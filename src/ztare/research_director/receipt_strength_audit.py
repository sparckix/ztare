"""Receipt-strength audit for action contracts and PDE carriers.

This primitive catches a recurring false-positive surface: a constructor has a
field with the right name (``noOverlap``, ``sameOwner``, ``fixedBeforePayoff``),
but the field is only ``Prop`` or free text.  The audit is deliberately general:
callers supply field names/types from Lean, JSON schemas, or action-contract
artifacts; this module classifies whether required receipt families are missing,
Prop-only, or backed by a typed/numeric witness.

It is not a theorem prover.  It is an anti-laundering prefilter for hard
residual work.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class ReceiptField:
    name: str
    type: str = ""


@dataclass(frozen=True)
class ReceiptRequirement:
    name: str
    keywords: tuple[str, ...]
    minimum_strength: str = "typed"  # typed | numeric
    required: bool = True


DEFAULT_RECEIPT_REQUIREMENTS: tuple[ReceiptRequirement, ...] = (
    ReceiptRequirement(
        name="owner_root_numeric_bound",
        keywords=("ownerrootbudget", "owner_root_budget", "rootbudget"),
        minimum_strength="numeric",
    ),
    ReceiptRequirement(
        name="no_overlap_or_disjointness",
        keywords=("nooverlap", "no_overlap", "disjoint", "overlap"),
        minimum_strength="typed",
    ),
    ReceiptRequirement(
        name="payoff_independence",
        keywords=(
            "notdefinedfrompayoff",
            "not_defined_from_payoff",
            "fixedbeforepayoff",
            "fixed_before_payoff",
            "declaredbeforepayoff",
            "declared_before_payoff",
        ),
        minimum_strength="typed",
    ),
    ReceiptRequirement(
        name="same_owner_or_source_binding",
        keywords=("sameowner", "same_owner", "sameprefix", "same_prefix", "samesource", "same_source", "refinesownerpreimage"),
        minimum_strength="typed",
    ),
    ReceiptRequirement(
        name="no_reuse_or_no_rebilling",
        keywords=("noreuse", "no_reuse", "rebill", "double_spend", "doublespend"),
        minimum_strength="typed",
    ),
)

_NUMERIC_MARKERS = (
    "<=", "≤", ">=", "≥", "<", ">", "=", "+", "-", "*", "/",
    "Real", "Nat", "ℝ", "ℕ",
)
_LEANISH_MARKERS = _NUMERIC_MARKERS + (
    "∀", "∃", "->", "→", "¬", "∧", "∨", "(", ")", ".",
)


def _normalize_field(raw: Any) -> ReceiptField:
    if isinstance(raw, ReceiptField):
        return raw
    if isinstance(raw, Mapping):
        return ReceiptField(
            name=str(raw.get("name") or raw.get("field_name") or ""),
            type=str(raw.get("type") or raw.get("field_type") or ""),
        )
    text = str(raw)
    if ":" in text:
        name, ftype = text.split(":", 1)
        return ReceiptField(name=name.strip(), type=ftype.strip())
    return ReceiptField(name=text.strip(), type="")


def _compact(value: str) -> str:
    return value.lower().replace("-", "_").replace(" ", "")


def _field_text(field: ReceiptField) -> str:
    return _compact(f"{field.name} {field.type}")


def _is_prop_only(field: ReceiptField) -> bool:
    ftype = field.type.strip()
    return ftype == "Prop" or ftype.endswith(" Prop")


def _looks_free_text(ftype: str) -> bool:
    stripped = ftype.strip()
    if not stripped or _is_prop_only(ReceiptField("", stripped)):
        return False
    if any(marker in stripped for marker in _LEANISH_MARKERS):
        return False
    compact = stripped.replace("_", "")
    has_space = any(ch.isspace() for ch in stripped)
    has_camel_or_acronym = any(ch.isupper() for ch in compact[1:])
    return has_space and not has_camel_or_acronym


def _strength(field: ReceiptField, prop_names: set[str] | None = None) -> str:
    if _is_prop_only(field) or not field.type:
        return "prop_only_or_untyped"
    if prop_names and _compact(field.type) in prop_names:
        return "prop_only_or_untyped"
    if _looks_free_text(field.type):
        return "free_text"
    if any(marker in field.type for marker in _NUMERIC_MARKERS):
        return "numeric"
    return "typed"


def _meets(minimum: str, strength: str) -> bool:
    order = {"prop_only_or_untyped": 0, "free_text": 0, "typed": 1, "numeric": 2}
    return order.get(strength, 0) >= order.get(minimum, 1)


def _coerce_requirements(
    requirements: Iterable[ReceiptRequirement | Mapping[str, Any]] | None,
) -> tuple[ReceiptRequirement, ...]:
    if requirements is None:
        return DEFAULT_RECEIPT_REQUIREMENTS
    out: list[ReceiptRequirement] = []
    for item in requirements:
        if isinstance(item, ReceiptRequirement):
            out.append(item)
            continue
        out.append(ReceiptRequirement(
            name=str(item.get("name") or item.get("id") or "receipt"),
            keywords=tuple(str(x) for x in item.get("keywords", ())),
            minimum_strength=str(item.get("minimum_strength") or "typed"),
            required=bool(item.get("required", True)),
        ))
    return tuple(out)


def run_receipt_strength_audit(
    fields: Iterable[Any],
    *,
    requirements: Iterable[ReceiptRequirement | Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Audit whether named receipt families are backed by strong fields.

    ``passed`` means every required receipt family has at least one matching
    field whose strength meets the requested minimum.  The output is advisory:
    it identifies laundering risk, not mathematical truth.
    """
    normalized = [f for f in (_normalize_field(raw) for raw in fields) if f.name]
    prop_names = {_compact(field.name) for field in normalized if _is_prop_only(field)}
    reqs = _coerce_requirements(requirements)
    requirement_reports: list[dict[str, Any]] = []
    missing: list[str] = []
    weak: list[str] = []

    for req in reqs:
        keywords = tuple(_compact(k) for k in req.keywords if str(k))
        hits = []
        for field in normalized:
            text = _field_text(field)
            if any(k in text for k in keywords):
                strength = _strength(field, prop_names)
                hits.append({
                    "name": field.name,
                    "type": field.type,
                    "strength": strength,
                    "meets_minimum": _meets(req.minimum_strength, strength),
                })
        ok = any(hit["meets_minimum"] for hit in hits)
        if req.required and not hits:
            missing.append(req.name)
        elif req.required and not ok:
            weak.append(req.name)
        requirement_reports.append({
            "name": req.name,
            "keywords": list(req.keywords),
            "minimum_strength": req.minimum_strength,
            "required": req.required,
            "passed": ok or not req.required,
            "hits": hits,
        })

    warnings: list[str] = []
    if missing:
        warnings.append("missing receipt family/families: " + ", ".join(missing))
    if weak:
        warnings.append("weak receipt family/families: " + ", ".join(weak))
    if not normalized:
        warnings.append("no fields supplied")

    passed = not missing and not weak
    return {
        "gate_id": "RD-RECEIPT-STRENGTH-AUDIT",
        "passed": passed,
        "advisory": True,
        "n_fields": len(normalized),
        "missing_receipts": missing,
        "weak_receipts": weak,
        "requirements": requirement_reports,
        "warnings": warnings,
        "summary": (
            "receipt families have typed/numeric backing"
            if passed else
            "receipt families are missing or too weak"
        ),
    }


__all__ = [
    "ReceiptField",
    "ReceiptRequirement",
    "DEFAULT_RECEIPT_REQUIREMENTS",
    "run_receipt_strength_audit",
]
