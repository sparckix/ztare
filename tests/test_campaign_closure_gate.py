from __future__ import annotations

import pytest

from ztare.leanmill.campaign_closure_gate import (
    GENERALIZATION_ADJUDICATION_SCHEMA,
    LINEAGE_DISPOSITION_SCHEMA,
    TASK_DISCHARGE_AUTHORITY_RECEIPT_SCHEMA,
    assert_campaign_closable,
    build_generalization_residual_receipt,
    campaign_closure_gate,
    lineage_disposition_from_terminal_transition,
)
from ztare.leanmill.theory_ir import content_hash


def _budget_stop() -> dict:
    core = {
        "schema": "leanmill.budget_stop_receipt.v1",
        "reason": "test_budget_boundary",
        "budget_digest": "budget:test",
        "elapsed_ms": 1,
        "usage": {},
        "phase_usage": {},
        "outstanding_reservations": [],
        "attempt_id": "attempt:test",
        "context_hash": "context:test",
        "last_information_observation": None,
    }
    return {**core, "receipt_sha256": content_hash(core)}


def _disposition(lineage_id: str) -> dict:
    return lineage_disposition_from_terminal_transition(
        context_hash="context:test",
        lineage_id=lineage_id,
        transition_receipt=_budget_stop(),
    )


def test_terminal_gate_requires_every_frozen_lineage_disposition() -> None:
    receipt = campaign_closure_gate(
        context_hash="context:test",
        frozen_lineage_ids=("lineage:0", "lineage:1"),
        lineage_dispositions=(_disposition("lineage:0"),),
    )

    assert receipt["ready"] is False
    assert receipt["missing_lineage_disposition_ids"] == ["lineage:1"]
    with pytest.raises(ValueError, match="lineage:1"):
        assert_campaign_closable(
            context_hash="context:test",
            frozen_lineage_ids=("lineage:0", "lineage:1"),
            lineage_dispositions=(_disposition("lineage:0"),),
        )


def test_proved_finite_witness_requires_generalization_adjudication() -> None:
    residual = build_generalization_residual_receipt(
        context_hash="context:test",
        lineage_id="lineage:0",
        witness_id="model:fin3",
        claim_id="claim:reconstruction-counterexample",
        evidence_refs=("finite-witness-replay:passed",),
    )
    blocked = campaign_closure_gate(
        context_hash="context:test",
        frozen_lineage_ids=("lineage:0",),
        lineage_dispositions=(_disposition("lineage:0"),),
        generalization_residuals=(residual,),
    )
    assert blocked["ready"] is False
    assert blocked["unadjudicated_generalization_residual_ids"] == [
        residual["residual_id"]
    ]

def test_terminal_gate_rejects_hash_valid_unregistered_disposition() -> None:
    core = {
        "schema": LINEAGE_DISPOSITION_SCHEMA,
        "context_hash": "context:test",
        "lineage_id": "lineage:0",
        "terminal_state": "objective_discharged",
        "evidence_refs": ["planted:opaque"],
        "authority": "planted_task_adjudicator",
        "authority_receipt": {"receipt_sha256": "planted"},
    }
    planted = {**core, "receipt_sha256": content_hash(core)}

    with pytest.raises(ValueError, match="authority is not registered"):
        campaign_closure_gate(
            context_hash="context:test",
            frozen_lineage_ids=("lineage:0",),
            lineage_dispositions=(planted,),
        )


def test_terminal_gate_rejects_hash_valid_registered_authority_with_planted_origin() -> None:
    origin_core = {
        "schema": TASK_DISCHARGE_AUTHORITY_RECEIPT_SCHEMA,
        "theory_program": {},
        "discharge_bundle": {},
        "discharge_consumption": {},
        "boundary_result": {},
        "authority": "registered_task_adjudicator_replay",
    }
    origin = {**origin_core, "receipt_sha256": content_hash(origin_core)}
    core = {
        "schema": LINEAGE_DISPOSITION_SCHEMA,
        "context_hash": "context:test",
        "lineage_id": "lineage:0",
        "terminal_state": "objective_discharged",
        "evidence_refs": ["planted:opaque"],
        "authority": "validated_theory_task_discharge_consumption",
        "authority_receipt": origin,
    }
    planted = {**core, "receipt_sha256": content_hash(core)}

    with pytest.raises((KeyError, ValueError), match="program|identity|required"):
        campaign_closure_gate(
            context_hash="context:test",
            frozen_lineage_ids=("lineage:0",),
            lineage_dispositions=(planted,),
        )


def test_terminal_gate_rejects_hash_valid_generalization_with_opaque_origin() -> None:
    residual = build_generalization_residual_receipt(
        context_hash="context:test",
        lineage_id="lineage:0",
        witness_id="model:fin3",
        claim_id="claim:test",
        evidence_refs=("finite-witness:passed",),
    )
    origin_core = {
        "schema": TASK_DISCHARGE_AUTHORITY_RECEIPT_SCHEMA,
        "theory_program": {},
        "discharge_bundle": {},
        "discharge_consumption": {},
        "boundary_result": {},
        "authority": "registered_task_adjudicator_replay",
    }
    origin = {**origin_core, "receipt_sha256": content_hash(origin_core)}
    core = {
        "schema": GENERALIZATION_ADJUDICATION_SCHEMA,
        "context_hash": "context:test",
        "lineage_id": "lineage:0",
        "residual_id": residual["residual_id"],
        "residual_receipt_sha256": residual["receipt_sha256"],
        "terminal_state": "refuted_general",
        "evidence_refs": ["review:planted"],
        "authority": "campaign_owned_governed_formal_counterexample_adjudicator",
        "authority_receipt": origin,
    }
    planted = {**core, "receipt_sha256": content_hash(core)}

    with pytest.raises((KeyError, ValueError), match="program|identity|required"):
        campaign_closure_gate(
            context_hash="context:test",
            frozen_lineage_ids=("lineage:0",),
            lineage_dispositions=(_disposition("lineage:0"),),
            generalization_residuals=(residual,),
            generalization_adjudications=(planted,),
        )
