"""Catalog closure audit: the hypothesis language ships with its own algebra.

Standing discipline (2026-07-03, after the toggle miss): operator families span
(what can CONDITION a rule) x (what a rule can WRITE) x (interface). Waiting
for residuals to find unclosed cells one at a time means every hole costs a
full mine-extend-verify round. This audit enumerates the declared closure
table against the catalog SOURCE (string markers — robust to concurrent edits,
no import fragility) and pre-registers every unclosed cell as an operator-
proposal card, so grammar gaps are named BEFORE evidence hits them. Cards are
dedup'd by family sha — re-running the audit is idempotent; closing a cell in
the catalog makes its card stop being emitted.
"""

from __future__ import annotations

from pathlib import Path

from ztare.common.operator_proposal_contract import (
    operator_proposal_card, write_proposal_cards)

# cell -> (source marker that closes it, sketch, acceptance test)
CLOSURE_TABLE = {
    "condition:global_count": ("when_count", "", ""),
    "condition:mover_region_overlap": ("when_overlap", "", ""),
    "condition:action_identity": ("when_action", "", ""),
    "condition:indicator_region_state": ("when_region",
        "when_region guard: rule fires only when a rect's step-start contents match a learned pattern",
        "planted synthetic: a move legal only while an indicator region holds a pattern"),
    "condition:phase_periodicity": ("when_phase",
        "when_phase [m, r] guard: fires iff step-start t % m == r (blinkers, patrol cycles)",
        "planted synthetic: a blinker mechanic only a phase guard separates"),
    "condition:rule_coupling": ("when_effect",
        "when_effect [ref_id, pol] guard: a rule fires iff another (id'd) rule DID/DIDN'T fire "
        "this step (a timer coupled to whether the mover moved) — mid-chain fired-flag",
        "planted synthetic: a timer whose tick/pause split coincides with the mover's move split "
        "at varying positions, so no positional/periodic guard separates it — only the coupling"),
    "condition:destination_content": ("when_dest",
        "when_dest [ref_id, colors, flag] guard: fires iff the acting translate's destination "
        "window (its components displaced by that rule's OWN dy/dx) holds one of colors == flag — "
        "the object-anchored 'what lies ahead' gate (transit/lock freezes); relational, no "
        "absolute rects or frame indices",
        "planted synthetic: a timer that pauses only while the mover's next cell is void, with "
        "freezes at varying positions so no absolute rect or phase separates the split"),
    "condition:event_history_latch": (None,
        "hidden-state guard: rule gated on an event having fired THIS EPISODE with no visible "
        "grid trace (automaton-state extension; also covers direction-memory for bouncing movers)",
        "a synthetic log where identical visible states behave differently based only on episode "
        "history; refute all visible-state guard families first"),
    "condition:relational_anchor": (None,
        "guards/rects anchored to a tracked OBJECT's current location, not absolute coordinates "
        "(the relational-template tier; build when cross-level transfer shows fixed rects breaking)",
        "two levels sharing physics with shifted geometry: relational spec must transfer zero-shot"),
    "effect:rigid_translate": ("translate_block", "", ""),
    "effect:global_recolor": ("recolor_map", "", ""),
    "effect:count_consume": ("consume_extremal", "", ""),
    "effect:fixed_region_write": ("region_event", "", ""),
    "effect:state_dependent_toggle": ("toggle",
        "toggle writes: pairwise color swap dependent on the written cell's current state",
        "planted synthetic swap log"),
    "effect:permutation_cycle_write": ("cycle",
        "k-cycle writes c1->c2->c3->c1 (multi-state doors/lights); toggle is k=2",
        "planted synthetic 3-state indicator"),
    "effect:hidden_state_update": (None,
        "effects that update non-grid state (direction memory, inventory) — same card family as "
        "the event-history latch; one automaton-state extension covers both",
        "same as condition:event_history_latch"),
    "interface:discrete_actions": ("action", "", ""),
    "interface:coordinate_actions": (None,
        "actions carrying (x, y) arguments (ARC-AGI-3 click games): arity model + abduction must "
        "treat the coordinate as a rule parameter, not an opaque action id",
        "verify at tu93 unpark BEFORE the inter-game test; a coordinate game's log must abduce "
        "with position-parameterized rules"),
}


def catalog_closure_audit(catalog_source: "str | None" = None) -> "list[dict]":
    """Return proposal cards for every UNCLOSED cell. `catalog_source` defaults
    to the live spec_catalog source text (injectable for tests)."""
    if catalog_source is None:
        catalog_source = (Path(__file__).parent / "spec_catalog.py").read_text()
    cards = []
    for cell, (marker, sketch, test) in CLOSURE_TABLE.items():
        if marker is not None and marker in catalog_source:
            continue                      # closed (or in flight in the source)
        cards.append(operator_proposal_card(
            failure_family=f"closure:{cell}",
            evidence_indices=[],
            spatial_footprint={},
            why_existing_ops_fail={"closure_audit":
                f"no operator family covers {cell}; pre-registered before evidence hits it"},
            proposed_operator_sketch=sketch or cell,
            acceptance_test=test or "planted synthetic only the proposed family explains"))
    return cards


def write_closure_cards(project: "Path | str") -> "list[dict]":
    path = Path(project) / "workspace" / "operator_proposals.jsonl"
    return write_proposal_cards(path, catalog_closure_audit())
