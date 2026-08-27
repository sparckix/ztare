"""Exact-state wrapper for a Responses API reasoning continuation.

This module owns model-thread identity only.  Environment semantics, action
costs, and tool execution stay with callers.  A stored response chain is
required because ``previous_response_id`` is the authority that makes prior
reasoning items available on the next turn.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from ztare.common.codex_app_server_fork import (
    AppServerForkReceipt,
    AppServerProtocolError,
    AppServerTurnReceipt,
    CodexAppServerClient,
    stable_sha256,
)


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
        exchange_observer: (
            Callable[[Mapping[str, Any]], None] | None
        ) = None,
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
        self.exchange_observer = exchange_observer
        self.request_index = 0
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
            exchange_observer=self.exchange_observer,
        )
        child.previous_response_id = self.previous_response_id
        return child

    def set_exchange_observer(
        self,
        observer: Callable[[Mapping[str, Any]], None] | None,
    ) -> None:
        self.exchange_observer = observer

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
        self.request_index += 1
        if self.exchange_observer is not None:
            self.exchange_observer({
                "schema": "ztare-responses-exchange-v1",
                "request_index": self.request_index,
                "request": request,
                "response": dict(_response_payload(response)),
            })
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


def _protocol_event_text(payload: Mapping[str, Any]) -> str:
    return json.dumps(
        {
            "schema": "ztare-app-server-controller-input-v1",
            **dict(payload),
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _app_server_content_inputs(
    content: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    lowered: list[dict[str, Any]] = []
    for row in content:
        kind = str(row.get("type") or "")
        if kind == "input_text":
            lowered.append({"type": "text", "text": str(row.get("text") or "")})
        elif kind == "input_image":
            url = str(row.get("image_url") or "")
            if not url:
                raise ResponsesContinuationError(
                    "input_image omitted image_url"
                )
            lowered.append({"type": "image", "url": url})
        else:
            raise ResponsesContinuationError(
                f"unsupported Responses content item {kind!r}"
            )
    return lowered


def app_server_inputs_from_responses_items(
    input_items: Iterable[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    """Lower a sealed Responses input envelope to app-server user inputs.

    The app-server has no function-call item for this controller.  Tool-result
    semantics therefore travel as a canonical protocol-event text followed by
    any observation text/images carried in that result.
    """

    lowered: list[dict[str, Any]] = []
    for item in input_items:
        kind = str(item.get("type") or "")
        if kind == "function_call_output":
            call_id = str(item.get("call_id") or "")
            if not call_id:
                raise ResponsesContinuationError(
                    "function_call_output omitted call_id"
                )
            output = item.get("output")
            lowered.append({
                "type": "text",
                "text": _protocol_event_text({
                    "event": "function_call_output",
                    "call_id": call_id,
                    "output_kind": (
                        "content_items" if isinstance(output, list) else "text"
                    ),
                    "output": output if not isinstance(output, list) else None,
                }),
            })
            if isinstance(output, list):
                lowered.extend(_app_server_content_inputs(output))
            continue
        if "role" in item:
            role = str(item.get("role") or "")
            if role != "user":
                raise ResponsesContinuationError(
                    f"unsupported Responses input role {role!r}"
                )
            content = item.get("content")
            if not isinstance(content, list):
                raise ResponsesContinuationError(
                    "role input omitted content items"
                )
            lowered.extend(_app_server_content_inputs(content))
            continue
        if kind in {"input_text", "input_image"}:
            lowered.extend(_app_server_content_inputs((item,)))
            continue
        raise ResponsesContinuationError(
            f"unsupported Responses input item {kind!r}"
        )
    if not lowered:
        raise ResponsesContinuationError("controller input lowered to empty")
    return tuple(lowered)


class PersistentAppServerToolThread:
    """Stored Codex thread exposed through the H97 decision interface.

    The assistant emits one schema-constrained JSON message; no app-server
    tool item is available to the controller.  The compatibility decision
    keeps downstream proposal code transport-agnostic while the separate
    transport receipt retains thread and exact-fork authority.
    """

    def __init__(
        self,
        client: CodexAppServerClient,
        *,
        model_id: str,
        instructions: str,
        tool: Mapping[str, Any],
        cwd: Path,
        reasoning_effort: str = "xhigh",
        reasoning_context: str = "all_turns",
        max_output_tokens: int = 4096,
        timeout_seconds: float = 300,
        exchange_observer: (
            Callable[[Mapping[str, Any]], None] | None
        ) = None,
    ) -> None:
        if reasoning_context != "all_turns":
            raise ValueError("app-server fork requires all_turns context")
        if not model_id:
            raise ValueError("model_id is required")
        if not instructions.strip():
            raise ValueError("instructions are required")
        if tool.get("type") != "function" or not tool.get("name"):
            raise ValueError("tool must be one function-shaped output schema")
        parameters = tool.get("parameters")
        if not isinstance(parameters, Mapping):
            raise ValueError("tool parameters must be a JSON schema")
        self._client = client
        self.model_id = str(model_id)
        self.instructions = str(instructions)
        self.tool = dict(tool)
        self.tool_name = str(tool["name"])
        self.output_schema = dict(parameters)
        self.cwd = Path(cwd).resolve()
        self.reasoning_effort = str(reasoning_effort)
        self.reasoning_context = str(reasoning_context)
        self.max_output_tokens = int(max_output_tokens)
        self.timeout_seconds = float(timeout_seconds)
        self.exchange_observer = exchange_observer
        self.request_index = 0
        self.previous_response_id: str | None = None
        self._thread_id: str | None = None
        self.last_turn_receipt: AppServerTurnReceipt | None = None
        self.last_fork_receipt: AppServerForkReceipt | None = None

    @property
    def thread_id(self) -> str:
        if not self._thread_id:
            raise ResponsesContinuationError(
                "app-server thread has not been started or resumed"
            )
        return self._thread_id

    def _new_sibling(self) -> "PersistentAppServerToolThread":
        return PersistentAppServerToolThread(
            self._client,
            model_id=self.model_id,
            instructions=self.instructions,
            tool=self.tool,
            cwd=self.cwd,
            reasoning_effort=self.reasoning_effort,
            reasoning_context=self.reasoning_context,
            max_output_tokens=self.max_output_tokens,
            timeout_seconds=self.timeout_seconds,
            exchange_observer=self.exchange_observer,
        )

    def _ensure_started(self) -> None:
        if self._thread_id:
            return
        started = self._client.start_thread(
            model=self.model_id,
            cwd=self.cwd,
            base_instructions=self.instructions,
        )
        thread = started.get("thread")
        if not isinstance(thread, Mapping) or not thread.get("id"):
            raise AppServerProtocolError("thread/start omitted identity")
        self._thread_id = str(thread["id"])

    def resume_from(
        self,
        *,
        thread_id: str,
        last_turn_id: str,
    ) -> "PersistentAppServerToolThread":
        if self._thread_id is not None:
            raise ResponsesContinuationError(
                "cannot resume over an existing app-server thread"
            )
        result = self._client.resume_thread(
            str(thread_id),
            model=self.model_id,
            cwd=self.cwd,
        )
        thread = result.get("thread")
        if not isinstance(thread, Mapping) or str(thread.get("id") or "") != str(thread_id):
            raise AppServerProtocolError("thread/resume crossed identity")
        self._thread_id = str(thread_id)
        self.previous_response_id = str(last_turn_id)
        return self

    def fork_from_current(self) -> "PersistentAppServerToolThread":
        if not self._thread_id or not self.previous_response_id:
            raise ResponsesContinuationError(
                "cannot fork before a completed app-server turn"
            )
        fork = self._client.fork_thread(
            source_thread_id=self._thread_id,
            last_turn_id=self.previous_response_id,
            model=self.model_id,
            cwd=self.cwd,
        )
        child = self._new_sibling()
        child._thread_id = fork.fork_thread_id
        child.previous_response_id = fork.last_turn_id
        child.last_fork_receipt = fork
        return child

    def set_exchange_observer(
        self,
        observer: Callable[[Mapping[str, Any]], None] | None,
    ) -> None:
        self.exchange_observer = observer

    def transport_receipt(self) -> dict[str, Any]:
        core = {
            "schema": "ztare-app-server-controller-thread-v1",
            "thread_id": self.thread_id,
            "last_turn_id": self.previous_response_id,
            "turn": (
                self.last_turn_receipt.to_receipt()
                if self.last_turn_receipt is not None
                else None
            ),
            "fork": (
                self.last_fork_receipt.to_receipt()
                if self.last_fork_receipt is not None
                else None
            ),
        }
        return {**core, "sha256": stable_sha256(core)}

    def decide(
        self,
        input_items: Iterable[Mapping[str, Any]],
    ) -> ResponsesToolDecision:
        self._ensure_started()
        prior = self.previous_response_id
        lowered = app_server_inputs_from_responses_items(input_items)
        receipt = self._client.run_turn(
            thread_id=self.thread_id,
            prompt=lowered,
            output_schema=self.output_schema,
            model=self.model_id,
            effort=self.reasoning_effort,
            timeout_seconds=self.timeout_seconds,
        )
        if receipt.tool_item_count:
            raise ResponsesContinuationError(
                "app-server controller used a forbidden tool item"
            )
        try:
            arguments = json.loads(receipt.assistant_text)
        except json.JSONDecodeError as exc:
            raise ResponsesContinuationError(
                "app-server assistant output was not JSON"
            ) from exc
        if not isinstance(arguments, dict):
            raise ResponsesContinuationError(
                "app-server assistant output must be an object"
            )
        self.request_index += 1
        self.last_turn_receipt = receipt
        self.previous_response_id = receipt.turn_id
        decision = ResponsesToolDecision(
            response_id=receipt.turn_id,
            previous_response_id=prior,
            call_id=f"app-server-call:{receipt.turn_id}",
            tool_name=self.tool_name,
            arguments=arguments,
            requested_reasoning_context=self.reasoning_context,
            effective_reasoning_context="all_turns",
            input_tokens=receipt.input_tokens,
            output_tokens=receipt.output_tokens,
            cached_input_tokens=receipt.cached_input_tokens,
        )
        if self.exchange_observer is not None:
            self.exchange_observer({
                "schema": "ztare-app-server-controller-exchange-v1",
                "request_index": self.request_index,
                "input_envelope": list(lowered),
                "input_envelope_sha256": stable_sha256(lowered),
                "output_schema_sha256": stable_sha256(self.output_schema),
                "response_decision": decision.to_receipt(),
                "transport": self.transport_receipt(),
            })
        return decision


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


def responses_tool_decision_from_receipt(
    receipt: Mapping[str, Any],
) -> ResponsesToolDecision:
    if receipt.get("schema") != "ztare-responses-tool-decision-v1":
        raise ValueError("wrong Responses tool-decision schema")
    row = ResponsesToolDecision(
        response_id=str(receipt["response_id"]),
        previous_response_id=(
            str(receipt["previous_response_id"])
            if receipt.get("previous_response_id") is not None
            else None
        ),
        call_id=str(receipt["call_id"]),
        tool_name=str(receipt["tool_name"]),
        arguments=dict(receipt["arguments"]),
        requested_reasoning_context=str(
            receipt["requested_reasoning_context"]
        ),
        effective_reasoning_context=str(
            receipt["effective_reasoning_context"]
        ),
        input_tokens=int(receipt["input_tokens"]),
        output_tokens=int(receipt["output_tokens"]),
        cached_input_tokens=int(receipt["cached_input_tokens"]),
    )
    if row.to_receipt() != dict(receipt):
        raise ValueError("Responses tool-decision receipt drifted")
    return row


__all__ = [
    "PersistentResponsesToolThread",
    "ResponsesContinuationError",
    "ResponsesForkAuthority",
    "ResponsesToolDecision",
    "compile_responses_fork_authority",
    "responses_tool_decision_from_receipt",
]
