"""Product-domain deliverable templates (PLUGIN). Self-register on import via `register_template`; deleting
this file removes the PM deliverables with zero kernel change (the rot test). Each template composes slots
PURELY from governed elements under PM-native labels — the provenance firewall (kernel) enforces that
regardless of who registered it. Governed edges among the cited elements become edge-licensed `relations`
(`relations_among`), so a deliverable reads as an ARGUMENT, not a list. No free prose, no fabricated content."""
from __future__ import annotations

from ztare.scenarios.artifacts import (
    FINDING_KINDS,
    Deliverable,
    GovernedState,
    Slot,
    register_template,
    relations_among,
)

# All PM findings (tension/gap/constraint/finding) as one bucket; templates that want a subset name it explicitly.
_RISKS = FINDING_KINDS


def _compose(name: str, governed: GovernedState,
             sections: "list[tuple[str, tuple[str, ...]]]") -> Deliverable:
    """Build a deliverable from `sections` = [(label, kinds), ...]: one governed slot per element of each kind,
    in declared order. Pure governed composition (the firewall gates it); `relations_among` grafts the governed
    argument for free. The ONE composer for every PM template so they can't drift on how they cite the graph."""
    slots: "list[Slot]" = []
    for label, kinds in sections:
        for kind in kinds:
            for element in governed.of_kind(kind):
                slots.append(Slot(label, element.id, element.text))
    return Deliverable(name=name, slots=slots, relations=relations_among(governed, slots))


def product_spec(governed: GovernedState) -> Deliverable:
    return _compose("product_spec", governed, [
        ("What we're building (hardened)", ("thesis", "claim")),
        ("Evidence", ("evidence",)),
        ("Adversarial finding", _RISKS),
        ("Kill-criterion", ("falsifier",))])


def risk_register(governed: GovernedState) -> Deliverable:
    return _compose("risk_register", governed, [
        ("Risk (adversarial finding)", _RISKS),
        ("Trigger / kill-criterion", ("falsifier",))])


def prd(governed: GovernedState) -> Deliverable:
    """A Product Requirements Doc: problem/hypothesis → evidence → scope/non-goals (constraints) → open risks →
    kill-criteria. Non-goals and risks are separated so scope discipline is visible on the artifact's face."""
    return _compose("prd", governed, [
        ("Problem & hypothesis (hardened)", ("thesis", "claim")),
        ("Customer / data evidence", ("evidence",)),
        ("Non-goals & scope", ("constraint",)),
        ("Open risk", ("tension", "gap", "finding")),
        ("Kill-criterion / what would change our mind", ("falsifier",))])


def launch_readiness(governed: GovernedState) -> Deliverable:
    """A launch-readiness brief: the readiness assertion, the evidence for it, the failure modes still open, and
    the pre-registered abort criteria. Honest by construction — an unresolved failure mode shows as an open risk,
    not a green check."""
    return _compose("launch_readiness", governed, [
        ("Readiness assertion (hardened)", ("thesis", "claim")),
        ("Readiness evidence", ("evidence",)),
        ("Failure mode / open risk", _RISKS),
        ("Abort criterion", ("falsifier",))])


def adr(governed: GovernedState) -> Deliverable:
    """An Architecture/Decision Record. Uniquely pulls the governed `rejected` node kind into an explicit
    'Alternatives considered & rejected' section — the thing a decision record exists to preserve and the one
    place the graph's ruled-out branches surface as a first-class artifact section."""
    return _compose("adr", governed, [
        ("Decision (hardened)", ("thesis", "claim")),
        ("Context & evidence", ("evidence",)),
        ("Alternatives considered & rejected", ("rejected",)),
        ("Consequence / risk", _RISKS),
        ("Revisit-if (kill-criterion)", ("falsifier",))])


def rice(governed: GovernedState) -> Deliverable:
    """The governed INPUTS to a RICE score — never fabricated numbers. Reach/Impact rest on evidence; Confidence
    is bounded by the open findings; the kill-criterion bounds the downside of Effort spent. The score itself is
    the PM's judgment over these governed inputs; this template refuses to invent it (that would launder a number
    through the stamp)."""
    return _compose("rice", governed, [
        ("What we're scoring (hardened)", ("thesis", "claim")),
        ("Reach & impact evidence (grounds R, I)", ("evidence",)),
        ("Confidence discount (bounds C)", _RISKS),
        ("Kill-criterion (bounds Effort risk)", ("falsifier",))])


def leadership_packet(governed: GovernedState) -> Deliverable:
    """Leadership packet — PM composition of the *same* governed claim/evidence graph that core claim cards
    summarize. Not a new core primitive: claim cards remain core; this is a persona-facing packet that cites
    hardened claims as executive claim lines, then the warrant (evidence), open risks, scope constraints, and
    kill-criteria. Firewall-pure: every slot is a governed ref, no free prose, no apparatus meta."""
    return _compose("leadership_packet", governed, [
        ("Executive claim (portable claim-card unit)", ("thesis", "claim")),
        ("Warrant / evidence", ("evidence",)),
        ("Scope & non-goals", ("constraint",)),
        ("Open risk / adversarial finding", _RISKS),
        ("What would change the decision", ("falsifier",))])


def roadmap_backing(governed: GovernedState) -> Deliverable:
    """Governed roadmap with backing — PM overlay artifact: feature/bet nodes as hardened claims, dependencies
    surface via `relations_among` (governed edges only), confidence heat is *not* invented here (that would
    launder scores); open risks and kill-criteria bound confidence. Consumes core graph; does not extend
    research-map semantics."""
    return _compose("roadmap_backing", governed, [
        ("Roadmap item (hardened claim)", ("thesis", "claim")),
        ("Backing evidence", ("evidence",)),
        ("Dependency / constraint", ("constraint",)),
        ("Risk that weakens the item", _RISKS),
        ("Kill-criterion / re-sequence if", ("falsifier",))])


def bet_registry(governed: GovernedState) -> Deliverable:
    """Bet registry export for PM — composition of governed claims under test + falsifiers as settlement
    conditions. Does *not* replace the core wager/agenda kernel (Open points); it is a deliverable *view* of
    the same governed content a PMT would put in a decision record. Register live bets via the core wager
    surface; this template only packages what is already governed."""
    return _compose("bet_registry", governed, [
        ("Bet / claim under decision", ("thesis", "claim")),
        ("Settlement / kill-criterion", ("falsifier",)),
        ("Evidence that would move the bet", ("evidence",)),
        ("Risk if the bet is wrong", _RISKS)])


for _name, _builder in (
    ("product_spec", product_spec),
    ("risk_register", risk_register),
    ("prd", prd),
    ("launch_readiness", launch_readiness),
    ("adr", adr),
    ("rice", rice),
    ("leadership_packet", leadership_packet),
    ("roadmap_backing", roadmap_backing),
    ("bet_registry", bet_registry),
):
    register_template(_name, _builder)
