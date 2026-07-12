from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ztare.common.file_io import append_jsonl
from ztare.common.kernel_admissibility import validate_kernel_change_admissibility


SCHEMA = "ztare-harness-weakness-receipt-v1"
LEDGER = "harness_weakness_receipts.jsonl"
LATEST = "latest_harness_weakness.json"
CLASSIFIER_LEDGER = "weakness_classifiers.jsonl"

_PREDICATE_RELATIONS = {"eq", "ne", "in", "not_in", "contains", "startswith", "exists"}


def build_harness_weakness_receipt(
    *,
    project_dir: str | Path,
    source_ref: str,
    regression_receipt: dict[str, Any],
    counterexample_trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify a failed harness interaction without changing gate authority."""
    classification = classify_harness_weakness(
        project_dir=project_dir,
        regression_receipt=regression_receipt,
        counterexample_trace=counterexample_trace,
    )
    weakness_class = classification["class_name"]
    route = classification["route"]
    recommended_capability_id = classification["recommended_capability_id"]
    relation = str(regression_receipt.get("candidate_relation") or "")
    comparison = regression_receipt.get("quotient_comparison")
    comparison = comparison if isinstance(comparison, dict) else {}
    best_ref = str(regression_receipt.get("best_prior_submission") or "")
    quotient_relation = str(comparison.get("relation") or "")
    candidate_exact = _maybe_int(regression_receipt.get("candidate_exact_rows"))
    best_exact = _maybe_int(regression_receipt.get("best_prior_exact_rows"))

    trace = counterexample_trace if isinstance(counterexample_trace, dict) else {}
    workbench_task = _workbench_task(
        weakness_class=weakness_class,
        source_ref=source_ref,
        route=route,
        recommended_capability_id=recommended_capability_id,
        trace=trace,
    )
    return {
        "schema": SCHEMA,
        "project": str(Path(project_dir)),
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_ref": source_ref,
        "weakness_class": weakness_class,
        "relation": relation,
        "quotient_relation": quotient_relation,
        "candidate_sha": regression_receipt.get("candidate_sha"),
        "best_prior_sha": regression_receipt.get("best_prior_sha"),
        "best_prior_submission": best_ref,
        "deltas": {
            "exact_rows": regression_receipt.get("exact_rows_delta"),
            "wrong_cells": regression_receipt.get("wrong_cells_delta"),
            "holdout_depth": regression_receipt.get("holdout_depth_delta"),
            "gate_score": regression_receipt.get("gate_score_delta"),
        },
        "counterexample": {
            "first_mismatch": str(trace.get("first_mismatch") or regression_receipt.get("first_mismatch") or "")[:300],
            "residual_table": (trace.get("residual_table") or [])[:48],
            "candidate_top_quotient": comparison.get("candidate_top_quotient") or {},
            "best_prior_top_quotient": comparison.get("best_prior_top_quotient") or {},
        },
        "recommended_route": route,
        "recommended_capability_id": recommended_capability_id,
        "workbench_task": workbench_task,
        "authority": (
            "diagnostic only; cannot promote candidates, close Strategy cards, "
            "or override replay/holdout/terminal gates"
        ),
    }


def classify_harness_weakness(
    *,
    project_dir: str | Path,
    regression_receipt: dict[str, Any],
    counterexample_trace: dict[str, Any] | None = None,
) -> dict[str, str]:
    context = _weakness_context(project_dir=project_dir, regression_receipt=regression_receipt, counterexample_trace=counterexample_trace)
    for entry in _weakness_registry(project_dir):
        if entry["predicate_fn"](context):
            return {
                "class_name": entry["class_name"],
                "route": entry["route"],
                "recommended_capability_id": entry["recommended_capability_id"],
                "provenance": entry["provenance"],
            }
    return {
        "class_name": "unclassifiable_carrier_or_gate_failure",
        "route": "repair_carrier_contract_or_request_workbench_capability",
        "recommended_capability_id": "",
        "provenance": "seed",
    }


def append_weakness_classifier_row(
    *,
    project_dir: str | Path,
    class_name: str,
    predicate_spec: dict[str, Any],
    route: str,
    admissibility_receipt: dict[str, Any],
    provenance: str = "office",
) -> dict[str, Any]:
    project = Path(project_dir)
    row = {
        "class_name": str(class_name),
        "predicate_spec": dict(predicate_spec),
        "route": str(route),
        "provenance": str(provenance),
        "admissibility": dict(admissibility_receipt),
    }
    if not _validate_weakness_classifier_row(row):
        raise ValueError("invalid weakness_classifier row")
    append_jsonl(project / "workspace" / CLASSIFIER_LEDGER, row)
    return row


def write_harness_weakness_receipt(
    *,
    project_dir: str | Path,
    source_ref: str,
    regression_receipt: dict[str, Any],
    counterexample_trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    project = Path(project_dir)
    receipt = build_harness_weakness_receipt(
        project_dir=project,
        source_ref=source_ref,
        regression_receipt=regression_receipt,
        counterexample_trace=counterexample_trace,
    )
    workspace = project / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / LATEST).write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    append_jsonl(workspace / LEDGER, receipt)
    return receipt


def _maybe_int(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except Exception:
        return None


def _visible_replay_is_exact(trace: dict[str, Any] | None) -> bool:
    if not isinstance(trace, dict):
        return False
    wrong = _maybe_int(trace.get("wrong_cell_count"))
    checked = _maybe_int(trace.get("checked_rows"))
    exact = _maybe_int(trace.get("exact_rows"))
    if wrong is None or wrong != 0:
        return False
    return bool(checked is not None and exact is not None and checked == exact)


def _has_boundary_gate_failure(trace: dict[str, Any] | None) -> bool:
    if not isinstance(trace, dict):
        return False
    failed = trace.get("failed_gates")
    labels = [str(row).lower() for row in failed] if isinstance(failed, list) else []
    return any("holdout" in label or "transfer" in label or "terminal" in label for label in labels)


def _counterexample_context_probe_available(comparison: dict[str, Any]) -> bool:
    if comparison.get("relation") not in {
        "changed_support",
        "same_support_changed_pairs",
        "same_quotient_worse_frequency",
    }:
        return False
    cand = comparison.get("candidate_top_quotient")
    best = comparison.get("best_prior_top_quotient")
    if not isinstance(cand, dict) or not isinstance(best, dict):
        return False
    bbox = cand.get("bbox") if isinstance(cand.get("bbox"), list) else []
    return (
        _maybe_int(cand.get("first_row")) is not None
        and _maybe_int(best.get("first_row")) is not None
        and len(bbox) == 4
    )


def _workbench_task(
    *,
    weakness_class: str,
    source_ref: str,
    route: str,
    recommended_capability_id: str,
    trace: dict[str, Any],
) -> dict[str, Any]:
    artifact_refs = [source_ref] if source_ref else []
    if source_ref.endswith(":candidate_regression_receipt"):
        artifact_refs = [source_ref.split(":", 1)[0]]
    seed = json.dumps(
        {
            "weakness_class": weakness_class,
            "source_ref": source_ref,
            "route": route,
            "recommended_capability_id": recommended_capability_id,
            "first_mismatch": trace.get("first_mismatch"),
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    capabilities = []
    if recommended_capability_id:
        capabilities.append(recommended_capability_id)
    if (
        weakness_class in {"candidate_quality_failure", "unclassifiable_carrier_or_gate_failure"}
        and "run_visible_json_probe" not in capabilities
    ):
        capabilities.append("run_visible_json_probe")
    if (
        weakness_class == "visible_counterexample_trace_unfactored"
        and "run_visible_json_probe" not in capabilities
    ):
        capabilities.append("run_visible_json_probe")
    if weakness_class == "boundary_evidence_missing":
        objective = (
            "Visible replay has no remaining counterexample; request or return "
            "the registered substrate boundary gate receipt, then hand the "
            "result to the conductor/Strategy Office. Do not propose another "
            "visible-residual delta unless a new visible quotient appears."
        )
    elif weakness_class == "declared_gate_obligation_open":
        objective = (
            "A declared Strategy gate is the next unresolved boundary. Request "
            "or return that registered gate receipt, then hand the result to "
            "the conductor/Strategy Office. Do not propose another visible "
            "residual delta unless a new visible quotient appears."
        )
    else:
        objective = (
            "Produce a receipt-backed observation that separates the failed "
            "counterexample quotient, then propose a candidate delta; if current "
            "capabilities cannot expose the needed distinction, emit "
            "LOWERABILITY_BLOCKED with the missing sensor/morphism named."
        )
    return {
        "schema": "ztare-leaf-workbench-task-v1",
        "task_id": hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16],
        "failure_class": weakness_class,
        "source_ref": source_ref,
        "visible_artifact_refs": artifact_refs,
        "admissible_capability_ids": capabilities,
        "objective": objective,
        "first_counterexample": str(trace.get("first_mismatch") or "")[:300],
        "authority": "diagnostic task only; receipts inform mutations but do not override gates",
    }


def _weakness_context(
    *,
    project_dir: str | Path,
    regression_receipt: dict[str, Any],
    counterexample_trace: dict[str, Any] | None,
) -> dict[str, Any]:
    comparison = regression_receipt.get("quotient_comparison")
    comparison = comparison if isinstance(comparison, dict) else {}
    trace = counterexample_trace if isinstance(counterexample_trace, dict) else {}
    return {
        "project_dir": str(project_dir),
        "relation": str(regression_receipt.get("candidate_relation") or ""),
        "quotient_relation": str(comparison.get("relation") or ""),
        "geometry_kind": str(regression_receipt.get("geometry_kind") or ""),
        "best_prior_submission": str(regression_receipt.get("best_prior_submission") or ""),
        "candidate_exact_rows": _maybe_int(regression_receipt.get("candidate_exact_rows")),
        "best_prior_exact_rows": _maybe_int(regression_receipt.get("best_prior_exact_rows")),
        "first_mismatch": str(trace.get("first_mismatch") or regression_receipt.get("first_mismatch") or ""),
        "visible_replay_exact": _visible_replay_is_exact(trace),
        "boundary_gate_failure": _has_boundary_gate_failure(trace),
        "counterexample_context_probe_available": _counterexample_context_probe_available(comparison),
        "declared_strategy_gate_available": _declared_strategy_gate_available(Path(project_dir)),
        "holdout_witness_missing": _holdout_witness_missing(trace, regression_receipt),
    }


def _holdout_witness_missing(trace: dict[str, Any], receipt: dict[str, Any]) -> bool:
    """A failed holdout gate whose receipt carries no counterexample witness is
    unfalsifiable — a gate-harness defect, not evidence about the candidate."""
    failed = trace.get("failed_gates")
    labels = " ".join(str(x).lower() for x in failed) if isinstance(failed, list) else ""
    if "holdout" not in labels:
        return False
    witness = trace.get("holdout_witness") or receipt.get("holdout_witness")
    return not (isinstance(witness, dict) and witness)


def _weakness_registry(project_dir: str | Path) -> list[dict[str, Any]]:
    registry = [
        {
            "class_name": "boundary_evidence_missing",
            "predicate_fn": lambda ctx: ctx["relation"] == "hard_gate_failure"
            and ctx["visible_replay_exact"]
            and ctx["boundary_gate_failure"],
            "route": "run_or_return_substrate_boundary_gate",
            "recommended_capability_id": "run_strategy_required_gate",
            "provenance": "seed",
        },
        {
            "class_name": "unquotiented_counterexample_chart_missing",
            "predicate_fn": lambda ctx: ctx["relation"] == "hard_gate_failure"
            and bool(ctx["first_mismatch"])
            and ctx["counterexample_context_probe_available"],
            "route": "request_counterexample_context_then_refine_abstraction",
            "recommended_capability_id": "inspect_worldmodel_counterexample_context",
            "provenance": "seed",
        },
        {
            "class_name": "visible_counterexample_trace_unfactored",
            "predicate_fn": lambda ctx: ctx["relation"] == "hard_gate_failure" and bool(ctx["first_mismatch"]),
            "route": "inspect_visible_regression_trace_then_refine_or_propose_capability",
            "recommended_capability_id": "mine_worldmodel_separating_features",
            "provenance": "seed",
        },
        {
            "class_name": "declared_gate_obligation_open",
            "predicate_fn": lambda ctx: ctx["relation"] == "hard_gate_failure"
            and ctx["quotient_relation"] == "hard_gate_failure_without_visible_quotient"
            and ctx["declared_strategy_gate_available"],
            "route": "run_declared_strategy_gate_before_new_visible_probe",
            "recommended_capability_id": "run_strategy_required_gate",
            "provenance": "seed",
        },
        {
            "class_name": "mutable_prior_identity_leak",
            "predicate_fn": lambda ctx: bool(ctx["best_prior_submission"]) and not str(ctx["best_prior_submission"]).startswith("workspace/submissions/"),
            "route": "select_immutable_content_addressed_prior",
            "recommended_capability_id": "",
            "provenance": "seed",
        },
        {
            "class_name": "local_receipt_overgeneralized",
            "predicate_fn": lambda ctx: ctx["quotient_relation"] == "changed_support"
            and ctx["candidate_exact_rows"] is not None
            and ctx["best_prior_exact_rows"] is not None
            and ctx["candidate_exact_rows"] < ctx["best_prior_exact_rows"],
            "route": "request_counterexample_context_then_factor_delta_by_residual_quotient",
            "recommended_capability_id": "inspect_worldmodel_counterexample_context",
            "provenance": "seed",
        },
        {
            "class_name": "quotient_context_missing",
            "predicate_fn": lambda ctx: ctx["quotient_relation"] in {"same_support_changed_pairs", "same_quotient_worse_frequency"}
            and ctx["candidate_exact_rows"] is not None
            and ctx["best_prior_exact_rows"] is not None
            and ctx["candidate_exact_rows"] < ctx["best_prior_exact_rows"],
            "route": "request_counterexample_context_then_separate_same_support_cases",
            "recommended_capability_id": "inspect_worldmodel_counterexample_context",
            "provenance": "seed",
        },
        {
            "class_name": "plateau_without_information_gain",
            "predicate_fn": lambda ctx: ctx["relation"] == "no_strict_improvement",
            "route": "request_discriminator_or_capability_proposal",
            "recommended_capability_id": "",
            "provenance": "seed",
        },
        {
            "class_name": "failing_gate_without_witness",
            "predicate_fn": lambda ctx: ctx["holdout_witness_missing"],
            "route": "repair_gate_harness_to_emit_counterexample_witness",
            "recommended_capability_id": "",
            "provenance": "seed",
        },
        {
            "class_name": "unclassifiable_carrier_or_gate_failure",
            "predicate_fn": lambda ctx: True,
            "route": "repair_carrier_contract_or_request_workbench_capability",
            "recommended_capability_id": "",
            "provenance": "seed",
        },
    ]
    terminal = registry.pop()
    registry.extend(_load_ledger_weakness_classifiers(project_dir))
    registry.append(terminal)
    return registry


def _load_ledger_weakness_classifiers(project_dir: str | Path) -> list[dict[str, Any]]:
    path = Path(project_dir) / "workspace" / CLASSIFIER_LEDGER
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if not isinstance(row, dict):
            continue
        admissibility = row.get("admissibility")
        if not validate_kernel_change_admissibility(admissibility).passed:
            continue
        spec = row.get("predicate_spec")
        if not _validate_predicate_spec(spec):
            continue
        predicate_fn = _predicate_from_spec(spec)
        if predicate_fn is None:
            continue
        rows.append({
            "class_name": str(row.get("class_name") or ""),
            "predicate_fn": predicate_fn,
            "route": str(row.get("route") or ""),
            "recommended_capability_id": str(row.get("recommended_capability_id") or ""),
            "provenance": "office",
        })
    return rows


def _validate_weakness_classifier_row(row: dict[str, Any]) -> bool:
    return (
        isinstance(row, dict)
        and isinstance(row.get("class_name"), str)
        and isinstance(row.get("route"), str)
        and isinstance(row.get("predicate_spec"), dict)
        and _validate_predicate_spec(row.get("predicate_spec"))
        and validate_kernel_change_admissibility(row.get("admissibility")).passed
    )


def _validate_predicate_spec(spec: Any) -> bool:
    if not isinstance(spec, dict):
        return False
    field = spec.get("field")
    relation = str(spec.get("relation") or "")
    if not isinstance(field, str) or not field.strip():
        return False
    if relation not in _PREDICATE_RELATIONS:
        return False
    return True


def _predicate_from_spec(spec: Any):
    if not _validate_predicate_spec(spec):
        return None
    field = str(spec["field"])
    relation = str(spec["relation"])
    value = spec.get("value")

    def _fn(ctx: dict[str, Any]) -> bool:
        actual = ctx.get(field)
        if relation == "exists":
            return actual is not None
        if relation == "eq":
            return actual == value
        if relation == "ne":
            return actual != value
        if relation == "in":
            return actual in value if isinstance(value, (list, tuple, set, frozenset, dict)) else False
        if relation == "not_in":
            return actual not in value if isinstance(value, (list, tuple, set, frozenset, dict)) else False
        if relation == "contains":
            return str(value) in str(actual)
        if relation == "startswith":
            return str(actual).startswith(str(value))
        return False

    return _fn


def _declared_strategy_gate_available(project: Path) -> bool:
    path = project / "workspace" / "strategy_experiments.jsonl"
    if not path.exists():
        return False
    try:
        from ztare.common.operator_proposal_contract import open_cards

        cards = open_cards(path)
    except Exception:
        return False
    for card in cards:
        plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
        gate = plan.get("required_next_gate") if isinstance(plan.get("required_next_gate"), dict) else {}
        if str(gate.get("command") or "").strip():
            return True
    return False
