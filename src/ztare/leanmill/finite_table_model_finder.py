"""Targeted SMT countermodels for typed finite first-order signatures."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations, product
import json
from math import prod
import time
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from ztare.leanmill.finite_model import (
    FiniteModel,
    evaluate_axiom,
    finite_model_relabeling_count,
    relabel_finite_model,
    validate_model,
)
from ztare.leanmill.theory_ir import (
    AxiomFormula,
    Formula,
    Term,
    TheorySignature,
    content_hash,
    validate_axiom,
)

if TYPE_CHECKING:
    from ztare.leanmill.magma_law_universe import MagmaLaw


@dataclass(frozen=True)
class FiniteModelSearchReceipt:
    status: str
    signature_hash: str
    sort_sizes: tuple[tuple[str, int], ...]
    base_formula_ids: tuple[str, ...]
    premise_formula_ids: tuple[str, ...]
    target_formula_id: str
    solver: str
    timeout_ms: int
    witness: FiniteModel | None = None
    reason: str = ""
    schema: str = "leanmill.finite_model_search.v1"

    @property
    def carrier_size(self) -> int | None:
        return self.sort_sizes[0][1] if len(self.sort_sizes) == 1 else None

    def to_json(self) -> dict[str, Any]:
        core = {
            "schema": self.schema,
            "status": self.status,
            "signature_sha256": self.signature_hash,
            "sort_sizes": dict(self.sort_sizes),
            "base_formula_ids": list(self.base_formula_ids),
            "premise_formula_ids": list(self.premise_formula_ids),
            "target_formula_id": self.target_formula_id,
            "solver": self.solver,
            "timeout_ms": self.timeout_ms,
            "witness": self.witness.to_json() if self.witness else None,
            "reason": self.reason,
            "host_replay_status": (
                "passed" if self.status == "countermodel_found" else "not_applicable"
            ),
            "claim_boundary": "one fixed finite carrier-size vector",
        }
        if self.carrier_size is not None:
            core["carrier_size"] = self.carrier_size
        return {**core, "receipt_sha256": content_hash(core)}


@dataclass(frozen=True)
class FiniteTableSearchReceipt:
    status: str
    carrier_size: int
    premise_formula_ids: tuple[str, ...]
    target_formula_id: str
    solver: str
    timeout_ms: int
    witness: FiniteModel | None = None
    reason: str = ""
    schema: str = "leanmill.finite_table_model_search.v1"

    def to_json(self) -> dict[str, Any]:
        core = {
            "schema": self.schema,
            "status": self.status,
            "carrier_size": self.carrier_size,
            "premise_formula_ids": list(self.premise_formula_ids),
            "target_formula_id": self.target_formula_id,
            "solver": self.solver,
            "timeout_ms": self.timeout_ms,
            "witness": self.witness.to_json() if self.witness else None,
            "reason": self.reason,
            "claim_boundary": "one fixed finite carrier size",
        }
        return {**core, "receipt_sha256": content_hash(core)}


@dataclass(frozen=True)
class FiniteModelIsomorphismClass:
    """One canonical model and the number of labeled models in its orbit."""

    model: FiniteModel
    multiplicity: int

    def __post_init__(self) -> None:
        if type(self.multiplicity) is not int or self.multiplicity < 1:
            raise ValueError("finite model class multiplicity must be positive")


@dataclass(frozen=True)
class FiniteModelEnumerationReceipt:
    """Exhaustion receipt for one fixed finite carrier-size vector."""

    status: str
    signature_hash: str
    sort_sizes: tuple[tuple[str, int], ...]
    base_formula_ids: tuple[str, ...]
    solver: str
    timeout_ms: int
    max_canonical_models: int
    quotient_policy: str
    solver_checks: int
    accepted_labeled_count: int
    canonical_model_count: int
    reason: str = ""
    schema: str = "leanmill.finite_model_enumeration.v1"

    @property
    def complete(self) -> bool:
        return self.status == "exhausted"

    @property
    def receipt_digest(self) -> str:
        return content_hash(self.to_json(include_digest=False))

    def to_json(self, *, include_digest: bool = True) -> dict[str, Any]:
        core = {
            "schema": self.schema,
            "status": self.status,
            "signature_sha256": self.signature_hash,
            "sort_sizes": dict(self.sort_sizes),
            "base_formula_ids": list(self.base_formula_ids),
            "solver": self.solver,
            "timeout_ms": self.timeout_ms,
            "max_canonical_models": self.max_canonical_models,
            "quotient_policy": self.quotient_policy,
            "solver_checks": self.solver_checks,
            "accepted_labeled_count": self.accepted_labeled_count,
            "canonical_model_count": self.canonical_model_count,
            "complete": self.complete,
            "reason": self.reason,
            "host_replay_status": "passed",
            "claim_boundary": "one fixed finite carrier-size vector",
        }
        return {**core, "receipt_sha256": content_hash(core)} if include_digest else core


@dataclass(frozen=True)
class FiniteModelEnumerationResult:
    model_classes: tuple[FiniteModelIsomorphismClass, ...]
    receipt: FiniteModelEnumerationReceipt

    def __post_init__(self) -> None:
        if len(self.model_classes) != self.receipt.canonical_model_count:
            raise ValueError("finite model enumeration class count mismatch")
        if sum(row.multiplicity for row in self.model_classes) != (
            self.receipt.accepted_labeled_count
        ):
            raise ValueError("finite model enumeration multiplicity mismatch")


def _normalize_sort_sizes(
    signature: TheorySignature,
    sort_sizes: Mapping[str, int],
) -> dict[str, int]:
    if not isinstance(sort_sizes, Mapping) or not all(
        isinstance(key, str) and type(value) is int
        for key, value in sort_sizes.items()
    ):
        raise ValueError("sort_sizes must name every sort with a positive integer")
    sizes = dict(sort_sizes)
    if set(sizes) != set(signature.sort_map) or any(value < 1 for value in sizes.values()):
        raise ValueError("sort_sizes must name every sort with a positive integer")
    return sizes


class _FiniteSMTEncoding:
    """Shared Z3 lowering for countermodel search and complete enumeration."""

    def __init__(self, signature: TheorySignature, sizes: Mapping[str, int]) -> None:
        import z3

        self.z3 = z3
        self.signature = signature
        self.sizes = dict(sizes)
        self.solver = z3.Solver()
        self.operation_cells: dict[str, list[Any]] = {}
        self.relation_cells: dict[str, list[Any]] = {}
        for operation in signature.operations:
            row_count = prod(self.sizes[sort] for sort in operation.arg_sorts)
            cells = [
                z3.Int(f"op_{operation.name}_{index}")
                for index in range(row_count)
            ]
            self.solver.add(
                *(
                    z3.And(cell >= 0, cell < self.sizes[operation.result_sort])
                    for cell in cells
                )
            )
            self.operation_cells[operation.name] = cells
        for relation in signature.relations:
            row_count = prod(self.sizes[sort] for sort in relation.arg_sorts)
            self.relation_cells[relation.name] = [
                z3.Bool(f"rel_{relation.name}_{index}")
                for index in range(row_count)
            ]

    @property
    def solver_name(self) -> str:
        return f"z3:{self.z3.get_version_string()}"

    def _table_at(
        self,
        cells: Sequence[Any],
        args: Sequence[Any],
        arg_sorts: Sequence[str],
    ) -> Any:
        if not args:
            return cells[0]
        rows = tuple(product(*(range(self.sizes[sort]) for sort in arg_sorts)))
        value = cells[-1]
        for index in reversed(range(len(rows) - 1)):
            condition = self.z3.And(
                *(
                    arg == expected
                    for arg, expected in zip(args, rows[index], strict=True)
                )
            )
            value = self.z3.If(condition, cells[index], value)
        return value

    def _term(self, term: Term, environment: Mapping[str, Any]) -> Any:
        if term.kind == "var":
            return environment[term.name]
        operation = self.signature.operation_map[term.name]
        args = tuple(self._term(child, environment) for child in term.args)
        return self._table_at(
            self.operation_cells[operation.name], args, operation.arg_sorts
        )

    def formula(self, formula: Formula, environment: Mapping[str, Any] | None = None) -> Any:
        environment = dict(environment or {})
        kind = formula.kind
        if kind == "true":
            return self.z3.BoolVal(True)
        if kind == "false":
            return self.z3.BoolVal(False)
        if kind == "eq":
            return self._term(formula.terms[0], environment) == self._term(
                formula.terms[1], environment
            )
        if kind == "rel":
            relation = self.signature.relation_map[formula.relation or ""]
            args = tuple(self._term(term, environment) for term in formula.terms)
            return self._table_at(
                self.relation_cells[relation.name], args, relation.arg_sorts
            )
        if kind == "not":
            return self.z3.Not(self.formula(formula.formulas[0], environment))
        if kind == "and":
            return self.z3.And(
                *(self.formula(row, environment) for row in formula.formulas)
            )
        if kind == "or":
            return self.z3.Or(
                *(self.formula(row, environment) for row in formula.formulas)
            )
        if kind == "implies":
            return self.z3.Implies(
                self.formula(formula.formulas[0], environment),
                self.formula(formula.formulas[1], environment),
            )
        if kind == "iff":
            return self.formula(
                formula.formulas[0], environment
            ) == self.formula(formula.formulas[1], environment)
        if kind not in {"forall", "exists"}:
            raise ValueError(
                f"unsupported formula kind in finite SMT encoding: {kind!r}"
            )
        grounded = []
        for values in product(
            *(range(self.sizes[binder.sort]) for binder in formula.binders)
        ):
            local = dict(environment)
            local.update(
                {
                    binder.name: self.z3.IntVal(value)
                    for binder, value in zip(formula.binders, values, strict=True)
                }
            )
            grounded.append(self.formula(formula.formulas[0], local))
        return (
            self.z3.And(*grounded)
            if kind == "forall"
            else self.z3.Or(*grounded)
        )

    def add_axioms(self, axioms: Sequence[AxiomFormula]) -> None:
        self.solver.add(*(self.formula(axiom.formula) for axiom in axioms))

    def check(self, timeout_ms: int) -> Any:
        self.solver.set(timeout=timeout_ms)
        return self.solver.check()

    def materialize_model(self) -> FiniteModel:
        z3_model = self.solver.model()
        model = FiniteModel(
            sort_sizes=tuple(sorted(self.sizes.items())),
            operations=tuple(
                (
                    operation.name,
                    tuple(
                        z3_model.eval(cell, model_completion=True).as_long()
                        for cell in self.operation_cells[operation.name]
                    ),
                )
                for operation in self.signature.operations
            ),
            relations=tuple(
                (
                    relation.name,
                    tuple(
                        self.z3.is_true(z3_model.eval(cell, model_completion=True))
                        for cell in self.relation_cells[relation.name]
                    ),
                )
                for relation in self.signature.relations
            ),
        )
        validate_model(self.signature, model)
        return model

    def block_models(self, models: Sequence[FiniteModel]) -> None:
        for model in models:
            operation_tables = model.operation_map
            relation_tables = model.relation_map
            differences = [
                cell != value
                for operation in self.signature.operations
                for cell, value in zip(
                    self.operation_cells[operation.name],
                    operation_tables[operation.name],
                    strict=True,
                )
            ]
            differences.extend(
                cell != self.z3.BoolVal(value)
                for relation in self.signature.relations
                for cell, value in zip(
                    self.relation_cells[relation.name],
                    relation_tables[relation.name],
                    strict=True,
                )
            )
            self.solver.add(self.z3.Or(*differences))


def _isomorphism_class(
    signature: TheorySignature,
    model: FiniteModel,
    *,
    max_relabelings: int,
) -> tuple[FiniteModel, tuple[FiniteModel, ...]]:
    count = finite_model_relabeling_count(model)
    if count > max_relabelings:
        raise ValueError("finite model isomorphism quotient exceeds relabeling cap")
    sorts = tuple(name for name, _size in model.sort_sizes)
    bands = tuple(
        tuple(permutations(range(model.sort_size_map[sort]))) for sort in sorts
    )
    orbit: dict[str, FiniteModel] = {}
    for choices in product(*bands):
        candidate = relabel_finite_model(
            signature,
            model,
            dict(zip(sorts, choices, strict=True)),
        )
        key = json.dumps(candidate.to_json(), sort_keys=True, separators=(",", ":"))
        orbit.setdefault(key, candidate)
    ordered = tuple(orbit[key] for key in sorted(orbit))
    if not ordered:
        raise RuntimeError("finite model isomorphism orbit is empty")
    return ordered[0], ordered


def enumerate_finite_models_smt(
    signature: TheorySignature,
    *,
    sort_sizes: Mapping[str, int],
    base_axioms: Sequence[AxiomFormula] = (),
    quotient_isomorphisms: bool = True,
    max_relabelings_per_model: int = 720,
    max_canonical_models: int = 5_000,
    timeout_ms: int = 300_000,
) -> FiniteModelEnumerationResult:
    """Enumerate a fixed finite base theory; exactness requires a final UNSAT."""

    sizes = _normalize_sort_sizes(signature, sort_sizes)
    if type(max_relabelings_per_model) is not int or max_relabelings_per_model < 1:
        raise ValueError("max_relabelings_per_model must be positive")
    if type(max_canonical_models) is not int or max_canonical_models < 1:
        raise ValueError("max_canonical_models must be positive")
    if type(timeout_ms) is not int or timeout_ms < 1:
        raise ValueError("timeout_ms must be positive")
    base_axioms = tuple(base_axioms)
    for axiom in base_axioms:
        validate_axiom(signature, axiom)
    encoding = _FiniteSMTEncoding(signature, sizes)
    encoding.add_axioms(base_axioms)
    deadline = time.monotonic() + timeout_ms / 1_000
    classes: list[FiniteModelIsomorphismClass] = []
    solver_checks = 0
    status = "unknown"
    reason = ""
    while True:
        remaining_ms = int((deadline - time.monotonic()) * 1_000)
        if remaining_ms < 1:
            status = "timeout"
            reason = "enumeration wall-time bound reached before exhaustion"
            break
        verdict = encoding.check(remaining_ms)
        solver_checks += 1
        if verdict == encoding.z3.unsat:
            status = "exhausted"
            reason = "SMT blocking clauses exhausted the fixed size vector"
            break
        if verdict == encoding.z3.unknown:
            status = "unknown"
            reason = encoding.solver.reason_unknown()
            break
        if len(classes) >= max_canonical_models:
            status = "model_cap_reached"
            reason = "another model exists beyond the canonical-model cap"
            break
        model = encoding.materialize_model()
        if not all(evaluate_axiom(signature, row, model) for row in base_axioms):
            raise RuntimeError("SMT enumeration model failed host base-theory replay")
        if quotient_isomorphisms:
            canonical, orbit = _isomorphism_class(
                signature,
                model,
                max_relabelings=max_relabelings_per_model,
            )
        else:
            canonical, orbit = model, (model,)
        encoding.block_models(orbit)
        classes.append(FiniteModelIsomorphismClass(canonical, len(orbit)))
    receipt = FiniteModelEnumerationReceipt(
        status=status,
        signature_hash=signature.content_hash,
        sort_sizes=tuple(sorted(sizes.items())),
        base_formula_ids=tuple(
            "formula:" + row.semantic_hash for row in base_axioms
        ),
        solver=encoding.solver_name,
        timeout_ms=timeout_ms,
        max_canonical_models=max_canonical_models,
        quotient_policy=(
            "sortwise_isomorphism_orbit_blocking.v1"
            if quotient_isomorphisms
            else "labeled_models_no_isomorphism_quotient.v1"
        ),
        solver_checks=solver_checks,
        accepted_labeled_count=sum(row.multiplicity for row in classes),
        canonical_model_count=len(classes),
        reason=reason,
    )
    return FiniteModelEnumerationResult(tuple(classes), receipt)


def find_finite_countermodel(
    signature: TheorySignature,
    premises: Sequence[AxiomFormula],
    target: AxiomFormula,
    *,
    sort_sizes: Mapping[str, int] | None = None,
    carrier_size: int | None = None,
    base_axioms: Sequence[AxiomFormula] = (),
    timeout_ms: int = 30_000,
) -> FiniteModelSearchReceipt:
    """Decide ``base ∧ premises ∧ ¬target`` on one finite size vector."""

    if sort_sizes is None:
        if carrier_size is None or len(signature.sorts) != 1:
            raise ValueError("countermodel search requires one complete sort-size vector")
        sort_sizes = {signature.sorts[0].name: carrier_size}
    sizes = _normalize_sort_sizes(signature, sort_sizes)
    if type(timeout_ms) is not int or timeout_ms < 1:
        raise ValueError("timeout_ms must be positive")
    premises = tuple(premises)
    base_axioms = tuple(base_axioms)
    for axiom in (*base_axioms, *premises, target):
        validate_axiom(signature, axiom)

    encoding = _FiniteSMTEncoding(signature, sizes)
    encoding.add_axioms((*base_axioms, *premises))
    common = {
        "signature_hash": signature.content_hash,
        "sort_sizes": tuple(sorted(sizes.items())),
        "base_formula_ids": tuple(
            "formula:" + row.semantic_hash for row in base_axioms
        ),
        "premise_formula_ids": tuple(
            "formula:" + row.semantic_hash for row in premises
        ),
        "target_formula_id": "formula:" + target.semantic_hash,
        "solver": encoding.solver_name,
        "timeout_ms": timeout_ms,
    }
    premise_verdict = encoding.check(timeout_ms)
    if premise_verdict == encoding.z3.unknown:
        return FiniteModelSearchReceipt(
            status="unknown",
            reason="premise satisfiability: " + encoding.solver.reason_unknown(),
            **common,
        )
    if premise_verdict == encoding.z3.unsat:
        return FiniteModelSearchReceipt(
            status="no_premise_model_at_fixed_size",
            reason="base theory and premises have no model on the fixed size vector",
            **common,
        )
    encoding.solver.add(encoding.z3.Not(encoding.formula(target.formula)))
    verdict = encoding.check(timeout_ms)
    if verdict == encoding.z3.unknown:
        return FiniteModelSearchReceipt(
            status="unknown", reason=encoding.solver.reason_unknown(), **common
        )
    if verdict == encoding.z3.unsat:
        return FiniteModelSearchReceipt(
            status="no_countermodel_at_fixed_size",
            reason="SMT encoding exhausted the fixed carrier-size vector",
            **common,
        )
    witness = encoding.materialize_model()
    if not all(
        evaluate_axiom(signature, row, witness) for row in (*base_axioms, *premises)
    ):
        raise RuntimeError("SMT witness failed host premise replay")
    if evaluate_axiom(signature, target, witness):
        raise RuntimeError("SMT witness failed host target replay")
    return FiniteModelSearchReceipt(
        status="countermodel_found", witness=witness, **common
    )


def find_magma_countermodel(
    premises: Sequence[MagmaLaw],
    target: MagmaLaw,
    *,
    carrier_size: int,
    timeout_ms: int = 30_000,
) -> FiniteTableSearchReceipt:
    """Decide premises and not-target over one fixed finite carrier size."""
    from ztare.leanmill.magma_law_universe import anonymous_magma_signature

    if type(carrier_size) is not int or carrier_size < 1:
        raise ValueError("carrier_size must be positive")
    if type(timeout_ms) is not int or timeout_ms < 1:
        raise ValueError("timeout_ms must be positive")
    generic = find_finite_countermodel(
        anonymous_magma_signature(),
        tuple(row.axiom for row in premises),
        target.axiom,
        carrier_size=carrier_size,
        timeout_ms=timeout_ms,
    )
    return FiniteTableSearchReceipt(
        status=generic.status,
        carrier_size=carrier_size,
        premise_formula_ids=tuple(row.formula_id for row in premises),
        target_formula_id=target.formula_id,
        solver=generic.solver,
        timeout_ms=timeout_ms,
        witness=generic.witness,
        reason=generic.reason,
    )


__all__ = [
    "FiniteModelEnumerationReceipt", "FiniteModelEnumerationResult",
    "FiniteModelIsomorphismClass", "FiniteModelSearchReceipt",
    "FiniteTableSearchReceipt", "enumerate_finite_models_smt",
    "find_finite_countermodel", "find_magma_countermodel",
]
