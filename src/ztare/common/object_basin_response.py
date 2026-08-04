"""Prospective intervention admission from object-plan response families.

An externally settled intervention effect is useful only if it can condition a
later decision before the later outcome is known.  This kernel groups
randomized object-linked proposal transitions by their contract-relative
pre-intervention basin.  It then admits an intervention only for the exact
basins where:

* offer and withhold both have enough support;
* the offer changes the typed object path more often than withhold; and
* the externally settled, cost-adjusted intent-to-treat effect is positive.

The response family contains opaque object and intervention identities.  It
does not inspect memory text, condition names, or substrate-specific role
labels.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping, Sequence

from ztare.common.equivariance import stable_sha256
from ztare.common.instrumented_proposal_plasticity import (
    InstrumentedProposalOutcome,
    estimate_instrumented_plasticity,
)
from ztare.common.object_linked_judgment import (
    ObjectLinkedControllerProposal,
    ObjectLinkedProposalTransition,
    ObjectReferenceAuthority,
    ObjectRolePathContract,
    object_plan_basin_sha256,
    proposal_satisfies_object_contract,
)
from ztare.common.wake_sleep_credit_router import MemoryScope


SCHEMA = "ztare-object-basin-response-family-v1"
_STATUSES = frozenset({
    "identified_positive",
    "identified_nonpositive",
    "weak_instrument",
    "undersampled",
})
_ACTIONS = frozenset({"offer", "silence", "explore"})


def _nonempty(value: str, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} must be nonempty")
    return text


def _finite(value: float, name: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _nonnegative(value: float, name: str) -> float:
    number = _finite(value, name)
    if number < 0.0:
        raise ValueError(f"{name} must be nonnegative")
    return number


def _positive_int(value: int, name: str) -> int:
    if isinstance(value, bool) or int(value) != value or int(value) <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def _scope_from_receipt(receipt: Mapping[str, Any]) -> MemoryScope:
    return MemoryScope(
        task_sha256=str(receipt["task_sha256"]),
        controller_sha256=str(receipt["controller_sha256"]),
        context_sha256=str(receipt["context_sha256"]),
        choice_set_sha256=str(receipt["choice_set_sha256"]),
        action_vocabulary_sha256=str(
            receipt["action_vocabulary_sha256"]
        ),
    )


def object_proposal_from_receipt(
    receipt: Mapping[str, Any],
) -> ObjectLinkedControllerProposal:
    """Rehydrate and hash-check one object-linked proposal."""

    if receipt.get("schema") != "ztare-object-linked-judgment-v1":
        raise ValueError("unknown object proposal receipt schema")
    if receipt.get("kind") != "object_linked_controller_proposal":
        raise ValueError("receipt is not an object-linked proposal")
    proposal = ObjectLinkedControllerProposal(
        scope=_scope_from_receipt(dict(receipt["scope"])),
        controller_instance_sha256=str(
            receipt["controller_instance_sha256"]
        ),
        observation_sha256=str(receipt["observation_sha256"]),
        catalog_sha256=str(receipt["catalog_sha256"]),
        proposal_ref=str(receipt["proposal_ref"]),
        action_ref=str(receipt["action_ref"]),
        predicted_consequence_ref=str(
            receipt["predicted_consequence_ref"]
        ),
        controlled_object_ref=str(receipt["controlled_object_ref"]),
        ordered_waypoint_refs=tuple(
            receipt["ordered_waypoint_refs"]
        ),
        parent_proposal_sha256=str(
            receipt["parent_proposal_sha256"]
        ),
        consumed_intervention_revision_sha256=str(
            receipt["consumed_intervention_revision_sha256"]
        ),
    )
    if proposal.to_receipt() != dict(receipt):
        raise ValueError("object proposal receipt hash or fields drifted")
    return proposal


def object_contract_from_receipt(
    receipt: Mapping[str, Any],
) -> ObjectRolePathContract:
    """Rehydrate and hash-check one object-role path contract."""

    if receipt.get("schema") != "ztare-object-linked-judgment-v1":
        raise ValueError("unknown object contract receipt schema")
    if receipt.get("kind") != "object_role_path_contract":
        raise ValueError("receipt is not an object-role path contract")
    contract = ObjectRolePathContract(
        scope=_scope_from_receipt(dict(receipt["scope"])),
        catalog_sha256=str(receipt["catalog_sha256"]),
        intervention_revision_sha256=str(
            receipt["intervention_revision_sha256"]
        ),
        required_controlled_object_ref=str(
            receipt["required_controlled_object_ref"]
        ),
        required_waypoint_refs=tuple(
            receipt["required_waypoint_refs"]
        ),
        forbidden_controlled_object_refs=tuple(
            receipt["forbidden_controlled_object_refs"]
        ),
        evidence_refs=tuple(receipt["evidence_refs"]),
    )
    if contract.to_receipt() != dict(receipt):
        raise ValueError("object contract receipt hash or fields drifted")
    return contract


def object_transition_from_receipt(
    receipt: Mapping[str, Any],
) -> ObjectLinkedProposalTransition:
    """Rehydrate and hash-check one object-linked transition receipt."""

    if receipt.get("schema") != "ztare-object-linked-judgment-v1":
        raise ValueError("unknown object transition receipt schema")
    if receipt.get("kind") != "object_linked_proposal_transition":
        raise ValueError("receipt is not an object-linked transition")
    transition = ObjectLinkedProposalTransition(
        scope=_scope_from_receipt(dict(receipt["scope"])),
        trial_ref=str(receipt["trial_ref"]),
        stratum_sha256=str(receipt["stratum_sha256"]),
        controller_instance_sha256=str(
            receipt["controller_instance_sha256"]
        ),
        contract_sha256=str(receipt["contract_sha256"]),
        intervention_revision_sha256=str(
            receipt["intervention_revision_sha256"]
        ),
        catalog_sha256=str(receipt["catalog_sha256"]),
        assignment=str(receipt["assignment"]),
        pre_proposal_sha256=str(receipt["pre_proposal_sha256"]),
        post_proposal_sha256=str(receipt["post_proposal_sha256"]),
        pre_basin_sha256=str(receipt["pre_basin_sha256"]),
        relation=str(receipt["relation"]),
        changed_action=bool(receipt["changed_action"]),
        changed_prediction=bool(receipt["changed_prediction"]),
        changed_path=bool(receipt["changed_path"]),
        supported_transport=bool(receipt["supported_transport"]),
    )
    if transition.to_receipt() != dict(receipt):
        raise ValueError("object transition receipt hash or fields drifted")
    return transition


def object_outcome_from_receipt(
    receipt: Mapping[str, Any],
    *,
    transition: ObjectLinkedProposalTransition,
) -> InstrumentedProposalOutcome:
    """Rehydrate and hash-check an external settlement for a transition."""

    if receipt.get("schema") != (
        "ztare-instrumented-proposal-plasticity-v1"
    ):
        raise ValueError("unknown object outcome receipt schema")
    if receipt.get("kind") != "instrumented_proposal_outcome":
        raise ValueError("receipt is not an instrumented outcome")
    if str(receipt["transition_sha256"]) != transition.sha256:
        raise ValueError("outcome cites a different transition")
    outcome = InstrumentedProposalOutcome(
        transition=transition,
        external_outcome_ref=str(receipt["external_outcome_ref"]),
        external_value=float(receipt["external_value"]),
        offer_cost=float(receipt["offer_cost"]),
        primitive_action_cost=float(receipt["primitive_action_cost"]),
    )
    if outcome.to_receipt() != dict(receipt):
        raise ValueError("object outcome receipt hash or fields drifted")
    return outcome


def object_response_family_from_receipt(
    receipt: Mapping[str, Any],
) -> ObjectResponseFamily:
    """Rehydrate a family after validating every response identity."""

    if receipt.get("schema") != SCHEMA:
        raise ValueError("unknown response-family receipt schema")
    if receipt.get("kind") != "object_response_family":
        raise ValueError("receipt is not an object response family")
    responses = []
    for row in receipt["responses"]:
        response = ObjectBasinResponse(
            scope_sha256=str(row["scope_sha256"]),
            contract_sha256=str(row["contract_sha256"]),
            intervention_revision_sha256=str(
                row["intervention_revision_sha256"]
            ),
            catalog_sha256=str(row["catalog_sha256"]),
            pre_basin_sha256=str(row["pre_basin_sha256"]),
            status=str(row["status"]),
            offer_count=int(row["offer_count"]),
            withhold_count=int(row["withhold_count"]),
            offer_supported_transport_rate=float(
                row["offer_supported_transport_rate"]
            ),
            withhold_supported_transport_rate=float(
                row["withhold_supported_transport_rate"]
            ),
            first_stage_transport_delta=float(
                row["first_stage_transport_delta"]
            ),
            intent_to_treat_net_delta=float(
                row["intent_to_treat_net_delta"]
            ),
            complier_net_effect=(
                None
                if row["complier_net_effect"] is None
                else float(row["complier_net_effect"])
            ),
            primitive_action_cost=float(row["primitive_action_cost"]),
            outcome_sha256s=tuple(row["outcome_sha256s"]),
        )
        if response.to_receipt() != dict(row):
            raise ValueError("response-family row hash or fields drifted")
        responses.append(response)
    family = ObjectResponseFamily(
        scope_sha256=str(receipt["scope_sha256"]),
        contract_sha256=str(receipt["contract_sha256"]),
        intervention_revision_sha256=str(
            receipt["intervention_revision_sha256"]
        ),
        catalog_sha256=str(receipt["catalog_sha256"]),
        source_result_ref=str(receipt["source_result_ref"]),
        source_result_sha256=str(receipt["source_result_sha256"]),
        minimum_offer_count=int(receipt["minimum_offer_count"]),
        minimum_withhold_count=int(receipt["minimum_withhold_count"]),
        minimum_first_stage_transport_delta=float(
            receipt["minimum_first_stage_transport_delta"]
        ),
        minimum_intent_to_treat_net_delta=float(
            receipt["minimum_intent_to_treat_net_delta"]
        ),
        responses=tuple(responses),
    )
    if family.to_receipt() != dict(receipt):
        raise ValueError("response-family receipt hash or fields drifted")
    return family


@dataclass(frozen=True)
class ObjectBasinResponse:
    """Cost-adjusted randomized response evidence for one proposal basin."""

    scope_sha256: str
    contract_sha256: str
    intervention_revision_sha256: str
    catalog_sha256: str
    pre_basin_sha256: str
    status: str
    offer_count: int
    withhold_count: int
    offer_supported_transport_rate: float
    withhold_supported_transport_rate: float
    first_stage_transport_delta: float
    intent_to_treat_net_delta: float
    complier_net_effect: float | None
    primitive_action_cost: float
    outcome_sha256s: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "scope_sha256",
            "contract_sha256",
            "intervention_revision_sha256",
            "catalog_sha256",
            "pre_basin_sha256",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if self.status not in _STATUSES:
            raise ValueError(f"unknown response status {self.status!r}")
        if self.offer_count < 0 or self.withhold_count < 0:
            raise ValueError("response counts must be nonnegative")
        for name in (
            "offer_supported_transport_rate",
            "withhold_supported_transport_rate",
            "first_stage_transport_delta",
            "intent_to_treat_net_delta",
        ):
            object.__setattr__(
                self,
                name,
                _finite(getattr(self, name), name),
            )
        if self.complier_net_effect is not None:
            object.__setattr__(
                self,
                "complier_net_effect",
                _finite(
                    self.complier_net_effect,
                    "complier_net_effect",
                ),
            )
        object.__setattr__(
            self,
            "primitive_action_cost",
            _nonnegative(
                self.primitive_action_cost,
                "primitive_action_cost",
            ),
        )
        outcomes = tuple(sorted(set(self.outcome_sha256s)))
        if len(outcomes) != self.offer_count + self.withhold_count:
            raise ValueError(
                "response outcome identities do not match its sample count"
            )
        object.__setattr__(self, "outcome_sha256s", outcomes)

    @property
    def admissible(self) -> bool:
        return self.status == "identified_positive"

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "object_basin_response",
            "scope_sha256": self.scope_sha256,
            "contract_sha256": self.contract_sha256,
            "intervention_revision_sha256": (
                self.intervention_revision_sha256
            ),
            "catalog_sha256": self.catalog_sha256,
            "pre_basin_sha256": self.pre_basin_sha256,
            "status": self.status,
            "admissible": self.admissible,
            "offer_count": self.offer_count,
            "withhold_count": self.withhold_count,
            "offer_supported_transport_rate": (
                self.offer_supported_transport_rate
            ),
            "withhold_supported_transport_rate": (
                self.withhold_supported_transport_rate
            ),
            "first_stage_transport_delta": (
                self.first_stage_transport_delta
            ),
            "intent_to_treat_net_delta": (
                self.intent_to_treat_net_delta
            ),
            "complier_net_effect": self.complier_net_effect,
            "primitive_action_cost": self.primitive_action_cost,
            "outcome_sha256s": list(self.outcome_sha256s),
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


@dataclass(frozen=True)
class ObjectResponseFamily:
    """Immutable map from typed pre-proposal basins to settled responses."""

    scope_sha256: str
    contract_sha256: str
    intervention_revision_sha256: str
    catalog_sha256: str
    source_result_ref: str
    source_result_sha256: str
    minimum_offer_count: int
    minimum_withhold_count: int
    minimum_first_stage_transport_delta: float
    minimum_intent_to_treat_net_delta: float
    responses: tuple[ObjectBasinResponse, ...]

    def __post_init__(self) -> None:
        for name in (
            "scope_sha256",
            "contract_sha256",
            "intervention_revision_sha256",
            "catalog_sha256",
            "source_result_ref",
            "source_result_sha256",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        object.__setattr__(
            self,
            "minimum_offer_count",
            _positive_int(
                self.minimum_offer_count,
                "minimum_offer_count",
            ),
        )
        object.__setattr__(
            self,
            "minimum_withhold_count",
            _positive_int(
                self.minimum_withhold_count,
                "minimum_withhold_count",
            ),
        )
        object.__setattr__(
            self,
            "minimum_first_stage_transport_delta",
            _nonnegative(
                self.minimum_first_stage_transport_delta,
                "minimum_first_stage_transport_delta",
            ),
        )
        object.__setattr__(
            self,
            "minimum_intent_to_treat_net_delta",
            _finite(
                self.minimum_intent_to_treat_net_delta,
                "minimum_intent_to_treat_net_delta",
            ),
        )
        ordered = tuple(
            sorted(self.responses, key=lambda row: row.pre_basin_sha256)
        )
        if not ordered:
            raise ValueError("response family must contain responses")
        if len({row.pre_basin_sha256 for row in ordered}) != len(ordered):
            raise ValueError("response family repeats a pre-basin")
        for row in ordered:
            if (
                row.scope_sha256 != self.scope_sha256
                or row.contract_sha256 != self.contract_sha256
                or row.intervention_revision_sha256
                != self.intervention_revision_sha256
                or row.catalog_sha256 != self.catalog_sha256
            ):
                raise ValueError(
                    "response crossed family identity authority"
                )
        object.__setattr__(self, "responses", ordered)

    def response_for_basin(
        self,
        pre_basin_sha256: str,
    ) -> ObjectBasinResponse | None:
        matches = tuple(
            row for row in self.responses
            if row.pre_basin_sha256 == pre_basin_sha256
        )
        if not matches:
            return None
        if len(matches) != 1:
            raise RuntimeError("response family basin identity is ambiguous")
        return matches[0]

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "object_response_family",
            "scope_sha256": self.scope_sha256,
            "contract_sha256": self.contract_sha256,
            "intervention_revision_sha256": (
                self.intervention_revision_sha256
            ),
            "catalog_sha256": self.catalog_sha256,
            "source_result_ref": self.source_result_ref,
            "source_result_sha256": self.source_result_sha256,
            "minimum_offer_count": self.minimum_offer_count,
            "minimum_withhold_count": self.minimum_withhold_count,
            "minimum_first_stage_transport_delta": (
                self.minimum_first_stage_transport_delta
            ),
            "minimum_intent_to_treat_net_delta": (
                self.minimum_intent_to_treat_net_delta
            ),
            "responses": [row.to_receipt() for row in self.responses],
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def compile_object_response_family(
    outcomes: Sequence[InstrumentedProposalOutcome],
    *,
    source_result_ref: str,
    source_result_sha256: str,
    minimum_offer_count: int = 2,
    minimum_withhold_count: int = 2,
    minimum_first_stage_transport_delta: float = 1.0,
    minimum_intent_to_treat_net_delta: float = 0.0,
) -> ObjectResponseFamily:
    """Compile basin-local randomized settlements into a response family."""

    rows = tuple(outcomes)
    if not rows:
        raise ValueError("response family requires outcomes")
    minimum_offers = _positive_int(
        minimum_offer_count,
        "minimum_offer_count",
    )
    minimum_withholds = _positive_int(
        minimum_withhold_count,
        "minimum_withhold_count",
    )
    minimum_first_stage = _nonnegative(
        minimum_first_stage_transport_delta,
        "minimum_first_stage_transport_delta",
    )
    minimum_itt = _finite(
        minimum_intent_to_treat_net_delta,
        "minimum_intent_to_treat_net_delta",
    )
    transitions = tuple(row.transition for row in rows)
    if not all(
        isinstance(row, ObjectLinkedProposalTransition)
        for row in transitions
    ):
        raise ValueError(
            "object response family requires object-linked transitions"
        )
    identities = {
        (
            row.scope.sha256,
            row.contract_sha256,
            row.intervention_revision_sha256,
            row.catalog_sha256,
        )
        for row in transitions
    }
    if len(identities) != 1:
        raise ValueError("outcomes cross response-family identity")
    primitive_costs = {row.primitive_action_cost for row in rows}
    if len(primitive_costs) != 1:
        raise ValueError("outcomes cross primitive action cost")
    grouped: dict[str, list[InstrumentedProposalOutcome]] = {}
    for outcome in rows:
        grouped.setdefault(
            outcome.transition.pre_basin_sha256,
            [],
        ).append(outcome)
    response_rows = []
    for pre_basin, group in sorted(grouped.items()):
        group_rows = tuple(group)
        offers = sum(
            row.transition.assignment == "offer"
            for row in group_rows
        )
        withholds = len(group_rows) - offers
        estimate = estimate_instrumented_plasticity(
            group_rows,
            minimum_first_stage=minimum_first_stage,
        )
        if offers < minimum_offers or withholds < minimum_withholds:
            status = "undersampled"
        elif estimate.status != "identified":
            status = "weak_instrument"
        elif estimate.intent_to_treat_net_delta > minimum_itt:
            status = "identified_positive"
        else:
            status = "identified_nonpositive"
        transition = group_rows[0].transition
        response_rows.append(ObjectBasinResponse(
            scope_sha256=transition.scope.sha256,
            contract_sha256=transition.contract_sha256,
            intervention_revision_sha256=(
                transition.intervention_revision_sha256
            ),
            catalog_sha256=transition.catalog_sha256,
            pre_basin_sha256=pre_basin,
            status=status,
            offer_count=estimate.offer_count,
            withhold_count=estimate.withhold_count,
            offer_supported_transport_rate=(
                estimate.offer_supported_transport_rate
            ),
            withhold_supported_transport_rate=(
                estimate.withhold_supported_transport_rate
            ),
            first_stage_transport_delta=(
                estimate.first_stage_transport_delta
            ),
            intent_to_treat_net_delta=(
                estimate.intent_to_treat_net_delta
            ),
            complier_net_effect=estimate.complier_net_effect,
            primitive_action_cost=next(iter(primitive_costs)),
            outcome_sha256s=estimate.outcome_sha256s,
        ))
    identity = next(iter(identities))
    return ObjectResponseFamily(
        scope_sha256=identity[0],
        contract_sha256=identity[1],
        intervention_revision_sha256=identity[2],
        catalog_sha256=identity[3],
        source_result_ref=source_result_ref,
        source_result_sha256=source_result_sha256,
        minimum_offer_count=minimum_offers,
        minimum_withhold_count=minimum_withholds,
        minimum_first_stage_transport_delta=minimum_first_stage,
        minimum_intent_to_treat_net_delta=minimum_itt,
        responses=tuple(response_rows),
    )


@dataclass(frozen=True)
class ObjectAdmissionDecision:
    """Prospective response-family action for one blind object proposal."""

    family_sha256: str
    proposal_sha256: str
    pre_basin_sha256: str
    action: str
    reason: str
    matched_response_sha256: str = ""

    def __post_init__(self) -> None:
        for name in (
            "family_sha256",
            "proposal_sha256",
            "pre_basin_sha256",
            "reason",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if self.action not in _ACTIONS:
            raise ValueError(f"unknown admission action {self.action!r}")
        if self.action == "offer" and not self.matched_response_sha256:
            raise ValueError("offer requires a matched response identity")

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "object_admission_decision",
            "family_sha256": self.family_sha256,
            "proposal_sha256": self.proposal_sha256,
            "pre_basin_sha256": self.pre_basin_sha256,
            "action": self.action,
            "reason": self.reason,
            "matched_response_sha256": (
                self.matched_response_sha256
            ),
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def compile_object_admission(
    proposal: ObjectLinkedControllerProposal,
    *,
    contract: ObjectRolePathContract,
    authority: ObjectReferenceAuthority,
    family: ObjectResponseFamily,
) -> ObjectAdmissionDecision:
    """Choose offer, silence, or exploration before intervention delivery."""

    if proposal.scope != contract.scope:
        raise ValueError("proposal and contract scopes differ")
    if proposal.scope.sha256 != family.scope_sha256:
        raise ValueError("proposal crossed response-family scope")
    if contract.sha256 != family.contract_sha256:
        raise ValueError("contract crossed response-family identity")
    if (
        contract.intervention_revision_sha256
        != family.intervention_revision_sha256
    ):
        raise ValueError("intervention crossed response-family identity")
    if authority.catalog_sha256 != family.catalog_sha256:
        raise ValueError("catalog crossed response-family identity")
    if proposal.observation_sha256 != authority.observation_sha256:
        raise ValueError("proposal crossed observation authority")
    if proposal.catalog_sha256 != authority.catalog_sha256:
        raise ValueError("proposal crossed catalog authority")
    unknown = set(proposal.path) - set(authority.object_refs)
    if unknown:
        raise ValueError(
            f"proposal contains unknown object refs: {sorted(unknown)}"
        )
    pre_basin = object_plan_basin_sha256(proposal, contract)
    response = family.response_for_basin(pre_basin)
    if proposal_satisfies_object_contract(proposal, contract):
        action = "silence"
        reason = "blind_proposal_already_satisfies_object_contract"
    elif response is None:
        action = "explore"
        reason = "proposal_basin_unseen"
    elif response.status in {"weak_instrument", "undersampled"}:
        action = "explore"
        reason = "proposal_basin_response_is_weak"
    elif response.admissible:
        action = "offer"
        reason = "exact_basin_has_identified_positive_net_response"
    else:
        action = "silence"
        reason = "exact_basin_has_nonpositive_net_response"
    return ObjectAdmissionDecision(
        family_sha256=family.sha256,
        proposal_sha256=proposal.sha256,
        pre_basin_sha256=pre_basin,
        action=action,
        reason=reason,
        matched_response_sha256=(
            response.sha256 if response is not None else ""
        ),
    )


__all__ = [
    "ObjectAdmissionDecision",
    "ObjectBasinResponse",
    "ObjectResponseFamily",
    "compile_object_admission",
    "compile_object_response_family",
    "object_contract_from_receipt",
    "object_outcome_from_receipt",
    "object_proposal_from_receipt",
    "object_response_family_from_receipt",
    "object_transition_from_receipt",
]
