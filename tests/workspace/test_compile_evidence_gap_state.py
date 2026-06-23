from __future__ import annotations

import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ztare.workspace import compile_evidence as ce
from ztare.workspace.compile_evidence import (
    EVIDENCE_GAP_ACTION_SCHEMA,
    EVIDENCE_REPLAY_MANIFEST_SCHEMA,
    build_evidence_gap_action_contract,
    load_active_evidence_gaps,
    render_evidence_gap_brief,
    render_no_active_evidence_gap_brief,
)
from ztare.workspace.evidence_gap_resolutions import main as evidence_gap_main
from ztare.workspace.evidence_gap_resolutions import write_gap_resolution
from ztare.workspace.evidence_gaps import evidence_gap_recovery
from ztare.workspace.evidence_replay import verify_evidence_replay_manifest


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _workspace_packet(project: str) -> dict:
    return {
        "project": project,
        "compiler_summary": "test packet",
        "immutable_ground_truth": [],
        "numerical_ranges_and_constraints": [],
        "identified_contradictions": [],
        "epistemic_voids": [],
        "provenance": [],
        "candidate_claims_to_test": [],
    }


def test_compile_evidence_provenance_binds_output_hashes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project = tmp_path / "demo"
    workspace = project / "workspace"
    workspace.mkdir(parents=True)
    _write_json(workspace / "workspace_snapshot.json", _workspace_packet("demo"))
    monkeypatch.setattr(
        sys,
        "argv",
        ["compile-evidence", "--project", str(project), "--mode", "workspace"],
    )

    rc = ce.main()

    assert rc == 0
    evidence_path = project / "evidence.txt"
    packet_path = project / "compiled_evidence_packet.json"
    replay_path = project / "compiled_evidence_replay_manifest.json"
    provenance = json.loads(
        (project / "compiled_evidence_provenance.json").read_text(encoding="utf-8")
    )
    replay_manifest = json.loads(replay_path.read_text(encoding="utf-8"))
    assert provenance["output_path"] == str(evidence_path)
    assert provenance["output_sha256"] == hashlib.sha256(
        evidence_path.read_bytes()
    ).hexdigest()
    assert provenance["audit_copy_path"] == str(project / "compiled_evidence.txt")
    assert provenance["audit_copy_sha256"] == hashlib.sha256(
        (project / "compiled_evidence.txt").read_bytes()
    ).hexdigest()
    assert provenance["packet_output_path"] == str(packet_path)
    assert provenance["packet_output_sha256"] == hashlib.sha256(
        packet_path.read_bytes()
    ).hexdigest()
    assert provenance["evidence_replay_manifest_path"] == str(replay_path)
    assert provenance["evidence_replay_manifest_sha256"] == hashlib.sha256(
        replay_path.read_bytes()
    ).hexdigest()
    assert provenance["support_binding_sha256"] == replay_manifest["support_binding_sha256"]
    assert provenance["input_binding_sha256"] == replay_manifest["input_binding_sha256"]
    assert replay_manifest["schema"] == EVIDENCE_REPLAY_MANIFEST_SCHEMA
    assert replay_manifest["mode"] == "workspace"
    assert replay_manifest["replay_mode"] == "workspace_snapshot_replay"
    assert replay_manifest["input_projection"]["workspace_snapshot_sha256"] == hashlib.sha256(
        (workspace / "workspace_snapshot.json").read_bytes()
    ).hexdigest()
    assert replay_manifest["support_projection_counts"] == {
        "immutable_ground_truth": 0,
        "numerical_ranges_and_constraints": 0,
        "identified_contradictions": 0,
        "epistemic_voids": 0,
        "provenance": 0,
        "candidate_claims_to_test": 0,
    }

    replay_check = verify_evidence_replay_manifest(project)
    assert replay_check["ok"] is True
    assert replay_check["status"] == "ok"
    assert replay_check["support_binding_sha256"] == replay_manifest["support_binding_sha256"]


def test_evidence_replay_detects_stale_compiled_evidence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project = tmp_path / "demo"
    workspace = project / "workspace"
    workspace.mkdir(parents=True)
    _write_json(workspace / "workspace_snapshot.json", _workspace_packet("demo"))
    monkeypatch.setattr(
        sys,
        "argv",
        ["compile-evidence", "--project", str(project), "--mode", "workspace"],
    )
    assert ce.main() == 0

    (project / "evidence.txt").write_text("tampered evidence\n", encoding="utf-8")

    replay_check = verify_evidence_replay_manifest(project)
    assert replay_check["ok"] is False
    assert replay_check["status"] == "stale_or_invalid"
    assert any("evidence_txt hash mismatch" in error for error in replay_check["errors"])


def test_load_active_evidence_gaps_skips_inactive_champion_rows(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    _write_json(
        workspace / "champion_evidence_gaps.json",
        {
            "evidence_gaps": [
                {"id": "old", "severity": "degrading", "status": "resolved"},
            ]
        },
    )
    _write_json(
        workspace / "latest_evidence_gaps.json",
        {
            "generated_on": "2026-06-20T00:00:00Z",
            "evidence_gaps": [
                {"id": "active", "severity": "degrading", "target": "active target"},
                {"id": "ignored", "severity": "degrading", "status": "justified"},
            ],
        },
    )

    payload, source_path, warnings = load_active_evidence_gaps(workspace)

    assert source_path == workspace / "latest_evidence_gaps.json"
    assert payload is not None
    assert payload["active_evidence_gap_count"] == 1
    assert payload["inactive_evidence_gap_count"] == 1
    assert payload["recovery_kind_counts"] == {"public_evidence": 1}
    assert len(payload["evidence_gaps"]) == 1
    active_gap = payload["evidence_gaps"][0]
    assert "recovery_contract" in active_gap
    assert {
        key: active_gap[key]
        for key in (
            "id",
            "severity",
            "target",
            "recovery_kind",
            "recovery_channel",
            "required_surface",
            "can_public_fetch",
            "in_loop_consumable",
            "recovery_contract_source",
        )
    } == {
        "id": "active",
        "severity": "degrading",
        "target": "active target",
        "recovery_kind": "public_evidence",
        "recovery_channel": "out_of_loop_evidence_recovery",
        "required_surface": "public_or_local_source",
        "can_public_fetch": True,
        "in_loop_consumable": False,
        "recovery_contract_source": "sanitized_inference",
    }
    assert active_gap["recovery_contract"]["schema"] == (
        "ztare-evidence-gap-recovery-contract-v1"
    )
    assert active_gap["recovery_contract"]["contract_ok"] is True
    assert active_gap["recovery_contract"]["can_public_fetch"] is True
    assert "champion_evidence_gaps.json contains no active evidence gaps." in warnings


def test_load_active_evidence_gaps_skips_repaired_local_artifact_gap(
    tmp_path: Path,
) -> None:
    project = tmp_path / "demo"
    workspace = project / "workspace"
    project.mkdir(parents=True)
    (project / "test_model.py").write_text(
        "def I_model():\n    return 1.0\n",
        encoding="utf-8",
    )
    _write_json(
        workspace / "latest_evidence_gaps.json",
        {
            "generated_on": "2026-06-20T00:00:00Z",
            "evidence_gaps": [
                {
                    "id": "missing-suite",
                    "severity": "degrading",
                    "target": "test_model.py",
                    "description": "The falsification suite is missing.",
                }
            ],
        },
    )

    payload, source_path, warnings = load_active_evidence_gaps(workspace)

    assert payload is None
    assert source_path is None
    assert "latest_evidence_gaps.json contains no active evidence gaps." in warnings


def test_load_active_evidence_gaps_skips_hash_bound_gap_resolution(
    tmp_path: Path,
) -> None:
    project = tmp_path / "demo"
    workspace = project / "workspace"
    _write_json(
        workspace / "latest_evidence_gaps.json",
        {
            "generated_on": "2026-06-20T00:00:00Z",
            "evidence_gaps": [
                {
                    "id": "public-gap",
                    "severity": "degrading",
                    "target": "benchmark baseline",
                    "description": "Need another public comparator.",
                }
            ],
        },
    )

    write_gap_resolution(
        project_dir=project,
        gap_id="public-gap",
        reason="Comparator is out of scope for this bounded packet.",
        repo=tmp_path,
    )

    payload, source_path, warnings = load_active_evidence_gaps(workspace)

    assert payload is None
    assert source_path is None
    assert "latest_evidence_gaps.json contains no active evidence gaps." in warnings


def test_gap_resolution_can_target_active_champion_gap_source(tmp_path: Path) -> None:
    project = tmp_path / "demo"
    workspace = project / "workspace"
    latest = workspace / "latest_evidence_gaps.json"
    champion = workspace / "champion_evidence_gaps.json"
    _write_json(
        champion,
        {
            "generated_on": "2026-06-20T00:00:00Z",
            "evidence_gaps": [
                {
                    "target": "cached champion gap",
                    "description": "Champion gap is the active source for this project.",
                    "severity": "degrading",
                    "recovery_kind": "local_verification",
                }
            ],
        },
    )
    _write_json(
        latest,
        {
            "generated_on": "2026-06-20T00:00:00Z",
            "evidence_gaps": [
                {
                    "id": "latest-gap",
                    "target": "latest gap",
                    "description": "Latest gap should not be selected by active-source resolution.",
                    "severity": "degrading",
                }
            ],
        },
    )

    write_gap_resolution(
        project_dir=project,
        target="cached champion gap",
        source="active",
        reason="The active champion gap is covered by local verifier evidence.",
        repo=tmp_path,
    )

    payload, source_path, warnings = load_active_evidence_gaps(workspace)

    assert source_path == latest
    assert payload is not None
    assert payload["active_evidence_gap_count"] == 1
    assert payload["evidence_gaps"][0]["target"] == "latest gap"
    assert "champion_evidence_gaps.json contains no active evidence gaps." in warnings


def test_gap_resolution_parallel_writes_preserve_all_rows(tmp_path: Path) -> None:
    project = tmp_path / "demo"
    workspace = project / "workspace"
    gap_count = 8
    _write_json(
        workspace / "latest_evidence_gaps.json",
        {
            "generated_on": "2026-06-20T00:00:00Z",
            "evidence_gaps": [
                {
                    "id": f"gap-{idx}",
                    "target": f"target-{idx}",
                    "description": f"Need local receipt {idx}.",
                    "severity": "degrading",
                }
                for idx in range(gap_count)
            ],
        },
    )

    def _resolve(idx: int) -> None:
        write_gap_resolution(
            project_dir=project,
            gap_id=f"gap-{idx}",
            reason=f"Parallel receipt {idx} is covered by the local project fixture.",
            repo=tmp_path,
        )

    with ThreadPoolExecutor(max_workers=gap_count) as pool:
        list(pool.map(_resolve, range(gap_count)))

    receipt = json.loads((workspace / "evidence_gap_resolutions.json").read_text(encoding="utf-8"))
    rows = receipt["resolutions"]

    assert receipt["resolution_count"] == gap_count
    assert sorted(row["gap_id"] for row in rows) == [f"gap-{idx}" for idx in range(gap_count)]
    assert not (workspace / "evidence_gap_resolutions.json.lock").exists()


def test_protocol_definition_gap_routes_to_local_verification(tmp_path: Path) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    gap = {
        "gap_type": "other",
        "target": "extraction_yield_floor",
        "description": "No operational definition of minimum documented yield threshold for the audit gate.",
        "severity": "degrading",
        "producer": "meta_judge",
        "producer_rationale": (
            "Gate cannot be executed or falsified without a numeric or "
            "pattern-based floor."
        ),
        "fetch_query": "define yield floor from claim card patterns",
    }

    recovery = evidence_gap_recovery(gap, project_dir=project)

    assert recovery["active"] is True
    assert recovery["recovery_kind"] == "local_verification"
    assert recovery["classification_source"] == "legacy_text"
    assert recovery["target"] == "extraction_yield_floor"


def test_hash_bound_gap_resolution_reactivates_when_gap_changes(
    tmp_path: Path,
) -> None:
    project = tmp_path / "demo"
    workspace = project / "workspace"
    latest = workspace / "latest_evidence_gaps.json"
    _write_json(
        latest,
        {
            "generated_on": "2026-06-20T00:00:00Z",
            "evidence_gaps": [
                {
                    "id": "public-gap",
                    "severity": "degrading",
                    "target": "benchmark baseline",
                    "description": "Need another public comparator.",
                }
            ],
        },
    )
    write_gap_resolution(
        project_dir=project,
        gap_id="public-gap",
        reason="Comparator is out of scope for this bounded packet.",
        repo=tmp_path,
    )
    _write_json(
        latest,
        {
            "generated_on": "2026-06-20T00:00:00Z",
            "evidence_gaps": [
                {
                    "id": "public-gap",
                    "severity": "degrading",
                    "target": "benchmark baseline",
                    "description": "Need an official public comparator.",
                }
            ],
        },
    )

    payload, source_path, warnings = load_active_evidence_gaps(workspace)

    assert source_path == latest
    assert payload is not None
    assert payload["active_evidence_gap_count"] == 1
    assert payload["evidence_gaps"][0]["id"] == "public-gap"
    assert warnings == []


def test_render_evidence_gap_brief_uses_active_gap_payload_only() -> None:
    payload = {
        "generated_on": "2026-06-20T00:00:00Z",
        "judge_model": "gemini-2.5-flash",
        "evidence_gaps": [
            {
                "gap_type": "other",
                "severity": "degrading",
                "target": "active target",
                "description": "missing active evidence",
                "fetch_query": "active query",
                "recovery_kind": "public_evidence",
            },
            {
                "gap_type": "other",
                "severity": "blocking",
                "target": "blocking target",
                "description": "missing blocking evidence",
                "fetch_query": "blocking query",
                "recovery_kind": "public_evidence",
            },
            {
                "gap_type": "other",
                "severity": "blocking",
                "target": "local verifier",
                "description": "missing local verifier receipt",
                "recovery_kind": "local_verification",
            }
        ],
        "active_evidence_gap_count": 3,
        "inactive_evidence_gap_count": 2,
    }

    action = build_evidence_gap_action_contract("demo", payload)
    brief = render_evidence_gap_brief("demo", payload)

    assert action["schema"] == EVIDENCE_GAP_ACTION_SCHEMA
    assert action["active_evidence_gap_count"] == 3
    assert action["recovery_kind_counts"]["public_evidence"] == 2
    assert action["recovery_kind_counts"]["local_verification"] == 1
    assert action["next_action"]["action_type"] == "public_source_recovery"
    assert action["next_action"]["selected_gap"]["label"] == (
        "blocking:public_evidence:blocking target"
    )
    assert action["next_action"]["command"] == (
        "make evidence-fetch PROJECT=demo SEVERITY=blocking MAX_FETCHES=3 "
        "MODEL=gemini EVIDENCE_SEARCH_BACKEND=auto"
    )
    assert "active target" in brief
    assert "active query" in brief
    assert "Recovery kind: public_evidence" in brief
    assert "- Active evidence gaps: 3" in brief
    assert "- Public-source recovery gaps: 2" in brief
    assert "- Local-verification gaps: 1" in brief
    assert "## Next Action" in brief
    assert "- Selected gap: blocking:public_evidence:blocking target" in brief
    assert "- Target: blocking target" in brief
    assert "- Recovery kind: public_evidence" in brief
    assert "- Query to recover: blocking query" in brief
    assert (
        "- Boundary: public-source recovery may fetch new evidence; "
        "it does not run the autoresearch loop."
    ) in brief
    assert "- Strongest public-source severity: blocking" in brief
    assert (
        "`make evidence-fetch PROJECT=demo SEVERITY=blocking MAX_FETCHES=3 "
        "MODEL=gemini EVIDENCE_SEARCH_BACKEND=auto`"
    ) in brief
    assert "resolved" not in brief
    assert "ignored" not in brief


def test_render_no_active_evidence_gap_brief_overwrites_stale_guidance() -> None:
    action = build_evidence_gap_action_contract("demo", {"evidence_gaps": []})
    brief = render_no_active_evidence_gap_brief(
        "demo",
        warnings=[
            "champion_evidence_gaps.json contains no active evidence gaps.",
            "latest_evidence_gaps.json contains no active evidence gaps.",
        ],
    )

    assert action["schema"] == EVIDENCE_GAP_ACTION_SCHEMA
    assert action["next_action"]["action_type"] == "none"
    assert action["next_action"]["selected_gap"] is None
    assert "- Active evidence gaps: 0" in brief
    assert "Next recovery class: none" in brief
    assert "make evidence-fetch" not in brief
    assert "champion_evidence_gaps.json contains no active evidence gaps." in brief


def test_render_evidence_gap_brief_does_not_fetch_local_only_gaps() -> None:
    payload = {
        "generated_on": "2026-06-20T00:00:00Z",
        "judge_model": "grok",
        "evidence_gaps": [
            {
                "gap_type": "other",
                "severity": "blocking",
                "target": "local verifier",
                "description": "missing local verifier receipt",
                "recovery_kind": "local_verification",
            }
        ],
    }

    action = build_evidence_gap_action_contract("demo", payload)
    brief = render_evidence_gap_brief("demo", payload)

    assert action["next_action"]["action_type"] == "local_verification"
    assert action["next_action"]["command"] == (
        "ztare autoresearch trace --project demo --rubric <rubric> --brief"
    )
    assert "Next recovery class: local verification" in brief
    assert "- Selected gap: blocking:local_verification:local verifier" in brief
    assert "- Command: `ztare autoresearch trace --project demo --rubric <rubric> --brief`" in brief
    assert "local-verification gaps need a local verifier" in brief
    assert "make evidence-fetch" not in brief


def test_evidence_gap_list_cli_reports_active_contracts(
    tmp_path: Path,
    capsys,
) -> None:
    project = tmp_path / "demo"
    workspace = project / "workspace"
    _write_json(
        workspace / "latest_evidence_gaps.json",
        {
            "generated_on": "2026-06-20T00:00:00Z",
            "evidence_gaps": [
                {
                    "id": "gap-public",
                    "gap_type": "other",
                    "severity": "blocking",
                    "target": "external comparator",
                    "description": "missing public comparator",
                    "fetch_query": "official comparator",
                    "recovery_kind": "public_evidence",
                },
                {
                    "id": "gap-resolved",
                    "gap_type": "other",
                    "severity": "degrading",
                    "target": "old comparator",
                    "description": "already resolved",
                    "status": "resolved",
                },
            ],
        },
    )

    rc = evidence_gap_main(["list", "--project", str(project), "--json"])
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert rc == 0
    assert payload["schema"] == "ztare-evidence-gap-list-result-v1"
    assert payload["project"] == "demo"
    assert payload["active_evidence_gap_count"] == 1
    assert payload["evidence_gaps"][0]["id"] == "gap-public"
    assert payload["next_action"]["next_action"]["action_type"] == "public_source_recovery"
    assert payload["next_action"]["next_action"]["selected_gap"]["target"] == (
        "external comparator"
    )
