"""Contract tests for project-local LeanMill areas and scaffolding.

LeanMill work lives under the canonical autoresearch project tree
(projects/<slug>/leanmill), distinct from the curated example formalizations
under ztare_proofs/leanmill-formalizations. These tests pin that behavior at the
shared-module level rather than through the HTTP server.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ztare.leanmill.workbench_target import (
    leanmill_folder_contract,
    list_project_leanmill_areas,
    scaffold_project_leanmill_area,
)
from ztare.workspace.server_payloads.leanmill import project_areas_payload, scaffold_payload


def _project(repo: Path, slug: str) -> Path:
    project = repo / "projects" / slug
    project.mkdir(parents=True)
    return project


def test_list_areas_is_empty_without_leanmill_folders(tmp_path: Path) -> None:
    _project(tmp_path, "alpha")
    assert list_project_leanmill_areas(tmp_path) == []


def test_scaffold_creates_folder_contract_and_is_idempotent(tmp_path: Path) -> None:
    _project(tmp_path, "alpha")
    first = scaffold_project_leanmill_area("alpha", repo=tmp_path)
    assert first["already_existed"] is False
    contract = leanmill_folder_contract("alpha")
    for key in ("targets", "lean", "notes", "history"):
        assert (tmp_path / contract[key]).is_dir()
    assert (tmp_path / contract["readme"]).is_file()

    second = scaffold_project_leanmill_area("alpha", repo=tmp_path)
    assert second["already_existed"] is True
    assert second["created_paths"] == []


def test_scaffold_rejects_unknown_project(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        scaffold_project_leanmill_area("ghost", repo=tmp_path)


def test_list_areas_summarizes_targets_and_jobs(tmp_path: Path) -> None:
    _project(tmp_path, "alpha")
    scaffold_project_leanmill_area("alpha", repo=tmp_path)
    (tmp_path / "projects/alpha/leanmill/targets/t1_target.md").write_text("# t1\n", encoding="utf-8")
    (tmp_path / "projects/alpha/leanmill/jobs").mkdir()
    (tmp_path / "projects/alpha/leanmill/jobs/j1_result.json").write_text("{}\n", encoding="utf-8")
    areas = list_project_leanmill_areas(tmp_path)
    assert len(areas) == 1
    area = areas[0]
    assert area["project"] == "alpha"
    assert area["target_count"] == 1
    assert area["job_count"] == 1
    assert area["latest_activity"]


def test_project_areas_payload_separates_user_work_from_examples(tmp_path: Path) -> None:
    _project(tmp_path, "alpha")
    scaffold_project_leanmill_area("alpha", repo=tmp_path)
    payload = project_areas_payload(tmp_path, storage=None)
    assert payload["kind"] == "user_projects"
    assert payload["count"] == 1
    assert payload["areas"][0]["project"] == "alpha"


def test_scaffold_payload_previews_then_accepts(tmp_path: Path) -> None:
    _project(tmp_path, "alpha")
    preview = scaffold_payload({"project": "alpha", "confirmed": False}, repo=tmp_path, storage=None)
    assert preview["status"] == "needs_confirmation"
    assert preview["accepted"] is False

    confirmed = scaffold_payload({"project": "alpha", "confirmed": True}, repo=tmp_path, storage=None)
    assert confirmed["accepted"] is True
    assert confirmed["status"] == "scaffolded"
