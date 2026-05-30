"""Event-family binding gate.

General-purpose receipt check for arguments that transfer a payment, measure,
or estimate from one event family to another.  It forces the caller to say that
the target events and source events are the same family before payoff, on the
same carrier/owner, with no proxy or deficit-selected event substitution.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-EVENT-FAMILY-BINDING"

IDENTITY_REQUIRED_FIELDS = (
    "target_event_family",
    "source_event_family",
    "event_identity",
    "pre_payoff_timing",
    "same_carrier",
    "same_owner_or_source",
    "index_map",
    "index_map_total_on_prefix",
    "no_proxy_family",
    "no_post_payoff_selection",
)

DOMINATED_INJECTION_REQUIRED_FIELDS = (
    "target_event_family",
    "source_event_family",
    "dominating_event_injection",
    "domination_inequality",
    "error_or_loss_budget",
    "pre_payoff_timing",
    "same_carrier",
    "same_owner_or_source",
    "index_map",
    "index_map_total_on_prefix",
    "no_proxy_family",
    "no_post_payoff_selection",
)

REQUIRED_FIELDS = IDENTITY_REQUIRED_FIELDS
RELATION_REQUIRED_FIELDS = {
    "identity": IDENTITY_REQUIRED_FIELDS,
    "dominated_injection": DOMINATED_INJECTION_REQUIRED_FIELDS,
}

WEAK_SUBSTITUTES = (
    "same_vocabulary",
    "same_label",
    "same_threshold_name",
    "both_local",
    "both_finite_prefix",
    "owner_label_only",
)


def _present(value: Any) -> bool:
    if isinstance(value, str):
        text = value.strip()
        lowered = text.lower()
        if not text:
            return False
        false_exact_matches = {
            "missing",
            "absent",
            "unknown",
            "todo",
            "owed",
            "unpaid",
            "not supplied",
            "not provided",
            "none",
            "null",
            "false",
            "0",
        }
        return lowered not in false_exact_matches
    return value not in (None, "", [], {}, False)


def run_event_family_binding_gate(
    receipt: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
) -> dict[str, Any]:
    """Validate a source/target event-family binding receipt.

    The gate does not prove event identity. It catches the common false proof
    move where a source theorem on one carrier is consumed by a target event
    family with matching vocabulary but no pre-payoff identity map.
    """
    receipt = receipt or {}
    violations: list[dict[str, Any]] = []

    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": not enforce_block,
            "blocking_active": enforce_block,
            "violations": [{
                "type": "event_family_binding_receipt_malformed",
                "severity": "blocking" if enforce_block else "advisory",
                "reason": "receipt must be a JSON object",
            }],
            "required_fields": list(REQUIRED_FIELDS),
            "summary": "malformed receipt",
        }

    relation_type = str(receipt.get("relation_type") or "identity").strip().lower().replace("-", "_")
    required_fields = RELATION_REQUIRED_FIELDS.get(relation_type, IDENTITY_REQUIRED_FIELDS)
    missing = [field for field in required_fields if not _present(receipt.get(field))]
    if relation_type not in RELATION_REQUIRED_FIELDS:
        violations.append({
            "type": "event_family_binding_unknown_relation_type",
            "severity": "blocking" if enforce_block else "advisory",
            "relation_type": relation_type,
            "reason": "relation_type must be identity or dominated_injection",
        })
    if missing:
        violations.append({
            "type": "event_family_binding_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": (
                "event-family transfer needs explicit source/target family, "
                "the selected relation receipt, pre-payoff timing, same "
                "carrier/source, total prefix index map, and no-proxy/no-post-payoff receipts"
            ),
        })

    weak_present = [
        field for field in WEAK_SUBSTITUTES if _present(receipt.get(field))
    ]
    if weak_present and missing:
        violations.append({
            "type": "event_family_binding_replaced_by_weak_substitutes",
            "severity": "blocking" if enforce_block else "advisory",
            "weak_substitutes": weak_present,
            "reason": (
                "shared labels, local vocabulary, finite-prefix shape, or owner "
                "labels do not substitute for event-family identity"
            ),
        })

    if _present(receipt.get("known_proxy_family_confuser")):
        violations.append({
            "type": "event_family_binding_proxy_confuser_declared",
            "severity": "blocking" if enforce_block else "advisory",
            "confuser": receipt.get("known_proxy_family_confuser"),
            "reason": "caller declared a proxy-family confuser for this transfer",
        })

    blocking = [v for v in violations if v.get("severity") == "blocking"]
    passed = not blocking if enforce_block else True

    complete = not missing and not any(
        v["type"] == "event_family_binding_proxy_confuser_declared"
        for v in violations
    )
    return {
        "gate_id": GATE_ID,
        "passed": passed,
        "complete": complete,
        "blocking_active": enforce_block,
        "violations": violations,
        "missing_fields": missing,
        "weak_substitutes_present": weak_present,
        "relation_type": relation_type,
        "required_fields": list(required_fields),
        "summary": (
            f"complete event-family binding receipt ({relation_type})"
            if complete else
            f"incomplete event-family binding receipt; missing {len(missing)} field(s)"
        ),
    }


def _self_test() -> None:
    weak = run_event_family_binding_gate({
        "target_event_family": "H-prefix",
        "source_event_family": "LEI tents",
        "same_label": "local high-interface events",
    })
    assert weak["complete"] is False
    assert any(v["type"] == "event_family_binding_receipt_incomplete"
               for v in weak["violations"])

    strong = run_event_family_binding_gate({
        "target_event_family": "H-prefix",
        "source_event_family": "LEI tents",
        "event_identity": "H_event n = LEI_event n for n<N",
        "pre_payoff_timing": "event map fixed before payoff",
        "same_carrier": "same local-energy carrier",
        "same_owner_or_source": "same owner-root prefix",
        "index_map": "n ↦ n",
        "index_map_total_on_prefix": "all n<N covered",
        "no_proxy_family": "not a threshold proxy",
        "no_post_payoff_selection": "H fixed before target deficit",
    })
    assert strong["complete"] is True
    assert strong["passed"] is True


if __name__ == "__main__":
    _self_test()
