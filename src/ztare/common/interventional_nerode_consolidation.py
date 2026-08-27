"""Epoch-frozen causal consolidation over immutable episode fibers.

The quotient never owns or replaces an episode.  It learns a provisional
predictive state from matched intervention contrasts, seals that state, and
lets fresh fibers either validate it or become counterexamples for a later
epoch.  Substrate-specific feature meanings and environment outcomes remain
caller-owned.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import itertools
import json
from typing import Any, Iterable, Mapping, Sequence


SCHEMA = "ztare-interventional-nerode-consolidation-v1"


def stable_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _nonempty(value: object, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} is required")
    return text


def _fraction(value: Fraction | int | str, name: str) -> Fraction:
    try:
        result = value if isinstance(value, Fraction) else Fraction(value)
    except (TypeError, ValueError, ZeroDivisionError) as exc:
        raise ValueError(f"{name} must be an exact rational") from exc
    return result


def _fraction_text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def pre_observation_occurrence_sha256(
    *,
    parent_state_sha256: str,
    pre_proposal_sha256: str,
    pre_observation_content_sha256: str,
) -> str:
    """Identify one observation occurrence without conflating equal content."""

    return stable_sha256({
        "parent_state_sha256": _nonempty(
            parent_state_sha256,
            "parent_state_sha256",
        ),
        "pre_proposal_sha256": _nonempty(
            pre_proposal_sha256,
            "pre_proposal_sha256",
        ),
        "pre_observation_content_sha256": _nonempty(
            pre_observation_content_sha256,
            "pre_observation_content_sha256",
        ),
    })


def canonical_projection_library(
    feature_catalog: Iterable[str],
) -> tuple[tuple[str, ...], ...]:
    """Enumerate every feature mask in coarsest-first canonical order."""

    features = tuple(sorted({_nonempty(row, "feature key") for row in feature_catalog}))
    if not features:
        raise ValueError("feature catalog must be nonempty")
    return tuple(
        combination
        for size in range(len(features) + 1)
        for combination in itertools.combinations(features, size)
    )


@dataclass(frozen=True)
class InterventionalNerodeAuthority:
    scope_sha256: str
    response_program_sha256: str
    derivative_sha256: str
    eligibility_rule_sha256: str
    intervention_set_sha256: str
    utility_measure_sha256: str
    restored_prefix_sha256: str
    feature_catalog: tuple[str, ...]
    candidate_projections: tuple[tuple[str, ...], ...]
    training_set_sha256: str
    primitive_action_cost: Fraction
    epoch: int
    minimum_training_fibers: int = 2
    minimum_holdout_fibers: int = 2

    def __post_init__(self) -> None:
        for name in (
            "scope_sha256",
            "response_program_sha256",
            "derivative_sha256",
            "eligibility_rule_sha256",
            "intervention_set_sha256",
            "utility_measure_sha256",
            "restored_prefix_sha256",
            "training_set_sha256",
        ):
            object.__setattr__(self, name, _nonempty(getattr(self, name), name))
        features = tuple(sorted({_nonempty(row, "feature key") for row in self.feature_catalog}))
        if not features:
            raise ValueError("feature_catalog must be nonempty")
        expected = canonical_projection_library(features)
        projections = tuple(tuple(row) for row in self.candidate_projections)
        if projections != expected:
            raise ValueError("candidate projection library is incomplete or noncanonical")
        if self.epoch < 1:
            raise ValueError("epoch must be positive")
        if self.minimum_training_fibers < 2 or self.minimum_holdout_fibers < 2:
            raise ValueError("consolidation needs at least two exact fibers")
        cost = _fraction(self.primitive_action_cost, "primitive_action_cost")
        if cost <= 0:
            raise ValueError("primitive_action_cost must be positive")
        object.__setattr__(self, "feature_catalog", features)
        object.__setattr__(self, "candidate_projections", projections)
        object.__setattr__(self, "primitive_action_cost", cost)

    def to_receipt(self) -> dict[str, Any]:
        core = {
            "schema": SCHEMA,
            "kind": "interventional_nerode_authority",
            "scope_sha256": self.scope_sha256,
            "response_program_sha256": self.response_program_sha256,
            "derivative_sha256": self.derivative_sha256,
            "eligibility_rule_sha256": self.eligibility_rule_sha256,
            "intervention_set_sha256": self.intervention_set_sha256,
            "utility_measure_sha256": self.utility_measure_sha256,
            "restored_prefix_sha256": self.restored_prefix_sha256,
            "feature_catalog": list(self.feature_catalog),
            "candidate_projections": [list(row) for row in self.candidate_projections],
            "training_set_sha256": self.training_set_sha256,
            "primitive_action_cost": _fraction_text(self.primitive_action_cost),
            "epoch": self.epoch,
            "minimum_training_fibers": self.minimum_training_fibers,
            "minimum_holdout_fibers": self.minimum_holdout_fibers,
        }
        return {**core, "sha256": stable_sha256(core)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def interventional_nerode_authority_from_receipt(
    receipt: Mapping[str, Any],
) -> InterventionalNerodeAuthority:
    """Rehydrate and hash-check one frozen consolidation authority."""

    if receipt.get("schema") != SCHEMA:
        raise ValueError("unknown interventional Nerode receipt schema")
    if receipt.get("kind") != "interventional_nerode_authority":
        raise ValueError("receipt is not an interventional Nerode authority")
    authority = InterventionalNerodeAuthority(
        scope_sha256=str(receipt["scope_sha256"]),
        response_program_sha256=str(receipt["response_program_sha256"]),
        derivative_sha256=str(receipt["derivative_sha256"]),
        eligibility_rule_sha256=str(receipt["eligibility_rule_sha256"]),
        intervention_set_sha256=str(receipt["intervention_set_sha256"]),
        utility_measure_sha256=str(receipt["utility_measure_sha256"]),
        restored_prefix_sha256=str(receipt["restored_prefix_sha256"]),
        feature_catalog=tuple(receipt["feature_catalog"]),
        candidate_projections=tuple(
            tuple(row) for row in receipt["candidate_projections"]
        ),
        training_set_sha256=str(receipt["training_set_sha256"]),
        primitive_action_cost=Fraction(str(receipt["primitive_action_cost"])),
        epoch=int(receipt["epoch"]),
        minimum_training_fibers=int(receipt["minimum_training_fibers"]),
        minimum_holdout_fibers=int(receipt["minimum_holdout_fibers"]),
    )
    if authority.to_receipt() != dict(receipt):
        raise ValueError("interventional Nerode authority receipt drifted")
    return authority


@dataclass(frozen=True)
class ExactInterventionalFiber:
    authority_sha256: str
    fiber_sha256: str
    parent_state_sha256: str
    pre_proposal_sha256: str
    pre_observation_content_sha256: str
    pre_observation_occurrence_sha256: str
    exact_micro_basin_sha256: str
    feature_values: tuple[tuple[str, str], ...]
    fork_authority_sha256: str
    offer_transition_sha256: str
    withhold_transition_sha256: str
    offer_evidence_sha256: str
    withhold_evidence_sha256: str
    offer_supported: bool
    withhold_supported: bool
    task_delta: int
    value_delta: Fraction
    offer_primitive_action_cost: Fraction
    withhold_primitive_action_cost: Fraction
    evidence_refs: tuple[str, ...]
    phase: str

    def __post_init__(self) -> None:
        for name in (
            "authority_sha256",
            "fiber_sha256",
            "parent_state_sha256",
            "pre_proposal_sha256",
            "pre_observation_content_sha256",
            "pre_observation_occurrence_sha256",
            "exact_micro_basin_sha256",
            "fork_authority_sha256",
            "offer_transition_sha256",
            "withhold_transition_sha256",
            "offer_evidence_sha256",
            "withhold_evidence_sha256",
        ):
            object.__setattr__(self, name, _nonempty(getattr(self, name), name))
        if self.phase not in {"training", "holdout"}:
            raise ValueError("fiber phase must be training or holdout")
        features = tuple(sorted(
            (_nonempty(key, "feature key"), str(value))
            for key, value in self.feature_values
        ))
        if len({key for key, _value in features}) != len(features):
            raise ValueError("fiber repeats a feature key")
        offer_cost = _fraction(
            self.offer_primitive_action_cost,
            "offer_primitive_action_cost",
        )
        withhold_cost = _fraction(
            self.withhold_primitive_action_cost,
            "withhold_primitive_action_cost",
        )
        if offer_cost <= 0 or withhold_cost <= 0 or offer_cost != withhold_cost:
            raise ValueError("matched fiber primitive costs must be equal and positive")
        refs = tuple(sorted({_nonempty(row, "evidence ref") for row in self.evidence_refs}))
        if not refs:
            raise ValueError("fiber needs evidence refs")
        object.__setattr__(self, "feature_values", features)
        object.__setattr__(self, "value_delta", _fraction(self.value_delta, "value_delta"))
        object.__setattr__(self, "offer_primitive_action_cost", offer_cost)
        object.__setattr__(self, "withhold_primitive_action_cost", withhold_cost)
        object.__setattr__(self, "evidence_refs", refs)
        expected_occurrence = pre_observation_occurrence_sha256(
            parent_state_sha256=self.parent_state_sha256,
            pre_proposal_sha256=self.pre_proposal_sha256,
            pre_observation_content_sha256=(
                self.pre_observation_content_sha256
            ),
        )
        if self.pre_observation_occurrence_sha256 != expected_occurrence:
            raise ValueError(
                "pre_observation_occurrence_sha256 crossed its content identity"
            )
        if self.fiber_sha256 != stable_sha256(self.identity_payload()):
            raise ValueError("fiber_sha256 is not its canonical content identity")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "authority_sha256": self.authority_sha256,
            "parent_state_sha256": self.parent_state_sha256,
            "pre_proposal_sha256": self.pre_proposal_sha256,
            "pre_observation_content_sha256": (
                self.pre_observation_content_sha256
            ),
            "pre_observation_occurrence_sha256": (
                self.pre_observation_occurrence_sha256
            ),
            "exact_micro_basin_sha256": self.exact_micro_basin_sha256,
            "feature_values": [list(row) for row in self.feature_values],
            "fork_authority_sha256": self.fork_authority_sha256,
            "offer_transition_sha256": self.offer_transition_sha256,
            "withhold_transition_sha256": self.withhold_transition_sha256,
            "offer_evidence_sha256": self.offer_evidence_sha256,
            "withhold_evidence_sha256": self.withhold_evidence_sha256,
            "offer_supported": self.offer_supported,
            "withhold_supported": self.withhold_supported,
            "task_delta": self.task_delta,
            "value_delta": _fraction_text(self.value_delta),
            "offer_primitive_action_cost": _fraction_text(
                self.offer_primitive_action_cost
            ),
            "withhold_primitive_action_cost": _fraction_text(
                self.withhold_primitive_action_cost
            ),
            "evidence_refs": list(self.evidence_refs),
            "phase": self.phase,
        }

    def feature_map(self) -> dict[str, str]:
        return dict(self.feature_values)

    def to_receipt(self) -> dict[str, Any]:
        core = {
            "schema": SCHEMA,
            "kind": "exact_interventional_fiber",
            "authority_sha256": self.authority_sha256,
            "fiber_sha256": self.fiber_sha256,
            "parent_state_sha256": self.parent_state_sha256,
            "pre_proposal_sha256": self.pre_proposal_sha256,
            "pre_observation_content_sha256": (
                self.pre_observation_content_sha256
            ),
            "pre_observation_occurrence_sha256": (
                self.pre_observation_occurrence_sha256
            ),
            "exact_micro_basin_sha256": self.exact_micro_basin_sha256,
            "feature_values": [list(row) for row in self.feature_values],
            "fork_authority_sha256": self.fork_authority_sha256,
            "offer_transition_sha256": self.offer_transition_sha256,
            "withhold_transition_sha256": self.withhold_transition_sha256,
            "offer_evidence_sha256": self.offer_evidence_sha256,
            "withhold_evidence_sha256": self.withhold_evidence_sha256,
            "offer_supported": self.offer_supported,
            "withhold_supported": self.withhold_supported,
            "task_delta": self.task_delta,
            "value_delta": _fraction_text(self.value_delta),
            "offer_primitive_action_cost": _fraction_text(
                self.offer_primitive_action_cost
            ),
            "withhold_primitive_action_cost": _fraction_text(
                self.withhold_primitive_action_cost
            ),
            "evidence_refs": list(self.evidence_refs),
            "phase": self.phase,
        }
        return {**core, "sha256": stable_sha256(core)}


def compile_exact_interventional_fiber(
    *,
    authority_sha256: str,
    parent_state_sha256: str,
    pre_proposal_sha256: str,
    pre_observation_content_sha256: str,
    exact_micro_basin_sha256: str,
    feature_values: Iterable[tuple[str, str]],
    fork_authority_sha256: str,
    offer_transition_sha256: str,
    withhold_transition_sha256: str,
    offer_evidence_sha256: str,
    withhold_evidence_sha256: str,
    offer_supported: bool,
    withhold_supported: bool,
    task_delta: int,
    value_delta: Fraction | int | str,
    offer_primitive_action_cost: Fraction | int | str,
    withhold_primitive_action_cost: Fraction | int | str,
    evidence_refs: Iterable[str],
    phase: str,
) -> ExactInterventionalFiber:
    normalized_features = tuple(sorted((str(key), str(value)) for key, value in feature_values))
    normalized_refs = tuple(sorted(set(str(row) for row in evidence_refs)))
    value = _fraction(value_delta, "value_delta")
    offer_cost = _fraction(offer_primitive_action_cost, "offer_primitive_action_cost")
    withhold_cost = _fraction(
        withhold_primitive_action_cost,
        "withhold_primitive_action_cost",
    )
    occurrence_sha256 = pre_observation_occurrence_sha256(
        parent_state_sha256=str(parent_state_sha256),
        pre_proposal_sha256=str(pre_proposal_sha256),
        pre_observation_content_sha256=str(pre_observation_content_sha256),
    )
    identity = {
        "authority_sha256": str(authority_sha256),
        "parent_state_sha256": str(parent_state_sha256),
        "pre_proposal_sha256": str(pre_proposal_sha256),
        "pre_observation_content_sha256": str(
            pre_observation_content_sha256
        ),
        "pre_observation_occurrence_sha256": occurrence_sha256,
        "exact_micro_basin_sha256": str(exact_micro_basin_sha256),
        "feature_values": [list(row) for row in normalized_features],
        "fork_authority_sha256": str(fork_authority_sha256),
        "offer_transition_sha256": str(offer_transition_sha256),
        "withhold_transition_sha256": str(withhold_transition_sha256),
        "offer_evidence_sha256": str(offer_evidence_sha256),
        "withhold_evidence_sha256": str(withhold_evidence_sha256),
        "offer_supported": bool(offer_supported),
        "withhold_supported": bool(withhold_supported),
        "task_delta": int(task_delta),
        "value_delta": _fraction_text(value),
        "offer_primitive_action_cost": _fraction_text(offer_cost),
        "withhold_primitive_action_cost": _fraction_text(withhold_cost),
        "evidence_refs": list(normalized_refs),
        "phase": str(phase),
    }
    return ExactInterventionalFiber(
        authority_sha256=str(authority_sha256),
        fiber_sha256=stable_sha256(identity),
        parent_state_sha256=str(parent_state_sha256),
        pre_proposal_sha256=str(pre_proposal_sha256),
        pre_observation_content_sha256=str(pre_observation_content_sha256),
        pre_observation_occurrence_sha256=occurrence_sha256,
        exact_micro_basin_sha256=str(exact_micro_basin_sha256),
        feature_values=normalized_features,
        fork_authority_sha256=str(fork_authority_sha256),
        offer_transition_sha256=str(offer_transition_sha256),
        withhold_transition_sha256=str(withhold_transition_sha256),
        offer_evidence_sha256=str(offer_evidence_sha256),
        withhold_evidence_sha256=str(withhold_evidence_sha256),
        offer_supported=bool(offer_supported),
        withhold_supported=bool(withhold_supported),
        task_delta=int(task_delta),
        value_delta=value,
        offer_primitive_action_cost=offer_cost,
        withhold_primitive_action_cost=withhold_cost,
        evidence_refs=normalized_refs,
        phase=str(phase),
    )


def exact_interventional_fiber_from_receipt(
    receipt: Mapping[str, Any],
) -> ExactInterventionalFiber:
    """Rehydrate and hash-check one immutable episode fiber."""

    if receipt.get("schema") != SCHEMA:
        raise ValueError("unknown interventional Nerode receipt schema")
    if receipt.get("kind") != "exact_interventional_fiber":
        raise ValueError("receipt is not an exact interventional fiber")
    fiber = ExactInterventionalFiber(
        authority_sha256=str(receipt["authority_sha256"]),
        fiber_sha256=str(receipt["fiber_sha256"]),
        parent_state_sha256=str(receipt["parent_state_sha256"]),
        pre_proposal_sha256=str(receipt["pre_proposal_sha256"]),
        pre_observation_content_sha256=str(
            receipt["pre_observation_content_sha256"]
        ),
        pre_observation_occurrence_sha256=str(
            receipt["pre_observation_occurrence_sha256"]
        ),
        exact_micro_basin_sha256=str(receipt["exact_micro_basin_sha256"]),
        feature_values=tuple(
            (str(key), str(value)) for key, value in receipt["feature_values"]
        ),
        fork_authority_sha256=str(receipt["fork_authority_sha256"]),
        offer_transition_sha256=str(receipt["offer_transition_sha256"]),
        withhold_transition_sha256=str(receipt["withhold_transition_sha256"]),
        offer_evidence_sha256=str(receipt["offer_evidence_sha256"]),
        withhold_evidence_sha256=str(receipt["withhold_evidence_sha256"]),
        offer_supported=bool(receipt["offer_supported"]),
        withhold_supported=bool(receipt["withhold_supported"]),
        task_delta=int(receipt["task_delta"]),
        value_delta=Fraction(str(receipt["value_delta"])),
        offer_primitive_action_cost=Fraction(
            str(receipt["offer_primitive_action_cost"])
        ),
        withhold_primitive_action_cost=Fraction(
            str(receipt["withhold_primitive_action_cost"])
        ),
        evidence_refs=tuple(receipt["evidence_refs"]),
        phase=str(receipt["phase"]),
    )
    if fiber.to_receipt() != dict(receipt):
        raise ValueError("exact interventional fiber receipt drifted")
    return fiber


def _quotient_key(
    fiber: ExactInterventionalFiber,
    projection: Sequence[str],
) -> tuple[tuple[str, str], ...]:
    values = fiber.feature_map()
    return tuple((key, values[key]) for key in projection)


@dataclass(frozen=True)
class InterventionalNerodeState:
    authority_sha256: str
    projection: tuple[str, ...]
    quotient_key: tuple[tuple[str, str], ...]
    training_fiber_sha256s: tuple[str, ...]
    exact_micro_basin_sha256s: tuple[str, ...]
    predicted_value_delta: Fraction
    predicted_sign: str

    def to_receipt(self) -> dict[str, Any]:
        core = {
            "schema": SCHEMA,
            "kind": "interventional_nerode_state",
            "authority_sha256": self.authority_sha256,
            "projection": list(self.projection),
            "quotient_key": [list(row) for row in self.quotient_key],
            "training_fiber_sha256s": list(self.training_fiber_sha256s),
            "exact_micro_basin_sha256s": list(self.exact_micro_basin_sha256s),
            "predicted_value_delta": _fraction_text(self.predicted_value_delta),
            "predicted_sign": self.predicted_sign,
        }
        return {**core, "sha256": stable_sha256(core)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


@dataclass(frozen=True)
class InterventionalNerodeEpoch:
    authority: InterventionalNerodeAuthority
    selected_projection: tuple[str, ...]
    training_fibers: tuple[ExactInterventionalFiber, ...]
    states: tuple[InterventionalNerodeState, ...]

    def to_receipt(self) -> dict[str, Any]:
        core = {
            "schema": SCHEMA,
            "kind": "interventional_nerode_epoch",
            "authority": self.authority.to_receipt(),
            "selected_projection": list(self.selected_projection),
            "training_fibers": [row.to_receipt() for row in self.training_fibers],
            "states": [row.to_receipt() for row in self.states],
            "status": "provisional_prediction_model",
            "promotion_authorized": False,
            "compounding_supported": False,
            "takeoff_supported": False,
        }
        return {**core, "sha256": stable_sha256(core)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def interventional_nerode_epoch_from_receipt(
    receipt: Mapping[str, Any],
) -> InterventionalNerodeEpoch:
    """Recompile a sealed epoch from its exact authority and training fibers."""

    if receipt.get("schema") != SCHEMA:
        raise ValueError("unknown interventional Nerode receipt schema")
    if receipt.get("kind") != "interventional_nerode_epoch":
        raise ValueError("receipt is not an interventional Nerode epoch")
    authority = interventional_nerode_authority_from_receipt(
        dict(receipt["authority"])
    )
    fibers = tuple(
        exact_interventional_fiber_from_receipt(dict(row))
        for row in receipt["training_fibers"]
    )
    epoch = compile_interventional_nerode_epoch(authority, fibers)
    if epoch.to_receipt() != dict(receipt):
        raise ValueError("interventional Nerode epoch receipt drifted")
    return epoch


def _validate_fibers(
    authority: InterventionalNerodeAuthority,
    fibers: Sequence[ExactInterventionalFiber],
    *,
    phase: str,
) -> tuple[ExactInterventionalFiber, ...]:
    rows = tuple(sorted(fibers, key=lambda row: row.fiber_sha256))
    if not rows:
        raise ValueError("consolidation needs exact fibers")
    if any(row.authority_sha256 != authority.sha256 for row in rows):
        raise ValueError("fiber crossed consolidation authority")
    if any(row.phase != phase for row in rows):
        raise ValueError("fiber crossed training/holdout phase")
    if len({row.fiber_sha256 for row in rows}) != len(rows):
        raise ValueError("exact fiber identity was reused")
    if len({row.parent_state_sha256 for row in rows}) != len(rows):
        raise ValueError("stored parent state was reused")
    if len({row.pre_proposal_sha256 for row in rows}) != len(rows):
        raise ValueError("pre-proposal identity was reused")
    if (
        len({row.pre_observation_occurrence_sha256 for row in rows})
        != len(rows)
    ):
        raise ValueError("pre-observation occurrence identity was reused")
    if any(
        tuple(key for key, _value in row.feature_values)
        != authority.feature_catalog
        for row in rows
    ):
        raise ValueError("fiber feature catalog drifted")
    if any(
        row.offer_primitive_action_cost != authority.primitive_action_cost
        for row in rows
    ):
        raise ValueError("fiber primitive cost crossed authority")
    evidence = [
        identity
        for row in rows
        for identity in (
            row.offer_evidence_sha256,
            row.withhold_evidence_sha256,
        )
    ]
    if len(set(evidence)) != len(evidence):
        raise ValueError("settlement evidence was reused")
    return rows


def _projection_groups(
    fibers: Sequence[ExactInterventionalFiber],
    projection: Sequence[str],
) -> dict[tuple[tuple[str, str], ...], tuple[ExactInterventionalFiber, ...]]:
    groups: dict[tuple[tuple[str, str], ...], list[ExactInterventionalFiber]] = {}
    for fiber in fibers:
        groups.setdefault(_quotient_key(fiber, projection), []).append(fiber)
    return {
        key: tuple(sorted(rows, key=lambda row: row.fiber_sha256))
        for key, rows in groups.items()
    }


def _training_cell_valid(
    rows: Sequence[ExactInterventionalFiber],
    minimum: int,
) -> bool:
    return bool(
        len(rows) >= minimum
        and all(row.offer_supported and not row.withhold_supported for row in rows)
        and all(row.value_delta >= 0 for row in rows)
        and sum((row.value_delta for row in rows), Fraction(0)) > 0
        and sum(row.task_delta for row in rows) >= 0
    )


def compile_interventional_nerode_epoch(
    authority: InterventionalNerodeAuthority,
    training_fibers: Sequence[ExactInterventionalFiber],
) -> InterventionalNerodeEpoch:
    rows = _validate_fibers(authority, training_fibers, phase="training")
    candidates = []
    for projection in authority.candidate_projections:
        groups = _projection_groups(rows, projection)
        if all(
            _training_cell_valid(group, authority.minimum_training_fibers)
            for group in groups.values()
        ):
            candidates.append((projection, groups))
    if not candidates:
        raise ValueError("no candidate projection predicts the training contrasts")
    projection, groups = candidates[0]
    states = []
    for key, group in sorted(groups.items()):
        mean = sum((row.value_delta for row in group), Fraction(0)) / len(group)
        states.append(InterventionalNerodeState(
            authority_sha256=authority.sha256,
            projection=tuple(projection),
            quotient_key=key,
            training_fiber_sha256s=tuple(row.fiber_sha256 for row in group),
            exact_micro_basin_sha256s=tuple(sorted({
                row.exact_micro_basin_sha256 for row in group
            })),
            predicted_value_delta=mean,
            predicted_sign="positive" if mean > 0 else "nonpositive",
        ))
    return InterventionalNerodeEpoch(
        authority=authority,
        selected_projection=tuple(projection),
        training_fibers=rows,
        states=tuple(states),
    )


def _minimal_distinguishing_keys(
    fiber: ExactInterventionalFiber,
    training: Sequence[ExactInterventionalFiber],
    feature_catalog: Sequence[str],
) -> tuple[str, ...]:
    target = fiber.feature_map()
    training_maps = [row.feature_map() for row in training]
    for size in range(1, len(feature_catalog) + 1):
        for subset in itertools.combinations(feature_catalog, size):
            if all(
                any(target[key] != row[key] for key in subset)
                for row in training_maps
            ):
                return tuple(subset)
    return ()


@dataclass(frozen=True)
class InterventionalNerodeSettlement:
    epoch_sha256: str
    holdout_fibers: tuple[ExactInterventionalFiber, ...]
    checks: Mapping[str, bool]
    promoted_state_sha256s: tuple[str, ...]
    counterexamples: tuple[Mapping[str, Any], ...]

    @property
    def promoted(self) -> bool:
        return bool(self.promoted_state_sha256s) and all(self.checks.values())

    def to_receipt(self) -> dict[str, Any]:
        core = {
            "schema": SCHEMA,
            "kind": "interventional_nerode_settlement",
            "epoch_sha256": self.epoch_sha256,
            "holdout_fibers": [row.to_receipt() for row in self.holdout_fibers],
            "checks": dict(sorted(self.checks.items())),
            "status": "promoted" if self.promoted else "refinement_required",
            "promoted": self.promoted,
            "promoted_child_count": (
                len(self.promoted_state_sha256s) if self.promoted else 0
            ),
            "promoted_state_sha256s": (
                list(self.promoted_state_sha256s) if self.promoted else []
            ),
            "counterexamples": [dict(row) for row in self.counterexamples],
            "supercriticality_supported": False,
            "compounding_supported": False,
            "takeoff_supported": False,
        }
        return {**core, "sha256": stable_sha256(core)}


def settle_interventional_nerode_holdout(
    epoch: InterventionalNerodeEpoch,
    holdout_fibers: Sequence[ExactInterventionalFiber],
) -> InterventionalNerodeSettlement:
    rows = _validate_fibers(epoch.authority, holdout_fibers, phase="holdout")
    if len(rows) < epoch.authority.minimum_holdout_fibers:
        raise ValueError("holdout has insufficient exact fibers")
    training_fiber_ids = {row.fiber_sha256 for row in epoch.training_fibers}
    training_evidence_ids = {
        value
        for row in epoch.training_fibers
        for value in (row.offer_evidence_sha256, row.withhold_evidence_sha256)
    }
    if training_fiber_ids.intersection(row.fiber_sha256 for row in rows):
        raise ValueError("holdout reused a training fiber")
    if training_evidence_ids.intersection(
        value
        for row in rows
        for value in (row.offer_evidence_sha256, row.withhold_evidence_sha256)
    ):
        raise ValueError("holdout reused training evidence")

    state_by_key = {row.quotient_key: row for row in epoch.states}
    mappings = [
        state_by_key.get(_quotient_key(row, epoch.selected_projection))
        for row in rows
    ]
    known = all(state is not None for state in mappings)
    first_stage = all(
        row.offer_supported and not row.withhold_supported for row in rows
    )
    no_negative = all(row.value_delta >= 0 for row in rows)
    positive_mean = (
        sum((row.value_delta for row in rows), Fraction(0)) / len(rows) > 0
    )
    task_nonnegative = sum(row.task_delta for row in rows) >= 0
    at_least_one_win = any(row.value_delta > 0 for row in rows)
    prediction_signs = all(
        state is not None
        and state.predicted_sign == "positive"
        and row.value_delta >= 0
        for row, state in zip(rows, mappings)
    )
    mapped_state_ids = tuple(sorted({
        state.sha256 for state in mappings if state is not None
    }))
    one_state = len(mapped_state_ids) == 1
    checks = {
        "minimum_fresh_fibers": (
            len(rows) >= epoch.authority.minimum_holdout_fibers
        ),
        "known_frozen_state": known,
        "single_predicted_state": one_state,
        "target_first_stage_every_pair": first_stage,
        "no_negative_pair_delta": no_negative,
        "positive_mean_value_delta": positive_mean,
        "nonnegative_total_task_delta": task_nonnegative,
        "at_least_one_positive_pair": at_least_one_win,
        "sealed_sign_prediction_every_pair": prediction_signs,
        "training_holdout_identity_disjoint": True,
    }
    passed = all(checks.values())
    counterexamples = []
    if not passed:
        failed_rows = [
            row for row, state in zip(rows, mappings)
            if (
                state is None
                or not row.offer_supported
                or row.withhold_supported
                or row.value_delta < 0
            )
        ]
        if not failed_rows:
            failed_rows = list(rows)
        for row in failed_rows:
            keys = _minimal_distinguishing_keys(
                row,
                epoch.training_fibers,
                epoch.authority.feature_catalog,
            )
            counterexamples.append({
                "fiber_sha256": row.fiber_sha256,
                "exact_micro_basin_sha256": row.exact_micro_basin_sha256,
                "minimal_distinguishing_feature_keys": list(keys),
                "frozen_catalog_has_distinguishing_projection": bool(keys),
                "next_epoch_required": True,
            })
    return InterventionalNerodeSettlement(
        epoch_sha256=epoch.sha256,
        holdout_fibers=rows,
        checks=checks,
        promoted_state_sha256s=mapped_state_ids if passed else (),
        counterexamples=tuple(counterexamples),
    )


__all__ = [
    "ExactInterventionalFiber",
    "InterventionalNerodeAuthority",
    "InterventionalNerodeEpoch",
    "InterventionalNerodeSettlement",
    "InterventionalNerodeState",
    "canonical_projection_library",
    "compile_exact_interventional_fiber",
    "compile_interventional_nerode_epoch",
    "exact_interventional_fiber_from_receipt",
    "interventional_nerode_authority_from_receipt",
    "interventional_nerode_epoch_from_receipt",
    "pre_observation_occurrence_sha256",
    "settle_interventional_nerode_holdout",
    "stable_sha256",
]
