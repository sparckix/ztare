"""Complete finite-model census and first-adapter isomorphism quotient."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from typing import Any, Iterable, Sequence

from ztare.leanmill.finite_model import (
    FiniteModel,
    evaluate_axiom,
    finite_interpretation_count,
    iter_finite_models,
    validate_model,
)
from ztare.leanmill.theory_ir import (
    AxiomFormula,
    TheorySignature,
    content_hash,
    validate_axioms,
)


CENSUS_SCHEMA = "leanmill.finite_model_universe.v1"
CANONICAL_MODEL_SCHEMA = "leanmill.canonical_finite_model.v1"


@dataclass(frozen=True)
class CanonicalModelRecord:
    model_id: str
    carrier_size: int
    operation_name: str
    canonical_table: tuple[int, ...]
    model: FiniteModel
    labeled_orbit_count: int
    schema: str = CANONICAL_MODEL_SCHEMA

    @property
    def stratum_id(self) -> str:
        return f"carrier_size:{self.carrier_size}"

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "model_id": self.model_id,
            "carrier_size": self.carrier_size,
            "operation_name": self.operation_name,
            "canonical_table": list(self.canonical_table),
            "model": self.model.to_json(),
            "labeled_orbit_count": self.labeled_orbit_count,
        }


@dataclass(frozen=True)
class FiniteModelUniverseReceipt:
    signature_hash: str
    carrier_sizes: tuple[int, ...]
    base_axiom_hashes: tuple[str, ...]
    labeled_interpretation_count: int
    accepted_labeled_count: int
    canonical_model_count: int
    model_order_digest: str
    isomorphism_policy: str
    complete: bool = True
    schema: str = CENSUS_SCHEMA

    @property
    def receipt_digest(self) -> str:
        return content_hash(self.to_json(include_digest=False))

    @property
    def declared_strata(self) -> tuple[dict[str, int], ...]:
        return tuple({"carrier_size": size} for size in self.carrier_sizes)

    def to_json(self, *, include_digest: bool = True) -> dict[str, Any]:
        payload = {
            "schema": self.schema,
            "signature_sha256": self.signature_hash,
            "carrier_sizes": list(self.carrier_sizes),
            "base_axiom_sha256s": list(self.base_axiom_hashes),
            "labeled_interpretation_count": self.labeled_interpretation_count,
            "accepted_labeled_count": self.accepted_labeled_count,
            "canonical_model_count": self.canonical_model_count,
            "model_order_digest": self.model_order_digest,
            "isomorphism_policy": self.isomorphism_policy,
            "complete": self.complete,
        }
        if include_digest:
            payload["receipt_sha256"] = content_hash(payload)
        return payload


@dataclass(frozen=True)
class MagmaModelUniverse:
    signature: TheorySignature
    models: tuple[CanonicalModelRecord, ...]
    receipt: FiniteModelUniverseReceipt

    @property
    def adapter_id(self) -> str:
        return "magma_equational.v1"

    def __post_init__(self) -> None:
        if not self.receipt.complete:
            raise ValueError("MagmaModelUniverse requires a complete census")
        if self.receipt.signature_hash != self.signature.content_hash:
            raise ValueError("census receipt signature mismatch")
        ids = tuple(row.model_id for row in self.models)
        if len(set(ids)) != len(ids):
            raise ValueError("canonical model IDs must be unique")
        if self.receipt.canonical_model_count != len(self.models):
            raise ValueError("census receipt model count mismatch")
        if self.receipt.model_order_digest != content_hash({"model_ids": list(ids)}):
            raise ValueError("census receipt model order mismatch")

    @property
    def model_ids(self) -> tuple[str, ...]:
        return tuple(row.model_id for row in self.models)

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": "leanmill.model_universe_envelope.v1",
            "adapter_id": self.adapter_id,
            "signature": self.signature.to_json(),
            "receipt": self.receipt.to_json(),
            "models": [row.to_json() for row in self.models],
        }


def _validate_magma_signature(
    signature: TheorySignature,
    *,
    operation_name: str,
) -> str:
    if len(signature.sorts) != 1 or len(signature.operations) != 1 or signature.relations:
        raise ValueError("magma census requires one sort, one operation, and no relations")
    operation = signature.operations[0]
    sort_name = signature.sorts[0].name
    if operation.name != operation_name:
        raise ValueError(f"unknown magma operation: {operation_name!r}")
    if operation.arg_sorts != (sort_name, sort_name) or operation.result_sort != sort_name:
        raise ValueError("magma operation must be binary and closed on the sole sort")
    return sort_name


def canonicalize_magma_table(
    table: Sequence[int],
    carrier_size: int,
) -> tuple[int, ...]:
    """Canonicalize a binary table under every carrier relabeling."""

    if type(carrier_size) is not int or carrier_size < 1:
        raise ValueError("carrier_size must be a positive integer")
    expected = carrier_size * carrier_size
    values = tuple(table)
    if len(values) != expected:
        raise ValueError(f"binary table needs {expected} entries")
    if any(type(value) is not int or value < 0 or value >= carrier_size for value in values):
        raise ValueError("binary table contains an out-of-carrier result")

    candidates: list[tuple[int, ...]] = []
    for old_to_new in permutations(range(carrier_size)):
        new_to_old = [0] * carrier_size
        for old, new in enumerate(old_to_new):
            new_to_old[new] = old
        relabeled = tuple(
            old_to_new[
                values[
                    new_to_old[left] * carrier_size
                    + new_to_old[right]
                ]
            ]
            for left in range(carrier_size)
            for right in range(carrier_size)
        )
        candidates.append(relabeled)
    return min(candidates)


def _canonical_model(
    *,
    signature: TheorySignature,
    sort_name: str,
    operation_name: str,
    carrier_size: int,
    table: tuple[int, ...],
    labeled_orbit_count: int,
) -> CanonicalModelRecord:
    model = FiniteModel(
        sort_sizes=((sort_name, carrier_size),),
        operations=((operation_name, table),),
    )
    validate_model(signature, model)
    model_id = "model:" + content_hash(
        {
            "signature_sha256": signature.content_hash,
            "carrier_size": carrier_size,
            "operation": operation_name,
            "canonical_table": list(table),
        }
    )
    return CanonicalModelRecord(
        model_id=model_id,
        carrier_size=carrier_size,
        operation_name=operation_name,
        canonical_table=table,
        model=model,
        labeled_orbit_count=labeled_orbit_count,
    )


def enumerate_magma_model_universe(
    signature: TheorySignature,
    *,
    carrier_sizes: Iterable[int],
    operation_name: str = "op0",
    base_axioms: Sequence[AxiomFormula] = (),
) -> MagmaModelUniverse:
    """Enumerate and quotient every magma in the declared carrier strata."""

    sort_name = _validate_magma_signature(signature, operation_name=operation_name)
    sizes = tuple(sorted(set(carrier_sizes)))
    if not sizes or any(type(size) is not int or size < 1 for size in sizes):
        raise ValueError("carrier_sizes must contain positive integers")
    validate_axioms(signature, base_axioms)

    labeled_total = 0
    accepted_total = 0
    orbit_counts: dict[tuple[int, tuple[int, ...]], int] = {}
    for carrier_size in sizes:
        sort_sizes = {sort_name: carrier_size}
        labeled_total += finite_interpretation_count(signature, sort_sizes)
        for model in iter_finite_models(signature, sort_sizes):
            if not all(evaluate_axiom(signature, axiom, model) for axiom in base_axioms):
                continue
            accepted_total += 1
            canonical_table = canonicalize_magma_table(
                model.operation_map[operation_name],
                carrier_size,
            )
            key = (carrier_size, canonical_table)
            orbit_counts[key] = orbit_counts.get(key, 0) + 1

    models = tuple(
        _canonical_model(
            signature=signature,
            sort_name=sort_name,
            operation_name=operation_name,
            carrier_size=carrier_size,
            table=table,
            labeled_orbit_count=orbit_counts[(carrier_size, table)],
        )
        for carrier_size, table in sorted(orbit_counts)
    )
    model_ids = tuple(row.model_id for row in models)
    receipt = FiniteModelUniverseReceipt(
        signature_hash=signature.content_hash,
        carrier_sizes=sizes,
        base_axiom_hashes=tuple(
            sorted(axiom.semantic_hash for axiom in base_axioms)
        ),
        labeled_interpretation_count=labeled_total,
        accepted_labeled_count=accepted_total,
        canonical_model_count=len(models),
        model_order_digest=content_hash({"model_ids": list(model_ids)}),
        isomorphism_policy="all_carrier_permutations_min_lex_table.v1",
    )
    return MagmaModelUniverse(signature=signature, models=models, receipt=receipt)


__all__ = [
    "CANONICAL_MODEL_SCHEMA",
    "CENSUS_SCHEMA",
    "CanonicalModelRecord",
    "FiniteModelUniverseReceipt",
    "MagmaModelUniverse",
    "canonicalize_magma_table",
    "enumerate_magma_model_universe",
]
