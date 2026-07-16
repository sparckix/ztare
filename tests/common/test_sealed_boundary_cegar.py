from __future__ import annotations

import json

import pytest

from ztare.common.control_state_machine import ControlMorphism
from ztare.common.sealed_boundary_cegar import (
    BOUNDARY_CEGAR_CHART,
    boundary_cegar_admissible_events,
    boundary_cegar_candidate_delta_lowerability,
    boundary_cegar_state_object,
    render_boundary_cegar_retry_surface,
    validate_lowerability_blocked_receipt,
)


def test_boundary_cegar_uses_existing_ledger_surfaces() -> None:
    obj = boundary_cegar_state_object(state="counterexample_open")

    assert obj["schema"] == "ztare-sealed-boundary-cegar-automaton-v1"
    assert obj["admissible_events"] == [
        "request_typed_observation",
        "submit_candidate_delta",
        "report_tool_gap",
    ]
    assert "proposal_taxonomy" not in obj
    contracts = {row["contract"] for row in obj["ledger_surfaces"]}
    assert "ztare.common.leaf_workbench_contract" in contracts
    assert "ztare.common.tool_synthesis_contract" in contracts
    assert "ztare.common.operator_proposal_contract" in contracts


def test_boundary_cegar_retry_surface_preserves_workbench_action_shape() -> None:
    surface = render_boundary_cegar_retry_surface(
        state="counterexample_open",
        executed_morphisms=[],
        admissible_next=[
            ControlMorphism(
                capability_id="inspect_worldmodel_counterexample_context",
                input_refs={"latest_eval_ref": "latest_eval_results.json"},
                claim_bindings=["separate latest quotient"],
            )
        ],
    )

    assert "WORKBENCH STATE" in surface
    assert "SEALED BOUNDARY-CEGAR LIFECYCLE" in surface
    assert "LEAF_WORKBENCH_ACTION_REQUEST" in surface
    assert '"inspect_worldmodel_counterexample_context"' in surface
    assert (
        BOUNDARY_CEGAR_CHART.next_state(
            "counterexample_open",
            "request_typed_observation",
        )
        == "observation_requested"
    )


def test_boundary_cegar_retry_surface_accepts_custom_no_next_policy() -> None:
    surface = render_boundary_cegar_retry_surface(
        state="observation_receipt_available",
        executed_morphisms=["mine_worldmodel_global_carrier_selectors_from_observable_context"],
        carried_receipts_json=(
            '[{"type":"LEAF_WORKBENCH_RECEIPT","payload":{"capability_id":'
            '"mine_worldmodel_global_carrier_selectors_from_observable_context",'
            '"output_summary":"{\\"candidate_delta_admissible\\":true}"}}]'
        ),
        no_next_morphism_policy="submit the lowered candidate or block with typed evidence",
    )

    assert "submit the lowered candidate or block with typed evidence" in surface


def test_boundary_cegar_warns_candidate_without_lowerability_witness() -> None:
    receipts = (
        '[{"type":"LEAF_WORKBENCH_RECEIPT","payload":{"capability_id":'
        '"mine_worldmodel_separating_features","output_summary":'
        '"{\\"schema\\":\\"ztare-worldmodel-separating-feature-miner-v1\\",'
        '\\"candidate_predicates\\":[],\\"support_scoped_predicates\\":[{'
        '\\"lowering_scope\\":\\"quotient_chart_only\\"}]}"}}]'
    )

    assert boundary_cegar_admissible_events(
        state="observation_receipt_available",
        carried_receipts_json=receipts,
    ) == ["request_typed_observation", "submit_candidate_delta", "report_tool_gap"]

    obj = boundary_cegar_state_object(
        state="observation_receipt_available",
        carried_receipts_json=receipts,
    )
    assert obj["context"]["candidate_delta_warning"] == "no_lowerable_receipt_witness"

    surface = render_boundary_cegar_retry_surface(
        state="observation_receipt_available",
        executed_morphisms=["mine_worldmodel_separating_features"],
        carried_receipts_json=receipts,
    )
    assert "candidate_delta_warning" in surface
    assert "negative receipts refute only their named subjects" in surface


def test_candidate_and_family_rejections_do_not_become_space_exhaustion() -> None:
    receipts = json.dumps(
        [
            {
                "type": "LEAF_WORKBENCH_RECEIPT",
                "payload": {
                    "capability_id": "score_worldmodel_candidate_delta",
                    "output_summary": json.dumps(
                        {
                            "schema": "ztare-worldmodel-candidate-delta-score-v1",
                            "admissibility_scope": "candidate",
                            "candidate_sha256": "candidate-a",
                            "candidate_delta_admissible": False,
                            "status": "candidate_preflight_failed",
                        }
                    ),
                },
            },
            {
                "type": "LEAF_WORKBENCH_RECEIPT",
                "payload": {
                    "capability_id": "mine_worldmodel_lowerable_selectors",
                    "output_summary": json.dumps(
                        {
                            "schema": "ztare-worldmodel-lowerable-selector-miner-v1",
                            "admissibility_scope": "candidate_family",
                            "candidate_family_id": "same-shaped-window-selector-v1",
                            "candidate_family_admissible": False,
                            "lowerability_status": "no_zero_error_selector_found",
                        }
                    ),
                },
            },
        ]
    )

    assert boundary_cegar_candidate_delta_lowerability(receipts) is None
    obj = boundary_cegar_state_object(
        state="observation_receipt_available",
        carried_receipts_json=receipts,
    )
    assert obj["context"]["refuted_scopes"] == [
        {
            "scope_kind": "candidate",
            "subject": "candidate-a",
            "verdict": "candidate_preflight_failed",
            "schema": "ztare-worldmodel-candidate-delta-score-v1",
        },
        {
            "scope_kind": "candidate_family",
            "subject": "same-shaped-window-selector-v1",
            "verdict": "no_zero_error_selector_found",
            "schema": "ztare-worldmodel-lowerable-selector-miner-v1",
        },
    ]


def test_boundary_cegar_warns_candidate_on_lowerability_blocked_receipt() -> None:
    receipts = (
        '[{"type":"LOWERABILITY_BLOCKED","payload":{'
        '"visible_capabilities_attempted":["run_visible_json_probe"],'
        '"candidate_family_attempted":"patch-base selector",'
        '"obstruction":"visible chart has no carrier-domain selector",'
        '"missing_witness_or_sensor":"gamma-lowerable selector",'
        '"next_action":"request lowerability witness miner",'
        '"evidence_refs":["workspace/visible_cli_receipts/latest_visible_probe.json"]}}]'
    )

    assert boundary_cegar_candidate_delta_lowerability(receipts) is False
    assert boundary_cegar_admissible_events(
        state="observation_receipt_available",
        carried_receipts_json=receipts,
    ) == ["request_typed_observation", "submit_candidate_delta", "report_tool_gap"]


def test_lowerability_blocked_consumed_counterexample_requires_analysis_ref() -> None:
    payload = {
        "visible_capabilities_attempted": ["score-worldmodel-candidate"],
        "candidate_family_attempted": "candidate_delta",
        "obstruction": "candidate regressed after using staged counterexample",
        "missing_witness_or_sensor": "state/action separator",
        "next_action": "continue visible abduction",
        "evidence_refs": [
            "raw/episodes/episode_002.jsonl",
            "workspace/visible_cli_receipts/score.json",
        ],
        "evidence_statuses": [
            {"ref": "raw/episodes/episode_002.jsonl", "status": "consumed_counterexample"}
        ],
    }

    with pytest.raises(ValueError, match="evidence_analysis_refs"):
        validate_lowerability_blocked_receipt(payload)

    payload["evidence_analysis_refs"] = ["workspace/visible_cli_receipts/score.json"]
    with pytest.raises(ValueError, match="stopping_rationale"):
        validate_lowerability_blocked_receipt(payload)

    payload["stopping_rationale"] = "remaining local probes have no new visible features to test"
    with pytest.raises(ValueError, match="local_frontier_decision"):
        validate_lowerability_blocked_receipt(payload)

    payload["local_frontier_decision"] = {
        "available_actions": ["score candidate", "probe visible receipts"],
        "attempted_actions": ["score candidate"],
        "unattempted_actions": ["probe visible receipts"],
        "chosen": "stop",
        "stop_reason": "remaining probe needs hidden authority boundary",
        "expected_info_note": "scorer already exposed the same quotient",
        "evidence_refs": ["workspace/visible_cli_receipts/score.json"],
    }
    normalized = validate_lowerability_blocked_receipt(payload)
    assert normalized["evidence_analysis_refs"] == ["workspace/visible_cli_receipts/score.json"]
    assert normalized["stopping_rationale"] == "remaining local probes have no new visible features to test"
    assert normalized["local_frontier_decision"]["chosen"] == "stop"


def test_boundary_cegar_warns_candidate_on_no_visible_quotient_receipt() -> None:
    receipts = (
        '[{"type":"LEAF_WORKBENCH_RECEIPT","payload":{"capability_id":'
        '"run_visible_json_probe","output_summary":'
        '"{\\"workspace/latest_patch_base_regression.json\\":{'
        '\\"candidate_regression_receipt\\":{'
        '\\"quotient_comparison\\":{\\"relation\\":'
        '\\"hard_gate_failure_without_visible_quotient\\"}}}}"}}]'
    )

    assert boundary_cegar_admissible_events(
        state="observation_receipt_available",
        carried_receipts_json=receipts,
    ) == ["request_typed_observation", "submit_candidate_delta", "report_tool_gap"]


def test_boundary_cegar_warns_candidate_on_context_only_receipt() -> None:
    receipts = (
        '[{"type":"LEAF_WORKBENCH_RECEIPT","payload":{"capability_id":'
        '"inspect_worldmodel_counterexample_context","output_summary":'
        '"relation=changed_support; support_bbox=[61, 51, 62, 63]; '
        'context_delta=local_band_counts:candidate=... best_prior=..."}}]'
    )

    assert boundary_cegar_admissible_events(
        state="observation_receipt_available",
        carried_receipts_json=receipts,
    ) == ["request_typed_observation", "submit_candidate_delta", "report_tool_gap"]


def test_boundary_cegar_allows_candidate_with_lowerability_witness() -> None:
    receipts = (
        '[{"type":"LEAF_WORKBENCH_RECEIPT","payload":{"capability_id":'
        '"mine_worldmodel_separating_features","output_summary":'
        '"{\\"candidate_predicates\\":[{\\"features\\":[{\\"name\\":'
        '\\"action\\",\\"value\\":1}]}]}"}}]'
    )

    assert boundary_cegar_admissible_events(
        state="observation_receipt_available",
        carried_receipts_json=receipts,
    ) == [
        "request_typed_observation",
        "submit_candidate_delta",
        "report_tool_gap",
    ]


def test_boundary_cegar_keeps_diagnostic_family_non_candidate_even_when_coverage_completes() -> None:
    receipts = (
        '[{"type":"LEAF_WORKBENCH_RECEIPT","payload":{"capability_id":"a",'
        '"output_summary":"{\\"candidate_delta_admissible\\":false,'
        '\\"candidate_label_coverage\\":{\\"required\\":[\\"r1\\",\\"r2\\"],'
        '\\"covered\\":[\\"r1\\"]}}"}}'
        ',{"type":"LEAF_WORKBENCH_RECEIPT","payload":{"capability_id":"b",'
        '"output_summary":"{\\"candidate_delta_admissible\\":false,'
        '\\"candidate_label_coverage\\":{\\"required\\":[\\"r1\\",\\"r2\\"],'
        '\\"covered\\":[\\"r2\\"]}}"}}]'
    )

    assert boundary_cegar_admissible_events(
        state="observation_receipt_available",
        carried_receipts_json=receipts,
    ) == ["request_typed_observation", "submit_candidate_delta", "report_tool_gap"]


# -- search_receipts contract for missing-feature impossibility claims -----------


def _base_lowerability_blocked_payload(**overrides: object) -> dict:
    """Minimal valid LOWERABILITY_BLOCKED payload with no missing-feature language."""
    base = {
        "visible_capabilities_attempted": ["inspect_replay_residual_quotient"],
        "candidate_family_attempted": "patch-base selector",
        "obstruction": "no gamma-lowerable candidate identified after analysis",
        "missing_witness_or_sensor": "gamma-lowerable selector",
        "next_action": "request additional observation",
        "evidence_refs": ["workspace/visible_cli_receipts/probe.json"],
    }
    base.update(overrides)
    return base


def test_lowerability_blocked_missing_feature_claim_without_search_receipts_is_rejected() -> None:
    """A missing-feature obstruction with no probe receipt is a typed R1 reject."""
    payload = _base_lowerability_blocked_payload(
        obstruction="the exposed state lacks a transportable selector for this transition",
        missing_witness_or_sensor="transportable state selector",
        # evidence_refs has no workspace/visible_cli_receipts/* ref
        evidence_refs=["workspace/candidate_memory.json"],
    )
    with pytest.raises(ValueError, match="impossibility claim"):
        validate_lowerability_blocked_receipt(payload)


def test_lowerability_blocked_missing_feature_claim_with_search_receipt_passes() -> None:
    """Same payload WITH a visible_cli_receipts/* ref in evidence_refs passes."""
    payload = _base_lowerability_blocked_payload(
        obstruction="the exposed state lacks a transportable selector for this transition",
        missing_witness_or_sensor="transportable state selector",
        evidence_refs=["workspace/visible_cli_receipts/feature_probe.json"],
    )
    normalized = validate_lowerability_blocked_receipt(payload)
    assert normalized["obstruction"] == "the exposed state lacks a transportable selector for this transition"


def test_lowerability_blocked_missing_feature_claim_with_search_receipts_field_passes() -> None:
    """search_receipts field (separate from evidence_refs) also satisfies the requirement."""
    payload = _base_lowerability_blocked_payload(
        obstruction="the exposed state lacks a transportable selector for this transition",
        missing_witness_or_sensor="transportable state selector",
        evidence_refs=["workspace/candidate_memory.json"],
        search_receipts=["workspace/visible_cli_receipts/feature_probe.json"],
    )
    normalized = validate_lowerability_blocked_receipt(payload)
    assert "obstruction" in normalized


def test_lowerability_blocked_non_missing_feature_obstruction_unaffected() -> None:
    """An obstruction not claiming a missing feature requires no search_receipts."""
    payload = _base_lowerability_blocked_payload(
        obstruction="candidate family exhausted; no improvement on replay quotient",
        missing_witness_or_sensor="gamma-lowerable selector",
        evidence_refs=["workspace/candidate_memory.json"],
    )
    # Should pass: no missing-feature language in obstruction or missing_witness_or_sensor
    normalized = validate_lowerability_blocked_receipt(payload)
    assert normalized["candidate_family_attempted"] == "patch-base selector"
