"""FramerRecommendationProvider — surface the framer's verdict to mutator.

When `enable_framer=true` and the framer wrote a `framing_report.json`
to the workspace (either via the 1D path or the N-D adapter), this
provider injects the recommended (h_in, h_out) into the mutator's
next-iter briefing. The mutator may choose to apply the transform
inside its PARAMETRIC_FORM. The holdout gate validates the result.

This is the "active mode" mechanism for N-D substrates: the framer
proposes deterministically; the mutator integrates structurally; the
gate verifies empirically. No data-flow modification at the apparatus
level — same separation-of-concerns as the 1D framer's observe-mode.
"""
from __future__ import annotations

import json

from ztare.orchestrator.briefing_providers import section_unavailable
from ztare.orchestrator.mutator_briefing import (
    BriefingContext,
    BriefingProvider,
)


class FramerRecommendationProvider(BriefingProvider):
    name = "framer_recommendation"
    priority = 320  # after fit telemetry + gate gap; before iter trajectory

    def _report_path(self, ctx: BriefingContext):
        return (ctx.workspace_dir or ctx.project_dir / "workspace") / "framing_report.json"

    def _load_report(self, ctx: BriefingContext, *, strict: bool = False) -> dict:
        path = self._report_path(ctx)
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except SystemExit:
            raise
        except Exception:
            if strict:
                raise
            return {}

    def applies(self, ctx: BriefingContext) -> bool:
        if not bool(ctx.rubric.get("enable_framer", False)):
            return False
        path = self._report_path(ctx)
        if not path.exists():
            return False
        try:
            report = self._load_report(ctx, strict=True)
        except SystemExit:
            raise
        except Exception:
            # Corrupt (not absent) report: apply so fragment() banners.
            return True
        return bool(report.get("framer_engaged"))

    def fragment(self, ctx: BriefingContext) -> str:
        try:
            report = self._load_report(ctx, strict=True)
        except SystemExit:
            raise
        except Exception as exc:
            return section_unavailable("GP-152 FRAMER RECOMMENDATION", exc)
        h_in = report.get("h_in") or "identity"
        h_out = report.get("h_out") or "identity"
        mdl_gain = report.get("MDL_gain_bits", 0.0)
        mdl_gain_balanced = report.get("MDL_gain_bits_balanced", None)
        primary = report.get("primary_feature_key")
        shape = report.get("shape", "1d")

        try:
            mdl_gain_f = float(mdl_gain)
        except (TypeError, ValueError) as exc:
            # A malformed MDL number must NOT be coerced to 0.0 — that would
            # silently downgrade a possibly-DECISIVE verdict to "suggestive".
            # Surface the malformation; the mutator keeps its prior guidance.
            return section_unavailable(
                "GP-152 FRAMER RECOMMENDATION",
                type(exc)(f"malformed MDL_gain_bits {mdl_gain!r}"),
            )

        # Frame Adjudicator v2 threshold: bits at which framer signal is
        # treated as "decisive" (Kass-Raftery decisive ≈ 7 bits; we use
        # 20 as ~3× decisive). Below threshold, observe-only recommendation
        # (legacy mode). Above threshold AND class-balanced MDL also clears,
        # switch to mechanism-generative prompt.
        threshold_bits = float(
            ctx.rubric.get("frame_adjudicator_threshold_bits", 20.0)
        )
        balanced_clear = True
        if mdl_gain_balanced is not None:
            try:
                balanced_clear = float(mdl_gain_balanced) >= max(
                    10.0, threshold_bits * 0.5
                )
            except (TypeError, ValueError) as exc:
                # Do NOT coerce a malformed balanced-MDL to "confirmed" — that
                # would over-confirm a decisive switch. Banner the malformation.
                return section_unavailable(
                    "GP-152 FRAMER RECOMMENDATION",
                    type(exc)(
                        f"malformed MDL_gain_bits_balanced {mdl_gain_balanced!r}"
                    ),
                )
        decisive = mdl_gain_f >= threshold_bits and balanced_clear

        lines = [
            "\n    ### GP-152 FRAMER RECOMMENDATION (deterministic coordinate-transform search)\n",
        ]
        if shape == "n_d" and primary:
            lines.append(
                f"    The framer projected your N-D substrate onto its primary axis "
                f"`features['{primary}']` and searched a fixed library of unary coordinate "
                f"transforms (log/sqrt/inverse/identity/etc.). Verdict:\n"
            )
        else:
            lines.append(
                "    The framer searched a fixed library of unary coordinate transforms\n"
                "    (log/sqrt/inverse/identity/etc.) on (x, y). Verdict:\n"
            )
        lines.append(f"      - h_in (transform on independent variable): {h_in}")
        lines.append(f"      - h_out (transform on observable):         {h_out}")
        lines.append(f"      - MDL gain vs raw frame: {mdl_gain_f:.2f} bits")
        if mdl_gain_balanced is not None:
            try:
                lines.append(
                    f"      - MDL gain (class-balanced recompute): "
                    f"{float(mdl_gain_balanced):.2f} bits"
                )
            except (TypeError, ValueError):
                pass

        if decisive:
            primary_str = (
                f"`features['{primary}']`"
                if (shape == "n_d" and primary)
                else "the independent variable"
            )
            lines.append(
                f"\n    🚨 MDL gain {mdl_gain_f:.1f} bits is DECISIVE evidence (Kass-Raftery "
                f"decisive ≈ 7 bits; threshold here is {threshold_bits:.0f}). The data is "
                f"telling you that {primary_str} is structurally important and that the "
                f"transform `{h_in}` compresses the relationship. Class-balanced MDL recompute "
                f"{'CONFIRMED' if balanced_clear else 'DID NOT CONFIRM'} — the signal is "
                f"{'substrate-wide, not row-imbalance artifact' if balanced_clear else 'likely a row-imbalance artifact (one class dominates).'}."
            )
            if balanced_clear:
                lines.append(
                    f"\n    PROMPT TO YOU (this is not a substitution rule — it is a question):"
                )
                lines.append(
                    f"      The framer found that `{h_in}({primary_str})` compresses the data "
                    f"by {mdl_gain_f:.1f} bits over raw coordinates. **What physical mechanism "
                    f"would produce this preference?** Propose 2-3 candidate mechanisms — "
                    f"symmetries, conservation laws, scaling regimes, screening fields, or "
                    f"geometric structures — that would naturally generate `{h_in}` shape "
                    f"in {primary_str}. List each as a short hypothesis (one sentence each), "
                    f"then encode the strongest as PARAMETRIC_FORM."
                )
                lines.append(
                    f"\n    CRITICAL CONSTRAINT — anchor preservation:"
                )
                lines.append(
                    f"      Do NOT apply the transform as a free additive corrector. Sim has "
                    f"shown naïve corrector forms break Solar-System / asymptotic anchors by "
                    f"~0.5 dex (the optimizer cheats any soft screen). Your form must encode "
                    f"the mechanism in a way that vanishes in regimes where the anchors live. "
                    f"If you cannot propose such a mechanism, return to the previous form — "
                    f"the framer signal is not yet usable."
                )
            else:
                lines.append(
                    f"\n    Because class-balanced MDL did NOT confirm, treat the {h_in} "
                    f"signal as a coverage artifact and prefer forms that respect the "
                    f"non-dominant classes (anchors). Do not adopt the transform until the "
                    f"balanced signal exceeds 10 bits."
                )
        else:
            # Below threshold OR balanced-not-confirmed → legacy observe-only
            if shape == "n_d" and primary:
                lines.append(
                    f"\n    USAGE: consider applying h_in to `features['{primary}']` and "
                    f"\n    h_out to your predicted y *inside* PARAMETRIC_FORM. Below the "
                    f"\n    decisive threshold ({threshold_bits:.0f} bits), this is suggestive, "
                    f"\n    not directive — only adopt if you can argue a physical reason."
                )
            else:
                lines.append(
                    "\n    USAGE: consider applying h_in / h_out inside your PARAMETRIC_FORM "
                    "to fit the framed data instead of raw data. Suggestive, not directive."
                )

        lines.append(
            "\n    The framer is OBSERVE-only at the apparatus layer — it does NOT modify\n"
            "    the data flowing into the fit primitive. The holdout gate + R11 per-class\n"
            "    MRE + anchor checks adjudicate the result."
        )
        return "\n".join(lines) + "\n"
