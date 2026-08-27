"""Exact state-dependent kinetics for authority-typed capability networks.

RAF membership and a feasible stoichiometric flux describe reaction potential.
This module asks whether one exact capability stock makes those reactions fast
enough to outrun depreciation and error growth under the same primitive-cost
rate.  Synthetic rate laws remain theory fixtures unless their evidence refs
are backed by prospective external settlements.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Iterable, Mapping, Sequence

from ztare.common.capability_autocatalysis import (
    CapabilityAuthority,
    CapabilityAutocatalysisReceipt,
    CapabilitySpecies,
    CatalyticCapabilityReaction,
)
from ztare.common.epistemic_autocatalysis import stable_sha256


SCHEMA = "ztare-capability-kinetics-v1"


def _nonempty(value: object, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} is required")
    return text


def _canonical(values: Iterable[object]) -> tuple[str, ...]:
    return tuple(sorted({_nonempty(value, "identity") for value in values}))


def _exact_fraction(value: object, name: str) -> Fraction:
    if isinstance(value, bool) or isinstance(value, float):
        raise TypeError(f"{name} must be an exact rational")
    if not isinstance(value, (Fraction, int, str)):
        raise TypeError(f"{name} must be an exact rational")
    try:
        result = value if isinstance(value, Fraction) else Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(f"{name} must be an exact rational") from exc
    if result < 0:
        raise ValueError(f"{name} must be nonnegative")
    return result


def _fraction_text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _exact_rows(
    values: Iterable[tuple[object, object]],
    name: str,
) -> tuple[tuple[str, Fraction], ...]:
    rows: dict[str, Fraction] = {}
    for raw_identity, raw_value in values:
        identity = _nonempty(raw_identity, f"{name}.identity")
        if identity in rows:
            raise ValueError(f"{name} repeats {identity!r}")
        rows[identity] = _exact_fraction(raw_value, f"{name}.{identity}")
    return tuple(sorted(rows.items()))


@dataclass(frozen=True)
class CapabilityReactionRateLaw:
    authority: CapabilityAuthority
    reaction_id: str
    reaction_sha256: str
    rate_constant: Fraction
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.authority, CapabilityAuthority):
            raise TypeError("authority must be a CapabilityAuthority")
        object.__setattr__(
            self,
            "reaction_id",
            _nonempty(self.reaction_id, "reaction_id"),
        )
        object.__setattr__(
            self,
            "reaction_sha256",
            _nonempty(self.reaction_sha256, "reaction_sha256"),
        )
        object.__setattr__(
            self,
            "rate_constant",
            _exact_fraction(self.rate_constant, "rate_constant"),
        )
        evidence = _canonical(self.evidence_refs)
        if not evidence:
            raise ValueError("reaction rate law requires evidence")
        object.__setattr__(self, "evidence_refs", evidence)

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "capability_reaction_rate_law",
            "authority_sha256": self.authority.sha256,
            "reaction_id": self.reaction_id,
            "reaction_sha256": self.reaction_sha256,
            "rate_constant": _fraction_text(self.rate_constant),
            "evidence_refs": list(self.evidence_refs),
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


@dataclass(frozen=True)
class CapabilityKineticModel:
    authority: CapabilityAuthority
    autocatalysis_receipt_sha256: str
    reaction_rate_laws: tuple[CapabilityReactionRateLaw, ...]
    depreciation_rates: tuple[tuple[str, Fraction], ...]
    primitive_budget_rate: Fraction
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.authority, CapabilityAuthority):
            raise TypeError("authority must be a CapabilityAuthority")
        object.__setattr__(
            self,
            "autocatalysis_receipt_sha256",
            _nonempty(
                self.autocatalysis_receipt_sha256,
                "autocatalysis_receipt_sha256",
            ),
        )
        laws = tuple(sorted(
            self.reaction_rate_laws,
            key=lambda row: row.reaction_id,
        ))
        if not laws:
            raise ValueError("kinetic model requires reaction rate laws")
        if any(not isinstance(row, CapabilityReactionRateLaw) for row in laws):
            raise TypeError("invalid reaction rate law")
        if any(row.authority != self.authority for row in laws):
            raise ValueError("reaction rate law crossed kinetic authority")
        if len({row.reaction_id for row in laws}) != len(laws):
            raise ValueError("reaction rate laws repeat a reaction identity")
        object.__setattr__(self, "reaction_rate_laws", laws)
        depreciation = _exact_rows(
            self.depreciation_rates,
            "depreciation_rates",
        )
        if not depreciation:
            raise ValueError("kinetic model requires depreciation rates")
        object.__setattr__(self, "depreciation_rates", depreciation)
        object.__setattr__(
            self,
            "primitive_budget_rate",
            _exact_fraction(
                self.primitive_budget_rate,
                "primitive_budget_rate",
            ),
        )
        evidence = _canonical(self.evidence_refs)
        if not evidence:
            raise ValueError("kinetic model requires evidence")
        object.__setattr__(self, "evidence_refs", evidence)

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "capability_kinetic_model",
            "authority_sha256": self.authority.sha256,
            "autocatalysis_receipt_sha256": (
                self.autocatalysis_receipt_sha256
            ),
            "reaction_rate_laws": [
                row.to_receipt() for row in self.reaction_rate_laws
            ],
            "depreciation_rates": [
                {
                    "species_id": species_id,
                    "rate": _fraction_text(rate),
                }
                for species_id, rate in self.depreciation_rates
            ],
            "primitive_budget_rate": _fraction_text(
                self.primitive_budget_rate
            ),
            "evidence_refs": list(self.evidence_refs),
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


@dataclass(frozen=True)
class CapabilityStockState:
    authority: CapabilityAuthority
    kinetic_model_sha256: str
    state_id: str
    scale_parameter: Fraction
    species_amounts: tuple[tuple[str, Fraction], ...]
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.authority, CapabilityAuthority):
            raise TypeError("authority must be a CapabilityAuthority")
        object.__setattr__(
            self,
            "kinetic_model_sha256",
            _nonempty(self.kinetic_model_sha256, "kinetic_model_sha256"),
        )
        object.__setattr__(
            self,
            "state_id",
            _nonempty(self.state_id, "state_id"),
        )
        object.__setattr__(
            self,
            "scale_parameter",
            _exact_fraction(self.scale_parameter, "scale_parameter"),
        )
        amounts = _exact_rows(self.species_amounts, "species_amounts")
        if not amounts:
            raise ValueError("capability stock state requires species amounts")
        object.__setattr__(self, "species_amounts", amounts)
        evidence = _canonical(self.evidence_refs)
        if not evidence:
            raise ValueError("capability stock state requires evidence")
        object.__setattr__(self, "evidence_refs", evidence)

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "capability_stock_state",
            "authority_sha256": self.authority.sha256,
            "kinetic_model_sha256": self.kinetic_model_sha256,
            "state_id": self.state_id,
            "scale_parameter": _fraction_text(self.scale_parameter),
            "species_amounts": [
                {
                    "species_id": species_id,
                    "amount": _fraction_text(amount),
                }
                for species_id, amount in self.species_amounts
            ],
            "evidence_refs": list(self.evidence_refs),
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


@dataclass(frozen=True)
class CapabilityKineticDriftReceipt:
    topology_sha256: str
    model: CapabilityKineticModel
    state: CapabilityStockState
    reaction_rates: tuple[tuple[str, Fraction], ...]
    internal_drift: tuple[tuple[str, Fraction], ...]
    primitive_cost_rate: Fraction
    status: str
    reason: str

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "capability_kinetic_drift_receipt",
            "topology_sha256": self.topology_sha256,
            "model": self.model.to_receipt(),
            "state": self.state.to_receipt(),
            "reaction_rates": [
                {
                    "reaction_id": reaction_id,
                    "rate": _fraction_text(rate),
                }
                for reaction_id, rate in self.reaction_rates
            ],
            "internal_drift": [
                {
                    "species_id": species_id,
                    "drift": _fraction_text(drift),
                }
                for species_id, drift in self.internal_drift
            ],
            "primitive_cost_rate": _fraction_text(
                self.primitive_cost_rate
            ),
            "status": self.status,
            "reason": self.reason,
            "takeoff_supported": False,
            "measured_kinetic_parameters_required": True,
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


@dataclass(frozen=True)
class CapabilityCriticalBracketReceipt:
    lower: CapabilityKineticDriftReceipt
    upper: CapabilityKineticDriftReceipt
    capability_species_ids: tuple[str, ...]
    fixed_food_species_ids: tuple[str, ...]
    status: str
    reason: str

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "capability_critical_bracket_receipt",
            "lower": self.lower.to_receipt(),
            "upper": self.upper.to_receipt(),
            "capability_species_ids": list(self.capability_species_ids),
            "fixed_food_species_ids": list(self.fixed_food_species_ids),
            "status": self.status,
            "reason": self.reason,
            "continuity_basis": "exact_polynomial_mass_action",
            "takeoff_supported": False,
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def _reaction_rate(
    reaction: CatalyticCapabilityReaction,
    law: CapabilityReactionRateLaw,
    amounts: Mapping[str, Fraction],
) -> Fraction:
    rate = law.rate_constant
    for species_id, count in reaction.reactants:
        rate *= amounts[species_id] ** count
    for species_id in reaction.catalyst_species_ids:
        rate *= amounts[species_id]
    return rate


def _validate_model(
    topology: CapabilityAutocatalysisReceipt,
    model: CapabilityKineticModel,
) -> None:
    if model.authority != topology.authority:
        raise ValueError("kinetic model crossed topology authority")
    if model.autocatalysis_receipt_sha256 != topology.sha256:
        raise ValueError("kinetic model crossed autocatalysis receipt")
    reactions = {row.reaction_id: row for row in topology.reactions}
    laws = {row.reaction_id: row for row in model.reaction_rate_laws}
    if set(laws) != set(reactions):
        raise ValueError("kinetic model must bind every reaction exactly once")
    for reaction_id, reaction in reactions.items():
        if laws[reaction_id].reaction_sha256 != reaction.sha256:
            raise ValueError("kinetic rate law crossed reaction identity")
    dynamic_ids = {
        row.species_id
        for row in topology.species
        if row.role in {"capability", "error"}
    }
    depreciation_ids = {
        species_id for species_id, _rate in model.depreciation_rates
    }
    if depreciation_ids != dynamic_ids:
        raise ValueError(
            "kinetic model must bind every capability/error depreciation rate"
        )


def compile_capability_kinetic_drift(
    topology: CapabilityAutocatalysisReceipt,
    model: CapabilityKineticModel,
    state: CapabilityStockState,
) -> CapabilityKineticDriftReceipt:
    """Compile exact mass-action drift and resource rate at one stock state."""

    if not isinstance(topology, CapabilityAutocatalysisReceipt):
        raise TypeError("topology must be a CapabilityAutocatalysisReceipt")
    if not isinstance(model, CapabilityKineticModel):
        raise TypeError("model must be a CapabilityKineticModel")
    if not isinstance(state, CapabilityStockState):
        raise TypeError("state must be a CapabilityStockState")
    _validate_model(topology, model)
    if state.authority != model.authority:
        raise ValueError("capability stock state crossed kinetic authority")
    if state.kinetic_model_sha256 != model.sha256:
        raise ValueError("capability stock state crossed kinetic model")
    species = {row.species_id: row for row in topology.species}
    amounts = dict(state.species_amounts)
    if set(amounts) != set(species):
        raise ValueError("stock state must bind every topology species exactly")
    laws = {row.reaction_id: row for row in model.reaction_rate_laws}
    rates = {
        reaction.reaction_id: _reaction_rate(
            reaction,
            laws[reaction.reaction_id],
            amounts,
        )
        for reaction in topology.reactions
    }
    depreciation = dict(model.depreciation_rates)
    dynamic_species = tuple(
        row for row in topology.species if row.role in {"capability", "error"}
    )
    drift = {
        row.species_id: sum(
            (
                reaction.coefficient(row.species_id)
                * rates[reaction.reaction_id]
                for reaction in topology.reactions
                if not reaction.bootstrap
            ),
            Fraction(0),
        ) - depreciation[row.species_id] * amounts[row.species_id]
        for row in dynamic_species
    }
    cost_rate = sum(
        (
            reaction.primitive_cost * rates[reaction.reaction_id]
            for reaction in topology.reactions
        ),
        Fraction(0),
    )
    capability_ids = tuple(
        row.species_id for row in dynamic_species if row.role == "capability"
    )
    error_ids = tuple(
        row.species_id for row in dynamic_species if row.role == "error"
    )
    if topology.status != "productive_autocatalytic_core":
        status = "topology_not_productive"
        reason = "autocatalysis_receipt_lacks_productive_core"
    elif any(drift[species_id] > 0 for species_id in error_ids):
        status = "error_rate_unstable"
        reason = "positive_error_drift"
    elif not capability_ids or any(
        drift[species_id] <= 0 for species_id in capability_ids
    ):
        status = "kinetically_subcritical"
        reason = "capability_reaction_rate_did_not_outrun_depreciation"
    elif cost_rate > model.primitive_budget_rate:
        status = "resource_rate_blocked"
        reason = "productive_rate_exceeded_primitive_budget_rate"
    else:
        status = "kinetically_supercritical_candidate"
        reason = "positive_capability_drift_with_stable_errors_within_budget"
    return CapabilityKineticDriftReceipt(
        topology_sha256=topology.sha256,
        model=model,
        state=state,
        reaction_rates=tuple(sorted(rates.items())),
        internal_drift=tuple(sorted(drift.items())),
        primitive_cost_rate=cost_rate,
        status=status,
        reason=reason,
    )


def compile_capability_critical_bracket(
    topology: CapabilityAutocatalysisReceipt,
    lower: CapabilityKineticDriftReceipt,
    upper: CapabilityKineticDriftReceipt,
) -> CapabilityCriticalBracketReceipt:
    """Certify a fixed-model subcritical-to-supercritical stock bracket."""

    if not isinstance(topology, CapabilityAutocatalysisReceipt):
        raise TypeError("topology must be a CapabilityAutocatalysisReceipt")
    if lower.topology_sha256 != topology.sha256:
        raise ValueError("lower drift crossed topology identity")
    if upper.topology_sha256 != topology.sha256:
        raise ValueError("upper drift crossed topology identity")
    if lower.model.sha256 != upper.model.sha256:
        raise ValueError("critical bracket crossed kinetic model")
    if lower.state.kinetic_model_sha256 != lower.model.sha256:
        raise ValueError("lower state crossed kinetic model")
    if upper.state.kinetic_model_sha256 != upper.model.sha256:
        raise ValueError("upper state crossed kinetic model")
    if lower.state.scale_parameter >= upper.state.scale_parameter:
        raise ValueError("critical bracket scale did not increase")
    lower_amounts = dict(lower.state.species_amounts)
    upper_amounts = dict(upper.state.species_amounts)
    capabilities = tuple(sorted(
        row.species_id for row in topology.species
        if row.role == "capability"
    ))
    foods = tuple(sorted(
        row.species_id for row in topology.species if row.role == "food"
    ))
    errors = tuple(sorted(
        row.species_id for row in topology.species if row.role == "error"
    ))
    if any(lower_amounts[row] != upper_amounts[row] for row in foods):
        raise ValueError("critical bracket changed food stock")
    if any(lower_amounts[row] != upper_amounts[row] for row in errors):
        raise ValueError("critical bracket changed error stock")
    if any(lower_amounts[row] > upper_amounts[row] for row in capabilities):
        raise ValueError("critical bracket decreased a capability stock")
    if not any(
        lower_amounts[row] < upper_amounts[row] for row in capabilities
    ):
        raise ValueError("critical bracket did not increase capability stock")
    if lower.status != "kinetically_subcritical":
        raise ValueError("critical bracket lower state is not subcritical")
    if upper.status != "kinetically_supercritical_candidate":
        raise ValueError("critical bracket upper state is not supercritical")
    return CapabilityCriticalBracketReceipt(
        lower=lower,
        upper=upper,
        capability_species_ids=capabilities,
        fixed_food_species_ids=foods,
        status="critical_stock_bracket",
        reason="fixed_model_exact_drift_changed_sign_across_capability_stock",
    )


__all__ = [
    "CapabilityCriticalBracketReceipt",
    "CapabilityKineticDriftReceipt",
    "CapabilityKineticModel",
    "CapabilityReactionRateLaw",
    "CapabilityStockState",
    "compile_capability_critical_bracket",
    "compile_capability_kinetic_drift",
]
