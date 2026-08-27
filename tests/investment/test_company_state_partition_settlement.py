from ztare.common.equivariance import stable_sha256
from ztare.investment.company_state_partition_frontier import (
    COMPANY_STATE_PARTITION_FRONTIER_SCHEMA,
    NEXT_TRANSITION_EVIDENCE_SCHEMA,
)
from ztare.investment.company_state_partition_settlement import (
    compile_company_state_partition_status,
)


def _frontier():
    states = [
        "valuation_expensive__durability_low", "valuation_expensive__durability_high",
        "valuation_cheap__durability_low", "valuation_cheap__durability_high",
    ]
    definition = (
        "valuation=epoch_empirical_quantile_2;durability=epoch_empirical_quantile_2;"
        "composition=cartesian_product"
    )
    partition = {
        "partition_id": "valuation_2__x__durability_2", "value_levels": 2,
        "durability_levels": 2, "definition": definition, "state_ids": states,
        "program_id": "program", "support_valid": True,
    }
    grammar = {"grammar_digest": "grammar"}
    partition_sha = stable_sha256({
        "partition_id": partition["partition_id"], "value_levels": 2,
        "durability_levels": 2, "definition": definition, "state_ids": states,
        "grammar_digest": "grammar",
    })
    assignments = [
        {"entity_id": "A", "state_id": states[0], "evidence_sha256": "a" * 64,
         "source_refs": ["sec_a", "price_a"]},
        {"entity_id": "B", "state_id": states[-1], "evidence_sha256": "b" * 64,
         "source_refs": ["sec_b", "price_b"]},
    ]
    evidence = {
        "schema": NEXT_TRANSITION_EVIDENCE_SCHEMA, "partition_sha256": partition_sha,
        "source_epoch": "2026-06-30", "target_epoch": "2026-09-30",
        "settlement_not_before": "2026-09-30T23:59:59Z", "benchmark_id": "SPY",
        "min_years": 3, "source_entity_count": 2,
        "source_entity_ids_sha256": stable_sha256(["A", "B"]),
        "source_assignments_sha256": stable_sha256(assignments),
        "minimum_target_entity_count": 2, "signal_authority": False,
        "capital_authority": False,
    }
    evidence["evidence_id"] = (
        "company-state-transition:2026-06-30:2026-09-30:"
        + stable_sha256(evidence)[:16]
    )
    activation = {
        "status": "future_research_activation", "partition_id": partition["partition_id"],
        "partition_sha256": partition_sha,
        "source_snapshot": {"epoch": "2026-06-30", "assignments": assignments},
        "next_evidence_identity": evidence, "signal_authority": False,
        "model_fit_authority": False, "capital_authority": False,
    }
    activation["activation_sha256"] = stable_sha256(activation)
    body = {
        "schema": COMPANY_STATE_PARTITION_FRONTIER_SCHEMA,
        "authority": "research_activation_only", "grammar": grammar,
        "closure": {"frontier_program_ids": ["program"]},
        "candidate_partitions": [partition], "activation": activation,
    }
    return {**body, "partition_frontier_sha256": stable_sha256(body)}


def test_settlement_horizon_boundary_precedes_evidence_access(tmp_path):
    frontier = _frontier()
    before = compile_company_state_partition_status(
        frontier, workspace=tmp_path, as_of="2026-09-30T23:59:58Z",
    )
    due = compile_company_state_partition_status(
        frontier, workspace=tmp_path, as_of="2026-09-30T23:59:59Z",
    )

    assert before["status"] == "horizon_not_reached"
    assert due["status"] == "evidence_unavailable" and due["reason"] == "source_run_absent"
    assert before["activation_sha256"] == due["activation_sha256"]
    assert before["capital_authority"] is due["capital_authority"] is False
