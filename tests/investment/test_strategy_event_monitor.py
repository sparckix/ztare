from ztare.common.equivariance import stable_sha256
from ztare.investment.strategy_event_monitor import (
    compile_strategy_event_activations,
    compile_strategy_event_monitor,
)
from ztare.investment.strategy_learning import (
    STRATEGY_COHORT_PLAN_SCHEMA,
    STRATEGY_COHORT_REQUEST_SCHEMA,
    STRATEGY_MOVE_LIBRARY_SCHEMA,
    compile_strategy_cohort_research_plan,
    compile_strategy_cohort_research_result,
)


def _request():
    body = {
        "schema": STRATEGY_COHORT_REQUEST_SCHEMA,
        "request_id": "strategy-cohort:phenotype:peer",
        "created_at": "2026-01-01T00:00:00Z", "law_id": "law",
        "mechanism_signature_sha256": "a" * 64,
        "mechanism_signature": {"action": "expand", "economic_bridge": "growth"},
        "mechanism_phenotype_sha256": "b" * 64,
        "mechanism_phenotype": {"strategy_form": "capacity"},
        "industry_id": "Widgets",
        "focal_moves": [{
            "implementation_event": {"implementation_event_sha256": "c" * 64},
        }],
        "peer_entity_id": "PEER", "peer_name": "Peer", "peer_security_id": "equity:PEER",
        "search_start_at": "2020-01-01T00:00:00Z",
        "search_end_at": "2026-01-01T00:00:00Z",
        "required_source_classes": ["sec_filings", "issuer_investor_materials"],
        "required_capability": "subscription_web_research",
        "expected_exit": "typed_equivalent_adoption_classification_or_source_gap",
        "control_use_boundary": "bounded", "capital_authority": False,
    }
    from ztare.investment.strategy_learning import strategy_cohort_query_identity

    body["query_sha256"] = strategy_cohort_query_identity(body)["query_sha256"]
    return {**body, "request_sha256": stable_sha256(body)}


def _result(request):
    raw = {
        "schema": "jaggedthoughts-strategy-cohort-research-result-v2",
        "request_sha256": request["request_sha256"], "peer_entity_id": "PEER",
        "mechanism_signature_sha256": "a" * 64,
        "mechanism_phenotype_sha256": "b" * 64,
        "classification": "no_family_adoption_found",
        "assessed_at": "2026-01-02T00:00:00Z",
        "coverage": {
            "sec_filings_searched": True, "issuer_materials_searched": True,
            "search_start_at": request["search_start_at"],
            "search_end_at": request["search_end_at"],
        },
        "events": [],
        "sources": [
            {"url": "https://example.test/filing", "source_kind": "filing", "published_at": "2025-12-01", "supports": ["bounded filing search"]},
            {"url": "https://example.test/ir", "source_kind": "issuer", "published_at": "2025-12-01", "supports": ["bounded issuer search"]},
        ],
        "rationale": "No matching family event was found in the bounded search.",
        "residuals": ["Undisclosed implementation remains possible."],
    }
    return compile_strategy_cohort_research_result(raw, request)


def test_strategy_event_monitor_reopens_only_on_new_source_or_due_window():
    request = _request()
    result = _result(request)
    baseline = {
        "sec_peer_submissions": {
            "adapter": "sec_submissions", "content_sha256": "d" * 64,
            "receipt_sha256": "e" * 64, "retrieved_at": "2026-01-01T00:00:00Z",
        },
    }
    monitor = compile_strategy_event_monitor(
        request, result, baseline, recorded_at="2026-01-02T00:00:00Z",
    )
    plan_body = {
        "schema": STRATEGY_COHORT_PLAN_SCHEMA, "request_count": 1,
        "requests": [request],
    }
    plan = {**plan_body, "plan_sha256": stable_sha256(plan_body)}
    unchanged = compile_strategy_event_activations(
        plan, {request["request_sha256"]: result}, [monitor], baseline,
        as_of="2026-03-01T00:00:00Z",
    )
    assert unchanged["activation_count"] == 0

    changed = {"sec_peer_submissions": {
        **baseline["sec_peer_submissions"], "content_sha256": "f" * 64,
        "retrieved_at": "2026-02-01T00:00:00Z",
    }}
    activated = compile_strategy_event_activations(
        plan, {request["request_sha256"]: result}, [monitor], changed,
        as_of="2026-02-02T00:00:00Z",
    )
    assert activated["activations"][0]["trigger_kinds"] == ["sec_submissions_changed"]
    assert activated["activations"][0]["search_end_at"] == "2026-02-01T00:00:00Z"
    assert "not-yet-treated" in monitor["negative_evidence_boundary"]

    due = compile_strategy_event_activations(
        plan, {request["request_sha256"]: result}, [monitor], baseline,
        as_of="2026-04-02T00:00:00Z",
    )
    assert due["activations"][0]["trigger_kinds"] == ["issuer_materials_recheck_due"]
    assert due["activations"][0]["search_end_at"] == "2026-04-01T00:00:00Z"


def test_cohort_plan_advances_only_an_activated_query():
    event_body = {
        "event_kind": "adoption",
        "occurred_at": "2025-01-01T00:00:00Z",
        "available_at": "2025-01-02T00:00:00Z",
        "treatment_timing_status": "exact_adoption_event",
    }
    library = {
        "schema": STRATEGY_MOVE_LIBRARY_SCHEMA, "library_sha256": "1" * 64,
        "moves": [{
            "entity_id": "FOCAL", "causal_panel_status": "treatment_event_ready",
            "mechanism": {"action": "expand", "economic_bridge": "growth"},
            "mechanism_signature_sha256": "a" * 64,
            "mechanism_signature": {"action": "expand", "economic_bridge": "growth"},
            "mechanism_phenotype_sha256": "b" * 64,
            "mechanism_phenotype": {"strategy_form": "capacity"},
            "move_sha256": "c" * 64, "option_id": "capacity", "kind": "capacity",
            "description": "Expand capacity", "environment": {},
            "implementation_event": {
                **event_body,
                "implementation_event_sha256": stable_sha256(event_body),
            },
        }],
    }
    catalog = {
        "catalog_sha256": "2" * 64, "retrieved_at": "2026-01-01T00:00:00Z",
        "securities": [
            {"symbol": "FOCAL", "name": "Focal", "entity_kind": "public_equity", "security_kind": "common_equity", "security_id": "equity:FOCAL", "industry": "Widgets", "market_cap": 100},
            {"symbol": "PEER", "name": "Peer", "entity_kind": "public_equity", "security_kind": "common_equity", "security_id": "equity:PEER", "industry": "Widgets", "market_cap": 90},
        ],
    }
    initial = compile_strategy_cohort_research_plan(library, catalog)
    query_sha = initial["requests"][0]["query_sha256"]
    later = compile_strategy_cohort_research_plan(
        library, {**catalog, "retrieved_at": "2026-02-01T00:00:00Z"},
        prior_plan=initial,
    )
    assert later["requests"][0]["search_end_at"] == "2026-01-01T00:00:00Z"
    advanced = compile_strategy_cohort_research_plan(
        library, catalog, prior_plan=initial,
        search_end_by_query_sha256={query_sha: "2026-01-15T00:00:00Z"},
    )
    assert advanced["requests"][0]["search_end_at"] == "2026-01-15T00:00:00Z"
    assert advanced["requests"][0]["query_sha256"] == query_sha
