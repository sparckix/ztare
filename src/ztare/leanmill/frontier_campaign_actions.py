"""Read-model and lifecycle actions for one frontier campaign attempt."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from ztare.common.leaf_workbench_environment import resolve_leaf_workbench_environment
from ztare.leanmill.common import read_json, write_json_atomic
from ztare.leanmill.exploration_budget import ExplorationBudget, ExplorationBudgetLedger
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
        inputs["prediction_formula_ids"] = [
            str(value) for value in candidate.get(prediction_field) or ()
        ]
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
    state = ledger.state()
    reservations = sorted(
        state["reservations"].values(),
        key=lambda value: (
            int(value.get("at_ms") or 0),
            str(value.get("reservation_id") or ""),
        ),
    )
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
        "soft_stop_reason": ledger.soft_stop_reason(),
    }


def frontier_campaign_status(attempt_dir: str | Path) -> dict[str, Any]:
    directory = Path(attempt_dir)
    run = read_json(directory / "run.json", {})
    boundary = read_json(directory / "boundary_completion.json", {})
    governance_recheck = read_json(directory / "boundary_governance_recheck.json", {})
    interpretation_rows = _interpretations(directory)
    interpretation = interpretation_rows[-1] if interpretation_rows else {}
    forge = read_json(directory / "adapter_forge_completion.json", {})
    retirement = read_json(directory / "retirement.json", {})
    campaign_manifest = read_json(directory / "campaign_manifest.json", {})
    budget_state = _budget_status(directory)
    lease_state = attempt_lease_status(directory)
    status = (
        "retired" if retirement
        else str(boundary.get("status") or "boundary_complete") if boundary
        else str(forge.get("status") or "adapter_forge_complete") if forge
        else "running"
        if budget_state.get("outstanding_reservation_count", 0)
        or lease_state.get("active")
        else str(run.get("status") or "missing")
    )
    navigation = run.get("navigation") or {}
    run_summary = _project(
        run,
        (
            "status", "brief_id", "blueprint_id", "context_hash",
            "packet_digest", "context_summary",
        ),
        finalist_count=len(navigation.get("finalists") or ()),
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
        "boundary_completion": boundary_summary,
        "adapter_forge_completion": forge_summary,
        "post_freeze_interpretation": _project(
            interpretation,
            ("status", "model", "reasoning_effort", "receipt_sha256"),
            attempt_count=len(interpretation_rows),
            novelty_assessment=(
                (interpretation.get("review") or {}).get("novelty_assessment")
            ),
        ),
        "retirement": retirement or None,
        "budget": dict(budget_state),
        "attempt_lease": lease_state,
    }


def inspect_frontier_campaign(attempt_dir: str | Path) -> dict[str, Any]:
    """Cold-safe user view; no sealed evidence or private signer bytes."""
    directory = Path(attempt_dir)
    if not (directory / "budget.events.jsonl").is_file():
        raise ValueError("campaign budget ledger is missing")
    run = read_json(directory / "run.json", {})
    interpretations = _interpretations(directory)
    return {
        "schema": "leanmill.frontier_campaign_inspection.v1",
        "status": frontier_campaign_status(directory)["status"],
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
            and existing.get("run_digest") == run.get("run_digest")
            and existing.get("context_hash") == run.get("context_hash")
            and int(existing.get("context_epoch", -1)) == context_epoch
            and (
                run.get("status") != "frontier_objective_unmet"
                or isinstance(existing.get("objective_unmet_check"), Mapping)
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
                program_ok = bool(
                    program.program_id == finalist.get("theory_program_id")
                    and program.context_hash == context.context_hash
                    and program.context_epoch == context_epoch
                    and program.presentation_formula_ids == tuple(sorted(formulas))
                    and program.prediction_formula_ids
                    == tuple(finalist.get("boundary_target_ids") or ())
                    and program.selection_receipt_id == receipt["receipt_id"]
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
        stop_ok = bool(
            _receipt_is_content_bound(stop)
            and stop.get("context_hash") == context.context_hash
            and stop.get("budget_digest") == run.get("budget_digest")
            and not rows
            and not rejection_checks
        )
        budget_stop_check = {
            "ok": stop_ok,
            "reason": stop.get("reason") if isinstance(stop, Mapping) else None,
            "receipt_sha256": (
                stop.get("receipt_sha256") if isinstance(stop, Mapping) else None
            ),
        }
        ok = ok and stop_ok
    objective_unmet_check = None
    if run.get("status") == "frontier_objective_unmet":
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
                and int(row.get("context_epoch", -1)) == context_epoch
                and row.get("objective_contract") == objective
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
        or language_request_check
        or isolated_language_request_check
    )
    core = {
        "schema": "leanmill.frontier_campaign_replay.v3",
        "ok": ok and has_replayable_outcome,
        "run_digest": run.get("run_digest"),
        "context_hash": context.context_hash,
        "context_epoch": context_epoch,
        "finalist_checks": rows,
        "rejection_checks": rejection_checks,
        "budget_stop_check": budget_stop_check,
        "objective_unmet_check": objective_unmet_check,
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
