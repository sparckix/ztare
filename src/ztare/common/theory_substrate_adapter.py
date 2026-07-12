"""Shared outer contract for exact or evidence-induced theory substrates."""
from __future__ import annotations

from typing import Any, Protocol, Sequence, runtime_checkable

from ztare.common.abstraction_functor import AbstractionFunctor
from ztare.common.finite_incidence_context import FiniteIncidenceContext


@runtime_checkable
class TheorySubstrateAdapter(AbstractionFunctor, Protocol):
    """Abstraction/lowering plus theory-context and raw-check capabilities."""

    @property
    def adapter_id(self) -> str: ...

    def signature(self, state: Any) -> Any: ...

    def base_axioms(self, state: Any) -> Sequence[Any]: ...

    def build_context(self, state: Any) -> FiniteIncidenceContext: ...

    def check_raw(self, prediction: Any, observation: Any) -> dict[str, Any]: ...


__all__ = ["TheorySubstrateAdapter"]
