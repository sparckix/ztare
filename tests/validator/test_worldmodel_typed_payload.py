from __future__ import annotations

import json

import pytest

from ztare.validator.worldmodel_typed_payload import (
    extract_worldmodel_control_receipts,
    parse_worldmodel_typed_payload_text,
    render_worldmodel_typed_payload,
    validate_worldmodel_carrier_source,
    worldmodel_typed_payload_contract_prompt,
)


def test_worldmodel_typed_payload_renders_receipts_outside_python() -> None:
    rendered = render_worldmodel_typed_payload(
        {
            "control_receipts": [
                {
                    "type": "STRATEGY_CARD_DISCHARGE",
                    "payload": {
                        "failure_family_sha": "abc",
                        "outcome": "blocked",
                        "observed_status": "needs operator proposal",
                        "evidence_refs": ["workspace/receipt.json"],
                    },
                }
            ],
            "thesis_markdown": "## Logic DAG\n- receipt -> carrier",
            "test_model_py": "def step(grid, action, t):\n    return grid",
        }
    )

    assert rendered.startswith("STRATEGY_CARD_DISCHARGE:")
    assert "## Logic DAG" in rendered
    assert "```python\ndef step(grid, action, t):" in rendered
    python_block = rendered.split("```python", 1)[1]
    assert "STRATEGY_CARD_DISCHARGE" not in python_block
    compile(python_block.rsplit("```", 1)[0], "<candidate>", "exec")


def test_worldmodel_typed_payload_parser_prefers_outer_schema_object() -> None:
    text = (
        "prefix {\"capability_id\":\"run_strategy_required_gate\"}\n"
        "{\"control_receipts\":[{\"type\":\"LEAF_WORKBENCH_RECEIPT\","
        "\"payload\":{\"capability_id\":\"run_strategy_required_gate\","
        "\"input_hashes\":{\"request\":\"{\\\"capability_id\\\":\\\"nested\\\"}\"},"
        "\"output_summary\":\"{\\\"result\\\":{\\\"exact_steps\\\":0}}\","
        "\"claim_bindings\":[\"gate\"]}}],"
        "\"thesis_markdown\":\"receipt consumed\","
        "\"test_model_py\":\"def step(grid, action, t):\\n    return grid\\n\"}"
        " trailing"
    )

    payload = parse_worldmodel_typed_payload_text(text)

    assert payload["thesis_markdown"] == "receipt consumed"
    assert "def step" in payload["test_model_py"]


def test_worldmodel_typed_payload_parser_keeps_receipt_array_boundary() -> None:
    text = (
        "{\"control_receipts\":["
        "{\"type\":\"LEAF_WORKBENCH_RECEIPT\",\"payload\":{"
        "\"capability_id\":\"run_strategy_required_gate\","
        "\"input_hashes\":{\"receipt_ref\":\"workspace/latest.json\"},"
        "\"output_summary\":\"top={\\\"pair_counts\\\":[{\\\"predicted\\\":11,\\\"observed\\\":3}]}\","
        "\"claim_bindings\":[\"gate\"]}},"
        "{\"type\":\"STRATEGY_CARD_DISCHARGE\",\"payload\":{"
        "\"failure_family_sha\":\"abc\",\"outcome\":\"blocked\","
        "\"evidence_refs\":[\"workspace/latest.json\"]}}],"
        "\"thesis_markdown\":\"receipt array consumed\","
        "\"test_model_py\":\"def step(grid, action, t):\\n    return grid\\n\"}"
    )

    payload = parse_worldmodel_typed_payload_text(text)

    receipts = payload["control_receipts"]
    assert isinstance(receipts, list)
    assert len(receipts) == 2
    assert payload["thesis_markdown"] == "receipt array consumed"


def test_worldmodel_typed_payload_parser_repairs_spilled_control_receipt_type() -> None:
    text = (
        '{"control_receipts":['
        '{"type":"LEAF_WORKBENCH_RECEIPT","payload":{'
        '"capability_id":"run_strategy_required_gate",'
        '"input_hashes":{"receipt_ref":"workspace/latest.json"},'
        '"output_summary":"status=bounded_mismatch",'
        '"claim_bindings":["gate"]}},'
        '{"payload":{'
        '"capability_id":"local_neighborhood_quotient_probe",'
        '"claim_bindings":["need lowerability witness"],'
        '"gap_statement":"visible quotient lacks local neighborhood",'
        '"input_contract":[{"name":"strategy_gate_receipt","type":"artifact_ref"}],'
        '"output_contract":{"schema":"ztare-local-neighborhood-quotient-probe-v1"},'
        '"secret_policy":"visible_only",'
        '"safety_invariant":"does not expose hidden holdout or candidate authority",'
        '"evaluator":"schema round-trip and visible artifact hash binding",'
        '"rollback_condition":"no deterministic variance or schema failure",'
        '"target_artifact":"src/ztare/worldmodel/leaf_workbench.py",'
        '"type":"LEAF_WORKBENCH_CAPABILITY_PROPOSAL"}],'
        '"type":"LEAF_WORKBENCH_CAPABILITY_PROPOSAL"}],'
        '"thesis_markdown":"proposal only",'
        '"test_model_py":""}'
    )

    payload = parse_worldmodel_typed_payload_text(text)

    assert payload["thesis_markdown"] == "proposal only"
    with pytest.raises(ValueError, match="optional meta evidence only"):
        render_worldmodel_typed_payload(payload)


def test_worldmodel_typed_payload_allows_proposal_when_lowerability_blocked() -> None:
    payload = {
        "control_receipts": [
            {
                "type": "LOWERABILITY_BLOCKED",
                "payload": {
                    "visible_capabilities_attempted": ["probe-json"],
                    "candidate_family_attempted": "local_neighborhood_quotient",
                    "obstruction": "no gamma-lowerable witness in visible records",
                    "missing_witness_or_sensor": "local neighborhood quotient probe",
                    "next_action": "batch-review proposed mutable sensor",
                    "evidence_refs": [
                        "workspace/latest_eval_results.json",
                        "workspace/visible_cli_receipts/probe.json",
                    ],
                },
            },
            {
                "type": "LEAF_WORKBENCH_CAPABILITY_PROPOSAL",
                "payload": {
                    "capability_id": "local_neighborhood_quotient_probe",
                    "claim_bindings": ["need lowerability witness"],
                    "gap_statement": "visible quotient lacks local neighborhood",
                    "input_contract": [{"name": "strategy_gate_receipt", "type": "artifact_ref"}],
                    "output_contract": {"schema": "ztare-local-neighborhood-quotient-probe-v1"},
                    "secret_policy": "visible_only",
                    "safety_invariant": "does not expose hidden holdout or candidate authority",
                    "evaluator": "schema round-trip and visible artifact hash binding",
                    "rollback_condition": "no deterministic variance or schema failure",
                    "target_artifact": "src/ztare/worldmodel/leaf_workbench.py",
                },
            },
        ],
        "thesis_markdown": "obstruction plus cold proposal",
        "test_model_py": "",
    }

    rendered = render_worldmodel_typed_payload(payload)

    assert "LOWERABILITY_BLOCKED:" in rendered
    assert "LEAF_WORKBENCH_CAPABILITY_PROPOSAL:" in rendered
    assert "```python" not in rendered


def test_worldmodel_control_receipt_extractor_handles_raw_and_rendered_payloads() -> None:
    payload = {
        "control_receipts": [
            {
                "type": "LOWERABILITY_BLOCKED",
                "payload": {
                    "visible_capabilities_attempted": ["score-worldmodel-candidate"],
                    "candidate_family_attempted": "composed visible selector",
                    "obstruction": "candidate family regresses visible replay",
                    "missing_witness_or_sensor": "joint interaction witness",
                    "next_action": "continue visible synthesis from scored regression",
                    "evidence_refs": ["workspace/visible_cli_receipts/score.json"],
                },
            }
        ],
        "thesis_markdown": "blocked",
        "test_model_py": "",
    }
    rendered = render_worldmodel_typed_payload(payload)

    raw_rows = extract_worldmodel_control_receipts(json.dumps(payload))
    rendered_rows = extract_worldmodel_control_receipts(rendered)

    assert [row["type"] for row in raw_rows] == ["LOWERABILITY_BLOCKED"]
    assert [row["type"] for row in rendered_rows] == ["LOWERABILITY_BLOCKED"]
    assert raw_rows[0]["payload"]["missing_witness_or_sensor"] == "joint interaction witness"
    assert rendered_rows[0]["payload"]["missing_witness_or_sensor"] == "joint interaction witness"


def test_worldmodel_typed_payload_normalizes_top_level_receipt_aliases() -> None:
    payload = {
        "control_receipts": [
            {
                "marker": "STRATEGY_CARD_DISCHARGE",
                "strategy_card_ref": "workspace/strategy_experiments.jsonl:abc",
                "failure_family_sha": "abc",
                "outcome": "blocked",
                "blocker": "requires_visible_probe",
                "evidence_refs": ["workspace/latest_visible_probe.json"],
            }
        ],
        "thesis_markdown": "receipt alias shape",
        "test_model_py": "def step(grid, action, t):\n    return grid\n",
    }

    rendered = render_worldmodel_typed_payload(payload)

    assert rendered.startswith("STRATEGY_CARD_DISCHARGE:")
    assert '"card_ref":"workspace/strategy_experiments.jsonl:abc"' in rendered
    assert '"blocker_kind":"requires_visible_probe"' in rendered
    assert '"marker"' not in rendered.split("\n", 1)[0]


def test_worldmodel_typed_payload_rejects_missing_carrier() -> None:
    with pytest.raises(ValueError, match="test_model_py"):
        render_worldmodel_typed_payload(
            {
                "control_receipts": [],
                "thesis_markdown": "missing source",
            }
        )


def test_worldmodel_typed_payload_allows_action_request_without_carrier() -> None:
    rendered = render_worldmodel_typed_payload(
        {
            "control_receipts": [
                {
                    "type": "LEAF_WORKBENCH_ACTION_REQUEST",
                    "payload": {
                        "capability_id": "inspect_replay_residual_quotient",
                        "input_refs": {"diagnostics_ref": "workspace/latest.json"},
                        "claim_bindings": ["need current residual quotient"],
                    },
                }
            ],
            "thesis_markdown": "request probe only",
        }
    )

    assert rendered.startswith("LEAF_WORKBENCH_ACTION_REQUEST:")
    assert "request probe only" in rendered
    assert "```python" not in rendered


def test_worldmodel_typed_payload_action_request_survives_malformed_optional_proposal() -> None:
    rendered = render_worldmodel_typed_payload(
        {
            "control_receipts": [
                {
                    "type": "LEAF_WORKBENCH_ACTION_REQUEST",
                    "payload": {
                        "capability_id": "run_strategy_required_gate",
                        "input_refs": {
                            "command": "arc3_level_transfer_probe",
                            "failure_family_sha": "abc",
                        },
                        "claim_bindings": ["execute declared gate"],
                    },
                },
                {
                    "type": "LEAF_WORKBENCH_CAPABILITY_PROPOSAL",
                    "payload": {
                        "capability_id": "joined_lowerable_selector_synthesizer",
                        "current_state": "partial selector receipts",
                        "desired_state": "candidate delta can be lowered",
                    },
                },
            ],
            "thesis_markdown": "action plus optional malformed proposal",
        }
    )

    assert rendered.startswith("LEAF_WORKBENCH_ACTION_REQUEST:")
    assert "LEAF_WORKBENCH_CAPABILITY_PROPOSAL_QUARANTINED:" in rendered
    assert "joined_lowerable_selector_synthesizer" not in rendered
    assert "```python" not in rendered


def test_worldmodel_typed_payload_rejects_malformed_proposal_as_empty_candidate_reason() -> None:
    with pytest.raises(ValueError, match="optional meta evidence only"):
        render_worldmodel_typed_payload(
            {
                "control_receipts": [
                    {
                        "type": "LEAF_WORKBENCH_CAPABILITY_PROPOSAL",
                        "payload": {
                            "capability_id": "joined_lowerable_selector_synthesizer",
                            "current_state": "partial selector receipts",
                        },
                    }
                ],
                "thesis_markdown": "malformed proposal only",
                "test_model_py": "",
            }
        )


def test_worldmodel_typed_payload_rejects_blocked_strategy_discharge_without_runtime_effect() -> None:
    with pytest.raises(ValueError, match="requires non-empty `test_model_py`"):
        render_worldmodel_typed_payload(
            {
                "control_receipts": [
                    {
                        "type": "STRATEGY_CARD_DISCHARGE",
                        "payload": {
                            "failure_family_sha": "abc",
                            "outcome": "blocked",
                            "blocker_kind": "underdetermined_by_current_log",
                            "evidence_refs": ["workspace/receipt.json"],
                        },
                    }
                ],
                "thesis_markdown": "not enough",
            }
        )


def test_worldmodel_typed_payload_rejects_refuted_strategy_discharge_without_runtime_effect() -> None:
    with pytest.raises(ValueError, match="requires non-empty `test_model_py`"):
        render_worldmodel_typed_payload(
            {
                "control_receipts": [
                    {
                        "type": "STRATEGY_CARD_DISCHARGE",
                        "payload": {
                            "failure_family_sha": "abc",
                            "outcome": "refuted",
                            "evidence_refs": ["workspace/receipt.json"],
                        },
                    }
                ],
                "thesis_markdown": "gate refuted candidate",
            }
        )


def test_worldmodel_typed_payload_rejects_refuted_strategy_discharge_without_evidence() -> None:
    with pytest.raises(ValueError, match="test_model_py"):
        render_worldmodel_typed_payload(
            {
                "control_receipts": [
                    {
                        "type": "STRATEGY_CARD_DISCHARGE",
                        "payload": {
                            "failure_family_sha": "abc",
                            "outcome": "refuted",
                        },
                    }
                ],
                "thesis_markdown": "no evidence",
            }
        )


def test_worldmodel_typed_payload_still_requires_carrier_for_nonblocking_strategy_receipt() -> None:
    with pytest.raises(ValueError, match="test_model_py"):
        render_worldmodel_typed_payload(
            {
                "control_receipts": [
                    {
                        "type": "STRATEGY_CARD_DISCHARGE",
                        "payload": {
                            "failure_family_sha": "abc",
                            "outcome": "blocked",
                            "evidence_refs": ["workspace/receipt.json"],
                        },
                    }
                ],
                "thesis_markdown": "not enough",
            }
        )


def test_worldmodel_typed_payload_accepts_file_map_carrier() -> None:
    rendered = render_worldmodel_typed_payload(
        {
            "control_receipts": [],
            "thesis_markdown": "file-map carrier",
            "files": {
                "test_model.py": "def step(grid, action, t):\n    return grid",
            },
        }
    )

    assert "file-map carrier" in rendered
    assert "```python\ndef step(grid, action, t):" in rendered


def test_worldmodel_typed_payload_accepts_source_alias_carrier() -> None:
    rendered = render_worldmodel_typed_payload(
        {
            "control_receipts": [],
            "thesis_markdown": "source alias",
            "python_code": "def step(grid, action, t):\n    return grid",
        }
    )

    assert "source alias" in rendered
    assert "```python\ndef step(grid, action, t):" in rendered


def test_worldmodel_typed_payload_accepts_thesis_prose_alias() -> None:
    rendered = render_worldmodel_typed_payload(
        {
            "control_receipts": [],
            "thesis_prose": "alias accepted before legacy markdown fallback",
            "test_model_py": "def step(grid, action, t):\n    return grid",
        }
    )

    assert "alias accepted before legacy markdown fallback" in rendered
    assert "```python\ndef step(grid, action, t):" in rendered


def test_worldmodel_typed_payload_normalizes_envelope_aliases() -> None:
    text = (
        '{"receipts":[],"thesis":"alias thesis",'
        '"PROGRAM":"def step(grid, action, t):\\n    return grid\\n"}'
    )

    payload = parse_worldmodel_typed_payload_text(text)
    rendered = render_worldmodel_typed_payload(payload)

    assert payload["control_receipts"] == []
    assert payload["thesis_markdown"] == "alias thesis"
    assert "```python\ndef step(grid, action, t):" in rendered


def test_worldmodel_typed_payload_contract_forbids_invented_catalog_ops() -> None:
    prompt = worldmodel_typed_payload_contract_prompt()

    assert "exact full `failure_family_sha`" in prompt
    assert "SHA prefixes" in prompt
    assert "Never invent an op" in prompt
    assert "postprocess_clear_pair" in prompt
    assert "PATCH_BASE" in prompt
    assert "PATCH_DELTA" in prompt
    assert "<full-sha256>" in prompt
    assert "PATCH_DELTA(base_next, state, action)" in prompt
    assert "Never invent a patch-base source_ref or sha" in prompt
    assert "adapter replay index is not transition-law evidence" not in prompt
    assert "t == 1" not in prompt
    assert "translate_block" in prompt
    assert "LEAF WORKBENCH CONTRACT" in prompt
    assert "compute_residual_quotient" not in prompt
    assert "run_visible_json_probe" in prompt
    assert "inspect_replay_residual_quotient" in prompt
    assert "LEAF_WORKBENCH_CAPABILITY_PROPOSAL" in prompt


def test_worldmodel_carrier_allows_plain_executable_step_without_spec() -> None:
    validate_worldmodel_carrier_source(
        "def step(grid, action, t):\n"
        "    return grid\n"
        "PROGRAM = step\n"
    )


def test_worldmodel_carrier_rejects_absolute_t_literal_without_receipt() -> None:
    with pytest.raises(ValueError, match="temporal admissibility"):
        validate_worldmodel_carrier_source(
            "def PATCH_DELTA(base_next, state, action, t):\n"
            "    if t == 128:\n"
            "        return base_next\n"
            "    return base_next\n"
        )


def test_worldmodel_carrier_rejects_bare_patch_delta_without_patch_base() -> None:
    with pytest.raises(ValueError, match="PATCH_DELTA is a patch combiner"):
        validate_worldmodel_carrier_source(
            "def PATCH_DELTA(base_next, state, action):\n"
            "    return base_next\n"
        )


def test_worldmodel_carrier_rejects_self_declared_temporal_receipt() -> None:
    with pytest.raises(ValueError, match="temporal admissibility"):
        validate_worldmodel_carrier_source(
        "TEMPORAL_ADMISSIBILITY = {'status': 'phase_shift_holdout'}\n"
        "def PATCH_DELTA(base_next, state, action, t):\n"
        "    if t == 128:\n"
        "        return base_next\n"
        "    return base_next\n"
        )


def test_worldmodel_carrier_rejects_fake_spec_wrapper() -> None:
    with pytest.raises(ValueError, match="WORLD_MODEL_SPEC must be a literal catalog spec"):
        validate_worldmodel_carrier_source(
            "def step(grid, action, t):\n"
            "    return grid\n"
            "WORLD_MODEL_SPEC = {'step': step}\n"
            "PROGRAM = step\n"
        )


def test_worldmodel_carrier_rejects_non_lowerable_literal_spec() -> None:
    with pytest.raises(ValueError, match="non-empty actions"):
        validate_worldmodel_carrier_source(
            "WORLD_MODEL_SPEC = {'step': 'not a catalog spec'}\n"
            "def step(grid, action, t):\n"
            "    return grid\n"
        )


def test_worldmodel_carrier_accepts_lowerable_literal_spec() -> None:
    validate_worldmodel_carrier_source(
        "WORLD_MODEL_SPEC = {'actions': {'0': [{'op': 'identity'}]}}\n"
    )


def test_worldmodel_carrier_rejects_global_replay_counter() -> None:
    with pytest.raises(ValueError, match="global.*replay state"):
        validate_worldmodel_carrier_source(
            "_COUNT = 0\n"
            "def PATCH_DELTA(base_next, state, action, t):\n"
            "    global _COUNT\n"
            "    _COUNT += 1\n"
            "    return base_next\n"
        )


def test_worldmodel_carrier_rejects_module_cache_mutation() -> None:
    with pytest.raises(ValueError, match="module-scope object"):
        validate_worldmodel_carrier_source(
            "_SEEN = []\n"
            "def step(grid, action, t):\n"
            "    _SEEN.append((action, t))\n"
            "    return grid\n"
        )


def test_worldmodel_carrier_allows_local_output_mutation() -> None:
    validate_worldmodel_carrier_source(
        "def step(grid, action, t):\n"
        "    out = [list(row) for row in grid]\n"
        "    if out:\n"
        "        out[0][0] = out[0][0]\n"
        "    return out\n"
    )


def test_worldmodel_typed_payload_renders_leaf_workbench_receipt() -> None:
    rendered = render_worldmodel_typed_payload(
        {
            "control_receipts": [
                {
                    "type": "LEAF_WORKBENCH_RECEIPT",
                    "payload": {
                        "capability_id": "run_visible_json_probe",
                        "input_hashes": {"artifact_hashes": {"workspace/file.json": "sha256:abc"}},
                        "output_summary": "2 residue classes over visible artifact",
                        "claim_bindings": ["visible probe separates two quotient classes"],
                    },
                }
            ],
            "thesis_markdown": "uses a workbench receipt",
            "test_model_py": "def step(grid, action, t):\n    return grid",
        }
    )

    assert rendered.startswith("VISIBLE_WORKBENCH_DIAGNOSTIC:")
    assert '"capability_id":"run_visible_json_probe"' in rendered
    assert "LEAF_WORKBENCH_RECEIPT:" not in rendered
    python_block = rendered.split("```python", 1)[1]
    assert "LEAF_WORKBENCH_RECEIPT" not in python_block


def test_worldmodel_typed_payload_rejects_unknown_action_instead_of_converting() -> None:
    with pytest.raises(ValueError, match="unknown capability_id"):
        render_worldmodel_typed_payload(
            {
                "control_receipts": [
                    {
                        "type": "LEAF_WORKBENCH_ACTION_REQUEST",
                        "payload": {
                            "capability_id": "inspect_patch_delta_abi_context",
                            "input_refs": {
                                "latest_eval_ref": "latest_eval_results.json",
                                "episode_log_ref": "raw/episodes/episode_001.jsonl",
                            },
                            "claim_bindings": [
                                "Expose a missing visible ABI/context observation"
                            ],
                        },
                    }
                ],
                "thesis_markdown": "control-only proposal",
                "test_model_py": "def step(grid, action, t):\n    return grid",
            }
        )


def test_worldmodel_typed_payload_accepts_worldmodel_leaf_workbench_receipt() -> None:
    rendered = render_worldmodel_typed_payload(
        {
            "control_receipts": [
                {
                    "type": "LEAF_WORKBENCH_RECEIPT",
                    "payload": {
                        "capability_id": "inspect_replay_residual_quotient",
                        "input_hashes": {"diagnostics_ref": "sha256:def"},
                        "output_summary": "class_count=36; pairs=8->3x4",
                        "claim_bindings": ["candidate targets current replay quotient"],
                    },
                }
            ],
            "thesis_markdown": "uses worldmodel workbench",
            "test_model_py": "def step(grid, action, t):\n    return grid",
        }
    )

    assert rendered.startswith("LEAF_WORKBENCH_RECEIPT:")
    assert '"capability_id":"inspect_replay_residual_quotient"' in rendered


def test_worldmodel_typed_payload_accepts_non_lowerable_receipt_without_carrier() -> None:
    rendered = render_worldmodel_typed_payload(
        {
            "control_receipts": [
                {
                    "type": "STRATEGY_CARD_DISCHARGE",
                    "payload": {
                        "failure_family_sha": "abc123",
                        "outcome": "blocked",
                        "blocker_kind": "attempted_probe_failed",
                        "observed_status": "no lowerable witness",
                        "evidence_refs": ["workspace/receipt.json"],
                    },
                },
                {
                    "type": "LEAF_WORKBENCH_RECEIPT",
                    "payload": {
                        "capability_id": "mine_worldmodel_lowerable_selectors",
                        "input_hashes": {"receipt_ref": "sha256:abc"},
                        "output_summary": (
                            '{"authority":"diagnostic_only",'
                            '"candidate_delta_admissible":false,'
                            '"candidate_predicates":[]}'
                        ),
                        "claim_bindings": ["lowerability check"],
                    },
                },
            ],
            "thesis_markdown": "blocked by carried lowerability receipt",
            "test_model_py": "",
        }
    )

    assert "STRATEGY_CARD_DISCHARGE:" in rendered
    assert "LEAF_WORKBENCH_RECEIPT:" in rendered
    assert "candidate_delta_admissible" in rendered
    assert "```python" not in rendered


def test_worldmodel_typed_payload_rejects_candidate_with_non_lowerable_receipt() -> None:
    with pytest.raises(ValueError, match="cannot pair executable"):
        render_worldmodel_typed_payload(
            {
                "control_receipts": [
                    {
                        "type": "LEAF_WORKBENCH_RECEIPT",
                        "payload": {
                            "capability_id": "mine_worldmodel_lowerable_selectors",
                            "input_hashes": {"receipt_ref": "sha256:abc"},
                            "output_summary": (
                                '{"authority":"diagnostic_only",'
                                '"candidate_delta_admissible":false,'
                                '"candidate_predicates":[]}'
                            ),
                            "claim_bindings": ["lowerability check"],
                        },
                    },
                ],
                "thesis_markdown": "contradictory candidate",
                "test_model_py": "def step(grid, action, t):\n    return grid",
            }
        )


def test_worldmodel_typed_payload_accepts_lowerability_blocked_without_carrier() -> None:
    rendered = render_worldmodel_typed_payload(
        {
            "control_receipts": [
                {
                    "type": "LOWERABILITY_BLOCKED",
                    "payload": {
                        "visible_capabilities_attempted": [
                            "run_visible_json_probe",
                            "check_worldmodel_carrier_contract",
                        ],
                        "candidate_family_attempted": "patch-base local selector",
                        "obstruction": "visible predicates separate the chart but do not lower to a state/action carrier",
                        "missing_witness_or_sensor": "transportable selector over carrier inputs",
                        "next_action": "request lowerability witness miner or submit capability proposal",
                        "evidence_refs": [
                            "workspace/visible_cli_receipts/latest_visible_probe.json",
                            "workspace/visible_cli_receipts/carrier_preflight.json",
                        ],
                    },
                }
            ],
            "thesis_markdown": "no gamma-lowerable candidate after visible preflight",
            "test_model_py": "",
        }
    )

    assert rendered.startswith("LOWERABILITY_BLOCKED:")
    assert '"schema":"ztare-lowerability-blocked-v1"' in rendered
    assert "```python" not in rendered


def test_worldmodel_typed_payload_rejects_malformed_lowerability_blocked_escape() -> None:
    with pytest.raises(ValueError, match="visible_capabilities_attempted"):
        render_worldmodel_typed_payload(
            {
                "control_receipts": [
                    {
                        "type": "LOWERABILITY_BLOCKED",
                        "payload": {
                            "candidate_family_attempted": "patch-base local selector",
                            "obstruction": "not enough",
                            "missing_witness_or_sensor": "selector",
                            "next_action": "request probe",
                            "evidence_refs": ["workspace/latest_visible_probe.json"],
                        },
                    }
                ],
                "thesis_markdown": "malformed lowerability escape",
                "test_model_py": "",
            }
        )


def test_worldmodel_typed_payload_repairs_surplus_receipt_brace_without_inner_projection() -> None:
    text = (
        '{"control_receipts":[{"type":"STRATEGY_CARD_DISCHARGE","payload":'
        '{"failure_family_sha":"abc","outcome":"blocked","observed_status":"x",'
        '"evidence_refs":["workspace/a"],"blocker_kind":"requires_external_actions",'
        '"next_action":"probe","attempted_repair":"repair"}}}],'
        '"thesis_markdown":"uses geometric quotient",'
        '"test_model_py":"def step(grid, action, t):\\n    return grid"}'
    )

    obj = parse_worldmodel_typed_payload_text(text)
    rendered = render_worldmodel_typed_payload(obj)

    assert "def step(grid, action, t)" in rendered
    assert rendered.startswith("STRATEGY_CARD_DISCHARGE:")


def test_worldmodel_typed_payload_normalizes_replay_diagnostics_alias() -> None:
    rendered = render_worldmodel_typed_payload(
        {
            "control_receipts": [
                {
                    "type": "LEAF_WORKBENCH_RECEIPT",
                    "payload": {
                        "capability_id": "latest_replay_diagnostics",
                        "input_hashes": {
                            "diagnostics_ref": "workspace/latest_replay_diagnostics_after_abduce.json",
                        },
                        "output_summary": "class_count=37; t=128; action=1",
                        "claim_bindings": ["candidate targets current replay quotient"],
                    },
                }
            ],
            "thesis_markdown": "uses legacy diagnostic label",
            "test_model_py": "def step(grid, action, t):\n    return grid",
        }
    )

    assert '"capability_id":"inspect_replay_residual_quotient"' in rendered
    assert '"capability_id":"latest_replay_diagnostics"' not in rendered


def test_worldmodel_typed_payload_rejects_unknown_leaf_workbench_action() -> None:
    with pytest.raises(ValueError, match="unknown capability_id"):
        render_worldmodel_typed_payload(
            {
                "control_receipts": [
                    {
                        "type": "LEAF_WORKBENCH_RECEIPT",
                        "payload": {
                            "capability_id": "inspect_raw_holdout",
                            "input_hashes": {"candidate_ref": "sha256:abc"},
                            "output_summary": "peeked",
                            "claim_bindings": ["claim"],
                        },
                    }
                ],
                "thesis_markdown": "bad receipt",
                "test_model_py": "def step(grid, action, t):\n    return grid",
            }
        )


def test_worldmodel_typed_payload_demotes_visible_route_action_to_diagnostic() -> None:
    rendered = render_worldmodel_typed_payload(
        {
            "control_receipts": [
                {
                    "type": "LEAF_WORKBENCH_RECEIPT",
                    "payload": {
                        "capability_id": "route_action",
                        "input_hashes": {
                            "source_ref": "stdin",
                            "source_sha256": "0" * 64,
                        },
                        "output_summary": "tool_synthesis routes to parent_kernel",
                        "claim_bindings": ["local route preflight"],
                    },
                }
            ],
            "thesis_markdown": "route checked locally",
            "test_model_py": "def step(grid, action, t):\n    return grid\n",
        }
    )

    assert "VISIBLE_WORKBENCH_DIAGNOSTIC:" in rendered
    assert "LEAF_WORKBENCH_RECEIPT:" not in rendered
    assert '"capability_id":"route_action"' in rendered


def test_worldmodel_typed_payload_demotes_visible_probe_to_diagnostic() -> None:
    rendered = render_worldmodel_typed_payload(
        {
            "control_receipts": [
                {
                    "type": "LEAF_WORKBENCH_RECEIPT",
                    "payload": {
                        "capability_id": "run_visible_json_probe",
                        "input_hashes": {
                            "artifact_hashes": {
                                "visible_manifest.json": "a" * 64,
                            },
                            "probe_sha256": "b" * 64,
                        },
                        "output_summary": "visible staged artifacts summarized",
                        "claim_bindings": ["visible CLI probe"],
                    },
                }
            ],
            "thesis_markdown": "visible probe checked locally",
            "test_model_py": "def step(grid, action, t):\n    return grid\n",
        }
    )

    assert "VISIBLE_WORKBENCH_DIAGNOSTIC:" in rendered
    assert "LEAF_WORKBENCH_RECEIPT:" not in rendered
    assert '"capability_id":"run_visible_json_probe"' in rendered
    assert "```python" in rendered


def test_worldmodel_typed_payload_demotes_persisted_visible_adapter_receipt() -> None:
    rendered = render_worldmodel_typed_payload(
        {
            "control_receipts": [
                {
                    "type": "LEAF_WORKBENCH_RECEIPT",
                    "payload": {
                        "capability_id": "mine_worldmodel_lowerable_selectors",
                        "input_hashes": {
                            "latest_regression_ref": "workspace/visible_cli_receipts/score.json",
                            "receipt_ref": "workspace/visible_cli_receipts/mine.json",
                            "receipt_sha256": "a" * 64,
                        },
                        "output_ref": "workspace/visible_cli_receipts/mine.json",
                        "output_sha256": "a" * 64,
                        "output_summary": "visible selector miner result",
                        "claim_bindings": ["visible local action"],
                    },
                }
            ],
            "thesis_markdown": "visible adapter receipt checked locally",
            "test_model_py": "def step(grid, action, t):\n    return grid\n",
        }
    )

    assert "VISIBLE_WORKBENCH_DIAGNOSTIC:" in rendered
    assert "LEAF_WORKBENCH_RECEIPT:" not in rendered
    assert '"capability_id":"mine_worldmodel_lowerable_selectors"' in rendered


def test_worldmodel_typed_payload_demotes_unstamped_visible_adapter_diagnostics() -> None:
    rendered = render_worldmodel_typed_payload(
        {
            "control_receipts": [
                {
                    "type": "LEAF_WORKBENCH_RECEIPT",
                    "payload": {
                        "capability_id": "cell_local_lowerable_carrier_selector_miner",
                        "input_hashes": {
                            "request": "{\"capability_id\":\"cell_local_lowerable_carrier_selector_miner\"}",
                            "strategy_gate_receipt_ref": "workspace/latest_level_transfer_probe.json",
                            "strategy_gate_receipt_sha256": "a" * 64,
                        },
                        "output_summary": "partial visible selector family",
                        "claim_bindings": ["visible local action"],
                    },
                },
                {
                    "type": "LEAF_WORKBENCH_RECEIPT",
                    "payload": {
                        "capability_id": "score_worldmodel_candidate_delta",
                        "input_hashes": {
                            "candidate_ref": "workspace/scratch/generated-artifact.any",
                            "candidate_sha256": "b" * 64,
                            "request": "{\"capability_id\":\"score_worldmodel_candidate_delta\"}",
                        },
                        "output_summary": "{\"status\":\"candidate_preflight_passed\"}",
                        "claim_bindings": ["visible local action"],
                    },
                },
            ],
            "thesis_markdown": "visible local diagnostics inform the candidate but do not claim authority",
            "test_model_py": "def step(grid, action, t):\n    return grid\n",
        }
    )

    assert rendered.count("VISIBLE_WORKBENCH_DIAGNOSTIC:") == 2
    assert "LEAF_WORKBENCH_RECEIPT:" not in rendered
    assert '"capability_id":"cell_local_lowerable_carrier_selector_miner"' in rendered
    assert '"capability_id":"score_worldmodel_candidate_delta"' in rendered


def test_worldmodel_typed_payload_rejects_proposal_only_without_lowerability_blocker() -> None:
    payload = {
            "control_receipts": [
                {
                    "type": "LEAF_WORKBENCH_CAPABILITY_PROPOSAL",
                    "payload": {
                        "proposed_capability_id": "compare_candidate_minimality",
                        "gap_statement": "current scorer cannot decide whether two patches are behaviorally equivalent",
                        "input_contract": ["candidate_a_ref", "candidate_b_ref", "evaluator_ref"],
                        "output_contract": ["equivalence_summary", "distinguishing_counterexample_ref"],
                        "evaluator": "frozen replay plus no-regression gate",
                        "secret_policy": "sealed_aggregate_only",
                        "safety_invariant": "no raw hidden data leaves the evaluator",
                        "rollback_condition": "any regression or missing counterexample receipt",
                    },
                }
            ],
            "thesis_markdown": "proposal only",
            "test_model_py": "",
        }

    with pytest.raises(ValueError, match="optional meta evidence only"):
        render_worldmodel_typed_payload(payload)


def test_worldmodel_typed_payload_rejects_structured_proposal_only_without_lowerability_blocker() -> None:
    payload = {
            "control_receipts": [
                {
                    "type": "LEAF_WORKBENCH_CAPABILITY_PROPOSAL",
                    "payload": {
                        "proposed_capability_id": "patch_base_improvement_precheck_repair",
                        "gap_statement": "current precheck reports regression but the leaf needs a bounded repair instrument",
                        "input_contract": {
                            "required_fields": ["rejection_ref", "base_source_ref", "repair_rationale"],
                            "candidate_carrier_kind": "PATCH_BASE plus PATCH_DELTA",
                        },
                        "output_contract": {
                            "required_fields": ["patch_base", "patch_delta_scope", "rollback_condition"],
                        },
                        "evaluator": {
                            "type": "deterministic_replay_prejudge",
                            "pass_condition": "strict improvement over preserved base",
                        },
                        "secret_policy": {"uses_secret_data": False, "policy": "public_only"},
                        "safety_invariant": "proposal cannot modify hard-kernel gates",
                        "rollback_condition": "any deterministic regression against the preserved base",
                    },
                }
            ],
            "thesis_markdown": "proposal only",
            "test_model_py": "",
        }

    with pytest.raises(ValueError, match="optional meta evidence only"):
        render_worldmodel_typed_payload(payload)


def test_worldmodel_typed_payload_recovers_nested_type_capability_proposal() -> None:
    payload = {
            "control_receipts": [
                {
                    "payload": {
                        "capability_id": "quotient_free_boundary_carrier_miner",
                        "motivation": (
                            "current probes expose the residue but cannot lower "
                            "the chart separator into an executable selector"
                        ),
                        "required_inputs": [
                            "raw/episodes/episode_001.jsonl",
                            "workspace/latest_patch_base_regression.json",
                        ],
                        "required_output_schema": {
                            "schema": "ztare-quotient-free-boundary-carrier-miner-v1",
                            "candidate_delta_admissible": "boolean",
                            "candidate_predicates": "list",
                        },
                        "forbidden_feature_audit": [
                            "absolute_row",
                            "absolute_time",
                            "support_identity",
                            "quotient_label",
                            "hidden_evaluator_field",
                        ],
                        "type": "LEAF_WORKBENCH_CAPABILITY_PROPOSAL",
                    }
                }
            ],
            "thesis_markdown": "proposal with displaced wrapper type",
            "test_model_py": "",
        }

    with pytest.raises(ValueError, match="optional meta evidence only"):
        render_worldmodel_typed_payload(payload)


def test_worldmodel_typed_payload_accepts_minimal_claim_bound_capability_proposal() -> None:
    payload = {
            "control_receipts": [
                {
                    "type": "LEAF_WORKBENCH_CAPABILITY_PROPOSAL",
                    "payload": {
                        "capability_id": "mine_visible_transition_law_lowerability_witness",
                        "claim_bindings": [
                            "find or refute an admissible executable transition carrier "
                            "using observable features only"
                        ],
                        "reason": (
                            "existing registered observations separate the failure "
                            "diagnostically but do not provide a lowerable witness"
                        ),
                    },
                }
            ],
            "thesis_markdown": "minimal proposal",
            "test_model_py": "",
        }

    with pytest.raises(ValueError, match="optional meta evidence only"):
        render_worldmodel_typed_payload(payload)


def test_worldmodel_typed_payload_accepts_leaf_workbench_action_request() -> None:
    rendered = render_worldmodel_typed_payload(
        {
            "control_receipts": [
                {
                    "type": "LEAF_WORKBENCH_ACTION_REQUEST",
                    "payload": {
                        "capability_id": "inspect_replay_residual_quotient",
                        "input_refs": {"diagnostics_ref": "workspace/latest.json"},
                        "claim_bindings": ["need current residual quotient"],
                    },
                }
            ],
            "thesis_markdown": "request action",
            "test_model_py": "def step(grid, action, t):\n    return grid",
        }
    )

    assert rendered.startswith("LEAF_WORKBENCH_ACTION_REQUEST:")
    assert "inspect_replay_residual_quotient" in rendered
    assert "```python" in rendered
    assert "def step(grid, action, t)" in rendered


def test_worldmodel_typed_payload_does_not_erase_candidate_when_control_receipt_present() -> None:
    rendered = render_worldmodel_typed_payload(
        {
            "control_receipts": [
                {
                    "type": "LEAF_WORKBENCH_ACTION_REQUEST",
                    "payload": {
                        "capability_id": "inspect_replay_residual_quotient",
                        "input_refs": {"diagnostics_ref": "workspace/latest.json"},
                        "claim_bindings": ["need current residual quotient"],
                    },
                }
            ],
            "thesis_markdown": "candidate plus action request",
            "test_model_py": "def step(grid, action, t):\n    return tuple(tuple(row) for row in grid)",
        }
    )

    assert "LEAF_WORKBENCH_ACTION_REQUEST:" in rendered
    assert "```python" in rendered
    assert "return tuple(tuple(row) for row in grid)" in rendered


def test_worldmodel_typed_payload_action_request_may_coexist_with_strategy_discharge_without_carrier() -> None:
    rendered = render_worldmodel_typed_payload(
        {
            "control_receipts": [
                {
                    "type": "STRATEGY_CARD_DISCHARGE",
                    "payload": {
                        "failure_family_sha": "abc123",
                        "outcome": "blocked",
                        "blocker_kind": "requires_external_actions",
                        "observed_status": "requesting declared gate",
                        "evidence_refs": ["latest_eval_results.json"],
                        "new_evidence_refs": ["pending workbench action"],
                        "next_action": "arc3_level_transfer_probe:exact_local_transfer_depth",
                    },
                },
                {
                    "type": "LEAF_WORKBENCH_ACTION_REQUEST",
                    "payload": {
                        "capability_id": "run_strategy_required_gate",
                        "input_refs": {
                            "failure_family_sha": "abc123",
                            "command": "arc3_level_transfer_probe",
                            "candidate_path": "test_model.py",
                        },
                        "claim_bindings": ["run declared Strategy gate"],
                    },
                },
            ],
            "thesis_markdown": "request bounded gate receipt before carrier adoption",
        }
    )

    assert "STRATEGY_CARD_DISCHARGE:" in rendered
    assert "LEAF_WORKBENCH_ACTION_REQUEST:" in rendered
    assert "```python" not in rendered
