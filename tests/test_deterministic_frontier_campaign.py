from __future__ import annotations

from ztare.common.kernel_action_schema import validate_kernel_action_schema
from ztare.leanmill.deterministic_frontier_campaign import run_deterministic_frontier_campaign
from ztare.leanmill.finite_model_census import enumerate_magma_model_universe
from ztare.leanmill.finite_theory_context import build_formal_theory_context
from ztare.leanmill.magma_law_universe import anonymous_magma_signature, magma_laws_through_order
from ztare.leanmill.theory_campaign_journal import TheoryCampaignJournal


def test_fake_agent_campaign_freezes_diverse_nodes_and_prices_queries(tmp_path):
    signature = anonymous_magma_signature()
    laws = magma_laws_through_order(2)
    context = build_formal_theory_context(
        signature=signature,
        formulas=tuple(row.axiom for row in laws),
        universe=enumerate_magma_model_universe(signature, carrier_sizes=(2,)),
    )
    journal = TheoryCampaignJournal(tmp_path / "events.jsonl")
    result = run_deterministic_frontier_campaign(
        context,
        campaign_id="test-campaign",
        attempt_id="attempt-1",
        journal=journal,
        max_finalists=4,
    )
    assert 1 < len(result.finalist_node_ids) <= 4
    assert result.ranked_queries
    assert all(len(row["formula_ids"]) == 2 for row in result.finalists)
    assert all(row["extent_size"] >= 2 for row in result.finalists)
    assert len(result.workbench_receipts) == len(result.finalist_node_ids)
    assert len(journal.views().finalists) == len(result.finalist_node_ids)
    assert result.to_json()["provider_calls"] == 0
    assert all(
        validate_kernel_action_schema(row["kernel_action"])[0]
        for row in result.ranked_queries
    )
