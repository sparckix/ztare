"""Exact-state wrapper for a Responses API reasoning continuation.

This module owns model-thread identity only.  Environment semantics, action
costs, and tool execution stay with callers.  A stored response chain is
required because ``previous_response_id`` is the authority that makes prior
reasoning items available on the next turn.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Iterable, Mapping


class ResponsesContinuationError(RuntimeError):
    """The provider response did not satisfy the continuation contract."""


@dataclass(frozen=True)
class ResponsesToolDecision:
    response_id: str
    previous_response_id: str | None
    call_id: str
    tool_name: str
    arguments: Mapping[str, Any]
    requested_reasoning_context: str
    effective_reasoning_context: str
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int

    def to_receipt(self) -> dict[str, Any]:
        return {
            "schema": "ztare-responses-tool-decision-v1",
            "response_id": self.response_id,
            "previous_response_id": self.previous_response_id,
            "call_id": self.call_id,
            "tool_name": self.tool_name,
            "arguments": dict(self.arguments),
            "requested_reasoning_context": self.requested_reasoning_context,
            "effective_reasoning_context": self.effective_reasoning_context,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_input_tokens": self.cached_input_tokens,
        }


@dataclass(frozen=True)
class ResponsesForkAuthority:
    """Exact shared-parent authority for counterfactual continuations."""

    parent_response_id: str
    child_response_ids: tuple[str, ...]
    child_previous_response_ids: tuple[str, ...]
    reasoning_context: str

    def __post_init__(self) -> None:
        if not self.parent_response_id:
            raise ValueError("fork parent response id is required")
        if len(self.child_response_ids) < 2:
            raise ValueError("counterfactual fork requires two children")
        if len(self.child_response_ids) != len(
            self.child_previous_response_ids
        ):
            raise ValueError("fork child identity counts differ")
        if len(set(self.child_response_ids)) != len(
            self.child_response_ids
        ):
            raise ValueError("fork children must have distinct identities")
        if any(
            value != self.parent_response_id
            for value in self.child_previous_response_ids
        ):
            raise ValueError("fork children do not share the exact parent")
        if self.reasoning_context != "all_turns":
            raise ValueError(
                "counterfactual fork requires all_turns reasoning context"
            )

    def to_receipt(self) -> dict[str, Any]:
        return {
            "schema": "ztare-responses-counterfactual-fork-v1",
            "parent_response_id": self.parent_response_id,
            "child_response_ids": list(self.child_response_ids),
            "child_previous_response_ids": list(
                self.child_previous_response_ids
            ),
            "child_count": len(self.child_response_ids),
            "reasoning_context": self.reasoning_context,
            "shared_parent": True,
        }


def _field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _response_payload(response: Any) -> Mapping[str, Any]:
    if isinstance(response, Mapping):
        return response
    dump = getattr(response, "model_dump", None)
    if callable(dump):
        payload = dump()
        if isinstance(payload, Mapping):
            return payload
    return {}


def _reasoning_context(response: Any) -> str:
    reasoning = _field(response, "reasoning")
    direct = _field(reasoning, "context")
    if direct:
        return str(direct)
    payload_reasoning = _response_payload(response).get("reasoning")
    if isinstance(payload_reasoning, Mapping) and payload_reasoning.get("context"):
        return str(payload_reasoning["context"])
    return ""


def _usage(response: Any) -> tuple[int, int, int]:
    usage = _field(response, "usage")
    input_tokens = int(_field(usage, "input_tokens", 0) or 0)
    output_tokens = int(_field(usage, "output_tokens", 0) or 0)
    details = _field(usage, "input_tokens_details")
    cached = int(_field(details, "cached_tokens", 0) or 0)
    return input_tokens, output_tokens, cached


class PersistentResponsesToolThread:
    """One model-owned reasoning thread constrained to one named action tool."""

    def __init__(
        self,
        client: Any,
        *,
        model_id: str,
        instructions: str,
        tool: Mapping[str, Any],
        reasoning_effort: str = "xhigh",
        reasoning_context: str = "all_turns",
        max_output_tokens: int = 4096,
        timeout_seconds: float = 300,
    ) -> None:
        if reasoning_context not in {"all_turns", "current_turn"}:
            raise ValueError(
                "reasoning_context must be all_turns or current_turn"
            )
        if not model_id:
            raise ValueError("model_id is required")
        if not instructions.strip():
            raise ValueError("instructions are required")
        if tool.get("type") != "function" or not tool.get("name"):
            raise ValueError("tool must be one Responses function definition")
        self._client = client
        self.model_id = model_id
        self.instructions = instructions
        self.tool = dict(tool)
        self.tool_name = str(tool["name"])
        self.reasoning_effort = reasoning_effort
        self.reasoning_context = reasoning_context
        self.max_output_tokens = int(max_output_tokens)
        self.timeout_seconds = float(timeout_seconds)
        self.previous_response_id: str | None = None

    def fork_from_current(self) -> "PersistentResponsesToolThread":
        """Create an independent continuation from the exact stored parent."""

        if not self.previous_response_id:
            raise ResponsesContinuationError(
                "cannot fork before a stored parent response exists"
            )
        child = PersistentResponsesToolThread(
            self._client,
            model_id=self.model_id,
            instructions=self.instructions,
            tool=self.tool,
            reasoning_effort=self.reasoning_effort,
            reasoning_context=self.reasoning_context,
            max_output_tokens=self.max_output_tokens,
            timeout_seconds=self.timeout_seconds,
        )
        child.previous_response_id = self.previous_response_id
        return child

    def decide(self, input_items: Iterable[Mapping[str, Any]]) -> ResponsesToolDecision:
        prior = self.previous_response_id
        request: dict[str, Any] = {
            "model": self.model_id,
            "instructions": self.instructions,
            "input": list(input_items),
            "tools": [self.tool],
            "tool_choice": {
                "type": "function",
                "name": self.tool_name,
            },
            "parallel_tool_calls": False,
            "reasoning": {
                "effort": self.reasoning_effort,
                "context": self.reasoning_context,
            },
            "store": True,
            "max_output_tokens": self.max_output_tokens,
            "timeout": self.timeout_seconds,
        }
        if prior is not None:
            request["previous_response_id"] = prior
        response = self._client.responses.create(**request)
        response_id = str(_field(response, "id", "") or "")
        if not response_id:
            raise ResponsesContinuationError("response omitted its identity")

        effective_context = _reasoning_context(response)
        if not effective_context:
            raise ResponsesContinuationError(
                "response omitted effective reasoning.context"
            )
        if effective_context != self.reasoning_context:
            raise ResponsesContinuationError(
                "reasoning context drifted: "
                f"requested {self.reasoning_context}, got {effective_context}"
            )

        calls = [
            item
            for item in (_field(response, "output", ()) or ())
            if _field(item, "type") == "function_call"
        ]
        if len(calls) != 1:
            raise ResponsesContinuationError(
                f"expected exactly one function call, got {len(calls)}"
            )
        call = calls[0]
        name = str(_field(call, "name", "") or "")
        if name != self.tool_name:
            raise ResponsesContinuationError(
                f"unexpected function call {name!r}"
            )
        call_id = str(_field(call, "call_id", "") or "")
        if not call_id:
            raise ResponsesContinuationError("function call omitted call_id")
        raw_arguments = _field(call, "arguments", "{}")
        try:
            arguments = (
                dict(raw_arguments)
                if isinstance(raw_arguments, Mapping)
                else json.loads(str(raw_arguments))
            )
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ResponsesContinuationError(
                "function call arguments were not JSON"
            ) from exc
        if not isinstance(arguments, dict):
            raise ResponsesContinuationError(
                "function call arguments must be an object"
            )

        input_tokens, output_tokens, cached = _usage(response)
        self.previous_response_id = response_id
        return ResponsesToolDecision(
            response_id=response_id,
            previous_response_id=prior,
            call_id=call_id,
            tool_name=name,
            arguments=arguments,
            requested_reasoning_context=self.reasoning_context,
            effective_reasoning_context=effective_context,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached,
        )


def compile_responses_fork_authority(
    parent: ResponsesToolDecision,
    children: Iterable[ResponsesToolDecision],
) -> ResponsesForkAuthority:
    rows = tuple(children)
    if len(rows) < 2:
        raise ValueError("counterfactual fork requires two child decisions")
    contexts = {
        row.effective_reasoning_context for row in rows
    }
    if contexts != {"all_turns"}:
        raise ValueError("fork children drifted from all_turns")
    return ResponsesForkAuthority(
        parent_response_id=parent.response_id,
        child_response_ids=tuple(row.response_id for row in rows),
        child_previous_response_ids=tuple(
            str(row.previous_response_id or "") for row in rows
        ),
        reasoning_context="all_turns",
    )


__all__ = [
    "PersistentResponsesToolThread",
    "ResponsesContinuationError",
    "ResponsesForkAuthority",
    "ResponsesToolDecision",
    "compile_responses_fork_authority",
]
