"""Subscription-agent bindings for frontier blueprint, review, and navigation roles."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any, Iterator, Mapping

from ztare.common.subscription_agent_runtime import (
    CODEX_SANDBOX_SEALED_COMPLETION,
    CODEX_SANDBOX_VISIBLE_WORKBENCH,
    CODEX_SANDBOX_WEB_RESEARCH,
    SEALED_CLAUDE_DISALLOWED_TOOLS,
    get_or_create_warm_session,
    persist_warm_session,
    run_subscription_agent_with_recovery,
    warm_session_recovery_callbacks,
)
from ztare.leanmill import prompts
from ztare.leanmill.common import read_json, write_json_atomic, write_text_atomic
from ztare.leanmill.data_only_json import strict_json_data
from ztare.leanmill.frontier_blueprint_compiler import render_frontier_blueprint_prompt
from ztare.leanmill.theory_ir import content_hash


_MAX_DURABLE_ROLE_CALL_BYTES = 65_536
_MAX_DURABLE_ROLE_PROMPT_BYTES = 32_000_000
_MAX_DURABLE_ROLE_RESULT_BYTES = 16_000_000
_MAX_DURABLE_ROLE_SCHEMA_BYTES = 1_000_000
_DURABLE_ROLE_CALL_FIELDS = {
    "schema",
    "role",
    "agent_id",
    "runtime",
    "model",
    "prompt_digest",
    "returncode",
    "provider_call_charge",
    "wallclock_s",
    "stdout_digest",
    "stderr_digest",
    "result_digest",
    "output_schema_digest",
}


def _bounded_role_text(path: Path, *, maximum: int, context: str) -> str:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{context} is missing or not a regular file")
    observed = path.stat().st_size
    if observed > maximum:
        raise ValueError(f"{context} exceeds durable role byte ceiling")
    return path.read_text(encoding="utf-8")


def parse_bounded_frontier_json(
    text: str,
    *,
    context: str,
    maximum: int = _MAX_DURABLE_ROLE_RESULT_BYTES,
    allow_finite_floats: bool = False,
) -> Any:
    """Parse one bounded JSON document and apply the shared depth/type gate."""

    if len(text.encode("utf-8")) > maximum:
        raise ValueError(f"{context} exceeds durable role byte ceiling")
    try:
        value = json.loads(text)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError(f"{context} is not bounded JSON") from exc
    try:
        return strict_json_data(
            value,
            context=context,
            max_wire_bytes=maximum,
            max_integer_bits=4_096,
            allow_finite_floats=allow_finite_floats,
        )
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError(f"{context} is not bounded JSON") from exc


def read_completed_frontier_role_call(
    prefix: Path,
    *,
    expected_role: str,
    expected_prompt: str | None = None,
    expected_agent_id: str = "",
    expected_runtime: str = "",
    expected_model: str = "",
) -> dict[str, Any]:
    """Read one successful durable role call under its complete receipt."""

    call = read_frontier_role_call_receipt(prefix)
    if (
        call.get("role") != expected_role
        or expected_agent_id
        and call.get("agent_id") != expected_agent_id
        or expected_runtime
        and call.get("runtime") != expected_runtime
        or expected_model
        and call.get("model") != expected_model
        or call.get("returncode") != 0
    ):
        raise ValueError("durable frontier role call receipt changed identity")
    prompt = _bounded_role_text(
        prefix.with_suffix(".prompt.txt"),
        maximum=_MAX_DURABLE_ROLE_PROMPT_BYTES,
        context="durable frontier role prompt",
    )
    if (
        call.get("prompt_digest") != content_hash({"prompt": prompt})
        or expected_prompt is not None
        and prompt != expected_prompt
    ):
        raise ValueError("durable frontier role prompt bytes do not match receipt")
    stdout = _bounded_role_text(
        prefix.with_suffix(".stdout.txt"),
        maximum=_MAX_DURABLE_ROLE_RESULT_BYTES,
        context="durable frontier role stdout",
    )
    stderr_path = prefix.with_suffix(".stderr.txt")
    stderr = (
        _bounded_role_text(
            stderr_path,
            maximum=_MAX_DURABLE_ROLE_RESULT_BYTES,
            context="durable frontier role stderr",
        )
        if stderr_path.is_file()
        else ""
    )
    if (
        call.get("stdout_digest") != content_hash({"stdout": stdout})
        or call.get("stderr_digest") != content_hash({"stderr": stderr})
    ):
        raise ValueError("durable frontier role output bytes do not match receipt")
    result_path = prefix.with_suffix(".result.json")
    result_text = (
        _bounded_role_text(
            result_path,
            maximum=_MAX_DURABLE_ROLE_RESULT_BYTES,
            context="durable frontier role result",
        )
        if result_path.is_file()
        else stdout
    )
    result_digest = str(call.get("result_digest") or "")
    if result_path.is_file() and not result_digest:
        raise ValueError("durable frontier role result lacks its byte digest")
    if result_digest and result_digest != content_hash({"result": result_text}):
        raise ValueError("durable frontier role result bytes do not match receipt")
    try:
        parsed = _parse_last_json_object(result_text)
        parsed = strict_json_data(
            parsed,
            context="durable frontier role result",
            max_wire_bytes=_MAX_DURABLE_ROLE_RESULT_BYTES,
            max_integer_bits=4_096,
            allow_finite_floats=True,
        )
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError("durable frontier role result is not bounded JSON") from exc
    schema_path = prefix.with_suffix(".schema.json")
    schema_digest = str(call.get("output_schema_digest") or "")
    if schema_digest:
        schema_text = _bounded_role_text(
            schema_path,
            maximum=_MAX_DURABLE_ROLE_SCHEMA_BYTES,
            context="durable frontier role schema",
        )
        schema = parse_bounded_frontier_json(
            schema_text,
            context="durable frontier role schema",
            maximum=_MAX_DURABLE_ROLE_SCHEMA_BYTES,
        )
        if not isinstance(schema, Mapping) or content_hash(dict(schema)) != schema_digest:
            raise ValueError("durable frontier role schema bytes do not match receipt")
    return {
        "call": call,
        "prompt": prompt,
        "stdout": stdout,
        "stderr": stderr,
        "result_text": result_text,
        "result": parsed,
    }


def read_failed_frontier_role_call(
    prefix: Path,
    *,
    expected_role: str,
    expected_prompt: str,
    expected_agent_id: str,
    expected_runtime: str,
    expected_model: str,
) -> dict[str, Any]:
    """Read a failed call under the same byte and identity joins as success."""

    call = read_frontier_role_call_receipt(prefix)
    if (
        call.get("role") != expected_role
        or call.get("agent_id") != expected_agent_id
        or call.get("runtime") != expected_runtime
        or call.get("model") != expected_model
        or call.get("returncode") == 0
    ):
        raise ValueError("durable frontier role call receipt changed identity")
    prompt = _bounded_role_text(
        prefix.with_suffix(".prompt.txt"),
        maximum=_MAX_DURABLE_ROLE_PROMPT_BYTES,
        context="durable frontier role prompt",
    )
    if (
        prompt != expected_prompt
        or call.get("prompt_digest") != content_hash({"prompt": prompt})
    ):
        raise ValueError("durable frontier role prompt bytes do not match receipt")
    stdout = _bounded_role_text(
        prefix.with_suffix(".stdout.txt"),
        maximum=_MAX_DURABLE_ROLE_RESULT_BYTES,
        context="durable frontier role stdout",
    )
    stderr_path = prefix.with_suffix(".stderr.txt")
    stderr = (
        _bounded_role_text(
            stderr_path,
            maximum=_MAX_DURABLE_ROLE_RESULT_BYTES,
            context="durable frontier role stderr",
        )
        if stderr_path.is_file()
        else ""
    )
    if (
        call.get("stdout_digest") != content_hash({"stdout": stdout})
        or call.get("stderr_digest") != content_hash({"stderr": stderr})
    ):
        raise ValueError("durable frontier role output bytes do not match receipt")
    result_path = prefix.with_suffix(".result.json")
    if result_path.exists():
        result_text = _bounded_role_text(
            result_path,
            maximum=_MAX_DURABLE_ROLE_RESULT_BYTES,
            context="durable frontier role result",
        )
        result_digest = str(call.get("result_digest") or "")
        if not result_digest or result_digest != content_hash({"result": result_text}):
            raise ValueError("durable frontier role result bytes do not match receipt")
    return {"call": call, "prompt": prompt, "stdout": stdout, "stderr": stderr}


def read_frontier_role_call_receipt(prefix: Path) -> dict[str, Any]:
    """Read the bounded scalar receipt shared by live replay and recovery."""

    call_text = _bounded_role_text(
        prefix.with_suffix(".call.json"),
        maximum=_MAX_DURABLE_ROLE_CALL_BYTES,
        context="durable frontier role call",
    )
    call = parse_bounded_frontier_json(
        call_text,
        context="durable frontier role call",
        maximum=_MAX_DURABLE_ROLE_CALL_BYTES,
        allow_finite_floats=True,
    )
    def digest(value: Any, *, optional: bool = False) -> bool:
        raw = str(value or "")
        return bool(optional and not raw) or (
            len(raw) == 64
            and all(character in "0123456789abcdef" for character in raw)
        )

    if (
        not isinstance(call, dict)
        or set(call) != _DURABLE_ROLE_CALL_FIELDS
        or call.get("schema") != "leanmill.frontier_subscription_role_call.v1"
        or any(
            not isinstance(call.get(field), str) or not call[field]
            for field in ("role", "agent_id", "runtime", "model")
        )
        or type(call.get("returncode")) is not int
        or type(call.get("provider_call_charge")) is not int
        or call.get("provider_call_charge") not in {0, 1}
        or type(call.get("wallclock_s")) not in {int, float}
        or float(call["wallclock_s"]) < 0
        or not digest(call.get("prompt_digest"))
        or not digest(call.get("stdout_digest"))
        or not digest(call.get("stderr_digest"))
        or not digest(call.get("result_digest"), optional=True)
        or not digest(call.get("output_schema_digest"), optional=True)
    ):
        raise ValueError("durable frontier role call receipt changed identity")
    return call


def _parse_last_json_object(text: str) -> dict[str, Any]:
    value = str(text or "").strip()
    if value.startswith("```"):
        value = value.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        parsed_whole = json.loads(value)
    except json.JSONDecodeError:
        parsed_whole = None
    if isinstance(parsed_whole, dict):
        return parsed_whole
    decoder = json.JSONDecoder()
    found: list[tuple[int, int, dict[str, Any]]] = []
    for index, character in enumerate(value):
        if character != "{":
            continue
        try:
            parsed, end = decoder.raw_decode(value[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            found.append((index, index + end, parsed))
    if not found:
        raise ValueError("subscription frontier role returned no JSON object")
    outermost = [
        candidate
        for candidate in found
        if not any(
            other_start <= candidate[0]
            and candidate[1] <= other_end
            and (other_start, other_end) != candidate[:2]
            for other_start, other_end, _other in found
        )
    ]
    return (outermost or found)[-1][2]


def _retryable_transport_failure(stderr: str) -> str | None:
    lowered = str(stderr).lower()
    if (
        "failed to initialize in-process app-server client" in lowered
        and "operation not permitted" in lowered
    ):
        return "subscription_runtime_sandbox_denied"
    if "invalid_json_schema" in lowered:
        return "invalid_json_schema"
    if "requires a newer version of codex" in lowered:
        return "codex_cli_upgrade_required"
    if (
        "reasoning.effort" in lowered
        and "invalid_value" in lowered
    ) or (
        "invalid value" in lowered
        and "supported values" in lowered
        and ("xhigh" in lowered or "reasoning" in lowered)
    ):
        return "unsupported_reasoning_effort"
    return None


def _provider_call_charge(result: subprocess.CompletedProcess[str]) -> int:
    """Count inference for this campaign role; unfamiliar failures cost one."""

    if result.returncode == 0:
        return 1
    text = f"{result.stdout or ''}\n{result.stderr or ''}".lower()
    if (
        "invalid_json_schema" in text
        or "requires a newer version of codex" in text
        or (
            "reasoning.effort" in text
            and "invalid_value" in text
        )
        or (
            "invalid value" in text
            and "supported values" in text
            and ("xhigh" in text or "reasoning" in text)
        )
        or (
            "model" in text
            and "not supported" in text
            and "chatgpt account" in text
        )
        or "selected model is at capacity" in text
        or "model is at capacity" in text
        or (
            "failed to initialize in-process app-server client" in text
            and "operation not permitted" in text
        )
    ):
        return 0
    return 1


def _validate_codex_strict_schema(node: Any, path: str = "$") -> None:
    """Reject response-schema shapes Codex cannot accept before dispatch."""

    if not isinstance(node, Mapping):
        return
    unsupported = {"uniqueItems"}.intersection(node)
    if unsupported:
        keyword = sorted(unsupported)[0]
        raise ValueError(
            f"Codex output schema uses unsupported keyword {keyword!r} at {path}"
        )
    if "const" in node and "type" not in node:
        raise ValueError(f"Codex output schema const lacks type at {path}")
    if node.get("type") == "object":
        properties = node.get("properties")
        if not isinstance(properties, Mapping) or node.get("additionalProperties") is not False:
            raise ValueError(f"Codex output schema object is not strict at {path}")
        if set(node.get("required") or ()) != set(properties):
            raise ValueError(f"Codex output schema object has optional fields at {path}")
    for key in ("properties", "$defs"):
        for name, child in dict(node.get(key) or {}).items():
            _validate_codex_strict_schema(child, f"{path}.{key}.{name}")
    if "items" in node:
        _validate_codex_strict_schema(node["items"], f"{path}.items")
    for key in ("anyOf", "oneOf", "allOf"):
        for index, child in enumerate(node.get(key) or ()):
            _validate_codex_strict_schema(child, f"{path}.{key}[{index}]")


class FrontierRolePreDispatchContractError(ValueError):
    """The local/provider response contract failed before inference."""


@dataclass(frozen=True)
class FrontierAgentConfig:
    runtime: str = "codex"
    model: str = "gpt-5.4-mini"
    reasoning_effort: str = "low"
    timeout_seconds: int = 300
    visible_workbench: bool = False
    web_research: bool = False
    governed_pool: bool = False
    allow_subscription_failover: bool = False

    def __post_init__(self) -> None:
        from ztare.common.llm_runtime import NORMALIZED_REASONING_EFFORTS

        if self.reasoning_effort not in NORMALIZED_REASONING_EFFORTS:
            raise ValueError("frontier role requires low, medium, high, or ultra effort")
        if self.visible_workbench and self.web_research:
            raise ValueError("frontier role cannot expose workbench and web in one call")


@contextmanager
def scoped_frontier_agent_environment(
    config: FrontierAgentConfig,
    *,
    solver_run_tag: str = "",
) -> Iterator[None]:
    """Apply one campaign role to LeanMill's existing subscription-agent knobs."""

    bindings = {
        "ZTARE_DEFAULT_SUBSCRIPTION_RUNTIME": config.runtime,
        "ZTARE_LEANMILL_LEAF_RUNTIME": config.runtime,
        "ZTARE_LEANMILL_PROPOSER_POOL": "1" if config.governed_pool else "0",
        "ZTARE_LEANMILL_NO_SUBSCRIPTION_FAILOVER": (
            "0" if config.allow_subscription_failover else "1"
        ),
    }
    if solver_run_tag:
        bindings["ZTARE_SOLVER_RUN_TAG"] = solver_run_tag
    from ztare.common.llm_runtime import subscription_reasoning_effort

    native_effort = subscription_reasoning_effort(
        config.runtime, config.reasoning_effort, model=config.model
    )
    if native_effort is None:
        raise ValueError(f"unsupported effort for {config.runtime}: {config.reasoning_effort}")
    if config.runtime == "codex":
        bindings.update(
            {
                "ZTARE_CODEX_AGENT_MODEL": config.model,
                "ZTARE_CODEX_AGENT_REASONING_EFFORT": native_effort,
            }
        )
    elif config.runtime == "claude":
        bindings.update(
            {
                "ZTARE_CLAUDE_AGENT_MODEL": config.model,
                "ZTARE_CLAUDE_EFFORT": native_effort,
            }
        )
    else:
        raise ValueError(f"unsupported frontier subscription runtime: {config.runtime}")
    prior = {key: os.environ.get(key) for key in bindings}
    os.environ.update(bindings)
    try:
        yield
    finally:
        for key, value in prior.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


@dataclass
class SubscriptionJSONRole:
    role: str
    agent_id: str
    repo: Path
    artifact_dir: Path
    config: FrontierAgentConfig = field(default_factory=FrontierAgentConfig)
    output_schema: Mapping[str, Any] | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)
    budget_ledger: Any | None = None

    @property
    def call_count(self) -> int:
        return sum(not row.get("replayed") for row in self.calls)

    @property
    def provider_call_count(self) -> int:
        """Inference calls charged to the campaign's scientific budget.

        Receipts written before this field existed count as one, preserving the
        conservative historical interpretation.
        """

        return sum(
            int(row.get("provider_call_charge", 1))
            for row in self.calls
            if not row.get("replayed")
        )

    def replay_durable_success(self, prompt: str) -> dict[str, Any] | None:
        """Replay one exact completed call before any new-work reservation."""

        index = len(self.calls)
        prefix = self.artifact_dir / f"{index:03d}"
        call_path = prefix.with_suffix(".call.json")
        if not call_path.is_file():
            return None
        prior = read_frontier_role_call_receipt(prefix)
        if prior.get("returncode") != 0:
            return None
        durable = read_completed_frontier_role_call(
            prefix,
            expected_role=self.role,
            expected_prompt=prompt,
            expected_agent_id=self.agent_id,
            expected_runtime=self.config.runtime,
            expected_model=self.config.model,
        )
        parsed = durable["result"]
        if not isinstance(parsed, dict):
            raise ValueError("durable frontier role result is not an object")
        frozen_schema = read_json(prefix.with_suffix(".schema.json"), None)
        if isinstance(frozen_schema, Mapping):
            self._validate_result_against(parsed, frozen_schema)
        self.calls.append({**durable["call"], "replayed": True})
        return parsed

    def __call__(self, prompt: str) -> dict[str, Any]:
        index = len(self.calls)
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        prefix = self.artifact_dir / f"{index:03d}"
        prompt_digest = content_hash({"prompt": prompt})
        call_path = prefix.with_suffix(".call.json")
        prompt_path = prefix.with_suffix(".prompt.txt")
        stdout_path = prefix.with_suffix(".stdout.txt")
        result_path = prefix.with_suffix(".result.json")
        schema_path = prefix.with_suffix(".schema.json")
        if call_path.exists():
            prior = read_frontier_role_call_receipt(prefix)
            if prior.get("returncode") != 0:
                failed = read_failed_frontier_role_call(
                    prefix,
                    expected_role=self.role,
                    expected_prompt=prompt,
                    expected_agent_id=self.agent_id,
                    expected_runtime=self.config.runtime,
                    expected_model=self.config.model,
                )
                failure = _retryable_transport_failure(
                    f"{failed['stdout']}\n{failed['stderr']}"
                )
                if failure is None:
                    raise ValueError("durable frontier role call failed non-retryably")
                self.calls.append(
                    {
                        **prior,
                        "replayed": True,
                        "retryable_transport_failure": failure,
                    }
                )
                return self(prompt)
            durable = read_completed_frontier_role_call(
                prefix,
                expected_role=self.role,
                expected_prompt=prompt,
                expected_agent_id=self.agent_id,
                expected_runtime=self.config.runtime,
                expected_model=self.config.model,
            )
            parsed = durable["result"]
            if not isinstance(parsed, dict):
                raise ValueError("durable frontier role result is not an object")
            frozen_schema = read_json(schema_path, None)
            if isinstance(frozen_schema, Mapping):
                self._validate_result_against(parsed, frozen_schema)
            self.calls.append({**prior, "replayed": True})
            return parsed

        if result_path.exists():
            raise ValueError("frontier role has result bytes without a completed call receipt")
        write_text_atomic(prompt_path, prompt)
        if self.output_schema is not None:
            if self.config.runtime == "codex":
                _validate_codex_strict_schema(self.output_schema)
            write_json_atomic(schema_path, dict(self.output_schema))

        timeout_seconds = self.config.timeout_seconds
        if self.budget_ledger is not None:
            remaining_ms = (
                self.budget_ledger.wall_clock_cap_s() * 1_000
                - self.budget_ledger.elapsed_ms()
            )
            if remaining_ms <= 0:
                from ztare.leanmill.exploration_budget import BudgetExceeded

                raise BudgetExceeded("hard_cap_reached:wall_clock_s")
            timeout_seconds = min(timeout_seconds, max(1, remaining_ms // 1_000))
        started = time.monotonic()
        session_dir = self.artifact_dir.parent / ".sessions"
        session_agent_id = re.sub(r"\.wave-\d+$", "", self.agent_id)
        session_state = get_or_create_warm_session(
            session_dir,
            runtime=self.config.runtime,
            agent_id=session_agent_id,
        )
        invalidate_session, create_replacement_session = (
            warm_session_recovery_callbacks(
                session_dir,
                runtime=self.config.runtime,
                agent_id=session_agent_id,
            )
        )
        with scoped_frontier_agent_environment(self.config):
            run = run_subscription_agent_with_recovery(
                runtime=self.config.runtime,
                prompt=prompt,
                agent_id=self.agent_id,
                repo=self.repo,
                session_state=session_state,
                timeout_seconds=timeout_seconds,
                invalidate_session=invalidate_session,
                create_replacement_session=create_replacement_session,
                default_codex_model=self.config.model,
                codex_sandbox=(
                    CODEX_SANDBOX_WEB_RESEARCH
                    if self.config.web_research
                    else CODEX_SANDBOX_VISIBLE_WORKBENCH
                    if self.config.visible_workbench
                    else CODEX_SANDBOX_SEALED_COMPLETION
                ),
                claude_disallowed_tools=(
                    tuple(
                        tool
                        for tool in SEALED_CLAUDE_DISALLOWED_TOOLS
                        if not self.config.web_research
                        or tool not in {"WebSearch", "WebFetch"}
                    )
                    if self.config.runtime == "claude"
                    and not self.config.visible_workbench
                    else None
                ),
                output_schema=(
                    schema_path
                    if self.output_schema is not None and self.config.runtime == "codex"
                    else None
                ),
                output_last_message_path=(
                    result_path if self.config.runtime == "codex" else None
                ),
                dispatch_receipt_path=prefix.with_suffix(".dispatch.json"),
                stdout_path=str(stdout_path),
                stderr_path=str(prefix.with_suffix(".stderr.txt")),
            )
        stdout = str(run.result.stdout or "")
        stderr = str(run.result.stderr or "")
        write_text_atomic(stdout_path, stdout)
        write_text_atomic(prefix.with_suffix(".stderr.txt"), stderr)
        result_text = (
            result_path.read_text(encoding="utf-8")
            if result_path.is_file()
            else ""
        )
        record = {
            "schema": "leanmill.frontier_subscription_role_call.v1",
            "role": self.role,
            "agent_id": self.agent_id,
            "runtime": self.config.runtime,
            "model": self.config.model,
            "prompt_digest": prompt_digest,
            "returncode": int(run.result.returncode),
            "provider_call_charge": _provider_call_charge(run.result),
            "wallclock_s": round(time.monotonic() - started, 3),
            "stdout_digest": content_hash({"stdout": stdout}),
            "stderr_digest": content_hash({"stderr": stderr}),
            "result_digest": (
                content_hash({"result": result_text}) if result_text else ""
            ),
            "output_schema_digest": (
                content_hash(dict(self.output_schema))
                if self.output_schema is not None else ""
            ),
        }
        write_json_atomic(prefix.with_suffix(".call.json"), record)
        self.calls.append(record)
        if run.result.returncode == 0:
            persist_warm_session(
                session_dir,
                runtime=self.config.runtime,
                agent_id=session_agent_id,
                session_state=getattr(run, "final_session_state", None),
            )
        if run.result.returncode != 0 or not stdout.strip():
            failure = _retryable_transport_failure(f"{stdout}\n{stderr}")
            if failure == "invalid_json_schema":
                raise FrontierRolePreDispatchContractError(
                    "frontier role output schema was rejected before inference"
                )
            raise RuntimeError(f"frontier {self.role} agent failed: rc={run.result.returncode}")
        if self.config.runtime == "codex" and not result_text.strip():
            raise RuntimeError(f"frontier {self.role} agent produced no dedicated final message")
        parsed = _parse_last_json_object(result_text or stdout)
        self._validate_result(parsed)
        return parsed

    def call_with_compatible_prompts(
        self,
        prompt: str,
        compatible_prompts: tuple[str, ...],
    ) -> dict[str, Any]:
        """Replay immutable prior bytes under their exact historical prompt."""

        index = len(self.calls)
        prefix = self.artifact_dir / f"{index:03d}"
        call_path = prefix.with_suffix(".call.json")
        prior = (
            read_frontier_role_call_receipt(prefix)
            if call_path.exists()
            else None
        )
        current_digest = content_hash({"prompt": prompt})
        if isinstance(prior, dict) and prior.get("prompt_digest") != current_digest:
            prompt_path = prefix.with_suffix(".prompt.txt")
            if prompt_path.is_file():
                frozen_prompt = _bounded_role_text(
                    prompt_path,
                    maximum=_MAX_DURABLE_ROLE_PROMPT_BYTES,
                    context="durable frontier role prompt",
                )
                if content_hash({"prompt": frozen_prompt}) != prior.get("prompt_digest"):
                    raise ValueError("durable frontier role prompt bytes do not match receipt")
                if prior.get("returncode") == 0:
                    return self(frozen_prompt)
            matched = next(
                (
                    candidate
                    for candidate in compatible_prompts
                    if content_hash({"prompt": candidate}) == prior.get("prompt_digest")
                ),
                None,
            )
            if matched is None and not prompt_path.is_file():
                raise ValueError(
                    "durable frontier role call does not match any prompt version"
                )
            if prior.get("returncode") == 0:
                if matched is None:
                    raise ValueError(
                        "durable frontier role call does not match any prompt version"
                    )
                return self(matched)
            failed_prompt = frozen_prompt if prompt_path.is_file() else matched
            if failed_prompt is None:
                raise ValueError(
                    "durable frontier role call does not match any prompt version"
                )
            failed = read_failed_frontier_role_call(
                prefix,
                expected_role=self.role,
                expected_prompt=failed_prompt,
                expected_agent_id=self.agent_id,
                expected_runtime=self.config.runtime,
                expected_model=self.config.model,
            )
            failure = _retryable_transport_failure(
                f"{failed['stdout']}\n{failed['stderr']}"
            )
            if failure is None:
                raise ValueError("durable frontier role call failed non-retryably")
            self.calls.append(
                {
                    **prior,
                    "replayed": True,
                    "retryable_transport_failure": failure,
                }
            )
        return self(prompt)

    def _validate_result(self, value: Mapping[str, Any]) -> None:
        if self.output_schema is None:
            return
        self._validate_result_against(value, self.output_schema)

    @staticmethod
    def _validate_result_against(
        value: Mapping[str, Any], schema: Mapping[str, Any]
    ) -> None:
        from jsonschema import Draft202012Validator

        Draft202012Validator(dict(schema)).validate(dict(value))


def make_subscription_frontier_compiler_roles(
    *,
    compiler: SubscriptionJSONRole,
    reviewer: SubscriptionJSONRole,
) -> tuple[Any, Any]:
    if compiler.agent_id == reviewer.agent_id:
        raise ValueError("frontier compiler and reviewer must use distinct agent identities")

    def draft_fn(brief: Mapping[str, Any]) -> Mapping[str, Any]:
        return compiler(render_frontier_blueprint_prompt(brief))

    def review_fn(payload: Mapping[str, Any]) -> Mapping[str, Any]:
        return reviewer(
            prompts.FRONTIER_BLUEPRINT_SEMANTIC_REVIEW_PROMPT.format(
                review_json=json.dumps(dict(payload), sort_keys=True, separators=(",", ":"))
            )
        )

    # Preserve call accounting across the thin closures.
    draft_fn.call_role = compiler  # type: ignore[attr-defined]
    review_fn.call_role = reviewer  # type: ignore[attr-defined]
    return draft_fn, review_fn


def make_subscription_campaign_budget_compiler(role: SubscriptionJSONRole) -> Any:
    """Compile campaign-level NL preferences to the canonical budget YAML shape."""

    def compiler(preference_text: str) -> Mapping[str, Any]:
        return role(
            prompts.AXIOMPACK_CAMPAIGN_BUDGET_COMPILER_PROMPT.format(
                preference_text=str(preference_text)
            )
        )

    compiler.call_role = role  # type: ignore[attr-defined]
    return compiler


def make_subscription_adapter_reviewer(role: SubscriptionJSONRole) -> Any:
    """Bind independent AdapterForge review to the shared subscription runtime."""

    def reviewer(payload: Mapping[str, Any]) -> Mapping[str, Any]:
        return role(
            prompts.ADAPTER_FORGE_REVIEW_PROMPT.format(
                review_json=json.dumps(dict(payload), sort_keys=True, separators=(",", ":"))
            )
        )

    reviewer.call_role = role  # type: ignore[attr-defined]
    return reviewer


def make_subscription_witness_constructor(role: SubscriptionJSONRole) -> Any:
    """Bind a distinct visible-workbench role to inert witness authorship."""

    from ztare.leanmill.witness_construction_boundary import (
        WitnessConstructorUnavailable,
        build_witness_constructor_output,
        validate_witness_constructor_request,
    )

    def constructor(request: Mapping[str, Any]) -> Mapping[str, Any]:
        frozen = validate_witness_constructor_request(request)
        if role.role != "witness_constructor" or not role.config.visible_workbench:
            raise WitnessConstructorUnavailable(
                "visible_witness_constructor_runtime_unavailable"
            )
        prompt = prompts.AXIOMPACK_WITNESS_CONSTRUCTOR_PROMPT.format(
            construction_request_json=json.dumps(
                frozen, sort_keys=True, separators=(",", ":")
            )
        )
        ledger = role.budget_ledger
        reservation = None
        before = role.provider_call_count
        replay = getattr(role, "replay_durable_success", None)
        raw = replay(prompt) if callable(replay) else None
        if raw is None:
            if getattr(constructor, "continuation_turn_available", True) is not True:
                raise WitnessConstructorUnavailable(
                    "witness_constructor_causal_continuation_unavailable"
                )
            if ledger is not None:
                if (
                    min(
                        ledger.remaining_capacity(
                            str(getattr(constructor, "budget_phase", "navigation")),
                            "provider_calls",
                        ),
                        ledger.remaining_capacity(
                            str(getattr(constructor, "budget_phase", "navigation")),
                            "agent_turns",
                        ),
                    )
                    < 2
                ):
                    raise WitnessConstructorUnavailable(
                        "witness_constructor_causal_continuation_unavailable"
                    )
                reservation = ledger.reserve(
                    "witness-constructor:" + frozen["request_sha256"][:16],
                    str(getattr(constructor, "budget_phase", "navigation")),
                    {"provider_calls": 1, "agent_turns": 1},
                )
            try:
                raw = role(prompt)
            except RuntimeError as exc:
                raise WitnessConstructorUnavailable(
                    "witness_constructor_runtime_failure:" + str(exc)[:256]
                ) from exc
            finally:
                if reservation is not None:
                    used = max(
                        0,
                        min(1, role.provider_call_count - before),
                    )
                    ledger.commit(
                        reservation,
                        {"provider_calls": used, "agent_turns": used},
                    )
        if type(raw) is not dict or set(raw) != {"artifact", "orientation"}:
            raise ValueError("witness constructor returned an invalid output envelope")
        call = role.calls[-1] if role.calls else None
        if not isinstance(call, Mapping):
            raise ValueError("witness constructor lacks a durable call receipt")
        call_fields = (
            "schema",
            "role",
            "agent_id",
            "runtime",
            "model",
            "prompt_digest",
            "returncode",
            "provider_call_charge",
            "stdout_digest",
            "stderr_digest",
            "result_digest",
            "output_schema_digest",
        )
        call_receipt = {field: call.get(field) for field in call_fields}
        if (
            call_receipt["role"] != "witness_constructor"
            or call_receipt["agent_id"] != role.agent_id
            or call_receipt["prompt_digest"] != content_hash({"prompt": prompt})
            or call_receipt["returncode"] != 0
        ):
            raise ValueError("witness constructor call receipt changed identity")
        return build_witness_constructor_output(
            frozen,
            artifact=raw["artifact"],
            orientation=raw["orientation"],
            role="witness_constructor",
            agent_id=role.agent_id,
            call_receipt_sha256=content_hash(call_receipt),
        )

    constructor.call_role = role  # type: ignore[attr-defined]
    return constructor


def make_subscription_theory_navigator(
    role: SubscriptionJSONRole,
    *,
    attempt_id: str,
    campaign_id: str = "",
    witness_constructor_fn: Any | None = None,
) -> Any:
    """Adapt one JSON subscription role to the public navigator callback."""
    from ztare.leanmill.theory_navigator import run_interactive_theory_navigator

    def navigator(
        context: Any,
        blueprint: Any,
        journal: Any,
        *,
        budget_ledger: Any | None = None,
    ) -> Mapping[str, Any]:
        max_finalists = int(blueprint.query_budget.get("max_finalists", 8))
        role.budget_ledger = budget_ledger
        constructor = getattr(
            navigator, "witness_constructor_fn", witness_constructor_fn
        )
        constructor_role = getattr(constructor, "call_role", None)
        if constructor_role is not None:
            constructor_role.budget_ledger = budget_ledger
        if constructor is not None:
            constructor.budget_phase = "navigation"  # type: ignore[attr-defined]
        return run_interactive_theory_navigator(
            context,
            blueprint,
            journal,
            agent_fn=role,
            attempt_id=attempt_id,
            campaign_id=(
                campaign_id
                or "campaign:"
                + blueprint.blueprint_id.split(":", 1)[1][:24]
            ),
            max_rounds=int(blueprint.query_budget.get("navigator_rounds", 24)),
            max_finalists=max_finalists,
            budget_ledger=budget_ledger,
            initial_trace=tuple(getattr(navigator, "initial_trace", ())),
            prior_agent_turns=int(getattr(navigator, "prior_agent_turns", 0)),
            round_offset=int(getattr(navigator, "round_offset", 0)),
            epoch=int(getattr(navigator, "epoch", 0)),
            prior_conflict_rows=tuple(
                getattr(navigator, "prior_conflict_rows", ())
            ),
            replay_decisions=tuple(
                getattr(navigator, "replay_decisions", ())
            ),
            witness_constructor_fn=constructor,
            candidate_outcome_memory=getattr(
                navigator, "candidate_outcome_memory", None
            ),
        )

    navigator.call_role = role  # type: ignore[attr-defined]
    if witness_constructor_fn is not None:
        navigator.witness_constructor_fn = witness_constructor_fn  # type: ignore[attr-defined]
    navigator.accepts_budget_ledger = True  # type: ignore[attr-defined]
    navigator.accepts_theory_conflict_memory = True  # type: ignore[attr-defined]
    return navigator


__all__ = [
    "FrontierAgentConfig", "FrontierRolePreDispatchContractError",
    "SubscriptionJSONRole",
    "make_subscription_adapter_reviewer", "make_subscription_campaign_budget_compiler",
    "make_subscription_frontier_compiler_roles", "make_subscription_witness_constructor",
    "make_subscription_theory_navigator",
    "scoped_frontier_agent_environment",
]
