#!/usr/bin/env python3
"""Deterministic Elo/P-UCB population rater for LeanMill attempt records.

This is an APN-lite baseline primitive: it ranks arms, tactics, and repair
families from executable Lean/governance outcomes. It does not call models, does
not run Lean, and carries no proof credit. Governance receipts remain the only
proof-value authority.
"""
from __future__ import annotations

import argparse
import json
import math
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

from leanmill_factory_config import read_policy
from leanmill_paths import DATA_DIR, FACTORY_POLICY

DEFAULT_CHECKPOINT = f"{DATA_DIR}/evaluation_harness_run.jsonl"
DEFAULT_OUT = f"{DATA_DIR}/leanmill_population_elo.json"
DEFAULT_MD = f"{DATA_DIR}/leanmill_population_elo.md"
DEFAULT_POLICY = FACTORY_POLICY
DEFAULT_OUTCOME_SCORES = {
    "ratified_closure": 1.0,
    "exact_gap": 0.95,
    "valid_falsifier": 0.95,
    "governed_tool_tactic_closure_candidate": 0.72,
    "raw_closure_candidate": 0.62,
    "failed_negative_control": 0.05,
    "target_kind_audit_failure": 0.0,
    "harness_candidate_build_failure": 0.0,
    "harness_no_candidates": 0.0,
    "wall_timeout_hit": 0.1,
    "tested_no_positive_signal": 0.2,
}


def _read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in p.read_text(errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _policy_population(path: str | Path) -> dict[str, Any]:
    policy = read_policy(path)
    ops = policy.get("operations") if isinstance(policy, dict) else {}
    pop = (ops or {}).get("population_elo") if isinstance(ops, dict) else {}
    return pop if isinstance(pop, dict) else {}


def _float(obj: Any, fallback: float) -> float:
    try:
        return float(obj)
    except (TypeError, ValueError):
        return fallback


def _score_record(rec: dict[str, Any], outcome_scores: dict[str, float], attempt_penalty: float, time_penalty: float) -> float:
    base = outcome_scores.get(str(rec.get("learning_exit") or ""), 0.0)
    attempts = int(rec.get("attempt_count") or 0)
    wall = _float(rec.get("wall_time_used_s"), 0.0)
    score = base - attempt_penalty * max(0, attempts - 1) - time_penalty * wall
    return max(0.0, min(1.0, score))


def _score_attempt(attempt: dict[str, Any], outcome_scores: dict[str, float]) -> float:
    if "build" in attempt:
        return outcome_scores.get("harness_candidate_build_failure", 0.0)
    return outcome_scores.get(str(attempt.get("learning_exit") or "tested_no_positive_signal"), 0.0)


def _contestant_key(kind: str, name: str) -> str:
    return f"{kind}:{name}"


def _expected(ra: float, rb: float) -> float:
    return 1.0 / (1.0 + 10 ** ((rb - ra) / 400.0))


def _update(ratings: dict[str, float], stats: dict[str, dict[str, Any]], a: str, b: str, result_a: float, *, k: float, initial: float) -> None:
    ratings.setdefault(a, initial)
    ratings.setdefault(b, initial)
    ea = _expected(ratings[a], ratings[b])
    delta = k * (result_a - ea)
    ratings[a] += delta
    ratings[b] -= delta
    stats[a]["games"] += 1
    stats[b]["games"] += 1
    if result_a > 0.5:
        stats[a]["wins"] += 1
        stats[b]["losses"] += 1
    elif result_a < 0.5:
        stats[a]["losses"] += 1
        stats[b]["wins"] += 1
    else:
        stats[a]["ties"] += 1
        stats[b]["ties"] += 1


def _pair_result(score_a: float, score_b: float, margin: float) -> float | None:
    if abs(score_a - score_b) <= margin:
        return 0.5
    return 1.0 if score_a > score_b else 0.0


def _rating_rows(ratings: dict[str, float], stats: dict[str, dict[str, Any]], *, initial: float, exploration_c: float) -> list[dict[str, Any]]:
    total_games = sum(int(s.get("games") or 0) for s in stats.values())
    rows = []
    for key, rating in ratings.items():
        games = int(stats[key].get("games") or 0)
        explore = exploration_c * 400.0 * math.sqrt(math.log(total_games + 2.0) / (games + 1.0)) if exploration_c else 0.0
        rows.append({
            "contestant": key,
            "rating": round(rating, 3),
            "games": games,
            "wins": int(stats[key].get("wins") or 0),
            "losses": int(stats[key].get("losses") or 0),
            "ties": int(stats[key].get("ties") or 0),
            "p_ucb_priority": round(rating + explore, 3),
            "exploration_bonus": round(explore, 3),
            "cold_start": games == 0 and abs(rating - initial) < 1e-9,
        })
    rows.sort(key=lambda row: (-float(row["p_ucb_priority"]), -float(row["rating"]), str(row["contestant"])))
    return rows


def build(args: argparse.Namespace) -> dict[str, Any]:
    pop_policy = _policy_population(args.policy)
    initial = _float(pop_policy.get("initial_rating"), 1000.0)
    k = _float(pop_policy.get("k_factor"), 24.0)
    margin = _float(pop_policy.get("tie_margin"), 0.03)
    exploration_c = _float(pop_policy.get("p_ucb_exploration_c"), 0.35)
    attempt_penalty = _float(pop_policy.get("attempt_penalty"), 0.005)
    time_penalty = _float(pop_policy.get("wall_time_penalty_per_s"), 0.0)
    scores = dict(DEFAULT_OUTCOME_SCORES)
    scores.update({str(k): float(v) for k, v in (pop_policy.get("outcome_scores") or {}).items()})

    records = _read_jsonl(args.checkpoint)
    if args.run_id:
        records = [r for r in records if str(r.get("run_id") or "") == args.run_id]
    by_row: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in records:
        row_id = str(rec.get("row_id") or "")
        if row_id:
            by_row[row_id].append(rec)

    ratings: dict[str, float] = {}
    stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"games": 0, "wins": 0, "losses": 0, "ties": 0})
    events: list[dict[str, Any]] = []

    # Arm-level pairwise contests on the same row.
    for row_id, recs in by_row.items():
        scored = [
            (_contestant_key("arm", str(rec.get("arm") or "unknown")), _score_record(rec, scores, attempt_penalty, time_penalty), rec)
            for rec in recs
        ]
        for i, (a, score_a, rec_a) in enumerate(scored):
            for b, score_b, rec_b in scored[i + 1:]:
                result = _pair_result(score_a, score_b, margin)
                if result is None:
                    continue
                _update(ratings, stats, a, b, result, k=k, initial=initial)
                events.append({"scope": "arm", "row_id": row_id, "a": a, "b": b, "score_a": round(score_a, 4), "score_b": round(score_b, 4), "result_a": result})

    # Candidate/tool contests within each row-arm trace. A candidate that closes
    # beats failed earlier attempts; otherwise attempts with equal no-signal tie.
    for rec in records:
        row_id = str(rec.get("row_id") or "")
        arm = str(rec.get("arm") or "unknown")
        attempts = [a for a in rec.get("attempts") or [] if isinstance(a, dict)]
        scored_attempts = []
        for attempt in attempts:
            kind = str(attempt.get("candidate_kind") or "unknown")
            cid = str(attempt.get("candidate_id") or "unknown")
            family = str(attempt.get("family") or "")
            key = _contestant_key("candidate", f"{kind}:{cid}")
            scored_attempts.append((key, _score_attempt(attempt, scores), attempt))
            if family:
                scored_attempts.append((_contestant_key("family", family), _score_attempt(attempt, scores), attempt))
        for i, (a, score_a, attempt_a) in enumerate(scored_attempts):
            for b, score_b, attempt_b in scored_attempts[i + 1:]:
                if a == b:
                    continue
                result = _pair_result(score_a, score_b, margin)
                if result is None:
                    continue
                _update(ratings, stats, a, b, result, k=k, initial=initial)
                events.append({"scope": "candidate", "row_id": row_id, "arm": arm, "a": a, "b": b, "score_a": round(score_a, 4), "score_b": round(score_b, 4), "result_a": result})

    rows = _rating_rows(ratings, stats, initial=initial, exploration_c=exploration_c)
    result = {
        "schema": "leanmill-population-elo-v1",
        "checkpoint": args.checkpoint,
        "run_id": args.run_id,
        "policy": args.policy,
        "record_count": len(records),
        "row_count": len(by_row),
        "contestant_count": len(rows),
        "event_count": len(events),
        "params": {
            "initial_rating": initial,
            "k_factor": k,
            "tie_margin": margin,
            "p_ucb_exploration_c": exploration_c,
            "attempt_penalty": attempt_penalty,
            "wall_time_penalty_per_s": time_penalty,
            "outcome_scores": scores,
        },
        "non_laundering_note": "Elo/P-UCB ranks observed executable attempts only. It is routing/population memory, not proof credit; governance receipts remain authoritative.",
        "ratings": rows,
        "events_sample": events[: int(args.event_sample_limit)],
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    if args.md:
        _write_md(args.md, result)
    return result


def _write_md(path: str | Path, result: dict[str, Any]) -> None:
    lines = [
        "# LeanMill Population Elo",
        "",
        f"- records: `{result['record_count']}`",
        f"- rows: `{result['row_count']}`",
        f"- contestants: `{result['contestant_count']}`",
        f"- events: `{result['event_count']}`",
        "",
        "## Top Ratings",
        "",
        "| contestant | rating | p_ucb | games | W-L-T |",
        "|---|---:|---:|---:|---|",
    ]
    for row in result["ratings"][:40]:
        lines.append("| " + " | ".join([
            str(row["contestant"]),
            str(row["rating"]),
            str(row["p_ucb_priority"]),
            str(row["games"]),
            f"{row['wins']}-{row['losses']}-{row['ties']}",
        ]) + " |")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n")


def _self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="leanmill_population_elo_") as td:
        root = Path(td)
        ck = root / "ck.jsonl"
        recs = [
            {"run_id": "x", "row_id": "r1", "arm": "a", "learning_exit": "ratified_closure", "attempt_count": 2, "attempts": [
                {"candidate_kind": "tool_tactic", "candidate_id": "aesop", "learning_exit": "tested_no_positive_signal"},
                {"candidate_kind": "tool_tactic", "candidate_id": "simp", "learning_exit": "ratified_closure"},
            ]},
            {"run_id": "x", "row_id": "r1", "arm": "b", "learning_exit": "tested_no_positive_signal", "attempt_count": 3, "attempts": [{"candidate_kind": "tool_tactic", "candidate_id": "aesop", "learning_exit": "tested_no_positive_signal"}]},
        ]
        ck.write_text("".join(json.dumps(r) + "\n" for r in recs))
        policy = root / "policy.json"
        policy.write_text(json.dumps({"operations": {"population_elo": {"initial_rating": 1000, "k_factor": 24, "p_ucb_exploration_c": 0.0}}}) + "\n")
        result = build(argparse.Namespace(checkpoint=str(ck), run_id="x", policy=str(policy), out=None, md=None, event_sample_limit=20))
        ratings = {r["contestant"]: r["rating"] for r in result["ratings"]}
        assert ratings["arm:a"] > ratings["arm:b"], result
        assert ratings["candidate:tool_tactic:simp"] > ratings["candidate:tool_tactic:aesop"], result
    print("leanmill_population_elo self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", default=DEFAULT_CHECKPOINT)
    ap.add_argument("--run-id", default="")
    ap.add_argument("--policy", default=DEFAULT_POLICY)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--md", default=DEFAULT_MD)
    ap.add_argument("--event-sample-limit", type=int, default=200)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    result = build(args)
    print(json.dumps({
        "out": args.out,
        "md": args.md,
        "record_count": result["record_count"],
        "row_count": result["row_count"],
        "contestant_count": result["contestant_count"],
        "event_count": result["event_count"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
