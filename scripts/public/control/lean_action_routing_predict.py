#!/usr/bin/env python3
"""Predict Lean action routes for unlabeled rows from a labeled routing set.

This freezes Path-A routing predictions before any new solver spend.
It trains only on the existing hidden labels, reads visible pre-attempt
features for new rows, and writes a JSONL prediction packet with nearest
neighbors and action choices. No Lean, no Codex, no proof search.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
CTL = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(CTL))

import lean_action_routing_dataset as ds  # noqa: E402
import lean_action_routing_eval as ev  # noqa: E402


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines()
            if line.strip()]


def _proofstate_by_row(path: Path | None) -> dict[str, dict[str, Any]]:
    if not path or not path.exists():
        return {}
    out: dict[str, dict[str, Any]] = {}
    for rec in _load_jsonl(path):
        if rec.get("status") == "ok" and isinstance(rec.get("features"), dict):
            out[str(rec.get("row_id"))] = rec["features"]
    return out


def _labeled_rows(data_dir: Path) -> list[dict[str, Any]]:
    manifest = _load_jsonl(data_dir / "lean_routing_manifest.jsonl")
    key = {r["unit_id"]: r for r in _load_jsonl(data_dir / "lean_routing_key.jsonl")}
    return [{"manifest": m, "key": key[m["unit_id"]]} for m in manifest
            if m["unit_id"] in key]


def _unlabeled_rows(corpus: Path, proofstate_features: Path | None) -> list[dict[str, Any]]:
    rows = ds._load_frozen_corpus(corpus)
    ps_by_row = _proofstate_by_row(proofstate_features)
    out: list[dict[str, Any]] = []
    for unit_id, row in rows.items():
        visible = ds._visible_packet({"id": unit_id}, row)
        if unit_id in ps_by_row:
            visible["visible_features"].update({
                f"ps_{k}": v for k, v in ps_by_row[unit_id].items()
                if k != "type_head_top"
            })
            top = ps_by_row[unit_id].get("type_head_top") or {}
            if isinstance(top, dict):
                for head, n in list(top.items())[:8]:
                    safe = re.sub(r"[^A-Za-z0-9_]", "_", str(head)).strip("_")
                    if safe:
                        visible["visible_features"][f"ps_type_{safe}"] = int(n)
        out.append({
            "manifest": {
                "unit_id": unit_id,
                "visible_packet": visible,
                "candidate_actions": list(ev.DEFAULT_ACTIONS),
                "split": "unlabeled",
            },
            "source_row": row,
        })
    return out


def _choose_from_neighbors(nbrs: list[dict[str, Any]], actions: tuple[str, ...]) -> str:
    scores = {
        a: (sum(1 for r in nbrs if a in ev._valid(r)),
            sum(ev._utility(r, a) for r in nbrs))
        for a in actions
    }
    return max(actions, key=lambda a: (scores[a][0], scores[a][1], -actions.index(a)))


def predict(data_dir: Path, corpus: Path, proofstate_features: Path | None,
            out: Path, k: int) -> dict[str, Any]:
    labeled = _labeled_rows(data_dir)
    unlabeled = _unlabeled_rows(corpus, proofstate_features)
    actions = ev._actions(labeled)
    names = ev._feature_names(labeled + unlabeled)  # same visible feature space
    train = [r for r in labeled if r["manifest"].get("split") == "train"]
    if not train:
        raise SystemExit("no train rows in labeled data")
    out.parent.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    with out.open("w") as fh:
        for row in unlabeled:
            rv = ev._vec(row, names)
            nbrs = sorted(train, key=lambda r: ev._dist(rv, ev._vec(r, names)))[:k]
            action = _choose_from_neighbors(nbrs, actions)
            counts[action] = counts.get(action, 0) + 1
            rec = {
                "unit_id": row["manifest"]["unit_id"],
                "predicted_action": action,
                "policy": f"nearest{k}_train",
                "has_proofstate_features": int(
                    "ps_goal_chars" in row["manifest"]["visible_packet"]["visible_features"]),
                "neighbors": [
                    {
                        "unit_id": n["manifest"]["unit_id"],
                        "valid_actions": sorted(ev._valid(n)),
                        "route": ev._route(n),
                        "distance": round(ev._dist(rv, ev._vec(n, names)), 4),
                    }
                    for n in nbrs
                ],
            }
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
    summary = {
        "data_dir": str(data_dir),
        "corpus": str(corpus),
        "proofstate_features": str(proofstate_features) if proofstate_features else None,
        "out": str(out),
        "k": k,
        "n": len(unlabeled),
        "prediction_counts": counts,
    }
    return summary


def self_test() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        data = root / "data"
        data.mkdir()
        (data / "lean_routing_manifest.jsonl").write_text("\n".join([
            json.dumps({"unit_id": "a", "split": "train",
                        "visible_packet": {"visible_features": {"x": 0}}}),
            json.dumps({"unit_id": "b", "split": "train",
                        "visible_packet": {"visible_features": {"x": 1}}}),
        ]) + "\n")
        (data / "lean_routing_key.jsonl").write_text("\n".join([
            json.dumps({"unit_id": "a", "valid_actions": ["defer_or_abstain"],
                        "gold_route_class": "no_observed_action_closes"}),
            json.dumps({"unit_id": "b", "valid_actions": ["use_feedback_agentic"],
                        "gold_route_class": "feedback_only_win"}),
        ]) + "\n")
        corpus = root / "corpus.json"
        corpus.write_text(json.dumps({"rows": [
            {"id": "u", "target_name": "u", "sorried_file": str(root / "u.lean"),
             "target_line": 1}
        ]}) + "\n")
        ps = root / "ps.jsonl"
        ps.write_text(json.dumps({"row_id": "u", "status": "ok",
                                  "features": {"goal_chars": 1}}) + "\n")
        summary = predict(data, corpus, ps, root / "pred.jsonl", 1)
        assert summary["n"] == 1
        assert (root / "pred.jsonl").exists()
    print("lean_action_routing_predict self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir")
    ap.add_argument("--corpus")
    ap.add_argument("--proofstate-features")
    ap.add_argument("--out")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if not args.data_dir or not args.corpus or not args.out:
        ap.error("--data-dir, --corpus, and --out are required unless --self-test is set")
    summary = predict(Path(args.data_dir), Path(args.corpus),
                      Path(args.proofstate_features) if args.proofstate_features else None,
                      Path(args.out), args.k)
    print(json.dumps(summary, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
