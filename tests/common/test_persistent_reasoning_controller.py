from __future__ import annotations

from types import SimpleNamespace

import pytest

from ztare.common.persistent_reasoning_controller import (
    PersistentResponsesToolThread,
    ResponsesContinuationError,
    compile_responses_fork_authority,
    responses_tool_decision_from_receipt,
)


def _response(response_id: str, call_id: str, *, context: str = "all_turns"):
    return SimpleNamespace(
        id=response_id,
        reasoning=SimpleNamespace(context=context),
        output=[
            SimpleNamespace(
                type="function_call",
                name="act",
                call_id=call_id,
                arguments='{"action":2}',
            )
        ],
        usage=SimpleNamespace(
            input_tokens=11,
            output_tokens=7,
            input_tokens_details=SimpleNamespace(cached_tokens=3),
        ),
    )


class _Responses:
    def __init__(self, rows):
        self.rows = list(rows)
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return self.rows.pop(0)


def _thread(rows):
    responses = _Responses(rows)
    client = SimpleNamespace(responses=responses)
    thread = PersistentResponsesToolThread(
        client,
        model_id="gpt-5.6-sol",
        instructions="choose one action",
        tool={
            "type": "function",
            "name": "act",
            "parameters": {
                "type": "object",
                "properties": {"action": {"type": "integer"}},
                "required": ["action"],
                "additionalProperties": False,
            },
            "strict": True,
        },
        reasoning_effort="xhigh",
        reasoning_context="all_turns",
    )
    return thread, responses


def test_thread_chains_previous_response_and_all_turn_reasoning() -> None:
    thread, responses = _thread([
        _response("resp-1", "call-1"),
        _response("resp-2", "call-2"),
    ])

    first = thread.decide([{"role": "user", "content": "frame 0"}])
    second = thread.decide([{
        "type": "function_call_output",
        "call_id": first.call_id,
        "output": "frame 1",
    }])

    assert "previous_response_id" not in responses.requests[0]
    assert responses.requests[1]["previous_response_id"] == "resp-1"
    assert responses.requests[0]["reasoning"] == {
        "effort": "xhigh",
        "context": "all_turns",
    }
    assert responses.requests[0]["store"] is True
    assert responses.requests[0]["parallel_tool_calls"] is False
    assert first.arguments == {"action": 2}
    assert second.previous_response_id == "resp-1"
    assert second.cached_input_tokens == 3


def test_thread_rejects_effective_context_drift() -> None:
    thread, _responses = _thread([
        _response("resp-1", "call-1", context="current_turn")
    ])

    with pytest.raises(ResponsesContinuationError, match="context drifted"):
        thread.decide([{"role": "user", "content": "frame"}])


def test_thread_rejects_response_without_exactly_one_action() -> None:
    row = _response("resp-1", "call-1")
    row.output = []
    thread, _responses = _thread([row])

    with pytest.raises(ResponsesContinuationError, match="exactly one"):
        thread.decide([{"role": "user", "content": "frame"}])


def test_thread_forks_two_children_from_exact_stored_parent() -> None:
    thread, responses = _thread([
        _response("resp-parent", "call-parent"),
        _response("resp-offer", "call-offer"),
        _response("resp-placebo", "call-placebo"),
    ])
    parent = thread.decide([{
        "role": "user",
        "content": "blind proposal",
    }])
    offer = thread.fork_from_current()
    placebo = thread.fork_from_current()

    offer_decision = offer.decide([{
        "role": "user",
        "content": "causal revision",
    }])
    placebo_decision = placebo.decide([{
        "role": "user",
        "content": "placebo revision",
    }])
    authority = compile_responses_fork_authority(
        parent,
        (offer_decision, placebo_decision),
    )

    assert responses.requests[1]["previous_response_id"] == "resp-parent"
    assert responses.requests[2]["previous_response_id"] == "resp-parent"
    assert authority.parent_response_id == "resp-parent"
    assert authority.child_response_ids == (
        "resp-offer",
        "resp-placebo",
    )
    assert authority.to_receipt()["shared_parent"] is True
    assert responses_tool_decision_from_receipt(
        parent.to_receipt()
    ) == parent
