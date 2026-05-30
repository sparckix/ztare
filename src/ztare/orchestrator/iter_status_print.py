"""Iter-status print helpers (Phase 4g, 2026-05-06 PM).

Three print helpers + one tiny predicate extracted from autoresearch_loop:

  - ``print_latest_artifact_status`` — print regime-fingerprint banner
    after a successful iter that updated `latest_*` artifacts
  - ``print_champion_artifact_status`` — banner after a successful
    champion promotion
  - ``print_champion_reconstruction_status`` — banner after a
    saved-best-history reconstruction
  - ``is_catastrophic_failure`` — simple score predicate

All four are pure (no apparatus state, no module globals beyond the
imported `artifact_regime_fingerprint` helper) and were defined inline
at autoresearch_loop.py lines 1097-1144 + 1327-1332. Moving them out
of the engine entry point makes them testable + reusable.

Behaviour preserved verbatim from the prior inline implementation
(autoresearch_loop.py 2026-05-05 git history).
"""
from __future__ import annotations

from typing import Callable

from src.ztare.validator.utilities.champion_artifacts import artifact_regime_fingerprint


def print_latest_artifact_status(
    payload: dict,
    previous_champion_fingerprint: str | None,
    *,
    score_regime_fingerprint_from_score_contract: Callable,
) -> None:
    """Print the per-iter LATEST-artifact-update banner.

    Calls into ``artifact_regime_fingerprint`` to determine whether the
    new latest-eval represents a different score regime than the
    current champion. The ``score_regime_fingerprint_from_score_contract``
    callable is passed through so the autoresearch_loop wrapper can
    fill it from the extracted best_state_persistence module.
    """
    latest_fingerprint = artifact_regime_fingerprint(
        payload,
        score_regime_fingerprint_from_score_contract=score_regime_fingerprint_from_score_contract,
    )
    shifted = (
        latest_fingerprint is not None
        and previous_champion_fingerprint is not None
        and latest_fingerprint != previous_champion_fingerprint
    )
    shifted_label = (
        "n/a" if previous_champion_fingerprint is None else ("yes" if shifted else "no")
    )
    fingerprint_label = latest_fingerprint or "unknown"
    print(
        f"🧾 LATEST artifacts updated: latest_eval_results / latest_probability_dag / latest_evidence_gaps "
        f"(regime fingerprint: {fingerprint_label}; shifted vs champion: {shifted_label})"
    )


def print_champion_artifact_status(
    previous_champion_fingerprint: str | None,
    new_champion_fingerprint: str | None,
) -> None:
    """Print the per-iter CHAMPION-artifact-update banner."""
    shifted = (
        new_champion_fingerprint is not None
        and previous_champion_fingerprint is not None
        and new_champion_fingerprint != previous_champion_fingerprint
    )
    shifted_label = (
        "n/a" if previous_champion_fingerprint is None else ("yes" if shifted else "no")
    )
    fingerprint_label = new_champion_fingerprint or "unknown"
    print(
        f"🏆 CHAMPION artifacts updated: champion_eval_results / champion_probability_dag / champion_evidence_gaps "
        f"(regime fingerprint: {fingerprint_label}; shifted vs previous champion: {shifted_label})"
    )


def print_champion_reconstruction_status(
    previous_champion_fingerprint: str | None,
    new_champion_fingerprint: str | None,
) -> None:
    """Print the saved-best-history reconstruction banner."""
    shifted = (
        new_champion_fingerprint is not None
        and previous_champion_fingerprint is not None
        and new_champion_fingerprint != previous_champion_fingerprint
    )
    shifted_label = (
        "n/a" if previous_champion_fingerprint is None else ("yes" if shifted else "no")
    )
    fingerprint_label = new_champion_fingerprint or "unknown"
    print(
        f"🛠️ CHAMPION artifacts reconstructed from saved best history "
        f"(regime fingerprint: {fingerprint_label}; shifted vs previous champion: {shifted_label})"
    )


def is_catastrophic_failure(candidate_score: int, best_score_before: int) -> bool:
    """Catastrophic-failure predicate: True if the candidate scored
    zero/negative OR collapsed to less than half of the prior best.

    Used by the iter loop to decide whether to suppress promotion
    + roll back project state to the prior champion.
    """
    if candidate_score <= 0:
        return True
    if best_score_before > 0 and candidate_score < (best_score_before * 0.5):
        return True
    return False
