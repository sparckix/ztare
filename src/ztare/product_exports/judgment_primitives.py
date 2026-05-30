"""Typed, public-safe judgment primitive export for product surfaces.

Boundary discipline:
1. This module exports only product-safe repair primitives.
2. It does NOT expose private seam identifiers, private file paths, or
   kernel-only runtime control surfaces as if they were product primitives.
3. It models the fractal as lineage, not identity. A product primitive may
   have analogues at other scales, but those layers retain distinct roles.

Why this exists:
- The main kernel has multiple vocabularies: universal research operations,
  reflexive engineering primitives, runtime pivot heuristics, fit-time
  transforms, verification ops, and engineering patterns.
- Downstream product repos need a thin, stable layer for user-facing repair
  moves. They do not need the full kernel taxonomy.
- The safe move is export separation, not vocabulary merger.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any


EXPORT_VERSION = "judgment_primitives.v1"


@dataclass(frozen=True)
class PrimitiveLineage:
    """Cross-scale aliases for one product primitive.

    These are analogues, not identities. They exist to explain lineage and
    enable later validation, not to collapse all layers into one blob.
    """

    universal_language: str
    reflexive_analogues: tuple[str, ...] = ()
    runtime_analogues: tuple[str, ...] = ()
    coordinate_analogues: tuple[str, ...] = ()


@dataclass(frozen=True)
class JudgmentPrimitive:
    key: str
    title: str
    plain_label: str
    description: str
    repair_prompt: str
    surfaces: tuple[str, ...]
    lineage: PrimitiveLineage


@dataclass(frozen=True)
class NonPrimitiveRuntimeConcept:
    key: str
    title: str
    role: str
    description: str
    not_for_export_as_primitive: bool = True


JUDGMENT_PRIMITIVES_V1: tuple[JudgmentPrimitive, ...] = (
    JudgmentPrimitive(
        key="problem_reformulation",
        title="Problem Reformulation & Reduction",
        plain_label="Reframe the claim",
        description=(
            "Restate the claim in a form the current evidence can actually answer, "
            "or narrow it to the discriminating question."
        ),
        repair_prompt=(
            "Rewrite the claim so the evidence on the table could actually prove "
            "or disconfirm it."
        ),
        surfaces=("clearjudgment", "mini-ztare"),
        lineage=PrimitiveLineage(
            universal_language="Problem Reformulation & Reduction",
            runtime_analogues=("coordinate_compression",),
            coordinate_analogues=("log", "signed_log"),
        ),
    ),
    JudgmentPrimitive(
        key="generalization_abstraction",
        title="Generalization & Abstraction",
        plain_label="Change the level of abstraction",
        description=(
            "Broaden or relax the category boundary so the argument is not "
            "winning by definition or by an overly local frame."
        ),
        repair_prompt=(
            "Move up one level and state the broader category the argument must "
            "survive."
        ),
        surfaces=("clearjudgment", "mini-ztare"),
        lineage=PrimitiveLineage(
            universal_language="Generalization & Abstraction",
            reflexive_analogues=("Token-Optimized Self-Modeling", "Research Taste Router"),
            runtime_analogues=("dimensional_shift", "category_switch"),
            coordinate_analogues=("signed_log", "softplus"),
        ),
    ),
    JudgmentPrimitive(
        key="decomposition_recomposition",
        title="Decomposition & Recomposition",
        plain_label="Break the argument into parts",
        description=(
            "Split the claim into separable components, test each one directly, "
            "then rebuild only what survives."
        ),
        repair_prompt=(
            "Name the subclaims explicitly, test them one by one, then reassemble "
            "the surviving structure."
        ),
        surfaces=("clearjudgment", "mini-ztare"),
        lineage=PrimitiveLineage(
            universal_language="Decomposition & Recomposition",
            reflexive_analogues=("Hybrid Persona Router",),
            runtime_analogues=("entropy_stripping",),
        ),
    ),
    JudgmentPrimitive(
        key="local_to_global_assembly",
        title="Local-to-Global Assembly",
        plain_label="Rebuild the whole from local support",
        description=(
            "Show how a local result scales, transports, or aggregates before "
            "claiming the global conclusion."
        ),
        repair_prompt=(
            "State what is locally established, then identify the explicit gluing "
            "or scaling step needed for the global claim."
        ),
        surfaces=("clearjudgment", "mini-ztare"),
        lineage=PrimitiveLineage(
            universal_language="Local-to-Global Assembly",
            reflexive_analogues=("Hybrid Persona Router",),
        ),
    ),
    JudgmentPrimitive(
        key="canonical_form_invariance",
        title="Canonical Form & Invariance",
        plain_label="Define the invariant or decision rule",
        description=(
            "Replace a fragile proxy with the measurement, invariant, or "
            "comparison class that the argument actually needs."
        ),
        repair_prompt=(
            "Name the invariant, metric, or canonical representative that would "
            "make the argument robust to relabeling or proxy drift."
        ),
        surfaces=("clearjudgment", "mini-ztare"),
        lineage=PrimitiveLineage(
            universal_language="Canonical Form & Invariance",
            reflexive_analogues=("Procedural Self-Audit",),
        ),
    ),
    JudgmentPrimitive(
        key="cross_domain_translation",
        title="Cross-Domain Translation",
        plain_label="Translate the claim into a tractable frame",
        description=(
            "Move the argument into a different representation where the core "
            "issue becomes measurable, comparable, or testable."
        ),
        repair_prompt=(
            "Translate the problem into a different frame where the same structure "
            "can be checked more directly."
        ),
        surfaces=("clearjudgment", "mini-ztare"),
        lineage=PrimitiveLineage(
            universal_language="Cross-Domain Translation",
            reflexive_analogues=("Residual Isomorphism",),
            runtime_analogues=("coordinate_compression",),
            coordinate_analogues=("log", "signed_log"),
        ),
    ),
)


NON_PRIMITIVE_RUNTIME_CONCEPTS_V1: tuple[NonPrimitiveRuntimeConcept, ...] = (
    NonPrimitiveRuntimeConcept(
        key="topological_pivot",
        title="Topological Pivot",
        role="runtime_meta_decision",
        description=(
            "Decision that the current framing is wrong and that the search should "
            "reframe rather than continue local basin search. This is a runtime "
            "decision heuristic, not a product repair primitive."
        ),
    ),
    NonPrimitiveRuntimeConcept(
        key="pivot_heuristic_module",
        title="Pivot Heuristic Module",
        role="runtime_injection",
        description=(
            "Tactical mutator-prompt module such as coordinate compression or "
            "category switch. Useful as lineage, but not exported as the primary "
            "product vocabulary."
        ),
    ),
    NonPrimitiveRuntimeConcept(
        key="fit_time_transform",
        title="Fit-Time Transform",
        role="coordinate_scale_apparatus",
        description=(
            "Mathematical transform used inside fitting or representation change. "
            "These are lower-scale apparatus elements, not user-facing judgment "
            "primitives."
        ),
    ),
)


def _primitive_public_dict(primitive: JudgmentPrimitive) -> dict[str, Any]:
    return {
        "key": primitive.key,
        "title": primitive.title,
        "plain_label": primitive.plain_label,
        "description": primitive.description,
        "repair_prompt": primitive.repair_prompt,
        "surfaces": list(primitive.surfaces),
        "lineage": {
            "universal_language": primitive.lineage.universal_language,
            "reflexive_analogues": list(primitive.lineage.reflexive_analogues),
            "runtime_analogues": list(primitive.lineage.runtime_analogues),
            "coordinate_analogues": list(primitive.lineage.coordinate_analogues),
        },
    }


def _non_primitive_public_dict(concept: NonPrimitiveRuntimeConcept) -> dict[str, Any]:
    return asdict(concept)


def export_judgment_primitives_payload() -> dict[str, Any]:
    return {
        "export_version": EXPORT_VERSION,
        "role_boundary": {
            "product_primitives": (
                "User-facing repair moves for ClearJudgment and Mini-ZTARE."
            ),
            "non_primitive_runtime_concepts": (
                "Kernel or runtime concepts that should not be collapsed into the "
                "product primitive vocabulary."
            ),
            "warning": (
                "Fractal lineage does not imply identity. Cross-scale aliases are "
                "for translation and audit, not for merging all vocabularies."
            ),
        },
        "public_lineage_sources": [
            "paper5b_universal_language",
            "reflexive_engineering",
            "cross_scale_fractal_map",
        ],
        "judgment_primitives": [
            _primitive_public_dict(p) for p in JUDGMENT_PRIMITIVES_V1
        ],
        "non_primitive_runtime_concepts": [
            _non_primitive_public_dict(c) for c in NON_PRIMITIVE_RUNTIME_CONCEPTS_V1
        ],
    }


def render_typescript_module() -> str:
    payload = export_judgment_primitives_payload()
    json_blob = json.dumps(payload, indent=2, sort_keys=True)
    return (
        "// GENERATED FILE. Source of truth: ZTARE product export.\n"
        "// Do not hand-edit in downstream product repos.\n\n"
        f"export const JUDGMENT_PRIMITIVES_EXPORT = {json_blob} as const;\n\n"
        "export type JudgmentPrimitiveExport = typeof JUDGMENT_PRIMITIVES_EXPORT;\n"
    )


__all__ = [
    "EXPORT_VERSION",
    "PrimitiveLineage",
    "JudgmentPrimitive",
    "NonPrimitiveRuntimeConcept",
    "JUDGMENT_PRIMITIVES_V1",
    "NON_PRIMITIVE_RUNTIME_CONCEPTS_V1",
    "export_judgment_primitives_payload",
    "render_typescript_module",
]
