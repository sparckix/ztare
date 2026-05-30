#!/usr/bin/env python3
"""Two-stage Lean action router over proof-state features.

Stage 1 gates easy rows: predict whether both A and B1gs are likely to
close. If yes, choose the cheaper governed static action.

Stage 2 only handles the void where routing matters: static-only,
feedback-only, or no-observed-close. This directly encodes the residual
mining result from the 14-row validation: easy rows dominated the label
space and made one-stage kNN learn surface similarity, not failure mode.

No Lean, no Codex. This is an offline policy artifact.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
CTL = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(CTL))

import lean_action_routing_dataset as ds  # noqa: E402
import lean_action_routing_eval as ev  # noqa: E402
import lean_action_routing_score_predictions as sp  # noqa: E402

EASY_ACTION = "use_governed_static_agentic"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines()
            if line.strip()]


def _training_rows(data_dir: Path) -> list[dict[str, Any]]:
    return ev._rows(data_dir)


def _proofstate_by_row(path: Path | None) -> dict[str, dict[str, Any]]:
    if not path or not path.exists():
        return {}
    out: dict[str, dict[str, Any]] = {}
    for rec in _load_jsonl(path):
        if rec.get("status") == "ok" and isinstance(rec.get("features"), dict):
            out[str(rec.get("row_id"))] = rec["features"]
    return out


def _visible_rows(corpus: Path, proofstate_features: Path | None) -> list[dict[str, Any]]:
    corpus_by = ds._load_frozen_corpus(corpus)
    ps_by = _proofstate_by_row(proofstate_features)
    rows: list[dict[str, Any]] = []
    for unit_id, row in corpus_by.items():
        visible = ds._visible_packet({"id": unit_id}, row)
        if unit_id in ps_by:
            visible["visible_features"].update({
                f"ps_{k}": v for k, v in ps_by[unit_id].items()
                if k != "type_head_top"
            })
            top = ps_by[unit_id].get("type_head_top") or {}
            if isinstance(top, dict):
                for head, n in list(top.items())[:8]:
                    safe = re.sub(r"[^A-Za-z0-9_]", "_", str(head)).strip("_")
                    if safe:
                        visible["visible_features"][f"ps_type_{safe}"] = int(n)
        rows.append({
            "manifest": {
                "unit_id": unit_id,
                "split": "unlabeled",
                "candidate_actions": list(ev.DEFAULT_ACTIONS),
                "visible_packet": visible,
            }
        })
    return rows


def _is_easy(row: dict[str, Any]) -> bool:
    return ev._route(row) == "multiple_actions_close"


def _action_for_route(route: str) -> str:
    if route == "feedback_only_win":
        return "use_feedback_agentic"
    if route == "static_only_win":
        return "use_governed_static_agentic"
    if route == "no_observed_action_closes":
        return "defer_or_abstain"
    return EASY_ACTION


def _predict_one(row: dict[str, Any], train: list[dict[str, Any]],
                 names: list[str], *, k_easy: int, k_void: int,
                 easy_threshold: float, missing_policy: str) -> dict[str, Any]:
    feats = ev._features(row)
    has_ps = "ps_goal_chars" in feats
    if not has_ps and missing_policy != "nearest":
        action = missing_policy
        return {
            "predicted_action": action,
            "stage": "missing_proofstate_fallback",
            "easy_neighbor_rate": None,
            "neighbors": [],
            "has_proofstate_features": 0,
        }

    rv = ev._vec(row, names)
    nearest = sorted(train, key=lambda r: ev._dist(rv, ev._vec(r, names)))
    easy_nbrs = nearest[:k_easy]
    easy_rate = (sum(1 for r in easy_nbrs if _is_easy(r)) / len(easy_nbrs)
                 if easy_nbrs else 0.0)
    if easy_rate >= easy_threshold:
        return {
            "predicted_action": EASY_ACTION,
            "stage": "easy_both_close_gate",
            "easy_neighbor_rate": round(easy_rate, 3),
            "neighbors": _neighbor_packet(easy_nbrs, rv, names),
            "has_proofstate_features": int(has_ps),
        }

    void_train = [r for r in train if not _is_easy(r)]
    pool = sorted(void_train or train, key=lambda r: ev._dist(rv, ev._vec(r, names)))[:k_void]
    route_counts = Counter(ev._route(r) for r in pool)
    if not pool:
        action = "defer_or_abstain"
    else:
        route = max(route_counts, key=lambda rt: (route_counts[rt], -str(rt).count("z")))
        action = _action_for_route(route)
    return {
        "predicted_action": action,
        "stage": "void_route",
        "easy_neighbor_rate": round(easy_rate, 3),
        "void_route_counts": dict(route_counts),
        "neighbors": _neighbor_packet(pool, rv, names),
        "has_proofstate_features": int(has_ps),
    }


def _neighbor_packet(rows: list[dict[str, Any]], rv: list[float],
                     names: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "unit_id": r["manifest"]["unit_id"],
            "route": ev._route(r),
            "valid_actions": sorted(ev._valid(r)),
            "distance": round(ev._dist(rv, ev._vec(r, names)), 4),
        }
        for r in rows
    ]


def predict(data_dir: Path, corpus: Path, proofstate_features: Path | None,
            out: Path, *, k_easy: int, k_void: int, easy_threshold: float,
            missing_policy: str) -> dict[str, Any]:
    train = _training_rows(data_dir)
    visible = _visible_rows(corpus, proofstate_features)
    names = ev._feature_names(train + visible)
    out.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter()
    stages = Counter()
    with out.open("w") as fh:
        for row in visible:
            pred = _predict_one(row, train, names, k_easy=k_easy,
                                k_void=k_void,
                                easy_threshold=easy_threshold,
                                missing_policy=missing_policy)
            rec = {
                "unit_id": row["manifest"]["unit_id"],
                "policy": "two_stage_easy_then_void",
                **pred,
            }
            counts[rec["predicted_action"]] += 1
            stages[rec["stage"]] += 1
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
    return {
        "data_dir": str(data_dir),
        "corpus": str(corpus),
        "proofstate_features": str(proofstate_features) if proofstate_features else None,
        "out": str(out),
        "n": len(visible),
        "k_easy": k_easy,
        "k_void": k_void,
        "easy_threshold": easy_threshold,
        "missing_policy": missing_policy,
        "prediction_counts": dict(counts),
        "stage_counts": dict(stages),
    }


def score(data_dir: Path, corpus: Path, proofstate_features: Path | None,
          ckpt: Path, out: Path, *, k_easy: int, k_void: int,
          easy_threshold: float, missing_policy: str) -> dict[str, Any]:
    pred_path = out.with_suffix(".predictions.jsonl")
    summary = predict(data_dir, corpus, proofstate_features, pred_path,
                      k_easy=k_easy, k_void=k_void,
                      easy_threshold=easy_threshold,
                      missing_policy=missing_policy)
    scored = sp.score(pred_path, ckpt, out)
    scored["two_stage_config"] = {
        "k_easy": k_easy,
        "k_void": k_void,
        "easy_threshold": easy_threshold,
        "missing_policy": missing_policy,
    }
    scored["prediction_summary"] = summary
    out.write_text(json.dumps(scored, indent=1, sort_keys=True) + "\n")
    return scored


def self_test() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        data = root / "data"
        data.mkdir()
        (data / "lean_routing_manifest.jsonl").write_text("\n".join([
            json.dumps({"unit_id": "easy", "split": "train", "candidate_actions": ev.DEFAULT_ACTIONS,
                        "visible_packet": {"visible_features": {"ps_goal_chars": 10, "x": 0}}}),
            json.dumps({"unit_id": "hard", "split": "train", "candidate_actions": ev.DEFAULT_ACTIONS,
                        "visible_packet": {"visible_features": {"ps_goal_chars": 20, "x": 1}}}),
        ]) + "\n")
        (data / "lean_routing_key.jsonl").write_text("\n".join([
            json.dumps({"unit_id": "easy", "valid_actions": [
                "use_governed_static_agentic", "use_feedback_agentic"],
                "gold_route_class": "multiple_actions_close"}),
            json.dumps({"unit_id": "hard", "valid_actions": ["defer_or_abstain"],
                        "gold_route_class": "no_observed_action_closes"}),
        ]) + "\n")
        corpus = root / "corpus.json"
        src = root / "u.lean"
        src.write_text("theorem u : True := by\n  sorry\n")
        corpus.write_text(json.dumps({"rows": [
            {"id": "u", "target_name": "u", "sorried_file": str(src), "target_line": 1}
        ]}) + "\n")
        ps = root / "ps.jsonl"
        ps.write_text(json.dumps({"row_id": "u", "status": "ok",
                                  "features": {"goal_chars": 10}}) + "\n")
        out = root / "pred.jsonl"
        summary = predict(data, corpus, ps, out, k_easy=1, k_void=1,
                          easy_threshold=0.5,
                          missing_policy="defer_or_abstain")
        assert summary["prediction_counts"]["use_governed_static_agentic"] == 1
    print("lean_action_routing_two_stage self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir")
    ap.add_argument("--corpus")
    ap.add_argument("--proofstate-features")
    ap.add_argument("--ckpt", help="If provided, score predictions against labels")
    ap.add_argument("--out")
    ap.add_argument("--k-easy", type=int, default=3)
    ap.add_argument("--k-void", type=int, default=3)
    ap.add_argument("--easy-threshold", type=float, default=0.67)
    ap.add_argument("--missing-policy", default="defer_or_abstain",
                    choices=["defer_or_abstain", "use_governed_static_agentic",
                             "use_feedback_agentic", "nearest"])
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if not args.data_dir or not args.corpus or not args.out:
        ap.error("--data-dir, --corpus, and --out are required unless --self-test is set")
    if args.ckpt:
        result = score(Path(args.data_dir), Path(args.corpus),
                       Path(args.proofstate_features) if args.proofstate_features else None,
                       Path(args.ckpt), Path(args.out),
                       k_easy=args.k_easy, k_void=args.k_void,
                       easy_threshold=args.easy_threshold,
                       missing_policy=args.missing_policy)
    else:
        result = predict(Path(args.data_dir), Path(args.corpus),
                         Path(args.proofstate_features) if args.proofstate_features else None,
                         Path(args.out),
                         k_easy=args.k_easy, k_void=args.k_void,
                         easy_threshold=args.easy_threshold,
                         missing_policy=args.missing_policy)
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
