from __future__ import annotations

import json
from pathlib import Path

from ztare.scaffold.substrate_queue import (
    build_project_packet,
    build_project_packet_from_compiled,
    validate_project_packet,
    validate_project_packet_falsifier,
    write_project_packet,
)


def test_packet_falsifier_resolves_repo_relative_refs_against_supplied_repo_root(
    tmp_path: Path,
) -> None:
    project = tmp_path / "projects" / "demo"
    project.mkdir(parents=True)
    source = project / "raw" / "source.md"
    evidence = project / "workspace" / "control_followup_policy.jsonl"
    source.parent.mkdir(parents=True)
    evidence.parent.mkdir(parents=True)
    source.write_text("---\nsource_type: source_evidence\n---\nsource\n", encoding="utf-8")
    evidence.write_text('{"record_type":"control_followup_policy_decision"}\n', encoding="utf-8")
    packet_path = project / "control_demo_packet.json"
    write_project_packet(
        packet_path,
        build_project_packet(
            project="demo",
            rubric="demo",
            task="validate repo-root packet refs",
            bounded_claim="repo-relative packet refs are resolved against the supplied root",
            source_refs=["projects/demo/raw/source.md"],
            evidence_refs=["projects/demo/workspace/control_followup_policy.jsonl"],
            non_claims=["not a live run"],
            next_falsifier="remove the evidence ref and validation must fail",
            expected_command=(
                "ztare autoresearch route --task 'validate repo-root packet refs' "
                "--project demo --rubric demo"
            ),
        ),
    )

    result = validate_project_packet_falsifier(
        packet_path,
        remove_ref="evidence_refs[1]",
        repo_root=tmp_path,
    )

    assert result["ok"] is True
    assert result["baseline"]["ok"] is True
    assert result["expected_error_fragment"] == "evidence_refs[1] local path does not exist"


def test_project_packet_from_compiled_maps_source_ids_to_raw_refs(
    tmp_path: Path,
) -> None:
    project = tmp_path / "projects" / "demo"
    raw = project / "raw"
    raw.mkdir(parents=True)
    (raw / "a.md").write_text("source a\n", encoding="utf-8")
    (raw / "b.md").write_text("source b\n", encoding="utf-8")
    compiled = project / "compiled_evidence_packet.json"
    compiled.write_text(
        json.dumps(
            {
                "candidate_claims_to_test": [
                    {
                        "claim": "candidate one",
                        "priority": "high",
                        "source_ids": ["S002"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (project / "compiled_evidence.txt").write_text("compiled text\n", encoding="utf-8")
    provenance = project / "compiled_evidence_provenance.json"
    provenance.write_text(
        json.dumps(
            {
                "raw_dir": str(raw),
                "sources": [
                    {"source_id": "S001", "path": "a.md"},
                    {"source_id": "S002", "path": "b.md"},
                ],
            }
        ),
        encoding="utf-8",
    )
    packet_path = project / "demo_packet.json"

    packet = build_project_packet_from_compiled(
        project="demo",
        rubric="demo",
        output_path=packet_path,
        compiled_path=compiled,
        provenance_path=provenance,
        repo_root=tmp_path,
    )
    validation = validate_project_packet(
        packet,
        base_dir=packet_path.parent,
        repo_root=tmp_path,
        require_source_preflight=False,
    )

    assert packet["bounded_claim"] == "candidate one"
    assert packet["source_refs"] == ["projects/demo/raw/b.md"]
    assert packet["evidence_refs"] == [
        "projects/demo/compiled_evidence_packet.json",
        "projects/demo/compiled_evidence.txt",
        "projects/demo/compiled_evidence_provenance.json",
    ]
    assert packet["draft_source"]["candidate_source_ids"] == ["S002"]
    assert packet["draft_source"]["missing_source_refs"] == []
    assert validation["ok"] is True


def test_project_packet_from_compiled_keeps_moved_source_missing_by_default(
    tmp_path: Path,
) -> None:
    project = tmp_path / "projects" / "demo"
    raw = project / "raw"
    (raw / "folder").mkdir(parents=True)
    (raw / "folder" / "source.md").write_text("source\n", encoding="utf-8")
    compiled = project / "compiled_evidence_packet.json"
    compiled.write_text(
        json.dumps(
            {
                "candidate_claims_to_test": [
                    {
                        "claim": "candidate one",
                        "priority": "high",
                        "source_ids": ["S001"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    provenance = project / "compiled_evidence_provenance.json"
    provenance.write_text(
        json.dumps(
            {
                "raw_dir": str(raw),
                "sources": [
                    {"source_id": "S001", "path": "folder/public/source.md"},
                ],
            }
        ),
        encoding="utf-8",
    )
    packet_path = project / "demo_packet.json"

    packet = build_project_packet_from_compiled(
        project="demo",
        rubric="demo",
        output_path=packet_path,
        compiled_path=compiled,
        provenance_path=provenance,
        repo_root=tmp_path,
    )
    validation = validate_project_packet(
        packet,
        base_dir=packet_path.parent,
        repo_root=tmp_path,
        require_source_preflight=False,
    )

    assert packet["source_refs"] == ["projects/demo/raw/folder/public/source.md"]
    assert packet["draft_source"]["missing_source_refs"] == [
        "projects/demo/raw/folder/public/source.md"
    ]
    assert packet["draft_source"]["source_ref_repairs"] == []
    assert validation["ok"] is False


def test_project_packet_from_compiled_records_explicit_moved_source_repair(
    tmp_path: Path,
) -> None:
    project = tmp_path / "projects" / "demo"
    raw = project / "raw"
    (raw / "folder").mkdir(parents=True)
    (raw / "folder" / "source.md").write_text("source\n", encoding="utf-8")
    compiled = project / "compiled_evidence_packet.json"
    compiled.write_text(
        json.dumps(
            {
                "candidate_claims_to_test": [
                    {
                        "claim": "candidate one",
                        "priority": "high",
                        "source_ids": ["S001"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    provenance = project / "compiled_evidence_provenance.json"
    provenance.write_text(
        json.dumps(
            {
                "raw_dir": str(raw),
                "sources": [
                    {"source_id": "S001", "path": "folder/public/source.md"},
                ],
            }
        ),
        encoding="utf-8",
    )
    packet_path = project / "demo_packet.json"

    packet = build_project_packet_from_compiled(
        project="demo",
        rubric="demo",
        output_path=packet_path,
        compiled_path=compiled,
        provenance_path=provenance,
        repo_root=tmp_path,
        repair_moved_sources=True,
    )
    validation = validate_project_packet(
        packet,
        base_dir=packet_path.parent,
        repo_root=tmp_path,
        require_source_preflight=False,
    )

    assert packet["source_refs"] == ["projects/demo/raw/folder/source.md"]
    assert packet["draft_source"]["missing_source_refs"] == []
    assert packet["draft_source"]["source_ref_repairs"] == [
        {
            "source_id": "S001",
            "from_ref": "projects/demo/raw/folder/public/source.md",
            "to_ref": "projects/demo/raw/folder/source.md",
            "method": "drop_one_raw_path_segment",
        }
    ]
    assert packet["draft_source"]["repair_moved_sources"] is True
    assert "not evidence that compiled evidence was refreshed after raw source moves" in packet["non_claims"]
    assert validation["ok"] is True
