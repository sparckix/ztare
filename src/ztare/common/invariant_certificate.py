"""General deterministic proof->consumer bridge (autoresearch kernel).

Any project that proves an invariant (worldmodel timer-monotonicity, PDE
energy dissipation, fit monotone-regime, qualitative conservation) and wants a
downstream organ (planner, gate, constraint) to USE it faces the external-
review risk: an LLM reading the proof and hand-writing the consumer relocates
hallucination to translation. This module is the substrate-agnostic fix.

Contract (identical across substrates):
  - a proven invariant is a STRUCTURED certificate: a `quantity` (a total,
    deterministic function of a state, given by a substrate-registered kind)
    + a `relation` over consecutive states + a `status`. Never English.
  - `holds(before, after)` is a total boolean; `admissible(certs, b, a)` is
    True unless some ENFORCED (kernel-ratified) invariant is violated.
  - consumers FILTER model output (drop theorem-impossible transitions), they
    do not prune the hypothesis/search space — so no valid solution is lost.
  - trust is gated on `status == "kernel_ratified"`; a conjectured invariant
    is carried but never enforced (no proof -> no action).

Substrates register quantity kinds via `register_quantity(kind, fn)`; the core
stays domain-free.
"""

from __future__ import annotations

from dataclasses import dataclass

_QUANTITY_KINDS: "dict[str, object]" = {}


def register_quantity(kind: str, fn) -> None:
    """fn(state, *args) -> comparable. Substrate plugin point."""
    _QUANTITY_KINDS[kind] = fn


@dataclass(frozen=True)
class InvariantCertificate:
    quantity: tuple            # (kind, *args) resolved via the registry
    relation: str              # non_increasing | non_decreasing | constant
    status: str                # kernel_ratified | conjectured
    theorem: str = ""

    def value(self, state):
        fn = _QUANTITY_KINDS.get(self.quantity[0])
        if fn is None:
            raise ValueError(f"unregistered quantity kind {self.quantity[0]!r}")
        return fn(state, *self.quantity[1:])

    def holds(self, before, after) -> bool:
        vb, va = self.value(before), self.value(after)
        if self.relation == "non_increasing":
            return va <= vb
        if self.relation == "non_decreasing":
            return va >= vb
        if self.relation == "constant":
            return va == vb
        raise ValueError(f"unknown relation {self.relation!r}")


def enforced(certs) -> "list[InvariantCertificate]":
    return [c for c in (certs or []) if c.status == "kernel_ratified"]


def admissible(certs, before, after) -> bool:
    return all(c.holds(before, after) for c in enforced(certs))


def as_constraint_text(cert) -> str:
    """A proven invariant as a natural-language constraint for the
    identification briefing — deterministic, built from the structured fields
    (no LLM reading a proof)."""
    q = cert.quantity
    qtxt = f"the count of value {q[1]}" if q and q[0] == "count" else str(q)
    rel = {"non_increasing": "never increases",
           "non_decreasing": "never decreases",
           "constant": "is conserved"}.get(cert.relation, cert.relation)
    return f"{qtxt} {rel} across any transition"


def proven_constraints_briefing(certs) -> str:
    """Render KERNEL-RATIFIED invariants as a HARD, proof-backed briefing tier —
    categorically stronger than adversarially-surfaced (survived-N-runs)
    constraints: machine-checked theorems, so violating one is an error, not a
    hypothesis. '' if none ratified (dormant until a proof lands). The general
    fix for proven facts NOT reaching identification."""
    ratified = enforced(certs)
    if not ratified:
        return ""
    lines = ["PROVEN INVARIANTS (kernel-ratified — HARD, not advisory):",
             "Machine-checked theorems about the law. A thesis that violates one "
             "is refuted by construction; do not propose it."]
    for c in ratified:
        lines.append(f"- PROVEN [{c.theorem or 'invariant'}]: {as_constraint_text(c)}")
    return "\n".join(lines) + "\n"
