from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from types import SimpleNamespace


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
            "arguments": __import__("json").dumps(arguments),
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
