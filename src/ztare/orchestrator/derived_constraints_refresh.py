"""Refresh the derived-constraints ledger from one iter's eval payload.

Phase 4g extraction (2026-05-06 PM). The body coordinates four
sub-systems and was 137 lines of tangled apparatus state in
autoresearch_loop:

  - judge-emitted constraints (sanitize + ledger update)
  - GP-061 Component A: structural_extractor (cross-family invariant)
  - GP-062: trajectory_thrash_detector (preserved-skeleton signal)
  - GP-061.B: negative_space_extractor (unexplored AST slots)

Each sub-system reads workspace artifacts + appends a proposal to the
same ledger. The coordination is the value: serialised provisional-
gate updates that don't race on the ledger file.

The function takes everything it needs as explicit args. The
autoresearch_loop wrapper fills in module globals
(args.project, DERIVED_CONSTRAINTS_PATH, DERIVED_CONSTRAINTS_BRIEF_PATH,
PROJECT_DIR, rubric_data, score-regime callable, the disable flag).

Behaviour preserved verbatim from the prior inline implementation
(autoresearch_loop.py 2026-05-05 git history).
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

# These four are operational primitives the loop already imports
# elsewhere; importing them here keeps this module self-contained
# (no circular dependency with autoresearch_loop).
from src.ztare.gates.derived_constraints import (
    sanitize_constraint_proposals,
    update_derived_constraints_ledger,
    write_derived_constraints_brief,
)
from src.ztare.gates.structural_constraint_extractor import run_structural_extractor
from src.ztare.motion.trajectory_thrash_detector import (
    run_trajectory_thrash_detector,
)
from src.ztare.gates.negative_space_extractor import (
    run_negative_space_extractor,
)


def refresh_derived_constraints_from_eval(
    evaluation: dict,
    *,
    run_id: int,
    iteration_index: int,
    project_name: str,
    project_dir: str | Path,
    ledger_path: str | Path,
    brief_path: str | Path,
    confirmation_threshold_runs: int,
    score_regime_fingerprint_from_score_contract: Callable,
    disable_negative_space_extractor: bool = False,
    artifact_role: str = "latest",
) -> None:
    """Append all four constraint sources to the derived-constraints ledger.

    Order matters — judge-emitted first (highest signal-to-noise),
    then GP-061 structural, then GP-062 trajectory, then GP-061.B
    negative-space. Each block is independent and best-effort —
    a sub-extractor failure is logged but does not abort the others.

    All four sources flow through the same ``update_derived_constraints_ledger``
    serialisation, which preserves the provisional-gate discipline
    (proposal needs ≥2 distinct runs before promotion to confirmed).
    """
    project_dir = Path(project_dir)
    ledger_path = Path(ledger_path)
    brief_path = Path(brief_path)

    # ---- 1. Judge-emitted constraints from this iter's eval ----
    proposals = sanitize_constraint_proposals(evaluation.get("derived_constraints"))
    weakest_point = str(evaluation.get("weakest_point", "") or "")
    fingerprint = score_regime_fingerprint_from_score_contract(
        evaluation.get("score_contract")
    )
    ledger = update_derived_constraints_ledger(
        project=project_name,
        ledger_path=ledger_path,
        proposals=proposals,
        run_id=run_id,
        iteration_index=iteration_index,
        source_score=evaluation.get("score"),
        weakest_point=weakest_point,
        score_regime_fingerprint=fingerprint,
        artifact_role=artifact_role,
        confirmation_threshold_runs=confirmation_threshold_runs,
    )
    write_derived_constraints_brief(ledger, brief_path)
    print(
        "🧷 Derived constraints updated: "
        f"{ledger.get('confirmed_constraint_count', 0)} confirmed / "
        f"{ledger.get('provisional_constraint_count', 0)} provisional"
    )

    # ---- 2. GP-061 Component A: structural_extractor ----
    # Reads workspace/structural_memory.json, looks for a skeleton
    # shared by all failed families, emits a have-to-believe
    # constraint into the ledger.
    try:
        _, _, structural_proposal = run_structural_extractor(
            project_dir=project_dir,
            run_id=run_id,
            iteration_index=iteration_index,
        )
    except Exception as exc:  # pragma: no cover — extractor is best-effort
        print(f"⚠️  structural_extractor skipped: {exc}")
        structural_proposal = None

    if structural_proposal is not None:
        ledger = update_derived_constraints_ledger(
            project=project_name,
            ledger_path=ledger_path,
            proposals=[structural_proposal],
            run_id=run_id,
            iteration_index=iteration_index,
            source_score=evaluation.get("score"),
            weakest_point=(
                "structural_extractor: cross-family invariant in structural_memory"
            ),
            score_regime_fingerprint=fingerprint,
            artifact_role=artifact_role,
        )
        write_derived_constraints_brief(ledger, brief_path)
        print(
            "🧭 structural_extractor emitted have-to-believe constraint "
            f"(coupling={structural_proposal.get('failure_family', '?')})"
        )

    # ---- 3. GP-062: trajectory_thrash_detector ----
    # Reads latent_distance.jsonl + structural_memory.json for the
    # same-run trajectory signal and emits a constraint naming
    # preserved skeleton features when the mutator rewrites semantic
    # surface while keeping the outer skeleton. Same provisional gate
    # as GP-061 — two distinct runs required before confirmed
    # injection.
    try:
        _, thrash_proposal = run_trajectory_thrash_detector(
            project_dir=project_dir,
        )
    except Exception as exc:  # pragma: no cover — detector is best-effort
        print(f"⚠️  trajectory_thrash_detector skipped: {exc}")
        thrash_proposal = None

    if thrash_proposal is not None:
        ledger = update_derived_constraints_ledger(
            project=project_name,
            ledger_path=ledger_path,
            proposals=[thrash_proposal],
            run_id=run_id,
            iteration_index=iteration_index,
            source_score=evaluation.get("score"),
            weakest_point=(
                "trajectory_extractor: semantic-high / structural-zero thrash "
                "across iterations"
            ),
            score_regime_fingerprint=fingerprint,
            artifact_role=artifact_role,
        )
        write_derived_constraints_brief(ledger, brief_path)
        print(
            "🧭 trajectory_extractor emitted thrash constraint "
            f"(preserved_features_count="
            f"{len(thrash_proposal.get('constraint', '').split(':')[-1].split(','))})"
        )

    # ---- 4. GP-061.B: negative_space_extractor ----
    # Reads structural_memory.json via the generalized AST feature
    # matrix and emits a constraint listing (function × arg_pos ×
    # operator) slots that every failed family left empty. Same
    # provisional gate as Component A — stays in the provisional
    # bucket until a second distinct run confirms the surfaced voids.
    if disable_negative_space_extractor:
        print(
            "🚫 negative_space_extractor disabled via "
            "--disable-negative-space-extractor (GP-061.B cold-harvest discipline)"
        )
        void_proposal = None
    else:
        try:
            _, void_proposal = run_negative_space_extractor(
                project_dir=project_dir,
            )
        except Exception as exc:  # pragma: no cover — detector is best-effort
            print(f"⚠️  negative_space_extractor skipped: {exc}")
            void_proposal = None

    if void_proposal is not None:
        ledger = update_derived_constraints_ledger(
            project=project_name,
            ledger_path=ledger_path,
            proposals=[void_proposal],
            run_id=run_id,
            iteration_index=iteration_index,
            source_score=evaluation.get("score"),
            weakest_point=(
                "negative_space_extractor: unexplored structural slots across "
                "failed families"
            ),
            score_regime_fingerprint=fingerprint,
            artifact_role=artifact_role,
        )
        write_derived_constraints_brief(ledger, brief_path)
        print(
            "🧭 negative_space_extractor emitted void constraint "
            f"(void_count="
            f"{void_proposal.get('constraint', '').count(chr(10) + '  - ')})"
        )
