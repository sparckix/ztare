from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from ztare.common.equivariance import stable_sha256
from ztare.investment.household_allocation import (
    CAPITAL_MARKET_BASIS_SCHEMA,
    HOUSEHOLD_ALLOCATION_SCHEMA,
)
from ztare.investment.public_capital_market_basis import PUBLIC_SLEEVE_IDS
from ztare.investment.factor_analysis import PricePoint
from ztare.investment.fund_sleeve_comparison import (
    compile_fund_sleeve_comparison,
    compile_fund_lookthrough_acquisition_plan,
)
from ztare.investment import fund_lookthrough_optimizer
from ztare.investment.fund_implementation_review import (
    activate_fund_implementation_review,
    compile_fund_implementation_research_evidence,
    compile_fund_implementation_research_request,
    compile_fund_implementation_review_audit,
    compile_fund_implementation_review_proposal,
    compile_workspace_fund_implementation_review,
)
from ztare.investment.instrument_portfolio_admission import (
    compile_instrument_portfolio_admission,
)
from ztare.investment.sleeve_implementation import (
    SLEEVE_IMPLEMENTATION_FRONTIER_SCHEMA,
    compile_sleeve_implementation_frontier,
)
from ztare.investment.watchlist import (
    FUND_HOLDINGS_GRAPH_SCHEMA,
    WATCHLIST_RESULT_SCHEMA,
    _fund_choice_frontier,
)


def _sealed(body: dict[str, Any], field: str) -> dict[str, Any]:
    return {**body, field: stable_sha256(body)}


def _contains_key(value: Any, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(row, key) for row in value.values())
    if isinstance(value, list):
        return any(_contains_key(row, key) for row in value)
    return False


def test_minimum_call_cover_reuses_last_success(monkeypatch) -> None:
    calls = []

    def run(*args, **kwargs):
        calls.append(kwargs["input"])
        return type("Result", (), {
            "returncode": 0, "stdout": '{"optimal": true, "selected_entity_ids": ["CACHE"]}',
            "stderr": "",
        })()

    monkeypatch.setattr(fund_lookthrough_optimizer, "_LAST_SUCCESS", None)
    monkeypatch.setattr(fund_lookthrough_optimizer.subprocess, "run", run)
    payload = {"cache_probe": "unchanged-plan-input"}
    assert fund_lookthrough_optimizer.run_minimum_call_cover(payload)["optimal"]
    assert fund_lookthrough_optimizer.run_minimum_call_cover(payload)["optimal"]
    assert len(calls) == 1


def test_sleeve_bridge_preserves_identity_frontier_and_mandate_boundary(
    tmp_path: Path,
) -> None:
    basis = _sealed({
        "schema": CAPITAL_MARKET_BASIS_SCHEMA,
        "basis_id": "public-usd-broad-sleeves",
        "as_of": "2026-08-12T00:00:00+00:00",
        "asset_classes": [
            {"asset_id": sleeve_id, "currency": "USD"}
            for sleeve_id in PUBLIC_SLEEVE_IDS
        ],
        "return_scenarios": [{
            "scenario_id": "current_source_anchor",
            "expected_returns": {"cash": 0.03},
            "source_refs": ["public-cash-source"],
            "expected_return_claim": False,
        }],
        "capital_authority": False,
    }, "basis_sha256")
    def candidate(
        entity_id: str, sleeve_id: str, *, expected: float, margin: float,
        growth: float, fee: float, drawdown: float,
    ) -> dict[str, Any]:
        metrics = {
            "median_bid_ask_spread": 0.0002,
            "average_daily_volume_30d": 2_000_000.0,
            "fund_net_assets": 5_000_000_000.0,
        } if entity_id == "AAA" else {}
        return {
            "entity_id": entity_id, "name": f"{entity_id} ETF",
            "category": "US broad" if sleeve_id == "us_equity" else "developed ex-US",
            "vehicle_kind": "exchange_traded_fund",
            "implementation_sleeve_id": sleeve_id,
            "implementation_sleeve_source_refs": [f"issuer:{entity_id}:{sleeve_id}"],
            "analysis": {
                "assumption_implied": {"return_without_residual_alpha": expected},
                "historical": {"maximum_drawdown": drawdown},
                "coefficients": {"betas": {"market": 1.0}}, "source_refs": [],
            },
                "valuation": {
                    "valuation_kind": "aggregate_expectations_proxy",
                    "earnings_yield": 0.06, "book_to_price": 0.40,
                    "earnings_power_margin": margin, "implied_growth_median": growth,
                    "expense_ratio": fee, "net_earnings_yield": 0.06 - fee,
                    "required_return": expected,
                    "source_refs": [f"issuer:{entity_id}:aggregate-valuation"],
                },
            "fund_evidence": {
                "metrics": metrics,
                "holdings_snapshot_path": (
                    "data/fund_holdings/aaa.json" if entity_id == "AAA" else None
                ),
            },
        }

    frontier = _fund_choice_frontier(
        watchlist_id="funds", as_of=basis["as_of"], candidates=[
            candidate("AAA", "us_equity", expected=0.10, margin=0.20,
                      growth=0.01, fee=0.001, drawdown=-0.20),
            candidate("BBB", "us_equity", expected=0.05, margin=0.10,
                      growth=0.02, fee=0.003, drawdown=-0.30),
            candidate("CCC", "international_equity", expected=0.04, margin=0.05,
                      growth=0.03, fee=0.004, drawdown=-0.40),
        ],
    )
    assert frontier["frontier_entity_ids"] == ["AAA", "CCC"]
    ccc = next(row for row in frontier["alternatives"] if row["entity_id"] == "CCC")
    assert ccc["nearest_substitutes"] == []
    graph = _sealed({
        "schema": FUND_HOLDINGS_GRAPH_SCHEMA, "as_of": basis["as_of"],
        "target_entity_id": "AAA", "scope_closed": True,
        "snapshots": [{
            "entity_id": "AAA", "position_count": 500, "disclosed_weight": 0.99,
            "snapshot_sha256": "a" * 64,
        }],
        "pairwise_overlap": [{
            "left_entity_id": "AAA", "right_entity_id": "BBB",
            "shared_holding_count": 100, "holding_jaccard_similarity": 0.4,
            "weighted_overlap": 0.3, "disclosed_active_share": 0.7,
            "shared_identifiers": ["MUST_NOT_COPY"],
        }],
        "target_coverage": {"company_quality_weight": 0.75},
    }, "fund_holdings_graph_sha256")
    watchlist = _sealed({
        "schema": WATCHLIST_RESULT_SCHEMA, "watchlist_id": "funds",
        "as_of": basis["as_of"],
        "implementation_sleeve_ids": ["international_equity", "us_equity"],
        "fund_choice_frontier": frontier, "fund_holdings_graph": graph,
    }, "watchlist_sha256")
    fund_proposal = _sealed({
        "schema": "jaggedthoughts-public-fund-paper-proposal-v1",
        "entity": {"entity_id": "AAA", "entity_kind": "public_fund"},
        "activation_blockers": [], "capital_authority": False,
        "brokerage_authority": False,
    }, "proposal_sha256")
    fund_decision = _sealed({
        "schema": "jaggedthoughts-public-fund-paper-decision-v1",
        "decision_id": "fund-paper-decision:AAA",
        "proposal_sha256": fund_proposal["proposal_sha256"],
        "entity": {"entity_id": "AAA", "entity_kind": "public_fund"},
        "lifecycle": {"data_class": "operator", "stage": "active"},
        "paper_policy": {"target_weight": 0.0, "allocation_allowed": False},
        "capital_authority": False, "brokerage_authority": False,
    }, "decision_sha256")
    fund_decision["transition"] = {"to_state": "active_paper"}
    fund_audit = {
        "rows": [{
            "entity_id": "AAA", "status": "eligible_proposal",
            "activation_eligible": True, "blockers": [], "proposal": fund_proposal,
        }],
    }
    incomplete = _sealed({
        "schema": HOUSEHOLD_ALLOCATION_SCHEMA, "as_of": basis["as_of"],
        "mandate_sha256": "b" * 64, "basis_sha256": basis["basis_sha256"],
        "status": "mandate_incomplete",
        "blockers": ["tax_residence", "after_tax_return_policy"],
        "frontier": [], "selected_policy": None, "capital_authority": False,
        "brokerage_authority": False,
    }, "allocation_sha256")
    equity_audit = {
        "rows": [{
            "entity_id": "XYZ", "status": "eligible_proposal",
            "activation_eligible": True, "blockers": [], "proposal": None,
        }],
    }

    result = compile_sleeve_implementation_frontier(
        capital_market_basis=basis, household_allocation=incomplete,
        fund_watchlists=[watchlist], fund_proposal_audit=[fund_audit],
        equity_proposal_audit=equity_audit, paper_decisions=[fund_decision],
    )

    historical_watchlist = _sealed({
        **{key: value for key, value in watchlist.items() if key != "watchlist_sha256"},
        "watchlist_id": "historical-funds",
    }, "watchlist_sha256")
    scoped = compile_sleeve_implementation_frontier(
        capital_market_basis=basis, household_allocation=incomplete,
        fund_watchlists=[watchlist, historical_watchlist],
        fund_watchlist_entity_scopes={
            watchlist["watchlist_sha256"]: {"BBB", "CCC"},
            historical_watchlist["watchlist_sha256"]: {"AAA"},
        },
    )
    assert sorted(
        row["identity"]["subject_id"]
        for sleeve in scoped["sleeves"]
        for row in sleeve["eligible_instruments"]
        if not row.get("basis_proxy")
    ) == ["AAA", "BBB", "CCC"]

    assert result["schema"] == SLEEVE_IMPLEMENTATION_FRONTIER_SCHEMA
    assert result["policy_consumed"] is False
    assert result["mandate_blockers"] == ["tax_residence", "after_tax_return_policy"]
    assert not _contains_key(result, "weights")
    us_equity = next(row for row in result["sleeves"] if row["sleeve_id"] == "us_equity")
    aaa = next(
        row for row in us_equity["eligible_instruments"]
        if row["identity"]["subject_id"] == "AAA"
    )
    assert aaa["identity"] == {
        "subject_id": "AAA", "subject_kind": "public_security",
        "entity_kind": "public_fund", "security_kind": "exchange_traded_fund",
        "implementation_epoch": basis["as_of"],
    }
    assert aaa["proposal_gate"]["eligible"] is True
    assert aaa["factor_fit"]["residual_alpha_uncertainty"][
        "factor_frontier_alpha_credit"
    ] == 0.0
    assert aaa["policy_implementation_eligible"] is False
    assert aaa["implementation_candidate"]["status"] == "admitted_to_implementation_review"
    assert aaa["implementation_candidate"]["portfolio_candidate"] is False
    assert aaa["implementation_candidate"]["lineage"] == {
        "proposal_sha256": fund_proposal["proposal_sha256"],
        "fund_choice_frontier_sha256": frontier["fund_choice_frontier_sha256"],
        "fund_holdings_graph_sha256": graph["fund_holdings_graph_sha256"],
        "alternative_sha256": stable_sha256(next(
            row for row in frontier["alternatives"] if row["entity_id"] == "AAA"
        )),
    }
    assert result["implementation_review_admitted_count"] == 1
    assert aaa["overlap"][0]["counterpart_entity_id"] == "BBB"
    assert "shared_identifiers" not in aaa["overlap"][0]
    assert [row["subject_id"] for row in us_equity["nondominated_substitutes"]] == ["AAA"]
    assert not any(
        row["identity"]["subject_id"] == "CCC"
        for row in us_equity["eligible_instruments"]
    )
    international = next(
        row for row in result["sleeves"]
        if row["sleeve_id"] == "international_equity"
    )
    assert any(
        row["identity"]["subject_id"] == "CCC"
        for row in international["eligible_instruments"]
    )
    assert any(
        row["identity"]["entity_kind"] == "public_equity"
        and row["evidence_gap"] == "broad_sleeve_fit_unbound"
        for row in result["unassigned_evidence"]
    )
    assert next(
        row for row in result["subject_kind_registry"]
        if row["entity_kind"] == "private_fund_interest"
    )["supported"] is False
    assert result["expected_return_invented"] is False
    assert result["capital_authority"] is result["brokerage_authority"] is False

    open_graph = _sealed({
        **{key: value for key, value in graph.items() if key != "fund_holdings_graph_sha256"},
        "scope_closed": False,
    }, "fund_holdings_graph_sha256")
    open_watchlist = _sealed({
        **{key: value for key, value in watchlist.items() if key != "watchlist_sha256"},
        "fund_holdings_graph": open_graph,
    }, "watchlist_sha256")
    qualified_open_peer_scope = compile_sleeve_implementation_frontier(
        capital_market_basis=basis, household_allocation=incomplete,
        fund_watchlists=[open_watchlist], fund_proposal_audit=[fund_audit],
        paper_decisions=[fund_decision],
    )
    qualified_aaa = next(
        row for sleeve in qualified_open_peer_scope["sleeves"]
        for row in sleeve["eligible_instruments"]
        if row["identity"]["subject_id"] == "AAA"
    )
    assert qualified_aaa["implementation_candidate"]["implementation_review_admitted"] is True
    assert "peer_holdings_scope_open" not in qualified_aaa["evidence_gaps"]

    complete_body = {
        **{key: value for key, value in incomplete.items() if key != "allocation_sha256"},
        "status": "paper_policy_ready", "blockers": [],
        "selected_policy": {
            "weights": {
                sleeve_id: 1.0 if sleeve_id == "us_equity" else 0.0
                for sleeve_id in PUBLIC_SLEEVE_IDS
            },
        },
    }
    complete = _sealed(complete_body, "allocation_sha256")
    unwatched = compile_sleeve_implementation_frontier(
        capital_market_basis=basis, household_allocation=complete,
        fund_watchlists=[watchlist], fund_proposal_audit=[fund_audit],
    )
    assert next(
        row for sleeve in unwatched["sleeves"] if sleeve["sleeve_id"] == "us_equity"
        for row in sleeve["eligible_instruments"]
        if row["identity"]["subject_id"] == "AAA"
    )["policy_implementation_eligible"] is False
    consumed = compile_sleeve_implementation_frontier(
        capital_market_basis=basis, household_allocation=complete,
        fund_watchlists=[watchlist], fund_proposal_audit=[fund_audit],
        paper_decisions=[fund_decision],
    )
    assert consumed["policy_consumed"] is True
    assert not _contains_key(consumed, "weights")
    consumed_us = next(row for row in consumed["sleeves"] if row["sleeve_id"] == "us_equity")
    assert consumed_us["policy_status"] == "selected"
    assert next(
        row for row in consumed_us["eligible_instruments"]
        if row["identity"]["subject_id"] == "AAA"
    )["policy_implementation_eligible"] is True

    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    points = [
        PricePoint(
            entity_id=entity, observed_at=(start + timedelta(days=index)).isoformat(),
            available_at=(start + timedelta(days=index)).isoformat(),
            value=100 * (1 + drift) ** index,
            observation_id=f"{entity}:{index}", source_ref=f"prices:{entity}",
        )
        for entity, drift in (("AAA", 0.001), ("BBB", 0.0005), ("CCC", 0.0002))
        for index in range(130)
    ]
    comparison = compile_fund_sleeve_comparison(
        sleeve_implementation=result, price_points=points,
        capital_market_basis=basis,
        holdings_quality={
            "AAA": {
                "status": "sufficient_for_cross_fund_comparison",
                "durable_earnings_power": 0.8,
            },
        },
    )
    assert comparison["comparison_eligible_count"] == 1
    aaa_program = next(
        row for sleeve in comparison["sleeves"] for row in sleeve["programs"]
        if row["identity"]["subject_id"] == "AAA"
    )
    assert aaa_program["factor_uncertainty"]["precision_status"] == (
        "prospective_record_required"
    )
    cash_comparison = aaa_program["cash_comparison"]
    assert cash_comparison["status"] == "positive_factor_assumption_spread"
    assert abs(cash_comparison["expected_excess_return"] - 0.069) < 1e-12
    assert cash_comparison["cash_hurdle_sha256"] == comparison["cash_hurdle"][
        "cash_hurdle_sha256"
    ]
    assert cash_comparison["residual_alpha_credit"] == 0.0
    assert comparison["risk_basis"]["return_count"] == 129
    tournament = comparison["portfolio_policy_tournament_input"]
    assert (
        tournament["program_count"],
        tournament["same_information_core_candidate_count"],
        tournament["lookthrough_quality_candidate_count"],
        tournament["portfolio_policy_candidate_count"],
    ) == (3, 1, 1, 0)
    assert tournament["prospective_ranking_ticket_count"] == 0
    assert tournament["cash_hurdle_candidate_program_ids"] == [aaa_program["program_id"]]
    assert comparison["invest_vs_cash_activation"]["candidate_program_ids"] == [
        aaa_program["program_id"]
    ]
    assert comparison["invest_vs_cash_activation"]["ranked_research_candidates"] == [{
        "research_priority_rank_within_sleeve": 1,
        "sleeve_id": "us_equity",
        "entity_id": "AAA",
        "program_id": aaa_program["program_id"],
        "expected_excess_return_vs_cash": cash_comparison["expected_excess_return"],
        "ranking_semantics": "factor_assumption_spread_research_priority",
    }]
    assert comparison["invest_vs_cash_activation"]["required_next_transition"] == (
        "compile_comparison_bound_fund_implementation_research_request"
    )

    monitor_candidate = _sealed({
        "schema": "jaggedthoughts-discovery-candidate-v1",
        "candidate_id": "fund:test:AAA",
        "entity_id": "AAA", "entity_kind": "public_fund", "screen_status": "monitor",
        "as_of": basis["as_of"],
    }, "candidate_sha256")
    request = compile_fund_implementation_research_request(
        candidate=monitor_candidate, candidate_leaf="c" * 64,
        comparison_program=aaa_program, created_at=basis["as_of"],
    )
    with pytest.raises(ValueError, match="every declared scope coordinate"):
        compile_fund_implementation_research_evidence(
            request=request, completed_at=basis["as_of"],
            findings={"fees": {"status": "observed"}},
        )
    with pytest.raises(ValueError, match="typed fields"):
        compile_fund_implementation_research_evidence(
            request=request, completed_at=basis["as_of"],
            findings={
                coordinate: {
                    "status": "observed", "values": {"note": "looks fine"},
                    "source_refs": ["test-source"],
                }
                for coordinate in ("fees", "holdings", "liquidity", "mechanics", "tax_fit")
            },
        )
    evidence = compile_fund_implementation_research_evidence(
        request=request, completed_at=basis["as_of"],
        findings={
            "fees": {"status": "observed", "values": {"expense_ratio": 0.001},
                     "source_refs": ["test-source:fees"]},
            "holdings": {"status": "observed", "values": {"portfolio_holdings_count": 500},
                         "source_refs": ["test-source:holdings"]},
            "liquidity": {"status": "observed", "values": {
                "median_bid_ask_spread": 0.0002, "average_daily_volume_30d": 2_000_000,
                "fund_net_assets": 5_000_000_000,
            }, "source_refs": ["test-source:liquidity"]},
            "mechanics": {"status": "observed", "values": {"portfolio_turnover": 0.1},
                          "source_refs": ["test-source:mechanics"]},
            "tax_fit": {"status": "observed", "values": {
                "distribution_tax_character": "mixed", "foreign_withholding_tax_rate": 0.0,
                "trading_currency": "USD", "underlying_currency_exposure": "USD",
            }, "source_refs": ["test-source:tax"]},
        },
    )
    proposal = compile_fund_implementation_review_proposal(
        evidence=evidence, compiled_at=basis["as_of"],
    )
    review_audit = compile_fund_implementation_review_audit(
        [proposal], compiled_at=basis["as_of"],
    )
    review_decision = activate_fund_implementation_review(
        proposal, confirmation=proposal["required_operator_confirmation"],
        operator_id="test-operator", activated_at=basis["as_of"],
    )
    reviewed = compile_sleeve_implementation_frontier(
        capital_market_basis=basis, household_allocation=incomplete,
        fund_watchlists=[watchlist], fund_implementation_review_audit=review_audit,
        implementation_review_decisions=[review_decision],
    )
    reviewed_aaa = next(
        row for sleeve in reviewed["sleeves"] for row in sleeve["eligible_instruments"]
        if row["identity"]["subject_id"] == "AAA"
    )
    review_candidate = reviewed_aaa["implementation_candidate"]
    assert review_candidate["implementation_review_admitted"] is True
    assert review_candidate["implementation_review_activated"] is True
    assert review_candidate["paper_watch_activated"] is False
    assert review_candidate["lineage"]["comparison_program_sha256"] == aaa_program[
        "program_sha256"
    ]
    assert review_candidate["paper_decision_sha256"] is None
    assert review_candidate["implementation_review_decision_sha256"] == review_decision[
        "decision_sha256"
    ]
    assert review_candidate["portfolio_candidate"] is False
    assert review_candidate["allocation_allowed"] is False
    assert review_candidate["order_routing_allowed"] is False
    assert review_decision["capital_authority"] is False
    with pytest.raises(
        ValueError, match="implementation-review decisions cannot enter portfolio admission",
    ):
        compile_instrument_portfolio_admission(
            paper_watch_decision=review_decision, sleeve_implementation={},
            factor_analysis={}, return_covariance={}, compiled_at=basis["as_of"],
        )

    (tmp_path / "discovery").mkdir()
    (tmp_path / "portfolio" / "fund_sleeve_comparison").mkdir(parents=True)
    (tmp_path / "discovery" / "latest.json").write_text(
        json.dumps({"run_sha256": "d" * 64, "candidates": [monitor_candidate]}),
        encoding="utf-8",
    )
    (tmp_path / "discovery" / "latest_record.json").write_text(
        json.dumps({
            "run_sha256": "d" * 64,
            "candidate_leaves": {"fund:test:AAA": "c" * 64},
        }),
        encoding="utf-8",
    )
    (tmp_path / "portfolio" / "fund_sleeve_comparison" / "latest.json").write_text(
        json.dumps(comparison), encoding="utf-8",
    )
    pending_review = compile_workspace_fund_implementation_review(
        tmp_path, comparison=comparison,
    )
    assert pending_review["status"] == "implementation_evidence_source_gaps"
    assert pending_review["request_count"] == 1
    assert pending_review["evidence_count"] == pending_review["proposal_count"] == 1
    assert pending_review["eligible_proposal_count"] == pending_review["decision_count"] == 0
    assert pending_review["next_missing_coordinates"] == [
        "holdings", "mechanics", "tax_fit",
    ]
    persisted_request = json.loads(
        (tmp_path / pending_review["requests"][0]["artifact_path"]).read_text(
            encoding="utf-8"
        )
    )
    evidence_dir = tmp_path / "research_jobs" / "fund_implementation" / "evidence"
    persisted_evidence = json.loads(next(evidence_dir.glob("*.json")).read_text(encoding="utf-8"))
    assert persisted_evidence["coverage_status"] == "partial_source_gap"
    assert persisted_evidence["blockers"] == [
        "source_gap:holdings", "source_gap:mechanics", "source_gap:tax_fit",
    ]
    assert pending_review["automatic_activation"] is False
    assert (tmp_path / pending_review["audit_path"]).is_file()
    admitted_comparison = json.loads(json.dumps(comparison))
    admitted_comparison.pop("fund_sleeve_comparison_sha256")
    admitted_program = next(
        row for sleeve in admitted_comparison["sleeves"] for row in sleeve["programs"]
        if row["identity"]["subject_id"] == "AAA"
    )
    admitted_program.pop("program_sha256")
    admitted_program["implementation_review_admitted"] = True
    admitted_program["program_sha256"] = stable_sha256(admitted_program)
    admitted_comparison["fund_sleeve_comparison_sha256"] = stable_sha256(admitted_comparison)
    replayed_review = compile_workspace_fund_implementation_review(
        tmp_path, comparison=admitted_comparison,
        compiled_at=persisted_request["created_at"],
    )
    assert replayed_review["requests"][0]["request_sha256"] == persisted_request[
        "request_sha256"
    ]
    assert replayed_review["proposal_count"] == 1
    assert replayed_review["status"] == "implementation_evidence_source_gaps"
    assert not _contains_key(tournament, "weights")
    assert comparison["allocation_selected"] is False
    assert comparison["portfolio_handoff"]["compatible_compiler"].endswith(
        "compile_portfolio_assembly"
    )
    acquisition = comparison["portfolio_handoff"]["evidence_acquisition"]
    assert acquisition["kernel_ready"]["unsupported_residual_alpha_credit"] is False
    assert acquisition["next_public_activation"]["owner"].endswith(
        "run_workspace_fund_lookthrough_acquisition"
    )
    assert next(
        row for row in acquisition["public_evidence_requirements"]
        if row["requirement_id"] == "equity_sleeve_identity:broad_sleeve_fit_unbound"
    )["subject_ids"] == ["XYZ"]
    assert "tax_currency:trading_currency_absent" in acquisition[
        "adapter_gap_requirement_ids"
    ]


def test_equity_paper_watch_uses_source_bound_country_only_as_sleeve_proxy() -> None:
    basis = _sealed({
        "schema": CAPITAL_MARKET_BASIS_SCHEMA, "as_of": "2026-08-12T00:00:00Z",
        "asset_classes": [{"asset_id": row} for row in PUBLIC_SLEEVE_IDS],
        "capital_authority": False,
    }, "basis_sha256")
    proposal = _sealed({
        "schema": "jaggedthoughts-public-equity-paper-proposal-v1",
        "entity": {"entity_id": "XYZ", "entity_kind": "public_equity"},
        "candidate_identity": {"as_of": "2026-08-12T00:00:00Z"},
        "evidence": {"dossier_sha256": "d" * 64},
        "activation_blockers": [], "capital_authority": False,
        "brokerage_authority": False,
    }, "proposal_sha256")
    decision = _sealed({
        "schema": "jaggedthoughts-public-equity-paper-decision-v1",
        "decision_id": "equity-paper-decision:XYZ",
        "proposal_sha256": proposal["proposal_sha256"],
        "entity": {"entity_id": "XYZ", "entity_kind": "public_equity"},
        "lifecycle": {"data_class": "operator", "stage": "active"},
        "paper_policy": {"target_weight": 0.0, "allocation_allowed": False},
        "capital_authority": False, "brokerage_authority": False,
    }, "decision_sha256")
    receipt = {
        "source_id": "nasdaq_us_listed_equities", "raw_path": "universe/raw/x.json",
        "content_sha256": "c" * 64, "retrieved_at": "2026-08-13T00:00:00Z",
    }
    catalog = _sealed({
        "schema": "jaggedthoughts-public-market-catalog-v1",
        "retrieved_at": "2026-08-13T00:00:00Z", "source_receipts": [receipt],
        "securities": [{
            "security_id": "public_equity:XYZ", "symbol": "XYZ", "name": "XYZ Co",
            "entity_kind": "public_equity",
            "security_kind": "common_equity", "country": "United States",
            "sector": "Industrials", "volume": 1000,
            "available_at": "2026-08-13T00:00:00Z",
            "availability_mode": "retrieval_only",
            "source_id": receipt["source_id"], "source_path": receipt["raw_path"],
        }],
    }, "catalog_sha256")
    result = compile_sleeve_implementation_frontier(
        capital_market_basis=basis,
        equity_proposal_audit={"rows": [{
            "entity_id": "XYZ", "status": "eligible_proposal",
            "activation_eligible": True, "blockers": [], "proposal": proposal,
        }]},
        paper_decisions=[decision], security_catalog=catalog,
    )
    us_equity = next(row for row in result["sleeves"] if row["sleeve_id"] == "us_equity")
    xyz = next(row for row in us_equity["eligible_instruments"]
               if row["identity"]["subject_id"] == "XYZ")
    assert xyz["sleeve_fit"]["method"] == "catalog_country_proxy"
    assert xyz["sleeve_fit"]["catalog_sha256"] == catalog["catalog_sha256"]
    assert xyz["identity"]["implementation_epoch"] == "2026-08-13T00:00:00Z"
    assert "does not establish revenue" in xyz["sleeve_fit"]["use_boundary"]
    assert xyz["implementation_candidate"]["status"] == "admitted_to_implementation_review"
    assert xyz["implementation_candidate"]["portfolio_candidate"] is False
    assert xyz["factor_fit"]["expected_return_claim"] is False
    comparison = compile_fund_sleeve_comparison(
        sleeve_implementation=result, price_points=[],
    )
    assert not any(row["programs"] for row in comparison["sleeves"])


def test_cross_fund_lookthrough_plan_spends_one_shared_registry_call() -> None:
    tournament = _sealed({
        "schema": "jaggedthoughts-fund-program-tournament-input-v1",
        "as_of": "2026-08-13T00:00:00Z",
        "sleeves": [{
            "sleeve_id": "us_equity",
            "programs": [
                {"entity_id": "F1", "same_information_core_ready": True},
                {"entity_id": "F2", "same_information_core_ready": True},
            ],
        }],
    }, "tournament_input_sha256")

    def snapshot(entity_id: str, holdings: list[dict[str, Any]]) -> dict[str, Any]:
        return _sealed({
            "entity_id": entity_id,
            "disclosed_weight": sum(row["weight"] for row in holdings),
            "holdings": holdings,
        }, "snapshot_sha256")

    result = compile_fund_lookthrough_acquisition_plan(
        tournament_input=tournament,
        holdings_snapshots=[
            snapshot("F1", [
                {"identifier": "A@NYSE", "weight": 0.20},
                {"identifier": "B@NASDAQ", "weight": 0.30},
                {"identifier": "Q@NYSE", "weight": 0.10},
            ]),
            snapshot("F2", [
                {"identifier": "A@NASDAQ", "weight": 0.15},
                {"identifier": "R@NYSE", "weight": 0.25},
                {"identifier": "X@TOKYO STOCK EXCHANGE", "weight": 0.10},
            ]),
        ],
        quality_entity_ids=["Q"], enrolled_entity_ids=["R"],
        public_equity_ids=["A", "B"], max_source_calls=3,
    )

    assert result["selected_entity_ids"] == ["A", "B"]
    assert result["selection_policy"]["objective"] == (
        "minimum_call_same_sleeve_threshold_closure_then_cross_fund_coverage"
    )
    assert result["same_sleeve_threshold_closure_projection"]["status"] == (
        "unreachable_with_current_eligible_issuer_set"
    )
    assert result["source_budget"] == {
        "max_source_calls": 3, "sec_registry_batch_calls": 1,
        "sec_companyfacts_calls": 2, "estimated_source_calls": 3,
    }
    assert result["selected"][0]["fund_count"] == 2
    assert result["aggregate_before_company_quality_weight"] == 0.10
    assert round(result["aggregate_after_company_quality_weight_potential"], 8) == 0.75
    assert [row["entity_id"] for row in result["remaining_gaps"]["metric_repair"]] == ["R"]
    assert result["remaining_gaps"]["public_source_identity_unavailable_count"] == 1
    assert not _contains_key(result, "weights")


def test_cross_fund_lookthrough_moves_to_the_next_unclosed_sleeve() -> None:
    tournament = _sealed({
        "schema": "jaggedthoughts-fund-program-tournament-input-v1",
        "as_of": "2026-08-13T00:00:00Z",
        "sleeves": [{
            "sleeve_id": sleeve_id,
            "programs": [
                {"entity_id": fund_id, "same_information_core_ready": True}
                for fund_id in fund_ids
            ],
        } for sleeve_id, fund_ids in (
            ("closed", ("C1", "C2")), ("open", ("O1", "O2")),
        )],
    }, "tournament_input_sha256")

    def snapshot(entity_id: str, identifier: str) -> dict[str, Any]:
        return _sealed({
            "entity_id": entity_id, "disclosed_weight": 1.0,
            "holdings": [{"identifier": identifier, "weight": 0.6}],
        }, "snapshot_sha256")

    result = compile_fund_lookthrough_acquisition_plan(
        tournament_input=tournament,
        holdings_snapshots=[
            snapshot("C1", "DONE1"), snapshot("C2", "DONE2"),
            snapshot("O1", "NEXT1"), snapshot("O2", "NEXT2"),
        ],
        quality_entity_ids=["DONE1", "DONE2"], enrolled_entity_ids=[],
        public_equity_ids=["NEXT1", "NEXT2"], max_source_calls=3,
    )

    projection = result["same_sleeve_threshold_closure_projection"]
    assert result["selected_entity_ids"] == ["NEXT1", "NEXT2"]
    assert projection["observed_closed_sleeve_ids"] == ["closed"]
    assert projection["target_open_sleeve_ids"] == ["open"]
