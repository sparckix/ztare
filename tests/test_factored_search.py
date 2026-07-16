from dataclasses import dataclass

from ztare.common.factored_search import search_factored
from ztare.worldmodel.compiled_fiber_planning import (
    CompiledFiberProjection,
    CompiledFiberPartialOperationProblem,
    CompiledFiberOperationDiscriminationProblem,
    FiberFactors,
    OperationRecurrenceAcquisitionObligation,
    _partition_presentation,
    attach_compiled_projection,
)


@dataclass(frozen=True)
class State:
    base: int
    configuration: int
    budget: int
    renewal_available: bool


class OpaqueProblem:
    problem_id = "opaque-consumer-projection-v1"
    projection_sha256 = "a" * 64
    factor_names = ("x0", "x1", "x2", "x3")
    terminal_factor_names = ("x0", "x1")
    feasibility_factor_names = ("x2",)
    availability_factor_names = ("x3",)
    evidence_refs = ("fixture:factor-effects", "fixture:terminal-edge")

    def dominance_key(self, state):
        return state.base, state.configuration, state.renewal_available

    def dominance_vector(self, state):
        return (state.budget,)

    def goal_edge(self, state, intervention, _time):
        return (
            state.base == 3
            and state.configuration == 1
            and state.budget > 0
            and intervention == "finish"
        )

    def admissible(self, state):
        return state.budget > 0

    def estimate(self, state):
        return abs(3 - state.base) + int(state.configuration != 1)


def _predict(state, intervention, _time):
    if intervention == "advance" and state.base < 3:
        return State(
            state.base + 1,
            state.configuration,
            state.budget - 1,
            state.renewal_available,
        )
    if intervention == "configure" and state.base == 2:
        return State(
            state.base,
            1,
            state.budget - 1,
            state.renewal_available,
        )
    if intervention == "renew" and state.base == 1 and state.renewal_available:
        return State(state.base, state.configuration, 5, False)
    return state


def test_factored_search_composes_terminal_and_feasibility_coordinates():
    result = search_factored(
        predict=_predict,
        start=State(0, 0, 2, True),
        interventions=("advance", "configure", "renew", "finish"),
        problem=OpaqueProblem(),
        max_depth=12,
        max_states=100,
    )

    assert result.status == "edge_found"
    assert result.actions[-1] == "finish"
    assert "renew" in result.actions
    assert result.generated < 30


class NovelStateProblem(OpaqueProblem):
    evidence_keys = {(0, 0, True), (1, 0, True)}

    def goal_edge(self, _state, _intervention, _time):
        return False

    def state_target(self, state):
        return self.dominance_key(state) not in self.evidence_keys

    def estimate(self, _state):
        return 0


def test_factored_search_can_target_a_novel_state_identity():
    result = search_factored(
        predict=_predict,
        start=State(0, 0, 4, True),
        interventions=("advance", "configure", "renew"),
        problem=NovelStateProblem(),
        max_depth=6,
        max_states=30,
    )

    assert result.status == "state_found"
    assert result.actions == ("advance", "advance")


@dataclass(frozen=True)
class HiddenPhaseState:
    phase: int


class HiddenPhaseProblem:
    problem_id = "hidden-phase-projection-v1"
    projection_sha256 = "b" * 64
    factor_names = ("visible", "budget")
    terminal_factor_names = ("visible",)
    feasibility_factor_names = ("budget",)
    availability_factor_names = ()
    evidence_refs = ("fixture:hidden-phase",)

    def dominance_key(self, _state):
        return "same-visible-key"

    def dominance_vector(self, _state):
        return (1,)

    def goal_edge(self, state, intervention, _time):
        return state.phase == 1 and intervention == "finish"

    def admissible(self, _state):
        return True

    def estimate(self, _state):
        return 0


def test_dominance_merge_challenges_hidden_control_coordinate():
    def predict(state, intervention, _time):
        if intervention == "advance":
            return HiddenPhaseState(1)
        return state

    result = search_factored(
        predict=predict,
        start=HiddenPhaseState(0),
        interventions=("advance", "finish"),
        problem=HiddenPhaseProblem(),
        max_depth=4,
        max_states=20,
    )

    assert result.status == "projection_noncommuting"
    assert result.projection_counterexample["kind"] == "dominance_simulation_failed"
    assert result.projection_counterexample["intervention"] == repr("finish")


def test_discrete_configuration_separates_partition_from_presentation():
    first_partition, first_presentation = _partition_presentation(
        (12, 12, 5, 12, 5)
    )
    second_partition, second_presentation = _partition_presentation(
        (9, 9, 5, 9, 5)
    )

    assert first_partition == second_partition
    assert first_presentation == (12, 5)
    assert second_presentation == (9, 5)


def test_operation_acquisition_obligation_keeps_opaque_unhashable_state_identity():
    first = {"configuration": [1, 2]}
    equal_copy = {"configuration": [1, 2]}
    second = {"configuration": [2, 1]}
    obligation = OperationRecurrenceAcquisitionObligation(
        obligation_sha256="a" * 64,
        operation_identity_sha256="b" * 64,
        trigger_lowering_sha256="c" * 64,
        witnesses=(
            (first, 0, 4, "evidence:a", "epoch-a"),
            (equal_copy, 1, 5, "evidence:b", "epoch-a"),
            (second, 2, 6, "evidence:c", "epoch-b"),
        ),
        evidence_refs=("evidence:a", "evidence:b", "evidence:c"),
        trigger=lambda _source, _successor: False,
    )

    assert obligation.known_source_states == (first, second)
    assert obligation.goal_source_states == ()
    scoped = obligation.for_source_epoch("epoch-a")
    assert scoped.known_source_states == (first,)
    assert scoped.goal_source_states == ()
    assert scoped.obligation_sha256 != obligation.obligation_sha256


def test_operation_discrimination_treats_affordance_budget_as_identity():
    class Projection:
        projection_sha256 = "d" * 64
        evidence_refs = ("fixture:projection",)
        rules = ()
        sprite = ((0,),)
        _configuration_partition_next = {}

        def factor(self, state):
            return FiberFactors(
                controlled_base=((0, 0),),
                finite_configuration=(0,),
                presentation_assignment=("presentation",),
                ordered_budget=state[1],
                one_shot_availability=(),
            )

        def in_domain(self, _state):
            return True

    known = ("known", 2)
    projection = Projection()
    obligation = OperationRecurrenceAcquisitionObligation(
        obligation_sha256="a" * 64,
        operation_identity_sha256="b" * 64,
        trigger_lowering_sha256="c" * 64,
        witnesses=((known, 0, 7, "evidence:known", "epoch-a"),),
        evidence_refs=("evidence:known",),
        trigger=lambda source, _successor: source[0] == "distinct",
    )
    problem = CompiledFiberOperationDiscriminationProblem(
        projection=projection,
        target=projection.factor(known),
        terminal_intervention=0,
        target_evidence_ref="evidence:known",
        additional_evidence_refs=(),
        obligation=obligation,
        predict=lambda state, _intervention, _time: state,
    )

    assert problem.dominance_key(("same", 2)) != problem.dominance_key(
        ("same", 1)
    )
    assert problem.dominance_vector(("same", 2)) == ()
    assert problem.goal_edge(known, 0, 7) is False
    assert problem.goal_edge(known, 0, 8) is False
    assert problem.goal_edge(("distinct", 2), 0, 8) is True


def test_partial_operation_problem_targets_only_an_undefined_image():
    class Projection:
        projection_sha256 = "e" * 64
        evidence_refs = ("fixture:partial-operation",)

        def factor(self, state):
            return FiberFactors(
                controlled_base=((state[0], 0),),
                finite_configuration=(state[1],),
                presentation_assignment=("presentation",),
                ordered_budget=state[2],
                one_shot_availability=(),
            )

        def in_domain(self, _state):
            return True

    projection = Projection()

    def predict(state, intervention, _time):
        if state[1] == 3 and intervention == "probe":
            return None
        return state

    problem = CompiledFiberPartialOperationProblem(
        projection=projection,
        unresolved_configurations=frozenset({(3,)}),
        predict=predict,
    )

    assert problem.goal_edge((0, 2, 5), "probe", 0) is False
    assert problem.goal_edge((0, 3, 5), "wait", 0) is False
    assert problem.goal_edge((0, 3, 5), "probe", 0) is True


def test_patch_state_machine_refines_inherited_projection_to_partial_graph():
    projection = CompiledFiberProjection(
        sprite=((7,),),
        display_cells=((1, 0), (1, 1), (1, 2)),
        configurations=((0, 0, 1), (0, 1, 0)),
        configuration_next={(0, 0, 1): (0, 1, 0), (0, 1, 0): (0, 0, 1)},
        budget_groups=(((2, 0),),),
        budget_live_value=6,
        rules=({
            "id": "legacy_totalization",
            "bbox": (0, 1, 1),
            "type": "rotation_increment",
            "one_time": False,
        },),
        domain_predicate=lambda _state: True,
        evidence_refs=("fixture:base-projection",),
    )

    def carrier(state, _action, _time):
        return state

    carrier._ztare_factored_projection = projection
    attach_compiled_projection(
        carrier,
        {
            "PATCH_DELTA_SPEC": {
                "actions": {},
                "always": [{
                    "op": "region_event",
                    "mover_colors": [7],
                    "rect": [0, 1, 0, 1],
                    "edge": "enter",
                    "region": [1, 0, 1, 2],
                    "content_states": [[0, 0, 1], [0, 1, 0]],
                    "state_transition": [[0, 1]],
                }],
            },
        },
    )

    refined = carrier._ztare_factored_projection
    assert refined.configuration_next == {(0, 0, 1): (0, 1, 0)}
    state = ((7, 0, 0), (0, 0, 1), (6, 0, 0))
    assert refined.partial_operation_problem(start=state, predict=carrier) is not None

    def untransported_carrier(state, _action, _time):
        return state

    untransported_carrier._ztare_factored_projection = projection
    attach_compiled_projection(
        untransported_carrier,
        {
            "PATCH_DELTA_SPEC": {
                "actions": {},
                "always": [{"op": "fixed_write", "writes": [[8, [[0, 0]]]]}],
            },
        },
    )
    assert untransported_carrier._ztare_factored_projection is None


def test_operation_acquisition_obligation_loads_only_authoritative_within_epoch_witness(
    tmp_path,
    monkeypatch,
):
    from ztare.common.equivariance import stable_sha256
    from ztare.common import leaf_workbench_executor
    from ztare.worldmodel.compiled_fiber_planning import (
        operation_recurrence_acquisition_obligation,
    )
    from ztare.worldmodel.episode_log import EpisodeLog, Transition
    from ztare.worldmodel.transition_identity import TransitionIdentity

    project = tmp_path / "project"
    episode = project / "raw" / "episodes" / "episode_001.jsonl"
    state = ((0,),)
    successor = ((1,),)
    identity = TransitionIdentity(
        kind="dynamics",
        authority="environment_adapter",
        source_epoch="epoch-a",
        target_epoch="epoch-a",
        evidence_refs=("adapter:step:0",),
    )
    EpisodeLog([
        Transition(7, state, 0, successor, identity),
    ]).write_jsonl(episode)

    operation_sha = "b" * 64
    trigger_rule = {
        "op": "region_event",
        "mover_colors": [1],
        "rect": [0, 0, 0, 0],
        "edge": "enter",
        "writes": [[1, [[0, 0]]]],
    }
    obligation_identity = {
        "kind": "operation_recurrence",
        "operation_identity_sha256": operation_sha,
        "task_id": "task-a",
        "source_epoch": "epoch-a",
    }
    observation_ref = "raw/episodes/episode_001.jsonl#transition:0"
    family = {
        "mine_worldmodel_lowerable_selectors": {
            "input_hashes": {
                "kernel_receipt_ref": "workspace/workbench.json#task-a",
            },
            "output_summary": {
                "schema": "ztare-worldmodel-operation-domain-selector-v1",
                # Routing is owned by the typed obligation, not this diagnostic
                # property.  A missing safe selector is precisely when a second
                # distinguishing occurrence can be required.
                "lowerability_status": "no_operation_domain_selector_found",
                "operation_identity_sha256": operation_sha,
                "operation_lowering_sha256": stable_sha256(trigger_rule),
                "conjecture_predicates": [trigger_rule],
                "acquisition_obligation": {
                    "schema": "ztare-worldmodel-edge-acquisition-obligation-v1",
                    "obligation_identity": obligation_identity,
                    "obligation_sha256": stable_sha256(obligation_identity),
                    "source_observation_ref": observation_ref,
                },
            },
        },
    }
    monkeypatch.setattr(
        leaf_workbench_executor,
        "active_workbench_task_receipt_family",
        lambda *_args, **_kwargs: family,
    )

    obligation = operation_recurrence_acquisition_obligation(
        project,
        source_epoch="epoch-a",
    )

    assert obligation is not None
    assert obligation.witnesses == ((state, 0, 7, observation_ref, "epoch-a"),)
    assert obligation.evidence_refs == (
        "workspace/workbench.json#task-a",
        observation_ref,
    )
    assert obligation.trigger(state, successor) is True
    assert obligation.accepts_edge(state, 0, 7, successor) is False
    assert obligation.accepts_edge(state, 0, 8, successor) is False
    assert obligation.accepts_edge(state, 1, 8, successor) is True
    assert operation_recurrence_acquisition_obligation(
        project,
        source_epoch="epoch-b",
    ) is None
