import json

import pytest
import yaml

from ztare.common.equivariance import stable_sha256
from ztare.leanmill import work_queue
from ztare.investment import workspace as investment_workspace
from ztare.investment import research_agent as investment_research_agent
from ztare.investment.discovery import default_discovery_policy
from ztare.investment.research_jobs import default_enrichment_policy
from ztare.investment.universe import enroll_public_funds
from ztare.investment.universe import repair_public_fund_sources
from ztare.investment.workspace import (
    BROAD_FUND_ACQUISITION_JOB_KIND,
    WORKSPACE_SCHEMA,
    _broad_fund_acquisition_status,
    _broad_fund_queue_rows,
    _compile_workspace_broad_fund_acquisition,
    _finish_broad_fund_acquisition,
    _prepare_broad_fund_acquisition,
    build_read_model,
    fund_lookthrough_acquisition_status,
    read_cached_read_model,
    run_workspace_discovery_service,
    run_workspace_scheduled_market_scouts,
)


def _sealed(body, field):
    return {**body, field: stable_sha256(body)}


def _write(path, payload, *, yaml_payload=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False) if yaml_payload else json.dumps(payload),
        encoding="utf-8",
    )


def test_candidate_prompt_projects_only_the_frozen_selected_question():
    request = {
        "request_sha256": "r" * 64,
        "research_question_frontier": {
            "schema": "frontier", "question_frontier_sha256": "f" * 64,
            "selected_program": {"program_id": "selected", "atom_ids": ["a"]},
            "frontier_programs": [{"program_id": "unused"}],
            "grammar": {"terminals": ["unused"]},
        },
    }
    projected = investment_research_agent._research_request_prompt_projection(request)
    assert projected["request_sha256"] == request["request_sha256"]
    assert projected["research_question_frontier"]["selected_program"]["program_id"] == "selected"
    assert "frontier_programs" not in projected["research_question_frontier"]


def test_fund_lookthrough_heartbeat_reuses_plan_before_cadence(tmp_path, monkeypatch):
    policy = {
        "enabled": True, "max_source_calls": 9, "configured_max_source_calls": 9,
        "cadence_hours": 24.0, "cadence_owner": "discovery_policy",
        "source_budget_owner": "enrichment_policy", "policy_sha256": "p" * 64,
    }
    payloads = {
        "portfolio-acquisition-latest.json": {"completed_at": "2026-08-14T12:00:00Z", "acquisition_sha256": "a" * 64},
        "fund_lookthrough_service.json": {"schema": investment_workspace.FUND_LOOKTHROUGH_AUTONOMY_SCHEMA, "current_plan_sha256": "n" * 64, "last_acquisition_sha256": "a" * 64, "selected_entity_ids": ["A", "B"], "policy": policy},
    }
    monkeypatch.setattr(investment_workspace, "load_workspace_config", lambda *_: (tmp_path, {}))
    monkeypatch.setattr(investment_workspace, "_read_json", lambda path: payloads.get(path.name))
    monkeypatch.setattr(investment_workspace, "_fund_lookthrough_policy", lambda *_: policy)
    monkeypatch.setattr(
        investment_workspace, "compile_workspace_fund_lookthrough_acquisition_plan",
        lambda *_args, **_kwargs: pytest.fail("not-due heartbeat recompiled the plan"),
    )

    status = fund_lookthrough_acquisition_status(
        tmp_path, now="2026-08-14T12:05:00Z",
    )

    assert status["status"] == "not_due"
    assert status["selected_entity_ids"] == ["A", "B"]
    assert status["current_plan_sha256"] == "n" * 64


def test_research_queue_recompiles_once_after_discovery_epoch_change(tmp_path, monkeypatch):
    latest = tmp_path / "discovery" / "latest.json"
    _write(latest, {"run_id": "run-1", "run_sha256": "1" * 64})
    calls = []

    def compile_queue(root):
        calls.append(root)
        if len(calls) == 1:
            _write(latest, {"run_id": "run-2", "run_sha256": "2" * 64})
            raise investment_research_agent._DiscoveryEpochChanged("superseded")
        return {
            "schema": "jaggedthoughts-subscription-research-enqueue-v1",
            "discovery_run_id": "run-2", "discovery_run_sha256": "2" * 64,
        }

    monkeypatch.setattr(
        investment_research_agent, "_enqueue_research_request_jobs_unlocked", compile_queue,
    )
    result = investment_research_agent.enqueue_research_request_jobs(tmp_path)

    assert len(calls) == 2
    assert result["discovery_run_id"] == "run-2"


def _ready_watchlist(symbols):
    candidates = []
    for symbol in symbols:
        analysis = _sealed({
            "schema": "jaggedthoughts-factor-analysis-v1",
            "candidate_entity_id": symbol,
        }, "analysis_sha256")
        candidates.append({
            "entity_id": symbol,
            "screen_status": "qualified",
            "analysis": analysis,
            "valuation": {"kind": "aggregate"},
            "fund_evidence": {
                "source_refs": [f"issuer:{symbol}"],
                "metrics": {
                    "portfolio_top10_concentration": 0.3,
                    "fund_net_assets": 1_000_000,
                },
            },
        })
    return _sealed({
        "schema": "jaggedthoughts-opportunity-watchlist-result-v1",
        "watchlist_id": "regional-funds",
        "as_of": "2026-08-13T00:00:00Z",
        "candidates": candidates,
    }, "watchlist_sha256")


def test_fund_source_repair_updates_all_profiles_and_rejects_duplicate_identity(tmp_path):
    _write(tmp_path / "sources.yaml", {
        "schema": "jaggedthoughts-public-source-manifest-v1", "sources": [], "signals": [],
    }, yaml_payload=True)
    for filename, watchlist_id, symbol in (
        ("value.yaml", "value", "IVE"), ("neutral.yaml", "neutral", "EFV"),
    ):
        _write(tmp_path / "watchlists" / filename, {
            "schema": "jaggedthoughts-opportunity-watchlist-v1",
            "watchlist_id": watchlist_id,
            "candidates": [{
                "entity_id": symbol, "name": f"iShares {symbol} ETF",
                "valuation_inputs": [],
            }],
        }, yaml_payload=True)

    repaired = repair_public_fund_sources(tmp_path)
    assert set(repaired["watchlist_sha256s"]) == {
        "watchlists/neutral.yaml", "watchlists/value.yaml",
    }
    assert repaired["watchlist_sha256"] == stable_sha256(
        repaired["watchlist_sha256s"]
    )
    assert {row["ticker"] for row in repaired["configured"]} == {"IVE", "EFV"}

    duplicate = yaml.safe_load((tmp_path / "watchlists/neutral.yaml").read_text())
    duplicate["candidates"].append({"entity_id": "IVE", "name": "Duplicate"})
    _write(tmp_path / "watchlists/neutral.yaml", duplicate, yaml_payload=True)
    with pytest.raises(ValueError, match="multiple watchlists"):
        repair_public_fund_sources(tmp_path)


def test_recurring_service_queues_exact_fund_residuals_once_then_stops(tmp_path, monkeypatch):
    symbols = ("IWD", "IWS", "EFAV", "EFV")
    names = {
        "IWD": "iShares Russell 1000 Value ETF",
        "IWS": "iShares Russell 1000 Value Peer ETF",
        "EFAV": "iShares MSCI EAFE Value ETF",
        "EFV": "iShares MSCI EAFE Value Peer ETF",
    }
    catalog_body = {
        "schema": "jaggedthoughts-public-market-catalog-v1",
        "retrieved_at": "2026-08-13T00:00:00Z",
        "security_count": len(symbols),
        "source_receipts": [{
            "source_id": "public-funds",
            "raw_path": "universe/raw/public-funds.json",
            "content_sha256": "a" * 64,
        }],
        "securities": [{
            "security_id": f"public_fund:{symbol}",
            "symbol": symbol,
            "name": names[symbol],
            "entity_kind": "public_fund",
            "security_kind": "exchange_traded_fund",
            "last_price": 25.0,
            "source_id": "public-funds",
            "source_path": "universe/raw/public-funds.json",
            "available_at": "2026-08-13T00:00:00Z",
        } for symbol in symbols],
    }
    market_policy = {
        "schema": "jaggedthoughts-market-scout-policy-v1",
        "enabled": True,
        "catalog_refresh_hours": 24,
        "default_max_results": 50,
        "intents": [
            {"id": "broad-public-funds", "enabled": True, "mode": "broad_fund"},
            {"id": "saved-mid-cap-funds", "enabled": True, "query": "Find US mid-cap value funds"},
        ],
        "activation_boundary": "research queues only",
    }
    config = {
        "schema": WORKSPACE_SCHEMA,
        "name": "fund-cycle-test",
        "owner": "test",
        "source_manifest": "sources.yaml",
        "market_scout_policy": "research_jobs/intents.yaml",
        "enrichment_policy": "research_jobs/enrichment_policy.yaml",
        "discovery_policy": "discovery.yaml",
    }
    _write(tmp_path / "workspace.yaml", config, yaml_payload=True)
    _write(tmp_path / "research_jobs/intents.yaml", market_policy, yaml_payload=True)
    _write(tmp_path / "research_jobs/enrichment_policy.yaml", default_enrichment_policy(), yaml_payload=True)
    _write(tmp_path / "discovery.yaml", default_discovery_policy(), yaml_payload=True)
    _write(tmp_path / "sources.yaml", {
        "schema": "jaggedthoughts-public-source-manifest-v1", "sources": [], "signals": [],
    }, yaml_payload=True)
    _write(tmp_path / "watchlists/public_fund_opportunities.yaml", {
        "schema": "jaggedthoughts-opportunity-watchlist-v1",
        "watchlist_id": "public-fund-opportunities",
        "as_of": "latest_source_run",
        "candidates": [],
    }, yaml_payload=True)
    _write(tmp_path / "watchlists/public_equity_etf_opportunities.yaml", {
        "schema": "jaggedthoughts-opportunity-watchlist-v1",
        "watchlist_id": "public-equity-etf-opportunities",
        "as_of": "latest_source_run",
        "candidates": [],
    }, yaml_payload=True)
    _write(tmp_path / "universe/catalog-latest.json", _sealed(catalog_body, "catalog_sha256"))
    _write(tmp_path / "data/latest_source_run.json", _sealed({
        "schema": "jaggedthoughts-public-source-run-v1",
        "as_of": "2026-08-13T00:00:00Z",
    }, "run_sha256"))

    scout_cycle = run_workspace_scheduled_market_scouts(
        tmp_path, now="2026-08-13T00:30:00Z",
    )
    assert [(row["intent_id"], row["mode"]) for row in scout_cycle["results"]] == [
        ("broad-public-funds", "broad_fund"),
        ("saved-mid-cap-funds", "language"),
    ]

    enrichment_policy = default_enrichment_policy()
    first = _prepare_broad_fund_acquisition(
        root=tmp_path, config=config, policy=enrichment_policy,
        base_refresh_source_ids=set(),
    )
    second = _prepare_broad_fund_acquisition(
        root=tmp_path, config=config, policy=enrichment_policy,
        base_refresh_source_ids=set(),
    )
    queue_rows = _broad_fund_queue_rows(tmp_path)
    assert first["reserved_funds"] == second["reserved_funds"] == 2
    assert len(queue_rows) == 2
    assert {row["kind"] for row in queue_rows} == {BROAD_FUND_ACQUISITION_JOB_KIND}
    assert {row["attempts"] for row in queue_rows} == {1}
    assert all(str(row["work_id"]).startswith("fund-source:") for row in queue_rows)
    enrolled_candidates = yaml.safe_load(
        (tmp_path / "watchlists/public_equity_etf_opportunities.yaml").read_text(encoding="utf-8")
    )["candidates"]
    assert all(row.get("implementation_sleeve_source_refs") for row in enrolled_candidates)
    assert {row.get("implementation_sleeve_id") for row in enrolled_candidates} <= {
        "us_equity", "international_equity"
    }
    assert all(row.get("peer_group_id") and row.get("comparison_cell") for row in enrolled_candidates)
    assert not yaml.safe_load(
        (tmp_path / "watchlists/public_fund_opportunities.yaml").read_text(encoding="utf-8")
    )["candidates"]
    with pytest.raises(FileExistsError):
        enroll_public_funds(
            tmp_path, watchlist_path="watchlists/public_fund_opportunities.yaml",
            funds=[{"ticker": enrolled_candidates[0]["entity_id"], "name": "Duplicate"}],
        )
    with pytest.raises(ValueError, match="non-equity"):
        enroll_public_funds(
            tmp_path, watchlist_path="watchlists/public_equity_etf_opportunities.yaml",
            funds=[{
                "ticker": "BOND", "name": "Bond ETF", "peer_group_id": "fixed-income",
                "comparison_cell": {"asset_class": "fixed_income"},
            }],
        )

    _write(tmp_path / "watchlists/results/regional-funds.json", _ready_watchlist(symbols))
    _scout, post_plan = _compile_workspace_broad_fund_acquisition(
        tmp_path, config, compiled_at="2026-08-13T01:00:00Z",
    )
    _finish_broad_fund_acquisition(root=tmp_path, context=first, post_plan=post_plan)
    status = _broad_fund_acquisition_status(tmp_path, next_due_at="2026-08-14T00:00:00Z")
    assert post_plan["new_job_count"] == 0
    assert {
        (group["peer_group"]["region"], tuple(row["entity_id"] for row in group["members"]))
        for group in post_plan["completed_peer_groups"]
    } == {
        ("us", ("IWD", "IWS")),
        ("developed_ex_us", ("EFAV", "EFV")),
    }
    assert status["status"] == "comparison_ready"
    assert status["ready_group_count"] == 2
    assert status["residual_peer_group_count"] == 0
    assert status["comparison_coverage_fraction"] == 1.0
    assert status["residual_job_count"] == 0
    assert status["next_due_at"] is None
    assert {row["status"] for row in _broad_fund_queue_rows(tmp_path)} == {"done"}
    stopped = _prepare_broad_fund_acquisition(
        root=tmp_path, config=config, policy=enrichment_policy,
        base_refresh_source_ids=set(),
    )
    assert stopped["reserved_funds"] == 0
    assert stopped["claimed_jobs"] == []

    status = _broad_fund_acquisition_status(tmp_path, next_due_at="2026-08-14T00:00:00Z")
    read_model = build_read_model(tmp_path)
    assert read_model["broad_fund_acquisition"] == status
    stale_read_model = dict(read_model)
    stale_read_model.pop("broad_fund_acquisition")
    _write(tmp_path / "state/read_model.json", stale_read_model)
    assert read_cached_read_model(tmp_path)["broad_fund_acquisition"] == status
    assert [row["id"] for row in market_policy["intents"]] == [
        "broad-public-funds", "saved-mid-cap-funds",
    ]

    monkeypatch.setattr(investment_workspace, "run_workspace_discovery", lambda *_args, **_kwargs: {
        "status": "not_due",
        "schedule": {"next_due_at": "2026-08-14T00:00:00Z"},
        "latest_run": {
            "run_id": "discovery-test", "run_sha256": "d" * 64,
            "completed_at": "2026-08-13T00:00:00Z",
        },
        "broad_fund_acquisition": status,
    })
    monkeypatch.setattr(investment_workspace, "research_agent_status", lambda _root: {
        "enabled": True, "runtime": "codex", "runtime_executable": "/usr/bin/codex",
        "transport": "operator_subscription_cli",
        "daily_dispatch_budget": {"exhausted": True},
        "queue": {"by_status": {"queued": 1}, "jobs": [{
            "work_id": "research:one", "kind": "subscription_research",
            "status": "queued", "payload": {},
        }]},
        "service": {"status": "running"},
    })
    monkeypatch.setattr(investment_workspace, "_utc_now", lambda: "2026-08-13T05:45:00Z")
    monkeypatch.setattr(
        investment_workspace, "run_workspace_fund_lookthrough_acquisition",
        lambda *_args, **_kwargs: {
            "status": "not_due", "next_action": "wait_for_discovery_cadence",
            "next_due_at": "2026-08-14T00:00:00Z", "selected_entity_ids": ["A"],
            "current_plan_sha256": "f" * 64, "capital_authority": False,
        },
    )
    heartbeat = run_workspace_discovery_service(tmp_path, once=True)
    assert heartbeat["last_action"] == "not_due"
    assert heartbeat["broad_fund_acquisition_status"] == "comparison_ready"
    assert heartbeat["broad_fund_acquisition_next_due_at"] is None
    assert heartbeat["fund_lookthrough"] == {
        "status": "not_due", "next_action": "wait_for_discovery_cadence",
        "next_due_at": "2026-08-14T00:00:00Z", "selected_entity_ids": ["A"],
        "current_plan_sha256": "f" * 64, "last_acquisition_sha256": None,
        "source_run_sha256": None, "source_selection_sha256": None,
        "capital_authority": False,
    }
    activation = heartbeat["periodic_activation"]
    assert activation["status"] == "blocked"
    assert activation["last_activation"]["discovery_run_id"] == "discovery-test"
    assert activation["next_activation"]["work_id"] == "research:one"
    assert activation["next_activation"]["at"] == "2026-08-14T00:00:00Z"
    assert activation["blocked_activation"]["reasons"] == [
        "daily_subscription_dispatch_budget_exhausted",
    ]
    assert activation["source_boundary"] == {
        "contract": "cached_public_bytes_with_observed_and_available_times",
        "discovery_run_sha256": "d" * 64,
        "candidate_leaf_count": 0,
        "research_transport": "operator_subscription_cli",
        "runtime": "codex",
    }
    assert activation["capital_authority"] is False


def test_periodic_service_defers_a_ready_broad_fund_plan_to_discovery_cadence(
    tmp_path, monkeypatch,
):
    _write(tmp_path / "workspace.yaml", {
        "schema": WORKSPACE_SCHEMA, "name": "fund-due-test", "owner": "test",
        "discovery_policy": "discovery.yaml",
    }, yaml_payload=True)
    _write(tmp_path / "discovery.yaml", default_discovery_policy(), yaml_payload=True)
    _write(tmp_path / "research_jobs/fund_acquisition/latest.json", {
        "status": "ready_to_enqueue",
    })
    monkeypatch.setattr(
        investment_workspace, "discovery_schedule_status",
        lambda **_kwargs: {"due": False, "next_due_at": "2026-08-14T00:00:00Z"},
    )
    monkeypatch.setattr(
        investment_workspace, "run_workspace_scheduled_market_scouts",
        lambda _root: {"status": "not_due"},
    )
    calls = []
    monkeypatch.setattr(
        investment_workspace, "_prepare_autonomous_enrichment",
        lambda **_kwargs: calls.append("prepared") or {
            "broad_fund_acquisition": {"claimed_jobs": []},
            "refresh_source_ids": [],
        },
    )
    monkeypatch.setattr(
        investment_workspace, "refresh_workspace_sources",
        lambda *_args, **_kwargs: {"ok": True, "as_of": "2026-08-13T00:00:00Z"},
    )
    monkeypatch.setattr(
        investment_workspace, "_compile_current_discovery_epoch",
        lambda *_args, **_kwargs: (
            {"ok": True}, {"run_id": "run", "run_sha256": "r" * 64}, {},
        ),
    )
    monkeypatch.setattr(
        investment_workspace, "_compile_workspace_broad_fund_acquisition",
        lambda *_args, **_kwargs: (None, {"status": "ready_to_enqueue"}),
    )
    monkeypatch.setattr(investment_workspace, "_finish_broad_fund_acquisition", lambda **_kwargs: None)
    monkeypatch.setattr(investment_workspace, "_finalize_autonomous_enrichment", lambda **_kwargs: {})
    monkeypatch.setattr(investment_workspace, "_ensure_qualified_research_requests", lambda *_args: {})
    monkeypatch.setattr(
        investment_workspace, "enqueue_research_request_jobs",
        lambda _root: {
            "discovery_run_id": "run", "discovery_run_sha256": "r" * 64,
        },
    )
    monkeypatch.setattr(
        investment_workspace, "build_read_model",
        lambda _root: {"broad_fund_acquisition": {"status": "acquiring"}},
    )

    action = investment_workspace.run_workspace_discovery(tmp_path)

    assert calls == []
    assert action["status"] == "not_due"


def test_subscription_service_survives_error_and_marks_stale_heartbeat(tmp_path, monkeypatch):
    _write(tmp_path / "workspace.yaml", {
        "schema": WORKSPACE_SCHEMA, "name": "service-test", "owner": "test",
        "enrichment_policy": "research_jobs/enrichment_policy.yaml",
    }, yaml_payload=True)
    policy = default_enrichment_policy()
    policy["agent_research"] = {
        "enabled": True, "runtime": "codex", "model": "account-default",
        "reasoning_effort": "high", "timeout_seconds": 60,
        "lease_seconds": 120, "poll_seconds": 5, "max_attempts": 1,
        "max_dispatches_per_day": 1,
    }
    _write(tmp_path / "research_jobs/enrichment_policy.yaml", policy, yaml_payload=True)
    monkeypatch.setattr(
        investment_research_agent, "run_research_agent_once",
        lambda _root: (_ for _ in ()).throw(ValueError("broken queue")),
    )
    heartbeat = investment_research_agent.run_research_agent_service(tmp_path, once=True)
    assert heartbeat["status"] == "checked_once"
    assert heartbeat["ok"] is False
    assert heartbeat["last_error"] == "ValueError: broken queue"

    _write(tmp_path / "state/research_agent_service.json", {
        **heartbeat, "status": "dispatching", "ok": True,
        "checked_at": "2026-08-13T00:00:00Z", "poll_seconds": 5,
    })
    monkeypatch.setattr(investment_research_agent, "_utc_now", lambda: "2026-08-13T00:01:00Z")
    assert investment_research_agent.research_agent_status(tmp_path)["service"]["status"] == "dispatching"

    _write(tmp_path / "state/research_agent_service.json", {
        **heartbeat, "status": "running", "ok": True,
        "checked_at": "2026-08-13T00:00:00Z", "poll_seconds": 5,
    })
    monkeypatch.setattr(investment_research_agent, "_utc_now", lambda: "2026-08-13T00:01:00Z")
    service = investment_research_agent.research_agent_status(tmp_path)["service"]
    assert service["status"] == "stale"
    assert service["restart_command"] == "workspace research-agent"


def test_subscription_queue_retires_obsolete_candidate_and_monitor_epochs(tmp_path):
    current = {
        "equity:ALPHA": {
            "candidate_sha256": "c" * 64, "candidate_leaf": "d" * 64,
        },
    }
    requests = {
        "activation-old.json": {
            "candidate_id": "equity:ALPHA", "candidate_sha256": "a" * 64,
            "candidate_leaf": "b" * 64, "request_sha256": "1" * 64,
        },
        "activation-current.json": {
            "candidate_id": "equity:ALPHA", **current["equity:ALPHA"],
            "request_sha256": "2" * 64,
        },
        "activation-removed.json": {
            "candidate_id": "retired:ALPHA", "candidate_sha256": "e" * 64,
            "candidate_leaf": "f" * 64, "request_sha256": "5" * 64,
        },
        "reopen-old.json": {
            "entity_id": "ALPHA", "subscription_leaf": "old-sub",
            "request_sha256": "3" * 64, "created_at": "2026-08-12T00:00:00Z",
            "trigger_receipt": {"source_id": "sec_alpha"},
        },
        "reopen-current.json": {
            "entity_id": "ALPHA", "subscription_leaf": "current-sub",
            "request_sha256": "4" * 64, "created_at": "2026-08-13T00:00:00Z",
            "trigger_receipt": {"source_id": "sec_alpha"},
        },
    }
    for name, request in requests.items():
        _write(tmp_path / "requests" / name, request)
    jobs = [
        ("activation-old", investment_research_agent.ACTIVATION_RESEARCH_JOB_KIND,
         {"dossier_request_path": "requests/activation-old.json"}),
        ("activation-current", investment_research_agent.ACTIVATION_RESEARCH_JOB_KIND,
         {"dossier_request_path": "requests/activation-current.json"}),
        ("activation-removed", investment_research_agent.ACTIVATION_RESEARCH_JOB_KIND,
         {"dossier_request_path": "requests/activation-removed.json"}),
        ("reopen-old", investment_research_agent.REASSESSMENT_JOB_KIND,
         {"request_path": "requests/reopen-old.json"}),
        ("reopen-current", investment_research_agent.REASSESSMENT_JOB_KIND,
         {"request_path": "requests/reopen-current.json"}),
    ]
    connection = work_queue.connect(str(tmp_path / "state/research_jobs.sqlite3"))
    try:
        for work_id, kind, payload in jobs:
            work_queue.enqueue(
                connection, kind=kind, priority=1,
                payload={"work_id": work_id, **payload},
            )
    finally:
        connection.close()

    settled = investment_research_agent._settle_superseded_research_jobs(
        tmp_path, policy={"lease_seconds": 120}, candidate_index=current,
        covered_requests={"2" * 64: "coverage-leaf"},
        current_subscription_by_entity={"ALPHA": "current-sub"},
    )
    connection = work_queue.connect(str(tmp_path / "state/research_jobs.sqlite3"))
    try:
        rows = {row["work_id"]: row for row in work_queue.list_items(connection)}
    finally:
        connection.close()
    assert set(settled["superseded"]) == {
        "activation-old", "activation-removed", "reopen-old",
    }
    assert settled["covered"] == ["activation-current"]
    assert rows["activation-old"]["payload"]["provider_called"] is False
    assert rows["reopen-old"]["payload"]["current_subscription_leaf"] == "current-sub"
    assert rows["activation-current"]["payload"]["coverage_leaf"] == "coverage-leaf"
    assert rows["reopen-current"]["status"] == "queued"


def test_subscription_queue_retires_terminal_strategy_source_gap(tmp_path):
    request = {
        "request_id": "peer:GFS", "request_sha256": "a" * 64,
        "peer_entity_id": "GFS",
    }
    _write(tmp_path / "research_jobs/strategy_cohorts/requests/request.json", request)
    _write(tmp_path / "institutional_learning/strategy_cohorts/latest.json", {
        "requests": [request],
    })
    _write(tmp_path / "institutional_learning/strategy_cohorts/panel-readiness.json", {
        "history_status": [{"entity_id": "GFS", "status": "excluded_source_gap"}],
    })
    connection = work_queue.connect(str(tmp_path / "state/research_jobs.sqlite3"))
    try:
        work_queue.enqueue(
            connection, kind=investment_research_agent.STRATEGY_COHORT_JOB_KIND,
            priority=1, payload={
                "work_id": "strategy-gap",
                "request_path": "research_jobs/strategy_cohorts/requests/request.json",
            },
        )
    finally:
        connection.close()

    settled = investment_research_agent._settle_superseded_research_jobs(
        tmp_path, policy={"lease_seconds": 120}, candidate_index={},
    )
    connection = work_queue.connect(str(tmp_path / "state/research_jobs.sqlite3"))
    try:
        row = work_queue.list_items(connection)[0]
    finally:
        connection.close()
    assert settled["terminal"] == ["strategy-gap"]
    assert row["status"] == "done"
    assert row["payload"]["stage"] == "terminal_source_gap"
    assert row["payload"]["provider_called"] is False


def test_strategy_control_classification_hydrates_missing_accounting_history(
    tmp_path, monkeypatch,
):
    from ztare.investment import company_quality, sources, universe

    (tmp_path / "data").mkdir()
    (tmp_path / "data/observations.csv").write_text("header\n", encoding="utf-8")
    calls = []
    monkeypatch.setattr(company_quality, "compile_company_quality_history", lambda **_: ())
    monkeypatch.setattr(universe, "public_equity_is_enrolled", lambda *_: False)
    monkeypatch.setattr(
        universe, "enroll_public_equity",
        lambda *_args, **_kwargs: {"enrollment_sha256": "e" * 64},
    )
    monkeypatch.setattr(
        sources, "consume_public_sources",
        lambda *_args, **kwargs: calls.append(kwargs["source_ids"]) or {
            "run_sha256": "r" * 64,
            "source_statuses": [{"source_id": "sec_klra_companyfacts", "status": "consumed"}],
        },
    )
    status = investment_research_agent._hydrate_strategy_control_history(
        tmp_path,
        request={"peer_entity_id": "KLRA", "search_end_at": "2026-08-13T00:00:00Z"},
        result={"classification": "no_family_adoption_found"},
    )
    assert calls == [("sec_klra_companyfacts",)]
    assert status["status"] == "source_gap"
    assert status["history_role"] == "strict_control"
    assert status["source_called"] is True

    active = investment_research_agent._hydrate_strategy_control_history(
        tmp_path,
        request={"peer_entity_id": "Q", "search_end_at": "2026-08-13T00:00:00Z"},
        result={"classification": "family_adoption_only"},
    )
    assert active["history_role"] == "active_comparator"
    assert calls[-1] == ("sec_q_companyfacts",)
