from __future__ import annotations

from ztare.common.relational_task_contract import (
    EdgeTaskHypothesis,
    StateTaskHypothesis,
    TaskHypothesisVersionSpace,
    pullback_edge_hypothesis,
)


def test_edge_hypotheses_survive_empty_unary_representation() -> None:
    left = EdgeTaskHypothesis(
        "left_contract",
        lambda source, operation, outcome: (
            source == "ready"
            and operation == "left"
            and outcome == "accepted"
        ),
    )
    right = EdgeTaskHypothesis(
        "right_contract",
        lambda source, operation, outcome: (
            source == "ready"
            and operation == "right"
            and outcome == "open"
        ),
    )
    space = TaskHypothesisVersionSpace(edge_hypotheses=(left, right))

    assert not space("ready")
    assert space.state_projection_key("ready") == ()
    assert space.active_count == 2
    assert space.refute_edge_satisfied("ready", "right", "open") == (
        "right_contract",
    )
    assert space.active_ids == ("left_contract",)
    assert space.edge_satisfied_ids("ready", "left", "accepted") == (
        "left_contract",
    )


def test_relational_pullback_composes_guarded_preparation() -> None:
    hypothesis = EdgeTaskHypothesis(
        "accepted_edge",
        lambda source, operation, outcome: (
            source == "ready"
            and operation == "probe"
            and outcome == "accepted"
        ),
    )
    relation = {
        ("start", "prepare"): {"ready"},
        ("other", "prepare"): {"wrong"},
        ("ready", "probe"): {"accepted"},
        ("wrong", "probe"): {"open"},
    }

    receipt = pullback_edge_hypothesis(
        hypothesis,
        relation_targets=relation,
        preparation=("prepare",),
        probe_operation="probe",
        candidate_sources=("start", "other"),
    )

    assert receipt.initial_sources == ("start",)
    assert [row["kind"] for row in receipt.layers] == [
        "terminal_edge",
        "relational_preimage",
    ]


def test_may_and_must_pullbacks_separate_nondeterministic_edges() -> None:
    hypothesis = EdgeTaskHypothesis(
        "accepted_edge",
        lambda _source, operation, outcome: (
            operation == "probe" and outcome == "accepted"
        ),
    )
    relation = {
        ("start", "prepare"): {"ready"},
        ("ready", "probe"): {"accepted", "open"},
    }

    may = pullback_edge_hypothesis(
        hypothesis,
        relation_targets=relation,
        preparation=("prepare",),
        probe_operation="probe",
        candidate_sources=("start",),
        modality="may",
    )
    must = pullback_edge_hypothesis(
        hypothesis,
        relation_targets=relation,
        preparation=("prepare",),
        probe_operation="probe",
        candidate_sources=("start",),
        modality="must",
    )

    assert may.initial_sources == ("start",)
    assert must.initial_sources == ()


def test_unary_task_hypotheses_remain_falsifiable() -> None:
    unary = StateTaskHypothesis(
        "state_contract",
        lambda state: state == "candidate",
    )
    space = TaskHypothesisVersionSpace(state_hypotheses=(unary,))

    assert space("candidate")
    assert space.state_satisfied_ids("candidate") == ("state_contract",)
    assert space.refute_state_satisfied("candidate") == ("state_contract",)
    assert not space("candidate")
    assert space.active_count == 0


def test_worldmodel_edge_wrapper_preserves_identity_and_scope() -> None:
    from ztare.worldmodel.goal_abduction import (
        RelationalGoalEdgeHypothesisSet,
    )

    hypothesis = EdgeTaskHypothesis(
        "relation",
        lambda _source, operation, descriptor: (
            operation == 1 and descriptor == "selected"
        ),
    )
    space = TaskHypothesisVersionSpace(
        edge_hypotheses=(hypothesis,),
        source_epoch=2,
        task_contract_sha256="a" * 64,
    )
    goal = RelationalGoalEdgeHypothesisSet(
        hypotheses=space,
        describe_edge=lambda source, operation, _time: (
            "selected" if source == ((1,),) and operation == 1 else "other"
        ),
        descriptor_id="fixture.relation.v1",
        evidence_refs=("fixture:relation",),
    )

    assert goal.for_source_epoch(2) is goal
    assert goal.for_source_epoch(3) is None
    assert goal(((1,),), 1, 4)
    assert goal.satisfied_ids(((1,),), 1, 4) == ("relation",)
    assert goal.refute_satisfied(((1,),), 1, 4) == ("relation",)
    assert goal.active_count == 0
    assert len(goal.identity_sha256) == 64


def test_planner_stops_on_relational_candidate_edge() -> None:
    from ztare.worldmodel.goal_abduction import (
        RelationalGoalEdgeHypothesisSet,
    )
    from ztare.worldmodel.planner import plan_to_goal, pursue_goal

    hypothesis = EdgeTaskHypothesis(
        "relation",
        lambda _source, operation, descriptor: (
            operation == 1 and descriptor == "selected"
        ),
    )
    goal = RelationalGoalEdgeHypothesisSet(
        hypotheses=TaskHypothesisVersionSpace(
            edge_hypotheses=(hypothesis,),
            source_epoch=2,
            task_contract_sha256="b" * 64,
        ),
        describe_edge=lambda source, operation, _time: (
            "selected" if source == ((1,),) and operation == 1 else "other"
        ),
        descriptor_id="fixture.relation.v1",
    )

    def carrier(state, operation, _time):
        value = state[0][0]
        if value == 0 and operation == 0:
            return ((1,),)
        if value == 1 and operation == 1:
            return ((2,),)
        return state

    plan = plan_to_goal(
        carrier,
        ((0,),),
        2,
        goal_fn=None,
        goal_edge_fn=goal,
        max_depth=3,
    )
    assert plan is not None
    assert plan.actions == [0, 1]
    assert plan.simulated_terminal == ((1,),)

    class Adapter:
        action_arity = 2
        levels_completed = 0
        last_transition_identity = None

        def __init__(self):
            self.t = 0
            self.state = ((0,),)

        def step(self, operation):
            self.state = carrier(self.state, operation, self.t)
            self.t += 1
            return self.state

    receipt = pursue_goal(
        Adapter(),
        carrier,
        goal_edge_fn=goal,
        max_steps=2,
        max_replans=0,
        plan_depth=3,
    )

    assert receipt.status == "candidate_goal_edge_reached"
    assert receipt.trace == [0, 1]
    assert receipt.levels_gained == 0
    assert receipt.candidate_goal_edge["hypothesis_ids"] == ["relation"]
    assert receipt.candidate_goal_edge["source"] == ((1,),)


def test_factored_search_preserves_relation_truth_and_finds_edge() -> None:
    from ztare.common.factored_search import search_factored
    from ztare.worldmodel.compiled_fiber_planning import (
        CompiledFiberProjection,
        CompiledFiberRelationalGoalProblem,
        FiberFactors,
    )
    from ztare.worldmodel.goal_abduction import (
        RelationalGoalEdgeHypothesisSet,
    )

    class Projection:
        projection_sha256 = "c" * 64
        evidence_refs = ("fixture:carrier-chart",)

        @staticmethod
        def factor(_state):
            # The carrier chart intentionally erases the task distinction.
            return FiberFactors(
                controlled_base=(),
                finite_configuration=(),
                presentation_assignment=(),
                operation_domain_assignment=(),
                ordered_feasibility_configuration=(True,),
                ordered_budget=1,
                one_shot_availability=(),
            )

        @staticmethod
        def in_domain(_state):
            return True

        @staticmethod
        def explain_state_difference(left, right):
            return {
                "schema": "fixture-difference-v1",
                "left": left,
                "right": right,
            }

    hypothesis = EdgeTaskHypothesis(
        "probe_when_selected",
        lambda _source, operation, descriptor: (
            operation == "probe" and descriptor == "selected"
        ),
    )
    goal = RelationalGoalEdgeHypothesisSet(
        hypotheses=TaskHypothesisVersionSpace(
            edge_hypotheses=(hypothesis,),
            source_epoch=2,
            task_contract_sha256="d" * 64,
        ),
        describe_edge=lambda source, operation, _time: (
            "selected"
            if source == 1 and operation == "probe"
            else "other"
        ),
        descriptor_id="fixture.selected-relation.v1",
        operations=("advance", "probe"),
        evidence_refs=("fixture:held-out-edge",),
    )
    projection = Projection()

    problem = CompiledFiberProjection.problem_for(projection, goal, 0)
    assert isinstance(problem, CompiledFiberRelationalGoalProblem)
    assert problem.dominance_key(0) != problem.dominance_key(1)
    assert problem.explain_state_difference(0, 1)["task_relation_changed"]

    def predict(state, operation, _time):
        return 1 if state == 0 and operation == "advance" else state

    result = search_factored(
        predict=predict,
        start=0,
        interventions=goal.operations,
        problem=problem,
        max_depth=3,
        max_states=16,
    )

    assert result.status == "edge_found"
    assert result.actions == ("advance", "probe")


def test_exact_relational_fallback_withdraws_refuted_factor_equality() -> None:
    from ztare.common.factored_search import search_factored
    from ztare.worldmodel.compiled_fiber_planning import (
        CompiledFiberExactRelationalGoalProblem,
        CompiledFiberProjection,
        FiberFactors,
    )
    from ztare.worldmodel.goal_abduction import (
        RelationalGoalEdgeHypothesisSet,
    )

    class Projection:
        projection_sha256 = "e" * 64
        evidence_refs = ("fixture:refuted-factor-chart",)

        @staticmethod
        def factor(_state):
            return FiberFactors(
                controlled_base=(),
                finite_configuration=(),
                presentation_assignment=(),
                operation_domain_assignment=(),
                ordered_feasibility_configuration=(True,),
                ordered_budget=1,
                one_shot_availability=(),
            )

        @staticmethod
        def in_domain(_state):
            return True

        @staticmethod
        def explain_state_difference(left, right):
            return {"left": left, "right": right}

    goal = RelationalGoalEdgeHypothesisSet(
        hypotheses=TaskHypothesisVersionSpace(
            edge_hypotheses=(
                EdgeTaskHypothesis(
                    "probe_at_one",
                    lambda _source, operation, descriptor: (
                        operation == "probe" and descriptor == "selected"
                    ),
                ),
            ),
            task_contract_sha256="f" * 64,
        ),
        describe_edge=lambda source, operation, _time: (
            "selected"
            if source == 1 and operation == "probe"
            else "other"
        ),
        descriptor_id="fixture.exact-relation.v1",
        operations=("advance", "probe"),
    )
    projection = Projection()

    factored = CompiledFiberProjection.problem_for(projection, goal, 0)
    exact = CompiledFiberProjection.exact_relational_problem_for(
        projection,
        goal,
        0,
    )
    assert isinstance(exact, CompiledFiberExactRelationalGoalProblem)
    # Both observations are task-negative and factor-identical.
    assert factored.dominance_key(0) == factored.dominance_key(2)
    assert exact.dominance_key(0) != exact.dominance_key(2)

    result = search_factored(
        predict=lambda state, operation, _time: (
            1 if state == 0 and operation == "advance" else state
        ),
        start=0,
        interventions=goal.operations,
        problem=exact,
        max_depth=3,
        max_states=16,
    )
    assert result.status == "edge_found"
    assert result.actions == ("advance", "probe")
