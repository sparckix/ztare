"""Briefing provider for evidence-grounded qualitative cold shot.

Reads `workspace/qualitative_evidence_cold_shot.json` and renders the 3
thesis-family candidates as T2-priority mandatory-consider alternatives.
Activates only when `enable_qualitative_evidence_cold_shot=true` and the
artifact exists with ≥2 candidates.
"""
from __future__ import annotations

import json
from pathlib import Path

from ztare.orchestrator.mutator_briefing import BriefingContext, BriefingProvider

ARTIFACT_NAME = "qualitative_evidence_cold_shot.json"


class QualitativeEvidenceSeedProvider(BriefingProvider):
    name = "qualitative_evidence_seed"
    priority = 160  # just after cold_llm_seed (150); renders before analogy (350)

    def applies(self, ctx: BriefingContext) -> bool:
        if not bool(ctx.rubric.get("enable_qualitative_evidence_cold_shot", False)):
            return False
        ws = ctx.workspace_dir or ctx.project_dir / "workspace"
        artifact = ws / ARTIFACT_NAME
        if not artifact.exists():
            return False
        try:
            data = json.loads(artifact.read_text(encoding="utf-8"))
        except SystemExit:
            raise
        except Exception:
            # Corrupt (not absent) artifact: apply so fragment() renders its
            # UNAVAILABLE banner rather than silently omitting the section.
            return True
        return len(data.get("candidates") or []) >= 2

    def fragment(self, ctx: BriefingContext) -> str:
        ws = ctx.workspace_dir or ctx.project_dir / "workspace"
        try:
            data = json.loads((ws / ARTIFACT_NAME).read_text(encoding="utf-8"))
        except Exception as exc:
            return (
                "## ⚠️  Evidence cold shot (UNAVAILABLE)\n\n"
                f"Load error: `{exc}`. Proceed with standard briefing.\n\n"
            )

        candidates = data.get("candidates") or []
        weakest = data.get("weakest_point_used", "")
        lines: list[str] = []
        lines.append(
            "## 🔎 Evidence Cold Shot — MANDATORY CONSIDER (T2)\n"
        )
        lines.append(
            "A fresh analytical agent (no shared context with mutator or judge) "
            "read the evidence brief, the current champion's weakest point, and the "
            "rubric gate definitions, then proposed the thesis families below. "
            "These are evidence-grounded starting points — structurally distinct from "
            "the cross-domain de-anchor seed and from each other.\n"
        )
        if weakest:
            lines.append(
                f"**Champion weakest point addressed:** {weakest[:300]}\n"
            )
        lines.append("### Thesis family candidates\n")
        for i, cand in enumerate(candidates[:3], 1):
            name = cand.get("name", f"Family {i}")
            claim = cand.get("core_claim", "")
            commitment = cand.get("structural_commitment", "")
            resolves = cand.get("resolves_weakest_point", "")
            avoids = cand.get("failure_modes_avoided", "")
            lines.append(f"#### Family {i}: {name}\n")
            if claim:
                lines.append(f"**Core claim:** {claim}\n")
            if commitment:
                lines.append(f"**Structural commitment:** {commitment}\n")
            if resolves:
                lines.append(f"**Resolves weakest point:** {resolves}\n")
            if avoids:
                lines.append(f"**Gate failures avoided:** {avoids}\n")
        lines.append("### Adherence requirement (T2)\n")
        lines.append(
            "Your thesis MUST either: (a) adopt one of these families as your structural "
            "spine, OR (b) explicitly state which family comes closest and why you are "
            "taking a different approach. Ignoring all three without explanation receives "
            "an R1 strike. From iter 2 onward these families remain as alternatives; "
            "engagement is no longer mandatory.\n"
        )
        return "\n".join(lines) + "\n"
