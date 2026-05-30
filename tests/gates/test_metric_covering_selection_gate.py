from src.ztare.gates.metric_covering_selection_gate import (
    run_metric_covering_selection_gate,
)


def test_metric_covering_selection_rejects_label_only_receipt() -> None:
    result = run_metric_covering_selection_gate({
        "source_family": "topology reconnection tents",
        "besicovitch_label": "Besicovitch packing",
        "topology_label": "vortex-line reconnection",
    })

    assert result["passed"] is True
    assert result["complete"] is False
    assert "ambient_metric_or_quasi_metric" in result["missing_fields"]
    assert any(
        v["type"] == "metric_covering_selection_replaced_by_weak_substitutes"
        for v in result["violations"]
    )


def test_metric_covering_selection_accepts_complete_receipt() -> None:
    result = run_metric_covering_selection_gate({
        "ambient_metric_or_quasi_metric": "parabolic metric on spacetime tents",
        "source_family": "topology reconnection tents",
        "scale_or_radius_function": "tent radius fixed by extractor",
        "doubling_or_besicovitch_constant": "Besicovitch constant B",
        "bounded_eccentricity_or_engulfing": "Whitney engulfing by 5Q",
        "selection_rule": "pre-payoff maximal disjoint subfamily",
        "selection_totality_or_paid_omission": "selected prefix covered or omitted children paid",
        "pre_payoff_selection_timing": "rule fixed before debit payoff",
        "same_carrier_binding": "same pressure/Duhamel carrier",
        "bounded_overlap_conclusion": "overlap <= B",
        "nested_children_policy": "parent pays nested children once",
        "discarded_or_nested_error_budget": "nested/omitted debit <= viscous error reserve",
    })

    assert result["passed"] is True
    assert result["complete"] is True
    assert result["violations"] == []


def test_metric_covering_selection_blocks_declared_nested_cascade() -> None:
    result = run_metric_covering_selection_gate(
        {
            "ambient_metric_or_quasi_metric": "parabolic metric on spacetime tents",
            "source_family": "topology reconnection tents",
            "scale_or_radius_function": "tent radius fixed by extractor",
            "doubling_or_besicovitch_constant": "Besicovitch constant B",
            "bounded_eccentricity_or_engulfing": "Whitney engulfing by 5Q",
            "selection_rule": "pre-payoff maximal disjoint subfamily",
            "selection_totality_or_paid_omission": "selected prefix covered or omitted children paid",
            "pre_payoff_selection_timing": "rule fixed before debit payoff",
            "same_carrier_binding": "same pressure/Duhamel carrier",
            "bounded_overlap_conclusion": "overlap <= B",
            "nested_children_policy": "parent pays nested children once",
            "discarded_or_nested_error_budget": "nested/omitted debit <= viscous error reserve",
            "known_non_doubling_or_nested_cascade_confuser": "dyadic nested reconnection cascade",
        },
        enforce_block=True,
    )

    assert result["passed"] is False
    assert any(
        v["type"] == "metric_covering_selection_confuser_declared"
        for v in result["violations"]
    )
