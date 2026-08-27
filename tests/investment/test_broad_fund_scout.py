from ztare.common.equivariance import stable_sha256
from ztare.investment.broad_fund_scout import (
    _classify,
    broad_fund_scout_policy,
    compile_broad_fund_scout,
)


def _fund(symbol, name, one_year_return=0.0):
    return {
        "security_id": f"public_fund:{symbol}",
        "symbol": symbol,
        "name": name,
        "entity_kind": "public_fund",
        "security_kind": "exchange_traded_fund",
        "last_price": 25.0,
        "one_year_return": one_year_return,
        "source_id": "public-funds",
        "source_path": "universe/raw/public-funds.json",
        "available_at": "2026-08-12T00:00:00Z",
    }


def _catalog(funds):
    body = {
        "schema": "jaggedthoughts-public-market-catalog-v1",
        "retrieved_at": "2026-08-12T00:00:00Z",
        "security_count": len(funds),
        "source_receipts": [{
            "source_id": "public-funds",
            "raw_path": "universe/raw/public-funds.json",
            "content_sha256": "a" * 64,
        }],
        "securities": funds,
    }
    return {**body, "catalog_sha256": stable_sha256(body)}


def test_permutation_and_same_cell_duplicate_preserve_breadth_and_selection() -> None:
    funds = [
        _fund("ALPV", "Alpha US Large Cap Value ETF", -0.8),
        _fund("BETG", "Beta US Large Cap Growth ETF", 0.9),
        _fund("GAMB", "Gamma US Aggregate Bond ETF", 0.1),
    ]
    policy = broad_fund_scout_policy(max_results=3, max_per_cell=1)
    assert _classify("S&P 500 Value ETF", policy)[0]["region"] == "us"
    baseline = compile_broad_fund_scout(
        _catalog(funds), policy, completed_at="2026-08-13T00:00:00Z",
    )
    transformed = compile_broad_fund_scout(
        _catalog([_fund("ZVAL", "Zeta US Large Cap Value ETF", 99.0), *reversed(funds)]),
        policy, completed_at="2026-08-13T00:00:00Z",
    )

    assert [row["entity_id"] for row in baseline["selected"]] == [
        row["entity_id"] for row in transformed["selected"]
    ]
    assert baseline["selected_cell_count"] == transformed["selected_cell_count"] == 3
    assert baseline["max_selected_in_any_cell"] == transformed["max_selected_in_any_cell"] == 1
    assert all(row["expected_return_used"] is False for row in transformed["selected"])
    assert "one_year_return" in transformed["priority_contract"]["excluded_inputs"]
    assert transformed["selected_required_cell_count"] == baseline["selected_required_cell_count"]
