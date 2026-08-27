"""Typed opportunity-funnel lifecycle over distinct investment objects.

The state chart is a projection.  Each event creates a new typed object and a
receipt connecting it to its predecessor; a source observation is never
mutated into a screen, profile, decision, allocation, or scorecard.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from ztare.common.control_state_machine import ControlStateChart, ControlTransition
from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, require_refs, require_text


OPPORTUNITY_FUNNEL = ControlStateChart(
    schema="jaggedthoughts-opportunity-funnel-state-chart-v1",
    transitions=(
        ControlTransition("observed", "qualify", "screened", "source coverage and screen receipt exist"),
        ControlTransition("screened", "draft", "draft", "play, rival mechanism, falsifiers, and source epoch exist"),
        ControlTransition("draft", "activate_paper", "active_paper", "operator confirmation and compile receipt exist"),
        ControlTransition("active_paper", "admit", "portfolio_candidate", "decision epoch and portfolio identity are compatible"),
        ControlTransition("active_paper", "monitor", "monitored", "next evidence request is named"),
        ControlTransition("portfolio_candidate", "allocate_paper", "allocated_paper", "portfolio constraints and frontier certificate pass"),
        ControlTransition("portfolio_candidate", "decline", "monitored", "dominating alternative or binding constraint is recorded"),
        ControlTransition("allocated_paper", "settle", "settled", "outcome and counterfactual are point-in-time bound"),
        ControlTransition("active_paper", "settle", "settled", "zero-weight paper policy and counterfactual are point-in-time bound"),
        ControlTransition("monitored", "settle", "settled", "missed-opportunity counterfactual is point-in-time bound"),
        ControlTransition("settled", "learn", "learned", "scorecard changes a model, screen, or next evidence request"),
        ControlTransition("monitored", "new_evidence", "observed", "a newer source epoch exists"),
        ControlTransition("learned", "new_evidence", "observed", "a newer source epoch exists"),
        ControlTransition("draft", "archive", "archived", "reason is recorded"),
        ControlTransition("active_paper", "archive", "archived", "reason is recorded"),
        ControlTransition("monitored", "archive", "archived", "reason is recorded"),
    ),
)


@dataclass(frozen=True, slots=True)
class FunnelObjectRef:
    object_kind: str
    object_id: str
    sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "object_kind", require_text(self.object_kind, "funnel object kind"))
        object.__setattr__(self, "object_id", require_text(self.object_id, "funnel object id"))
        digest = require_text(self.sha256, "funnel object sha256")
        if len(digest) != 64:
            raise ValueError("funnel object sha256 must be a SHA-256 digest")

    def to_dict(self) -> dict[str, str]:
        return {"object_kind": self.object_kind, "object_id": self.object_id, "sha256": self.sha256}

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "FunnelObjectRef":
        return cls(
            object_kind=str(raw.get("object_kind") or ""),
            object_id=str(raw.get("object_id") or ""),
            sha256=str(raw.get("sha256") or ""),
        )


@dataclass(frozen=True, slots=True)
class FunnelTransitionReceipt:
    transition_id: str
    from_state: str
    event: str
    to_state: str
    occurred_at: str
    predecessor: FunnelObjectRef
    successor: FunnelObjectRef
    guard_refs: tuple[str, ...]
    context: Mapping[str, Any] = field(default_factory=dict)
    receipt_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        for attr in ("transition_id", "from_state", "event", "to_state"):
            object.__setattr__(self, attr, require_text(getattr(self, attr), f"funnel {attr}"))
        expected = OPPORTUNITY_FUNNEL.next_state(self.from_state, self.event)
        if expected != self.to_state:
            raise ValueError(
                f"inadmissible funnel transition {self.from_state} --{self.event}--> {self.to_state}; expected {expected}"
            )
        if self.predecessor.object_kind == self.successor.object_kind and self.predecessor.object_id == self.successor.object_id:
            raise ValueError("funnel transitions must create or route to a distinct successor object")
        object.__setattr__(self, "occurred_at", canonical_timestamp(self.occurred_at, "funnel occurred_at"))
        object.__setattr__(self, "guard_refs", require_refs(self.guard_refs, "funnel guard ref"))
        object.__setattr__(self, "context", dict(self.context))
        object.__setattr__(self, "receipt_sha256", stable_sha256(self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "jaggedthoughts-opportunity-funnel-transition-v1",
            "transition_id": self.transition_id,
            "from_state": self.from_state,
            "event": self.event,
            "to_state": self.to_state,
            "occurred_at": self.occurred_at,
            "predecessor": self.predecessor.to_dict(),
            "successor": self.successor.to_dict(),
            "guard_refs": list(self.guard_refs),
            "context": dict(self.context),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "receipt_sha256": self.receipt_sha256}

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "FunnelTransitionReceipt":
        predecessor = raw.get("predecessor")
        successor = raw.get("successor")
        if not isinstance(predecessor, Mapping) or not isinstance(successor, Mapping):
            raise ValueError("funnel receipt predecessor and successor must be mappings")
        receipt = cls(
            transition_id=str(raw.get("transition_id") or ""),
            from_state=str(raw.get("from_state") or ""),
            event=str(raw.get("event") or ""),
            to_state=str(raw.get("to_state") or ""),
            occurred_at=str(raw.get("occurred_at") or ""),
            predecessor=FunnelObjectRef.from_dict(predecessor),
            successor=FunnelObjectRef.from_dict(successor),
            guard_refs=tuple(raw.get("guard_refs") or ()),
            context=dict(raw.get("context") or {}),
        )
        declared = str(raw.get("receipt_sha256") or receipt.receipt_sha256)
        if declared != receipt.receipt_sha256:
            raise ValueError("funnel transition receipt hash mismatch")
        return receipt


def funnel_surface(state: str, *, context: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return OPPORTUNITY_FUNNEL.surface_object(state=state, context=dict(context or {}))


__all__ = [
    "FunnelObjectRef", "FunnelTransitionReceipt", "OPPORTUNITY_FUNNEL", "funnel_surface",
]
