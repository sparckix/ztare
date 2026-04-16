"""Offline telemetry reporter for GP-038 (cycle time / episode) and GP-040 (cost / throughput).

Reads workspace/iteration_telemetry.jsonl produced by autoresearch_loop.py and emits
three report sections:

  Cost Report  (GP-040 Slice 1.5) — per-run and aggregate cost / token breakdown (mean/min/max)
  Episode Report  (GP-038 Slice 1.5) — load-bearing episode classification and cycle-time stats
  Tail Report   (Slice 2a)        — p50/p90/p95/p99 wall-clock and cost, split by load-bearing

The Tail Report is the Slice 2a deliverable. Means lie on heavy tails; GP-032 Turn 1 §2
requires load-bearing claims quote tail cycle-time, not mean. Quoting per-iter means from
the Cost Report as "cost of experimentation" is the laundering failure mode flagged in
GP-032 Turn 1 §5 — use the Tail Report instead.

A load-bearing episode is any iteration where at least one of the following is true:
  - gate_engagement is True (GP-030 deterministic gate fired)
  - escalation_flags.self_reference is True
  - escalation_flags.semantic_escalation is True
  - loop_control_action is "underidentified" or "catastrophic_failure"

Usage:
  python -m src.ztare.validator.telemetry_reporter --project gp037_substrate_swap_01
  python -m src.ztare.validator.telemetry_reporter --telemetry path/to/iteration_telemetry.jsonl
  python -m src.ztare.validator.telemetry_reporter --project gp037_substrate_swap_01 --output report.json
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

from src.ztare.common.paths import PROJECTS_DIR


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_records(telemetry_path: Path) -> list[dict[str, Any]]:
    records = []
    for line in telemetry_path.read_text().splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def group_by_run(records: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """Group records into per-run dicts keyed by run_id."""
    runs: dict[int, dict[str, Any]] = {}
    for rec in records:
        run_id = rec["run_id"]
        if run_id not in runs:
            runs[run_id] = {"start": None, "end": None, "iterations": []}
        if rec["record_type"] == "run_start":
            runs[run_id]["start"] = rec
        elif rec["record_type"] == "run_end":
            runs[run_id]["end"] = rec
        elif rec["record_type"] == "iteration":
            runs[run_id]["iterations"].append(rec)
    return runs


# ---------------------------------------------------------------------------
# Episode classification (GP-038)
# ---------------------------------------------------------------------------

_LOAD_BEARING_LOOP_ACTIONS = {"underidentified", "catastrophic_failure"}

_TAIL_PS: tuple[int, ...] = (50, 90, 95, 99)


def _percentile(values: list[float], p: float) -> float | None:
    """Linear-interpolation percentile. Returns None on empty input.

    Uses the same convention as numpy.percentile default (linear). Written
    inline to keep the reporter stdlib-only per the Slice 1 constraint.
    """

    if not values:
        return None
    if len(values) == 1:
        return float(values[0])
    sorted_vals = sorted(values)
    rank = (p / 100.0) * (len(sorted_vals) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = rank - lo
    return sorted_vals[lo] + frac * (sorted_vals[hi] - sorted_vals[lo])


def tail_stats(values: list[float]) -> dict[str, float | int | None]:
    """Return n + p50/p90/p95/p99 for a list of numeric values."""

    return {
        "n": len(values),
        **{f"p{p}": _percentile(values, p) for p in _TAIL_PS},
    }


def is_load_bearing(it: dict[str, Any]) -> bool:
    if it.get("gate_engagement"):
        return True
    flags = it.get("escalation_flags", {})
    if flags.get("self_reference") or flags.get("semantic_escalation"):
        return True
    if it.get("loop_control_action") in _LOAD_BEARING_LOOP_ACTIONS:
        return True
    return False


# ---------------------------------------------------------------------------
# Per-run analysis
# ---------------------------------------------------------------------------

def analyse_run(run_id: int, run: dict[str, Any]) -> dict[str, Any]:
    iters = run["iterations"]
    start = run["start"] or {}
    end = run["end"] or {}

    if not iters:
        return {"run_id": run_id, "iteration_count": 0}

    # --- cost / throughput (GP-040) ---
    costs = [it.get("estimated_cost_usd", 0.0) for it in iters]
    total_cost = sum(costs)

    mutator_in = sum(it.get("mutator_usage", {}).get("input_tokens", 0) for it in iters)
    mutator_out = sum(it.get("mutator_usage", {}).get("output_tokens", 0) for it in iters)
    judge_in = sum(it.get("judge_usage", {}).get("input_tokens", 0) for it in iters)
    judge_out = sum(it.get("judge_usage", {}).get("output_tokens", 0) for it in iters)
    total_tokens = mutator_in + mutator_out + judge_in + judge_out

    wall_times = [it.get("wall_clock_seconds", 0.0) for it in iters]
    total_wall = sum(wall_times)

    # --- episode classification (GP-038) ---
    lb_iters = [it for it in iters if is_load_bearing(it)]
    non_lb_iters = [it for it in iters if not is_load_bearing(it)]

    lb_wall = [it.get("wall_clock_seconds", 0.0) for it in lb_iters]
    non_lb_wall = [it.get("wall_clock_seconds", 0.0) for it in non_lb_iters]

    # stagnation run: consecutive iterations with the same stagnation_count increasing
    stagnation_windows: list[dict[str, Any]] = []
    in_stagnation = False
    stag_start_idx = 0
    prev_stag = 0
    for i, it in enumerate(iters):
        sc = it.get("stagnation_count", 0)
        if sc > prev_stag:
            if not in_stagnation:
                in_stagnation = True
                stag_start_idx = i
        else:
            if in_stagnation:
                stagnation_windows.append({
                    "start_iter": iters[stag_start_idx]["iteration_index"],
                    "end_iter": iters[i - 1]["iteration_index"],
                    "length": i - stag_start_idx,
                })
            in_stagnation = False
        prev_stag = sc
    if in_stagnation:
        stagnation_windows.append({
            "start_iter": iters[stag_start_idx]["iteration_index"],
            "end_iter": iters[-1]["iteration_index"],
            "length": len(iters) - stag_start_idx,
        })

    # loop control action counts
    action_counts: dict[str, int] = {}
    for it in iters:
        action = it.get("loop_control_action", "unknown")
        action_counts[action] = action_counts.get(action, 0) + 1

    # gate failure summary
    all_failed_gates: list[str] = []
    for it in iters:
        all_failed_gates.extend(it.get("failed_gate_ids", []))
    gate_failure_freq: dict[str, int] = {}
    for g in all_failed_gates:
        gate_failure_freq[g] = gate_failure_freq.get(g, 0) + 1

    result: dict[str, Any] = {
        "run_id": run_id,
        "project": start.get("project", "unknown"),
        "iteration_count": len(iters),
        "exit_reason": end.get("run_exit_reason", "unknown"),
        "final_score": end.get("final_score", iters[-1].get("score", 0) if iters else 0),

        # GP-040 cost
        "cost": {
            "total_usd": round(total_cost, 6),
            "mean_per_iter_usd": round(statistics.mean(costs), 6) if costs else 0.0,
            "min_per_iter_usd": round(min(costs), 6) if costs else 0.0,
            "max_per_iter_usd": round(max(costs), 6) if costs else 0.0,
            "total_tokens": total_tokens,
            "mutator_tokens": mutator_in + mutator_out,
            "judge_tokens": judge_in + judge_out,
            "total_wall_seconds": round(total_wall, 1),
            "mean_wall_per_iter_seconds": round(statistics.mean(wall_times), 1) if wall_times else 0.0,
        },

        # Slice 2a tail stats — the honest cycle-time / cost answer
        "tail": {
            "wall_seconds_all": tail_stats(wall_times),
            "wall_seconds_load_bearing": tail_stats(lb_wall),
            "wall_seconds_non_load_bearing": tail_stats(non_lb_wall),
            "cost_usd_all": tail_stats([c for c in costs if c is not None]),
            "cost_usd_load_bearing": tail_stats(
                [it.get("estimated_cost_usd") or 0.0 for it in lb_iters]
            ),
            "cost_usd_non_load_bearing": tail_stats(
                [it.get("estimated_cost_usd") or 0.0 for it in non_lb_iters]
            ),
        },

        # GP-038 episode
        "episodes": {
            "load_bearing_count": len(lb_iters),
            "non_load_bearing_count": len(non_lb_iters),
            "load_bearing_fraction": round(len(lb_iters) / len(iters), 3) if iters else 0.0,
            "mean_wall_load_bearing_seconds": round(statistics.mean(lb_wall), 1) if lb_wall else None,
            "mean_wall_non_load_bearing_seconds": round(statistics.mean(non_lb_wall), 1) if non_lb_wall else None,
            "stagnation_windows": stagnation_windows,
            "loop_control_actions": action_counts,
            "gate_failure_frequency": gate_failure_freq,
        },
    }
    # Stash raw iterations under a leading-underscore key so aggregate()
    # can pool across runs without re-loading the telemetry file. Not
    # emitted in the JSON output (see main()).
    result["_raw_iterations"] = iters
    return result


# ---------------------------------------------------------------------------
# Aggregate across runs
# ---------------------------------------------------------------------------

def aggregate(run_results: list[dict[str, Any]]) -> dict[str, Any]:
    if not run_results:
        return {}
    total_cost = sum(r["cost"]["total_usd"] for r in run_results if "cost" in r)
    total_iters = sum(r["iteration_count"] for r in run_results)
    total_wall = sum(r["cost"]["total_wall_seconds"] for r in run_results if "cost" in r)
    total_tokens = sum(r["cost"]["total_tokens"] for r in run_results if "cost" in r)

    all_lb = sum(r["episodes"]["load_bearing_count"] for r in run_results if "episodes" in r)
    all_non_lb = sum(r["episodes"]["non_load_bearing_count"] for r in run_results if "episodes" in r)

    # Slice 2a cross-run pooled tails. Pooling is correct here — we want
    # "what does an iteration look like across all runs," not "what does
    # the average of per-run means look like."
    pooled_wall_all: list[float] = []
    pooled_wall_lb: list[float] = []
    pooled_wall_non_lb: list[float] = []
    pooled_cost_all: list[float] = []
    pooled_cost_lb: list[float] = []
    pooled_cost_non_lb: list[float] = []
    for r in run_results:
        raw_iters = r.get("_raw_iterations", [])
        for it in raw_iters:
            w = it.get("wall_clock_seconds") or 0.0
            c = it.get("estimated_cost_usd") or 0.0
            pooled_wall_all.append(w)
            pooled_cost_all.append(c)
            if is_load_bearing(it):
                pooled_wall_lb.append(w)
                pooled_cost_lb.append(c)
            else:
                pooled_wall_non_lb.append(w)
                pooled_cost_non_lb.append(c)

    return {
        "run_count": len(run_results),
        "total_iterations": total_iters,
        "total_cost_usd": round(total_cost, 6),
        "total_wall_seconds": round(total_wall, 1),
        "total_tokens": total_tokens,
        "cost_per_iteration_usd": round(total_cost / total_iters, 6) if total_iters else 0.0,
        "wall_per_iteration_seconds": round(total_wall / total_iters, 1) if total_iters else 0.0,
        "load_bearing_fraction_overall": round(all_lb / (all_lb + all_non_lb), 3) if (all_lb + all_non_lb) else 0.0,
        "tail_pooled": {
            "wall_seconds_all": tail_stats(pooled_wall_all),
            "wall_seconds_load_bearing": tail_stats(pooled_wall_lb),
            "wall_seconds_non_load_bearing": tail_stats(pooled_wall_non_lb),
            "cost_usd_all": tail_stats(pooled_cost_all),
            "cost_usd_load_bearing": tail_stats(pooled_cost_lb),
            "cost_usd_non_load_bearing": tail_stats(pooled_cost_non_lb),
        },
    }


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_cost_section(run: dict[str, Any]) -> str:
    c = run["cost"]
    lines = [
        f"  Run {run['run_id']}  project={run['project']}  exit={run['exit_reason']}  final_score={run['final_score']}",
        f"    iterations : {run['iteration_count']}",
        f"    total cost : ${c['total_usd']:.4f}",
        f"    per-iter   : ${c['mean_per_iter_usd']:.4f} mean  [${c['min_per_iter_usd']:.4f} – ${c['max_per_iter_usd']:.4f}]",
        f"    wall time  : {c['total_wall_seconds']:.0f}s total  {c['mean_wall_per_iter_seconds']:.0f}s/iter",
        f"    tokens     : {c['total_tokens']:,}  (mutator {c['mutator_tokens']:,} / judge {c['judge_tokens']:,})",
    ]
    return "\n".join(lines)


def render_episode_section(run: dict[str, Any]) -> str:
    e = run["episodes"]
    lb_mean = f"{e['mean_wall_load_bearing_seconds']:.0f}s" if e["mean_wall_load_bearing_seconds"] is not None else "n/a"
    non_lb_mean = f"{e['mean_wall_non_load_bearing_seconds']:.0f}s" if e["mean_wall_non_load_bearing_seconds"] is not None else "n/a"
    lines = [
        f"  Run {run['run_id']}  project={run['project']}",
        f"    load-bearing iters : {e['load_bearing_count']} / {run['iteration_count']} ({e['load_bearing_fraction']:.0%})  mean wall {lb_mean}",
        f"    non-load-bearing   : {e['non_load_bearing_count']}  mean wall {non_lb_mean}",
    ]
    if e["stagnation_windows"]:
        for w in e["stagnation_windows"]:
            lines.append(f"    stagnation window  : iter {w['start_iter']}–{w['end_iter']} ({w['length']} iters)")
    else:
        lines.append("    stagnation windows : none")
    actions = "  ".join(f"{k}={v}" for k, v in sorted(e["loop_control_actions"].items()))
    lines.append(f"    loop actions       : {actions}")
    if e["gate_failure_frequency"]:
        gf = "  ".join(f"{k}={v}" for k, v in sorted(e["gate_failure_frequency"].items()))
        lines.append(f"    gate failures      : {gf}")
    return "\n".join(lines)


def _fmt_tail(label: str, stats: dict[str, Any], unit: str, precision: int) -> str:
    n = stats.get("n", 0)
    if not n:
        return f"    {label:<28} n=0"
    parts = [f"    {label:<28} n={n}"]
    for p in _TAIL_PS:
        v = stats.get(f"p{p}")
        if v is None:
            parts.append(f" p{p}=n/a")
        else:
            parts.append(f" p{p}={v:.{precision}f}{unit}")
    return "".join(parts)


def render_tail_section(run: dict[str, Any]) -> str:
    t = run.get("tail")
    if not t:
        return ""
    lines = [f"  Run {run['run_id']}  project={run['project']}"]
    lines.append("    wall clock (seconds)")
    lines.append(_fmt_tail("  all iterations", t["wall_seconds_all"], "s", 1))
    lines.append(_fmt_tail("  load-bearing", t["wall_seconds_load_bearing"], "s", 1))
    lines.append(_fmt_tail("  non-load-bearing", t["wall_seconds_non_load_bearing"], "s", 1))
    lines.append("    cost (USD per iter)")
    lines.append(_fmt_tail("  all iterations", t["cost_usd_all"], "", 4))
    lines.append(_fmt_tail("  load-bearing", t["cost_usd_load_bearing"], "", 4))
    lines.append(_fmt_tail("  non-load-bearing", t["cost_usd_non_load_bearing"], "", 4))
    return "\n".join(lines)


def render_report(run_results: list[dict[str, Any]], agg: dict[str, Any]) -> str:
    sections = []

    sections.append("=" * 70)
    sections.append("GP-040  COST / THROUGHPUT REPORT")
    sections.append("=" * 70)
    for r in run_results:
        if "cost" in r:
            sections.append(render_cost_section(r))
    sections.append("")
    sections.append("  AGGREGATE")
    sections.append(f"    runs           : {agg['run_count']}")
    sections.append(f"    total iters    : {agg['total_iterations']}")
    sections.append(f"    total cost     : ${agg['total_cost_usd']:.4f}")
    sections.append(f"    cost/iter      : ${agg['cost_per_iteration_usd']:.4f}")
    sections.append(f"    wall time      : {agg['total_wall_seconds']:.0f}s  ({agg['wall_per_iteration_seconds']:.0f}s/iter)")
    sections.append(f"    total tokens   : {agg['total_tokens']:,}")
    sections.append("")

    sections.append("=" * 70)
    sections.append("GP-038  EPISODE / CYCLE-TIME REPORT")
    sections.append("=" * 70)
    for r in run_results:
        if "episodes" in r:
            sections.append(render_episode_section(r))
    sections.append("")
    sections.append("  AGGREGATE")
    sections.append(f"    load-bearing fraction (all runs) : {agg['load_bearing_fraction_overall']:.0%}")
    sections.append("")

    sections.append("=" * 70)
    sections.append("SLICE 2a  TAIL REPORT  (p50/p90/p95/p99)")
    sections.append("=" * 70)
    sections.append("  (quote these — not the means — for any load-bearing claim)")
    sections.append("")
    for r in run_results:
        if "tail" in r:
            sections.append(render_tail_section(r))
    sections.append("")
    pooled = agg.get("tail_pooled")
    if pooled:
        sections.append("  POOLED ACROSS RUNS")
        sections.append("    wall clock (seconds)")
        sections.append(_fmt_tail("  all iterations", pooled["wall_seconds_all"], "s", 1))
        sections.append(_fmt_tail("  load-bearing", pooled["wall_seconds_load_bearing"], "s", 1))
        sections.append(_fmt_tail("  non-load-bearing", pooled["wall_seconds_non_load_bearing"], "s", 1))
        sections.append("    cost (USD per iter)")
        sections.append(_fmt_tail("  all iterations", pooled["cost_usd_all"], "", 4))
        sections.append(_fmt_tail("  load-bearing", pooled["cost_usd_load_bearing"], "", 4))
        sections.append(_fmt_tail("  non-load-bearing", pooled["cost_usd_non_load_bearing"], "", 4))
        sections.append("")

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Offline telemetry reporter (GP-038 + GP-040)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--project", help="Project name under projects/")
    group.add_argument("--telemetry", help="Explicit path to iteration_telemetry.jsonl")
    parser.add_argument("--output", help="Optional path to write JSON report")
    args = parser.parse_args()

    if args.project:
        telemetry_path = PROJECTS_DIR / args.project / "workspace" / "iteration_telemetry.jsonl"
    else:
        telemetry_path = Path(args.telemetry)

    if not telemetry_path.exists():
        raise SystemExit(f"Telemetry file not found: {telemetry_path}")

    records = load_records(telemetry_path)
    runs = group_by_run(records)
    run_results = [analyse_run(run_id, run) for run_id, run in sorted(runs.items())]
    agg = aggregate([r for r in run_results if "cost" in r])

    print(render_report(run_results, agg))

    if args.output:
        public_runs = [{k: v for k, v in r.items() if not k.startswith("_")} for r in run_results]
        output = {"runs": public_runs, "aggregate": agg}
        Path(args.output).write_text(json.dumps(output, indent=2))
        print(f"JSON report written to {args.output}")


if __name__ == "__main__":
    main()
