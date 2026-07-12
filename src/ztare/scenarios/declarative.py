"""Declarative, provenance-safe deliverable composition.

Scenario authors can describe a one-shot document in YAML without writing a
Python template.  The recipe only selects governed node kinds into labelled
sections; it cannot add prose, facts, or relations.  The normal provenance
firewall remains the final authority.
"""
from __future__ import annotations

from typing import Any

from ztare.scenarios.config import DeliverableSpec
from ztare.scenarios.firewall import relations_among
from ztare.scenarios.governed_types import Deliverable, GovernedState, Slot


def compose_declarative(spec: DeliverableSpec | dict[str, Any], governed: GovernedState) -> Deliverable:
    """Build a document from a validated section recipe.

    Sections preserve the governed graph's stable element order.  A positive
    section limit is a presentation cap, not a claim-selection mechanism: it
    is explicit in the manifest and the omitted governed nodes remain visible
    in the source map.
    """
    if not isinstance(spec, DeliverableSpec):
        spec = DeliverableSpec.model_validate(spec)
    slots: list[Slot] = []
    for section in spec.sections:
        selected = [element for element in governed.elements if element.kind in section.kinds]
        if section.limit:
            selected = selected[:section.limit]
        slots.extend(Slot(section.label, element.id, element.text) for element in selected)
    if not slots:
        return Deliverable(spec.name, stub_reason="no governed content matches this document design")
    return Deliverable(
        spec.name,
        slots=slots,
        relations=relations_among(governed, slots),
        label=spec.label,
        audience=spec.audience,
        description=spec.description,
        presentation_brief=spec.presentation_brief,
    )


def spec_payload(spec: DeliverableSpec) -> dict[str, Any]:
    """Expose only presentation metadata; never serialize an executable prompt."""
    return spec.model_dump(mode="json")
