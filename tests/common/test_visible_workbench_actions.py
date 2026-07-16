from __future__ import annotations

from ztare.common.visible_workbench_actions import route_visible_workbench_action_request
from ztare.worldmodel.leaf_workbench import validate_worldmodel_leaf_workbench_registry


def test_tool_synthesis_routes_to_capability_proposal_not_parent_kernel() -> None:
    route = route_visible_workbench_action_request(
        {
            "type": "LEAF_WORKBENCH_ACTION_REQUEST",
            "payload": {
                "capability_id": "tool_synthesis",
                "required_next_gate": {
                    "command": "tool_synthesis_gate",
                    "success_status": "compiled_tool_receipt_plus_regression_pass",
                },
            },
        }
    )

    assert route["route"] == "capability_proposal"
    assert route["authority"] == "proposal_only"


def test_unknown_non_tool_action_routes_to_invalid_request() -> None:
    route = route_visible_workbench_action_request(
        {
            "type": "LEAF_WORKBENCH_ACTION_REQUEST",
            "payload": {"capability_id": "run_private_authority_gate"},
        }
    )

    assert route["route"] == "invalid_action_request"
    assert route["status"] == "fail"


def test_gate_command_as_capability_routes_to_invalid_request() -> None:
    route = route_visible_workbench_action_request(
        {
            "type": "LEAF_WORKBENCH_ACTION_REQUEST",
            "payload": {
                "capability_id": "arc3_level_transfer_probe",
                "required_next_gate": {"command": "arc3_level_transfer_probe"},
            },
        }
    )

    assert route["route"] == "invalid_action_request"
    assert "run_strategy_required_gate" in route["reason"]


def test_strategy_gate_wrapper_rejects_verification_only_inner_command() -> None:
    route = route_visible_workbench_action_request(
        {
            "type": "LEAF_WORKBENCH_ACTION_REQUEST",
            "payload": {
                "capability_id": "run_strategy_required_gate",
                "input_refs": {"command": "replay_diagnostics"},
            },
        }
    )

    assert route["route"] == "invalid_action_request"
    assert route["status"] == "fail"
    assert "registered executable domain" in route["reason"]
    assert "candidate-bound" in route["reason"]


def test_strategy_gate_wrapper_accepts_registered_inner_command() -> None:
    route = route_visible_workbench_action_request(
        {
            "type": "LEAF_WORKBENCH_ACTION_REQUEST",
            "payload": {
                "capability_id": "run_strategy_required_gate",
                "input_refs": {"command": "arc3_level_transfer_probe"},
            },
        }
    )

    assert route["route"] == "parent_kernel"
    assert route["status"] == "ok"


def test_adapter_registered_local_workbench_capability_routes_to_in_turn_cli() -> None:
    route = route_visible_workbench_action_request(
        {
            "type": "LEAF_WORKBENCH_ACTION_REQUEST",
            "payload": {
                "capability_id": "mine_worldmodel_global_carrier_selectors_from_observable_context",
            },
        }
    )

    assert route["route"] == "in_turn_cli"
    assert route["status"] == "ok"
    assert route["authority"] == "pure_diagnostic"
    assert route["suggested_command"][-2:] == ["--source", "-"]


def test_score_candidate_delta_routes_to_in_turn_cli() -> None:
    route = route_visible_workbench_action_request(
        {
            "type": "LEAF_WORKBENCH_ACTION_REQUEST",
            "payload": {"capability_id": "score_worldmodel_candidate_delta"},
        }
    )

    assert route["route"] == "in_turn_cli"
    assert route["status"] == "ok"
    assert route["authority"] == "scorer"
    assert "visible_workbench_cli" in " ".join(route["suggested_command"])


def test_join_lowerable_selectors_routes_to_in_turn_cli() -> None:
    route = route_visible_workbench_action_request(
        {
            "type": "LEAF_WORKBENCH_ACTION_REQUEST",
            "payload": {"capability_id": "join_lowerable_selectors"},
        }
    )

    assert route["route"] == "in_turn_cli"
    assert route["status"] == "ok"
    assert route["authority"] == "pure_diagnostic"


def test_record_only_workbench_capability_is_not_routed_as_parent_action() -> None:
    route = route_visible_workbench_action_request(
        {
            "type": "LEAF_WORKBENCH_ACTION_REQUEST",
            "payload": {"capability_id": "inspect_worldmodel_patch_base"},
        }
    )

    assert route["route"] == "invalid_action_request"
    assert route["status"] == "fail"


def test_worldmodel_workbench_registry_parity_gate_passes() -> None:
    validate_worldmodel_leaf_workbench_registry()
