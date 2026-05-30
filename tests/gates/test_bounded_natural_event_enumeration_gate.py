from src.ztare.gates.bounded_natural_event_enumeration_gate import (
    REQUIRED_FIELDS,
    run_bounded_natural_event_enumeration_gate,
)


def test_bounded_natural_event_enumeration_advisory_mode_passes_incomplete() -> None:
    result = run_bounded_natural_event_enumeration_gate({
        "target_family": "selected bad nodes",
        "coverage_prop_only": "coverage exists",
    })

    assert result["passed"] is True
    assert result["complete"] is False
    assert result["weak_substitutes_present"] == ["coverage_prop_only"]


def test_bounded_natural_event_enumeration_weak_substitute_is_advisory() -> None:
    result = run_bounded_natural_event_enumeration_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "fin_enumeration_assumed": "confuser only",
    }, enforce_block=True)

    assert result["passed"] is True
    assert result["complete"] is True
    assert result["weak_substitutes_present"] == ["fin_enumeration_assumed"]


def test_bounded_natural_event_enumeration_hard_violation_blocks() -> None:
    result = run_bounded_natural_event_enumeration_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "missing_strict_prefix_bound": "unbounded Nat witness",
    }, enforce_block=True)

    assert result["passed"] is False
    assert result["complete"] is False
    assert result["hard_violations_present"] == ["missing_strict_prefix_bound"]


def test_bounded_natural_event_enumeration_falsey_is_exact_not_prefix() -> None:
    result = run_bounded_natural_event_enumeration_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "selected_bad_node_natural_event_enumeration":
            "missing because bounded theorem is pending",
    }, enforce_block=True)

    assert result["passed"] is True
    assert result["missing_fields"] == []
