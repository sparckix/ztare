"""Canonical anonymous magma equations for finite-theory campaigns.

The enumeration matches the Equational Theories Project convention: laws are
quotiented by variable renaming and exchange of the two equation sides, and
nontrivial tautologies w = w are removed while x = x is retained.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Iterator

from ztare.leanmill.theory_ir import (
    AxiomFormula,
    Binder,
    Formula,
    OperationSymbol,
    SortDecl,
    Term,
    TheorySignature,
)


MAGMA_GRAMMAR_SCHEMA = "leanmill.magma_law_universe.v1"


@dataclass(frozen=True)
class MagmaTerm:
    variable: int | None = None
    left: "MagmaTerm | None" = None
    right: "MagmaTerm | None" = None

    def __post_init__(self) -> None:
        is_variable = self.variable is not None
        has_children = self.left is not None or self.right is not None
        if is_variable == has_children:
            raise ValueError("magma term must be exactly a variable or a binary application")
        if is_variable:
            if type(self.variable) is not int or self.variable < 0:
                raise ValueError("magma variable indices must be nonnegative integers")
        elif self.left is None or self.right is None:
            raise ValueError("magma application requires left and right children")

    @classmethod
    def var(cls, index: int) -> "MagmaTerm":
        return cls(variable=index)

    @classmethod
    def app(cls, left: "MagmaTerm", right: "MagmaTerm") -> "MagmaTerm":
        return cls(left=left, right=right)

    @property
    def is_variable(self) -> bool:
        return self.variable is not None

    @property
    def operation_count(self) -> int:
        if self.is_variable:
            return 0
        assert self.left is not None and self.right is not None
        return 1 + self.left.operation_count + self.right.operation_count

    def variables(self) -> tuple[int, ...]:
        if self.is_variable:
            assert self.variable is not None
            return (self.variable,)
        assert self.left is not None and self.right is not None
        return self.left.variables() + self.right.variables()

    def postfix(self, *, operation_name: str = "op0") -> str:
        if self.is_variable:
            return f"x{self.variable}"
        assert self.left is not None and self.right is not None
        return f"{self.left.postfix(operation_name=operation_name)} {self.right.postfix(operation_name=operation_name)} {operation_name}"

    def to_ir(self, *, operation_name: str = "op0") -> Term:
        if self.is_variable:
            return Term.var(f"x{self.variable}")
        assert self.left is not None and self.right is not None
        return Term.app(
            operation_name,
            self.left.to_ir(operation_name=operation_name),
            self.right.to_ir(operation_name=operation_name),
        )

    def to_json(self) -> dict[str, Any]:
        if self.is_variable:
            return {"kind": "var", "index": self.variable}
        assert self.left is not None and self.right is not None
        return {
            "kind": "app",
            "left": self.left.to_json(),
            "right": self.right.to_json(),
        }


@dataclass(frozen=True)
class MagmaLaw:
    left: MagmaTerm
    right: MagmaTerm
    exact_order: int
    axiom: AxiomFormula
    schema: str = MAGMA_GRAMMAR_SCHEMA

    @property
    def formula_id(self) -> str:
        return "formula:" + self.axiom.semantic_hash

    @property
    def postfix(self) -> str:
        return f"{self.left.postfix()} = {self.right.postfix()}"

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "formula_id": self.formula_id,
            "exact_order": self.exact_order,
            "postfix": self.postfix,
            "left": self.left.to_json(),
            "right": self.right.to_json(),
            "axiom": self.axiom.to_json(),
        }


def anonymous_magma_signature(
    *,
    name: str = "AnonymousMagma",
    sort_name: str = "S0",
    operation_name: str = "op0",
) -> TheorySignature:
    return TheorySignature(
        name=name,
        sorts=(SortDecl(sort_name),),
        operations=(
            OperationSymbol(
                name=operation_name,
                arg_sorts=(sort_name, sort_name),
                result_sort=sort_name,
            ),
        ),
    )


@lru_cache(maxsize=None)
def _term_shapes(operation_count: int) -> tuple[object, ...]:
    if operation_count < 0:
        raise ValueError("operation_count must be nonnegative")
    if operation_count == 0:
        return ("var",)
    out: list[object] = []
    for left_count in range(operation_count):
        right_count = operation_count - 1 - left_count
        for left in _term_shapes(left_count):
            for right in _term_shapes(right_count):
                out.append(("app", left, right))
    return tuple(out)


def _restricted_growth_strings(length: int) -> Iterator[tuple[int, ...]]:
    """Canonical set partitions, hence variable assignments up to renaming."""

    if length < 1:
        return

    def generate(prefix: tuple[int, ...], maximum: int) -> Iterator[tuple[int, ...]]:
        if len(prefix) == length:
            yield prefix
            return
        for value in range(maximum + 2):
            yield from generate(prefix + (value,), max(maximum, value))

    yield from generate((0,), 0)


def _fill_shape(
    shape: object,
    labels: tuple[int, ...],
    position: list[int],
) -> MagmaTerm:
    if shape == "var":
        value = labels[position[0]]
        position[0] += 1
        return MagmaTerm.var(value)
    tag, left, right = shape  # type: ignore[misc]
    if tag != "app":
        raise ValueError(f"unknown magma shape: {tag!r}")
    return MagmaTerm.app(
        _fill_shape(left, labels, position),
        _fill_shape(right, labels, position),
    )


def _rename_term(term: MagmaTerm, mapping: dict[int, int], next_index: list[int]) -> MagmaTerm:
    if term.is_variable:
        assert term.variable is not None
        if term.variable not in mapping:
            mapping[term.variable] = next_index[0]
            next_index[0] += 1
        return MagmaTerm.var(mapping[term.variable])
    assert term.left is not None and term.right is not None
    return MagmaTerm.app(
        _rename_term(term.left, mapping, next_index),
        _rename_term(term.right, mapping, next_index),
    )


def _normalize_orientation(
    left: MagmaTerm,
    right: MagmaTerm,
) -> tuple[MagmaTerm, MagmaTerm]:
    mapping: dict[int, int] = {}
    next_index = [0]
    return (
        _rename_term(left, mapping, next_index),
        _rename_term(right, mapping, next_index),
    )


def _canonical_law_terms(
    left: MagmaTerm,
    right: MagmaTerm,
) -> tuple[MagmaTerm, MagmaTerm]:
    forward = _normalize_orientation(left, right)
    reverse = _normalize_orientation(right, left)

    def key(pair: tuple[MagmaTerm, MagmaTerm]) -> tuple[str, str]:
        return pair[0].postfix(), pair[1].postfix()

    return min((forward, reverse), key=key)


def _axiom_from_terms(
    left: MagmaTerm,
    right: MagmaTerm,
    *,
    sort_name: str,
    operation_name: str,
) -> AxiomFormula:
    variables = sorted(set(left.variables() + right.variables()))
    formula = Formula.forall(
        tuple(Binder(f"x{index}", sort_name) for index in variables),
        Formula.eq(
            left.to_ir(operation_name=operation_name),
            right.to_ir(operation_name=operation_name),
        ),
    )
    temporary = AxiomFormula("magma_law", formula)
    return AxiomFormula(f"magma_law_{temporary.semantic_hash[:16]}", formula)


@lru_cache(maxsize=None)
def _cached_laws(
    exact_order: int,
    sort_name: str,
    operation_name: str,
) -> tuple[MagmaLaw, ...]:
    if exact_order < 0:
        raise ValueError("exact_order must be nonnegative")
    canonical: dict[tuple[str, str], tuple[MagmaTerm, MagmaTerm]] = {}
    leaf_count = exact_order + 2
    for left_order in range(exact_order + 1):
        right_order = exact_order - left_order
        for left_shape in _term_shapes(left_order):
            for right_shape in _term_shapes(right_order):
                for labels in _restricted_growth_strings(leaf_count):
                    position = [0]
                    left = _fill_shape(left_shape, labels, position)
                    right = _fill_shape(right_shape, labels, position)
                    left, right = _canonical_law_terms(left, right)
                    if exact_order > 0 and left == right:
                        continue
                    key = (left.postfix(), right.postfix())
                    canonical[key] = (left, right)

    laws: list[MagmaLaw] = []
    seen_formula_ids: set[str] = set()
    for key in sorted(canonical):
        left, right = canonical[key]
        axiom = _axiom_from_terms(
            left,
            right,
            sort_name=sort_name,
            operation_name=operation_name,
        )
        formula_id = "formula:" + axiom.semantic_hash
        if formula_id in seen_formula_ids:
            continue
        seen_formula_ids.add(formula_id)
        laws.append(
            MagmaLaw(
                left=left,
                right=right,
                exact_order=exact_order,
                axiom=axiom,
            )
        )
    return tuple(laws)


def magma_laws_exact_order(
    exact_order: int,
    *,
    sort_name: str = "S0",
    operation_name: str = "op0",
) -> tuple[MagmaLaw, ...]:
    return _cached_laws(exact_order, sort_name, operation_name)


def magma_laws_through_order(
    max_order: int,
    *,
    sort_name: str = "S0",
    operation_name: str = "op0",
) -> tuple[MagmaLaw, ...]:
    if max_order < 0:
        raise ValueError("max_order must be nonnegative")
    return tuple(
        law
        for exact_order in range(max_order + 1)
        for law in magma_laws_exact_order(
            exact_order,
            sort_name=sort_name,
            operation_name=operation_name,
        )
    )


__all__ = [
    "MAGMA_GRAMMAR_SCHEMA",
    "MagmaLaw",
    "MagmaTerm",
    "anonymous_magma_signature",
    "magma_laws_exact_order",
    "magma_laws_through_order",
]
