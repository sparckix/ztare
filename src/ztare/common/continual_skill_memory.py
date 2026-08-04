"""Durable composition state for continual guarded-skill learning.

The existing guarded compiler correctly owns one immutable evidence snapshot:
it discovers repeated words, binds guards, records side exits, and falls back
to primitives.  Continual learning has a different lifecycle.  Additional
evidence should revise a skill without changing the identity of the skill
family, externally adjudicated outcomes should calibrate future judgment, and
an explicit isomorphism should reduce the demonstrations needed in a new
operation algebra.

This module keeps those identities separate:

* a *family* is an operation word inside a caller-owned operation namespace;
* a *revision* is one evidence-bound ``GuardedSkillProgram``;
* a *task experience* is an externally labeled process-token sequence;
* a *choice experience* binds one effect option to its local context and
  available alternatives;
* a *decision experience* binds a controller-level option to the complete
  choice set at the point where the controller selected it;
* causal credit is admitted only from a matched one-edit outcome contrast;
* a transported family remains non-executable until one local guard witness.

No boundary kind implies task success.  No unpaired outcome receives causal
credit.  Transport never copies task outcome authority.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import json
import os
from pathlib import Path
from typing import Any, Callable, Hashable, Iterable, Mapping

from ztare.common.equivariance import stable_sha256
from ztare.common.guarded_skill_compiler import (
    GuardedActionTrace,
    GuardedSkillLibrary,
    GuardedSkillProgram,
    SkillOccurrence,
    SkillVariant,
)


MEMORY_SCHEMA = "ztare-continual-skill-memory-v1"
OUTCOME_CLASSES = frozenset({"attained", "open", "failed"})
INTRINSIC_SIGNAL_KINDS = frozenset({
    "mdl_admission",
    "quotient_transport",
    "cegar_counterexample",
    "guard_side_exit",
    "local_guard_validation",
})
INTRINSIC_DISPOSITIONS = frozenset({
    "supports_reuse",
    "requires_refinement",
    "requires_fallback",
})


def _nonempty(value: str, name: str) -> str:
    result = str(value).strip()
    if not result:
        raise ValueError(f"{name} must be nonempty")
    return result


def _sorted_unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value) for value in values if str(value)}))


def _operation_family_sha256(
    operation_namespace: str,
    operations: Iterable[Hashable],
) -> str:
    namespace = _nonempty(operation_namespace, "operation_namespace")
    return stable_sha256({
        "schema": "ztare-guarded-skill-family-v1",
        "operation_namespace": namespace,
        "operations": tuple(operations),
    })


@dataclass(frozen=True)
class SkillFamilyMemory:
    """Append-only evidence history for one stable skill family."""

    family_sha256: str
    operation_namespace: str
    operation_sha256s: tuple[str, ...]
    operation_reprs: tuple[str, ...]
    revision_sha256s: tuple[str, ...] = ()
    context_sha256s: tuple[str, ...] = ()
    trace_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    transferred_from_sha256s: tuple[str, ...] = ()
    local_validation_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _nonempty(self.family_sha256, "family_sha256")
        _nonempty(self.operation_namespace, "operation_namespace")
        if not self.operation_sha256s:
            raise ValueError("skill families require operations")
        if len(self.operation_sha256s) != len(self.operation_reprs):
            raise ValueError("operation digests and representations must align")
        for name in (
            "revision_sha256s",
            "context_sha256s",
            "trace_refs",
            "evidence_refs",
            "transferred_from_sha256s",
            "local_validation_refs",
        ):
            values = getattr(self, name)
            if values != _sorted_unique(values):
                raise ValueError(f"{name} must be unique and canonical")

    @property
    def independent_trace_support(self) -> int:
        return len(self.trace_refs)

    @property
    def context_support(self) -> int:
        return len(self.context_sha256s)

    @property
    def cross_context_reused(self) -> bool:
        return self.context_support > 1 or bool(self.transferred_from_sha256s)

    def to_dict(self) -> dict[str, Any]:
        return {
            "family_sha256": self.family_sha256,
            "operation_namespace": self.operation_namespace,
            "operation_sha256s": list(self.operation_sha256s),
            "operation_reprs": list(self.operation_reprs),
            "revision_sha256s": list(self.revision_sha256s),
            "context_sha256s": list(self.context_sha256s),
            "trace_refs": list(self.trace_refs),
            "evidence_refs": list(self.evidence_refs),
            "transferred_from_sha256s": list(
                self.transferred_from_sha256s
            ),
            "local_validation_refs": list(self.local_validation_refs),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SkillFamilyMemory":
        return cls(
            family_sha256=str(payload["family_sha256"]),
            operation_namespace=str(payload["operation_namespace"]),
            operation_sha256s=tuple(map(str, payload["operation_sha256s"])),
            operation_reprs=tuple(map(str, payload["operation_reprs"])),
            revision_sha256s=tuple(map(str, payload.get(
                "revision_sha256s", ()
            ))),
            context_sha256s=tuple(map(str, payload.get(
                "context_sha256s", ()
            ))),
            trace_refs=tuple(map(str, payload.get("trace_refs", ()))),
            evidence_refs=tuple(map(str, payload.get("evidence_refs", ()))),
            transferred_from_sha256s=tuple(map(str, payload.get(
                "transferred_from_sha256s", ()
            ))),
            local_validation_refs=tuple(map(str, payload.get(
                "local_validation_refs", ()
            ))),
        )


@dataclass(frozen=True)
class TaskExperience:
    """One authority-labeled process presentation."""

    task_contract_sha256: str
    trace_ref: str
    outcome: str
    process_tokens: tuple[str, ...]
    evidence_ref: str
    context_sha256: str

    def __post_init__(self) -> None:
        _nonempty(self.task_contract_sha256, "task_contract_sha256")
        _nonempty(self.trace_ref, "trace_ref")
        _nonempty(self.evidence_ref, "evidence_ref")
        _nonempty(self.context_sha256, "context_sha256")
        if self.outcome not in OUTCOME_CLASSES:
            raise ValueError(
                f"task outcome must be one of {sorted(OUTCOME_CLASSES)}"
            )
        if not self.process_tokens:
            raise ValueError("task experiences require process tokens")
        if any(not str(token).strip() for token in self.process_tokens):
            raise ValueError("process token identities must be nonempty")

    @property
    def experience_sha256(self) -> str:
        return stable_sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_contract_sha256": self.task_contract_sha256,
            "trace_ref": self.trace_ref,
            "outcome": self.outcome,
            "process_tokens": list(self.process_tokens),
            "evidence_ref": self.evidence_ref,
            "context_sha256": self.context_sha256,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TaskExperience":
        return cls(
            task_contract_sha256=str(payload["task_contract_sha256"]),
            trace_ref=str(payload["trace_ref"]),
            outcome=str(payload["outcome"]),
            process_tokens=tuple(map(str, payload["process_tokens"])),
            evidence_ref=str(payload["evidence_ref"]),
            context_sha256=str(payload["context_sha256"]),
        )


@dataclass(frozen=True)
class TaskOptionChoiceExperience:
    """One externally labeled option choice in a replayable local context."""

    task_contract_sha256: str
    trace_ref: str
    choice_index: int
    outcome: str
    choice_context_sha256: str
    continuation_context_sha256: str
    chosen_effect_option_family_sha256: str
    chosen_effect_option_variant_sha256: str
    available_effect_option_family_sha256s: tuple[str, ...]
    evidence_ref: str

    def __post_init__(self) -> None:
        for name in (
            "task_contract_sha256",
            "trace_ref",
            "choice_context_sha256",
            "continuation_context_sha256",
            "chosen_effect_option_family_sha256",
            "chosen_effect_option_variant_sha256",
            "evidence_ref",
        ):
            _nonempty(getattr(self, name), name)
        if self.choice_index < 0:
            raise ValueError("choice_index must be nonnegative")
        if self.outcome not in OUTCOME_CLASSES:
            raise ValueError(
                f"task outcome must be one of {sorted(OUTCOME_CLASSES)}"
            )
        available = self.available_effect_option_family_sha256s
        if available != _sorted_unique(available):
            raise ValueError(
                "available effect-option families must be unique and canonical"
            )
        if self.chosen_effect_option_family_sha256 not in available:
            raise ValueError(
                "chosen effect-option family must belong to the choice set"
            )

    @property
    def experience_sha256(self) -> str:
        return stable_sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_contract_sha256": self.task_contract_sha256,
            "trace_ref": self.trace_ref,
            "choice_index": self.choice_index,
            "outcome": self.outcome,
            "choice_context_sha256": self.choice_context_sha256,
            "continuation_context_sha256": (
                self.continuation_context_sha256
            ),
            "chosen_effect_option_family_sha256": (
                self.chosen_effect_option_family_sha256
            ),
            "chosen_effect_option_variant_sha256": (
                self.chosen_effect_option_variant_sha256
            ),
            "available_effect_option_family_sha256s": list(
                self.available_effect_option_family_sha256s
            ),
            "evidence_ref": self.evidence_ref,
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> "TaskOptionChoiceExperience":
        return cls(
            task_contract_sha256=str(payload["task_contract_sha256"]),
            trace_ref=str(payload["trace_ref"]),
            choice_index=int(payload["choice_index"]),
            outcome=str(payload["outcome"]),
            choice_context_sha256=str(payload["choice_context_sha256"]),
            continuation_context_sha256=str(
                payload["continuation_context_sha256"]
            ),
            chosen_effect_option_family_sha256=str(
                payload["chosen_effect_option_family_sha256"]
            ),
            chosen_effect_option_variant_sha256=str(
                payload["chosen_effect_option_variant_sha256"]
            ),
            available_effect_option_family_sha256s=tuple(map(
                str,
                payload["available_effect_option_family_sha256s"],
            )),
            evidence_ref=str(payload["evidence_ref"]),
        )


@dataclass(frozen=True)
class TaskDecisionChoiceExperience:
    """One externally labeled controller decision at its selection boundary."""

    task_contract_sha256: str
    trace_ref: str
    choice_index: int
    outcome: str
    decision_namespace: str
    choice_context_sha256: str
    continuation_context_sha256: str
    chosen_option_family_sha256: str
    chosen_option_variant_sha256: str
    available_option_family_sha256s: tuple[str, ...]
    evidence_ref: str

    def __post_init__(self) -> None:
        for name in (
            "task_contract_sha256",
            "trace_ref",
            "decision_namespace",
            "choice_context_sha256",
            "continuation_context_sha256",
            "chosen_option_family_sha256",
            "chosen_option_variant_sha256",
            "evidence_ref",
        ):
            _nonempty(getattr(self, name), name)
        if self.choice_index < 0:
            raise ValueError("choice_index must be nonnegative")
        if self.outcome not in OUTCOME_CLASSES:
            raise ValueError(
                f"task outcome must be one of {sorted(OUTCOME_CLASSES)}"
            )
        available = self.available_option_family_sha256s
        if available != _sorted_unique(available):
            raise ValueError(
                "available decision-option families must be unique and "
                "canonical"
            )
        if self.chosen_option_family_sha256 not in available:
            raise ValueError(
                "chosen decision-option family must belong to the choice set"
            )

    @property
    def experience_sha256(self) -> str:
        return stable_sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_contract_sha256": self.task_contract_sha256,
            "trace_ref": self.trace_ref,
            "choice_index": self.choice_index,
            "outcome": self.outcome,
            "decision_namespace": self.decision_namespace,
            "choice_context_sha256": self.choice_context_sha256,
            "continuation_context_sha256": (
                self.continuation_context_sha256
            ),
            "chosen_option_family_sha256": (
                self.chosen_option_family_sha256
            ),
            "chosen_option_variant_sha256": (
                self.chosen_option_variant_sha256
            ),
            "available_option_family_sha256s": list(
                self.available_option_family_sha256s
            ),
            "evidence_ref": self.evidence_ref,
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> "TaskDecisionChoiceExperience":
        return cls(
            task_contract_sha256=str(payload["task_contract_sha256"]),
            trace_ref=str(payload["trace_ref"]),
            choice_index=int(payload["choice_index"]),
            outcome=str(payload["outcome"]),
            decision_namespace=str(payload["decision_namespace"]),
            choice_context_sha256=str(payload["choice_context_sha256"]),
            continuation_context_sha256=str(
                payload["continuation_context_sha256"]
            ),
            chosen_option_family_sha256=str(
                payload["chosen_option_family_sha256"]
            ),
            chosen_option_variant_sha256=str(
                payload["chosen_option_variant_sha256"]
            ),
            available_option_family_sha256s=tuple(map(
                str,
                payload["available_option_family_sha256s"],
            )),
            evidence_ref=str(payload["evidence_ref"]),
        )


@dataclass(frozen=True)
class CausalCreditWitness:
    """A token isolated by one matched positive/nonpositive edit."""

    task_contract_sha256: str
    direction: str
    process_token: str
    edit_index: int
    positive_experience_sha256: str
    contrast_experience_sha256: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.direction not in {"enables", "hazard"}:
            raise ValueError("credit direction must be enables or hazard")
        if self.edit_index < 0:
            raise ValueError("credit edit_index must be nonnegative")

    @property
    def witness_sha256(self) -> str:
        return stable_sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_contract_sha256": self.task_contract_sha256,
            "direction": self.direction,
            "process_token": self.process_token,
            "edit_index": self.edit_index,
            "positive_experience_sha256": self.positive_experience_sha256,
            "contrast_experience_sha256": self.contrast_experience_sha256,
            "evidence_refs": list(self.evidence_refs),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CausalCreditWitness":
        return cls(
            task_contract_sha256=str(payload["task_contract_sha256"]),
            direction=str(payload["direction"]),
            process_token=str(payload["process_token"]),
            edit_index=int(payload["edit_index"]),
            positive_experience_sha256=str(
                payload["positive_experience_sha256"]
            ),
            contrast_experience_sha256=str(
                payload["contrast_experience_sha256"]
            ),
            evidence_refs=tuple(map(str, payload["evidence_refs"])),
        )


@dataclass(frozen=True)
class SkillTransportMemory:
    """Persistent lineage for one locally validated operation transport."""

    source_family_sha256: str
    source_revision_sha256: str
    target_family_sha256: str
    target_revision_sha256: str
    source_operation_namespace: str
    target_operation_namespace: str
    source_operation_sha256s: tuple[str, ...]
    target_operation_sha256s: tuple[str, ...]
    source_operation_reprs: tuple[str, ...]
    target_operation_reprs: tuple[str, ...]
    context_sha256: str
    validation_trace_ref: str
    validation_trace_sha256: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "source_family_sha256",
            "source_revision_sha256",
            "target_family_sha256",
            "target_revision_sha256",
            "source_operation_namespace",
            "target_operation_namespace",
            "context_sha256",
            "validation_trace_ref",
            "validation_trace_sha256",
        ):
            _nonempty(getattr(self, name), name)
        lengths = {
            len(self.source_operation_sha256s),
            len(self.target_operation_sha256s),
            len(self.source_operation_reprs),
            len(self.target_operation_reprs),
        }
        if len(lengths) != 1 or next(iter(lengths), 0) == 0:
            raise ValueError(
                "transport operation identities must be nonempty and aligned"
            )
        if self.evidence_refs != _sorted_unique(self.evidence_refs):
            raise ValueError("transport evidence refs must be canonical")

    @property
    def transport_sha256(self) -> str:
        return stable_sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_family_sha256": self.source_family_sha256,
            "source_revision_sha256": self.source_revision_sha256,
            "target_family_sha256": self.target_family_sha256,
            "target_revision_sha256": self.target_revision_sha256,
            "source_operation_namespace": self.source_operation_namespace,
            "target_operation_namespace": self.target_operation_namespace,
            "source_operation_sha256s": list(
                self.source_operation_sha256s
            ),
            "target_operation_sha256s": list(
                self.target_operation_sha256s
            ),
            "source_operation_reprs": list(self.source_operation_reprs),
            "target_operation_reprs": list(self.target_operation_reprs),
            "context_sha256": self.context_sha256,
            "validation_trace_ref": self.validation_trace_ref,
            "validation_trace_sha256": self.validation_trace_sha256,
            "evidence_refs": list(self.evidence_refs),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SkillTransportMemory":
        return cls(
            source_family_sha256=str(payload["source_family_sha256"]),
            source_revision_sha256=str(payload["source_revision_sha256"]),
            target_family_sha256=str(payload["target_family_sha256"]),
            target_revision_sha256=str(payload["target_revision_sha256"]),
            source_operation_namespace=str(
                payload["source_operation_namespace"]
            ),
            target_operation_namespace=str(
                payload["target_operation_namespace"]
            ),
            source_operation_sha256s=tuple(map(
                str,
                payload["source_operation_sha256s"],
            )),
            target_operation_sha256s=tuple(map(
                str,
                payload["target_operation_sha256s"],
            )),
            source_operation_reprs=tuple(map(
                str,
                payload["source_operation_reprs"],
            )),
            target_operation_reprs=tuple(map(
                str,
                payload["target_operation_reprs"],
            )),
            context_sha256=str(payload["context_sha256"]),
            validation_trace_ref=str(payload["validation_trace_ref"]),
            validation_trace_sha256=str(
                payload["validation_trace_sha256"]
            ),
            evidence_refs=tuple(map(str, payload["evidence_refs"])),
        )


@dataclass(frozen=True)
class IntrinsicLearningSignal:
    """One CEGAR/quotient/MDL teaching signal for an exact revision."""

    family_sha256: str
    revision_sha256: str
    context_sha256: str
    evidence_epoch_sha256: str
    kind: str
    disposition: str
    measure_before: int = 0
    measure_after: int = 0
    failed_step: int | None = None
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "family_sha256",
            "revision_sha256",
            "context_sha256",
            "evidence_epoch_sha256",
        ):
            _nonempty(getattr(self, name), name)
        if self.kind not in INTRINSIC_SIGNAL_KINDS:
            raise ValueError(
                f"intrinsic signal kind must be one of "
                f"{sorted(INTRINSIC_SIGNAL_KINDS)}"
            )
        if self.disposition not in INTRINSIC_DISPOSITIONS:
            raise ValueError(
                f"intrinsic disposition must be one of "
                f"{sorted(INTRINSIC_DISPOSITIONS)}"
            )
        if min(self.measure_before, self.measure_after) < 0:
            raise ValueError("intrinsic measures must be nonnegative")
        if self.failed_step is not None and self.failed_step < 0:
            raise ValueError("intrinsic failed_step must be nonnegative")
        if (
            self.kind == "cegar_counterexample"
            and self.disposition != "requires_refinement"
        ):
            raise ValueError("CEGAR counterexamples require refinement")
        if (
            self.kind == "guard_side_exit"
            and self.disposition != "requires_fallback"
        ):
            raise ValueError("guard side exits require fallback")

    @property
    def signal_sha256(self) -> str:
        return stable_sha256(self.to_dict())

    @property
    def measured_gain(self) -> int:
        return self.measure_before - self.measure_after

    def to_dict(self) -> dict[str, Any]:
        return {
            "family_sha256": self.family_sha256,
            "revision_sha256": self.revision_sha256,
            "context_sha256": self.context_sha256,
            "evidence_epoch_sha256": self.evidence_epoch_sha256,
            "kind": self.kind,
            "disposition": self.disposition,
            "measure_before": self.measure_before,
            "measure_after": self.measure_after,
            "failed_step": self.failed_step,
            "evidence_refs": list(self.evidence_refs),
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> "IntrinsicLearningSignal":
        failed_step = payload.get("failed_step")
        return cls(
            family_sha256=str(payload["family_sha256"]),
            revision_sha256=str(payload["revision_sha256"]),
            context_sha256=str(payload["context_sha256"]),
            evidence_epoch_sha256=str(payload["evidence_epoch_sha256"]),
            kind=str(payload["kind"]),
            disposition=str(payload["disposition"]),
            measure_before=int(payload.get("measure_before", 0)),
            measure_after=int(payload.get("measure_after", 0)),
            failed_step=(
                int(failed_step) if failed_step is not None else None
            ),
            evidence_refs=tuple(map(str, payload.get("evidence_refs", ()))),
        )


@dataclass(frozen=True)
class ContinualSkillMemory:
    """Persistent derived state updated by evidence and authority receipts."""

    families: tuple[SkillFamilyMemory, ...] = ()
    intrinsic_signals: tuple[IntrinsicLearningSignal, ...] = ()
    task_experiences: tuple[TaskExperience, ...] = ()
    task_choice_experiences: tuple[TaskOptionChoiceExperience, ...] = ()
    task_decision_experiences: tuple[
        TaskDecisionChoiceExperience, ...
    ] = ()
    credit_witnesses: tuple[CausalCreditWitness, ...] = ()
    skill_transports: tuple[SkillTransportMemory, ...] = ()
    schema: str = MEMORY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != MEMORY_SCHEMA:
            raise ValueError(f"unsupported continual memory schema: {self.schema}")
        family_ids = [family.family_sha256 for family in self.families]
        if family_ids != sorted(family_ids) or len(family_ids) != len(
            set(family_ids)
        ):
            raise ValueError("skill families must be unique and canonical")
        signal_ids = [
            signal.signal_sha256 for signal in self.intrinsic_signals
        ]
        if signal_ids != sorted(signal_ids) or len(signal_ids) != len(
            set(signal_ids)
        ):
            raise ValueError("intrinsic signals must be unique and canonical")
        experience_ids = [
            experience.experience_sha256
            for experience in self.task_experiences
        ]
        if experience_ids != sorted(experience_ids) or len(
            experience_ids
        ) != len(set(experience_ids)):
            raise ValueError("task experiences must be unique and canonical")
        choice_experience_ids = [
            experience.experience_sha256
            for experience in self.task_choice_experiences
        ]
        if choice_experience_ids != sorted(choice_experience_ids) or len(
            choice_experience_ids
        ) != len(set(choice_experience_ids)):
            raise ValueError(
                "task choice experiences must be unique and canonical"
            )
        decision_experience_ids = [
            experience.experience_sha256
            for experience in self.task_decision_experiences
        ]
        if decision_experience_ids != sorted(
            decision_experience_ids
        ) or len(decision_experience_ids) != len(
            set(decision_experience_ids)
        ):
            raise ValueError(
                "task decision experiences must be unique and canonical"
            )
        witness_ids = [
            witness.witness_sha256 for witness in self.credit_witnesses
        ]
        if witness_ids != sorted(witness_ids) or len(witness_ids) != len(
            set(witness_ids)
        ):
            raise ValueError("credit witnesses must be unique and canonical")
        transport_ids = [
            transport.transport_sha256 for transport in self.skill_transports
        ]
        if transport_ids != sorted(transport_ids) or len(
            transport_ids
        ) != len(set(transport_ids)):
            raise ValueError("skill transports must be unique and canonical")

    @property
    def memory_sha256(self) -> str:
        return stable_sha256(self.to_dict())

    def family(self, family_sha256: str) -> SkillFamilyMemory | None:
        return next(
            (
                family for family in self.families
                if family.family_sha256 == family_sha256
            ),
            None,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "families": [family.to_dict() for family in self.families],
            "intrinsic_signals": [
                signal.to_dict() for signal in self.intrinsic_signals
            ],
            "task_experiences": [
                experience.to_dict() for experience in self.task_experiences
            ],
            "task_choice_experiences": [
                experience.to_dict()
                for experience in self.task_choice_experiences
            ],
            "task_decision_experiences": [
                experience.to_dict()
                for experience in self.task_decision_experiences
            ],
            "credit_witnesses": [
                witness.to_dict() for witness in self.credit_witnesses
            ],
            "skill_transports": [
                transport.to_dict() for transport in self.skill_transports
            ],
        }

    def to_receipt(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "memory_sha256": self.memory_sha256,
            "family_count": len(self.families),
            "revision_count": sum(
                len(family.revision_sha256s) for family in self.families
            ),
            "cross_context_family_count": sum(
                family.cross_context_reused for family in self.families
            ),
            "intrinsic_signal_count": len(self.intrinsic_signals),
            "open_cegar_counterexample_count": sum(
                signal.kind == "cegar_counterexample"
                for signal in self.intrinsic_signals
            ),
            "task_experience_count": len(self.task_experiences),
            "task_choice_experience_count": len(
                self.task_choice_experiences
            ),
            "task_decision_experience_count": len(
                self.task_decision_experiences
            ),
            "credit_witness_count": len(self.credit_witnesses),
            "enable_witness_count": sum(
                witness.direction == "enables"
                for witness in self.credit_witnesses
            ),
            "hazard_witness_count": sum(
                witness.direction == "hazard"
                for witness in self.credit_witnesses
            ),
            "validated_transport_count": len(self.skill_transports),
            "families": [family.to_dict() for family in self.families],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ContinualSkillMemory":
        memory = cls(
            families=tuple(sorted(
                (
                    SkillFamilyMemory.from_dict(row)
                    for row in payload.get("families", ())
                ),
                key=lambda family: family.family_sha256,
            )),
            intrinsic_signals=tuple(sorted(
                (
                    IntrinsicLearningSignal.from_dict(row)
                    for row in payload.get("intrinsic_signals", ())
                ),
                key=lambda signal: signal.signal_sha256,
            )),
            task_experiences=tuple(sorted(
                (
                    TaskExperience.from_dict(row)
                    for row in payload.get("task_experiences", ())
                ),
                key=lambda experience: experience.experience_sha256,
            )),
            task_choice_experiences=tuple(sorted(
                (
                    TaskOptionChoiceExperience.from_dict(row)
                    for row in payload.get("task_choice_experiences", ())
                ),
                key=lambda experience: experience.experience_sha256,
            )),
            task_decision_experiences=tuple(sorted(
                (
                    TaskDecisionChoiceExperience.from_dict(row)
                    for row in payload.get(
                        "task_decision_experiences",
                        (),
                    )
                ),
                key=lambda experience: experience.experience_sha256,
            )),
            credit_witnesses=tuple(sorted(
                (
                    CausalCreditWitness.from_dict(row)
                    for row in payload.get("credit_witnesses", ())
                ),
                key=lambda witness: witness.witness_sha256,
            )),
            skill_transports=tuple(sorted(
                (
                    SkillTransportMemory.from_dict(row)
                    for row in payload.get("skill_transports", ())
                ),
                key=lambda transport: transport.transport_sha256,
            )),
            schema=str(payload.get("schema", MEMORY_SCHEMA)),
        )
        derived = _derive_all_credit_witnesses(
            memory.task_experiences,
            memory.task_choice_experiences,
            memory.task_decision_experiences,
        )
        if memory.credit_witnesses != derived:
            raise ValueError(
                "persisted causal-credit witnesses do not match task experiences"
            )
        for signal in memory.intrinsic_signals:
            family = memory.family(signal.family_sha256)
            if (
                family is None
                or signal.revision_sha256 not in family.revision_sha256s
                or signal.context_sha256 not in family.context_sha256s
            ):
                raise ValueError(
                    "persisted intrinsic signal lineage drifted"
                )
        for transport in memory.skill_transports:
            source_family = memory.family(
                transport.source_family_sha256
            )
            target_family = memory.family(
                transport.target_family_sha256
            )
            if (
                source_family is None
                or source_family.operation_namespace
                != transport.source_operation_namespace
                or source_family.operation_sha256s
                != transport.source_operation_sha256s
                or source_family.operation_reprs
                != transport.source_operation_reprs
                or transport.source_revision_sha256
                not in source_family.revision_sha256s
            ):
                raise ValueError("persisted transport source lineage drifted")
            if (
                target_family is None
                or target_family.operation_namespace
                != transport.target_operation_namespace
                or target_family.operation_sha256s
                != transport.target_operation_sha256s
                or target_family.operation_reprs
                != transport.target_operation_reprs
                or transport.target_revision_sha256
                not in target_family.revision_sha256s
                or transport.context_sha256
                not in target_family.context_sha256s
                or not set(transport.evidence_refs) <= set(
                    target_family.local_validation_refs
                )
            ):
                raise ValueError("persisted transport target lineage drifted")
        return memory


def empty_continual_skill_memory() -> ContinualSkillMemory:
    return ContinualSkillMemory()


def _program_evidence_refs(program: GuardedSkillProgram) -> tuple[str, ...]:
    return _sorted_unique((
        *(
            ref
            for occurrence in program.occurrences
            for ref in occurrence.evidence_refs
        ),
        *(side_exit.evidence_ref for side_exit in program.side_exits),
    ))


def _merge_family(
    prior: SkillFamilyMemory | None,
    incoming: SkillFamilyMemory,
) -> SkillFamilyMemory:
    if prior is None:
        return incoming
    identity_fields = (
        "operation_namespace",
        "operation_sha256s",
        "operation_reprs",
    )
    if any(
        getattr(prior, field) != getattr(incoming, field)
        for field in identity_fields
    ):
        raise ValueError("skill family identity collision")
    return SkillFamilyMemory(
        family_sha256=prior.family_sha256,
        operation_namespace=prior.operation_namespace,
        operation_sha256s=prior.operation_sha256s,
        operation_reprs=prior.operation_reprs,
        revision_sha256s=_sorted_unique((
            *prior.revision_sha256s,
            *incoming.revision_sha256s,
        )),
        context_sha256s=_sorted_unique((
            *prior.context_sha256s,
            *incoming.context_sha256s,
        )),
        trace_refs=_sorted_unique((*prior.trace_refs, *incoming.trace_refs)),
        evidence_refs=_sorted_unique((
            *prior.evidence_refs,
            *incoming.evidence_refs,
        )),
        transferred_from_sha256s=_sorted_unique((
            *prior.transferred_from_sha256s,
            *incoming.transferred_from_sha256s,
        )),
        local_validation_refs=_sorted_unique((
            *prior.local_validation_refs,
            *incoming.local_validation_refs,
        )),
    )


def merge_guarded_skill_library(
    memory: ContinualSkillMemory,
    library: GuardedSkillLibrary,
    *,
    operation_namespace: str,
    context_key: Hashable,
) -> ContinualSkillMemory:
    """Merge one compiler snapshot without replacing prior family identity."""

    namespace = _nonempty(operation_namespace, "operation_namespace")
    context_sha = stable_sha256(context_key)
    families = {
        family.family_sha256: family for family in memory.families
    }
    signals = {
        signal.signal_sha256: signal
        for signal in memory.intrinsic_signals
    }
    for program in library.programs:
        family_sha = program.structural_sha256(namespace)
        evidence_refs = _program_evidence_refs(program)
        incoming = SkillFamilyMemory(
            family_sha256=family_sha,
            operation_namespace=namespace,
            operation_sha256s=tuple(
                stable_sha256(operation) for operation in program.operations
            ),
            operation_reprs=tuple(map(repr, program.operations)),
            revision_sha256s=(program.skill_sha256,),
            context_sha256s=(context_sha,),
            trace_refs=_sorted_unique(
                occurrence.trace_ref for occurrence in program.occurrences
            ),
            evidence_refs=evidence_refs,
        )
        families[family_sha] = _merge_family(
            families.get(family_sha),
            incoming,
        )
        mdl_signal = IntrinsicLearningSignal(
            family_sha256=family_sha,
            revision_sha256=program.skill_sha256,
            context_sha256=context_sha,
            evidence_epoch_sha256=library.source_sha256,
            kind="mdl_admission",
            disposition="supports_reuse",
            measure_before=program.encoded_savings,
            measure_after=program.definition_cost,
            evidence_refs=evidence_refs,
        )
        signals[mdl_signal.signal_sha256] = mdl_signal
    return replace(
        memory,
        families=tuple(sorted(
            families.values(),
            key=lambda family: family.family_sha256,
        )),
        intrinsic_signals=tuple(sorted(
            signals.values(),
            key=lambda signal: signal.signal_sha256,
        )),
    )


def record_library_quotient_transport(
    memory: ContinualSkillMemory,
    library: GuardedSkillLibrary,
    *,
    operation_namespace: str,
    context_key: Hashable,
    predictive_quotient: Any,
) -> tuple[ContinualSkillMemory, dict[str, Any]]:
    """Bind a commuting predictive quotient to every current skill revision.

    A failed global quotient is not blamed on every skill.  It returns a typed
    non-admission and awaits a path-local CEGAR witness.  A passing quotient,
    however, certifies that the current compiler snapshot is represented by a
    commuting action/effect carrier, so each revision may consume that support.
    """

    passed_section = bool(
        getattr(predictive_quotient, "passed_section", False)
    )
    passed_transport = bool(
        getattr(predictive_quotient, "passed_transport", False)
    )
    quotient_sha = str(getattr(predictive_quotient, "sha256", "") or "")
    if not passed_section or not passed_transport or not quotient_sha:
        return memory, {
            "schema": "ztare-library-quotient-transport-v1",
            "status": "not_admitted",
            "passed_section": passed_section,
            "passed_transport": passed_transport,
            "family_count": 0,
        }
    namespace = _nonempty(operation_namespace, "operation_namespace")
    context_sha = stable_sha256(context_key)
    source_count = int(
        getattr(predictive_quotient, "source_fiber_count", 0)
    )
    class_count = int(getattr(predictive_quotient, "class_count", 0))
    updated = memory
    admitted = []
    for program in library.programs:
        family_sha = program.structural_sha256(namespace)
        signal = IntrinsicLearningSignal(
            family_sha256=family_sha,
            revision_sha256=program.skill_sha256,
            context_sha256=context_sha,
            evidence_epoch_sha256=quotient_sha,
            kind="quotient_transport",
            disposition="supports_reuse",
            measure_before=source_count,
            measure_after=class_count,
            evidence_refs=(f"predictive_quotient:{quotient_sha}",),
        )
        updated = record_intrinsic_signal(updated, signal)
        admitted.append(family_sha)
    return updated, {
        "schema": "ztare-library-quotient-transport-v1",
        "status": "admitted",
        "predictive_quotient_sha256": quotient_sha,
        "source_fiber_count": source_count,
        "class_count": class_count,
        "family_count": len(admitted),
        "family_sha256s": sorted(admitted),
    }


def process_tokens_for_trace(
    library: GuardedSkillLibrary,
    *,
    trace_ref: str,
    operation_namespace: str,
) -> tuple[str, ...]:
    """Return the compiler's lossless skill/primitive process tokenization."""

    namespace = _nonempty(operation_namespace, "operation_namespace")
    source = dict(library.source_operations_by_trace)
    if trace_ref not in source:
        raise KeyError(f"trace not present in guarded library: {trace_ref}")
    operations = source[trace_ref]
    occurrence_at: dict[int, tuple[Any, GuardedSkillProgram]] = {}
    for program in library.programs:
        selected = set(program.encoding_occurrence_sha256s)
        for occurrence in program.occurrences:
            if (
                occurrence.trace_ref == trace_ref
                and occurrence.occurrence_sha256 in selected
            ):
                occurrence_at[occurrence.start_index] = (
                    occurrence,
                    program,
                )
    tokens: list[str] = []
    index = 0
    while index < len(operations):
        match = occurrence_at.get(index)
        if match is None:
            tokens.append(
                "primitive:" + stable_sha256({
                    "operation_namespace": namespace,
                    "operation": operations[index],
                })
            )
            index += 1
            continue
        occurrence, program = match
        tokens.append(
            "skill:" + program.structural_sha256(namespace)
        )
        index = occurrence.end_index
    return tuple(tokens)


def _single_insertion(
    longer: tuple[str, ...],
    shorter: tuple[str, ...],
) -> tuple[int, str] | None:
    if len(longer) != len(shorter) + 1:
        return None
    for index, token in enumerate(longer):
        if longer[:index] + longer[index + 1:] == shorter:
            return index, token
    return None


def _single_substitution(
    positive: tuple[str, ...],
    contrast: tuple[str, ...],
) -> tuple[int, str, str] | None:
    if len(positive) != len(contrast):
        return None
    differing = [
        index
        for index, (left, right) in enumerate(zip(positive, contrast))
        if left != right
    ]
    if len(differing) != 1:
        return None
    index = differing[0]
    return index, positive[index], contrast[index]


def _derive_credit_witnesses(
    experiences: Iterable[TaskExperience],
) -> tuple[CausalCreditWitness, ...]:
    rows = tuple(experiences)
    by_task_context: dict[tuple[str, str], list[TaskExperience]] = {}
    for row in rows:
        by_task_context.setdefault((
            row.task_contract_sha256,
            row.context_sha256,
        ), []).append(row)
    witnesses: dict[str, CausalCreditWitness] = {}
    for (task_contract, _context_sha256), task_rows in (
        by_task_context.items()
    ):
        positives = [
            row for row in task_rows if row.outcome == "attained"
        ]
        contrasts = [
            row for row in task_rows if row.outcome != "attained"
        ]
        for positive in positives:
            for contrast in contrasts:
                isolated = _single_insertion(
                    positive.process_tokens,
                    contrast.process_tokens,
                )
                direction = "enables"
                if isolated is None:
                    isolated = _single_insertion(
                        contrast.process_tokens,
                        positive.process_tokens,
                    )
                    direction = "hazard"
                evidence_refs = _sorted_unique((
                    positive.evidence_ref,
                    contrast.evidence_ref,
                ))
                if isolated is not None:
                    index, token = isolated
                    witness = CausalCreditWitness(
                        task_contract_sha256=task_contract,
                        direction=direction,
                        process_token=token,
                        edit_index=index,
                        positive_experience_sha256=(
                            positive.experience_sha256
                        ),
                        contrast_experience_sha256=(
                            contrast.experience_sha256
                        ),
                        evidence_refs=evidence_refs,
                    )
                    witnesses[witness.witness_sha256] = witness
                    continue
                substitution = _single_substitution(
                    positive.process_tokens,
                    contrast.process_tokens,
                )
                if substitution is None:
                    continue
                index, enabling_token, hazardous_token = substitution
                for substitution_direction, token in (
                    ("enables", enabling_token),
                    ("hazard", hazardous_token),
                ):
                    witness = CausalCreditWitness(
                        task_contract_sha256=task_contract,
                        direction=substitution_direction,
                        process_token=token,
                        edit_index=index,
                        positive_experience_sha256=(
                            positive.experience_sha256
                        ),
                        contrast_experience_sha256=(
                            contrast.experience_sha256
                        ),
                        evidence_refs=evidence_refs,
                    )
                    witnesses[witness.witness_sha256] = witness
    return tuple(sorted(
        witnesses.values(),
        key=lambda witness: witness.witness_sha256,
    ))


def _derive_choice_credit_witnesses(
    experiences: Iterable[TaskOptionChoiceExperience],
) -> tuple[CausalCreditWitness, ...]:
    """Isolate option value only across the same local choice experiment."""

    rows = tuple(experiences)
    by_comparison: dict[
        tuple[str, str, str, tuple[str, ...]],
        list[TaskOptionChoiceExperience],
    ] = {}
    for row in rows:
        by_comparison.setdefault((
            row.task_contract_sha256,
            row.choice_context_sha256,
            row.continuation_context_sha256,
            row.available_effect_option_family_sha256s,
        ), []).append(row)
    witnesses: dict[str, CausalCreditWitness] = {}
    for (
        task_contract,
        _choice_context,
        _continuation_context,
        _available,
    ), comparison_rows in by_comparison.items():
        positives = [
            row for row in comparison_rows if row.outcome == "attained"
        ]
        contrasts = [
            row for row in comparison_rows if row.outcome != "attained"
        ]
        for positive in positives:
            for contrast in contrasts:
                enabling_family = (
                    positive.chosen_effect_option_family_sha256
                )
                hazardous_family = (
                    contrast.chosen_effect_option_family_sha256
                )
                if enabling_family == hazardous_family:
                    continue
                evidence_refs = _sorted_unique((
                    positive.evidence_ref,
                    contrast.evidence_ref,
                ))
                for direction, family_sha in (
                    ("enables", enabling_family),
                    ("hazard", hazardous_family),
                ):
                    witness = CausalCreditWitness(
                        task_contract_sha256=task_contract,
                        direction=direction,
                        process_token="effect_option:" + family_sha,
                        edit_index=positive.choice_index,
                        positive_experience_sha256=(
                            positive.experience_sha256
                        ),
                        contrast_experience_sha256=(
                            contrast.experience_sha256
                        ),
                        evidence_refs=evidence_refs,
                    )
                    witnesses[witness.witness_sha256] = witness
    return tuple(sorted(
        witnesses.values(),
        key=lambda witness: witness.witness_sha256,
    ))


def decision_option_family_sha256(
    decision_namespace: str,
    option_family_id: str,
) -> str:
    """Return the substrate-independent identity of a controller option."""

    return stable_sha256({
        "schema": "ztare-decision-option-family-v1",
        "decision_namespace": _nonempty(
            decision_namespace,
            "decision_namespace",
        ),
        "option_family_id": _nonempty(
            option_family_id,
            "option_family_id",
        ),
    })


def _decision_choice_token(
    *,
    decision_namespace: str,
    option_family_sha256: str,
    choice_context_sha256: str,
    continuation_context_sha256: str,
    available_option_family_sha256s: Iterable[str],
) -> str:
    """Scope decision value to one reproducible controller experiment."""

    identity = stable_sha256({
        "schema": "ztare-task-decision-credit-scope-v1",
        "decision_namespace": _nonempty(
            decision_namespace,
            "decision_namespace",
        ),
        "option_family_sha256": _nonempty(
            option_family_sha256,
            "option_family_sha256",
        ),
        "choice_context_sha256": _nonempty(
            choice_context_sha256,
            "choice_context_sha256",
        ),
        "continuation_context_sha256": _nonempty(
            continuation_context_sha256,
            "continuation_context_sha256",
        ),
        "available_option_family_sha256s": _sorted_unique(
            available_option_family_sha256s
        ),
    })
    return "decision_option:" + identity


def _derive_decision_credit_witnesses(
    experiences: Iterable[TaskDecisionChoiceExperience],
) -> tuple[CausalCreditWitness, ...]:
    """Compare controller options only within one identical choice surface."""

    rows = tuple(experiences)
    by_comparison: dict[
        tuple[str, str, str, str, tuple[str, ...]],
        list[TaskDecisionChoiceExperience],
    ] = {}
    for row in rows:
        by_comparison.setdefault((
            row.task_contract_sha256,
            row.decision_namespace,
            row.choice_context_sha256,
            row.continuation_context_sha256,
            row.available_option_family_sha256s,
        ), []).append(row)
    witnesses: dict[str, CausalCreditWitness] = {}
    for (
        task_contract,
        decision_namespace,
        choice_context,
        continuation_context,
        available,
    ), comparison_rows in by_comparison.items():
        positives = [
            row for row in comparison_rows if row.outcome == "attained"
        ]
        contrasts = [
            row for row in comparison_rows if row.outcome != "attained"
        ]
        for positive in positives:
            for contrast in contrasts:
                enabling_family = positive.chosen_option_family_sha256
                hazardous_family = contrast.chosen_option_family_sha256
                if enabling_family == hazardous_family:
                    continue
                evidence_refs = _sorted_unique((
                    positive.evidence_ref,
                    contrast.evidence_ref,
                ))
                for direction, family_sha in (
                    ("enables", enabling_family),
                    ("hazard", hazardous_family),
                ):
                    witness = CausalCreditWitness(
                        task_contract_sha256=task_contract,
                        direction=direction,
                        process_token=_decision_choice_token(
                            decision_namespace=decision_namespace,
                            option_family_sha256=family_sha,
                            choice_context_sha256=choice_context,
                            continuation_context_sha256=(
                                continuation_context
                            ),
                            available_option_family_sha256s=available,
                        ),
                        edit_index=positive.choice_index,
                        positive_experience_sha256=(
                            positive.experience_sha256
                        ),
                        contrast_experience_sha256=(
                            contrast.experience_sha256
                        ),
                        evidence_refs=evidence_refs,
                    )
                    witnesses[witness.witness_sha256] = witness
    return tuple(sorted(
        witnesses.values(),
        key=lambda witness: witness.witness_sha256,
    ))


def _derive_all_credit_witnesses(
    task_experiences: Iterable[TaskExperience],
    choice_experiences: Iterable[TaskOptionChoiceExperience],
    decision_experiences: Iterable[TaskDecisionChoiceExperience],
) -> tuple[CausalCreditWitness, ...]:
    """Combine representations without counting one external contrast twice."""

    derived = (
        *_derive_credit_witnesses(task_experiences),
        *_derive_choice_credit_witnesses(choice_experiences),
        *_derive_decision_credit_witnesses(decision_experiences),
    )
    by_external_contrast: dict[
        tuple[str, str, str, tuple[str, ...]],
        CausalCreditWitness,
    ] = {}
    for witness in derived:
        identity = (
            witness.task_contract_sha256,
            witness.direction,
            witness.process_token,
            witness.evidence_refs,
        )
        prior = by_external_contrast.get(identity)
        if (
            prior is None
            or witness.witness_sha256 < prior.witness_sha256
        ):
            by_external_contrast[identity] = witness
    return tuple(sorted(
        by_external_contrast.values(),
        key=lambda witness: witness.witness_sha256,
    ))


def record_task_experience(
    memory: ContinualSkillMemory,
    *,
    task_contract_sha256: str,
    trace_ref: str,
    outcome: str,
    process_tokens: Iterable[str],
    evidence_ref: str,
    context_key: Hashable,
) -> ContinualSkillMemory:
    """Append one external outcome and derive only matched-contrast credit."""

    experience = TaskExperience(
        task_contract_sha256=task_contract_sha256,
        trace_ref=trace_ref,
        outcome=outcome,
        process_tokens=tuple(process_tokens),
        evidence_ref=evidence_ref,
        context_sha256=stable_sha256(context_key),
    )
    by_id = {
        row.experience_sha256: row for row in memory.task_experiences
    }
    conflicting = [
        row for row in memory.task_experiences
        if (
            row.task_contract_sha256 == experience.task_contract_sha256
            and row.trace_ref == experience.trace_ref
            and row.experience_sha256 != experience.experience_sha256
        )
    ]
    if conflicting:
        raise ValueError(
            "one task/trace identity cannot carry conflicting experiences"
        )
    by_id[experience.experience_sha256] = experience
    experiences = tuple(sorted(
        by_id.values(),
        key=lambda row: row.experience_sha256,
    ))
    return replace(
        memory,
        task_experiences=experiences,
        credit_witnesses=_derive_all_credit_witnesses(
            experiences,
            memory.task_choice_experiences,
            memory.task_decision_experiences,
        ),
    )


def record_task_choice_experience(
    memory: ContinualSkillMemory,
    *,
    task_contract_sha256: str,
    trace_ref: str,
    choice_index: int,
    outcome: str,
    choice_context_sha256: str,
    continuation_context_sha256: str,
    chosen_effect_option_family_sha256: str,
    chosen_effect_option_variant_sha256: str,
    available_effect_option_family_sha256s: Iterable[str],
    evidence_ref: str,
) -> ContinualSkillMemory:
    """Append one choice-local outcome and rederive matched contextual credit."""

    experience = TaskOptionChoiceExperience(
        task_contract_sha256=task_contract_sha256,
        trace_ref=trace_ref,
        choice_index=choice_index,
        outcome=outcome,
        choice_context_sha256=choice_context_sha256,
        continuation_context_sha256=continuation_context_sha256,
        chosen_effect_option_family_sha256=(
            chosen_effect_option_family_sha256
        ),
        chosen_effect_option_variant_sha256=(
            chosen_effect_option_variant_sha256
        ),
        available_effect_option_family_sha256s=_sorted_unique(
            available_effect_option_family_sha256s
        ),
        evidence_ref=evidence_ref,
    )
    by_id = {
        row.experience_sha256: row
        for row in memory.task_choice_experiences
    }
    conflicting = [
        row for row in memory.task_choice_experiences
        if (
            row.task_contract_sha256 == experience.task_contract_sha256
            and row.trace_ref == experience.trace_ref
            and row.choice_index == experience.choice_index
            and row.experience_sha256 != experience.experience_sha256
        )
    ]
    if conflicting:
        raise ValueError(
            "one task/trace/choice identity cannot carry conflicting "
            "experiences"
        )
    by_id[experience.experience_sha256] = experience
    experiences = tuple(sorted(
        by_id.values(),
        key=lambda row: row.experience_sha256,
    ))
    return replace(
        memory,
        task_choice_experiences=experiences,
        credit_witnesses=_derive_all_credit_witnesses(
            memory.task_experiences,
            experiences,
            memory.task_decision_experiences,
        ),
    )


def record_task_decision_experience(
    memory: ContinualSkillMemory,
    *,
    task_contract_sha256: str,
    trace_ref: str,
    choice_index: int,
    outcome: str,
    decision_namespace: str,
    choice_context_sha256: str,
    continuation_context_sha256: str,
    chosen_option_family_sha256: str,
    chosen_option_variant_sha256: str,
    available_option_family_sha256s: Iterable[str],
    evidence_ref: str,
) -> ContinualSkillMemory:
    """Append one controller choice and derive exact-context task credit."""

    experience = TaskDecisionChoiceExperience(
        task_contract_sha256=task_contract_sha256,
        trace_ref=trace_ref,
        choice_index=choice_index,
        outcome=outcome,
        decision_namespace=decision_namespace,
        choice_context_sha256=choice_context_sha256,
        continuation_context_sha256=continuation_context_sha256,
        chosen_option_family_sha256=chosen_option_family_sha256,
        chosen_option_variant_sha256=chosen_option_variant_sha256,
        available_option_family_sha256s=_sorted_unique(
            available_option_family_sha256s
        ),
        evidence_ref=evidence_ref,
    )
    by_id = {
        row.experience_sha256: row
        for row in memory.task_decision_experiences
    }
    conflicting = [
        row for row in memory.task_decision_experiences
        if (
            row.task_contract_sha256 == experience.task_contract_sha256
            and row.trace_ref == experience.trace_ref
            and row.choice_index == experience.choice_index
            and row.experience_sha256 != experience.experience_sha256
        )
    ]
    if conflicting:
        raise ValueError(
            "one task/trace/decision identity cannot carry conflicting "
            "experiences"
        )
    by_id[experience.experience_sha256] = experience
    experiences = tuple(sorted(
        by_id.values(),
        key=lambda row: row.experience_sha256,
    ))
    return replace(
        memory,
        task_decision_experiences=experiences,
        credit_witnesses=_derive_all_credit_witnesses(
            memory.task_experiences,
            memory.task_choice_experiences,
            experiences,
        ),
    )


@dataclass(frozen=True)
class IntrinsicSkillJudgment:
    """CEGAR/quotient/MDL judgment for one exact skill revision."""

    status: str
    family_sha256: str
    revision_sha256: str
    context_sha256: str
    decisive_kind: str = ""
    failed_step: int | None = None
    avoided_tail_steps: int = 0
    evidence_refs: tuple[str, ...] = ()

    def to_receipt(self) -> dict[str, Any]:
        return {
            "schema": "ztare-intrinsic-skill-judgment-v1",
            "status": self.status,
            "family_sha256": self.family_sha256,
            "revision_sha256": self.revision_sha256,
            "context_sha256": self.context_sha256,
            "decisive_kind": self.decisive_kind,
            "failed_step": self.failed_step,
            "avoided_tail_steps": self.avoided_tail_steps,
            "evidence_refs": list(self.evidence_refs),
            "authority": "cegar_quotient_mdl_receipts",
        }


def record_intrinsic_signal(
    memory: ContinualSkillMemory,
    signal: IntrinsicLearningSignal,
) -> ContinualSkillMemory:
    """Append one exact-revision teaching signal."""

    family = memory.family(signal.family_sha256)
    if family is None:
        raise ValueError("intrinsic signal names an unknown skill family")
    if signal.revision_sha256 not in family.revision_sha256s:
        raise ValueError("intrinsic signal names an unknown skill revision")
    if signal.context_sha256 not in family.context_sha256s:
        raise ValueError("intrinsic signal names an unknown skill context")
    signals = {
        row.signal_sha256: row for row in memory.intrinsic_signals
    }
    signals[signal.signal_sha256] = signal
    return replace(
        memory,
        intrinsic_signals=tuple(sorted(
            signals.values(),
            key=lambda row: row.signal_sha256,
        )),
    )


def judge_intrinsic_revision(
    memory: ContinualSkillMemory,
    *,
    family_sha256: str,
    revision_sha256: str,
    context_key: Hashable,
    planned_total_steps: int | None = None,
) -> IntrinsicSkillJudgment:
    """Apply the week-1 intrinsic judges without inventing a scalar value."""

    context_sha = stable_sha256(context_key)
    rows = [
        signal for signal in memory.intrinsic_signals
        if (
            signal.family_sha256 == family_sha256
            and signal.revision_sha256 == revision_sha256
            and signal.context_sha256 == context_sha
        )
    ]
    counterexamples = [
        signal for signal in rows
        if signal.kind == "cegar_counterexample"
    ]
    if counterexamples:
        decisive = min(
            counterexamples,
            key=lambda signal: (
                signal.failed_step
                if signal.failed_step is not None
                else 10**12,
                signal.signal_sha256,
            ),
        )
        avoided = (
            max(
                0,
                int(planned_total_steps)
                - int(decisive.failed_step or 0)
                - 1,
            )
            if planned_total_steps is not None
            and decisive.failed_step is not None
            else 0
        )
        return IntrinsicSkillJudgment(
            status="refine_early",
            family_sha256=family_sha256,
            revision_sha256=revision_sha256,
            context_sha256=context_sha,
            decisive_kind=decisive.kind,
            failed_step=decisive.failed_step,
            avoided_tail_steps=avoided,
            evidence_refs=_sorted_unique(
                ref for signal in counterexamples
                for ref in signal.evidence_refs
            ),
        )
    fallbacks = [
        signal for signal in rows
        if signal.disposition == "requires_fallback"
    ]
    if fallbacks:
        return IntrinsicSkillJudgment(
            status="primitive_fallback",
            family_sha256=family_sha256,
            revision_sha256=revision_sha256,
            context_sha256=context_sha,
            decisive_kind=fallbacks[0].kind,
            failed_step=min(
                (
                    signal.failed_step for signal in fallbacks
                    if signal.failed_step is not None
                ),
                default=None,
            ),
            evidence_refs=_sorted_unique(
                ref for signal in fallbacks for ref in signal.evidence_refs
            ),
        )
    support_kinds = {
        signal.kind for signal in rows
        if signal.disposition == "supports_reuse"
    }
    if {"mdl_admission", "quotient_transport"} <= support_kinds:
        status = "reuse_admitted"
    elif "local_guard_validation" in support_kinds:
        status = "validated_transfer"
    elif "mdl_admission" in support_kinds:
        status = "provisional_compression"
    else:
        status = "unknown"
    return IntrinsicSkillJudgment(
        status=status,
        family_sha256=family_sha256,
        revision_sha256=revision_sha256,
        context_sha256=context_sha,
        evidence_refs=_sorted_unique(
            ref for signal in rows for ref in signal.evidence_refs
        ),
    )


def consumable_skill_revision_sha256s(
    memory: ContinualSkillMemory,
    library: GuardedSkillLibrary,
    *,
    operation_namespace: str,
    context_key: Hashable,
    additional_programs: Iterable[GuardedSkillProgram] = (),
) -> tuple[frozenset[str], dict[str, Any]]:
    """Return exact revisions admitted by the intrinsic judgment loop."""

    namespace = _nonempty(operation_namespace, "operation_namespace")
    admitted: list[str] = []
    judgments = []
    program_by_revision: dict[str, GuardedSkillProgram] = {}
    for program in (*library.programs, *tuple(additional_programs)):
        prior = program_by_revision.get(program.skill_sha256)
        if prior is not None and prior != program:
            raise ValueError("skill revision identity collision")
        program_by_revision[program.skill_sha256] = program
    programs = tuple(sorted(
        program_by_revision.values(),
        key=lambda program: program.skill_sha256,
    ))
    for program in programs:
        family_sha = program.structural_sha256(namespace)
        judgment = judge_intrinsic_revision(
            memory,
            family_sha256=family_sha,
            revision_sha256=program.skill_sha256,
            context_key=context_key,
        )
        judgments.append(judgment.to_receipt())
        if judgment.status in {"reuse_admitted", "validated_transfer"}:
            admitted.append(program.skill_sha256)
    return frozenset(admitted), {
        "schema": "ztare-consumable-skill-revisions-v1",
        "library_source_sha256": library.source_sha256,
        "program_count": len(programs),
        "transported_program_count": sum(
            program.admission_authority == "validated_transport"
            for program in programs
        ),
        "admitted_revision_count": len(admitted),
        "admitted_revision_sha256s": sorted(admitted),
        "judgments": judgments,
    }


@dataclass(frozen=True)
class TaskJudgment:
    """Conservative task calibration over a process prefix."""

    status: str
    task_contract_sha256: str
    decisive_token: str = ""
    decisive_index: int | None = None
    enable_support: int = 0
    hazard_support: int = 0
    evidence_refs: tuple[str, ...] = ()
    avoided_tail_steps: int = 0

    def to_receipt(self) -> dict[str, Any]:
        return {
            "schema": "ztare-internal-skill-judgment-v1",
            "status": self.status,
            "task_contract_sha256": self.task_contract_sha256,
            "decisive_token": self.decisive_token,
            "decisive_index": self.decisive_index,
            "enable_support": self.enable_support,
            "hazard_support": self.hazard_support,
            "evidence_refs": list(self.evidence_refs),
            "avoided_tail_steps": self.avoided_tail_steps,
            "authority": "matched_external_outcome_contrasts_only",
        }


@dataclass(frozen=True)
class EffectOptionTaskJudgment:
    """Matched-contrast task authority for one effect-conditioned option."""

    effect_option_family_sha256: str
    task_contract_sha256: str
    status: str
    source_family_sha256s: tuple[str, ...]
    enable_support: int = 0
    hazard_support: int = 0
    evidence_refs: tuple[str, ...] = ()

    def to_receipt(self) -> dict[str, Any]:
        return {
            "schema": "ztare-effect-option-task-judgment-v1",
            "effect_option_family_sha256": (
                self.effect_option_family_sha256
            ),
            "task_contract_sha256": self.task_contract_sha256,
            "status": self.status,
            "source_family_sha256s": list(
                self.source_family_sha256s
            ),
            "enable_support": self.enable_support,
            "hazard_support": self.hazard_support,
            "evidence_refs": list(self.evidence_refs),
            "authority": "matched_external_outcome_contrasts_only",
        }


@dataclass(frozen=True)
class DecisionOptionTaskJudgment:
    """Exact-choice task authority for one controller-level option."""

    decision_namespace: str
    option_family_sha256: str
    task_contract_sha256: str
    choice_context_sha256: str
    continuation_context_sha256: str
    available_option_family_sha256s: tuple[str, ...]
    status: str
    enable_support: int = 0
    hazard_support: int = 0
    scoped_experience_count: int = 0
    contrast_priority: int = 0
    evidence_refs: tuple[str, ...] = ()

    @property
    def preference(self) -> int:
        if self.status == "task_credited":
            return 1
        if self.status == "task_hazard":
            return -1
        return 0

    def to_receipt(self) -> dict[str, Any]:
        return {
            "schema": "ztare-decision-option-task-judgment-v1",
            "decision_namespace": self.decision_namespace,
            "option_family_sha256": self.option_family_sha256,
            "task_contract_sha256": self.task_contract_sha256,
            "choice_context_sha256": self.choice_context_sha256,
            "continuation_context_sha256": (
                self.continuation_context_sha256
            ),
            "available_option_family_sha256s": list(
                self.available_option_family_sha256s
            ),
            "status": self.status,
            "preference": self.preference,
            "enable_support": self.enable_support,
            "hazard_support": self.hazard_support,
            "scoped_experience_count": self.scoped_experience_count,
            "contrast_priority": self.contrast_priority,
            "evidence_refs": list(self.evidence_refs),
            "authority": "matched_external_outcome_contrasts_only",
        }


def judge_decision_option_task_credit(
    memory: ContinualSkillMemory,
    *,
    decision_namespace: str,
    option_family_sha256: str,
    task_contract_sha256: str,
    choice_context_sha256: str,
    continuation_context_sha256: str,
    available_option_family_sha256s: Iterable[str],
) -> DecisionOptionTaskJudgment:
    """Read task value only at the exact controller choice surface."""

    namespace = _nonempty(decision_namespace, "decision_namespace")
    option_family = _nonempty(
        option_family_sha256,
        "option_family_sha256",
    )
    task = _nonempty(task_contract_sha256, "task_contract_sha256")
    choice_context = _nonempty(
        choice_context_sha256,
        "choice_context_sha256",
    )
    continuation_context = _nonempty(
        continuation_context_sha256,
        "continuation_context_sha256",
    )
    available = _sorted_unique(available_option_family_sha256s)
    if option_family not in available:
        raise ValueError("judged decision option must belong to the choice set")
    decision_token = _decision_choice_token(
        decision_namespace=namespace,
        option_family_sha256=option_family,
        choice_context_sha256=choice_context,
        continuation_context_sha256=continuation_context,
        available_option_family_sha256s=available,
    )
    enabling = []
    hazardous = []
    for witness in memory.credit_witnesses:
        if (
            witness.task_contract_sha256 != task
            or witness.process_token != decision_token
        ):
            continue
        if witness.direction == "enables":
            enabling.append(witness)
        else:
            hazardous.append(witness)
    scoped_experiences = [
        experience
        for experience in memory.task_decision_experiences
        if (
            experience.task_contract_sha256 == task
            and experience.decision_namespace == namespace
            and experience.choice_context_sha256 == choice_context
            and experience.continuation_context_sha256
            == continuation_context
            and experience.available_option_family_sha256s == available
        )
    ]
    observed_families = {
        experience.chosen_option_family_sha256
        for experience in scoped_experiences
    }
    unresolved_contrast = any(
        experience.outcome != "attained"
        for experience in scoped_experiences
    )
    if enabling and hazardous:
        status = "credit_conflict"
    elif enabling:
        status = "task_credited"
    elif hazardous:
        status = "task_hazard"
    else:
        status = "uncredited"
    return DecisionOptionTaskJudgment(
        decision_namespace=namespace,
        option_family_sha256=option_family,
        task_contract_sha256=task,
        choice_context_sha256=choice_context,
        continuation_context_sha256=continuation_context,
        available_option_family_sha256s=available,
        status=status,
        enable_support=len(enabling),
        hazard_support=len(hazardous),
        scoped_experience_count=len(scoped_experiences),
        contrast_priority=int(
            unresolved_contrast
            and option_family not in observed_families
        ),
        evidence_refs=_sorted_unique(
            ref
            for witness in (*enabling, *hazardous)
            for ref in witness.evidence_refs
        ),
    )


def judge_effect_option_task_credit(
    memory: ContinualSkillMemory,
    *,
    effect_option_family_sha256: str,
    task_contract_sha256: str,
    source_family_sha256s: Iterable[str],
) -> EffectOptionTaskJudgment:
    """Keep effect evidence separate from task-selection authority."""

    effect_family = _nonempty(
        effect_option_family_sha256,
        "effect_option_family_sha256",
    )
    task = _nonempty(task_contract_sha256, "task_contract_sha256")
    source_families = _sorted_unique(source_family_sha256s)
    effect_token = "effect_option:" + effect_family
    enabling = []
    hazardous = []
    for witness in memory.credit_witnesses:
        if (
            witness.task_contract_sha256 != task
            or witness.process_token != effect_token
        ):
            continue
        if witness.direction == "enables":
            enabling.append(witness)
        else:
            hazardous.append(witness)
    if enabling and hazardous:
        status = "credit_conflict"
    elif enabling:
        status = "task_credited"
    elif hazardous:
        status = "task_hazard"
    else:
        status = "uncredited"
    return EffectOptionTaskJudgment(
        effect_option_family_sha256=effect_family,
        task_contract_sha256=task,
        status=status,
        source_family_sha256s=source_families,
        enable_support=len(enabling),
        hazard_support=len(hazardous),
        evidence_refs=_sorted_unique(
            ref
            for witness in (*enabling, *hazardous)
            for ref in witness.evidence_refs
        ),
    )


def judge_process_prefix(
    memory: ContinualSkillMemory,
    *,
    task_contract_sha256: str,
    process_tokens: Iterable[str],
    planned_total_steps: int | None = None,
) -> TaskJudgment:
    """Judge a prefix without converting association into causal credit."""

    task = _nonempty(task_contract_sha256, "task_contract_sha256")
    tokens = tuple(process_tokens)
    support: dict[str, dict[str, list[CausalCreditWitness]]] = {}
    for witness in memory.credit_witnesses:
        if witness.task_contract_sha256 != task:
            continue
        support.setdefault(
            witness.process_token,
            {"enables": [], "hazard": []},
        )[witness.direction].append(witness)

    progress: tuple[int, str, list[CausalCreditWitness]] | None = None
    for index, token in enumerate(tokens):
        token_support = support.get(token)
        if not token_support:
            continue
        hazards = token_support["hazard"]
        enables = token_support["enables"]
        if hazards and not enables:
            tail = (
                max(0, int(planned_total_steps) - index - 1)
                if planned_total_steps is not None
                else 0
            )
            return TaskJudgment(
                status="fail_early",
                task_contract_sha256=task,
                decisive_token=token,
                decisive_index=index,
                enable_support=0,
                hazard_support=len(hazards),
                evidence_refs=_sorted_unique(
                    ref for witness in hazards
                    for ref in witness.evidence_refs
                ),
                avoided_tail_steps=tail,
            )
        if enables and not hazards and progress is None:
            progress = index, token, enables
    if progress is not None:
        index, token, enables = progress
        return TaskJudgment(
            status="progress_supported",
            task_contract_sha256=task,
            decisive_token=token,
            decisive_index=index,
            enable_support=len(enables),
            evidence_refs=_sorted_unique(
                ref for witness in enables for ref in witness.evidence_refs
            ),
        )
    return TaskJudgment(
        status="unknown",
        task_contract_sha256=task,
    )


@dataclass(frozen=True)
class SkillTransferProposal:
    """Explicit family transport; local guard evidence is still owed."""

    source_family_sha256: str
    source_revision_sha256: str
    source_operation_namespace: str
    target_operation_namespace: str
    target_operations: tuple[Hashable, ...]
    target_family_sha256: str
    source_trace_support: int
    status: str = "local_guard_validation_required"

    def __post_init__(self) -> None:
        for name in (
            "source_family_sha256",
            "source_revision_sha256",
            "source_operation_namespace",
            "target_operation_namespace",
            "target_family_sha256",
        ):
            _nonempty(getattr(self, name), name)
        if self.status != "local_guard_validation_required":
            raise ValueError("unsupported skill transport proposal status")
        if self.source_trace_support < 0:
            raise ValueError("source trace support must be nonnegative")
        if not self.target_operations:
            raise ValueError("transport proposals require target operations")
        for operation in self.target_operations:
            try:
                hash(operation)
            except TypeError as exc:
                raise TypeError(
                    "transported operations must be hashable"
                ) from exc
        expected_family = _operation_family_sha256(
            self.target_operation_namespace,
            self.target_operations,
        )
        if self.target_family_sha256 != expected_family:
            raise ValueError("transport target family identity drifted")

    def to_receipt(self) -> dict[str, Any]:
        return {
            "schema": "ztare-skill-transfer-proposal-v1",
            "source_family_sha256": self.source_family_sha256,
            "source_revision_sha256": self.source_revision_sha256,
            "source_operation_namespace": self.source_operation_namespace,
            "target_operation_namespace": self.target_operation_namespace,
            "target_operation_sha256s": [
                stable_sha256(operation) for operation in self.target_operations
            ],
            "target_family_sha256": self.target_family_sha256,
            "source_trace_support": self.source_trace_support,
            "status": self.status,
            "task_outcome_transferred": False,
        }


def propose_skill_transport(
    memory: ContinualSkillMemory,
    *,
    source_program: GuardedSkillProgram,
    source_operation_namespace: str,
    target_operation_namespace: str,
    operation_map: Mapping[Hashable, Hashable] | Callable[[Hashable], Hashable],
) -> SkillTransferProposal:
    """Transport an operation word through an explicit support bijection."""

    source_namespace = _nonempty(
        source_operation_namespace,
        "source_operation_namespace",
    )
    source_family = source_program.structural_sha256(source_namespace)
    remembered = memory.family(source_family)
    if remembered is None:
        raise ValueError("source skill family is absent from continual memory")
    if source_program.skill_sha256 not in remembered.revision_sha256s:
        raise ValueError("source skill revision is absent from continual memory")
    if (
        remembered.operation_namespace != source_namespace
        or remembered.operation_sha256s
        != tuple(
            stable_sha256(operation)
            for operation in source_program.operations
        )
        or remembered.operation_reprs
        != tuple(map(repr, source_program.operations))
    ):
        raise ValueError("source skill operation identity drifted")
    target_operations: list[Hashable] = []
    for operation in source_program.operations:
        if callable(operation_map):
            target = operation_map(operation)
        else:
            if operation not in operation_map:
                raise ValueError(
                    f"operation transport is undefined for {operation!r}"
                )
            target = operation_map[operation]
        try:
            hash(target)
        except TypeError as exc:
            raise TypeError("transported operations must be hashable") from exc
        target_operations.append(target)
    target_word = tuple(target_operations)
    if len(set(source_program.operations)) != len(set(target_word)):
        raise ValueError(
            "operation transport must be injective on source support"
        )
    return SkillTransferProposal(
        source_family_sha256=source_family,
        source_revision_sha256=source_program.skill_sha256,
        source_operation_namespace=source_namespace,
        target_operation_namespace=_nonempty(
            target_operation_namespace,
            "target_operation_namespace",
        ),
        target_operations=target_word,
        target_family_sha256=_operation_family_sha256(
            target_operation_namespace,
            target_word,
        ),
        source_trace_support=remembered.independent_trace_support,
    )


@dataclass(frozen=True)
class ValidatedSkillTransfer:
    """One target-context guard/effect witness for a transported family."""

    proposal: SkillTransferProposal
    initiation_key: Hashable
    termination_key: Hashable
    effect_trace: tuple[Hashable, ...]
    evidence_refs: tuple[str, ...]
    validation_trace_ref: str
    validation_trace_sha256: str
    program: GuardedSkillProgram

    def admits(self, initiation_key: Hashable) -> bool:
        return initiation_key == self.initiation_key

    def to_receipt(self) -> dict[str, Any]:
        return {
            "schema": "ztare-validated-skill-transfer-v1",
            "proposal": self.proposal.to_receipt(),
            "initiation_sha256": stable_sha256(self.initiation_key),
            "termination_sha256": stable_sha256(self.termination_key),
            "effect_sha256s": [
                stable_sha256(effect) for effect in self.effect_trace
            ],
            "target_revision_sha256": self.program.skill_sha256,
            "validation_trace_ref": self.validation_trace_ref,
            "validation_trace_sha256": self.validation_trace_sha256,
            "evidence_refs": list(self.evidence_refs),
            "local_guard_validated": True,
            "task_outcome_transferred": False,
        }


def _validated_transport_program(
    validation_trace: GuardedActionTrace,
) -> GuardedSkillProgram:
    transitions = validation_trace.transitions
    if any(
        transition.boundary_kind
        or transition.successor is None
        or transition.effect is None
        for transition in transitions
    ):
        raise ValueError(
            "transport validation requires an ordinary effect-owned trace"
        )
    evidence_refs = _sorted_unique(
        transition.evidence_ref for transition in transitions
    )
    first = transitions[0]
    last = transitions[-1]
    occurrence = SkillOccurrence(
        trace_ref=validation_trace.trace_ref,
        start_index=0,
        end_index=len(transitions),
        initiation_key=first.source,
        termination_key=last.successor,
        effect_trace=tuple(
            transition.effect for transition in transitions
        ),
        evidence_refs=evidence_refs,
    )
    variant = SkillVariant(
        effect_trace=occurrence.effect_trace,
        termination_key=occurrence.termination_key,
        initiation_keys=(occurrence.initiation_key,),
        occurrence_sha256s=(occurrence.occurrence_sha256,),
        trace_refs=(validation_trace.trace_ref,),
        evidence_refs=evidence_refs,
    )
    saved_tokens = max(0, len(transitions) - 1)
    return GuardedSkillProgram(
        operations=validation_trace.operations,
        occurrences=(occurrence,),
        encoding_occurrence_sha256s=(occurrence.occurrence_sha256,),
        variants=(variant,),
        side_exits=(),
        admitted_initiation_keys=(occurrence.initiation_key,),
        fallback_initiation_keys=(),
        definition_cost=0,
        encoded_savings=saved_tokens,
        net_gain=saved_tokens,
        admission_authority="validated_transport",
    )


def validate_skill_transport(
    memory: ContinualSkillMemory,
    proposal: SkillTransferProposal,
    *,
    validation_trace: GuardedActionTrace,
    context_key: Hashable,
) -> tuple[ContinualSkillMemory, ValidatedSkillTransfer]:
    """Admit a transported word after one exact local guard/effect witness."""

    if validation_trace.operations != proposal.target_operations:
        raise ValueError("local validation trace does not match transported word")
    source_family = memory.family(proposal.source_family_sha256)
    if (
        source_family is None
        or source_family.operation_namespace
        != proposal.source_operation_namespace
        or proposal.source_revision_sha256
        not in source_family.revision_sha256s
    ):
        raise ValueError("transport source lineage is absent from memory")
    program = _validated_transport_program(validation_trace)
    first = validation_trace.transitions[0]
    last = validation_trace.transitions[-1]
    evidence_refs = _sorted_unique(
        transition.evidence_ref
        for transition in validation_trace.transitions
    )
    validation_revision = program.skill_sha256
    incoming = SkillFamilyMemory(
        family_sha256=proposal.target_family_sha256,
        operation_namespace=proposal.target_operation_namespace,
        operation_sha256s=tuple(
            stable_sha256(operation)
            for operation in proposal.target_operations
        ),
        operation_reprs=tuple(map(repr, proposal.target_operations)),
        revision_sha256s=(validation_revision,),
        context_sha256s=(stable_sha256(context_key),),
        trace_refs=(validation_trace.trace_ref,),
        evidence_refs=evidence_refs,
        transferred_from_sha256s=(proposal.source_family_sha256,),
        local_validation_refs=evidence_refs,
    )
    families = {
        family.family_sha256: family for family in memory.families
    }
    families[incoming.family_sha256] = _merge_family(
        families.get(incoming.family_sha256),
        incoming,
    )
    context_sha = stable_sha256(context_key)
    validation_signal = IntrinsicLearningSignal(
        family_sha256=proposal.target_family_sha256,
        revision_sha256=validation_revision,
        context_sha256=context_sha,
        evidence_epoch_sha256=validation_trace.sha256,
        kind="local_guard_validation",
        disposition="supports_reuse",
        measure_before=len(proposal.target_operations),
        measure_after=1,
        evidence_refs=evidence_refs,
    )
    signals = {
        signal.signal_sha256: signal
        for signal in memory.intrinsic_signals
    }
    signals[validation_signal.signal_sha256] = validation_signal
    transport = SkillTransportMemory(
        source_family_sha256=proposal.source_family_sha256,
        source_revision_sha256=proposal.source_revision_sha256,
        target_family_sha256=proposal.target_family_sha256,
        target_revision_sha256=validation_revision,
        source_operation_namespace=proposal.source_operation_namespace,
        target_operation_namespace=proposal.target_operation_namespace,
        source_operation_sha256s=source_family.operation_sha256s,
        target_operation_sha256s=tuple(
            stable_sha256(operation)
            for operation in proposal.target_operations
        ),
        source_operation_reprs=source_family.operation_reprs,
        target_operation_reprs=tuple(map(repr, proposal.target_operations)),
        context_sha256=context_sha,
        validation_trace_ref=validation_trace.trace_ref,
        validation_trace_sha256=validation_trace.sha256,
        evidence_refs=evidence_refs,
    )
    transports = {
        row.transport_sha256: row for row in memory.skill_transports
    }
    transports[transport.transport_sha256] = transport
    updated = replace(
        memory,
        families=tuple(sorted(
            families.values(),
            key=lambda family: family.family_sha256,
        )),
        intrinsic_signals=tuple(sorted(
            signals.values(),
            key=lambda signal: signal.signal_sha256,
        )),
        skill_transports=tuple(sorted(
            transports.values(),
            key=lambda row: row.transport_sha256,
        )),
    )
    validated = ValidatedSkillTransfer(
        proposal=proposal,
        initiation_key=first.source,
        termination_key=last.successor,
        effect_trace=tuple(
            transition.effect
            for transition in validation_trace.transitions
        ),
        evidence_refs=evidence_refs,
        validation_trace_ref=validation_trace.trace_ref,
        validation_trace_sha256=validation_trace.sha256,
        program=program,
    )
    return updated, validated


def rehydrate_validated_skill_programs(
    memory: ContinualSkillMemory,
    traces: Iterable[GuardedActionTrace],
    *,
    operation_namespace: str,
    context_key: Hashable,
) -> tuple[GuardedSkillProgram, ...]:
    """Rebuild executable transported revisions from exact local evidence."""

    namespace = _nonempty(operation_namespace, "operation_namespace")
    context_sha = stable_sha256(context_key)
    trace_by_identity = {
        (trace.trace_ref, trace.sha256): trace for trace in traces
    }
    programs: dict[str, GuardedSkillProgram] = {}
    for transport in memory.skill_transports:
        if (
            transport.target_operation_namespace != namespace
            or transport.context_sha256 != context_sha
        ):
            continue
        source_family = memory.family(transport.source_family_sha256)
        target_family = memory.family(transport.target_family_sha256)
        if (
            source_family is None
            or transport.source_revision_sha256
            not in source_family.revision_sha256s
        ):
            raise ValueError("persisted transport lost source lineage")
        if (
            target_family is None
            or transport.target_revision_sha256
            not in target_family.revision_sha256s
            or context_sha not in target_family.context_sha256s
        ):
            raise ValueError("persisted transport lost target lineage")
        trace = trace_by_identity.get((
            transport.validation_trace_ref,
            transport.validation_trace_sha256,
        ))
        if trace is None:
            continue
        operation_sha256s = tuple(
            stable_sha256(operation) for operation in trace.operations
        )
        operation_reprs = tuple(map(repr, trace.operations))
        if (
            operation_sha256s != transport.target_operation_sha256s
            or operation_reprs != transport.target_operation_reprs
            or operation_sha256s != target_family.operation_sha256s
            or operation_reprs != target_family.operation_reprs
        ):
            raise ValueError("transported operation identity drifted")
        program = _validated_transport_program(trace)
        if (
            program.structural_sha256(namespace)
            != transport.target_family_sha256
            or program.skill_sha256
            != transport.target_revision_sha256
        ):
            raise ValueError("rehydrated transport revision identity drifted")
        validation_signal = next(
            (
                signal for signal in memory.intrinsic_signals
                if (
                    signal.family_sha256
                    == transport.target_family_sha256
                    and signal.revision_sha256
                    == transport.target_revision_sha256
                    and signal.context_sha256 == context_sha
                    and signal.kind == "local_guard_validation"
                    and signal.disposition == "supports_reuse"
                )
            ),
            None,
        )
        if validation_signal is None:
            raise ValueError("transport lacks local validation authority")
        prior = programs.get(program.skill_sha256)
        if prior is not None and prior != program:
            raise ValueError("rehydrated skill revision collision")
        programs[program.skill_sha256] = program
    return tuple(sorted(
        programs.values(),
        key=lambda program: program.skill_sha256,
    ))


def save_continual_skill_memory(
    path: str | Path,
    memory: ContinualSkillMemory,
) -> Path:
    """Atomically persist the complete derived state."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.tmp")
    temporary.write_text(
        json.dumps(
            memory.to_dict(),
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        ) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, target)
    return target


def load_continual_skill_memory(
    path: str | Path,
) -> ContinualSkillMemory:
    target = Path(path)
    if not target.exists():
        return empty_continual_skill_memory()
    payload = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("continual skill memory must be a JSON object")
    return ContinualSkillMemory.from_dict(payload)


__all__ = [
    "CausalCreditWitness",
    "ContinualSkillMemory",
    "DecisionOptionTaskJudgment",
    "EffectOptionTaskJudgment",
    "INTRINSIC_DISPOSITIONS",
    "INTRINSIC_SIGNAL_KINDS",
    "IntrinsicLearningSignal",
    "IntrinsicSkillJudgment",
    "MEMORY_SCHEMA",
    "SkillFamilyMemory",
    "SkillTransportMemory",
    "SkillTransferProposal",
    "TaskJudgment",
    "TaskExperience",
    "TaskDecisionChoiceExperience",
    "TaskOptionChoiceExperience",
    "ValidatedSkillTransfer",
    "consumable_skill_revision_sha256s",
    "decision_option_family_sha256",
    "empty_continual_skill_memory",
    "judge_decision_option_task_credit",
    "judge_intrinsic_revision",
    "judge_effect_option_task_credit",
    "judge_process_prefix",
    "load_continual_skill_memory",
    "merge_guarded_skill_library",
    "process_tokens_for_trace",
    "propose_skill_transport",
    "rehydrate_validated_skill_programs",
    "record_library_quotient_transport",
    "record_task_decision_experience",
    "record_intrinsic_signal",
    "record_task_choice_experience",
    "record_task_experience",
    "save_continual_skill_memory",
    "validate_skill_transport",
]
