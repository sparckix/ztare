"""Operator workspace orchestration for JaggedThoughts investment decisions.

The workspace is a file-backed operating projection over the reusable
investment kernel.  Source bytes, editable profiles, compiled decisions,
reports, portfolio assemblies, tournament artifacts, and the SQLite golden
store remain separate objects with explicit paths and lifecycles.
"""

from __future__ import annotations

from collections import Counter
import csv
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import time
import zipfile
from threading import Event, Lock, Thread
from typing import Any, Iterable, Mapping, Sequence

import yaml

from ztare.common.equivariance import stable_sha256
from ztare.common.linear_preference_regions import compile_linear_preference_regions
from ztare.leanmill import work_queue

from .adaptive_execution import (
    execution_market_status,
    run_execution_market_probe,
)
from .closed_book import (
    CLOSED_BOOK_RUN_SCHEMA,
    CLOSED_BOOK_SETTLEMENT_SCHEMA,
    _price_rows_by_entity,
    closed_book_price_refresh_entity_ids,
    closed_book_status,
    open_closed_book_forecast,
    settle_due_closed_book_forecasts,
)
from .prospective_return_window import (
    bind_prospective_return_window,
    settle_prospective_return_window,
)
from .research_question_policy_outcome import (
    freeze_research_question_policy_action,
    settle_research_question_policy_outcome,
)
from .market_state_forecast import (
    MARKET_STATE_SOURCE_IDS,
    due_market_state_horizons,
    market_state_forecast_status,
    open_market_state_forecast,
    settle_due_market_state_forecasts,
)
from .market_flow_shadow import run_market_flow_shadow_cycle
from .market_flow_successor import (
    SUCCESSOR_RESULT_SCHEMA,
    compile_market_flow_successor_memory,
)
from .paper_watch import paper_watch_decisions as current_paper_watch_decisions
from .capital_cycle import (
    CAPITAL_CYCLE_RUN_SCHEMA,
    capital_cycle_status,
    compile_opportunity_book,
    default_capital_cycle_policy,
    due_forecast_windows,
    load_capital_cycle_policy,
)
from .compiler import compile_investment_profile_file
from .company_quality import (
    InsufficientCompanyHistoryError,
    compile_company_quality_from_observations,
    load_company_fundamentals_index,
)
from .contracts import (
    MetricObservation, canonical_timestamp, require_finite, require_text, timestamp_key,
)
from .drafts import activate_public_equity_profile, create_public_equity_draft
from .discovery import (
    DISCOVERY_ENGINE_VERSION,
    activation_map,
    compile_discovery_run,
    default_discovery_policy,
    discovery_schedule_status,
    load_discovery_policy,
)
from .funnel import FunnelObjectRef, FunnelTransitionReceipt, funnel_surface
from .factor_analysis import InsufficientFactorHistoryError
from .institutional_learning import (
    default_law_catalog,
    institutional_learning_status,
    run_institutional_learning_cycle,
)
from .institutional_edge import compile_institutional_edge_map
from .learning_credit import (
    compile_learning_credit_assignment,
)
from .learning_experiment_design import compile_learning_experiment_design
from .learning_experiment_activation import compile_learning_experiment_activation
from .underwriting_method_policy import compile_underwriting_method_policy
from .strategy_alpha_tournament import (
    compile_strategy_alpha_evidence,
    evaluate_strategy_alpha_tournament,
    strategy_alpha_tournament_surface,
)
from .strategy_alpha_binding import (
    process_strategy_alpha_issuance_actions,
    strategy_alpha_binding_status,
)
from .strategy_alpha_scheduler import (
    compile_strategy_alpha_episode_history,
    compile_strategy_alpha_source_readiness,
    schedule_strategy_alpha_prospective_episodes,
    strategy_alpha_cohort_gate,
    strategy_alpha_cohort_policy,
)
from .strategy_dual_outcome import compile_strategy_dual_outcome_episodes
from .strategy_transfer import (
    compile_strategy_program_transfer_index,
    compile_strategy_transfer_index,
)
from .strategy_outcome_acquisition import (
    submit_workspace_program_control_observation_outcomes,
    compile_strategy_outcome_source_plan,
    compile_workspace_strategy_program_outcome_acquisition,
    compile_workspace_strategy_outcome_acquisition,
    submit_workspace_observation_outcomes,
    submit_workspace_program_observation_outcomes,
)
from .strategy_program_comparison import (
    STRATEGY_PROGRAM_OPERATING_COMPARISON_SCHEMA,
    compile_strategy_program_operating_comparison,
)
from .strategy_control_eligibility import compile_workspace_strategy_control_eligibility
from .strategy_control_status import compile_workspace_strategy_control_runtime_status
from .strategy_state_control_acquisition import (
    compile_workspace_strategy_state_control_acquisition,
)
from .strategy_transfer_acquisition import (
    STRATEGY_PROGRAM_CONTROL_ACQUISITION_SCHEMA,
    STRATEGY_TRANSFER_ACQUISITION_SCHEMA,
    compile_strategy_program_control_acquisition,
    compile_strategy_transfer_acquisition_policy,
)
from .historical_strategy_event_replay import (
    acquire_workspace_historical_strategy_events,
    compile_workspace_historical_strategy_event_replay,
)
from .strategy_walk_forward import (
    compile_workspace_strategy_security_walk_forward,
    compile_workspace_strategy_walk_forward,
)
from .strategy_representation_learning import (
    compile_strategy_security_representation_learning,
)
from .strategy_path_shadow import (
    acquire_workspace_strategy_path_shadow,
    compile_workspace_strategy_path_shadow,
)
from .historical_strategy_control_design import (
    acquire_workspace_historical_strategy_controls,
    compile_workspace_historical_strategy_control_design,
)
from .historical_strategy_bulk_corpus import (
    acquire_sec_bulk_companyfacts,
    acquire_sec_bulk_submissions,
    compile_historical_strategy_bulk_event_corpus,
    enforce_sec_bulk_archive_retention,
)
from .historical_strategy_bulk_learning import (
    acquire_bulk_strategy_documents,
    compile_bulk_strategy_learning_queue,
    resolve_bulk_strategy_ambiguities,
)
from .historical_strategy_bulk_outcomes import (
    compile_bulk_strategy_outcome_observations,
    compile_bulk_strategy_outcome_coverage,
    compile_bulk_strategy_panel_readiness,
)
from .historical_strategy_bulk_effects import (
    compile_bulk_strategy_effect_diagnostics,
    compile_bulk_strategy_outcome_robustness,
)
from .historical_strategy_law_search import compile_bulk_strategy_law_search
from .historical_strategy_law_trial import advance_bulk_strategy_law_trial
from .underwriting_adapter import compile_workspace_underwriting_index
from .state_pricing import audit_workspace_state_price_readiness
from .state_price_authoring import audit_workspace_modeled_grids, audit_workspace_proposals
from .valuation_grammar_evaluation import schedule_valuation_grammar_evaluations
from .allocation_readiness import compile_workspace_allocation_readiness
from .sleeve_implementation import compile_workspace_sleeve_implementation_frontier
from .fund_sleeve_comparison import (
    compile_workspace_fund_lookthrough_acquisition_plan,
    compile_workspace_fund_sleeve_comparison,
)
from .fund_implementation_review import compile_workspace_fund_implementation_review
from .strategy_active_comparator import compile_workspace_strategy_active_comparator
from .strategy_valuation_bridge import compile_strategy_valuation_bridge_readiness
from .instrument_portfolio_admission import (
    WORKSPACE_INSTRUMENT_PORTFOLIO_ADMISSIONS_SCHEMA,
    compile_workspace_instrument_portfolio_admissions,
)
from .paper_policy_path import compile_workspace_household_paper_policy_path
from .household_goal_surface import compile_private_household_workspace
from .household_allocation_scenario import (
    compile_household_allocation_scenario,
    default_household_allocation_scenario_inputs,
)
from .household_mandate_frontier import compile_household_mandate_frontier
from .household_policy_tournament import (
    household_policy_price_refresh_entity_ids,
    household_policy_tournament_status,
    open_household_policy_tournament,
    settle_household_policy_tournaments,
)
from .operator_paper_policy import (
    compose_operator_household_mandate,
    freeze_operator_paper_policy,
    operator_paper_policy_status,
)
from .search_trial_census import (
    compile_workspace_search_trial_census,
    register_prospective_search_surface,
)
from .equity_paper import (
    activate_workspace_equity_paper_watch,
    compile_workspace_equity_proposals,
)
from .fund_paper import (
    activate_workspace_fund_paper_watch,
    compile_workspace_fund_proposals,
)
from .investor_action_brief import compile_investor_action_brief
from .broad_equity_acquisition import (
    compile_broad_equity_acquisition,
    default_broad_equity_policy,
)
from .sec_frame_screen import (
    SCREEN_SCHEMA as SEC_FRAME_SCREEN_SCHEMA,
    compile_sec_frame_acquisition_run,
    hydrate_sec_annual_frame_screen,
)
from .broad_fund_acquisition import compile_broad_fund_acquisition_plan
from .broad_fund_scout import broad_fund_scout_policy, compile_broad_fund_scout
from .universe_breadth import audit_workspace_breadth
from .golden_store import (
    decode_golden_body,
    GoldenEdge,
    GoldenLeaf,
    GoldenStore,
    record_agent_research_request,
    record_candidate_research_dossier,
    record_company_quality_report,
    record_discovery_run,
    record_funnel_transition,
    record_investment_decision,
    record_investment_settlement,
    record_market_flow_experiment,
    record_mechanism_research_result,
    record_opportunity_watchlist,
    record_portfolio_assembly,
    record_research_evidence_quarantine,
    record_strategy_move_library,
    record_company_contingent_recourse_selection,
    record_strategy_program_control_outcome_episode,
    record_strategy_program_control_outcome_plan,
    record_strategy_program_outcome_episode,
    record_world_model_tournament,
    research_evidence_admissibility,
)
from .market_flow import compile_market_flow_backtest
from .market_flow_panel import compile_cross_sectional_flow_evidence
from .company_state_flow import compile_company_state_flow_evidence
from .company_state_newton_successor import freeze_company_state_newton_successor
from .company_state_path_action import compile_company_state_path_action
from .company_state_path_action_settlement import compile_company_state_path_action_status
from .max_caliber_recovery import compile_max_caliber_readiness, compile_workspace_recovery
from .strategy_path_lagrangian import compile_workspace_strategy_path_activation
from .strategy_program_representation_ablation import (
    compile_workspace_strategy_program_representation_activation,
)
from .strategy_state_transition_join import compile_workspace_strategy_state_transition_join
from .metrics import metric_universe_surface
from .paper import OutcomeSnapshot, settle_paper_decision
from .portfolio import (
    PatientCapitalPolicy,
    PortfolioConstraints,
    PortfolioExposureBand,
    PortfolioObjective,
    compile_portfolio_assembly,
)
from .portfolio_policy import (
    PORTFOLIO_POLICY_STATUS_SCHEMA,
    open_portfolio_policy_tournament,
    portfolio_policy_price_refresh_entity_ids,
    portfolio_policy_status,
    settle_portfolio_policy_tournaments,
)
from .rank_program_tournament import (
    DIAGNOSTIC_HORIZON_DAYS,
    open_rank_program_tournament,
    rank_program_price_refresh_entity_ids,
    rank_program_tournament_status,
    settle_rank_program_tournaments,
)
from .valuation import compile_hurdle_price_frontier
from .research_jobs import (
    ENRICHMENT_JOB_KIND,
    ENRICHMENT_POLICY_SCHEMA,
    ResearchEvidenceTimestampError,
    claim_cycle_jobs,
    compile_enrichment_cycle,
    compile_research_learning,
    compile_research_request,
    default_enrichment_policy,
    enqueue_cycle_jobs,
    ensure_qualified_research_job,
    finish_claimed_job,
    latest_discovery_candidate_index,
    load_enrichment_policy,
    mark_job_researched,
    materialize_cycle,
    materialize_job_result,
    recover_completed_job,
    require_research_parent_ready,
    research_job_snapshot,
    research_rank_priority,
    research_request_currency,
    validated_discovery_research_handoff,
    validate_research_dossier,
)
from .research_agent import (
    enqueue_strategy_calibration_successors,
    enqueue_research_request_jobs,
    ensure_strategy_alpha_issuance_action,
    research_agent_live_status,
    research_agent_status,
)
from .report import decision_report, scorecard_report, tournament_report
from .research_memory import (
    candidate_research_coverage,
    compile_research_coverage_index,
    compile_research_memory,
    record_candidate_research_coverage,
)
from .research_monitor import (
    MATERIAL_MONITOR_ADAPTERS,
    current_monitor_receipts,
    material_monitor_source_ids,
    record_monitor_subscription,
)
from .research_budget_tournament import research_budget_tournament_status
from .evidence_vault import evidence_vault_status
from .point_in_time_replay import (
    run_sealed_walk_forward_cycle,
    sealed_walk_forward_status,
)
from .sources import (
    consume_public_sources,
    load_source_manifest,
    project_cached_yahoo_adjusted_prices,
    source_requirements,
)
from .source_epoch import current_source_epoch, validate_source_epoch
from .strategy_options import (
    compile_company_strategy_frontier, select_company_contingent_recourse,
)
from .strategy_measurement_contract import normalize_strategy_measurement_parent_profile
from .strategy_learning import compile_workspace_strategy_move_library
from .strategy_law_induction import (
    STRATEGY_LAW_INDUCTION_SCHEMA,
    compile_strategy_law_induction,
)
from .tournament import compile_world_model_tournament_profile
from .universe import (
    _fund_issuer_source,
    enroll_public_equities,
    enroll_public_equity,
    enroll_public_funds,
    enroll_public_fund,
    public_equity_is_enrolled,
    repair_public_equity_monitor_sources,
    repair_public_equity_quarterly_sources,
    repair_public_fund_sources,
)
from .universe_catalog import refresh_public_market_catalog, run_market_scout
from .watchlist import compile_fund_watchlist


WORKSPACE_SCHEMA = "jaggedthoughts-investment-workspace-v1"
READ_MODEL_SCHEMA = "jaggedthoughts-investment-workspace-read-model-v1"
HOUSEHOLD_MANDATE_FRONTIER_CACHE_SCHEMA = (
    "jaggedthoughts-household-mandate-frontier-cache-v1"
)
BUILD_SCHEMA = "jaggedthoughts-investment-workspace-build-v1"
MARKET_SCOUT_POLICY_SCHEMA = "jaggedthoughts-market-scout-policy-v1"
MARKET_SCOUT_CYCLE_SCHEMA = "jaggedthoughts-market-scout-cycle-v1"
ENRICHMENT_EXECUTION_SCHEMA = "jaggedthoughts-autonomous-enrichment-execution-v1"
BROAD_FUND_ACQUISITION_JOB_KIND = "jaggedthoughts_broad_fund_source_acquisition"
FUND_LOOKTHROUGH_AUTONOMY_SCHEMA = "jaggedthoughts-fund-lookthrough-autonomy-v1"

_DISCOVERY_LOCK = Lock()
_MARKET_SCOUT_LOCK = Lock()
_ENRICHMENT_LOCK = Lock()
_FUND_LOOKTHROUGH_LOCK = Lock()
_CAPITAL_CYCLE_LOCK = Lock()
_DISCOVERY_SERVICE: Thread | None = None
_DISCOVERY_STOP = Event()
_CAPITAL_CYCLE_SERVICE: Thread | None = None
_CAPITAL_CYCLE_STOP = Event()
_GOLDEN_VERIFICATION_CACHE: dict[str, dict[str, Any]] = {}
_READ_MODEL_CACHE_LOCK = Lock()
_READ_MODEL_PARSE_CACHE: dict[str, tuple[int, int, dict[str, Any]]] = {}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_workspace_path() -> Path:
    configured = str(os.environ.get("ZTARE_INVESTMENT_WORKSPACE") or "").strip()
    return (Path(configured).expanduser() if configured else
            _repo_root() / "projects" / "jaggedthoughts_capital" / "workspace" / "investment").resolve()


def resolve_workspace(path: str | Path | None = None) -> Path:
    return (Path(path).expanduser() if path else default_workspace_path()).resolve()


def _workspace_preview_root(root: Path) -> str | None:
    """Return the repository-relative preview authority for one workspace."""
    try:
        return root.resolve().relative_to(_repo_root().resolve()).as_posix()
    except ValueError:
        return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    _atomic_bytes(path, (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"))


def _atomic_text(path: Path, content: str) -> None:
    _atomic_bytes(path, content.encode("utf-8"))


def _load_yaml(path: Path) -> Mapping[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"YAML artifact must be a mapping: {path}")
    return payload


def _compact_ui_lineage(value: Any) -> Any:
    """Replace large evidence-ID vectors with an inspectable count and hash."""
    if isinstance(value, Mapping):
        vector_keys = {
            "source_observation_ids": "source_observation",
            "price_evidence_refs": "price_evidence_ref",
        }
        compacted = {
            str(key): _compact_ui_lineage(item)
            for key, item in value.items()
            if key not in vector_keys
        }
        for key, stem in vector_keys.items():
            identifiers = value.get(key)
            if isinstance(identifiers, list):
                compacted[f"{stem}_count"] = len(identifiers)
                compacted[f"{key}_sha256"] = stable_sha256(identifiers)
        return compacted
    if isinstance(value, list):
        return [_compact_ui_lineage(item) for item in value]
    return value


def _ui_source_run(source_run: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not source_run:
        return None
    projected = {
        key: source_run.get(key)
        for key in (
            "schema", "ok", "as_of", "retrieved_at", "run_sha256",
            "observation_count", "required_failure_count", "historical_use_boundary",
        )
        if source_run.get(key) is not None
    }
    compaction = source_run.get("yahoo_identity_compaction")
    if isinstance(compaction, Mapping):
        projected["yahoo_identity_compaction"] = {
            key: compaction.get(key)
            for key in (
                "schema", "adapter", "metric_ids", "before_count", "after_count",
                "collapsed_count", "status", "receipt_sha256", "capital_authority",
            )
            if compaction.get(key) is not None
        }
    return projected


def _ui_quality_report(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: row.get(key)
        for key in (
            "schema", "report_id", "entity_id", "as_of", "available_at", "coverage",
            "metrics", "scores", "residuals", "use_boundary", "quality_report_sha256",
            "result_path",
        )
        if row.get(key) is not None
    }


def _latest_company_strategy_frontiers(root: Path) -> list[dict[str, Any]]:
    """Project one latest immutable company frontier per entity."""
    latest: dict[str, tuple[tuple[Any, ...], dict[str, Any], Path]] = {}
    for path in sorted((root / "strategy_frontiers" / "results").glob("*.json")):
        result = _read_json(path)
        if not result:
            continue
        entity_id = str((result.get("company") or {}).get("id") or path.stem).upper()
        rank = (
            timestamp_key(str(result.get("evidence_epoch") or "1970-01-01T00:00:00Z")),
            int(result.get("compiler_contract_version") or 1),
            bool(result.get("objective_weight_regions")),
            bool(result.get("economic_bridge")),
            str(result.get("strategy_frontier_sha256") or ""),
        )
        if entity_id not in latest or rank > latest[entity_id][0]:
            latest[entity_id] = (rank, result, path)
    projected_rows = []
    for _rank, result, path in sorted(
        latest.values(), key=lambda row: row[1]["company"]["id"]
    ):
        projected = dict(result)
        if not projected.get("objective_weight_regions") and projected.get("frontier_programs"):
            try:
                projected["objective_weight_regions"] = compile_linear_preference_regions(
                    objective_names=tuple(str(value) for value in projected["objectives"]),
                    alternatives={
                        str(program["program_id"]): program["objective_values"]
                        for program in projected["frontier_programs"]
                    },
                )
            except (KeyError, TypeError, ValueError, RuntimeError):
                pass
        projected_rows.append({
            **projected, "result_path": path.relative_to(root).as_posix(),
        })
    return projected_rows


def _strategy_frontier_index(root: Path) -> dict[str, dict[str, Any]]:
    rows = []
    for projected in _latest_company_strategy_frontiers(root):
        path = projected.get("result_path")
        row = _read_json(root / str(path)) if path else None
        if row:
            rows.append(row)
    return {
        str((row.get("company") or {}).get("id") or "").upper(): row
        for row in rows if (row.get("company") or {}).get("id")
    }


def _strategy_frontier_for_candidate(
    frontiers: Mapping[str, Mapping[str, Any]], candidate: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    frontier = frontiers.get(str(candidate.get("entity_id") or "").upper())
    if frontier is None:
        return None
    try:
        return frontier if timestamp_key(str(frontier["evidence_epoch"])) <= timestamp_key(
            str(candidate["as_of"])
        ) else None
    except (KeyError, TypeError, ValueError):
        return None


def _ui_strategy_frontier(row: Mapping[str, Any]) -> dict[str, Any]:
    choice_space = dict(row.get("choice_space_certificate") or {})
    choice_space["constraint_authority"] = dict(
        choice_space.get("constraint_authority") or {}
    )
    constraints = row.get("feasibility_constraints") or {}
    predicates = [
        {
            "constraint_id": item.get("constraint_id"),
            "predicate_id": "not_all_selected",
            "expression": f"NOT({' AND '.join(item.get('option_ids') or ())})",
            "evidence_refs": list(item.get("evidence_refs") or ()),
            "authority": item.get("authority"),
        }
        for item in constraints.get("incompatibilities") or ()
    ]
    predicates += [
        {
            "constraint_id": item.get("constraint_id"),
            "predicate_id": "implies_all_selected",
            "expression": f"{item.get('option_id')} => {' AND '.join(item.get('requires') or ())}",
            "evidence_refs": list(item.get("evidence_refs") or ()),
            "authority": item.get("authority"),
        }
        for item in constraints.get("prerequisites") or ()
    ]
    predicates += [
        {
            "constraint_id": item.get("constraint_id"),
            "predicate_id": "linear_sum_le",
            "expression": (
                " + ".join(
                    f"{amount}*{option_id}"
                    for option_id, amount in (item.get("uses") or {}).items()
                )
                + f" <= {item.get('limit')} {item.get('unit') or ''}"
            ).strip(),
            "evidence_refs": list(item.get("evidence_refs") or ()),
            "authority": item.get("authority"),
        }
        for item in constraints.get("resources") or ()
    ]
    audit = (row.get("certificate") or {}).get("representation_audit") or {}
    bridge = row.get("economic_bridge") or {}
    company = row.get("company") or {}
    projected = {
        key: row.get(key)
        for key in (
            "schema", "compiler_contract_version", "company", "evidence_epoch",
            "industry_state", "grammar", "enumeration", "choice_space_certificate",
            "constraint_witnesses", "interaction_catalog", "feasibility_constraints",
            "objectives", "contingent_policy_catalog",
            "frontier_program_ids", "frontier_programs", "objective_weight_regions",
            "local_peak_program_ids", "local_peak_programs", "decision_closed",
            "neighborhood",
            "scope_closed", "use_boundary", "strategy_frontier_sha256", "result_path",
        )
        if row.get(key) is not None
    }
    projected["choice_space_certificate"] = choice_space
    projected["explanation_chain"] = {
        "schema": "jaggedthoughts-strategy-frontier-explanation-chain-v1",
        "evidence_refs": sorted({
            ref for predicate in predicates for ref in predicate["evidence_refs"]
        }),
        "predicates": predicates,
        "gate": {
            "status": "accepted" if company.get("strategy_constraint_gate_sha256") else "not_recorded",
            "sha256": company.get("strategy_constraint_gate_sha256"),
            "evidence_grade": (
                company.get("strategy_constraint_evidence_grade")
                or "legacy_ungraded" if company.get("strategy_constraint_gate_sha256")
                else "not_applicable"
            ),
            "research_claim_eligible": bool(
                company.get("strategy_constraint_research_claim_eligible")
            ),
        },
        "z3_delta": {
            key: choice_space.get(key)
            for key in (
                "bounded_bundle_count", "feasible_bundle_count", "excluded_bundle_count",
            )
        } | {"witness_count": len(row.get("constraint_witnesses") or ())},
        "representation": {
            "status": audit.get("status") or "unrecorded",
            "residuals": list(audit.get("residuals") or ())[:3],
        },
        "valuation": {
            "status": "capital_authorized" if bridge.get("capital_authority") else "blocked",
            "next_transition": bridge.get("next_transition"),
        },
    }
    return projected


def _ui_strategy_investment_path(
    frontiers: Iterable[Mapping[str, Any]],
    move_library: Mapping[str, Any],
    valuation_bridge: Mapping[str, Any],
) -> dict[str, Any]:
    """Project one inspectable company path from choices to priced-world readiness."""
    moves = [row for row in move_library.get("moves") or () if isinstance(row, Mapping)]
    candidates: list[tuple[tuple[Any, ...], Mapping[str, Any], Mapping[str, Any] | None]] = []
    for frontier in frontiers:
        company = frontier.get("company") or {}
        if company.get("data_class") == "reference_fixture":
            continue
        frontier_sha = str(frontier.get("strategy_frontier_sha256") or "")
        exact_moves = [row for row in moves if row.get("strategy_frontier_sha256") == frontier_sha]
        displayed_program_ids = {
            str(row.get("program_id"))
            for row in (
                *tuple(frontier.get("frontier_programs") or ()),
                *tuple(frontier.get("local_peak_programs") or ()),
            )
            if isinstance(row, Mapping) and row.get("program_id")
        }
        edges = [
            row for row in (frontier.get("neighborhood") or {}).get("edges") or ()
            if isinstance(row, Mapping)
            and str(row.get("target_program_id") or "") in displayed_program_ids
        ]
        edge = max(
            edges,
            key=lambda row: (
                any(
                    move.get("option_id") == row.get("added_option_id")
                    and move.get("outcome_episodes") for move in exact_moves
                ),
                any(
                    move.get("option_id") == row.get("added_option_id")
                    and move.get("outcome_contracts") for move in exact_moves
                ),
                bool(row.get("target_is_frontier")),
                bool(row.get("target_is_local_peak")),
                str(row.get("edge_sha256") or ""),
            ),
            default=None,
        )
        edge_moves = [
            row for row in exact_moves
            if edge and row.get("option_id") == edge.get("added_option_id")
        ]
        move = max(
            edge_moves,
            key=lambda row: (
                bool(row.get("outcome_episodes")), bool(row.get("outcome_contracts")),
                bool(row.get("implementation_event")), str(row.get("evidence_epoch") or ""),
            ),
            default=None,
        )
        candidates.append(((
            bool(edge), bool(move and move.get("outcome_episodes")),
            bool(move and move.get("outcome_contracts")),
            bool(move and move.get("implementation_event")),
            bool(frontier.get("scope_closed")), len(edges),
            str(frontier.get("evidence_epoch") or ""),
        ), frontier, edge))
    if not candidates:
        return {"schema": "jaggedthoughts-strategy-investment-path-v1", "status": "unavailable"}

    _score, frontier, edge = max(candidates, key=lambda row: row[0])
    company = dict(frontier.get("company") or {})
    frontier_sha = str(frontier.get("strategy_frontier_sha256") or "")
    exact_moves = [row for row in moves if row.get("strategy_frontier_sha256") == frontier_sha]
    edge_moves = [
        row for row in exact_moves
        if edge and row.get("option_id") == edge.get("added_option_id")
    ]
    move = max(
        edge_moves,
        key=lambda row: (
            bool(row.get("outcome_episodes")), bool(row.get("outcome_contracts")),
            bool(row.get("implementation_event")), str(row.get("evidence_epoch") or ""),
        ),
        default=None,
    )
    programs = {
        str(row.get("program_id")): row
        for row in (*tuple(frontier.get("frontier_programs") or ()),
                    *tuple(frontier.get("local_peak_programs") or ()))
        if isinstance(row, Mapping) and row.get("program_id")
    }
    program_id = str((edge or {}).get("target_program_id") or "")
    program = programs.get(program_id) or next(iter(programs.values()), {})
    program_id = str(program.get("program_id") or "")
    terminals = []
    option_labels: dict[str, str] = {}
    for terminal in (frontier.get("grammar") or {}).get("terminals") or ():
        if not isinstance(terminal, Mapping):
            continue
        option_id = str(terminal.get("terminal_id") or "").removeprefix("option:")
        label = option_id.replace("_", " ")
        option_labels[option_id] = label
        terminals.append({
            "option_id": option_id, "label": label,
            "description": terminal.get("description"),
        })
    option_ids = list(program.get("option_ids") or (edge or {}).get("target_option_ids") or ())
    contracts = list((move or {}).get("outcome_contracts") or ())
    episodes = list((move or {}).get("outcome_episodes") or ())
    contract = dict(contracts[0]) if contracts and isinstance(contracts[0], Mapping) else {}
    episode = dict(episodes[0]) if episodes and isinstance(episodes[0], Mapping) else {}
    implementation = dict((move or {}).get("implementation_event") or {})
    if episode:
        empirical_status = "operating_outcome_observed"
    elif contract:
        empirical_status = "awaiting_operating_outcome"
    elif implementation:
        empirical_status = "implementation_observed_needs_metric_contract"
    elif move:
        empirical_status = "needs_exact_implementation_event"
    elif edge:
        empirical_status = "next_test_candidate_not_yet_bound"
    else:
        empirical_status = "needs_one_choice_contrast"
    proposals = list(program.get("economic_coordinate_proposals") or ())
    proposal = next((row for row in proposals if isinstance(row, Mapping)), {})
    return {
        "schema": "jaggedthoughts-strategy-investment-path-v1",
        "status": empirical_status,
        "company": {key: company.get(key) for key in ("id", "name") if company.get(key)},
        "evidence_epoch": frontier.get("evidence_epoch"),
        "choices": terminals,
        "feasible_programs": {
            "count": (frontier.get("choice_space_certificate") or {}).get("feasible_bundle_count"),
            "excluded_count": (frontier.get("choice_space_certificate") or {}).get(
                "excluded_bundle_count"
            ),
            "constraint_witness_count": len(frontier.get("constraint_witnesses") or ()),
            "scope_closed": bool(frontier.get("scope_closed")),
        },
        "highlighted_program": {
            "program_id": program_id,
            "option_ids": option_ids,
            "option_labels": [option_labels.get(value, str(value).replace("_", " ")) for value in option_ids],
            "objective_values": dict(program.get("objective_values") or {}),
            "global_frontier": program_id in set(frontier.get("frontier_program_ids") or ()),
            "local_peak": program_id in set(frontier.get("local_peak_program_ids") or ()),
            "global_frontier_count": len(frontier.get("frontier_program_ids") or ()),
            "local_peak_count": len(frontier.get("local_peak_program_ids") or ()),
        },
        "empirical_contrast": {
            "status": empirical_status,
            "base_option_ids": list((edge or {}).get("base_option_ids") or ()),
            "target_option_ids": list((edge or {}).get("target_option_ids") or ()),
            "added_option_id": (edge or {}).get("added_option_id"),
            "added_option_label": option_labels.get(str((edge or {}).get("added_option_id") or "")),
            "authored_objective_delta": dict((edge or {}).get("authored_objective_delta") or {}),
            "implementation_event": {
                key: implementation.get(key) for key in (
                    "event_kind", "occurred_at", "timing_precision", "treatment_timing_status",
                ) if implementation.get(key) is not None
            },
            "metric_contract": {
                key: contract.get(key) for key in (
                    "metric_id", "direction", "minimum_effect", "unit", "comparator", "due_at",
                ) if contract.get(key) is not None
            },
        },
        "earnings_effect": {
            "status": "observed" if episode else "contracted" if contract else "unmeasured",
            "economic_bridge": ((move or {}).get("mechanism") or {}).get("economic_bridge"),
            "economic_coordinate": proposal.get("economic_coordinate"),
            "metric_id": contract.get("metric_id"),
            "minimum_effect": contract.get("minimum_effect"),
            "unit": contract.get("unit"),
            "due_at": contract.get("due_at"),
            "observed": episode,
        },
        "valuation": {
            "status": valuation_bridge.get("status") or "awaiting_strategy_learning_cycle",
            "direct_financial_effect_count": int(
                valuation_bridge.get("direct_financial_effect_count") or 0
            ),
            "blockers": list(valuation_bridge.get("blockers") or ()),
            "next_activation": valuation_bridge.get("activation_point"),
            "company_specific_result": False,
        },
        "definitions": {
            "pareto": "No feasible program is at least as good on every objective and better on one.",
            "local_peak": (
                "No feasible add, remove, or one-for-one substitution improves it under the "
                "declared objectives."
            ),
        },
        "capital_authority": False,
    }


def _compile_strategy_event_learning_units(
    root: Path, *, shadow: Mapping[str, Any], acquisition: Mapping[str, Any],
    dossiers: Iterable[Mapping[str, Any]], frontiers: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Join each event's discovery, research, formalization, and settlement clocks."""
    request_candidates: dict[str, list[dict[str, Any]]] = {}
    for path in (root / "research_jobs" / "requests").glob("*.json"):
        request = _read_json(path)
        trigger = request.get("strategy_event_trigger") if request else None
        event_sha = str((trigger or {}).get("event_research_request_sha256") or "")
        if event_sha:
            request_candidates.setdefault(event_sha, []).append(request)
    candidate_index = latest_discovery_candidate_index(root)
    requests = {}
    request_currencies = {}
    for event_sha, candidates in request_candidates.items():
        ranked = []
        for request in candidates:
            currency = research_request_currency(request, candidate_index)
            ranked.append((
                {"exact": 2, "compatible_successor": 1}.get(
                    str(currency.get("currency") or ""), 0,
                ),
                str(request.get("as_of") or ""),
                str(request.get("request_sha256") or ""),
                request, currency,
            ))
        selected = max(ranked, key=lambda row: row[:3])
        requests[event_sha], request_currencies[event_sha] = selected[3], selected[4]
    dossiers_by_request = {
        str(row.get("request_sha256") or ""): row for row in dossiers
        if isinstance(row, Mapping) and row.get("request_sha256")
    }
    frontiers_by_request: dict[str, Mapping[str, Any]] = {}
    for row in frontiers:
        company = row.get("company") if isinstance(row, Mapping) else None
        request_sha = str((company or {}).get("source_request_sha256") or "")
        prior = frontiers_by_request.get(request_sha)
        if request_sha and (
            prior is None
            or (
                str(row.get("compiled_at") or ""),
                str(row.get("strategy_frontier_sha256") or ""),
            ) > (
                str(prior.get("compiled_at") or ""),
                str(prior.get("strategy_frontier_sha256") or ""),
            )
        ):
            frontiers_by_request[request_sha] = row
    jobs_by_request: dict[str, dict[str, Any]] = {}
    queue_path = root / "state" / "research_jobs.sqlite3"
    if queue_path.is_file():
        connection = work_queue.connect(str(queue_path))
        try:
            for row in work_queue.list_items(connection, limit=10_000):
                if row.get("kind") != "jaggedthoughts_subscription_research":
                    continue
                request_sha = str((row.get("payload") or {}).get("request_sha256") or "")
                prior = jobs_by_request.get(request_sha)
                if request_sha and (
                    not prior
                    or int(row.get("updated_at") or 0) > int(prior.get("updated_at") or 0)
                ):
                    jobs_by_request[request_sha] = row
        finally:
            connection.close()
    outcomes = {
        str(row.get("event_research_request_sha256") or ""): row
        for row in acquisition.get("discovery_outcomes") or ()
        if isinstance(row, Mapping)
    }
    operating_forecasts = {
        str(row.get("move_observation_sha256") or ""): row
        for row in shadow.get("operating_forecasts") or ()
        if isinstance(row, Mapping) and row.get("move_observation_sha256")
    }
    return_forecasts = {
        str(row.get("target_move_observation_sha256") or ""): row
        for row in shadow.get("forecasts") or ()
        if isinstance(row, Mapping) and row.get("target_move_observation_sha256")
        and int(row.get("path_length") or 0) == 1
    }
    operating_settlements = {
        str(row.get("operating_forecast_sha256") or ""): row
        for row in shadow.get("operating_settlements") or ()
        if isinstance(row, Mapping) and row.get("operating_forecast_sha256")
    }
    return_settlements = {
        str(row.get("forecast_sha256") or ""): row
        for row in shadow.get("settlements") or ()
        if isinstance(row, Mapping) and row.get("forecast_sha256")
    }
    operating_tournament = shadow.get("operating_tournament") or {}
    return_tournament = shadow.get("single_move_tournament") or {}
    units = []
    for event in shadow.get("event_research_queue") or ():
        if not isinstance(event, Mapping):
            continue
        event_sha = str(event.get("research_request_sha256") or "")
        move_sha = str(event.get("move_observation_sha256") or "")
        request = requests.get(event_sha) or {}
        request_currency = request_currencies.get(event_sha) or {}
        request_sha = str(request.get("request_sha256") or "")
        dossier = dossiers_by_request.get(request_sha) or {}
        frontier = frontiers_by_request.get(request_sha) or {}
        job = jobs_by_request.get(request_sha) or {}
        job_payload = job.get("payload") or {}
        discovery = outcomes.get(event_sha) or {}
        operating = operating_forecasts.get(move_sha) or {}
        security = return_forecasts.get(move_sha) or {}
        operating_settlement = operating_settlements.get(
            str(operating.get("operating_forecast_sha256") or "")
        )
        return_settlement = return_settlements.get(
            str(security.get("forecast_sha256") or "")
        )
        if discovery.get("state") == "frontier_closed":
            stage = "discovery_frontier_closed"
            next_activation = str(discovery.get("reason") or "resolve discovery input gap")
        elif not request:
            stage, next_activation = (
                "awaiting_research_request",
                "Bind the candidate leaf to an event research request.",
            )
        elif not dossier and job_payload.get("stage") == "superseded":
            stage, next_activation = (
                "research_request_superseded",
                "Rebind the event to the current compatible discovery leaf or close the path.",
            )
        elif not dossier and job.get("status") == "failed":
            stage, next_activation = (
                "strategy_research_failed",
                "Inspect the typed failure and retry only after its activation condition changes.",
            )
        elif not dossier:
            stage, next_activation = (
                "strategy_research_queued",
                "Run the subscription research job when its dispatch budget opens.",
            )
        elif not frontier:
            stage, next_activation = (
                "awaiting_formal_strategy_frontier",
                "Compile the accepted event dossier into the option grammar.",
            )
        elif not operating_settlement:
            stage = "awaiting_operating_settlement"
            next_activation = (
                "Acquire the earliest public operating observation after "
                f"{(operating.get('settlement_contract') or {}).get('not_before')}."
            )
        elif not return_settlement:
            stage = "awaiting_return_settlement"
            next_activation = (
                "Settle the factor-controlled return after "
                f"{(security.get('settlement_contract') or {}).get('not_before')}."
            )
        else:
            stage, next_activation = (
                "joined_evidence_ready",
                "Review the frozen aggregate tournaments; this unit cannot promote itself.",
            )
        body = {
            "schema": "jaggedthoughts-strategy-event-learning-unit-v1",
            "entity_id": event.get("entity_id"),
            "move_observation_sha256": move_sha,
            "event_research_request_sha256": event_sha,
            "research_priority_rank": event.get("research_priority_rank"),
            "candidate_state": discovery.get("state"),
            "candidate_leaf": discovery.get("candidate_leaf"),
            "research_request_sha256": request_sha or None,
            "research_request_currency": request_currency.get("currency"),
            "research_population": request.get("research_population"),
            "research_job_status": job.get("status"),
            "research_job_stage": job_payload.get("stage"),
            "research_job_currency": job_payload.get("currency"),
            "current_candidate_leaf": job_payload.get("current_candidate_leaf"),
            "dossier_sha256": dossier.get("dossier_sha256"),
            "strategy_frontier_sha256": frontier.get("strategy_frontier_sha256"),
            "operating_forecast_sha256": operating.get("operating_forecast_sha256"),
            "operating_due_at": (operating.get("settlement_contract") or {}).get("not_before"),
            "operating_settlement_sha256": (
                (operating_settlement or {}).get("settlement_sha256")
            ),
            "return_forecast_sha256": security.get("forecast_sha256"),
            "return_due_at": (security.get("settlement_contract") or {}).get("not_before"),
            "return_settlement_sha256": (
                (return_settlement or {}).get("settlement_sha256")
            ),
            "aggregate_tournament_refs": {
                "operating_tournament_sha256": operating_tournament.get(
                    "tournament_sha256"
                ),
                "operating_representation_credit": operating_tournament.get(
                    "operating_representation_credit", False
                ),
                "return_tournament_sha256": return_tournament.get(
                    "tournament_sha256"
                ),
                "return_representation_credit": return_tournament.get(
                    "representation_credit", False
                ),
            },
            "joined_evidence_ready": bool(
                frontier and operating_settlement and return_settlement
            ),
            "stage": stage, "next_activation": next_activation,
            "learning_credit_authority": False, "capital_authority": False,
        }
        units.append({**body, "unit_sha256": stable_sha256(body)})
    units.sort(key=lambda row: (
        int(row.get("research_priority_rank") or 10_000), str(row.get("entity_id") or ""),
    ))
    body = {
        "schema": "jaggedthoughts-strategy-event-learning-units-v1",
        "strategy_path_shadow_sha256": shadow.get("shadow_sha256"),
        "unit_count": len(units),
        "stage_counts": dict(sorted(Counter(row["stage"] for row in units).items())),
        "units": units, "learning_credit_authority": False,
        "capital_authority": False,
    }
    return {**body, "index_sha256": stable_sha256(body)}


def _ui_discovery_status(discovery: Mapping[str, Any]) -> dict[str, Any]:
    projected = dict(discovery)
    latest = dict(projected.get("latest_run") or {})
    rank_input = latest.get("rank_program_input")
    if isinstance(rank_input, Mapping):
        lane_summaries = []
        for lane in rank_input.get("lanes") or ():
            if not isinstance(lane, Mapping):
                continue
            lane_candidates = [
                row for row in lane.get("candidates") or () if isinstance(row, Mapping)
            ]
            lane_summaries.append({
                "lane_id": lane.get("lane_id"),
                "entity_kind": lane.get("entity_kind"),
                "benchmark_id": lane.get("benchmark_id"),
                "candidate_count": len(lane_candidates),
                "eligible_count": sum(
                    row.get("rank_program_eligible") is True for row in lane_candidates
                ),
            })
        latest["rank_program_input"] = {
            "schema": rank_input.get("schema"),
            "rank_program_input_sha256": rank_input.get("rank_program_input_sha256"),
            "pre_truncation": rank_input.get("pre_truncation"),
            "enumerated_candidate_count": rank_input.get("enumerated_candidate_count"),
            "eligibility_policy": rank_input.get("eligibility_policy"),
            "lanes": lane_summaries,
            "capital_authority": False,
        }
    candidates = []
    for raw in latest.get("candidates") or ():
        row = dict(raw)
        valuation = dict(row.get("valuation") or {})
        if valuation:
            row["valuation"] = {
                key: valuation.get(key)
                for key in ("summary", "artifact_path", "envelope_sha256")
                if valuation.get(key) is not None
            }
        row.pop("beta_receipt", None)
        row.pop("input_compatibility", None)
        row.pop("criteria", None)
        row.pop("source_refs", None)
        candidates.append(row)
    if latest:
        latest["candidates"] = candidates
        projected["latest_run"] = latest
    return projected


def _ui_research_request(row: Mapping[str, Any]) -> dict[str, Any]:
    projected = {
        key: row.get(key)
        for key in (
            "schema", "request_id", "request_sha256", "candidate_leaf",
            "candidate_sha256", "entity_id", "entity_kind", "created_at",
            "discovery_run_id", "cycle_sha256", "lifecycle_stage", "request_path",
            "dossier_path", "decision_id", "settlement_status", "learning_status",
            "screen_status", "research_population",
        )
        if row.get(key) is not None
    }
    frontier = row.get("research_question_frontier") or {}
    if frontier:
        closure = frontier.get("closure") or {}
        enumeration = frontier.get("enumeration") or {}
        projected["research_question_frontier"] = {
            "closure": {
                "frontier_count": closure.get("frontier_count"),
                "scope_closed": closure.get("scope_closed"),
            },
            "enumeration": {
                "program_count": enumeration.get("program_count"),
                "exhausted_within_scope": enumeration.get("exhausted_within_scope"),
            },
        }
    return projected


def _ui_subscription_research(status: Mapping[str, Any]) -> dict[str, Any]:
    projected = dict(status)
    queue = dict(status.get("queue") or {})
    queue.pop("jobs", None)
    projected["queue"] = queue
    return projected


def _active_research_transition(status: Mapping[str, Any]) -> dict[str, Any] | None:
    candidate_lane = dict(status.get("candidate_lane") or {})
    activation_lane = dict(status.get("activation_lane") or {})
    lane = activation_lane if activation_lane.get("due_next_claim") else candidate_lane
    service = dict(status.get("service") or {})
    active_job = next(iter(status.get("active_jobs") or ()), {})
    if active_job:
        payload = active_job.get("payload") or {}
        return {
            "enabled": True, "active": True,
            "transition": active_job.get("kind") or candidate_lane.get("active_kind"),
            "work_id": active_job.get("work_id"),
            "job_kind": active_job.get("kind") or candidate_lane.get("active_kind"),
            "subject_id": payload.get("entity_id") or candidate_lane.get("active_entity_id"),
            "status": service.get("status"),
            "starter": (status.get("persistence") or {}).get("starter"),
            "blocked_reasons": [], "capital_authority": False,
        }
    next_job = dict(status.get("next_job") or {})
    if not next_job and lane.get("waiting_count"):
        next_job = {
            "work_id": lane.get("next_work_id"),
            "kind": lane.get("next_kind"),
            "payload": {
                "entity_id": lane.get("next_entity_id"),
                "research_rank": lane.get("next_research_rank"),
                "potential_rank": lane.get("next_potential_rank"),
            },
            "fresh_dispatch_budget_units": lane.get("fresh_dispatch_budget_units") or 1,
        }
    if not next_job:
        return None
    budget = dict(status.get("daily_dispatch_budget") or {})
    blocked = []
    needed = int(next_job.get("fresh_dispatch_budget_units") or 1)
    remaining = int(budget.get("remaining") or 0)
    if remaining < needed:
        blocked.append("daily_subscription_dispatch_budget_insufficient")
    if service.get("status") in {"error", "stale"}:
        blocked.append(f"subscription_research_service_{service['status']}")
    not_before = None
    if remaining < needed and budget.get("utc_day"):
        not_before = (
            datetime.fromisoformat(str(budget["utc_day"])) + timedelta(days=1)
        ).date().isoformat() + "T00:00:00Z"
    payload = dict(next_job.get("payload") or {})
    return {
        "enabled": True, "active": False,
        "transition": next_job.get("kind") or "subscription_research",
        "work_id": next_job.get("work_id"),
        "job_kind": next_job.get("kind"),
        "subject_id": (
            payload.get("entity_id") or payload.get("peer_entity_id")
            or payload.get("project_id")
        ),
        "research_rank": payload.get("research_rank"),
        "potential_rank": payload.get("potential_rank"),
        "dispatch_selection_basis": next_job.get("dispatch_selection_basis"),
        "status": "blocked" if blocked else "queued",
        "not_before": not_before,
        "due_next_claim": True,
        "waiting_count": sum(int(status.get(name, {}).get("waiting_count") or 0) for name in (
            "candidate_lane", "fund_lane",
        )),
        "starter": (status.get("persistence") or {}).get("starter"),
        "blocked_reasons": blocked, "capital_authority": False,
    }


def _ui_research_dossier(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: row.get(key)
        for key in (
            "schema", "request_id", "request_sha256", "candidate_leaf",
            "candidate_sha256", "entity_id", "entity_kind", "as_of", "generated_at",
            "screen_status", "lifecycle_stage", "dossier_sha256", "dossier_path",
        )
        if row.get(key) is not None
    }


def _ui_capital_cycle(status: Mapping[str, Any]) -> dict[str, Any]:
    projected = {
        key: value for key, value in status.items()
        if key not in {"latest_run", "latest_book"}
    }
    run = dict(status.get("latest_run") or {})
    book = dict(status.get("latest_book") or {})
    if run:
        projected["latest_run"] = {
            key: run.get(key)
            for key in (
                "schema", "cycle_id", "started_at", "completed_at", "next_action",
                "opportunity_book_path", "paper_posture", "strategy_alpha_schedule",
                "paper_watch_auto_enrollment",
                "capital_authority",
            )
            if run.get(key) is not None
        }
    if book:
        latest_book = {
            key: book.get(key)
            for key in (
                "schema", "book_id", "generated_at", "qualified_count", "research_count",
                "repair_count", "rows", "paper_posture", "law_policy_influence",
                "next_action", "capital_authority",
            )
            if book.get(key) is not None
        }
        latest_book["candidates"] = [
            {
                key: row.get(key)
                for key in (
                    "candidate_id", "entity_id", "entity_kind", "name", "rank",
                    "research_rank", "learned_research_rank", "potential_rank",
                    "learned_potential_rank", "learned_research_priority_score",
                    "research_priority_score", "research_priority_is_expected_return",
                    "law_policy_influence", "causal_law_target_influence",
                    "economic_coordinates", "screen_status", "next_action", "paper_decision",
                )
                if row.get(key) is not None
            }
            for row in (book.get("candidates") or ())[:10]
        ]
        projected["latest_book"] = latest_book
    return projected


def load_workspace_config(workspace: str | Path | None = None) -> tuple[Path, Mapping[str, Any]]:
    root = resolve_workspace(workspace)
    path = root / "workspace.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"investment workspace is not initialized: {root}")
    payload = _load_yaml(path)
    if payload.get("schema") != WORKSPACE_SCHEMA:
        raise ValueError(f"workspace schema must be {WORKSPACE_SCHEMA}")
    return root, payload


def _copy_reference_fixture(root: Path) -> None:
    source = _repo_root() / "examples" / "jaggedthoughts" / "investment"
    targets = {
        source / "value_quality_play.yaml": root / "profiles" / "reference_fixture.yaml",
        source / "observations" / "value_quality_observations.csv": root / "observations" / "value_quality_observations.csv",
        source / "sources" / "value_quality_memo.md": root / "sources" / "value_quality_memo.md",
        source / "world_model_tournament.yaml": root / "tournaments" / "reference_tournament.yaml",
    }
    for src, destination in targets.items():
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copyfile(src, destination)


def initialize_workspace(
    workspace: str | Path | None = None,
    *,
    owner: str = "operator-paper-book",
    include_reference_fixture: bool = True,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Create an editable workspace and a visibly labelled acceptance fixture."""
    root = resolve_workspace(workspace)
    config_path = root / "workspace.yaml"
    if config_path.exists() and not overwrite:
        raise FileExistsError(f"investment workspace already exists: {root}")
    for directory in (
        "data", "decisions", "observations", "outcomes", "profiles", "reports",
        "sources", "state", "tournaments", "portfolio", "quality", "watchlists", "watchlists/results",
        "experiments", "experiments/results", "discovery", "discovery/runs",
        "discovery/valuations",
        "research", "research/dossiers", "research_jobs", "research_jobs/runs",
        "research_jobs/scheduled", "research_jobs/scheduled/runs",
        "research_jobs/enrichment", "research_jobs/enrichment/runs",
        "research_jobs/enrichment/results", "research_jobs/requests",
        "universe", "universe/raw", "strategy_frontiers", "strategy_frontiers/results",
        "institutional_learning/strategy_moves", "institutional_learning/strategy_outcomes",
        "institutional_learning/strategy_programs", "institutional_learning/strategy_programs/results",
        "institutional_learning/strategy_cohorts", "institutional_learning/strategy_cohorts/results",
        "research_jobs/strategy_cohorts/requests",
        "research_jobs/strategy_programs/requests",
        "research_jobs/strategy_event_refinements/requests",
        "institutional_learning/strategy_event_refinements/results",
        "closed_book", "closed_book/runs", "closed_book/settlements", "closed_book/agent_calls",
        "market_state", "market_state/snapshots", "market_state/runs", "market_state/settlements",
        "portfolio_policy", "portfolio_policy/runs", "portfolio_policy/settlements",
        "portfolio_policy/reviews",
        "rank_program_tournament", "rank_program_tournament/runs",
        "rank_program_tournament/settlements", "rank_program_tournament/return_windows",
        "action_briefs", "capital_cycles", "opportunity_books",
        "institutional_learning", "institutional_learning/cohorts",
        "institutional_learning/evaluations", "institutional_learning/laws",
        "institutional_learning/laws/compiled", "institutional_learning/laws/generated",
        "institutional_learning/panels", "institutional_learning/runs",
    ):
        (root / directory).mkdir(parents=True, exist_ok=True)
    config = {
        "schema": WORKSPACE_SCHEMA,
        "name": "JaggedThoughts Capital Workbench",
        "owner": owner,
        "created_at": _utc_now(),
        "source_manifest": "sources.yaml",
        "profile_globs": ["profiles/*.yaml", "profiles/drafts/*.yaml"],
        "tournament_globs": ["tournaments/*.yaml"],
        "watchlist_globs": ["watchlists/*.yaml"],
        "market_flow_profile_globs": ["experiments/*.yaml"],
        "discovery_policy": "discovery.yaml",
        "market_scout_policy": "research_jobs/intents.yaml",
        "enrichment_policy": "research_jobs/enrichment_policy.yaml",
        "capital_cycle_policy": "capital_cycle.yaml",
        "investment_law_catalog": "institutional_learning/laws.yaml",
        "company_quality": {"enabled": True, "min_years": 3},
        "golden_store": "state/golden_store.sqlite3",
        "reference_profile_ids": ["jaggedthoughts.value-quality.reference"] if include_reference_fixture else [],
        "portfolio": {
            "enabled": include_reference_fixture,
            "portfolio_id": "operator-paper-portfolio",
            "profile_ids": ["jaggedthoughts.value-quality.reference"] if include_reference_fixture else [],
            "include_active_operator_profiles": True,
            "reference_fixture_fallback": include_reference_fixture,
            "max_combinations": 65536,
            "constraints": {
                "id": "operator-paper-constraints",
                "max_invested_weight": 0.90,
                "max_candidate_weight": 0.15,
                "max_turnover_weight": 0.20,
                "max_weighted_downside": 0.30,
                "fixed_weighted_downside": 0.15,
            },
            "objectives": [
                {"id": "return", "metric": "expected_excess_return", "direction": "maximize", "scale": 0.10, "utility_weight": 0.60},
                {"id": "downside", "metric": "weighted_downside", "direction": "minimize", "scale": 0.30, "utility_weight": 0.25},
                {"id": "confidence", "metric": "thesis_confidence", "direction": "maximize", "scale": 0.15, "utility_weight": 0.10},
                {"id": "turnover", "metric": "turnover", "direction": "minimize", "scale": 0.20, "utility_weight": 0.05},
            ],
        },
        "authority": "paper",
        "public_data_default": True,
    }
    source_manifest = {
        "schema": "jaggedthoughts-public-source-manifest-v1",
        "as_of": "now",
        "sources": [
            {
                "id": "sec_ibm_companyfacts", "adapter": "sec_companyfacts", "enabled": True,
                "required": False, "cik": "0000051143", "entity_id": "IBM",
                "user_agent_env": "ZTARE_SEC_USER_AGENT",
                "selections": [
                    {"metric_id": "revenue_fy", "taxonomy": "us-gaap", "concept": "RevenueFromContractWithCustomerExcludingAssessedTax", "fallback_concepts": ["Revenues", "SalesRevenueNet"], "source_unit": "USD", "unit": "USD/year", "period": "annual"},
                    {"metric_id": "operating_cash_flow_fy", "taxonomy": "us-gaap", "concept": "NetCashProvidedByUsedInOperatingActivities", "source_unit": "USD", "unit": "USD/year", "period": "annual"},
                    {"metric_id": "capital_expenditure_fy", "taxonomy": "us-gaap", "concept": "PaymentsToAcquirePropertyPlantAndEquipment", "source_unit": "USD", "unit": "USD/year", "period": "annual"},
                    {"metric_id": "net_income_fy", "taxonomy": "us-gaap", "concept": "NetIncomeLoss", "source_unit": "USD", "unit": "USD/year", "period": "annual"},
                    {"metric_id": "cash", "taxonomy": "us-gaap", "concept": "CashAndCashEquivalentsAtCarryingValue", "source_unit": "USD", "unit": "USD", "period": "instant"},
                    {"metric_id": "assets", "taxonomy": "us-gaap", "concept": "Assets", "source_unit": "USD", "unit": "USD", "period": "instant"},
                    {"metric_id": "debt_current", "taxonomy": "us-gaap", "concept": "LongTermDebtAndCapitalLeaseObligationsCurrent", "fallback_concepts": ["LongTermDebtCurrent", "ShortTermBorrowings", "FinanceLeaseLiabilityCurrent"], "source_unit": "USD", "unit": "USD", "period": "instant"},
                    {"metric_id": "debt_noncurrent", "taxonomy": "us-gaap", "concept": "LongTermDebtAndCapitalLeaseObligations", "fallback_concepts": ["LongTermDebtNoncurrent", "LongTermDebt", "FinanceLeaseLiabilityNoncurrent"], "source_unit": "USD", "unit": "USD", "period": "instant"},
                    {"metric_id": "diluted_shares", "taxonomy": "us-gaap", "concept": "WeightedAverageNumberOfDilutedSharesOutstanding", "source_unit": "shares", "unit": "shares", "period": "annual"},
                    {"metric_id": "diluted_shares_current", "taxonomy": "us-gaap", "concept": "WeightedAverageNumberOfDilutedSharesOutstanding", "source_unit": "shares", "unit": "shares", "period": "any"},
                ],
            },
            {
                "id": "nyu_us_implied_erp", "adapter": "damodaran_current_erp", "enabled": True,
                "required": False, "entity_id": "US-MARKET",
                "erp_metric_id": "implied_equity_risk_premium", "risk_free_metric_id": "risk_free_rate",
            },
            {
                "id": "fred_public_market_state", "adapter": "http_csv", "enabled": True,
                "required": False,
                "latest_only": True,
                "bind_retrieval_epoch": True,
                "url": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=T10Y3M%2CDGS3MO%2CDGS1%2CDFII10%2CT10YIE&cosd=2025-01-01",
                "transport": "curl", "timeout_seconds": 60,
                "user_agent": "Mozilla/5.0 JaggedThoughts-Capital/1.0",
                "provider_note": "Public no-key FRED export normalized to the latest non-missing row per coordinate; history remains in cached source bytes.",
                "mappings": [
                    {
                        "entity_id": "US-MACRO", "metric_id": metric_id,
                        "value_column": series_id, "unit": "decimal", "scale": 0.01,
                        "observed_at_column": "observation_date",
                    }
                    for series_id, metric_id in (
                        ("T10Y3M", "term_spread_10y_3m"),
                        ("DGS3MO", "treasury_3m_yield"),
                        ("DGS1", "treasury_1y_yield"),
                        ("DFII10", "treasury_10y_real_yield"),
                        ("T10YIE", "breakeven_inflation_10y"),
                    )
                ],
            },
            {
                "id": "public_sp500_yield_surface", "adapter": "http_regex_metrics",
                "enabled": True, "required": False, "timeout_seconds": 30,
                "canonical_url": "https://www.multpl.com/s-p-500-earnings-yield",
                "provider_note": "Public current trailing-yield pages plus a dated NYSE/FactSet forward-multiple observation; values retain distinct denominator identities.",
                "mappings": [
                    {"url": "https://www.multpl.com/s-p-500-earnings-yield", "entity_id": "US-MARKET", "metric_id": "sp500_trailing_earnings_yield", "pattern": r"Current S&P 500 Earnings Yield\s*:\s*([0-9.]+)%", "unit": "decimal", "scale": 0.01},
                    {"url": "https://www.multpl.com/s-p-500-dividend-yield", "entity_id": "US-MARKET", "metric_id": "sp500_trailing_dividend_yield", "pattern": r"Current Yield\s*:\s*([0-9.]+)%", "unit": "decimal", "scale": 0.01},
                    {"url": "https://beta.nyse.com/mac-desk/quarterly-earnings-preview", "entity_id": "US-MARKET", "metric_id": "sp500_forward_earnings_yield", "pattern": r"Forward 12-month P/E\s*:\s*~?([0-9.]+)x", "unit": "decimal", "transform": "reciprocal", "observed_at": "2026-07-10T23:59:59Z"},
                ],
            },
            {
                "id": "alpha_vantage_ibm_daily", "adapter": "alpha_vantage_daily", "enabled": False,
                "required": False, "symbol": "IBM", "entity_id": "IBM", "metric_id": "price",
                "unit": "USD", "api_key_env": "ALPHAVANTAGE_API_KEY",
            },
            {
                "id": "alpha_vantage_benchmark_daily", "adapter": "alpha_vantage_daily", "enabled": False,
                "required": True, "symbol": "SPY", "entity_id": "SPY", "metric_id": "price", "unit": "USD",
                "api_key_env": "ALPHAVANTAGE_API_KEY",
            },
            {
                "id": "yahoo_ibm_daily", "adapter": "yahoo_chart_daily", "enabled": True,
                "required": False, "symbol": "IBM", "entity_id": "IBM", "metric_id": "price",
                "unit": "USD", "range": "5y", "interval": "1d", "price_kind": "close",
            },
            {
                "id": "yahoo_spy_daily", "adapter": "yahoo_chart_daily", "enabled": True,
                "required": False, "symbol": "SPY", "entity_id": "SPY", "metric_id": "price",
                "unit": "USD", "range": "5y", "interval": "1d", "price_kind": "close",
            },
            {
                "id": "yahoo_spy_adjusted_daily", "adapter": "yahoo_chart_daily", "enabled": True,
                "required": False, "symbol": "SPY", "entity_id": "SPY", "metric_id": "adjusted_price",
                "unit": "USD", "range": "5y", "interval": "1d", "price_kind": "adjusted_close",
            },
            *[
                {
                    "id": f"yahoo_{symbol.lower()}_adjusted_daily",
                    "adapter": "yahoo_chart_daily", "enabled": True, "required": False,
                    "symbol": symbol, "entity_id": symbol, "metric_id": "adjusted_price",
                    "unit": "USD", "range": "5y", "interval": "1d",
                    "price_kind": "adjusted_close",
                }
                for symbol in ("BIL", "VXUS", "BND", "TIP")
            ],
            *[
                {
                    "id": f"yahoo_{symbol.lower()}_daily", "adapter": "yahoo_chart_daily",
                    "enabled": True, "required": False, "symbol": symbol,
                    "entity_id": symbol, "metric_id": "price", "unit": "USD",
                    "range": "5y", "interval": "1d", "price_kind": "close",
                }
                for symbol in ("VOE", "VBR", "IVE", "IWD", "IWF", "IJR", "MTUM", "QUAL")
            ],
            {
                "id": "ishares_ive_fundamentals", "adapter": "ishares_fundamentals",
                "enabled": True, "required": False, "entity_id": "IVE",
                "url": "https://www.ishares.com/us/products/239728/ishares-sp-500-value-etf",
            },
            {
                "id": "fred_dgs10", "adapter": "fred_series", "enabled": False, "required": False,
                "series_id": "DGS10", "entity_id": "US-MACRO", "metric_id": "risk_free_10y",
                "unit": "decimal", "scale": 0.01, "api_key_env": "FRED_API_KEY",
            },
        ],
        "signals": [
            {
                "schema": "jaggedthoughts-signal-definition-v1", "id": "ibm_owner_earnings",
                "required": False, "entity_id": "IBM", "metric_id": "normalized_owner_earnings",
                "operator": "aligned_subtract", "unit": "USD/year",
                "description": "Annual operating cash flow less reported capital expenditure from the same fiscal period.",
                "arguments": [{"metric": "operating_cash_flow_fy"}, {"metric": "capital_expenditure_fy"}],
            },
            {
                "schema": "jaggedthoughts-signal-definition-v1", "id": "ibm_cash_conversion",
                "required": False, "entity_id": "IBM", "metric_id": "cash_conversion",
                "operator": "ratio", "unit": "multiple",
                "description": "Annual operating cash flow divided by annual net income.",
                "arguments": [{"metric": "operating_cash_flow_fy"}, {"metric": "net_income_fy"}],
            },
            {
                "schema": "jaggedthoughts-signal-definition-v1", "id": "ibm_return_on_assets",
                "required": False, "entity_id": "IBM", "metric_id": "return_on_assets",
                "operator": "ratio", "unit": "decimal",
                "description": "Annual net income divided by the latest reported assets.",
                "arguments": [{"metric": "net_income_fy"}, {"metric": "assets"}],
            },
            {
                "schema": "jaggedthoughts-signal-definition-v1", "id": "ibm_cash_to_assets",
                "required": False, "entity_id": "IBM", "metric_id": "cash_to_assets",
                "operator": "ratio", "unit": "decimal",
                "description": "Cash and equivalents divided by reported assets.",
                "arguments": [{"metric": "cash"}, {"metric": "assets"}],
            },
            {
                "schema": "jaggedthoughts-signal-definition-v1", "id": "ibm_total_debt",
                "required": False, "entity_id": "IBM", "metric_id": "total_debt",
                "operator": "add", "unit": "USD",
                "description": "Current and noncurrent reported debt.",
                "arguments": [{"metric": "debt_current"}, {"metric": "debt_noncurrent"}],
            },
            {
                "schema": "jaggedthoughts-signal-definition-v1", "id": "ibm_excess_net_cash",
                "required": False, "entity_id": "IBM", "metric_id": "excess_net_cash",
                "operator": "subtract", "unit": "USD",
                "description": "Cash and equivalents less total reported debt; negative values denote net debt.",
                "arguments": [{"metric": "cash"}, {"metric": "total_debt"}],
            },
            {
                "schema": "jaggedthoughts-signal-definition-v1", "id": "ibm_net_debt",
                "required": False, "entity_id": "IBM", "metric_id": "net_debt",
                "operator": "negative", "unit": "USD",
                "description": "Total reported debt less cash and equivalents.",
                "arguments": [{"metric": "excess_net_cash"}],
            },
            {
                "schema": "jaggedthoughts-signal-definition-v1", "id": "ibm_market_cap",
                "required": False, "entity_id": "IBM", "metric_id": "market_cap",
                "operator": "multiply", "unit": "USD",
                "description": "Latest retrieved price times the freshest filed diluted-share basis.",
                "arguments": [{"metric": "price"}, {"metric": "diluted_shares_current"}],
            },
            {
                "schema": "jaggedthoughts-signal-definition-v1", "id": "ibm_owner_earnings_yield",
                "required": False, "entity_id": "IBM", "metric_id": "owner_earnings_yield",
                "operator": "yield", "unit": "decimal",
                "description": "Normalized owner earnings divided by the source-derived market capitalization.",
                "arguments": [{"metric": "normalized_owner_earnings"}, {"metric": "market_cap"}],
            },
            {
                "schema": "jaggedthoughts-signal-definition-v1", "id": "ibm_net_debt_to_owner_earnings",
                "required": False, "entity_id": "IBM", "metric_id": "net_debt_to_owner_earnings",
                "operator": "ratio", "unit": "multiple",
                "description": "Total reported debt less cash, divided by normalized owner earnings.",
                "arguments": [{"metric": "net_debt"}, {"metric": "normalized_owner_earnings"}],
            },
        ],
    }
    _atomic_text(config_path, yaml.safe_dump(config, sort_keys=False, allow_unicode=True))
    _atomic_text(root / "sources.yaml", yaml.safe_dump(source_manifest, sort_keys=False, allow_unicode=True))
    _atomic_text(root / "discovery.yaml", yaml.safe_dump(
        default_discovery_policy(), sort_keys=False, allow_unicode=True,
    ))
    _atomic_text(root / "research_jobs" / "intents.yaml", yaml.safe_dump(
        default_market_scout_policy(), sort_keys=False, allow_unicode=True,
    ))
    _atomic_text(root / "research_jobs" / "enrichment_policy.yaml", yaml.safe_dump(
        default_enrichment_policy(), sort_keys=False, allow_unicode=True,
    ))
    _atomic_text(root / "capital_cycle.yaml", yaml.safe_dump(
        default_capital_cycle_policy(), sort_keys=False, allow_unicode=True,
    ))
    _atomic_text(root / "institutional_learning" / "laws.yaml", yaml.safe_dump(
        default_law_catalog(), sort_keys=False, allow_unicode=True,
    ))
    _atomic_text(root / "watchlists" / "public_fund_opportunities.yaml", yaml.safe_dump(
        _default_public_fund_watchlist(), sort_keys=False, allow_unicode=True,
    ))
    _atomic_text(root / "watchlists" / "public_equity_etf_opportunities.yaml", yaml.safe_dump(
        _default_public_equity_etf_watchlist(), sort_keys=False, allow_unicode=True,
    ))
    _atomic_text(root / "experiments" / "lagrangian_market_flow.yaml", yaml.safe_dump(
        _default_market_flow_profile(), sort_keys=False, allow_unicode=True,
    ))
    if include_reference_fixture:
        _copy_reference_fixture(root)
    _atomic_text(root / "README.md", _workspace_readme())
    read_model = build_read_model(root)
    _atomic_json(root / "state" / "read_model.json", read_model)
    return {
        "schema": "jaggedthoughts-investment-workspace-initialization-v1",
        "ok": True,
        "workspace_path": str(root),
        "config_path": str(config_path),
        "reference_fixture_installed": include_reference_fixture,
        "read_model": read_model,
    }


def _workspace_readme() -> str:
    return """# JaggedThoughts Capital Workbench workspace

This directory contains operator state and is normally ignored by git.

- `sources.yaml` declares public-data adapters and signal formulas.
- `sources/raw/` caches exact source bytes by content hash.
- `data/observations.csv` is the normalized point-in-time observation stream.
- `profiles/` contains editable investment decision profiles.
- `decisions/` and `reports/` contain compiled artifacts.
- `portfolio/` contains the constrained paper-portfolio assembly.
- `tournaments/` contains world-model evaluation profiles and results.
- `watchlists/` contains public-fund opportunity screens and factor decompositions.
- `discovery.yaml` owns cadence, declared universes, assumption grids, and screen thresholds.
- `research_jobs/intents.yaml` owns editable recurring broad-market searches.
- `research_jobs/scheduled/` contains periodic broad-scout cycle receipts.
- `research_jobs/enrichment_policy.yaml` owns acquisition, diversity, and source-call budgets.
- `research_jobs/enrichment/` contains immutable selection cycles and leased job results.
- `research_jobs/requests/` contains candidate-leaf-bound agent handoffs.
- `research_jobs/agent/` contains leased subscription-agent call and retry artifacts.
- `discovery/runs/` contains immutable ranked opportunity runs; full valuation envelopes live beside them.
- `capital_cycle.yaml` owns paper risk ceilings and non-overlapping forecast cadences.
- `opportunity_books/` joins discovery, research, strategy, and paper decisions into one action queue.
- `capital_cycles/` contains immutable recurring operating-cycle receipts.
- `experiments/` contains isolated model-family profiles and result summaries.
- `state/golden_store.sqlite3` is the append-only typed lineage store.
- `state/read_model.json` is a disposable UI projection.

The installed fictional reference fixture is marked `reference_fixture` in the
UI. It verifies the complete operating path but is not public market evidence.
Enable and configure public adapters, then add an operator profile whose source
references bind to their cached receipts. All authority remains paper-only.
"""


def default_market_scout_policy() -> dict[str, Any]:
    """Return editable starter intents based on the operator's stated use cases."""
    return {
        "schema": MARKET_SCOUT_POLICY_SCHEMA,
        "enabled": True,
        "catalog_refresh_hours": 24,
        "default_max_results": 50,
        "intents": [
            {
                "id": "broad-public-equities",
                "enabled": True,
                "mode": "broad_equity",
                "acquisition_policy": default_broad_equity_policy(),
            },
            {
                "id": "broad-public-funds",
                "enabled": True,
                "mode": "broad_fund",
                "acquisition_policy": broad_fund_scout_policy(),
            },
        ],
        "activation_boundary": (
            "Scheduled scouts create bounded enrichment queues. Enrollment, research, "
            "underwriting, paper activation, and capital execution are separate transitions."
        ),
    }


def _default_market_flow_profile() -> dict[str, Any]:
    return {
        "schema": "jaggedthoughts-market-flow-experiment-profile-v1",
        "experiment_id": "lagrangian-probability-current-retrospective",
        "as_of": "latest_source_run",
        "mode": "retrospective_retrieval_diagnostic",
        "entity_ids": ["SPY", "IWD", "IWF", "IJR", "MTUM", "QUAL", "VOE", "VBR", "IBM"],
        "lookback": 252,
        "bin_count": 9,
        "state_clip": 4.0,
        "evaluation_stride": 5,
        "training_fraction": 0.60,
        "transaction_cost_bps": 5.0,
        "mass_squared_grid": [0.5, 1.0, 2.0],
        "quartic_grid": [0.0, 0.25, 1.0, 4.0],
        "hypothesis": "A nonlinear Lagrangian response to estimated return-state probability current predicts next-session return and local density change better than linear current, momentum, mean reversion, drift, and zero controls after declared costs.",
        "information_question": "Does the action-derived response add out-of-sample information beyond the estimated current itself, or merely reparameterize it?",
        "kill_condition": "Reject or narrow the nonlinear response family if it fails the return-error, after-cost economic, or linked density-change control comparison. Retrieval-history diagnostics cannot promote the family.",
    }


def _default_public_fund_watchlist() -> dict[str, Any]:
    return {
        "schema": "jaggedthoughts-opportunity-watchlist-v1",
        "watchlist_id": "us-value-fund-opportunities",
        "min_observations": 252,
        "risk_free_metric": {"entity_id": "US-MARKET", "metric_id": "risk_free_rate"},
        "factors": [
            {"id": "market", "long_entity_id": "SPY", "expected_premium_metric": {"entity_id": "US-MARKET", "metric_id": "implied_equity_risk_premium"}},
            {"id": "value", "long_entity_id": "IWD", "short_entity_id": "IWF", "expected_annual_premium": 0.015},
            {"id": "size", "long_entity_id": "IJR", "short_entity_id": "SPY", "expected_annual_premium": 0.010},
            {"id": "momentum", "long_entity_id": "MTUM", "short_entity_id": "SPY", "expected_annual_premium": 0.015},
            {"id": "quality", "long_entity_id": "QUAL", "short_entity_id": "SPY", "expected_annual_premium": 0.010},
        ],
        "criteria": [
            {"id": "predictive-fit", "path": "factor.leave_one_out_r2", "operator": "gt", "value": 0.0},
            {"id": "positive-value-exposure", "path": "factor.beta.value", "operator": "gt", "value": 0.10},
            {"id": "return-hurdle", "path": "factor.implied_return", "operator": "ge", "value": 0.06},
            {"id": "drawdown-budget", "path": "factor.maximum_drawdown", "operator": "ge", "value": -0.50},
        ],
        "candidates": [
            {
                "id": "ive-large-cap-value", "entity_id": "IVE",
                "name": "iShares S&P 500 Value ETF", "category": "US large-cap value",
                "implementation_sleeve_id": "us_equity",
                "implementation_sleeve_source_refs": ["issuer_identity:IVE:S&P_500_Value"],
                "vehicle_kind": "exchange_traded_fund", "alpha_persistence_weight": 0.0,
                "valuation_inputs": ["portfolio_price_to_earnings", "portfolio_price_to_book", "expense_ratio"],
                "payout_ratio_assumptions": [0.35, 0.50, 0.65],
                "thesis_prompt": "Are aggregate earnings power and the growth implied by the current multiple sufficient after factor exposures, fees, and category-relative risks?",
            },
            {"id": "voe-mid-cap-value", "entity_id": "VOE", "name": "Vanguard Mid-Cap Value ETF", "category": "US mid-cap value", "implementation_sleeve_id": "us_equity", "implementation_sleeve_source_refs": ["issuer_identity:VOE:US_Mid_Cap_Value"], "vehicle_kind": "exchange_traded_fund", "alpha_persistence_weight": 0.0, "valuation_inputs": ["portfolio_price_to_earnings", "portfolio_price_to_book", "expense_ratio"], "thesis_prompt": "Is the mid-cap value sleeve priced for an unduly weak earnings-power path after controlling for market, value, size, momentum, and quality exposures?"},
            {"id": "vbr-small-cap-value", "entity_id": "VBR", "name": "Vanguard Small-Cap Value ETF", "category": "US small-cap value", "implementation_sleeve_id": "us_equity", "implementation_sleeve_source_refs": ["issuer_identity:VBR:US_Small_Cap_Value"], "vehicle_kind": "exchange_traded_fund", "alpha_persistence_weight": 0.0, "valuation_inputs": ["portfolio_price_to_earnings", "portfolio_price_to_book", "expense_ratio"], "thesis_prompt": "Does the small-cap value sleeve offer sufficient assumption-implied return and valuation support for its drawdown and factor risks?"},
        ],
    }


def _default_public_equity_etf_watchlist() -> dict[str, Any]:
    """Return a neutral equity-ETF analysis profile for broad acquisitions."""
    profile = _default_public_fund_watchlist()
    return {
        **profile,
        "watchlist_id": "public-equity-etf-opportunities",
        "criteria": [
            row for row in profile["criteria"]
            if row["id"] != "positive-value-exposure"
        ],
        "candidates": [],
    }


def _ensure_public_equity_etf_watchlist(root: Path) -> dict[str, Any]:
    """Materialize the neutral profile and move broad acquisitions out of value policy."""
    neutral_path = root / "watchlists" / "public_equity_etf_opportunities.yaml"
    value_path = root / "watchlists" / "public_fund_opportunities.yaml"
    neutral = (
        dict(_load_yaml(neutral_path))
        if neutral_path.is_file() else _default_public_equity_etf_watchlist()
    )
    moved: list[str] = []
    if value_path.is_file():
        value = dict(_load_yaml(value_path))
        candidates = list(value.get("candidates") or ())
        broad = [
            dict(row) for row in candidates if isinstance(row, Mapping)
            and row.get("category") == "broad regional comparison acquisition"
        ]
        existing = {
            str(row.get("entity_id") or "").upper()
            for row in neutral.get("candidates") or () if isinstance(row, Mapping)
        }
        additions = [
            row for row in broad
            if str(row.get("entity_id") or "").upper() not in existing
        ]
        if additions:
            neutral["candidates"] = [*(neutral.get("candidates") or ()), *additions]
            value["candidates"] = [
                row for row in candidates
                if not (
                    isinstance(row, Mapping)
                    and row.get("category") == "broad regional comparison acquisition"
                )
            ]
            _atomic_text(value_path, yaml.safe_dump(value, sort_keys=False, allow_unicode=True))
            moved = [str(row.get("entity_id") or "").upper() for row in additions]
    _atomic_text(neutral_path, yaml.safe_dump(neutral, sort_keys=False, allow_unicode=True))
    return {
        "watchlist_path": neutral_path.relative_to(root).as_posix(),
        "watchlist_id": neutral["watchlist_id"],
        "moved_entity_ids": moved,
        "watchlist_sha256": stable_sha256(neutral),
    }


def _glob_files(root: Path, patterns: Iterable[Any]) -> list[Path]:
    files: dict[str, Path] = {}
    for pattern in patterns:
        for path in root.glob(str(pattern)):
            if path.is_file():
                files[path.relative_to(root).as_posix()] = path
    return [files[key] for key in sorted(files)]


def _store_path(root: Path, config: Mapping[str, Any]) -> Path:
    relative = Path(str(config.get("golden_store") or "state/golden_store.sqlite3"))
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ValueError("golden store path escapes investment workspace") from error
    return path


def refresh_workspace_sources(
    workspace: str | Path | None = None, *, strict: bool = False,
    source_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    root, config = load_workspace_config(workspace)
    manifest = (root / str(config.get("source_manifest") or "sources.yaml")).resolve()
    return consume_public_sources(
        manifest, workspace=root, strict=strict, source_ids=source_ids,
    )


def project_workspace_cached_adjusted_prices(
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    root, config = load_workspace_config(workspace)
    manifest = (root / str(config.get("source_manifest") or "sources.yaml")).resolve()
    projection = project_cached_yahoo_adjusted_prices(manifest, workspace=root)
    discovery_run = _read_json(root / "discovery" / "latest.json") or {}
    rank_program_learning = (
        _open_rank_program_learning_block(root, config, discovery_run)
        if discovery_run.get("rank_program_input") else None
    )
    read_model = build_read_model(root)
    _atomic_json(root / "state" / "read_model.json", read_model)
    return {
        **projection,
        "rank_program_learning": rank_program_learning,
        "read_model_sha256": read_model["read_model_sha256"],
    }


def _compile_company_quality(
    root: Path, config: Mapping[str, Any], store: GoldenStore
) -> list[dict[str, Any]]:
    raw = config.get("company_quality") or {}
    if not isinstance(raw, Mapping) or raw.get("enabled", True) is False:
        return []
    source_run = _current_source_run(root)
    if not source_run:
        return [{"status": "blocked", "error": "public sources have not been refreshed"}]
    manifest_path = root / str(config.get("source_manifest") or "sources.yaml")
    manifest = load_source_manifest(manifest_path)
    entity_ids = sorted({
        str(row.get("entity_id") or "").upper()
        for row in manifest.get("sources", [])
        if isinstance(row, Mapping)
        and row.get("enabled", True) is not False
        and row.get("adapter") == "sec_companyfacts"
        and str(row.get("entity_id") or "").strip()
    })
    observations_by_entity = load_company_fundamentals_index(
        root / "data" / "observations.csv",
        as_of=str(source_run["as_of"]), entity_ids=entity_ids,
    )
    statuses: list[dict[str, Any]] = []
    for entity_id in entity_ids:
        try:
            report = compile_company_quality_from_observations(
                entity_id=entity_id,
                observations=observations_by_entity.get(entity_id, ()),
                as_of=str(source_run["as_of"]),
                min_years=int(raw.get("min_years", 3)),
            )
            destination = root / "quality" / f"{entity_id.lower()}.json"
            _atomic_json(destination, report)
            leaf = record_company_quality_report(
                store, owner=str(config.get("owner") or "operator-paper-book"), report=report,
            )
            transition = FunnelTransitionReceipt(
                transition_id=f"{entity_id}:{source_run['as_of']}:quality-screen",
                from_state="observed", event="qualify", to_state="screened",
                occurred_at=str(source_run["as_of"]),
                predecessor=FunnelObjectRef(
                    object_kind="public_source_epoch",
                    object_id=f"{entity_id}@{source_run['as_of']}",
                    sha256=str(source_run["run_sha256"]),
                ),
                successor=FunnelObjectRef(
                    object_kind="company_quality_report",
                    object_id=str(report["report_id"]),
                    sha256=str(report["quality_report_sha256"]),
                ),
                guard_refs=tuple(report["source_refs"]),
                context={
                    "coverage_status": report["coverage"]["status"],
                    "durable_earnings_power": report["scores"]["durable_earnings_power"],
                },
            )
            funnel_leaf = record_funnel_transition(
                store, owner=str(config.get("owner") or "operator-paper-book"),
                receipt=transition.to_dict(),
            )
            statuses.append({
                "status": "compiled", "entity_id": entity_id,
                "result_path": destination.relative_to(root).as_posix(),
                "golden_leaf": leaf, "funnel_transition_leaf": funnel_leaf,
            })
        except InsufficientCompanyHistoryError as error:
            statuses.append({"status": "blocked", "entity_id": entity_id, "error": str(error)})
        except (KeyError, OSError, TypeError, ValueError) as error:
            statuses.append({"status": "failed", "entity_id": entity_id, "error": str(error)})
    return statuses


def _compile_profiles(root: Path, config: Mapping[str, Any], store: GoldenStore) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    decisions: list[dict[str, Any]] = []
    statuses: list[dict[str, Any]] = []
    reference_ids = set(str(value) for value in config.get("reference_profile_ids", []))
    for profile_path in _glob_files(root, config.get("profile_globs", ["profiles/*.yaml"])):
        relative = profile_path.relative_to(root).as_posix()
        is_draft = profile_path.parent.name == "drafts"
        try:
            decision = compile_investment_profile_file(profile_path, source_root=root)
            profile_id = str(decision["profile_id"])
            lifecycle = decision.get("profile_lifecycle") if isinstance(decision.get("profile_lifecycle"), Mapping) else {}
            data_class = "reference_fixture" if profile_id in reference_ids else str(lifecycle.get("data_class") or "operator")
            profile_stage = "reference" if data_class == "reference_fixture" else str(lifecycle.get("stage") or "active")
            destination = root / "decisions" / f"{decision['decision_id']}.json"
            report_path = root / "reports" / f"{decision['decision_id']}.md"
            status = "compiled"
            warning = ""
            try:
                leaves = record_investment_decision(store, decision)
            except ValueError as error:
                try:
                    existing = store.head(
                        str(decision["owner"]), "paper_decision", str(decision["decision_id"]),
                    )
                except KeyError:
                    raise error
                payload = existing.get("payload")
                if (
                    not isinstance(payload, Mapping)
                    or payload.get("schema") != "jaggedthoughts-investment-decision-v1"
                    or payload.get("decision_id") != decision.get("decision_id")
                ):
                    raise error
                decision = dict(payload)
                leaves = {"decision": str(existing["leaf_sha256"])}
                status = "frozen_existing"
                warning = (
                    "The profile recompiles differently at its frozen evidence epoch; the recorded "
                    "decision remains the projection until a new evidence epoch is created."
                )
            _atomic_json(destination, decision)
            _atomic_text(report_path, decision_report(decision))
            decisions.append(decision)
            statuses.append({
                "profile_path": relative, "profile_id": profile_id, "decision_id": decision["decision_id"],
                "status": status, "data_class": data_class, "profile_stage": profile_stage,
                "decision_path": destination.relative_to(root).as_posix(),
                "report_path": report_path.relative_to(root).as_posix(), "golden_leaves": leaves,
                **({"warning": warning} if warning else {}),
            })
        except (KeyError, OSError, ValueError, yaml.YAMLError) as error:
            statuses.append({
                "profile_path": relative,
                "status": "blocked" if is_draft else "failed",
                "error": str(error),
            })
    return decisions, statuses


def _compile_portfolio_exposure_bands(
    root: Path,
    declarations: Any,
    decisions: Iterable[Mapping[str, Any]],
) -> tuple[PortfolioExposureBand, ...]:
    if not isinstance(declarations, list):
        raise ValueError("portfolio exposure_bands must be a list")
    decision_rows = tuple(decisions)
    watchlists = tuple(filter(None, (
        _read_json(path) for path in sorted((root / "watchlists" / "results").glob("*.json"))
    )))
    bands = []
    for declaration in declarations:
        if not isinstance(declaration, Mapping):
            raise ValueError("portfolio exposure band must be a mapping")
        coefficients = declaration.get("coefficients")
        refs = tuple(str(value) for value in declaration.get("source_refs") or ())
        if coefficients is None:
            factor_id = require_text(declaration.get("factor_id"), "portfolio exposure factor_id")
            derived: dict[str, float] = {}
            source_refs: set[str] = set()
            for decision in decision_rows:
                entity_id = str((decision.get("entity") or {}).get("entity_id") or "")
                cutoff = timestamp_key(canonical_timestamp(
                    decision.get("as_of"), f"portfolio factor cutoff {entity_id}",
                ))
                matches = []
                for watchlist in watchlists:
                    for candidate in watchlist.get("candidates") or ():
                        analysis = candidate.get("analysis") if isinstance(candidate, Mapping) else None
                        if (
                            isinstance(analysis, Mapping)
                            and str(candidate.get("entity_id") or "") == entity_id
                            and analysis.get("schema") == "jaggedthoughts-factor-analysis-v1"
                            and factor_id in ((analysis.get("coefficients") or {}).get("betas") or {})
                            and timestamp_key(str(analysis.get("available_at") or "")) <= cutoff
                        ):
                            matches.append((
                                str(analysis["available_at"]), str(analysis["as_of"]),
                                str(analysis["analysis_sha256"]), watchlist, analysis,
                            ))
                if not matches:
                    raise ValueError(
                        f"exposure {declaration.get('id')} has no pre-decision {factor_id} "
                        f"factor receipt for {entity_id}"
                    )
                available_at, analysis_as_of, digest, watchlist, analysis = sorted(matches)[-1]
                tied = {
                    row[2] for row in matches
                    if row[0] == available_at and row[1] == analysis_as_of
                }
                if len(tied) != 1:
                    raise ValueError(
                        f"exposure {declaration.get('id')} has ambiguous latest factor receipts for {entity_id}"
                    )
                derived[entity_id] = float(analysis["coefficients"]["betas"][factor_id])
                source_refs.update({
                    f"factor-analysis:{digest}",
                    f"opportunity-watchlist:{watchlist['watchlist_sha256']}",
                })
            coefficients, refs = derived, tuple(sorted(source_refs))
        bands.append(PortfolioExposureBand(
            exposure_id=str(declaration.get("id") or ""),
            minimum=(
                float(declaration["minimum"])
                if declaration.get("minimum") is not None else None
            ),
            maximum=(
                float(declaration["maximum"])
                if declaration.get("maximum") is not None else None
            ),
            fixed_exposure=float(declaration.get("fixed_exposure", 0)),
            coefficients=tuple(
                (str(key), float(value)) for key, value in dict(coefficients or {}).items()
            ),
            source_refs=refs,
        ))
    return tuple(bands)


def _compile_portfolio(
    root: Path, config: Mapping[str, Any], store: GoldenStore, decisions: list[dict[str, Any]]
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    raw = config.get("portfolio")
    if not isinstance(raw, Mapping) or not raw.get("enabled", False):
        return None, {"status": "disabled"}
    profile_ids = set(str(value) for value in raw.get("profile_ids", []))
    eligible = [
        row for row in decisions
        if str((row.get("profile_lifecycle") or {}).get("stage") or "active") in {"active", "reference"}
    ]
    active_operator = [
        row for row in eligible
        if str((row.get("profile_lifecycle") or {}).get("data_class") or "") == "operator"
        and str((row.get("profile_lifecycle") or {}).get("stage") or "") == "active"
    ]
    selection_mode = "configured_profiles"
    excluded_incompatible: list[str] = []
    if raw.get("include_active_operator_profiles", True) and active_operator:
        cohorts: dict[tuple[str, ...], list[dict[str, Any]]] = {}
        for row in active_operator:
            book = row.get("paper_book_before") or {}
            benchmark = row.get("benchmark") or {}
            identity = (
                str(row.get("owner") or ""), str(row.get("as_of") or ""),
                str(benchmark.get("entity_id") or ""), str(book.get("book_sha256") or ""),
                str(book.get("currency") or ""),
            )
            cohorts.setdefault(identity, []).append(row)
        selected_identity, selected = max(
            cohorts.items(),
            key=lambda item: (
                timestamp_key(item[0][1]), len(item[1]),
                tuple(sorted(str(row.get("decision_id")) for row in item[1])),
            ),
        )
        selected = sorted(selected, key=lambda row: str(row.get("decision_id")))
        selected_ids = {str(row.get("decision_id")) for row in selected}
        excluded_incompatible = sorted(
            str(row.get("decision_id")) for row in active_operator
            if str(row.get("decision_id")) not in selected_ids
        )
        selection_mode = "latest_compatible_active_operator_cohort"
    else:
        selected = [row for row in eligible if not profile_ids or str(row.get("profile_id")) in profile_ids]
        if selected and not raw.get("reference_fixture_fallback", True):
            selected = [row for row in selected if row.get("profile_lifecycle")]
    if not selected:
        return None, {"status": "blocked", "error": "no compiled decisions match portfolio.profile_ids"}
    constraints_raw = raw.get("constraints")
    if not isinstance(constraints_raw, Mapping):
        return None, {"status": "failed", "error": "portfolio constraints must be a mapping"}
    try:
        constraints = PortfolioConstraints(
            constraint_id=str(constraints_raw.get("id") or ""),
            max_invested_weight=float(constraints_raw["max_invested_weight"]),
            max_candidate_weight=float(constraints_raw["max_candidate_weight"]),
            max_turnover_weight=float(constraints_raw["max_turnover_weight"]),
            max_weighted_downside=float(constraints_raw["max_weighted_downside"]),
            fixed_weighted_downside=float(constraints_raw.get("fixed_weighted_downside", 0)),
            max_positions=(
                int(constraints_raw["max_positions"])
                if constraints_raw.get("max_positions") is not None else None
            ),
            min_position_weight=float(constraints_raw.get("min_position_weight", 0)),
        )
        patient_raw = raw.get("patient_capital")
        patient_policy = (
            PatientCapitalPolicy(
                policy_id=str(patient_raw.get("id") or ""),
                minimum_after_cost_return_edge=float(
                    patient_raw["minimum_after_cost_return_edge"]
                ),
                impairment_return_floor=float(patient_raw["impairment_return_floor"]),
                impairment_confidence_floor=float(patient_raw["impairment_confidence_floor"]),
            ) if isinstance(patient_raw, Mapping) else None
        )
        exposure_bands = _compile_portfolio_exposure_bands(
            root, raw.get("exposure_bands", []), selected,
        )
        objectives = tuple(PortfolioObjective(
            objective_id=str(row["id"]), metric=str(row["metric"]),
            direction=str(row["direction"]), scale=float(row["scale"]),
            utility_weight=float(row["utility_weight"]),
        ) for row in raw.get("objectives", []))
        profile_digest = stable_sha256({"portfolio": raw, "decisions": [row["decision_record_sha256"] for row in selected]})
        assembly = compile_portfolio_assembly(
            portfolio_id=str(raw.get("portfolio_id") or "operator-paper-portfolio"),
            decisions=selected, constraints=constraints, objectives=objectives,
            exposure_bands=exposure_bands,
            patient_capital_policy=patient_policy,
            max_combinations=int(raw.get("max_combinations", 65536)),
            profile_source_sha256=profile_digest,
        )
        destination = root / "portfolio" / "latest_assembly.json"
        _atomic_json(destination, assembly)
        leaf = record_portfolio_assembly(store, assembly=assembly, decisions=selected)
        funnel_leaves: list[str] = []
        selected_alternative = next(
            row for row in assembly["feasible_alternatives"]
            if row["alternative_id"] == assembly["selected_alternative_id"]
        )
        accepted = set(str(value) for value in selected_alternative["accepted_decision_ids"])
        for decision in selected:
            lifecycle = decision.get("profile_lifecycle") or {}
            if lifecycle.get("data_class") != "operator" or lifecycle.get("stage") != "active":
                continue
            decision_id = str(decision["decision_id"])
            decision_ref = FunnelObjectRef(
                object_kind="paper_decision", object_id=decision_id,
                sha256=str(decision["decision_record_sha256"]),
            )
            admission_payload = {
                "schema": "jaggedthoughts-portfolio-admission-v1",
                "portfolio_id": assembly["portfolio_id"], "decision_id": decision_id,
                "assembly_sha256": assembly["portfolio_assembly_sha256"],
                "identity": {
                    "owner": assembly["owner"], "as_of": assembly["as_of"],
                    "benchmark_id": assembly["benchmark_id"], "currency": assembly["currency"],
                    "starting_book_sha256": assembly["starting_book_sha256"],
                },
            }
            admission_ref = FunnelObjectRef(
                object_kind="portfolio_admission",
                object_id=f"{assembly['portfolio_id']}:{decision_id}",
                sha256=stable_sha256(admission_payload),
            )
            admission = FunnelTransitionReceipt(
                transition_id=f"{decision_id}:admit:{assembly['portfolio_assembly_sha256'][:16]}",
                from_state="active_paper", event="admit", to_state="portfolio_candidate",
                occurred_at=str(assembly["as_of"]), predecessor=decision_ref,
                successor=admission_ref,
                guard_refs=(str(decision["decision_record_sha256"]), str(assembly["portfolio_assembly_sha256"])),
                context={"selection_mode": selection_mode},
            )
            funnel_leaves.append(record_funnel_transition(
                store, owner=str(assembly["owner"]), receipt=admission.to_dict(),
            ))
            if decision_id in accepted:
                event, next_state, object_kind = "allocate_paper", "allocated_paper", "paper_allocation"
                context = {"target_weight": assembly["selected_target_weights"].get(str(decision["entity"]["entity_id"]))}
            else:
                event, next_state, object_kind = "decline", "monitored", "monitoring_request"
                context = {"reason": "selected portfolio frontier did not accept this candidate at this epoch"}
            successor_payload = {
                "schema": f"jaggedthoughts-{object_kind.replace('_', '-')}-v1",
                "portfolio_id": assembly["portfolio_id"], "decision_id": decision_id,
                "assembly_sha256": assembly["portfolio_assembly_sha256"], **context,
            }
            allocation = FunnelTransitionReceipt(
                transition_id=f"{decision_id}:{event}:{assembly['portfolio_assembly_sha256'][:16]}",
                from_state="portfolio_candidate", event=event, to_state=next_state,
                occurred_at=str(assembly["as_of"]), predecessor=admission_ref,
                successor=FunnelObjectRef(
                    object_kind=object_kind,
                    object_id=f"{assembly['portfolio_id']}:{decision_id}:{event}",
                    sha256=stable_sha256(successor_payload),
                ),
                guard_refs=(str(assembly["portfolio_assembly_sha256"]),), context=context,
            )
            funnel_leaves.append(record_funnel_transition(
                store, owner=str(assembly["owner"]), receipt=allocation.to_dict(),
            ))
        return assembly, {
            "status": "compiled", "path": destination.relative_to(root).as_posix(),
            "candidate_count": len(selected), "golden_leaf": leaf,
            "selection_mode": selection_mode,
            "excluded_incompatible_decision_ids": excluded_incompatible,
            "funnel_transition_leaves": funnel_leaves,
        }
    except (KeyError, OSError, ValueError) as error:
        return None, {"status": "failed", "error": str(error)}


def _compile_tournaments(root: Path, config: Mapping[str, Any], store: GoldenStore) -> list[dict[str, Any]]:
    statuses: list[dict[str, Any]] = []
    for path in _glob_files(root, config.get("tournament_globs", ["tournaments/*.yaml"])):
        relative = path.relative_to(root).as_posix()
        try:
            result = compile_world_model_tournament_profile(path)
            destination = root / "tournaments" / "results" / f"{result['tournament_id']}.json"
            report_path = root / "reports" / f"{result['tournament_id']}.md"
            _atomic_json(destination, result)
            _atomic_text(report_path, tournament_report(result))
            leaves = record_world_model_tournament(store, result)
            statuses.append({
                "profile_path": relative, "status": "compiled", "tournament_id": result["tournament_id"],
                "result_path": destination.relative_to(root).as_posix(),
                "report_path": report_path.relative_to(root).as_posix(), "golden_leaves": leaves,
            })
        except (KeyError, OSError, ValueError, yaml.YAMLError) as error:
            statuses.append({"profile_path": relative, "status": "failed", "error": str(error)})
    return statuses


def _research_project_projection(
    root: Path, registration: Mapping[str, Any],
) -> dict[str, Any]:
    relative = require_text(registration.get("path"), "research project path")
    project_path = (root / relative).resolve()
    projects_root = (_repo_root() / "projects").resolve()
    project_path.relative_to(projects_root)
    receipt_path = project_path / "evidence_source_receipt.json"
    gate_path = project_path / "latest_gate_results.json"
    candidate_path = project_path / "test_model.py"
    receipt = _read_json(receipt_path) or {}
    gate = _read_json(gate_path) or {}
    historical_admission = _read_json(
        project_path / "workspace" / "historical_admission.json"
    ) or {}
    if (
        historical_admission.get("schema")
        == "jaggedthoughts-company-state-historical-admission-v1"
        and historical_admission.get("status") == "complete"
    ):
        gate_path = project_path / "workspace" / "historical_gate_results.json"
        gate = historical_admission.get("gate_result") or {}
    if not receipt or not gate or not candidate_path.is_file():
        raise ValueError("research project requires evidence receipt, candidate, and gate result")
    history_path = project_path / "workspace" / "eval_history.jsonl"
    iteration_count = sum(
        bool(line.strip()) for line in history_path.read_text(encoding="utf-8").splitlines()
    ) if history_path.is_file() else 0
    hashes = {
        "evidence_receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
        "candidate_sha256": str(
            historical_admission.get("candidate_sha256")
            or hashlib.sha256(candidate_path.read_bytes()).hexdigest()
        ),
        "gate_result_sha256": hashlib.sha256(gate_path.read_bytes()).hexdigest(),
    }
    submissions = [
        {
            "path": path.relative_to(project_path).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in sorted((project_path / "workspace" / "submissions").glob("*.py"))
    ]
    matching_submissions = [
        row["path"] for row in submissions
        if row["sha256"] == hashes["candidate_sha256"]
    ]
    if historical_admission and not matching_submissions:
        raise ValueError("historically admitted candidate bytes are unavailable")
    search_lineage_body = {
        "schema": "jaggedthoughts-research-search-lineage-v1",
        "evaluation_row_count": iteration_count,
        "submission_count": len(submissions),
        "submission_set_sha256": stable_sha256(submissions),
        "current_candidate_sha256": hashes["candidate_sha256"],
        "current_candidate_source": (
            "submission" if matching_submissions else "outside_submission_set"
        ),
        "matching_submission_paths": matching_submissions,
    }
    search_lineage = {
        **search_lineage_body,
        "search_lineage_sha256": stable_sha256(search_lineage_body),
    }
    visible_path = project_path / (
        "evidence_state.txt" if (project_path / "evidence_state.txt").is_file()
        else "evidence.txt"
    )
    partition_hashes = {
        name: hashlib.sha256(path.read_bytes()).hexdigest()
        for name, path in {
            "visible": visible_path,
            "holdout": project_path / "evidence_holdout.txt",
            "farther_tail": project_path / "evidence_farther_tail.txt",
        }.items()
    }
    if gate.get("candidate_sha256") != hashes["candidate_sha256"]:
        raise ValueError("research gate result is not bound to the current candidate")
    if gate.get("evidence_receipt_sha256") != hashes["evidence_receipt_sha256"]:
        raise ValueError("research gate result is not bound to the current evidence receipt")
    if gate.get("partition_file_sha256s") != partition_hashes:
        raise ValueError("research gate result is not bound to the evaluated partitions")
    evaluated_at = datetime.fromtimestamp(
        gate_path.stat().st_mtime, timezone.utc,
    ).isoformat(timespec="microseconds").replace("+00:00", "Z")
    source_refs = tuple(filter(None, (
        str(receipt.get("source_url") or ""),
        f"project:{project_path.name}:evidence:{hashes['evidence_receipt_sha256']}",
        f"project:{project_path.name}:candidate:{hashes['candidate_sha256']}",
        f"project:{project_path.name}:gates:{hashes['gate_result_sha256']}",
    )))
    point_in_time = receipt.get("point_in_time_authority") == "point_in_time"
    body = {
        "schema": "jaggedthoughts-mechanism-research-result-v1",
        "project_id": str(registration.get("project_id") or project_path.name),
        "label": str(registration.get("label") or project_path.name.replace("_", " ").title()),
        "mode": str(registration.get("mode") or "research"),
        "project_path": project_path.relative_to(_repo_root()).as_posix(),
        "evaluated_at": evaluated_at,
        "evidence_epoch": receipt.get("receipt_sha256"),
        "source_url": receipt.get("source_url"),
        "row_counts": receipt.get("row_counts") or {},
        "point_in_time_authority": receipt.get("point_in_time_authority"),
        "iteration_count": iteration_count,
        "search_lineage": search_lineage,
        "harness_ok": bool(gate.get("harness_ok")),
        "screen_pass": bool(gate.get("screen_pass")),
        "score": gate.get("score"),
        "gates": gate.get("gates") or [],
        "partition_results": gate.get("partitions") or {},
        "cross_coordinate_sensitivities": gate.get("cross_coordinate_sensitivities") or {},
        "partition_file_sha256s": partition_hashes,
        **hashes,
        "source_refs": list(source_refs),
        "authority": "experiment_only",
        "capital_authority": False,
        "promotion_eligible": bool(gate.get("screen_pass")) and point_in_time,
        "status": "diagnostic_survivor" if gate.get("screen_pass") else "screen_rejected",
    }
    if "prior_shrinkage" in gate:
        body["prior_shrinkage"] = gate["prior_shrinkage"]
    historical_gate = historical_admission.get("gate_result") or {}
    if historical_admission.get("schema") == "jaggedthoughts-company-state-historical-admission-v1":
        body["historical_admission"] = {
            "status": historical_admission.get("status"),
            "locked_at": historical_admission.get("locked_at"),
            "completed_at": historical_admission.get("completed_at"),
            "candidate_sha256": historical_admission.get("candidate_sha256"),
            "candidate_provenance": historical_admission.get("candidate_provenance"),
            "screen_pass": bool(historical_gate.get("screen_pass")),
            "score": historical_gate.get("score"),
            "partitions": {
                name: {
                    "entity_path_count": values.get("entity_path_count"),
                    "block_win_rate": values.get("block_win_rate"),
                    "proper_score_control_pass": bool(
                        values.get("proper_score_control_pass")
                    ),
                    "block_robustness_pass": bool(values.get("block_robustness_pass")),
                    "metrics": values.get("metrics") or {},
                }
                for name, values in (historical_gate.get("partitions") or {}).items()
                if isinstance(values, Mapping)
            },
            "capital_authority": False,
        }
    return {**body, "research_result_sha256": stable_sha256(body)}


def _compile_research_projects(
    root: Path, config: Mapping[str, Any], store: GoldenStore,
) -> list[dict[str, Any]]:
    statuses = []
    for registration in config.get("research_projects") or ():
        if not isinstance(registration, Mapping):
            continue
        try:
            result = _research_project_projection(root, registration)
            destination = root / "experiments" / "results" / f"{result['project_id']}.json"
            _atomic_json(destination, result)
            leaf = record_mechanism_research_result(
                store, owner=str(config.get("owner") or "operator-paper-book"), result=result,
            )
            statuses.append({
                "project_id": result["project_id"], "status": "compiled",
                "screen_status": result["status"],
                "result_path": destination.relative_to(root).as_posix(),
                "golden_leaf": leaf,
            })
        except (KeyError, OSError, ValueError) as error:
            statuses.append({
                "project_id": str(registration.get("project_id") or "unknown"),
                "status": "failed", "error": str(error),
            })
    return statuses


def _compile_watchlists(root: Path, config: Mapping[str, Any], store: GoldenStore) -> list[dict[str, Any]]:
    statuses: list[dict[str, Any]] = []
    paths = _glob_files(root, config.get("watchlist_globs", ["watchlists/*.yaml"]))
    if not _current_source_run(root):
        return [{"profile_path": path.relative_to(root).as_posix(), "status": "blocked", "error": "public sources have not been refreshed"} for path in paths]
    for path in paths:
        relative = path.relative_to(root).as_posix()
        try:
            result = compile_fund_watchlist(path, workspace=root)
            destination = root / "watchlists" / "results" / f"{result['watchlist_id']}.json"
            _atomic_json(destination, result)
            leaf = record_opportunity_watchlist(
                store, owner=str(config.get("owner") or "operator-paper-book"), watchlist=result,
            )
            statuses.append({
                "profile_path": relative, "status": "compiled",
                "watchlist_id": result["watchlist_id"],
                "candidate_count": result["candidate_count"],
                "qualified_count": result["qualified_count"],
                "result_path": destination.relative_to(root).as_posix(),
                "golden_leaf": leaf,
            })
        except InsufficientFactorHistoryError as error:
            statuses.append({"profile_path": relative, "status": "blocked", "error": str(error)})
        except (KeyError, OSError, ValueError, yaml.YAMLError) as error:
            statuses.append({"profile_path": relative, "status": "failed", "error": str(error)})
    return statuses


def build_workspace(
    workspace: str | Path | None = None, *, project_read_model: bool = True,
) -> dict[str, Any]:
    """Compile every configured profile, portfolio, and tournament into the store."""
    root, config = load_workspace_config(workspace)
    store_path = _store_path(root, config)
    store = GoldenStore(store_path)
    phase_seconds: dict[str, float] = {}
    phase_started = time.perf_counter()
    company_quality_statuses = _compile_company_quality(root, config, store)
    phase_seconds["company_quality"] = round(time.perf_counter() - phase_started, 3)
    phase_started = time.perf_counter()
    decisions, profile_statuses = _compile_profiles(root, config, store)
    phase_seconds["profiles"] = round(time.perf_counter() - phase_started, 3)
    phase_started = time.perf_counter()
    watchlist_statuses = _compile_watchlists(root, config, store)
    phase_seconds["watchlists"] = round(time.perf_counter() - phase_started, 3)
    phase_started = time.perf_counter()
    assembly, portfolio_status = _compile_portfolio(root, config, store, decisions)
    phase_seconds["portfolio"] = round(time.perf_counter() - phase_started, 3)
    phase_started = time.perf_counter()
    tournament_statuses = _compile_tournaments(root, config, store)
    phase_seconds["tournaments"] = round(time.perf_counter() - phase_started, 3)
    phase_started = time.perf_counter()
    research_project_statuses = _compile_research_projects(root, config, store)
    phase_seconds["research_projects"] = round(time.perf_counter() - phase_started, 3)
    phase_started = time.perf_counter()
    try:
        strategy_move_library = compile_workspace_strategy_move_library(root)
        _atomic_json(
            root / "institutional_learning" / "strategy_moves" / "latest.json",
            strategy_move_library,
        )
        strategy_move_status = {
            "status": "compiled", "move_count": strategy_move_library["move_count"],
            "measurable_move_count": strategy_move_library["measurable_move_count"],
            "outcome_episode_count": strategy_move_library["outcome_episode_count"],
            "library_sha256": strategy_move_library["library_sha256"],
            "golden_leaf": record_strategy_move_library(
                store, owner=str(config.get("owner") or "operator-paper-book"),
                library=strategy_move_library,
            ),
        }
        strategy_state_transition_join = (
            compile_workspace_strategy_state_transition_join(root)
            if (root / "experiments/results/company-state-probability-current.json").is_file()
            else {"status": "awaiting_company_state_flow"}
        )
    except (OSError, TypeError, ValueError, yaml.YAMLError) as error:
        strategy_move_status = {"status": "failed", "error": str(error)}
        strategy_state_transition_join = {"status": "unavailable", "error": str(error)}
    try:
        max_caliber_recovery = compile_workspace_recovery(root)
    except (OSError, TypeError, ValueError) as error:
        max_caliber_recovery = {"status": "unavailable", "error": str(error)}
    try:
        strategy_path_lagrangian = compile_workspace_strategy_path_activation(root)
    except (OSError, TypeError, ValueError) as error:
        strategy_path_lagrangian = {"status": "unavailable", "error": str(error)}
    try:
        strategy_program_representation = (
            compile_workspace_strategy_program_representation_activation(root)
        )
    except (OSError, TypeError, ValueError) as error:
        strategy_program_representation = {"status": "unavailable", "error": str(error)}
    phase_seconds["strategy_move_library"] = round(
        time.perf_counter() - phase_started, 3,
    )
    phase_started = time.perf_counter()
    verification = _verified_golden_store(root, store_path)
    phase_seconds["golden_store_verification"] = round(
        time.perf_counter() - phase_started, 3,
    )
    body: dict[str, Any] = {
        "schema": BUILD_SCHEMA,
        "built_at": _utc_now(),
        "workspace_path": str(root),
        "profile_statuses": profile_statuses,
        "company_quality_statuses": company_quality_statuses,
        "portfolio_status": portfolio_status,
        "watchlist_statuses": watchlist_statuses,
        "tournament_statuses": tournament_statuses,
        "research_project_statuses": research_project_statuses,
        "strategy_move_status": strategy_move_status,
        "strategy_state_transition_join": strategy_state_transition_join,
        "max_caliber_recovery": max_caliber_recovery,
        "strategy_path_lagrangian": strategy_path_lagrangian,
        "strategy_program_representation": strategy_program_representation,
        "compiled_decision_count": len(decisions),
        "company_quality_compiled_count": sum(row.get("status") == "compiled" for row in company_quality_statuses),
        "portfolio_compiled": assembly is not None,
        "watchlist_compiled_count": sum(row.get("status") == "compiled" for row in watchlist_statuses),
        "golden_store_verification": verification,
        "phase_seconds": phase_seconds,
    }
    ok = (
        bool(decisions)
        and not any(row.get("status") == "failed" for row in company_quality_statuses)
        and not any(row.get("status") == "failed" for row in profile_statuses)
        and portfolio_status.get("status") not in {"failed", "blocked"}
        and not any(row.get("status") == "failed" for row in watchlist_statuses)
        and not any(row.get("status") == "failed" for row in tournament_statuses)
        and not any(row.get("status") == "failed" for row in research_project_statuses)
        and strategy_move_status.get("status") != "failed"
        and bool(verification.get("ok"))
    )
    result = {**body, "ok": ok, "build_sha256": stable_sha256(body)}
    _atomic_json(root / "state" / "latest_build.json", result)
    if not project_read_model:
        return result
    read_model = build_read_model(root)
    _atomic_json(root / "state" / "read_model.json", read_model)
    return {**result, "read_model": read_model}


def refresh_workspace(
    workspace: str | Path | None = None, *, strict_sources: bool = False
) -> dict[str, Any]:
    """Run the operator refresh transaction from public sources through reports."""
    root, config = load_workspace_config(workspace)
    source_run = refresh_workspace_sources(root, strict=strict_sources)
    build = build_workspace(root)
    body = {
        "schema": "jaggedthoughts-investment-workspace-refresh-v1",
        "ok": bool(source_run.get("ok")) and bool(build.get("ok")),
        "refreshed_at": _utc_now(),
        "source_run": _ui_source_run(source_run),
        "build": {key: value for key, value in build.items() if key != "read_model"},
        "read_model": build["read_model"],
    }
    result = {**body, "refresh_sha256": stable_sha256(body)}
    _atomic_json(root / "state" / "latest_refresh.json", result)
    return result


def _discovery_policy(root: Path, config: Mapping[str, Any]) -> tuple[Path, Mapping[str, Any]]:
    relative = Path(str(config.get("discovery_policy") or "discovery.yaml"))
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ValueError("discovery policy path escapes investment workspace") from error
    return path, load_discovery_policy(path)


def _current_research_routing_inputs(
    root: Path,
) -> tuple[
    Mapping[str, Any] | None, Mapping[str, Any] | None, Mapping[str, Any] | None,
]:
    read_model = _read_json(root / "state" / "read_model.json") or {}
    learning = read_model.get("research_learning")
    if not isinstance(learning, Mapping):
        return None, None, None
    experiment = learning.get("research_question_policy_experiment")
    if not isinstance(experiment, Mapping):
        return None, None, None
    decision = experiment.get("routing_decision")
    credit = read_model.get("learning_credit_assignment")
    return (
        decision if isinstance(decision, Mapping) else None,
        credit if isinstance(credit, Mapping) else None,
        learning,
    )


def _research_basis_source_snapshot(
    root: Path, entity_id: str,
) -> tuple[dict[str, Any], ...]:
    receipts = current_monitor_receipts(root)
    return tuple({
        "source_id": source_id,
        **{
            key: receipt.get(key)
            for key in (
                "content_sha256", "receipt_sha256", "retrieved_at", "canonical_url",
            )
        },
    } for source_id in material_monitor_source_ids(root, entity_id)
      for receipt in (receipts.get(source_id) or {},))


def workspace_discovery_status(
    workspace: str | Path | None = None, *, now: str | None = None
) -> dict[str, Any]:
    root, config = load_workspace_config(workspace)
    policy_path, policy = _discovery_policy(root, config)
    latest = _read_json(root / "discovery" / "latest.json")
    record = _read_json(root / "discovery" / "latest_record.json")
    service = _read_json(root / "state" / "discovery_service.json")
    return {
        "schema": "jaggedthoughts-discovery-status-v1",
        "policy_path": policy_path.relative_to(root).as_posix(),
        "policy_sha256": stable_sha256(policy),
        "schedule": discovery_schedule_status(policy=policy, latest_run=latest, now=now),
        "latest_run": latest,
        "latest_record": record,
        "service": service,
        "activation_points": activation_map(),
    }


def _materialize_valuation_artifacts(
    root: Path, run: dict[str, Any], valuations: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    for candidate in run.get("candidates", []):
        if not isinstance(candidate, dict):
            continue
        entity_id = str(candidate.get("entity_id") or "")
        envelope = valuations.get(entity_id)
        if envelope is None:
            continue
        digest = str(envelope["envelope_sha256"])
        path = root / "discovery" / "valuations" / f"{entity_id.lower()}-{digest[:16]}.json"
        _atomic_json(path, envelope)
        valuation = candidate.get("valuation")
        if isinstance(valuation, dict):
            valuation["artifact_path"] = path.relative_to(root).as_posix()
        candidate.pop("candidate_sha256", None)
        candidate["candidate_sha256"] = stable_sha256(candidate)
    run.pop("run_sha256", None)
    run["run_sha256"] = stable_sha256(run)
    return run


def _ensure_qualified_research_requests(
    root: Path, config: Mapping[str, Any], run: Mapping[str, Any],
    record: Mapping[str, Any], *,
    strategy_event_triggers: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Bind capital candidates and exact zero-weight strategy cases to research."""
    existing = {
        str(request.get("candidate_leaf") or "")
        for path in (root / "research_jobs" / "requests").glob("*.json")
        if (request := _read_json(path))
    }
    leaves = record.get("candidate_leaves") if isinstance(record.get("candidate_leaves"), Mapping) else {}
    owner = str(config.get("owner") or "operator-paper-book")
    store = GoldenStore(_store_path(root, config))
    coverage_index = compile_research_coverage_index(store, owner=owner)
    activations: list[dict[str, Any]] = []
    move_library = _read_json(
        root / "institutional_learning" / "strategy_moves" / "latest.json"
    ) or {}
    strategy_frontiers = _strategy_frontier_index(root)
    measurable_strategy_entities = {
        str(move.get("entity_id") or "")
        for move in move_library.get("moves") or ()
        if isinstance(move, Mapping)
        and move.get("outcome_contracts")
        and (move.get("implementation_event") or {}).get("timing_precision") == "date"
    }
    event_research_entities = set((strategy_event_triggers or {}).keys())
    eligible = [
        dict(candidate)
        for candidate in run.get("candidates", ())
        if isinstance(candidate, Mapping)
        and (
            candidate.get("screen_status") == "qualified"
            or (
                candidate.get("screen_status") == "monitor"
                and candidate.get("entity_kind") == "public_equity"
                and candidate.get("entity_id") in (
                    measurable_strategy_entities | event_research_entities
                )
            )
        )
    ]
    pending: list[dict[str, Any]] = []
    receipts = current_monitor_receipts(root)
    source_manifest = load_source_manifest(
        root / str(config.get("source_manifest") or "sources.yaml")
    )
    monitor_sources_by_entity: dict[str, list[str]] = {}
    for source in source_manifest.get("sources") or ():
        if (
            isinstance(source, Mapping)
            and source.get("enabled", True)
            and source.get("adapter") in MATERIAL_MONITOR_ADAPTERS
            and source.get("entity_id") and source.get("id")
        ):
            monitor_sources_by_entity.setdefault(str(source["entity_id"]), []).append(
                str(source["id"])
            )
    for candidate in eligible:
        candidate_leaf = str(leaves.get(str(candidate.get("candidate_id") or "")) or "")
        if not candidate_leaf:
            continue
        if candidate.get("screen_status") == "monitor":
            if candidate_leaf not in existing:
                pending.append(candidate)
            continue
        coverage = candidate_research_coverage(
            store, owner=owner, candidate_leaf=candidate_leaf,
            current_receipts=receipts,
            required_source_ids=tuple(sorted(
                monitor_sources_by_entity.get(str(candidate["entity_id"]), ())
            )),
            coverage_index=coverage_index,
        )
        prior_dossier_leaf = str(coverage.get("prior_dossier_leaf") or "")
        if coverage.get("covered") and prior_dossier_leaf:
            dossier = store.get_leaf(prior_dossier_leaf).get("payload") or {}
            try:
                validate_research_dossier(dossier, expected_identity={
                    key: dossier.get(key)
                    for key in ("candidate_leaf", "candidate_sha256", "entity_id", "as_of")
                })
            except ResearchEvidenceTimestampError as error:
                record_research_evidence_quarantine(
                    store, owner=owner, target_leaf=prior_dossier_leaf,
                    reason_code=error.to_dict()["reason_code"],
                    detected_at=_utc_now(),
                    source_refs=(error.source_url or f"dossier_leaf:{prior_dossier_leaf}",),
                    details={**error.to_dict(), "dossier_sha256": dossier.get("dossier_sha256")},
                )
                coverage = candidate_research_coverage(
                    store, owner=owner, candidate_leaf=candidate_leaf,
                    current_receipts=receipts,
                    required_source_ids=tuple(sorted(
                        monitor_sources_by_entity.get(str(candidate["entity_id"]), ())
                    )),
                    coverage_index=coverage_index,
                )
        coverage_leaf = record_candidate_research_coverage(
            store, owner=owner, coverage=coverage,
        )
        if coverage["covered"]:
            activations.append({
                "status": coverage["status"],
                "entity_id": candidate["entity_id"],
                "entity_kind": candidate["entity_kind"],
                "candidate_leaf": candidate_leaf,
                "coverage_leaf": coverage_leaf,
                "prior_dossier_leaf": coverage["prior_dossier_leaf"],
                "full_dossier_provider_call_required": False,
                "reassessment_provider_call_required": False,
            })
            continue
        if coverage["deep_research_activation"] == "await_reassessment":
            activations.append({
                "status": "awaiting_source_reassessment",
                "entity_id": candidate["entity_id"],
                "entity_kind": candidate["entity_kind"],
                "candidate_leaf": candidate_leaf,
                "coverage_leaf": coverage_leaf,
                "prior_dossier_leaf": coverage["prior_dossier_leaf"],
                "full_dossier_provider_call_required": False,
                "reassessment_provider_call_required": True,
            })
            continue
        if candidate_leaf not in existing:
            pending.append(candidate)
    routing_decision, learning_credit_assignment, current_research_learning = (
        _current_research_routing_inputs(root)
    )
    for candidate in pending:
        candidate_leaf = str(leaves.get(str(candidate.get("candidate_id") or "")) or "")
        if not candidate_leaf:
            continue
        requested = (
            ["balance_sheet_resilience", "cash_conversion", "earnings_durability",
             "earnings_power_margin", "growth_duration", "low_implied_growth",
             "price_implied_excess_return", "reinvestment_return"]
            if candidate.get("entity_kind") == "public_equity" else
            ["earnings_power_margin", "factor_exposure", "fees", "holdings_concentration",
             "liquidity", "low_implied_growth", "tax_fit"]
        )
        research_population = (
            "capital_candidate"
            if candidate.get("screen_status") == "qualified" else "strategy_learning"
        )
        work_prefix = (
            "qualified-research" if research_population == "capital_candidate"
            else "strategy-learning-research"
        )
        job_body = {
            "work_id": f"{work_prefix}:{run['run_id']}:{candidate['entity_id']}",
            "cycle_sha256": run["run_sha256"],
            "requested_measurements": requested,
            "activation": research_population,
            "research_population": research_population,
        }
        job = {**job_body, "job_sha256": stable_sha256(job_body)}
        request = compile_research_request(
            job=job, candidate=candidate, candidate_leaf=candidate_leaf,
            discovery_run=run,
            research_basis_sources=_research_basis_source_snapshot(
                root, str(candidate["entity_id"]),
            ),
            routing_decision=routing_decision,
            learning_credit_assignment=learning_credit_assignment,
            current_research_learning=current_research_learning,
            strategy_frontier=_strategy_frontier_for_candidate(
                strategy_frontiers, candidate,
            ),
            strategy_event_trigger=(strategy_event_triggers or {}).get(
                str(candidate["entity_id"])
            ),
        )
        request_leaf = record_agent_research_request(
            store, owner=owner, request=request,
        )
        path = root / "research_jobs" / "requests" / (
            f"{str(request['entity_id']).lower()}-{str(request['candidate_sha256'])[:12]}-"
            f"{str(request['request_sha256'])[:12]}.json"
        )
        _atomic_json(path, request)
        ensure_qualified_research_job(
            db_path=root / "state" / "research_jobs.sqlite3",
            events_path=root / "research_jobs" / "enrichment" / "events.jsonl",
            request=request,
        )
        existing.add(candidate_leaf)
        activations.append({
            "status": "research_requested",
            "entity_id": request["entity_id"], "entity_kind": request["entity_kind"],
            "candidate_leaf": candidate_leaf, "request_id": request["request_id"],
            "request_sha256": request["request_sha256"],
            "request_leaf": request_leaf,
            "request_path": path.relative_to(root).as_posix(),
            "research_population": research_population,
            "full_dossier_provider_call_required": True,
            "reassessment_provider_call_required": False,
        })
    return activations


def _compile_current_discovery_epoch(
    root: Path, config: Mapping[str, Any], policy: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Compile and record discovery from the already materialized source epoch."""
    source_lock_path = root / "state" / "source_refresh.lock"
    compile_lock_path = root / "state" / "discovery_compile.lock"
    compile_lock_path.parent.mkdir(parents=True, exist_ok=True)
    with (
        source_lock_path.open("a+b") as source_handle,
        compile_lock_path.open("a+b") as compile_handle,
    ):
        fcntl.flock(source_handle.fileno(), fcntl.LOCK_EX)
        fcntl.flock(compile_handle.fileno(), fcntl.LOCK_EX)
        source_run = _current_source_run(root) or {}
        existing = _read_json(root / "discovery" / "latest.json") or {}
        existing_record = _read_json(root / "discovery" / "latest_record.json") or {}
        existing_build = _read_json(root / "state" / "latest_build.json") or {}
        if (
            existing.get("compiler_version") == DISCOVERY_ENGINE_VERSION
            and existing.get("source_run_sha256") == source_run.get("run_sha256")
            and existing.get("policy_sha256") == stable_sha256(policy)
            and existing_record.get("run_sha256") == existing.get("run_sha256")
            and len(existing_record.get("candidate_leaves") or {})
            == int(existing.get("candidate_count") or -1)
            and existing_build.get("ok") is True
        ):
            return {**existing_build, "compile_reused": True}, existing, existing_record
        build = build_workspace(root, project_read_model=False)
        run, valuations = compile_discovery_run(
            workspace=root, workspace_config=config, policy=policy,
        )
        run = _materialize_valuation_artifacts(root, run, valuations)
        run_path = root / "discovery" / "runs" / f"{run['run_id']}.json"
        _atomic_json(run_path, run)
        record = record_discovery_run(
            GoldenStore(_store_path(root, config)),
            owner=str(config.get("owner") or "operator-paper-book"), run=run,
        )
        record_payload = {
            "schema": "jaggedthoughts-discovery-record-receipt-v1",
            "run_id": run["run_id"], "run_sha256": run["run_sha256"],
            "run_path": run_path.relative_to(root).as_posix(), **record,
        }
        _write_discovery_research_handoff(root, run, status="preparing")
        _atomic_json(root / "discovery" / "latest.json", run)
        _atomic_json(root / "discovery" / "latest_record.json", record_payload)
        return build, run, record_payload


def _write_discovery_research_handoff(
    root: Path, run: Mapping[str, Any], *, status: str,
    research_queue: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if status not in {"preparing", "complete"}:
        raise ValueError("discovery research handoff status must be preparing or complete")
    if status == "complete" and (
        not research_queue
        or research_queue.get("discovery_run_id") != run.get("run_id")
        or research_queue.get("discovery_run_sha256") != run.get("run_sha256")
    ):
        raise ValueError("research queue handoff does not bind the discovery epoch")
    body = {
        "schema": "jaggedthoughts-discovery-research-handoff-v1",
        "status": status,
        "discovery_run_id": run.get("run_id"),
        "discovery_run_sha256": run.get("run_sha256"),
        "recorded_at": _utc_now(),
        "research_enqueue_sha256": (
            stable_sha256(research_queue) if research_queue is not None else None
        ),
        "capital_authority": False,
    }
    receipt = {**body, "handoff_sha256": stable_sha256(body)}
    _atomic_json(root / "state" / "discovery_research_handoff.json", receipt)
    return receipt


def _open_rank_program_learning_block(
    root: Path, config: Mapping[str, Any], run: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze incumbent and challenger rank programs on this discovery population."""
    try:
        activated_at = _utc_now()
        primary = open_rank_program_tournament(
            root,
            owner=str(config.get("owner") or "operator-paper-book"),
            store_path=_store_path(root, config),
            discovery_run=run,
            opened_at=activated_at,
            sealed_at=activated_at,
        )
        try:
            diagnostic = open_rank_program_tournament(
                root,
                owner=str(config.get("owner") or "operator-paper-book"),
                store_path=_store_path(root, config),
                discovery_run=run,
                horizon_days=DIAGNOSTIC_HORIZON_DAYS,
                opened_at=activated_at,
                sealed_at=activated_at,
            )
        except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
            diagnostic = {
                "ok": False, "status": "deferred",
                "reason": f"{type(error).__name__}: {error}"[:1_000],
                "horizon_days": DIAGNOSTIC_HORIZON_DAYS,
                "capital_authority": False,
            }
        return {
            **primary,
            "diagnostic_horizon_days": DIAGNOSTIC_HORIZON_DAYS,
            "diagnostic_run": diagnostic,
        }
    except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
        return {
            "schema": "jaggedthoughts-rank-program-tournament-activation-v1",
            "ok": False,
            "status": "deferred",
            "reason": f"{type(error).__name__}: {error}"[:1_000],
            "discovery_run_id": run.get("run_id"),
            "automatic_policy_change": False,
            "portfolio_mutation_authority": False,
            "capital_authority": False,
        }


def _current_discovery_record(
    root: Path, run: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not run:
        return None
    record = _read_json(root / "discovery" / "latest_record.json")
    if (
        not record
        or record.get("run_id") != run.get("run_id")
        or record.get("run_sha256") != run.get("run_sha256")
        or len(record.get("candidate_leaves") or {})
        != int(run.get("candidate_count") or -1)
    ):
        return None
    return record


def _update_live_discovery_phase(root: Path, status: str, action: str) -> None:
    """Expose a long discovery phase only when this process owns the service."""
    path = root / "state" / "discovery_service.json"
    current = _read_json(path) or {}
    if (
        current.get("schema") != "jaggedthoughts-discovery-service-v1"
        or current.get("pid") != os.getpid()
    ):
        return
    _atomic_json(path, {
        **current,
        "status": status,
        "last_action": action,
        "phase_started_at": _utc_now(),
    })


def run_workspace_discovery(
    workspace: str | Path | None = None, *, force: bool = False, strict_sources: bool = False
) -> dict[str, Any]:
    """Execute one due discovery cycle from source refresh through immutable candidate leaves."""
    root, config = load_workspace_config(workspace)
    policy_path, policy = _discovery_policy(root, config)
    latest = _read_json(root / "discovery" / "latest.json")
    current_source_run = _current_source_run(root) or {}
    source_epoch_invalid = bool(
        (root / "data" / "latest_source_epoch.json").is_file()
        and not current_source_run
    )
    source_manifest_path = root / str(config.get("source_manifest") or "sources.yaml")
    market_flow_source_ids = _market_flow_shadow_refresh_source_ids(
        root, config,
        load_source_manifest(source_manifest_path)
        if source_manifest_path.is_file() else {"sources": []},
    )
    current_retrieval = str(current_source_run.get("retrieved_at") or "")
    current_heads = current_monitor_receipts(root)
    market_flow_shadow_refresh_due = bool(
        current_retrieval and any(
            str((current_heads.get(source_id) or {}).get("retrieved_at") or "")
            != current_retrieval
            for source_id in market_flow_source_ids
        )
    )
    schedule = discovery_schedule_status(policy=policy, latest_run=latest)
    # Discovery force bypasses the deep-analysis cadence. Catalog/scout refresh
    # has its own freshness policy and explicit ``scout-scheduled --force`` action.
    scout_cycle = run_workspace_scheduled_market_scouts(root)
    if not bool(policy.get("enabled", True)):
        return {"schema": "jaggedthoughts-discovery-action-v1", "ok": True, "status": "disabled", "schedule": schedule, "market_scout_cycle": scout_cycle}
    scout_completed = scout_cycle.get("status") == "completed"
    compiler_repair_due = bool(
        latest and latest.get("compiler_version") != DISCOVERY_ENGINE_VERSION
    )
    handoff_repair_due = bool(
        latest and not validated_discovery_research_handoff(root, latest)
    )
    record_repair_due = bool(latest and not _current_discovery_record(root, latest))
    source_epoch_compile_due = bool(
        latest and current_source_run.get("run_sha256")
        and latest.get("source_run_sha256") != current_source_run.get("run_sha256")
    )
    projection_repair_due = (
        compiler_repair_due or handoff_repair_due or record_repair_due
        or source_epoch_compile_due
    )
    # A ready fund batch participates in the next discovery epoch; it does not
    # override the daily source/compiler cadence on every service heartbeat.
    full_cycle_due = (
        force or schedule["due"] or scout_completed or source_epoch_invalid
        or market_flow_shadow_refresh_due
    )
    if not full_cycle_due and not projection_repair_due:
        return {"schema": "jaggedthoughts-discovery-action-v1", "ok": True, "status": "not_due", "schedule": schedule, "latest_run": latest, "market_scout_cycle": scout_cycle}
    repair_before_full_cycle = bool(
        not force and (
            source_epoch_compile_due
            or handoff_repair_due
            and not compiler_repair_due and not record_repair_due
        )
    )
    if not full_cycle_due or repair_before_full_cycle:
        with _DISCOVERY_LOCK, _ENRICHMENT_LOCK:
            phase_seconds: dict[str, float] = {}
            phase_started = time.perf_counter()
            if compiler_repair_due or record_repair_due or source_epoch_compile_due:
                build, run, record_payload = _compile_current_discovery_epoch(
                    root, config, policy,
                )
            else:
                build = _read_json(root / "state" / "latest_build.json") or {}
                run = dict(latest or {})
                record_payload = _current_discovery_record(root, run) or {}
            phase_seconds["compile_discovery_epoch"] = round(
                time.perf_counter() - phase_started, 3,
            )
            _write_discovery_research_handoff(root, run, status="preparing")
            phase_started = time.perf_counter()
            qualified_requests = _ensure_qualified_research_requests(
                root, config, run, record_payload,
            )
            phase_seconds["compile_research_requests"] = round(
                time.perf_counter() - phase_started, 3,
            )
            phase_started = time.perf_counter()
            research_queue = enqueue_research_request_jobs(root)
            phase_seconds["compile_research_queue"] = round(
                time.perf_counter() - phase_started, 3,
            )
            discovery_research_handoff = _write_discovery_research_handoff(
                root, run, status="complete", research_queue=research_queue,
            )
            phase_started = time.perf_counter()
            rank_program_learning = _open_rank_program_learning_block(
                root, config, run,
            )
            cached_read_model = _read_json(root / "state" / "read_model.json") or {}
            cached_run = (
                (cached_read_model.get("discovery") or {}).get("latest_run") or {}
            )
            if cached_run.get("run_sha256") == run.get("run_sha256"):
                read_model_body = {
                    key: value for key, value in cached_read_model.items()
                    if key != "read_model_sha256"
                }
                read_model_body["discovery_research_handoff"] = discovery_research_handoff
                read_model_body["rank_program_tournament"] = (
                    rank_program_tournament_status(root)
                )
                read_model = {
                    **read_model_body,
                    "read_model_sha256": stable_sha256(read_model_body),
                }
            else:
                read_model = build_read_model(root)
            _atomic_json(root / "state" / "read_model.json", read_model)
            phase_seconds["publish_learning_and_read_model"] = round(
                time.perf_counter() - phase_started, 3,
            )
        return {
            "schema": "jaggedthoughts-discovery-action-v1", "ok": True,
            "status": "projection_repaired", "forced": False,
            "repair_reasons": [
                reason for reason, present in (
                    ("compiler_drift", compiler_repair_due),
                    ("research_handoff_incomplete", handoff_repair_due),
                    ("discovery_record_incomplete", record_repair_due),
                    ("source_epoch_advanced", source_epoch_compile_due),
                ) if present
            ],
            "policy_path": policy_path.relative_to(root).as_posix(),
            "build_ok": bool(build.get("ok")), "market_scout_cycle": scout_cycle,
            "qualified_research_requests": qualified_requests,
            "research_queue": research_queue,
            "discovery_research_handoff": discovery_research_handoff,
            "rank_program_learning": rank_program_learning,
            "phase_seconds": phase_seconds,
            "run": run, "record": record_payload, "read_model": read_model,
        }
    with _DISCOVERY_LOCK, _ENRICHMENT_LOCK:
        phase_seconds: dict[str, float] = {}
        _update_live_discovery_phase(
            root, "refreshing_public_sources",
            "refresh_declared_sources_then_compile_epoch",
        )
        phase_started = time.perf_counter()
        enrichment_context = _prepare_autonomous_enrichment(
            root=root, config=config, scout_cycle=scout_cycle,
        )
        phase_seconds["prepare_enrichment"] = round(
            time.perf_counter() - phase_started, 3,
        )
        lease_heartbeat = _start_enrichment_lease_heartbeat(
            root, (enrichment_context, enrichment_context.get("broad_fund_acquisition") or {}),
        )
        try:
            phase_started = time.perf_counter()
            source_run = refresh_workspace_sources(
                root, strict=strict_sources,
                source_ids=enrichment_context.get("refresh_source_ids") or None,
            )
            phase_seconds["refresh_public_sources"] = round(
                time.perf_counter() - phase_started, 3,
            )
            _update_live_discovery_phase(
                root, "compiling_discovery_epoch",
                "compile_ranked_candidates_from_completed_source_epoch",
            )
            phase_started = time.perf_counter()
            build, run, record_payload = _compile_current_discovery_epoch(
                root, config, policy,
            )
            phase_seconds["compile_discovery_epoch"] = round(
                time.perf_counter() - phase_started, 3,
            )
            _write_discovery_research_handoff(root, run, status="preparing")
            _broad_scout, broad_plan = _compile_workspace_broad_fund_acquisition(
                root, config, compiled_at=str(source_run.get("as_of") or _utc_now()),
            )
        except Exception as error:
            _stop_enrichment_lease_heartbeat(lease_heartbeat)
            broad_context = enrichment_context.get("broad_fund_acquisition") or {}
            _finish_broad_fund_acquisition(
                root=root, context=broad_context, post_plan=None, fatal_error=str(error),
            )
            _finalize_autonomous_enrichment(
                root=root, context=enrichment_context,
                source_run=locals().get("source_run"), discovery_run=None,
                discovery_record=None, fatal_error=str(error),
            )
            raise
        _stop_enrichment_lease_heartbeat(lease_heartbeat)
        broad_context = enrichment_context.get("broad_fund_acquisition") or {}
        _finish_broad_fund_acquisition(
            root=root, context=broad_context, post_plan=broad_plan,
        )
        enrichment = _finalize_autonomous_enrichment(
            root=root, context=enrichment_context, source_run=source_run,
            discovery_run=run, discovery_record=record_payload,
        )
        _update_live_discovery_phase(
            root, "publishing_research_handoff",
            "bind_qualified_requests_and_durable_queue",
        )
        phase_started = time.perf_counter()
        qualified_requests = _ensure_qualified_research_requests(
            root, config, run, record_payload,
        )
        phase_seconds["compile_research_requests"] = round(
            time.perf_counter() - phase_started, 3,
        )
        phase_started = time.perf_counter()
        research_queue = enqueue_research_request_jobs(root)
        phase_seconds["compile_research_queue"] = round(
            time.perf_counter() - phase_started, 3,
        )
        discovery_research_handoff = _write_discovery_research_handoff(
            root, run, status="complete", research_queue=research_queue,
        )
        rank_program_learning = _open_rank_program_learning_block(
            root, config, run,
        )
        _update_live_discovery_phase(
            root, "publishing_read_model",
            "project_completed_epoch_for_workbench",
        )
        phase_started = time.perf_counter()
        read_model = build_read_model(root)
        _atomic_json(root / "state" / "read_model.json", read_model)
        phase_seconds["publish_learning_and_read_model"] = round(
            time.perf_counter() - phase_started, 3,
        )
        broad_fund_acquisition = read_model.get("broad_fund_acquisition") or {}
    return {
        "schema": "jaggedthoughts-discovery-action-v1", "ok": True, "status": "completed",
        "forced": force, "policy_path": policy_path.relative_to(root).as_posix(),
        "source_run_ok": bool(source_run.get("ok")), "build_ok": bool(build.get("ok")),
        "market_scout_cycle": scout_cycle,
        "autonomous_enrichment": enrichment,
        "broad_fund_acquisition": broad_fund_acquisition,
        "qualified_research_requests": qualified_requests,
        "research_queue": research_queue,
        "discovery_research_handoff": discovery_research_handoff,
        "rank_program_learning": rank_program_learning,
        "phase_seconds": phase_seconds,
        "run": run, "record": record_payload, "read_model": read_model,
    }


def run_workspace_autonomous_enrichment(
    workspace: str | Path | None = None, *, strict_sources: bool = False,
) -> dict[str, Any]:
    """Force one scout -> budgeted enrichment -> deep discovery transaction."""
    return run_workspace_discovery(
        workspace, force=True, strict_sources=strict_sources,
    )


def _periodic_activation_status(
    root: Path, *, action: Mapping[str, Any], checked_at: str,
) -> dict[str, Any]:
    """Project the existing discovery and subscription consumers as one paper lane."""
    research = research_agent_status(root)
    queue = research.get("queue") if isinstance(research.get("queue"), Mapping) else {}
    jobs = [row for row in queue.get("jobs") or () if isinstance(row, Mapping)]
    queued = [row for row in jobs if row.get("status") in {"queued", "claimed"}]
    completed = [
        row for row in jobs
        if row.get("status") == "done" and (row.get("payload") or {}).get("completed_at")
    ]
    last_job = max(
        completed, key=lambda row: str((row.get("payload") or {}).get("completed_at")),
        default=None,
    )
    latest_run = action.get("run") or action.get("latest_run") or {}
    latest_record = action.get("record") or _read_json(root / "discovery" / "latest_record.json") or {}
    schedule = action.get("schedule") if isinstance(action.get("schedule"), Mapping) else {}
    budget = (
        research.get("daily_dispatch_budget")
        if isinstance(research.get("daily_dispatch_budget"), Mapping) else {}
    )
    blockers: list[str] = []
    if not research.get("enabled"):
        blockers.append("subscription_research_disabled")
    if not research.get("runtime_executable"):
        blockers.append("subscription_runtime_unavailable")
    if queued and budget.get("exhausted"):
        blockers.append("daily_subscription_dispatch_budget_exhausted")
    service = research.get("service") if isinstance(research.get("service"), Mapping) else {}
    if service.get("status") in {"error", "stale"}:
        blockers.append(f"subscription_research_service_{service['status']}")
    next_job = queued[0] if queued else None
    next_kind = (
        "subscription_research" if next_job else
        "public_market_discovery"
    )
    budget_reset_at = None
    if next_job and budget.get("exhausted"):
        checked = timestamp_key(checked_at).astimezone(timezone.utc)
        budget_reset_at = (checked.replace(
            hour=0, minute=0, second=0, microsecond=0,
        ) + timedelta(days=1)).isoformat(timespec="seconds").replace("+00:00", "Z")
    body = {
        "schema": "jaggedthoughts-periodic-investment-activation-v1",
        "checked_at": checked_at,
        "status": "blocked" if blockers else ("research_pending" if next_job else "waiting"),
        "last_activation": {
            "discovery_action": action.get("status"),
            "discovery_run_id": latest_run.get("run_id") if isinstance(latest_run, Mapping) else None,
            "discovery_completed_at": (
                latest_run.get("completed_at") if isinstance(latest_run, Mapping) else None
            ),
            "research_work_id": last_job.get("work_id") if last_job else None,
            "research_completed_at": (
                (last_job.get("payload") or {}).get("completed_at") if last_job else None
            ),
        },
        "next_activation": {
            "kind": next_kind,
            "at": budget_reset_at if next_job else schedule.get("next_due_at"),
            "work_id": next_job.get("work_id") if next_job else None,
            "job_kind": next_job.get("kind") if next_job else None,
        },
        "blocked_activation": {
            "work_id": next_job.get("work_id") if next_job else None,
            "reasons": blockers,
        } if blockers else None,
        "queue": dict(queue.get("by_status") or {}),
        "source_boundary": {
            "contract": "cached_public_bytes_with_observed_and_available_times",
            "discovery_run_sha256": (
                latest_run.get("run_sha256") if isinstance(latest_run, Mapping) else None
            ),
            "candidate_leaf_count": len(latest_record.get("candidate_leaves") or {}),
            "research_transport": research.get("transport"),
            "runtime": research.get("runtime"),
        },
        "authority": "paper_research_only",
        "capital_authority": False,
    }
    return {**body, "activation_sha256": stable_sha256(body)}


def run_workspace_discovery_service(
    workspace: str | Path | None = None, *, poll_seconds: float = 300.0,
    once: bool = False, stop_event: Event | None = None,
) -> dict[str, Any]:
    """Maintain the due-check loop and a small inspectable service heartbeat."""
    if poll_seconds < 5 and not once:
        raise ValueError("discovery service poll_seconds must be at least five")
    root, config = load_workspace_config(workspace)
    stopper = stop_event or Event()
    started_at = _utc_now()
    heartbeat: dict[str, Any] = {}
    while not stopper.is_set():
        checked_at = _utc_now()
        transition_pending = _composite_epoch_transition_pending(root)
        heartbeat = {
            "schema": "jaggedthoughts-discovery-service-v1", "ok": True,
            "status": (
                "publishing_completed_discovery_epoch"
                if transition_pending else "checking_due_work"
            ),
            "last_action": (
                "compile_source_epoch_then_publish_research_handoff"
                if transition_pending else None
            ),
            "started_at": started_at,
            "checked_at": checked_at, "pid": os.getpid(),
            "starter": "forensic_workbench_server_or_investment_cli",
            "stops_with_process": True, "poll_seconds": poll_seconds,
            "capital_authority": False,
        }
        _atomic_json(root / "state" / "discovery_service.json", heartbeat)
        try:
            action = run_workspace_discovery(root, force=False)
            fund_lookthrough = run_workspace_fund_lookthrough_acquisition(
                root, force=False,
            )
            fund_acquisition = (
                action.get("broad_fund_acquisition")
                if isinstance(action.get("broad_fund_acquisition"), Mapping)
                else _broad_fund_acquisition_status(
                    root, next_due_at=(action.get("schedule") or {}).get("next_due_at"),
                )
            )
            heartbeat = {
                "schema": "jaggedthoughts-discovery-service-v1", "ok": True,
                "status": "running" if not once else "checked_once",
                "started_at": started_at, "checked_at": checked_at,
                "pid": os.getpid(), "starter": "forensic_workbench_server_or_investment_cli",
                "stops_with_process": True,
                "poll_seconds": poll_seconds, "last_action": action.get("status"),
                "last_run_id": (((action.get("run") or action.get("latest_run") or {}).get("run_id"))
                                if isinstance(action.get("run") or action.get("latest_run"), Mapping) else None),
                "last_enrichment_status": (
                    (action.get("autonomous_enrichment") or {}).get("status")
                    if isinstance(action.get("autonomous_enrichment"), Mapping) else None
                ),
                "last_evidence_ready_count": (
                    (action.get("autonomous_enrichment") or {}).get("evidence_ready_count")
                    if isinstance(action.get("autonomous_enrichment"), Mapping) else 0
                ),
                "last_phase_seconds": action.get("phase_seconds"),
                "broad_fund_acquisition_status": fund_acquisition.get("status"),
                "broad_fund_acquisition_next_due_at": fund_acquisition.get("next_due_at"),
                "fund_lookthrough": {
                    key: fund_lookthrough.get(key) for key in (
                        "status", "next_action", "next_due_at", "selected_entity_ids",
                        "current_plan_sha256", "last_acquisition_sha256",
                        "source_run_sha256", "source_selection_sha256",
                        "capital_authority",
                    )
                },
                "periodic_activation": _periodic_activation_status(
                    root, action=action, checked_at=checked_at,
                ),
                "capital_authority": False,
            }
        except Exception as error:  # noqa: BLE001 - heartbeat must expose service failure.
            heartbeat = {
                "schema": "jaggedthoughts-discovery-service-v1", "ok": False,
                "status": "error", "started_at": started_at, "checked_at": checked_at,
                "pid": os.getpid(), "starter": "forensic_workbench_server_or_investment_cli",
                "stops_with_process": True,
                "poll_seconds": poll_seconds, "error": str(error),
            }
        _atomic_json(root / "state" / "discovery_service.json", heartbeat)
        if once:
            return heartbeat
        stopper.wait(poll_seconds)
    heartbeat = {**heartbeat, "status": "stopped", "stopped_at": _utc_now()}
    _atomic_json(root / "state" / "discovery_service.json", heartbeat)
    return heartbeat


def start_workspace_discovery_service(
    workspace: str | Path | None = None, *, poll_seconds: float = 300.0
) -> Thread:
    """Start at most one daemon discovery service in the current process."""
    global _DISCOVERY_SERVICE
    if _DISCOVERY_SERVICE is not None and _DISCOVERY_SERVICE.is_alive():
        return _DISCOVERY_SERVICE
    _DISCOVERY_STOP.clear()
    _DISCOVERY_SERVICE = Thread(
        target=run_workspace_discovery_service,
        kwargs={"workspace": workspace, "poll_seconds": poll_seconds, "stop_event": _DISCOVERY_STOP},
        name="jaggedthoughts-discovery", daemon=True,
    )
    _DISCOVERY_SERVICE.start()
    return _DISCOVERY_SERVICE


def seed_workspace_public_equity_draft(
    workspace: str | Path | None = None, **inputs: Any
) -> dict[str, Any]:
    """Create and compile one source-bound equity draft for review in the UI."""
    root, config = load_workspace_config(workspace)
    entity_id = str(inputs.get("entity_id") or "").upper()
    enrollment: dict[str, Any] | None = None
    if not public_equity_is_enrolled(root, entity_id):
        enrollment = enroll_public_equity(root, ticker=entity_id)
        refresh_workspace_sources(root, strict=False)
    draft = create_public_equity_draft(root, **inputs)
    store = GoldenStore(_store_path(root, config))
    funnel_leaves = [
        record_funnel_transition(
            store, owner=str(config.get("owner") or "operator-paper-book"), receipt=row,
        )
        for row in draft.get("funnel_transitions", [])
    ]
    build = build_workspace(root)
    return {
        **draft,
        "enrollment": enrollment,
        "funnel_transition_leaves": funnel_leaves,
        "build_ok": bool(build.get("ok")),
        "read_model": build["read_model"],
    }


def submit_workspace_research_dossier(
    dossier_path: str, workspace: str | Path | None = None, *,
    refresh_projection: bool = True,
) -> dict[str, Any]:
    """Validate and record one agent dossier without changing capital authority."""
    root, config = load_workspace_config(workspace)
    owner = str(config.get("owner") or "operator-paper-book")
    dossier_file = (root / require_text(dossier_path, "dossier_path")).resolve()
    try:
        dossier_file.relative_to(root)
    except ValueError as error:
        raise ValueError("candidate dossier path escapes the investment workspace") from error
    dossier_payload = _read_json(dossier_file)
    if not dossier_payload:
        raise ValueError("candidate dossier does not exist or is not a JSON object")
    request_id = require_text(dossier_payload.get("request_id"), "candidate dossier request_id")
    request_sha = require_text(
        dossier_payload.get("request_sha256"), "candidate dossier request_sha256",
    )
    requests: list[tuple[Path, dict[str, Any]]] = []
    for path in (root / "research_jobs" / "requests").glob("*.json"):
        request = _read_json(path)
        if (
            request and request.get("request_id") == request_id
            and request.get("request_sha256") == request_sha
        ):
            requests.append((path, request))
    if len(requests) != 1:
        raise ValueError("candidate dossier must bind exactly one immutable research request")
    request_path, request = requests[0]
    currency = research_request_currency(
        request, latest_discovery_candidate_index(root),
    )
    if not currency["qualitative_research_current"]:
        raise ValueError("candidate dossier request is superseded by the current discovery identity")
    store = GoldenStore(_store_path(root, config))
    candidate_leaf = require_text(request.get("candidate_leaf"), "research request candidate_leaf")
    candidate = store.get_leaf(candidate_leaf)
    candidate_payload = candidate.get("payload") or {}
    expected_identity = {
        "candidate_leaf": candidate_leaf,
        "candidate_sha256": candidate_payload.get("candidate_sha256"),
        "entity_id": candidate_payload.get("entity_id"),
        "as_of": candidate_payload.get("as_of"),
    }
    normalized = validate_research_dossier(
        dossier_payload, expected_identity=expected_identity, request=request,
        materialized_at=datetime.fromtimestamp(
            dossier_file.stat().st_mtime, tz=timezone.utc,
        ).isoformat(timespec="seconds").replace("+00:00", "Z"),
    )
    request_leaves: list[str] = []
    for row in store.list_leaves(owner=owner, object_kind="agent_research_request", limit=10_000):
        leaf_sha = str(row.get("leaf_sha256") or "")
        leaf = store.get_leaf(leaf_sha)
        if (leaf.get("payload") or {}).get("request_sha256") == request_sha:
            request_leaves.append(leaf_sha)
    if len(request_leaves) != 1:
        raise ValueError("candidate dossier request has no unique golden-store leaf")
    require_research_parent_ready(
        db_path=root / "state" / "research_jobs.sqlite3", request=request,
    )
    relative = dossier_file.relative_to(root).as_posix()
    _atomic_json(dossier_file, normalized)
    dossier_leaf = record_candidate_research_dossier(
        store, owner=owner, dossier=normalized, request_leaf=request_leaves[0],
    )
    monitor_subscription_leaf = record_monitor_subscription(
        store, root=root, owner=owner, dossier_leaf=dossier_leaf, dossier=normalized,
        baseline_receipts={
            str(row.get("source_id") or ""): dict(row)
            for row in request.get("research_basis_source_snapshot") or ()
            if isinstance(row, Mapping) and row.get("source_id")
        },
    )
    mark_job_researched(
        db_path=root / "state" / "research_jobs.sqlite3",
        events_path=root / "research_jobs" / "enrichment" / "events.jsonl",
        request=request,
        dossier_path=relative,
        dossier_leaf=dossier_leaf,
        dossier_sha256=str(normalized["dossier_sha256"]),
    )
    coverage = candidate_research_coverage(
        store, owner=owner, candidate_leaf=candidate_leaf,
        current_receipts=current_monitor_receipts(root),
        required_source_ids=material_monitor_source_ids(root, str(normalized["entity_id"])),
    )
    coverage_leaf = record_candidate_research_coverage(
        store, owner=owner, coverage=coverage,
    )
    enqueue = enqueue_research_request_jobs(root) if refresh_projection else {
        "status": "deferred_until_research_claim_closes",
    }
    fund_proposal_audit = None
    if (
        refresh_projection
        and
        request.get("entity_kind") == "public_fund"
        and request.get("screen_status") == "qualified"
    ):
        fund_proposal_audit = compile_workspace_fund_proposals(root)
        _atomic_json(
            root / "paper_proposals" / "funds" / "latest.json",
            fund_proposal_audit,
        )
    fund_proposal_row = next((
        row for row in (fund_proposal_audit or {}).get("rows") or ()
        if row.get("candidate_leaf") == candidate_leaf
    ), None)
    read_model = (
        build_read_model(root) if refresh_projection else read_cached_read_model(root)
    )
    if refresh_projection:
        _atomic_json(root / "state" / "read_model.json", read_model)
    return {
        "schema": "jaggedthoughts-research-dossier-submission-v1",
        "ok": True,
        "status": "researched",
        "entity_id": normalized["entity_id"],
        "screen_status": request.get("screen_status"),
        "candidate_leaf": candidate_leaf,
        "request_path": request_path.relative_to(root).as_posix(),
        "request_leaf": request_leaves[0],
        "dossier_path": relative,
        "dossier_sha256": normalized["dossier_sha256"],
        "dossier_leaf": dossier_leaf,
        "monitor_subscription_leaf": monitor_subscription_leaf,
        "coverage_leaf": coverage_leaf,
        "coverage_status": coverage["status"],
        "enqueue": enqueue,
        "projection_refresh_deferred": not refresh_projection,
        "next_activation": (
            "draft_candidate" if request.get("screen_status") == "qualified"
            and request.get("entity_kind") == "public_equity"
            else "operator_review_inactive_fund_proposal"
            if (fund_proposal_row or {}).get("activation_eligible")
            else "repair_fund_proposal_evidence"
            if fund_proposal_audit is not None
            else "monitor_next_source_epoch" if request.get("entity_kind") == "public_fund"
            else request.get("next_activation")
        ),
        "fund_proposal_audit_sha256": (
            fund_proposal_audit.get("audit_sha256") if fund_proposal_audit else None
        ),
        "capital_authority": False,
        "read_model": read_model,
    }


def compile_workspace_fund_paper_audit(
    workspace: str | Path | None = None, *, compiled_at: str | None = None,
) -> dict[str, Any]:
    """Persist the current inactive fund-proposal audit and refresh its projections."""
    root, _ = load_workspace_config(workspace)
    audit = compile_workspace_fund_proposals(root, compiled_at=compiled_at)
    relative = Path("paper_proposals/funds/latest.json")
    _atomic_json(root / relative, audit)
    readiness = compile_workspace_allocation_readiness(root)
    _atomic_json(root / "allocation" / "latest.json", readiness)
    _atomic_json(root / "state" / "read_model.json", build_read_model(root))
    return {
        "schema": "jaggedthoughts-public-fund-paper-proposal-audit-action-v1",
        "ok": True, "status": "compiled", "artifact_path": relative.as_posix(),
        "audit": audit, "readiness_sha256": readiness["readiness_sha256"],
        "capital_authority": False, "brokerage_authority": False,
    }


def draft_workspace_discovery_candidate(
    candidate_leaf: str,
    *,
    thesis_claim: str | None = None,
    entity_name: str | None = None,
    base_growth: float | None = None,
    terminal_growth: float | None = None,
    dossier_path: str | None = None,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Turn one immutable equity candidate leaf into a reviewable, still-inactive draft."""
    root, config = load_workspace_config(workspace)
    owner = str(config.get("owner") or "operator-paper-book")
    store = GoldenStore(_store_path(root, config))
    leaf = store.get_leaf(require_text(candidate_leaf, "candidate_leaf"))
    if leaf.get("owner") != owner or leaf.get("object_kind") != "discovery_candidate":
        raise ValueError("candidate leaf is not a discovery candidate owned by this workspace")
    payload = leaf.get("payload")
    if not isinstance(payload, Mapping) or payload.get("entity_kind") != "public_equity":
        raise ValueError("draft-candidate currently supports public-equity candidate leaves")
    if payload.get("screen_status") != "qualified":
        raise ValueError("candidate leaf is not qualified; research the named gap or use an explicit operator seed")
    source_run = _current_source_run(root)
    if not source_run or str(payload.get("as_of")) != str(source_run.get("as_of")):
        raise ValueError("candidate leaf is not from the current source epoch; run discovery again")
    beta_receipt = payload.get("beta_receipt") if isinstance(payload.get("beta_receipt"), Mapping) else {}
    if beta_receipt.get("status") == "estimated":
        analysis = beta_receipt.get("analysis") if isinstance(beta_receipt.get("analysis"), Mapping) else {}
        beta = float(((analysis.get("coefficients") or {}).get("betas") or {}).get("market"))
    else:
        beta = float(beta_receipt.get("value", 1.0))
    entity_id = str(payload["entity_id"])
    dossier_relative = ""
    dossier: Mapping[str, Any] | None = None
    if dossier_path:
        dossier_file = (root / dossier_path).resolve()
        try:
            dossier_file.relative_to(root)
        except ValueError as error:
            raise ValueError("candidate dossier path escapes the investment workspace") from error
        dossier_payload = _read_json(dossier_file)
        expected_identity = {
            "candidate_leaf": candidate_leaf,
            "candidate_sha256": payload.get("candidate_sha256"),
            "entity_id": entity_id,
            "as_of": payload.get("as_of"),
        }
        dossier = validate_research_dossier(
            dossier_payload, expected_identity=expected_identity,
            materialized_at=datetime.fromtimestamp(
                dossier_file.stat().st_mtime, tz=timezone.utc,
            ).isoformat(timespec="seconds").replace("+00:00", "Z"),
        )
        dossier_relative = dossier_file.relative_to(root).as_posix()
    dossier_thesis = ""
    if dossier:
        thesis_block = dossier.get("thesis")
        dossier_thesis = str(thesis_block.get("claim") if isinstance(thesis_block, Mapping) else thesis_block or "").strip()
    claim = str(thesis_claim or dossier_thesis).strip()
    if not claim:
        raise ValueError("draft-candidate requires a thesis or a dossier thesis.claim")
    if thesis_claim and dossier_thesis and thesis_claim.strip() != dossier_thesis:
        raise ValueError("CLI thesis and dossier thesis.claim differ")
    assumptions = dossier.get("valuation_assumptions") if dossier and isinstance(dossier.get("valuation_assumptions"), Mapping) else {}
    growth_value = float(base_growth if base_growth is not None else assumptions.get("base_growth", 0.03))
    terminal_value = float(terminal_growth if terminal_growth is not None else assumptions.get("terminal_growth", 0.025))
    origin = {
        "schema": "jaggedthoughts-discovery-origin-v1",
        "candidate_leaf": candidate_leaf,
        "candidate_sha256": payload.get("candidate_sha256"),
        "candidate_id": payload.get("candidate_id"),
        "entity_id": entity_id,
        "as_of": payload.get("as_of"),
    }
    draft = create_public_equity_draft(
        root, entity_id=entity_id, entity_name=entity_name or str(payload.get("name") or entity_id),
        thesis_claim=claim, beta=beta, base_growth=growth_value,
        terminal_growth=terminal_value, overwrite=True, discovery_origin=origin,
        research_dossier_path=dossier_relative or None,
    )
    funnel_leaves = [
        record_funnel_transition(store, owner=owner, receipt=row)
        for row in draft.get("funnel_transitions", [])
    ]
    build = build_workspace(root)
    matching = [
        row for row in build.get("profile_statuses", [])
        if row.get("profile_id") == draft["profile_id"] and row.get("status") in {"compiled", "frozen_existing"}
    ]
    if len(matching) != 1:
        raise ValueError("candidate draft did not compile into exactly one profile")
    decision_leaf = str((matching[0].get("golden_leaves") or {}).get("decision") or "")
    if not decision_leaf:
        raise ValueError("candidate draft compilation produced no decision leaf")
    lineage_edge = store.append_edge(GoldenEdge(decision_leaf, candidate_leaf, "derived_from"))
    read_model = build_read_model(root)
    _atomic_json(root / "state" / "read_model.json", read_model)
    return {
        **draft, "candidate_leaf": candidate_leaf,
        "funnel_transition_leaves": funnel_leaves,
        "decision_leaf": decision_leaf, "candidate_lineage_edge": lineage_edge,
        "build_ok": bool(build.get("ok")), "read_model": read_model,
    }


def enroll_workspace_public_equity(
    ticker: str, workspace: str | Path | None = None
) -> dict[str, Any]:
    """Enroll a ticker, consume the enlarged public-source manifest, and rebuild screens."""
    root, _config = load_workspace_config(workspace)
    enrollment = enroll_public_equity(root, ticker=ticker)
    source_run = refresh_workspace_sources(root, strict=False)
    build = build_workspace(root)
    return {
        **enrollment, "source_run_ok": bool(source_run.get("ok")),
        "build_ok": bool(build.get("ok")), "read_model": build["read_model"],
    }


def hydrate_workspace_strategy_cohort(
    workspace: str | Path | None = None, *, limit: int = 8,
) -> dict[str, Any]:
    """Enroll the selected strategy peers and acquire their public filing histories."""
    if limit < 1 or limit > 50:
        raise ValueError("strategy cohort hydration limit must be in [1, 50]")
    root, _config = load_workspace_config(workspace)
    plan = _read_json(root / "institutional_learning" / "strategy_cohorts" / "latest.json")
    if not plan:
        enqueue_research_request_jobs(root)
        plan = _read_json(root / "institutional_learning" / "strategy_cohorts" / "latest.json") or {}
    ranked_requests = sorted(
        (row for row in plan.get("requests") or () if row.get("peer_entity_id")),
        key=lambda row: (
            row.get("search_role") != "cross_environment_transfer_discovery",
            str(row.get("industry_id") or ""), str(row.get("peer_entity_id") or ""),
        ),
    )
    tickers = list(dict.fromkeys(
        str(row["peer_entity_id"]).upper() for row in ranked_requests
    ))[:limit]
    if not tickers:
        return {
            "schema": "jaggedthoughts-strategy-cohort-acquisition-v1",
            "ok": True, "status": "no_selected_peers", "selected_tickers": [],
            "capital_authority": False,
        }
    new_tickers = [ticker for ticker in tickers if not public_equity_is_enrolled(root, ticker)]
    enrollment = enroll_public_equities(root, tickers=new_tickers) if new_tickers else {
        "schema": "jaggedthoughts-public-equity-enrollment-batch-v1",
        "enrollments": [], "registry_source_calls": 0,
        "added_source_count": 0, "added_signal_count": 0,
    }
    manifest = load_source_manifest(root / "sources.yaml")
    source_ids = sorted({
        str(row["id"]) for row in manifest.get("sources") or ()
        if isinstance(row, Mapping)
        and str(row.get("entity_id") or "").upper() in set(tickers)
        and row.get("adapter") in {"sec_companyfacts", "sec_submissions"}
    })
    source_run = refresh_workspace_sources(root, strict=False, source_ids=source_ids) if source_ids else None
    build = build_workspace(root)
    body = {
        "schema": "jaggedthoughts-strategy-cohort-acquisition-v1",
        "plan_sha256": plan.get("plan_sha256"),
        "selected_tickers": tickers,
        "newly_enrolled_tickers": new_tickers,
        "source_ids": source_ids,
        "source_run_as_of": (source_run or {}).get("as_of"),
        "source_run_ok": bool((source_run or {}).get("ok", not source_ids)),
        "build_ok": bool(build.get("ok")),
        "capital_authority": False,
    }
    receipt = {**body, "acquisition_sha256": stable_sha256(body)}
    _atomic_json(root / "institutional_learning" / "strategy_cohorts" / "acquisition-latest.json", receipt)
    return {**receipt, "ok": True, "status": "completed", "enrollment": enrollment, "read_model": build["read_model"]}


def _hydrate_workspace_strategy_event_research(
    root: Path, config: Mapping[str, Any], shadow: Mapping[str, Any], *, limit: int = 3,
) -> dict[str, Any]:
    """Turn observed strategy moves into bounded source refresh and typed discovery states."""

    receipt_path = (
        root / "institutional_learning" / "strategy_path_shadow"
        / "event-research-acquisition-latest.json"
    )

    def reprioritize(event_rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
        """Bind event information value to research attention, never security rank."""
        by_sha: dict[str, dict[str, Any]] = {}
        for raw in event_rows:
            row = dict(raw)
            declared = str(row.pop("research_request_sha256", ""))
            row.pop("research_priority_rank", None)
            if declared and stable_sha256(row) == declared:
                by_sha[declared] = dict(raw)
        if not by_sha:
            return []
        updates = []
        connection = work_queue.connect(str(root / "state" / "research_jobs.sqlite3"))
        try:
            for queued in work_queue.list_items(connection, status="queued", limit=10_000):
                payload = queued.get("payload") or {}
                request_path = root / str(payload.get("request_path") or "")
                request = _read_json(request_path) if request_path.is_file() else None
                trigger = (
                    request.get("strategy_event_trigger")
                    if isinstance(request, Mapping) else None
                )
                event_sha = str(
                    (trigger or {}).get("event_research_request_sha256") or ""
                )
                event = by_sha.get(event_sha)
                if not event:
                    continue
                priority = research_rank_priority({
                    **request,
                    "strategy_event_trigger": {**dict(trigger), **event},
                })
                if int(queued.get("priority") or 0) == priority:
                    continue
                connection.execute(
                    "UPDATE work_items SET priority=? WHERE work_id=? AND status='queued'",
                    (priority, str(queued["work_id"])),
                )
                updates.append({
                    "work_id": queued["work_id"], "entity_id": request["entity_id"],
                    "event_research_request_sha256": event_sha,
                    "research_priority": priority,
                    "selection_use": "evidence_acquisition_only",
                })
            connection.commit()
        finally:
            connection.close()
        return updates
    prior = _read_json(receipt_path) or {}
    consumed = set(map(str, prior.get("consumed_request_sha256s") or ()))
    if prior.get("acquisition_sha256") and not consumed:
        prior_entities = set(map(str, prior.get("selected_tickers") or ()))
        consumed = {
            str(row["research_request_sha256"])
            for row in shadow.get("event_research_queue") or ()
            if str(row.get("entity_id") or "") in prior_entities
        }
        migrated = {
            key: value for key, value in prior.items() if key != "acquisition_sha256"
        }
        migrated["consumed_request_sha256s"] = sorted(consumed)
        prior = {**migrated, "acquisition_sha256": stable_sha256(migrated)}
        _atomic_json(receipt_path, prior)
    queue_by_entity = {
        str(row.get("entity_id") or ""): row
        for row in shadow.get("event_research_queue") or ()
    }
    prior_outcomes = []
    for raw in prior.get("discovery_outcomes") or ():
        row = dict(raw)
        trigger = queue_by_entity.get(str(row.get("entity_id") or ""))
        if trigger:
            row.setdefault("move_observation_sha256", trigger["move_observation_sha256"])
            row.setdefault(
                "event_research_request_sha256", trigger["research_request_sha256"],
            )
        prior_outcomes.append(row)
    if prior_outcomes and prior_outcomes != list(prior.get("discovery_outcomes") or ()):
        migrated = {
            key: value for key, value in prior.items() if key != "acquisition_sha256"
        }
        migrated["discovery_outcomes"] = prior_outcomes
        prior = {**migrated, "acquisition_sha256": stable_sha256(migrated)}
        _atomic_json(receipt_path, prior)
    selected = [
        row for row in shadow.get("event_research_queue") or ()
        if str(row.get("research_request_sha256") or "") not in consumed
    ][:max(0, limit)]
    routed_event_requests: dict[str, list[dict[str, Any]]] = {}
    for path in (root / "research_jobs" / "requests").glob("*.json"):
        request = _read_json(path)
        trigger = request.get("strategy_event_trigger") if request else None
        event_sha = str((trigger or {}).get("event_research_request_sha256") or "")
        if event_sha:
            routed_event_requests.setdefault(event_sha, []).append(request)
    candidate_index = latest_discovery_candidate_index(root)
    repair_rows = [
        row for row in shadow.get("event_research_queue") or ()
        if str(row.get("research_request_sha256") or "") in consumed
        and not any(
            research_request_currency(request, candidate_index).get("admissible")
            for request in routed_event_requests.get(
                str(row.get("research_request_sha256") or ""), ()
            )
        )
        and any(
            outcome.get("entity_id") == row.get("entity_id")
            and outcome.get("candidate_leaf")
            for outcome in prior.get("discovery_outcomes") or ()
            if isinstance(outcome, Mapping)
        )
    ]
    if not selected and prior.get("acquisition_sha256") and not repair_rows:
        priority_updates = reprioritize(
            row for row in shadow.get("event_research_queue") or ()
            if str(row.get("research_request_sha256") or "") in consumed
        )
        if not priority_updates:
            return prior
        reprioritized = {
            key: value for key, value in prior.items() if key != "acquisition_sha256"
        }
        reprioritized["research_priority_updates"] = [
            *list(prior.get("research_priority_updates") or ()), *priority_updates,
        ]
        receipt = {
            **reprioritized, "acquisition_sha256": stable_sha256(reprioritized),
        }
        _atomic_json(receipt_path, receipt)
        return receipt
    if not selected and repair_rows:
        discovery_run = _read_json(root / "discovery" / "latest.json") or {}
        discovery_record = _read_json(root / "discovery" / "latest_record.json") or {}
        repair_triggers = {
            str(row["entity_id"]).upper(): {
                **dict(row), "strategy_path_shadow_sha256": shadow["shadow_sha256"],
            }
            for row in repair_rows
        }
        activations = _ensure_qualified_research_requests(
            root, config, discovery_run, discovery_record,
            strategy_event_triggers=repair_triggers,
        )
        event_activations = [
            row for row in activations
            if str(row.get("entity_id") or "") in repair_triggers
        ]
        research_queue = enqueue_research_request_jobs(root)
        priority_updates = reprioritize(repair_rows)
        repaired = {
            key: value for key, value in prior.items() if key != "acquisition_sha256"
        }
        repaired["qualified_research_request_count"] = (
            int(prior.get("qualified_research_request_count") or 0)
            + len(event_activations)
        )
        repaired["research_activations"] = [
            *list(prior.get("research_activations") or ()), *event_activations,
        ]
        repaired["research_enqueue_sha256"] = research_queue.get("enqueue_sha256")
        repaired["research_priority_updates"] = [
            *list(prior.get("research_priority_updates") or ()), *priority_updates,
        ]
        receipt = {**repaired, "acquisition_sha256": stable_sha256(repaired)}
        _atomic_json(receipt_path, receipt)
        return receipt
    tickers = list(dict.fromkeys(
        str(row["entity_id"]).upper() for row in selected
    ))
    strategy_event_triggers = {
        str(row["entity_id"]).upper(): {
            **dict(row),
            "strategy_path_shadow_sha256": shadow["shadow_sha256"],
        }
        for row in selected
    }
    if not tickers:
        body = {
            "schema": "jaggedthoughts-strategy-event-research-acquisition-v1",
            "status": "queue_empty", "selected_tickers": [],
            "capital_authority": False,
        }
        return {**body, "acquisition_sha256": stable_sha256(body)}
    new_tickers = [
        ticker for ticker in tickers if not public_equity_is_enrolled(root, ticker)
    ]
    enrollment = enroll_public_equities(root, tickers=new_tickers) if new_tickers else {
        "schema": "jaggedthoughts-public-equity-enrollment-batch-v1",
        "enrollments": [], "registry_source_calls": 0,
        "added_source_count": 0, "added_signal_count": 0,
    }
    manifest = load_source_manifest(root / str(config.get("source_manifest") or "sources.yaml"))
    selected_set = set(tickers)
    source_ids = sorted({
        str(row["id"]) for row in manifest.get("sources") or ()
        if isinstance(row, Mapping)
        and str(row.get("entity_id") or "").upper() in selected_set
        and row.get("adapter") in {
            "sec_companyfacts", "sec_submissions", "yahoo_chart_daily",
        }
    })
    source_run = (
        refresh_workspace_sources(root, strict=False, source_ids=source_ids)
        if source_ids else None
    )
    _policy_path, discovery_policy = _discovery_policy(root, config)
    build, discovery_run, discovery_record = _compile_current_discovery_epoch(
        root, config, discovery_policy,
    )
    candidate_by_id = {
        str(row["candidate_id"]): row for row in discovery_run.get("candidates") or ()
    }
    failure_by_id = {
        str(row["candidate_id"]): row
        for row in (discovery_run.get("frontier_closure") or {}).get("failures") or ()
    }
    candidate_leaves = dict(discovery_record.get("candidate_leaves") or {})
    outcomes = []
    for ticker in tickers:
        candidate_id = f"equity:{ticker}"
        candidate = candidate_by_id.get(candidate_id)
        failure = failure_by_id.get(candidate_id)
        trigger = strategy_event_triggers[ticker]
        lineage = {
            "move_observation_sha256": trigger["move_observation_sha256"],
            "event_research_request_sha256": trigger["research_request_sha256"],
        }
        if candidate is not None:
            outcomes.append({
                "entity_id": ticker, "candidate_id": candidate_id,
                **lineage,
                "state": str(candidate.get("screen_status") or "screened"),
                "candidate_sha256": candidate.get("candidate_sha256"),
                "candidate_leaf": candidate_leaves.get(candidate_id),
                "rank": candidate.get("rank"),
                "next_activation": candidate.get("next_activation"),
            })
        elif failure is not None:
            outcomes.append({
                "entity_id": ticker, "candidate_id": candidate_id,
                **lineage,
                "state": "frontier_closed", "reason": failure.get("reason"),
            })
        else:
            outcomes.append({
                "entity_id": ticker, "candidate_id": candidate_id,
                **lineage,
                "state": "not_enumerated_after_refresh",
                "reason": "public identity or required typed observations remain unavailable",
            })
    qualified_requests = _ensure_qualified_research_requests(
        root, config, discovery_run, discovery_record,
        strategy_event_triggers=strategy_event_triggers,
    )
    research_queue = enqueue_research_request_jobs(root)
    priority_updates = reprioritize(selected)
    discovery_research_handoff = _write_discovery_research_handoff(
        root, discovery_run, status="complete", research_queue=research_queue,
    )
    prior_outcomes = {
        str(row["entity_id"]): dict(row)
        for row in prior.get("discovery_outcomes") or () if row.get("entity_id")
    }
    prior_outcomes.update({str(row["entity_id"]): row for row in outcomes})
    consumed.update(str(row["research_request_sha256"]) for row in selected)
    body = {
        "schema": "jaggedthoughts-strategy-event-research-acquisition-v1",
        "status": "completed", "strategy_path_shadow_sha256": shadow.get("shadow_sha256"),
        "selected_tickers": tickers, "newly_enrolled_tickers": new_tickers,
        "source_ids": source_ids, "source_run_sha256": (source_run or {}).get("run_sha256"),
        "source_run_ok": bool((source_run or {}).get("ok", not source_ids)),
        "discovery_run_sha256": discovery_run.get("run_sha256"),
        "discovery_outcomes": [prior_outcomes[key] for key in sorted(prior_outcomes)],
        "consumed_request_sha256s": sorted(consumed),
        "qualified_research_request_count": len(qualified_requests),
        "research_enqueue_sha256": research_queue.get("enqueue_sha256"),
        "research_priority_updates": priority_updates,
        "discovery_research_handoff_sha256": discovery_research_handoff.get(
            "handoff_sha256"
        ),
        "build_ok": bool(build.get("ok")),
        "selection_use": "evidence_acquisition_only",
        "automatic_order_authority": False, "capital_authority": False,
    }
    receipt = {**body, "acquisition_sha256": stable_sha256(body)}
    _atomic_json(receipt_path, receipt)
    return receipt


def hydrate_workspace_fund_lookthrough(
    workspace: str | Path | None = None, *, target_entity_id: str = "FNK", limit: int = 10,
) -> dict[str, Any]:
    """Acquire the next holdings-weighted issuer slice and rebuild its evidence coverage."""
    if str(target_entity_id).strip().upper() in {"ALL", "PORTFOLIO"}:
        return hydrate_workspace_fund_portfolio_lookthrough(
            workspace, max_source_calls=limit,
        )
    if limit < 1 or limit > 50:
        raise ValueError("fund look-through limit must be in [1, 50]")
    root, config = load_workspace_config(workspace)
    result_path = root / "watchlists" / "results" / "us-value-fund-opportunities.json"
    if not result_path.is_file():
        build_workspace(root)
    watchlist = _read_json(result_path)
    graph = watchlist.get("fund_holdings_graph")
    if not isinstance(graph, Mapping):
        raise ValueError("fund look-through requires a compiled holdings graph")
    target = require_text(target_entity_id, "fund look-through target").upper()
    if str(graph.get("target_entity_id") or "").upper() != target:
        raise ValueError(f"compiled holdings graph targets {graph.get('target_entity_id')}, not {target}")
    queue = [
        row for row in graph.get("acquisition_queue") or ()
        if isinstance(row, Mapping) and row.get("next_action") == "enroll_public_equity"
    ]
    selected = queue[:limit]
    tickers = [str(row["entity_id"]).upper() for row in selected]
    if not tickers:
        return {
            "schema": "jaggedthoughts-fund-lookthrough-acquisition-v1",
            "ok": True, "status": "coverage_queue_exhausted",
            "target_entity_id": target, "selected_tickers": [],
            "before_coverage": graph.get("target_coverage"),
            "after_coverage": graph.get("target_coverage"),
            "read_model": build_read_model(root),
        }
    new_tickers = [ticker for ticker in tickers if not public_equity_is_enrolled(root, ticker)]
    enrollment = enroll_public_equities(root, tickers=new_tickers) if new_tickers else {
        "schema": "jaggedthoughts-public-equity-enrollment-batch-v1",
        "enrollments": [], "registry_source_calls": 0,
        "added_source_count": 0, "added_signal_count": 0,
    }
    manifest = load_source_manifest(root / "sources.yaml")
    source_ids = sorted({
        str(row["id"]) for row in manifest.get("sources") or ()
        if isinstance(row, Mapping)
        and str(row.get("entity_id") or "").upper() in set(tickers)
        and row.get("adapter") in {"sec_companyfacts", "yahoo_chart_daily"}
    })
    source_run = refresh_workspace_sources(root, strict=False, source_ids=source_ids) if source_ids else None
    _policy_path, discovery_policy = _discovery_policy(root, config)
    build, discovery_run, discovery_record = _compile_current_discovery_epoch(
        root, config, discovery_policy,
    )
    qualified_requests = _ensure_qualified_research_requests(
        root, config, discovery_run, discovery_record,
    )
    research_queue = enqueue_research_request_jobs(root)
    updated_watchlist = _read_json(result_path)
    updated_graph = updated_watchlist.get("fund_holdings_graph") or {}
    body = {
        "schema": "jaggedthoughts-fund-lookthrough-acquisition-v1",
        "target_entity_id": target, "limit": limit,
        "selected": selected, "selected_tickers": tickers,
        "newly_enrolled_tickers": new_tickers,
        "source_ids": source_ids,
        "source_run_as_of": (source_run or {}).get("as_of"),
        "before_coverage": graph.get("target_coverage"),
        "after_coverage": updated_graph.get("target_coverage"),
        "fund_holdings_graph_sha256": updated_graph.get("fund_holdings_graph_sha256"),
    }
    receipt = {**body, "acquisition_sha256": stable_sha256(body)}
    _atomic_json(root / "data" / "fund_holdings" / f"{target.lower()}-acquisition-latest.json", receipt)
    capital_cycle = run_workspace_capital_cycle(root, force=True)
    return {
        **receipt, "ok": True, "status": "completed", "enrollment": enrollment,
        "source_run_ok": bool((source_run or {}).get("ok", not source_ids)),
        "build_ok": bool(build.get("ok")), "discovery_run": discovery_run,
        "qualified_research_requests": qualified_requests,
        "research_queue": research_queue, "capital_cycle": capital_cycle.get("run"),
        "opportunity_book": capital_cycle.get("opportunity_book"),
        "read_model": capital_cycle["read_model"],
    }


def _fund_lookthrough_policy(
    root: Path, config: Mapping[str, Any],
) -> dict[str, Any]:
    enrichment = load_enrichment_policy(
        root / str(config.get("enrichment_policy") or "research_jobs/enrichment_policy.yaml")
    )
    raw = (
        enrichment.get("fund_lookthrough")
        if isinstance(enrichment.get("fund_lookthrough"), Mapping) else {}
    )
    discovery = load_discovery_policy(
        root / str(config.get("discovery_policy") or "discovery.yaml")
    )
    desired = int(raw.get("max_source_calls", 10))
    budgets = enrichment["budgets"]
    max_source_calls = min(
        desired,
        int(budgets["max_incremental_source_calls"]),
        int(budgets["max_total_source_calls"]),
    )
    if desired < 1 or desired > 100:
        raise ValueError("fund look-through policy max_source_calls must be in [1, 100]")
    cadence_hours = require_finite(
        discovery.get("cadence_hours", 24), "fund look-through cadence_hours",
    )
    if cadence_hours <= 0:
        raise ValueError("fund look-through cadence_hours must be positive")
    return {
        "enabled": bool(enrichment.get("enabled", True) and raw.get("enabled", True)),
        "max_source_calls": max_source_calls,
        "configured_max_source_calls": desired,
        "cadence_hours": cadence_hours,
        "cadence_owner": "discovery_policy",
        "source_budget_owner": "enrichment_policy",
        "policy_sha256": stable_sha256(enrichment),
    }


def fund_lookthrough_acquisition_status(
    workspace: str | Path | None = None, *, now: str | None = None,
    plan: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Project the next bounded cross-fund public-source transition."""
    root, config = load_workspace_config(workspace)
    checked_at = canonical_timestamp(now or _utc_now(), "fund look-through checked_at")
    policy = _fund_lookthrough_policy(root, config)
    latest = _read_json(
        root / "data" / "fund_holdings" / "portfolio-acquisition-latest.json"
    )
    last_completed_at = str(
        (latest or {}).get("completed_at") or (latest or {}).get("source_run_as_of") or ""
    )
    next_due_at = checked_at
    cadence_due = True
    if last_completed_at:
        next_due = (
            datetime.fromisoformat(last_completed_at.replace("Z", "+00:00"))
            + timedelta(hours=float(policy["cadence_hours"]))
        )
        next_due_at = next_due.astimezone(timezone.utc).isoformat(
            timespec="seconds"
        ).replace("+00:00", "Z")
        cadence_due = timestamp_key(checked_at) >= timestamp_key(next_due_at)
    current_plan = dict(plan) if isinstance(plan, Mapping) else None
    current_comparison = _read_json(
        root / "portfolio" / "fund_sleeve_comparison" / "latest.json"
    ) or {}
    current_tournament_sha256 = str(
        (current_comparison.get("portfolio_policy_tournament_input") or {}).get(
            "tournament_input_sha256"
        ) or ""
    )
    if current_plan is None and not cadence_due:
        cached = _read_json(root / "state" / "fund_lookthrough_service.json") or {}
        cached_policy = cached.get("policy") if isinstance(cached.get("policy"), Mapping) else {}
        if (
            cached.get("schema") == FUND_LOOKTHROUGH_AUTONOMY_SCHEMA
            and cached.get("current_plan_sha256")
            and cached.get("last_acquisition_sha256") == (latest or {}).get("acquisition_sha256")
            and cached_policy.get("policy_sha256") == policy.get("policy_sha256")
            and (
                not current_tournament_sha256
                or cached.get("fund_program_tournament_input_sha256")
                == current_tournament_sha256
            )
        ):
            current_plan = {
                "plan_sha256": cached["current_plan_sha256"],
                "fund_program_tournament_input_sha256": cached.get(
                    "fund_program_tournament_input_sha256"
                ),
                "selected_entity_ids": list(cached.get("selected_entity_ids") or ()),
                "aggregate_before_company_quality_weight": cached.get(
                    "observed_aggregate_company_quality_weight"
                ),
                "aggregate_after_company_quality_weight_potential": cached.get(
                    "post_batch_aggregate_weight_potential"
                ),
                "source_budget": cached.get("source_budget"),
            }
    error = None
    if current_plan is not None and current_plan.get("status") == "unavailable":
        error = str(current_plan.get("error") or "fund look-through plan unavailable")
    if current_plan is None and policy["max_source_calls"] > 0:
        try:
            current_plan = compile_workspace_fund_lookthrough_acquisition_plan(
                root, max_source_calls=int(policy["max_source_calls"]),
            )
        except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as exc:
            error = f"{type(exc).__name__}: {exc}"[:1_000]
    selected = list((current_plan or {}).get("selected_entity_ids") or ())
    if not policy["enabled"]:
        status = "disabled"
        next_action = None
    elif policy["max_source_calls"] < 1:
        status = "source_budget_unavailable"
        next_action = "increase_existing_enrichment_source_budget"
    elif error:
        status = "plan_unavailable"
        next_action = "refresh_fund_comparison_inputs"
    elif not selected:
        status = "coverage_queue_exhausted"
        next_action = None
        next_due_at = None
    elif not cadence_due:
        status = "not_due"
        next_action = "wait_for_discovery_cadence"
    else:
        status = "due"
        next_action = "acquire_selected_public_issuer_facts"
    body = {
        "schema": FUND_LOOKTHROUGH_AUTONOMY_SCHEMA,
        "checked_at": checked_at,
        "status": status,
        "next_action": next_action,
        "next_due_at": next_due_at,
        "last_completed_at": last_completed_at or None,
        "last_acquisition_sha256": (latest or {}).get("acquisition_sha256"),
        "last_plan_sha256": (latest or {}).get("plan_sha256"),
        "current_plan_sha256": (current_plan or {}).get("plan_sha256"),
        "fund_program_tournament_input_sha256": (current_plan or {}).get(
            "fund_program_tournament_input_sha256"
        ),
        "selected_entity_ids": selected,
        "selected_count": len(selected),
        "observed_aggregate_company_quality_weight": (
            (current_plan or {}).get("aggregate_before_company_quality_weight")
        ),
        "post_batch_aggregate_weight_potential": (
            (current_plan or {}).get("aggregate_after_company_quality_weight_potential")
        ),
        "source_budget": (current_plan or {}).get("source_budget") or {
            "max_source_calls": policy["max_source_calls"],
        },
        "policy": policy,
        "error": error,
        "source_boundary": "public_sec_companyfacts_only",
        "allocation_selected": False,
        "capital_authority": False,
    }
    return {**body, "status_sha256": stable_sha256(body)}


def run_workspace_fund_lookthrough_acquisition(
    workspace: str | Path | None = None, *, force: bool = False,
) -> dict[str, Any]:
    """Execute at most one due cross-fund source batch from the discovery service."""
    root, _config = load_workspace_config(workspace)
    with _FUND_LOOKTHROUGH_LOCK:
        status = fund_lookthrough_acquisition_status(root)
        if not force and status["status"] != "due":
            _atomic_json(root / "state" / "fund_lookthrough_service.json", status)
            return {**status, "ok": status["status"] != "plan_unavailable"}
        if status["status"] in {"disabled", "source_budget_unavailable", "plan_unavailable", "coverage_queue_exhausted"}:
            _atomic_json(root / "state" / "fund_lookthrough_service.json", status)
            return {**status, "ok": status["status"] != "plan_unavailable"}
        plan = compile_workspace_fund_lookthrough_acquisition_plan(
            root, max_source_calls=int(status["policy"]["max_source_calls"]),
        )
        if plan["plan_sha256"] != status["current_plan_sha256"]:
            changed = {
                **status,
                "status": "plan_changed_before_execution",
                "next_action": "retry_next_service_poll",
                "replacement_plan_sha256": plan["plan_sha256"],
                "ok": True,
            }
            _atomic_json(root / "state" / "fund_lookthrough_service.json", changed)
            return changed
        result = hydrate_workspace_fund_portfolio_lookthrough(
            root, max_source_calls=int(status["policy"]["max_source_calls"]),
            plan=plan, refresh_capital_cycle=False,
        )
        completed = fund_lookthrough_acquisition_status(root)
        action = {
            **completed,
            "ok": bool(result.get("ok")),
            "last_action": result.get("status"),
            "executed_plan_sha256": plan["plan_sha256"],
            "source_run_sha256": result.get("source_run_sha256"),
            "source_selection_sha256": result.get("source_selection_sha256"),
            "acquisition_sha256": result.get("acquisition_sha256"),
        }
        _atomic_json(root / "state" / "fund_lookthrough_service.json", action)
        read_model = build_read_model(root)
        _atomic_json(root / "state" / "read_model.json", read_model)
        return {**action, "read_model": read_model}


def hydrate_workspace_fund_portfolio_lookthrough(
    workspace: str | Path | None = None, *, max_source_calls: int = 10,
    plan: Mapping[str, Any] | None = None, refresh_capital_cycle: bool = True,
) -> dict[str, Any]:
    """Execute the cross-fund issuer plan through the existing SEC/build owners."""
    root, config = load_workspace_config(workspace)
    plan = (
        dict(plan) if isinstance(plan, Mapping)
        else compile_workspace_fund_lookthrough_acquisition_plan(
            root, max_source_calls=max_source_calls,
        )
    )
    plan_body = {key: value for key, value in plan.items() if key != "plan_sha256"}
    if (
        plan.get("schema") != "jaggedthoughts-fund-lookthrough-acquisition-plan-v1"
        or stable_sha256(plan_body) != plan.get("plan_sha256")
    ):
        raise ValueError("fund look-through execution requires an exact hashed plan")
    tickers = list(plan["selected_entity_ids"])
    if not tickers:
        return {
            "schema": "jaggedthoughts-fund-portfolio-lookthrough-acquisition-v1",
            "ok": True, "status": "coverage_queue_exhausted",
            "plan": plan, "selected_tickers": [],
            "read_model": build_read_model(root), "capital_authority": False,
        }
    enrollment = enroll_public_equities(root, tickers=tickers)
    manifest = load_source_manifest(root / "sources.yaml")
    selected_ids = set(tickers)
    source_ids = sorted(
        str(row["id"]) for row in manifest.get("sources") or ()
        if isinstance(row, Mapping)
        and str(row.get("entity_id") or "").upper() in selected_ids
        and row.get("adapter") == "sec_companyfacts"
    )
    source_run = refresh_workspace_sources(
        root, strict=False, source_ids=source_ids,
    )
    _policy_path, discovery_policy = _discovery_policy(root, config)
    build, discovery_run, discovery_record = _compile_current_discovery_epoch(
        root, config, discovery_policy,
    )
    qualified_requests = _ensure_qualified_research_requests(
        root, config, discovery_run, discovery_record,
    )
    research_queue = enqueue_research_request_jobs(root)
    after_plan = compile_workspace_fund_lookthrough_acquisition_plan(
        root, max_source_calls=max_source_calls,
    )
    source_receipts = sorted(
        ({
            "source_id": row.get("source_id"),
            "receipt_sha256": row.get("receipt_sha256"),
            "content_sha256": row.get("content_sha256"),
        } for row in source_run.get("source_receipts") or ()
         if row.get("source_id") in set(source_ids)),
        key=lambda row: str(row["source_id"]),
    )
    source_selection = {
        "plan_sha256": plan["plan_sha256"],
        "source_ids": source_ids,
        "source_run_sha256": source_run["run_sha256"],
        "source_receipts": source_receipts,
    }
    body = {
        "schema": "jaggedthoughts-fund-portfolio-lookthrough-acquisition-v1",
        "completed_at": source_run.get("retrieved_at") or _utc_now(),
        "plan_sha256": plan["plan_sha256"],
        "selected": plan["selected"],
        "selected_tickers": tickers,
        "source_budget": plan["source_budget"],
        "source_ids": source_ids,
        "source_run_as_of": source_run.get("as_of"),
        "source_run_sha256": source_run["run_sha256"],
        "source_selection_sha256": stable_sha256(source_selection),
        "source_receipts": source_receipts,
        "next_plan_sha256": after_plan["plan_sha256"],
        "before_coverage": plan["before_after_coverage_potential"],
        "after_coverage_potential": plan["before_after_coverage_potential"],
        "after_observed_coverage": after_plan["before_after_coverage_potential"],
        "remaining_gaps": after_plan["remaining_gaps"],
        "allocation_selected": False,
        "capital_authority": False,
    }
    receipt = {**body, "acquisition_sha256": stable_sha256(body)}
    _atomic_json(
        root / "data" / "fund_holdings" / "portfolio-acquisition-latest.json",
        receipt,
    )
    capital_cycle = (
        run_workspace_capital_cycle(root, force=True) if refresh_capital_cycle else None
    )
    read_model = (
        capital_cycle["read_model"] if capital_cycle is not None
        else build_read_model(root)
    )
    if capital_cycle is None:
        _atomic_json(root / "state" / "read_model.json", read_model)
    return {
        **receipt, "ok": True, "status": "completed", "enrollment": enrollment,
        "source_run_ok": bool(source_run.get("ok")), "build_ok": bool(build.get("ok")),
        "discovery_run": discovery_run,
        "qualified_research_requests": qualified_requests,
        "research_queue": research_queue,
        "capital_cycle": (capital_cycle or {}).get("run"),
        "opportunity_book": (capital_cycle or {}).get("opportunity_book"),
        "read_model": read_model,
    }


def enroll_workspace_public_fund(
    ticker: str,
    name: str,
    workspace: str | Path | None = None,
    *,
    category: str = "public ETF catalog candidate",
) -> dict[str, Any]:
    """Enroll one public fund, then run its public price/factor analysis."""
    root, _config = load_workspace_config(workspace)
    enrollment = enroll_public_fund(
        root, ticker=ticker, name=name, category=category,
    )
    source_run = refresh_workspace_sources(root, strict=False)
    build = build_workspace(root)
    return {
        **enrollment, "source_run_ok": bool(source_run.get("ok")),
        "build_ok": bool(build.get("ok")), "read_model": build["read_model"],
    }


def refresh_workspace_market_catalog(
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Refresh the broad retrieval-time security catalog without deep enrichment."""
    root, _config = load_workspace_config(workspace)
    catalog = refresh_public_market_catalog(root)
    read_model = build_read_model(root)
    _atomic_json(root / "state" / "read_model.json", read_model)
    return {
        "ok": True,
        "catalog": catalog,
        "catalog_path": "universe/catalog-latest.json",
        "read_model": read_model,
    }


def run_workspace_market_scout(
    query: str,
    workspace: str | Path | None = None,
    *,
    max_results: int = 50,
    refresh_catalog: bool = False,
    intent_overrides: Mapping[str, Any] | None = None,
    subscribe_id: str | None = None,
) -> dict[str, Any]:
    """Compile operator language into a bounded catalog research queue."""
    root, config = load_workspace_config(workspace)
    result = run_market_scout(
        root, query, max_results=max_results, refresh_catalog=refresh_catalog,
        intent_overrides=intent_overrides,
    )
    subscription = None
    if subscribe_id:
        policy_path, policy = _market_scout_policy(root, config, materialize=True)
        rows = [
            dict(row) for row in policy.get("intents") or ()
            if isinstance(row, Mapping) and str(row.get("id") or "") != subscribe_id
        ]
        row = {
            "id": require_text(subscribe_id, "scheduled intent id"),
            "enabled": True,
            "mode": "language",
            "query": require_text(query, "market research query"),
            "max_results": int(max_results),
        }
        if intent_overrides:
            row["intent_overrides"] = dict(intent_overrides)
        updated = {**dict(policy), "intents": [*rows, row]}
        _atomic_text(policy_path, yaml.safe_dump(
            updated, sort_keys=False, allow_unicode=True,
        ))
        subscription_body = {
            "schema": "jaggedthoughts-market-intent-subscription-v1",
            "intent_id": row["id"],
            "intent_sha256": result["intent"]["intent_sha256"],
            "query": row["query"],
            "max_results": row["max_results"],
            "intent_overrides": dict(intent_overrides or {}),
            "policy_path": policy_path.relative_to(root).as_posix(),
            "policy_sha256": stable_sha256(updated),
            "next_activation": "periodic_discovery_service_or_scout_scheduled_force",
            "authority": "research_queue_only",
        }
        subscription = {
            **subscription_body,
            "subscription_sha256": stable_sha256(subscription_body),
        }
    read_model = build_read_model(root)
    _atomic_json(root / "state" / "read_model.json", read_model)
    return {
        "ok": True, "scout": result, "subscription": subscription,
        "read_model": read_model,
    }


def _market_scout_policy(
    root: Path, config: Mapping[str, Any], *, materialize: bool,
) -> tuple[Path, Mapping[str, Any]]:
    relative = str(config.get("market_scout_policy") or "research_jobs/intents.yaml")
    path = root / relative
    if not path.is_file():
        if not materialize:
            return path, default_market_scout_policy()
        _atomic_text(path, yaml.safe_dump(
            default_market_scout_policy(), sort_keys=False, allow_unicode=True,
        ))
    policy = _load_yaml(path)
    if policy.get("schema") != MARKET_SCOUT_POLICY_SCHEMA:
        raise ValueError(f"market scout policy schema must be {MARKET_SCOUT_POLICY_SCHEMA}")
    return path, policy


def _market_catalog_due(
    catalog: Mapping[str, Any] | None, *, refresh_hours: float, now: str,
) -> bool:
    if catalog is None:
        return True
    retrieved_at = canonical_timestamp(catalog.get("retrieved_at"), "catalog retrieved_at")
    return timestamp_key(now) >= timestamp_key(retrieved_at) + timedelta(hours=refresh_hours)


def _broad_equity_rollforward_due(
    root: Path, cycle: Mapping[str, Any], config: Mapping[str, Any],
) -> bool:
    """Recompile cached potential when a legacy or exhausted successor frontier remains."""
    result = next((
        row for row in cycle.get("results") or ()
        if isinstance(row, Mapping) and row.get("mode") == "broad_equity"
    ), None)
    if result is None:
        return False
    run = _read_json(root / str(result.get("run_path") or ""))
    if not run:
        return True
    frontier = run.get("enrichment_frontier")
    if not isinstance(frontier, list):
        return True
    latest_discovery = _read_json(root / "discovery" / "latest.json") or {}
    excluded = set(_enrolled_security_ids(root, config)) | {
        f"public_equity:{str(candidate['entity_id']).upper()}"
        for candidate in latest_discovery.get("candidates") or ()
        if isinstance(candidate, Mapping)
        and candidate.get("entity_kind") == "public_equity"
        and candidate.get("entity_id")
    }
    return not any(
        isinstance(candidate, Mapping)
        and str(candidate.get("security_id") or "") not in excluded
        for candidate in frontier
    )


def run_workspace_scheduled_market_scouts(
    workspace: str | Path | None = None,
    *,
    force: bool = False,
    now: str | None = None,
) -> dict[str, Any]:
    """Run due editable market intents and persist bounded enrichment queues."""
    root, config = load_workspace_config(workspace)
    policy_path, policy = _market_scout_policy(root, config, materialize=True)
    completed_at = canonical_timestamp(now or _utc_now(), "market scout cycle time")
    latest = _read_json(root / "research_jobs" / "scheduled" / "latest.json")
    if not bool(policy.get("enabled", True)):
        return {
            "schema": MARKET_SCOUT_CYCLE_SCHEMA, "ok": True, "status": "disabled",
            "policy_path": policy_path.relative_to(root).as_posix(),
        }
    refresh_hours = require_finite(
        policy.get("catalog_refresh_hours", 24), "catalog_refresh_hours",
    )
    if refresh_hours <= 0:
        raise ValueError("catalog_refresh_hours must be positive")
    last_completed = str((latest or {}).get("completed_at") or "")
    due_at = (
        timestamp_key(last_completed) + timedelta(hours=refresh_hours)
        if last_completed else None
    )
    selection_rollforward = bool(
        latest and _broad_equity_rollforward_due(root, latest, config)
    )
    if (
        not force and not selection_rollforward
        and due_at is not None and timestamp_key(completed_at) < due_at
    ):
        return {
            "schema": MARKET_SCOUT_CYCLE_SCHEMA, "ok": True, "status": "not_due",
            "policy_path": policy_path.relative_to(root).as_posix(),
            "next_due_at": due_at.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "latest_cycle": latest,
        }
    with _MARKET_SCOUT_LOCK:
        catalog = _read_json(root / "universe" / "catalog-latest.json")
        refresh_catalog = force or _market_catalog_due(
            catalog, refresh_hours=refresh_hours, now=completed_at,
        )
        catalog_was_refreshed = refresh_catalog
        if refresh_catalog:
            catalog = refresh_public_market_catalog(root, retrieved_at=completed_at)
        if catalog is None:
            raise ValueError("scheduled scouts require a public-market catalog")
        sec_frame_path = root / "data" / "sec_frames" / "latest.json"
        sec_frame_screen = _read_json(sec_frame_path) or {}
        sec_frame_refreshed = False
        if (
            force
            or sec_frame_screen.get("schema") != SEC_FRAME_SCREEN_SCHEMA
            or sec_frame_screen.get("catalog_sha256") != catalog.get("catalog_sha256")
        ):
            sec_frame_screen = hydrate_sec_annual_frame_screen(root)
            sec_frame_refreshed = True
        default_max_results = int(policy.get("default_max_results") or 50)
        results: list[dict[str, Any]] = []
        for row in policy.get("intents") or ():
            if not isinstance(row, Mapping) or not bool(row.get("enabled", True)):
                continue
            intent_id = require_text(row.get("id"), "scheduled intent id")
            mode = str(row.get("mode") or "language")
            if mode == "broad_equity":
                acquisition_policy = row.get("acquisition_policy") or default_broad_equity_policy()
                if not isinstance(acquisition_policy, Mapping):
                    raise ValueError(f"scheduled intent {intent_id} acquisition_policy must be a mapping")
                latest_discovery = _read_json(root / "discovery" / "latest.json") or {}
                scout = compile_sec_frame_acquisition_run(
                    catalog, sec_frame_screen,
                    policy=acquisition_policy,
                    enrolled_security_ids=_enrolled_security_ids(root, config),
                    current_security_ids=(
                        f"public_equity:{candidate['entity_id']}"
                        for candidate in latest_discovery.get("candidates") or ()
                        if isinstance(candidate, Mapping)
                        and candidate.get("entity_kind") == "public_equity"
                        and candidate.get("entity_id")
                    ),
                    completed_at=completed_at,
                )
                run_path = root / "research_jobs" / "runs" / f"{scout['run_id']}.json"
                _atomic_json(run_path, scout)
                scout = {**scout, "run_path": run_path.relative_to(root).as_posix()}
                query = str((scout.get("intent") or {}).get("query") or "")
            elif mode == "broad_fund":
                acquisition_policy = row.get("acquisition_policy") or broad_fund_scout_policy()
                if not isinstance(acquisition_policy, Mapping):
                    raise ValueError(f"scheduled intent {intent_id} acquisition_policy must be a mapping")
                scout = compile_broad_fund_scout(
                    catalog,
                    acquisition_policy,
                    watchlist_results=(
                        result for path in sorted((root / "watchlists" / "results").glob("*.json"))
                        if (result := _read_json(path))
                    ),
                    completed_at=completed_at,
                )
                run_id = (
                    f"broad-fund-{timestamp_key(completed_at).strftime('%Y%m%d%H%M%S')}-"
                    f"{str(scout['scout_sha256'])[:8]}"
                )
                run_path = root / "research_jobs" / "runs" / f"{run_id}.json"
                _atomic_json(run_path, scout)
                scout = {**scout, "run_id": run_id, "run_path": run_path.relative_to(root).as_posix()}
                query = ""
            elif mode == "language":
                query = require_text(row.get("query"), f"scheduled intent {intent_id} query")
                overrides = row.get("intent_overrides")
                if overrides is not None and not isinstance(overrides, Mapping):
                    raise ValueError(f"scheduled intent {intent_id} intent_overrides must be a mapping")
                scout = run_market_scout(
                    root,
                    query,
                    max_results=int(row.get("max_results") or default_max_results),
                    refresh_catalog=False,
                    write_latest=False,
                    intent_overrides=overrides,
                )
            else:
                raise ValueError(f"scheduled intent {intent_id} has unsupported mode: {mode}")
            population = scout.get("population") or {}
            results.append({
                "intent_id": intent_id,
                "mode": mode,
                "query": query,
                "run_id": scout["run_id"],
                "run_path": scout["run_path"],
                "intent_sha256": (scout.get("intent") or {}).get("intent_sha256"),
                "receipt_sha256": scout.get("run_sha256") or scout.get("scout_sha256"),
                "eligible_count": int(
                    population.get("eligible_count")
                    or population.get("distinct_eligible_equity_count") or 0
                    or scout.get("eligible_fund_count") or 0
                ),
                "returned_count": int(
                    population.get("returned_count") or population.get("selected_count")
                    or scout.get("selected_count") or 0
                ),
            })
        body: dict[str, Any] = {
            "schema": MARKET_SCOUT_CYCLE_SCHEMA,
            "ok": True,
            "status": "completed",
            "completed_at": completed_at,
            "policy_path": policy_path.relative_to(root).as_posix(),
            "policy_sha256": stable_sha256(policy),
            "catalog_refreshed": catalog_was_refreshed,
            "selection_rollforward": selection_rollforward,
            "sec_frame_screen": {
                "screen_sha256": sec_frame_screen.get("screen_sha256"),
                "frame": sec_frame_screen.get("frame"),
                "retrieved_at": sec_frame_screen.get("retrieved_at"),
                "refreshed": sec_frame_refreshed,
                "coverage": sec_frame_screen.get("coverage"),
                "typed_exclusions": sec_frame_screen.get("typed_exclusions"),
            },
            "intent_count": len(results),
            "results": results,
            "activation_boundary": policy.get("activation_boundary"),
        }
        cycle_sha256 = stable_sha256(body)
        cycle = {**body, "cycle_sha256": cycle_sha256}
        stamp = timestamp_key(completed_at).strftime("%Y%m%d%H%M%S")
        cycle_path = root / "research_jobs" / "scheduled" / "runs" / (
            f"scout-cycle-{stamp}-{cycle_sha256[:8]}.json"
        )
        _atomic_json(cycle_path, cycle)
        _atomic_json(root / "research_jobs" / "scheduled" / "latest.json", cycle)
    return {**cycle, "cycle_path": cycle_path.relative_to(root).as_posix()}


def _enrichment_policy(
    root: Path, config: Mapping[str, Any], *, materialize: bool,
) -> tuple[Path, Mapping[str, Any]]:
    relative = str(
        config.get("enrichment_policy") or "research_jobs/enrichment_policy.yaml"
    )
    path = root / relative
    if not path.is_file():
        if not materialize:
            return path, default_enrichment_policy()
        _atomic_text(path, yaml.safe_dump(
            default_enrichment_policy(), sort_keys=False, allow_unicode=True,
        ))
    policy = load_enrichment_policy(path)
    if policy.get("schema") != ENRICHMENT_POLICY_SCHEMA:
        raise ValueError(f"enrichment policy schema must be {ENRICHMENT_POLICY_SCHEMA}")
    return path, policy


def _enrolled_security_ids(root: Path, config: Mapping[str, Any]) -> set[str]:
    enrolled: set[str] = set()
    manifest = load_source_manifest(
        root / str(config.get("source_manifest") or "sources.yaml")
    )
    for row in manifest.get("sources") or ():
        if not isinstance(row, Mapping) or row.get("enabled", True) is False:
            continue
        if row.get("adapter") == "sec_companyfacts" and row.get("entity_id"):
            enrolled.add(f"public_equity:{str(row['entity_id']).upper()}")
    for watchlist_path in sorted((root / "watchlists").rglob("*.yaml")):
        watchlist = _load_yaml(watchlist_path)
        for row in watchlist.get("candidates") or ():
            if isinstance(row, Mapping) and row.get("entity_id"):
                enrolled.add(f"public_fund:{str(row['entity_id']).upper()}")
    return enrolled


def _research_question_policy_price_refresh_entity_ids(root: Path) -> set[str]:
    entities: set[str] = set()
    settlement_root = (
        root / "institutional_learning" / "research_question_policy_outcomes"
        / "settlements"
    )
    settled = {path.stem for path in settlement_root.glob("*.json") if (
        (row := _read_json(path)) and str(row.get("status") or "").startswith("settled_")
    )}
    for path in (root / "research_jobs" / "requests").glob("*.json"):
        request = _read_json(path) or {}
        contract = request.get("research_policy_outcome_contract")
        if not isinstance(contract, Mapping) or not contract.get("eligible"):
            continue
        unit_id = str(contract.get("assignment_unit_id") or "")
        if unit_id in settled:
            continue
        entities.update({
            str(contract.get("entity_id") or "").upper(),
            str(contract.get("benchmark_id") or "").upper(),
        })
    return {entity for entity in entities if entity}


def _market_flow_shadow_refresh_source_ids(
    root: Path, config: Mapping[str, Any], manifest: Mapping[str, Any],
) -> set[str]:
    """Keep each registered prospective cross-section measurable at its source epoch."""
    entities: set[str] = set()
    for registration in config.get("research_projects") or ():
        if not isinstance(registration, Mapping):
            continue
        lifecycle = registration.get("prospective_lifecycle")
        if (
            not isinstance(lifecycle, Mapping)
            or lifecycle.get("kind") != "cross_sectional_market_flow_shadow"
            or not lifecycle.get("profile")
        ):
            continue
        profile = _load_yaml(root / str(lifecycle["profile"]))
        entities.update(
            str(value).upper()
            for value in profile.get("entity_ids") or () if str(value)
        )
    sources_by_entity: dict[str, list[Mapping[str, Any]]] = {}
    for row in manifest.get("sources") or ():
        if (
            isinstance(row, Mapping)
            and row.get("enabled", True) is not False
            and row.get("adapter") == "yahoo_chart_daily"
            and row.get("emit_adjusted_price", True) is not False
            and row.get("entity_id")
        ):
            sources_by_entity.setdefault(
                str(row["entity_id"]).upper(), []
            ).append(row)
    missing = sorted(entities - set(sources_by_entity))
    if missing:
        raise ValueError(
            "prospective market-flow cohort lacks adjusted-price sources: "
            + ", ".join(missing)
        )
    return {
        str(min(sources_by_entity[entity], key=lambda row: (
            row.get("metric_id") != "adjusted_price", str(row.get("id") or ""),
        ))["id"])
        for entity in entities
    }


def _baseline_refresh_source_ids(
    root: Path, config: Mapping[str, Any], policy: Mapping[str, Any],
) -> set[str]:
    manifest = load_source_manifest(
        root / str(config.get("source_manifest") or "sources.yaml")
    )
    refresh = policy.get("source_refresh") if isinstance(policy.get("source_refresh"), Mapping) else {}
    ids = {str(value) for value in refresh.get("core_source_ids") or ()}
    adapters = {str(value) for value in refresh.get("always_adapters") or ()}
    active_entities: set[str] = set()
    if bool(refresh.get("include_active_profile_entities", True)):
        for path in (root / "profiles").glob("**/*.yaml"):
            try:
                profile = _load_yaml(path)
            except (OSError, TypeError, ValueError, yaml.YAMLError):
                continue
            lifecycle = profile.get("lifecycle") if isinstance(profile.get("lifecycle"), Mapping) else {}
            entity = profile.get("entity") if isinstance(profile.get("entity"), Mapping) else {}
            if lifecycle.get("stage") in {"draft", "active"} and entity.get("id"):
                active_entities.add(str(entity["id"]).upper())
    configured: set[str] = set()
    for row in manifest.get("sources") or ():
        if not isinstance(row, Mapping) or row.get("enabled", True) is False:
            continue
        source_id = str(row.get("id") or "")
        configured.add(source_id)
        if (
            row.get("required") is True or row.get("adapter") in adapters
            or str(row.get("entity_id") or "").upper() in active_entities
        ):
            ids.add(source_id)
    ids.update(_market_flow_shadow_refresh_source_ids(root, config, manifest))
    pending_price_entities = sorted(
        set(rank_program_price_refresh_entity_ids(root))
        | set(household_policy_price_refresh_entity_ids(root))
        | set(closed_book_price_refresh_entity_ids(root))
        | set(portfolio_policy_price_refresh_entity_ids(root))
        | _research_question_policy_price_refresh_entity_ids(root)
    )
    price_sources: dict[str, list[Mapping[str, Any]]] = {}
    for row in manifest.get("sources") or ():
        if (
            isinstance(row, Mapping)
            and row.get("enabled", True) is not False
            and row.get("adapter") == "yahoo_chart_daily"
            and row.get("emit_adjusted_price", True) is not False
            and row.get("entity_id")
        ):
            price_sources.setdefault(str(row["entity_id"]).upper(), []).append(row)
    missing_price_entities = sorted(set(pending_price_entities) - set(price_sources))
    if missing_price_entities:
        raise ValueError(
            "pending prospective windows lack adjusted-price sources: "
            + ", ".join(missing_price_entities)
        )
    for entity_id in pending_price_entities:
        source = min(price_sources[entity_id], key=lambda row: (
            str(row.get("id") or "") not in ids,
            row.get("metric_id") != "adjusted_price",
            str(row.get("id") or ""),
        ))
        ids.add(str(source["id"]))
    unknown = sorted(ids - configured)
    if unknown:
        raise ValueError("enrichment core sources are absent or disabled: " + ", ".join(unknown))
    return ids


def _maintenance_refresh_source_ids(
    root: Path,
    config: Mapping[str, Any],
    policy: Mapping[str, Any],
    *,
    already_selected: set[str],
    remaining_calls: int,
) -> dict[str, Any]:
    """Select whole request entities for evidence maintenance under spare budget.

    Acquisition adds new securities; maintenance keeps unresolved or monitored
    request identities current.  The two jobs have different owners and cost
    accounting, so maintenance never enters the acquisition-priority score.
    """
    refresh = policy.get("source_refresh") if isinstance(policy.get("source_refresh"), Mapping) else {}
    if not bool(refresh.get("include_research_request_entities", True)):
        return {"enabled": False, "source_ids": [], "entities": [], "used_calls": 0}
    ceiling = max(0, int(refresh.get("max_maintenance_source_calls", 8)))
    budget = min(max(0, int(remaining_calls)), ceiling)
    manifest = load_source_manifest(
        root / str(config.get("source_manifest") or "sources.yaml")
    )
    sources_by_entity: dict[str, set[str]] = {}
    for row in manifest.get("sources") or ():
        if not isinstance(row, Mapping) or row.get("enabled", True) is False:
            continue
        entity = str(row.get("entity_id") or "").upper()
        source_id = str(row.get("id") or "")
        if entity and source_id:
            sources_by_entity.setdefault(entity, set()).add(source_id)

    dossier_requests = {
        str(dossier.get("request_sha256") or "")
        for path in (root / "research" / "dossiers").glob("*.json")
        if (dossier := _read_json(path))
    }
    candidate_index = latest_discovery_candidate_index(root)
    latest_by_entity: dict[str, dict[str, Any]] = {}
    for path in (root / "research_jobs" / "requests").glob("*.json"):
        request = _read_json(path)
        if not request:
            continue
        entity = str(request.get("entity_id") or "").upper()
        if not entity or entity not in sources_by_entity:
            continue
        currency = research_request_currency(request, candidate_index)
        current_status = (
            str(currency.get("current_screen_status") or "")
            if currency["known"] else str(request.get("screen_status") or "")
        )
        if current_status not in {
            "qualified", "monitor", "stale_evidence", "needs_valuation_evidence",
        }:
            continue
        row = {
            "entity_id": entity,
            "request_sha256": request.get("request_sha256"),
            "as_of": request.get("as_of"),
            "screen_status": current_status,
            "request_is_current": currency["is_current"],
            "stage": (
                "researched"
                if str(request.get("request_sha256") or "") in dossier_requests
                else "evidence_ready"
            ),
            "rank_score": (
                currency.get("current_rank_score")
                if currency["known"] else request.get("rank_score")
            ),
        }
        prior = latest_by_entity.get(entity)
        if prior is None or timestamp_key(str(row["as_of"])) > timestamp_key(str(prior["as_of"])):
            latest_by_entity[entity] = row
    cohort_plan = _read_json(
        root / "institutional_learning" / "strategy_cohorts" / "latest.json"
    ) or {}
    manifest_rows = [
        row for row in manifest.get("sources") or () if isinstance(row, Mapping)
    ]
    for request in cohort_plan.get("requests") or ():
        entity = str(request.get("peer_entity_id") or "").upper()
        if not entity or entity not in sources_by_entity:
            continue
        monitored_ids = sorted(
            str(row["id"]) for row in manifest_rows
            if str(row.get("entity_id") or "").upper() == entity
            and row.get("adapter") in {"sec_companyfacts", "sec_submissions"}
        )
        if not monitored_ids:
            continue
        row = {
            "entity_id": entity, "request_sha256": request.get("request_sha256"),
            "as_of": request.get("search_end_at"), "screen_status": "strategy_monitor",
            "request_is_current": True, "stage": "strategy_cohort",
            "rank_score": 0, "requested_source_ids": monitored_ids,
        }
        prior = latest_by_entity.get(entity)
        if prior is None or timestamp_key(str(row["as_of"])) > timestamp_key(str(prior["as_of"])):
            latest_by_entity[entity] = row
    latest_execution = _read_json(
        root / "research_jobs" / "enrichment" / "latest_execution.json"
    ) or {}
    latest_cycle = _read_json(
        root / "research_jobs" / "enrichment" / "latest.json"
    ) or {}
    jobs_by_id = {
        str(row.get("work_id") or ""): row
        for row in latest_cycle.get("jobs") or ()
        if isinstance(row, Mapping)
    }
    receipt_heads = current_monitor_receipts(root)
    for result in latest_execution.get("results") or ():
        if not isinstance(result, Mapping) or result.get("result_status") != "blocked":
            continue
        job = jobs_by_id.get(str(result.get("work_id") or ""), result)
        if not isinstance(job, Mapping):
            continue
        entity = str(job.get("symbol") or job.get("entity_id") or "").upper()
        required_ids = sorted(sources_by_entity.get(entity, ()))
        completed_at = str(result.get("completed_at") or "")
        if not entity or not required_ids or not completed_at:
            continue
        if all(
            source_id in receipt_heads
            and receipt_heads[source_id].get("retrieved_at")
            and timestamp_key(str(receipt_heads[source_id].get("retrieved_at") or ""))
            > timestamp_key(completed_at)
            for source_id in required_ids
        ):
            continue
        row = {
            "entity_id": entity,
            "request_sha256": result.get("job_sha256"),
            "as_of": completed_at,
            "screen_status": "enrichment_repair",
            "request_is_current": True,
            "stage": "blocked_enrichment",
            "rank_score": 0,
            "requested_source_ids": required_ids,
        }
        prior = latest_by_entity.get(entity)
        if prior is None or timestamp_key(completed_at) > timestamp_key(str(prior["as_of"])):
            latest_by_entity[entity] = row
    requests = list(latest_by_entity.values())
    screen_priority = {
        "enrichment_repair": 0, "stale_evidence": 1, "qualified": 2,
        "strategy_monitor": 3, "monitor": 4, "needs_valuation_evidence": 5,
    }
    requests.sort(key=lambda row: (
        screen_priority.get(str(row.get("screen_status") or ""), 3),
        -float(row.get("rank_score") or 0),
        row["stage"] != "researched",
        -timestamp_key(str(row["as_of"])).timestamp(),
        row["entity_id"],
    ))
    selected: list[dict[str, Any]] = []
    source_ids: set[str] = set()
    for request in requests:
        entity = request["entity_id"]
        eligible = set(request.get("requested_source_ids") or sources_by_entity[entity])
        incremental = sorted(eligible - already_selected - source_ids)
        if not incremental:
            continue
        if len(source_ids) + len(incremental) > budget:
            continue
        source_ids.update(incremental)
        selected.append({**request, "source_ids": incremental, "source_call_cost": len(incremental)})
    return {
        "enabled": True,
        "budget_calls": budget,
        "used_calls": len(source_ids),
        "source_ids": sorted(source_ids),
        "entities": selected,
        "meaning": (
            "Spare source-call budget refreshes unresolved request entities as whole units; "
            "unscheduled candidate sources are stale for the new discovery epoch."
        ),
    }


def _attach_maintenance_refresh(
    root: Path, config: Mapping[str, Any], context: dict[str, Any]
) -> None:
    selected = set(str(value) for value in context.get("refresh_source_ids") or ())
    cycle = context.get("cycle") if isinstance(context.get("cycle"), Mapping) else {}
    policy = context.get("policy") if isinstance(context.get("policy"), Mapping) else {}
    budgets = policy.get("budgets") if isinstance(policy.get("budgets"), Mapping) else {}
    max_total = max(0, int(budgets.get("max_total_source_calls", 0)))
    registry_calls = int(
        ((cycle.get("budget_usage") or {}).get("sec_registry_batch_source_calls") or 0)
    )
    remaining = max(0, max_total - len(selected) - registry_calls)
    prior = (
        context.get("maintenance_refresh")
        if isinstance(context.get("maintenance_refresh"), Mapping) else {}
    )
    ceiling = max(0, int(
        (policy.get("source_refresh") or {}).get("max_maintenance_source_calls", 8)
    ))
    remaining = min(remaining, max(0, ceiling - int(prior.get("used_calls") or 0)))
    receipt = _maintenance_refresh_source_ids(
        root, config, policy, already_selected=selected, remaining_calls=remaining,
    )
    selected.update(receipt["source_ids"])
    context["refresh_source_ids"] = sorted(selected)
    if prior:
        receipt = {
            **receipt,
            "budget_calls": int(prior.get("budget_calls") or 0) + int(receipt["budget_calls"]),
            "used_calls": int(prior.get("used_calls") or 0) + int(receipt["used_calls"]),
            "source_ids": sorted({*prior.get("source_ids", ()), *receipt["source_ids"]}),
            "entities": [*prior.get("entities", ()), *receipt["entities"]],
        }
    context["maintenance_refresh"] = receipt
    context["source_refresh_plan"] = {
        "max_total_source_calls": max_total,
        "registry_source_calls": registry_calls,
        "selected_refresh_source_calls": len(selected),
        "estimated_total_source_calls": len(selected) + registry_calls,
        "within_total_budget": len(selected) + registry_calls <= max_total,
    }


def _scout_runs_for_cycle(root: Path, cycle: Mapping[str, Any]) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for result in cycle.get("results") or ():
        if not isinstance(result, Mapping):
            continue
        relative = str(result.get("run_path") or "")
        payload = _read_json(root / relative) if relative else None
        if not payload:
            continue
        frontier = payload.get("enrichment_frontier")
        candidate_surface = (
            "enrichment_frontier"
            if payload.get("potential_scope_only") and isinstance(frontier, list)
            else "candidates"
        )
        candidates = []
        for candidate in payload.get(candidate_surface) or ():
            if not isinstance(candidate, Mapping):
                continue
            candidate_row = dict(candidate)
            candidate_row["scout_candidate_surface"] = candidate_surface
            if candidate_row.get("entity_kind") == "public_fund":
                issuer = _fund_issuer_source(
                    str(candidate_row.get("symbol") or ""),
                    str(candidate_row.get("name") or ""),
                )
                candidate_row["source_activation"] = {
                    "status": "supported" if issuer else "blocked",
                    "reason": None if issuer else "issuer_adapter_not_registered",
                    "issuer_adapter": (issuer or {}).get("adapter"),
                    "required_evidence": ["aggregate_valuation", "issuer_evidence"],
                }
            candidates.append(candidate_row)
        runs.append({
            **payload,
            "candidates": candidates,
            "run_path": relative,
            "scheduled_intent_id": str(result.get("intent_id") or ""),
        })
    return runs


def _broad_fund_policy(
    root: Path, config: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    _path, policy = _market_scout_policy(root, config, materialize=False)
    for row in policy.get("intents") or ():
        if (
            isinstance(row, Mapping) and bool(row.get("enabled", True))
            and str(row.get("mode") or "language") == "broad_fund"
        ):
            acquisition = row.get("acquisition_policy") or broad_fund_scout_policy()
            if not isinstance(acquisition, Mapping):
                raise ValueError("scheduled broad-fund acquisition_policy must be a mapping")
            return acquisition
    return None


def _broad_fund_queue_rows(root: Path) -> list[dict[str, Any]]:
    path = root / "state" / "research_jobs.sqlite3"
    if not path.exists():
        return []
    connection = work_queue.connect(str(path))
    try:
        return [
            row for row in work_queue.list_items(connection, limit=10_000)
            if row.get("kind") == BROAD_FUND_ACQUISITION_JOB_KIND
        ]
    finally:
        connection.close()


def _broad_fund_acquisition_status(
    root: Path, *, next_due_at: str | None = None,
) -> dict[str, Any]:
    plan = _read_json(root / "research_jobs" / "fund_acquisition" / "latest.json") or {}
    queue_rows = _broad_fund_queue_rows(root)
    active = [row for row in queue_rows if row.get("status") in {"queued", "claimed", "running"}]
    coverage = plan.get("coverage") if isinstance(plan.get("coverage"), Mapping) else {}
    ready_groups = int(coverage.get("completed_peer_group_count") or 0)
    residual_members = {
        str(member.get("security_id") or "")
        for group in plan.get("selected_groups") or () if isinstance(group, Mapping)
        for member in group.get("members") or () if isinstance(member, Mapping)
        and member.get("requested_coordinates")
    }
    target = int(plan.get("target_group_count") or 2)
    residual_groups = int(coverage.get("residual_peer_group_count") or 0)
    if plan and plan.get("status") == "comparison_coverage_ready":
        status = "comparison_ready"
    elif plan and plan.get("status") == "ready_to_enqueue" and not active:
        status = "scheduled"
    elif active or int(plan.get("new_job_count") or 0):
        status = "acquiring"
    elif plan:
        status = "blocked"
    else:
        status = "not_compiled"
    return {
        "schema": "jaggedthoughts-broad-fund-acquisition-status-v1",
        "enabled": bool(plan),
        "status": status,
        "ready_group_count": ready_groups,
        "target_group_count": target,
        "observed_cell_count": int(coverage.get("observed_cell_count") or 0),
        "comparable_peer_group_count": int(
            coverage.get("comparable_peer_group_count") or 0
        ),
        "residual_peer_group_count": residual_groups,
        "blocked_peer_group_count": int(
            coverage.get("blocked_peer_group_count") or 0
        ),
        "comparison_coverage_fraction": float(
            coverage.get("comparison_coverage_fraction") or 0.0
        ),
        "singleton_cell_count": int(coverage.get("singleton_cell_count") or 0),
        "selected_peer_groups": [
            {
                "peer_group_id": group.get("peer_group_id"),
                "peer_group": group.get("peer_group"),
                "entity_ids": [
                    member.get("entity_id")
                    for member in group.get("members") or ()
                    if isinstance(member, Mapping)
                ],
            }
            for group in plan.get("selected_groups") or ()
            if isinstance(group, Mapping)
        ],
        "residual_job_count": len(residual_members),
        "active_job_count": len(active),
        "next_due_at": None if status == "comparison_ready" else next_due_at,
        "source_run_sha256": plan.get("source_run_sha256"),
        "plan_sha256": plan.get("plan_sha256"),
        "next_activation": plan.get("next_activation"),
        "capital_authority": False,
    }


def _compile_workspace_broad_fund_acquisition(
    root: Path,
    config: Mapping[str, Any],
    *,
    compiled_at: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    policy = _broad_fund_policy(root, config)
    if policy is None:
        return None, None
    catalog = _read_json(root / "universe" / "catalog-latest.json")
    source_run = _current_source_run(root)
    if not catalog or not source_run:
        return None, None
    watchlists = [
        result for path in sorted((root / "watchlists" / "results").glob("*.json"))
        if (result := _read_json(path))
    ]
    scout = compile_broad_fund_scout(
        catalog, policy, watchlist_results=watchlists, completed_at=compiled_at,
    )
    plan = compile_broad_fund_acquisition_plan(
        scout=scout,
        catalog=catalog,
        policy=policy,
        source_manifest=load_source_manifest(
            root / str(config.get("source_manifest") or "sources.yaml")
        ),
        source_run=source_run,
        watchlist_results=watchlists,
        existing_jobs=_broad_fund_queue_rows(root),
        capital_market_basis=_read_json(
            root / "household" / "capital_market_basis" / "latest.json"
        ),
        compiled_at=compiled_at,
    )
    directory = root / "research_jobs" / "fund_acquisition"
    _atomic_json(directory / "scouts" / f"{scout['scout_sha256']}.json", scout)
    _atomic_json(directory / "runs" / f"{plan['plan_sha256']}.json", plan)
    _atomic_json(directory / "latest_scout.json", scout)
    _atomic_json(directory / "latest.json", plan)
    return scout, plan


def _prepare_broad_fund_acquisition(
    *,
    root: Path,
    config: Mapping[str, Any],
    policy: Mapping[str, Any],
    base_refresh_source_ids: set[str],
) -> dict[str, Any]:
    neutral_watchlist = _ensure_public_equity_etf_watchlist(root)
    scout, plan = _compile_workspace_broad_fund_acquisition(
        root, config, compiled_at=_utc_now(),
    )
    context: dict[str, Any] = {
        "scout": scout, "plan": plan, "jobs": [], "claimed_jobs": [],
        "reserved_funds": 0, "reserved_source_calls": 0,
        "reserved_research_minutes": 0,
        "neutral_equity_watchlist": neutral_watchlist,
    }
    if plan is None:
        return context
    queue_rows = _broad_fund_queue_rows(root)
    active_jobs = [
        dict(row.get("payload") or {}) for row in queue_rows
        if row.get("status") in {"queued", "claimed", "running"}
        and isinstance(row.get("payload"), Mapping)
    ]
    active_ids = {str(job.get("work_id") or "") for job in active_jobs}
    residual_jobs = []
    for job in plan.get("jobs") or ():
        if not isinstance(job, Mapping):
            continue
        work_id = f"fund-source:{job['job_sha256']}"
        if work_id not in active_ids:
            residual_jobs.append({**dict(job), "work_id": work_id})
    candidates = [
        job for job in (*active_jobs, *residual_jobs)
        if (job.get("comparison_cell") or {}).get("asset_class") == "equity"
        or (
            not job.get("comparison_cell")
            and job.get("implementation_sleeve_id") in {"us_equity", "international_equity"}
        )
    ]
    budgets = policy.get("budgets") if isinstance(policy.get("budgets"), Mapping) else {}
    costs = policy.get("cost_model") if isinstance(policy.get("cost_model"), Mapping) else {}
    fund_cost = costs.get("public_fund") if isinstance(costs.get("public_fund"), Mapping) else {}
    per_job_calls = max(0, int(fund_cost.get("incremental_source_calls", 0)))
    per_job_minutes = max(0, int(fund_cost.get("research_minutes", 0)))
    max_funds = max(0, int(budgets.get("max_funds", 0)))
    max_incremental = max(0, int(budgets.get("max_incremental_source_calls", 0)))
    max_total = max(0, int(budgets.get("max_total_source_calls", 0)))
    max_minutes = max(0, int(budgets.get("max_estimated_research_minutes", 0)))
    selected: list[dict[str, Any]] = []
    for index, raw in enumerate(candidates):
        if len(selected) >= max_funds:
            break
        next_calls = (len(selected) + 1) * per_job_calls
        next_minutes = (len(selected) + 1) * per_job_minutes
        if next_calls > max_incremental or len(base_refresh_source_ids) + next_calls > max_total:
            break
        if next_minutes > max_minutes:
            break
        body = {
            **raw,
            "schema": "jaggedthoughts-broad-fund-source-work-v1",
            "plan_sha256": plan["plan_sha256"],
            "selection_rank": index + 1,
            "cost": {
                "incremental_source_calls": per_job_calls,
                "research_minutes": per_job_minutes,
            },
            "stage": "queued",
            "capital_authority": False,
        }
        selected.append({**body, "work_sha256": stable_sha256(body)})
    enrolled = _enrolled_security_ids(root, config)
    to_enroll = [
        job for job in selected
        if str(job.get("security_id") or "") not in enrolled
        and (job.get("comparison_cell") or {}).get("asset_class") == "equity"
    ]
    enrollment = None
    if to_enroll:
        enrollment = enroll_public_funds(
            root,
            watchlist_path="watchlists/public_equity_etf_opportunities.yaml",
            funds=[{
                "ticker": job["entity_id"],
                "name": job["name"],
                "category": "broad regional comparison acquisition",
                "implementation_sleeve_id": job.get("implementation_sleeve_id"),
                "implementation_sleeve_source_refs": job.get(
                    "implementation_sleeve_source_refs"
                ),
                "peer_group_id": job.get("peer_group_id"),
                "comparison_cell": job.get("comparison_cell"),
            } for job in to_enroll],
        )
    existing_ids = {str(row.get("work_id") or "") for row in queue_rows}
    connection = work_queue.connect(str(root / "state" / "research_jobs.sqlite3"))
    try:
        for job in selected:
            work_queue.enqueue(
                connection,
                kind=BROAD_FUND_ACQUISITION_JOB_KIND,
                priority=100_000 - int(job["selection_rank"]),
                max_attempts=max(1, int(policy.get("max_attempts", 2))),
                payload=job,
            )
            if str(job["work_id"]) not in existing_ids:
                work_queue.append_event(
                    str(root / "research_jobs" / "enrichment" / "events.jsonl"),
                    {
                        "event_type": "investment_broad_fund_source_job_enqueued",
                        "payload": {
                            "work_id": job["work_id"], "job_sha256": job.get("job_sha256"),
                        },
                    },
                )
    finally:
        connection.close()
    worker_id = f"investment-fund-acquisition:{os.getpid()}:{str(plan['plan_sha256'])[:12]}"
    claimed = claim_cycle_jobs(
        db_path=root / "state" / "research_jobs.sqlite3",
        events_path=root / "research_jobs" / "enrichment" / "events.jsonl",
        jobs=selected,
        worker_id=worker_id,
        lease_seconds=max(60, int(policy.get("lease_seconds", 3600))),
    )
    context.update({
        "jobs": selected,
        "claimed_jobs": claimed,
        "worker_id": worker_id,
        "lease_seconds": max(60, int(policy.get("lease_seconds", 3600))),
        "reserved_funds": len(selected),
        "reserved_source_calls": len(selected) * per_job_calls,
        "reserved_research_minutes": len(selected) * per_job_minutes,
        "enrollment": enrollment,
    })
    return context


def _finish_broad_fund_acquisition(
    *, root: Path, context: Mapping[str, Any], post_plan: Mapping[str, Any] | None,
    fatal_error: str = "",
) -> None:
    residual = {
        str(member.get("security_id") or "")
        for group in (post_plan or {}).get("selected_groups") or () if isinstance(group, Mapping)
        for member in group.get("members") or () if isinstance(member, Mapping)
        and member.get("requested_coordinates")
    }
    connection = work_queue.connect(str(root / "state" / "research_jobs.sqlite3"))
    try:
        for job in context.get("claimed_jobs") or ():
            work_id = str(job["work_id"])
            result_status = (
                "retryable_source_error" if fatal_error else
                "typed_source_gap" if str(job.get("security_id") or "") in residual else
                "comparison_ready"
            )
            work_queue.heartbeat(
                connection,
                work_id=work_id,
                worker_id=str(context.get("worker_id") or ""),
                lease_s=int(context.get("lease_seconds") or 60),
                payload_update={
                    "stage": result_status,
                    "completed_at": _utc_now(),
                    "result_status": result_status,
                    "error": fatal_error or None,
                    "result_plan_sha256": (post_plan or {}).get("plan_sha256"),
                },
            )
            work_queue.finish_specific(
                connection,
                work_id=work_id,
                worker_id=str(context.get("worker_id") or ""),
                done=not fatal_error,
            )
    finally:
        connection.close()


def _resumable_enrichment_jobs(
    *, root: Path, queue_rows: Sequence[Mapping[str, Any]],
    cycle: Mapping[str, Any], enrolled_security_ids: set[str],
    exclude_work_ids: set[str], registry_source_calls: int = 1,
) -> list[dict[str, Any]]:
    """Resume interrupted acquisition work inside the current bounded budget."""
    screen = _read_json(root / "data" / "sec_frames" / "latest.json") or {}
    potential = {
        str(row.get("security_id") or ""): (
            int(row.get("rank") or 10**9),
            float(row.get("research_priority_score") or 0.0),
        )
        for row in screen.get("research_queue") or ()
        if isinstance(row, Mapping) and row.get("security_id")
    }
    catalog = _read_json(root / "universe" / "catalog-latest.json") or {}
    sector_by_security = {
        str(row.get("security_id") or ""): str(row.get("sector") or "").strip().lower()
        for row in catalog.get("securities") or () if isinstance(row, Mapping)
    }
    pending = []
    for row in queue_rows:
        payload = row.get("payload") if isinstance(row.get("payload"), Mapping) else {}
        if (
            row.get("kind") != ENRICHMENT_JOB_KIND
            or row.get("status") != "queued"
            or int(row.get("attempts") or 0) >= int(row.get("max_attempts") or 0)
            or str(row.get("work_id") or "") in exclude_work_ids
            or not potential
            or str(payload.get("security_id") or "") not in potential
        ):
            continue
        pending.append((dict(row), dict(payload)))
    pending.sort(key=lambda item: (
        item[1].get("security_id") not in potential,
        potential.get(str(item[1].get("security_id") or ""), (10**9, 0.0))[0],
        -int(item[0].get("priority") or 0),
        int(item[0].get("created_at") or 0),
        str(item[0].get("work_id") or ""),
    ))

    limits = dict(cycle.get("budget_limits") or {})
    usage = dict(cycle.get("budget_usage") or {})
    counts = {
        "public_equity": int(usage.get("equities") or 0),
        "public_fund": int(usage.get("funds") or 0),
    }
    sector_counts: Counter[str] = Counter()
    for candidate in cycle.get("candidates") or ():
        if not isinstance(candidate, Mapping) or candidate.get("selection_status") != "selected":
            continue
        sector = sector_by_security.get(str(candidate.get("security_id") or ""), "")
        if candidate.get("entity_kind") == "public_equity" and sector:
            sector_counts[sector] += 1
    incremental = int(usage.get("incremental_source_calls") or 0)
    total = int(usage.get("estimated_total_source_calls") or 0)
    minutes = int(usage.get("estimated_research_minutes") or 0)
    registry_used = int(usage.get("sec_registry_batch_source_calls") or 0)
    selected: list[dict[str, Any]] = []
    for _row, job in pending:
        kind = str(job.get("entity_kind") or "")
        if kind not in counts:
            continue
        kind_limit = int(limits.get("max_equities" if kind == "public_equity" else "max_funds") or 0)
        if counts[kind] >= kind_limit:
            continue
        sector = sector_by_security.get(str(job.get("security_id") or ""), "")
        if (
            kind == "public_equity" and sector
            and sector_counts[sector] >= int(limits.get("max_equities_per_sector") or 10**9)
        ):
            continue
        cost = dict(job.get("cost") or {})
        calls = int(cost.get("incremental_source_calls") or 0)
        research_minutes = int(cost.get("research_minutes") or 0)
        registry = max(0, int(registry_source_calls)) if (
            kind == "public_equity"
            and str(job.get("security_id") or "") not in enrolled_security_ids
            and registry_used == 0
        ) else 0
        if (
            incremental + calls > int(limits.get("max_incremental_source_calls") or 0)
            or total + calls + registry > int(limits.get("max_total_source_calls") or 0)
            or minutes + research_minutes > int(limits.get("max_estimated_research_minutes") or 0)
        ):
            continue
        selected.append(job)
        counts[kind] += 1
        incremental += calls
        total += calls + registry
        minutes += research_minutes
        registry_used += registry
        if kind == "public_equity" and sector:
            sector_counts[sector] += 1
    return selected


def _rebase_current_enrichment_priorities(
    *, db_path: Path, queue_rows: Sequence[Mapping[str, Any]],
    potential_screen: Mapping[str, Any],
) -> list[str]:
    """Make durable queued order agree with the current potential screen."""
    rank_by_security = {
        str(row.get("security_id") or ""): int(row.get("rank") or 0)
        for row in potential_screen.get("research_queue") or ()
        if isinstance(row, Mapping) and row.get("security_id") and int(row.get("rank") or 0) > 0
    }
    updates = [
        (research_rank_priority({"rank": rank}), str(row["work_id"]))
        for row in queue_rows
        if row.get("kind") == ENRICHMENT_JOB_KIND
        and row.get("status") == "queued"
        and (rank := rank_by_security.get(str((row.get("payload") or {}).get("security_id") or "")))
        and int(row.get("priority") or 0) != research_rank_priority({"rank": rank})
    ]
    if not updates:
        return []
    connection = work_queue.connect(str(db_path))
    try:
        connection.executemany(
            "UPDATE work_items SET priority=? WHERE work_id=? AND status='queued'",
            updates,
        )
        connection.commit()
    finally:
        connection.close()
    return [work_id for _priority, work_id in updates]


def _recover_interrupted_enrichment_jobs(
    *, db_path: Path, events_path: Path, queue_rows: Sequence[Mapping[str, Any]],
    current_security_ids: set[str], max_attempts: int,
) -> list[str]:
    """Requeue one current-potential acquisition epoch lost with its worker."""
    recovered: list[str] = []
    connection = work_queue.connect(str(db_path))
    try:
        for row in queue_rows:
            payload = row.get("payload") if isinstance(row.get("payload"), Mapping) else {}
            if (
                row.get("kind") != ENRICHMENT_JOB_KIND
                or row.get("status") != "dead_letter"
                or payload.get("result_status")
                or str(payload.get("security_id") or "") not in current_security_ids
                or int(payload.get("interruption_recoveries") or 0) >= 1
            ):
                continue
            recovery = {
                **payload,
                "stage": "queued",
                "interruption_recoveries": 1,
                "interruption_recovered_at": _utc_now(),
                "dead_letter_reason": None,
                "exit_kind": None,
                "ops_exit_kind": None,
            }
            work_queue.enqueue(
                connection, kind=ENRICHMENT_JOB_KIND,
                priority=int(row.get("priority") or 0),
                max_attempts=max(1, max_attempts), payload=recovery,
            )
            recovered.append(str(row["work_id"]))
        if recovered:
            work_queue.append_event(str(events_path), {
                "event_type": "investment_enrichment_interruptions_recovered",
                "payload": {"recovered_at": _utc_now(), "work_ids": recovered},
            })
    finally:
        connection.close()
    return recovered


def _supersede_out_of_scope_enrichment_jobs(
    *, db_path: Path, events_path: Path, queue_rows: Sequence[Mapping[str, Any]],
    current_security_ids: set[str], exclude_work_ids: set[str],
) -> list[str]:
    """Settle acquisition epochs no longer owned by the current potential screen."""
    if not current_security_ids:
        return []
    completed_at = _utc_now()
    superseded: list[str] = []
    connection = work_queue.connect(str(db_path))
    try:
        for row in queue_rows:
            payload = row.get("payload") if isinstance(row.get("payload"), Mapping) else {}
            work_id = str(row.get("work_id") or "")
            if (
                row.get("kind") != ENRICHMENT_JOB_KIND
                or row.get("status") != "queued"
                or work_id in exclude_work_ids
                or str(payload.get("security_id") or "") in current_security_ids
            ):
                continue
            work_queue.update_status(
                connection, work_id=work_id, status="done", payload_update={
                    "stage": "superseded",
                    "result_status": "superseded",
                    "completed_at": completed_at,
                    "provider_called": False,
                    "supersession_reason": "outside_current_investment_potential_scope",
                    "capital_authority": False,
                },
            )
            superseded.append(work_id)
        if superseded:
            work_queue.append_event(str(events_path), {
                "event_type": "investment_enrichment_jobs_superseded",
                "payload": {
                    "completed_at": completed_at,
                    "reason": "outside_current_investment_potential_scope",
                    "work_ids": superseded,
                },
            })
    finally:
        connection.close()
    return superseded


def _start_enrichment_lease_heartbeat(
    root: Path, contexts: Sequence[Mapping[str, Any]],
) -> tuple[Event, Thread] | None:
    active = [
        (
            str(context.get("worker_id") or ""),
            int(context.get("lease_seconds") or 0),
            [str(job.get("work_id") or "") for job in context.get("claimed_jobs") or ()],
        )
        for context in contexts
        if context.get("worker_id") and context.get("claimed_jobs")
    ]
    if not active:
        return None
    stop = Event()

    def beat() -> None:
        while not stop.wait(60):
            connection = work_queue.connect(str(root / "state" / "research_jobs.sqlite3"))
            try:
                for worker_id, lease_seconds, work_ids in active:
                    for work_id in work_ids:
                        work_queue.heartbeat(
                            connection, work_id=work_id, worker_id=worker_id,
                            lease_s=max(120, lease_seconds),
                        )
            finally:
                connection.close()

    thread = Thread(target=beat, name="investment-enrichment-lease", daemon=True)
    thread.start()
    return stop, thread


def _stop_enrichment_lease_heartbeat(heartbeat: tuple[Event, Thread] | None) -> None:
    if heartbeat is None:
        return
    stop, thread = heartbeat
    stop.set()
    thread.join(timeout=5)


def _prepare_autonomous_enrichment(
    *, root: Path, config: Mapping[str, Any], scout_cycle: Mapping[str, Any],
) -> dict[str, Any]:
    """Select, enqueue, lease, and batch-enroll one bounded acquisition cycle."""
    policy_path, policy = _enrichment_policy(root, config, materialize=True)
    equity_monitor_repair = repair_public_equity_monitor_sources(root)
    equity_quarterly_repair = repair_public_equity_quarterly_sources(root)
    fund_source_repair = repair_public_fund_sources(root)
    base_refresh_source_ids = _baseline_refresh_source_ids(root, config, policy)
    base_refresh_source_ids.update(
        str(value) for value in fund_source_repair.get("added_source_ids") or ()
    )
    if not bool(policy.get("enabled", True)):
        return {
            "status": "disabled", "policy": policy,
            "policy_path": policy_path.relative_to(root).as_posix(),
            "claimed_jobs": [], "jobs": [], "enrollment_errors": {},
            "fund_source_repair": fund_source_repair,
            "equity_monitor_repair": equity_monitor_repair,
            "equity_quarterly_repair": equity_quarterly_repair,
            "equity_quarterly_repair": equity_quarterly_repair,
            "refresh_source_ids": sorted(base_refresh_source_ids),
        }
    refresh_policy = (
        policy.get("source_refresh")
        if isinstance(policy.get("source_refresh"), Mapping) else {}
    )
    max_total_source_calls = int((policy.get("budgets") or {}).get("max_total_source_calls", 0))
    if len(base_refresh_source_ids) > max_total_source_calls:
        raise ValueError(
            "enrichment baseline refresh requires "
            f"{len(base_refresh_source_ids)} sources but max_total_source_calls is "
            f"{max_total_source_calls}"
        )
    broad_fund_acquisition = _prepare_broad_fund_acquisition(
        root=root,
        config=config,
        policy=policy,
        base_refresh_source_ids=base_refresh_source_ids,
    )
    for job in broad_fund_acquisition.get("claimed_jobs") or ():
        base_refresh_source_ids.update(str(value) for value in job.get("source_requirements") or ())
    broad_plan = broad_fund_acquisition.get("plan") or {}
    factor_batch = (broad_plan.get("shared_source_batches") or {}).get("factor_benchmarks") or {}
    base_refresh_source_ids.update(
        str(value) for value in factor_batch.get("source_ids") or ()
        if value not in set(factor_batch.get("missing_source_ids") or ())
    )
    cycle_policy = dict(policy)
    cycle_budgets = dict(policy.get("budgets") or {})
    cycle_budgets["max_funds"] = max(
        0,
        int(cycle_budgets.get("max_funds", 0))
        - int(broad_fund_acquisition.get("reserved_funds") or 0),
    )
    cycle_budgets["max_incremental_source_calls"] = max(
        0,
        int(cycle_budgets.get("max_incremental_source_calls", 0))
        - int(broad_fund_acquisition.get("reserved_source_calls") or 0),
    )
    cycle_budgets["max_estimated_research_minutes"] = max(
        0,
        int(cycle_budgets.get("max_estimated_research_minutes", 0))
        - int(broad_fund_acquisition.get("reserved_research_minutes") or 0),
    )
    cycle_policy["budgets"] = cycle_budgets
    reserve = max(0, int(refresh_policy.get("reserved_maintenance_source_calls", 0)))
    reserved_maintenance = _maintenance_refresh_source_ids(
        root, config, policy, already_selected=base_refresh_source_ids,
        remaining_calls=reserve,
    )
    base_refresh_source_ids.update(reserved_maintenance["source_ids"])
    effective_cycle = (
        scout_cycle.get("latest_cycle")
        if scout_cycle.get("status") == "not_due"
        and isinstance(scout_cycle.get("latest_cycle"), Mapping)
        else scout_cycle
    )
    runs = _scout_runs_for_cycle(root, effective_cycle)
    if not runs:
        return {
            "status": "no_scout_runs", "policy": policy,
            "policy_path": policy_path.relative_to(root).as_posix(),
            "claimed_jobs": [], "jobs": [], "enrollment_errors": {},
            "fund_source_repair": fund_source_repair,
            "equity_monitor_repair": equity_monitor_repair,
            "refresh_source_ids": sorted(base_refresh_source_ids),
            "broad_fund_acquisition": broad_fund_acquisition,
            "maintenance_refresh": reserved_maintenance,
        }
    queue_db = root / "state" / "research_jobs.sqlite3"
    events_path = root / "research_jobs" / "enrichment" / "events.jsonl"
    prior = research_job_snapshot(queue_db, limit=10_000)["jobs"]
    enrolled_security_ids = _enrolled_security_ids(root, config)
    cycle = compile_enrichment_cycle(
        scout_runs=runs, policy=cycle_policy,
        enrolled_security_ids=enrolled_security_ids,
        prior_jobs=prior,
        enabled_source_count=len(base_refresh_source_ids),
    )
    new_jobs = enqueue_cycle_jobs(
        db_path=queue_db, events_path=events_path, cycle=cycle,
        max_attempts=max(1, int(policy.get("max_attempts", 2))),
    )
    potential_screen = _read_json(root / "data" / "sec_frames" / "latest.json") or {}
    current_potential_ids = {
        str(row.get("security_id") or "")
        for row in potential_screen.get("research_queue") or ()
        if isinstance(row, Mapping) and row.get("security_id")
    }
    recovered_work_ids = _recover_interrupted_enrichment_jobs(
        db_path=queue_db, events_path=events_path, queue_rows=prior,
        current_security_ids=current_potential_ids,
        max_attempts=max(1, int(policy.get("max_attempts", 2))),
    )
    if recovered_work_ids:
        prior = research_job_snapshot(queue_db, limit=10_000)["jobs"]
    reprioritized_work_ids = _rebase_current_enrichment_priorities(
        db_path=queue_db,
        queue_rows=research_job_snapshot(queue_db, limit=10_000)["jobs"],
        potential_screen=potential_screen,
    )
    superseded_work_ids = _supersede_out_of_scope_enrichment_jobs(
        db_path=queue_db, events_path=events_path, queue_rows=prior,
        current_security_ids=current_potential_ids,
        exclude_work_ids={str(job["work_id"]) for job in new_jobs},
    )
    resumed_jobs = _resumable_enrichment_jobs(
        root=root,
        queue_rows=prior,
        cycle=cycle,
        enrolled_security_ids=enrolled_security_ids,
        exclude_work_ids={str(job["work_id"]) for job in new_jobs},
        registry_source_calls=int(
            (cycle_policy.get("cost_model") or {}).get(
                "sec_registry_batch_source_calls", 1,
            )
        ),
    )
    paths = materialize_cycle(root, cycle, new_jobs)
    current_potential_rank = {
        str(row.get("security_id") or ""): int(row.get("rank") or 10**9)
        for row in potential_screen.get("research_queue") or ()
        if isinstance(row, Mapping) and row.get("security_id")
    }
    jobs = sorted(
        [*new_jobs, *resumed_jobs],
        key=lambda job: (
            current_potential_rank.get(str(job.get("security_id") or ""), 10**9),
            -int(round(float(job.get("acquisition_priority") or 0.0) * 100_000)),
            str(job.get("security_id") or ""),
        ),
    )
    resumed_equities = sum(job.get("entity_kind") == "public_equity" for job in resumed_jobs)
    resumed_funds = sum(job.get("entity_kind") == "public_fund" for job in resumed_jobs)
    resumed_calls = sum(int((job.get("cost") or {}).get("incremental_source_calls") or 0) for job in resumed_jobs)
    resumed_minutes = sum(int((job.get("cost") or {}).get("research_minutes") or 0) for job in resumed_jobs)
    resumed_registry = int(bool({
        str(job.get("security_id") or "") for job in resumed_jobs
        if job.get("entity_kind") == "public_equity"
        and str(job.get("security_id") or "") not in enrolled_security_ids
    })) * int((cycle_policy.get("cost_model") or {}).get("sec_registry_batch_source_calls", 1))
    resumed_budget_usage = {
        "equities": resumed_equities,
        "funds": resumed_funds,
        "incremental_source_calls": resumed_calls,
        "sec_registry_batch_source_calls": resumed_registry,
        "estimated_research_minutes": resumed_minutes,
        "estimated_total_source_calls": resumed_calls + resumed_registry,
    }
    context: dict[str, Any] = {
        "status": "no_candidates" if not jobs else "queued",
        "policy": policy,
        "policy_path": policy_path.relative_to(root).as_posix(),
        "cycle": cycle, "jobs": jobs, "claimed_jobs": [],
        "cycle_path": paths["cycle_path"], "queue_db": queue_db,
        "events_path": events_path, "enrollment_errors": {},
        "owner": str(config.get("owner") or "operator-paper-book"),
        "store_path": _store_path(root, config),
        "equity_enrollment": None, "fund_enrollment": None,
        "fund_source_repair": fund_source_repair,
        "equity_monitor_repair": equity_monitor_repair,
        "equity_quarterly_repair": equity_quarterly_repair,
        "refresh_source_ids": sorted(base_refresh_source_ids),
        "maintenance_refresh": reserved_maintenance,
        "broad_fund_acquisition": broad_fund_acquisition,
        "resumed_job_count": len(resumed_jobs),
        "resumed_work_ids": [str(job["work_id"]) for job in resumed_jobs],
        "resumed_budget_usage": resumed_budget_usage,
        "superseded_work_ids": superseded_work_ids,
        "recovered_interruption_work_ids": recovered_work_ids,
        "reprioritized_work_ids": reprioritized_work_ids,
    }
    if not jobs:
        if bool(policy.get("auto_fetch_public_data", True)):
            _attach_maintenance_refresh(root, config, context)
        return context
    if not (
        bool(policy.get("auto_enroll", True))
        and bool(policy.get("auto_fetch_public_data", True))
    ):
        return context
    lease_seconds = max(60, int(policy.get("lease_seconds", 3600)))
    worker_id = f"investment-discovery:{os.getpid()}:{str(cycle['cycle_sha256'])[:12]}"
    claimed = claim_cycle_jobs(
        db_path=queue_db, events_path=events_path, jobs=jobs,
        worker_id=worker_id, lease_seconds=lease_seconds,
    )
    context.update({
        "status": "enriching" if claimed else "lease_busy",
        "claimed_jobs": claimed, "worker_id": worker_id,
        "lease_seconds": lease_seconds,
    })
    if not claimed:
        _attach_maintenance_refresh(root, config, context)
        return context
    enrolled = _enrolled_security_ids(root, config)
    equities = [
        job for job in claimed
        if job.get("entity_kind") == "public_equity"
        and str(job.get("security_id") or "") not in enrolled
    ]
    funds = [
        job for job in claimed
        if job.get("entity_kind") == "public_fund"
        and str(job.get("security_id") or "") not in enrolled
    ]
    if equities:
        try:
            context["equity_enrollment"] = enroll_public_equities(
                root, tickers=[str(job["symbol"]) for job in equities],
            )
        except (OSError, TypeError, ValueError) as error:
            for job in equities:
                context["enrollment_errors"][str(job["symbol"])] = str(error)
    if funds:
        try:
            context["fund_enrollment"] = enroll_public_funds(
                root,
                funds=[{
                    "ticker": job["symbol"], "name": job["name"],
                    "category": "autonomous scout acquisition",
                } for job in funds],
            )
        except (OSError, TypeError, ValueError) as error:
            for job in funds:
                context["enrollment_errors"][str(job["symbol"])] = str(error)
    selected_source_ids = set(context["refresh_source_ids"])
    for row in (context.get("equity_enrollment") or {}).get("enrollments") or ():
        selected_source_ids.update(str(value) for value in row.get("source_ids") or ())
    for row in (context.get("fund_enrollment") or {}).get("enrollments") or ():
        selected_source_ids.update(str(value) for value in row.get("source_ids") or ())
    claimed_entities = {
        str(job.get("symbol") or job.get("entity_id") or "").upper()
        for job in claimed
    }
    manifest = load_source_manifest(
        root / str(config.get("source_manifest") or "sources.yaml")
    )
    claimed_source_bindings: dict[str, list[str]] = {}
    for row in manifest.get("sources") or ():
        if not isinstance(row, Mapping) or row.get("enabled", True) is False:
            continue
        entity = str(row.get("entity_id") or "").upper()
        source_id = str(row.get("id") or "")
        if entity in claimed_entities and source_id:
            selected_source_ids.add(source_id)
            claimed_source_bindings.setdefault(entity, []).append(source_id)
    context["claimed_source_bindings"] = {
        entity: sorted(source_ids)
        for entity, source_ids in sorted(claimed_source_bindings.items())
    }
    context["refresh_source_ids"] = sorted(selected_source_ids)
    _attach_maintenance_refresh(root, config, context)
    return context


def _finalize_autonomous_enrichment(
    *, root: Path, context: Mapping[str, Any],
    source_run: Mapping[str, Any] | None,
    discovery_run: Mapping[str, Any] | None,
    discovery_record: Mapping[str, Any] | None,
    fatal_error: str = "",
) -> dict[str, Any]:
    claimed = list(context.get("claimed_jobs") or ())
    cycle = context.get("cycle") if isinstance(context.get("cycle"), Mapping) else {}
    cycle_usage = dict(cycle.get("budget_usage") or {})
    resumed_usage = dict(context.get("resumed_budget_usage") or {})
    execution_budget_usage = dict(cycle_usage)
    for key, value in resumed_usage.items():
        execution_budget_usage[key] = int(execution_budget_usage.get(key) or 0) + int(value or 0)
    candidates = [
        row for row in (discovery_run or {}).get("candidates") or ()
        if isinstance(row, Mapping)
    ]
    leaves = (
        discovery_record.get("candidate_leaves")
        if isinstance(discovery_record, Mapping)
        and isinstance(discovery_record.get("candidate_leaves"), Mapping)
        else {}
    )
    recovered: list[dict[str, Any]] = []
    strategy_frontiers = _strategy_frontier_index(root)
    routing_decision, learning_credit_assignment, current_research_learning = (
        _current_research_routing_inputs(root)
    )
    if (
        not fatal_error and candidates and leaves
        and context.get("queue_db") and context.get("events_path")
        and context.get("store_path") and context.get("owner")
    ):
        existing_request_leaves = {
            str(payload.get("candidate_leaf") or "")
            for path in (root / "research_jobs" / "requests").glob("*.json")
            if (payload := _read_json(path))
        }
        for row in research_job_snapshot(context["queue_db"], limit=10_000)["jobs"]:
            job = row.get("payload") if isinstance(row.get("payload"), Mapping) else {}
            if job.get("result_status") != "blocked":
                continue
            candidate = next((
                item for item in candidates
                if str(item.get("entity_id") or "").upper() == str(job.get("symbol") or "").upper()
                and item.get("entity_kind") == job.get("entity_kind")
            ), None)
            candidate_leaf = str(leaves.get(str((candidate or {}).get("candidate_id") or "")) or "")
            if (
                not candidate or not candidate_leaf or candidate_leaf in existing_request_leaves
                or candidate.get("screen_status") in {"blocked", "stale_evidence"}
            ):
                continue
            request = compile_research_request(
                job=job, candidate=candidate, candidate_leaf=candidate_leaf,
                discovery_run=discovery_run or {},
                research_basis_sources=_research_basis_source_snapshot(
                    root, str(candidate["entity_id"]),
                ),
                routing_decision=routing_decision,
                learning_credit_assignment=learning_credit_assignment,
                current_research_learning=current_research_learning,
                strategy_frontier=_strategy_frontier_for_candidate(
                    strategy_frontiers, candidate,
                ),
            )
            request_leaf = record_agent_research_request(
                GoldenStore(context["store_path"]),
                owner=str(context["owner"]), request=request,
            )
            result = materialize_job_result(
                root, job=job,
                result={
                    "completed_at": _utc_now(), "result_status": "evidence_ready",
                    "candidate_leaf": candidate_leaf,
                    "candidate_sha256": candidate.get("candidate_sha256"),
                    "discovery_run_id": (discovery_run or {}).get("run_id"),
                    "source_run_sha256": (source_run or {}).get("run_sha256"),
                    "research_request_leaf": request_leaf,
                    "error": None,
                },
                research_request=request,
            )
            recover_completed_job(
                db_path=context["queue_db"], events_path=context["events_path"],
                job=job, result=result,
            )
            recovered.append({**result, "recovered_from_block": True})
            existing_request_leaves.add(candidate_leaf)
    if not claimed:
        body = {
            "schema": ENRICHMENT_EXECUTION_SCHEMA,
            "ok": context.get("status") not in {"error"},
            "status": context.get("status") or "not_run",
            "completed_at": _utc_now(),
            "policy_path": context.get("policy_path"),
            "cycle_sha256": cycle.get("cycle_sha256"),
            "cycle_path": context.get("cycle_path"),
            "selected_count": len(context.get("jobs") or ()),
            "completed_job_count": 0,
            "evidence_ready_count": len(recovered),
            "blocked_count": 0,
            "recovered_job_count": len(recovered),
            "resumed_job_count": int(context.get("resumed_job_count") or 0),
            "resumed_work_ids": list(context.get("resumed_work_ids") or ()),
            "resumed_budget_usage": context.get("resumed_budget_usage"),
            "superseded_work_ids": list(context.get("superseded_work_ids") or ()),
            "recovered_interruption_work_ids": list(
                context.get("recovered_interruption_work_ids") or ()
            ),
            "results": recovered,
            "budget_usage": cycle.get("budget_usage"),
            "execution_budget_usage": execution_budget_usage,
            "maintenance_refresh": context.get("maintenance_refresh"),
            "source_refresh_plan": context.get("source_refresh_plan"),
            "fund_source_repair": context.get("fund_source_repair"),
            "capital_authority": False,
        }
        execution = {**body, "execution_sha256": stable_sha256(body)}
        _atomic_json(
            root / "research_jobs" / "enrichment" / "latest_execution.json",
            execution,
        )
        return execution
    results: list[dict[str, Any]] = list(recovered)
    ready = len(recovered)
    blocked = 0
    for job in claimed:
        symbol = str(job["symbol"]).upper()
        kind = str(job["entity_kind"])
        candidate = next((
            row for row in candidates
            if str(row.get("entity_id") or "").upper() == symbol
            and row.get("entity_kind") == kind
        ), None)
        candidate_leaf = str(leaves.get(str((candidate or {}).get("candidate_id") or "")) or "")
        error = (
            fatal_error
            or str((context.get("enrollment_errors") or {}).get(symbol) or "")
        )
        status = "evidence_ready"
        if not candidate or not candidate_leaf:
            status = "blocked"
            error = error or "deep discovery produced no addressable candidate leaf"
        elif candidate.get("screen_status") in {"blocked", "stale_evidence"}:
            status = "blocked"
            error = error or str(candidate.get("error") or candidate.get("next_activation") or "evidence blocked")
        request: dict[str, Any] | None = None
        request_leaf: str | None = None
        if status == "evidence_ready" and candidate is not None:
            request = compile_research_request(
                job=job, candidate=candidate, candidate_leaf=candidate_leaf,
                discovery_run=discovery_run or {},
                research_basis_sources=_research_basis_source_snapshot(
                    root, str(candidate["entity_id"]),
                ),
                routing_decision=routing_decision,
                learning_credit_assignment=learning_credit_assignment,
                current_research_learning=current_research_learning,
                strategy_frontier=_strategy_frontier_for_candidate(
                    strategy_frontiers, candidate,
                ),
            )
            request_leaf = record_agent_research_request(
                GoldenStore(context["store_path"]),
                owner=str(context["owner"]), request=request,
            )
            ready += 1
        else:
            blocked += 1
        result = materialize_job_result(
            root, job=job,
            result={
                "completed_at": _utc_now(), "result_status": status,
                "candidate_leaf": candidate_leaf or None,
                "candidate_sha256": (candidate or {}).get("candidate_sha256"),
                "discovery_run_id": (discovery_run or {}).get("run_id"),
                "source_run_sha256": (source_run or {}).get("run_sha256"),
                "research_request_leaf": request_leaf,
                "error": error or None,
            },
            research_request=request,
        )
        finish_claimed_job(
            db_path=context["queue_db"], events_path=context["events_path"],
            job=job, worker_id=str(context["worker_id"]), result=result,
            lease_seconds=int(context["lease_seconds"]),
        )
        results.append(result)
    body: dict[str, Any] = {
        "schema": ENRICHMENT_EXECUTION_SCHEMA,
        "ok": not fatal_error,
        "status": "completed" if not fatal_error else "blocked",
        "completed_at": _utc_now(),
        "policy_path": context.get("policy_path"),
        "cycle_sha256": cycle.get("cycle_sha256"),
        "cycle_path": context.get("cycle_path"),
        "selected_count": len(context.get("jobs") or ()),
        "claimed_count": len(claimed),
        "completed_job_count": len(results),
        "evidence_ready_count": ready,
        "blocked_count": blocked,
        "recovered_job_count": len(recovered),
        "resumed_job_count": int(context.get("resumed_job_count") or 0),
        "resumed_work_ids": list(context.get("resumed_work_ids") or ()),
        "resumed_budget_usage": context.get("resumed_budget_usage"),
        "superseded_work_ids": list(context.get("superseded_work_ids") or ()),
        "recovered_interruption_work_ids": list(
            context.get("recovered_interruption_work_ids") or ()
        ),
        "budget_usage": cycle.get("budget_usage"),
        "execution_budget_usage": execution_budget_usage,
        "maintenance_refresh": context.get("maintenance_refresh"),
        "source_refresh_plan": context.get("source_refresh_plan"),
        "equity_enrollment": context.get("equity_enrollment"),
        "fund_enrollment": context.get("fund_enrollment"),
        "fund_source_repair": context.get("fund_source_repair"),
        "results": results,
        "fatal_error": fatal_error or None,
        "capital_authority": False,
    }
    execution = {**body, "execution_sha256": stable_sha256(body)}
    stamp = timestamp_key(str(execution["completed_at"])).strftime("%Y%m%d%H%M%S")
    path = root / "research_jobs" / "enrichment" / "executions" / (
        f"execution-{stamp}-{str(execution['execution_sha256'])[:8]}.json"
    )
    _atomic_json(path, execution)
    _atomic_json(root / "research_jobs" / "enrichment" / "latest_execution.json", execution)
    return {**execution, "execution_path": path.relative_to(root).as_posix()}


class StrategyFrontierHeadChangedError(RuntimeError):
    """The company frontier changed before a prepared successor could publish."""

    def __init__(self, *, expected: str, current: str) -> None:
        self.expected = expected
        self.current = current
        super().__init__(
            "company strategy frontier head changed before publication: "
            f"expected {expected or '<absent>'}, found {current or '<absent>'}"
        )


def compile_workspace_company_strategy(
    profile: str | Path,
    workspace: str | Path | None = None,
    *, refresh_read_model: bool = True,
    expected_head_sha256: str | None = None,
) -> dict[str, Any]:
    """Compile one source-authored industry option space into a frontier."""
    root, config = load_workspace_config(workspace)
    source = Path(profile).expanduser()
    if not source.is_absolute():
        source = root / source
    source = source.resolve()
    payload, _migration = normalize_strategy_measurement_parent_profile(_load_yaml(source))
    result = compile_company_strategy_frontier(payload)
    company_id = str((result.get("company") or {}).get("id") or "company").lower()
    destination = root / "strategy_frontiers" / "results" / (
        f"{company_id}-{result['strategy_frontier_sha256'][:12]}.json"
    )
    head_path = root / "strategy_frontiers" / "heads" / f"{company_id}.json"
    state_dir = root / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    with (state_dir / "strategy_frontier_publish.lock").open("a+b") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        current_head_sha256 = str(
            (_read_json(head_path) or {}).get("strategy_frontier_sha256") or ""
        )
        if (
            expected_head_sha256 is not None
            and current_head_sha256 != expected_head_sha256
        ):
            raise StrategyFrontierHeadChangedError(
                expected=expected_head_sha256, current=current_head_sha256,
            )
        _atomic_json(destination, result)
        _atomic_json(head_path, result)
        _atomic_json(root / "strategy_frontiers" / "latest.json", result)
        strategy_move_library = compile_workspace_strategy_move_library(root)
        _atomic_json(
            root / "institutional_learning" / "strategy_moves" / "latest.json",
            strategy_move_library,
        )
        strategy_move_leaf = record_strategy_move_library(
            GoldenStore(_store_path(root, config)),
            owner=str(config.get("owner") or "operator-paper-book"),
            library=strategy_move_library,
        )
    read_model = build_read_model(root) if refresh_read_model else None
    if read_model is not None:
        company_rows = [
            row for row in read_model.get("company_strategy_frontiers") or ()
            if str((row.get("company") or {}).get("id") or "").upper()
            != str((result.get("company") or {}).get("id") or "").upper()
        ]
        company_rows.append(_ui_strategy_frontier({
            **result, "result_path": destination.relative_to(root).as_posix(),
        }))
        summary = dict(read_model.get("summary") or {})
        summary.update({
            "company_strategy_frontier_count": len(company_rows),
            "strategy_move_count": strategy_move_library["move_count"],
            "measurable_strategy_move_count": strategy_move_library["measurable_move_count"],
            "strategy_move_outcome_episode_count": strategy_move_library["outcome_episode_count"],
        })
        read_model = {
            **read_model,
            "company_strategy_frontiers": sorted(
                company_rows, key=lambda row: str((row.get("company") or {}).get("id") or ""),
            ),
            "strategy_move_learning": strategy_move_library,
            "summary": summary,
        }
        read_model = {
            **{key: value for key, value in read_model.items() if key != "read_model_sha256"},
            "read_model_sha256": stable_sha256({
                key: value for key, value in read_model.items() if key != "read_model_sha256"
            }),
        }
        _atomic_json(root / "state" / "read_model.json", read_model)
    return {
        "ok": True, "result": result,
        "result_path": destination.relative_to(root).as_posix(),
        "strategy_move_library_sha256": strategy_move_library["library_sha256"],
        "strategy_move_golden_leaf": strategy_move_leaf,
        "read_model": read_model,
    }


def select_workspace_company_contingent_recourse(
    request: str | Path, workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Select and record one frozen company-policy branch from later observations."""
    root, config = load_workspace_config(workspace)
    source = Path(request).expanduser()
    if not source.is_absolute():
        source = root / source
    payload = _read_json(source.resolve())
    if payload is None:
        raise ValueError(f"contingent recourse request must be a JSON object: {source}")
    if payload.get("schema") != "jaggedthoughts-company-contingent-recourse-request-v1":
        raise ValueError("unsupported contingent recourse request schema")
    company_id = require_text(payload.get("company_id"), "recourse company_id")
    policy_id = require_text(payload.get("policy_id"), "recourse policy_id")
    frontier = _read_json(
        root / "strategy_frontiers" / "heads" / f"{company_id.lower()}.json"
    )
    if not frontier or str((frontier.get("company") or {}).get("id")) != company_id:
        raise ValueError("contingent recourse requires the current company frontier")
    matches = [
        row for row in frontier.get("contingent_policy_catalog") or ()
        if str(row.get("policy_id")) == policy_id
    ]
    if len(matches) != 1:
        raise ValueError("contingent recourse requires exactly one current policy")
    observations = tuple(
        MetricObservation(
            observation_id=row.get("observation_id"),
            entity_id=row.get("entity_id"), metric_id=row.get("metric_id"),
            value=row.get("value"), unit=row.get("unit"),
            observed_at=row.get("observed_at"), available_at=row.get("available_at"),
            source_ref=row.get("source_ref"),
        )
        for row in payload.get("observations") or ()
        if isinstance(row, Mapping)
    )
    if len(observations) != len(payload.get("observations") or ()) or not observations:
        raise ValueError("contingent recourse observations must be nonempty objects")
    policy = matches[0]
    selection = select_company_contingent_recourse(
        policy, evaluated_at=payload.get("evaluated_at"), observations=observations,
    )
    destination = root / "strategy_frontiers" / "recourse" / (
        f"{company_id.lower()}-{policy_id}-{selection['selection_sha256'][:12]}.json"
    )
    _atomic_json(destination, selection)
    leaves = record_company_contingent_recourse_selection(
        GoldenStore(_store_path(root, config)),
        owner=str(config.get("owner") or "operator-paper-book"),
        policy=policy, selection=selection,
    )
    return {
        "schema": "jaggedthoughts-company-contingent-recourse-workspace-receipt-v1",
        "ok": True, "selection": selection,
        "artifact_path": destination.relative_to(root).as_posix(),
        "golden_leaves": leaves, "capital_authority": False,
    }


def submit_workspace_strategy_outcome(
    outcome: str | Path,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Validate and record one matured, exact-move business outcome."""
    root, _config = load_workspace_config(workspace)
    source = Path(outcome).expanduser()
    if not source.is_absolute():
        source = root / source
    raw = _read_json(source.resolve())
    if raw is None:
        raise ValueError(f"strategy outcome must be a JSON object: {source}")

    prior = compile_workspace_strategy_move_library(root)
    compiled = compile_workspace_strategy_move_library(root, extra_outcomes=(raw,))
    prior_episode_ids = {
        str(episode["episode_sha256"])
        for move in prior["moves"] for episode in move["outcome_episodes"]
    }
    candidate_episodes = [
        episode
        for move in compiled["moves"] for episode in move["outcome_episodes"]
        if str(episode["episode_sha256"]) not in prior_episode_ids
    ]
    replayed = not candidate_episodes
    if replayed:
        observed_at = canonical_timestamp(
            raw.get("observed_at"), "strategy outcome observed_at",
        )
        candidate_episodes = [
            episode
            for move in compiled["moves"] for episode in move["outcome_episodes"]
            if episode["move_sha256"] == raw.get("move_sha256")
            and episode["contract_sha256"] == raw.get("contract_sha256")
            and episode["observed_at"] == observed_at
        ]
    if len(candidate_episodes) != 1:
        raise ValueError("strategy outcome must resolve to exactly one outcome episode")

    episode = candidate_episodes[0]
    destination = root / "institutional_learning" / "strategy_outcomes" / (
        f"strategy-outcome-{episode['episode_sha256'][:16]}.json"
    )
    if not replayed:
        _atomic_json(destination, raw)
    build = build_workspace(root)
    strategy_status = dict(build.get("strategy_move_status") or {})
    return {
        "schema": "jaggedthoughts-strategy-move-outcome-submission-v1",
        "ok": strategy_status.get("status") == "compiled",
        "replayed": replayed,
        "episode": episode,
        "outcome_path": destination.relative_to(root).as_posix(),
        "library_sha256": strategy_status.get("library_sha256"),
        "golden_leaf": strategy_status.get("golden_leaf"),
        "build_ok": bool(build.get("ok")),
        "capital_authority": False,
    }


def run_workspace_market_flow_experiment(
    profile: str | Path,
    workspace: str | Path | None = None,
    *,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Run one isolated market-flow diagnostic and record its immutable leaf."""
    root, config = load_workspace_config(workspace)
    profile_path = Path(profile).expanduser()
    if not profile_path.is_absolute():
        profile_path = root / profile_path
    profile_path = profile_path.resolve()
    result = compile_market_flow_backtest(profile_path, workspace=root)
    destination_root = (
        Path(output_dir).expanduser().resolve()
        if output_dir else root / "experiments" / "runs"
    )
    destination = destination_root / f"{result['experiment_id']}-{result['market_flow_backtest_sha256'][:12]}.json"
    _atomic_json(destination, result)
    store = GoldenStore(_store_path(root, config))
    prior_leaves = [
        row for row in store.list_leaves(object_kind="market_flow_experiment", limit=10_000)
        if str(row.get("owner")) == str(config.get("owner") or "operator-paper-book")
        and str(row.get("object_id")) == str(result["experiment_id"])
    ]
    leaf = record_market_flow_experiment(
        store, owner=str(config.get("owner") or "operator-paper-book"), result=result,
    )
    supersedes_leaf = next(
        (str(row["leaf_sha256"]) for row in prior_leaves if str(row["leaf_sha256"]) != leaf),
        None,
    )
    if supersedes_leaf:
        store.append_edge(GoldenEdge(
            src_leaf_sha256=leaf,
            dst_leaf_sha256=supersedes_leaf,
            relation="supersedes",
            metadata={
                "reason": "new market-flow implementation epoch",
                "implementation_id": result["implementation_id"],
            },
        ))
    summary = {key: value for key, value in result.items() if key != "episodes"}
    try:
        artifact_path = destination.relative_to(root).as_posix()
    except ValueError:
        artifact_path = str(destination)
    summary.update({
        "artifact_path": artifact_path, "golden_leaf": leaf,
        "supersedes_leaf": supersedes_leaf,
    })
    summary_path = root / "experiments" / "results" / f"{result['experiment_id']}.json"
    _atomic_json(summary_path, summary)
    read_model = build_read_model(root)
    _atomic_json(root / "state" / "read_model.json", read_model)
    return {
        "schema": "jaggedthoughts-market-flow-workspace-run-v1",
        "ok": True,
        "result": summary,
        "artifact_path": artifact_path,
        "summary_path": summary_path.relative_to(root).as_posix(),
        "golden_leaf": leaf,
        "supersedes_leaf": supersedes_leaf,
        "read_model": read_model,
    }


def run_workspace_cross_sectional_flow_evidence(
    profile: str | Path,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Freeze the exact panel evidence packet consumed by Newton search."""
    root, config = load_workspace_config(workspace)
    profile_path = Path(profile).expanduser()
    if not profile_path.is_absolute():
        profile_path = root / profile_path
    result = compile_cross_sectional_flow_evidence(profile_path.resolve(), workspace=root)
    artifact = root / "experiments" / "runs" / (
        f"{result['experiment_id']}-{result['evidence_sha256'][:12]}.json"
    )
    _atomic_json(artifact, result)
    leaf = record_market_flow_experiment(
        GoldenStore(_store_path(root, config)),
        owner=str(config.get("owner") or "operator-paper-book"),
        result=result,
    )
    summary = {key: value for key, value in result.items() if key != "partitions"}
    summary.update({"artifact_path": artifact.relative_to(root).as_posix(), "golden_leaf": leaf})
    summary_path = root / "experiments" / "results" / f"{result['experiment_id']}.json"
    _atomic_json(summary_path, summary)
    return {
        "schema": "jaggedthoughts-cross-sectional-flow-workspace-run-v1",
        "ok": True,
        "result": summary,
        "artifact_path": artifact.relative_to(root).as_posix(),
        "summary_path": summary_path.relative_to(root).as_posix(),
        "golden_leaf": leaf,
        "capital_authority": False,
    }


def run_workspace_company_state_flow_experiment(
    profile: str | Path,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Compile and record the persistent-company probability-current diagnostic."""
    root, config = load_workspace_config(workspace)
    profile_path = Path(profile).expanduser()
    if not profile_path.is_absolute():
        profile_path = root / profile_path
    result = compile_company_state_flow_evidence(profile_path.resolve(), workspace=root)
    artifact = root / "experiments" / "runs" / (
        f"{result['experiment_id']}-{result['evidence_sha256'][:12]}.json"
    )
    _atomic_json(artifact, result)
    store = GoldenStore(_store_path(root, config))
    leaf = record_market_flow_experiment(
        store, owner=str(config.get("owner") or "operator-paper-book"), result=result,
    )
    summary = {
        key: value for key, value in result.items()
        if key not in {"partitions", "transition_blocks"}
    }
    summary.update({"artifact_path": artifact.relative_to(root).as_posix(), "golden_leaf": leaf})
    summary_path = root / "experiments" / "results" / f"{result['experiment_id']}.json"
    _atomic_json(summary_path, summary)
    if (root / "institutional_learning/strategy_moves/latest.json").is_file():
        compile_workspace_strategy_state_transition_join(root)
    read_model = build_read_model(root)
    _atomic_json(root / "state" / "read_model.json", read_model)
    return {
        "schema": "jaggedthoughts-company-state-flow-workspace-run-v1", "ok": True,
        "result": summary, "artifact_path": artifact.relative_to(root).as_posix(),
        "summary_path": summary_path.relative_to(root).as_posix(), "golden_leaf": leaf,
    }


def run_workspace_company_state_path_action(
    profile: str | Path,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Open and record one prospective company-state path challenger."""
    root, config = load_workspace_config(workspace)
    profile_path = Path(profile).expanduser()
    if not profile_path.is_absolute():
        profile_path = root / profile_path
    result = compile_company_state_path_action(profile_path.resolve(), workspace=root)
    artifact = root / "experiments" / "runs" / (
        f"{result['experiment_id']}-{result['run_sha256'][:12]}.json"
    )
    _atomic_json(artifact, result)
    store = GoldenStore(_store_path(root, config))
    leaf = record_market_flow_experiment(
        store, owner=str(config.get("owner") or "operator-paper-book"), result=result,
    )
    summary = {key: value for key, value in result.items() if key != "models"}
    summary.update({"artifact_path": artifact.relative_to(root).as_posix(), "golden_leaf": leaf})
    summary_path = root / "experiments" / "results" / f"{result['experiment_id']}.json"
    _atomic_json(summary_path, summary)
    read_model = build_read_model(root)
    _atomic_json(root / "state" / "read_model.json", read_model)
    return {
        "schema": "jaggedthoughts-company-state-path-action-workspace-run-v1",
        "ok": True,
        "result": summary,
        "artifact_path": artifact.relative_to(root).as_posix(),
        "summary_path": summary_path.relative_to(root).as_posix(),
        "golden_leaf": leaf,
        "read_model": read_model,
    }


def freeze_workspace_company_state_newton_successor(
    source_run: str | Path,
    candidate: str | Path,
    activation_status: str | Path,
    research_result: str | Path,
    workspace: str | Path | None = None,
    *,
    opened_at: str | None = None,
) -> dict[str, Any]:
    """Persist one attributed Newton candidate as a prospective path-action successor."""
    root, config = load_workspace_config(workspace)
    source_path = Path(source_run).expanduser()
    if not source_path.is_absolute():
        source_path = root / source_path
    candidate_path = Path(candidate).expanduser().resolve()
    activation_path = Path(activation_status).expanduser()
    if not activation_path.is_absolute():
        activation_path = root / activation_path
    result_path = Path(research_result).expanduser()
    if not result_path.is_absolute():
        result_path = root / result_path
    result = freeze_company_state_newton_successor(
        root, source_path.resolve(), candidate_path, activation_path.resolve(),
        result_path.resolve(), opened_at=opened_at,
    )
    artifact = root / "experiments" / "runs" / (
        f"{result['experiment_id']}-{result['run_sha256'][:12]}.json"
    )
    _atomic_json(artifact, result)
    store = GoldenStore(_store_path(root, config))
    leaf = record_market_flow_experiment(
        store, owner=str(config.get("owner") or "operator-paper-book"), result=result,
    )
    freeze = dict(result["candidate_freeze"])
    provenance = dict(freeze["candidate_provenance"])
    summary = {
        "schema": result["schema"],
        "experiment_id": result["experiment_id"],
        "run_id": result["run_id"],
        "run_sha256": result["run_sha256"],
        "as_of": result["as_of"],
        "opened_at": result["opened_at"],
        "status": result["status"],
        "authority": result["authority"],
        "generation_mode": result["generation_mode"],
        "subscription_newton_searched": True,
        "source_path_action_run_sha256": result["source_path_action_run_sha256"],
        "candidate": {
            "candidate_sha256": freeze["candidate_sha256"],
            "freeze_sha256": freeze["freeze_sha256"],
            "iteration_index": provenance["iteration_index"],
            "subscription_run_id": provenance["run_id"],
            "mutator_model": provenance.get("mutator_model"),
            "fitted_parameters": freeze["fitted_parameters"],
            "lagrangian": freeze["lagrangian"],
            "fit_evidence": freeze["fit_evidence"],
            "research_project_lineage": freeze["research_project_lineage"],
            "action_prediction_binding_max_abs": freeze["action_prediction_binding_max_abs"],
        },
        "point_in_time_evidence": {
            key: result["evidence_manifest_ref"].get(key)
            for key in (
                "status", "manifest_leaf_sha256", "source_run_sha256",
                "manifest_ingested_at", "archive_authority", "ref_sha256",
            )
        },
        "source_snapshot": {
            "epoch": result["source_snapshot"]["epoch"],
            "entity_count": len(result["source_snapshot"]["assignments"]),
            "source_assignments_sha256": result["source_assignments_sha256"],
            "source_ref_count": len(result["source_refs"]),
            "source_refs_sha256": stable_sha256(result["source_refs"]),
        },
        "state_ids": result["state_ids"],
        "required_control_ids": result["required_control_ids"],
        "structural_checks": result["structural_checks"],
        "outcome_contracts": [{
            key: contract[key] for key in (
                "leg", "status", "evidence_id", "base_evidence_id",
                "opened_at", "settlement_not_before", "contract_sha256",
            )
        } for contract in result["outcome_contracts"]],
        "next_due_at": result["outcome_contracts"][0]["settlement_not_before"],
        "evaluation_status": result["evaluation_status"],
        "signal_authority": False,
        "model_fit_authority": False,
        "capital_authority": False,
        "artifact_path": artifact.relative_to(root).as_posix(),
        "golden_leaf": leaf,
    }
    summary_path = root / "experiments" / "results" / f"{result['experiment_id']}.json"
    _atomic_json(summary_path, summary)
    read_model = build_read_model(root)
    _atomic_json(root / "state" / "read_model.json", read_model)
    return {
        "schema": "jaggedthoughts-company-state-newton-successor-workspace-run-v1",
        "ok": True,
        "result": summary,
        "artifact_path": artifact.relative_to(root).as_posix(),
        "summary_path": summary_path.relative_to(root).as_posix(),
        "golden_leaf": leaf,
        "read_model_sha256": read_model["read_model_sha256"],
        "signal_authority": False,
        "model_fit_authority": False,
        "capital_authority": False,
    }


def settle_workspace_company_state_path_action(
    workspace: str | Path | None = None, *, as_of: str | None = None,
) -> dict[str, Any]:
    """Advance the immutable path-action run through its two settlement horizons."""
    root, _config = load_workspace_config(workspace)
    summary = _read_json(
        root / "experiments" / "results" / "company-state-two-quarter-path-action.json"
    )
    if not summary:
        return {
            "schema": "jaggedthoughts-company-state-path-action-workspace-status-v1",
            "ok": True,
            "status": "not_opened",
            "signal_authority": False,
            "capital_authority": False,
        }
    run_path = root / require_text(summary.get("artifact_path"), "path-action artifact_path")
    run = _read_json(run_path)
    if not run:
        raise FileNotFoundError(f"path-action run artifact is absent: {run_path}")
    frontier = _read_json(
        root / "experiments" / "results" / "company-state-partition-frontier.json"
    )
    if not frontier:
        raise FileNotFoundError("path-action settlement requires the frozen partition frontier")
    settlement_root = root / "experiments" / "settlements" / str(run["run_sha256"])
    latest_path = settlement_root / "latest.json"
    result = compile_company_state_path_action_status(
        run, frontier, workspace=root, as_of=as_of, prior_status=_read_json(latest_path),
    )
    artifact = settlement_root / f"{result['status_sha256']}.json"
    _atomic_json(artifact, result)
    _atomic_json(latest_path, result)
    return {
        "schema": "jaggedthoughts-company-state-path-action-workspace-status-v1",
        "ok": True,
        "status": result["status"],
        "result": result,
        "artifact_path": artifact.relative_to(root).as_posix(),
        "latest_path": latest_path.relative_to(root).as_posix(),
        "signal_authority": False,
        "capital_authority": False,
    }


def activate_workspace_profile(
    profile_id: str, confirmation: str, workspace: str | Path | None = None
) -> dict[str, Any]:
    """Activate a reviewed draft, then recompile its paper artifact and read model."""
    root, config = load_workspace_config(workspace)
    activation = activate_public_equity_profile(
        root, profile_id=profile_id, confirmation=confirmation,
    )
    store = GoldenStore(_store_path(root, config))
    funnel_leaf = record_funnel_transition(
        store, owner=str(config.get("owner") or "operator-paper-book"),
        receipt=activation["funnel_transition"],
    )
    build = build_workspace(root)
    return {
        **activation, "funnel_transition_leaf": funnel_leaf,
        "build_ok": bool(build.get("ok")), "read_model": build["read_model"],
    }


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _cached_household_mandate_frontier(
    root: Path, *, base_inputs: Mapping[str, Any],
    goal_surface: Mapping[str, Any], public_basis_acquisition: Mapping[str, Any],
) -> dict[str, Any]:
    """Reuse a pure enumeration until one of its typed inputs changes."""
    cache_input = {
        "compiler_version": 1,
        "base_inputs": base_inputs,
        "goal_surface": goal_surface,
        "public_basis_acquisition": public_basis_acquisition,
    }
    input_sha256 = stable_sha256(cache_input)
    cache_path = root / "household" / "mandate_frontier" / "latest.json"
    cached = _read_json(cache_path)
    if (
        cached
        and cached.get("schema") == HOUSEHOLD_MANDATE_FRONTIER_CACHE_SCHEMA
        and cached.get("input_sha256") == input_sha256
        and isinstance(cached.get("frontier"), Mapping)
    ):
        return dict(cached["frontier"])
    frontier = compile_household_mandate_frontier(
        base_inputs=base_inputs,
        goal_surface=goal_surface,
        public_basis_acquisition=public_basis_acquisition,
    )
    _atomic_json(cache_path, {
        "schema": HOUSEHOLD_MANDATE_FRONTIER_CACHE_SCHEMA,
        "input_sha256": input_sha256,
        "frontier": frontier,
    })
    return frontier


def _store_logical_state(path: Path) -> dict[str, Any]:
    """Fingerprint immutable rows and the mutable, rebuildable head projection."""
    with sqlite3.connect(path, timeout=30) as connection:
        leaf_count, leaf_max_rowid = connection.execute(
            "SELECT COUNT(*), COALESCE(MAX(rowid), 0) FROM golden_leaf"
        ).fetchone()
        edge_count, edge_max_rowid = connection.execute(
            "SELECT COUNT(*), COALESCE(MAX(rowid), 0) FROM golden_edge"
        ).fetchone()
        dangling_head_count = connection.execute(
            """SELECT COUNT(*) FROM golden_head h
               LEFT JOIN golden_leaf l ON l.leaf_sha256=h.leaf_sha256
               WHERE l.leaf_sha256 IS NULL"""
        ).fetchone()[0]
        dangling_edge_count = connection.execute(
            """SELECT COUNT(*) FROM golden_edge e
               LEFT JOIN golden_leaf s ON s.leaf_sha256=e.src_leaf_sha256
               LEFT JOIN golden_leaf d ON d.leaf_sha256=e.dst_leaf_sha256
               WHERE s.leaf_sha256 IS NULL OR d.leaf_sha256 IS NULL"""
        ).fetchone()[0]
        immutability_trigger_count = connection.execute(
            """SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' AND name IN
               ('golden_leaf_no_update','golden_leaf_no_delete',
                'golden_edge_no_update','golden_edge_no_delete',
                'golden_head_no_delete','golden_head_identity_no_update')"""
        ).fetchone()[0]
        trigger_rows = connection.execute(
            """SELECT name, sql FROM sqlite_master WHERE type='trigger' AND name IN
               ('golden_leaf_no_update','golden_leaf_no_delete',
                'golden_edge_no_update','golden_edge_no_delete',
                'golden_head_no_delete','golden_head_identity_no_update') ORDER BY name"""
        ).fetchall()
        schema_version = connection.execute("PRAGMA schema_version").fetchone()[0]
        stale_head_count = connection.execute(
            """SELECT COUNT(*) FROM golden_head h
               LEFT JOIN golden_leaf l ON l.leaf_sha256=h.leaf_sha256
               WHERE l.leaf_sha256 IS NULL
                  OR l.owner<>h.owner OR l.object_kind<>h.object_kind
                  OR l.object_id<>h.object_id OR l.available_at<>h.available_at
                  OR EXISTS (
                       SELECT 1 FROM golden_leaf newer
                       WHERE newer.owner=h.owner AND newer.object_kind=h.object_kind
                         AND newer.object_id=h.object_id
                         AND newer.available_at>h.available_at
                  )
                  OR EXISTS (
                       SELECT 1 FROM golden_leaf tied
                       WHERE tied.owner=h.owner AND tied.object_kind=h.object_kind
                         AND tied.object_id=h.object_id
                         AND tied.available_at=h.available_at
                         AND tied.rowid>l.rowid
                  )"""
        ).fetchone()[0]
        head_rows = connection.execute(
            """SELECT owner, object_kind, object_id, leaf_sha256, available_at
               FROM golden_head ORDER BY owner, object_kind, object_id"""
        ).fetchall()
    return {
        "store_path": str(path.resolve()),
        "leaf_count": int(leaf_count),
        "leaf_max_rowid": int(leaf_max_rowid),
        "edge_count": int(edge_count),
        "edge_max_rowid": int(edge_max_rowid),
        "dangling_head_count": int(dangling_head_count),
        "dangling_edge_count": int(dangling_edge_count),
        "immutability_trigger_count": int(immutability_trigger_count),
        "trigger_schema_sha256": stable_sha256([
            {"name": str(name), "sql": str(sql)} for name, sql in trigger_rows
        ]),
        "schema_version": int(schema_version),
        "stale_head_count": int(stale_head_count),
        "head_projection_sha256": stable_sha256([
            {
                "owner": str(owner), "object_kind": str(object_kind),
                "object_id": str(object_id), "leaf_sha256": str(leaf_sha256),
                "available_at": str(available_at),
            }
            for owner, object_kind, object_id, leaf_sha256, available_at in head_rows
        ]),
    }


def _store_state_fingerprint(path: Path) -> str:
    return stable_sha256(_store_logical_state(path))


def _golden_content_prefix_verified(receipt: Mapping[str, Any]) -> bool:
    """Accept a full content receipt whose only failures are mutable head drift."""
    if bool(receipt.get("ok")):
        return True
    errors = receipt.get("errors")
    if receipt.get("verification_mode") != "full_content" or not isinstance(errors, list):
        return False
    head_only_suffixes = (
        "head projections violate identity or recency",
        "golden heads are not latest",
    )
    return bool(errors) and all(
        isinstance(error, str) and error.endswith(head_only_suffixes)
        for error in errors
    )


def _incremental_golden_verification(
    path: Path, prior: Mapping[str, Any], state: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Verify only rows appended after a protected, previously verified prefix."""
    if (
        not _golden_content_prefix_verified(prior)
        or prior.get("schema") != "jaggedthoughts-golden-store-verification-v1"
        or state["dangling_head_count"] or state["dangling_edge_count"]
        or state["stale_head_count"]
        or state["immutability_trigger_count"] != 6
        or prior.get("path") != state["store_path"]
        or prior.get("trigger_schema_sha256") != state["trigger_schema_sha256"]
        or prior.get("schema_version") != state["schema_version"]
    ):
        return None
    prior_leaf_count = int(prior.get("leaf_count", -1))
    prior_edge_count = int(prior.get("edge_count", -1))
    if (
        prior_leaf_count < 0 or prior_edge_count < 0
        or prior_leaf_count > state["leaf_count"]
        or prior_edge_count > state["edge_count"]
    ):
        return None
    leaf_max = int(
        prior.get("verified_leaf_max_rowid") or prior_leaf_count
    )
    edge_max = int(
        prior.get("verified_edge_max_rowid") or prior_edge_count
    )
    with sqlite3.connect(path, timeout=30) as connection:
        if connection.execute(
            "SELECT COUNT(*) FROM golden_leaf WHERE rowid<=?", (leaf_max,)
        ).fetchone()[0] != prior_leaf_count:
            return None
        if connection.execute(
            "SELECT COUNT(*) FROM golden_edge WHERE rowid<=?", (edge_max,)
        ).fetchone()[0] != prior_edge_count:
            return None
        leaf_rows = connection.execute(
            """SELECT rowid, leaf_sha256, owner, object_kind, object_id, epoch,
                      occurred_at, available_at, payload_schema, payload_sha256, body_json
               FROM golden_leaf WHERE rowid>? ORDER BY rowid""",
            (leaf_max,),
        ).fetchall()
        edge_rows = connection.execute(
            """SELECT rowid, edge_sha256, src_leaf_sha256, dst_leaf_sha256, relation, body_json
               FROM golden_edge WHERE rowid>? ORDER BY rowid""",
            (edge_max,),
        ).fetchall()
    if (
        prior_leaf_count + len(leaf_rows) != state["leaf_count"]
        or prior_edge_count + len(edge_rows) != state["edge_count"]
    ):
        return None
    errors: list[str] = []
    for row in leaf_rows:
        (
            _rowid, leaf_sha256, owner, object_kind, object_id, epoch,
            occurred_at, available_at, payload_schema, payload_sha256, body_json,
        ) = row
        body = decode_golden_body(body_json)
        declared = body.pop("leaf_sha256", "")
        if stable_sha256(body) != declared or declared != leaf_sha256:
            errors.append(f"leaf hash mismatch: {leaf_sha256}")
        if stable_sha256(body.get("payload")) != payload_sha256:
            errors.append(f"payload hash mismatch: {leaf_sha256}")
        projections = {
            "owner": owner, "object_kind": object_kind, "object_id": object_id,
            "epoch": epoch, "occurred_at": occurred_at, "available_at": available_at,
            "payload_schema": payload_schema, "payload_sha256": payload_sha256,
        }
        for field, value in projections.items():
            if body.get(field) != value:
                errors.append(f"leaf {field} projection mismatch: {leaf_sha256}")
    for _rowid, edge_sha256, src_leaf_sha256, dst_leaf_sha256, relation, body_json in edge_rows:
        body = decode_golden_body(body_json)
        declared = body.pop("edge_sha256", "")
        if stable_sha256(body) != declared or declared != edge_sha256:
            errors.append(f"edge hash mismatch: {edge_sha256}")
        for field, value in {
            "src_leaf_sha256": src_leaf_sha256,
            "dst_leaf_sha256": dst_leaf_sha256,
            "relation": relation,
        }.items():
            if body.get(field) != value:
                errors.append(f"edge {field} projection mismatch: {edge_sha256}")
    return {
        "schema": "jaggedthoughts-golden-store-verification-v1",
        "path": str(path),
        "leaf_count": state["leaf_count"],
        "edge_count": state["edge_count"],
        "ok": not errors,
        "errors": errors,
        "verified_leaf_max_rowid": state["leaf_max_rowid"],
        "verified_edge_max_rowid": state["edge_max_rowid"],
        "verification_mode": "append_only_incremental",
        "trigger_schema_sha256": state["trigger_schema_sha256"],
        "schema_version": state["schema_version"],
        "stale_head_count": state["stale_head_count"],
        "head_projection_sha256": state["head_projection_sha256"],
    }


def _verified_golden_store(root: Path, path: Path) -> dict[str, Any]:
    """Serialize verification and publish one receipt for all workspace services."""
    state_dir = root / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    with (state_dir / ".golden_verification.lock").open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        receipt = _verified_golden_store_locked(root, path)
        _atomic_json(state_dir / "golden_verification.json", receipt)
        return receipt


def _verified_golden_store_locked(root: Path, path: Path) -> dict[str, Any]:
    """Reuse a content check while the protected append-only state is unchanged."""
    state = _store_logical_state(path)
    if state["stale_head_count"]:
        GoldenStore(path).refresh_heads()
        state = _store_logical_state(path)
    fingerprint = stable_sha256(state)
    cached = _GOLDEN_VERIFICATION_CACHE.get(fingerprint)
    if cached is not None:
        return dict(cached)
    receipts = [
        _read_json(root / "state" / "golden_verification.json"),
        (_read_json(root / "state" / "read_model.json") or {}).get("golden_store"),
        (_read_json(root / "state" / "latest_build.json") or {}).get(
            "golden_store_verification"
        ),
    ]
    compatible_receipts = []
    for row in receipts:
        if not isinstance(row, Mapping):
            continue
        try:
            cursor = (
                int(row.get("verified_leaf_max_rowid") or row.get("leaf_count") or -1),
                int(row.get("verified_edge_max_rowid") or row.get("edge_count") or -1),
            )
        except (TypeError, ValueError):
            continue
        if (
            _golden_content_prefix_verified(row)
            and row.get("schema") == "jaggedthoughts-golden-store-verification-v1"
            and row.get("path") == state["store_path"]
            and row.get("trigger_schema_sha256") == state["trigger_schema_sha256"]
            and row.get("schema_version") == state["schema_version"]
        ):
            compatible_receipts.append((cursor, row))
    prior_receipt = max(
        compatible_receipts,
        key=lambda item: item[0],
        default=None,
    )
    prior_receipt = prior_receipt[1] if prior_receipt else None
    prior_matches_immutable_rows = (
        isinstance(prior_receipt, Mapping)
        and bool(prior_receipt.get("ok"))
        and prior_receipt.get("schema")
        == "jaggedthoughts-golden-store-verification-v1"
        and prior_receipt.get("path") == state["store_path"]
        and prior_receipt.get("trigger_schema_sha256")
        == state["trigger_schema_sha256"]
        and prior_receipt.get("schema_version") == state["schema_version"]
        and int(prior_receipt.get("leaf_count", -1)) == state["leaf_count"]
        and int(prior_receipt.get("edge_count", -1)) == state["edge_count"]
        and state["dangling_head_count"] == 0
        and state["dangling_edge_count"] == 0
        and state["stale_head_count"] == 0
        and state["immutability_trigger_count"] == 6
        and prior_receipt.get("head_projection_sha256")
        == state["head_projection_sha256"]
    )
    if prior_matches_immutable_rows:
        receipt = {
            **dict(prior_receipt), "store_fingerprint": fingerprint,
            "verified_leaf_max_rowid": state["leaf_max_rowid"],
            "verified_edge_max_rowid": state["edge_max_rowid"],
            "trigger_schema_sha256": state["trigger_schema_sha256"],
            "schema_version": state["schema_version"],
            "stale_head_count": state["stale_head_count"],
            "head_projection_sha256": state["head_projection_sha256"],
        }
        _GOLDEN_VERIFICATION_CACHE[fingerprint] = receipt
        return receipt
    if isinstance(prior_receipt, Mapping):
        incremental = _incremental_golden_verification(
            path, prior_receipt, state,
        )
        if incremental is not None:
            receipt = {**incremental, "store_fingerprint": fingerprint}
            _GOLDEN_VERIFICATION_CACHE[fingerprint] = receipt
            return receipt
    verification: dict[str, Any] = {}
    for _attempt in range(3):
        before_state = _store_logical_state(path)
        before = stable_sha256(before_state)
        verification = GoldenStore(path).verify()
        after_state = _store_logical_state(path)
        after = stable_sha256(after_state)
        if before == after:
            state_errors = list(verification.get("errors") or ())
            if after_state["immutability_trigger_count"] != 6:
                state_errors.append("golden store protection trigger set is incomplete")
            if after_state["dangling_edge_count"]:
                state_errors.append(
                    f"{after_state['dangling_edge_count']} golden edges reference missing leaves"
                )
            if after_state["stale_head_count"]:
                state_errors.append(
                    f"{after_state['stale_head_count']} golden heads are not latest"
                )
            receipt = {
                **verification, "ok": bool(verification.get("ok")) and not state_errors,
                "errors": state_errors, "store_fingerprint": after,
                "verified_leaf_max_rowid": after_state["leaf_max_rowid"],
                "verified_edge_max_rowid": after_state["edge_max_rowid"],
                "verification_mode": "full_content",
                "trigger_schema_sha256": after_state["trigger_schema_sha256"],
                "schema_version": after_state["schema_version"],
                "stale_head_count": after_state["stale_head_count"],
                "head_projection_sha256": after_state["head_projection_sha256"],
            }
            _GOLDEN_VERIFICATION_CACHE[after] = receipt
            return receipt
    return {**verification, "store_fingerprint": None}


def _decision_rows(root: Path, config: Mapping[str, Any]) -> list[dict[str, Any]]:
    reference_ids = set(str(value) for value in config.get("reference_profile_ids", []))
    latest_build = _read_json(root / "state" / "latest_build.json") or {}
    active_decision_ids = {
        str(row.get("decision_id"))
        for row in latest_build.get("profile_statuses", [])
        if isinstance(row, Mapping)
        and row.get("status") in {"compiled", "frozen_existing"}
        and row.get("decision_id")
    }
    rows: list[dict[str, Any]] = []
    for path in sorted((root / "decisions").glob("*.json")):
        decision = _read_json(path)
        if not decision or decision.get("schema") != "jaggedthoughts-investment-decision-v1":
            continue
        if active_decision_ids and str(decision.get("decision_id")) not in active_decision_ids:
            continue
        summary = decision.get("summary") or {}
        proposal = decision.get("position_proposal") or {}
        play = decision.get("play") or {}
        fingerprint = decision.get("fingerprint") or {}
        market_state = decision.get("market_state") or {}
        valuation_summary = (decision.get("valuation_envelope") or {}).get("summary") or {}
        hurdle_prices = decision.get("hurdle_price_frontier") or {}
        thesis = decision.get("thesis") or {}
        underwriting = decision.get("underwriting_case") or {}
        if not hurdle_prices:
            try:
                hurdle_prices = compile_hurdle_price_frontier(
                    decision["valuation_envelope"],
                    excess_return_hurdle=float(underwriting["hurdle_rate"]),
                )
            except (KeyError, TypeError, ValueError):
                hurdle_prices = {}
        policy_regions = decision.get("policy_objective_weight_regions") or {}
        if not policy_regions:
            try:
                objectives = tuple(decision["policy_objectives"])
                evaluations = {
                    str(row["program_id"]): row
                    for row in decision["policy_synthesis"]["evaluations"]
                }
                frontier_ids = tuple(
                    decision["policy_synthesis"]["certificate"]["frontier_program_ids"]
                )
                policy_regions = compile_linear_preference_regions(
                    objective_names=tuple(str(row["objective_id"]) for row in objectives),
                    alternatives={
                        str(program_id): {
                            str(objective["objective_id"]): (
                                float(value) / float(objective["scale"])
                            )
                            for objective, value in zip(
                                objectives,
                                evaluations[str(program_id)]["objective_values"],
                                strict=True,
                            )
                        }
                        for program_id in frontier_ids
                    },
                )
            except (KeyError, TypeError, ValueError, RuntimeError):
                policy_regions = {}
        selected_program_id = str((decision.get("policy_selection") or {}).get("program_id") or "")
        selected_region = next(
            (
                row for row in policy_regions.get("regions") or ()
                if str(row.get("alternative_id")) == selected_program_id
            ),
            {},
        )
        as_of = str(decision.get("as_of") or "")
        try:
            due = timestamp_key(as_of) + timedelta(days=int(play.get("horizon_days") or 0))
            due_at = due.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        except (TypeError, ValueError):
            due_at = ""
        rows.append({
            "decision_id": decision.get("decision_id"), "profile_id": decision.get("profile_id"),
            "entity": decision.get("entity"), "play": play, "as_of": as_of,
            "due_at": due_at, "authority": decision.get("authority"),
            "selected_action_id": summary.get("selected_action_id"),
            "current_weight": summary.get("current_weight"), "target_weight": summary.get("target_weight"),
            "frontier_count": summary.get("frontier_count"),
            "objective_weight_region_count": (
                summary.get("objective_weight_region_count")
                if summary.get("objective_weight_region_count") is not None
                else len(policy_regions.get("supported_alternative_ids") or ())
            ),
            "selected_policy_has_objective_weight_region": (
                summary.get("selected_policy_has_objective_weight_region")
                if summary.get("selected_policy_has_objective_weight_region") is not None
                else bool(selected_region.get("supported"))
            ),
            "selected_policy_priority_witness": (
                selected_region.get("strict_preference_witness")
                or selected_region.get("preference_witness")
            ),
            "representation_status": summary.get("representation_status"),
            "economic_status": summary.get("economic_status"),
            "estimated_cost": summary.get("estimated_cost"),
            "fingerprint_score": fingerprint.get("aggregate_score"),
            "market_premium": market_state.get("weighted_premium"),
            "market_downside": market_state.get("weighted_downside"),
            "earnings_power_margin_of_safety": valuation_summary.get("earnings_power_margin_of_safety"),
            "implied_growth_median": valuation_summary.get("implied_growth_median"),
            "implied_required_return_median": valuation_summary.get("implied_required_return_median"),
            "price_implied_excess_return": valuation_summary.get("price_implied_excess_return"),
            "robust_maximum_price": hurdle_prices.get("robust_maximum_price"),
            "median_maximum_price": hurdle_prices.get("median_maximum_price"),
            "optimistic_maximum_price": hurdle_prices.get("optimistic_maximum_price"),
            "hurdle_price_frontier_sha256": hurdle_prices.get("hurdle_price_frontier_sha256"),
            "thesis_claim": thesis.get("claim"),
            "falsifiers": list(thesis.get("falsifiers") or []),
            "hurdle_rate": underwriting.get("hurdle_rate"),
            "decisive_observation": underwriting.get("decisive_observation"),
            "decision_record_sha256": decision.get("decision_record_sha256"),
            "proposal_sha256": proposal.get("proposal_sha256"),
            "data_class": (
                "reference_fixture" if str(decision.get("profile_id")) in reference_ids
                else str((decision.get("profile_lifecycle") or {}).get("data_class") or "operator")
            ),
            "profile_stage": (
                "reference" if str(decision.get("profile_id")) in reference_ids
                else str((decision.get("profile_lifecycle") or {}).get("stage") or "active")
            ),
            "decision_path": path.relative_to(root).as_posix(),
            "report_path": f"reports/{decision.get('decision_id')}.md",
        })
    return rows


def _paper_watch_rows(
    root: Path, *, include_inadmissible: bool = False,
) -> list[dict[str, Any]]:
    """Read typed fund/equity paper-watch decisions without treating them as positions."""
    expected = {
        "equities": "jaggedthoughts-public-equity-paper-decision-v1",
        "funds": "jaggedthoughts-public-fund-paper-decision-v1",
    }
    store: GoldenStore | None = None
    store_owner = ""
    config_path = root / "workspace.yaml"
    if config_path.is_file():
        config = _load_yaml(config_path)
        store_owner = str(config.get("owner") or "")
        store_path = _store_path(root, config)
        if store_path.is_file():
            store = GoldenStore(store_path)
    rows: list[dict[str, Any]] = []
    for directory, schema in expected.items():
        for path in sorted((root / "paper_decisions" / directory).glob("*.json")):
            payload = _read_json(path)
            if not payload or payload.get("schema") != schema:
                continue
            body = dict(payload)
            declared = str(body.pop("decision_sha256", ""))
            body.pop("transition", None)
            if len(declared) != 64 or stable_sha256(body) != declared:
                raise ValueError(f"paper-watch decision identity is invalid: {path}")
            evidence = payload.get("evidence") or {}
            dossier_leaf = str(evidence.get("dossier_leaf") or "")
            admissibility = (
                research_evidence_admissibility(
                    store, owner=store_owner, target_leaf=dossier_leaf,
                )
                if store is not None and dossier_leaf else None
            )
            if (
                admissibility is not None
                and not admissibility["admissible"]
                and not include_inadmissible
            ):
                continue
            rows.append({
                **payload,
                "artifact_path": path.relative_to(root).as_posix(),
                "paper_watch_only": True,
                "research_evidence_admissibility": admissibility,
            })
    # A proposal is a dated compilation; the watch it activates is the
    # entity at one candidate/research-evidence epoch. Recompiling derived
    # fingerprints must not create another active watch over the same epoch.
    unique: dict[tuple[str, ...], dict[str, Any]] = {}
    for row in rows:
        identity = _paper_watch_enrollment_identity(row)
        current = unique.get(identity)
        if current is None or (
            str(row.get("activated_at") or ""), str(row.get("decision_sha256") or "")
        ) < (
            str(current.get("activated_at") or ""), str(current.get("decision_sha256") or "")
        ):
            unique[identity] = row
    return [unique[key] for key in sorted(unique)]


def _paper_watch_enrollment_identity(payload: Mapping[str, Any]) -> tuple[str, ...]:
    """Name one watch independently of proposal compilation churn."""
    entity = payload.get("entity") if isinstance(payload.get("entity"), Mapping) else {}
    evidence = payload.get("evidence") if isinstance(payload.get("evidence"), Mapping) else {}
    stable = tuple(str(evidence.get(key) or "") for key in ("candidate_leaf", "dossier_leaf"))
    if all(stable):
        return (
            str(entity.get("entity_kind") or ""),
            str(entity.get("entity_id") or "").upper(),
            *stable,
        )
    return ("legacy_proposal", str(payload.get("proposal_sha256") or ""))


def _settled_decision_ids(store: GoldenStore) -> set[str]:
    settled: set[str] = set()
    for row in store.list_leaves(object_kind="economic_scorecard", limit=10_000):
        leaf = store.get_leaf(str(row["leaf_sha256"]))
        decision_id = str((leaf.get("payload") or {}).get("decision_id") or "")
        if decision_id:
            settled.add(decision_id)
    return settled


def _settlement_scorecards(store: GoldenStore) -> dict[str, dict[str, Any]]:
    scorecards: dict[str, dict[str, Any]] = {}
    for row in store.list_leaves(object_kind="economic_scorecard", limit=10_000):
        leaf = store.get_leaf(str(row["leaf_sha256"]))
        payload = leaf.get("payload")
        if not isinstance(payload, Mapping):
            continue
        decision_id = str(payload.get("decision_id") or "")
        if decision_id:
            scorecards[decision_id] = {
                **dict(payload),
                "observed_at": leaf.get("occurred_at"),
                "available_at": leaf.get("available_at"),
            }
    return scorecards


def _closed_book_research_scorecards(
    root: Path,
) -> dict[tuple[str, str], dict[str, Any]]:
    """Project the first sealed 90-day outcome per candidate and dossier."""
    runs = {}
    for path in (root / "closed_book" / "runs").glob("*.json"):
        run = _read_json(path)
        if not run or run.get("schema") != CLOSED_BOOK_RUN_SCHEMA:
            continue
        body = {key: value for key, value in run.items() if key != "run_sha256"}
        subject = (run.get("evidence_packet") or {}).get("subject") or {}
        if (
            stable_sha256(body) != run.get("run_sha256")
            or subject.get("kind") != "paper_watch_decision"
            or int(run.get("horizon_days") or 0) != 90
            or not subject.get("candidate_leaf")
        ):
            continue
        runs[str(run["run_id"])] = run

    scorecards: dict[str, dict[str, Any]] = {}
    for path in (root / "closed_book" / "settlements").glob("*.json"):
        settlement = _read_json(path)
        if not settlement or settlement.get("schema") != CLOSED_BOOK_SETTLEMENT_SCHEMA:
            continue
        body = {key: value for key, value in settlement.items() if key != "settlement_sha256"}
        run = runs.get(str(settlement.get("run_id") or ""))
        actual = settlement.get("actual_values") or {}
        if (
            run is None
            or stable_sha256(body) != settlement.get("settlement_sha256")
            or settlement.get("run_sha256") != run.get("run_sha256")
            or actual.get("active_return") is None
        ):
            continue
        packet = dict(run.get("evidence_packet") or {})
        candidate_leaf = str((packet.get("subject") or {})["candidate_leaf"])
        dossier_sha = str(
            (((packet.get("research_snapshot") or {}).get("evidence") or {}).get(
                "dossier_sha256"
            ) or "")
        )
        if len(dossier_sha) != 64:
            continue
        row = {
            "decision_id": ((run.get("evidence_packet") or {}).get("subject") or {}).get(
                "subject_id"
            ),
            "net_excess_return": require_finite(
                actual["active_return"], "closed-book paper-watch active_return",
            ),
            "settlement_id": settlement.get("settlement_id"),
            "settlement_sha256": settlement.get("settlement_sha256"),
            "economic_horizon_days": 90,
            "economic_outcome_source": "sealed_paper_watch_forecast_settlement",
            "opened_at": run.get("opened_at"),
            "evaluated_at": settlement.get("evaluated_at"),
        }
        key = (candidate_leaf, dossier_sha)
        prior = scorecards.get(key)
        if prior is None or (str(row["opened_at"]), str(row["settlement_id"])) < (
            str(prior["opened_at"]), str(prior["settlement_id"]),
        ):
            scorecards[key] = row
    return scorecards


def _advance_research_question_policy_outcomes(
    root: Path, *, as_of: str | None = None,
) -> dict[str, Any]:
    """Advance every v2 assignment through cutoff, price binding, and payoff."""
    evaluated_at = canonical_timestamp(
        as_of or _utc_now(), "research-question outcome as_of"
    )
    base = root / "institutional_learning" / "research_question_policy_outcomes"
    action_root = base / "actions"
    binding_root = base / "bindings"
    window_root = base / "return_windows"
    settlement_root = base / "settlements"
    runs = [
        row for path in sorted((root / "closed_book" / "runs").glob("*.json"))
        if (row := _read_json(path))
    ]
    requests = []
    for path in sorted((root / "research_jobs" / "requests").glob("*.json")):
        request = _read_json(path) or {}
        contract = request.get("research_policy_outcome_contract")
        if not isinstance(contract, Mapping):
            continue
        request_body = {
            key: value for key, value in request.items()
            if key not in {"request_sha256", "research_policy_outcome_contract"}
        }
        contract_body = {
            key: value for key, value in contract.items()
            if key != "outcome_contract_sha256"
        }
        if (
            stable_sha256(request_body) != contract.get("request_basis_sha256")
            or stable_sha256(contract_body) != contract.get("outcome_contract_sha256")
        ):
            continue
        requests.append((path, request, dict(contract)))
    entity_ids = {
        str(contract[key]).upper()
        for _, _, contract in requests if contract.get("eligible")
        for key in ("entity_id", "benchmark_id") if contract.get(key)
    }
    prices = (
        _price_rows_by_entity(root, entity_ids, as_of=evaluated_at)
        if entity_ids else {}
    )
    rows = []
    for request_path, request, contract in requests:
        unit_id = str(contract.get("assignment_unit_id") or "")
        row = {
            "assignment_unit_id": unit_id,
            "request_sha256": request.get("request_sha256"),
            "request_path": request_path.relative_to(root).as_posix(),
            "eligible": bool(contract.get("eligible")),
            "action_status": "not_due",
            "binding_status": "not_due",
            "settlement_status": "not_due",
        }
        if not contract.get("eligible"):
            row.update({
                "action_status": "ineligible", "binding_status": "ineligible",
                "settlement_status": "ineligible",
                "reason": contract.get("ineligible_reason"),
            })
            rows.append(row)
            continue
        action_path = action_root / f"{unit_id}.json"
        action = _read_json(action_path)
        if timestamp_key(evaluated_at) >= timestamp_key(contract["decision_cutoff_at"]):
            if not action:
                action = freeze_research_question_policy_action(
                    contract, closed_book_runs=runs,
                    frozen_at=str(contract["decision_cutoff_at"]),
                )
                _atomic_json(action_path, action)
            row["action_status"] = action["status"]
        return_window = contract.get("return_window") or {}
        binding_path = binding_root / f"{unit_id}.json"
        binding = _read_json(binding_path)
        if timestamp_key(evaluated_at) >= timestamp_key(contract["decision_cutoff_at"]):
            if not binding or binding.get("status") != "bound":
                binding = bind_prospective_return_window(
                    return_window, points=prices, as_of=evaluated_at,
                )
                _atomic_json(binding_path, binding)
            row["binding_status"] = binding["status"]
        window = None
        if binding and binding.get("status") == "bound":
            window_path = window_root / f"{unit_id}.json"
            window = _read_json(window_path)
            if not window or window.get("status") != "settled":
                window = settle_prospective_return_window(
                    return_window, binding, points=prices, as_of=evaluated_at,
                )
                _atomic_json(window_path, window)
        settlement_path = settlement_root / f"{unit_id}.json"
        settlement = _read_json(settlement_path)
        if (
            action and timestamp_key(evaluated_at)
            >= timestamp_key(contract["outcome_due_at"])
            and (not settlement or settlement.get("status") == "due_censored")
        ):
            settlement = settle_research_question_policy_outcome(
                contract, action, return_window_settlement=window,
                settled_at=evaluated_at,
            )
            _atomic_json(settlement_path, settlement)
        if settlement:
            row["settlement_status"] = settlement["status"]
            row["incremental_return_vs_no_action"] = settlement.get(
                "incremental_return_vs_no_action"
            )
        elif timestamp_key(evaluated_at) >= timestamp_key(contract["outcome_due_at"]):
            row["settlement_status"] = "due_censored"
        rows.append(row)
    body = {
        "schema": "jaggedthoughts-research-question-policy-outcome-cycle-v1",
        "evaluated_at": evaluated_at,
        "request_count": len(rows),
        "eligible_count": sum(bool(row["eligible"]) for row in rows),
        "action_count": sum(row["action_status"] == "shadow_probe" for row in rows),
        "abstention_count": sum(row["action_status"] == "abstain" for row in rows),
        "settled_count": sum(str(row["settlement_status"]).startswith("settled_") for row in rows),
        "due_censored_count": sum(row["settlement_status"] == "due_censored" for row in rows),
        "rows": rows,
        "capital_authority": False,
    }
    result = {**body, "cycle_sha256": stable_sha256(body)}
    _atomic_json(base / "latest.json", result)
    return result


def _research_question_policy_scorecards(root: Path) -> dict[str, dict[str, Any]]:
    scorecards = {}
    for path in (
        root / "institutional_learning" / "research_question_policy_outcomes"
        / "settlements"
    ).glob("*.json"):
        settlement = _read_json(path) or {}
        if (
            str(settlement.get("status") or "").startswith("settled_")
            and settlement.get("incremental_return_vs_no_action") is not None
        ):
            scorecards[path.stem] = {
                "incremental_return_vs_no_action": settlement[
                    "incremental_return_vs_no_action"
                ],
                "observed_at": settlement.get("settled_at"),
                "economic_outcome_source": (
                    "assignment_bound_fixed_probe_or_abstention"
                ),
                "outcome_settlement_sha256": settlement.get(
                    "outcome_settlement_sha256"
                ),
            }
    return scorecards


def _research_request_rows(
    root: Path,
    decisions: Iterable[Mapping[str, Any]],
    settlement_scorecards: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Project immutable research requests through their downstream lifecycle."""
    candidate_index = latest_discovery_candidate_index(root)
    closed_book_scorecards = _closed_book_research_scorecards(root)
    policy_scorecards = _research_question_policy_scorecards(root)
    dossier_by_request: dict[str, dict[str, Any]] = {}
    for path in sorted((root / "research" / "dossiers").glob("*.json")):
        dossier = _read_json(path)
        if not dossier or dossier.get("schema") != "jaggedthoughts-candidate-research-dossier-v1":
            continue
        claimed_dossier_sha = str(dossier.get("dossier_sha256") or "")
        dossier_body = {
            key: value for key, value in dossier.items() if key != "dossier_sha256"
        }
        request_id = str(dossier.get("request_id") or "")
        if (
            request_id and len(claimed_dossier_sha) == 64
            and stable_sha256(dossier_body) == claimed_dossier_sha
        ):
            sources = [row for row in dossier.get("sources") or () if isinstance(row, Mapping)]
            primary_ids = {
                str(row.get("id") or "") for row in sources
                if row.get("source_kind") in {"filing", "issuer", "regulator", "government"}
            }
            question_outcomes = [
                row for row in dossier.get("research_question_outcomes") or ()
                if isinstance(row, Mapping)
            ]
            resolved = [
                row for row in question_outcomes if row.get("status") != "unresolved"
            ]
            primary_resolved = [
                row for row in resolved
                if any(str(ref) in primary_ids for ref in row.get("evidence_refs") or ())
            ]
            observation = {
                "path": path.relative_to(root).as_posix(),
                "request_sha256": dossier.get("request_sha256"),
                "dossier_sha256": claimed_dossier_sha,
                "generated_at": dossier.get("generated_at"),
                "source_count": len(sources),
                "primary_source_count": sum(
                    row.get("source_kind") in {"filing", "issuer", "regulator", "government"}
                    for row in sources
                ),
                "falsifier_count": len(dossier.get("falsifiers") or ()),
                "catalyst_count": len(dossier.get("catalysts") or ()),
                "question_atom_count": len(question_outcomes),
                "question_resolved_atom_count": len(resolved),
                "question_resolution_rate": (
                    len(resolved) / len(question_outcomes) if question_outcomes else None
                ),
                "question_primary_evidence_rate": (
                    len(primary_resolved) / len(question_outcomes) if question_outcomes else None
                ),
                "question_rival_signal_count": sum(
                    row.get("status") in {"supports_rival", "mixed"}
                    for row in question_outcomes
                ),
            }
            prior = dossier_by_request.get(request_id)
            if prior is None or (
                str(observation.get("generated_at") or ""), claimed_dossier_sha
            ) > (
                str(prior.get("generated_at") or ""),
                str(prior.get("dossier_sha256") or ""),
            ):
                dossier_by_request[request_id] = observation

    profile_by_leaf: dict[str, dict[str, Any]] = {}
    for path in sorted((root / "profiles").glob("**/*.yaml")):
        try:
            profile = _load_yaml(path)
        except (OSError, TypeError, ValueError, yaml.YAMLError):
            continue
        origin = profile.get("discovery_origin")
        if not isinstance(origin, Mapping) or not origin.get("candidate_leaf"):
            continue
        profile_by_leaf[str(origin["candidate_leaf"])] = {
            "profile_id": profile.get("profile_id"),
            "profile_stage": str((profile.get("lifecycle") or {}).get("stage") or "draft"),
            "profile_path": path.relative_to(root).as_posix(),
        }

    decision_by_profile = {
        str(row.get("profile_id")): dict(row)
        for row in decisions if row.get("profile_id")
    }
    result_by_leaf: dict[str, dict[str, Any]] = {}
    for path in sorted((root / "research_jobs" / "enrichment" / "results").glob("*.json")):
        result = _read_json(path)
        if result and result.get("candidate_leaf"):
            result_by_leaf[str(result["candidate_leaf"])] = {
                **result, "result_path": path.relative_to(root).as_posix(),
            }

    rows: list[dict[str, Any]] = []
    for path in sorted((root / "research_jobs" / "requests").glob("*.json"), reverse=True):
        request = _read_json(path)
        if not request or request.get("schema") != "jaggedthoughts-agent-research-request-v1":
            continue
        leaf = str(request.get("candidate_leaf") or "")
        dossier_observations = dossier_by_request.get(
            str(request.get("request_id") or "")
        ) or {}
        if dossier_observations.get("request_sha256") != request.get("request_sha256"):
            dossier_observations = {}
        dossier_path = dossier_observations.get("path")
        profile = profile_by_leaf.get(leaf)
        decision = decision_by_profile.get(str((profile or {}).get("profile_id") or ""))
        assignment = request.get("research_policy_assignment")
        assignment = assignment if isinstance(assignment, Mapping) else {}
        settlement_scorecard = policy_scorecards.get(
            str(assignment.get("assignment_unit_id") or "")
        ) or settlement_scorecards.get(
            str((decision or {}).get("decision_id") or "")
        ) or closed_book_scorecards.get((
            leaf, str(dossier_observations.get("dossier_sha256") or ""),
        ))
        stage = "evidence_ready"
        if dossier_path:
            stage = "researched"
        if profile:
            stage = "paper_active" if profile.get("profile_stage") == "active" else "drafted"
        if decision and decision.get("settlement_status") == "settled":
            stage = "settled"
        elif settlement_scorecard:
            stage = "settled"
        currency = research_request_currency(request, candidate_index)
        if (
            stage == "evidence_ready" and currency["known"]
            and not currency["qualitative_research_current"]
        ):
            stage = "superseded"
        result = result_by_leaf.get(leaf) or {}
        rows.append({
            **request,
            "lifecycle_stage": stage,
            "currency": currency,
            "request_path": path.relative_to(root).as_posix(),
            "research_request_leaf": result.get("research_request_leaf"),
            "result_path": result.get("result_path"),
            "dossier_path": dossier_path,
            "dossier_observations": dossier_observations,
            "profile": profile,
            "decision_id": (
                (decision or {}).get("decision_id")
                or (settlement_scorecard or {}).get("decision_id")
            ),
            "paper_target_weight": (decision or {}).get("target_weight"),
            "settlement_status": (
                (decision or {}).get("settlement_status")
                or ("settled" if settlement_scorecard else None)
            ),
            "settlement_scorecard": settlement_scorecard,
            "learning_status": (
                "settled_outcome_available_for_policy_review"
                if stage == "settled" else
                "superseded_by_later_candidate" if stage == "superseded" else
                "awaiting_downstream_outcome"
            ),
        })
    rows.sort(key=lambda row: (str(row.get("created_at") or ""), str(row.get("request_id") or "")), reverse=True)
    return rows


def _latest_observations(root: Path, source_run: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    epoch_path = root / "data" / "latest_source_epoch.json"
    if epoch_path.is_file():
        try:
            validated = validate_source_epoch(root, epoch_path)
        except (OSError, TypeError, ValueError, RuntimeError, json.JSONDecodeError):
            return []
        epoch_run = validated["source_run"]
        if source_run and epoch_run.get("run_sha256") != source_run.get("run_sha256"):
            return []
        return list(validated["projection"].get("observations") or ())
    projection = _read_json(root / "data" / "latest_observations.json")
    if (
        projection
        and projection.get("schema") == "jaggedthoughts-latest-observation-projection-v1"
        and projection.get("as_of") == (source_run or {}).get("as_of")
        and int(projection.get("observation_count") or -1)
        == int((source_run or {}).get("observation_count") or -2)
    ):
        return list(projection.get("observations") or ())
    path = root / "data" / "observations.csv"
    if not path.is_file():
        return []
    as_of = canonical_timestamp((source_run or {}).get("as_of") or _utc_now(), "observations as_of")
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                if timestamp_key(str(row["available_at"])) > timestamp_key(as_of):
                    continue
                key = (str(row["entity_id"]), str(row["metric_id"]))
                current = latest.get(key)
                if current is None or (str(row["available_at"]), str(row["observed_at"]), str(row["observation_id"])) > (
                    str(current["available_at"]), str(current["observed_at"]), str(current["observation_id"])
                ):
                    latest[key] = dict(row)
            except (KeyError, ValueError):
                continue
    return [latest[key] for key in sorted(latest)]


def _current_source_run(root: Path) -> dict[str, Any] | None:
    """Resolve the run behind the canonical current-source publication pointer."""
    epoch_path = root / "data" / "latest_source_epoch.json"
    if epoch_path.is_file():
        try:
            return validate_source_epoch(root, epoch_path)["source_run"]
        except (OSError, TypeError, ValueError, RuntimeError, json.JSONDecodeError):
            return None
    return _read_json(root / "data" / "latest_source_run.json")


def _current_instrument_portfolio_admissions(root: Path) -> dict[str, Any]:
    """Return the last capital-cycle admission epoch without minting a new one."""
    artifact = _read_json(root / "portfolio" / "instrument_admissions" / "latest.json")
    if not artifact:
        raise FileNotFoundError("current instrument portfolio admissions absent")
    body = dict(artifact)
    claimed = str(body.pop("workspace_admissions_sha256", ""))
    if (
        body.get("schema") != WORKSPACE_INSTRUMENT_PORTFOLIO_ADMISSIONS_SCHEMA
        or len(claimed) != 64
        or stable_sha256(body) != claimed
    ):
        raise ValueError("current instrument portfolio admissions content hash mismatch")
    return {**body, "workspace_admissions_sha256": claimed}


def _sec_frame_potential_projection(root: Path) -> dict[str, Any]:
    """Project a bounded potential-ranked queue without sending the full screen to the UI."""
    screen = _read_json(root / "data" / "sec_frames" / "latest.json") or {}
    acquisition_path = "data/sec_frames/research-acquisition.json"
    acquisition = _read_json(
        root / acquisition_path
    ) or {}
    if screen.get("schema") != SEC_FRAME_SCREEN_SCHEMA:
        return {
            "schema": "jaggedthoughts-broad-equity-potential-ui-v1",
            "enabled": False,
            "status": "awaiting_sec_frame_screen",
            "capital_authority": False,
        }
    scheduled = _read_json(root / "research_jobs" / "scheduled" / "latest.json") or {}
    for intent in scheduled.get("results") or ():
        if not isinstance(intent, Mapping) or intent.get("mode") != "broad_equity":
            continue
        candidate_path = str(intent.get("run_path") or "")
        candidate = _read_json(root / candidate_path) if candidate_path else None
        if candidate and candidate.get("potential_screen_sha256") == screen.get("screen_sha256"):
            acquisition, acquisition_path = candidate, candidate_path
            break
    queue = [
        dict(row) for row in screen.get("research_queue") or ()
        if isinstance(row, Mapping)
    ]
    priority_by_id = {
        str(row.get("security_id") or ""): row for row in queue
        if row.get("security_id")
    }
    selected = []
    for row in acquisition.get("candidates") or ():
        if not isinstance(row, Mapping) or row.get("selection_status") != "selected":
            continue
        potential = priority_by_id.get(str(row.get("security_id") or ""), {})
        selected.append({
            "selection_rank": row.get("selection_rank"),
            "security_id": row.get("security_id"),
            "symbol": row.get("symbol"),
            "name": row.get("name"),
            "sector": row.get("sector"),
            "size": row.get("size"),
            "research_priority_score": potential.get(
                "research_priority_score", row.get("acquisition_priority")
            ),
            "component_scores": dict(potential.get("component_scores") or {}),
            "doctrine_ranks": dict(potential.get("doctrine_ranks") or {}),
            "leading_doctrines": list(potential.get("leading_doctrines") or ()),
            "unresolved_residuals": list(
                potential.get("unresolved_residuals") or ()
            ),
            "selection_reason": row.get("selection_reason"),
        })
    coverage = dict(screen.get("coverage") or {})
    return {
        "schema": "jaggedthoughts-broad-equity-potential-ui-v1",
        "enabled": True,
        "status": "research_queue_ranked",
        "frame": screen.get("frame"),
        "retrieved_at": screen.get("retrieved_at"),
        "screen_sha256": screen.get("screen_sha256"),
        "coverage": coverage,
        "typed_exclusions": dict(screen.get("typed_exclusions") or {}),
        "ranking_contract": dict(screen.get("ranking_contract") or {}),
        "research_queue_contract": dict(
            screen.get("research_queue_contract") or {}
        ),
        "top_candidates": queue[:20],
        "potential_candidate_count": len(queue),
        "selected_count": len(selected),
        "selected_candidates": selected[:20],
        "acquisition_path": acquisition_path,
        "research_allocation": (
            "potential_rank_then_diversity_closure_then_bounded_web_underwriting"
        ),
        "web_research_boundary": (
            "web and primary-source research resolve durability, implied growth, "
            "strategy, and risk residuals only after deterministic potential ranking"
        ),
        "score_identity": "underwriting_priority_not_expected_return",
        "capital_authority": False,
    }


def _strategy_program_learning_status(root: Path) -> dict[str, Any]:
    """Project immutable program questions, classifications, and outcome plans."""
    request_dir = root / "research_jobs" / "strategy_programs" / "requests"
    result_dir = root / "institutional_learning" / "strategy_programs" / "results"
    plan_dir = root / "institutional_learning" / "strategy_programs" / "outcome-plans"

    def valid_rows(directory: Path, schema: str, hash_field: str) -> list[dict[str, Any]]:
        rows = []
        for path in sorted(directory.glob("*.json")):
            row = _read_json(path)
            if not row or row.get("schema") != schema:
                continue
            declared = str(row.get(hash_field) or "")
            if declared != stable_sha256({key: value for key, value in row.items() if key != hash_field}):
                continue
            rows.append({**row, "artifact_path": path.relative_to(root).as_posix()})
        return rows

    requests = valid_rows(
        request_dir, "jaggedthoughts-strategy-program-adoption-research-request-v1",
        "request_sha256",
    )
    results = valid_rows(
        result_dir, "jaggedthoughts-strategy-program-adoption-research-result-v1",
        "result_sha256",
    )
    plans = valid_rows(
        plan_dir, "jaggedthoughts-strategy-program-outcome-plan-v1", "plan_sha256",
    )
    outcomes = valid_rows(
        root / "institutional_learning" / "strategy_programs" / "outcomes",
        "jaggedthoughts-strategy-program-outcome-v1", "episode_sha256",
    )
    result_by_request = {str(row["request_sha256"]): row for row in results}
    plan_by_result = {str(row["result_sha256"]): row for row in plans}
    outcome_count_by_plan = Counter(str(row["plan_sha256"]) for row in outcomes)
    queue_by_request = {
        str((row.get("payload") or {}).get("request_sha256") or ""): row
        for row in ((research_agent_status(root).get("queue") or {}).get("jobs") or ())
        if row.get("kind") == "jaggedthoughts_strategy_program_adoption_research"
    }
    schedule = _read_json(root / "institutional_learning" / "scheduler" / "latest.json") or {}
    schedule_by_work = {
        str(row.get("work_id") or ""): row for row in schedule.get("actions") or ()
        if isinstance(row, Mapping)
    }
    rows = []
    for request in requests:
        result = result_by_request.get(str(request["request_sha256"]))
        plan = plan_by_result.get(str((result or {}).get("result_sha256") or ""))
        job = queue_by_request.get(str(request["request_sha256"])) or {}
        scheduled = schedule_by_work.get(str(job.get("work_id") or "")) or {}
        queue_status = str(job.get("status") or "awaiting_enqueue")
        rows.append({
            "entity_id": request["entity_id"],
            "request_id": request["request_id"],
            "request_sha256": request["request_sha256"],
            "work_id": job.get("work_id"),
            "candidate_program_count": len(request.get("candidate_programs") or ()),
            "candidate_programs": request.get("candidate_programs") or [],
            "common_option_ids": request.get("common_option_ids") or [],
            "observed_exact_option_event_count": len(
                request.get("observed_exact_option_event_sha256s") or ()
            ),
            "status": (
                "prospective_outcome_plan_frozen" if plan and plan.get("readout_count")
                else "classified" if result else
                "primary_source_search_running" if queue_status == "claimed" else
                "primary_source_search_failed" if queue_status == "dead_letter" else
                "queued_for_primary_source_classification" if queue_status == "queued" else
                queue_status
            ),
            "queue_status": queue_status, "queue_priority": job.get("priority"),
            "attempts": int(job.get("attempts") or 0),
            "learning_schedule_rank": scheduled.get("rank"),
            "learning_schedule_score": scheduled.get("ranking_score"),
            "classification": (result or {}).get("classification"),
            "selected_program_ids": (result or {}).get("selected_program_ids") or [],
            "readout_count": int((plan or {}).get("readout_count") or 0),
            "settled_readout_count": outcome_count_by_plan.get(str((plan or {}).get("plan_sha256") or ""), 0),
            "next_activation": (
                (plan or {}).get("next_activation")
                or (result or {}).get("next_activation")
                or "Classify the integrated program from opened primary sources."
            ),
            "artifact_path": (
                (plan or {}).get("artifact_path")
                or (result or {}).get("artifact_path")
                or request["artifact_path"]
            ),
        })
    pending_rows = sorted(
        (row for row in rows if not row.get("readout_count")),
        key=lambda row: (
            row.get("learning_schedule_rank") is None,
            row.get("learning_schedule_rank") or 0,
            -(row.get("queue_priority") or 0),
        ),
    )
    next_row = pending_rows[0] if pending_rows else None
    body = {
        "schema": "jaggedthoughts-strategy-program-learning-status-v1",
        "request_count": len(requests), "pending_count": sum(
            row["status"] in {
                "queued_for_primary_source_classification", "primary_source_search_running",
            } for row in rows
        ),
        "result_count": len(results),
        "exact_adoption_count": sum(
            row.get("classification") == "exact_integrated_program_adoption" for row in rows
        ),
        "prospective_outcome_plan_count": sum(bool(row["readout_count"]) for row in rows),
        "settled_program_outcome_count": len(outcomes),
        "rows": rows,
        "next_transition": ({
            "transition": "classify_integrated_program_from_primary_sources",
            "work_id": next_row.get("work_id"),
            "entity_id": next_row.get("entity_id"),
            "request_sha256": next_row.get("request_sha256"),
            "queue_status": next_row.get("queue_status"),
            "learning_schedule_rank": next_row.get("learning_schedule_rank"),
        } if next_row else None),
        "next_activation": (
            next_row["next_activation"] if next_row else
            "Compile a company frontier with at least two exact option events."
        ),
        "program_outcome_credit": False, "capital_authority": False,
    }
    return {**body, "status_sha256": stable_sha256(body)}


def _build_read_model_unlocked(workspace: str | Path | None = None) -> dict[str, Any]:
    """Build the finance-native UI projection without changing authority state."""
    root = resolve_workspace(workspace)
    config_path = root / "workspace.yaml"
    if not config_path.is_file():
        return {
            "schema": READ_MODEL_SCHEMA, "ok": True, "initialized": False,
            "workspace_path": str(root),
            "workspace_preview_root": _workspace_preview_root(root),
            "capital_authority": False,
            "next_action": "Initialize the investment workspace.",
        }
    config = _load_yaml(config_path)
    source_run = _current_source_run(root)
    build = _read_json(root / "state" / "latest_build.json")
    portfolio = _read_json(root / "portfolio" / "latest_assembly.json")
    # A compiler fixture may exercise the portfolio kernel, but only an
    # assembly owned by this workspace belongs in its current-book projection.
    if portfolio and portfolio.get("owner") != config.get("owner"):
        portfolio = None
    decisions = _decision_rows(root, config)
    paper_watch_history = _paper_watch_rows(root)
    history_by_id = {
        str(row.get("decision_id") or ""): row for row in paper_watch_history
    }
    paper_watch_decisions = []
    for current in current_paper_watch_decisions(root):
        prior = history_by_id.get(str(current.get("decision_id") or ""), {})
        paper_watch_decisions.append({
            **current,
            "artifact_path": current.get("decision_path"),
            "paper_watch_only": True,
            "research_evidence_admissibility": prior.get(
                "research_evidence_admissibility"
            ),
        })
    store_path = _store_path(root, config)
    settled: set[str] = set()
    settlement_scorecards: dict[str, dict[str, Any]] = {}
    funnel_transition_receipts: list[dict[str, Any]] = []
    verification: dict[str, Any] = {"ok": True, "leaf_count": 0, "edge_count": 0, "path": str(store_path)}
    research_memory: dict[str, Any] = {
        "schema": "jaggedthoughts-research-memory-v2", "source_count": 0,
        "mechanism_claim_count": 0, "dossier_count": 0,
        "research_coverage_count": 0, "research_coverage_assessment_count": 0,
        "strategy_phenotype_count": 0,
        "cross_entity_strategy_phenotype_count": 0,
        "monitor_subscription_count": 0, "source_change_event_count": 0,
        "reopen_request_count": 0, "reassessment_count": 0,
        "reused_source_count": 0, "sources": [], "research_coverage": [],
        "strategy_phenotypes": [], "mechanism_research_result_count": 0,
        "market_flow_successor_result_count": 0, "mechanism_family_count": 0,
        "model_research_results": [], "mechanism_families": [],
    }
    if store_path.exists():
        store = GoldenStore(store_path)
        verification = _verified_golden_store(root, store_path)
        research_memory = compile_research_memory(store)
        settled = _settled_decision_ids(store)
        settlement_scorecards = _settlement_scorecards(store)
        for metadata in reversed(store.list_leaves(
            object_kind="opportunity_funnel_transition", limit=10_000,
        )):
            leaf = store.get_leaf(str(metadata["leaf_sha256"]))
            payload = leaf.get("payload")
            if isinstance(payload, Mapping):
                funnel_transition_receipts.append(dict(payload))
    for row in decisions:
        row["settlement_status"] = "settled" if str(row["decision_id"]) in settled else "pending"
    pending = [
        row for row in decisions
        if row["settlement_status"] == "pending" and row["profile_stage"] in {"active", "reference"}
    ]
    source_receipts = list((source_run or {}).get("source_receipts") or [])
    source_statuses = list((source_run or {}).get("source_statuses") or [])
    latest_observations = _latest_observations(root, source_run)
    household_basis_snapshot = _read_json(
        root / "household" / "capital_market_basis" / "latest.json"
    )
    household_basis_as_of = str(
        ((household_basis_snapshot or {}).get("capital_market_basis") or {}).get("as_of")
        or ""
    ) or None
    household_goal_surface = None
    if config.get("household_intake"):
        try:
            household_goal_surface = _current_household_goal_surface(
                root, config, as_of=household_basis_as_of,
                observations=latest_observations,
            )
        except (KeyError, OSError, TypeError, ValueError, yaml.YAMLError) as error:
            household_goal_surface = {"available": False, "error": str(error)}
    metric_universe = metric_universe_surface(latest_observations)
    broad_equity_potential = _sec_frame_potential_projection(root)
    required_failures = [row for row in source_statuses if row.get("status") == "failed" and row.get("required")]
    operator_decisions = [
        row for row in decisions
        if row["data_class"] == "operator" and row["profile_stage"] == "active"
    ]
    operator_drafts = [
        row for row in decisions
        if row["data_class"] == "operator" and row["profile_stage"] == "draft"
    ]
    tournament_results: list[dict[str, Any]] = []
    for path in sorted((root / "tournaments" / "results").glob("*.json")):
        result = _read_json(path)
        if result:
            tournament_results.append({
                "tournament_id": result.get("tournament_id"), "mode": result.get("mode"),
                "episode_count": result.get("episode_count"), "inference_block_count": result.get("inference_block_count"),
                "survivor_model_ids": result.get("survivor_model_ids"),
                "capital_authority": result.get("capital_authority"),
                "result_path": path.relative_to(root).as_posix(),
                "report_path": f"reports/{result.get('tournament_id')}.md",
            })
    watchlists: list[dict[str, Any]] = []
    for path in sorted((root / "watchlists" / "results").glob("*.json")):
        result = _read_json(path)
        if result:
            watchlists.append({**result, "result_path": path.relative_to(root).as_posix()})
    company_quality: list[dict[str, Any]] = []
    for path in sorted((root / "quality").glob("*.json")):
        result = _read_json(path)
        if result:
            company_quality.append({**result, "result_path": path.relative_to(root).as_posix()})
    company_strategy_frontiers = _latest_company_strategy_frontiers(root)
    research_projects: list[dict[str, Any]] = []
    for registration in config.get("research_projects") or ():
        if not isinstance(registration, Mapping):
            continue
        project_path = (root / str(registration.get("path") or "")).resolve()
        prospective_shadow = _read_json(
            project_path / "workspace" / "prospective_shadow" / "latest.json"
        ) or {}
        try:
            result = _research_project_projection(root, registration)
            partition_results = result.get("partition_results") or {}
            research_projects.append({
                **{key: result[key] for key in (
                    "project_id", "label", "mode", "project_path", "evaluated_at",
                    "evidence_epoch", "source_url", "row_counts", "point_in_time_authority",
                    "iteration_count", "harness_ok", "screen_pass", "score",
                    "gates", "research_result_sha256", "authority",
                    "capital_authority", "promotion_eligible", "status",
                )},
                "search_lineage": result["search_lineage"],
                "historical_admission": result.get("historical_admission"),
                "prospective_shadow": prospective_shadow,
                "charter_present": True,
                "result_path": f"experiments/results/{result['project_id']}.json",
                "partition_gates": {
                    name: {
                        gate: bool(value) for gate, value in values.items()
                        if gate.endswith("_pass") and isinstance(value, bool)
                    }
                    for name, values in partition_results.items() if isinstance(values, Mapping)
                },
            })
        except (KeyError, OSError, ValueError):
            research_projects.append({
                "project_id": str(registration.get("project_id") or "unknown"),
                "label": str(registration.get("label") or "Research project"),
                "mode": str(registration.get("mode") or "research"),
                "charter_present": False,
                "harness_ok": False,
                "screen_pass": False,
                "score": None,
                "partition_gates": {},
                "prospective_shadow": prospective_shadow,
                "capital_authority": False,
                "status": "evidence_missing",
            })
    market_flow_experiments: list[dict[str, Any]] = []
    for path in sorted((root / "experiments" / "results").glob("*.json")):
        result = _read_json(path)
        if result and result.get("schema") in {
            "jaggedthoughts-market-flow-backtest-v1",
            "jaggedthoughts-cross-sectional-market-flow-evidence-v2",
            "jaggedthoughts-company-state-flow-evidence-v1",
            "jaggedthoughts-company-state-representation-replay-v1",
            "jaggedthoughts-company-state-path-action-run-v1",
        }:
            if result.get("schema") == "jaggedthoughts-company-state-path-action-run-v1":
                result = {
                    **result,
                    "settlement_status": _read_json(
                        root / "experiments" / "settlements"
                        / str(result.get("run_sha256") or "") / "latest.json"
                    ),
                }
            market_flow_experiments.append({**result, "summary_path": path.relative_to(root).as_posix()})
    catalog = _read_json(root / "universe" / "catalog-latest.json")
    catalog_summary = None
    if catalog:
        catalog_summary = {
            key: value for key, value in catalog.items() if key != "securities"
        }
        catalog_summary["catalog_path"] = "universe/catalog-latest.json"
    latest_scout = _read_json(root / "research_jobs" / "latest.json")
    scheduled_scout_cycle = _read_json(
        root / "research_jobs" / "scheduled" / "latest.json"
    )
    latest_enrichment_cycle = _read_json(
        root / "research_jobs" / "enrichment" / "latest.json"
    )
    latest_enrichment_execution = _read_json(
        root / "research_jobs" / "enrichment" / "latest_execution.json"
    )
    research_job_queue = research_job_snapshot(
        root / "state" / "research_jobs.sqlite3", limit=500,
    )
    try:
        subscription_research = research_agent_status(root, include_jobs=False)
        live_research = research_agent_live_status(root)
        subscription_research = {
            **subscription_research,
            "active_jobs": live_research["active_jobs"],
            "candidate_lane": live_research["candidate_lane"],
            "activation_lane": live_research["activation_lane"],
            "fund_lane": live_research["fund_lane"],
            "frozen_chain_lane": live_research["frozen_chain_lane"],
            "next_job": live_research["next_job"],
            "live_queue_counts": live_research["queue_counts"],
            "live_queued_by_kind": live_research["queued_by_kind"],
            "live_observed_at": live_research["observed_at"],
        }
    except (FileNotFoundError, OSError, TypeError, ValueError, yaml.YAMLError) as error:
        subscription_research = {
            "schema": "jaggedthoughts-subscription-research-status-v1",
            "enabled": False, "error": str(error),
        }
    learning_schedule = _read_json(
        root / "institutional_learning" / "scheduler" / "latest.json"
    ) or {
        "schema": "jaggedthoughts-institutional-learning-schedule-v1",
        "queued_action_count": 0,
        "actions": [],
        "next_action": None,
        "status": "awaiting_research_queue_cycle",
        "capital_authority": False,
    }
    try:
        research_budget_tournament = research_budget_tournament_status(root)
    except (OSError, TypeError, ValueError) as error:
        research_budget_tournament = {
            "schema": "jaggedthoughts-research-budget-tournament-status-v1",
            "enabled": False,
            "status": "invalid_current_block",
            "error": str(error),
            "capital_authority": False,
            "queue_mutation_authority": False,
        }
    activation_matrix_policy_learning = _read_json(
        root / "research_jobs" / "activation" / "matrix_policy" / "latest.json"
    ) or {
        "schema": "jaggedthoughts-activation-matrix-policy-learning-v2",
        "status": "collecting_matched_settlements",
        "observed_episode_count": 0,
        "complete_pair_count": 0,
        "minimum_pairs": 20,
        "preferred_arm": None,
        "routing_change_allowed": False,
        "future_routing": {
            "incumbent_question": 0.5,
            "stochastic_matrix_selected_question": 0.5,
        },
        "capital_authority": False,
    }
    try:
        point_in_time_evidence = evidence_vault_status(root, store_path=store_path)
    except (KeyError, OSError, TypeError, ValueError) as error:
        point_in_time_evidence = {
            "schema": "jaggedthoughts-point-in-time-evidence-status-v1",
            "enabled": False, "status": "invalid_archive",
            "error": str(error), "capital_authority": False,
        }
    sealed_walk_forward_profile = (
        root / "point_in_time_replay" / "sealed_walk_forward_seed.json"
    )
    try:
        sealed_walk_forward_readiness = (
            sealed_walk_forward_status(
                root, sealed_walk_forward_profile,
                owner=str(config.get("owner") or "operator-paper-book"),
                store_path=store_path,
            )
            if sealed_walk_forward_profile.is_file()
            else {
                "schema": "jaggedthoughts-sealed-walk-forward-status-v1",
                "enabled": False,
                "status": "profile_missing",
                "capital_authority": False,
            }
        )
    except (KeyError, OSError, TypeError, ValueError) as error:
        sealed_walk_forward_readiness = {
            "schema": "jaggedthoughts-sealed-walk-forward-status-v1",
            "enabled": False,
            "status": "invalid_profile_or_archive",
            "error": str(error),
            "capital_authority": False,
        }
    try:
        adaptive_execution = execution_market_status(root)
    except (OSError, TypeError, ValueError) as error:
        adaptive_execution = {
            "schema": "jaggedthoughts-execution-market-status-v1",
            "enabled": False,
            "error": str(error),
            "capital_authority": False,
        }
    try:
        closed_book = closed_book_status(root)
    except (OSError, TypeError, ValueError) as error:
        closed_book = {
            "schema": "jaggedthoughts-closed-book-status-v1",
            "enabled": False,
            "error": str(error),
            "capital_authority": False,
        }
    try:
        ablation_status = dict(closed_book.get("underwriting_ablation") or {})
        latest_closed_run = dict(closed_book.get("latest_run") or {})
        policy_time = (
            ablation_status.get("latest_settled_at")
            or latest_closed_run.get("sealed_at")
            or latest_closed_run.get("opened_at")
            or "1970-01-01T00:00:00Z"
        )
        underwriting_method_policy = compile_underwriting_method_policy(
            ablation_status, compiled_at=str(policy_time),
        )
    except (KeyError, OSError, TypeError, ValueError) as error:
        underwriting_method_policy = {
            "schema": "jaggedthoughts-underwriting-method-policy-v1",
            "routing_decision": "continue_balanced",
            "status": "awaiting_valid_settled_ablation",
            "error": str(error),
            "weights_authority": False,
            "capital_authority": False,
        }
    try:
        market_state = market_state_forecast_status(root)
    except (OSError, TypeError, ValueError) as error:
        market_state = {
            "schema": "jaggedthoughts-market-state-forecast-status-v1",
            "enabled": False,
            "error": str(error),
            "capital_authority": False,
        }
    try:
        institutional_learning = institutional_learning_status(root)
    except (OSError, TypeError, ValueError) as error:
        institutional_learning = {
            "schema": "jaggedthoughts-institutional-learning-state-v1",
            "enabled": False,
            "status": "error",
            "error": str(error),
            "capital_authority": False,
        }
    historical_strategy_event_replay = _read_json(
        root / "institutional_learning" / "historical_strategy_event_replay"
        / "latest.json"
    ) or {
        "schema": "jaggedthoughts-historical-strategy-event-replay-v1",
        "status": "awaiting_historical_strategy_events",
        "event_count": 0,
        "matured_event_count": 0,
        "outcome_ready_event_count": 0,
        "episode_count": 0,
        "entity_count": 0,
        "cohort_summaries": [],
        "capital_authority": False,
    }
    historical_strategy_walk_forward = _read_json(
        root / "institutional_learning" / "historical_strategy_event_replay"
        / "walk-forward.json"
    ) or {
        "schema": "jaggedthoughts-strategy-walk-forward-tournament-v1",
        "status": "awaiting_historical_strategy_replay",
        "fold_count": 0,
        "scored_episode_count": 0,
        "policy_summary": {},
        "capital_authority": False,
    }
    historical_strategy_security_walk_forward = _read_json(
        root / "institutional_learning" / "historical_strategy_event_replay"
        / "security-walk-forward.json"
    ) or {
        "schema": "jaggedthoughts-strategy-security-walk-forward-tournament-v1",
        "status": "awaiting_historical_strategy_replay",
        "fold_count": 0,
        "scored_episode_count": 0,
        "policy_summary": {},
        "capital_authority": False,
    }
    historical_strategy_representation_learning = _read_json(
        root / "institutional_learning" / "historical_strategy_event_replay"
        / "representation-learning.json"
    ) or {
        "schema": "jaggedthoughts-strategy-security-representation-learning-v1",
        "status": "awaiting_strategy_security_tournament",
        "conjecture_count": 0,
        "conjectures": [],
        "capital_authority": False,
    }
    historical_strategy_control_design = _read_json(
        root / "institutional_learning" / "historical_strategy_event_replay"
        / "control-design-latest.json"
    ) or {
        "schema": "jaggedthoughts-historical-strategy-control-design-v1",
        "status": "awaiting_historical_strategy_replay",
        "activation_cell_count": 0,
        "treated_history_ready_count": 0,
        "control_source_request_count": 0,
        "pretrend_rankable_control_count": 0,
        "capital_authority": False,
    }
    historical_strategy_control_acquisition = _read_json(
        root / "institutional_learning" / "historical_strategy_event_replay"
        / "control-acquisition-latest.json"
    ) or {
        "schema": "jaggedthoughts-historical-strategy-control-acquisition-v1",
        "status": "awaiting_control_source_frontier",
        "selected_request_count": 0,
        "attempted_entity_count": 0,
        "capital_authority": False,
    }
    historical_strategy_bulk_corpus = _read_json(
        root / "institutional_learning" / "historical_strategy_bulk_corpus" / "latest.json"
    ) or {
        "schema": "jaggedthoughts-historical-strategy-bulk-event-corpus-v2",
        "status": "awaiting_sec_bulk_archive",
        "event_count": 0, "event_entity_count": 0,
        "capital_authority": False,
    }
    historical_strategy_bulk_learning = _read_json(
        root / "institutional_learning" / "historical_strategy_bulk_learning" / "latest.json"
    ) or {
        "schema": "jaggedthoughts-historical-strategy-bulk-learning-v1",
        "status": "awaiting_bulk_strategy_corpus",
        "supported_design_cell_count": 0, "classified_event_count": 0,
        "queue_count": 0, "ambiguous_semantic_queue_count": 0,
        "capital_authority": False,
    }
    historical_strategy_bulk_outcomes = _read_json(
        root / "institutional_learning" / "historical_strategy_bulk_outcomes" / "latest.json"
    ) or {
        "schema": "jaggedthoughts-historical-strategy-bulk-outcomes-v2",
        "status": "awaiting_bulk_companyfacts",
        "covered_entity_count": 0, "observation_count": 0,
        "capital_authority": False,
    }
    historical_strategy_bulk_panel_readiness = _read_json(
        root / "institutional_learning" / "historical_strategy_bulk_outcomes"
        / "panel-readiness.json"
    ) or {
        "schema": "jaggedthoughts-historical-strategy-panel-readiness-v8",
        "estimation_status": "awaiting_typed_events_and_outcomes",
        "history_ready_event_count": 0, "group_time_ready_cell_count": 0,
        "capital_authority": False,
    }
    historical_strategy_bulk_effects = _read_json(
        root / "institutional_learning" / "historical_strategy_bulk_outcomes"
        / "effect-diagnostics.json"
    ) or {
        "schema": "jaggedthoughts-historical-strategy-bulk-effect-diagnostics-v1",
        "status": "awaiting_joint_panel", "ready_cell_count": 0,
        "causal_claim": False, "capital_authority": False,
    }
    historical_strategy_bulk_panel_projection = {
        key: value for key, value in historical_strategy_bulk_panel_readiness.items()
        if key not in {"history_status", "bounded_control_status", "adoption_cells"}
    }
    historical_strategy_bulk_effects_projection = {
        key: value for key, value in historical_strategy_bulk_effects.items()
        if key != "diagnostics"
    }
    historical_strategy_bulk_effects_projection["diagnostics"] = [
        {
            "cell": {
                key: value for key, value in dict(row.get("cell") or {}).items()
                if key in {"implementation_mode", "adoption_year"}
            },
            "evaluation": {
                "diagnostic_status": (row.get("evaluation") or {}).get(
                    "diagnostic_status"
                ),
            },
        }
        for row in historical_strategy_bulk_effects.get("diagnostics") or ()
        if isinstance(row, Mapping)
    ]
    historical_strategy_outcome_robustness = _read_json(
        root / "institutional_learning" / "historical_strategy_bulk_outcomes"
        / "outcome-robustness.json"
    ) or {
        "schema": "jaggedthoughts-historical-strategy-outcome-robustness-v1",
        "status": "awaiting_joint_panel", "family_count": 0,
        "causal_claim": False, "capital_authority": False,
    }
    historical_strategy_law_search = _read_json(
        root / "institutional_learning" / "historical_strategy_bulk_outcomes"
        / "law-search.json"
    ) or {
        "schema": "jaggedthoughts-historical-strategy-law-search-v1",
        "status": "awaiting_parent_diagnostic", "frozen_child_candidate_count": 0,
        "acquisition_frontier_count": 0, "capital_authority": False,
    }
    historical_strategy_law_trial_current = _read_json(
        root / "institutional_learning" / "historical_strategy_bulk_outcomes"
        / "law-trials" / "current.json"
    ) or {
        "schema": "jaggedthoughts-historical-strategy-law-trial-v1",
        "status": "awaiting_child_law_frontier", "capital_authority": False,
    }
    historical_strategy_law_trial_epoch = _read_json(
        root / "institutional_learning" / "historical_strategy_bulk_outcomes"
        / "law-trials" / "latest.json"
    ) or {}
    historical_strategy_law_trial = (
        {
            **historical_strategy_law_trial_current,
            **historical_strategy_law_trial_epoch,
            "schema": historical_strategy_law_trial_current.get("schema"),
            "evaluation_epoch_schema": historical_strategy_law_trial_epoch.get(
                "schema"
            ),
        }
        if historical_strategy_law_trial_epoch.get("trial_sha256")
        == historical_strategy_law_trial_current.get("trial_sha256")
        else historical_strategy_law_trial_current
    )
    strategy_path_shadow = _read_json(
        root / "institutional_learning" / "strategy_path_shadow" / "latest.json"
    ) or {
        "schema": "jaggedthoughts-strategy-path-shadow-v1",
        "status": "awaiting_qualified_path_grammar",
        "move_count": 0, "typed_path_count": 0, "forecast_count": 0,
        "capital_authority": False,
    }
    strategy_event_research_acquisition = _read_json(
        root / "institutional_learning" / "strategy_path_shadow"
        / "event-research-acquisition-latest.json"
    ) or {
        "schema": "jaggedthoughts-strategy-event-research-acquisition-v1",
        "status": "awaiting_strategy_event", "discovery_outcomes": [],
        "capital_authority": False,
    }
    strategy_business_clock = _read_json(
        root / "institutional_learning" / "strategy_business_clock" / "latest.json"
    ) or {
        "schema": "jaggedthoughts-strategy-business-clock-v1",
        "status": "awaiting_first_cycle",
        "historical_strategy_episode_count": 0,
        "capital_authority": False,
    }
    strategy_state_experiment = _read_json(
        root / "experiments" / "results" / "strategy-state-experiment.json"
    ) or {}
    strategy_state_control_acquisition = _read_json(
        root / "experiments" / "results" / "strategy-state-control-acquisition.json"
    ) or {
        "schema": "jaggedthoughts-strategy-state-control-acquisition-v1",
        "status": "awaiting_strategy_business_clock",
        "eligible_no_family_controls_exist": False,
        "audit": {},
        "next_activation": "Run the strategy business clock.",
        "capital_authority": False,
    }
    strategy_state_successor = _read_json(
        root / "experiments" / "results" / "strategy-state-successor-readiness.json"
    ) or {
        "schema": "jaggedthoughts-strategy-state-successor-readiness-v1",
        "status": "awaiting_predecessor_experiment",
        "peer_control_frontier": {}, "selected_dependencies": [],
        "capital_authority": False,
    }
    strategy_state_transition_join = _read_json(
        root / "experiments" / "results" / "strategy-state-transition-join.json"
    ) or {
        "schema": "jaggedthoughts-strategy-state-transition-join-v1",
        "status": "awaiting_company_state_and_strategy_events",
        "transition_episode_count": 0, "exact_event_issuer_count": 0,
        "observable_post_event_issuer_count": 0,
        "capital_authority": False,
    }
    max_caliber_recovery = _read_json(
        root / "experiments" / "results" / "max-caliber-recovery.json"
    ) or {
        "schema": "jaggedthoughts-max-caliber-recovery-v1",
        "status": "awaiting_recovery_audit",
        "signal_authority": False,
        "capital_authority": False,
    }
    strategy_path_lagrangian = _read_json(
        root / "experiments" / "results" / "strategy-path-lagrangian.json"
    ) or {
        "schema": "jaggedthoughts-strategy-path-lagrangian-activation-v1",
        "status": "awaiting_input_gates", "blockers": [], "tournament": None,
        "signal_authority": False, "capital_authority": False,
    }
    strategy_program_representation = _read_json(
        root / "experiments" / "results" / "strategy-program-representation-ablation.json"
    ) or {
        "schema": "jaggedthoughts-strategy-program-representation-activation-v1",
        "status": "awaiting_input_gates", "blockers": [], "tournament": None,
        "capital_authority": False,
    }
    strategy_move_learning = _read_json(
        root / "institutional_learning" / "strategy_moves" / "latest.json"
    ) or {
        "schema": "jaggedthoughts-strategy-move-library-v1",
        "move_count": 0, "move_family_count": 0, "measurable_move_count": 0,
        "outcome_episode_count": 0, "next_outcome_due_at": None,
        "next_activation": "Compile company strategy frontiers.",
        "capital_authority": False,
    }
    strategy_program_learning = _strategy_program_learning_status(root)
    strategy_program_transfer = _read_json(
        root / "institutional_learning" / "strategy_programs" / "transfer-latest.json"
    ) or {
        "schema": "jaggedthoughts-strategy-program-transfer-index-v1",
        "card_count": 0, "settled_episode_count": 0,
        "cross_company_card_count": 0, "comparison_ready_card_count": 0,
        "next_activation": "Accumulate independent integrated-program outcomes.",
        "causal_program_credit": False, "capital_authority": False,
    }
    strategy_program_control_acquisition = _read_json(
        root / "institutional_learning" / "strategy_programs"
        / "control-acquisition-latest.json"
    ) or {
        "schema": STRATEGY_PROGRAM_CONTROL_ACQUISITION_SCHEMA,
        "card_count": 0,
        "ready_fragmented_control_count": 0,
        "ready_local_peak_control_count": 0,
        "next_transition": None,
        "causal_program_credit": False,
        "security_return_credit": False,
        "capital_authority": False,
    }
    strategy_program_comparison = _read_json(
        root / "institutional_learning" / "strategy_programs" / "comparison-latest.json"
    ) or {
        "schema": STRATEGY_PROGRAM_OPERATING_COMPARISON_SCHEMA,
        "status": "awaiting_integrated_program_outcomes",
        "card_count": 0, "treated_episode_count": 0, "control_episode_count": 0,
        "reviewable_composition_card_count": 0,
        "operating_association_reviewable": False,
        "causal_program_credit": False, "capital_authority": False,
    }
    strategy_cohort_research = _read_json(
        root / "institutional_learning" / "strategy_cohorts" / "latest.json"
    ) or {
        "schema": "jaggedthoughts-strategy-cohort-research-plan-v2",
        "request_count": 0, "exact_focal_move_count": 0,
        "next_activation": "Compile an exact source-bound strategy adoption event.",
        "capital_authority": False,
    }
    strategy_event_activation = _read_json(
        root / "institutional_learning" / "strategy_cohorts" / "activation-latest.json"
    ) or {
        "schema": "jaggedthoughts-strategy-event-activation-v1",
        "activation_count": 0, "activations": [], "blocked_count": 0, "blocks": [],
        "next_activation": "Classify the initial bounded strategy-peer cohort.",
        "capital_authority": False,
    }
    all_strategy_cohort_results = [
        row for path in sorted((root / "institutional_learning" / "strategy_cohorts" / "results").glob("*.json"))
        if (row := _read_json(path))
    ]
    current_cohort_requests = {
        str(row.get("request_sha256") or "")
        for row in strategy_cohort_research.get("requests") or ()
    }
    strategy_cohort_results = [
        row for row in all_strategy_cohort_results
        if str(row.get("request_sha256") or "") in current_cohort_requests
    ]
    strategy_cohort_coverage = _read_json(
        root / "institutional_learning" / "strategy_cohorts" / "coverage-chain.json"
    ) or {}
    coverage_bindings = [
        row for row in strategy_cohort_coverage.get("bindings") or ()
        if isinstance(row, Mapping)
    ]
    bound_result_count = int(
        strategy_cohort_coverage.get("bound_result_count") or len(strategy_cohort_results)
    )
    pending_interval_count = sum(bool(row.get("pending_delta")) for row in coverage_bindings)
    unclassified_count = int(
        strategy_cohort_coverage.get("pending_result_count")
        or max(0, len(current_cohort_requests) - bound_result_count)
    )
    strategy_cohort_research = {
        **strategy_cohort_research,
        "result_count": bound_result_count,
        "exact_result_count": int(
            strategy_cohort_coverage.get("exact_result_count") or len(strategy_cohort_results)
        ),
        "recovered_compatible_result_count": int(
            strategy_cohort_coverage.get("recovered_compatible_result_count") or 0
        ),
        "unclassified_request_count": unclassified_count,
        "pending_interval_refresh_count": pending_interval_count,
        "pending_research_count": unclassified_count,
        "prior_result_count": len(all_strategy_cohort_results) - len(strategy_cohort_results),
        "classification_counts": dict(sorted(Counter(
            str(row.get("classification") or "unknown") for row in coverage_bindings
        ).items())),
        "next_activation": (
            "Strict peer classification is complete; acquire compatible controls and post-treatment "
            "operating histories before selecting a mechanism grain."
            if bound_result_count == len(current_cohort_requests) and not pending_interval_count
            else (
                f"Search {unclassified_count} unclassified peers; monitor "
                f"{pending_interval_count} covered intervals for material source changes."
            )
        ),
    }
    strategy_active_comparator = _read_json(
        root / "institutional_learning" / "strategy_cohorts"
        / "active-comparator-frontier.json"
    ) or {
        "schema": "jaggedthoughts-strategy-active-comparator-frontier-v1",
        "selection_status": "awaiting_strategy_cohort_frontier",
        "comparison_groups": [],
        "audit": {},
        "next_company_facts_acquisition_entities": [],
        "causal_estimate_ran": False,
        "rank_authority": False,
        "law_authority": False,
        "capital_authority": False,
    }
    strategy_law_induction = _read_json(
        root / "institutional_learning" / "strategy_laws" / "latest.json"
    ) or {
        "schema": STRATEGY_LAW_INDUCTION_SCHEMA,
        "candidate_count": 0, "eligible_candidate_count": 0,
        "status": "awaiting_strategy_learning_cycle", "next_activation": [],
        "capital_authority": False,
    }
    strategy_valuation_bridge = _read_json(
        root / "institutional_learning" / "strategy_valuation" / "latest.json"
    ) or {
        "schema": "jaggedthoughts-strategy-valuation-bridge-readiness-v1",
        "status": "awaiting_strategy_learning_cycle",
        "transported_effect_count": 0, "direct_financial_effect_count": 0,
        "capital_authority": False,
    }
    strategy_transfer_acquisition = _read_json(
        root / "institutional_learning" / "strategy_acquisition" / "latest.json"
    ) or {}
    acquisition_body = {
        key: value for key, value in strategy_transfer_acquisition.items()
        if key != "policy_sha256"
    }
    if not (
        strategy_transfer_acquisition.get("schema") == STRATEGY_TRANSFER_ACQUISITION_SCHEMA
        and strategy_transfer_acquisition.get("policy_sha256") == stable_sha256(acquisition_body)
        and strategy_transfer_acquisition.get("library_sha256")
        == strategy_move_learning.get("library_sha256")
    ):
        try:
            control_frontier = compile_workspace_strategy_control_eligibility(root)
            strategy_transfer_acquisition = compile_strategy_transfer_acquisition_policy(
                library=strategy_move_learning,
                cohort_plan=strategy_cohort_research,
                control_frontier=control_frontier,
                panel_readiness=_read_json(
                    root / "institutional_learning" / "strategy_cohorts" / "panel-readiness.json"
                ) or {},
                queue_jobs=research_job_queue.get("jobs") or (),
                subscription_research=subscription_research,
                generated_at=_utc_now(),
            )
        except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
            strategy_transfer_acquisition = {
                "schema": STRATEGY_TRANSFER_ACQUISITION_SCHEMA,
                "status": "unavailable",
                "error": str(error),
                "control_batch": {"selected": []},
                "next_transition": None,
                "capital_authority": False,
            }
    try:
        max_caliber_readiness = compile_max_caliber_readiness(
            max_caliber_recovery, strategy_state_transition_join, learning_schedule,
        )
    except (KeyError, TypeError, ValueError) as error:
        max_caliber_readiness = {
            "schema": "jaggedthoughts-max-caliber-readiness-v1",
            "status": "unavailable", "error": str(error),
            "signal_authority": False, "capital_authority": False,
        }
    try:
        strategy_control_runtime = compile_workspace_strategy_control_runtime_status(root)
    except (FileNotFoundError, OSError, TypeError, ValueError) as error:
        strategy_control_runtime = {
            "schema": "jaggedthoughts-strategy-control-runtime-status-v1",
            "job_count": 0, "runtime_state_counts": {}, "jobs": [],
            "status": "unavailable", "error": str(error), "capital_authority": False,
        }
    try:
        strategy_transfer = compile_strategy_transfer_index(
            strategy_move_learning,
            institutional_learning,
            generated_at=str(institutional_learning.get("generated_at") or _utc_now()),
        )
    except (KeyError, TypeError, ValueError) as error:
        strategy_transfer = {
            "schema": "jaggedthoughts-strategy-transfer-index-v1",
            "card_count": 0,
            "settled_operating_outcome_count": 0,
            "counterexample_count": 0,
            "cards": [],
            "status": "unavailable",
            "error": str(error),
            "capital_authority": False,
        }
    try:
        _strategy_alpha_episodes, strategy_alpha_evidence = compile_strategy_alpha_evidence(root)
    except (OSError, TypeError, ValueError) as error:
        strategy_alpha_evidence = {
            "schema": "jaggedthoughts-strategy-alpha-evidence-v1",
            "eligible_count": 0,
            "tournament_ready": False,
            "gap_counts": {},
            "error": str(error),
            "capital_authority": False,
        }
    strategy_alpha_tournament = strategy_alpha_tournament_surface(
        strategy_transfer, strategy_alpha_evidence,
    )
    strategy_alpha_tournament["source_readiness"] = (
        compile_strategy_alpha_source_readiness(root)
    )
    strategy_alpha_history = compile_strategy_alpha_episode_history(root)
    issuance_blockers = [
        row for row in strategy_alpha_history["episodes"]
        if row["run_id"] in strategy_alpha_history["issuance_blocking_run_ids"]
    ]
    cohort_gate = strategy_alpha_cohort_gate(
        issuance_blockers, evaluated_at=_utc_now(),
        **strategy_alpha_cohort_policy(root),
    )
    strategy_alpha_tournament["issuance_gate"] = {
        "status": (
            "cohort_capacity_available" if cohort_gate["admission_available"]
            else "blocked_cohort_capacity"
        ),
        "current_abi_blocker_count": len(issuance_blockers),
        "current_abi_open_issuer_count": cohort_gate["open_issuer_count"],
        **cohort_gate,
        "legacy_unsettled_count": len(
            strategy_alpha_history["nonblocking_legacy_unsettled_run_ids"]
        ),
        "capital_authority": False,
    }
    strategy_alpha_tournament["evidence"] = strategy_alpha_evidence
    if strategy_alpha_evidence.get("tournament_ready"):
        try:
            frozen_at = min(
                episode.trained_through for episode in _strategy_alpha_episodes
            )
            strategy_alpha_tournament["evaluation"] = evaluate_strategy_alpha_tournament(
                tournament_id=(
                    "strategy-alpha-live:"
                    f"{str(strategy_alpha_evidence['evidence_sha256'])[:20]}"
                ),
                owner=str(config.get("owner") or "operator-paper-book"),
                as_of=_utc_now(),
                candidate_set_frozen_at=frozen_at,
                episodes=_strategy_alpha_episodes,
            )
            strategy_alpha_tournament["status"] = strategy_alpha_tournament[
                "evaluation"
            ]["status"]
        except (KeyError, TypeError, ValueError) as error:
            strategy_alpha_tournament["evaluation"] = {
                "status": "error", "error": str(error), "capital_authority": False,
            }
    try:
        strategy_alpha_tournament["binding_activation"] = strategy_alpha_binding_status(root)
    except (OSError, TypeError, ValueError) as error:
        strategy_alpha_tournament["binding_activation"] = {
            "schema": "jaggedthoughts-strategy-alpha-binding-status-v1",
            "run_count": 0,
            "bindable_count": 0,
            "gap_counts": {},
            "error": str(error),
            "capital_authority": False,
        }
    try:
        strategy_dual_outcomes = compile_strategy_dual_outcome_episodes(root)
    except (OSError, TypeError, ValueError) as error:
        strategy_dual_outcomes = {
            "schema": "jaggedthoughts-strategy-dual-outcome-episodes-v1",
            "episode_count": 0, "pending_count": 0, "settled_count": 0,
            "status": "unavailable", "error": str(error),
            "capital_authority": False,
        }
    try:
        strategy_outcome_acquisition = compile_workspace_strategy_outcome_acquisition(root)
    except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
        strategy_outcome_acquisition = {
            "schema": "jaggedthoughts-strategy-outcome-acquisition-v1",
            "unsettled_contract_count": 0,
            "due_contract_count": 0,
            "eligible_outcome_count": 0,
            "blocked_due_contract_count": 0,
            "status": "unavailable",
            "error": str(error),
            "capital_authority": False,
        }
    try:
        strategy_program_outcome_acquisition = (
            compile_workspace_strategy_program_outcome_acquisition(root)
        )
    except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
        strategy_program_outcome_acquisition = {
            "schema": "jaggedthoughts-strategy-program-outcome-acquisition-v1",
            "unsettled_readout_count": 0, "due_readout_count": 0,
            "eligible_episode_count": 0, "blocked_due_readout_count": 0,
            "status": "unavailable", "error": str(error),
            "causal_program_credit": False, "capital_authority": False,
        }
    underwriting_full: dict[str, Any] = {}
    try:
        underwriting_full = _read_json(root / "underwriting" / "latest.json")
        if not underwriting_full:
            underwriting_full = compile_workspace_underwriting_index(root)
        current_discovery_sha = str((_read_json(root / "discovery" / "latest.json") or {}).get("run_sha256") or "")
        underwriting_current = bool(
            current_discovery_sha
            and underwriting_full.get("discovery_run_sha256") == current_discovery_sha
        )
        underwriting_index = {
            **{key: value for key, value in underwriting_full.items() if key != "candidates"},
            "candidates": list(underwriting_full.get("candidates") or ())[:50],
            "result_path": "underwriting/latest.json",
            "current": underwriting_current,
            "next_activation": (
                "Inspect the typed underwriting coordinates."
                if underwriting_current
                else "Run the due capital cycle to join the latest discovery and market-state epochs."
            ),
        }
    except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
        underwriting_index = {
            "schema": "jaggedthoughts-underwriting-opportunity-index-v1",
            "candidate_count": 0,
            "ranking_eligible_count": 0,
            "state_price_aware_count": 0,
            "candidates": [],
            "status": "unavailable",
            "error": str(error),
            "capital_authority": False,
        }
        underwriting_full = underwriting_index
    try:
        state_pricing = audit_workspace_state_price_readiness(
            root, latest_observations=latest_observations,
        )
    except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
        state_pricing = {
            "schema": "jaggedthoughts-state-price-workspace-readiness-v1",
            "payoff_state_contract_count": 0,
            "eligible_contract_count": 0,
            "status": "unavailable",
            "error": str(error),
            "capital_authority": False,
        }
    try:
        state_price_proposals = _read_json(root / "state_pricing" / "proposal-audit.json")
        current_discovery_sha = str((_read_json(root / "discovery" / "latest.json") or {}).get("run_sha256") or "")
        if not state_price_proposals or state_price_proposals.get("discovery_run_sha256") != current_discovery_sha:
            state_price_proposals = audit_workspace_proposals(root)
        state_pricing = {**state_pricing, "proposal_audit": state_price_proposals}
    except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
        state_pricing = {
            **state_pricing,
            "proposal_audit": {
                "schema": "jaggedthoughts-state-price-proposal-audit-v1",
                "valid_proposal_count": 0,
                "solver_eligible_count": 0,
                "status": "unavailable",
                "error": str(error),
                "capital_authority": False,
            },
        }
    try:
        modeled_grid_audit = _read_json(root / "state_pricing" / "modeled-grid-audit.json")
        if not modeled_grid_audit or modeled_grid_audit.get("discovery_run_sha256") != current_discovery_sha:
            modeled_grid_audit = _compile_workspace_modeled_payoff_grids(root)
        state_pricing = {**state_pricing, "modeled_grid_audit": modeled_grid_audit}
    except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
        modeled_grid_audit = {
            "schema": "jaggedthoughts-modeled-payoff-grid-audit-v1",
            "eligible_grid_count": 0, "positive_state_price_count": 0,
            "status": "unavailable", "error": str(error), "capital_authority": False,
        }
        state_pricing = {
            **state_pricing,
            "modeled_grid_audit": modeled_grid_audit,
        }
    try:
        grammar_evaluation_schedule = schedule_valuation_grammar_evaluations(
            modeled_grid_audit["grammar_learning"],
            _read_json(root / "discovery" / "latest.json") or {},
            scheduled_at=str(modeled_grid_audit["grammar_learning"]["compiled_at"]),
        )
        state_pricing = {
            **state_pricing,
            "grammar_evaluation_schedule": grammar_evaluation_schedule,
        }
    except (KeyError, TypeError, ValueError) as error:
        state_pricing = {
            **state_pricing,
            "grammar_evaluation_schedule": {
                "schema": "jaggedthoughts-valuation-grammar-evaluation-schedule-v1",
                "evaluation_count": 0, "ready_count": 0,
                "status": "unavailable", "error": str(error), "capital_authority": False,
            },
        }
    try:
        portfolio_policy = portfolio_policy_status(root)
    except (OSError, TypeError, ValueError) as error:
        portfolio_policy = {
            "schema": "jaggedthoughts-portfolio-policy-status-v1",
            "error": str(error), "run_count": 0, "settled_count": 0,
            "pending_count": 0, "capital_authority": False,
        }
    try:
        household_policy_tournament = household_policy_tournament_status(root)
    except (OSError, TypeError, ValueError) as error:
        household_policy_tournament = {
            "schema": "jaggedthoughts-household-policy-tournament-status-v1",
            "error": str(error), "run_count": 0, "settled_count": 0,
            "pending_count": 0, "capital_authority": False,
        }
    try:
        operator_household_paper_policy = operator_paper_policy_status(
            root,
            owner=str(config.get("owner") or "operator-paper-book"),
            store_path=store_path,
        )
    except (OSError, TypeError, ValueError) as error:
        operator_household_paper_policy = {
            "schema": "jaggedthoughts-operator-paper-policy-status-v1",
            "status": "unavailable", "error": str(error),
            "paper_policy_authority": False, "capital_authority": False,
            "brokerage_authority": False, "order_routing_allowed": False,
        }
    try:
        rank_program_tournament = rank_program_tournament_status(root)
    except (OSError, TypeError, ValueError) as error:
        rank_program_tournament = {
            "schema": "jaggedthoughts-rank-program-tournament-status-v1",
            "error": str(error), "run_count": 0, "settled_count": 0,
            "pending_count": 0, "capital_authority": False,
        }
    fund_paper_proposals = _read_json(
        root / "paper_proposals" / "funds" / "latest.json"
    ) or {
        "schema": "jaggedthoughts-public-fund-paper-proposal-audit-v1",
        "qualified_candidate_count": 0, "proposal_count": 0,
        "eligible_count": 0, "blocked_count": 0, "rows": [],
        "status": "not_compiled", "capital_authority": False,
    }
    try:
        allocation_readiness = _read_json(root / "allocation" / "latest.json")
        current_book_sha = str((_read_json(root / "opportunity_books" / "latest.json") or {}).get("book_sha256") or "")
        current_fund_audit_sha = fund_paper_proposals.get("audit_sha256")
        if (
            not allocation_readiness
            or allocation_readiness.get("opportunity_book_sha256") != current_book_sha
            or allocation_readiness.get("fund_proposal_audit_sha256") != current_fund_audit_sha
        ):
            allocation_readiness = compile_workspace_allocation_readiness(root)
    except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
        allocation_readiness = {
            "schema": "jaggedthoughts-allocation-readiness-v1",
            "counts": {}, "candidates": [], "status": "unavailable",
            "error": str(error), "capital_authority": False,
        }
    try:
        sleeve_implementation_frontier = compile_workspace_sleeve_implementation_frontier(root)
    except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
        sleeve_implementation_frontier = {
            "schema": "jaggedthoughts-sleeve-implementation-frontier-v1",
            "policy_consumed": False, "sleeves": [], "status": "unavailable",
            "error": str(error), "capital_authority": False,
            "brokerage_authority": False,
        }
    try:
        fund_sleeve_comparison = compile_workspace_fund_sleeve_comparison(
            root, sleeve_implementation=sleeve_implementation_frontier,
        )
    except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
        fund_sleeve_comparison = {
            "schema": "jaggedthoughts-fund-sleeve-comparison-v1",
            "status": "unavailable", "sleeves": [], "error": str(error),
            "allocation_selected": False, "capital_authority": False,
            "brokerage_authority": False,
        }
    try:
        fund_implementation_review = compile_workspace_fund_implementation_review(
            root, comparison=fund_sleeve_comparison,
        )
        sleeve_implementation_frontier = compile_workspace_sleeve_implementation_frontier(root)
        fund_sleeve_comparison = compile_workspace_fund_sleeve_comparison(
            root, sleeve_implementation=sleeve_implementation_frontier,
        )
    except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
        fund_implementation_review = {
            "schema": "jaggedthoughts-workspace-fund-implementation-review-v1",
            "status": "unavailable", "request_count": 0, "evidence_count": 0,
            "proposal_count": 0, "decision_count": 0, "error": str(error),
            "automatic_activation": False, "capital_authority": False,
            "brokerage_authority": False,
        }
    try:
        instrument_portfolio_admissions = _current_instrument_portfolio_admissions(root)
    except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
        instrument_portfolio_admissions = {
            "schema": "jaggedthoughts-workspace-instrument-portfolio-admissions-v1",
            "status": "unavailable", "watch_count": 0, "admitted_count": 0,
            "blocked_count": 0, "error_count": 1, "admissions": [],
            "errors": [{"message": str(error)}], "capital_authority": False,
            "brokerage_authority": False, "order_routing_allowed": False,
        }
    if instrument_portfolio_admissions.get("workspace_admissions_sha256"):
        try:
            allocation_readiness = compile_workspace_allocation_readiness(
                root,
                instrument_portfolio_admissions=instrument_portfolio_admissions,
            )
        except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
            allocation_readiness = {
                "schema": "jaggedthoughts-allocation-readiness-v1",
                "counts": {}, "candidates": [], "status": "unavailable",
                "error": str(error), "capital_authority": False,
            }
    household_default_allocation = None
    household_mandate_frontier = None
    household_basis = None
    household_default_inputs = None
    if isinstance(household_goal_surface, Mapping) and (
        household_goal_surface.get("available") is not False
    ):
        try:
            household_basis = household_basis_snapshot
            if not household_basis:
                raise ValueError("current public household capital-market basis is unavailable")
            household_default_inputs = default_household_allocation_scenario_inputs(
                household_goal_surface,
                household_basis.get("capital_market_basis") or {},
            )
            opportunity_book = _read_json(root / "opportunity_books" / "latest.json")
            implementation_inputs = {}
            if (
                instrument_portfolio_admissions.get("workspace_admissions_sha256")
                and opportunity_book and opportunity_book.get("book_sha256")
                and portfolio_policy.get("schema") == PORTFOLIO_POLICY_STATUS_SCHEMA
            ):
                implementation_inputs = {
                    "instrument_admissions": instrument_portfolio_admissions,
                    "opportunity_book": opportunity_book,
                    "portfolio_policy": portfolio_policy,
                }
            scenario = compile_household_allocation_scenario(
                household_default_inputs,
                goal_surface=household_goal_surface,
                public_basis_acquisition=household_basis,
                **implementation_inputs,
            )
            default_body = {
                "schema": "jaggedthoughts-household-default-allocation-projection-v1",
                "status": "assumption_labeled_default_ready",
                "input_policy": "shared_backend_and_workbench_defaults",
                "scenario": scenario,
                "policy_authority": False,
                "capital_authority": False,
            }
            household_default_allocation = {
                **default_body,
                "projection_sha256": stable_sha256(default_body),
            }
        except (KeyError, OSError, TypeError, ValueError) as error:
            household_default_allocation = {
                "schema": "jaggedthoughts-household-default-allocation-projection-v1",
                "status": "unavailable", "error": str(error),
                "policy_authority": False, "capital_authority": False,
            }
    if household_default_inputs and household_basis:
        try:
            household_mandate_frontier = _cached_household_mandate_frontier(
                root,
                base_inputs=household_default_inputs,
                goal_surface=household_goal_surface,
                public_basis_acquisition=household_basis,
            )
        except (KeyError, OSError, TypeError, ValueError) as error:
            household_mandate_frontier = {
                "schema": "jaggedthoughts-household-mandate-frontier-v1",
                "status": "unavailable", "error": str(error),
                "policy_authority": False, "capital_authority": False,
                "brokerage_authority": False, "order_routing_allowed": False,
            }
    source_manifest = None
    manifest_path = root / str(config.get("source_manifest") or "sources.yaml")
    try:
        source_manifest = load_source_manifest(manifest_path)
        fund_lookthrough_acquisition_plan = (
            compile_workspace_fund_lookthrough_acquisition_plan(
                root,
                tournament_input=fund_sleeve_comparison[
                    "portfolio_policy_tournament_input"
                ],
                source_manifest=source_manifest,
            )
        )
    except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
        fund_lookthrough_acquisition_plan = {
            "schema": "jaggedthoughts-fund-lookthrough-acquisition-plan-v1",
            "status": "unavailable", "selected": [], "error": str(error),
            "capital_authority": False,
        }
    try:
        fund_lookthrough_acquisition = fund_lookthrough_acquisition_status(
            root, plan=fund_lookthrough_acquisition_plan,
        )
    except (FileNotFoundError, KeyError, OSError, TypeError, ValueError, yaml.YAMLError) as error:
        fund_lookthrough_acquisition = {
            "schema": FUND_LOOKTHROUGH_AUTONOMY_SCHEMA,
            "status": "unavailable", "error": str(error),
            "next_action": "refresh_fund_comparison_inputs",
            "capital_authority": False,
        }
    try:
        household_paper_policy_path = compile_workspace_household_paper_policy_path(
            root,
            sleeve_implementation=sleeve_implementation_frontier,
            fund_sleeve_comparison=fund_sleeve_comparison,
            portfolio_policy=portfolio_policy,
            planning_scenario=(household_default_allocation or {}).get("scenario"),
            portfolio_assembly=portfolio,
            state_pricing=state_pricing,
        )
    except (FileNotFoundError, KeyError, OSError, TypeError, ValueError, yaml.YAMLError) as error:
        household_paper_policy_path = {
            "schema": "jaggedthoughts-household-paper-policy-path-v1",
            "status": "unavailable", "error": str(error),
            "capital_authority": False, "brokerage_authority": False,
        }
    try:
        capital_cycle = capital_cycle_status(
            root,
            policy_path=root / str(config.get("capital_cycle_policy") or "capital_cycle.yaml"),
            owner=str(config.get("owner") or "operator-paper-book"),
            store_path=store_path,
        )
    except (FileNotFoundError, OSError, TypeError, ValueError, yaml.YAMLError) as error:
        capital_cycle = {
            "schema": "jaggedthoughts-capital-cycle-status-v1",
            "enabled": False,
            "configured": False,
            "due": False,
            "error": str(error),
            "capital_authority": False,
        }
    try:
        universe_breadth = audit_workspace_breadth(root)
    except (FileNotFoundError, KeyError, OSError, TypeError, ValueError, yaml.YAMLError) as error:
        universe_breadth = {
            "schema": "jaggedthoughts-universe-breadth-audit-v1",
            "status": "unavailable", "error": str(error), "capital_authority": False,
        }
    equity_paper_proposals = _read_json(
        root / "paper_proposals" / "equities" / "latest.json"
    ) or {
        "schema": "jaggedthoughts-public-equity-paper-proposal-audit-v1",
        "qualified_candidate_count": 0, "proposal_count": 0,
        "eligible_count": 0, "blocked_count": 0, "rows": [],
        "status": "not_compiled", "capital_authority": False,
    }
    if market_state.get("enabled"):
        market_state = {
            **market_state,
            "schedule": dict(capital_cycle.get("market_state_due") or {}),
        }
    research_requests = _research_request_rows(
        root, decisions, settlement_scorecards,
    )
    coverage_by_candidate = {
        str(row.get("candidate_leaf") or ""): row
        for row in research_memory.get("research_coverage") or ()
        if isinstance(row, Mapping) and row.get("candidate_leaf")
    }
    for request in research_requests:
        coverage = coverage_by_candidate.get(str(request.get("candidate_leaf") or ""))
        if not coverage or request.get("lifecycle_stage") != "evidence_ready":
            continue
        if coverage.get("covered"):
            request["lifecycle_stage"] = "covered_by_prior_dossier"
            request["research_coverage"] = coverage
            request["learning_status"] = "prior_evidence_reused_under_monitor"
        else:
            request["research_coverage"] = coverage
            request["learning_status"] = f"research_coverage_{coverage.get('status') or 'not_current'}"
    research_dossiers: list[dict[str, Any]] = []
    for request in research_requests:
        relative = str(request.get("dossier_path") or "")
        dossier = _read_json(root / relative) if relative else None
        if dossier:
            research_dossiers.append({
                **dossier, "dossier_path": relative,
                "entity_kind": request.get("entity_kind"),
                "screen_status": request.get("screen_status"),
                "lifecycle_stage": request.get("lifecycle_stage"),
            })
    strategy_event_learning_units = _compile_strategy_event_learning_units(
        root, shadow=strategy_path_shadow,
        acquisition=strategy_event_research_acquisition,
        dossiers=research_dossiers, frontiers=company_strategy_frontiers,
    )
    research_learning = compile_research_learning(
        research_requests=research_requests,
        queue_jobs=research_job_queue.get("jobs") or (),
    )
    research_question_policy_outcomes = _read_json(
        root / "institutional_learning" / "research_question_policy_outcomes"
        / "latest.json"
    ) or {
        "schema": "jaggedthoughts-research-question-policy-outcome-cycle-v1",
        "request_count": 0, "eligible_count": 0, "action_count": 0,
        "abstention_count": 0, "settled_count": 0, "due_censored_count": 0,
        "rows": [], "capital_authority": False,
    }
    path_action = max(
        (
            row for row in market_flow_experiments
            if row.get("schema") == "jaggedthoughts-company-state-path-action-run-v1"
        ),
        key=lambda row: (str(row.get("opened_at") or ""), str(row.get("run_sha256") or "")),
        default=None,
    )
    institutional_edge_map = compile_institutional_edge_map(
        research_learning=research_learning,
        strategy_move_learning=strategy_move_learning,
        institutional_learning=institutional_learning,
        closed_book=closed_book,
        portfolio_policy=portfolio_policy,
        path_action=path_action,
        historical_strategy_bulk_learning=historical_strategy_bulk_learning,
        historical_strategy_bulk_panel=historical_strategy_bulk_panel_readiness,
        historical_strategy_bulk_effects=historical_strategy_bulk_effects,
        historical_strategy_outcome_robustness=historical_strategy_outcome_robustness,
        historical_strategy_law_search=historical_strategy_law_search,
        historical_strategy_security_walk_forward=(
            historical_strategy_security_walk_forward
        ),
        strategy_security_representation_learning=(
            historical_strategy_representation_learning
        ),
        research_budget_tournament=research_budget_tournament,
        strategy_program_learning=strategy_program_learning,
        strategy_program_transfer=strategy_program_transfer,
        strategy_program_control_acquisition=strategy_program_control_acquisition,
        strategy_program_comparison=strategy_program_comparison,
    )
    learning_credit_assignment = compile_learning_credit_assignment(
        research_learning=research_learning,
        closed_book=closed_book,
        institutional_learning=institutional_learning,
        fund_sleeve_comparison=fund_sleeve_comparison,
        portfolio_policy=portfolio_policy,
        household_policy_tournament=household_policy_tournament,
        activation_matrix_policy_learning=activation_matrix_policy_learning,
        underwriting_method_policy=underwriting_method_policy,
    )
    learning_experiment_design = compile_learning_experiment_design(
        learning_credit_assignment=learning_credit_assignment,
        research_learning=research_learning,
        strategy_alpha_tournament=strategy_alpha_tournament,
        institutional_learning=institutional_learning,
        fund_sleeve_comparison=fund_sleeve_comparison,
        portfolio_policy=portfolio_policy,
        household_policy_tournament=household_policy_tournament,
    )
    try:
        discovery = workspace_discovery_status(root)
    except (FileNotFoundError, OSError, TypeError, ValueError, yaml.YAMLError) as error:
        discovery = {
            "schema": "jaggedthoughts-discovery-status-v1", "configured": False,
            "error": str(error), "activation_points": activation_map(),
            "latest_run": None, "schedule": {"enabled": False, "due": False},
        }
    discovery_research_handoff = _read_json(
        root / "state" / "discovery_research_handoff.json"
    ) or {}
    learning_experiment_activation = compile_learning_experiment_activation(
        learning_experiment_design=learning_experiment_design,
        research_learning=research_learning,
        research_requests=research_requests,
        subscription_research=subscription_research,
        discovery=discovery,
        strategy_alpha_tournament=strategy_alpha_tournament,
        capital_cycle=capital_cycle,
        household_policy_tournament=household_policy_tournament,
    )
    broad_fund_acquisition = _broad_fund_acquisition_status(
        root,
        next_due_at=(discovery.get("schedule") or {}).get("next_due_at"),
    )
    try:
        search_trial_census = compile_workspace_search_trial_census(root)
    except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
        search_trial_census = {
            "schema": "jaggedthoughts-search-trial-census-v1",
            "census_complete": False, "status": "unavailable", "error": str(error),
            "alpha_claim_eligible": False, "capital_authority": False,
        }
    try:
        schedule = dict(discovery.get("schedule") or {})
        schedule["starter"] = (
            (subscription_research.get("persistence") or {}).get("starter")
        )
        periodic = (
            ((discovery.get("service") or {}).get("periodic_activation") or {})
            if isinstance(discovery.get("service"), Mapping) else {}
        )
        activation = periodic.get("next_activation") or {}
        if activation.get("at"):
            schedule.update({
                "enabled": True,
                "next_due_at": activation.get("at"),
                "next_transition": activation.get("kind"),
                "work_id": activation.get("work_id"),
                "job_kind": activation.get("job_kind"),
                "status": periodic.get("status"),
                "blocked_reasons": list(
                    (periodic.get("blocked_activation") or {}).get("reasons") or ()
                ),
            })
        active_research = _active_research_transition(subscription_research)
        if active_research:
            schedule.update({
                **active_research,
                "next_due_at": active_research.get("not_before"),
                "next_transition": active_research["transition"],
            })
        investor_action_brief = compile_investor_action_brief(
            breadth_audit=universe_breadth,
            discovery_run=_read_json(root / "discovery" / "latest.json") or {},
            opportunity_book=_read_json(root / "opportunity_books" / "latest.json") or {},
            underwriting_index=underwriting_full,
            allocation_readiness=allocation_readiness,
            equity_proposal_audit=equity_paper_proposals,
            fund_proposal_audit=fund_paper_proposals,
            paper_watch_decisions=paper_watch_decisions,
            research_queue=research_job_queue,
            research_service=schedule,
            sleeve_implementation_frontier=sleeve_implementation_frontier,
            fund_sleeve_comparison=fund_sleeve_comparison,
            portfolio_policy=portfolio_policy,
            planning_scenario=(household_default_allocation or {}).get("scenario"),
            household_policy_tournament=household_policy_tournament,
        )
    except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
        investor_action_brief = {
            "schema": "jaggedthoughts-investor-action-brief-v2",
            "status": "unavailable", "error": str(error),
            "investable_now": {"paper": [], "funded": []},
            "review_now": [], "active_paper_watches": [],
            "research_now": [], "capital_authority": False,
        }
    _atomic_json(root / "action_briefs" / "latest.json", investor_action_brief)
    requirements: list[dict[str, Any]] = []
    if source_manifest is not None:
        requirements = source_requirements(source_manifest)
    elif manifest_path.is_file():
        try:
            requirements = source_requirements(load_source_manifest(manifest_path))
        except (OSError, ValueError, yaml.YAMLError):
            pass
    if discovery.get("schedule", {}).get("due"):
        next_action = "Run the due public-market discovery cycle and inspect its ranked evidence requests."
    elif capital_cycle.get("due"):
        next_action = "Run the due capital cycle: settle forecasts, open due blocks, and refresh the opportunity book."
    elif not source_run:
        next_action = "Refresh public sources and inspect their availability modes."
    elif required_failures:
        next_action = "Repair required source configuration before compiling operator profiles."
    elif any(row.get("lifecycle_stage") == "evidence_ready" for row in research_requests):
        next_action = "Use the highest-priority evidence-ready request to produce a candidate-leaf-bound research dossier."
    elif any(row.get("review_state") == "operator_review"
             for row in investor_action_brief.get("review_now") or ()):
        next_action = "Review a current evidence-bound proposal for a zero-weight paper watch."
    elif operator_drafts:
        next_action = "Review the source-bound draft, edit its thesis and assumptions, then activate it for paper tracking."
    elif not operator_decisions:
        next_action = "Create an operator profile bound to the public-source receipts; the fixture is only a workflow check."
    elif pending:
        next_action = "Review pending paper decisions and settle those whose horizon or falsifier has matured."
    else:
        next_action = "Refresh sources and compile the next evidence epoch."
    readiness = {
        "source_run_available": source_run is not None,
        "public_sources_consumed": bool(source_receipts),
        "required_sources_ok": not required_failures,
        "operator_decision_count": len(operator_decisions),
        "paper_watch_count": len(paper_watch_decisions),
        "paper_watch_history_count": len(paper_watch_history),
        "operator_draft_count": len(operator_drafts),
        "reference_fixture_count": sum(row["data_class"] == "reference_fixture" for row in decisions),
        "portfolio_available": portfolio is not None,
        "pending_settlement_count": len(pending),
        "tournament_count": len(tournament_results),
        "watchlist_count": len(watchlists),
        "fund_candidate_count": sum(int(row.get("candidate_count") or 0) for row in watchlists),
        "qualified_fund_candidate_count": sum(int(row.get("qualified_count") or 0) for row in watchlists),
        "company_quality_report_count": len(company_quality),
        "company_strategy_frontier_count": len(company_strategy_frontiers),
        "discovery_candidate_count": int((discovery.get("latest_run") or {}).get("candidate_count") or 0),
        "qualified_discovery_candidate_count": int((discovery.get("latest_run") or {}).get("qualified_count") or 0),
        "discovery_due": bool((discovery.get("schedule") or {}).get("due")),
        "market_flow_experiment_count": len(market_flow_experiments),
        "research_project_count": len(research_projects),
        "execution_market_run_count": int(adaptive_execution.get("run_count") or 0),
        "verified_agent_execution_count": int(
            adaptive_execution.get("verified_agent_receipt_count") or 0
        ),
        "closed_book_run_count": int(closed_book.get("run_count") or 0),
        "closed_book_pending_count": int(closed_book.get("pending_count") or 0),
        "closed_book_settled_count": int(closed_book.get("settled_count") or 0),
        "market_state_run_count": int(market_state.get("run_count") or 0),
        "market_state_pending_count": int(market_state.get("pending_count") or 0),
        "market_state_settled_count": int(market_state.get("settled_count") or 0),
        "investment_law_candidate_count": int(institutional_learning.get("candidate_count") or 0),
        "phenotype_episode_count": int(institutional_learning.get("phenotype_episode_count") or 0),
        "investment_law_transfer_candidate_count": int(
            institutional_learning.get("transfer_candidate_count") or 0
        ),
        "strategy_move_count": int(strategy_move_learning.get("move_count") or 0),
        "measurable_strategy_move_count": int(
            strategy_move_learning.get("measurable_move_count") or 0
        ),
        "strategy_move_outcome_episode_count": int(
            strategy_move_learning.get("outcome_episode_count") or 0
        ),
        "strategy_transfer_card_count": int(strategy_transfer.get("card_count") or 0),
        "strategy_transfer_counterexample_count": int(
            strategy_transfer.get("counterexample_count") or 0
        ),
        "strategy_outcome_due_count": int(
            strategy_outcome_acquisition.get("due_contract_count") or 0
        ),
        "strategy_event_activation_count": int(
            strategy_event_activation.get("activation_count") or 0
        ),
        "underwriting_rank_eligible_count": int(
            underwriting_index.get("ranking_eligible_count") or 0
        ),
        "state_price_proposal_count": int(
            (state_pricing.get("proposal_audit") or {}).get("valid_proposal_count") or 0
        ),
        "modeled_payoff_grid_count": int(
            (state_pricing.get("modeled_grid_audit") or {}).get("eligible_grid_count") or 0
        ),
        "portfolio_policy_run_count": int(portfolio_policy.get("run_count") or 0),
        "portfolio_policy_settled_count": int(portfolio_policy.get("settled_count") or 0),
        "allocation_ready_count": int(
            (allocation_readiness.get("counts") or {}).get("portfolio_candidate_count") or 0
        ),
        "instrument_portfolio_admitted_count": int(
            instrument_portfolio_admissions.get("admitted_count") or 0
        ),
        "capital_cycle_due": bool(capital_cycle.get("due")),
        "capital_cycle_qualified_count": int(
            ((capital_cycle.get("latest_book") or {}).get("qualified_count") or 0)
        ),
        "capital_cycle_research_count": int(
            ((capital_cycle.get("latest_book") or {}).get("research_count") or 0)
        ),
        "market_catalog_count": int((catalog or {}).get("security_count") or 0),
        "market_scout_candidate_count": int(((latest_scout or {}).get("population") or {}).get("returned_count") or 0),
        "scheduled_market_scout_count": int((scheduled_scout_cycle or {}).get("intent_count") or 0),
        "enrichment_selected_count": int((latest_enrichment_cycle or {}).get("selected_count") or 0),
        "enrichment_evidence_ready_count": int((latest_enrichment_execution or {}).get("evidence_ready_count") or 0),
        "agent_research_request_count": len(research_requests),
        "subscription_research_queued_count": int(
            ((subscription_research.get("queue") or {}).get("by_status") or {}).get("queued", 0)
        ),
        "research_dossier_count": int(research_learning["counts"]["dossiers"]),
        "research_coverage_count": int(research_memory.get("research_coverage_count") or 0),
        "mechanism_research_result_count": int(
            research_memory.get("mechanism_research_result_count") or 0
        ),
        "market_flow_successor_result_count": int(
            research_memory.get("market_flow_successor_result_count") or 0
        ),
        "cross_entity_strategy_phenotype_count": int(
            research_memory.get("cross_entity_strategy_phenotype_count") or 0
        ),
        "fund_review_count": sum(
            row.get("entity_kind") == "public_fund" for row in research_dossiers
        ),
        "research_settled_pair_count": int(
            research_learning["counts"]["settled_score_pairs"]
        ),
        "activation_matrix_policy_pair_count": int(
            activation_matrix_policy_learning.get("complete_pair_count") or 0
        ),
        "strategy_walk_forward_fold_count": int(
            historical_strategy_walk_forward.get("fold_count") or 0
        ),
        "strategy_security_walk_forward_fold_count": int(
            historical_strategy_security_walk_forward.get("fold_count") or 0
        ),
        "strategy_security_independent_block_count": int(
            historical_strategy_security_walk_forward.get("independent_block_count")
            if historical_strategy_security_walk_forward.get("independent_block_count") is not None
            else historical_strategy_security_walk_forward.get("fold_count") or 0
        ),
        "strategy_representation_conjecture_count": int(
            historical_strategy_representation_learning.get("conjecture_count") or 0
        ),
        "funnel_transition_count": len(funnel_transition_receipts),
        "golden_store_ok": bool(verification.get("ok")),
        "registered_metric_count": int(metric_universe.get("metric_count") or 0),
        "observed_registered_metric_count": int(metric_universe.get("observed_registered_count") or 0),
        "capital_authority": False,
    }
    body: dict[str, Any] = {
        "schema": READ_MODEL_SCHEMA,
        "ok": bool(verification.get("ok")),
        "initialized": True,
        "workspace_path": str(root),
        "workspace_preview_root": _workspace_preview_root(root),
        "workspace_name": str(config.get("name") or "JaggedThoughts Capital Workbench"),
        "owner": str(config.get("owner") or ""),
        "generated_at": _utc_now(),
        "capital_authority": False,
        "readiness": readiness,
        "next_action": next_action,
        "source_run": _ui_source_run(source_run),
        "source_statuses": source_statuses,
        "source_receipts": source_receipts,
        "point_in_time_evidence": point_in_time_evidence,
        "sealed_walk_forward_readiness": sealed_walk_forward_readiness,
        "source_requirements": requirements,
        "latest_observations": latest_observations[:500],
        "household_goal_surface": household_goal_surface,
        "household_default_allocation": household_default_allocation,
        "household_mandate_frontier": household_mandate_frontier,
        "metric_universe": metric_universe,
        "broad_equity_potential": broad_equity_potential,
        "signal_receipts": list((source_run or {}).get("signal_receipts") or [])[-100:],
        "decisions": decisions,
        "operator_drafts": operator_drafts,
        "pending_decisions": pending,
        "portfolio": portfolio,
        "watchlists": watchlists,
        "company_quality": [_ui_quality_report(row) for row in company_quality],
        "company_strategy_frontiers": [
            _ui_strategy_frontier(row) for row in company_strategy_frontiers
        ],
        "strategy_investment_path": _ui_strategy_investment_path(
            company_strategy_frontiers, strategy_move_learning, strategy_valuation_bridge,
        ),
        "discovery": _ui_discovery_status(discovery),
        "discovery_research_handoff": discovery_research_handoff,
        "market_flow_experiments": market_flow_experiments,
        "research_projects": research_projects,
        "adaptive_execution": adaptive_execution,
        "closed_book": closed_book,
        "underwriting_method_policy": underwriting_method_policy,
        "market_state": market_state,
        "institutional_learning": institutional_learning,
        "historical_strategy_event_replay": historical_strategy_event_replay,
        "historical_strategy_walk_forward": historical_strategy_walk_forward,
        "historical_strategy_security_walk_forward": (
            historical_strategy_security_walk_forward
        ),
        "historical_strategy_representation_learning": (
            historical_strategy_representation_learning
        ),
        "historical_strategy_control_design": historical_strategy_control_design,
        "historical_strategy_control_acquisition": (
            historical_strategy_control_acquisition
        ),
        "historical_strategy_bulk_corpus": historical_strategy_bulk_corpus,
        "historical_strategy_bulk_learning": historical_strategy_bulk_learning,
        "historical_strategy_bulk_outcomes": historical_strategy_bulk_outcomes,
        "historical_strategy_bulk_panel_readiness": (
            historical_strategy_bulk_panel_projection
        ),
        "historical_strategy_bulk_effects": historical_strategy_bulk_effects_projection,
        "historical_strategy_outcome_robustness": historical_strategy_outcome_robustness,
        "historical_strategy_law_search": historical_strategy_law_search,
        "historical_strategy_law_trial": historical_strategy_law_trial,
        "strategy_path_shadow": strategy_path_shadow,
        "strategy_event_research_acquisition": strategy_event_research_acquisition,
        "strategy_event_learning_units": strategy_event_learning_units,
        "strategy_business_clock": strategy_business_clock,
        "strategy_state_experiment": strategy_state_experiment,
        "strategy_state_control_acquisition": strategy_state_control_acquisition,
        "strategy_state_successor": strategy_state_successor,
        "strategy_state_transition_join": strategy_state_transition_join,
        "max_caliber_recovery": max_caliber_recovery,
        "strategy_path_lagrangian": strategy_path_lagrangian,
        "strategy_program_representation": strategy_program_representation,
        "max_caliber_readiness": max_caliber_readiness,
        "institutional_edge_map": institutional_edge_map,
        "learning_credit_assignment": learning_credit_assignment,
        "learning_experiment_design": learning_experiment_design,
        "learning_experiment_activation": learning_experiment_activation,
        "learning_schedule": learning_schedule,
        "research_budget_tournament": research_budget_tournament,
        "activation_matrix_policy_learning": activation_matrix_policy_learning,
        "strategy_move_learning": strategy_move_learning,
        "strategy_program_learning": strategy_program_learning,
        "strategy_program_transfer": strategy_program_transfer,
        "strategy_program_control_acquisition": strategy_program_control_acquisition,
        "strategy_program_comparison": strategy_program_comparison,
        "strategy_cohort_research": strategy_cohort_research,
        "strategy_active_comparator": strategy_active_comparator,
        "strategy_law_induction": strategy_law_induction,
        "strategy_valuation_bridge": strategy_valuation_bridge,
        "strategy_event_activation": strategy_event_activation,
        "strategy_transfer_acquisition": strategy_transfer_acquisition,
        "strategy_control_runtime": strategy_control_runtime,
        "strategy_transfer": strategy_transfer,
        "strategy_alpha_tournament": strategy_alpha_tournament,
        "strategy_dual_outcomes": strategy_dual_outcomes,
        "strategy_outcome_acquisition": strategy_outcome_acquisition,
        "strategy_program_outcome_acquisition": strategy_program_outcome_acquisition,
        "search_trial_census": search_trial_census,
        "underwriting_index": underwriting_index,
        "state_pricing": state_pricing,
        "portfolio_policy": portfolio_policy,
        "household_policy_tournament": household_policy_tournament,
        "operator_household_paper_policy": operator_household_paper_policy,
        "rank_program_tournament": rank_program_tournament,
        "allocation_readiness": allocation_readiness,
        "sleeve_implementation_frontier": sleeve_implementation_frontier,
        "fund_sleeve_comparison": fund_sleeve_comparison,
        "fund_implementation_review": fund_implementation_review,
        "instrument_portfolio_admissions": instrument_portfolio_admissions,
        "fund_lookthrough_acquisition_plan": fund_lookthrough_acquisition_plan,
        "fund_lookthrough_acquisition": fund_lookthrough_acquisition,
        "household_paper_policy_path": household_paper_policy_path,
        "universe_breadth": universe_breadth,
        "equity_paper_proposals": equity_paper_proposals,
        "fund_paper_proposals": fund_paper_proposals,
        "paper_watch_decisions": paper_watch_decisions,
        "paper_watch_history_count": len(paper_watch_history),
        "investor_action_brief": investor_action_brief,
        "capital_cycle": _ui_capital_cycle(capital_cycle),
        "market_catalog": catalog_summary,
        "latest_market_scout": latest_scout,
        "scheduled_market_scout_cycle": scheduled_scout_cycle,
        "latest_enrichment_cycle": latest_enrichment_cycle,
        "latest_enrichment_execution": latest_enrichment_execution,
        "broad_fund_acquisition": broad_fund_acquisition,
        "research_job_queue": research_job_queue,
        "subscription_research": _ui_subscription_research(subscription_research),
        "live_automatic_transition": _active_research_transition(subscription_research),
        "research_requests": [_ui_research_request(row) for row in research_requests],
        "research_dossiers": [_ui_research_dossier(row) for row in research_dossiers],
        "research_learning": research_learning,
        "research_question_policy_outcomes": research_question_policy_outcomes,
        "research_memory": research_memory,
        "funnel_transition_receipts": funnel_transition_receipts[-100:],
        "funnel_transition_counts": dict(sorted(Counter(
            str(row.get("to_state") or "unknown") for row in funnel_transition_receipts
        ).items())),
        "opportunity_funnel": funnel_surface("observed", context={
            "source_epoch": (source_run or {}).get("as_of"),
            "screened_fund_candidates": sum(int(row.get("candidate_count") or 0) for row in watchlists),
            "operator_drafts": len(operator_drafts),
            "active_paper_decisions": len(operator_decisions),
            "pending_settlements": len(pending),
            "company_quality_screens": len(company_quality),
            "transition_receipts": len(funnel_transition_receipts),
        }),
        "tournaments": tournament_results,
        "golden_store": verification,
        "latest_build": build,
        "paths": {
            "config": "workspace.yaml", "source_manifest": str(config.get("source_manifest") or "sources.yaml"),
            "observations": "data/observations.csv", "source_run": "data/latest_source_run.json",
            "golden_store": str(config.get("golden_store") or "state/golden_store.sqlite3"),
            "read_model": "state/read_model.json",
            "company_quality": "quality/",
            "company_strategy_frontiers": "strategy_frontiers/results/",
            "market_flow_experiments": "experiments/results/",
            "execution_market_runs": "execution_market/runs/",
            "closed_book_runs": "closed_book/runs/",
            "closed_book_settlements": "closed_book/settlements/",
            "market_state_snapshots": "market_state/snapshots/",
            "market_state_runs": "market_state/runs/",
            "market_state_settlements": "market_state/settlements/",
            "portfolio_policy_reviews": "portfolio_policy/reviews/",
            "rank_program_tournament_runs": "rank_program_tournament/runs/",
            "investment_law_catalog": str(
                config.get("investment_law_catalog")
                or "institutional_learning/laws.yaml"
            ),
            "institutional_learning_latest": "institutional_learning/latest.json",
            "historical_strategy_event_replay_latest": (
                "institutional_learning/historical_strategy_event_replay/latest.json"
                if historical_strategy_event_replay.get("replay_sha256") else None
            ),
            "historical_strategy_walk_forward_latest": (
                "institutional_learning/historical_strategy_event_replay/walk-forward.json"
                if historical_strategy_walk_forward.get("tournament_sha256") else None
            ),
            "historical_strategy_security_walk_forward_latest": (
                "institutional_learning/historical_strategy_event_replay/security-walk-forward.json"
                if historical_strategy_security_walk_forward.get("tournament_sha256") else None
            ),
            "historical_strategy_representation_learning_latest": (
                "institutional_learning/historical_strategy_event_replay/representation-learning.json"
                if historical_strategy_representation_learning.get("learning_sha256") else None
            ),
            "historical_strategy_control_design_latest": (
                "institutional_learning/historical_strategy_event_replay/control-design-latest.json"
                if historical_strategy_control_design.get("control_design_sha256") else None
            ),
            "historical_strategy_control_acquisition_latest": (
                "institutional_learning/historical_strategy_event_replay/control-acquisition-latest.json"
                if historical_strategy_control_acquisition.get("acquisition_sha256") else None
            ),
            "historical_strategy_bulk_corpus_latest": (
                "institutional_learning/historical_strategy_bulk_corpus/latest.json"
                if historical_strategy_bulk_corpus.get("corpus_sha256") else None
            ),
            "historical_strategy_bulk_learning_latest": (
                "institutional_learning/historical_strategy_bulk_learning/latest.json"
                if historical_strategy_bulk_learning.get("learning_queue_sha256") else None
            ),
            "historical_strategy_bulk_outcomes_latest": (
                "institutional_learning/historical_strategy_bulk_outcomes/latest.json"
                if historical_strategy_bulk_outcomes.get("outcomes_sha256") else None
            ),
            "historical_strategy_bulk_panel_readiness_latest": (
                "institutional_learning/historical_strategy_bulk_outcomes/panel-readiness.json"
                if historical_strategy_bulk_panel_readiness.get("readiness_sha256") else None
            ),
            "historical_strategy_bulk_effects_latest": (
                "institutional_learning/historical_strategy_bulk_outcomes/effect-diagnostics.json"
                if historical_strategy_bulk_effects.get("diagnostics_sha256") else None
            ),
            "historical_strategy_outcome_robustness_latest": (
                "institutional_learning/historical_strategy_bulk_outcomes/outcome-robustness.json"
                if historical_strategy_outcome_robustness.get("robustness_sha256") else None
            ),
            "historical_strategy_law_search_latest": (
                "institutional_learning/historical_strategy_bulk_outcomes/law-search.json"
                if historical_strategy_law_search.get("law_search_sha256") else None
            ),
            "historical_strategy_law_trial_latest": (
                "institutional_learning/historical_strategy_bulk_outcomes/law-trials/latest.json"
                if historical_strategy_law_trial.get("epoch_sha256") else
                "institutional_learning/historical_strategy_bulk_outcomes/law-trials/current.json"
                if historical_strategy_law_trial.get("trial_sha256") else None
            ),
            "strategy_path_shadow_latest": (
                "institutional_learning/strategy_path_shadow/latest.json"
                if strategy_path_shadow.get("shadow_sha256") else None
            ),
            "strategy_event_research_acquisition_latest": (
                "institutional_learning/strategy_path_shadow/"
                "event-research-acquisition-latest.json"
                if strategy_event_research_acquisition.get("acquisition_sha256") else None
            ),
            "strategy_business_clock_latest": (
                "institutional_learning/strategy_business_clock/latest.json"
                if strategy_business_clock.get("clock_sha256") else None
            ),
            "strategy_state_experiment_latest": (
                "experiments/results/strategy-state-experiment.json"
                if strategy_state_experiment.get("experiment_sha256") else None
            ),
            "strategy_state_control_acquisition_latest": (
                "experiments/results/strategy-state-control-acquisition.json"
                if strategy_state_control_acquisition.get("acquisition_sha256") else None
            ),
            "strategy_state_successor_latest": (
                "experiments/results/strategy-state-successor-readiness.json"
                if strategy_state_successor.get("readiness_sha256") else None
            ),
            "strategy_state_transition_join_latest": (
                "experiments/results/strategy-state-transition-join.json"
                if strategy_state_transition_join.get("join_sha256") else None
            ),
            "max_caliber_recovery_latest": (
                "experiments/results/max-caliber-recovery.json"
                if max_caliber_recovery.get("result_sha256") else None
            ),
            "strategy_path_lagrangian_latest": (
                "experiments/results/strategy-path-lagrangian.json"
                if strategy_path_lagrangian.get("activation_sha256") else None
            ),
            "strategy_program_representation_latest": (
                "experiments/results/strategy-program-representation-ablation.json"
                if strategy_program_representation.get("activation_sha256") else None
            ),
            "learning_schedule_latest": (
                "institutional_learning/scheduler/latest.json"
                if (root / "institutional_learning" / "scheduler" / "latest.json").is_file()
                else None
            ),
            "research_budget_tournament_latest": (
                "institutional_learning/research_budget_tournament/current/latest.json"
                if research_budget_tournament.get("enabled") else None
            ),
            "activation_matrix_policy_learning_latest": (
                "research_jobs/activation/matrix_policy/latest.json"
                if (
                    root / "research_jobs" / "activation" / "matrix_policy" / "latest.json"
                ).is_file() else None
            ),
            "point_in_time_evidence_latest": (
                "evidence_vault/latest_capture.json"
                if point_in_time_evidence.get("enabled") else None
            ),
            "sealed_walk_forward_profile": (
                "point_in_time_replay/sealed_walk_forward_seed.json"
                if sealed_walk_forward_profile.is_file() else None
            ),
            "strategy_move_learning_latest": "institutional_learning/strategy_moves/latest.json",
            "strategy_program_learning_latest": (
                strategy_program_learning["rows"][0]["artifact_path"]
                if strategy_program_learning["rows"] else None
            ),
            "strategy_program_transfer_latest": (
                "institutional_learning/strategy_programs/transfer-latest.json"
                if (root / "institutional_learning" / "strategy_programs" / "transfer-latest.json").is_file()
                else None
            ),
            "strategy_program_control_acquisition_latest": (
                "institutional_learning/strategy_programs/control-acquisition-latest.json"
                if (
                    root / "institutional_learning" / "strategy_programs"
                    / "control-acquisition-latest.json"
                ).is_file() else None
            ),
            "strategy_program_comparison_latest": (
                "institutional_learning/strategy_programs/comparison-latest.json"
                if (
                    root / "institutional_learning" / "strategy_programs"
                    / "comparison-latest.json"
                ).is_file() else None
            ),
            "strategy_cohort_research_latest": "institutional_learning/strategy_cohorts/latest.json",
            "strategy_active_comparator_latest": (
                "institutional_learning/strategy_cohorts/active-comparator-frontier.json"
                if strategy_active_comparator.get("active_comparator_frontier_sha256") else None
            ),
            "strategy_law_induction_latest": (
                "institutional_learning/strategy_laws/latest.json"
                if strategy_law_induction.get("candidate_count") else None
            ),
            "strategy_valuation_bridge_latest": (
                "institutional_learning/strategy_valuation/latest.json"
                if (root / "institutional_learning" / "strategy_valuation" / "latest.json").is_file()
                else None
            ),
            "strategy_transfer_latest": (
                "institutional_learning/strategy_transfer/latest.json"
                if (root / "institutional_learning" / "strategy_transfer" / "latest.json").is_file()
                else None
            ),
            "underwriting_latest": (
                "underwriting/latest.json"
                if (root / "underwriting" / "latest.json").is_file()
                else None
            ),
            "state_price_proposal_audit": (
                "state_pricing/proposal-audit.json"
                if (root / "state_pricing" / "proposal-audit.json").is_file()
                else None
            ),
            "modeled_payoff_grid_audit": (
                "state_pricing/modeled-grid-audit.json"
                if (root / "state_pricing" / "modeled-grid-audit.json").is_file()
                else None
            ),
            "allocation_readiness_latest": (
                "allocation/latest.json"
                if (root / "allocation" / "latest.json").is_file()
                else None
            ),
            "equity_paper_proposals_latest": (
                "paper_proposals/equities/latest.json"
                if (root / "paper_proposals" / "equities" / "latest.json").is_file()
                else None
            ),
            "fund_paper_proposals_latest": (
                "paper_proposals/funds/latest.json"
                if (root / "paper_proposals" / "funds" / "latest.json").is_file()
                else None
            ),
            "fund_implementation_review_latest": (
                "research_jobs/fund_implementation/latest.json"
                if (root / "research_jobs" / "fund_implementation" / "latest.json").is_file()
                else None
            ),
            "investor_action_brief_latest": "action_briefs/latest.json",
            "capital_cycle_policy": str(config.get("capital_cycle_policy") or "capital_cycle.yaml"),
            "capital_cycle_latest": "capital_cycles/latest.json",
            "opportunity_book_latest": "opportunity_books/latest.json",
            "discovery_policy": str(config.get("discovery_policy") or "discovery.yaml"),
            "discovery_latest": "discovery/latest.json",
            "market_catalog": "universe/catalog-latest.json",
            "sec_frame_screen_latest": (
                "data/sec_frames/latest.json"
                if broad_equity_potential.get("enabled") else None
            ),
            "sec_frame_acquisition_latest": (
                broad_equity_potential.get("acquisition_path")
                if broad_equity_potential.get("enabled") else None
            ),
            "market_scout_latest": "research_jobs/latest.json",
            "market_scout_policy": str(config.get("market_scout_policy") or "research_jobs/intents.yaml"),
            "scheduled_market_scout_latest": "research_jobs/scheduled/latest.json",
            "enrichment_policy": str(config.get("enrichment_policy") or "research_jobs/enrichment_policy.yaml"),
            "enrichment_latest": "research_jobs/enrichment/latest.json",
            "enrichment_execution_latest": "research_jobs/enrichment/latest_execution.json",
            "broad_fund_acquisition_latest": "research_jobs/fund_acquisition/latest.json",
            "search_trial_census": "golden-store://search_trial_family",
            "research_requests": "research_jobs/requests/",
            "fund_holdings": "data/fund_holdings/",
            "fund_lookthrough_acquisition_latest": (
                "data/fund_holdings/portfolio-acquisition-latest.json"
                if (root / "data" / "fund_holdings" / "portfolio-acquisition-latest.json").is_file()
                else None
            ),
        },
        "public_data_policy": {
            "default": True,
            "rule": "Every numeric input must bind to cached bytes and observed/available times.",
            "retrieval_only_boundary": "Retrieval-only rows cannot be used before the recorded retrieval time.",
            "configured_sources": ["Nasdaq broad equity and ETF catalogs", "SEC EDGAR", "NYU current implied ERP", "FRED/ALFRED", "Alpha Vantage", "Yahoo retrieval-only chart", "iShares issuer characteristics", "generic HTTPS CSV"],
        },
    }
    projection = _compact_ui_lineage(body)
    return {**projection, "read_model_sha256": stable_sha256(projection)}


def _composite_epoch_transition_pending(root: Path) -> bool:
    """Return whether sources are ahead of the completed discovery publication."""
    source_run = _current_source_run(root) or {}
    discovery = _read_json(root / "discovery" / "latest.json") or {}
    if not source_run or not discovery:
        return False
    return bool(
        source_run.get("run_sha256") != discovery.get("source_run_sha256")
        or _current_discovery_record(root, discovery) is None
        or not validated_discovery_research_handoff(root, discovery)
    )


def build_read_model(workspace: str | Path | None = None) -> dict[str, Any]:
    """Coalesce concurrent service projections into one filesystem-visible build."""
    root = resolve_workspace(workspace)
    started_ns = time.time_ns()
    state_dir = root / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    lock_path = state_dir / "read_model.lock"
    with lock_path.open("a+b") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        cached_path = state_dir / "read_model.json"
        try:
            stat = cached_path.stat()
        except OSError:
            stat = None
        cached = _read_json(cached_path) if stat is not None else None
        cached_is_current_workspace = bool(
            cached
            and cached.get("schema") == READ_MODEL_SCHEMA
            and str(cached.get("workspace_path") or "") == str(root)
        )
        if cached_is_current_workspace and _composite_epoch_transition_pending(root):
            return cached
        if stat is not None and stat.st_mtime_ns >= started_ns:
            if cached_is_current_workspace:
                return cached
        return _build_read_model_unlocked(root)


def project_workspace_read_model(
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Build and persist the UI projection after a bounded state transition."""
    root = resolve_workspace(workspace)
    read_model = build_read_model(root)
    _atomic_json(root / "state" / "read_model.json", read_model)
    return read_model


def read_cached_read_model(workspace: str | Path | None = None) -> dict[str, Any]:
    """Read the last completed UI projection and overlay only live service state."""
    root = resolve_workspace(workspace)
    cached_path = root / "state" / "read_model.json"
    try:
        stat = cached_path.stat()
    except OSError:
        stat = None
    cached = None
    if stat is not None:
        cache_key = str(cached_path)
        with _READ_MODEL_CACHE_LOCK:
            entry = _READ_MODEL_PARSE_CACHE.get(cache_key)
            if entry and entry[:2] == (stat.st_mtime_ns, stat.st_size):
                cached = entry[2]
            else:
                cached = _read_json(cached_path)
                if cached:
                    _READ_MODEL_PARSE_CACHE[cache_key] = (
                        stat.st_mtime_ns, stat.st_size, cached,
                    )
    if (
        cached
        and cached.get("schema") == READ_MODEL_SCHEMA
        and str(cached.get("workspace_path") or "") == str(root)
    ):
        projection = {**cached}
        try:
            _, config = load_workspace_config(root)
        except (FileNotFoundError, OSError, ValueError):
            config = {}
        registrations = {
            str(row.get("project_id") or ""): row
            for row in (config.get("research_projects") or ())
            if isinstance(row, Mapping)
        }
        live_projects = []
        for row in projection.get("research_projects") or ():
            if not isinstance(row, Mapping):
                live_projects.append(row)
                continue
            registration = registrations.get(str(row.get("project_id") or ""))
            shadow = None
            if registration:
                project_path = (root / str(registration.get("path") or "")).resolve()
                shadow = _read_json(
                    project_path / "workspace" / "prospective_shadow" / "latest.json"
                )
            live_projects.append({**row, **({"prospective_shadow": shadow} if shadow else {})})
        if live_projects:
            projection["research_projects"] = live_projects
        for section, filename in (
            ("discovery", "discovery_service.json"),
            ("capital_cycle", "capital_cycle_service.json"),
            ("subscription_research", "research_agent_service.json"),
        ):
            heartbeat = _read_json(root / "state" / filename)
            if heartbeat and isinstance(projection.get(section), Mapping):
                projection[section] = {**projection[section], "service": heartbeat}
        if isinstance(projection.get("subscription_research"), Mapping):
            live_research = research_agent_live_status(root)
            projection["subscription_research"] = {
                **projection["subscription_research"],
                "active_jobs": live_research["active_jobs"],
                "candidate_lane": live_research["candidate_lane"],
                "activation_lane": live_research["activation_lane"],
                "fund_lane": live_research["fund_lane"],
                "frozen_chain_lane": live_research["frozen_chain_lane"],
                "next_job": live_research["next_job"],
                "daily_dispatch_budget": live_research["daily_dispatch_budget"],
                "live_queue_counts": live_research["queue_counts"],
                "live_queued_by_kind": live_research["queued_by_kind"],
                "live_observed_at": live_research["observed_at"],
            }
            projection["live_automatic_transition"] = _active_research_transition(
                projection["subscription_research"]
            )
        projection["discovery_research_handoff"] = _read_json(
            root / "state" / "discovery_research_handoff.json"
        ) or {}
        frontier_heads = [
            row for path in sorted((root / "strategy_frontiers" / "heads").glob("*.json"))
            if (row := _read_json(path)) and row.get("company")
        ]
        latest_frontier = _read_json(root / "strategy_frontiers" / "latest.json")
        head_entities = {
            str(row["company"].get("id") or "").upper() for row in frontier_heads
        }
        if (
            latest_frontier and latest_frontier.get("company")
            and str(latest_frontier["company"].get("id") or "").upper() not in head_entities
        ):
            frontier_heads.append(latest_frontier)
        for frontier_head in frontier_heads:
            entity_id = str(frontier_head["company"].get("id") or "").upper()
            frontier_rows = [
                row for row in projection.get("company_strategy_frontiers") or ()
                if str((row.get("company") or {}).get("id") or "").upper() != entity_id
            ]
            frontier_path = root / "strategy_frontiers" / "results" / (
                f"{entity_id.lower()}-{str(frontier_head.get('strategy_frontier_sha256'))[:12]}.json"
            )
            frontier_rows.append(_ui_strategy_frontier({
                **frontier_head,
                "result_path": frontier_path.relative_to(root).as_posix(),
            }))
            projection["company_strategy_frontiers"] = sorted(
                frontier_rows,
                key=lambda row: str((row.get("company") or {}).get("id") or ""),
            )
        discovery = projection.get("discovery") or {}
        fund_lookthrough = _read_json(root / "state" / "fund_lookthrough_service.json")
        current_plan_sha256 = str(
            (projection.get("fund_lookthrough_acquisition_plan") or {}).get(
                "plan_sha256"
            ) or ""
        )
        if (
            fund_lookthrough
            and (
                not current_plan_sha256
                or fund_lookthrough.get("current_plan_sha256")
                == current_plan_sha256
            )
        ):
            projection["fund_lookthrough_acquisition"] = fund_lookthrough
        business_clock = _read_json(
            root / "institutional_learning" / "strategy_business_clock" / "latest.json"
        )
        if business_clock:
            projection["strategy_business_clock"] = business_clock
        if "broad_fund_acquisition" not in projection:
            projection["broad_fund_acquisition"] = _broad_fund_acquisition_status(
                root,
                next_due_at=(discovery.get("schedule") or {}).get("next_due_at"),
            )
        return projection
    return build_read_model(root)


def _record_capital_cycle_bundle(
    root: Path,
    config: Mapping[str, Any],
    *,
    run: Mapping[str, Any],
    book: Mapping[str, Any],
) -> dict[str, tuple[str, ...]]:
    """Atomically bind one cycle and opportunity book to their golden lineage."""

    owner = str(config.get("owner") or "operator-paper-book")
    completed_at = str(run["completed_at"])
    store = GoldenStore(_store_path(root, config))
    book_leaf = GoldenLeaf(
        owner=owner,
        object_kind="opportunity_book",
        object_id="operator-opportunity-book",
        epoch=str(book["book_sha256"]),
        occurred_at=completed_at,
        available_at=completed_at,
        payload=dict(book),
        source_refs=tuple(book["source_refs"]),
    )
    cycle_leaf = GoldenLeaf(
        owner=owner,
        object_kind="capital_cycle_run",
        object_id=str(run["cycle_id"]),
        epoch=str(run["run_sha256"]),
        occurred_at=completed_at,
        available_at=completed_at,
        payload=dict(run),
        source_refs=(
            f"discovery:{book['discovery_run_sha256']}",
            f"opportunity_book:{book['book_sha256']}",
        ),
    )
    edges = [GoldenEdge(cycle_leaf.leaf_sha256, book_leaf.leaf_sha256, "contains")]
    walk_forward_leaf = str(
        (run.get("sealed_walk_forward") or {}).get("golden_leaf_sha256") or ""
    )
    if walk_forward_leaf:
        edges.append(GoldenEdge(
            cycle_leaf.leaf_sha256, walk_forward_leaf, "contains",
        ))
    try:
        discovery_head = store.head(owner, "discovery_run", "workspace-opportunity-discovery")
        edges.append(GoldenEdge(
            book_leaf.leaf_sha256, str(discovery_head["leaf_sha256"]), "derived_from",
        ))
    except KeyError:
        pass
    for action in run.get("forecast_actions") or []:
        if not isinstance(action, Mapping) or not action.get("run_id"):
            continue
        try:
            forecast_head = store.head(
                owner, "closed_book_forecast_run", str(action["run_id"]),
            )
            edges.append(GoldenEdge(
                cycle_leaf.leaf_sha256, str(forecast_head["leaf_sha256"]), "contains",
            ))
        except KeyError:
            continue
    for action in (run.get("market_state") or {}).get("forecast_actions") or []:
        if not isinstance(action, Mapping) or not action.get("run_id"):
            continue
        try:
            forecast_head = store.head(
                owner, "market_state_forecast_run", str(action["run_id"]),
            )
            edges.append(GoldenEdge(
                cycle_leaf.leaf_sha256, str(forecast_head["leaf_sha256"]), "contains",
            ))
        except KeyError:
            continue
    policy_action = (run.get("portfolio_policy") or {}).get("open") or {}
    if isinstance(policy_action, Mapping) and policy_action.get("run_id"):
        try:
            policy_head = store.head(
                owner, "portfolio_policy_run", str(policy_action["run_id"]),
            )
            edges.append(GoldenEdge(
                cycle_leaf.leaf_sha256, str(policy_head["leaf_sha256"]), "contains",
            ))
            if policy_action.get("opportunity_book_sha256") == book.get("book_sha256"):
                edges.append(GoldenEdge(
                    str(policy_head["leaf_sha256"]), book_leaf.leaf_sha256, "derived_from",
                ))
        except KeyError:
            pass
    record = store.append_bundle((book_leaf, cycle_leaf), tuple(edges), make_heads=True)
    _atomic_json(root / "state" / "capital_cycle_commit.json", {
        "schema": "jaggedthoughts-capital-cycle-commit-v1",
        "cycle_id": run["cycle_id"],
        "run_sha256": run["run_sha256"],
        "book_sha256": book["book_sha256"],
        "committed_at": _utc_now(),
        "golden_record": record,
    })
    return record


def _compile_workspace_strategy_transfer(
    root: Path, learning_state: Mapping[str, Any],
) -> dict[str, Any]:
    move_library = _read_json(
        root / "institutional_learning" / "strategy_moves" / "latest.json"
    ) or {}
    result = compile_strategy_transfer_index(
        move_library,
        learning_state,
        generated_at=str(learning_state.get("generated_at") or _utc_now()),
    )
    _atomic_json(
        root / "institutional_learning" / "strategy_transfer" / "latest.json",
        result,
    )
    return result


def _compile_workspace_strategy_program_transfer(root: Path) -> dict[str, Any]:
    plans = [
        row for path in sorted(
            (root / "institutional_learning" / "strategy_programs" / "outcome-plans").glob("*.json")
        ) if (row := _read_json(path))
    ]
    episodes = [
        row for path in sorted(
            (root / "institutional_learning" / "strategy_programs" / "outcomes").glob("*.json")
        ) if (row := _read_json(path))
    ]
    result = compile_strategy_program_transfer_index(
        plans, episodes, generated_at=_utc_now(),
    )
    _atomic_json(
        root / "institutional_learning" / "strategy_programs" / "transfer-latest.json",
        result,
    )
    return result


def _compile_workspace_strategy_program_controls(
    root: Path, program_transfer: Mapping[str, Any],
) -> dict[str, Any]:
    requests = [
        row for path in sorted(
            (root / "research_jobs" / "strategy_programs" / "requests").glob("*.json")
        ) if (row := _read_json(path))
    ]
    results = [
        row for path in sorted(
            (root / "institutional_learning" / "strategy_programs" / "results").glob("*.json")
        ) if (row := _read_json(path))
    ]
    queue = research_agent_status(root).get("queue") or {}
    result = compile_strategy_program_control_acquisition(
        program_transfer=program_transfer,
        library=_read_json(
            root / "institutional_learning" / "strategy_moves" / "latest.json"
        ) or {},
        program_requests=requests,
        program_results=results,
        queue_jobs=queue.get("jobs") or (),
        generated_at=_utc_now(),
    )
    _atomic_json(
        root / "institutional_learning" / "strategy_programs"
        / "control-acquisition-latest.json",
        result,
    )
    return result


def _compile_workspace_strategy_program_comparison(
    root: Path, program_transfer: Mapping[str, Any],
    program_controls: Mapping[str, Any],
) -> dict[str, Any]:
    plans = [
        row for path in sorted(
            (root / "institutional_learning" / "strategy_programs" / "outcome-plans").glob("*.json")
        ) if (row := _read_json(path))
    ]
    program_episodes = [
        row for path in sorted(
            (root / "institutional_learning" / "strategy_programs" / "outcomes").glob("*.json")
        ) if (row := _read_json(path))
    ]
    control_episodes = [
        row for path in sorted(
            (root / "institutional_learning" / "strategy_programs" / "control-outcomes").glob("*.json")
        ) if (row := _read_json(path))
    ]
    result = compile_strategy_program_operating_comparison(
        program_transfer=program_transfer,
        control_acquisition=program_controls,
        program_plans=plans,
        program_episodes=program_episodes,
        control_episodes=control_episodes,
        generated_at=_utc_now(),
    )
    _atomic_json(
        root / "institutional_learning" / "strategy_programs" / "comparison-latest.json",
        result,
    )
    return result


def _compile_workspace_strategy_laws(
    root: Path, learning_state: Mapping[str, Any],
) -> dict[str, Any]:
    move_library = _read_json(
        root / "institutional_learning" / "strategy_moves" / "latest.json"
    ) or {}
    cohort_plan = _read_json(
        root / "institutional_learning" / "strategy_cohorts" / "latest.json"
    ) or {}
    projection = _read_json(
        root / "institutional_learning" / "strategy_cohorts" / "projection-frontier.json"
    ) or {}
    destination = root / "institutional_learning" / "strategy_laws" / "latest.json"
    prior = _read_json(destination)
    result = compile_strategy_law_induction(
        move_library, cohort_plan, projection, learning_state,
        generated_at=str(learning_state.get("generated_at") or _utc_now()),
        prior=prior,
    )
    _atomic_json(destination, result)
    return result


def _advance_workspace_strategy_business_clock(
    root: Path, config: Mapping[str, Any], *, acquire_historical_sources: bool = False,
) -> dict[str, Any]:
    """Settle due operating evidence, then refresh panels, controls, and laws."""
    clock_epoch = _utc_now()
    strategy_move_library = compile_workspace_strategy_move_library(root)
    manifest_path = root / str(config.get("source_manifest") or "sources.yaml")
    outcome_source_plan = compile_strategy_outcome_source_plan(
        strategy_move_library, load_source_manifest(manifest_path), as_of=clock_epoch,
    )
    outcome_source_refresh = None
    if outcome_source_plan["source_ids"]:
        outcome_source_refresh = consume_public_sources(
            manifest_path, workspace=root, strict=False,
            retrieved_at=clock_epoch, source_ids=outcome_source_plan["source_ids"],
            derive_metrics=True,
            receipt_dir=root / "institutional_learning" / "strategy_business_clock",
        )
    outcomes = submit_workspace_observation_outcomes(
        root, as_of=clock_epoch if outcome_source_refresh else None,
    )
    program_outcomes = submit_workspace_program_observation_outcomes(root)
    store = GoldenStore(_store_path(root, config))
    owner = str(config.get("owner") or "operator-paper-book")
    strategy_move_library = compile_workspace_strategy_move_library(root)
    _atomic_json(
        root / "institutional_learning" / "strategy_moves" / "latest.json",
        strategy_move_library,
    )
    record_strategy_move_library(
        store, owner=owner, library=strategy_move_library,
    )
    strategy_calibration_successors = enqueue_strategy_calibration_successors(
        root, strategy_move_library,
    )
    program_episode_rows = {
        str(row.get("episode_sha256")): row
        for path in sorted(
            (root / "institutional_learning" / "strategy_programs" / "outcomes").glob("*.json")
        ) if (row := _read_json(path)) and row.get("episode_sha256")
    }
    for episode in program_episode_rows.values():
        record_strategy_program_outcome_episode(store, owner=owner, episode=episode)
    result = run_institutional_learning_cycle(
        root,
        owner=str(config.get("owner") or "operator-paper-book"),
        store_path=_store_path(root, config),
        catalog_path=root / str(
            config.get("investment_law_catalog")
            or "institutional_learning/laws.yaml"
        ),
    )
    state = dict(result.get("state") or institutional_learning_status(root))
    transfer = _compile_workspace_strategy_transfer(root, state)
    program_transfer = _compile_workspace_strategy_program_transfer(root)
    program_control_acquisition = _compile_workspace_strategy_program_controls(
        root, program_transfer,
    )
    for card in program_control_acquisition.get("cards") or ():
        for target in card.get("admitted_source_controls") or ():
            plan = target.get("control_readout")
            if plan:
                record_strategy_program_control_outcome_plan(
                    store, owner=owner, plan=plan,
                    acquisition_card_sha256=str(card["acquisition_card_sha256"]),
                    transfer_card_sha256=str(card["transfer_card_sha256"]),
                )
    program_control_outcomes = submit_workspace_program_control_observation_outcomes(root)
    for path in sorted((
        root / "institutional_learning" / "strategy_programs" / "control-outcomes"
    ).glob("*.json")):
        if episode := _read_json(path):
            record_strategy_program_control_outcome_episode(
                store, owner=owner, episode=episode,
            )
    program_comparison = _compile_workspace_strategy_program_comparison(
        root, program_transfer, program_control_acquisition,
    )
    laws = _compile_workspace_strategy_laws(root, state)
    strategy_valuation_bridge = compile_strategy_valuation_bridge_readiness(
        laws, generated_at=str(state.get("generated_at") or _utc_now()),
    )
    _atomic_json(
        root / "institutional_learning" / "strategy_valuation" / "latest.json",
        strategy_valuation_bridge,
    )
    try:
        frontier = compile_workspace_strategy_control_eligibility(root)
        _atomic_json(
            root / "institutional_learning" / "strategy_cohorts"
            / "control-eligibility-frontier.json",
            frontier,
        )
        from .strategy_control_research import bind_workspace_strategy_control_research

        control_binding = bind_workspace_strategy_control_research(root)
    except (
        FileNotFoundError, KeyError, OSError, RuntimeError, TypeError, ValueError,
        yaml.YAMLError,
    ) as error:
        frontier = {
            "status": "unavailable", "error": f"{type(error).__name__}: {error}"[:1_000],
            "admissible_controls": [], "capital_authority": False,
        }
        control_binding = {
            "status": "unavailable", "error": frontier["error"],
            "capital_authority": False,
        }
    try:
        strategy_active_comparator = compile_workspace_strategy_active_comparator(root)
    except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
        strategy_active_comparator = {
            "schema": "jaggedthoughts-strategy-active-comparator-frontier-v1",
            "selection_status": "unavailable",
            "error": f"{type(error).__name__}: {error}"[:1_000],
            "comparison_groups": [], "audit": {},
            "next_company_facts_acquisition_entities": [],
            "causal_estimate_ran": False, "rank_authority": False,
            "law_authority": False, "capital_authority": False,
        }
    try:
        strategy_state_control_acquisition = (
            compile_workspace_strategy_state_control_acquisition(
                root,
                root / "experiments" / "results" / "strategy-state-experiment.json",
            )
        )
        _atomic_json(
            root / "experiments" / "results"
            / "strategy-state-control-acquisition.json",
            strategy_state_control_acquisition,
        )
    except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
        strategy_state_control_acquisition = {
            "schema": "jaggedthoughts-strategy-state-control-acquisition-v1",
            "status": "unavailable",
            "error": f"{type(error).__name__}: {error}"[:1_000],
            "eligible_no_family_controls_exist": False,
            "audit": {},
            "capital_authority": False,
        }
    historical_acquisition = None
    try:
        if acquire_historical_sources:
            historical_action = acquire_workspace_historical_strategy_events(root, limit=4)
            historical_replay = historical_action["replay"]
            historical_acquisition = historical_action["acquisition"]
        else:
            historical_replay = compile_workspace_historical_strategy_event_replay(root)
            _atomic_json(
                root / "institutional_learning" / "historical_strategy_event_replay"
                / "latest.json",
                historical_replay,
            )
    except (
        FileNotFoundError, KeyError, OSError, RuntimeError, TypeError, ValueError,
        yaml.YAMLError,
    ) as error:
        historical_replay = {
            "status": "unavailable",
            "error": f"{type(error).__name__}: {error}"[:1_000],
            "episode_count": 0,
            "capital_authority": False,
        }
    try:
        historical_walk_forward = compile_workspace_strategy_walk_forward(root)
    except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
        historical_walk_forward = {
            "status": "unavailable",
            "error": f"{type(error).__name__}: {error}"[:1_000],
            "fold_count": 0,
            "scored_episode_count": 0,
            "capital_authority": False,
        }
    try:
        historical_security_walk_forward = (
            compile_workspace_strategy_security_walk_forward(root)
        )
    except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
        historical_security_walk_forward = {
            "status": "unavailable",
            "error": f"{type(error).__name__}: {error}"[:1_000],
            "fold_count": 0,
            "scored_episode_count": 0,
            "capital_authority": False,
        }
    try:
        historical_strategy_representation_learning = (
            compile_strategy_security_representation_learning(
                historical_security_walk_forward,
                replay=historical_replay,
            )
        )
        _atomic_json(
            root / "institutional_learning" / "historical_strategy_event_replay"
            / "representation-learning.json",
            historical_strategy_representation_learning,
        )
    except (KeyError, TypeError, ValueError) as error:
        historical_strategy_representation_learning = {
            "status": "unavailable",
            "error": f"{type(error).__name__}: {error}"[:1_000],
            "conjecture_count": 0,
            "capital_authority": False,
        }
    try:
        historical_control_design = compile_workspace_historical_strategy_control_design(root)
        if acquire_historical_sources:
            historical_control_action = acquire_workspace_historical_strategy_controls(
                root, design=historical_control_design, limit=4,
            )
            historical_control_design = historical_control_action["design"]
            historical_control_acquisition = historical_control_action["acquisition"]
        else:
            historical_control_acquisition = None
    except (
        FileNotFoundError, KeyError, OSError, RuntimeError, TypeError, ValueError,
        yaml.YAMLError,
    ) as error:
        historical_control_design = {
            "status": "unavailable",
            "error": f"{type(error).__name__}: {error}"[:1_000],
            "pretrend_rankable_control_count": 0,
            "capital_authority": False,
        }
        historical_control_acquisition = {
            "status": "unavailable",
            "error": historical_control_design["error"],
            "capital_authority": False,
        }
    try:
        if acquire_historical_sources:
            bulk_receipt = acquire_sec_bulk_submissions(root)
            source_check_body = {
                "schema": "jaggedthoughts-strategy-event-source-check-v1",
                "checked_at": _utc_now(),
                "bulk_source_receipt_sha256": bulk_receipt.get("receipt_sha256"),
                "bulk_source_retrieved_at": bulk_receipt.get("retrieved_at"),
                "capital_authority": False,
            }
            _atomic_json(
                root / "institutional_learning" / "strategy_path_shadow"
                / "source-check.json",
                {**source_check_body, "source_check_sha256": stable_sha256(source_check_body)},
            )
        historical_bulk_corpus = (
            compile_historical_strategy_bulk_event_corpus(root)
            if (root / "sources" / "bulk" / "sec_submissions" / "latest.json").exists()
            else {
                "status": "awaiting_sec_bulk_archive", "event_count": 0,
                "capital_authority": False,
            }
        )
    except (
        FileNotFoundError, KeyError, OSError, RuntimeError, TypeError, ValueError,
        zipfile.BadZipFile, yaml.YAMLError,
    ) as error:
        historical_bulk_corpus = {
            "status": "unavailable",
            "error": f"{type(error).__name__}: {error}"[:1_000],
            "event_count": 0, "capital_authority": False,
        }
    historical_bulk_acquisition = None
    historical_bulk_semantic_resolution = None
    historical_bulk_outcomes = None
    historical_bulk_outcome_coverage = None
    historical_bulk_panel_readiness = None
    historical_bulk_effects = None
    historical_outcome_robustness = None
    historical_law_search = None
    historical_law_trial = None
    try:
        if historical_bulk_corpus.get("corpus_sha256"):
            if acquire_historical_sources:
                historical_bulk_acquisition = acquire_bulk_strategy_documents(root, limit=8)
                historical_bulk_learning = historical_bulk_acquisition["queue"]
                if historical_bulk_learning.get("ambiguous_semantic_queue_count"):
                    historical_bulk_semantic_resolution = resolve_bulk_strategy_ambiguities(
                        root, limit=4,
                    )
                    historical_bulk_learning = historical_bulk_semantic_resolution["queue"]
            else:
                historical_bulk_learning = compile_bulk_strategy_learning_queue(root)
        else:
            historical_bulk_learning = {
                "status": "awaiting_bulk_strategy_corpus", "queue_count": 0,
                "classified_event_count": 0, "capital_authority": False,
            }
    except (FileNotFoundError, KeyError, OSError, RuntimeError, TypeError, ValueError) as error:
        historical_bulk_learning = {
            "status": "unavailable",
            "error": f"{type(error).__name__}: {error}"[:1_000],
            "queue_count": 0, "classified_event_count": 0,
            "capital_authority": False,
        }
    try:
        if acquire_historical_sources:
            acquire_sec_bulk_companyfacts(root)
        if (root / "sources" / "bulk" / "sec_companyfacts" / "latest.json").exists():
            historical_bulk_outcomes = compile_bulk_strategy_outcome_observations(root)
            historical_bulk_outcome_coverage = compile_bulk_strategy_outcome_coverage(root)
            historical_bulk_panel_readiness = compile_bulk_strategy_panel_readiness(root)
            historical_bulk_effects = compile_bulk_strategy_effect_diagnostics(root)
            historical_outcome_robustness = compile_bulk_strategy_outcome_robustness(root)
            historical_law_search = compile_bulk_strategy_law_search(root)
            historical_law_trial = advance_bulk_strategy_law_trial(root)
            historical_bulk_learning = compile_bulk_strategy_learning_queue(root)
        else:
            historical_bulk_outcomes = {
                "status": "awaiting_bulk_companyfacts", "observation_count": 0,
                "covered_entity_count": 0, "capital_authority": False,
            }
            historical_bulk_panel_readiness = {
                "estimation_status": "awaiting_bulk_companyfacts",
                "group_time_ready_cell_count": 0, "capital_authority": False,
            }
            historical_bulk_outcome_coverage = {
                "status": "awaiting_bulk_companyfacts", "covered_entity_count": 0,
                "capital_authority": False,
            }
            historical_bulk_effects = {
                "status": "awaiting_joint_panel", "ready_cell_count": 0,
                "causal_claim": False, "capital_authority": False,
            }
            historical_outcome_robustness = {
                "status": "awaiting_joint_panel", "family_count": 0,
                "causal_claim": False, "capital_authority": False,
            }
            historical_law_search = {
                "status": "awaiting_parent_diagnostic",
                "frozen_child_candidate_count": 0,
                "acquisition_frontier_count": 0, "capital_authority": False,
            }
            historical_law_trial = {
                "status": "awaiting_child_law_frontier", "capital_authority": False,
            }
    except (
        FileNotFoundError, KeyError, OSError, RuntimeError, TypeError, ValueError,
        zipfile.BadZipFile,
    ) as error:
        historical_bulk_outcomes = {
            "status": "unavailable", "error": f"{type(error).__name__}: {error}"[:1_000],
            "observation_count": 0, "covered_entity_count": 0,
            "capital_authority": False,
        }
        historical_bulk_panel_readiness = {
            "estimation_status": "unavailable",
            "error": f"{type(error).__name__}: {error}"[:1_000],
            "group_time_ready_cell_count": 0, "capital_authority": False,
        }
        historical_bulk_outcome_coverage = {
            "status": "unavailable", "error": f"{type(error).__name__}: {error}"[:1_000],
            "covered_entity_count": 0, "capital_authority": False,
        }
        historical_bulk_effects = {
            "status": "unavailable", "error": f"{type(error).__name__}: {error}"[:1_000],
            "ready_cell_count": 0, "causal_claim": False, "capital_authority": False,
        }
        historical_outcome_robustness = {
            "status": "unavailable", "error": f"{type(error).__name__}: {error}"[:1_000],
            "family_count": 0, "causal_claim": False, "capital_authority": False,
        }
        historical_law_search = {
            "status": "unavailable", "error": f"{type(error).__name__}: {error}"[:1_000],
            "frozen_child_candidate_count": 0,
            "acquisition_frontier_count": 0, "capital_authority": False,
        }
        historical_law_trial = {
            "status": "unavailable", "error": f"{type(error).__name__}: {error}"[:1_000],
            "capital_authority": False,
        }
    historical_bulk_retention = None
    try:
        if (
            acquire_historical_sources
            and historical_bulk_corpus.get("corpus_sha256")
            and historical_bulk_outcomes.get("outcomes_sha256")
        ):
            historical_bulk_retention = enforce_sec_bulk_archive_retention(root)
    except (FileNotFoundError, KeyError, OSError, RuntimeError, TypeError, ValueError) as error:
        historical_bulk_retention = {
            "status": "retention_failed_closed",
            "error": f"{type(error).__name__}: {error}"[:1_000],
            "capital_authority": False,
        }
    strategy_path_acquisition = None
    strategy_path_semantic_resolution = None
    strategy_event_research_acquisition = None
    try:
        strategy_path_shadow = compile_workspace_strategy_path_shadow(root)
        if acquire_historical_sources and strategy_path_shadow.get("acquisition_queue"):
            strategy_path_acquisition = acquire_workspace_strategy_path_shadow(
                root, strategy_path_shadow, limit=8,
            )
            ambiguous = list(
                strategy_path_acquisition.get("ambiguous_accessions") or ()
            )
            if ambiguous:
                try:
                    strategy_path_semantic_resolution = resolve_bulk_strategy_ambiguities(
                        root, limit=min(4, len(ambiguous)),
                        accession_numbers=ambiguous,
                    )
                except (OSError, RuntimeError, TypeError, ValueError) as error:
                    strategy_path_semantic_resolution = {
                        "status": "unavailable",
                        "error": f"{type(error).__name__}: {error}"[:1_000],
                        "capital_authority": False,
                    }
            strategy_path_shadow = compile_workspace_strategy_path_shadow(root)
        if acquire_historical_sources and strategy_path_shadow.get("event_research_queue"):
            try:
                strategy_event_research_acquisition = (
                    _hydrate_workspace_strategy_event_research(
                        root, config, strategy_path_shadow, limit=3,
                    )
                )
            except (
                FileNotFoundError, KeyError, OSError, RuntimeError, TypeError,
                ValueError, yaml.YAMLError,
            ) as error:
                strategy_event_research_acquisition = {
                    "schema": "jaggedthoughts-strategy-event-research-acquisition-v1",
                    "status": "unavailable",
                    "error": f"{type(error).__name__}: {error}"[:1_000],
                    "capital_authority": False,
                }
        _atomic_json(
            root / "institutional_learning" / "strategy_path_shadow" / "latest.json",
            strategy_path_shadow,
        )
        if strategy_path_shadow.get("shadow_sha256"):
            _atomic_json(
                root / "institutional_learning" / "strategy_path_shadow" / "snapshots"
                / f"{strategy_path_shadow['shadow_sha256']}.json",
                strategy_path_shadow,
            )
    except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
        strategy_path_shadow = {
            "schema": "jaggedthoughts-strategy-path-shadow-v1",
            "status": "unavailable",
            "error": f"{type(error).__name__}: {error}"[:1_000],
            "forecast_count": 0, "capital_authority": False,
        }
    try:
        strategy_program_representation = (
            compile_workspace_strategy_program_representation_activation(root)
        )
    except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
        strategy_program_representation = {
            "status": "unavailable",
            "error": f"{type(error).__name__}: {error}"[:1_000],
            "capital_authority": False,
        }
    clock_body = {
        "schema": "jaggedthoughts-strategy-business-clock-v1",
        "advanced_at": str(state.get("generated_at") or _utc_now()),
        "outcome_acquisition_sha256": outcomes.get("acquisition_sha256"),
        "outcome_source_plan_sha256": outcome_source_plan.get("source_plan_sha256"),
        "outcome_source_refresh_run_sha256": (
            outcome_source_refresh.get("run_sha256") if outcome_source_refresh else None
        ),
        "due_point_in_time_outcome_contract_count": int(
            outcome_source_plan.get("due_point_in_time_contract_count") or 0
        ),
        "scheduled_outcome_source_ids": list(outcome_source_plan.get("source_ids") or ()),
        "missing_outcome_source_entity_ids": list(
            outcome_source_plan.get("missing_source_entity_ids") or ()
        ),
        "unsettled_outcome_contract_count": int(
            outcomes.get("unsettled_contract_count") or 0
        ),
        "due_outcome_contract_count": int(outcomes.get("due_contract_count") or 0),
        "eligible_outcome_count": int(outcomes.get("eligible_outcome_count") or 0),
        "blocked_due_outcome_contract_count": int(
            outcomes.get("blocked_due_contract_count") or 0
        ),
        "submitted_outcome_count": int(outcomes.get("submitted_count") or 0),
        "next_outcome_due_at": outcomes.get("next_due_at"),
        "learning_state_sha256": state.get("state_sha256"),
        "control_frontier_sha256": frontier.get("control_frontier_sha256"),
        "admissible_control_count": len(frontier.get("admissible_controls") or ()),
        "control_binding_sha256": control_binding.get("binding_sha256"),
        "strategy_state_control_acquisition_sha256": (
            strategy_state_control_acquisition.get("acquisition_sha256")
        ),
        "law_induction_sha256": laws.get("induction_sha256"),
        "strategy_program_control_outcome_acquisition_sha256": (
            program_control_outcomes.get("acquisition_sha256")
        ),
        "strategy_program_control_outcome_count": int(
            program_comparison.get("control_episode_count") or 0
        ),
        "strategy_program_comparison_sha256": program_comparison.get(
            "comparison_sha256"
        ),
        "strategy_program_comparison_status": program_comparison.get("status"),
        "strategy_program_representation_activation_sha256": (
            strategy_program_representation.get("activation_sha256")
        ),
        "strategy_program_representation_status": (
            strategy_program_representation.get("status")
        ),
        "strategy_valuation_bridge_readiness_sha256": (
            strategy_valuation_bridge.get("readiness_sha256")
        ),
        "strategy_valuation_bridge_status": strategy_valuation_bridge.get("status"),
        "historical_strategy_replay_sha256": historical_replay.get("replay_sha256"),
        "historical_strategy_episode_count": int(
            historical_replay.get("episode_count") or 0
        ),
        "historical_strategy_matured_event_count": int(
            historical_replay.get("matured_event_count") or 0
        ),
        "historical_strategy_outcome_ready_event_count": int(
            historical_replay.get("outcome_ready_event_count") or 0
        ),
        "historical_strategy_control_design_sha256": historical_control_design.get(
            "control_design_sha256"
        ),
        "historical_strategy_control_acquisition_sha256": (
            (historical_control_acquisition or {}).get("acquisition_sha256")
        ),
        "historical_strategy_activation_cell_count": int(
            historical_control_design.get("activation_cell_count") or 0
        ),
        "historical_strategy_pretrend_rankable_control_count": int(
            historical_control_design.get("pretrend_rankable_control_count") or 0
        ),
        "historical_strategy_bulk_corpus_sha256": historical_bulk_corpus.get(
            "corpus_sha256"
        ),
        "historical_strategy_bulk_event_count": int(
            historical_bulk_corpus.get("event_count") or 0
        ),
        "historical_strategy_supported_design_cell_count": int(
            historical_bulk_learning.get("supported_design_cell_count") or 0
        ),
        "historical_strategy_classified_event_count": int(
            historical_bulk_learning.get("classified_event_count") or 0
        ),
        "historical_strategy_document_queue_count": int(
            historical_bulk_learning.get("queue_count") or 0
        ),
        "historical_strategy_outcome_observation_count": int(
            historical_bulk_outcomes.get("observation_count") or 0
        ),
        "historical_strategy_outcome_covered_entity_count": int(
            historical_bulk_outcomes.get("covered_entity_count") or 0
        ),
        "historical_strategy_bulk_panel_readiness_sha256": (
            historical_bulk_panel_readiness.get("readiness_sha256")
        ),
        "historical_strategy_bulk_outcome_coverage_sha256": (
            historical_bulk_outcome_coverage.get("coverage_sha256")
        ),
        "historical_strategy_bulk_effect_diagnostics_sha256": (
            historical_bulk_effects.get("diagnostics_sha256")
        ),
        "historical_strategy_outcome_robustness_sha256": (
            historical_outcome_robustness.get("robustness_sha256")
        ),
        "strategy_path_shadow_sha256": strategy_path_shadow.get("shadow_sha256"),
        "strategy_path_shadow_status": strategy_path_shadow.get("status"),
        "strategy_path_shadow_move_count": int(
            strategy_path_shadow.get("move_count") or 0
        ),
        "strategy_path_shadow_forecast_count": int(
            strategy_path_shadow.get("forecast_count") or 0
        ),
        "strategy_event_research_queue_count": int(
            strategy_path_shadow.get("event_research_queue_count") or 0
        ),
        "strategy_event_research_acquisition_sha256": (
            (strategy_event_research_acquisition or {}).get("acquisition_sha256")
        ),
        "strategy_operating_forecast_count": int(
            strategy_path_shadow.get("operating_forecast_count") or 0
        ),
        "strategy_operating_settled_forecast_count": int(
            strategy_path_shadow.get("operating_settled_forecast_count") or 0
        ),
        "strategy_operating_tournament_status": (
            (strategy_path_shadow.get("operating_tournament") or {}).get("status")
        ),
        "strategy_operating_next_due_at": min((
            str((row.get("settlement_contract") or {}).get("not_before"))
            for row in strategy_path_shadow.get("operating_forecasts") or ()
            if (row.get("settlement_contract") or {}).get("not_before")
        ), default=None),
        "historical_strategy_law_search_sha256": (
            historical_law_search.get("law_search_sha256")
        ),
        "historical_strategy_law_trial_status": historical_law_trial.get("status"),
        "historical_strategy_law_trial_acquisition_queue_count": int(
            historical_bulk_learning.get("sealed_law_trial_holdout_queue_count") or 0
        ),
        "historical_strategy_law_trial_id": historical_bulk_learning.get(
            "sealed_law_trial_id"
        ),
        "historical_strategy_frozen_child_candidate_count": int(
            historical_law_search.get("frozen_child_candidate_count") or 0
        ),
        "historical_strategy_refinement_acquisition_count": int(
            historical_law_search.get("acquisition_frontier_count") or 0
        ),
        "historical_strategy_history_ready_event_count": int(
            historical_bulk_panel_readiness.get("history_ready_event_count") or 0
        ),
        "historical_strategy_group_time_ready_cell_count": int(
            historical_bulk_panel_readiness.get("group_time_ready_cell_count") or 0
        ),
        "causal_credit": {
            "granted": False,
            "boundary": (
                "Operating episodes remain descriptive until bounded controls, compatible "
                "pretrends, prospective holdouts, power, and multiplicity gates all pass."
            ),
        },
        "capital_authority": False,
    }
    clock = {**clock_body, "clock_sha256": stable_sha256(clock_body)}
    _atomic_json(
        root / "institutional_learning" / "strategy_business_clock" / "latest.json",
        clock,
    )
    return {
        **result,
        "strategy_transfer": transfer,
        "strategy_program_transfer": program_transfer,
        "strategy_program_control_acquisition": program_control_acquisition,
        "strategy_program_control_outcomes": program_control_outcomes,
        "strategy_program_comparison": program_comparison,
        "strategy_program_representation": strategy_program_representation,
        "strategy_law_induction": laws,
        "strategy_calibration_successors": strategy_calibration_successors,
        "strategy_valuation_bridge": strategy_valuation_bridge,
        "strategy_outcomes": outcomes,
        "strategy_outcome_source_plan": outcome_source_plan,
        "strategy_outcome_source_refresh": outcome_source_refresh,
        "strategy_program_outcomes": program_outcomes,
        "strategy_control_frontier": frontier,
        "strategy_control_binding": control_binding,
        "strategy_active_comparator": strategy_active_comparator,
        "strategy_state_control_acquisition": strategy_state_control_acquisition,
        "historical_strategy_event_replay": historical_replay,
        "historical_strategy_security_walk_forward": historical_security_walk_forward,
        "historical_strategy_representation_learning": (
            historical_strategy_representation_learning
        ),
        "historical_strategy_walk_forward": historical_walk_forward,
        "historical_strategy_event_acquisition": historical_acquisition,
        "historical_strategy_control_design": historical_control_design,
        "historical_strategy_control_acquisition": historical_control_acquisition,
        "historical_strategy_bulk_corpus": historical_bulk_corpus,
        "historical_strategy_bulk_learning": historical_bulk_learning,
        "historical_strategy_bulk_acquisition": historical_bulk_acquisition,
        "historical_strategy_bulk_semantic_resolution": historical_bulk_semantic_resolution,
        "historical_strategy_bulk_outcomes": historical_bulk_outcomes,
        "historical_strategy_bulk_outcome_coverage": historical_bulk_outcome_coverage,
        "historical_strategy_bulk_panel_readiness": historical_bulk_panel_readiness,
        "historical_strategy_bulk_effects": historical_bulk_effects,
        "historical_strategy_outcome_robustness": historical_outcome_robustness,
        "historical_strategy_law_search": historical_law_search,
        "historical_strategy_law_trial": historical_law_trial,
        "historical_strategy_bulk_retention": historical_bulk_retention,
        "strategy_path_shadow": strategy_path_shadow,
        "strategy_path_acquisition": strategy_path_acquisition,
        "strategy_path_semantic_resolution": strategy_path_semantic_resolution,
        "strategy_event_research_acquisition": strategy_event_research_acquisition,
        "strategy_business_clock": clock,
    }


def _compile_workspace_underwriting(root: Path) -> dict[str, Any]:
    result = compile_workspace_underwriting_index(root)
    immutable_path = root / "underwriting" / "indices" / (
        f"{result['underwriting_index_sha256']}.json"
    )
    if not immutable_path.is_file():
        _atomic_json(immutable_path, result)
    _atomic_json(root / "underwriting" / "latest.json", result)
    return result


def _capital_cycle_institutional_learning_ref(
    result: Mapping[str, Any],
) -> dict[str, Any]:
    """Keep the cycle boundary small while preserving the learning epoch identity."""

    state = dict(result.get("state") or {})
    clock = dict(result.get("strategy_business_clock") or {})
    return {
        "ok": result.get("ok"),
        "status": result.get("status"),
        "state": {"state_sha256": state.get("state_sha256")},
        "strategy_business_clock_sha256": clock.get("clock_sha256"),
        "artifact_path": "institutional_learning/latest.json",
        "strategy_business_clock_path": (
            "institutional_learning/strategy_business_clock/latest.json"
        ),
        "capital_authority": False,
    }


def _capital_cycle_underwriting_ref(result: Mapping[str, Any]) -> dict[str, Any]:
    """Reference the immutable index instead of copying every candidate into a cycle."""

    digest = str(result.get("underwriting_index_sha256") or "")
    return {
        key: result.get(key)
        for key in (
            "schema", "generated_at", "discovery_run_sha256", "candidate_count",
            "ranking_eligible_count", "underwriting_coordinate_complete_count",
            "conditional_payoff_aware_count", "forecast_return_aware_count",
            "state_price_aware_count", "rank_program_input_sha256",
            "underwriting_index_sha256", "authority", "capital_authority",
            "status", "error",
        )
        if result.get(key) is not None
    } | {
        "artifact_path": (
            f"underwriting/indices/{digest}.json" if len(digest) == 64
            else "underwriting/latest.json"
        ),
    }


def _compile_workspace_state_price_proposals(root: Path) -> dict[str, Any]:
    discovery_sha = str((_read_json(root / "discovery" / "latest.json") or {}).get("run_sha256") or "")
    cached = _read_json(root / "state_pricing" / "proposal-audit.json")
    if cached and cached.get("discovery_run_sha256") == discovery_sha:
        return cached
    result = audit_workspace_proposals(root)
    _atomic_json(root / "state_pricing" / "proposal-audit.json", result)
    return result


def _compile_workspace_modeled_payoff_grids(root: Path) -> dict[str, Any]:
    discovery_sha = str((_read_json(root / "discovery" / "latest.json") or {}).get("run_sha256") or "")
    cached = _read_json(root / "state_pricing" / "modeled-grid-audit.json")
    materialized = [
        root / str(row["artifact_path"])
        for row in (cached or {}).get("rows") or () if row.get("artifact_path")
    ]
    if (
        cached and cached.get("discovery_run_sha256") == discovery_sha
        and "grammar_learning" in cached and "residual_sets" in cached
        and materialized and all(path.is_file() for path in materialized)
    ):
        return cached
    result = audit_workspace_modeled_grids(root, materialize_limit=1)
    _atomic_json(root / "state_pricing" / "modeled-grid-audit.json", result)
    return result


def _compile_workspace_valuation_grammar_evaluations(
    root: Path, modeled_grid_audit: Mapping[str, Any],
) -> dict[str, Any]:
    discovery = _read_json(root / "discovery" / "latest.json")
    learning = modeled_grid_audit.get("grammar_learning")
    if not discovery or not isinstance(learning, Mapping):
        raise ValueError("valuation grammar evaluation requires current discovery and residual learning")
    result = schedule_valuation_grammar_evaluations(
        learning, discovery, scheduled_at=str(learning["compiled_at"]),
    )
    _atomic_json(root / "state_pricing" / "grammar-evaluation-schedule.json", result)
    return result


def _compile_workspace_allocation_readiness(
    root: Path, *, opportunity_book: Mapping[str, Any], underwriting_index: Mapping[str, Any],
    instrument_portfolio_admissions: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    result = compile_workspace_allocation_readiness(
        root, opportunity_book=opportunity_book, underwriting_index=underwriting_index,
        instrument_portfolio_admissions=instrument_portfolio_admissions,
    )
    _atomic_json(root / "allocation" / "latest.json", result)
    return result


def _auto_enroll_eligible_paper_watches(
    root: Path, *, policy: Mapping[str, Any],
    equity_audit: Mapping[str, Any], fund_audit: Mapping[str, Any],
    opportunity_book: Mapping[str, Any],
    activated_at: str,
) -> dict[str, Any]:
    """Apply the operator's standing zero-weight paper-watch policy."""

    enrollment = dict(policy.get("paper_watch_auto_enrollment") or {})
    enabled = bool(enrollment.get("enabled"))
    limit = int(enrollment.get("max_new_per_cycle") or 0)
    actor = str(enrollment.get("actor_id") or "")
    eligible = []
    for kind, audit in (("equity", equity_audit), ("fund", fund_audit)):
        for row in audit.get("rows") or ():
            proposal = row.get("proposal") if isinstance(row.get("proposal"), Mapping) else None
            if (
                proposal
                and row.get("activation_eligible") is True
                and not row.get("blockers")
                and proposal.get("activation_eligible") is True
                and not proposal.get("activation_blockers")
                and float((proposal.get("paper_policy") or {}).get("target_weight", -1)) == 0
            ):
                eligible.append({
                    "entity_kind": kind,
                    "entity_id": str(row.get("entity_id") or "").upper(),
                    "candidate_sha256": str(row.get("candidate_sha256") or ""),
                    "proposal": dict(proposal),
                })
    learned_order = {
        (
            str(row.get("entity_kind") or ""),
            str(row.get("entity_id") or "").upper(),
            str(row.get("candidate_sha256") or ""),
        ): (int(row["learned_research_rank"]), position)
        for position, row in enumerate(opportunity_book.get("candidates") or ())
        if row.get("learned_research_rank") is not None
    }
    for audit_position, candidate in enumerate(eligible):
        learned = learned_order.get((
            f"public_{candidate['entity_kind']}", candidate["entity_id"],
            candidate["candidate_sha256"],
        ))
        candidate["learned_research_rank"] = learned[0] if learned else None
        candidate["_selection_key"] = (
            (0, *learned, audit_position) if learned
            else (1, 10**9, audit_position, audit_position)
        )
    eligible.sort(key=lambda row: row["_selection_key"])
    existing = {
        _paper_watch_enrollment_identity(row)
        for row in _paper_watch_rows(root, include_inadmissible=True)
    }
    actions = []
    new_count = 0
    for selection_order, candidate in enumerate(eligible, start=1):
        kind = str(candidate["entity_kind"])
        entity_id = str(candidate["entity_id"])
        proposal = dict(candidate["proposal"])
        proposal_sha = str(proposal["proposal_sha256"])
        watch_identity = _paper_watch_enrollment_identity(proposal)
        ordering = {
            "selection_order": selection_order,
            "learned_research_rank": candidate["learned_research_rank"],
            "ordering_source": (
                "current_opportunity_book_learned_rank"
                if candidate["learned_research_rank"] is not None
                else "proposal_audit_fallback"
            ),
        }
        if watch_identity in existing:
            actions.append({
                "entity_id": entity_id, "entity_kind": kind,
                "proposal_sha256": proposal_sha, "status": "already_enrolled",
                **ordering,
            })
            continue
        if not enabled or new_count >= limit:
            actions.append({
                "entity_id": entity_id, "entity_kind": kind,
                "proposal_sha256": proposal_sha,
                "status": "policy_disabled" if not enabled else "budget_deferred",
                **ordering,
            })
            continue
        activate = (
            activate_workspace_equity_paper_watch
            if kind == "equity" else activate_workspace_fund_paper_watch
        )
        try:
            for attempt in range(2):
                try:
                    result = activate(
                        root, entity_id, proposal_sha256=proposal_sha,
                        confirmation=str(proposal["required_operator_confirmation"]),
                        operator_id=actor, activated_at=activated_at,
                    )
                    break
                except ValueError as error:
                    if attempt or "proposal hash is not current" not in str(error):
                        raise
                    audit_path = root / "paper_proposals" / (
                        "equities" if kind == "equity" else "funds"
                    ) / "latest.json"
                    current_audit = _read_json(audit_path) or {}
                    current_rows = [
                        row for row in current_audit.get("rows") or ()
                        if str(row.get("entity_id") or "").upper() == entity_id.upper()
                    ]
                    current_row = current_rows[0] if len(current_rows) == 1 else {}
                    current = current_row.get("proposal")
                    if (
                        not isinstance(current, Mapping)
                        or current_row.get("activation_eligible") is not True
                        or current_row.get("blockers")
                        or current.get("activation_eligible") is not True
                        or current.get("activation_blockers")
                        or float((current.get("paper_policy") or {}).get("target_weight", -1)) != 0
                    ):
                        raise
                    proposal = dict(current)
                    proposal_sha = str(proposal.get("proposal_sha256") or "")
            actions.append({
                "entity_id": entity_id, "entity_kind": kind,
                "proposal_sha256": proposal_sha, "status": result["status"],
                "artifact_path": result.get("artifact_path"),
                **ordering,
            })
            existing.add(watch_identity)
            new_count += int(result.get("status") == "activated_paper_watch")
        except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
            actions.append({
                "entity_id": entity_id, "entity_kind": kind,
                "proposal_sha256": proposal_sha, "status": "error",
                "error": f"{type(error).__name__}: {error}"[:1_000],
                **ordering,
            })
    body = {
        "schema": "jaggedthoughts-paper-watch-auto-enrollment-v1",
        "evaluated_at": canonical_timestamp(activated_at, "paper watch enrollment time"),
        "policy": enrollment,
        "opportunity_book_sha256": opportunity_book.get("book_sha256"),
        "selection_order": "learned_research_rank_then_proposal_audit_order",
        "eligible_count": len(eligible),
        "new_activation_count": new_count,
        "already_enrolled_count": sum(row["status"] == "already_enrolled" for row in actions),
        "deferred_count": sum(row["status"] in {"policy_disabled", "budget_deferred"} for row in actions),
        "error_count": sum(row["status"] == "error" for row in actions),
        "actions": actions,
        "target_weight": 0.0,
        "capital_authority": False,
        "portfolio_authority": False,
        "brokerage_authority": False,
    }
    return {**body, "enrollment_sha256": stable_sha256(body)}


def _open_capital_cycle_forecast(
    root: Path,
    *,
    owner: str,
    store_path: Path,
    policy: Mapping[str, Any],
    window: Mapping[str, Any],
    price_rows_by_entity: Mapping[str, tuple[dict[str, Any], ...]] | None = None,
) -> dict[str, Any]:
    paper_watch_id = (
        str(window["paper_watch_decision_id"])
        if window.get("paper_watch_decision_id") else None
    )
    opened = open_closed_book_forecast(
        root,
        owner=owner,
        store_path=store_path,
        decision_id=(str(window["decision_id"]) if window.get("decision_id") else None),
        paper_watch_decision_id=paper_watch_id,
        candidate_leaf=(
            str(window["candidate_leaf"])
            if window.get("candidate_leaf") and not paper_watch_id else None
        ),
        benchmark_id=str(policy.get("discovery_benchmark_id") or "SPY"),
        probe_weight=float(policy.get("discovery_probe_weight") or 0.05),
        horizon_days=int(window["horizon_days"]),
        strategy_experiment_nomination=(
            dict(window["strategy_experiment_nomination"])
            if isinstance(window.get("strategy_experiment_nomination"), Mapping) else None
        ),
        kernel_removal_trial=bool(window.get("kernel_removal_trial")),
        price_rows_by_entity=price_rows_by_entity,
    )
    candidate_ids = tuple(sorted({
        str(row.get("trial_family_id") or "")
        for row in opened.get("candidate_forecasts") or ()
        if isinstance(row, Mapping) and row.get("trial_family_id")
    }))
    search_trial_family = None
    if candidate_ids:
        search_trial_family = register_prospective_search_surface(
            root,
            owner=owner,
            trial_family_id=(
                f"closed-book:{int(opened['horizon_days'])}d:{stable_sha256(candidate_ids)}"
            ),
            research_question=(
                "Which frozen forecasting process best predicts later benchmark-relative "
                "return after the declared paper costs?"
            ),
            model_family="closed_book_world_models",
            selection_unit="forecast_model",
            candidate_ids=candidate_ids,
            declared_at=str(opened.get("sealed_at") or opened["opened_at"]),
            outcome_access_after=str(opened["end_at"]),
            generator_receipts=(f"closed-book-run:{opened['run_sha256']}",),
            source_refs=(str(opened["run_path"]),),
        )
    strategy_alpha_issuance = process_strategy_alpha_issuance_actions(
        root, run_ids=(str(opened["run_id"]),),
    )
    provider = dict(opened.get("provider") or {})
    return {
        **window,
        "status": "opened" if not opened.get("replayed") else "replayed",
        "ok": bool(opened.get("ok", True)),
        "run_id": opened.get("run_id"),
        "run_sha256": opened.get("run_sha256"),
        "opened_at": opened.get("opened_at"),
        "end_at": opened.get("end_at"),
        "run_path": opened.get("run_path"),
        "provider_called": bool(provider.get("called")),
        "provider_error": provider.get("error"),
        "search_trial_family": search_trial_family,
        "strategy_alpha_issuance": strategy_alpha_issuance,
    }


def _schedule_kernel_removal_trial(
    root: Path, windows: list[dict[str, Any]], policy: Mapping[str, Any], *, now: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Reserve at most one non-overlapping paper-watch window for deletion evidence."""
    config = dict(policy.get("kernel_removal_trial") or {})
    horizon = int(config.get("horizon_days") or 90)
    maximum = int(config.get("maximum_independent_blocks") or 8)
    runs = [
        row for path in sorted((root / "closed_book" / "runs").glob("*.json"))
        if (row := _read_json(path))
        and (row.get("kernel_removal_trial") or {}).get("status")
        == "sealed_four_arm_forecast"
        and ((row.get("kernel_removal_trial") or {}).get("execution_receipt") or {})
        .get("execution_complete") is True
        and int(row.get("horizon_days") or 0) == horizon
    ]
    open_runs = [row for row in runs if timestamp_key(str(row["end_at"])) > timestamp_key(now)]
    body = {
        "schema": "jaggedthoughts-kernel-removal-schedule-v1",
        "enabled": bool(config.get("enabled")),
        "horizon_days": horizon,
        "sealed_block_count": len(runs),
        "maximum_independent_blocks": maximum,
        "open_block_count": len(open_runs),
        "selected_entity_id": None,
        "status": "disabled",
        "capital_authority": False,
    }
    if not body["enabled"]:
        return windows, {**body, "schedule_sha256": stable_sha256(body)}
    if len(runs) >= maximum:
        body["status"] = "cohort_full"
        return windows, {**body, "schedule_sha256": stable_sha256(body)}
    if open_runs:
        body["status"] = "awaiting_nonoverlapping_window"
        return windows, {**body, "schedule_sha256": stable_sha256(body)}
    used = {
        str((row.get("evidence_packet") or {}).get("entity", {}).get("entity_id") or "")
        for row in runs
    }
    eligible = [
        (index, row) for index, row in enumerate(windows)
        if row.get("paper_watch_decision_id")
        and int(row.get("horizon_days") or 0) == horizon
    ]
    if not eligible:
        body["status"] = "awaiting_due_paper_watch"
        return windows, {**body, "schedule_sha256": stable_sha256(body)}
    index, selected = min(eligible, key=lambda pair: (
        str(pair[1].get("entity_id") or "") in used,
        stable_sha256({
            "entity_id": str(pair[1].get("entity_id") or ""),
            "cohort": "kernel_removal",
        }),
    ))
    windows[index] = {**selected, "kernel_removal_trial": True}
    body["status"] = "trial_window_reserved"
    body["selected_entity_id"] = selected.get("entity_id")
    return windows, {**body, "schedule_sha256": stable_sha256(body)}


def run_workspace_capital_cycle(
    workspace: str | Path | None = None, *, force: bool = False,
) -> dict[str, Any]:
    """Run one paper-capital cycle over the latest immutable input epochs."""

    root, config = load_workspace_config(workspace)
    policy_path = root / str(config.get("capital_cycle_policy") or "capital_cycle.yaml")
    policy = load_capital_cycle_policy(policy_path)
    if _composite_epoch_transition_pending(root):
        return {
            "schema": "jaggedthoughts-capital-cycle-action-v1",
            "ok": True,
            "status": "awaiting_completed_discovery_epoch",
            "capital_authority": False,
        }
    status = capital_cycle_status(
        root, policy_path=policy_path,
        owner=str(config.get("owner") or "operator-paper-book"),
        store_path=_store_path(root, config),
    )
    if not bool(policy.get("enabled")):
        return {
            "schema": "jaggedthoughts-capital-cycle-action-v1",
            "ok": True,
            "status": "disabled",
            "capital_cycle": status,
            "capital_authority": False,
        }
    latest_run = status.get("latest_run")
    latest_book = status.get("latest_book")
    if isinstance(latest_run, Mapping) and isinstance(latest_book, Mapping):
        owner = str(config.get("owner") or "operator-paper-book")
        try:
            GoldenStore(_store_path(root, config)).head(
                owner, "capital_cycle_run", str(latest_run["cycle_id"]),
            )
        except KeyError:
            record = _record_capital_cycle_bundle(
                root, config, run=latest_run, book=latest_book,
            )
            read_model = build_read_model(root)
            _atomic_json(root / "state" / "read_model.json", read_model)
            return {
                "schema": "jaggedthoughts-capital-cycle-action-v1",
                "ok": True,
                "status": "recovered_uncommitted_cycle",
                "forced": force,
                "run": dict(latest_run),
                "opportunity_book": dict(latest_book),
                "golden_record": record,
                "read_model": read_model,
                "capital_authority": False,
            }
    if not force and not bool(status.get("due")):
        return {
            "schema": "jaggedthoughts-capital-cycle-action-v1",
            "ok": True,
            "status": "not_due",
            "capital_cycle": status,
            "capital_authority": False,
        }
    with _CAPITAL_CYCLE_LOCK:
        started_at = _utc_now()
        owner = str(config.get("owner") or "operator-paper-book")
        store_path = _store_path(root, config)
        walk_forward_profile = (
            root / "point_in_time_replay" / "sealed_walk_forward_seed.json"
        )
        try:
            sealed_walk_forward = (
                run_sealed_walk_forward_cycle(
                    root, walk_forward_profile, as_of=started_at,
                    owner=owner, store_path=store_path,
                )
                if walk_forward_profile.is_file() else {
                    "ok": True, "status": "profile_missing",
                    "capital_authority": False,
                }
            )
        except (KeyError, OSError, TypeError, ValueError) as error:
            sealed_walk_forward = {
                "ok": False, "status": "error",
                "error": f"{type(error).__name__}: {error}"[:1_000],
                "capital_authority": False,
            }
        settlement = settle_due_closed_book_forecasts(
            root, owner=owner, store_path=store_path,
        )
        try:
            research_question_policy_outcomes = (
                _advance_research_question_policy_outcomes(root, as_of=started_at)
            )
        except (KeyError, OSError, TypeError, ValueError) as error:
            research_question_policy_outcomes = {
                "schema": "jaggedthoughts-research-question-policy-outcome-cycle-v1",
                "status": "error",
                "error": f"{type(error).__name__}: {error}"[:1_000],
                "capital_authority": False,
            }
        portfolio_policy_settlement = settle_portfolio_policy_tournaments(
            root, owner=owner, store_path=store_path,
        )
        household_policy_settlement = settle_household_policy_tournaments(
            root, owner=owner, store_path=store_path,
        )
        rank_program_settlement = settle_rank_program_tournaments(
            root, owner=owner, store_path=store_path,
        )
        market_state_source_run = None
        if bool((status.get("market_state_due") or {}).get("source_refresh_required")):
            market_state_source_run = _refresh_market_state_sources(root, config)
        market_state = _run_market_state_cycle_action(
            root, config, policy, force=False,
        )
        market_state["source_refresh"] = market_state_source_run
        source_epoch = current_source_epoch(root)
        source_epoch_ref = None if source_epoch is None else {
            "source_epoch_sha256": source_epoch["source_epoch_sha256"],
            "source_run_sha256": source_epoch["source_run"]["sha256"],
            "as_of": source_epoch["as_of"],
        }
        due = list(due_forecast_windows(root, policy=policy))
        budget = int(policy.get("max_new_forecast_episodes_per_cycle") or 0)
        strategy_alpha_schedule = schedule_strategy_alpha_prospective_episodes(
            root,
            base_windows=due,
            policy=policy,
            budget=budget,
        )
        ready_windows = []
        strategy_alpha_preopen_actions = []
        preopen_deferred = []
        for window in strategy_alpha_schedule["scheduled_windows"]:
            nomination = window.get("strategy_experiment_nomination")
            if not isinstance(nomination, Mapping):
                ready_windows.append(window)
                continue
            try:
                receipt = ensure_strategy_alpha_issuance_action(root, nomination)
                strategy_alpha_preopen_actions.append(receipt)
                ready_windows.append({**window, "strategy_alpha_preopen_action": receipt})
            except Exception as error:  # noqa: BLE001 - preserve independent base forecast lanes.
                deferred = {
                    **window, "status": "deferred_preopen_action",
                    "ok": False,
                    "error": f"{type(error).__name__}: {error}"[:1_000],
                    "capital_authority": False,
                }
                strategy_alpha_preopen_actions.append(deferred)
                preopen_deferred.append(deferred)
        ready_windows, kernel_removal_schedule = _schedule_kernel_removal_trial(
            root, ready_windows, policy, now=started_at,
        )
        forecast_actions: list[dict[str, Any]] = []
        forecast_prices = _price_rows_by_entity(
            root,
            {
                str(window.get("entity_id") or "").upper()
                for window in ready_windows
            } | {str(policy.get("discovery_benchmark_id") or "SPY").upper()},
            as_of=_utc_now(),
        )
        for window in ready_windows:
            try:
                forecast_actions.append(_open_capital_cycle_forecast(
                    root,
                    owner=owner,
                    store_path=store_path,
                    policy=policy,
                    window=window,
                    price_rows_by_entity=forecast_prices,
                ))
            except Exception as error:  # noqa: BLE001 - a cycle preserves partial lane failures.
                forecast_actions.append({
                    **window,
                    "status": "error",
                    "ok": False,
                    "error": f"{type(error).__name__}: {error}"[:1_000],
                })
        try:
            institutional_learning = _advance_workspace_strategy_business_clock(
                root, config, acquire_historical_sources=True,
            )
        except (
            KeyError, OSError, RuntimeError, TypeError, ValueError, yaml.YAMLError,
        ) as error:
            institutional_learning = {
                "ok": False,
                "status": "error",
                "error": f"{type(error).__name__}: {error}"[:1_000],
                "capital_authority": False,
            }
        current_epoch_after_learning = current_source_epoch(root)
        current_epoch_after_learning_sha = (
            current_epoch_after_learning or {}
        ).get("source_epoch_sha256")
        opened_epoch_sha = (source_epoch_ref or {}).get("source_epoch_sha256")
        if current_epoch_after_learning_sha != opened_epoch_sha:
            return {
                "schema": "jaggedthoughts-capital-cycle-action-v1",
                "ok": True,
                "status": "awaiting_completed_discovery_epoch",
                "reason": "public source epoch advanced during institutional learning",
                "opened_source_epoch": source_epoch_ref,
                "current_source_epoch": (
                    None if current_epoch_after_learning is None else {
                        "source_epoch_sha256": current_epoch_after_learning_sha,
                        "source_run_sha256": (
                            current_epoch_after_learning.get("source_run") or {}
                        ).get("sha256"),
                        "as_of": current_epoch_after_learning.get("as_of"),
                    }
                ),
                "forecast_actions": forecast_actions,
                "kernel_removal_schedule": kernel_removal_schedule,
                "institutional_learning": _capital_cycle_institutional_learning_ref(
                    institutional_learning,
                ),
                "capital_authority": False,
            }
        try:
            strategy_dual_outcomes = compile_strategy_dual_outcome_episodes(root)
            _atomic_json(
                root / "institutional_learning" / "strategy_dual_outcomes" / "latest.json",
                strategy_dual_outcomes,
            )
        except (OSError, TypeError, ValueError) as error:
            strategy_dual_outcomes = {
                "schema": "jaggedthoughts-strategy-dual-outcome-episodes-v1",
                "status": "error",
                "error": f"{type(error).__name__}: {error}"[:1_000],
                "capital_authority": False,
            }
        completed_at = _utc_now()
        try:
            state_price_proposals = _compile_workspace_state_price_proposals(root)
        except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
            state_price_proposals = {
                "ok": False,
                "status": "error",
                "error": f"{type(error).__name__}: {error}"[:1_000],
                "capital_authority": False,
            }
        try:
            modeled_payoff_grids = _compile_workspace_modeled_payoff_grids(root)
        except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
            modeled_payoff_grids = {
                "status": "error",
                "error": f"{type(error).__name__}: {error}"[:1_000],
                "capital_authority": False,
            }
        try:
            underwriting = _compile_workspace_underwriting(root)
        except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
            underwriting = {
                "ok": False,
                "status": "error",
                "error": f"{type(error).__name__}: {error}"[:1_000],
                "capital_authority": False,
            }
        try:
            valuation_grammar_evaluations = _compile_workspace_valuation_grammar_evaluations(
                root, modeled_payoff_grids,
            )
        except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
            valuation_grammar_evaluations = {
                "status": "error",
                "error": f"{type(error).__name__}: {error}"[:1_000],
                "capital_authority": False,
            }
        try:
            equity_paper_proposals = compile_workspace_equity_proposals(
                root, compiled_at=completed_at,
            )
            _atomic_json(
                root / "paper_proposals" / "equities" / "latest.json",
                equity_paper_proposals,
            )
        except (FileNotFoundError, KeyError, OSError, TypeError, ValueError, yaml.YAMLError) as error:
            equity_paper_proposals = {
                "status": "error",
                "error": f"{type(error).__name__}: {error}"[:1_000],
                "capital_authority": False,
            }
        try:
            fund_paper_proposals = compile_workspace_fund_proposals(
                root, compiled_at=completed_at,
            )
            _atomic_json(
                root / "paper_proposals" / "funds" / "latest.json",
                fund_paper_proposals,
            )
        except (FileNotFoundError, KeyError, OSError, TypeError, ValueError, yaml.YAMLError) as error:
            fund_paper_proposals = {
                "status": "error",
                "error": f"{type(error).__name__}: {error}"[:1_000],
                "capital_authority": False,
            }
        book = compile_opportunity_book(root, policy=policy, generated_at=completed_at)
        book_path = root / "opportunity_books" / (
            f"{book['book_id']}-{str(book['book_sha256'])[:10]}.json"
        )
        try:
            preopen_sleeve_implementation = (
                compile_workspace_sleeve_implementation_frontier(root)
            )
            preopen_instrument_admissions = (
                compile_workspace_instrument_portfolio_admissions(
                    root, sleeve_implementation=preopen_sleeve_implementation,
                    compiled_at=completed_at,
                )
            )
        except (FileNotFoundError, KeyError, OSError, TypeError, ValueError):
            preopen_instrument_admissions = None
        try:
            fund_program_tournament_input = compile_workspace_fund_sleeve_comparison(
                root,
            ).get("portfolio_policy_tournament_input")
        except (FileNotFoundError, KeyError, OSError, TypeError, ValueError):
            fund_program_tournament_input = None
        try:
            portfolio_policy_open = open_portfolio_policy_tournament(
                root,
                owner=owner,
                store_path=store_path,
                opportunity_book=book,
                horizon_days=int(policy["portfolio_policy_horizon_days"]),
                benchmark_id=str(policy.get("discovery_benchmark_id") or "SPY"),
                generated_at=completed_at,
                gross_weight=float(policy["portfolio_policy_gross_weight"]),
                max_position_weight=float(policy["portfolio_policy_max_position_weight"]),
                risk_aversion=float(
                    policy["portfolio_policy_diagnostic_risk_aversion"]
                ),
                portfolio_assembly=_read_json(root / "portfolio" / "latest_assembly.json"),
                fund_program_tournament_input=fund_program_tournament_input,
                paper_proposal_audits=tuple(
                    audit for audit in (equity_paper_proposals, fund_paper_proposals)
                    if audit.get("audit_sha256")
                ),
                instrument_portfolio_admissions=preopen_instrument_admissions,
            )
            policy_candidate_ids = tuple(sorted(
                f"{row['policy_id']}@{row.get('version') or '1'}"
                for row in portfolio_policy_open.get("policies") or ()
                if isinstance(row, Mapping) and row.get("policy_id")
            ))
            if policy_candidate_ids:
                portfolio_policy_open = {
                    **portfolio_policy_open,
                    "search_trial_family": register_prospective_search_surface(
                        root,
                        owner=owner,
                        trial_family_id=str(
                            (portfolio_policy_open.get("trial_family") or {})["trial_family_id"]
                        ),
                        research_question=(
                            "Which complete paper-allocation policy improves later after-cost "
                            "portfolio excess return and security selection?"
                        ),
                        model_family="portfolio_policy",
                        selection_unit="complete_portfolio_policy",
                        candidate_ids=policy_candidate_ids,
                        declared_at=str(portfolio_policy_open["opened_at"]),
                        outcome_access_after=str(portfolio_policy_open["end_at"]),
                        generator_receipts=(
                            f"portfolio-policy-run:{portfolio_policy_open['run_sha256']}",
                        ),
                        source_refs=(
                            str(portfolio_policy_open.get("run_path") or (
                                f"portfolio_policy/runs/{portfolio_policy_open['run_id']}.json"
                            )),
                        ),
                    ),
                }
        except ValueError as error:
            portfolio_policy_open = {
                "ok": True, "status": "unavailable",
                "reason": str(error)[:1_000],
                "capital_authority": False,
            }
        except (FileNotFoundError, KeyError, OSError, TypeError) as error:
            portfolio_policy_open = {
                "ok": False, "status": "error",
                "error": f"{type(error).__name__}: {error}"[:1_000],
                "capital_authority": False,
            }
        try:
            paper_watch_auto_enrollment = _auto_enroll_eligible_paper_watches(
                root, policy=policy,
                equity_audit=equity_paper_proposals,
                fund_audit=fund_paper_proposals,
                opportunity_book=book,
                activated_at=completed_at,
            )
        except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
            paper_watch_auto_enrollment = {
                "schema": "jaggedthoughts-paper-watch-auto-enrollment-v1",
                "status": "error",
                "error": f"{type(error).__name__}: {error}"[:1_000],
                "capital_authority": False,
                "portfolio_authority": False,
                "brokerage_authority": False,
            }
        try:
            sleeve_implementation_frontier = compile_workspace_sleeve_implementation_frontier(root)
            fund_sleeve_comparison = compile_workspace_fund_sleeve_comparison(
                root, sleeve_implementation=sleeve_implementation_frontier,
            )
            _atomic_json(
                root / "portfolio" / "fund_sleeve_comparison" / "latest.json",
                fund_sleeve_comparison,
            )
        except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
            fund_sleeve_comparison = {
                "schema": "jaggedthoughts-fund-sleeve-comparison-v1",
                "status": "error", "sleeves": [],
                "error": f"{type(error).__name__}: {error}"[:1_000],
                "allocation_selected": False, "capital_authority": False,
                "brokerage_authority": False,
            }
        try:
            instrument_portfolio_admissions = (
                compile_workspace_instrument_portfolio_admissions(
                    root, sleeve_implementation=sleeve_implementation_frontier,
                    compiled_at=completed_at,
                )
            )
            _atomic_json(
                root / "portfolio" / "instrument_admissions" / "latest.json",
                instrument_portfolio_admissions,
            )
        except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
            instrument_portfolio_admissions = {
                "schema": "jaggedthoughts-workspace-instrument-portfolio-admissions-v1",
                "status": "error", "watch_count": 0, "admitted_count": 0,
                "blocked_count": 0, "error_count": 1, "admissions": [],
                "errors": [{"message": f"{type(error).__name__}: {error}"[:1_000]}],
                "capital_authority": False, "brokerage_authority": False,
                "order_routing_allowed": False,
            }
        try:
            allocation_readiness = _compile_workspace_allocation_readiness(
                root, opportunity_book=book, underwriting_index=underwriting,
                instrument_portfolio_admissions=instrument_portfolio_admissions,
            )
        except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
            allocation_readiness = {
                "status": "error",
                "error": f"{type(error).__name__}: {error}"[:1_000],
                "capital_authority": False,
            }
        run_identity = {
            "started_at": started_at,
            "completed_at": completed_at,
            "source_epoch_sha256": (
                source_epoch_ref or {}
            ).get("source_epoch_sha256"),
            "discovery_run_sha256": book["discovery_run_sha256"],
            "opportunity_book_sha256": book["book_sha256"],
            "forecast_runs": [row.get("run_id") for row in forecast_actions],
            "strategy_alpha_action_sha256s": [
                row.get("action_sha256") for row in strategy_alpha_preopen_actions
                if row.get("action_sha256")
            ],
            "strategy_alpha_schedule_sha256": strategy_alpha_schedule["schedule_sha256"],
            "kernel_removal_schedule_sha256": kernel_removal_schedule["schedule_sha256"],
            "settlement_evaluated_at": settlement.get("evaluated_at"),
            "research_question_policy_outcome_cycle_sha256": (
                research_question_policy_outcomes.get("cycle_sha256")
            ),
            "market_state_forecast_runs": [
                row.get("run_id") for row in market_state.get("forecast_actions") or ()
            ],
            "institutional_learning_sha256": (
                (institutional_learning.get("state") or {}).get("state_sha256")
            ),
            "strategy_dual_outcomes_sha256": strategy_dual_outcomes.get("index_sha256"),
            "portfolio_policy_run_id": portfolio_policy_open.get("run_id"),
            "portfolio_policy_settlement_at": portfolio_policy_settlement.get("evaluated_at"),
            "household_policy_settlement_at": household_policy_settlement.get("evaluated_at"),
            "fund_sleeve_comparison_sha256": fund_sleeve_comparison.get(
                "fund_sleeve_comparison_sha256"
            ),
            "instrument_portfolio_admissions_sha256": (
                instrument_portfolio_admissions.get("workspace_admissions_sha256")
            ),
            "paper_watch_enrollment_sha256": paper_watch_auto_enrollment.get(
                "enrollment_sha256"
            ),
            "sealed_walk_forward_run_sha256": (
                (sealed_walk_forward.get("run") or {}).get("run_sha256")
            ),
            "sealed_walk_forward_status_sha256": (
                (sealed_walk_forward.get("matrix_status") or {}).get("status_sha256")
            ),
        }
        cycle_id = f"capital-cycle-{stable_sha256(run_identity)[:20]}"
        run_body = {
            "schema": CAPITAL_CYCLE_RUN_SCHEMA,
            "cycle_id": cycle_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "source_epoch": source_epoch_ref,
            "discovery_run_id": book["discovery_run_id"],
            "discovery_run_sha256": book["discovery_run_sha256"],
            "policy_sha256": policy["policy_sha256"],
            "settlement": settlement,
            "research_question_policy_outcomes": research_question_policy_outcomes,
            "due_forecast_window_count": len(due),
            "forecast_budget": budget,
            "forecast_actions": forecast_actions,
            "strategy_alpha_schedule": strategy_alpha_schedule,
            "kernel_removal_schedule": kernel_removal_schedule,
            "strategy_alpha_preopen_actions": strategy_alpha_preopen_actions,
            "market_state": market_state,
            "institutional_learning": _capital_cycle_institutional_learning_ref(
                institutional_learning,
            ),
            "strategy_dual_outcomes": strategy_dual_outcomes,
            "sealed_walk_forward": sealed_walk_forward,
            "underwriting": _capital_cycle_underwriting_ref(underwriting),
            "state_price_proposals": state_price_proposals,
            "modeled_payoff_grids": modeled_payoff_grids,
            "valuation_grammar_evaluations": valuation_grammar_evaluations,
            "allocation_readiness": allocation_readiness,
            "equity_paper_proposals": equity_paper_proposals,
            "fund_paper_proposals": fund_paper_proposals,
            "paper_watch_auto_enrollment": paper_watch_auto_enrollment,
            "fund_sleeve_comparison": fund_sleeve_comparison,
            "instrument_portfolio_admissions": instrument_portfolio_admissions,
            "portfolio_policy": {
                "settlement": portfolio_policy_settlement,
                "open": portfolio_policy_open,
            },
            "household_policy_tournament": {
                "settlement": household_policy_settlement,
                "status": household_policy_tournament_status(root),
            },
            "rank_program_tournament": {
                "settlement": rank_program_settlement,
                "status": rank_program_tournament_status(root),
            },
            "deferred_forecast_windows": [
                *strategy_alpha_schedule["deferred_base_windows"],
                *strategy_alpha_schedule["deferred_experiment_windows"],
                *preopen_deferred,
            ],
            "opportunity_book_id": book["book_id"],
            "opportunity_book_sha256": book["book_sha256"],
            "opportunity_book_path": book_path.relative_to(root).as_posix(),
            "paper_posture": book["paper_posture"],
            "next_action": book["next_action"],
            "authority": "paper_shadow",
            "capital_authority": False,
        }
        run = {**run_body, "run_sha256": stable_sha256(run_body)}
        run_path = root / "capital_cycles" / f"{cycle_id}.json"
        current_epoch = current_source_epoch(root)
        current_epoch_sha = (current_epoch or {}).get("source_epoch_sha256")
        if current_epoch_sha != (source_epoch_ref or {}).get("source_epoch_sha256"):
            raise RuntimeError("public source epoch changed during capital-cycle compilation")
        _atomic_json(book_path, book)
        _atomic_json(run_path, run)
        record = _record_capital_cycle_bundle(root, config, run=run, book=book)
        _atomic_json(root / "opportunity_books" / "latest.json", book)
        _atomic_json(root / "capital_cycles" / "latest.json", run)
        read_model = build_read_model(root)
        _atomic_json(root / "state" / "read_model.json", read_model)
        provider_failures = (
            sum(not bool(row.get("ok")) for row in forecast_actions)
            + sum(not bool(row.get("ok")) for row in preopen_deferred)
            + sum(row.get("status") == "error" for row in market_state.get("forecast_actions") or ())
            + int(bool(market_state_source_run) and not bool(market_state_source_run.get("ok")))
            + int(not bool(institutional_learning.get("ok")))
            + int(underwriting.get("status") == "error")
            + int(state_price_proposals.get("status") == "error")
            + int(modeled_payoff_grids.get("status") == "error")
            + int(valuation_grammar_evaluations.get("status") == "error")
            + int(allocation_readiness.get("status") == "error")
            + int(equity_paper_proposals.get("status") == "error")
            + int(fund_paper_proposals.get("status") == "error")
            + int(paper_watch_auto_enrollment.get("status") == "error")
            + int(fund_sleeve_comparison.get("status") == "error")
            + int(instrument_portfolio_admissions.get("status") == "error")
            + int(not bool(portfolio_policy_open.get("ok")))
            + int(sealed_walk_forward.get("status") == "error")
        )
        return {
            "schema": "jaggedthoughts-capital-cycle-action-v1",
            "ok": True,
            "status": "completed_with_forecast_errors" if provider_failures else "completed",
            "forced": force,
            "run": run,
            "run_path": run_path.relative_to(root).as_posix(),
            "opportunity_book": book,
            "golden_record": record,
            "read_model": read_model,
            "capital_authority": False,
        }


def _terminal_market_flow_successors(value: Any) -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}

    def visit(node: Any) -> None:
        if isinstance(node, Mapping):
            if (
                node.get("schema") == SUCCESSOR_RESULT_SCHEMA
                and node.get("status") in {
                    "typed_failure", "screen_rejected", "admission_candidate",
                }
            ):
                digest = str(node.get("successor_result_sha256") or "")
                if digest:
                    found[digest] = dict(node)
            for child in node.values():
                visit(child)
        elif isinstance(node, (list, tuple)):
            for child in node:
                visit(child)

    visit(value)
    return [found[digest] for digest in sorted(found)]


def _run_registered_market_flow_shadows(
    root: Path, config: Mapping[str, Any], *, as_of: str,
) -> dict[str, Any]:
    rows = []
    for registration in config.get("research_projects") or ():
        if not isinstance(registration, Mapping):
            continue
        lifecycle = registration.get("prospective_lifecycle")
        if not isinstance(lifecycle, Mapping) or lifecycle.get("kind") != (
            "cross_sectional_market_flow_shadow"
        ):
            continue
        project_id = str(registration.get("project_id") or "unknown")
        try:
            project_root = root / str(registration["path"])
            status = run_market_flow_shadow_cycle(
                profile_path=root / str(lifecycle["profile"]),
                workspace=root,
                project_dir=project_root,
                as_of=as_of,
                owner=str(config.get("owner") or "operator-paper-book"),
                min_inference_blocks=int(lifecycle.get("min_inference_blocks") or 8),
            )
            memory_rows = []
            for successor in _terminal_market_flow_successors(status):
                try:
                    result = compile_market_flow_successor_memory(successor)
                    leaf = record_mechanism_research_result(
                        GoldenStore(_store_path(root, config)),
                        owner=str(config.get("owner") or "operator-paper-book"),
                        result=result,
                    )
                    memory_rows.append({
                        "status": "recorded",
                        "terminal_status": successor["status"],
                        "successor_result_sha256": successor[
                            "successor_result_sha256"
                        ],
                        "research_result_sha256": result[
                            "research_result_sha256"
                        ],
                        "golden_leaf": leaf,
                        "capital_authority": False,
                    })
                except (KeyError, OSError, TypeError, ValueError) as error:
                    memory_rows.append({
                        "status": "blocked_result_projection",
                        "successor_result_sha256": successor.get(
                            "successor_result_sha256"
                        ),
                        "error": f"{type(error).__name__}: {error}"[:500],
                        "capital_authority": False,
                    })
            status = {
                **status,
                "institutional_memory": {
                    "schema": "jaggedthoughts-market-flow-research-memory-write-v1",
                    "terminal_result_count": len(memory_rows),
                    "recorded_count": sum(
                        row["status"] == "recorded" for row in memory_rows
                    ),
                    "rows": memory_rows,
                    "predictive_law_authority": False,
                    "paper_policy_authority": False,
                    "capital_authority": False,
                },
            }
            _atomic_json(
                project_root / "workspace" / "prospective_shadow" / "latest.json",
                status,
            )
            rows.append({"project_id": project_id, "ok": True, **status})
        except (KeyError, OSError, TypeError, ValueError) as error:
            rows.append({
                "project_id": project_id,
                "ok": False,
                "status": "error",
                "error": f"{type(error).__name__}: {error}"[:1_000],
                "paper_policy_authority": False,
                "capital_authority": False,
            })
    return {
        "schema": "jaggedthoughts-registered-market-flow-shadows-v1",
        "as_of": as_of,
        "project_count": len(rows),
        "projects": rows,
        "paper_policy_authority": False,
        "capital_authority": False,
    }


def run_workspace_capital_cycle_service(
    workspace: str | Path | None = None,
    *,
    poll_seconds: float | None = None,
    once: bool = False,
    stop_event: Event | None = None,
) -> dict[str, Any]:
    """Maintain event-driven capital-cycle due checks with a visible heartbeat."""

    root, config = load_workspace_config(workspace)
    policy = load_capital_cycle_policy(
        root / str(config.get("capital_cycle_policy") or "capital_cycle.yaml")
    )
    cadence = float(poll_seconds if poll_seconds is not None else policy["poll_seconds"])
    if cadence < 5 and not once:
        raise ValueError("capital-cycle service poll_seconds must be at least five")
    stopper = stop_event or Event()
    started_at = _utc_now()
    heartbeat: dict[str, Any] = {}
    while not stopper.is_set():
        checked_at = _utc_now()
        heartbeat = {
            "schema": "jaggedthoughts-capital-cycle-service-v1",
            "ok": True,
            "status": "checking_due_work",
            "started_at": started_at,
            "checked_at": checked_at,
            "pid": os.getpid(),
            "starter": "forensic_workbench_server_or_investment_cli",
            "stops_with_process": True,
            "poll_seconds": cadence,
            "capital_authority": False,
        }
        _atomic_json(root / "state" / "capital_cycle_service.json", heartbeat)
        source_refreshing = False
        source_lock = root / "state" / "source_refresh.lock"
        source_lock.parent.mkdir(parents=True, exist_ok=True)
        with source_lock.open("a+b") as source_handle:
            try:
                fcntl.flock(source_handle.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
                fcntl.flock(source_handle.fileno(), fcntl.LOCK_UN)
            except BlockingIOError:
                source_refreshing = True
        if source_refreshing:
            heartbeat = {
                **heartbeat,
                "status": "waiting_for_source_refresh",
                "last_action": "capital_cycle_deferred_until_source_epoch_is_atomic",
            }
            _atomic_json(root / "state" / "capital_cycle_service.json", heartbeat)
            if once:
                return heartbeat
            stopper.wait(cadence)
            continue
        try:
            try:
                path_action = settle_workspace_company_state_path_action(root)
            except (OSError, TypeError, ValueError) as error:
                path_action = {
                    "status": "error", "error": f"{type(error).__name__}: {error}"[:1_000],
                    "capital_authority": False,
                }
            market_flow_shadows = _run_registered_market_flow_shadows(
                root, config, as_of=checked_at,
            )
            heartbeat = {
                **heartbeat,
                "status": "running_capital_cycle",
                "last_action": "settle_then_open_due_prospective_episodes",
                "company_state_path_action": path_action,
                "market_flow_shadows": market_flow_shadows,
            }
            _atomic_json(root / "state" / "capital_cycle_service.json", heartbeat)
            action = run_workspace_capital_cycle(root, force=False)
            latest = action.get("run") or ((action.get("capital_cycle") or {}).get("latest_run") or {})
            heartbeat = {
                "schema": "jaggedthoughts-capital-cycle-service-v1",
                "ok": True,
                "status": "checked_once" if once else "running",
                "started_at": started_at,
                "checked_at": checked_at,
                "pid": os.getpid(),
                "starter": "forensic_workbench_server_or_investment_cli",
                "stops_with_process": True,
                "poll_seconds": cadence,
                "last_action": action.get("status"),
                "last_cycle_id": latest.get("cycle_id") if isinstance(latest, Mapping) else None,
                "sealed_walk_forward": (
                    latest.get("sealed_walk_forward")
                    if isinstance(latest, Mapping) else None
                ),
                "company_state_path_action": path_action,
                "market_flow_shadows": market_flow_shadows,
                "capital_authority": False,
            }
        except Exception as error:  # noqa: BLE001 - heartbeat exposes retryable service failure.
            heartbeat = {
                "schema": "jaggedthoughts-capital-cycle-service-v1",
                "ok": False,
                "status": "error",
                "started_at": started_at,
                "checked_at": checked_at,
                "pid": os.getpid(),
                "starter": "forensic_workbench_server_or_investment_cli",
                "stops_with_process": True,
                "poll_seconds": cadence,
                "error": f"{type(error).__name__}: {error}"[:1_000],
                "capital_authority": False,
            }
        _atomic_json(root / "state" / "capital_cycle_service.json", heartbeat)
        if once:
            return heartbeat
        stopper.wait(cadence)
    heartbeat = {**heartbeat, "status": "stopped", "stopped_at": _utc_now()}
    _atomic_json(root / "state" / "capital_cycle_service.json", heartbeat)
    return heartbeat


def start_workspace_capital_cycle_service(
    workspace: str | Path | None = None, *, poll_seconds: float | None = None,
) -> Thread:
    """Start at most one capital-cycle due-check thread in the current process."""

    global _CAPITAL_CYCLE_SERVICE
    if _CAPITAL_CYCLE_SERVICE is not None and _CAPITAL_CYCLE_SERVICE.is_alive():
        return _CAPITAL_CYCLE_SERVICE
    _CAPITAL_CYCLE_STOP.clear()
    _CAPITAL_CYCLE_SERVICE = Thread(
        target=run_workspace_capital_cycle_service,
        kwargs={
            "workspace": workspace,
            "poll_seconds": poll_seconds,
            "stop_event": _CAPITAL_CYCLE_STOP,
        },
        name="jaggedthoughts-capital-cycle",
        daemon=True,
    )
    _CAPITAL_CYCLE_SERVICE.start()
    return _CAPITAL_CYCLE_SERVICE


def run_workspace_execution_market_probe(
    workspace: str | Path | None = None,
    *,
    decision_id: str | None = None,
    program_id: str | None = None,
) -> dict[str, Any]:
    """Run one explicit capability-adaptive valuation probe and refresh the UI."""

    root, config = load_workspace_config(workspace)
    result = run_execution_market_probe(
        root,
        owner=str(config.get("owner") or "operator-paper-book"),
        store_path=_store_path(root, config),
        decision_id=decision_id,
        program_id=program_id,
    )
    read_model = build_read_model(root)
    _atomic_json(root / "state" / "read_model.json", read_model)
    return {**result, "read_model": read_model}


def _market_state_project_path(root: Path, config: Mapping[str, Any]) -> Path:
    registration = next(
        (
            row for row in config.get("research_projects") or ()
            if isinstance(row, Mapping)
            and row.get("project_id") == "jaggedthoughts_market_state_newton"
        ),
        None,
    )
    if not registration or not registration.get("path"):
        raise ValueError("market-state cycle requires the registered Newton evidence project")
    project = (root / str(registration["path"])).resolve()
    if not (project / "evidence_state.txt").is_file() or not (project / "test_model.py").is_file():
        raise ValueError("registered market-state project is missing frozen evidence or candidate bytes")
    return project


def _refresh_market_state_sources(root: Path, config: Mapping[str, Any]) -> dict[str, Any]:
    run = consume_public_sources(
        root / str(config.get("source_manifest") or "sources.yaml"),
        workspace=root,
        source_ids=MARKET_STATE_SOURCE_IDS,
        derive_metrics=False,
        receipt_dir=root / "market_state",
    )
    statuses = [
        dict(row) for row in run.get("source_statuses") or ()
        if row.get("source_id") in MARKET_STATE_SOURCE_IDS
    ]
    consumed = {str(row["source_id"]) for row in statuses if row.get("status") == "consumed"}
    return {
        "schema": "jaggedthoughts-market-state-source-refresh-v1",
        "ok": bool(run.get("ok")) and consumed == set(MARKET_STATE_SOURCE_IDS),
        "retrieved_at": run.get("retrieved_at"),
        "run_sha256": run.get("run_sha256"),
        "source_statuses": statuses,
        "observation_count": run.get("observation_count"),
        "derive_metrics": False,
    }


def _run_market_state_cycle_action(
    root: Path,
    config: Mapping[str, Any],
    policy: Mapping[str, Any],
    *,
    force: bool,
) -> dict[str, Any]:
    owner = str(config.get("owner") or "operator-paper-book")
    store_path = _store_path(root, config)
    settlement = settle_due_market_state_forecasts(
        root, owner=owner, store_path=store_path,
    )
    windows = list(policy.get("market_state_forecast_windows") or ())
    cadence_by_horizon = {
        int(row["horizon_days"]): int(row["cadence_days"]) for row in windows
    }
    horizons = (
        tuple(int(row["horizon_days"]) for row in windows)
        if force else due_market_state_horizons(root, windows=windows)
    )
    issued_at = _utc_now()
    project_path = _market_state_project_path(root, config)
    actions: list[dict[str, Any]] = []
    for horizon in horizons:
        try:
            opened = open_market_state_forecast(
                root, owner=owner, store_path=store_path, horizon_days=horizon,
                project_path=project_path, issued_at=issued_at,
                issuance_cadence_days=cadence_by_horizon[horizon],
            )
            actions.append({
                "horizon_days": horizon,
                "status": "replayed" if opened.get("replayed") else "opened",
                "run_id": opened.get("run_id"),
                "run_sha256": opened.get("run_sha256"),
                "run_path": opened.get("run_path"),
                "candidate_count": len(opened.get("candidate_forecasts") or ()),
                "unavailable_challengers": list(opened.get("unavailable_challengers") or ()),
            })
        except Exception as error:  # noqa: BLE001 - preserve other horizon actions.
            actions.append({
                "horizon_days": horizon,
                "status": "error",
                "error": f"{type(error).__name__}: {error}"[:1_000],
            })
    return {
        "schema": "jaggedthoughts-market-state-cycle-action-v1",
        "evaluated_at": issued_at,
        "due_horizons": list(horizons),
        "settlement": settlement,
        "forecast_actions": actions,
        "ok": all(row["status"] != "error" for row in actions),
        "capital_authority": False,
    }


def run_workspace_market_state_cycle(
    workspace: str | Path | None = None,
    *,
    refresh_sources: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """Refresh the small public state bundle, then settle and issue due forecasts."""

    root, config = load_workspace_config(workspace)
    source_run = None
    if refresh_sources:
        source_run = _refresh_market_state_sources(root, config)
        if not source_run.get("ok"):
            return {
                "schema": "jaggedthoughts-market-state-cycle-action-v1",
                "ok": False,
                "status": "source_refresh_failed",
                "source_run": source_run,
                "capital_authority": False,
            }
    policy = load_capital_cycle_policy(
        root / str(config.get("capital_cycle_policy") or "capital_cycle.yaml")
    )
    action = _run_market_state_cycle_action(root, config, policy, force=force)
    read_model = build_read_model(root)
    _atomic_json(root / "state" / "read_model.json", read_model)
    return {**action, "source_run": source_run, "read_model": read_model}


def run_workspace_institutional_learning(
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Compile the current phenotype, conjecture, counterexample, and law state."""

    root, config = load_workspace_config(workspace)
    result = _advance_workspace_strategy_business_clock(root, config)
    read_model = build_read_model(root)
    _atomic_json(root / "state" / "read_model.json", read_model)
    return {**result, "read_model": read_model}


def open_workspace_closed_book_forecast(
    workspace: str | Path | None = None,
    *,
    decision_id: str | None = None,
    paper_watch_decision_id: str | None = None,
    candidate_leaf: str | None = None,
    benchmark_id: str = "SPY",
    probe_weight: float = 0.05,
    horizon_days: int = 90,
    kernel_removal_trial: bool = False,
) -> dict[str, Any]:
    """Freeze one prospective evidence packet and its candidate forecasts."""

    root, config = load_workspace_config(workspace)
    result = open_closed_book_forecast(
        root,
        owner=str(config.get("owner") or "operator-paper-book"),
        store_path=_store_path(root, config),
        decision_id=decision_id,
        paper_watch_decision_id=paper_watch_decision_id,
        candidate_leaf=candidate_leaf,
        benchmark_id=benchmark_id,
        probe_weight=probe_weight,
        horizon_days=horizon_days,
        kernel_removal_trial=kernel_removal_trial,
    )
    strategy_alpha_issuance = process_strategy_alpha_issuance_actions(
        root, run_ids=(str(result["run_id"]),),
    )
    read_model = build_read_model(root)
    _atomic_json(root / "state" / "read_model.json", read_model)
    return {
        **result,
        "strategy_alpha_issuance": strategy_alpha_issuance,
        "read_model": read_model,
    }


def settle_workspace_closed_book_forecasts(
    workspace: str | Path | None = None,
    *,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Settle due closed-book windows from source-bound cached prices."""

    root, config = load_workspace_config(workspace)
    result = settle_due_closed_book_forecasts(
        root,
        owner=str(config.get("owner") or "operator-paper-book"),
        store_path=_store_path(root, config),
        as_of=as_of,
    )
    read_model = build_read_model(root)
    _atomic_json(root / "state" / "read_model.json", read_model)
    return {**result, "read_model": read_model}


def run_workspace_household_allocation_scenario(
    inputs: Mapping[str, Any], workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Compile one non-persistent household sleeve scenario from current artifacts."""
    root, config = load_workspace_config(workspace)
    basis = _read_json(root / "household" / "capital_market_basis" / "latest.json")
    if not basis:
        raise ValueError("current public household capital-market basis is unavailable")
    basis_as_of = str((basis.get("capital_market_basis") or {}).get("as_of") or "")
    surface = _current_household_goal_surface(root, config, as_of=basis_as_of)
    return compile_household_allocation_scenario(
        inputs, goal_surface=surface, public_basis_acquisition=basis,
        instrument_admissions=_read_json(
            root / "portfolio" / "instrument_admissions" / "latest.json"
        ),
        opportunity_book=_read_json(root / "opportunity_books" / "latest.json"),
        portfolio_policy=portfolio_policy_status(root),
    )


def _current_household_goal_surface(
    root: Path, config: Mapping[str, Any], *, as_of: str | None = None,
    observations: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    intake_ref = config.get("household_intake")
    if not intake_ref:
        raise ValueError("household intake is not configured")
    source_run = _current_source_run(root)
    cutoff = canonical_timestamp(
        as_of or (source_run or {}).get("as_of") or _utc_now(), "household FX cutoff",
    )
    observation_rows = (
        observations if observations is not None
        else _latest_observations(root, source_run)
    )
    fx_rows = [row for row in observation_rows if (
        row.get("entity_id") == "EURUSD" and row.get("metric_id") == "usd_per_eur"
        and timestamp_key(str(row.get("available_at") or "")) <= timestamp_key(cutoff)
    )]
    if not fx_rows:
        observations_path = root / "data" / "observations.csv"
        if observations_path.is_file():
            with observations_path.open("r", encoding="utf-8", newline="") as handle:
                fx_rows = [
                    dict(row) for row in csv.DictReader(handle)
                    if row.get("entity_id") == "EURUSD"
                    and row.get("metric_id") == "usd_per_eur"
                    and timestamp_key(str(row.get("available_at") or ""))
                    <= timestamp_key(cutoff)
                ]
    if not fx_rows:
        raise ValueError("current public USD-per-EUR evidence is unavailable")
    fx = max(fx_rows, key=lambda row: (
        timestamp_key(str(row["available_at"])), timestamp_key(str(row["observed_at"])),
        str(row["observation_id"]),
    ))
    surface = compile_private_household_workspace(
        root / str(intake_ref), fx_to_base={"EUR": float(fx["value"])},
        base_currency=str(config.get("household_base_currency") or "USD"),
        fx_source_refs=(str(fx["source_ref"]),), as_of=str(fx["available_at"]),
        budget_evidence=_read_json(root / "household" / "budget" / "latest.json"),
    )
    return surface


def freeze_workspace_household_policy_tournament(
    inputs: Mapping[str, Any],
    *,
    expected_scenario_sha256: str,
    horizon_days: int = 365,
    transaction_cost_bps: float = 10.0,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Recompile and freeze the displayed household comparison under paper authority."""

    root, config = load_workspace_config(workspace)
    scenario = run_workspace_household_allocation_scenario(inputs, root)
    if scenario["scenario_sha256"] != str(expected_scenario_sha256):
        raise ValueError("displayed household scenario is stale; rerun it before freezing")
    result = open_household_policy_tournament(
        root,
        owner=str(config.get("owner") or "operator-paper-book"),
        store_path=_store_path(root, config),
        scenario=scenario,
        horizon_days=int(horizon_days),
        transaction_cost_bps=float(transaction_cost_bps),
    )
    read_model = build_read_model(root)
    _atomic_json(root / "state" / "read_model.json", read_model)
    return {
        **result,
        "tournament_status": household_policy_tournament_status(root),
        "read_model": read_model,
    }


def freeze_workspace_operator_paper_policy(
    mandate: Mapping[str, Any],
    scenario_inputs: Mapping[str, Any],
    *,
    expected_scenario_sha256: str,
    selected_proposal_id: str,
    operator_id: str,
    attestation: str,
    reviewed_at: str | None = None,
    transaction_cost_bps: float = 10.0,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Freeze one explicit operator-owned paper policy against the displayed epoch."""

    root, config = load_workspace_config(workspace)
    scenario = run_workspace_household_allocation_scenario(scenario_inputs, root)
    if scenario["scenario_sha256"] != str(expected_scenario_sha256):
        raise ValueError("displayed household scenario is stale; rerun it before selection")
    acquired_basis = _read_json(root / "household" / "capital_market_basis" / "latest.json")
    basis = dict((acquired_basis or {}).get("capital_market_basis") or {})
    if not basis:
        raise ValueError("current public household capital-market basis is unavailable")
    result = freeze_operator_paper_policy(
        root,
        owner=str(config.get("owner") or "operator-paper-book"),
        store_path=_store_path(root, config),
        mandate=mandate,
        capital_market_basis=basis,
        scenario=scenario,
        selected_proposal_id=selected_proposal_id,
        operator_id=operator_id,
        attestation=attestation,
        reviewed_at=reviewed_at,
        transaction_cost_bps=float(transaction_cost_bps),
    )
    read_model = build_read_model(root)
    _atomic_json(root / "state" / "read_model.json", read_model)
    return {**result, "read_model": read_model}


def freeze_workspace_composed_operator_paper_policy(
    completion: Mapping[str, Any],
    scenario_inputs: Mapping[str, Any],
    *,
    expected_scenario_sha256: str,
    selected_proposal_id: str,
    operator_id: str,
    attestation: str,
    reviewed_at: str | None = None,
    transaction_cost_bps: float = 10.0,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Compose known private facts with explicit choices, then freeze the policy."""

    root, config = load_workspace_config(workspace)
    scenario = run_workspace_household_allocation_scenario(scenario_inputs, root)
    if scenario["scenario_sha256"] != str(expected_scenario_sha256):
        raise ValueError("displayed household scenario is stale; rerun it before selection")
    mandate = compose_operator_household_mandate(
        goal_surface=_current_household_goal_surface(
            root, config, as_of=str(scenario["as_of"]),
        ),
        scenario=scenario,
        completion=completion,
    )
    return freeze_workspace_operator_paper_policy(
        mandate,
        scenario_inputs,
        expected_scenario_sha256=expected_scenario_sha256,
        selected_proposal_id=selected_proposal_id,
        operator_id=operator_id,
        attestation=attestation,
        reviewed_at=reviewed_at,
        transaction_cost_bps=transaction_cost_bps,
        workspace=root,
    )


def workspace_operator_paper_policy_status(
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Read the authoritative operator paper-policy head."""

    root, config = load_workspace_config(workspace)
    return operator_paper_policy_status(
        root,
        owner=str(config.get("owner") or "operator-paper-book"),
        store_path=_store_path(root, config),
    )


def refresh_workspace_household_budget_evidence(
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Refresh the private content-addressed workbook receipt without altering its source."""
    root, config = load_workspace_config(workspace)
    intake_ref = config.get("household_intake")
    if not intake_ref:
        raise ValueError("household intake is not configured")
    intake = _load_yaml(root / str(intake_ref))
    source = next((row for row in intake.get("source_candidates") or () if (
        str(row.get("kind") or "") in {"spreadsheet", "household_budget_workbook"}
    )), None)
    if not source:
        raise ValueError("household budget workbook is not configured")
    from .household_budget_evidence import compile_household_budget_evidence
    result = compile_household_budget_evidence(
        source.get("path"), source_id=str(source.get("source_id") or "budget"),
    )
    _atomic_json(root / "household" / "budget" / "latest.json", result)
    return result


def settle_workspace_decision(
    decision_id: str,
    outcome_path: str | Path,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    root, config = load_workspace_config(workspace)
    decision_path = root / "decisions" / f"{decision_id}.json"
    decision = _read_json(decision_path)
    if not decision:
        raise FileNotFoundError(f"unknown compiled decision: {decision_id}")
    outcome_payload = _read_json(Path(outcome_path).expanduser().resolve())
    if not outcome_payload:
        raise ValueError("outcome must be a JSON object")
    outcome = OutcomeSnapshot.from_dict(outcome_payload)
    scorecard = settle_paper_decision(decision, outcome).to_dict()
    score_path = root / "outcomes" / f"{decision_id}-{outcome.observed_at[:10]}.scorecard.json"
    report_path = root / "reports" / f"{decision_id}-{outcome.observed_at[:10]}.settlement.md"
    _atomic_json(score_path, scorecard)
    _atomic_text(report_path, scorecard_report(scorecard))
    store = GoldenStore(_store_path(root, config))
    try:
        store.head(str(decision["owner"]), "paper_decision", str(decision["decision_id"]))
    except KeyError:
        record_investment_decision(store, decision)
    leaves = record_investment_settlement(store, decision=decision, outcome=outcome.to_dict(), scorecard=scorecard)
    funnel_leaf: str | None = None
    lifecycle = decision.get("profile_lifecycle") or {}
    if lifecycle.get("data_class") == "operator":
        prior_receipt: Mapping[str, Any] | None = None
        for metadata in store.list_leaves(object_kind="opportunity_funnel_transition", limit=10_000):
            leaf = store.get_leaf(str(metadata["leaf_sha256"]))
            payload = leaf.get("payload") or {}
            if not str(payload.get("transition_id") or "").startswith(f"{decision_id}:"):
                continue
            if payload.get("to_state") in {"allocated_paper", "monitored"}:
                prior_receipt = payload
                break
        if prior_receipt:
            from_state = str(prior_receipt["to_state"])
            predecessor = FunnelObjectRef.from_dict(prior_receipt["successor"])
        else:
            from_state = "active_paper"
            predecessor = FunnelObjectRef(
                object_kind="paper_decision", object_id=decision_id,
                sha256=str(decision["decision_record_sha256"]),
            )
        transition = FunnelTransitionReceipt(
            transition_id=f"{decision_id}:settle:{scorecard['scorecard_sha256'][:16]}",
            from_state=from_state, event="settle", to_state="settled",
            occurred_at=str(outcome.available_at), predecessor=predecessor,
            successor=FunnelObjectRef(
                object_kind="economic_scorecard",
                object_id=f"{decision_id}@{outcome.observed_at}",
                sha256=str(scorecard["scorecard_sha256"]),
            ),
            guard_refs=(
                str(decision["decision_record_sha256"]),
                str(outcome.outcome_sha256), str(scorecard["scorecard_sha256"]),
            ),
            context={
                "paper_return": scorecard["paper_return"],
                "net_excess_return": scorecard["net_excess_return"],
                "incremental_return_vs_no_action": scorecard["incremental_return_vs_no_action"],
            },
        )
        funnel_leaf = record_funnel_transition(
            store, owner=str(decision["owner"]), receipt=transition.to_dict(),
        )
    read_model = build_read_model(root)
    _atomic_json(root / "state" / "read_model.json", read_model)
    return {
        "schema": "jaggedthoughts-investment-workspace-settlement-v1", "ok": True,
        "decision_id": decision_id, "scorecard": scorecard, "golden_leaves": leaves,
        "funnel_transition_leaf": funnel_leaf,
        "scorecard_path": score_path.relative_to(root).as_posix(),
        "report_path": report_path.relative_to(root).as_posix(), "read_model": read_model,
    }


def settle_workspace_prices(
    decision_id: str,
    *,
    observed_at: str,
    available_at: str,
    prices: Mapping[str, Any],
    source_refs: Iterable[str],
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Capture a later price snapshot and settle its bound paper decision."""
    root, _config = load_workspace_config(workspace)
    decision = _read_json(root / "decisions" / f"{decision_id}.json")
    if not decision:
        raise FileNotFoundError(f"unknown compiled decision: {decision_id}")
    outcome = OutcomeSnapshot.from_dict({
        "schema": "jaggedthoughts-investment-outcome-v1",
        "decision_record_sha256": decision["decision_record_sha256"],
        "observed_at": observed_at,
        "available_at": available_at,
        "prices": {str(key): float(value) for key, value in prices.items()},
        "source_refs": list(source_refs),
    })
    outcome_path = root / "outcomes" / f"{decision_id}-{outcome.observed_at[:10]}.snapshot.json"
    _atomic_json(outcome_path, outcome.to_dict())
    result = settle_workspace_decision(decision_id, outcome_path, root)
    return {**result, "outcome_path": outcome_path.relative_to(root).as_posix()}


__all__ = [
    "BUILD_SCHEMA",
    "MARKET_SCOUT_CYCLE_SCHEMA",
    "MARKET_SCOUT_POLICY_SCHEMA",
    "READ_MODEL_SCHEMA",
    "WORKSPACE_SCHEMA",
    "build_read_model",
    "project_workspace_read_model",
    "build_workspace",
    "compile_workspace_company_strategy",
    "select_workspace_company_contingent_recourse",
    "default_workspace_path",
    "default_market_scout_policy",
    "initialize_workspace",
    "read_cached_read_model",
    "load_workspace_config",
    "refresh_workspace",
    "refresh_workspace_market_catalog",
    "refresh_workspace_sources",
    "project_workspace_cached_adjusted_prices",
    "resolve_workspace",
    "settle_workspace_decision",
    "settle_workspace_prices",
    "submit_workspace_strategy_outcome",
    "hydrate_workspace_strategy_cohort",
    "seed_workspace_public_equity_draft",
    "draft_workspace_discovery_candidate",
    "enroll_workspace_public_equity",
    "enroll_workspace_public_fund",
    "fund_lookthrough_acquisition_status",
    "hydrate_workspace_fund_lookthrough",
    "hydrate_workspace_fund_portfolio_lookthrough",
    "run_workspace_company_state_flow_experiment",
    "run_workspace_cross_sectional_flow_evidence",
    "run_workspace_household_allocation_scenario",
    "freeze_workspace_household_policy_tournament",
    "freeze_workspace_operator_paper_policy",
    "freeze_workspace_composed_operator_paper_policy",
    "workspace_operator_paper_policy_status",
    "refresh_workspace_household_budget_evidence",
    "run_workspace_company_state_path_action",
    "freeze_workspace_company_state_newton_successor",
    "settle_workspace_company_state_path_action",
    "run_workspace_market_flow_experiment",
    "run_workspace_market_scout",
    "run_workspace_scheduled_market_scouts",
    "run_workspace_discovery",
    "run_workspace_autonomous_enrichment",
    "run_workspace_discovery_service",
    "run_workspace_fund_lookthrough_acquisition",
    "run_workspace_capital_cycle",
    "run_workspace_capital_cycle_service",
    "start_workspace_discovery_service",
    "start_workspace_capital_cycle_service",
    "workspace_discovery_status",
    "activate_workspace_profile",
]
