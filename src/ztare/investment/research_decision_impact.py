"""Verify that one frozen research artifact changed one typed decision."""

from __future__ import annotations

from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, require_finite, require_text, timestamp_key


RESEARCH_DECISION_SNAPSHOT_SCHEMA = "jaggedthoughts-research-decision-snapshot-v1"
RESEARCH_DECISION_IMPACT_RECEIPT_SCHEMA = "jaggedthoughts-research-decision-impact-receipt-v1"
_FREEZE_SCHEMA = "jaggedthoughts-research-budget-freeze-v1"
_PROPOSAL_AUDIT_SCHEMAS = {
    "jaggedthoughts-public-equity-paper-proposal-audit-v1",
    "jaggedthoughts-public-fund-paper-proposal-audit-v1",
}
_CHOICE_FIELDS = {"selected_ids", "weights", "disposition", "next_transition", "blockers"}


def _digest(value: Any, label: str) -> str:
    digest = require_text(value, label)
    if len(digest) != 64:
        raise ValueError(f"{label} must be a SHA-256 digest")
    return digest


def _signed(raw: Mapping[str, Any], *, schema: str, field: str, label: str) -> dict[str, Any]:
    body = dict(raw)
    digest = str(body.pop(field, ""))
    if body.get("schema") != schema or len(digest) != 64 or stable_sha256(body) != digest:
        raise ValueError(f"invalid {label} identity")
    return {**body, field: digest}


def _choice(raw: Mapping[str, Any]) -> dict[str, Any]:
    unknown = sorted(set(raw) - _CHOICE_FIELDS)
    if unknown:
        raise ValueError(f"unsupported decision choice fields: {', '.join(unknown)}")
    choice: dict[str, Any] = {}
    if "selected_ids" in raw:
        selected = [require_text(value, "decision selected_id") for value in raw["selected_ids"]]
        if len(selected) != len(set(selected)):
            raise ValueError("decision selected_ids must be unique")
        choice["selected_ids"] = selected
    if "weights" in raw:
        weights = {
            require_text(key, "decision weight id"): require_finite(value, f"decision weight {key}")
            for key, value in raw["weights"].items()
        }
        choice["weights"] = dict(sorted(weights.items()))
    for field in ("disposition", "next_transition"):
        if field in raw:
            choice[field] = (
                require_text(raw[field], f"decision {field}") if raw[field] is not None else None
            )
    if "blockers" in raw:
        choice["blockers"] = sorted({
            require_text(value, "decision blocker") for value in raw["blockers"]
        })
    if not choice:
        raise ValueError("decision choice cannot be empty")
    return choice


def compile_research_decision_snapshot(
    *, decision_kind: str, subject_id: str, decision_surface_id: str,
    source_artifact_ref: str, source_artifact_sha256: str,
    choice: Mapping[str, Any], captured_at: str,
) -> dict[str, Any]:
    """Freeze semantic decision state separately from administrative metadata."""
    normalized = _choice(choice)
    body = {
        "schema": RESEARCH_DECISION_SNAPSHOT_SCHEMA,
        "decision_kind": require_text(decision_kind, "decision kind"),
        "subject_id": require_text(subject_id, "decision subject_id"),
        "decision_surface_id": require_text(decision_surface_id, "decision surface_id"),
        "source_artifact_ref": require_text(source_artifact_ref, "decision source artifact ref"),
        "source_artifact_sha256": _digest(
            source_artifact_sha256, "decision source artifact sha256",
        ),
        "captured_at": canonical_timestamp(captured_at, "decision captured_at"),
        "choice": normalized,
        "decision_value_sha256": stable_sha256(normalized),
    }
    return {**body, "snapshot_sha256": stable_sha256(body)}


def compile_candidate_proposal_decision_snapshot(
    proposal_audit: Mapping[str, Any], *, candidate_leaf: str,
    source_artifact_ref: str, captured_at: str,
    required_dossier_sha256: str | None = None,
) -> dict[str, Any]:
    """Project one verified proposal-audit row onto the paper-watch decision surface."""
    audit = dict(proposal_audit)
    audit_sha = _digest(audit.pop("audit_sha256", ""), "proposal audit sha256")
    if audit.get("schema") not in _PROPOSAL_AUDIT_SCHEMAS or stable_sha256(audit) != audit_sha:
        raise ValueError("invalid proposal audit identity")
    captured = canonical_timestamp(captured_at, "proposal decision captured_at")
    if timestamp_key(str(audit.get("compiled_at"))) > timestamp_key(captured):
        raise ValueError("proposal decision snapshot cannot precede its audit")
    leaf = _digest(candidate_leaf, "proposal decision candidate leaf")
    rows = [
        dict(row) for row in audit.get("rows") or ()
        if isinstance(row, Mapping) and row.get("candidate_leaf") == leaf
    ]
    if len(rows) != 1:
        raise ValueError("proposal decision requires one candidate-bound audit row")
    row = rows[0]
    proposal = row.get("proposal")
    if isinstance(proposal, Mapping):
        proposal = dict(proposal)
        proposal_sha = _digest(
            proposal.pop("proposal_sha256", ""), "paper proposal sha256",
        )
        if stable_sha256(proposal) != proposal_sha:
            raise ValueError("invalid paper proposal identity")
        proposal = {**proposal, "proposal_sha256": proposal_sha}
        if required_dossier_sha256 is not None and (
            (proposal.get("evidence") or {}).get("dossier_sha256")
            != _digest(required_dossier_sha256, "required dossier sha256")
        ):
            raise ValueError("paper proposal does not consume the settled dossier")
        choice = {
            "selected_ids": (
                [require_text(proposal.get("proposal_id"), "paper proposal id")]
                if proposal.get("activation_eligible") is True else []
            ),
            "disposition": require_text(row.get("status"), "paper proposal status"),
            "next_transition": proposal.get("next_activation"),
            "blockers": list(proposal.get("activation_blockers") or ()),
        }
        source_sha = proposal_sha
    else:
        if required_dossier_sha256 is not None:
            raise ValueError("paper proposal audit did not consume the settled dossier")
        choice = {
            "selected_ids": [],
            "disposition": require_text(row.get("status"), "paper proposal status"),
            "next_transition": "repair_candidate_evidence",
            "blockers": list(row.get("blockers") or ()),
        }
        source_sha = stable_sha256(row)
    return compile_research_decision_snapshot(
        decision_kind="candidate_zero_weight_paper_watch",
        subject_id=leaf,
        decision_surface_id=f"candidate-paper-watch:{leaf}",
        source_artifact_ref=source_artifact_ref,
        source_artifact_sha256=source_sha,
        choice=choice,
        captured_at=captured,
    )


def _verified_snapshot(raw: Mapping[str, Any]) -> dict[str, Any]:
    snapshot = _signed(
        raw, schema=RESEARCH_DECISION_SNAPSHOT_SCHEMA,
        field="snapshot_sha256", label="research decision snapshot",
    )
    if snapshot.get("choice") != _choice(snapshot.get("choice") or {}):
        raise ValueError("decision snapshot choice is not canonical")
    if snapshot.get("decision_value_sha256") != stable_sha256(snapshot["choice"]):
        raise ValueError("decision snapshot value identity mismatch")
    _digest(snapshot.get("source_artifact_sha256"), "decision source artifact sha256")
    return snapshot


def compile_research_decision_impact_receipt(
    *, research_budget_freeze: Mapping[str, Any], work_id: str,
    evidence_ref: str, evidence_sha256: str, evidence_available_at: str,
    decision_before: Mapping[str, Any], decision_after: Mapping[str, Any],
    consumed_at: str,
) -> dict[str, Any]:
    """Bind one prospective research freeze to a later semantic decision delta."""
    freeze = _signed(
        research_budget_freeze, schema=_FREEZE_SCHEMA,
        field="freeze_sha256", label="research budget freeze",
    )
    work = require_text(work_id, "research work_id")
    selected = {
        str(item.get("work_id") or "")
        for arm in freeze.get("arms") or () for item in arm.get("selected") or ()
    }
    if work not in selected:
        raise ValueError("decision impact work was not frozen by the research tournament")
    before, after = _verified_snapshot(decision_before), _verified_snapshot(decision_after)
    comparable = ("decision_kind", "subject_id", "decision_surface_id")
    if any(before.get(field) != after.get(field) for field in comparable):
        raise ValueError("decision impact snapshots cross a decision identity boundary")
    frozen_at = timestamp_key(str(freeze["frozen_at"]))
    evidence_at = timestamp_key(canonical_timestamp(
        evidence_available_at, "research evidence available_at",
    ))
    consumed = timestamp_key(canonical_timestamp(consumed_at, "research evidence consumed_at"))
    if not (
        timestamp_key(str(before["captured_at"])) <= frozen_at
        <= evidence_at <= consumed <= timestamp_key(str(after["captured_at"]))
    ):
        raise ValueError("decision impact chronology must be before <= freeze <= evidence <= consume <= after")
    evidence = {
        "work_id": work,
        "artifact_ref": require_text(evidence_ref, "research evidence ref"),
        "artifact_sha256": _digest(evidence_sha256, "research evidence sha256"),
        "available_at": canonical_timestamp(
            evidence_available_at, "research evidence available_at",
        ),
    }
    edge_body = {
        "schema": "jaggedthoughts-research-evidence-consumption-edge-v1",
        "edge_kind": "research_evidence_consumed_by_decision",
        "freeze_sha256": research_budget_freeze["freeze_sha256"],
        "work_id": work,
        "evidence_sha256": evidence["artifact_sha256"],
        "decision_before_sha256": decision_before["snapshot_sha256"],
        "decision_after_sha256": decision_after["snapshot_sha256"],
        "consumed_at": canonical_timestamp(consumed_at, "research evidence consumed_at"),
    }
    edge = {**edge_body, "edge_sha256": stable_sha256(edge_body)}
    changed = before["decision_value_sha256"] != after["decision_value_sha256"]
    body = {
        "schema": RESEARCH_DECISION_IMPACT_RECEIPT_SCHEMA,
        "freeze_sha256": research_budget_freeze["freeze_sha256"],
        "work_id": work,
        "evidence": evidence,
        "decision_before": decision_before,
        "decision_after": decision_after,
        "evidence_consumption_edge": edge,
        "decision_changed": changed,
        "decision_change_basis": "typed_semantic_value_delta" if changed else "semantic_value_unchanged",
        "authority": "research_scheduler_settlement_evidence_only",
        "queue_mutation_authority": False,
        "capital_authority": False,
    }
    return {**body, "impact_receipt_sha256": stable_sha256(body)}


def verify_research_decision_impact_receipt(
    raw: Mapping[str, Any], *, research_budget_freeze: Mapping[str, Any],
    work_id: str, evidence_ref: str, evidence_sha256: str,
) -> dict[str, Any]:
    """Recompile the receipt so asserted booleans and edges cannot substitute for identity."""
    receipt = _signed(
        raw, schema=RESEARCH_DECISION_IMPACT_RECEIPT_SCHEMA,
        field="impact_receipt_sha256", label="research decision impact receipt",
    )
    evidence = receipt.get("evidence") if isinstance(receipt.get("evidence"), Mapping) else {}
    edge = receipt.get("evidence_consumption_edge")
    edge = _signed(
        edge if isinstance(edge, Mapping) else {},
        schema="jaggedthoughts-research-evidence-consumption-edge-v1",
        field="edge_sha256", label="research evidence-consumption edge",
    )
    if evidence.get("artifact_ref") != evidence_ref:
        raise ValueError("decision impact evidence ref differs from the settled artifact")
    if evidence.get("artifact_sha256") != _digest(
        evidence_sha256, "settled research evidence sha256",
    ):
        raise ValueError("decision impact evidence digest differs from the settled artifact")
    rebuilt = compile_research_decision_impact_receipt(
        research_budget_freeze=research_budget_freeze,
        work_id=work_id,
        evidence_ref=str(evidence.get("artifact_ref") or ""),
        evidence_sha256=str(evidence.get("artifact_sha256") or ""),
        evidence_available_at=str(evidence.get("available_at") or ""),
        decision_before=receipt.get("decision_before") or {},
        decision_after=receipt.get("decision_after") or {},
        consumed_at=str(edge.get("consumed_at") or ""),
    )
    if rebuilt != raw:
        raise ValueError("research decision impact receipt does not recompile exactly")
    return receipt


__all__ = [
    "RESEARCH_DECISION_IMPACT_RECEIPT_SCHEMA", "RESEARCH_DECISION_SNAPSHOT_SCHEMA",
    "compile_candidate_proposal_decision_snapshot",
    "compile_research_decision_impact_receipt", "compile_research_decision_snapshot",
    "verify_research_decision_impact_receipt",
]
