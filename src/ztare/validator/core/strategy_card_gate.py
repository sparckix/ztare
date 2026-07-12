from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ztare.common.operator_proposal_contract import record_disposition
from ztare.common.control_work_items import RunContext, should_block
from ztare.common.structured_blocks import balanced_object_after_marker
from ztare.common.strategy_card_roles import strategy_card_role


@dataclass(frozen=True)
class StrategyCardGateResult:
    ran: bool
    passed: bool
    message: str
    payload: dict[str, Any]


_VALID_OUTCOMES = {"satisfied", "refuted", "blocked"}
_EXTERNAL_ACTION_BLOCKER_KINDS = {"requires_external_actions", "requires_live_actions"}
_NO_ATTEMPT_BLOCKER_KINDS = {
    "missing_seed",
    "missing_evidence",
    "verifier_defect",
    "requires_external_actions",
    "requires_live_actions",
    "underdetermined_by_current_log",
}

def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _nonempty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value)


def _nonempty_next_action(value: Any) -> bool:
    if _nonempty_text(value):
        return True
    if isinstance(value, dict):
        return any(
            _nonempty_text(v) or _nonempty_list(v) or isinstance(v, dict)
            for v in value.values()
        )
    if isinstance(value, list):
        return bool(value)
    return False


def _card_requires_repair_discharge(card: dict[str, Any]) -> bool:
    kind = str(card.get("kind") or "").lower()
    plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
    return bool(
        "repair" in kind
        or plan.get("required_next_gate")
        or plan.get("repair_certificate")
    )


def _required_next_gate(card: dict[str, Any]) -> dict[str, Any]:
    plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
    gate = plan.get("required_next_gate") if isinstance(plan.get("required_next_gate"), dict) else {}
    return gate


def _no_attempt_blocker_is_admissible(blocker_kind: str, card: dict[str, Any]) -> bool:
    if blocker_kind not in _NO_ATTEMPT_BLOCKER_KINDS:
        return False
    if blocker_kind not in _EXTERNAL_ACTION_BLOCKER_KINDS:
        return True
    gate = _required_next_gate(card)
    return gate.get("spends_external_actions") is True


def admissible_no_attempt_blocker_kinds(card: dict[str, Any]) -> list[str]:
    """Return no-attempt blocker kinds admissible for this card's gate contract.

    This is property-based: callers must not infer action cost from command
    names, status strings, or substrate vocabulary.
    """
    preferred = [
        "missing_seed",
        "missing_evidence",
        "verifier_defect",
        "underdetermined_by_current_log",
        "requires_external_actions",
    ]
    return [kind for kind in preferred if _no_attempt_blocker_is_admissible(kind, card)]


def _load_open_strategy_cards(project_dir: Path) -> list[dict[str, Any]]:
    try:
        from ztare.common.operator_proposal_contract import open_cards

        return [
            card for card in open_cards(project_dir / "workspace" / "strategy_experiments.jsonl")
            if isinstance(card, dict)
        ]
    except Exception:  # noqa: BLE001
        return []


def _blocking_strategy_cards(
    cards: list[dict[str, Any]],
    *,
    context: RunContext | None = None,
) -> list[dict[str, Any]]:
    ctx = context or RunContext()
    return [card for card in cards if should_block(strategy_card_role(card), ctx)]


def _coerce_receipt(raw: str) -> dict[str, Any] | None:
    try:
        obj = json.loads(raw)
    except Exception:
        try:
            obj = ast.literal_eval(raw)
        except Exception:
            return None
    return obj if isinstance(obj, dict) else None


_STRATEGY_CARD_RECEIPT_MARKERS = (
    "STRATEGY_CARD_DISCHARGE",
    "STRATEGY_CARD_RECEIPT",
)


def _append_gate_receipt(project_dir: Path, row: dict[str, Any]) -> None:
    ledger = project_dir / "workspace" / "strategy_card_gate_receipts.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")


def extract_strategy_card_discharges(*texts: str) -> list[dict[str, Any]]:
    """Extract typed Strategy Office card receipts from candidate artifacts.

    The carrier is intentionally small and content-addressed:

    ``STRATEGY_CARD_DISCHARGE: {"failure_family_sha": "...", ...}``

    Markdown or Python may carry the same marker; this parser only accepts a
    balanced object after the marker and does not infer discharge from prose.
    ``STRATEGY_CARD_RECEIPT`` is accepted as a compatibility alias because the
    surrounding gate is named a receipt precheck.
    """

    receipts: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _append_receipt(obj: dict[str, Any]) -> None:
        receipt_type = str(obj.get("type") or "").strip()
        if receipt_type in _STRATEGY_CARD_RECEIPT_MARKERS and isinstance(obj.get("payload"), dict):
            rec = dict(obj["payload"])
        else:
            rec = obj
        try:
            key = json.dumps(rec, sort_keys=True, separators=(",", ":"))
        except TypeError:
            key = repr(sorted(rec.items()))
        if key in seen:
            return
        seen.add(key)
        receipts.append(rec)

    for text in texts:
        if not text:
            continue
        try:
            parsed = json.loads(text)
        except Exception:
            parsed = None
        if isinstance(parsed, dict):
            raw_receipts = parsed.get("control_receipts")
            if isinstance(raw_receipts, list):
                for row in raw_receipts:
                    if isinstance(row, dict):
                        _append_receipt(row)
        for marker in _STRATEGY_CARD_RECEIPT_MARKERS:
            for raw in balanced_object_after_marker(text, marker):
                receipt = _coerce_receipt(raw)
                if receipt is not None:
                    _append_receipt(receipt)
    return receipts


def _unparseable_discharges(*texts: str) -> list[str]:
    """Return raw marker payloads that failed to parse as receipt objects.

    A malformed discharge must not silently land in "missing": the author
    needs to see that their JSON was unparseable, not that it was absent.
    """
    raws: list[str] = []
    for text in texts:
        if not text:
            continue
        for marker in _STRATEGY_CARD_RECEIPT_MARKERS:
            for raw in balanced_object_after_marker(text, marker):
                if _coerce_receipt(raw) is None:
                    raws.append(raw)
    return raws


def _receipt_matches_card(receipt: dict[str, Any], card: dict[str, Any]) -> bool:
    sha = str(card.get("failure_family_sha") or "")
    family = str(card.get("failure_family") or "")
    refs = {
        str(receipt.get("failure_family_sha") or ""),
        str(receipt.get("card_sha") or ""),
        str(receipt.get("card_ref") or ""),
        str(receipt.get("failure_family") or ""),
    }
    return bool((sha and sha in refs) or (family and family in refs))


def _receipt_valid(
    receipt: dict[str, Any],
    card: dict[str, Any],
    *,
    semantic_status: bool,
) -> tuple[bool, str]:
    outcome = str(receipt.get("outcome") or receipt.get("status") or "").strip()
    if outcome not in _VALID_OUTCOMES:
        return False, "missing_or_invalid_outcome"
    evidence_refs = receipt.get("evidence_refs")
    new_evidence_refs = receipt.get("new_evidence_refs")
    has_evidence_refs = _nonempty_list(evidence_refs)
    has_blocked_new_evidence_refs = (
        outcome == "blocked" and _nonempty_list(new_evidence_refs)
    )
    if not has_evidence_refs and not has_blocked_new_evidence_refs:
        return False, "missing_evidence_refs"
    plan = card.get("action_plan") or {}
    required = (plan.get("required_next_gate") or {}).get("success_status")
    observed = str(receipt.get("observed_status") or receipt.get("next_gate_status") or "")
    if semantic_status and required and observed and observed != required:
        # A failed/refuted card may still be useful, but it must say what it
        # learned instead of pretending to have satisfied the planned gate.
        if outcome == "satisfied":
            return False, "satisfied_receipt_mismatches_required_gate"
    if semantic_status and required and outcome == "satisfied":
        if not observed:
            return False, "satisfied_receipt_missing_next_gate_status"
        if observed != required:
            return False, "satisfied_receipt_mismatches_required_gate"
    if outcome == "blocked" and _card_requires_repair_discharge(card):
        blocker_kind = str(receipt.get("blocker_kind") or "").strip()
        if not blocker_kind:
            return False, "blocked_repair_missing_blocker_kind"
        if not _nonempty_next_action(receipt.get("next_action")):
            return False, "blocked_repair_missing_next_action"
        if blocker_kind in _NO_ATTEMPT_BLOCKER_KINDS:
            if not _no_attempt_blocker_is_admissible(blocker_kind, card):
                return False, f"blocked_repair_{blocker_kind}_not_supported_by_required_gate"
            return True, ""
        if (
            _nonempty_text(receipt.get("attempted_repair"))
            or _nonempty_text(receipt.get("attempted_probe"))
            or _nonempty_list(receipt.get("new_evidence_refs"))
        ):
            return True, ""
        return False, "blocked_repair_missing_attempt_or_new_evidence"
    return True, ""


def evaluate_strategy_card_gate(
    *,
    project_dir: str | Path,
    thesis_text: str,
    candidate_source: str = "",
    semantic_status: bool = True,
    run_context: RunContext | None = None,
) -> StrategyCardGateResult:
    project = Path(project_dir)
    all_cards = _load_open_strategy_cards(project)
    context = run_context or RunContext()
    cards = _blocking_strategy_cards(all_cards, context=context)
    if not cards:
        receipt = {
            "site": "strategy_card_gate.py:104",
            "fallback_taken": "no_blocking_cards",
            "cause": "open cards were non-blocking for the current lane",
            "run_lane": context.lane,
            "open_cards": len(all_cards),
        }
        _append_gate_receipt(project, receipt)
        return StrategyCardGateResult(
            ran=False,
            passed=False,
            message=f"no blocking strategy cards for {context.lane}",
            payload={
                "schema": "strategy-card-gate-v1",
                "open_cards": 0,
                "all_open_cards": len(all_cards),
                "run_lane": context.lane,
                "verdict": "no_blocking_cards",
                "control_receipt": receipt,
                "nonblocking_cards": [
                    {
                        "failure_family_sha": str(card.get("failure_family_sha") or ""),
                        "kind": str(card.get("kind") or ""),
                        "role": strategy_card_role(card).to_dict(),
                    }
                    for card in all_cards
                    if card not in cards
                ],
            },
        )

    receipts = extract_strategy_card_discharges(thesis_text, candidate_source)
    missing: list[dict[str, str]] = []
    invalid: list[dict[str, str]] = []
    for raw in _unparseable_discharges(thesis_text, candidate_source):
        invalid.append({
            "reason": "unparseable_receipt",
            "raw_prefix": raw[:120],
        })
    for card in cards:
        matches = [receipt for receipt in receipts if _receipt_matches_card(receipt, card)]
        if not matches:
            missing.append({
                "failure_family_sha": str(card.get("failure_family_sha") or ""),
                "kind": str(card.get("kind") or ""),
            })
            continue
        valid = False
        reasons: list[str] = []
        for receipt in matches:
            ok, reason = _receipt_valid(
                receipt,
                card,
                semantic_status=semantic_status,
            )
            valid = valid or ok
            if reason:
                reasons.append(reason)
        if not valid:
            invalid.append({
                "failure_family_sha": str(card.get("failure_family_sha") or ""),
                "kind": str(card.get("kind") or ""),
                "reason": ",".join(reasons) or "invalid_receipt",
            })

    passed = not missing and not invalid
    payload = {
        "schema": "strategy-card-gate-v1",
        "open_cards": len(cards),
        "all_open_cards": len(all_cards),
        "run_lane": context.lane,
        "nonblocking_cards": [
            {
                "failure_family_sha": str(card.get("failure_family_sha") or ""),
                "kind": str(card.get("kind") or ""),
                "role": strategy_card_role(card).to_dict(),
            }
            for card in all_cards
            if card not in cards
        ],
        "receipts": receipts,
        "missing": missing,
        "invalid": invalid,
        "passed": passed,
    }
    if passed:
        return StrategyCardGateResult(
            ran=True,
            passed=True,
            message=f"strategy card discharge gate passed ({len(cards)} card(s))",
            payload=payload,
        )
    return StrategyCardGateResult(
        ran=True,
        passed=False,
        message=(
            "strategy card discharge gate failed: "
            f"missing={len(missing)} invalid={len(invalid)}"
        ),
        payload=payload,
    )


def has_valid_blocked_strategy_card_discharge(
    *,
    project_dir: str | Path,
    thesis_text: str,
    candidate_source: str = "",
    semantic_status: bool = False,
) -> bool:
    """Return true when all blocking Strategy cards are validly blocked.

    This is a routing outcome, not candidate credit. It lets the mutation loop
    hand control to evidence acquisition / next-action routing without forcing
    the worker to invent a non-improving executable carrier.
    """
    project = Path(project_dir)
    cards = _blocking_strategy_cards(_load_open_strategy_cards(project), context=RunContext())
    if not cards:
        return False
    receipts = extract_strategy_card_discharges(thesis_text, candidate_source)
    for card in cards:
        matches = [receipt for receipt in receipts if _receipt_matches_card(receipt, card)]
        valid_blocked = False
        for receipt in matches:
            outcome = str(receipt.get("outcome") or receipt.get("status") or "").strip()
            if outcome != "blocked":
                continue
            ok, _reason = _receipt_valid(
                receipt,
                card,
                semantic_status=semantic_status,
            )
            valid_blocked = valid_blocked or ok
        if not valid_blocked:
            return False
    return True


def persist_strategy_card_discharges(
    *,
    project_dir: str | Path,
    thesis_text: str,
    candidate_source: str = "",
    semantic_status: bool = False,
) -> list[dict[str, Any]]:
    """Persist valid Strategy-card discharge receipts into the Strategy ledger.

    Control-only worldmodel submissions can contain useful routing evidence.
    Persisting a validated discharge prevents the next worker from rediscovering
    the same obligation, while still granting no candidate score or promotion.
    """

    project = Path(project_dir)
    ledger = project / "workspace" / "strategy_experiments.jsonl"
    cards = _load_open_strategy_cards(project)
    receipts = extract_strategy_card_discharges(thesis_text, candidate_source)
    written: list[dict[str, Any]] = []
    for card in cards:
        for receipt in receipts:
            if not _receipt_matches_card(receipt, card):
                continue
            ok, reason = _receipt_valid(
                receipt,
                card,
                semantic_status=semantic_status,
            )
            if not ok:
                continue
            outcome = str(receipt.get("outcome") or receipt.get("status") or "").strip()
            disposition = {
                "satisfied": "accepted",
                "refuted": "rejected",
                "blocked": "blocked",
            }.get(outcome)
            if not disposition:
                continue
            row = dict(card)
            row["disposition"] = disposition
            row["receipt"] = dict(receipt)
            row["disposition_authority"] = "strategy_card_discharge_receipt"
            if reason:
                row["disposition_reason"] = reason
            written.append(record_disposition(ledger, row))
            break
    return written


def blocked_eval_from_strategy_card_gate(result: StrategyCardGateResult) -> dict[str, Any]:
    if result.payload.get("verdict") == "no_blocking_cards":
        raise RuntimeError("strategy card gate returned a typed no_blocking_cards verdict; caller must branch")
    return {
        "score": 0,
        "weakest_point": (
            "STRATEGY_CARD_GATE: candidate ignored or malformed a blocking "
            "skill-acquisition Strategy Office work order before judge review. "
            f"{result.message}"
        ),
        "verified_axioms": [],
        "retired_axioms_approved": [],
        "evidence_gaps": [],
        "derived_constraints": [],
        "logic_gaps": [
            "Blocking skill-acquisition Strategy Office cards must be discharged "
            "by a typed receipt before judge evaluation."
        ],
        "debate_summary": (
            "Pre-judge Strategy Office gate blocked evaluation to prevent "
            "silent prompt-level drift from consuming judge cycles."
        ),
        "adversarial_alignment": "",
        "friction_points": [],
        "probability_dag": {
            "outcome": {
                "label": "strategy_card_not_discharged",
                "probability": 0.0,
            },
            "nodes": [],
            "edges": [],
        },
        "strategy_card_gate_fired": True,
        "strategy_card_gate_payload": result.payload,
        "score_cap_reason": "strategy_card_not_discharged",
    }
