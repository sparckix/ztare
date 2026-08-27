import json

from ztare.common.equivariance import stable_sha256
from ztare.investment.broad_equity_acquisition import (
    compile_broad_equity_acquisition,
    default_broad_equity_policy,
)
from ztare.investment.sec_frame_screen import (
    REGISTRY_URL,
    _frame_specs,
    _frame_url,
    compile_sec_frame_acquisition_run,
    compile_sec_frame_priority_candidates,
    hydrate_sec_annual_frame_screen,
)
from ztare.investment.universe_catalog import CATALOG_SCHEMA


def test_sec_frame_screen_is_source_bound_point_in_time_and_ranks_potential(tmp_path):
    securities = [{
        "security_id": f"public_equity:{symbol}", "symbol": symbol, "name": symbol,
        "entity_kind": "public_equity", "security_kind": "common_equity",
        "market_cap": market_cap, "volume": 200_000, "sector": "Industrials",
        "industry": "Widgets",
    } for symbol, market_cap in (
        ("A", 500_000_000.0), ("B", 500_000_000.0), ("NOSEC", 500_000_000.0),
    )]
    catalog_body = {
        "schema": CATALOG_SCHEMA, "retrieved_at": "2026-01-01T00:00:00Z",
        "security_count": len(securities), "securities": securities,
    }
    catalog = {**catalog_body, "catalog_sha256": stable_sha256(catalog_body)}
    path = tmp_path / "universe/catalog-latest.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(catalog), encoding="utf-8")

    payloads = {REGISTRY_URL: {
        "fields": ["cik", "name", "ticker", "exchange"],
        "data": [[2, "A", "A", "Nasdaq"], [1, "B", "B", "NYSE"]],
    }}
    values = {
        "revenue": (100.0, 100.0), "net_income": (20.0, 5.0),
        "operating_cash_flow": (30.0, 8.0), "capital_expenditure": (5.0, 6.0),
        "assets": (100.0, 100.0), "liabilities": (20.0, 80.0), "cash": (30.0, 5.0),
    }
    for metric_id, tag, frame in _frame_specs("CY2025"):
        if metric_id == "revenue" and tag == "Revenues":
            rows = []
        else:
            rows = [{
                "accn": f"accn-{cik}-{tag}", "cik": cik, "entityName": symbol,
                "end": "2025-12-31", "val": values[metric_id][cik - 1],
            } for cik, symbol in ((1, "A"), (2, "B"))]
        payloads[_frame_url(tag, frame)] = {
            "taxonomy": "us-gaap", "tag": tag, "ccp": frame,
            "uom": "USD", "data": rows,
        }

    def fetch(url):
        return json.dumps(payloads[url], sort_keys=True).encode()

    result = hydrate_sec_annual_frame_screen(
        tmp_path, frame="CY2025", retrieved_at="2026-08-13T12:00:00Z", fetch=fetch,
    )

    assert result["coverage"] == {
        "catalog_common_equity_count": 3, "ticker_cik_join_count": 2,
        "ticker_cik_join_ratio": 2 / 3, "ticker_registry_gap_count": 1,
        "unique_cik_accounting_candidate_count": 2,
        "joined_security_count_by_metric": {
            "revenue": 2, "net_income": 2, "operating_cash_flow": 2,
            "capital_expenditure": 2, "assets": 2, "liabilities": 2, "cash": 2,
        },
        "fully_comparable_ranked_count": 2, "investable_ranked_count": 2,
        "research_queue_count": 1,
    }
    assert [row["symbol"] for row in result["ranked_candidates"]] == ["B", "A"]
    assert result["ranked_candidates"][0]["coordinates"]["free_cash_flow_yield_proxy"] == 5e-8
    assert set(result["ranked_candidates"][0]["component_scores"]) == {
        "cheapness", "earnings_power", "quality", "balance_sheet_risk",
    }
    assert set(result["ranked_candidates"][0]["doctrine_ranks"]) == {
        "balanced_quality_value_proxy", "quality_resilience_proxy", "value_proxy",
    }
    priorities = compile_sec_frame_priority_candidates(result)
    assert [row["symbol"] for row in priorities["candidates"]] == ["B"]
    policy = default_broad_equity_policy()
    policy.update({"max_selected": 1, "unknown_cell_quota": 1})
    unprioritized = compile_broad_equity_acquisition(
        catalog=catalog, policy=policy, completed_at="2026-08-13T12:00:01Z",
    )
    prioritized = compile_broad_equity_acquisition(
        catalog=catalog, policy=policy, priority_candidates=priorities["candidates"],
        completed_at="2026-08-13T12:00:01Z",
    )
    assert unprioritized["selected_security_ids"] == ["public_equity:A"]
    assert prioritized["selected_security_ids"] == ["public_equity:B"]
    acquisition = compile_sec_frame_acquisition_run(catalog, result)
    assert acquisition["selected_security_ids"] == ["public_equity:B"]
    assert acquisition["potential_scope_only"] is True
    assert acquisition["run_sha256"] == stable_sha256({
        key: value for key, value in acquisition.items() if key != "run_sha256"
    })
    assert result["ranking_contract"]["is_expected_return"] is False
    assert result["capital_authority"] is False
    assert all(row["availability_mode"] == "retrieval_only" for row in result["source_receipts"])
    observations = [json.loads(row) for row in (tmp_path / result["paths"]["observations"]).read_text().splitlines()]
    assert len(observations) == 14
    assert {row["available_at"] for row in observations} == {"2026-08-13T12:00:00Z"}
    assert all(row["source_ref"].startswith("sec_frame_") for row in observations)
    compile_sec_frame_priority_candidates,
