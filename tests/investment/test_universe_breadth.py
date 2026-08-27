from ztare.investment.universe_breadth import compile_universe_breadth_audit


def test_breadth_audit_is_order_invariant_and_keeps_unknown_classification():
    catalog_rows = [
        {"symbol": "A", "entity_kind": "public_equity", "security_kind": "common_equity",
         "market_cap": 3e9, "sector": "Technology", "industry": "Software"},
        {"symbol": "B", "entity_kind": "public_equity", "security_kind": "common_equity",
         "market_cap": 20e9, "sector": "Energy", "industry": "Oil"},
        {"symbol": "F", "entity_kind": "public_fund", "security_kind": "exchange_traded_fund"},
        {"symbol": "W", "entity_kind": "public_equity", "security_kind": "other_listed_security"},
    ]
    candidates = [
        {"entity_id": "A", "entity_kind": "public_equity", "rank": 1, "rank_score": .6,
         "screen_status": "qualified", "criteria": [
             {"criterion_id": "quality", "observed": .6, "operator": "ge", "threshold": .5}]},
        {"entity_id": "F", "entity_kind": "public_fund", "rank": 2, "rank_score": .6,
         "screen_status": "qualified", "criteria": [
             {"criterion_id": "return", "observed": .07, "operator": "ge", "threshold": .06}]},
        {"entity_id": "B", "entity_kind": "public_equity", "rank": 3, "rank_score": .49,
         "screen_status": "monitor", "criteria": [
             {"criterion_id": "quality", "observed": .49, "operator": "ge", "threshold": .5}]},
    ]
    policy = {
        "equities": {"universe": "enrolled_sec_companies", "minimum_score": .5,
                     "criteria": [{"id": "quality"}]},
        "funds": {"universe": "compiled_watchlists", "minimum_score": .5,
                  "criteria": [{"id": "return"}]},
    }
    scout_runs = [
        {"run_id": "eq", "intent": {"entity_kinds": ["public_equity"], "capitalization": "mid",
                                        "styles": ["value"]}, "candidates": [catalog_rows[0]]},
        {"run_id": "fund", "intent": {"entity_kinds": ["public_fund"], "capitalization": "mid",
                                          "styles": ["value"]}, "candidates": [catalog_rows[2]]},
    ]
    scout_cycle = {"results": [
        {"run_id": "eq", "intent_id": "eq", "eligible_count": 1, "returned_count": 1},
        {"run_id": "fund", "intent_id": "fund", "eligible_count": 1, "returned_count": 1},
    ]}

    def compile(rows, ranked):
        return compile_universe_breadth_audit(
            catalog={"securities": rows}, discovery_policy=policy,
            discovery_run={"candidates": ranked},
            opportunity_book={"candidates": []}, scout_cycle=scout_cycle,
            scout_runs=scout_runs,
        )

    first = compile(catalog_rows, candidates)
    permuted = compile(list(reversed(catalog_rows)), list(reversed(candidates)))

    assert first["source_universe"] == permuted["source_universe"]
    assert first["threshold_sensitivity"] == permuted["threshold_sensitivity"]
    assert first["breadth_verdict"] == permuted["breadth_verdict"]
    assert first["breadth_verdict"]["active_ingress_is_mid_cap_value_only"] is True
    assert first["source_universe"]["profile"]["dimensions"]["style"]["unknown_count"] == 3


def test_breadth_audit_exposes_declared_and_active_orthogonal_ingress():
    catalog = [
        {"symbol": "A", "entity_kind": "public_equity", "security_kind": "common_equity",
         "market_cap": 3e9, "country": "United States", "sector": "Technology"},
        {"symbol": "F", "entity_kind": "public_fund", "security_kind": "exchange_traded_fund"},
    ]
    equity_run = {
        "run_id": "eq", "schema": "jaggedthoughts-broad-equity-acquisition-run-v1",
        "candidates": [catalog[0]],
        "coverage": {"selected": {
            "size_counts": {"mid": 1}, "country_counts": {"United States": 1},
            "sector_counts": {"Technology": 1},
        }},
    }
    fund_run = {
        "run_id": "fund", "schema": "jaggedthoughts-broad-fund-scout-v1",
        "selected": [{"security_id": "public_fund:F", "entity_id": "F"}],
        "selected_coverage": {"size": {"large": 1}, "region": {"global": 1}},
    }
    cycle = {"results": [
        {"run_id": "eq", "intent_id": "eq", "mode": "broad_equity",
         "eligible_count": 1, "returned_count": 1},
        {"run_id": "fund", "intent_id": "fund", "mode": "broad_fund",
         "eligible_count": 1, "returned_count": 1},
    ]}
    audit = compile_universe_breadth_audit(
        catalog={"securities": catalog},
        discovery_policy={"equities": {}, "funds": {}},
        discovery_run={"candidates": []}, opportunity_book={"candidates": []},
        scout_policy={"intents": [
            {"id": "eq", "mode": "broad_equity", "enabled": True},
            {"id": "fund", "mode": "broad_fund", "enabled": True},
        ]},
        scout_cycle=cycle, scout_runs=[equity_run, fund_run],
    )

    assert audit["funnel"]["branches"]["public_fund"]["scout_returned"] == 1
    assert audit["active_ingress_boundary"]["declared_orthogonal_policy"] is True
    assert audit["active_ingress_boundary"]["latest_cycle_is_orthogonal"] is True
    assert audit["breadth_verdict"]["verdict"] == (
        "broad_catalog_orthogonal_periodic_ingress_bounded_deep_screen"
    )
