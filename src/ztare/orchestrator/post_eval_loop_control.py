"""Post-eval loop-control + information-yield persistence (Phase 4g, 2026-05-06 PM).

Two cohesive helpers extracted from autoresearch_loop:

  - ``write_latest_information_yield`` — persist the per-iter
    information-yield artifact (signal + decision + optional
    latent-motion summary) to ``workspace/latest_information_yield.json``
  - ``evaluate_post_eval_loop_control`` — compute the per-iter
    loop-control decision (continue / refresh / pivot) by enriching
    the latest signal, computing yield, optionally applying the
    bounded-discriminator latent-motion veto, then persisting the
    artifact

The two go together: the evaluator produces the
(decision, latent_motion_payload) tuple; the persister writes it.
The loop calls the evaluator + the persister is the evaluator's own
final step.

Behaviour preserved verbatim from the prior inline implementation
(autoresearch_loop.py 2026-05-05 git history).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from ztare.common.file_io import write_file


def write_latest_information_yield(
    workspace_dir: Path,
    *,
    signal,
    decision,
    latent_motion_summary: dict | None = None,
) -> None:
    """Persist the per-iter information-yield artifact.

    The artifact is a snapshot of (signal, decision[, latent_motion])
    consumed by post-run analyzers + by the next iter's mutator
    briefing context. Written verbatim — no apparatus interpretation.
    """
    payload = {
        "signal": {
            "iteration_index": signal.iteration_index,
            "score": signal.score,
            "weakest_point": signal.weakest_point,
            "score_improved": signal.score_improved,
            "runtime_failure": signal.runtime_failure,
            "catastrophic_failure": signal.catastrophic_failure,
            "novel_attack_ids": list(signal.novel_attack_ids),
            "novel_hinge_ids": list(signal.novel_hinge_ids),
            "novel_primitive_ids": list(signal.novel_primitive_ids),
            "verified_axioms_added": signal.verified_axioms_added,
            "falsification_mode": signal.falsification_mode,
            "mutation_r1_mismatch": signal.mutation_r1_mismatch,
            "claim_delta_type": signal.claim_delta_type,
            "committee_digest": signal.committee_digest,
            "prior_committee_digest": signal.prior_committee_digest,
        },
        "decision": {
            "action": decision.action.value,
            "stagnant_window": decision.stagnant_window,
            "rationale": decision.rationale,
        },
    }
    if latent_motion_summary is not None:
        payload["latent_motion_summary"] = latent_motion_summary
    write_file(
        str(workspace_dir / "latest_information_yield.json"),
        json.dumps(payload, indent=2),
    )


def evaluate_post_eval_loop_control(
    workspace_dir: Path,
    *,
    signal,
    iteration_history: list,
    project_dir: str | Path,
    underidentified_after,
    populate_weakest_class: Callable,
    stagnation_trigger_mode: Callable[[], str],
    evaluate_information_yield: Callable,
    summarize_recent_latent_motion: Callable,
    apply_latent_motion_veto: Callable,
) -> tuple[object, dict | None]:
    """Compute the post-eval loop-control decision + persist the yield artifact.

    Pipeline:

      1. Task 12 enrichment: populate ``signal.weakest_class`` if
         absent, and update the latest entry of ``iteration_history``
         in place (it's the same object reference) so subsequent
         class-novelty checks see the enriched signal.
      2. Compute the raw yield decision via ``evaluate_information_yield``,
         honoring the rubric's stagnation_trigger_mode (score-only vs
         new-class).
      3. If the substrate is in bounded_discriminator falsification
         mode, summarise recent latent motion and apply the veto if
         it changes the decision; record the latent_motion_summary
         payload either way.
      4. Persist the yield artifact via
         ``write_latest_information_yield``.

    Returns ``(final_decision, latent_motion_payload_or_None)``.

    Note: ``iteration_history`` is mutated in place when the latest
    signal needs enrichment. The autoresearch_loop wrapper passes
    its module-level history list directly, so the mutation is
    visible to subsequent iters.
    """
    # Task 12: enrich the freshly-appended signal with weakest_class
    # before yield eval. Mutation in place so the loop's history list
    # is updated.
    if iteration_history and iteration_history[-1] is signal:
        enriched = populate_weakest_class(signal)
        if enriched is not signal:
            iteration_history[-1] = enriched
            signal = enriched

    class_mode = stagnation_trigger_mode() == "new_class"
    raw_decision = evaluate_information_yield(
        iteration_history,
        underidentified_after=underidentified_after,
        class_novelty_mode=class_mode,
    )
    latent_motion_payload: dict | None = None
    final_decision = raw_decision

    if (signal.falsification_mode or "").strip().lower() == "bounded_discriminator":
        latent_motion = summarize_recent_latent_motion(project_dir=Path(project_dir))
        if latent_motion is not None:
            final_decision = apply_latent_motion_veto(
                raw_decision,
                records_considered=latent_motion.records_considered,
                mean_max_set_distance=latent_motion.mean_max_set_distance,
                threshold=latent_motion.threshold,
            )
            latent_motion_payload = {
                "records_considered": latent_motion.records_considered,
                "window_size": latent_motion.window_size,
                "mean_max_set_distance": latent_motion.mean_max_set_distance,
                "structural_move_count": latent_motion.structural_move_count,
                "motion_classes": list(latent_motion.motion_classes),
                "threshold": latent_motion.threshold,
                "veto_applied": final_decision.action != raw_decision.action,
                "base_action": raw_decision.action.value,
                "final_action": final_decision.action.value,
            }

    write_latest_information_yield(
        workspace_dir,
        signal=signal,
        decision=final_decision,
        latent_motion_summary=latent_motion_payload,
    )
    return final_decision, latent_motion_payload
