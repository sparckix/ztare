"""G-PDE-ANALYTIC-SUBSTANCE -- distinguish PDE estimates from plumbing.

This gate is substrate-neutral but PDE-shaped.  It is meant to sit beside
source-contract gates such as same-carrier packing and nonadaptive selection.
Those gates can certify that a route is not postselected; this one checks
whether the receipt also contains analytic PDE content: a quantity, inequality,
scale/localization data, derivation mechanism, constants/exponents, and a
sharpness or hostile-packet boundary.
"""
from __future__ import annotations

from typing import Any

try:  # pragma: no cover - keeps direct script execution usable
    from ztare.gates.required_field_semantics import is_semantically_present
except ModuleNotFoundError:  # pragma: no cover
    from required_field_semantics import is_semantically_present

GATE_ID = "G-PDE-ANALYTIC-SUBSTANCE"

REQUIRED_FIELDS = (
    "analytic_object",
    "target_estimate",
    "quantitative_inequality",
    "norm_or_quantity",
    "scale_or_localization",
    "derivation_mechanism",
    "constants_or_exponents",
    "endpoint_or_limit_handling",
    "hostile_packet_or_sharpness",
)

WEAK_SUBSTITUTES = (
    "source_label",
    "constructor_name",
    "lean_constructor",
    "bridge_receipt",
    "timing_receipt",
    "gate_pass_only",
    "same_carrier_label",
    "finite_budget_label",
    "workbench_pack_only",
    "formal_transport_only",
)

ANALYTIC_MARKERS = (
    "calderon",
    "cz",
    "riesz",
    "heat kernel",
    "duhamel",
    "pressure",
    "local energy",
    "caccioppoli",
    "carleson",
    "morrey",
    "besov",
    "parabolic",
    "interpolation",
    "commutator",
    "reverse holder",
    "maximal",
    "green",
    "kernel",
    "cutoff",
    "annulus",
    "scale",
    "endpoint",
)


def _present(value: Any, *, field: str | None = None) -> bool:
    return is_semantically_present(value, field=field)


def _text_blob(receipt: dict[str, Any]) -> str:
    values: list[str] = []
    for value in receipt.values():
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, (list, tuple)):
            values.extend(str(item) for item in value)
        elif isinstance(value, dict):
            values.extend(str(item) for item in value.values())
    return " ".join(values).lower()


def run_pde_analytic_substance_gate(receipt: dict[str, Any]) -> dict[str, Any]:
    """Validate that a claimed PDE step contains analytic estimate content."""
    missing = [
        field for field in REQUIRED_FIELDS
        if not _present(receipt.get(field), field=field)
    ]
    weak_hits = [
        field for field in WEAK_SUBSTITUTES
        if _present(receipt.get(field), field=field)
    ]
    blob = _text_blob(receipt)
    markers = [marker for marker in ANALYTIC_MARKERS if marker in blob]

    violations: list[dict[str, Any]] = []
    if missing:
        violations.append({
            "type": "pde_analytic_substance_missing",
            "missing_fields": missing,
            "reason": (
                "PDE estimate receipts need a quantitative analytic object, "
                "inequality, scale/localization, derivation mechanism, "
                "constants/exponents, endpoint handling, and sharpness boundary"
            ),
        })
    if weak_hits:
        violations.append({
            "type": "pde_analytic_substance_replaced_by_plumbing",
            "fields": weak_hits,
            "reason": (
                "constructor names, bridge receipts, timing labels, and gate "
                "passes do not by themselves constitute PDE estimate work"
            ),
        })
    if not markers:
        violations.append({
            "type": "pde_analytic_markers_absent",
            "reason": (
                "receipt text exposes no recognizable PDE analytic mechanism "
                "such as pressure, heat kernel, Duhamel, localization, "
                "Carleson/Morrey control, or endpoint handling"
            ),
        })
    if _present(receipt.get("declared_non_estimate")):
        violations.append({
            "type": "declared_non_estimate",
            "reason": "receipt declares that it is not a PDE estimate",
        })

    complete = not missing
    passed = complete and not weak_hits and bool(markers) and not _present(
        receipt.get("declared_non_estimate")
    )
    return {
        "gate": GATE_ID,
        "label": receipt.get("label", "pde_analytic_substance"),
        "passed": passed,
        "complete": complete,
        "classification": (
            "analytic_pde_estimate" if passed else "source_contract_or_plumbing"
        ),
        "missing_fields": missing,
        "weak_substitutes": weak_hits,
        "analytic_markers": markers,
        "violations": violations,
        "required_fields": list(REQUIRED_FIELDS),
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
        description="Validate analytic PDE substance in an estimate receipt."
    )
    parser.add_argument("receipt_json", help="Path to receipt JSON, or - for stdin")
    args = parser.parse_args(argv)
    result = run_pde_analytic_substance_gate(_read_json(args.receipt_json))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
