"""Subscription-backed Codex/Claude agent runtime helpers.

This module is for interactive agent CLIs authenticated by the operator's
subscription, not API-backed LLM calls. API LLM calls belong in
`src.ztare.common.llm_runtime`.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


SUPPORTED_SUBSCRIPTION_RUNTIMES = {"codex", "claude"}


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
) -> list[str]:
    if runtime not in SUPPORTED_SUBSCRIPTION_RUNTIMES:
        raise ValueError(f"unsupported subscription runtime: {runtime}")
    # ABSOLUTE: `_run_cli` runs with cwd=repo AND codex gets `--cd repo`; a relative repo
    # then DOUBLES (cwd/repo/repo → "No such file or directory"). abspath makes relative→
    # absolute (fixing the doubling) WITHOUT resolving symlinks — so already-absolute paths
    # pass through unchanged (no regression for existing callers).
    repo_path = os.path.abspath(str(repo))
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
        cmd = ["codex", "exec", "--skip-git-repo-check"]
        # Sentinel models mean "use the account-configured default" — OMIT --model so codex
        # uses the strong default instead of being forced onto a weak pinned model.
        if model and model not in ("default", "account-default", "account_default"):
            cmd += ["--model", model]
        cmd += ["--cd", repo_path]
        if _full_auto or codex_sandbox in ("danger-full-access", "bypass"):
            cmd.append("--dangerously-bypass-approvals-and-sandbox")
        else:
            cmd += ["--sandbox", codex_sandbox]
        if session_state and session_state.get("session_id") and not session_state.get("is_new"):
            cmd.extend(["resume", str(session_state["session_id"])])
            cmd.append(prompt)
            return cmd
        cmd.append(prompt)
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
    _claude_effort = os.environ.get("ZTARE_CLAUDE_EFFORT", "").strip().lower()
    if _claude_effort in ("low", "medium", "high", "xhigh", "max"):
        cmd += ["--effort", _claude_effort]
    if session_state and session_state.get("session_id"):
        if session_state.get("is_new"):
            cmd.extend(["--session-id", str(session_state["session_id"])])
        else:
            cmd.extend(["--resume", str(session_state["session_id"])])
    for tool_name in claude_disallowed_tools or ():
        cmd.extend(["--disallowedTools", str(tool_name)])
    cmd.extend(["-p", prompt])
    return cmd


def subscription_agent_env(runtime: str, base_env: dict[str, str] | None = None) -> dict[str, str]:
    """Return an environment that prefers subscription auth over API keys."""
    if runtime not in SUPPORTED_SUBSCRIPTION_RUNTIMES:
        raise ValueError(f"unsupported subscription runtime: {runtime}")
    env = dict(base_env or os.environ)
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


def _run_cli(command: list[str], *, runtime: str, repo: str | Path, timeout_seconds: int,
             idle_timeout_seconds: "int | None" = None) -> subprocess.CompletedProcess[str]:
    """Run the agent CLI. `idle_timeout_seconds=None` (every existing caller) ⇒ the original subprocess.run
    path, byte-identical — ZERO regression on the shared dispatch. #103(3) IDLE/HEARTBEAT KILL (opt-in): with it
    set, stream stdout/stderr and kill only on SILENCE (no output for idle s) — true free-will hang-protection:
    an agent actively producing output is never guillotined mid-thought by an arbitrary wall; a wedged CLI dies
    in idle s. The hard `timeout_seconds` wall still applies (a chatty-but-stuck loop can't run forever). Both
    kill paths return the SAME rc-124 CompletedProcess shape the run() path produces — plus the PARTIAL output
    already streamed (subprocess.run discards it on kill), so a killed dispatch still yields its work-so-far."""
    if idle_timeout_seconds is None:
        try:
            return subprocess.run(
                command,
                cwd=str(Path(repo)),
                env=subscription_agent_env(runtime),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired as exc:
            return subprocess.CompletedProcess(
                command,
                124,
                stdout=str(exc.stdout or ""),
                stderr=(str(exc.stderr or "") + f"\nsubscription agent command timed out after {timeout_seconds}s"),
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
                            stdin=subprocess.DEVNULL, start_new_session=True)

    def _kill_group():
        try:
            _os.killpg(_os.getpgid(proc.pid), _signal.SIGKILL)   # the whole group: CLI + helpers
        except (ProcessLookupError, PermissionError, OSError):
            proc.kill()   # group already gone / unsupported → direct kill fallback
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
    return subprocess.CompletedProcess(command, rc, stdout="".join(out_buf), stderr="".join(err_buf) + kill_note)


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


def idle_seconds_for_runtime(runtime: str) -> "int | None":
    """Output-IDLE kill budget for a dispatch, or None (no idle kill). CODEX ONLY: `codex exec` STREAMS
    (reasoning + exec lines), so prolonged silence is a hang signal; `claude --print` BUFFERS everything
    until the final message — an idle kill there would FALSELY kill every long dispatch. Budget from the
    central factory (`agent_idle`, ZTARE_LEANMILL_AGENT_IDLE_S; =0 disables). The safety prerequisite for
    LONG consolidated dispatches (#103/#117): a hung CLI stops costing its whole wallclock budget."""
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
    )
    _idle = idle_seconds_for_runtime(runtime)
    result = _run_cli(initial_command, runtime=runtime, repo=repo, timeout_seconds=timeout_seconds,
                      idle_timeout_seconds=_idle)
    recovery_note: str | None = None
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
        )
        recovery_note = f"invalid {runtime} resume session for {agent_id}; retried once with a fresh session id"
        result = _run_cli(final_command, runtime=runtime, repo=repo, timeout_seconds=timeout_seconds,
                          idle_timeout_seconds=_idle)
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
