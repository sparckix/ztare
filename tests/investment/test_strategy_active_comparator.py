from ztare.common.equivariance import stable_sha256
from ztare.investment.strategy_active_comparator import (
    compile_strategy_active_comparator_frontier,
)
from ztare.investment.strategy_learning import (
    STRATEGY_COHORT_PLAN_SCHEMA,
    STRATEGY_COHORT_REQUEST_SCHEMA,
    STRATEGY_COHORT_RESULT_SCHEMA,
    compile_strategy_cohort_research_result,
)


def test_active_comparator_is_relation_only_pre_outcome_and_history_gated():
    phenotype, family = "p" * 64, "f" * 64
    focal_event = {
        "occurred_at": "2022-06-01T00:00:00Z", "available_at": "2022-06-02T00:00:00Z",
        "implementation_state": "operational", "timing_precision": "date",
        "treatment_timing_status": "exact_adoption_event",
        "implementation_event_sha256": "a" * 64,
    }
    request_body = {
        "schema": STRATEGY_COHORT_REQUEST_SCHEMA, "created_at": "2026-01-01T00:00:00Z",
        "peer_entity_id": "ALT", "mechanism_signature_sha256": family,
        "mechanism_phenotype_sha256": phenotype, "industry_id": "Software",
        "focal_moves": [{"implementation_event": focal_event}],
        "required_source_classes": ["sec_filings", "issuer_investor_materials"],
        "search_start_at": "2020-01-01T00:00:00Z", "search_end_at": "2026-01-01T00:00:00Z",
    }
    request = {**request_body, "request_sha256": stable_sha256(request_body)}
    plan_body = {
        "schema": STRATEGY_COHORT_PLAN_SCHEMA, "request_count": 1, "requests": [request],
        "mechanism_environments": [{
            "mechanism_phenotype_sha256": phenotype,
            "mechanism_signature_sha256": family, "industry_id": "Software",
            "focal_moves": [{"entity_id": "FOCAL", "implementation_event": focal_event}],
        }],
    }
    plan = {**plan_body, "plan_sha256": stable_sha256(plan_body)}
    source = {
        "url": "https://example.com/filing", "source_kind": "filing",
        "published_at": "2022-07-01T00:00:00Z", "supports": ["event"],
    }
    raw = {
        "schema": STRATEGY_COHORT_RESULT_SCHEMA, "request_sha256": request["request_sha256"],
        "peer_entity_id": "ALT", "mechanism_signature_sha256": family,
        "mechanism_phenotype_sha256": phenotype, "classification": "family_adoption_only",
        "assessed_at": "2026-01-01T00:00:00Z",
        "coverage": {"sec_filings_searched": True, "issuer_materials_searched": True,
                     "search_start_at": request["search_start_at"],
                     "search_end_at": request["search_end_at"]},
        "events": [{
            "event_id": "alt-organic", "description": "Operational organic alternative",
            "occurred_at": "2022-07-01T00:00:00Z", "available_at": "2022-07-02T00:00:00Z",
            "implementation_mode": "organic_program", "implementation_state": "operational",
            "focal_relation": {"strategy_form": "same", "addressed_actor_profile": "same",
                               "implementation_mode": "different", "operating_object_scope": "same"},
            "source_urls": [source["url"]],
        }],
        "sources": [source], "rationale": "typed active alternative",
    }
    result = compile_strategy_cohort_research_result(raw, request)
    projection_body = {
        "schema": "jaggedthoughts-strategy-phenotype-projection-frontier-v1",
        "plan_sha256": plan["plan_sha256"],
        "certificate": {"scope": {"evidence_epoch": "2026-01-01T00:00:00Z"}},
        "projections": [{"program_id": "projection", "frontier_status": "frontier",
                         "required_relation_fields": ["implementation_mode"]}],
    }
    projection = {
        **projection_body, "projection_frontier_sha256": stable_sha256(projection_body),
    }
    report = lambda year: {"history": [{"observed_at": f"{year}-12-31T00:00:00Z"}]}
    frontier = compile_strategy_active_comparator_frontier(
        plan, projection, [result],
        {"FOCAL": [report(year) for year in (2020, 2021, 2023)],
         "ALT": [report(year) for year in (2020, 2021, 2023)]},
        minimum_independent_focal_firms=1, minimum_independent_alternative_firms=1,
    )
    rows = {row["entity_id"]: row for row in frontier["comparison_groups"][0]["entities"]}
    assert rows["FOCAL"]["partition"] == "focal"
    assert rows["ALT"]["partition"] == "eligible_active_alternative"
    assert rows["ALT"]["q_phenotype_sha256"] is None
    assert frontier["comparison_groups"][0]["floor_ready_cell_count"] == 1
    assert frontier["outcome_contract"]["metric_id"] == "earnings_durability"
    assert frontier["outcome_contract"]["fiscal_alignment"] == "first_full_fiscal_period_after_index_event"
    assert frontier["causal_estimate_ran"] is False

    missing = compile_strategy_active_comparator_frontier(
        plan, projection, [result], {"FOCAL": [], "ALT": []},
    )
    assert missing["next_company_facts_acquisition_entities"] == ["ALT", "FOCAL"]
