"""Codex GPT-5 prover — subscription path via subscription_agent_runtime.

Mirrors `claude_opus.py`. Uses the same `codex` CLI subscription that the v28
dispatcher and the leanmill agent_repair_worker use. Credit-exhausted is
detected as a typed error rather than passed through as proof text.
"""
from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

from ztare.leanmill.providers.base import Provider, ProviderError, ProviderResult

_CREDIT_PATTERNS = (
    "credit balance is too low",
    "insufficient credits",
    "out of credit",
    "quota exceeded",
)
_AUTH_PATTERNS = (
    "not logged in",
    "please run `codex login`",
    "codex login",
    "unauthorized",
    "authentication required",
)
_RATE_PATTERNS = (
    "rate limit",
    "too many requests",
    "429",
)

_LEAN_PROMPT_TEMPLATE = (
    "You are a Lean 4 theorem prover. Produce ONLY the Lean proof term or "
    "tactic block that closes this goal. No prose, no markdown fence, no "
    "explanations.\n\nGoal:\n{goal}"
)


class CodexGpt5Provider(Provider):
    name = "codex_gpt5"
    capability = "codex_subscription"

    def __init__(self, model: str = "gpt-5.5") -> None:
        self.model = model

    def _available(self) -> tuple[bool, str | None]:
        if shutil.which("codex") is None:
            return False, "codex CLI not found on PATH"
        return True, None

    def _invoke(self, goal_text: str, timeout_s: int) -> ProviderResult:
        repo = Path(__file__).resolve().parents[4]
        if str(repo) not in sys.path:
            sys.path.insert(0, str(repo))
        from ztare.common.subscription_agent_runtime import (  # type: ignore
            run_subscription_agent_with_recovery,
        )

        prompt = _LEAN_PROMPT_TEMPLATE.format(goal=goal_text)
        start = time.time()
        stdout: str = ""
        stderr: str = ""
        err: ProviderError = ProviderError.none
        err_detail: str | None = None
        try:
            run = run_subscription_agent_with_recovery(
                runtime="codex",
                prompt=prompt,
                agent_id=f"leanmill::solver_lane::codex_gpt5::{self.model}",
                repo=repo,
                session_state=None,
                timeout_seconds=timeout_s,
                default_codex_model=self.model,
            )
            stdout = (getattr(run.result, "stdout", "") or "") if run else ""
            stderr = (getattr(run.result, "stderr", "") or "") if run else ""
        except Exception as exc:
            err = ProviderError.other
            err_detail = repr(exc)

        wall = time.time() - start
        haystack = f"{stdout}\n{stderr}".lower()

        if err == ProviderError.none:
            if any(pat in haystack for pat in _CREDIT_PATTERNS):
                err = ProviderError.credit_exhausted
                err_detail = "codex subscription credit exhausted on this node"
            elif any(pat in haystack for pat in _AUTH_PATTERNS):
                err = ProviderError.auth_missing
                err_detail = "codex CLI not authenticated on this node"
            elif any(pat in haystack for pat in _RATE_PATTERNS):
                err = ProviderError.rate_limited
                err_detail = "codex rate limit hit"
            elif not stdout.strip():
                err = ProviderError.malformed
                err_detail = "empty stdout"

        proof_text = stdout.strip() if err == ProviderError.none else None

        return ProviderResult(
            provider=self.name,
            proof_text=proof_text,
            error=err,
            error_detail=err_detail,
            wallclock_s=round(wall, 2),
            raw_stdout_excerpt=stdout[:400] if stdout else None,
            raw_stderr_excerpt=stderr[:400] if stderr else None,
            extra={"model": self.model},
        )
