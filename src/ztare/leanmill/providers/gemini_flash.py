"""Gemini Flash prover — delegates to `ztare.common.llm_runtime.LLMRuntime`.

The unified `LLMRuntime.call_text()` handles model resolution, fallback chains,
retries, transient-error detection, and timeout. Provider wrapper just maps
its exceptions to typed `ProviderError`.
"""
from __future__ import annotations

import os
import time

from ztare.leanmill.providers.base import Provider, ProviderError, ProviderResult


_LEAN_PROMPT_TEMPLATE = (
    "You are a Lean 4 theorem prover. Produce ONLY the Lean proof term or "
    "tactic block that closes this goal. No prose, no markdown fence, no "
    "explanations.\n\nGoal:\n{goal}"
)


def _classify(exc: Exception | None, stdout: str) -> tuple[ProviderError, str | None]:
    if exc is None and stdout.strip():
        return ProviderError.none, None
    if exc is None:
        return ProviderError.malformed, "empty stdout"
    msg = str(exc).lower()
    if "rate" in msg or "429" in msg or "quota" in msg:
        return ProviderError.rate_limited, str(exc)
    if "auth" in msg or "api key" in msg or "unauthorized" in msg:
        return ProviderError.auth_missing, str(exc)
    if "timeout" in msg or "timed out" in msg:
        return ProviderError.timeout, str(exc)
    if any(c in msg for c in ("500", "502", "503", "504", "unavailable")):
        return ProviderError.upstream_5xx, str(exc)
    return ProviderError.other, str(exc)


class GeminiFlashProvider(Provider):
    name = "gemini_flash"
    capability = "gemini_api"

    def __init__(self, model_id: str = "gemini-2.5-flash") -> None:
        self.model_id = model_id

    def _available(self) -> tuple[bool, str | None]:
        if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
            return False, "GEMINI_API_KEY / GOOGLE_API_KEY not set"
        return True, None

    def _invoke(self, goal_text: str, timeout_s: int) -> ProviderResult:
        from ztare.common.llm_runtime import LLMRuntime  # lazy import

        prompt = _LEAN_PROMPT_TEMPLATE.format(goal=goal_text)
        start = time.time()
        stdout = ""
        exc: Exception | None = None
        try:
            resp = LLMRuntime().call_text(
                prompt,
                model_id=self.model_id,
                timeout_seconds=timeout_s,
                request_label=f"leanmill::solver::gemini::{self.model_id}",
                max_tokens=16384  # was 2048 — truncated real Lean proofs (foot-gun fix),
            )
            stdout = getattr(resp, "text", "") or ""
        except Exception as e:
            exc = e
        wall = time.time() - start

        err, detail = _classify(exc, stdout)
        return ProviderResult(
            provider=self.name,
            proof_text=stdout.strip() if err == ProviderError.none else None,
            error=err,
            error_detail=detail,
            wallclock_s=round(wall, 2),
            raw_stdout_excerpt=stdout[:400] if stdout else None,
            extra={"model_id": self.model_id, "via": "ztare.common.llm_runtime.LLMRuntime.call_text"},
        )
