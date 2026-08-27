"""Authority-typed catalytic closure for compounding capabilities.

The compiler separates topological recurrence, food generation, catalysis,
stoichiometric production, error dissipation, and primitive-contact cost.  A
cycle alone cannot pass.  The positive receipt owns one bounded exact integer
flux; it does not claim that the reactions were generated autonomously or
observed in a live environment.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import itertools
from typing import Any, Iterable, Mapping, Sequence

from ztare.common.epistemic_autocatalysis import stable_sha256
from ztare.common.wake_sleep_credit_router import MemoryScope


SCHEMA = "ztare-capability-autocatalysis-v1"
_ROLES = frozenset({"food", "capability", "error"})


def _nonempty(value: object, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} is required")
    return text


def _canonical(values: Iterable[object]) -> tuple[str, ...]:
    return tuple(sorted({_nonempty(value, "identity") for value in values}))


def _fraction(value: object, name: str) -> Fraction:
    if isinstance(value, bool):
        raise TypeError(f"{name} cannot be Boolean")
    result = value if isinstance(value, Fraction) else Fraction(value)
    if result < 0:
        raise ValueError(f"{name} must be nonnegative")
    return result


def _stoichiometry(
    values: Iterable[tuple[object, object]],
    name: str,
) -> tuple[tuple[str, int], ...]:
    combined: dict[str, int] = {}
    for raw_species, raw_count in values:
        species = _nonempty(raw_species, f"{name}.species_id")
        if (
            isinstance(raw_count, bool)
            or int(raw_count) != raw_count
            or int(raw_count) <= 0
        ):
            raise ValueError(f"{name} counts must be positive integers")
        combined[species] = combined.get(species, 0) + int(raw_count)
    return tuple(sorted(combined.items()))


def _fraction_text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


@dataclass(frozen=True)
class CapabilityAuthority:
    scope: MemoryScope
    capability_catalog_sha256: str
    evidence_epoch_sha256: str
    primitive_cost_unit: str

    def __post_init__(self) -> None:
        if not isinstance(self.scope, MemoryScope):
            raise TypeError("scope must be a MemoryScope")
        for name in (
            "capability_catalog_sha256",
            "evidence_epoch_sha256",
            "primitive_cost_unit",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "capability_authority",
            "scope": self.scope.to_receipt(),
            "scope_sha256": self.scope.sha256,
            "capability_catalog_sha256": self.capability_catalog_sha256,
            "evidence_epoch_sha256": self.evidence_epoch_sha256,
            "primitive_cost_unit": self.primitive_cost_unit,
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


@dataclass(frozen=True)
class CapabilitySpecies:
    authority: CapabilityAuthority
    species_id: str
    role: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "species_id",
            _nonempty(self.species_id, "species_id"),
        )
        if self.role not in _ROLES:
            raise ValueError(f"unknown capability species role {self.role!r}")
        evidence = _canonical(self.evidence_refs)
        if not evidence:
            raise ValueError("capability species requires evidence")
        object.__setattr__(self, "evidence_refs", evidence)

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "capability_species",
            "authority_sha256": self.authority.sha256,
            "species_id": self.species_id,
            "role": self.role,
            "evidence_refs": list(self.evidence_refs),
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


@dataclass(frozen=True)
class CatalyticCapabilityReaction:
    authority: CapabilityAuthority
    reaction_id: str
    reactants: tuple[tuple[str, int], ...]
    products: tuple[tuple[str, int], ...]
    catalyst_species_ids: tuple[str, ...]
    primitive_cost: Fraction
    bootstrap: bool
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "reaction_id",
            _nonempty(self.reaction_id, "reaction_id"),
        )
        reactants = _stoichiometry(self.reactants, "reactants")
        products = _stoichiometry(self.products, "products")
        if not reactants or not products:
            raise ValueError("capability reaction needs reactants and products")
        object.__setattr__(self, "reactants", reactants)
        object.__setattr__(self, "products", products)
        catalysts = _canonical(self.catalyst_species_ids)
        if not catalysts:
            raise ValueError("capability reaction requires a catalyst")
        object.__setattr__(self, "catalyst_species_ids", catalysts)
        object.__setattr__(
            self,
            "primitive_cost",
            _fraction(self.primitive_cost, "primitive_cost"),
        )
        evidence = _canonical(self.evidence_refs)
        if not evidence:
            raise ValueError("capability reaction requires evidence")
        object.__setattr__(self, "evidence_refs", evidence)

    @property
    def reactant_species_ids(self) -> frozenset[str]:
        return frozenset(species for species, _count in self.reactants)

    @property
    def product_species_ids(self) -> frozenset[str]:
        return frozenset(species for species, _count in self.products)

    def coefficient(self, species_id: str) -> int:
        products = dict(self.products).get(species_id, 0)
        reactants = dict(self.reactants).get(species_id, 0)
        return products - reactants

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "catalytic_capability_reaction",
            "authority_sha256": self.authority.sha256,
            "reaction_id": self.reaction_id,
            "reactants": [
                {"species_id": species, "count": count}
                for species, count in self.reactants
            ],
            "products": [
                {"species_id": species, "count": count}
                for species, count in self.products
            ],
            "catalyst_species_ids": list(self.catalyst_species_ids),
            "primitive_cost": _fraction_text(self.primitive_cost),
            "bootstrap": self.bootstrap,
            "evidence_refs": list(self.evidence_refs),
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


@dataclass(frozen=True)
class CapabilityGrowthFlux:
    reaction_fluxes: tuple[tuple[str, int], ...]
    total_primitive_cost: Fraction
    net_production: tuple[tuple[str, int], ...]
    internal_net_production: tuple[tuple[str, int], ...]

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "capability_growth_flux",
            "reaction_fluxes": [
                {"reaction_id": reaction_id, "flux": flux}
                for reaction_id, flux in self.reaction_fluxes
            ],
            "total_primitive_cost": _fraction_text(
                self.total_primitive_cost
            ),
            "net_production": [
                {"species_id": species, "net": net}
                for species, net in self.net_production
            ],
            "internal_net_production": [
                {"species_id": species, "net": net}
                for species, net in self.internal_net_production
            ],
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


@dataclass(frozen=True)
class CapabilityAutocatalysisReceipt:
    authority: CapabilityAuthority
    species: tuple[CapabilitySpecies, ...]
    reactions: tuple[CatalyticCapabilityReaction, ...]
    primitive_budget: Fraction
    food_closure_species_ids: tuple[str, ...]
    maximal_raf_reaction_ids: tuple[str, ...]
    growth_flux: CapabilityGrowthFlux | None
    status: str
    reason: str

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "capability_autocatalysis_receipt",
            "authority": self.authority.to_receipt(),
            "species": [row.to_receipt() for row in self.species],
            "reactions": [row.to_receipt() for row in self.reactions],
            "primitive_budget": _fraction_text(self.primitive_budget),
            "food_closure_species_ids": list(
                self.food_closure_species_ids
            ),
            "maximal_raf_reaction_ids": list(
                self.maximal_raf_reaction_ids
            ),
            "growth_flux": (
                self.growth_flux.to_receipt()
                if self.growth_flux is not None
                else None
            ),
            "status": self.status,
            "reason": self.reason,
            "takeoff_supported": False,
            "live_reaction_evidence_required": True,
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def _food_closure(
    food_species_ids: set[str],
    reactions: Sequence[CatalyticCapabilityReaction],
) -> set[str]:
    closure = set(food_species_ids)
    changed = True
    while changed:
        changed = False
        for reaction in reactions:
            if reaction.reactant_species_ids.issubset(closure):
                before = len(closure)
                closure.update(reaction.product_species_ids)
                changed = changed or len(closure) > before
    return closure


def _maximal_raf(
    food_species_ids: set[str],
    reactions: Sequence[CatalyticCapabilityReaction],
) -> tuple[tuple[CatalyticCapabilityReaction, ...], set[str]]:
    candidate = tuple(reactions)
    while candidate:
        closure = _food_closure(food_species_ids, candidate)
        retained = tuple(
            reaction
            for reaction in candidate
            if reaction.reactant_species_ids.issubset(closure)
            and set(reaction.catalyst_species_ids).intersection(closure)
        )
        if retained == candidate:
            return retained, closure
        candidate = retained
    return (), set(food_species_ids)


def _active_food_generated(
    food_species_ids: set[str],
    reactions: Sequence[CatalyticCapabilityReaction],
    fluxes: Sequence[int],
) -> tuple[bool, set[str]]:
    active = tuple(
        reaction for reaction, flux in zip(reactions, fluxes) if flux > 0
    )
    closure = _food_closure(food_species_ids, active)
    return (
        all(
            reaction.reactant_species_ids.issubset(closure)
            and set(reaction.catalyst_species_ids).intersection(closure)
            for reaction in active
        ),
        closure,
    )


def _growth_flux(
    species: Sequence[CapabilitySpecies],
    reactions: Sequence[CatalyticCapabilityReaction],
    *,
    food_species_ids: set[str],
    primitive_budget: Fraction,
    max_flux_per_reaction: int,
) -> CapabilityGrowthFlux | None:
    capability_ids = tuple(
        row.species_id for row in species if row.role == "capability"
    )
    error_ids = tuple(
        row.species_id for row in species if row.role == "error"
    )
    candidates = []
    for fluxes in itertools.product(
        range(max_flux_per_reaction + 1),
        repeat=len(reactions),
    ):
        if not any(fluxes):
            continue
        cost = sum(
            (
                reaction.primitive_cost * flux
                for reaction, flux in zip(reactions, fluxes)
            ),
            Fraction(0),
        )
        if cost > primitive_budget:
            continue
        generated, _closure = _active_food_generated(
            food_species_ids,
            reactions,
            fluxes,
        )
        if not generated:
            continue
        net = {
            row.species_id: sum(
                reaction.coefficient(row.species_id) * flux
                for reaction, flux in zip(reactions, fluxes)
            )
            for row in species
        }
        internal_net = {
            row.species_id: sum(
                reaction.coefficient(row.species_id) * flux
                for reaction, flux in zip(reactions, fluxes)
                if not reaction.bootstrap
            )
            for row in species
        }
        if not capability_ids or not all(
            internal_net[species_id] > 0 for species_id in capability_ids
        ):
            continue
        if any(net[species_id] > 0 for species_id in error_ids):
            continue
        active_products = {
            product
            for reaction, flux in zip(reactions, fluxes)
            if flux > 0
            for product in reaction.product_species_ids
        }
        if any(
            flux > 0
            and not (
                set(reaction.catalyst_species_ids).intersection(
                    food_species_ids | active_products
                )
            )
            for reaction, flux in zip(reactions, fluxes)
        ):
            continue
        candidates.append((cost, sum(fluxes), fluxes, net, internal_net))
    if not candidates:
        return None
    cost, _total_flux, fluxes, net, internal_net = min(candidates)
    return CapabilityGrowthFlux(
        reaction_fluxes=tuple(
            (reaction.reaction_id, flux)
            for reaction, flux in zip(reactions, fluxes)
        ),
        total_primitive_cost=cost,
        net_production=tuple(sorted(net.items())),
        internal_net_production=tuple(sorted(internal_net.items())),
    )


def compile_capability_autocatalysis(
    species: Sequence[CapabilitySpecies],
    reactions: Sequence[CatalyticCapabilityReaction],
    *,
    primitive_budget: Fraction | int | str,
    max_flux_per_reaction: int = 3,
) -> CapabilityAutocatalysisReceipt:
    """Compile RAF closure and one exact budget-feasible productive flux."""

    species_rows = tuple(species)
    reaction_rows = tuple(reactions)
    if not species_rows or not reaction_rows:
        raise ValueError("capability autocatalysis needs species and reactions")
    authority = species_rows[0].authority
    if any(row.authority != authority for row in species_rows):
        raise ValueError("capability species crossed authority")
    if any(row.authority != authority for row in reaction_rows):
        raise ValueError("capability reaction crossed authority")
    if len({row.species_id for row in species_rows}) != len(species_rows):
        raise ValueError("capability species repeat an identity")
    if len({row.reaction_id for row in reaction_rows}) != len(reaction_rows):
        raise ValueError("capability reactions repeat an identity")
    known = {row.species_id for row in species_rows}
    for reaction in reaction_rows:
        referenced = (
            set(reaction.reactant_species_ids)
            | set(reaction.product_species_ids)
            | set(reaction.catalyst_species_ids)
        )
        if not referenced.issubset(known):
            raise ValueError("capability reaction references unknown species")
    budget = _fraction(primitive_budget, "primitive_budget")
    if (
        isinstance(max_flux_per_reaction, bool)
        or not isinstance(max_flux_per_reaction, int)
        or max_flux_per_reaction <= 0
    ):
        raise ValueError("max_flux_per_reaction must be positive")
    food_ids = {
        row.species_id for row in species_rows if row.role == "food"
    }
    if not food_ids:
        raise ValueError("capability autocatalysis needs a food set")
    raf, closure = _maximal_raf(food_ids, reaction_rows)
    flux = _growth_flux(
        species_rows,
        raf,
        food_species_ids=food_ids,
        primitive_budget=budget,
        max_flux_per_reaction=max_flux_per_reaction,
    ) if raf else None
    if not raf:
        status = "no_reflexively_autocatalytic_food_generated_set"
        reason = "no_reaction_subset_passed_food_generation_and_catalysis"
    elif flux is None:
        status = "nonproductive_or_resource_blocked"
        reason = "no_exact_internal_growth_flux_within_budget_and_error_bound"
    else:
        status = "productive_autocatalytic_core"
        reason = "raf_and_exact_internal_growth_flux_passed"
    return CapabilityAutocatalysisReceipt(
        authority=authority,
        species=tuple(sorted(species_rows, key=lambda row: row.species_id)),
        reactions=tuple(sorted(reaction_rows, key=lambda row: row.reaction_id)),
        primitive_budget=budget,
        food_closure_species_ids=tuple(sorted(closure)),
        maximal_raf_reaction_ids=tuple(sorted(
            row.reaction_id for row in raf
        )),
        growth_flux=flux,
        status=status,
        reason=reason,
    )


__all__ = [
    "CapabilityAuthority",
    "CapabilityAutocatalysisReceipt",
    "CapabilityGrowthFlux",
    "CapabilitySpecies",
    "CatalyticCapabilityReaction",
    "compile_capability_autocatalysis",
]
