from ztare.common.guarded_skill_compiler import (
    GuardedActionTrace,
    GuardedTraceTransition,
    compile_guarded_skill_library,
)
from ztare.common.partial_action_system import (
    PartialActionObservation,
    build_partial_action_system,
)
from ztare.common.relational_task_contract import (
    EdgeTaskHypothesis,
    pullback_edge_hypothesis,
)
from ztare.common.task_conditioned_reachability import (
    TaskRelationEdge,
    compile_task_reachability_basin,
    plan_task_conditioned_acquisition,
)


OPERATIONS = ("go", "finish", "gamble", "probe", "bridge", "noise")


def _system():
    rows = (
        PartialActionObservation("start", "go", "stage", "e#0"),
        PartialActionObservation("stage", "finish", "goal", "e#1"),
        PartialActionObservation("goal", "probe", "goal-done", "e#1b"),
        PartialActionObservation("chance", "gamble", "goal", "e#2"),
        PartialActionObservation("chance", "gamble", "dead-a", "e#3"),
        PartialActionObservation("left", "noise", "dead-a", "e#4"),
        PartialActionObservation("right", "noise", "dead-b", "e#5"),
        PartialActionObservation("dead-a", "noise", "dead-a", "e#6"),
        PartialActionObservation("dead-b", "noise", "dead-b", "e#7"),
        PartialActionObservation("outside", "noise", "outside", "e#8"),
    )
    return build_partial_action_system(
        rows,
        project=lambda state: state,
        effect=lambda source, operation, target, *_keys: (
            operation,
            source != target,
        ),
        projection_id="task-basin-fixture",
    )


def _basin():
    return compile_task_reachability_basin(
        _system(),
        task_edges=(
            TaskRelationEdge(
                source="goal",
                operation="probe",
                hypothesis_id="edge-goal",
                evidence_refs=("task#0",),
            ),
        ),
        task_relation_sha256="task-relation-v1",
        operations=OPERATIONS,
    )


def test_fixed_point_keeps_may_must_interval_and_exact_route():
    basin = _basin()

    assert {"start", "stage", "goal", "chance"} <= basin.may_sources
    assert {"start", "stage", "goal"} <= basin.must_sources
    assert "chance" not in basin.must_sources

    route = basin.route_from("start", modality="must")
    assert route.status == "route_found"
    assert route.actions == ("go", "finish", "probe")
    assert not route.feedback_required


def test_task_quotient_discards_transition_distinction_without_decision_effect():
    basin = _basin()
    system = basin.source_system

    assert (
        system.relation_targets[("left", "noise")]
        != system.relation_targets[("right", "noise")]
    )
    assert basin.decision_class_by_source["left"] == (
        basin.decision_class_by_source["right"]
    )


def test_missing_edge_is_selected_only_when_its_image_changes_the_basin():
    basin = _basin()

    plan = plan_task_conditioned_acquisition(
        basin,
        start_source="outside",
        predict_targets=lambda source, operation: (
            ("stage",)
            if (source, operation) == ("outside", "bridge")
            else ("dead-a",)
        ),
    )

    assert plan.status == "task_changing_frontier_found"
    assert plan.selected_frontier is not None
    assert plan.selected_frontier.operation == "bridge"
    assert plan.selected_frontier.gain_kind == "must_basin_bridge"
    assert plan.selected_frontier.actions == ("bridge",)
    assert all(
        row.operation != "noise"
        for row in plan.task_changing_frontier
    )


def test_guarded_skill_word_acts_by_relational_preimage_composition():
    traces = tuple(
        GuardedActionTrace(
            trace_ref=f"trace-{index}",
            transitions=(
                GuardedTraceTransition(
                    "start",
                    "go",
                    "stage",
                    "move",
                    f"trace-{index}#0",
                ),
                GuardedTraceTransition(
                    "stage",
                    "finish",
                    "goal",
                    "arrive",
                    f"trace-{index}#1",
                ),
            ),
        )
        for index in range(3)
    )
    library = compile_guarded_skill_library(
        traces,
        min_word_length=2,
        max_word_length=2,
        min_variant_support=2,
    )
    assert len(library.programs) == 1
    word = library.programs[0].operations
    system = _system()
    pullback = pullback_edge_hypothesis(
        EdgeTaskHypothesis(
            hypothesis_id="edge-goal",
            predicate=lambda source, operation, _outcome: (
                source == "goal" and operation == "probe"
            ),
        ),
        relation_targets=system.relation_targets,
        preparation=word,
        probe_operation="probe",
        candidate_sources=("start", "chance"),
        modality="must",
    )

    assert word == ("go", "finish")
    assert pullback.initial_sources == ("start",)
