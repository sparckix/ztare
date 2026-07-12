"""Structural protocols consumed by the generic finite-theory context."""
from __future__ import annotations

from typing import Any, Mapping, Protocol, runtime_checkable

from ztare.leanmill.finite_model import FiniteModel
from ztare.leanmill.theory_ir import TheorySignature


@runtime_checkable
class FiniteModelRecordLike(Protocol):
    @property
    def model_id(self) -> str: ...

    @property
    def stratum_id(self) -> str: ...

    @property
    def model(self) -> FiniteModel: ...

    def to_json(self) -> Mapping[str, Any]: ...


@runtime_checkable
class FiniteModelUniverseReceiptLike(Protocol):
    @property
    def complete(self) -> bool: ...

    @property
    def receipt_digest(self) -> str: ...

    @property
    def base_axiom_hashes(self) -> tuple[str, ...]: ...

    @property
    def declared_strata(self) -> tuple[Mapping[str, Any], ...]: ...

    def to_json(self) -> Mapping[str, Any]: ...


@runtime_checkable
class FiniteModelUniverseLike(Protocol):
    @property
    def adapter_id(self) -> str: ...

    @property
    def signature(self) -> TheorySignature: ...

    @property
    def models(self) -> tuple[FiniteModelRecordLike, ...]: ...

    @property
    def model_ids(self) -> tuple[str, ...]: ...

    @property
    def receipt(self) -> FiniteModelUniverseReceiptLike: ...

    def to_json(self) -> Mapping[str, Any]: ...


def finite_model_record_weight(record: FiniteModelRecordLike) -> int:
    """Return the represented labeled-model mass across census implementations."""

    value = getattr(record, "multiplicity", None)
    if value is None:
        value = getattr(record, "labeled_orbit_count", 1)
    if type(value) is not int or value < 1:
        raise ValueError("finite model record weight must be positive")
    return value


__all__ = [
    "FiniteModelRecordLike", "FiniteModelUniverseLike", "finite_model_record_weight",
    "FiniteModelUniverseReceiptLike",
]
