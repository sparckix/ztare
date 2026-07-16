"""Typed identity for observed transitions and epoch transport.

Grid differences are observations.  They do not decide whether a row belongs
to within-epoch dynamics or crosses an environment-owned boundary.  That
identity is supplied by the adapter/collector and travels with the row.

Object transport is a relation rather than a bijection.  ``None`` is the empty
endpoint: ``None -> x`` records genesis, ``x -> None`` annihilation, and
multiple links permit fission or fusion.  An empty correspondence makes no
cross-epoch object-identity claim.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


TransitionKind = Literal[
    "dynamics",
    "epoch_boundary",
    "reset_boundary",
    "unclassified",
]

TRUSTED_TRANSITION_IDENTITY_AUTHORITIES = frozenset(
    {"environment_adapter", "episode_collector"}
)
BOUNDARY_TRANSITION_KINDS = frozenset({"epoch_boundary", "reset_boundary"})


@dataclass(frozen=True)
class ObjectIdentityLink:
    """One edge in a partial cross-epoch object correspondence."""

    source_object_id: str | None
    target_object_id: str | None
    evidence_ref: str | None = None

    def __post_init__(self) -> None:
        if self.source_object_id is None and self.target_object_id is None:
            raise ValueError("identity correspondence cannot map empty to empty")
        for value, label in (
            (self.source_object_id, "source_object_id"),
            (self.target_object_id, "target_object_id"),
        ):
            if value is not None and not str(value).strip():
                raise ValueError(f"{label} must be non-empty when present")

    @property
    def relation(self) -> str:
        if self.source_object_id is None:
            return "genesis"
        if self.target_object_id is None:
            return "annihilation"
        return "correspondence"

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "source_object_id": self.source_object_id,
            "target_object_id": self.target_object_id,
            "relation": self.relation,
        }
        if self.evidence_ref:
            out["evidence_ref"] = self.evidence_ref
        return out

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ObjectIdentityLink":
        if not isinstance(payload, dict):
            raise ValueError("object identity link must be an object")
        return cls(
            source_object_id=payload.get("source_object_id"),
            target_object_id=payload.get("target_object_id"),
            evidence_ref=payload.get("evidence_ref"),
        )


@dataclass(frozen=True)
class TransitionIdentity:
    """Adapter-owned classification and partial transport across one row."""

    kind: TransitionKind
    authority: str
    source_epoch: str | int | None = None
    target_epoch: str | int | None = None
    boundary_kind: str | None = None
    object_correspondence: tuple[ObjectIdentityLink, ...] = field(default_factory=tuple)
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        allowed = {"dynamics", "epoch_boundary", "reset_boundary", "unclassified"}
        if self.kind not in allowed:
            raise ValueError(f"unknown transition identity kind: {self.kind!r}")
        if not str(self.authority or "").strip():
            raise ValueError("transition identity authority is required")
        if self.kind == "dynamics" and (
            self.source_epoch is not None
            and self.target_epoch is not None
            and self.source_epoch != self.target_epoch
        ):
            raise ValueError("within-epoch dynamics cannot change epoch identity")
        if self.kind in BOUNDARY_TRANSITION_KINDS and (
            self.source_epoch is not None
            and self.target_epoch is not None
            and self.source_epoch == self.target_epoch
        ):
            raise ValueError("boundary transition must sever or change epoch identity")
        if self.boundary_kind is not None and not str(self.boundary_kind).strip():
            raise ValueError("boundary_kind must be non-empty when present")

    @property
    def is_authoritative(self) -> bool:
        return self.authority in TRUSTED_TRANSITION_IDENTITY_AUTHORITIES

    @property
    def is_boundary(self) -> bool:
        return self.kind in BOUNDARY_TRANSITION_KINDS

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "schema": "ztare-transition-identity-v1",
            "kind": self.kind,
            "authority": self.authority,
            "source_epoch": self.source_epoch,
            "target_epoch": self.target_epoch,
            "object_correspondence": [
                link.to_dict() for link in self.object_correspondence
            ],
            "evidence_refs": list(self.evidence_refs),
        }
        if self.boundary_kind is not None:
            out["boundary_kind"] = self.boundary_kind
        return out

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TransitionIdentity":
        if not isinstance(payload, dict):
            raise ValueError("transition identity must be an object")
        schema = payload.get("schema")
        if schema not in (None, "ztare-transition-identity-v1"):
            raise ValueError(f"unsupported transition identity schema: {schema!r}")
        raw_links = payload.get("object_correspondence") or []
        if not isinstance(raw_links, list):
            raise ValueError("object_correspondence must be a list")
        raw_refs = payload.get("evidence_refs") or []
        if not isinstance(raw_refs, list):
            raise ValueError("evidence_refs must be a list")
        return cls(
            kind=str(payload.get("kind") or "unclassified"),  # type: ignore[arg-type]
            authority=str(payload.get("authority") or ""),
            source_epoch=payload.get("source_epoch"),
            target_epoch=payload.get("target_epoch"),
            boundary_kind=payload.get("boundary_kind"),
            object_correspondence=tuple(
                ObjectIdentityLink.from_dict(row) for row in raw_links
            ),
            evidence_refs=tuple(str(ref) for ref in raw_refs if str(ref).strip()),
        )


def authoritative_boundary(identity: TransitionIdentity | None) -> bool:
    return bool(identity and identity.is_authoritative and identity.is_boundary)


def authoritative_dynamics(identity: TransitionIdentity | None) -> bool:
    """Whether a row carries positive within-epoch-law authority.

    Older ARC collectors emitted ``kind=dynamics`` as the default whenever
    the public API exposed no level or terminal event.  That is negative
    evidence: the same API does not expose automatic respawns.  Requiring an
    evidence reference keeps those legacy defaults from suppressing a
    structurally witnessed boundary, while adapters with a positive dynamics
    signal can still protect a row from heuristic reclassification.
    """
    return bool(
        identity
        and identity.is_authoritative
        and identity.kind == "dynamics"
        and identity.evidence_refs
    )
