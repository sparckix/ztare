#!/usr/bin/env python3
"""Solver-lane telemetry — make solve_adhoc's move/exit/efficiency profile LEGIBLE on the leanmill dashboard.

READ-ONLY over the governance exhaust (never a soundness surface): aggregates
`analytics/public/queries/solver_lane_attempts.db` into:
  • per-MOVE: attempts, closed, advanced, close-rate, median wallclock (which moves actually close vs grind)
  • per-OUTCOME mix (closed / advanced / failed_compile / no_advance / …)
  • per-PROVIDER efficiency (attempts per closure)
  • recent RUNS (by run_tag): attempts, advances, closures — the per-campaign yield

`closed` = ratified=1 OR outcome ∈ {closed, admitted_and_closed} (the kernel-credit set); `advanced` = a
kernel-gated step that did not (yet) close. The dashboard absorbs the JSON; nothing here gates soundness.

Usage:
  python scripts/public/control/leanmill/solver_lane_telemetry.py [--repo .] [--json [OUT]] [--selftest]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
import sys
from collections import defaultdict
from pathlib import Path

DB_REL = "analytics/public/queries/solver_lane_attempts.db"
DEFAULT_JSON_REL = "analytics/public/leanmill/dashboard_data/solver_lane_telemetry.json"  # the leanmill dashboard home
_CLOSED_OUTCOMES = ("closed", "admitted_and_closed")


def _is_closed(outcome: "str | None", ratified) -> bool:
    return (ratified == 1) or ((outcome or "") in _CLOSED_OUTCOMES)


def load_rows(repo: Path) -> "list[dict]":
    p = repo / DB_REL
    if not p.exists():
        return []
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        rows = [dict(r) for r in con.execute(
            "select run_tag, move, provider, outcome, ratified, wallclock_s from attempts")]
    except sqlite3.Error:
        rows = []
    finally:
        con.close()
    return rows


def summarize(rows: "list[dict]") -> dict:
    """Pure aggregation (injectable rows ⇒ testable with no DB)."""
    by_move: dict = defaultdict(lambda: {"attempts": 0, "closed": 0, "advanced": 0, "_wc": []})
    by_outcome: dict = defaultdict(int)
    by_provider: dict = defaultdict(lambda: {"attempts": 0, "closed": 0})
    by_run: dict = defaultdict(lambda: {"attempts": 0, "closed": 0, "advanced": 0})
    for r in rows:
        outcome, ratified = r.get("outcome"), r.get("ratified")
        closed = _is_closed(outcome, ratified)
        adv = (outcome == "advanced")
        m = by_move[r.get("move") or "?"]
        m["attempts"] += 1
        m["closed"] += int(closed)
        m["advanced"] += int(adv)
        if isinstance(r.get("wallclock_s"), (int, float)):
            m["_wc"].append(float(r["wallclock_s"]))
        by_outcome[outcome or "?"] += 1
        p = by_provider[r.get("provider") or "?"]
        p["attempts"] += 1
        p["closed"] += int(closed)
        rt = by_run[r.get("run_tag") or "?"]
        rt["attempts"] += 1
        rt["closed"] += int(closed)
        rt["advanced"] += int(adv)

    def _move_view(d: dict) -> dict:
        wc = d.pop("_wc")
        return {**d, "close_rate": round(d["closed"] / d["attempts"], 3) if d["attempts"] else None,
                "median_wallclock_s": round(statistics.median(wc), 1) if wc else None}

    moves = {k: _move_view(v) for k, v in sorted(by_move.items(), key=lambda kv: -kv[1]["attempts"])}
    provs = {k: {**v, "attempts_per_closure": round(v["attempts"] / v["closed"], 1) if v["closed"] else None}
             for k, v in sorted(by_provider.items(), key=lambda kv: -kv[1]["attempts"])}
    runs = dict(sorted(by_run.items(), key=lambda kv: kv[0], reverse=True)[:12])   # 12 most-recent run_tags
    total = len(rows)
    closed_total = sum(1 for r in rows if _is_closed(r.get("outcome"), r.get("ratified")))
    return {
        "title": "Solver-lane telemetry (solve_adhoc moves / exits / efficiency)",
        "totals": {"attempts": total, "closed": closed_total,
                   "advanced": by_outcome.get("advanced", 0),
                   "close_rate": round(closed_total / total, 4) if total else None},
        "by_move": moves, "by_outcome": dict(sorted(by_outcome.items(), key=lambda kv: -kv[1])),
        "by_provider": provs, "recent_runs": runs,
    }


def render_md(rep: dict) -> str:
    t = rep["totals"]
    lines = [f"# {rep['title']}",
             f"attempts={t['attempts']} closed={t['closed']} advanced={t['advanced']} "
             f"close_rate={t['close_rate']}", "", "## by move (attempts / closed / advanced / close-rate / median wc)"]
    for m, v in rep["by_move"].items():
        lines.append(f"  {m:<22} {v['attempts']:>4} / {v['closed']:>3} / {v['advanced']:>3}  "
                     f"rate={v['close_rate']} wc={v['median_wallclock_s']}s")
    lines.append("\n## by outcome")
    for o, n in rep["by_outcome"].items():
        lines.append(f"  {o:<22} {n}")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--json", nargs="?", const="DEFAULT", default=None,
                    help=f"also write the dashboard JSON (bare --json ⇒ {DEFAULT_JSON_REL})")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    repo = Path(args.repo).resolve()
    rep = summarize(load_rows(repo))
    print(render_md(rep))
    if args.json is not None:
        out = repo / DEFAULT_JSON_REL if args.json == "DEFAULT" else Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(rep, indent=2, default=str))
        print(f"\n[wrote] {out}")
    return 0


def _selftest() -> int:
    fails = []

    def ok(n, c):
        print(f"  [{'PASS' if c else 'FAIL'}] {n}")
        if not c:
            fails.append(n)

    rows = [
        {"run_tag": "r1", "move": "claude_warm", "provider": "claude_opus_warm", "outcome": "closed",
         "ratified": 1, "wallclock_s": 100.0},
        {"run_tag": "r1", "move": "claude_warm", "provider": "claude_opus_warm", "outcome": "failed_compile",
         "ratified": None, "wallclock_s": 200.0},
        {"run_tag": "r1", "move": "conjecture_lemma", "provider": "codex", "outcome": "advanced",
         "ratified": None, "wallclock_s": 50.0},
        {"run_tag": "r2", "move": "native_hammer", "provider": "native", "outcome": "failed_compile",
         "ratified": None, "wallclock_s": 0.0},
    ]
    rep = summarize(rows)
    ok("totals: 4 attempts, 1 closed, 1 advanced", rep["totals"]["attempts"] == 4 and
       rep["totals"]["closed"] == 1 and rep["totals"]["advanced"] == 1)
    ok("claude_warm: 2 attempts, 1 closed, close_rate 0.5, median wc 150",
       rep["by_move"]["claude_warm"]["attempts"] == 2 and rep["by_move"]["claude_warm"]["closed"] == 1
       and rep["by_move"]["claude_warm"]["close_rate"] == 0.5
       and rep["by_move"]["claude_warm"]["median_wallclock_s"] == 150.0)
    ok("conjecture_lemma advanced counted", rep["by_move"]["conjecture_lemma"]["advanced"] == 1)
    ok("provider efficiency: claude 2 attempts / 1 closure", rep["by_provider"]["claude_opus_warm"]["attempts_per_closure"] == 2.0)
    ok("native provider has no closure ⇒ attempts_per_closure None", rep["by_provider"]["native"]["attempts_per_closure"] is None)
    ok("recent_runs split by run_tag", set(rep["recent_runs"]) == {"r1", "r2"})
    ok("empty rows ⇒ empty-but-shaped report", summarize([])["totals"]["attempts"] == 0)
    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
