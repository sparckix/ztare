from __future__ import annotations

import pytest

from ztare.leanmill.theory_program import (
    TheoryProgram,
    compare_host_isolated_theory_programs,
    derive_lineage_id,
)


def _program(lineage: str, hypotheses: tuple[str, ...], predictions: tuple[str, ...]):
    return TheoryProgram(
        campaign_id="campaign:test",
        lineage_id=lineage,
        context_hash="context:test",
        context_epoch=0,
        presentation_formula_ids=hypotheses,
        prediction_formula_ids=predictions,
        selection_receipt_id="receipt:test:" + lineage,
    )


def test_lineage_identity_is_stable_across_context_epochs():
    lineage = derive_lineage_id(
        campaign_id="campaign:test", attempt_id="attempt:test", branch=2
    )
    assert lineage == derive_lineage_id(
        campaign_id="campaign:test", attempt_id="attempt:test", branch=2
    )

    first = TheoryProgram(
        campaign_id="campaign:test",
        lineage_id=lineage,
        context_hash="context:0",
        context_epoch=0,
        presentation_formula_ids=("f0",),
        prediction_formula_ids=("p0",),
        selection_receipt_id="receipt:0",
    )
    successor = TheoryProgram(
        campaign_id="campaign:test",
        lineage_id=lineage,
        context_hash="context:1",
        context_epoch=1,
        presentation_formula_ids=("f0", "f1"),
        prediction_formula_ids=("p1",),
        selection_receipt_id="receipt:1",
    )
    assert first.lineage_id == successor.lineage_id
    assert first.program_id != successor.program_id

    assert TheoryProgram.from_json(first.to_json()) == first
    tampered = first.to_json()
    tampered["lineage_id"] = "lineage:tampered"
    with pytest.raises(ValueError, match="digest"):
        TheoryProgram.from_json(tampered)


def test_host_isolated_programs_cross_pollinate_only_as_fresh_replay_proposal():
    left = _program("lineage:left", ("a", "shared"), ("p", "q"))
    right = _program("lineage:right", ("b", "shared"), ("q", "r"))

    comparison = compare_host_isolated_theory_programs((left, right))

    assert comparison["common_hypothesis_ids"] == ["shared"]
    assert comparison["common_prediction_ids"] == ["q"]
    assert comparison["lineage_unique_hypothesis_ids"]["lineage:left"] == ["a"]
    assert comparison["late_synthesis_candidate"]["status"] == (
        "proposal_only_requires_fresh_context_replay"
    )


def test_program_comparison_rejects_shared_or_cross_context_lineages():
    left = _program("lineage:left", ("a",), ("p",))
    with pytest.raises(ValueError, match="host-isolated"):
        compare_host_isolated_theory_programs((left, left))

    crossed = TheoryProgram(
        campaign_id="campaign:test",
        lineage_id="lineage:right",
        context_hash="context:other",
        context_epoch=0,
        presentation_formula_ids=("b",),
        prediction_formula_ids=("q",),
        selection_receipt_id="receipt:right",
    )
    with pytest.raises(ValueError, match="source context"):
        compare_host_isolated_theory_programs((left, crossed))
