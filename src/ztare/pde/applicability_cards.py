"""Deterministic PDE applicability-card retrieval for leaf agents.

This is not a lemma bank and it does not duplicate LeanMill's premise shelf or
family lemma library. It ranks project/app theorem profiles by PDE obligation
language and runs field-level applicability/confuser checks. Citable Lean
premises remain LeanMill's responsibility.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from ztare.research_director.theorem_applicability_db import (
    match_theorem_applicability,
)


@dataclass(frozen=True)
class PDEApplicabilityCard:
    schema: str
    theorem_id: str
    source_profile: str
    relevance_score: float
    matched_terms: list[str]
    requires: list[str]
    concludes: dict[str, Any]
    rejected_substitutes: list[str]
    applicability: dict[str, Any]


def _tokens(text: str) -> set[str]:
    return {
        token for token in re.findall(r"[A-Za-z0-9]+", text.lower().replace("_", " "))
        if len(token) >= 3
    }


def _profile_text(theorem_id: str, profile: dict[str, Any]) -> str:
    bits: list[str] = [theorem_id]
    requires = profile.get("requires") or {}
    concludes = profile.get("concludes") or {}
    rejects = profile.get("does_not_accept") or []
    if isinstance(requires, dict):
        bits.extend(str(key) for key in requires)
    if isinstance(concludes, dict):
        bits.extend(str(key) for key in concludes)
    if isinstance(rejects, list):
        bits.extend(str(item) for item in rejects)
    return " ".join(bits)


def applicability_card_retrieval(
    theorem_db: dict[str, dict[str, Any]],
    *,
    query: str = "",
    available: dict[str, Any] | None = None,
    source_profile: str = "unknown",
    top_k: int = 8,
) -> list[dict[str, Any]]:
    """Return ranked applicability cards with field-level PDE profile data."""
    query_tokens = _tokens(query)
    cards: list[dict[str, Any]] = []
    for theorem_id, profile in theorem_db.items():
        profile_tokens = _tokens(_profile_text(theorem_id, profile))
        matched = sorted(query_tokens & profile_tokens)
        if query_tokens:
            score = len(matched) / max(1, len(query_tokens))
        else:
            score = 0.0
        applicability = match_theorem_applicability(
            theorem_id,
            available or {},
            theorem_db,
        )
        requires = profile.get("requires") or {}
        concludes = profile.get("concludes") or {}
        rejects = profile.get("does_not_accept") or []
        card = PDEApplicabilityCard(
            schema="pde-applicability-card-v1",
            theorem_id=theorem_id,
            source_profile=source_profile,
            relevance_score=round(score, 6),
            matched_terms=matched,
            requires=list(requires.keys()) if isinstance(requires, dict) else [],
            concludes=concludes if isinstance(concludes, dict) else {},
            rejected_substitutes=[
                str(item) for item in rejects
            ] if isinstance(rejects, list) else [],
            applicability=applicability,
        )
        cards.append(asdict(card))
    cards.sort(
        key=lambda item: (
            float(item.get("relevance_score") or 0.0),
            len(item.get("matched_terms") or []),
            str(item.get("theorem_id") or ""),
        ),
        reverse=True,
    )
    if top_k <= 0:
        return []
    return cards[:top_k]


def render_applicability_cards(cards: list[dict[str, Any]]) -> str:
    """Render compact applicability cards for workbench packs and dispatch prompts."""
    if not cards:
        return "- (no applicability cards)"
    lines: list[str] = []
    for card in cards:
        app = card.get("applicability") if isinstance(card.get("applicability"), dict) else {}
        lines.append(
            f"- `{card.get('theorem_id')}` score={card.get('relevance_score')} "
            f"verdict=`{app.get('verdict')}`"
        )
        missing = app.get("missing_fields") or []
        rejected = app.get("rejected_substitutes") or []
        if missing:
            lines.append(f"  - missing: {missing[:8]}")
        if rejected:
            lines.append(f"  - rejected: {rejected[:8]}")
    return "\n".join(lines)
