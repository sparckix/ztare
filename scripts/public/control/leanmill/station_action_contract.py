#!/usr/bin/env python3
"""Emit station-utilization and residual-to-check contracts for LeanMill.

Throughput is only useful if each station emits the unit of learning:
ratified closure, guarded repair canary, exact-gap packet, source request,
retire decision, or a typed residual that selects the next check. This script
turns the file-backed factory state into explicit station contracts.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from leanmill_paths import DATA_DIR as DEFAULT_DATA_DIR
from leanmill_paths import REPAIR_FAMILY_REGISTRY as DEFAULT_REGISTRY



def _read(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return {}


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _station_name(value: Any) -> str:
    aliases = {
        "path_a_active": "proof_execution_active",
        "path_a_idle_with_ready_wip": "proof_execution_idle_with_ready_wip",
        "path_b_governance": "governance_gate",
        "path_c_repair_compiler": "residual_compiler",
        "path_c_curriculum": "residual_compiler",
        "path_c": "residual_compiler",
    }
    text = str(value or "")
    return aliases.get(text, text)


def _registry_statuses(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(f.get("family") or ""): f for f in registry.get("families") or []}


def _consumed_rows(registry: dict[str, Any]) -> set[str]:
    rows: set[str] = set()
    for family in registry.get("families") or []:
        useful = (
            _int(family.get("ratified_proof_closure"))
            + _int(family.get("exact_gap"))
            + _int(family.get("valid_falsifier"))
        )
        if useful:
            rows.update(str(r) for r in family.get("rows_attempted") or [] if str(r))
        elif _int(family.get("negative_controls_expected_fail")):
            rows.update(str(r) for r in family.get("rows_attempted") or [] if str(r))
    return rows


def _family_is_actionable_from_residual_plan(
    packet: dict[str, Any],
    registry_statuses: dict[str, dict[str, Any]],
    consumed_rows: set[str],
) -> bool:
    family = str(packet.get("repair_family") or "")
    entry = registry_statuses.get(family) or {}
    status = str(entry.get("status") or "")
    packet_rows = {str(r) for r in packet.get("rows") or [] if str(r)}
    attempted = {str(r) for r in entry.get("rows_attempted") or [] if str(r)}
    useful = (
        _int(entry.get("ratified_proof_closure"))
        + _int(entry.get("exact_gap"))
        + _int(entry.get("valid_falsifier"))
    )
    if packet_rows and packet_rows.issubset(attempted) and useful >= len(packet_rows):
        return False
    if packet_rows and packet_rows.issubset(consumed_rows):
        return False
    return status not in {"candidate_family", "validated_family_requires_true_holdout_check"}


def _registry_promotion_target(registry: dict[str, Any]) -> dict[str, Any] | None:
    families = list(registry.get("families") or [])
    candidates = [
        f for f in families
        if str(f.get("status") or "") == "seed_only"
        and _int(f.get("negative_controls_unexpected_pass")) == 0
        and _int(f.get("false_ratifications")) == 0
    ]
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda f: (
            -_int(f.get("ratified_proof_closure")),
            -_int(f.get("negative_controls_expected_fail")),
            _int(f.get("unique_ratified_rows")),
            str(f.get("family") or ""),
        ),
    )[0]


def _registry_kpis(registry: dict[str, Any]) -> dict[str, Any]:
    families = list(registry.get("families") or [])
    return {
        "ratified_repair_canary_closures": sum(_int(f.get("ratified_proof_closure")) for f in families),
        "expected_failing_negative_controls": sum(_int(f.get("negative_controls_expected_fail")) for f in families),
        "unexpected_negative_control_passes": sum(_int(f.get("negative_controls_unexpected_pass")) for f in families),
        "candidate_families": _int((registry.get("status_counts") or {}).get("candidate_family")),
        "validated_family_receipts_needed": _int(
            (registry.get("status_counts") or {}).get("validated_family_requires_true_holdout_check")
        ),
        "seed_only_families": _int((registry.get("status_counts") or {}).get("seed_only")),
        "inventory_only_families": _int((registry.get("status_counts") or {}).get("inventory_only")),
        "source_credit_eligible_ratifications": sum(
            _int(f.get("source_credit_eligible_ratifications")) for f in families
        ),
        "clean_solver_credit_eligible_ratifications": sum(
            _int(f.get("clean_solver_credit_eligible_ratifications")) for f in families
        ),
    }


def _work_orders(contracts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_station = {str(c.get("station")): c for c in contracts}
    orders: list[dict[str, Any]] = []

    residual = by_station.get("residual_curriculum") or {}
    top_packet = residual.get("top_packet")
    if top_packet:
        family = str(top_packet.get("repair_family") or "")
        orders.append({
            "priority": 1,
            "work_order_id": f"residual_compiler:{family}",
            "station": "residual_curriculum",
            "action": "compile family-specific canary/exact-gap packet",
            "learning_unit_exit": "repair canary, exact gap, valid falsifier, or tested retirement",
            "family": family,
            "rows": list(top_packet.get("rows") or []),
            "required_receipt": residual.get("required_check_receipt"),
            "success_gate": [
                "all selected rows have a typed exit",
                "matched negative controls are present for canary positives",
                "unexpected negative-control passes remain zero",
                "source-credit and repair-credit are recorded separately",
            ],
        })
    elif residual.get("state") == "ready" and _int(residual.get("wip_count")):
        orders.append({
            "priority": 1,
            "work_order_id": "residual_compiler:refresh_source_plan",
            "station": "residual_curriculum",
            "action": residual.get("next_action"),
            "learning_unit_exit": "repair canary, exact gap, valid falsifier, source request, or tested retirement",
            "family": None,
            "wip_count": _int(residual.get("wip_count")),
            "required_receipt": residual.get("required_check_receipt"),
            "success_gate": [
                "ready residual rows are reclassified into typed exits",
                "no row remains in generic residual backlog without a next check",
                "exact-gap/falsifier candidates are not counted as closures",
            ],
        })

    registry = by_station.get("repair_registry") or {}
    promotion_target = registry.get("promotion_target")
    if promotion_target:
        family = str(promotion_target.get("family") or "")
        rows = list(promotion_target.get("rows_attempted") or [])
        orders.append({
            "priority": 2,
            "work_order_id": f"registry:{family}",
            "station": "repair_registry",
            "action": "find sibling or heldout evidence for seed family",
            "learning_unit_exit": "candidate-family promotion or seed hold with reason",
            "family": family,
            "rows": rows,
            "required_receipt": registry.get("required_check_receipt"),
            "success_gate": [
                ">=2 useful outcomes across >=2 rows for candidate promotion",
                ">=1 expected-failing negative control",
                "0 unexpected negative-control passes",
                "hold if no sibling/heldout row can be sourced",
            ],
        })

    source = by_station.get("source_qualification") or {}
    if source.get("state") in {"needs_static_filter", "needs_target_context_filter", "ready_for_intake"}:
        orders.append({
            "priority": 3,
            "work_order_id": "source:qualification",
            "station": "source_qualification",
            "action": source.get("next_action"),
            "learning_unit_exit": "qualified source or target-context-ready intake row",
            "wip_count": _int(source.get("wip_count")),
            "required_receipt": source.get("required_check_receipt"),
            "success_gate": [
                "exact-target and post-target same-file exclusions are counted",
                "source safety status is recorded",
                "target-context-ready candidate count is emitted",
            ],
        })

    governance = by_station.get("governance_gate") or {}
    if governance.get("state") == "active":
        orders.append({
            "priority": 0,
            "work_order_id": "governance:drain",
            "station": "governance_gate",
            "action": governance.get("next_action"),
            "learning_unit_exit": "ratified closure or rejected/residualized candidate",
            "wip_count": _int(governance.get("wip_count")),
            "required_receipt": governance.get("required_check_receipt"),
            "success_gate": ["pending governance queue reaches zero"],
        })

    return sorted(orders, key=lambda o: (_int(o.get("priority")), str(o.get("work_order_id") or "")))


def _source_buffer_contract(latest: dict[str, Any]) -> dict[str, Any]:
    sp = latest.get("source_packet") or {}
    sf = latest.get("static_filter") or {}
    rc = latest.get("row_context_filter") or latest.get("row_context_partial") or {}
    usable = _int(sp.get("usable_candidate_total"))
    rows = _int(sp.get("row_count") or latest.get("queue_count"))
    target_ready = _int(rc.get("row_context_ready_total"))
    static_ready = _int(sf.get("canary_ready_total"))
    if target_ready:
        state = "ready_for_intake"
        next_action = "build or refresh intake DB from row-context-ready rows"
    elif static_ready:
        state = "needs_target_context_filter"
        next_action = "run row-context qualification before proof execution"
    elif usable:
        state = "needs_static_filter"
        next_action = "run static/source-safety qualification when the Lean slot is free"
    else:
        state = "empty"
        next_action = "run source acquisition or refill"
    return {
        "station": "source_qualification",
        "state": state,
        "wip_count": target_ready or static_ready or usable or rows,
        "required_check_receipt": {
            "artifact": "source_to_intake_receipt",
            "must_include": [
                "exact-target exclusion count",
                "post-target same-file exclusion count",
                "source safety status",
                "row-context-ready candidate count",
            ],
        },
        "causal_edge": "source candidates -> target-context-ready intake rows",
        "next_action": next_action,
    }


def _station_contracts(
    status: dict[str, Any],
    p0: dict[str, Any],
    live: dict[str, Any],
    source_plan: dict[str, Any],
    registry: dict[str, Any],
) -> list[dict[str, Any]]:
    intake = status.get("intake") or {}
    mill = status.get("mill") or {}
    queue = status.get("governance_queue") or {}
    residual_plan = status.get("residual_plan") or {}
    p0_proof = p0.get("proof_execution") or p0.get("path_a_execution") or {}
    p0_governance = p0.get("governance_gate") or p0.get("path_b_governance") or {}
    p0_residual = p0.get("residual_compiler") or p0.get("path_c_curriculum") or {}
    latest = live.get("latest_source_buffer") or {}
    registry_statuses = _registry_statuses(registry)
    consumed_rows = _consumed_rows(registry)
    promotion_target = _registry_promotion_target(registry)

    top_residual = None
    packets = source_plan.get("packets") or residual_plan.get("top_packets") or []
    ready_packets = [
        p for p in packets
        if (
            _int(p.get("lead_count"))
            or p.get("scale_decision") == "promote_to_repair_lane"
        )
        and _family_is_actionable_from_residual_plan(p, registry_statuses, consumed_rows)
    ]
    if ready_packets:
        top_residual = sorted(
            ready_packets,
            key=lambda p: (-_int(p.get("priority")), -_int(p.get("lead_count")), str(p.get("repair_family") or "")),
        )[0]

    contracts = [_source_buffer_contract(latest)]
    contracts.extend([
        {
            "station": "intake_buffer",
            "state": "ready" if _int(intake.get("ready_total")) else "idle",
            "wip_count": _int(intake.get("ready_total")),
            "required_check_receipt": {
                "artifact": "intake_queue_receipt",
                "must_include": ["explicit global intake cap", "lane_hint", "priority", "stale-claim policy"],
            },
            "causal_edge": "target-context-ready intake rows -> bounded Proof Execution work",
            "next_action": (
                "start one bounded mill worker"
                if _int(intake.get("ready_total"))
                else "refill from source qualification when target-context-ready rows exist"
            ),
        },
        {
            "station": "proof_execution",
            "state": "active" if _int(mill.get("path_a_active_count")) else "idle",
            "wip_count": _int(mill.get("path_a_active_count")),
            "completed_count": _int(mill.get("path_a_done") or p0_proof.get("rows_done")),
            "required_check_receipt": {
                "artifact": "proof_execution_exit_receipt",
                "must_include": [
                    "compile-closed-to-govern event or typed residual event",
                    "residual_class",
                    "evidence_tail",
                    "next_lever",
                ],
            },
            "causal_edge": "row attempt -> governance candidate or residual-to-check edge",
            "next_action": (
                "do not add another heavy local Lean worker; let active job finish"
                if _int(mill.get("path_a_active_count"))
                else "wait for intake or source buffer"
            ),
        },
        {
            "station": "governance_gate",
            "state": "active" if _int(queue.get("pending_total") or p0_governance.get("pending")) else "idle",
            "wip_count": _int(queue.get("pending_total") or p0_governance.get("pending")),
            "completed_count": _int(queue.get("done_total") or p0_governance.get("ratified_proof_closures")),
            "required_check_receipt": {
                "artifact": "governance_verdict_receipt",
                "must_include": ["gate verdict", "axiom/sorry audit reason", "persisted proof path or residualized reason"],
            },
            "causal_edge": "compile-clean candidate -> ratified closure or rejected/residualized proof attempt",
            "next_action": (
                "run governance consumers until pending is zero"
                if _int(queue.get("pending_total") or p0_governance.get("pending"))
                else "do not add Governance Gate workers; gate is drained"
            ),
        },
        {
            "station": "residual_curriculum",
            "state": "ready" if _int(p0_residual.get("residual_events") or residual_plan.get("residual_events")) else "idle",
            "wip_count": _int(p0_residual.get("residual_events") or residual_plan.get("residual_events")),
            "required_check_receipt": {
                "artifact": "residual_to_check_contract",
                "must_include": [
                    "repair_family or exact_gap family",
                    "selected causal edge",
                    "nearest wrong-edge or negative control",
                    "required check that would make the artifact executable",
                ],
            },
            "causal_edge": "typed residual -> repair canary, exact-gap packet, source request, or retire decision",
            "next_action": (
                f"build canary/exact-gap packet for {top_residual.get('repair_family')}"
                if top_residual
                else "residual plan is drained for current registry; refresh residual family source plan"
            ),
            "top_packet": top_residual,
        },
        {
            "station": "repair_registry",
            "state": "ready" if registry.get("families") else "empty",
            "wip_count": _int((registry.get("status_counts") or {}).get("seed_only")),
            "completed_count": _int((registry.get("status_counts") or {}).get("candidate_family")),
            "required_check_receipt": {
                "artifact": "family_registry_receipt",
                "must_include": [
                    "ratified closure count",
                    "expected-failing negative-control count",
                    "unexpected negative-control pass count",
                    "source-credit and clean-solver-credit flags",
                ],
            },
            "causal_edge": "canary events -> seed/candidate/validated repair-family status",
            "next_action": (
                f"promote seed family {promotion_target.get('family')} with sibling or heldout evidence"
                if promotion_target
                else "seek heldout evidence for candidate families or refresh registry inventory"
            ),
            "promotion_target": promotion_target,
        },
    ])
    return contracts


def build(args: argparse.Namespace) -> dict[str, Any]:
    data = Path(args.data_dir)
    status = _read(data / "status_final.json")
    p0 = _read(data / "p0_rollup_final.json")
    live = _read(data / "factory_live_state.json")
    source_plan = _read(data / "residual_family_source_plan.json")
    registry = _read(Path(args.registry))
    contracts = _station_contracts(status, p0, live, source_plan, registry)
    work_orders = _work_orders(contracts)
    active = [c for c in contracts if c["state"] in {"ready", "ready_for_intake", "needs_target_context_filter", "needs_static_filter", "active"}]
    first_order = work_orders[0] if work_orders else {}
    payload = {
        "schema": "leanmill-station-action-contract-v1",
        "generated_at_epoch": int(time.time()),
        "principle": (
            "Maximize throughput of the learning unit, not raw row count: every station exit must emit "
            "a ratified closure, guarded repair canary, exact-gap packet, source request, retire decision, "
            "or typed residual-to-check edge."
        ),
        "mm_translation": {
            "mm_02": "quotient surface wording into the station/evidence-path graph",
            "mm_03": "promote the recurring residual/blocker into the primary edge that selects the next check",
            "active_unit": "residual-to-check causal edge plus required-check receipt",
        },
        "current_bottleneck": _station_name(
            (status.get("bottleneck") or {}).get("current_bottleneck") or live.get("current_bottleneck")
        ),
        "recommended_next_action": first_order.get("action")
        or (status.get("bottleneck") or {}).get("recommended_next_action")
        or live.get("recommended_next_action"),
        "registry_status_counts": registry.get("status_counts") or {},
        "kpis": _registry_kpis(registry),
        "station_contracts": contracts,
        "work_orders": work_orders,
        "active_or_ready_station_count": len(active),
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _self_test() -> int:
    payload = build(argparse.Namespace(data_dir="/tmp/no_such_dir", registry="/tmp/no_such_registry.json", out=None))
    assert payload["schema"] == "leanmill-station-action-contract-v1"
    assert len(payload["station_contracts"]) == 6
    assert "residual-to-check" in payload["mm_translation"]["active_unit"]
    fake = build(argparse.Namespace(data_dir="/tmp/no_such_dir", registry="/tmp/no_such_registry.json", out=None))
    assert fake["registry_status_counts"] == {}
    assert isinstance(fake["work_orders"], list)
    print("leanmill_station_action_contract self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    ap.add_argument("--registry", default=DEFAULT_REGISTRY)
    ap.add_argument("--out")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    obj = build(args)
    print(json.dumps({
        "out": args.out,
        "current_bottleneck": obj.get("current_bottleneck"),
        "active_or_ready_station_count": obj.get("active_or_ready_station_count"),
        "recommended_next_action": obj.get("recommended_next_action"),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
