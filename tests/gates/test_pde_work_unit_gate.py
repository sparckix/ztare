from ztare.research_director.pde_work_unit_gate import (
    validate_pde_work_units,
)


def _estimate(label: str) -> dict:
    return {
        "type": "estimate_derivation",
        "target": label,
        "normalized_variables": {"r_Q": 1},
        "target_inequality": "c <= A",
        "terms": {"A": "positive carrier"},
        "proof_steps": ["decompose", "estimate"],
        "first_failed_line": "line 2",
        "conclusion": "fails at exchange rate",
    }


def test_terminal_gap_without_pde_work_units_fails() -> None:
    result = validate_pde_work_units({
        "terminal_verdict": "MISSING_HYPOTHESIS",
        "work_units": [],
    })

    assert result["passed"] is False
    violation_types = {v["type"] for v in result["violations"]}
    assert "too_few_estimate_derivations" in violation_types
    assert "too_few_falsifier_packets" in violation_types
    assert "missing_shrink_or_literature_match" in violation_types


def test_terminal_gap_with_required_pde_work_units_passes() -> None:
    result = validate_pde_work_units({
        "terminal_verdict": "OPEN",
        "work_units": [
            _estimate("attempt_1"),
            _estimate("attempt_2"),
            {
                "type": "falsifier_packet",
                "name": "nested_reuse",
                "amplitude": "1/r",
                "support_volume": "r^5",
                "frequency": "N",
                "satisfies_hypotheses": True,
                "violates_conclusion": True,
                "kills": ["freshness"],
                "survives": ["energy"],
            },
            {
                "type": "smaller_theorem",
                "statement": "same-carrier positive flux freshness",
                "smaller_than_target": {"fewer_carriers": True},
                "proof_obligation": "prove monotone reserve drop",
                "falsifier_class_excluded": "nested_reuse",
                "residual_normal_form": "same_carrier_reuse",
            },
        ],
    })

    assert result["passed"] is True



def _positive_constructor() -> dict:
    return {
        "type": "positive_constructor_attempt",
        "source_law": "high-interface floor law",
        "target_carrier": "boundary-paid event",
        "bounded_or_selectable_variable": "interface share",
        "constructor_map": "select event inside high-interface carrier",
        "nearest_confuser": "global bounded-share patch",
        "first_failed_line_or_success": "conditional law pays boundary share",
        "conclusion": "constructor attempted",
    }


def test_constructive_turn_due_requires_positive_constructor_attempt() -> None:
    result = validate_pde_work_units({
        "terminal_verdict": "IN_PROGRESS",
        "conditional_source_law": "high-interface floor law",
        "bounded_or_selectable_variable": "interface share",
        "target_carrier": "boundary-paid event",
        "work_units": [_estimate("obstruction_only")],
    })

    assert result["passed"] is False
    assert result["constructive_turn_due"] is True
    assert {v["type"] for v in result["violations"]} == {
        "missing_positive_constructor_attempt"
    }


def test_constructive_turn_due_passes_with_positive_constructor_attempt() -> None:
    result = validate_pde_work_units({
        "terminal_verdict": "IN_PROGRESS",
        "constructive_turn_signals": {
            "conditional_source_law": "high-interface floor law",
            "target_carrier": "boundary-paid event",
            "bounded_or_selectable_variable": "interface share",
        },
        "work_units": [_positive_constructor()],
    })

    assert result["passed"] is True
    assert result["counts"]["positive_constructor_attempt"] == 1


def test_constructive_turn_not_due_when_packet_already_kills_source() -> None:
    result = validate_pde_work_units({
        "terminal_verdict": "IN_PROGRESS",
        "conditional_source_law": "high-interface floor law",
        "bounded_or_selectable_variable": "interface share",
        "target_carrier": "boundary-paid event",
        "immediate_packet_kill": "low-interface surplus packet",
        "work_units": [_estimate("packet_killed")],
    })

    assert result["passed"] is True
    assert result["constructive_turn_due"] is False

def test_constructive_turn_inferred_from_work_unit_text():
    payload = {
        "terminal_verdict": "MISSING_HYPOTHESIS",
        "work_units": [
            {
                "type": "estimate_derivation",
                "target": "HighInterfaceConditionalBoundaryShareSource",
                "normalized_variables": {"S": "conditional bounded share on a source-fixed high-interface law"},
                "target_inequality": "conditional law produces a restricted selected event",
                "terms": ["bounded share", "selected event"],
                "proof_steps": ["The positive conditional constructor directly inhabits the restricted carrier."],
                "first_failed_line": "conditional mean-share bias remains unsourced",
                "conclusion": "positive conditional constructor shifts the burden to a conditional bias theorem",
            },
            {
                "type": "estimate_derivation",
                "target": "conditional bias",
                "normalized_variables": {},
                "target_inequality": "E_H S > a",
                "terms": ["conditional law"],
                "proof_steps": ["No source theorem supplies the bias."],
                "first_failed_line": "bias missing",
                "conclusion": "open",
            },
            {
                "type": "falsifier_packet",
                "name": "conditional_share_confuser",
                "amplitude": "global surplus outside H",
                "support_volume": "positive outside support",
                "frequency": "threshold source",
                "satisfies_hypotheses": ["global boundary share"],
                "violates_conclusion": ["no conditional high-interface selected event"],
                "kills": ["global-to-conditional lift"],
                "survives": ["source-fixed conditional mean-share surplus"],
            },
            {
                "type": "smaller_theorem",
                "statement": "conditional source law plus bounded share produces selected event",
                "smaller_than_target": "selector only",
                "proof_obligation": "prove conditional bias",
                "falsifier_class_excluded": "global surplus outside H",
                "residual_normal_form": "conditional bias missing",
            },
        ],
    }

    result = validate_pde_work_units(payload)
    assert result["constructive_turn_due"] is True
    assert result["passed"] is False
    assert "missing_positive_constructor_attempt" in {v["type"] for v in result["violations"]}

