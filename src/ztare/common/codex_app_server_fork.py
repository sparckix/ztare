"""Headless Codex app-server turns and exact stored-thread forks.

The client is intentionally small and substrate-neutral.  It owns the JSON-RPC
transport, per-message persistence, completed-turn identity, and
``thread/fork(lastTurnId=...)`` receipts.  Callers own prompts, output schemas,
experimental arms, external environments, and outcome interpretation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time
from typing import Any, Callable, Mapping, Sequence


SCHEMA = "ztare-codex-app-server-fork-v1"


class AppServerProtocolError(RuntimeError):
    """The app-server violated or rejected the required protocol."""


class AppServerTimeout(TimeoutError):
    """A bounded app-server request or turn did not complete."""


def _nonempty(value: object, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} is required")
    return text


def stable_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def text_sha256(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def canonical_prompt_sha256(value: object) -> str:
    if isinstance(value, str):
        return text_sha256(value)
    return stable_sha256(value)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class _DurableJsonlTrace:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._stream = self.path.open("a", encoding="utf-8")
        self._lock = threading.Lock()

    def write(self, channel: str, payload: object) -> None:
        row = {
            "recorded_at_utc": _utc_now(),
            "channel": _nonempty(channel, "trace channel"),
            "payload": payload,
        }
        encoded = json.dumps(row, sort_keys=True, ensure_ascii=False)
        with self._lock:
            self._stream.write(encoded + "\n")
            self._stream.flush()
            os.fsync(self._stream.fileno())

    def close(self) -> None:
        with self._lock:
            if not self._stream.closed:
                self._stream.flush()
                self._stream.close()


_TOOL_ITEM_TYPES = frozenset({
    "commandExecution",
    "fileChange",
    "mcpToolCall",
    "dynamicToolCall",
    "webSearch",
    "collabAgentToolCall",
    "imageGeneration",
})


@dataclass(frozen=True)
class AppServerTurnReceipt:
    thread_id: str
    turn_id: str
    prompt_sha256: str
    assistant_text: str
    status: str
    item_types: tuple[str, ...]
    tool_item_count: int
    started_at: int | None
    completed_at: int | None
    duration_ms: int | None
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int

    def __post_init__(self) -> None:
        for name in ("thread_id", "turn_id", "prompt_sha256", "status"):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if self.tool_item_count < 0:
            raise ValueError("tool_item_count must be nonnegative")
        if min(
            self.input_tokens,
            self.output_tokens,
            self.cached_input_tokens,
        ) < 0:
            raise ValueError("turn token counts must be nonnegative")

    @property
    def assistant_output_sha256(self) -> str:
        return text_sha256(self.assistant_text)

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "app_server_turn_receipt",
            "thread_id": self.thread_id,
            "turn_id": self.turn_id,
            "prompt_sha256": self.prompt_sha256,
            "assistant_text": self.assistant_text,
            "assistant_output_sha256": self.assistant_output_sha256,
            "status": self.status,
            "item_types": list(self.item_types),
            "tool_item_count": self.tool_item_count,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_input_tokens": self.cached_input_tokens,
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


@dataclass(frozen=True)
class AppServerForkReceipt:
    source_thread_id: str
    last_turn_id: str
    fork_thread_id: str
    forked_from_id: str
    inherited_turn_ids: tuple[str, ...]
    ephemeral: bool

    def __post_init__(self) -> None:
        for name in (
            "source_thread_id",
            "last_turn_id",
            "fork_thread_id",
            "forked_from_id",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if self.fork_thread_id == self.source_thread_id:
            raise ValueError("fork retained the source thread identity")
        if self.forked_from_id != self.source_thread_id:
            raise ValueError("forkedFromId crossed source thread identity")
        if not self.inherited_turn_ids:
            raise ValueError("fork inherited no completed turns")
        if self.inherited_turn_ids[-1] != self.last_turn_id:
            raise ValueError("fork did not end at the requested last turn")

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "app_server_fork_receipt",
            "source_thread_id": self.source_thread_id,
            "last_turn_id": self.last_turn_id,
            "fork_thread_id": self.fork_thread_id,
            "forked_from_id": self.forked_from_id,
            "inherited_turn_ids": list(self.inherited_turn_ids),
            "ephemeral": self.ephemeral,
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def turn_receipt_from_completion(
    *,
    thread_id: str,
    prompt: object,
    completion_params: Mapping[str, Any],
    token_usage: Mapping[str, Any] | None = None,
) -> AppServerTurnReceipt:
    """Compile one ``turn/completed`` notification into a stable receipt."""

    if str(completion_params.get("threadId") or "") != str(thread_id):
        raise AppServerProtocolError("turn completion crossed thread identity")
    turn = completion_params.get("turn")
    if not isinstance(turn, Mapping):
        raise AppServerProtocolError("turn completion omitted turn payload")
    items = turn.get("items")
    if not isinstance(items, list):
        raise AppServerProtocolError("turn completion omitted item list")
    item_types = tuple(str(row.get("type") or "") for row in items)
    assistant_rows = [
        str(row.get("text") or "")
        for row in items
        if row.get("type") == "agentMessage"
    ]
    if not assistant_rows:
        raise AppServerProtocolError("turn completion omitted agent message")
    last_usage = (
        token_usage.get("last")
        if isinstance(token_usage, Mapping)
        else None
    )
    if not isinstance(last_usage, Mapping):
        last_usage = {}
    return AppServerTurnReceipt(
        thread_id=str(thread_id),
        turn_id=_nonempty(turn.get("id"), "turn id"),
        prompt_sha256=canonical_prompt_sha256(prompt),
        assistant_text="\n".join(assistant_rows),
        status=_nonempty(turn.get("status"), "turn status"),
        item_types=item_types,
        tool_item_count=sum(
            item_type in _TOOL_ITEM_TYPES for item_type in item_types
        ),
        started_at=turn.get("startedAt"),
        completed_at=turn.get("completedAt"),
        duration_ms=turn.get("durationMs"),
        input_tokens=int(last_usage.get("inputTokens") or 0),
        output_tokens=int(last_usage.get("outputTokens") or 0),
        cached_input_tokens=int(
            last_usage.get("cachedInputTokens") or 0
        ),
    )


def fork_receipt_from_response(
    *,
    source_thread_id: str,
    last_turn_id: str,
    response: Mapping[str, Any],
) -> AppServerForkReceipt:
    """Compile one ``thread/fork`` response into an exact-prefix receipt."""

    thread = response.get("thread")
    if not isinstance(thread, Mapping):
        raise AppServerProtocolError("fork response omitted thread")
    turns = thread.get("turns")
    if not isinstance(turns, list):
        raise AppServerProtocolError("fork response omitted inherited turns")
    turn_ids = tuple(_nonempty(row.get("id"), "inherited turn id") for row in turns)
    return AppServerForkReceipt(
        source_thread_id=str(source_thread_id),
        last_turn_id=str(last_turn_id),
        fork_thread_id=_nonempty(thread.get("id"), "fork thread id"),
        forked_from_id=_nonempty(
            thread.get("forkedFromId"),
            "forkedFromId",
        ),
        inherited_turn_ids=turn_ids,
        ephemeral=bool(thread.get("ephemeral")),
    )


class CodexAppServerClient:
    """One initialized stdio app-server connection with durable JSONL trace."""

    def __init__(
        self,
        *,
        trace_path: Path,
        command: Sequence[str] = (
            "codex",
            "app-server",
            "--listen",
            "stdio://",
        ),
        cwd: Path | None = None,
        timeout_seconds: float = 600.0,
    ) -> None:
        self.trace = _DurableJsonlTrace(Path(trace_path))
        self.command = tuple(_nonempty(row, "app-server command") for row in command)
        self.cwd = Path(cwd).resolve() if cwd is not None else None
        self.timeout_seconds = float(timeout_seconds)
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._request_id = 0
        self._messages: list[dict[str, Any]] = []
        self._stdout_queue: queue.Queue[object] = queue.Queue()
        self._process: subprocess.Popen[str] | None = None
        self._threads: list[threading.Thread] = []
        self._initialized = False

    @property
    def messages(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._messages)

    def __enter__(self) -> "CodexAppServerClient":
        self.start()
        return self

    def __exit__(self, _type, _value, _traceback) -> None:
        self.close()

    def _pump_stdout(self, stream) -> None:
        try:
            for raw in iter(stream.readline, ""):
                line = raw.rstrip("\n")
                self.trace.write("server_stdout", line)
                self._stdout_queue.put(line)
        finally:
            self._stdout_queue.put(None)

    def _pump_stderr(self, stream) -> None:
        for raw in iter(stream.readline, ""):
            self.trace.write("server_stderr", raw.rstrip("\n"))

    def start(self) -> None:
        if self._process is not None:
            return
        self.trace.write("client_process_start", {
            "command": list(self.command),
            "cwd": str(self.cwd) if self.cwd is not None else None,
        })
        self._process = subprocess.Popen(
            self.command,
            cwd=str(self.cwd) if self.cwd is not None else None,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
        assert self._process.stdout is not None
        assert self._process.stderr is not None
        self._threads = [
            threading.Thread(
                target=self._pump_stdout,
                args=(self._process.stdout,),
                daemon=True,
            ),
            threading.Thread(
                target=self._pump_stderr,
                args=(self._process.stderr,),
                daemon=True,
            ),
        ]
        for thread in self._threads:
            thread.start()
        self.initialize()

    def _write(self, payload: Mapping[str, Any]) -> None:
        if self._process is None or self._process.stdin is None:
            raise AppServerProtocolError("app-server process is not running")
        self.trace.write("client_request", dict(payload))
        self._process.stdin.write(
            json.dumps(payload, sort_keys=True, ensure_ascii=False) + "\n"
        )
        self._process.stdin.flush()

    def _next_message(self, deadline: float) -> dict[str, Any]:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AppServerTimeout("app-server message deadline elapsed")
        try:
            raw = self._stdout_queue.get(timeout=remaining)
        except queue.Empty as error:
            raise AppServerTimeout("app-server produced no message") from error
        if raw is None:
            returncode = self._process.poll() if self._process is not None else None
            raise AppServerProtocolError(
                f"app-server stdout closed with returncode {returncode}"
            )
        try:
            message = json.loads(str(raw))
        except json.JSONDecodeError as error:
            raise AppServerProtocolError(
                f"app-server emitted non-JSON stdout: {str(raw)[:200]}"
            ) from error
        if not isinstance(message, dict):
            raise AppServerProtocolError("app-server message is not an object")
        self._messages.append(message)
        return message

    def _wait_for(
        self,
        predicate: Callable[[Mapping[str, Any]], bool],
        *,
        deadline: float,
        since: int = 0,
    ) -> dict[str, Any]:
        for message in self._messages[since:]:
            if predicate(message):
                return message
        while True:
            message = self._next_message(deadline)
            if predicate(message):
                return message

    def request(
        self,
        method: str,
        params: Mapping[str, Any] | None = None,
        *,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        self._request_id += 1
        request_id = self._request_id
        payload: dict[str, Any] = {
            "id": request_id,
            "method": _nonempty(method, "request method"),
        }
        if params is not None:
            payload["params"] = dict(params)
        self._write(payload)
        timeout = self.timeout_seconds if timeout_seconds is None else float(timeout_seconds)
        deadline = time.monotonic() + timeout
        response = self._wait_for(
            lambda row: row.get("id") == request_id,
            deadline=deadline,
        )
        if response.get("error") is not None:
            raise AppServerProtocolError(
                f"{method} rejected: {json.dumps(response['error'], sort_keys=True)}"
            )
        result = response.get("result")
        if not isinstance(result, dict):
            raise AppServerProtocolError(f"{method} response omitted result")
        return result

    def notify(
        self,
        method: str,
        params: Mapping[str, Any] | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "method": _nonempty(method, "notification method"),
        }
        if params is not None:
            payload["params"] = dict(params)
        self._write(payload)

    def initialize(self) -> dict[str, Any]:
        if self._initialized:
            return {}
        result = self.request("initialize", {
            "clientInfo": {
                "name": "ztare_h97_fork_probe",
                "title": "ZTARE H97 Fork Probe",
                "version": "1.0.0",
            },
            "capabilities": {
                "experimentalApi": True,
            },
        })
        self.notify("initialized", {})
        self._initialized = True
        return result

    def start_thread(
        self,
        *,
        model: str,
        cwd: Path,
        base_instructions: str,
    ) -> dict[str, Any]:
        result = self.request("thread/start", {
            "model": _nonempty(model, "model"),
            "allowProviderModelFallback": False,
            "cwd": str(Path(cwd).resolve()),
            "sandbox": "read-only",
            "approvalPolicy": "never",
            "baseInstructions": _nonempty(
                base_instructions,
                "base_instructions",
            ),
            "dynamicTools": [],
            "environments": [],
            "selectedCapabilityRoots": [],
            "ephemeral": False,
            "experimentalRawEvents": False,
            "config": {
                "features.rmcp_client": False,
                "features.js_repl": False,
                "tools.web_search": False,
            },
        })
        if not isinstance(result.get("thread"), Mapping):
            raise AppServerProtocolError("thread/start omitted thread")
        return result

    def run_turn(
        self,
        *,
        thread_id: str,
        prompt: str | Sequence[Mapping[str, Any]],
        output_schema: Mapping[str, Any],
        model: str = "gpt-5.6-sol",
        effort: str = "xhigh",
        timeout_seconds: float | None = None,
    ) -> AppServerTurnReceipt:
        timeout = self.timeout_seconds if timeout_seconds is None else float(timeout_seconds)
        since = len(self._messages)
        app_input = (
            [{"type": "text", "text": str(prompt)}]
            if isinstance(prompt, str)
            else [dict(row) for row in prompt]
        )
        if not app_input:
            raise ValueError("app-server turn input must be nonempty")
        result = self.request("turn/start", {
            "threadId": _nonempty(thread_id, "thread_id"),
            "input": app_input,
            "model": _nonempty(model, "model"),
            "effort": _nonempty(effort, "effort"),
            "environments": [],
            "approvalPolicy": "never",
            "outputSchema": dict(output_schema),
            "responsesapiClientMetadata": {
                "ztare_transport": "app_server_exact_fork_v1",
            },
        }, timeout_seconds=timeout)
        turn = result.get("turn")
        if not isinstance(turn, Mapping):
            raise AppServerProtocolError("turn/start omitted turn")
        turn_id = _nonempty(turn.get("id"), "started turn id")
        deadline = time.monotonic() + timeout
        completed = self._wait_for(
            lambda row: (
                row.get("method") == "turn/completed"
                and isinstance(row.get("params"), Mapping)
                and row["params"].get("threadId") == thread_id
                and isinstance(row["params"].get("turn"), Mapping)
                and row["params"]["turn"].get("id") == turn_id
            ),
            deadline=deadline,
            since=since,
        )
        token_rows = [
            row["params"]["tokenUsage"]
            for row in self._messages[since:]
            if row.get("method") == "thread/tokenUsage/updated"
            and isinstance(row.get("params"), Mapping)
            and row["params"].get("threadId") == thread_id
            and row["params"].get("turnId") == turn_id
            and isinstance(row["params"].get("tokenUsage"), Mapping)
        ]
        receipt = turn_receipt_from_completion(
            thread_id=thread_id,
            prompt=app_input,
            completion_params=completed["params"],
            token_usage=token_rows[-1] if token_rows else None,
        )
        if receipt.status != "completed":
            raise AppServerProtocolError(
                f"turn {turn_id} ended with status {receipt.status}"
            )
        return receipt

    def fork_thread(
        self,
        *,
        source_thread_id: str,
        last_turn_id: str,
        model: str = "gpt-5.6-sol",
        cwd: Path | None = None,
    ) -> AppServerForkReceipt:
        params: dict[str, Any] = {
            "threadId": _nonempty(source_thread_id, "source_thread_id"),
            "lastTurnId": _nonempty(last_turn_id, "last_turn_id"),
            "model": _nonempty(model, "model"),
            "sandbox": "read-only",
            "approvalPolicy": "never",
            "ephemeral": False,
            "excludeTurns": False,
        }
        if cwd is not None:
            params["cwd"] = str(Path(cwd).resolve())
        result = self.request("thread/fork", params)
        return fork_receipt_from_response(
            source_thread_id=source_thread_id,
            last_turn_id=last_turn_id,
            response=result,
        )

    def resume_thread(
        self,
        thread_id: str,
        *,
        model: str = "gpt-5.6-sol",
        cwd: Path | None = None,
    ) -> dict[str, Any]:
        """Load a persisted thread without changing its inherited instructions."""

        params: dict[str, Any] = {
            "threadId": _nonempty(thread_id, "thread_id"),
            "model": _nonempty(model, "model"),
            "sandbox": "read-only",
            "approvalPolicy": "never",
        }
        if cwd is not None:
            params["cwd"] = str(Path(cwd).resolve())
        result = self.request("thread/resume", params)
        if not isinstance(result.get("thread"), Mapping):
            raise AppServerProtocolError("thread/resume omitted thread")
        return result

    def read_thread(
        self,
        thread_id: str,
        *,
        include_turns: bool = True,
    ) -> dict[str, Any]:
        return self.request("thread/read", {
            "threadId": _nonempty(thread_id, "thread_id"),
            "includeTurns": bool(include_turns),
        })

    def close(self) -> None:
        process = self._process
        if process is not None:
            if process.stdin is not None and not process.stdin.closed:
                process.stdin.close()
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            self.trace.write("client_process_stop", {
                "returncode": process.returncode,
            })
            self._process = None
        self.trace.close()
