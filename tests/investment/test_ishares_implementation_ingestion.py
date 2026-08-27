import json

import yaml

from ztare.common.equivariance import stable_sha256
from ztare.investment import sources
from ztare.investment.golden_store import GoldenStore, record_opportunity_watchlist
from ztare.investment.watchlist import compile_fund_holdings_graph


def test_holdings_publication_advances_watchlist_availability(tmp_path):
    (tmp_path / "data/fund_holdings").mkdir(parents=True)
    (tmp_path / "sources.yaml").write_text(yaml.safe_dump({"sources": []}))
    snapshot = {
        "schema": "jaggedthoughts-fund-holdings-snapshot-v1",
        "entity_id": "FUND", "as_of": "2026-08-10T00:00:00Z",
        "available_at": "2026-08-12T00:00:00Z", "source_id": "issuer:FUND",
        "holdings": [{"identifier": "ACME", "security_name": "Acme", "weight": 1.0}],
    }
    snapshot["snapshot_sha256"] = stable_sha256(snapshot)
    (tmp_path / "data/fund_holdings/fund.json").write_text(json.dumps(snapshot))

    graph = compile_fund_holdings_graph(
        root=tmp_path, as_of="2026-08-11T00:00:00Z",
        fund_entity_ids={"FUND"}, target_entity_id="FUND",
    )
    body = {
        "schema": "jaggedthoughts-opportunity-watchlist-result-v1",
        "watchlist_id": "funds", "as_of": "2026-08-11T00:00:00Z",
        "compiler_available_at": "2026-08-01T00:00:00Z",
        "factor_premium_source_refs": ["factor:market"], "candidates": [],
        "fund_holdings_graph": graph,
    }
    watchlist = {**body, "watchlist_sha256": stable_sha256(body)}
    store = GoldenStore(tmp_path / "store.sqlite3")
    leaf = store.get_leaf(record_opportunity_watchlist(
        store, owner="paper", watchlist=watchlist,
    ))

    assert graph["fund_snapshot_entity_ids"] == ["FUND"]
    assert leaf["available_at"] == "2026-08-12T00:00:00Z"
    assert "issuer:FUND" in leaf["source_refs"]


def test_ishares_ingestion_normalizes_implementation_evidence(tmp_path, monkeypatch):
    characteristics = {"containersByNameMap": {"default": {"dataPointsByNameMap": {
        "priceEarnings": {"value": 18.5, "asOfDate": 20260807},
        "priceBook": {"value": 2.1, "asOfDate": 20260807},
        "numHoldings": {"value": 6},
    }}}}
    facts = {"dataPoints": {
        "totalNetAssetsFundLevel": {"formattedValue": "1,250,000", "formattedAsOfDate": "Aug 11, 2026"},
        "thirtyDayMedianBidAskSpread": {"formattedValue": "0.03%", "formattedAsOfDate": "Aug 10, 2026"},
        "thirtyDayAverageVolume": {"formattedValue": "42,500", "formattedAsOfDate": "Aug 10, 2026"},
    }}
    encoded = lambda value: json.dumps(value).replace('"', "&quot;")
    product = (
        '<title>TEST iShares ETF</title>'
        f'<walrus-render-on-client componentkey="PortfolioCharacteristicsV3" componentprops="{encoded(characteristics)}">'
        f'<walrus-render-on-client componentkey="KeyFundFactsV3" componentprops="{encoded(facts)}">'
        '<a href="/test/latest-holdings.csv">holdings</a>'
        '"name":"Expense Ratio:","value":"0.20"'
    ).encode()
    holdings = (
        'Fund Holdings as of,"Aug 11, 2026"\n\n'
        "Ticker,Name,Sector,Asset Class,Market Value,Weight (%),Location,Exchange,Quantity\n"
        "A,Alpha,Industrials,Equity,687500,55,United States,NYSE,600\n"
        "A,Another Alpha,Industrials,Equity,437500,35,Canada,TSX,400\n"
        "-,Missing Ticker One,Industrials,Equity,62500,5,India,NSE,50\n"
        "-,Missing Ticker Two,Industrials,Equity,62500,5,India,NSE,50\n"
        "Z,Zero One,Industrials,Equity,0,0,United States,NYSE,0\n"
        "Z,Zero Two,Energy,Equity,0,0,United States,NYSE,0\n"
    ).encode()

    monkeypatch.setattr(
        sources, "_fetch",
        lambda url, **_kwargs: (holdings if url.endswith("latest-holdings.csv") else product, {}),
    )
    receipt, observations = sources._ishares_fundamentals_adapter(
        tmp_path,
        {"id": "ishares_test_fundamentals", "adapter": "ishares_fundamentals", "symbol": "TEST", "entity_id": "TEST", "url": "https://example.com/test"},
        "2026-08-12T00:00:00Z",
    )

    values = {row.metric_id: row.value for row in observations}
    assert values["fund_net_assets"] == 1_250_000
    assert values["median_bid_ask_spread"] == 0.0003
    assert values["average_daily_volume_30d"] == 42_500
    assert values["portfolio_top10_concentration"] == 1.0
    assert round(values["portfolio_holdings_hhi"], 2) == 0.43
    snapshot = json.loads((tmp_path / "data/fund_holdings/test.json").read_text())
    assert {row["identifier"] for row in snapshot["holdings"] if row["country"] == "India"} == {
        "NAME:MISSING TICKER ONE@NSE", "NAME:MISSING TICKER TWO@NSE",
    }
    assert receipt.observation_count == len(observations)


def test_ishares_fund_of_fund_uses_issuer_reported_direct_scope(tmp_path, monkeypatch):
    characteristics = {"containersByNameMap": {"default": {"dataPointsByNameMap": {
        "priceEarnings": {"value": 18.5}, "priceBook": {"value": 2.1},
        "numHoldings": {"value": 1},
    }}}}
    facts = {"dataPoints": {}}
    encoded = lambda value: json.dumps(value).replace('"', "&quot;")
    product = (
        '<title>TEST iShares ETF</title>'
        f'<walrus-render-on-client componentkey="PortfolioCharacteristicsV3" componentprops="{encoded(characteristics)}">'
        f'<walrus-render-on-client componentkey="KeyFundFactsV3" componentprops="{encoded(facts)}">'
        '<a href="/test/latest-holdings.csv">holdings</a>'
        '"name":"Expense Ratio:","value":"0.20"'
    ).encode()
    holdings = (
        'Fund Holdings as of,"Aug 11, 2026"\n\n'
        "Ticker,Name,Sector,Asset Class,Market Value,Weight (%),Location,Exchange,Quantity\n"
        "BASE,Underlying ETF,Financials,Equity,1004000,100.4,United States,NASDAQ,10000\n"
        "A,Lookthrough A,Industrials,Equity,600000,60,United States,NYSE,600\n"
        "B,Lookthrough B,Energy,Equity,400000,40,United States,NYSE,400\n"
    ).encode()
    monkeypatch.setattr(
        sources, "_fetch",
        lambda url, **_kwargs: (holdings if url.endswith("latest-holdings.csv") else product, {}),
    )
    _receipt, observations = sources._ishares_fundamentals_adapter(
        tmp_path,
        {"id": "ishares_test_fundamentals", "adapter": "ishares_fundamentals", "symbol": "TEST", "entity_id": "TEST", "url": "https://example.com/test"},
        "2026-08-12T00:00:00Z",
    )
    snapshot = json.loads((tmp_path / "data/fund_holdings/test.json").read_text())
    assert snapshot["provider_row_count"] == 3 and snapshot["reported_count"] == 1
    assert snapshot["holdings_scope"] == "issuer_reported_direct_holdings_filtered_from_lookthrough"
    assert [row["identifier"] for row in snapshot["holdings"]] == ["BASE@NASDAQ"]
    assert {row.metric_id: row.value for row in observations}["portfolio_holdings_count"] == 1
