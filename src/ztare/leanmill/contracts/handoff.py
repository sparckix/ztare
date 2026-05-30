"""LeanMill agentic handoff contract helpers.

Agents may generate source requests, family-spec patches, or binding artifacts.
They do not create value. A terminal generation row must either point to the
next deterministic station or explain why no such handoff is possible.
"""
from __future__ import annotations

from typing import Any


POLICY_SCHEMA = "leanmill-agentic-handoff-contract-policy-v1"
READ_MODEL_SCHEMA = "leanmill-agentic-handoff-contract-read-model-v1"
REPAIR_SELECTION_SCHEMA = "leanmill-agentic-handoff-repair-selection-v1"
REPAIR_RECEIPT_SCHEMA = "leanmill-agentic-handoff-repair-receipt-v1"

CREDIT_BOUNDARY = (
    "Handoff receipts are routing integrity evidence only. They do not create "
    "proof credit, benchmark lift, governance pass, or C credit-ready status."
)

DEFAULT_FAMILY_SPEC_PATCH_ACTIVATION_RECEIPTS = {
    "family_birth_candidate": "family_birth_activation",
    "family_spec_positive_repair": "family_spec_positive_repair_activation",
    "c_supply_template_backfill": "family_spec_positive_repair_activation",
}

DEFAULT_TERMINAL_EXISTING_SKIP_KEYS = (
    "terminal_exact_work_id_done",
    "terminal_exact_work_id_failed",
    "terminal_exact_work_id_retired",
    "terminal_exact_work_id_dead_letter",
)

DEFAULT_SOURCE_SEARCH_READY_SUMMARY_KEYS = (
    "ready_total",
    "canary_ready_total",
    "source_canary_ready_candidates",
)

AGENTIC_FAMILY_SPEC_PATCH_KINDS = (
    "agent_repair_task",
    "subscription_agent_task",
    "agent_task",
    "agent_repair",
)


def int_count(obj: dict[str, Any], key: str) -> int:
    try:
        return int(obj.get(key) or 0)
    except (TypeError, ValueError):
        return 0


def policy_from_factory_policy(factory_policy: dict[str, Any] | None) -> dict[str, Any]:
    operations = factory_policy.get("operations") if isinstance(factory_policy, dict) and isinstance(factory_policy.get("operations"), dict) else {}
    policy = operations.get("agentic_handoff_contract_policy") if isinstance(operations.get("agentic_handoff_contract_policy"), dict) else {}
    receipts = policy.get("family_spec_patch_activation_receipts") if isinstance(policy.get("family_spec_patch_activation_receipts"), dict) else {}
    return {
        "schema": str(policy.get("schema") or POLICY_SCHEMA),
        "rule": str(
            policy.get("rule")
            or "terminal agentic generation must hand off to deterministic verification/governance or emit a visible blocked receipt"
        ),
        "family_spec_patch_activation_receipts": {
            **DEFAULT_FAMILY_SPEC_PATCH_ACTIVATION_RECEIPTS,
            **{str(k): str(v) for k, v in receipts.items() if str(k) and str(v)},
        },
        "terminal_existing_skip_keys": [
            str(x) for x in (policy.get("terminal_existing_skip_keys") or DEFAULT_TERMINAL_EXISTING_SKIP_KEYS) if str(x)
        ],
        "source_search_ready_summary_keys": [
            str(x) for x in (policy.get("source_search_ready_summary_keys") or DEFAULT_SOURCE_SEARCH_READY_SUMMARY_KEYS) if str(x)
        ],
        "recommendation_class": str(policy.get("recommendation_class") or "agentic_handoff_contract_leakage"),
        "credit_boundary": str(policy.get("credit_boundary") or CREDIT_BOUNDARY),
        "rationale": str(policy.get("rationale") or ""),
    }


def receipt_field_for_mode(mode: str, policy: dict[str, Any] | None = None) -> str:
    receipts = (
        policy.get("family_spec_patch_activation_receipts")
        if isinstance(policy, dict) and isinstance(policy.get("family_spec_patch_activation_receipts"), dict)
        else DEFAULT_FAMILY_SPEC_PATCH_ACTIVATION_RECEIPTS
    )
    return str(receipts.get(str(mode) or "") or "agentic_handoff_repair")


def has_existing_terminal_skip(receipt: dict[str, Any], skip_keys: list[str] | tuple[str, ...] | None = None) -> bool:
    skip_counts = receipt.get("skip_counts") if isinstance(receipt.get("skip_counts"), dict) else {}
    keys = skip_keys or DEFAULT_TERMINAL_EXISTING_SKIP_KEYS
    return any(int_count(skip_counts, key) > 0 for key in keys)


def classify_family_spec_receipt(
    receipt: dict[str, Any],
    *,
    skip_keys: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    if not isinstance(receipt, dict) or not receipt:
        return {"class": "missing_receipt", "hard_leak": True, "blocked": False, "verified": False}
    status = str(receipt.get("status") or "unknown")
    enqueued = int_count(receipt, "enqueued")
    job_count = int_count(receipt, "job_count")
    selected_count = int_count(receipt, "selected_row_count")
    if status == "pass" and (enqueued > 0 or job_count > 0 or has_existing_terminal_skip(receipt, skip_keys)):
        return {
            "class": "verified_or_existing_terminal",
            "hard_leak": False,
            "blocked": False,
            "verified": True,
            "status": status,
            "enqueued": enqueued,
            "job_count": job_count,
            "selected_row_count": selected_count,
        }
    if status in {"skipped", "fail"} or str(receipt.get("reason") or ""):
        return {
            "class": f"blocked_{status}",
            "hard_leak": False,
            "blocked": True,
            "verified": False,
            "status": status,
            "reason": str(receipt.get("reason") or ""),
            "enqueued": enqueued,
            "job_count": job_count,
            "selected_row_count": selected_count,
        }
    return {
        "class": "zero_handoff_without_blocker",
        "hard_leak": True,
        "blocked": False,
        "verified": False,
        "status": status,
        "enqueued": enqueued,
        "job_count": job_count,
        "selected_row_count": selected_count,
    }


def source_search_ready_total(payload: dict[str, Any], ready_keys: list[str] | tuple[str, ...] | None = None) -> int:
    summary = payload.get("source_search_summary") if isinstance(payload.get("source_search_summary"), dict) else {}
    out = 0
    for key in ready_keys or DEFAULT_SOURCE_SEARCH_READY_SUMMARY_KEYS:
        out = max(out, int_count(summary, key), int_count(payload, key))
    return out


def accepted_family_spec_patch_mode(*, kind: str, status: str, payload: dict[str, Any]) -> str:
    if str(kind) not in AGENTIC_FAMILY_SPEC_PATCH_KINDS:
        return ""
    if str(status) != "done":
        return ""
    if str(payload.get("expected_exit") or "") != "family_spec_patch":
        return ""
    receipt = payload.get("family_spec_patch_receipt") if isinstance(payload.get("family_spec_patch_receipt"), dict) else {}
    if str(receipt.get("status") or "") != "pass":
        return ""
    return str(payload.get("family_spec_patch_mode") or "")


def required_receipt_field_for_terminal_family_spec_patch(
    *,
    kind: str,
    status: str,
    payload: dict[str, Any],
    policy: dict[str, Any] | None = None,
) -> str:
    mode = accepted_family_spec_patch_mode(kind=kind, status=status, payload=payload)
    if not mode:
        return ""
    return receipt_field_for_mode(mode, policy)


def terminal_missing_handoff_receipt(
    *,
    kind: str,
    status: str,
    payload: dict[str, Any],
    policy: dict[str, Any] | None = None,
) -> bool:
    receipt_field = required_receipt_field_for_terminal_family_spec_patch(
        kind=kind,
        status=status,
        payload=payload,
        policy=policy,
    )
    return bool(receipt_field and not isinstance(payload.get(receipt_field), dict))


def ensure_terminal_handoff_receipt(
    *,
    kind: str,
    status: str,
    payload: dict[str, Any],
    policy: dict[str, Any] | None = None,
) -> bool:
    """Stamp a visible blocked receipt when terminal agentic work lacks handoff.

    This is a routing-integrity fail-closed default. It does not enqueue work
    and does not create credit; it prevents accepted generation from becoming
    invisible terminal state.
    """
    mode = accepted_family_spec_patch_mode(kind=kind, status=status, payload=payload)
    if not mode:
        return False
    receipt_field = receipt_field_for_mode(mode, policy)
    if isinstance(payload.get(receipt_field), dict):
        return False
    work_id = str(payload.get("work_id") or "")
    family = str(payload.get("family") or payload.get("repair_family") or "")
    receipt = {
        "schema": REPAIR_RECEIPT_SCHEMA,
        "status": "skipped",
        "reason": "terminal_agentic_patch_missing_downstream_handoff_at_queue_boundary",
        "work_id": work_id,
        "source_work_id": work_id,
        "family": family,
        "family_spec_patch_mode": mode,
        "selected_row_count": 0,
        "enqueued": 0,
        "job_count": 0,
        "credit_boundary": CREDIT_BOUNDARY,
    }
    payload[receipt_field] = receipt
    payload["agentic_handoff_boundary_receipt"] = receipt
    return True


def credit_boundary() -> str:
    return CREDIT_BOUNDARY


def _self_test() -> int:
    policy = policy_from_factory_policy({"operations": {"agentic_handoff_contract_policy": {"recommendation_class": "x"}}})
    assert policy["recommendation_class"] == "x", policy
    assert receipt_field_for_mode("c_supply_template_backfill", policy) == "family_spec_positive_repair_activation"
    assert classify_family_spec_receipt({})["hard_leak"] is True
    assert classify_family_spec_receipt({"status": "pass", "skip_counts": {"terminal_exact_work_id_done": 1}})["verified"] is True
    assert classify_family_spec_receipt({"status": "skipped", "reason": "no_pair"})["blocked"] is True
    assert source_search_ready_total({"source_search_summary": {"ready_total": 3}}) == 3
    payload = {
        "work_id": "w",
        "expected_exit": "family_spec_patch",
        "family_spec_patch_mode": "family_spec_positive_repair",
        "family_spec_patch_receipt": {"status": "pass"},
    }
    assert ensure_terminal_handoff_receipt(kind="agent_repair_task", status="done", payload=payload, policy=policy) is True
    assert payload["family_spec_positive_repair_activation"]["reason"] == "terminal_agentic_patch_missing_downstream_handoff_at_queue_boundary"
    print("ztare.leanmill.contracts.handoff self-test PASS")
    return 0


__all__ = [
    "CREDIT_BOUNDARY",
    "AGENTIC_FAMILY_SPEC_PATCH_KINDS",
    "POLICY_SCHEMA",
    "READ_MODEL_SCHEMA",
    "REPAIR_RECEIPT_SCHEMA",
    "REPAIR_SELECTION_SCHEMA",
    "accepted_family_spec_patch_mode",
    "classify_family_spec_receipt",
    "credit_boundary",
    "ensure_terminal_handoff_receipt",
    "has_existing_terminal_skip",
    "int_count",
    "policy_from_factory_policy",
    "receipt_field_for_mode",
    "required_receipt_field_for_terminal_family_spec_patch",
    "source_search_ready_total",
    "terminal_missing_handoff_receipt",
]


if __name__ == "__main__":
    raise SystemExit(_self_test())
