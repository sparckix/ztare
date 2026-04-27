"""AnalogyCandidatesProvider — surface cross-domain L1 candidates to mutator.

Reads `workspace/analogy_log.jsonl` (written by the GP-164 analogy hook
in autoresearch_loop). For the most recent record on the most recent
iter, surfaces the LLM-proposed candidate forms to the mutator's next-
iter briefing.

Two engagement modes per the gp-164 seam:

  * **OBSERVE mode** (default — `enable_analogy_active` is False or
    absent): candidate forms are rendered with a "consider, not
    apparatus-validated" caveat. The mutator may use them as
    inspiration but should not treat them as confirmed templates.
  * **ACTIVE mode** (`enable_analogy_active=True`): candidate forms
    are rendered as concrete suggestions to integrate. The mutator
    is told the apparatus is opting in to cross-domain transfer this
    iter.

The provider is contamination-defended: it surfaces only the
structural-descriptor + candidate-form text from the LLM response,
never the original substrate's variable names or charter prose.
The fingerprint that produced the analogy is already anonymized
upstream (in analogy.build_residual_fingerprint).
"""
from __future__ import annotations

import json

from src.ztare.orchestrator.mutator_briefing import (
    BriefingContext,
    BriefingProvider,
)


class AnalogyCandidatesProvider(BriefingProvider):
    name = "analogy_candidates"
    priority = 350  # after fit/gate/trajectory; before outliers/asymptote

    def _load_latest_record(self, ctx: BriefingContext) -> dict | None:
        path = (ctx.workspace_dir or ctx.project_dir / "workspace") / "analogy_log.jsonl"
        if not path.exists():
            return None
        latest: dict | None = None
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                latest = rec  # last record wins
        except Exception:
            return None
        return latest

    def applies(self, ctx: BriefingContext) -> bool:
        if not bool(ctx.rubric.get("enable_analogy", False)):
            return False
        rec = self._load_latest_record(ctx)
        if not rec:
            return False
        if rec.get("error"):
            return False
        return bool(rec.get("candidate_forms"))

    def fragment(self, ctx: BriefingContext) -> str:
        rec = self._load_latest_record(ctx) or {}
        candidates = rec.get("candidate_forms") or []
        descriptors = rec.get("structural_descriptors") or []
        reasoning = rec.get("reasoning") or ""
        active = bool(ctx.rubric.get("enable_analogy_active", False))

        header = (
            "\n    ### GP-164 ANALOGY CANDIDATES (cross-domain transfer, prior iter)\n\n"
        )
        if active:
            preamble = (
                "    ACTIVE mode. The apparatus queried a frontier LLM with a\n"
                "    structurally-anonymized fingerprint of the prior fit's residuals\n"
                "    (no variable names, no charter prose, no domain hints). Candidate\n"
                "    forms returned are listed below. Consider integrating them or a\n"
                "    structural variant. The apparatus has NOT yet validated these\n"
                "    against your substrate; the holdout gate will validate.\n\n"
            )
        else:
            preamble = (
                "    OBSERVE mode (logged, not endorsed). The apparatus queried a\n"
                "    frontier LLM with a structurally-anonymized fingerprint of the\n"
                "    prior fit's residuals. Candidate forms are listed below. They\n"
                "    are inspiration only; the apparatus has not validated them and\n"
                "    is not pushing you to use them. Use your own judgment about\n"
                "    whether the structural descriptors match your problem.\n\n"
            )

        body_lines: list[str] = []
        if descriptors:
            body_lines.append("    Structural descriptors (LLM's read of the residual shape):")
            for d in descriptors[:5]:
                body_lines.append(f"      - {d}")
            body_lines.append("")
        if candidates:
            body_lines.append("    Candidate forms (placeholder vars x, y, z; not your substrate's vars):")
            for c in candidates[:5]:
                body_lines.append(f"      - {c}")
            body_lines.append("")
        if reasoning:
            body_lines.append(f"    Reasoning (LLM): {reasoning[:300]}")
        body_lines.append(
            "\n    REMINDER: ANALOGY is structural, not semantic. The candidate forms\n"
            "    above are abstract patterns. Do NOT import their domain-of-origin\n"
            "    axioms. Map placeholder variables to your features carefully and\n"
            "    let the holdout gate decide whether the structural pattern matches."
        )
        return header + preamble + "\n".join(body_lines) + "\n"
