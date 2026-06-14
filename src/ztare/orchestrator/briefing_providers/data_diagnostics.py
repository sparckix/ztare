"""GP-167 unified Data Diagnostics — one briefing surface for the
substrate's structural state and the data's noise profile.

This provider replaces two earlier providers (`noise_profile` and
`substrate_critique`) with a single unified view. The architectural
reason, surfaced by the 2026-04-25 epistemic panel review: both modules
operate on the same conceptual layer ("measure before you assume")
but emit through separate briefing surfaces, which forced the mutator
to reconcile two parallel diagnostic streams.

Unification keeps the same backend modules (noise_profile.py and
substrate_critic.py both still own their JSON artifacts) and merges
their views at render time. The mutator now sees one section titled
"Data Diagnostics" with three sub-views:

  1. Noise profile — what kind of noise the data carries (post-fit
     residuals or pre-flight baseline).
  2. Substrate structure — what the substrate's data shows, doesn't
     show, and cannot constrain.
  3. Operator-action-needed — proposed substrate edits NOT auto-applied.

The provider is read-only and never modifies the substrate. It applies
when either the noise_profile.json or the substrate_critique.json
artifact exists in the workspace.

Backward compatibility: when only one of the two artifacts is
present, the corresponding sub-view is still rendered and the other
sub-view is silently omitted. Substrates that adopt only one of the
two diagnostic modules continue to work.
"""
from __future__ import annotations

import json
import re

from src.ztare.orchestrator.mutator_briefing import BriefingContext, BriefingProvider


# Numeric-redaction helpers (2026-04-26). The substrate critic
# emits implication strings like "below 1 in 2424/2424 rows" and "log10|y|
# jump of 2.7 dex"; those numerics seed mutator priors with values that
# can coincide with GT (RH-18 kernel-camouflage centers were memorized
# from the cross-class-signal numerics in iter-5). The redactor:
#
#   - replaces "X/Y rows" with "(N rows)" where N is qualitative
#   - replaces bare scientific-notation floats with "<value>"
#   - replaces decimal numbers >0.5 with "<value>" (preserve 0/1 booleans
#     and small fractions because they're rarely identifying)
#   - leaves substantive prose untouched
#
# Numerics stay in workspace/*.json for operator audit; only the
# briefing-rendered text is redacted.

_FLOAT_PATTERN = re.compile(
    r"(?<![A-Za-z_])([+-]?(?:\d+\.\d+|\d+(?:e[+-]?\d+)?|\.\d+)(?:e[+-]?\d+)?)(?![A-Za-z_])",
    re.IGNORECASE,
)
_FRACTION_PATTERN = re.compile(r"\b(\d+)/(\d+)\b")


def _redact_numeric_phrases(text: str) -> str:
    """Replace numeric values in implication text with qualitative
    placeholders. Preserves prose semantics; strips parameter priors.

    SCOPE: Apply ONLY to substrate-critique `implication` strings and
    other ground-truth-adjacent prose surfaced into the mutator
    briefing. Do NOT apply to debate logs, model IDs, configuration
    metadata, or any text where numerics carry non-prior meaning —
    the regex over-matches on substrings like "gpt-4.1" -> "gpt-<value>"
    and would corrupt those if scoped wrongly."""
    if not text:
        return ""
    # Bucket "X/Y rows" fractions
    def _row_repl(m: re.Match) -> str:
        try:
            num = int(m.group(1)); den = int(m.group(2))
        except (ValueError, TypeError):
            return m.group(0)
        if den <= 0:
            return "(rows)"
        frac = num / den
        if frac >= 0.95:
            return "(nearly all rows)"
        if frac >= 0.5:
            return "(majority of rows)"
        if frac >= 0.1:
            return "(minority of rows)"
        return "(few rows)"
    text = _FRACTION_PATTERN.sub(_row_repl, text)

    # Replace bare floats with placeholder
    def _float_repl(m: re.Match) -> str:
        s = m.group(1)
        try:
            v = float(s)
        except (ValueError, TypeError):
            return s
        # Preserve booleans / counts that aren't substantive priors
        if v in (0, 1):
            return s
        if abs(v) < 1e-6:
            return "<small_value>"
        if abs(v) > 1e6:
            return "<large_value>"
        return "<value>"
    text = _FLOAT_PATTERN.sub(_float_repl, text)
    return text


class DataDiagnosticsBriefingProvider(BriefingProvider):
    """Unified noise-profile + substrate-critique view."""

    name = "data_diagnostics"
    priority = 220  # earlier than per_class_breakdown (280); same slot
                    # as the legacy noise_profile provider it replaces.

    def applies(self, ctx: BriefingContext) -> bool:
        if ctx.workspace_dir is None:
            return False
        return (
            (ctx.workspace_dir / "noise_profile.json").exists()
            or (ctx.workspace_dir / "substrate_critique.json").exists()
        )

    def fragment(self, ctx: BriefingContext) -> str:
        ws = ctx.workspace_dir
        np_data = self._read_json(ws / "noise_profile.json")
        sc_data = self._read_json(ws / "substrate_critique.json")
        sg_data = self._read_json(ws / "substrate_critique_suggestions.json")

        if not np_data and not sc_data:
            return ""

        lines: list[str] = []
        lines.append("## Data Diagnostics (GP-166 + GP-167)")
        lines.append("")
        lines.append(
            "The apparatus has measured what the data shows, doesn't "
            "show, and cannot constrain — before any form is fitted, "
            "and again after each iter's fit. Three sub-views below; "
            "each describes a different aspect of the substrate's "
            "epistemic state. Treat the structural facts as binding "
            "when proposing forms; treat the operator-action items as "
            "proposals to the operator, not to the mutator."
        )
        lines.append("")

        if np_data:
            lines.extend(self._render_noise_profile(np_data))
        if sc_data:
            lines.extend(self._render_substrate_structure(sc_data))
        if sg_data:
            lines.extend(self._render_suggestions(sg_data))

        return "\n".join(lines)

    @staticmethod
    def _read_json(path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        except Exception:
            return {}

    @staticmethod
    def _render_noise_profile(d: dict) -> list[str]:
        lines: list[str] = []
        lines.append("### Noise profile")
        lines.append("")
        if d.get("summary"):
            lines.append(f"  **{d['summary']}**")
            lines.append(
                f"  - n tested: {d.get('n_rows_tested', '?')}, "
                f"baseline form: {d.get('baseline_form', '?')}"
            )
            lines.append("")

        ev = d.get("evidence") or {}
        het = ev.get("heteroscedasticity") or {}
        norm = ev.get("normality") or {}
        ac = ev.get("autocorrelation") or {}
        eix = ev.get("errors_in_x") or {}
        if any([het, norm, ac, eix]):
            lines.append("  Test-by-test:")
            if het:
                v = "FIRED" if het.get("verdict") else "ok"
                lines.append(
                    f"    - heteroscedasticity ({het.get('test', '?')}): {v} "
                    f"(r={het.get('r', 0):.3f}, p={het.get('p', 1):.3g})"
                )
            if norm:
                v = "FIRED" if norm.get("verdict") else "ok"
                lines.append(
                    f"    - normality ({norm.get('test', '?')}): {v} "
                    f"(p={norm.get('p', 1):.3g}, skew={norm.get('skew', 0):.2f}, "
                    f"kurt={norm.get('kurtosis_pearson', 3):.2f})"
                )
            if ac:
                v = "FIRED" if ac.get("verdict") else "ok"
                lines.append(
                    f"    - autocorrelation ({ac.get('test', '?')}): {v} "
                    f"(DW={ac.get('dw', 2):.3f})"
                )
            if eix:
                v = "FIRED" if eix.get("verdict") else "ok"
                keys = eix.get("sigma_x_keys_found") or []
                lines.append(
                    f"    - errors-in-X ({eix.get('test', '?')}): {v}"
                    + (f" (keys={keys})" if keys else "")
                )
            lines.append("")

        applied = d.get("auto_route_updates_applied") or []
        if applied:
            lines.append(f"  Solver auto-routing applied: {applied}")
            lines.append("")

        if d.get("needs_robust"):
            lines.append(
                "  **Heavy-tail / non-Gaussian signal detected.** Standard χ² "
                "fits over-weight outlier residuals on this substrate. If your "
                "form fits the bulk well but aggregate MRE is dominated by a "
                "few rows, that is the heavy-tail signal — consider whether "
                "the cause is class-dependent physics or σ underestimation."
            )
            lines.append("")
        if d.get("needs_correlated"):
            lines.append(
                "  **Residual autocorrelation detected.** The errors are not "
                "independent — usually a sign of missing model structure (a "
                "feature or transform that captures the autocorrelated trend)."
            )
            lines.append("")

        return lines

    @staticmethod
    def _render_substrate_structure(d: dict) -> list[str]:
        lines: list[str] = []
        lines.append("### Substrate structure")
        lines.append("")
        if d.get("summary"):
            lines.append(f"  **Verdict:** {d['summary']}")
            lines.append("")

        cc = d.get("cross_class_signal") or []
        if cc:
            # Numeric-redaction panel blind spot from gp163d
            # iter-5 RH-18 hack). Previously we emitted the literal
            # withheld-class numeric values ("withheld ['14.5', '31.09']");
            # the mutator memorized those into kernel centers. Now we
            # emit only qualitative descriptors. Numeric values stay in
            # workspace/substrate_critique.json for operator audit.
            lines.append("  Cross-class extrapolation power per feature:")
            for item in cc:
                power = item.get("extrapolation_power", "unknown")
                overlap_frac = item.get("overlap_fraction_of_withheld", 0)
                if overlap_frac >= 0.5:
                    overlap_label = "high overlap"
                elif overlap_frac >= 0.1:
                    overlap_label = "partial overlap"
                else:
                    overlap_label = "no overlap"
                lines.append(
                    f"    - `{item.get('feature_key', '?')}`: "
                    f"extrapolation={power} ({overlap_label} between visible and "
                    f"withheld ranges; specific values held by gate harness)"
                )
            lines.append(
                "    Forms depending on `extrapolation=none` features cannot be "
                "constrained by visible-class fitting. Use only features whose "
                "values genuinely vary within visible — do NOT pin kernel "
                "centers/widths/amplitudes to withheld-class numeric values "
                "(R20 G-WITHHELD-VALUE-LEAKAGE will flag that)."
            )
            lines.append("")

        cols = d.get("feature_dimensionality_collapses") or []
        if cols:
            # Bucket the relative_range qualitatively
            # so we don't leak the exact within-class span the mutator could
            # memorize as a parameter init value.
            lines.append("  Feature dimensionality collapses (visible class):")
            for c in cols:
                rr = c.get("relative_range", 0) or 0
                if rr < 1e-3:
                    bucket = "essentially constant (< 0.1%)"
                elif rr < 1e-2:
                    bucket = "very narrow (< 1%)"
                elif rr < 1e-1:
                    bucket = "narrow (< 10%)"
                else:
                    bucket = "moderate"
                lines.append(
                    f"    - `{c.get('feature_key')}` in class "
                    f"{c.get('class')!r}: within-class span = {bucket}"
                )
            lines.append(
                "    These features have near-zero within-class variance. "
                "Any free parameter coefficient on them will be unconstrainable."
            )
            lines.append("")

        art = d.get("data_artifacts_suspected") or []
        if art:
            # Strip per-row counts and exact ratios from the
            # implication text to avoid leaking n_rows/min_ratio/max_ratio
            # numerics that could anchor mutator priors. Replace with
            # qualitative descriptors. Numerics stay in workspace JSON
            # for operator audit.
            lines.append("  Suspected data artifacts:")
            for a in art:
                impl = a.get("implication", "") or ""
                impl_redacted = _redact_numeric_phrases(impl)
                lines.append(
                    f"    - {a.get('kind')} in class {a.get('class')!r}: "
                    f"{impl_redacted}"
                )
            lines.append("")

        rb = d.get("regime_breaks_in_data") or []
        if rb:
            # Never emit the exact split_at_x or jump magnitude
            # — those frequently coincide with the GT crossover constant
            # (g_dagger ≈ 1.2e-10 for RAR; transition mass for power laws).
            # Replace with bucketed descriptors.
            lines.append("  Regime breaks in raw data:")
            for r in rb:
                jump = r.get("log10_y_jump") or 0
                try:
                    jump_f = float(jump)
                except (TypeError, ValueError):
                    jump_f = 0.0
                if jump_f >= 2.0:
                    jump_bucket = "≥2 dex (large)"
                elif jump_f >= 1.0:
                    jump_bucket = "1-2 dex (moderate)"
                elif jump_f >= 0.3:
                    jump_bucket = "<1 dex (small)"
                else:
                    jump_bucket = "marginal"
                impl = _redact_numeric_phrases(r.get("implication", "") or "")
                lines.append(
                    f"    - regime break detected along `{r.get('primary_feature')}` "
                    f"(exact split point held by gate harness; jump magnitude: "
                    f"{jump_bucket}). {impl}"
                )
            lines.append("")

        voids = d.get("epistemic_voids") or []
        if voids:
            lines.append("  Epistemic voids (what the substrate cannot decide):")
            preflight = [v for v in voids if not str(v.get("stage", "")).startswith("post_fit")]
            postfit = [v for v in voids if str(v.get("stage", "")).startswith("post_fit")]
            for v in preflight[:4]:
                lines.append(f"    - **{v.get('unknown', '')}**")
                if v.get("why_it_matters"):
                    lines.append(f"      why it matters: {v['why_it_matters']}")
                if v.get("blocking"):
                    lines.append(f"      blocking: {v['blocking']}")
            if postfit:
                lines.append("")
                lines.append("    Post-fit residual analysis (current iter):")
                for v in postfit[:3]:
                    lines.append(f"    - **{v.get('unknown', '')}**")
                    if v.get("why_it_matters"):
                        lines.append(f"      why it matters: {v['why_it_matters']}")
                    if v.get("blocking"):
                        lines.append(f"      blocking: {v['blocking']}")
            if len(voids) > 7:
                lines.append(f"    ... and {len(voids) - 7} more")
            lines.append("")
            lines.append(
                "    Voids are limits of what visible data can tell you. "
                "The honest move on a substrate with unresolved voids is "
                "either to commit to a publishable null *with* the void as "
                "the caveat, or to ask the operator for substrate "
                "enrichment before proposing forms the data cannot constrain."
            )
            lines.append("")

        return lines

    @staticmethod
    def _render_suggestions(d: dict) -> list[str]:
        lines: list[str] = []
        action_needed = [
            s for s in (d.get("suggestions") or [])
            if s.get("operator_action_needed")
        ]
        if not action_needed:
            return lines
        lines.append("### Operator-action-needed (substrate edits proposed, NOT auto-applied)")
        lines.append("")
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
            "  These are proposals to the operator, not to the mutator. "
            "The apparatus does not auto-edit features.py or the rubric. "
            "As the mutator: do not assume any of these will be applied "
            "this iter. Propose forms that work given the substrate AS IT "
            "IS NOW."
        )
        lines.append("")
        return lines
