"""Generic deterministic theorem-applicability matcher for PDE prompts."""
from __future__ import annotations

from typing import Any


def match_theorem_applicability(
    theorem_id: str,
    available: dict[str, Any],
    theorem_db: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Return MATCH, PARTIAL, or NO_MATCH against explicit theorem fields."""
    theorem = theorem_db.get(theorem_id)
    if theorem is None:
        return {
            "theorem": theorem_id,
            "verdict": "NO_MATCH",
            "reason": "unknown theorem id",
        }
    missing = [
        field for field in theorem["requires"]
        if not available.get(field)
    ]
    rejected = [
        field for field in theorem.get("does_not_accept", [])
        if available.get(field)
    ]
    if rejected:
        verdict = "NO_MATCH"
    elif missing:
        verdict = "PARTIAL"
    else:
        verdict = "MATCH"
    return {
        "theorem": theorem_id,
        "verdict": verdict,
        "requires": theorem["requires"],
        "available": available,
        "missing_fields": missing,
        "rejected_substitutes": rejected,
        "concludes": theorem.get("concludes", {}),
    }
