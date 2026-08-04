from ztare.worldmodel.compiled_fiber_planning import FiberFactors
from ztare.common.partial_action_system import plan_observed_action_frontier
from ztare.worldmodel.mechanism_effects import (
    HistoryTrajectoryEvidence,
    build_fiber_action_system,
    compile_history_guarded_skill_library,
    fiber_mechanism_effect,
    fiber_transition_key,
    guarded_skill_option_specs,
    guarded_skill_traces_from_history_evidence,
    operation_effect_token,
    select_fiber_history_action_system,
)


def _factors(*, base=((2, 3),), budget=3, availability=()):
    return FiberFactors(
        controlled_base=base,
        finite_configuration=(0, 1),
        presentation_assignment=(9, 14),
        ordered_budget=budget,
        one_shot_availability=availability,
        ordered_feasibility_configuration=tuple(
            index < budget for index in range(4)
        ),
    )


def test_translation_effect_is_invariant_under_origin_shift():
    first = fiber_mechanism_effect(
        _factors(base=((2, 3),)),
        _factors(base=((2, 8),), budget=2),
    )
    shifted = fiber_mechanism_effect(
        _factors(base=((10, 20),)),
        _factors(base=((10, 25),), budget=2),
    )

    assert first == shifted
    assert ("controlled_base", ("translate", 0, 5)) in first


def test_presentation_labels_do_not_enter_transition_identity_or_effect():
    source = _factors()
    renamed = FiberFactors(
        **{
            **source.__dict__,
            "presentation_assignment": (3, 8),
        }
    )

    assert fiber_transition_key(source) == fiber_transition_key(renamed)
    assert fiber_mechanism_effect(source, renamed) == (("identity",),)


def test_control_exclusion_is_transported_as_boundary_partiality():
    class Projection:
        projection_sha256 = "a" * 64

        @staticmethod
        def factor(state):
            return _factors(base=((state, 0),))

    class Transition:
        s = 0
        a = 2
        t = 7
        s_next = 1
        identity = None

    system = build_fiber_action_system(
        (Transition(),),
        projection=Projection(),
        evidence_ref="fixture:control-exclusion",
        boundary_predicate=lambda source, operation, time: (
            source == 0 and operation == 2 and time == 7
        ),
    )

    assert system.relation_targets == {}
    ranked = system.ranked[0]
    assert ranked.effect == ("boundary", "control_exclusion")
    assert ranked.boundary_kind == "control_exclusion"


def test_explicit_boundary_outside_law_rows_refutes_single_valued_relation():
    class Projection:
        projection_sha256 = "b" * 64

        @staticmethod
        def factor(_state):
            return _factors(base=((0, 0),))

    class Transition:
        s = "law-presentation"
        a = 3
        t = 5
        s_next = "law-successor"
        identity = None

    system = build_fiber_action_system(
        (Transition(),),
        projection=Projection(),
        evidence_ref="fixture:law-bank",
        explicit_boundary_edges=(
            (
                "boundary-presentation",
                3,
                "sealed/eval_slice.jsonl#7",
            ),
        ),
    )
    relation_key = (fiber_transition_key(Projection.factor(None)), 3)

    assert relation_key in system.noncommuting_relations
    assert len(system.relation_effects[relation_key]) == 2
    boundary_class = (3, ("boundary", "control_exclusion"))
    assert system.effect_evidence_refs[boundary_class] == (
        "sealed/eval_slice.jsonl#7",
    )
    plan = plan_observed_action_frontier(
        system,
        start_key=relation_key[0],
        operations=(3,),
    )
    assert plan.status == "observed_frontier_exhausted"


def test_history_trajectory_preserves_adapter_boundary_identity():
    class Projection:
        projection_sha256 = "e" * 64

        @staticmethod
        def factor(_state):
            return _factors(base=((0, 0),))

    class Identity:
        kind = "epoch_boundary"
        source_epoch = 2
        target_epoch = 3

    class Transition:
        s = "terminal-source"
        a = 1
        t = 17
        s_next = "terminal-render"
        identity = Identity()

    selection = select_fiber_history_action_system(
        (Transition(),),
        projection=Projection(),
        evidence_ref="fixture:bank",
        history_trajectories=(
            HistoryTrajectoryEvidence(
                transitions=(Transition(),),
                evidence_ref="sealed/terminal.jsonl",
            ),
        ),
    )
    source_key = selection.start_key(Projection.factor(None))
    relation_key = (source_key, 1)

    assert selection.action_system.relation_targets == {}
    assert selection.action_system.relation_effects[relation_key] == (
        frozenset({("boundary", "epoch_boundary")})
    )
    boundary_class = (1, ("boundary", "epoch_boundary"))
    assert selection.action_system.effect_evidence_refs[boundary_class] == (
        "sealed/terminal.jsonl#0",
    )


def test_history_lift_selects_recursive_suffix_for_boundary_ambiguity():
    class Projection:
        projection_sha256 = "c" * 64

        @staticmethod
        def factor(_state):
            return _factors(base=((0, 0),))

    class Transition:
        s = "shared-frame"
        a = 2
        t = 3
        s_next = "law-successor"
        identity = None

    kwargs = dict(
        transitions=(Transition(),),
        projection=Projection(),
        evidence_ref="fixture:law-bank",
        history_trajectories=(
                HistoryTrajectoryEvidence(
                    transitions=(Transition(),),
                    action_prefix=(9, 9, 9, 0),
                    evidence_ref="sealed/law_slice.jsonl",
                ),
        ),
        explicit_boundary_edges=(
            (
                    "shared-frame",
                    2,
                    "sealed/eval_slice.jsonl#4",
                    (9, 9, 9, 1),
            ),
        ),
        max_suffix_length=4,
    )
    selection = select_fiber_history_action_system(**kwargs)
    exhaustive = select_fiber_history_action_system(
        **kwargs,
        exhaustive_candidates=True,
    )

    assert selection.suffix_length == 1
    assert selection.boundary_noncommuting_relations == 0
    assert selection.action_system.sha256 == exhaustive.action_system.sha256
    assert selection.history_kind == exhaustive.history_kind
    assert selection.pruned_candidate_count == 6
    assert exhaustive.pruned_candidate_count == 0
    assert selection.start_key(
        Projection.factor(None),
        action_history=(0,),
    ) in selection.action_system.fibers


def test_operation_effect_history_separates_equal_action_histories():
    class Projection:
        projection_sha256 = "d" * 64

        @staticmethod
        def factor(state):
            bases = {
                "law-pre": ((0, 0),),
                "boundary-pre": ((2, 0),),
                "law-frame": ((1, 0),),
                "boundary-frame": ((1, 0),),
                "law-successor": ((1, 1),),
            }
            return _factors(base=bases[state])

    class Transition:
        identity = None

        def __init__(self, source, action, successor, time_value):
            self.s = source
            self.a = action
            self.s_next = successor
            self.t = time_value

    law_predecessor = Transition("law-pre", 0, "law-frame", 0)
    law_edge = Transition("law-frame", 2, "law-successor", 1)
    boundary_predecessor = Transition(
        "boundary-pre",
        0,
        "boundary-frame",
        0,
    )
    boundary_edge = Transition(
        "boundary-frame",
        2,
        "law-successor",
        1,
    )
    selection = select_fiber_history_action_system(
        (law_predecessor, law_edge, boundary_predecessor),
        projection=Projection(),
        evidence_ref="fixture:operation-effect-history",
        history_trajectories=(
                HistoryTrajectoryEvidence(
                    transitions=(law_predecessor, law_edge),
                    action_prefix=(9, 9),
                    evidence_ref="sealed/law.jsonl",
                ),
                HistoryTrajectoryEvidence(
                    transitions=(boundary_predecessor, boundary_edge),
                    action_prefix=(9, 9),
                    boundary_indices=frozenset({1}),
                    evidence_ref="sealed/boundary.jsonl",
            ),
        ),
        max_suffix_length=2,
    )

    assert selection.history_kind == "operation_effect"
    assert selection.suffix_length == 1
    assert selection.boundary_noncommuting_relations == 0
    assert selection.start_key(
        Projection.factor("law-frame"),
        action_history=(0,),
        operation_effect_history=(
            operation_effect_token(Projection(), law_predecessor),
        ),
    ) in selection.action_system.fibers
    action_candidate = next(
        row
        for row in selection.candidates
        if row["history_kind"] == "action"
        and row["suffix_length"] == 1
    )
    assert action_candidate["boundary_noncommuting_relation_count"] == 1
    assert selection.pruned_candidate_count > 0


def test_history_lift_refines_terminal_collision_with_component_reservoir():
    class Projection:
        projection_sha256 = "f" * 64

        @staticmethod
        def factor(_state):
            return _factors(base=((0, 0),))

    class OrdinaryIdentity:
        kind = "dynamics"
        source_epoch = 2
        target_epoch = 2

    class TerminalIdentity:
        kind = "epoch_boundary"
        source_epoch = 2
        target_epoch = 3

    def frame(count):
        grid = [[0 for _ in range(14)] for _ in range(8)]
        for index, col in enumerate((1, 5, 9)):
            value = 8 if index < count else 3
            for row_offset in range(2):
                for col_offset in range(2):
                    grid[5 + row_offset][col + col_offset] = value
        return tuple(tuple(row) for row in grid)

    class Transition:
        def __init__(self, count, *, terminal=False):
            self.s = frame(count)
            self.a = 1
            self.t = 20 - count
            self.s_next = frame(3)
            self.identity = (
                TerminalIdentity() if terminal else OrdinaryIdentity()
            )

    safe_three = Transition(3)
    safe_two = Transition(2)
    terminal_one = Transition(1, terminal=True)
    ordered_transitions = (
        (3, safe_three),
        (3, Transition(3)),
        (2, safe_two),
        (2, Transition(2)),
        (1, terminal_one),
        (1, Transition(1, terminal=True)),
    )
    trajectories = (
        HistoryTrajectoryEvidence(
            transitions=tuple(
                transition
                for _count, transition in ordered_transitions
            ),
            action_prefix=(0,),
            evidence_ref="sealed/depleting-sequence.jsonl",
        ),
    )
    selection = select_fiber_history_action_system(
        tuple(transition for _count, transition in ordered_transitions),
        projection=Projection(),
        evidence_ref="fixture:reservoir",
        history_trajectories=trajectories,
        max_suffix_length=1,
    )
    exhaustive = select_fiber_history_action_system(
        tuple(transition for _count, transition in ordered_transitions),
        projection=Projection(),
        evidence_ref="fixture:reservoir",
        history_trajectories=trajectories,
        max_suffix_length=1,
        exhaustive_candidates=True,
    )

    assert selection.predictive_context is not None
    assert selection.predictive_context.witness_counts == (3, 3, 2, 2, 1, 1)
    assert selection.boundary_noncommuting_relations == 0
    assert not selection.action_system.noncommuting_relations
    assert selection.candidates[0]["noncommuting_relations"]
    assert selection.history_kind == exhaustive.history_kind
    assert selection.suffix_length == exhaustive.suffix_length
    assert (
        selection.predictive_context.structural_sha256
        == exhaustive.predictive_context.structural_sha256
    )
    assert selection.action_system.sha256 == exhaustive.action_system.sha256
    assert len(selection.candidates) <= 4
    assert selection.start_key(
        Projection.factor(frame(3)),
        observation=frame(3),
        action_history=(0,),
    ) in selection.action_system.fibers


def test_history_evidence_lowers_to_guarded_skills_without_crossing_boundary():
    class Projection:
        projection_sha256 = "7" * 64

        @staticmethod
        def factor(state):
            stage = {
                "clean-1": 0,
                "clean-2": 0,
                "unsafe": 0,
                "mid-1": 1,
                "mid-2": 2,
                "done": 3,
            }[state]
            return _factors(base=((stage, 0),))

    class HistoryLift:
        @staticmethod
        def start_key(
            factors,
            *,
            observation,
            action_history=(),
            operation_effect_history=(),
        ):
            context = "unsafe" if observation == "unsafe" else "clean"
            return fiber_transition_key(factors), context

    class Transition:
        identity = None

        def __init__(self, source, operation, successor, time_value):
            self.s = source
            self.a = operation
            self.s_next = successor
            self.t = time_value

    clean_one = (
        Transition("clean-1", "a", "mid-1", 0),
        Transition("mid-1", "b", "mid-2", 1),
        Transition("mid-2", "c", "done", 2),
    )
    clean_two = (
        Transition("clean-2", "a", "mid-1", 0),
        Transition("mid-1", "b", "mid-2", 1),
        Transition("mid-2", "c", "done", 2),
    )
    unsafe = (
        Transition("unsafe", "a", "mid-1", 0),
        Transition("mid-1", "b", "mid-2", 1),
        Transition("mid-2", "c", "done", 2),
    )
    trajectories = (
        HistoryTrajectoryEvidence(
            transitions=clean_one,
            evidence_ref="sealed/clean-1.jsonl",
        ),
        HistoryTrajectoryEvidence(
            transitions=clean_two,
            evidence_ref="sealed/clean-2.jsonl",
        ),
        HistoryTrajectoryEvidence(
            transitions=unsafe,
            boundary_indices=frozenset({2}),
            evidence_ref="sealed/unsafe.jsonl",
        ),
    )

    traces = guarded_skill_traces_from_history_evidence(
        trajectories,
        projection=Projection(),
        history_lift=HistoryLift(),
    )
    library = compile_history_guarded_skill_library(
        trajectories,
        projection=Projection(),
        history_lift=HistoryLift(),
        max_word_length=3,
    )

    assert len(traces) == 3
    assert traces[2].transitions[-1].boundary_kind == (
        "observed_degeneration"
    )
    assert library.exact_reconstruction
    assert len(library.programs) == 1
    program = library.programs[0]
    assert program.operations == ("a", "b", "c")
    assert program.side_exits[0].failed_step == 2
    clean_key = traces[0].transitions[0].source
    unsafe_key = traces[2].transitions[0].source
    assert program.decide(clean_key).status == "compiled"
    assert program.decide(unsafe_key).status == "primitive_fallback"
    option_specs = guarded_skill_option_specs(
        library,
        operation_namespace="fixture-actions",
    )
    assert len(option_specs) == 1
    assert option_specs[0].source_family_sha256 == (
        program.structural_sha256("fixture-actions")
    )
    assert option_specs[0].source_revision_sha256 == (
        program.skill_sha256
    )
