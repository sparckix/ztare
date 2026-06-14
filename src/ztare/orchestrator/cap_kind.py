"""Cap-source classifier — REFRAME vs REFINE decision support.

Background (2026-04-27): the apparatus has 5 overlapping diversity-forcing
mechanisms (forced_reframe, Erdős re-query, structural pivot, axiom purge,
REFRAME alien-math seam) that all fire on the same `score_cap_reason`
signal. This is correct when the cap source is *gaming* (parameter
laundering, kernel camouflage). It is WRONG when the cap source is
generalization gap (farther-tail per-class fail), physics violation
(PPN miss), or numerical failure (L3 assert) — those signal "refine the
prior honest form," not "pivot to a different family."

This module classifies the cap_reason string into a `cap_kind` enum
that the providers use to decide refine vs reframe. The classification
is regex-based and idempotent so it can run repeatedly without
side-effects.

Cap kinds:
  - gaming               R20-R24, RH-18, RH-EFFK-LAUNDER (parameter laundering)
  - physics_violation    Mercury / Cassini PPN strict bound failures
  - generalization_gap   Farther-tail per-class MRE failures (Class B/C)
  - holdout_miss         Class A holdout MRE failure (without farther-tail)
  - numerical_failure    L3 assert, non-finite, harness defect, contract violation
  - none                 No cap applied (judge score preserved)
  - unknown              Cap reason present but doesn't match any pattern

Usage:
  from src.ztare.orchestrator.cap_kind import classify_cap_kind
  kind = classify_cap_kind(eval_record.get("score_cap_reason"))
  if kind == "gaming":
      # fire forced_reframe / Erdős re-query / structural pivot
  elif kind in ("generalization_gap", "physics_violation"):
      # render "refine prior winner" block — DO NOT pivot
"""
from __future__ import annotations

import re
from typing import Optional


# Regex patterns are case-insensitive substring matches.
# Order matters — the FIRST match wins. Place specific patterns first.
_GAMING_PATTERNS = (
    r"R20-WITHHELD",
    r"R21-EFFECTIVE-K",
    r"R22-RH-",
    r"R24-FEATURE-BUMP",
    r"parameter[- ]laundering",
    r"kernel[- ]camouflage",
    r"effective-K mismatch",
    r"constant[- ]laundering",
    r"hidden[- ]parameter",
    r"hidden[- ]universality",
    r"cage_constant_laundering",
)

_PHYSICS_VIOLATION_PATTERNS = (
    r"MERCURY-PRECESSION",
    r"CASSINI-PPN",
    r"G-MERCURY",
    r"G-CASSINI",
    r"PPN gate\(s\) FAILED",
    r"Solar-System PPN",
    r"PPN cap",
)

_GENERALIZATION_GAP_PATTERNS = (
    r"FARTHER_TAIL.*fail",
    r"FARTHER_TAIL:.*<\s*0\.",
    r"per-class farther-tail",
    r"enforce_per_class_farther_tail",
    r"farther.tail.*fail",
    r"R11.*per-class.*MRE",
    r"R11 per-class",
)

_HOLDOUT_MISS_PATTERNS = (
    r"HOLDOUT:.*<\s*0\.",
    r"HOLDOUT failed",
    r"holdout_hard_gate.*FIRED",
)

_NUMERICAL_FAILURE_PATTERNS = (
    r"L3 assert",
    r"non-finite",
    r"NaN",
    r"harness defect",
    r"contract violation",
    r"adherence reject",
    r"compiler-bounce",
    r"PARAMETRIC_FORM.*Syntax",
    r"missing.*I_model",
    r"unit tests failed",
)

_NO_CAP_PATTERNS = (
    r"cap_inactive",
    r"score_already_below_cap",
)


def classify_cap_kind(cap_reason: Optional[str]) -> str:
    """Classify a `score_cap_reason` string into a cap kind enum.

    Returns one of: 'gaming', 'physics_violation', 'generalization_gap',
    'holdout_miss', 'numerical_failure', 'none', 'unknown'.
    """
    if not cap_reason:
        return "none"
    text = str(cap_reason)
    if not text.strip():
        return "none"

    # No-cap markers come first (some apparatus paths emit "cap_inactive_*")
    for pat in _NO_CAP_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return "none"

    # Gaming patterns dominate — if R20-R24 fired, it's gaming regardless
    # of what other gates also fired.
    for pat in _GAMING_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return "gaming"

    # Physics violations (PPN) are second — structural physics-failure
    for pat in _PHYSICS_VIOLATION_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return "physics_violation"

    # Generalization gap (farther-tail per-class)
    for pat in _GENERALIZATION_GAP_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return "generalization_gap"

    # Holdout miss (Class A primary holdout)
    for pat in _HOLDOUT_MISS_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return "holdout_miss"

    # Numerical / contract failures
    for pat in _NUMERICAL_FAILURE_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return "numerical_failure"

    return "unknown"


def is_gaming_cap(cap_reason: Optional[str]) -> bool:
    """Convenience: True iff cap kind is 'gaming'."""
    return classify_cap_kind(cap_reason) == "gaming"


def is_honest_cap(cap_reason: Optional[str]) -> bool:
    """Convenience: True iff cap kind indicates a structurally-honest form
    that should be REFINED rather than reframed.

    Honest caps: physics_violation (form has wrong physics), generalization_gap
    (form passed gaming + holdout but not farther-tail), holdout_miss (form
    is structurally OK but doesn't fit Class A well).

    These all signal "the form is engaging the variational contract; refine it" —
    NOT "pivot to a different family."
    """
    return classify_cap_kind(cap_reason) in (
        "physics_violation",
        "generalization_gap",
        "holdout_miss",
    )


def cap_kind_for_eval_history(history: list[dict]) -> list[tuple[int, str, str]]:
    """For each iter in eval_history, return (iter, cap_kind, score_cap_reason).
    Useful for selecting the "best honest-cap iter" to refine."""
    out: list[tuple[int, str, str]] = []
    for rec in history:
        if not isinstance(rec, dict):
            continue
        iter_idx = rec.get("iteration")
        if iter_idx is None:
            continue
        reason = rec.get("score_cap_reason") or ""
        kind = classify_cap_kind(reason)
        out.append((int(iter_idx), kind, reason))
    return out


def find_best_honest_iter(history: list[dict]) -> Optional[dict]:
    """Find the iter in eval_history with the highest score that capped
    via an honest mechanism (physics_violation / generalization_gap /
    holdout_miss). Returns the eval record dict, or None if no honest
    cap exists.

    This is the iter the apparatus should ENCOURAGE refinement of —
    the form was structurally honest and capped only by a refineable
    failure mode."""
    best: Optional[dict] = None
    best_score = -1
    for rec in history:
        if not isinstance(rec, dict):
            continue
        kind = classify_cap_kind(rec.get("score_cap_reason"))
        if kind not in ("physics_violation", "generalization_gap", "holdout_miss"):
            continue
        try:
            score = int(rec.get("score") or 0)
        except (TypeError, ValueError):
            continue
        # Use raw_judge_score if available — that's the pre-cap signal of
        # "how good was the form before the apparatus capped it"
        try:
            raw = rec.get("raw_judge_score")
            if raw is not None:
                raw_int = int(raw)
                if raw_int > score:
                    score = raw_int
        except (TypeError, ValueError):
            pass
        if score > best_score:
            best_score = score
            best = rec
    return best
