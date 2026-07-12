"""Cheap, signature-generic baselines for finite structural collapse.

The theory navigator should not receive discovery credit merely because a
presentation forces an operation or relation into one of the smallest table
templates.  This module detects those templates directly from finite models
and asks the incidence context which candidate consequences they already
explain.  Every conclusion remains conditional on the frozen finite context.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from math import log2
from threading import RLock
from typing import Any, Mapping, Sequence

from ztare.common.finite_incidence_context import FiniteIncidenceContext
from ztare.leanmill.finite_model_universe import FiniteModelRecordLike
from ztare.leanmill.theory_ir import TheorySignature, content_hash


STRUCTURAL_BASELINE_SCHEMA = "leanmill.finite_low_complexity_baseline.v1"
STRUCTURAL_BASELINE_REF = "leanmill.finite_low_complexity_structure.v1"
_TEMPLATE_CACHE: dict[tuple[str, str], tuple["FiniteStructureTemplate", ...]] = {}
_TEMPLATE_CACHE_MAX = 32
_CACHE_LOCK = RLock()


@dataclass(frozen=True)
class FiniteStructureTemplate:
    """One anonymous low-description-length table shape."""

    template_id: str
    symbol_kind: str
    symbol_index: int
    shape: str
    argument_index: int | None
    support_bits: int
    closure_ids: tuple[str, ...]

    def to_json(self, *, base_count: int) -> dict[str, Any]:
        support_count = self.support_bits.bit_count()
        return {
            "template_id": self.template_id,
            "symbol_kind": self.symbol_kind,
            "symbol_index": self.symbol_index,
            "shape": self.shape,
            "argument_index": self.argument_index,
            "support_count": support_count,
            "base_count": base_count,
            "template_information_bits": round(
                log2(base_count / support_count)
                if base_count and support_count
                else 0.0,
                8,
            ),
            "closure_formula_ids": list(self.closure_ids),
        }


@dataclass(frozen=True)
class FiniteStructuralBaseline:
    """Consequences explained by primitive table templates in one context."""

    context_hash: str
    presentation_ids: tuple[str, ...]
    presentation_extent_size: int
    forced_templates: tuple[FiniteStructureTemplate, ...]
    conditioning_bits: int
    explained_formula_ids: tuple[str, ...]
    explanation_map: Mapping[str, tuple[str, ...]]
    schema: str = STRUCTURAL_BASELINE_SCHEMA

    def to_json(self, *, base_count: int) -> dict[str, Any]:
        core = {
            "schema": self.schema,
            "authority": "exact_finite_context_template_replay",
            "claim_boundary": (
                "template forcing, residual conditioning, and explained formulas "
                "are conditional on the frozen finite context"
            ),
            "context_hash": self.context_hash,
            "presentation_ids": list(self.presentation_ids),
            "presentation_extent_size": self.presentation_extent_size,
            "base_model_count": base_count,
            "conditioning_bits_hex": hex(self.conditioning_bits),
            "conditioning_model_count": self.conditioning_bits.bit_count(),
            "forced_templates": [
                row.to_json(base_count=base_count) for row in self.forced_templates
            ],
            "explained_formula_ids": list(self.explained_formula_ids),
            "explanation_map": {
                key: list(value) for key, value in sorted(self.explanation_map.items())
            },
        }
        return {**core, "receipt_sha256": content_hash(core)}


def _operation_matches_constant(table: Sequence[int]) -> bool:
    return bool(table) and len(set(table)) == 1


def _operation_matches_projection(
    *,
    table: Sequence[int],
    argument_sizes: Sequence[int],
    argument_index: int,
) -> bool:
    return all(
        output == arguments[argument_index]
        for output, arguments in zip(
            table,
            product(*(range(size) for size in argument_sizes)),
            strict=True,
        )
    )


def _operation_ignores_argument(
    *,
    table: Sequence[int],
    argument_sizes: Sequence[int],
    argument_index: int,
) -> bool:
    """Return whether varying one argument can never change the output."""

    outputs: dict[tuple[int, ...], int] = {}
    for output, arguments in zip(
        table,
        product(*(range(size) for size in argument_sizes)),
        strict=True,
    ):
        other_arguments = (
            arguments[:argument_index] + arguments[argument_index + 1 :]
        )
        prior = outputs.setdefault(other_arguments, output)
        if prior != output:
            return False
    return True


def _template_supports(
    signature: TheorySignature,
    models: Sequence[FiniteModelRecordLike],
) -> tuple[tuple[str, str, int, str, int | None, int], ...]:
    rows: list[tuple[str, str, int, str, int | None, int]] = []
    for symbol_index, operation in enumerate(signature.operations):
        if not operation.arg_sorts:
            continue
        constant_bits = 0
        projection_bits = [0 for _ in operation.arg_sorts]
        inessential_argument_bits = [0 for _ in operation.arg_sorts]
        for model_index, record in enumerate(models):
            model = record.model
            table = model.operation_map[operation.name]
            if _operation_matches_constant(table):
                constant_bits |= 1 << model_index
            sizes = model.sort_size_map
            argument_sizes = tuple(sizes[sort] for sort in operation.arg_sorts)
            for argument_index, argument_sort in enumerate(operation.arg_sorts):
                if len(operation.arg_sorts) > 1 and _operation_ignores_argument(
                    table=table,
                    argument_sizes=argument_sizes,
                    argument_index=argument_index,
                ):
                    inessential_argument_bits[argument_index] |= 1 << model_index
                if operation.result_sort != argument_sort:
                    continue
                if _operation_matches_projection(
                    table=table,
                    argument_sizes=argument_sizes,
                    argument_index=argument_index,
                ):
                    projection_bits[argument_index] |= 1 << model_index
        rows.append(
            (
                f"operation:{symbol_index}:constant",
                "operation",
                symbol_index,
                "constant",
                None,
                constant_bits,
            )
        )
        rows.extend(
            (
                f"operation:{symbol_index}:projection:{argument_index}",
                "operation",
                symbol_index,
                "projection",
                argument_index,
                support_bits,
            )
            for argument_index, support_bits in enumerate(projection_bits)
            if operation.result_sort == operation.arg_sorts[argument_index]
        )
        rows.extend(
            (
                f"operation:{symbol_index}:inessential_argument:{argument_index}",
                "operation",
                symbol_index,
                "inessential_argument",
                argument_index,
                support_bits,
            )
            for argument_index, support_bits in enumerate(
                inessential_argument_bits
            )
        )
    for symbol_index, relation in enumerate(signature.relations):
        if not relation.arg_sorts:
            continue
        empty_bits = 0
        full_bits = 0
        for model_index, record in enumerate(models):
            table = record.model.relation_map[relation.name]
            if not any(table):
                empty_bits |= 1 << model_index
            if all(table):
                full_bits |= 1 << model_index
        rows.extend(
            (
                (
                    f"relation:{symbol_index}:empty",
                    "relation",
                    symbol_index,
                    "empty",
                    None,
                    empty_bits,
                ),
                (
                    f"relation:{symbol_index}:full",
                    "relation",
                    symbol_index,
                    "full",
                    None,
                    full_bits,
                ),
            )
        )
    return tuple(rows)


def finite_structure_templates(
    *,
    context_hash: str,
    signature: TheorySignature,
    models: Sequence[FiniteModelRecordLike],
    incidence: FiniteIncidenceContext,
) -> tuple[FiniteStructureTemplate, ...]:
    """Materialize nontrivial primitive templates for one exact context."""

    if not incidence.exact:
        return ()
    cache_key = (context_hash, incidence.context_hash)
    with _CACHE_LOCK:
        cached = _TEMPLATE_CACHE.get(cache_key)
        if cached is not None:
            return cached
    attribute_ids = incidence.attribute_ids
    templates: list[FiniteStructureTemplate] = []
    for template_id, kind, index, shape, argument_index, raw_support in _template_supports(
        signature, models
    ):
        support = raw_support & incidence.base_mask
        if not support or support == incidence.base_mask:
            continue
        closure_bits = incidence.closure_bits_for_extent(support)
        closure_ids = tuple(
            formula_id
            for formula_index, formula_id in enumerate(attribute_ids)
            if closure_bits & (1 << formula_index)
        )
        templates.append(
            FiniteStructureTemplate(
                template_id=template_id,
                symbol_kind=kind,
                symbol_index=index,
                shape=shape,
                argument_index=argument_index,
                support_bits=support,
                closure_ids=closure_ids,
            )
        )
    result = tuple(sorted(templates, key=lambda row: row.template_id))
    with _CACHE_LOCK:
        while len(_TEMPLATE_CACHE) >= _TEMPLATE_CACHE_MAX:
            _TEMPLATE_CACHE.pop(next(iter(_TEMPLATE_CACHE)))
        _TEMPLATE_CACHE[cache_key] = result
    return result


def finite_structural_baseline(
    *,
    context_hash: str,
    signature: TheorySignature,
    models: Sequence[FiniteModelRecordLike],
    incidence: FiniteIncidenceContext,
    presentation_ids: Sequence[str],
    candidate_formula_ids: Sequence[str],
) -> FiniteStructuralBaseline:
    """Find candidate consequences explained by forced primitive templates."""

    presentation = tuple(dict.fromkeys(str(row) for row in presentation_ids))
    candidates = tuple(dict.fromkeys(str(row) for row in candidate_formula_ids))
    extent = incidence.extent_bits(presentation)
    forced_rows = tuple(
        row
        for row in finite_structure_templates(
            context_hash=context_hash,
            signature=signature,
            models=models,
            incidence=incidence,
        )
        if extent and not (extent & ~row.support_bits)
    )
    specifically_collapsed_operations = {
        row.symbol_index
        for row in forced_rows
        if row.symbol_kind == "operation"
        and row.shape in {"constant", "projection"}
    }
    forced = tuple(
        row
        for row in forced_rows
        if not (
            row.shape == "inessential_argument"
            and row.symbol_index in specifically_collapsed_operations
        )
    )
    conditioning_bits = incidence.base_mask
    for template in forced:
        conditioning_bits &= template.support_bits
    joint_closure_ids: frozenset[str] = frozenset()
    if forced and conditioning_bits:
        closure_bits = incidence.closure_bits_for_extent(conditioning_bits)
        joint_closure_ids = frozenset(
            formula_id
            for formula_index, formula_id in enumerate(incidence.attribute_ids)
            if closure_bits & (1 << formula_index)
        )
    explanations: dict[str, tuple[str, ...]] = {}
    for formula_id in candidates:
        template_ids = tuple(
            row.template_id for row in forced if formula_id in row.closure_ids
        )
        if not template_ids and formula_id in joint_closure_ids:
            template_ids = tuple(row.template_id for row in forced)
        if template_ids:
            explanations[formula_id] = template_ids
    explained = tuple(row for row in candidates if row in explanations)
    return FiniteStructuralBaseline(
        context_hash=context_hash,
        presentation_ids=presentation,
        presentation_extent_size=extent.bit_count(),
        forced_templates=forced,
        conditioning_bits=conditioning_bits,
        explained_formula_ids=explained,
        explanation_map=explanations,
    )


__all__ = [
    "STRUCTURAL_BASELINE_REF",
    "STRUCTURAL_BASELINE_SCHEMA",
    "FiniteStructuralBaseline",
    "FiniteStructureTemplate",
    "finite_structural_baseline",
    "finite_structure_templates",
]
