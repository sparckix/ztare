#!/usr/bin/env python3
"""v32_import_curated_rows.py — import pre-vetted rows from v2.1+ harness.

Anti-amnesia: instead of inventing new test rows, import the scientifically-
vetted rows from v2000+ that the v2.1+ row-isolation harness already
curated. Each row has:
  - row_id (canonical handle into the apparatus)
  - theorem (lemma name)
  - source_file (Mathlib path)
  - score (priority)
  - quarantine flag (if any) + reason

Output: /tmp/v32_curated_test_rows.json — flat list ready for batch dispatch
into route_c_layer_2c_dispatch.py.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
LR = ROOT / "analytics/public/leanmill"

# Mathlib in the v28A sandbox (anchor for resolving Mathlib source paths)
MATHLIB_ROOT = (
    LR / "external_benchmarks/sandboxes/v28A_carleson_baseline/carleson/"
       ".lake/packages/mathlib"
)


def resolve_source_path(source_file: str) -> Path | None:
    """Resolve a Mathlib source path like `Mathlib/Topology/AlexandrovDiscrete.lean`."""
    candidate = MATHLIB_ROOT / source_file
    if candidate.exists():
        return candidate
    # Try without leading "Mathlib/" if path already starts with it
    alt = MATHLIB_ROOT / source_file.replace("Mathlib/", "", 1)
    if alt.exists():
        return alt
    return None


def import_v2000_rows() -> list[dict]:
    """Source-safe + quarantined rows from v2000."""
    p = LR / "v2000_fresh_queue_source_safety_audit.json"
    d = json.load(open(p))
    out = []
    for r in d.get("primary_source_safe_next_queue", []):
        sf = r.get("source_file", "")
        path = resolve_source_path(sf)
        out.append({
            "import_source": "v2000_primary_source_safe",
            "row_id": r.get("row_id"),
            "theorem": r.get("theorem"),
            "source_file": sf,
            "resolved_path": str(path) if path else None,
            "score": r.get("score"),
            "quarantined": False,
            "quarantine_reason": None,
            "gold_tactic_exposed": r.get("interactive_gold_tactic_exposure"),
        })
    for r in d.get("quarantined_rows", []):
        sf = r.get("source_file", "")
        path = resolve_source_path(sf)
        out.append({
            "import_source": "v2000_quarantined",
            "row_id": r.get("row_id"),
            "theorem": r.get("theorem"),
            "source_file": sf,
            "resolved_path": str(path) if path else None,
            "score": r.get("score"),
            "quarantined": True,
            "quarantine_reason": r.get("basis"),
            "gold_tactic_exposed": r.get("interactive_gold_tactic_exposure"),
        })
    return out


def import_v2003_rows() -> list[dict]:
    """High-yield bundle from v2003."""
    p = LR / "v2003_high_scientific_yield_row_selector.json"
    d = json.load(open(p))
    out = []
    for r in d.get("high_yield_bundle", []):
        sf = r.get("source_file", "")
        path = resolve_source_path(sf) if sf else None
        out.append({
            "import_source": "v2003_high_yield",
            "row_id": r.get("row_id"),
            "theorem": r.get("theorem"),
            "source_file": sf,
            "resolved_path": str(path) if path else None,
            "score": r.get("scientific_yield_score") or r.get("model_rank_min"),
            "quarantined": False,
            "lane_id": r.get("lane_id"),
            "body_line_count": r.get("body_line_count"),
            "top_area": r.get("top_area"),
            "tautology_risk": r.get("tautology_risk"),
            "gold_target_closed_in_prior_run": r.get("gold_target_closed"),
            "decision_impact_if_replayed": r.get("decision_impact_if_replayed"),
        })
    return out


def main():
    rows = []
    rows.extend(import_v2000_rows())
    rows.extend(import_v2003_rows())

    n_resolved = sum(1 for r in rows if r.get("resolved_path"))
    n_quarantined = sum(1 for r in rows if r.get("quarantined"))
    print(f"# v32 curated row import")
    print(f"Total rows: {len(rows)}")
    print(f"With resolved source paths: {n_resolved}")
    print(f"Quarantined (gold-tactic exposed in prior session, do NOT test): {n_quarantined}")
    print(f"Source-safe + high-yield (USABLE for v32 Route C testing): {len(rows) - n_quarantined}")

    # Output
    out_path = Path("/tmp/v32_curated_test_rows.json")
    out_path.write_text(json.dumps({
        "total": len(rows),
        "resolved": n_resolved,
        "quarantined": n_quarantined,
        "usable": len(rows) - n_quarantined,
        "sources": ["v2000_fresh_queue_source_safety_audit", "v2003_high_scientific_yield_row_selector"],
        "rows": rows,
    }, indent=2))
    print(f"\nwrote {out_path}")
    print()
    print("## Usable rows (first 10)")
    usable = [r for r in rows if not r.get("quarantined")]
    for r in usable[:10]:
        path_marker = "✓" if r.get("resolved_path") else "✗"
        print(f"  {path_marker} [{r['import_source']}] row_id={r.get('row_id')} thm={r.get('theorem','?')[:50]}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
