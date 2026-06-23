"""GP-166 Per-Class MRE Breakdown — surfaces holdout / farther-tail per
class so the mutator can SEE Hypothesis-U-vs-S failure structure on
any multi-class substrate.

The provider is substrate-agnostic. It reads
`workspace/gate_harness_result.json` (a JSON envelope written by the
substrate's `gate_harness.py` when the substrate exposes per-class MRE
buckets) and renders whatever class names the harness reported. It
makes no assumption that classes are named A/B/C, that the visible
class is "disk", or that the withheld classes are "clusters" or
"binaries" — those were one substrate's class names. The provider
discovers the visible class as the one with a non-zero
`holdout.per_class_mre` entry and the withheld classes as the ones
appearing only in `farther_tail.per_class_mre`.

Schema the provider expects in `gate_harness_result.json`:

    {
      "holdout":   { "per_class_mre": {<class>: <MRE>}, ... },
      "farther_tail": { "per_class_mre": {<class>: <MRE>}, ... },
      "farther_tail_class_<NAME>": { "mean_relative_error": ..., "passed": ..., "n": ... },
      "asymptotic": { "passed": ..., "violations": [...] }
    }

Substrate authors who want their `gate_harness.py` to drive this
provider should produce a file matching this schema. gp163d's
harness is the canonical example.

Engagement: applies whenever `gate_harness_result.json` exists with
`per_class_mre` populated. Skips quietly otherwise.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ztare.orchestrator.mutator_briefing import BriefingContext, BriefingProvider


class PerClassBreakdownProvider(BriefingProvider):
    """Surfaces per-class fit quality + Hypothesis-U-vs-S signal."""

    name = "per_class_breakdown"
    priority = 280  # between fit_telemetry (200) and gate_gap (250)

    def applies(self, ctx: BriefingContext) -> bool:
        if ctx.workspace_dir is None:
            return False
        path = ctx.workspace_dir / "gate_harness_result.json"
        return path.exists()

    def fragment(self, ctx: BriefingContext) -> str:
        path = ctx.workspace_dir / "gate_harness_result.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            return ""

        lines: list[str] = []
        lines.append("## Per-Class Fit Quality (latest iter)")
        lines.append("")

        # Holdout breakdown
        holdout = data.get("holdout") or {}
        if holdout.get("per_class_mre"):
            lines.append("**Holdout (visible-class withhold):**")
            lines.append(f"  - aggregate MRE: {holdout.get('mean_relative_error', 0):.4f} "
                         f"(threshold {holdout.get('threshold', 0):.2f}, "
                         f"{'PASS' if holdout.get('passed') else 'FAIL'}, "
                         f"n={holdout.get('n', 0)})")
            for cls, mre in sorted(holdout["per_class_mre"].items()):
                lines.append(f"  - class {cls}: MRE {mre:.4f}")
            lines.append("")

        # Farther-tail breakdown — the U-vs-S signal lives here.
        # Discover per-class farther-tail entries dynamically (any key
        # of the form "farther_tail_class_<NAME>") so the provider works
        # on any substrate's class naming convention.
        ft = data.get("farther_tail") or {}
        ft_per_class = {
            k.replace("farther_tail_class_", ""): v
            for k, v in data.items()
            if k.startswith("farther_tail_class_") and isinstance(v, dict)
        }
        if ft:
            lines.append("**Farther-tail (out-of-class extrapolation — Newton step):**")
            lines.append(f"  - aggregate MRE: {ft.get('mean_relative_error', 0):.4f} "
                         f"(threshold {ft.get('threshold', 0):.2f}, "
                         f"{'PASS' if ft.get('passed') else 'FAIL'}, "
                         f"n={ft.get('n', 0)})")
            for cls_name, cls_data in sorted(ft_per_class.items()):
                lines.append(
                    f"  - class `{cls_name}`: MRE "
                    f"{cls_data.get('mean_relative_error', 0):.4f} "
                    f"(n={cls_data.get('n', 0)}, "
                    f"{'PASS' if cls_data.get('passed') else 'FAIL'})"
                )
            lines.append("")

        # U-vs-S signal: discover the visible class dynamically as the
        # one whose MRE is referenced in holdout.per_class_mre. If
        # multiple visible classes exist, use the one with the lowest
        # MRE (the "easy" class) as the comparison anchor.
        u_failed = (
            holdout.get("passed", False)
            and not ft.get("passed", True)
        )
        if u_failed:
            visible_per_class = holdout.get("per_class_mre") or {}
            if visible_per_class:
                visible_anchor_class = min(
                    visible_per_class.items(), key=lambda kv: kv[1]
                )
                anchor_name, anchor_mre = visible_anchor_class
                lines.append("**Hypothesis-U-vs-S diagnosis:**")
                lines.append(
                    f"  - Holdout PASSED on visible class `{anchor_name}` "
                    f"(MRE {anchor_mre:.4f}) but farther-tail FAILED on "
                    f"out-of-class systems."
                )
                # Surface ratio for each withheld class with MRE >= 5× anchor
                for cls_name, cls_data in sorted(ft_per_class.items()):
                    cls_mre = cls_data.get("mean_relative_error", 0)
                    if anchor_mre > 0 and cls_mre / anchor_mre >= 5:
                        lines.append(
                            f"  - Class `{cls_name}` MRE is "
                            f"{cls_mre / anchor_mre:.0f}× larger than "
                            f"visible-class `{anchor_name}` MRE "
                            f"(visible={anchor_mre:.4f}, "
                            f"{cls_name}={cls_mre:.4f})."
                        )
                lines.append("")
            lines.append(
                "  **Hypothesis U (universal constant across classes) is rejected by "
                "the data.** Restating Hypothesis U on a similar form will produce the "
                "same farther-tail failure. To make progress, either:"
            )
            lines.append(
                "    (a) Pivot to **Hypothesis S** — express the crossover constant as "
                "a function of features (e.g. `system_class`, `mass_log10`, "
                "`radius_log10`). Use the per-class MRE structure above to inform "
                "which features carry the dependence."
            )
            lines.append(
                "    (b) **Commit to U as a publishable null** — explicitly state "
                "'universality of the crossover constant is empirically rejected by "
                "out-of-class data,' name the magnitude of the rejection, and stop "
                "fitting. The judge scores this path per the rubric's "
                "`Newton-Step Validation` criterion (70 if interpreted in U-vs-S terms)."
            )
            lines.append("")

        # Asymptotic check status (if present)
        asymp = data.get("asymptotic") or {}
        if asymp:
            status = "PASS" if asymp.get("passed") else "FAIL"
            lines.append(f"**Asymptotic regime checks:** {status}")
            for v in (asymp.get("violations") or [])[:3]:
                lines.append(f"  - {v}")
            lines.append("")

        return "\n".join(lines)
