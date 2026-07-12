from __future__ import annotations

import json

from ztare.validator.core.candidate_preflight import (
    CandidatePreflightRequest,
    ControlOnlyPreflightRequest,
    run_candidate_preflights,
    run_worldmodel_control_only_preflights,
)


def test_control_only_preflight_rejects_missing_visible_receipt_ref(tmp_path) -> None:
    payload = {
        "control_receipts": [
            {
                "type": "LOWERABILITY_BLOCKED",
                "payload": {
                    "candidate_family_attempted": "candidate family",
                    "evidence_refs": [
                        "workspace/visible_cli_receipts/missing_score.json",
                    ],
                    "evidence_statuses": [],
                    "missing_witness_or_sensor": "selector",
                    "next_action": "rerun after durable evidence",
                    "obstruction": "candidate scorer unavailable",
                    "visible_capabilities_attempted": ["score_worldmodel_candidate_delta"],
                },
            }
        ],
        "thesis_markdown": "blocked",
        "test_model_py": "",
    }

    message = run_worldmodel_control_only_preflights(
        ControlOnlyPreflightRequest(
            project_dir=tmp_path,
            thesis_text=json.dumps(payload),
        )
    )

    assert message is not None
    assert "missing_refs=workspace/visible_cli_receipts/missing_score.json" in message


def test_control_only_preflight_rejects_missing_strategy_discharge_ref(tmp_path) -> None:
    payload = {
        "control_receipts": [
            {
                "type": "STRATEGY_CARD_DISCHARGE",
                "payload": {
                    "status": "blocked_by_lowerability",
                    "evidence_refs": [
                        "workspace/visible_cli_receipts/missing_strategy_gate.json",
                    ],
                },
            }
        ],
        "thesis_markdown": "blocked",
        "test_model_py": "",
    }

    message = run_worldmodel_control_only_preflights(
        ControlOnlyPreflightRequest(
            project_dir=tmp_path,
            thesis_text=json.dumps(payload),
        )
    )

    assert message is not None
    assert "missing_refs=workspace/visible_cli_receipts/missing_strategy_gate.json" in message


def test_control_only_preflight_accepts_durable_visible_receipt_ref(tmp_path) -> None:
    receipt = tmp_path / "workspace" / "visible_cli_receipts" / "score.json"
    receipt.parent.mkdir(parents=True)
    receipt.write_text('{"status":"ok"}\n', encoding="utf-8")
    payload = {
        "control_receipts": [
            {
                "type": "LOWERABILITY_BLOCKED",
                "payload": {
                    "candidate_family_attempted": "candidate family",
                    "evidence_refs": [str(receipt.relative_to(tmp_path))],
                    "evidence_statuses": [],
                    "missing_witness_or_sensor": "selector",
                    "next_action": "continue CEGIS",
                    "obstruction": "no lowerable selector yet",
                    "visible_capabilities_attempted": ["score_worldmodel_candidate_delta"],
                },
            }
        ],
        "thesis_markdown": "blocked",
        "test_model_py": "",
    }

    message = run_worldmodel_control_only_preflights(
        ControlOnlyPreflightRequest(
            project_dir=tmp_path,
            thesis_text=json.dumps(payload),
        )
    )

    assert message is None


def test_candidate_preflight_accepts_raw_json_visible_diagnostic_binding(tmp_path) -> None:
    receipt = tmp_path / "workspace" / "visible_cli_receipts" / "score.json"
    receipt.parent.mkdir(parents=True)
    receipt.write_text('{"status":"ok"}\n', encoding="utf-8")
    payload = {
        "control_receipts": [
            {
                "type": "VISIBLE_WORKBENCH_DIAGNOSTIC",
                "payload": {
                    "capability_id": "score_worldmodel_candidate_delta",
                    "claim_bindings": ["visible candidate preflight"],
                    "input_hashes": {
                        "receipt_ref": "workspace/visible_cli_receipts/score.json",
                        "receipt_sha256": "not-authority-for-this-test",
                    },
                    "output_summary": "score_worldmodel_candidate_delta visible diagnostic",
                },
            }
        ],
        "thesis_markdown": "uses score_worldmodel_candidate_delta diagnostic",
        "test_model_py": "",
    }

    message = run_candidate_preflights(
        CandidatePreflightRequest(
            project_dir=tmp_path,
            thesis_text=json.dumps(payload),
            executable_candidate_source="def step(grid, action, t):\n    return grid\n",
            python_executable="python",
            pre_judge_gate_harness=True,
            is_worldmodel_contract=True,
            source_ref="workspace/submissions/demo.py",
        )
    )

    assert message is None
