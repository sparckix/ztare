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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


SUPPORTED_SUBSCRIPTION_RUNTIMES = {"codex", "claude"}


@dataclass(frozen=True)
class SubscriptionAgentRun:
    result: subprocess.CompletedProcess[str]
    final_session_state: dict[str, Any] | None
    initial_command: list[str]
    final_command: list[str]
    recovery_note: str | None = None


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
    repo_path = str(Path(repo))
    if runtime == "codex":
        model = codex_model or os.environ.get(codex_model_env) or default_codex_model
        cmd = [
            "codex",
            "exec",
            "--skip-git-repo-check",
            "--model",
            model,
            "--cd",
            repo_path,
            "--sandbox",
            codex_sandbox,
        ]
        if session_state and session_state.get("session_id") and not session_state.get("is_new"):
            cmd.extend(["resume", str(session_state["session_id"])])
            cmd.append(prompt)
            return cmd
        cmd.append(prompt)
        return cmd

    permission_mode = claude_permission_mode or os.environ.get("ZTARE_CLAUDE_PERMISSION_MODE", "acceptEdits")
    cmd = [
        "claude",
        "--print",
        "--permission-mode",
        permission_mode,
    ]
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
    if runtime == "codex":
        env.pop("OPENAI_API_KEY", None)
        env.pop("OPENAI_BASE_URL", None)
        env.pop("OPENAI_ORG_ID", None)
    if runtime == "claude":
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("ANTHROPIC_AUTH_TOKEN", None)
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


def _run_cli(command: list[str], *, runtime: str, repo: str | Path, timeout_seconds: int) -> subprocess.CompletedProcess[str]:
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
    result = _run_cli(initial_command, runtime=runtime, repo=repo, timeout_seconds=timeout_seconds)
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
        result = _run_cli(final_command, runtime=runtime, repo=repo, timeout_seconds=timeout_seconds)
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
    assert "--cd" in codex_resumed and "--sandbox" in codex_resumed and "resume" in codex_resumed, codex_resumed
    resumed = build_subscription_agent_command(
        runtime="claude",
        prompt="hi",
        repo=repo,
        session_state={"session_id": "s", "is_new": False},
        claude_disallowed_tools=("Bash", "Read"),
    )
    assert "--resume" in resumed, resumed
    assert resumed.count("--disallowedTools") == 2, resumed
    env = subscription_agent_env("codex", {"OPENAI_API_KEY": "x", "KEEP": "y"})
    assert "OPENAI_API_KEY" not in env and env["KEEP"] == "y"
    env = subscription_agent_env("claude", {"ANTHROPIC_API_KEY": "x", "KEEP": "y"})
    assert "ANTHROPIC_API_KEY" not in env and env["KEEP"] == "y"
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
