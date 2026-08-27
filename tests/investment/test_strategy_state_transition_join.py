from ztare.common.equivariance import stable_sha256
from ztare.investment.strategy_state_transition_join import (
    compile_strategy_state_transition_join,
)


def test_strategy_state_join_uses_public_availability_for_post_event_paths():
    block = {
        "source_epoch": "2026-03-31", "target_epoch": "2026-06-30",
        "rows": [{
            "entity_id": "A", "source_state": "low", "target_state": "high",
            "active_return": 0.1, "source_refs": ["facts"],
            "source_evidence_sha256": "source", "target_evidence_sha256": "target",
        }],
    }
    flow = {
        "schema": "jaggedthoughts-company-state-flow-evidence-v1",
        "as_of": "2026-06-30T23:59:59Z", "transition_blocks": [block],
    }
    flow["evidence_sha256"] = stable_sha256(flow)
    event = {
        "implementation_event_sha256": "event", "occurred_at": "2026-03-01T00:00:00Z",
        "available_at": "2026-05-01T00:00:00Z",
        "treatment_timing_status": "exact_adoption_event",
    }
    moves = {
        "schema": "jaggedthoughts-strategy-move-library-v1",
        "moves": [{
            "entity_id": "A", "move_sha256": "move",
            "mechanism_phenotype_sha256": "phenotype", "implementation_event": event,
            "causal_panel_status": "treatment_event_ready",
        }],
    }
    moves["library_sha256"] = stable_sha256(moves)

    result = compile_strategy_state_transition_join(flow, moves)
    assert result["exact_event_issuer_count"] == 1
    assert result["observable_post_event_issuer_count"] == 0
    assert result["fit_qualified_issuer_count"] == 0
    assert result["status"] == "collecting_post_event_paths"
    assert result["event_bundles"][0]["straddling_or_not_yet_observable_count"] == 1
