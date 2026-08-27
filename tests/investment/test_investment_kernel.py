from __future__ import annotations

import json
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import sqlite3

import pytest
import yaml

from ztare.common.equivariance import stable_sha256
from ztare.common.linear_preference_regions import compile_linear_preference_regions
from ztare.investment.golden_store import record_strategy_move_library

from ztare.investment import (
    GoldenStore,
    FactorDefinition,
    SignalDefinition,
    OPPORTUNITY_FUNNEL,
    OutcomeSnapshot,
    PatientCapitalPolicy,
    PortfolioCandidate,
    ValuationAssumption,
    PortfolioConstraints,
    PortfolioExposureBand,
    PortfolioMechanismScenario,
    PortfolioObjective,
    compile_investment_profile_file,
    compile_company_strategy_frontier,
    explain_strategy_bundle_feasibility,
    select_company_contingent_recourse,
    compile_strategy_cohort_research_plan,
    compile_strategy_cohort_research_result,
    compile_strategy_law_candidates,
    compile_strategy_phenotype_projection_frontier,
    compile_strategy_move_library,
    compile_enrichment_cycle,
    compile_research_learning,
    compile_market_scout,
    default_law_catalog,
    conservative_density_step,
    compile_research_intent,
    compile_portfolio_assembly,
    compile_patient_rotation_review,
    compile_valuation_envelope,
    compile_world_model_tournament_profile,
    consume_public_sources,
    discovery_schedule_status,
    default_enrichment_policy,
    derive_signals_partial,
    due_strategy_outcome_requests,
    evaluate_difference_in_differences,
    validate_research_dossier,
    record_investment_decision,
    record_investment_settlement,
    record_portfolio_assembly,
    record_world_model_tournament,
    resolve_strategy_cohort_results,
    settle_paper_decision,
    standard_signal_definitions,
    strategy_cohort_query_identity,
    analyze_factor_exposure,
    assign_research_question_policies,
)
from ztare.investment.factor_analysis import PricePoint
from ztare.investment.contracts import MetricObservation
from ztare.investment.golden_store import GoldenLeaf, record_discovery_run
from ztare.investment.discovery import (
    _assign_research_ranks,
    _compile_fund,
    _compile_rank_program_input,
    _fund_score,
    _rank_candidate_lanes,
)
from ztare.investment.institutional_learning import _full_fiscal_treatment_period
from ztare.investment.learning_credit import compile_learning_credit_assignment
from ztare.investment.price_action import PriceActionCandidate, evaluate_price_action_candidate
from ztare.investment.portfolio_policy import _compile_policy_review
from ztare.investment.watchlist import (
    bound_fund_valuation_coordinates,
    fund_evidence_vote_receipt,
    fund_potential_family_score,
    verify_fund_evidence_vote_receipt,
)
from ztare.investment.research_monitor import (
    enqueue_changed_source_research,
    record_monitor_subscription,
)
from ztare.investment.strategy_measurement_contract import (
    STRATEGY_MEASUREMENT_RESULT_SCHEMA,
    _measurement_relation,
    build_strategy_measurement_successor_profile,
    compile_strategy_measurement_contract_request,
    compile_strategy_measurement_contract_result,
    due_strategy_measurement_contract_requests,
)
from ztare.investment.strategy_event_refinement import (
    STRATEGY_EVENT_REFINEMENT_RESULT_SCHEMA,
    compile_strategy_event_refinement_request,
    compile_strategy_event_refinement_result,
)
from ztare.investment.research_memory import (
    candidate_research_coverage,
    record_candidate_research_coverage,
    strategy_choice_system_phenotype,
)
from ztare.investment.research_jobs import (
    ResearchEvidenceTimestampError,
    ENRICHMENT_JOB_KIND,
    require_research_parent_ready,
    research_job_snapshot,
    research_rank_priority,
)
from ztare.investment.research_agent import (
    _strategy_calibration_successor_request,
    _strategy_frontier_profile_path,
    validate_strategy_frontier_proposal,
)
from ztare.investment.sources import _ishares_characteristics_payload, _vanguard_profile_payload
from ztare.investment.watchlist import _fund_valuation
from ztare.investment.workspace import (
    _compile_portfolio_exposure_bands,
    _rebase_current_enrichment_priorities,
    _recover_interrupted_enrichment_jobs,
    _resumable_enrichment_jobs,
)
from ztare.leanmill import work_queue


ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples" / "jaggedthoughts" / "investment"


def test_research_rank_skips_non_survivors_and_owns_queue_priority() -> None:
    candidates = [
        {"candidate_id": "equity:top", "entity_kind": "public_equity",
         "rank_score": 0.90, "screen_status": "qualified"},
        {"candidate_id": "equity:blocked", "entity_kind": "public_equity",
         "rank_score": 0.80, "screen_status": "blocked"},
        {"candidate_id": "fund:monitor", "entity_kind": "public_fund",
         "rank_score": 0.90, "screen_status": "monitor",
         "investment_potential": {"peer_group": "a"}},
        {"candidate_id": "fund:FDTS", "entity_kind": "public_fund",
         "rank_score": 0.80, "screen_status": "qualified",
         "investment_potential": {"peer_group": "b"}},
    ]
    _rank_candidate_lanes(candidates)
    for rank, row in enumerate(candidates, start=1):
        row["rank"] = rank
    _assign_research_ranks(candidates)

    by_id = {row["candidate_id"]: row for row in candidates}
    assert (by_id["fund:FDTS"]["rank"], by_id["fund:FDTS"]["research_rank"]) == (4, 2)
    assert "research_rank" not in by_id["fund:monitor"]
    assert research_rank_priority(by_id["fund:FDTS"]) == 998_000
    assert research_rank_priority(by_id["fund:FDTS"]) > research_rank_priority(
        by_id["fund:monitor"]
    )


def test_equity_rank_program_rejects_declared_beta_fallback() -> None:
    candidate = {
        "candidate_id": "equity:X", "entity_id": "X", "entity_kind": "public_equity",
        "score_components": {
            "durable_earnings_power": .5, "price_implied_excess_return": .5,
            "earnings_power_margin": .5, "low_implied_growth": .5,
            "evidence_coverage": 1.0,
        },
        "criteria": [{"passed": True}], "source_refs": ["source:x"],
        "beta_receipt": {"status": "declared_fallback"},
    }
    fallback = _compile_rank_program_input(
        [candidate], run_id="r", as_of="2026-08-14T00:00:00Z",
        equity_benchmark_id="SPY",
    )["lanes"][0]["candidates"][0]
    candidate["beta_receipt"] = {"status": "estimated"}
    estimated = _compile_rank_program_input(
        [candidate], run_id="r", as_of="2026-08-14T00:00:00Z",
        equity_benchmark_id="SPY",
    )["lanes"][0]["candidates"][0]
    assert (fallback["rank_program_eligible"], estimated["rank_program_eligible"]) == (False, True)


def test_subscription_dossier_waits_for_exact_evidence_ready_parent(tmp_path) -> None:
    db = tmp_path / "queue.sqlite3"
    work_id, leaf = "investment-enrichment:test:one", "a" * 64
    connection = work_queue.connect(str(db))
    work_queue.enqueue(connection, kind=ENRICHMENT_JOB_KIND, priority=1, payload={
        "work_id": work_id, "candidate_leaf": leaf, "stage": "queued",
        "expected_exit": "evidence_ready_or_typed_block", "capital_authority": False,
    })
    connection.close()
    request = {"job_id": work_id, "candidate_leaf": leaf}
    with pytest.raises(ValueError, match="one completed queue item"):
        require_research_parent_ready(db_path=db, request=request)
    connection = work_queue.connect(str(db))
    work_queue.update_status(connection, work_id=work_id, status="done", payload_update={
        "stage": "evidence_ready", "result_status": "evidence_ready",
        "completed_at": "2026-08-14T00:00:00Z", "capital_authority": False,
    })
    connection.close()
    assert require_research_parent_ready(db_path=db, request=request)["stage"] == "evidence_ready"


def test_potential_ranking_never_compares_fund_sleeves_or_rewards_missing_valuation() -> None:
    candidates = [
        {"candidate_id": "equity", "entity_kind": "public_equity", "rank_score": 0.01},
        {"candidate_id": "fund-a2", "entity_kind": "public_fund", "rank_score": 0.60,
         "investment_potential": {"peer_group": "sleeve-a"}},
        {"candidate_id": "fund-b1", "entity_kind": "public_fund", "rank_score": 0.99,
         "investment_potential": {"peer_group": "sleeve-b"}},
        {"candidate_id": "fund-a1", "entity_kind": "public_fund", "rank_score": 0.80,
         "investment_potential": {"peer_group": "sleeve-a"}},
    ]
    _rank_candidate_lanes(candidates)
    ranks = {row["candidate_id"]: row["potential_rank"] for row in candidates}
    assert (ranks["fund-a1"]["peer_rank"], ranks["fund-b1"]["peer_rank"],
            ranks["fund-a2"]["peer_rank"]) == (1, 1, 2)
    assert [row["candidate_id"] for row in candidates] == [
        "equity", "fund-a1", "fund-b1", "fund-a2",
    ]
    assert _fund_score({"investment_potential": {"score": None}}) == (None, {})

    low = {
        "earnings_yield": 0.02, "book_to_price": 0.20,
        "earnings_power_margin": -0.50, "factor_return_per_volatility": 0.20,
        "drawdown_resilience": -0.50, "fee_efficiency": -0.01,
        "factor_fit_coverage": 0.20,
    }
    high = {name: value + 1 for name, value in low.items()}
    merged = [
        {"candidate_id": "left:a", "entity_id": "A", "entity_kind": "public_fund",
         "rank_score": 0.99, "investment_potential": {
             "peer_group": "same-sleeve", "coordinates": low}},
        {"candidate_id": "right:b", "entity_id": "B", "entity_kind": "public_fund",
         "rank_score": 0.01, "investment_potential": {
             "peer_group": "same-sleeve", "coordinates": high}},
    ]
    _rank_candidate_lanes(merged)
    assert [row["entity_id"] for row in merged] == ["B", "A"]
    assert merged[0]["investment_potential"]["normalization_population"] == 2


def test_fund_potential_quotients_shared_evidence_carriers() -> None:
    components = {
        "earnings_yield": 0.8, "book_to_price": 0.6,
        "factor_return_per_volatility": 0.7, "drawdown_resilience": 0.4,
        "fee_efficiency": 0.9, "factor_fit_coverage": 0.1,
        "net_earnings_yield": 0.2, "factor_return_after_fee": 0.3,
    }
    score, _ = fund_potential_family_score(components)
    changed_diagnostics = {
        **components, "factor_fit_coverage": 1.0,
        "net_earnings_yield": 1.0, "factor_return_after_fee": 1.0,
    }
    assert fund_potential_family_score(changed_diagnostics)[0] == score
    receipt = fund_evidence_vote_receipt(
        components, analysis_sha256="factor-analysis", valuation_source_refs=["issuer:fund"],
    )
    assert receipt["shared_carrier_controls"]["aligned_return_panel"]["analysis_sha256"] == "factor-analysis"
    assert receipt["shared_carrier_controls"]["expense_ratio"]["excluded_derived_votes"] == [
        "net_earnings_yield", "factor_return_after_fee",
    ]
    assert verify_fund_evidence_vote_receipt(receipt)
    assert not verify_fund_evidence_vote_receipt({**receipt, "rule_id": "tampered"})


def test_legacy_fund_valuation_missing_coordinate_blocks_without_crashing() -> None:
    valuation = _fund_valuation(
        evidence=[
            {"metric_id": "portfolio_price_to_earnings", "value": 20, "source_ref": "issuer"},
            {"metric_id": "portfolio_price_to_book", "value": 2, "source_ref": "issuer"},
            {"metric_id": "expense_ratio", "value": 0.001, "source_ref": "issuer"},
        ],
        required_return=0.08,
        payout_ratio_assumptions=[0.5],
    )
    assert valuation is not None
    legacy = {key: value for key, value in valuation.items() if key != "earnings_yield"}
    coordinates, blockers = bound_fund_valuation_coordinates(legacy)
    assert coordinates is None
    assert blockers == ("valuation_coordinate_absent:earnings_yield",)
    score, components = _fund_score({
        "analysis": {
            "fit": {"leave_one_out_r2": 0.5},
            "assumption_implied": {"return_without_residual_alpha": 0.08},
            "historical": {
                "maximum_drawdown": -0.2,
                "candidate_annualized_volatility": 0.15,
            },
        },
        "valuation": legacy,
    })
    assert score is None
    assert components == {}


def test_market_intent_and_catalog_scope_are_explicit() -> None:
    intent = compile_research_intent("Identify mid-cap value funds", max_results=10)
    assert intent["entity_kinds"] == ["public_fund"]
    assert intent["capitalization"] == "mid"
    assert intent["styles"] == ["value"]
    open_theme = compile_research_intent(
        "Find mid-cap companies in a specialized industrial theme",
        overrides={"theme_terms": ["aerospace", "defense"]},
    )
    assert open_theme["theme_terms"] == ["aerospace", "defense"]
    assert open_theme["translation"]["structured_override"] is True
    catalog = {
        "schema": "jaggedthoughts-public-market-catalog-v1",
        "catalog_sha256": "a" * 64,
        "retrieved_at": "2026-08-09T00:00:00Z",
        "security_count": 3,
        "securities": [
            {"security_id": "public_fund:MV", "symbol": "MV", "name": "Mid Cap Value ETF", "entity_kind": "public_fund", "security_kind": "exchange_traded_fund"},
            {"security_id": "public_fund:LG", "symbol": "LG", "name": "Large Growth ETF", "entity_kind": "public_fund", "security_kind": "exchange_traded_fund"},
            {"security_id": "public_equity:CO", "symbol": "CO", "name": "Company Common Stock", "entity_kind": "public_equity", "security_kind": "common_equity", "market_cap": 5e9},
        ],
    }
    scout = compile_market_scout(catalog, intent, completed_at="2026-08-09T01:00:00Z")
    assert [row["symbol"] for row in scout["candidates"]] == ["MV"]
    assert scout["population"] == {
        "catalog_count": 3, "evaluated_count": 3, "eligible_count": 1,
        "returned_count": 1, "truncated": False,
        "rejected_by_reason": {"entity_kind": 1, "fund_name_style": 1},
    }


def test_enrichment_cycle_respects_identity_diversity_and_source_budgets() -> None:
    def security(symbol: str, kind: str, *, sector: str = "", volume: int = 1000) -> dict:
        return {
            "security_id": f"{kind}:{symbol}", "symbol": symbol,
            "name": f"{symbol} candidate", "entity_kind": kind,
            "sector": sector, "industry": f"{sector} services", "volume": volume,
            "last_price": 25, "market_cap": 5_000_000_000,
            "one_year_return": 0.05,
            "requested_measurements": ["durable_earnings", "implied_growth", "valuation"],
        }

    scout_runs = [{
        "run_id": "companies", "run_path": "research_jobs/companies.json",
        "scheduled_intent_id": "value-companies",
        "intent": {"capitalization": "mid", "styles": ["value"]},
        "candidates": [
            security("TECH1", "public_equity", sector="Technology", volume=9000),
            security("TECH2", "public_equity", sector="Technology", volume=8000),
            security("IND1", "public_equity", sector="Industrials", volume=7000),
            security("HLTH1", "public_equity", sector="Health Care", volume=6000),
        ],
    }, {
        "run_id": "funds", "run_path": "research_jobs/funds.json",
        "scheduled_intent_id": "value-funds",
        "intent": {"capitalization": "mid", "styles": ["value"]},
        "candidates": [
            security("FUND1", "public_fund", volume=5000),
            security("FUND2", "public_fund", volume=4000),
        ],
    }]
    cycle = compile_enrichment_cycle(
        scout_runs=scout_runs, policy=default_enrichment_policy(),
        enrolled_security_ids={"public_equity:IND1"}, enabled_source_count=16,
        completed_at="2026-08-09T12:00:00Z",
    )
    selected = [row for row in cycle["candidates"] if row["selection_status"] == "selected"]
    assert sum(row["entity_kind"] == "public_equity" for row in selected) == 2
    assert sum(row["entity_kind"] == "public_fund" for row in selected) == 2
    assert len({row.get("sector") for row in selected if row["entity_kind"] == "public_equity"}) == 2
    assert "public_equity:IND1" not in cycle["selected_security_ids"]
    assert cycle["budget_usage"]["estimated_total_source_calls"] <= 28
    assert cycle["score_contract"]["kind"] == "uncalibrated_acquisition_priority_proxy"


def test_enrichment_preserves_a_potential_scoped_scout_order() -> None:
    def candidate(symbol: str, potential: float, volume: int) -> dict:
        return {
            "security_id": f"public_equity:{symbol}", "symbol": symbol,
            "name": symbol, "entity_kind": "public_equity", "sector": "Technology",
            "industry": "Software", "volume": volume, "last_price": 10,
            "market_cap": 2_000_000_000, "base_priority": potential,
            "requested_measurements": ["durability"],
        }

    cycle = compile_enrichment_cycle(
        scout_runs=[{
            "run_id": "potential", "potential_scope_only": True,
            "intent": {}, "candidates": [
                candidate("HIGH", 0.9, 1), candidate("LIQUID", 0.1, 1_000_000),
            ],
        }],
        policy=default_enrichment_policy(), enrolled_security_ids=(),
        enabled_source_count=0, completed_at="2026-08-13T12:00:00Z",
    )
    assert cycle["selected_security_ids"][0] == "public_equity:HIGH"
    assert cycle["candidates"][0]["base_priority_source"] == (
        "deterministic_investment_potential"
    )
    assert cycle["score_contract"]["kind"] == (
        "deterministic_potential_then_acquisition_diversity"
    )


def test_interrupted_enrichment_resumes_by_current_potential(tmp_path: Path) -> None:
    screen_path = tmp_path / "data/sec_frames/latest.json"
    screen_path.parent.mkdir(parents=True)
    screen_path.write_text(json.dumps({"research_queue": [
        {"security_id": "public_equity:HIGH", "rank": 1, "research_priority_score": .9},
        {"security_id": "public_equity:LOW", "rank": 2, "research_priority_score": .1},
    ]}), encoding="utf-8")
    catalog_path = tmp_path / "universe/catalog-latest.json"
    catalog_path.parent.mkdir(parents=True)
    catalog_path.write_text(json.dumps({"securities": [
        {"security_id": "public_equity:HIGH", "sector": "Technology"},
        {"security_id": "public_equity:LOW", "sector": "Industrials"},
    ]}), encoding="utf-8")
    def queued(symbol: str, priority: int) -> dict:
        return {"work_id": symbol, "kind": "jaggedthoughts_public_market_enrichment",
                "status": "queued", "attempts": 1, "max_attempts": 2,
                "priority": priority, "created_at": 1, "payload": {
                    "work_id": symbol, "security_id": f"public_equity:{symbol}",
                    "symbol": symbol, "entity_kind": "public_equity",
                    "cost": {"incremental_source_calls": 3, "research_minutes": 40}}}
    cycle = {"budget_limits": {"max_equities": 1, "max_funds": 0,
              "max_equities_per_sector": 1, "max_incremental_source_calls": 3,
              "max_total_source_calls": 10, "max_estimated_research_minutes": 40},
             "budget_usage": {"equities": 0, "funds": 0,
              "incremental_source_calls": 0, "estimated_total_source_calls": 0,
              "estimated_research_minutes": 0, "sec_registry_batch_source_calls": 0},
             "candidates": []}

    selected = _resumable_enrichment_jobs(
        root=tmp_path, queue_rows=[queued("LOW", 99), queued("HIGH", 1)],
        cycle=cycle, enrolled_security_ids={"public_equity:HIGH", "public_equity:LOW"},
        exclude_work_ids=set(),
    )

    assert [row["symbol"] for row in selected] == ["HIGH"]

    rank_db = tmp_path / "rank-queue.sqlite3"
    connection = work_queue.connect(str(rank_db))
    work_queue.enqueue(connection, kind="jaggedthoughts_public_market_enrichment",
                       priority=99, payload=queued("LOW", 99)["payload"])
    work_queue.enqueue(connection, kind="jaggedthoughts_public_market_enrichment",
                       priority=1, payload=queued("HIGH", 1)["payload"])
    connection.close()
    changed = _rebase_current_enrichment_priorities(
        db_path=rank_db,
        queue_rows=research_job_snapshot(rank_db, limit=10)["jobs"],
        potential_screen=json.loads(screen_path.read_text(encoding="utf-8")),
    )
    ranked = {row["work_id"]: row for row in research_job_snapshot(rank_db, limit=10)["jobs"]}
    assert set(changed) == {"HIGH", "LOW"}
    assert ranked["HIGH"]["priority"] > ranked["LOW"]["priority"]

    db_path = tmp_path / "queue.sqlite3"
    events_path = tmp_path / "events.jsonl"
    connection = work_queue.connect(str(db_path))
    stale = queued("STALE", 100)["payload"]
    stale.update({"job_sha256": "stale", "cycle_sha256": "old"})
    current = queued("HIGH", 1)["payload"]
    current.update({"job_sha256": "current", "cycle_sha256": "old"})
    for job in (stale, current):
        work_queue.record_terminal_item(
            connection, kind="jaggedthoughts_public_market_enrichment",
            status="dead_letter", priority=1, max_attempts=2, payload=job,
        )
    connection.close()
    rows = research_job_snapshot(db_path, limit=10)["jobs"]
    recovered = _recover_interrupted_enrichment_jobs(
        db_path=db_path, events_path=events_path, queue_rows=rows,
        current_security_ids={"public_equity:HIGH"}, max_attempts=2,
    )
    after = {row["work_id"]: row for row in research_job_snapshot(db_path, limit=10)["jobs"]}
    assert recovered == ["HIGH"]
    assert after["HIGH"]["status"] == "queued"
    assert after["HIGH"]["payload"]["cycle_sha256"] == "old"
    assert after["STALE"]["status"] == "dead_letter"


def test_optional_signal_block_does_not_erase_derivable_outputs() -> None:
    source = MetricObservation(
        "source:cash", "ACME", "cash", 10, "USD",
        "2026-08-09T00:00:00Z", "2026-08-09T01:00:00Z", "filing",
    )
    definitions = (
        SignalDefinition.from_dict({
            "id": "cash-copy", "entity_id": "ACME", "metric_id": "cash_copy",
            "operator": "identity", "arguments": [{"metric": "cash"}],
            "unit": "USD", "description": "Available output",
        }),
        SignalDefinition.from_dict({
            "id": "debt-copy", "entity_id": "ACME", "metric_id": "debt_copy",
            "operator": "identity", "arguments": [{"metric": "debt"}],
            "unit": "USD", "description": "Blocked output",
        }),
    )
    rows, receipts, blocks = derive_signals_partial(
        (source,), definitions, as_of="2026-08-09T02:00:00Z",
    )
    assert any(row.metric_id == "cash_copy" for row in rows)
    assert [row.definition.signal_id for row in receipts] == ["cash-copy"]
    assert blocks[0]["signal_id"] == "debt-copy"


def test_owner_earnings_requires_one_fiscal_epoch() -> None:
    definition = next(
        row for row in standard_signal_definitions("ACME", "public_equity")
        if row.metric_id == "normalized_owner_earnings"
    )
    cash_flow = MetricObservation(
        "ocf:2025", "ACME", "operating_cash_flow_fy", 100, "USD/year",
        "2025-12-31T00:00:00Z", "2026-02-01T00:00:00Z", "filing:2025",
    )
    capex = MetricObservation(
        "capex:2025", "ACME", "capital_expenditure_fy", 30, "USD/year",
        "2025-12-31T00:00:00Z", "2026-02-01T00:00:00Z", "filing:2025",
    )
    aligned, _receipts, _blocks = derive_signals_partial(
        (cash_flow, capex), (definition,), as_of="2026-03-01T00:00:00Z",
    )
    assert next(row.value for row in aligned if row.metric_id == "normalized_owner_earnings") == 70

    old_capex = MetricObservation(
        "capex:2024", "ACME", "capital_expenditure_fy", 30, "USD/year",
        "2024-12-31T00:00:00Z", "2025-02-01T00:00:00Z", "filing:2024",
    )
    stale_output = MetricObservation(
        "signal:old", "ACME", "normalized_owner_earnings", 70, "USD/year",
        "2024-12-31T00:00:00Z", "2025-02-01T00:00:00Z", "signal:standard:ACME:old",
    )
    misaligned, _receipts, blocks = derive_signals_partial(
        (cash_flow, old_capex, stale_output), (definition,), as_of="2026-03-01T00:00:00Z",
    )
    assert not any(row.metric_id == "normalized_owner_earnings" for row in misaligned)
    assert "same observed_at" in blocks[0]["reason"]


def test_research_dossier_binds_the_exact_agent_request() -> None:
    identity = {
        "candidate_leaf": "a" * 64, "candidate_sha256": "b" * 64,
        "entity_id": "ACME", "as_of": "2026-08-09T00:00:00Z",
    }
    request = {
        "schema": "jaggedthoughts-agent-research-request-v1",
        **identity, "request_id": "research:acme", "request_sha256": "c" * 64,
        "research_question_frontier": {
            "selected_program": {"atom_ids": ["rival_mechanism_falsifier"]},
        },
    }
    dossier = {
        "schema": "jaggedthoughts-candidate-research-dossier-v1",
        **identity, "request_id": "research:acme", "request_sha256": "c" * 64,
        "generated_at": "2026-08-10T00:00:00Z",
        "thesis": {"claim": "Conditional claim", "mechanism": "Choice to cash flow", "confidence": 0.5},
        "rival_view": {"claim": "Rival", "mechanism": "Different chain"},
        "decisive_observation": {"observation": "Later report"},
        "falsifiers": [{"condition": "Fails"}], "catalysts": [],
        "strategy": {
            "choices": [{"id": "choice", "description": "Choice", "evidence_refs": ["filing"]}],
            "reinforcing_edges": [],
            "feasibility_constraints": {
                "incompatibilities": [], "prerequisites": [],
                "resources": [{
                    "constraint_id": "team_capacity", "resource_id": "team",
                    "unit": "teams", "limit": 1,
                    "uses": [{"option_id": "choice", "amount": 1}],
                    "evidence_refs": ["filing"],
                }],
            },
        },
        "industry": {"profit_pool": "Services"},
        "durable_earnings_bridge": {"revenue_durability": "Conditional"},
        "valuation_assumptions": {"base_growth": 0.03},
        "research_question_outcomes": [{
            "atom_id": "rival_mechanism_falsifier", "status": "mixed",
            "finding": "Both mechanisms remain possible.", "evidence_refs": ["filing"],
        }],
        "sources": [{
            "id": "filing", "title": "Filing", "url": "https://example.test/filing",
            "publisher": "Issuer", "published_at": "2026-08-09",
            "accessed_at": "2026-08-10T00:00:00Z", "source_kind": "filing",
            "supports": [
                "claim", "rival_mechanism_falsifier", "strategy_constraint:team_capacity",
            ],
        }, {
            "id": "issuer", "title": "Release", "url": "https://example.test/release",
            "publisher": "Issuer", "published_at": "2026-08-09",
            "accessed_at": "2026-08-10T00:00:00Z", "source_kind": "issuer",
            "supports": ["mechanism"],
        }],
    }
    normalized = validate_research_dossier(dossier, expected_identity=identity, request=request)
    normalized_body = {key: value for key, value in normalized.items() if key != "dossier_sha256"}
    assert normalized["dossier_sha256"] == stable_sha256(normalized_body)
    assert normalized["sources"][0]["published_at"] == "2026-08-09"
    unsupported_constraint = deepcopy(dossier)
    unsupported_constraint["sources"][0]["supports"].pop()
    with pytest.raises(ValueError, match="lacks exact source support"):
        validate_research_dossier(
            unsupported_constraint, expected_identity=identity, request=request,
        )
    whitespace_date = deepcopy(dossier)
    whitespace_date["sources"][0]["published_at"] = " 2026-08-09 "
    assert validate_research_dossier(
        whitespace_date, expected_identity=identity, request=request,
    )["sources"][0]["published_at"] == "2026-08-09"
    ambiguous = deepcopy(dossier)
    ambiguous["sources"][0]["published_at"] = "current data through 2026-08-09"
    with pytest.raises(ResearchEvidenceTimestampError) as raised:
        validate_research_dossier(ambiguous, expected_identity=identity, request=request)
    assert raised.value.to_dict() == {
        "reason_code": "ambiguous_or_invalid_publication_time",
        "field": "candidate dossier sources[0].published_at",
        "source_index": 0, "source_id": "filing",
        "source_url": "https://example.test/filing",
        "raw_value": "current data through 2026-08-09",
        "publication_time_inferred": False,
    }
    assert raised.value.dossier_body_sha256 == stable_sha256(ambiguous)
    same_day = deepcopy(dossier)
    same_day["sources"][0]["published_at"] = "2026-08-10"
    same_day["sources"][0]["accessed_at"] = "2026-08-10T00:00:01Z"
    validate_research_dossier(same_day, expected_identity=identity, request=request)
    same_day["sources"][0]["published_at"] = "2026-08-11"
    with pytest.raises(ValueError, match="accessed before publication"):
        validate_research_dossier(same_day, expected_identity=identity, request=request)
    accepted = validate_research_dossier(
        {**dossier, "generated_at": "2099-01-01T00:00:00Z"},
        expected_identity=identity, request=request,
        accepted_at="2026-08-10T01:00:00Z",
    )
    assert accepted["generated_at"] == "2026-08-10T01:00:00Z"
    assert {row["accessed_at"] for row in accepted["sources"]} == {
        "2026-08-10T01:00:00Z"
    }
    with pytest.raises(ValueError, match="bind"):
        validate_research_dossier(
            {**dossier, "request_sha256": "d" * 64},
            expected_identity=identity, request=request,
        )


def test_company_strategy_option_fixture_closes_only_its_declared_scope() -> None:
    payload = yaml.safe_load((EXAMPLE / "company_strategy_options.yaml").read_text(encoding="utf-8"))
    result = compile_company_strategy_frontier(payload)
    assert result["enumeration"]["program_count"] == 11
    assert result["choice_space_certificate"]["feasible_bundle_count"] == 11
    assert result["enumeration"]["method"] == "z3_associative_commutative_option_set_quotient"
    assert result["scope_closed"] is True
    assert result["decision_closed"] is False
    assert result["constraint_witnesses"]
    assert result["neighborhood"]["edge_count"] == len(result["neighborhood"]["edges"])
    assert result["neighborhood"]["search_edge_count"] > result["neighborhood"]["edge_count"]
    assert result["choice_space_certificate"]["excluded_bundle_count"] == 3
    assert result["choice_space_certificate"]["excluded_bundles"] == [
        {
            "option_ids": ["broaden_customer_program", "commodity_price_push"],
            "violated_constraint_ids": [
                "incompatible:broaden_customer_program:commodity_price_push",
            ],
        },
        {
            "option_ids": [
                "broaden_customer_program", "co_design_interface", "commodity_price_push",
            ],
            "violated_constraint_ids": [
                "incompatible:broaden_customer_program:commodity_price_push",
            ],
        },
        {
            "option_ids": [
                "broaden_customer_program", "commodity_price_push", "qualify_second_input",
            ],
            "violated_constraint_ids": [
                "incompatible:broaden_customer_program:commodity_price_push",
            ],
        },
    ]
    assert all(len(row["target_option_ids"]) == len(row["base_option_ids"]) + 1
               for row in result["neighborhood"]["edges"])
    assert len(result["option_catalog"]) == len(payload["options"])
    assert len(result["interaction_catalog"]) == len(payload["interactions"])
    assert all(
        interaction["interaction_sha256"] in program["active_interaction_sha256s"]
        for interaction in result["interaction_catalog"]
        for program in result["programs"]
        if set(interaction["option_ids"]).issubset(program["unique_option_ids"])
    )
    assert result["frontier_programs"]
    assert any(row["objective_values"]["industry_pressure_coverage"] == 1 for row in result["frontier_programs"])
    policy = result["contingent_policy_catalog"][0]
    assert policy["company_id"] == "ALPHA"
    assert policy["commit_option_ids"] == ["qualify_second_input"]
    assert len(policy["final_programs"]) == 3
    assert {row["threshold_basis"] for row in policy["conditions"]} == {"reference_fixture"}
    assert policy["policy_action_regions"]["total_over_condition_space"] is True
    assert policy["policy_action_regions"]["deterministic_over_condition_space"] is True
    recourse = select_company_contingent_recourse(
        policy, evaluated_at="2026-10-05T00:00:00Z", observations=(
            MetricObservation(
                "alpha-demand-q3", "ALPHA", "adjacent_program_demand_score", 0.7,
                "decimal score", "2026-09-30T20:00:00Z", "2026-10-02T00:00:00Z",
                "alpha-q3-report",
            ),
            MetricObservation(
                "alpha-margin-q3", "ALPHA", "interface_contribution_margin", 0.1,
                "decimal margin", "2026-09-30T20:00:00Z", "2026-10-02T00:00:00Z",
                "alpha-q3-report",
            ),
        ),
    )
    assert recourse["selected_final_option_ids"] == [
        "broaden_customer_program", "qualify_second_input",
    ]
    mislabeled = deepcopy(payload)
    mislabeled["company"]["data_class"] = "operator"
    with pytest.raises(ValueError, match="reference-fixture thresholds"):
        compile_company_strategy_frontier(mislabeled)
    reordered = compile_company_strategy_frontier({**payload, "options": list(reversed(payload["options"]))})
    assert reordered["choice_space_certificate"]["choice_space_sha256"] == result["choice_space_certificate"]["choice_space_sha256"]
    constrained_payload = deepcopy(payload)
    constrained_payload["feasibility_constraints"] = {
        "prerequisites": [{
            "option_id": "broaden_customer_program",
            "requires": ["qualify_second_input"],
            "evidence_refs": ["investment_memo"],
        }],
        "resources": [{
            "resource_id": "management_bandwidth", "unit": "team_quarters",
            "limit": 3, "uses": {
                "broaden_customer_program": 2, "co_design_interface": 2,
            }, "evidence_refs": ["investment_memo"],
        }],
    }
    constrained = compile_company_strategy_frontier(constrained_payload)
    bundles = [set(row["option_ids"]) for row in constrained["choice_space_certificate"]["feasible_bundles"]]
    assert all("broaden_customer_program" not in row or "qualify_second_input" in row for row in bundles)
    assert all(not {"broaden_customer_program", "co_design_interface"}.issubset(row) for row in bundles)
    assert any(row["kind"] == "missing_prerequisite" for row in constrained["constraint_witnesses"])
    assert any(row["kind"] == "resource_limit" for row in constrained["constraint_witnesses"])
    explanation = explain_strategy_bundle_feasibility(constrained, (
        "broaden_customer_program", "co_design_interface", "commodity_price_push",
    ))
    assert explanation["feasible"] is False
    assert set(explanation["violated_constraint_ids"]) == {
        "incompatible:broaden_customer_program:commodity_price_push",
        "prerequisite:broaden_customer_program", "resource:management_bandwidth",
    }


def test_strategy_move_identity_ignores_evolving_calibration_projection(tmp_path: Path) -> None:
    payload = yaml.safe_load((EXAMPLE / "company_strategy_options.yaml").read_text(encoding="utf-8"))
    library = compile_strategy_move_library((compile_company_strategy_frontier(payload),))
    store = GoldenStore(tmp_path / "strategy.sqlite3")
    record_strategy_move_library(store, owner="research", library=library)
    changed = deepcopy(library)
    changed["moves"][0]["scenario_calibration_status"] = "challenged"
    body = {key: value for key, value in changed.items() if key != "library_sha256"}
    changed["library_sha256"] = stable_sha256(body)

    record_strategy_move_library(store, owner="research", library=changed)
    changed["moves"][0]["timing_refinement"] = {"classification": "interval_remains_censored"}
    changed["library_sha256"] = stable_sha256({key: value for key, value in changed.items() if key != "library_sha256"})
    record_strategy_move_library(store, owner="research", library=changed)


def test_strategy_outcome_contract_is_typed_and_prospective() -> None:
    payload = yaml.safe_load((EXAMPLE / "company_strategy_options.yaml").read_text(encoding="utf-8"))
    payload["options"][0]["outcome_contracts"] = [{
        "id": "margin-q", "metric_id": "operating_margin_q", "unit": "decimal",
        "direction": "increase", "minimum_effect": 0.01, "horizon_days": 90,
        "outcome_role": "leading_operating", "acquisition_mode": "point_in_time_observation",
        "comparator": "pre_move_baseline", "evidence_refs": ["sec-companyfacts"],
    }]
    contract = next(
        row for row in compile_company_strategy_frontier(payload)["option_catalog"]
        if row["outcome_contracts"]
    )["outcome_contracts"][0]
    assert (contract["outcome_role"], contract["acquisition_mode"]) == (
        "leading_operating", "point_in_time_observation",
    )
    payload["options"][0]["outcome_contracts"][0].update({
        "measurement_start_at": "2025-01-01T00:00:00Z", "horizon_days": 90,
    })
    with pytest.raises(ValueError, match="target must remain after its evidence epoch"):
        compile_company_strategy_frontier(payload)


def test_strategy_measurement_rejects_untyped_or_expired_supply_windows() -> None:
    event = {
        "implementation_mode": "supply_commitment",
        "occurred_at": "2021-07-13T00:00:00Z",
    }
    with pytest.raises(ValueError, match="mechanism_window_unresolved"):
        _measurement_relation(event, "2026-08-24T00:00:00Z")
    with pytest.raises(ValueError, match="expired_mechanism_gap"):
        _measurement_relation(
            {**event, "mechanism_effective_until": "2025-12-31T23:59:59Z"},
            "2026-08-24T00:00:00Z",
        )


def test_strategy_measurement_adds_a_contract_only_to_the_exact_successor() -> None:
    parent = yaml.safe_load((EXAMPLE / "company_strategy_options.yaml").read_text())
    option = parent["options"][0]
    option["mechanism"] = {
        "action": "secure_supply", "economic_bridge": "downside_resilience",
        "object_id": "qualified_input", "implementation_conditions": ["qualification"],
        "break_conditions": ["economics fail"], "evidence_refs": ["investment_memo"],
    }
    option["implementation_event"] = {
        "id": "announced-adoption", "event_kind": "first_public_observation",
        "implementation_mode": "organic_program", "status_after": "underway",
        "occurred_at": "2026-06-01T00:00:00Z",
        "available_at": "2026-06-01T00:00:00Z", "timing_precision": "date",
        "source_refs": ["investment_memo"],
    }
    frontier = compile_company_strategy_frontier(parent)
    library = compile_strategy_move_library((frontier,))
    move = next(row for row in library["moves"] if row["option_id"] == option["id"])
    assert move["implementation_event"]["treatment_timing_status"] == "interval_censored_adoption_event"
    event_request = compile_strategy_event_refinement_request(
        move, library_sha256=library["library_sha256"],
        search_end_at="2026-06-30T20:00:00Z",
    )
    event_result = compile_strategy_event_refinement_result({
        "schema": STRATEGY_EVENT_REFINEMENT_RESULT_SCHEMA,
        "request_sha256": event_request["request_sha256"],
        "move_sha256": move["move_sha256"], "entity_id": move["entity_id"],
        "classification": "exact_implementation_event_found",
        "assessed_at": "2026-06-30T20:00:30Z",
        "coverage": {
            "sec_filings_searched": True, "issuer_materials_searched": True,
            "search_start_at": event_request["search_start_at"],
            "search_end_at": event_request["search_end_at"],
        },
        "exact_event": {
            "event_id": "operational-adoption", "description": "Program became operational.",
            "occurred_at": "2026-06-01T00:00:00Z",
            "available_at": "2026-06-01T00:00:00Z",
            "implementation_mode": "organic_program", "implementation_state": "operational",
            "timing_precision": "date", "source_urls": ["https://example.test/issuer"],
        },
        "sources": [{
            "url": "https://example.test/issuer", "source_kind": "issuer",
            "published_at": "2026-06-01T00:00:00Z", "supports": ["exact_event"],
        }],
        "rationale": "Issuer dates the operating launch.", "residuals": [],
        "capital_authority": False,
    }, event_request)
    library = compile_strategy_move_library(
        (frontier,), event_refinement_requests=(event_request,),
        event_refinement_results=(event_result,),
    )
    move = next(row for row in library["moves"] if row["option_id"] == option["id"])
    request = compile_strategy_measurement_contract_request(
        move, library=library, parent_profile=parent,
        parent_profile_path="strategy_frontiers/alpha.yaml",
        created_at="2026-06-30T20:01:00Z",
    )
    assert request["implementation_event_source"] == "timing_refinement"
    forged = deepcopy(move)
    forged["timing_refinement"]["assessed_at"] = "2026-06-30T20:00:31Z"
    with pytest.raises(ValueError, match="exact member"):
        compile_strategy_measurement_contract_request(
            forged, library=library, parent_profile=parent,
            parent_profile_path="strategy_frontiers/alpha.yaml",
            created_at="2026-06-30T20:01:00Z",
        )
    bridge = move["mechanism"]["economic_bridge"]
    result = compile_strategy_measurement_contract_result({
        "schema": STRATEGY_MEASUREMENT_RESULT_SCHEMA,
        "request_sha256": request["request_sha256"], "move_sha256": move["move_sha256"],
        "option_id": move["option_id"], "assessed_at": "2026-06-30T20:02:00Z",
        "classification": "contract_found", "capital_authority": False,
        "sources": [{
            "id": "issuer-metric", "title": "Issuer operating metric",
            "url": "https://example.test/issuer", "publisher": "Alpha Components",
            "source_kind": "issuer", "published_at": "2026-06-01T00:00:00Z",
            "accessed_at": "2026-06-30T20:01:30Z",
            "supports": ["metric:qualified_program_revenue", "clock"],
        }],
        "contracts": [{
            "contract_id": "adoption-growth", "metric_id": "qualified_program_revenue",
            "unit": "usd", "direction": "increase", "minimum_effect": 0,
            "minimum_effect_basis": "directional_zero",
            "minimum_effect_rationale": "Freeze direction before the horizon settles.",
            "minimum_effect_source_refs": [], "horizon_days": 365,
            "measurement_start_at": "2026-06-30T20:01:00Z",
            "comparator": "pre_move_baseline", "outcome_role": "leading_operating",
            "acquisition_mode": "subscription_primary_document",
            "objective_coordinate": bridge,
            "metric_locator": "Issuer KPI table: qualified program revenue.",
            "economic_bridge_rationale": "Qualified revenue tests downside resilience.",
            "evidence_refs": ["issuer-metric"],
        }], "residuals": [],
    }, request)
    successor = build_strategy_measurement_successor_profile(parent, request, result)

    assert "outcome_contracts" not in option
    changed = [
        row["id"] for row in successor["options"]
        if row != next(parent_row for parent_row in parent["options"] if parent_row["id"] == row["id"])
    ]
    assert changed == [option["id"]]
    frozen_contract = successor["options"][0]["outcome_contracts"][0]
    assert frozen_contract["id"] == "adoption-growth"
    assert frozen_contract["measurement_source_catalog"] == result["sources"]
    matured = due_strategy_outcome_requests(
        compile_strategy_move_library((compile_company_strategy_frontier(successor),)),
        as_of="2027-07-01T20:02:00Z",
    )
    assert matured[0]["metric_locator"] == frozen_contract["metric_locator"]
    assert matured[0]["measurement_source_catalog"] == result["sources"]
    assert matured[0]["unit"] == frozen_contract["unit"]
    short_runway = deepcopy(result)
    short_runway.pop("result_sha256")
    short_runway["contracts"][0]["horizon_days"] = 30
    with pytest.raises(ValueError, match="prospective runway"):
        compile_strategy_measurement_contract_result(short_runway, request)
    unbound_comparator = deepcopy(result)
    unbound_comparator.pop("result_sha256")
    unbound_comparator["contracts"][0]["comparator"] = "matched_peer"
    with pytest.raises(ValueError, match="unsupported measurement direction or comparator"):
        compile_strategy_measurement_contract_result(unbound_comparator, request)


def test_strategy_measurement_schedules_one_branch_from_latest_frontier() -> None:
    older = yaml.safe_load((EXAMPLE / "company_strategy_options.yaml").read_text())
    for index, option in enumerate(older["options"][:2]):
        option["mechanism"] = {
            "action": "secure_supply", "economic_bridge": "downside_resilience",
            "object_id": f"program-{index}", "implementation_conditions": ["operational"],
            "break_conditions": ["economics fail"], "evidence_refs": option["evidence_refs"],
        }
        option["implementation_event"] = {
            "id": f"adoption-{index}", "event_kind": "adoption",
            "implementation_mode": "organic_program", "status_after": "underway",
            "occurred_at": "2026-06-01T00:00:00Z",
            "available_at": "2026-06-15T00:00:00Z", "timing_precision": "date",
            "source_refs": option["evidence_refs"],
        }
    newer = deepcopy(older)
    newer["evidence_epoch"] = "2026-07-01T00:00:00Z"
    older_frontier = compile_company_strategy_frontier(older)
    newer_frontier = compile_company_strategy_frontier(newer)
    library = compile_strategy_move_library((older_frontier, newer_frontier))

    due = due_strategy_measurement_contract_requests(
        library,
        parent_profiles={
            older_frontier["strategy_frontier_sha256"]: ("older.yaml", older),
            newer_frontier["strategy_frontier_sha256"]: ("newer.yaml", newer),
        },
        as_of="2026-07-02T00:00:00Z", max_requests=4,
    )

    assert len(due) == 1
    assert due[0]["parent_strategy_frontier_sha256"] == newer_frontier[
        "strategy_frontier_sha256"
    ]


def test_subscription_strategy_profile_is_dossier_bound_and_compile_checked() -> None:
    profile = yaml.safe_load((EXAMPLE / "company_strategy_options.yaml").read_text(encoding="utf-8"))
    profile["evidence_epoch"] = "2026-06-30T20:00:00Z"
    profile["options"] = profile["options"][:2]
    profile["interactions"] = []
    profile.pop("contingent_policies", None)
    profile["max_bundle_size"] = 2
    for scenario in profile["scenarios"]:
        scenario["base"] = [0, 0, 0, 0]
    mechanisms = (
        ("secure_supply", "downside_resilience", "critical_input"),
        ("expand_adjacent_scope", "growth", "adjacent_buyer_programs"),
    )
    for option, (action, bridge, object_id) in zip(profile["options"], mechanisms, strict=True):
        option["mechanism"] = {
            "action": action, "economic_bridge": bridge, "object_id": object_id,
            "implementation_conditions": ["execution succeeds"],
            "break_conditions": ["economics fail"], "evidence_refs": option["evidence_refs"],
        }
        option["scenario_effects"] = {
            scenario["id"]: [0, 1, 0, 1] for scenario in profile["scenarios"]
        }
    constraint_candidates = {
        "incompatibilities": [{
            "constraint_id": "exclusive_programs",
            "option_ids": sorted(option["id"] for option in profile["options"]),
            "evidence_refs": ["investment_memo"],
        }],
        "prerequisites": [], "resources": [],
    }
    profile["feasibility_constraints"] = deepcopy(constraint_candidates)
    dossier_sha = "d" * 64
    request_body = {
        "schema": "jaggedthoughts-strategy-frontier-request-v1",
        "request_id": "strategy-frontier:fixture", "entity_id": "ALPHA",
        "entity_kind": "public_equity", "candidate_leaf": "a" * 64,
        "candidate_sha256": "b" * 64, "source_request_sha256": "c" * 64,
        "dossier_path": "research/dossiers/alpha.json", "dossier_sha256": dossier_sha,
        "evidence_epoch": profile["evidence_epoch"],
        "source_ids": ["investment_memo", "point_in_time_export"],
        "current_dossier_source_ids": ["investment_memo", "point_in_time_export"],
        "feasibility_constraint_candidates": constraint_candidates,
        "feasibility_constraint_candidates_sha256": stable_sha256(constraint_candidates),
        "profile_schema": profile["schema"], "created_at": profile["evidence_epoch"],
        "capital_authority": False,
    }
    request = {**request_body, "request_sha256": stable_sha256(request_body)}
    proposal, compiled_profile = validate_strategy_frontier_proposal({
        "schema": "jaggedthoughts-strategy-frontier-proposal-v1",
        "request_sha256": request["request_sha256"], "dossier_sha256": dossier_sha,
        "entity_id": "ALPHA", "generated_at": profile["evidence_epoch"],
        "profile_yaml": yaml.safe_dump(profile), "capital_authority": False,
    }, request=request, dossier={
        "dossier_sha256": dossier_sha,
        "candidate_leaf": request["candidate_leaf"],
        "candidate_sha256": request["candidate_sha256"],
    })
    assert proposal["profile_sha256"] == stable_sha256(compiled_profile)
    assert compiled_profile["company"]["source_dossier_sha256"] == dossier_sha
    frontier = compile_company_strategy_frontier(compiled_profile)
    move = compile_strategy_move_library((frontier,))["moves"][0]
    assert (move["candidate_leaf"], move["candidate_sha256"]) == (
        request["candidate_leaf"], request["candidate_sha256"],
    )
    unbound = deepcopy(profile)
    unbound["options"][0]["outcome_contracts"] = [{
        "id": "direction", "metric_id": "margin", "unit": "ratio",
        "direction": "increase", "minimum_effect": 0.01, "horizon_days": 90,
        "comparator": "pre_move_baseline",
        "evidence_refs": unbound["options"][0]["evidence_refs"],
    }]
    with pytest.raises(ValueError, match="objective_coordinate"):
        validate_strategy_frontier_proposal({
            "schema": "jaggedthoughts-strategy-frontier-proposal-v1",
            "request_sha256": request["request_sha256"], "dossier_sha256": dossier_sha,
            "entity_id": "ALPHA", "generated_at": profile["evidence_epoch"],
            "profile_yaml": yaml.safe_dump(unbound), "capital_authority": False,
        }, request=request, dossier={
            "dossier_sha256": dossier_sha, "candidate_leaf": request["candidate_leaf"],
            "candidate_sha256": request["candidate_sha256"],
        })
    with pytest.raises(ValueError, match="candidate identities differ"):
        validate_strategy_frontier_proposal({
            "schema": "jaggedthoughts-strategy-frontier-proposal-v1",
            "request_sha256": request["request_sha256"], "dossier_sha256": dossier_sha,
            "entity_id": "ALPHA", "generated_at": profile["evidence_epoch"],
            "profile_yaml": yaml.safe_dump(profile), "capital_authority": False,
        }, request=request, dossier={
            "dossier_sha256": dossier_sha, "candidate_leaf": request["candidate_leaf"],
            "candidate_sha256": "f" * 64,
        })


def test_strategy_move_outcomes_preserve_business_and_investment_separation() -> None:
    payload = yaml.safe_load((EXAMPLE / "company_strategy_options.yaml").read_text(encoding="utf-8"))
    payload["options"][0]["outcome_contracts"] = [{
        "id": "margin", "metric_id": "operating_margin", "unit": "ratio",
        "direction": "increase", "minimum_effect": 0.01, "horizon_days": 365,
        "comparator": "pre_move_baseline", "objective_coordinate": "downside_resilience",
        "evidence_refs": ["filing"],
    }]
    payload["options"][0]["implementation_event"] = {
        "id": "adoption", "event_kind": "adoption", "status_after": "underway",
        "implementation_mode": "supply_commitment",
        "occurred_at": "2026-06-01T00:00:00Z", "available_at": "2026-06-02T00:00:00Z",
        "timing_precision": "date", "source_refs": ["filing"],
    }
    payload["options"][0]["mechanism"] = {
        "action": "secure_supply", "economic_bridge": "downside_resilience",
        "object_id": "critical_input", "implementation_conditions": ["qualification succeeds"],
        "break_conditions": ["supplier fails"], "evidence_refs": ["filing"],
    }
    frontier = compile_company_strategy_frontier(payload)
    equivalent_epoch = {**frontier, "evidence_epoch": "2026-06-30 20:00:00+00:00"}
    initial = compile_strategy_move_library((frontier, equivalent_epoch))
    assert initial["move_count"] == len(payload["options"])
    weaker = deepcopy(frontier)
    weaker.pop("strategy_frontier_sha256")
    weaker["choice_space_certificate"]["predicate_catalog"] = []
    weaker["strategy_frontier_sha256"] = stable_sha256(weaker)
    selected = compile_strategy_move_library((weaker, frontier))
    assert {row["strategy_frontier_sha256"] for row in selected["moves"]} == {
        frontier["strategy_frontier_sha256"]
    }
    evolved = compile_strategy_move_library((
        frontier, {**frontier, "evidence_epoch": "2026-07-01T20:00:00Z"},
    ))
    assert evolved["frontier_evolution_pair_count"] == 1
    assert evolved["frontier_evolution"][0]["mechanism_families"]["jaccard"] == 1
    assert evolved["frontier_evolution"][0]["preserved_strategy_choice_count"] == len(
        payload["options"]
    )
    revised_payload = deepcopy(payload)
    revised_payload["evidence_epoch"] = "2026-07-02T20:00:00Z"
    revised_payload["options"][3]["incompatible_with"] = []
    revised = compile_strategy_move_library((
        frontier, compile_company_strategy_frontier(revised_payload),
    ))["frontier_evolution"][0]["constraint_evolution"]
    assert len(revised["removed"]) == 1
    assert len(revised["newly_admitted_bundles"]) == 3
    assert revised["empirical_counterexample_bound"] is False
    assert initial["implementation_observed_move_count"] == 1
    assert initial["treatment_event_ready_move_count"] == 1
    move = next(row for row in initial["moves"] if row["outcome_contracts"])
    assert move["evidence_grade"] == "implementation_observed"
    assert due_strategy_outcome_requests(initial, as_of="2027-06-29T23:59:59Z") == []
    due = due_strategy_outcome_requests(initial, as_of="2027-06-30T20:00:00Z")
    assert [(row["move_sha256"], row["contract_sha256"]) for row in due] == [
        (move["move_sha256"], move["outcome_contracts"][0]["contract_sha256"]),
    ]
    outcome = {
        "schema": "jaggedthoughts-strategy-move-outcome-v1",
        "move_sha256": move["move_sha256"],
        "contract_sha256": move["outcome_contracts"][0]["contract_sha256"],
        "observed_at": "2027-06-30T20:00:00Z", "available_at": "2027-07-01T12:00:00Z",
        "unit": "ratio", "baseline_value": 0.10, "outcome_value": 0.13,
        "source_refs": ["filing:2027"],
    }
    learned = compile_strategy_move_library((compile_company_strategy_frontier(payload),), (outcome,))
    assert learned["outcome_episode_count"] == 1
    learned_move = next(row for row in learned["moves"] if row["move_sha256"] == move["move_sha256"])
    assert learned_move["outcome_episodes"][0]["status"] == "supports"
    assert learned_move["outcome_episodes"][0]["scenario_calibration_receipt"]["status"] == "supports_direction"
    assert learned_move["scenario_direction_hypotheses"][0]["ordinal_direction_summary"] == "increase"
    assert learned_move["scenario_calibration_status"] == "supports_direction"
    assert learned["frontier_calibrations"][0]["status"] == "supports_direction"
    assert learned_move["evidence_grade"] == "descriptive_outcome_support"
    mixed_payload = deepcopy(payload)
    first_scenario = mixed_payload["scenarios"][0]["id"]
    mixed_payload["options"][0]["scenario_effects"][first_scenario][3] = -1
    mixed_frontier = compile_company_strategy_frontier(mixed_payload)
    mixed_move = next(
        row for row in compile_strategy_move_library((mixed_frontier,))["moves"]
        if row["outcome_contracts"]
    )
    mixed_outcome = {
        **outcome, "move_sha256": mixed_move["move_sha256"],
        "contract_sha256": mixed_move["outcome_contracts"][0]["contract_sha256"],
    }
    mixed = compile_strategy_move_library((mixed_frontier,), (mixed_outcome,))
    mixed_learned_move = next(
        row for row in mixed["moves"] if row["move_sha256"] == mixed_move["move_sha256"]
    )
    assert mixed_learned_move["scenario_calibration_status"] == "inconclusive"
    assert mixed_learned_move["scenario_calibration_next_transition"] == (
        "bind_realized_scenario_or_restate_direction_in_successor_frontier"
    )
    assert learned["move_families"][0]["promotion_eligible"] is False
    with pytest.raises(ValueError, match="before its frozen horizon"):
        compile_strategy_move_library(
            (compile_company_strategy_frontier(payload),),
            ({**outcome, "observed_at": "2027-06-29T20:00:00Z"},),
        )


def test_strategy_calibration_successor_preserves_parent_identity() -> None:
    payload = yaml.safe_load((EXAMPLE / "company_strategy_options.yaml").read_text(encoding="utf-8"))
    payload["company"]["strategy_measurement_lineage"] = [{
        "parent_strategy_frontier_sha256": "a" * 64,
    }]
    payload["options"][0].update({
        "mechanism": {
            "action": "secure_supply", "economic_bridge": "downside_resilience",
            "object_id": "critical_input", "implementation_conditions": ["qualified"],
            "break_conditions": ["supplier fails"], "evidence_refs": ["filing"],
        },
        "outcome_contracts": [{
            "id": "margin", "metric_id": "operating_margin", "unit": "ratio",
            "direction": "increase", "minimum_effect": 0.01, "horizon_days": 365,
            "comparator": "pre_move_baseline", "objective_coordinate": "downside_resilience",
            "evidence_refs": ["filing"],
        }],
    })
    frontier = compile_company_strategy_frontier(payload)
    move = next(
        row for row in compile_strategy_move_library((frontier,))["moves"]
        if row["outcome_contracts"]
    )
    outcome = {
        "schema": "jaggedthoughts-strategy-move-outcome-v1",
        "move_sha256": move["move_sha256"],
        "contract_sha256": move["outcome_contracts"][0]["contract_sha256"],
        "observed_at": "2027-06-30T20:00:00Z", "available_at": "2027-07-01T12:00:00Z",
        "unit": "ratio", "baseline_value": 0.10, "outcome_value": 0.07,
        "source_refs": ["filing:2027"],
    }
    learned = compile_strategy_move_library((frontier,), (outcome,))
    receipt = next(
        episode["scenario_calibration_receipt"]
        for row in learned["moves"] for episode in row["outcome_episodes"]
    )
    assert receipt["status"] == "challenges_direction"
    base_body = {
        "schema": "jaggedthoughts-strategy-frontier-request-v1",
        "request_id": "base", "entity_id": "SARO", "dossier_sha256": "d" * 64,
        "created_at": "2026-08-09T00:00:00Z", "capital_authority": False,
    }
    base = {**base_body, "request_sha256": stable_sha256(base_body)}
    frozen_parent = deepcopy(frontier)
    first = _strategy_calibration_successor_request(base, frontier, (receipt,))
    assert first == _strategy_calibration_successor_request(base, frontier, (receipt,))
    assert frontier == frozen_parent
    assert first["parent_strategy_frontier_sha256"] == frontier["strategy_frontier_sha256"]
    assert first["evidence_epoch"] == receipt["available_at"]
    assert first["calibration_trigger"]["calibration_receipt_sha256s"] == [
        receipt["calibration_sha256"]
    ]
    assert first["preserved_measurement_contract_sha256s"] == [
        move["outcome_contracts"][0]["contract_sha256"]
    ]
    workspace = Path("/tmp/jaggedthoughts-test")
    assert _strategy_frontier_profile_path(workspace, first) != (
        _strategy_frontier_profile_path(workspace, base)
    )
    with pytest.raises(ValueError, match="exact challenge receipts"):
        _strategy_calibration_successor_request(
            base, frontier, ({**receipt, "metric_effect": {"value": 99}},),
        )


def test_strategy_group_time_panel_preserves_event_identity() -> None:
    assert _full_fiscal_treatment_period(
        datetime(2025, 11, 10, tzinfo=timezone.utc),
        (datetime(2024, 12, 31, tzinfo=timezone.utc), datetime(2025, 12, 31, tzinfo=timezone.utc)),
    ) == (2025, 2026)
    assert _full_fiscal_treatment_period(
        datetime(2026, 5, 28, tzinfo=timezone.utc),
        (datetime(2025, 5, 3, tzinfo=timezone.utc), datetime(2026, 5, 2, tzinfo=timezone.utc)),
    ) == (2027, 2028)
    law = next(
        row for row in default_law_catalog()["candidates"]
        if row["law_id"] == "reinforcing-strategy-choice-durability"
    )
    rows = []
    for cohort, prefix in ((2, "early"), (3, "late"), (None, "control")):
        for unit_index in range(4):
            unit = f"{prefix}-{unit_index}"
            event_sha = stable_sha256({"unit": unit, "cohort": cohort}) if cohort else None
            for period in range(5):
                effect = 1.0 if cohort is not None and period >= cohort else 0.0
                rows.append({
                    "schema": "jaggedthoughts-causal-panel-row-v2",
                    "law_id": law["law_id"], "unit_id": unit,
                    "period_index": period, "treated_group": cohort is not None,
                    "treatment_period": cohort, "treatment_event_sha256": event_sha,
                    "treatment_event_sha256s": [event_sha] if event_sha else [],
                    "treatment_timing_status": (
                        "exact_adoption_event" if cohort is not None else "never_treated_as_of_panel"
                    ),
                    "treatment_occurred_at": (
                        f"202{cohort}-01-01T00:00:00Z" if cohort is not None else None
                    ),
                    "treatment_available_at": (
                        f"202{cohort}-01-02T00:00:00Z" if cohort is not None else None
                    ),
                    "outcome_metric_id": "earnings_durability", "outcome_unit": "score",
                    "outcome": period * 0.1 + effect,
                    "observed_at": f"202{period}-12-31T23:59:59Z",
                    "available_at": f"202{period}-12-31T23:59:59Z",
                    "environment": {"industry_id": "fixture"},
                    "observation_ids": [f"filing:{unit}:{period}"],
                    "source_refs": [f"filing:{unit}"],
                })
    result = evaluate_difference_in_differences(law, rows, generated_at="2026-08-13T13:00:00Z")
    assert result["status"] == "diagnostic_direction_supported"
    assert result["design"].startswith("unadjusted group-time ATT")
    assert result["details"]["aggregate_att"] == pytest.approx(1.0)
    future = deepcopy(rows)
    future[-1]["available_at"] = "2026-08-14T00:00:00Z"
    with pytest.raises(ValueError, match="outcome unavailable"):
        evaluate_difference_in_differences(law, future, generated_at="2026-08-13T13:00:00Z")


def test_strategy_regularity_uses_future_events_bounded_controls_and_cegar() -> None:
    law = deepcopy(next(
        row for row in default_law_catalog()["candidates"]
        if row["law_id"] == "reinforcing-strategy-choice-durability"
    ))
    seed_events = {industry: stable_sha256({"seed": industry}) for industry in ("A", "B")}
    law.update({
        "law_id": "strategy-phenotype-fixture-durability",
        "version": "1", "origin": "strategy_phenotype_compiler",
        "created_at": "2025-01-01T00:00:00Z", "not_before": "2025-01-01T00:00:00Z",
        "generation_receipt": {
            "mechanism_phenotype_sha256": "a" * 64,
            "implementation_event_sha256s": list(seed_events.values()),
            "cohort_plan_sha256": "b" * 64, "cohort_query_sha256s": ["c" * 64],
        },
    })
    law["validation"]["minimum_transfer_environments"] = 2
    law["validation"]["minimum_meaningful_effect"] = 0.05
    law["cohort"]["counterexample_fields"] = ["industry_id"]

    def panel(effects: dict[str, float]) -> list[dict[str, object]]:
        dates = [
            "2024-03-31T00:00:00Z", "2024-06-30T00:00:00Z",
            "2024-09-30T00:00:00Z", "2025-06-30T00:00:00Z",
            "2025-12-31T00:00:00Z",
        ]
        rows = []
        for industry, effect in effects.items():
            for treated, count in ((True, 5), (False, 4)):
                for unit_index in range(count):
                    unit = f"{industry}-{'treated' if treated else 'control'}-{unit_index}"
                    event_sha = (
                        seed_events[industry] if treated and unit_index == 0 else
                        stable_sha256({"future_event": unit}) if treated else None
                    )
                    for period, observed_at in enumerate(dates):
                        rows.append({
                            "schema": "jaggedthoughts-causal-panel-row-v2",
                            "law_id": law["law_id"], "unit_id": unit,
                            "period_index": period, "treated_group": treated,
                            "treatment_period": 3 if treated else None,
                            "treatment_event_sha256": event_sha,
                            "treatment_event_sha256s": [event_sha] if event_sha else [],
                            "treatment_timing_status": (
                                "exact_adoption_event" if treated else "never_treated_as_of_panel"
                            ),
                            "treatment_occurred_at": (
                                "2024-12-01T00:00:00Z" if event_sha in seed_events.values()
                                else "2025-02-01T00:00:00Z" if treated else None
                            ),
                            "treatment_available_at": (
                                "2024-12-02T00:00:00Z" if event_sha in seed_events.values()
                                else "2025-02-02T00:00:00Z" if treated else None
                            ),
                            "control_observation_start_at": (
                                None if treated else "2024-01-01T00:00:00Z"
                            ),
                            "control_observation_end_at": (
                                None if treated else "2026-01-01T00:00:00Z"
                            ),
                            "outcome_metric_id": "earnings_durability", "outcome_unit": "score",
                            "outcome": period * 0.1 + (effect if treated and period >= 3 else 0.0),
                            "observed_at": observed_at, "available_at": observed_at,
                            "environment": {"industry_id": industry},
                            "observation_ids": [f"filing:{unit}:{period}"],
                            "source_refs": [f"filing:{unit}"],
                        })
        return rows

    supported = evaluate_difference_in_differences(
        law, panel({"A": 1.0, "B": 0.8}), generated_at="2026-01-02T00:00:00Z",
    )["strategy_regularity"]
    assert supported["status"] == "prospective_transfer_candidate"
    observed = supported["prospective_holdout"]["observed"]
    assert {key: observed[key] for key in (
        "independent_treated_units", "bounded_control_units",
        "transfer_environments", "group_time_cells",
    )} == {
        "independent_treated_units": 8, "bounded_control_units": 8,
        "transfer_environments": 2, "group_time_cells": 4,
    }
    assert observed["minimum_detectable_effect_at_declared_power"] <= 0.05
    assert not set(supported["prospective_holdout"]["independent_treatment_event_sha256s"]) & set(seed_events.values())

    challenged = evaluate_difference_in_differences(
        law, panel({"A": 1.0, "B": -1.0}), generated_at="2026-01-02T00:00:00Z",
    )["strategy_regularity"]
    assert challenged["status"] == "challenged_by_counterexample"
    assert challenged["refinement_proposals"][0]["condition"] == {
        "path": "industry_id", "operator": "ne", "value": "B",
    }


def test_strategy_cohort_search_does_not_infer_untreated_from_absence() -> None:
    payload = yaml.safe_load((EXAMPLE / "company_strategy_options.yaml").read_text(encoding="utf-8"))
    payload["options"][0]["implementation_event"] = {
        "id": "adoption", "event_kind": "adoption", "status_after": "underway",
        "occurred_at": "2026-06-01T00:00:00Z", "available_at": "2026-06-02T00:00:00Z",
        "timing_precision": "date", "source_refs": ["filing"],
    }
    payload["options"][0]["mechanism"] = {
        "action": "secure_supply", "economic_bridge": "downside_resilience",
        "object_id": "critical_input", "implementation_conditions": ["qualification succeeds"],
        "break_conditions": ["supplier fails"], "evidence_refs": ["filing"],
    }
    library = compile_strategy_move_library((compile_company_strategy_frontier(payload),))
    catalog = {
        "catalog_sha256": "a" * 64, "retrieved_at": "2026-08-12T00:00:00Z",
        "securities": [
            {"symbol": "ALPHA", "name": "Alpha", "entity_kind": "public_equity", "security_kind": "common_equity", "security_id": "public_equity:ALPHA", "industry": "Widgets", "market_cap": 100},
            {"symbol": "PEER", "name": "Peer", "entity_kind": "public_equity", "security_kind": "common_equity", "security_id": "public_equity:PEER", "industry": "Widgets", "market_cap": 90},
        ],
    }
    plan = compile_strategy_cohort_research_plan(library, catalog)
    assert plan["max_peers_per_family"] == 8
    assert plan["target_control_unit_count"] == 4
    assert plan["adaptive_expansion_cap"] == 25
    request = plan["requests"][0]
    strategy_laws = compile_strategy_law_candidates(library, plan)
    assert len(strategy_laws) == 1
    other_environment = {**plan["mechanism_environments"][0], "industry_id": "Other Widgets"}
    cross_industry_laws = compile_strategy_law_candidates(
        library, {**plan, "mechanism_environments": [*plan["mechanism_environments"], other_environment]},
    )
    assert len(cross_industry_laws) == 1
    assert cross_industry_laws[0]["generation_receipt"]["seed_industry_ids"] == [
        "Other Widgets", "Widgets",
    ]
    assert strategy_laws[0]["origin"] == "strategy_phenotype_compiler"
    assert strategy_laws[0]["not_before"] >= request["search_end_at"]
    assert strategy_laws[0]["estimator"]["treatment_id"].endswith(
        request["mechanism_phenotype_sha256"]
    )
    assert strategy_laws[0]["capital_authority"] is False
    raw = {
        "schema": "jaggedthoughts-strategy-cohort-research-result-v2",
        "request_sha256": request["request_sha256"], "peer_entity_id": "PEER",
        "mechanism_signature_sha256": request["mechanism_signature_sha256"],
        "mechanism_phenotype_sha256": request["mechanism_phenotype_sha256"],
        "classification": "no_family_adoption_found", "assessed_at": "2026-08-13T00:00:00Z",
        "coverage": {"sec_filings_searched": True, "issuer_materials_searched": True, "search_start_at": request["search_start_at"], "search_end_at": request["search_end_at"]},
        "events": [], "rationale": "No equivalent adoption was located in the bounded search.", "residuals": ["Private implementation may be undisclosed."],
        "sources": [
            {"url": "https://example.test/10-k", "source_kind": "filing", "published_at": "2026-02-01", "supports": ["filing search"]},
            {"url": "https://example.test/investors", "source_kind": "issuer", "published_at": "2026-05-01", "supports": ["issuer search"]},
        ],
    }
    result = compile_strategy_cohort_research_result(raw, request)
    assert result["panel_role"] == "not_yet_treated_candidate"
    assert result["classification_authority"] == "subscription_agent_proposal"

    exact_move = next(
        row for row in library["moves"]
        if row["causal_panel_status"] == "treatment_event_ready"
    )
    bridge_move = {
        **exact_move,
        "entity_id": "BRIDGE", "move_sha256": "e" * 64,
        "evidence_epoch": "2026-08-12T12:00:00Z",
        "claim_status": "supported",
        "causal_panel_status": "requires_adoption_event", "implementation_event": None,
    }
    transfer_catalog = {
        **catalog,
        "securities": [*catalog["securities"],
            {"symbol": "BRIDGE", "name": "Bridge", "entity_kind": "public_equity", "security_kind": "common_equity", "security_id": "public_equity:BRIDGE", "industry": "Gadgets", "market_cap": 50},
            {"symbol": "OTHER", "name": "Other", "entity_kind": "public_equity", "security_kind": "common_equity", "security_id": "public_equity:OTHER", "industry": "Gadgets", "market_cap": 40},
        ],
    }
    transfer_plan = compile_strategy_cohort_research_plan(
        {**library, "moves": [*library["moves"], bridge_move]}, transfer_catalog,
        max_transfer_environments=1, transfer_peers_per_environment=2,
    )
    transfer_requests = [
        row for row in transfer_plan["requests"]
        if row.get("search_role") == "cross_environment_transfer_discovery"
    ]
    blind_requests = [
        row for row in transfer_plan["requests"]
        if row.get("search_role") == "law_blind_environment_probe"
    ]
    assert len(blind_requests) == 1
    assert {
        row["peer_entity_id"] for row in [*blind_requests, *transfer_requests]
    } == {"BRIDGE", "OTHER"}
    assert {row["industry_id"] for row in transfer_requests} == {"Gadgets"}
    assert transfer_plan["transfer_environment_search_count"] == 1
    assert transfer_plan["transfer_request_count"] == 1
    assert all(row["created_at"] >= bridge_move["evidence_epoch"] for row in transfer_requests)
    anchor_erased = compile_strategy_cohort_research_plan(
        library, transfer_catalog,
        max_transfer_environments=1, transfer_peers_per_environment=2,
    )
    assert anchor_erased["law_blind_environment_probes"] == (
        transfer_plan["law_blind_environment_probes"]
    )

    commitment = {
        **raw,
        "classification": "family_adoption_only",
        "events": [{
            "event_id": "signed-deal", "description": "Signed but not closed.",
            "occurred_at": "2026-07-01T00:00:00Z",
            "available_at": "2026-07-01T00:00:00Z",
            "implementation_mode": "acquisition", "implementation_state": "committed",
            "focal_relation": {
                "strategy_form": "same", "addressed_actor_profile": "same",
                "implementation_mode": "same", "operating_object_scope": "same",
            },
            "source_urls": ["https://example.test/10-k"],
        }],
    }
    assert compile_strategy_cohort_research_result(commitment, request)["panel_role"] == "related_treatment_excluded"
    with pytest.raises(ValueError, match="operational exact-phenotype"):
        compile_strategy_cohort_research_result(
            {**commitment, "classification": "phenotype_adoption_found"}, request,
        )
    projection = compile_strategy_phenotype_projection_frontier(
        plan, (result,),
    )
    assert projection["projection_count"] == 16
    assert projection["certificate"]["scope_closed"] is True
    assert projection["certificate"]["decision_closed"] is False

    later_catalog = {**catalog, "retrieved_at": "2026-08-14T00:00:00Z"}
    later_plan = compile_strategy_cohort_research_plan(library, later_catalog)
    later_request = later_plan["requests"][0]
    assert later_request["request_sha256"] != request["request_sha256"]
    assert later_request["query_sha256"] == request["query_sha256"]
    recovered, chain = resolve_strategy_cohort_results(
        later_plan, (result,), historical_requests=(request,),
    )
    assert recovered[later_request["request_sha256"]]["result_sha256"] == result["result_sha256"]
    assert chain["recovered_compatible_result_count"] == 1

    changed = {**later_request, "mechanism_phenotype_sha256": "f" * 64}
    changed.pop("request_sha256")
    changed["query_sha256"] = strategy_cohort_query_identity(changed)["query_sha256"]
    changed["request_sha256"] = stable_sha256(changed)
    changed_plan_body = {**later_plan, "requests": [changed]}
    changed_plan_body.pop("plan_sha256")
    changed_plan = {**changed_plan_body, "plan_sha256": stable_sha256(changed_plan_body)}
    rejected, rejection_chain = resolve_strategy_cohort_results(
        changed_plan, (result,), historical_requests=(request,),
    )
    assert rejected == {}
    assert rejection_chain["rejected_changed_identity_count"] == 1


def test_golden_store_compresses_large_leaf_bodies(tmp_path: Path) -> None:
    store = GoldenStore(tmp_path / "compressed.sqlite3")
    leaf = GoldenLeaf(
        owner="paper", object_kind="large_packet", object_id="one", epoch="v1",
        occurred_at="2026-01-01T00:00:00Z", available_at="2026-01-01T00:00:00Z",
        payload={"schema": "large-packet-v1", "rows": ["repeatable"] * 20_000},
        source_refs=("fixture:large-packet",),
    )
    store.append_leaf(leaf)
    with sqlite3.connect(store.path) as connection:
        storage_type, stored_bytes = connection.execute(
            "SELECT typeof(body_json), length(body_json) FROM golden_leaf"
        ).fetchone()
    assert storage_type == "blob" and stored_bytes < len(json.dumps(leaf.to_dict())) / 2
    assert store.get_leaf(leaf.leaf_sha256) == leaf.to_dict()
    assert store.get_leaves((leaf.leaf_sha256, leaf.leaf_sha256)) == {
        leaf.leaf_sha256: leaf.to_dict()
    }
    assert store.verify()["ok"] is True


def test_golden_store_tie_breaks_heads_by_append_order(tmp_path: Path) -> None:
    store = GoldenStore(tmp_path / "tied-head.sqlite3")
    common = {
        "owner": "paper", "object_kind": "portfolio", "object_id": "one",
        "occurred_at": "2026-01-01T00:00:00Z",
        "available_at": "2026-01-02T00:00:00Z",
        "source_refs": ("fixture:tied-head",),
    }
    first = GoldenLeaf(epoch="v1", payload={"schema": "portfolio-v1", "version": 1}, **common)
    second = GoldenLeaf(epoch="v2", payload={"schema": "portfolio-v1", "version": 2}, **common)
    store.append_leaf(first)
    store.append_leaf(second)

    assert store.head("paper", "portfolio", "one")["leaf_sha256"] == second.leaf_sha256
    assert store.verify()["ok"] is True


def test_reference_decision_settlement_and_lineage(tmp_path: Path) -> None:
    decision = compile_investment_profile_file(EXAMPLE / "value_quality_play.yaml")
    valuation = decision["valuation_envelope"]
    frontier = valuation["expectations_frontier"]

    assert decision == compile_investment_profile_file(EXAMPLE / "value_quality_play.yaml")
    assert decision["point_in_time_snapshot"]["excluded_future_count"] == 1
    assert {row["entity_id"] for row in decision["point_in_time_snapshot"]["observations"]} == {
        decision["entity"]["entity_id"], decision["benchmark"]["entity_id"],
    }
    assert len(valuation["results"]) == 17
    assert len(valuation["failures"]) == 8
    assert {tuple(row["scenario_ids"]) for row in valuation["results"]} >= {
        ("base_compounding_cash_flow",),
        ("concentration_stress_cash_flow",),
    }
    assert frontier["scope_closed"] is True
    assert frontier["implied_growth_curve"] and frontier["implied_return_curve"]
    hurdle_prices = decision["hurdle_price_frontier"]
    assert hurdle_prices["required_total_return"] == pytest.approx(0.10)
    assert hurdle_prices["robust_maximum_price"] < hurdle_prices["current_price"] < hurdle_prices["optimistic_maximum_price"]
    assert decision["initial_state"]["firm"]["expected_excess_return"] == pytest.approx(
        valuation["summary"]["price_implied_excess_return"]
    )
    assert decision["policy_selection"]["expression"] == "act::watch"
    assert decision["policy_frontier"]["canonical_frontier_program_ids"]
    assert any(
        row["source_program_id"] != row["canonical_program_id"]
        for row in decision["policy_frontier"]["replacements"]
    )
    action_regions = decision["policy_action_regions"]
    assert action_regions["total_over_condition_space"] is True
    assert action_regions["deterministic_over_condition_space"] is True
    assert action_regions["current_state_action_ids"] == [decision["summary"]["selected_action_id"]]

    store = GoldenStore(tmp_path / "capital.sqlite")
    leaves = record_investment_decision(store, decision)
    decision_leaf = store.get_leaf(leaves["decision"])
    assert store.identity(
        decision_leaf["owner"], decision_leaf["object_kind"],
        decision_leaf["object_id"], decision_leaf["epoch"],
    ) == decision_leaf
    assert store.verify() == {
        "schema": "jaggedthoughts-golden-store-verification-v1",
        "path": str((tmp_path / "capital.sqlite").resolve()),
        "leaf_count": 9,
        "edge_count": 16,
        "ok": True,
        "errors": [],
    }
    lineage = store.lineage(leaves["decision"])
    assert {row["object_kind"] for row in lineage["nodes"]} >= {
        "paper_decision", "valuation_envelope", "underwriting_case",
        "recursive_policy_frontier",
    }
    assembly = compile_portfolio_assembly(
        portfolio_id="reference-book-assembly",
        decisions=(decision,),
        constraints=PortfolioConstraints("reference", 0.9, 0.15, 0.2, 0.3, 0.15),
        objectives=(
            PortfolioObjective("return", "expected_excess_return", "maximize", 0.1, 0.8),
            PortfolioObjective("risk", "weighted_downside", "minimize", 0.3, 0.2),
        ),
    )
    record_portfolio_assembly(store, assembly=assembly, decisions=(decision,))
    assert assembly["feasibility_certificate"]["feasible_assignment_count"] == 2
    envelope = assembly["continuous_allocation_envelope"]
    assert envelope["scope_closed"] is True and envelope["capital_authority"] is False
    assert envelope["candidate_capacity"][0]["maximum_feasible_weight"] == 0
    assert store.verify()["leaf_count"] == 10

    outcome = OutcomeSnapshot.from_dict({
        "schema": "jaggedthoughts-investment-outcome-v1",
        "decision_record_sha256": decision["decision_record_sha256"],
        "observed_at": "2027-06-30T20:00:00Z",
        "available_at": "2027-06-30T21:00:00Z",
        "prices": {"ALPHA": 58, "VTI": 324},
        "source_refs": ["sealed-2027q2-price-export"],
    })
    scorecard = settle_paper_decision(decision, outcome).to_dict()
    assert scorecard["paper_return"] == pytest.approx(0.04)
    assert scorecard["net_excess_return"] == pytest.approx(-0.04)
    record_investment_settlement(
        store, decision=decision, outcome=outcome.to_dict(), scorecard=scorecard
    )
    assert store.verify()["leaf_count"] == 12

    candidate = PriceActionCandidate.from_dict(json.loads(
        (EXAMPLE / "price_action" / "lagrangian_candidate.json").read_text()
    ))
    baseline = PriceActionCandidate.from_dict(json.loads(
        (EXAMPLE / "price_action" / "historical_mean_control.json").read_text()
    ))
    price_outcome = json.loads((EXAMPLE / "price_action" / "outcome.json").read_text())
    evaluation = evaluate_price_action_candidate(
        candidate, price_outcome, baselines=(baseline,), transaction_cost_bps=10
    )
    assert evaluation["screen_pass"] is True

    tournament = compile_world_model_tournament_profile(EXAMPLE / "world_model_tournament.yaml")
    assert tournament["inference_block_count"] == 8
    assert tournament["evaluation_matrix"]["complete_matrix"] is True
    assert tournament["survivor_model_ids"] == ["strategy-transition"]
    assert tournament["model_metrics"][1]["economic_backtest"]["information_ratio"] > 1
    assert tournament["capital_authority"] is False
    tournament_leaves = record_world_model_tournament(store, tournament)
    assert set(tournament_leaves["model_tracks"]) == {
        "historical-control@1", "strategy-transition@1",
    }
    assert store.verify()["leaf_count"] == 23


def test_valuation_assumption_identity_is_global() -> None:
    rows = (
        ValuationAssumption("price", "MarketPrice", 50, "currency/share", ("memo",)),
        ValuationAssumption("earnings", "OwnerEarnings", 7, "currency/year", ("memo",)),
        ValuationAssumption("cash", "ExcessNetCash", 5, "currency", ("memo",)),
        ValuationAssumption("shares", "Shares", 2, "shares", ("memo",)),
        ValuationAssumption("rf", "RiskFreeRate", 0.04, "decimal", ("memo",)),
        ValuationAssumption("erp", "EquityRiskPremium", 0.04, "decimal", ("memo",)),
        ValuationAssumption("beta", "EquityBeta", 1, "multiple", ("memo",)),
        ValuationAssumption("growth", "ForecastGrowth", 0.03, "decimal", ("memo",)),
        ValuationAssumption("terminal", "TerminalGrowth", 0.02, "decimal", ("memo",)),
        ValuationAssumption("horizon", "Horizon", 10, "years", ("memo",)),
    )
    envelope = compile_valuation_envelope(
        envelope_id="ALPHA@epoch",
        entity_id="ALPHA",
        evidence_epoch="epoch",
        grammar_id="valuation",
        grammar_version="1",
        assumptions=rows,
    )
    assert envelope.expectations_frontier.scope_closed is True
    assert all(result.source_refs == ("memo",) for result in envelope.results)

    with pytest.raises(ValueError, match="nonempty and unique"):
        compile_valuation_envelope(
            envelope_id="ALPHA@epoch",
            entity_id="ALPHA",
            evidence_epoch="epoch",
            grammar_id="valuation",
            grammar_version="1",
            assumptions=(*rows, ValuationAssumption(
                "growth", "DiscountRate", 0.1, "decimal", ("memo",)
            )),
        )


def test_portfolio_assembly_keeps_capital_constraints_outside_entity_grammar(tmp_path: Path) -> None:
    alpha = compile_investment_profile_file(EXAMPLE / "value_quality_play.yaml")
    beta = deepcopy(alpha)
    beta.pop("decision_record_sha256")
    beta["decision_id"] = "beta-value-quality-2026q2"
    beta["entity"] = {**beta["entity"], "entity_id": "BETA", "name": "Beta Systems"}
    beta["initial_state"]["firm"]["expected_excess_return"] = 0.12
    beta["initial_state"]["firm"]["downside_risk"] = 0.25
    beta["position_proposal"] = {
        **beta["position_proposal"],
        "decision_id": beta["decision_id"],
        "entity_id": "BETA",
        "current_weight": 0.0,
        "target_weight": 0.10,
        "estimated_cost": 15.0,
    }
    beta["decision_record_sha256"] = stable_sha256(beta)

    assembly = compile_portfolio_assembly(
        portfolio_id="reference-multi-entity-book",
        decisions=(alpha, beta),
        constraints=PortfolioConstraints(
            "reference-constraints", 0.8, 0.15, 0.15, 0.25, 0.15
        ),
        objectives=(
            PortfolioObjective("return", "expected_excess_return", "maximize", 0.1, 0.7),
            PortfolioObjective("downside", "weighted_downside", "minimize", 0.3, 0.2),
            PortfolioObjective("turnover", "turnover", "minimize", 0.2, 0.1),
        ),
    )
    assert assembly["scope_closed"] is True
    assert assembly["combination_count"] == 4
    assert assembly["selected_target_weights"] == {"ALPHA": 0.0, "BETA": 0.0}
    assert assembly["selected_metrics"]["weighted_downside"] <= 0.25
    assert assembly["nominal_selected_target_weights"] == {"ALPHA": 0.0, "BETA": 0.1}
    assert assembly["selection_tradeoff"]["allocation_changed_by_mechanism_weight"] is True
    mechanism_regions = assembly["mechanism_weight_regions"]["certificate"]
    assert len(mechanism_regions["strictly_supported_alternative_ids"]) == 2
    assert assembly["candidates"][1]["robust_bounds"] == {
        "expected_excess_return_floor": pytest.approx(0.05998127900613593),
        "downside_risk_ceiling": 0.25,
        "thesis_confidence_floor": 0.61,
    }
    objectives = (
        PortfolioObjective("return", "expected_excess_return", "maximize", 0.1, 1.0),
    )
    position_capped = compile_portfolio_assembly(
        portfolio_id="position-capped", decisions=(alpha, beta),
        constraints=PortfolioConstraints(
            "position-cap", 0.8, 0.15, 0.15, 0.25, 0.15,
            max_positions=1, min_position_weight=0.05,
        ),
        objectives=objectives,
    )
    beta_check = next(row for row in position_capped["feasibility_certificate"]["acceptance_checks"] if row["entity_id"] == "BETA")
    assert beta_check["blocking_constraint_ids"] == ["max_positions"]
    minimum_blocked = compile_portfolio_assembly(
        portfolio_id="minimum-blocked", decisions=(alpha, beta),
        constraints=PortfolioConstraints(
            "position-minimum", 0.8, 0.15, 0.15, 0.25, 0.15,
            max_positions=2, min_position_weight=0.12,
        ),
        objectives=objectives,
    )
    beta_check = next(row for row in minimum_blocked["feasibility_certificate"]["acceptance_checks"] if row["entity_id"] == "BETA")
    assert beta_check["blocking_constraint_ids"] == ["min_position_weight:BETA"]

    exposure_capped = compile_portfolio_assembly(
        portfolio_id="exposure-capped", decisions=(alpha, beta),
        constraints=PortfolioConstraints(
            "exposure-cap", 0.8, 0.15, 0.15, 0.25, 0.15,
        ),
        objectives=objectives,
        exposure_bands=(PortfolioExposureBand(
            "beta-factor", None, 0.05, 0.0,
            (("ALPHA", 0.0), ("BETA", 1.0)), ("factor-analysis:fixture",),
        ),),
    )
    beta_check = next(row for row in exposure_capped["feasibility_certificate"]["acceptance_checks"] if row["entity_id"] == "BETA")
    assert beta_check["blocking_constraint_ids"] == ["exposure_max:beta-factor"]
    assert beta_check["exposure_activation_ranges"][0]["maximum_must_be_at_least"] == 0.10
    exposure_range = exposure_capped["continuous_allocation_envelope"]["exposure_ranges"][0]
    assert exposure_range["maximum_attainable"] == 0.05
    assert "exposure_max:beta-factor" in exposure_range["maximum_witness"]["binding_constraint_ids"]

    results = tmp_path / "watchlists" / "results"
    results.mkdir(parents=True)
    analyses = []
    for entity_id, factor_beta in (("ALPHA", 1.05), ("BETA", 0.85)):
        analyses.append({
            "entity_id": entity_id,
            "analysis": {
                "schema": "jaggedthoughts-factor-analysis-v1", "as_of": "2026-06-01T00:00:00Z",
                "available_at": "2026-06-01T00:00:00Z", "analysis_sha256": entity_id.lower() * 64,
                "coefficients": {"betas": {"market": factor_beta}},
            },
        })
    (results / "funds.json").write_text(json.dumps({
        "watchlist_sha256": "f" * 64, "candidates": analyses,
    }), encoding="utf-8")
    derived = _compile_portfolio_exposure_bands(tmp_path, [{
        "id": "market-beta", "factor_id": "market", "minimum": 0.5, "maximum": 1.2,
    }], (alpha, beta))
    assert dict(derived[0].coefficients) == {"ALPHA": 1.05, "BETA": 0.85}
    assert derived[0].source_refs[0].startswith("factor-analysis:")


def test_patient_capital_requires_a_superior_after_cost_replacement() -> None:
    def candidate(entity: str, current: float, target: float, expected: float) -> PortfolioCandidate:
        return PortfolioCandidate(
            f"{entity}-decision", stable_sha256(entity), entity, current, target,
            expected, 0.2, 0.8, 0.0001,
            (PortfolioMechanismScenario("base", "b" * 64, expected, 0.2, 0.8),),
        )

    incumbent = candidate("ALPHA", 0.10, 0.0, 0.05)
    challenger = candidate("BETA", 0.0, 0.10, 0.10)
    policy = PatientCapitalPolicy("patient", 0.04, 0.0, 0.35)
    qualified = compile_patient_rotation_review(
        (incumbent, challenger), {"ALPHA": 0.0, "BETA": 0.10}, policy,
    )
    assert qualified["status"] == "qualified_rotation"
    assert qualified["replacement_flows"][0]["matched_weight"] == pytest.approx(0.10)

    muted = candidate("BETA", 0.0, 0.10, 0.08)
    blocked = compile_patient_rotation_review(
        (incumbent, muted), {"ALPHA": 0.0, "BETA": 0.10}, policy,
    )
    assert blocked["status"] == "blocked_rotation"
    assert blocked["blockers"][0]["minimum_return_edge_must_be_at_most"] == pytest.approx(0.028)


def test_factor_decomposition_reuses_shared_ols_and_funnel_is_guarded() -> None:
    returns = {"MKT": [], "VAL": [], "FUND": []}
    for index in range(140):
        market = 0.001 * ((index % 7) - 3)
        value = 0.0007 * ((index % 11) - 5)
        returns["MKT"].append(market)
        returns["VAL"].append(value)
        returns["FUND"].append(0.0001 + 1.2 * market + 0.5 * value)
    points = []
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for entity, series in returns.items():
        price = 100.0
        points.append(PricePoint(entity, start.isoformat(), "2026-01-01T00:00:00Z", price, f"{entity}:0", "fixture"))
        for index, value in enumerate(series, 1):
            price *= 1 + value
            observed = start + timedelta(days=index)
            points.append(PricePoint(entity, observed.isoformat(), "2026-01-01T00:00:00Z", price, f"{entity}:{index}", "fixture"))
    points = [row for row in points if row.observation_id != "VAL:70"]
    result = analyze_factor_exposure(
        analysis_id="synthetic-fund", candidate_entity_id="FUND",
        factors=(FactorDefinition("market", "MKT"), FactorDefinition("value", "VAL")),
        price_points=points, as_of="2026-01-02T00:00:00Z", min_observations=100,
    )
    assert result["coefficients"]["betas"] == pytest.approx({"market": 1.2, "value": 0.5})
    assert result["fit"]["leave_one_out_r2"] > 0.99
    assert result["temporal_alignment"]["aligned_return_count"] == 138
    assert result["historical"]["residual_alpha_uncertainty"]["annualized_interval"][0] == pytest.approx(
        (1.0001 ** 252) - 1, abs=1e-10,
    )
    assert OPPORTUNITY_FUNNEL.next_state("draft", "activate_paper") == "active_paper"
    assert OPPORTUNITY_FUNNEL.next_state("draft", "allocate_paper") is None


def test_retrieval_only_refresh_preserves_prior_observation_epoch(tmp_path: Path) -> None:
    (tmp_path / "prices.csv").write_text("date,close\n2026-01-02,100\n", encoding="utf-8")
    manifest = tmp_path / "sources.yaml"
    manifest.write_text(json.dumps({
        "schema": "jaggedthoughts-public-source-manifest-v1",
        "as_of": "now",
        "sources": [{
            "id": "prices", "adapter": "local_csv", "path": "prices.csv",
            "mappings": [{
                "entity_id": "FUND", "metric_id": "price", "unit": "USD/share",
                "value_column": "close", "observed_at_column": "date",
            }],
        }],
    }), encoding="utf-8")
    consume_public_sources(
        manifest, workspace=tmp_path, retrieved_at="2026-01-03T00:00:00Z",
    )
    second = consume_public_sources(
        manifest, workspace=tmp_path, retrieved_at="2026-01-04T00:00:00Z",
    )
    assert second["observation_count"] == 1
    (tmp_path / "prices.csv").write_text("date,close\n2026-01-02,101\n", encoding="utf-8")
    third = consume_public_sources(
        manifest, workspace=tmp_path, retrieved_at="2026-01-05T00:00:00Z",
    )
    assert third["observation_count"] == 2
    rows = (tmp_path / "data" / "observations.csv").read_text(encoding="utf-8").splitlines()
    assert len(rows) == 3


def test_discovery_identity_schedule_and_issuer_payload(tmp_path: Path) -> None:
    props = {
        "containersByNameMap": {"default": {"dataPointsByNameMap": {
            "priceEarnings": {"value": 18.5, "asOfDate": 20260807},
        }}},
    }
    encoded = json.dumps(props).replace('"', "&quot;")
    html = (
        '<walrus-render-on-client componentkey="PortfolioCharacteristicsV3" '
        f'componentprops="{encoded}">'
    ).encode()
    assert _ishares_characteristics_payload(html) == props
    vanguard = (
        '<script id="fundProfileData" type="application/json">'
        '{"fundProfile":{"ticker":"VOE","expenseRatio":"0.0500"}}'
        '</script>'
    ).encode()
    assert _vanguard_profile_payload(vanguard)["fundProfile"]["ticker"] == "VOE"
    valuation = _fund_valuation(
        evidence=[
            {"metric_id": "portfolio_price_to_earnings", "value": 20, "source_ref": "issuer"},
            {"metric_id": "portfolio_price_to_book", "value": 2, "source_ref": "issuer"},
            {"metric_id": "expense_ratio", "value": 0.001, "source_ref": "issuer"},
        ],
        required_return=0.08,
        payout_ratio_assumptions=[0.5],
    )
    assert valuation is not None
    assert valuation["earnings_yield"] == pytest.approx(0.05)
    assert valuation["book_to_price"] == pytest.approx(0.5)

    fund = _compile_fund(
        row={
            "entity_id": "FUND", "name": "Fund", "screen_status": "qualified",
            "valuation_claim_allowed": True,
            "valuation": {
                "earnings_power_margin": 0.2, "implied_growth_median": 0.01,
                "source_refs": ["issuer"],
            },
            "analysis": {
                "assumption_implied": {"return_without_residual_alpha": 0.08},
                "historical": {"maximum_drawdown": -0.2, "residual_alpha_annualized": 0.0},
                "fit": {"leave_one_out_r2": 0.5}, "source_refs": ["prices"],
            },
            "investment_potential": {"score": 0.8, "component_scores": {}},
        },
        watchlist_id="funds", as_of="2026-08-10T12:00:00Z",
        config={"criteria": [], "minimum_score": 0.5}, input_leaf=None,
    )
    assert fund["screen_status"] == "blocked_watchlist_lineage"
    assert fund["next_activation"] == "rebuild_current_watchlist"

    schedule = discovery_schedule_status(
        policy={"enabled": True, "cadence_hours": 24},
        latest_run={"completed_at": "2026-08-09T12:00:00Z"},
        now="2026-08-10T12:00:01Z",
    )
    assert schedule["due"] is True
    candidate_body = {
        "schema": "jaggedthoughts-discovery-candidate-v1",
        "candidate_id": "equity:ALPHA", "entity_id": "ALPHA",
        "entity_kind": "public_equity", "name": "Alpha",
        "as_of": "2026-08-10T12:00:00Z", "analysis_kind": "test",
        "screen_status": "monitor", "rank_score": 0.4, "rank": 1,
        "score_components": {}, "criteria": [], "metrics": {},
        "source_refs": ["fixture"], "input_golden_leaves": [],
        "next_activation": "monitor_next_source_epoch",
    }
    candidate = {**candidate_body, "candidate_sha256": stable_sha256(candidate_body)}
    run_body = {
        "schema": "jaggedthoughts-discovery-run-v1", "run_id": "discovery-test",
        "workspace_name": "JaggedThoughts", "owner": "paper",
        "as_of": "2026-08-10T12:00:00Z", "completed_at": "2026-08-10T12:00:01Z",
        "source_run_sha256": "source", "policy_sha256": "policy",
        "authority": "analysis_and_research_request_only", "enumeration": {},
        "frontier_closure": {"scope_closed": True}, "qualified_count": 0,
        "candidate_count": 1, "candidates": [candidate], "activation_points": [],
    }
    run = {**run_body, "run_sha256": stable_sha256(run_body)}
    store = GoldenStore(tmp_path / "discovery.sqlite")
    receipt = record_discovery_run(store, owner="paper", run=run)
    assert set(receipt["candidate_leaves"]) == {"equity:ALPHA"}
    later_body = {
        **run_body, "run_id": "discovery-test-later",
        "completed_at": "2026-08-10T12:00:02Z",
    }
    later = {**later_body, "run_sha256": stable_sha256(later_body)}
    later_receipt = record_discovery_run(store, owner="paper", run=later)
    assert later_receipt["candidate_leaves"] == receipt["candidate_leaves"]
    assert store.verify()["ok"] is True


def test_research_learning_keeps_pending_requests_censored() -> None:
    requests = [
        {
            "request_id": "research:ALPHA", "job_id": "job-alpha",
            "candidate_leaf": "a" * 64, "entity_id": "ALPHA",
            "entity_kind": "public_equity", "created_at": "2026-08-09T00:00:00Z",
            "lifecycle_stage": "settled", "dossier_path": "alpha.json",
            "decision_id": "alpha-paper",
            "settlement_scorecard": {
                "net_excess_return": 0.08,
                "incremental_return_vs_no_action": 0.06,
            },
        },
        {
            "request_id": "research:BETA", "job_id": "job-beta",
            "candidate_leaf": "b" * 64, "entity_id": "BETA",
            "entity_kind": "public_equity", "created_at": "2026-08-10T00:00:00Z",
            "lifecycle_stage": "evidence_ready", "dossier_path": None,
        },
    ]
    jobs = [
        {"work_id": "job-alpha", "payload": {"acquisition_priority": 0.8, "cost": {"research_minutes": 40}}},
        {"work_id": "job-beta", "payload": {"acquisition_priority": 0.6, "cost": {"research_minutes": 40}}},
    ]
    learning = compile_research_learning(
        research_requests=requests, queue_jobs=jobs,
        generated_at="2026-08-10T01:00:00Z", minimum_settled_pairs=2,
    )
    assert learning["counts"] == {
        "requests": 2, "dossiers": 1, "drafts": 1,
        "paper_activations": 1, "settled_score_pairs": 1,
    }
    assert learning["calibration_gate"]["policy_refit_allowed"] is False
    assert learning["rows"][1]["paper_settled"] is False


def test_economic_question_policy_winner_changes_only_operational_routing() -> None:
    assigned = [
        {"entity_kind": "public_equity", "candidate_leaf": f"{index:064x}"}
        for index in range(1, 200)
    ]
    assign_research_question_policies(
        assigned, source_run_ids=("run",), completed_at="2025-08-10T00:00:00Z",
    )
    by_arm = {
        arm: [row for row in assigned
              if row["research_policy_assignment"]["arm_id"] == arm][:5]
        for arm in ("coverage_first", "disagreement_first")
    }
    requests = []
    for arm, rows in by_arm.items():
        for index, row in enumerate(rows):
            assignment = row["research_policy_assignment"]
            requests.append({
                "request_id": f"research:{arm}:{index}", "entity_id": f"E:{arm}:{index}",
                "entity_kind": "public_equity", "created_at": "2025-08-10T00:00:00Z",
                "lifecycle_stage": "settled", "dossier_path": f"{arm}-{index}.json",
                "research_policy_assignment": assignment,
                "settlement_scorecard": {
                    "observed_at": "2026-08-10T00:00:00Z",
                    "incremental_return_vs_no_action": (
                        0.05 if arm == "disagreement_first" else 0.0
                    )
                },
            })
    learning = compile_research_learning(
        research_requests=requests, queue_jobs=[], generated_at="2026-08-11T00:00:00Z",
        minimum_question_policy_units_per_arm=5,
    )
    decision = learning["research_question_policy_experiment"]["routing_decision"]
    assert decision["recommended_arm"] == "disagreement_first"
    assert decision["routing_change_allowed"] is True

    selected = [
        {"entity_kind": "public_equity", "candidate_leaf": f"{rank + 500:064x}"}
        for rank in range(20)
    ]
    assign_research_question_policies(
        selected, source_run_ids=("next",), completed_at="2026-08-12T00:00:00Z",
        routing_decision=decision,
    )
    assert {
        row["research_policy_assignment"]["routing_mode"] for row in selected
    } == {"balanced_audit"}

    credit = compile_learning_credit_assignment(
        research_learning=learning, closed_book={}, institutional_learning={},
        fund_sleeve_comparison={}, portfolio_policy={},
    )
    selected = [
        {"entity_kind": "public_equity", "candidate_leaf": f"{rank + 650:064x}"}
        for rank in range(20)
    ]
    assign_research_question_policies(
        selected, source_run_ids=("next",), completed_at="2026-08-12T00:00:00Z",
        routing_decision=decision, learning_credit_assignment=credit,
        current_research_learning=learning,
    )
    assignments = [row["research_policy_assignment"] for row in selected]
    audit = [row for row in assignments if row["eligible"]]
    operational = [row for row in assignments if not row["eligible"]]
    assert {row["arm_id"] for row in audit} == {"coverage_first", "disagreement_first"}
    assert {row["arm_id"] for row in operational} == {"disagreement_first"}
    assert audit and operational

    stale = [
        {"entity_kind": "public_equity", "candidate_leaf": f"{rank + 800:064x}"}
        for rank in range(20)
    ]
    newer_body = dict(learning)
    newer_body.pop("learning_sha256")
    newer_body["generated_at"] = "2026-08-13T00:00:00Z"
    newer_learning = {
        **newer_body, "learning_sha256": stable_sha256(newer_body),
    }
    assign_research_question_policies(
        stale, source_run_ids=("later",), completed_at="2026-08-13T00:00:00Z",
        routing_decision=decision, learning_credit_assignment=credit,
        current_research_learning=newer_learning,
    )
    assert {
        row["research_policy_assignment"]["routing_mode"] for row in stale
    } == {"balanced_audit"}


def test_material_source_change_reopens_only_the_subscribed_dossier(tmp_path: Path) -> None:
    workspace = {
        "schema": "jaggedthoughts-investment-workspace-v1",
        "owner": "paper",
        "source_manifest": "sources.yaml",
        "golden_store": "state/golden_store.sqlite3",
    }
    (tmp_path / "workspace.yaml").write_text(yaml.safe_dump(workspace), encoding="utf-8")
    (tmp_path / "sources.yaml").write_text(yaml.safe_dump({
        "schema": "jaggedthoughts-public-source-manifest-v1",
        "sources": [{
            "id": "sec_alpha_companyfacts", "adapter": "sec_companyfacts",
            "enabled": True, "entity_id": "ALPHA",
        }, {
            "id": "sec_alpha_submissions", "adapter": "sec_submissions",
            "enabled": True, "entity_id": "ALPHA",
        }],
    }), encoding="utf-8")
    (tmp_path / "data").mkdir()
    baseline = {
        "source_id": "sec_alpha_companyfacts", "adapter": "sec_companyfacts",
        "canonical_url": "https://data.sec.gov/alpha.json",
        "content_sha256": "a" * 64, "receipt_sha256": "b" * 64,
        "retrieved_at": "2026-08-10T00:00:00Z", "raw_path": "sources/alpha-a.json",
    }
    (tmp_path / "data" / "latest_source_run.json").write_text(json.dumps({
        "source_receipts": [baseline],
    }), encoding="utf-8")
    store = GoldenStore(tmp_path / "state" / "golden_store.sqlite3")
    candidate = GoldenLeaf(
        owner="paper", object_kind="discovery_candidate", object_id="equity:ALPHA",
        epoch="candidate", occurred_at="2026-08-10T00:00:00Z",
        available_at="2026-08-10T00:00:00Z",
        payload={
            "schema": "jaggedthoughts-discovery-candidate-v1",
            "entity_id": "ALPHA", "candidate_sha256": "c" * 64,
        },
        source_refs=("fixture",),
    )
    store.append_bundle((candidate,))
    dossier_payload = {
        "schema": "jaggedthoughts-candidate-research-dossier-v1",
        "entity_id": "ALPHA", "candidate_leaf": candidate.leaf_sha256,
        "dossier_sha256": "d" * 64,
        "decisive_observation": {"observation": "filing delta"},
        "falsifiers": [{"condition": "cash conversion falls"}],
    }
    dossier = GoldenLeaf(
        owner="paper", object_kind="candidate_research_dossier",
        object_id="research:ALPHA", epoch="dossier",
        occurred_at="2026-08-10T00:01:00Z", available_at="2026-08-10T00:01:00Z",
        payload=dossier_payload, source_refs=("fixture",),
    )
    store.append_bundle((dossier,))
    subscription = record_monitor_subscription(
        store, root=tmp_path, owner="paper", dossier_leaf=dossier.leaf_sha256,
        dossier=dossier_payload, subscribed_at="2026-08-10T00:02:00Z",
    )
    coverage = candidate_research_coverage(
        store, owner="paper", candidate_leaf=candidate.leaf_sha256,
        current_receipts={"sec_alpha_companyfacts": baseline},
        required_source_ids=("sec_alpha_companyfacts", "sec_alpha_submissions"),
    )
    assert coverage["covered"] is True
    assert coverage["source_checks"][1]["status"] == "dormant_until_first_receipt"
    first_submission = {
        **baseline, "source_id": "sec_alpha_submissions",
        "content_sha256": "1" * 64, "receipt_sha256": "2" * 64,
        "retrieved_at": "2026-08-10T00:01:00Z",
    }
    unbound_coverage = candidate_research_coverage(
        store, owner="paper", candidate_leaf=candidate.leaf_sha256,
        current_receipts={
            "sec_alpha_companyfacts": baseline,
            "sec_alpha_submissions": first_submission,
        },
        required_source_ids=("sec_alpha_companyfacts", "sec_alpha_submissions"),
    )
    assert unbound_coverage["source_checks"][1]["status"] == "baseline_unobserved"
    assert unbound_coverage["deep_research_activation"] == "request"
    assert store.get_leaf(record_candidate_research_coverage(
        store, owner="paper", coverage=coverage,
    ))["object_kind"] == "research_evidence_coverage"
    changed = {
        **baseline, "content_sha256": "e" * 64, "receipt_sha256": "f" * 64,
        "retrieved_at": "2026-08-14T00:00:00Z", "raw_path": "sources/alpha-e.json",
    }
    (tmp_path / "data" / "latest_source_run.json").write_text(json.dumps({
        "source_receipts": [changed],
    }), encoding="utf-8")
    result = enqueue_changed_source_research(tmp_path)
    changed_coverage = candidate_research_coverage(
        store, owner="paper", candidate_leaf=candidate.leaf_sha256,
        current_receipts={"sec_alpha_companyfacts": changed},
        required_source_ids=("sec_alpha_companyfacts", "sec_alpha_submissions"),
    )
    assert changed_coverage["deep_research_activation"] == "await_reassessment"
    record_candidate_research_coverage(store, owner="paper", coverage=changed_coverage)
    assert store.head("paper", "research_evidence_coverage", f"research-coverage:{candidate.leaf_sha256}")["payload"]["covered"] is False
    assert result["queued_count"] == 1
    request = store.get_leaf(result["queued"][0]["reopen_request_leaf"])
    assert request["payload"]["subscription_leaf"] == subscription
    assert request["payload"]["affected_mechanism_claim_leaves"] == []
    assert enqueue_changed_source_research(tmp_path)["already_enqueued_count"] == 1

    # A second dossier can have another baseline for the same fetched receipt.
    # That is a distinct transition event, while request identity stays scoped
    # to its subscription and remains replay-safe.
    second_payload = {**dossier_payload, "dossier_sha256": "9" * 64}
    second_dossier = GoldenLeaf(
        owner="paper", object_kind="candidate_research_dossier",
        object_id="research:ALPHA:second", epoch="dossier-2",
        occurred_at="2026-08-10T12:00:00Z", available_at="2026-08-10T12:00:00Z",
        payload=second_payload, source_refs=("fixture",),
    )
    store.append_bundle((second_dossier,))
    (tmp_path / "data" / "latest_source_run.json").write_text(json.dumps({
        "source_receipts": [{
            **baseline, "content_sha256": "8" * 64, "receipt_sha256": "7" * 64,
            "retrieved_at": "2026-08-10T11:00:00Z",
        }],
    }), encoding="utf-8")
    record_monitor_subscription(
        store, root=tmp_path, owner="paper", dossier_leaf=second_dossier.leaf_sha256,
        dossier=second_payload, subscribed_at="2026-08-10T12:01:00Z",
    )
    (tmp_path / "data" / "latest_source_run.json").write_text(json.dumps({
        "source_receipts": [changed],
    }), encoding="utf-8")
    distinct = enqueue_changed_source_research(tmp_path)
    assert distinct["queued_count"] == 1
    events = store.list_leaves(
        owner="paper", object_kind="public_source_change_event", limit=10,
    )
    transitions = {
        (
            (store.get_leaf(row["leaf_sha256"])["payload"])["previous_content_sha256"],
            (store.get_leaf(row["leaf_sha256"])["payload"])["current_content_sha256"],
        )
        for row in events
    }
    assert transitions == {("a" * 64, "e" * 64), ("8" * 64, "e" * 64)}
    assert enqueue_changed_source_research(tmp_path)["already_enqueued_count"] == 2


def test_strategy_phenotype_is_invariant_to_choice_names_and_order() -> None:
    def dossier(ids: list[str]) -> dict:
        return {
            "entity_id": ids[0], "candidate_leaf": "a" * 64,
            "dossier_sha256": "b" * 64,
            "strategy": {
                "choices": [{"id": value} for value in ids],
                "reinforcing_edges": [
                    {"from": ids[0], "to": ids[1]},
                    {"from": ids[1], "to": ids[2]},
                ],
            },
        }
    assert (
        strategy_choice_system_phenotype(dossier(["a", "b", "c"]))["phenotype_id"]
        == strategy_choice_system_phenotype(dossier(["z", "x", "y"]))["phenotype_id"]
    )


def test_preference_regions_are_permutation_invariant_and_expose_unsupported_frontier() -> None:
    alternatives = {
        "return": {"return": 1, "quality": 0},
        "quality": {"return": 0, "quality": 1},
        "middle": {"return": 0.4, "quality": 0.4},
    }
    left = compile_linear_preference_regions(
        objective_names=("return", "quality"), alternatives=alternatives,
    )
    right = compile_linear_preference_regions(
        objective_names=("quality", "return"), alternatives=dict(reversed(alternatives.items())),
    )
    assert left["preference_regions_sha256"] == right["preference_regions_sha256"]
    assert left["supported_alternative_ids"] == ["quality", "return"]
    return_region = next(row for row in left["regions"] if row["alternative_id"] == "return")
    assert return_region["coordinate_bounds"]["return"] == {
        "lower_exact": "1/2", "upper_exact": "1",
    }


def test_complete_policy_review_requires_paired_blocks_before_recommending() -> None:
    family = {
        "schema": "jaggedthoughts-portfolio-policy-trial-family-v1",
        "trial_family_id": "paired-policy-family",
        "policy_versions": {"cash": "1", "candidate": "1"},
        "horizon_days": 365,
        "estimand_role": "primary_patient_capital_policy_evidence",
        "return_price_identity": "adjusted_close_total_return_proxy",
    }
    pairs = []
    for index in range(8):
        run_id = f"policy-run-{index}"
        pairs.append((
            {"run_id": run_id, "equivalent_policies": []},
            {
                "inference_block_id": f"block-{index}",
                "evaluated_at": f"2027-0{index + 1}-01T00:00:00Z",
                "settlement_sha256": f"{index + 1:064x}",
                "policy_scores": [
                    {"policy_id": "cash", "portfolio_excess_return_after_cost": 0.0, "selection_active_contribution_after_cost": 0.0},
                    {"policy_id": "candidate", "portfolio_excess_return_after_cost": 0.02, "selection_active_contribution_after_cost": 0.02},
                ],
            },
        ))
    review = _compile_policy_review(family, pairs)
    assert review["activation_status"] == "eligible_for_paper_policy_review"
    assert review["recommended_policy_id"] == "candidate"
    assert review["automatic_policy_change"] is False


def test_probability_flux_step_conserves_mass_and_is_mirror_equivariant() -> None:
    mass = (0.1, 0.2, 0.4, 0.2, 0.1)
    flux = (0.05, -0.8, 0.03, 0.2)
    result = conservative_density_step(mass, flux)
    mirrored = conservative_density_step(tuple(reversed(mass)), tuple(-x for x in reversed(flux)))
    assert sum(result) == pytest.approx(1.0)
    assert min(result) >= 0
    assert result == pytest.approx(tuple(reversed(mirrored)))
