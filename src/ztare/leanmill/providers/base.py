"""Typed provider base — the typed-result contract every prover wrapper obeys."""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProviderError(str, Enum):
    """Typed provider failure modes. The bash wrappers conflated all of these
    with "proof text"; the solver lane now branches on them."""

    none = "none"
    credit_exhausted = "credit_exhausted"
    rate_limited = "rate_limited"
    timeout = "timeout"
    auth_missing = "auth_missing"        # subscription not logged in / API key absent
    binary_not_found = "binary_not_found"  # CLI not on PATH for this node
    malformed = "malformed"                # provider returned junk / empty
    upstream_5xx = "upstream_5xx"
    cancelled = "cancelled"
    other = "other"


@dataclass
class ProviderResult:
    """Typed result of a single provider invocation.

    Routing layer reads `error`. If `error != none`, the proof_text is NOT
    accepted as a closure candidate. The router may fall through to
    provider_fallbacks (per policy.operations.solver_lane.provider_fallbacks).
    """

    provider: str
    proof_text: str | None = None
    error: ProviderError = ProviderError.none
    error_detail: str | None = None
    wallclock_s: float = 0.0
    cost_usd: float | None = None
    credit_remaining_hint: str | None = None
    raw_stdout_excerpt: str | None = None
    raw_stderr_excerpt: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.error == ProviderError.none and bool(self.proof_text)

    def to_jsonable(self) -> dict[str, Any]:
        d = {
            "provider": self.provider,
            "proof_text": self.proof_text,
            "error": str(self.error.value),
            "error_detail": self.error_detail,
            "wallclock_s": self.wallclock_s,
            "cost_usd": self.cost_usd,
            "credit_remaining_hint": self.credit_remaining_hint,
            "raw_stdout_excerpt": self.raw_stdout_excerpt,
            "raw_stderr_excerpt": self.raw_stderr_excerpt,
        }
        if self.extra:
            d["extra"] = self.extra
        return d


class Provider(abc.ABC):
    """ABC for a typed prover provider.

    Subclasses implement `_invoke(goal_text)` and `_available()`. The base
    handles timing, capability declaration, and error normalization.
    """

    name: str = ""
    capability: str = ""  # e.g. "claude_subscription", "codex_subscription",
                          # "deepseek_api", "gemini_api", "lean_native_tactics"

    @abc.abstractmethod
    def _invoke(self, goal_text: str, timeout_s: int) -> ProviderResult:
        ...

    def available(self) -> tuple[bool, str | None]:
        """Return (available, reason_if_not). Routers consult this for node
        capability detection without spending tokens."""
        return self._available()

    def _available(self) -> tuple[bool, str | None]:
        # Default: assume available. Subclasses override.
        return True, None

    def invoke(self, goal_text: str, timeout_s: int = 180) -> ProviderResult:
        avail, reason = self.available()
        if not avail:
            return ProviderResult(
                provider=self.name,
                error=ProviderError.binary_not_found if reason and "not found" in reason
                else ProviderError.auth_missing,
                error_detail=reason,
            )
        return self._invoke(goal_text, timeout_s)


# ---------------------------------------------------------------------------
# Registry — lazy import to avoid loading heavy SDKs unless asked.

REGISTRY: dict[str, str] = {
    # provider_name -> dotted module path (resolved lazily via get_provider)
    "claude_opus":   "ztare.leanmill.providers.claude_opus.ClaudeOpusProvider",
    "codex_gpt5":    "ztare.leanmill.providers.codex_gpt5.CodexGpt5Provider",
    "gemini_flash":  "ztare.leanmill.providers.gemini_flash.GeminiFlashProvider",
    "deepseek_v2":   "ztare.leanmill.providers.deepseek_v2.DeepseekV2Provider",
    "placebo":       "ztare.leanmill.providers.placebo.PlaceboProvider",
    # native_hammer (Lean tactic battery) has a different invocation shape
    # (goal_file + proof_file). Keep it on the legacy bash-wrapper path until
    # the next migration round.
}


def get_provider(name: str) -> Provider:
    if name not in REGISTRY:
        raise KeyError(f"unknown provider {name!r}; known: {sorted(REGISTRY)}")
    dotted = REGISTRY[name]
    module_path, class_name = dotted.rsplit(".", 1)
    import importlib

    mod = importlib.import_module(module_path)
    cls = getattr(mod, class_name)
    return cls()
