import hashlib
import json
from pathlib import Path

from ztare.scaffold.source_check import check_evidence_project, check_source_project, main


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


def test_evidence_admission_selects_transition_carrier_and_ignores_scratch(
    tmp_path: Path,
) -> None:
    episodes = tmp_path / "projects/demo/raw/episodes"
    episodes.mkdir(parents=True)
    episode = episodes / "episode_001.jsonl"
    # A three-dimensional observation proves the carrier does not assume a 2-D grid.
    episode.write_text(
        json.dumps({"t": 0, "s": [[[1]]], "a": {"axis": 2}, "s_next": [[[2]]]})
        + "\n",
        encoding="utf-8",
    )
    digest = hashlib.sha256(episode.read_bytes()).hexdigest()
    (episodes / "episode_001.identity.json").write_text(
        json.dumps(
            {
                "schema": "ztare-episode-identity-sidecar-v1",
                "episode_sha256": digest,
                "bindings": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    scratch = episodes / "eval_slices"
    scratch.mkdir()
    (scratch / "eval_bad.jsonl").write_text("not-json\n", encoding="utf-8")

    report = check_evidence_project(
        project="demo",
        repo=tmp_path,
        rubric={"substrate_class": "interactive_environment"},
    )

    assert report["ok"] is True
    assert report["carrier_kind"] == "transition_stream"
    assert report["requires_source_index"] is False
    assert report["requires_compiled_evidence"] is False
    assert report["source_count"] == 1
    assert report["sources"][0]["identity_status"] == "bound"
    assert report["sources"][0]["first_transition"] == {
        "t": 0,
        "action_kind": "dict",
        "state_kind": "list",
    }


def test_transition_carrier_blocks_a_sidecar_bound_to_other_bytes(tmp_path: Path) -> None:
    episodes = tmp_path / "projects/demo/raw/episodes"
    episodes.mkdir(parents=True)
    episode = episodes / "episode_001.jsonl"
    episode.write_text(
        json.dumps({"t": 0, "s": [1], "a": 0, "s_next": [2]}) + "\n",
        encoding="utf-8",
    )
    (episodes / "episode_001.identity.json").write_text(
        json.dumps(
            {
                "schema": "ztare-episode-identity-sidecar-v1",
                "episode_sha256": "0" * 64,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    report = check_evidence_project(
        project="demo",
        repo=tmp_path,
        rubric={"evidence_carrier_kind": "transition_stream"},
    )

    assert report["ok"] is False
    assert report["sources"][0]["identity_status"] == "stale"
    assert report["blocking"] == [
        "projects/demo/raw/episodes/episode_001.identity.json does not bind the episode bytes"
    ]
