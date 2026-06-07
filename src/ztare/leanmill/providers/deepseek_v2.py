"""DeepSeek prover — delegates to `ztare.common.llm_runtime.LLMRuntime`."""
from __future__ import annotations

import os
import time

from ztare.leanmill.providers.base import Provider, ProviderError, ProviderResult
from ztare.leanmill.providers.gemini_flash import _classify  # reuse error mapping


_LEAN_PROMPT_TEMPLATE = (
    "You are a Lean 4 theorem prover. Produce ONLY the Lean proof term or "
    "tactic block that closes this goal. No prose, no markdown fence, no "
    "explanations.\n\nGoal:\n{goal}"
)


class DeepseekV2Provider(Provider):
    name = "deepseek_v2"
    capability = "deepseek_api"

    def __init__(self, model_id: str = "deepseek-chat") -> None:
        self.model_id = model_id

    def _available(self) -> tuple[bool, str | None]:
        if not os.environ.get("DEEPSEEK_API_KEY"):
            return False, "DEEPSEEK_API_KEY not set"
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
                request_label=f"leanmill::solver::deepseek::{self.model_id}",
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
