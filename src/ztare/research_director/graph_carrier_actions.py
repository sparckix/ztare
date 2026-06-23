"""Research Director action rows derived from graph-carrier receipts."""
from __future__ import annotations

from typing import Any, Iterable

from ztare.common.graph_carrier import validate_graph_carrier_summary
from ztare.research_director.primitive_operator_cards import (
    operator_card_route_receipts,
    route_operator_cards_semantic,
)


def graph_carrier_action_rows(carriers: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Lower graph-carrier decision receipts into advisory RD action rows.

    This is a read model. It does not schedule in-loop iterations and does not
    execute out-of-loop work; it tells the RD which side of the boundary the
    graph evidence points to.
    """
    actions: list[dict[str, Any]] = []
    for carrier in carriers:
        if not isinstance(carrier, dict) or not _carrier_valid(carrier):
            continue
        receipt = carrier.get("decision_receipt")
        if not isinstance(receipt, dict):
            continue
        effect = str(receipt.get("effect") or "").strip()
        graph_kind = str(carrier.get("graph_kind") or "").strip()
        graph_id = str(carrier.get("graph_id") or "").strip()
        project = graph_id.split(":", 1)[0] if ":" in graph_id else ""

        if effect == "strategy_change":
            route_change = str(receipt.get("route_change") or "").strip()
            discriminator = str(receipt.get("selected_next_discriminator") or "").strip()
            if graph_kind == "source_claim_graph" and route_change:
                action_type = (
                    "out_of_loop_evidence_recovery"
                    if route_change.startswith("fetch or justify")
                    else "out_of_loop_source_prepare"
                )
                actions.append(
                    _with_operator_card_provenance(
                        {
                            "action_type": action_type,
                            "work_mode": "out_of_loop_prep",
                            "project": project,
                            "graph_id": graph_id,
                            "reason": route_change,
                            "recommended_actor": "research_director_or_prep_agent",
                        },
                        graph_kind=graph_kind,
                        receipt=receipt,
                    )
                )
            elif discriminator and _runtime_consumable(receipt):
                row = {
                    "action_type": "in_loop_focus_receipt",
                    "work_mode": "in_loop",
                    "project": project,
                    "graph_id": graph_id,
                    "reason": discriminator,
                    "recommended_actor": "autoresearch_loop",
                }
                gap_ids = _csv(receipt.get("selected_gap_ids"))
                targets = _csv(receipt.get("selected_targets"))
                if gap_ids:
                    row["gap_ids"] = gap_ids
                if targets:
                    row["targets"] = targets
                actions.append(
                    _with_operator_card_provenance(
                        row,
                        graph_kind=graph_kind,
                        receipt=receipt,
                    )
                )
            elif route_change:
                actions.append(
                    _with_operator_card_provenance(
                        {
                            "action_type": "graph_route_change",
                            "work_mode": "advisory",
                            "project": project,
                            "graph_id": graph_id,
                            "reason": route_change,
                            "recommended_actor": "research_director",
                        },
                        graph_kind=graph_kind,
                        receipt=receipt,
                    )
                )
        elif effect == "misleading_or_noise":
            actions.append(
                _with_operator_card_provenance(
                    {
                        "action_type": "demote_graph_signal",
                        "work_mode": "out_of_loop_review",
                        "project": project,
                        "graph_id": graph_id,
                        "reason": str(receipt.get("reason") or "graph signal marked misleading"),
                        "recommended_actor": "research_director",
                    },
                    graph_kind=graph_kind,
                    receipt=receipt,
                )
            )
    return actions


def _with_operator_card_provenance(
    row: dict[str, Any],
    *,
    graph_kind: str,
    receipt: dict[str, Any],
) -> dict[str, Any]:
    routes = _graph_operator_card_routes(graph_kind=graph_kind, receipt=receipt)
    if routes:
        row["operator_card_routes"] = routes
        row["operator_card_ids"] = _unique_card_ids(routes)
    return row


def _graph_operator_card_routes(
    *,
    graph_kind: str,
    receipt: dict[str, Any],
) -> list[dict[str, Any]]:
    context = " ".join(
        item
        for item in (
            "graph diagnostic carrier",
            "graph_diagnostic_carrier",
            "decision_receipt",
            graph_kind.replace("_", " "),
            str(receipt.get("effect") or ""),
            str(receipt.get("route_change") or ""),
            str(receipt.get("selected_next_discriminator") or ""),
            str(receipt.get("reason") or ""),
        )
        if item
    )
    routes = operator_card_route_receipts(
        route_operator_cards_semantic(context=context, top_n=4)
    )
    return [route for route in routes if route.get("card_id") == "OP-GDC-01"]


def _unique_card_ids(routes: list[dict[str, Any]]) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    for route in routes:
        card_id = str(route.get("card_id") or "").strip()
        if not card_id or card_id in seen:
            continue
        seen.add(card_id)
        ids.append(card_id)
    return ids


def _carrier_valid(carrier: dict[str, Any]) -> bool:
    return validate_graph_carrier_summary(carrier).ok


def _runtime_consumable(receipt: dict[str, Any]) -> bool:
    """Only a literal false blocks in-loop use; absent means legacy admissible."""
    return receipt.get("runtime_consumable") is not False


def _csv(value: Any) -> str:
    if not isinstance(value, list):
        return ""
    return ",".join(str(item).strip() for item in value if str(item).strip())
