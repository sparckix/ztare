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

from src.ztare.orchestrator.mutator_briefing import (
    BriefingContext,
    BriefingProvider,
)


class FramerRecommendationProvider(BriefingProvider):
    name = "framer_recommendation"
    priority = 320  # after fit telemetry + gate gap; before iter trajectory

    def _load_report(self, ctx: BriefingContext) -> dict:
        path = (ctx.workspace_dir or ctx.project_dir / "workspace") / "framing_report.json"
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def applies(self, ctx: BriefingContext) -> bool:
        if not bool(ctx.rubric.get("enable_framer", False)):
            return False
        report = self._load_report(ctx)
        return bool(report.get("framer_engaged"))

    def fragment(self, ctx: BriefingContext) -> str:
        report = self._load_report(ctx)
        h_in = report.get("h_in") or "identity"
        h_out = report.get("h_out") or "identity"
        mdl_gain = report.get("MDL_gain_bits", 0.0)
        primary = report.get("primary_feature_key")
        shape = report.get("shape", "1d")

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
        try:
            lines.append(f"      - MDL gain vs raw frame: {float(mdl_gain):.2f} bits")
        except (TypeError, ValueError):
            lines.append(f"      - MDL gain vs raw frame: {mdl_gain}")
        if shape == "n_d" and primary:
            lines.append(
                f"\n    USAGE: consider applying h_in to `features['{primary}']` and "
                f"\n    h_out to your predicted y *inside* PARAMETRIC_FORM. Example "
                f"\n    skeleton (substitute the actual h_in/h_out shapes named above):\n\n"
                f"      PARAMETRIC_FORM = (\n"
                f"          \"<inverse_h_out>(\"\n"
                f"          \"  params['a'] + params['b'] * <h_in>(features['{primary}'])\"\n"
                f"          \")\"\n"
                f"      )\n"
            )
        else:
            lines.append(
                "\n    USAGE: consider applying h_in / h_out inside your PARAMETRIC_FORM "
                "to fit the framed data instead of raw data."
            )
        lines.append(
            "\n    The framer is OBSERVE-only at the apparatus layer — it does NOT modify\n"
            "    the data flowing into the fit primitive. If you adopt the recommendation,\n"
            "    encode it in PARAMETRIC_FORM yourself. The holdout gate validates the\n"
            "    result. If the framer's frame is structurally correct for your problem,\n"
            "    the form should be simpler under it (smaller K, lower BIC)."
        )
        return "\n".join(lines) + "\n"
