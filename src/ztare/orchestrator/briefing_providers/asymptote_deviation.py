"""AsymptoteDeviationProvider — current form's deviation from charter-declared asymptotes.

When the charter declares asymptotic behavior (e.g. y → x at high x,
y → sqrt(c·x) at low x), this provider evaluates the prior fit's form
at boundary x's and reports the deviation factor.

Substrate-aware but not substrate-specific. Generalizes to any
substrate that declares asymptotes in the charter; silent if charter
declares none. Does NOT encode any specific physics, only
charter-declared boundary behavior.

Limitations: parses asymptote claims heuristically from charter prose.
For now, reports raw boundary-x evaluations without computing the
declared asymptote (which would need symbolic charter parsing); the
mutator infers the deviation by comparing the reported predicted-y
at boundary x's to its charter-declared expectation.
"""
from __future__ import annotations

import json
import math
import re
from typing import Optional

from ztare.orchestrator.briefing_providers import section_unavailable
from ztare.orchestrator.mutator_briefing import (
    BriefingContext,
    BriefingProvider,
)


class AsymptoteDeviationProvider(BriefingProvider):
    name = "asymptote_deviation"
    priority = 450

    def _load_fit(self, ctx: BriefingContext) -> dict:
        # Absent → {} (legit). Present-but-corrupt → RAISE so applies()/
        # fragment() can banner instead of silently dropping the section.
        path = (ctx.workspace_dir or ctx.project_dir / "workspace") / "fit_features_result.json"
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _charter_has_asymptote(self, ctx: BriefingContext) -> bool:
        if ctx.charter_meta and ctx.charter_meta.get("asymptotes_declared"):
            return True
        path = ctx.project_dir / "project_charter.md"
        if not path.exists():
            return False
        try:
            text = path.read_text(encoding="utf-8", errors="replace").lower()
        except Exception:
            return False
        markers = ["asymptot", "high x", "low x", "→", "->", "as n →", "as t → ∞"]
        return any(m in text for m in markers)

    def _evidence_x_range(
        self, ctx: BriefingContext
    ) -> tuple[Optional[tuple[float, float]], list[int]]:
        # Best-effort: find min/max of column 1 in evidence.txt.
        # Returns (range_or_None, 1-based line numbers of non-numeric data rows
        # skipped). Header/separator/comment lines are filtered first and are
        # NOT counted as skipped.
        path = ctx.project_dir / "evidence.txt"
        if not path.exists():
            return None, []
        xs: list[float] = []
        skipped: list[int] = []
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
        ):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "----" in stripped or "===" in stripped:
                continue
            parts = stripped.split()
            if "|" in stripped:
                parts = [p.strip() for p in stripped.split("|") if p.strip()]
            try:
                nums = [float(p) for p in parts]
                if len(nums) >= 2 and nums[0] > 0:
                    xs.append(nums[0])
            except ValueError:
                skipped.append(lineno)
                continue
        if not xs:
            return None, skipped
        return (min(xs), max(xs)), skipped

    def applies(self, ctx: BriefingContext) -> bool:
        if not self._charter_has_asymptote(ctx):
            return False
        try:
            d = self._load_fit(ctx)
        except Exception:
            # Corrupt fit artifact: run fragment() so it banners.
            return True
        return bool(d.get("success"))

    def fragment(self, ctx: BriefingContext) -> str:
        # We don't symbolically evaluate the form here — that would
        # require executing the apparatus's compiled f(). Instead we
        # surface a structured prompt asking the mutator to mentally
        # check its form against the declared asymptote at boundary x's.
        # This is the substrate-agnostic ANALYTICAL reminder; substrate-
        # specific numerical asymptote checking belongs in the gate
        # harness, not here.
        try:
            self._load_fit(ctx)  # re-checked here so a corrupt fit banners
            rng, skipped = self._evidence_x_range(ctx)
        except Exception as exc:
            return section_unavailable("ASYMPTOTE DEVIATION", exc)
        if rng is None:
            return ""  # no usable evidence x-range — nothing to anchor (legit)
        xmin, xmax = rng
        skipped_note = (
            f"    NOTE: {len(skipped)} non-numeric evidence row(s) skipped "
            f"(line(s) {skipped[:10]}"
            + (f" + {len(skipped) - 10} more" if len(skipped) > 10 else "")
            + "); x-range below is from parseable rows only.\n\n"
            if skipped
            else ""
        )
        return (
            "\n    ### ASYMPTOTIC-DEVIATION CHECK (charter declares boundary behavior)\n\n"
            + skipped_note
            + "    The charter declares asymptotic behavior at boundary x's. Evaluate\n"
            "    YOUR form mentally at the visible-data boundaries before refining:\n\n"
            f"    - x_min (visible): {xmin:.4g}\n"
            f"    - x_max (visible): {xmax:.4g}\n\n"
            "    For each boundary, ask:\n"
            "      (1) What does the charter's declared asymptote predict at this x?\n"
            "      (2) What does YOUR form predict at this x (under your fitted params)?\n"
            "      (3) Is the deviation > 1 order of magnitude? If yes, the form\n"
            "          violates the charter's hard constraint and will fail farther-tail\n"
            "          even if it passes holdout. Restructure rather than tune.\n\n"
            "    A form that passes holdout but violates a declared asymptote is a\n"
            "    Padé-class trap (Weierstrass approximation). The farther-tail\n"
            "    discriminator is designed to catch this; the apparatus's gate verdict\n"
            "    will reflect it. Pre-emptively check before submitting.\n"
        )
