from __future__ import annotations

import os
import json
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

from ztare.common.ask_spec import AskSpec
from ztare.common.dispatch_model import (
    DispatchTextResponse,
    dispatch_call_text,
    dispatch_env_for_call_site,
    dispatch_model,
    dispatch_result_receipt,
    resolve_agent_execution_mode,
    resolve_agent_timeout_seconds,
    resolve_dispatch_capability,
)
from ztare.common.subscription_agent_runtime import (
    CODEX_SANDBOX_SEALED_COMPLETION,
    CODEX_SANDBOX_VISIBLE_WORKBENCH,
    build_subscription_agent_command,
)
from ztare.research_director.autoresearch_dispatch_canary import (
    run_dispatch_canary,
    run_dispatch_parity_benchmark,
)


def test_dispatch_model_llm_delegates_to_call_once() -> None:
    result = dispatch_model("hello", llm_call=lambda prompt: prompt.upper())

    assert result.text == "HELLO"
    assert result.capability == "llm"
    assert result.transport == "api"


def test_dispatch_model_llm_projects_explicit_ask_spec() -> None:
    seen: dict[str, str] = {}

    def fake_llm(prompt: str) -> str:
        seen["prompt"] = prompt
        return "ok"

    spec = AskSpec(
        contract_id="demo-contract-v1",
        objective="Return the demo payload.",
        target_surface="candidate",
        expected_output_schema="demo_payload",
        validator="demo.validate",
        authority_level="routing_only",
        blocking_policy="blocks_candidate",
    )

    result = dispatch_model("payload body", llm_call=fake_llm, ask_specs=(spec,))

    assert result.text == "ok"
    assert "demo-contract-v1" in seen["prompt"]
    assert "expected_output_schema: demo_payload" in seen["prompt"]
    assert "payload body" in seen["prompt"]


def test_dispatch_model_agent_requires_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ZTARE_AGENT_DISPATCH", raising=False)

    with pytest.raises(RuntimeError):
        dispatch_model("hello", capability="agent")


def test_dispatch_model_agent_uses_subscription_runner(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH", "agent")
    seen: dict[str, object] = {}

    def fake_runner(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["codex"], 0, stdout="typed contract", stderr=""),
            final_command=["codex", "exec", "redacted"],
            recovery_note=None,
        )

    result = dispatch_model(
        "emit mutation",
        "prior failure: missing declaration",
        capability="agent",
        backend="codex",
        repo=tmp_path,
        runner=fake_runner,
    )

    assert result.text == "typed contract"
    assert result.transport == "subscription_cli"
    assert result.worker_archetype == "fungible_agent_worker"
    assert "EXTERNALIZED BRIEFING" in seen["prompt"]
    assert "prior failure" in seen["prompt"]
    assert "emit mutation" in seen["prompt"]
    assert "sealed completion workbench" in seen["prompt"]
    assert "read-only local inspection commands" not in seen["prompt"]
    assert "typed workbench action contract" in seen["prompt"]
    assert seen["codex_sandbox"] == "read-only"
    assert result.agent_execution_mode == "sealed_completion"


def test_dispatch_model_visible_workbench_uses_workspace_write_shell(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH", "agent")
    seen: dict[str, object] = {}

    def fake_runner(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["codex"], 0, stdout="typed contract", stderr=""),
            final_command=["codex", "exec", "redacted"],
            recovery_note=None,
        )

    result = dispatch_model(
        "emit mutation",
        capability="agent",
        backend="codex",
        repo=tmp_path,
        agent_execution_mode="visible_workbench",
        runner=fake_runner,
    )

    assert result.agent_execution_mode == "visible_workbench"
    assert seen["codex_sandbox"] == CODEX_SANDBOX_VISIBLE_WORKBENCH
    assert "staged visible workbench" in seen["prompt"]
    assert "TASK.md" in seen["prompt"]
    assert "CONTEXT.md" in seen["prompt"]
    assert seen["repo"] != tmp_path
    assert (seen["repo"] / "TASK.md").exists()
    assert (seen["repo"] / "ASKS.json").exists()
    assert (seen["repo"] / "ATTENTION.md").exists()
    assert (seen["repo"] / "RECORDS.json").exists()
    assert (seen["repo"] / "CONTEXT.md").exists()
    debug_meta = next((tmp_path / "workspace" / "agent_prompt_debug").glob("*.meta.json"))
    debug_payload = json.loads(debug_meta.read_text(encoding="utf-8"))
    assert debug_payload["agent_execution_mode"] == "visible_workbench"
    assert debug_payload["phase_timings_s"]["runner_subprocess_s"] >= 0
    assert "build_visible_workbench_pack_s" in debug_payload["phase_timings_s"]


def test_dispatch_model_stateful_resume_uses_delta_prompt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH", "agent")
    monkeypatch.setenv("ZTARE_VISIBLE_WORKBENCH_STRIKE_RESUME", "1")
    seen: dict[str, object] = {}
    session_dir = tmp_path / ".ztare_agent_sessions"
    session_dir.mkdir()
    (session_dir / "codex_rd-director.json").write_text(
        json.dumps(
            {
                "schema": "leanmill-subscription-agent-session-v1",
                "runtime": "codex",
                "agent_id": "rd-director",
                "session_id": "session-123",
                "started_at_epoch": int(time.time()),
                "tick_count": 1,
                "is_new": False,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    def fake_runner(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["codex"], 0, stdout="typed contract", stderr=""),
            final_command=["codex", "exec", "redacted"],
            recovery_note=None,
        )

    result = dispatch_model(
        "full briefing text",
        "full workbench briefing",
        delta_prompt="delta receipt only",
        capability="agent",
        backend="codex",
        repo=tmp_path,
        stateful=True,
        fungible=False,
        continuity_key="rd-director",
        session_dir=session_dir,
        runner=fake_runner,
    )

    assert result.text == "typed contract"
    assert seen["prompt"] == "delta receipt only"


def test_dispatch_model_visible_workbench_copies_receipts_to_project(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH", "agent")
    seen: dict[str, object] = {}

    def fake_runner(**kwargs):
        seen.update(kwargs)
        staged = kwargs["repo"]
        receipt_dir = staged / "workspace" / "visible_cli_receipts"
        receipt_dir.mkdir(parents=True, exist_ok=True)
        (receipt_dir / "probe_abc.json").write_text(
            json.dumps({"schema": "ztare-visible-workbench-cli-receipt-v1", "status": "ok"})
            + "\n",
            encoding="utf-8",
        )
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["codex"], 0, stdout="typed contract", stderr=""),
            final_command=["codex", "exec", "redacted"],
            recovery_note=None,
        )

    dispatch_model(
        "emit mutation",
        capability="agent",
        backend="codex",
        repo=tmp_path,
        agent_execution_mode="visible_workbench",
        runner=fake_runner,
    )

    assert seen["repo"] != tmp_path
    assert (tmp_path / "workspace" / "visible_cli_receipts" / "probe_abc.json").exists()
    debug_meta = next((tmp_path / "workspace" / "agent_prompt_debug").glob("*.meta.json"))
    debug_payload = json.loads(debug_meta.read_text(encoding="utf-8"))
    assert debug_payload["visible_receipt_sync"]["copied"] == 1


def test_visible_workbench_receipt_sync_uses_authority_project(tmp_path) -> None:
    from ztare.common.dispatch_model import _sync_visible_workbench_receipts_to_repo

    repo_root = tmp_path / "repo"
    authority_project = repo_root / "projects" / "arc3_ls20_gov"
    workbench = tmp_path / "pack"
    receipt_dir = workbench / "workspace" / "visible_cli_receipts"
    receipt_dir.mkdir(parents=True)
    cited_artifact_ref = "workspace/scratch/leaf-created-artifact.any"
    (receipt_dir / "probe_abc.json").write_text(
        json.dumps(
            {
                "status": "ok",
                "input_hashes": {"source_ref": cited_artifact_ref},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    source = workbench / cited_artifact_ref
    source.parent.mkdir(parents=True)
    source.write_text("arbitrary staged artifact\n", encoding="utf-8")
    workbench.mkdir(exist_ok=True)
    (workbench / "MANIFEST.json").write_text(
        json.dumps({"authority_project_path": str(authority_project)}) + "\n",
        encoding="utf-8",
    )

    sync = _sync_visible_workbench_receipts_to_repo(
        workbench=workbench,
        repo=repo_root,
        response_text=json.dumps({"visible_receipt_ref": "workspace/visible_cli_receipts/probe_abc.json"}),
    )

    assert sync["copied"] == 1
    assert sync["artifact_copied"] == 1
    assert sync["project"] == str(authority_project.resolve())
    assert (authority_project / "workspace" / "visible_cli_receipts" / "probe_abc.json").exists()
    assert (authority_project / cited_artifact_ref).exists()
    assert not (repo_root / "workspace" / "visible_cli_receipts" / "probe_abc.json").exists()


def test_dispatch_model_visible_workbench_stages_when_repo_has_sealed_holdout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH", "agent")
    (tmp_path / "evidence_holdout.txt").write_text("hidden\n")
    seen: dict[str, object] = {}

    def fake_runner(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["codex"], 0, stdout="typed contract", stderr=""),
            final_command=["codex", "exec", "redacted"],
            recovery_note=None,
        )

    result = dispatch_model(
        "emit mutation",
        capability="agent",
        backend="codex",
        repo=tmp_path,
        agent_execution_mode="visible_workbench",
        runner=fake_runner,
    )

    staged = seen["repo"]
    assert result.agent_execution_mode == "visible_workbench"
    assert staged != tmp_path
    assert (staged / "TASK.md").exists()
    assert (staged / "ASKS.json").exists()
    assert (staged / "ATTENTION.md").exists()
    assert (staged / "RECORDS.json").exists()
    assert (staged / "CONTEXT.md").exists()
    assert (staged / "visible_manifest.json").exists()
    assert (staged / "MANIFEST.json").exists()
    assert (staged / "WORKBENCH_TOOLS.md").exists()
    assert (staged / "src/ztare/common/visible_workbench_cli.py").exists()
    assert not (staged / "evidence_holdout.txt").exists()
    route = subprocess.run(
        [
            sys.executable,
            "-m",
            "ztare.common.visible_workbench_cli",
            "route-action",
            "--source",
            "-",
        ],
        cwd=staged,
        env={**os.environ, "PYTHONPATH": "src"},
        input=json.dumps(
            {
                "type": "LEAF_WORKBENCH_ACTION_REQUEST",
                "payload": {
                    "capability_id": "inspect_worldmodel_counterexample_context"
                },
            }
        ),
        capture_output=True,
        text=True,
        check=False,
    )
    assert route.returncode == 0, route.stderr
    assert json.loads(route.stdout)["route"]["route"] == "parent_kernel"
    manifest = json.loads((staged / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["front_door"] == ["TASK.md", "ASKS.json", "ATTENTION.md", "RECORDS.json", "WORKBENCH_TOOLS.md"]
    assert manifest["background"] == ["CONTEXT.md"]
    assert manifest["sealed_boundary_present"] is True


def test_dispatch_model_visible_workbench_pack_uses_structured_records_front_door(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH", "agent")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    records_path = workspace / "mutator_briefing_iter_001_records.json"
    records_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "iter_index": 1,
                "records": [
                    {
                        "provider": "strategy_experiments",
                        "source_type": "strategy_experiment",
                        "source_ref": "workspace/strategy_experiments.jsonl:abc",
                        "summary": "open quotient repair card",
                        "next_action": "produce candidate delta or blocker",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_runner(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["codex"], 0, stdout="typed contract", stderr=""),
            final_command=["codex", "exec", "redacted"],
            recovery_note=None,
        )

    dispatch_model(
        "emit mutation",
        "background briefing",
        capability="agent",
        backend="codex",
        repo=tmp_path,
        agent_execution_mode="visible_workbench",
        runner=fake_runner,
    )

    staged = seen["repo"]
    records = json.loads((staged / "RECORDS.json").read_text(encoding="utf-8"))
    assert records["source_ref"] == "workspace/mutator_briefing_iter_001_records.json"
    assert records["structured_records"][0]["source_type"] == "strategy_experiment"
    attention = (staged / "ATTENTION.md").read_text(encoding="utf-8")
    assert "open quotient repair card" in attention
    manifest = json.loads((staged / "MANIFEST.json").read_text(encoding="utf-8"))
    pack = {row["ref"]: row for row in manifest["pack_files"]}
    assert pack["TASK.md"]["authority_level"] == "task_contract"
    assert pack["ASKS.json"]["authority_level"] == "ask_contract_index"
    assert pack["ATTENTION.md"]["authority_level"] == "sufficient_statistics"
    assert pack["RECORDS.json"]["sha256"]
    assert pack["CONTEXT.md"]["visible_status"] == "visible"
    assert "emit mutation" not in seen["prompt"]
    assert "TASK.md" in seen["prompt"]


def test_dispatch_model_visible_workbench_attention_prioritizes_residual_work(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH", "agent")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "mutator_briefing_iter_001_records.json").write_text(
        json.dumps(
            {
                "records": [
                    {
                        "provider": "leanmill_proof_jobs",
                        "source_type": "leanmill_wip_proof_surface",
                        "summary": "async proof work",
                    },
                        {
                            "provider": "strategy_experiments",
                            "source_type": "strategy_experiment",
                            "lane": "skill_acquisition",
                            "summary": "residual quotient repair",
                            "action": "run declared residual gate",
                        },
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_runner(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["codex"], 0, stdout="typed contract", stderr=""),
            final_command=["codex", "exec", "redacted"],
            recovery_note=None,
        )

    dispatch_model(
        "emit mutation",
        capability="agent",
        backend="codex",
        repo=tmp_path,
        agent_execution_mode="visible_workbench",
        runner=fake_runner,
    )

    attention = (seen["repo"] / "ATTENTION.md").read_text(encoding="utf-8")
    assert attention.find("residual quotient repair") < attention.find("async proof work")


def test_dispatch_model_visible_workbench_attention_preserves_producer_coverage(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH", "agent")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    records = [
        {
            "provider": "surviving_candidates",
            "source_type": "deterministic_near_miss",
            "source_ref": f"workspace/submissions/candidate_{index}.py",
            "summary": f"candidate row {index}",
        }
        for index in range(12)
    ]
    records.append(
        {
            "provider": "worldmodel_committee",
            "source_type": "worldmodel_committee",
            "summary": "current grammar ceiling over the active evidence epoch",
        }
    )
    (workspace / "mutator_briefing_iter_001_records.json").write_text(
        json.dumps({"records": records}) + "\n",
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_runner(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["codex"], 0, stdout="typed contract", stderr=""),
            final_command=["codex", "exec", "redacted"],
            recovery_note=None,
        )

    dispatch_model(
        "emit mutation",
        capability="agent",
        backend="codex",
        repo=tmp_path,
        agent_execution_mode="visible_workbench",
        runner=fake_runner,
    )

    attention = (seen["repo"] / "ATTENTION.md").read_text(encoding="utf-8")
    assert "current grammar ceiling over the active evidence epoch" in attention
    assert attention.count("provider=surviving_candidates") == 7


def test_visible_workbench_front_door_prefers_materialized_observation_over_task(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH", "agent")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    records = [
        {
            "provider": "leaf_workbench",
            "source_type": "leaf_workbench_task",
            "capability_id": "inspect_counterexample_context",
            "summary": "inspect the active counterexample",
        },
        {
            "provider": "leaf_workbench",
            # The live provider currently retains its capability identity when
            # it attaches a materialized observation.  Presence of the typed
            # fiber, rather than a presentation label, owns front-door rank.
            "source_type": "leaf_workbench_capability",
            "capability_id": "inspect_counterexample_context",
            "summary": "verbose coordinate diagnostics that must follow the identity",
            "behavioral_fiber": {
                "member_count": 3,
                "member_rows": [7, 11, 19],
                "interventions": [0, 2],
                "intervention_relation": "varied_interventions_one_consequence",
                "observed_relation": "many_presentations_one_consequence",
                "shared_observed_consequence_sha256": "a" * 64,
                "authority": "diagnostic_finite_witness",
                "carrier_promotion_authorized": False,
            },
        },
    ]
    records.extend(
        {
            "provider": f"provider_{index}",
            "source_type": f"type_{index}",
            "summary": f"producer row {index}",
        }
        for index in range(7)
    )
    (workspace / "mutator_briefing_iter_001_records.json").write_text(
        json.dumps({"records": records}) + "\n",
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_runner(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(
            result=subprocess.CompletedProcess(
                ["codex"], 0, stdout="typed contract", stderr=""
            ),
            final_command=["codex", "exec", "redacted"],
            recovery_note=None,
        )

    dispatch_model(
        "emit mutation",
        capability="agent",
        backend="codex",
        repo=tmp_path,
        agent_execution_mode="visible_workbench",
        runner=fake_runner,
    )

    attention = (seen["repo"] / "ATTENTION.md").read_text(encoding="utf-8")
    assert "behavioral_fiber members=" in attention
    assert "7, 11, 19" in attention
    assert "many_presentations_one_consequence" in attention
    assert "varied_interventions_one_consequence" in attention
    assert "inspect the active counterexample" not in attention


def test_dispatch_model_visible_workbench_attention_demotes_meta_tool_cards(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH", "agent")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "mutator_briefing_iter_001_records.json").write_text(
        json.dumps(
            {
                "records": [
                    {
                        "provider": "strategy_experiments",
                        "source_type": "strategy_experiment",
                        "kind": "tool_synthesis",
                        "summary": "implement joint selector workbench tool",
                        "action": "implement tool and pass evaluator",
                        "next_gate": {"command": "tool_synthesis_gate"},
                    },
                    {
                        "provider": "strategy_experiments",
                        "source_type": "strategy_experiment",
                        "kind": "compressed_counterexample_repair",
                        "summary": "active residual quotient repair",
                        "action": "submit candidate delta or blocker",
                    },
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_runner(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["codex"], 0, stdout="typed contract", stderr=""),
            final_command=["codex", "exec", "redacted"],
            recovery_note=None,
        )

    dispatch_model(
        "emit mutation",
        capability="agent",
        backend="codex",
        repo=tmp_path,
        agent_execution_mode="visible_workbench",
        runner=fake_runner,
    )

    attention = (seen["repo"] / "ATTENTION.md").read_text(encoding="utf-8")
    assert attention.find("active residual quotient repair") < attention.find("implement joint selector")
    assert "kind=tool_synthesis" in attention


def test_dispatch_model_visible_workbench_attention_does_not_trust_stale_markdown_agenda(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH", "agent")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "mutator_briefing_iter_001_records.json").write_text(
        json.dumps(
            {
                "records": [
                    {
                        "provider": "leanmill_proof_jobs",
                        "source_type": "leanmill_wip_proof_surface",
                        "summary": "async proof work",
                    },
                    {
                        "provider": "strategy_experiments",
                        "source_type": "strategy_experiment",
                        "summary": "active residual quotient",
                        "action": "lower current quotient",
                    },
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_runner(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["codex"], 0, stdout="typed contract", stderr=""),
            final_command=["codex", "exec", "redacted"],
            recovery_note=None,
        )

    dispatch_model(
        "## Briefing Attention Agenda\n\n- provider=leanmill_proof_jobs; async proof work\n",
        capability="agent",
        backend="codex",
        repo=tmp_path,
        agent_execution_mode="visible_workbench",
        runner=fake_runner,
    )

    attention = (seen["repo"] / "ATTENTION.md").read_text(encoding="utf-8")
    assert attention.find("active residual quotient") < attention.find("Background Agenda")
    assert "Older rendered agenda retained for context only" in attention


def test_dispatch_model_visible_workbench_records_bind_to_agent_project(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH", "agent")
    (tmp_path / "projects/demo/workspace").mkdir(parents=True)
    (tmp_path / "projects/other/workspace").mkdir(parents=True)
    (tmp_path / "projects/demo/workspace/mutator_briefing_iter_001_records.json").write_text(
        json.dumps(
            {
                "records": [
                    {
                        "provider": "strategy_experiments",
                        "source_type": "strategy_experiment",
                        "source_ref": "workspace/demo.jsonl",
                        "summary": "demo project record",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "projects/other/workspace/mutator_briefing_iter_999_records.json").write_text(
        json.dumps(
            {
                "records": [
                    {
                        "provider": "strategy_experiments",
                        "source_type": "strategy_experiment",
                        "source_ref": "workspace/other.jsonl",
                        "summary": "wrong project record",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_runner(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["codex"], 0, stdout="typed contract", stderr=""),
            final_command=["codex", "exec", "redacted"],
            recovery_note=None,
        )

    dispatch_model(
        "emit mutation",
        capability="agent",
        backend="codex",
        repo=tmp_path,
        agent_id="autoresearch_mutator_demo",
        agent_execution_mode="visible_workbench",
        runner=fake_runner,
    )

    records = json.loads((seen["repo"] / "RECORDS.json").read_text(encoding="utf-8"))
    assert records["source_ref"] == "projects/demo/workspace/mutator_briefing_iter_001_records.json"
    assert records["structured_records"][0]["summary"] == "demo project record"


def test_dispatch_model_visible_workbench_worldmodel_task_is_compact_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH", "agent")
    (tmp_path / "projects/demo/workspace").mkdir(parents=True)
    (tmp_path / "projects/demo/workspace/mutator_briefing_iter_001_records.json").write_text(
        json.dumps(
            {
                "records": [
                    {
                        "provider": "strategy_experiments",
                        "source_type": "strategy_experiment",
                        "failure_family_sha": "a" * 64,
                        "summary": "active repair card",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_runner(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["codex"], 0, stdout="typed contract", stderr=""),
            final_command=["codex", "exec", "redacted"],
            recovery_note=None,
        )

    prompt = (
        "### TASK: Resolve the current boundary mismatch.\n"
        "### PROBABILITY DAG\n"
        + ("legacy ceremony\n" * 200)
        + "WORLDMODEL TYPED PAYLOAD CONTRACT:\n"
        "- Return ONLY one raw JSON object.\n"
    )
    dispatch_model(
        prompt,
        capability="agent",
        backend="codex",
        repo=tmp_path,
        agent_id="autoresearch_mutator_demo",
        agent_execution_mode="visible_workbench",
        runner=fake_runner,
    )

    task = (seen["repo"] / "TASK.md").read_text(encoding="utf-8")
    tools_doc = (seen["repo"] / "WORKBENCH_TOOLS.md").read_text(encoding="utf-8")
    asks = json.loads((seen["repo"] / "ASKS.json").read_text(encoding="utf-8"))
    context = (seen["repo"] / "CONTEXT.md").read_text(encoding="utf-8")
    assert asks["asks"][0]["contract_id"] == "worldmodel-candidate-first-v1"
    assert asks["asks"][0]["target_surface"] == "candidate"
    assert asks["asks"][0]["blocking_policy"] == "blocks_candidate"
    assert "Resolve the current boundary mismatch" not in task
    assert "Compress the staged transition evidence" in task
    assert "`control_receipts`" in task
    assert "route-action" in task
    assert "a" * 64 in task
    assert "legacy ceremony" not in task
    assert "legacy ceremony" in context


def test_worldmodel_task_hypothesis_focus_changes_the_typed_ask(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH", "agent")
    monkeypatch.setenv("ZTARE_WORLDMODEL_TURN_FOCUS", "task_hypothesis")
    (tmp_path / "projects/demo/workspace").mkdir(parents=True)
    (tmp_path / "projects/demo/workspace/mutator_briefing_iter_001_records.json").write_text(
        json.dumps({
            "records": [
                {
                    "provider": "strategy_experiments",
                    "source_type": "strategy_experiment",
                    "kind": "search_control_residue_repair",
                    "failure_family_sha": "a" * 64,
                },
                {
                    "provider": "strategy_experiments",
                    "source_type": "strategy_experiment",
                    "kind": "evidence_probe",
                    "failure_family_sha": "b" * 64,
                },
            ]
        }) + "\n",
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_runner(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["codex"], 0, stdout="typed", stderr=""),
            final_command=["codex", "exec", "redacted"],
            recovery_note=None,
        )

    dispatch_model(
        "WORLDMODEL TYPED PAYLOAD CONTRACT:\n- Return ONLY one raw JSON object.\n",
        capability="agent",
        backend="codex",
        repo=tmp_path,
        agent_id="autoresearch_mutator_demo",
        agent_execution_mode="visible_workbench",
        runner=fake_runner,
    )

    task = (seen["repo"] / "TASK.md").read_text(encoding="utf-8")
    asks = json.loads((seen["repo"] / "ASKS.json").read_text(encoding="utf-8"))
    assert asks["asks"][0]["contract_id"] == "worldmodel-task-hypothesis-v1"
    assert asks["asks"][0]["current_refs"] == ["routing_record_sha256:" + "a" * 64]
    assert "GOAL_PREDICATE(state)" in task
    assert "never a report, receipt, score, task-adjudicator field" in task
    assert "Do not add or modify transition operations" in task
    assert "coordinates, labels" in task
    assert "target-chart discriminator" in task
    assert "Search locally in the CEGIS loop" not in task


def test_dispatch_model_visible_workbench_worldmodel_retry_task_is_compact_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH", "agent")
    (tmp_path / "projects/demo/workspace").mkdir(parents=True)
    (tmp_path / "projects/demo/workspace/mutator_briefing_iter_001_records.json").write_text(
        json.dumps(
            {
                "records": [
                    {
                        "provider": "strategy_experiments",
                        "source_type": "strategy_experiment",
                        "failure_family_sha": "b" * 64,
                        "summary": "retry residual card",
                        "next_action": "compose visible selector receipts",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_runner(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["codex"], 0, stdout="typed contract", stderr=""),
            final_command=["codex", "exec", "redacted"],
            recovery_note=None,
        )

    retry_prompt = (
        "RESUBMIT ONLY ONE RAW JSON OBJECT.\n"
        "- `control_receipts`: list\n"
        "- `test_model_py`: string\n"
        "LEAF_WORKBENCH_ACTION_REQUEST_PRECHECK: executed requested action.\n"
        "CARRIED RECEIPT FACTS: "
        + ("old retry ceremony\n" * 200)
    )
    dispatch_model(
        retry_prompt,
        capability="agent",
        backend="codex",
        repo=tmp_path,
        agent_id="autoresearch_mutator_demo",
        agent_execution_mode="visible_workbench",
        runner=fake_runner,
    )

    task = (seen["repo"] / "TASK.md").read_text(encoding="utf-8")
    tools_doc = (seen["repo"] / "WORKBENCH_TOOLS.md").read_text(encoding="utf-8")
    asks = json.loads((seen["repo"] / "ASKS.json").read_text(encoding="utf-8"))
    context = (seen["repo"] / "CONTEXT.md").read_text(encoding="utf-8")
    attention = (seen["repo"] / "ATTENTION.md").read_text(encoding="utf-8")
    assert asks["asks"][0]["contract_id"] == "worldmodel-candidate-first-v1"
    assert asks["asks"][0]["current_refs"] == ["routing_record_sha256:" + "b" * 64]
    assert "retry residual card" not in task
    assert "retry residual card" in attention
    assert "probe-json" not in task
    assert "probe-json" in tools_doc
    assert "Search locally in the CEGIS loop" in task
    assert "Strategy-card prose or the tool menu" in task
    assert "old retry ceremony" not in task
    assert "old retry ceremony" in context


def test_dispatch_model_visible_workbench_materializes_structured_visible_workspace_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH", "agent")
    (tmp_path / "projects/demo/workspace").mkdir(parents=True)
    (tmp_path / "workspace").mkdir()
    (tmp_path / "workspace/latest_patch_base_regression.json").write_text(
        '{"schema":"stale"}\n',
        encoding="utf-8",
    )
    (tmp_path / "projects/demo/evidence_holdout.txt").write_text("hidden\n")
    (tmp_path / "projects/demo/workspace/latest_patch_base_regression.json").write_text(
        '{"schema":"visible"}\n',
        encoding="utf-8",
    )
    (tmp_path / "projects/demo/workspace/submissions").mkdir()
    (tmp_path / "projects/demo/workspace/submissions/base.py").write_text(
        "PATCH_BASE = {}\n",
        encoding="utf-8",
    )
    (tmp_path / "projects/demo/workspace/submissions/frontier.py").write_text(
        "def step(state, action, t): return state\n",
        encoding="utf-8",
    )
    (tmp_path / "projects/demo/workspace/submissions/donor.py").write_text(
        "def step(state, action, t): return state\n",
        encoding="utf-8",
    )
    (tmp_path / "projects/demo/workspace/leaf_workbench_action_receipts").mkdir()
    (tmp_path / "projects/demo/workspace/leaf_workbench_action_receipts/inspect.json").write_text(
        json.dumps(
            {
                "receipt": {
                    "output_summary": json.dumps(
                        {
                            "archived_residual_donors": [
                                {
                                    "candidate_ref": "workspace/submissions/donor.py",
                                    "authority": "diagnostic_operation_salvage_only",
                                }
                            ]
                        }
                    )
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "projects/demo/workspace/sealed_holdout.json").write_text(
        '{"hidden":true}\n',
        encoding="utf-8",
    )
    (tmp_path / "src/ztare/common").mkdir(parents=True)
    (tmp_path / "src/ztare/common/harness_weakness.py").write_text(
        "LEDGER = 'harness_weakness_receipts.jsonl'\n",
        encoding="utf-8",
    )
    (tmp_path / "projects/demo/workspace/mutator_briefing_iter_001_records.json").write_text(
        json.dumps(
            {
                "records": [
                    {
                        "provider": "strategy_experiments",
                        "source_type": "strategy_experiment",
                        "source_ref": "workspace/latest_patch_base_regression.json",
                        "evidence_refs": [
                            "workspace/submissions/base.py",
                            "workspace/leaf_workbench_action_receipts/inspect.json",
                        ],
                        "submission": "workspace/submissions/frontier.py",
                        "summary": "stage only structured evidence refs",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_runner(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["codex"], 0, stdout="typed contract", stderr=""),
            final_command=["codex", "exec", "redacted"],
            recovery_note=None,
        )

    prompt = (
        "Inspect workspace/latest_patch_base_regression.json and "
        "workspace/submissions/base.py and src/ztare/common/harness_weakness.py; "
        "do not inspect workspace/sealed_holdout.json."
    )
    result = dispatch_model(
        prompt,
        capability="agent",
        backend="codex",
        repo=tmp_path,
        agent_id="autoresearch_mutator_demo",
        agent_execution_mode="visible_workbench",
        runner=fake_runner,
    )

    staged = seen["repo"]
    assert result.agent_execution_mode == "visible_workbench"
    assert (staged / "workspace/latest_patch_base_regression.json").read_text(encoding="utf-8") == (
        '{"schema":"visible"}\n'
    )
    assert (staged / "workspace/submissions/base.py").read_text(encoding="utf-8") == (
        "PATCH_BASE = {}\n"
    )
    assert (staged / "workspace/submissions/frontier.py").is_file()
    assert (staged / "workspace/submissions/donor.py").is_file()
    assert not (staged / "src/ztare/common/harness_weakness.py").exists()
    assert not (staged / "workspace/sealed_holdout.json").exists()
    manifest = json.loads((staged / "visible_manifest.json").read_text(encoding="utf-8"))
    by_ref = {row["ref"]: row for row in manifest["visible_artifacts"]}
    assert by_ref["workspace/latest_patch_base_regression.json"]["status"] == "materialized"
    assert by_ref["workspace/submissions/base.py"]["status"] == "materialized"
    assert by_ref["workspace/submissions/frontier.py"]["status"] == "materialized"
    assert by_ref["workspace/submissions/donor.py"]["status"] == "materialized"
    assert "src/ztare/common/harness_weakness.py" not in by_ref
    assert "workspace/sealed_holdout.json" not in by_ref


def test_dispatch_model_visible_workbench_canonicalizes_evidence_ref_suffixes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH", "agent")
    (tmp_path / "projects/demo/workspace/submissions").mkdir(parents=True)
    (tmp_path / "projects/demo/workspace/submissions/base.py").write_text(
        "PATCH_BASE = {}\n",
        encoding="utf-8",
    )
    (tmp_path / "projects/demo/workspace/strategy_experiments.jsonl").write_text(
        '{"failure_family_sha":"abc"}\n',
        encoding="utf-8",
    )
    (tmp_path / "projects/demo/workspace/mutator_briefing_iter_001_records.json").write_text(
        json.dumps(
            {
                "records": [
                    {
                        "provider": "strategy_experiments",
                        "source_ref": "workspace/strategy_experiments.jsonl:a0c7867",
                        "evidence_refs": ["workspace/submissions/base.py#sha=abc123"],
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "projects/demo/evidence_holdout.txt").write_text("hidden\n")
    seen: dict[str, object] = {}

    def fake_runner(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["codex"], 0, stdout="typed contract", stderr=""),
            final_command=["codex", "exec", "redacted"],
            recovery_note=None,
        )

    prompt = "Use the structured evidence refs from RECORDS.json."
    dispatch_model(
        prompt,
        capability="agent",
        backend="codex",
        repo=tmp_path,
        agent_id="autoresearch_mutator_demo",
        agent_execution_mode="visible_workbench",
        runner=fake_runner,
    )

    staged = seen["repo"]
    manifest = json.loads((staged / "visible_manifest.json").read_text(encoding="utf-8"))
    by_ref = {row["ref"]: row for row in manifest["visible_artifacts"]}
    assert by_ref["workspace/submissions/base.py"]["status"] == "materialized"
    assert by_ref["workspace/strategy_experiments.jsonl"]["status"] == "materialized"
    assert "workspace/submissions/base.py#sha=abc123" not in by_ref
    assert "workspace/strategy_experiments.jsonl:a0c7867" not in by_ref


def test_worldmodel_ask_tracks_consumed_receipt_work_objects(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH", "agent")
    workspace = tmp_path / "projects/demo/workspace"
    (workspace / "submissions").mkdir(parents=True)
    (workspace / "leaf_workbench_action_receipts").mkdir()
    (workspace / "submissions/donor.py").write_text("def step(): pass\n", encoding="utf-8")
    (workspace / "leaf_workbench_action_receipts/receipt.json").write_text(
        '{"status":"pass"}\n',
        encoding="utf-8",
    )
    # A selector-miner consequence may carry donor deltas even when an older
    # inspection receipt no longer exposes a standalone observation digest.
    observation_sha = ""
    (workspace / "mutator_briefing_iter_001_records.json").write_text(
        json.dumps(
            {
                "records": [
                    {
                        "source_type": "leaf_workbench_kernel_receipt",
                        "record_role": "active_task_first_fire",
                        "source_ref": "workspace/leaf_workbench_action_receipts/receipt.json",
                        "consumer_projection": {
                            "observation_sha256": observation_sha,
                            "archived_residual_donors": [
                                {
                                    "candidate_ref": "workspace/submissions/donor.py",
                                    "candidate_sha256": "d" * 64,
                                }
                            ],
                        },
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_runner(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["codex"], 0, stdout="typed", stderr=""),
            final_command=["codex", "exec", "redacted"],
            recovery_note=None,
        )

    dispatch_model(
        "WORLDMODEL TYPED PAYLOAD CONTRACT:\n- Return ONLY one raw JSON object.\n",
        capability="agent",
        backend="codex",
        repo=tmp_path,
        agent_id="autoresearch_mutator_demo",
        agent_execution_mode="visible_workbench",
        runner=fake_runner,
    )

    staged = seen["repo"]
    asks = json.loads((staged / "ASKS.json").read_text(encoding="utf-8"))
    assert asks["asks"][0]["current_refs"] == [
        "artifact_ref:workspace/submissions/donor.py#sha256=" + "d" * 64,
        "receipt_ref:workspace/leaf_workbench_action_receipts/receipt.json",
    ]
    task = (staged / "TASK.md").read_text(encoding="utf-8")
    assert "no staged counterexample refs were materialized" not in task
    assert "workspace/submissions/donor.py" in task


def test_dispatch_model_visible_workbench_rejects_active_holdout_artifact_refs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH", "agent")
    monkeypatch.setenv("ZTARE_AGENT_VISIBLE_WORKBENCH_MAX_ARTIFACT_BYTES", "4")
    monkeypatch.setenv("ZTARE_AGENT_VISIBLE_WORKBENCH_MAX_LARGE_ARTIFACT_BYTES", "16")
    project_name = "arc3_demo"
    (tmp_path / f"projects/{project_name}/raw/episodes").mkdir(parents=True)
    (tmp_path / f"projects/{project_name}/raw/episodes/episode_002.jsonl").write_text(
        '{"t":2}\n{"t":3}\n',
        encoding="utf-8",
    )
    (tmp_path / f"projects/{project_name}/workspace").mkdir(parents=True)
    (tmp_path / f"projects/{project_name}/workspace/mutator_briefing_iter_001_records.json").write_text(
        json.dumps(
            {
                "records": [
                    {
                        "provider": "workbench",
                        "episode_log_ref": "raw/episodes/episode_002.jsonl",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_runner(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["codex"], 0, stdout="typed contract", stderr=""),
            final_command=["codex", "exec", "redacted"],
            recovery_note=None,
        )

    dispatch_model(
        "Use the staged episode log.",
        capability="agent",
        backend="codex",
        repo=tmp_path,
        agent_id=f"autoresearch_mutator_{project_name}",
        agent_execution_mode="visible_workbench",
        runner=fake_runner,
    )

    staged = seen["repo"]
    assert not (staged / "raw/episodes/episode_002.jsonl").exists()
    manifest = json.loads((staged / "visible_manifest.json").read_text(encoding="utf-8"))
    by_ref = {row["ref"]: row for row in manifest["visible_artifacts"]}
    assert by_ref["raw/episodes/episode_002.jsonl"]["status"] == "withheld"


def test_dispatch_model_visible_workbench_cli_runs_inside_staged_cwd(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH", "agent")
    (tmp_path / "projects/demo/workspace").mkdir(parents=True)
    (tmp_path / "projects/demo/evidence_holdout.txt").write_text("hidden\n")
    (tmp_path / "projects/demo/workspace/latest_patch_base_regression.json").write_text(
        '{"schema":"visible","candidate_regression_receipt":{"exact_rows_delta":-1}}\n',
        encoding="utf-8",
    )
    (tmp_path / "projects/demo/workspace/mutator_briefing_iter_001_records.json").write_text(
        json.dumps(
            {
                "records": [
                    {
                        "provider": "strategy_experiments",
                        "source_ref": "workspace/latest_patch_base_regression.json",
                        "summary": "visible regression receipt",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_runner(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["codex"], 0, stdout="typed contract", stderr=""),
            final_command=["codex", "exec", "redacted"],
            recovery_note=None,
        )

    dispatch_model(
        "Inspect workspace/latest_patch_base_regression.json.",
        capability="agent",
        backend="codex",
        repo=tmp_path,
        agent_id="autoresearch_mutator_demo",
        agent_execution_mode="visible_workbench",
        runner=fake_runner,
    )

    staged = seen["repo"]
    env = {**os.environ, "PYTHONPATH": "src"}
    scorer_import = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from ztare.validator.core.pre_judge_gate import "
                "detect_patch_base_regression_preflight"
            ),
        ],
        cwd=staged,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert scorer_import.returncode == 0, scorer_import.stderr
    composed_carrier_import = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from ztare.worldmodel.patch_base_carrier import "
                "composed_carrier_description_length; "
                "from ztare.fit.mdl import description_units"
            ),
        ],
        cwd=staged,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert composed_carrier_import.returncode == 0, composed_carrier_import.stderr
    adapter_operation_import = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from ztare.worldmodel.spec_abduction import "
                "catalog_state_morphisms"
            ),
        ],
        cwd=staged,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert adapter_operation_import.returncode == 0, adapter_operation_import.stderr
    probe = subprocess.run(
        [
            sys.executable,
            "-m",
            "ztare.common.visible_workbench_cli",
            "probe-json",
            "--artifact",
            "workspace/latest_patch_base_regression.json",
        ],
        cwd=staged,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert probe.returncode == 0, probe.stderr
    probe_payload = json.loads(probe.stdout)
    assert probe_payload["capability_id"] == "run_visible_json_probe"
    assert "workspace/latest_patch_base_regression.json" in probe_payload["input_hashes"]["artifact_hashes"]
    probe_receipt_check = subprocess.run(
        [
            sys.executable,
            "-m",
            "ztare.common.visible_workbench_cli",
            "check-receipt",
            "--kind",
            "worldmodel-payload",
            "--source",
            "-",
        ],
        cwd=staged,
        env=env,
        input=json.dumps(
            {
                "control_receipts": [probe_payload["receipt"]],
                "thesis_markdown": "visible diagnostic plus candidate",
                "test_model_py": "def step(grid, action, t):\n    return grid\n",
            }
        ),
        text=True,
        capture_output=True,
        check=False,
    )
    assert probe_receipt_check.returncode == 0, probe_receipt_check.stdout
    assert json.loads(probe_receipt_check.stdout)["status"] == "pass"

    carrier = subprocess.run(
        [
            sys.executable,
            "-m",
            "ztare.common.visible_workbench_cli",
            "check-worldmodel-carrier",
            "--source",
            "-",
        ],
        cwd=staged,
        env=env,
        input=(
            "def PATCH_DELTA(base_next, state, action, t):\n"
            "    if t == 1:\n"
            "        return base_next\n"
            "    return base_next\n"
        ),
        text=True,
        capture_output=True,
        check=False,
    )
    assert carrier.returncode == 1
    carrier_payload = json.loads(carrier.stdout)
    assert carrier_payload["capability_id"] == "check_worldmodel_carrier_contract"
    assert "temporal admissibility reject" in carrier_payload["output_summary"]

    bare_delta = subprocess.run(
        [
            sys.executable,
            "-m",
            "ztare.common.visible_workbench_cli",
            "check-worldmodel-carrier",
            "--source",
            "-",
        ],
        cwd=staged,
        env=env,
        input=(
            "def PATCH_DELTA(base_next, state, action):\n"
            "    return base_next\n"
        ),
        text=True,
        capture_output=True,
        check=False,
    )
    assert bare_delta.returncode == 1
    bare_payload = json.loads(bare_delta.stdout)
    assert "PATCH_DELTA is a patch combiner" in bare_payload["output_summary"]

    bad_receipt = subprocess.run(
        [
            sys.executable,
            "-m",
            "ztare.common.visible_workbench_cli",
            "check-receipt",
            "--kind",
            "strategy-discharge",
            "--source",
            "-",
        ],
        cwd=staged,
        env=env,
        input='{"failure_family_sha":"abc","outcome":"resubmit"}',
        text=True,
        capture_output=True,
        check=False,
    )
    assert bad_receipt.returncode == 1
    bad_payload = json.loads(bad_receipt.stdout)
    assert bad_payload["capability_id"] == "check_receipt_compatibility"
    assert "outcome must be satisfied|refuted|blocked" in bad_payload["output_summary"]
    assert bad_payload["repair_hints"]

    local_route = subprocess.run(
        [
            sys.executable,
            "-m",
            "ztare.common.visible_workbench_cli",
            "route-action",
            "--source",
            "-",
        ],
        cwd=staged,
        env=env,
        input=json.dumps(
            {
                "type": "LEAF_WORKBENCH_ACTION_REQUEST",
                "payload": {"capability_id": "run_visible_json_probe"},
            }
        ),
        text=True,
        capture_output=True,
        check=False,
    )
    assert local_route.returncode == 0, local_route.stderr
    local_payload = json.loads(local_route.stdout)
    assert local_payload["route"]["route"] == "in_turn_cli"
    assert local_payload["route"]["suggested_command"]

    score_route = subprocess.run(
        [
            sys.executable,
            "-m",
            "ztare.common.visible_workbench_cli",
            "route-action",
            "--source",
            "-",
        ],
        cwd=staged,
        env=env,
        input=json.dumps(
            {
                "type": "LEAF_WORKBENCH_ACTION_REQUEST",
                "payload": {"capability_id": "score_worldmodel_candidate_delta"},
            }
        ),
        text=True,
        capture_output=True,
        check=False,
    )
    assert score_route.returncode == 0, score_route.stderr
    score_route_payload = json.loads(score_route.stdout)
    assert score_route_payload["route"]["route"] == "in_turn_cli"
    assert "score-worldmodel-candidate" in " ".join(score_route_payload["route"]["suggested_command"])

    score_run_action = subprocess.run(
        [
            sys.executable,
            "-m",
            "ztare.common.visible_workbench_cli",
            "run-action",
            "--source",
            "-",
        ],
        cwd=staged,
        env=env,
        input=json.dumps(
            {
                "type": "LEAF_WORKBENCH_ACTION_REQUEST",
                "payload": {"capability_id": "score_worldmodel_candidate_delta"},
            }
        ),
        text=True,
        capture_output=True,
        check=False,
    )
    assert score_run_action.returncode == 1
    score_run_payload = json.loads(score_run_action.stdout)
    assert score_run_payload["status"] == "fail"
    assert "dedicated CLI command" in score_run_payload["output_summary"]

    invalid_route = subprocess.run(
        [
            sys.executable,
            "-m",
            "ztare.common.visible_workbench_cli",
            "route-action",
            "--source",
            "-",
        ],
        cwd=staged,
        env=env,
        input=json.dumps(
            {
                "type": "LEAF_WORKBENCH_ACTION_REQUEST",
                "payload": {"capability_id": "not_registered"},
            }
        ),
        text=True,
        capture_output=True,
        check=False,
    )
    assert invalid_route.returncode == 1
    invalid_payload = json.loads(invalid_route.stdout)
    assert invalid_payload["status"] == "fail"
    assert invalid_payload["route"]["route"] == "invalid_action_request"

    authority_route = subprocess.run(
        [
            sys.executable,
            "-m",
            "ztare.common.visible_workbench_cli",
            "route-action",
            "--source",
            "-",
        ],
        cwd=staged,
        env=env,
        input=json.dumps({"capability_id": "run_strategy_required_gate"}),
        text=True,
        capture_output=True,
        check=False,
    )
    assert authority_route.returncode == 0, authority_route.stderr
    authority_payload = json.loads(authority_route.stdout)
    assert authority_payload["route"]["route"] == "parent_kernel"
    assert authority_payload["route"]["capability_id"] == "run_strategy_required_gate"

    manifest = subprocess.run(
        [
            sys.executable,
            "-m",
            "ztare.common.visible_workbench_cli",
            "manifest",
        ],
        cwd=staged,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert manifest.returncode == 0, manifest.stderr
    manifest_payload = json.loads(manifest.stdout)
    command_ids = {row["command"] for row in manifest_payload["commands"]}
    assert "score-worldmodel-candidate" in command_ids
    assert "score-worldmodel-candidate" in (staged / "WORKBENCH_TOOLS.md").read_text(encoding="utf-8")

    worldmodel_payload = subprocess.run(
        [
            sys.executable,
            "-m",
            "ztare.common.visible_workbench_cli",
            "check-receipt",
            "--kind",
            "worldmodel-payload",
            "--source",
            "-",
        ],
        cwd=staged,
        env=env,
        input=json.dumps(
            {
                "control_receipts": [],
                "thesis_markdown": "visible preflight",
                "test_model_py": "def step(grid, action, t):\n    return grid\n",
            }
        ),
        text=True,
        capture_output=True,
        check=False,
    )
    assert worldmodel_payload.returncode == 0, worldmodel_payload.stderr
    wm_payload = json.loads(worldmodel_payload.stdout)
    assert wm_payload["capability_id"] == "check_receipt_compatibility"
    assert wm_payload["status"] == "pass"
    malformed_proposal = subprocess.run(
        [
            sys.executable,
            "-m",
            "ztare.common.visible_workbench_cli",
            "check-receipt",
            "--kind",
            "worldmodel-payload",
            "--source",
            "-",
        ],
        cwd=staged,
        env=env,
        input=json.dumps(
            {
                "control_receipts": [
                    {
                        "type": "LEAF_WORKBENCH_CAPABILITY_PROPOSAL",
                        "payload": {
                            "capability_id": "mine_missing_sensor",
                            "reason": "needs a new observation",
                        },
                    }
                ],
                "thesis_markdown": "malformed proposal must not preflight",
                "test_model_py": "",
            }
        ),
        text=True,
        capture_output=True,
        check=False,
    )
    assert malformed_proposal.returncode == 1
    malformed_payload = json.loads(malformed_proposal.stdout)
    assert malformed_payload["status"] == "fail"
    assert "malformed_capability_proposal" in malformed_payload["error_classes"]


def test_visible_workbench_source_membrane_covers_evaluator_identity() -> None:
    from ztare.common.projection_owner_registry import VISIBLE_WORKBENCH_SOURCE_REFS
    from ztare.worldmodel.gates import EVALUATOR_IMPLEMENTATION_REFS

    required = {
        f"src/ztare/{relative}"
        for relative in EVALUATOR_IMPLEMENTATION_REFS
    }
    assert required <= set(VISIBLE_WORKBENCH_SOURCE_REFS)


def test_dispatch_model_agent_wraps_stdout_contract_without_briefing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH", "agent")
    seen: dict[str, object] = {}

    def fake_runner(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["codex"], 0, stdout="typed contract", stderr=""),
            final_command=["codex", "exec", "redacted"],
            recovery_note=None,
        )

    dispatch_model(
        "RESUBMIT THE COMPLETE SUBMISSION: thesis prose plus test_model.py.",
        capability="agent",
        backend="codex",
        repo=tmp_path,
        runner=fake_runner,
    )

    assert "automated parser" in seen["prompt"]
    assert "Do not write or modify repository files" in seen["prompt"]
    assert "Do not replace the contract with a summary" in seen["prompt"]
    assert "sealed completion workbench" in seen["prompt"]
    assert "=== TASK ===" in seen["prompt"]


def test_dispatch_model_codex_prompt_capped_to_window(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    # A judge-sized prompt overflows gpt-5.5 in `codex exec` (0 tokens, rc=1). The
    # agent path middle-elides it (head + tail contract preserved) so it fits;
    # the mutator-sized prompt below the cap passes through untouched.
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH", "agent")
    monkeypatch.setenv("ZTARE_CODEX_AGENT_MAX_PROMPT_CHARS", "5000")
    seen: dict[str, str] = {}

    def fake_runner(**kwargs):
        seen["prompt"] = kwargs["prompt"]
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["codex"], 0, stdout="ok", stderr=""),
            final_command=["codex", "exec", "redacted"],
            recovery_note=None,
        )

    big = "HEAD-INSTRUCTIONS " + ("evidence " * 5000) + " TAIL-JSON-CONTRACT"
    dispatch_model(big, capability="agent", backend="codex", repo=tmp_path, runner=fake_runner)
    assert len(seen["prompt"]) <= 5000 + 200  # cap + marker slack
    assert "HEAD-INSTRUCTIONS" in seen["prompt"]
    assert "TAIL-JSON-CONTRACT" in seen["prompt"]
    assert "elided" in seen["prompt"]

    # Under the cap: no elision, byte-for-byte passthrough (mutator case).
    small = "short mutator prompt"
    dispatch_model(small, capability="agent", backend="codex", repo=tmp_path, runner=fake_runner)
    assert "elided" not in seen["prompt"] and small in seen["prompt"]

    # claude runtime is not window-capped here (bigger window, buffers output).
    monkeypatch.setenv("ZTARE_CODEX_AGENT_MAX_PROMPT_CHARS", "50")
    dispatch_model(big, capability="agent", backend="claude", repo=tmp_path, runner=fake_runner)
    assert "elided" not in seen["prompt"]


def test_codex_subscription_worker_reasoning_effort_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("ZTARE_CODEX_AGENT_REASONING_EFFORT", "low")

    cmd = build_subscription_agent_command(
        runtime="codex",
        prompt="hi",
        repo=tmp_path,
        codex_sandbox=CODEX_SANDBOX_SEALED_COMPLETION,
    )

    assert "model_reasoning_effort=low" in cmd

    monkeypatch.setenv("ZTARE_CODEX_AGENT_REASONING_EFFORT", "bogus")
    cmd = build_subscription_agent_command(runtime="codex", prompt="hi", repo=tmp_path)

    assert not any("model_reasoning_effort" in part for part in cmd)


def test_codex_subscription_output_schema_is_explicit_and_codex_only(tmp_path) -> None:
    schema = tmp_path / "response.schema.json"
    schema.write_text('{"type":"object","additionalProperties":false,"required":[],"properties":{}}')

    cmd = build_subscription_agent_command(
        runtime="codex", prompt="hi", repo=tmp_path, output_schema=schema
    )

    index = cmd.index("--output-schema")
    assert cmd[index + 1] == str(schema)
    result = tmp_path / "result.json"
    cmd = build_subscription_agent_command(
        runtime="codex",
        prompt="hi",
        repo=tmp_path,
        output_schema=schema,
        output_last_message_path=result,
    )
    result_index = cmd.index("--output-last-message")
    assert cmd[result_index + 1] == str(result)
    with pytest.raises(ValueError, match="Codex"):
        build_subscription_agent_command(
            runtime="claude", prompt="hi", repo=tmp_path, output_schema=schema
        )
    with pytest.raises(ValueError, match="Codex"):
        build_subscription_agent_command(
            runtime="claude",
            prompt="hi",
            repo=tmp_path,
            output_last_message_path=result,
        )


def test_codex_subscription_remote_mcp_is_default_off_and_explicitly_opt_in(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.delenv("ZTARE_SUBSCRIPTION_AGENT_REMOTE_MCP", raising=False)
    command = build_subscription_agent_command(
        runtime="codex", prompt="hi", repo=tmp_path
    )
    assert "features.rmcp_client=false" in command

    monkeypatch.setenv("ZTARE_SUBSCRIPTION_AGENT_REMOTE_MCP", "1")
    command = build_subscription_agent_command(
        runtime="codex", prompt="hi", repo=tmp_path
    )
    assert "features.rmcp_client=false" not in command


def test_codex_web_research_keeps_mcp_and_shell_off(tmp_path, monkeypatch) -> None:
    from ztare.common.subscription_agent_runtime import (
        CODEX_SANDBOX_WEB_RESEARCH,
    )

    monkeypatch.delenv("ZTARE_SUBSCRIPTION_AGENT_REMOTE_MCP", raising=False)
    command = build_subscription_agent_command(
        runtime="codex",
        prompt="review sources",
        repo=tmp_path,
        codex_sandbox=CODEX_SANDBOX_WEB_RESEARCH,
    )

    assert "features.rmcp_client=false" in command
    assert command[:3] == ["codex", "--search", "exec"]
    assert command.count("--disable") == 2
    assert "shell_tool" in command and "unified_exec" in command


def test_codex_web_research_can_use_host_process_boundary(tmp_path, monkeypatch) -> None:
    from ztare.common.subscription_agent_runtime import (
        CODEX_SANDBOX_WEB_RESEARCH,
    )

    monkeypatch.setenv("ZTARE_CODEX_NESTED_SANDBOX", "0")
    command = build_subscription_agent_command(
        runtime="codex",
        prompt="review sources",
        repo=tmp_path,
        codex_sandbox=CODEX_SANDBOX_WEB_RESEARCH,
    )

    assert "--sandbox" not in command
    assert "--dangerously-bypass-approvals-and-sandbox" in command
    assert command[:3] == ["codex", "--search", "exec"]
    assert "shell_tool" in command and "unified_exec" in command
    assert "features.js_repl=false" in command
    assert "features.rmcp_client=false" in command


def test_common_effort_policy_maps_campaign_high_to_each_runtime_ceiling() -> None:
    from ztare.common.llm_runtime import (
        api_reasoning_effort,
        subscription_reasoning_effort,
    )

    assert subscription_reasoning_effort("codex", "high") == "xhigh"
    assert subscription_reasoning_effort("claude", "high") == "max"
    assert subscription_reasoning_effort("codex", "ultra") == "ultra"
    assert (
        subscription_reasoning_effort("codex", "ultra", model="gpt-5.5")
        == "xhigh"
    )
    assert (
        subscription_reasoning_effort(
            "codex", "ultra", model="gpt-5.6-luna"
        )
        == "max"
    )
    assert subscription_reasoning_effort("codex", "max", model="luna") == "max"
    assert subscription_reasoning_effort("claude", "ultra") == "max"
    assert api_reasoning_effort("gpt-5.5", "high") == "high"
    assert api_reasoning_effort("gpt-5.6-terra", "ultra") == "ultra"
    assert api_reasoning_effort("claude-opus-4-8", "high") == "max"
    assert api_reasoning_effort("claude-opus-4-8", "ultra") == "max"
    assert api_reasoning_effort("gemini-3.1-pro-preview", "high") == "HIGH"
    assert api_reasoning_effort("deepseek-reasoner", "high") is None


def test_dispatch_result_receipt_omits_full_command_prompt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH", "agent")

    def fake_runner(**_kwargs):
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["codex"], 0, stdout="typed contract", stderr=""),
            final_command=["codex", "exec", "prompt text should not be stored"],
            recovery_note=None,
        )

    result = dispatch_model(
        "prompt text should not be stored",
        capability="agent",
        backend="codex",
        repo=tmp_path,
        runner=fake_runner,
    )
    receipt = dispatch_result_receipt("mutator", result)

    assert receipt["call_site"] == "mutator"
    assert receipt["transport"] == "subscription_cli"
    assert receipt["completed"] is True
    assert receipt["command_head"] == "codex"
    assert receipt["agent_execution_mode"] == "sealed_completion"
    assert "prompt text should not be stored" not in json.dumps(receipt)


def test_dispatch_model_stateful_agent_persists_warm_session(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH", "agent")
    session_dir = tmp_path / "sessions"
    seen: dict[str, object] = {}

    def fake_runner(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["codex"], 0, stdout="typed contract", stderr=""),
            final_session_state={
                "schema": "leanmill-subscription-agent-session-v1",
                "runtime": "codex",
                "agent_id": "rd-director",
                "session_id": "session-123",
                "started_at_epoch": 123,
                "tick_count": 7,
                "is_new": False,
            },
            final_command=["codex", "exec", "redacted"],
            recovery_note=None,
        )

    result = dispatch_model(
        "continue the workbench thread",
        capability="agent",
        backend="codex",
        repo=tmp_path,
        stateful=True,
        fungible=False,
        continuity_key="rd-director",
        session_dir=session_dir,
        runner=fake_runner,
    )

    persisted = json.loads((session_dir / "codex_rd-director.json").read_text())
    assert result.worker_archetype == "persistent_agent_worker"
    assert seen["session_state"]["is_new"] is True
    assert persisted["session_id"] == "session-123"
    assert persisted["tick_count"] == 7
    assert persisted["last_used_at_epoch"] is not None


def test_dispatch_call_text_preserves_api_response_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ZTARE_AGENT_DISPATCH_RUBRIC_REVIEW", raising=False)

    response = dispatch_call_text(
        "rubric_review",
        "prompt",
        llm_response_call=lambda prompt: DispatchTextResponse(
            text=f"api:{prompt}",
            usage={"tokens": 3},
            model_id_used="gemini-test",
        ),
    )

    assert response.text == "api:prompt"
    assert response.usage == {"tokens": 3}
    assert response.model_id_used == "gemini-test"
    assert response.dispatch_result is not None
    assert response.dispatch_result.transport == "api"


def test_dispatch_call_text_uses_scoped_agent_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH_RUBRIC_REVIEW", "agent")
    monkeypatch.setenv("ZTARE_AUTORESEARCH_RUBRIC_REVIEW_AGENT_RUNTIME", "codex")
    seen: dict[str, object] = {}

    def fake_runner(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["codex"], 0, stdout='{"ok": true}', stderr=""),
            final_command=["codex", "exec", "redacted"],
            recovery_note=None,
        )

    response = dispatch_call_text(
        "rubric_review",
        "return json",
        llm_response_call=lambda _prompt: DispatchTextResponse(text="api should not run"),
        repo=tmp_path,
        timeout_seconds=123,
        runner=fake_runner,
    )

    assert response.text == '{"ok": true}'
    assert response.model_id_used == "codex"
    assert response.dispatch_result is not None
    assert response.dispatch_result.transport == "subscription_cli"
    assert seen["agent_id"] == "autoresearch_rubric_review"
    assert seen["timeout_seconds"] == 123


def test_dispatch_call_text_uses_generic_agent_timeout_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH_RUBRIC_REVIEW", "agent")
    monkeypatch.setenv("ZTARE_AUTORESEARCH_AGENT_TIMEOUT_SECONDS", "17")
    seen: dict[str, object] = {}

    def fake_runner(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["codex"], 0, stdout="ok", stderr=""),
            final_command=["codex", "exec", "redacted"],
            recovery_note=None,
        )

    dispatch_call_text(
        "rubric_review",
        "return text",
        llm_response_call=lambda _prompt: DispatchTextResponse(text="api should not run"),
        repo=tmp_path,
        timeout_seconds=123,
        runner=fake_runner,
    )

    assert seen["timeout_seconds"] == 17


def test_dispatch_call_text_uses_scoped_agent_timeout_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH_MUTATOR", "agent")
    monkeypatch.setenv("ZTARE_AUTORESEARCH_AGENT_TIMEOUT_SECONDS", "17")
    monkeypatch.setenv("ZTARE_AUTORESEARCH_MUTATOR_AGENT_TIMEOUT_SECONDS", "11")
    seen: dict[str, object] = {}

    def fake_runner(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["codex"], 0, stdout="ok", stderr=""),
            final_command=["codex", "exec", "redacted"],
            recovery_note=None,
        )

    dispatch_call_text(
        "mutator",
        "return text",
        llm_response_call=lambda _prompt: DispatchTextResponse(text="api should not run"),
        repo=tmp_path,
        timeout_seconds=123,
        runner=fake_runner,
    )

    assert seen["timeout_seconds"] == 11


def test_resolve_agent_timeout_seconds_ignores_invalid_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ZTARE_AUTORESEARCH_AGENT_TIMEOUT_SECONDS", "not-an-int")
    monkeypatch.setenv("ZTARE_AUTORESEARCH_MUTATOR_AGENT_TIMEOUT_SECONDS", "0")

    assert resolve_agent_timeout_seconds("mutator", default=123) == 123


def test_resolve_agent_execution_mode_scoped_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ZTARE_AUTORESEARCH_AGENT_EXECUTION_MODE", raising=False)
    monkeypatch.delenv("ZTARE_AUTORESEARCH_MUTATOR_AGENT_EXECUTION_MODE", raising=False)

    assert resolve_agent_execution_mode("mutator") == "visible_workbench"
    assert resolve_agent_execution_mode("judge") == "sealed_completion"

    monkeypatch.setenv("ZTARE_AUTORESEARCH_AGENT_EXECUTION_MODE", "sealed")
    monkeypatch.setenv("ZTARE_AUTORESEARCH_MUTATOR_AGENT_EXECUTION_MODE", "read-only-shell")

    assert resolve_agent_execution_mode("mutator") == "visible_workbench"
    assert resolve_agent_execution_mode("judge") == "sealed_completion"


def test_resolve_dispatch_capability_supports_call_site_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH", "off")
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH_MUTATOR", "agent")

    assert resolve_dispatch_capability("mutator") == "agent"
    assert resolve_dispatch_capability("judge") == "llm"


def test_dispatch_env_for_call_site_matches_scoped_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH", "agent")
    monkeypatch.delenv("ZTARE_AGENT_DISPATCH_JUDGE", raising=False)
    assert dispatch_env_for_call_site("judge") == "ZTARE_AGENT_DISPATCH"

    monkeypatch.setenv("ZTARE_AGENT_DISPATCH_JUDGE", "agent")
    assert dispatch_env_for_call_site("judge") == "ZTARE_AGENT_DISPATCH_JUDGE"


def test_dispatch_canary_exercises_subscription_path_without_live_cli(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.delenv("ZTARE_AGENT_DISPATCH_MUTATOR", raising=False)

    report = run_dispatch_canary(
        call_site="mutator",
        runtime="codex",
        live=False,
        repo=tmp_path,
    )

    assert report["ok"] is True
    assert report["live"] is False
    assert report["transport"] == "subscription_cli"
    assert report["worker_archetype"] == "fungible_agent_worker"
    assert report["token_seen"] is True
    assert "ZTARE_AGENT_DISPATCH_MUTATOR" not in os.environ


def test_dispatch_canary_validates_mutator_contract_without_live_cli(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.delenv("ZTARE_AGENT_DISPATCH_MUTATOR", raising=False)

    report = run_dispatch_canary(
        call_site="mutator",
        contract="mutator",
        runtime="codex",
        live=False,
        repo=tmp_path,
    )

    assert report["ok"] is True
    assert report["contract"] == "mutator"
    assert report["contract_error"] is None
    assert report["contract_validation"]["mutation_validation"]["mismatch_code"] == "CLEAN"
    assert report["contract_validation"]["candidate_extraction"]["python_code_present"] is True


def test_dispatch_canary_validates_judge_contract_without_live_cli(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.delenv("ZTARE_AGENT_DISPATCH_JUDGE", raising=False)

    report = run_dispatch_canary(
        call_site="judge",
        contract="judge",
        runtime="codex",
        live=False,
        repo=tmp_path,
    )

    assert report["ok"] is True
    assert report["contract"] == "judge"
    assert report["contract_error"] is None
    assert report["contract_validation"]["score"] == 42
    assert report["contract_validation"]["probability_dag_keys"] == ["edges", "nodes", "outcome"]


def test_dispatch_canary_validates_committee_contract_without_live_cli(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.delenv("ZTARE_AGENT_DISPATCH_COMMITTEE", raising=False)

    report = run_dispatch_canary(
        call_site="committee",
        contract="committee",
        runtime="codex",
        live=False,
        repo=tmp_path,
    )

    assert report["ok"] is True
    assert report["contract"] == "committee"
    assert report["contract_error"] is None
    assert report["contract_validation"]["persona_count"] == 3
    assert report["contract_validation"]["roles"] == [
        "Boundary Auditor",
        "Mechanism Skeptic",
        "Execution Auditor",
    ]


def test_dispatch_canary_validates_inverter_contract_without_live_cli(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.delenv("ZTARE_AGENT_DISPATCH_INVERTER_REVIEW", raising=False)

    report = run_dispatch_canary(
        call_site="inverter_review",
        contract="inverter",
        runtime="codex",
        live=False,
        repo=tmp_path,
    )

    assert report["ok"] is True
    assert report["contract"] == "inverter"
    assert report["contract_error"] is None
    assert report["contract_validation"]["test_count"] == 3
    assert report["contract_validation"]["categories"] == [
        "measurement_artifact",
        "confound",
        "generalization",
    ]
    assert report["contract_validation"]["auto_testable_count"] == 2


def test_dispatch_parity_benchmark_compares_api_and_subscription_contracts_without_live_cli(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.delenv("ZTARE_AGENT_DISPATCH", raising=False)
    monkeypatch.delenv("ZTARE_AGENT_DISPATCH_MUTATOR", raising=False)
    monkeypatch.delenv("ZTARE_AGENT_DISPATCH_JUDGE", raising=False)
    monkeypatch.delenv("ZTARE_AGENT_DISPATCH_COMMITTEE", raising=False)
    monkeypatch.delenv("ZTARE_AGENT_DISPATCH_INVERTER_REVIEW", raising=False)

    report = run_dispatch_parity_benchmark(runtime="codex", repo=tmp_path)

    assert report["schema"] == "ztare-autoresearch-dispatch-parity-v1"
    assert report["ok"] is True
    assert report["live_subscription"] is False
    assert report["contracts"] == ["text", "mutator", "judge", "committee", "inverter"]
    assert report["summary"]["num_contracts"] == 5
    assert report["summary"]["num_parity"] == 5
    assert report["summary"]["api_all_ok"] is True
    assert report["summary"]["subscription_all_ok"] is True
    assert report["summary"]["api_mean_quality_score"] == 1.0
    assert report["summary"]["subscription_mean_quality_score"] == 1.0
    assert report["summary"]["quality_parity_count"] == 5
    assert report["summary"]["api_model_calls"] == 5
    assert report["summary"]["subscription_cli_invocations"] == 5
    assert report["summary"]["cost_basis"] == "replay_proxy"
    for row in report["rows"]:
        assert row["contract_parity"] is True
        assert row["quality_parity"] is True
        assert row["api"]["transport"] == "api"
        assert row["api"]["quality"]["quality_score"] == 1.0
        assert row["api"]["quality"]["checks_passed"] == row["api"]["quality"]["checks_total"]
        assert row["api"]["cost_proxy"]["api_model_calls"] == 1
        assert row["subscription"]["transport"] == "subscription_cli"
        assert row["subscription"]["runtime"] == "codex"
        assert row["subscription"]["quality"]["quality_score"] == 1.0
        assert (
            row["subscription"]["quality"]["checks_passed"]
            == row["subscription"]["quality"]["checks_total"]
        )
        assert row["subscription"]["cost_proxy"]["subscription_cli_invocations"] == 1
    assert "ZTARE_AGENT_DISPATCH" not in os.environ
    assert "ZTARE_AGENT_DISPATCH_MUTATOR" not in os.environ
    assert "ZTARE_AGENT_DISPATCH_JUDGE" not in os.environ
    assert "ZTARE_AGENT_DISPATCH_COMMITTEE" not in os.environ
    assert "ZTARE_AGENT_DISPATCH_INVERTER_REVIEW" not in os.environ


def test_dispatch_parity_benchmark_rejects_unknown_contract(tmp_path) -> None:
    with pytest.raises(ValueError, match="unsupported canary contract"):
        run_dispatch_parity_benchmark(contracts=("text", "unknown"), repo=tmp_path)
