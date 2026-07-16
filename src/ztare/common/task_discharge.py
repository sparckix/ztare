"""Substrate-neutral task-discharge contracts and receipts.

The common kernel does not assume that achievement is a scalar, a level
counter, a game event, a proof, or a human rating.  A project declares which
registered adjudicator owns the stopping decision.  The substrate adapter
returns a typed receipt; the lifecycle controller only consumes its status.

Substrate vocabulary and comparison logic belong in the adapter named by
``adjudicator_id``.  This keeps the same contract usable for text, quantitative
models, proof work, partially observed environments, and observations of any
dimension.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256


def _json_stable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _json_stable(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_json_stable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "to_dict"):
        return _json_stable(value.to_dict())
    raise TypeError(
        f"task-discharge payloads must be JSON-stable, got {type(value).__qualname__}"
    )


@dataclass(frozen=True)
class TaskDischargeContract:
    """Identity of a project-owned stopping obligation.

    ``parameters`` are opaque to common code.  Only the registered substrate
    adjudicator may interpret them.
    """

    contract_id: str
    adjudicator_id: str
    lifecycle_scope: str
    owner: str
    parameters: Mapping[str, Any] = field(default_factory=dict)
    schema: str = "ztare-task-discharge-contract-v1"

    def __post_init__(self) -> None:
        for label, value in (
            ("contract_id", self.contract_id),
            ("adjudicator_id", self.adjudicator_id),
            ("lifecycle_scope", self.lifecycle_scope),
            ("owner", self.owner),
        ):
            if not str(value).strip():
                raise ValueError(f"{label} is required")
        _json_stable(self.parameters)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "contract_id": self.contract_id,
            "adjudicator_id": self.adjudicator_id,
            "lifecycle_scope": self.lifecycle_scope,
            "owner": self.owner,
            "parameters": _json_stable(self.parameters),
        }

    @property
    def sha256(self) -> str:
        return stable_sha256(self.to_dict())

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TaskDischargeContract":
        if payload.get("schema") not in (None, "ztare-task-discharge-contract-v1"):
            raise ValueError("unsupported task-discharge contract schema")
        parameters = payload.get("parameters") or {}
        if not isinstance(parameters, Mapping):
            raise TypeError("task-discharge parameters must be an object")
        return cls(
            contract_id=str(payload.get("contract_id") or ""),
            adjudicator_id=str(payload.get("adjudicator_id") or ""),
            lifecycle_scope=str(payload.get("lifecycle_scope") or ""),
            owner=str(payload.get("owner") or ""),
            parameters=dict(parameters),
        )


@dataclass(frozen=True)
class TaskDischargeReceipt:
    """Adapter-authored decision bound to one exact task contract."""

    contract_sha256: str
    adjudicator_id: str
    status: str
    authority: str
    observed: Any
    evidence_refs: tuple[str, ...] = ()
    schema: str = "ztare-task-discharge-receipt-v1"

    def __post_init__(self) -> None:
        if self.status not in {"open", "discharged", "unavailable"}:
            raise ValueError("task-discharge status must be open, discharged, or unavailable")
        for label, value in (
            ("contract_sha256", self.contract_sha256),
            ("adjudicator_id", self.adjudicator_id),
            ("authority", self.authority),
        ):
            if not str(value).strip():
                raise ValueError(f"{label} is required")
        _json_stable(self.observed)
        if self.status == "discharged" and not tuple(
            ref for ref in self.evidence_refs if str(ref).strip()
        ):
            raise ValueError("a discharged task requires an authority evidence ref")

    @property
    def discharged(self) -> bool:
        return self.status == "discharged"

    @property
    def sha256(self) -> str:
        """Stable identity of this exact adjudication event."""
        return stable_sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "contract_sha256": self.contract_sha256,
            "adjudicator_id": self.adjudicator_id,
            "status": self.status,
            "authority": self.authority,
            "observed": _json_stable(self.observed),
            "evidence_refs": list(self.evidence_refs),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TaskDischargeReceipt":
        if payload.get("schema") not in (None, "ztare-task-discharge-receipt-v1"):
            raise ValueError("unsupported task-discharge receipt schema")
        refs = payload.get("evidence_refs") or []
        if not isinstance(refs, list):
            raise TypeError("task-discharge evidence_refs must be a list")
        return cls(
            contract_sha256=str(payload.get("contract_sha256") or ""),
            adjudicator_id=str(payload.get("adjudicator_id") or ""),
            status=str(payload.get("status") or ""),
            authority=str(payload.get("authority") or ""),
            observed=payload.get("observed"),
            evidence_refs=tuple(str(ref) for ref in refs),
        )


def adjudicate_task_discharge(adapter: Any, contract: TaskDischargeContract) -> TaskDischargeReceipt:
    """Ask the registered substrate adjudicator and verify receipt identity."""
    provider = getattr(adapter, "adjudicate_task_discharge", None)
    if not callable(provider):
        raise TypeError(
            "the active substrate adapter does not implement adjudicate_task_discharge"
        )
    raw = provider(contract)
    _, receipt = bind_task_discharge_receipt(contract, raw)
    return receipt


def bind_task_discharge_receipt(
    contract: TaskDischargeContract | Mapping[str, Any],
    receipt: TaskDischargeReceipt | Mapping[str, Any],
) -> tuple[TaskDischargeContract, TaskDischargeReceipt]:
    """Parse and bind a receipt to the exact task contract it adjudicates.

    This is the single reader door for stored and live task-discharge payloads.
    A status label or Boolean outside this pair has no stopping authority.
    """
    bound_contract = (
        contract
        if isinstance(contract, TaskDischargeContract)
        else TaskDischargeContract.from_dict(contract)
        if isinstance(contract, Mapping)
        else None
    )
    if bound_contract is None:
        raise TypeError("task contract must be TaskDischargeContract or a mapping")
    bound_receipt = (
        receipt
        if isinstance(receipt, TaskDischargeReceipt)
        else TaskDischargeReceipt.from_dict(receipt)
        if isinstance(receipt, Mapping)
        else None
    )
    if bound_receipt is None:
        raise TypeError("task adjudicator must return TaskDischargeReceipt or a mapping")
    if bound_receipt.contract_sha256 != bound_contract.sha256:
        raise ValueError("task-discharge receipt is bound to a different contract")
    if bound_receipt.adjudicator_id != bound_contract.adjudicator_id:
        raise ValueError("task-discharge receipt came from a different adjudicator")
    return bound_contract, bound_receipt


def task_discharge_from_profile(
    profile: Mapping[str, Any],
) -> TaskDischargeContract | None:
    """Load an explicit task contract; absence preserves caller lifecycle policy."""
    payload = profile.get("task_discharge")
    if payload is None:
        return None
    if not isinstance(payload, Mapping):
        raise TypeError("task_discharge must be an object")
    return TaskDischargeContract.from_dict(payload)
