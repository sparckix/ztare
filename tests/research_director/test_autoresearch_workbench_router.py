from __future__ import annotations

import json

from src.ztare.research_director.autoresearch_workbench_router import (
    main,
    route_autoresearch_workbench,
    route_autoresearch_workbench_from_context,
)


def test_router_invokes_autoresearch_when_surface_is_ready() -> None:
    decision = route_autoresearch_workbench(
        "test a bounded mechanism",
        stable_evaluator=True,
        bounded_claim=True,
        rubric_ready=True,
        artifact_surface=True,
        subscription_worker_available=True,
        project="gp_example",
        rubric="gp_example",
    )

    assert decision.decision == "invoke_autoresearch"
    assert decision.missing == []
    assert decision.project == "gp_example"
    assert decision.rubric == "gp_example"
    assert decision.worker_metadata == {
        "worker_archetype": "fungible_agent_worker",
        "worker_capability": "tool_using_agent",
        "worker_state": "stateless_externalized_briefing",
        "worker_identity": "fungible",
        "transport": "subscription_cli",
        "worker_metadata_source": "autoresearch_workbench_router",
    }


def test_router_prepares_surface_when_some_prerequisites_exist() -> None:
    decision = route_autoresearch_workbench(
        "rough research direction",
        stable_evaluator=False,
        bounded_claim=True,
        rubric_ready=False,
        artifact_surface=False,
    )

    assert decision.decision == "prepare_autoresearch_surface"
    assert "stable evaluator/gate" in decision.missing
    scaffold_by_missing = {row["missing"]: row for row in decision.surface_scaffold}
    assert scaffold_by_missing["stable evaluator/gate"]["artifact"] == "test_model.py or gate_harness.py"
    assert "scoring_or_gate_function" in scaffold_by_missing["stable evaluator/gate"]["required_fields"]
    assert scaffold_by_missing["rubric surface"]["surface"] == "rubric"


def test_router_stays_out_of_loop_for_unbounded_exploration() -> None:
    decision = route_autoresearch_workbench(
        "brainstorm possible theories",
        stable_evaluator=False,
        bounded_claim=False,
        rubric_ready=False,
        artifact_surface=False,
    )

    assert decision.decision == "stay_out_of_loop"
    assert decision.worker_metadata["worker_archetype"] == "persistent_agent"
    assert decision.worker_metadata["worker_state"] == "stateful"
    assert {row["missing"] for row in decision.surface_scaffold} == {
        "bounded claim/eigenquestion",
        "stable evaluator/gate",
        "rubric surface",
        "artifact surface",
    }


def test_router_cli_emits_parseable_json_with_context(capsys) -> None:
    rc = main([
        "test a bounded mechanism",
        "--project",
        "gp_example",
        "--rubric",
        "gp_example",
        "--bounded-claim",
        "--stable-evaluator",
        "--rubric-ready",
        "--artifact-surface",
    ])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["decision"] == "invoke_autoresearch"
    assert payload["project"] == "gp_example"
    assert payload["rubric"] == "gp_example"
    assert payload["worker_metadata"]["worker_capability"] == "bare_llm_call"
    assert payload["worker_metadata"]["worker_state"] == "stateless_externalized_briefing"
    assert payload["surface_scaffold"] == []


def test_router_infers_ready_surface_from_project_and_rubric(tmp_path) -> None:
    project_dir = tmp_path / "projects" / "gp_example"
    rubric_dir = tmp_path / "rubrics"
    project_dir.mkdir(parents=True)
    rubric_dir.mkdir()
    (project_dir / "current_iteration.md").write_text("claim", encoding="utf-8")
    (project_dir / "test_model.py").write_text("def test_smoke(): pass\n", encoding="utf-8")
    (rubric_dir / "gp_example.json").write_text(
        json.dumps({"dimensions": [{"name": "fit"}]}),
        encoding="utf-8",
    )

    decision = route_autoresearch_workbench_from_context(
        "evaluate the bounded claim",
        project="gp_example",
        rubric="gp_example",
        repo_root=tmp_path,
    )

    assert decision.decision == "invoke_autoresearch"
    assert decision.bounded_claim is True
    assert decision.stable_evaluator is True
    assert decision.rubric_ready is True
    assert decision.artifact_surface is True


def test_router_cli_infers_context_without_manual_booleans(tmp_path, capsys, monkeypatch) -> None:
    project_dir = tmp_path / "projects" / "gp_example"
    rubric_dir = tmp_path / "rubrics"
    project_dir.mkdir(parents=True)
    rubric_dir.mkdir()
    (project_dir / "current_iteration.md").write_text("claim", encoding="utf-8")
    (project_dir / "test_model.py").write_text("def test_smoke(): pass\n", encoding="utf-8")
    (rubric_dir / "gp_example.json").write_text(
        json.dumps({"dimensions": [{"name": "fit"}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "src.ztare.research_director.autoresearch_workbench_router.REPO_ROOT",
        tmp_path,
    )

    rc = main([
        "evaluate the bounded claim",
        "--project",
        "gp_example",
        "--rubric",
        "gp_example",
    ])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["decision"] == "invoke_autoresearch"
    assert payload["bounded_claim"] is True
    assert payload["stable_evaluator"] is True
