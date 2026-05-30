"""LeanMill prover providers — typed Python invocations.

Replaces the legacy `scripts/public/lean/providers/*.sh` shell wrappers.
Bash wrappers had no typed error channel: credit-exhausted errors were
returned as stdout strings and silently treated as "proof text" by the
solver lane. Typed providers make availability and failure modes explicit.
"""
from ztare.leanmill.providers.base import (
    Provider,
    ProviderError,
    ProviderResult,
    REGISTRY,
    get_provider,
)

__all__ = ["Provider", "ProviderError", "ProviderResult", "REGISTRY", "get_provider"]
