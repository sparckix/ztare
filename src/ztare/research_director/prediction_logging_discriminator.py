"""Deterministic discriminator for when RD work needs a Prediction Ledger row.

The goal is to avoid two opposite failures:

* under-logging decisions that later become calibration-relevant; and
* logging every tick, which turns calibration into bookkeeping theater.

The rule is intentionally simple and auditable. It decides whether an action
is Tier 1 / Tier 2 / Tier 3 under PATTERN-012.
"""
from __future__ import annotations

from dataclasses import dataclass


TIER1_REASONS = {
    "agent_dispatch",
    "external_dispatch",
    "parallel_swarm",
    "promote",
    "demote",
    "kill",
    "escalate",
    "paid_spend",
    "pre_registered_experiment",
    "route_commitment",
}

TIER2_REASONS = {
    "prioritization",
    "atom_ordering",
    "which_agent_first",
    "campaign_triage",
    "substate_selection",
    "substrate_selection",
}


@dataclass(frozen=True)
class PredictionLogDecision:
    tier: int
    must_log: bool
    should_log: bool
    reason: str
    anti_gaming_note: str


def decide_prediction_logging(
    *,
    action_kind: str,
    gates_typed_action: bool = False,
    outcome_observable: bool = True,
    cost_usd: float = 0.0,
    agent_count: int = 1,
) -> PredictionLogDecision:
    """Return the PATTERN-012 logging decision for a proposed RD action.

    Parameters are deliberately minimal so the rule can be used from CLIs,
    daemon prechecks, and agent-written work notes.
    """
    kind = action_kind.strip().lower().replace("-", "_")
    if cost_usd > 0:
        kind = "paid_spend"
    if agent_count >= 2:
        kind = "parallel_swarm"

    if kind in TIER1_REASONS or gates_typed_action:
        return PredictionLogDecision(
            tier=1,
            must_log=True,
            should_log=True,
            reason=(
                "Tier 1: action gates a typed commitment or calibration-relevant "
                f"dispatch ({kind}). Write PL row before action."
            ),
            anti_gaming_note=(
                "If this later gates a typed action, it remains Tier 1 even if "
                "initially described as exploratory."
            ),
        )

    if kind in TIER2_REASONS and outcome_observable:
        return PredictionLogDecision(
            tier=2,
            must_log=False,
            should_log=True,
            reason=(
                "Tier 2: prioritization decision with observable outcome. "
                "PL row recommended when effort/cost is nontrivial."
            ),
            anti_gaming_note=(
                "Escalates to Tier 1 if it becomes the basis for dispatch, "
                "promotion/demotion, kill, or spend."
            ),
        )

    return PredictionLogDecision(
        tier=3,
        must_log=False,
        should_log=False,
        reason=(
            "Tier 3: housekeeping, read-only orientation, or idle hypothesis. "
            "Do not log unless it starts gating a typed action."
        ),
        anti_gaming_note=(
            "Retrospective Tier promotion is a catch condition: if this action "
            "gated a commitment, it should have been logged before resolution."
        ),
    )

