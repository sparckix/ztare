"""Authority boundary between boundary evidence and a rebuilt context epoch."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from ztare.leanmill.theory_campaign_journal import TheoryCampaignEvent, TheoryCampaignJournal
from ztare.leanmill.theory_context import TheoryLandscapeContext
from ztare.leanmill.theory_ir import content_hash


@dataclass(frozen=True)
class ContextEpochProposal:
    campaign_id: str
    epoch: int
    source_context_hash: str
    evidence_refs: tuple[str, ...]
    proposed_additions: tuple[Mapping[str, Any], ...]
    required_rebuild: Mapping[str, Any]
    schema: str = "leanmill.context_epoch_proposal.v1"

    @property
    def proposal_id(self) -> str:
        return "context-epoch-proposal:" + content_hash(self.to_json(include_id=False))

    def to_json(self, *, include_id: bool = True) -> dict[str, Any]:
        core = {
            "schema": self.schema,
            "campaign_id": self.campaign_id,
            "epoch": self.epoch,
            "source_context_hash": self.source_context_hash,
            "evidence_refs": list(self.evidence_refs),
            "proposed_additions": [dict(row) for row in self.proposed_additions],
            "required_rebuild": dict(self.required_rebuild),
        }
        return {**core, "proposal_id": self.proposal_id} if include_id else core


def propose_context_epoch(
    journal: TheoryCampaignJournal,
    *,
    attempt_id: str,
    campaign_id: str,
    context_hash: str,
    evidence_refs: Sequence[str],
    proposed_additions: Sequence[Mapping[str, Any]],
) -> ContextEpochProposal | None:
    refs = tuple(sorted(set(str(row) for row in evidence_refs if str(row))))
    additions = tuple(dict(row) for row in proposed_additions)
    if not refs or not additions:
        return None
    current = journal.replay()
    epoch = current[-1].epoch if current else 0
    proposal = ContextEpochProposal(
        campaign_id=campaign_id,
        epoch=epoch,
        source_context_hash=context_hash,
        evidence_refs=refs,
        proposed_additions=additions,
        required_rebuild={
            "mint_new_context_hash": True,
            "recompute_all_truth_profiles": True,
            "recompute_all_theory_nodes": True,
            "exactness_requires_new_completeness_receipt": True,
            "no_in_place_context_mutation": True,
        },
    )
    journal.append(
        TheoryCampaignEvent(
            attempt_id=attempt_id,
            campaign_id=campaign_id,
            epoch=epoch,
            context_hash=context_hash,
            event_type="context_epoch_proposed",
            subject_ids=(proposal.proposal_id,),
            input_refs=refs,
            output_refs=("proposal:" + content_hash(proposal.to_json()),),
            evidence_status="proposed",
            authority="frontier_boundary_orchestrator",
        )
    )
    return proposal


def admit_rebuilt_context_epoch(
    journal: TheoryCampaignJournal,
    proposal: ContextEpochProposal,
    rebuilt_context: TheoryLandscapeContext,
    *,
    attempt_id: str,
    authority: str,
) -> TheoryCampaignEvent:
    rows = journal.replay()
    if not rows or rows[-1].context_hash != proposal.source_context_hash:
        raise ValueError("epoch proposal does not bind the journal's current context")
    proposal_event = next(
        (
            row for row in rows
            if row.event_type == "context_epoch_proposed"
            and proposal.proposal_id in row.subject_ids
        ),
        None,
    )
    if proposal_event is None:
        raise ValueError("epoch proposal was not recorded in the campaign journal")
    if rebuilt_context.context_hash == proposal.source_context_hash:
        raise ValueError("rebuilt epoch must mint a new context hash")
    event = TheoryCampaignEvent(
        attempt_id=attempt_id,
        campaign_id=proposal.campaign_id,
        epoch=proposal.epoch + 1,
        context_hash=rebuilt_context.context_hash,
        event_type="evidence_promoted_to_next_epoch",
        subject_ids=(proposal.proposal_id,),
        input_refs=proposal.evidence_refs,
        output_refs=(
            rebuilt_context.completeness_receipt_digest,
            "context:" + rebuilt_context.context_hash,
        ),
        evidence_status="bounded_exact" if rebuilt_context.complete else "witnessed",
        authority=authority,
        parent_event_ids=(proposal_event.event_id,),
    )
    journal.append(event)
    return event


__all__ = [
    "ContextEpochProposal", "admit_rebuilt_context_epoch", "propose_context_epoch",
]
