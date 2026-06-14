#!/usr/bin/env python3
"""Compounding-curve telemetry (#110) — make the self-evolving loop's compounding LEGIBLE (or falsify it).

READ-ONLY over the governance exhaust (never a soundness surface):
  • adhoc_closure_certificates.jsonl  → kernel-closed rungs over time (the verified-rung tree growth)
  • solver_lane_attempts.db           → wallclock-per-rung trend + per-run move mix
  • RE-DERIVATION RATE                → closures whose target was ALREADY certified at attempt time
    (the amnesia metric: ~100% re-derivation before the 2026-06-12 persistence/compounding fixes; should → 0 after)

Usage:
  python -m scripts.public.control.leanmill.compounding_curve [--repo .] [--json OUT] [--selftest]
Emits a markdown summary to stdout; `--json` additionally writes a dashboard-shaped payload.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

CERTS_REL = "analytics/public/queries/adhoc_closure_certificates.jsonl"
DB_REL = "analytics/public/queries/solver_lane_attempts.db"


def load_certs(repo: Path) -> "list[dict]":
    p = repo / CERTS_REL
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue   # a torn line never breaks telemetry
    return sorted(out, key=lambda d: d.get("ts") or "")


def rungs_over_time(certs: "list[dict]") -> "list[dict]":
    """Cumulative kernel-closed DISTINCT targets by timestamp (the verified-rung growth curve)."""
    seen: set = set()
    curve = []
    for c in certs:
        if c.get("outcome") != "closed":
            continue
        t = c.get("target")
        if t in seen:
            continue
        seen.add(t)
        curve.append({"ts": c.get("ts"), "target": t, "cumulative_rungs": len(seen)})
    return curve


def rederivation_rate(certs: "list[dict]") -> dict:
    """Closures of an ALREADY-certified target = re-derivation (the amnesia metric). First closure per target is
    genuine; every later 'closed' cert for the same target re-proved known work. Rejections are excluded —
    governance refusing a re-proof is the system working, not amnesia."""
    first_ts: dict = {}
    redo, total = 0, 0
    by_target: "dict[str, int]" = defaultdict(int)
    for c in certs:
        if c.get("outcome") != "closed":
            continue
        t = c.get("target") or ""
        total += 1
        if t in first_ts:
            redo += 1
            by_target[t] += 1
        else:
            first_ts[t] = c.get("ts")
    return {"closures": total, "distinct_rungs": len(first_ts), "rederived": redo,
            "rederivation_rate": round(redo / total, 3) if total else None,
            "worst_offenders": sorted(by_target.items(), key=lambda kv: -kv[1])[:5]}


def wallclock_and_moves(repo: Path) -> dict:
    """Per-run-tag: attempts, closes, wallclock, and whether the RETIRED cold one-shots still fire (should be 0
    after the agent-first ladder, 2026-06-12)."""
    p = repo / DB_REL
    if not p.exists():
        return {}
    out: dict = {}
    try:
        with sqlite3.connect(str(p)) as con:
            rows = con.execute(
                "SELECT COALESCE(run_tag,'(untagged)'), COUNT(*), "
                "SUM(CASE WHEN outcome LIKE '%closed%' THEN 1 ELSE 0 END), "
                "ROUND(SUM(COALESCE(wallclock_s,0))), "
                "SUM(CASE WHEN provider IN ('claude_opus','codex_gpt5','gemini_flash','deepseek_v2',"
                "'leancopilot','leanhammer') THEN 1 ELSE 0 END) "
                "FROM attempts GROUP BY 1 ORDER BY MAX(attempt_at) DESC LIMIT 12").fetchall()
    except sqlite3.Error:
        return {}
    for tag, n, closes, wall, cold in rows:
        out[tag] = {"attempts": n, "closes": closes or 0, "wallclock_s": wall or 0,
                    "cold_oneshot_attempts": cold or 0}
    return out


def report(repo: Path) -> dict:
    certs = load_certs(repo)
    curve = rungs_over_time(certs)
    rr = rederivation_rate(certs)
    runs = wallclock_and_moves(repo)
    return {"curve": curve, "rederivation": rr, "runs": runs}


def render_markdown(rep: dict) -> str:
    lines = ["# Compounding curve — verified-rung growth + amnesia metric", ""]
    rr = rep["rederivation"]
    lines.append(f"**Distinct kernel-closed rungs:** {rr['distinct_rungs']}  |  "
                 f"**re-derivation rate:** {rr['rederivation_rate']} "
                 f"({rr['rederived']}/{rr['closures']} closures re-proved known work — should trend → 0 "
                 "after the 2026-06-12 persistence fixes)")
    if rr["worst_offenders"]:
        lines.append("  worst: " + ", ".join(f"{t}×{n}" for t, n in rr["worst_offenders"]))
    lines.append("\n## Rung growth")
    for pt in rep["curve"][-10:]:
        lines.append(f"- {str(pt['ts'])[:16]}  #{pt['cumulative_rungs']}  {pt['target']}")
    lines.append("\n## Recent runs (attempts / closes / wallclock / cold-oneshot attempts)")
    for tag, m in rep["runs"].items():
        cold_flag = "  ⚠️ cold one-shots fired (pre-agent-first?)" if m["cold_oneshot_attempts"] else ""
        lines.append(f"- `{tag}`: {m['attempts']} att, {m['closes']} closed, {m['wallclock_s']}s"
                     f", cold={m['cold_oneshot_attempts']}{cold_flag}")
    return "\n".join(lines)


def _selftest() -> int:
    import tempfile
    fails: "list[str]" = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    repo = Path(tempfile.mkdtemp(prefix="cc_"))
    (repo / "analytics/public/queries").mkdir(parents=True)
    certs = [
        {"ts": "2026-06-10T00:00:00", "target": "A", "outcome": "closed"},
        {"ts": "2026-06-11T00:00:00", "target": "B", "outcome": "closed"},
        {"ts": "2026-06-12T00:00:00", "target": "A", "outcome": "closed"},          # re-derivation
        {"ts": "2026-06-12T01:00:00", "target": "A", "outcome": "rejected_governance"},  # NOT amnesia
    ]
    (repo / CERTS_REL).write_text("\n".join(json.dumps(c) for c in certs))
    rep = report(repo)
    ok("curve counts distinct rungs in ts order",
       [p["cumulative_rungs"] for p in rep["curve"]] == [1, 2] and rep["curve"][0]["target"] == "A")
    ok("re-derivation: 1 of 3 closures; rejection excluded",
       rep["rederivation"]["closures"] == 3 and rep["rederivation"]["rederived"] == 1
       and rep["rederivation"]["rederivation_rate"] == 0.333)
    ok("missing DB is safe (empty runs)", rep["runs"] == {})
    ok("markdown renders", "re-derivation rate" in render_markdown(rep))
    ok("empty repo is safe", report(Path(tempfile.mkdtemp()))["rederivation"]["closures"] == 0)
    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


DEFAULT_JSON_REL = "analytics/public/leanmill/dashboard_data/compounding_curve.json"   # the leanmill dashboard home


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--json", nargs="?", const="DEFAULT", default=None,
                    help=f"also write the dashboard JSON (bare --json ⇒ {DEFAULT_JSON_REL})")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    repo = Path(a.repo).resolve()
    rep = report(repo)
    print(render_markdown(rep))
    if a.json:
        out = (repo / DEFAULT_JSON_REL) if a.json == "DEFAULT" else Path(a.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(rep, indent=2, default=str))
        print(f"\n[json] {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
