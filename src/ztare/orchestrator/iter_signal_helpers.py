"""Iter-signal helpers (Phase 4g, 2026-05-06 PM).

Two small helpers extracted from autoresearch_loop:

  - ``stagnation_trigger_mode(rubric_data)`` — read the rubric flag
    that decides between score-only stagnation (legacy) and
    new-class stagnation (Gemini Inversion #3, GP-148)
  - ``populate_weakest_class(signal)`` — enrich a frozen
    IterationSignal with `weakest_class` via the runtime regex
    classifier; returns the input unchanged when already populated
  - ``weakest_point_text(signal)`` — read weakest-point text from either
    the current IterationSignal dataclass or older dict-shaped records

Both pure / near-pure (the second imports the classifier lazily
to avoid a top-level dep cycle).

Behaviour preserved verbatim from the prior inline implementation
(autoresearch_loop.py 2026-05-05 git history).
"""
from __future__ import annotations


def stagnation_trigger_mode(rubric_data: dict) -> str:
    """Task 12 rubric flag: 'score' (legacy) | 'new_class' (Gemini Inversion #3).

    When 'new_class', evaluate_information_yield resets stagnation when
    the iteration's weakest-link class has not been seen earlier in
    the session. Champion persistence profile (GP-148) shows 28 iters
    / 10 distinct classes; score-only stagnation prematurely kills
    class-cycling. Default 'score'.
    """
    try:
        return str(rubric_data.get("stagnation_trigger_mode") or "score").strip().lower()
    except Exception:
        return "score"


def populate_weakest_class(signal):
    """Enrich signal.weakest_class via runtime classifier (cheap regex).

    Returns the input unchanged when already populated, classification
    fails, or the weakest_point string is empty. Uses dataclasses.replace
    since IterationSignal is frozen.
    """
    if signal.weakest_class or not signal.weakest_point:
        return signal
    try:
        from src.ztare.validator.weakest_link_classifier import classify_weakest_point
        cls = classify_weakest_point(signal.weakest_point)
    except Exception:
        return signal
    if not cls:
        return signal
    import dataclasses as _dc
    return _dc.replace(signal, weakest_class=cls)


def weakest_point_text(signal) -> str:
    """Return weakest-point text from an IterationSignal or legacy dict row."""
    if signal is None:
        return ""
    if isinstance(signal, dict):
        return str(signal.get("weakest_point") or "")
    return str(getattr(signal, "weakest_point", "") or "")
