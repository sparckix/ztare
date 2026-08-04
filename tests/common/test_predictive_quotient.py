from ztare.common.partial_action_system import (
    PartialActionObservation,
    build_partial_action_system,
)
from ztare.common.equivariance import stable_sha256
from ztare.common.predictive_quotient import (
    compile_predictive_compatibility,
    compile_predictive_quotient,
    plan_predictive_quotient_frontier,
    plan_predictive_support_frontier,
)


def _system(observations):
    return build_partial_action_system(
        observations,
        project=lambda state: state,
        effect=lambda *_args: ("advance",),
        projection_id="fixture-predictive-quotient",
    )


def _effect_system(observations, effect):
    return build_partial_action_system(
        observations,
        project=lambda state: state,
        effect=effect,
        projection_id="fixture-predictive-compatibility",
    )


def test_predictive_quotient_merges_future_equivalent_presentations():
    system = _system((
        PartialActionObservation("a1", 0, "b1", "trace:1"),
        PartialActionObservation("a2", 0, "b2", "trace:2"),
        PartialActionObservation("b1", 1, "c1", "trace:3"),
        PartialActionObservation("b2", 1, "c2", "trace:4"),
    ))

    quotient = compile_predictive_quotient(
        system,
        operations=(0, 1),
    )

    assert quotient.passed_section
    assert quotient.passed_transport
    assert quotient.compressed
    assert quotient.class_count == 3
    assert quotient.class_for_source("a1") == quotient.class_for_source("a2")
    assert quotient.class_for_source("b1") == quotient.class_for_source("b2")
    assert quotient.class_for_source("c1") == quotient.class_for_source("c2")
    assert any(
        option.operations == (0, 1)
        and option.initiation_support == 2
        for option in quotient.options
    )


def test_unknown_and_boundary_outcomes_remain_distinct():
    system = _system((
        PartialActionObservation("root", 1, "unknown", "trace:1"),
        PartialActionObservation(
            "boundary",
            0,
            None,
            "trace:2",
            boundary_kind="control_exclusion",
        ),
    ))

    quotient = compile_predictive_quotient(
        system,
        operations=(0, 1),
    )

    assert (
        quotient.class_for_source("unknown")
        != quotient.class_for_source("boundary")
    )
    boundary_class = quotient.class_for_source("boundary")
    effects = quotient.relation_effects[(boundary_class, 0)]
    assert effects == frozenset({("boundary", "control_exclusion")})


def test_quotient_frontier_traverses_only_single_valued_edges():
    system = _system((
        PartialActionObservation("a1", 0, "b1", "trace:1"),
        PartialActionObservation("a2", 0, "b2", "trace:2"),
    ))
    quotient = compile_predictive_quotient(
        system,
        operations=(0,),
    )

    plan = plan_predictive_quotient_frontier(
        quotient,
        source_system=system,
        start_source_key="a1",
        operations=(0,),
    )

    assert plan.status == "frontier_pair_found"
    assert plan.actions == (0, 0)
    assert plan.ambiguous_edges_on_path == 0


def test_local_operation_symmetry_surfaces_orbit_completion():
    system = _system((
        PartialActionObservation("s1", 0, "t1", "trace:1"),
        PartialActionObservation("s2", 0, "t2", "trace:2"),
        PartialActionObservation("s1", 1, "t3", "trace:3"),
        PartialActionObservation("s2", 1, "t4", "trace:4"),
    ))

    quotient = compile_predictive_quotient(
        system,
        operations=(0, 1, 2),
    )

    assert len(quotient.orbit_completions) == 1
    experiment = quotient.orbit_completions[0]
    assert experiment.orbit_kind == "shared_predictive_target"
    assert experiment.witnessed_operations == (0, 1)
    assert experiment.query_operations == (2,)
    assert experiment.source_support == 2


def test_predictive_compatibility_separates_unknown_from_behavior():
    system = _effect_system((
        PartialActionObservation("s1", 0, "t1", "trace:1"),
        PartialActionObservation("root", 9, "s2", "trace:2"),
    ), lambda _source, _operation, successor, *_args: ("to", successor))

    compatibility = compile_predictive_compatibility(
        system,
        operations=(0,),
    )

    assert compatibility.is_compatible("s1", "s2")
    gap = next(
        row for row in compatibility.support_gaps
        if row.tested_source == "s1"
        and row.untested_source == "s2"
        and row.operation == 0
    )
    assert gap.effects == (("to", "t1"),)
    assert not any(
        {row.left_source, row.right_source} == {"s1", "s2"}
        for row in compatibility.incompatibilities
    )


def test_jointly_witnessed_disjoint_effects_refute_compatibility():
    system = _effect_system((
        PartialActionObservation("s1", 0, "red", "trace:1"),
        PartialActionObservation("s2", 0, "blue", "trace:2"),
    ), lambda _source, _operation, successor, *_args: ("to", successor))

    compatibility = compile_predictive_compatibility(
        system,
        operations=(0,),
    )

    assert not compatibility.is_compatible("s1", "s2")
    witness = next(
        row for row in compatibility.incompatibilities
        if {row.left_source, row.right_source} == {"s1", "s2"}
    )
    assert witness.kind == "disjoint_jointly_witnessed_effects"
    assert witness.operation == 0


def test_successor_incompatibility_propagates_to_predecessors():
    system = _effect_system((
        PartialActionObservation("s1", 0, "t1", "trace:1"),
        PartialActionObservation("s2", 0, "t2", "trace:2"),
        PartialActionObservation("t1", 1, "red", "trace:3"),
        PartialActionObservation("t2", 1, "blue", "trace:4"),
    ), lambda _source, operation, successor, *_args: (
        ("shared",) if operation == 0 else ("to", successor)
    ))

    compatibility = compile_predictive_compatibility(
        system,
        operations=(0, 1),
    )

    assert not compatibility.is_compatible("t1", "t2")
    assert not compatibility.is_compatible("s1", "s2")
    witness = next(
        row for row in compatibility.incompatibilities
        if {row.left_source, row.right_source} == {"s1", "s2"}
    )
    assert witness.kind == "joint_effect_successors_incompatible"
    assert witness.operation == 0


def test_boundary_and_dynamics_are_jointly_incompatible():
    system = _effect_system((
        PartialActionObservation(
            "boundary",
            0,
            None,
            "trace:1",
            boundary_kind="control_exclusion",
        ),
        PartialActionObservation("dynamic", 0, "target", "trace:2"),
    ), lambda *_args: ("advance",))

    compatibility = compile_predictive_compatibility(
        system,
        operations=(0,),
    )

    assert not compatibility.is_compatible("boundary", "dynamic")


def test_support_frontier_queries_unknown_member_without_borrowing_effect():
    system = _system((
        PartialActionObservation("start", 0, "start-next", "trace:0"),
        PartialActionObservation("peer", 0, "peer-next", "trace:1"),
        PartialActionObservation("peer", 1, "end", "trace:1"),
    ))
    compatibility = compile_predictive_compatibility(
        system,
        operations=(0, 1),
    )

    plan = plan_predictive_support_frontier(
        compatibility,
        source_system=system,
        start_source_key="start",
        operations=(0, 1),
    )

    assert plan.status == "support_gap_found"
    assert plan.actions == (1,)
    assert plan.target_operation == 1
    assert plan.joint_operations == (0,)


def test_support_frontier_totally_orders_tied_tested_sources():
    observations = (
        PartialActionObservation("untested", 0, "u-next", "trace:0"),
        PartialActionObservation("tested-a", 0, "a-next", "trace:1"),
        PartialActionObservation("tested-a", 1, "a-probe", "trace:2"),
        PartialActionObservation("tested-b", 0, "b-next", "trace:3"),
        PartialActionObservation("tested-b", 1, "b-probe", "trace:4"),
    )
    selected = []
    for rows in (observations, tuple(reversed(observations))):
        system = _system(rows)
        compatibility = compile_predictive_compatibility(
            system,
            operations=(0, 1),
        )
        plan = plan_predictive_support_frontier(
            compatibility,
            source_system=system,
            start_source_key="untested",
            operations=(0, 1),
        )
        assert plan.status == "support_gap_found"
        assert plan.actions == (1,)
        selected.append(plan.tested_source_sha256)

    assert selected == [
        min(stable_sha256("tested-a"), stable_sha256("tested-b"))
    ] * 2
