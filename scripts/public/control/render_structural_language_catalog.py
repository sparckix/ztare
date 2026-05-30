#!/usr/bin/env python3
"""Render RD structural-language registries into a human-readable catalog."""

from __future__ import annotations

from pathlib import Path

from src.ztare.research_director.pde_estimate_craft_ops import (
    render_vocabulary_summary as render_pde_summary,
)
from src.ztare.research_director.problem_solving_ops import (
    render_vocabulary_summary as render_problem_solving_summary,
)
from src.ztare.research_director.theory_building_ops import (
    render_vocabulary_summary as render_theory_building_summary,
)
from src.ztare.research_director.two_cultures import render_two_cultures_summary
from src.ztare.research_director.universal_research_ops import (
    render_meta_meta_summary,
    render_vocabulary_summary as render_universal_summary,
)


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs/concepts/structural_language_catalog.md"


def main() -> int:
    sections = [
        "# Structural Language Catalog",
        "",
        "**Generated from Python registries. Do not hand-edit this file; run "
        "`python scripts/public/control/render_structural_language_catalog.py` "
        "after changing the registries.**",
        "",
        "Purpose: a readable public concept surface for the universal research "
        "language, the theory-builder/problem-solver split, meta-meta reframes, "
        "and GP-219 PDE estimate-craft language. The `.py` registries remain "
        "canonical because tick briefs, gates, and classifiers import them.",
        "",
        "## Use Rule",
        "",
        "Pattern catalog = how to move next. Structural language = what mechanism "
        "the move found or repaired. Pretick may require either move-layer v5 "
        "ops or game-layer `mm_*` ops when the tick changes what counts as the "
        "object, state, or admissible frame. Closure artifacts should include "
        "`structural_language_fingerprint` with universal ops, TB/PS culture, "
        "PDE ops or `not_applicable`, evidence pointer, and next-move effect.",
        "",
        render_universal_summary(),
        "",
        render_meta_meta_summary(),
        "",
        render_theory_building_summary(),
        "",
        render_problem_solving_summary(),
        "",
        render_two_cultures_summary(),
        "",
        render_pde_summary(),
        "",
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(sections), encoding="utf-8")
    print(OUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
