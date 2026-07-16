from __future__ import annotations

import pytest

from ztare.common.task_discharge import TaskDischargeContract
from ztare.leanmill.theory_adapter_registry import adjudicate_theory_adapter_task
from ztare.leanmill.theory_ir import content_hash
from ztare.leanmill.theory_program import (
    THEORY_PROGRAM_V2,
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


def test_program_tasks_extend_without_changing_the_v1_wire_contract():
    legacy = _program("lineage:legacy", ("a",), ("p",))
    assert set(legacy.to_json()) == {
        "schema", "campaign_id", "lineage_id", "context_hash", "context_epoch",
        "presentation_formula_ids", "prediction_formula_ids",
        "selection_receipt_id", "authority", "program_id",
    }
    lowered = legacy.executable_task_contracts()
    assert len(lowered) == 1
    assert lowered[0].parameters["target_formula_id"] == "p"

    authored = TaskDischargeContract(
        contract_id="task:classification",
        adjudicator_id="test.classification.v1",
        lifecycle_scope="campaign:test",
        owner="lineage:new",
        parameters={"partition_ref": "candidate:partition"},
    )
    extended = TheoryProgram(
        campaign_id="campaign:test",
        lineage_id="lineage:new",
        context_hash="context:test",
        context_epoch=0,
        presentation_formula_ids=("a",),
        prediction_formula_ids=(),
        selection_receipt_id="receipt:new",
        schema=THEORY_PROGRAM_V2,
        task_discharge_contracts=(authored,),
    )
    assert TheoryProgram.from_json(extended.to_json()) == extended
    assert extended.executable_task_contracts() == (authored,)


def test_formula_prediction_flows_through_registered_task_adjudicator():
    program = _program("lineage:e2e", ("a", "b"), ("p",))
    contract = program.executable_task_contracts()[0]
    governed_core = {
        "schema": "leanmill.governed_consequence_attempt.v1",
        "task_id": "lean-task:p",
        "status": "proved_attributed",
    }
    governed = {**governed_core, "receipt_sha256": content_hash(governed_core)}
    row = {
        "candidate_kind": "theory_program",
        "premise_formula_ids": ["a", "b"],
        "target_formula_id": "p",
        "program_prediction_status": "kernel_verified_attributed",
        "lean": {"status": "proved_attributed", "governed_attempt": governed},
    }
    boundary_core = {
        "schema": "leanmill.frontier_boundary_result.v1",
        "context_hash": "context:test",
        "query_results": [row],
        "stop_reason": "campaign_finished",
        "next_epoch_proposal": None,
    }
    boundary = {**boundary_core, "result_sha256": content_hash(boundary_core)}

    receipt = adjudicate_theory_adapter_task(
        "generic_fol_finite.v1", contract, boundary_result=boundary
    )
    assert receipt.status == "discharged"
    assert receipt.contract_sha256 == contract.sha256
    assert receipt.evidence_refs == (
        governed["receipt_sha256"], boundary["result_sha256"]
    )

    row["program_prediction_status"] = "unresolved"
    row["lean"] = {"status": "unresolved"}
    boundary_core["query_results"] = [row]
    boundary = {**boundary_core, "result_sha256": content_hash(boundary_core)}
    assert adjudicate_theory_adapter_task(
        "generic_fol_finite.v1", contract, boundary_result=boundary
    ).status == "open"


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
