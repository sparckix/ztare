from __future__ import annotations

from typing import Any
from pathlib import Path

from ztare.common.control_work_items import (
    META_HARDENING_LANE,
    SKILL_ACQUISITION_LANE,
    RunContext,
    WorkItemRole,
    classify_control_work_item,
    should_block,
)


StrategyCardRole = WorkItemRole

_TERMINAL_STRATEGY_DISPOSITIONS = frozenset(
    {
        "accepted",
        "rejected",
        "killed",
        "rejected_unlowerable",
        "observed",
        "survived",
    }
)


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


def is_active_strategy_card(card: dict[str, Any]) -> bool:
    """Whether a Strategy experiment still owns a downstream obligation."""
    return str(card.get("disposition") or "open").strip() not in (
        _TERMINAL_STRATEGY_DISPOSITIONS
    )


def active_strategy_cards(path: str | Path) -> list[dict[str, Any]]:
    """Nonterminal Strategy cards, newest work order first."""
    from ztare.common.operator_proposal_contract import open_cards

    return list(
        reversed(
            [card for card in open_cards(path) if is_active_strategy_card(card)]
        )
    )


def blocking_strategy_cards(
    cards: list[dict[str, Any]],
    *,
    context: RunContext | None = None,
    project_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Return the single Strategy work order that owns the active run frontier.

    An identity-bound workbench task is a newer work-order object than an
    unbound Strategy ledger row.  While such a task is active, a Strategy card
    may block only when it names the same task or carrier frontier.  This keeps
    historical case memory visible without letting it veto a different
    evidence epoch.
    """

    ctx = context or RunContext()
    eligible = [card for card in cards if should_block(strategy_card_role(card), ctx)]
    if project_dir is not None and eligible:
        project = Path(project_dir)
        try:
            import json

            from ztare.common.leaf_workbench_executor import (
                active_workbench_task_capability_scope,
            )

            scope, task = active_workbench_task_capability_scope(project)
            if scope:
                payload = json.loads(
                    (project / "workspace" / "latest_harness_weakness.json").read_text(
                        encoding="utf-8"
                    )
                )
                frontier = (
                    payload.get("active_frontier")
                    if isinstance(payload.get("active_frontier"), dict)
                    else {}
                )
                task_id = str(task.get("task_id") or "").strip()
                candidate_sha = str(
                    frontier.get("candidate_sha") or payload.get("candidate_sha") or ""
                ).strip()
                eligible = [
                    card
                    for card in eligible
                    if _card_matches_workbench_frontier(
                        card,
                        task_id=task_id,
                        candidate_sha=candidate_sha,
                    )
                ]
        except (OSError, ValueError, TypeError):
            pass
    # One run has one work-order identity. Older matching cards stay auditable
    # backlog instead of becoming an ever-growing candidate veto.
    return eligible[:1]


def _card_matches_workbench_frontier(
    card: dict[str, Any],
    *,
    task_id: str,
    candidate_sha: str,
) -> bool:
    plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
    frontier = card.get("active_frontier")
    if not isinstance(frontier, dict):
        frontier = plan.get("active_frontier") if isinstance(plan.get("active_frontier"), dict) else {}
    card_task = str(
        card.get("workbench_task_id")
        or card.get("task_id")
        or plan.get("workbench_task_id")
        or plan.get("task_id")
        or ""
    ).strip()
    card_sha = str(
        frontier.get("candidate_sha")
        or card.get("candidate_sha")
        or plan.get("candidate_sha")
        or ""
    ).strip()
    task_matches = bool(task_id and card_task and task_id == card_task)
    sha_matches = bool(
        candidate_sha
        and card_sha
        and (candidate_sha.startswith(card_sha) or card_sha.startswith(candidate_sha))
    )
    return task_matches or sha_matches
