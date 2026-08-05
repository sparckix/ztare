"""Typed intermediate representation for candidate mathematical theories.

The IR is deliberately small: many-sorted first-order formulas with equality,
total operations, and relations.  It is expressive enough for finite algebraic
laws while remaining exactly executable by :mod:`finite_model`.

Candidate laws lower to a conditional Lean typeclass.  They are never emitted
as global ``axiom`` declarations, so every downstream theorem must retain the
candidate pack as an explicit typeclass assumption.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations, product
from math import prod
import re
from typing import Any, Iterable, Mapping, Sequence

from ztare.common.content_identity import (
    canonical_json as _canonical_json,
    content_sha256 as content_hash,
)


SIGNATURE_SCHEMA = "leanmill.theory_signature.v1"
AXIOM_FORMULA_SCHEMA = "leanmill.axiom_formula.v1"
IR_VERSION = "leanmill.first_order_ir.v1"

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class IRValidationError(ValueError):
    """Raised when an IR object is malformed or ill-typed."""


def _require_identifier(value: str, *, context: str) -> None:
    if not isinstance(value, str) or not _IDENTIFIER_RE.fullmatch(value):
        raise IRValidationError(f"{context} must be an identifier, got {value!r}")


def _require_qualified_identifier(value: str, *, context: str) -> None:
    if not isinstance(value, str) or not value or any(
        not _IDENTIFIER_RE.fullmatch(part) for part in value.split(".")
    ):
        raise IRValidationError(
            f"{context} must be a namespace-qualified identifier, got {value!r}"
        )


def _require_exact_keys(
    obj: Mapping[str, Any],
    *,
    required: set[str],
    optional: set[str] = frozenset(),
    context: str,
) -> None:
    missing = required - set(obj)
    unknown = set(obj) - required - optional
    if missing:
        raise IRValidationError(f"{context} missing fields: {sorted(missing)}")
    if unknown:
        raise IRValidationError(f"{context} has unknown fields: {sorted(unknown)}")


def _string_field(obj: Mapping[str, Any], key: str, *, context: str) -> str:
    value = obj[key]
    if not isinstance(value, str):
        raise IRValidationError(f"{context} field {key!r} must be a string")
    return value


@dataclass(frozen=True, order=True)
class SortDecl:
    name: str

    def __post_init__(self) -> None:
        _require_identifier(self.name, context="sort name")

    def to_json(self) -> dict[str, str]:
        return {"name": self.name}

    @classmethod
    def from_json(cls, obj: Mapping[str, Any]) -> "SortDecl":
        _require_exact_keys(obj, required={"name"}, context="sort")
        return cls(name=_string_field(obj, "name", context="sort"))


@dataclass(frozen=True, order=True)
class OperationSymbol:
    name: str
    arg_sorts: tuple[str, ...]
    result_sort: str

    def __post_init__(self) -> None:
        _require_identifier(self.name, context="operation name")
        _require_identifier(self.result_sort, context=f"result sort of {self.name}")
        for sort in self.arg_sorts:
            _require_identifier(sort, context=f"argument sort of {self.name}")

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "arg_sorts": list(self.arg_sorts),
            "result_sort": self.result_sort,
        }

    @classmethod
    def from_json(cls, obj: Mapping[str, Any]) -> "OperationSymbol":
        _require_exact_keys(
            obj,
            required={"name", "arg_sorts", "result_sort"},
            context="operation",
        )
        args = obj["arg_sorts"]
        if not isinstance(args, list) or not all(isinstance(x, str) for x in args):
            raise IRValidationError("operation arg_sorts must be a list of strings")
        return cls(
            name=_string_field(obj, "name", context="operation"),
            arg_sorts=tuple(args),
            result_sort=_string_field(obj, "result_sort", context="operation"),
        )


@dataclass(frozen=True, order=True)
class RelationSymbol:
    name: str
    arg_sorts: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_identifier(self.name, context="relation name")
        for sort in self.arg_sorts:
            _require_identifier(sort, context=f"argument sort of {self.name}")

    def to_json(self) -> dict[str, Any]:
        return {"name": self.name, "arg_sorts": list(self.arg_sorts)}

    @classmethod
    def from_json(cls, obj: Mapping[str, Any]) -> "RelationSymbol":
        _require_exact_keys(obj, required={"name", "arg_sorts"}, context="relation")
        args = obj["arg_sorts"]
        if not isinstance(args, list) or not all(isinstance(x, str) for x in args):
            raise IRValidationError("relation arg_sorts must be a list of strings")
        return cls(
            name=_string_field(obj, "name", context="relation"),
            arg_sorts=tuple(args),
        )


@dataclass(frozen=True)
class TheorySignature:
    name: str
    sorts: tuple[SortDecl, ...]
    operations: tuple[OperationSymbol, ...] = ()
    relations: tuple[RelationSymbol, ...] = ()
    schema: str = SIGNATURE_SCHEMA

    def __post_init__(self) -> None:
        if not all(isinstance(item, SortDecl) for item in self.sorts):
            raise IRValidationError("signature sorts must contain SortDecl values")
        if not all(isinstance(item, OperationSymbol) for item in self.operations):
            raise IRValidationError(
                "signature operations must contain OperationSymbol values"
            )
        if not all(isinstance(item, RelationSymbol) for item in self.relations):
            raise IRValidationError(
                "signature relations must contain RelationSymbol values"
            )
        object.__setattr__(self, "sorts", tuple(sorted(self.sorts)))
        object.__setattr__(self, "operations", tuple(sorted(self.operations)))
        object.__setattr__(self, "relations", tuple(sorted(self.relations)))
        _require_identifier(self.name, context="signature name")
        if self.schema != SIGNATURE_SCHEMA:
            raise IRValidationError(f"unsupported signature schema: {self.schema!r}")
        if not self.sorts:
            raise IRValidationError("a signature needs at least one sort")
        sort_names = [item.name for item in self.sorts]
        if len(sort_names) != len(set(sort_names)):
            raise IRValidationError("sort names must be unique")
        symbol_names = [item.name for item in self.operations] + [
            item.name for item in self.relations
        ]
        if len(symbol_names) != len(set(symbol_names)):
            raise IRValidationError("operation and relation names must be globally unique")
        known_sorts = set(sort_names)
        for operation in self.operations:
            referenced = set(operation.arg_sorts) | {operation.result_sort}
            unknown = referenced - known_sorts
            if unknown:
                raise IRValidationError(
                    f"operation {operation.name!r} references unknown sorts: {sorted(unknown)}"
                )
        for relation in self.relations:
            unknown = set(relation.arg_sorts) - known_sorts
            if unknown:
                raise IRValidationError(
                    f"relation {relation.name!r} references unknown sorts: {sorted(unknown)}"
                )

    @property
    def sort_map(self) -> dict[str, SortDecl]:
        return {item.name: item for item in self.sorts}

    @property
    def operation_map(self) -> dict[str, OperationSymbol]:
        return {item.name: item for item in self.operations}

    @property
    def relation_map(self) -> dict[str, RelationSymbol]:
        return {item.name: item for item in self.relations}

    def canonical_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "name": self.name,
            "sorts": [item.to_json() for item in sorted(self.sorts)],
            "operations": [item.to_json() for item in sorted(self.operations)],
            "relations": [item.to_json() for item in sorted(self.relations)],
        }

    def to_json(self) -> dict[str, Any]:
        return self.canonical_dict()

    @property
    def content_hash(self) -> str:
        return content_hash(self.canonical_dict())

    @classmethod
    def from_json(cls, obj: Mapping[str, Any]) -> "TheorySignature":
        _require_exact_keys(
            obj,
            required={"name", "sorts"},
            optional={"schema", "operations", "relations"},
            context="theory signature",
        )
        raw_sorts = obj["sorts"]
        raw_operations = obj.get("operations", [])
        raw_relations = obj.get("relations", [])
        if not isinstance(raw_sorts, list) or not all(isinstance(x, Mapping) for x in raw_sorts):
            raise IRValidationError("signature sorts must be a list of objects")
        if not isinstance(raw_operations, list) or not all(
            isinstance(x, Mapping) for x in raw_operations
        ):
            raise IRValidationError("signature operations must be a list of objects")
        if not isinstance(raw_relations, list) or not all(
            isinstance(x, Mapping) for x in raw_relations
        ):
            raise IRValidationError("signature relations must be a list of objects")
        return cls(
            name=_string_field(obj, "name", context="theory signature"),
            sorts=tuple(SortDecl.from_json(x) for x in raw_sorts),
            operations=tuple(OperationSymbol.from_json(x) for x in raw_operations),
            relations=tuple(RelationSymbol.from_json(x) for x in raw_relations),
            schema=(
                _string_field(obj, "schema", context="theory signature")
                if "schema" in obj
                else SIGNATURE_SCHEMA
            ),
        )


@dataclass(frozen=True, order=True)
class Binder:
    name: str
    sort: str

    def __post_init__(self) -> None:
        _require_identifier(self.name, context="binder name")
        _require_identifier(self.sort, context=f"sort of binder {self.name}")

    def to_json(self) -> dict[str, str]:
        return {"name": self.name, "sort": self.sort}

    @classmethod
    def from_json(cls, obj: Mapping[str, Any]) -> "Binder":
        _require_exact_keys(obj, required={"name", "sort"}, context="binder")
        return cls(
            name=_string_field(obj, "name", context="binder"),
            sort=_string_field(obj, "sort", context="binder"),
        )


@dataclass(frozen=True)
class Term:
    kind: str
    name: str
    args: tuple["Term", ...] = ()

    def __post_init__(self) -> None:
        if self.kind not in {"var", "app"}:
            raise IRValidationError(f"unsupported term kind: {self.kind!r}")
        _require_identifier(self.name, context=f"{self.kind} term name")
        if not all(isinstance(arg, Term) for arg in self.args):
            raise IRValidationError("term arguments must contain Term values")
        if self.kind == "var" and self.args:
            raise IRValidationError("variable terms cannot have arguments")

    @classmethod
    def var(cls, name: str) -> "Term":
        return cls(kind="var", name=name)

    @classmethod
    def app(cls, symbol: str, *args: "Term") -> "Term":
        return cls(kind="app", name=symbol, args=tuple(args))

    def to_json(self) -> dict[str, Any]:
        if self.kind == "var":
            return {"kind": "var", "name": self.name}
        return {"kind": "app", "symbol": self.name, "args": [x.to_json() for x in self.args]}

    @classmethod
    def from_json(cls, obj: Mapping[str, Any]) -> "Term":
        kind = obj.get("kind")
        if kind == "var":
            _require_exact_keys(obj, required={"kind", "name"}, context="variable term")
            return cls.var(_string_field(obj, "name", context="variable term"))
        if kind == "app":
            _require_exact_keys(obj, required={"kind", "symbol", "args"}, context="application term")
            args = obj["args"]
            if not isinstance(args, list) or not all(isinstance(x, Mapping) for x in args):
                raise IRValidationError("application args must be a list of term objects")
            return cls.app(
                _string_field(obj, "symbol", context="application term"),
                *(cls.from_json(x) for x in args),
            )
        raise IRValidationError(f"unsupported or missing term kind: {kind!r}")


@dataclass(frozen=True)
class Formula:
    """A closed-formula building block.

    Fields are shared across formula variants to keep serialization explicit.
    Use the constructors below instead of instantiating the dataclass directly.
    """

    kind: str
    terms: tuple[Term, ...] = ()
    formulas: tuple["Formula", ...] = ()
    binders: tuple[Binder, ...] = ()
    relation: str | None = None

    def __post_init__(self) -> None:
        allowed = {
            "true",
            "false",
            "eq",
            "rel",
            "not",
            "and",
            "or",
            "implies",
            "iff",
            "forall",
            "exists",
        }
        if self.kind not in allowed:
            raise IRValidationError(f"unsupported formula kind: {self.kind!r}")
        if not all(isinstance(term, Term) for term in self.terms):
            raise IRValidationError("formula terms must contain Term values")
        if not all(isinstance(child, Formula) for child in self.formulas):
            raise IRValidationError("formula children must contain Formula values")
        if not all(isinstance(binder, Binder) for binder in self.binders):
            raise IRValidationError("formula binders must contain Binder values")
        expected_terms = {"eq": 2}
        expected_formulas = {"not": 1, "implies": 2, "iff": 2, "forall": 1, "exists": 1}
        if self.kind in expected_terms and len(self.terms) != expected_terms[self.kind]:
            raise IRValidationError(f"{self.kind} requires {expected_terms[self.kind]} terms")
        if self.kind in expected_formulas and len(self.formulas) != expected_formulas[self.kind]:
            raise IRValidationError(
                f"{self.kind} requires {expected_formulas[self.kind]} child formulas"
            )
        if self.kind in {"and", "or"} and len(self.formulas) < 2:
            raise IRValidationError(f"{self.kind} requires at least two child formulas")
        if self.kind == "rel":
            if self.relation is None:
                raise IRValidationError("relation formula requires a relation name")
            _require_identifier(self.relation, context="relation formula name")
        elif self.relation is not None:
            raise IRValidationError(f"{self.kind} formula cannot name a relation")
        if self.kind in {"forall", "exists"}:
            if not self.binders:
                raise IRValidationError(f"{self.kind} requires at least one binder")
            names = [binder.name for binder in self.binders]
            if len(names) != len(set(names)):
                raise IRValidationError(f"{self.kind} binder names must be unique")
        elif self.binders:
            raise IRValidationError(f"{self.kind} formula cannot contain binders")
        if self.kind not in {"eq", "rel"} and self.terms:
            raise IRValidationError(f"{self.kind} formula cannot contain terms")
        if self.kind not in {"not", "and", "or", "implies", "iff", "forall", "exists"} and self.formulas:
            raise IRValidationError(f"{self.kind} formula cannot contain child formulas")

    @classmethod
    def truth(cls) -> "Formula":
        return cls(kind="true")

    @classmethod
    def falsity(cls) -> "Formula":
        return cls(kind="false")

    @classmethod
    def eq(cls, left: Term, right: Term) -> "Formula":
        return cls(kind="eq", terms=(left, right))

    @classmethod
    def rel(cls, relation: str, *args: Term) -> "Formula":
        return cls(kind="rel", relation=relation, terms=tuple(args))

    @classmethod
    def negate(cls, body: "Formula") -> "Formula":
        return cls(kind="not", formulas=(body,))

    @classmethod
    def conjunction(cls, *items: "Formula") -> "Formula":
        return cls(kind="and", formulas=tuple(items))

    @classmethod
    def disjunction(cls, *items: "Formula") -> "Formula":
        return cls(kind="or", formulas=tuple(items))

    @classmethod
    def implies(cls, antecedent: "Formula", consequent: "Formula") -> "Formula":
        return cls(kind="implies", formulas=(antecedent, consequent))

    @classmethod
    def iff(cls, left: "Formula", right: "Formula") -> "Formula":
        return cls(kind="iff", formulas=(left, right))

    @classmethod
    def forall(cls, binders: Sequence[Binder], body: "Formula") -> "Formula":
        return cls(kind="forall", binders=tuple(binders), formulas=(body,))

    @classmethod
    def exists(cls, binders: Sequence[Binder], body: "Formula") -> "Formula":
        return cls(kind="exists", binders=tuple(binders), formulas=(body,))

    def to_json(self) -> dict[str, Any]:
        if self.kind in {"true", "false"}:
            return {"kind": self.kind}
        if self.kind == "eq":
            return {"kind": "eq", "left": self.terms[0].to_json(), "right": self.terms[1].to_json()}
        if self.kind == "rel":
            return {
                "kind": "rel",
                "name": self.relation,
                "args": [term.to_json() for term in self.terms],
            }
        if self.kind == "not":
            return {"kind": "not", "body": self.formulas[0].to_json()}
        if self.kind in {"and", "or"}:
            return {"kind": self.kind, "items": [item.to_json() for item in self.formulas]}
        if self.kind in {"implies", "iff"}:
            return {
                "kind": self.kind,
                "left": self.formulas[0].to_json(),
                "right": self.formulas[1].to_json(),
            }
        return {
            "kind": self.kind,
            "binders": [binder.to_json() for binder in self.binders],
            "body": self.formulas[0].to_json(),
        }

    @classmethod
    def from_json(cls, obj: Mapping[str, Any]) -> "Formula":
        kind = obj.get("kind")
        if kind in {"true", "false"}:
            _require_exact_keys(obj, required={"kind"}, context=f"{kind} formula")
            return cls.truth() if kind == "true" else cls.falsity()
        if kind == "eq":
            _require_exact_keys(obj, required={"kind", "left", "right"}, context="equality formula")
            if not isinstance(obj["left"], Mapping) or not isinstance(obj["right"], Mapping):
                raise IRValidationError("equality operands must be term objects")
            return cls.eq(Term.from_json(obj["left"]), Term.from_json(obj["right"]))
        if kind == "rel":
            _require_exact_keys(obj, required={"kind", "name", "args"}, context="relation formula")
            args = obj["args"]
            if not isinstance(args, list) or not all(isinstance(x, Mapping) for x in args):
                raise IRValidationError("relation args must be a list of term objects")
            return cls.rel(
                _string_field(obj, "name", context="relation formula"),
                *(Term.from_json(x) for x in args),
            )
        if kind == "not":
            _require_exact_keys(obj, required={"kind", "body"}, context="negation formula")
            if not isinstance(obj["body"], Mapping):
                raise IRValidationError("negation body must be a formula object")
            return cls.negate(cls.from_json(obj["body"]))
        if kind in {"and", "or"}:
            _require_exact_keys(obj, required={"kind", "items"}, context=f"{kind} formula")
            items = obj["items"]
            if not isinstance(items, list) or not all(isinstance(x, Mapping) for x in items):
                raise IRValidationError(f"{kind} items must be a list of formula objects")
            parsed = tuple(cls.from_json(x) for x in items)
            return cls.conjunction(*parsed) if kind == "and" else cls.disjunction(*parsed)
        if kind in {"implies", "iff"}:
            _require_exact_keys(obj, required={"kind", "left", "right"}, context=f"{kind} formula")
            if not isinstance(obj["left"], Mapping) or not isinstance(obj["right"], Mapping):
                raise IRValidationError(f"{kind} operands must be formula objects")
            left = cls.from_json(obj["left"])
            right = cls.from_json(obj["right"])
            return cls.implies(left, right) if kind == "implies" else cls.iff(left, right)
        if kind in {"forall", "exists"}:
            _require_exact_keys(obj, required={"kind", "binders", "body"}, context=f"{kind} formula")
            raw_binders = obj["binders"]
            if not isinstance(raw_binders, list) or not all(
                isinstance(x, Mapping) for x in raw_binders
            ):
                raise IRValidationError(f"{kind} binders must be a list of objects")
            if not isinstance(obj["body"], Mapping):
                raise IRValidationError(f"{kind} body must be a formula object")
            binders = tuple(Binder.from_json(x) for x in raw_binders)
            body = cls.from_json(obj["body"])
            return cls.forall(binders, body) if kind == "forall" else cls.exists(binders, body)
        raise IRValidationError(f"unsupported or missing formula kind: {kind!r}")


@dataclass(frozen=True)
class AxiomFormula:
    name: str
    formula: Formula
    schema: str = AXIOM_FORMULA_SCHEMA

    def __post_init__(self) -> None:
        _require_identifier(self.name, context="axiom name")
        if not isinstance(self.formula, Formula):
            raise IRValidationError("axiom formula must contain a Formula value")
        if self.schema != AXIOM_FORMULA_SCHEMA:
            raise IRValidationError(f"unsupported axiom schema: {self.schema!r}")

    def canonical_dict(self) -> dict[str, Any]:
        canonical_formula = _canonicalize_formula(self.formula, env={}, counter=[0])
        return {"schema": self.schema, "name": self.name, "formula": canonical_formula}

    def to_json(self) -> dict[str, Any]:
        return {"schema": self.schema, "name": self.name, "formula": self.formula.to_json()}

    @property
    def content_hash(self) -> str:
        return content_hash(self.canonical_dict())

    @property
    def semantic_hash(self) -> str:
        return content_hash(self.canonical_dict()["formula"])

    @classmethod
    def from_json(cls, obj: Mapping[str, Any]) -> "AxiomFormula":
        _require_exact_keys(
            obj,
            required={"name", "formula"},
            optional={"schema"},
            context="axiom formula",
        )
        if not isinstance(obj["formula"], Mapping):
            raise IRValidationError("axiom formula field must be an object")
        return cls(
            name=_string_field(obj, "name", context="axiom formula"),
            formula=Formula.from_json(obj["formula"]),
            schema=(
                _string_field(obj, "schema", context="axiom formula")
                if "schema" in obj
                else AXIOM_FORMULA_SCHEMA
            ),
        )


def _canonicalize_term(term: Term, env: Mapping[str, str]) -> dict[str, Any]:
    if term.kind == "var":
        return {"kind": "var", "name": env.get(term.name, term.name)}
    return {
        "kind": "app",
        "symbol": term.name,
        "args": [_canonicalize_term(arg, env) for arg in term.args],
    }


def _canonicalize_formula(
    formula: Formula,
    *,
    env: Mapping[str, str],
    counter: list[int],
) -> dict[str, Any]:
    kind = formula.kind
    if kind in {"true", "false"}:
        return {"kind": kind}
    if kind == "eq":
        sides = [_canonicalize_term(term, env) for term in formula.terms]
        sides.sort(key=_canonical_json)
        return {"kind": "eq", "left": sides[0], "right": sides[1]}
    if kind == "rel":
        return {
            "kind": "rel",
            "name": formula.relation,
            "args": [_canonicalize_term(term, env) for term in formula.terms],
        }
    if kind == "not":
        return {
            "kind": "not",
            "body": _canonicalize_formula(
                formula.formulas[0], env=env, counter=[counter[0]]
            ),
        }
    if kind in {"and", "or"}:
        items: list[dict[str, Any]] = []
        for child in formula.formulas:
            # Quantifiers in sibling branches have disjoint scopes.  Giving
            # each branch the same starting index makes conjunction and
            # disjunction hashes independent of presentation order.
            canonical = _canonicalize_formula(
                child, env=env, counter=[counter[0]]
            )
            if canonical.get("kind") == kind:
                items.extend(canonical["items"])
            else:
                items.append(canonical)
        items.sort(key=_canonical_json)
        return {"kind": kind, "items": items}
    if kind in {"implies", "iff"}:
        left = _canonicalize_formula(
            formula.formulas[0], env=env, counter=[counter[0]]
        )
        right = _canonicalize_formula(
            formula.formulas[1], env=env, counter=[counter[0]]
        )
        if kind == "iff" and _canonical_json(left) > _canonical_json(right):
            left, right = right, left
        return {"kind": kind, "left": left, "right": right}
    local_env = dict(env)
    binders: list[dict[str, str]] = []
    for binder in formula.binders:
        canonical_name = f"_v{counter[0]}"
        counter[0] += 1
        local_env[binder.name] = canonical_name
        binders.append({"name": canonical_name, "sort": binder.sort})
    return {
        "kind": kind,
        "binders": binders,
        "body": _canonicalize_formula(formula.formulas[0], env=local_env, counter=counter),
    }


def logical_coordinate_hash(formula: Formula) -> str:
    """Hash a formula modulo consecutive same-quantifier binder grouping.

    This is an additive frontier-coordinate quotient.  ``semantic_hash`` stays
    byte-compatible with banked theory artifacts.
    """

    def normalize(value: Formula) -> Formula:
        children = tuple(normalize(row) for row in value.formulas)
        if value.kind in {"forall", "exists"}:
            binders = list(value.binders)
            body = children[0]
            while body.kind == value.kind:
                binders.extend(body.binders)
                body = body.formulas[0]
            constructor = Formula.forall if value.kind == "forall" else Formula.exists
            return constructor(binders, body)
        return Formula(
            kind=value.kind,
            terms=value.terms,
            formulas=children,
            relation=value.relation,
        )

    normalized = normalize(formula)
    return content_hash(_canonicalize_formula(normalized, env={}, counter=[0]))


def permute_operation_arguments(
    formula: Formula,
    argument_permutations: Mapping[str, Sequence[int]],
) -> Formula:
    """Apply one declared input-coordinate permutation at every operation call.

    This is a syntactic coordinate change, not an equivalence judgment.  The
    caller must obtain type-correct maps from
    :func:`operation_argument_permutation_variants` (or otherwise validate the
    transformed formula against its signature).
    """

    normalized = {
        str(symbol): tuple(int(index) for index in permutation)
        for symbol, permutation in argument_permutations.items()
    }

    def transform_term(term: Term) -> Term:
        if term.kind == "var":
            return term
        args = tuple(transform_term(arg) for arg in term.args)
        permutation = normalized.get(term.name, tuple(range(len(args))))
        if len(permutation) != len(args) or set(permutation) != set(range(len(args))):
            raise IRValidationError(
                f"operation {term.name!r} requires a permutation of {len(args)} inputs"
            )
        return Term.app(term.name, *(args[index] for index in permutation))

    return Formula(
        kind=formula.kind,
        terms=tuple(transform_term(term) for term in formula.terms),
        formulas=tuple(
            permute_operation_arguments(child, normalized)
            for child in formula.formulas
        ),
        binders=formula.binders,
        relation=formula.relation,
    )


def operation_argument_permutation_variants(
    signature: TheorySignature,
    formula: Formula,
    *,
    include_identity: bool = False,
    max_variants: int = 256,
) -> tuple[tuple[tuple[tuple[str, tuple[int, ...]], ...], Formula], ...]:
    """Enumerate type-correct global input-coordinate variants of ``formula``.

    A permutation is admissible only when it preserves the declared argument
    sorts of its operation.  Results retain the operation symbols and change
    only their input coordinates.  They therefore provide deterministic search
    queries; they do not assert that a source uses an equivalent presentation.
    """

    if type(max_variants) is not int or max_variants < 1:
        raise ValueError("max_variants must be a positive integer")
    choices: list[tuple[tuple[int, ...], ...]] = []
    operations = tuple(signature.operations)
    for operation in operations:
        admissible = tuple(
            permutation
            for permutation in permutations(range(len(operation.arg_sorts)))
            if tuple(operation.arg_sorts[index] for index in permutation)
            == operation.arg_sorts
        )
        choices.append(admissible or ((),))
    variant_count = prod(len(rows) for rows in choices) if choices else 1
    emitted_count = variant_count if include_identity else max(0, variant_count - 1)
    if emitted_count > max_variants:
        raise ValueError(
            "operation-coordinate variant count exceeds the declared cap"
        )
    identity = tuple(
        (operation.name, tuple(range(len(operation.arg_sorts))))
        for operation in operations
    )
    variants = []
    for selected in product(*choices) if choices else ((),):
        mapping = tuple(
            (operation.name, tuple(permutation))
            for operation, permutation in zip(operations, selected, strict=True)
        )
        if not include_identity and mapping == identity:
            continue
        transformed = permute_operation_arguments(formula, dict(mapping))
        validate_axiom(
            signature,
            AxiomFormula(name="coordinate_variant", formula=transformed),
        )
        variants.append((mapping, transformed))
    return tuple(variants)


def validate_axiom(signature: TheorySignature, axiom: AxiomFormula) -> None:
    """Validate that ``axiom`` is closed and well typed for ``signature``."""

    _validate_formula(signature, axiom.formula, env={})


def validate_axioms(signature: TheorySignature, axioms: Iterable[AxiomFormula]) -> None:
    names: set[str] = set()
    for axiom in axioms:
        if axiom.name in names:
            raise IRValidationError(f"duplicate axiom name: {axiom.name!r}")
        names.add(axiom.name)
        validate_axiom(signature, axiom)


def theory_content_hash(
    signature: TheorySignature, axioms: Iterable[AxiomFormula]
) -> str:
    """Hash a theory independently of declaration order.

    Axiom names remain part of each axiom content hash.  This digest therefore
    identifies the exact named theory surface presented to downstream gates,
    while each axiom's ``semantic_hash`` remains available for deduplication.
    """

    axioms = tuple(axioms)
    validate_axioms(signature, axioms)
    return content_hash(
        {
            "schema": "leanmill.named_theory.v1",
            "signature_sha256": signature.content_hash,
            "axiom_sha256s": sorted(axiom.content_hash for axiom in axioms),
        }
    )


def relative_theory_content_hash(
    signature: TheorySignature,
    candidate_axioms: Iterable[AxiomFormula],
    *,
    base_axioms: Iterable[AxiomFormula] = (),
) -> str:
    """Hash a candidate extension while preserving the base/candidate cut."""

    candidates = tuple(candidate_axioms)
    base = tuple(base_axioms)
    validate_axioms(signature, base + candidates)
    if not base:
        return theory_content_hash(signature, candidates)
    return content_hash(
        {
            "schema": "leanmill.relative_named_theory.v1",
            "signature_sha256": signature.content_hash,
            "base_axiom_sha256s": sorted(axiom.content_hash for axiom in base),
            "candidate_axiom_sha256s": sorted(
                axiom.content_hash for axiom in candidates
            ),
        }
    )


def _infer_term_sort(signature: TheorySignature, term: Term, env: Mapping[str, str]) -> str:
    if term.kind == "var":
        if term.name not in env:
            raise IRValidationError(f"unbound variable: {term.name!r}")
        return env[term.name]
    operation = signature.operation_map.get(term.name)
    if operation is None:
        raise IRValidationError(f"unknown operation: {term.name!r}")
    if len(term.args) != len(operation.arg_sorts):
        raise IRValidationError(
            f"operation {term.name!r} expects {len(operation.arg_sorts)} args, got {len(term.args)}"
        )
    actual_sorts = tuple(_infer_term_sort(signature, arg, env) for arg in term.args)
    if actual_sorts != operation.arg_sorts:
        raise IRValidationError(
            f"operation {term.name!r} expects {operation.arg_sorts}, got {actual_sorts}"
        )
    return operation.result_sort


def _validate_formula(signature: TheorySignature, formula: Formula, env: Mapping[str, str]) -> None:
    if formula.kind in {"true", "false"}:
        return
    if formula.kind == "eq":
        left_sort = _infer_term_sort(signature, formula.terms[0], env)
        right_sort = _infer_term_sort(signature, formula.terms[1], env)
        if left_sort != right_sort:
            raise IRValidationError(
                f"equality operands have different sorts: {left_sort!r} and {right_sort!r}"
            )
        return
    if formula.kind == "rel":
        relation = signature.relation_map.get(formula.relation or "")
        if relation is None:
            raise IRValidationError(f"unknown relation: {formula.relation!r}")
        if len(formula.terms) != len(relation.arg_sorts):
            raise IRValidationError(
                f"relation {relation.name!r} expects {len(relation.arg_sorts)} args, "
                f"got {len(formula.terms)}"
            )
        actual_sorts = tuple(_infer_term_sort(signature, term, env) for term in formula.terms)
        if actual_sorts != relation.arg_sorts:
            raise IRValidationError(
                f"relation {relation.name!r} expects {relation.arg_sorts}, got {actual_sorts}"
            )
        return
    if formula.kind in {"forall", "exists"}:
        local_env = dict(env)
        known_sorts = signature.sort_map
        for binder in formula.binders:
            if binder.sort not in known_sorts:
                raise IRValidationError(
                    f"binder {binder.name!r} references unknown sort {binder.sort!r}"
                )
            if binder.name in local_env:
                raise IRValidationError(f"binder shadows existing variable: {binder.name!r}")
            local_env[binder.name] = binder.sort
        _validate_formula(signature, formula.formulas[0], local_env)
        return
    for child in formula.formulas:
        _validate_formula(signature, child, env)


@dataclass(frozen=True)
class LeanLoweringConfig:
    namespace: str = "LeanMillGenerated"
    signature_class: str | None = None
    base_class: str = "BaseTheory"
    pack_class: str = "CandidateAxiomPack"

    def __post_init__(self) -> None:
        _require_identifier(self.namespace, context="Lean namespace")
        _require_identifier(self.pack_class, context="Lean pack class")
        _require_identifier(self.base_class, context="Lean base class")
        if self.signature_class is not None:
            _require_identifier(self.signature_class, context="Lean signature class")


def lower_conditional_pack_to_lean(
    signature: TheorySignature,
    axioms: Sequence[AxiomFormula],
    *,
    base_axioms: Sequence[AxiomFormula] = (),
    config: LeanLoweringConfig | None = None,
) -> str:
    """Lower a signature and candidate laws to conditional Lean classes.

    The generated text contains no global assumptions.  Symbols live in a
    signature typeclass; laws live in a ``Prop``-valued pack typeclass that
    requires the signature instance.
    """

    config = config or LeanLoweringConfig()
    base_axioms = tuple(base_axioms)
    axioms = tuple(axioms)
    validate_axioms(signature, (*base_axioms, *axioms))
    signature_class = config.signature_class or f"{signature.name}Signature"
    _require_identifier(signature_class, context="Lean signature class")

    sort_params = " ".join(
        f"({sort.name} : Type u{index})" for index, sort in enumerate(signature.sorts)
    )
    sort_args = " ".join(sort.name for sort in signature.sorts)
    universes = " ".join(f"u{index}" for index in range(len(signature.sorts)))
    nonempty_instances = "".join(
        f" [Nonempty {sort.name}]" for sort in signature.sorts
    )

    lines = [f"namespace {config.namespace}", "", f"universe {universes}", ""]
    lines.append(f"class {signature_class} {sort_params} where")
    if not signature.operations and not signature.relations:
        lines.append("  marker : True")
    for operation in signature.operations:
        pieces = [*operation.arg_sorts, operation.result_sort]
        lines.append(f"  {operation.name} : {' -> '.join(pieces)}")
    for relation in signature.relations:
        pieces = [*relation.arg_sorts, "Prop"]
        lines.append(f"  {relation.name} : {' -> '.join(pieces)}")
    lines.append("")
    if base_axioms:
        lines.append(
            f"class {config.base_class} {sort_params} [{signature_class} {sort_args}]"
            f"{nonempty_instances} : Prop where"
        )
        for axiom in base_axioms:
            rendered = _render_formula_lean(axiom.formula, signature_class)
            lines.append(f"  {axiom.name} : {rendered}")
        lines.append("")
        base_instance = f" [{config.base_class} {sort_args}]"
    else:
        base_instance = ""
    lines.append(
        f"class {config.pack_class} {sort_params} [{signature_class} {sort_args}]"
        f"{nonempty_instances}{base_instance} : Prop where"
    )
    if not axioms:
        lines.append("  admitted_empty_pack : True")
    for axiom in axioms:
        rendered = _render_formula_lean(axiom.formula, signature_class)
        lines.append(f"  {axiom.name} : {rendered}")
    lines.extend(["", f"end {config.namespace}", ""])
    return "\n".join(lines)


def _render_term_lean(term: Term, signature_class: str) -> str:
    if term.kind == "var":
        return term.name
    head = f"{signature_class}.{term.name}"
    if not term.args:
        return head
    return f"({head} {' '.join(_render_term_lean(arg, signature_class) for arg in term.args)})"


def _render_formula_lean(formula: Formula, signature_class: str) -> str:
    kind = formula.kind
    if kind == "true":
        return "True"
    if kind == "false":
        return "False"
    if kind == "eq":
        return (
            f"({_render_term_lean(formula.terms[0], signature_class)} = "
            f"{_render_term_lean(formula.terms[1], signature_class)})"
        )
    if kind == "rel":
        head = f"{signature_class}.{formula.relation}"
        if not formula.terms:
            return head
        return f"({head} {' '.join(_render_term_lean(term, signature_class) for term in formula.terms)})"
    if kind == "not":
        return f"Not ({_render_formula_lean(formula.formulas[0], signature_class)})"
    if kind == "and":
        rendered = [_render_formula_lean(item, signature_class) for item in formula.formulas]
        result = rendered[0]
        for item in rendered[1:]:
            result = f"And ({result}) ({item})"
        return result
    if kind == "or":
        rendered = [_render_formula_lean(item, signature_class) for item in formula.formulas]
        result = rendered[0]
        for item in rendered[1:]:
            result = f"Or ({result}) ({item})"
        return result
    if kind == "implies":
        left = _render_formula_lean(formula.formulas[0], signature_class)
        right = _render_formula_lean(formula.formulas[1], signature_class)
        return f"(({left}) -> ({right}))"
    if kind == "iff":
        left = _render_formula_lean(formula.formulas[0], signature_class)
        right = _render_formula_lean(formula.formulas[1], signature_class)
        return f"Iff ({left}) ({right})"
    binder_text = " ".join(f"({binder.name} : {binder.sort})" for binder in formula.binders)
    body = _render_formula_lean(formula.formulas[0], signature_class)
    if kind == "forall":
        return f"(forall {binder_text}, {body})"
    rendered = body
    for binder in reversed(formula.binders):
        rendered = f"Exists (fun {binder.name} : {binder.sort} => {rendered})"
    return rendered


def render_formula_to_lean(
    signature: TheorySignature,
    formula: Formula,
    *,
    signature_class: str | None = None,
) -> str:
    """Public, validated rendering boundary for consequence-task builders."""
    _validate_formula(signature, formula, {})
    class_name = signature_class or f"{signature.name}Signature"
    _require_qualified_identifier(class_name, context="Lean signature class")
    return _render_formula_lean(formula, class_name)


def render_formula_plain(formula: Formula) -> str:
    """Render one IR formula without relying on substrate-specific notation."""

    def term(value: Term) -> str:
        if value.kind == "var":
            return value.name
        if not value.args:
            return value.name
        return f"{value.name}({', '.join(term(row) for row in value.args)})"

    kind = formula.kind
    if kind == "true":
        return "True"
    if kind == "false":
        return "False"
    if kind == "eq":
        return f"{term(formula.terms[0])} = {term(formula.terms[1])}"
    if kind == "rel":
        return f"{formula.relation}({', '.join(term(row) for row in formula.terms)})"
    if kind == "not":
        return f"not ({render_formula_plain(formula.formulas[0])})"
    if kind in {"and", "or"}:
        joiner = " and " if kind == "and" else " or "
        return joiner.join(
            f"({render_formula_plain(row)})" for row in formula.formulas
        )
    if kind in {"implies", "iff"}:
        joiner = " -> " if kind == "implies" else " <-> "
        return (
            f"({render_formula_plain(formula.formulas[0])}){joiner}"
            f"({render_formula_plain(formula.formulas[1])})"
        )
    binders = ", ".join(f"{row.name}:{row.sort}" for row in formula.binders)
    quantifier = "forall" if kind == "forall" else "exists"
    return f"{quantifier} {binders}, {render_formula_plain(formula.formulas[0])}"


def anonymous_formula_ir(
    signature: TheorySignature,
    formula: Formula,
) -> dict[str, Any]:
    """Render typed formula IR with only positional signature symbols visible."""

    _validate_formula(signature, formula, {})
    operation_map = {
        row.name: f"op_{index}" for index, row in enumerate(signature.operations)
    }
    relation_map = {
        row.name: f"rel_{index}" for index, row in enumerate(signature.relations)
    }
    sort_map = {
        row.name: f"sort_{index}" for index, row in enumerate(signature.sorts)
    }

    def scrub(value: Any, key: str = "") -> Any:
        if isinstance(value, Mapping):
            return {name: scrub(child, str(name)) for name, child in value.items()}
        if isinstance(value, (list, tuple)):
            return [scrub(child, key) for child in value]
        if isinstance(value, str):
            if key == "symbol" and value in operation_map:
                return operation_map[value]
            if key == "relation" and value in relation_map:
                return relation_map[value]
            if key == "sort" and value in sort_map:
                return sort_map[value]
        return value

    return scrub(formula.to_json())


__all__ = [
    "AXIOM_FORMULA_SCHEMA",
    "IRValidationError",
    "IR_VERSION",
    "SIGNATURE_SCHEMA",
    "AxiomFormula",
    "Binder",
    "Formula",
    "LeanLoweringConfig",
    "OperationSymbol",
    "RelationSymbol",
    "SortDecl",
    "Term",
    "TheorySignature",
    "anonymous_formula_ir",
    "content_hash",
    "lower_conditional_pack_to_lean",
    "logical_coordinate_hash",
    "operation_argument_permutation_variants",
    "permute_operation_arguments",
    "render_formula_plain",
    "render_formula_to_lean",
    "relative_theory_content_hash",
    "theory_content_hash",
    "validate_axiom",
    "validate_axioms",
]
