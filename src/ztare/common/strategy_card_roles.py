from __future__ import annotations

from typing import Any

from ztare.common.control_work_items import (
    META_HARDENING_LANE,
    SKILL_ACQUISITION_LANE,
    RunContext,
    WorkItemRole,
    classify_control_work_item,
    should_block,
)


StrategyCardRole = WorkItemRole


def strategy_card_role(card: dict[str, Any]) -> WorkItemRole:
    return classify_control_work_item({"source_type": "strategy_experiment", **card})


def strategy_card_lane(card: dict[str, Any]) -> str:
    return strategy_card_role(card).lane


def strategy_card_blocks_context(card: dict[str, Any], context: RunContext | None = None) -> bool:
    return should_block(strategy_card_role(card), context)


def is_skill_acquisition_card(card: dict[str, Any]) -> bool:
    return strategy_card_role(card).lane == SKILL_ACQUISITION_LANE


def is_meta_hardening_card(card: dict[str, Any]) -> bool:
    return strategy_card_role(card).lane == META_HARDENING_LANE
