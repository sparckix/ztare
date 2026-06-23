"""Post-fit Cage dispatch — extracted from autoresearch_loop.

Part of the GP-157 §3a backport. New POST_FIT-phase gates
register through the Cage and dispatch through this single entry-point
rather than accreting inline if-blocks in autoresearch_loop.

Today this dispatches the three POST_FIT-phase backported gates:
  - R13 substrate_critic (per-iter refresh, appends post_fit_iter_N voids)
  - R14 noise_profile (residual classifier on the fitted model)
  - R15 ANALOGY (cross-domain residual fingerprint query, gated on stagnation)

POST_FIT runs AFTER fit_primitive_features writes fit_features_result.json
but BEFORE the holdout gate harness — which then triggers post_harness
gates (R10/R11). This is the conceptual inverse of `post_harness_dispatch.py`.

Contract:
    autoresearch_loop calls `dispatch_post_fit_cage(...)` once per iter
    after the fit primitive completes. The function reads the per-iter
    context from the supplied candidate (visible_pairs, fitted_form,
    fitted_params, fit_result_json, stagnation_count, runtime, mutator
    model id) and walks the Cage's POST_FIT gate list applying can_handle
    + run. Errors are caught per-gate.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

from ztare.orchestrator.pre_fit_dispatch import (
    _engage_gates_by_phase_and_name_filter,
)


@dataclass
class PostFitVerdict:
    """Result of running POST_FIT-phase Cage gates for one iter."""
    engagements: list[dict] = field(default_factory=list)
    log_lines: list[str] = field(default_factory=list)
    error: Optional[str] = None


def dispatch_post_fit_cage(
    *,
    cage_runtime: Any,
    rubric_data: dict,
    project_dir: Path,
    workspace_dir: Path,
    iter_index: int,
    visible_pairs: Optional[list] = None,
    fitted_form: Optional[str] = None,
    fitted_params: Optional[dict] = None,
    fit_result_json: Optional[dict] = None,
    stagnation_count: int = 0,
    mutator_model_id: str = "",
    runtime: Any = None,
    project_name: str = "",
) -> PostFitVerdict:
    """PER-ITER post-fit dispatch — runs after fit_primitive_features.

    Engages R13 (substrate_critic per-iter refresh), R14 (residual
    classifier on the fitted model), and R15 (ANALOGY cross-domain
    query, gated on stagnation/pathology).

    Each gate's adapter reads from the candidate context. The dispatcher
    is intentionally context-rich because the four POST_FIT adapters
    have different input needs (substrate_critic re-loads features.py;
    noise_profile compiles the fitted form; analogy queries an LLM with
    the residual fingerprint).
    """
    verdict = PostFitVerdict()
    candidate = SimpleNamespace(
        project_dir=project_dir,
        workspace_dir=workspace_dir,
        iter_index=iter_index,
        project=project_name,
        visible_pairs=visible_pairs or [],
        fitted_form=fitted_form,
        fitted_params=fitted_params,
        fit_result_json=fit_result_json or {},
        stagnation_count=stagnation_count,
        mutator_model_id=mutator_model_id,
        runtime=runtime,
        # noise_profile_post_fit doesn't auto-route; live_rubric_data is
        # included for future symmetry with preflight.
        live_rubric_data=rubric_data,
    )
    engagements, log_lines = _engage_gates_by_phase_and_name_filter(
        cage_runtime,
        rubric_data,
        candidate,
        phase="POST_FIT",
        name_substrings=(
            "R13_substrate_critic_post_fit",
            "R14_noise_profile_post_fit",
            "R15_analogy",
        ),
    )
    verdict.engagements = engagements
    verdict.log_lines = log_lines
    return verdict
