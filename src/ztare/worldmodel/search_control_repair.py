"""Strategy cards for search-control residues.

This module turns a planner-level receipt pattern into a falsifiable Strategy
Office card without an LLM call:

    closed/usable dynamics + no terminal event + no new evidence

The output is intentionally not a model patch. It is a cross-cycle work order
requiring a more specific target, discriminator, or evidence request before the
loop spends another broad sweep on the same residue.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ztare.common.abstraction_functor import (
    FiniteQuotient,
    parse_disjunctive_atoms,
)
from ztare.common.cegis_membrane import assess_cegis_membrane
from ztare.common.operator_proposal_contract import (
    DISPOSITION_ACCEPTED,
    open_cards,
    record_disposition,
    set_disposition,
)
from ztare.research_director.strategy_decision_policy import (
    STRATEGY_LEDGER,
    StrategyCardBatchSubmission,
    submit_strategy_card_batch,
)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - receipts are best-effort readers
        return {}
    return obj if isinstance(obj, dict) else {}


def _ledger_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _candidate_memory_records(path: Path) -> list[dict[str, Any]]:
    obj = _load_json(path)
    records = obj.get("records") if isinstance(obj, dict) else []
    if not isinstance(records, list):
        return []
    return [r for r in records if isinstance(r, dict)]


def _current_gate_passing_candidate(
    project: Path,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Select support only from the active carrier/evidence population."""
    try:
        from ztare.worldmodel.carrier_loader import (
            CarrierEvidenceIdentityError,
            require_current_carrier_evidence_binding,
            resolve_current_carrier_evidence_identity,
        )

        current = resolve_current_carrier_evidence_identity(project)
    except (OSError, TypeError, ValueError):
        return {}
    passing = [
        r for r in records
        if (
            float(r.get("gate_score") or 0.0) >= 1.0
            and int(r.get("passed_gates") or 0) > 0
            and int(r.get("holdout_depth") or 0) > 0
        )
    ]
    current_passing = []
    for row in passing:
        try:
            binding = require_current_carrier_evidence_binding(row, current)
        except CarrierEvidenceIdentityError:
            continue
        current_passing.append((row, binding))
    if not current_passing:
        return {}
    current_passing.sort(key=lambda pair: str(pair[0].get("observed_at_utc") or ""))
    row, binding = current_passing[-1]
    has_membrane = "claim_class" in row or "holdout_exposed_to_proposer" in row
    return {
        "sha": str(row.get("sha") or ""),
        "observed_at_utc": str(row.get("observed_at_utc") or ""),
        "source_type": str(row.get("source_type") or ""),
        "gate_score": row.get("gate_score"),
        "passed_gates": row.get("passed_gates"),
        "holdout_depth": row.get("holdout_depth"),
        "assistance_label": str(row.get("assistance_label") or ""),
        "run_role": str(row.get("run_role") or "EVALUATION"),
        "holdout_exposed_to_proposer": bool(row.get("holdout_exposed_to_proposer")),
        "claim_class": (
            str(row.get("claim_class"))
            if has_membrane
            else "candidate_gate_passed_visibility_unrecorded"
        ),
        "fresh_holdout_required": (
            bool(row.get("fresh_holdout_required"))
            if has_membrane
            else True
        ),
        "carrier_evidence_identity": binding,
    }


def _terminal_autonomy_provenance(terminal: dict[str, Any]) -> dict[str, Any]:
    provenance = terminal.get("autonomy_provenance")
    assistance = str(terminal.get("assistance_label") or "")
    if isinstance(provenance, dict):
        interventions = provenance.get("operator_interventions")
        label = str(provenance.get("label") or assistance)
        proven = (
            interventions == 0
            and label in {"autonomous", "self_play", "unassisted"}
        )
        reason = "" if proven else "terminal_provenance_not_unassisted"
        return {
            "proven": proven,
            "reason": reason,
            "assistance_label": label,
            "operator_interventions": interventions,
            "source": str(provenance.get("source") or "terminal_report"),
        }
    if assistance in {"autonomous", "self_play", "unassisted"}:
        return {
            "proven": True,
            "reason": "",
            "assistance_label": assistance,
            "operator_interventions": 0,
            "source": "terminal_report.assistance_label",
        }
    return {
        "proven": False,
        "reason": "missing_explicit_unassisted_terminal_provenance",
        "assistance_label": assistance,
        "operator_interventions": None,
        "source": "",
    }


def build_search_control_residue_card(dossier: dict[str, Any]) -> dict[str, Any] | None:
    """Build a substrate-neutral Strategy Office card from planner anomalies.

    The card is only a routing constraint. It cannot adopt a model, weaken a
    gate, or claim a solve; the next cycle must discharge it with a terminal
    event, new evidence, or a narrower executable strategy receipt.
    """
    planner = dossier.get("planner_attention_pressure") or {}
    anomalies = [a for a in planner.get("anomalies") or [] if isinstance(a, dict)]
    if not anomalies:
        return None

    ledger = dossier.get("ledger_closure") or {}
    cycles = [a.get("cycle") for a in anomalies if a.get("cycle") is not None]
    steps = [int(a.get("steps") or 0) for a in anomalies]
    goal_candidates = int(ledger.get("goal_candidates_undispositioned") or 0)
    planning_outcome = next(
        (
            dict(a["planning_outcome"])
            for a in reversed(anomalies)
            if isinstance(a.get("planning_outcome"), dict)
            and a["planning_outcome"]
        ),
        {},
    )

    plan = {
        "residue_quotient": {
            "residue_class": "closed_dynamics_no_terminal_progress",
            "anomaly_class": "plan_exhausted_without_terminal_or_new_evidence",
            "anomaly_count": len(anomalies),
            "cycles": cycles,
            "total_steps": sum(steps),
        },
        "routing_class": "target_synthesis_or_discriminating_probe",
        "planning_outcome": planning_outcome,
        "candidate_status": {
            "goal_abduction_mode": ledger.get("goal_abduction_mode"),
            "goal_candidates_undispositioned": goal_candidates,
            "open_operator_cards": int(ledger.get("open_operator_cards") or 0),
        },
        "discriminator_axis": {
            "axis": "target_specification_gap_vs_transition_model_gap",
            "class_invariant": (
                "zero information gain under a reusable dynamics model must be "
                "routed by residual class, not by the order or count of failed "
                "broad sweeps"
            ),
            "required_receipt": (
                "name a terminal-predicate/goal-cue receipt or a model-gap "
                "counterexample receipt before repeating broad coverage"
            ),
        },
        "required_next_gate": {
            "command": "arc3_play_loop",
            "spends_external_actions": True,
            "success_status": (
                "terminal_event_or_new_evidence_or_more_specific_strategy_receipt"
            ),
        },
    }
    family_identity = {
        "residue_class": plan["residue_quotient"]["residue_class"],
        "anomaly_class": plan["residue_quotient"]["anomaly_class"],
        "routing_class": plan["routing_class"],
        "discriminator_axis": plan["discriminator_axis"]["axis"],
    }
    family = (
        "search_control_residue_repair|"
        + json.dumps(family_identity, sort_keys=True)
    )
    return {
        "schema": "strategy-experiment-v1",
        "kind": "search_control_residue_repair",
        "failure_family": family,
        "rationale": (
            "planner receipts show dynamics-driven pursuit exhausted without a "
            "terminal event or new evidence; broad coverage should be replaced "
            "by target synthesis or a discriminating probe"
        ),
        "falsifiable_prediction": (
            "the next cycle either reaches a terminal event, grows evidence, or "
            "produces a narrower executable strategy/goal-discriminator receipt"
        ),
        "action_plan": plan,
        "kill_condition": (
            "another plan_exhausted/no-new-evidence cycle occurs with no narrower "
            "strategy receipt and no terminal counterexample"
        ),
        "disposition": "open",
    }


def write_search_control_repair_card(project: str | Path) -> list[dict[str, Any]]:
    """Materialize the planner-attention card through the Strategy membrane."""
    from ztare.worldmodel.strategy_battery import WorldmodelBattery

    root = Path(project)
    dossier = WorldmodelBattery().run_audits(root)
    card = build_search_control_residue_card(dossier)
    if card is None:
        return []
    receipt = submit_strategy_card_batch(StrategyCardBatchSubmission(
        project_dir=root,
        cards=[card],
        source_ref="search_control_repair:planner_residue",
    ))
    return list(receipt.get("written_cards") or [])


def _status_options(status: Any) -> set[str]:
    """Parse a declared gate-status formula into symbolic atoms.

    Strategy cards currently use compact names such as
    ``terminal_event_or_new_evidence_or_more_specific_strategy_receipt``.
    This parser keeps that readable surface while making the matcher exact:
    closure is atom intersection, never substring matching.
    """
    return set(parse_disjunctive_atoms(status))


def _bound_task_discharge(cycle: dict[str, Any]):
    """Return the bound discharged receipt; reject free status properties."""
    try:
        from ztare.common.task_discharge import bind_task_discharge_receipt

        _, receipt = bind_task_discharge_receipt(
            cycle.get("task_contract"),
            cycle.get("task_discharge_receipt"),
        )
    except (TypeError, ValueError):
        return None
    return receipt if receipt.discharged else None


def _observed_play_status_quotient(cycle: dict[str, Any]) -> FiniteQuotient:
    """Quotient a play-cycle receipt into substrate-neutral status atoms."""
    observed = set()
    explicit = cycle.get("observed_status")
    if explicit:
        observed |= _status_options(explicit)
    # Terminal authority cannot be supplied by an unbound status atom.  Stored
    # reports must carry the same contract/receipt pair as the live adapter path.
    observed.discard("terminal_event")
    if _bound_task_discharge(cycle) is not None:
        observed.add("terminal_event")
    if int(cycle.get("levels_gained") or 0) > 0:
        observed.add("task_progress")
    if cycle.get("pursuit") == "goal_reached":
        observed.add("goal_candidate_reached")
    if int(cycle.get("evidence_grown_by") or 0) > 0:
        observed.add("new_evidence")
    if cycle.get("strategy_receipt"):
        observed.add("more_specific_strategy_receipt")
    return FiniteQuotient(frozenset(observed), source="arc3_play_loop_cycle")


def _observed_play_statuses(cycle: dict[str, Any]) -> set[str]:
    return set(_observed_play_status_quotient(cycle).atoms)


def _cycle_satisfies_required_gate(cycle: dict[str, Any], required: str) -> bool:
    return _observed_play_status_quotient(cycle).satisfies_any(required)


def disposition_search_control_cards_from_report(
    project: str | Path,
    report: dict[str, Any],
) -> list[dict[str, Any]]:
    """Close search-control cards when the live report satisfies their gate.

    This is the ledger counterpart of a terminal or evidence-bearing play
    receipt. It does not infer success from prose or judge score: only typed
    play-report fields can discharge the card.
    """
    root = Path(project)
    ledger = root / "workspace" / STRATEGY_LEDGER
    dispositions: list[dict[str, Any]] = []
    cards = [
        card for card in open_cards(ledger)
        if card.get("kind") == "search_control_residue_repair"
    ]
    if not cards:
        return dispositions
    cycles = [c for c in report.get("cycles") or [] if isinstance(c, dict)]
    for card in cards:
        gate = ((card.get("action_plan") or {}).get("required_next_gate") or {})
        required = gate.get("success_status") or ""
        witness = next((c for c in cycles if _cycle_satisfies_required_gate(c, required)), None)
        if witness is None:
            continue
        observed_atoms = sorted(_observed_play_statuses(witness))
        matched_atoms = sorted(set(observed_atoms) & _status_options(required))
        discharge_receipt = _bound_task_discharge(witness)
        out = set_disposition(card, DISPOSITION_ACCEPTED)
        out["receipt"] = "strategy card discharged by typed live-play report"
        out["discharge"] = {
            "schema": "ztare-strategy-card-discharge-v1",
            "required_next_gate": required,
            "observed_status": matched_atoms[0] if matched_atoms else "",
            "observed_statuses": observed_atoms,
            "cycle": witness.get("cycle"),
            "levels_gained": int(witness.get("levels_gained") or 0),
            "steps": int(witness.get("steps") or 0),
            "terminal_witness_sha": witness.get("terminal_witness_sha"),
            "task_discharge_receipt_sha256": (
                discharge_receipt.sha256 if discharge_receipt is not None else ""
            ),
            "evidence_refs": ["workspace/arc3_play_loop_report.json"],
        }
        dispositions.append(record_disposition(ledger, out))
    return dispositions


def build_terminal_closure_audit(project: str | Path) -> dict[str, Any]:
    """Bind terminal play, Strategy Office discharge, and candidate gate status.

    This is a reader receipt. It exists to keep authority levels separate:
    a terminal verifier event may close a search-control card, while candidate
    promotion still belongs to replay/holdout/judge gates.
    """
    root = Path(project)
    report_ref = "workspace/arc3_play_loop_report.json"
    ledger_ref = f"workspace/{STRATEGY_LEDGER}"
    eval_ref = "latest_eval_results.json"
    candidate_memory_ref = "workspace/candidate_memory.json"
    report = _load_json(root / report_ref)
    latest_eval = _load_json(root / eval_ref)
    ledger_rows = _ledger_rows(root / ledger_ref)
    candidate_records = _candidate_memory_records(root / candidate_memory_ref)
    latest_gate_passing = _current_gate_passing_candidate(root, candidate_records)

    cycles = [c for c in report.get("cycles") or [] if isinstance(c, dict)]
    terminal_cycles = [
        cycle
        for cycle in cycles
        if "terminal_event" in _observed_play_status_quotient(cycle).atoms
    ]
    terminal = terminal_cycles[-1] if terminal_cycles else {}
    task_discharge_receipt = _bound_task_discharge(terminal) if terminal else None
    task_discharge_sha = (
        task_discharge_receipt.sha256 if task_discharge_receipt is not None else ""
    )
    terminal_sha = str(terminal.get("terminal_witness_sha") or "")

    open_rows = [r for r in ledger_rows if str(r.get("disposition") or "open") == "open"]
    accepted_rows = [
        r for r in ledger_rows
        if str(r.get("disposition") or "") == DISPOSITION_ACCEPTED
    ]
    terminal_discharges = []
    for row in accepted_rows:
        discharge = row.get("discharge") or {}
        statuses = set(discharge.get("observed_statuses") or [])
        if discharge.get("observed_status"):
            statuses.add(str(discharge.get("observed_status")))
        if "terminal_event" in statuses:
            terminal_discharges.append(row)
    matching_discharges = [
        row for row in terminal_discharges
        if task_discharge_sha
        and str(
            (row.get("discharge") or {}).get("task_discharge_receipt_sha256") or ""
        ) == task_discharge_sha
    ]

    score_cap = str(latest_eval.get("score_cap_reason") or "")
    score = latest_eval.get("score")
    candidate_blocked = score == 0 and bool(score_cap)
    task_discharged = task_discharge_receipt is not None
    search_control_closed = bool(task_discharged and not open_rows and matching_discharges)
    autonomy = _terminal_autonomy_provenance(terminal)
    if search_control_closed and candidate_blocked:
        status = "terminal_closed_candidate_unpromoted"
    elif search_control_closed:
        status = "terminal_closed"
    elif task_discharged:
        status = "terminal_event_without_matching_strategy_discharge"
    else:
        status = "not_terminal_closed"

    receipt = {
        "schema": "ztare-worldmodel-terminal-closure-audit-v1",
        "project": str(root),
        "status": status,
        # ``level_closed`` remains a compatibility projection for existing
        # report readers.  The governing identity is task discharge.
        "task_discharged": task_discharged,
        "level_closed": task_discharged,
        "search_control_closed": search_control_closed,
        "sources": {
            "play_report": report_ref,
            "strategy_ledger": ledger_ref,
            "latest_eval": eval_ref if latest_eval else None,
            "candidate_memory": candidate_memory_ref if candidate_records else None,
        },
        "terminal_report": {
            "result": report.get("result"),
            "mode": report.get("mode"),
            "cycle": terminal.get("cycle"),
            "status": terminal.get("status"),
            "pursuit": terminal.get("pursuit"),
            "levels_gained": int(terminal.get("levels_gained") or 0),
            "steps": int(terminal.get("steps") or 0),
            "terminal_witness_sha": terminal_sha,
            "task_contract": terminal.get("task_contract"),
            "task_discharged": bool(terminal.get("task_discharged")),
            "task_discharge_receipt": terminal.get("task_discharge_receipt"),
            "task_discharge_receipt_sha256": task_discharge_sha,
        },
        "strategy_ledger": {
            "rows": len(ledger_rows),
            "open_cards": len(open_rows),
            "accepted_terminal_discharges": len(terminal_discharges),
            "matching_terminal_discharges": len(matching_discharges),
            "matched_failure_family_shas": [
                str(row.get("failure_family_sha") or "") for row in matching_discharges
            ],
        },
        "candidate_gate": {
            "score": score,
            "score_cap_reason": score_cap,
            "blocked_before_judge": score_cap in {
                "pre_judge_gate_harness_failed",
                "pre_judge_gate_harness_error",
                "strategy_card_not_discharged",
            },
            "candidate_unpromoted": candidate_blocked,
        },
        "candidate_memory": {
            "records": len(candidate_records),
            "latest_gate_passing": latest_gate_passing,
        },
        "claim_boundaries": {
            "level_closure": {
                "proven": task_discharged,
                "authority": "task_discharge_receipt" if task_discharged else "",
                "terminal_witness_sha": terminal_sha,
                "task_discharge_receipt_sha256": task_discharge_sha,
            },
            "search_control_card": {
                "proven": search_control_closed,
                "authority": "strategy_ledger_discharge",
                "matching_terminal_discharges": len(matching_discharges),
            },
            "candidate_promotion": {
                "proven": False,
                "authority": "replay_holdout_judge_gate",
                "reason": "terminal_closure_does_not_promote_candidate",
            },
            "bridge_law_support": {
                "proven": bool(latest_gate_passing),
                "authority": "candidate_memory_gate_receipt" if latest_gate_passing else "",
                "latest_gate_passing_sha": latest_gate_passing.get("sha", ""),
                "separate_from_terminal_closure": True,
            },
            "autonomous_completion": autonomy,
        },
        "claim_accounting": {
            "level_solve": assess_cegis_membrane(
                role="EVALUATION",
                terminal_event=task_discharged,
            ).to_dict(),
            "bridge_law": (
                {
                    **assess_cegis_membrane(
                        role=latest_gate_passing.get("run_role") or "EVALUATION",
                        withheld_refs=("holdout",),
                        candidate_gate_passed=bool(latest_gate_passing),
                        exposed_refs=("holdout",)
                        if latest_gate_passing.get("holdout_exposed_to_proposer")
                        else (),
                    ).to_dict(),
                    "claim_class": latest_gate_passing.get("claim_class")
                    or (
                        "clean_transfer"
                        if latest_gate_passing
                        and not latest_gate_passing.get("fresh_holdout_required")
                        else "candidate_gate_passed_visibility_unrecorded"
                    ),
                    "fresh_holdout_required": bool(
                        latest_gate_passing.get("fresh_holdout_required")
                    ),
                }
                if latest_gate_passing
                else {}
            ),
            "autonomy": autonomy,
        },
        "authority": {
            "closure_source": "task_discharge_receipt" if task_discharged else "",
            "candidate_gate_source": "latest_eval_results" if latest_eval else "",
            "candidate_promotion_used_for_closure": False,
            "authority_ladder_ok": bool(task_discharged and (search_control_closed or not ledger_rows)),
        },
    }
    receipt["closure_verification"] = validate_terminal_closure_audit(receipt)
    return receipt


def validate_terminal_closure_audit(receipt: dict[str, Any]) -> dict[str, Any]:
    """Check that a terminal close does not launder candidate promotion.

    This is a reader-side verifier for the closure receipt. It checks that the
    terminal event, Strategy Office discharge, candidate gate, and autonomy
    boundary remain separated. It does not create authority for a model patch.
    """
    errors: list[str] = []
    warnings: list[str] = []
    if receipt.get("schema") != "ztare-worldmodel-terminal-closure-audit-v1":
        errors.append("wrong_schema")

    status = str(receipt.get("status") or "")
    terminal = receipt.get("terminal_report") or {}
    strategy = receipt.get("strategy_ledger") or {}
    candidate_gate = receipt.get("candidate_gate") or {}
    claim_boundaries = receipt.get("claim_boundaries") or {}
    authority = receipt.get("authority") or {}

    level = claim_boundaries.get("level_closure") or {}
    search = claim_boundaries.get("search_control_card") or {}
    candidate = claim_boundaries.get("candidate_promotion") or {}
    bridge = claim_boundaries.get("bridge_law_support") or {}
    autonomy = claim_boundaries.get("autonomous_completion") or {}

    level_closed = bool(receipt.get("task_discharged", receipt.get("level_closed")))
    search_closed = bool(receipt.get("search_control_closed"))
    terminal_sha = str(terminal.get("terminal_witness_sha") or "")
    terminal_event = "terminal_event" in _observed_play_status_quotient(terminal).atoms

    if level_closed:
        if not terminal_event:
            errors.append("level_closed_without_terminal_event")
        discharge = _bound_task_discharge(terminal)
        if discharge is None:
            errors.append("task_discharge_receipt_not_bound_to_contract")
        elif terminal.get("task_discharge_receipt_sha256") != discharge.sha256:
            errors.append("task_discharge_receipt_identity_mismatch")
        if level.get("authority") != "task_discharge_receipt":
            errors.append("task_discharge_not_bound_to_receipt")
        if level.get("task_discharge_receipt_sha256") != terminal.get(
            "task_discharge_receipt_sha256"
        ):
            errors.append("task_discharge_claim_identity_mismatch")
        if not level.get("proven"):
            errors.append("level_closed_but_claim_boundary_unproven")

    if search_closed:
        if not search.get("proven"):
            errors.append("search_control_closed_but_claim_boundary_unproven")
        if int(strategy.get("open_cards") or 0) != 0:
            errors.append("search_control_closed_with_open_cards")
        if int(strategy.get("matching_terminal_discharges") or 0) <= 0:
            errors.append("search_control_closed_without_matching_terminal_discharge")

    if authority.get("candidate_promotion_used_for_closure") is not False:
        errors.append("candidate_promotion_used_for_terminal_closure")
    if candidate.get("proven") is not False:
        errors.append("candidate_promotion_claim_not_false")
    if candidate.get("reason") != "terminal_closure_does_not_promote_candidate":
        errors.append("candidate_promotion_boundary_missing_reason")

    if candidate_gate.get("candidate_unpromoted"):
        if not candidate_gate.get("blocked_before_judge"):
            errors.append("candidate_unpromoted_without_pre_judge_block")
    elif status == "terminal_closed_candidate_unpromoted":
        errors.append("terminal_closed_candidate_unpromoted_status_without_gate")

    if bridge.get("proven"):
        if bridge.get("authority") != "candidate_memory_gate_receipt":
            errors.append("bridge_support_not_bound_to_candidate_memory")
        if bridge.get("separate_from_terminal_closure") is not True:
            errors.append("bridge_support_not_separated_from_terminal_closure")

    if autonomy.get("proven"):
        if autonomy.get("operator_interventions") != 0:
            errors.append("autonomy_claim_without_zero_intervention_receipt")
        if autonomy.get("assistance_label") not in {"autonomous", "self_play", "unassisted"}:
            errors.append("autonomy_claim_without_unassisted_label")
        if not autonomy.get("source"):
            errors.append("autonomy_claim_without_source")
    elif level_closed:
        warnings.append(str(autonomy.get("reason") or "autonomy_not_proven"))

    if authority.get("closure_source") not in {"", "task_discharge_receipt"}:
        errors.append("closure_source_not_task_discharge_receipt")
    if authority.get("authority_ladder_ok") and not level_closed:
        errors.append("authority_ladder_ok_without_level_closure")
    if status == "terminal_closed_candidate_unpromoted":
        if not (level_closed and search_closed and candidate_gate.get("candidate_unpromoted")):
            errors.append("status_claim_not_supported_by_receipt_fields")

    return {
        "schema": "ztare-terminal-closure-verification-v1",
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def write_terminal_closure_audit(project: str | Path) -> dict[str, Any]:
    """Write the terminal closure audit into the project workspace."""
    root = Path(project)
    receipt = build_terminal_closure_audit(root)
    path = root / "workspace" / "terminal_closure_audit.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _append_terminal_closure_ledger(root, receipt)
    return receipt


def _append_terminal_closure_ledger(root: Path, receipt: dict[str, Any]) -> None:
    """Persist durable terminal closes without letting later attempts erase them."""
    if not receipt.get("task_discharged"):
        return
    if not receipt.get("closure_verification", {}).get("ok"):
        return
    terminal = receipt.get("terminal_report") or {}
    discharge_sha = str(terminal.get("task_discharge_receipt_sha256") or "")
    if not discharge_sha:
        return
    path = root / "workspace" / "terminal_closure_audits.jsonl"
    seen: set[str] = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            if isinstance(row, dict):
                prior = (
                    (row.get("terminal_report") or {}).get(
                        "task_discharge_receipt_sha256"
                    )
                    or ""
                )
                if prior:
                    seen.add(str(prior))
    if discharge_sha in seen:
        return
    row = dict(receipt)
    row["ledger_schema"] = "ztare-terminal-closure-audit-ledger-v1"
    row["ledger_note"] = (
        "durable terminal-close receipt; latest terminal_closure_audit.json may "
        "describe a later non-closing attempt"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--closure-audit", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    if args.closure_audit:
        receipt = write_terminal_closure_audit(args.project)
        print(json.dumps(receipt, indent=2, sort_keys=True))
        if args.check and not receipt.get("closure_verification", {}).get("ok"):
            return 1
        return 0
    written = write_search_control_repair_card(args.project)
    print(json.dumps({
        "schema": "ztare-search-control-repair-card-result-v1",
        "project": args.project,
        "cards_written": len(written),
        "written": written,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
