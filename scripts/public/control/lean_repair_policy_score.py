#!/usr/bin/env python3
"""Score repair-policy signal from Path-A repair trajectories.

This is the cheap experiment before any new solver spend. Given
repair-trajectory rows, evaluate whether visible error/repair classes
can select a useful next repair on held-out targets.

Unit of evaluation: target. Candidate actions are the observed repair
attempt records for that target. Leave-one-target-out avoids training
on another round from the same theorem. Optional routing score files
can restrict evaluation to discriminative rows only.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DEFAULT_DATASET = "/tmp/rung1/lean_repair_trajectory_dataset_rich.jsonl"
DEFAULT_SCORE = "/tmp/rung1/lean_repair_policy_score.json"
DISCRIMINATIVE_ROUTES = {
    "static_only_win",
    "feedback_only_win",
    "external_backend_only_win",
    "no_observed_action_closes",
}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(errors="ignore").splitlines()
            if line.strip()]


def _positive(rec: dict[str, Any]) -> bool:
    hidden = rec.get("hidden") or {}
    return bool(hidden.get("ratified") or hidden.get("label_closure_or_exact_gap"))


def _target(rec: dict[str, Any]) -> str:
    return str((rec.get("visible") or {}).get("target") or rec.get("target") or "")


def _features(rec: dict[str, Any]) -> dict[str, str]:
    v = rec.get("visible") or {}
    return {
        "repair_class": str(v.get("repair_class") or "missing"),
        "error_class": str(v.get("error_class") or "missing"),
        "arm": str(v.get("arm") or "missing"),
        "failed_tactic_family": str(v.get("failed_tactic_family") or "missing"),
    }


def _key(rec: dict[str, Any], policy: str) -> tuple[str, ...]:
    f = _features(rec)
    if policy == "repair_class":
        return (f["repair_class"],)
    if policy == "error_repair":
        return (f["error_class"], f["repair_class"])
    if policy == "error_repair_arm":
        return (f["error_class"], f["repair_class"], f["arm"])
    if policy == "full_visible":
        return (f["error_class"], f["repair_class"], f["failed_tactic_family"], f["arm"])
    raise ValueError(policy)


def _discriminative_targets(path: Path | None) -> set[str] | None:
    if not path:
        return None
    if not path.exists():
        raise SystemExit(f"routing score file missing: {path}")
    data = json.loads(path.read_text(errors="ignore"))
    rows = data.get("rows") or []
    return {str(r.get("id")) for r in rows
            if str(r.get("route")) in DISCRIMINATIVE_ROUTES}


def _utility(target_has_positive: bool, chosen: dict[str, Any] | None) -> float:
    if chosen is None:
        return 0.35 if not target_has_positive else -0.20
    if _positive(chosen):
        return 1.0
    return -0.30 if not target_has_positive else -0.50


def _fit_priors(train: list[dict[str, Any]], policy: str) -> dict[tuple[str, ...], float]:
    counts: dict[tuple[str, ...], Counter[str]] = defaultdict(Counter)
    for rec in train:
        counts[_key(rec, policy)]["pos" if _positive(rec) else "neg"] += 1
    priors: dict[tuple[str, ...], float] = {}
    for k, c in counts.items():
        # Laplace smoothing keeps sparse classes from becoming brittle.
        priors[k] = (c["pos"] + 1) / (c["pos"] + c["neg"] + 2)
    return priors


def _choose_by_prior(cands: list[dict[str, Any]], train: list[dict[str, Any]],
                     policy: str, threshold: float) -> tuple[dict[str, Any] | None, float]:
    priors = _fit_priors(train, policy)
    global_pos = (sum(_positive(r) for r in train) + 1) / (len(train) + 2) if train else 0.5
    best: dict[str, Any] | None = None
    best_score = -1.0
    for rec in cands:
        score = priors.get(_key(rec, policy), global_pos)
        if score > best_score:
            best = rec
            best_score = score
    if best_score < threshold:
        return None, best_score
    return best, best_score


def _choose_best_train_repair(cands: list[dict[str, Any]], train: list[dict[str, Any]],
                              threshold: float) -> tuple[dict[str, Any] | None, float]:
    return _choose_by_prior(cands, train, "repair_class", threshold)


def score(dataset: Path, out: Path | None = None,
          routing_score: Path | None = None,
          thresholds: list[float] | None = None,
          exclude_error_class: set[str] | None = None,
          include_error_class: set[str] | None = None) -> dict[str, Any]:
    thresholds = thresholds or [0.0, 0.25, 0.5, 0.67]
    exclude_error_class = exclude_error_class or set()
    include_error_class = include_error_class or set()
    records = []
    for r in _load_jsonl(dataset):
        if not _target(r):
            continue
        err = str((r.get("visible") or {}).get("error_class") or "")
        if exclude_error_class and err in exclude_error_class:
            continue
        if include_error_class and err not in include_error_class:
            continue
        records.append(r)
    filt = _discriminative_targets(routing_score)
    by_target: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in records:
        t = _target(rec)
        if filt is not None and t not in filt:
            continue
        by_target[t].append(rec)
    if not by_target:
        raise SystemExit("no records after target filtering")

    target_rows = []
    policies = ["repair_class", "error_repair", "error_repair_arm", "full_visible"]
    per_policy: dict[str, list[dict[str, Any]]] = {p: [] for p in policies}
    baseline_rows: dict[str, list[dict[str, Any]]] = {
        "always_abstain": [],
        "first_observed": [],
        "oracle": [],
    }
    threshold_rows: dict[str, list[dict[str, Any]]] = {
        f"{p}@{thr:g}": [] for p in policies for thr in thresholds
    }

    for target, cands in sorted(by_target.items()):
        train = [r for t, rs in by_target.items() if t != target for r in rs]
        has_pos = any(_positive(r) for r in cands)
        target_rows.append({
            "target": target,
            "candidate_count": len(cands),
            "positive_count": sum(_positive(r) for r in cands),
            "has_positive": has_pos,
            "repair_classes": sorted(set(_features(r)["repair_class"] for r in cands)),
            "error_classes": sorted(set(_features(r)["error_class"] for r in cands)),
        })
        baseline_choices = {
            "always_abstain": None,
            "first_observed": cands[0],
            "oracle": next((r for r in cands if _positive(r)), None),
        }
        for name, choice in baseline_choices.items():
            baseline_rows[name].append({
                "target": target,
                "chosen": None if choice is None else choice["trace_id"],
                "success": bool(choice is not None and _positive(choice)) or (choice is None and not has_pos),
                "utility": _utility(has_pos, choice),
            })
        for p in policies:
            for thr in thresholds:
                choice, prior = _choose_by_prior(cands, train, p, thr)
                threshold_rows[f"{p}@{thr:g}"].append({
                    "target": target,
                    "chosen": None if choice is None else choice["trace_id"],
                    "chosen_repair_class": None if choice is None else _features(choice)["repair_class"],
                    "chosen_error_class": None if choice is None else _features(choice)["error_class"],
                    "prior": round(prior, 4),
                    "success": bool(choice is not None and _positive(choice)) or (choice is None and not has_pos),
                    "utility": _utility(has_pos, choice),
                })

    def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
        util = sum(float(r["utility"]) for r in rows)
        return {
            "n": len(rows),
            "success": sum(bool(r["success"]) for r in rows),
            "accuracy": round(sum(bool(r["success"]) for r in rows) / len(rows), 3) if rows else 0.0,
            "utility": round(util, 3),
            "utility_per_target": round(util / len(rows), 3) if rows else 0.0,
        }

    baseline_summary = {k: summarize(v) for k, v in baseline_rows.items()}
    policy_summary = {k: summarize(v) for k, v in threshold_rows.items()}
    best_policy_name, best_policy = max(policy_summary.items(),
                                        key=lambda kv: (kv[1]["utility"], kv[1]["accuracy"]))
    out_obj = {
        "schema": "path-a-repair-policy-score-v1",
        "dataset": str(dataset),
        "routing_score_filter": str(routing_score) if routing_score else None,
        "exclude_error_class": sorted(exclude_error_class),
        "include_error_class": sorted(include_error_class),
        "n_records": len(records),
        "n_targets": len(by_target),
        "positive_targets": sum(any(_positive(r) for r in rs) for rs in by_target.values()),
        "baseline_summary": baseline_summary,
        "policy_summary": policy_summary,
        "best_policy": {"name": best_policy_name, **best_policy},
        "target_rows": target_rows,
        "rows_by_policy": {**baseline_rows, **threshold_rows},
        "interpretation": (
            "PASS only if best learned repair policy beats first_observed and "
            "always_abstain utility on the chosen evaluation slice. Otherwise "
            "repair-class routing has not earned new solver spend."
        ),
    }
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(out_obj, indent=1, sort_keys=True) + "\n")
    return out_obj


def self_test() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        ds = root / "ds.jsonl"
        score_p = root / "score.json"
        rows = [
            {"trace_id": "a1", "visible": {"target": "a", "repair_class": "simp", "error_class": "timeout", "arm": "A", "failed_tactic_family": "simp"}, "hidden": {"ratified": 1}},
            {"trace_id": "a2", "visible": {"target": "a", "repair_class": "struct", "error_class": "timeout", "arm": "B", "failed_tactic_family": "structure"}, "hidden": {"ratified": 0}},
            {"trace_id": "b1", "visible": {"target": "b", "repair_class": "simp", "error_class": "timeout", "arm": "A", "failed_tactic_family": "simp"}, "hidden": {"ratified": 1}},
            {"trace_id": "c1", "visible": {"target": "c", "repair_class": "struct", "error_class": "type", "arm": "A", "failed_tactic_family": "structure"}, "hidden": {"ratified": 0}},
        ]
        ds.write_text("".join(json.dumps(r) + "\n" for r in rows))
        score_p.write_text(json.dumps({"rows": [
            {"id": "a", "route": "feedback_only_win"},
            {"id": "b", "route": "multiple_actions_close"},
            {"id": "c", "route": "no_observed_action_closes"},
        ]}))
        out = score(ds, routing_score=score_p, thresholds=[0.0, 0.5])
        assert out["n_targets"] == 2
        assert out["positive_targets"] == 1
        assert "repair_class@0" in out["policy_summary"]
        out2 = score(ds, thresholds=[0.0], exclude_error_class={"timeout"})
        assert out2["n_records"] == 1
        assert out2["n_targets"] == 1
    print("lean_repair_policy_score self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default=DEFAULT_DATASET)
    ap.add_argument("--routing-score")
    ap.add_argument("--out", default=DEFAULT_SCORE)
    ap.add_argument("--thresholds", default="0,0.25,0.5,0.67")
    ap.add_argument("--exclude-error-class", action="append", default=[])
    ap.add_argument("--include-error-class", action="append", default=[])
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    thresholds = [float(x) for x in args.thresholds.split(",") if x.strip()]
    result = score(Path(args.dataset), Path(args.out) if args.out else None,
                   Path(args.routing_score) if args.routing_score else None,
                   thresholds,
                   set(args.exclude_error_class or []),
                   set(args.include_error_class or []))
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
