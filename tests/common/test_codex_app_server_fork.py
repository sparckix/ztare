from __future__ import annotations

import pytest

from ztare.common.codex_app_server_fork import (
    AppServerForkReceipt,
    AppServerProtocolError,
    AppServerTurnReceipt,
    fork_receipt_from_response,
    turn_receipt_from_completion,
)
from ztare.common.persistent_reasoning_controller import (
    PersistentAppServerToolThread,
    app_server_inputs_from_responses_items,
)


def _completion(*, thread_id: str = "thread-parent", tool: bool = False):
    items = [
        {"id": "user", "type": "userMessage", "content": []},
        {"id": "reasoning", "type": "reasoning", "summary": []},
        {"id": "answer", "type": "agentMessage", "text": '{"choice": 2}'},
    ]
    if tool:
        items.insert(2, {
            "id": "command",
            "type": "commandExecution",
            "command": "pwd",
        })
    return {
        "threadId": thread_id,
        "turn": {
            "id": "turn-parent",
            "status": "completed",
            "items": items,
            "startedAt": 10,
            "completedAt": 12,
            "durationMs": 2000,
        },
    }


def test_completed_turn_binds_prompt_output_and_zero_tool_count() -> None:
    receipt = turn_receipt_from_completion(
        thread_id="thread-parent",
        prompt="opaque parent prompt",
        completion_params=_completion(),
    )

    assert receipt.turn_id == "turn-parent"
    assert receipt.status == "completed"
    assert receipt.assistant_text == '{"choice": 2}'
    assert receipt.tool_item_count == 0
    assert receipt.to_receipt()["assistant_output_sha256"]


def test_tool_item_is_visible_in_turn_receipt() -> None:
    receipt = turn_receipt_from_completion(
        thread_id="thread-parent",
        prompt="prompt",
        completion_params=_completion(tool=True),
    )
    assert receipt.tool_item_count == 1


def test_turn_completion_cannot_cross_thread_identity() -> None:
    with pytest.raises(AppServerProtocolError, match="crossed thread"):
        turn_receipt_from_completion(
            thread_id="expected",
            prompt="prompt",
            completion_params=_completion(thread_id="other"),
        )


def test_fork_receipt_requires_distinct_thread_and_exact_last_turn() -> None:
    receipt = fork_receipt_from_response(
        source_thread_id="thread-parent",
        last_turn_id="turn-parent",
        response={
            "thread": {
                "id": "thread-child",
                "forkedFromId": "thread-parent",
                "ephemeral": False,
                "turns": [
                    {"id": "turn-setup"},
                    {"id": "turn-parent"},
                ],
            }
        },
    )

    assert receipt.fork_thread_id == "thread-child"
    assert receipt.forked_from_id == "thread-parent"
    assert receipt.inherited_turn_ids == ("turn-setup", "turn-parent")


def test_fork_receipt_rejects_wrong_parent_or_boundary() -> None:
    with pytest.raises(ValueError, match="forkedFromId"):
        fork_receipt_from_response(
            source_thread_id="thread-parent",
            last_turn_id="turn-parent",
            response={
                "thread": {
                    "id": "thread-child",
                    "forkedFromId": "other-parent",
                    "turns": [{"id": "turn-parent"}],
                }
            },
        )
    with pytest.raises(ValueError, match="requested last turn"):
        fork_receipt_from_response(
            source_thread_id="thread-parent",
            last_turn_id="turn-parent",
            response={
                "thread": {
                    "id": "thread-child",
                    "forkedFromId": "thread-parent",
                    "turns": [{"id": "turn-earlier"}],
                }
            },
        )


def test_responses_input_lowering_preserves_protocol_event_and_image() -> None:
    lowered = app_server_inputs_from_responses_items([
        {
            "type": "function_call_output",
            "call_id": "call-parent",
            "output": [{
                "type": "input_image",
                "image_url": "data:image/png;base64,opaque",
            }],
        },
        {
            "role": "user",
            "content": [{"type": "input_text", "text": "revision"}],
        },
    ])

    assert lowered[0]["type"] == "text"
    assert '"event":"function_call_output"' in lowered[0]["text"]
    assert lowered[1] == {
        "type": "image",
        "url": "data:image/png;base64,opaque",
    }
    assert lowered[2] == {"type": "text", "text": "revision"}


class _FakeAppServerClient:
    def __init__(self) -> None:
        self.outputs = iter((
            '{"choice":1}',
            '{"choice":2}',
            '{"choice":3}',
        ))
        self.thread_count = 0
        self.turn_count = 0
        self.fork_count = 0
        self.resumes: list[tuple[str, str]] = []

    def start_thread(self, **_kwargs):
        self.thread_count += 1
        return {"thread": {"id": f"thread-{self.thread_count}"}}

    def run_turn(self, *, thread_id, prompt, **_kwargs):
        self.turn_count += 1
        return AppServerTurnReceipt(
            thread_id=thread_id,
            turn_id=f"turn-{self.turn_count}",
            prompt_sha256="a" * 64,
            assistant_text=next(self.outputs),
            status="completed",
            item_types=("agentMessage",),
            tool_item_count=0,
            started_at=1,
            completed_at=2,
            duration_ms=1000,
            input_tokens=11,
            output_tokens=7,
            cached_input_tokens=3,
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

    def resume_thread(self, thread_id, *, model, cwd):
        self.resumes.append((thread_id, str(cwd)))
        return {"thread": {"id": thread_id}}


def _app_thread(client, tmp_path):
    return PersistentAppServerToolThread(
        client,
        model_id="gpt-5.6-sol",
        instructions="sealed controller",
        tool={
            "type": "function",
            "name": "commit",
            "parameters": {
                "type": "object",
                "properties": {"choice": {"type": "integer"}},
                "required": ["choice"],
                "additionalProperties": False,
            },
        },
        cwd=tmp_path,
    )


def test_app_server_thread_forks_exact_turn_and_resumes(tmp_path) -> None:
    client = _FakeAppServerClient()
    parent = _app_thread(client, tmp_path)
    parent_decision = parent.decide([
        {"role": "user", "content": [
            {"type": "input_text", "text": "parent"},
        ]},
    ])
    child_a = parent.fork_from_current()
    child_b = parent.fork_from_current()
    decision_a = child_a.decide([
        {"role": "user", "content": [
            {"type": "input_text", "text": "a"},
        ]},
    ])
    decision_b = child_b.decide([
        {"role": "user", "content": [
            {"type": "input_text", "text": "b"},
        ]},
    ])

    assert decision_a.previous_response_id == parent_decision.response_id
    assert decision_b.previous_response_id == parent_decision.response_id
    assert child_a.thread_id != child_b.thread_id
    assert child_a.transport_receipt()["fork"]["last_turn_id"] == (
        parent_decision.response_id
    )
    resumed = _app_thread(client, tmp_path).resume_from(
        thread_id=child_a.thread_id,
        last_turn_id=decision_a.response_id,
    )
    assert resumed.thread_id == child_a.thread_id
    assert resumed.previous_response_id == decision_a.response_id
    assert decision_a.input_tokens == 11
