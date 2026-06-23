from __future__ import annotations

import json
import os
import time
from pathlib import Path

from ztare.reports import operations_intelligence as ops
from ztare.reports.operations_intelligence import build, parse_markdown_table


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_parse_markdown_table_skips_separator(tmp_path: Path) -> None:
    path = tmp_path / "table.md"
    write(path, "| A | B |\n|---|---|\n| x | y |\n")
    assert parse_markdown_table(path) == [["A", "B"], ["x", "y"]]


def test_main_json_mode_prints_written_payload(tmp_path: Path, capsys) -> None:
    out = tmp_path / "ops.json"

    rc = ops.main([
        "--repo",
        str(tmp_path),
        "--out",
        str(out),
        "--no-markdown",
        "--json",
    ])

    assert rc == 0
    printed = json.loads(capsys.readouterr().out)
    written = json.loads(out.read_text(encoding="utf-8"))
    assert printed == written
    assert printed["schema"] == "ztare-intelligence-surface-v1"


def test_build_extracts_focus_track_intelligence_and_source_health(tmp_path: Path) -> None:
    repo = tmp_path
    write(repo / "projects/ns_millennium_hunt/project_charter.md", "# NS Hunt\n")
    write(
        repo / "projects/ns_millennium_hunt/workspace/ns_residual_manifest.md",
        "# Residual Manifest\n\nLatest route: C7 fresh-radius invoice.\n",
    )
    write(
        repo / "analytics/public/ledgers/research_yield_decomposition/GP-233_EVIDENCE_LEDGER.md",
        "\n".join(
            [
                "| Date | Substrate / lane | Evidence pointer | GP-233 bottleneck named | Decision changed | Verdict |",
                "|---|---|---|---|---|---|",
                "| 2026-05-20 | NS Track B | `projects/ns_millennium_hunt/workspace/ns_residual_manifest.md` | `fresh_radius_invoice` | Changed next lever | positive |",
            ]
        ),
    )
    aggregate = {
        "contract_id": "tick999-ns-c7",
        "contract_question": "NS C7 fresh radius route",
        "aggregate": {"p_success": 0.2},
        "allocation_recommendation": {"action": "ask_another_independent_agent"},
    }
    write(repo / "analytics/public/forecast_pool/aggregates/tick999-ns-c7.json", json.dumps(aggregate))
    write(repo / "analytics/public/forecast_pool/contracts/tick999-ns-c7.json", "{}")
    write(
        repo / "analytics/public/queries/trajectory/trajectory_curves.json",
        json.dumps(
            {
                "curves": {
                    "confound_a_code_activity_density": {"2026-05-13": 10, "2026-05-20": 40},
                    "confound_b_total_artifact_creation_per_week": {"2026-05-13": 20, "2026-05-20": 80},
                    "insight_a_f_row_creates_per_week": {"2026-05-13": 3, "2026-05-20": 4},
                    "insight_b_f_row_closures_per_week": {"2026-05-13": 1, "2026-05-20": 1},
                    "insight_e_verified_axioms_added_per_week": {"2026-05-13": 1, "2026-05-20": 1},
                }
            }
        ),
    )
    write(
        repo / "research_areas/EXPERIMENT_TRACK_RECORD.md",
        "\n".join(
            [
                "| Date | Track | Status | Finding |",
                "|---|---|---|---|",
                "| 2026-05-20 | ns_millennium_hunt | active | result: C7 route remains blocked |",
            ]
        ),
    )
    write(
        repo / "analytics/public/ledgers/catch/catch_ledger.jsonl",
        json.dumps({"catch_id": "C-1", "category": "test", "status": "ratified", "consequential": True}) + "\n",
    )
    write(
        repo / "analytics/public/action_intelligence/state/source_health.json",
        json.dumps(
            {
                "counts": {"blocking": 1},
                "issues": [
                    {
                        "severity": "blocking",
                        "issue_type": "missing_decision_use",
                        "blocking_rule": "repair decision-use emitter",
                        "evidence_refs": ["analytics/public/forecast_pool/decision_use/decision_use_ledger.jsonl"],
                    }
                ],
            }
        ),
    )
    payload = build(repo, freshness_days=30, max_projects=10)
    assert payload["schema"] == "ztare-intelligence-surface-v1"
    assert payload["headline"]["active_focus_tracks"] == 1
    assert payload["headline"]["experiment_rows"] == 1
    assert payload["headline"]["source_health_blockers"] == 1
    assert payload["source_health_summary"]["issue_count"] == 1
    assert payload["source_health_summary"]["blocking_count"] == 1
    assert payload["source_health_summary"]["warning_count"] == 0
    assert payload["source_health_summary"]["issue_type_counts"]["missing_decision_use"] == 1
    assert payload["source_health_summary"]["issue_sample"] == [
        {
            "severity": "blocking",
            "scope": None,
            "issue_type": "missing_decision_use",
            "blocking_rule": "repair decision-use emitter",
            "recommended_action": None,
            "evidence_refs": [
                "analytics/public/forecast_pool/decision_use/decision_use_ledger.jsonl"
            ],
        }
    ]
    assert payload["headline"]["forecast_decision_use_rate"] == 0.0
    track = next(row for row in payload["focus_tracks"]["rows"] if row["track_id"] == "ns_millennium_hunt")
    assert track["linkage_quality"] == "strong"
    assert track["signals"]["gp233_refs"] == 1
    assert track["signals"]["forecast_refs"] == 1
    assert track["signals"]["experiment_refs"] == 1
    assert payload["attention"][0]["kind"] == "source_health"
    assert payload["learning_candidates"][0]["observer_only"] is True
    assert payload["learning_candidates"][0]["promotion_decision"] == "close_as_source_repair_not_primitive"
    decision_contract = payload["learning_candidates"][0]["promotion_contract"]
    assert decision_contract["typed_carrier"] == "forecast_decision_use_source_repair"
    assert decision_contract["validation"]["ok"] is True
    assert "PREDICTION-LOGGING-DISCRIMINATOR" in decision_contract["nearest_existing_surface"]
    assert "new primitive" in decision_contract["non_claim"]
    assert payload["forecast_market"]["decision_use_gap"] == 1
    forecast_gap_candidate = next(
        row for row in payload["learning_candidates"]
        if row["source_kind"] == "forecast_market"
        and row["object_ref"] == "decision_use_gap"
    )
    assert forecast_gap_candidate["promotion_decision"] == "close_as_source_repair_not_primitive"
    assert payload["activity_yield"]["verdict"] == "activity_outpacing_yield"
    assert payload["source_map"]["gap_count"] >= 1
    assert payload["source_improvement_backlog"]
    assert payload["etl_manifest"]["load"]["writes_official_state"] is False
    assert payload["etl_manifest"]["validate"]["issue_count"] >= 1
    assert payload["source_readiness"]["schema"] == "ztare-source-readiness-v1"
    assert payload["source_readiness"]["summary"]["blocked"] >= 1
    forecast_readiness = next(
        row for row in payload["source_readiness"]["rows"]
        if row["source_id"] == "gp230_forecast_pool"
    )
    assert forecast_readiness["valid_promotion_contract_count"] >= 1
    assert decision_contract["candidate_id"] in forecast_readiness["promotion_contract_ids"]
    assert payload["executive_brief"]["schema"] == "ztare-intelligence-executive-brief-v1"
    assert payload["executive_brief"]["operating_status"] == "blocked_for_allocation"
    assert "forecast-market allocation claims" in " ".join(payload["executive_brief"]["do_not_use_for"])
    areas = payload["research_ops_metric_areas"]
    assert areas["schema"] == "ztare-research-ops-metric-areas-v1"
    assert {area["area_id"] for area in areas["areas"]} >= {"information_yield", "decision_use", "recursive_learning"}
    assert "implemented_source_blocked" in areas["status_counts"]


def test_source_readiness_blocks_missing_local_source_refs(tmp_path: Path) -> None:
    repo = tmp_path
    write(repo / "present.json", "{}\n")
    payload = {
        "source_map": {
            "rows": [
                {
                    "source_id": "present_source",
                    "source_refs": ["present.json"],
                    "feeds": ["demo"],
                    "source_gaps": [],
                },
                {
                    "source_id": "missing_source",
                    "source_refs": ["missing.json"],
                    "feeds": ["demo"],
                    "source_gaps": [],
                },
                {
                    "source_id": "external_source",
                    "source_refs": ["https://example.test/artifact.json"],
                    "feeds": ["demo"],
                    "source_gaps": [],
                },
            ]
        },
        "source_improvement_backlog": [],
        "etl_manifest": {"validate": {"issues": []}},
        "learning_promotion_contracts": [],
    }

    readiness = ops.build_source_readiness(payload, repo=repo)

    rows = {row["source_id"]: row for row in readiness["rows"]}
    assert rows["present_source"]["readiness"] == "ready"
    assert rows["present_source"]["present_source_refs"] == ["present.json"]
    assert rows["missing_source"]["readiness"] == "blocked"
    assert rows["missing_source"]["use_now"] == "do_not_use_for_allocation"
    assert rows["missing_source"]["missing_source_refs"] == ["missing.json"]
    assert rows["missing_source"]["missing_source_ref_count"] == 1
    assert rows["external_source"]["readiness"] == "ready"
    assert rows["external_source"]["external_source_refs"] == ["https://example.test/artifact.json"]
    assert readiness["summary"]["missing_source_ref_count"] == 1


def test_build_tracks_agentic_workbench_action_rows(tmp_path: Path) -> None:
    repo = tmp_path
    write(
        repo / "analytics/public/ledgers/action_intelligence/action_impact_ledger.jsonl",
        "\n".join(
            json.dumps(row)
            for row in [
                {
                    "schema_version": 1,
                    "action_impact_id": "ai_agentic_fixture",
                    "recorded_at": "2026-06-11T12:00:00Z",
                    "decision_point": {
                        "decision_id": "agentic_fixture",
                        "tick_id": "tick-agentic-fixture",
                        "project_id": "fixture_project",
                        "domain": "agentic_workbench",
                        "stage": "pretick",
                    },
                    "candidate_actions": ["invoke_autoresearch", "run_out_of_loop_agent"],
                    "selected_action": "run_out_of_loop_agent",
                    "policy_source": "rd",
                    "logged_policy": {
                        "logging_policy": "rd_workbench_router",
                        "propensity_or_selection_rule": "manual",
                        "eligible_actions": ["invoke_autoresearch", "run_out_of_loop_agent"],
                        "why_selected": "subscription CLI agent was used after router check",
                        "why_not_selected": {},
                    },
                    "source_refs": {"source_refs": ["analytics/public/queries/rd/autoresearch_routes/missing_surface_fixture.json"]},
                    "context_features": {
                        "task": "agentic_workbench autoresearch boundary fixture",
                        "project_family": "agentic_ai_workbench",
                        "workbench_router_decision": "prepare_autoresearch_surface",
                        "why_not_autoresearch": "stable evaluator missing",
                        "bounded_claim": True,
                        "stable_evaluator": False,
                        "rubric_ready": True,
                        "artifact_surface": False,
                        "operator_card_ids": ["OP-AWR-01"],
                        "worker": {
                            "worker_archetype": "persistent_agent",
                            "transport": "subscription_cli",
                        },
                    },
                    "outcome": {"known": True, "decision_impact": "prepared_autoresearch_surface"},
                    "counterfactual": {"notes": "fixture"},
                },
                {
                    "schema_version": 1,
                    "action_impact_id": "ai_agentic_ready_bypass",
                    "recorded_at": "2026-06-11T12:10:00Z",
                    "decision_point": {
                        "decision_id": "agentic_ready_bypass",
                        "project_id": "fixture_project",
                        "domain": "agentic_workbench",
                        "stage": "pretick",
                    },
                    "candidate_actions": ["invoke_autoresearch", "run_out_of_loop_agent"],
                    "selected_action": "run_out_of_loop_agent",
                    "policy_source": "rd",
                    "logged_policy": {
                        "logging_policy": "rd_workbench_router",
                        "propensity_or_selection_rule": "manual",
                        "eligible_actions": ["invoke_autoresearch", "run_out_of_loop_agent"],
                        "why_selected": "subscription CLI was faster for this ready workbench",
                        "why_not_selected": {},
                    },
                    "source_refs": {"source_refs": ["route_ready.json"]},
                    "context_features": {
                        "task": "ready bounded workbench bypass fixture",
                        "project_family": "agentic_ai_workbench",
                        "workbench_router_decision": "invoke_autoresearch",
                        "why_not_autoresearch": "subscription cost/capability choice",
                        "bounded_claim": True,
                        "stable_evaluator": True,
                        "rubric_ready": True,
                        "artifact_surface": True,
                        "operator_card_routes": [
                            {
                                "card_id": "OP-AWR-01",
                                "route_mode": "lexical_fallback",
                            }
                        ],
                        "worker": {"transport": "subscription_cli"},
                    },
                    "outcome": {"known": False},
                    "counterfactual": {"notes": "fixture"},
                },
            ]
        )
        + "\n",
    )
    write(
        repo / "analytics/public/action_intelligence/state/action_intelligence.json",
        json.dumps({"summary": {"agentic_workbench_rows": 2}}),
    )
    write(
        repo / "analytics/public/ledgers/reflexive/bifurcation_report.json",
        json.dumps(
            {
                "bifurcation": {
                    "iter_loop_artifacts": 100,
                    "agent_work_artifacts": 300,
                    "agent_work_share": 0.75,
                }
            }
        ),
    )
    payload = build(repo, freshness_days=30, max_projects=10)
    track = next(row for row in payload["focus_tracks"]["rows"] if row["track_id"] == "agentic_ai_workbench")
    assert track["activity_state"] == "active"
    assert track["linkage_quality"] == "strong"
    assert track["signals"]["action_refs"] == 2
    assert payload["headline"]["agentic_workbench_rows"] == 2
    assert payload["headline"]["ready_workbench_bypasses"] == 1
    summary = payload["agentic_workbench"]
    assert summary["rows"] == 2
    assert summary["decision_counts"]["prepare_autoresearch_surface"] == 1
    assert summary["decision_counts"]["invoke_autoresearch"] == 1
    assert summary["selected_action_counts"]["run_out_of_loop_agent"] == 2
    assert summary["operator_card_counts"]["OP-AWR-01"] == 2
    assert summary["recent_rows"][0]["operator_card_ids"] == ["OP-AWR-01"]
    assert summary["ready_workbench_bypasses"] == 1
    assert summary["ready_workbench_bypasses_without_reason"] == 0
    assert summary["missing_surface_preparations"] == 1
    assert summary["missing_surface_counts"]["missing_stable_evaluator"] == 1
    assert summary["missing_surface_counts"]["missing_artifact"] == 1
    assert summary["missing_surface_examples"][0]["decision_id"] == "agentic_fixture"
    assert summary["missing_surface_examples"][0]["missing_categories"] == [
        "missing_artifact",
        "missing_stable_evaluator",
    ]
    assert summary["bypass_reason_counts"]["ready_workbench_bypassed"] == 1
    assert summary["bypass_reason_counts"]["cost_or_capability_bypass"] == 1
    assert summary["reflexive_bifurcation"]["out_of_loop_share"] == 0.75
    assert summary["reflexive_bifurcation"]["in_loop_share"] == 0.25
    assert summary["route_row_coverage"]["status"] == "sparse_route_rows_for_high_out_of_loop_share"
    assert summary["route_row_coverage"]["needs_logging_attention"] is True
    assert summary["route_row_coverage"]["route_rows"] == 2
    assert summary["route_row_coverage"]["recommended_min_route_rows"] == 5
    assert summary["route_row_coverage"]["additional_route_rows_needed"] == 3
    assert summary["route_row_coverage"]["next_command_template"].startswith(
        "ztare autoresearch route --task"
    )
    assert any(item["kind"] == "agentic_workbench_route_coverage" for item in payload["attention"])
    item = next(row for row in payload["attention"] if row["kind"] == "agentic_workbench_route_coverage")
    assert item["recommended_command"].startswith("ztare autoresearch route --task")
    assert "additional_route_rows_needed=3" in item["why"]
    missing_item = next(
        row for row in payload["attention"]
        if row["kind"] == "agentic_workbench_missing_surface_preparation"
    )
    assert missing_item["missing_surface_counts"]["missing_artifact"] == 1
    assert missing_item["examples"][0]["decision_id"] == "agentic_fixture"
    assert any(
        candidate["source_kind"] == "agentic_workbench"
        and candidate["transition_kind"] == "source_repair"
        for candidate in payload["learning_candidates"]
    )
    missing_candidate = next(
        row for row in payload["learning_candidates"]
        if row["object_ref"] == "missing_surface_preparations"
    )
    assert missing_candidate["promotion_decision"] == "promote_to_typed_carrier_candidate"
    contract = missing_candidate["promotion_contract"]
    assert contract["typed_carrier"] == "agentic_workbench_route_accounting"
    assert contract["validation"]["ok"] is True
    assert "OP-AWR-01" in contract["nearest_existing_surface"]
    assert "model lift" in contract["non_claim"]
    assert "action_impact_ref" in contract["carrier_required_fields"]
    assert "workbench_evidence_ref" in contract["carrier_required_fields"]
    assert "worker_metadata" in contract["carrier_required_fields"]
    assert contract["kernel_action_schema"]["action_name"] == "agentic_workbench_route_accounting"
    assert payload["learning_promotion_contracts"]
    assert any(
        row["promotion_decision"] == "promote_to_typed_carrier_candidate"
        and row["typed_carrier"] == "agentic_workbench_route_accounting"
        and row["validation"]["ok"] is True
        for row in payload["learning_promotion_contracts"]
    )
    readiness = next(
        row for row in payload["source_readiness"]["rows"]
        if row["source_id"] == "action_intelligence"
    )
    assert readiness["valid_promotion_contract_count"] >= 1
    assert missing_candidate["candidate_id"] in readiness["promotion_contract_ids"]
    assert missing_candidate["proposed_payload"]["missing_surface_preparations"] == 1
    assert missing_candidate["proposed_payload"]["missing_surface_examples"][0]["decision_id"] == "agentic_fixture"
    out = repo / "ops.md"
    ops.write_markdown(payload, out)
    rendered = out.read_text(encoding="utf-8")
    assert "route rows needed: `3`" in rendered
    assert "operator-card counts: `{'OP-AWR-01': 2}`" in rendered
    assert "route logging command: `ztare autoresearch route --task" in rendered
    assert "ready workbench bypasses without reason: 0" in rendered
    assert "missing surface example: `decision_id=agentic_fixture`" in rendered
    assert "## Learning Promotion Contracts" in rendered
    assert "`agentic_workbench_route_accounting`" in rendered
    assert "non-claim: Does not claim autoresearch output quality" in rendered
    html_out = repo / "ops.html"
    ops.write_html(payload, html_out)
    html_rendered = html_out.read_text(encoding="utf-8")
    assert '"operator_card_counts": {"OP-AWR-01": 2}' in html_rendered
    assert "cards=${JSON.stringify(aw.operator_card_counts || {})}" in html_rendered


def test_ready_workbench_non_invoke_actions_count_as_bypasses(tmp_path: Path) -> None:
    repo = tmp_path
    write(
        repo / "analytics/public/ledgers/action_intelligence/action_impact_ledger.jsonl",
        json.dumps(
            {
                "schema_version": 1,
                "action_impact_id": "ai_ready_repair",
                "recorded_at": "2026-06-11T12:10:00Z",
                "decision_point": {
                    "decision_id": "ready_repair",
                    "project_id": "fixture_project",
                    "domain": "agentic_workbench",
                    "stage": "pretick",
                },
                "candidate_actions": ["invoke_autoresearch", "repair_source_emitter"],
                "selected_action": "repair_source_emitter",
                "policy_source": "rd",
                "logged_policy": {
                    "logging_policy": "rd_workbench_router",
                    "propensity_or_selection_rule": "manual",
                    "eligible_actions": ["invoke_autoresearch", "repair_source_emitter"],
                    "why_selected": "route source needed repair before launch",
                    "why_not_selected": {},
                },
                "source_refs": {
                    "source_refs": [
                        "analytics/public/queries/rd/autoresearch_routes/ready_repair.json"
                    ]
                },
                "context_features": {
                    "task": "ready bounded workbench repair fixture",
                    "project_family": "agentic_ai_workbench",
                    "workbench_router_decision": "invoke_autoresearch",
                    "why_not_autoresearch": "route source needed repair before launch",
                    "bounded_claim": True,
                    "stable_evaluator": True,
                    "rubric_ready": True,
                    "artifact_surface": True,
                    "worker": {"transport": "subscription_cli"},
                },
                "outcome": {"known": False},
                "counterfactual": {"notes": "fixture"},
            }
        )
        + "\n",
    )
    write(
        repo / "analytics/public/action_intelligence/state/action_intelligence.json",
        json.dumps({"summary": {"agentic_workbench_rows": 1}}),
    )
    write(
        repo / "analytics/public/ledgers/reflexive/bifurcation_report.json",
        json.dumps(
            {
                "bifurcation": {
                    "iter_loop_artifacts": 100,
                    "agent_work_artifacts": 300,
                    "agent_work_share": 0.75,
                }
            }
        ),
    )

    payload = build(repo, freshness_days=30, max_projects=10)
    summary = payload["agentic_workbench"]

    assert summary["ready_workbench_bypasses"] == 1
    assert summary["ready_workbench_bypasses_without_reason"] == 0
    assert summary["bypass_reason_counts"]["ready_workbench_bypassed"] == 1
    assert summary["selected_action_counts"]["repair_source_emitter"] == 1
    assert payload["headline"]["ready_workbench_bypasses"] == 1


def test_build_flags_ready_workbench_bypass_without_reason(tmp_path: Path) -> None:
    repo = tmp_path
    write(
        repo / "analytics/public/ledgers/action_intelligence/action_impact_ledger.jsonl",
        json.dumps(
            {
                "schema_version": 1,
                "action_impact_id": "ai_unexplained_ready_bypass",
                "recorded_at": "2026-06-11T12:10:00Z",
                "decision_point": {
                    "decision_id": "unexplained_ready_bypass",
                    "project_id": "fixture_project",
                    "domain": "agentic_workbench",
                    "stage": "pretick",
                },
                "candidate_actions": ["invoke_autoresearch", "run_out_of_loop_agent"],
                "selected_action": "run_out_of_loop_agent",
                "policy_source": "rd",
                "logged_policy": {
                    "logging_policy": "rd_workbench_router",
                    "propensity_or_selection_rule": "manual",
                    "eligible_actions": ["invoke_autoresearch", "run_out_of_loop_agent"],
                    "why_selected": "",
                    "why_not_selected": {},
                },
                "source_refs": {"source_refs": ["route_ready.json"]},
                "context_features": {
                    "task": "ready bounded workbench bypass fixture",
                    "project_family": "agentic_ai_workbench",
                    "workbench_router_decision": "invoke_autoresearch",
                    "why_not_autoresearch": "",
                    "bounded_claim": True,
                    "stable_evaluator": True,
                    "rubric_ready": True,
                    "artifact_surface": True,
                    "worker": {"transport": "subscription_cli"},
                },
                "outcome": {"known": False},
                "counterfactual": {"notes": "fixture"},
            }
        )
        + "\n",
    )

    payload = build(repo, freshness_days=30, max_projects=10)
    summary = payload["agentic_workbench"]

    assert summary["ready_workbench_bypasses"] == 1
    assert summary["ready_workbench_bypasses_without_reason"] == 1
    item = next(
        row for row in payload["attention"]
        if row["kind"] == "agentic_workbench_unexplained_bypass"
    )
    assert item["priority"] == "p1"
    assert "missing a reason" in item["title"]
    candidate = next(
        row for row in payload["learning_candidates"]
        if row["object_ref"] == "ready_workbench_bypasses_without_reason"
    )
    assert candidate["source_kind"] == "agentic_workbench"
    assert candidate["promotion_decision"] == "promote_to_typed_carrier_candidate"
    assert candidate["promotion_contract"]["validation"]["ok"] is True
    assert candidate["promotion_contract"]["typed_carrier"] == "agentic_workbench_route_accounting"
    assert candidate["proposed_payload"]["ready_workbench_bypasses_without_reason"] == 1
    out = repo / "ops.md"
    ops.write_markdown(payload, out)
    rendered = out.read_text(encoding="utf-8")
    assert "ready workbench bypasses without reason: 1" in rendered


def test_build_surfaces_subscription_outcome_evidence_gap(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path
    monkeypatch.setattr(
        ops,
        "summarize_subscription_outcomes",
        lambda repo: {
            "schema": "ztare-agentic-workbench-subscription-outcomes-v1",
            "status": "transport_metadata_missing",
            "ok": False,
            "summary": {
                "node_count": 8,
                "api_rows": 0,
                "subscription_rows": 0,
                "comparison_present": False,
            },
            "action": "run fresh API and subscription-backed rows with worker metadata",
            "next_command": "make autoresearch-subscription-outcome-audit JSON=1",
            "matched_run_plan": [
                {
                    "project": "demo_project",
                    "matched_run_id": "pair_demo_project_001",
                    "matched_pair_command": (
                        "make autoresearch-matched-transport-pair PROJECT=demo_project "
                        "RUBRIC=demo_project ITERS=1 MATCHED_RUN_ID=pair_demo_project_001"
                    ),
                    "api_command": "make experiment-loop PROJECT=demo_project RUBRIC=demo_project ITERS=1",
                    "subscription_command": (
                        "make experiment-loop PROJECT=demo_project RUBRIC=demo_project "
                        "ITERS=1 AGENT_MUTATOR=1"
                    ),
                    "audit_command": "make autoresearch-subscription-outcome-audit PROJECT=demo_project JSON=1",
                }
            ],
            "observer_only": True,
        },
    )

    payload = build(repo, freshness_days=30, max_projects=10)

    subscription = payload["agentic_workbench"]["subscription_outcomes"]
    assert subscription["status"] == "transport_metadata_missing"
    assert subscription["matched_run_plan"][0]["project"] == "demo_project"
    assert payload["headline"]["subscription_outcome_status"] == "transport_metadata_missing"
    assert payload["headline"]["subscription_outcome_comparison_present"] is False
    item = next(
        row for row in payload["attention"]
        if row["kind"] == "subscription_outcome_evidence_gap"
    )
    assert item["priority"] == "p1"
    assert item["recommended_pair"]["matched_run_id"] == "pair_demo_project_001"
    assert item["recommended_command"].startswith("make autoresearch-matched-transport-pair PROJECT=demo_project")
    candidate = next(
        row for row in payload["learning_candidates"]
        if row["object_ref"] == "transport_metadata_missing"
    )
    assert candidate["source_kind"] == "agentic_workbench"
    assert candidate["observer_only"] is True
    assert candidate["proposed_payload"]["recommended_pair"]["matched_run_id"] == (
        "pair_demo_project_001"
    )
    assert candidate["proposed_payload"]["matched_pair_command"].startswith(
        "make autoresearch-matched-transport-pair PROJECT=demo_project"
    )
    assert candidate["proposed_payload"]["subscription_command"].endswith("AGENT_MUTATOR=1")
    out = repo / "ops.md"
    ops.write_markdown(payload, out)
    rendered = out.read_text(encoding="utf-8")
    assert "subscription matched pair id: `pair_demo_project_001`" in rendered
    assert "subscription matched-pair command: `make autoresearch-matched-transport-pair PROJECT=demo_project" in rendered
    assert "subscription API command: `make experiment-loop PROJECT=demo_project" in rendered


def test_build_flags_high_out_of_loop_share_with_no_route_rows(tmp_path: Path) -> None:
    repo = tmp_path
    write(
        repo / "analytics/public/ledgers/reflexive/bifurcation_report.json",
        json.dumps(
            {
                "bifurcation": {
                    "iter_loop_artifacts": 10,
                    "agent_work_artifacts": 90,
                    "agent_work_share": 0.9,
                }
            }
        ),
    )

    payload = build(repo, freshness_days=30, max_projects=10)
    summary = payload["agentic_workbench"]

    assert summary["rows"] == 0
    assert summary["reflexive_bifurcation"]["out_of_loop_share"] == 0.9
    assert summary["route_row_coverage"]["status"] == "missing_route_rows_for_high_out_of_loop_share"
    assert summary["route_row_coverage"]["needs_logging_attention"] is True
    assert summary["route_row_coverage"]["additional_route_rows_needed"] == 5
    item = next(row for row in payload["attention"] if row["kind"] == "agentic_workbench_route_coverage")
    assert item["priority"] == "p0"
    assert "missing" in item["title"]
    assert "additional_route_rows_needed=5" in item["why"]


def test_build_surfaces_pending_eigenquestion_rotation(tmp_path: Path) -> None:
    repo = tmp_path
    pending_project = repo / "projects" / "pending_project"
    accepted_project = repo / "projects" / "accepted_project"
    pending_project.mkdir(parents=True)
    accepted_project.mkdir(parents=True)
    write(pending_project / "project_charter.md", "## Eigenquestion\n\nold\n")
    write(pending_project / "proposed_eigenquestion_20260612T000000Z.md", "# Proposed\n\nnew\n")
    write(accepted_project / "project_charter.md", "## Eigenquestion\n\nnew\n")
    write(accepted_project / "proposed_eigenquestion_20260611T000000Z.md", "# Proposed\n\nold\n")
    now = time.time()
    os.utime(pending_project / "project_charter.md", (now - 7200, now - 7200))
    os.utime(pending_project / "proposed_eigenquestion_20260612T000000Z.md", (now - 60, now - 60))
    os.utime(accepted_project / "proposed_eigenquestion_20260611T000000Z.md", (now - 7200, now - 7200))
    os.utime(accepted_project / "project_charter.md", (now - 60, now - 60))

    payload = build(repo, freshness_days=30, max_projects=10)

    summary = payload["eigenquestion_rotation"]
    assert summary["projects_with_proposals"] == 2
    assert summary["pending_projects"] == 1
    assert summary["pending_proposals"] == 1
    pending = next(row for row in summary["rows"] if row["project"] == "pending_project")
    accepted = next(row for row in summary["rows"] if row["project"] == "accepted_project")
    assert pending["latest_status"] == "pending_review"
    assert pending["validate_command"] == "ztare eigenquestion validate --project pending_project"
    assert accepted["latest_status"] == "older_than_charter"
    assert payload["headline"]["pending_eigenquestion_projects"] == 1
    item = next(row for row in payload["attention"] if row["kind"] == "eigenquestion_rotation_review")
    assert item["priority"] == "p1"
    candidate = next(row for row in payload["learning_candidates"] if row["source_kind"] == "eigenquestion_rotation")
    assert candidate["observer_only"] is True
    assert "pending_project" in json.dumps(candidate["proposed_payload"])
