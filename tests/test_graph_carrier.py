from ztare.common.graph_carrier import (
    REGISTERED_GRAPH_KINDS,
    canonical_graph_kind_specs,
    validate_graph_carrier,
    validate_graph_carrier_summary,
)


def _valid_carrier() -> dict:
    return {
        "graph_id": "demo_probability_dag_v1",
        "graph_kind": "probability_dag",
        "producer": "latest_probability_dag.json",
        "source_artifacts": ["projects/demo/workspace/latest_probability_dag.json"],
        "consumer": "compute_dag_steering_context",
        "freshness_rule": "fresh when produced by the current run workspace",
        "node_count": 4,
        "edge_count": 3,
        "node_vocabulary": ["hypothesis", "gate", "open_question"],
        "edge_vocabulary": {"survives_to": "weighted directed edge"},
        "diagnostics": [
            {
                "method": "edge_weight_times_probability",
                "baseline": "prior iteration ordering",
                "result_summary": "open_question_2 became the highest urgency node",
            }
        ],
        "noise_filter": "drop stale nodes from prior project slug",
        "decision_receipt": {
            "effect": "strategy_change",
            "selected_next_discriminator": "test open_question_2 before new mutations",
        },
        "library_anchor": "standard library JSON plus local DAG parser",
        "literature_anchor": "directed acyclic graph scheduling and dependency analysis",
    }


def test_canonical_graph_kind_specs_cover_registered_kinds() -> None:
    specs = canonical_graph_kind_specs()
    assert set(specs) == set(REGISTERED_GRAPH_KINDS)
    assert specs["constraint_basin_graph"]["status"] == "generic_after_adapter"
    assert specs["source_claim_graph"]["status"] == "generic_now"


def test_validate_graph_carrier_accepts_complete_strategy_change() -> None:
    result = validate_graph_carrier(_valid_carrier())
    assert result.ok
    assert result.errors == []


def test_validate_graph_carrier_summary_accepts_compact_trace_row() -> None:
    carrier = _valid_carrier()
    result = validate_graph_carrier_summary(
        {
            "graph_id": carrier["graph_id"],
            "graph_kind": carrier["graph_kind"],
            "source_artifacts": carrier["source_artifacts"],
            "node_count": carrier["node_count"],
            "edge_count": carrier["edge_count"],
            "decision_receipt": carrier["decision_receipt"],
            "validation": {"ok": True, "errors": [], "warnings": []},
        }
    )

    assert result.ok
    assert result.errors == []


def test_validate_graph_carrier_summary_rejects_forged_validation_ok() -> None:
    carrier = _valid_carrier()
    result = validate_graph_carrier_summary(
        {
            "graph_id": carrier["graph_id"],
            "graph_kind": carrier["graph_kind"],
            "source_artifacts": carrier["source_artifacts"],
            "node_count": carrier["node_count"],
            "edge_count": carrier["edge_count"],
            "decision_receipt": {"effect": "strategy_change"},
            "validation": {"ok": True, "errors": [], "warnings": []},
        }
    )

    assert not result.ok
    assert any("strategy_change receipt" in error for error in result.errors)


def test_validate_graph_carrier_summary_requires_bound_source_artifacts() -> None:
    carrier = _valid_carrier()
    result = validate_graph_carrier_summary(
        {
            "graph_id": carrier["graph_id"],
            "graph_kind": carrier["graph_kind"],
            "source_artifacts": [],
            "node_count": carrier["node_count"],
            "edge_count": carrier["edge_count"],
            "decision_receipt": carrier["decision_receipt"],
            "validation": {"ok": True, "errors": [], "warnings": []},
        }
    )

    assert not result.ok
    assert "source_artifacts must be a non-empty list" in result.errors


def test_validate_graph_carrier_rejects_metric_without_decision_effect() -> None:
    carrier = _valid_carrier()
    carrier["decision_receipt"] = {"effect": "strategy_change"}
    result = validate_graph_carrier(carrier)
    assert not result.ok
    assert any("strategy_change receipt" in error for error in result.errors)


def test_validate_graph_carrier_accepts_no_action_with_reason() -> None:
    carrier = _valid_carrier()
    carrier["decision_receipt"] = {
        "effect": "no_strategy_change",
        "reason": "diagnostic matched the existing route and added no discriminator",
    }
    result = validate_graph_carrier(carrier)
    assert result.ok


def test_validate_graph_carrier_requires_rationale_for_unregistered_kind() -> None:
    carrier = _valid_carrier()
    carrier["graph_kind"] = "custom_graph"
    result = validate_graph_carrier(carrier)
    assert not result.ok
    assert any("unregistered" in error for error in result.errors)

    carrier["new_kind_rationale"] = "temporary substrate-private extraction under review"
    result = validate_graph_carrier(carrier)
    assert result.ok
    assert any("unregistered graph_kind" in warning for warning in result.warnings)
