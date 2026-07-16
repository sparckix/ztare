from __future__ import annotations

from ztare.common.artifact_refs import (
    collect_artifact_refs,
    collect_artifact_refs_from_text,
    missing_project_artifact_refs,
    normalize_artifact_ref,
    project_artifact_ref_exists,
    project_ref_requires_resolution,
    resolve_project_artifact_ref,
    visible_workbench_authority_project,
)


def test_artifact_ref_membrane_normalizes_hash_suffix_and_resolves(tmp_path) -> None:
    path = tmp_path / "workspace" / "visible_cli_receipts" / "score.json"
    path.parent.mkdir(parents=True)
    path.write_text("{}\n", encoding="utf-8")

    ref = "workspace/visible_cli_receipts/score.json#sha=abc123"

    assert normalize_artifact_ref(ref) == "workspace/visible_cli_receipts/score.json"
    assert project_ref_requires_resolution(ref)
    assert resolve_project_artifact_ref(tmp_path, ref) == path.resolve()
    assert project_artifact_ref_exists(tmp_path, ref)
    assert missing_project_artifact_refs(tmp_path, [ref]) == ()

    typed_ref = "workspace/visible_cli_receipts/score.json:candidate_regression_receipt"
    assert normalize_artifact_ref(typed_ref) == "workspace/visible_cli_receipts/score.json"
    assert project_artifact_ref_exists(tmp_path, typed_ref)
    assert missing_project_artifact_refs(tmp_path, [typed_ref]) == ()


def test_artifact_ref_membrane_rejects_escape_and_reports_missing(tmp_path) -> None:
    assert resolve_project_artifact_ref(tmp_path, "../outside.json") is None
    assert not project_ref_requires_resolution("../outside.json")
    assert missing_project_artifact_refs(
        tmp_path,
        ["workspace/visible_cli_receipts/missing.json"],
    ) == ("workspace/visible_cli_receipts/missing.json",)


def test_collect_artifact_refs_recurses_over_receipt_payloads() -> None:
    payload = {
        "evidence_refs": ["workspace/a.json"],
        "input_hashes": {
            "receipt_refs": ["workspace/visible_cli_receipts/r.json"],
            "source_sha256": "not-a-ref",
        },
        "nested": [
            {"output_ref": "workspace/out.json"},
            {"strategy_card_sha": "not-a-path"},
        ],
    }

    assert collect_artifact_refs(payload) == (
        "workspace/a.json",
        "workspace/visible_cli_receipts/r.json",
        "workspace/out.json",
    )


def test_collect_artifact_refs_preserves_scalar_and_typed_ref_equivalence() -> None:
    scalar = {
        "evidence_refs": [
            "raw/episodes/episode_001.jsonl#transition:4",
            "workspace/visible_cli_receipts/r.json",
        ]
    }
    typed = {
        "evidence_refs": [
            {
                "ref": "raw/episodes/episode_001.jsonl#transition:4",
                "evidence_status": "used_for_abduction",
            },
            {
                "ref": "workspace/visible_cli_receipts/r.json",
                "evidence_status": "diagnostic",
            },
        ]
    }

    assert collect_artifact_refs(typed) == collect_artifact_refs(scalar)


def test_collect_artifact_refs_from_text_prefers_json_payloads() -> None:
    text = '{"control_receipts":[{"payload":{"source_ref":"workspace/candidate.py","evidence_refs":["workspace/r.json"]}}]}'

    assert collect_artifact_refs_from_text(text) == (
        "workspace/candidate.py",
        "workspace/r.json",
    )


def test_visible_workbench_authority_project_reads_manifest(tmp_path) -> None:
    repo = tmp_path / "repo"
    project = repo / "projects" / "arc3_ls20_gov"
    workbench = tmp_path / "pack"
    workbench.mkdir()
    (workbench / "MANIFEST.json").write_text(
        '{"authority_project_path": "' + str(project) + '"}\n',
        encoding="utf-8",
    )

    assert visible_workbench_authority_project(workbench, fallback=repo) == project.resolve()
