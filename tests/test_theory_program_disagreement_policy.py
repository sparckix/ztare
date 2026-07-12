from __future__ import annotations

from dataclasses import dataclass, replace

import pytest

from ztare.common.finite_incidence_context import (
    FiniteIncidenceContext,
    IncidenceProfile,
)
from ztare.leanmill.theory_ir import content_hash
from ztare.leanmill.theory_program import TheoryProgram
from ztare.leanmill.theory_program_disagreement_policy import (
    plan_theory_program_disagreement_lifts,
)


@dataclass(frozen=True)
class _Context:
    incidence: FiniteIncidenceContext

    context_hash = property(lambda self: self.incidence.context_hash)
    formula_ids = property(lambda self: self.incidence.attribute_ids)
    object_ids = property(lambda self: self.incidence.object_ids)
    complete = property(lambda _self: True)

    def closure_ids(self, formula_ids):
        return self.incidence.closure_ids(formula_ids)

    def cheap_structural_baseline(self, _presentation, _candidates):
        return None


def _context(*, unanimous: bool = False) -> _Context:
    return _Context(
        FiniteIncidenceContext(
            object_ids=("m0", "m1", "m2", "m3"),
            profiles=(
                IncidenceProfile("a", 0b0011),
                IncidenceProfile("b", 0b0101),
                IncidenceProfile("p", 0b1111 if unanimous else 0b0011),
                IncidenceProfile("q", 0b1111 if unanimous else 0b0101),
            ),
            base_mask=0b1111,
            exact=True,
            completeness_ref="test:complete",
        )
    )


def _programs(context: _Context) -> tuple[TheoryProgram, TheoryProgram]:
    common = {
        "campaign_id": "campaign:composition",
        "context_hash": context.context_hash,
        "context_epoch": 1,
    }
    return (
        TheoryProgram(
            **common,
            lineage_id="lineage:a",
            presentation_formula_ids=("a",),
            prediction_formula_ids=("p",),
            selection_receipt_id="selection:a",
        ),
        TheoryProgram(
            **common,
            lineage_id="lineage:b",
            presentation_formula_ids=("b",),
            prediction_formula_ids=("q",),
            selection_receipt_id="selection:b",
        ),
    )


def _isolation(context: _Context) -> dict[str, object]:
    core = {
        "schema": "leanmill.theory_lineage_isolation.v1",
        "context_hash": context.context_hash,
        "context_epoch": 1,
        "lineage_ids": ["lineage:a", "lineage:b"],
        "agent_identities": ["agent:a", "agent:b"],
        "shared_input_classes": ["frozen_context"],
        "withheld_between_lineages": ["action_trace"],
        "claim_boundary": "host orchestration only",
        "authority": "deterministic_host_orchestration",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def _plan(context: _Context, **kwargs):
    return plan_theory_program_disagreement_lifts(
        context,
        _programs(context),
        isolation_receipt=_isolation(context),
        **kwargs,
    )


def test_ranks_disagreement_then_proposes_full_program_lift():
    context = _context()
    result = _plan(
        context,
        query_cost_units={"p": 2.0, "q": 1.0},
        max_queries=1,
    )

    assert result["status"] == "boundary_lifts_proposed"
    assert [row["target_formula_id"] for row in result["ranked_queries"]] == [
        "q",
        "p",
    ]
    lift = result["boundary_lift_requests"][0]
    assert lift["lineage_id"] == "lineage:b"
    assert lift["priority_target_formula_id"] == "q"
    assert lift["required_boundary_target_ids"] == ["q"]
    core = {key: value for key, value in result.items() if key != "receipt_sha256"}
    assert result["receipt_sha256"] == content_hash(core)


def test_unanimous_predictions_return_an_explicit_null():
    result = _plan(_context(unanimous=True))

    assert result["status"] == "no_actionable_prediction_disagreement"
    assert result["ranked_queries"] == []
    assert result["boundary_lift_requests"] == []
    assert {
        row["query_status"] for row in result["target_evaluations"]
    } == {"excluded_unanimous_seed_prediction"}


def test_isolation_receipt_must_bind_the_committee():
    context = _context()
    receipt = _isolation(context)
    receipt["context_epoch"] = 0
    with pytest.raises(ValueError, match="isolation receipt"):
        plan_theory_program_disagreement_lifts(
            context,
            _programs(context),
            isolation_receipt=receipt,
        )


def test_isolation_receipt_may_cover_more_lineages_than_selected_committee():
    context = _context()
    receipt = _isolation(context)
    receipt["lineage_ids"] = ["lineage:a", "lineage:b", "lineage:c"]
    core = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    receipt["receipt_sha256"] = content_hash(core)

    result = plan_theory_program_disagreement_lifts(
        context,
        _programs(context),
        isolation_receipt=receipt,
    )

    assert result["status"] == "boundary_lifts_proposed"


def test_program_context_and_formula_identities_are_checked():
    context = _context()
    left, right = _programs(context)
    with pytest.raises(ValueError, match="frozen source context"):
        plan_theory_program_disagreement_lifts(
            context,
            (replace(left, context_hash="other"), right),
            isolation_receipt=_isolation(context),
        )
    with pytest.raises(ValueError, match="unknown formulas"):
        plan_theory_program_disagreement_lifts(
            context,
            (replace(left, prediction_formula_ids=("missing",)), right),
            isolation_receipt=_isolation(context),
        )
