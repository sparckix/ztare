"""Declarative YAML/JSON profiles for the JaggedThoughts kernel.

Profiles contain substrate vocabulary and evidence. The kernel keeps control
of type checking, recursive enumeration, program identity, neighborhood
materialization, frontier partitioning, and closure. Factor-graph profiles
evaluate every enumerated program automatically; table profiles remain
available for externally computed models.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from ztare.common.content_identity import content_sha256

from .evidence import StrategyEvidenceManifest, compile_evidence_manifest
from .evaluation import (
    FactorEvaluationModel,
    StrategicFactor,
    StrategicScenario,
    compile_factor_evaluations,
)
from .exploration import build_exploration_agenda
from .jaggedthoughts import (
    CandidateEvaluation,
    ClaimDisposition,
    EnumerationResult,
    FrontierScope,
    JaggedThoughtsFrontierCertificate,
    Neighborhood,
    OperatorGrammar,
    Program,
    RepresentationAudit,
    StrategicClaim,
    TypedOperator,
    TypedTerminal,
    compile_jaggedthoughts_frontier,
    enumerate_typed_programs,
)


PROFILE_SCHEMA = "jaggedthoughts-profile-v1"


class JaggedThoughtsProfileError(ValueError):
    """Raised when a declarative strategy profile is malformed or ambiguous."""


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise JaggedThoughtsProfileError(f"{label} must be a mapping")
    return value


def _rows(value: Any, label: str) -> tuple[Mapping[str, Any], ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise JaggedThoughtsProfileError(f"{label} must be a list")
    return tuple(_mapping(row, f"{label} row") for row in value)


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise JaggedThoughtsProfileError(f"{label} must be a non-empty string")
    return value.strip()


def _texts(value: Any, label: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise JaggedThoughtsProfileError(f"{label} must be a list of strings")
    return tuple(_text(item, f"{label} item") for item in value)


def _numbers(value: Any, label: str) -> tuple[float, ...]:
    if not isinstance(value, list) or not value:
        raise JaggedThoughtsProfileError(
            f"{label} must be a non-empty numeric list"
        )
    if any(isinstance(item, bool) for item in value):
        raise JaggedThoughtsProfileError(f"{label} must be numeric")
    try:
        return tuple(float(item) for item in value)
    except (TypeError, ValueError) as error:
        raise JaggedThoughtsProfileError(f"{label} must be numeric") from error


def _number_rows(value: Any, label: str) -> tuple[tuple[float, ...], ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise JaggedThoughtsProfileError(f"{label} must be a list")
    return tuple(
        _numbers(row, f"{label} row")
        for row in value
    )


def program_terminal_ids(program: Program) -> tuple[str, ...]:
    """Return terminal IDs in ordered derivation traversal."""
    if program.terminal_id is not None:
        return (program.terminal_id,)
    return tuple(
        terminal_id
        for child in program.children
        for terminal_id in program_terminal_ids(child)
    )


@dataclass(frozen=True, slots=True)
class CompiledJaggedThoughtsProfile:
    profile_id: str
    title: str
    decision_question: str
    owner: str
    as_of: str
    grammar: OperatorGrammar
    enumeration: EnumerationResult
    neighborhood: Neighborhood
    claims: tuple[StrategicClaim, ...]
    claim_dispositions: tuple[ClaimDisposition, ...]
    evidence_manifest: StrategyEvidenceManifest
    evaluation_kind: str
    evaluation_model: FactorEvaluationModel | None
    evaluations: tuple[CandidateEvaluation, ...]
    certificate: JaggedThoughtsFrontierCertificate

    def summary(self) -> dict[str, Any]:
        agenda = build_exploration_agenda(self)
        return {
            "profile_id": self.profile_id,
            "title": self.title,
            "decision_question": self.decision_question,
            "owner": self.owner,
            "as_of": self.as_of,
            "grammar_digest": self.grammar.grammar_digest,
            "enumeration_digest": self.enumeration.enumeration_digest,
            "certificate_sha256": self.certificate.certificate_sha256,
            "target_program_count": len(self.certificate.target_program_ids),
            "frontier_count": len(self.certificate.frontier_program_ids),
            "local_peak_count": len(self.certificate.local_peak_program_ids),
            "residual_program_count": len(self.certificate.residual_program_ids),
            "scope_closed": self.certificate.scope_closed,
            "decision_closed": self.certificate.decision_closed,
            "representation_status": self.certificate.representation_audit.status,
            "source_count": len(self.evidence_manifest.sources),
            "bound_evidence_count": len(self.evidence_manifest.evidence),
            "evaluation_kind": self.evaluation_kind,
            "exploration_probe_count": len(agenda.probes),
            "pivotal_probe_count": agenda.pivotal_probe_count,
        }

    def to_dict(self) -> dict[str, Any]:
        evaluation_model = (
            self.evaluation_model.to_dict()
            if self.evaluation_model is not None
            else None
        )
        return {
            "schema": PROFILE_SCHEMA,
            "summary": self.summary(),
            "decision": {
                "title": self.title,
                "question": self.decision_question,
                "owner": self.owner,
                "as_of": self.as_of,
            },
            "grammar": self.grammar.to_dict(),
            "evidence_manifest": self.evidence_manifest.to_dict(),
            "evaluation": {
                "kind": self.evaluation_kind,
                "model": evaluation_model,
                "candidates": [
                    {
                        "program_id": evaluation.program_id,
                        "objective_values": list(evaluation.objective_values),
                        "behavior_signature": list(
                            evaluation.behavior_signature
                        ),
                        "evidence_refs": list(evaluation.evidence_refs),
                    }
                    for evaluation in self.evaluations
                ],
            },
            "exploration_agenda": build_exploration_agenda(self).to_dict(),
            "enumeration": self.enumeration.to_dict(),
            "certificate": self.certificate.to_dict(),
        }


def _parse_claims(profile: Mapping[str, Any]) -> tuple[StrategicClaim, ...]:
    return tuple(
        StrategicClaim(
            claim_id=_text(row.get("id"), "claim.id"),
            kind=_text(row.get("kind"), "claim.kind"),  # type: ignore[arg-type]
            text=_text(row.get("text"), "claim.text"),
        )
        for row in _rows(profile.get("claims"), "claims")
    )


def _parse_grammar(profile: Mapping[str, Any]) -> tuple[
    OperatorGrammar,
    str,
    int,
    int,
]:
    raw = _mapping(profile.get("grammar"), "grammar")
    terminals = tuple(
        TypedTerminal(
            terminal_id=_text(row.get("id"), "terminal.id"),
            output_type=_text(row.get("type"), "terminal.type"),
            claim_ids=_texts(row.get("claims"), "terminal.claims"),
            description=str(row.get("description", "")),
        )
        for row in _rows(raw.get("terminals"), "grammar.terminals")
    )
    operators = tuple(
        TypedOperator(
            operator_id=_text(row.get("id"), "operator.id"),
            input_types=_texts(row.get("inputs"), "operator.inputs"),
            output_type=_text(row.get("output"), "operator.output"),
            claim_ids=_texts(row.get("claims"), "operator.claims"),
            commutative=bool(row.get("commutative", False)),
            description=str(row.get("description", "")),
        )
        for row in _rows(raw.get("operators"), "grammar.operators")
    )
    target_type = _text(raw.get("target_type"), "grammar.target_type")
    max_depth = raw.get("max_depth")
    max_programs = raw.get("max_programs")
    if not isinstance(max_depth, int) or max_depth < 0:
        raise JaggedThoughtsProfileError("grammar.max_depth must be non-negative")
    if not isinstance(max_programs, int) or max_programs < 1:
        raise JaggedThoughtsProfileError("grammar.max_programs must be positive")
    return (
        OperatorGrammar(
            grammar_id=_text(raw.get("id"), "grammar.id"),
            version=_text(raw.get("version"), "grammar.version"),
            terminals=terminals,
            operators=operators,
        ),
        target_type,
        max_depth,
        max_programs,
    )


def _selector_match(program: Program, selector: Mapping[str, Any]) -> bool:
    root = selector.get("root_operator")
    if root is not None and program.operator_id != _text(
        root,
        "evaluation.selector.root_operator",
    ):
        return False
    depth = selector.get("depth")
    if depth is not None:
        if not isinstance(depth, int) or depth < 0:
            raise JaggedThoughtsProfileError(
                "evaluation.selector.depth must be non-negative"
            )
        if program.depth != depth:
            return False
    terminals = _texts(
        selector.get("terminals"),
        "evaluation.selector.terminals",
    )
    return not terminals or program_terminal_ids(program) == terminals


def _resolve_selector(
    selector: Mapping[str, Any],
    target_programs: Sequence[Program],
    label: str,
) -> Program:
    matches = [
        program for program in target_programs if _selector_match(program, selector)
    ]
    if len(matches) != 1:
        raise JaggedThoughtsProfileError(
            f"{label} matched {len(matches)} target programs; expected exactly one"
        )
    return matches[0]


def _parse_table_evaluations(
    profile: Mapping[str, Any],
    target_programs: Sequence[Program],
) -> tuple[CandidateEvaluation, ...]:
    evaluation_block = _mapping(profile.get("evaluation"), "evaluation")
    results: list[CandidateEvaluation] = []
    for index, row in enumerate(_rows(evaluation_block.get("rows"), "evaluation.rows")):
        selector = _mapping(row.get("selector"), "evaluation.selector")
        program = _resolve_selector(selector, target_programs, f"evaluation row {index}")
        values = row.get("objective_values")
        if not isinstance(values, list):
            raise JaggedThoughtsProfileError(
                "evaluation.objective_values must be a numeric list"
            )
        results.append(CandidateEvaluation(
            program_id=program.program_id,
            objective_values=tuple(values),
            behavior_signature=_texts(
                row.get("behavior_signature"),
                "evaluation.behavior_signature",
            ),
            evidence_refs=_texts(
                row.get("evidence_refs"),
                "evaluation.evidence_refs",
            ),
        ))
    return tuple(results)


def _parse_factor_model(
    evaluation_block: Mapping[str, Any],
) -> FactorEvaluationModel:
    objective_names = _texts(
        evaluation_block.get("objectives"),
        "evaluation.objectives",
    )
    scenarios: list[StrategicScenario] = []
    for scenario_row in _rows(
        evaluation_block.get("scenarios"),
        "evaluation.scenarios",
    ):
        factors = tuple(
            StrategicFactor(
                factor_id=_text(factor_row.get("id"), "factor.id"),
                requires=_texts(factor_row.get("requires"), "factor.requires"),
                delta=_numbers(factor_row.get("delta"), "factor.delta"),
                evidence_refs=_texts(
                    factor_row.get("evidence_refs"),
                    "factor.evidence_refs",
                ),
                alternatives=_number_rows(
                    factor_row.get("alternatives"),
                    "factor.alternatives",
                ),
                question=str(factor_row.get("question") or "").strip(),
                test=str(factor_row.get("test") or "").strip(),
                cost=float(factor_row.get("cost", 1.0)),
            )
            for factor_row in _rows(
                scenario_row.get("factors"),
                "evaluation.scenario.factors",
            )
        )
        try:
            weight = float(scenario_row.get("weight", 1.0))
        except (TypeError, ValueError) as error:
            raise JaggedThoughtsProfileError(
                "scenario.weight must be numeric"
            ) from error
        scenarios.append(StrategicScenario(
            scenario_id=_text(scenario_row.get("id"), "scenario.id"),
            weight=weight,
            base=_numbers(scenario_row.get("base"), "scenario.base"),
            factors=factors,
            evidence_refs=_texts(
                scenario_row.get("evidence_refs"),
                "scenario.evidence_refs",
            ),
        ))
    return FactorEvaluationModel(
        model_id=_text(evaluation_block.get("model_id"), "evaluation.model_id"),
        objective_names=objective_names,
        aggregation=_text(
            evaluation_block.get("aggregation", "scenario_vector"),
            "evaluation.aggregation",
        ),  # type: ignore[arg-type]
        scenarios=tuple(scenarios),
    )


def _parse_neighborhood(
    profile: Mapping[str, Any],
    target_programs: Sequence[Program],
) -> Neighborhood:
    raw = _mapping(profile.get("neighborhood"), "neighborhood")
    neighborhood_id = _text(raw.get("id"), "neighborhood.id")
    mode = _text(raw.get("mode"), "neighborhood.mode")
    if mode == "isolated":
        return Neighborhood(neighborhood_id, ())
    if mode == "complete":
        return Neighborhood(
            neighborhood_id,
            tuple(
                (left.program_id, right.program_id)
                for left, right in combinations(target_programs, 2)
            ),
        )
    if mode != "leaf_hamming":
        raise JaggedThoughtsProfileError(
            "neighborhood.mode must be isolated, complete, or leaf_hamming"
        )
    distance = raw.get("distance", 1)
    if not isinstance(distance, int) or distance < 1:
        raise JaggedThoughtsProfileError(
            "leaf_hamming neighborhood.distance must be positive"
        )
    same_root = raw.get("same_root_operator", True)
    if not isinstance(same_root, bool):
        raise JaggedThoughtsProfileError(
            "neighborhood.same_root_operator must be boolean"
        )
    edges: list[tuple[str, str]] = []
    for left, right in combinations(target_programs, 2):
        if same_root and left.operator_id != right.operator_id:
            continue
        left_leaves = program_terminal_ids(left)
        right_leaves = program_terminal_ids(right)
        if len(left_leaves) != len(right_leaves):
            continue
        hamming = sum(
            left_id != right_id
            for left_id, right_id in zip(left_leaves, right_leaves, strict=True)
        )
        if hamming == distance:
            edges.append((left.program_id, right.program_id))
    return Neighborhood(neighborhood_id, tuple(edges))


def _parse_representation_audit(
    profile: Mapping[str, Any],
    profile_id: str,
) -> RepresentationAudit:
    raw_value = profile.get("representation_audit")
    if raw_value is None:
        return RepresentationAudit(f"{profile_id}.representation-unassessed")
    raw = _mapping(raw_value, "representation_audit")
    return RepresentationAudit(
        audit_id=_text(raw.get("id"), "representation_audit.id"),
        status=_text(
            raw.get("status", "unassessed"),
            "representation_audit.status",
        ),  # type: ignore[arg-type]
        residuals=_texts(
            raw.get("residuals"),
            "representation_audit.residuals",
        ),
        evidence_refs=_texts(
            raw.get("evidence_refs"),
            "representation_audit.evidence_refs",
        ),
    )


def compile_profile(
    payload: Mapping[str, Any],
    *,
    source_root: Path | None = None,
) -> CompiledJaggedThoughtsProfile:
    """Compile a declarative profile into a replayable frontier certificate."""
    if payload.get("schema") != PROFILE_SCHEMA:
        raise JaggedThoughtsProfileError(
            f"profile.schema must equal {PROFILE_SCHEMA}"
        )
    profile_id = _text(payload.get("profile_id"), "profile_id")
    title = _text(payload.get("title"), "title")
    decision_question = _text(
        payload.get("decision_question"),
        "decision_question",
    )
    owner = _text(payload.get("owner"), "owner")
    as_of = _text(payload.get("as_of"), "as_of")
    evidence_manifest = compile_evidence_manifest(
        payload,
        source_root=source_root,
    )
    claims = _parse_claims(payload)
    grammar, target_type, max_depth, max_programs = _parse_grammar(payload)
    enumeration = enumerate_typed_programs(
        grammar,
        max_depth=max_depth,
        max_programs=max_programs,
    )
    target_programs = enumeration.programs_of_type(target_type)
    neighborhood = _parse_neighborhood(payload, target_programs)
    evaluation_block = _mapping(payload.get("evaluation"), "evaluation")
    declared_model_id = _text(
        evaluation_block.get("model_id"),
        "evaluation.model_id",
    )
    evaluation_kind = _text(
        evaluation_block.get("kind", "table"),
        "evaluation.kind",
    )
    evaluation_model: FactorEvaluationModel | None = None
    if evaluation_kind == "factor_graph":
        evaluation_model = _parse_factor_model(evaluation_block)
        grammar_symbols = {
            terminal.terminal_id for terminal in grammar.terminals
        } | {
            operator.operator_id for operator in grammar.operators
        }
        unknown_factor_symbols = sorted({
            symbol
            for scenario in evaluation_model.scenarios
            for factor in scenario.factors
            for symbol in factor.requires
            if symbol not in grammar_symbols
        })
        if unknown_factor_symbols:
            raise JaggedThoughtsProfileError(
                "factor requirements reference unknown grammar symbols: "
                f"{unknown_factor_symbols}"
            )
        objective_names = evaluation_model.compiled_objective_names
        evaluations = compile_factor_evaluations(
            target_programs,
            evaluation_model,
        )
    elif evaluation_kind == "table":
        objective_names = _texts(
            evaluation_block.get("objectives"),
            "evaluation.objectives",
        )
        evaluations = _parse_table_evaluations(payload, target_programs)
    else:
        raise JaggedThoughtsProfileError(
            "evaluation.kind must be table or factor_graph"
        )
    decision_surface_digest = content_sha256({
        "schema": "jaggedthoughts-decision-surface-v1",
        "evaluation": evaluation_block,
        "claims": payload.get("claims", []),
        "claim_dispositions": payload.get("claim_dispositions", []),
        "evidence_manifest_sha256": evidence_manifest.manifest_sha256,
    })
    scope = FrontierScope(
        grammar_id=grammar.grammar_id,
        grammar_version=grammar.version,
        grammar_digest=grammar.grammar_digest,
        target_type=target_type,
        max_depth=max_depth,
        max_programs=max_programs,
        evaluation_model_id=(
            f"{declared_model_id}@sha256:{decision_surface_digest}"
        ),
        landscape_mode=_text(
            evaluation_block.get("landscape_mode", "fixed"),
            "evaluation.landscape_mode",
        ),  # type: ignore[arg-type]
        evidence_epoch=_text(
            evaluation_block.get("evidence_epoch"),
            "evaluation.evidence_epoch",
        ),
        objective_names=objective_names,
        neighborhood_id=neighborhood.neighborhood_id,
    )
    dispositions = tuple(
        ClaimDisposition(
            claim_id=_text(row.get("claim_id"), "claim_disposition.claim_id"),
            status=_text(
                row.get("status"),
                "claim_disposition.status",
            ),  # type: ignore[arg-type]
            evidence_ref=_text(
                row.get("evidence_ref"),
                "claim_disposition.evidence_ref",
            ),
        )
        for row in _rows(payload.get("claim_dispositions"), "claim_dispositions")
    )
    evidence_manifest.require_refs(
        (disposition.evidence_ref for disposition in dispositions),
        context="claim dispositions",
    )
    evidence_manifest.require_refs(
        (
            ref
            for evaluation in evaluations
            for ref in evaluation.evidence_refs
        ),
        context="candidate evaluations",
    )
    if evaluation_model is not None:
        evidence_manifest.require_refs(
            evaluation_model.evidence_refs,
            context="factor evaluation model",
        )
    representation_audit = _parse_representation_audit(payload, profile_id)
    evidence_manifest.require_refs(
        representation_audit.evidence_refs,
        context="representation audit",
    )
    certificate = compile_jaggedthoughts_frontier(
        scope=scope,
        enumeration=enumeration,
        claims=claims,
        claim_dispositions=dispositions,
        evaluations=evaluations,
        neighborhood=neighborhood,
        representation_audit=representation_audit,
    )
    return CompiledJaggedThoughtsProfile(
        profile_id=profile_id,
        title=title,
        decision_question=decision_question,
        owner=owner,
        as_of=as_of,
        grammar=grammar,
        enumeration=enumeration,
        neighborhood=neighborhood,
        claims=claims,
        claim_dispositions=dispositions,
        evidence_manifest=evidence_manifest,
        evaluation_kind=evaluation_kind,
        evaluation_model=evaluation_model,
        evaluations=evaluations,
        certificate=certificate,
    )


def load_profile(path: str | Path) -> Mapping[str, Any]:
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    if source.suffix.lower() == ".json":
        payload = json.loads(text)
    elif source.suffix.lower() in {".yaml", ".yml"}:
        payload = yaml.safe_load(text)
    else:
        raise JaggedThoughtsProfileError("profile must be JSON or YAML")
    return _mapping(payload, "profile")


def compile_profile_file(path: str | Path) -> CompiledJaggedThoughtsProfile:
    source = Path(path)
    return compile_profile(load_profile(source), source_root=source.parent)
