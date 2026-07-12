from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from ztare.common.file_io import append_jsonl
from ztare.common.operator_proposal_contract import family_sha, write_proposal_cards
from ztare.common.optional_kernels import import_optional_kernel_module


DECISION_RECEIPT_SCHEMA = "ztare-strategy-decision-receipt-v1"
DECISION_LEDGER = "strategy_decision_receipts.jsonl"
DECISION_LATEST = "strategy_decision_latest.json"
STRATEGY_LEDGER = "strategy_experiments.jsonl"

DecisionPositionKind = Literal["approve", "reject", "abstain", "recuse", "veto"]
DecisionRecommendation = Literal["approve", "reject", "escalate"]

_DIRECT_POLICIES = {"", "direct", "none", "off"}
_PROFILE_ALIASES = {
    "single": "single_authority",
    "single_authority": "single_authority",
    "majority": "majority",
    "quorum_majority": "quorum_majority",
    "veto": "veto_review",
    "veto_review": "veto_review",
    "unanimity": "unanimity",
}


@dataclass(frozen=True)
class StrategyDecisionPosition:
    actor_id: str
    role_id: str
    position: str
    rationale: str
    evidence_refs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StrategyCardBatchSubmission:
    project_dir: str | Path
    cards: list[dict[str, Any]]
    source_ref: str
    policy: str | None = "direct"
    backend: str = "auto"
    positions: list[StrategyDecisionPosition | dict[str, Any]] | None = None
    subject_ref: str | None = None
    eligible_roles: list[str] | None = None
    eligible_actors: list[str] | None = None
    quorum: int | None = None
    persist_decision: bool | None = None
    ledger_rel: str = STRATEGY_LEDGER


def normalize_decision_policy(policy: str | None) -> str:
    key = str(policy or "direct").strip().lower().replace("-", "_")
    if key in _DIRECT_POLICIES:
        return "direct"
    if key not in _PROFILE_ALIASES:
        raise ValueError(
            f"unsupported strategy decision policy {policy!r}; "
            f"expected direct or one of {sorted(_PROFILE_ALIASES)}"
        )
    return _PROFILE_ALIASES[key]


def default_approval_position(
    *,
    actor_id: str = "agent.strategy_office_leaf",
    role_id: str = "role.strategy_leaf",
    rationale: str = "strategy leaf proposed the card batch",
    evidence_refs: list[str] | None = None,
) -> StrategyDecisionPosition:
    return StrategyDecisionPosition(
        actor_id=actor_id,
        role_id=role_id,
        position="approve",
        rationale=rationale,
        evidence_refs=list(evidence_refs or []),
    )


def submit_strategy_card_batch(submission: StrategyCardBatchSubmission) -> dict[str, Any]:
    """Single write membrane for Strategy Office cards.

    Producers may build experiment cards, repair cards, or tool-synthesis cards,
    but card writes go through this function: aggregate approval first, then
    append only approved cards to the Strategy ledger. This is card governance,
    not candidate authority.
    """

    project = Path(submission.project_dir)
    decision = decide_strategy_card_batch(
        project_dir=project,
        cards=list(submission.cards),
        policy=submission.policy,
        backend=submission.backend,
        positions=submission.positions,
        subject_ref=submission.subject_ref,
        source_ref=submission.source_ref,
        eligible_roles=submission.eligible_roles,
        eligible_actors=submission.eligible_actors,
        quorum=submission.quorum,
        persist=submission.persist_decision,
    )
    approved = list(decision.get("approved_cards") or [])
    written = (
        write_proposal_cards(project / "workspace" / submission.ledger_rel, approved)
        if approved
        else []
    )
    # Fail-loud accounting: every approved card is either written or gets an
    # explicit per-card rejection receipt (write_proposal_cards silently skips
    # failure_family_sha duplicates — that skip must never be invisible here).
    written_shas = [str(row.get("failure_family_sha")) for row in written]
    unmatched = list(written_shas)
    rejected: list[dict[str, Any]] = []
    for card in approved:
        sha = str(card.get("failure_family_sha") or family_sha(card.get("failure_family")))
        if sha in unmatched:
            unmatched.remove(sha)
            continue
        rejected.append({
            "schema": "ztare-strategy-card-rejection-v1",
            "failure_family": card.get("failure_family"),
            "failure_family_sha": sha,
            "failing_field": "failure_family_sha",
            "reason": (
                f"duplicate failure_family_sha {sha}: already present in "
                f"workspace/{submission.ledger_rel} or earlier in this batch"
            ),
        })
    if len(written) + len(rejected) != len(approved):
        raise RuntimeError(
            "strategy card write accounting broke: "
            f"{len(approved)} approved != {len(written)} written + {len(rejected)} rejected"
        )
    out = dict(decision)
    out["written_cards"] = written
    out["written_card_count"] = len(written)
    out["rejected_cards"] = rejected
    out["rejected_card_count"] = len(rejected)
    out["ledger_ref"] = f"workspace/{submission.ledger_rel}"
    return out


def decide_strategy_card_batch(
    *,
    project_dir: str | Path,
    cards: list[dict[str, Any]],
    policy: str | None = "direct",
    backend: str = "auto",
    positions: list[StrategyDecisionPosition | dict[str, Any]] | None = None,
    subject_ref: str | None = None,
    source_ref: str = "strategy_office:convene",
    eligible_roles: list[str] | None = None,
    eligible_actors: list[str] | None = None,
    quorum: int | None = None,
    persist: bool | None = None,
) -> dict[str, Any]:
    """Aggregate approval for a batch of Strategy Office cards.

    This is an approval membrane, not a candidate gate. A non-direct policy can
    block or escalate card writes, but it cannot promote a model, weaken replay,
    or close a terminal/verifier obligation.
    """

    project = Path(project_dir)
    normalized_policy = normalize_decision_policy(policy)
    batch_sha = _card_batch_sha(cards)
    subject = subject_ref or f"strategy_card_batch:{batch_sha}"
    should_persist = bool(persist) if persist is not None else normalized_policy != "direct"
    if normalized_policy == "direct":
        receipt = _receipt(
            project=project,
            policy=normalized_policy,
            backend="direct",
            subject_ref=subject,
            source_ref=source_ref,
            cards=cards,
            recommendation="approve",
            status="computed",
            rationale="direct strategy-office write path",
            positions=[],
            counts={},
            quorum=0,
            quorum_met=True,
            case_ref="",
        )
        if should_persist:
            _persist_receipt(project, receipt)
        return receipt

    normalized_positions = _normalize_positions(
        positions or [
            default_approval_position(
                evidence_refs=[source_ref, subject],
            )
        ]
    )
    roles = _unique(eligible_roles or [p.role_id for p in normalized_positions])
    actors = _unique(eligible_actors or [])
    if not roles and not actors:
        roles = ["role.strategy_leaf"]

    backend_choice = str(backend or "auto").strip().lower()
    cognitive_error = ""
    if backend_choice in {"auto", "cognitive_firm", "cognitive-firm"}:
        try:
            receipt = _decide_with_cognitive_firm(
                project=project,
                policy=normalized_policy,
                subject_ref=subject,
                source_ref=source_ref,
                cards=cards,
                positions=normalized_positions,
                eligible_roles=roles,
                eligible_actors=actors,
                quorum=quorum,
            )
            if should_persist:
                _persist_receipt(project, receipt)
            return receipt
        except Exception as exc:  # noqa: BLE001
            cognitive_error = f"{type(exc).__name__}: {str(exc)[:240]}"
            if backend_choice in {"cognitive_firm", "cognitive-firm"}:
                receipt = _receipt(
                    project=project,
                    policy=normalized_policy,
                    backend="cognitive_firm",
                    subject_ref=subject,
                    source_ref=source_ref,
                    cards=cards,
                    recommendation="escalate",
                    status="escalated",
                    rationale=f"cognitive_firm decision backend unavailable: {cognitive_error}",
                    positions=normalized_positions,
                    counts={},
                    quorum=int(quorum or 0),
                    quorum_met=False,
                    case_ref="",
                )
                if should_persist:
                    _persist_receipt(project, receipt)
                return receipt

    receipt = _decide_locally(
        project=project,
        policy=normalized_policy,
        subject_ref=subject,
        source_ref=source_ref,
        cards=cards,
        positions=normalized_positions,
        eligible_roles=roles,
        eligible_actors=actors,
        quorum=quorum,
        backend_note=cognitive_error,
    )
    if should_persist:
        _persist_receipt(project, receipt)
    return receipt


def _decide_with_cognitive_firm(
    *,
    project: Path,
    policy: str,
    subject_ref: str,
    source_ref: str,
    cards: list[dict[str, Any]],
    positions: list[StrategyDecisionPosition],
    eligible_roles: list[str],
    eligible_actors: list[str],
    quorum: int | None,
) -> dict[str, Any]:
    da = _load_cognitive_firm_decision_aggregation()
    log_path = project / "workspace" / "cognitive_firm_strategy_decisions.jsonl"
    case_id = "dac_" + hashlib.sha256(
        f"{subject_ref}|{policy}|{_positions_sha(positions)}".encode("utf-8")
    ).hexdigest()[:12]
    case = da.open_decision_aggregation_case_from_profile(
        procedure_profile=policy,
        subject_ref=subject_ref,
        decision_class="strategy_card_batch",
        scope_kind="ztare_project",
        scope_ref=str(project),
        opened_by="ztare.strategy_office",
        eligibility_basis="ztare strategy decision policy",
        eligible_roles=eligible_roles,
        eligible_actors=eligible_actors,
        quorum=quorum,
        downstream_ref="workspace/strategy_experiments.jsonl",
        evidence_refs=[source_ref],
        metadata={"source": "ztare_strategy_decision_policy"},
        case_id=case_id,
        log_path=log_path,
    )
    for position in positions:
        da.record_decision_position(
            case.case_id,
            actor_id=position.actor_id,
            role_id=position.role_id,
            position=position.position,
            rationale=position.rationale,
            evidence_refs=position.evidence_refs,
            metadata=position.metadata,
            position_id="dpos_" + hashlib.sha256(
                f"{case.case_id}|{position.actor_id}|{position.role_id}".encode("utf-8")
            ).hexdigest()[:12],
            log_path=log_path,
        )
    computed = da.compute_decision_aggregation_case(case.case_id, log_path=log_path)
    result = computed.result.as_dict() if computed.result else {}
    recommendation = str(result.get("recommendation") or "escalate")
    return _receipt(
        project=project,
        policy=policy,
        backend="cognitive_firm",
        subject_ref=subject_ref,
        source_ref=source_ref,
        cards=cards,
        recommendation=_recommendation(recommendation),
        status=str(computed.status),
        rationale=str(result.get("rationale") or "cognitive_firm decision aggregation"),
        positions=positions,
        counts={
            "approve": int(result.get("approvals") or 0),
            "reject": int(result.get("rejections") or 0),
            "abstain": int(result.get("abstentions") or 0),
            "recuse": int(result.get("recusals") or 0),
            "veto": int(result.get("vetoes") or 0),
        },
        quorum=int(result.get("quorum") or 0),
        quorum_met=bool(result.get("quorum_met")),
        case_ref=f"{log_path.relative_to(project)}:{computed.case_id}",
    )


def _decide_locally(
    *,
    project: Path,
    policy: str,
    subject_ref: str,
    source_ref: str,
    cards: list[dict[str, Any]],
    positions: list[StrategyDecisionPosition],
    eligible_roles: list[str],
    eligible_actors: list[str],
    quorum: int | None,
    backend_note: str = "",
) -> dict[str, Any]:
    counts = _position_counts(positions)
    slot_count = max(1, len(_unique(eligible_roles)) + len(_unique(eligible_actors)))
    effective_quorum = _default_quorum(policy, slot_count) if quorum is None else max(1, int(quorum))
    non_abstain = counts["approve"] + counts["reject"] + counts["veto"]
    quorum_met = non_abstain >= effective_quorum
    recommendation: DecisionRecommendation
    rationale: str
    if policy == "single_authority":
        if non_abstain != 1:
            recommendation, rationale, quorum_met = (
                "escalate",
                "single_authority requires exactly one non-abstaining position",
                False,
            )
        elif counts["approve"] == 1:
            recommendation, rationale, quorum_met = "approve", "single authority approved", True
        else:
            recommendation, rationale, quorum_met = "reject", "single authority rejected", True
    elif policy == "unanimity":
        if counts["veto"] or counts["reject"]:
            recommendation, rationale = "reject", "unanimity saw rejection or veto"
        elif counts["approve"] >= effective_quorum and not counts["abstain"] and not counts["recuse"]:
            recommendation, rationale, quorum_met = "approve", "all eligible positions approved", True
        else:
            recommendation, rationale, quorum_met = "escalate", "unanimity requires every eligible slot", False
    elif policy == "veto_review" and counts["veto"]:
        recommendation, rationale = "reject", "eligible veto recorded"
    elif not quorum_met:
        recommendation, rationale = "escalate", "quorum not met"
    elif counts["approve"] > counts["reject"]:
        recommendation, rationale = "approve", "approvals exceed rejections"
    elif counts["reject"] > counts["approve"]:
        recommendation, rationale = "reject", "rejections exceed approvals"
    else:
        recommendation, rationale = "escalate", "tie without decisive result"
    if backend_note:
        rationale = f"{rationale}; cognitive_firm fallback={backend_note}"
    return _receipt(
        project=project,
        policy=policy,
        backend="local",
        subject_ref=subject_ref,
        source_ref=source_ref,
        cards=cards,
        recommendation=recommendation,
        status="computed" if recommendation in {"approve", "reject"} else "escalated",
        rationale=rationale,
        positions=positions,
        counts=counts,
        quorum=effective_quorum,
        quorum_met=quorum_met,
        case_ref="",
    )


def _receipt(
    *,
    project: Path,
    policy: str,
    backend: str,
    subject_ref: str,
    source_ref: str,
    cards: list[dict[str, Any]],
    recommendation: DecisionRecommendation,
    status: str,
    rationale: str,
    positions: list[StrategyDecisionPosition],
    counts: dict[str, int],
    quorum: int,
    quorum_met: bool,
    case_ref: str,
) -> dict[str, Any]:
    card_refs = [_card_ref(card) for card in cards]
    approved = cards if recommendation == "approve" else []
    receipt = {
        "schema": DECISION_RECEIPT_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "project": str(project),
        "policy": policy,
        "backend": backend,
        "subject_ref": subject_ref,
        "source_ref": source_ref,
        "status": status,
        "recommendation": recommendation,
        "rationale": rationale,
        "counts": dict(counts),
        "quorum": quorum,
        "quorum_met": quorum_met,
        "case_ref": case_ref,
        "card_count": len(cards),
        "card_refs": card_refs,
        "approved_card_count": len(approved),
        "approved_card_refs": [_card_ref(card) for card in approved],
        "positions": [p.as_dict() for p in positions],
        "approved_cards": approved,
        "authority": (
            "strategy decision only; may approve, reject, or escalate Strategy "
            "card writes, but cannot promote candidates or override gates"
        ),
    }
    receipt["decision_sha256"] = hashlib.sha256(
        json.dumps(
            {
                "policy": policy,
                "backend": backend,
                "subject_ref": subject_ref,
                "recommendation": recommendation,
                "card_refs": card_refs,
                "positions": receipt["positions"],
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return receipt


def _persist_receipt(project: Path, receipt: dict[str, Any]) -> None:
    workspace = project / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    latest = dict(receipt)
    latest.pop("approved_cards", None)
    (workspace / DECISION_LATEST).write_text(
        json.dumps(latest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    row = dict(latest)
    append_jsonl(workspace / DECISION_LEDGER, row)


def _load_cognitive_firm_decision_aggregation() -> Any:
    return import_optional_kernel_module(
        "cognitive_firm.orchestration.decision_aggregation",
        kernel_id="cognitive_firm",
    )


def _normalize_positions(rows: list[StrategyDecisionPosition | dict[str, Any]]) -> list[StrategyDecisionPosition]:
    out: list[StrategyDecisionPosition] = []
    for row in rows:
        if isinstance(row, StrategyDecisionPosition):
            out.append(row)
            continue
        if not isinstance(row, dict):
            continue
        actor_id = row.get("actor_id") or row.get("agent_id") or row.get("authority_id")
        role_id = row.get("role_id") or row.get("role") or row.get("authority_role")
        rationale = row.get("rationale") or row.get("reason") or row.get("summary")
        out.append(
            StrategyDecisionPosition(
                actor_id=str(actor_id or ""),
                role_id=str(role_id or ""),
                position=str(row.get("position") or ""),
                rationale=str(rationale or ""),
                evidence_refs=[str(ref) for ref in row.get("evidence_refs") or []],
                metadata=dict(row.get("metadata") or {}),
            )
        )
    if not out:
        raise ValueError("at least one decision position is required")
    for pos in out:
        if pos.position not in {"approve", "reject", "abstain", "recuse", "veto"}:
            raise ValueError(f"invalid decision position: {pos.position!r}")
        if not pos.actor_id or not pos.role_id or not pos.rationale:
            raise ValueError("decision positions require actor_id, role_id, and rationale")
    return out


def _position_counts(positions: list[StrategyDecisionPosition]) -> dict[str, int]:
    return {
        key: sum(1 for pos in positions if pos.position == key)
        for key in ("approve", "reject", "abstain", "recuse", "veto")
    }


def _default_quorum(policy: str, slot_count: int) -> int:
    if policy == "single_authority":
        return 1
    if policy == "unanimity":
        return slot_count
    return slot_count // 2 + 1


def _recommendation(value: str) -> DecisionRecommendation:
    return value if value in {"approve", "reject", "escalate"} else "escalate"  # type: ignore[return-value]


def _unique(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        s = str(value or "").strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def _card_ref(card: dict[str, Any]) -> str:
    if card.get("failure_family_sha"):
        return str(card["failure_family_sha"])
    if card.get("failure_family") is not None:
        return family_sha(card.get("failure_family"))
    return hashlib.sha256(json.dumps(card, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _card_batch_sha(cards: list[dict[str, Any]]) -> str:
    refs = [_card_ref(card) for card in cards]
    return hashlib.sha256(json.dumps(refs, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def _positions_sha(positions: list[StrategyDecisionPosition]) -> str:
    return hashlib.sha256(
        json.dumps([p.as_dict() for p in positions], sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:16]
