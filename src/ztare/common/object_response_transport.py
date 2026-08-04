"""Fail-closed transport of object-basin intervention responses.

A response family is local to an exact observation catalog and contract.  This
module does not weaken that identity boundary.  It compiles a separate,
inspectable transport attempt:

1. required source occurrences must have a unique content-type match in the
   target catalog;
2. the object-role contract must map exactly;
3. a source pre/post response witness must map to the same contract-relative
   blind-plan signature and to a supported target path; and
4. a fresh target blind proposal must occupy that transported signature before
   an exploratory intervention may be delivered.

External target-fiber settlement is deliberately absent here.  A commuting
candidate authorizes only ``explore_transport`` or ``explore_lineage``.  It
becomes target-fiber credit through a later randomized settlement compiler.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from ztare.common.equivariance import stable_sha256
from ztare.common.decision_intervention_market import (
    DecisionInterventionProposal,
)
from ztare.common.object_basin_response import (
    ObjectBasinResponse,
    ObjectResponseFamily,
)
from ztare.common.object_linked_judgment import (
    ObjectLinkedControllerProposal,
    ObjectRolePathContract,
    object_plan_basin_sha256,
    object_plan_basin_signature,
    proposal_satisfies_object_contract,
)
from ztare.common.object_lineage_transport import (
    CausalObjectLineageTransport,
)
from ztare.common.wake_sleep_credit_router import MemoryScope
from ztare.worldmodel.observation_object_catalog import GridObjectCatalog


SCHEMA = "ztare-object-response-transport-v1"
_ATTEMPT_STATUSES = frozenset({"transportable", "refused"})
_CANDIDATE_STATUSES = frozenset({
    "candidate_commuting",
    "refused",
})
_ACTIONS = frozenset({
    "explore_lineage",
    "explore_transport",
    "refuse_transport",
})
_INTERVENTION_TRANSPORT_STATUSES = frozenset({
    "transportable",
    "refused",
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


@dataclass(frozen=True)
class InterventionRevisionTransport:
    """A lawful re-rendering of one intervention in a new context.

    Exact rendered revisions remain local.  This receipt relates them only
    when acquisition provenance, invariant payload, non-context scope
    authority, provider identity, calibration, and costs are preserved.
    """

    source_scope_sha256: str
    target_scope_sha256: str
    source_intervention_revision_sha256: str
    target_intervention_revision_sha256: str
    source_rendered_content_sha256: str
    target_rendered_content_sha256: str
    payload_invariant_sha256: str
    acquisition_provenance_sha256: str
    preserved_scope_coordinates: tuple[str, ...]
    changed_scope_coordinates: tuple[str, ...]
    invariant_checks: tuple[str, ...]
    status: str
    reason: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "source_scope_sha256",
            "target_scope_sha256",
            "source_intervention_revision_sha256",
            "target_intervention_revision_sha256",
            "source_rendered_content_sha256",
            "target_rendered_content_sha256",
            "payload_invariant_sha256",
            "acquisition_provenance_sha256",
            "reason",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if self.status not in _INTERVENTION_TRANSPORT_STATUSES:
            raise ValueError(
                f"unknown intervention transport status {self.status!r}"
            )
        preserved = _canonical(self.preserved_scope_coordinates)
        changed = _canonical(self.changed_scope_coordinates)
        if set(preserved) & set(changed):
            raise ValueError("scope coordinates cannot be both changed and preserved")
        object.__setattr__(
            self,
            "preserved_scope_coordinates",
            preserved,
        )
        object.__setattr__(
            self,
            "changed_scope_coordinates",
            changed,
        )
        checks = _canonical(self.invariant_checks)
        if not checks:
            raise ValueError("intervention transport requires invariant checks")
        object.__setattr__(self, "invariant_checks", checks)
        evidence = _canonical(self.evidence_refs)
        if not evidence:
            raise ValueError("intervention transport requires evidence refs")
        object.__setattr__(self, "evidence_refs", evidence)

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "intervention_revision_transport",
            "source_scope_sha256": self.source_scope_sha256,
            "target_scope_sha256": self.target_scope_sha256,
            "source_intervention_revision_sha256": (
                self.source_intervention_revision_sha256
            ),
            "target_intervention_revision_sha256": (
                self.target_intervention_revision_sha256
            ),
            "source_rendered_content_sha256": (
                self.source_rendered_content_sha256
            ),
            "target_rendered_content_sha256": (
                self.target_rendered_content_sha256
            ),
            "payload_invariant_sha256": self.payload_invariant_sha256,
            "acquisition_provenance_sha256": (
                self.acquisition_provenance_sha256
            ),
            "preserved_scope_coordinates": list(
                self.preserved_scope_coordinates
            ),
            "changed_scope_coordinates": list(
                self.changed_scope_coordinates
            ),
            "invariant_checks": list(self.invariant_checks),
            "status": self.status,
            "reason": self.reason,
            "evidence_refs": list(self.evidence_refs),
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def compile_intervention_revision_transport(
    source: DecisionInterventionProposal,
    target: DecisionInterventionProposal,
    *,
    source_payload_invariant_sha256: str,
    target_payload_invariant_sha256: str,
    evidence_refs: Iterable[str],
) -> InterventionRevisionTransport:
    """Relate context-local revisions without collapsing their identities."""

    scope_names = (
        "task_sha256",
        "controller_sha256",
        "context_sha256",
        "choice_set_sha256",
        "action_vocabulary_sha256",
    )
    preserved = tuple(
        name for name in scope_names
        if getattr(source.scope, name) == getattr(target.scope, name)
    )
    changed = tuple(
        name for name in scope_names
        if getattr(source.scope, name) != getattr(target.scope, name)
    )
    invariant_pairs = (
        ("payload_invariant", source_payload_invariant_sha256,
         target_payload_invariant_sha256),
        ("acquisition_provenance", source.acquisition_provenance.sha256,
         target.acquisition_provenance.sha256),
        ("intervention_kind", source.intervention_kind,
         target.intervention_kind),
        ("provider_id", source.provider_id, target.provider_id),
        ("provider_revision", source.provider_revision_sha256,
         target.provider_revision_sha256),
        ("tokenizer", source.tokenizer_sha256, target.tokenizer_sha256),
        ("rendered_token_count", source.rendered_token_count,
         target.rendered_token_count),
        ("predicted_decision_delta", source.predicted_decision_delta,
         target.predicted_decision_delta),
        ("prompt_cost_per_token", source.prompt_cost_per_token,
         target.prompt_cost_per_token),
        ("primitive_action_cost", source.primitive_action_cost,
         target.primitive_action_cost),
        ("authority_score", source.authority_score,
         target.authority_score),
        ("actionability_score", source.actionability_score,
         target.actionability_score),
        ("recency_score", source.recency_score, target.recency_score),
        ("guard_features", source.guard_features, target.guard_features),
        ("semantic_features", source.semantic_features,
         target.semantic_features),
        ("support_refs", source.support_refs, target.support_refs),
        ("boundary_support_refs", source.boundary_support_refs,
         target.boundary_support_refs),
        ("content_ref", source.content_ref, target.content_ref),
    )
    failed = [name for name, left, right in invariant_pairs if left != right]
    forbidden_scope_changes = sorted(
        set(changed) - {"context_sha256"}
    )
    if forbidden_scope_changes:
        reason = (
            "forbidden_scope_coordinate_changed:"
            + ",".join(forbidden_scope_changes)
        )
    elif "context_sha256" not in changed:
        reason = "context_coordinate_did_not_change"
    elif failed:
        reason = "intervention_invariant_changed:" + ",".join(failed)
    else:
        reason = "context_rerender_preserves_payload_provenance_and_cost"
    status = "transportable" if not forbidden_scope_changes and (
        "context_sha256" in changed and not failed
    ) else "refused"
    return InterventionRevisionTransport(
        source_scope_sha256=source.scope.sha256,
        target_scope_sha256=target.scope.sha256,
        source_intervention_revision_sha256=(
            source.intervention_revision_sha256
        ),
        target_intervention_revision_sha256=(
            target.intervention_revision_sha256
        ),
        source_rendered_content_sha256=source.rendered_content_sha256,
        target_rendered_content_sha256=target.rendered_content_sha256,
        payload_invariant_sha256=_nonempty(
            source_payload_invariant_sha256,
            "source_payload_invariant_sha256",
        ),
        acquisition_provenance_sha256=(
            source.acquisition_provenance.sha256
        ),
        preserved_scope_coordinates=preserved,
        changed_scope_coordinates=changed,
        invariant_checks=tuple(name for name, _left, _right in invariant_pairs),
        status=status,
        reason=reason,
        evidence_refs=tuple(evidence_refs),
    )


@dataclass(frozen=True)
class ObjectCatalogTransport:
    """One partial occurrence transport or an inspectable refusal."""

    source_observation_sha256: str
    source_catalog_sha256: str
    target_observation_sha256: str
    target_catalog_sha256: str
    required_source_object_refs: tuple[str, ...]
    object_ref_bindings: tuple[tuple[str, str, str], ...]
    status: str
    reason: str
    evidence_refs: tuple[str, ...]
    method: str = "unique_type_sha256"

    def __post_init__(self) -> None:
        for name in (
            "source_observation_sha256",
            "source_catalog_sha256",
            "target_observation_sha256",
            "target_catalog_sha256",
            "reason",
            "method",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if self.status not in _ATTEMPT_STATUSES:
            raise ValueError(f"unknown transport status {self.status!r}")
        required = _canonical(self.required_source_object_refs)
        if not required:
            raise ValueError("transport requires source object refs")
        object.__setattr__(
            self,
            "required_source_object_refs",
            required,
        )
        bindings = tuple(sorted(
            (
                _nonempty(source, "source_object_ref"),
                _nonempty(target, "target_object_ref"),
                _nonempty(type_sha, "type_sha256"),
            )
            for source, target, type_sha in self.object_ref_bindings
        ))
        sources = [row[0] for row in bindings]
        targets = [row[1] for row in bindings]
        if len(sources) != len(set(sources)):
            raise ValueError("transport repeats a source object")
        if len(targets) != len(set(targets)):
            raise ValueError("transport merges target objects")
        if not set(sources).issubset(set(required)):
            raise ValueError("transport contains an unrequested source ref")
        if self.status == "transportable" and set(sources) != set(required):
            raise ValueError(
                "transportable attempt must bind every required source ref"
            )
        object.__setattr__(self, "object_ref_bindings", bindings)
        evidence = _canonical(self.evidence_refs)
        if not evidence:
            raise ValueError("transport requires evidence refs")
        object.__setattr__(self, "evidence_refs", evidence)

    def map_ref(self, source_object_ref: str) -> str:
        if self.status != "transportable":
            raise ValueError("refused transport cannot map objects")
        matches = [
            target
            for source, target, _type_sha in self.object_ref_bindings
            if source == str(source_object_ref)
        ]
        if len(matches) != 1:
            raise ValueError(
                "source object is absent from transport authority"
            )
        return matches[0]

    def map_path(self, source_path: Iterable[str]) -> tuple[str, ...]:
        return tuple(self.map_ref(value) for value in source_path)

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "object_catalog_transport",
            "source_observation_sha256": (
                self.source_observation_sha256
            ),
            "source_catalog_sha256": self.source_catalog_sha256,
            "target_observation_sha256": (
                self.target_observation_sha256
            ),
            "target_catalog_sha256": self.target_catalog_sha256,
            "required_source_object_refs": list(
                self.required_source_object_refs
            ),
            "object_ref_bindings": [
                {
                    "source_object_ref": source,
                    "target_object_ref": target,
                    "type_sha256": type_sha,
                }
                for source, target, type_sha in self.object_ref_bindings
            ],
            "status": self.status,
            "reason": self.reason,
            "evidence_refs": list(self.evidence_refs),
            "method": self.method,
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def compile_unique_type_object_transport(
    source_catalog: GridObjectCatalog,
    target_catalog: GridObjectCatalog,
    *,
    required_source_object_refs: Iterable[str],
    evidence_refs: Iterable[str],
) -> ObjectCatalogTransport:
    """Bind requested occurrences only when their type is unique on both sides."""

    required = _canonical(required_source_object_refs)
    source_by_ref = {
        row.object_ref: row for row in source_catalog.objects
    }
    missing_source = set(required) - set(source_by_ref)
    if missing_source:
        raise ValueError(
            f"required source refs are absent: {sorted(missing_source)}"
        )
    bindings = []
    refusal_reason = ""
    for source_ref in required:
        source = source_by_ref[source_ref]
        source_matches = [
            row for row in source_catalog.objects
            if row.type_sha256 == source.type_sha256
        ]
        target_matches = [
            row for row in target_catalog.objects
            if row.type_sha256 == source.type_sha256
        ]
        if len(source_matches) != 1 or len(target_matches) != 1:
            refusal_reason = (
                "required_contract_object_has_no_unique_target"
            )
            continue
        bindings.append((
            source_ref,
            target_matches[0].object_ref,
            source.type_sha256,
        ))
    status = (
        "transportable"
        if len(bindings) == len(required)
        else "refused"
    )
    return ObjectCatalogTransport(
        source_observation_sha256=source_catalog.observation_sha256,
        source_catalog_sha256=source_catalog.sha256,
        target_observation_sha256=target_catalog.observation_sha256,
        target_catalog_sha256=target_catalog.sha256,
        required_source_object_refs=required,
        object_ref_bindings=tuple(bindings),
        status=status,
        reason=(
            "unique_type_correspondence_complete"
            if status == "transportable"
            else refusal_reason
        ),
        evidence_refs=tuple(evidence_refs),
    )


def transport_object_role_contract(
    source_contract: ObjectRolePathContract,
    *,
    target_scope: MemoryScope,
    target_catalog: GridObjectCatalog,
    transport: ObjectCatalogTransport | CausalObjectLineageTransport,
    intervention_transport: InterventionRevisionTransport,
    evidence_refs: Iterable[str],
) -> ObjectRolePathContract:
    """Construct the target contract only under complete object authority."""

    if transport.status != "transportable":
        raise ValueError("refused object transport cannot move a contract")
    if source_contract.scope.context_sha256 != (
        transport.source_observation_sha256
    ):
        raise ValueError("source contract crossed transport observation")
    if source_contract.catalog_sha256 != (
        transport.source_catalog_sha256
    ):
        raise ValueError("source contract crossed transport catalog")
    if target_scope.context_sha256 != (
        transport.target_observation_sha256
    ):
        raise ValueError("target scope crossed transport observation")
    if target_catalog.sha256 != transport.target_catalog_sha256:
        raise ValueError("target catalog crossed transport authority")
    if intervention_transport.status != "transportable":
        raise ValueError("refused intervention transport cannot move a contract")
    if intervention_transport.source_scope_sha256 != source_contract.scope.sha256:
        raise ValueError("intervention transport crossed source scope")
    if intervention_transport.target_scope_sha256 != target_scope.sha256:
        raise ValueError("intervention transport crossed target scope")
    if intervention_transport.source_intervention_revision_sha256 != (
        source_contract.intervention_revision_sha256
    ):
        raise ValueError("intervention transport crossed source revision")
    for name in (
        "task_sha256",
        "controller_sha256",
        "choice_set_sha256",
        "action_vocabulary_sha256",
    ):
        if getattr(source_contract.scope, name) != getattr(
            target_scope,
            name,
        ):
            raise ValueError(
                f"contract transport changed {name}"
            )
    return ObjectRolePathContract(
        scope=target_scope,
        catalog_sha256=target_catalog.sha256,
        intervention_revision_sha256=(
            intervention_transport.target_intervention_revision_sha256
        ),
        required_controlled_object_ref=transport.map_ref(
            source_contract.required_controlled_object_ref
        ),
        required_waypoint_refs=transport.map_path(
            source_contract.required_waypoint_refs
        ),
        forbidden_controlled_object_refs=transport.map_path(
            source_contract.forbidden_controlled_object_refs
        ),
        evidence_refs=tuple(evidence_refs),
    )


@dataclass(frozen=True)
class ResponseTransportCandidate:
    """Pre-outcome judgment about one target blind proposal."""

    source_family_sha256: str
    source_response_sha256: str
    object_transport_sha256: str
    intervention_transport_sha256: str
    source_contract_sha256: str
    target_contract_sha256: str
    source_pre_proposal_sha256: str
    source_post_proposal_sha256: str
    target_pre_proposal_sha256: str
    source_pre_basin_sha256: str
    target_pre_basin_sha256: str
    source_basin_signature: tuple[tuple[str, Any], ...]
    target_basin_signature: tuple[tuple[str, Any], ...]
    mapped_source_post_path: tuple[str, ...]
    status: str
    action: str
    reason: str

    def __post_init__(self) -> None:
        for name in (
            "source_family_sha256",
            "source_response_sha256",
            "object_transport_sha256",
            "intervention_transport_sha256",
            "source_contract_sha256",
            "target_contract_sha256",
            "source_pre_proposal_sha256",
            "source_post_proposal_sha256",
            "target_pre_proposal_sha256",
            "source_pre_basin_sha256",
            "target_pre_basin_sha256",
            "reason",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if self.status not in _CANDIDATE_STATUSES:
            raise ValueError(f"unknown candidate status {self.status!r}")
        if self.action not in _ACTIONS:
            raise ValueError(f"unknown candidate action {self.action!r}")
        if (
            self.status == "candidate_commuting"
            and self.action not in {
                "explore_lineage",
                "explore_transport",
            }
        ):
            raise ValueError("commuting candidate must remain exploratory")
        if (
            self.status == "refused"
            and self.action != "refuse_transport"
        ):
            raise ValueError("refused candidate must refuse transport")

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "response_transport_candidate",
            "source_family_sha256": self.source_family_sha256,
            "source_response_sha256": self.source_response_sha256,
            "object_transport_sha256": self.object_transport_sha256,
            "intervention_transport_sha256": (
                self.intervention_transport_sha256
            ),
            "source_contract_sha256": self.source_contract_sha256,
            "target_contract_sha256": self.target_contract_sha256,
            "source_pre_proposal_sha256": (
                self.source_pre_proposal_sha256
            ),
            "source_post_proposal_sha256": (
                self.source_post_proposal_sha256
            ),
            "target_pre_proposal_sha256": (
                self.target_pre_proposal_sha256
            ),
            "source_pre_basin_sha256": self.source_pre_basin_sha256,
            "target_pre_basin_sha256": self.target_pre_basin_sha256,
            "source_basin_signature": dict(
                self.source_basin_signature
            ),
            "target_basin_signature": dict(
                self.target_basin_signature
            ),
            "mapped_source_post_path": list(
                self.mapped_source_post_path
            ),
            "status": self.status,
            "action": self.action,
            "reason": self.reason,
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def compile_response_transport_candidate(
    *,
    source_family: ObjectResponseFamily,
    source_response: ObjectBasinResponse,
    object_transport: (
        ObjectCatalogTransport | CausalObjectLineageTransport
    ),
    intervention_transport: InterventionRevisionTransport,
    source_contract: ObjectRolePathContract,
    target_contract: ObjectRolePathContract,
    source_pre_proposal: ObjectLinkedControllerProposal,
    source_post_proposal: ObjectLinkedControllerProposal,
    target_pre_proposal: ObjectLinkedControllerProposal,
) -> ResponseTransportCandidate:
    """Compile a prospective target-fiber probe without granting target credit."""

    if object_transport.status != "transportable":
        raise ValueError("refused object transport cannot form a square")
    if intervention_transport.status != "transportable":
        raise ValueError("refused intervention transport cannot form a square")
    if source_response not in source_family.responses:
        raise ValueError("response is absent from source family")
    if source_response.scope_sha256 != source_contract.scope.sha256:
        raise ValueError("source response crossed contract scope")
    if source_response.contract_sha256 != source_contract.sha256:
        raise ValueError("source response crossed contract identity")
    if source_response.catalog_sha256 != (
        object_transport.source_catalog_sha256
    ):
        raise ValueError("source response crossed transport catalog")
    if source_pre_proposal.scope != source_contract.scope:
        raise ValueError("source pre proposal crossed contract scope")
    if source_post_proposal.scope != source_contract.scope:
        raise ValueError("source post proposal crossed contract scope")
    if object_plan_basin_sha256(
        source_pre_proposal,
        source_contract,
    ) != source_response.pre_basin_sha256:
        raise ValueError("source witness occupies a different response basin")
    if not proposal_satisfies_object_contract(
        source_post_proposal,
        source_contract,
    ):
        raise ValueError("source post witness does not satisfy its contract")
    if target_pre_proposal.scope != target_contract.scope:
        raise ValueError("target pre proposal crossed target scope")
    if target_pre_proposal.catalog_sha256 != (
        object_transport.target_catalog_sha256
    ):
        raise ValueError("target pre proposal crossed transport catalog")
    if intervention_transport.source_scope_sha256 != (
        source_contract.scope.sha256
    ):
        raise ValueError("intervention transport crossed source scope")
    if intervention_transport.target_scope_sha256 != (
        target_contract.scope.sha256
    ):
        raise ValueError("intervention transport crossed target scope")
    if intervention_transport.source_intervention_revision_sha256 != (
        source_contract.intervention_revision_sha256
    ):
        raise ValueError("source contract crossed intervention transport")
    if intervention_transport.target_intervention_revision_sha256 != (
        target_contract.intervention_revision_sha256
    ):
        raise ValueError("target contract crossed intervention transport")
    if target_contract.required_controlled_object_ref != (
        object_transport.map_ref(
            source_contract.required_controlled_object_ref
        )
    ):
        raise ValueError("target contract changed controlled-object map")
    if target_contract.required_waypoint_refs != (
        object_transport.map_path(
            source_contract.required_waypoint_refs
        )
    ):
        raise ValueError("target contract changed waypoint map")

    source_signature = object_plan_basin_signature(
        source_pre_proposal,
        source_contract,
    )
    target_signature = object_plan_basin_signature(
        target_pre_proposal,
        target_contract,
    )
    mapped_post_path = object_transport.map_path(
        source_post_proposal.path
    )
    target_required_path = (
        target_contract.required_controlled_object_ref,
        *target_contract.required_waypoint_refs,
    )
    post_commutes = bool(
        mapped_post_path[0] == target_required_path[0]
        and all(
            value in mapped_post_path[1:]
            for value in target_required_path[1:]
        )
    )
    signatures_match = source_signature == target_signature
    if signatures_match and post_commutes:
        status = "candidate_commuting"
        if isinstance(
            object_transport,
            CausalObjectLineageTransport,
        ):
            action = "explore_lineage"
            reason = "lineage_contract_and_response_square_commute"
        else:
            action = "explore_transport"
            reason = "object_contract_and_response_square_commute"
    else:
        status = "refused"
        action = "refuse_transport"
        reason = (
            "target_blind_basin_mismatch"
            if not signatures_match
            else "source_post_path_does_not_transport"
        )
    return ResponseTransportCandidate(
        source_family_sha256=source_family.sha256,
        source_response_sha256=source_response.sha256,
        object_transport_sha256=object_transport.sha256,
        intervention_transport_sha256=intervention_transport.sha256,
        source_contract_sha256=source_contract.sha256,
        target_contract_sha256=target_contract.sha256,
        source_pre_proposal_sha256=source_pre_proposal.sha256,
        source_post_proposal_sha256=source_post_proposal.sha256,
        target_pre_proposal_sha256=target_pre_proposal.sha256,
        source_pre_basin_sha256=source_response.pre_basin_sha256,
        target_pre_basin_sha256=object_plan_basin_sha256(
            target_pre_proposal,
            target_contract,
        ),
        source_basin_signature=tuple(sorted(source_signature.items())),
        target_basin_signature=tuple(sorted(target_signature.items())),
        mapped_source_post_path=mapped_post_path,
        status=status,
        action=action,
        reason=reason,
    )


__all__ = [
    "InterventionRevisionTransport",
    "ObjectCatalogTransport",
    "ResponseTransportCandidate",
    "compile_intervention_revision_transport",
    "compile_response_transport_candidate",
    "compile_unique_type_object_transport",
    "transport_object_role_contract",
]
