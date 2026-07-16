from __future__ import annotations

import json
import hashlib
import sys
from types import SimpleNamespace

import pytest

from ztare.common.observation_chart import ObservationChart
from ztare.worldmodel.episode_log import (
    EpisodeIdentityBindingError,
    EpisodeLog,
    Transition,
    declared_episode_observation_chart,
)
from ztare.worldmodel.gates import env_frame_indices
from ztare.worldmodel.grid_dsl import grid_from_lists
from ztare.worldmodel.transition_identity import (
    ObjectIdentityLink,
    TransitionIdentity,
)


def _grid(rows):
    return grid_from_lists(rows)


def test_multi_chart_sidecar_requires_explicit_episode_chart_identity() -> None:
    replay = ObservationChart(
        "replay", "v1", "transition-v1", ("state",), "collector"
    )
    bank = ObservationChart(
        "bank", "v1", "transition-v1", ("state",), "collector"
    )
    payload = {"observation_charts": [replay.to_dict(), bank.to_dict()]}

    with pytest.raises(EpisodeIdentityBindingError, match="episode_chart_sha256"):
        declared_episode_observation_chart(payload)

    payload["episode_chart_sha256"] = bank.sha256
    assert declared_episode_observation_chart(payload) == bank


def test_partial_object_correspondence_supports_genesis_annihilation_and_relation() -> None:
    links = (
        ObjectIdentityLink(None, "new-object", "receipt:new"),
        ObjectIdentityLink("spent-object", None, "receipt:spent"),
        ObjectIdentityLink("parent", "child-a"),
        ObjectIdentityLink("parent", "child-b"),
    )
    identity = TransitionIdentity(
        kind="epoch_boundary",
        authority="environment_adapter",
        source_epoch=4,
        target_epoch=5,
        boundary_kind="level_completed",
        object_correspondence=links,
    )

    payload = identity.to_dict()
    assert [row["relation"] for row in payload["object_correspondence"]] == [
        "genesis",
        "annihilation",
        "correspondence",
        "correspondence",
    ]
    assert TransitionIdentity.from_dict(payload) == identity


def test_episode_log_roundtrip_preserves_transition_identity_and_legacy_shape(tmp_path) -> None:
    a = _grid([[1, 2], [2, 1]])
    b = _grid([[2, 1], [1, 2]])
    identity = TransitionIdentity(
        kind="epoch_boundary",
        authority="environment_adapter",
        source_epoch="episode-1",
        target_epoch="episode-2",
        boundary_kind="reset",
    )
    log = EpisodeLog()
    log.append(a, 0, b, t=7, identity=identity)
    log.append(b, 1, a, t=0)
    path = tmp_path / "episode.jsonl"
    log.write_jsonl(path)

    raw_rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert raw_rows[0]["identity"]["kind"] == "epoch_boundary"
    assert "identity" not in raw_rows[1]
    loaded = EpisodeLog.read_jsonl(path)
    assert loaded.transitions()[0].identity == identity
    assert loaded.transitions()[1].identity is None
    assert loaded.content_hash() == log.content_hash()

    selected = EpisodeLog.read_jsonl_indices(path, {0, 1})
    assert selected[0] == loaded.transitions()[0]
    assert selected[1] == loaded.transitions()[1]
    with pytest.raises(IndexError, match="outside log"):
        EpisodeLog.read_jsonl_indices(path, {2})


def test_sidecar_advances_across_compatible_append_but_rejects_bound_row_mutation(tmp_path) -> None:
    a = _grid([[1]])
    b = _grid([[2]])
    c = _grid([[3]])
    identity = TransitionIdentity(
        kind="dynamics",
        authority="environment_adapter",
        source_epoch=4,
        target_epoch=4,
    )
    path = tmp_path / "episode.jsonl"
    EpisodeLog([Transition(7, a, 0, b)]).write_jsonl(path)
    first = EpisodeLog.read_jsonl(path).transitions()[0]
    sidecar = path.with_name("episode.identity.json")
    sidecar.write_text(json.dumps({
        "schema": "ztare-episode-identity-sidecar-v1",
        "episode_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bindings": [{
            "row_index": 0,
            "observation_sha256": first.observation_hash(),
            "attestation_kind": "exact_environment_replay",
            "identity": identity.to_dict(),
        }],
        "transport_windows": [],
        "observation_charts": [],
    }))

    loaded = EpisodeLog.read_jsonl(path)
    assert EpisodeLog.read_jsonl_indices(path, {0})[0].identity == identity
    loaded.append(b, 0, c, t=8)
    loaded.write_jsonl(path)
    rebound = json.loads(sidecar.read_text())
    assert rebound["episode_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert len(EpisodeLog.read_jsonl(path)) == 2

    before = path.read_bytes()
    mutated = EpisodeLog([Transition(7, c, 0, b, identity), loaded.transitions()[1]])
    with pytest.raises(EpisodeIdentityBindingError, match="does not match transition bytes"):
        mutated.write_jsonl(path)
    assert path.read_bytes() == before


def test_incremental_append_advances_sidecar_without_rewriting_prefix(tmp_path) -> None:
    a = _grid([[1]])
    b = _grid([[2]])
    c = _grid([[3]])
    path = tmp_path / "episode.jsonl"
    EpisodeLog([Transition(7, a, 0, b)]).write_jsonl(path)
    first = EpisodeLog.read_jsonl(path).transitions()[0]
    sidecar = path.with_name("episode.identity.json")
    sidecar.write_text(json.dumps({
        "schema": "ztare-episode-identity-sidecar-v1",
        "episode_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bindings": [{
            "row_index": 0,
            "observation_sha256": first.observation_hash(),
            "attestation_kind": "exact_environment_replay",
            "identity": TransitionIdentity(
                kind="dynamics",
                authority="environment_adapter",
                source_epoch=1,
                target_epoch=1,
            ).to_dict(),
        }],
        "transport_windows": [],
        "observation_charts": [],
    }))
    loaded = EpisodeLog.read_jsonl(path)
    prefix = path.read_bytes()

    assert loaded.append_jsonl(path, [Transition(8, b, 0, c)]) == 1
    assert path.read_bytes().startswith(prefix)
    assert len(EpisodeLog.read_jsonl(path)) == 2
    rebound = json.loads(sidecar.read_text())
    assert rebound["episode_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()

    stale = EpisodeLog([Transition(7, a, 0, b)])
    with pytest.raises(EpisodeIdentityBindingError, match="loaded from the target"):
        stale.append_jsonl(path, [Transition(9, c, 0, a)])


def test_gate_uses_authoritative_identity_and_refuses_untrusted_excuse() -> None:
    # Identical observed values, three different identity authorities. Counts
    # are preserved so the legacy refill heuristic has no independent reason
    # to exclude any row.
    before = _grid([[1, 2], [2, 1]])
    after = _grid([[2, 1], [1, 2]])
    boundary = TransitionIdentity(
        kind="epoch_boundary",
        authority="environment_adapter",
        source_epoch=1,
        target_epoch=2,
        boundary_kind="level_completed",
    )
    dynamics = TransitionIdentity(
        kind="dynamics",
        authority="environment_adapter",
        source_epoch=2,
        target_epoch=2,
        evidence_refs=("environment_api:within_epoch_transition",),
    )
    untrusted = TransitionIdentity(
        kind="epoch_boundary",
        authority="candidate",
        source_epoch=2,
        target_epoch=3,
        boundary_kind="claimed_reset",
    )
    log = EpisodeLog(
        [
            Transition(3, before, 0, after, boundary),
            Transition(3, before, 0, after, dynamics),
            Transition(3, before, 0, after, untrusted),
        ]
    )

    assert env_frame_indices(log) == {0}


def test_unsupported_dynamics_default_does_not_hide_structural_reset() -> None:
    """No boundary signal is not an attestation that no boundary occurred."""

    default_dynamics = TransitionIdentity(
        kind="dynamics",
        authority="environment_adapter",
        source_epoch=2,
        target_epoch=2,
    )
    attested_dynamics = TransitionIdentity(
        kind="dynamics",
        authority="environment_adapter",
        source_epoch=2,
        target_epoch=2,
        evidence_refs=("environment_api:within_epoch_transition",),
    )
    full = _grid([[7, 7, 7]])
    two = _grid([[7, 7, 0]])
    one = _grid([[7, 0, 0]])
    empty = _grid([[0, 0, 0]])

    inferred = EpisodeLog([
        Transition(0, full, 0, two, default_dynamics),
        Transition(1, two, 0, one, default_dynamics),
        Transition(2, empty, 0, full, default_dynamics),
    ])
    protected = EpisodeLog([
        Transition(0, full, 0, two, default_dynamics),
        Transition(1, two, 0, one, default_dynamics),
        Transition(2, empty, 0, full, attested_dynamics),
    ])

    assert env_frame_indices(inferred) == {2}
    assert env_frame_indices(protected) == set()


def test_arc_adapter_authors_epoch_boundary_from_environment_signal(monkeypatch) -> None:
    class FakeEnv:
        action_space = ("ACTION1",)

        def __init__(self):
            self.action_calls = 0

        def step(self, action):
            if action == "RESET":
                return SimpleNamespace(
                    frame=[[[0, 0], [0, 0]]],
                    state=SimpleNamespace(name="PLAY"),
                    levels_completed=0,
                )
            self.action_calls += 1
            return SimpleNamespace(
                frame=[[[self.action_calls, 0], [0, 0]]],
                state=SimpleNamespace(name="PLAY"),
                levels_completed=1,
            )

    fake_env = FakeEnv()
    fake_arcade = SimpleNamespace(make=lambda _game_id: fake_env)
    monkeypatch.setitem(
        sys.modules,
        "arc_agi",
        SimpleNamespace(Arcade=lambda: fake_arcade),
    )
    monkeypatch.setitem(
        sys.modules,
        "arcengine",
        SimpleNamespace(GameAction=SimpleNamespace(RESET="RESET")),
    )

    from ztare.substrates.arc_agi3 import ArcAgi3Adapter

    adapter = ArcAgi3Adapter("ls20-test", arcade=fake_arcade)
    _ = adapter.state
    adapter.step(0)
    identity = adapter.last_transition_identity
    assert identity is not None
    assert identity.kind == "epoch_boundary"
    assert identity.boundary_kind == "level_completed"
    assert identity.source_epoch == 0
    assert identity.target_epoch == 1


def test_goal_edge_exemplars_are_scoped_to_source_epoch() -> None:
    from ztare.worldmodel.goal_abduction import authoritative_goal_edge_predicate

    first = _grid([[1]])
    second = _grid([[2]])
    log = EpisodeLog([
        Transition(
            3,
            first,
            0,
            second,
            TransitionIdentity(
                kind="epoch_boundary",
                authority="environment_adapter",
                source_epoch=0,
                target_epoch=1,
                boundary_kind="level_completed",
                evidence_refs=("epoch-0-edge",),
            ),
        ),
        Transition(
            8,
            second,
            1,
            first,
            TransitionIdentity(
                kind="epoch_boundary",
                authority="environment_adapter",
                source_epoch=1,
                target_epoch=2,
                boundary_kind="level_completed",
                evidence_refs=("epoch-1-edge",),
            ),
        ),
    ])

    epoch_one, count = authoritative_goal_edge_predicate(log, source_epoch=1)
    assert count == 1
    assert epoch_one is not None
    assert epoch_one(second, 1, 8)
    assert not epoch_one(first, 0, 3)
    unknown, count = authoritative_goal_edge_predicate(log, source_epoch=2)
    assert unknown is None
    assert count == 0


def test_arc_adapter_marks_terminal_animation_as_epoch_boundary(monkeypatch) -> None:
    class FakeEnv:
        action_space = ("ACTION1",)

        def step(self, action):
            if action == "RESET":
                return SimpleNamespace(
                    frame=[[[8, 8], [8, 8]]],
                    state=SimpleNamespace(name="PLAY"),
                    levels_completed=0,
                )
            return SimpleNamespace(
                frame=[[[3, 3], [3, 3]]],
                state=SimpleNamespace(name="GAME_OVER"),
                levels_completed=0,
            )

    fake_env = FakeEnv()
    fake_arcade = SimpleNamespace(make=lambda _game_id: fake_env)
    monkeypatch.setitem(
        sys.modules,
        "arc_agi",
        SimpleNamespace(Arcade=lambda: fake_arcade),
    )
    monkeypatch.setitem(
        sys.modules,
        "arcengine",
        SimpleNamespace(GameAction=SimpleNamespace(RESET="RESET")),
    )

    from ztare.substrates.arc_agi3 import ArcAgi3Adapter

    adapter = ArcAgi3Adapter("ls20-test", arcade=fake_arcade)
    _ = adapter.state
    before = adapter.state
    after = adapter.step(0)
    identity = adapter.last_transition_identity
    assert before != after
    assert identity is not None
    assert identity.kind == "epoch_boundary"
    assert identity.boundary_kind == "terminal_state:GAME_OVER"

    log = EpisodeLog()
    log.append(before, 0, after, t=0, identity=identity)
    assert env_frame_indices(log) == {0}


def test_arc_task_discharge_is_a_run_entry_epoch_morphism() -> None:
    from ztare.common.task_discharge import TaskDischargeContract
    from ztare.substrates.arc_agi3 import ArcAgi3Adapter

    adapter = object.__new__(ArcAgi3Adapter)
    adapter.levels_completed = 7
    adapter._last_transition_identity = None
    adapter._task_discharge_baselines = {}
    contract = TaskDischargeContract(
        contract_id="next-epoch.v1",
        adjudicator_id="arc.level_count.v1",
        lifecycle_scope="current_play_run",
        owner="test_profile",
        parameters={"comparison": "increase_from_run_entry", "target_delta": 1},
    )

    entry = adapter.adjudicate_task_discharge(contract)
    assert entry.status == "open"
    assert entry.observed["run_entry_levels_completed"] == 7
    adapter.levels_completed = 8
    adapter._last_transition_identity = TransitionIdentity(
        kind="epoch_boundary",
        authority="environment_adapter",
        source_epoch=7,
        target_epoch=8,
        boundary_kind="level_completed",
        evidence_refs=("adapter:event:7->8",),
    )
    successor = adapter.adjudicate_task_discharge(contract)
    assert successor.status == "discharged"
    assert successor.observed["delta_from_run_entry"] == 1
    assert successor.evidence_refs == ("adapter:event:7->8",)


def test_pursuit_receipt_carries_identity_into_episode_log(monkeypatch) -> None:
    from ztare.worldmodel import planner

    start = _grid([[0]])
    finish = _grid([[1]])
    identity = TransitionIdentity(
        kind="epoch_boundary",
        authority="environment_adapter",
        source_epoch=0,
        target_epoch=1,
        boundary_kind="level_completed",
    )

    class Adapter:
        action_arity = 1
        levels_completed = 0
        t = 0
        state = start
        last_transition_identity = None

        def step(self, action):
            assert action == 0
            self.t += 1
            self.levels_completed = 1
            self.last_transition_identity = identity
            return finish

    monkeypatch.setattr(
        planner,
        "plan_novelty",
        lambda *_args, **_kwargs: planner.Plan([0], "test"),
    )
    receipt = planner.pursue_goal(
        Adapter(),
        lambda _state, _action, _t: finish,
        max_steps=1,
        max_replans=1,
    )

    assert receipt.status == "goal_reached"
    assert receipt.divergence is None
    assert len(receipt.observed_transitions) == 1
    transition = receipt.observed_transitions[0]
    assert transition.identity == identity
    log = EpisodeLog()
    log.append_transition(transition)
    assert env_frame_indices(log) == {0}


def test_prediction_memo_does_not_infer_period_from_visible_samples(monkeypatch) -> None:
    from ztare.worldmodel import planner

    state = _grid([[0]])

    class Adapter:
        def __init__(self):
            self.action_arity = 1
            self.levels_completed = 0
            self.t = 0
            self.state = state
            self.last_transition_identity = TransitionIdentity(
                kind="dynamics",
                authority="environment_adapter",
                source_epoch=0,
                target_epoch=0,
            )

        def step(self, action):
            assert action == 0
            self.t += 1
            return state

    predicted_times: list[int] = []

    def carrier(_state, _action, t):
        predicted_times.append(t)
        return state

    monkeypatch.setattr(
        planner,
        "plan_novelty",
        lambda *_args, **_kwargs: planner.Plan([0, 0, 0, 0, 0], "test"),
    )
    receipt = planner.pursue_goal(
        Adapter(),
        carrier,
        max_steps=5,
        max_replans=1,
    )

    assert receipt.steps_executed == 5
    assert predicted_times == [0, 1, 2, 3, 4]
