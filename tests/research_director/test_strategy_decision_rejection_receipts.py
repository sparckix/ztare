"""A card approved by submit_strategy_card_batch is never silently dropped:
it is either written to the ledger or returned as an explicit per-card
rejection receipt naming the failing field. written + rejected == submitted."""

import json

from ztare.research_director.strategy_office import _meta_card
from ztare.research_director.strategy_decision_policy import (
    STRATEGY_LEDGER,
    StrategyCardBatchSubmission,
    submit_strategy_card_batch,
)


def _submit(project_dir, cards):
    return submit_strategy_card_batch(StrategyCardBatchSubmission(
        project_dir=project_dir,
        cards=cards,
        source_ref="test:strategy_office",
        policy="direct",
    ))


def test_meta_card_direct_policy_lands_in_ledger(tmp_path):
    card = _meta_card("query budget exhausted before commit — escalate", {"rounds": 3})
    out = _submit(tmp_path, [card])
    assert out["recommendation"] == "approve"
    assert out["written_card_count"] == 1
    assert out["rejected_card_count"] == 0
    ledger = tmp_path / "workspace" / STRATEGY_LEDGER
    rows = [json.loads(l) for l in ledger.read_text().splitlines() if l.strip()]
    assert any(str(r.get("failure_family", "")).startswith("strategy_office:meta:") for r in rows)


def test_duplicate_card_yields_explicit_rejection_receipt(tmp_path):
    card = _meta_card("leaf committed no experiments", {"rounds": 2})
    first = _submit(tmp_path, [card])
    assert first["written_card_count"] == 1

    # same failure_family → write_proposal_cards dedups; the drop must be loud
    second = _submit(tmp_path, [_meta_card("leaf committed no experiments", {"rounds": 3})])
    assert second["recommendation"] == "approve"
    assert second["written_card_count"] == 0
    assert second["rejected_card_count"] == 1
    receipt = second["rejected_cards"][0]
    assert receipt["failing_field"] == "failure_family_sha"
    assert receipt["failure_family_sha"]
    assert "duplicate" in receipt["reason"]
    # the silent case is impossible: every submitted card is accounted for
    assert second["written_card_count"] + second["rejected_card_count"] == 1


def test_written_plus_rejected_sums_to_submitted(tmp_path):
    cards = [
        _meta_card("query budget exhausted before commit — escalate", {"rounds": 1}),
        _meta_card("query budget exhausted before commit — escalate", {"rounds": 2}),  # in-batch dup
        _meta_card("leaf committed no experiments", {"rounds": 1}),
    ]
    out = _submit(tmp_path, cards)
    assert out["written_card_count"] + out["rejected_card_count"] == len(cards)
    assert out["written_card_count"] == 2
    assert out["rejected_card_count"] == 1
