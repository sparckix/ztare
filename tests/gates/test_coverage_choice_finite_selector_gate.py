from ztare.gates.coverage_choice_finite_selector_gate import (
    REQUIRED_FIELDS,
    run_coverage_choice_finite_selector_gate,
)


def test_coverage_choice_finite_selector_advisory_mode_passes_incomplete() -> None:
    result = run_coverage_choice_finite_selector_gate({
        "target_family": "L3A target prefix",
        "coverage_label_only": "coverage exists",
    })

    assert result["passed"] is True
    assert result["complete"] is False
    assert result["weak_substitutes_present"] == ["coverage_label_only"]


def test_coverage_choice_finite_selector_weak_substitute_is_advisory() -> None:
    result = run_coverage_choice_finite_selector_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "target_membership_label_only": "confuser only",
    }, enforce_block=True)

    assert result["passed"] is True
    assert result["complete"] is True
    assert result["weak_substitutes_present"] == ["target_membership_label_only"]


def test_coverage_choice_finite_selector_hard_violation_blocks() -> None:
    result = run_coverage_choice_finite_selector_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "witness_not_event_to_badnode": "not the displayed event map",
    }, enforce_block=True)

    assert result["passed"] is False
    assert result["complete"] is False
    assert result["hard_violations_present"] == ["witness_not_event_to_badnode"]


def test_coverage_choice_finite_selector_falsey_is_exact_not_prefix() -> None:
    result = run_coverage_choice_finite_selector_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "coverage_packet": "missing because the stronger packet is pending",
    }, enforce_block=True)

    assert result["passed"] is True
    assert result["complete"] is True
    assert result["missing_fields"] == []
