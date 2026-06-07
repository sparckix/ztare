"""RefineHandover — the ONE produce→verify→feedback→refine→gate loop.

Grounded finding (handover-contract check, 2026-06-05): the solver's gap-refine and the
autoformalizer's compile-fix are the SAME shape — generate an artifact, run it past a verifier/kernel
gate, and on rejection hand the artifact back its OWN verifier feedback and regenerate, bounded. They
had been implemented ad-hoc (the solver) or not at all (the autoformalizer is one-shot). The
action-card / pattern_action_contract family is a DIFFERENT object — declarative pattern→action→
antipattern governance tuples + one-shot shape validators — so this is the genuinely-missing shared
abstraction, NOT a duplicate of them.

ZERO new governance. The gate (`verify`) is INJECTED: the kernel-compile + matched-negative-control
contract for the solver, the faithfulness firewall for the autoformalizer. The driver only standardizes
*how an artifact is handed back its verifier feedback and regenerated under a bounded budget*. The
emitted trace reuses the field names of `research_director/boundary_card_repair_trace` (the one place the
produce→reject→repair→re-gate sequence was already formalized) so measurement stays unified.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional


def _short(x: Any, n: int = 240) -> str:
    return (str(x) or "")[:n]


def _basis(verdict: Any) -> str:
    return _short(getattr(verdict, "reason", None) or getattr(verdict, "feedback", None) or verdict, 160)


def _gate(verdict: Any, accept_when: "Callable[[Any], bool]") -> dict:
    return {"accepted": bool(accept_when(verdict)),
            "detail": _short(getattr(verdict, "checks", None) or getattr(verdict, "reason", None) or "", 200)}


@dataclass
class RefineHandover:
    """generate(ctx)->artifact ; verify(artifact)->verdict (the INJECTED gate — no new governance) ;
    accept_when(verdict)->bool ; build_refine_context(artifact, verdict, ctx)->ctx' | None (None ⇒ stop,
    one-shot) ; better(a, va, b, vb)->(artifact, verdict) keep-policy (default: take the refine only if it
    is accepted — monotone toward acceptance) ; max_refines bounds the loop (1 = solver default; 0 = pure
    one-shot). run(ctx) returns (artifact, verdict, trace) where trace uses boundary_card_repair_trace fields."""
    generate: Callable[[Any], Any]
    verify: Callable[[Any], Any]
    accept_when: Callable[[Any], bool]
    build_refine_context: Optional[Callable[[Any, Any, Any], Any]] = None
    better: Optional[Callable[[Any, Any, Any, Any], "tuple[Any, Any]"]] = None
    max_refines: int = 1

    def run(self, ctx: Any) -> "tuple[Any, Any, list[dict]]":
        artifact = self.generate(ctx)
        verdict = self.verify(artifact)
        trace: list[dict] = [{"round": 0, "rejected_card": None, "repair_prompt": None,
                              "repaired_card": _short(artifact),
                              "post_repair_gate_result": _gate(verdict, self.accept_when)}]
        refines = 0
        while (not self.accept_when(verdict) and refines < self.max_refines
               and self.build_refine_context is not None):
            ctx2 = self.build_refine_context(artifact, verdict, ctx)
            if ctx2 is None:                       # generator/gate says "no refinable feedback" → stop
                break
            a2 = self.generate(ctx2)
            v2 = self.verify(a2)
            refines += 1
            trace.append({"round": refines, "rejected_card": _short(artifact),
                          "pre_repair_gate_result": _gate(verdict, self.accept_when),
                          "rejection_basis": _basis(verdict), "repair_prompt": _short(ctx2),
                          "repaired_card": _short(a2),
                          "post_repair_gate_result": _gate(v2, self.accept_when)})
            if self.better is not None:
                artifact, verdict = self.better(artifact, verdict, a2, v2)
            elif self.accept_when(v2):             # default keep-policy: monotone toward acceptance
                artifact, verdict = a2, v2
        return artifact, verdict, trace
