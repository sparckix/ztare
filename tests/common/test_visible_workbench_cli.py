from __future__ import annotations

import json
import io
from pathlib import Path

import pytest

from ztare.common import visible_workbench_cli


def test_score_worldmodel_candidate_fails_closed_without_authority_project(tmp_path: Path) -> None:
    (tmp_path / "candidate.py").write_text(
        "def step(grid, action, t):\n    return grid\n",
        encoding="utf-8",
    )
    payload = visible_workbench_cli._score_worldmodel_candidate(
        project=tmp_path,
        source_ref="candidate.py",
    )

    assert payload["status"] == "fail"
    assert "authority project" in payload["output_summary"]


def test_score_worldmodel_candidate_uses_manifest_authority_project(
    monkeypatch,
    tmp_path: Path,
) -> None:
    visible = tmp_path / "visible"
    visible.mkdir()
    authority = tmp_path / "projects" / "demo"
    authority.mkdir(parents=True)
    (authority / "gate_harness.py").write_text("# gate\n", encoding="utf-8")
    (visible / "MANIFEST.json").write_text(
        json.dumps(
            {
                "schema": "ztare-visible-agent-workbench-v1",
                "authority_project_path": str(authority),
            }
        )
        + "\n",
        encoding="utf-8",
    )

    seen: dict[str, Path] = {}

    def fake_preflight(*, enabled, project_dir, candidate_path, **_kwargs):
        seen["project_dir"] = Path(project_dir)
        seen["candidate_path"] = Path(candidate_path)
        assert enabled is True
        return None

    monkeypatch.setattr(
        "ztare.validator.core.pre_judge_gate.detect_patch_base_regression_preflight",
        fake_preflight,
    )
    monkeypatch.setattr(
        visible_workbench_cli.sys,
        "stdin",
        io.StringIO("def step(grid, action, t):\n    return grid\n"),
    )

    payload = visible_workbench_cli._score_worldmodel_candidate(
        project=visible,
        source_ref="-",
    )

    assert payload["status"] == "ok"
    assert seen["project_dir"] == authority
    assert seen["candidate_path"].name.endswith(".py")
    assert not seen["candidate_path"].is_relative_to(visible)
    summary = json.loads(payload["receipt"]["payload"]["output_summary"])
    assert summary["candidate_relation"] == "no_regression_detected"


def test_lowerability_blocker_with_tool_claims_requires_receipt_refs(
    tmp_path: Path,
) -> None:
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(
        json.dumps(
            {
                "control_receipts": [
                    {
                        "type": "LOWERABILITY_BLOCKED",
                        "payload": {
                            "visible_capabilities_attempted": [
                                "check-worldmodel-carrier:candidate.py",
                                "score-worldmodel-candidate:candidate.py",
                            ],
                            "candidate_family_attempted": "candidate_delta",
                            "obstruction": "candidate regressed",
                            "missing_witness_or_sensor": "selector",
                            "next_action": "stop",
                            "evidence_refs": ["candidate.py"],
                        },
                    }
                ],
                "thesis_markdown": "blocked",
                "test_model_py": "",
            }
        ),
        encoding="utf-8",
    )

    receipt = visible_workbench_cli._check_receipt(
        project=tmp_path,
        source_ref="payload.json",
        kind="worldmodel-payload",
    )

    assert receipt["status"] == "fail"
    assert "malformed_lowerability_blocked" in receipt["error_classes"]
    assert "self-attested" in receipt["output_summary"]


def test_lowerability_blocker_rejects_source_fiber_evidence_ref(tmp_path: Path) -> None:
    (tmp_path / "MANIFEST.json").write_text(
        json.dumps(
            {
                "visible_artifacts": [
                    {
                        "ref": "src/ztare/worldmodel/spec_abduction.py",
                        "authority_level": "visible_diagnostic_tool_source",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(
        json.dumps(
            {
                "control_receipts": [
                    {
                        "type": "LOWERABILITY_BLOCKED",
                        "payload": {
                            "visible_capabilities_attempted": [
                                "inspect_worldmodel_counterexample_context",
                                "mine_worldmodel_lowerable_selectors",
                                "mine_worldmodel_separating_features",
                                "cell_local_lowerable_carrier_selector_miner",
                                "mine_worldmodel_global_carrier_selectors_from_observable_context",
                            ],
                            "candidate_family_attempted": "candidate_delta",
                            "obstruction": "no lowerable witness",
                            "missing_witness_or_sensor": "abducer extension",
                            "next_action": "cold_meta_backlog",
                            "evidence_refs": ["src/ztare/worldmodel/spec_abduction.py"],
                        },
                    }
                ],
                "thesis_markdown": "blocked",
                "test_model_py": "",
            }
        ),
        encoding="utf-8",
    )

    receipt = visible_workbench_cli._check_receipt(
        project=tmp_path,
        source_ref="payload.json",
        kind="worldmodel-payload",
    )

    assert receipt["status"] == "fail"
    assert "malformed_lowerability_blocked" in receipt["error_classes"]
    assert "source-fiber files" in receipt["output_summary"]


def test_lowerability_blocker_requires_receipt_for_visible_tool_attempt(tmp_path: Path) -> None:
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(
        json.dumps(
            {
                "control_receipts": [
                    {
                        "type": "LOWERABILITY_BLOCKED",
                        "payload": {
                            "visible_capabilities_attempted": [
                                "inspect_worldmodel_counterexample_context",
                                "mine_worldmodel_lowerable_selectors",
                                "mine_worldmodel_separating_features",
                                "cell_local_lowerable_carrier_selector_miner",
                                "mine_worldmodel_global_carrier_selectors_from_observable_context",
                            ],
                            "candidate_family_attempted": "candidate_delta",
                            "obstruction": "no lowerable witness",
                            "missing_witness_or_sensor": "selector",
                            "next_action": "cold_meta_backlog",
                            "evidence_refs": ["workspace/abduced_core.json"],
                        },
                    }
                ],
                "thesis_markdown": "blocked",
                "test_model_py": "",
            }
        ),
        encoding="utf-8",
    )

    receipt = visible_workbench_cli._check_receipt(
        project=tmp_path,
        source_ref="payload.json",
        kind="worldmodel-payload",
    )

    assert receipt["status"] == "fail"
    assert "self-attested" in receipt["output_summary"]


def test_lowerability_blocker_allows_receipted_visible_tool_attempt(tmp_path: Path) -> None:
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(
        json.dumps(
            {
                "control_receipts": [
                    {
                        "type": "LOWERABILITY_BLOCKED",
                        "payload": {
                            "visible_capabilities_attempted": [
                                "mine_worldmodel_lowerable_selectors",
                            ],
                            "candidate_family_attempted": "candidate_delta",
                            "obstruction": "no lowerable witness",
                            "missing_witness_or_sensor": "selector",
                            "next_action": "cold_meta_backlog",
                            "evidence_refs": [
                                "workspace/abduced_core.json",
                                "workspace/visible_cli_receipts/mine_selectors.json",
                            ],
                        },
                    }
                ],
                "thesis_markdown": "blocked",
                "test_model_py": "",
            }
        ),
        encoding="utf-8",
    )

    receipt = visible_workbench_cli._check_receipt(
        project=tmp_path,
        source_ref="payload.json",
        kind="worldmodel-payload",
    )

    assert receipt["status"] == "pass"


def test_rank_next_morphisms_is_optional_frontier_after_candidate_feedback(
    tmp_path: Path,
) -> None:
    (tmp_path / "workspace").mkdir()
    (tmp_path / "workspace" / "latest_information_yield.json").write_text(
        json.dumps({"decision": {"action": "CONTINUE"}}),
        encoding="utf-8",
    )
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(
        json.dumps(
            {
                "control_receipts": [
                    {
                        "type": "LOWERABILITY_BLOCKED",
                        "payload": {
                            "visible_capabilities_attempted": [
                                "score-worldmodel-candidate:candidate.py",
                            ],
                            "candidate_family_attempted": "candidate_delta",
                        },
                    }
                ],
                "thesis_markdown": "blocked",
                "test_model_py": "",
            }
        ),
        encoding="utf-8",
    )

    ranked = visible_workbench_cli._rank_next_morphisms(
        project=tmp_path,
        source_ref="payload.json",
    )

    assert ranked["status"] == "ok"
    assert ranked["frontier_state"] == "optional_frontier_available"
    assert ranked["ranked_morphisms"]
    assert "optional" in ranked["output_summary"]
    assert ranked["loop_information_yield"]["decision"]["action"] == "CONTINUE"


def test_visible_cli_persists_receipt_ref_for_leaf_local_composition(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(
        json.dumps(
            {
                "control_receipts": [
                    {
                        "type": "LOWERABILITY_BLOCKED",
                        "payload": {
                            "visible_capabilities_attempted": [
                                "inspect_worldmodel_counterexample_context",
                                "mine_worldmodel_lowerable_selectors",
                                "mine_worldmodel_separating_features",
                                "cell_local_lowerable_carrier_selector_miner",
                                "mine_worldmodel_global_carrier_selectors_from_observable_context",
                            ],
                            "candidate_family_attempted": "candidate_delta",
                            "obstruction": "no lowerable witness",
                            "missing_witness_or_sensor": "selector",
                            "next_action": "cold_meta_backlog",
                            "evidence_refs": [
                                "workspace/abduced_core.json",
                                "workspace/visible_cli_receipts/frontier.json",
                            ],
                        },
                    }
                ],
                "thesis_markdown": "blocked",
                "test_model_py": "",
            }
        ),
        encoding="utf-8",
    )

    rc = visible_workbench_cli.main(
        [
            "--project-dir",
            str(tmp_path),
            "check-receipt",
            "--kind",
            "worldmodel-payload",
            "--source",
            "payload.json",
        ]
    )

    assert rc == 0
    stdout = capsys.readouterr().out
    payload = json.loads(stdout)
    ref = payload["persistent_receipt"]["ref"]
    assert ref.startswith("workspace/visible_cli_receipts/")
    assert (tmp_path / ref).is_file()


def test_visible_cli_persistent_receipt_binds_nested_leaf_receipt(tmp_path: Path) -> None:
    payload = {
        "schema": "ztare-visible-workbench-cli-v1",
        "status": "ok",
        "command": "run-action",
        "receipt": {
            "type": "LEAF_WORKBENCH_RECEIPT",
            "payload": {
                "capability_id": "mine_worldmodel_lowerable_selectors",
                "input_hashes": {"latest_regression_ref": "workspace/score.json"},
                "output_summary": "diagnostic result",
                "claim_bindings": ["visible local action"],
            },
        },
    }

    visible_workbench_cli._attach_persistent_receipt(project=tmp_path, payload=payload)

    persistent = payload["persistent_receipt"]
    nested = payload["receipt"]["payload"]
    assert nested["input_hashes"]["receipt_ref"] == persistent["ref"]
    assert nested["input_hashes"]["receipt_sha256"] == persistent["sha256"]
    assert nested["output_ref"] == persistent["ref"]
    assert nested["output_sha256"] == persistent["sha256"]


def test_visible_cli_activity_meter_classifies_receipt(tmp_path: Path) -> None:
    payload = {
        "schema": "ztare-visible-workbench-cli-v1",
        "status": "ok",
        "command": "check-receipt",
        "capability_id": "check_receipt_compatibility",
        "output_summary": "receipt compatibility passed",
    }
    visible_workbench_cli._attach_persistent_receipt(project=tmp_path, payload=payload)
    meter = payload["activity_meter"]["activity_classes"]
    assert meter["preflight_repair"] == 1
    assert meter["probe_query"] == 0
