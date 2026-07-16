"""Bounded typed stack codecs for model-authored frontier formulas.

The compact equation codec remains the cheapest representation for algebraic
campaigns.  ``decode_postfix_formula`` is the signature-generic surface: one
typed stack may contain terms and formulas, so relations, connectives, and
quantifiers do not require a recursive JSON AST from the model.
"""
from __future__ import annotations

from typing import Mapping, Sequence

from ztare.leanmill.conservative_definition import ConservativeOperationDefinition
from ztare.leanmill.theory_ir import (
    AxiomFormula,
    Binder,
    Formula,
    Term,
    TheorySignature,
    validate_axiom,
)


_FORMULA_CONNECTIVES = frozenset({"not", "and", "or", "implies", "iff"})


def _pop(
    stack: list[tuple[str, object, str | None]],
    *,
    kind: str,
    count: int,
    token: str,
) -> list[tuple[str, object, str | None]]:
    if count == 0:
        return []
    if len(stack) < count or any(row[0] != kind for row in stack[-count:]):
        raise ValueError(f"postfix stack expected {count} {kind} value(s) at {token!r}")
    rows = stack[-count:]
    del stack[-count:]
    return rows


def decode_postfix_term(
    signature: TheorySignature,
    *,
    variable_sorts: Mapping[str, str],
    tokens: Sequence[str],
    max_tokens: int = 128,
    derived_definitions: Mapping[str, ConservativeOperationDefinition] | None = None,
) -> tuple[Term, str]:
    if not tokens or len(tokens) > max_tokens:
        raise ValueError("postfix term token count is outside the codec bound")
    operations = {row.name: row for row in signature.operations}
    derived_definitions = dict(derived_definitions or {})
    known_sorts = {row.name for row in signature.sorts}
    if not variable_sorts or any(sort not in known_sorts for sort in variable_sorts.values()):
        raise ValueError("postfix variables require declared signature sorts")
    stack: list[tuple[Term, str]] = []
    for raw in tokens:
        token = str(raw)
        if token in variable_sorts:
            stack.append((Term.var(token), variable_sorts[token]))
            continue
        operation = operations.get(token)
        definition = derived_definitions.get(token)
        if operation is None and definition is None:
            raise ValueError(f"unknown postfix token: {token!r}")
        assert operation is not None or definition is not None
        arg_sorts = (
            operation.arg_sorts
            if operation is not None
            else tuple(row.sort for row in definition.parameters)
        )
        result_sort = (
            operation.result_sort if operation is not None else definition.result_sort
        )
        arity = len(arg_sorts)
        if len(stack) < arity:
            raise ValueError(f"postfix stack underflow at operation {token!r}")
        arguments = stack[-arity:] if arity else []
        if arity:
            del stack[-arity:]
        actual_sorts = tuple(sort for _term, sort in arguments)
        if actual_sorts != arg_sorts:
            raise ValueError(
                f"postfix operation {token!r} expected {arg_sorts}, got {actual_sorts}"
            )
        terms = tuple(term for term, _sort in arguments)
        term = (
            Term.app(token, *terms)
            if operation is not None
            else definition.expand(terms)
        )
        stack.append((term, result_sort))
    if len(stack) != 1:
        raise ValueError("postfix term must leave exactly one stack value")
    return stack[0]


def decode_postfix_equation(
    signature: TheorySignature,
    *,
    name: str,
    variable_sorts: Mapping[str, str],
    lhs_tokens: Sequence[str],
    rhs_tokens: Sequence[str],
    max_tokens_per_side: int = 128,
    derived_definitions: Mapping[str, ConservativeOperationDefinition] | None = None,
) -> AxiomFormula:
    left, left_sort = decode_postfix_term(
        signature,
        variable_sorts=variable_sorts,
        tokens=lhs_tokens,
        max_tokens=max_tokens_per_side,
        derived_definitions=derived_definitions,
    )
    right, right_sort = decode_postfix_term(
        signature,
        variable_sorts=variable_sorts,
        tokens=rhs_tokens,
        max_tokens=max_tokens_per_side,
        derived_definitions=derived_definitions,
    )
    if left_sort != right_sort:
        raise ValueError("postfix equation sides have different sorts")
    axiom = AxiomFormula(
        name,
        Formula.forall(
            tuple(Binder(variable, sort) for variable, sort in variable_sorts.items()),
            Formula.eq(left, right),
        ),
    )
    validate_axiom(signature, axiom)
    return axiom


def decode_postfix_formula(
    signature: TheorySignature,
    *,
    name: str,
    variable_sorts: Mapping[str, str],
    tokens: Sequence[str],
    max_tokens: int = 256,
    derived_definitions: Mapping[str, ConservativeOperationDefinition] | None = None,
) -> AxiomFormula:
    """Decode a flat typed first-order formula and close free variables.

    Tokens use signature symbol names (callers may translate anonymous aliases):

    - a variable or operation pushes a term;
    - a relation symbol or ``eq`` consumes terms and pushes a formula;
    - ``not``, ``and``, ``or``, ``implies``, and ``iff`` consume formulas;
    - ``forall:<variable>`` and ``exists:<variable>`` bind the top formula.

    Declared variables left free by explicit quantifier tokens are universally
    closed at the end.  This preserves the equation codec's convention while
    allowing local existential and alternating-quantifier hypotheses.
    """

    if not tokens or len(tokens) > max_tokens:
        raise ValueError("postfix formula token count is outside the codec bound")
    operations = {row.name: row for row in signature.operations}
    derived_definitions = dict(derived_definitions or {})
    relations = {row.name: row for row in signature.relations}
    known_sorts = {row.name for row in signature.sorts}
    if not variable_sorts or any(
        sort not in known_sorts for sort in variable_sorts.values()
    ):
        raise ValueError("postfix variables require declared signature sorts")

    stack: list[tuple[str, object, str | None]] = []
    explicitly_bound: set[str] = set()
    for raw in tokens:
        token = str(raw)
        if token in variable_sorts:
            stack.append(("term", Term.var(token), variable_sorts[token]))
            continue
        operation = operations.get(token)
        definition = derived_definitions.get(token)
        if operation is not None or definition is not None:
            assert operation is not None or definition is not None
            arg_sorts = (
                operation.arg_sorts
                if operation is not None
                else tuple(row.sort for row in definition.parameters)
            )
            result_sort = (
                operation.result_sort
                if operation is not None
                else definition.result_sort
            )
            arguments = _pop(
                stack,
                kind="term",
                count=len(arg_sorts),
                token=token,
            )
            actual_sorts = tuple(str(row[2]) for row in arguments)
            if actual_sorts != arg_sorts:
                raise ValueError(
                    f"postfix operation {token!r} expected {arg_sorts}, "
                    f"got {actual_sorts}"
                )
            terms = tuple(row[1] for row in arguments)
            stack.append(
                (
                    "term",
                    (
                        Term.app(token, *terms)
                        if operation is not None
                        else definition.expand(terms)
                    ),
                    result_sort,
                )
            )
            continue
        relation = relations.get(token)
        if relation is not None:
            arguments = _pop(
                stack,
                kind="term",
                count=len(relation.arg_sorts),
                token=token,
            )
            actual_sorts = tuple(str(row[2]) for row in arguments)
            if actual_sorts != relation.arg_sorts:
                raise ValueError(
                    f"postfix relation {token!r} expected {relation.arg_sorts}, "
                    f"got {actual_sorts}"
                )
            stack.append(
                (
                    "formula",
                    Formula.rel(token, *(row[1] for row in arguments)),
                    None,
                )
            )
            continue
        if token in {"eq", "="}:
            left, right = _pop(
                stack, kind="term", count=2, token=token
            )
            if left[2] != right[2]:
                raise ValueError("postfix equality terms have different sorts")
            stack.append(("formula", Formula.eq(left[1], right[1]), None))
            continue
        if token in _FORMULA_CONNECTIVES:
            count = 1 if token == "not" else 2
            operands = _pop(
                stack, kind="formula", count=count, token=token
            )
            formulas = [row[1] for row in operands]
            if token == "not":
                body = Formula.negate(formulas[0])
            elif token == "and":
                body = Formula.conjunction(*formulas)
            elif token == "or":
                body = Formula.disjunction(*formulas)
            elif token == "implies":
                body = Formula.implies(*formulas)
            else:
                body = Formula.iff(*formulas)
            stack.append(("formula", body, None))
            continue
        quantifier, separator, variable = token.partition(":")
        if separator and quantifier in {"forall", "exists"}:
            if variable not in variable_sorts:
                raise ValueError(f"postfix quantifier names unknown variable {variable!r}")
            if variable in explicitly_bound:
                raise ValueError(f"postfix variable {variable!r} is bound more than once")
            operand = _pop(
                stack, kind="formula", count=1, token=token
            )[0][1]
            binder = (Binder(variable, variable_sorts[variable]),)
            body = (
                Formula.forall(binder, operand)
                if quantifier == "forall"
                else Formula.exists(binder, operand)
            )
            explicitly_bound.add(variable)
            stack.append(("formula", body, None))
            continue
        raise ValueError(f"unknown postfix formula token: {token!r}")

    if len(stack) != 1 or stack[0][0] != "formula":
        raise ValueError("postfix formula must leave exactly one formula value")
    body = stack[0][1]
    remaining = tuple(
        Binder(variable, sort)
        for variable, sort in variable_sorts.items()
        if variable not in explicitly_bound
    )
    if remaining:
        body = Formula.forall(remaining, body)
    axiom = AxiomFormula(name, body)
    validate_axiom(signature, axiom)
    return axiom


__all__ = [
    "decode_postfix_equation",
    "decode_postfix_formula",
    "decode_postfix_term",
]
