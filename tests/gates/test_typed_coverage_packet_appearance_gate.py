from src.ztare.gates.typed_coverage_packet_appearance_gate import (
    REQUIRED_FIELDS,
    run_typed_coverage_packet_appearance_gate,
)


def test_typed_coverage_packet_appearance_advisory_mode_passes_incomplete() -> None:
    result = run_typed_coverage_packet_appearance_gate({
        "target_family": "L3A target prefix",
        "ordinary_coverage_only": "coverage exists",
    })

    assert result["passed"] is True
    assert result["complete"] is False
    assert result["weak_substitutes_present"] == ["ordinary_coverage_only"]


def test_typed_coverage_packet_appearance_weak_substitute_is_advisory() -> None:
    result = run_typed_coverage_packet_appearance_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "standalone_typed_appearance": "confuser only",
    }, enforce_block=True)

    assert result["passed"] is True
    assert result["complete"] is True
    assert result["weak_substitutes_present"] == ["standalone_typed_appearance"]


def test_typed_coverage_packet_appearance_hard_violation_blocks() -> None:
    result = run_typed_coverage_packet_appearance_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "typed_witness_not_in_packet": "witness is external",
    }, enforce_block=True)

    assert result["passed"] is False
    assert result["complete"] is False
    assert result["hard_violations_present"] == ["typed_witness_not_in_packet"]


def test_typed_coverage_packet_appearance_falsey_is_exact_not_prefix() -> None:
    result = run_typed_coverage_packet_appearance_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "typed_coverage_packet": "missing because stronger packet is pending",
    }, enforce_block=True)

    assert result["passed"] is True
    assert result["complete"] is True
    assert result["missing_fields"] == []
