"""Placebo prover — matched negative control for the solver lane.

Ported from the epistemic-generation `A_route vs A_routeP` discipline
(`workingpapers/epistemic-generation/SEALED_PREREG_functional_routing_20260519.md`):
the placebo arm has *identical structure* to the real arm but no actual
prover. Closures from the real arm must beat the placebo arm with the
pre-registered effect size; otherwise the closure is structurally indistinguishable
from chance and gets typed `consequence_exposure_NOT_genuine`.

Concretely the PlaceboProvider returns a *syntactically plausible but
mathematically vacuous* response with the same prompt shape as a real prover:
no LLM call, no token spend, no proof. Governance can call it the same way it
calls a real provider, log the same fields, and detect spurious wins by
comparing the population.

Use:
  real = get_provider("claude_opus").invoke(goal)
  ctrl = get_provider("placebo").invoke(goal)
  # If governance ratifies ctrl as readily as real, the discipline is broken.
"""
from __future__ import annotations

import time

from ztare.leanmill.providers.base import Provider, ProviderError, ProviderResult


# The placebo emits a syntactically plausible Lean tactic that almost never
# closes a real goal. This is intentional: if governance gates ratify this as
# a closure, the gate is broken (no proof was actually generated).
_PLACEBO_PROOFS = [
    "by sorry",
    "by trivial",
    "by exact?",
    "by simp",
    "by rfl",
]


class PlaceboProvider(Provider):
    name = "placebo"
    capability = "matched_negative_control"

    def _available(self) -> tuple[bool, str | None]:
        return True, None

    def _invoke(self, goal_text: str, timeout_s: int) -> ProviderResult:
        # Deterministic by goal — same goal always gets same placebo so
        # paired-comparison stats are clean across runs.
        h = sum(ord(c) for c in goal_text[:200])
        proof = _PLACEBO_PROOFS[h % len(_PLACEBO_PROOFS)]
        # Tiny wallclock so it's distinguishable from real providers in logs
        time.sleep(0.001)
        return ProviderResult(
            provider=self.name,
            proof_text=proof,
            error=ProviderError.none,
            wallclock_s=0.001,
            cost_usd=0.0,
            extra={
                "matched_negative_control": True,
                "lineage": "epistemic-generation:SEALED_PREREG_functional_routing_20260519:A_routeP placebo arm",
                "discipline_note": "PlaceboProvider is structurally identical to real providers but mathematically vacuous. If governance ratifies a placebo result, the discipline is broken.",
            },
        )
