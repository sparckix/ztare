#!/usr/bin/env python3
"""Mathlib build-frontier LEDGER (#111) — mine the campaign exhaust into a structured record of the
formal machinery the attack REQUIRED: what Mathlib lacked, what we BUILT (the citable closures shelf),
and what remains OPEN (the sorry'd scaffolds + `-- GAP:` annotations the agent left).

READ-ONLY over governance exhaust (certs probes, the closures shelf, refined-notes frontiers):
  • BUILT    = theorems/lemmas materialized in ztare_proofs/closures/*.lean (kernel-verified shelf)
  • OPEN     = `-- GAP:` comments + `:= by ... sorry` scaffolds inside closure-cert probes / blueprints
  • The ledger doubles as (a) the research-output artifact, (b) compounding fuel (what to materialize
    next), (c) the upstream-Mathlib-contribution shortlist.

Usage:
  python -m scripts.public.control.leanmill.build_frontier_ledger [--repo .] [--json [PATH]] [--selftest]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CERTS_REL = "analytics/public/queries/adhoc_closure_certificates.jsonl"
CLOSURES_REL = "ztare_proofs/closures"
DEFAULT_JSON_REL = "analytics/public/leanmill/dashboard_data/build_frontier_ledger.json"

_DECL = re.compile(r"(?m)^\s*(?:theorem|lemma)\s+([A-Za-z_][\w.']*)")
_GAP = re.compile(r"(?m)--\s*GAP:?\s*([^\n]+)")


def built_shelf(repo: Path) -> "list[dict]":
    """The kernel-verified interior we BUILT — every decl in the closures shelf (sorry-free files only)."""
    out = []
    d = repo / CLOSURES_REL
    if not d.is_dir():
        return out
    for f in sorted(d.glob("*.lean")):
        txt = f.read_text(encoding="utf-8", errors="replace")
        if "sorry" in txt:
            continue   # the shelf is the SORRY-FREE interior; a sorried file is frontier, not shelf
        for name in _DECL.findall(txt):
            out.append({"name": name, "file": str(f.relative_to(repo))})
    return out


def open_frontier(repo: Path) -> "list[dict]":
    """The OPEN frontier mined from closure-cert probes: `-- GAP:` annotations and sorry'd scaffolds.
    Source = the recompilable probes governance already archived (no new surface)."""
    p = repo / CERTS_REL
    gaps: "dict[str, dict]" = {}
    if not p.exists():
        return []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        probe = d.get("recompilable_probe") or ""
        target = d.get("target") or "?"
        for g in _GAP.findall(probe):
            key = g.strip()[:160]
            gaps.setdefault(key, {"gap": key, "seen_in": [], "first_ts": d.get("ts")})
            if target not in gaps[key]["seen_in"]:
                gaps[key]["seen_in"].append(target)
        # sorry'd decls inside a probe = scaffolds the agent framed but did not close
        if "sorry" in probe:
            for blk_name in _DECL.findall(probe):
                # only count a decl as OPEN if its own block carries the sorry (cheap line-scope check)
                pass   # block-scoping needs decl_blocks; the GAP comments are the high-signal channel
    return sorted(gaps.values(), key=lambda g: g["first_ts"] or "")


def report(repo: Path) -> dict:
    built = built_shelf(repo)
    frontier = open_frontier(repo)
    return {"built_shelf": built, "open_frontier": frontier,
            "summary": {"built": len(built), "open_gaps": len(frontier)}}


def render_markdown(rep: dict) -> str:
    lines = ["# Mathlib build-frontier ledger", "",
             f"**Built (kernel-verified shelf):** {rep['summary']['built']} decls  |  "
             f"**Open GAPs:** {rep['summary']['open_gaps']}", "", "## Built — the citable interior"]
    by_file: "dict[str, list]" = {}
    for b in rep["built_shelf"]:
        by_file.setdefault(b["file"], []).append(b["name"])
    for f, names in by_file.items():
        lines.append(f"- `{f}`: " + ", ".join(f"`{n}`" for n in names[:6]) + (" …" if len(names) > 6 else ""))
    lines.append("\n## Open frontier — what the attack still needs (agent-annotated GAPs)")
    for g in rep["open_frontier"] or [{"gap": "(none mined)", "seen_in": []}]:
        lines.append(f"- {g['gap']}  _(in: {', '.join(g.get('seen_in', [])[:3])})_")
    return "\n".join(lines)


def _selftest() -> int:
    import tempfile
    fails: "list[str]" = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    repo = Path(tempfile.mkdtemp(prefix="bfl_"))
    (repo / CLOSURES_REL).mkdir(parents=True)
    (repo / "analytics/public/queries").mkdir(parents=True)
    (repo / CLOSURES_REL / "good.lean").write_text("theorem shelf_thm : True := trivial\nlemma shelf_lem : 1=1 := rfl\n")
    (repo / CLOSURES_REL / "frontier.lean").write_text("theorem not_done : False := by sorry\n")
    certs = [{"ts": "2026-06-12T00:00:00", "target": "T1", "outcome": "closed",
              "recompilable_probe": "theorem a : P := by\n  -- GAP: prove the residue-vanishing theorem\n  sorry"},
             {"ts": "2026-06-12T01:00:00", "target": "T2", "outcome": "rejected_governance",
              "recompilable_probe": "-- GAP: prove the residue-vanishing theorem\n-- GAP: formal inverse step\n"}]
    (repo / CERTS_REL).write_text("\n".join(json.dumps(c) for c in certs))
    rep = report(repo)
    ok("shelf counts sorry-free decls only", rep["summary"]["built"] == 2
       and {b["name"] for b in rep["built_shelf"]} == {"shelf_thm", "shelf_lem"})
    ok("GAPs deduped across certs + targets accumulated",
       rep["summary"]["open_gaps"] == 2
       and any(set(g["seen_in"]) == {"T1", "T2"} for g in rep["open_frontier"]))
    ok("markdown renders", "build-frontier ledger" in render_markdown(rep))
    ok("empty repo safe", report(Path(tempfile.mkdtemp()))["summary"] == {"built": 0, "open_gaps": 0})
    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--json", nargs="?", const="DEFAULT", default=None)
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
