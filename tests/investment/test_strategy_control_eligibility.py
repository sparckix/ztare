from ztare.common.equivariance import stable_sha256
from ztare.investment.institutional_learning import CAUSAL_PANEL_ROW_SCHEMA
from ztare.investment.strategy_control_eligibility import (
    compile_strategy_control_eligibility_frontier,
)
from ztare.investment.strategy_learning import (
    STRATEGY_COHORT_PLAN_SCHEMA,
    STRATEGY_COHORT_REQUEST_SCHEMA,
    STRATEGY_COHORT_RESULT_SCHEMA,
    compile_strategy_cohort_research_result,
)


def test_related_family_adoption_removes_an_otherwise_admissible_control():
    signature, phenotype = "s" * 64, "p" * 64
    environment = {
        "industry_id": "Semiconductors",
        "mechanism_signature_sha256": signature,
        "mechanism_phenotype_sha256": phenotype,
    }
    request_body = {
        "schema": STRATEGY_COHORT_REQUEST_SCHEMA,
        "created_at": "2026-01-01T00:00:00Z",
        "peer_entity_id": "PEER",
        **environment,
        "search_start_at": "2020-01-01T00:00:00Z",
        "search_end_at": "2026-01-01T00:00:00Z",
        "required_source_classes": ["sec_filings", "issuer_investor_materials"],
    }
    request = {**request_body, "request_sha256": stable_sha256(request_body)}
    plan_body = {
        "schema": STRATEGY_COHORT_PLAN_SCHEMA,
        "request_count": 1,
        "requests": [request],
    }
    plan = {**plan_body, "plan_sha256": stable_sha256(plan_body)}
    source = {
        "url": "https://example.com/filing", "source_kind": "filing",
        "published_at": "2025-01-01T00:00:00Z", "supports": ["bounded search"],
    }

    def result(classification, events):
        return compile_strategy_cohort_research_result({
            "schema": STRATEGY_COHORT_RESULT_SCHEMA,
            "request_sha256": request["request_sha256"],
            "peer_entity_id": "PEER",
            "mechanism_signature_sha256": signature,
            "mechanism_phenotype_sha256": phenotype,
            "classification": classification,
            "assessed_at": "2026-01-01T00:00:00Z",
            "coverage": {
                "sec_filings_searched": True, "issuer_materials_searched": True,
                "search_start_at": request["search_start_at"],
                "search_end_at": request["search_end_at"],
            },
            "events": events, "sources": [source], "rationale": "bounded review",
        }, request)

    def panel_row(entity, period, *, treated, treatment_period=None):
        return {
            "schema": CAUSAL_PANEL_ROW_SCHEMA,
            "unit_id": f"{phenotype[:12]}:{entity}", "period_index": period,
            "treated_group": treated, "treatment_period": treatment_period,
            "treatment_event_sha256": "e" * 64 if treated else None,
            "treatment_timing_status": (
                "exact_adoption_event" if treated else "never_treated_as_of_panel"
            ),
            "outcome_metric_id": "earnings_durability", "outcome_unit": "score",
            "environment": environment,
        }

    panel = [
        panel_row("FOCAL", period, treated=True, treatment_period=2025)
        for period in (2023, 2024, 2025)
    ] + [panel_row("PEER", period, treated=False) for period in (2023, 2024)]
    law = {
        "outcome_metric_id": "earnings_durability",
        "validation": {"minimum_pre_periods": 2, "minimum_post_periods": 1},
    }
    no_adoption = result("no_family_adoption_found", [])
    admitted = compile_strategy_control_eligibility_frontier(plan, [no_adoption], panel, law)
    assert admitted["admissible_controls"][0]["peer_entity_id"] == "PEER"

    event = {
        "event_id": "adjacent-acquisition", "description": "Adjacent acquisition",
        "occurred_at": "2024-01-01T00:00:00Z", "available_at": "2024-01-02T00:00:00Z",
        "implementation_mode": "acquisition", "implementation_state": "completed",
        "focal_relation": {
            "strategy_form": "same", "addressed_actor_profile": "same",
            "implementation_mode": "same", "operating_object_scope": "different",
        },
        "source_urls": [source["url"]],
    }
    contaminated = compile_strategy_control_eligibility_frontier(
        plan, [result("family_adoption_only", [event])], panel, law,
    )
    assert contaminated["admissible_controls"] == []
    assert contaminated["peer_eligibility"][0]["kill_reasons"] == [
        "related_family_adoption_contaminates_control"
    ]

    terminal = compile_strategy_control_eligibility_frontier(
        plan, [], panel, law,
        terminal_gap_request_sha256s=[request["request_sha256"]],
    )
    assert terminal["peer_eligibility"][0]["classification"] == "terminal_source_gap"
    assert terminal["next_source_requests"] == []
