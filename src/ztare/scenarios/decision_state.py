"""One compiled, domain-neutral decision state over the governed argument graph."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any

from ztare.scenarios.argument_kernel import argument_analysis
from ztare.scenarios.governed_types import GovernedState
from ztare.scenarios.tiers import TIER_NAME

_HEADLINE = {
    "SUPPORTED": "Supported at the current trust floor",
    "BLOCKED": "Decision needs verification",
    "REFUTED": "Does not stand as written",
}
_POSTURE = {"SUPPORTED": "proceed", "BLOCKED": "investigate", "REFUTED": "revise"}


@dataclass(frozen=True)
class DecisionState:
    payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        return dict(self.payload)


def _transition(before: Any, after: Any) -> dict[str, Any]:
    """Return one stable, presentation-neutral transition record."""
    return {"from": before, "to": after, "changed": before != after}


def diff_decision_states(before: DecisionState | dict[str, Any],
                         after: DecisionState | dict[str, Any]) -> dict[str, Any]:
    """Describe exactly what a governed-state mutation changed in the compiled decision.

    The delta is derived from two compiled states. Callers never infer a decision change from a model score or
    from the fact that evidence was admitted; valid evidence can leave the governing hinge or posture unchanged.
    """
    prior = before.to_payload() if isinstance(before, DecisionState) else dict(before)
    current = after.to_payload() if isinstance(after, DecisionState) else dict(after)
    prior_strength = list((prior.get("strength") or {}).get("profile") or [])
    current_strength = list((current.get("strength") or {}).get("profile") or [])
    width = max(len(prior_strength), len(current_strength))
    strength_delta = [
        float(current_strength[index] if index < len(current_strength) else 0.0)
        - float(prior_strength[index] if index < len(prior_strength) else 0.0)
        for index in range(width)
    ]

    transitions = {
        "status": _transition(prior.get("status"), current.get("status")),
        "posture": _transition(prior.get("posture"), current.get("posture")),
        "trust_floor": _transition(prior.get("trust_floor"), current.get("trust_floor")),
        "strength_profile": _transition(prior_strength, current_strength),
        "hinge": _transition(prior.get("hinge"), current.get("hinge")),
        "next_test": _transition(prior.get("next_test"), current.get("next_test")),
        "minimal_cores": _transition(prior.get("minimal_cores") or [], current.get("minimal_cores") or []),
        "counts": _transition(prior.get("counts") or {}, current.get("counts") or {}),
    }
    changed_fields = [name for name, transition in transitions.items() if transition["changed"]]
    decision_changed = prior.get("fingerprint") != current.get("fingerprint")
    if transitions["status"]["changed"]:
        summary = f"{prior.get('status') or 'UNKNOWN'} -> {current.get('status') or 'UNKNOWN'}"
    elif decision_changed:
        summary = "Decision posture held; its support structure changed."
    elif changed_fields:
        summary = "Decision held; the admitted evidence did not change its governing support."
    else:
        summary = "No decision change."

    return {
        "schema": "ztare-decision-delta-v1",
        "changed": bool(changed_fields),
        "decision_changed": decision_changed,
        "from_fingerprint": str(prior.get("fingerprint") or ""),
        "to_fingerprint": str(current.get("fingerprint") or ""),
        "summary": summary,
        "changed_fields": changed_fields,
        **transitions,
        "strength_delta": strength_delta,
    }


def compile_decision_state(governed: GovernedState, *, analysis: dict[str, Any] | None = None) -> DecisionState:
    """Compile the single decision posture consumed by Map, Thesis, Results, Verdict, and deliverables.

    Model scores and forecasts are intentionally absent. They are observations about a run; this state is the
    deterministic judgment over admitted nodes, typed relations, and warrants.
    """
    analysis = analysis or argument_analysis(governed)
    status = str(analysis.get("verdict") or "BLOCKED")
    strength = analysis.get("strength") or {}
    text_of = {element.id: element.text for element in governed.elements}
    hinge_id = str(analysis.get("hinge") or "")
    hinge_ties = [str(item) for item in (analysis.get("hinge_ties") or [])]
    agenda = list(analysis.get("test_agenda") or [])
    next_row = agenda[0] if agenda else None
    next_test = None
    if next_row:
        assumption = str(next_row.get("assumption") or "")
        next_test = {
            "id": assumption,
            "text": text_of.get(assumption, assumption),
            "flips_alone": bool(next_row.get("flips_alone")),
            "in_cores": int(next_row.get("in_cores") or 0),
            "cost": float(next_row.get("cost") or 0.0),
        }

    fingerprint_material = {
        "status": status,
        "warrant_ceiling": analysis.get("warrant_ceiling") or "",
        "cores": analysis.get("minimal_cores") or [],
        "node_states": analysis.get("node_states") or {},
        "strength_profile": strength.get("profile") or [],
    }
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    warrant = str(analysis.get("warrant_ceiling") or "")
    payload = {
        "schema": "ztare-decision-state-v1",
        "fingerprint": fingerprint,
        "status": status,
        "posture": _POSTURE.get(status, "investigate"),
        "headline": _HEADLINE.get(status, status.title()),
        "reason": str(analysis.get("reason") or ""),
        "coverage": float(analysis.get("coverage") or 0.0),
        "warrant_ceiling": warrant,
        "trust_floor": TIER_NAME.get(warrant, "none"),
        "strength": {
            "status": strength.get("status"),
            "profile": list(strength.get("profile") or []),
            "converged": bool(strength.get("converged", True)),
        },
        "hinge": {
            "id": hinge_id,
            "text": text_of.get(hinge_id, hinge_id),
            "ties": hinge_ties,
        } if hinge_id else None,
        "minimal_cores": list(analysis.get("minimal_cores") or []),
        "next_test": next_test,
        "open_test_count": len(agenda),
        "counts": {
            "claims": len(governed.of_kind("thesis")) + len(governed.of_kind("claim")),
            "evidence": len(governed.of_kind("evidence")),
            "edges": len(governed.edges),
        },
    }
    return DecisionState(payload)
