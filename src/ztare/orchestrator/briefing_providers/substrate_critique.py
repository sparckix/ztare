"""GP-167 SubstrateCritic Briefing — surfaces the substrate's structural
critique to the mutator each iter.

Reads `workspace/substrate_critique.json` (written by the pre-flight
hook in autoresearch_loop when rubric.enable_substrate_critic=True) and
renders the operator-actionable items as a markdown fragment. The
provider is read-only and never modifies the substrate; the mutator
sees the same critique the operator does.

The critique exposes structural facts the apparatus has measured but
that the mutator cannot derive from the visible data alone:

  * Feature dimensionality collapses — features whose within-visible-
    class variance is too small to constrain a free parameter.
  * Cross-class signal — which features have range overlap between
    visible and withheld classes (i.e., which features actually carry
    extrapolation power).
  * Data artifacts — known instrument-artifact patterns detected in
    the raw data (e.g., y/x systematically below 1 for a class).
  * Regime breaks in the raw data — discontinuities the form must
    accommodate.
  * Epistemic voids — synthesized statements of what the substrate
    CANNOT decide given the visible data, with operator-level
    suggested fixes.

Mutator-facing tone: this is what the substrate shows you that the fit
result alone does not. Constraints on what forms can be honestly
proposed given the data's structural limits.
"""
from __future__ import annotations

import json

from src.ztare.orchestrator.mutator_briefing import BriefingContext, BriefingProvider


class SubstrateCritiqueBriefingProvider(BriefingProvider):
    """Surfaces GP-167 substrate critique to the mutator briefing."""

    name = "substrate_critique"
    priority = 230  # right after fit_telemetry / noise_profile

    def applies(self, ctx: BriefingContext) -> bool:
        if ctx.workspace_dir is None:
            return False
        return (ctx.workspace_dir / "substrate_critique.json").exists()

    def fragment(self, ctx: BriefingContext) -> str:
        path = ctx.workspace_dir / "substrate_critique.json"
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return ""

        lines: list[str] = []
        lines.append("## Substrate Critique (GP-167)")
        lines.append("")
        lines.append(
            "What the substrate's raw data shows, doesn't show, and "
            "cannot constrain. These are structural facts the apparatus "
            "has measured directly from the data — independent of any "
            "fit. Treat them as binding when proposing forms."
        )
        lines.append("")
        if d.get("summary"):
            lines.append(f"**Verdict:** {d['summary']}")
            lines.append("")

        # Cross-class signal — which features can/cannot extrapolate
        cc = d.get("cross_class_signal") or []
        if cc:
            lines.append("**Cross-class extrapolation power per feature:**")
            for item in cc:
                power = item.get("extrapolation_power", "unknown")
                fk = item.get("feature_key", "?")
                vis = item.get("visible_range")
                wth = item.get("withheld_range")
                lines.append(
                    f"  - `{fk}`: extrapolation={power} "
                    f"(visible {vis}, withheld {wth}, "
                    f"overlap {item.get('overlap_fraction_of_withheld', 0):.0%} of withheld span)"
                )
            lines.append("")
            lines.append(
                "  Forms that depend on a `extrapolation=none` feature "
                "cannot be constrained by visible-class fitting; the "
                "fit primitive will absorb those parameters into noise."
            )
            lines.append("")

        # Dimensionality collapses
        cols = d.get("feature_dimensionality_collapses") or []
        if cols:
            lines.append("**Feature dimensionality collapses (visible class):**")
            for c in cols:
                lines.append(
                    f"  - `{c.get('feature_key')}` in class "
                    f"{c.get('class')!r}: relative range "
                    f"{c.get('relative_range', 0):.2g}"
                )
            lines.append(
                "  These features have near-zero within-class variance. "
                "Any free parameter coefficient on them will be "
                "unconstrainable from visible data."
            )
            lines.append("")

        # Data artifacts
        art = d.get("data_artifacts_suspected") or []
        if art:
            lines.append("**Suspected data artifacts:**")
            for a in art:
                lines.append(
                    f"  - {a.get('kind')} in class {a.get('class')!r}: "
                    f"{a.get('implication', '')}"
                )
            lines.append("")

        # Regime breaks
        rb = d.get("regime_breaks_in_data") or []
        if rb:
            lines.append("**Regime breaks in raw data:**")
            for r in rb:
                lines.append(
                    f"  - {r.get('primary_feature')} = "
                    f"{r.get('split_at_x')}: log10|y| jump of "
                    f"{r.get('log10_y_jump')} dex. "
                    f"{r.get('implication', '')}"
                )
            lines.append("")

        # Epistemic voids — the priority items
        voids = d.get("epistemic_voids") or []
        if voids:
            lines.append("**Epistemic voids (what the substrate cannot decide):**")
            # Group by stage: pre-flight first, post-fit second
            preflight_voids = [v for v in voids if not str(v.get("stage", "")).startswith("post_fit")]
            postfit_voids = [v for v in voids if str(v.get("stage", "")).startswith("post_fit")]
            for v in preflight_voids[:4]:
                unknown = v.get("unknown", "")
                why = v.get("why_it_matters", "")
                blocking = v.get("blocking", "")
                lines.append(f"  - **{unknown}**")
                if why:
                    lines.append(f"    why it matters: {why}")
                if blocking:
                    lines.append(f"    blocking: {blocking}")
            if postfit_voids:
                lines.append("")
                lines.append("  Post-fit residual analysis (current iter):")
                for v in postfit_voids[:3]:
                    unknown = v.get("unknown", "")
                    why = v.get("why_it_matters", "")
                    blocking = v.get("blocking", "")
                    lines.append(f"  - **{unknown}**")
                    if why:
                        lines.append(f"    why it matters: {why}")
                    if blocking:
                        lines.append(f"    blocking: {blocking}")
            if len(voids) > 7:
                lines.append(f"  ... and {len(voids) - 7} more")
            lines.append("")
            lines.append(
                "  These are not apparatus failures. They are limits of "
                "what visible data can tell you. The honest move on a "
                "substrate with unresolved voids is either to commit to "
                "a publishable null *with* the void as the caveat, or "
                "to ask the operator for substrate enrichment before "
                "proposing forms that the data cannot constrain."
            )
            lines.append("")

        # Operator-actionable suggestions sidecar — gated, never auto-applied
        sug_path = ctx.workspace_dir / "substrate_critique_suggestions.json"
        if sug_path.exists():
            try:
                sd = json.loads(sug_path.read_text(encoding="utf-8"))
                action_needed = [
                    s for s in (sd.get("suggestions") or [])
                    if s.get("operator_action_needed")
                ]
                if action_needed:
                    lines.append("**Operator-action-needed (substrate edits proposed, NOT auto-applied):**")
                    for s in action_needed[:4]:
                        kind = s.get("kind", "?")
                        ev = s.get("evidence", "")
                        lines.append(f"  - kind: `{kind}` — {ev}")
                        for opt in (s.get("options") or [])[:3]:
                            lines.append(f"    • option: {opt}")
                    if len(action_needed) > 4:
                        lines.append(f"  ... and {len(action_needed) - 4} more")
                    lines.append("")
                    lines.append(
                        "  These are proposals to the operator, not to "
                        "the mutator. The apparatus does not auto-edit "
                        "features.py or the rubric. As the mutator: do "
                        "not assume any of these will be applied this "
                        "iter. Propose forms that work given the "
                        "substrate AS IT IS NOW."
                    )
                    lines.append("")
            except Exception:
                pass

        return "\n".join(lines)
