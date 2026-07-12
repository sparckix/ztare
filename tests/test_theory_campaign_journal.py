from __future__ import annotations

import json

import pytest

from ztare.leanmill.theory_campaign_journal import (
    TheoryCampaignEvent,
    TheoryCampaignJournal,
    materialize_campaign_views,
)


def event(**overrides):
    values = {
        "attempt_id": "attempt-1",
        "campaign_id": "campaign-1",
        "epoch": 0,
        "context_hash": "context-a",
        "event_type": "theory_presentation_submitted",
        "subject_ids": ("node-1",),
        "created_at": "2026-07-09T00:00:00Z",
    }
    values.update(overrides)
    return TheoryCampaignEvent(**values)


def test_content_bound_event_rejects_mutated_identity():
    row = event()
    raw = row.to_json()
    raw["context_hash"] = "context-b"
    with pytest.raises(ValueError, match="event_id"):
        TheoryCampaignEvent.from_json(raw)


def test_append_is_idempotent_and_materializes_views(tmp_path):
    journal = TheoryCampaignJournal(tmp_path / "campaign.jsonl")
    first = event()
    second = event(
        event_type="conditional_consequence_proved",
        subject_ids=("consequence-1",),
        parent_event_ids=(first.event_id,),
        created_at="2026-07-09T00:00:01Z",
    )
    assert journal.append(first)
    assert not journal.append(first)
    assert journal.append(second)
    views = journal.views()
    assert views.theory_archive["node-1"] == first
    assert views.proof_panel["consequence-1"] == second
    assert len(journal.replay()) == 2


def test_context_change_requires_next_epoch_and_new_hash():
    first = event()
    with pytest.raises(ValueError, match="multiple context"):
        materialize_campaign_views(
            (first, event(context_hash="context-b", created_at="2026-07-09T00:00:01Z"))
        )
    with pytest.raises(ValueError, match="new context"):
        materialize_campaign_views(
            (first, event(epoch=1, created_at="2026-07-09T00:00:01Z"))
        )
    next_epoch = event(
        epoch=1,
        context_hash="context-b",
        event_type="formula_added",
        subject_ids=("formula-2",),
        parent_event_ids=(first.event_id,),
        created_at="2026-07-09T00:00:01Z",
    )
    assert materialize_campaign_views((first, next_epoch)).latest_epoch == 1


def test_replay_fails_on_truncated_or_unknown_event(tmp_path):
    path = tmp_path / "campaign.jsonl"
    path.write_text(json.dumps({"schema": "bad"}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 1"):
        TheoryCampaignJournal(path).replay()
