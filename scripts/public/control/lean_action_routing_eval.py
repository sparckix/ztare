#!/usr/bin/env python3
"""Offline policy evaluation for the Lean action-routing dataset.

This is deliberately cheap and measurement-only. It evaluates whether
any visible-information policy can choose among:
  - use_governed_static_agentic
  - use_feedback_agentic
  - defer_or_abstain

better than simple baselines on the hidden labels produced by
lean_action_routing_dataset.py. No Lean, no Codex, no prompt generation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

DEFAULT_DATA_DIR = "/tmp/rung1/lean_action_routing"
DEFAULT_OUT = "/tmp/rung1/lean_action_routing/lean_routing_eval.json"
DEFAULT_ACTIONS = (
    "use_governed_static_agentic",
    "use_feedback_agentic",
    "defer_or_abstain",
)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _rows(data_dir: Path) -> list[dict[str, Any]]:
    manifest = _load_jsonl(data_dir / "lean_routing_manifest.jsonl")
    key = {r["unit_id"]: r for r in _load_jsonl(data_dir / "lean_routing_key.jsonl")}
    out = []
    for m in manifest:
        k = key.get(m["unit_id"])
        if not k:
            raise SystemExit(f"missing key for {m['unit_id']}")
        out.append({"manifest": m, "key": k})
    return out


def _actions(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    seen: list[str] = []
    for r in rows:
        for a in r["manifest"].get("candidate_actions") or DEFAULT_ACTIONS:
            if a not in seen:
                seen.append(a)
    for a in DEFAULT_ACTIONS:
        if a not in seen:
            seen.append(a)
    return tuple(seen)


def _features(row: dict[str, Any]) -> dict[str, Any]:
    return row["manifest"]["visible_packet"].get("visible_features") or {}


def _num(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0


def _feature_names(rows: list[dict[str, Any]]) -> list[str]:
    names: set[str] = set()
    for r in rows:
        for k, v in _features(r).items():
            if isinstance(v, (int, float, bool)):
                names.add(k)
    return sorted(names)


def _vec(row: dict[str, Any], names: list[str]) -> list[float]:
    f = _features(row)
    out: list[float] = []
    for name in names:
        v = _num(f.get(name, 0))
        # crude robust scaling for tiny routing smoke: binary stays
        # binary, counts/lengths become log-ish buckets.
        if v > 1:
            v = min(v, 64.0) / 64.0
        out.append(v)
    return out


def _dist(a: list[float], b: list[float]) -> float:
    return sum(abs(x - y) for x, y in zip(a, b))


def _sig(row: dict[str, Any]) -> tuple:
    f = _features(row)
    return (
        int(f.get("has_integral_word", 0)),
        int(f.get("has_inequality_word", 0)),
        int(f.get("has_sum_token", 0)),
        int(f.get("has_tendsto_token", 0)),
        int(f.get("has_integral_token", 0)),
        int(f.get("has_order_token", 0)),
        int(f.get("has_nat_int_token", 0)),
        int(f.get("has_real_norm_token", 0)),
        int(f.get("has_forall_token", 0)),
        int(f.get("has_exists_token", 0)),
        min(int(f.get("arrow_count", 0)), 3),
        min(int(f.get("binder_count", 0)), 6),
        min(int(f.get("target_stmt_lines", 0)), 6),
        min(int(f.get("ps_hyp_count", 0)), 8),
        min(int(f.get("ps_ctx_lines", 0)), 8),
        min(int(f.get("ps_arrow_count", 0)), 4),
        min(int(f.get("ps_target_token_count", 0)), 30) // 5,
        int(f.get("ps_has_forall", 0)),
        int(f.get("ps_has_exists", 0)),
        int(f.get("ps_has_implication", 0)),
        int(f.get("ps_has_equality", 0)),
        int(f.get("ps_has_order", 0)),
        int(f.get("ps_has_sum", 0)),
        int(f.get("ps_has_tendsto", 0)),
        int(f.get("ps_has_integral", 0)),
        int(f.get("ps_has_set", 0)),
        int(f.get("ps_has_norm", 0)),
        int(f.get("ps_has_nat_int", 0)),
        int(f.get("ps_has_real", 0)),
    )


def _valid(row: dict[str, Any]) -> set[str]:
    return set(row["key"]["valid_actions"])


def _route(row: dict[str, Any]) -> str:
    return str(row["key"].get("gold_route_class"))


def _correct(row: dict[str, Any], action: str) -> bool:
    return action in _valid(row)


def _utility(row: dict[str, Any], action: str) -> float:
    """Cost-sensitive utility for selection work.

    Correct closure action: 1.0
    Correct defer on no observed closer: 0.35
    Wrong defer when a closer existed: -0.20
    Wrong solve action when no observed closer: -0.30
    Wrong solve action when another closer was required: -0.50
    """
    if _correct(row, action):
        return 0.35 if action == "defer_or_abstain" else 1.0
    if action == "defer_or_abstain":
        return -0.20
    if _route(row) == "no_observed_action_closes":
        return -0.30
    return -0.50


def _best_action(rows: list[dict[str, Any]], actions: tuple[str, ...]) -> str:
    if not rows:
        return actions[0]
    scores = {
        a: (sum(1 for r in rows if _correct(r, a)),
            sum(_utility(r, a) for r in rows))
        for a in actions
    }
    return max(actions, key=lambda a: (scores[a][0], scores[a][1], -actions.index(a)))


def _choose_valid(valid: set[str], fallback: str, actions: tuple[str, ...]) -> str:
    if fallback in valid:
        return fallback
    return max(actions, key=lambda a: (int(a in valid), -actions.index(a)))


def _train(rows: list[dict[str, Any]], actions: tuple[str, ...]) -> dict[str, Any]:
    train = [r for r in rows if r["manifest"].get("split") == "train"]
    global_best = _best_action(train, actions)
    by_sig: dict[tuple, str] = {}
    for sig, group in _group_by_sig(train).items():
        by_sig[sig] = _best_action(group, actions)
    feature_names = _feature_names(rows)
    return {
        "global_best": global_best,
        "by_sig": by_sig,
        "feature_names": feature_names,
        "train_rows": train,
        "all_rows": rows,
        "actions": actions,
    }


def _group_by_sig(rows: list[dict[str, Any]]) -> dict[tuple, list[dict[str, Any]]]:
    groups: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        groups[_sig(r)].append(r)
    return groups


def _predict(policy: str, row: dict[str, Any], fit: dict[str, Any]) -> str:
    if policy == "always_static":
        return "use_governed_static_agentic"
    if policy == "always_feedback":
        return "use_feedback_agentic"
    if policy == "always_defer":
        return "defer_or_abstain"
    if policy == "always_external":
        return "use_external_backend_adapter"
    if policy == "train_majority":
        return fit["global_best"]
    if policy == "visible_feature_majority":
        return fit["by_sig"].get(_sig(row), fit["global_best"])
    if policy == "nearest_train":
        names = fit.get("feature_names") or []
        train = fit.get("train_rows") or []
        candidates = [r for r in train if r["manifest"]["unit_id"] != row["manifest"]["unit_id"]]
        if not names or not candidates:
            return fit["global_best"]
        rv = _vec(row, names)
        nbr = min(candidates, key=lambda r: _dist(rv, _vec(r, names)))
        return _choose_valid(_valid(nbr), fit["global_best"], fit["actions"])
    if policy in ("nearest3_train", "nearest5_train", "nearest_loo_all"):
        names = fit.get("feature_names") or []
        source = fit.get("all_rows") if policy == "nearest_loo_all" else fit.get("train_rows")
        candidates = [r for r in (source or [])
                      if r["manifest"]["unit_id"] != row["manifest"]["unit_id"]]
        if not names or not candidates:
            return fit["global_best"]
        k = 3 if policy in ("nearest3_train", "nearest_loo_all") else 5
        rv = _vec(row, names)
        nbrs = sorted(candidates, key=lambda r: _dist(rv, _vec(r, names)))[:k]
        scores = {
            a: (sum(1 for r in nbrs if a in _valid(r)),
                sum(_utility(r, a) for r in nbrs))
            for a in fit["actions"]
        }
        return max(fit["actions"], key=lambda a: (scores[a][0], scores[a][1], -fit["actions"].index(a)))
    raise KeyError(policy)


def _score_policy(policy: str, rows: list[dict[str, Any]], fit: dict[str, Any]) -> dict[str, Any]:
    by_split: dict[str, dict[str, Any]] = {}
    all_correct = 0
    all_utility = 0.0
    confusion = Counter()
    for split in ("train", "dev", "eval", "all"):
        subset = rows if split == "all" else [
            r for r in rows if r["manifest"].get("split") == split]
        correct = 0
        util = 0.0
        for r in subset:
            pred = _predict(policy, r, fit)
            correct += int(_correct(r, pred))
            util += _utility(r, pred)
            if split == "all":
                confusion[(pred, _route(r))] += 1
        n = len(subset)
        by_split[split] = {
            "n": n,
            "accuracy": round(correct / n, 3) if n else 0.0,
            "correct": correct,
            "utility": round(util, 3),
            "utility_per_row": round(util / n, 3) if n else 0.0,
        }
        if split == "all":
            all_correct = correct
            all_utility = util
    return {
        "policy": policy,
        "splits": by_split,
        "all_correct": all_correct,
        "all_utility": round(all_utility, 3),
        "confusion": [
            {"pred": p, "gold_route": g, "n": n}
            for (p, g), n in sorted(confusion.items())
        ],
    }


def _with_split(rows: list[dict[str, Any]], salt: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in rows:
        h = int(hashlib.sha1(
            f"{salt}:{r['manifest']['unit_id']}".encode()).hexdigest()[:8], 16) % 10
        split = "train" if h < 6 else "dev" if h < 8 else "eval"
        rr = {
            "manifest": dict(r["manifest"]),
            "key": r["key"],
        }
        rr["manifest"]["split"] = split
        out.append(rr)
    return out


def _split_sensitivity(rows: list[dict[str, Any]], actions: tuple[str, ...],
                       policies: list[str], trials: int = 50) -> dict[str, Any]:
    acc: dict[str, list[float]] = {p: [] for p in policies}
    util: dict[str, list[float]] = {p: [] for p in policies}
    skipped = 0
    for i in range(trials):
        trial = _with_split(rows, f"split-{i}")
        if not any(r["manifest"].get("split") == "eval" for r in trial):
            skipped += 1
            continue
        fit = _train(trial, actions)
        for p in policies:
            s = _score_policy(p, trial, fit)["splits"]["eval"]
            acc[p].append(float(s["accuracy"]))
            util[p].append(float(s["utility_per_row"]))

    def summ(xs: list[float]) -> dict[str, float]:
        if not xs:
            return {"mean": 0.0, "min": 0.0, "max": 0.0}
        ys = sorted(xs)
        return {
            "mean": round(sum(xs) / len(xs), 3),
            "min": round(ys[0], 3),
            "max": round(ys[-1], 3),
        }

    return {
        "trials": trials,
        "skipped": skipped,
        "accuracy": {p: summ(xs) for p, xs in acc.items()},
        "utility_per_row": {p: summ(xs) for p, xs in util.items()},
    }


def evaluate(data_dir: Path, out_path: Path) -> dict[str, Any]:
    rows = _rows(data_dir)
    actions = _actions(rows)
    fit = _train(rows, actions)
    policies = [
        "always_static",
        "always_feedback",
        "always_defer",
        *([] if "use_external_backend_adapter" not in actions else ["always_external"]),
        "train_majority",
        "visible_feature_majority",
        "nearest_train",
        "nearest3_train",
        "nearest5_train",
        "nearest_loo_all",
    ]
    results = [_score_policy(p, rows, fit) for p in policies]
    sensitivity_policies = [
        "always_static", "always_feedback", "always_defer",
        "train_majority", "nearest_train", "nearest3_train",
        "nearest5_train",
    ]
    winner_accuracy = max(results, key=lambda r: (r["splits"]["eval"]["accuracy"],
                                                  r["splits"]["all"]["accuracy"]))
    winner_utility = max(results, key=lambda r: (r["splits"]["eval"]["utility_per_row"],
                                                 r["splits"]["all"]["utility_per_row"]))
    route_counts = Counter(_route(r) for r in rows)
    out = {
        "data_dir": str(data_dir),
        "n": len(rows),
        "candidate_actions": list(actions),
        "route_counts": dict(route_counts),
        "train_fit": {
            "global_best": fit["global_best"],
            "by_visible_signature": {
                str(k): v for k, v in sorted(fit["by_sig"].items())
            },
            "feature_names_n": len(fit.get("feature_names") or []),
        },
        "policies": results,
        "split_sensitivity": _split_sensitivity(
            rows, actions, sensitivity_policies, trials=50),
        "winner_eval_accuracy": winner_accuracy["policy"],
        "winner_eval_utility": winner_utility["policy"],
        "interpretation": (
            "measurement_only: if visible_feature_majority does not beat "
            "always_static/always_feedback on eval, there is no routing "
            "signal yet beyond arm priors in this tiny decider-derived set. "
            "nearest_loo_all is diagnostic only: it uses all labels except "
            "the target row and is not a sealed policy."
        ),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    return out


def self_test() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        manifest = root / "lean_routing_manifest.jsonl"
        key = root / "lean_routing_key.jsonl"
        rows_m = []
        rows_k = []
        specs = [
            ("a", "train", 1, 0, ["use_feedback_agentic"], "feedback_only_win"),
            ("b", "train", 0, 1, ["use_governed_static_agentic"], "static_only_win"),
            ("c", "eval", 1, 0, ["use_feedback_agentic"], "feedback_only_win"),
            ("d", "eval", 0, 1, ["use_governed_static_agentic"], "static_only_win"),
            ("e", "eval", 0, 0, ["defer_or_abstain"], "no_observed_action_closes"),
        ]
        for uid, split, integ, ineq, valid, route in specs:
            rows_m.append({
                "unit_id": uid,
                "split": split,
                "visible_packet": {
                    "visible_features": {
                        "has_integral_word": integ,
                        "has_inequality_word": ineq,
                        "has_sum_token": 0,
                        "has_tendsto_token": 0,
                        "has_integral_token": 0,
                        "has_order_token": 0,
                        "has_nat_int_token": 0,
                        "has_real_norm_token": 0,
                        "has_forall_token": 0,
                        "has_exists_token": 0,
                        "arrow_count": 0,
                        "binder_count": 0,
                        "target_stmt_lines": 0,
                        "ps_hyp_count": 0,
                        "ps_ctx_lines": 0,
                        "ps_arrow_count": 0,
                        "ps_target_token_count": 0,
                        "ps_has_forall": 0,
                        "ps_has_exists": 0,
                        "ps_has_implication": 0,
                        "ps_has_equality": 0,
                        "ps_has_order": 0,
                        "ps_has_sum": 0,
                        "ps_has_tendsto": 0,
                        "ps_has_integral": 0,
                        "ps_has_set": 0,
                        "ps_has_norm": 0,
                        "ps_has_nat_int": 0,
                        "ps_has_real": 0,
                    }
                },
            })
            rows_k.append({
                "unit_id": uid,
                "valid_actions": valid,
                "gold_route_class": route,
            })
        manifest.write_text("\n".join(json.dumps(r) for r in rows_m) + "\n")
        key.write_text("\n".join(json.dumps(r) for r in rows_k) + "\n")
        out = evaluate(root, root / "eval.json")
        vf = next(r for r in out["policies"] if r["policy"] == "visible_feature_majority")
        assert vf["splits"]["eval"]["correct"] == 2
        sig = ("(1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, "
               "0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)")
        assert out["train_fit"]["by_visible_signature"][sig] == "use_feedback_agentic"
    print("lean_action_routing_eval self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    out = evaluate(Path(args.data_dir), Path(args.out))
    print(json.dumps({
        "out": args.out,
        "n": out["n"],
        "route_counts": out["route_counts"],
        "winner_eval_accuracy": out["winner_eval_accuracy"],
        "winner_eval_utility": out["winner_eval_utility"],
        "policy_eval": {
            r["policy"]: r["splits"]["eval"] for r in out["policies"]
        },
    }, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
