from __future__ import annotations

from ztare.leanmill.adapters.generic_finite_evidence import build_evidence_context
from ztare.leanmill.context_epoch import admit_rebuilt_context_epoch, propose_context_epoch
from ztare.leanmill.theory_campaign_journal import TheoryCampaignEvent, TheoryCampaignJournal
from ztare.leanmill.theory_ir import SortDecl, TheorySignature


def _context(*, extra: bool):
    objects = [
        {"object_id": "o0"},
        {"object_id": "o1"},
    ]
    if extra:
        objects.append({"object_id": "o2"})
    return build_evidence_context(
        TheorySignature(name="Evidence", sorts=(SortDecl("Observation"),)),
        adapter_config={
            "completeness_ref": "fixture:complete:v2" if extra else "fixture:complete:v1",
            "objects": objects,
            "hypotheses": [
                {
                    "hypothesis_id": "h0",
                    "satisfied_object_ids": [row["object_id"] for row in objects],
                    "anonymous_shape": {"kind": "predicate"},
                }
            ],
        },
        strata=(),
    )


def test_counterexample_proposal_requires_rebuilt_context_before_epoch_promotion(tmp_path):
    old = _context(extra=False)
    journal = TheoryCampaignJournal(tmp_path / "events.jsonl")
    journal.append(
        TheoryCampaignEvent(
            attempt_id="attempt",
            campaign_id="campaign",
            epoch=0,
            context_hash=old.context_hash,
            event_type="finalist_frozen",
            subject_ids=("node",),
            evidence_status="frozen",
        )
    )
    proposal = propose_context_epoch(
        journal,
        attempt_id="attempt",
        campaign_id="campaign",
        context_hash=old.context_hash,
        evidence_refs=("receipt:counterexample",),
        proposed_additions=({"kind": "raw_counterexample", "object_ref": "o2"},),
    )
    assert proposal is not None
    assert journal.views().latest_epoch == 0

    rebuilt = _context(extra=True)
    event = admit_rebuilt_context_epoch(
        journal,
        proposal,
        rebuilt,
        attempt_id="attempt",
        authority="context-rebuild-authority",
    )
    assert event.epoch == 1
    assert event.context_hash == rebuilt.context_hash
    assert journal.views().latest_epoch == 1
