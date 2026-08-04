import json

from ztare.worldmodel.compiled_fiber_planning import FiberFactors
from ztare.worldmodel.level_boundary_seed import replay_latest_seed_trace
from ztare.worldmodel.mechanism_effects import (
    predictive_prefixes_from_transitions,
)
from ztare.worldmodel.transition_identity import TransitionIdentity


def _factors(position):
    return FiberFactors(
        controlled_base=((position, 0),),
        finite_configuration=(0,),
        presentation_assignment=(0,),
        ordered_budget=4,
        one_shot_availability=(),
        ordered_feasibility_configuration=(True,),
    )


def test_seed_trace_resets_predictive_history_at_level_boundary(tmp_path):
    class Adapter:
        action_arity = 2

        def __init__(self):
            self.state = ((0,),)
            self.t = 0
            self.levels_completed = 0
            self.last_transition_identity = None

        def step(self, action):
            source_epoch = self.levels_completed
            self.t += 1
            self.state = ((self.t,),)
            if action == 1:
                self.levels_completed += 1
                self.last_transition_identity = TransitionIdentity(
                    kind="epoch_boundary",
                    authority="environment_adapter",
                    source_epoch=source_epoch,
                    target_epoch=self.levels_completed,
                    boundary_kind="level_completed",
                )
            else:
                self.last_transition_identity = TransitionIdentity(
                    kind="dynamics",
                    authority="environment_adapter",
                    source_epoch=source_epoch,
                    target_epoch=source_epoch,
                )
            return self.state

        def reset(self):
            self.state = ((0,),)
            self.t = 0
            return self.state

    class Projection:
        @staticmethod
        def factor(state):
            return _factors(state[0][0])

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "latest_level_boundary_seed.json").write_text(
        json.dumps({
            "completed_level": 1,
            "full_sequence_from_reset": [0, 1],
        }),
        encoding="utf-8",
    )

    receipt, transitions = replay_latest_seed_trace(tmp_path, Adapter())
    actions, effects = predictive_prefixes_from_transitions(
        transitions,
        projection=Projection(),
    )

    assert receipt["status"] == "verified"
    assert len(transitions) == 2
    assert transitions[-1].identity.boundary_kind == "level_completed"
    assert actions == ()
    assert effects == ()
    ledger_row = json.loads(
        (workspace / "level_boundary_seed_replays.jsonl").read_text(
            encoding="utf-8"
        )
    )
    assert "transitions" not in ledger_row
