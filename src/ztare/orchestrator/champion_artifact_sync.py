"""Champion artifact synchronization (Phase 4g, 2026-05-06 PM).

Three cohesive operations on the champion artifact triple
(``champion_eval_results.json``, ``champion_probability_dag.json``,
``champion_evidence_gaps.json``):

  - ``reconstruct_champion_artifacts_from_saved_best`` — rebuild the
    champion triple from the saved-best history (used at startup
    when champion files are absent or stale)
  - ``champion_artifacts_out_of_sync`` — detect when the champion
    triple's regime fingerprint diverges from the saved-best meta's
    fingerprint (a warning signal that the saved best was promoted
    under a different rubric than what's currently active)
  - ``promote_latest_artifacts_to_champion`` — copy the latest
    triple to the champion triple after a successful promotion gate

Each takes paths + apparatus state (model IDs, project name) as
explicit args. The autoresearch_loop wrappers fill in module
globals (CHAMPION_*_PATH, LATEST_*_PATH, args.rubric, args.dynamic,
args.project, MUTATOR_MODEL_ID, JUDGE_MODEL_ID) so existing call
sites are unchanged.

Behaviour preserved verbatim from the prior inline implementation
(autoresearch_loop.py 2026-05-05 git history).
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Callable

from src.ztare.common.file_io import read_json, write_json

# These three are operational primitives the loop already imports
# from validator/utilities/champion_artifacts. Import once here so
# the wrappers' call sites stay clean.
from src.ztare.validator.utilities.champion_artifacts import (
    artifact_regime_fingerprint,
    build_champion_eval_from_saved_best,
    build_champion_gap_payload_from_saved_best,
    champion_artifacts_out_of_sync_with_saved_best as _audit_out_of_sync,
    set_artifact_role,
)


def reconstruct_champion_artifacts_from_saved_best(
    *,
    saved_best_history: tuple[str | None, dict | None],
    project_rubric: str,
    project_dynamic,
    project_name: str,
    mutator_model_id: str,
    judge_model_id: str,
    history_dir: str | Path,
    champion_eval_path: str | Path,
    champion_evidence_gaps_path: str | Path,
    champion_probability_dag_path: str | Path,
    score_regime_fingerprint_from_meta: Callable,
    score_regime_fingerprint_from_score_contract: Callable,
) -> dict:
    """Rebuild the champion triple from saved-best history if available.

    Returns a status dict:
      - ``reconstructed: bool`` — whether the rebuild happened
      - ``reason: str`` — "saved_best_history" on success, "saved_best_missing" otherwise
      - ``regime_fingerprint: str | None`` — the rebuilt champion's regime fingerprint

    The saved-best history is a precomputed ``(stem, meta)`` tuple
    (typically from ``saved_best_history_payload``); accepting it as
    an arg avoids re-reading the file twice when the caller already
    has it.
    """
    history_stem, meta = saved_best_history
    if not history_stem or not isinstance(meta, dict):
        return {
            "reconstructed": False,
            "reason": "saved_best_missing",
            "regime_fingerprint": None,
        }

    champion_eval = build_champion_eval_from_saved_best(
        meta,
        history_stem,
        project_rubric=project_rubric,
        project_dynamic=project_dynamic,
        project_mutator_model_id=mutator_model_id,
        project_judge_model_id=judge_model_id,
        score_regime_fingerprint_from_meta=score_regime_fingerprint_from_meta,
        score_regime_fingerprint_from_score_contract=score_regime_fingerprint_from_score_contract,
    )
    write_json(champion_eval_path, champion_eval)

    history_dag_path = Path(history_dir) / f"{history_stem}_dag.json"
    if history_dag_path.exists():
        shutil.copy(history_dag_path, champion_probability_dag_path)

    champion_gap_payload = build_champion_gap_payload_from_saved_best(
        meta,
        project_name=project_name,
        score_regime_fingerprint_from_meta=score_regime_fingerprint_from_meta,
        score_regime_fingerprint_from_score_contract=score_regime_fingerprint_from_score_contract,
    )
    write_json(champion_evidence_gaps_path, champion_gap_payload)

    return {
        "reconstructed": True,
        "reason": "saved_best_history",
        "regime_fingerprint": artifact_regime_fingerprint(
            champion_eval,
            score_regime_fingerprint_from_score_contract=score_regime_fingerprint_from_score_contract,
        ),
    }


def champion_artifacts_out_of_sync(
    *,
    champion_eval_path: str | Path,
    saved_best_history: tuple[str | None, dict | None],
    score_regime_fingerprint_from_meta: Callable,
    score_regime_fingerprint_from_score_contract: Callable,
) -> bool:
    """True if the champion triple's regime fingerprint diverges
    from the saved-best meta's fingerprint.

    Surfaces the case where the saved best was promoted under a
    different rubric than what's currently active — typical of
    rubric-edit-mid-run; the GP-167 panel-revealed fix uses this
    signal to decide whether to demote rather than discard.
    """
    champion_eval = read_json(champion_eval_path)
    history_stem, saved_meta = saved_best_history
    return _audit_out_of_sync(
        champion_eval,
        history_stem=history_stem,
        saved_meta=saved_meta,
        score_regime_fingerprint_from_meta=score_regime_fingerprint_from_meta,
        score_regime_fingerprint_from_score_contract=score_regime_fingerprint_from_score_contract,
    )


def promote_latest_artifacts_to_champion(
    *,
    latest_eval_path: str | Path,
    latest_evidence_gaps_path: str | Path,
    latest_probability_dag_path: str | Path,
    champion_eval_path: str | Path,
    champion_evidence_gaps_path: str | Path,
    champion_probability_dag_path: str | Path,
    score_regime_fingerprint_from_score_contract: Callable,
) -> dict:
    """Copy the latest triple to the champion triple after a
    successful promotion gate.

    Effects:
      - If ``latest_eval_path`` exists, set ``artifact_role=champion``
        on its payload + write to ``champion_eval_path``
      - If ``latest_probability_dag_path`` exists, copy to
        ``champion_probability_dag_path``
      - If ``latest_evidence_gaps_path`` exists, set
        ``artifact_role=champion`` on its payload + write to
        ``champion_evidence_gaps_path``

    Returns a status dict with the new champion's regime fingerprint
    + flags for which of the three artifacts were written.
    """
    latest_eval = read_json(latest_eval_path)
    champion_eval = None
    regime_fingerprint = None
    if latest_eval is not None:
        champion_eval = set_artifact_role(
            latest_eval,
            "champion",
            score_regime_fingerprint_from_score_contract=score_regime_fingerprint_from_score_contract,
        )
        write_json(champion_eval_path, champion_eval)
        regime_fingerprint = artifact_regime_fingerprint(
            champion_eval,
            score_regime_fingerprint_from_score_contract=score_regime_fingerprint_from_score_contract,
        )

    if os.path.exists(latest_probability_dag_path):
        shutil.copy(
            str(latest_probability_dag_path), str(champion_probability_dag_path)
        )

    latest_gaps = read_json(latest_evidence_gaps_path)
    if latest_gaps is not None:
        champion_gaps = set_artifact_role(
            latest_gaps,
            "champion",
            score_regime_fingerprint_from_score_contract=score_regime_fingerprint_from_score_contract,
        )
        write_json(champion_evidence_gaps_path, champion_gaps)

    return {
        "regime_fingerprint": regime_fingerprint,
        "champion_eval_written": champion_eval is not None,
        "champion_gap_written": latest_gaps is not None,
        "champion_dag_written": os.path.exists(champion_probability_dag_path),
    }
