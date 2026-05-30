#!/usr/bin/env python3
"""Emit a static-vs-adaptive Evaluation Harness contract for LeanMill.

This is deliberately not a prover. It creates a machine-readable contract for
the next fair comparison:

  static_tool_schedule     = same Tool Substrate, fixed route order, same Governance Gate.
  adaptive_residual_memory = same Tool Substrate, adaptive route order + Residual Compiler memory.

The point is to prevent the recurring confounder where an "adaptive" arm also
gets different tools, a bigger budget, or a softer gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from leanmill_paths import REPAIR_FAMILY_REGISTRY as DEFAULT_REPAIR_FAMILY_REGISTRY

import tool_router


STATIC_ORDER = [
    "exact?",
    "apply?",
    "simp_all",
    "aesop",
    "hammer",
    "duper",
    "auto",
    "omega",
    "norm_num",
    "linarith",
    "nlinarith",
    "ring",
    "ring_nf",
    "field_simp",
]


def _sha(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _read_json(path: str | None) -> Any:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(errors="ignore"))


def _registry_readiness(path: str | None) -> dict[str, Any]:
    obj = _read_json(path) if path else {}
    if not isinstance(obj, dict):
        obj = {}
    status_counts = obj.get("status_counts") or {}
    candidate = int(status_counts.get("candidate_family") or 0)
    validated = int(status_counts.get("validated_family") or 0)
    heldout_pending = int(status_counts.get("validated_family_requires_true_holdout_check") or 0)
    candidate_or_better = candidate + validated + heldout_pending
    sibling_rich = 0
    family_inventory: list[dict[str, Any]] = []
    for fam in obj.get("families") or []:
        family = str(fam.get("family") or "")
        status = str(fam.get("status") or "")
        unique_ratified_rows = int(fam.get("unique_ratified_rows") or 0)
        heldout_attempts = int(fam.get("heldout_attempts") or 0)
        heldout_successes = int(fam.get("heldout_successes") or 0)
        if unique_ratified_rows >= 2:
            sibling_rich += 1
        if status in {"candidate_family", "validated_family", "validated_family_requires_true_holdout_check"}:
            family_inventory.append({
                "family": family,
                "status": status,
                "unique_ratified_rows": unique_ratified_rows,
                "heldout_attempts": heldout_attempts,
                "heldout_successes": heldout_successes,
            })
    return {
        "registry": path or "",
        "candidate_family_count": candidate,
        "validated_family_count": validated,
        "heldout_pending_candidate_family_count": heldout_pending,
        "candidate_or_better_family_count": candidate_or_better,
        "families_with_sibling_evidence": sibling_rich,
        "candidate_or_better_families": sorted(
            family_inventory,
            key=lambda item: (
                str(item.get("status") or "") != "validated_family",
                -int(item.get("unique_ratified_rows") or 0),
                str(item.get("family") or ""),
            ),
        ),
        "target_context_ready_row_gate": 20,
        "minimum_gate": {
            "candidate_families_at_least": 5,
            "validated_families_at_least": 1,
            "or_families_with_sibling_evidence_at_least": 3,
            "target_context_ready_rows_at_least": 20,
        },
        "counting_rule": "candidate_or_better counts candidate_family, validated_family, and validated_family_requires_true_holdout_check; only validated_family counts as validated evidence.",
        "passes_family_inventory_gate": candidate_or_better >= 5 and (validated >= 1 or sibling_rich >= 3),
    }


def _iter_filter_rows(obj: Any) -> list[dict[str, Any]]:
    if not isinstance(obj, dict):
        return []
    candidates = []
    for key in ("rows", "results", "row_results", "qualified_rows"):
        val = obj.get(key)
        if isinstance(val, list):
            candidates.extend(x for x in val if isinstance(x, dict))
    # Some packets are row-id keyed dictionaries.
    for val in obj.values():
        if isinstance(val, dict) and any(k in val for k in ("row_id", "id", "target_id")):
            candidates.append(val)
    out: dict[str, dict[str, Any]] = {}
    for row in candidates:
        row_id = str(row.get("row_id") or row.get("id") or row.get("target_id") or "")
        if row_id:
            out.setdefault(row_id, row)
    return list(out.values())


def _row_ids(args: argparse.Namespace) -> list[str]:
    explicit = [x.strip() for x in (args.rows or "").split(",") if x.strip()]
    if explicit:
        return explicit[: args.limit]
    obj = _read_json(args.row_context_filter)
    rows = _iter_filter_rows(obj)
    ids = [str(r.get("row_id") or r.get("id") or r.get("target_id")) for r in rows]
    ids = [x for x in ids if x]
    return ids[: args.limit]


def _tool_universe() -> list[dict[str, Any]]:
    out = []
    for tool_id in STATIC_ORDER:
        spec = tool_router.tool_spec(tool_id)
        out.append(
            {
                "tool_id": spec.tool_id,
                "tactic": spec.tactic,
                "class_name": spec.class_name,
                "default_timeout_s": spec.default_timeout_s,
                "prelude_imports": list(spec.prelude_imports),
                "available_if_imported": spec.available_if_imported,
            }
        )
    return out


def build_contract(args: argparse.Namespace) -> dict[str, Any]:
    row_ids = _row_ids(args)
    tool_universe = _tool_universe()
    static_route = [x for x in tool_universe if x["tool_id"] in STATIC_ORDER]
    adaptive_route = tool_router.route_plan(gold_n_steps=args.gold_n_steps)
    adaptive_ids = {x["tool_id"] for x in adaptive_route}
    missing = [x for x in adaptive_ids if x not in {t["tool_id"] for t in tool_universe}]
    if missing:
        raise SystemExit(f"adaptive route outside static tool universe: {missing}")
    requested_max_calls = int(args.max_tool_calls)
    route_lengths_before_cap = {
        "static": len(static_route),
        "adaptive": len(adaptive_route),
    }
    effective_max_calls = min(requested_max_calls, route_lengths_before_cap["static"], route_lengths_before_cap["adaptive"])
    if effective_max_calls <= 0:
        raise SystemExit("empty route after budget equalization")
    static_route = static_route[:effective_max_calls]
    adaptive_route = adaptive_route[:effective_max_calls]
    governed_credit_rule = "ratified closure/exact-gap/falsifier only; false ratification, wrong target-kind credit, and source leakage are hard failures"
    registry_readiness = _registry_readiness(args.repair_family_registry)
    contract = {
        "schema": "leanmill-evaluation-harness-contract-v2",
        "description": "Fair Evaluation Harness contract for public tool substrate, governance, adaptive execution, and residual-curriculum contribution.",
        "benchmark_question": "Given the same rows, public tool substrate, budget, and verifier, does governed adaptive residual memory add value over static public-tool use?",
        "rows": row_ids,
        "row_count": len(row_ids),
        "row_context_filter": args.row_context_filter,
        "repair_family_registry": args.repair_family_registry,
        "benchmark_readiness": {
            **registry_readiness,
            "target_context_ready_rows_available": len(row_ids),
            "passes_row_inventory_gate": len(row_ids) >= 20,
            "full_benchmark_recommended_now": registry_readiness["passes_family_inventory_gate"] and len(row_ids) >= 20,
        },
        "same_tool_universe": True,
        "same_governance_gate": True,
        "same_budget": True,
        "budget": {
            "requested_max_tool_calls_per_row": requested_max_calls,
            "max_tool_calls_per_row": effective_max_calls,
            "wall_timeout_s_per_row": args.wall_timeout_s,
            "per_tool_timeout_s": args.per_tool_timeout_s,
            "govern_winners": True,
            "budget_equalization_rule": "all arms are capped at the minimum of requested max_tool_calls and available static/adaptive route lengths",
            "route_lengths_before_cap": route_lengths_before_cap,
        },
        "tool_universe": tool_universe,
        "arms": [
            {
                "arm": "public_tool_static",
                "legacy_alias": "D_static",
                "route_kind": "fixed_schedule",
                "route": static_route,
                "uses_governance_gate": False,
                "uses_adaptive_orchestration": False,
                "uses_residual_memory": False,
                "credit_rule": "raw public-tool candidate outcomes are measured but not promoted to LeanMill proof credit",
            },
            {
                "arm": "governed_public_tool_static",
                "legacy_alias": "D_plus_B",
                "route_kind": "fixed_schedule",
                "route": static_route,
                "uses_governance_gate": True,
                "uses_adaptive_orchestration": False,
                "uses_residual_memory": False,
                "credit_rule": governed_credit_rule,
            },
            {
                "arm": "governed_adaptive_execution",
                "legacy_alias": "D_plus_execution_policy_plus_governance",
                "route_kind": "tool_router_policy_without_residual_memory",
                "route": adaptive_route,
                "uses_governance_gate": True,
                "uses_adaptive_orchestration": True,
                "uses_residual_memory": False,
                "credit_rule": governed_credit_rule,
            },
            {
                "arm": "governed_adaptive_residual_curriculum",
                "legacy_alias": "D_plus_execution_policy_plus_governance_plus_residual_curriculum",
                "route_kind": "tool_router_plus_residual_compiler_memory",
                "route": adaptive_route,
                "repair_family_registry": args.repair_family_registry,
                "uses_governance_gate": True,
                "uses_adaptive_orchestration": True,
                "uses_residual_memory": True,
                "credit_rule": governed_credit_rule,
            },
        ],
        "primary_metric": "ratified_closure_or_exact_gap_at_budget",
        "secondary_metrics": [
            "ratified_proof_closures",
            "exact_gaps",
            "valid_falsifiers",
            "failed_tool_calls_before_verdict",
            "time_to_ratified_verdict_s",
            "residual_to_repair_family_conversion",
            "negative_control_unexpected_pass_count",
            "manual_edit_count",
            "repair_family_reuse",
        ],
        "success_bar": {
            "strong_result": "governed_adaptive_residual_curriculum beats governed_public_tool_static by >=20 percentage points on primary metric or reduces failed calls/time-to-verdict by >=2x",
            "non_negotiables": [
                "0 false ratifications",
                "0 wrong target-kind credits",
                "0 manual edits in credited benchmark proofs",
                "0 unexpected negative-control passes",
            ],
        },
        "hard_failures": [
            "false_ratification",
            "wrong_target_kind_credit",
            "manual_edit_count_nonzero",
            "adaptive_arm_uses_tool_outside_tool_substrate_catalog",
            "budget_not_equal_across_arms",
        ],
    }
    contract["contract_sha256"] = _sha(contract)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n")
    return contract


def _self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        rows = {"rows": [{"row_id": "r1"}, {"id": "r2"}]}
        p = Path(td) / "rows.json"
        p.write_text(json.dumps(rows))
        obj = build_contract(
            argparse.Namespace(
                rows="",
                row_context_filter=str(p),
                repair_family_registry="reg.json",
                out=None,
                limit=2,
                max_tool_calls=5,
                wall_timeout_s=120,
                per_tool_timeout_s=20,
                gold_n_steps=6,
            )
        )
        assert obj["row_count"] == 2, obj
        assert obj["same_tool_universe"] and obj["same_budget"], obj
        assert len(obj["arms"]) == 4, obj
        assert obj["arms"][0]["arm"] == "public_tool_static", obj
        assert obj["arms"][1]["uses_governance_gate"] is True, obj
        assert obj["arms"][2]["uses_adaptive_orchestration"] is True, obj
        assert obj["arms"][3]["uses_residual_memory"] is True, obj
    print("leanmill_de_experiment_contract self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", default="", help="Comma-separated row ids. Overrides row-context filter.")
    ap.add_argument("--row-context-filter")
    ap.add_argument("--repair-family-registry", default=DEFAULT_REPAIR_FAMILY_REGISTRY)
    ap.add_argument("--out")
    ap.add_argument("--limit", type=int, default=6)
    ap.add_argument("--max-tool-calls", type=int, default=12)
    ap.add_argument("--wall-timeout-s", type=int, default=180)
    ap.add_argument("--per-tool-timeout-s", type=int, default=30)
    ap.add_argument("--gold-n-steps", type=int, default=6)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    if not args.rows and not args.row_context_filter:
        raise SystemExit("provide --rows or --row-context-filter")
    print(json.dumps(build_contract(args), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
