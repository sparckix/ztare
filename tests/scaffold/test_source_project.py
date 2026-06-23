from pathlib import Path

import pytest

from ztare.scaffold.source_project import init_source_project, project_dir_for


def test_source_project_init_creates_dirs_without_fake_evidence(tmp_path: Path) -> None:
    report = init_source_project(
        project="demo_sources",
        rubric="demo_sources",
        model="deepseek",
        repo=tmp_path,
    )

    assert report["ok"] is True
    assert report["project_slug"] == "demo_sources"
    assert report["created_dirs"] == [
        "projects/demo_sources",
        "projects/demo_sources/raw",
        "projects/demo_sources/workspace",
    ]
    assert (tmp_path / "projects/demo_sources/raw").is_dir()
    assert (tmp_path / "projects/demo_sources/workspace").is_dir()
    assert (tmp_path / "projects/demo_sources/raw/source_type_map.json").read_text(
        encoding="utf-8"
    ) == "{}\n"
    assert not (tmp_path / "projects/demo_sources/evidence.txt").exists()
    assert report["created_files"] == [
        "projects/demo_sources/raw/source_type_map.json",
    ]
    assert report["next_commands"] == [
        "ztare project source-check --project demo_sources --json",
        "make evidence-prepare PROJECT=demo_sources MODEL=deepseek",
        "ztare project intake create --help",
        "ztare autoresearch trace --project demo_sources --rubric demo_sources --json",
    ]
    assert any("source_type_map.json" in step for step in report["next_steps"])
    assert "does not launch autoresearch" in report["non_actions"]


def test_source_project_init_dry_run_does_not_write(tmp_path: Path) -> None:
    report = init_source_project(
        project="projects/demo_sources",
        repo=tmp_path,
        dry_run=True,
    )

    assert report["dry_run"] is True
    assert report["created_dirs"] == []
    assert report["would_create_dirs"] == [
        "projects/demo_sources",
        "projects/demo_sources/raw",
        "projects/demo_sources/workspace",
    ]
    assert report["would_create_files"] == [
        "projects/demo_sources/raw/source_type_map.json",
    ]
    assert not (tmp_path / "projects/demo_sources").exists()


def test_source_project_init_rejects_unsafe_project_paths(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        project_dir_for(tmp_path, "../escape")
    with pytest.raises(ValueError):
        project_dir_for(tmp_path, "/absolute/path")
    with pytest.raises(ValueError):
        project_dir_for(tmp_path, "bad slug")
