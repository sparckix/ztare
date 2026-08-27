"""Compile an investment profile into a paper decision through JaggedThoughts."""

from __future__ import annotations

from functools import lru_cache
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import yaml

from ztare.common.equivariance import stable_sha256
from ztare.common.linear_preference_regions import compile_linear_preference_regions
from ztare.strategy import (
    MechanismEffect,
    MechanismRule,
    OperatorGrammar,
    PolicyCondition,
    PolicyObjective,
    Program,
    RepresentationAudit,
    StateCondition,
    StrategicAction,
    StrategicMechanism,
    StrategicState,
    TypedOperator,
    TypedTerminal,
    compile_condition_partition_states,
    compile_policy_action_regions,
    synthesize_policies,
)
from ztare.strategy.policies import PolicySynthesis

from .contracts import (
    EntityFingerprint,
    EntityRef,
    FingerprintMetric,
    FingerprintMetricDefinition,
    InvestmentObjectiveSpec,
    InvestmentPlay,
    InvestmentProfileLifecycle,
    InvestmentThesis,
    MarketStateCommittee,
    MetricObservation,
    PointInTimeSnapshot,
    PositionActionSpec,
    PremiumEstimate,
    ThesisReviewPacket,
    UnderwritingCase,
    canonical_timestamp,
    mapping_rows,
    require_finite,
    require_refs,
    require_text,
    timestamp_key,
)
from .paper import PaperBook, PaperPosition, PositionProposal, apply_paper_action
from .observation_index import load_observation_rows, observation_source_sha256
from .valuation import (
    ValuationAssumption,
    ValuationEnvelope,
    ValuationScenario,
    compile_hurdle_price_frontier,
    compile_valuation_envelope,
)


INVESTMENT_PROFILE_SCHEMA = "jaggedthoughts-investment-profile-v1"
INVESTMENT_DECISION_SCHEMA = "jaggedthoughts-investment-decision-v1"


class InvestmentProfileError(ValueError):
    """Raised when an investment profile crosses an identity or time boundary."""


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise InvestmentProfileError(f"{label} must be a mapping")
    return value


def _rows(value: Any, label: str) -> tuple[Mapping[str, Any], ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise InvestmentProfileError(f"{label} must be a list")
    return tuple(_mapping(row, f"{label} row") for row in value)


def _texts(value: Any, label: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise InvestmentProfileError(f"{label} must be a list")
    return tuple(require_text(item, f"{label} item") for item in value)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_payload(path: Path) -> Mapping[str, Any]:
    raw = path.read_text(encoding="utf-8")
    parsed = json.loads(raw) if path.suffix.lower() == ".json" else yaml.safe_load(raw)
    return _mapping(parsed, "investment profile")


def _source_receipts(
    payload: Mapping[str, Any],
    *,
    source_root: Path,
) -> tuple[dict[str, str], ...]:
    receipts: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in _rows(payload.get("sources"), "sources"):
        source_id = require_text(row.get("id"), "source.id")
        if source_id in seen:
            raise InvestmentProfileError(f"duplicate source identity: {source_id}")
        seen.add(source_id)
        relative = require_text(row.get("path"), "source.path")
        path = (source_root / relative).resolve()
        try:
            path.relative_to(source_root.resolve())
        except ValueError as error:
            raise InvestmentProfileError(f"source escapes profile root: {relative}") from error
        if not path.is_file():
            raise InvestmentProfileError(f"source does not exist: {relative}")
        receipts.append({
            "source_id": source_id,
            "path": relative,
            "sha256": _file_sha256(path),
        })
    return tuple(sorted(receipts, key=lambda row: row["source_id"]))


@lru_cache(maxsize=4)
def _cached_file_sha256(path_text: str, mtime_ns: int, size: int) -> str:
    path = Path(path_text)
    digest = observation_source_sha256(path)
    after = path.stat()
    if after.st_mtime_ns != mtime_ns or after.st_size != size:
        raise InvestmentProfileError(f"observations file changed while hashing: {path}")
    return digest


@lru_cache(maxsize=8)
def _cached_observation_rows(
    path_text: str, mtime_ns: int, size: int, entity_ids: tuple[str, ...] | None,
    metric_ids: tuple[str, ...] | None,
) -> tuple[tuple[MetricObservation, ...], str]:
    """Query one immutable file version only for the declared snapshot scope."""
    path = Path(path_text)
    digest = _cached_file_sha256(path_text, mtime_ns, size)
    if entity_ids == () or metric_ids == ():
        return (), digest
    try:
        raw_rows = load_observation_rows(
            path, as_of="9999-12-31T23:59:59Z", entity_ids=entity_ids,
            metric_ids=metric_ids, strict=True,
        )
        observations = tuple(MetricObservation(
            observation_id=str(row["observation_id"]),
            entity_id=str(row["entity_id"]), metric_id=str(row["metric_id"]),
            value=float(row["value"]), unit=str(row["unit"]),
            observed_at=str(row["observed_at"]), available_at=str(row["available_at"]),
            source_ref=str(row["source_ref"]),
        ) for row in raw_rows)
    except (TypeError, ValueError) as error:
        raise InvestmentProfileError(str(error)) from error
    after = path.stat()
    if after.st_mtime_ns != mtime_ns or after.st_size != size:
        raise InvestmentProfileError(f"observations file changed while reading: {path}")
    return observations, digest


@lru_cache(maxsize=32)
def _cached_snapshot_rows(
    path_text: str, mtime_ns: int, size: int, canonical_as_of: str,
    entity_ids: tuple[str, ...] | None, metric_ids: tuple[str, ...] | None,
) -> tuple[tuple[MetricObservation, ...], int, str]:
    rows, digest = _cached_observation_rows(
        path_text, mtime_ns, size, entity_ids, metric_ids,
    )
    cutoff = timestamp_key(canonical_as_of)
    included = tuple(row for row in rows if timestamp_key(row.available_at) <= cutoff)
    return included, len(rows) - len(included), digest


def load_point_in_time_snapshot(
    path: Path,
    *,
    as_of: str,
    snapshot_id: str,
    display_path: str | None = None,
    entity_ids: Iterable[str] | None = None,
    metric_ids: Iterable[str] | None = None,
) -> PointInTimeSnapshot:
    """Load numeric observations and exclude rows unavailable at ``as_of``."""
    if not path.is_file():
        raise InvestmentProfileError(f"observations file does not exist: {path}")
    canonical_as_of = canonical_timestamp(as_of, "decision.as_of")
    resolved = path.resolve()
    stat = resolved.stat()
    entity_scope = (
        tuple(sorted({require_text(value, "snapshot entity_id") for value in entity_ids}))
        if entity_ids is not None else None
    )
    metric_scope = (
        tuple(sorted({require_text(value, "snapshot metric_id") for value in metric_ids}))
        if metric_ids is not None else None
    )
    observations, excluded, digest = _cached_snapshot_rows(
        str(resolved), stat.st_mtime_ns, stat.st_size, canonical_as_of,
        entity_scope, metric_scope,
    )
    return PointInTimeSnapshot(
        snapshot_id=snapshot_id,
        as_of=canonical_as_of,
        source_path=display_path or str(path),
        source_sha256=digest,
        observations=observations,
        excluded_future_count=excluded,
    )


def _parse_entity(row: Mapping[str, Any], label: str) -> EntityRef:
    return EntityRef(
        entity_id=require_text(row.get("id"), f"{label}.id"),
        entity_kind=require_text(row.get("kind"), f"{label}.kind"),
        name=require_text(row.get("name"), f"{label}.name"),
        currency=require_text(row.get("currency"), f"{label}.currency"),
    )


def _parse_play(row: Mapping[str, Any]) -> InvestmentPlay:
    return InvestmentPlay(
        play_id=require_text(row.get("id"), "play.id"),
        version=require_text(row.get("version"), "play.version"),
        entity_kind=require_text(row.get("entity_kind"), "play.entity_kind"),
        universe=require_text(row.get("universe"), "play.universe"),
        benchmark_id=require_text(row.get("benchmark_id"), "play.benchmark_id"),
        horizon_days=int(row.get("horizon_days", 0)),
        min_weight=float(row.get("min_weight", 0)),
        max_weight=float(row.get("max_weight", 0)),
        allow_short=bool(row.get("allow_short", False)),
        transaction_cost_bps=float(row.get("transaction_cost_bps", 0)),
    )


def compile_fingerprint(
    *,
    entity: EntityRef,
    play: InvestmentPlay,
    snapshot: PointInTimeSnapshot,
    block: Mapping[str, Any],
) -> EntityFingerprint:
    definitions = tuple(
        FingerprintMetricDefinition(
            metric_id=require_text(row.get("id"), "fingerprint.metric.id"),
            unit=require_text(row.get("unit"), "fingerprint.metric.unit"),
            direction=require_text(row.get("direction"), "fingerprint.metric.direction"),  # type: ignore[arg-type]
            floor=float(row.get("floor")),
            ceiling=float(row.get("ceiling")),
            weight=float(row.get("weight", 0)),
            required=bool(row.get("required", True)),
        )
        for row in _rows(block.get("metrics"), "fingerprint.metrics")
    )
    if not definitions or len({row.metric_id for row in definitions}) != len(definitions):
        raise InvestmentProfileError("fingerprint metric definitions must be nonempty and unique")
    metrics: list[FingerprintMetric] = []
    missing_optional: list[str] = []
    for definition in definitions:
        try:
            observation = snapshot.latest(entity.entity_id, definition.metric_id)
        except KeyError:
            if definition.required:
                raise InvestmentProfileError(
                    f"required fingerprint metric is missing: {definition.metric_id}"
                ) from None
            missing_optional.append(definition.metric_id)
            continue
        metrics.append(FingerprintMetric(
            definition=definition,
            observation=observation,
            normalized_score=definition.normalize(observation.value),
        ))
    weight = sum(row.definition.weight for row in metrics)
    if weight <= 0:
        raise InvestmentProfileError("observed fingerprint metric weight must be positive")
    aggregate = sum(
        row.definition.weight * row.normalized_score for row in metrics
    ) / weight
    schema_version = require_text(block.get("version", "1"), "fingerprint.version")
    return EntityFingerprint(
        fingerprint_id=f"{entity.entity_id}:{play.play_key}:{snapshot.snapshot_id}",
        schema_version=schema_version,
        entity=entity,
        play_key=play.play_key,
        evidence_epoch=snapshot.snapshot_sha256,
        metrics=tuple(metrics),
        missing_optional_metrics=tuple(missing_optional),
        aggregate_score=aggregate,
    )


def _parse_market_state(
    block: Mapping[str, Any],
    *,
    as_of: str,
    play: InvestmentPlay,
) -> MarketStateCommittee:
    return MarketStateCommittee(
        committee_id=require_text(block.get("id"), "market_state.id"),
        as_of=as_of,
        horizon_days=play.horizon_days,
        estimates=tuple(
            PremiumEstimate(
                estimate_id=require_text(row.get("id"), "market_state.estimate.id"),
                annualized_premium=float(row.get("annualized_premium")),
                downside_return=float(row.get("downside_return")),
                weight=float(row.get("weight", 1)),
                horizon_days=int(row.get("horizon_days", play.horizon_days)),
                source_refs=_texts(row.get("source_refs"), "market_state.estimate.source_refs"),
            )
            for row in _rows(block.get("estimates"), "market_state.estimates")
        ),
    )


def _parse_actions(value: Any) -> tuple[PositionActionSpec, ...]:
    actions = tuple(
        PositionActionSpec(
            action_id=require_text(row.get("id"), "action.id"),
            kind=require_text(row.get("kind"), "action.kind"),  # type: ignore[arg-type]
            description=require_text(row.get("description"), "action.description"),
            target_weight=(
                None if row.get("target_weight") is None
                else float(row["target_weight"])
            ),
            weight_delta=(
                None if row.get("weight_delta") is None
                else float(row["weight_delta"])
            ),
            primitive_cost=float(row.get("primitive_cost", 0)),
            irreversibility=float(row.get("irreversibility", 0)),
            evidence_refs=_texts(row.get("evidence_refs"), "action.evidence_refs"),
        )
        for row in _rows(value, "actions")
    )
    if not actions or len({row.action_id for row in actions}) != len(actions):
        raise InvestmentProfileError("position actions must be nonempty and unique")
    return actions


def _parse_book(
    block: Mapping[str, Any],
    *,
    snapshot: PointInTimeSnapshot,
    as_of: str,
    price_metric: str,
) -> PaperBook:
    positions: list[PaperPosition] = []
    for row in _rows(block.get("positions"), "portfolio.positions"):
        entity_id = require_text(row.get("entity_id"), "portfolio.position.entity_id")
        price = snapshot.latest(entity_id, price_metric).value
        positions.append(PaperPosition(
            entity_id=entity_id,
            quantity=float(row.get("quantity")),
            last_price=price,
        ))
    return PaperBook(
        book_id=require_text(block.get("id"), "portfolio.id"),
        as_of=as_of,
        currency=require_text(block.get("currency"), "portfolio.currency"),
        cash=float(block.get("cash", 0)),
        positions=tuple(positions),
    )


def _parse_conditions(value: Any) -> tuple[PolicyCondition, ...]:
    rows = tuple(
        PolicyCondition(
            condition_id=require_text(row.get("id"), "policy.condition.id"),
            path=require_text(row.get("path"), "policy.condition.path"),
            operator=require_text(row.get("operator"), "policy.condition.operator"),  # type: ignore[arg-type]
            value=float(row.get("value")),
            evidence_refs=_texts(row.get("evidence_refs"), "policy.condition.evidence_refs"),
        )
        for row in _rows(value, "policy.conditions")
    )
    if len({row.condition_id for row in rows}) != len(rows):
        raise InvestmentProfileError("policy condition identities must be unique")
    return rows


def _parse_objectives(value: Any) -> tuple[InvestmentObjectiveSpec, ...]:
    rows = tuple(
        InvestmentObjectiveSpec(
            objective_id=require_text(row.get("id"), "policy.objective.id"),
            path=require_text(row.get("path"), "policy.objective.path"),
            direction=require_text(row.get("direction"), "policy.objective.direction"),  # type: ignore[arg-type]
            scale=float(row.get("scale")),
            utility_weight=float(row.get("utility_weight")),
        )
        for row in _rows(value, "policy.objectives")
    )
    if not rows or len({row.objective_id for row in rows}) != len(rows):
        raise InvestmentProfileError("investment objectives must be nonempty and unique")
    weight = sum(row.utility_weight for row in rows)
    if abs(weight - 1.0) > 1e-9:
        raise InvestmentProfileError("objective utility weights must sum to 1")
    return rows


def _parse_state_condition(row: Mapping[str, Any]) -> StateCondition:
    return StateCondition(
        path=require_text(row.get("path"), "mechanism.condition.path"),
        operator=require_text(row.get("operator"), "mechanism.condition.operator"),  # type: ignore[arg-type]
        value=float(row.get("value")),
    )


def _parse_effects(value: Any) -> tuple[MechanismEffect, ...]:
    if isinstance(value, Mapping):
        return tuple(
            MechanismEffect(path=str(path), delta=float(delta))
            for path, delta in value.items()
        )
    return tuple(
        MechanismEffect(
            path=require_text(row.get("path"), "mechanism.effect.path"),
            delta=float(row.get("delta")),
        )
        for row in _rows(value, "mechanism.effects")
    )


def _compile_mechanisms(
    value: Any,
    *,
    actions: Sequence[PositionActionSpec],
    current_weight: float,
    transaction_cost_bps: float,
    all_paths: set[str],
) -> tuple[StrategicMechanism, ...]:
    action_ids = {row.action_id for row in actions}
    models: list[StrategicMechanism] = []
    for model_row in _rows(value, "mechanisms"):
        model_id = require_text(model_row.get("id"), "mechanism.id")
        model_refs = _texts(model_row.get("evidence_refs"), "mechanism.evidence_refs")
        semantic_rules: list[MechanismRule] = []
        for action in actions:
            target = action.target_from(current_weight)
            delta = target - current_weight
            semantic_rules.append(MechanismRule(
                rule_id=f"semantics::{action.action_id}",
                phase="primary",
                action_ids=(action.action_id,),
                conditions=(),
                effects=(
                    MechanismEffect("firm.position_weight", delta),
                    MechanismEffect(
                        "firm.implementation_cost",
                        abs(delta) * transaction_cost_bps / 10_000,
                    ),
                ),
                evidence_refs=action.evidence_refs,
                priority=-100,
            ))
        domain_rules: list[MechanismRule] = []
        for rule_row in _rows(model_row.get("rules"), "mechanism.rules"):
            effects = _parse_effects(rule_row.get("effects"))
            forbidden = {
                effect.path for effect in effects
                if effect.path in {"firm.position_weight", "firm.implementation_cost"}
            }
            if forbidden:
                raise InvestmentProfileError(
                    f"mechanism {model_id} cannot redefine invariant action semantics: "
                    f"{sorted(forbidden)}"
                )
            actions_for_rule = _texts(rule_row.get("actions"), "mechanism.rule.actions")
            unknown_actions = set(actions_for_rule) - action_ids
            if unknown_actions:
                raise InvestmentProfileError(
                    f"mechanism {model_id} references unknown actions: {sorted(unknown_actions)}"
                )
            unknown_paths = {
                *(effect.path for effect in effects),
                *(
                    require_text(row.get("path"), "mechanism.condition.path")
                    for row in _rows(rule_row.get("conditions"), "mechanism.conditions")
                ),
            } - all_paths
            if unknown_paths:
                raise InvestmentProfileError(
                    f"mechanism {model_id} references unknown paths: {sorted(unknown_paths)}"
                )
            domain_rules.append(MechanismRule(
                rule_id=require_text(rule_row.get("id"), "mechanism.rule.id"),
                phase=require_text(rule_row.get("phase", "primary"), "mechanism.rule.phase"),  # type: ignore[arg-type]
                action_ids=actions_for_rule,
                conditions=tuple(
                    _parse_state_condition(row)
                    for row in _rows(rule_row.get("conditions"), "mechanism.conditions")
                ),
                effects=effects,
                evidence_refs=_texts(rule_row.get("evidence_refs"), "mechanism.rule.evidence_refs"),
                actor_id=str(rule_row.get("actor_id") or ""),
                priority=int(rule_row.get("priority", 0)),
            ))
        models.append(StrategicMechanism(
            mechanism_id=model_id,
            description=require_text(model_row.get("description"), "mechanism.description"),
            description_units=int(model_row.get("description_units", max(1, len(domain_rules)))),
            rules=tuple((*semantic_rules, *domain_rules)),
            evidence_refs=model_refs,
        ))
    if not models or len({row.mechanism_id for row in models}) != len(models):
        raise InvestmentProfileError("mechanisms must be nonempty and unique")
    return tuple(models)


def _finance_policy_grammar(
    *,
    grammar_id: str,
    version: str,
    actions: Sequence[StrategicAction],
    conditions: Sequence[PolicyCondition],
) -> OperatorGrammar:
    """A recursive contingent policy that terminates in one position action."""
    return OperatorGrammar(
        grammar_id=grammar_id,
        version=version,
        terminals=tuple(
            TypedTerminal(
                terminal_id=f"act::{action.action_id}",
                output_type="Policy",
                description=action.description,
            )
            for action in actions
        ) + tuple(
            TypedTerminal(
                terminal_id=f"when::{condition.condition_id}",
                output_type="Condition",
                description=f"{condition.path} {condition.operator} {condition.value}",
            )
            for condition in conditions
        ),
        operators=(TypedOperator(
            operator_id="branch",
            input_types=("Condition", "Policy", "Policy"),
            output_type="Policy",
            description="Choose one position action from the current investment state.",
        ),),
    )


def _program_expression(program: Program) -> str:
    if program.terminal_id is not None:
        return program.terminal_id
    return f"{program.operator_id}(" + ", ".join(
        _program_expression(child) for child in program.children
    ) + ")"


def _resolve_terminal_action(
    program: Program,
    *,
    state: StrategicState,
    conditions: Mapping[str, PolicyCondition],
) -> str:
    if program.terminal_id is not None:
        if not program.terminal_id.startswith("act::"):
            raise InvestmentProfileError("selected policy did not terminate in an action")
        return program.terminal_id.removeprefix("act::")
    if program.operator_id != "branch":
        raise InvestmentProfileError(f"investment grammar emitted unsupported operator: {program.operator_id}")
    condition_id = (program.children[0].terminal_id or "").removeprefix("when::")
    condition = conditions.get(condition_id)
    if condition is None:
        raise InvestmentProfileError(f"selected policy references unknown condition: {condition_id}")
    branch = program.children[1] if condition.matches(state) else program.children[2]
    return _resolve_terminal_action(branch, state=state, conditions=conditions)


@dataclass(frozen=True, slots=True)
class SelectedInvestmentPolicy:
    program_id: str
    expression: str
    action_id: str
    robust_objective_values: tuple[tuple[str, float], ...]
    utility_components: tuple[tuple[str, float], ...]
    utility: float
    selection_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        for attr in ("program_id", "expression", "action_id"):
            object.__setattr__(self, attr, require_text(getattr(self, attr), f"selection.{attr}"))
        objectives = mapping_rows(dict(self.robust_objective_values))
        components = mapping_rows(dict(self.utility_components))
        object.__setattr__(self, "robust_objective_values", objectives)
        object.__setattr__(self, "utility_components", components)
        object.__setattr__(self, "utility", require_finite(self.utility, "selection.utility"))
        object.__setattr__(self, "selection_sha256", stable_sha256(self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "jaggedthoughts-investment-policy-selection-v1",
            "program_id": self.program_id,
            "expression": self.expression,
            "action_id": self.action_id,
            "robust_objective_values": dict(self.robust_objective_values),
            "utility_components": dict(self.utility_components),
            "utility": self.utility,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "selection_sha256": self.selection_sha256}


def _select_policy(
    synthesis: PolicySynthesis,
    *,
    frontier_program_ids: Sequence[str],
    objectives: Sequence[InvestmentObjectiveSpec],
    initial_state: StrategicState,
    conditions: Sequence[PolicyCondition],
) -> SelectedInvestmentPolicy:
    programs = {row.program_id: row for row in synthesis.enumeration.programs}
    evaluations = {row.program_id: row for row in synthesis.evaluations}
    candidates: list[tuple[float, int, int, str, tuple[tuple[str, float], ...]]] = []
    for program_id in frontier_program_ids:
        evaluation = evaluations[program_id]
        components = tuple(
            (spec.objective_id, spec.utility_component(value))
            for spec, value in zip(objectives, evaluation.objective_values, strict=True)
        )
        program = programs[program_id]
        candidates.append((
            sum(value for _name, value in components),
            program.depth,
            len(_program_expression(program)),
            program_id,
            components,
        ))
    if not candidates:
        raise InvestmentProfileError("policy synthesis produced no robust frontier member")
    utility, _depth, _expression_length, program_id, components = sorted(
        candidates, key=lambda row: (-row[0], row[1], row[2], row[3])
    )[0]
    program = programs[program_id]
    action_id = _resolve_terminal_action(
        program,
        state=initial_state,
        conditions={row.condition_id: row for row in conditions},
    )
    evaluation = evaluations[program_id]
    return SelectedInvestmentPolicy(
        program_id=program_id,
        expression=_program_expression(program),
        action_id=action_id,
        robust_objective_values=tuple(
            (spec.objective_id, value)
            for spec, value in zip(objectives, evaluation.objective_values, strict=True)
        ),
        utility_components=components,
        utility=utility,
    )


def _canonical_policy_frontier(synthesis: PolicySynthesis) -> dict[str, Any]:
    """Use the smallest program in each consequence-equivalent frontier class."""
    programs = {row.program_id: row for row in synthesis.enumeration.programs}
    members = {
        program_id: [program_id]
        for program_id in synthesis.certificate.frontier_program_ids
    }
    for witness in synthesis.certificate.equivalent:
        if witness.representative_program_id in members:
            members[witness.representative_program_id].append(witness.program_id)
    replacements = []
    for representative, program_ids in sorted(members.items()):
        canonical = min(
            program_ids,
            key=lambda program_id: (
                programs[program_id].depth,
                len(_program_expression(programs[program_id])),
                program_id,
            ),
        )
        replacements.append({
            "source_program_id": representative,
            "canonical_program_id": canonical,
            "equivalent_program_count": len(program_ids),
        })
    body = {
        "schema": "jaggedthoughts-policy-frontier-canonicalization-v1",
        "source_frontier_program_ids": list(synthesis.certificate.frontier_program_ids),
        "canonical_frontier_program_ids": sorted(
            row["canonical_program_id"] for row in replacements
        ),
        "replacements": replacements,
        "rule": "minimum program depth, then expression length, then program identity",
    }
    return {**body, "canonicalization_sha256": stable_sha256(body)}


def _validate_refs(refs: Iterable[str], allowed: set[str], context: str) -> None:
    unknown = set(refs) - allowed
    if unknown:
        raise InvestmentProfileError(f"{context} uses unknown source refs: {sorted(unknown)}")


def _compile_valuation(
    block: Mapping[str, Any],
    *,
    entity: EntityRef,
    snapshot: PointInTimeSnapshot,
    price: MetricObservation,
    market_state: MarketStateCommittee,
    allowed_refs: set[str],
) -> ValuationEnvelope:
    """Compile source-bound valuation specifications into one expectations envelope."""
    assumptions: list[ValuationAssumption] = [ValuationAssumption(
        assumption_id=f"market_price::{price.observation_id}",
        assumption_type="MarketPrice",
        value=price.value,
        unit="currency/share",
        source_refs=(price.source_ref,),
    )]

    def observation_assumption(
        *,
        field: str,
        assumption_type: str,
        expected_unit: str,
        normalized_unit: str,
    ) -> None:
        metric_id = require_text(block.get(field), f"valuation.{field}")
        observation = snapshot.latest(entity.entity_id, metric_id)
        if observation.unit != expected_unit:
            raise InvestmentProfileError(
                f"valuation metric {metric_id} must use {expected_unit}, got {observation.unit}"
            )
        assumptions.append(ValuationAssumption(
            assumption_id=f"{assumption_type.lower()}::{observation.observation_id}",
            assumption_type=assumption_type,
            value=observation.value,
            unit=normalized_unit,
            source_refs=(observation.source_ref,),
        ))

    observation_assumption(
        field="owner_earnings_metric",
        assumption_type="OwnerEarnings",
        expected_unit=f"{entity.currency}/year",
        normalized_unit="currency/year",
    )
    observation_assumption(
        field="excess_net_cash_metric",
        assumption_type="ExcessNetCash",
        expected_unit=entity.currency,
        normalized_unit="currency",
    )
    observation_assumption(
        field="shares_metric",
        assumption_type="Shares",
        expected_unit="shares",
        normalized_unit="shares",
    )

    def literal_assumptions(
        field: str,
        assumption_type: str,
        *,
        value_field: str = "value",
        unit: str = "decimal",
    ) -> None:
        for row in _rows(block.get(field), f"valuation.{field}"):
            refs = _texts(row.get("source_refs"), f"valuation.{field}.source_refs")
            _validate_refs(refs, allowed_refs, f"valuation assumption {row.get('id')}")
            assumptions.append(ValuationAssumption(
                assumption_id=require_text(row.get("id"), f"valuation.{field}.id"),
                assumption_type=assumption_type,
                value=require_finite(row.get(value_field), f"valuation.{field}.{value_field}"),
                unit=unit,
                source_refs=refs,
            ))

    risk_free = _mapping(block.get("risk_free_rate"), "valuation.risk_free_rate")
    risk_free_refs = _texts(risk_free.get("source_refs"), "valuation.risk_free_rate.source_refs")
    _validate_refs(risk_free_refs, allowed_refs, "valuation risk-free rate")
    assumptions.append(ValuationAssumption(
        assumption_id=require_text(risk_free.get("id"), "valuation.risk_free_rate.id"),
        assumption_type="RiskFreeRate",
        value=require_finite(risk_free.get("value"), "valuation.risk_free_rate.value"),
        unit="decimal",
        source_refs=risk_free_refs,
    ))
    assumptions.extend(
        ValuationAssumption(
            assumption_id=f"erp::{estimate.estimate_id}",
            assumption_type="EquityRiskPremium",
            value=estimate.annualized_premium,
            unit="decimal",
            source_refs=estimate.source_refs,
        )
        for estimate in market_state.estimates
    )
    literal_assumptions("equity_betas", "EquityBeta", unit="multiple")
    literal_assumptions("discount_rates", "DiscountRate")
    literal_assumptions("forecast_growth_rates", "ForecastGrowth")
    literal_assumptions("terminal_growth_rates", "TerminalGrowth")
    literal_assumptions("horizons", "Horizon", value_field="years", unit="years")
    scenarios: list[ValuationScenario] = []
    for row in _rows(block.get("cash_flow_scenarios"), "valuation.cash_flow_scenarios"):
        refs = _texts(row.get("source_refs"), "valuation.cash_flow_scenarios.source_refs")
        _validate_refs(refs, allowed_refs, f"valuation scenario {row.get('id')}")
        scenarios.append(ValuationScenario(
            scenario_id=require_text(row.get("id"), "valuation.cash_flow_scenarios.id"),
            mechanism_id=require_text(
                row.get("mechanism_id"), "valuation.cash_flow_scenarios.mechanism_id"
            ),
            assumption_ids=_texts(
                row.get("assumption_ids"), "valuation.cash_flow_scenarios.assumption_ids"
            ),
            source_refs=refs,
        ))
    if not scenarios:
        raise InvestmentProfileError("valuation.cash_flow_scenarios must be nonempty")
    try:
        return compile_valuation_envelope(
            envelope_id=f"{entity.entity_id}@{snapshot.snapshot_sha256}",
            entity_id=entity.entity_id,
            evidence_epoch=snapshot.snapshot_sha256,
            grammar_id=require_text(block.get("grammar_id"), "valuation.grammar_id"),
            grammar_version=require_text(block.get("version"), "valuation.version"),
            assumptions=assumptions,
            scenarios=scenarios,
            max_depth=int(block.get("max_depth", 4)),
            max_programs=int(block.get("max_programs", 5000)),
        )
    except ValueError as error:
        raise InvestmentProfileError(f"valuation: {error}") from error


def compile_investment_profile(
    payload: Mapping[str, Any],
    *,
    source_root: Path,
    profile_source_sha256: str,
) -> dict[str, Any]:
    """Compile one profile into an immutable paper decision record."""
    if payload.get("schema") != INVESTMENT_PROFILE_SCHEMA:
        raise InvestmentProfileError(f"schema must be {INVESTMENT_PROFILE_SCHEMA}")
    profile_id = require_text(payload.get("profile_id"), "profile_id")
    lifecycle_declared = payload.get("lifecycle") is not None
    lifecycle_raw = payload.get("lifecycle") or {
        "data_class": "operator", "stage": "active", "authority": "paper",
    }
    lifecycle_block = _mapping(lifecycle_raw, "lifecycle")
    lifecycle = InvestmentProfileLifecycle(
        data_class=require_text(lifecycle_block.get("data_class"), "lifecycle.data_class"),  # type: ignore[arg-type]
        stage=require_text(lifecycle_block.get("stage"), "lifecycle.stage"),  # type: ignore[arg-type]
        authority=require_text(lifecycle_block.get("authority", "paper"), "lifecycle.authority"),
    )
    decision = _mapping(payload.get("decision"), "decision")
    decision_id = require_text(decision.get("id"), "decision.id")
    as_of = canonical_timestamp(decision.get("as_of"), "decision.as_of")
    owner = require_text(decision.get("owner"), "decision.owner")
    question = require_text(decision.get("question"), "decision.question")
    entity = _parse_entity(_mapping(payload.get("entity"), "entity"), "entity")
    benchmark = _parse_entity(_mapping(payload.get("benchmark"), "benchmark"), "benchmark")
    play = _parse_play(_mapping(payload.get("play"), "play"))
    if entity.entity_kind != play.entity_kind:
        raise InvestmentProfileError("entity kind does not match play entity kind")
    if benchmark.entity_id != play.benchmark_id:
        raise InvestmentProfileError("benchmark identity does not match play benchmark_id")
    source_receipts = _source_receipts(payload, source_root=source_root)
    observation_rel = require_text(payload.get("observations_file"), "observations_file")
    observation_path = (source_root / observation_rel).resolve()
    try:
        observation_path.relative_to(source_root.resolve())
    except ValueError as error:
        raise InvestmentProfileError("observations_file escapes the profile root") from error
    portfolio_block = _mapping(payload.get("portfolio"), "portfolio")
    snapshot_entities = {
        entity.entity_id, benchmark.entity_id,
        *(
            require_text(row.get("entity_id"), "portfolio.position.entity_id")
            for row in _rows(portfolio_block.get("positions"), "portfolio.positions")
        ),
    }
    snapshot = load_point_in_time_snapshot(
        observation_path,
        as_of=as_of,
        snapshot_id=f"{profile_id}@{as_of}",
        display_path=observation_rel,
        entity_ids=snapshot_entities,
    )
    allowed_refs = {
        *(receipt["source_id"] for receipt in source_receipts),
        *snapshot.evidence_refs,
    }
    fingerprint = compile_fingerprint(
        entity=entity,
        play=play,
        snapshot=snapshot,
        block=_mapping(payload.get("fingerprint"), "fingerprint"),
    )
    market_state = _parse_market_state(
        _mapping(payload.get("market_state"), "market_state"),
        as_of=as_of,
        play=play,
    )
    for estimate in market_state.estimates:
        _validate_refs(estimate.source_refs, allowed_refs, f"premium estimate {estimate.estimate_id}")
    thesis_block = _mapping(payload.get("thesis"), "thesis")
    thesis = InvestmentThesis(
        thesis_id=require_text(thesis_block.get("id"), "thesis.id"),
        version=require_text(thesis_block.get("version"), "thesis.version"),
        entity_id=entity.entity_id,
        play_key=play.play_key,
        evidence_epoch=snapshot.snapshot_sha256,
        claim=require_text(thesis_block.get("claim"), "thesis.claim"),
        mechanism_ids=_texts(thesis_block.get("mechanism_ids"), "thesis.mechanism_ids"),
        catalysts=_texts(thesis_block.get("catalysts"), "thesis.catalysts"),
        falsifiers=_texts(thesis_block.get("falsifiers"), "thesis.falsifiers"),
        source_refs=_texts(thesis_block.get("source_refs"), "thesis.source_refs"),
    )
    _validate_refs(thesis.source_refs, allowed_refs, "thesis")
    underwriting_block = _mapping(payload.get("underwriting"), "underwriting")
    underwriting = UnderwritingCase(
        case_id=require_text(underwriting_block.get("id"), "underwriting.id"),
        entity_id=entity.entity_id,
        thesis_id=thesis.thesis_id,
        evidence_epoch=snapshot.snapshot_sha256,
        outside_view_reference=require_text(
            underwriting_block.get("outside_view_reference"),
            "underwriting.outside_view_reference",
        ),
        outside_view_base_rate=require_finite(
            underwriting_block.get("outside_view_base_rate"),
            "underwriting.outside_view_base_rate",
        ),
        failure_sequence=_texts(
            underwriting_block.get("failure_sequence"), "underwriting.failure_sequence"
        ),
        hurdle_rate=require_finite(
            underwriting_block.get("hurdle_rate"), "underwriting.hurdle_rate"
        ),
        next_best_alternative=require_text(
            underwriting_block.get("next_best_alternative"),
            "underwriting.next_best_alternative",
        ),
        rival_view=require_text(underwriting_block.get("rival_view"), "underwriting.rival_view"),
        decisive_observation=require_text(
            underwriting_block.get("decisive_observation"),
            "underwriting.decisive_observation",
        ),
        action_condition_id=require_text(
            underwriting_block.get("action_condition_id"),
            "underwriting.action_condition_id",
        ),
        source_refs=_texts(underwriting_block.get("source_refs"), "underwriting.source_refs"),
    )
    _validate_refs(underwriting.source_refs, allowed_refs, "underwriting")
    price_metric = require_text(payload.get("price_metric", "price"), "price_metric")
    entity_price = snapshot.latest(entity.entity_id, price_metric)
    benchmark_price = snapshot.latest(benchmark.entity_id, price_metric)
    if entity_price.unit != entity.currency or benchmark_price.unit != benchmark.currency:
        raise InvestmentProfileError("price observation units must equal entity currencies")
    valuation = _compile_valuation(
        _mapping(payload.get("valuation"), "valuation"),
        entity=entity,
        snapshot=snapshot,
        price=entity_price,
        market_state=market_state,
        allowed_refs=allowed_refs,
    )
    valuation_summary = dict(valuation.summary)
    hurdle_price_frontier = compile_hurdle_price_frontier(
        valuation,
        excess_return_hurdle=underwriting.hurdle_rate,
    )
    book_before = _parse_book(
        portfolio_block,
        snapshot=snapshot,
        as_of=as_of,
        price_metric=price_metric,
    )
    actions = _parse_actions(payload.get("actions"))
    for action in actions:
        _validate_refs(action.evidence_refs, allowed_refs, f"action {action.action_id}")
        target = action.target_from(book_before.weight(entity.entity_id))
        if target < play.min_weight - 1e-12 or target > play.max_weight + 1e-12:
            raise InvestmentProfileError(
                f"action {action.action_id} target weight is outside the play bounds"
            )
    policy_block = _mapping(payload.get("policy"), "policy")
    conditions = _parse_conditions(policy_block.get("conditions"))
    objectives = _parse_objectives(policy_block.get("objectives"))
    underwriting_condition = next(
        (row for row in conditions if row.condition_id == underwriting.action_condition_id),
        None,
    )
    if underwriting_condition is None:
        raise InvestmentProfileError("underwriting action_condition_id is absent from policy conditions")
    if (
        underwriting_condition.path != "firm.valuation_price_implied_excess_return"
        or underwriting_condition.operator not in {"ge", "gt"}
        or abs(underwriting_condition.value - underwriting.hurdle_rate) > 1e-12
    ):
        raise InvestmentProfileError(
            "underwriting action condition must apply its hurdle to price-implied excess return"
        )
    for condition in conditions:
        _validate_refs(condition.evidence_refs, allowed_refs, f"condition {condition.condition_id}")
    initial_values = {
        str(name): require_finite(value, f"policy.state.{name}")
        for name, value in _mapping(policy_block.get("state"), "policy.state").items()
    }
    reserved = {
        "position_weight": book_before.weight(entity.entity_id),
        "implementation_cost": 0.0,
        "fingerprint_score": fingerprint.aggregate_score,
        "market_premium": market_state.weighted_premium,
        "market_downside": market_state.weighted_downside,
        "market_dispersion": market_state.premium_dispersion,
        "expected_excess_return": valuation_summary["price_implied_excess_return"],
        "valuation_earnings_power_margin": valuation_summary["earnings_power_margin_of_safety"],
        "valuation_implied_growth": valuation_summary["implied_growth_median"],
        "valuation_implied_return": valuation_summary["implied_required_return_median"],
        "valuation_price_implied_excess_return": valuation_summary["price_implied_excess_return"],
        "outside_view_base_rate": underwriting.outside_view_base_rate,
        "underwriting_hurdle_rate": underwriting.hurdle_rate,
    }
    overlap = set(initial_values) & set(reserved)
    if overlap:
        raise InvestmentProfileError(f"policy.state cannot redefine reserved coordinates: {sorted(overlap)}")
    initial_values.update(reserved)
    initial_state = StrategicState(
        decision_id=decision_id,
        epoch=0,
        firm=tuple(initial_values.items()),
        context=(
            ("entity_id", entity.entity_id),
            ("play_key", play.play_key),
            ("evidence_epoch", snapshot.snapshot_sha256),
        ),
    )
    all_paths = set(initial_state.paths)
    for path in (
        *(condition.path for condition in conditions),
        *(objective.path for objective in objectives),
    ):
        if path not in all_paths:
            raise InvestmentProfileError(f"policy references unknown state path: {path}")
    strategic_actions = tuple(
        StrategicAction(
            action_id=action.action_id,
            description=action.description,
            primitive_cost=action.primitive_cost,
            irreversibility=action.irreversibility,
            authority_tier="paper",
            evidence_refs=action.evidence_refs,
        )
        for action in actions
    )
    mechanisms = _compile_mechanisms(
        payload.get("mechanisms"),
        actions=actions,
        current_weight=book_before.weight(entity.entity_id),
        transaction_cost_bps=play.transaction_cost_bps,
        all_paths=all_paths,
    )
    mechanism_ids = {row.mechanism_id for row in mechanisms}
    if set(thesis.mechanism_ids) != mechanism_ids:
        raise InvestmentProfileError(
            "thesis mechanism_ids must equal the compiled mechanism committee"
        )
    if {row.mechanism_id for row in valuation.scenarios} != mechanism_ids:
        raise InvestmentProfileError(
            "valuation scenario mechanism_ids must cover the mechanism committee"
        )
    for mechanism in mechanisms:
        _validate_refs(mechanism.evidence_refs, allowed_refs, f"mechanism {mechanism.mechanism_id}")
        for rule in mechanism.rules:
            _validate_refs(rule.evidence_refs, allowed_refs, f"mechanism rule {rule.rule_id}")
    representation_block = _mapping(payload.get("representation"), "representation")
    representation = RepresentationAudit(
        audit_id=require_text(representation_block.get("id"), "representation.id"),
        status=require_text(representation_block.get("status", "residual"), "representation.status"),  # type: ignore[arg-type]
        residuals=_texts(representation_block.get("residuals"), "representation.residuals"),
        evidence_refs=_texts(representation_block.get("evidence_refs"), "representation.evidence_refs"),
    )
    if representation.evidence_refs:
        _validate_refs(representation.evidence_refs, allowed_refs, "representation audit")
    grammar = _finance_policy_grammar(
        grammar_id=require_text(policy_block.get("grammar_id"), "policy.grammar_id"),
        version=require_text(policy_block.get("version"), "policy.version"),
        actions=strategic_actions,
        conditions=conditions,
    )
    policy_evaluation_states, policy_condition_partition = compile_condition_partition_states(
        initial_state=initial_state,
        conditions=conditions,
    )
    synthesis = synthesize_policies(
        decision_id=decision_id,
        evidence_epoch=snapshot.snapshot_sha256,
        grammar=grammar,
        max_depth=int(policy_block.get("max_depth", 2)),
        max_programs=int(policy_block.get("max_programs", 5000)),
        max_action_steps=1,
        initial_state=initial_state,
        evaluation_states=policy_evaluation_states,
        actions=strategic_actions,
        conditions=conditions,
        mechanisms=mechanisms,
        objectives=tuple(
            PolicyObjective(row.objective_id, row.path, row.direction)
            for row in objectives
        ),
        representation_audit=representation,
    )
    policy_frontier = _canonical_policy_frontier(synthesis)
    policy_frontier_ids = tuple(policy_frontier["canonical_frontier_program_ids"])
    selection = _select_policy(
        synthesis,
        frontier_program_ids=policy_frontier_ids,
        objectives=objectives,
        initial_state=initial_state,
        conditions=conditions,
    )
    selected_program = next(
        row for row in synthesis.enumeration.programs if row.program_id == selection.program_id
    )
    policy_action_regions = compile_policy_action_regions(
        program=selected_program,
        conditions=conditions,
        current_state=initial_state,
    )
    evaluation_by_id = {row.program_id: row for row in synthesis.evaluations}
    policy_objective_weight_regions = compile_linear_preference_regions(
        objective_names=tuple(row.objective_id for row in objectives),
        alternatives={
            program_id: {
                objective.objective_id: value / objective.scale
                for objective, value in zip(
                    objectives, evaluation_by_id[program_id].objective_values, strict=True
                )
            }
            for program_id in policy_frontier_ids
        },
    )
    action_by_id = {row.action_id: row for row in actions}
    proposal, book_after = apply_paper_action(
        decision_id=decision_id,
        as_of=as_of,
        entity=entity,
        play=play,
        book=book_before,
        action=action_by_id[selection.action_id],
        price=entity_price.value,
    )
    review_packet = ThesisReviewPacket(
        packet_id=f"{decision_id}:review",
        as_of=as_of,
        entity=entity,
        play=play,
        thesis=thesis,
        underwriting_sha256=underwriting.case_sha256,
        fingerprint_sha256=fingerprint.fingerprint_sha256,
        market_state_sha256=market_state.committee_sha256,
        calculations=(
            ("fingerprint_score", fingerprint.aggregate_score),
            ("market_weighted_premium", market_state.weighted_premium),
            ("market_weighted_downside", market_state.weighted_downside),
            ("market_premium_dispersion", market_state.premium_dispersion),
            ("decision_price", entity_price.value),
            ("earnings_power_margin_of_safety", valuation_summary["earnings_power_margin_of_safety"]),
            ("intrinsic_value_low", valuation_summary["intrinsic_value_low"]),
            ("intrinsic_value_high", valuation_summary["intrinsic_value_high"]),
            ("implied_growth_median", valuation_summary["implied_growth_median"]),
            ("implied_required_return_median", valuation_summary["implied_required_return_median"]),
            ("price_implied_excess_return", valuation_summary["price_implied_excess_return"]),
            ("outside_view_base_rate", underwriting.outside_view_base_rate),
            ("underwriting_hurdle_rate", underwriting.hurdle_rate),
        ),
        source_refs=tuple(sorted({
            *thesis.source_refs,
            *underwriting.source_refs,
            *(row.observation.source_ref for row in fingerprint.metrics),
            *(ref for estimate in market_state.estimates for ref in estimate.source_refs),
            *(ref for assumption in valuation.assumptions for ref in assumption.source_refs),
        })),
    )
    body: dict[str, Any] = {
        "schema": INVESTMENT_DECISION_SCHEMA,
        "decision_id": decision_id,
        "profile_id": profile_id,
        "profile_source_sha256": profile_source_sha256,
        "as_of": as_of,
        "owner": owner,
        "question": question,
        "authority": "paper",
        "entity": entity.to_dict(),
        "benchmark": benchmark.to_dict(),
        "play": play.to_dict(),
        "source_receipts": list(source_receipts),
        "point_in_time_snapshot": snapshot.to_dict(),
        "fingerprint": fingerprint.to_dict(),
        "market_state": market_state.to_dict(),
        "valuation_envelope": valuation.to_dict(),
        "hurdle_price_frontier": hurdle_price_frontier,
        "thesis": thesis.to_dict(),
        "underwriting_case": underwriting.to_dict(),
        "review_packet": review_packet.to_dict(),
        "initial_state": initial_state.to_dict(),
        "position_actions": [row.to_dict() for row in actions],
        "policy_conditions": [row.to_dict() for row in conditions],
        "policy_condition_partition": policy_condition_partition,
        "policy_objectives": [row.to_dict() for row in objectives],
        "mechanisms": [row.to_dict() for row in mechanisms],
        "policy_synthesis": synthesis.to_dict(),
        "policy_frontier": policy_frontier,
        "policy_objective_weight_regions": policy_objective_weight_regions,
        "policy_selection": selection.to_dict(),
        "policy_action_regions": policy_action_regions,
        "paper_book_before": book_before.to_dict(),
        "position_proposal": proposal.to_dict(),
        "paper_book_after": book_after.to_dict(),
        "benchmark_start_price": benchmark_price.value,
        "summary": {
            "frontier_count": len(policy_frontier_ids),
            "objective_weight_region_count": len(
                policy_objective_weight_regions["supported_alternative_ids"]
            ),
            "selected_policy_has_objective_weight_region": (
                selection.program_id in policy_objective_weight_regions["supported_alternative_ids"]
            ),
            "policy_action_region_count": len(policy_action_regions["regions"]),
            "reachable_policy_action_count": len(policy_action_regions["reachable_action_ids"]),
            "target_policy_count": len(synthesis.certificate.target_program_ids),
            "scope_closed": synthesis.certificate.scope_closed,
            "decision_closed": synthesis.certificate.decision_closed,
            "representation_status": synthesis.certificate.representation_audit.status,
            "valuation_program_count": len(valuation.results),
            "valuation_failure_count": len(valuation.failures),
            "earnings_power_margin_of_safety": valuation_summary["earnings_power_margin_of_safety"],
            "implied_growth_median": valuation_summary["implied_growth_median"],
            "implied_required_return_median": valuation_summary["implied_required_return_median"],
            "outside_view_base_rate": underwriting.outside_view_base_rate,
            "underwriting_hurdle_rate": underwriting.hurdle_rate,
            "robust_maximum_price": hurdle_price_frontier["robust_maximum_price"],
            "median_maximum_price": hurdle_price_frontier["median_maximum_price"],
            "optimistic_maximum_price": hurdle_price_frontier["optimistic_maximum_price"],
            "selected_action_id": selection.action_id,
            "current_weight": proposal.current_weight,
            "target_weight": proposal.target_weight,
            "estimated_cost": proposal.estimated_cost,
            "economic_status": "pending_settlement",
        },
    }
    if lifecycle_declared:
        body["profile_lifecycle"] = lifecycle.to_dict()
    return {**body, "decision_record_sha256": stable_sha256(body)}


def compile_investment_profile_file(
    path: str | Path,
    *,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    profile_path = Path(path).resolve()
    if not profile_path.is_file():
        raise InvestmentProfileError(f"profile does not exist: {profile_path}")
    resolved_root = Path(source_root).expanduser().resolve() if source_root is not None else profile_path.parent
    try:
        profile_path.relative_to(resolved_root)
    except ValueError as error:
        raise InvestmentProfileError("profile must live inside its declared source root") from error
    return compile_investment_profile(
        _load_payload(profile_path),
        source_root=resolved_root,
        profile_source_sha256=_file_sha256(profile_path),
    )


__all__ = [
    "INVESTMENT_DECISION_SCHEMA",
    "INVESTMENT_PROFILE_SCHEMA",
    "InvestmentProfileError",
    "SelectedInvestmentPolicy",
    "compile_fingerprint",
    "compile_investment_profile",
    "compile_investment_profile_file",
    "load_point_in_time_snapshot",
]
