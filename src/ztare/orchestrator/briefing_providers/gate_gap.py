"""GateGapProvider — substrate-agnostic near-miss diagnostic.

When prior-iter gates ran but score=0 due to threshold breach, surface
the actual numerical gap per gate. Identifies the dominant gap (which
gate is most over-threshold) and a generic structural-vs-extrapolation
hint based on whether the dominant gap is in-regime (HOLDOUT) or
extrapolation (FARTHER_TAIL).

Substrate-agnostic. No hypothesis-specific advice. The mutator infers
the structural move from the numbers.
"""
from __future__ import annotations

import json

from ztare.orchestrator.briefing_providers import section_unavailable
from ztare.orchestrator.mutator_briefing import (
    BriefingContext,
    BriefingProvider,
)


class GateGapProvider(BriefingProvider):
    name = "gate_gap"
    priority = 250

    def _path(self, ctx: BriefingContext):
        return ctx.project_dir / "latest_eval_results.json"

    def _load(self, ctx: BriefingContext) -> dict:
        # Swallows only the ABSENT case → {} (legit "not applicable").
        # Corrupt/unreadable files propagate so fragment() can banner.
        path = self._path(ctx)
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _extract_gates(self, prior_eval: dict) -> list[dict]:
        gates: list[dict] = []
        payload = prior_eval.get("holdout_payload") or {}
        for gname in ("holdout", "farther_tail"):
            g = payload.get(gname) if isinstance(payload, dict) else None
            if isinstance(g, dict) and g.get("mean_relative_error") is not None and g.get("threshold") is not None:
                mre = float(g["mean_relative_error"])
                thr = float(g["threshold"])
                gap_pct = (mre - thr) / max(thr, 1e-12) * 100.0
                gates.append({
                    "name": gname.upper(),
                    "mre": mre,
                    "threshold": thr,
                    "gap_pct": gap_pct,
                    "passed": bool(g.get("passed")),
                })
        if not gates:
            for g in (prior_eval.get("gate_results") or []):
                if isinstance(g, dict) and g.get("value") is not None and g.get("threshold") is not None:
                    mre = float(g["value"])
                    thr = float(g["threshold"])
                    gap_pct = (mre - thr) / max(thr, 1e-12) * 100.0
                    gates.append({
                        "name": g.get("name", "?"),
                        "mre": mre,
                        "threshold": thr,
                        "gap_pct": gap_pct,
                        "passed": bool(g.get("passed", g.get("pass", False))),
                    })
        return gates

    def applies(self, ctx: BriefingContext) -> bool:
        # Present-but-corrupt still applies so fragment() renders a banner
        # rather than the section vanishing before fragment() is reached.
        if self._path(ctx).exists():
            return True
        prior = self._load(ctx)
        if not prior:
            return False
        gates = self._extract_gates(prior)
        return any(not g["passed"] for g in gates)

    def fragment(self, ctx: BriefingContext) -> str:
        try:
            prior = self._load(ctx)
        except Exception as exc:
            return section_unavailable("GATE GAP", exc)
        gates = self._extract_gates(prior)
        sorted_gates = sorted(gates, key=lambda g: g["gap_pct"], reverse=True)
        failed = [g for g in sorted_gates if not g["passed"]]
        if not failed:
            return ""

        lines = ["\n    ### NEAR-MISS GATE DIAGNOSTIC (numerical-gap feedback, prior iter)\n"]
        lines.append("    Prior iter's gates produced these per-gate gaps. Use the")
        lines.append("    DOMINANT GAP (largest over-threshold) to choose your next")
        lines.append("    structural move. Score=0 reflects hard-gate semantics; the")
        lines.append("    numerical gradient below shows how close each gate was.\n")
        for g in sorted_gates:
            tag = ("PASS" if g["passed"]
                   else ("near-miss" if 0 < g["gap_pct"] <= 25
                         else "hard-fail"))
            lines.append(
                f"    - {g['name']}: MRE={g['mre']:.4g} vs threshold "
                f"{g['threshold']:.4g}  (gap {g['gap_pct']:+.1f}%, {tag})"
            )
        dominant = failed[0]
        lines.append(
            f"\n    DOMINANT GAP: {dominant['name']} (gap {dominant['gap_pct']:+.1f}%)."
        )
        dom_name = dominant["name"].upper()
        if "HOLDOUT" in dom_name and "FARTHER" not in dom_name:
            lines.append(
                "    The form is failing IN-REGIME (held-out class-A or "
                "primary holdout). The structural family or fitted constants "
                "are wrong. Reconsider the form's functional class before "
                "tuning further; another iteration of the same form will "
                "likely converge to the same local minimum."
            )
        elif "FARTHER" in dom_name or "TAIL" in dom_name:
            lines.append(
                "    The form fits IN-REGIME but FAILS EXTRAPOLATION. "
                "The form's structural capacity does not extend to the "
                "held-out tail/class. Consider whether the form needs "
                "additional features, class-conditional structure, or a "
                "different functional family that respects the asymptotic "
                "behavior the charter declares."
            )
        else:
            lines.append(
                f"    Largest deficit at {dom_name}. Use the gap "
                f"sign and magnitude to direct your next structural change."
            )
        return "\n".join(lines) + "\n"
