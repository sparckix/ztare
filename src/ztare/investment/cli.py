"""Command line workbench for paper investment decisions and settlement."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

from .compiler import compile_investment_profile_file
from .equity_paper import activate_workspace_equity_paper_watch
from .golden_store import (
    GoldenStore,
    record_investment_decision,
    record_investment_settlement,
    record_portfolio_assembly,
    record_world_model_tournament,
)
from .fund_paper import activate_workspace_fund_paper_watch
from .paper import OutcomeSnapshot, settle_paper_decision
from .point_in_time_replay import (
    compile_archived_accounting_replay,
    compile_point_in_time_forecast_replay,
    compile_sealed_walk_forward_readiness,
)
from .portfolio import compile_portfolio_profile_file
from .price_action import PriceActionCandidate, evaluate_price_action_candidate
from .research_agent import (
    research_agent_status,
    run_research_agent_once,
    run_research_agent_service,
)
from .report import decision_report, scorecard_report, tournament_report
from .strategy_options import explain_strategy_bundle_feasibility
from .tournament import compile_world_model_tournament_profile
from .workspace import (
    activate_workspace_profile,
    build_workspace,
    compile_workspace_company_strategy,
    compile_workspace_fund_paper_audit,
    default_workspace_path,
    draft_workspace_discovery_candidate,
    enroll_workspace_public_equity,
    enroll_workspace_public_fund,
    freeze_workspace_company_state_newton_successor,
    freeze_workspace_operator_paper_policy,
    hydrate_workspace_fund_lookthrough,
    hydrate_workspace_strategy_cohort,
    initialize_workspace,
    open_workspace_closed_book_forecast,
    project_workspace_cached_adjusted_prices,
    refresh_workspace,
    refresh_workspace_market_catalog,
    refresh_workspace_sources,
    read_cached_read_model,
    run_workspace_discovery,
    run_workspace_autonomous_enrichment,
    run_workspace_capital_cycle,
    run_workspace_capital_cycle_service,
    run_workspace_discovery_service,
    run_workspace_execution_market_probe,
    run_workspace_company_state_flow_experiment,
    run_workspace_cross_sectional_flow_evidence,
    run_workspace_company_state_path_action,
    run_workspace_market_flow_experiment,
    run_workspace_market_state_cycle,
    run_workspace_institutional_learning,
    run_workspace_market_scout,
    run_workspace_scheduled_market_scouts,
    seed_workspace_public_equity_draft,
    select_workspace_company_contingent_recourse,
    submit_workspace_research_dossier,
    submit_workspace_strategy_outcome,
    settle_workspace_decision,
    settle_workspace_closed_book_forecasts,
    settle_workspace_company_state_path_action,
    settle_workspace_prices,
)


def _read_json(path: str | Path) -> Mapping[str, Any]:
    source = Path(path).expanduser().resolve()
    value = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON artifact must be an object: {source}")
    return value


def _write_text(path: str | Path, text: str) -> None:
    destination = Path(path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(destination)


def _emit_json(value: Mapping[str, Any], output: str | None) -> None:
    rendered = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if output:
        _write_text(output, rendered)
    else:
        print(rendered, end="")


def _compile(args: argparse.Namespace) -> int:
    decision = compile_investment_profile_file(args.profile)
    leaves: dict[str, str] | None = None
    if args.store:
        leaves = record_investment_decision(GoldenStore(args.store), decision)
    _emit_json(decision, args.output)
    if args.report:
        _write_text(args.report, decision_report(decision))
    if args.summary:
        print(json.dumps({
            "decision_id": decision["decision_id"],
            "decision_record_sha256": decision["decision_record_sha256"],
            "selected_action_id": decision["summary"]["selected_action_id"],
            "target_weight": decision["summary"]["target_weight"],
            "frontier_count": decision["summary"]["frontier_count"],
            "representation_status": decision["summary"]["representation_status"],
            "golden_leaves": leaves,
        }, indent=2, sort_keys=True))
    return 0


def _settle(args: argparse.Namespace) -> int:
    decision = _read_json(args.decision)
    outcome = OutcomeSnapshot.from_dict(_read_json(args.outcome))
    scorecard = settle_paper_decision(decision, outcome)
    score = scorecard.to_dict()
    leaves: dict[str, str] | None = None
    if args.store:
        store = GoldenStore(args.store)
        try:
            store.head(str(decision["owner"]), "paper_decision", str(decision["decision_id"]))
        except KeyError:
            record_investment_decision(store, decision)
        leaves = record_investment_settlement(
            store,
            decision=decision,
            outcome=outcome.to_dict(),
            scorecard=score,
        )
    _emit_json(score, args.output)
    if args.report:
        _write_text(args.report, scorecard_report(score))
    if args.summary:
        print(json.dumps({
            "decision_id": score["decision_id"],
            "paper_return": score["paper_return"],
            "benchmark_return": score["benchmark_return"],
            "net_excess_return": score["net_excess_return"],
            "incremental_return_vs_no_action": score["incremental_return_vs_no_action"],
            "golden_leaves": leaves,
        }, indent=2, sort_keys=True))
    return 0


def _price_eval(args: argparse.Namespace) -> int:
    candidate = PriceActionCandidate.from_dict(_read_json(args.candidate))
    baselines = tuple(PriceActionCandidate.from_dict(_read_json(path)) for path in args.baseline)
    evaluation = evaluate_price_action_candidate(
        candidate,
        _read_json(args.outcome),
        baselines=baselines,
        transaction_cost_bps=args.transaction_cost_bps,
    )
    _emit_json(evaluation, args.output)
    return 0


def _portfolio(args: argparse.Namespace) -> int:
    assembly, decisions = compile_portfolio_profile_file(args.profile)
    leaf: str | None = None
    if args.store:
        leaf = record_portfolio_assembly(
            GoldenStore(args.store), assembly=assembly, decisions=decisions
        )
    _emit_json(assembly, args.output)
    if args.summary:
        print(json.dumps({
            "portfolio_id": assembly["portfolio_id"],
            "portfolio_assembly_sha256": assembly["portfolio_assembly_sha256"],
            "combination_count": assembly["combination_count"],
            "feasible_count": len(assembly["feasible_alternatives"]),
            "frontier_count": len(assembly["frontier_alternative_ids"]),
            "selected_target_weights": assembly["selected_target_weights"],
            "selected_metrics": assembly["selected_metrics"],
            "golden_leaf": leaf,
        }, indent=2, sort_keys=True))
    return 0


def _tournament(args: argparse.Namespace) -> int:
    result = compile_world_model_tournament_profile(args.profile)
    leaves: dict[str, Any] | None = None
    if args.store:
        leaves = record_world_model_tournament(GoldenStore(args.store), result)
    _emit_json(result, args.output)
    if args.report:
        _write_text(args.report, tournament_report(result))
    if args.summary:
        print(json.dumps({
            "tournament_id": result["tournament_id"],
            "tournament_sha256": result["tournament_sha256"],
            "mode": result["mode"],
            "episode_count": result["episode_count"],
            "inference_block_count": result["inference_block_count"],
            "survivor_model_ids": result["survivor_model_ids"],
            "capital_authority": result["capital_authority"],
            "golden_leaves": leaves,
        }, indent=2, sort_keys=True))
    return 0


def _store(args: argparse.Namespace) -> int:
    store = GoldenStore(args.path)
    if args.store_command == "verify":
        result = store.verify()
        _emit_json(result, args.output)
        return 0 if result["ok"] else 1
    if args.store_command == "list":
        result = {
            "schema": "jaggedthoughts-golden-leaf-list-v2",
            "projection": "metadata_only",
            "leaves": store.list_leaves(
                owner=args.owner,
                object_kind=args.kind,
                limit=args.limit,
            ),
        }
    elif args.store_command == "show":
        result = store.get_leaf(args.leaf_sha256)
    elif args.store_command == "lineage":
        result = store.lineage(args.leaf_sha256, max_depth=args.max_depth)
    else:  # pragma: no cover - argparse owns this boundary
        raise ValueError(f"unsupported store command: {args.store_command}")
    _emit_json(result, args.output)
    return 0


def _workspace(args: argparse.Namespace) -> int:
    path = args.path
    if args.workspace_command == "init":
        result = initialize_workspace(
            path,
            owner=args.owner,
            include_reference_fixture=not args.no_reference_fixture,
            overwrite=args.overwrite,
        )
    elif args.workspace_command == "status":
        result = read_cached_read_model(path)
    elif args.workspace_command == "sources":
        result = refresh_workspace_sources(path, strict=args.strict)
    elif args.workspace_command == "sources-project-cached":
        result = project_workspace_cached_adjusted_prices(path)
    elif args.workspace_command == "build":
        result = build_workspace(path)
    elif args.workspace_command == "refresh":
        result = refresh_workspace(path, strict_sources=args.strict)
    elif args.workspace_command == "discover":
        result = run_workspace_discovery(
            path, force=args.force, strict_sources=args.strict,
        )
    elif args.workspace_command == "enrichment-run":
        result = run_workspace_autonomous_enrichment(
            path, strict_sources=args.strict,
        )
    elif args.workspace_command == "capital-cycle":
        result = run_workspace_capital_cycle(path, force=args.force)
    elif args.workspace_command == "capital-cycle-service":
        result = run_workspace_capital_cycle_service(
            path, poll_seconds=args.poll_seconds, once=args.once,
        )
    elif args.workspace_command == "operator-paper-policy-freeze":
        result = freeze_workspace_operator_paper_policy(
            _read_json(args.mandate),
            _read_json(args.scenario_inputs),
            expected_scenario_sha256=args.expected_scenario_sha256,
            selected_proposal_id=args.selected_proposal_id,
            operator_id=args.operator_id,
            attestation=args.attestation,
            reviewed_at=args.reviewed_at,
            transaction_cost_bps=args.transaction_cost_bps,
            workspace=path,
        )
    elif args.workspace_command == "universe-refresh":
        result = refresh_workspace_market_catalog(path)
    elif args.workspace_command == "scout":
        intent_overrides = (
            _read_json(args.intent_overrides) if args.intent_overrides else None
        )
        result = run_workspace_market_scout(
            args.query, path, max_results=args.max_results,
            refresh_catalog=args.refresh_catalog,
            intent_overrides=intent_overrides,
            subscribe_id=args.subscribe,
        )
    elif args.workspace_command == "scout-scheduled":
        result = run_workspace_scheduled_market_scouts(path, force=args.force)
    elif args.workspace_command == "strategy-frontier":
        result = compile_workspace_company_strategy(args.profile, path)
    elif args.workspace_command == "strategy-explain":
        result = explain_strategy_bundle_feasibility(
            _read_json(args.frontier), args.option_id,
        )
    elif args.workspace_command == "strategy-recourse":
        result = select_workspace_company_contingent_recourse(args.request, path)
    elif args.workspace_command == "strategy-outcome":
        result = submit_workspace_strategy_outcome(args.outcome, path)
    elif args.workspace_command == "draft-candidate":
        result = draft_workspace_discovery_candidate(
            args.candidate_leaf, thesis_claim=args.thesis,
            entity_name=args.entity_name, base_growth=args.base_growth,
            terminal_growth=args.terminal_growth, dossier_path=args.dossier,
            workspace=path,
        )
    elif args.workspace_command == "submit-dossier":
        result = submit_workspace_research_dossier(args.dossier, path)
    elif args.workspace_command == "fund-proposals":
        result = compile_workspace_fund_paper_audit(path)
    elif args.workspace_command == "equity-activate":
        result = activate_workspace_equity_paper_watch(
            path, args.entity_id, proposal_sha256=args.proposal_sha256,
            confirmation=args.confirmation, operator_id=args.operator_id,
            activated_at=args.activated_at,
        )
    elif args.workspace_command == "fund-activate":
        result = activate_workspace_fund_paper_watch(
            path, args.entity_id, proposal_sha256=args.proposal_sha256,
            confirmation=args.confirmation, operator_id=args.operator_id,
            activated_at=args.activated_at,
        )
    elif args.workspace_command == "discovery-service":
        result = run_workspace_discovery_service(
            path, poll_seconds=args.poll_seconds, once=args.once,
        )
    elif args.workspace_command == "research-agent":
        research_path = path or default_workspace_path()
        if args.work_id and not args.once:
            raise ValueError("--work-id requires --once")
        result = (
            run_research_agent_once(research_path, work_id=args.work_id)
            if args.once
            else run_research_agent_service(
                research_path, poll_seconds=args.poll_seconds,
            )
        )
    elif args.workspace_command == "research-agent-status":
        result = research_agent_status(path or default_workspace_path())
    elif args.workspace_command == "settle":
        result = settle_workspace_decision(args.decision_id, args.outcome, path)
    elif args.workspace_command == "settle-prices":
        prices: dict[str, float] = {}
        for raw in args.price:
            entity_id, separator, value = raw.partition("=")
            if not separator or not entity_id.strip():
                raise ValueError("--price must use ENTITY=VALUE")
            prices[entity_id.strip().upper()] = float(value)
        result = settle_workspace_prices(
            args.decision_id,
            observed_at=args.observed_at,
            available_at=args.available_at,
            prices=prices,
            source_refs=args.source_ref,
            workspace=path,
        )
    elif args.workspace_command == "seed-equity":
        result = seed_workspace_public_equity_draft(
            path,
            entity_id=args.entity_id,
            entity_name=args.entity_name,
            benchmark_id=args.benchmark_id,
            benchmark_name=args.benchmark_name,
            thesis_claim=args.thesis,
            beta=args.beta,
            base_growth=args.base_growth,
            terminal_growth=args.terminal_growth,
            overwrite=args.overwrite,
        )
    elif args.workspace_command == "enroll-equity":
        result = enroll_workspace_public_equity(args.ticker, path)
    elif args.workspace_command == "enroll-fund":
        result = enroll_workspace_public_fund(
            args.ticker, args.name, path, category=args.category,
        )
    elif args.workspace_command == "hydrate-fund":
        result = hydrate_workspace_fund_lookthrough(
            path, target_entity_id=args.ticker, limit=args.limit,
        )
    elif args.workspace_command == "hydrate-strategy-cohort":
        result = hydrate_workspace_strategy_cohort(path, limit=args.limit)
    elif args.workspace_command == "activate":
        result = activate_workspace_profile(args.profile_id, args.confirmation, path)
    elif args.workspace_command == "market-flow":
        result = run_workspace_market_flow_experiment(
            args.profile, path, output_dir=args.output_dir,
        )
    elif args.workspace_command == "market-flow-panel":
        result = run_workspace_cross_sectional_flow_evidence(args.profile, path)
    elif args.workspace_command == "company-state-flow":
        result = run_workspace_company_state_flow_experiment(args.profile, path)
    elif args.workspace_command == "company-state-path-action":
        result = run_workspace_company_state_path_action(args.profile, path)
    elif args.workspace_command == "company-state-newton-freeze":
        result = freeze_workspace_company_state_newton_successor(
            args.source_run, args.candidate, args.source_status, args.research_result,
            path, opened_at=args.opened_at,
        )
    elif args.workspace_command == "company-state-path-status":
        result = settle_workspace_company_state_path_action(path, as_of=args.as_of)
    elif args.workspace_command == "point-in-time-replay":
        replay_root = path or default_workspace_path()
        profile = Path(args.profile).expanduser()
        if not profile.is_absolute():
            profile = replay_root / profile
        result = compile_point_in_time_forecast_replay(replay_root, profile)
    elif args.workspace_command == "sealed-walk-forward-readiness":
        replay_root = path or default_workspace_path()
        profile = Path(args.profile).expanduser()
        if not profile.is_absolute():
            profile = replay_root / profile
        result = compile_sealed_walk_forward_readiness(replay_root, profile)
    elif args.workspace_command == "archived-accounting-replay":
        result = compile_archived_accounting_replay(
            path or default_workspace_path(), as_of=args.as_of,
            source_ids=tuple(args.source_id or ()),
        )
    elif args.workspace_command == "execution-market":
        result = run_workspace_execution_market_probe(
            path,
            decision_id=args.decision_id,
            program_id=args.program_id,
        )
    elif args.workspace_command == "closed-book-open":
        result = open_workspace_closed_book_forecast(
            path,
            decision_id=args.decision_id,
            paper_watch_decision_id=args.paper_watch_decision_id,
            candidate_leaf=args.candidate_leaf,
            benchmark_id=args.benchmark_id,
            probe_weight=args.probe_weight,
            horizon_days=args.horizon_days,
        )
    elif args.workspace_command == "closed-book-settle":
        result = settle_workspace_closed_book_forecasts(path, as_of=args.as_of)
    elif args.workspace_command == "market-state-cycle":
        result = run_workspace_market_state_cycle(
            path, refresh_sources=args.refresh_sources, force=args.force,
        )
    elif args.workspace_command == "institutional-learning":
        result = run_workspace_institutional_learning(path)
    else:  # pragma: no cover - argparse owns this boundary
        raise ValueError(f"unsupported workspace command: {args.workspace_command}")
    _emit_json(result, args.output)
    return 0 if result.get("ok", True) else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ztare investment",
        description="Compile, record, and prospectively settle JaggedThoughts paper decisions.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    compile_parser = commands.add_parser("compile", help="Compile a point-in-time profile into a paper decision.")
    compile_parser.add_argument("profile")
    compile_parser.add_argument("--output")
    compile_parser.add_argument("--report")
    compile_parser.add_argument("--store", help="SQLite golden-store path.")
    compile_parser.add_argument("--summary", action="store_true")
    compile_parser.set_defaults(handler=_compile)

    settle_parser = commands.add_parser("settle", help="Score a frozen decision against a later outcome.")
    settle_parser.add_argument("decision")
    settle_parser.add_argument("outcome")
    settle_parser.add_argument("--output")
    settle_parser.add_argument("--report")
    settle_parser.add_argument("--store", help="SQLite golden-store path.")
    settle_parser.add_argument("--summary", action="store_true")
    settle_parser.set_defaults(handler=_settle)

    price_parser = commands.add_parser("price-eval", help="Compare a frozen price-law proposal with controls.")
    price_parser.add_argument("candidate")
    price_parser.add_argument("outcome")
    price_parser.add_argument("--baseline", action="append", required=True)
    price_parser.add_argument("--transaction-cost-bps", type=float, default=10.0)
    price_parser.add_argument("--output")
    price_parser.set_defaults(handler=_price_eval)

    portfolio_parser = commands.add_parser(
        "portfolio", help="Assemble several frozen entity decisions under portfolio constraints."
    )
    portfolio_parser.add_argument("profile")
    portfolio_parser.add_argument("--output")
    portfolio_parser.add_argument("--store", help="SQLite golden-store path.")
    portfolio_parser.add_argument("--summary", action="store_true")
    portfolio_parser.set_defaults(handler=_portfolio)

    tournament_parser = commands.add_parser(
        "tournament", help="Score frozen world models on point-in-time episodes."
    )
    tournament_parser.add_argument("profile")
    tournament_parser.add_argument("--output")
    tournament_parser.add_argument("--report")
    tournament_parser.add_argument("--store", help="SQLite golden-store path.")
    tournament_parser.add_argument("--summary", action="store_true")
    tournament_parser.set_defaults(handler=_tournament)

    store_parser = commands.add_parser("store", help="Inspect or verify an append-only golden store.")
    store_parser.add_argument("--path", required=True)
    store_commands = store_parser.add_subparsers(dest="store_command", required=True)
    verify = store_commands.add_parser("verify")
    verify.add_argument("--output")
    list_parser = store_commands.add_parser("list")
    list_parser.add_argument("--owner")
    list_parser.add_argument("--kind")
    list_parser.add_argument("--limit", type=int, default=100)
    list_parser.add_argument("--output")
    show = store_commands.add_parser("show")
    show.add_argument("leaf_sha256")
    show.add_argument("--output")
    lineage = store_commands.add_parser("lineage")
    lineage.add_argument("leaf_sha256")
    lineage.add_argument("--max-depth", type=int, default=12)
    lineage.add_argument("--output")
    store_parser.set_defaults(handler=_store)

    workspace_parser = commands.add_parser(
        "workspace", help="Operate the public-source investment workspace and UI read model."
    )
    workspace_parser.add_argument("--path", help="Workspace directory; defaults to ZTARE_INVESTMENT_WORKSPACE or the local project workspace.")
    workspace_commands = workspace_parser.add_subparsers(dest="workspace_command", required=True)
    workspace_init = workspace_commands.add_parser("init", help="Initialize an editable operator workspace.")
    workspace_init.add_argument("--owner", default="operator-paper-book")
    workspace_init.add_argument("--no-reference-fixture", action="store_true")
    workspace_init.add_argument("--overwrite", action="store_true")
    workspace_init.add_argument("--output")
    workspace_status = workspace_commands.add_parser("status", help="Read the current finance-native UI projection.")
    workspace_status.add_argument("--output")
    workspace_sources = workspace_commands.add_parser("sources", help="Consume configured public sources and derive signals.")
    workspace_sources.add_argument("--strict", action="store_true")
    workspace_sources.add_argument("--output")
    workspace_cached_sources = workspace_commands.add_parser(
        "sources-project-cached",
        help="Project adjusted-price rows from verified cached Yahoo receipt heads without provider calls.",
    )
    workspace_cached_sources.add_argument("--output")
    workspace_build = workspace_commands.add_parser("build", help="Compile decisions, portfolio, tournaments, and golden-store lineage.")
    workspace_build.add_argument("--output")
    workspace_refresh = workspace_commands.add_parser("refresh", help="Run source consumption and the complete workspace build.")
    workspace_refresh.add_argument("--strict", action="store_true")
    workspace_refresh.add_argument("--output")
    workspace_discover = workspace_commands.add_parser(
        "discover", help="Run the due public-markets discovery cycle, or force one now."
    )
    workspace_discover.add_argument("--force", action="store_true")
    workspace_discover.add_argument("--strict", action="store_true")
    workspace_discover.add_argument("--output")
    workspace_enrichment = workspace_commands.add_parser(
        "enrichment-run",
        help="Run a bounded scout-to-public-evidence cycle and emit agent research requests.",
    )
    workspace_enrichment.add_argument("--strict", action="store_true")
    workspace_enrichment.add_argument("--output")
    workspace_capital_cycle = workspace_commands.add_parser(
        "capital-cycle",
        help="Settle due forecasts, open non-overlapping blocks, and compile the opportunity book.",
    )
    workspace_capital_cycle.add_argument("--force", action="store_true")
    workspace_capital_cycle.add_argument("--output")
    workspace_capital_service = workspace_commands.add_parser(
        "capital-cycle-service",
        help="Maintain event-driven capital-cycle due checks.",
    )
    workspace_capital_service.add_argument("--poll-seconds", type=float)
    workspace_capital_service.add_argument("--once", action="store_true")
    workspace_capital_service.add_argument("--output")
    workspace_operator_policy = workspace_commands.add_parser(
        "operator-paper-policy-freeze",
        help="Freeze an explicit paper-only household mandate and implementation choice.",
    )
    workspace_operator_policy.add_argument("--mandate", required=True)
    workspace_operator_policy.add_argument("--scenario-inputs", required=True)
    workspace_operator_policy.add_argument("--expected-scenario-sha256", required=True)
    workspace_operator_policy.add_argument("--selected-proposal-id", required=True)
    workspace_operator_policy.add_argument("--operator-id", required=True)
    workspace_operator_policy.add_argument(
        "--attestation", required=True, choices=("paper_only_reviewed",),
    )
    workspace_operator_policy.add_argument("--reviewed-at")
    workspace_operator_policy.add_argument("--transaction-cost-bps", type=float, default=10.0)
    workspace_operator_policy.add_argument("--output")
    workspace_universe = workspace_commands.add_parser(
        "universe-refresh", help="Refresh broad US-listed equity and ETF identity catalogs."
    )
    workspace_universe.add_argument("--output")
    workspace_scout = workspace_commands.add_parser(
        "scout", help="Compile a market-research request into a broad catalog shortlist."
    )
    workspace_scout.add_argument("query")
    workspace_scout.add_argument("--max-results", type=int, default=50)
    workspace_scout.add_argument("--refresh-catalog", action="store_true")
    workspace_scout.add_argument(
        "--subscribe",
        help="Persist this exact language intent under the supplied recurring id.",
    )
    workspace_scout.add_argument(
        "--intent-overrides",
        help="JSON object with agent/operator-supplied typed filters such as open theme_terms.",
    )
    workspace_scout.add_argument("--output")
    workspace_scout_scheduled = workspace_commands.add_parser(
        "scout-scheduled", help="Run due editable intents from research_jobs/intents.yaml."
    )
    workspace_scout_scheduled.add_argument("--force", action="store_true")
    workspace_scout_scheduled.add_argument("--output")
    workspace_strategy = workspace_commands.add_parser(
        "strategy-frontier", help="Compile a source-authored company strategy option space."
    )
    workspace_strategy.add_argument("profile")
    workspace_strategy.add_argument("--output")
    workspace_strategy_explain = workspace_commands.add_parser(
        "strategy-explain",
        help="Explain why a proposed option bundle is feasible or rejected by its frozen Z3 constraints.",
    )
    workspace_strategy_explain.add_argument("frontier")
    workspace_strategy_explain.add_argument("option_id", nargs="+")
    workspace_strategy_explain.add_argument("--output")
    workspace_strategy_recourse = workspace_commands.add_parser(
        "strategy-recourse",
        help="Select and record one frozen strategy branch from later typed observations.",
    )
    workspace_strategy_recourse.add_argument("request")
    workspace_strategy_recourse.add_argument("--output")
    workspace_strategy_outcome = workspace_commands.add_parser(
        "strategy-outcome",
        help="Validate and settle one matured source-bound strategy move outcome.",
    )
    workspace_strategy_outcome.add_argument("outcome")
    workspace_strategy_outcome.add_argument("--output")
    workspace_service = workspace_commands.add_parser(
        "discovery-service", help="Maintain periodic due checks for the configured discovery policy."
    )
    workspace_service.add_argument("--poll-seconds", type=float, default=300.0)
    workspace_service.add_argument("--once", action="store_true")
    workspace_service.add_argument("--output")
    workspace_research_agent = workspace_commands.add_parser(
        "research-agent",
        help="Consume immutable research-request leaves through the subscription web agent.",
    )
    workspace_research_agent.add_argument("--poll-seconds", type=float)
    workspace_research_agent.add_argument("--once", action="store_true")
    workspace_research_agent.add_argument("--work-id")
    workspace_research_agent.add_argument("--output")
    workspace_research_status = workspace_commands.add_parser(
        "research-agent-status",
        help="Inspect subscription-agent queue, budget, executable, and process ownership.",
    )
    workspace_research_status.add_argument("--output")
    workspace_candidate = workspace_commands.add_parser(
        "draft-candidate", help="Create an inactive underwriting draft from one discovery candidate leaf."
    )
    workspace_candidate.add_argument("candidate_leaf")
    workspace_candidate.add_argument("--thesis")
    workspace_candidate.add_argument("--dossier", help="Workspace-relative structured research dossier JSON.")
    workspace_candidate.add_argument("--entity-name")
    workspace_candidate.add_argument("--base-growth", type=float)
    workspace_candidate.add_argument("--terminal-growth", type=float)
    workspace_candidate.add_argument("--output")
    workspace_dossier = workspace_commands.add_parser(
        "submit-dossier",
        help="Validate and content-address a candidate research dossier against its agent request.",
    )
    workspace_dossier.add_argument("dossier", help="Workspace-relative dossier JSON path.")
    workspace_dossier.add_argument("--output")
    workspace_fund_proposals = workspace_commands.add_parser(
        "fund-proposals",
        help="Compile current qualified fund evidence into inactive paper drafts.",
    )
    workspace_fund_proposals.add_argument("--output")
    workspace_equity_activate = workspace_commands.add_parser(
        "equity-activate",
        help="Explicitly activate one current zero-weight equity proposal for paper watching.",
    )
    workspace_equity_activate.add_argument("entity_id")
    workspace_equity_activate.add_argument("--proposal-sha256", required=True)
    workspace_equity_activate.add_argument("--confirmation", required=True)
    workspace_equity_activate.add_argument("--operator-id", required=True)
    workspace_equity_activate.add_argument("--activated-at")
    workspace_equity_activate.add_argument("--output")
    workspace_fund_activate = workspace_commands.add_parser(
        "fund-activate",
        help="Explicitly activate one current zero-weight fund proposal for paper watching.",
    )
    workspace_fund_activate.add_argument("entity_id")
    workspace_fund_activate.add_argument("--proposal-sha256", required=True)
    workspace_fund_activate.add_argument("--confirmation", required=True)
    workspace_fund_activate.add_argument("--operator-id", required=True)
    workspace_fund_activate.add_argument("--activated-at")
    workspace_fund_activate.add_argument("--output")
    workspace_settle = workspace_commands.add_parser("settle", help="Settle one frozen workspace decision from a later outcome file.")
    workspace_settle.add_argument("decision_id")
    workspace_settle.add_argument("outcome")
    workspace_settle.add_argument("--output")
    workspace_prices = workspace_commands.add_parser(
        "settle-prices", help="Capture a later entity/benchmark price snapshot and settle its paper decision."
    )
    workspace_prices.add_argument("decision_id")
    workspace_prices.add_argument("--observed-at", required=True)
    workspace_prices.add_argument("--available-at", required=True)
    workspace_prices.add_argument("--price", action="append", required=True, help="ENTITY=VALUE; repeat for entity and benchmark.")
    workspace_prices.add_argument("--source-ref", action="append", required=True)
    workspace_prices.add_argument("--output")
    workspace_seed = workspace_commands.add_parser("seed-equity", help="Create and compile a source-bound public-equity draft.")
    workspace_seed.add_argument("entity_id")
    workspace_seed.add_argument("entity_name")
    workspace_seed.add_argument("--benchmark-id", default="SPY")
    workspace_seed.add_argument("--benchmark-name", default="S&P 500 ETF benchmark")
    workspace_seed.add_argument("--thesis", required=True)
    workspace_seed.add_argument("--beta", type=float, default=1.0)
    workspace_seed.add_argument("--base-growth", type=float, default=0.03)
    workspace_seed.add_argument("--terminal-growth", type=float, default=0.025)
    workspace_seed.add_argument("--overwrite", action="store_true")
    workspace_seed.add_argument("--output")
    workspace_enroll = workspace_commands.add_parser(
        "enroll-equity", help="Resolve a ticker through the SEC registry and add its public-source bundle."
    )
    workspace_enroll.add_argument("ticker")
    workspace_enroll.add_argument("--output")
    workspace_fund = workspace_commands.add_parser(
        "enroll-fund", help="Add a public ETF to the price/factor watchlist and rebuild."
    )
    workspace_fund.add_argument("ticker")
    workspace_fund.add_argument("name")
    workspace_fund.add_argument("--category", default="public ETF catalog candidate")
    workspace_fund.add_argument("--output")
    workspace_hydrate_fund = workspace_commands.add_parser(
        "hydrate-fund", help="Acquire the next holdings-weighted issuer evidence slice."
    )
    workspace_hydrate_fund.add_argument("ticker", nargs="?", default="PORTFOLIO")
    workspace_hydrate_fund.add_argument("--limit", type=int, default=10)
    workspace_hydrate_fund.add_argument("--output")
    workspace_hydrate_strategy = workspace_commands.add_parser(
        "hydrate-strategy-cohort",
        help="Enroll selected strategy peers and acquire their public filing histories.",
    )
    workspace_hydrate_strategy.add_argument("--limit", type=int, default=8)
    workspace_hydrate_strategy.add_argument("--output")
    workspace_activate = workspace_commands.add_parser("activate", help="Create an active paper profile from a reviewed draft.")
    workspace_activate.add_argument("profile_id")
    workspace_activate.add_argument("--confirmation", required=True)
    workspace_activate.add_argument("--output")
    workspace_flow = workspace_commands.add_parser(
        "market-flow", help="Run an isolated probability-current/Lagrangian model-family diagnostic."
    )
    workspace_flow.add_argument("--profile", default="experiments/lagrangian_market_flow.yaml")
    workspace_flow.add_argument("--output-dir")
    workspace_flow.add_argument("--output")
    workspace_flow_panel = workspace_commands.add_parser(
        "market-flow-panel",
        help="Freeze the cross-sectional probability-current evidence used by Newton search.",
    )
    workspace_flow_panel.add_argument(
        "--profile", default="experiments/lagrangian_probability_current_panel.yaml",
    )
    workspace_flow_panel.add_argument("--output")
    workspace_company_flow = workspace_commands.add_parser(
        "company-state-flow",
        help="Test persistent-company valuation x durability current against a reversible control.",
    )
    workspace_company_flow.add_argument(
        "--profile", default="experiments/company_state_probability_current.yaml",
    )
    workspace_company_flow.add_argument("--output")
    workspace_company_path = workspace_commands.add_parser(
        "company-state-path-action",
        help="Open the prospective two-quarter company-state path-action challenger.",
    )
    workspace_company_path.add_argument(
        "--profile", default="experiments/company_state_path_action.yaml",
    )
    workspace_company_path.add_argument("--output")
    workspace_company_newton = workspace_commands.add_parser(
        "company-state-newton-freeze",
        help="Freeze an attributed subscription-Newton candidate before both path horizons.",
    )
    workspace_company_newton.add_argument("--source-run", required=True)
    workspace_company_newton.add_argument("--candidate", required=True)
    workspace_company_newton.add_argument("--source-status", required=True)
    workspace_company_newton.add_argument("--research-result", required=True)
    workspace_company_newton.add_argument("--opened-at")
    workspace_company_newton.add_argument("--output")
    workspace_company_path_status = workspace_commands.add_parser(
        "company-state-path-status",
        help="Bind and score any due company-state path-action leg.",
    )
    workspace_company_path_status.add_argument("--as-of")
    workspace_company_path_status.add_argument("--output")
    workspace_replay = workspace_commands.add_parser(
        "point-in-time-replay",
        help="Score a deterministic forecast from two content-addressed evidence cutoffs.",
    )
    workspace_replay.add_argument("--profile", required=True)
    workspace_replay.add_argument("--output")
    workspace_walk_forward = workspace_commands.add_parser(
        "sealed-walk-forward-readiness",
        help="Check broad deterministic replay coverage without backfilling old cutoffs.",
    )
    workspace_walk_forward.add_argument("--profile", required=True)
    workspace_walk_forward.add_argument("--output")
    workspace_accounting_replay = workspace_commands.add_parser(
        "archived-accounting-replay",
        help="Score filing-time forecasts from content-addressed SEC evidence.",
    )
    workspace_accounting_replay.add_argument("--as-of")
    workspace_accounting_replay.add_argument("--source-id", action="append")
    workspace_accounting_replay.add_argument("--output")
    workspace_execution = workspace_commands.add_parser(
        "execution-market",
        help="Run a verified deterministic/direct-agent/agent-program valuation tournament.",
    )
    workspace_execution.add_argument("--decision-id")
    workspace_execution.add_argument("--program-id")
    workspace_execution.add_argument("--output")
    workspace_closed_book_open = workspace_commands.add_parser(
        "closed-book-open",
        help="Freeze one prospective source packet and sealed candidate forecast set.",
    )
    workspace_closed_book_open.add_argument("--decision-id")
    workspace_closed_book_open.add_argument("--paper-watch-decision-id")
    workspace_closed_book_open.add_argument("--candidate-leaf")
    workspace_closed_book_open.add_argument("--benchmark-id", default="SPY")
    workspace_closed_book_open.add_argument("--probe-weight", type=float, default=0.05)
    workspace_closed_book_open.add_argument("--horizon-days", type=int, default=90)
    workspace_closed_book_open.add_argument("--output")
    workspace_closed_book_settle = workspace_commands.add_parser(
        "closed-book-settle",
        help="Settle every due forecast window from cached point-in-time prices.",
    )
    workspace_closed_book_settle.add_argument("--as-of")
    workspace_closed_book_settle.add_argument("--output")
    workspace_market_state = workspace_commands.add_parser(
        "market-state-cycle",
        help="Refresh the public market-state bundle, settle matured outcomes, and issue due forecasts.",
    )
    workspace_market_state.add_argument("--refresh-sources", action="store_true")
    workspace_market_state.add_argument("--force", action="store_true")
    workspace_market_state.add_argument("--output")
    workspace_learning = workspace_commands.add_parser(
        "institutional-learning",
        help="Compile cohort phenotypes and challenge the current investment-law catalog.",
    )
    workspace_learning.add_argument("--output")
    workspace_parser.set_defaults(handler=_workspace)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        return int(args.handler(args))
    except (KeyError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ztare investment: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
