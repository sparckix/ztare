"""Bounded finite-model certificates for :mod:`ztare.leanmill.theory_ir`.

The checker exhaustively enumerates finite interpretations until it finds a
witness or exhausts a declared carrier bound.  A completed bounded search is
reported as ``*_WITHIN_BOUND``; it is never reported as an unqualified proof
of consistency, inconsistency, implication, or equivalence.  If the explicit
interpretation budget interrupts enumeration, the result is ``UNKNOWN``.

This module evaluates formulas exactly.  It does not schedule experiments or
assign information-yield scores; callers can pass candidate experiments to the
shared ``ztare.common.information_yield_pricing`` primitive when needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import permutations, product
import json
from math import factorial, prod
from typing import Any, Callable, Iterable, Iterator, Mapping, Sequence

from ztare.leanmill.theory_ir import (
    AxiomFormula,
    Formula,
    IRValidationError,
    Term,
    TheorySignature,
    content_hash,
    relative_theory_content_hash,
    validate_axioms,
)


CERTIFICATE_SCHEMA = "leanmill.finite_model_certificate.v1"
THEORY_SUITE_SCHEMA = "leanmill.theory_semantic_suite.v1"
EVALUATOR_VERSION = "leanmill.finite_model.enumerative.v1"

SAT = "SAT"
NO_MODEL_WITHIN_BOUND = "NO_MODEL_WITHIN_BOUND"
INDEPENDENCE_WITNESS = "INDEPENDENCE_WITNESS"
NO_INDEPENDENCE_WITNESS_WITHIN_BOUND = "NO_INDEPENDENCE_WITNESS_WITHIN_BOUND"
COUNTERMODEL = "COUNTERMODEL"
NO_COUNTERMODEL_WITHIN_BOUND = "NO_COUNTERMODEL_WITHIN_BOUND"
NOT_EQUIVALENT = "NOT_EQUIVALENT"
EQUIVALENT_WITHIN_BOUND = "EQUIVALENT_WITHIN_BOUND"
UNKNOWN = "UNKNOWN"

CERTIFIED_WITH_WITNESSES = "CERTIFIED_WITH_WITNESSES"
SAT_WITHOUT_COMPLETE_INDEPENDENCE_WITNESSES = (
    "SAT_WITHOUT_COMPLETE_INDEPENDENCE_WITNESSES"
)
NO_CANDIDATE_AXIOMS = "NO_CANDIDATE_AXIOMS"


@dataclass(frozen=True)
class FiniteSearchBounds:
    """Explicit finite search limits.

    Every carrier is non-empty.  ``sort_max_sizes`` can lower or raise the
    shared maximum for named sorts.  The interpretation budget is global over
    all carrier-size vectors.
    """

    max_carrier_size: int = 2
    max_interpretations: int = 100_000
    sort_max_sizes: tuple[tuple[str, int], ...] = ()
    min_carrier_size: int = 1

    def __post_init__(self) -> None:
        for name, value in (
            ("min_carrier_size", self.min_carrier_size),
            ("max_carrier_size", self.max_carrier_size),
            ("max_interpretations", self.max_interpretations),
        ):
            if type(value) is not int:
                raise ValueError(f"{name} must be an integer")
        if not all(
            isinstance(item, tuple)
            and len(item) == 2
            and isinstance(item[0], str)
            and type(item[1]) is int
            for item in self.sort_max_sizes
        ):
            raise ValueError("sort_max_sizes must contain (string, integer) pairs")
        object.__setattr__(
            self, "sort_max_sizes", tuple(sorted(self.sort_max_sizes))
        )
        if self.min_carrier_size < 1:
            raise ValueError("finite carriers must be non-empty")
        if self.max_carrier_size < self.min_carrier_size:
            raise ValueError("max_carrier_size must be at least min_carrier_size")
        if self.max_interpretations < 1:
            raise ValueError("max_interpretations must be positive")
        names = [name for name, _ in self.sort_max_sizes]
        if len(names) != len(set(names)):
            raise ValueError("sort_max_sizes cannot name a sort twice")
        for name, size in self.sort_max_sizes:
            if not name:
                raise ValueError("sort_max_sizes requires non-empty sort names")
            if size < self.min_carrier_size:
                raise ValueError(
                    f"maximum for sort {name!r} must be at least min_carrier_size"
                )

    def max_for_sort(self, name: str) -> int:
        return dict(self.sort_max_sizes).get(name, self.max_carrier_size)

    def to_json(self) -> dict[str, Any]:
        return {
            "min_carrier_size": self.min_carrier_size,
            "max_carrier_size": self.max_carrier_size,
            "max_interpretations": self.max_interpretations,
            "sort_max_sizes": {
                name: size for name, size in sorted(self.sort_max_sizes)
            },
        }

    @property
    def content_hash(self) -> str:
        return content_hash(self.to_json())


@dataclass(frozen=True)
class FiniteModel:
    """A finite interpretation over implicit carriers ``range(size)``."""

    sort_sizes: tuple[tuple[str, int], ...]
    operations: tuple[tuple[str, tuple[int, ...]], ...] = ()
    relations: tuple[tuple[str, tuple[bool, ...]], ...] = ()

    def __post_init__(self) -> None:
        try:
            sort_sizes = tuple(
                (name, size) for name, size in self.sort_sizes
            )
            operations = tuple(
                (name, tuple(table)) for name, table in self.operations
            )
            relations = tuple(
                (name, tuple(table)) for name, table in self.relations
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("finite model tables must contain name/value pairs") from exc
        if not all(
            isinstance(name, str) and type(size) is int
            for name, size in sort_sizes
        ):
            raise ValueError("finite model sort sizes require string names and integer sizes")
        if not all(
            isinstance(name, str)
            and all(type(value) is int for value in table)
            for name, table in operations
        ):
            raise ValueError("finite model operation tables require integer values")
        if not all(
            isinstance(name, str)
            and all(value is True or value is False for value in table)
            for name, table in relations
        ):
            raise ValueError("finite model relation tables require boolean values")
        object.__setattr__(self, "sort_sizes", tuple(sorted(sort_sizes)))
        object.__setattr__(self, "operations", tuple(sorted(operations)))
        object.__setattr__(self, "relations", tuple(sorted(relations)))
        sort_names = [name for name, _ in self.sort_sizes]
        operation_names = [name for name, _ in self.operations]
        relation_names = [name for name, _ in self.relations]
        if len(sort_names) != len(set(sort_names)):
            raise ValueError("finite model sort names must be unique")
        if len(operation_names) != len(set(operation_names)):
            raise ValueError("finite model operation names must be unique")
        if len(relation_names) != len(set(relation_names)):
            raise ValueError("finite model relation names must be unique")
        if any(size < 1 for _, size in self.sort_sizes):
            raise ValueError("finite model carriers must be non-empty")

    @property
    def sort_size_map(self) -> dict[str, int]:
        return dict(self.sort_sizes)

    @property
    def operation_map(self) -> dict[str, tuple[int, ...]]:
        return dict(self.operations)

    @property
    def relation_map(self) -> dict[str, tuple[bool, ...]]:
        return dict(self.relations)

    def to_json(self) -> dict[str, Any]:
        return {
            "carrier_encoding": "zero_based_indices",
            "table_order": "lexicographic_argument_indices_last_argument_fastest",
            "sort_sizes": {name: size for name, size in sorted(self.sort_sizes)},
            "operations": {
                name: list(table) for name, table in sorted(self.operations)
            },
            "relations": {
                name: list(table) for name, table in sorted(self.relations)
            },
        }

    @classmethod
    def from_json(cls, obj: Mapping[str, Any]) -> "FiniteModel":
        allowed = {
            "carrier_encoding",
            "table_order",
            "sort_sizes",
            "operations",
            "relations",
        }
        unknown = set(obj) - allowed
        if unknown:
            raise ValueError(f"finite model has unknown fields: {sorted(unknown)}")
        if obj.get("carrier_encoding", "zero_based_indices") != "zero_based_indices":
            raise ValueError("unsupported finite model carrier encoding")
        if obj.get(
            "table_order",
            "lexicographic_argument_indices_last_argument_fastest",
        ) != "lexicographic_argument_indices_last_argument_fastest":
            raise ValueError("unsupported finite model table order")
        sort_sizes = obj.get("sort_sizes")
        operations = obj.get("operations", {})
        relations = obj.get("relations", {})
        if not isinstance(sort_sizes, Mapping):
            raise ValueError("finite model sort_sizes must be an object")
        if not isinstance(operations, Mapping):
            raise ValueError("finite model operations must be an object")
        if not isinstance(relations, Mapping):
            raise ValueError("finite model relations must be an object")
        if not all(
            isinstance(name, str)
            and type(size) is int
            for name, size in sort_sizes.items()
        ):
            raise ValueError("finite model sort sizes require string names and integer sizes")
        for name, table in operations.items():
            if not isinstance(name, str) or not isinstance(table, list):
                raise ValueError("finite model operation tables must be named lists")
            if not all(type(value) is int for value in table):
                raise ValueError("finite model operation tables require integer values")
        for name, table in relations.items():
            if not isinstance(name, str) or not isinstance(table, list):
                raise ValueError("finite model relation tables must be named lists")
            if not all(value is True or value is False for value in table):
                raise ValueError("finite model relation tables require boolean values")
        return cls(
            sort_sizes=tuple(sorted((name, size) for name, size in sort_sizes.items())),
            operations=tuple(
                sorted(
                    (name, tuple(table))
                    for name, table in operations.items()
                )
            ),
            relations=tuple(
                sorted(
                    (name, tuple(_strict_bool(value) for value in table))
                    for name, table in relations.items()
                )
            ),
        )

    def content_hash(self, signature: TheorySignature) -> str:
        return content_hash(
            {"signature_sha256": signature.content_hash, "model": self.to_json()}
        )


def _strict_bool(value: Any) -> bool:
    if value is True:
        return True
    if value is False:
        return False
    raise ValueError(f"relation table values must be booleans, got {value!r}")


def validate_model(signature: TheorySignature, model: FiniteModel) -> None:
    sizes = model.sort_size_map
    expected_sorts = set(signature.sort_map)
    if set(sizes) != expected_sorts:
        raise IRValidationError(
            f"model sorts do not match signature: expected {sorted(expected_sorts)}, got {sorted(sizes)}"
        )
    operations = model.operation_map
    expected_operations = set(signature.operation_map)
    if set(operations) != expected_operations:
        raise IRValidationError(
            "model operations do not match signature: "
            f"expected {sorted(expected_operations)}, got {sorted(operations)}"
        )
    relations = model.relation_map
    expected_relations = set(signature.relation_map)
    if set(relations) != expected_relations:
        raise IRValidationError(
            "model relations do not match signature: "
            f"expected {sorted(expected_relations)}, got {sorted(relations)}"
        )
    for operation in signature.operations:
        rows = prod(sizes[sort] for sort in operation.arg_sorts)
        table = operations[operation.name]
        if len(table) != rows:
            raise IRValidationError(
                f"operation {operation.name!r} table needs {rows} rows, got {len(table)}"
            )
        result_size = sizes[operation.result_sort]
        if any(value < 0 or value >= result_size for value in table):
            raise IRValidationError(
                f"operation {operation.name!r} returns an out-of-carrier value"
            )
    for relation in signature.relations:
        rows = prod(sizes[sort] for sort in relation.arg_sorts)
        table = relations[relation.name]
        if len(table) != rows:
            raise IRValidationError(
                f"relation {relation.name!r} table needs {rows} rows, got {len(table)}"
            )
        if any(value is not True and value is not False for value in table):
            raise IRValidationError(
                f"relation {relation.name!r} table contains a non-boolean value"
            )


def finite_model_relabeling_count(model: FiniteModel) -> int:
    """Return the number of sort-preserving carrier relabelings."""

    return prod(factorial(size) for _sort, size in model.sort_sizes)


def relabel_finite_model(
    signature: TheorySignature,
    model: FiniteModel,
    relabelings: Mapping[str, Sequence[int]],
) -> FiniteModel:
    """Transport an interpretation through one permutation per carrier sort."""

    validate_model(signature, model)
    sizes = model.sort_size_map
    if set(relabelings) != set(sizes):
        raise ValueError("finite model relabeling must name every signature sort")
    old_to_new: dict[str, tuple[int, ...]] = {}
    new_to_old: dict[str, tuple[int, ...]] = {}
    for sort, size in sizes.items():
        permutation = tuple(relabelings[sort])
        if len(permutation) != size or set(permutation) != set(range(size)):
            raise ValueError("finite model relabeling must be a carrier permutation")
        inverse = [0] * size
        for old, new in enumerate(permutation):
            inverse[new] = old
        old_to_new[sort] = permutation
        new_to_old[sort] = tuple(inverse)

    operations = []
    for operation in signature.operations:
        old_table = model.operation_map[operation.name]
        domain_sizes = tuple(sizes[sort] for sort in operation.arg_sorts)
        table = []
        for new_args in product(*(range(size) for size in domain_sizes)):
            old_args = tuple(
                new_to_old[sort][value]
                for sort, value in zip(
                    operation.arg_sorts, new_args, strict=True
                )
            )
            old_result = old_table[_table_index(old_args, domain_sizes)]
            table.append(old_to_new[operation.result_sort][old_result])
        operations.append((operation.name, tuple(table)))

    relations = []
    for relation in signature.relations:
        old_table = model.relation_map[relation.name]
        domain_sizes = tuple(sizes[sort] for sort in relation.arg_sorts)
        table = []
        for new_args in product(*(range(size) for size in domain_sizes)):
            old_args = tuple(
                new_to_old[sort][value]
                for sort, value in zip(relation.arg_sorts, new_args, strict=True)
            )
            table.append(old_table[_table_index(old_args, domain_sizes)])
        relations.append((relation.name, tuple(table)))
    return FiniteModel(model.sort_sizes, tuple(operations), tuple(relations))


def canonicalize_finite_model(
    signature: TheorySignature,
    model: FiniteModel,
    *,
    max_relabelings: int | None = None,
) -> FiniteModel:
    """Choose a canonical representative under sort-preserving isomorphism."""

    validate_model(signature, model)
    relabeling_count = finite_model_relabeling_count(model)
    if max_relabelings is not None and relabeling_count > max_relabelings:
        raise ValueError("finite model isomorphism quotient exceeds relabeling cap")
    sorts = tuple(name for name, _size in model.sort_sizes)
    bands = tuple(
        tuple(permutations(range(model.sort_size_map[sort]))) for sort in sorts
    )
    best: FiniteModel | None = None
    best_key = ""
    for choices in product(*bands):
        candidate = relabel_finite_model(
            signature,
            model,
            dict(zip(sorts, choices, strict=True)),
        )
        key = json.dumps(candidate.to_json(), sort_keys=True, separators=(",", ":"))
        if best is None or key < best_key:
            best = candidate
            best_key = key
    if best is None:
        raise RuntimeError("finite model canonicalization produced no representative")
    return best


def evaluate_axiom(
    signature: TheorySignature,
    axiom: AxiomFormula,
    model: FiniteModel,
) -> bool:
    validate_axioms(signature, (axiom,))
    validate_model(signature, model)
    return evaluate_formula(signature, axiom.formula, model)


def evaluate_formula(
    signature: TheorySignature,
    formula: Formula,
    model: FiniteModel,
    *,
    environment: Mapping[str, int] | None = None,
) -> bool:
    """Evaluate a validated formula exactly in ``model``."""

    env = dict(environment or {})
    kind = formula.kind
    if kind == "true":
        return True
    if kind == "false":
        return False
    if kind == "eq":
        return _evaluate_term(signature, formula.terms[0], model, env) == _evaluate_term(
            signature, formula.terms[1], model, env
        )
    if kind == "rel":
        relation = signature.relation_map[formula.relation or ""]
        values = tuple(
            _evaluate_term(signature, term, model, env) for term in formula.terms
        )
        index = _table_index(
            values,
            tuple(model.sort_size_map[sort] for sort in relation.arg_sorts),
        )
        return model.relation_map[relation.name][index]
    if kind == "not":
        return not evaluate_formula(
            signature, formula.formulas[0], model, environment=env
        )
    if kind == "and":
        return all(
            evaluate_formula(signature, child, model, environment=env)
            for child in formula.formulas
        )
    if kind == "or":
        return any(
            evaluate_formula(signature, child, model, environment=env)
            for child in formula.formulas
        )
    if kind == "implies":
        return (
            not evaluate_formula(signature, formula.formulas[0], model, environment=env)
            or evaluate_formula(signature, formula.formulas[1], model, environment=env)
        )
    if kind == "iff":
        return evaluate_formula(
            signature, formula.formulas[0], model, environment=env
        ) == evaluate_formula(signature, formula.formulas[1], model, environment=env)
    domains = [
        range(model.sort_size_map[binder.sort]) for binder in formula.binders
    ]
    assignments = product(*domains)
    if kind == "forall":
        for values in assignments:
            local = dict(env)
            local.update(
                (binder.name, value)
                for binder, value in zip(formula.binders, values, strict=True)
            )
            if not evaluate_formula(
                signature, formula.formulas[0], model, environment=local
            ):
                return False
        return True
    for values in assignments:
        local = dict(env)
        local.update(
            (binder.name, value)
            for binder, value in zip(formula.binders, values, strict=True)
        )
        if evaluate_formula(
            signature, formula.formulas[0], model, environment=local
        ):
            return True
    return False


def _evaluate_term(
    signature: TheorySignature,
    term: Term,
    model: FiniteModel,
    env: Mapping[str, int],
) -> int:
    if term.kind == "var":
        return env[term.name]
    operation = signature.operation_map[term.name]
    values = tuple(
        _evaluate_term(signature, arg, model, env) for arg in term.args
    )
    index = _table_index(
        values,
        tuple(model.sort_size_map[sort] for sort in operation.arg_sorts),
    )
    return model.operation_map[operation.name][index]


def _table_index(values: tuple[int, ...], domain_sizes: tuple[int, ...]) -> int:
    index = 0
    for value, size in zip(values, domain_sizes, strict=True):
        index = index * size + value
    return index


@dataclass(frozen=True)
class SemanticCheckReceipt:
    check: str
    status: str
    signature_hash: str
    input_hashes: Mapping[str, Any]
    claim_bindings: tuple[str, ...]
    bounds: FiniteSearchBounds
    interpretations_tested: int
    search_space_size: int
    completed_size_vectors: tuple[tuple[tuple[str, int], ...], ...]
    witness: Mapping[str, Any] | None = None
    details: Mapping[str, Any] = field(default_factory=dict)
    schema: str = CERTIFICATE_SCHEMA
    evaluator_version: str = EVALUATOR_VERSION

    @property
    def bounded_absence(self) -> bool:
        return self.status in {
            NO_MODEL_WITHIN_BOUND,
            NO_INDEPENDENCE_WITNESS_WITHIN_BOUND,
            NO_COUNTERMODEL_WITHIN_BOUND,
            EQUIVALENT_WITHIN_BOUND,
        }

    def to_json(self) -> dict[str, Any]:
        check_subject_digest = content_hash(
            {
                "signature_sha256": self.signature_hash,
                "input_hashes": dict(self.input_hashes),
            }
        )
        payload: dict[str, Any] = {
            "schema": self.schema,
            "capability_id": "leanmill.finite_model_certificate",
            "evaluator_version": self.evaluator_version,
            "check": self.check,
            "status": self.status,
            "input_hashes": {
                **dict(self.input_hashes),
                "signature_sha256": self.signature_hash,
                "bounds_sha256": self.bounds.content_hash,
            },
            "claim_bindings": list(self.claim_bindings),
            "output_summary": _output_summary(self),
            "search": {
                "bounds": self.bounds.to_json(),
                "interpretations_tested": self.interpretations_tested,
                "search_space_size": self.search_space_size,
                "completed_size_vectors": [
                    {name: size for name, size in vector}
                    for vector in self.completed_size_vectors
                ],
                "bounded_absence": self.bounded_absence,
            },
            "details": dict(self.details),
            "check_subject_digest": check_subject_digest,
        }
        if self.check == "joint_satisfiability":
            candidate_hashes = sorted(self.input_hashes.get("axiom_sha256s", []))
            base_hashes = sorted(
                self.input_hashes.get("base_axiom_sha256s", [])
            )
            if base_hashes:
                theory_subject = {
                    "schema": "leanmill.relative_named_theory.v1",
                    "signature_sha256": self.signature_hash,
                    "base_axiom_sha256s": base_hashes,
                    "candidate_axiom_sha256s": candidate_hashes,
                }
            else:
                theory_subject = {
                    "schema": "leanmill.named_theory.v1",
                    "signature_sha256": self.signature_hash,
                    "axiom_sha256s": candidate_hashes,
                }
            payload["theory_digest"] = content_hash(theory_subject)
        if self.witness is not None:
            payload["witness"] = dict(self.witness)
        digest = content_hash(payload)
        payload["certificate_digest"] = digest
        payload["receipt_sha256"] = digest
        return payload

    @property
    def receipt_hash(self) -> str:
        return self.to_json()["receipt_sha256"]


@dataclass(frozen=True)
class TheorySemanticSuiteReceipt:
    """Aggregate semantic evidence for one exact named theory.

    Positive certification requires a joint model and a distinct finite
    independence witness for every candidate axiom.  Bounded non-discovery of
    a witness is retained as an unresolved result and cannot certify the pack.
    """

    status: str
    theory_digest: str
    signature_hash: str
    axiom_hashes: tuple[str, ...]
    base_axiom_hashes: tuple[str, ...]
    bounds: FiniteSearchBounds
    joint_satisfiability: SemanticCheckReceipt
    independence: tuple[SemanticCheckReceipt, ...]
    implications: tuple[SemanticCheckReceipt, ...] = ()
    schema: str = THEORY_SUITE_SCHEMA

    @property
    def certified(self) -> bool:
        return self.status == CERTIFIED_WITH_WITNESSES

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": self.schema,
            "status": self.status,
            "certified": self.certified,
            "theory_digest": self.theory_digest,
            "input_hashes": {
                "signature_sha256": self.signature_hash,
                "axiom_sha256s": list(self.axiom_hashes),
                "base_axiom_sha256s": list(self.base_axiom_hashes),
                "bounds_sha256": self.bounds.content_hash,
            },
            "joint_satisfiability": self.joint_satisfiability.to_json(),
            "independence": [receipt.to_json() for receipt in self.independence],
            "implications": [receipt.to_json() for receipt in self.implications],
        }
        digest = content_hash(payload)
        payload["certificate_digest"] = digest
        payload["receipt_sha256"] = digest
        return payload

    @property
    def certificate_digest(self) -> str:
        return self.to_json()["certificate_digest"]


def _output_summary(receipt: SemanticCheckReceipt) -> str:
    bounded = "; bounded finite conclusion only" if receipt.bounded_absence else ""
    return (
        f"{receipt.check}: status={receipt.status}; "
        f"tested={receipt.interpretations_tested}/{receipt.search_space_size}{bounded}"
    )


@dataclass(frozen=True)
class _SearchResult:
    witness: FiniteModel | None
    exhaustive: bool
    tested: int
    search_space_size: int
    completed_size_vectors: tuple[tuple[tuple[str, int], ...], ...]
    interrupted_size_vector: tuple[tuple[str, int], ...] | None = None


def certify_joint_satisfiability(
    signature: TheorySignature,
    axioms: Sequence[AxiomFormula],
    bounds: FiniteSearchBounds | None = None,
    *,
    base_axioms: Sequence[AxiomFormula] = (),
) -> SemanticCheckReceipt:
    bounds = bounds or FiniteSearchBounds()
    axioms = _ordered_axioms(axioms)
    base_axioms = _ordered_axioms(base_axioms)
    _validate_search_inputs(signature, base_axioms + axioms, bounds)
    result = _search_models(
        signature,
        bounds,
        lambda model: _all_hold(signature, base_axioms + axioms, model),
    )
    if result.witness is not None:
        status = SAT
    elif result.exhaustive:
        status = NO_MODEL_WITHIN_BOUND
    else:
        status = UNKNOWN
    return _receipt(
        check="joint_satisfiability",
        status=status,
        signature=signature,
        input_hashes={
            "axiom_sha256s": [axiom.content_hash for axiom in axioms],
            "base_axiom_sha256s": [
                axiom.content_hash for axiom in base_axioms
            ],
        },
        claim_bindings=tuple(
            [f"base:{axiom.name}" for axiom in base_axioms]
            + [f"candidate:{axiom.name}" for axiom in axioms]
        ),
        bounds=bounds,
        result=result,
        details={
            "base_axiom_names": [axiom.name for axiom in base_axioms],
            "candidate_axiom_names": [axiom.name for axiom in axioms],
        },
    )


def certify_theory(
    signature: TheorySignature,
    axioms: Sequence[AxiomFormula],
    bounds: FiniteSearchBounds | None = None,
    *,
    base_axioms: Sequence[AxiomFormula] = (),
    implication_receipts: Sequence[SemanticCheckReceipt] = (),
) -> TheorySemanticSuiteReceipt:
    """Run and bind the minimum semantic suite for a candidate axiom pack."""

    bounds = bounds or FiniteSearchBounds()
    axioms = _ordered_axioms(axioms)
    base_axioms = _ordered_axioms(base_axioms)
    _validate_search_inputs(signature, base_axioms + axioms, bounds)
    implications = tuple(implication_receipts)
    for receipt in implications:
        if receipt.check != "implication":
            raise ValueError("implication_receipts must contain implication checks")
        if receipt.signature_hash != signature.content_hash:
            raise ValueError("implication receipt signature does not match theory")
        if receipt.bounds.content_hash != bounds.content_hash:
            raise ValueError("implication receipt bounds do not match theory suite")

    joint = certify_joint_satisfiability(
        signature, axioms, bounds, base_axioms=base_axioms
    )
    independence = certify_axiom_independence(
        signature, axioms, bounds, base_axioms=base_axioms
    )
    if not axioms:
        status = NO_CANDIDATE_AXIOMS
    elif joint.status == SAT and all(
        receipt.status == INDEPENDENCE_WITNESS for receipt in independence
    ):
        status = CERTIFIED_WITH_WITNESSES
    elif joint.status == SAT:
        status = SAT_WITHOUT_COMPLETE_INDEPENDENCE_WITNESSES
    elif joint.status == NO_MODEL_WITHIN_BOUND:
        status = NO_MODEL_WITHIN_BOUND
    else:
        status = UNKNOWN
    return TheorySemanticSuiteReceipt(
        status=status,
        theory_digest=relative_theory_content_hash(
            signature, axioms, base_axioms=base_axioms
        ),
        signature_hash=signature.content_hash,
        axiom_hashes=tuple(sorted(axiom.content_hash for axiom in axioms)),
        base_axiom_hashes=tuple(
            sorted(axiom.content_hash for axiom in base_axioms)
        ),
        bounds=bounds,
        joint_satisfiability=joint,
        independence=independence,
        implications=implications,
    )


def certify_axiom_independence(
    signature: TheorySignature,
    axioms: Sequence[AxiomFormula],
    bounds: FiniteSearchBounds | None = None,
    *,
    base_axioms: Sequence[AxiomFormula] = (),
) -> tuple[SemanticCheckReceipt, ...]:
    """Search for a model of every other axiom that refutes each target."""

    bounds = bounds or FiniteSearchBounds()
    axioms = _ordered_axioms(axioms)
    base_axioms = _ordered_axioms(base_axioms)
    _validate_search_inputs(signature, base_axioms + axioms, bounds)
    receipts: list[SemanticCheckReceipt] = []
    for index, target in enumerate(axioms):
        other_candidates = axioms[:index] + axioms[index + 1 :]
        background = base_axioms + other_candidates
        result = _search_models(
            signature,
            bounds,
            lambda model, background=background, target=target: (
                _all_hold(signature, background, model)
                and not evaluate_formula(signature, target.formula, model)
            ),
        )
        if result.witness is not None:
            status = INDEPENDENCE_WITNESS
        elif result.exhaustive:
            status = NO_INDEPENDENCE_WITNESS_WITHIN_BOUND
        else:
            status = UNKNOWN
        receipts.append(
            _receipt(
                check="axiom_independence",
                status=status,
                signature=signature,
                input_hashes={
                    "target_axiom_sha256": target.content_hash,
                    "background_axiom_sha256s": [
                        axiom.content_hash for axiom in other_candidates
                    ],
                    "base_axiom_sha256s": [
                        axiom.content_hash for axiom in base_axioms
                    ],
                },
                claim_bindings=(target.name,),
                bounds=bounds,
                result=result,
                details={
                    "target_axiom": target.name,
                    "base_axioms": [axiom.name for axiom in base_axioms],
                    "background_candidate_axioms": [
                        axiom.name for axiom in other_candidates
                    ],
                },
            )
        )
    return tuple(receipts)


def certify_implication(
    signature: TheorySignature,
    premises: Sequence[AxiomFormula],
    conclusions: Sequence[AxiomFormula],
    bounds: FiniteSearchBounds | None = None,
) -> SemanticCheckReceipt:
    """Search for a finite countermodel to ``premises => conclusions``."""

    bounds = bounds or FiniteSearchBounds()
    premises = _ordered_axioms(premises)
    conclusions = _ordered_axioms(conclusions)
    _validate_search_inputs(signature, premises + conclusions, bounds)
    result = _search_models(
        signature,
        bounds,
        lambda model: (
            _all_hold(signature, premises, model)
            and not _all_hold(signature, conclusions, model)
        ),
    )
    if result.witness is not None:
        status = COUNTERMODEL
    elif result.exhaustive:
        status = NO_COUNTERMODEL_WITHIN_BOUND
    else:
        status = UNKNOWN
    return _receipt(
        check="implication",
        status=status,
        signature=signature,
        input_hashes={
            "premise_sha256s": [axiom.content_hash for axiom in premises],
            "conclusion_sha256s": [axiom.content_hash for axiom in conclusions],
        },
        claim_bindings=tuple(
            [f"premise:{axiom.name}" for axiom in premises]
            + [f"conclusion:{axiom.name}" for axiom in conclusions]
        ),
        bounds=bounds,
        result=result,
        details={
            "premises": [axiom.name for axiom in premises],
            "conclusions": [axiom.name for axiom in conclusions],
        },
    )


def certify_equivalence(
    signature: TheorySignature,
    left_axioms: Sequence[AxiomFormula],
    right_axioms: Sequence[AxiomFormula],
    bounds: FiniteSearchBounds | None = None,
) -> SemanticCheckReceipt:
    """Check both finite implication directions under the same bounds."""

    bounds = bounds or FiniteSearchBounds()
    left_axioms = _ordered_axioms(left_axioms)
    right_axioms = _ordered_axioms(right_axioms)
    left_to_right = certify_implication(
        signature, left_axioms, right_axioms, bounds
    )
    right_to_left = certify_implication(
        signature, right_axioms, left_axioms, bounds
    )
    directions = (left_to_right, right_to_left)
    if any(receipt.status == COUNTERMODEL for receipt in directions):
        status = NOT_EQUIVALENT
        witness_receipt = next(
            receipt for receipt in directions if receipt.status == COUNTERMODEL
        )
        witness = witness_receipt.witness
    elif all(
        receipt.status == NO_COUNTERMODEL_WITHIN_BOUND for receipt in directions
    ):
        status = EQUIVALENT_WITHIN_BOUND
        witness = None
    else:
        status = UNKNOWN
        witness = None
    combined_space = left_to_right.search_space_size + right_to_left.search_space_size
    result = _SearchResult(
        witness=None,
        exhaustive=status == EQUIVALENT_WITHIN_BOUND,
        tested=(
            left_to_right.interpretations_tested
            + right_to_left.interpretations_tested
        ),
        search_space_size=combined_space,
        completed_size_vectors=(
            left_to_right.completed_size_vectors
            + right_to_left.completed_size_vectors
        ),
    )
    direction_json = [receipt.to_json() for receipt in directions]
    return SemanticCheckReceipt(
        check="equivalence",
        status=status,
        signature_hash=signature.content_hash,
        input_hashes={
            "left_axiom_sha256s": [axiom.content_hash for axiom in left_axioms],
            "right_axiom_sha256s": [axiom.content_hash for axiom in right_axioms],
            "direction_receipt_sha256s": [
                receipt.receipt_hash for receipt in directions
            ],
        },
        claim_bindings=tuple(
            [f"left:{axiom.name}" for axiom in left_axioms]
            + [f"right:{axiom.name}" for axiom in right_axioms]
        ),
        bounds=bounds,
        interpretations_tested=result.tested,
        search_space_size=result.search_space_size,
        completed_size_vectors=result.completed_size_vectors,
        witness=witness,
        details={"direction_receipts": direction_json},
    )


def _validate_search_inputs(
    signature: TheorySignature,
    axioms: Sequence[AxiomFormula],
    bounds: FiniteSearchBounds,
) -> None:
    validate_axioms(signature, axioms)
    unknown_sorts = set(dict(bounds.sort_max_sizes)) - set(signature.sort_map)
    if unknown_sorts:
        raise IRValidationError(
            f"search bounds reference unknown sorts: {sorted(unknown_sorts)}"
        )


def _ordered_axioms(
    axioms: Iterable[AxiomFormula],
) -> tuple[AxiomFormula, ...]:
    """Canonical declaration order for deterministic search and receipts."""

    return tuple(sorted(tuple(axioms), key=lambda axiom: axiom.name))


def _all_hold(
    signature: TheorySignature,
    axioms: Iterable[AxiomFormula],
    model: FiniteModel,
) -> bool:
    return all(
        evaluate_formula(signature, axiom.formula, model) for axiom in axioms
    )


def _receipt(
    *,
    check: str,
    status: str,
    signature: TheorySignature,
    input_hashes: Mapping[str, Any],
    claim_bindings: tuple[str, ...],
    bounds: FiniteSearchBounds,
    result: _SearchResult,
    details: Mapping[str, Any],
) -> SemanticCheckReceipt:
    witness: dict[str, Any] | None = None
    if result.witness is not None:
        witness = {
            "model": result.witness.to_json(),
            "model_sha256": result.witness.content_hash(signature),
        }
    full_details = dict(details)
    if result.interrupted_size_vector is not None:
        full_details["unknown_reason"] = "max_interpretations_exhausted"
        full_details["interrupted_size_vector"] = dict(
            result.interrupted_size_vector
        )
    return SemanticCheckReceipt(
        check=check,
        status=status,
        signature_hash=signature.content_hash,
        input_hashes=input_hashes,
        claim_bindings=claim_bindings,
        bounds=bounds,
        interpretations_tested=result.tested,
        search_space_size=result.search_space_size,
        completed_size_vectors=result.completed_size_vectors,
        witness=witness,
        details=full_details,
    )


def _search_models(
    signature: TheorySignature,
    bounds: FiniteSearchBounds,
    predicate: Callable[[FiniteModel], bool],
) -> _SearchResult:
    vectors = tuple(_size_vectors(signature, bounds))
    search_space_size = sum(
        _interpretation_count(signature, dict(vector)) for vector in vectors
    )
    tested = 0
    completed: list[tuple[tuple[str, int], ...]] = []
    for vector in vectors:
        for model in _interpretations(signature, dict(vector)):
            if tested >= bounds.max_interpretations:
                return _SearchResult(
                    witness=None,
                    exhaustive=False,
                    tested=tested,
                    search_space_size=search_space_size,
                    completed_size_vectors=tuple(completed),
                    interrupted_size_vector=vector,
                )
            tested += 1
            if predicate(model):
                return _SearchResult(
                    witness=model,
                    exhaustive=False,
                    tested=tested,
                    search_space_size=search_space_size,
                    completed_size_vectors=tuple(completed),
                )
        completed.append(vector)
    return _SearchResult(
        witness=None,
        exhaustive=True,
        tested=tested,
        search_space_size=search_space_size,
        completed_size_vectors=tuple(completed),
    )


def _size_vectors(
    signature: TheorySignature,
    bounds: FiniteSearchBounds,
) -> Iterator[tuple[tuple[str, int], ...]]:
    names = tuple(sorted(signature.sort_map))
    domains = [
        range(bounds.min_carrier_size, bounds.max_for_sort(name) + 1)
        for name in names
    ]
    for values in product(*domains):
        yield tuple(zip(names, values, strict=True))


def _interpretation_count(
    signature: TheorySignature,
    sizes: Mapping[str, int],
) -> int:
    count = 1
    for operation in signature.operations:
        rows = prod(sizes[sort] for sort in operation.arg_sorts)
        count *= sizes[operation.result_sort] ** rows
    for relation in signature.relations:
        rows = prod(sizes[sort] for sort in relation.arg_sorts)
        count *= 2**rows
    return count


def _interpretations(
    signature: TheorySignature,
    sizes: Mapping[str, int],
) -> Iterator[FiniteModel]:
    components: list[tuple[str, str, tuple[Any, ...], int]] = []
    for operation in sorted(signature.operations):
        rows = prod(sizes[sort] for sort in operation.arg_sorts)
        components.append(
            (
                "operation",
                operation.name,
                tuple(range(sizes[operation.result_sort])),
                rows,
            )
        )
    for relation in sorted(signature.relations):
        rows = prod(sizes[sort] for sort in relation.arg_sorts)
        components.append(("relation", relation.name, (False, True), rows))

    def build(
        index: int,
        operations: list[tuple[str, tuple[int, ...]]],
        relations: list[tuple[str, tuple[bool, ...]]],
    ) -> Iterator[FiniteModel]:
        if index == len(components):
            yield FiniteModel(
                sort_sizes=tuple(sorted(sizes.items())),
                operations=tuple(operations),
                relations=tuple(relations),
            )
            return
        kind, name, outcomes, rows = components[index]
        for table in product(outcomes, repeat=rows):
            if kind == "operation":
                yield from build(
                    index + 1,
                    operations + [(name, tuple(int(value) for value in table))],
                    relations,
                )
            else:
                yield from build(
                    index + 1,
                    operations,
                    relations + [(name, tuple(bool(value) for value in table))],
                )

    yield from build(0, [], [])


def finite_interpretation_count(
    signature: TheorySignature,
    sort_sizes: Mapping[str, int],
) -> int:
    """Return the complete table-interpretation count for one size vector."""

    sizes = _validated_size_vector(signature, sort_sizes)
    return _interpretation_count(signature, sizes)


def iter_finite_models(
    signature: TheorySignature,
    sort_sizes: Mapping[str, int],
) -> Iterator[FiniteModel]:
    """Enumerate every interpretation for one explicit carrier-size vector.

    This is the public complete-census surface.  Budgeted witness search stays
    in the certificate helpers above; callers using this iterator own storage,
    quotienting, and the completeness receipt.
    """

    sizes = _validated_size_vector(signature, sort_sizes)
    yield from _interpretations(signature, sizes)


def _validated_size_vector(
    signature: TheorySignature,
    sort_sizes: Mapping[str, int],
) -> dict[str, int]:
    sizes = dict(sort_sizes)
    if set(sizes) != set(signature.sort_map):
        raise ValueError(
            "sort_sizes must name exactly the signature sorts: "
            f"expected {sorted(signature.sort_map)}, got {sorted(sizes)}"
        )
    if any(type(size) is not int or size < 1 for size in sizes.values()):
        raise ValueError("finite carrier sizes must be positive integers")
    return sizes


def verify_receipt_hash(receipt: Mapping[str, Any]) -> bool:
    """Verify the receipt's self-hash without trusting its producer."""

    expected = receipt.get("receipt_sha256")
    certificate_digest = receipt.get("certificate_digest")
    unsigned = dict(receipt)
    unsigned.pop("receipt_sha256", None)
    unsigned.pop("certificate_digest", None)
    return (
        isinstance(expected, str)
        and expected == certificate_digest
        and expected == content_hash(unsigned)
    )


def verify_theory_suite_hash(receipt: Mapping[str, Any]) -> bool:
    """Verify a semantic-suite self-hash without trusting its producer."""

    return verify_receipt_hash(receipt)


def verify_certified_theory_suite(
    signature: TheorySignature,
    axioms: Sequence[AxiomFormula],
    receipt: Mapping[str, Any],
    *,
    base_axioms: Sequence[AxiomFormula] = (),
) -> tuple[bool, list[str]]:
    """Replay every positive semantic witness in an aggregate receipt.

    This verifies mathematical content against authority-supplied IR.  It does
    not authenticate who ran the checker; deployment code can additionally
    require a worker signature or daemon stamp.
    """

    axioms = _ordered_axioms(axioms)
    base_axioms = _ordered_axioms(base_axioms)
    validate_axioms(signature, base_axioms + axioms)
    errors: list[str] = []
    if receipt.get("schema") != THEORY_SUITE_SCHEMA:
        errors.append("wrong_suite_schema")
    if not verify_theory_suite_hash(receipt):
        errors.append("invalid_suite_digest")
    expected_theory_digest = relative_theory_content_hash(
        signature, axioms, base_axioms=base_axioms
    )
    if receipt.get("theory_digest") != expected_theory_digest:
        errors.append("theory_digest_mismatch")
    inputs = receipt.get("input_hashes")
    if not isinstance(inputs, Mapping):
        errors.append("missing_suite_input_hashes")
        inputs = {}
    if inputs.get("signature_sha256") != signature.content_hash:
        errors.append("signature_digest_mismatch")
    if inputs.get("axiom_sha256s") != sorted(
        axiom.content_hash for axiom in axioms
    ):
        errors.append("axiom_digest_mismatch")
    if inputs.get("base_axiom_sha256s") != sorted(
        axiom.content_hash for axiom in base_axioms
    ):
        errors.append("base_axiom_digest_mismatch")
    if receipt.get("status") != CERTIFIED_WITH_WITNESSES:
        errors.append("suite_not_certified_with_witnesses")
    if receipt.get("certified") is not True:
        errors.append("suite_certified_flag_not_true")

    joint = receipt.get("joint_satisfiability")
    if not isinstance(joint, Mapping):
        errors.append("missing_joint_satisfiability_receipt")
    else:
        _verify_joint_receipt(
            signature, base_axioms, axioms, joint, inputs, errors
        )

    independence = receipt.get("independence")
    if not isinstance(independence, list):
        errors.append("missing_independence_receipts")
    else:
        _verify_independence_receipts(
            signature, base_axioms, axioms, independence, inputs, errors
        )
    implications = receipt.get("implications")
    if not isinstance(implications, list):
        errors.append("malformed_implication_receipts")
    elif implications:
        # The aggregate stores optional implication evidence, but replaying an
        # arbitrary implication also requires the authority-supplied target IR.
        # Until that IR is an argument here, do not silently trust nested rows.
        errors.append("unreplayed_implication_receipts")
    return not errors, errors


def _verify_joint_receipt(
    signature: TheorySignature,
    base_axioms: tuple[AxiomFormula, ...],
    axioms: tuple[AxiomFormula, ...],
    receipt: Mapping[str, Any],
    suite_inputs: Mapping[str, Any],
    errors: list[str],
) -> None:
    if not verify_receipt_hash(receipt):
        errors.append("invalid_joint_receipt_digest")
    if receipt.get("check") != "joint_satisfiability" or receipt.get("status") != SAT:
        errors.append("joint_receipt_not_sat")
    inputs = receipt.get("input_hashes")
    if not isinstance(inputs, Mapping):
        errors.append("missing_joint_input_hashes")
        return
    if inputs.get("signature_sha256") != signature.content_hash:
        errors.append("joint_signature_digest_mismatch")
    if inputs.get("axiom_sha256s") != [axiom.content_hash for axiom in axioms]:
        errors.append("joint_axiom_digest_mismatch")
    if inputs.get("base_axiom_sha256s") != [
        axiom.content_hash for axiom in base_axioms
    ]:
        errors.append("joint_base_axiom_digest_mismatch")
    if inputs.get("bounds_sha256") != suite_inputs.get("bounds_sha256"):
        errors.append("joint_bounds_digest_mismatch")
    model = _verified_witness_model(signature, receipt, "joint", errors)
    if model is not None and not _all_hold(
        signature, base_axioms + axioms, model
    ):
        errors.append("joint_witness_does_not_satisfy_theory")


def _verify_independence_receipts(
    signature: TheorySignature,
    base_axioms: tuple[AxiomFormula, ...],
    axioms: tuple[AxiomFormula, ...],
    receipts: list[Any],
    suite_inputs: Mapping[str, Any],
    errors: list[str],
) -> None:
    if len(receipts) != len(axioms):
        errors.append("independence_receipt_count_mismatch")
    by_name = {axiom.name: axiom for axiom in axioms}
    seen: set[str] = set()
    for raw in receipts:
        if not isinstance(raw, Mapping):
            errors.append("malformed_independence_receipt")
            continue
        details = raw.get("details")
        target_name = (
            details.get("target_axiom") if isinstance(details, Mapping) else None
        )
        if not isinstance(target_name, str) or target_name not in by_name:
            errors.append("unknown_independence_target")
            continue
        if target_name in seen:
            errors.append(f"duplicate_independence_target:{target_name}")
            continue
        seen.add(target_name)
        target = by_name[target_name]
        other_candidates = tuple(
            axiom for axiom in axioms if axiom.name != target_name
        )
        background = base_axioms + other_candidates
        if not verify_receipt_hash(raw):
            errors.append(f"invalid_independence_digest:{target_name}")
        if raw.get("check") != "axiom_independence" or raw.get("status") != INDEPENDENCE_WITNESS:
            errors.append(f"independence_receipt_not_witness:{target_name}")
        inputs = raw.get("input_hashes")
        if not isinstance(inputs, Mapping):
            errors.append(f"missing_independence_inputs:{target_name}")
            continue
        if inputs.get("signature_sha256") != signature.content_hash:
            errors.append(f"independence_signature_mismatch:{target_name}")
        if inputs.get("target_axiom_sha256") != target.content_hash:
            errors.append(f"independence_target_mismatch:{target_name}")
        if inputs.get("background_axiom_sha256s") != [
            axiom.content_hash for axiom in other_candidates
        ]:
            errors.append(f"independence_background_mismatch:{target_name}")
        if inputs.get("base_axiom_sha256s") != [
            axiom.content_hash for axiom in base_axioms
        ]:
            errors.append(f"independence_base_mismatch:{target_name}")
        if inputs.get("bounds_sha256") != suite_inputs.get("bounds_sha256"):
            errors.append(f"independence_bounds_mismatch:{target_name}")
        model = _verified_witness_model(
            signature, raw, f"independence:{target_name}", errors
        )
        if model is not None:
            if not _all_hold(signature, background, model):
                errors.append(
                    f"independence_witness_fails_background:{target_name}"
                )
            if evaluate_formula(signature, target.formula, model):
                errors.append(
                    f"independence_witness_does_not_refute_target:{target_name}"
                )
    missing = set(by_name) - seen
    errors.extend(f"missing_independence_target:{name}" for name in sorted(missing))


def _verified_witness_model(
    signature: TheorySignature,
    receipt: Mapping[str, Any],
    label: str,
    errors: list[str],
) -> FiniteModel | None:
    witness = receipt.get("witness")
    if not isinstance(witness, Mapping) or not isinstance(witness.get("model"), Mapping):
        errors.append(f"missing_witness_model:{label}")
        return None
    try:
        model = FiniteModel.from_json(witness["model"])
        validate_model(signature, model)
    except (IRValidationError, TypeError, ValueError) as exc:
        errors.append(f"malformed_witness_model:{label}:{type(exc).__name__}")
        return None
    if witness.get("model_sha256") != model.content_hash(signature):
        errors.append(f"witness_model_digest_mismatch:{label}")
    return model


__all__ = [
    "CERTIFICATE_SCHEMA",
    "CERTIFIED_WITH_WITNESSES",
    "COUNTERMODEL",
    "EQUIVALENT_WITHIN_BOUND",
    "EVALUATOR_VERSION",
    "INDEPENDENCE_WITNESS",
    "NO_COUNTERMODEL_WITHIN_BOUND",
    "NO_CANDIDATE_AXIOMS",
    "NO_INDEPENDENCE_WITNESS_WITHIN_BOUND",
    "NO_MODEL_WITHIN_BOUND",
    "NOT_EQUIVALENT",
    "SAT",
    "SAT_WITHOUT_COMPLETE_INDEPENDENCE_WITNESSES",
    "THEORY_SUITE_SCHEMA",
    "UNKNOWN",
    "FiniteModel",
    "FiniteSearchBounds",
    "SemanticCheckReceipt",
    "TheorySemanticSuiteReceipt",
    "canonicalize_finite_model",
    "certify_axiom_independence",
    "certify_equivalence",
    "certify_implication",
    "certify_joint_satisfiability",
    "certify_theory",
    "evaluate_axiom",
    "evaluate_formula",
    "finite_interpretation_count",
    "finite_model_relabeling_count",
    "iter_finite_models",
    "relabel_finite_model",
    "validate_model",
    "verify_receipt_hash",
    "verify_certified_theory_suite",
    "verify_theory_suite_hash",
]
