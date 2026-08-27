from ztare.common.equivariance import stable_sha256
from ztare.investment.strategy_control_eligibility import (
    STRATEGY_CONTROL_ELIGIBILITY_FRONTIER_SCHEMA,
)
from ztare.investment.strategy_control_research import (
    compile_strategy_control_research_requests,
)
from ztare.investment.strategy_learning import (
    STRATEGY_COHORT_PLAN_SCHEMA,
    STRATEGY_COHORT_REQUEST_SCHEMA,
)


def test_control_research_adapter_is_order_invariant_and_prioritizes_ready_history():
    signature, phenotype = "a" * 64, "b" * 64

    def cohort(entity):
        body = {
            "schema": STRATEGY_COHORT_REQUEST_SCHEMA, "law_id": "law",
            "peer_entity_id": entity, "mechanism_signature_sha256": signature,
            "mechanism_signature": {"action": "expand", "economic_bridge": "growth"},
            "mechanism_phenotype_sha256": phenotype,
            "mechanism_phenotype": {"strategy_form": "adjacent"},
            "focal_moves": [{"move_sha256": entity.lower() * 32}],
            "search_start_at": "2020-01-01T00:00:00Z",
            "search_end_at": "2026-01-01T00:00:00Z",
        }
        return {**body, "request_sha256": stable_sha256(body)}

    ready, blocked = cohort("AA"), cohort("BB")
    plan_body = {
        "schema": STRATEGY_COHORT_PLAN_SCHEMA, "request_count": 2,
        "requests": [ready, blocked],
    }
    plan = {**plan_body, "plan_sha256": stable_sha256(plan_body)}
    peer_rows = [{
        "peer_entity_id": row["peer_entity_id"], "request_sha256": row["request_sha256"],
        "classification": "pending", "environment": {
            "industry_id": "Semiconductors",
            "mechanism_signature_sha256": signature,
            "mechanism_phenotype_sha256": phenotype,
        },
    } for row in plan["requests"]]
    source_rows = [{
        "request_sha256": row["request_sha256"],
        "required_source_classes": ["sec_filings", "issuer_investor_materials"],
        "required_evidence": ["bounded_adoption_relation"],
    } for row in plan["requests"]]
    frontier_body = {
        "schema": STRATEGY_CONTROL_ELIGIBILITY_FRONTIER_SCHEMA,
        "plan_sha256": plan["plan_sha256"], "as_of": "2026-01-01T00:00:00Z",
        "outcome_contract": {
            "metric_id": "earnings_durability", "unit": "score",
            "minimum_pre_periods": 2, "minimum_post_periods": 1,
        },
        "treatment_periods": [2025], "peer_eligibility": peer_rows,
        "next_source_requests": source_rows,
    }
    frontier = {**frontier_body, "control_frontier_sha256": stable_sha256(frontier_body)}
    readiness = {"history_status": [
        {"entity_id": "AA", "status": "history_ready", "period_count": 4},
        {"entity_id": "BB", "status": "awaiting_history", "period_count": 0},
    ]}
    first = compile_strategy_control_research_requests(frontier, plan, readiness)
    reversed_plan_body = {**plan_body, "requests": list(reversed(plan_body["requests"]))}
    reversed_plan = {
        **reversed_plan_body, "plan_sha256": stable_sha256(reversed_plan_body),
    }
    reversed_frontier_body = {**frontier_body, "plan_sha256": reversed_plan["plan_sha256"]}
    reversed_frontier = {
        **reversed_frontier_body,
        "control_frontier_sha256": stable_sha256(reversed_frontier_body),
    }
    second = compile_strategy_control_research_requests(reversed_frontier, reversed_plan, readiness)
    assert [row["peer_entity_id"] for row in first] == ["AA", "BB"]
    assert [row["information_yield"]["priority_basis"] for row in first] == [
        "negative_classification_can_enter_control_admission_now",
        "negative_classification_still_requires_outcome_history",
    ]
    assert [row["cohort_request_sha256"] for row in first] == [
        row["cohort_request_sha256"] for row in second
    ]
