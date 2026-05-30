#!/usr/bin/env python3
"""Rank LeanMill source/family work by governed learning yield."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from leanmill_paths import REPAIR_FAMILY_REGISTRY as DEFAULT_REGISTRY

DEFAULT_SOURCE_QUALITY = "analytics/public/leanmill/dashboard_data/source_quality_feedback.json"


REWARD = {
    "ratified_closure": 10.0,
    "exact_gap": 8.0,
    "valid_falsifier": 8.0,
    "candidate_family": 5.0,
    "negative_control_success": 3.0,
    "canary_ready_row": 1.0,
    "source_order_risk": -5.0,
    "timeout": -5.0,
    "unexpected_negative_pass": -10.0,
    "false_ratification": -100.0,
}


def _read(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return {}


def _score_family(fam: dict[str, Any]) -> float:
    score = 0.0
    score += float(fam.get("ratified_proof_closure") or 0) * REWARD["ratified_closure"]
    score += float(fam.get("exact_gap") or 0) * REWARD["exact_gap"]
    score += float(fam.get("valid_falsifier") or 0) * REWARD["valid_falsifier"]
    score += float(fam.get("negative_controls_expected_fail") or 0) * REWARD["negative_control_success"]
    score += float(fam.get("negative_controls_unexpected_pass") or 0) * REWARD["unexpected_negative_pass"]
    score += float(fam.get("false_ratifications") or 0) * REWARD["false_ratification"]
    if fam.get("status") == "candidate_family":
        score += REWARD["candidate_family"]
    return score


def _source_quality_by_family(path: str) -> dict[str, dict[str, Any]]:
    obj = _read(path)
    out: dict[str, dict[str, Any]] = {}
    for rec in obj.get("families") or []:
        family = str(rec.get("family") or "")
        if family:
            out[family] = rec
    return out


def build(args: argparse.Namespace) -> dict[str, Any]:
    registry = _read(args.registry)
    source_quality = _source_quality_by_family(args.source_quality)
    allocations = []
    for fam in registry.get("families") or []:
        family = str(fam.get("family") or "")
        score = _score_family(fam)
        status = str(fam.get("status") or "")
        sq = source_quality.get(family) or {}
        source_loss_pressure = float(sq.get("source_loss_pressure") or 0.0)
        source_throttle = bool(sq.get("throttle_source_binding"))
        source_hold = bool(sq.get("hold_source_binding"))
        score -= source_loss_pressure
        if status in {"superseded_family", "seed_hold"}:
            action = "do_not_spend_until_new_evidence"
        elif source_hold:
            action = "hold_source_binding_until_new_target_evidence"
        elif source_throttle:
            action = "repair_source_strategy_before_more_binding"
        elif status == "candidate_family":
            action = "seek_heldout_validation"
        elif status == "seed_only":
            action = "seek_sibling_or_hold"
        elif status == "inventory_only":
            action = "seek_first_useful_exit_or_retire"
        else:
            action = "review"
        allocations.append({
            "family": family,
            "status": status,
            "yield_score": round(score, 3),
            "base_yield_score": round(_score_family(fam), 3),
            "source_loss_pressure": round(source_loss_pressure, 3),
            "source_quality": sq,
            "next_required_evidence": fam.get("next_required_evidence"),
            "recommended_action": action,
            "negative_control_pass_rate": fam.get("negative_control_pass_rate"),
            "median_drain_time_s": fam.get("median_drain_time_s"),
        })
    allocations.sort(key=lambda x: (-float(x.get("yield_score") or 0), str(x.get("family") or "")))
    payload = {
        "schema": "leanmill-source-family-allocator-v1",
        "registry": args.registry,
        "source_quality": args.source_quality,
        "reward": REWARD,
        "allocation_count": len(allocations),
        "allocations": allocations,
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _self_test() -> int:
    payload = build(argparse.Namespace(registry="/tmp/no_such_registry.json", source_quality="/tmp/no_such_quality.json", out=None))
    assert payload["allocation_count"] == 0
    print("leanmill_source_family_allocator self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default=DEFAULT_REGISTRY)
    ap.add_argument("--source-quality", default=DEFAULT_SOURCE_QUALITY)
    ap.add_argument("--out")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    payload = build(args)
    print(json.dumps({"allocation_count": payload["allocation_count"], "out": args.out}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
