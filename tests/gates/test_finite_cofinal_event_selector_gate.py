from src.ztare.gates.finite_cofinal_event_selector_gate import (
    REQUIRED_FIELDS,
    run_finite_cofinal_event_selector_gate,
)


def test_finite_cofinal_event_selector_advisory_mode_passes_incomplete() -> None:
    result = run_finite_cofinal_event_selector_gate({
        "target_family": "selected bad nodes",
    })

    assert result["passed"] is True
    assert result["complete"] is False
    assert "ordinary_coverage_packet" in result["missing_fields"]


def test_finite_cofinal_event_selector_weak_substitute_is_advisory() -> None:
    result = run_finite_cofinal_event_selector_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "nat_selector_with_separate_bound_only": "Nat selector plus bound",
    }, enforce_block=True)

    assert result["passed"] is True
    assert result["complete"] is True
    assert result["weak_substitutes_present"] == [
        "nat_selector_with_separate_bound_only"
    ]


def test_finite_cofinal_event_selector_hard_violation_blocks() -> None:
    result = run_finite_cofinal_event_selector_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "bound_not_from_fin_codomain": "external bound",
    }, enforce_block=True)

    assert result["passed"] is False
    assert result["complete"] is False
    assert result["hard_violations_present"] == ["bound_not_from_fin_codomain"]


def test_finite_cofinal_event_selector_falsey_is_exact_not_prefix() -> None:
    result = run_finite_cofinal_event_selector_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "finite_cofinal_event_selector":
            "missing because finite selector theorem is pending",
    }, enforce_block=True)

    assert result["passed"] is True
    assert result["missing_fields"] == []


def test_finite_cofinal_event_selector_exact_falsey_blocks() -> None:
    result = run_finite_cofinal_event_selector_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "finite_cofinal_event_selector": "missing",
    }, enforce_block=True)

    assert result["passed"] is False
    assert result["missing_fields"] == ["finite_cofinal_event_selector"]
