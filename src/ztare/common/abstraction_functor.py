"""Sound-abstraction interface: laws at role level, verification at raw level.

The general contract (autoresearch-kernel level — substrates plug in):

  alpha   : raw evidence -> abstract state (entities + behavioral ROLES),
            induced ONLY from evidence statistics (sealed-safe: no docs)
  laws    : hypotheses expressed over roles (compact, transferable)
  gamma   : deterministic lowering of role-level laws to RAW predictions
  gates   : verification happens ONLY at the raw level, by the substrate's
            existing deterministic gates — abstraction proposes, raw disposes
  refine  : a raw counterexample is classified SPURIOUS (the abstraction
            aliased two behaviorally-distinct raw states -> split the role)
            or REAL (the law is wrong at role level) — the CEGAR loop

Literature anchors: counterexample-guided abstraction refinement (model
checking); MDP homomorphisms / bisimulation (a role map is sound iff raw
states sharing a role share transition behavior under the lowering); state-
abstraction soundness taxonomy; automaton induction (counterexamples add
states). Kernel-transported analogs (research_isomorphism, 2026-07-03):
gauge fixing as lowering, anomaly as an abstraction symmetry that fails to
survive it. Failure modes carry those names in receipts.

Why kernel-level: 'roles' instantiate per substrate — grid objects
(worldmodel), fit regimes (quantitative), equation terms (PDE), mechanisms
(qualitative). The contract, receipts, and refinement loop are shared; only
alpha/gamma are substrate plugins.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@runtime_checkable
class AbstractionFunctor(Protocol):
    """A substrate's alpha/gamma pair. Implementations must induce roles from
    evidence only, and lower deterministically."""

    def abstract(self, raw_evidence) -> "AbstractState": ...
    def lower(self, abstract_law, raw_state): ...          # -> raw prediction


@dataclass
class Role:
    name: str                 # behavioral, never semantic: "moves_under_actions"
    members: "list"           # raw-level entities carrying the role
    evidence: str = ""        # the statistic that induced it


@dataclass
class AbstractState:
    roles: "list[Role]"
    detail: str = ""


@dataclass(frozen=True)
class FiniteQuotient:
    """Finite event/status quotient used by governance and substrate adapters.

    This is the small algebraic carrier behind many alpha maps: raw receipts
    become typed atoms; a consumer asks whether a declared atom formula is
    satisfied. Today the formula language is disjunction only, written with
    ``_or_`` for ledger readability. If a caller needs conjunction later, add a
    typed formula here rather than inventing local string matching.
    """

    atoms: frozenset[str]
    source: str = ""

    def satisfies_any(self, required) -> bool:
        need = parse_disjunctive_atoms(required)
        return bool(need and (self.atoms & need))


def parse_disjunctive_atoms(expr, *, separator: str = "_or_") -> frozenset[str]:
    """Parse a compact disjunctive atom expression into exact atoms.

    ``terminal_event_or_new_evidence`` becomes
    ``{"terminal_event", "new_evidence"}``; ``terminal_eventual`` remains one
    atom and therefore does not match ``terminal_event``.
    """
    text = str(expr or "").strip()
    if not text:
        return frozenset()
    return frozenset(part for part in text.split(separator) if part)


@dataclass
class RefinementVerdict:
    kind: str                 # "spurious_abstraction" | "real_law_failure"
    role: "str | None" = None
    detail: str = ""


def _signature(state: "AbstractState") -> tuple:
    return tuple(sorted((r.name, tuple(map(str, r.members))) for r in state.roles))


def classify_counterexample(functor: AbstractionFunctor, abstract_law,
                            raw_state, raw_next, predicted,
                            history: "list | None" = None,
                            max_witness_search: int = 64) -> RefinementVerdict:
    """CEGAR classification with an ALIASING WITNESS (external review fix,
    2026-07-03: the original skeleton never used raw_next — deterministic
    alpha/gamma re-run on one state can never expose aliasing; aliasing is a
    TWO-state property).

    spurious_abstraction  <- some historical raw state shares this state's
                             abstract signature, but its OBSERVED ground-truth
                             behavior differs from this one's (the role map
                             aliases behaviorally-distinct raw states)
    real_law_failure      <- no aliasing witness found: the abstraction is
                             faithful as far as evidence shows; the role-level
                             law itself mispredicts (predicted != raw_next)
    not_a_counterexample  <- the lowered prediction matches ground truth
    """
    if predicted == raw_next:
        return RefinementVerdict(kind="not_a_counterexample",
                                 detail="lowered prediction matches ground truth")
    try:
        sig_here = _signature(functor.abstract([raw_state]))
    except Exception as exc:  # noqa: BLE001
        return RefinementVerdict(kind="real_law_failure",
                                 detail=f"abstraction failed on the state: {exc}")
    for (h_state, h_next) in (history or [])[:max_witness_search]:
        try:
            if _signature(functor.abstract([h_state])) != sig_here:
                continue
        except Exception:  # noqa: BLE001
            continue
        h_pred = functor.lower(abstract_law, h_state)
        # same abstract signature; if the law's lowering matched THAT state's
        # ground truth but fails this one's, the two raw states are aliased
        # while behaving differently -> the role map is too coarse
        if h_pred == h_next:
            return RefinementVerdict(
                kind="spurious_abstraction",
                detail="aliasing witness: a raw state with the identical role "
                       "signature obeys the lowered law while this one refutes "
                       "it — split the role that aliases them")
    return RefinementVerdict(kind="real_law_failure",
                             detail="no aliasing witness in history; the role-level "
                                    "law mispredicts and must change")
