"""LeanMill binding for the substrate-neutral finite incidence context."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ztare.common.finite_incidence_context import (
    FiniteIncidenceContext,
    GeneratedConcept,
    build_incidence_context,
)
from ztare.leanmill.finite_model import evaluate_axiom
from ztare.leanmill.finite_structure_baseline import finite_structural_baseline
from ztare.leanmill.finite_model_universe import (
    FiniteModelRecordLike,
    FiniteModelUniverseLike,
)
from ztare.leanmill.common import write_json_atomic
from ztare.leanmill.theory_ir import (
    AxiomFormula,
    TheorySignature,
    anonymous_formula_ir,
    content_hash,
    validate_axioms,
)


FORMAL_CONTEXT_SCHEMA = "leanmill.formal_theory_context.v1"
FORMULA_PROFILE_SCHEMA = "leanmill.formula_profile.v1"
THEORY_NODE_SCHEMA = "leanmill.semantic_theory_node.v1"
_GENERATED_NODE_CACHE: dict[
    tuple[str, int, bool], tuple["SemanticTheoryNode", ...]
] = {}


@dataclass(frozen=True)
class FormulaProfile:
    formula_id: str
    axiom: AxiomFormula
    truth_bits: int
    schema: str = FORMULA_PROFILE_SCHEMA

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "formula_id": self.formula_id,
            "semantic_sha256": self.axiom.semantic_hash,
            "truth_bits_hex": hex(self.truth_bits),
            "axiom": self.axiom.to_json(),
        }


@dataclass(frozen=True)
class SemanticTheoryNode:
    context_hash: str
    node_id: str
    extent_bits: int
    closure_bits: int
    minimal_generators: tuple[tuple[str, ...], ...]
    presentation_count: int
    schema: str = THEORY_NODE_SCHEMA

    @classmethod
    def from_concept(
        cls,
        concept: GeneratedConcept,
        *,
        formal_context_hash: str,
    ) -> "SemanticTheoryNode":
        return cls(
            context_hash=formal_context_hash,
            node_id=content_hash(
                {
                    "context_hash": formal_context_hash,
                    "extent_bits_hex": hex(concept.extent_bits),
                }
            ),
            extent_bits=concept.extent_bits,
            closure_bits=concept.closure_bits,
            minimal_generators=concept.minimal_generators,
            presentation_count=concept.presentation_count,
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "context_hash": self.context_hash,
            "node_id": self.node_id,
            "extent_bits_hex": hex(self.extent_bits),
            "closure_bits_hex": hex(self.closure_bits),
            "minimal_generators": [list(row) for row in self.minimal_generators],
            "presentation_count": self.presentation_count,
        }


@dataclass(frozen=True)
class FormalTheoryContext:
    signature: TheorySignature
    universe: FiniteModelUniverseLike
    formula_profiles: tuple[FormulaProfile, ...]
    base_axioms: tuple[AxiomFormula, ...]
    incidence: FiniteIncidenceContext
    schema: str = FORMAL_CONTEXT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != FORMAL_CONTEXT_SCHEMA:
            raise ValueError(f"unsupported formal context schema: {self.schema!r}")
        if self.signature.content_hash != self.universe.signature.content_hash:
            raise ValueError("formal context signature does not match model universe")
        formula_ids = tuple(row.formula_id for row in self.formula_profiles)
        if formula_ids != self.incidence.attribute_ids:
            raise ValueError("formula profile order does not match incidence context")
        if self.universe.model_ids != self.incidence.object_ids:
            raise ValueError("model order does not match incidence context")
        for profile, incidence_profile in zip(
            self.formula_profiles, self.incidence.profiles, strict=True
        ):
            if profile.truth_bits != incidence_profile.truth_bits:
                raise ValueError("formula truth bits do not match incidence context")

    @property
    def context_hash(self) -> str:
        return content_hash(
            {
                "schema": self.schema,
                "signature_sha256": self.signature.content_hash,
                "model_census_receipt_sha256": self.universe.receipt.receipt_digest,
                "base_axiom_sha256s": [
                    axiom.semantic_hash for axiom in self.base_axioms
                ],
                "formula_ids": [row.formula_id for row in self.formula_profiles],
                "incidence_context_hash": self.incidence.context_hash,
            }
        )

    @property
    def formula_ids(self) -> tuple[str, ...]:
        return tuple(row.formula_id for row in self.formula_profiles)

    @property
    def object_ids(self) -> tuple[str, ...]:
        return self.universe.model_ids

    @property
    def complete(self) -> bool:
        return self.incidence.exact and self.universe.receipt.complete

    @property
    def completeness_receipt_digest(self) -> str:
        return self.universe.receipt.receipt_digest

    @property
    def object_identity_policy(self) -> str:
        receipt = dict(self.universe.receipt.to_json())
        policy = str(
            receipt.get("quotient_policy")
            or receipt.get("isomorphism_policy")
            or ""
        )
        if policy == "functor_image_then_sortwise_isomorphism.v1":
            return "sortwise_isomorphism_canonicalization.v1"
        return policy

    @property
    def object_contrast_admissible(self) -> bool:
        return self.object_identity_policy in {
            "all_carrier_permutations_min_lex_table.v1",
            "sortwise_isomorphism_canonicalization.v1",
        }

    def anonymous_formula_profile(self, formula_id: str) -> dict[str, Any]:
        profile = self._profile_map().get(formula_id)
        if profile is None:
            raise ValueError("unknown formula_id in frozen context")
        return {
            "formula_id": formula_id,
            "truth_count": profile.truth_bits.bit_count(),
            "formula": anonymous_formula_ir(self.signature, profile.axiom.formula),
        }

    def anonymous_object_profile(self, object_id: str) -> dict[str, Any]:
        try:
            record = self._model_map()[object_id]
        except KeyError as exc:
            raise ValueError("unknown model_id in frozen context") from exc
        model = record.model
        sort_aliases = {
            row.name: f"sort_{index}"
            for index, row in enumerate(self.signature.sorts)
        }
        return {
            "object_id": record.model_id,
            "stratum_id": record.stratum_id,
            "object_kind": "finite_structure",
            "carrier_encoding": "zero_based_indices",
            "table_order": "lexicographic_argument_indices_last_argument_fastest",
            "sort_sizes": {
                sort_aliases[row.name]: model.sort_size_map[row.name]
                for row in self.signature.sorts
            },
            "operations": [
                {
                    "symbol": f"op_{index}",
                    "table": list(model.operation_map[row.name]),
                }
                for index, row in enumerate(self.signature.operations)
            ],
            "relations": [
                {
                    "symbol": f"rel_{index}",
                    "table": list(model.relation_map[row.name]),
                }
                for index, row in enumerate(self.signature.relations)
            ],
        }

    def _profile_map(self) -> dict[str, FormulaProfile]:
        return {row.formula_id: row for row in self.formula_profiles}

    def _model_map(self) -> dict[str, FiniteModelRecordLike]:
        return {row.model_id: row for row in self.universe.models}

    def extent_model_ids(self, formula_ids: Iterable[str]) -> tuple[str, ...]:
        return self.incidence.extent_object_ids(formula_ids)

    def extent_models(
        self, formula_ids: Iterable[str]
    ) -> tuple[FiniteModelRecordLike, ...]:
        by_id = self._model_map()
        return tuple(by_id[model_id] for model_id in self.extent_model_ids(formula_ids))

    def closure_ids(self, formula_ids: Iterable[str]) -> tuple[str, ...]:
        return self.incidence.closure_ids(formula_ids)

    def closure_axioms(self, formula_ids: Iterable[str]) -> tuple[AxiomFormula, ...]:
        profiles = self._profile_map()
        return tuple(profiles[formula_id].axiom for formula_id in self.closure_ids(formula_ids))

    def semantic_formula_classes(self) -> tuple[tuple[str, ...], ...]:
        return self.incidence.semantic_attribute_classes()

    def synergy_ids(self, presentation: Sequence[str]) -> tuple[str, ...]:
        return self.incidence.synergy_ids(presentation)

    def cheap_structural_baseline(
        self,
        presentation: Sequence[str],
        candidate_formula_ids: Sequence[str],
    ) -> Mapping[str, Any]:
        """Return finite-context consequences explained by primitive table shapes."""

        baseline = finite_structural_baseline(
            context_hash=self.context_hash,
            signature=self.signature,
            models=self.universe.models,
            incidence=self.incidence,
            presentation_ids=presentation,
            candidate_formula_ids=candidate_formula_ids,
        )
        return baseline.to_json(base_count=self.incidence.base_mask.bit_count())

    def independence_witness(
        self,
        presentation: Sequence[str],
        target_formula_id: str,
    ) -> FiniteModelRecordLike | None:
        model_id = self.incidence.independence_object_id(
            presentation, target_formula_id
        )
        return self._model_map().get(model_id) if model_id else None

    def implication_countermodel(
        self,
        premise_formula_ids: Iterable[str],
        target_formula_id: str,
    ) -> FiniteModelRecordLike | None:
        model_id = self.incidence.implication_counterexample_object_id(
            premise_formula_ids,
            target_formula_id,
        )
        return self._model_map().get(model_id) if model_id else None

    def separation_witness(
        self,
        left_formula_ids: Iterable[str],
        right_formula_ids: Iterable[str],
    ) -> FiniteModelRecordLike | None:
        model_id = self.incidence.separation_object_id(
            left_formula_ids, right_formula_ids
        )
        return self._model_map().get(model_id) if model_id else None

    def generated_theory_nodes(
        self,
        *,
        max_presentation_size: int,
        semantic_quotient: bool = False,
    ) -> tuple[SemanticTheoryNode, ...]:
        key = (self.context_hash, max_presentation_size, semantic_quotient)
        cached = _GENERATED_NODE_CACHE.get(key)
        if cached is not None:
            return cached
        generated = tuple(
            SemanticTheoryNode.from_concept(
                row,
                formal_context_hash=self.context_hash,
            )
            for row in self.incidence.generated_concepts(
                max_presentation_size=max_presentation_size,
                semantic_quotient=semantic_quotient,
            )
        )
        if len(_GENERATED_NODE_CACHE) >= 16:
            _GENERATED_NODE_CACHE.pop(next(iter(_GENERATED_NODE_CACHE)))
        _GENERATED_NODE_CACHE[key] = generated
        return generated

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "context_hash": self.context_hash,
            "signature": self.signature.to_json(),
            "model_census": self.universe.receipt.to_json(),
            "base_axioms": [axiom.to_json() for axiom in self.base_axioms],
            "formula_profiles": [row.to_json() for row in self.formula_profiles],
            "incidence": self.incidence.to_json(),
        }


def _formula_id(axiom: AxiomFormula) -> str:
    return "formula:" + axiom.semantic_hash


def build_formal_theory_context(
    *,
    signature: TheorySignature,
    formulas: Sequence[AxiomFormula],
    universe: FiniteModelUniverseLike,
    base_axioms: Sequence[AxiomFormula] = (),
) -> FormalTheoryContext:
    """Evaluate every formula on every canonical model in a complete census."""

    if not universe.receipt.complete:
        raise ValueError("formal theory context requires a complete model census")
    if signature.content_hash != universe.signature.content_hash:
        raise ValueError("signature does not match model universe")
    validate_axioms(signature, tuple(base_axioms) + tuple(formulas))

    census_base_hashes = set(universe.receipt.base_axiom_hashes)
    context_base_hashes = {axiom.semantic_hash for axiom in base_axioms}
    if not census_base_hashes <= context_base_hashes:
        raise ValueError(
            "context base axioms must include every census-filtering axiom"
        )

    unique: dict[str, AxiomFormula] = {}
    for axiom in formulas:
        unique.setdefault(_formula_id(axiom), axiom)
    if not unique:
        raise ValueError("formal theory context requires at least one formula")

    base_mask = 0
    for model_index, record in enumerate(universe.models):
        if all(evaluate_axiom(signature, axiom, record.model) for axiom in base_axioms):
            base_mask |= 1 << model_index

    truth_bits: dict[str, int] = {}
    profiles: list[FormulaProfile] = []
    for formula_id, axiom in sorted(unique.items()):
        bits = 0
        for model_index, record in enumerate(universe.models):
            if evaluate_axiom(signature, axiom, record.model):
                bits |= 1 << model_index
        truth_bits[formula_id] = bits
        profiles.append(
            FormulaProfile(
                formula_id=formula_id,
                axiom=axiom,
                truth_bits=bits,
            )
        )

    incidence = build_incidence_context(
        object_ids=universe.model_ids,
        attribute_truth_bits=truth_bits,
        base_mask=base_mask,
        exact=True,
        completeness_ref=universe.receipt.receipt_digest,
        provenance_refs={
            formula_id: "semantic_sha256:" + axiom.semantic_hash
            for formula_id, axiom in unique.items()
        },
    )
    return FormalTheoryContext(
        signature=signature,
        universe=universe,
        formula_profiles=tuple(profiles),
        base_axioms=tuple(sorted(base_axioms, key=lambda axiom: axiom.semantic_hash)),
        incidence=incidence,
    )


def formal_theory_context_snapshot(context: FormalTheoryContext) -> dict[str, Any]:
    """Self-contained replay bundle; no provider or external corpus is needed."""
    core = {
        "schema": "leanmill.formal_theory_context_snapshot.v1",
        "context_hash": context.context_hash,
        "signature": context.signature.to_json(),
        "base_axioms": [row.to_json() for row in context.base_axioms],
        "formulas": [row.axiom.to_json() for row in context.formula_profiles],
        "model_universe": dict(context.universe.to_json()),
        "materialized_context": context.to_json(),
    }
    return {**core, "snapshot_sha256": content_hash(core)}


def save_formal_theory_context(context: FormalTheoryContext, path: str | Path) -> Path:
    return write_json_atomic(path, formal_theory_context_snapshot(context))


def formal_theory_context_from_snapshot(
    value: Mapping[str, Any],
) -> FormalTheoryContext:
    """Replay a context from bytes already frozen by its ingress owner."""

    raw = dict(value)
    if not isinstance(raw, Mapping) or raw.get("schema") != "leanmill.formal_theory_context_snapshot.v1":
        raise ValueError("unsupported formal theory context snapshot")
    unsigned = dict(raw)
    snapshot_hash = unsigned.pop("snapshot_sha256", None)
    if snapshot_hash != content_hash(unsigned):
        raise ValueError("formal theory context snapshot hash")
    signature = TheorySignature.from_json(raw["signature"])
    universe_row = raw.get("model_universe")
    if not isinstance(universe_row, Mapping):
        raise ValueError("snapshot model universe missing")
    from ztare.leanmill.theory_adapter_registry import load_model_universe

    universe = load_model_universe(universe_row)
    if universe.signature.content_hash != signature.content_hash:
        raise ValueError("snapshot universe signature")
    materialized = raw.get("materialized_context")
    if isinstance(materialized, Mapping):
        from ztare.common.finite_incidence_context import FiniteIncidenceContext

        profiles = tuple(
            FormulaProfile(
                formula_id=str(row["formula_id"]),
                axiom=AxiomFormula.from_json(row["axiom"]),
                truth_bits=int(str(row["truth_bits_hex"]), 16),
                schema=str(row["schema"]),
            )
            for row in materialized.get("formula_profiles") or ()
            if isinstance(row, Mapping)
        )
        context = FormalTheoryContext(
            signature=signature,
            universe=universe,
            formula_profiles=profiles,
            base_axioms=tuple(
                AxiomFormula.from_json(row) for row in materialized.get("base_axioms") or ()
            ),
            incidence=FiniteIncidenceContext.from_json(materialized["incidence"]),
            schema=str(materialized.get("schema") or ""),
        )
        if materialized.get("context_hash") != context.context_hash:
            raise ValueError("materialized formal context hash")
    else:
        context = build_formal_theory_context(
            signature=signature,
            formulas=tuple(AxiomFormula.from_json(row) for row in raw["formulas"]),
            universe=universe,
            base_axioms=tuple(AxiomFormula.from_json(row) for row in raw["base_axioms"]),
        )
    if raw.get("context_hash") != context.context_hash:
        raise ValueError("replayed formal context hash")
    return context


def load_formal_theory_context(path: str | Path) -> FormalTheoryContext:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise ValueError("unsupported formal theory context snapshot")
    return formal_theory_context_from_snapshot(raw)


__all__ = [
    "FORMAL_CONTEXT_SCHEMA",
    "FORMULA_PROFILE_SCHEMA",
    "THEORY_NODE_SCHEMA",
    "FormalTheoryContext",
    "FormulaProfile",
    "SemanticTheoryNode",
    "build_formal_theory_context",
    "formal_theory_context_snapshot",
    "formal_theory_context_from_snapshot",
    "load_formal_theory_context",
    "save_formal_theory_context",
]
