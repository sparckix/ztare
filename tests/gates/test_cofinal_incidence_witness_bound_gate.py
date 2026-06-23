from ztare.gates.cofinal_incidence_witness_bound_gate import (
    REQUIRED_FIELDS,
    run_cofinal_incidence_witness_bound_gate,
)


def test_cofinal_incidence_witness_bound_advisory_mode_passes_incomplete() -> None:
    result = run_cofinal_incidence_witness_bound_gate({
        "target_family": "selected bad nodes",
        "event_cover_prop_only": "exists event",
    })

    assert result["passed"] is True
    assert result["complete"] is False
    assert result["weak_substitutes_present"] == ["event_cover_prop_only"]


def test_cofinal_incidence_witness_bound_weak_substitute_is_advisory() -> None:
    result = run_cofinal_incidence_witness_bound_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "bound_on_nonchosen_witness": "confuser only",
    }, enforce_block=True)

    assert result["passed"] is True
    assert result["complete"] is True
    assert result["weak_substitutes_present"] == ["bound_on_nonchosen_witness"]


def test_cofinal_incidence_witness_bound_hard_violation_blocks() -> None:
    result = run_cofinal_incidence_witness_bound_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "bound_applies_to_nonchosen_witness": "wrong witness",
    }, enforce_block=True)

    assert result["passed"] is False
    assert result["complete"] is False
    assert result["hard_violations_present"] == [
        "bound_applies_to_nonchosen_witness"
    ]


def test_cofinal_incidence_witness_bound_falsey_is_exact_not_prefix() -> None:
    result = run_cofinal_incidence_witness_bound_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "cofinal_selected_tree_incidence_receipt":
            "missing because receipt theorem is pending",
    }, enforce_block=True)

    assert result["passed"] is True
    assert result["missing_fields"] == []
