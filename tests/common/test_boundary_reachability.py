from ztare.common.boundary_reachability import (
    OptionProgramSpec,
    compile_boundary_reachability_fibers,
    compile_effect_option_families,
    plan_boundary_reachability_frontier,
    reindex_option_program,
)
from ztare.common.equivariance import stable_sha256
from ztare.common.partial_action_system import (
    PartialActionObservation,
    build_partial_action_system,
)


def _system(rows, *, effect=None):
    return build_partial_action_system(
        rows,
        project=lambda state: state,
        effect=effect or (
            lambda _source, operation, _successor, *_keys: (
                "effect",
                operation,
            )
        ),
        projection_id="fixture-boundary-reachability",
    )


def test_support_is_a_fiber_over_control_identity():
    system = _system((
        PartialActionObservation("start", 0, "middle", "trace#0"),
        PartialActionObservation("middle", 1, "end", "trace#1"),
    ))
    fibers = compile_boundary_reachability_fibers(
        system,
        operations=(0, 1, 2),
        context_key=lambda source: source == "end",
    )

    assert fibers.passed_section
    assert len(fibers.nodes) == 3
    assert fibers.support_by_node["start"] == frozenset({0})
    assert fibers.source_operation_frontier_count == 7
    assert len(fibers.context_transition_edges) == 1


def test_admission_support_can_be_coarser_than_control_state():
    system = _system((
        PartialActionObservation(
            ("same-frame", "history-a"),
            0,
            ("next", "history-a"),
            "trace#0",
        ),
        PartialActionObservation(
            "start",
            1,
            ("same-frame", "history-b"),
            "trace#1",
        ),
    ))
    fibers = compile_boundary_reachability_fibers(
        system,
        operations=(0, 1),
        context_key=lambda _source: "same",
        support_key=lambda source: (
            source[0] if isinstance(source, tuple) else source
        ),
    )

    sibling = ("same-frame", "history-b")
    assert fibers.support_by_node[sibling] == frozenset({0})
    # Support equivalence prevents a duplicate acquisition query, but no
    # transition target is copied into the history-specific control graph.
    assert (sibling, 0) not in fibers.edges


def test_frontier_rank_requires_context_or_boundary_relevance():
    system = _system((
        PartialActionObservation("start", 0, "gate", "trace#0"),
        PartialActionObservation("gate", 0, "post", "trace#1"),
        PartialActionObservation(
            "post",
            0,
            None,
            "trace#2",
            boundary_kind="lifecycle_boundary",
        ),
    ))
    fibers = compile_boundary_reachability_fibers(
        system,
        operations=(0, 1),
        context_key=lambda source: source == "post",
    )

    plan = plan_boundary_reachability_frontier(
        fibers,
        start_key="start",
    )

    assert plan.status == "boundary_relevant_frontier_found"
    assert plan.actions == (0, 0, 1)
    assert plan.route_crosses_context
    assert plan.source_has_boundary
    assert plan.target_operation == 1


def test_boundary_edges_are_not_traversed():
    system = _system((
        PartialActionObservation(
            "start",
            0,
            None,
            "trace#0",
            boundary_kind="reset",
        ),
        PartialActionObservation("unreachable", 0, "end", "trace#1"),
    ))
    fibers = compile_boundary_reachability_fibers(
        system,
        operations=(0, 1),
        context_key=lambda _source: "same",
    )

    plan = plan_boundary_reachability_frontier(
        fibers,
        start_key="start",
    )

    assert plan.actions == (1,)
    assert plan.reachable_nodes == 1
    assert plan.source_has_boundary


def test_edge_lineage_is_owned_by_the_source_operation_relation():
    system = _system((
        PartialActionObservation("left", 0, "left-next", "trace#left"),
        PartialActionObservation("right", 0, "right-next", "trace#right"),
    ), effect=lambda *_args: ("shared-effect",))
    fibers = compile_boundary_reachability_fibers(
        system,
        operations=(0,),
        context_key=lambda _source: "same",
    )

    assert system.effect_evidence_refs[(0, ("shared-effect",))] == (
        "trace#left",
        "trace#right",
    )
    assert fibers.edges[("left", 0)].evidence_refs == ("trace#left",)
    assert fibers.edges[("right", 0)].evidence_refs == ("trace#right",)


def test_option_program_survives_as_context_gated_after_refinement():
    system = _system((
        PartialActionObservation("a1", 0, "b1", "trace#0"),
        PartialActionObservation("b1", 1, "red", "trace#1"),
        PartialActionObservation("a2", 0, "b2", "trace#2"),
        PartialActionObservation("b2", 1, "blue", "trace#3"),
    ), effect=lambda _source, operation, successor, *_keys: (
        "step",
        operation,
        successor if operation == 1 else "shared",
    ))
    fibers = compile_boundary_reachability_fibers(
        system,
        operations=(0, 1),
        context_key=lambda source: (
            "red-context" if source == "red"
            else "blue-context" if source == "blue"
            else "pre"
        ),
    )
    spec = OptionProgramSpec(
        operations=(0, 1),
        initiation_source_sha256s=(
            stable_sha256("a1"),
            stable_sha256("a2"),
        ),
        lineage_refs=("trace#0", "trace#2"),
        imported_ref="older-quotient-receipt",
    )

    option = reindex_option_program(spec, fibers=fibers)

    assert option.status == "context_gated"
    assert option.resolved_initiation_count == 2
    assert len(option.variants) == 2
    assert all(
        variant.context_transitions == (1,)
        for variant in option.variants
    )
    assert all(
        variant.source_target_sha256_pairs
        for variant in option.variants
    )
    assert option.option_sha256 == spec.option_sha256
    assert "quotient" not in repr(spec.option_sha256)


def test_option_program_never_borrows_an_unwitnessed_edge():
    system = _system((
        PartialActionObservation("a1", 0, "b1", "trace#0"),
        PartialActionObservation("b1", 1, "end", "trace#1"),
        PartialActionObservation("a2", 0, "b2", "trace#2"),
    ))
    fibers = compile_boundary_reachability_fibers(
        system,
        operations=(0, 1),
        context_key=lambda _source: "same",
    )
    spec = OptionProgramSpec(
        operations=(0, 1),
        initiation_source_sha256s=(
            stable_sha256("a1"),
            stable_sha256("a2"),
        ),
        lineage_refs=("trace#0", "trace#2"),
    )

    option = reindex_option_program(spec, fibers=fibers)

    assert option.status == "partially_supported"
    assert option.resolved_initiation_count == 1
    assert option.failure_kinds == ("operation_unsupported",)


def test_option_initiation_pulls_back_over_explicit_refinement_parent():
    parent = ("a",)
    child_one = (*parent, ("predictive_context", 1))
    child_two = (*parent, ("predictive_context", 2))

    def lineage(source):
        if (
            isinstance(source, tuple)
            and source
            and isinstance(source[-1], tuple)
            and source[-1][:1] == ("predictive_context",)
        ):
            return source, source[:-1]
        return (source,)

    complete_system = _system((
        PartialActionObservation("seed-1", 9, child_one, "trace#seed-1"),
        PartialActionObservation("seed-2", 9, child_two, "trace#seed-2"),
        PartialActionObservation(child_one, 0, "red", "trace#one"),
        PartialActionObservation(child_two, 0, "blue", "trace#two"),
    ))
    complete_fibers = compile_boundary_reachability_fibers(
        complete_system,
        operations=(0, 9),
        context_key=lambda source: source,
        source_lineage_keys=lineage,
    )
    spec = OptionProgramSpec(
        operations=(0,),
        initiation_source_sha256s=(stable_sha256(parent),),
        lineage_refs=("trace#one", "trace#two"),
    )

    complete = reindex_option_program(spec, fibers=complete_fibers)

    assert complete.status == "context_gated"
    assert complete.resolved_initiation_count == 1
    assert len(complete.variants) == 2
    assert complete.option_sha256 == spec.option_sha256

    partial_system = _system((
        PartialActionObservation("seed-1", 9, child_one, "trace#seed-1"),
        PartialActionObservation("seed-2", 9, child_two, "trace#seed-2"),
        PartialActionObservation(child_one, 0, "red", "trace#one"),
    ))
    partial_fibers = compile_boundary_reachability_fibers(
        partial_system,
        operations=(0, 9),
        context_key=lambda source: source,
        source_lineage_keys=lineage,
    )

    partial = reindex_option_program(spec, fibers=partial_fibers)

    assert partial.status == "partially_supported"
    assert partial.resolved_initiation_count == 1
    assert partial.failure_kinds == ("operation_unsupported",)
    assert len(partial.variants) == 1


def test_effect_option_family_groups_motor_words_by_witnessed_effect():
    system = _system((
        PartialActionObservation("left", 0, "left-end", "trace#left"),
        PartialActionObservation("right", 1, "right-end", "trace#right"),
    ), effect=lambda *_args: ("shared-controlled-effect",))
    fibers = compile_boundary_reachability_fibers(
        system,
        operations=(0, 1),
        context_key=lambda _source: "shared-terminal-context",
    )
    left = reindex_option_program(
        OptionProgramSpec(
            operations=(0,),
            initiation_source_sha256s=(stable_sha256("left"),),
            lineage_refs=("trace#left",),
            source_family_sha256="motor-family-left",
            source_revision_sha256="motor-revision-left",
        ),
        fibers=fibers,
    )
    right = reindex_option_program(
        OptionProgramSpec(
            operations=(1,),
            initiation_source_sha256s=(stable_sha256("right"),),
            lineage_refs=("trace#right",),
            source_family_sha256="motor-family-right",
            source_revision_sha256="motor-revision-right",
        ),
        fibers=fibers,
    )

    families = compile_effect_option_families(
        (left, right),
        effect_namespace="fixture-effects",
    )

    assert len(families) == 1
    family = families[0]
    assert len(family.implementations) == 2
    assert len(family.context_variants) == 1
    assert {
        implementation.source_family_sha256
        for implementation in family.implementations
    } == {"motor-family-left", "motor-family-right"}
    assert family.to_receipt()["evidence_status"] == "effect_supported"
    assert family.to_receipt()["task_credit_transferred"] is False


def test_effect_schema_keeps_terminal_contexts_as_guarded_variants():
    system = _system((
        PartialActionObservation("left", 0, "red-end", "trace#left"),
        PartialActionObservation("right", 0, "blue-end", "trace#right"),
    ), effect=lambda *_args: ("shared-controlled-effect",))
    fibers = compile_boundary_reachability_fibers(
        system,
        operations=(0,),
        context_key=lambda source: (
            "red-context" if source == "red-end"
            else "blue-context" if source == "blue-end"
            else "pre"
        ),
    )
    option = reindex_option_program(
        OptionProgramSpec(
            operations=(0,),
            initiation_source_sha256s=(
                stable_sha256("left"),
                stable_sha256("right"),
            ),
            lineage_refs=("trace#left", "trace#right"),
            source_family_sha256="motor-family",
            source_revision_sha256="motor-revision",
        ),
        fibers=fibers,
    )

    families = compile_effect_option_families(
        (option,),
        effect_namespace="fixture-effects",
    )

    assert len(families) == 1
    family = families[0]
    assert len(family.context_variants) == 2
    assert len(family.implementations) == 2
    assert {
        variant.to_receipt()["terminal_context_sha256"]
        for variant in family.context_variants
    } == {
        stable_sha256("red-context"),
        stable_sha256("blue-context"),
    }
