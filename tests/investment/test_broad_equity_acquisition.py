import json

import yaml

from ztare.common.equivariance import stable_sha256
from ztare.investment.broad_equity_acquisition import (
    compile_broad_equity_acquisition,
    default_broad_equity_policy,
)
from ztare.investment.research_jobs import compile_enrichment_cycle, default_enrichment_policy
from ztare.investment.universe_catalog import CATALOG_SCHEMA
from ztare.investment.workspace import (
    MARKET_SCOUT_POLICY_SCHEMA,
    WORKSPACE_SCHEMA,
    _scout_runs_for_cycle,
    default_market_scout_policy,
    run_workspace_market_scout,
    run_workspace_scheduled_market_scouts,
)


def test_broad_equity_acquisition_is_permutation_and_sector_crowding_invariant():
    def row(symbol, sector, cap, priority, country="United States"):
        return {
            "security_id": f"public_equity:{symbol}", "symbol": symbol, "name": symbol,
            "entity_kind": "public_equity", "security_kind": "common_equity",
            "market_cap": cap, "sector": sector, "industry": f"{sector} industry",
            "country": country, "last_price": 10, "volume": 100, "base_priority": priority,
        }

    base = [
        row("A", "Technology", 3e9, .9), row("B", "Energy", 1e9, .8, "Canada"),
        row("C", "Finance", 20e9, .7, "United Kingdom"),
        row("D", "Health Care", 4e9, .6, "Israel"),
        row("U", "", None, .1, ""), row("X", "Industrials", 5e9, 1.0),
    ]
    policy = default_broad_equity_policy()
    policy.update({"max_selected": 5, "max_per_sector": 1,
                   "max_per_country": 2, "max_per_size_sector_cell": 1,
                   "unknown_cell_quota": 1})

    def compile(rows):
        return compile_broad_equity_acquisition(
            catalog={"schema": CATALOG_SCHEMA, "securities": rows}, policy=policy,
            enrolled_security_ids=["public_equity:X"], current_security_ids=["public_equity:CURRENT"],
            completed_at="2026-08-12T00:00:00Z",
        )

    first = compile(base)
    assert first == compile(list(reversed(base)))
    crowded = compile(base + [row(f"T{index}", "Technology", 2e9 + index, .99) for index in range(50)])

    stable_cells = {row["sector"]: row["security_id"] for row in first["candidates"]
                    if row["sector"] not in {"Technology", "unknown"}}
    crowded_cells = {row["sector"]: row["security_id"] for row in crowded["candidates"]
                      if row["sector"] not in {"Technology", "unknown"}}
    assert stable_cells == crowded_cells
    assert len({row["sector"] for row in crowded["candidates"] if row["sector"] != "unknown"}) == 4
    assert len({row["country"] for row in crowded["candidates"] if row["country"] != "unknown"}) == 4
    assert sum(row["sector"] == "unknown" for row in crowded["candidates"]) == 1
    assert "public_equity:X" not in crowded["selected_security_ids"]
    assert crowded["classification_support"]["geography"]["source_field"] == "country"


def test_scheduled_broad_equity_receipt_flows_into_enrichment_with_narrow_intent(tmp_path):
    defaults = default_market_scout_policy()["intents"]
    assert [row["mode"] for row in defaults] == ["broad_equity", "broad_fund"]

    def security(symbol, sector, cap):
        return {
            "security_id": f"public_equity:{symbol}", "symbol": symbol, "name": symbol,
            "entity_kind": "public_equity", "security_kind": "common_equity",
            "market_cap": cap, "sector": sector, "industry": f"{sector} industry",
            "country": "United States", "last_price": 10, "volume": 100,
            "available_at": "2026-08-12T00:00:00Z",
        }

    rows = [
        security("A", "Technology", 3e9), security("CUR", "Utilities", 3e9),
        security("B", "Energy", 1e9), security("C", "Finance", 20e9),
        security("D", "Health Care", 4e9),
    ]
    catalog_body = {
        "schema": CATALOG_SCHEMA, "retrieved_at": "2026-08-12T00:00:00Z",
        "security_count": len(rows), "securities": rows,
    }
    catalog = {**catalog_body, "catalog_sha256": stable_sha256(catalog_body)}
    broad_policy = default_broad_equity_policy()
    broad_policy.update({"max_selected": 3, "max_per_sector": 1,
                         "max_per_size_sector_cell": 1, "unknown_cell_quota": 0})
    scout_policy = {
        "schema": MARKET_SCOUT_POLICY_SCHEMA, "enabled": True,
        "catalog_refresh_hours": 24, "default_max_results": 10,
        "intents": [
            {"id": "broad", "enabled": True, "mode": "broad_equity",
             "acquisition_policy": broad_policy},
            {"id": "operator-small-energy", "enabled": True,
             "query": "Find US small-cap energy companies"},
        ],
        "activation_boundary": "research queues only",
    }

    def write(relative, payload, *, as_yaml=False):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump(payload, sort_keys=False) if as_yaml else json.dumps(payload),
            encoding="utf-8",
        )

    write("workspace.yaml", {
        "schema": WORKSPACE_SCHEMA, "name": "test", "owner": "test",
        "source_manifest": "sources.yaml", "market_scout_policy": "research_jobs/intents.yaml",
    }, as_yaml=True)
    write("sources.yaml", {
        "schema": "jaggedthoughts-public-source-manifest-v1", "as_of": "now",
        "sources": [{"id": "sec_a", "adapter": "sec_companyfacts", "enabled": True,
                     "entity_id": "A"}],
    }, as_yaml=True)
    write("research_jobs/intents.yaml", scout_policy, as_yaml=True)
    write("universe/catalog-latest.json", catalog)
    write("data/sec_frames/latest.json", {
        "schema": "jaggedthoughts-sec-frame-screen-v1",
        "screen_sha256": "0" * 64,
        "catalog_sha256": catalog["catalog_sha256"],
        "retrieved_at": "2026-08-12T00:30:00Z",
        "frame": "CY2025",
        "coverage": {"research_queue_count": 3},
        "typed_exclusions": {"financial_business_model_count": 1},
        "research_queue": [{
            "security_id": f"public_equity:{symbol}", "symbol": symbol,
            "research_priority_score": score,
            "component_scores": {"cheapness": score},
            "unresolved_residuals": ["durability"],
        } for symbol, score in (("A", .9), ("B", .8), ("D", .7))],
    })
    write("discovery/latest.json", {
        "candidates": [{"entity_id": "CUR", "entity_kind": "public_equity"}],
    })

    cycle = run_workspace_scheduled_market_scouts(tmp_path, now="2026-08-12T01:00:00Z")
    assert [(row["intent_id"], row["mode"]) for row in cycle["results"]] == [
        ("broad", "broad_equity"), ("operator-small-energy", "language")]
    broad_receipt = json.loads((tmp_path / cycle["results"][0]["run_path"]).read_text())
    assert broad_receipt["run_sha256"] == cycle["results"][0]["receipt_sha256"]
    assert set(broad_receipt["selected_security_ids"]) == {
        "public_equity:B", "public_equity:D"}
    assert broad_receipt["selection_contract"]["is_expected_return"] is False
    assert broad_receipt["selection_contract"]["coverage_or_liquidity_only_candidates_admitted"] is False

    runs = _scout_runs_for_cycle(tmp_path, cycle)
    enrichment = compile_enrichment_cycle(
        scout_runs=runs, policy=default_enrichment_policy(),
        enrolled_security_ids=["public_equity:A"], enabled_source_count=0,
        completed_at="2026-08-12T01:01:00Z",
    )
    candidate_b = next(row for row in enrichment["candidates"] if row["security_id"] == "public_equity:B")
    assert len(candidate_b["scout_run_paths"]) == 2
    assert set(enrichment["source_scout_run_ids"]) == {row["run_id"] for row in cycle["results"]}

    legacy_receipt = dict(broad_receipt)
    legacy_receipt.pop("enrichment_frontier")
    legacy_receipt.pop("enrichment_frontier_security_ids")
    (tmp_path / cycle["results"][0]["run_path"]).write_text(
        json.dumps(legacy_receipt), encoding="utf-8",
    )
    rolled = run_workspace_scheduled_market_scouts(
        tmp_path, now="2026-08-12T02:00:00Z",
    )
    assert rolled["status"] == "completed"
    assert rolled["selection_rollforward"] is True
    assert rolled["catalog_refreshed"] is False
    assert rolled["sec_frame_screen"]["refreshed"] is False
    assert json.loads(
        (tmp_path / rolled["results"][0]["run_path"]).read_text()
    )["enrichment_frontier"]

    subscribed = run_workspace_market_scout(
        "Find US small-cap energy companies", tmp_path,
        max_results=7, subscribe_id="operator-energy",
    )
    persisted = yaml.safe_load((tmp_path / "research_jobs/intents.yaml").read_text())
    recurring = next(row for row in persisted["intents"] if row["id"] == "operator-energy")
    assert recurring == {
        "id": "operator-energy", "enabled": True, "mode": "language",
        "query": "Find US small-cap energy companies", "max_results": 7,
    }
    assert subscribed["subscription"]["intent_sha256"] == subscribed["scout"]["intent"]["intent_sha256"]


def test_enrichment_advances_past_an_already_enrolled_initial_scout_batch(tmp_path):
    rows = [{
        "security_id": f"public_equity:{symbol}", "symbol": symbol, "name": symbol,
        "entity_kind": "public_equity", "security_kind": "common_equity",
        "market_cap": 1e9 + index, "sector": f"Sector {index}",
        "industry": f"Industry {index}", "country": "United States",
        "last_price": 10, "volume": 1000 - index, "base_priority": 1 - index / 10,
    } for index, symbol in enumerate(("A", "B", "C", "D", "E", "F"))]
    catalog_body = {"schema": CATALOG_SCHEMA, "securities": rows}
    catalog = {**catalog_body, "catalog_sha256": stable_sha256(catalog_body)}
    policy = default_broad_equity_policy()
    policy.update({
        "max_selected": 2, "max_frontier_candidates": 6,
        "max_per_country": 2, "max_per_sector": 1,
        "max_per_size_sector_cell": 1, "unknown_cell_quota": 0,
    })
    run = compile_broad_equity_acquisition(
        catalog=catalog, policy=policy, completed_at="2026-08-14T00:00:00Z",
    )
    run = {**run, "potential_scope_only": True, "run_id": run["run_id"]}
    run_path = tmp_path / "research_jobs" / "runs" / "broad.json"
    run_path.parent.mkdir(parents=True)
    run_path.write_text(json.dumps(run), encoding="utf-8")
    scout_runs = _scout_runs_for_cycle(tmp_path, {"results": [{
        "intent_id": "broad", "mode": "broad_equity",
        "run_id": run["run_id"], "run_path": "research_jobs/runs/broad.json",
    }]})
    enrichment_policy = default_enrichment_policy()
    enrichment_policy["budgets"].update({"max_equities": 2, "max_funds": 0})
    cycle = compile_enrichment_cycle(
        scout_runs=scout_runs, policy=enrichment_policy,
        enrolled_security_ids=run["selected_security_ids"], enabled_source_count=0,
        completed_at="2026-08-14T00:01:00Z",
    )

    assert len(scout_runs[0]["candidates"]) == 6
    assert set(cycle["selected_security_ids"]).isdisjoint(run["selected_security_ids"])
    assert cycle["selected_count"] == 2
    assert all(
        row["base_priority_source"] == "deterministic_investment_potential"
        for row in cycle["candidates"]
    )


def test_enrichment_preserves_unsupported_funds_as_source_gaps(tmp_path):
    run = {
        "run_id": "funds", "intent": {"styles": ["value"]},
        "candidates": [
            {"security_id": "public_fund:NOPE", "symbol": "NOPE",
             "name": "Unmapped Issuer Value ETF", "entity_kind": "public_fund",
             "last_price": 10, "volume": 1_000, "requested_measurements": ["fees"]},
            {"security_id": "public_fund:GOOD", "symbol": "GOOD",
             "name": "Vanguard Example Value ETF", "entity_kind": "public_fund",
             "last_price": 10, "volume": 1_000, "requested_measurements": ["fees"]},
        ],
    }
    run_path = tmp_path / "research_jobs/runs/funds.json"
    run_path.parent.mkdir(parents=True)
    run_path.write_text(json.dumps(run), encoding="utf-8")
    runs = _scout_runs_for_cycle(tmp_path, {"results": [{
        "intent_id": "funds", "run_path": "research_jobs/runs/funds.json",
    }]})
    cycle = compile_enrichment_cycle(
        scout_runs=runs, policy=default_enrichment_policy(),
        enrolled_security_ids=(), enabled_source_count=0,
        completed_at="2026-08-13T00:00:00Z",
    )
    rows = {row["symbol"]: row for row in cycle["candidates"]}
    assert rows["GOOD"]["selection_status"] == "selected"
    assert rows["NOPE"]["selection_reason"] == "source_capability_unavailable"
    assert rows["NOPE"]["source_activation"]["reason"] == "issuer_adapter_not_registered"
