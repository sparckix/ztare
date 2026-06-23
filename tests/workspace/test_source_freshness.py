from __future__ import annotations

import hashlib
from pathlib import Path

from ztare.workspace.source_freshness import (
    SOURCE_BINDING_CONTRACT_SCHEMA,
    artifact_source_freshness,
    raw_relative_path,
    source_binding_contract_blocks_kernel,
)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_raw_relative_path_normalizes_common_source_shapes(tmp_path: Path) -> None:
    repo = tmp_path
    project = repo / "projects" / "demo"
    raw = project / "raw"
    raw.mkdir(parents=True)
    source = raw / "source.md"
    source.write_text("source", encoding="utf-8")

    assert raw_relative_path("source.md", project_dir=project, repo=repo) == "source.md"
    assert raw_relative_path("raw/source.md", project_dir=project, repo=repo) == "source.md"
    assert raw_relative_path("projects/demo/raw/source.md", project_dir=project, repo=repo) == "source.md"
    assert raw_relative_path(str(source), project_dir=project, repo=repo) == "source.md"


def test_artifact_source_freshness_detects_count_only_artifact(tmp_path: Path) -> None:
    project = tmp_path / "projects" / "demo"
    current_hash = _sha256_text("current source")
    source_preflight = {
        "sources": [
            {
                "relative_raw_path": "source.md",
                "source_type": "source_evidence",
                "sha256": current_hash,
            }
        ]
    }

    result = artifact_source_freshness(
        source_preflight=source_preflight,
        artifact_sources=[],
        artifact_name="compiled_evidence_provenance.json",
        project_dir=project,
        repo=tmp_path,
    )

    assert result["status"] == "unverified_no_artifact_sources"
    assert result["verified"] is False
    assert result["ok"] is True
    assert result["contract_ok"] is False
    assert result["kernel_entry_ok"] is False
    assert result["source_binding_contract"] == {
        "schema": SOURCE_BINDING_CONTRACT_SCHEMA,
        "artifact": "compiled_evidence_provenance.json",
        "status": "unverified_no_artifact_sources",
        "contract_ok": False,
        "kernel_entry_ok": False,
        "required": True,
        "checked": False,
        "verified": False,
        "current_source_count": 1,
        "artifact_source_count": 0,
        "blockers": ["unverified_no_artifact_sources"],
    }
    assert source_binding_contract_blocks_kernel(result) is True
    assert result["current_source_count"] == 1
    assert result["artifact_source_count"] == 0


def test_artifact_source_freshness_marks_no_current_sources_not_applicable(
    tmp_path: Path,
) -> None:
    project = tmp_path / "projects" / "demo"

    result = artifact_source_freshness(
        source_preflight={"sources": []},
        artifact_sources=[{"path": "source.md", "sha256": _sha256_text("source")}],
        artifact_name="workspace/source_index.json",
        project_dir=project,
        repo=tmp_path,
    )

    assert result["status"] == "skipped_no_current_sources"
    assert result["ok"] is True
    assert result["verified"] is False
    assert result["contract_ok"] is True
    assert result["kernel_entry_ok"] is True
    assert result["source_binding_contract"]["status"] == (
        "not_applicable_no_current_sources"
    )
    assert result["source_binding_contract"]["required"] is False
    assert source_binding_contract_blocks_kernel(result) is False


def test_artifact_source_freshness_detects_stale_hash(tmp_path: Path) -> None:
    project = tmp_path / "projects" / "demo"
    current_hash = _sha256_text("current source")
    source_preflight = {
        "sources": [
            {
                "relative_raw_path": "source.md",
                "source_type": "source_evidence",
                "sha256": current_hash,
            }
        ]
    }

    result = artifact_source_freshness(
        source_preflight=source_preflight,
        artifact_sources=[
            {
                "path": "source.md",
                "source_type": "source_evidence",
                "sha256": _sha256_text("old source"),
            }
        ],
        artifact_name="workspace/source_index.json",
        project_dir=project,
        repo=tmp_path,
    )

    assert result["status"] == "stale"
    assert result["ok"] is False
    assert result["contract_ok"] is False
    assert result["kernel_entry_ok"] is False
    assert result["source_binding_contract"]["status"] == "stale"
    assert source_binding_contract_blocks_kernel(result) is True
    assert result["hash_mismatches"] == ["source.md"]


def test_artifact_source_freshness_accepts_matching_hash(tmp_path: Path) -> None:
    project = tmp_path / "projects" / "demo"
    current_hash = _sha256_text("current source")
    source_preflight = {
        "sources": [
            {
                "relative_raw_path": "source.md",
                "source_type": "source_evidence",
                "sha256": current_hash,
            }
        ]
    }

    result = artifact_source_freshness(
        source_preflight=source_preflight,
        artifact_sources=[
            {
                "path": "source.md",
                "source_type": "source_evidence",
                "sha256": current_hash,
            }
        ],
        artifact_name="workspace/source_index.json",
        project_dir=project,
        repo=tmp_path,
    )

    assert result["status"] == "fresh"
    assert result["ok"] is True
    assert result["verified"] is True
    assert result["contract_ok"] is True
    assert result["kernel_entry_ok"] is True
    assert result["source_binding_contract"]["status"] == "verified_fresh"
    assert result["source_binding_contract"]["blockers"] == []
    assert source_binding_contract_blocks_kernel(result) is False


def test_artifact_source_freshness_accepts_artifact_relative_raw_path(
    tmp_path: Path,
) -> None:
    project = tmp_path / "projects" / "demo"
    current_hash = _sha256_text("current source")
    source_preflight = {
        "sources": [
            {
                "relative_raw_path": "source.md",
                "source_type": "source_evidence",
                "sha256": current_hash,
            }
        ]
    }

    result = artifact_source_freshness(
        source_preflight=source_preflight,
        artifact_sources=[
            {
                "relative_raw_path": "source.md",
                "source_type": "source_evidence",
                "sha256": current_hash,
            }
        ],
        artifact_name="workspace/source_index.json",
        project_dir=project,
        repo=tmp_path,
    )

    assert result["status"] == "fresh"
    assert result["ok"] is True
    assert result["verified"] is True


def test_artifact_source_freshness_detects_relative_raw_path_stale_hash(
    tmp_path: Path,
) -> None:
    project = tmp_path / "projects" / "demo"
    current_hash = _sha256_text("current source")
    source_preflight = {
        "sources": [
            {
                "relative_raw_path": "source.md",
                "source_type": "source_evidence",
                "sha256": current_hash,
            }
        ]
    }

    result = artifact_source_freshness(
        source_preflight=source_preflight,
        artifact_sources=[
            {
                "relative_raw_path": "source.md",
                "source_type": "source_evidence",
                "sha256": _sha256_text("old source"),
            }
        ],
        artifact_name="workspace/source_index.json",
        project_dir=project,
        repo=tmp_path,
    )

    assert result["status"] == "stale"
    assert result["ok"] is False
    assert result["hash_mismatches"] == ["source.md"]
