"""Counterexample-guided diagnostics for autonomous strategy representations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

from ztare.common.equivariance import stable_sha256

if TYPE_CHECKING:
    from .autonomy import CompiledAutonomousStrategy


@dataclass(frozen=True, slots=True)
class StrategyRepresentationResidual:
    residual_id: str
    kind: str
    priority: int
    evidence_refs: tuple[str, ...]
    counterexample: str
    required_refinement: str
    kill_test: str
    structural_analogue: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "residual_id": self.residual_id,
            "kind": self.kind,
            "priority": self.priority,
            "evidence_refs": list(self.evidence_refs),
            "counterexample": self.counterexample,
            "required_refinement": self.required_refinement,
            "kill_test": self.kill_test,
            "structural_analogue": self.structural_analogue,
        }


@dataclass(frozen=True, slots=True)
class StrategyDiagnosticReport:
    status: str
    next_action: str
    next_action_reason: str
    residuals: tuple[StrategyRepresentationResidual, ...]
    diagnostic_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "jaggedthoughts-strategy-diagnostics-v1",
            "status": self.status,
            "next_action": self.next_action,
            "next_action_reason": self.next_action_reason,
            "residual_count": len(self.residuals),
            "residuals": [row.to_dict() for row in self.residuals],
            "diagnostic_sha256": self.diagnostic_sha256,
        }


def _target_signature(compiled: CompiledAutonomousStrategy) -> tuple[str, ...]:
    return tuple(
        sorted(
            transition.target.state_sha256
            for transition in compiled.traces.transitions
            if transition.target is not None
        )
    )


def _aliasing_residuals(
    compiled: CompiledAutonomousStrategy,
) -> tuple[StrategyRepresentationResidual, ...]:
    groups: dict[tuple[str, str], list[Any]] = {}
    for transition in compiled.traces.transitions:
        if transition.target is None:
            continue
        groups.setdefault(
            (transition.source.state_sha256, transition.action_id),
            [],
        ).append(transition)
    residuals = []
    for (source_sha, action_id), rows in sorted(groups.items()):
        targets = {row.target.state_sha256 for row in rows if row.target is not None}
        if len(targets) <= 1:
            continue
        refs = tuple(sorted({
            ref for row in rows for ref in row.evidence_refs
        }))
        residuals.append(StrategyRepresentationResidual(
            residual_id=stable_sha256({
                "kind": "transition_nonfunctionality",
                "source": source_sha,
                "action": action_id,
                "targets": sorted(targets),
            }),
            kind="transition_nonfunctionality",
            priority=100,
            evidence_refs=refs,
            counterexample=(
                f"encoded source {source_sha[:12]} under action {action_id} "
                f"has {len(targets)} observed successors; the current encoding "
                "makes the transition multivalued"
            ),
            required_refinement=(
                "split the state chart with a pre-action discriminator, "
                "declare a stochastic transition family, or open a new epoch "
                "for regime or action-identity drift"
            ),
            kill_test=(
                "withheld repetitions conditioned on the new coordinate or "
                "noise family predict successor frequencies inside tolerance"
            ),
            structural_analogue="CEGAR spurious-abstraction witness",
        ))
    return tuple(residuals)


def diagnose_autonomous_strategy(
    compiled: CompiledAutonomousStrategy,
) -> StrategyDiagnosticReport:
    """Compile observed failures into ordered representation-repair contracts."""
    residuals = list(_aliasing_residuals(compiled))
    version_space = compiled.version_space
    if not version_space.survivors:
        evidence_refs = tuple(sorted({
            ref
            for transition in compiled.traces.transitions
            for ref in transition.evidence_refs
        }))
        residuals.append(StrategyRepresentationResidual(
            residual_id=stable_sha256({
                "kind": "mechanism_language_exhausted",
                "version_space": version_space.version_space_sha256,
            }),
            kind="mechanism_language_exhausted",
            priority=95,
            evidence_refs=evidence_refs,
            counterexample="every executable mechanism is refuted by trace replay",
            required_refinement=(
                "add a mechanism rule family, revise the state chart, or "
                "justify a wider measurement tolerance from source evidence"
            ),
            kill_test=(
                "a revised candidate replays current traces and predicts a "
                "concealed future transition better than the baseline"
            ),
            structural_analogue="CEGIS grammar counterexample",
        ))
    agenda = compiled.probe_agenda
    if (
        len(version_space.survivors) > 1
        and (
            agenda is None
            or agenda.selection.status != "selected"
        )
    ):
        residuals.append(StrategyRepresentationResidual(
            residual_id=stable_sha256({
                "kind": "committee_probe_deadlock",
                "version_space": version_space.version_space_sha256,
            }),
            kind="committee_probe_deadlock",
            priority=90,
            evidence_refs=tuple(sorted({
                ref for model in version_space.survivors
                for ref in model.evidence_refs
            })),
            counterexample=(
                f"{len(version_space.survivors)} mechanisms survive, while "
                "no admitted probe separates their predicted responses"
            ),
            required_refinement=(
                "add a response coordinate, longer-horizon probe, new reversible "
                "action, or quotient the committee under decision equivalence"
            ),
            kill_test=(
                "the revised probe set induces at least two response cells "
                "inside the same authority envelope"
            ),
            structural_analogue="active learning identifiability failure",
        ))
    synthesis = compiled.policy_synthesis
    if synthesis is not None:
        certificate = synthesis.certificate
        if not synthesis.enumeration.exhausted_within_scope:
            residuals.append(StrategyRepresentationResidual(
                residual_id=stable_sha256({
                    "kind": "policy_enumeration_truncated",
                    "enumeration": synthesis.enumeration.enumeration_digest,
                }),
                kind="policy_enumeration_truncated",
                priority=80,
                evidence_refs=tuple(sorted({
                    ref for row in synthesis.evaluations
                    for ref in row.evidence_refs
                })),
                counterexample="the policy budget ended before grammar exhaustion",
                required_refinement=(
                    "increase a justified bound, factor independent policy "
                    "components, or add a certified behavioral quotient"
                ),
                kill_test=(
                    "the revised enumeration exhausts its declared scope with "
                    "stable frontier behavior"
                ),
                structural_analogue="symbolic-search state explosion",
            ))
        target_count = len(certificate.target_program_ids)
        frontier_count = len(certificate.frontier_program_ids)
        if target_count >= 20 and frontier_count / target_count >= 0.5:
            residuals.append(StrategyRepresentationResidual(
                residual_id=stable_sha256({
                    "kind": "frontier_saturation",
                    "scope": certificate.scope.scope_id,
                    "target_count": target_count,
                    "frontier_count": frontier_count,
                }),
                kind="frontier_saturation",
                priority=70,
                evidence_refs=tuple(sorted({
                    ref for row in synthesis.evaluations
                    for ref in row.evidence_refs
                })),
                counterexample=(
                    f"{frontier_count} of {target_count} policies remain "
                    "non-dominated"
                ),
                required_refinement=(
                    "add decision constraints, improve consequence resolution, "
                    "or declare a choice rule without collapsing objectives"
                ),
                kill_test=(
                    "the added distinction removes policies prospectively and "
                    "preserves withheld expert choices"
                ),
                structural_analogue="partial-order antichain saturation",
            ))
        audit = certificate.representation_audit
        for detail in audit.residuals:
            residuals.append(StrategyRepresentationResidual(
                residual_id=stable_sha256({
                    "kind": "declared_representation_residual",
                    "audit_id": audit.audit_id,
                    "detail": detail,
                }),
                kind="declared_representation_residual",
                priority=60,
                evidence_refs=audit.evidence_refs,
                counterexample=detail,
                required_refinement=(
                    "author a challenger state, action, objective, condition, "
                    "or mechanism epoch that directly addresses this residual"
                ),
                kill_test=(
                    "compare challenger and incumbent behavior on the same "
                    "evidence epoch and combined frontier"
                ),
                structural_analogue="counterexample-guided abstraction refinement",
            ))
    for calibration in compiled.calibration_receipts:
        if (
            int(calibration.get("observation_count", 0)) >= 2
            and float(calibration.get("mean_absolute_error", 0.0)) > 0.5
        ):
            residuals.append(StrategyRepresentationResidual(
                residual_id=stable_sha256({
                    "kind": "probe_yield_miscalibration",
                    "calibration": calibration.get("sha256"),
                }),
                kind="probe_yield_miscalibration",
                priority=50,
                evidence_refs=tuple(calibration.get("evidence_refs", ())),
                counterexample=(
                    "observed information yield differs materially from "
                    "the probe selector's prediction"
                ),
                required_refinement=(
                    "recalibrate response partitions or protocol costs for this "
                    "exact decision authority"
                ),
                kill_test=(
                    "prospective calibration error falls below the declared "
                    "decision threshold"
                ),
                structural_analogue="forecast calibration failure",
            ))
    residuals.sort(key=lambda row: (-row.priority, row.kind, row.residual_id))

    kinds = {row.kind for row in residuals}
    if "transition_nonfunctionality" in kinds:
        next_action = "refine_state_chart"
        reason = "one encoded state-action pair has incompatible successors"
    elif "mechanism_language_exhausted" in kinds:
        next_action = "extend_mechanism_language"
        reason = "the current mechanism grammar explains no complete trace set"
    elif agenda is not None and agenda.selection.status == "selected":
        next_action = "execute_selected_probe"
        reason = f"probe {agenda.selection.selected_protocol_id} separates live models"
    elif "committee_probe_deadlock" in kinds:
        next_action = "extend_probe_language"
        reason = "the live model committee is indistinguishable under admitted probes"
    elif "policy_enumeration_truncated" in kinds:
        next_action = "factor_policy_grammar"
        reason = "frontier coverage is blocked by the enumeration bound"
    elif "frontier_saturation" in kinds:
        next_action = "refine_decision_surface"
        reason = "the Pareto antichain is too broad for the declared decision surface"
    elif "declared_representation_residual" in kinds:
        next_action = "author_representation_challenger"
        reason = "the current audit names an unresolved strategic distinction"
    elif synthesis is not None and synthesis.certificate.frontier_program_ids:
        next_action = "external_policy_choice"
        reason = "the bounded frontier is ready for the declared decision authority"
    else:
        next_action = "collect_transition_evidence"
        reason = "the current evidence does not support a policy frontier"

    payload = {
        "status": "residual" if residuals else "clear_within_declared_surface",
        "next_action": next_action,
        "next_action_reason": reason,
        "residuals": [row.to_dict() for row in residuals],
        "trace_targets": _target_signature(compiled),
    }
    return StrategyDiagnosticReport(
        status=payload["status"],
        next_action=next_action,
        next_action_reason=reason,
        residuals=tuple(residuals),
        diagnostic_sha256=stable_sha256(payload),
    )


__all__ = [
    "StrategyDiagnosticReport",
    "StrategyRepresentationResidual",
    "diagnose_autonomous_strategy",
]
