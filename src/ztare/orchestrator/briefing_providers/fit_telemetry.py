"""FitTelemetryProvider — surface fit-primitive telemetry to mutator.

What was previously the inline `_prior_fit_diag_block` in
autoresearch_loop. Reads `workspace/fit_features_result.json` and
emits classification + fitted_params + BIC + pathology_reason +
sparse-cats + per-category residual diagnostic.

All these fields are deterministic outputs of the fit primitive; the
mutator was previously blind to them despite them being printed to
stdout and written to JSON.
"""
from __future__ import annotations

import json

from src.ztare.orchestrator.mutator_briefing import (
    BriefingContext,
    BriefingProvider,
)


class FitTelemetryProvider(BriefingProvider):
    name = "fit_telemetry"
    priority = 200  # critical — this is the fit-side ground truth

    def _load(self, ctx: BriefingContext) -> dict:
        path = (ctx.workspace_dir or ctx.project_dir / "workspace") / "fit_features_result.json"
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def applies(self, ctx: BriefingContext) -> bool:
        return bool(self._load(ctx))

    def fragment(self, ctx: BriefingContext) -> str:
        d = self._load(ctx)
        if not d:
            return ""
        if d.get("success"):
            lines = [
                "\n    ### PRIOR FIT TELEMETRY (from last iter — read before refining)\n",
            ]
            conv = d.get("classification", "")
            if conv:
                lines.append(f"    convergence_classification: {conv}")
            fp = d.get("fitted_params") or {}
            if fp:
                summary = ", ".join(
                    f"{k}={v:.5g}" if isinstance(v, (int, float)) else f"{k}={v}"
                    for k, v in fp.items()
                )
                lines.append(f"    fitted_params: {{{summary}}}")
            bic = d.get("bic")
            k = d.get("k_params")
            n = d.get("n_fit_rows")
            if bic is not None and isinstance(bic, (int, float)) and bic == bic:
                lines.append(
                    f"    BIC: {bic:.2f} (K={k}, N={n}) — lower = better-justified K"
                )
            if d.get("pathological") and d.get("pathology_reason"):
                lines.append(
                    "\n    ⚠️ PATHOLOGICAL FIT FLAG (apparatus diagnostic):\n    "
                    + str(d["pathology_reason"]).replace("\n", "\n    ")
                )
                # GP-166 Fix C: surface that pathology enforcement replaced
                # the catastrophic params with init-range midpoints, so the
                # mutator knows the gate harness saw bounded values, not the
                # blow-up. The MODEL_PARAMS in the saved test_model.py is
                # the SUBSTITUTED set, NOT the catastrophic fitted set.
                if d.get("pathology_substitute_blocked"):
                    fitted = d.get("fitted_params") or {}
                    substituted = d.get("substituted_params") or {}
                    extreme = d.get("extreme_params") or {}
                    diffs = []
                    for k in extreme.keys():
                        if k in fitted and k in substituted:
                            diffs.append(
                                f"{k}: fitted={fitted[k]:.3g} → substituted={substituted[k]:.3g}"
                            )
                    lines.append(
                        "    🛑 APPARATUS REJECTED catastrophic fit — substituted "
                        "init-range midpoints into MODEL_PARAMS so the gate harness "
                        "received bounded values. The fitted form's k-params went "
                        "outside the declared INIT_RANGE because they are "
                        "underdetermined by visible-class data. RESTRUCTURE the "
                        "form so each free parameter is bounded by visible-class "
                        "rows alone — adding more parameters that only the "
                        "withheld classes could constrain will not help."
                    )
                    if diffs:
                        lines.append("    Substitutions applied: " + "; ".join(diffs))
            fvc = d.get("feature_value_counts") or {}
            sparse = []
            for fk, vc in fvc.items():
                for v, c in (vc or {}).items():
                    if c < 3:
                        sparse.append(f"{fk}='{v}' (n={c})")
            if sparse:
                lines.append(
                    "    ⚠️ SPARSE CATEGORIES (<3 rows): "
                    + ", ".join(sparse[:6])
                    + (" …" if len(sparse) > 6 else "")
                )
            if d.get("residual_diagnostic"):
                lines.append(
                    "\n    Per-categorical-group residual diagnostic (groups whose "
                    "mean residual exceeds 1.5× the overall mean):\n\n    "
                    + str(d["residual_diagnostic"]).replace("\n", "\n    ")
                )
            return "\n".join(lines) + "\n"
        elif d.get("error_message"):
            err_full = str(d["error_message"])
            err_text = err_full if len(err_full) <= 1500 else err_full[:1500] + "...[truncated]"
            return (
                "\n    ### PRIOR FIT FAILURE (from last iter — READ BEFORE WRITING)\n\n"
                f"    Your previous iter's fit FAILED. Apparatus diagnostic:\n\n"
                f"    {err_text.replace(chr(10), chr(10) + '    ')}\n\n"
                "    Fix the form grammar (PARAMETRIC_FORM must be a single Python "
                "expression with `features[...]` and `params[...]` subscripts). "
                "If the diagnostic mentions specific anti-patterns (Greek letters, "
                "statement blocks, bare identifiers, pseudocode), translate every "
                "one of them to valid Python BEFORE submitting.\n"
            )
        return ""
