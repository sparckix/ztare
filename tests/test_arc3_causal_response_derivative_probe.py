from __future__ import annotations

import argparse
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from ztare.common.codex_app_server_fork import (
    AppServerForkReceipt,
    AppServerTurnReceipt,
)


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "scripts/public/control/arc3_causal_response_derivative_probe.py"
)
SPEC = importlib.util.spec_from_file_location(
    "arc3_causal_response_derivative_probe_under_test",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


def _response(response_id: str, call_id: str, arguments: dict):
    return {
        "id": response_id,
        "reasoning": {"context": "all_turns"},
        "output": [{
            "type": "function_call",
            "name": "commit_arc_plan",
            "call_id": call_id,
            "arguments": json.dumps(arguments),
        }],
        "usage": {
            "input_tokens": 11,
            "output_tokens": 7,
            "input_tokens_details": {"cached_tokens": 3},
        },
    }


class _Responses:
    def __init__(self, rows):
        self.rows = list(rows)
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return self.rows.pop(0)


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _current_handle(request: dict) -> str:
    for row in _walk(request["input"]):
        if row.get("type") != "input_text":
            continue
        try:
            payload = json.loads(str(row["text"]))
            presentation = payload[
                "catalog_scoped_object_presentation"
            ]
        except (KeyError, TypeError, ValueError):
            continue
        objects = presentation.get("objects") or ()
        bindings = presentation.get("handle_bindings") or ()
        candidates = objects or bindings
        if candidates:
            return str(candidates[0]["handle"])
    raise AssertionError("request omitted the current object catalog")


class _AdaptiveResponses:
    def __init__(self, scripted: list[dict]):
        self.scripted = list(scripted)
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        index = len(self.requests)
        arguments = (
            self.scripted.pop(0)
            if self.scripted
            else _decision(
                controlled=_current_handle(kwargs),
                waypoints=[],
                action=2,
            )
        )
        return _response(
            f"resp-{index:03d}",
            f"call-{index:03d}",
            arguments,
        )


class _FrozenReplayAdapter:
    def __init__(self, observations: list[tuple[tuple[int, ...], ...]]):
        self._observations = observations
        self._prefix_index = 0
        self.action_arity = 4
        self.levels_completed = 0
        self.current_epoch = 0
        self.last_transition_identity = None

    def reset(self):
        self._prefix_index = 0
        return self._observations[0]

    def step(self, _action: int):
        self._prefix_index = min(
            self._prefix_index + 1,
            len(self._observations) - 1,
        )
        return self._observations[self._prefix_index]


def _frozen_replay_adapter_factory():
    h96_path = (
        ROOT
        / "research_areas/pre_registrations"
        / "arc3_consumer_indexed_exception_frontier_20260723"
        / "h96_causal_object_lineage/manifest.json"
    )
    h96 = json.loads(h96_path.read_text(encoding="utf-8"))
    observations = [
        probe.decode_grid_rle_rows(tuple(row["grid_rle_rows"]))
        for row in h96["descendant_prefix"]["observations"]
    ]
    return lambda _game: _FrozenReplayAdapter(observations)


def _args(output_dir: Path) -> argparse.Namespace:
    base = (
        ROOT
        / "research_areas/pre_registrations"
        / "arc3_consumer_indexed_exception_frontier_20260723"
    )
    return argparse.Namespace(
        spec=str(base / "h97_causal_response_derivative_spec.json"),
        output_dir=str(output_dir),
        max_output_tokens=4096,
        timeout_seconds=300.0,
    )


class _FakeH97AppServer:
    def __init__(self, decisions: list[dict]) -> None:
        self.decisions = list(decisions)
        self.thread_count = 0
        self.turn_count = 0
        self.fork_count = 0
        self.resumed: list[str] = []

    def start_thread(self, **_kwargs):
        self.thread_count += 1
        return {"thread": {"id": f"thread-{self.thread_count}"}}

    def run_turn(self, *, thread_id, **_kwargs):
        self.turn_count += 1
        return AppServerTurnReceipt(
            thread_id=thread_id,
            turn_id=f"turn-{self.turn_count}",
            prompt_sha256="b" * 64,
            assistant_text=json.dumps(self.decisions.pop(0)),
            status="completed",
            item_types=("agentMessage",),
            tool_item_count=0,
            started_at=1,
            completed_at=2,
            duration_ms=1000,
            input_tokens=13,
            output_tokens=8,
            cached_input_tokens=2,
        )

    def fork_thread(self, *, source_thread_id, last_turn_id, **_kwargs):
        self.fork_count += 1
        return AppServerForkReceipt(
            source_thread_id=source_thread_id,
            last_turn_id=last_turn_id,
            fork_thread_id=f"fork-{self.fork_count}",
            forked_from_id=source_thread_id,
            inherited_turn_ids=(last_turn_id,),
            ephemeral=False,
        )

    def resume_thread(self, thread_id, **_kwargs):
        self.resumed.append(thread_id)
        return {"thread": {"id": thread_id}}


def _decision(
    *,
    controlled: str,
    waypoints: list[str],
    action: int,
) -> dict:
    return {
        "action": action,
        "prediction": "visible state changes",
        "plan_summary": "test the current object path",
        "uncertainty": "mechanism remains uncertain",
        "controlled_object_handle": controlled,
        "ordered_waypoint_handles": waypoints,
    }


def test_h97_exact_fork_is_offline_resumable_before_environment(
    tmp_path: Path,
) -> None:
    args = _args(tmp_path / "h97")
    context = probe._compile_live_context(args)
    responses = _Responses([
        _response(
            "resp-parent",
            "call-parent",
            _decision(controlled="o02", waypoints=[], action=2),
        ),
        _response(
            "resp-offer",
            "call-offer",
            _decision(controlled="o03", waypoints=["o00"], action=1),
        ),
        _response(
            "resp-withhold",
            "call-withhold",
            _decision(controlled="o02", waypoints=[], action=2),
        ),
    ])
    client = SimpleNamespace(responses=responses)

    pair = probe._prepare_pair(
        client=client,
        context=context,
        args=args,
        pair_index=1,
        order=("offer", "withhold"),
    )

    assert pair is not None
    assert len(responses.requests) == 3
    assert "previous_response_id" not in responses.requests[0]
    assert responses.requests[1]["previous_response_id"] == "resp-parent"
    assert responses.requests[2]["previous_response_id"] == "resp-parent"
    assert pair["setup"]["fork_authority"]["shared_parent"] is True
    assert (
        pair["branches"]["offer"]["transition"].relation
        == "offered_supported_derivative"
    )
    assert pair["branches"]["offer"]["transition"].supported_transport
    assert not pair["branches"]["withhold"]["transition"].supported_transport
    assert pair["setup"]["environment_contact"] is False
    assert (
        pair["setup"]["admission"]["environment_contact_before_admission"]
        is False
    )
    assert (
        pair["setup"]["branches"]["offer"]["presented_utf8_bytes"]
        == 3849
    )
    assert (
        pair["setup"]["branches"]["withhold"]["presented_utf8_bytes"]
        == 3849
    )

    resumed_responses = _Responses([])
    resumed = probe._prepare_pair(
        client=SimpleNamespace(responses=resumed_responses),
        context=context,
        args=args,
        pair_index=1,
        order=("offer", "withhold"),
    )
    assert resumed is not None
    assert resumed_responses.requests == []
    assert resumed["setup"] == pair["setup"]


def test_h97_app_server_manifest_and_exact_thread_fork_are_distinct(
    tmp_path: Path,
) -> None:
    args = _args(tmp_path / "h97_app")
    args.controller_transport = probe.CODEX_APP_SERVER_TRANSPORT
    args.app_server_cwd = str(tmp_path / "sealed_cwd")
    client = _FakeH97AppServer([
        _decision(controlled="o02", waypoints=[], action=2),
        _decision(controlled="o03", waypoints=["o00"], action=1),
        _decision(controlled="o02", waypoints=[], action=2),
    ])
    context = probe._compile_live_context(args)
    pair = probe._prepare_pair(
        client=client,
        context=context,
        args=args,
        pair_index=1,
        order=("offer", "withhold"),
    )

    assert pair is not None
    assert context["manifest"]["controller_transport"] == (
        probe.CODEX_APP_SERVER_TRANSPORT
    )
    assert context["manifest"]["live_controller_scope_transport"][
        "controller_identity"
    ]["kind"] == "persistent_codex_app_server_reasoner"
    authority = pair["setup"]["fork_authority"]
    assert authority["shared_parent"] is True
    assert authority["parent_thread_id"] == "thread-1"
    assert {row["fork_thread_id"] for row in authority["branches"]} == {
        "fork-1",
        "fork-2",
    }
    assert pair["setup"]["environment_contact"] is False


def test_h109_exact_prefix_chronology_changes_only_controller_scope(
    tmp_path: Path,
) -> None:
    endpoint_args = _args(tmp_path / "h97_endpoint")
    endpoint_args.controller_transport = probe.CODEX_APP_SERVER_TRANSPORT
    endpoint_args.app_server_cwd = str(tmp_path / "endpoint_cwd")
    endpoint = probe._compile_live_context(endpoint_args)

    chronology_args = _args(tmp_path / "h109_chronology")
    chronology_args.controller_transport = probe.CODEX_APP_SERVER_TRANSPORT
    chronology_args.app_server_cwd = str(tmp_path / "chronology_cwd")
    chronology_args.initial_history_mode = probe.EXACT_PREFIX_CHRONOLOGY
    chronology = probe._compile_live_context(chronology_args)

    assert "initial_history_authority" not in endpoint["manifest"]
    history = chronology["initial_history_authority"]
    assert history["mode"] == probe.EXACT_PREFIX_CHRONOLOGY
    assert history["source_prefix_sha256"] == (
        chronology["prefix"]["sha256"]
    )
    carrier = history["chronology_carrier"]
    assert carrier["action_count"] == 7
    assert carrier["observation_count"] == 8
    assert carrier["transition_count"] == 7
    assert carrier["actions"] == [2, 2, 2, 0, 0, 0, 1]

    endpoint_scope = endpoint["scope"].to_receipt()
    chronology_scope = chronology["scope"].to_receipt()
    for coordinate in (
        "task_sha256",
        "context_sha256",
        "choice_set_sha256",
        "action_vocabulary_sha256",
    ):
        assert chronology_scope[coordinate] == endpoint_scope[coordinate]
    assert (
        chronology_scope["controller_sha256"]
        != endpoint_scope["controller_sha256"]
    )
    controller_identity = chronology["manifest"][
        "live_controller_scope_transport"
    ]["controller_identity"]
    assert controller_identity["initial_history_mode"] == (
        probe.EXACT_PREFIX_CHRONOLOGY
    )
    assert controller_identity[
        "initial_history_authority_sha256"
    ] == history["sha256"]

    initial_input = probe._initial_parent_input(
        chronology["grid"],
        levels_completed=int(
            chronology["observation"]["levels_completed"]
        ),
        action_arity=int(chronology["prefix"]["action_arity"]),
        presentation=chronology["presentation"],
        prefix_action_count=len(chronology["prefix"]["actions"]),
        prefix=chronology["prefix"],
        initial_history_mode=probe.EXACT_PREFIX_CHRONOLOGY,
        chronology_carrier=carrier,
    )
    assert probe._sha({"input": initial_input}) == (
        history["rendered_parent_input_sha256"]
    )
    content = initial_input[0]["content"]
    assert sum(row["type"] == "input_image" for row in content) == 9
    decoded = [
        json.loads(row["text"])
        for row in content
        if row["type"] == "input_text"
    ]
    chronology_rows = [
        row
        for row in decoded
        if row.get("phase") == "restored_prefix_observation"
    ]
    assert len(chronology_rows) == 8
    assert [
        row["settled_observation"]["sha256"]
        for row in chronology_rows
    ] == carrier["observation_sha256s"]
    assert [
        row["following_action"]
        for row in chronology_rows[:-1]
    ] == carrier["actions"]
    assert chronology_rows[-1]["current_endpoint"] is True


def test_h109_prefix_chronology_refuses_tampered_links_and_content(
    tmp_path: Path,
) -> None:
    args = _args(tmp_path / "h109_source")
    source = probe._compile_live_context(args)["prefix"]
    assert probe._compile_prefix_chronology_carrier(source)[
        "source_prefix_sha256"
    ] == source["sha256"]

    wrong_action = deepcopy(source)
    wrong_action["transitions"][0]["action"] = 1
    with pytest.raises(ValueError, match="transition link"):
        probe._compile_prefix_chronology_carrier(wrong_action)

    wrong_observation = deepcopy(source)
    wrong_observation["observations"][0]["grid_rle_rows"][0] = "4x64"
    with pytest.raises(ValueError, match="observation content hash"):
        probe._compile_prefix_chronology_carrier(wrong_observation)

    wrong_endpoint = deepcopy(source)
    wrong_endpoint["final_observation"] = dict(
        wrong_endpoint["observations"][-2]
    )
    with pytest.raises(ValueError, match="final observation"):
        probe._compile_prefix_chronology_carrier(wrong_endpoint)


def test_h97_first_stage_failure_stops_before_environment(
    tmp_path: Path,
) -> None:
    args = _args(tmp_path / "h97")
    responses = _Responses([
        _response(
            "resp-parent",
            "call-parent",
            _decision(controlled="o02", waypoints=[], action=2),
        ),
        _response(
            "resp-offer",
            "call-offer",
            _decision(controlled="o02", waypoints=[], action=2),
        ),
        _response(
            "resp-withhold",
            "call-withhold",
            _decision(controlled="o02", waypoints=[], action=2),
        ),
    ])

    result = probe.run_live(
        args,
        client=SimpleNamespace(responses=responses),
        adapter_factory=_frozen_replay_adapter_factory(),
    )

    assert result["verdict"] == "rejected"
    assert result["environment_contact"] is False
    assert result["failed_pair_index"] == 1
    assert result["failed_checks"] == [
        "pair_01:offer_supported_derivative"
    ]
    assert len(responses.requests) == 3
    assert not (Path(args.output_dir) / "arms").exists()
    assert not (Path(args.output_dir) / "turns").exists()


def test_h97_fake_full_live_reaches_external_settlement(
    tmp_path: Path,
) -> None:
    args = _args(tmp_path / "h97")
    parent = _decision(controlled="o02", waypoints=[], action=2)
    offer = _decision(
        controlled="o03",
        waypoints=["o00"],
        action=1,
    )
    withhold = _decision(controlled="o02", waypoints=[], action=2)
    responses = _AdaptiveResponses([
        parent,
        offer,
        withhold,
        parent,
        withhold,
        offer,
    ])

    result = probe.run_live(
        args,
        client=SimpleNamespace(responses=responses),
        adapter_factory=_frozen_replay_adapter_factory(),
    )

    assert len(responses.requests) == 82
    assert result["status"] == "live_complete"
    assert result["environment_contact"] is True
    assert result["prefix_replay_action_count"] == 28
    assert result["post_prefix_action_count"] == 80
    assert result["arc_action_count"] == 108
    assert len(result["pairs"]) == 2
    assert result["checks"]["eligible_matched_pair_count"]
    assert result["checks"]["shared_parent_identity_rate"]
    assert result["checks"]["offer_supported_derivative_rate"]
    assert result["checks"]["withhold_spontaneous_derivative_rate"]
    assert result["checks"]["first_stage_derivative_delta"]
    assert result["verdict"] == "rejected"
    assert "minimum_mean_composite_delta_exclusive" in (
        result["failed_checks"]
    )
