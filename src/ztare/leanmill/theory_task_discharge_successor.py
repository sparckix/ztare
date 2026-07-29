"""Content-bound successors for theory-task discharge bundles.

The initial task adjudicator may establish an intermediate state whose next
obligation belongs to a different authority.  Construction artifacts are the
first such case: the witness boundary verifies the finite object, while a
provider-free LeanMill ratification action owns theorem credit.  This module
keeps both decisions immutable and joins them in one replayable successor.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from ztare.common.task_discharge import (
    TaskDischargeContract,
    bind_task_discharge_receipt,
)
from ztare.leanmill.construction_artifact_ratification import (
    validate_construction_artifact_ratification_aggregate,
)
from ztare.leanmill.theory_ir import content_hash


CONSTRUCTION_RATIFICATION_TRANSITION_SCHEMA = (
    "leanmill.construction_artifact_ratification_transition.v1"
)
CONSTRUCTION_RATIFICATION_TRANSITION_ROW_SCHEMA = (
    "leanmill.construction_artifact_ratification_transition_row.v1"
)
CONSTRUCTION_RATIFICATION_TRANSITION_KEY = (
    "construction_artifact_ratification_transition"
)


def _bundle_core(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != "receipt_sha256"}


def _boundary_ref(value: Mapping[str, Any]) -> str:
    row = dict(value)
    core = {key: item for key, item in row.items() if key != "result_sha256"}
    reference = str(row.get("result_sha256") or "")
    if (
        row.get("schema") != "leanmill.frontier_boundary_result.v1"
        or reference != content_hash(core)
    ):
        raise ValueError("construction ratification boundary does not replay")
    return reference


def _validate_base_bundle(
    value: Mapping[str, Any],
    *,
    boundary_result_sha256: str,
    context: str,
) -> dict[str, Any]:
    row = dict(value)
    core = _bundle_core(row)
    if (
        row.get("schema") != "leanmill.theory_task_discharge.v1"
        or row.get("receipt_sha256") != content_hash(core)
        or row.get("boundary_result_sha256") != boundary_result_sha256
        or row.get("authority") != "registered_adapter_receipts_host_aggregation"
        or not str(row.get("adapter_id") or "")
        or not isinstance(row.get("rows"), list)
        or not isinstance(row.get("program_outcomes"), Mapping)
    ):
        raise ValueError(f"{context} does not replay")
    return row


def _validated_rows(
    bundle: Mapping[str, Any], *, context: str
) -> dict[tuple[str, str], dict[str, Any]]:
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    for raw in bundle.get("rows") or ():
        if not isinstance(raw, Mapping):
            raise ValueError(f"{context} contains a malformed row")
        row = dict(raw)
        core = {key: item for key, item in row.items() if key != "receipt_sha256"}
        contract, _receipt = bind_task_discharge_receipt(
            row.get("contract") or {}, row.get("receipt") or {}
        )
        program_id = str(row.get("program_id") or "")
        key = (program_id, contract.sha256)
        if (
            not program_id
            or key in indexed
            or row.get("receipt_sha256") != content_hash(core)
            or row.get("contract_sha256") != contract.sha256
            or row.get("source") not in {"explicit_task", "legacy_prediction"}
        ):
            raise ValueError(f"{context} row changed identity")
        indexed[key] = row
    return indexed


def _program_outcomes(rows: Sequence[Mapping[str, Any]]) -> tuple[dict[str, str], str]:
    explicit: dict[str, list[str]] = {}
    declared_programs: set[str] = set()
    for row in rows:
        program_id = str(row.get("program_id") or "")
        declared_programs.add(program_id)
        if row.get("source") != "explicit_task":
            continue
        _contract, receipt = bind_task_discharge_receipt(
            row.get("contract") or {}, row.get("receipt") or {}
        )
        explicit.setdefault(program_id, []).append(receipt.status)
    outcomes = {
        program_id: (
            "not_declared"
            if not explicit.get(program_id)
            else "discharged"
            if all(status == "discharged" for status in explicit[program_id])
            else "unavailable"
            if any(status == "unavailable" for status in explicit[program_id])
            else "open"
        )
        for program_id in sorted(declared_programs)
    }
    declared = [status for status in outcomes.values() if status != "not_declared"]
    status = (
        "not_declared"
        if not declared
        else "discharged"
        if "discharged" in declared
        else "unavailable"
        if all(value == "unavailable" for value in declared)
        else "open"
    )
    return outcomes, status


def build_construction_ratification_successor_bundle(
    predecessor_bundle: Mapping[str, Any],
    outer_boundary_result: Mapping[str, Any],
    replacements: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Replace intermediate witness receipts through a frozen authority join."""

    boundary_ref = _boundary_ref(outer_boundary_result)
    predecessor = _validate_base_bundle(
        predecessor_bundle,
        boundary_result_sha256=boundary_ref,
        context="predecessor theory-task bundle",
    )
    if CONSTRUCTION_RATIFICATION_TRANSITION_KEY in predecessor:
        raise ValueError("construction ratification predecessor is already a successor")
    prior_rows = _validated_rows(predecessor, context="predecessor theory-task bundle")
    transition_rows: list[dict[str, Any]] = []
    final_receipts: dict[tuple[str, str], dict[str, Any]] = {}
    for raw in replacements:
        if not isinstance(raw, Mapping):
            raise TypeError("construction ratification replacement must be an object")
        program_id = str(raw.get("program_id") or "")
        contract_sha = str(raw.get("task_contract_sha256") or "")
        key = (program_id, contract_sha)
        prior = prior_rows.get(key)
        if prior is None or key in final_receipts:
            raise ValueError("construction ratification replacement is not unique")
        contract, prior_receipt = bind_task_discharge_receipt(
            prior["contract"], prior["receipt"]
        )
        aggregate = validate_construction_artifact_ratification_aggregate(
            contract,
            outer_boundary_result,
            prior_receipt,
            raw.get("aggregate") or {},
        )
        final_receipt = dict(aggregate["final_task_discharge_receipt"])
        row_core = {
            "schema": CONSTRUCTION_RATIFICATION_TRANSITION_ROW_SCHEMA,
            "program_id": program_id,
            "task_contract_sha256": contract.sha256,
            "predecessor_row_receipt_sha256": str(prior["receipt_sha256"]),
            "prior_open_receipt": prior_receipt.to_dict(),
            "prior_open_receipt_sha256": prior_receipt.sha256,
            "aggregate": aggregate,
            "aggregate_sha256": str(aggregate["aggregate_sha256"]),
            "authority": "construction_artifact_ratification_successor_join",
        }
        transition_rows.append(
            {**row_core, "receipt_sha256": content_hash(row_core)}
        )
        final_receipts[key] = final_receipt

    if not transition_rows:
        raise ValueError("construction ratification successor requires a replacement")
    successor_rows: list[dict[str, Any]] = []
    for prior in predecessor["rows"]:
        key = (str(prior["program_id"]), str(prior["contract_sha256"]))
        receipt = final_receipts.get(key)
        if receipt is None:
            successor_rows.append(dict(prior))
            continue
        core = {
            **{name: item for name, item in prior.items() if name != "receipt_sha256"},
            "receipt": receipt,
        }
        successor_rows.append({**core, "receipt_sha256": content_hash(core)})

    transition_core = {
        "schema": CONSTRUCTION_RATIFICATION_TRANSITION_SCHEMA,
        "predecessor_bundle": predecessor,
        "predecessor_bundle_receipt_sha256": str(predecessor["receipt_sha256"]),
        "rows": sorted(
            transition_rows,
            key=lambda row: (row["program_id"], row["task_contract_sha256"]),
        ),
        "authority": "leanmill.construction_artifact_ratification_transition",
    }
    transition = {
        **transition_core,
        "receipt_sha256": content_hash(transition_core),
    }
    outcomes, status = _program_outcomes(successor_rows)
    core = {
        "schema": "leanmill.theory_task_discharge.v1",
        "adapter_id": predecessor["adapter_id"],
        "boundary_result_sha256": boundary_ref,
        "rows": successor_rows,
        "program_outcomes": outcomes,
        "explicit_program_status": status,
        "authority": "registered_adapter_receipts_host_aggregation",
        CONSTRUCTION_RATIFICATION_TRANSITION_KEY: transition,
    }
    result = {**core, "receipt_sha256": content_hash(core)}
    return validate_construction_ratification_successor_bundle(
        result, outer_boundary_result
    )


def validate_construction_ratification_successor_bundle(
    value: Mapping[str, Any],
    outer_boundary_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay every changed receipt through its ratification aggregate."""

    boundary_ref = _boundary_ref(outer_boundary_result)
    successor = _validate_base_bundle(
        value,
        boundary_result_sha256=boundary_ref,
        context="construction ratification successor bundle",
    )
    transition = successor.get(CONSTRUCTION_RATIFICATION_TRANSITION_KEY)
    if not isinstance(transition, Mapping):
        raise ValueError("construction ratification successor lacks its transition")
    transition = dict(transition)
    transition_core = {
        key: item for key, item in transition.items() if key != "receipt_sha256"
    }
    predecessor_raw = transition.get("predecessor_bundle")
    if (
        transition.get("schema") != CONSTRUCTION_RATIFICATION_TRANSITION_SCHEMA
        or transition.get("receipt_sha256") != content_hash(transition_core)
        or transition.get("authority")
        != "leanmill.construction_artifact_ratification_transition"
        or not isinstance(predecessor_raw, Mapping)
    ):
        raise ValueError("construction ratification transition does not replay")
    predecessor = _validate_base_bundle(
        predecessor_raw,
        boundary_result_sha256=boundary_ref,
        context="construction ratification predecessor bundle",
    )
    if (
        CONSTRUCTION_RATIFICATION_TRANSITION_KEY in predecessor
        or transition.get("predecessor_bundle_receipt_sha256")
        != predecessor.get("receipt_sha256")
        or successor.get("adapter_id") != predecessor.get("adapter_id")
    ):
        raise ValueError("construction ratification transition crossed its predecessor")

    prior_rows = _validated_rows(predecessor, context="ratification predecessor")
    successor_rows = _validated_rows(successor, context="ratification successor")
    if set(prior_rows) != set(successor_rows):
        raise ValueError("construction ratification successor changed task coverage")
    changed: dict[tuple[str, str], dict[str, Any]] = {}
    for raw in transition.get("rows") or ():
        if not isinstance(raw, Mapping):
            raise ValueError("construction ratification transition row is malformed")
        row = dict(raw)
        row_core = {
            key: item for key, item in row.items() if key != "receipt_sha256"
        }
        key = (str(row.get("program_id") or ""), str(row.get("task_contract_sha256") or ""))
        prior = prior_rows.get(key)
        if (
            prior is None
            or key in changed
            or row.get("schema") != CONSTRUCTION_RATIFICATION_TRANSITION_ROW_SCHEMA
            or row.get("receipt_sha256") != content_hash(row_core)
            or row.get("predecessor_row_receipt_sha256")
            != prior.get("receipt_sha256")
            or row.get("authority")
            != "construction_artifact_ratification_successor_join"
        ):
            raise ValueError("construction ratification transition row changed identity")
        contract, prior_receipt = bind_task_discharge_receipt(
            prior["contract"], row.get("prior_open_receipt") or {}
        )
        if (
            prior_receipt.to_dict() != prior.get("receipt")
            or row.get("prior_open_receipt_sha256") != prior_receipt.sha256
        ):
            raise ValueError("construction ratification transition changed prior receipt")
        aggregate = validate_construction_artifact_ratification_aggregate(
            contract,
            outer_boundary_result,
            prior_receipt,
            row.get("aggregate") or {},
        )
        if row.get("aggregate_sha256") != aggregate.get("aggregate_sha256"):
            raise ValueError("construction ratification aggregate reference changed")
        changed[key] = aggregate

    if not changed:
        raise ValueError("construction ratification transition has no changed task")
    for key, prior in prior_rows.items():
        current = successor_rows[key]
        aggregate = changed.get(key)
        if aggregate is None:
            if current != prior:
                raise ValueError("unratified task row changed in successor")
            continue
        expected_receipt = aggregate["final_task_discharge_receipt"]
        expected_core = {
            **{name: item for name, item in prior.items() if name != "receipt_sha256"},
            "receipt": expected_receipt,
        }
        expected = {
            **expected_core,
            "receipt_sha256": content_hash(expected_core),
        }
        if current != expected:
            raise ValueError("ratified task row does not match its aggregate")

    outcomes, status = _program_outcomes(successor["rows"])
    if (
        successor.get("program_outcomes") != outcomes
        or successor.get("explicit_program_status") != status
    ):
        raise ValueError("construction ratification successor aggregate is inconsistent")
    return successor


def construction_ratification_predecessor_ref(
    bundle: Mapping[str, Any],
) -> str:
    transition = bundle.get(CONSTRUCTION_RATIFICATION_TRANSITION_KEY)
    return (
        str(transition.get("predecessor_bundle_receipt_sha256") or "")
        if isinstance(transition, Mapping)
        else ""
    )


__all__ = [
    "CONSTRUCTION_RATIFICATION_TRANSITION_KEY",
    "build_construction_ratification_successor_bundle",
    "construction_ratification_predecessor_ref",
    "validate_construction_ratification_successor_bundle",
]
