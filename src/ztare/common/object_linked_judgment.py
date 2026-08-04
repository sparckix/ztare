"""Typed controller plans over externally compiled object identities.

The object catalog and task-role selectors belong to substrate adapters.  This
kernel receives only opaque object references.  It binds one controller's
pre/post plans to the same scope, observation, catalog, proposal ancestry, and
intervention assignment, then classifies contract-relative path transport.

Free text is retained by the caller as evidence.  It carries no authority for
the transport relation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256
from ztare.common.wake_sleep_credit_router import MemoryScope


SCHEMA = "ztare-object-linked-judgment-v1"
_ASSIGNMENTS = frozenset({"offer", "withhold"})
_RELATIONS = frozenset({
    "offered_supported_transport",
    "offered_contradiction",
    "offered_other_transport",
    "offered_no_uptake",
    "withheld_spontaneous_supported",
    "withheld_spontaneous_contradiction",
    "withheld_spontaneous_other",
    "withheld_stable",
})


def _nonempty(value: str, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} must be nonempty")
    return text


def _canonical(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({
        str(value).strip() for value in values if str(value).strip()
    }))


def _ordered(values: Iterable[str], name: str) -> tuple[str, ...]:
    rows = tuple(_nonempty(str(value), name) for value in values)
    if len(rows) != len(set(rows)):
        raise ValueError(f"{name} cannot repeat object refs")
    return rows


def _contains_ordered_subsequence(
    observed: tuple[str, ...],
    required: tuple[str, ...],
) -> bool:
    if not required:
        return True
    index = 0
    for value in observed:
        if value == required[index]:
            index += 1
            if index == len(required):
                return True
    return False


@dataclass(frozen=True)
class ObjectReferenceAuthority:
    """Exact observation catalog allowed to interpret proposal refs."""

    observation_sha256: str
    catalog_sha256: str
    object_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "observation_sha256",
            _nonempty(self.observation_sha256, "observation_sha256"),
        )
        object.__setattr__(
            self,
            "catalog_sha256",
            _nonempty(self.catalog_sha256, "catalog_sha256"),
        )
        refs = _canonical(self.object_refs)
        if not refs:
            raise ValueError("object authority must contain object refs")
        object.__setattr__(self, "object_refs", refs)

    @property
    def sha256(self) -> str:
        return stable_sha256({
            "schema": SCHEMA,
            "kind": "object_reference_authority",
            "observation_sha256": self.observation_sha256,
            "catalog_sha256": self.catalog_sha256,
            "object_refs": list(self.object_refs),
        })


@dataclass(frozen=True)
class ObjectLinkedControllerProposal:
    """One committed action proposal expressed as a path over object refs."""

    scope: MemoryScope
    controller_instance_sha256: str
    observation_sha256: str
    catalog_sha256: str
    proposal_ref: str
    action_ref: str
    predicted_consequence_ref: str
    controlled_object_ref: str
    ordered_waypoint_refs: tuple[str, ...] = field(default_factory=tuple)
    parent_proposal_sha256: str = ""
    consumed_intervention_revision_sha256: str = ""

    def __post_init__(self) -> None:
        for name in (
            "controller_instance_sha256",
            "observation_sha256",
            "catalog_sha256",
            "proposal_ref",
            "action_ref",
            "predicted_consequence_ref",
            "controlled_object_ref",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if self.observation_sha256 != self.scope.context_sha256:
            raise ValueError(
                "proposal observation must equal the consumption context"
            )
        object.__setattr__(
            self,
            "ordered_waypoint_refs",
            _ordered(
                self.ordered_waypoint_refs,
                "ordered_waypoint_refs",
            ),
        )

    @property
    def path(self) -> tuple[str, ...]:
        return (
            self.controlled_object_ref,
            *self.ordered_waypoint_refs,
        )

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "object_linked_controller_proposal",
            "scope": self.scope.to_receipt(),
            "scope_sha256": self.scope.sha256,
            "controller_instance_sha256": (
                self.controller_instance_sha256
            ),
            "observation_sha256": self.observation_sha256,
            "catalog_sha256": self.catalog_sha256,
            "proposal_ref": self.proposal_ref,
            "action_ref": self.action_ref,
            "predicted_consequence_ref": (
                self.predicted_consequence_ref
            ),
            "controlled_object_ref": self.controlled_object_ref,
            "ordered_waypoint_refs": list(self.ordered_waypoint_refs),
            "parent_proposal_sha256": self.parent_proposal_sha256,
            "consumed_intervention_revision_sha256": (
                self.consumed_intervention_revision_sha256
            ),
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


@dataclass(frozen=True)
class ObjectRolePathContract:
    """Evidence-backed path constraints selected by one intervention."""

    scope: MemoryScope
    catalog_sha256: str
    intervention_revision_sha256: str
    required_controlled_object_ref: str
    required_waypoint_refs: tuple[str, ...]
    forbidden_controlled_object_refs: tuple[str, ...] = field(
        default_factory=tuple
    )
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for name in (
            "catalog_sha256",
            "intervention_revision_sha256",
            "required_controlled_object_ref",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        object.__setattr__(
            self,
            "required_waypoint_refs",
            _ordered(
                self.required_waypoint_refs,
                "required_waypoint_refs",
            ),
        )
        object.__setattr__(
            self,
            "forbidden_controlled_object_refs",
            _canonical(self.forbidden_controlled_object_refs),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _canonical(self.evidence_refs),
        )
        if not self.required_waypoint_refs:
            raise ValueError("required_waypoint_refs must be nonempty")
        if not self.evidence_refs:
            raise ValueError("evidence_refs must be nonempty")
        if self.required_controlled_object_ref in (
            self.forbidden_controlled_object_refs
        ):
            raise ValueError(
                "required controlled ref cannot also be forbidden"
            )

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "object_role_path_contract",
            "scope": self.scope.to_receipt(),
            "scope_sha256": self.scope.sha256,
            "catalog_sha256": self.catalog_sha256,
            "intervention_revision_sha256": (
                self.intervention_revision_sha256
            ),
            "required_controlled_object_ref": (
                self.required_controlled_object_ref
            ),
            "required_waypoint_refs": list(
                self.required_waypoint_refs
            ),
            "forbidden_controlled_object_refs": list(
                self.forbidden_controlled_object_refs
            ),
            "evidence_refs": list(self.evidence_refs),
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def _validate_refs(
    proposal: ObjectLinkedControllerProposal,
    authority: ObjectReferenceAuthority,
) -> None:
    if proposal.observation_sha256 != authority.observation_sha256:
        raise ValueError("proposal crossed observation authority")
    if proposal.catalog_sha256 != authority.catalog_sha256:
        raise ValueError("proposal crossed object catalog authority")
    allowed = set(authority.object_refs)
    unknown = set(proposal.path) - allowed
    if unknown:
        raise ValueError(
            f"proposal contains unknown object refs: {sorted(unknown)}"
        )


def _validate_contract(
    contract: ObjectRolePathContract,
    authority: ObjectReferenceAuthority,
) -> None:
    if contract.scope.context_sha256 != authority.observation_sha256:
        raise ValueError("contract crossed observation authority")
    if contract.catalog_sha256 != authority.catalog_sha256:
        raise ValueError("contract crossed object catalog authority")
    allowed = set(authority.object_refs)
    refs = {
        contract.required_controlled_object_ref,
        *contract.required_waypoint_refs,
        *contract.forbidden_controlled_object_refs,
    }
    unknown = refs - allowed
    if unknown:
        raise ValueError(
            f"contract contains unknown object refs: {sorted(unknown)}"
        )


def proposal_satisfies_object_contract(
    proposal: ObjectLinkedControllerProposal,
    contract: ObjectRolePathContract,
) -> bool:
    if proposal.scope != contract.scope:
        raise ValueError("proposal and contract scopes differ")
    return bool(
        proposal.controlled_object_ref
        == contract.required_controlled_object_ref
        and proposal.controlled_object_ref
        not in set(contract.forbidden_controlled_object_refs)
        and _contains_ordered_subsequence(
            proposal.ordered_waypoint_refs,
            contract.required_waypoint_refs,
        )
    )


def object_plan_basin_sha256(
    proposal: ObjectLinkedControllerProposal,
    contract: ObjectRolePathContract,
) -> str:
    signature = object_plan_basin_signature(proposal, contract)
    return stable_sha256({
        "scope_sha256": proposal.scope.sha256,
        "contract_sha256": contract.sha256,
        "catalog_sha256": proposal.catalog_sha256,
        **signature,
    })


def object_plan_basin_signature(
    proposal: ObjectLinkedControllerProposal,
    contract: ObjectRolePathContract,
) -> dict[str, Any]:
    """Return the identity-free contract-relative shape of an object plan.

    The full basin hash remains scoped by the exact context, catalog, and
    contract.  This structural signature is narrower: it is the coordinate
    that a separately certified object/contract transport may compare across
    two fibers.
    """

    if proposal.scope != contract.scope:
        raise ValueError("proposal and contract scopes differ")
    if (
        proposal.controlled_object_ref
        == contract.required_controlled_object_ref
    ):
        control_relation = "required"
    elif proposal.controlled_object_ref in (
        contract.forbidden_controlled_object_refs
    ):
        control_relation = "forbidden"
    else:
        control_relation = "other"
    matched_prefix = 0
    for observed, required in zip(
        proposal.ordered_waypoint_refs,
        contract.required_waypoint_refs,
    ):
        if observed != required:
            break
        matched_prefix += 1
    return {
        "control_relation": control_relation,
        "required_waypoint_prefix_length": matched_prefix,
        "required_waypoint_order_satisfied": (
            _contains_ordered_subsequence(
                proposal.ordered_waypoint_refs,
                contract.required_waypoint_refs,
            )
        ),
    }


@dataclass(frozen=True)
class ObjectLinkedProposalTransition:
    """One typed plan response under an offer/withhold assignment."""

    scope: MemoryScope
    trial_ref: str
    stratum_sha256: str
    controller_instance_sha256: str
    contract_sha256: str
    intervention_revision_sha256: str
    catalog_sha256: str
    assignment: str
    pre_proposal_sha256: str
    post_proposal_sha256: str
    pre_basin_sha256: str
    relation: str
    changed_action: bool
    changed_prediction: bool
    changed_path: bool
    supported_transport: bool

    def __post_init__(self) -> None:
        for name in (
            "trial_ref",
            "stratum_sha256",
            "controller_instance_sha256",
            "contract_sha256",
            "intervention_revision_sha256",
            "catalog_sha256",
            "pre_proposal_sha256",
            "post_proposal_sha256",
            "pre_basin_sha256",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if self.assignment not in _ASSIGNMENTS:
            raise ValueError(f"unknown assignment {self.assignment!r}")
        if self.relation not in _RELATIONS:
            raise ValueError(f"unknown relation {self.relation!r}")

    @property
    def changed_features(self) -> bool:
        """Compatibility with the generic instrumented estimator receipt."""

        return self.changed_path

    @property
    def action_relevant_displacement(self) -> bool:
        return bool(
            self.changed_action
            or self.changed_prediction
            or self.changed_path
        )

    @property
    def response_signature_sha256(self) -> str:
        return stable_sha256({
            "scope_sha256": self.scope.sha256,
            "contract_sha256": self.contract_sha256,
            "intervention_revision_sha256": (
                self.intervention_revision_sha256
            ),
            "catalog_sha256": self.catalog_sha256,
            "pre_basin_sha256": self.pre_basin_sha256,
            "assignment": self.assignment,
            "relation": self.relation,
            "changed_action": self.changed_action,
            "changed_prediction": self.changed_prediction,
            "changed_path": self.changed_path,
            "supported_transport": self.supported_transport,
        })

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "object_linked_proposal_transition",
            "scope": self.scope.to_receipt(),
            "scope_sha256": self.scope.sha256,
            "trial_ref": self.trial_ref,
            "stratum_sha256": self.stratum_sha256,
            "controller_instance_sha256": (
                self.controller_instance_sha256
            ),
            "contract_sha256": self.contract_sha256,
            "intervention_revision_sha256": (
                self.intervention_revision_sha256
            ),
            "catalog_sha256": self.catalog_sha256,
            "assignment": self.assignment,
            "pre_proposal_sha256": self.pre_proposal_sha256,
            "post_proposal_sha256": self.post_proposal_sha256,
            "pre_basin_sha256": self.pre_basin_sha256,
            "response_signature_sha256": (
                self.response_signature_sha256
            ),
            "relation": self.relation,
            "changed_action": self.changed_action,
            "changed_prediction": self.changed_prediction,
            "changed_path": self.changed_path,
            "changed_features": self.changed_features,
            "action_relevant_displacement": (
                self.action_relevant_displacement
            ),
            "supported_transport": self.supported_transport,
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def compile_object_linked_transition(
    *,
    trial_ref: str,
    stratum_sha256: str,
    assignment: str,
    pre_proposal: ObjectLinkedControllerProposal,
    post_proposal: ObjectLinkedControllerProposal,
    contract: ObjectRolePathContract,
    authority: ObjectReferenceAuthority,
) -> ObjectLinkedProposalTransition:
    """Compile pre/post paths under exact catalog and intervention authority."""

    if assignment not in _ASSIGNMENTS:
        raise ValueError(f"unknown assignment {assignment!r}")
    _validate_contract(contract, authority)
    _validate_refs(pre_proposal, authority)
    _validate_refs(post_proposal, authority)
    if pre_proposal.scope != contract.scope:
        raise ValueError("pre proposal and contract scopes differ")
    if post_proposal.scope != pre_proposal.scope:
        raise ValueError("post proposal scope drifted")
    if post_proposal.controller_instance_sha256 != (
        pre_proposal.controller_instance_sha256
    ):
        raise ValueError("post proposal controller instance drifted")
    if post_proposal.observation_sha256 != pre_proposal.observation_sha256:
        raise ValueError("post proposal observation drifted")
    if post_proposal.catalog_sha256 != pre_proposal.catalog_sha256:
        raise ValueError("post proposal catalog drifted")
    if post_proposal.parent_proposal_sha256 != pre_proposal.sha256:
        raise ValueError("post proposal has the wrong parent")
    consumed = post_proposal.consumed_intervention_revision_sha256
    if assignment == "offer":
        if consumed != contract.intervention_revision_sha256:
            raise ValueError(
                "offered post proposal did not cite the intervention"
            )
    elif consumed:
        raise ValueError(
            "withheld post proposal cannot cite an intervention"
        )

    before_satisfies = proposal_satisfies_object_contract(
        pre_proposal,
        contract,
    )
    after_satisfies = proposal_satisfies_object_contract(
        post_proposal,
        contract,
    )
    contradicted = (
        post_proposal.controlled_object_ref
        in set(contract.forbidden_controlled_object_refs)
    )
    changed_action = pre_proposal.action_ref != post_proposal.action_ref
    changed_prediction = (
        pre_proposal.predicted_consequence_ref
        != post_proposal.predicted_consequence_ref
    )
    changed_path = pre_proposal.path != post_proposal.path
    meaningful = changed_action or changed_prediction or changed_path
    supported = bool(
        changed_path and after_satisfies and not before_satisfies
    )
    if assignment == "offer":
        if supported:
            relation = "offered_supported_transport"
        elif contradicted:
            relation = "offered_contradiction"
        elif meaningful:
            relation = "offered_other_transport"
        else:
            relation = "offered_no_uptake"
    else:
        if supported:
            relation = "withheld_spontaneous_supported"
        elif contradicted:
            relation = "withheld_spontaneous_contradiction"
        elif meaningful:
            relation = "withheld_spontaneous_other"
        else:
            relation = "withheld_stable"
    return ObjectLinkedProposalTransition(
        scope=pre_proposal.scope,
        trial_ref=_nonempty(trial_ref, "trial_ref"),
        stratum_sha256=_nonempty(
            stratum_sha256,
            "stratum_sha256",
        ),
        controller_instance_sha256=(
            pre_proposal.controller_instance_sha256
        ),
        contract_sha256=contract.sha256,
        intervention_revision_sha256=(
            contract.intervention_revision_sha256
        ),
        catalog_sha256=authority.catalog_sha256,
        assignment=assignment,
        pre_proposal_sha256=pre_proposal.sha256,
        post_proposal_sha256=post_proposal.sha256,
        pre_basin_sha256=object_plan_basin_sha256(
            pre_proposal,
            contract,
        ),
        relation=relation,
        changed_action=changed_action,
        changed_prediction=changed_prediction,
        changed_path=changed_path,
        supported_transport=supported,
    )


def compile_object_reference_authority(
    *,
    observation_sha256: str,
    catalog_sha256: str,
    object_refs: Iterable[str],
) -> ObjectReferenceAuthority:
    return ObjectReferenceAuthority(
        observation_sha256=observation_sha256,
        catalog_sha256=catalog_sha256,
        object_refs=tuple(object_refs),
    )


__all__ = [
    "ObjectLinkedControllerProposal",
    "ObjectLinkedProposalTransition",
    "ObjectReferenceAuthority",
    "ObjectRolePathContract",
    "compile_object_linked_transition",
    "compile_object_reference_authority",
    "object_plan_basin_sha256",
    "object_plan_basin_signature",
    "proposal_satisfies_object_contract",
]
