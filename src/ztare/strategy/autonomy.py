"""End-to-end compilation and bounded execution for JaggedThoughts strategy loops."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

from ztare.common.equivariance import stable_sha256
from ztare.common.guarded_experiment_protocol import ProtocolCost
from ztare.common.temporal_decision_credit import (
    DecisionChoiceAuthority,
    DecisionEligibilityChain,
    DecisionEligibilityEdge,
    compile_decision_yield_calibration,
    compile_temporal_decision_credit,
)

from .evidence import StrategyEvidenceManifest, compile_evidence_manifest
from .jaggedthoughts import RepresentationAudit
from .mechanisms import (
    MechanismEffect,
    MechanismRule,
    MechanismVersionSpace,
    StateCondition,
    StrategicMechanism,
    compile_mechanism_version_space,
)
from .policies import (
    PolicyCondition,
    PolicyObjective,
    PolicySynthesis,
    build_policy_grammar,
    synthesize_policies,
)
from .probes import (
    ProbeAuthority,
    ProbeExecutionReceipt,
    StrategicProbe,
    StrategicProbeAgenda,
    compile_probe_agenda,
    default_probe_adapter_registry,
)
from .transitions import (
    StrategicAction,
    StrategicState,
    StrategicTraceSet,
    StrategicTransition,
    compile_observed_action_system,
)


AUTONOMOUS_SCHEMA = "jaggedthoughts-autonomous-profile-v1"
RUN_STATE_SCHEMA = "jaggedthoughts-autonomous-run-state-v1"


class AutonomousProfileError(ValueError):
    """Raised when an autonomous profile crosses an identity or schema boundary."""


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AutonomousProfileError(f"{label} must be a mapping")
    return value


def _rows(value: Any, label: str) -> tuple[Mapping[str, Any], ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise AutonomousProfileError(f"{label} must be a list")
    return tuple(_mapping(row, f"{label} row") for row in value)


def _text(value: Any, label: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise AutonomousProfileError(f"{label} must be nonempty")
    return result


def _texts(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise AutonomousProfileError(f"{label} must be a nonempty list")
    return tuple(_text(row, f"{label} item") for row in value)


def _finite(value: Any, label: str, *, nonnegative: bool = False) -> float:
    if isinstance(value, bool):
        raise AutonomousProfileError(f"{label} must be numeric")
    number = float(value)
    if not math.isfinite(number) or (nonnegative and number < 0):
        raise AutonomousProfileError(f"{label} has an invalid numeric value")
    return number


def _parse_state(row: Mapping[str, Any], decision_id: str) -> StrategicState:
    payload = dict(row)
    payload.setdefault("decision_id", decision_id)
    return StrategicState.from_mapping(payload)


def _parse_transition(
    row: Mapping[str, Any],
    *,
    states: Mapping[str, StrategicState],
    decision_id: str,
) -> StrategicTransition:
    source_raw = row.get("source")
    target_raw = row.get("target")
    source = (
        states[_text(source_raw, "transition.source")]
        if isinstance(source_raw, str)
        else _parse_state(_mapping(source_raw, "transition.source"), decision_id)
    )
    target = (
        None
        if target_raw is None
        else states[_text(target_raw, "transition.target")]
        if isinstance(target_raw, str)
        else _parse_state(_mapping(target_raw, "transition.target"), decision_id)
    )
    return StrategicTransition(
        transition_id=_text(row.get("id") or row.get("transition_id"), "transition.id"),
        source=source,
        action_id=_text(row.get("action") or row.get("action_id"), "transition.action"),
        target=target,
        occurred_at=_text(row.get("occurred_at"), "transition.occurred_at"),
        evidence_refs=_texts(row.get("evidence_refs"), "transition.evidence_refs"),
        boundary_kind=str(row.get("boundary_kind") or "").strip(),
    )


def _parse_mechanism(row: Mapping[str, Any]) -> StrategicMechanism:
    rules = []
    for rule in _rows(row.get("rules"), "mechanism.rules"):
        rules.append(MechanismRule(
            rule_id=_text(rule.get("id"), "mechanism.rule.id"),
            phase=_text(rule.get("phase"), "mechanism.rule.phase"),  # type: ignore[arg-type]
            action_ids=_texts(rule.get("actions"), "mechanism.rule.actions"),
            actor_id=str(rule.get("actor_id") or ""),
            priority=int(rule.get("priority", 0)),
            conditions=tuple(
                StateCondition(
                    path=_text(condition.get("path"), "rule.condition.path"),
                    operator=_text(
                        condition.get("operator"),
                        "rule.condition.operator",
                    ),  # type: ignore[arg-type]
                    value=_finite(condition.get("value"), "rule.condition.value"),
                )
                for condition in _rows(rule.get("conditions"), "rule.conditions")
            ),
            effects=tuple(
                MechanismEffect(
                    path=_text(effect.get("path"), "rule.effect.path"),
                    delta=_finite(effect.get("delta"), "rule.effect.delta"),
                )
                for effect in _rows(rule.get("effects"), "rule.effects")
            ),
            evidence_refs=_texts(
                rule.get("evidence_refs"),
                "mechanism.rule.evidence_refs",
            ),
        ))
    return StrategicMechanism(
        mechanism_id=_text(row.get("id"), "mechanism.id"),
        description=_text(row.get("description"), "mechanism.description"),
        description_units=int(row.get("description_units", 1)),
        rules=tuple(rules),
        evidence_refs=_texts(
            row.get("evidence_refs"),
            "mechanism.evidence_refs",
        ),
    )


@dataclass(frozen=True, slots=True)
class CompiledAutonomousStrategy:
    profile_id: str
    decision_id: str
    question: str
    evidence_epoch: str
    evidence_manifest: StrategyEvidenceManifest
    states: tuple[tuple[str, StrategicState], ...]
    actions: tuple[StrategicAction, ...]
    traces: StrategicTraceSet
    observed_action_system: Any
    version_space: MechanismVersionSpace
    policy_synthesis: PolicySynthesis | None
    probe_agenda: StrategicProbeAgenda | None
    calibration_receipts: tuple[dict[str, Any], ...]
    temporal_credit_receipt: dict[str, Any] | None
    profile_sha256: str

    @property
    def status(self) -> str:
        if not self.version_space.survivor_ids:
            return "representation_revision_required"
        if self.probe_agenda and self.probe_agenda.selection.status == "selected":
            return "probe_ready"
        if self.policy_synthesis is not None:
            return "policy_frontier_ready"
        return "model_revision_required"

    @property
    def diagnostics(self) -> Any:
        from .diagnostics import diagnose_autonomous_strategy

        return diagnose_autonomous_strategy(self)

    def summary(self) -> dict[str, Any]:
        certificate = (
            self.policy_synthesis.certificate
            if self.policy_synthesis is not None
            else None
        )
        diagnostics = self.diagnostics
        return {
            "profile_id": self.profile_id,
            "decision_id": self.decision_id,
            "question": self.question,
            "status": self.status,
            "profile_sha256": self.profile_sha256,
            "trace_sha256": self.traces.trace_sha256,
            "trace_count": len(self.traces.transitions),
            "mechanism_count": len(self.version_space.mechanisms),
            "survivor_ids": list(self.version_space.survivor_ids),
            "policy_count": (
                len(certificate.target_program_ids) if certificate else 0
            ),
            "frontier_count": (
                len(certificate.frontier_program_ids) if certificate else 0
            ),
            "local_peak_count": (
                len(certificate.local_peak_program_ids) if certificate else 0
            ),
            "scope_closed": certificate.scope_closed if certificate else False,
            "decision_closed": (
                certificate.decision_closed if certificate else False
            ),
            "selected_probe_id": (
                self.probe_agenda.selection.selected_protocol_id
                if self.probe_agenda else ""
            ),
            "calibration_count": len(self.calibration_receipts),
            "temporal_credit_available": self.temporal_credit_receipt is not None,
            "diagnostic_residual_count": len(diagnostics.residuals),
            "next_refinement_action": diagnostics.next_action,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": AUTONOMOUS_SCHEMA,
            "summary": self.summary(),
            "evidence_manifest": self.evidence_manifest.to_dict(),
            "states": {
                state_id: state.to_dict() for state_id, state in self.states
            },
            "actions": [action.to_dict() for action in self.actions],
            "traces": self.traces.to_dict(),
            "observed_action_system": self.observed_action_system.to_receipt(),
            "version_space": self.version_space.to_dict(),
            "policy_synthesis": (
                self.policy_synthesis.to_dict()
                if self.policy_synthesis is not None
                else None
            ),
            "probe_agenda": (
                self.probe_agenda.to_dict()
                if self.probe_agenda is not None
                else None
            ),
            "yield_calibration": list(self.calibration_receipts),
            "temporal_credit": self.temporal_credit_receipt,
            "diagnostics": self.diagnostics.to_dict(),
        }


def _parse_credit(
    payload: Mapping[str, Any],
    appended_chains: Iterable[DecisionEligibilityChain] = (),
) -> tuple[tuple[dict[str, Any], ...], dict[str, Any] | None]:
    block = payload.get("credit")
    credit = _mapping(block, "credit") if block is not None else {}
    chains = (
        *tuple(
            DecisionEligibilityChain.from_receipt(row)
            for row in _rows(credit.get("chains"), "credit.chains")
        ),
        *tuple(appended_chains),
    )
    if not chains:
        return (), None
    calibration = tuple(
        row.to_receipt() for row in compile_decision_yield_calibration(chains)
    )
    by_ref = {chain.chain_ref: chain for chain in chains}
    pairs = tuple(
        (
            by_ref[_text(row.get("left"), "credit.pair.left")],
            by_ref[_text(row.get("right"), "credit.pair.right")],
        )
        for row in _rows(credit.get("pairs"), "credit.pairs")
    )
    temporal = (
        compile_temporal_decision_credit(pairs).to_receipt()
        if pairs
        else None
    )
    return calibration, temporal


def compile_autonomous_profile(
    payload: Mapping[str, Any],
    *,
    source_root: Path,
    appended_transitions: Iterable[StrategicTransition] = (),
    appended_credit_chains: Iterable[DecisionEligibilityChain] = (),
) -> CompiledAutonomousStrategy:
    """Compile one profile through trace, model, policy, and probe layers."""
    if payload.get("schema") != AUTONOMOUS_SCHEMA:
        raise AutonomousProfileError(f"schema must be {AUTONOMOUS_SCHEMA}")
    decision = _mapping(payload.get("decision"), "decision")
    profile_id = _text(payload.get("profile_id"), "profile_id")
    decision_id = _text(decision.get("id"), "decision.id")
    question = _text(decision.get("question"), "decision.question")
    evidence_epoch = _text(decision.get("evidence_epoch"), "decision.evidence_epoch")
    manifest = compile_evidence_manifest(payload, source_root=source_root)
    state_rows = _rows(payload.get("states"), "states")
    state_ids = tuple(_text(row.get("id"), "state.id") for row in state_rows)
    if len(state_ids) != len(set(state_ids)):
        raise AutonomousProfileError("state identities must be unique")
    states = {
        state_id: _parse_state(row, decision_id)
        for state_id, row in zip(state_ids, state_rows, strict=True)
    }
    if not state_rows:
        raise AutonomousProfileError("states must be nonempty")
    actions = tuple(
        StrategicAction(
            action_id=_text(row.get("id"), "action.id"),
            description=_text(row.get("description"), "action.description"),
            primitive_cost=_finite(
                row.get("primitive_cost"),
                "action.primitive_cost",
                nonnegative=True,
            ),
            irreversibility=_finite(
                row.get("irreversibility"),
                "action.irreversibility",
                nonnegative=True,
            ),
            authority_tier=_text(row.get("authority_tier"), "action.authority_tier"),
            evidence_refs=_texts(row.get("evidence_refs"), "action.evidence_refs"),
        )
        for row in _rows(payload.get("actions"), "actions")
    )
    action_by_id = {row.action_id: row for row in actions}
    if len(action_by_id) != len(actions) or not actions:
        raise AutonomousProfileError("action identities must be unique and nonempty")
    declared_transitions = tuple(
        _parse_transition(
            row,
            states=states,
            decision_id=decision_id,
        )
        for row in _rows(payload.get("transitions"), "transitions")
    )
    traces = StrategicTraceSet(
        trace_set_id=f"{profile_id}@{evidence_epoch}",
        transitions=(*declared_transitions, *tuple(appended_transitions)),
    )
    for transition in traces.transitions:
        if transition.action_id not in action_by_id:
            raise AutonomousProfileError(
                f"transition references unknown action: {transition.action_id}"
            )
    models = tuple(
        _parse_mechanism(row)
        for row in _rows(payload.get("mechanisms"), "mechanisms")
    )
    all_paths = set(next(iter(states.values())).paths)
    all_refs = {
        *(ref for action in actions for ref in action.evidence_refs),
        *(ref for transition in traces.transitions for ref in transition.evidence_refs
          if not ref.startswith("observation:")),
        *(ref for model in models for ref in model.evidence_refs),
        *(ref for model in models for rule in model.rules for ref in rule.evidence_refs),
    }
    for model in models:
        for rule in model.rules:
            unknown_actions = set(rule.action_ids) - set(action_by_id)
            if unknown_actions:
                raise AutonomousProfileError(
                    f"mechanism rule references unknown actions: {sorted(unknown_actions)}"
                )
            unknown_paths = {
                *(condition.path for condition in rule.conditions),
                *(effect.path for effect in rule.effects),
            } - all_paths
            if unknown_paths:
                raise AutonomousProfileError(
                    f"mechanism rule references unknown paths: {sorted(unknown_paths)}"
                )
    tolerance = {
        str(path): _finite(value, f"tolerance.{path}", nonnegative=True)
        for path, value in _mapping(
            payload.get("tolerance_by_path") or {},
            "tolerance_by_path",
        ).items()
    }
    version_space = compile_mechanism_version_space(
        models,
        traces,
        tolerance_by_path=tolerance,
    )
    policy_block = _mapping(payload.get("policy"), "policy")
    conditions = tuple(
        PolicyCondition(
            condition_id=_text(row.get("id"), "policy.condition.id"),
            path=_text(row.get("path"), "policy.condition.path"),
            operator=_text(
                row.get("operator"),
                "policy.condition.operator",
            ),  # type: ignore[arg-type]
            value=_finite(row.get("value"), "policy.condition.value"),
            evidence_refs=_texts(
                row.get("evidence_refs"),
                "policy.condition.evidence_refs",
            ),
        )
        for row in _rows(policy_block.get("conditions"), "policy.conditions")
    )
    objectives = tuple(
        PolicyObjective(
            objective_id=_text(row.get("id"), "policy.objective.id"),
            path=_text(row.get("path"), "policy.objective.path"),
            direction=_text(
                row.get("direction"),
                "policy.objective.direction",
            ),  # type: ignore[arg-type]
        )
        for row in _rows(policy_block.get("objectives"), "policy.objectives")
    )
    all_refs.update(
        ref for condition in conditions for ref in condition.evidence_refs
    )
    representation_block = _mapping(
        policy_block.get("representation") or {},
        "policy.representation",
    )
    representation_refs = tuple(
        str(value) for value in representation_block.get("evidence_refs", [])
    )
    all_refs.update(representation_refs)
    representation_status = str(
        representation_block.get("status", "residual")
    )
    default_residuals = (
        ["untried grammar and state-coordinate alternatives"]
        if representation_status == "residual"
        else []
    )
    representation = RepresentationAudit(
        audit_id=_text(
            representation_block.get("id", f"{profile_id}-representation"),
            "policy.representation.id",
        ),
        status=representation_status,  # type: ignore[arg-type]
        residuals=tuple(
            str(value) for value in representation_block.get(
                "residuals",
                default_residuals,
            )
        ),
        evidence_refs=representation_refs,
    )
    synthesis = None
    if version_space.survivors:
        grammar = build_policy_grammar(
            grammar_id=_text(policy_block.get("grammar_id"), "policy.grammar_id"),
            version=_text(policy_block.get("version"), "policy.version"),
            actions=actions,
            conditions=conditions,
        )
        synthesis = synthesize_policies(
            decision_id=decision_id,
            evidence_epoch=evidence_epoch,
            grammar=grammar,
            max_depth=int(policy_block.get("max_depth", 2)),
            max_programs=int(policy_block.get("max_programs", 1000)),
            max_action_steps=int(policy_block.get("max_action_steps", 8)),
            initial_state=states[_text(
                policy_block.get("initial_state"),
                "policy.initial_state",
            )],
            actions=actions,
            conditions=conditions,
            mechanisms=version_space.survivors,
            objectives=objectives,
            representation_audit=representation,
        )
    probe_rows = []
    for row in _rows(payload.get("probes"), "probes"):
        action = action_by_id[_text(row.get("action"), "probe.action")]
        cost_row = _mapping(row.get("cost"), "probe.cost")
        probe = StrategicProbe(
            probe_id=_text(row.get("id"), "probe.id"),
            start_state=states[_text(row.get("start_state"), "probe.start_state")],
            action=action,
            response_paths=_texts(row.get("response_paths"), "probe.response_paths"),
            adapter_id=_text(row.get("adapter"), "probe.adapter"),
            adapter_config=tuple(sorted(
                (str(key), str(value))
                for key, value in _mapping(
                    row.get("adapter_config") or {},
                    "probe.adapter_config",
                ).items()
            )),
            cost=ProtocolCost(
                preparation_execution_units=_finite(
                    cost_row.get("preparation", 0),
                    "probe.cost.preparation",
                    nonnegative=True,
                ),
                probe_execution_units=_finite(
                    cost_row.get("probe"),
                    "probe.cost.probe",
                    nonnegative=True,
                ),
                readout_units=_finite(
                    cost_row.get("readout", 0),
                    "probe.cost.readout",
                    nonnegative=True,
                ),
                control_units=_finite(
                    cost_row.get("control", 0),
                    "probe.cost.control",
                    nonnegative=True,
                ),
                irreversibility_units=_finite(
                    cost_row.get("irreversibility", action.irreversibility),
                    "probe.cost.irreversibility",
                    nonnegative=True,
                ),
            ),
            evidence_refs=_texts(row.get("evidence_refs"), "probe.evidence_refs"),
            novel_context=bool(row.get("novel_context", False)),
        )
        all_refs.update(probe.evidence_refs)
        probe_rows.append(probe)
    if len({probe.probe_id for probe in probe_rows}) != len(probe_rows):
        raise AutonomousProfileError("probe identities must be unique")
    manifest.require_refs(all_refs, context="autonomous strategy profile")
    authority_block = _mapping(payload.get("authority"), "authority")
    authority = ProbeAuthority(
        authority_id=_text(authority_block.get("id"), "authority.id"),
        allowed_adapters=_texts(
            authority_block.get("allowed_adapters"),
            "authority.allowed_adapters",
        ),
        allowed_action_tiers=_texts(
            authority_block.get("allowed_action_tiers"),
            "authority.allowed_action_tiers",
        ),
        max_primitive_execution_units=_finite(
            authority_block.get("max_primitive_execution_units"),
            "authority.max_primitive_execution_units",
            nonnegative=True,
        ),
        max_irreversibility_units=_finite(
            authority_block.get("max_irreversibility_units"),
            "authority.max_irreversibility_units",
            nonnegative=True,
        ),
    )
    agenda = (
        compile_probe_agenda(
            probe_rows,
            version_space=version_space,
            authority=authority,
        )
        if probe_rows and version_space.survivors
        else None
    )
    calibration, temporal = _parse_credit(payload, appended_credit_chains)
    profile_sha = stable_sha256({
        "schema": AUTONOMOUS_SCHEMA,
        "payload": payload,
        "evidence_manifest_sha256": manifest.manifest_sha256,
    })
    return CompiledAutonomousStrategy(
        profile_id=profile_id,
        decision_id=decision_id,
        question=question,
        evidence_epoch=evidence_epoch,
        evidence_manifest=manifest,
        states=tuple(sorted(states.items())),
        actions=actions,
        traces=traces,
        observed_action_system=compile_observed_action_system(traces),
        version_space=version_space,
        policy_synthesis=synthesis,
        probe_agenda=agenda,
        calibration_receipts=calibration,
        temporal_credit_receipt=temporal,
        profile_sha256=profile_sha,
    )


@dataclass(frozen=True, slots=True)
class AutonomousRunState:
    profile_sha256: str
    observed_transitions: tuple[StrategicTransition, ...]
    execution_receipts: tuple[dict[str, Any], ...]
    eligibility_edges: tuple[dict[str, Any], ...]
    eligibility_chains: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": RUN_STATE_SCHEMA,
            "profile_sha256": self.profile_sha256,
            "observed_transitions": [
                transition.to_dict() for transition in self.observed_transitions
            ],
            "execution_receipts": list(self.execution_receipts),
            "eligibility_edges": list(self.eligibility_edges),
            "eligibility_chains": list(self.eligibility_chains),
        }
        return {**payload, "run_state_sha256": stable_sha256(payload)}


@dataclass(frozen=True, slots=True)
class AutonomousStep:
    before: CompiledAutonomousStrategy
    execution: ProbeExecutionReceipt | None
    after: CompiledAutonomousStrategy
    run_state: AutonomousRunState

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "jaggedthoughts-autonomous-step-v1",
            "before": self.before.summary(),
            "execution": self.execution.to_dict() if self.execution else None,
            "after": self.after.summary(),
            "run_state": self.run_state.to_dict(),
        }


def _load_payload(path: Path) -> Mapping[str, Any]:
    text = path.read_text(encoding="utf-8")
    parsed = json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)
    return _mapping(parsed, "profile")


def load_run_state(
    path: Path | None,
    *,
    decision_id: str,
) -> AutonomousRunState | None:
    if path is None or not path.is_file():
        return None
    payload = _mapping(json.loads(path.read_text(encoding="utf-8")), "run state")
    if payload.get("schema") != RUN_STATE_SCHEMA:
        raise AutonomousProfileError("run-state schema mismatch")
    transitions = tuple(
        _parse_transition(row, states={}, decision_id=decision_id)
        for row in _rows(payload.get("observed_transitions"), "observed_transitions")
    )
    return AutonomousRunState(
        profile_sha256=_text(payload.get("profile_sha256"), "run_state.profile_sha256"),
        observed_transitions=transitions,
        execution_receipts=tuple(
            dict(row) for row in _rows(
                payload.get("execution_receipts"),
                "execution_receipts",
            )
        ),
        eligibility_edges=tuple(
            dict(row) for row in _rows(
                payload.get("eligibility_edges"),
                "eligibility_edges",
            )
        ),
        eligibility_chains=tuple(
            dict(row) for row in _rows(
                payload.get("eligibility_chains"),
                "eligibility_chains",
            )
        ),
    )


def compile_autonomous_profile_file(
    path: str | Path,
    *,
    run_state_path: str | Path | None = None,
) -> CompiledAutonomousStrategy:
    source = Path(path)
    payload = _load_payload(source)
    decision = _mapping(payload.get("decision"), "decision")
    run_state = load_run_state(
        Path(run_state_path) if run_state_path else None,
        decision_id=_text(decision.get("id"), "decision.id"),
    )
    compiled = compile_autonomous_profile(
        payload,
        source_root=source.parent,
        appended_transitions=(
            run_state.observed_transitions if run_state is not None else ()
        ),
        appended_credit_chains=(
            tuple(
                DecisionEligibilityChain.from_receipt(row)
                for row in run_state.eligibility_chains
            )
            if run_state is not None else ()
        ),
    )
    if run_state is not None and run_state.profile_sha256 != compiled.profile_sha256:
        raise AutonomousProfileError("run state belongs to another profile identity")
    return compiled


def run_autonomous_step(
    profile_path: str | Path,
    *,
    run_state_path: str | Path | None = None,
    adapter_root: str | Path | None = None,
) -> AutonomousStep:
    """Execute only the selected registered probe and recompile from its readout."""
    source = Path(profile_path)
    payload = _load_payload(source)
    decision_id = _text(
        _mapping(payload.get("decision"), "decision").get("id"),
        "decision.id",
    )
    previous = load_run_state(
        Path(run_state_path) if run_state_path else None,
        decision_id=decision_id,
    )
    before = compile_autonomous_profile(
        payload,
        source_root=source.parent,
        appended_transitions=(
            previous.observed_transitions if previous else ()
        ),
        appended_credit_chains=(
            tuple(
                DecisionEligibilityChain.from_receipt(row)
                for row in previous.eligibility_chains
            )
            if previous else ()
        ),
    )
    if previous and previous.profile_sha256 != before.profile_sha256:
        raise AutonomousProfileError("run state belongs to another profile identity")
    probe = before.probe_agenda.selected_probe if before.probe_agenda else None
    if probe is None:
        state = previous or AutonomousRunState(
            before.profile_sha256,
            (),
            (),
            (),
            (),
        )
        return AutonomousStep(before, None, before, state)
    receipt = default_probe_adapter_registry().execute(
        probe,
        authority=before.probe_agenda.authority,
        adapter_root=Path(adapter_root) if adapter_root else source.parent,
    )
    old_transitions = previous.observed_transitions if previous else ()
    new_transitions = (
        (*old_transitions, receipt.observed_transition)
        if receipt.observed_transition is not None
        else old_transitions
    )
    after_without_credit = compile_autonomous_profile(
        payload,
        source_root=source.parent,
        appended_transitions=new_transitions,
    )
    old_receipts = previous.execution_receipts if previous else ()
    old_edges = previous.eligibility_edges if previous else ()
    old_chains = previous.eligibility_chains if previous else ()
    edges = old_edges
    chains = old_chains
    if receipt.observed_transition is not None:
        selected = before.probe_agenda.selection.selected
        if selected is None:
            raise AssertionError("selected probe price is missing")
        available = tuple(row.probe_sha256 for row in before.probe_agenda.probes)
        authority = DecisionChoiceAuthority(
            task_contract_sha256=before.profile_sha256,
            decision_namespace=before.decision_id,
            choice_context_sha256=before.version_space.version_space_sha256,
            continuation_context_sha256=(
                before.policy_synthesis.synthesis_sha256
                if before.policy_synthesis else stable_sha256("no-policy")
            ),
            available_option_family_sha256s=available,
        )
        observed_yield = math.log2(
            len(before.version_space.survivors)
            / max(1, len(after_without_credit.version_space.survivors))
        )
        edge = DecisionEligibilityEdge(
            chain_ref=f"probe-chain::{len(old_edges)}",
            edge_index=0,
            authority=authority,
            chosen_option_family_sha256=probe.probe_sha256,
            chosen_option_variant_sha256=stable_sha256({
                "adapter_id": probe.adapter_id,
                "adapter_config": probe.adapter_config,
            }),
            successor_decision_state_sha256=(
                after_without_credit.version_space.version_space_sha256
            ),
            predicted_information_yield=selected.identification,
            observed_information_yield=observed_yield,
            information_yield_measure_sha256=stable_sha256(
                "log2-version-space-contraction-v1"
            ),
            primitive_action_cost=probe.cost.primitive_execution_units,
            immediate_task_status="open",
            evidence_ref=f"probe-execution:{receipt.to_dict()['receipt_sha256']}",
        )
        edges = (*old_edges, edge.to_receipt())
        chain = DecisionEligibilityChain(
            chain_ref=edge.chain_ref,
            matched_pair_ref=f"unmatched::{authority.sha256}",
            arm_id=probe.probe_id,
            continuation_policy_sha256=authority.continuation_context_sha256,
            edges=(edge,),
            terminal_task_status="open",
            terminal_adjudication_ref=(
                f"pending:{receipt.to_dict()['receipt_sha256']}"
            ),
        )
        chains = (*old_chains, chain.to_receipt())
    after = compile_autonomous_profile(
        payload,
        source_root=source.parent,
        appended_transitions=new_transitions,
        appended_credit_chains=tuple(
            DecisionEligibilityChain.from_receipt(row) for row in chains
        ),
    )
    state = AutonomousRunState(
        profile_sha256=before.profile_sha256,
        observed_transitions=tuple(new_transitions),
        execution_receipts=(*old_receipts, receipt.to_dict()),
        eligibility_edges=tuple(edges),
        eligibility_chains=tuple(chains),
    )
    return AutonomousStep(before, receipt, after, state)


__all__ = [
    "AUTONOMOUS_SCHEMA",
    "RUN_STATE_SCHEMA",
    "AutonomousProfileError",
    "AutonomousRunState",
    "AutonomousStep",
    "CompiledAutonomousStrategy",
    "compile_autonomous_profile",
    "compile_autonomous_profile_file",
    "load_run_state",
    "run_autonomous_step",
]
