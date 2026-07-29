"""Substrate-neutral contracts for replaying target predicates on prior art.

The contract freezes the question being asked before examples are retrieved.
Common code binds identities and a closed ``overlap | unknown`` outcome
algebra; only a registered substrate adapter interprets the opaque predicate
and normalized example payloads.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
import re
from typing import Any, Mapping


TARGET_PREDICATE_CONTRACT_SCHEMA = "ztare-target-predicate-contract-v1"
RETRIEVED_EXAMPLE_SCHEMA = "ztare-retrieved-example-v1"
TARGET_PREDICATE_ADJUDICATION_SCHEMA = "ztare-target-predicate-adjudication-v1"
TARGET_PREDICATE_RECEIPT_SCHEMA = "ztare-target-predicate-replay-receipt-v1"
TARGET_PREDICATE_AUTHORITY = "registered_adapter_prior_art_overlap_only"
TARGET_PREDICATE_OUTCOMES = ("overlap", "unknown")

_SHA256 = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")


def _json_stable(value: Any, *, context: str) -> Any:
    """Return strict JSON data without coercing keys or opaque objects."""

    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError(f"{context} object keys must be strings")
        return {
            key: _json_stable(item, context=context)
            for key, item in sorted(value.items())
        }
    if isinstance(value, (list, tuple)):
        return [_json_stable(item, context=context) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{context} cannot contain non-finite numbers")
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(
        f"{context} must be JSON-stable, got {type(value).__qualname__}"
    )


def _sha256(value: Any) -> str:
    payload = json.dumps(
        _json_stable(value, context="hash payload"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _require_nonempty(**fields: str) -> None:
    missing = [name for name, value in fields.items() if not str(value).strip()]
    if missing:
        raise ValueError(
            "target-predicate identity requires " + ", ".join(sorted(missing))
        )


def _require_exact_fields(
    payload: Mapping[str, Any], required: set[str], *, context: str
) -> None:
    missing = required - set(payload)
    unknown = set(payload) - required
    if missing or unknown:
        raise ValueError(
            f"{context} field mismatch: missing={sorted(missing)}, "
            f"unknown={sorted(unknown)}"
        )


@dataclass(frozen=True)
class TargetPredicateContract:
    """Frozen, adapter-owned target question for one objective epoch."""

    contract_id: str
    owner: str
    lifecycle_scope: str
    context_hash: str
    adapter_id: str
    evaluator_capability: str
    predicate_ir: Mapping[str, Any] = field(default_factory=dict)
    input_schema: Mapping[str, Any] = field(default_factory=dict)
    claim_scope: str = "one_retrieved_example_prior_art_overlap_only"
    schema: str = TARGET_PREDICATE_CONTRACT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != TARGET_PREDICATE_CONTRACT_SCHEMA:
            raise ValueError(f"unsupported target-predicate contract schema: {self.schema}")
        _require_nonempty(
            contract_id=self.contract_id,
            owner=self.owner,
            lifecycle_scope=self.lifecycle_scope,
            context_hash=self.context_hash,
            adapter_id=self.adapter_id,
            evaluator_capability=self.evaluator_capability,
            claim_scope=self.claim_scope,
        )
        if self.claim_scope != "one_retrieved_example_prior_art_overlap_only":
            raise ValueError("target-predicate contract cannot claim corpus completeness")
        if not isinstance(self.predicate_ir, Mapping) or not isinstance(
            self.input_schema, Mapping
        ):
            raise TypeError("target predicate IR and input schema must be objects")
        object.__setattr__(
            self,
            "predicate_ir",
            _json_stable(self.predicate_ir, context="target predicate IR"),
        )
        object.__setattr__(
            self,
            "input_schema",
            _json_stable(self.input_schema, context="target predicate input schema"),
        )
        if not self.predicate_ir or not self.input_schema:
            raise ValueError("target-predicate contract requires predicate IR and input schema")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "contract_id": self.contract_id,
            "owner": self.owner,
            "lifecycle_scope": self.lifecycle_scope,
            "context_hash": self.context_hash,
            "adapter_id": self.adapter_id,
            "evaluator_capability": self.evaluator_capability,
            "predicate_ir": _json_stable(
                self.predicate_ir, context="target predicate IR"
            ),
            "input_schema": _json_stable(
                self.input_schema, context="target predicate input schema"
            ),
            "claim_scope": self.claim_scope,
        }

    @property
    def sha256(self) -> str:
        return _sha256(self.to_dict())

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetPredicateContract":
        required = {
            "schema", "contract_id", "owner", "lifecycle_scope", "context_hash",
            "adapter_id", "evaluator_capability", "predicate_ir", "input_schema",
            "claim_scope",
        }
        _require_exact_fields(payload, required, context="target-predicate contract")
        predicate_ir = payload["predicate_ir"]
        input_schema = payload["input_schema"]
        if not isinstance(predicate_ir, Mapping) or not isinstance(input_schema, Mapping):
            raise TypeError("target predicate IR and input schema must be objects")
        return cls(
            contract_id=str(payload["contract_id"]),
            owner=str(payload["owner"]),
            lifecycle_scope=str(payload["lifecycle_scope"]),
            context_hash=str(payload["context_hash"]),
            adapter_id=str(payload["adapter_id"]),
            evaluator_capability=str(payload["evaluator_capability"]),
            predicate_ir=dict(predicate_ir),
            input_schema=dict(input_schema),
            claim_scope=str(payload["claim_scope"]),
            schema=str(payload["schema"]),
        )


@dataclass(frozen=True)
class RetrievedExample:
    """Source-bound example normalized for one registered adapter."""

    example_id: str
    source_id: str
    source_url: str
    source_content_sha256: str
    source_locator: str
    adapter_id: str
    normalized_input: Mapping[str, Any]
    evidence_refs: tuple[str, ...]
    schema: str = RETRIEVED_EXAMPLE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != RETRIEVED_EXAMPLE_SCHEMA:
            raise ValueError(f"unsupported retrieved-example schema: {self.schema}")
        _require_nonempty(
            example_id=self.example_id,
            source_id=self.source_id,
            source_url=self.source_url,
            source_content_sha256=self.source_content_sha256,
            source_locator=self.source_locator,
            adapter_id=self.adapter_id,
        )
        if not _SHA256.fullmatch(self.source_content_sha256):
            raise ValueError("retrieved example requires a source content SHA-256")
        if not isinstance(self.normalized_input, Mapping):
            raise TypeError("retrieved example normalized input must be an object")
        if not isinstance(self.evidence_refs, (list, tuple)):
            raise TypeError("retrieved example evidence refs must be a list or tuple")
        object.__setattr__(
            self,
            "normalized_input",
            _json_stable(self.normalized_input, context="retrieved example input"),
        )
        object.__setattr__(
            self, "evidence_refs", tuple(str(ref) for ref in self.evidence_refs)
        )
        if not self.normalized_input:
            raise ValueError("retrieved example normalized input must not be empty")
        if not self.evidence_refs or any(
            not str(ref).strip() for ref in self.evidence_refs
        ):
            raise ValueError("retrieved example requires nonempty evidence refs")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "example_id": self.example_id,
            "source_id": self.source_id,
            "source_url": self.source_url,
            "source_content_sha256": self.source_content_sha256,
            "source_locator": self.source_locator,
            "adapter_id": self.adapter_id,
            "normalized_input": _json_stable(
                self.normalized_input, context="retrieved example input"
            ),
            "evidence_refs": list(self.evidence_refs),
        }

    @property
    def sha256(self) -> str:
        return _sha256(self.to_dict())

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RetrievedExample":
        required = {
            "schema", "example_id", "source_id", "source_url",
            "source_content_sha256", "source_locator", "adapter_id",
            "normalized_input", "evidence_refs",
        }
        _require_exact_fields(payload, required, context="retrieved example")
        normalized = payload["normalized_input"]
        refs = payload["evidence_refs"]
        if not isinstance(normalized, Mapping) or not isinstance(refs, list):
            raise TypeError("retrieved example input must be an object and refs a list")
        return cls(
            example_id=str(payload["example_id"]),
            source_id=str(payload["source_id"]),
            source_url=str(payload["source_url"]),
            source_content_sha256=str(payload["source_content_sha256"]),
            source_locator=str(payload["source_locator"]),
            adapter_id=str(payload["adapter_id"]),
            normalized_input=dict(normalized),
            evidence_refs=tuple(str(ref) for ref in refs),
            schema=str(payload["schema"]),
        )


@dataclass(frozen=True)
class TargetPredicateAdjudication:
    """Narrow result returned by a registered predicate evaluator."""

    outcome: str
    reason_code: str
    reason: str
    witness: Any
    evidence_refs: tuple[str, ...] = ()
    schema: str = TARGET_PREDICATE_ADJUDICATION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != TARGET_PREDICATE_ADJUDICATION_SCHEMA:
            raise ValueError(f"unsupported predicate adjudication schema: {self.schema}")
        if self.outcome not in TARGET_PREDICATE_OUTCOMES:
            raise ValueError("target-predicate outcome must be overlap or unknown")
        _require_nonempty(reason_code=self.reason_code, reason=self.reason)
        if not isinstance(self.evidence_refs, (list, tuple)):
            raise TypeError("target predicate evidence refs must be a list or tuple")
        object.__setattr__(
            self,
            "witness",
            _json_stable(self.witness, context="target predicate witness"),
        )
        object.__setattr__(
            self, "evidence_refs", tuple(str(ref) for ref in self.evidence_refs)
        )
        if self.outcome == "overlap" and (
            self.witness in (None, {}, [])
            or not self.evidence_refs
            or any(not str(ref).strip() for ref in self.evidence_refs)
        ):
            raise ValueError("overlap requires a witness and authority evidence refs")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "outcome": self.outcome,
            "reason_code": self.reason_code,
            "reason": self.reason,
            "witness": _json_stable(self.witness, context="target predicate witness"),
            "evidence_refs": list(self.evidence_refs),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetPredicateAdjudication":
        required = {
            "schema", "outcome", "reason_code", "reason", "witness",
            "evidence_refs",
        }
        _require_exact_fields(payload, required, context="target predicate adjudication")
        refs = payload["evidence_refs"]
        if not isinstance(refs, list):
            raise TypeError("target predicate adjudication refs must be a list")
        return cls(
            outcome=str(payload["outcome"]),
            reason_code=str(payload["reason_code"]),
            reason=str(payload["reason"]),
            witness=payload["witness"],
            evidence_refs=tuple(str(ref) for ref in refs),
            schema=str(payload["schema"]),
        )


@dataclass(frozen=True)
class TargetPredicateReceipt:
    """Host-bound adapter result carrying everything needed for deterministic replay."""

    contract: TargetPredicateContract
    retrieved_example: RetrievedExample
    adjudication: TargetPredicateAdjudication
    authority: str = TARGET_PREDICATE_AUTHORITY
    schema: str = TARGET_PREDICATE_RECEIPT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != TARGET_PREDICATE_RECEIPT_SCHEMA:
            raise ValueError(f"unsupported target-predicate receipt schema: {self.schema}")
        if self.authority != TARGET_PREDICATE_AUTHORITY:
            raise ValueError("target-predicate receipt has excess or unknown authority")
        if self.contract.adapter_id != self.retrieved_example.adapter_id:
            raise ValueError("target-predicate contract and example adapters differ")

    @property
    def subject_id(self) -> str:
        return f"{self.contract.sha256}:{self.retrieved_example.sha256}"

    def core_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "contract": self.contract.to_dict(),
            "contract_sha256": self.contract.sha256,
            "retrieved_example": self.retrieved_example.to_dict(),
            "example_sha256": self.retrieved_example.sha256,
            "adjudication": self.adjudication.to_dict(),
            "authority": self.authority,
        }

    @property
    def sha256(self) -> str:
        return _sha256(self.core_dict())

    def to_dict(self) -> dict[str, Any]:
        return {**self.core_dict(), "receipt_sha256": self.sha256}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetPredicateReceipt":
        required = {
            "schema", "contract", "contract_sha256", "retrieved_example",
            "example_sha256", "adjudication", "authority", "receipt_sha256",
        }
        _require_exact_fields(payload, required, context="target-predicate receipt")
        if not all(
            isinstance(payload[key], Mapping)
            for key in ("contract", "retrieved_example", "adjudication")
        ):
            raise TypeError("target-predicate receipt nested artifacts must be objects")
        receipt = cls(
            contract=TargetPredicateContract.from_dict(payload["contract"]),
            retrieved_example=RetrievedExample.from_dict(payload["retrieved_example"]),
            adjudication=TargetPredicateAdjudication.from_dict(payload["adjudication"]),
            authority=str(payload["authority"]),
            schema=str(payload["schema"]),
        )
        if str(payload["contract_sha256"]) != receipt.contract.sha256:
            raise ValueError("target-predicate receipt contract identity mismatch")
        if str(payload["example_sha256"]) != receipt.retrieved_example.sha256:
            raise ValueError("target-predicate receipt example identity mismatch")
        if str(payload["receipt_sha256"]) != receipt.sha256:
            raise ValueError("target-predicate receipt digest mismatch")
        return receipt


__all__ = [
    "RETRIEVED_EXAMPLE_SCHEMA", "TARGET_PREDICATE_ADJUDICATION_SCHEMA",
    "TARGET_PREDICATE_AUTHORITY", "TARGET_PREDICATE_CONTRACT_SCHEMA",
    "TARGET_PREDICATE_OUTCOMES", "TARGET_PREDICATE_RECEIPT_SCHEMA",
    "RetrievedExample", "TargetPredicateAdjudication", "TargetPredicateContract",
    "TargetPredicateReceipt",
]
