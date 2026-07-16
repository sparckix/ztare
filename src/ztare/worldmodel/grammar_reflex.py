"""Route a catalog-ceiling residual into the governed candidate path.

This module owns proposal identity and delivery only.  It never implements an
operator, calls a scientific leaf, or adopts a carrier.  The ordinary governed
candidate worker consumes current-evidence cards and the single evaluator door
decides whether any resulting executable carrier is admitted.
"""
from __future__ import annotations

from ztare.common.operator_proposal_contract import proposal_identity_sha
from ztare.worldmodel.operator_proposals import propose_operators, write_proposals


def _bind_cards_to_evidence(project, log, cards: list[dict]) -> list[dict]:
    """Bind row coordinates to the visible evidence lifecycle that names them."""
    task_id = ""
    try:
        from ztare.common.leaf_workbench_executor import (
            active_workbench_task_capability_scope,
        )

        task_scope, task = active_workbench_task_capability_scope(project)
        if task_scope:
            task_id = str(task.get("task_id") or "")
    except Exception:  # noqa: BLE001 -- task binding is optional, evidence is not
        task_id = ""
    binding = {
        "schema": "ztare-operator-proposal-evidence-binding-v1",
        "mode": "exact_evidence_epoch",
        "evidence_role": "visible",
        "evidence_ref": "raw/episodes/episode_001.jsonl",
        "evidence_content_sha256": log.content_hash(),
        "row_count": len(log),
    }
    if task_id:
        binding["workbench_task_id"] = task_id
    bound: list[dict] = []
    for source in cards:
        card = dict(source)
        card["evidence_binding"] = dict(binding)
        card["proposal_identity_sha"] = proposal_identity_sha(card)
        bound.append(card)
    return bound


def route_operator_proposals(
    project,
    log,
    ab_result,
    *,
    residual_indices=None,
) -> dict:
    """Persist current-evidence cards for the registered governed consumer."""
    spec = getattr(ab_result, "spec", None)
    cards = _bind_cards_to_evidence(
        project,
        log,
        propose_operators(log, spec, residual_indices),
    )
    written = write_proposals(project, cards)
    return {
        "status": "proposals_routed",
        "result": ab_result,
        "cards": cards,
        "written_count": len(written),
        "dispositions": [],
        "implementation_owner": "governed_carrier",
        "route": {
            "consumer": "operator_proposals_briefing_to_governed_candidate_gate",
            "proposal_identity_shas": [
                str(card.get("proposal_identity_sha") or "") for card in cards
            ],
        },
    }
