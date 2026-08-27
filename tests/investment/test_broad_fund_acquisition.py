from ztare.common.equivariance import stable_sha256
from ztare.investment.broad_fund_acquisition import compile_broad_fund_acquisition_plan
from ztare.investment.broad_fund_scout import _cell_id, broad_fund_scout_policy, _classify
from ztare.investment.sources import PUBLIC_SOURCE_MANIFEST_SCHEMA, SOURCE_RUN_SCHEMA
from ztare.investment.universe_catalog import CATALOG_SCHEMA


def _sealed(body, field):
    return {**body, field: stable_sha256(body)}


def test_plan_binds_inputs_batches_sources_and_deduplicates_jobs():
    policy = broad_fund_scout_policy(max_results=4)
    names = {
        "DMV": "First Trust Developed Markets Ex-US Value Fund",
        "DMS": "First Trust Developed Markets Ex-US Value Peer Fund",
        "EMV": "First Trust Emerging Markets Value Fund",
        "EMS": "First Trust Emerging Markets Value Peer Fund",
        "USV": "First Trust US Large Cap Value Fund",
        "USP": "First Trust US Large Cap Value Peer Fund",
    }
    securities = [{
        "security_id": f"public_fund:{symbol}", "symbol": symbol, "name": name,
        "entity_kind": "public_fund", "security_kind": "exchange_traded_fund",
        "last_price": 10.0,
    } for symbol, name in names.items()]
    catalog = _sealed({"schema": CATALOG_SCHEMA, "securities": securities}, "catalog_sha256")
    cells = {_cell_id(cell): cell for cell in (_classify(name, policy)[0] for name in names.values())}
    scout = _sealed({
        "schema": "jaggedthoughts-broad-fund-scout-v1",
        "catalog_sha256": catalog["catalog_sha256"], "policy_sha256": policy["policy_sha256"],
        "selected": [{"cell_id": cell_id, "cell": cell} for cell_id, cell in cells.items()],
    }, "scout_sha256")
    factor_ids = (
        "nyu_us_implied_erp", "yahoo_spy_daily", "yahoo_iwd_daily", "yahoo_iwf_daily",
        "yahoo_ijr_daily", "yahoo_mtum_daily", "yahoo_qual_daily",
    )
    manifest = {
        "schema": PUBLIC_SOURCE_MANIFEST_SCHEMA,
        "sources": [{"id": source_id, "adapter": "fixture", "enabled": True} for source_id in factor_ids]
        + [{
            "id": "first_trust_dmv_fundamentals", "adapter": "first_trust_fundamentals",
            "entity_id": "DMV", "enabled": True,
        }],
    }
    source_run = _sealed({"schema": SOURCE_RUN_SCHEMA, "as_of": "2026-08-12T00:00:00Z"}, "run_sha256")

    plan = compile_broad_fund_acquisition_plan(
        scout=scout, catalog=catalog, policy=policy, source_manifest=manifest,
        source_run=source_run, existing_jobs=[{
            "security_id": "public_fund:DMV", "status": "queued",
        }], compiled_at="2026-08-12T01:00:00Z",
    )

    assert plan["status"] == "ready_to_enqueue"
    assert plan["selected_group_count"] == 2 and plan["new_job_count"] == 3
    assert plan["minimum_acquisition_count"] == 3
    assert {row["peer_group"]["region"] for row in plan["selected_groups"]} == {
        "developed_ex_us", "us",
    }
    first_group_ids = {
        row["security_id"] for row in plan["selected_groups"][0]["members"]
    }
    first_group_job_ids = [
        row["security_id"] for row in plan["selected_groups"][0]["members"]
        if row["security_id"] in first_group_ids and row["new_job_required"]
    ]
    assert [row["security_id"] for row in plan["jobs"][:len(first_group_job_ids)]] == first_group_job_ids
    assert "public_fund:DMV" not in {row["security_id"] for row in plan["jobs"]}
    assert not plan["shared_source_batches"]["factor_benchmarks"]["missing_source_ids"]
    assert plan["catalog_sha256"] == catalog["catalog_sha256"]
    assert plan["scout_sha256"] == scout["scout_sha256"]
    assert plan["source_run_sha256"] == source_run["run_sha256"]
    assert plan["expected_return_used"] is plan["security_rank_override"] is False
    assert plan["capital_authority"] is False
    assert {row["implementation_sleeve_id"] for row in plan["jobs"]} == {
        "international_equity", "us_equity",
    }
    assert all(
        row["implementation_sleeve_source_refs"] == [
            f"catalog:{catalog['catalog_sha256']}:security:{row['security_id']}"
        ]
        for row in plan["jobs"]
    )
    assert all(row["comparison_cell"]["asset_class"] == "equity" for row in plan["jobs"])
    assert all(
        row["peer_group_id"] == _cell_id(row["comparison_cell"])
        for row in plan["jobs"]
    )

    ready_candidates = []
    for entity_id in {row["entity_id"] for group in plan["selected_groups"] for row in group["members"]}:
        analysis = _sealed({
            "schema": "jaggedthoughts-factor-analysis-v1",
            "candidate_entity_id": entity_id,
        }, "analysis_sha256")
        ready_candidates.append({
            "entity_id": entity_id, "screen_status": "qualified", "analysis": analysis,
            "valuation": {"kind": "aggregate"},
            "fund_evidence": {
                "source_refs": [f"issuer:{entity_id}"],
                "metrics": {
                    "portfolio_top10_concentration": 0.3,
                    "fund_net_assets": 1_000_000,
                },
            },
        })
    watchlist = _sealed({
        "schema": "jaggedthoughts-opportunity-watchlist-result-v1",
        "watchlist_id": "rotation", "as_of": "2026-08-12T00:00:00Z",
        "candidates": ready_candidates,
    }, "watchlist_sha256")
    rotated = compile_broad_fund_acquisition_plan(
        scout=scout, catalog=catalog, policy=policy, source_manifest=manifest,
        source_run=source_run, watchlist_results=[watchlist],
        compiled_at="2026-08-12T02:00:00Z",
    )
    assert rotated["coverage"]["completed_peer_group_count"] == 2
    assert rotated["coverage"]["residual_peer_group_count"] == 1
    assert [row["peer_group"]["region"] for row in rotated["selected_groups"]] == ["emerging_markets"]
    assert rotated["selection_epoch"]["watchlist_sha256s"] == [watchlist["watchlist_sha256"]]
    monitor_watchlist = _sealed({
        **{key: value for key, value in watchlist.items() if key != "watchlist_sha256"},
        "candidates": [
            {**candidate, "screen_status": "monitor"}
            for candidate in watchlist["candidates"]
        ],
    }, "watchlist_sha256")
    monitored = compile_broad_fund_acquisition_plan(
        scout=scout, catalog=catalog, policy=policy, source_manifest=manifest,
        source_run=source_run, watchlist_results=[monitor_watchlist],
        compiled_at="2026-08-12T02:00:00Z",
    )
    assert monitored["coverage"]["completed_peer_group_count"] == 2
    assert all(
        "screen_qualification" not in member["requested_coordinates"]
        for group in monitored["completed_peer_groups"] for member in group["members"]
    )
    future = _sealed({
        **{key: value for key, value in watchlist.items() if key != "watchlist_sha256"},
        "as_of": "2026-08-13T00:00:00Z",
    }, "watchlist_sha256")
    future_blocked = compile_broad_fund_acquisition_plan(
        scout=scout, catalog=catalog, policy=policy, source_manifest=manifest,
        source_run=source_run, watchlist_results=[future],
        compiled_at="2026-08-12T02:00:00Z",
    )
    assert future_blocked["coverage"]["completed_peer_group_count"] == 0
    assert future_blocked["selection_epoch"]["ignored_future_watchlist_count"] == 1
    active = compile_broad_fund_acquisition_plan(
        scout=scout, catalog=catalog, policy=policy, source_manifest=manifest,
        source_run=source_run,
        existing_jobs=[{
            "security_id": row["security_id"], "status": "running",
        } for group in future_blocked["selected_groups"] for row in group["members"]],
        compiled_at="2026-08-12T02:00:00Z",
    )
    assert active["status"] == "acquisition_in_progress"
    assert active["next_activation"] == "await_active_peer_group_acquisition"


def test_plan_exposes_five_same_sleeve_cohorts_without_calling_assumptions_alpha():
    policy = broad_fund_scout_policy(max_results=10)
    names = {
        "USA": "Vanguard U.S. Total Stock Market ETF", "USB": "iShares U.S. Total Stock Market ETF",
        "INTA": "Vanguard International Equity ETF", "INTB": "iShares International Equity ETF",
        "BNDA": "Vanguard U.S. Total Bond Market ETF", "BNDB": "iShares U.S. Aggregate Bond ETF",
        "TIPA": "Vanguard U.S. Inflation-Protected Bond ETF", "TIPB": "iShares U.S. TIPS Bond ETF",
        "CASHA": "Vanguard U.S. Treasury Bill ETF", "CASHB": "iShares U.S. 0-3 Month Treasury Bond ETF",
    }
    securities = [{
        "security_id": f"public_fund:{symbol}", "symbol": symbol, "name": name,
        "entity_kind": "public_fund", "security_kind": "exchange_traded_fund",
        "last_price": 10.0,
    } for symbol, name in names.items()]
    catalog = _sealed({"schema": CATALOG_SCHEMA, "securities": securities}, "catalog_sha256")
    scout = _sealed({
        "schema": "jaggedthoughts-broad-fund-scout-v1",
        "catalog_sha256": catalog["catalog_sha256"], "policy_sha256": policy["policy_sha256"],
        "selected": [],
    }, "scout_sha256")
    basis_body = {
        "schema": "jaggedthoughts-capital-market-basis-v1", "basis_id": "public-usd-broad-sleeves",
        "as_of": "2026-08-12T00:00:00Z", "asset_classes": [
            {"asset_id": sleeve_id} for sleeve_id in (
                "cash", "us_equity", "international_equity", "usd_bonds", "us_tips",
            )
        ],
        "return_scenarios": [{
            "scenario_id": "current_source_anchor",
            "expected_returns": {
                "cash": .04, "us_equity": .09, "international_equity": .085,
                "usd_bonds": .047, "us_tips": .046,
            },
            "source_refs": ["public-basis"], "expected_return_claim": False,
        }],
        "capital_authority": False,
    }
    basis = {**basis_body, "basis_sha256": stable_sha256(basis_body)}
    plan = compile_broad_fund_acquisition_plan(
        scout=scout, catalog=catalog, policy=policy,
        source_manifest={"schema": PUBLIC_SOURCE_MANIFEST_SCHEMA, "sources": []},
        source_run=_sealed({
            "schema": SOURCE_RUN_SCHEMA, "as_of": "2026-08-12T01:00:00Z",
        }, "run_sha256"),
        capital_market_basis=basis, compiled_at="2026-08-12T02:00:00Z",
    )

    cohorts = {row["sleeve_id"]: row for row in plan["same_sleeve_research_cohorts"]}
    assert set(cohorts) == {"cash", "us_equity", "international_equity", "usd_bonds", "us_tips"}
    assert all(row["catalog_candidate_count"] == 2 for row in cohorts.values())
    assert cohorts["us_equity"]["assumption_spread_to_cash"] == .05
    assert cohorts["usd_bonds"]["assumption_spread_to_cash"] == .007
    assert all(not row["alpha_claim"] for row in cohorts.values())
    assert {row["implementation_sleeve_id"] for row in plan["selected_groups"]} == {
        "us_equity", "international_equity",
    }
