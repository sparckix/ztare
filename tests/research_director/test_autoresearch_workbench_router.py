from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ztare.research_director.autoresearch_workbench_router import (
    main,
    route_autoresearch_workbench,
    route_autoresearch_workbench_from_context,
)
from ztare.scaffold.substrate_queue import build_project_packet, write_project_packet


def _valid_kepler_rubric() -> dict:
    return {
        "persona": "Adversarial qualitative judge.",
        "rubric_mode": "kepler",
        "fit_score_mode": "none",
        "disable_evidence_fit_gate": True,
        "disable_evidence_fit_gate_reason": "router packet fixture",
        "disable_uniqueness_gap_gate": True,
        "disable_uniqueness_gap_gate_reason": "router packet fixture",
        "farther_tail_region": None,
        "dimensions": [
            {"name": "Generative Yield", "weight": 100, "description": "yield"}
        ],
        "criteria": {"Generative_Yield": "yield"},
    }


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_source_ready_project(root: Path, slug: str) -> Path:
    project_dir = root / "projects" / slug
    workspace = project_dir / "workspace"
    raw = project_dir / "raw"
    rubric_dir = root / "rubrics"
    raw.mkdir(parents=True)
    workspace.mkdir(parents=True)
    rubric_dir.mkdir(exist_ok=True)
    (project_dir / "project_charter.md").write_text("# Charter\n\nBounded fixture.\n", encoding="utf-8")
    (project_dir / "thesis.md").write_text("# Thesis\n\nA bounded claim.\n", encoding="utf-8")
    (project_dir / "test_model.py").write_text("def test_smoke(): pass\n", encoding="utf-8")
    source_text = "source claim"
    (raw / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\n" + source_text + "\n",
        encoding="utf-8",
    )
    (project_dir / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    source_row = {
        "source_id": "S001",
        "path": "source.md",
        "source_type": "source_evidence",
        "sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
    }
    evidence_path = project_dir / "evidence.txt"
    (project_dir / "compiled_evidence_provenance.json").write_text(
        json.dumps(
            {
                "source_count": 1,
                "sources": [source_row],
                "output_path": str(evidence_path),
                "output_sha256": _sha256_file(evidence_path),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (workspace / "workspace_meta.json").write_text(
        json.dumps({"merge_status": "success", "source_count": 1}) + "\n",
        encoding="utf-8",
    )
    (workspace / "source_index.json").write_text(
        json.dumps({"sources": [source_row]}) + "\n",
        encoding="utf-8",
    )
    (rubric_dir / f"{slug}.json").write_text(
        json.dumps(_valid_kepler_rubric()) + "\n",
        encoding="utf-8",
    )
    packet_path = root / f"{slug}_packet.json"
    write_project_packet(
        packet_path,
        build_project_packet(
            project=slug,
            rubric=slug,
            task="test a bounded packet-backed claim",
            bounded_claim="packet-backed routing has enough source evidence",
            source_refs=[f"projects/{slug}/raw/source.md"],
            evidence_refs=[f"projects/{slug}/evidence.txt"],
            non_claims=["not a full replication"],
            next_falsifier="remove the evidence ref and route must block",
            expected_command=(
                "ztare autoresearch route --task 'test a bounded packet-backed claim' "
                f"--project {slug} --rubric {slug}"
            ),
            created_at="2026-06-20T00:00:00Z",
        ),
    )
    return packet_path


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
    plan_preview = decision.to_dict()["plan_preview"]
    assert plan_preview["schema"] == "ztare-autoresearch-plan-preview-v1"
    assert plan_preview["status"] == "ready_for_preflight"
    assert plan_preview["model_calls_before_confirmation"] is False
    assert plan_preview["recommended_first_command"] == (
        "ztare autoresearch run --project gp_example --rubric gp_example "
        "--preflight-only"
    )
    assert plan_preview["budget"]["model_fallback_policy"] == "disabled_by_default"
    assert [step["id"] for step in plan_preview["dependency_order"]] == [
        "route_decision",
        "preflight_only",
        "bounded_loop_run",
        "trace_health_review",
    ]
    assert any(
        route["card_id"] == "OP-AWR-01"
        for route in decision.operator_card_routes
    )


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
    plan_preview = decision.to_dict()["plan_preview"]
    assert plan_preview["status"] == "surface_preparation_required"
    assert plan_preview["model_calls_before_confirmation"] is False
    assert plan_preview["largest_quality_drop_risk"] == "underspecified_surface"
    assert "repair_surfaces" in [step["id"] for step in plan_preview["dependency_order"]]
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
    assert any(
        route["card_id"] == "OP-AWR-01"
        for route in payload["operator_card_routes"]
    )
    assert payload["surface_scaffold"] == []


def test_router_infers_ready_surface_from_project_and_rubric(tmp_path) -> None:
    project_dir = tmp_path / "projects" / "gp_example"
    rubric_dir = tmp_path / "rubrics"
    project_dir.mkdir(parents=True)
    rubric_dir.mkdir()
    (project_dir / "current_iteration.md").write_text("claim", encoding="utf-8")
    (project_dir / "test_model.py").write_text("def test_smoke(): pass\n", encoding="utf-8")
    (rubric_dir / "gp_example.json").write_text(
        json.dumps({"dimensions": [{"name": "Fit", "weight": 100, "description": "score fit"}]}),
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


def test_router_enforces_packet_backed_kernel_entry(tmp_path) -> None:
    packet_path = _write_source_ready_project(tmp_path, "packet_ready")

    decision = route_autoresearch_workbench_from_context(
        "test a bounded packet-backed claim",
        project="packet_ready",
        rubric="packet_ready",
        packet=str(packet_path),
        repo_root=tmp_path,
    )

    assert decision.decision == "invoke_autoresearch"
    assert decision.source_contract_errors == []
    assert decision.kernel_entry_contract["schema"] == "ztare-kernel-entry-contract-v1"
    assert decision.kernel_entry_contract["can_enter_kernel"] is True
    assert decision.kernel_entry_contract["status"] == "ready"
    assert decision.kernel_entry_contract["entry_command"] == (
        "ztare autoresearch route --task 'test a bounded packet-backed claim' "
        "--project packet_ready --rubric packet_ready --intake packet_ready_packet.json"
    )


def test_router_surfaces_kernel_entry_graph_focus_when_ready(tmp_path) -> None:
    packet_path = _write_source_ready_project(tmp_path, "packet_graph_focus")
    workspace = tmp_path / "projects" / "packet_graph_focus" / "workspace"
    (workspace / "latest_evidence_gaps.json").write_text(
        json.dumps(
            {
                "evidence_gaps": [
                    {
                        "id": "local-check",
                        "severity": "degrading",
                        "target": "next_falsifier_execution",
                        "description": "No evidence that preflight executes the falsifier.",
                        "producer_rationale": "contract_enforcement",
                    }
                ]
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    decision = route_autoresearch_workbench_from_context(
        "test a bounded packet-backed claim",
        project="packet_graph_focus",
        rubric="packet_graph_focus",
        packet=str(packet_path),
        repo_root=tmp_path,
    )

    assert decision.decision == "invoke_autoresearch"
    assert decision.kernel_entry_contract["can_enter_kernel"] is True
    assert decision.kernel_entry_contract["in_loop_focus_receipts"]
    assert any(
        reason.startswith(
            "run-readiness in-loop focus: resolve 1 local verification gap(s)"
        )
        for reason in decision.reasons
    )


def test_router_blocks_packet_with_missing_evidence_ref(tmp_path) -> None:
    packet_path = _write_source_ready_project(tmp_path, "packet_missing_ref")
    payload = json.loads(packet_path.read_text(encoding="utf-8"))
    payload["evidence_refs"] = ["projects/packet_missing_ref/workspace/missing_receipt.json"]
    packet_path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")

    decision = route_autoresearch_workbench_from_context(
        "test a bounded packet-backed claim",
        project="packet_missing_ref",
        rubric="packet_missing_ref",
        packet=str(packet_path),
        repo_root=tmp_path,
    )

    assert decision.decision == "prepare_autoresearch_surface"
    assert decision.kernel_entry_contract["can_enter_kernel"] is False
    assert "autoresearch trace blocks run readiness: project_packet" in decision.source_contract_errors
    assert any(
        "autoresearch run-readiness recovery[project_packet]" in error
        for error in decision.source_contract_errors
    )


def test_router_blocks_ready_surface_when_trace_sources_are_stale(tmp_path) -> None:
    project_dir = tmp_path / "projects" / "stale_trace"
    workspace = project_dir / "workspace"
    rubric_dir = tmp_path / "rubrics"
    raw_dir = project_dir / "raw"
    raw_dir.mkdir(parents=True)
    workspace.mkdir()
    rubric_dir.mkdir()
    (project_dir / "project_charter.md").write_text("charter\n", encoding="utf-8")
    (project_dir / "thesis.md").write_text("claim\n", encoding="utf-8")
    (project_dir / "test_model.py").write_text("def test_smoke(): pass\n", encoding="utf-8")
    (raw_dir / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\ncurrent source\n",
        encoding="utf-8",
    )
    (project_dir / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    stale_source = {
        "source_id": "S001",
        "path": "source.md",
        "source_type": "source_evidence",
        "sha256": "0" * 64,
    }
    (workspace / "workspace_meta.json").write_text(
        json.dumps({"merge_status": "success", "source_count": 1}) + "\n",
        encoding="utf-8",
    )
    (workspace / "source_index.json").write_text(
        json.dumps({"sources": [stale_source]}) + "\n",
        encoding="utf-8",
    )
    (project_dir / "compiled_evidence_provenance.json").write_text(
        json.dumps({"source_count": 1, "sources": [stale_source]}) + "\n",
        encoding="utf-8",
    )
    (rubric_dir / "stale_trace.json").write_text(
        json.dumps({"dimensions": [{"name": "Fit", "weight": 100, "description": "score fit"}]}),
        encoding="utf-8",
    )

    decision = route_autoresearch_workbench_from_context(
        "evaluate the bounded claim",
        project="stale_trace",
        rubric="stale_trace",
        repo_root=tmp_path,
    )

    assert decision.decision == "prepare_autoresearch_surface"
    assert decision.bounded_claim is True
    assert decision.stable_evaluator is True
    assert decision.rubric_ready is False
    assert decision.artifact_surface is True
    assert "source contract failed preflight" in decision.reasons
    assert (
        "autoresearch trace blocks run readiness: source_index_stale"
        in decision.source_contract_errors
    )
    assert (
        "autoresearch trace blocks run readiness: evidence_compile_stale"
        in decision.source_contract_errors
    )
    assert (
        "autoresearch trace recovery[evidence_prepare]: "
        "make evidence-prepare PROJECT=stale_trace MODEL=gemini"
        in decision.source_contract_errors
    )


def test_router_blocks_stale_source_index_receipt(tmp_path) -> None:
    packet_path = _write_source_ready_project(tmp_path, "stale_source_receipt")
    project_dir = tmp_path / "projects" / "stale_source_receipt"
    workspace = project_dir / "workspace"
    receipt = {
        "schema": "ztare-source-index-receipt-v1",
        "status": "indexed",
        "project": "stale_source_receipt",
        "source_index_sha256": _sha256_file(workspace / "source_index.json"),
        "workspace_meta_sha256": _sha256_file(workspace / "workspace_meta.json"),
    }
    (workspace / "source_index_receipt.json").write_text(
        json.dumps(receipt, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (workspace / "workspace_meta.json").write_text(
        json.dumps({"merge_status": "success", "source_count": 2}) + "\n",
        encoding="utf-8",
    )

    decision = route_autoresearch_workbench_from_context(
        "test a bounded packet-backed claim",
        project="stale_source_receipt",
        rubric="stale_source_receipt",
        packet=str(packet_path),
        repo_root=tmp_path,
    )

    assert decision.decision == "prepare_autoresearch_surface"
    assert decision.kernel_entry_contract["can_enter_kernel"] is False
    assert (
        "autoresearch trace blocks run readiness: source_index_receipt_stale"
        in decision.source_contract_errors
    )
    assert (
        "autoresearch run-readiness recovery[source_index_receipt_stale]: "
        "ztare project source-index --project stale_source_receipt"
        in decision.source_contract_errors
    )


def test_router_surfaces_withheld_graph_focus_when_kernel_entry_is_blocked(tmp_path) -> None:
    packet_path = _write_source_ready_project(tmp_path, "blocked_graph_focus")
    project_dir = tmp_path / "projects" / "blocked_graph_focus"
    workspace = project_dir / "workspace"
    (workspace / "latest_evidence_gaps.json").write_text(
        json.dumps(
            {
                "evidence_gaps": [
                    {
                        "id": "local-check",
                        "severity": "degrading",
                        "target": "next_falsifier_execution",
                        "description": "No evidence that preflight executes the falsifier.",
                        "producer_rationale": "contract_enforcement",
                    }
                ]
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    receipt = {
        "schema": "ztare-source-index-receipt-v1",
        "status": "indexed",
        "project": "blocked_graph_focus",
        "source_index_sha256": _sha256_file(workspace / "source_index.json"),
        "workspace_meta_sha256": _sha256_file(workspace / "workspace_meta.json"),
    }
    (workspace / "source_index_receipt.json").write_text(
        json.dumps(receipt, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (workspace / "workspace_meta.json").write_text(
        json.dumps({"merge_status": "success", "source_count": 2}) + "\n",
        encoding="utf-8",
    )

    decision = route_autoresearch_workbench_from_context(
        "test a bounded packet-backed claim",
        project="blocked_graph_focus",
        rubric="blocked_graph_focus",
        packet=str(packet_path),
        repo_root=tmp_path,
    )

    assert decision.decision == "prepare_autoresearch_surface"
    assert decision.kernel_entry_contract["can_enter_kernel"] is False
    assert decision.kernel_entry_contract["in_loop_focus_receipts"] == []
    assert decision.kernel_entry_contract["withheld_in_loop_focus_receipts"]
    assert any(
        reason.startswith(
            "run-readiness in-loop focus withheld until blockers clear: "
            "resolve 1 local verification gap(s)"
        )
        for reason in decision.reasons
    )
    assert (
        "autoresearch trace blocks run readiness: source_index_receipt_stale"
        in decision.source_contract_errors
    )


def test_router_blocks_stale_compiled_evidence_output(tmp_path) -> None:
    packet_path = _write_source_ready_project(tmp_path, "stale_evidence_output")
    project_dir = tmp_path / "projects" / "stale_evidence_output"
    evidence_path = project_dir / "evidence.txt"
    original_evidence = evidence_path.read_text(encoding="utf-8")
    provenance_path = project_dir / "compiled_evidence_provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["output_path"] = str(evidence_path)
    provenance["output_sha256"] = hashlib.sha256(
        original_evidence.encode("utf-8")
    ).hexdigest()
    provenance_path.write_text(json.dumps(provenance, sort_keys=True) + "\n", encoding="utf-8")
    evidence_path.write_text("Edited evidence packet\n", encoding="utf-8")

    decision = route_autoresearch_workbench_from_context(
        "test a bounded packet-backed claim",
        project="stale_evidence_output",
        rubric="stale_evidence_output",
        packet=str(packet_path),
        repo_root=tmp_path,
    )

    assert decision.decision == "prepare_autoresearch_surface"
    assert decision.kernel_entry_contract["can_enter_kernel"] is False
    assert (
        "autoresearch trace blocks run readiness: evidence_output_stale"
        in decision.source_contract_errors
    )
    assert (
        "autoresearch run-readiness recovery[evidence_output_stale]: "
        "make evidence-prepare PROJECT=stale_evidence_output MODEL=gemini"
        in decision.source_contract_errors
    )


def test_router_cli_infers_context_without_manual_booleans(tmp_path, capsys, monkeypatch) -> None:
    project_dir = tmp_path / "projects" / "gp_example"
    rubric_dir = tmp_path / "rubrics"
    project_dir.mkdir(parents=True)
    rubric_dir.mkdir()
    (project_dir / "current_iteration.md").write_text("claim", encoding="utf-8")
    (project_dir / "test_model.py").write_text("def test_smoke(): pass\n", encoding="utf-8")
    (rubric_dir / "gp_example.json").write_text(
        json.dumps({"dimensions": [{"name": "Fit", "weight": 100, "description": "score fit"}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "ztare.research_director.autoresearch_workbench_router.REPO_ROOT",
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


def test_router_blocks_malformed_weighted_dimensions(tmp_path) -> None:
    project_dir = tmp_path / "projects" / "gp_example"
    rubric_dir = tmp_path / "rubrics"
    project_dir.mkdir(parents=True)
    rubric_dir.mkdir()
    (project_dir / "current_iteration.md").write_text("claim", encoding="utf-8")
    (project_dir / "test_model.py").write_text("def test_smoke(): pass\n", encoding="utf-8")
    (rubric_dir / "gp_example.json").write_text(
        json.dumps(
            {
                "dimensions": [
                    {"name": "Fit", "weight": 70, "description": "score fit"},
                    {"name": "Novelty", "weight": 20, "description": "score novelty"},
                ]
            }
        ),
        encoding="utf-8",
    )

    decision = route_autoresearch_workbench_from_context(
        "evaluate the bounded claim",
        project="gp_example",
        rubric="gp_example",
        repo_root=tmp_path,
    )

    assert decision.decision == "prepare_autoresearch_surface"
    assert decision.rubric_ready is False
    assert "rubric dimensions weights must sum to 100" in decision.source_contract_errors
    assert "source contract failed preflight" in decision.reasons


def test_router_blocks_holdout_gate_without_required_sources(tmp_path) -> None:
    project_dir = tmp_path / "projects" / "gp_example"
    rubric_dir = tmp_path / "rubrics"
    project_dir.mkdir(parents=True)
    rubric_dir.mkdir()
    (project_dir / "current_iteration.md").write_text("claim", encoding="utf-8")
    (project_dir / "test_model.py").write_text("def test_smoke(): pass\n", encoding="utf-8")
    (rubric_dir / "gp_example.json").write_text(
        json.dumps(
            {
                "criteria": {"fit": "score fit"},
                "holdout_hard_gate": True,
            }
        ),
        encoding="utf-8",
    )

    decision = route_autoresearch_workbench_from_context(
        "evaluate the bounded claim",
        project="gp_example",
        rubric="gp_example",
        repo_root=tmp_path,
    )

    assert decision.decision == "prepare_autoresearch_surface"
    assert "holdout_hard_gate requires gate_harness.py" in decision.source_contract_errors
    assert "holdout_hard_gate requires evidence_holdout.txt" in decision.source_contract_errors


def test_router_fails_closed_on_malformed_rubric_json(tmp_path) -> None:
    project_dir = tmp_path / "projects" / "gp_example"
    rubric_dir = tmp_path / "rubrics"
    project_dir.mkdir(parents=True)
    rubric_dir.mkdir()
    (rubric_dir / "gp_example.json").write_text("{not json", encoding="utf-8")

    with pytest.raises(ValueError, match="malformed rubric JSON"):
        route_autoresearch_workbench_from_context(
            "evaluate the bounded claim",
            project="gp_example",
            rubric="gp_example",
            repo_root=tmp_path,
        )


def test_router_fails_closed_on_non_object_rubric_json(tmp_path) -> None:
    project_dir = tmp_path / "projects" / "gp_example"
    rubric_dir = tmp_path / "rubrics"
    project_dir.mkdir(parents=True)
    rubric_dir.mkdir()
    (rubric_dir / "gp_example.json").write_text('["not", "an", "object"]\n', encoding="utf-8")

    with pytest.raises(ValueError, match="top-level value must be an object"):
        route_autoresearch_workbench_from_context(
            "evaluate the bounded claim",
            project="gp_example",
            rubric="gp_example",
            repo_root=tmp_path,
        )


def test_router_blocks_empty_criteria_rubric(tmp_path) -> None:
    project_dir = tmp_path / "projects" / "gp_example"
    rubric_dir = tmp_path / "rubrics"
    project_dir.mkdir(parents=True)
    rubric_dir.mkdir()
    (project_dir / "current_iteration.md").write_text("claim", encoding="utf-8")
    (project_dir / "test_model.py").write_text("def test_smoke(): pass\n", encoding="utf-8")
    (rubric_dir / "gp_example.json").write_text(
        json.dumps({"criteria": {}}),
        encoding="utf-8",
    )

    decision = route_autoresearch_workbench_from_context(
        "evaluate the bounded claim",
        project="gp_example",
        rubric="gp_example",
        repo_root=tmp_path,
    )

    assert decision.decision == "prepare_autoresearch_surface"
    assert decision.rubric_ready is False
    assert "rubric criteria must be a non-empty object when provided" in decision.source_contract_errors
    assert "source contract failed preflight" in decision.reasons


def test_router_blocks_empty_criteria_value(tmp_path) -> None:
    project_dir = tmp_path / "projects" / "gp_example"
    rubric_dir = tmp_path / "rubrics"
    project_dir.mkdir(parents=True)
    rubric_dir.mkdir()
    (project_dir / "current_iteration.md").write_text("claim", encoding="utf-8")
    (project_dir / "test_model.py").write_text("def test_smoke(): pass\n", encoding="utf-8")
    (rubric_dir / "gp_example.json").write_text(
        json.dumps({"criteria": {"fit": ""}}),
        encoding="utf-8",
    )

    decision = route_autoresearch_workbench_from_context(
        "evaluate the bounded claim",
        project="gp_example",
        rubric="gp_example",
        repo_root=tmp_path,
    )

    assert decision.decision == "prepare_autoresearch_surface"
    assert "rubric criteria['fit'] must be non-empty" in decision.source_contract_errors
