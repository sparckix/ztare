#!/usr/bin/env python3
"""Run H100's Walsh-coded settlement scaling discriminator."""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import json
from pathlib import Path
import sys


REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from ztare.common.epistemic_autocatalysis import (
    MeasurementAxis,
    ResidualNicheCandidate,
    ResidualSettlementTrial,
    ResponseFissionAuthority,
    compile_residual_fission,
    compile_sparse_settlement_schedule,
    settle_residual_fission,
    stable_sha256,
)
from ztare.common.wake_sleep_credit_router import MemoryScope


BASE = Path(__file__).resolve().parent
H97 = BASE / "h97_causal_response_derivative/manifest.json"
RUNTIME = (
    BASE
    / "h97_causal_response_derivative/live_attempt_01_runtime_receipt.json"
)
H99 = BASE / "h99_lineage_bound_epistemic_branching_result.json"
OUTPUT = BASE / "h100_sparse_orthogonal_settlement_result.json"


def authority(rank: int) -> ResponseFissionAuthority:
    manifest = json.loads(H97.read_text(encoding="utf-8"))
    derivative = manifest["live_response_derivative"]
    residual = derivative["residual_contract"]
    scope = MemoryScope(**residual["scope"])
    return ResponseFissionAuthority(
        scope=scope,
        catalog_sha256=residual["catalog_sha256"],
        source_program_sha256=stable_sha256({
            "kind": "h100_rank_fixture",
            "rank": rank,
            "h97_source_program_sha256": residual["source_program_sha256"],
        }),
        derivative_sha256=stable_sha256({
            "kind": "h100_rank_derivative",
            "rank": rank,
            "h97_derivative_sha256": derivative["sha256"],
        }),
        intervention_revision_sha256=(
            residual["intervention_revision_sha256"]
        ),
        primitive_cost_unit="charged_environment_action",
    )


def rank_fission(rank: int, *, parents: tuple[str, ...] = ()):
    owner = authority(rank)
    axes = tuple(
        MeasurementAxis(f"axis-{index}", 1.0)
        for index in range(rank)
    )
    candidates = tuple(
        ResidualNicheCandidate(
            authority=owner,
            niche_ref=f"child-{index}",
            response_signature=tuple(
                Fraction(1 if index == column else 0)
                for column in range(rank)
            ),
            predicted_information_yield=0.6,
            offline_replay_cost=0.1,
            evidence_refs=(f"h100-offline-replay:{rank}:{index}",),
            parent_child_sha256s=parents,
        )
        for index in range(rank)
    )
    return compile_residual_fission(candidates, axes=axes)


def scheduled_trials(fission, schedule, *, prefix: str):
    predicted = {
        row.niche_ref: row.predicted_information_yield
        for row in fission.basis_niches
    }
    rows = []
    for trajectory_index, pattern in enumerate(
        schedule.assignment_patterns,
        start=1,
    ):
        for niche_index, (niche_ref, sign) in enumerate(
            zip(schedule.niche_refs, pattern),
            start=1,
        ):
            offer = sign == 1
            rows.append(ResidualSettlementTrial(
                fission_sha256=fission.sha256,
                trajectory_ref=f"{prefix}-trajectory-{trajectory_index}",
                niche_ref=niche_ref,
                decision_index=3 + niche_index * 4,
                assignment="offer" if offer else "withhold",
                supported_transport=offer,
                contradicted=False,
                pivot_axis_id=fission.pivot_axis(niche_ref),
                local_external_value=0.8 if offer else 0.1,
                observed_information_yield=(
                    predicted[niche_ref] + 0.1 if offer else 0.1
                ),
                trajectory_primitive_action_cost=20.0,
                settlement_observation_sha256=(
                    f"{prefix}-observation-{trajectory_index}-{niche_index}"
                ),
            ))
    return tuple(rows)


def caught(label, fn) -> dict:
    try:
        fn()
    except (KeyError, TypeError, ValueError) as exc:
        return {"label": label, "rejected": True, "reason": str(exc)}
    return {"label": label, "rejected": False, "reason": "accepted"}


def main() -> int:
    runtime = json.loads(RUNTIME.read_text(encoding="utf-8"))
    if runtime["evidence_effect"] != "none" or runtime["environment_contact"]:
        raise RuntimeError("H97 runtime boundary changed")
    h99 = json.loads(H99.read_text(encoding="utf-8"))
    if h99["verdict"] != "supported":
        raise RuntimeError("H99 prerequisite is not supported")

    scaling = []
    schedules = {}
    for rank in range(2, 13):
        fission = rank_fission(rank)
        schedule = compile_sparse_settlement_schedule(fission)
        schedules[rank] = (fission, schedule)
        scaling.append({
            "rank": rank,
            "modeled_term_count": schedule.modeled_term_count,
            "model_rank": schedule.model_rank,
            "sparse_trajectory_count": schedule.trajectory_count,
            "full_factorial_trajectory_count": (
                schedule.full_factorial_trajectory_count
            ),
            "trajectory_compression_ratio": (
                schedule.trajectory_compression_ratio
            ),
            "schedule_sha256": schedule.sha256,
        })

    rank_three = rank_fission(
        3,
        parents=("h99-promoted-parent-a", "h99-promoted-parent-b"),
    )
    rank_three_schedule = compile_sparse_settlement_schedule(rank_three)
    rank_three_trials = scheduled_trials(
        rank_three,
        rank_three_schedule,
        prefix="h100-rank3",
    )
    rank_three_criticality = settle_residual_fission(
        rank_three,
        rank_three_trials,
        parent_count=2,
        require_full_factorial=False,
        settlement_schedule=rank_three_schedule,
    )

    interaction_fission = rank_fission(3)
    interaction_schedule = compile_sparse_settlement_schedule(
        interaction_fission,
        modeled_interactions=(("child-0", "child-1"),),
    )
    interaction_masks = tuple(
        mask for _term, mask in interaction_schedule.term_masks
    )

    additive = schedules[3][1]
    additive_fission = schedules[3][0]
    additive_trials = scheduled_trials(
        additive_fission,
        additive,
        prefix="h100-additive",
    )
    missing_trials = tuple(
        row
        for row in additive_trials
        if row.trajectory_ref != "h100-additive-trajectory-4"
    )
    drifted_trials = list(additive_trials)
    drifted_trials[0] = replace(
        drifted_trials[0],
        assignment="withhold",
    )
    negatives = (
        caught(
            "zero_factor_mask",
            lambda: replace(
                schedules[2][1],
                factor_masks=(("child-0", 0), ("child-1", 1)),
            ),
        ),
        caught(
            "repeated_factor_mask",
            lambda: replace(
                schedules[2][1],
                factor_masks=(("child-0", 1), ("child-1", 1)),
            ),
        ),
        caught(
            "missing_schedule_row",
            lambda: settle_residual_fission(
                additive_fission,
                missing_trials,
                require_full_factorial=False,
                settlement_schedule=additive,
            ),
        ),
        caught(
            "assignment_drift",
            lambda: settle_residual_fission(
                additive_fission,
                tuple(drifted_trials),
                require_full_factorial=False,
                settlement_schedule=additive,
            ),
        ),
        caught(
            "post_outcome_interaction_relabel",
            lambda: settle_residual_fission(
                additive_fission,
                additive_trials,
                require_full_factorial=False,
                settlement_schedule=interaction_schedule,
            ),
        ),
        caught(
            "full_factorial_and_sparse_double_authority",
            lambda: settle_residual_fission(
                additive_fission,
                additive_trials,
                settlement_schedule=additive,
            ),
        ),
        caught(
            "rank_deficient_pattern_forgery",
            lambda: replace(
                additive,
                assignment_patterns=(
                    additive.assignment_patterns[0],
                ) * additive.trajectory_count,
            ),
        ),
    )
    passed = bool(
        all(row["model_rank"] == row["rank"] + 1 for row in scaling)
        and all(
            row["sparse_trajectory_count"]
            == 1 << row["rank"].bit_length()
            for row in scaling
        )
        and all(
            row["sparse_trajectory_count"]
            < row["full_factorial_trajectory_count"]
            for row in scaling if row["rank"] >= 3
        )
        and rank_three_schedule.trajectory_count == 4
        and rank_three_criticality.knowledge_reproduction == 1.5
        and rank_three_criticality.error_reproduction == 0.0
        and rank_three_criticality.shared_trajectory_cost == 80.0
        and rank_three_criticality.separate_trajectory_cost == 240.0
        and rank_three_criticality.status
        == "supercritical_mechanism_candidate"
        and interaction_schedule.modeled_term_count == 4
        and interaction_schedule.model_rank == 5
        and len(interaction_masks) == len(set(interaction_masks))
        and all(row["rejected"] for row in negatives)
    )
    core = {
        "schema": "ztare-h100-sparse-orthogonal-settlement-audit-v1",
        "kind": "offline_scaling_result",
        "status": "offline_complete",
        "verdict": "supported" if passed else "rejected",
        "environment_contact": False,
        "controller_contact": False,
        "h97_runtime_boundary": {
            "receipt_ref": str(RUNTIME.relative_to(REPO)),
            "status": runtime["status"],
            "evidence_effect": runtime["evidence_effect"],
        },
        "h99_result": {
            "result_ref": str(H99.relative_to(REPO)),
            "sha256": h99["sha256"],
            "verdict": h99["verdict"],
        },
        "additive_scaling": scaling,
        "rank_three_settlement": {
            "schedule": rank_three_schedule.to_receipt(),
            "criticality": rank_three_criticality.to_receipt(),
            "factorial_shared_cost_counterfactual": 160.0,
            "sparse_shared_cost": (
                rank_three_criticality.shared_trajectory_cost
            ),
            "absolute_cost_reduction": 80.0,
        },
        "declared_interaction": interaction_schedule.to_receipt(),
        "negative_fixtures": list(negatives),
        "nearest_prior_art": [
            {
                "component": "micro-randomized causal excursion effects",
                "url": "https://arxiv.org/abs/2107.03544",
            },
            {
                "component": "model-based design of experiments",
                "url": "https://arxiv.org/abs/2406.09557",
            },
        ],
        "claim_boundary": [
            "The synthetic settlement compiler removes the complete-factorial requirement for a declared sparse effect model.",
            "Rank-three shared cost falls from 160 to 80 primitive action units while the synthetic criticality verdict is unchanged.",
            "The result does not settle H97 or demonstrate live ARC offspring.",
            "The result does not authorize a capability-takeoff claim.",
            "Walsh and fractional-factorial components are established; literature novelty is not established.",
        ],
    }
    result = {**core, "sha256": stable_sha256(core)}
    OUTPUT.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "result_ref": str(OUTPUT.relative_to(REPO)),
        "verdict": result["verdict"],
        "rank_three_rows": rank_three_schedule.trajectory_count,
        "rank_three_full_factorial_rows": 8,
        "rank_three_shared_cost": (
            rank_three_criticality.shared_trajectory_cost
        ),
        "rank_twelve_rows": scaling[-1]["sparse_trajectory_count"],
        "rank_twelve_full_factorial_rows": (
            scaling[-1]["full_factorial_trajectory_count"]
        ),
        "rank_twelve_compression": (
            scaling[-1]["trajectory_compression_ratio"]
        ),
        "sha256": result["sha256"],
    }, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

