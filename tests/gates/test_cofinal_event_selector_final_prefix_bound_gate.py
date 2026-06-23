from ztare.gates.cofinal_event_selector_final_prefix_bound_gate import (
    REQUIRED_FIELDS,
    run_cofinal_event_selector_final_prefix_bound_gate,
)


def test_cofinal_event_selector_final_prefix_bound_advisory_mode_passes_incomplete() -> None:
    result = run_cofinal_event_selector_final_prefix_bound_gate({
        "target_family": "selected bad nodes",
    })

    assert result["passed"] is True
    assert result["complete"] is False
    assert "ordinary_coverage_packet" in result["missing_fields"]


def test_cofinal_event_selector_final_prefix_bound_weak_substitute_is_advisory() -> None:
    result = run_cofinal_event_selector_final_prefix_bound_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "explicit_subtype_witness_only": "subtype witness",
    }, enforce_block=True)

    assert result["passed"] is True
    assert result["complete"] is True
    assert result["weak_substitutes_present"] == ["explicit_subtype_witness_only"]


def test_cofinal_event_selector_final_prefix_bound_hard_violation_blocks() -> None:
    result = run_cofinal_event_selector_final_prefix_bound_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "bound_applies_to_nonselector": "wrong witness",
    }, enforce_block=True)

    assert result["passed"] is False
    assert result["complete"] is False
    assert result["hard_violations_present"] == ["bound_applies_to_nonselector"]


def test_cofinal_event_selector_final_prefix_bound_falsey_is_exact_not_prefix() -> None:
    result = run_cofinal_event_selector_final_prefix_bound_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "cofinal_event_selector": "missing because selector theorem is pending",
    }, enforce_block=True)

    assert result["passed"] is True
    assert result["missing_fields"] == []


def test_cofinal_event_selector_final_prefix_bound_exact_falsey_blocks() -> None:
    result = run_cofinal_event_selector_final_prefix_bound_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "cofinal_event_selector": "missing",
    }, enforce_block=True)

    assert result["passed"] is False
    assert result["missing_fields"] == ["cofinal_event_selector"]
