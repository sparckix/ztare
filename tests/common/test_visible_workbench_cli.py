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


def test_visible_cli_compiles_active_task_into_action_scope(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source = "def step(grid, action, t):\n    return grid\n"
    (tmp_path / "test_model.py").write_text(source, encoding="utf-8")
    import hashlib

    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    (workspace / "latest_harness_weakness.json").write_text(
        json.dumps(
            {
                "active_frontier": {
                    "candidate_sha": digest,
                    "source_ref": "test_model.py",
                },
                "workbench_task": {
                    "schema": "ztare-leaf-workbench-task-v1",
                    "task_id": "context-only",
                    "source_ref": "test_model.py",
                    "admissible_capability_ids": [
                        "inspect_worldmodel_counterexample_context"
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    (workspace / "input.json").write_text("{}", encoding="utf-8")

    manifest = visible_workbench_cli.manifest_payload(project=tmp_path)
    assert manifest["active_task_scope"]["admissible_evidence_capability_ids"] == [
        "inspect_worldmodel_counterexample_context"
    ]
    assert "inspect_worldmodel_counterexample_context" in manifest["capability_routes"]
    assert (
        manifest["capability_routes"]["inspect_worldmodel_counterexample_context"]["route"]
        == "parent_kernel"
    )
    assert "run_visible_json_probe" not in manifest["capability_routes"]
    assert "probe-json" not in {row["command"] for row in manifest["commands"]}

    with pytest.raises(ValueError, match="outside that task scope"):
        visible_workbench_cli._probe_json(
            project=tmp_path,
            artifact_refs=["workspace/input.json"],
            probe_py="",
            max_output_chars=100,
        )


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


def test_authority_derived_query_preserves_manifest_evidence_boundary(tmp_path: Path) -> None:
    authority = tmp_path / "authority"
    visible = tmp_path / "visible"
    authority.mkdir()
    visible.mkdir()
    (authority / "gate_harness.py").write_text("# gate\n", encoding="utf-8")
    (visible / "MANIFEST.json").write_text(
        json.dumps(
            {
                "authority_project_path": str(authority),
                "authority_project_ref": "projects/example",
                "visible_artifacts": [
                    {
                        "ref": "raw/episodes/episode_001.jsonl",
                        "status": "withheld",
                        "visible_status": "withheld",
                        "reason": "too_large",
                    },
                    {
                        "ref": "workspace/latest_patch_base_regression.json",
                        "status": "materialized",
                        "visible_status": "visible",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    resolved, binding = visible_workbench_cli._authority_project_for_derived_action(
        visible_project=visible,
        capability_id="mine_worldmodel_lowerable_selectors",
        request={
            "input_refs": {
                "latest_regression_ref": "workspace/latest_patch_base_regression.json",
                "episode_log_ref": "visible",
            }
        },
    )

    assert resolved == authority.resolve()
    assert binding["evidence_execution_mode"] == "authority_derived_query"
    assert binding["manifest_visible_evidence_refs"] == [
        "raw/episodes/episode_001.jsonl",
        "workspace/latest_patch_base_regression.json",
    ]


def test_authority_derived_query_rejects_nonvisible_episode(tmp_path: Path) -> None:
    authority = tmp_path / "authority"
    visible = tmp_path / "visible"
    authority.mkdir()
    visible.mkdir()
    (authority / "gate_harness.py").write_text("# gate\n", encoding="utf-8")
    (visible / "MANIFEST.json").write_text(
        json.dumps(
            {
                "authority_project_path": str(authority),
                "visible_artifacts": [
                    {
                        "ref": "raw/episodes/episode_001.jsonl",
                        "status": "materialized",
                        "visible_status": "visible",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="withheld evidence role"):
        visible_workbench_cli._authority_project_for_derived_action(
            visible_project=visible,
            capability_id="contrast_worldmodel_episodes",
            request={"input_refs": {"episode_ref_a": "visible", "episode_ref_b": "holdout"}},
        )


def test_holdout_role_cannot_cross_bridge_when_withheld_only_for_size(
    tmp_path: Path,
) -> None:
    authority = tmp_path / "authority"
    visible = tmp_path / "visible"
    authority.mkdir()
    visible.mkdir()
    (authority / "gate_harness.py").write_text("# gate\n", encoding="utf-8")
    (visible / "MANIFEST.json").write_text(
        json.dumps(
            {
                "authority_project_path": str(authority),
                "episode_roles": {
                    "visible": "raw/episodes/episode_001.jsonl",
                    "holdout": "raw/episodes/episode_002.jsonl",
                },
                "visible_artifacts": [
                    {
                        "ref": "raw/episodes/episode_001.jsonl",
                        "status": "withheld",
                        "visible_status": "withheld",
                        "reason": "too_large",
                    },
                    {
                        "ref": "raw/episodes/episode_002.jsonl",
                        "status": "withheld",
                        "visible_status": "withheld",
                        "reason": "too_large",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="withheld evidence role"):
        visible_workbench_cli._authority_project_for_derived_action(
            visible_project=visible,
            capability_id="contrast_worldmodel_episodes",
            request={
                "input_refs": {
                    "episode_ref_a": "visible",
                    "episode_ref_b": "holdout",
                }
            },
        )


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
