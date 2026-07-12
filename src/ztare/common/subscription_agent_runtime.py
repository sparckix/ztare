"""Subscription-backed Codex/Claude agent runtime helpers.

This module is for interactive agent CLIs authenticated by the operator's
subscription, not API-backed LLM calls. API LLM calls belong in
`src.ztare.common.llm_runtime`.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import json
import os
import re
import select
import signal
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping


SUPPORTED_SUBSCRIPTION_RUNTIMES = {"codex", "claude"}
CODEX_SANDBOX_SEALED_COMPLETION = "read-only"
CODEX_SANDBOX_VISIBLE_WORKBENCH = "workspace-write-shell"
CODEX_SANDBOX_LEGACY_READ_ONLY_SHELL = "read-only-shell"
CODEX_SANDBOX_WEB_RESEARCH = "read-only-web"


def _codex_execution_boundary(command: list[str], sandbox: str) -> None:
    """Select the Codex process boundary declared by the execution host.

    Some remote workers already provide the process boundary but cannot nest
    Codex's Linux bubblewrap sandbox.  They set
    ``ZTARE_CODEX_NESTED_SANDBOX=0``; capability-specific tool seals remain in
    force, while Codex skips the unavailable nested boundary.
    """

    if os.environ.get("ZTARE_CODEX_NESTED_SANDBOX", "1") == "0":
        command.append("--dangerously-bypass-approvals-and-sandbox")
    else:
        command += ["--sandbox", sandbox]

def prompt_inline_max_bytes() -> int:
    """Resolve the inline-prompt transport limit from the LeanMill policy."""

    try:
        from ztare.leanmill.policy import prompt_transport_policy

        return int(prompt_transport_policy()["inline_prompt_max_bytes"])
    except (ImportError, KeyError, TypeError, ValueError):
        # Isolated runtime tests may not ship the policy tree.  The policy
        # helper itself supplies the platform-derived fallback.
        return max(1, int(os.sysconf("SC_ARG_MAX")) // 4)

_DISPATCH_BUDGET_HOOKS: ContextVar[
    tuple[Callable[[str, tuple[str, ...]], Any], Callable[[Any], None]] | None
] = ContextVar("subscription_dispatch_budget_hooks", default=None)


@contextmanager
def subscription_dispatch_budget_scope(
    *,
    before_dispatch: Callable[[str, tuple[str, ...]], Any],
    after_dispatch: Callable[[Any], None],
) -> Iterator[None]:
    """Meter logical subscription dispatches without changing their transport."""

    token = _DISPATCH_BUDGET_HOOKS.set((before_dispatch, after_dispatch))
    try:
        yield
    finally:
        _DISPATCH_BUDGET_HOOKS.reset(token)


def default_subscription_runtime(env_var: str = "ZTARE_AGENT_RUNTIME") -> str:
    """The canonical env-driven SELECTOR for which subscription agent to use — read `env_var`, VALIDATE
    against SUPPORTED_SUBSCRIPTION_RUNTIMES, fall back to 'codex'. The ONE place a caller picks codex↔claude
    without a hardcoded provider string; callers pass their own scoped env var (e.g. the solver leaf uses
    `ZTARE_LEANMILL_LEAF_RUNTIME`). Fail-safe: an unknown value silently degrades to 'codex' (never crashes
    a run on a typo'd provider)."""
    rt = (os.environ.get(env_var) or "").strip().lower()
    if rt in SUPPORTED_SUBSCRIPTION_RUNTIMES:
        return rt
    # GLOBAL one-switch override (2026-06-10): when a provider is out (codex hit its usage limit), set
    # ZTARE_DEFAULT_SUBSCRIPTION_RUNTIME=claude ONCE to flip every scoped selector that didn't set its own
    # env var — the leaf, planner, formalizer default together. Reversible (unset when codex returns). Then
    # the historical 'codex' fallback. (Per-dispatch provider FAILOVER in agentic_leaf is the safety net on top.)
    g = (os.environ.get("ZTARE_DEFAULT_SUBSCRIPTION_RUNTIME") or "").strip().lower()
    if g in SUPPORTED_SUBSCRIPTION_RUNTIMES:
        return g
    return "codex"


@dataclass(frozen=True)
class SubscriptionAgentRun:
    result: subprocess.CompletedProcess[str]
    final_session_state: dict[str, Any] | None
    initial_command: list[str]
    final_command: list[str]
    recovery_note: str | None = None


OWNED_DISPATCH_SCHEMA = "ztare.owned_dispatch.v1"


@dataclass(frozen=True)
class OwnedDispatch:
    """Recorded proof that a child process group belongs to one dispatch.

    Cancellation is permitted only while the live pid/pgid/sid mapping still
    matches this receipt. Command-name matching and inferred process ancestry
    are deliberately outside the contract.
    """

    call_id: str
    leader_pid: int
    pgid: int
    sid: int
    parent_pgid: int
    command_sha256: str
    stdin_sha256: str = ""
    stdout_path: str = ""
    stderr_path: str = ""
    started_at_epoch: float = 0.0
    schema: str = OWNED_DISPATCH_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != OWNED_DISPATCH_SCHEMA:
            raise ValueError(f"unsupported owned dispatch schema: {self.schema!r}")
        if not self.call_id or not self.command_sha256:
            raise ValueError("owned dispatch identity fields must be non-empty")
        if min(self.leader_pid, self.pgid, self.sid, self.parent_pgid) <= 0:
            raise ValueError("owned dispatch process identities must be positive")
        if self.leader_pid != self.pgid or self.leader_pid != self.sid:
            raise ValueError("owned dispatch requires leader_pid == pgid == sid")
        if self.pgid == self.parent_pgid:
            raise ValueError("owned dispatch group must differ from the parent group")

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "call_id": self.call_id,
            "leader_pid": self.leader_pid,
            "pgid": self.pgid,
            "sid": self.sid,
            "parent_pgid": self.parent_pgid,
            "command_sha256": self.command_sha256,
            "stdin_sha256": self.stdin_sha256,
            "stdout_path": self.stdout_path,
            "stderr_path": self.stderr_path,
            "started_at_epoch": self.started_at_epoch,
        }

    @classmethod
    def from_json(cls, value: Mapping[str, Any]) -> "OwnedDispatch":
        return cls(
            schema=str(value.get("schema", "")),
            call_id=str(value.get("call_id", "")),
            leader_pid=int(value.get("leader_pid", 0)),
            pgid=int(value.get("pgid", 0)),
            sid=int(value.get("sid", 0)),
            parent_pgid=int(value.get("parent_pgid", 0)),
            command_sha256=str(value.get("command_sha256", "")),
            stdin_sha256=str(value.get("stdin_sha256", "")),
            stdout_path=str(value.get("stdout_path", "")),
            stderr_path=str(value.get("stderr_path", "")),
            started_at_epoch=float(value.get("started_at_epoch", 0.0)),
        )


def _command_digest(command: list[str]) -> str:
    raw = json.dumps(command, ensure_ascii=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _owned_dispatch_for_process(
    proc: subprocess.Popen[Any],
    command: list[str],
    *,
    call_id: str | None = None,
    stdin_text: str | None = None,
    stdout_path: str = "",
    stderr_path: str = "",
) -> OwnedDispatch:
    return OwnedDispatch(
        call_id=call_id or str(uuid.uuid4()),
        leader_pid=proc.pid,
        pgid=os.getpgid(proc.pid),
        sid=os.getsid(proc.pid),
        parent_pgid=os.getpgrp(),
        command_sha256=_command_digest(command),
        stdin_sha256=(
            "sha256:" + hashlib.sha256(stdin_text.encode("utf-8")).hexdigest()
            if stdin_text is not None
            else ""
        ),
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        started_at_epoch=time.time(),
    )


def owned_dispatch_status(dispatch: OwnedDispatch) -> str:
    """Return running, exited, or ambiguous without inferring ownership."""
    try:
        live = (os.getpgid(dispatch.leader_pid), os.getsid(dispatch.leader_pid))
    except ProcessLookupError:
        return "exited"
    except (PermissionError, OSError):
        return "ambiguous"
    if live != (dispatch.pgid, dispatch.sid):
        return "ambiguous"
    if dispatch.leader_pid != dispatch.pgid or dispatch.leader_pid != dispatch.sid:
        return "ambiguous"
    if dispatch.pgid == os.getpgrp():
        return "ambiguous"
    return "running"


def cancel_owned_dispatch(dispatch: OwnedDispatch, *, sig: int = signal.SIGTERM) -> bool:
    """Signal exactly one proven child session; ambiguity always fails closed."""
    if owned_dispatch_status(dispatch) != "running":
        return False
    # Recheck immediately before the signal to narrow pid-reuse races.
    try:
        if (
            os.getpgid(dispatch.leader_pid) != dispatch.pgid
            or os.getsid(dispatch.leader_pid) != dispatch.sid
            or dispatch.pgid == os.getpgrp()
        ):
            return False
        os.killpg(dispatch.pgid, sig)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False


def _write_owned_dispatch_envelope(
    path: str | Path | None,
    dispatch: OwnedDispatch,
    *,
    status: str,
    returncode: int | None = None,
) -> None:
    if path is None:
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        **dispatch.to_json(),
        "status": status,
        "returncode": returncode,
        "updated_at_epoch": time.time(),
    }
    temporary = target.with_name(target.name + f".{uuid.uuid4().hex}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, target)


def owned_dispatch_receipt_status(path: str | Path) -> str:
    try:
        row = json.loads(Path(path).read_text(encoding="utf-8"))
        if row.get("status") == "completed":
            return "completed"
        return owned_dispatch_status(OwnedDispatch.from_json(row))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return "ambiguous"


def cancel_owned_dispatch_receipt(path: str | Path, *, sig: int = signal.SIGTERM) -> bool:
    try:
        row = json.loads(Path(path).read_text(encoding="utf-8"))
        if row.get("status") != "running":
            return False
        return cancel_owned_dispatch(OwnedDispatch.from_json(row), sig=sig)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False


def _terminate_owned_process(
    proc: subprocess.Popen[Any], dispatch: OwnedDispatch, *, grace_s: float = 0.5
) -> None:
    if proc.poll() is not None:
        return
    if not cancel_owned_dispatch(dispatch, sig=signal.SIGTERM):
        raise RuntimeError("refusing to terminate an ambiguously owned dispatch")
    # TERM may reap the leader before a descendant that inherited a pipe exits.
    # The group was proven above; retain that bounded authority through the
    # grace interval instead of trying to rediscover ownership from process lists.
    deadline = time.monotonic() + grace_s
    while time.monotonic() < deadline:
        time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
    if dispatch.pgid == os.getpgrp():
        raise RuntimeError("refusing to signal the current process group")
    try:
        os.killpg(dispatch.pgid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except (PermissionError, OSError) as exc:
        if proc.poll() is None:
            raise RuntimeError("could not finish owned dispatch termination") from exc
    proc.wait(timeout=max(1.0, grace_s))


# ── Durable warm-session manager ─────────────────────────────────────────────
# The ONE home for subscription-agent warm sessions (codex/claude CLI conversation reuse).
# Extracted 2026-06-11 from `agent_repair_worker._get_or_create_session`/`_persist_session`
# — the residual-family factory's PROVEN warm pattern (default-ON in production) — so the
# SOLVER / PLANNER / FORMALIZER dispatch can reuse the SAME code instead of the in-memory
# hand-rolled copy that lived in `agentic_leaf` (#96, non-durable, lost on process exit).
# A warm session is a PERFORMANCE CACHE of the fungible leaf's CLI conversation — NOT a
# special persistent agent identity (leaf fungibility preserved). Keyed by (runtime,
# agent_id) and persisted to disk so the NEXT dispatch (even a fresh process / queue work
# item) RESUMES, and so the leaf's formalize→plan→solve dispatches share ONE warm agent.
SUBSCRIPTION_SESSION_SCHEMA = "leanmill-subscription-agent-session-v1"
DEFAULT_WARM_MAX_TASKS = 20
DEFAULT_WARM_MAX_AGE_S = 6 * 60 * 60

# Hard capability seal for bounded text workers (claude runtime): the briefing is the
# worker's whole world. Added 2026-07-02 after a live unsealed autoresearch mutator
# grepped the repo, read evidence_holdout.txt, and ran the frozen gate_harness.py as a
# local scoring oracle. Codex has no per-tool disallow; its nearest sealed completion
# surface is CODEX_SANDBOX_SEALED_COMPLETION. Visible workbench dispatches use
# CODEX_SANDBOX_VISIBLE_WORKBENCH: local commands may run inside the staged pack,
# while JS/MCP/web stay off and parent-owned gates remain outside the leaf.
SEALED_CLAUDE_DISALLOWED_TOOLS = (
    "Bash", "Read", "Edit", "Write", "Grep", "Glob", "NotebookEdit",
    "WebSearch", "WebFetch", "Task", "Agent",
)


def session_slug(value: str) -> str:
    """Filesystem-safe slug — IDENTICAL to the worker's historical `_slug`, so the existing
    on-disk session files are preserved byte-for-byte across this extraction."""
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in str(value)).strip("_") or "agent"


def warm_session_path(session_dir: str | Path, *, runtime: str, agent_id: str) -> Path:
    return Path(session_dir) / f"{session_slug(runtime)}_{session_slug(agent_id)}.json"


def _read_session_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(errors="ignore"))
    except (json.JSONDecodeError, OSError):
        return {}
    return obj if isinstance(obj, dict) else {}


def get_or_create_warm_session(
    session_dir: str | Path,
    *,
    runtime: str,
    agent_id: str,
    enabled: bool = True,
    warm_max_tasks: int = DEFAULT_WARM_MAX_TASKS,
    warm_max_age_s: int = DEFAULT_WARM_MAX_AGE_S,
    now: int | None = None,
) -> dict[str, Any] | None:
    """Load the durable warm session for (runtime, agent_id), rotating it when STALE
    (>= warm_max_tasks dispatches OR older than warm_max_age_s). Returns None when disabled
    (the caller dispatches COLD). A live, non-stale session is marked `is_new=False` so
    `build_subscription_agent_command` emits a RESUME; a freshly-minted one is `is_new=True`
    (claude gets a new uuid to create; codex emits its own id on first run)."""
    if not enabled:
        return None
    path = warm_session_path(session_dir, runtime=runtime, agent_id=agent_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    state = _read_session_json(path)
    now_epoch = int(time.time() if now is None else now)
    stale = True
    if state.get("session_id") and state.get("started_at_epoch"):
        age_s = now_epoch - int(state.get("started_at_epoch") or now_epoch)
        stale = int(state.get("tick_count") or 0) >= warm_max_tasks or age_s >= warm_max_age_s
    if stale:
        state = {
            "schema": SUBSCRIPTION_SESSION_SCHEMA,
            "runtime": runtime,
            "agent_id": agent_id,
            "session_id": str(uuid.uuid4()) if runtime == "claude" else None,
            "started_at_epoch": now_epoch,
            "last_used_at_epoch": None,
            "tick_count": 0,
            "is_new": True,
            "policy": "session_warm_resume_if_supported",
        }
        path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    else:
        state["is_new"] = False
    state["session_state_path"] = str(path)
    return state


def persist_warm_session(
    session_dir: str | Path,
    *,
    runtime: str,
    agent_id: str,
    session_state: dict[str, Any] | None,
    now: int | None = None,
) -> None:
    """Write `run.final_session_state` back so the NEXT dispatch RESUMES (durable across
    processes / queue work items). No-op on an empty session (i.e. a cold dispatch)."""
    if not session_state:
        return
    path = warm_session_path(session_dir, runtime=runtime, agent_id=agent_id)
    state = {k: v for k, v in dict(session_state).items() if k != "session_state_path"}
    state.setdefault("schema", SUBSCRIPTION_SESSION_SCHEMA)
    state["runtime"] = runtime
    state["agent_id"] = agent_id
    state["is_new"] = False
    state["last_used_at_epoch"] = int(time.time() if now is None else now)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def warm_session_recovery_callbacks(
    session_dir: str | Path,
    *,
    runtime: str,
    agent_id: str,
    warm_max_tasks: int = DEFAULT_WARM_MAX_TASKS,
    warm_max_age_s: int = DEFAULT_WARM_MAX_AGE_S,
) -> "tuple[Callable[[str], None], Callable[[], dict[str, Any]]]":
    """Bind the (invalidate_session, create_replacement_session) callbacks that
    `run_subscription_agent_with_recovery` needs, against the on-disk session — so the
    claude 'session not found' recovery self-heals DURABLY (writes a fresh session, then
    the replacement mints a new one)."""
    def _invalidate(reason: str) -> None:
        persist_warm_session(
            session_dir,
            runtime=runtime,
            agent_id=agent_id,
            session_state={
                "schema": SUBSCRIPTION_SESSION_SCHEMA,
                "runtime": runtime,
                "agent_id": agent_id,
                "session_id": None,
                "is_new": True,
                "invalidated_reason": reason,
                "started_at_epoch": int(time.time()),
                "tick_count": 0,
            },
        )

    def _replacement() -> dict[str, Any]:
        return get_or_create_warm_session(
            session_dir,
            runtime=runtime,
            agent_id=agent_id,
            enabled=True,
            warm_max_tasks=warm_max_tasks,
            warm_max_age_s=warm_max_age_s,
        ) or {}

    return _invalidate, _replacement


def build_subscription_agent_command(
    *,
    runtime: str,
    prompt: str,
    repo: str | Path,
    session_state: dict[str, Any] | None = None,
    codex_model: str | None = None,
    codex_model_env: str = "ZTARE_CODEX_AGENT_MODEL",
    default_codex_model: str = "gpt-5.4-mini",
    codex_sandbox: str = "workspace-write",
    claude_permission_mode: str | None = None,
    claude_disallowed_tools: list[str] | tuple[str, ...] | None = None,
    output_schema: str | Path | None = None,
    output_last_message_path: str | Path | None = None,
) -> list[str]:
    if runtime not in SUPPORTED_SUBSCRIPTION_RUNTIMES:
        raise ValueError(f"unsupported subscription runtime: {runtime}")
    if output_schema is not None and runtime != "codex":
        raise ValueError("output_schema is currently supported only by the Codex runtime")
    if output_last_message_path is not None and runtime != "codex":
        raise ValueError(
            "output_last_message_path is currently supported only by the Codex runtime"
        )
    # ABSOLUTE: `_run_cli` runs with cwd=repo AND codex gets `--cd repo`; a relative repo
    # then DOUBLES (cwd/repo/repo → "No such file or directory"). abspath makes relative→
    # absolute (fixing the doubling) WITHOUT resolving symlinks — so already-absolute paths
    # pass through unchanged (no regression for existing callers).
    repo_path = os.path.abspath(str(repo))
    prompt_argument = "-" if len(prompt.encode("utf-8")) > prompt_inline_max_bytes() else prompt
    # FULL-AUTO (default-on): the agents run on an EXTERNALLY-sandboxed controlled box (the VPS) where the
    # kernel re-verifies every closure and governance catches laundering — so the agent MUST be able to run
    # its own shell loop (warm-Lean check, grep Mathlib, sympy/z3). The prior flags only auto-accepted FILE
    # edits, NOT shell exec: codex `--sandbox workspace-write` blocks escalations (network / out-of-workspace,
    # e.g. the warm-REPL socket at /tmp) with NO human to approve in headless `exec`, and claude `acceptEdits`
    # auto-accepts edits but NOT Bash — so the leaf reported "requires user approval" and degraded to pure
    # reasoning (couldn't iterate/compile/search). codex documents `--dangerously-bypass-approvals-and-sandbox`
    # as the mode for exactly an externally-sandboxed environment; claude's equivalent is `bypassPermissions`.
    # ZTARE_LEANMILL_AGENT_FULL_AUTO=0 reverts to the old approval-gated flags (the A/B baseline).
    _full_auto = os.environ.get("ZTARE_LEANMILL_AGENT_FULL_AUTO", "1") != "0"
    if runtime == "codex":
        model = codex_model or os.environ.get(codex_model_env) or default_codex_model
        # FRIENDLY-ALIAS RESOLUTION (2026-07-03, ONE canonical place): map a friendly model
        # alias ("gpt5.5" → "gpt-5.5") through the same MODEL_MAP the API path uses, so a caller
        # or env var can pass EITHER the alias or the exact CLI id and both reach codex `--model`
        # correctly. Unknown ids and the sentinels ("default"/"account-default") are not in the
        # map, so they pass through unchanged. Lazy+guarded: a model-map lookup must never break
        # command building (mirrors the existing "budget lookup must never break a dispatch").
        if model:
            try:
                from ztare.common.llm_runtime import MODEL_MAP
                model = MODEL_MAP.get(model, model)
            except Exception:  # noqa: BLE001
                pass
        cmd = ["codex", "exec", "--skip-git-repo-check"]
        # Remote MCP is ambient capability, not a default dependency. Bounded
        # subscription workers opt in explicitly when their contract names an
        # MCP surface; every other Codex call avoids plugin/MCP startup drift.
        if os.environ.get("ZTARE_SUBSCRIPTION_AGENT_REMOTE_MCP", "0") != "1":
            cmd += ["-c", "features.rmcp_client=false"]
        if output_schema is not None:
            schema_path = Path(output_schema)
            if not schema_path.is_file():
                raise ValueError(f"output_schema must be a readable file: {schema_path}")
            cmd += ["--output-schema", os.path.abspath(str(schema_path))]
        if output_last_message_path is not None:
            result_path = Path(output_last_message_path)
            result_path.parent.mkdir(parents=True, exist_ok=True)
            cmd += ["--output-last-message", os.path.abspath(str(result_path))]
        # Sentinel models mean "use the account-configured default" — OMIT --model so codex
        # uses the strong default instead of being forced onto a weak pinned model.
        if model and model not in ("default", "account-default", "account_default"):
            cmd += ["--model", model]
        cmd += ["--cd", repo_path]
        # An explicit read-only request is a deliberate CALLER SEAL and must beat the
        # full-auto env default — before this ordering, judge_out_of_loop's read-only
        # seal was silently overridden to full bypass (observed 2026-07-02).
        # HARD SEAL via --disable of every content-pulling tool (2026-07-03): codex --sandbox
        # read-only still EXPOSES agentic tools that let a bounded judge/mutator worker pull
        # unbounded content into context until the turn blows past the model window; auto-
        # compaction then fails ("ran out of room"), the turn yields NO final message, and
        # `codex exec` exits 1 with empty stdout (the observed "subscription judge dispatch
        # failed (returncode=1)"). shell_tool/unified_exec was only HALF the seal: a live judge
        # with those disabled STILL ran the js_repl 104× (analyzing the evidence) → two forced
        # context compactions → turn_aborted (rollout 2026-07-03T23-17-16). The briefing is a
        # bounded worker's whole world, so also disable the js REPL, the remote-MCP client, and
        # web search — making the dispatch a pure single-shot completion regardless of the
        # operator's ~/.codex/config.toml (the seal must not depend on ambient global config).
        # shell_tool/unified_exec are stable CLI feature toggles (`--disable`). The js REPL and the
        # bundled remote-MCP `js` app are NOT `--disable`-able in this CLI (`--disable rmcp_client`
        # errors "Unknown feature flag") — they are config-only `[features]` keys, so kill them via
        # `-c features.<name>=false` (exactly the global-config mitigation, but scoped to THIS
        # dispatch so the seal never depends on ~/.codex/config.toml). web search off via `tools`.
        if codex_sandbox == CODEX_SANDBOX_SEALED_COMPLETION:
            _codex_execution_boundary(cmd, "read-only")
            cmd += [
                "--disable", "shell_tool",
                "--disable", "unified_exec",
                "-c", "features.js_repl=false",
                "-c", "tools.web_search=false",
            ]
        elif codex_sandbox == CODEX_SANDBOX_WEB_RESEARCH:
            # `--search` is a TOP-LEVEL Codex flag (before `exec`), not an
            # exec-subcommand config field. It exposes the native Responses
            # web_search tool without enabling MCP or local execution.
            cmd.insert(1, "--search")
            _codex_execution_boundary(cmd, "read-only")
            cmd += [
                "--disable", "shell_tool",
                "--disable", "unified_exec",
                "-c", "features.js_repl=false",
            ]
        elif codex_sandbox == CODEX_SANDBOX_VISIBLE_WORKBENCH:
            _codex_execution_boundary(cmd, "workspace-write")
            cmd += [
                "-c", "features.js_repl=false",
                "-c", "tools.web_search=false",
            ]
        elif codex_sandbox == CODEX_SANDBOX_LEGACY_READ_ONLY_SHELL:
            # Back-compat spelling. Kept for external callers, but visible workbench
            # should request CODEX_SANDBOX_VISIBLE_WORKBENCH so local preflight commands can run.
            _codex_execution_boundary(cmd, "read-only")
            cmd += [
                "-c", "features.js_repl=false",
                "-c", "tools.web_search=false",
            ]
        elif _full_auto or codex_sandbox in ("danger-full-access", "bypass"):
            cmd.append("--dangerously-bypass-approvals-and-sandbox")
        else:
            cmd += ["--sandbox", codex_sandbox]
        # REASONING EFFORT: mirror the Claude effort override for Codex via scoped config.
        # This is intentionally opt-in; hard-math agents can keep the user's default, while
        # bounded typed-contract workers can run low/medium to avoid 600s high-effort stalls.
        from ztare.common.llm_runtime import subscription_reasoning_effort

        _codex_effort = subscription_reasoning_effort(
            "codex",
            os.environ.get("ZTARE_CODEX_AGENT_REASONING_EFFORT", "low"),
            model=str(model or ""),
        )
        if _codex_effort is not None:
            # Codex CLI config values are passed as key=value. Quoting the scalar
            # value can trip the subscription app-server setup path on macOS
            # ("could not create PATH aliases" / "failed to initialize
            # in-process app-server client"), while the unquoted form is accepted
            # by the CLI and still reports the requested effort.
            cmd += ["-c", f"model_reasoning_effort={_codex_effort}"]
        # RESUME contract (verified against codex-cli 0.142.4, 2026-07-04): `codex exec
        # resume [SESSION_ID] [PROMPT]` takes the prompt as a POSITIONAL arg (help: "Prompt to
        # send after resuming"), so appending it last is correct AND compatible with the runner's
        # stdin=DEVNULL — codex only reads the prompt from stdin when NO positional prompt is
        # given. (The "Reading additional input from stdin..." banner is BENIGN: codex prints it
        # whenever stdin is not a TTY; it appears on successful RC0 fresh runs too — it is NOT the
        # failure signal it looks like.) The seal flags added above apply to BOTH resume + fresh.
        # ESCAPE HATCH: warm sessions are a perf optimization, not correctness — set
        # ZTARE_CODEX_DISABLE_RESUME=1 to force every codex dispatch to run a FRESH session (e.g.
        # if a future codex version breaks `resume` semantics) with no code change or redeploy.
        if (
            os.environ.get("ZTARE_CODEX_DISABLE_RESUME") != "1"
            and session_state
            and session_state.get("session_id")
            and not session_state.get("is_new")
        ):
            cmd.extend(["resume", str(session_state["session_id"])])
            cmd.append(prompt_argument)
            return cmd
        cmd.append(prompt_argument)
        return cmd

    permission_mode = claude_permission_mode or os.environ.get(
        "ZTARE_CLAUDE_PERMISSION_MODE", "bypassPermissions" if _full_auto else "acceptEdits")
    cmd = [
        "claude",
        "--print",
        "--permission-mode",
        permission_mode,
    ]
    # MODEL OVERRIDE (2026-06-12, mirrors the codex ZTARE_CODEX_AGENT_MODEL pattern): unset/sentinel ⇒ OMIT
    # --model (account default — byte-parity with the prior command). Lets an experiment pin the claude lane
    # to a specific model (e.g. a frontier math model) per-run via env, no code change at the call sites.
    _claude_model = os.environ.get("ZTARE_CLAUDE_AGENT_MODEL", "")
    if _claude_model and _claude_model not in ("default", "account-default", "account_default"):
        cmd += ["--model", _claude_model]
    # REASONING EFFORT (2026-06-13): `claude --print` exposes `--effort {low,medium,high,xhigh,max}`. Pin it
    # per-run via ZTARE_CLAUDE_EFFORT for a hard-math campaign (e.g. xhigh on Opus). Unset ⇒ OMIT (account
    # default = byte-parity). Validated against the live CLI's documented levels before wiring.
    from ztare.common.llm_runtime import subscription_reasoning_effort

    _claude_effort = subscription_reasoning_effort(
        "claude", os.environ.get("ZTARE_CLAUDE_EFFORT", "")
    )
    if _claude_effort is not None:
        cmd += ["--effort", _claude_effort]
    if session_state and session_state.get("session_id"):
        if session_state.get("is_new"):
            cmd.extend(["--session-id", str(session_state["session_id"])])
        else:
            cmd.extend(["--resume", str(session_state["session_id"])])
    for tool_name in claude_disallowed_tools or ():
        cmd.extend(["--disallowedTools", str(tool_name)])
    cmd.extend(["-p", prompt_argument])
    return cmd


def subscription_agent_env(runtime: str, base_env: dict[str, str] | None = None) -> dict[str, str]:
    """Return an environment that prefers subscription auth over API keys."""
    if runtime not in SUPPORTED_SUBSCRIPTION_RUNTIMES:
        raise ValueError(f"unsupported subscription runtime: {runtime}")
    env = dict(base_env or os.environ)
    # Parent-runner controls must not leak into the subscription CLI process. In particular,
    # ZTARE_SUBSCRIPTION_AGENT_STREAMING selects our Python execution surface; inherited by
    # Codex on macOS it can trip the app-server startup path before the leaf starts.
    env.pop("ZTARE_SUBSCRIPTION_AGENT_STREAMING", None)
    # CWD-INDEPENDENCE (2026-06-11): the agent subprocess runs with cwd=repo (a SUBDIR, e.g. ztare_proofs/ the
    # lake root), but the runners export a RELATIVE `PYTHONPATH=src` (relative to the repo ROOT). Once the agent
    # `cd`s / runs from the lake subdir, `src` no longer resolves, so its OWN `python -m ztare.formal.lean_check_server`
    # warm-check (and any `python -m ztare.…` tool) fails with `ModuleNotFoundError: No module named 'ztare'` — an
    # iteration the now-shell-enabled leaf wastes recovering (observed live, RUNG A). Absolutize the PYTHONPATH
    # entries HERE (this process's cwd IS the repo root, so abspath resolves correctly) so the path survives the
    # agent's cwd. Idempotent: already-absolute entries pass through unchanged.
    _pp = env.get("PYTHONPATH")
    if _pp:
        env["PYTHONPATH"] = os.pathsep.join(
            (os.path.abspath(p) if (p and not os.path.isabs(p)) else p) for p in _pp.split(os.pathsep))
    if runtime == "codex":
        env.pop("OPENAI_API_KEY", None)
        env.pop("OPENAI_BASE_URL", None)
        env.pop("OPENAI_ORG_ID", None)
    if runtime == "claude":
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("CLAUDE_CODE_USE_BEDROCK", None)
        env.pop("CLAUDE_CODE_USE_VERTEX", None)
    return env


def redact_prompt_command(command: list[str], prompt_ref: str) -> list[str]:
    if not command:
        return []
    return command[:-1] + [prompt_ref]


def extract_subscription_session_id(runtime: str, stdout: str, stderr: str) -> str | None:
    """Extract a CLI conversation/session id when the runtime reports one."""
    text = f"{stdout}\n{stderr}"
    if runtime == "codex":
        match = re.search(r"^\s*session id:\s*([A-Za-z0-9_-]+)\s*$", text, flags=re.IGNORECASE | re.MULTILINE)
        return match.group(1) if match else None
    if runtime == "claude":
        for pattern in (
            r"^\s*session(?:\s+id)?:\s*([A-Za-z0-9_-]+)\s*$",
            r"^\s*conversation(?:\s+id)?:\s*([A-Za-z0-9_-]+)\s*$",
        ):
            match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1)
    return None


def _run_cli_unbudgeted(command: list[str], *, runtime: str, repo: str | Path, timeout_seconds: int,
             idle_timeout_seconds: "int | None" = None,
             stdin_text: str | None = None,
             dispatch_receipt_path: "str | Path | None" = None,
             stdout_path: str = "", stderr_path: str = "") -> subprocess.CompletedProcess[str]:
    """Run the agent CLI in a separately owned process session. #103(3) IDLE/HEARTBEAT KILL (opt-in): with it
    set, stream stdout/stderr and kill only on SILENCE (no output for idle s) — true free-will hang-protection:
    an agent actively producing output is never guillotined mid-thought by an arbitrary wall; a wedged CLI dies
    in idle s. The hard `timeout_seconds` wall still applies (a chatty-but-stuck loop can't run forever). Both
    kill paths return the SAME rc-124 CompletedProcess shape the run() path produces — plus the PARTIAL output
    already streamed (subprocess.run discards it on kill), so a killed dispatch still yields its work-so-far."""
    if idle_timeout_seconds is None:
        proc = subprocess.Popen(
            command,
            cwd=str(Path(repo)),
            env=subscription_agent_env(runtime),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            stdin=subprocess.PIPE if stdin_text is not None else subprocess.DEVNULL,
            start_new_session=True,
        )
        dispatch = _owned_dispatch_for_process(
            proc, command, stdin_text=stdin_text,
            stdout_path=stdout_path, stderr_path=stderr_path
        )
        _write_owned_dispatch_envelope(dispatch_receipt_path, dispatch, status="running")
        try:
            stdout, stderr = proc.communicate(
                input=stdin_text,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            _terminate_owned_process(proc, dispatch)
            stdout, stderr = proc.communicate()
            result = subprocess.CompletedProcess(
                command,
                124,
                stdout=stdout or str(exc.stdout or ""),
                stderr=(stderr or str(exc.stderr or ""))
                + f"\nsubscription agent command timed out after {timeout_seconds}s",
            )
        else:
            result = subprocess.CompletedProcess(command, proc.returncode, stdout=stdout, stderr=stderr)
        _write_owned_dispatch_envelope(
            dispatch_receipt_path, dispatch, status="completed", returncode=result.returncode
        )
        if runtime == "codex" and _codex_needs_tty_recovery(result):
            return _run_cli_with_pty(
                command, runtime=runtime, repo=repo, timeout_seconds=timeout_seconds,
                stdin_text=stdin_text,
                dispatch_receipt_path=dispatch_receipt_path,
                stdout_path=stdout_path, stderr_path=stderr_path,
            )
        return result
    if runtime == "codex":
        return _run_cli_with_pty(
            command,
            runtime=runtime,
            repo=repo,
            timeout_seconds=timeout_seconds,
            idle_timeout_seconds=idle_timeout_seconds,
            stdin_text=stdin_text,
            dispatch_receipt_path=dispatch_receipt_path,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
        )

    import os as _os
    import signal as _signal
    import threading
    import time as _time
    # start_new_session ⇒ the CLI + ALL its children form one process group we can kill TOGETHER. Without it,
    # killing the direct child leaves grandchildren (codex/claude spawn helpers) alive AND holding the pipe —
    # the readline pump never unblocks and the orphan keeps running (caught by the behavioural test: a bash
    # wrapper's `sleep` child held the pipe 10s past the kill).
    proc = subprocess.Popen(command, cwd=str(Path(repo)), env=subscription_agent_env(runtime),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            stdin=subprocess.PIPE if stdin_text is not None else subprocess.DEVNULL,
                            start_new_session=True)

    dispatch = _owned_dispatch_for_process(
        proc, command, stdin_text=stdin_text,
        stdout_path=stdout_path, stderr_path=stderr_path
    )
    _write_owned_dispatch_envelope(dispatch_receipt_path, dispatch, status="running")

    def _kill_group():
        _terminate_owned_process(proc, dispatch)
    out_buf: "list[str]" = []
    err_buf: "list[str]" = []
    last = [_time.monotonic()]   # last-activity clock, bumped by EITHER stream

    def _pump(stream, buf):
        for line in iter(stream.readline, ""):
            buf.append(line)
            last[0] = _time.monotonic()
        stream.close()

    threads = [threading.Thread(target=_pump, args=(proc.stdout, out_buf), daemon=True),
               threading.Thread(target=_pump, args=(proc.stderr, err_buf), daemon=True)]
    for t in threads:
        t.start()
    if stdin_text is not None and proc.stdin is not None:
        proc.stdin.write(stdin_text)
        proc.stdin.close()
    start = _time.monotonic()
    kill_note = ""
    while proc.poll() is None:
        _time.sleep(0.25)
        now = _time.monotonic()
        if now - start > timeout_seconds:
            kill_note = f"\nsubscription agent command timed out after {timeout_seconds}s"
            _kill_group()
            break
        if now - last[0] > idle_timeout_seconds:
            kill_note = (f"\n[idle-kill] no output for {idle_timeout_seconds}s "
                         f"(wall used {int(now - start)}s/{timeout_seconds}s) — killed on SILENCE")
            _kill_group()
            break
    proc.wait()
    for t in threads:
        t.join(timeout=1)   # group-kill closes the pipes; daemon threads — a brief leak is harmless
    rc = 124 if kill_note else proc.returncode
    result = subprocess.CompletedProcess(command, rc, stdout="".join(out_buf), stderr="".join(err_buf) + kill_note)
    _write_owned_dispatch_envelope(
        dispatch_receipt_path, dispatch, status="completed", returncode=result.returncode
    )
    if runtime == "codex" and _codex_needs_tty_recovery(result):
        return _run_cli_with_pty(
            command, runtime=runtime, repo=repo, timeout_seconds=timeout_seconds,
            stdin_text=stdin_text,
            dispatch_receipt_path=dispatch_receipt_path,
            stdout_path=stdout_path, stderr_path=stderr_path,
        )
    return result


def _run_cli(command: list[str], *, runtime: str, repo: str | Path, timeout_seconds: int,
             idle_timeout_seconds: "int | None" = None,
             stdin_text: str | None = None,
             dispatch_receipt_path: "str | Path | None" = None,
             stdout_path: str = "", stderr_path: str = "") -> subprocess.CompletedProcess[str]:
    hooks = _DISPATCH_BUDGET_HOOKS.get()
    reservation = hooks[0](runtime, tuple(command)) if hooks is not None else None
    try:
        return _run_cli_unbudgeted(
            command,
            runtime=runtime,
            repo=repo,
            timeout_seconds=timeout_seconds,
            idle_timeout_seconds=idle_timeout_seconds,
            stdin_text=stdin_text,
            dispatch_receipt_path=dispatch_receipt_path,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
        )
    finally:
        if hooks is not None:
            hooks[1](reservation)


def _codex_needs_tty_recovery(result: subprocess.CompletedProcess[str]) -> bool:
    """Detect the Codex CLI macOS app-server path that fails only when spawned as a pipe-backed child."""
    if result.returncode == 0:
        return False
    text = f"{result.stdout or ''}\n{result.stderr or ''}"
    return (
        "failed to initialize in-process app-server client" in text
        or "could not create PATH aliases" in text
    )


def _run_cli_with_pty(
    command: list[str],
    *,
    runtime: str,
    repo: str | Path,
    timeout_seconds: int,
    idle_timeout_seconds: "int | None" = None,
    stdin_text: str | None = None,
    dispatch_receipt_path: "str | Path | None" = None,
    stdout_path: str = "",
    stderr_path: str = "",
) -> subprocess.CompletedProcess[str]:
    """Run a subscription CLI behind a real PTY.

    Some Codex CLI builds initialize a local app-server differently when stdout/stderr are pipes than when
    they are terminal-backed. The shell path succeeds; the Python child path can fail before the leaf starts.
    This keeps that execution-surface repair in the subscription runtime instead of leaking it into ARC or
    briefing code.
    """
    import pty

    master_fd, slave_fd = pty.openpty()
    proc: subprocess.Popen[bytes] | None = None
    output = bytearray()
    kill_note = ""
    start = time.monotonic()
    last_activity = start
    try:
        proc = subprocess.Popen(
            command,
            cwd=str(Path(repo)),
            env=subscription_agent_env(runtime),
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            start_new_session=True,
            close_fds=True,
        )
        dispatch = _owned_dispatch_for_process(
            proc, command, stdin_text=stdin_text,
            stdout_path=stdout_path, stderr_path=stderr_path
        )
        _write_owned_dispatch_envelope(dispatch_receipt_path, dispatch, status="running")
        os.close(slave_fd)
        slave_fd = -1
        if stdin_text is not None:
            os.write(master_fd, stdin_text.encode("utf-8"))
            # Codex/Claude read a single stdin prompt and terminate at EOF;
            # Ctrl-D is the PTY representation of that EOF boundary.
            os.write(master_fd, b"\x04")
        while proc.poll() is None:
            now = time.monotonic()
            if now - start > timeout_seconds:
                kill_note = f"\nsubscription agent command timed out after {timeout_seconds}s"
                _terminate_owned_process(proc, dispatch)
                break
            if idle_timeout_seconds is not None and now - last_activity > idle_timeout_seconds:
                kill_note = (f"\n[idle-kill] no output for {idle_timeout_seconds}s "
                             f"(wall used {int(now - start)}s/{timeout_seconds}s) — killed on SILENCE")
                _terminate_owned_process(proc, dispatch)
                break
            ready, _, _ = select.select([master_fd], [], [], 0.25)
            if ready:
                try:
                    chunk = os.read(master_fd, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                output.extend(chunk)
                last_activity = time.monotonic()
        if proc is not None:
            proc.wait(timeout=2)
        while True:
            ready, _, _ = select.select([master_fd], [], [], 0)
            if not ready:
                break
            try:
                chunk = os.read(master_fd, 65536)
            except OSError:
                break
            if not chunk:
                break
            output.extend(chunk)
    finally:
        if slave_fd >= 0:
            try:
                os.close(slave_fd)
            except OSError:
                pass
        try:
            os.close(master_fd)
        except OSError:
            pass
    decoded = output.decode(errors="replace")
    rc = 124 if kill_note else (proc.returncode if proc is not None else 1)
    stderr = "[tty-recovery] recovered Codex CLI pipe-backed app-server startup\n" if rc == 0 else ""
    if proc is not None:
        _write_owned_dispatch_envelope(
            dispatch_receipt_path, dispatch, status="completed", returncode=rc
        )
    return subprocess.CompletedProcess(command, rc, stdout=decoded, stderr=stderr + kill_note)


def note_subscription_session_result(
    *,
    runtime: str,
    session_state: dict[str, Any] | None,
    result: subprocess.CompletedProcess[str],
) -> dict[str, Any] | None:
    """Return updated session metadata after one subscription-agent run."""
    state = dict(session_state or {})
    extracted = extract_subscription_session_id(runtime, result.stdout or "", result.stderr or "")
    if extracted:
        state["session_id"] = extracted
    if not state.get("session_id"):
        return session_state
    state["runtime"] = runtime
    state["is_new"] = False
    state["tick_count"] = int(state.get("tick_count") or 0) + 1
    return state


def _is_transient_subscription_capacity_error(result: subprocess.CompletedProcess[str]) -> bool:
    text = f"{result.stdout or ''}\n{result.stderr or ''}".lower()
    return (
        result.returncode != 0
        and (
            "selected model is at capacity" in text
            or "model is at capacity" in text
            or "server is overloaded" in text
            or "temporarily unavailable" in text
        )
    )


def _transient_capacity_retry_budget() -> tuple[int, float]:
    attempts_raw = os.environ.get("ZTARE_SUBSCRIPTION_TRANSIENT_RETRIES", "1")
    delay_raw = os.environ.get("ZTARE_SUBSCRIPTION_TRANSIENT_RETRY_DELAY_S", "10")
    try:
        attempts = max(0, int(attempts_raw))
    except ValueError:
        attempts = 1
    try:
        delay = max(0.0, float(delay_raw))
    except ValueError:
        delay = 10.0
    return attempts, delay


def idle_seconds_for_runtime(runtime: str) -> "int | None":
    """Output-IDLE kill budget for a dispatch, or None (no idle kill).

    Streaming idle-kill is useful for deliberately long Codex dispatches, but
    the threaded streaming runner can trip Codex CLI's subscription app-server
    setup on macOS before the worker starts. Keep the stable non-streaming
    subprocess path as the default; opt into streaming with
    ZTARE_SUBSCRIPTION_AGENT_STREAMING=1.
    """
    if os.environ.get("ZTARE_SUBSCRIPTION_AGENT_STREAMING", "") != "1":
        return None
    if runtime != "codex":
        return None
    try:
        from ztare.common.timeouts import timeout_s
        _v = int(timeout_s("agent_idle"))
        return _v if _v > 0 else None
    except Exception:  # noqa: BLE001 — budget lookup must never break a dispatch; fall back to no idle kill
        return None


def run_subscription_agent_with_recovery(
    *,
    runtime: str,
    prompt: str,
    agent_id: str,
    repo: str | Path,
    session_state: dict[str, Any] | None,
    timeout_seconds: int,
    invalidate_session: Callable[[str], None] | None = None,
    create_replacement_session: Callable[[], dict[str, Any]] | None = None,
    codex_model_env: str = "ZTARE_CODEX_AGENT_MODEL",
    default_codex_model: str = "gpt-5.4-mini",
    codex_sandbox: str = "workspace-write",
    claude_disallowed_tools: list[str] | tuple[str, ...] | None = None,
    output_schema: str | Path | None = None,
    output_last_message_path: str | Path | None = None,
    dispatch_receipt_path: str | Path | None = None,
    stdout_path: str = "",
    stderr_path: str = "",
) -> SubscriptionAgentRun:
    initial_command = build_subscription_agent_command(
        runtime=runtime,
        prompt=prompt,
        repo=repo,
        session_state=session_state,
        codex_model_env=codex_model_env,
        default_codex_model=default_codex_model,
        codex_sandbox=codex_sandbox,
        claude_disallowed_tools=claude_disallowed_tools,
        output_schema=output_schema,
        output_last_message_path=output_last_message_path,
    )
    initial_stdin_text = prompt if initial_command and initial_command[-1] == "-" else None
    _idle = idle_seconds_for_runtime(runtime)
    result = _run_cli(initial_command, runtime=runtime, repo=repo, timeout_seconds=timeout_seconds,
                      idle_timeout_seconds=_idle, stdin_text=initial_stdin_text,
                      dispatch_receipt_path=dispatch_receipt_path,
                      stdout_path=stdout_path, stderr_path=stderr_path)
    recovery_note: str | None = None
    transient_retries, transient_delay = _transient_capacity_retry_budget()
    for attempt in range(1, transient_retries + 1):
        if not _is_transient_subscription_capacity_error(result):
            break
        if transient_delay:
            time.sleep(transient_delay)
        recovery_note = (
            f"{runtime} transient capacity error; retried same command "
            f"{attempt}/{transient_retries}"
        )
        result = _run_cli(initial_command, runtime=runtime, repo=repo, timeout_seconds=timeout_seconds,
                          idle_timeout_seconds=_idle, stdin_text=initial_stdin_text,
                          dispatch_receipt_path=dispatch_receipt_path,
                          stdout_path=stdout_path, stderr_path=stderr_path)
    final_session_state = note_subscription_session_result(
        runtime=runtime,
        session_state=session_state,
        result=result,
    )
    final_command = initial_command
    if (
        runtime == "claude"
        and session_state
        and result.returncode != 0
        and "No conversation found with session ID" in result.stderr
        and invalidate_session is not None
        and create_replacement_session is not None
    ):
        invalidate_session("claude_resume_session_not_found")
        replacement_session_state = create_replacement_session()
        final_command = build_subscription_agent_command(
            runtime=runtime,
            prompt=prompt,
            repo=repo,
            session_state=replacement_session_state,
            codex_model_env=codex_model_env,
            default_codex_model=default_codex_model,
            codex_sandbox=codex_sandbox,
            claude_disallowed_tools=claude_disallowed_tools,
            output_schema=output_schema,
            output_last_message_path=output_last_message_path,
        )
        recovery_note = f"invalid {runtime} resume session for {agent_id}; retried once with a fresh session id"
        result = _run_cli(final_command, runtime=runtime, repo=repo, timeout_seconds=timeout_seconds,
                          idle_timeout_seconds=_idle,
                          stdin_text=prompt if final_command and final_command[-1] == "-" else None,
                          dispatch_receipt_path=dispatch_receipt_path,
                          stdout_path=stdout_path, stderr_path=stderr_path)
        final_session_state = note_subscription_session_result(
            runtime=runtime,
            session_state=replacement_session_state,
            result=result,
        )
    return SubscriptionAgentRun(
        result=result,
        final_session_state=final_session_state,
        initial_command=initial_command,
        final_command=final_command,
        recovery_note=recovery_note,
    )


def _self_test() -> int:
    repo = Path("/tmp/repo")
    codex = build_subscription_agent_command(runtime="codex", prompt="hi", repo=repo)
    assert codex[:4] == ["codex", "exec", "--skip-git-repo-check", "--model"], codex
    assert "--cd" in codex and str(repo) in codex, codex
    codex_resumed = build_subscription_agent_command(
        runtime="codex",
        prompt="hi",
        repo=repo,
        session_state={"session_id": "s", "is_new": False},
    )
    # FULL-AUTO default-on: codex gets the bypass flag (NOT --sandbox), claude gets bypassPermissions — so the
    # leaf can actually run its shell loop on the externally-sandboxed box. ZTARE_LEANMILL_AGENT_FULL_AUTO=0 reverts.
    assert "--cd" in codex_resumed and "resume" in codex_resumed, codex_resumed
    assert "--dangerously-bypass-approvals-and-sandbox" in codex_resumed and "--sandbox" not in codex_resumed, codex_resumed
    # RESUME argv/stdin CONTRACT (codex-cli 0.142.4): the prompt MUST be the trailing positional
    # right after `resume <session_id>` — codex reads the prompt from stdin ONLY when no positional
    # prompt is given, so this trailing-positional shape is exactly what makes the runner's
    # stdin=DEVNULL correct for a resumed session (not the suspected failure).
    _ri = codex_resumed.index("resume")
    assert codex_resumed[_ri:] == ["resume", "s", "hi"], codex_resumed
    # ESCAPE HATCH: ZTARE_CODEX_DISABLE_RESUME=1 forces a FRESH session (no `resume` subcommand)
    # while KEEPING the seal/flags — warm sessions are an optimization, correctness first.
    _pdr = os.environ.get("ZTARE_CODEX_DISABLE_RESUME")
    os.environ["ZTARE_CODEX_DISABLE_RESUME"] = "1"
    try:
        codex_noresume = build_subscription_agent_command(
            runtime="codex", prompt="hi", repo=repo,
            session_state={"session_id": "s", "is_new": False})
        assert "resume" not in codex_noresume and codex_noresume[-1] == "hi", codex_noresume
        assert "--cd" in codex_noresume, codex_noresume
    finally:
        os.environ.pop("ZTARE_CODEX_DISABLE_RESUME", None) if _pdr is None \
            else os.environ.__setitem__("ZTARE_CODEX_DISABLE_RESUME", _pdr)
    # HARD SEAL: a read-only request must pin --sandbox read-only AND disable the shell tools so the
    # bounded worker can't exec/read the repo (and can't blow the context window into a returncode=1).
    codex_sealed = build_subscription_agent_command(
        runtime="codex", prompt="hi", repo=repo, codex_sandbox=CODEX_SANDBOX_SEALED_COMPLETION)
    assert codex_sealed[-1] == "hi", codex_sealed
    assert "--sandbox" in codex_sealed and "read-only" in codex_sealed, codex_sealed
    # A bounded worker gets EVERY content-pulling tool disabled, not just the shell — otherwise it
    # balloons context via js_repl/web_search/MCP and the turn overflows into a returncode=1.
    # shell_tool/unified_exec via CLI --disable; the MCP/js/web tools via -c config overrides.
    assert codex_sealed.count("--disable") == 2, codex_sealed
    for _t in ("shell_tool", "unified_exec"):
        assert _t in codex_sealed, (_t, codex_sealed)
    for _kv in ("features.js_repl=false", "features.rmcp_client=false", "tools.web_search=false"):
        assert _kv in codex_sealed, (_kv, codex_sealed)
    assert "--dangerously-bypass-approvals-and-sandbox" not in codex_sealed, codex_sealed
    # VISIBLE WORKBENCH: local preflight tools need command execution and scratch space,
    # but not JS/MCP/web or hidden authority. Keep it inside the staged workspace.
    codex_visible = build_subscription_agent_command(
        runtime="codex", prompt="hi", repo=repo, codex_sandbox=CODEX_SANDBOX_VISIBLE_WORKBENCH)
    assert "--sandbox" in codex_visible and "workspace-write" in codex_visible, codex_visible
    assert "shell_tool" not in codex_visible and "unified_exec" not in codex_visible, codex_visible
    for _kv in ("features.js_repl=false", "features.rmcp_client=false", "tools.web_search=false"):
        assert _kv in codex_visible, (_kv, codex_visible)
    # POST-FREEZE RESEARCH: native web search is explicit while shell, JS, and
    # remote MCP stay sealed. This cannot leak ambient repo or plugin tools.
    codex_web = build_subscription_agent_command(
        runtime="codex", prompt="hi", repo=repo, codex_sandbox=CODEX_SANDBOX_WEB_RESEARCH)
    assert codex_web[:3] == ["codex", "--search", "exec"], codex_web
    assert "read-only" in codex_web, codex_web
    assert "features.rmcp_client=false" in codex_web, codex_web
    for _t in ("shell_tool", "unified_exec"):
        assert _t in codex_web, (_t, codex_web)
    # FRIENDLY-ALIAS → CLI id in the ONE builder: "gpt5.5" resolves to "gpt-5.5"; an exact id and a
    # sentinel pass through (sentinel ⇒ --model omitted so codex uses the account default).
    codex_alias = build_subscription_agent_command(runtime="codex", prompt="hi", repo=repo, codex_model="gpt5.5")
    assert codex_alias[codex_alias.index("--model") + 1] == "gpt-5.5", codex_alias
    codex_exact = build_subscription_agent_command(runtime="codex", prompt="hi", repo=repo, codex_model="gpt-5.5")
    assert codex_exact[codex_exact.index("--model") + 1] == "gpt-5.5", codex_exact
    assert "--model" not in build_subscription_agent_command(
        runtime="codex", prompt="hi", repo=repo, codex_model="account-default"), "sentinel must omit --model"
    _pcodex_effort = os.environ.get("ZTARE_CODEX_AGENT_REASONING_EFFORT")
    try:
        os.environ["ZTARE_CODEX_AGENT_REASONING_EFFORT"] = "low"
        codex_low = build_subscription_agent_command(runtime="codex", prompt="hi", repo=repo)
        assert "model_reasoning_effort=low" in codex_low, codex_low
        os.environ["ZTARE_CODEX_AGENT_REASONING_EFFORT"] = "bogus"
        assert not any("model_reasoning_effort" in part for part in build_subscription_agent_command(runtime="codex", prompt="hi", repo=repo))
    finally:
        if _pcodex_effort is None:
            os.environ.pop("ZTARE_CODEX_AGENT_REASONING_EFFORT", None)
        else:
            os.environ["ZTARE_CODEX_AGENT_REASONING_EFFORT"] = _pcodex_effort
    _prev = os.environ.get("ZTARE_LEANMILL_AGENT_FULL_AUTO")
    os.environ["ZTARE_LEANMILL_AGENT_FULL_AUTO"] = "0"
    try:
        codex_gated = build_subscription_agent_command(runtime="codex", prompt="hi", repo=repo)
        assert "--sandbox" in codex_gated and "--dangerously-bypass-approvals-and-sandbox" not in codex_gated, codex_gated
        claude_gated = build_subscription_agent_command(runtime="claude", prompt="hi", repo=repo)
        assert "acceptEdits" in claude_gated, claude_gated
    finally:
        if _prev is None:
            os.environ.pop("ZTARE_LEANMILL_AGENT_FULL_AUTO", None)
        else:
            os.environ["ZTARE_LEANMILL_AGENT_FULL_AUTO"] = _prev
    resumed = build_subscription_agent_command(
        runtime="claude",
        prompt="hi",
        repo=repo,
        session_state={"session_id": "s", "is_new": False},
        claude_disallowed_tools=("Bash", "Read"),
    )
    assert "--resume" in resumed, resumed
    assert "bypassPermissions" in resumed, resumed
    assert resumed.count("--disallowedTools") == 2, resumed
    # --effort + --model (2026-06-13): both pinned per-run via env; valid level ⇒ appended, unset/garbage ⇒
    # omitted (parity). Model + effort compose (Opus xhigh).
    _peff, _pmod = os.environ.get("ZTARE_CLAUDE_EFFORT"), os.environ.get("ZTARE_CLAUDE_AGENT_MODEL")
    try:
        os.environ["ZTARE_CLAUDE_EFFORT"] = "xhigh"
        os.environ["ZTARE_CLAUDE_AGENT_MODEL"] = "claude-opus-4-8"
        c_eff = build_subscription_agent_command(runtime="claude", prompt="hi", repo=repo)
        assert c_eff[c_eff.index("--effort") + 1] == "xhigh", c_eff
        assert c_eff[c_eff.index("--model") + 1] == "claude-opus-4-8", c_eff
        os.environ["ZTARE_CLAUDE_EFFORT"] = "bogus"
        assert "--effort" not in build_subscription_agent_command(runtime="claude", prompt="hi", repo=repo)
        os.environ.pop("ZTARE_CLAUDE_EFFORT", None)
        assert "--effort" not in build_subscription_agent_command(runtime="claude", prompt="hi", repo=repo)
    finally:
        for _k, _v in (("ZTARE_CLAUDE_EFFORT", _peff), ("ZTARE_CLAUDE_AGENT_MODEL", _pmod)):
            os.environ.pop(_k, None) if _v is None else os.environ.__setitem__(_k, _v)
    env = subscription_agent_env("codex", {"OPENAI_API_KEY": "x", "KEEP": "y"})
    assert "OPENAI_API_KEY" not in env and env["KEEP"] == "y"
    # PYTHONPATH absolutized (cwd-independence for the agent's `python -m ztare.…` tool calls); abs entries unchanged
    _penv = subscription_agent_env("codex", {"PYTHONPATH": f"src{os.pathsep}/already/abs"})
    _parts = _penv["PYTHONPATH"].split(os.pathsep)
    assert os.path.isabs(_parts[0]) and _parts[0].endswith(f"{os.sep}src") and _parts[1] == "/already/abs", _penv["PYTHONPATH"]
    env = subscription_agent_env("claude", {"ANTHROPIC_API_KEY": "x", "ANTHROPIC_AUTH_TOKEN": "token", "KEEP": "y"})
    assert "ANTHROPIC_API_KEY" not in env and env["ANTHROPIC_AUTH_TOKEN"] == "token" and env["KEEP"] == "y"
    assert extract_subscription_session_id("codex", "", "session id: abc_123") == "abc_123"
    assert extract_subscription_session_id("claude", "not a session id: nope", "") is None
    updated = note_subscription_session_result(
        runtime="codex",
        session_state=None,
        result=subprocess.CompletedProcess(["codex"], 0, stdout="", stderr="session id: s1"),
    )
    assert updated and updated["session_id"] == "s1" and updated["tick_count"] == 1
    print("subscription_agent_runtime self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    print(json.dumps({"supported_runtimes": sorted(SUPPORTED_SUBSCRIPTION_RUNTIMES)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
