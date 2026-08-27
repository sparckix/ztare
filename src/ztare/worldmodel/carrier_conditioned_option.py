"""Lower a remembered operation word through a current-state carrier.

Historical option support and current-state prediction have different
authority.  A guarded skill may nominate an operation word; an accepted
carrier may provisionally predict its concrete image; only an external
observation may settle that prediction.  This module preserves those three
identities and never transfers task credit.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Hashable, Iterable

from ztare.common.equivariance import stable_sha256
from ztare.worldmodel.mechanism_effects import fiber_mechanism_effect


EffectFunction = Callable[[Any, Any], Hashable]


def _required_digest(value: str, name: str) -> str:
    digest = str(value).strip()
    if len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return digest


def _required_refs(values: Iterable[str], name: str) -> tuple[str, ...]:
    refs = tuple(sorted({str(value).strip() for value in values if str(value).strip()}))
    if not refs:
        raise ValueError(f"{name} requires at least one evidence reference")
    return refs


def _effect_family_sha256(
    *,
    effect_namespace: str,
    effect_trace: tuple[Hashable, ...],
) -> str:
    return stable_sha256({
        "schema": "ztare-effect-option-family-v2",
        "effect_namespace": effect_namespace,
        "effect_trace": effect_trace,
    })


@dataclass(frozen=True)
class CarrierConditionedOptionPrediction:
    """One provisional carrier image of a remembered operation word."""

    operation_namespace: str
    effect_namespace: str
    carrier_execution_sha256: str
    projection_sha256: str
    source_skill_sha256: str
    source_state_sha256: str
    start_time: int
    operations: tuple[Hashable, ...]
    status: str
    predicted_effect_trace: tuple[Hashable, ...]
    predicted_intermediate_state_sha256s: tuple[str, ...]
    predicted_final_state_sha256: str
    evidence_refs: tuple[str, ...]
    failed_step: int | None = None

    def __post_init__(self) -> None:
        if self.status not in {"predicted", "carrier_undefined"}:
            raise ValueError("unknown carrier-conditioned prediction status")
        for value, name in (
            (self.carrier_execution_sha256, "carrier_execution_sha256"),
            (self.projection_sha256, "projection_sha256"),
            (self.source_skill_sha256, "source_skill_sha256"),
            (self.source_state_sha256, "source_state_sha256"),
        ):
            _required_digest(value, name)
        if not self.operation_namespace.strip() or not self.effect_namespace.strip():
            raise ValueError("option prediction requires operation/effect namespaces")
        if not self.operations:
            raise ValueError("option prediction requires a non-empty operation word")
        if not isinstance(self.start_time, int) or isinstance(self.start_time, bool):
            raise TypeError("option prediction start_time must be an integer")
        if self.status == "predicted":
            if self.failed_step is not None:
                raise ValueError("complete prediction cannot have failed_step")
            if len(self.predicted_effect_trace) != len(self.operations):
                raise ValueError("complete prediction effect length drifted")
            if len(self.predicted_intermediate_state_sha256s) != len(self.operations):
                raise ValueError("complete prediction state length drifted")
            _required_digest(
                self.predicted_final_state_sha256,
                "predicted_final_state_sha256",
            )
        else:
            if self.failed_step != len(self.predicted_effect_trace):
                raise ValueError("refusal failed_step must follow predicted prefix")
            if self.predicted_final_state_sha256:
                raise ValueError("refused prediction cannot claim a final state")
        _required_refs(self.evidence_refs, "option prediction")

    @property
    def predictive_effect_family_sha256(self) -> str:
        if self.status != "predicted":
            return ""
        return _effect_family_sha256(
            effect_namespace=self.effect_namespace,
            effect_trace=self.predicted_effect_trace,
        )

    @property
    def prediction_sha256(self) -> str:
        return stable_sha256(self._core_receipt())

    def _core_receipt(self) -> dict[str, Any]:
        return {
            "schema": "ztare-carrier-conditioned-option-prediction-v1",
            "authority": "predictive_carrier",
            "operation_namespace": self.operation_namespace,
            "effect_namespace": self.effect_namespace,
            "carrier_execution_sha256": self.carrier_execution_sha256,
            "projection_sha256": self.projection_sha256,
            "source_skill_sha256": self.source_skill_sha256,
            "source_state_sha256": self.source_state_sha256,
            "start_time": self.start_time,
            "operations": [repr(operation) for operation in self.operations],
            "status": self.status,
            "failed_step": self.failed_step,
            "predicted_effect_sha256s": [
                stable_sha256(effect) for effect in self.predicted_effect_trace
            ],
            "predicted_effect_family_sha256": (
                self.predictive_effect_family_sha256
            ),
            "predicted_intermediate_state_sha256s": list(
                self.predicted_intermediate_state_sha256s
            ),
            "predicted_final_state_sha256": self.predicted_final_state_sha256,
            "evidence_refs": list(self.evidence_refs),
            "externally_settled": False,
            "task_credit_transferred": False,
        }

    def to_receipt(self) -> dict[str, Any]:
        core = self._core_receipt()
        return {**core, "prediction_sha256": stable_sha256(core)}


@dataclass(frozen=True)
class CarrierConditionedOptionSettlement:
    """External comparison for one immutable carrier option prediction."""

    prediction: CarrierConditionedOptionPrediction
    environment_source_sha256: str
    observed_source_state_sha256: str
    observed_effect_trace: tuple[Hashable, ...]
    observed_intermediate_state_sha256s: tuple[str, ...]
    observed_final_state_sha256: str
    evidence_refs: tuple[str, ...]
    status: str
    boundary_kind: str = ""
    failed_step: int | None = None

    def __post_init__(self) -> None:
        _required_digest(
            self.environment_source_sha256,
            "environment_source_sha256",
        )
        _required_digest(
            self.observed_source_state_sha256,
            "observed_source_state_sha256",
        )
        _required_refs(self.evidence_refs, "option settlement")
        if self.status not in {
            "effect_confirmed",
            "counterexample",
            "source_mismatch",
            "boundary_crossed",
            "prediction_refused",
        }:
            raise ValueError("unknown carrier-conditioned settlement status")

    @property
    def effect_matches(self) -> bool:
        return (
            self.prediction.status == "predicted"
            and self.prediction.predicted_effect_trace
            == self.observed_effect_trace
        )

    @property
    def intermediate_states_match(self) -> bool:
        return (
            self.prediction.status == "predicted"
            and self.prediction.predicted_intermediate_state_sha256s
            == self.observed_intermediate_state_sha256s
        )

    @property
    def final_state_matches(self) -> bool:
        return (
            self.prediction.status == "predicted"
            and self.prediction.predicted_final_state_sha256
            == self.observed_final_state_sha256
        )

    @property
    def observed_effect_family_sha256(self) -> str:
        if not self.observed_effect_trace:
            return ""
        return _effect_family_sha256(
            effect_namespace=self.prediction.effect_namespace,
            effect_trace=self.observed_effect_trace,
        )

    @property
    def settlement_sha256(self) -> str:
        return stable_sha256(self._core_receipt())

    def _core_receipt(self) -> dict[str, Any]:
        return {
            "schema": "ztare-carrier-conditioned-option-settlement-v1",
            "authority": "external_environment_observation",
            "prediction_sha256": self.prediction.prediction_sha256,
            "environment_source_sha256": self.environment_source_sha256,
            "observed_source_state_sha256": self.observed_source_state_sha256,
            "observed_effect_sha256s": [
                stable_sha256(effect) for effect in self.observed_effect_trace
            ],
            "observed_effect_family_sha256": (
                self.observed_effect_family_sha256
            ),
            "observed_intermediate_state_sha256s": list(
                self.observed_intermediate_state_sha256s
            ),
            "observed_final_state_sha256": self.observed_final_state_sha256,
            "status": self.status,
            "boundary_kind": self.boundary_kind,
            "failed_step": self.failed_step,
            "effect_matches": self.effect_matches,
            "intermediate_states_match": self.intermediate_states_match,
            "final_state_matches": self.final_state_matches,
            "externally_settled": self.status == "effect_confirmed",
            "task_credit_transferred": False,
            "evidence_refs": list(self.evidence_refs),
        }

    def to_receipt(self) -> dict[str, Any]:
        core = self._core_receipt()
        return {**core, "settlement_sha256": stable_sha256(core)}


def compile_carrier_conditioned_option_prediction(
    *,
    carrier: Callable[[Any, Hashable, int], Any | None],
    projection: Any,
    source_state: Any,
    start_time: int,
    operations: Iterable[Hashable],
    operation_namespace: str,
    effect_namespace: str,
    carrier_execution_sha256: str,
    source_skill_sha256: str,
    evidence_refs: Iterable[str],
    effect: EffectFunction = fiber_mechanism_effect,
) -> CarrierConditionedOptionPrediction:
    """Provisionally lower a skill word through the accepted carrier."""

    word = tuple(operations)
    if not word:
        raise ValueError("carrier-conditioned option requires operations")
    projection_sha256 = _required_digest(
        str(getattr(projection, "projection_sha256", "")),
        "projection_sha256",
    )
    execution_sha = _required_digest(
        carrier_execution_sha256,
        "carrier_execution_sha256",
    )
    skill_sha = _required_digest(source_skill_sha256, "source_skill_sha256")
    refs = _required_refs(evidence_refs, "option prediction")
    current = source_state
    effects = []
    state_sha256s = []
    for step, operation in enumerate(word):
        successor = carrier(current, operation, start_time + step)
        if successor is None:
            return CarrierConditionedOptionPrediction(
                operation_namespace=str(operation_namespace),
                effect_namespace=str(effect_namespace),
                carrier_execution_sha256=execution_sha,
                projection_sha256=projection_sha256,
                source_skill_sha256=skill_sha,
                source_state_sha256=stable_sha256(source_state),
                start_time=start_time,
                operations=word,
                status="carrier_undefined",
                failed_step=step,
                predicted_effect_trace=tuple(effects),
                predicted_intermediate_state_sha256s=tuple(state_sha256s),
                predicted_final_state_sha256="",
                evidence_refs=refs,
            )
        effects.append(effect(
            projection.factor(current),
            projection.factor(successor),
        ))
        current = successor
        state_sha256s.append(stable_sha256(current))
    return CarrierConditionedOptionPrediction(
        operation_namespace=str(operation_namespace),
        effect_namespace=str(effect_namespace),
        carrier_execution_sha256=execution_sha,
        projection_sha256=projection_sha256,
        source_skill_sha256=skill_sha,
        source_state_sha256=stable_sha256(source_state),
        start_time=start_time,
        operations=word,
        status="predicted",
        predicted_effect_trace=tuple(effects),
        predicted_intermediate_state_sha256s=tuple(state_sha256s),
        predicted_final_state_sha256=stable_sha256(current),
        evidence_refs=refs,
    )


def settle_carrier_conditioned_option_prediction(
    prediction: CarrierConditionedOptionPrediction,
    *,
    projection: Any,
    observed_states: Iterable[Any],
    environment_source_sha256: str,
    evidence_refs: Iterable[str],
    boundary_kind: str = "",
    effect: EffectFunction = fiber_mechanism_effect,
) -> CarrierConditionedOptionSettlement:
    """Settle one prediction against a complete observed state path."""

    states = tuple(observed_states)
    if len(states) != len(prediction.operations) + 1:
        raise ValueError("observed option path length drifted from prediction")
    observed_effects = tuple(
        effect(projection.factor(source), projection.factor(target))
        for source, target in zip(states, states[1:])
    )
    observed_hashes = tuple(stable_sha256(state) for state in states[1:])
    source_sha = stable_sha256(states[0])
    final_sha = stable_sha256(states[-1])
    failed_step = next(
        (
            index
            for index, (predicted, observed) in enumerate(zip(
                prediction.predicted_intermediate_state_sha256s,
                observed_hashes,
            ))
            if predicted != observed
        ),
        None,
    )
    if prediction.status != "predicted":
        status = "prediction_refused"
        failed_step = prediction.failed_step
    elif source_sha != prediction.source_state_sha256:
        status = "source_mismatch"
        failed_step = 0
    elif str(boundary_kind).strip():
        status = "boundary_crossed"
    elif (
        observed_effects == prediction.predicted_effect_trace
        and observed_hashes
        == prediction.predicted_intermediate_state_sha256s
        and final_sha == prediction.predicted_final_state_sha256
    ):
        status = "effect_confirmed"
        failed_step = None
    else:
        status = "counterexample"
        if failed_step is None:
            failed_step = next(
                (
                    index
                    for index, (predicted, observed) in enumerate(zip(
                        prediction.predicted_effect_trace,
                        observed_effects,
                    ))
                    if predicted != observed
                ),
                len(prediction.operations) - 1,
            )
    return CarrierConditionedOptionSettlement(
        prediction=prediction,
        environment_source_sha256=_required_digest(
            environment_source_sha256,
            "environment_source_sha256",
        ),
        observed_source_state_sha256=source_sha,
        observed_effect_trace=observed_effects,
        observed_intermediate_state_sha256s=observed_hashes,
        observed_final_state_sha256=final_sha,
        evidence_refs=_required_refs(evidence_refs, "option settlement"),
        status=status,
        boundary_kind=str(boundary_kind).strip(),
        failed_step=failed_step,
    )
