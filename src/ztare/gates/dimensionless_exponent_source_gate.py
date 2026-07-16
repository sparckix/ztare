# G-DIMENSIONLESS-EXPONENT-SOURCE - analytic-source receipt for dimensionless powers.
#
# Dimensional/Pi checks cannot determine powers of dimensionless variables.
# For claims like `mu * r^2 / T`, the `mu/T` units are dimensional, but the
# `r^2` exponent must come from an analytic identity or inequality, not from
# dimensional analysis alone.
from __future__ import annotations

from fractions import Fraction
from typing import Any


GATE_ID = "G-DIMENSIONLESS-EXPONENT-SOURCE"

_REQUIRED_RECEIPTS = (
    "analytic_source",
    "source_identity_type",
    "source_derives_exponent",
    "fixed_before_payoff",
    "same_carrier_or_scope",
    "not_dimensional_analysis_only",
    "consumed_by",
)


def _fraction(value: Any) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value, 1)
    if isinstance(value, float):
        return Fraction(str(value))
    text = str(value).strip()
    if not text:
        raise ValueError("empty exponent")
    return Fraction(text)


def _fmt(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _normalise_dimensionless_variables(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return [{"name": str(name), "exponent": exponent} for name, exponent in value.items()]
    if isinstance(value, list):
        out: list[dict[str, Any]] = []
        for item in value:
            if isinstance(item, dict):
                out.append(dict(item))
            else:
                out.append({"name": str(item), "exponent": 1})
        return out
    return []


def run_gate(*, expression: str, dimensionless_variables: Any,
             receipts: dict[str, Any] | None = None,
             label: str | None = None) -> dict[str, Any]:
    receipts = receipts or {}
    variables = _normalise_dimensionless_variables(dimensionless_variables)
    parsed: list[dict[str, str]] = []
    violations: list[dict[str, Any]] = []

    for index, variable in enumerate(variables):
        name = str(variable.get("name") or "").strip()
        if not name:
            violations.append({"type": "missing_variable_name", "index": index})
            continue
        try:
            exponent = _fraction(variable.get("exponent", 1))
        except Exception as exc:
            violations.append({"type": "invalid_exponent", "name": name, "error": str(exc)})
            continue
        parsed.append({"name": name, "exponent": _fmt(exponent)})

    nontrivial = [item for item in parsed if item["exponent"] not in {"0", "1"}]
    if not nontrivial and not violations:
        return {
            "gate_id": GATE_ID,
            "label": label,
            "passed": True,
            "hard_fail": False,
            "expression": expression,
            "nontrivial_dimensionless_exponents": [],
            "reason": "no nontrivial dimensionless exponent declared; no analytic exponent receipt required",
        }

    missing = [field for field in _REQUIRED_RECEIPTS if receipts.get(field) in (None, "", [], {})]
    if missing:
        violations.append({
            "type": "missing_analytic_exponent_receipts",
            "missing_fields": missing,
        })

    bool_fields = (
        "source_derives_exponent",
        "fixed_before_payoff",
        "same_carrier_or_scope",
        "not_dimensional_analysis_only",
    )
    false_fields = [field for field in bool_fields if receipts.get(field) is not True]
    if false_fields:
        violations.append({
            "type": "analytic_exponent_receipt_false_or_unpaid",
            "fields": false_fields,
        })

    source_type = str(receipts.get("source_identity_type") or "").strip()
    known_source = source_type.lower().replace("-", "_") in {
        "cauchy_schwarz",
        "jensen",
        "energy_identity",
        "ode_normal_form",
        "interpolation",
        "definition",
        "coarea_identity",
        "other",
    }
    if source_type and not known_source:
        violations.append({
            "type": "unknown_source_identity_type",
            "source_identity_type": source_type,
        })

    passed = not violations
    return {
        "gate_id": GATE_ID,
        "label": label,
        "passed": passed,
        "hard_fail": not passed,
        "expression": expression,
        "nontrivial_dimensionless_exponents": nontrivial,
        "receipts": {field: receipts.get(field) for field in _REQUIRED_RECEIPTS},
        "violations": violations,
        "reason": (
            "nontrivial dimensionless exponent is backed by an analytic source receipt"
            if passed else
            "nontrivial dimensionless exponent cannot be spent from dimensional analysis alone"
        ),
    }


def format_report(result: dict[str, Any]) -> str:
    status = "PASS" if result.get("passed") else "FAIL"
    label = result.get("label") or result.get("expression") or GATE_ID
    return f"{status} {label}: {result.get('reason')}"
