"""Normalize LeanMill proof-loop outputs into one advisory exit schema.

This module is deliberately not a credit gate. It gives Route C, auto-prover,
and later proof-loop runners a common vocabulary so dashboards and audit packets
can aggregate outcomes before governance decides proof value.
"""
from __future__ import annotations

import time
from collections import Counter
from pathlib import Path
from typing import Any

from ztare.leanmill.common import read_json
from ztare.research_director.structural_fingerprint import (
    RESIDUAL_TO_LEVER,
)

REPO = Path(__file__).resolve().parents[3]

SCHEMA = "leanmill-typed-proof-exit-v1"
SUMMARY_SCHEMA = "leanmill-typed-proof-exit-summary-v1"

CREDIT_BOUNDARY = (
    "advisory_only_no_factory_credit; closures require the existing governance "
    "and matched-negative-control receipt path before credit-ready status"
)
COMPILER_CONTRACT_SCHEMA = "leanmill-proof-compiler-contract-v1"

APPARATUS_STATUSES = {
    "dispatch_timeout",
    "dispatch_timeout_500s",
    "dispatch_timeout_600s",
    "sig_extract_failed",
    "harness_fail",
}


def _now() -> int:
    return int(time.time())


def _read_json(path: str | Path) -> Any:
    return read_json(path)


def _public_path(value: str | Path | None) -> str:
    if value is None:
        return ""
    s = str(value)
    if not s:
        return ""
    try:
        p = Path(s)
        if not p.is_absolute():
            return s
        try:
            return str(p.resolve().relative_to(REPO))
        except Exception:
            pass
        try:
            return f"<home>/{p.resolve().relative_to(Path.home())}"
        except Exception:
            pass
        return f"<external>/{p.name}"
    except Exception:
        return s


def _as_bool(value: Any) -> bool:
    return bool(value is True or str(value).lower() == "true")


def _candidate_lemmas_from_rounds(rounds: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for rec in rounds:
        candidate = rec.get("candidate") if isinstance(rec.get("candidate"), dict) else {}
        name = str(candidate.get("lemma_name") or rec.get("lemma") or "").strip()
        if name and name not in out:
            out.append(name)
    return out


def _candidate_pathways_from_rounds(rounds: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for rec in rounds:
        candidate = rec.get("candidate") if isinstance(rec.get("candidate"), dict) else {}
        pathway = str(candidate.get("structural_pathway") or "").strip()
        if pathway and pathway not in out:
            out.append(pathway)
    return out


def _shelf_summary(shelf: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(shelf, dict):
        return {}
    sources = {}
    for key, value in shelf.items():
        if isinstance(value, list):
            sources[key] = len(value)
    return {
        "schema": shelf.get("schema"),
        "query_sha256": shelf.get("query_sha256"),
        "enabled": bool(shelf),
        "source_counts": sources,
        "skip_reasons": shelf.get("skip_reasons") or [],
    }


def _route_c_shelf(result: dict[str, Any]) -> dict[str, Any]:
    context = result.get("row_context") if isinstance(result.get("row_context"), dict) else {}
    return _shelf_summary(context.get("semantic_premise_shelf") if isinstance(context, dict) else {})


def _base_exit(*, source_kind: str, source_path: str = "", run_id: str = "") -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "generated_at_epoch": _now(),
        "source_kind": source_kind,
        "source_path": _public_path(source_path),
        "run_id": str(run_id or ""),
        "credit_status": "not_credit_ready",
        "credit_boundary": CREDIT_BOUNDARY,
        "proof_credit": "none_typed_exit_is_advisory",
    }


def _nearest_confuser(exit_kind: str, residual_class: str) -> str:
    if exit_kind == "unratified_closure_candidate":
        return "raw_closure_candidate_laundered_as_factory_credit"
    if exit_kind == "gap_report" or residual_class == "theorem_or_pde_gap":
        return "repeat_same_prompt_without_missing_lemma_contract"
    if residual_class == "apparatus_or_source_mismatch":
        return "spend_more_prover_calls_on_source_or_context_mismatch"
    if residual_class == "vocabulary_gap":
        return "treat_unknown_exit_as_credible_evidence"
    return "collapse_advisory_exit_into_ratified_claim"


def _action_program_for_exit(row: dict[str, Any]) -> list[dict[str, Any]]:
    exit_kind = str(row.get("typed_exit_kind") or "")
    residual_class = str(row.get("residual_class") or "")
    target = str(row.get("target_name") or row.get("attempt_id") or "target")
    lemmas = [str(x) for x in (row.get("candidate_lemmas") or []) if str(x)]
    if exit_kind == "unratified_closure_candidate":
        return [
            {
                "id": "route_to_governance_gate",
                "requires": ["compiled_candidate_artifact"],
                "produces": ["governance_receipt"],
            },
            {
                "id": "run_matched_negative_control",
                "requires": ["governance_receipt"],
                "produces": ["matched_negative_control_receipt"],
            },
            {
                "id": "credit_only_if_all_receipts_pass",
                "requires": ["governance_receipt", "matched_negative_control_receipt"],
                "produces": ["credit_ready_decision_or_rejection"],
            },
        ]
    if exit_kind == "gap_report" or residual_class == "theorem_or_pde_gap":
        missing = lemmas[0] if lemmas else target
        return [
            {
                "id": "promote_missing_lemma_obligation",
                "target": missing,
                "requires": ["gap_report"],
                "produces": ["missing_lemma_work_item_or_pencil_artifact"],
            },
            {
                "id": "attempt_missing_lemma_with_candidate_shelf",
                "target": missing,
                "requires": ["missing_lemma_work_item_or_pencil_artifact"],
                "produces": ["missing_lemma_receipt_or_typed_failure"],
            },
            {
                "id": "rerun_parent_target_after_receipt",
                "target": target,
                "requires": ["missing_lemma_receipt_or_typed_failure"],
                "produces": ["updated_typed_exit"],
            },
        ]
    if residual_class == "apparatus_or_source_mismatch":
        return [
            {
                "id": "repair_source_or_context",
                "requires": ["source_artifact_ref", "error_excerpt"],
                "produces": ["source_context_repair_receipt"],
            },
            {
                "id": "rerun_normalizer",
                "requires": ["source_context_repair_receipt"],
                "produces": ["updated_typed_exit"],
            },
        ]
    return [
        {
            "id": "operator_review_unknown_exit",
            "requires": ["typed_exit"],
            "produces": ["classified_residual_or_retirement"],
        }
    ]


def compiler_contract_for_exit(row: dict[str, Any]) -> dict[str, Any]:
    """Compact action contract for one advisory proof-loop exit.

    This is the LeanMill transposition of the reasoning-compiler result:
    keep labels advisory, but expose source-bound residual edge, nearest
    confuser, action program, invariant checks, and pending outcome trace.
    """
    source_path = str(row.get("source_path") or "")
    attempt = str(row.get("attempt_id") or row.get("target_name") or "unknown")
    residual_class = str(row.get("residual_class") or "vocabulary_gap")
    exit_kind = str(row.get("typed_exit_kind") or "unknown_advisory_exit")
    action_program = _action_program_for_exit(row)
    invariants = [
        {
            "id": "no_credit_without_governance",
            "status": "pass" if row.get("credit_status") != "credit_ready" else "fail",
            "detail": CREDIT_BOUNDARY,
        },
        {
            "id": "source_or_attempt_bound",
            "status": "pass" if (source_path or attempt != "unknown") else "fail",
            "detail": source_path or attempt,
        },
        {
            "id": "nearest_confuser_named",
            "status": "pass",
            "detail": _nearest_confuser(exit_kind, residual_class),
        },
        {
            "id": "action_program_nonempty",
            "status": "pass" if action_program else "fail",
            "detail": str(len(action_program)),
        },
    ]
    return {
        "schema": COMPILER_CONTRACT_SCHEMA,
        "contract_status": "accepted_for_shadow_execution"
        if all(x["status"] == "pass" for x in invariants) else "repair_before_execution",
        "source_facts": {
            "source_kind": row.get("source_kind"),
            "source_path": source_path,
            "run_id": row.get("run_id"),
            "attempt_id": attempt,
            "closure_verdict": row.get("closure_verdict") or row.get("outcome"),
            "compiled_any": row.get("compiled_any"),
            "candidate_lemmas": row.get("candidate_lemmas") or [],
            "semantic_premise_shelf": row.get("semantic_premise_shelf") or {},
        },
        "selected_residual_edge": {
            "residual_class": residual_class,
            "typed_exit_kind": exit_kind,
            "next_lever": row.get("next_lever"),
        },
        "rejected_nearest_confuser_edge": _nearest_confuser(exit_kind, residual_class),
        "action_program": action_program,
        "current_action_index": 0,
        "required_next_action": action_program[0]["id"] if action_program else "operator_review_unknown_exit",
        "program_counter_rule": (
            "Advance only after the required action has a concrete artifact_ref "
            "or typed terminal outcome; do not convert advisory exits into proof credit."
        ),
        "deterministic_invariants": invariants,
        "shadow_outcome_trace": {
            "status": "pending",
            "later_outcome_ref": None,
            "cost_or_regret_signal": None,
        },
        "credit_boundary": CREDIT_BOUNDARY,
    }


def _classify_route_c_exit(result: dict[str, Any]) -> tuple[str, str]:
    status = str(result.get("status") or "")
    verdict = str(result.get("closure_verdict") or result.get("verdict") or "")
    compiled = _as_bool(result.get("compiled_any"))
    if compiled or verdict in {"CLOSED", "CLOSED_BY_CANDIDATE"}:
        return "unratified_closure_candidate", "none_closed"
    if verdict.startswith("BLOCKED_"):
        return "blocked_by_audit_gate", "gate_contract_not_crisp"
    if status.startswith("result_read_error") or status.startswith("dispatch_timeout") or status in APPARATUS_STATUSES:
        return "apparatus_or_source_mismatch", "apparatus_or_source_mismatch"
    if verdict == "OPEN_GAP_REPORT" or result.get("gap_report") or result.get("proposed_lemmas"):
        return "gap_report", "theorem_or_pde_gap"
    return "unknown_advisory_exit", "vocabulary_gap"


def normalize_route_c_result(
    result: dict[str, Any],
    *,
    source_path: str = "",
    run_id: str = "",
    row_id_hint: str = "",
) -> dict[str, Any]:
    rounds = result.get("rounds") if isinstance(result.get("rounds"), list) else []
    gap = result.get("gap_report") if isinstance(result.get("gap_report"), dict) else {}
    candidate_lemmas = [
        str(x) for x in (
            result.get("proposed_lemmas")
            or gap.get("named_candidate_lemmas")
            or _candidate_lemmas_from_rounds(rounds)
            or []
        )
        if str(x)
    ]
    candidate_pathways = [
        str(x) for x in (gap.get("candidate_pathways") or _candidate_pathways_from_rounds(rounds) or [])
        if str(x)
    ]
    exit_kind, residual_class = _classify_route_c_exit(result)
    attempt_id = str(
        row_id_hint
        or result.get("row_id")
        or result.get("attempt_id")
        or gap.get("target_row")
        or result.get("theorem")
        or "unknown"
    )
    next_target = (
        f"Prove missing lemma `{candidate_lemmas[0]}`"
        if candidate_lemmas and residual_class == "theorem_or_pde_gap"
        else "Route closure candidate to governance" if residual_class == "none_closed"
        else "Inspect typed exit and repair source/context"
    )
    out = _base_exit(source_kind="route_c_layer_2c", source_path=source_path, run_id=run_id)
    out.update({
        "attempt_id": attempt_id,
        "target_name": str(result.get("theorem") or ""),
        "source_file": _public_path(result.get("source_file") or ""),
        "closure_verdict": result.get("closure_verdict") or result.get("verdict") or result.get("status"),
        "compiled_any": _as_bool(result.get("compiled_any")),
        "typed_exit_kind": exit_kind,
        "residual_class": residual_class,
        "next_lever": RESIDUAL_TO_LEVER[residual_class],
        "next_target_statement": next_target,
        "candidate_lemmas": candidate_lemmas,
        "candidate_pathways": candidate_pathways,
        "rounds_summary": [
            {
                "round": rec.get("round"),
                "lemma": rec.get("lemma") or ((rec.get("candidate") or {}).get("lemma_name") if isinstance(rec.get("candidate"), dict) else None),
                "compiled": rec.get("compiled"),
                "error_head": rec.get("error_head"),
            }
            for rec in rounds[:5]
            if isinstance(rec, dict)
        ],
        "operation_type": result.get("operation_type_chosen") or gap.get("operation_type"),
        "semantic_premise_shelf": _route_c_shelf(result),
        "raw_status": result.get("status"),
    })
    out["proof_compiler_contract"] = compiler_contract_for_exit(out)
    return out


def normalize_route_c_payload(payload: dict[str, Any], *, source_path: str = "", run_id: str = "") -> list[dict[str, Any]]:
    if isinstance(payload.get("results"), list):
        rid = str(run_id or payload.get("class") or payload.get("model") or "")
        return [
            normalize_route_c_result(row, source_path=source_path, run_id=rid, row_id_hint=str(row.get("row_id") or ""))
            for row in payload.get("results") or []
            if isinstance(row, dict)
        ]
    return [normalize_route_c_result(payload, source_path=source_path, run_id=run_id)]


def _classify_auto_prover_exit(result: dict[str, Any]) -> tuple[str, str]:
    outcome = str(result.get("outcome") or "")
    if outcome == "closed":
        return "unratified_closure_candidate", "none_closed"
    if outcome == "timeout":
        return "timeout", "apparatus_or_source_mismatch"
    if outcome in {"error", "skipped"}:
        return "apparatus_or_source_mismatch", "apparatus_or_source_mismatch"
    if outcome == "failed":
        return "failed_no_closure", "theorem_or_pde_gap"
    return "unknown_advisory_exit", "vocabulary_gap"


def normalize_auto_prover_result(
    result: dict[str, Any],
    *,
    source_path: str = "",
    run_id: str = "",
) -> dict[str, Any]:
    exit_kind, residual_class = _classify_auto_prover_exit(result)
    name = str(result.get("name") or result.get("target_name") or "unknown")
    next_target = (
        f"Route `{name}` closure candidate to governance"
        if residual_class == "none_closed"
        else f"Retry or prove `{name}` with a stronger prover/context"
    )
    out = _base_exit(source_kind="auto_prover_harness", source_path=source_path, run_id=run_id)
    out.update({
        "attempt_id": name,
        "target_name": name,
        "target_kind": result.get("kind"),
        "outcome": result.get("outcome"),
        "exit_code": result.get("exit_code"),
        "typed_exit_kind": exit_kind,
        "residual_class": residual_class,
        "next_lever": RESIDUAL_TO_LEVER[residual_class],
        "next_target_statement": next_target,
        "candidate_lemmas": [],
        "semantic_premise_shelf": _shelf_summary(result.get("semantic_premise_shelf") if isinstance(result.get("semantic_premise_shelf"), dict) else {}),
        "stderr_excerpt": result.get("stderr_excerpt"),
    })
    out["proof_compiler_contract"] = compiler_contract_for_exit(out)
    return out


def normalize_auto_prover_payload(payload: dict[str, Any], *, source_path: str = "", run_id: str = "") -> list[dict[str, Any]]:
    rid = str(run_id or payload.get("prover_cmd") or "")
    if isinstance(payload.get("results"), list):
        return [
            normalize_auto_prover_result(row, source_path=source_path, run_id=rid)
            for row in payload.get("results") or []
            if isinstance(row, dict)
        ]
    return [normalize_auto_prover_result(payload, source_path=source_path, run_id=run_id)]


def normalize_paths(
    *,
    route_c_paths: list[str | Path] | None = None,
    auto_prover_paths: list[str | Path] | None = None,
) -> list[dict[str, Any]]:
    exits: list[dict[str, Any]] = []
    for path in route_c_paths or []:
        payload = _read_json(path)
        if isinstance(payload, dict):
            exits.extend(normalize_route_c_payload(payload, source_path=str(path)))
    for path in auto_prover_paths or []:
        payload = _read_json(path)
        if isinstance(payload, dict):
            exits.extend(normalize_auto_prover_payload(payload, source_path=str(path)))
    return exits


def typed_exit_summary(exits: list[dict[str, Any]]) -> dict[str, Any]:
    source_counts = Counter(str(row.get("source_kind") or "unknown") for row in exits)
    kind_counts = Counter(str(row.get("typed_exit_kind") or "unknown") for row in exits)
    residual_counts = Counter(str(row.get("residual_class") or "unknown") for row in exits)
    candidate_lemmas = Counter()
    contract_status = Counter()
    required_actions = Counter()
    invariant_failures = Counter()
    for row in exits:
        candidate_lemmas.update(str(x) for x in (row.get("candidate_lemmas") or []) if str(x))
        contract = row.get("proof_compiler_contract") if isinstance(row.get("proof_compiler_contract"), dict) else {}
        if contract:
            contract_status.update([str(contract.get("contract_status") or "unknown")])
            required_actions.update([str(contract.get("required_next_action") or "unknown")])
            for inv in contract.get("deterministic_invariants") or []:
                if isinstance(inv, dict) and inv.get("status") != "pass":
                    invariant_failures.update([str(inv.get("id") or "unknown")])
    return {
        "schema": SUMMARY_SCHEMA,
        "exit_count": len(exits),
        "source_kind_counts": dict(sorted(source_counts.items())),
        "typed_exit_kind_counts": dict(sorted(kind_counts.items())),
        "residual_class_counts": dict(sorted(residual_counts.items())),
        "closure_candidate_count": kind_counts.get("unratified_closure_candidate", 0),
        "gap_report_count": kind_counts.get("gap_report", 0),
        "apparatus_or_source_mismatch_count": kind_counts.get("apparatus_or_source_mismatch", 0) + kind_counts.get("timeout", 0),
        "top_candidate_lemmas": [
            {"lemma": lemma, "count": count}
            for lemma, count in candidate_lemmas.most_common(20)
        ],
        "proof_compiler_contract": {
            "schema": COMPILER_CONTRACT_SCHEMA,
            "contract_status_counts": dict(sorted(contract_status.items())),
            "required_next_action_counts": dict(sorted(required_actions.items())),
            "invariant_failure_counts": dict(sorted(invariant_failures.items())),
            "instrumentation_boundary": (
                "reasoning-compiler shadow contract only; no enforcement or proof credit"
            ),
        },
        "credit_boundary": CREDIT_BOUNDARY,
        "proof_credit": "none_summary_is_advisory",
    }
