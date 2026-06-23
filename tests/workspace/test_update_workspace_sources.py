import hashlib
import json
from pathlib import Path

from ztare.workspace import compile_evidence as compile_module
from ztare.workspace import update_workspace as update_module
from ztare.workspace.update_workspace import collect_raw_sources, checkpoint_source_index


def test_workspace_update_excludes_source_type_map_and_applies_overrides(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "source.md").write_text("Primary source text.\n", encoding="utf-8")
    (raw / "source_type_map.json").write_text(
        json.dumps({"source.md": "source_evidence"}) + "\n",
        encoding="utf-8",
    )

    sources, warnings = collect_raw_sources(
        raw_dir=raw,
        max_files=10,
        max_chars_per_file=1000,
        max_total_chars=5000,
    )

    assert [source["path"] for source in sources] == ["source.md"]
    assert sources[0]["source_type"] == "source_evidence"
    assert not any("source_type_map.json" in warning for warning in warnings)


def test_workspace_update_supports_relative_source_type_map_keys(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    nested = raw / "sources"
    nested.mkdir(parents=True)
    (nested / "brief.txt").write_text("Research question text.\n", encoding="utf-8")
    (raw / "source_type_map.json").write_text(
        json.dumps({"sources/brief.txt": "research_question"}) + "\n",
        encoding="utf-8",
    )

    sources, warnings = collect_raw_sources(
        raw_dir=raw,
        max_files=10,
        max_chars_per_file=1000,
        max_total_chars=5000,
    )

    assert [source["path"] for source in sources] == ["sources/brief.txt"]
    assert sources[0]["source_type"] == "research_question"
    assert not warnings


def test_workspace_update_warns_on_invalid_source_type_map_values(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "source.md").write_text("Source text.\n", encoding="utf-8")
    (raw / "source_type_map.json").write_text(
        json.dumps({"source.md": "primary_fact"}) + "\n",
        encoding="utf-8",
    )

    sources, warnings = collect_raw_sources(
        raw_dir=raw,
        max_files=10,
        max_chars_per_file=1000,
        max_total_chars=5000,
    )

    assert [source["path"] for source in sources] == ["source.md"]
    assert sources[0]["source_type"] == "untyped"
    assert "source_type_map.json maps 'source.md' to invalid source_type 'primary_fact'" in warnings


def test_workspace_index_only_writes_source_index_without_snapshot(tmp_path: Path) -> None:
    project = tmp_path / "projects" / "demo"
    raw = project / "raw"
    workspace = project / "workspace"
    raw.mkdir(parents=True)
    (raw / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nPrimary source text.\n",
        encoding="utf-8",
    )

    report = checkpoint_source_index(
        project_dir=project,
        raw_dir=raw,
        workspace_dir=workspace,
        model_family="gemini",
        max_files=10,
        max_chars_per_file=1000,
        max_total_chars=5000,
    )

    assert report["llm_calls"] is False
    assert report["merge_status"] == "index_only"
    assert report["source_count"] == 1
    assert report["source_index_receipt"] == str(workspace / "source_index_receipt.json")
    source_index = json.loads((workspace / "source_index.json").read_text(encoding="utf-8"))
    workspace_meta = json.loads((workspace / "workspace_meta.json").read_text(encoding="utf-8"))
    receipt = json.loads((workspace / "source_index_receipt.json").read_text(encoding="utf-8"))
    assert source_index["sources"][0]["path"] == "source.md"
    assert source_index["sources"][0]["source_type"] == "source_evidence"
    assert workspace_meta["merge_status"] == "index_only"
    assert workspace_meta["source_count"] == 1
    assert receipt["schema"] == "ztare-source-index-receipt-v1"
    assert receipt["status"] == "indexed"
    assert receipt["llm_calls"] is False
    assert receipt["source_count"] == 1
    assert receipt["source_index_sha256"] == hashlib.sha256(
        (workspace / "source_index.json").read_bytes()
    ).hexdigest()
    assert receipt["workspace_meta"] == str(workspace / "workspace_meta.json")
    assert "workspace_meta_sha256" not in receipt
    assert receipt["sources"] == [
        {
            "path": "source.md",
            "source_type": "source_evidence",
            "sha256": hashlib.sha256("Primary source text.".encode("utf-8")).hexdigest(),
            "chars_used": len("Primary source text."),
            "truncated": False,
        }
    ]
    assert not (workspace / "workspace_snapshot.json").exists()


def test_workspace_index_only_uses_repo_relative_public_paths(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(compile_module, "REPO_ROOT", tmp_path)
    prompt_dir = tmp_path / "config" / "prompts"
    monkeypatch.setattr(update_module, "PROMPTS_DIR", prompt_dir)
    project = tmp_path / "projects" / "demo"
    raw = project / "raw"
    workspace = project / "workspace"
    raw.mkdir(parents=True)
    (raw / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nPrimary source text.\n",
        encoding="utf-8",
    )

    checkpoint_source_index(
        project_dir=project,
        raw_dir=raw,
        workspace_dir=workspace,
        model_family="gemini",
        max_files=10,
        max_chars_per_file=1000,
        max_total_chars=5000,
    )

    workspace_meta = json.loads((workspace / "workspace_meta.json").read_text(encoding="utf-8"))
    receipt = json.loads((workspace / "source_index_receipt.json").read_text(encoding="utf-8"))
    assert workspace_meta["raw_dir"] == "projects/demo/raw"
    assert workspace_meta["workspace_dir"] == "projects/demo/workspace"
    assert workspace_meta["prompts"]["extract_source_note"] == "config/prompts/extract_source_note.md"
    assert receipt["source_index"] == "projects/demo/workspace/source_index.json"
    assert receipt["workspace_meta"] == "projects/demo/workspace/workspace_meta.json"


def test_workspace_index_only_covers_sources_after_content_budget(tmp_path: Path) -> None:
    project = tmp_path / "projects" / "demo"
    raw = project / "raw"
    workspace = project / "workspace"
    raw.mkdir(parents=True)
    (raw / "a.md").write_text(
        "---\nsource_type: source_evidence\n---\n" + "a" * 40,
        encoding="utf-8",
    )
    (raw / "b.md").write_text(
        "---\nsource_type: source_evidence\n---\n" + "b" * 40,
        encoding="utf-8",
    )
    (raw / "c.md").write_text(
        "---\nsource_type: source_evidence\n---\n" + "c" * 40,
        encoding="utf-8",
    )

    report = checkpoint_source_index(
        project_dir=project,
        raw_dir=raw,
        workspace_dir=workspace,
        model_family="gemini",
        max_files=10,
        max_chars_per_file=20,
        max_total_chars=40,
    )

    source_index = json.loads((workspace / "source_index.json").read_text(encoding="utf-8"))
    receipt = json.loads((workspace / "source_index_receipt.json").read_text(encoding="utf-8"))
    assert report["source_count"] == 3
    assert [source["path"] for source in source_index["sources"]] == [
        "a.md",
        "b.md",
        "c.md",
    ]
    assert [source["path"] for source in receipt["sources"]] == [
        "a.md",
        "b.md",
        "c.md",
    ]
    assert receipt["sources"][2]["chars_used"] == 0
    assert receipt["sources"][2]["truncated"] is True
    assert "Stopped ingest because max_total_chars budget was reached." in report["warnings"]
