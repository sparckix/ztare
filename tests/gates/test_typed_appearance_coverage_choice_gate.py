from ztare.gates.typed_appearance_coverage_choice_gate import (
    REQUIRED_FIELDS,
    run_typed_appearance_coverage_choice_gate,
)


def test_typed_appearance_coverage_choice_advisory_mode_passes_incomplete() -> None:
    result = run_typed_appearance_coverage_choice_gate({
        "target_family": "L3A target prefix",
        "appearance_prop_only": "appearance exists",
    })

    assert result["passed"] is True
    assert result["complete"] is False
    assert result["weak_substitutes_present"] == ["appearance_prop_only"]


def test_typed_appearance_coverage_choice_weak_substitute_is_advisory() -> None:
    result = run_typed_appearance_coverage_choice_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "opaque_coverage_choice": "confuser only",
    }, enforce_block=True)

    assert result["passed"] is True
    assert result["complete"] is True
    assert result["weak_substitutes_present"] == ["opaque_coverage_choice"]


def test_typed_appearance_coverage_choice_hard_violation_blocks() -> None:
    result = run_typed_appearance_coverage_choice_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "bare_prop_choice": "Classical.choose from Prop",
    }, enforce_block=True)

    assert result["passed"] is False
    assert result["complete"] is False
    assert result["hard_violations_present"] == ["bare_prop_choice"]


def test_typed_appearance_coverage_choice_falsey_is_exact_not_prefix() -> None:
    result = run_typed_appearance_coverage_choice_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "coverage_packet": "missing because stronger typed packet is pending",
    }, enforce_block=True)

    assert result["passed"] is True
    assert result["complete"] is True
    assert result["missing_fields"] == []
