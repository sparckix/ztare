#!/usr/bin/env python3
"""Score frozen Lean action-routing predictions against governed labels.

Inputs:
  - prediction JSONL from lean_action_routing_predict.py
  - decider checkpoint JSONL from four_arm_wedge.py

No Lean, no Codex. This is a pure adjudication utility.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

ACTIONS = [
    "use_governed_static_agentic",
    "use_feedback_agentic",
    "defer_or_abstain",
]


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines()
            if line.strip()]


def _valid(row: dict[str, Any]) -> set[str]:
    b_ok = bool((row.get("B1gs") or {}).get("ratified"))
    a_ok = bool((row.get("A") or {}).get("ratified"))
    valid: list[str] = []
    if b_ok:
        valid.append("use_governed_static_agentic")
    if a_ok:
        valid.append("use_feedback_agentic")
    return set(valid or ["defer_or_abstain"])


def _route(row: dict[str, Any]) -> str:
    b_ok = bool((row.get("B1gs") or {}).get("ratified"))
    a_ok = bool((row.get("A") or {}).get("ratified"))
    if a_ok and b_ok:
        return "multiple_actions_close"
    if a_ok:
        return "feedback_only_win"
    if b_ok:
        return "static_only_win"
    return "no_observed_action_closes"


def _utility(row: dict[str, Any], action: str) -> float:
    if action in _valid(row):
        return 0.35 if action == "defer_or_abstain" else 1.0
    if action == "defer_or_abstain":
        return -0.20
    if _route(row) == "no_observed_action_closes":
        return -0.30
    return -0.50


def score(predictions: Path, ckpt: Path, out: Path | None = None) -> dict[str, Any]:
    preds = {r["unit_id"]: r for r in _load_jsonl(predictions)}
    rows = _load_jsonl(ckpt)
    scored = []
    for row in rows:
        pred = preds.get(row["id"])
        if not pred:
            continue
        action = pred["predicted_action"]
        scored.append({
            "id": row["id"],
            "predicted": action,
            "valid": sorted(_valid(row)),
            "route": _route(row),
            "correct": action in _valid(row),
            "utility": _utility(row, action),
            "has_proofstate_features": pred.get("has_proofstate_features"),
        })
    if not scored:
        raise SystemExit("no overlapping rows between predictions and ckpt")
    baselines = {}
    for action in ACTIONS:
        correct = sum(action in _valid(r) for r in rows if r["id"] in preds)
        util = sum(_utility(r, action) for r in rows if r["id"] in preds)
        baselines[f"always_{action}"] = {
            "correct": correct,
            "accuracy": round(correct / len(scored), 3),
            "utility": round(util, 3),
            "utility_per_row": round(util / len(scored), 3),
        }
    total_util = sum(r["utility"] for r in scored)
    out_obj = {
        "predictions": str(predictions),
        "ckpt": str(ckpt),
        "n": len(scored),
        "route_counts": dict(Counter(r["route"] for r in scored)),
        "prediction_counts": dict(Counter(r["predicted"] for r in scored)),
        "prediction_correct": sum(r["correct"] for r in scored),
        "prediction_accuracy": round(sum(r["correct"] for r in scored) / len(scored), 3),
        "prediction_utility": round(total_util, 3),
        "prediction_utility_per_row": round(total_util / len(scored), 3),
        "baselines": baselines,
        "rows": scored,
    }
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(out_obj, indent=1, sort_keys=True) + "\n")
    return out_obj


def self_test() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        pred = root / "pred.jsonl"
        ckpt = root / "ckpt.jsonl"
        pred.write_text("\n".join([
            json.dumps({"unit_id": "a", "predicted_action": "use_feedback_agentic"}),
            json.dumps({"unit_id": "b", "predicted_action": "defer_or_abstain"}),
        ]) + "\n")
        ckpt.write_text("\n".join([
            json.dumps({"id": "a", "B1gs": {"ratified": 0}, "A": {"ratified": 1}}),
            json.dumps({"id": "b", "B1gs": {"ratified": 0}, "A": {"ratified": 0}}),
        ]) + "\n")
        out = score(pred, ckpt)
        assert out["prediction_correct"] == 2
        assert out["route_counts"]["feedback_only_win"] == 1
        assert out["route_counts"]["no_observed_action_closes"] == 1
    print("lean_action_routing_score_predictions self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--predictions")
    ap.add_argument("--ckpt")
    ap.add_argument("--out")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if not args.predictions or not args.ckpt:
        ap.error("--predictions and --ckpt are required unless --self-test is set")
    out = score(Path(args.predictions), Path(args.ckpt),
                Path(args.out) if args.out else None)
    print(json.dumps(out, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
