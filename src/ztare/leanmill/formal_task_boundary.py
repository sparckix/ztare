"""Typed boundary receipts for agent-authored formal counterexample tasks.

The task text and choice of formal target remain upstream agent work.  This
module joins two independent trust-boundary outputs for one frozen task:

* an independent statement-faithfulness receipt; and
* a governed, premise-attributed Lean consequence attempt.

Neither receipt is sufficient alone, and an external recovery admission is
deliberately outside this outcome algebra.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from ztare.common.task_discharge import TaskDischargeContract, TaskDischargeReceipt
from ztare.leanmill.theory_ir import content_hash


GOVERNED_FORMAL_COUNTEREXAMPLE_CAPABILITY = "governed_formal_counterexample"
GOVERNED_FORMAL_COUNTEREXAMPLE_ADJUDICATOR = (
    "leanmill.governed_formal_counterexample.v1"
)
FORMAL_TASK_FAITHFULNESS_SCHEMA = "leanmill.formal_task_faithfulness.v1"
FORMAL_TASK_BOUNDARY_RESULT_SCHEMA = "leanmill.formal_task_boundary_result.v1"
FORMALIZATION_CAMPAIGN_TASK_BOUNDARY_RESULT_SCHEMA = (
    "leanmill.formalization_campaign_task_boundary_result.v1"
)
FORMAL_TASK_ATTEMPT_OUTCOME_SCHEMA = (
    "leanmill.formal_task_campaign_attempt_outcome.v1"
)


def compile_governed_formal_counterexample_task(
    *, request: Mapping[str, Any], context: Any
) -> dict[str, Any] | None:
    """Lower only the registered generic formal-counterexample capability."""

    if request.get("adjudicator_capability") != GOVERNED_FORMAL_COUNTEREXAMPLE_CAPABILITY:
        return None
    request_core = {
        key: value for key, value in request.items() if key != "request_id"
    }
    if (
        request.get("schema") != "leanmill.theory_task_request.v1"
        or request.get("request_id")
        != "theory-task-request:" + content_hash(request_core)
        or request.get("context_hash") != getattr(context, "context_hash", None)
        or request.get("authority") != "leaf_request_host_bound"
    ):
        raise ValueError("formal-counterexample task request changed identity")
    presentations = tuple(
        str(value) for value in request.get("presentation_formula_ids") or ()
    )
    known = set(getattr(context, "formula_ids", ()))
    if (
        not presentations
        or len(set(presentations)) != len(presentations)
        or not set(presentations) <= known
        or type(request.get("context_epoch")) is not int
        or int(request["context_epoch"]) < 0
    ):
        raise ValueError("formal-counterexample task crossed its frozen presentation")
    evidence_refs = request.get("evidence_refs")
    if not isinstance(evidence_refs, list) or not evidence_refs or any(
        not str(value).strip() for value in evidence_refs
    ):
        raise ValueError("formal-counterexample task requires receipted input evidence")
    text_fields = ("goal", "observable", "kill_condition")
    if any(not str(request.get(field) or "").strip() for field in text_fields):
        raise ValueError("formal-counterexample task text cannot be empty")
    finite_residual = request.get("finite_witness_residual")
    if finite_residual is not None:
        if (
            not isinstance(finite_residual, Mapping)
            or set(finite_residual)
            != {"source_scope", "witness_id", "claim_id", "evidence_refs"}
            or finite_residual.get("source_scope") != "proved_finite_witness"
            or any(
                not str(finite_residual.get(field) or "").strip()
                for field in ("witness_id", "claim_id")
            )
            or not isinstance(finite_residual.get("evidence_refs"), list)
            or not finite_residual["evidence_refs"]
            or any(
                not str(value).strip()
                for value in finite_residual["evidence_refs"]
            )
        ):
            raise ValueError("formal-counterexample finite residual is malformed")
        generalization_residual = {
            "source_scope": "proved_finite_witness",
            "witness_id": str(finite_residual["witness_id"]),
            "claim_id": str(finite_residual["claim_id"]),
            "evidence_refs": [
                str(value) for value in finite_residual["evidence_refs"]
            ],
        }
    else:
        generalization_residual = None
    parameters = {
        "kind": "governed_formal_counterexample",
        "request_id": str(request["request_id"]),
        "context_hash": str(request["context_hash"]),
        "context_epoch": int(request["context_epoch"]),
        "presentation_formula_ids": list(presentations),
        "task_specification": {
            "goal": str(request["goal"]),
            "observable": str(request["observable"]),
            "kill_condition": str(request["kill_condition"]),
        },
        "goal_sha256": content_hash({"goal": str(request["goal"])}),
        "observable_sha256": content_hash(
            {"observable": str(request["observable"])}
        ),
        "kill_condition_sha256": content_hash(
            {"kill_condition": str(request["kill_condition"])}
        ),
        "input_evidence_refs": [str(value) for value in evidence_refs],
        "claim_scope": "task_only_pending_independent_objective_authorization",
    }
    if generalization_residual is not None:
        parameters["generalization_residual"] = generalization_residual
    return {
        "adjudicator_id": GOVERNED_FORMAL_COUNTEREXAMPLE_ADJUDICATOR,
        "parameters": parameters,
    }


def build_formal_task_faithfulness_receipt(
    contract: TaskDischargeContract,
    *,
    formal_target_id: str,
    formal_statement_sha256: str,
    reviewer_evidence_refs: Sequence[str],
    authority: str,
) -> dict[str, Any]:
    """Record an independent faithful-statement decision for one exact task."""

    parameters = _formal_task_parameters(contract)
    refs = tuple(str(value) for value in reviewer_evidence_refs if str(value).strip())
    if not all(
        str(value).strip()
        for value in (formal_target_id, formal_statement_sha256, authority)
    ) or not refs:
        raise ValueError("formal-task faithfulness requires target and review evidence")
    core = {
        "schema": FORMAL_TASK_FAITHFULNESS_SCHEMA,
        "contract_sha256": contract.sha256,
        "request_id": str(parameters["request_id"]),
        "formal_target_id": str(formal_target_id),
        "formal_statement_sha256": str(formal_statement_sha256),
        "task_goal_sha256": str(parameters["goal_sha256"]),
        "task_observable_sha256": str(parameters["observable_sha256"]),
        "verdict": "faithful",
        "reviewer_evidence_refs": list(refs),
        "authority": str(authority),
    }
    return {**core, "receipt_sha256": content_hash(core)}


def _formal_task_parameters(contract: TaskDischargeContract) -> dict[str, Any]:
    if contract.adjudicator_id != GOVERNED_FORMAL_COUNTEREXAMPLE_ADJUDICATOR:
        raise KeyError(f"unsupported formal task adjudicator: {contract.adjudicator_id}")
    parameters = dict(contract.parameters)
    required = {
        "kind",
        "request_id",
        "context_hash",
        "context_epoch",
        "presentation_formula_ids",
        "task_specification",
        "goal_sha256",
        "observable_sha256",
        "kill_condition_sha256",
        "input_evidence_refs",
        "claim_scope",
    }
    if (
        set(parameters) not in (required, required | {"generalization_residual"})
        or parameters.get("kind") != "governed_formal_counterexample"
        or parameters.get("claim_scope")
        != "task_only_pending_independent_objective_authorization"
        or type(parameters.get("context_epoch")) is not int
        or not isinstance(parameters.get("presentation_formula_ids"), list)
        or not parameters["presentation_formula_ids"]
        or not isinstance(parameters.get("task_specification"), Mapping)
        or set(parameters["task_specification"])
        != {"goal", "observable", "kill_condition"}
        or any(
            not str(parameters["task_specification"].get(field) or "").strip()
            for field in ("goal", "observable", "kill_condition")
        )
        or parameters.get("goal_sha256")
        != content_hash({"goal": parameters["task_specification"]["goal"]})
        or parameters.get("observable_sha256")
        != content_hash(
            {"observable": parameters["task_specification"]["observable"]}
        )
        or parameters.get("kill_condition_sha256")
        != content_hash(
            {"kill_condition": parameters["task_specification"]["kill_condition"]}
        )
        or not isinstance(parameters.get("input_evidence_refs"), list)
        or not parameters["input_evidence_refs"]
    ):
        raise ValueError("formal-counterexample task contract changed identity")
    residual = parameters.get("generalization_residual")
    if residual is not None and (
        not isinstance(residual, Mapping)
        or set(residual)
        != {"source_scope", "witness_id", "claim_id", "evidence_refs"}
        or residual.get("source_scope") != "proved_finite_witness"
        or any(
            not str(residual.get(field) or "").strip()
            for field in ("witness_id", "claim_id")
        )
        or not isinstance(residual.get("evidence_refs"), list)
        or not residual["evidence_refs"]
        or any(not str(value).strip() for value in residual["evidence_refs"])
    ):
        raise ValueError("formal-counterexample generalization residual changed identity")
    return parameters


def formal_task_parameters(contract: TaskDischargeContract) -> dict[str, Any]:
    """Public replay validator for executor factories owning no task semantics."""

    return _formal_task_parameters(contract)


def _verify_content_receipt(
    value: Mapping[str, Any], *, schema: str, digest_field: str = "receipt_sha256"
) -> dict[str, Any]:
    row = dict(value)
    core = {key: item for key, item in row.items() if key != digest_field}
    if row.get("schema") != schema or row.get(digest_field) != content_hash(core):
        raise ValueError(f"{schema} digest mismatch")
    return row


def _verify_faithfulness(
    contract: TaskDischargeContract, value: Mapping[str, Any]
) -> dict[str, Any]:
    parameters = _formal_task_parameters(contract)
    row = _verify_content_receipt(
        value, schema=FORMAL_TASK_FAITHFULNESS_SCHEMA
    )
    required = {
        "schema",
        "contract_sha256",
        "request_id",
        "formal_target_id",
        "formal_statement_sha256",
        "task_goal_sha256",
        "task_observable_sha256",
        "verdict",
        "reviewer_evidence_refs",
        "authority",
        "receipt_sha256",
    }
    if (
        set(row) != required
        or row.get("contract_sha256") != contract.sha256
        or row.get("request_id") != parameters["request_id"]
        or row.get("task_goal_sha256") != parameters["goal_sha256"]
        or row.get("task_observable_sha256") != parameters["observable_sha256"]
        or row.get("verdict") != "faithful"
        or not str(row.get("formal_target_id") or "")
        or not str(row.get("formal_statement_sha256") or "")
        or not str(row.get("authority") or "")
        or not isinstance(row.get("reviewer_evidence_refs"), list)
        or not row["reviewer_evidence_refs"]
    ):
        raise ValueError("formal-task faithfulness does not bind its task")
    return row


def _verify_governed_attempt(value: Mapping[str, Any]) -> dict[str, Any]:
    row = _verify_content_receipt(
        value, schema="leanmill.governed_consequence_attempt.v1"
    )
    attribution = row.get("attribution")
    if not isinstance(attribution, Mapping):
        raise ValueError("formal task lacks premise attribution")
    attribution_row = _verify_content_receipt(
        attribution, schema="leanmill.matched_consequence_attribution.v1"
    )
    arms = attribution_row.get("arms")
    if not isinstance(arms, Mapping) or not isinstance(arms.get("full"), Mapping):
        raise ValueError("formal task attribution arms are malformed")
    full = arms["full"]
    negatives = [
        arm
        for label, arm in arms.items()
        if label == "empty" or str(label).startswith("without:")
    ]
    work_receipt = row.get("work_receipt")
    formal_leg = (
        work_receipt.get("formal_leg")
        if isinstance(work_receipt, Mapping)
        else None
    )
    if (
        row.get("status") != "proved_attributed"
        or not str(row.get("task_id") or "")
        or not str(row.get("proof_text") or "").strip()
        or full.get("status") != "proved"
        or full.get("kernel_checked") is not True
        or not negatives
        or any(arm.get("status") == "proved" for arm in negatives)
        or not isinstance(formal_leg, Mapping)
        or work_receipt.get("verdict") != "completed"
        or formal_leg.get("credit_ready") is not True
    ):
        raise ValueError("formal task lacks governed attributed kernel evidence")
    return row


def build_formal_task_boundary_result(
    contract: TaskDischargeContract,
    *,
    faithfulness_receipt: Mapping[str, Any],
    governed_attempt: Mapping[str, Any],
) -> dict[str, Any]:
    """Join statement review and governed kernel evidence at the boundary."""

    parameters = _formal_task_parameters(contract)
    faithfulness = _verify_faithfulness(contract, faithfulness_receipt)
    governed = _verify_governed_attempt(governed_attempt)
    if governed["task_id"] != faithfulness["formal_target_id"]:
        raise ValueError("formal-task reviewer and kernel attempt name different targets")
    core = {
        "schema": FORMAL_TASK_BOUNDARY_RESULT_SCHEMA,
        "candidate_kind": "theory_task",
        "context_hash": str(parameters["context_hash"]),
        "contract_sha256": contract.sha256,
        "adjudicator_id": contract.adjudicator_id,
        "request_id": str(parameters["request_id"]),
        "status": "kernel_verified_attributed",
        "formal_target_id": str(faithfulness["formal_target_id"]),
        "formal_statement_sha256": str(
            faithfulness["formal_statement_sha256"]
        ),
        "faithfulness_receipt": faithfulness,
        "governed_attempt": governed,
        "authority": "frontier_boundary_formal_task_join",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def validate_formal_task_boundary_result(
    contract: TaskDischargeContract,
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate one executor output before it enters the boundary result."""

    if value.get("schema") == FORMALIZATION_CAMPAIGN_TASK_BOUNDARY_RESULT_SCHEMA:
        from ztare.leanmill.formal_task_campaign_executor import (
            validate_formalization_campaign_task_boundary_result,
        )

        return validate_formalization_campaign_task_boundary_result(
            contract, value
        )
    if value.get("schema") == FORMAL_TASK_ATTEMPT_OUTCOME_SCHEMA:
        from ztare.leanmill.formal_task_campaign_executor import (
            validate_formal_task_attempt_outcome,
        )

        return validate_formal_task_attempt_outcome(contract, value)
    parameters = _formal_task_parameters(contract)
    row = _verify_content_receipt(
        value, schema=FORMAL_TASK_BOUNDARY_RESULT_SCHEMA
    )
    required = {
        "schema",
        "candidate_kind",
        "context_hash",
        "contract_sha256",
        "adjudicator_id",
        "request_id",
        "status",
        "formal_target_id",
        "formal_statement_sha256",
        "faithfulness_receipt",
        "governed_attempt",
        "authority",
        "receipt_sha256",
    }
    if (
        set(row) != required
        or row.get("candidate_kind") != "theory_task"
        or row.get("context_hash") != parameters["context_hash"]
        or row.get("contract_sha256") != contract.sha256
        or row.get("adjudicator_id") != contract.adjudicator_id
        or row.get("request_id") != parameters["request_id"]
        or row.get("status") != "kernel_verified_attributed"
        or row.get("authority") != "frontier_boundary_formal_task_join"
    ):
        raise ValueError("formal-task boundary result crossed its contract")
    faithfulness = _verify_faithfulness(
        contract, row.get("faithfulness_receipt") or {}
    )
    governed = _verify_governed_attempt(row.get("governed_attempt") or {})
    if (
        governed["task_id"] != faithfulness["formal_target_id"]
        or row.get("formal_target_id") != faithfulness["formal_target_id"]
        or row.get("formal_statement_sha256")
        != faithfulness["formal_statement_sha256"]
    ):
        raise ValueError("formal-task boundary result evidence does not join")
    return row


def adjudicate_governed_formal_counterexample_task(
    *,
    contract: TaskDischargeContract,
    boundary_result: Mapping[str, Any],
) -> TaskDischargeReceipt:
    """Adjudicate from an immutable boundary result without rerunning proof search."""

    parameters = _formal_task_parameters(contract)
    if boundary_result.get("schema") != "leanmill.frontier_boundary_result.v1":
        raise ValueError("formal task requires a frontier boundary result")
    boundary_core = {
        key: value for key, value in boundary_result.items()
        if key != "result_sha256"
    }
    boundary_ref = str(boundary_result.get("result_sha256") or "")
    if not boundary_ref or boundary_ref != content_hash(boundary_core):
        raise ValueError("formal-task boundary result digest mismatch")
    if boundary_result.get("context_hash") != parameters["context_hash"]:
        raise ValueError("formal-task boundary crossed its context")
    rows = boundary_result.get("query_results")
    if not isinstance(rows, list):
        raise ValueError("formal-task boundary query rows are malformed")
    matches = [
        dict(row)
        for row in rows
        if isinstance(row, Mapping)
        and row.get("candidate_kind") == "theory_task"
        and row.get("contract_sha256") == contract.sha256
        and row.get("adjudicator_id") == contract.adjudicator_id
    ]
    if len(matches) > 1:
        raise ValueError("formal-task boundary duplicated one task identity")
    if not matches:
        return TaskDischargeReceipt(
            contract_sha256=contract.sha256,
            adjudicator_id=contract.adjudicator_id,
            status="unavailable",
            authority="leanmill.frontier_boundary",
            observed={
                "request_id": parameters["request_id"],
                "boundary_status": "not_observed",
            },
            evidence_refs=(boundary_ref,),
        )
    row = validate_formal_task_boundary_result(contract, matches[0])
    if row.get("schema") == FORMAL_TASK_ATTEMPT_OUTCOME_SCHEMA:
        return TaskDischargeReceipt(
            contract_sha256=contract.sha256,
            adjudicator_id=contract.adjudicator_id,
            status="unavailable",
            authority="leanmill.frontier_boundary",
            observed={
                "request_id": parameters["request_id"],
                "boundary_status": row["status"],
                "stage": row["stage"],
                "reason_code": row["reason_code"],
            },
            evidence_refs=(str(row["receipt_sha256"]), boundary_ref),
        )
    faithfulness = dict(row["faithfulness_receipt"])
    if row.get("schema") == FORMALIZATION_CAMPAIGN_TASK_BOUNDARY_RESULT_SCHEMA:
        kernel = dict(row["kernel_replay_receipt"])
        roles = dict(row["role_separation_receipt"])
        evidence_refs = (
            str(faithfulness["receipt_sha256"]),
            str(roles["receipt_sha256"]),
            str(kernel["receipt_sha256"]),
            str(row["receipt_sha256"]),
            boundary_ref,
        )
    else:
        governed = dict(row["governed_attempt"])
        evidence_refs = (
            str(faithfulness["receipt_sha256"]),
            str(governed["receipt_sha256"]),
            str(row["receipt_sha256"]),
            boundary_ref,
        )
    return TaskDischargeReceipt(
        contract_sha256=contract.sha256,
        adjudicator_id=contract.adjudicator_id,
        status="discharged",
        authority="leanmill.frontier_boundary",
        observed={
            "request_id": parameters["request_id"],
            "formal_target_id": row["formal_target_id"],
            "boundary_status": row["status"],
            "claim_scope": parameters["claim_scope"],
        },
        evidence_refs=evidence_refs,
    )


__all__ = [
    "FORMAL_TASK_BOUNDARY_RESULT_SCHEMA",
    "FORMAL_TASK_ATTEMPT_OUTCOME_SCHEMA",
    "FORMAL_TASK_FAITHFULNESS_SCHEMA",
    "FORMALIZATION_CAMPAIGN_TASK_BOUNDARY_RESULT_SCHEMA",
    "GOVERNED_FORMAL_COUNTEREXAMPLE_ADJUDICATOR",
    "GOVERNED_FORMAL_COUNTEREXAMPLE_CAPABILITY",
    "adjudicate_governed_formal_counterexample_task",
    "build_formal_task_boundary_result",
    "build_formal_task_faithfulness_receipt",
    "compile_governed_formal_counterexample_task",
    "formal_task_parameters",
    "validate_formal_task_boundary_result",
]
