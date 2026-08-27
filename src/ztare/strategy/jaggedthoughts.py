"""JaggedThoughts: typed strategic programs and scope-bound frontier closure.

The module deliberately owns a small, deterministic kernel.  A strategy
substrate supplies typed terminals and operators, external/internal/dynamic burdens of
proof, evaluations, an explicit neighborhood, and a representation audit.
JaggedThoughts owns program identity, bounded enumeration, witnessed frontier
partitioning, and the distinction between frozen-grammar scope closure and
representation-audited decision closure.

All objectives are maximized.  A lowering that wants to minimize cost or risk
must provide a sign-normalized objective and name that transformation in its
evaluation-model identity.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from hashlib import sha256
from itertools import product
import json
import math
from typing import Any, Callable, Iterable, Literal, Mapping, Sequence


ClaimKind = Literal["external", "internal", "dynamic"]
ClaimStatus = Literal["supported", "refuted", "unresolved"]
RepresentationStatus = Literal["unassessed", "residual", "passed"]
LandscapeMode = Literal["fixed", "endogenous_transition"]

_PROGRAM_SCHEMA = "jaggedthoughts-program-v1"
_ENUMERATION_SCHEMA = "jaggedthoughts-enumeration-v1"
_SCOPE_SCHEMA = "jaggedthoughts-frontier-scope-v1"
_CERTIFICATE_SCHEMA = "jaggedthoughts-frontier-certificate-v1"


def _require_identity(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")


def _stable_tuple(values: Iterable[str]) -> tuple[str, ...]:
    materialized = tuple(values)
    for value in materialized:
        _require_identity(value, "identity member")
    return tuple(sorted(set(materialized)))


def _digest(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class TypedTerminal:
    """One atomic, typed symbol available to the strategy grammar."""

    terminal_id: str
    output_type: str
    claim_ids: tuple[str, ...] = ()
    description: str = ""

    def __post_init__(self) -> None:
        _require_identity(self.terminal_id, "terminal_id")
        _require_identity(self.output_type, "terminal output_type")
        object.__setattr__(self, "claim_ids", _stable_tuple(self.claim_ids))
        if not isinstance(self.description, str):
            raise ValueError("terminal description must be a string")
        object.__setattr__(self, "description", self.description.strip())

    def to_dict(self) -> dict[str, Any]:
        return {
            "terminal_id": self.terminal_id,
            "output_type": self.output_type,
            "claim_ids": list(self.claim_ids),
            "description": self.description,
        }


@dataclass(frozen=True, slots=True)
class TypedOperator:
    """One typed constructor in the strategic program language."""

    operator_id: str
    input_types: tuple[str, ...]
    output_type: str
    claim_ids: tuple[str, ...] = ()
    commutative: bool = False
    description: str = ""

    def __post_init__(self) -> None:
        _require_identity(self.operator_id, "operator_id")
        _require_identity(self.output_type, "operator output_type")
        if not self.input_types:
            raise ValueError("operators must take at least one typed input")
        for input_type in self.input_types:
            _require_identity(input_type, "operator input_type")
        if self.commutative and len(set(self.input_types)) != 1:
            raise ValueError(
                "commutative operators require identical ordered input types"
            )
        object.__setattr__(self, "claim_ids", _stable_tuple(self.claim_ids))
        if not isinstance(self.description, str):
            raise ValueError("operator description must be a string")
        object.__setattr__(self, "description", self.description.strip())

    def to_dict(self) -> dict[str, Any]:
        return {
            "operator_id": self.operator_id,
            "input_types": list(self.input_types),
            "output_type": self.output_type,
            "claim_ids": list(self.claim_ids),
            "commutative": self.commutative,
            "description": self.description,
        }


@dataclass(frozen=True, slots=True)
class OperatorGrammar:
    """A versioned, finite signature whose programs may recurse by type."""

    grammar_id: str
    version: str
    terminals: tuple[TypedTerminal, ...]
    operators: tuple[TypedOperator, ...]
    grammar_digest: str = field(init=False)

    def __post_init__(self) -> None:
        _require_identity(self.grammar_id, "grammar_id")
        _require_identity(self.version, "grammar version")
        terminal_ids = [terminal.terminal_id for terminal in self.terminals]
        operator_ids = [operator.operator_id for operator in self.operators]
        if len(terminal_ids) != len(set(terminal_ids)):
            raise ValueError("terminal IDs must be unique inside one grammar")
        if len(operator_ids) != len(set(operator_ids)):
            raise ValueError("operator IDs must be unique inside one grammar")
        if set(terminal_ids) & set(operator_ids):
            raise ValueError("terminal and operator IDs share one identity namespace")
        payload = {
            "grammar_id": self.grammar_id,
            "version": self.version,
            "terminals": [
                terminal.to_dict()
                for terminal in sorted(
                    self.terminals,
                    key=lambda item: item.terminal_id,
                )
            ],
            "operators": [
                operator.to_dict()
                for operator in sorted(
                    self.operators,
                    key=lambda item: item.operator_id,
                )
            ],
        }
        object.__setattr__(self, "grammar_digest", _digest(payload))

    def to_dict(self) -> dict[str, Any]:
        return {
            "grammar_id": self.grammar_id,
            "version": self.version,
            "grammar_digest": self.grammar_digest,
            "terminals": [
                terminal.to_dict()
                for terminal in sorted(
                    self.terminals,
                    key=lambda item: item.terminal_id,
                )
            ],
            "operators": [
                operator.to_dict()
                for operator in sorted(
                    self.operators,
                    key=lambda item: item.operator_id,
                )
            ],
        }


@dataclass(frozen=True, slots=True)
class Program:
    """One content-bound derivation in a frozen operator grammar."""

    program_id: str
    grammar_id: str
    grammar_version: str
    grammar_digest: str
    output_type: str
    depth: int
    terminal_id: str | None = None
    operator_id: str | None = None
    children: tuple[Program, ...] = ()
    claim_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_identity(self.program_id, "program_id")
        _require_identity(self.grammar_id, "program grammar_id")
        _require_identity(self.grammar_version, "program grammar_version")
        _require_identity(self.grammar_digest, "program grammar_digest")
        _require_identity(self.output_type, "program output_type")
        if self.depth < 0:
            raise ValueError("program depth cannot be negative")
        is_terminal = self.terminal_id is not None
        is_operator = self.operator_id is not None
        if is_terminal == is_operator:
            raise ValueError("program must be exactly one terminal or operator node")
        if is_terminal and (self.children or self.depth != 0):
            raise ValueError("terminal programs have no children and depth zero")
        if is_operator and not self.children:
            raise ValueError("operator programs require child programs")
        object.__setattr__(self, "claim_ids", _stable_tuple(self.claim_ids))

    @property
    def root_symbol(self) -> str:
        return self.terminal_id or self.operator_id or ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "program_id": self.program_id,
            "grammar_id": self.grammar_id,
            "grammar_version": self.grammar_version,
            "grammar_digest": self.grammar_digest,
            "output_type": self.output_type,
            "depth": self.depth,
            "terminal_id": self.terminal_id,
            "operator_id": self.operator_id,
            "child_program_ids": [child.program_id for child in self.children],
            "claim_ids": list(self.claim_ids),
        }


def _terminal_program(grammar: OperatorGrammar, terminal: TypedTerminal) -> Program:
    identity = {
        "schema": _PROGRAM_SCHEMA,
        "grammar_id": grammar.grammar_id,
        "grammar_version": grammar.version,
        "grammar_digest": grammar.grammar_digest,
        "node_kind": "terminal",
        "symbol_id": terminal.terminal_id,
        "output_type": terminal.output_type,
    }
    return Program(
        program_id=_digest(identity),
        grammar_id=grammar.grammar_id,
        grammar_version=grammar.version,
        grammar_digest=grammar.grammar_digest,
        output_type=terminal.output_type,
        depth=0,
        terminal_id=terminal.terminal_id,
        claim_ids=terminal.claim_ids,
    )


def _operator_program(
    grammar: OperatorGrammar,
    operator: TypedOperator,
    children: Sequence[Program],
) -> Program:
    ordered_children = tuple(children)
    if operator.commutative:
        ordered_children = tuple(
            sorted(ordered_children, key=lambda child: child.program_id)
        )
    identity = {
        "schema": _PROGRAM_SCHEMA,
        "grammar_id": grammar.grammar_id,
        "grammar_version": grammar.version,
        "grammar_digest": grammar.grammar_digest,
        "node_kind": "operator",
        "symbol_id": operator.operator_id,
        "output_type": operator.output_type,
        "child_program_ids": [child.program_id for child in ordered_children],
    }
    claim_ids: set[str] = set(operator.claim_ids)
    for child in ordered_children:
        claim_ids.update(child.claim_ids)
    return Program(
        program_id=_digest(identity),
        grammar_id=grammar.grammar_id,
        grammar_version=grammar.version,
        grammar_digest=grammar.grammar_digest,
        output_type=operator.output_type,
        depth=1 + max(child.depth for child in ordered_children),
        operator_id=operator.operator_id,
        children=ordered_children,
        claim_ids=tuple(sorted(claim_ids)),
    )


def build_typed_program(
    grammar: OperatorGrammar,
    *,
    terminal_id: str | None = None,
    operator_id: str | None = None,
    children: Sequence[Program] = (),
) -> Program:
    """Build one grammar-bound program without enumerating unrelated syntax."""
    if (terminal_id is None) == (operator_id is None):
        raise ValueError("typed program requires exactly one terminal or operator")
    if terminal_id is not None:
        if children:
            raise ValueError("terminal programs cannot have children")
        terminal = next(
            (row for row in grammar.terminals if row.terminal_id == terminal_id), None
        )
        if terminal is None:
            raise ValueError(f"grammar has no terminal {terminal_id}")
        return _terminal_program(grammar, terminal)

    operator = next(
        (row for row in grammar.operators if row.operator_id == operator_id), None
    )
    if operator is None:
        raise ValueError(f"grammar has no operator {operator_id}")
    child_rows = tuple(children)
    if tuple(row.output_type for row in child_rows) != operator.input_types:
        raise ValueError(f"operator {operator_id} received incompatible child types")
    if any(
        row.grammar_id != grammar.grammar_id
        or row.grammar_version != grammar.version
        or row.grammar_digest != grammar.grammar_digest
        for row in child_rows
    ):
        raise ValueError("operator children must belong to the supplied grammar")
    return _operator_program(grammar, operator, child_rows)


@dataclass(frozen=True, slots=True)
class EnumerationResidual:
    kind: str
    detail: str
    depth: int | None = None
    symbol_id: str | None = None
    child_program_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "detail": self.detail,
            "depth": self.depth,
            "symbol_id": self.symbol_id,
            "child_program_ids": list(self.child_program_ids),
        }


@dataclass(frozen=True, slots=True)
class EnumerationResult:
    grammar_id: str
    grammar_version: str
    grammar_digest: str
    max_depth: int
    max_programs: int
    programs: tuple[Program, ...]
    exhausted_within_scope: bool
    residuals: tuple[EnumerationResidual, ...]
    enumeration_digest: str

    def programs_of_type(self, output_type: str) -> tuple[Program, ...]:
        return tuple(
            program for program in self.programs if program.output_type == output_type
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": _ENUMERATION_SCHEMA,
            "grammar_id": self.grammar_id,
            "grammar_version": self.grammar_version,
            "grammar_digest": self.grammar_digest,
            "max_depth": self.max_depth,
            "max_programs": self.max_programs,
            "programs": [program.to_dict() for program in self.programs],
            "exhausted_within_scope": self.exhausted_within_scope,
            "residuals": [residual.to_dict() for residual in self.residuals],
            "enumeration_digest": self.enumeration_digest,
        }


def _enumeration_digest(
    *,
    grammar: OperatorGrammar,
    max_depth: int,
    max_programs: int,
    programs: Sequence[Program],
    exhausted: bool,
    residuals: Sequence[EnumerationResidual],
) -> str:
    return _digest({
        "schema": _ENUMERATION_SCHEMA,
        "grammar_id": grammar.grammar_id,
        "grammar_version": grammar.version,
        "grammar_digest": grammar.grammar_digest,
        "max_depth": max_depth,
        "max_programs": max_programs,
        "program_ids": [program.program_id for program in programs],
        "exhausted_within_scope": exhausted,
        "residuals": [residual.to_dict() for residual in residuals],
    })


def compile_enumeration_result(
    grammar: OperatorGrammar,
    *,
    programs: Sequence[Program],
    max_depth: int,
    max_programs: int,
    exhausted_within_scope: bool = True,
    residuals: Sequence[EnumerationResidual] = (),
) -> EnumerationResult:
    """Bind a specialized, already-closed program population to the kernel contract."""
    rows = tuple(sorted(programs, key=lambda row: (row.depth, row.program_id)))
    residual_rows = tuple(residuals)
    if max_depth < 0 or max_programs < 1 or len(rows) > max_programs:
        raise ValueError("invalid specialized enumeration bounds")
    if len({row.program_id for row in rows}) != len(rows):
        raise ValueError("specialized enumeration contains duplicate program identities")
    if any(row.depth > max_depth for row in rows):
        raise ValueError("specialized enumeration exceeds its depth bound")
    if any(
        row.grammar_id != grammar.grammar_id
        or row.grammar_version != grammar.version
        or row.grammar_digest != grammar.grammar_digest
        for row in rows
    ):
        raise ValueError("specialized enumeration contains a foreign program")
    digest = _enumeration_digest(
        grammar=grammar,
        max_depth=max_depth,
        max_programs=max_programs,
        programs=rows,
        exhausted=exhausted_within_scope,
        residuals=residual_rows,
    )
    return EnumerationResult(
        grammar_id=grammar.grammar_id,
        grammar_version=grammar.version,
        grammar_digest=grammar.grammar_digest,
        max_depth=max_depth,
        max_programs=max_programs,
        programs=rows,
        exhausted_within_scope=exhausted_within_scope,
        residuals=residual_rows,
        enumeration_digest=digest,
    )


def enumerate_typed_programs(
    grammar: OperatorGrammar,
    *,
    max_depth: int,
    max_programs: int,
) -> EnumerationResult:
    """Enumerate every well-typed program inside the declared finite scope.

    Enumeration is bottom-up.  A depth-d stage reads only programs admitted in
    earlier stages and requires at least one child at depth d-1.  This makes
    recursive same-type operators finite under ``max_depth`` and keeps output
    order independent of dictionary or set iteration.
    """
    if max_depth < 0:
        raise ValueError("max_depth cannot be negative")
    if max_programs < 1:
        raise ValueError("max_programs must be positive")

    programs: list[Program] = []
    seen: set[str] = set()
    residuals: list[EnumerationResidual] = []

    def finish(exhausted: bool) -> EnumerationResult:
        digest = _enumeration_digest(
            grammar=grammar,
            max_depth=max_depth,
            max_programs=max_programs,
            programs=programs,
            exhausted=exhausted,
            residuals=residuals,
        )
        return EnumerationResult(
            grammar_id=grammar.grammar_id,
            grammar_version=grammar.version,
            grammar_digest=grammar.grammar_digest,
            max_depth=max_depth,
            max_programs=max_programs,
            programs=tuple(programs),
            exhausted_within_scope=exhausted,
            residuals=tuple(residuals),
            enumeration_digest=digest,
        )

    for terminal in sorted(grammar.terminals, key=lambda item: item.terminal_id):
        program = _terminal_program(grammar, terminal)
        if len(programs) >= max_programs:
            residuals.append(EnumerationResidual(
                kind="program_budget_exhausted",
                detail="budget ended while interning grammar terminals",
                depth=0,
                symbol_id=terminal.terminal_id,
            ))
            return finish(False)
        programs.append(program)
        seen.add(program.program_id)

    operators = sorted(grammar.operators, key=lambda item: item.operator_id)
    for depth in range(1, max_depth + 1):
        prior_programs = tuple(programs)
        by_type: dict[str, tuple[Program, ...]] = {}
        types = {program.output_type for program in prior_programs}
        for output_type in types:
            by_type[output_type] = tuple(
                program
                for program in prior_programs
                if program.output_type == output_type and program.depth < depth
            )

        stage: list[Program] = []
        stage_seen: set[str] = set()
        for operator in operators:
            pools = [by_type.get(input_type, ()) for input_type in operator.input_types]
            if any(not pool for pool in pools):
                continue
            for children in product(*pools):
                if max(child.depth for child in children) != depth - 1:
                    continue
                if operator.commutative:
                    child_ids = tuple(child.program_id for child in children)
                    if child_ids != tuple(sorted(child_ids)):
                        continue
                program = _operator_program(grammar, operator, children)
                if program.program_id in seen or program.program_id in stage_seen:
                    continue
                if len(programs) + len(stage) >= max_programs:
                    programs.extend(stage)
                    residuals.append(EnumerationResidual(
                        kind="program_budget_exhausted",
                        detail=(
                            "budget ended before all type-compatible operator "
                            "applications inside the depth bound were interned"
                        ),
                        depth=depth,
                        symbol_id=operator.operator_id,
                        child_program_ids=tuple(
                            child.program_id for child in children
                        ),
                    ))
                    return finish(False)
                stage.append(program)
                stage_seen.add(program.program_id)
        programs.extend(stage)
        seen.update(stage_seen)

    return finish(True)


def compile_burden_of_proof(program: Program) -> tuple[str, ...]:
    """Return the exact, inherited burden-claim identities of one program."""
    return program.claim_ids


@dataclass(frozen=True, slots=True)
class TypedValue:
    """One runtime value whose type is checked at the grammar boundary."""

    value_type: str
    value: Any

    def __post_init__(self) -> None:
        _require_identity(self.value_type, "typed value type")


@dataclass(frozen=True, slots=True)
class ProgramInterpretation:
    """Substrate-owned semantics for one exact grammar digest."""

    interpretation_id: str
    grammar_digest: str
    terminal_values: Mapping[str, TypedValue]
    operator_functions: Mapping[
        str,
        Callable[[tuple[TypedValue, ...]], TypedValue],
    ]

    def __post_init__(self) -> None:
        _require_identity(self.interpretation_id, "interpretation_id")
        _require_identity(self.grammar_digest, "interpretation grammar_digest")


def interpret_program(
    program: Program,
    *,
    grammar: OperatorGrammar,
    interpretation: ProgramInterpretation,
) -> TypedValue:
    """Execute one typed operator program under substrate-supplied semantics."""
    if (
        program.grammar_id != grammar.grammar_id
        or program.grammar_version != grammar.version
        or program.grammar_digest != grammar.grammar_digest
    ):
        raise ValueError("program does not belong to the supplied grammar")
    if interpretation.grammar_digest != grammar.grammar_digest:
        raise ValueError("interpretation does not belong to the supplied grammar")
    terminals = {item.terminal_id: item for item in grammar.terminals}
    operators = {item.operator_id: item for item in grammar.operators}
    memo: dict[str, TypedValue] = {}

    def execute(node: Program) -> TypedValue:
        cached = memo.get(node.program_id)
        if cached is not None:
            return cached
        if node.terminal_id is not None:
            terminal = terminals.get(node.terminal_id)
            value = interpretation.terminal_values.get(node.terminal_id)
            if terminal is None or value is None:
                raise ValueError(
                    f"interpretation is missing terminal {node.terminal_id}"
                )
            if value.value_type != terminal.output_type:
                raise TypeError(
                    f"terminal {node.terminal_id} returned {value.value_type}; "
                    f"expected {terminal.output_type}"
                )
        else:
            operator_id = node.operator_id or ""
            operator = operators.get(operator_id)
            function = interpretation.operator_functions.get(operator_id)
            if operator is None or function is None:
                raise ValueError(
                    f"interpretation is missing operator {operator_id}"
                )
            child_values = tuple(execute(child) for child in node.children)
            child_types = tuple(value.value_type for value in child_values)
            if child_types != operator.input_types:
                raise TypeError(
                    f"operator {operator_id} received {child_types}; "
                    f"expected {operator.input_types}"
                )
            value = function(child_values)
            if not isinstance(value, TypedValue):
                raise TypeError(
                    f"operator {operator_id} must return TypedValue"
                )
            if value.value_type != operator.output_type:
                raise TypeError(
                    f"operator {operator_id} returned {value.value_type}; "
                    f"expected {operator.output_type}"
                )
        if value.value_type != node.output_type:
            raise TypeError("runtime value conflicts with program output type")
        memo[node.program_id] = value
        return value

    return execute(program)


@dataclass(frozen=True, slots=True)
class StrategicClaim:
    claim_id: str
    kind: ClaimKind
    text: str

    def __post_init__(self) -> None:
        _require_identity(self.claim_id, "claim_id")
        if self.kind not in {"external", "internal", "dynamic"}:
            raise ValueError(f"unsupported strategic claim kind: {self.kind}")
        _require_identity(self.text, "strategic claim text")


@dataclass(frozen=True, slots=True)
class ClaimDisposition:
    claim_id: str
    status: ClaimStatus
    evidence_ref: str

    def __post_init__(self) -> None:
        _require_identity(self.claim_id, "claim disposition claim_id")
        if self.status not in {"supported", "refuted", "unresolved"}:
            raise ValueError(f"unsupported claim status: {self.status}")
        _require_identity(self.evidence_ref, "claim disposition evidence_ref")


@dataclass(frozen=True, slots=True)
class CandidateEvaluation:
    program_id: str
    objective_values: tuple[float, ...]
    behavior_signature: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_identity(self.program_id, "evaluation program_id")
        if not self.objective_values:
            raise ValueError("candidate evaluation requires objective values")
        values = tuple(float(value) for value in self.objective_values)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("candidate objective values must be finite")
        if not self.behavior_signature:
            raise ValueError("candidate evaluation requires a behavior signature")
        for token in self.behavior_signature:
            _require_identity(token, "behavior signature token")
        refs = _stable_tuple(self.evidence_refs)
        if not refs:
            raise ValueError("candidate evaluation requires an evidence ref")
        object.__setattr__(self, "objective_values", values)
        object.__setattr__(self, "evidence_refs", refs)


@dataclass(frozen=True, slots=True)
class Neighborhood:
    neighborhood_id: str
    edges: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        _require_identity(self.neighborhood_id, "neighborhood_id")
        normalized: set[tuple[str, str]] = set()
        for left, right in self.edges:
            _require_identity(left, "neighborhood left program ID")
            _require_identity(right, "neighborhood right program ID")
            if left == right:
                raise ValueError("neighborhood edges cannot be self loops")
            normalized.add(tuple(sorted((left, right))))
        object.__setattr__(self, "edges", tuple(sorted(normalized)))


@dataclass(frozen=True, slots=True)
class RepresentationAudit:
    audit_id: str
    status: RepresentationStatus = "unassessed"
    residuals: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_identity(self.audit_id, "representation audit_id")
        if self.status not in {"unassessed", "residual", "passed"}:
            raise ValueError(f"unsupported representation status: {self.status}")
        residuals = _stable_tuple(self.residuals)
        evidence_refs = _stable_tuple(self.evidence_refs)
        if self.status == "residual" and not residuals:
            raise ValueError("a residual representation audit must name residuals")
        if self.status == "passed" and not evidence_refs:
            raise ValueError("a passed representation audit requires evidence")
        if self.status == "passed" and residuals:
            raise ValueError("a passed representation audit cannot retain residuals")
        object.__setattr__(self, "residuals", residuals)
        object.__setattr__(self, "evidence_refs", evidence_refs)


@dataclass(frozen=True, slots=True)
class FrontierScope:
    grammar_id: str
    grammar_version: str
    grammar_digest: str
    target_type: str
    max_depth: int
    max_programs: int
    evaluation_model_id: str
    landscape_mode: LandscapeMode
    evidence_epoch: str
    objective_names: tuple[str, ...]
    neighborhood_id: str
    scope_id: str = field(init=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.grammar_id, "scope grammar_id"),
            (self.grammar_version, "scope grammar_version"),
            (self.grammar_digest, "scope grammar_digest"),
            (self.target_type, "scope target_type"),
            (self.evaluation_model_id, "scope evaluation_model_id"),
            (self.evidence_epoch, "scope evidence_epoch"),
            (self.neighborhood_id, "scope neighborhood_id"),
        ):
            _require_identity(value, label)
        if self.landscape_mode not in {"fixed", "endogenous_transition"}:
            raise ValueError(f"unsupported landscape mode: {self.landscape_mode}")
        if self.max_depth < 0 or self.max_programs < 1:
            raise ValueError("scope enumeration bounds are invalid")
        objectives = tuple(self.objective_names)
        if not objectives or len(objectives) != len(set(objectives)):
            raise ValueError("scope objective names must be non-empty and unique")
        for objective in objectives:
            _require_identity(objective, "objective name")
        object.__setattr__(self, "objective_names", objectives)
        payload = {
            "schema": _SCOPE_SCHEMA,
            "grammar_id": self.grammar_id,
            "grammar_version": self.grammar_version,
            "grammar_digest": self.grammar_digest,
            "target_type": self.target_type,
            "max_depth": self.max_depth,
            "max_programs": self.max_programs,
            "evaluation_model_id": self.evaluation_model_id,
            "landscape_mode": self.landscape_mode,
            "evidence_epoch": self.evidence_epoch,
            "objective_names": list(self.objective_names),
            "neighborhood_id": self.neighborhood_id,
        }
        object.__setattr__(self, "scope_id", _digest(payload))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": _SCOPE_SCHEMA,
            "scope_id": self.scope_id,
            "grammar_id": self.grammar_id,
            "grammar_version": self.grammar_version,
            "grammar_digest": self.grammar_digest,
            "target_type": self.target_type,
            "max_depth": self.max_depth,
            "max_programs": self.max_programs,
            "evaluation_model_id": self.evaluation_model_id,
            "landscape_mode": self.landscape_mode,
            "evidence_epoch": self.evidence_epoch,
            "objective_names": list(self.objective_names),
            "neighborhood_id": self.neighborhood_id,
        }


@dataclass(frozen=True, slots=True)
class DominanceWitness:
    dominated_program_id: str
    dominator_program_id: str
    dominated_values: tuple[float, ...]
    dominator_values: tuple[float, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "dominated_program_id": self.dominated_program_id,
            "dominator_program_id": self.dominator_program_id,
            "dominated_values": list(self.dominated_values),
            "dominator_values": list(self.dominator_values),
        }


@dataclass(frozen=True, slots=True)
class InfeasibilityWitness:
    program_id: str
    refuted_claim_ids: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "program_id": self.program_id,
            "refuted_claim_ids": list(self.refuted_claim_ids),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class EquivalenceWitness:
    program_id: str
    representative_program_id: str
    behavior_signature: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "program_id": self.program_id,
            "representative_program_id": self.representative_program_id,
            "behavior_signature": list(self.behavior_signature),
        }


@dataclass(frozen=True, slots=True)
class ClosureResidual:
    kind: str
    detail: str
    program_id: str | None = None
    claim_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "detail": self.detail,
            "program_id": self.program_id,
            "claim_id": self.claim_id,
        }


@dataclass(frozen=True, slots=True)
class JaggedThoughtsFrontierCertificate:
    scope: FrontierScope
    enumeration_digest: str
    target_program_ids: tuple[str, ...]
    frontier_program_ids: tuple[str, ...]
    dominated: tuple[DominanceWitness, ...]
    infeasible: tuple[InfeasibilityWitness, ...]
    equivalent: tuple[EquivalenceWitness, ...]
    residual_program_ids: tuple[str, ...]
    residuals: tuple[ClosureResidual, ...]
    local_peak_program_ids: tuple[str, ...]
    representation_audit: RepresentationAudit
    scope_closed: bool
    decision_closed: bool
    certificate_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": _CERTIFICATE_SCHEMA,
            "certificate_sha256": self.certificate_sha256,
            "scope": self.scope.to_dict(),
            "enumeration_digest": self.enumeration_digest,
            "target_program_ids": list(self.target_program_ids),
            "frontier_program_ids": list(self.frontier_program_ids),
            "dominated": [witness.to_dict() for witness in self.dominated],
            "infeasible": [witness.to_dict() for witness in self.infeasible],
            "equivalent": [witness.to_dict() for witness in self.equivalent],
            "residual_program_ids": list(self.residual_program_ids),
            "residuals": [residual.to_dict() for residual in self.residuals],
            "local_peak_program_ids": list(self.local_peak_program_ids),
            "representation_audit": {
                "audit_id": self.representation_audit.audit_id,
                "status": self.representation_audit.status,
                "residuals": list(self.representation_audit.residuals),
                "evidence_refs": list(self.representation_audit.evidence_refs),
            },
            "scope_closed": self.scope_closed,
            "decision_closed": self.decision_closed,
        }


def _unique_by_id(items: Iterable[Any], attr: str, label: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for item in items:
        identity = getattr(item, attr)
        if identity in result:
            raise ValueError(f"duplicate {label}: {identity}")
        result[identity] = item
    return result


def _dominates(left: Sequence[float], right: Sequence[float]) -> bool:
    return all(a >= b for a, b in zip(left, right, strict=True)) and any(
        a > b for a, b in zip(left, right, strict=True)
    )


def _validate_scope(
    scope: FrontierScope,
    enumeration: EnumerationResult,
    neighborhood: Neighborhood,
) -> None:
    expected = (
        enumeration.grammar_id,
        enumeration.grammar_version,
        enumeration.grammar_digest,
        enumeration.max_depth,
        enumeration.max_programs,
    )
    actual = (
        scope.grammar_id,
        scope.grammar_version,
        scope.grammar_digest,
        scope.max_depth,
        scope.max_programs,
    )
    if actual != expected:
        raise ValueError("frontier scope does not match enumeration identity")
    if scope.neighborhood_id != neighborhood.neighborhood_id:
        raise ValueError("frontier scope does not match neighborhood identity")


def compile_jaggedthoughts_frontier(
    *,
    scope: FrontierScope,
    enumeration: EnumerationResult,
    claims: Iterable[StrategicClaim] = (),
    claim_dispositions: Iterable[ClaimDisposition] = (),
    evaluations: Iterable[CandidateEvaluation] = (),
    neighborhood: Neighborhood,
    representation_audit: RepresentationAudit,
) -> JaggedThoughtsFrontierCertificate:
    """Compile a witnessed jagged frontier for one frozen strategy scope."""
    _validate_scope(scope, enumeration, neighborhood)
    claim_by_id = _unique_by_id(claims, "claim_id", "strategic claim")
    disposition_by_id = _unique_by_id(
        claim_dispositions,
        "claim_id",
        "claim disposition",
    )
    evaluation_by_id = _unique_by_id(
        evaluations,
        "program_id",
        "candidate evaluation",
    )
    target_programs = tuple(sorted(
        enumeration.programs_of_type(scope.target_type),
        key=lambda program: program.program_id,
    ))
    target_ids = tuple(program.program_id for program in target_programs)
    target_id_set = set(target_ids)
    unknown_evaluations = set(evaluation_by_id) - target_id_set
    if unknown_evaluations:
        raise ValueError(
            "evaluations reference programs outside the target population: "
            f"{sorted(unknown_evaluations)}"
        )
    unknown_edges = {
        endpoint
        for edge in neighborhood.edges
        for endpoint in edge
        if endpoint not in target_id_set
    }
    if unknown_edges:
        raise ValueError(
            "neighborhood references programs outside the target population: "
            f"{sorted(unknown_edges)}"
        )

    residuals: list[ClosureResidual] = [
        ClosureResidual(
            kind=residual.kind,
            detail=residual.detail,
        )
        for residual in enumeration.residuals
    ]
    if not target_programs:
        residuals.append(ClosureResidual(
            kind="no_target_programs",
            detail=f"enumeration emitted no programs of type {scope.target_type}",
        ))

    infeasible: list[InfeasibilityWitness] = []
    residual_program_ids: set[str] = set()
    eligible: dict[str, CandidateEvaluation] = {}

    for program in target_programs:
        refuted_claim_ids: list[str] = []
        refuted_evidence_refs: list[str] = []
        program_has_residual = False
        for claim_id in compile_burden_of_proof(program):
            if claim_id not in claim_by_id:
                residuals.append(ClosureResidual(
                    kind="claim_definition_missing",
                    detail="program burden references an undefined claim",
                    program_id=program.program_id,
                    claim_id=claim_id,
                ))
                program_has_residual = True
                continue
            disposition = disposition_by_id.get(claim_id)
            if disposition is None:
                residuals.append(ClosureResidual(
                    kind="claim_disposition_missing",
                    detail="program burden has no evidence disposition",
                    program_id=program.program_id,
                    claim_id=claim_id,
                ))
                program_has_residual = True
            elif disposition.status == "unresolved":
                residuals.append(ClosureResidual(
                    kind="claim_unresolved",
                    detail="program burden remains unresolved",
                    program_id=program.program_id,
                    claim_id=claim_id,
                ))
                program_has_residual = True
            elif disposition.status == "refuted":
                refuted_claim_ids.append(claim_id)
                refuted_evidence_refs.append(disposition.evidence_ref)

        if refuted_claim_ids:
            infeasible.append(InfeasibilityWitness(
                program_id=program.program_id,
                refuted_claim_ids=tuple(sorted(refuted_claim_ids)),
                evidence_refs=tuple(sorted(set(refuted_evidence_refs))),
            ))
            continue
        evaluation = evaluation_by_id.get(program.program_id)
        if evaluation is None:
            residuals.append(ClosureResidual(
                kind="evaluation_missing",
                detail="target program has no candidate evaluation",
                program_id=program.program_id,
            ))
            program_has_residual = True
        elif len(evaluation.objective_values) != len(scope.objective_names):
            raise ValueError(
                "candidate objective arity does not match frontier scope"
            )
        if program_has_residual:
            residual_program_ids.add(program.program_id)
            continue
        if evaluation is None:  # narrowed by the branch above
            raise AssertionError("evaluation narrowing failed")
        eligible[program.program_id] = evaluation

    behavior_groups: dict[tuple[str, ...], list[str]] = defaultdict(list)
    for program_id, evaluation in eligible.items():
        behavior_groups[evaluation.behavior_signature].append(program_id)

    equivalent: list[EquivalenceWitness] = []
    representative_for: dict[str, str] = {}
    representatives: dict[str, CandidateEvaluation] = {}
    for signature in sorted(behavior_groups):
        program_ids = sorted(behavior_groups[signature])
        representative_id = program_ids[0]
        representative_evaluation = eligible[representative_id]
        for program_id in program_ids:
            evaluation = eligible[program_id]
            if evaluation.objective_values != representative_evaluation.objective_values:
                raise ValueError(
                    "one behavior signature maps to conflicting objective values"
                )
            representative_for[program_id] = representative_id
            if program_id != representative_id:
                equivalent.append(EquivalenceWitness(
                    program_id=program_id,
                    representative_program_id=representative_id,
                    behavior_signature=signature,
                ))
        representatives[representative_id] = representative_evaluation

    dominated: list[DominanceWitness] = []
    frontier_ids: list[str] = []
    for program_id in sorted(representatives):
        evaluation = representatives[program_id]
        dominators = [
            other_id
            for other_id, other_evaluation in representatives.items()
            if other_id != program_id
            and _dominates(
                other_evaluation.objective_values,
                evaluation.objective_values,
            )
        ]
        if not dominators:
            frontier_ids.append(program_id)
            continue
        dominator_id = sorted(dominators)[0]
        dominated.append(DominanceWitness(
            dominated_program_id=program_id,
            dominator_program_id=dominator_id,
            dominated_values=evaluation.objective_values,
            dominator_values=representatives[dominator_id].objective_values,
        ))

    neighbor_map: dict[str, set[str]] = defaultdict(set)
    for left, right in neighborhood.edges:
        if left not in representative_for or right not in representative_for:
            continue
        left_rep = representative_for[left]
        right_rep = representative_for[right]
        if left_rep == right_rep:
            continue
        neighbor_map[left_rep].add(right_rep)
        neighbor_map[right_rep].add(left_rep)

    local_peak_ids: list[str] = []
    for program_id in sorted(representatives):
        evaluation = representatives[program_id]
        has_better_neighbor = any(
            _dominates(
                representatives[neighbor_id].objective_values,
                evaluation.objective_values,
            )
            for neighbor_id in neighbor_map.get(program_id, set())
        )
        if not has_better_neighbor:
            local_peak_ids.append(program_id)

    partition_sets = (
        set(frontier_ids),
        {witness.dominated_program_id for witness in dominated},
        {witness.program_id for witness in infeasible},
        {witness.program_id for witness in equivalent},
        residual_program_ids,
    )
    union = set().union(*partition_sets)
    overlap_count = sum(len(partition) for partition in partition_sets) - len(union)
    if union != target_id_set or overlap_count:
        raise AssertionError(
            "frontier compiler failed to produce a disjoint target partition"
        )

    scope_closed = (
        enumeration.exhausted_within_scope
        and not enumeration.residuals
        and not residuals
        and not residual_program_ids
    )
    decision_closed = scope_closed and representation_audit.status == "passed"

    certificate_payload = {
        "schema": _CERTIFICATE_SCHEMA,
        "scope": scope.to_dict(),
        "enumeration_digest": enumeration.enumeration_digest,
        "target_program_ids": list(target_ids),
        "frontier_program_ids": sorted(frontier_ids),
        "dominated": [
            witness.to_dict()
            for witness in sorted(
                dominated,
                key=lambda item: item.dominated_program_id,
            )
        ],
        "infeasible": [
            witness.to_dict()
            for witness in sorted(
                infeasible,
                key=lambda item: item.program_id,
            )
        ],
        "equivalent": [
            witness.to_dict()
            for witness in sorted(
                equivalent,
                key=lambda item: item.program_id,
            )
        ],
        "residual_program_ids": sorted(residual_program_ids),
        "residuals": [
            residual.to_dict()
            for residual in sorted(
                residuals,
                key=lambda item: (
                    item.program_id or "",
                    item.claim_id or "",
                    item.kind,
                    item.detail,
                ),
            )
        ],
        "local_peak_program_ids": sorted(local_peak_ids),
        "representation_audit": {
            "audit_id": representation_audit.audit_id,
            "status": representation_audit.status,
            "residuals": list(representation_audit.residuals),
            "evidence_refs": list(representation_audit.evidence_refs),
        },
        "scope_closed": scope_closed,
        "decision_closed": decision_closed,
    }
    certificate_sha = _digest(certificate_payload)
    return JaggedThoughtsFrontierCertificate(
        scope=scope,
        enumeration_digest=enumeration.enumeration_digest,
        target_program_ids=target_ids,
        frontier_program_ids=tuple(sorted(frontier_ids)),
        dominated=tuple(sorted(
            dominated,
            key=lambda item: item.dominated_program_id,
        )),
        infeasible=tuple(sorted(
            infeasible,
            key=lambda item: item.program_id,
        )),
        equivalent=tuple(sorted(
            equivalent,
            key=lambda item: item.program_id,
        )),
        residual_program_ids=tuple(sorted(residual_program_ids)),
        residuals=tuple(sorted(
            residuals,
            key=lambda item: (
                item.program_id or "",
                item.claim_id or "",
                item.kind,
                item.detail,
            ),
        )),
        local_peak_program_ids=tuple(sorted(local_peak_ids)),
        representation_audit=representation_audit,
        scope_closed=scope_closed,
        decision_closed=decision_closed,
        certificate_sha256=certificate_sha,
    )
