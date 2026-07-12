"""Governed artifacts — the **provenance firewall** + the deliverable template registry. See `artifacts.py` for
the module-level docstring (the firewall invariant: total provenance, verbatim text, set-completeness)."""
from __future__ import annotations

from ztare.scenarios.governed_types import (
    Deliverable, EDGE_KINDS, FINDING_KINDS, GovernedState, ProvenanceVerdict, Relation, Slot, normalize,
    _EDGE_CONNECTIVE,
)


def provenance_firewall(deliverables: "list[Deliverable]", governed: GovernedState,
                        declared: "list[str]") -> ProvenanceVerdict:
    """THE gate. Total-provenance + verbatim + set-completeness. Machine-checkable, no LLM in the loop.
    `declared` is the charter-pre-registered deliverable set (WHAT must be produced)."""
    violations: "list[str]" = []
    emitted = {d.name for d in deliverables}

    # set-completeness (anti-cherry-pick): every declared deliverable emitted or stubbed.
    for name in declared:
        if name not in emitted:
            violations.append(f"declared deliverable '{name}' is neither emitted nor stubbed (cherry-pick guard)")

    for d in deliverables:
        if d.stub_reason:
            continue  # a stub asserts nothing → nothing to govern
        if not d.slots:
            violations.append(f"deliverable '{d.name}': empty non-stub (no governed content)")
        for s in d.slots:
            element = governed.by_id(s.element_id)
            if element is None:
                violations.append(
                    f"'{d.name}'/{s.label}: ORPHAN — element_id '{s.element_id}' not in the governed state")
                continue
            if normalize(s.text) != normalize(element.text):
                violations.append(
                    f"'{d.name}'/{s.label}: PARAPHRASE DRIFT — slot text is not verbatim to governed:{s.element_id}")
        for r in d.relations:  # a relation is a CLAIM; it must cite a governed edge or it's laundered rhetoric
            if r.kind not in EDGE_KINDS:
                violations.append(f"'{d.name}': relation kind '{r.kind}' not in {list(EDGE_KINDS)}")
            elif not governed.has_edge(r.src_id, r.kind, r.dst_id):
                violations.append(
                    f"'{d.name}': UNLICENSED RELATION — no governed edge {r.src_id} -{r.kind}-> {r.dst_id}")
    return ProvenanceVerdict(ok=not violations, violations=violations)


def render(deliverable: Deliverable, governed: "GovernedState | None" = None) -> str:
    """Render a (firewall-passed) deliverable to markdown — governed content only, each slot stamped with its
    provenance id. Relations render as an explicit 'Argument' block, each connective stamped with the governed
    edge that licenses it, so the argument structure is auditable on the face of the artifact."""
    lines = [f"# {deliverable.label or deliverable.name}", ""]
    if deliverable.stub_reason:
        return "\n".join(lines + [f"_Omitted: {deliverable.stub_reason}_", ""]) + "\n"
    if deliverable.audience:
        lines += [f"_For: {deliverable.audience}_", ""]
    # Description is catalog copy shown by the Workbench, not governed
    # document content. Rendering it here would let scenario metadata assert
    # a factual sentence without a governed element behind it.
    # ``presentation_brief`` is renderer metadata, not audience content.  The
    # plain source-packet renderer intentionally preserves only recorded
    # decision material; exposing an internal editorial instruction in the
    # packet would make a handoff read like a prompt instead of a document.
    current_label = None
    for s in deliverable.slots:
        if s.label != current_label:
            lines += [f"## {s.label}", ""]
            current_label = s.label
        lines += [f"- {s.text}", f"  <sub>← governed:{s.element_id}</sub>", ""]
    if deliverable.relations and governed is not None:
        lines += ["<details>", "<summary>Argument structure</summary>", ""]
        for r in deliverable.relations:
            src, dst = governed.by_id(r.src_id), governed.by_id(r.dst_id)
            connective = _EDGE_CONNECTIVE.get(r.kind, r.kind)
            lines.append(f"- {src.text if src else r.src_id} **{connective}** {dst.text if dst else r.dst_id} "
                         f"<sub>← governed-edge:{r.src_id}-{r.kind}-{r.dst_id}</sub>")
        lines += ["", "</details>", ""]
    return "\n".join(lines) + "\n"


def relations_among(governed: GovernedState, slots: "list[Slot]") -> "list[Relation]":
    """The governed edges whose BOTH endpoints are cited in `slots` — the deliverable's argument. Every one is
    edge-licensed by construction (it came from `governed.edges`), so the firewall passes it; a template gets
    an argument, not a list, for free. Shared by all templates so 'reads as an argument' is a kernel property."""
    ids = {s.element_id for s in slots}
    return [Relation(e.src, e.kind, e.dst) for e in governed.edges if e.src in ids and e.dst in ids]


def decision_memo(governed: GovernedState) -> Deliverable:
    """Kernel default template: a governed decision-memo composed VERBATIM from the governed graph (= the
    research map), with the governed edges among its elements rendered as the argument. Zero free prose — every
    section AND every connective is governed, so it passes the firewall by construction."""
    slots: "list[Slot]" = []
    for element in governed.of_kind("thesis") + governed.of_kind("claim"):
        slots.append(Slot("Hardened claim", element.id, element.text))
    for element in governed.of_kind("evidence"):
        slots.append(Slot("Evidence", element.id, element.text))
    for kind in FINDING_KINDS:
        for element in governed.of_kind(kind):
            slots.append(Slot("Adversarial finding", element.id, element.text))
    for element in governed.of_kind("falsifier"):
        slots.append(Slot("What would change our mind", element.id, element.text))
    return Deliverable(name="decision_memo", slots=slots, relations=relations_among(governed, slots))


# Deliverable template registry (KERNEL). Ships ONE domain-neutral default: `decision_memo` (governed
# claims/evidence/findings/falsifiers under neutral kind-labels — no domain nouns). DOMAIN templates (a PM
# product-spec, a risk-register, a Lean proof-brief) are PLUGIN assets that self-register via
# `register_template` from a scenario's providers/ module — deleting that module removes them without touching
# the kernel (the rot test). Each template MUST compose slots purely from governed elements; the firewall
# enforces it regardless of who registered it.
_TEMPLATES: "dict[str, object]" = {"decision_memo": decision_memo}


def register_template(name: str, builder) -> None:
    _TEMPLATES[name] = builder
