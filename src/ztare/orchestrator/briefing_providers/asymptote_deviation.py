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

from ztare.orchestrator.mutator_briefing import (
    BriefingContext,
    BriefingProvider,
)


class AsymptoteDeviationProvider(BriefingProvider):
    name = "asymptote_deviation"
    priority = 450

    def _load_fit(self, ctx: BriefingContext) -> dict:
        path = (ctx.workspace_dir or ctx.project_dir / "workspace") / "fit_features_result.json"
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

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

    def _evidence_x_range(self, ctx: BriefingContext) -> Optional[tuple[float, float]]:
        # Best-effort: find min/max of column 1 in evidence.txt
        path = ctx.project_dir / "evidence.txt"
        if not path.exists():
            return None
        xs = []
        try:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
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
                    continue
        except Exception:
            return None
        if not xs:
            return None
        return (min(xs), max(xs))

    def applies(self, ctx: BriefingContext) -> bool:
        if not self._charter_has_asymptote(ctx):
            return False
        d = self._load_fit(ctx)
        return bool(d.get("success"))

    def fragment(self, ctx: BriefingContext) -> str:
        # We don't symbolically evaluate the form here — that would
        # require executing the apparatus's compiled f(). Instead we
        # surface a structured prompt asking the mutator to mentally
        # check its form against the declared asymptote at boundary x's.
        # This is the substrate-agnostic ANALYTICAL reminder; substrate-
        # specific numerical asymptote checking belongs in the gate
        # harness, not here.
        rng = self._evidence_x_range(ctx)
        if rng is None:
            return ""
        xmin, xmax = rng
        return (
            "\n    ### ASYMPTOTIC-DEVIATION CHECK (charter declares boundary behavior)\n\n"
            "    The charter declares asymptotic behavior at boundary x's. Evaluate\n"
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
