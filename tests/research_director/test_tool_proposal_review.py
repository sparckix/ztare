from __future__ import annotations

import time


def test_tool_proposal_review_collects_absent_hung_model(tmp_path):
    from ztare.research_director import tool_proposal_review as tpr

    rows = [{
        "proposal_sha256": "abc123",
        "proposal": {"proposed_capability_id": "x", "gap_statement": "g", "target_artifact": "workspace/x.json"},
        "status": "queued",
        "tool_synthesis_status": "awaiting_strategy_office_batch_decision",
    }]
    from ztare.common.leaf_workbench_proposals import PROPOSAL_LEDGER

    ledger = tmp_path / "workspace" / PROPOSAL_LEDGER
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text("\n".join([__import__("json").dumps(row) for row in rows]) + "\n", encoding="utf-8")

    def hung(*_args, **_kwargs):
        time.sleep(0.2)
        return '{"position":"approve","rationale":"ok","evidence_refs":["proposal_sha256:abc123"]}'

    specs = [tpr.ToolProposalReviewerSpec(actor_id="hung", transport="api")]
    positions = tpr.collect_tool_proposal_review_positions(tmp_path, specs=specs, dispatcher=lambda *_a: hung(), timeout_seconds=0)
    assert any(pos.metadata.get("absent") for pos in positions)
    assert any(pos.position == "abstain" for pos in positions)
