from __future__ import annotations

from ztare.research_director.graph_carrier_actions import graph_carrier_action_rows


def _summary(
    *,
    graph_kind: str,
    decision_receipt: dict,
    graph_id: str = "demo:source_claim_graph",
    source_artifacts: list[str] | None = None,
    validation_ok: bool = True,
) -> dict:
    return {
        "graph_id": graph_id,
        "graph_kind": graph_kind,
        "source_artifacts": source_artifacts or ["projects/demo/workspace/source_index.json"],
        "node_count": 2,
        "edge_count": 1,
        "decision_receipt": decision_receipt,
        "validation": {
            "ok": validation_ok,
            "errors": [] if validation_ok else ["bad"],
            "warnings": [],
        },
    }


def _without_card_provenance(row: dict) -> dict:
    out = dict(row)
    assert out.pop("operator_card_ids") == ["OP-GDC-01"]
    routes = out.pop("operator_card_routes")
    assert len(routes) == 1
    assert routes[0]["card_id"] == "OP-GDC-01"
    assert routes[0]["route_mode"] in {"lexical_fallback", "semantic_atlas"}
    return out


def test_graph_carrier_actions_lower_source_claim_gap_to_out_of_loop_prep() -> None:
    rows = graph_carrier_action_rows(
        [
            _summary(
                graph_kind="source_claim_graph",
                decision_receipt={
                    "effect": "strategy_change",
                    "route_change": "fetch or justify 2 active evidence gap(s)",
                },
            )
        ]
    )

    assert [_without_card_provenance(row) for row in rows] == [
        {
            "action_type": "out_of_loop_evidence_recovery",
            "work_mode": "out_of_loop_prep",
            "project": "demo",
            "graph_id": "demo:source_claim_graph",
            "reason": "fetch or justify 2 active evidence gap(s)",
            "recommended_actor": "research_director_or_prep_agent",
        }
    ]


def test_graph_carrier_actions_keep_probability_dag_focus_in_loop() -> None:
    rows = graph_carrier_action_rows(
        [
            _summary(
                graph_id="demo:latest_probability_dag",
                graph_kind="probability_dag",
                source_artifacts=["projects/demo/latest_probability_dag.json"],
                decision_receipt={
                    "effect": "strategy_change",
                    "selected_next_discriminator": "DAG steering selected node 'n1'",
                    "runtime_consumable": True,
                },
            )
        ]
    )

    assert [_without_card_provenance(row) for row in rows] == [
        {
            "action_type": "in_loop_focus_receipt",
            "work_mode": "in_loop",
            "project": "demo",
            "graph_id": "demo:latest_probability_dag",
            "reason": "DAG steering selected node 'n1'",
            "recommended_actor": "autoresearch_loop",
        }
    ]


def test_graph_carrier_actions_keep_local_verification_gap_in_loop() -> None:
    rows = graph_carrier_action_rows(
        [
            _summary(
                graph_kind="source_claim_graph",
                decision_receipt={
                    "effect": "strategy_change",
                    "selected_next_discriminator": (
                        "resolve 1 local verification gap(s) inside the autoresearch loop"
                    ),
                    "selected_gap_ids": ["gap-a"],
                    "selected_targets": ["local_check"],
                    "runtime_consumable": True,
                },
            )
        ]
    )

    assert [_without_card_provenance(row) for row in rows] == [
        {
            "action_type": "in_loop_focus_receipt",
            "work_mode": "in_loop",
            "project": "demo",
            "graph_id": "demo:source_claim_graph",
            "reason": "resolve 1 local verification gap(s) inside the autoresearch loop",
            "recommended_actor": "autoresearch_loop",
            "gap_ids": "gap-a",
            "targets": "local_check",
        }
    ]


def test_graph_carrier_actions_lower_source_chain_gap_to_source_prepare() -> None:
    rows = graph_carrier_action_rows(
        [
            _summary(
                graph_kind="source_claim_graph",
                decision_receipt={
                    "effect": "strategy_change",
                    "route_change": "run evidence-prepare to bind evidence text to source rows",
                },
            )
        ]
    )

    assert [_without_card_provenance(row) for row in rows] == [
        {
            "action_type": "out_of_loop_source_prepare",
            "work_mode": "out_of_loop_prep",
            "project": "demo",
            "graph_id": "demo:source_claim_graph",
            "reason": "run evidence-prepare to bind evidence text to source rows",
            "recommended_actor": "research_director_or_prep_agent",
        }
    ]


def test_graph_carrier_actions_ignore_invalid_or_no_change_rows() -> None:
    rows = graph_carrier_action_rows(
        [
            _summary(
                graph_kind="source_claim_graph",
                decision_receipt={
                    "effect": "strategy_change",
                    "route_change": "fetch evidence",
                },
                validation_ok=False,
            ),
            _summary(
                graph_kind="source_claim_graph",
                decision_receipt={
                    "effect": "no_strategy_change",
                    "reason": "source/evidence chain present",
                },
            ),
        ]
    )

    assert rows == []


def test_graph_carrier_actions_reject_forged_validation_ok_without_receipt_payload() -> None:
    rows = graph_carrier_action_rows(
        [
            _summary(
                graph_kind="source_claim_graph",
                decision_receipt={"effect": "strategy_change"},
            )
        ]
    )

    assert rows == []


def test_graph_carrier_actions_reject_in_loop_receipt_marked_not_runtime_consumable() -> None:
    rows = graph_carrier_action_rows(
        [
            _summary(
                graph_id="demo:latest_probability_dag",
                graph_kind="probability_dag",
                source_artifacts=["projects/demo/latest_probability_dag.json"],
                decision_receipt={
                    "effect": "strategy_change",
                    "selected_next_discriminator": "DAG steering selected node 'n1'",
                    "runtime_consumable": False,
                },
            )
        ]
    )

    assert rows == []
