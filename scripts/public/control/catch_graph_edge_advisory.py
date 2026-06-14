#!/usr/bin/env python3
"""catch_graph_edge_advisory.py — conservative, leakage-free advisory that
derives the `surfaced_catch` graph-edge layer from the catch ledger ONLY
where the structured `category` field maps UNAMBIGUOUSLY to an
ANTI-PATTERN id.

Why this is an *advisory*, not an auto-writer (the 2026-05-15
mechanization principle, docs/concepts/closure_claim_governance.md §3):

  - `surfaced_catch` IS a ledger-derivable fact and should not be
    hand-maintained — but the ledger's `category` is a FREE-FORM string,
    not a controlled vocabulary keyed to AP ids. Only the unambiguous
    subset can be derived deterministically; force-mapping the rest would
    itself be a laundered "derived" fact.
  - `impact_factor_expost` legitimately encodes human judgment (recency,
    climb-triggers, decision-criticality) the ledger cannot fully capture, so
    this tool only PROPOSES, never overwrites (RP-001 falsifier watches
    for impact decaying into a rename of frequency).

Root-cause finding this tool surfaces: the real fix is upstream — make
`category` a controlled vocabulary of AP ids at catch-ratification time.
Until then, full mechanization is correctly impossible and this conservative
advisory is the proportionate mechanization.

CPU-only. Dry-run only (prints; never writes graph.yaml).

Usage:
  python3 scripts/public/control/catch_graph_edge_advisory.py
  python3 scripts/public/control/catch_graph_edge_advisory.py --json
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
LEDGER = REPO / "analytics/public/ledgers/catch/catch_ledger.jsonl"
GRAPH = REPO / "src/ztare/architecture_index/graph.yaml"

# ONLY unambiguous category -> ANTI-PATTERN capability id mappings.
# Deliberately partial: anything not here is reported UNMAPPED, never
# force-fit. Extend ONLY when a category is a 1:1 match to an AP slug.
UNAMBIGUOUS_CATEGORY_TO_AP = {
    "sorry_obligation_laundering": "ANTI-PATTERN-004-SORRY-OBLIGATION-LAUNDERING",
    "citation_laundering": "ANTI-PATTERN-002-CITATION-LAUNDERING",
}


def load_ledger() -> list[dict]:
    if not LEDGER.exists():
        return []
    return [json.loads(l) for l in LEDGER.read_text().splitlines() if l.strip()]


def current_graph_edges() -> dict[str, set[str]]:
    """capability -> set(surfaced_catch) from graph.yaml (fail-soft)."""
    out: dict[str, set[str]] = defaultdict(set)
    try:
        import yaml  # type: ignore
        d = yaml.safe_load(GRAPH.read_text()) or {}
        for e in d.get("edges", []):
            if isinstance(e, dict) and e.get("capability"):
                sc = e.get("surfaced_catch") or []
                if isinstance(sc, list):
                    out[e["capability"]] = set(sc)
    except Exception:
        pass
    return out


def build_advisory() -> dict:
    rows = load_ledger()
    ratified = [r for r in rows if r.get("status") == "ratified"]
    derived: dict[str, list[str]] = defaultdict(list)
    unmapped: dict[str, int] = defaultdict(int)
    for r in ratified:
        cat = r.get("category", "")
        ap = UNAMBIGUOUS_CATEGORY_TO_AP.get(cat)
        if ap:
            derived[ap].append(r["catch_id"])
        else:
            unmapped[cat] += 1

    graph = current_graph_edges()
    proposals = []
    for ap, catch_ids in sorted(derived.items()):
        have = graph.get(ap, set())
        missing = sorted(set(catch_ids) - have)
        if missing:
            proposals.append({
                "capability": ap,
                "add_surfaced_catch": missing,
                "current_in_graph": sorted(have),
                "impact_advisory": (
                    f"ledger-derived ratified catch count = {len(set(catch_ids))}; "
                    f"PROPOSAL ONLY — do not overwrite hand-judged "
                    f"impact_factor_expost (encodes recency/climb-trigger judgment)"
                ),
            })
    return {
        "ratified_catches": len(ratified),
        "total_catches": len(rows),
        "deterministic_proposals": proposals,
        "unmapped_categories": dict(sorted(unmapped.items(),
                                           key=lambda kv: -kv[1])),
        "root_cause": (
            "catch_ledger `category` is a free-form string, not a "
            "controlled vocabulary of AP ids. Full mechanization is "
            "correctly impossible until `category` is constrained at "
            "ratification time. This advisory mechanizes only the "
            "unambiguous subset (by design)."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    adv = build_advisory()
    if args.json:
        print(json.dumps(adv, indent=2))
        return 0
    print(f"  catch ledger: {adv['ratified_catches']} ratified "
          f"/ {adv['total_catches']} total")
    props = adv["deterministic_proposals"]
    if not props:
        print("  no surfaced_catch drift on unambiguously-mapped APs "
              "(graph.yaml is consistent with the derivable subset)")
    for p in props:
        print(f"  {p['capability']}: + surfaced_catch "
              f"{p['add_surfaced_catch']} (advisory; review before edit)")
        print(f"    {p['impact_advisory']}")
    print("  UNMAPPED ratified categories (NOT force-fit — upstream fix):")
    for cat, n in adv["unmapped_categories"].items():
        print(f"    {n:3d}  {cat}")
    print(f"  root cause: {adv['root_cause']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
