from __future__ import annotations

import json
from pathlib import Path

import pytest

from ztare.workspace import compile_evidence as ce


class _ExplodingLLMClient:
    def __init__(self, *_args, **_kwargs) -> None:
        raise AssertionError("LLM should not be constructed before source preflight passes")


def test_compile_from_raw_requires_source_evidence_before_llm(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = tmp_path / "project"
    raw_dir = project_dir / "raw"
    workspace_dir = project_dir / "workspace"
    raw_dir.mkdir(parents=True)
    (raw_dir / "notes.md").write_text("Untyped working notes.\n", encoding="utf-8")
    monkeypatch.setattr(ce, "LLMClient", _ExplodingLLMClient)

    with pytest.raises(ce.CompileEvidenceError) as exc_info:
        ce.compile_from_raw(
            project_dir=project_dir,
            raw_dir=raw_dir,
            workspace_dir=workspace_dir,
            model="gemini",
            max_files=10,
            max_chars_per_file=1000,
            max_total_chars=5000,
        )

    assert exc_info.value.phase == "source_preflight"
    assert "no source_evidence file is present" in str(exc_info.value)


def test_compile_from_raw_blocks_invalid_source_type_map_before_llm(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = tmp_path / "project"
    raw_dir = project_dir / "raw"
    workspace_dir = project_dir / "workspace"
    raw_dir.mkdir(parents=True)
    (raw_dir / "source.md").write_text("Source text.\n", encoding="utf-8")
    (raw_dir / "source_type_map.json").write_text(
        json.dumps({"source.md": "primary_fact"}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ce, "LLMClient", _ExplodingLLMClient)

    with pytest.raises(ce.CompileEvidenceError) as exc_info:
        ce.compile_from_raw(
            project_dir=project_dir,
            raw_dir=raw_dir,
            workspace_dir=workspace_dir,
            model="gemini",
            max_files=10,
            max_chars_per_file=1000,
            max_total_chars=5000,
        )

    assert exc_info.value.phase == "source_preflight"
    assert "source_type_map.json maps 'source.md' to invalid source_type 'primary_fact'" in str(
        exc_info.value
    )


def test_collect_sources_emits_compatible_source_hash_fields(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nSource text.\n",
        encoding="utf-8",
    )

    sources, warnings = ce.collect_sources(
        raw_dir=raw_dir,
        max_files=10,
        max_chars_per_file=1000,
        max_total_chars=5000,
    )

    assert warnings == []
    assert len(sources) == 1
    source_hash = ce.sha256_text("Source text.")
    assert sources[0]["sha256"] == source_hash
    assert sources[0]["full_sha256"] == source_hash
