"""G-PDE-PHYSICAL-ACCOUNTING -- force PDE routes through physical invoices.

The gate is deliberately substrate-general.  It does not prove an estimate;
it rejects routes that present an analytic-looking inequality without naming
the physical balance, dimensions, flux/boundary terms, localization carrier,
sign/positivity status, operator/projection losses, and hostile physical packet.
"""
from __future__ import annotations

from typing import Any

try:  # pragma: no cover - direct script execution
    from ztare.gates.pde_inequality_dimensional_gate import run_gate as run_pde_inequality_dimensional_gate
    from ztare.gates.pi_group_forcing import run_pi_group_forcing
    from ztare.gates.required_field_semantics import is_semantically_present
except ModuleNotFoundError:  # pragma: no cover
    from pde_inequality_dimensional_gate import run_gate as run_pde_inequality_dimensional_gate
    from pi_group_forcing import run_pi_group_forcing
    from required_field_semantics import is_semantically_present


GATE_ID = "G-PDE-PHYSICAL-ACCOUNTING"

REQUIRED_FIELDS = (
    "physical_system",
    "governing_law_or_balance",
    "conserved_or_dissipated_quantity",
    "quantity_dimensions",
    "target_dimensions",
    "scale_normalization",
    "flux_or_boundary_terms",
    "localization_region",
    "carrier_or_material_volume",
    "source_sink_or_forcing_terms",
    "sign_or_positivity_structure",
    "operator_or_projection_losses",
    "cutoff_commutator_or_tail_terms",
    "initial_boundary_data",
    "hostile_physical_packet",
)

REQUIRED_FIELD_GROUPS = (
    ("candidate_inequality", "target_inequality_or_statement"),
    ("balance_law_terms", "physical_balance_terms"),
)

REJECTED_SUBSTITUTES = (
    "dimension_check_omitted",
    "conservation_label_only",
    "energy_label_without_flux",
    "boundary_terms_discarded",
    "cutoff_tail_discarded",
    "operator_loss_ignored",
    "signed_cancellation_as_positive_payment",
    "proxy_carrier_or_control_volume",
    "post_selected_physical_region",
    "unit_inhomogeneous_inequality",
    "soft_physics_loss_only",
)

PHYSICAL_MARKERS = (
    "conservation",
    "balance",
    "flux",
    "energy",
    "mass",
    "momentum",
    "vorticity",
    "enstrophy",
    "dissipation",
    "boundary",
    "source",
    "forcing",
    "control volume",
    "material volume",
    "divergence",
    "stress",
    "pressure",
)

BALANCE_ROLE_GROUPS = {
    "time_change": ("time", "derivative", "evolution", "rate", "dt"),
    "flux_boundary": ("flux", "boundary", "divergence", "surface", "commutator"),
    "source_sink": ("source", "sink", "forcing", "dissipation", "viscous"),
    "sign": ("sign", "positive", "nonnegative", "signed", "positivity", "variation"),
}

PAYMENT_OK = {
    "paid",
    "excluded",
    "zero",
    "not_applicable",
    "target",
    "controlled",
    "bounded",
    "same_stream_paid",
    "outside_scope_paid_elsewhere",
}

NEXT_WORK_UNITS = (
    {
        "leaf_id": "pde.leaf.physics.dimensional_homogeneity",
        "target": "physical_dimensional_homogeneity",
        "op_id": "pec_h",
        "goal": "prove the candidate inequality is dimensionally homogeneous after the stated normalization",
        "work_unit_type": "estimate_derivation",
        "required_gate_ids": ["G-PDE-INEQ-DIM", GATE_ID],
        "must_return": {
            "target_inequality_or_statement": "dimension vector equality for both sides",
            "proof_steps": "list base dimensions, normalization powers, and resulting dimensionless groups",
            "first_failed_line_or_success": "first mismatched dimension or success",
            "hostile_packet_tested": "unit_inhomogeneous_inequality",
            "currency_exchange_used": "none unless normalization changes target currency",
            "verdict": "CLOSE | FAIL | SHRINK",
        },
    },
    {
        "leaf_id": "pde.leaf.physics.balance_flux_boundary",
        "target": "physical_balance_flux_boundary_invoice",
        "op_id": "pec_l",
        "goal": "derive the balance law with all boundary, flux, source, and sink terms paid or excluded",
        "work_unit_type": "estimate_derivation",
        "required_gate_ids": [GATE_ID, "G-PDE-HOSTILE-WITNESS"],
        "must_return": {
            "target_inequality_or_statement": "localized balance identity or inequality",
            "proof_steps": "derive time change, divergence/flux term, boundary term, source/sink term, and sign",
            "first_failed_line_or_success": "first unpaid physical invoice",
            "hostile_packet_tested": "energy_label_without_flux",
            "currency_exchange_used": "physical balance to proof currency",
            "verdict": "CLOSE | FAIL | SHRINK | NEED_THEOREM",
        },
    },
    {
        "leaf_id": "pde.leaf.physics.localization_carrier_identity",
        "target": "physical_localization_carrier_identity",
        "op_id": "pec_i",
        "goal": "bind the physical control volume/carrier to the selected analytic stream before payoff",
        "work_unit_type": "positive_constructor_attempt",
        "required_gate_ids": [GATE_ID, "G-NONADAPTIVE-SOURCE-SELECTION"],
        "must_return": {
            "target_inequality_or_statement": "carrier/control-volume identity before observation of the target payoff",
            "proof_steps": "localization choice, material/control-volume identity, source binding, anti-postselection",
            "first_failed_line_or_success": "first carrier/source mismatch",
            "hostile_packet_tested": "proxy_carrier_or_control_volume",
            "currency_exchange_used": "physical carrier to analytic carrier",
            "verdict": "CLOSE | FAIL | SHRINK | NEED_THEOREM",
        },
    },
    {
        "leaf_id": "pde.leaf.physics.sign_operator_tail_invoice",
        "target": "physical_sign_operator_tail_invoice",
        "op_id": "pec_l",
        "goal": "pay sign/positivity, projection, cutoff, and tail losses between the physical balance and target estimate",
        "work_unit_type": "estimate_derivation",
        "required_gate_ids": [GATE_ID, "G-PDE-OPERATOR-ADMISSIBILITY", "G-POSITIVE-VARIATION-BRIDGE"],
        "must_return": {
            "target_inequality_or_statement": "physical payment survives sign, projection, cutoff, and tail exchanges",
            "proof_steps": "sign/positivity step, operator loss, cutoff commutator, tail term, target currency",
            "first_failed_line_or_success": "first unpaid sign/operator/tail exchange",
            "hostile_packet_tested": "signed_cancellation_as_positive_payment",
            "currency_exchange_used": "physical balance to target positive currency",
            "verdict": "CLOSE | FAIL | SHRINK | NEED_THEOREM",
        },
    },
)


def _present(value: Any, *, field: str | None = None) -> bool:
    return is_semantically_present(value, field=field or "")


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if value in (None, ""):
        return []
    return [value]


def _field_group_present(receipt: dict[str, Any], group: tuple[str, ...]) -> bool:
    return any(_present(receipt.get(field), field=field) for field in group)


def _blob(receipt: dict[str, Any]) -> str:
    values: list[str] = []
    for value in receipt.values():
        if isinstance(value, dict):
            values.extend(str(item) for item in value.values())
        elif isinstance(value, (list, tuple)):
            values.extend(str(item) for item in value)
        else:
            values.append(str(value))
    return " ".join(values).lower()


def _dimension_vector(value: Any) -> dict[str, Any] | str:
    if isinstance(value, dict):
        return {
            str(key): val for key, val in sorted(value.items())
            if val not in (0, "0", None, "")
        }
    if isinstance(value, str):
        return " ".join(value.strip().lower().split())
    return ""


def _dimension_mismatch(receipt: dict[str, Any]) -> bool:
    left = _dimension_vector(receipt.get("quantity_dimensions"))
    right = _dimension_vector(receipt.get("target_dimensions"))
    if not left or not right:
        return False
    return left != right


def _candidate_inequality(receipt: dict[str, Any]) -> str:
    for field in ("candidate_inequality", "target_inequality_or_statement"):
        value = receipt.get(field)
        if _present(value, field=field):
            return str(value)
    return ""


def _allowed_endpoints(receipt: dict[str, Any]) -> set[str]:
    return {str(item) for item in _as_list(receipt.get("allowed_endpoints")) if str(item).strip()}


def _dimensional_features(receipt: dict[str, Any]) -> dict[str, Any]:
    value = receipt.get("dimensional_features")
    return dict(value) if isinstance(value, dict) else {}


def _candidate_dimension_audit(receipt: dict[str, Any]) -> dict[str, Any]:
    candidate = _candidate_inequality(receipt)
    if not candidate:
        return {
            "ran": False,
            "passed": False,
            "reason": "missing candidate_inequality or target_inequality_or_statement",
        }
    result = run_pde_inequality_dimensional_gate(
        candidate,
        dimensional_features=_dimensional_features(receipt),
        allowed_endpoints=_allowed_endpoints(receipt),
    )
    return {
        "ran": True,
        "passed": bool(result.get("passed")),
        "result": result,
    }


def _term_role_hits(role_text: str) -> set[str]:
    role = role_text.lower()
    hits: set[str] = set()
    for group, needles in BALANCE_ROLE_GROUPS.items():
        if any(needle in role for needle in needles):
            hits.add(group)
    return hits


def _balance_law_audit(receipt: dict[str, Any]) -> dict[str, Any]:
    raw_terms = receipt.get("balance_law_terms", receipt.get("physical_balance_terms"))
    terms = [term for term in _as_list(raw_terms) if isinstance(term, dict)]
    violations: list[dict[str, Any]] = []
    if not terms:
        return {
            "ran": False,
            "passed": False,
            "terms": [],
            "violations": [{
                "type": "balance_terms_missing",
                "reason": "term-level physical balance accounting is required",
            }],
        }

    role_hits: set[str] = set()
    comparable_dims: list[dict[str, Any] | str] = []
    audited_terms: list[dict[str, Any]] = []
    for i, term in enumerate(terms):
        role = str(term.get("role", ""))
        role_hits.update(_term_role_hits(role))
        status = str(term.get("payment_status", term.get("status", ""))).strip().lower()
        dim = _dimension_vector(term.get("dimensions"))
        audited = {
            "index": i,
            "name": str(term.get("name", f"term_{i}")),
            "role": role,
            "payment_status": status,
            "dimensions": dim,
        }
        audited_terms.append(audited)
        if not role:
            violations.append({"type": "balance_term_role_missing", "term_index": i})
        if not dim:
            violations.append({"type": "balance_term_dimensions_missing", "term_index": i})
        else:
            comparable_dims.append(dim)
        if status not in PAYMENT_OK:
            violations.append({
                "type": "balance_term_unpaid",
                "term_index": i,
                "payment_status": status,
            })

    missing_roles = [
        group for group in BALANCE_ROLE_GROUPS
        if group not in role_hits
    ]
    if missing_roles:
        violations.append({
            "type": "balance_roles_missing",
            "missing_roles": missing_roles,
        })

    nonmatching_dims: list[dict[str, Any]] = []
    if comparable_dims:
        expected = comparable_dims[0]
        for audited in audited_terms:
            if audited["dimensions"] and audited["dimensions"] != expected:
                nonmatching_dims.append({
                    "term_index": audited["index"],
                    "dimensions": audited["dimensions"],
                    "expected": expected,
                })
        if nonmatching_dims:
            violations.append({
                "type": "balance_term_dimension_mismatch",
                "nonmatching_terms": nonmatching_dims,
            })

    return {
        "ran": True,
        "passed": not violations,
        "terms": audited_terms,
        "role_hits": sorted(role_hits),
        "violations": violations,
    }


def _pi_group_audit(receipt: dict[str, Any]) -> dict[str, Any]:
    raw_contracts = receipt.get("pi_group_forcing", receipt.get("pi_group_contracts"))
    contracts = [
        contract for contract in _as_list(raw_contracts)
        if isinstance(contract, dict)
    ]
    if not contracts:
        return {"ran": False, "passed": True, "checks": [], "violations": []}

    checks: list[dict[str, Any]] = []
    violations: list[dict[str, Any]] = []
    for i, contract in enumerate(contracts):
        quantity_dim = contract.get("quantity_dim", contract.get("quantity_dimensions"))
        subset_dims = contract.get("subset_dims", contract.get("source_dimensions"))
        if not isinstance(quantity_dim, dict) or not isinstance(subset_dims, (dict, list, tuple)):
            violations.append({
                "type": "pi_group_contract_malformed",
                "contract_index": i,
            })
            continue
        result = run_pi_group_forcing(quantity_dim=quantity_dim, subset_dims=subset_dims)
        if result.get("forced"):
            actual = "forced"
        elif result.get("needs_independent_constant"):
            actual = "needs_independent_constant"
        elif result.get("ambiguous"):
            actual = "ambiguous"
        else:
            actual = "not_forced"
        expected = contract.get("expected")
        expected_values = {str(item) for item in _as_list(expected) if str(item).strip()}
        check = {
            "contract_index": i,
            "label": str(contract.get("label", f"pi_group_contract_{i}")),
            "expected": sorted(expected_values),
            "actual": actual,
            "result": result,
        }
        checks.append(check)
        if expected_values and actual not in expected_values:
            violations.append({
                "type": "pi_group_contract_mismatch",
                "contract_index": i,
                "expected": sorted(expected_values),
                "actual": actual,
                "reason": result.get("reason"),
            })

    return {
        "ran": True,
        "passed": not violations,
        "checks": checks,
        "violations": violations,
    }


def _next_required_work_units(
    *,
    missing_fields: list[str],
    rejected_substitutes: list[str],
    dimension_mismatch: bool,
    candidate_dimension_failed: bool,
    balance_law_failed: bool,
    pi_group_failed: bool,
) -> list[dict[str, Any]]:
    if not (
        missing_fields or rejected_substitutes or dimension_mismatch
        or candidate_dimension_failed or balance_law_failed or pi_group_failed
    ):
        return []
    blocked_by = {
        "missing_fields": missing_fields,
        "rejected_substitutes": rejected_substitutes,
        "dimension_mismatch": dimension_mismatch,
        "candidate_dimension_failed": candidate_dimension_failed,
        "balance_law_failed": balance_law_failed,
        "pi_group_failed": pi_group_failed,
    }
    units: list[dict[str, Any]] = []
    for unit in NEXT_WORK_UNITS:
        row = {
            "schema": "pde-next-required-work-unit-v1",
            "gate_id": GATE_ID,
            "action": "dispatch_physical_accounting_leaf",
            "blocked_by": blocked_by,
            **unit,
        }
        units.append(row)
    return units


def run_pde_physical_accounting_gate(receipt: dict[str, Any]) -> dict[str, Any]:
    """Validate that a PDE route exposes the physical invoices it consumes."""
    missing = [
        field for field in REQUIRED_FIELDS
        if not _present(receipt.get(field), field=field)
    ]
    missing.extend(
        "|".join(group) for group in REQUIRED_FIELD_GROUPS
        if not _field_group_present(receipt, group)
    )
    rejected = [
        field for field in REJECTED_SUBSTITUTES
        if _present(receipt.get(field), field=field)
    ]
    text = _blob(receipt)
    markers = [marker for marker in PHYSICAL_MARKERS if marker in text]
    dimension_mismatch = _dimension_mismatch(receipt)
    candidate_audit = _candidate_dimension_audit(receipt)
    balance_audit = _balance_law_audit(receipt)
    pi_audit = _pi_group_audit(receipt)
    violations: list[dict[str, Any]] = []
    if missing:
        violations.append({
            "type": "physical_accounting_missing",
            "missing_fields": missing,
            "reason": (
                "PDE routes must expose physical system, balance law, "
                "quantity, dimensions, normalization, flux/boundary/source "
                "terms, localization carrier, sign, operator/cutoff losses, "
                "data, and hostile physical packet"
            ),
        })
    if rejected:
        violations.append({
            "type": "physical_substitute_rejected",
            "rejected_substitutes": rejected,
            "reason": (
                "labels, discarded flux/tails, ignored operator losses, proxy "
                "carriers, post-selection, unit-inhomogeneous inequalities, "
                "and soft physics losses do not pay physical accounting"
            ),
        })
    if dimension_mismatch:
        violations.append({
            "type": "dimension_mismatch",
            "quantity_dimensions": receipt.get("quantity_dimensions"),
            "target_dimensions": receipt.get("target_dimensions"),
            "reason": "candidate physical quantity and target have different dimensions",
        })
    if not candidate_audit.get("passed"):
        violations.append({
            "type": "candidate_inequality_dimension_or_endpoint_failure",
            "audit": candidate_audit,
        })
    if not balance_audit.get("passed"):
        violations.append({
            "type": "balance_law_term_audit_failure",
            "audit": balance_audit,
        })
    if not pi_audit.get("passed"):
        violations.append({
            "type": "pi_group_forcing_contract_failure",
            "audit": pi_audit,
        })
    if not markers:
        violations.append({
            "type": "physical_markers_absent",
            "reason": "receipt exposes no recognizable physical balance, flux, or conserved/dissipated quantity",
        })
    complete = not missing
    passed = (
        complete
        and not rejected
        and not dimension_mismatch
        and bool(markers)
        and bool(candidate_audit.get("passed"))
        and bool(balance_audit.get("passed"))
        and bool(pi_audit.get("passed"))
    )
    return {
        "gate": GATE_ID,
        "label": receipt.get("label", "pde_physical_accounting"),
        "passed": passed,
        "complete": complete,
        "classification": (
            "physical_accounting_paid" if passed
            else "physical_accounting_unpaid"
        ),
        "missing_fields": missing,
        "rejected_substitutes": rejected,
        "physical_markers": markers,
        "dimension_mismatch": dimension_mismatch,
        "candidate_dimension_audit": candidate_audit,
        "balance_law_audit": balance_audit,
        "pi_group_audit": pi_audit,
        "violations": violations,
        "next_required_work_units": _next_required_work_units(
            missing_fields=missing,
            rejected_substitutes=rejected,
            dimension_mismatch=dimension_mismatch,
            candidate_dimension_failed=not bool(candidate_audit.get("passed")),
            balance_law_failed=not bool(balance_audit.get("passed")),
            pi_group_failed=not bool(pi_audit.get("passed")),
        ),
        "physics_forcing": {
            "deterministic": [
                "required physical invoice fields",
                "candidate inequality dimensional and endpoint audit",
                "term-level balance-law audit",
                "dimension-vector equality when supplied as comparable vectors",
                "optional Pi-group forcing contracts",
                "rejected shortcut tokens",
                "next leaf work orders for missing invoices",
            ],
            "agent_or_theorem_work": [
                "derive the balance law",
                "prove flux/boundary/source terms are paid or excluded",
                "prove sign/operator/cutoff exchanges",
                "formalize or cite the resulting theorem where claimed",
            ],
        },
    }
