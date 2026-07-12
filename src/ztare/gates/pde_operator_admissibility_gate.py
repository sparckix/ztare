"""G-PDE-OPERATOR-ADMISSIBILITY -- singular-integral operator payment gate.

This gate checks whether a PDE receipt has paid the operator-admissibility
obligations behind CZ/Riesz/Fourier-multiplier claims.  It does not prove a
bound; it rejects common substitutions where an unlocalized operator estimate,
signed moment, or unpaid cutoff leakage is used as if it were a same-carrier
localized payment.
"""
from __future__ import annotations

from typing import Any

try:  # pragma: no cover - direct script execution
    from ztare.gates.required_field_semantics import is_semantically_present
except ModuleNotFoundError:  # pragma: no cover
    from required_field_semantics import is_semantically_present


GATE_ID = "G-PDE-OPERATOR-ADMISSIBILITY"

REQUIRED_FIELDS = (
    "operator_family",
    "kernel_or_multiplier_model",
    "input_output_norms",
    "scale_or_bandlimit",
    "localization_or_cutoff",
    "carrier_identity",
    "endpoint_handling",
    "commutator_or_tail_payment",
    "currency_target",
    "hostile_packet_or_counterexample",
)

CANARY_FIELD_ALIASES = {
    "operator": ("operator", "operator_family"),
    "kernel_or_multiplier": ("kernel_or_multiplier", "kernel_or_multiplier_model"),
    "carrier": ("carrier", "carrier_identity"),
    "bandlimit": ("bandlimit", "scale_or_bandlimit"),
    "support_identity": ("support_identity", "carrier_identity", "localization_or_cutoff"),
    "endpoint": ("endpoint", "endpoint_handling"),
    "cutoff_commutator": ("cutoff_commutator", "commutator_or_tail_payment"),
    "low_high_leakage": ("low_high_leakage", "commutator_or_tail_payment"),
    "projection_target_identity": (
        "projection_target_identity",
        "currency_target",
        "input_output_norms",
    ),
    "same_stream_binding": ("same_stream_binding", "carrier_identity"),
    "hostile_packets": ("hostile_packets", "hostile_packet_or_counterexample"),
}

REJECTED_SUBSTITUTES = (
    "raw_global_CZ_bound",
    "raw_unlocalized_Riesz_measure_target",
    "signed_moment_as_total_variation",
    "post_projection_leakage_unpaid",
    "cutoff_commutator_tail_unpaid",
    "proxy_carrier_operator_bound",
    "bandlimit_chosen_after_payoff",
    "endpoint_asserted_by_label",
    "Besov_BV_or_CF_import_without_exchange",
)

OPERATOR_MARKERS = (
    "calderon",
    "cz",
    "riesz",
    "leray",
    "fourier",
    "multiplier",
    "singular integral",
    "kernel",
    "commutator",
    "projection",
    "annular",
    "bandlimit",
)

CANARY_NEXT_WORK_UNITS = (
    {
        "leaf_id": "pde.leaf.pec_l.uniform_annular_riesz_l1",
        "target": "uniform_annular_riesz_l1_on_fixed_bandlimited_annular_carrier",
        "op_id": "pec_l",
        "goal": "prove or falsify uniform annular Riesz/Leray/CZ L1 admissibility on the fixed pre-payoff annular carrier",
        "work_unit_type": "estimate_derivation",
        "required_gate_ids": [
            "G-PDE-OPERATOR-ADMISSIBILITY",
            "G-PDE-HOSTILE-WITNESS",
        ],
        "must_return": {
            "target_inequality_or_statement": "uniform annular operator L1/endpoint statement",
            "proof_steps": "annular kernel/multiplier localization, fixed bandlimit, endpoint handling",
            "first_failed_line_or_success": "exact missing operator payment or proof step",
            "hostile_packet_tested": "raw_CZ_L1_laundering",
            "currency_exchange_used": "localized operator norm to same-carrier tracefree variation",
            "verdict": "CLOSE | FAIL | SHRINK | NEED_THEOREM",
        },
    },
    {
        "leaf_id": "pde.leaf.pec_l.psd_trace_projection_payment",
        "target": "psd_trace_to_projected_tracefree_payment",
        "op_id": "pec_l",
        "goal": "prove or falsify that PSD trace currency pays the projected tracefree annular packet after projection",
        "work_unit_type": "estimate_derivation",
        "required_gate_ids": [
            "G-PDE-OPERATOR-ADMISSIBILITY",
            "G-POSITIVE-VARIATION-BRIDGE",
        ],
        "must_return": {
            "target_inequality_or_statement": "PSD trace payment implies projected tracefree packet payment",
            "proof_steps": "preprojection identity, Leray/Riesz projection payment, positivity preservation or loss accounting",
            "first_failed_line_or_success": "first projection/currency exchange that fails",
            "hostile_packet_tested": "signed_moment_as_total_variation",
            "currency_exchange_used": "psd_defect_trace_to_projected_tracefree_payment",
            "verdict": "CLOSE | FAIL | SHRINK | NEED_THEOREM",
        },
    },
    {
        "leaf_id": "pde.leaf.pec_l.cutoff_commutator_tail_payment",
        "target": "cutoff_commutator_tail_payment_on_same_stream",
        "op_id": "pec_l",
        "goal": "prove or falsify that cutoff and low-high commutator tails are paid on the selected stream",
        "work_unit_type": "estimate_derivation",
        "required_gate_ids": [
            "G-PDE-OPERATOR-ADMISSIBILITY",
            "G-PDE-HOSTILE-WITNESS",
        ],
        "must_return": {
            "target_inequality_or_statement": "cutoff commutator and low-high leakage are paid or excluded",
            "proof_steps": "localization, tail decomposition, same-stream tail invoice",
            "first_failed_line_or_success": "first unpaid cutoff/low-high term",
            "hostile_packet_tested": "low_high_projection_leak",
            "currency_exchange_used": "commutator_tail_to_selected_stream_payment",
            "verdict": "CLOSE | FAIL | SHRINK | NEED_THEOREM",
        },
    },
    {
        "leaf_id": "pde.leaf.pec_j.selected_owner_prefix_no_reuse_budget",
        "target": "selected_psd_owner_prefix_no_reuse_budget",
        "op_id": "pec_j",
        "goal": "prove or falsify selected owner-prefix no-reuse budget for PSD projected invoices",
        "work_unit_type": "positive_constructor_attempt",
        "required_gate_ids": [
            "G-SAME-CARRIER-PACKING",
            "G-NO-REBILLING-FRESHNESS",
            "G-OWNER-PREIMAGE-PREFIX",
        ],
        "must_return": {
            "target_inequality_or_statement": "selected owner-prefix all-prefix no-reuse bound",
            "proof_steps": "owner map, multiplicity/no-reuse, finite prefix budget",
            "first_failed_line_or_success": "first owner-prefix or no-rebilling field that fails",
            "hostile_packet_tested": "one_trace_packet_many_invoices",
            "currency_exchange_used": "same-carrier no-reuse to owner-prefix budget",
            "verdict": "CLOSE | FAIL | SHRINK | NEED_THEOREM",
        },
    },
    {
        "leaf_id": "pde.leaf.pec_i.nonadaptive_annular_event_stream_identity",
        "target": "nonadaptive_annular_event_stream_identity",
        "op_id": "pec_i",
        "goal": "prove or falsify that the annular projected packet is bound to the pre-payoff event stream",
        "work_unit_type": "positive_constructor_attempt",
        "required_gate_ids": [
            "G-NONADAPTIVE-SOURCE-SELECTION",
            "G-PDE-HOSTILE-WITNESS",
        ],
        "must_return": {
            "target_inequality_or_statement": "selected annular event stream equals the projected packet stream before payoff",
            "proof_steps": "source selection, event-stream identity, anti-postselection",
            "first_failed_line_or_success": "first source identity/postselection field that fails",
            "hostile_packet_tested": "post_selected_annular_packet",
            "currency_exchange_used": "source identity to operator/payment target",
            "verdict": "CLOSE | FAIL | SHRINK | NEED_THEOREM",
        },
    },
)


def _present(value: Any, *, field: str | None = None) -> bool:
    return is_semantically_present(value, field=field)


def _blob(receipt: dict[str, Any]) -> str:
    values: list[str] = []
    for value in receipt.values():
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, (list, tuple)):
            values.extend(str(item) for item in value)
        elif isinstance(value, dict):
            values.extend(str(item) for item in value.values())
    return " ".join(values).lower()


def _canonical_missing(receipt: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for canonical, aliases in CANARY_FIELD_ALIASES.items():
        if not any(_present(receipt.get(alias), field=alias) for alias in aliases):
            missing.append(canonical)
    return missing


def _canary_next_work_units(
    *,
    missing_fields: list[str],
    canonical_missing_fields: list[str],
    rejected_substitutes: list[str],
    text: str,
) -> list[dict[str, Any]]:
    if not (missing_fields or canonical_missing_fields or rejected_substitutes):
        return []
    markers = ("riesz", "leray", "cz", "calderon", "annular", "psd", "projection")
    if not any(marker in text for marker in markers):
        return []
    reason = {
        "missing_fields": missing_fields,
        "canonical_missing_fields": canonical_missing_fields,
        "rejected_substitutes": rejected_substitutes,
    }
    missing_set = set(missing_fields) | set(canonical_missing_fields)
    rejected_set = set(rejected_substitutes)
    selected_targets: set[str] = set()
    if (
        {"operator", "kernel_or_multiplier", "bandlimit", "endpoint"}
        & missing_set
        or {
            "raw_global_CZ_bound",
            "raw_unlocalized_Riesz_measure_target",
            "endpoint_asserted_by_label",
            "bandlimit_chosen_after_payoff",
        }
        & rejected_set
    ):
        selected_targets.add("uniform_annular_riesz_l1_on_fixed_bandlimited_annular_carrier")
    if (
        {"projection_target_identity", "input_output_norms"}
        & missing_set
        or {
            "signed_moment_as_total_variation",
            "post_projection_leakage_unpaid",
            "Besov_BV_or_CF_import_without_exchange",
        }
        & rejected_set
    ):
        selected_targets.add("psd_trace_to_projected_tracefree_payment")
    if (
        {"cutoff_commutator", "low_high_leakage"}
        & missing_set
        or {"cutoff_commutator_tail_unpaid"} & rejected_set
    ):
        selected_targets.add("cutoff_commutator_tail_payment_on_same_stream")
    if "one_trace_packet_many_invoices" in text:
        selected_targets.add("selected_psd_owner_prefix_no_reuse_budget")
    if missing_fields and (
        "raw_global_CZ_bound" in rejected_set
        or "raw global" in text
        or "raw cz" in text
    ):
        selected_targets.add("selected_psd_owner_prefix_no_reuse_budget")
    if (
        {"carrier", "support_identity", "same_stream_binding"}
        & missing_set
        or {"proxy_carrier_operator_bound"} & rejected_set
        or "post_selected_annular_packet" in text
    ):
        selected_targets.add("nonadaptive_annular_event_stream_identity")
    if not selected_targets:
        selected_targets = {str(unit["target"]) for unit in CANARY_NEXT_WORK_UNITS}
    return [
        {
            "schema": "pde-next-required-work-unit-v1",
            "gate_id": GATE_ID,
            "action": "dispatch_canary_leaf",
            "profile": "annular_bandlimited_riesz_l1_psd_trace_payment",
            "blocked_by": reason,
            **unit,
        }
        for unit in CANARY_NEXT_WORK_UNITS
        if str(unit.get("target")) in selected_targets
    ]


def run_pde_operator_admissibility_gate(receipt: dict[str, Any]) -> dict[str, Any]:
    """Validate operator-admissibility fields for a PDE estimate receipt."""
    missing = [
        field for field in REQUIRED_FIELDS
        if not _present(receipt.get(field), field=field)
    ]
    rejected = [
        field for field in REJECTED_SUBSTITUTES
        if _present(receipt.get(field), field=field)
    ]
    text = _blob(receipt)
    markers = [marker for marker in OPERATOR_MARKERS if marker in text]
    canonical_missing = _canonical_missing(receipt)
    violations: list[dict[str, Any]] = []
    if missing:
        violations.append({
            "type": "operator_admissibility_missing",
            "missing_fields": missing,
            "reason": (
                "operator claims require a concrete operator/kernel model, "
                "mapping norms, scale/bandlimit, localization, same-carrier "
                "identity, endpoint handling, tail payment, target currency, "
                "and hostile-packet boundary"
            ),
        })
    if rejected:
        violations.append({
            "type": "operator_substitute_rejected",
            "rejected_substitutes": rejected,
            "reason": (
                "raw global CZ/Riesz labels, signed moments, unpaid leakage, "
                "proxy carriers, and post-payoff bandlimits do not pay the "
                "localized operator-admissibility obligation"
            ),
        })
    if not markers:
        violations.append({
            "type": "operator_markers_absent",
            "reason": "receipt exposes no recognizable singular-integral/operator mechanism",
        })
    if canonical_missing:
        violations.append({
            "type": "operator_canary_fields_missing",
            "missing_fields": canonical_missing,
            "reason": (
                "annular Riesz/Leray/CZ canaries require explicit carrier, "
                "bandlimit, endpoint, commutator, low-high leakage, projection "
                "target, same-stream binding, and hostile-packet fields"
            ),
        })
    complete = not missing
    passed = complete and not canonical_missing and not rejected and bool(markers)
    next_units = _canary_next_work_units(
        missing_fields=missing,
        canonical_missing_fields=canonical_missing,
        rejected_substitutes=rejected,
        text=text,
    )
    return {
        "gate": GATE_ID,
        "label": receipt.get("label", "pde_operator_admissibility"),
        "passed": passed,
        "complete": complete,
        "classification": (
            "operator_admissibility_paid" if passed
            else "operator_admissibility_unpaid"
        ),
        "missing_fields": missing,
        "rejected_substitutes": rejected,
        "canonical_missing_fields": canonical_missing,
        "operator_markers": markers,
        "violations": violations,
        "required_fields": list(REQUIRED_FIELDS),
        "canonical_required_fields": list(CANARY_FIELD_ALIASES),
        "next_required_work_units": next_units,
    }


def _read_json(path: str) -> dict[str, Any]:
    import json
    import sys

    if path == "-":
        return json.loads(sys.stdin.read())
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Validate PDE singular-integral operator admissibility."
    )
    parser.add_argument("receipt_json", help="Path to receipt JSON, or - for stdin")
    args = parser.parse_args(argv)
    result = run_pde_operator_admissibility_gate(_read_json(args.receipt_json))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
