from ztare.gates.unbounded_event_witness_prefix_bound_gate import (
    REQUIRED_FIELDS,
    run_unbounded_event_witness_prefix_bound_gate,
)


def test_unbounded_event_witness_prefix_bound_advisory_mode_passes_incomplete() -> None:
    result = run_unbounded_event_witness_prefix_bound_gate({
        "target_family": "selected bad nodes",
        "existential_event_cover_only": "exists event",
    })

    assert result["passed"] is True
    assert result["complete"] is False
    assert result["weak_substitutes_present"] == ["existential_event_cover_only"]


def test_unbounded_event_witness_prefix_bound_weak_substitute_is_advisory() -> None:
    result = run_unbounded_event_witness_prefix_bound_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "bound_on_different_witness": "confuser only",
    }, enforce_block=True)

    assert result["passed"] is True
    assert result["complete"] is True
    assert result["weak_substitutes_present"] == ["bound_on_different_witness"]


def test_unbounded_event_witness_prefix_bound_hard_violation_blocks() -> None:
    result = run_unbounded_event_witness_prefix_bound_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "bound_applies_to_different_witness": "wrong witness",
    }, enforce_block=True)

    assert result["passed"] is False
    assert result["complete"] is False
    assert result["hard_violations_present"] == [
        "bound_applies_to_different_witness"
    ]


def test_unbounded_event_witness_prefix_bound_falsey_is_exact_not_prefix() -> None:
    result = run_unbounded_event_witness_prefix_bound_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "selected_bad_node_natural_event_witness":
            "missing because cofinal receipt is pending",
    }, enforce_block=True)

    assert result["passed"] is True
    assert result["missing_fields"] == []
