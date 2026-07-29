"""Read-model and lifecycle actions for one frontier campaign attempt."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from ztare.common.leaf_workbench_environment import resolve_leaf_workbench_environment
from ztare.leanmill.common import read_json, write_json_atomic
from ztare.leanmill.exploration_budget import (
    RESOURCE_KINDS,
    ExplorationBudget,
    ExplorationBudgetLedger,
)
from ztare.leanmill.frontier_blueprint import (
    FrontierTheoryBlueprint,
    frontier_objective_contract,
    navigator_selection_mode,
)
from ztare.leanmill.frontier_campaign_runner import (
    FrontierAttemptLeaseBusy,
    attempt_lease_status,
    frontier_attempt_lease,
)
from ztare.leanmill.theory_ir import content_hash


FRONTIER_CAMPAIGN_REPLAY_SCHEMA = "leanmill.frontier_campaign_replay.v5"
from ztare.leanmill.theory_language import TheoryLanguageExpansionRequest
from ztare.leanmill.theory_program import TheoryProgram


def _context(directory: Path):
    if (directory / "formal_context.json").is_file():
        from ztare.leanmill.finite_theory_context import load_formal_theory_context

        return load_formal_theory_context(directory / "formal_context.json")
    if (directory / "evidence_context.json").is_file():
        from ztare.leanmill.evidence_theory_context import load_evidence_theory_context

        return load_evidence_theory_context(directory / "evidence_context.json")
    raise ValueError("campaign context snapshot is missing")


def _interpretations(directory: Path) -> list[dict[str, Any]]:
    paths = [directory / "post_freeze_interpretation.json"] + sorted(
        directory.glob("post_freeze_interpretation.[0-9][0-9][0-9].json")
    )
    return [
        row for row in (read_json(path, None) for path in paths)
        if isinstance(row, dict) and row
    ]


def _solver_runs(directory: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted((directory / "solver_runs").glob("*.json")):
        row = read_json(path, None)
        if not isinstance(row, Mapping):
            continue
        diagnostics = row.get("diagnostics") or {}
        timing = row.get("phase_timing") or {}
        rows.append({
            "task_id": str(row.get("task_id") or ""),
            "run_tag": str(row.get("run_tag") or ""),
            "status": str(row.get("status") or ""),
            "governed_status": str(row.get("governed_status") or ""),
            "solver_attempts": int(diagnostics.get("total", 0) or 0),
            "ratified_attempts": int(diagnostics.get("ratified", 0) or 0),
            "diagnostic_headline": str(diagnostics.get("headline") or ""),
            "phase_events": int(timing.get("total_events", 0) or 0),
            "phase_wall_s": float(timing.get("total_wall_s", 0.0) or 0.0),
            "error": str(row.get("error") or row.get("observability_error") or ""),
        })
    return rows


def _context_epoch(run: Mapping[str, Any]) -> int:
    navigation = run.get("navigation") or {}
    return int(
        navigation.get(
            "context_epoch",
            (run.get("context_summary") or {}).get("context_epoch", 0),
        )
    )


def _receipt_is_content_bound(receipt: Mapping[str, Any] | None) -> bool:
    if not isinstance(receipt, Mapping) or not receipt:
        return False
    core = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    return receipt.get("receipt_sha256") == content_hash(core)


def _fields_match(
    row: Mapping[str, Any] | None, expected: Mapping[str, Any]
) -> bool:
    return bool(
        isinstance(row, Mapping)
        and all(row.get(key) == value for key, value in expected.items())
    )


def _project(
    row: Mapping[str, Any], fields: tuple[str, ...], **derived: Any
) -> dict[str, Any] | None:
    return ({key: row.get(key) for key in fields} | derived) if row else None


def _string_ids(values: Any) -> tuple[str, ...]:
    return tuple(sorted(str(value) for value in values or ()))


def _replay_selection(
    handler: Any,
    contract: Any,
    candidate: Mapping[str, Any],
    *,
    selection_mode: str,
    prediction_field: str,
) -> tuple[list[str], dict[str, Any], Mapping[str, Any]]:
    formulas = [str(value) for value in candidate.get("formula_ids") or ()]
    inputs: dict[str, Any] = {"formula_ids": formulas}
    if selection_mode == "theory_program":
        predictions = [
            str(value) for value in candidate.get(prediction_field) or ()
        ]
        # Match the live navigator's typed input exactly.  A v2 theory program
        # may carry only a host-compiled task, in which case an absent
        # prediction field and an explicitly empty prediction list are not the
        # same selector request.
        if predictions:
            inputs["prediction_formula_ids"] = predictions
    receipt = handler(
        ".",
        {"input_refs": inputs},
        None,
        contract,
    )
    return formulas, receipt, receipt["output_summary"]


def _budget_status(directory: Path) -> dict[str, Any]:
    budget_row = read_json(directory / "budget.json", {})
    if not budget_row or not (directory / "budget.events.jsonl").is_file():
        return {}
    budget = ExplorationBudget.from_json(budget_row)
    ledger = ExplorationBudgetLedger(
        directory / "budget.events.jsonl",
        budget,
        attempt_id=directory.name,
    )
    objective_active = False
    blueprint_row = read_json(directory / "blueprint.json", {})
    if blueprint_row:
        try:
            objective_active = frontier_objective_contract(
                FrontierTheoryBlueprint.from_json(blueprint_row)
            ) is not None
        except (KeyError, TypeError, ValueError):
            pass
    state = ledger.state()
    reservations = sorted(
        state["reservations"].values(),
        key=lambda value: (
            int(value.get("at_ms") or 0),
            str(value.get("reservation_id") or ""),
        ),
    )
    capacity_projection = ledger.remaining_capacities(
        phases=("navigation", "expansion", "boundary", "interpretation")
    )
    remaining = {
        phase: {
            resource: value
            for resource, value in values.items()
            if value
        }
        for phase, values in capacity_projection.items()
    }
    return {
        "budget_digest": budget.digest,
        "elapsed_ms": ledger.elapsed_ms(),
        "wall_clock_cap_s": state.get("wall_clock_cap_s", budget.wall_clock_s),
        "usage": {key: value for key, value in state["usage"].items() if value},
        "phase_usage": {
            phase: {key: value for key, value in values.items() if value}
            for phase, values in state["phase_usage"].items()
            if any(values.values())
        },
        "outstanding_reservation_count": len(reservations),
        "outstanding_actions": [
            {
                "action_id": str(row.get("action_id") or ""),
                "phase": str(row.get("phase") or ""),
                "resources": {
                    str(key): int(value)
                    for key, value in dict(row.get("resources") or {}).items()
                    if int(value)
                },
                "reserved_at_ms": int(row.get("at_ms") or 0),
            }
            for row in reservations
        ],
        "soft_stop_reason": ledger.soft_stop_reason(
            allow_coverage_target=not objective_active
        ),
        "coverage_stop_active": not objective_active,
        "remaining": {phase: values for phase, values in remaining.items() if values},
    }


def frontier_campaign_status(attempt_dir: str | Path) -> dict[str, Any]:
    directory = Path(attempt_dir)
    run = read_json(directory / "run.json", {})
    boundary = read_json(directory / "boundary_completion.json", {})
    governance_recheck = read_json(directory / "boundary_governance_recheck.json", {})
    interpretation_rows = _interpretations(directory)
    interpretation = interpretation_rows[-1] if interpretation_rows else {}
    forge: dict[str, Any] = {}
    forge_conformance: dict[str, Any] = {}
    gap_row = run.get("adapter_gap") or read_json(directory / "adapter_gap.json", {})
    if isinstance(gap_row, Mapping) and gap_row:
        from ztare.leanmill.adapter_forge import (
            AdapterGap,
            adapter_forge_attempt_directory,
            read_adapter_forge_completion,
        )

        try:
            gap = AdapterGap.from_json(gap_row)
            forge = read_adapter_forge_completion(directory, gap) or {}
            forge_conformance = read_json(
                adapter_forge_attempt_directory(directory, gap.gap_id)
                / "adapter_forge_host_conformance.json",
                {},
            )
        except (KeyError, TypeError, ValueError):
            forge = {}
            forge_conformance = {}
    sieve_paths = sorted(
        directory.glob("compound_implication_sieve_completion.stratum-*.json")
    )
    sieve = read_json(sieve_paths[-1], {}) if sieve_paths else {}
    retirement = read_json(directory / "retirement.json", {})
    replay = read_json(directory / "replay.json", {})
    closure_gate = read_json(directory / "campaign_closure_gate.json", {})
    campaign_manifest = read_json(directory / "campaign_manifest.json", {})
    budget_state = _budget_status(directory)
    lease_state = attempt_lease_status(directory)
    workbench_authorization = read_json(
        directory / "campaign_workbench_successor_authorization_required.json",
        {},
    )
    workbench_transitions = sorted(
        directory.glob("campaign_workbench_successor.*.json")
    )
    workbench_transition = (
        read_json(workbench_transitions[-1], {}) if workbench_transitions else {}
    )
    boundary_supersession_paths = sorted(
        directory.glob("boundary_attempt_supersession.*.json")
    )
    boundary_supersession = (
        read_json(boundary_supersession_paths[-1], {})
        if boundary_supersession_paths else {}
    )
    run_status = str(run.get("status") or "missing")
    status = (
        "retired"
        if retirement
        else "running"
        if budget_state.get("outstanding_reservation_count", 0)
        or lease_state.get("active")
        else str(boundary.get("status") or "boundary_complete")
        if boundary
        and run_status
        in {
            "frontier_candidates_frozen_awaiting_boundary_approval",
            "frontier_no_candidate",
        }
        else str(forge.get("status") or "adapter_forge_complete")
        if forge and run_status == "blocked_adapter_gap"
        else "workbench_successor_authority_required"
        if workbench_authorization
        else run_status
    )
    navigation = run.get("navigation") or {}
    finalist_summaries = [
        _project(
            row,
            (
                "node_id", "theory_program_id", "formula_ids",
                "boundary_target_ids", "selection_receipt_id",
            ),
        )
        for row in navigation.get("finalists") or ()
        if isinstance(row, Mapping)
    ]
    objective_survivor_summaries = [
        _project(
            row,
            (
                "node_id", "theory_program_id", "formula_ids",
                "boundary_target_ids", "selection_receipt_id",
            ),
        )
        for row in navigation.get("objective_survivors") or ()
        if isinstance(row, Mapping)
    ]
    wave_image = (
        navigation.get("search_wave_image_receipt")
        or navigation.get("search_wave_image_preview")
        or {}
    )
    run_summary = _project(
        run,
        (
            "status", "brief_id", "blueprint_id", "context_hash",
            "packet_digest", "context_summary",
        ),
        finalist_count=len(navigation.get("finalists") or ()),
        finalists=finalist_summaries,
        objective_survivor_count=len(objective_survivor_summaries),
        objective_survivors=objective_survivor_summaries,
        pending_leaf_decision=_project(
            navigation.get("pending_leaf_decision") or {},
            ("reason", "receipt_id", "receipt_sha256"),
        ),
        last_trace_decision=str(
            ((navigation.get("trace") or [{}])[-1] or {}).get("decision") or ""
        ),
        provider_calls=run.get("provider_calls", 0),
    )
    boundary_result = boundary.get("boundary_result") or {}
    boundary_summary = _project(
        boundary,
        ("status", "completion_sha256"),
        query_count=len(
            boundary_result.get("query_results") or ()
        ),
        stop_reason=boundary_result.get("stop_reason"),
        stop_policy=(
            boundary.get("stop_policy") or boundary_result.get("stop_policy")
        ),
        governance_recheck=_project(
            governance_recheck,
            ("status", "receipt_sha256"),
            proved_attributed_count=governance_recheck.get(
                "proved_attributed_count", 0
            ),
        ),
    )
    forge_summary = _project(forge, ("status", "completion_sha256", "gap_id"))
    return {
        "schema": "leanmill.frontier_campaign_status.v1",
        "status": status,
        "attempt_dir": str(directory),
        "campaign_id": campaign_manifest.get("campaign_id"),
        "run": run_summary,
        "search_wave_image": _project(
            wave_image,
            (
                "growth_kind", "search_wave", "new_raw_count",
                "new_image_count", "receipt_sha256",
            ),
        ),
        "boundary_completion": boundary_summary,
        "boundary_attempt_supersession": _project(
            boundary_supersession,
            (
                "supersession_kind", "source_stop_reason",
                "prior_stop_policy", "current_stop_policy",
                "superseded_completion_sha256", "receipt_sha256",
            ),
        ),
        "adapter_forge_completion": forge_summary,
        "adapter_forge_conformance": _project(
            forge_conformance,
            (
                "receipt_sha256", "coordinate_receipt_sha256",
                "coordinate_class_count", "retained_identity_fraction",
                "compression_bits",
            ),
        ),
        "compound_implication_sieve": _project(
            sieve,
            (
                "status", "sieve_receipt", "candidate_count",
                "eliminated_count", "survivor_count", "queries_used",
            ),
        ),
        "post_freeze_interpretation": _project(
            interpretation,
            ("status", "model", "reasoning_effort", "receipt_sha256"),
            attempt_count=len(interpretation_rows),
            novelty_assessment=(
                (interpretation.get("review") or {}).get("novelty_assessment")
            ),
        ),
        "solver_runs": _solver_runs(directory),
        "cold_replay": _project(
            replay,
            ("schema", "ok", "receipt_sha256", "provider_calls"),
            budget_stop_ok=(replay.get("budget_stop_check") or {}).get("ok"),
            retained_evidence_check_count=(
                replay.get("budget_stop_check") or {}
            ).get("retained_evidence_check_count"),
        ),
        "campaign_closure_gate": _project(
            closure_gate,
            (
                "ready",
                "missing_lineage_disposition_ids",
                "unadjudicated_generalization_residual_ids",
                "receipt_sha256",
            ),
        ),
        "retirement": retirement or None,
        "budget": dict(budget_state),
        "attempt_lease": lease_state,
        "workbench_successor": _project(
            workbench_transition or workbench_authorization,
            (
                "status",
                "source_packet_digest",
                "target_packet_digest",
                "authority_ref",
                "receipt_sha256",
                "next_route",
            ),
            policy_id=(
                (workbench_transition or workbench_authorization).get("policy")
                or {}
            ).get("policy_id"),
        ),
    }


def inspect_frontier_campaign(attempt_dir: str | Path) -> dict[str, Any]:
    """Cold-safe user view; no sealed evidence or private signer bytes."""
    directory = Path(attempt_dir)
    if not (directory / "budget.events.jsonl").is_file():
        raise ValueError("campaign budget ledger is missing")
    run = read_json(directory / "run.json", {})
    interpretations = _interpretations(directory)
    campaign_status = frontier_campaign_status(directory)
    return {
        "schema": "leanmill.frontier_campaign_inspection.v1",
        "status": campaign_status["status"],
        "campaign_definition_ref": (
            "campaign_definition.yaml"
            if (directory / "campaign_definition.yaml").is_file() else None
        ),
        "campaign_manifest_ref": (
            "campaign_manifest.json"
            if (directory / "campaign_manifest.json").is_file() else None
        ),
        "cold_manifest": read_json(directory / "cold_navigator_manifest.json", None),
        "context_summary": run.get("context_summary"),
        "navigation": run.get("navigation"),
        "boundary": read_json(directory / "boundary_result.json", None),
        "theory_task_discharge": read_json(
            directory / "theory_task_discharge.json", None
        ),
        "theory_task_discharge_consumption": read_json(
            directory / "theory_task_discharge_consumption.json", None
        ),
        "adapter_forge_conformance": campaign_status.get(
            "adapter_forge_conformance", {}
        ),
        "boundary_governance_recheck": read_json(
            directory / "boundary_governance_recheck.json", None
        ),
        "post_freeze_interpretation": (
            interpretations[-1] if interpretations else None
        ),
        "budget_stop_receipt": read_json(directory / "budget_stop_receipt.json", None),
        "sealed_evidence_visible": False,
        "private_signer_visible": False,
    }


def replay_frontier_campaign(attempt_dir: str | Path) -> dict[str, Any]:
    """Revalidate frozen navigator selections against the replayed context."""
    directory = Path(attempt_dir)
    run = read_json(directory / "run.json", {})
    if not isinstance(run, dict) or not run:
        raise ValueError("campaign replay requires an active frozen run")
    navigation = run.get("navigation") or {}
    context_epoch = _context_epoch(run)
    existing = read_json(directory / "replay.json", None)
    if isinstance(existing, dict) and existing:
        if (
            _receipt_is_content_bound(existing)
            and existing.get("schema") == FRONTIER_CAMPAIGN_REPLAY_SCHEMA
            and existing.get("run_digest") == run.get("run_digest")
            and existing.get("context_hash") == run.get("context_hash")
            and int(existing.get("context_epoch", -1)) == context_epoch
            and (
                run.get("status") != "frontier_objective_unmet"
                or isinstance(existing.get("objective_unmet_check"), Mapping)
                or isinstance(
                    existing.get("language_compilation_feedback_check"), Mapping
                )
            )
        ):
            return existing
        for archived_run_path in sorted(directory.glob("run.epoch-*.json")):
            archived_run = read_json(archived_run_path, {})
            if archived_run.get("context_hash") != existing.get("context_hash"):
                continue
            archived_epoch = _context_epoch(archived_run)
            archived_replay_path = directory / f"replay.epoch-{archived_epoch:03d}.json"
            if not archived_replay_path.exists():
                write_json_atomic(archived_replay_path, existing)
            break
    context = _context(directory)
    if context.context_hash != run.get("context_hash"):
        raise ValueError("replayed context differs from frozen run")
    blueprint = FrontierTheoryBlueprint.from_json(
        read_json(directory / "blueprint.json", {})
    )
    selection_mode = navigator_selection_mode(blueprint)
    environment = resolve_leaf_workbench_environment(
        "axiompack",
        context=context,
        context_epoch=context_epoch,
        selection_mode=selection_mode,
        max_presentation_size=blueprint.pack_arity,
    )
    handler = environment["action_handlers"]["select_theory_presentation"]
    rows: list[dict[str, Any]] = []
    ok = True
    for finalist in navigation.get("finalists") or ():
        formulas, receipt, summary = _replay_selection(
            handler,
            environment["contract"],
            finalist,
            selection_mode=selection_mode,
            prediction_field="boundary_target_ids",
        )
        expected_synergy = _string_ids(finalist.get("joint_only_consequence_ids"))
        actual_synergy = _string_ids(summary.get("synergy_formula_ids"))
        actual_residual = _string_ids(
            summary.get("residual_prediction_formula_ids")
            if selection_mode == "theory_program"
            else summary.get("residual_synergy_formula_ids")
        )
        residual_field = (
            "residual_prediction_formula_ids"
            if selection_mode == "theory_program"
            else "residual_joint_only_consequence_ids"
        )
        expected_residual = _string_ids(finalist.get(residual_field))
        program_ok = True
        if selection_mode == "theory_program":
            try:
                program = TheoryProgram.from_json(finalist.get("theory_program"))
            except (TypeError, ValueError):
                program_ok = False
            else:
                program_task_ids = _string_ids(
                    row.contract_id for row in program.task_discharge_contracts
                )
                finalist_task_ids = _string_ids(
                    finalist.get("task_contract_ids")
                )
                program_ok = bool(
                    program.program_id == finalist.get("theory_program_id")
                    and program.context_hash == context.context_hash
                    and program.context_epoch == context_epoch
                    and program.presentation_formula_ids == tuple(sorted(formulas))
                    and program.prediction_formula_ids
                    == tuple(finalist.get("boundary_target_ids") or ())
                    and program.selection_receipt_id == receipt["receipt_id"]
                    and program_task_ids == finalist_task_ids
                    and bool(
                        program.prediction_formula_ids
                        or program.task_discharge_contracts
                    )
                    and (
                        not isinstance(finalist.get("prediction_profile"), Mapping)
                        or finalist["prediction_profile"].get("receipt_sha256")
                        == dict(summary.get("prediction_profile") or {}).get(
                            "receipt_sha256"
                        )
                    )
                )
        row_ok = (
            summary["node_id"] == finalist.get("node_id")
            and (
                selection_mode == "theory_program"
                or summary["independent"] is True
            )
            and (
                not finalist.get("selection_receipt_id")
                or receipt["receipt_id"] == finalist.get("selection_receipt_id")
            )
            and actual_synergy == expected_synergy
            and (
                residual_field not in finalist
                or actual_residual == expected_residual
            )
            and program_ok
        )
        ok = ok and row_ok
        rows.append(
            {
                "node_id": finalist.get("node_id"),
                "ok": row_ok,
                "selection_receipt_id": receipt["receipt_id"],
                "synergy_formula_ids": list(actual_synergy),
                "residual_synergy_formula_ids": list(actual_residual),
                "candidate_kind": selection_mode,
                "theory_program_id": finalist.get("theory_program_id"),
            }
        )
    rejection_checks: list[dict[str, Any]] = []
    reject_all = navigation.get("reject_all_receipt") or {}
    for rejected in reject_all.get("rejected_candidates") or ():
        rejected_mode = str(rejected.get("selection_mode") or selection_mode)
        formulas, receipt, summary = _replay_selection(
            handler,
            environment["contract"],
            rejected,
            selection_mode=rejected_mode,
            prediction_field="prediction_formula_ids",
        )
        residual = dict(
            (summary.get("program_yield") or {}).get("coordinates") or {}
            if rejected_mode == "theory_program"
            else summary.get("residual_yield") or {}
        )
        replay_residual_ids = (
            summary.get("residual_prediction_formula_ids")
            if rejected_mode == "theory_program"
            else summary.get("residual_synergy_formula_ids")
        )
        row_ok = bool(
            receipt["receipt_id"] == rejected.get("selection_receipt_id")
            and residual.get("baseline_ref")
        )
        if rejected_mode == "theory_program":
            expected_profile = rejected.get("prediction_profile")
            actual_profile = summary.get("prediction_profile")
            row_ok = bool(
                row_ok
                and rejected.get("rejection_authority")
                == "anonymous_theory_navigator"
                and str(rejected.get("refusal_rationale") or "").strip()
                and isinstance(expected_profile, Mapping)
                and isinstance(actual_profile, Mapping)
                and expected_profile.get("receipt_sha256")
                == actual_profile.get("receipt_sha256")
            )
        else:
            row_ok = (
                row_ok
                and float(residual.get("identification_bits", -1.0)) == 0.0
                and not replay_residual_ids
            )
        ok = ok and row_ok
        rejection_checks.append(
            {
                "formula_ids": formulas,
                "ok": row_ok,
                "selection_receipt_id": receipt["receipt_id"],
                "baseline_ref": residual.get("baseline_ref"),
                "identification_bits": residual.get("identification_bits"),
            }
        )
    budget_stop_check = None
    if run.get("status") == "budget_stopped":
        stop = run.get("budget_stop_receipt")
        if not isinstance(stop, Mapping):
            stop = read_json(directory / "budget_stop_receipt.json", None)
        objective = frontier_objective_contract(blueprint)
        retained_evidence_checks = [*rows, *rejection_checks]
        retained_evidence_ok = bool(
            all(row.get("ok") is True for row in retained_evidence_checks)
            if isinstance(objective, Mapping)
            else not retained_evidence_checks
        )
        stop_ok = bool(
            _receipt_is_content_bound(stop)
            and stop.get("context_hash") == context.context_hash
            and stop.get("budget_digest") == run.get("budget_digest")
            and retained_evidence_ok
        )
        budget_stop_check = {
            "ok": stop_ok,
            "reason": stop.get("reason") if isinstance(stop, Mapping) else None,
            "receipt_sha256": (
                stop.get("receipt_sha256") if isinstance(stop, Mapping) else None
            ),
            "outer_objective_active": isinstance(objective, Mapping),
            "retained_evidence_check_count": len(retained_evidence_checks),
        }
        ok = ok and stop_ok
    language_feedback_row = navigation.get("language_compilation_feedback")
    if not isinstance(language_feedback_row, Mapping):
        language_feedback_row = next(
            (
                row
                for row in reversed(navigation.get("objective_review_history") or ())
                if isinstance(row, Mapping)
                and row.get("schema")
                == "leanmill.theory_language_compilation_feedback.v1"
            ),
            None,
        )
    objective_unmet_check = None
    if (
        run.get("status") == "frontier_objective_unmet"
        and not isinstance(language_feedback_row, Mapping)
    ):
        objective = frontier_objective_contract(blueprint)
        history = navigation.get("objective_review_history") or ()
        history_ok = bool(
            isinstance(objective, Mapping)
            and history
            and all(
                isinstance(row, Mapping)
                and _receipt_is_content_bound(row)
                and row.get("route") == "continue_search"
                and row.get("context_hash") == context.context_hash
                and (
                    int(row.get("context_epoch", -1)) == context_epoch
                    or (
                        row.get("schema")
                        == "leanmill.boundary_search_feedback.v1"
                        and row.get("context_epoch") is None
                        and bool(row.get("source_run_digest"))
                        and bool(row.get("boundary_result_sha256"))
                    )
                )
                and (
                    row.get("objective_contract") == objective
                    or (
                        row.get("schema")
                        == "leanmill.boundary_search_feedback.v1"
                        and row.get("objective_contract") is None
                        and bool(row.get("source_run_digest"))
                        and bool(row.get("boundary_result_sha256"))
                    )
                )
                for row in history
            )
        )
        terminal = (
            navigation.get("lineage_synthesis_budget_stop")
            or navigation.get("navigation_exhausted_receipt")
        )
        terminal_ok = bool(
            _receipt_is_content_bound(terminal)
            and terminal.get("context_hash") == context.context_hash
            and int(terminal.get("context_epoch", -1)) == context_epoch
        )
        objective_ok = bool(
            history_ok and terminal_ok and not rows and not rejection_checks
        )
        objective_unmet_check = {
            "ok": objective_ok,
            "review_count": len(history),
            "terminal_receipt_sha256": (
                terminal.get("receipt_sha256")
                if isinstance(terminal, Mapping) else None
            ),
        }
        ok = ok and objective_ok
    language_feedback_check = None
    if isinstance(language_feedback_row, Mapping):
        artifact = read_json(
            directory / "theory_language_compilation_feedback.json", None
        )
        request_ids: set[str] = set()
        for path in directory.glob("theory_language_expansion_request.epoch-*.json"):
            request_row = read_json(path, None)
            if not isinstance(request_row, Mapping):
                continue
            request_ids.add(
                TheoryLanguageExpansionRequest.from_json(request_row).request_id
            )
        feedback_ok = bool(
            artifact == dict(language_feedback_row)
            and _receipt_is_content_bound(language_feedback_row)
            and language_feedback_row.get("context_hash") == context.context_hash
            and language_feedback_row.get("request_id") in request_ids
            and language_feedback_row.get("outcome") in {"rejected", "unavailable"}
            and str(language_feedback_row.get("reason") or "").strip()
            and language_feedback_row.get("route") == "continue_search"
            and language_feedback_row.get("repeat_requires_new_evidence") is True
        )
        language_feedback_check = {
            "ok": feedback_ok,
            "request_id": language_feedback_row.get("request_id"),
            "outcome": language_feedback_row.get("outcome"),
            "receipt_sha256": language_feedback_row.get("receipt_sha256"),
        }
        ok = ok and feedback_ok
    language_request_check = None
    language_request_row = navigation.get("language_expansion_request")
    if isinstance(language_request_row, Mapping):
        request = TheoryLanguageExpansionRequest.from_json(language_request_row)
        artifact = read_json(
            directory
            / f"theory_language_expansion_request.epoch-{request.source_epoch:03d}.json",
            None,
        )
        request_ok = bool(
            artifact == request.to_json()
            and request.source_context_hash == context.context_hash
            and request.source_epoch == context_epoch
        )
        language_request_check = {
            "ok": request_ok,
            "request_id": request.request_id,
        }
        ok = ok and request_ok
    isolated_language_request_check = None
    formula_requests = navigation.get("expansion_proposals")
    language_requests = navigation.get("theory_language_expansion_requests")
    if (
        isinstance(formula_requests, list)
        and formula_requests
    ) or (
        isinstance(language_requests, list)
        and language_requests
    ):
        artifact = read_json(
            directory
            / f"isolated_lineage_language_requests.epoch-{context_epoch:03d}.json",
            None,
        )
        request_ok = bool(
            _receipt_is_content_bound(artifact)
            and int(artifact.get("source_epoch", -1)) == context_epoch
            and _fields_match(
                artifact,
                {
                    "source_context_hash": context.context_hash,
                    "formula_requests": list(formula_requests or ()),
                    "theory_language_requests": list(language_requests or ()),
                },
            )
        )
        isolated_language_request_check = {
            "ok": request_ok,
            "receipt_sha256": (
                artifact.get("receipt_sha256")
                if isinstance(artifact, Mapping)
                else None
            ),
        }
        ok = ok and request_ok
    has_replayable_outcome = bool(
        rows
        or rejection_checks
        or budget_stop_check
        or objective_unmet_check
        or language_feedback_check
        or language_request_check
        or isolated_language_request_check
    )
    core = {
        "schema": FRONTIER_CAMPAIGN_REPLAY_SCHEMA,
        "ok": ok and has_replayable_outcome,
        "run_digest": run.get("run_digest"),
        "context_hash": context.context_hash,
        "context_epoch": context_epoch,
        "finalist_checks": rows,
        "rejection_checks": rejection_checks,
        "budget_stop_check": budget_stop_check,
        "objective_unmet_check": objective_unmet_check,
        "language_compilation_feedback_check": language_feedback_check,
        "language_expansion_request_check": language_request_check,
        "isolated_language_requests_check": isolated_language_request_check,
        "provider_calls": 0,
    }
    receipt = {**core, "receipt_sha256": content_hash(core)}
    write_json_atomic(directory / "replay.json", receipt)
    return receipt


def request_frontier_campaign_stop(
    attempt_dir: str | Path,
    *,
    authority_ref: str,
) -> dict[str, Any]:
    directory = Path(attempt_dir)
    if not (directory / "budget.events.jsonl").is_file():
        raise ValueError("campaign budget ledger is missing")
    budget = ExplorationBudget.from_json(read_json(directory / "budget.json", {}))
    ledger = ExplorationBudgetLedger(
        directory / "budget.events.jsonl",
        budget,
        attempt_id=directory.name,
    )
    ledger.request_user_stop(authority_ref=authority_ref)
    return {
        "schema": "leanmill.frontier_campaign_stop_request.v1",
        "status": "user_stop_requested",
        "attempt_dir": str(directory),
        "authority_ref": authority_ref,
        "budget_digest": budget.digest,
    }


def retire_frontier_campaign(
    attempt_dir: str | Path,
    *,
    authority_ref: str,
    reason: str,
    _attempt_lease: Any | None = None,
) -> dict[str, Any]:
    directory = Path(attempt_dir)
    if _attempt_lease is None:
        lease_state = attempt_lease_status(directory)
        if lease_state.get("active") is True:
            raise ValueError("campaign retirement is denied while an attempt owner is active")
        if lease_state.get("status") != "unbound":
            try:
                with frontier_attempt_lease(
                    directory, action="retire_frontier_campaign"
                ) as lease:
                    return retire_frontier_campaign(
                        directory,
                        authority_ref=authority_ref,
                        reason=reason,
                        _attempt_lease=lease,
                    )
            except FrontierAttemptLeaseBusy as exc:
                raise ValueError(
                    "campaign retirement is denied while an attempt owner is active"
                ) from exc
    existing = read_json(directory / "retirement.json", None)
    if isinstance(existing, dict) and existing:
        return existing
    if not authority_ref.strip() or not reason.strip():
        raise ValueError("campaign retirement requires authority and reason")
    core = {
        "schema": "leanmill.frontier_campaign_retirement.v1",
        "status": "retired",
        "attempt_dir": str(directory),
        "authority_ref": authority_ref,
        "reason": reason,
        "prior_status": frontier_campaign_status(directory)["status"],
    }
    receipt = {**core, "receipt_sha256": content_hash(core)}
    write_json_atomic(directory / "retirement.json", receipt)
    return receipt


__all__ = [
    "frontier_campaign_status", "inspect_frontier_campaign",
    "replay_frontier_campaign", "request_frontier_campaign_stop",
    "retire_frontier_campaign",
]
