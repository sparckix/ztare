from ztare.gates.classical_choose_bound_gate import (
    REQUIRED_FIELDS,
    run_classical_choose_bound_gate,
)


def test_classical_choose_bound_advisory_mode_passes_incomplete() -> None:
    result = run_classical_choose_bound_gate({
        "target_family": "Level536",
        "some_bounded_witness_exists": "there exists an in-prefix event",
    })

    assert result["passed"] is True
    assert result["complete"] is False
    assert result["weak_substitutes_present"] == ["some_bounded_witness_exists"]


def test_classical_choose_bound_weak_substitute_is_advisory() -> None:
    result = run_classical_choose_bound_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "some_bounded_witness_exists": "confuser only",
    }, enforce_block=True)

    assert result["passed"] is True
    assert result["complete"] is True
    assert result["weak_substitutes_present"] == ["some_bounded_witness_exists"]


def test_classical_choose_bound_hard_violation_blocks() -> None:
    result = run_classical_choose_bound_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "bound_on_different_witness": "bounded alternate witness",
    }, enforce_block=True)

    assert result["passed"] is False
    assert result["complete"] is False
    assert result["hard_violations_present"] == ["bound_on_different_witness"]


def test_classical_choose_bound_falsey_is_exact_not_prefix() -> None:
    result = run_classical_choose_bound_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "choose_spec_equality": "missing would be bad, but here documented",
    }, enforce_block=True)

    assert result["passed"] is True
    assert result["complete"] is True
    assert result["missing_fields"] == []
