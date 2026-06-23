# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SRC = _REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ztare.scaffold import substrate_queue


def test_substrate_queue_resolves_next_unresolved_prep_item(tmp_path: Path) -> None:
    queue_dir = tmp_path / "queue"
    first = substrate_queue.enqueue_item(
        queue_dir=queue_dir,
        task="prepare minimal reproduction for paper A",
        kind="minimal_reproduction",
        project="paper_a",
        rubric="paper_a",
        source_route_json="analytics/public/queries/rd/autoresearch_routes/paper_a.json",
        source_action_impact_id="ai_route_fixture",
        requested_artifact="projects/paper_a/workspace/min_repro.json",
        readiness_criteria=["setup command exits 0", "cost estimate present"],
        claim_boundary="minimal reproduction only; no full replication claim",
        created_at="2026-06-18T00:00:00Z",
    )
    second = substrate_queue.enqueue_item(
        queue_dir=queue_dir,
        task="estimate full replication cost for paper B",
        kind="replication_cost_estimate",
        project="paper_b",
        rubric="paper_b",
        created_at="2026-06-18T00:00:01Z",
    )

    summary = substrate_queue.summarize(queue_dir)
    assert summary["pending_count"] == 2
    assert summary["next_item"]["item_id"] == first["item_id"]

    resolved = substrate_queue.resolve_next_item(
        queue_dir=queue_dir,
        result="ready_for_autoresearch",
        reason="surface prepared",
        artifact_refs=["projects/paper_a/workspace/min_repro.json"],
        resolved_by="test",
        resolved_at="2026-06-18T00:01:00Z",
    )
    assert resolved["item_id"] == first["item_id"]
    assert resolved["status"] == "ready_for_autoresearch"
    assert resolved["artifact_refs"] == ["projects/paper_a/workspace/min_repro.json"]
    assert resolved["source_action_impact_id"] == "ai_route_fixture"

    pending = substrate_queue.pending_items(queue_dir)
    completed = substrate_queue.completed_items(queue_dir)
    events = substrate_queue.read_jsonl(queue_dir / "events.jsonl")
    assert [row["item_id"] for row in pending] == [second["item_id"]]
    assert [row["item_id"] for row in completed] == [first["item_id"]]
    assert [row["event"] for row in events] == ["enqueued", "enqueued", "resolved"]


def test_substrate_queue_requires_reason_for_blocked_result(tmp_path: Path) -> None:
    substrate_queue.enqueue_item(
        queue_dir=tmp_path,
        task="triage repository setup blocker",
        kind="source_setup",
    )
    with pytest.raises(SystemExit, match="requires --reason"):
        substrate_queue.resolve_next_item(
            queue_dir=tmp_path,
            result="blocked_with_reason",
        )


def test_substrate_queue_cli_json_round_trip(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = substrate_queue.main([
        "--queue-dir",
        str(tmp_path),
        "add",
        "--task",
        "prepare project surface",
        "--kind",
        "project_prepare",
        "--project",
        "demo",
        "--rubric",
        "demo",
        "--json",
    ])
    assert rc == 0
    item = json.loads(capsys.readouterr().out)
    assert item["kind"] == "project_prepare"

    rc = substrate_queue.main([
        "--queue-dir",
        str(tmp_path),
        "resolve-next",
        "--result",
        "blocked_with_reason",
        "--reason",
        "missing setup instructions",
        "--json",
    ])
    assert rc == 0
    resolved = json.loads(capsys.readouterr().out)
    assert resolved["item_id"] == item["item_id"]
    assert resolved["status"] == "blocked_with_reason"
    assert resolved["result_reason"] == "missing setup instructions"


def test_project_prep_queue_default_and_legacy_env_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ZTARE_REPO", str(tmp_path))
    monkeypatch.delenv("ZTARE_PROJECT_PREP_QUEUE_DIR", raising=False)
    monkeypatch.delenv("ZTARE_SUBSTRATE_QUEUE_DIR", raising=False)

    assert substrate_queue.queue_dir_from_arg(None) == (
        tmp_path / "analytics/public/queues/project_prep"
    )

    monkeypatch.setenv("ZTARE_SUBSTRATE_QUEUE_DIR", "legacy_queue")
    assert substrate_queue.queue_dir_from_arg(None) == tmp_path / "legacy_queue"

    monkeypatch.setenv("ZTARE_PROJECT_PREP_QUEUE_DIR", "project_queue")
    assert substrate_queue.queue_dir_from_arg(None) == tmp_path / "project_queue"


def test_substrate_queue_add_from_prepare_route(tmp_path: Path) -> None:
    route_path = tmp_path / "route.json"
    route_path.write_text(
        json.dumps(
            {
                "route": {
                    "decision": "prepare_autoresearch_surface",
                    "task": "evaluate bounded paper claim",
                    "project": "paper_a",
                    "rubric": "paper_a",
                    "surface_scaffold": [
                        {
                            "missing": "artifact surface",
                            "surface": "artifact",
                            "artifact": "current_iteration.md",
                            "required_fields": ["mutable_claim_text", "evidence_refs"],
                            "acceptance_check": "mutator can edit the claim",
                        }
                    ],
                },
                "action_impact": {
                    "action_impact_id": "ai_route_prepare",
                    "decision_id": "decision_route_prepare",
                },
            }
        ),
        encoding="utf-8",
    )

    items = substrate_queue.enqueue_from_route(queue_dir=tmp_path / "queue", route_json=route_path)

    assert len(items) == 1
    item = items[0]
    assert item["kind"] == "project_prepare"
    assert item["task"] == "prepare autoresearch surface: artifact surface for evaluate bounded paper claim"
    assert item["project"] == "paper_a"
    assert item["rubric"] == "paper_a"
    assert item["source_route_json"] == str(route_path)
    assert item["source_action_impact_id"] == "ai_route_prepare"
    assert item["decision_id"] == "decision_route_prepare"
    assert item["requested_artifact"] == "current_iteration.md"
    assert item["readiness_criteria"] == [
        "required_field:mutable_claim_text",
        "required_field:evidence_refs",
        "acceptance_check:mutator can edit the claim",
    ]
    assert item["claim_boundary"] == "surface preparation only; no research-result claim"


def test_substrate_queue_rejects_stay_out_of_loop_route(tmp_path: Path) -> None:
    route_path = tmp_path / "route.json"
    route_path.write_text(
        json.dumps({
            "decision": "stay_out_of_loop",
            "task": "explore vague idea",
            "project": "paper_a",
        }),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="RD out-of-loop agent execution"):
        substrate_queue.enqueue_from_route(queue_dir=tmp_path / "queue", route_json=route_path)


def test_substrate_queue_cli_add_from_route(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    route_path = tmp_path / "route.json"
    route_path.write_text(
        json.dumps({
            "decision": "prepare_autoresearch_surface",
            "task": "prepare small reproduction",
            "project": "paper_b",
            "rubric": "paper_b",
            "missing": ["stable evaluator/gate"],
        }),
        encoding="utf-8",
    )

    rc = substrate_queue.main([
        "--queue-dir",
        str(tmp_path / "queue"),
        "add-from-route",
        "--route-json",
        str(route_path),
        "--decision-id",
        "decision_route_b",
        "--json",
    ])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["count"] == 1
    item = payload["enqueued"][0]
    assert item["decision_id"] == "decision_route_b"
    assert item["requested_artifact"] is None
    assert item["task"] == "prepare autoresearch surface: stable evaluator/gate for prepare small reproduction"


def test_project_packet_validate_and_enqueue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    packet_path = tmp_path / "packet.json"
    source_ref = tmp_path / "paper.md"
    source_ref_2 = tmp_path / "repo" / "README.md"
    raw = tmp_path / "projects" / "paper_c" / "raw"
    evidence_ref = tmp_path / "projects" / "paper_c" / "workspace" / "min_repro.json"
    raw.mkdir(parents=True)
    (raw / "source.md").write_text("Primary source text.\n", encoding="utf-8")
    (raw / "source_type_map.json").write_text(
        json.dumps({"source.md": "source_evidence"}) + "\n",
        encoding="utf-8",
    )
    source_ref.write_text("source", encoding="utf-8")
    source_ref_2.parent.mkdir(parents=True)
    source_ref_2.write_text("repo source", encoding="utf-8")
    evidence_ref.parent.mkdir(parents=True)
    evidence_ref.write_text('{"ok": true}\n', encoding="utf-8")
    packet = substrate_queue.build_project_packet(
        project="paper_c",
        rubric="paper_c",
        task="test a bounded reproduction claim",
        bounded_claim="the minimal reproduction reaches the documented baseline on fixture data",
        source_refs=["paper.md", "repo/README.md"],
        evidence_refs=["projects/paper_c/workspace/min_repro.json"],
        non_claims=["not a full replication"],
        next_falsifier="run the full setup from a clean checkout",
        expected_command="ztare autoresearch route --task 'test a bounded reproduction claim' --project paper_c --rubric paper_c",
        created_at="2026-06-19T00:00:00Z",
    )
    substrate_queue.write_project_packet(packet_path, packet)

    validation = substrate_queue.validate_project_packet_path(packet_path)
    assert validation["ok"] is True
    assert validation["errors"] == []

    item = substrate_queue.enqueue_project_packet(
        queue_dir=tmp_path / "queue",
        packet_path=packet_path,
        decision_id="decision_packet_c",
        created_at="2026-06-19T00:01:00Z",
    )

    assert item["kind"] == "project_intake"
    assert item["project"] == "paper_c"
    assert item["rubric"] == "paper_c"
    assert item["decision_id"] == "decision_packet_c"
    assert item["requested_artifact"] == str(packet_path)
    assert item["readiness_criteria"] == [
        "intake_validates",
        "source_refs_present",
        "evidence_refs_present",
        "non_claims_present",
        "next_falsifier_present",
    ]
    assert "no RD out-of-loop execution" in item["claim_boundary"]


def test_project_packet_runs_source_preflight_for_existing_project(tmp_path: Path) -> None:
    raw = tmp_path / "projects" / "paper_ready" / "raw"
    workspace = tmp_path / "projects" / "paper_ready" / "workspace"
    raw.mkdir(parents=True)
    workspace.mkdir(parents=True)
    (raw / "source.md").write_text("Primary source text.\n", encoding="utf-8")
    (raw / "source_type_map.json").write_text(
        json.dumps({"source.md": "source_evidence"}) + "\n",
        encoding="utf-8",
    )
    (workspace / "min_repro.json").write_text('{"ok": true}\n', encoding="utf-8")
    packet = substrate_queue.build_project_packet(
        project="paper_ready",
        rubric="paper_ready",
        task="test a bounded reproduction claim",
        bounded_claim="the minimal reproduction reaches the documented baseline on fixture data",
        source_refs=["projects/paper_ready/raw/source.md"],
        evidence_refs=["projects/paper_ready/workspace/min_repro.json"],
        non_claims=["not a full replication"],
        next_falsifier="run the full setup from a clean checkout",
        expected_command="ztare autoresearch route --task 'test claim' --project paper_ready --rubric paper_ready",
        created_at="2026-06-19T00:00:00Z",
    )

    validation = substrate_queue.validate_project_packet(
        packet,
        base_dir=tmp_path,
        repo_root=tmp_path,
    )

    assert validation["ok"] is True
    assert validation["source_preflight"]["checked"] is True
    assert validation["source_preflight"]["status"] == "ready_for_evidence_prepare"
    assert validation["source_preflight"]["source_evidence_count"] == 1


def test_project_packet_falsifier_fails_when_declared_evidence_ref_is_removed(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "projects" / "paper_ready" / "raw"
    workspace = tmp_path / "projects" / "paper_ready" / "workspace"
    packet_path = tmp_path / "packet.json"
    raw.mkdir(parents=True)
    workspace.mkdir(parents=True)
    (raw / "source.md").write_text("Primary source text.\n", encoding="utf-8")
    (raw / "source_type_map.json").write_text(
        json.dumps({"source.md": "source_evidence"}) + "\n",
        encoding="utf-8",
    )
    (workspace / "min_repro.json").write_text('{"ok": true}\n', encoding="utf-8")
    packet = substrate_queue.build_project_packet(
        project="paper_ready",
        rubric="paper_ready",
        task="test a bounded reproduction claim",
        bounded_claim="the minimal reproduction reaches the documented baseline on fixture data",
        source_refs=["projects/paper_ready/raw/source.md"],
        evidence_refs=["projects/paper_ready/workspace/min_repro.json"],
        non_claims=["not a full replication"],
        next_falsifier="remove the evidence ref and intake validation must fail",
        expected_command="ztare autoresearch route --task 'test claim' --project paper_ready --rubric paper_ready",
        created_at="2026-06-19T00:00:00Z",
    )
    substrate_queue.write_project_packet(packet_path, packet)

    result = substrate_queue.validate_project_packet_falsifier(
        packet_path,
        remove_ref="evidence_refs[1]",
    )

    assert result["ok"] is True
    assert result["removed_ref"] == "projects/paper_ready/workspace/min_repro.json"
    assert result["baseline"]["ok"] is True
    assert result["falsified"]["ok"] is False
    assert (
        "evidence_refs[1] local path does not exist"
        in "\n".join(result["falsified"]["errors"])
    )
    assert result["path_safety"]["absolute_local_refs_allowed"] is False
    assert result["path_safety"]["parent_traversal_allowed"] is False
    assert result["path_safety"]["symlink_escape_allowed"] is False
    assert "test_project_packet_rejects_symlink_escape_local_ref" in " ".join(
        result["path_safety"]["enforced_by"]
    )


def test_project_packet_falsifier_cli_writes_workspace_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    raw = tmp_path / "projects" / "paper_ready" / "raw"
    workspace = tmp_path / "projects" / "paper_ready" / "workspace"
    packet_path = tmp_path / "packet.json"
    raw.mkdir(parents=True)
    workspace.mkdir(parents=True)
    (raw / "source.md").write_text("Primary source text.\n", encoding="utf-8")
    (raw / "source_type_map.json").write_text(
        json.dumps({"source.md": "source_evidence"}) + "\n",
        encoding="utf-8",
    )
    (workspace / "min_repro.json").write_text('{"ok": true}\n', encoding="utf-8")
    packet = substrate_queue.build_project_packet(
        project="paper_ready",
        rubric="paper_ready",
        task="test a bounded reproduction claim",
        bounded_claim="the minimal reproduction reaches the documented baseline on fixture data",
        source_refs=["projects/paper_ready/raw/source.md"],
        evidence_refs=["projects/paper_ready/workspace/min_repro.json"],
        non_claims=["not a full replication"],
        next_falsifier="remove the evidence ref and intake validation must fail",
        expected_command=(
            "ztare autoresearch route --task 'test claim' "
            "--project paper_ready --rubric paper_ready"
        ),
        created_at="2026-06-19T00:00:00Z",
    )
    substrate_queue.write_project_packet(packet_path, packet)
    monkeypatch.chdir(tmp_path)

    rc = substrate_queue.main(
        [
            "falsify-packet",
            "--path",
            str(packet_path),
            "--remove-ref",
            "evidence_refs[1]",
            "--write-workspace-receipt",
            "--json",
        ]
    )

    out = json.loads(capsys.readouterr().out)
    receipt_path = workspace / "packet_falsifier_receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert rc == 0
    assert out["receipt_paths"] == [str(receipt_path)]
    assert receipt["status"] == "resolved"
    assert receipt["receipt_type"] == "project_packet_falsifier"
    assert receipt["remove_ref"] == "evidence_refs[1]"
    assert receipt["removed_ref"] == "projects/paper_ready/workspace/min_repro.json"
    assert "local path does not exist" in receipt["expected_failure"]
    assert receipt["path_safety"]["symlink_escape_allowed"] is False
    assert "--write-workspace-receipt" in receipt["command"]


def test_project_packet_blocks_invalid_local_source_preflight(tmp_path: Path) -> None:
    raw = tmp_path / "projects" / "paper_bad_source" / "raw"
    workspace = tmp_path / "projects" / "paper_bad_source" / "workspace"
    raw.mkdir(parents=True)
    workspace.mkdir(parents=True)
    (raw / "source.md").write_text(
        "---\nsource_type: primary_fact\n---\nSource text.\n",
        encoding="utf-8",
    )
    (workspace / "min_repro.json").write_text('{"ok": true}\n', encoding="utf-8")
    packet = substrate_queue.build_project_packet(
        project="paper_bad_source",
        rubric="paper_bad_source",
        task="test a bounded reproduction claim",
        bounded_claim="the minimal reproduction reaches the documented baseline on fixture data",
        source_refs=["projects/paper_bad_source/raw/source.md"],
        evidence_refs=["projects/paper_bad_source/workspace/min_repro.json"],
        non_claims=["not a full replication"],
        next_falsifier="run the full setup from a clean checkout",
        expected_command=(
            "ztare autoresearch route --task 'test claim' "
            "--project paper_bad_source --rubric paper_bad_source"
        ),
        created_at="2026-06-19T00:00:00Z",
    )

    validation = substrate_queue.validate_project_packet(
        packet,
        base_dir=tmp_path,
        repo_root=tmp_path,
    )

    assert validation["ok"] is False
    assert validation["source_preflight"]["checked"] is True
    assert validation["source_preflight"]["status"] == "blocked"
    assert (
        "source_preflight: one or more sources declare an invalid source_type"
        in validation["errors"]
    )


def test_project_packet_can_skip_source_preflight_for_trace_packet_shape(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "projects" / "paper_shape_only" / "raw"
    workspace = tmp_path / "projects" / "paper_shape_only" / "workspace"
    raw.mkdir(parents=True)
    workspace.mkdir(parents=True)
    (raw / "source.md").write_text(
        "---\nsource_type: invented_type\n---\nSource text.\n",
        encoding="utf-8",
    )
    (workspace / "min_repro.json").write_text('{"ok": true}\n', encoding="utf-8")
    packet = substrate_queue.build_project_packet(
        project="paper_shape_only",
        rubric="paper_shape_only",
        task="test packet shape only",
        bounded_claim="the packet shape is valid even when source readiness is checked elsewhere",
        source_refs=["projects/paper_shape_only/raw/source.md"],
        evidence_refs=["projects/paper_shape_only/workspace/min_repro.json"],
        non_claims=["not a source-readiness pass"],
        next_falsifier="run source-check separately",
        expected_command=(
            "ztare autoresearch route --task 'test packet shape only' "
            "--project paper_shape_only --rubric paper_shape_only"
        ),
        created_at="2026-06-19T00:00:00Z",
    )

    validation = substrate_queue.validate_project_packet(
        packet,
        base_dir=tmp_path,
        repo_root=tmp_path,
        require_source_preflight=False,
    )

    assert validation["ok"] is True
    assert validation["source_preflight"]["checked"] is False
    assert validation["source_preflight"]["status"] == "skipped"


def test_project_packet_enqueue_requires_local_source_preflight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    packet_path = tmp_path / "needs_source_packet.json"
    source_ref = tmp_path / "paper.md"
    evidence_ref = tmp_path / "projects" / "paper_needs_source" / "workspace" / "min_repro.json"
    source_ref.write_text("source", encoding="utf-8")
    evidence_ref.parent.mkdir(parents=True)
    evidence_ref.write_text('{"ok": true}\n', encoding="utf-8")
    packet = substrate_queue.build_project_packet(
        project="paper_needs_source",
        rubric="paper_needs_source",
        task="test a bounded reproduction claim",
        bounded_claim="the minimal reproduction reaches the documented baseline on fixture data",
        source_refs=["paper.md"],
        evidence_refs=["projects/paper_needs_source/workspace/min_repro.json"],
        non_claims=["not a full replication"],
        next_falsifier="run the full setup from a clean checkout",
        expected_command=(
            "ztare autoresearch route --task 'test claim' "
            "--project paper_needs_source --rubric paper_needs_source"
        ),
        created_at="2026-06-19T00:00:00Z",
    )
    substrate_queue.write_project_packet(packet_path, packet)

    validation = substrate_queue.validate_project_packet(
        packet,
        base_dir=tmp_path,
        repo_root=tmp_path,
        require_source_preflight=False,
    )
    assert validation["ok"] is True

    with pytest.raises(SystemExit, match="project intake is not ready"):
        substrate_queue.enqueue_project_packet(
            queue_dir=tmp_path / "queue",
            packet_path=packet_path,
        )


def test_project_packet_rejects_missing_evidence_refs(tmp_path: Path) -> None:
    packet_path = tmp_path / "bad_packet.json"
    packet_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "execution_boundary": substrate_queue.PACKET_BOUNDARY,
                "project": "paper_d",
                "rubric": "paper_d",
                "task": "test claim",
                "bounded_claim": "bounded claim",
                "source_refs": ["paper.md"],
                "evidence_refs": [],
                "non_claims": ["not a full replication"],
                "next_falsifier": "clean checkout run",
                "expected_command": "make experiment-loop PROJECT=paper_d RUBRIC=paper_d",
            }
        ),
        encoding="utf-8",
    )

    validation = substrate_queue.validate_project_packet_path(packet_path)
    assert validation["ok"] is False
    assert "missing required non-empty list: evidence_refs" in validation["errors"]
    with pytest.raises(SystemExit, match="project intake is not ready"):
        substrate_queue.enqueue_project_packet(queue_dir=tmp_path / "queue", packet_path=packet_path)


def test_project_packet_rejects_missing_local_source_or_evidence_ref(tmp_path: Path) -> None:
    packet_path = tmp_path / "bad_refs_packet.json"
    packet_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "execution_boundary": substrate_queue.PACKET_BOUNDARY,
                "project": "paper_missing",
                "rubric": "paper_missing",
                "task": "test claim",
                "bounded_claim": "bounded claim",
                "source_refs": ["missing_source.md"],
                "evidence_refs": ["workspace/missing_evidence.json"],
                "non_claims": ["not a full replication"],
                "next_falsifier": "clean checkout run",
                "expected_command": "make experiment-loop PROJECT=paper_missing RUBRIC=paper_missing",
            }
        ),
        encoding="utf-8",
    )

    validation = substrate_queue.validate_project_packet_path(packet_path)

    assert validation["ok"] is False
    assert "source_refs[1] local path does not exist: missing_source.md" in validation["errors"]
    assert (
        "evidence_refs[1] local path does not exist: workspace/missing_evidence.json"
        in validation["errors"]
    )


def test_project_packet_rejects_parent_traversal_local_ref(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence.md"
    evidence.write_text("evidence", encoding="utf-8")
    packet = substrate_queue.build_project_packet(
        project="paper_traversal",
        rubric="paper_traversal",
        task="test claim",
        bounded_claim="bounded claim",
        source_refs=["../outside.md"],
        evidence_refs=["evidence.md"],
        non_claims=["not a full replication"],
        next_falsifier="clean checkout run",
        expected_command="ztare autoresearch route --task 'test claim' --project paper_traversal --rubric paper_traversal",
    )

    validation = substrate_queue.validate_project_packet(
        packet,
        base_dir=tmp_path,
        repo_root=tmp_path,
        require_source_preflight=False,
    )

    assert validation["ok"] is False
    assert (
        "source_refs[1] unsafe local path: ../outside.md "
        "(path traversal or empty path segment is not allowed)"
    ) in validation["errors"]


def test_project_packet_rejects_symlink_escape_local_ref(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_source = outside / "source.md"
    outside_source.write_text("outside source", encoding="utf-8")
    link = repo / "linked_source.md"
    try:
        link.symlink_to(outside_source)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation unavailable on this filesystem")
    (repo / "evidence.md").write_text("evidence", encoding="utf-8")
    packet = substrate_queue.build_project_packet(
        project="paper_symlink",
        rubric="paper_symlink",
        task="test claim",
        bounded_claim="bounded claim",
        source_refs=["linked_source.md"],
        evidence_refs=["evidence.md"],
        non_claims=["not a full replication"],
        next_falsifier="clean checkout run",
        expected_command="ztare autoresearch route --task 'test claim' --project paper_symlink --rubric paper_symlink",
    )

    validation = substrate_queue.validate_project_packet(
        packet,
        base_dir=repo,
        repo_root=repo,
        require_source_preflight=False,
    )

    assert validation["ok"] is False
    assert (
        "source_refs[1] unsafe local path: linked_source.md "
        "(resolved path escapes allowed roots)"
    ) in validation["errors"]


def test_project_packet_rejects_non_string_scalar_and_list_values(tmp_path: Path) -> None:
    packet_path = tmp_path / "bad_types_packet.json"
    packet_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "execution_boundary": substrate_queue.PACKET_BOUNDARY,
                "project": "paper_types",
                "rubric": 42,
                "task": "test claim",
                "bounded_claim": True,
                "source_refs": ["paper.md", {"path": "smuggled.md"}],
                "evidence_refs": [123],
                "non_claims": ["not a full replication", None],
                "next_falsifier": "clean checkout run",
                "expected_command": "make experiment-loop PROJECT=paper_types RUBRIC=paper_types",
            }
        ),
        encoding="utf-8",
    )

    validation = substrate_queue.validate_project_packet_path(packet_path)

    assert validation["ok"] is False
    assert "missing required field: rubric" in validation["errors"]
    assert "missing required field: bounded_claim" in validation["errors"]
    assert "source_refs[2] must be a non-empty string" in validation["errors"]
    assert "evidence_refs[1] must be a non-empty string" in validation["errors"]
    assert "non_claims[2] must be a non-empty string" in validation["errors"]


def test_project_packet_accepts_external_uri_refs(tmp_path: Path) -> None:
    packet_path = tmp_path / "uri_refs_packet.json"
    packet = substrate_queue.build_project_packet(
        project="paper_uri",
        rubric="paper_uri",
        task="test a bounded reproduction claim",
        bounded_claim="the minimal reproduction reaches the documented baseline on fixture data",
        source_refs=["https://example.test/paper"],
        evidence_refs=["ztare://artifact/min_repro"],
        non_claims=["not a full replication"],
        next_falsifier="run the full setup from a clean checkout",
        expected_command="ztare autoresearch route --task 'test claim' --project paper_uri --rubric paper_uri",
        created_at="2026-06-19T00:00:00Z",
    )
    substrate_queue.write_project_packet(packet_path, packet)

    validation = substrate_queue.validate_project_packet_path(packet_path)

    assert validation["ok"] is True
    assert validation["errors"] == []


def test_project_packet_rejects_expected_command_for_different_project_or_rubric(tmp_path: Path) -> None:
    source_ref = tmp_path / "paper.md"
    evidence_ref = tmp_path / "evidence.json"
    source_ref.write_text("source", encoding="utf-8")
    evidence_ref.write_text('{"ok": true}\n', encoding="utf-8")
    packet_path = tmp_path / "bad_command_packet.json"
    packet = substrate_queue.build_project_packet(
        project="paper_expected",
        rubric="paper_expected",
        task="test a bounded reproduction claim",
        bounded_claim="the minimal reproduction reaches the documented baseline on fixture data",
        source_refs=["paper.md"],
        evidence_refs=["evidence.json"],
        non_claims=["not a full replication"],
        next_falsifier="run the full setup from a clean checkout",
        expected_command="ztare autoresearch route --task 'test claim' --project other --rubric other",
        created_at="2026-06-19T00:00:00Z",
    )
    substrate_queue.write_project_packet(packet_path, packet)

    validation = substrate_queue.validate_project_packet_path(packet_path)

    assert validation["ok"] is False
    assert "expected_command must name the intake project" in validation["errors"]
    assert "expected_command must name the intake rubric" in validation["errors"]


def test_project_packet_rejects_expected_command_substring_masquerade(tmp_path: Path) -> None:
    source_ref = tmp_path / "paper.md"
    evidence_ref = tmp_path / "evidence.json"
    source_ref.write_text("source", encoding="utf-8")
    evidence_ref.write_text('{"ok": true}\n', encoding="utf-8")
    packet_path = tmp_path / "substring_command_packet.json"
    packet = substrate_queue.build_project_packet(
        project="paper_expected",
        rubric="paper_expected",
        task="test a bounded reproduction claim",
        bounded_claim="the minimal reproduction reaches the documented baseline on fixture data",
        source_refs=["paper.md"],
        evidence_refs=["evidence.json"],
        non_claims=["not a full replication"],
        next_falsifier="run the full setup from a clean checkout",
        expected_command=(
            "ztare autoresearch route --task 'mentions --project paper_expected "
            "--rubric paper_expected' --project other --rubric other"
        ),
        created_at="2026-06-19T00:00:00Z",
    )
    substrate_queue.write_project_packet(packet_path, packet)

    validation = substrate_queue.validate_project_packet_path(packet_path)

    assert validation["ok"] is False
    assert "expected_command must name the intake project" in validation["errors"]
    assert "expected_command must name the intake rubric" in validation["errors"]


def test_project_packet_rejects_expected_command_shell_compound(tmp_path: Path) -> None:
    source_ref = tmp_path / "paper.md"
    evidence_ref = tmp_path / "evidence.json"
    source_ref.write_text("source", encoding="utf-8")
    evidence_ref.write_text('{"ok": true}\n', encoding="utf-8")
    packet_path = tmp_path / "compound_command_packet.json"
    packet = substrate_queue.build_project_packet(
        project="paper_expected",
        rubric="paper_expected",
        task="test a bounded reproduction claim",
        bounded_claim="the minimal reproduction reaches the documented baseline on fixture data",
        source_refs=["paper.md"],
        evidence_refs=["evidence.json"],
        non_claims=["not a full replication"],
        next_falsifier="run the full setup from a clean checkout",
        expected_command=(
            "ztare autoresearch route --task 'test claim' --project paper_expected "
            "--rubric paper_expected; ztare autoresearch run --project paper_expected --rubric paper_expected"
        ),
        created_at="2026-06-19T00:00:00Z",
    )
    substrate_queue.write_project_packet(packet_path, packet)

    validation = substrate_queue.validate_project_packet_path(packet_path)

    assert validation["ok"] is False
    assert (
        "expected_command must be a single in-loop command without shell control operators"
        in validation["errors"]
    )


def test_substrate_queue_cli_packet_round_trip(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    packet_path = tmp_path / "packet.json"
    queue_dir = tmp_path / "queue"
    source_ref = tmp_path / "paper.md"
    raw = tmp_path / "projects" / "paper_e" / "raw"
    evidence_ref = tmp_path / "projects" / "paper_e" / "workspace" / "min_repro.json"
    raw.mkdir(parents=True)
    (raw / "source.md").write_text("Primary source text.\n", encoding="utf-8")
    (raw / "source_type_map.json").write_text(
        json.dumps({"source.md": "source_evidence"}) + "\n",
        encoding="utf-8",
    )
    source_ref.write_text("source", encoding="utf-8")
    evidence_ref.parent.mkdir(parents=True)
    evidence_ref.write_text('{"ok": true}\n', encoding="utf-8")

    rc = substrate_queue.main([
        "--queue-dir",
        str(queue_dir),
        "create-packet",
        "--path",
        str(packet_path),
        "--project",
        "paper_e",
        "--rubric",
        "paper_e",
        "--task",
        "test bounded claim",
        "--bounded-claim",
        "the fixture reproduces the reported scalar",
        "--source-ref",
        "paper.md",
        "--evidence-ref",
        "projects/paper_e/workspace/min_repro.json",
        "--non-claim",
        "not full replication",
        "--next-falsifier",
        "run external dependency setup",
        "--expected-command",
        "make experiment-loop PROJECT=paper_e RUBRIC=paper_e",
        "--json",
    ])
    assert rc == 0
    created = json.loads(capsys.readouterr().out)
    assert created["validation"]["ok"] is True
    assert packet_path.exists()

    rc = substrate_queue.main([
        "--queue-dir",
        str(queue_dir),
        "validate-packet",
        "--path",
        str(packet_path),
        "--json",
    ])
    assert rc == 0
    validation = json.loads(capsys.readouterr().out)
    assert validation["ok"] is True

    rc = substrate_queue.main([
        "--queue-dir",
        str(queue_dir),
        "enqueue-packet",
        "--path",
        str(packet_path),
        "--json",
    ])
    assert rc == 0
    item = json.loads(capsys.readouterr().out)
    assert item["kind"] == "project_intake"
    assert item["requested_artifact"] == str(packet_path)
