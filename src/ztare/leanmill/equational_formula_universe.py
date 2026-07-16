"""Canonical universal equations generated from a typed signature.

The grammar is deliberately structural: callers declare a signature and a
finite operation-order band, while the host enumerates every well-typed
equation in that band.  Variable renaming and exchange of equation sides are
quotiented before formulas enter a theory context.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
import json
from typing import Any, Iterator, Mapping, Sequence

from ztare.leanmill.theory_ir import (
    AxiomFormula,
    Binder,
    Formula,
    Term,
    TheorySignature,
    content_hash,
    validate_axioms,
)


EQUATIONAL_GRAMMAR_SCHEMA = "leanmill.universal_equation_grammar.v1"


def _term_key(term: Term) -> str:
    return json.dumps(term.to_json(), sort_keys=True, separators=(",", ":"))


def _compositions(total: int, parts: int) -> Iterator[tuple[int, ...]]:
    if parts == 0:
        if total == 0:
            yield ()
        return
    if parts == 1:
        yield (total,)
        return
    for first in range(total + 1):
        for rest in _compositions(total - first, parts - 1):
            yield (first, *rest)


def _default_variable_count(signature: TheorySignature, max_order: int) -> int:
    max_arity = max((len(row.arg_sorts) for row in signature.operations), default=1)
    return max(2, 2 + max_order * max(0, max_arity - 1))


def _variable_limits(
    signature: TheorySignature,
    grammar: Mapping[str, Any],
    *,
    max_order: int,
) -> dict[str, int]:
    raw = grammar.get("max_variables_per_sort")
    if raw is None:
        count = _default_variable_count(signature, max_order)
        return {row.name: count for row in signature.sorts}
    if type(raw) is int:
        if raw < 1:
            raise ValueError("max_variables_per_sort must be positive")
        return {row.name: raw for row in signature.sorts}
    if not isinstance(raw, Mapping) or set(raw) != set(signature.sort_map):
        raise ValueError("max_variables_per_sort must name every signature sort")
    limits = {str(key): int(value) for key, value in raw.items()}
    if any(type(value) is not int or value < 1 for value in raw.values()):
        raise ValueError("max_variables_per_sort values must be positive integers")
    return limits


def _variable_name(sort_index: int, variable_index: int, *, one_sort: bool) -> str:
    return f"x{variable_index}" if one_sort else f"x{sort_index}_{variable_index}"


def _term_universe(
    signature: TheorySignature,
    *,
    max_order: int,
    variable_limits: Mapping[str, int],
) -> tuple[dict[tuple[str, int], tuple[Term, ...]], dict[str, str]]:
    sorts = tuple(row.name for row in signature.sorts)
    one_sort = len(sorts) == 1
    variable_sorts: dict[str, str] = {}
    terms: dict[tuple[str, int], tuple[Term, ...]] = {}
    for sort_index, sort in enumerate(sorts):
        rows = []
        for variable_index in range(variable_limits[sort]):
            name = _variable_name(sort_index, variable_index, one_sort=one_sort)
            variable_sorts[name] = sort
            rows.append(Term.var(name))
        terms[(sort, 0)] = tuple(rows)

    for order in range(1, max_order + 1):
        by_sort: dict[str, dict[str, Term]] = {sort: {} for sort in sorts}
        for operation in signature.operations:
            for child_orders in _compositions(order - 1, len(operation.arg_sorts)):
                child_bands = [
                    terms.get((sort, child_order), ())
                    for sort, child_order in zip(
                        operation.arg_sorts, child_orders, strict=True
                    )
                ]
                if any(not band for band in child_bands):
                    continue
                for children in product(*child_bands):
                    term = Term.app(operation.name, *children)
                    by_sort[operation.result_sort][_term_key(term)] = term
        for sort in sorts:
            terms[(sort, order)] = tuple(
                by_sort[sort][key] for key in sorted(by_sort[sort])
            )
    return terms, variable_sorts


def _rename_term(
    term: Term,
    *,
    variable_sorts: Mapping[str, str],
    sort_indices: Mapping[str, int],
    mapping: dict[str, str],
    counters: dict[str, int],
    canonical_sorts: dict[str, str],
) -> Term:
    if term.kind == "var":
        if term.name not in mapping:
            sort = variable_sorts[term.name]
            index = counters[sort]
            counters[sort] += 1
            canonical = _variable_name(
                sort_indices[sort], index, one_sort=len(sort_indices) == 1
            )
            mapping[term.name] = canonical
            canonical_sorts[canonical] = sort
        return Term.var(mapping[term.name])
    return Term.app(
        term.name,
        *(
            _rename_term(
                child,
                variable_sorts=variable_sorts,
                sort_indices=sort_indices,
                mapping=mapping,
                counters=counters,
                canonical_sorts=canonical_sorts,
            )
            for child in term.args
        ),
    )


def _normalize_orientation(
    left: Term,
    right: Term,
    *,
    variable_sorts: Mapping[str, str],
    sort_indices: Mapping[str, int],
) -> tuple[Term, Term, dict[str, str]]:
    mapping: dict[str, str] = {}
    counters = {sort: 0 for sort in sort_indices}
    canonical_sorts: dict[str, str] = {}
    normalized_left = _rename_term(
        left,
        variable_sorts=variable_sorts,
        sort_indices=sort_indices,
        mapping=mapping,
        counters=counters,
        canonical_sorts=canonical_sorts,
    )
    normalized_right = _rename_term(
        right,
        variable_sorts=variable_sorts,
        sort_indices=sort_indices,
        mapping=mapping,
        counters=counters,
        canonical_sorts=canonical_sorts,
    )
    return normalized_left, normalized_right, canonical_sorts


def _canonical_equation(
    left: Term,
    right: Term,
    *,
    variable_sorts: Mapping[str, str],
    sort_indices: Mapping[str, int],
) -> tuple[Term, Term, dict[str, str]]:
    forward = _normalize_orientation(
        left,
        right,
        variable_sorts=variable_sorts,
        sort_indices=sort_indices,
    )
    reverse = _normalize_orientation(
        right,
        left,
        variable_sorts=variable_sorts,
        sort_indices=sort_indices,
    )
    return min(
        (forward, reverse),
        key=lambda row: (_term_key(row[0]), _term_key(row[1])),
    )


def render_term_plain(term: Term) -> str:
    if term.kind == "var":
        return term.name
    if not term.args:
        return term.name
    return f"{term.name}({', '.join(render_term_plain(row) for row in term.args)})"


@dataclass(frozen=True)
class EquationalFormula:
    left: Term
    right: Term
    result_sort: str
    exact_operation_order: int
    axiom: AxiomFormula
    schema: str = EQUATIONAL_GRAMMAR_SCHEMA

    @property
    def formula_id(self) -> str:
        return "formula:" + self.axiom.semantic_hash

    @property
    def rendered(self) -> str:
        return f"{render_term_plain(self.left)} = {render_term_plain(self.right)}"

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "formula_id": self.formula_id,
            "result_sort": self.result_sort,
            "exact_operation_order": self.exact_operation_order,
            "rendered": self.rendered,
            "left": self.left.to_json(),
            "right": self.right.to_json(),
            "axiom": self.axiom.to_json(),
        }


def enumerate_universal_equations(
    signature: TheorySignature,
    grammar: Mapping[str, Any],
) -> tuple[EquationalFormula, ...]:
    """Enumerate the complete declared universal-equation band."""

    if grammar.get("schema") != EQUATIONAL_GRAMMAR_SCHEMA:
        raise ValueError("unsupported generic equational formula grammar")
    allowed = {
        "schema",
        "max_total_operation_order",
        "max_variables_per_sort",
        "max_formulas",
        "variable_renaming_quotient",
        "equation_side_quotient",
        "exclude_nonvariable_reflexive",
    }
    if set(grammar) - allowed:
        raise ValueError("generic equational formula grammar has unknown fields")
    max_order = grammar.get("max_total_operation_order")
    max_formulas = grammar.get("max_formulas", 100_000)
    if type(max_order) is not int or max_order < 0:
        raise ValueError("max_total_operation_order must be a nonnegative integer")
    if type(max_formulas) is not int or max_formulas < 1:
        raise ValueError("max_formulas must be a positive integer")
    for flag in (
        "variable_renaming_quotient",
        "equation_side_quotient",
        "exclude_nonvariable_reflexive",
    ):
        if flag in grammar and grammar[flag] is not True:
            raise ValueError(f"generic equational grammar requires {flag}=true")
    variable_limits = _variable_limits(signature, grammar, max_order=max_order)
    terms, variable_sorts = _term_universe(
        signature,
        max_order=max_order,
        variable_limits=variable_limits,
    )
    sort_indices = {row.name: index for index, row in enumerate(signature.sorts)}
    canonical: dict[tuple[str, str, str], tuple[Term, Term, dict[str, str], int]] = {}
    for result_sort in sorted(signature.sort_map):
        for exact_order in range(max_order + 1):
            for left_order in range(exact_order + 1):
                right_order = exact_order - left_order
                for left in terms.get((result_sort, left_order), ()):
                    for right in terms.get((result_sort, right_order), ()):
                        normalized_left, normalized_right, binder_sorts = _canonical_equation(
                            left,
                            right,
                            variable_sorts=variable_sorts,
                            sort_indices=sort_indices,
                        )
                        if exact_order > 0 and normalized_left == normalized_right:
                            continue
                        key = (
                            result_sort,
                            _term_key(normalized_left),
                            _term_key(normalized_right),
                        )
                        canonical[key] = (
                            normalized_left,
                            normalized_right,
                            binder_sorts,
                            exact_order,
                        )
                        if len(canonical) > max_formulas:
                            raise ValueError(
                                "generic equational formula universe exceeds max_formulas="
                                f"{max_formulas} at max_total_operation_order={max_order}; "
                                "max_formulas is a fail-closed safety cap, not truncation: "
                                "raise it to contain the complete band or lower "
                                "max_total_operation_order"
                            )

    rows: list[EquationalFormula] = []
    seen: set[str] = set()
    for key in sorted(canonical):
        left, right, binder_sorts, exact_order = canonical[key]
        body = Formula.eq(left, right)
        binders = tuple(Binder(name, binder_sorts[name]) for name in binder_sorts)
        formula = Formula.forall(binders, body) if binders else body
        temporary = AxiomFormula("equational_formula", formula)
        axiom = AxiomFormula(
            f"equational_formula_{temporary.semantic_hash[:16]}", formula
        )
        if axiom.semantic_hash in seen:
            continue
        seen.add(axiom.semantic_hash)
        rows.append(
            EquationalFormula(
                left=left,
                right=right,
                result_sort=key[0],
                exact_operation_order=exact_order,
                axiom=axiom,
            )
        )
    validate_axioms(signature, tuple(row.axiom for row in rows))
    return tuple(rows)


def equational_formula_universe_receipt(
    signature: TheorySignature,
    grammar: Mapping[str, Any],
    *,
    formulas: Sequence[AxiomFormula] | None = None,
) -> dict[str, Any]:
    formula_ids = [
        "formula:" + row.semantic_hash
        for row in (
            formulas
            if formulas is not None
            else tuple(item.axiom for item in enumerate_universal_equations(signature, grammar))
        )
    ]
    core = {
        "schema": "leanmill.equational_formula_universe_receipt.v1",
        "signature_sha256": signature.content_hash,
        "grammar_sha256": content_hash(dict(grammar)),
        "formula_count": len(formula_ids),
        "formula_ids_sha256": content_hash(formula_ids),
        "complete": True,
    }
    return {**core, "receipt_sha256": content_hash(core)}


__all__ = [
    "EQUATIONAL_GRAMMAR_SCHEMA",
    "EquationalFormula",
    "enumerate_universal_equations",
    "equational_formula_universe_receipt",
    "render_term_plain",
]
