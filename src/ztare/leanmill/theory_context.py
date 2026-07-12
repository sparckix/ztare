"""Minimal context interface shared by formal and evidence-induced campaigns."""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Protocol, Sequence

from ztare.common.finite_incidence_context import FiniteIncidenceContext
from ztare.leanmill.finite_theory_context import SemanticTheoryNode
from ztare.leanmill.theory_ir import TheorySignature


class ContextWitness(Protocol):
    model_id: str
    stratum_id: str


class TheoryLandscapeContext(Protocol):
    signature: TheorySignature
    incidence: FiniteIncidenceContext
    schema: str

    @property
    def context_hash(self) -> str: ...

    @property
    def formula_ids(self) -> tuple[str, ...]: ...

    @property
    def object_ids(self) -> tuple[str, ...]: ...

    @property
    def complete(self) -> bool: ...

    @property
    def completeness_receipt_digest(self) -> str: ...

    @property
    def object_identity_policy(self) -> str: ...

    @property
    def object_contrast_admissible(self) -> bool: ...

    def anonymous_formula_profile(self, formula_id: str) -> Mapping[str, Any]: ...
    def anonymous_object_profile(self, object_id: str) -> Mapping[str, Any]: ...
    def closure_ids(self, formula_ids: Iterable[str]) -> tuple[str, ...]: ...
    def semantic_formula_classes(self) -> tuple[tuple[str, ...], ...]: ...
    def synergy_ids(self, presentation: Sequence[str]) -> tuple[str, ...]: ...
    def cheap_structural_baseline(
        self,
        presentation: Sequence[str],
        candidate_formula_ids: Sequence[str],
    ) -> Mapping[str, Any] | None: ...
    def independence_witness(
        self, presentation: Sequence[str], target_formula_id: str
    ) -> ContextWitness | None: ...
    def separation_witness(
        self, left_formula_ids: Iterable[str], right_formula_ids: Iterable[str]
    ) -> ContextWitness | None: ...
    def generated_theory_nodes(
        self, *, max_presentation_size: int, semantic_quotient: bool = False
    ) -> tuple[SemanticTheoryNode, ...]: ...


__all__ = ["ContextWitness", "TheoryLandscapeContext"]
