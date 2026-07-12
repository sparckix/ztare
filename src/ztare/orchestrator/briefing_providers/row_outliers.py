"""RowOutlierProvider — top-K worst-fitted rows from prior fit.

Mutator currently sees only aggregate residual statistics. Per-row
outliers give the mutator concrete (x, y_observed, y_predicted)
evidence of WHERE the form fails. Substrate-agnostic.

Risk: too much detail crowds the prompt. Mitigation: top-5 only,
short row summary (~80 chars each).
"""
from __future__ import annotations

import json
from typing import Any

from ztare.orchestrator.briefing_providers import section_unavailable
from ztare.orchestrator.mutator_briefing import (
    BriefingContext,
    BriefingProvider,
)


class RowOutlierProvider(BriefingProvider):
    name = "row_outliers"
    priority = 400
    TOP_K = 5

    def _fit_path(self, ctx: BriefingContext):
        return (ctx.workspace_dir or ctx.project_dir / "workspace") / "fit_features_result.json"

    def _load_fit(self, ctx: BriefingContext) -> dict:
        # Swallows only the ABSENT case → {} (legit "not applicable").
        # Corrupt/unreadable files propagate so fragment() can banner.
        path = self._fit_path(ctx)
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _format_row(self, feats: dict, y_obs: float, y_pred: float) -> str:
        # Compact representation: 2-3 features + obs/pred
        feat_summary = ", ".join(
            f"{k}={v:.3g}" if isinstance(v, (int, float)) else f"{k}={v}"
            for k, v in list(feats.items())[:3]
        )
        rel_err = abs(y_pred - y_obs) / max(abs(y_obs), 1e-300)
        return (
            f"({feat_summary})  obs={y_obs:.4g}  pred={y_pred:.4g}  "
            f"rel_err={rel_err*100:.1f}%"
        )

    def applies(self, ctx: BriefingContext) -> bool:
        # Present-but-corrupt still applies so fragment() renders a banner
        # rather than the section vanishing before fragment() is reached.
        if self._fit_path(ctx).exists():
            return True
        d = self._load_fit(ctx)
        # Only fire when the fit succeeded AND has worst_residuals stored.
        # If the worst-residuals key isn't present, skip rather than
        # recompute (fit primitive is the canonical source).
        return bool(d.get("success")) and bool(d.get("worst_residuals"))

    def fragment(self, ctx: BriefingContext) -> str:
        try:
            d = self._load_fit(ctx)
        except Exception as exc:
            return section_unavailable("ROW OUTLIERS", exc)
        worst = d.get("worst_residuals") or []
        if not worst:
            return ""
        lines = [
            "\n    ### TOP-K WORST-FITTED ROWS (from prior fit)\n",
            "    These rows had the largest absolute residual under your fitted form.",
            "    Use them as concrete evidence of WHERE the structural form fails:\n",
        ]
        for r in worst[: self.TOP_K]:
            feats = r.get("features", {})
            y_obs = r.get("y_observed", float("nan"))
            y_pred = r.get("y_predicted", float("nan"))
            try:
                lines.append("    - " + self._format_row(feats, y_obs, y_pred))
            except Exception:
                continue
        return "\n".join(lines) + "\n"
