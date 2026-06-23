import hashlib
import json
from pathlib import Path

from ztare.scaffold.source_check import check_source_project, main


def test_source_check_reports_ready_typed_sources(tmp_path: Path) -> None:
    raw = tmp_path / "projects/demo/raw"
    raw.mkdir(parents=True)
    (raw / "source.md").write_text("Primary source text.\n", encoding="utf-8")
    (raw / "source_type_map.json").write_text(
        json.dumps({"source.md": "source_evidence"}) + "\n",
        encoding="utf-8",
    )

    report = check_source_project(project="demo", repo=tmp_path)

    assert report["ok"] is True
    assert report["status"] == "ready_for_evidence_prepare"
    assert report["source_count"] == 1
    assert report["source_evidence_count"] == 1
    assert report["sources"][0]["source_type"] == "source_evidence"
    assert report["sources"][0]["source_type_source"] == "source_type_map.json"
    assert report["sources"][0]["sha256"] == hashlib.sha256(
        "Primary source text.".encode("utf-8")
    ).hexdigest()
    assert report["next_steps"] == [
        "Compile the source/evidence chain before routing into the loop.",
    ]
    assert report["next_commands"] == ["make evidence-prepare PROJECT=demo MODEL=gemini"]
    assert "does not call an LLM" in report["non_actions"]


def test_source_check_json_cli_emits_hashed_report(tmp_path: Path, capsys) -> None:
    raw = tmp_path / "projects/demo/raw"
    raw.mkdir(parents=True)
    (raw / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nPrimary source text.\n",
        encoding="utf-8",
    )

    rc = main(["--project", "demo", "--repo", str(tmp_path), "--json"])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["sources"][0]["sha256"] == hashlib.sha256(
        "Primary source text.".encode("utf-8")
    ).hexdigest()


def test_source_check_blocks_missing_raw_sources(tmp_path: Path) -> None:
    report = check_source_project(project="demo", repo=tmp_path)

    assert report["ok"] is False
    assert report["status"] == "blocked"
    assert "project directory is missing" in report["blocking"]
    assert "raw source directory is missing" in report["blocking"]
    assert report["next_commands"] == ["ztare project source-init --project demo"]


def test_source_check_blocks_empty_initialized_surface_with_next_step(tmp_path: Path) -> None:
    raw = tmp_path / "projects/demo/raw"
    raw.mkdir(parents=True)
    (raw / "source_type_map.json").write_text("{}\n", encoding="utf-8")

    report = check_source_project(project="demo", repo=tmp_path)

    assert report["ok"] is False
    assert "no supported text-like source files found under raw" in report["blocking"]
    assert report["next_steps"] == ["Put text-like source files under projects/demo/raw."]
    assert report["next_commands"] == []


def test_source_check_blocks_when_no_source_evidence_is_present(tmp_path: Path) -> None:
    raw = tmp_path / "projects/demo/raw"
    raw.mkdir(parents=True)
    (raw / "source.txt").write_text("Untyped source text.\n", encoding="utf-8")
    (raw / "artifact.pdf").write_bytes(b"%PDF-1.4")

    report = check_source_project(project="demo", repo=tmp_path)

    assert report["ok"] is False
    assert report["source_count"] == 1
    assert report["untyped_source_count"] == 1
    assert report["unsupported_file_count"] == 1
    assert "no source_evidence file is present" in report["blocking"]
    assert any("untyped sources" in warning for warning in report["warnings"])
    assert any("unsupported non-text" in warning for warning in report["warnings"])
    assert any("at least one raw source as source_evidence" in step for step in report["next_steps"])
    assert any("Type untyped sources" in step for step in report["next_steps"])
    assert report["next_commands"] == []


def test_source_check_allows_typed_evidence_with_extra_untyped_sources(tmp_path: Path) -> None:
    raw = tmp_path / "projects/demo/raw"
    raw.mkdir(parents=True)
    (raw / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nPrimary source text.\n",
        encoding="utf-8",
    )
    (raw / "notes.txt").write_text("Untyped working note.\n", encoding="utf-8")
    (raw / "artifact.pdf").write_bytes(b"%PDF-1.4")

    report = check_source_project(project="demo", repo=tmp_path)

    assert report["ok"] is True
    assert report["source_count"] == 2
    assert report["source_evidence_count"] == 1
    assert report["untyped_source_count"] == 1
    assert report["unsupported_file_count"] == 1
    assert "no source_evidence file is present" not in report["blocking"]
    assert any("untyped sources" in warning for warning in report["warnings"])
    assert any("unsupported non-text" in warning for warning in report["warnings"])
    assert report["next_commands"] == ["make evidence-prepare PROJECT=demo MODEL=gemini"]


def test_source_check_blocks_invalid_source_type_declarations(tmp_path: Path) -> None:
    raw = tmp_path / "projects/demo/raw"
    raw.mkdir(parents=True)
    (raw / "source.md").write_text(
        "---\nsource_type: primary_fact\n---\nSource text.\n",
        encoding="utf-8",
    )

    report = check_source_project(project="demo", repo=tmp_path)

    assert report["ok"] is False
    assert "one or more sources declare an invalid source_type" in report["blocking"]
    assert report["sources"][0]["invalid_source_type_declaration"] is True


def test_source_check_blocks_invalid_source_type_map_values(tmp_path: Path) -> None:
    raw = tmp_path / "projects/demo/raw"
    raw.mkdir(parents=True)
    (raw / "source.md").write_text("Source text.\n", encoding="utf-8")
    (raw / "source_type_map.json").write_text(
        json.dumps({"source.md": "primary_fact"}) + "\n",
        encoding="utf-8",
    )

    report = check_source_project(project="demo", repo=tmp_path)

    assert report["ok"] is False
    assert "source_type_map.json has invalid entries" in report["blocking"]
    assert any("primary_fact" in warning for warning in report["warnings"])
