#!/usr/bin/env python3
"""Mine the discriminative void in Lean action-routing validations.

The routing problem is not "classify all rows"; most rows can be
closed by both arms and teach little. This script extracts the rows
where routing can matter:
  - static_only_win
  - feedback_only_win
  - no_observed_action_closes

It then emits a compact feature table and pattern hypotheses for the
next Path-A mechanism. No Lean, no Codex.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


FEATURE_KEYS = [
    "hyp_count", "ctx_lines", "target_chars", "target_token_count",
    "arrow_count", "binder_like_count", "has_forall", "has_exists",
    "has_implication", "has_equality", "has_order", "has_sum",
    "has_tendsto", "has_integral", "has_set", "has_norm",
    "has_real", "has_nat_int",
]


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines()
            if line.strip()]


def _feature_by_row(path: Path | None) -> dict[str, dict[str, Any]]:
    if not path or not path.exists():
        return {}
    out = {}
    for rec in _load_jsonl(path):
        if rec.get("status") == "ok" and isinstance(rec.get("features"), dict):
            out[rec["row_id"]] = rec["features"]
    return out


def _route_from_valid(valid: list[str]) -> str:
    s = set(valid)
    if s == {"use_governed_static_agentic", "use_feedback_agentic"}:
        return "multiple_actions_close"
    if s == {"use_governed_static_agentic"}:
        return "static_only_win"
    if s == {"use_feedback_agentic"}:
        return "feedback_only_win"
    if s == {"defer_or_abstain"}:
        return "no_observed_action_closes"
    return "unknown"


def _bucket(v: Any, cuts: tuple[int, int]) -> str:
    try:
        x = int(v)
    except Exception:
        return "missing"
    if x <= cuts[0]:
        return "low"
    if x <= cuts[1]:
        return "mid"
    return "high"


def mine(score: Path, features: Path | None, out: Path | None = None) -> dict[str, Any]:
    s = json.loads(score.read_text())
    f_by = _feature_by_row(features)
    rows = []
    all_rows = s.get("rows") or []
    for row in all_rows:
        route = row.get("route") or _route_from_valid(row.get("valid") or [])
        if route == "multiple_actions_close":
            continue
        feats = f_by.get(row["id"]) or {}
        compact = {k: feats.get(k) for k in FEATURE_KEYS}
        rows.append({
            "id": row["id"],
            "route": route,
            "predicted": row.get("predicted"),
            "correct": bool(row.get("correct")),
            "has_proofstate_features": row.get("has_proofstate_features"),
            "features": compact,
            "type_head_top": feats.get("type_head_top"),
            "feature_signature": {
                "hyp_bucket": _bucket(feats.get("hyp_count"), (8, 20)),
                "target_token_bucket": _bucket(feats.get("target_token_count"), (12, 25)),
                "arrow_bucket": _bucket(feats.get("arrow_count"), (1, 4)),
                "has_order": feats.get("has_order"),
                "has_sum": feats.get("has_sum"),
                "has_integral": feats.get("has_integral"),
                "has_norm": feats.get("has_norm"),
            },
        })
    by_route = Counter(r["route"] for r in rows)
    misses = [r for r in rows if not r["correct"]]
    hypotheses = [
        {
            "name": "easy-row dominance masks routing signal",
            "evidence": (
                f"{s.get('route_counts', {}).get('multiple_actions_close', 0)} "
                "rows were closable by both arms; discriminative rows are the minority."
            ),
            "next_test": "Train/evaluate only on discriminative labels, or use a two-stage easy-vs-discriminative gate.",
        },
        {
            "name": "nearest-neighbor optimizes surface similarity, not failure mode",
            "evidence": (
                f"{len(misses)}/{len(rows)} discriminative rows were missed by the frozen predictor."
            ),
            "next_test": "Replace kNN with explicit residual classes: easy-static, hard-open, feedback-needed.",
        },
        {
            "name": "missing proof-state features create false confidence",
            "evidence": (
                f"{sum(1 for r in rows if not r.get('has_proofstate_features'))}/"
                f"{len(rows)} discriminative rows lacked proof-state features."
            ),
            "next_test": "Fallback missing-feature rows to abstain/defer, not nearest-neighbor over statement features.",
        },
    ]
    out_obj = {
        "score": str(score),
        "features": str(features) if features else None,
        "n_total_scored": s.get("n"),
        "n_discriminative": len(rows),
        "route_counts": dict(by_route),
        "prediction_accuracy_on_discriminative": (
            round(sum(r["correct"] for r in rows) / len(rows), 3) if rows else 0.0),
        "rows": rows,
        "pattern_hypotheses": hypotheses,
    }
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(out_obj, indent=1, sort_keys=True) + "\n")
    return out_obj


def self_test() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        score = root / "score.json"
        feats = root / "features.jsonl"
        score.write_text(json.dumps({
            "n": 2,
            "route_counts": {"multiple_actions_close": 1, "static_only_win": 1},
            "rows": [
                {"id": "a", "route": "multiple_actions_close", "correct": True},
                {"id": "b", "route": "static_only_win", "predicted": "defer_or_abstain", "correct": False},
            ],
        }) + "\n")
        feats.write_text(json.dumps({
            "row_id": "b", "status": "ok",
            "features": {"hyp_count": 3, "target_token_count": 8, "has_order": 1},
        }) + "\n")
        out = mine(score, feats)
        assert out["n_discriminative"] == 1
        assert out["prediction_accuracy_on_discriminative"] == 0.0
    print("lean_action_routing_mine_void self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--score")
    ap.add_argument("--features")
    ap.add_argument("--out")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if not args.score:
        ap.error("--score is required unless --self-test is set")
    out = mine(Path(args.score), Path(args.features) if args.features else None,
               Path(args.out) if args.out else None)
    print(json.dumps(out, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
