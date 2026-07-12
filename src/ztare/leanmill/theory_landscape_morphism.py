"""Anonymous structural fingerprints and testable cross-context proposals."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from ztare.common.constraint_isomorphism import (
    ConstraintMorphism,
    ConstraintSignature,
)
from ztare.leanmill.finite_theory_context import FormalTheoryContext
from ztare.leanmill.theory_ir import content_hash


@dataclass(frozen=True)
class TheoryLandscapeFingerprint:
    context_hash: str
    semantic_formula_class_sizes: tuple[int, ...]
    node_extent_sizes: tuple[int, ...]
    node_closure_sizes: tuple[int, ...]
    minimal_basis_sizes: tuple[int, ...]
    cover_edges: tuple[tuple[str, str], ...]
    synergy_size_histogram: tuple[tuple[int, int], ...]
    stratum_model_counts: tuple[tuple[int, int], ...]
    schema: str = "leanmill.theory_landscape_fingerprint.v1"

    @property
    def fingerprint_id(self) -> str:
        return "landscape:" + content_hash(self.to_json())

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "context_hash": self.context_hash,
            "semantic_formula_class_sizes": list(self.semantic_formula_class_sizes),
            "node_extent_sizes": list(self.node_extent_sizes),
            "node_closure_sizes": list(self.node_closure_sizes),
            "minimal_basis_sizes": list(self.minimal_basis_sizes),
            "cover_edges": [list(row) for row in self.cover_edges],
            "synergy_size_histogram": [list(row) for row in self.synergy_size_histogram],
            "stratum_model_counts": [list(row) for row in self.stratum_model_counts],
        }


def _cover_edges(nodes: tuple[Any, ...]) -> tuple[tuple[str, str], ...]:
    rows: list[tuple[str, str]] = []
    ordered = sorted(nodes, key=lambda row: (row.closure_bits.bit_count(), row.node_id))
    for lower in ordered:
        supers = [
            upper for upper in ordered
            if lower.closure_bits != upper.closure_bits
            and lower.closure_bits & ~upper.closure_bits == 0
        ]
        minimal: list[Any] = []
        for upper in supers:
            if any(mid.closure_bits & ~upper.closure_bits == 0 for mid in minimal):
                continue
            minimal.append(upper)
        rows.extend((lower.node_id, upper.node_id) for upper in minimal)
    return tuple(sorted(rows))


def build_landscape_fingerprint(
    context: FormalTheoryContext, *, max_presentation_size: int = 2
) -> TheoryLandscapeFingerprint:
    nodes = context.generated_theory_nodes(max_presentation_size=max_presentation_size)
    synergy_hist: dict[int, int] = {}
    for node in nodes:
        for generator in node.minimal_generators:
            if len(generator) < 2:
                continue
            size = len(context.synergy_ids(generator))
            synergy_hist[size] = synergy_hist.get(size, 0) + 1
    strata: dict[int, int] = {}
    for model in context.universe.models:
        strata[model.carrier_size] = strata.get(model.carrier_size, 0) + 1
    return TheoryLandscapeFingerprint(
        context_hash=context.context_hash,
        semantic_formula_class_sizes=tuple(sorted(len(row) for row in context.semantic_formula_classes())),
        node_extent_sizes=tuple(sorted(row.extent_bits.bit_count() for row in nodes)),
        node_closure_sizes=tuple(sorted(row.closure_bits.bit_count() for row in nodes)),
        minimal_basis_sizes=tuple(
            sorted(min(map(len, row.minimal_generators)) for row in nodes)
        ),
        cover_edges=_cover_edges(nodes),
        synergy_size_histogram=tuple(sorted(synergy_hist.items())),
        stratum_model_counts=tuple(sorted(strata.items())),
    )


def propose_landscape_transport(
    source: TheoryLandscapeFingerprint,
    target: TheoryLandscapeFingerprint,
) -> ConstraintMorphism:
    """Nominate a mapping; all preservation obligations remain pending."""
    source_sig = ConstraintSignature(
        name="source_theory_landscape",
        components={
            "semantic_partition": "sequence",
            "closure_node_spectrum": "sequence",
            "cover_relation": "relation",
            "synergy_motif_spectrum": "sequence",
        },
    )
    target_sig = ConstraintSignature(
        name="target_theory_landscape",
        components=dict(source_sig.components),
    )
    component_map = {
        key: {
            "target": key,
            "source_type": value,
            "target_type": value,
            "transform": "anonymous_structural_match",
        }
        for key, value in source_sig.components.items()
    }
    obligations = [
        {
            "claim": f"preserve {key} under compiled target mapping",
            "status": "pending",
            "source_ref": source.fingerprint_id,
            "target_ref": target.fingerprint_id,
        }
        for key in component_map
    ]
    return ConstraintMorphism(
        source_signature=source_sig,
        target_signature=target_sig,
        component_map=component_map,
        preservation_obligations=obligations,
        target_discriminator={
            "kind": "target_context_replay",
            "target_context_hash": target.context_hash,
            "reject_on": "mapped formula, definition, or query fails local incidence evaluation",
        },
        relation="embedding",
    )


def test_compiled_landscape_mapping(
    morphism: ConstraintMorphism,
    *,
    compiled_mapping: Mapping[str, str],
    target_test: Callable[[Mapping[str, str]], bool],
) -> dict[str, Any]:
    required = set(morphism.component_map)
    if set(compiled_mapping) != required:
        raise ValueError("compiled mapping must cover every proposed component")
    passed = target_test(compiled_mapping) is True
    core = {
        "schema": "leanmill.compiled_landscape_mapping_test.v1",
        "morphism_hash": morphism.content_hash(),
        "compiled_mapping": dict(sorted(compiled_mapping.items())),
        "target_context_hash": morphism.target_discriminator.get("target_context_hash"),
        "status": "passed_local_target_test" if passed else "refuted",
        "axiom_authority_eligible": False,
        "next_gate": "separate signed obligation verification" if passed else "none",
    }
    return {**core, "receipt_sha256": content_hash(core)}


__all__ = [
    "TheoryLandscapeFingerprint", "build_landscape_fingerprint",
    "propose_landscape_transport", "test_compiled_landscape_mapping",
]
