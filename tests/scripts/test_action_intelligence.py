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


def test_source_health_warns_when_bifurcation_lacks_workbench_decision_rows(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_sources(monkeypatch, tmp_path)

    health = module.source_health_model(action_rows=[])

    issue_types = {issue["issue_type"] for issue in health["issues"]}
    assert "missing_agentic_workbench_decision_rows" in issue_types


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
    assert str(route_path) in row["source_refs"]["source_refs"]
    assert not module.validate_agentic_workbench_impact(row)


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
