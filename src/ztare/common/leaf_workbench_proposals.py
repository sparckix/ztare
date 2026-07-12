from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ztare.common.file_io import append_jsonl
from ztare.common.leaf_workbench_contract import validate_leaf_workbench_capability_proposal
from ztare.common.structured_blocks import json_objects_after_marker
from ztare.common.sealed_boundary_cegar import validate_lowerability_blocked_receipt
from ztare.common.tool_synthesis_contract import (
    classify_tool_target,
    tool_synthesis_card,
)
from ztare.research_director.strategy_decision_policy import (
    StrategyCardBatchSubmission,
    StrategyDecisionPosition,
    normalize_decision_policy,
    submit_strategy_card_batch,
)


PROPOSAL_LEDGER = "leaf_workbench_capability_proposals.jsonl"
PROPOSAL_SCHEMA = "ztare-leaf-workbench-capability-proposal-card-v1"


def extract_leaf_workbench_capability_proposals(text: str) -> list[dict[str, Any]]:
    proposals: list[dict[str, Any]] = []
    for payload in json_objects_after_marker(text or "", "LEAF_WORKBENCH_CAPABILITY_PROPOSAL:"):
        proposals.append(validate_leaf_workbench_capability_proposal(payload))
    return proposals


def proposal_fingerprint(proposal: dict[str, Any]) -> str:
    blob = json.dumps(proposal, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def sync_leaf_workbench_capability_proposals(
    project_dir: str | Path,
    text: str,
    *,
    source_ref: str = "candidate_thesis",
    default_target_artifact: str | None = None,
    require_lowerability_obstruction: bool = True,
    decision_policy: str | None = None,
    decision_positions: list[StrategyDecisionPosition | dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Persist missing-workbench-action proposals as cold meta-tool observations.

    Proposals are second-order: they are never evidence for the current
    candidate. In science runs, proposals remain queued cold backlog; Strategy
    Office batch review decides whether evidenced recurring blockers become
    active tool_synthesis cards.
    """
    proposals = extract_leaf_workbench_capability_proposals(text)
    if not proposals:
        return []
    lowerability_obstruction = _has_lowerability_obstruction(text)
    project = Path(project_dir)
    ledger = project / "workspace" / PROPOSAL_LEDGER
    seen = _seen_hashes(ledger)
    written: list[dict[str, Any]] = []
    for proposal in proposals:
        digest = proposal_fingerprint(proposal)
        if digest in seen:
            continue
        card = {
            "schema": PROPOSAL_SCHEMA,
            "proposal_sha256": digest,
            "status": "queued",
            "source_ref": source_ref,
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "proposal": proposal,
            "authority": (
                "meta-tool proposal only; cannot support candidate adoption until "
                "implemented as a registered workbench capability with tests"
            ),
        }
        if lowerability_obstruction or not require_lowerability_obstruction:
            tool_card = _maybe_write_tool_synthesis_card(
                project,
                proposal,
                proposal_sha256=digest,
                source_ref=source_ref,
                default_target_artifact=default_target_artifact,
                decision_policy=decision_policy,
                decision_positions=decision_positions,
            )
            if tool_card is not None:
                card["tool_synthesis_card_sha256"] = tool_card.get("failure_family_sha")
            else:
                card["tool_synthesis_status"] = "awaiting_strategy_office_batch_decision"
        else:
            card["tool_synthesis_status"] = "deferred_until_lowerability_obstruction"
        append_jsonl(ledger, card)
        seen.add(digest)
        written.append(card)
    return written


def review_leaf_workbench_capability_proposals(
    project_dir: str | Path,
    *,
    decision_policy: str,
    decision_positions: list[StrategyDecisionPosition | dict[str, Any]] | None = None,
    limit: int | None = None,
    source_ref: str = "leaf_workbench_capability_proposals:batch_review",
) -> dict[str, Any]:
    """Promote evidenced capability proposals through the Strategy decision membrane."""

    project = Path(project_dir)
    policy = normalize_decision_policy(decision_policy)
    if policy != "direct" and not decision_positions:
        return {
            "schema": "ztare-leaf-workbench-proposal-review-v1",
            "status": "blocked",
            "recommendation": "escalate",
            "rationale": "non-direct tool proposal review requires explicit decision positions",
            "approved_cards": [],
            "written_cards": [],
        }
    rows = _pending_tool_synthesis_proposal_rows(project)
    if limit is not None:
        rows = rows[: max(0, int(limit))]
    eligible: list[tuple[dict[str, Any], dict[str, Any]]] = []
    ineligible: list[dict[str, Any]] = []
    for row in rows:
        card = _tool_synthesis_card_for_proposal(
            row["proposal"],
            proposal_sha256=str(row.get("proposal_sha256") or ""),
            source_ref=str(row.get("source_ref") or source_ref),
            default_target_artifact=None,
        )
        if card is None:
            ineligible.append(row)
        else:
            eligible.append((row, card))
    if ineligible:
        _append_proposal_review_dispositions(
            project,
            ineligible,
            status="ineligible",
            tool_synthesis_status="not_mutable_sensor",
            source_ref=source_ref,
            rationale="proposal target is not an allowed mutable-sensor surface",
        )
    cards = [card for _row, card in eligible]
    if not cards:
        return {
            "schema": "ztare-leaf-workbench-proposal-review-v1",
            "status": "empty",
            "recommendation": "reject",
            "rationale": "no evidenced pending capability proposals eligible for tool_synthesis",
            "approved_cards": [],
            "written_cards": [],
        }
    decision = submit_strategy_card_batch(
        StrategyCardBatchSubmission(
            project_dir=project,
            cards=cards,
            policy=policy,
            backend=os.environ.get("ZTARE_STRATEGY_DECISION_BACKEND", "auto"),
            positions=decision_positions,
            source_ref=source_ref,
            quorum=_env_int("ZTARE_STRATEGY_DECISION_QUORUM"),
            persist_decision=True,
        )
    )
    written = list(decision.get("written_cards") or [])
    recommendation = str(decision.get("recommendation") or "escalate")
    if recommendation == "approve":
        _append_proposal_review_dispositions(
            project,
            [row for row, _card in eligible],
            status="promoted",
            tool_synthesis_status="approved_by_strategy_office",
            source_ref=source_ref,
            rationale=str(decision.get("rationale") or ""),
            decision_ref=str(decision.get("decision_sha256") or ""),
            written_card_refs=[str(card.get("failure_family_sha") or "") for card in written],
        )
    elif recommendation == "reject":
        _append_proposal_review_dispositions(
            project,
            [row for row, _card in eligible],
            status="review_rejected",
            tool_synthesis_status="rejected_by_strategy_office",
            source_ref=source_ref,
            rationale=str(decision.get("rationale") or ""),
            decision_ref=str(decision.get("decision_sha256") or ""),
        )
    else:
        _append_proposal_review_dispositions(
            project,
            [row for row, _card in eligible],
            status="review_escalated",
            tool_synthesis_status="escalated_by_strategy_office",
            source_ref=source_ref,
            rationale=str(decision.get("rationale") or ""),
            decision_ref=str(decision.get("decision_sha256") or ""),
        )
    out = dict(decision)
    out.pop("approved_cards", None)
    out["schema"] = "ztare-leaf-workbench-proposal-review-v1"
    out["written_cards"] = written
    return out


def pending_leaf_workbench_tool_synthesis_proposals(
    project_dir: str | Path,
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Return cold proposal rows eligible for Strategy Office tool review."""

    rows = _pending_tool_synthesis_proposal_rows(Path(project_dir))
    if limit is not None:
        rows = rows[: max(0, int(limit))]
    return [dict(row) for row in rows]


def _has_lowerability_obstruction(text: str) -> bool:
    for payload in json_objects_after_marker(text or "", "LOWERABILITY_BLOCKED:"):
        try:
            validate_lowerability_blocked_receipt(payload)
        except ValueError:
            continue
        return True
    return False


def _pending_tool_synthesis_proposal_rows(project: Path) -> list[dict[str, Any]]:
    ledger = project / "workspace" / PROPOSAL_LEDGER
    if not ledger.exists():
        return []
    latest: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for line in ledger.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        digest = str(row.get("proposal_sha256") or "")
        if not digest:
            continue
        if digest not in latest:
            order.append(digest)
        latest[digest] = row
    return [
        latest[digest]
        for digest in order
        if latest[digest].get("status") == "queued"
        and latest[digest].get("tool_synthesis_status")
        == "awaiting_strategy_office_batch_decision"
        and "tool_synthesis_card_sha256" not in latest[digest]
    ]


def _append_proposal_review_dispositions(
    project: Path,
    rows: list[dict[str, Any]],
    *,
    status: str,
    tool_synthesis_status: str,
    source_ref: str,
    rationale: str,
    decision_ref: str = "",
    written_card_refs: list[str] | None = None,
) -> None:
    if not rows:
        return
    ledger = project / "workspace" / PROPOSAL_LEDGER
    for row in rows:
        digest = str(row.get("proposal_sha256") or "")
        if not digest:
            continue
        append_jsonl(
            ledger,
            {
                "schema": PROPOSAL_SCHEMA,
                "proposal_sha256": digest,
                "status": status,
                "tool_synthesis_status": tool_synthesis_status,
                "source_ref": source_ref,
                "reviewed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "proposal": dict(row.get("proposal") or {}),
                "decision_ref": decision_ref,
                "rationale": rationale,
                "written_card_refs": list(written_card_refs or []),
                "authority": "proposal review disposition; latest row controls pending status",
            },
        )


def _maybe_write_tool_synthesis_card(
    project: Path,
    proposal: dict[str, Any],
    *,
    proposal_sha256: str,
    source_ref: str,
    default_target_artifact: str | None = None,
    decision_policy: str | None = None,
    decision_positions: list[StrategyDecisionPosition | dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    card = _tool_synthesis_card_for_proposal(
        proposal,
        proposal_sha256=proposal_sha256,
        source_ref=source_ref,
        default_target_artifact=default_target_artifact,
    )
    if card is None:
        return None
    raw_policy = (
        decision_policy
        or os.environ.get("ZTARE_TOOL_SYNTHESIS_DECISION_POLICY")
        or ""
    )
    if not raw_policy.strip():
        return None
    policy = normalize_decision_policy(raw_policy)
    if policy != "direct" and not decision_positions:
        return None
    decision = submit_strategy_card_batch(
        StrategyCardBatchSubmission(
            project_dir=project,
            cards=[card],
            policy=policy,
            backend=os.environ.get("ZTARE_STRATEGY_DECISION_BACKEND", "auto"),
            positions=decision_positions,
            source_ref=f"{source_ref}:leaf_workbench_capability_proposal:{proposal_sha256}",
            quorum=_env_int("ZTARE_STRATEGY_DECISION_QUORUM"),
            persist_decision=True,
        )
    )
    written = list(decision.get("written_cards") or [])
    return written[0] if written else None


def _tool_synthesis_card_for_proposal(
    proposal: dict[str, Any],
    *,
    proposal_sha256: str,
    source_ref: str,
    default_target_artifact: str | None = None,
) -> dict[str, Any] | None:
    target = str(proposal.get("target_artifact") or default_target_artifact or "").strip()
    if not target or classify_tool_target(target) != "mutable_sensor":
        return None
    capability_contract = {
        "proposed_capability_id": proposal.get("proposed_capability_id"),
        "input_contract": proposal.get("input_contract"),
        "output_contract": proposal.get("output_contract"),
        "secret_policy": proposal.get("secret_policy"),
        "safety_invariant": proposal.get("safety_invariant"),
    }
    card = tool_synthesis_card(
        proposed_capability_id=str(proposal.get("proposed_capability_id") or ""),
        gap_statement=str(proposal.get("gap_statement") or ""),
        target_artifact=target,
        capability_contract=capability_contract,
        evaluator=str(proposal.get("evaluator") or ""),
        rollback_condition=str(proposal.get("rollback_condition") or ""),
        source_ref=f"{source_ref}:leaf_workbench_capability_proposal:{proposal_sha256}",
    )
    return card


def _env_int(name: str) -> int | None:
    raw = os.environ.get(name)
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _seen_hashes(path: Path) -> set[str]:
    if not path.exists():
        return set()
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        digest = row.get("proposal_sha256") if isinstance(row, dict) else None
        if isinstance(digest, str) and digest:
            seen.add(digest)
    return seen
