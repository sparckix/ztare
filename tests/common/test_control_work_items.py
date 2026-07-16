from __future__ import annotations

from ztare.common.control_work_items import (
    META_HARDENING_LANE,
    SKILL_ACQUISITION_LANE,
    RunContext,
    classify_control_work_item,
    should_block,
)
from ztare.common.strategy_card_roles import is_active_strategy_card


def test_control_work_item_target_artifact_does_not_imply_meta_hardening() -> None:
    role = classify_control_work_item(
        {
            "source_type": "strategy_experiment",
            "kind": "compressed_counterexample_repair",
            "action_plan": {
                "target_artifact": "workspace/latest_transfer_probe.json",
                "required_next_gate": {
                    "command": "arc3_level_transfer_probe",
                    "success_status": "exact_local_transfer_depth",
                },
            },
        }
    )

    assert role.lane == SKILL_ACQUISITION_LANE
    assert role.target_surface == "candidate"
    assert should_block(role, RunContext(lane="skill_acquisition")) is True
    assert should_block(role, RunContext(lane="meta_hardening")) is False


def test_control_work_item_tool_synthesis_blocks_meta_hardening_not_candidate() -> None:
    role = classify_control_work_item(
        {
            "source_type": "strategy_experiment",
            "kind": "tool_synthesis",
            "action_plan": {
                "target_artifact": "src/ztare/common/briefing_pack.py",
                "target_surface": "prompt_sensor",
                "required_next_gate": {
                    "command": "tool_synthesis_gate",
                    "success_status": "compiled_tool_receipt_plus_regression_pass",
                },
            },
        }
    )

    assert role.lane == META_HARDENING_LANE
    assert role.target_surface == "prompt_sensor"
    assert should_block(role, RunContext(lane="skill_acquisition")) is False
    assert should_block(role, RunContext(lane="meta_hardening")) is True


def test_untyped_legacy_strategy_kind_cannot_default_to_candidate_blocker() -> None:
    role = classify_control_work_item(
        {
            "source_type": "strategy_experiment",
            "kind": "feedback_channel_ab",
            "action_plan": {"steps": ["compare two harness rounds"]},
        }
    )

    assert role.lane == "advisory"
    assert should_block(role, RunContext(lane="skill_acquisition")) is False


def test_strategy_lifecycle_severs_terminal_experiment_dispositions() -> None:
    assert is_active_strategy_card({"disposition": "open"}) is True
    assert is_active_strategy_card({"disposition": "blocked"}) is True
    assert is_active_strategy_card({"disposition": "observed"}) is False
    assert is_active_strategy_card({"disposition": "survived"}) is False
    assert is_active_strategy_card({"disposition": "killed"}) is False
    assert is_active_strategy_card({"disposition": "rejected_unlowerable"}) is False
