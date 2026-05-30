"""Distributed provider router — per-node capability detection + fallback.

Minimum viable router (2026-05-28): each worker independently detects what
its node can serve, walks the policy's preferred + fallback provider chain,
and only invokes providers that are actually available on this node. If a
provider returns `ProviderError.credit_exhausted` / `auth_missing` /
`binary_not_found` mid-run, the router falls through to the next provider in
the chain on the same call.

This is the laptop+VPS load balance the user flagged as the 10x lever: the
laptop watchdog declares its capability set, the VPS watchdog declares its
own, both claim from the same work queue, and each only acts on items its
node can serve. Work routing emerges from per-node availability without a
centralised scheduler.

Future increments (not in this first cut):
- queue-level `required_capability` column + claim filter
- per-node heartbeat publishing remaining quota / load
- routing-policy-owned weighting (round-robin across nodes with capacity)
"""
from __future__ import annotations

import functools
import os
from dataclasses import dataclass

from ztare.leanmill.providers.base import (
    Provider,
    ProviderError,
    ProviderResult,
    REGISTRY,
    get_provider,
)


# Errors that mean "this provider can't serve any request on this node right
# now" — the router moves on to the next preference without retrying.
_HARD_NODE_FAILURES = {
    ProviderError.credit_exhausted,
    ProviderError.auth_missing,
    ProviderError.binary_not_found,
}


@dataclass
class RouterDecision:
    """Records which provider was actually used + the chain walked to get there."""
    chosen_provider: str | None
    chain_walked: list[str]
    skipped_unavailable: list[tuple[str, str]]   # [(provider, reason)]
    skipped_hard_failed: list[tuple[str, str]]    # [(provider, error_value)]
    result: ProviderResult | None


@functools.lru_cache(maxsize=1)
def detect_node_capabilities() -> dict[str, bool]:
    """For each registered provider, ask Provider.available(). Cached per process.

    Returns {provider_name: True/False}. Workers can publish this with a
    heartbeat so the router can also do cross-node routing decisions.
    """
    out: dict[str, bool] = {}
    for name in sorted(REGISTRY):
        try:
            p = get_provider(name)
            ok, _reason = p.available()
            out[name] = bool(ok)
        except Exception:
            out[name] = False
    return out


def node_id() -> str:
    """Stable identifier for the node, used in routing receipts."""
    return os.environ.get("ZTARE_NODE_ID") or os.uname().nodename


def invalidate_capability_cache() -> None:
    """Reset the cache when env changes (e.g. an API key just got loaded)."""
    detect_node_capabilities.cache_clear()


def available_capabilities() -> list[str]:
    """Return the list of capability strings this node can serve right now.

    Pass to `work_queue.claim(capabilities=available_capabilities())` so the
    queue only returns items whose `required_capability` matches one of them
    (or is NULL, meaning lane-agnostic). This is what workers wire into their
    main loop to participate in cross-node routing.
    """
    caps: list[str] = []
    for name, ok in detect_node_capabilities().items():
        if not ok:
            continue
        try:
            caps.append(get_provider(name).capability)
        except Exception:
            continue
    # Dedupe while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for c in caps:
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def invoke_with_routing(
    goal_text: str,
    *,
    preferred: str,
    fallbacks: list[str] | None = None,
    timeout_s: int = 180,
) -> RouterDecision:
    """Invoke `preferred`; on hard node-failure, fall through `fallbacks` in order.

    `fallbacks` typically comes from `policy.operations.solver_lane.provider_fallbacks`.
    Providers not declared available on this node are skipped without invocation.
    """
    chain = [preferred] + [f for f in (fallbacks or []) if f != preferred]
    caps = detect_node_capabilities()
    skipped_unavail: list[tuple[str, str]] = []
    skipped_hard: list[tuple[str, str]] = []
    chain_walked: list[str] = []
    last_result: ProviderResult | None = None

    for name in chain:
        if name not in REGISTRY:
            skipped_unavail.append((name, "not_in_provider_registry"))
            continue
        if not caps.get(name, False):
            # Re-check uncached in case env was loaded after first probe
            ok, reason = get_provider(name).available()
            if not ok:
                skipped_unavail.append((name, reason or "unavailable"))
                continue
        chain_walked.append(name)
        result = get_provider(name).invoke(goal_text, timeout_s=timeout_s)
        last_result = result
        if result.ok:
            return RouterDecision(
                chosen_provider=name,
                chain_walked=chain_walked,
                skipped_unavailable=skipped_unavail,
                skipped_hard_failed=skipped_hard,
                result=result,
            )
        if result.error in _HARD_NODE_FAILURES:
            # Node-level block on this provider; try the next one.
            skipped_hard.append((name, result.error.value))
            continue
        # Soft failure (malformed / timeout / other) — return as the chosen result.
        return RouterDecision(
            chosen_provider=name,
            chain_walked=chain_walked,
            skipped_unavailable=skipped_unavail,
            skipped_hard_failed=skipped_hard,
            result=result,
        )

    return RouterDecision(
        chosen_provider=None,
        chain_walked=chain_walked,
        skipped_unavailable=skipped_unavail,
        skipped_hard_failed=skipped_hard,
        result=last_result,
    )


def _self_test() -> int:
    caps = detect_node_capabilities()
    print(f"node_id: {node_id()}")
    print("capabilities:")
    for name, ok in caps.items():
        print(f"  {name:<14} {ok}")
    print()
    decision = invoke_with_routing(
        "theorem demo : 1 + 1 = 2 := by",
        preferred="claude_opus",
        fallbacks=["gemini_flash", "deepseek_v2", "codex_gpt5"],
    )
    print(f"chosen:           {decision.chosen_provider}")
    print(f"chain_walked:     {decision.chain_walked}")
    print(f"skipped_unavail:  {decision.skipped_unavailable}")
    print(f"skipped_hard:     {decision.skipped_hard_failed}")
    if decision.result is not None:
        print(f"proof_text:       {decision.result.proof_text!r}")
        print(f"error:            {decision.result.error.value}")
    return 0


if __name__ == "__main__":
    import sys
    if "--self-test" in sys.argv:
        sys.exit(_self_test())
    print("usage: python -m ztare.leanmill.providers.router --self-test")
    sys.exit(2)
