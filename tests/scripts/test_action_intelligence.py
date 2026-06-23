from __future__ import annotations

import importlib.util
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "action_intelligence_under_test",
    REPO / "scripts" / "public" / "control" / "action_intelligence.py",
)
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _patch_sources(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(module, "DECISION_USE_LEDGER", tmp_path / "decision_use.jsonl")
    monkeypatch.setattr(module, "ACTION_IMPACT_LEDGER", tmp_path / "action_impact.jsonl")
    monkeypatch.setattr(module, "SURFACING_EVENT_LEDGER", tmp_path / "surfacing_event.jsonl")
    monkeypatch.setattr(module, "GP233_LEDGER", tmp_path / "gp233.md")
    monkeypatch.setattr(module, "CATCH_LEDGER", tmp_path / "catch.jsonl")
    monkeypatch.setattr(module, "TRAJECTORY_ARCHIVE", tmp_path / "trajectory_archive.jsonl")
    monkeypatch.setattr(
        module,
        "TRAJECTORY_ARCHIVE_ENRICHED",
        tmp_path / "trajectory_archive_enriched.jsonl",
    )
    monkeypatch.setattr(module, "BIFURCATION_REPORT", tmp_path / "bifurcation_report.json")
    _write_jsonl(tmp_path / "trajectory_archive_enriched.jsonl", [{"ok": True}])
    _write_json(tmp_path / "bifurcation_report.json", {"bifurcation": {"agent_work_share": 0.8}})


def test_primitive_miss_queue_surfaces_promotion_review_recommendation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    queue = tmp_path / "primitive_amnesia_miss_queue.jsonl"
    monkeypatch.setattr(module, "PRIMITIVE_MISS_QUEUE", queue)
    _write_jsonl(
        queue,
        [
            {
                "miss_id": "missing-target",
                "status": "open",
                "case_id": "case-missing",
                "query": "compile residual failure into graph operator",
                "targets": ["residual_graph_compiler"],
                "miss_kind": "benchmark_target_unresolved",
                "ranker": "semantic",
                "recorded_at": "2026-06-13T00:00:00+00:00",
                "target_resolution": {"resolved": False, "matches": []},
                "top_candidates": [],
                "repair_policy": "check duplicate before adding anything",
            }
        ],
    )

    recs = module.primitive_promotion_recommendations(action_rows=[])

    assert len(recs) == 1
    rec = recs[0]
    assert rec["domain"] == "trajectory_surfacing"
    assert rec["source"] == "primitive_amnesia_miss_queue"
    assert rec["recommended_action"] == "surface_primitive_promotion_review"
    assert rec["surface"]["surface_kind"] == "primitive_promotion_review"
    assert rec["surface"]["miss_id"] == "missing-target"
    assert rec["surface"]["promotion_decision"] == "review_missing_catalog_or_benchmark_target"
    assert rec["surface"]["typed_carrier"] == "primitive_catalog_candidate_or_benchmark_repair"
    assert rec["blocking_checks"] == ["primitive_promotion_review_unconsumed"]
    assert rec["execution_authority"] == "none_advisory_only"


def test_primitive_promotion_review_surfacing_event_becomes_action_row() -> None:
    event = {
        "schema_version": 1,
        "surface_id": "sf_primitive_review_fixture",
        "surface_kind": "primitive_promotion_review",
        "surface_payload_ref": (
            "analytics/public/queries/primitive_amnesia_miss_queue.jsonl#missing-target"
        ),
        "project_family": "primitive_amnesia",
        "target_decision_id": "primitive_review_missing_target",
        "shown_at": "2026-06-13T00:00:00Z",
        "rank": 1,
        "consumed_bool": True,
        "consumed_at": "2026-06-13T00:05:00Z",
        "consumed_by_tick": "tick-primitive-review",
        "suppressed_reason": None,
        "negative_externality_tags": [],
        "selected_action": "surface_primitive_promotion_review",
        "policy_source": "rd",
        "decision_impact": "opened_non_promotion_review",
        "yield_signal": "diagnostic",
        "outcome_known": True,
        "notes": "review consumed by primitive-amnesia repair pass",
        "promotion_decision": "review_missing_catalog_or_benchmark_target",
        "typed_carrier": "primitive_catalog_candidate_or_benchmark_repair",
        "nearest_confuser": "none",
    }

    assert module.validate_surfacing_event(event) == []
    row = module.surfacing_event_to_action_impact(event)

    assert row is not None
    assert row["selected_action"] == "surface_primitive_promotion_review"
    assert row["decision_point"]["domain"] == "trajectory_surfacing"
    assert row["source_refs"]["trajectory_refs"] == [event["surface_payload_ref"]]
    assert row["source_refs"]["source_refs"] == [event["surface_payload_ref"]]
    assert row["context_features"]["surface_kind"] == "primitive_promotion_review"
    assert row["context_features"]["promotion_decision"] == event["promotion_decision"]
    assert row["context_features"]["typed_carrier"] == event["typed_carrier"]
    assert module.validate_action_impact(row) == []


def test_source_health_warns_when_bifurcation_lacks_workbench_decision_rows(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_sources(monkeypatch, tmp_path)

    health = module.source_health_model(action_rows=[])

    issue_types = {issue["issue_type"] for issue in health["issues"]}
    assert "missing_agentic_workbench_decision_rows" in issue_types


def test_health_parser_accepts_json_flag() -> None:
    parser = module.build_parser()

    args = parser.parse_args(["health", "--json"])

    assert args.cmd == "health"
    assert args.json is True


def test_recommendation_id_ignores_generated_at() -> None:
    payload = {
        "schema_version": 1,
        "generated_at": "2026-06-22T00:00:00Z",
        "domain": "trajectory_surfacing",
        "decision_id": "decision_fixture",
        "recommended_action": "surface_trajectory_cluster",
        "evidence_refs": ["trajectory.jsonl#cluster"],
    }
    same_payload_later = {**payload, "generated_at": "2026-06-22T01:00:00Z"}
    changed_payload = {**payload, "recommended_action": "repair_source_emitter"}

    assert module.recommendation_id(payload) == module.recommendation_id(same_payload_later)
    assert module.recommendation_id(payload) != module.recommendation_id(changed_payload)


def test_source_health_does_not_double_count_missing_surfacing_events(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_sources(monkeypatch, tmp_path)

    health = module.source_health_model(action_rows=[])

    surface_issues = [
        issue for issue in health["issues"]
        if issue["scope"] == "trajectory_surfacing"
        and issue["issue_type"] == "unconsumed_surface"
    ]
    assert len(surface_issues) == 1
    assert surface_issues[0]["denominator"] == "surfacing event rows"


def test_source_health_flags_unconsumed_surfacing_events_once(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_sources(monkeypatch, tmp_path)
    _write_jsonl(
        tmp_path / "surfacing_event.jsonl",
        [
            {
                "schema_version": 1,
                "surface_id": "sf_shown",
                "surface_kind": "trajectory_cluster",
                "surface_payload_ref": "analytics/public/ledgers/trajectory/trajectory_archive.jsonl#cluster",
                "project_family": "fixture",
                "target_decision_id": "decision_fixture",
                "shown_at": "2026-06-13T00:00:00Z",
                "rank": 1,
                "consumed_bool": False,
                "consumed_at": None,
                "consumed_by_tick": None,
                "suppressed_reason": None,
                "negative_externality_tags": [],
                "selected_action": "surface_trajectory_cluster",
                "policy_source": "trajectory_miner",
                "decision_impact": None,
                "yield_signal": None,
                "outcome_known": False,
                "notes": "shown but not consumed",
            }
        ],
    )

    health = module.source_health_model(action_rows=[])

    surface_issues = [
        issue for issue in health["issues"]
        if issue["scope"] == "trajectory_surfacing"
    ]
    assert [issue["issue_type"] for issue in surface_issues] == ["unconsumed_surface"]
    assert surface_issues[0]["denominator"] == "surfacing consumption action-impact rows"


def test_source_health_flags_unmaterialized_consumed_surfacing_events(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_sources(monkeypatch, tmp_path)
    _write_jsonl(
        tmp_path / "surfacing_event.jsonl",
        [
            {
                "schema_version": 1,
                "surface_id": "sf_consumed",
                "surface_kind": "trajectory_cluster",
                "surface_payload_ref": "analytics/public/ledgers/trajectory/trajectory_archive.jsonl#cluster",
                "project_family": "fixture",
                "target_decision_id": "decision_fixture",
                "shown_at": "2026-06-13T00:00:00Z",
                "rank": 1,
                "consumed_bool": True,
                "consumed_at": "2026-06-13T00:05:00Z",
                "consumed_by_tick": "tick-fixture",
                "suppressed_reason": None,
                "negative_externality_tags": [],
                "selected_action": "surface_trajectory_cluster",
                "policy_source": "trajectory_miner",
                "decision_impact": "changed_next_probe",
                "yield_signal": "diagnostic",
                "outcome_known": True,
                "notes": "consumed but not materialized",
            }
        ],
    )

    health = module.source_health_model(action_rows=[])

    surface_issues = [
        issue for issue in health["issues"]
        if issue["scope"] == "trajectory_surfacing"
    ]
    assert [issue["issue_type"] for issue in surface_issues] == [
        "unmaterialized_surfacing_consumption"
    ]
    assert surface_issues[0]["denominator"] == "materialized surfacing action-impact rows"


def test_source_health_accepts_workbench_decision_rows_under_bifurcation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_sources(monkeypatch, tmp_path)
    action_rows = [
        {
            "decision_point": {"domain": "agentic_workbench"},
            "selected_action": "run_out_of_loop_agent",
            "context_features": {
                "workbench_router_decision": "stay_out_of_loop",
                "why_not_autoresearch": "rubric surface missing",
            },
        }
    ]

    health = module.source_health_model(action_rows=action_rows)

    issue_types = {issue["issue_type"] for issue in health["issues"]}
    assert "missing_agentic_workbench_decision_rows" not in issue_types


def test_stay_out_of_loop_requires_bypass_reason() -> None:
    row = {
        "schema_version": 1,
        "action_impact_id": "ai_test_stay_out",
        "recorded_at": "2026-06-11T00:00:00Z",
        "decision_point": {
            "decision_id": "decision_test",
            "domain": "agentic_workbench",
        },
        "candidate_actions": module.AGENTIC_WORKBENCH_ACTIONS,
        "selected_action": "stay_out_of_loop",
        "policy_source": "rd",
        "logged_policy": {
            "logging_policy": "rd_workbench_router",
            "propensity_or_selection_rule": "fixture",
            "eligible_actions": module.AGENTIC_WORKBENCH_ACTIONS,
        },
        "source_refs": {"source_refs": ["analytics/public/queries/rd/autoresearch_routes/fixture.json"]},
        "context_features": {
            "workbench_router_decision": "stay_out_of_loop",
            "why_not_autoresearch": "",
        },
        "outcome": {"known": False},
        "counterfactual": {},
    }

    errors = module.validate_agentic_workbench_impact(row)
    assert any("stay_out_of_loop requires" in error for error in errors)

    row["context_features"]["why_not_autoresearch"] = "no bounded claim yet"
    assert not module.validate_agentic_workbench_impact(row)


def test_ready_workbench_bypass_requires_reason() -> None:
    row = {
        "schema_version": 1,
        "action_impact_id": "ai_test_ready_bypass",
        "recorded_at": "2026-06-11T00:00:00Z",
        "decision_point": {
            "decision_id": "decision_test",
            "domain": "agentic_workbench",
        },
        "candidate_actions": module.AGENTIC_WORKBENCH_ACTIONS,
        "selected_action": "repair_source_emitter",
        "policy_source": "rd",
        "logged_policy": {
            "logging_policy": "rd_workbench_router",
            "propensity_or_selection_rule": "fixture",
            "eligible_actions": module.AGENTIC_WORKBENCH_ACTIONS,
        },
        "source_refs": {"source_refs": ["analytics/public/queries/rd/autoresearch_routes/fixture.json"]},
        "context_features": {
            "workbench_router_decision": "invoke_autoresearch",
            "why_not_autoresearch": "",
        },
        "outcome": {"known": False},
        "counterfactual": {},
    }

    errors = module.validate_agentic_workbench_impact(row)
    assert any("repair_source_emitter requires" in error for error in errors)

    row["context_features"]["why_not_autoresearch"] = "route row emitter needs repair first"
    assert not module.validate_agentic_workbench_impact(row)


def test_agentic_workbench_rows_require_route_json_ref() -> None:
    row = {
        "schema_version": 1,
        "action_impact_id": "ai_test_missing_route_ref",
        "recorded_at": "2026-06-11T00:00:00Z",
        "decision_point": {
            "decision_id": "decision_test",
            "domain": "agentic_workbench",
        },
        "candidate_actions": module.AGENTIC_WORKBENCH_ACTIONS,
        "selected_action": "invoke_autoresearch",
        "policy_source": "rd",
        "logged_policy": {
            "logging_policy": "rd_workbench_router",
            "propensity_or_selection_rule": "fixture",
            "eligible_actions": module.AGENTIC_WORKBENCH_ACTIONS,
        },
        "source_refs": {"source_refs": ["analytics/public/ledgers/action_intelligence/action_impact_ledger.jsonl"]},
        "context_features": {
            "workbench_router_decision": "invoke_autoresearch",
            "why_not_autoresearch": "",
        },
        "outcome": {"known": False},
        "counterfactual": {},
    }

    errors = module.validate_agentic_workbench_impact(row)
    assert "agentic workbench rows require a route JSON source ref" in errors


def test_agentic_workbench_from_args_accepts_named_route_ref() -> None:
    args = module.argparse.Namespace(
        action_impact_id=None,
        recorded_at="2026-06-11T00:00:00Z",
        decision_id="decision_manual_agentic",
        tick_id=None,
        project_id=None,
        project_family="gp_example",
        stage="pretick",
        task="evaluate bounded workbench task",
        selected_action="invoke_autoresearch",
        policy_source="rd",
        selection_rule="rd_workbench_router",
        why_selected="router marked autoresearch ready",
        workbench_router_decision="invoke_autoresearch",
        why_not_autoresearch=None,
        bounded_claim=True,
        stable_evaluator=True,
        rubric_ready=True,
        artifact_surface=True,
        worker_archetype="fungible_agent_worker",
        worker_capability="tool_using_agent",
        worker_state="stateless",
        worker_identity="fungible",
        transport="subscription_cli",
        forecast_contract_id=None,
        gp233_evidence_ref=None,
        route_json_ref="analytics/public/queries/rd/autoresearch_routes/manual.json",
        source_refs_json='["analytics/public/queries/rd/supporting_evidence.json"]',
        prediction_ids_json="[]",
        catch_ids_json="[]",
        outcome_known=False,
        success_bool=None,
        decision_impact=None,
        yield_signal=None,
        actual_cost_agent_minutes=None,
        negative_externality_tags_json="[]",
        baseline_action=None,
        counterfactual_action=None,
        counterfactual_value_bucket=None,
        notes=None,
    )

    row = module.agentic_workbench_impact_from_args(args)

    assert row["source_refs"]["source_refs"][0].endswith("manual.json")
    assert not module.validate_agentic_workbench_impact(row)


def test_source_health_flags_invalid_workbench_rows(tmp_path: Path, monkeypatch) -> None:
    _patch_sources(monkeypatch, tmp_path)
    action_rows = [
        {
            "schema_version": 1,
            "action_impact_id": "ai_invalid_ready_bypass",
            "recorded_at": "2026-06-11T00:00:00Z",
            "decision_point": {
                "decision_id": "decision_test",
                "domain": "agentic_workbench",
            },
            "candidate_actions": module.AGENTIC_WORKBENCH_ACTIONS,
            "selected_action": "repair_source_emitter",
            "policy_source": "rd",
            "logged_policy": {
                "logging_policy": "rd_workbench_router",
                "propensity_or_selection_rule": "fixture",
                "eligible_actions": module.AGENTIC_WORKBENCH_ACTIONS,
            },
            "source_refs": {},
            "context_features": {
                "workbench_router_decision": "invoke_autoresearch",
                "why_not_autoresearch": "",
            },
            "outcome": {"known": False},
            "counterfactual": {},
        }
    ]

    health = module.source_health_model(action_rows=action_rows)

    issue_types = {issue["issue_type"] for issue in health["issues"]}
    assert "invalid_agentic_workbench_rows" in issue_types
    issue = next(
        issue for issue in health["issues"]
        if issue["issue_type"] == "invalid_agentic_workbench_rows"
    )
    invalid = issue["details"]["invalid_rows"][0]
    assert invalid["action_impact_id"] == "ai_invalid_ready_bypass"
    assert invalid["selected_action"] == "repair_source_emitter"
    assert invalid["workbench_router_decision"] == "invoke_autoresearch"
    assert any("requires context_features.why_not_autoresearch" in error for error in invalid["validation_errors"])


def test_agentic_route_json_builds_invoke_row(tmp_path: Path) -> None:
    route_path = tmp_path / "route.json"
    _write_json(
        route_path,
        {
            "decision": "invoke_autoresearch",
            "task": "test bounded claim",
            "project": "gp_example",
            "rubric": "gp_example",
            "bounded_claim": True,
            "stable_evaluator": True,
            "rubric_ready": True,
            "artifact_surface": True,
            "subscription_worker_available": False,
            "missing": [],
            "operator_card_routes": [
                {
                    "card_id": "OP-AWR-01",
                    "name": "Autoresearch Workbench Routing",
                    "route_mode": "lexical_fallback",
                    "score": 9.0,
                    "matched_terms": ["autoresearch_workbench_routing"],
                }
            ],
            "worker_metadata": {
                "worker_archetype": "fungible_agent_worker",
                "worker_capability": "tool_using_agent",
                "worker_state": "stateless_externalized_briefing",
                "worker_identity": "fungible",
                "transport": "subscription_cli",
            },
        },
    )
    args = module.argparse.Namespace(
        route_json=route_path,
        action_impact_id=None,
        recorded_at="2026-06-11T00:00:00Z",
        decision_id="decision_route_invoke",
        tick_id=None,
        project_id=None,
        project_family=None,
        stage="pretick",
        task=None,
        selected_action=None,
        policy_source="rd",
        selection_rule="rd_workbench_router",
        why_selected=None,
        why_not_autoresearch=None,
        worker_archetype=None,
        worker_capability=None,
        worker_state=None,
        worker_identity=None,
        transport=None,
        forecast_contract_id=None,
        gp233_evidence_ref=None,
        source_refs_json="[]",
        prediction_ids_json="[]",
        catch_ids_json="[]",
        outcome_known=False,
        success_bool=None,
        decision_impact=None,
        yield_signal=None,
        actual_cost_agent_minutes=None,
        negative_externality_tags_json="[]",
        baseline_action=None,
        counterfactual_action=None,
        counterfactual_value_bucket=None,
        notes=None,
    )

    row = module.agentic_workbench_impact_from_route_args(args)

    assert row["selected_action"] == "invoke_autoresearch"
    assert row["context_features"]["workbench_router_decision"] == "invoke_autoresearch"
    assert row["context_features"]["worker"]["worker_archetype"] == "fungible_agent_worker"
    assert row["context_features"]["worker"]["worker_capability"] == "tool_using_agent"
    assert row["context_features"]["worker"]["worker_state"] == "stateless_externalized_briefing"
    assert row["context_features"]["worker"]["transport"] == "subscription_cli"
    assert row["context_features"]["operator_card_ids"] == ["OP-AWR-01"]
    assert row["context_features"]["operator_card_routes"][0]["route_mode"] == "lexical_fallback"
    assert str(route_path) in row["source_refs"]["source_refs"]
    assert not module.validate_agentic_workbench_impact(row)


def test_agentic_workbench_validation_checks_operator_card_route_shape() -> None:
    row = {
        "schema_version": 1,
        "action_impact_id": "ai_test_bad_card_route",
        "recorded_at": "2026-06-11T00:00:00Z",
        "decision_point": {
            "decision_id": "decision_test",
            "domain": "agentic_workbench",
        },
        "candidate_actions": module.AGENTIC_WORKBENCH_ACTIONS,
        "selected_action": "invoke_autoresearch",
        "policy_source": "rd",
        "logged_policy": {
            "logging_policy": "rd_workbench_router",
            "propensity_or_selection_rule": "fixture",
            "eligible_actions": module.AGENTIC_WORKBENCH_ACTIONS,
        },
        "source_refs": {"source_refs": ["analytics/public/queries/rd/autoresearch_routes/fixture.json"]},
        "context_features": {
            "workbench_router_decision": "invoke_autoresearch",
            "why_not_autoresearch": "",
            "operator_card_routes": [{"name": "missing card id"}],
            "operator_card_ids": "OP-AWR-01",
        },
        "outcome": {"known": False},
        "counterfactual": {},
    }

    errors = module.validate_agentic_workbench_impact(row)

    assert "context_features.operator_card_routes[1] missing card_id" in errors
    assert "context_features.operator_card_routes[1] missing route_mode" in errors
    assert "context_features.operator_card_ids must be a list when present" in errors


def test_agentic_route_json_defaults_missing_surface_reason(tmp_path: Path) -> None:
    route_path = tmp_path / "route.json"
    _write_json(
        route_path,
        {
            "decision": "stay_out_of_loop",
            "task": "explore broad research direction",
            "project": "gp_example",
            "bounded_claim": False,
            "stable_evaluator": False,
            "rubric_ready": False,
            "artifact_surface": False,
            "missing": ["bounded claim/eigenquestion", "stable evaluator/gate"],
        },
    )
    args = module.argparse.Namespace(
        route_json=route_path,
        action_impact_id=None,
        recorded_at="2026-06-11T00:00:00Z",
        decision_id="decision_route_stay",
        tick_id=None,
        project_id=None,
        project_family=None,
        stage="pretick",
        task=None,
        selected_action="run_out_of_loop_agent",
        policy_source="rd",
        selection_rule="rd_workbench_router",
        why_selected=None,
        why_not_autoresearch=None,
        worker_archetype=None,
        worker_capability=None,
        worker_state=None,
        worker_identity=None,
        transport=None,
        forecast_contract_id=None,
        gp233_evidence_ref=None,
        source_refs_json="[]",
        prediction_ids_json="[]",
        catch_ids_json="[]",
        outcome_known=False,
        success_bool=None,
        decision_impact=None,
        yield_signal=None,
        actual_cost_agent_minutes=None,
        negative_externality_tags_json="[]",
        baseline_action=None,
        counterfactual_action=None,
        counterfactual_value_bucket=None,
        notes=None,
    )

    row = module.agentic_workbench_impact_from_route_args(args)

    assert row["selected_action"] == "run_out_of_loop_agent"
    assert row["context_features"]["workbench_router_decision"] == "stay_out_of_loop"
    assert "bounded claim/eigenquestion" in row["context_features"]["why_not_autoresearch"]
    assert row["context_features"]["worker"]["worker_state"] == "stateful"
    assert not module.validate_agentic_workbench_impact(row)


def test_agentic_route_json_requires_typed_prerequisite_fields(tmp_path: Path) -> None:
    route_path = tmp_path / "route.json"
    _write_json(
        route_path,
        {
            "decision": "invoke_autoresearch",
            "task": "test bounded claim",
            "project": "gp_example",
            "bounded_claim": True,
            "stable_evaluator": True,
            "rubric_ready": True,
            "missing": [],
        },
    )
    args = module.argparse.Namespace(
        route_json=route_path,
        selected_action=None,
        source_refs_json="[]",
    )

    try:
        module.agentic_workbench_impact_from_route_args(args)
    except SystemExit as exc:
        assert "invalid agentic route JSON" in str(exc)
        assert "route JSON missing artifact_surface" in str(exc)
    else:
        raise AssertionError("expected invalid route JSON to fail")


def test_agentic_route_json_rejects_inconsistent_invoke_decision(tmp_path: Path) -> None:
    route_path = tmp_path / "route.json"
    _write_json(
        route_path,
        {
            "decision": "invoke_autoresearch",
            "task": "test bounded claim",
            "project": "gp_example",
            "bounded_claim": True,
            "stable_evaluator": True,
            "rubric_ready": True,
            "artifact_surface": False,
            "missing": ["artifact surface"],
        },
    )
    args = module.argparse.Namespace(
        route_json=route_path,
        selected_action=None,
        source_refs_json="[]",
    )

    try:
        module.agentic_workbench_impact_from_route_args(args)
    except SystemExit as exc:
        message = str(exc)
        assert "invalid agentic route JSON" in message
        assert "requires bounded_claim, stable_evaluator, rubric_ready, and artifact_surface all true" in message
        assert "requires empty missing list" in message
    else:
        raise AssertionError("expected inconsistent invoke route to fail")


def test_agentic_route_json_accepts_prepare_surface_contract(tmp_path: Path) -> None:
    route_path = tmp_path / "route.json"
    _write_json(
        route_path,
        {
            "decision": "prepare_autoresearch_surface",
            "task": "bounded claim missing artifact",
            "project": "gp_example",
            "bounded_claim": True,
            "stable_evaluator": True,
            "rubric_ready": True,
            "artifact_surface": False,
            "missing": ["artifact surface"],
        },
    )
    args = module.argparse.Namespace(
        route_json=route_path,
        action_impact_id=None,
        recorded_at="2026-06-11T00:00:00Z",
        decision_id="decision_route_prepare",
        tick_id=None,
        project_id=None,
        project_family=None,
        stage="pretick",
        task=None,
        selected_action=None,
        policy_source="rd",
        selection_rule="rd_workbench_router",
        why_selected=None,
        why_not_autoresearch=None,
        worker_archetype=None,
        worker_capability=None,
        worker_state=None,
        worker_identity=None,
        transport=None,
        forecast_contract_id=None,
        gp233_evidence_ref=None,
        source_refs_json="[]",
        prediction_ids_json="[]",
        catch_ids_json="[]",
        outcome_known=False,
        success_bool=None,
        decision_impact=None,
        yield_signal=None,
        actual_cost_agent_minutes=None,
        negative_externality_tags_json="[]",
        baseline_action=None,
        counterfactual_action=None,
        counterfactual_value_bucket=None,
        notes=None,
    )

    row = module.agentic_workbench_impact_from_route_args(args)

    assert row["selected_action"] == "prepare_autoresearch_surface"
    assert row["context_features"]["workbench_router_decision"] == "prepare_autoresearch_surface"
    assert row["context_features"]["artifact_surface"] is False
    assert not module.validate_agentic_workbench_impact(row)
