#!/usr/bin/env python3
"""build_graph_sowhat.py — "so what" freshness GATE + numbers digest.

Operator 2026-05-16: the per-graph "so what" headline is NOT templated/
deterministic. It is authored IN FLIGHT by the agent doing that week's
update (the one who just ran the mine, saw the adversary results, knows
what actually matters this cycle). Templates cannot say "Soph-D collapsed
to 20 — loop throughput died, and that is the point."

This script therefore does NOT write headlines. It:
  1. prints the salient numbers the updating agent needs to author from;
  2. GATES: fails loud if analytics/public/queries/graph_sowhat.json is
     missing or older than the fresh bifurcation report (i.e. the agent
     did not re-author the so-what this cycle).

The dashboard renders graph_sowhat.json["panels"][k]["headline"] above
each chart. Schema per panel: {headline, detail, trend}.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

REPO = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
Q = REPO / "analytics" / "public" / "queries"
SOWHAT = Q / "graph_sowhat.json"
BIF = REPO / "analytics/public/ledgers/reflexive/bifurcation_report.json"
REQUIRED_PANELS = ["bifurcation", "sophistication", "insight_volume",
                   "taste", "compounding", "recursive_gain"]


def _load(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def main() -> int:
    # --- numbers digest (so the updating agent authors from data) ---
    print("=== so-what numbers digest (author headlines from THESE) ===")
    bif = _load(BIF)
    if bif:
        cum = bif["bifurcation"]
        t = bif.get("as_of_today", {}).get("modified_last_7d", {})
        print(f"  bifurcation: cumulative out-of-loop "
              f"{round(cum['agent_work_share']*100)}% | live-7d "
              f"{round(100*t.get('agent_work',0)/max(1,t.get('all',1)))}%")
    tc = _load(Q / "trajectory" / "trajectory_curves.json")
    if tc:
        c = tc.get("curves", {})
        def ser(k):
            v = c.get(k, {})
            return [x for _, x in sorted(v.items())] if isinstance(v, dict) else v
        print(f"  Soph-A cumulative capability: {ser('sophistication_a_capability_count_cumulative')}")
        print(f"  Soph-D autonomous actions/wk: {ser('sophistication_d_autonomous_actions_per_week')}")
    tw = _load(Q / "taste" / "taste_weighted_insight.json")
    if tw:
        ws = tw.get("weekly_stats", {})
        print("  taste mean by week: " +
              ", ".join(f"{k}={ws[k]['mean_score']}" for k in sorted(ws)))

    # --- the GATE ---
    if not SOWHAT.exists():
        print("\nGATE FAIL: graph_sowhat.json missing. The updating agent "
              "must author per-graph so-what headlines this cycle "
              f"(panels: {REQUIRED_PANELS}).")
        return 2
    sw = _load(SOWHAT) or {}
    panels = sw.get("panels", {})
    missing = [p for p in REQUIRED_PANELS if p not in panels]
    if missing:
        print(f"\nGATE FAIL: graph_sowhat.json missing panels: {missing}")
        return 2
    if bif and SOWHAT.stat().st_mtime < BIF.stat().st_mtime:
        print("\nGATE FAIL: graph_sowhat.json is STALE (older than the fresh "
              "bifurcation report). The updating agent must RE-AUTHOR the "
              "so-what headlines from this cycle's numbers — do not ship "
              "last week's interpretation over this week's data.")
        return 2
    print(f"\nGATE OK: {len(panels)} fresh agent-authored so-what headlines.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
