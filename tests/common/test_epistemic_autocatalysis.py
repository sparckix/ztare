from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import itertools
import math

import pytest

from ztare.common.epistemic_autocatalysis import (
    MeasurementAxis,
    ResidualNicheCandidate,
    ResidualSettlementTrial,
    ResponseFissionAuthority,
    SparseSettlementSchedule,
    canonical_descendant_program_sha256,
    compile_epistemic_generation,
    compile_epistemic_lineage,
    compile_residual_fission,
    compile_sparse_settlement_schedule,
    settle_residual_fission,
)
from ztare.common.wake_sleep_credit_router import MemoryScope


def _authority(suffix: str = "a") -> ResponseFissionAuthority:
    return ResponseFissionAuthority(
        scope=MemoryScope(
            task_sha256=f"task-{suffix}",
            controller_sha256=f"controller-{suffix}",
            context_sha256=f"context-{suffix}",
            choice_set_sha256=f"choices-{suffix}",
            action_vocabulary_sha256=f"actions-{suffix}",
        ),
        catalog_sha256=f"catalog-{suffix}",
        source_program_sha256=f"program-{suffix}",
        derivative_sha256=f"derivative-{suffix}",
        intervention_revision_sha256=f"revision-{suffix}",
        primitive_cost_unit="charged_environment_action",
    )


def _candidate(
    authority: ResponseFissionAuthority,
    niche_ref: str,
    signature: tuple[int, ...],
    predicted: float,
    parents: tuple[str, ...] = (),
) -> ResidualNicheCandidate:
    return ResidualNicheCandidate(
        authority=authority,
        niche_ref=niche_ref,
        response_signature=tuple(Fraction(value) for value in signature),
        predicted_information_yield=predicted,
        offline_replay_cost=0.1,
        evidence_refs=(f"offline-replay:{niche_ref}",),
        parent_child_sha256s=parents,
    )


def _fission():
    authority = _authority()
    axes = (
        MeasurementAxis("axis-a", 0.5),
        MeasurementAxis("axis-b", 0.5),
        MeasurementAxis("axis-c", 2.0),
    )
    candidates = (
        _candidate(authority, "child-a", (1, 0, 1), 0.6),
        _candidate(authority, "child-b", (0, 1, 1), 0.7),
        _candidate(authority, "child-a-copy", (2, 0, 2), 0.5),
        _candidate(authority, "child-combination", (1, 1, 2), 0.1),
    )
    return compile_residual_fission(candidates, axes=axes)


def _trials(fission, *, false_edge: bool = False, miscalibrated: bool = False):
    assignments = (
        ("withhold", "withhold"),
        ("offer", "withhold"),
        ("withhold", "offer"),
        ("offer", "offer"),
    )
    predicted = {
        row.niche_ref: row.predicted_information_yield
        for row in fission.basis_niches
    }
    rows = []
    for trajectory_index, pattern in enumerate(assignments, start=1):
        for niche_index, (niche_ref, assignment) in enumerate(
            zip(
                (row.niche_ref for row in fission.basis_niches),
                pattern,
            ),
            start=1,
        ):
            offer = assignment == "offer"
            observed = (
                0.95
                if miscalibrated and offer
                else predicted[niche_ref] + 0.1
                if offer
                else 0.1
            )
            rows.append(ResidualSettlementTrial(
                fission_sha256=fission.sha256,
                trajectory_ref=f"trajectory-{trajectory_index}",
                niche_ref=niche_ref,
                decision_index=2 + niche_index * 3,
                assignment=assignment,
                supported_transport=(
                    offer or (false_edge and niche_ref == "child-a")
                ),
                contradicted=False,
                pivot_axis_id=fission.pivot_axis(niche_ref),
                local_external_value=0.8 if offer else 0.1,
                observed_information_yield=observed,
                trajectory_primitive_action_cost=20.0,
                settlement_observation_sha256=(
                    f"observation-{trajectory_index}-{niche_index}"
                ),
            ))
    return tuple(rows)


def test_residual_fission_quotients_copies_and_selects_minimum_cost_basis() -> None:
    fission = _fission()

    assert len(fission.raw_niche_sha256s) == 4
    assert len(fission.direction_quotient_classes) == 3
    assert fission.independent_offspring_capacity == 2
    assert {row.niche_ref for row in fission.basis_niches} == {
        "child-a",
        "child-b",
    }
    assert set(fission.selected_measurement_axis_ids) == {
        "axis-a",
        "axis-b",
    }
    assert fission.selected_live_measurement_cost == 1.0
    assert fission.compression_ratio == 2.0


def test_one_parent_can_reach_supercritical_candidate_without_takeoff_claim() -> None:
    fission = _fission()
    receipt = settle_residual_fission(fission, _trials(fission))

    assert receipt.proposal_reproduction == 4.0
    assert receipt.knowledge_reproduction == 2.0
    assert receipt.error_reproduction == 0.0
    assert receipt.good_spectral_radius == 2.0
    assert receipt.error_spectral_radius == 0.0
    assert receipt.assignment_rank == 2
    assert receipt.promoted_child_count == 2
    assert receipt.shared_trajectory_cost == 80.0
    assert receipt.separate_trajectory_cost == 160.0
    assert receipt.multiplexing_gain == 2.0
    assert receipt.status == "supercritical_mechanism_candidate"
    assert receipt.to_receipt()["takeoff_supported"] is False


def test_fission_rejects_cross_authority_candidates() -> None:
    axes = (MeasurementAxis("a", 1.0), MeasurementAxis("b", 1.0))
    with pytest.raises(ValueError, match="crossed response authority"):
        compile_residual_fission(
            (
                _candidate(_authority("a"), "left", (1, 0), 0.5),
                _candidate(_authority("b"), "right", (0, 1), 0.5),
            ),
            axes=axes,
        )


def test_scalar_or_correlated_surface_cannot_manufacture_two_offspring() -> None:
    authority = _authority()
    fission = compile_residual_fission(
        (
            _candidate(authority, "left", (1,), 0.6),
            _candidate(authority, "copy", (2,), 0.5),
        ),
        axes=(MeasurementAxis("scalar", 1.0),),
    )
    assert fission.independent_offspring_capacity == 1
    assert fission.raw_proposal_reproduction == 2.0


def test_incomplete_assignment_schedule_is_rejected() -> None:
    fission = _fission()
    rows = tuple(
        row
        for row in _trials(fission)
        if row.trajectory_ref != "trajectory-4"
    )
    with pytest.raises(ValueError, match="omitted a factorial assignment"):
        settle_residual_fission(fission, rows)


def test_false_edge_reproduction_blocks_supercritical_status() -> None:
    fission = _fission()
    receipt = settle_residual_fission(
        fission,
        _trials(fission, false_edge=True),
    )
    assert receipt.error_reproduction == 1.0
    assert receipt.knowledge_reproduction == 1.0
    assert receipt.status == "subcritical_or_unresolved"


def test_information_yield_miscalibration_blocks_promotion() -> None:
    fission = _fission()
    receipt = settle_residual_fission(
        fission,
        _trials(fission, miscalibrated=True),
    )
    assert receipt.promoted_child_count < 2
    assert receipt.status == "subcritical_or_unresolved"


def test_one_generation_compiler_refuses_declared_two_generation_status() -> None:
    fission = _fission()
    with pytest.raises(ValueError, match="exactly one generation"):
        settle_residual_fission(
            fission,
            _trials(fission),
            observed_generations=2,
        )


def test_settlement_rejects_pivot_axis_drift() -> None:
    fission = _fission()
    trials = list(_trials(fission))
    trials[0] = replace(trials[0], pivot_axis_id="axis-c")
    with pytest.raises(ValueError, match="pivot-axis authority"):
        settle_residual_fission(fission, trials)


def _factorial_trials(fission, *, prefix: str):
    niches = tuple(row.niche_ref for row in fission.basis_niches)
    predicted = {
        row.niche_ref: row.predicted_information_yield
        for row in fission.basis_niches
    }
    rows = []
    for trajectory_index, pattern in enumerate(
        itertools.product(("withhold", "offer"), repeat=len(niches)),
        start=1,
    ):
        for niche_index, (niche_ref, assignment) in enumerate(
            zip(niches, pattern),
            start=1,
        ):
            offer = assignment == "offer"
            rows.append(ResidualSettlementTrial(
                fission_sha256=fission.sha256,
                trajectory_ref=f"{prefix}-trajectory-{trajectory_index}",
                niche_ref=niche_ref,
                decision_index=2 + niche_index * 3,
                assignment=assignment,
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


def _two_generation_lineage(*, second_child_count: int = 3):
    root = ("root-parent-sha256",)
    first_authority = _authority("lineage-g1")
    first_axes = (
        MeasurementAxis("axis-a", 0.5),
        MeasurementAxis("axis-b", 0.5),
        MeasurementAxis("axis-c", 2.0),
    )
    first_fission = compile_residual_fission(
        (
            _candidate(
                first_authority, "g1-a", (1, 0, 1), 0.6, root
            ),
            _candidate(
                first_authority, "g1-b", (0, 1, 1), 0.7, root
            ),
            _candidate(
                first_authority, "g1-a-copy", (2, 0, 2), 0.5, root
            ),
            _candidate(
                first_authority, "g1-combination", (1, 1, 2), 0.1, root
            ),
        ),
        axes=first_axes,
    )
    first_criticality = settle_residual_fission(
        first_fission,
        _factorial_trials(first_fission, prefix="g1"),
        parent_count=1,
    )
    first = compile_epistemic_generation(
        first_fission,
        first_criticality,
        generation_index=1,
    )

    second_authority = ResponseFissionAuthority(
        scope=first_authority.scope,
        catalog_sha256=first_authority.catalog_sha256,
        source_program_sha256=canonical_descendant_program_sha256(
            first.promoted_child_sha256s
        ),
        derivative_sha256="derivative-lineage-g2",
        intervention_revision_sha256=(
            first_authority.intervention_revision_sha256
        ),
        primitive_cost_unit=first_authority.primitive_cost_unit,
    )
    second_axes = tuple(
        MeasurementAxis(f"axis-{index}", 0.5)
        for index in range(second_child_count)
    )
    second_candidates = tuple(
        _candidate(
            second_authority,
            f"g2-{index}",
            tuple(
                1 if column == index else 0
                for column in range(second_child_count)
            ),
            0.6,
            first.promoted_child_sha256s,
        )
        for index in range(second_child_count)
    )
    second_fission = compile_residual_fission(
        second_candidates,
        axes=second_axes,
    )
    second_criticality = settle_residual_fission(
        second_fission,
        _factorial_trials(second_fission, prefix="g2"),
        parent_count=len(first.promoted_child_sha256s),
    )
    second = compile_epistemic_generation(
        second_fission,
        second_criticality,
        generation_index=2,
    )
    return first, second


def test_two_generation_lineage_binds_children_as_exact_next_parents() -> None:
    first, second = _two_generation_lineage()
    lineage = compile_epistemic_lineage((first, second))

    assert first.knowledge_reproduction == 2.0
    assert second.knowledge_reproduction == 1.5
    assert lineage.knowledge_geometric_growth == pytest.approx(math.sqrt(3))
    assert lineage.error_geometric_growth == 0.0
    assert lineage.validated_descendant_multiplier == 3.0
    assert lineage.total_shared_trajectory_cost == 240.0
    assert lineage.total_separate_trajectory_cost == 640.0
    assert lineage.status == "multigeneration_mechanism_candidate"
    assert lineage.to_receipt()["takeoff_supported"] is False


def test_lineage_rejects_parent_relabeling() -> None:
    first, second = _two_generation_lineage()
    second = replace(second, parent_child_sha256s=("unrelated-parent",))
    with pytest.raises(ValueError, match="non-promoted parent set"):
        compile_epistemic_lineage((first, second))


def test_lineage_rejects_program_family_relabeling() -> None:
    first, second = _two_generation_lineage()
    second = replace(
        second,
        authority=replace(
            second.authority,
            source_program_sha256="unrelated-program",
        ),
    )
    with pytest.raises(ValueError, match="child-family identity"):
        compile_epistemic_lineage((first, second))


def test_lineage_rejects_derivative_reuse() -> None:
    first, second = _two_generation_lineage()
    second = replace(
        second,
        authority=replace(
            second.authority,
            derivative_sha256=first.authority.derivative_sha256,
        ),
    )
    with pytest.raises(ValueError, match="reused a response derivative"):
        compile_epistemic_lineage((first, second))


@pytest.mark.parametrize(
    ("field_name", "pattern"),
    (
        ("trajectory_refs", "reused a trajectory"),
        ("trial_sha256s", "reused a trial"),
        (
            "settlement_observation_sha256s",
            "reused a settlement observation",
        ),
    ),
)
def test_lineage_rejects_cross_generation_evidence_reuse(
    field_name: str,
    pattern: str,
) -> None:
    first, second = _two_generation_lineage()
    second_values = list(getattr(second, field_name))
    second_values[0] = getattr(first, field_name)[0]
    second = replace(second, **{field_name: tuple(second_values)})
    with pytest.raises(ValueError, match=pattern):
        compile_epistemic_lineage((first, second))


def test_critical_second_generation_blocks_lineage_candidate() -> None:
    first, second = _two_generation_lineage(second_child_count=2)
    lineage = compile_epistemic_lineage((first, second))

    assert second.knowledge_reproduction == 1.0
    assert lineage.status == "subcritical_or_unresolved"


def _rank_n_fission(
    rank: int,
    *,
    parents: tuple[str, ...] = (),
):
    authority = _authority(f"rank-{rank}")
    axes = tuple(
        MeasurementAxis(f"axis-{index}", 1.0)
        for index in range(rank)
    )
    candidates = tuple(
        _candidate(
            authority,
            f"child-{index}",
            tuple(
                1 if index == column else 0
                for column in range(rank)
            ),
            0.6,
            parents,
        )
        for index in range(rank)
    )
    return compile_residual_fission(candidates, axes=axes)


def _scheduled_trials(fission, schedule, *, prefix: str):
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
                decision_index=4 + niche_index * 3,
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


@pytest.mark.parametrize("rank", tuple(range(2, 13)))
def test_sparse_additive_schedule_has_power_of_two_envelope(rank: int) -> None:
    fission = _rank_n_fission(rank)
    schedule = compile_sparse_settlement_schedule(fission)
    expected_rows = 1 << rank.bit_length()

    assert schedule.trajectory_count == expected_rows
    assert schedule.model_rank == rank + 1
    assert schedule.modeled_term_count == rank
    if rank >= 3:
        assert schedule.trajectory_count < 2 ** rank


def test_rank_three_sparse_schedule_halves_h99_second_generation_cost() -> None:
    fission = _rank_n_fission(
        3,
        parents=("parent-a", "parent-b"),
    )
    schedule = compile_sparse_settlement_schedule(fission)
    criticality = settle_residual_fission(
        fission,
        _scheduled_trials(fission, schedule, prefix="sparse-g2"),
        parent_count=2,
        require_full_factorial=False,
        settlement_schedule=schedule,
    )

    assert schedule.trajectory_count == 4
    assert criticality.knowledge_reproduction == 1.5
    assert criticality.error_reproduction == 0.0
    assert criticality.shared_trajectory_cost == 80.0
    assert criticality.separate_trajectory_cost == 240.0
    assert criticality.trajectory_compression_ratio == 2.0
    assert criticality.status == "supercritical_mechanism_candidate"


def test_declared_interaction_receives_distinct_walsh_character() -> None:
    fission = _rank_n_fission(3)
    schedule = compile_sparse_settlement_schedule(
        fission,
        modeled_interactions=(("child-0", "child-1"),),
    )

    masks = [mask for _term, mask in schedule.term_masks]
    assert schedule.trajectory_count == 8
    assert schedule.modeled_term_count == 4
    assert schedule.model_rank == 5
    assert len(masks) == len(set(masks))


def test_sparse_schedule_rejects_missing_row() -> None:
    fission = _rank_n_fission(3)
    schedule = compile_sparse_settlement_schedule(fission)
    trials = tuple(
        row
        for row in _scheduled_trials(fission, schedule, prefix="missing")
        if row.trajectory_ref != "missing-trajectory-4"
    )
    with pytest.raises(ValueError, match="compiled sparse settlement"):
        settle_residual_fission(
            fission,
            trials,
            require_full_factorial=False,
            settlement_schedule=schedule,
        )


def test_sparse_schedule_rejects_assignment_drift() -> None:
    fission = _rank_n_fission(3)
    schedule = compile_sparse_settlement_schedule(fission)
    trials = list(_scheduled_trials(fission, schedule, prefix="drift"))
    trials[0] = replace(trials[0], assignment="withhold")
    with pytest.raises(ValueError, match="compiled sparse settlement"):
        settle_residual_fission(
            fission,
            trials,
            require_full_factorial=False,
            settlement_schedule=schedule,
        )


def test_interaction_declaration_changes_schedule_authority() -> None:
    fission = _rank_n_fission(3)
    additive = compile_sparse_settlement_schedule(fission)
    interaction = compile_sparse_settlement_schedule(
        fission,
        modeled_interactions=(("child-0", "child-1"),),
    )
    trials = _scheduled_trials(fission, additive, prefix="additive")

    assert additive.sha256 != interaction.sha256
    with pytest.raises(ValueError, match="compiled sparse settlement"):
        settle_residual_fission(
            fission,
            trials,
            require_full_factorial=False,
            settlement_schedule=interaction,
        )


@pytest.mark.parametrize(
    "factor_masks",
    (
        (("child-0", 0), ("child-1", 1)),
        (("child-0", 1), ("child-1", 1)),
    ),
)
def test_sparse_schedule_rejects_zero_or_repeated_factor_masks(
    factor_masks,
) -> None:
    fission = _rank_n_fission(2)
    schedule = compile_sparse_settlement_schedule(fission)
    with pytest.raises(ValueError, match="distinct and nonzero"):
        replace(schedule, factor_masks=factor_masks)


def test_sparse_schedule_rejects_rank_deficient_pattern_forgery() -> None:
    fission = _rank_n_fission(3)
    schedule = compile_sparse_settlement_schedule(fission)
    with pytest.raises(ValueError, match="crossed Walsh factor masks"):
        replace(
            schedule,
            assignment_patterns=(
                schedule.assignment_patterns[0],
            ) * schedule.trajectory_count,
        )
