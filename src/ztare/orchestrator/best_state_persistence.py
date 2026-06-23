"""Saved-best-state persistence (read + write) (Phase 4g, 2026-05-06).

Extracted from autoresearch_loop.py. This module owns BOTH sides of
the champion/saved-best persistence layer:

  Read side:
    - parse the best-iteration marker from a thesis file
    - look up the saved-best stem / score / meta json
    - read the score-regime fingerprint from a score_contract or meta
    - assemble the comparison anchor used to decide whether a new
      iteration's score should overwrite the saved best

  Write side:
    - persist a new best candidate: thesis content + meta json +
      probability dag snapshot, with the best_iteration marker
      threaded back into the live thesis file

Each path-dependent function takes the thesis path + history dir as
explicit arguments rather than reading module-level globals. The
autoresearch_loop wrappers fill in THESIS_PATH / HISTORY_DIR /
WORKING_PATH / BEST_ITERATION_RE / HISTORY_SCORE_RE /
LATEST_PROBABILITY_DAG_PATH so existing call sites are unchanged.

Behaviour preserved verbatim from the prior inline implementation
(autoresearch_loop.py 2026-05-05 git history).
"""
from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from ztare.common.file_io import write_file

DEFAULT_BEST_ITERATION_RE = re.compile(r"best_iteration:\s*([A-Za-z0-9_.-]+)")
DEFAULT_HISTORY_SCORE_RE = re.compile(r"_score_(\d+)_")


# ---------------------------------------------------------------------------
# Pure helpers — no apparatus state
# ---------------------------------------------------------------------------


def strip_best_iteration_marker(text: str) -> str:
    """Remove the trailing ``<!-- best_iteration: ... -->`` marker.

    The marker is appended to thesis files when an iteration becomes
    the saved best so future runs can identify the history stem. This
    helper strips it for cases where the apparatus needs the bare
    thesis content (e.g. when re-rendering for the next mutator
    prompt without leaking the marker into the prompt body).
    """
    cleaned = re.sub(
        r"\n\n<!--\s*best_iteration:\s*[A-Za-z0-9_.-]+\s*-->\s*$", "", text
    )
    return cleaned.rstrip()


def score_regime_fingerprint_from_score_contract(score_contract: Any) -> str | None:
    """Pull the regime fingerprint out of a score_contract dict, if present."""
    if not isinstance(score_contract, dict):
        return None
    fingerprint = score_contract.get("regime_fingerprint")
    if isinstance(fingerprint, str) and fingerprint.strip():
        return fingerprint.strip()
    return None


def score_regime_fingerprint_from_meta(meta: dict | None) -> str | None:
    """Pull the regime fingerprint out of a per-iteration meta json.

    Prefers the top-level ``score_regime_fingerprint`` key (newer
    schema); falls back to walking ``meta.score_contract.regime_fingerprint``
    (older schema). Returns None if neither is set.
    """
    if not isinstance(meta, dict):
        return None
    fingerprint = meta.get("score_regime_fingerprint")
    if isinstance(fingerprint, str) and fingerprint.strip():
        return fingerprint.strip()
    return score_regime_fingerprint_from_score_contract(meta.get("score_contract"))


# ---------------------------------------------------------------------------
# Path-dependent accessors — take paths as explicit args
# ---------------------------------------------------------------------------


def current_saved_best_stem(
    thesis_path: str | Path,
    *,
    best_iteration_re: re.Pattern = DEFAULT_BEST_ITERATION_RE,
) -> str | None:
    """Read the best-iteration stem from the thesis file's marker.

    Returns None if the thesis file is missing or the marker is absent.
    """
    if not os.path.exists(thesis_path):
        return None
    try:
        text = Path(thesis_path).read_text(encoding="utf-8")
    except OSError:
        return None
    match = best_iteration_re.search(text)
    if not match:
        return None
    return match.group(1)


def current_saved_best_score(
    thesis_path: str | Path,
    history_dir: str | Path,
    *,
    best_iteration_re: re.Pattern = DEFAULT_BEST_ITERATION_RE,
    history_score_re: re.Pattern = DEFAULT_HISTORY_SCORE_RE,
) -> int | None:
    """Read the saved-best score, preferring a structured meta.json
    over the legacy embedded-in-stem regex match.

    Returns None when the thesis marker is missing, the meta json is
    malformed, or no fallback regex match was found.
    """
    history_stem = current_saved_best_stem(
        thesis_path, best_iteration_re=best_iteration_re
    )
    if not history_stem:
        return None
    meta_path = Path(history_dir) / f"{history_stem}_meta.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            score = meta.get("score")
            return int(score) if score is not None else None
        except Exception:  # noqa: BLE001 — best-effort read; legacy fallback below
            pass
    match = history_score_re.search(history_stem)
    if not match:
        return None
    return int(match.group(1))


def current_saved_best_meta(
    thesis_path: str | Path,
    history_dir: str | Path,
    *,
    best_iteration_re: re.Pattern = DEFAULT_BEST_ITERATION_RE,
) -> dict | None:
    """Read the structured meta.json corresponding to the saved-best stem.

    Returns None when missing or malformed. The caller distinguishes
    "no saved best" (None from current_saved_best_stem) from
    "legacy schema, score in stem only" (None here, but
    current_saved_best_score still returns a value via the regex
    fallback) by chaining the calls.
    """
    history_stem = current_saved_best_stem(
        thesis_path, best_iteration_re=best_iteration_re
    )
    if not history_stem:
        return None
    meta_path = Path(history_dir) / f"{history_stem}_meta.json"
    if not meta_path.exists():
        return None
    try:
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — best-effort read
        return None
    return payload if isinstance(payload, dict) else None


def saved_best_history_payload(
    thesis_path: str | Path,
    history_dir: str | Path,
    *,
    best_iteration_re: re.Pattern = DEFAULT_BEST_ITERATION_RE,
) -> tuple[str | None, dict | None]:
    """Pair (stem, meta) for the saved-best iteration.

    Returns ``(None, None)`` when no saved-best stem can be parsed
    from the thesis. Returns ``(stem, None)`` when the stem exists
    but the corresponding ``{stem}_meta.json`` is absent (older
    schema runs, or file deleted). Returns ``(stem, meta)`` on the
    happy path.

    Useful as a one-call dispatch for callers that need both pieces
    (e.g. champion-artifact reconstruction reads the meta to
    reproduce the score_contract; the stem is also needed to copy
    the dag snapshot).
    """
    history_stem = current_saved_best_stem(
        thesis_path, best_iteration_re=best_iteration_re
    )
    if not history_stem:
        return None, None
    meta_path = Path(history_dir) / f"{history_stem}_meta.json"
    if not meta_path.exists():
        return history_stem, None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — best-effort read; legacy schema
        return history_stem, None
    return history_stem, (meta if isinstance(meta, dict) else None)


def saved_best_comparison_anchor(
    current_eval: dict,
    *,
    thesis_path: str | Path,
    history_dir: str | Path,
    best_iteration_re: re.Pattern = DEFAULT_BEST_ITERATION_RE,
    history_score_re: re.Pattern = DEFAULT_HISTORY_SCORE_RE,
) -> dict:
    """Compute the comparison anchor for promoting/demoting a new candidate.

    Returns a dict with keys: ``compare_score`` (the score to beat;
    None means no saved baseline), ``raw_saved_score`` (the actual
    persisted number, may be present even when compare_score is None
    in regime-mismatch cases), ``status``, ``label``.

    GP-167 fix (2026-04-25, panel-revealed): regime_mismatch
    keeps the raw saved score as the comparison anchor instead of
    returning None. Returning None had silently promoted any new
    score (even 0) over a previously-saved 50 whenever the rubric
    was edited mid-run, destroying accumulated work.
    """
    raw_saved_score = current_saved_best_score(
        thesis_path,
        history_dir,
        best_iteration_re=best_iteration_re,
        history_score_re=history_score_re,
    )
    if raw_saved_score is None:
        return {
            "compare_score": None,
            "raw_saved_score": None,
            "status": "none",
            "label": "none",
        }

    current_fingerprint = score_regime_fingerprint_from_score_contract(
        current_eval.get("score_contract")
    )
    if current_fingerprint is None:
        return {
            "compare_score": raw_saved_score,
            "raw_saved_score": raw_saved_score,
            "status": "current_regime_unknown",
            "label": str(raw_saved_score),
        }

    saved_meta = current_saved_best_meta(
        thesis_path, history_dir, best_iteration_re=best_iteration_re
    )
    if saved_meta is None:
        return {
            "compare_score": None,
            "raw_saved_score": raw_saved_score,
            "status": "legacy_missing_meta",
            "label": f"legacy_missing_meta:{raw_saved_score}",
        }

    saved_fingerprint = score_regime_fingerprint_from_meta(saved_meta)
    if saved_fingerprint is None:
        return {
            "compare_score": None,
            "raw_saved_score": raw_saved_score,
            "status": "legacy_missing_regime",
            "label": f"legacy_missing_regime:{raw_saved_score}",
        }

    if saved_fingerprint != current_fingerprint:
        # GP-167 fix: preserve the saved score as the comparison anchor
        # so the new candidate must actually beat it. Do NOT return
        # compare_score=None here — that would silently promote a
        # regression after a rubric edit.
        return {
            "compare_score": raw_saved_score,
            "raw_saved_score": raw_saved_score,
            "status": "regime_mismatch",
            "label": f"regime_mismatch:{raw_saved_score}",
        }

    return {
        "compare_score": raw_saved_score,
        "raw_saved_score": raw_saved_score,
        "status": "compatible",
        "label": str(raw_saved_score),
    }


# ---------------------------------------------------------------------------
# Write side
# ---------------------------------------------------------------------------


def persist_best_candidate(
    thesis_content: str,
    *,
    score: int,
    weakest_point: str,
    iteration: int,
    run_id: int,
    rubric_name: str,
    mutator_model_id: str,
    judge_model_id: str,
    score_contract: dict | None,
    thesis_path: str | Path,
    working_path: str | Path,
    history_dir: str | Path,
    latest_probability_dag_path: str | Path,
    session_mutator_models_used: set[str],
    session_mutator_fallback_events: list,
    score_regime_fingerprint_from_score_contract: Callable,
    extra_meta: dict | None = None,
) -> str:
    """Persist a new best candidate to the history corpus.

    Effects:
      - Writes ``{history_dir}/{stem}.md`` with the thesis content
        (best_iteration marker stripped, then re-attached after).
      - Writes ``{thesis_path}`` and ``{working_path}`` with the
        marker-bearing content so the next iter sees the new best
        as the live thesis.
      - Writes ``{history_dir}/{stem}_meta.json`` with the per-iter
        provenance (run_id, score, models, fallback events,
        weakest_point, score_contract, regime fingerprint, ts).
      - Copies ``latest_probability_dag.json`` to
        ``{history_dir}/{stem}_dag.json`` if present.

    Returns the history stem (the canonical id for the new best
    iteration; embedded into the thesis marker + meta filename).

    The session_* params are accepted as direct values (not module
    globals) so this function is testable in isolation. The
    autoresearch_loop wrapper passes the live module-level state.
    """
    clean_content = strip_best_iteration_marker(thesis_content)
    history_stem = f"{run_id}_iter{iteration}_score_{score}_{rubric_name}"
    history_dir = Path(history_dir)
    history_md_path = history_dir / f"{history_stem}.md"
    write_file(str(history_md_path), clean_content)

    thesis_with_marker = (
        clean_content + f"\n\n<!-- best_iteration: {history_stem} -->"
    )
    write_file(str(thesis_path), thesis_with_marker)
    write_file(str(working_path), thesis_with_marker)

    meta = {
        "run_id": run_id,
        "iteration": iteration,
        "score": score,
        "rubric": rubric_name,
        "mutator_model": mutator_model_id,
        "judge_model": judge_model_id,
        "effective_mutator_models": (
            sorted(session_mutator_models_used) or [mutator_model_id]
        ),
        "mutator_fallback_used": bool(session_mutator_fallback_events),
        "effective_judge_models": list(
            (score_contract or {}).get("effective_judge_models", [judge_model_id])
        ),
        "judge_fallback_used": bool(
            (score_contract or {}).get("judge_fallback_used", False)
        ),
        "weakest_point": weakest_point,
        "timestamp": datetime.now().isoformat(),
        "score_contract": score_contract or {},
        "score_regime_fingerprint": score_regime_fingerprint_from_score_contract(
            score_contract
        ),
    }
    # Merge any apparatus-specific extras (e.g. `dynamic` mode flag).
    # Caller-provided extras win over canonical fields only by explicit
    # override — defensive merge keeps the canonical schema stable.
    if extra_meta:
        for k, v in extra_meta.items():
            if k not in meta:
                meta[k] = v
            else:
                # Preserve canonical value; record the override under a
                # namespaced key so audit trails remain visible.
                meta[f"_extra_{k}"] = v
    write_file(
        str(history_dir / f"{history_stem}_meta.json"),
        json.dumps(meta, indent=2),
    )

    dag_src = Path(latest_probability_dag_path)
    if dag_src.exists():
        shutil.copy(str(dag_src), str(history_dir / f"{history_stem}_dag.json"))

    return history_stem
