"""Compile repeated action traces into guarded reusable generators.

The compiler operates one level above substrate observations.  Callers supply
ordered traces whose source, operation, effect, and successor identities are
opaque hashable values.  The common contract owns only:

* exact operation-word reconstruction;
* description-length admission of repeated words;
* witnessed effect/termination variants;
* explicit boundary side exits; and
* primitive fallback when an initiation guard is absent or conflicting.

It does not infer missing transitions, decide task success, or assign meaning
to an operation.  Predictive-state equality remains owned by the caller that
constructed the opaque source keys.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Hashable, Iterable

from ztare.common.equivariance import stable_sha256


def _stable(values: Iterable[Hashable]) -> tuple[Hashable, ...]:
    return tuple(sorted(values, key=lambda value: (stable_sha256(value), repr(value))))


@dataclass(frozen=True)
class GuardedTraceTransition:
    """One ordered, evidence-owned transition.

    ``successor`` may be absent only for a typed boundary.  Boundaries remain
    primitive trace tokens and stop candidate words; they are never compiled
    as successful effects.
    """

    source: Hashable
    operation: Hashable
    successor: Hashable | None
    effect: Hashable | None
    evidence_ref: str
    boundary_kind: str = ""

    def __post_init__(self) -> None:
        if not str(self.evidence_ref).strip():
            raise ValueError("guarded trace transitions require evidence_ref")
        if self.successor is None and not str(self.boundary_kind).strip():
            raise ValueError("missing successor requires boundary_kind")
        for name, value in (
            ("source", self.source),
            ("operation", self.operation),
        ):
            try:
                hash(value)
            except TypeError as exc:
                raise TypeError(f"{name} identity must be hashable") from exc
        if self.successor is not None:
            try:
                hash(self.successor)
            except TypeError as exc:
                raise TypeError("successor identity must be hashable") from exc
        if self.effect is not None:
            try:
                hash(self.effect)
            except TypeError as exc:
                raise TypeError("effect identity must be hashable") from exc

    def to_receipt(self) -> dict[str, Any]:
        return {
            "source_sha256": stable_sha256(self.source),
            "operation": repr(self.operation),
            "successor_sha256": (
                stable_sha256(self.successor)
                if self.successor is not None
                else None
            ),
            "effect_sha256": (
                stable_sha256(self.effect)
                if self.effect is not None
                else None
            ),
            "evidence_ref": self.evidence_ref,
            "boundary_kind": self.boundary_kind,
        }


@dataclass(frozen=True)
class GuardedActionTrace:
    """One ordered trace; typed boundaries may separate lifecycle segments."""

    trace_ref: str
    transitions: tuple[GuardedTraceTransition, ...]

    def __post_init__(self) -> None:
        if not str(self.trace_ref).strip():
            raise ValueError("guarded action traces require trace_ref")
        if not self.transitions:
            raise ValueError("guarded action traces require transitions")
        for prior, current in zip(self.transitions, self.transitions[1:]):
            if prior.boundary_kind:
                continue
            if prior.successor != current.source:
                raise ValueError(
                    "ordinary trace transitions must compose through exact "
                    "successor/source identity"
                )

    @property
    def operations(self) -> tuple[Hashable, ...]:
        return tuple(row.operation for row in self.transitions)

    @property
    def sha256(self) -> str:
        return stable_sha256({
            "schema": "ztare-guarded-action-trace-v1",
            "trace_ref": self.trace_ref,
            "transitions": [row.to_receipt() for row in self.transitions],
        })


@dataclass(frozen=True)
class SkillOccurrence:
    """One successful witnessed image of a retained operation word."""

    trace_ref: str
    start_index: int
    end_index: int
    initiation_key: Hashable
    termination_key: Hashable
    effect_trace: tuple[Hashable, ...]
    evidence_refs: tuple[str, ...]

    @property
    def occurrence_sha256(self) -> str:
        return stable_sha256({
            "trace_ref": self.trace_ref,
            "start_index": self.start_index,
            "end_index": self.end_index,
            "initiation_key": self.initiation_key,
            "termination_key": self.termination_key,
            "effect_trace": self.effect_trace,
            "evidence_refs": self.evidence_refs,
        })

    def to_receipt(self) -> dict[str, Any]:
        return {
            "occurrence_sha256": self.occurrence_sha256,
            "trace_ref": self.trace_ref,
            "start_index": self.start_index,
            "end_index": self.end_index,
            "initiation_sha256": stable_sha256(self.initiation_key),
            "termination_sha256": stable_sha256(self.termination_key),
            "effect_sha256s": [
                stable_sha256(effect) for effect in self.effect_trace
            ],
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True)
class SkillSideExit:
    """Earliest typed boundary encountered while matching a retained word."""

    trace_ref: str
    start_index: int
    failed_step: int
    initiation_key: Hashable
    source_key: Hashable
    attempted_operation: Hashable
    boundary_kind: str
    evidence_ref: str
    matched_prefix: tuple[Hashable, ...] = ()

    @property
    def side_exit_sha256(self) -> str:
        return stable_sha256({
            "trace_ref": self.trace_ref,
            "start_index": self.start_index,
            "failed_step": self.failed_step,
            "initiation_key": self.initiation_key,
            "source_key": self.source_key,
            "attempted_operation": self.attempted_operation,
            "boundary_kind": self.boundary_kind,
            "evidence_ref": self.evidence_ref,
            "matched_prefix": self.matched_prefix,
        })

    def to_receipt(self) -> dict[str, Any]:
        return {
            "side_exit_sha256": self.side_exit_sha256,
            "trace_ref": self.trace_ref,
            "start_index": self.start_index,
            "failed_step": self.failed_step,
            "initiation_sha256": stable_sha256(self.initiation_key),
            "source_sha256": stable_sha256(self.source_key),
            "attempted_operation": repr(self.attempted_operation),
            "boundary_kind": self.boundary_kind,
            "evidence_ref": self.evidence_ref,
            "matched_prefix": [
                repr(operation) for operation in self.matched_prefix
            ],
        }


@dataclass(frozen=True)
class SkillVariant:
    """One effect/termination image with its concrete initiation support."""

    effect_trace: tuple[Hashable, ...]
    termination_key: Hashable
    initiation_keys: tuple[Hashable, ...]
    occurrence_sha256s: tuple[str, ...]
    trace_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    @property
    def variant_sha256(self) -> str:
        return stable_sha256({
            "effect_trace": self.effect_trace,
            "termination_key": self.termination_key,
        })

    @property
    def support(self) -> int:
        return len(self.occurrence_sha256s)

    @property
    def independent_trace_support(self) -> int:
        return len(self.trace_refs)

    @property
    def distinct_initiation_support(self) -> int:
        """Number of exact initiation identities, independent of repeats."""
        return len({
            stable_sha256(key) for key in self.initiation_keys
        })

    @property
    def cross_initiation_exact_terminal_candidate(self) -> bool:
        """Whether one exact effect/terminal image varies the start identity.

        This is deliberately weaker than transferable-skill evidence: the
        compiler does not own task credit or held-out evaluation.  It prevents
        repeated traces from one exact state from masquerading as state
        variation.  Effect families that intentionally quotient terminal
        identity are owned by ``boundary_reachability``.
        """
        return (
            self.independent_trace_support >= 2
            and self.distinct_initiation_support >= 2
        )

    def to_receipt(self) -> dict[str, Any]:
        return {
            "variant_sha256": self.variant_sha256,
            "effect_sha256s": [
                stable_sha256(effect) for effect in self.effect_trace
            ],
            "termination_sha256": stable_sha256(self.termination_key),
            "initiation_sha256s": sorted(
                stable_sha256(key) for key in self.initiation_keys
            ),
            "support": self.support,
            "independent_trace_support": self.independent_trace_support,
            "distinct_initiation_support": self.distinct_initiation_support,
            "cross_initiation_exact_terminal_candidate": (
                self.cross_initiation_exact_terminal_candidate
            ),
            "occurrence_sha256s": list(self.occurrence_sha256s),
            "trace_refs": list(self.trace_refs),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True)
class SkillExecutionDecision:
    """Advisory compiled/fallback decision for one opaque initiation key."""

    status: str
    skill_sha256: str
    reason: str
    variant_sha256: str = ""
    operations: tuple[Hashable, ...] = ()

    def to_receipt(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "skill_sha256": self.skill_sha256,
            "reason": self.reason,
            "variant_sha256": self.variant_sha256,
            "operations": [repr(operation) for operation in self.operations],
        }


@dataclass(frozen=True)
class GuardedSkillProgram:
    """A description-length-admitted word with witnessed guards and exits."""

    operations: tuple[Hashable, ...]
    occurrences: tuple[SkillOccurrence, ...]
    encoding_occurrence_sha256s: tuple[str, ...]
    variants: tuple[SkillVariant, ...]
    side_exits: tuple[SkillSideExit, ...]
    admitted_initiation_keys: tuple[Hashable, ...]
    fallback_initiation_keys: tuple[Hashable, ...]
    definition_cost: int
    encoded_savings: int
    net_gain: int
    admission_authority: str = "local_mdl"

    def __post_init__(self) -> None:
        if self.admission_authority not in {
            "local_mdl",
            "validated_transport",
        }:
            raise ValueError(
                "skill admission authority must be local_mdl or "
                "validated_transport"
            )

    def structural_sha256(self, operation_namespace: str) -> str:
        """Stable skill-family identity, independent of evidence revision.

        ``skill_sha256`` remains the evidence-bound executable revision.  A
        continual learner needs a second identity that survives additional
        witnesses, guard refinements, and side exits.  The caller-owned
        operation namespace prevents identical-looking action words from
        different algebras from being silently identified.
        """
        namespace = str(operation_namespace).strip()
        if not namespace:
            raise ValueError("skill-family identity requires operation_namespace")
        return stable_sha256({
            "schema": "ztare-guarded-skill-family-v1",
            "operation_namespace": namespace,
            "operations": self.operations,
        })

    @property
    def skill_sha256(self) -> str:
        lineage_refs = sorted({
            ref
            for occurrence in self.occurrences
            for ref in occurrence.evidence_refs
        } | {
            side_exit.evidence_ref for side_exit in self.side_exits
        })
        return stable_sha256({
            "schema": "ztare-guarded-skill-program-v1",
            "operations": self.operations,
            "concrete_lineage": lineage_refs,
        })

    @property
    def cross_initiation_exact_terminal_variant_count(self) -> int:
        return sum(
            variant.cross_initiation_exact_terminal_candidate
            for variant in self.variants
        )

    @property
    def repeated_single_initiation_variant_count(self) -> int:
        return sum(
            variant.independent_trace_support >= 2
            and variant.distinct_initiation_support == 1
            for variant in self.variants
        )

    @property
    def max_distinct_initiation_support(self) -> int:
        return max(
            (
                variant.distinct_initiation_support
                for variant in self.variants
            ),
            default=0,
        )

    def decide(self, initiation_key: Hashable) -> SkillExecutionDecision:
        if initiation_key not in self.admitted_initiation_keys:
            reason = (
                "guard_conflict"
                if initiation_key in self.fallback_initiation_keys
                else "guard_unwitnessed"
            )
            return SkillExecutionDecision(
                status="primitive_fallback",
                skill_sha256=self.skill_sha256,
                reason=reason,
                operations=self.operations,
            )
        matching = [
            variant for variant in self.variants
            if initiation_key in variant.initiation_keys
        ]
        if len(matching) != 1:
            return SkillExecutionDecision(
                status="primitive_fallback",
                skill_sha256=self.skill_sha256,
                reason="variant_ambiguous",
                operations=self.operations,
            )
        return SkillExecutionDecision(
            status="compiled",
            skill_sha256=self.skill_sha256,
            reason="witnessed_guard",
            variant_sha256=matching[0].variant_sha256,
            operations=self.operations,
        )

    def to_receipt(self) -> dict[str, Any]:
        return {
            "schema": "ztare-guarded-skill-program-v1",
            "skill_sha256": self.skill_sha256,
            "operations": [repr(operation) for operation in self.operations],
            "operation_count": len(self.operations),
            "occurrence_count": len(self.occurrences),
            "encoding_occurrence_count": len(
                self.encoding_occurrence_sha256s
            ),
            "encoding_occurrence_sha256s": list(
                self.encoding_occurrence_sha256s
            ),
            "variants": [
                variant.to_receipt() for variant in self.variants
            ],
            "cross_initiation_exact_terminal_variant_count": (
                self.cross_initiation_exact_terminal_variant_count
            ),
            "repeated_single_initiation_variant_count": (
                self.repeated_single_initiation_variant_count
            ),
            "max_distinct_initiation_support": (
                self.max_distinct_initiation_support
            ),
            "side_exits": [
                side_exit.to_receipt() for side_exit in self.side_exits
            ],
            "admitted_initiation_sha256s": sorted(
                stable_sha256(key)
                for key in self.admitted_initiation_keys
            ),
            "fallback_initiation_sha256s": sorted(
                stable_sha256(key)
                for key in self.fallback_initiation_keys
            ),
            "definition_cost": self.definition_cost,
            "encoded_savings": self.encoded_savings,
            "net_gain": self.net_gain,
            "admission_authority": self.admission_authority,
        }


@dataclass(frozen=True)
class GuardedSkillLibrary:
    """A losslessly encoded trace corpus plus its retained generators."""

    source_sha256: str
    programs: tuple[GuardedSkillProgram, ...]
    primitive_token_count: int
    encoded_token_count: int
    dictionary_token_count: int
    reconstructed_operations_by_trace: tuple[
        tuple[str, tuple[Hashable, ...]],
        ...
    ]
    source_operations_by_trace: tuple[
        tuple[str, tuple[Hashable, ...]],
        ...
    ]
    schema: str = "ztare-guarded-skill-library-v1"

    @property
    def description_length(self) -> int:
        return self.encoded_token_count + self.dictionary_token_count

    @property
    def compression_gain(self) -> int:
        return self.primitive_token_count - self.description_length

    @property
    def exact_reconstruction(self) -> bool:
        return (
            self.reconstructed_operations_by_trace
            == self.source_operations_by_trace
        )

    @property
    def cross_initiation_exact_terminal_variant_count(self) -> int:
        return sum(
            program.cross_initiation_exact_terminal_variant_count
            for program in self.programs
        )

    @property
    def repeated_single_initiation_variant_count(self) -> int:
        return sum(
            program.repeated_single_initiation_variant_count
            for program in self.programs
        )

    @property
    def max_distinct_initiation_support(self) -> int:
        return max(
            (
                program.max_distinct_initiation_support
                for program in self.programs
            ),
            default=0,
        )

    def to_receipt(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "source_sha256": self.source_sha256,
            "program_count": len(self.programs),
            "programs": [program.to_receipt() for program in self.programs],
            "cross_initiation_exact_terminal_variant_count": (
                self.cross_initiation_exact_terminal_variant_count
            ),
            "repeated_single_initiation_variant_count": (
                self.repeated_single_initiation_variant_count
            ),
            "max_distinct_initiation_support": (
                self.max_distinct_initiation_support
            ),
            "primitive_token_count": self.primitive_token_count,
            "encoded_token_count": self.encoded_token_count,
            "dictionary_token_count": self.dictionary_token_count,
            "description_length": self.description_length,
            "compression_gain": self.compression_gain,
            "exact_reconstruction": self.exact_reconstruction,
            "trace_count": len(self.source_operations_by_trace),
        }


@dataclass(frozen=True)
class GuardedPlanToken:
    """One primitive or compiled token in a lossless execution plan."""

    kind: str
    operations: tuple[Hashable, ...]
    skill_sha256: str = ""

    def __post_init__(self) -> None:
        if self.kind not in {"primitive", "skill"}:
            raise ValueError("guarded plan token kind must be primitive or skill")
        if not self.operations:
            raise ValueError("guarded plan tokens require operations")
        if self.kind == "primitive" and len(self.operations) != 1:
            raise ValueError("primitive plan tokens contain one operation")
        if self.kind == "skill" and not self.skill_sha256:
            raise ValueError("skill plan tokens require skill_sha256")

    @property
    def token_sha256(self) -> str:
        return stable_sha256({
            "kind": self.kind,
            "operations": self.operations,
            "skill_sha256": self.skill_sha256,
        })

    def to_receipt(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "operations": [repr(operation) for operation in self.operations],
            "operation_count": len(self.operations),
            "skill_sha256": self.skill_sha256,
            "token_sha256": self.token_sha256,
        }


@dataclass(frozen=True)
class GuardedExecutionPlan:
    """Lossless tokenization of one witnessed primitive operation request."""

    status: str
    primitive_operations: tuple[Hashable, ...]
    tokens: tuple[GuardedPlanToken, ...] = ()
    final_key: Hashable | None = None
    failed_operation_index: int | None = None
    schema: str = "ztare-guarded-execution-plan-v1"

    @property
    def expanded_operations(self) -> tuple[Hashable, ...]:
        return tuple(
            operation
            for token in self.tokens
            for operation in token.operations
        )

    @property
    def exact_expansion(self) -> bool:
        return self.expanded_operations == self.primitive_operations

    @property
    def skill_token_count(self) -> int:
        return sum(token.kind == "skill" for token in self.tokens)

    @property
    def token_savings(self) -> int:
        return len(self.primitive_operations) - len(self.tokens)

    def to_receipt(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "status": self.status,
            "primitive_operations": [
                repr(operation) for operation in self.primitive_operations
            ],
            "primitive_operation_count": len(self.primitive_operations),
            "tokens": [token.to_receipt() for token in self.tokens],
            "token_count": len(self.tokens),
            "skill_token_count": self.skill_token_count,
            "token_savings": self.token_savings,
            "exact_expansion": self.exact_expansion,
            "final_key_sha256": (
                stable_sha256(self.final_key)
                if self.final_key is not None
                else None
            ),
            "failed_operation_index": self.failed_operation_index,
        }


def _plan_rank(tokens: tuple[GuardedPlanToken, ...]) -> tuple[Any, ...]:
    skill_coverage = sum(
        len(token.operations)
        for token in tokens
        if token.kind == "skill"
    )
    return (
        len(tokens),
        -skill_coverage,
        tuple(token.token_sha256 for token in tokens),
    )


def compile_guarded_execution_plan(
    library: GuardedSkillLibrary,
    *,
    start_key: Hashable,
    operations: Iterable[Hashable],
    transition: Callable[[Hashable, Hashable], Hashable | None],
    allowed_skill_sha256s: frozenset[str] | None = None,
    allowed_skill_invocations: frozenset[tuple[str, str]] | None = None,
    additional_programs: Iterable[GuardedSkillProgram] = (),
) -> GuardedExecutionPlan:
    """Losslessly tokenize one witnessed primitive route.

    The primitive reference path is computed first.  A skill may replace a
    suffix only when its initiation guard is admitted and replaying every
    operation through ``transition`` yields the identical reference prefixes.
    An undefined or boundary relation fails before tokenization.
    """
    requested = tuple(operations)
    states = [start_key]
    for index, operation in enumerate(requested):
        successor = transition(states[-1], operation)
        if successor is None:
            return GuardedExecutionPlan(
                status="primitive_route_undefined",
                primitive_operations=requested,
                final_key=states[-1],
                failed_operation_index=index,
            )
        try:
            hash(successor)
        except TypeError as exc:
            raise TypeError(
                "guarded plan transition returned an unhashable state"
            ) from exc
        states.append(successor)

    best: dict[int, tuple[GuardedPlanToken, ...]] = {0: ()}
    program_by_revision: dict[str, GuardedSkillProgram] = {}
    for program in (*library.programs, *tuple(additional_programs)):
        prior = program_by_revision.get(program.skill_sha256)
        if prior is not None and prior != program:
            raise ValueError("skill revision identity collision")
        program_by_revision[program.skill_sha256] = program
    programs = tuple(sorted(
        (
            program
            for program in program_by_revision.values()
            if (
                allowed_skill_sha256s is None
                or program.skill_sha256 in allowed_skill_sha256s
            )
        ),
        key=lambda program: program.skill_sha256,
    ))
    for index in range(len(requested)):
        if index not in best:
            continue
        prefix = best[index]
        primitive = GuardedPlanToken(
            kind="primitive",
            operations=(requested[index],),
        )
        primitive_candidate = (*prefix, primitive)
        prior = best.get(index + 1)
        if prior is None or _plan_rank(primitive_candidate) < _plan_rank(prior):
            best[index + 1] = primitive_candidate

        for program in programs:
            length = len(program.operations)
            end = index + length
            if end > len(requested):
                continue
            if requested[index:end] != program.operations:
                continue
            if (
                allowed_skill_invocations is not None
                and (
                    program.skill_sha256,
                    stable_sha256(states[index]),
                )
                not in allowed_skill_invocations
            ):
                continue
            decision = program.decide(states[index])
            if decision.status != "compiled":
                continue
            cursor = states[index]
            commutes = True
            for offset, operation in enumerate(program.operations, start=1):
                cursor = transition(cursor, operation)
                if cursor is None or cursor != states[index + offset]:
                    commutes = False
                    break
            if not commutes:
                continue
            token = GuardedPlanToken(
                kind="skill",
                operations=program.operations,
                skill_sha256=program.skill_sha256,
            )
            candidate = (*prefix, token)
            prior = best.get(end)
            if prior is None or _plan_rank(candidate) < _plan_rank(prior):
                best[end] = candidate

    tokens = best.get(len(requested), ())
    status = (
        "compiled_plan"
        if any(token.kind == "skill" for token in tokens)
        else "primitive_plan"
    )
    plan = GuardedExecutionPlan(
        status=status,
        primitive_operations=requested,
        tokens=tokens,
        final_key=states[-1],
    )
    if not plan.exact_expansion:
        raise RuntimeError("guarded execution plan failed exact expansion")
    return plan


def _canonical_traces(
    traces: Iterable[GuardedActionTrace],
) -> tuple[GuardedActionTrace, ...]:
    rows = tuple(traces)
    refs = [trace.trace_ref for trace in rows]
    if len(set(refs)) != len(refs):
        raise ValueError("guarded action trace refs must be unique")
    return tuple(sorted(
        rows,
        key=lambda trace: (trace.sha256, trace.trace_ref),
    ))


def _ordinary_windows(
    trace: GuardedActionTrace,
) -> tuple[tuple[int, int], ...]:
    windows = []
    start = 0
    for index, transition in enumerate(trace.transitions):
        if not transition.boundary_kind:
            continue
        if start < index:
            windows.append((start, index))
        start = index + 1
    if start < len(trace.transitions):
        windows.append((start, len(trace.transitions)))
    return tuple(windows)


def _successful_occurrences(
    traces: tuple[GuardedActionTrace, ...],
    word: tuple[Hashable, ...],
) -> tuple[SkillOccurrence, ...]:
    length = len(word)
    rows = []
    for trace in traces:
        for start, end in _ordinary_windows(trace):
            for index in range(start, end - length + 1):
                segment = trace.transitions[index:index + length]
                if tuple(row.operation for row in segment) != word:
                    continue
                termination = segment[-1].successor
                if termination is None:  # ordinary-window invariant
                    continue
                rows.append(SkillOccurrence(
                    trace_ref=trace.trace_ref,
                    start_index=index,
                    end_index=index + length,
                    initiation_key=segment[0].source,
                    termination_key=termination,
                    effect_trace=tuple(row.effect for row in segment),
                    evidence_refs=tuple(row.evidence_ref for row in segment),
                ))
    return tuple(sorted(
        rows,
        key=lambda row: (
            row.occurrence_sha256,
            row.trace_ref,
            row.start_index,
        ),
    ))


def _side_exits(
    traces: tuple[GuardedActionTrace, ...],
    word: tuple[Hashable, ...],
) -> tuple[SkillSideExit, ...]:
    rows = []
    for trace in traces:
        for start in range(len(trace.transitions)):
            matched: list[Hashable] = []
            initiation = trace.transitions[start].source
            for offset, expected in enumerate(word):
                index = start + offset
                if index >= len(trace.transitions):
                    break
                transition = trace.transitions[index]
                if transition.operation != expected:
                    break
                if transition.boundary_kind:
                    rows.append(SkillSideExit(
                        trace_ref=trace.trace_ref,
                        start_index=start,
                        failed_step=offset,
                        initiation_key=initiation,
                        source_key=transition.source,
                        attempted_operation=expected,
                        boundary_kind=transition.boundary_kind,
                        evidence_ref=transition.evidence_ref,
                        matched_prefix=tuple(matched),
                    ))
                    break
                matched.append(expected)
    unique = {
        row.side_exit_sha256: row for row in rows
    }
    return tuple(sorted(
        unique.values(),
        key=lambda row: (
            row.side_exit_sha256,
            row.trace_ref,
            row.start_index,
        ),
    ))


def _variants(
    occurrences: tuple[SkillOccurrence, ...],
) -> tuple[SkillVariant, ...]:
    grouped: dict[
        tuple[tuple[Hashable, ...], Hashable],
        list[SkillOccurrence],
    ] = defaultdict(list)
    for occurrence in occurrences:
        grouped[
            occurrence.effect_trace,
            occurrence.termination_key,
        ].append(occurrence)
    variants = []
    for (effects, termination), rows in grouped.items():
        variants.append(SkillVariant(
            effect_trace=effects,
            termination_key=termination,
            initiation_keys=_stable(
                row.initiation_key for row in rows
            ),
            occurrence_sha256s=tuple(sorted(
                row.occurrence_sha256 for row in rows
            )),
            trace_refs=tuple(sorted({
                row.trace_ref for row in rows
            })),
            evidence_refs=tuple(sorted({
                ref for row in rows for ref in row.evidence_refs
            })),
        ))
    return tuple(sorted(
        variants,
        key=lambda variant: variant.variant_sha256,
    ))


def _admission_sets(
    variants: tuple[SkillVariant, ...],
    side_exits: tuple[SkillSideExit, ...],
    *,
    min_variant_support: int,
) -> tuple[tuple[Hashable, ...], tuple[Hashable, ...]]:
    variants_by_start: dict[Hashable, set[str]] = defaultdict(set)
    support_by_variant = {
        variant.variant_sha256: variant.independent_trace_support
        for variant in variants
    }
    for variant in variants:
        for key in variant.initiation_keys:
            variants_by_start[key].add(variant.variant_sha256)
    side_exit_starts = {
        side_exit.initiation_key for side_exit in side_exits
    }
    admitted = []
    fallback = []
    for key, variant_ids in variants_by_start.items():
        supported = (
            len(variant_ids) == 1
            and support_by_variant[next(iter(variant_ids))]
            >= min_variant_support
        )
        if supported and key not in side_exit_starts:
            admitted.append(key)
        else:
            fallback.append(key)
    fallback.extend(
        key for key in side_exit_starts
        if key not in variants_by_start
    )
    return _stable(admitted), _stable(set(fallback))


def _candidate_words(
    traces: tuple[GuardedActionTrace, ...],
    *,
    min_word_length: int,
    max_word_length: int,
) -> tuple[tuple[Hashable, ...], ...]:
    words: set[tuple[Hashable, ...]] = set()
    for trace in traces:
        for start, end in _ordinary_windows(trace):
            operations = tuple(
                row.operation for row in trace.transitions[start:end]
            )
            for length in range(
                min_word_length,
                min(max_word_length, len(operations)) + 1,
            ):
                for index in range(len(operations) - length + 1):
                    words.add(operations[index:index + length])
    return tuple(sorted(
        words,
        key=lambda word: (
            stable_sha256(word),
            tuple(map(repr, word)),
        ),
    ))


def _encoding_occurrences(
    occurrences: tuple[SkillOccurrence, ...],
    *,
    admitted_starts: tuple[Hashable, ...],
    occupied: dict[str, set[int]],
) -> tuple[SkillOccurrence, ...]:
    admitted = frozenset(admitted_starts)
    local_occupied = {
        trace_ref: set(positions)
        for trace_ref, positions in occupied.items()
    }
    selected = []
    for occurrence in sorted(
        occurrences,
        key=lambda row: (
            row.trace_ref,
            row.start_index,
            row.occurrence_sha256,
        ),
    ):
        if occurrence.initiation_key not in admitted:
            continue
        positions = set(range(
            occurrence.start_index,
            occurrence.end_index,
        ))
        trace_occupied = local_occupied.setdefault(
            occurrence.trace_ref,
            set(),
        )
        if positions & trace_occupied:
            continue
        selected.append(occurrence)
        trace_occupied.update(positions)
    return tuple(selected)


def _program_candidate(
    traces: tuple[GuardedActionTrace, ...],
    word: tuple[Hashable, ...],
    *,
    occupied: dict[str, set[int]],
    min_variant_support: int,
) -> tuple[
    int,
    tuple[SkillOccurrence, ...],
    tuple[SkillOccurrence, ...],
    tuple[SkillVariant, ...],
    tuple[SkillSideExit, ...],
    tuple[Hashable, ...],
    tuple[Hashable, ...],
]:
    occurrences = _successful_occurrences(traces, word)
    exits = _side_exits(traces, word)
    variants = _variants(occurrences)
    admitted, fallback = _admission_sets(
        variants,
        exits,
        min_variant_support=min_variant_support,
    )
    encoding = _encoding_occurrences(
        occurrences,
        admitted_starts=admitted,
        occupied=occupied,
    )
    definition_cost = len(word)
    encoded_savings = len(encoding) * (len(word) - 1)
    gain = encoded_savings - definition_cost
    return (
        gain,
        occurrences,
        encoding,
        variants,
        exits,
        admitted,
        fallback,
    )


def _encode_traces(
    traces: tuple[GuardedActionTrace, ...],
    programs: tuple[GuardedSkillProgram, ...],
) -> tuple[
    tuple[tuple[str, tuple[tuple[str, Any], ...]], ...],
    tuple[tuple[str, tuple[Hashable, ...]], ...],
]:
    occurrence_owner = {}
    occurrence_start = {}
    for program in programs:
        for digest in program.encoding_occurrence_sha256s:
            occurrence_owner[digest] = program
        for occurrence in program.occurrences:
            if occurrence.occurrence_sha256 in occurrence_owner:
                occurrence_start[
                    occurrence.trace_ref,
                    occurrence.start_index,
                ] = occurrence
    encoded = []
    reconstructed = []
    for trace in sorted(traces, key=lambda row: row.trace_ref):
        tokens = []
        operations = []
        index = 0
        while index < len(trace.transitions):
            occurrence = occurrence_start.get((trace.trace_ref, index))
            if occurrence is None:
                operation = trace.transitions[index].operation
                tokens.append(("primitive", operation))
                operations.append(operation)
                index += 1
                continue
            program = occurrence_owner[occurrence.occurrence_sha256]
            tokens.append(("skill", program.skill_sha256))
            operations.extend(program.operations)
            index = occurrence.end_index
        encoded.append((trace.trace_ref, tuple(tokens)))
        reconstructed.append((trace.trace_ref, tuple(operations)))
    return tuple(encoded), tuple(reconstructed)


def compile_guarded_skill_library(
    traces: Iterable[GuardedActionTrace],
    *,
    min_word_length: int = 2,
    max_word_length: int = 8,
    min_variant_support: int = 2,
) -> GuardedSkillLibrary:
    """Compile a lossless, guarded, description-length-improving library.

    Candidate words are drawn only from ordinary witnessed segments.
    Selection is deterministic greedy MDL: a word is retained only when the
    primitive tokens saved by non-overlapping admitted occurrences exceed its
    dictionary definition cost.  Boundary attempts contribute side exits and
    can revoke an initiation guard, but never become successful occurrences.
    """
    if min_word_length < 2:
        raise ValueError("min_word_length must be at least two")
    if max_word_length < min_word_length:
        raise ValueError("max_word_length must cover min_word_length")
    if min_variant_support < 1:
        raise ValueError("min_variant_support must be positive")
    trace_rows = _canonical_traces(traces)
    words = _candidate_words(
        trace_rows,
        min_word_length=min_word_length,
        max_word_length=max_word_length,
    )
    occupied: dict[str, set[int]] = defaultdict(set)
    programs = []
    remaining = set(words)
    while remaining:
        candidates = []
        for word in remaining:
            candidate = _program_candidate(
                trace_rows,
                word,
                occupied=occupied,
                min_variant_support=min_variant_support,
            )
            gain, _all, encoding, *_rest = candidate
            candidates.append((
                -gain,
                -len(encoding) * len(word),
                -len(word),
                stable_sha256(word),
                tuple(map(repr, word)),
                word,
                candidate,
            ))
        (
            negative_gain,
            _negative_coverage,
            _negative_length,
            _word_digest,
            _word_repr,
            word,
            candidate,
        ) = min(candidates)
        gain = -negative_gain
        if gain <= 0:
            break
        (
            _gain,
            occurrences,
            encoding,
            variants,
            exits,
            admitted,
            fallback,
        ) = candidate
        program = GuardedSkillProgram(
            operations=word,
            occurrences=occurrences,
            encoding_occurrence_sha256s=tuple(sorted(
                row.occurrence_sha256 for row in encoding
            )),
            variants=variants,
            side_exits=exits,
            admitted_initiation_keys=admitted,
            fallback_initiation_keys=fallback,
            definition_cost=len(word),
            encoded_savings=len(encoding) * (len(word) - 1),
            net_gain=gain,
        )
        programs.append(program)
        for occurrence in encoding:
            occupied[occurrence.trace_ref].update(range(
                occurrence.start_index,
                occurrence.end_index,
            ))
        remaining.remove(word)
    program_rows = tuple(sorted(
        programs,
        key=lambda program: program.skill_sha256,
    ))
    encoded, reconstructed = _encode_traces(trace_rows, program_rows)
    source_operations = tuple(sorted(
        (
            (trace.trace_ref, trace.operations)
            for trace in trace_rows
        ),
        key=lambda row: row[0],
    ))
    encoded_count = sum(
        len(tokens) for _trace_ref, tokens in encoded
    )
    dictionary_count = sum(
        program.definition_cost for program in program_rows
    )
    primitive_count = sum(
        len(operations) for _trace_ref, operations in source_operations
    )
    source_sha = stable_sha256({
        "schema": "ztare-guarded-skill-source-v1",
        "traces": [trace.sha256 for trace in trace_rows],
        "min_word_length": min_word_length,
        "max_word_length": max_word_length,
        "min_variant_support": min_variant_support,
    })
    library = GuardedSkillLibrary(
        source_sha256=source_sha,
        programs=program_rows,
        primitive_token_count=primitive_count,
        encoded_token_count=encoded_count,
        dictionary_token_count=dictionary_count,
        reconstructed_operations_by_trace=tuple(sorted(
            reconstructed,
            key=lambda row: row[0],
        )),
        source_operations_by_trace=source_operations,
    )
    if not library.exact_reconstruction:
        raise RuntimeError("guarded skill compiler failed exact reconstruction")
    if library.compression_gain != sum(
        program.net_gain for program in library.programs
    ):
        raise RuntimeError("guarded skill compiler gain accounting drifted")
    return library
