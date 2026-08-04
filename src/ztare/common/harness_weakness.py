from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ztare.common.file_io import append_jsonl
from ztare.common.kernel_admissibility import validate_kernel_change_admissibility
from ztare.common.candidate_memory import admissible_candidate_memory_records
from ztare.common.patch_base_identity import repair_frontier_fields
from ztare.common.artifact_refs import resolve_project_artifact_ref
from ztare.common.observation_chart import capture_project_evidence_epoch


SCHEMA = "ztare-harness-weakness-receipt-v1"
LEDGER = "harness_weakness_receipts.jsonl"
LATEST = "latest_harness_weakness.json"
CLASSIFIER_LEDGER = "weakness_classifiers.jsonl"

_PREDICATE_RELATIONS = {"eq", "ne", "in", "not_in", "contains", "startswith", "exists"}

_ROUTE_CAPABILITY_CHAINS: dict[str, tuple[str, ...]] = {
    "request_counterexample_context_then_refine_abstraction": (
        "inspect_worldmodel_counterexample_context",
        "mine_worldmodel_lowerable_selectors",
    ),
    "request_counterexample_context_then_factor_delta_by_residual_quotient": (
        "inspect_worldmodel_counterexample_context",
        "mine_worldmodel_lowerable_selectors",
    ),
    "request_counterexample_context_then_separate_same_support_cases": (
        "inspect_worldmodel_counterexample_context",
        "mine_worldmodel_lowerable_selectors",
    ),
    "inspect_visible_regression_trace_then_refine_or_propose_capability": (
        "mine_worldmodel_lowerable_selectors",
    ),
}


def build_harness_weakness_receipt(
    *,
    project_dir: str | Path,
    source_ref: str,
    regression_receipt: dict[str, Any],
    counterexample_trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify a failed harness interaction without changing gate authority."""
    trace = counterexample_trace if isinstance(counterexample_trace, dict) else {}
    regression_receipt = _normalized_candidate_outcome(
        regression_receipt,
        trace,
    )
    classification = classify_harness_weakness(
        project_dir=project_dir,
        regression_receipt=regression_receipt,
        counterexample_trace=trace,
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

    frontier_source_ref, frontier_trace, frontier_role = _active_frontier(
        project_dir=project_dir,
        regression_receipt=regression_receipt,
        candidate_trace=trace,
        default_source_ref=source_ref,
    )
    frontier_sha256 = _frontier_content_sha256(
        project_dir=project_dir,
        source_ref=frontier_source_ref,
        declared_sha=(
            regression_receipt.get("best_prior_sha")
            if frontier_role == "best_admissible_prior"
            else regression_receipt.get("candidate_sha")
        ),
    )
    evidence_epoch_sha256 = capture_project_evidence_epoch(project_dir).epoch_sha256
    # A rejected sibling does not create a repair obligation for a surviving
    # frontier whose own gate trace is complete.  Keep the sibling failure in
    # the weakness ledger, but do not coerce it into a task owned by different
    # carrier bytes.
    frontier_closed = (
        frontier_role == "best_admissible_prior"
        and _visible_replay_is_exact(frontier_trace)
        and not tuple(frontier_trace.get("failed_gates") or ())
    )
    workbench_task = (
        {}
        if frontier_closed
        else _workbench_task(
            weakness_class=weakness_class,
            source_ref=frontier_source_ref,
            source_sha256=frontier_sha256,
            evidence_epoch_sha256=evidence_epoch_sha256,
            route=route,
            recommended_capability_id=recommended_capability_id,
            trace=frontier_trace,
        )
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
        "active_frontier": {
            "role": frontier_role,
            "source_ref": frontier_source_ref,
            "candidate_sha": (
                frontier_sha256
            ),
            "first_mismatch": str(frontier_trace.get("first_mismatch") or "")[:300],
            "evidence_ref": str(frontier_trace.get("evidence_ref") or ""),
        },
        "recommended_route": route,
        "recommended_capability_id": recommended_capability_id,
        "workbench_task": workbench_task,
        "authority": (
            "diagnostic only; cannot promote candidates, close Strategy cards, "
            "or override replay/holdout/terminal gates"
        ),
    }


def _frontier_content_sha256(
    *,
    project_dir: str | Path,
    source_ref: str,
    declared_sha: object,
) -> str:
    """Return the full identity of the immutable frontier artifact when visible.

    Candidate-memory ``sha`` historically served as a short display label.  A
    task scope is an authority boundary and must not inherit that presentation
    loss.  Resolve the named artifact once at the producer and carry its full
    digest through the task.  A conflicting declaration remains visible so
    the downstream identity check fails closed instead of blessing other
    bytes.
    """

    declared = str(declared_sha or "").strip().lower()
    try:
        path = resolve_project_artifact_ref(project_dir, source_ref)
        if path is None or not path.is_file():
            return declared
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
    except (OSError, ValueError):
        return declared
    if declared and not (
        observed.startswith(declared) or declared.startswith(observed)
    ):
        return declared
    return observed


def _active_frontier(
    *,
    project_dir: str | Path,
    regression_receipt: dict[str, Any],
    candidate_trace: dict[str, Any],
    default_source_ref: str,
) -> tuple[str, dict[str, Any], str]:
    """Select the surviving scientific frontier after a candidate comparison.

    A regressed proposal is an eliminated hypothesis.  Its counterexample is
    useful diagnostic evidence, but asking the next leaf to repair that
    proposal replaces the surviving carrier identity with a failed property.
    """
    frontier = repair_frontier_fields(regression_receipt)
    frontier_ref = frontier["source_ref"]
    frontier_sha = frontier["sha256"]
    frontier_role = frontier["role"]
    if frontier_role == "evaluated_candidate":
        candidate_sha = frontier_sha or str(candidate_trace.get("gated_sha256") or "").strip()
        candidate_ref = frontier_ref or str(candidate_trace.get("gated_file") or "").strip()
        record = _candidate_memory_frontier(
            project_dir,
            target_sha=candidate_sha,
            target_ref=candidate_ref,
        )
        if record is not None:
            stored_trace = record.get("counterexample_trace")
            return (
                str(record.get("submission") or candidate_ref or default_source_ref),
                stored_trace if isinstance(stored_trace, dict) else candidate_trace,
                "evaluated_candidate",
            )
        return (
            candidate_ref
            or default_source_ref,
            candidate_trace,
            "evaluated_candidate",
        )

    best = _candidate_memory_frontier(
        project_dir,
        target_sha=frontier_sha,
        target_ref=frontier_ref,
    )
    if best is not None:
        stored_trace = best.get("counterexample_trace")
        if isinstance(stored_trace, dict):
            return (
                str(best.get("submission") or frontier_ref),
                stored_trace,
                "best_admissible_prior",
            )

    comparison = regression_receipt.get("quotient_comparison")
    comparison = comparison if isinstance(comparison, dict) else {}
    quotient = comparison.get("best_prior_top_quotient")
    quotient = quotient if isinstance(quotient, dict) else {}
    synthetic = {
        "schema": "ztare-counterexample-trace-v1",
        "quotient": "best_prior_top_residual",
        "first_mismatch": (
            f"best prior residual at row={quotient.get('first_row')} "
            f"t={quotient.get('t')} action={quotient.get('action')} "
            f"bbox={quotient.get('bbox')}"
            if quotient
            else "best prior counterexample trace unavailable"
        ),
        "first_mismatch_signature": quotient,
    }
    return frontier_ref, synthetic, "best_admissible_prior"


def _candidate_memory_frontier(
    project_dir: str | Path,
    *,
    target_sha: str,
    target_ref: str,
) -> dict[str, Any] | None:
    matches = []
    for record in admissible_candidate_memory_records(project_dir):
        record_ref = str(record.get("submission") or "").strip()
        record_sha = str(record.get("sha") or "").strip()
        same_sha = bool(target_sha) and record_sha == target_sha
        if record_ref == target_ref or same_sha:
            matches.append(record)
    if not matches:
        return None
    return max(
        matches,
        key=lambda row: (
            1
            if str(row.get("submission") or "").startswith("workspace/submissions/")
            else 0,
            int(row.get("visible_checked_rows") or 0),
            str(row.get("observed_at_utc") or ""),
        ),
    )


def classify_harness_weakness(
    *,
    project_dir: str | Path,
    regression_receipt: dict[str, Any],
    counterexample_trace: dict[str, Any] | None = None,
) -> dict[str, str]:
    trace = counterexample_trace if isinstance(counterexample_trace, dict) else {}
    normalized = _normalized_candidate_outcome(regression_receipt, trace)
    context = _weakness_context(
        project_dir=project_dir,
        regression_receipt=normalized,
        counterexample_trace=trace,
    )
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
    return _persist_harness_weakness_receipt(workspace, receipt)


def write_lowerability_harness_weakness_receipt(
    *,
    project_dir: str | Path,
    blocker_payload: dict[str, Any],
    source_ref: str = "control_receipt:LOWERABILITY_BLOCKED",
) -> dict[str, Any] | None:
    """Persist a registered-capability failure carried by a blocker receipt.

    A scientific obstruction and a failed observation instrument have different
    owners.  Only the latter enters the apparatus-repair route here; ordinary
    missing-witness blockers remain scientific evidence gaps.
    """
    failures = [
        {
            "capability_id": str(row.get("capability_id") or "").strip(),
            "status": str(row.get("status") or "fail").strip(),
            "error": str(
                row.get("error")
                or row.get("visible_command_error")
                or row.get("summary")
                or row.get("output_summary")
                or ""
            ).strip(),
            "receipt_ref": str(row.get("receipt_ref") or row.get("output_ref") or "").strip(),
        }
        for row in (blocker_payload.get("visible_command_errors") or [])
        if isinstance(row, dict)
        and str(row.get("capability_id") or "").strip()
        and str(
            row.get("error")
            or row.get("visible_command_error")
            or row.get("summary")
            or row.get("output_summary")
            or ""
        ).strip()
    ]
    if not failures:
        return None
    identity_payload = [
        {
            "capability_id": row["capability_id"],
            "error": row["error"],
        }
        for row in failures
    ]
    failure_identity = hashlib.sha256(
        json.dumps(identity_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    evidence_epoch_sha256 = capture_project_evidence_epoch(project_dir).epoch_sha256
    receipt = {
        "schema": SCHEMA,
        "project": str(Path(project_dir)),
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_ref": source_ref,
        "weakness_class": "registered_capability_delivery_failure",
        "failure_identity_sha256": failure_identity,
        "relation": "lowerability_blocked",
        "quotient_relation": "instrument_failed_before_consequence",
        "registered_capability_failures": failures,
        "obstruction": str(blocker_payload.get("obstruction") or "").strip(),
        "missing_witness_or_sensor": str(
            blocker_payload.get("missing_witness_or_sensor") or ""
        ).strip(),
        "recommended_route": "repair_registered_capability_then_replay_receipt",
        "recommended_capability_id": failures[0]["capability_id"],
        "workbench_task": {
            "schema": "ztare-leaf-workbench-task-v1",
            "task_id": failure_identity,
            "evidence_epoch_sha256": evidence_epoch_sha256,
            "failure_class": "registered_capability_delivery_failure",
            "source_ref": source_ref,
            "visible_artifact_refs": [
                row["receipt_ref"] for row in failures if row["receipt_ref"]
            ],
            "admissible_capability_ids": [],
            "objective": (
                "A registered observation capability failed before producing its "
                "consequence. Preserve the scientific residual and route the "
                "instrument failure to its apparatus owner; replay the same "
                "receipt-producing action after repair."
            ),
            "first_counterexample": "",
            "authority": "apparatus repair input; cannot amend candidate semantics",
        },
        "authority": (
            "apparatus repair input only; cannot promote candidates or alter "
            "the scientific residual"
        ),
    }
    workspace = Path(project_dir) / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    return _persist_harness_weakness_receipt(workspace, receipt)


def _persist_harness_weakness_receipt(
    workspace: Path,
    receipt: dict[str, Any],
) -> dict[str, Any]:
    """Keep one refreshable ledger row per task in an evidence epoch."""
    task = receipt.get("workbench_task")
    task = task if isinstance(task, dict) else {}
    key = (
        str(task.get("task_id") or receipt.get("failure_identity_sha256") or ""),
        str(task.get("evidence_epoch_sha256") or ""),
    )
    now = str(receipt.get("created_at_utc") or "")
    matches: list[dict[str, Any]] = []
    retained: list[str] = []
    ledger = workspace / LEDGER
    if all(key) and ledger.exists():
        for line in ledger.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                row = json.loads(line)
            except Exception:
                retained.append(line)
                continue
            row_task = row.get("workbench_task") if isinstance(row, dict) else None
            row_task = row_task if isinstance(row_task, dict) else {}
            row_key = (
                str(
                    row_task.get("task_id")
                    or (row.get("failure_identity_sha256") if isinstance(row, dict) else "")
                    or ""
                ),
                str(row_task.get("evidence_epoch_sha256") or ""),
            )
            if row_key == key and isinstance(row, dict):
                matches.append(row)
            else:
                retained.append(line)

    receipt["occurrence_count"] = 1 + sum(
        max(1, _maybe_int(row.get("occurrence_count")) or 1) for row in matches
    )
    receipt["first_seen_at_utc"] = min(
        [
            str(row.get("first_seen_at_utc") or row.get("created_at_utc") or now)
            for row in matches
        ]
        + [now]
    )
    receipt["last_seen_at_utc"] = now
    if matches:
        retained.append(json.dumps(receipt, ensure_ascii=True))
        replacement = ledger.with_suffix(ledger.suffix + ".tmp")
        replacement.write_text("\n".join(retained) + "\n", encoding="utf-8")
        replacement.replace(ledger)
    else:
        append_jsonl(ledger, receipt)
    (workspace / LATEST).write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return receipt


def _maybe_int(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except Exception:
        return None


def _normalized_candidate_outcome(
    receipt: dict[str, Any],
    trace: dict[str, Any],
) -> dict[str, Any]:
    """Preserve candidate identity when a gate block has no prior comparison.

    The pre-judge boundary always knows the evaluated carrier and its typed
    counterexample, while a regression comparison is optional.  Treating the
    optional comparison as the carrier of gate identity erased the SHA and
    downgraded a specific observation into an unclassifiable task.
    """

    normalized = dict(receipt or {})
    candidate_sha = str(
        normalized.get("candidate_sha")
        or normalized.get("gated_sha256")
        or trace.get("gated_sha256")
        or ""
    ).strip()
    candidate_submission = str(
        normalized.get("candidate_submission")
        or normalized.get("gated_file")
        or trace.get("gated_file")
        or ""
    ).strip()
    if candidate_sha:
        normalized["candidate_sha"] = candidate_sha
    if candidate_submission:
        normalized["candidate_submission"] = candidate_submission
    relation = str(normalized.get("candidate_relation") or "").strip()
    failed = trace.get("failed_gates")
    has_gate_witness = bool(
        (isinstance(failed, list) and failed)
        or str(trace.get("first_mismatch") or "").strip()
    )
    if not relation and has_gate_witness:
        normalized["candidate_relation"] = "hard_gate_failure"
    return normalized


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


def _counterexample_context_probe_available(
    comparison: dict[str, Any],
    *,
    trace: dict[str, Any],
    candidate_identity: str,
) -> bool:
    if comparison.get("relation") in {
        "changed_support",
        "same_support_changed_pairs",
        "same_quotient_worse_frequency",
    }:
        cand = comparison.get("candidate_top_quotient")
        best = comparison.get("best_prior_top_quotient")
        if isinstance(cand, dict) and isinstance(best, dict):
            bbox = cand.get("bbox") if isinstance(cand.get("bbox"), list) else []
            if (
                _maybe_int(cand.get("first_row")) is not None
                and _maybe_int(best.get("first_row")) is not None
                and len(bbox) == 4
            ):
                return True
    if not candidate_identity:
        return False
    if not str(trace.get("evidence_ref") or "").strip():
        return False
    classes = trace.get("mismatch_classes")
    top = classes[0] if isinstance(classes, list) and classes else {}
    top = top if isinstance(top, dict) else {}
    signature = top.get("signature") if isinstance(top.get("signature"), dict) else {}
    bbox = signature.get("bbox") if isinstance(signature.get("bbox"), list) else []
    return _maybe_int(top.get("first_row")) is not None and len(bbox) == 4


def _workbench_task(
    *,
    weakness_class: str,
    source_ref: str,
    source_sha256: str,
    evidence_epoch_sha256: str,
    route: str,
    recommended_capability_id: str,
    trace: dict[str, Any],
) -> dict[str, Any]:
    artifact_refs = [source_ref] if source_ref else []
    if source_ref.endswith(":candidate_regression_receipt"):
        artifact_refs = [source_ref.split(":", 1)[0]]
    evidence_ref = str(trace.get("evidence_ref") or "").strip()
    if evidence_ref and evidence_ref not in artifact_refs:
        artifact_refs.append(evidence_ref)
    observation_sha256 = str(trace.get("observation_sha256") or "").strip()
    if not observation_sha256:
        observation_sha256 = hashlib.sha256(
            json.dumps(
                {
                    "gated_sha256": trace.get("gated_sha256"),
                    "failed_gates": trace.get("failed_gates"),
                    "first_mismatch": trace.get("first_mismatch"),
                    "evidence_ref": trace.get("evidence_ref"),
                    "mismatch_classes": trace.get("mismatch_classes"),
                },
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            ).encode("utf-8")
        ).hexdigest()
    # The obligation identity binds the failed evidence, carrier, and epoch.
    # The weakness label and operation ordering are replaceable routing
    # properties.  Neither may split one carrier/evidence/observation
    # obligation; route and capability changes belong to ``program_id`` below.
    seed = json.dumps(
        {
            "schema": "ztare-leaf-workbench-task-v1",
            "adapter_id": "worldmodel",
            "job": "resolve_falsified_carrier_observation",
            "source_sha256": source_sha256,
            "evidence_epoch_sha256": evidence_epoch_sha256,
            "observation_sha256": observation_sha256,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    capabilities = list(
        dict.fromkeys(
            [
                recommended_capability_id,
                *_ROUTE_CAPABILITY_CHAINS.get(route, ()),
            ]
        )
    )
    capabilities = [capability_id for capability_id in capabilities if capability_id]
    morphism_sequence = [
        capability_id
        for capability_id in _ROUTE_CAPABILITY_CHAINS.get(route, ())
        if capability_id
    ]
    task_id = hashlib.sha256(seed.encode("utf-8")).hexdigest()
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
    program_id = hashlib.sha256(
        json.dumps(
            {
                "task_id": task_id,
                "route": route,
                "admissible_capability_ids": capabilities,
                "morphism_sequence": morphism_sequence,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
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
    task = {
        "schema": "ztare-leaf-workbench-task-v1",
        "task_id": task_id,
        "obligation_id": task_id,
        "program_id": program_id,
        "failure_class": weakness_class,
        "source_ref": source_ref,
        "source_sha256": source_sha256,
        "evidence_epoch_sha256": evidence_epoch_sha256,
        "observation_sha256": observation_sha256,
        "visible_artifact_refs": artifact_refs,
        "admissible_capability_ids": capabilities,
        "objective": objective,
        "first_counterexample": str(trace.get("first_mismatch") or "")[:300],
        "authority": "diagnostic task only; receipts inform mutations but do not override gates",
    }
    if morphism_sequence:
        task["morphism_sequence"] = morphism_sequence
    return task


def _weakness_context(
    *,
    project_dir: str | Path,
    regression_receipt: dict[str, Any],
    counterexample_trace: dict[str, Any] | None,
) -> dict[str, Any]:
    comparison = regression_receipt.get("quotient_comparison")
    comparison = comparison if isinstance(comparison, dict) else {}
    trace = counterexample_trace if isinstance(counterexample_trace, dict) else {}
    relation = str(regression_receipt.get("candidate_relation") or "")
    candidate_identity = str(
        regression_receipt.get("candidate_sha")
        or regression_receipt.get("candidate_submission")
        or trace.get("gated_sha256")
        or trace.get("gated_file")
        or ""
    ).strip()
    return {
        "project_dir": str(project_dir),
        "relation": relation,
        "gate_failure": relation in {"hard_gate_failure", "improved_but_gate_failed"},
        "quotient_relation": str(comparison.get("relation") or ""),
        "geometry_kind": str(regression_receipt.get("geometry_kind") or ""),
        "best_prior_submission": str(regression_receipt.get("best_prior_submission") or ""),
        "candidate_exact_rows": _maybe_int(regression_receipt.get("candidate_exact_rows")),
        "best_prior_exact_rows": _maybe_int(regression_receipt.get("best_prior_exact_rows")),
        "first_mismatch": str(trace.get("first_mismatch") or regression_receipt.get("first_mismatch") or ""),
        "visible_replay_exact": _visible_replay_is_exact(trace),
        "boundary_gate_failure": _has_boundary_gate_failure(trace),
        "counterexample_context_probe_available": _counterexample_context_probe_available(
            comparison,
            trace=trace,
            candidate_identity=candidate_identity,
        ),
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
            "predicate_fn": lambda ctx: ctx["gate_failure"]
            and ctx["visible_replay_exact"]
            and ctx["boundary_gate_failure"],
            "route": "run_or_return_substrate_boundary_gate",
            "recommended_capability_id": "run_strategy_required_gate",
            "provenance": "seed",
        },
        {
            "class_name": "unquotiented_counterexample_chart_missing",
            "predicate_fn": lambda ctx: ctx["gate_failure"]
            and bool(ctx["first_mismatch"])
            and ctx["counterexample_context_probe_available"],
            "route": "request_counterexample_context_then_refine_abstraction",
            "recommended_capability_id": "inspect_worldmodel_counterexample_context",
            "provenance": "seed",
        },
        {
            "class_name": "visible_counterexample_trace_unfactored",
            "predicate_fn": lambda ctx: ctx["gate_failure"] and bool(ctx["first_mismatch"]),
            "route": "inspect_visible_regression_trace_then_refine_or_propose_capability",
            "recommended_capability_id": "mine_worldmodel_lowerable_selectors",
            "provenance": "seed",
        },
        {
            "class_name": "declared_gate_obligation_open",
            "predicate_fn": lambda ctx: ctx["gate_failure"]
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
        from ztare.common.strategy_card_roles import active_strategy_cards

        cards = active_strategy_cards(path)
    except Exception:
        return False
    for card in cards:
        plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
        gate = plan.get("required_next_gate") if isinstance(plan.get("required_next_gate"), dict) else {}
        if str(gate.get("command") or "").strip():
            return True
    return False
