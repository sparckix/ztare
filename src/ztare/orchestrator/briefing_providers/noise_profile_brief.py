"""GP-166 Noise Profile Briefing — surfaces the pre-flight diagnostic
verdict to the mutator each iter.

Reads `workspace/noise_profile.json` (written by the pre-flight hook
in autoresearch_loop on iter 0 when rubric.enable_noise_profile=True).
Surfaces the four flag verdicts (weighted / robust / correlated /
odr) plus the test statistics that produced them, so the mutator
sees WHY the solver was auto-routed.

This is the "physicist looks at error bars first" pattern made
visible to the LLM: the apparatus measured the noise, made a
verdict, told the mutator. The mutator can then choose forms
appropriate to the noise profile (e.g., heavy-tail signal → don't
fit Gaussian-likelihood-style residuals).
"""
from __future__ import annotations

import json
from typing import Any

from ztare.orchestrator.mutator_briefing import BriefingContext, BriefingProvider


class NoiseProfileBriefingProvider(BriefingProvider):
    """Surfaces GP-166 pre-flight noise-profile verdict to the mutator."""

    name = "noise_profile"
    priority = 220  # right after fit_telemetry (200)

    def applies(self, ctx: BriefingContext) -> bool:
        if ctx.workspace_dir is None:
            return False
        return (ctx.workspace_dir / "noise_profile.json").exists()

    def fragment(self, ctx: BriefingContext) -> str:
        path = ctx.workspace_dir / "noise_profile.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return ""

        lines: list[str] = []
        lines.append("## Noise-Profile Diagnostic (GP-166 pre-flight)")
        lines.append("")
        lines.append(
            f"The apparatus ran 4 statistical tests on baseline-fit "
            f"residuals before iter 1. Verdict:"
        )
        lines.append("")
        lines.append(f"  **{data.get('summary', '(no summary)')}**")
        lines.append(f"  - n tested: {data.get('n_rows_tested', '?')}")
        lines.append(f"  - baseline form: {data.get('baseline_form', '?')}")
        lines.append("")

        # Surface each test's evidence
        ev = data.get("evidence") or {}
        het = ev.get("heteroscedasticity") or {}
        norm = ev.get("normality") or {}
        ac = ev.get("autocorrelation") or {}
        eix = ev.get("errors_in_x") or {}

        lines.append("**Test-by-test:**")
        if het:
            verdict = "FIRED" if het.get("verdict") else "ok"
            lines.append(
                f"  - Heteroscedasticity ({het.get('test', '?')}): {verdict} "
                f"(r={het.get('r', 0):.3f}, p={het.get('p', 1):.3g})"
            )
        if norm:
            verdict = "FIRED" if norm.get("verdict") else "ok"
            lines.append(
                f"  - Normality ({norm.get('test', '?')}): {verdict} "
                f"(p={norm.get('p', 1):.3g}, skew={norm.get('skew', 0):.2f}, "
                f"kurt={norm.get('kurtosis_pearson', 3):.2f})"
            )
        if ac:
            verdict = "FIRED" if ac.get("verdict") else "ok"
            lines.append(
                f"  - Autocorrelation ({ac.get('test', '?')}): {verdict} "
                f"(DW={ac.get('dw', 2):.3f})"
            )
        if eix:
            verdict = "FIRED" if eix.get("verdict") else "ok"
            keys = eix.get("sigma_x_keys_found") or []
            lines.append(
                f"  - Errors-in-X ({eix.get('test', '?')}): {verdict}"
                + (f" (keys={keys})" if keys else "")
            )
        lines.append("")

        # Auto-route summary
        applied = data.get("auto_route_updates_applied") or []
        if applied:
            lines.append(f"**Solver auto-routing applied:** {applied}")
            lines.append("")

        # Tactical guidance
        if data.get("needs_robust"):
            lines.append(
                "  **Heavy-tail / non-Gaussian signal detected.** Standard χ² fits "
                "(weighted or unweighted) over-weight outlier residuals on this "
                "substrate. If your form fits the bulk well but the aggregate MRE "
                "is dominated by a few rows, that is the heavy-tail signal — "
                "consider whether the structural cause is genuine class-dependent "
                "physics (different fundamental scaling for different system types) "
                "or measurement artifact (σ underestimated). Robust loss is not "
                "yet wired in the solver, but the diagnostic is calling out the "
                "regime."
            )
            lines.append("")
        if data.get("needs_correlated"):
            lines.append(
                "  **Residual autocorrelation detected.** The errors are not "
                "independent — this often signals missing model structure (a "
                "feature or transform that captures the autocorrelated trend). "
                "The current form is likely under-specified."
            )
            lines.append("")

        return "\n".join(lines)
