from src.ztare.gates.explicit_cofinal_event_witness_bound_gate import (
    REQUIRED_FIELDS,
    run_explicit_cofinal_event_witness_bound_gate,
)


def test_explicit_cofinal_event_witness_bound_advisory_mode_passes_incomplete() -> None:
    result = run_explicit_cofinal_event_witness_bound_gate({
        "target_family": "selected bad nodes",
    })

    assert result["passed"] is True
    assert result["complete"] is False
    assert "ordinary_coverage_packet" in result["missing_fields"]


def test_explicit_cofinal_event_witness_bound_weak_substitute_is_advisory() -> None:
    result = run_explicit_cofinal_event_witness_bound_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "classical_choice_witness_only": "choose witness",
    }, enforce_block=True)

    assert result["passed"] is True
    assert result["complete"] is True
    assert result["weak_substitutes_present"] == ["classical_choice_witness_only"]


def test_explicit_cofinal_event_witness_bound_hard_violation_blocks() -> None:
    result = run_explicit_cofinal_event_witness_bound_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "bound_applies_to_nonexplicit_witness": "wrong witness",
    }, enforce_block=True)

    assert result["passed"] is False
    assert result["complete"] is False
    assert result["hard_violations_present"] == [
        "bound_applies_to_nonexplicit_witness"
    ]


def test_explicit_cofinal_event_witness_bound_falsey_is_exact_not_prefix() -> None:
    result = run_explicit_cofinal_event_witness_bound_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "explicit_cofinal_event_witness":
            "missing because explicit witness theorem is pending",
    }, enforce_block=True)

    assert result["passed"] is True
    assert result["missing_fields"] == []


def test_explicit_cofinal_event_witness_bound_exact_falsey_blocks() -> None:
    result = run_explicit_cofinal_event_witness_bound_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "explicit_cofinal_event_witness": "missing",
    }, enforce_block=True)

    assert result["passed"] is False
    assert result["missing_fields"] == ["explicit_cofinal_event_witness"]
