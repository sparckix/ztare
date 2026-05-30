"""Profile-driven single-spend carrier audit.

This is a small research-director primitive for the recurring failure mode
where a candidate mechanism declares several channels that all consume the
same scarce resource, but does not expose the receipts needed to keep those
channels separated.  It is not a theorem prover.  It checks the surface for:

  - named channels supplied by the caller or by the generic default profile
  - non-Prop evidence for channels that the profile marks as blocking
  - explicit nonnegativity witnesses for profile-declared spend variables
  - timing / identity / no-reuse receipts when the profile asks for them

Domain vocabulary belongs in the caller's profile, not in this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class CarrierField:
    name: str
    type: str = ""


@dataclass(frozen=True)
class CarrierAuditProfile:
    channel_keywords: Mapping[str, tuple[str, ...]]
    spend_variable_keywords: Mapping[str, tuple[str, ...]]
    blocking_channels: frozenset[str]
    gate_id: str = "RD-SINGLE-SPEND-CARRIER-AUDIT"


DEFAULT_CHANNEL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "source": ("source", "producer", "production", "gain"),
    "target_charge": ("target_charge", "targetcharge", "charge", "invoice", "debit"),
    "reserve": ("reserve", "buffer", "collateral", "escrow"),
    "partition": ("partition", "totalbudget", "total_budget", "single_spend", "singlespend"),
    "identity": ("identity", "sameindex", "same_index", "incidence", "receipt"),
    "timing": ("timing", "before", "fixed", "preselected", "precommitted", "precommit"),
    "no_reuse": (
        "norepeated",
        "no_repeated",
        "noreuse",
        "no_reuse",
        "nonreuse",
        "double_spend",
        "doublecount",
        "rebill",
    ),
}

DEFAULT_SPEND_VARIABLE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "source": ("sourcespend", "source_spend"),
    "target_charge": ("targetchargespend", "target_charge_spend", "chargespent", "charge_spend"),
    "reserve": ("reservespent", "reserve_spend"),
}

DEFAULT_BLOCKING_CHANNELS = frozenset({"source", "target_charge", "reserve", "partition", "identity"})

NONNEGATIVE_KEYWORDS = (
    "nonnegative",
    "nonneg",
    "ge_zero",
    "gezero",
    "0≤",
    "0<=",
)

STRUCTURED_EVIDENCE_KEYWORDS = (
    "spend",
    "budget",
    "bound",
    "certificate",
    "estimate",
    "evidence",
    "receipt",
    "witness",
    "measure",
    "embedding",
    "partition",
    "carrier",
)

LEANISH_TYPE_MARKERS = (
    "≤",
    "<=",
    "≥",
    ">=",
    "=",
    "→",
    "->",
    "∀",
    "∃",
    "¬",
    "∧",
    "∨",
    "ℝ",
    "ℕ",
    ".",
    "(",
    ")",
)


def _normalize_keywords(values: Iterable[Any]) -> tuple[str, ...]:
    return tuple(str(value).lower().replace("-", "_") for value in values if str(value))


def _coerce_profile(profile: CarrierAuditProfile | Mapping[str, Any] | None) -> CarrierAuditProfile:
    if isinstance(profile, CarrierAuditProfile):
        return profile
    if profile is None:
        return CarrierAuditProfile(
            channel_keywords=DEFAULT_CHANNEL_KEYWORDS,
            spend_variable_keywords=DEFAULT_SPEND_VARIABLE_KEYWORDS,
            blocking_channels=DEFAULT_BLOCKING_CHANNELS,
        )
    if "channel_keywords" in profile:
        raw_channels = profile.get("channel_keywords") or {}
    else:
        raw_channels = profile
    channels = {
        str(channel): _normalize_keywords(keywords)
        for channel, keywords in raw_channels.items()
    }
    raw_spend = profile.get("spend_variable_keywords", {}) if "channel_keywords" in profile else {}
    spend_keywords = {
        str(channel): _normalize_keywords(keywords)
        for channel, keywords in raw_spend.items()
    }
    raw_blocking = profile.get("blocking_channels") if "channel_keywords" in profile else None
    blocking = (
        frozenset(str(channel) for channel in raw_blocking)
        if raw_blocking is not None else
        frozenset(channels)
    )
    return CarrierAuditProfile(
        channel_keywords=channels,
        spend_variable_keywords=spend_keywords,
        blocking_channels=blocking,
        gate_id=str(profile.get("gate_id") or "RD-SINGLE-SPEND-CARRIER-AUDIT")
        if "channel_keywords" in profile else
        "RD-SINGLE-SPEND-CARRIER-AUDIT",
    )


def _normalize_field(raw: Any) -> CarrierField:
    if isinstance(raw, CarrierField):
        return raw
    if isinstance(raw, dict):
        return CarrierField(
            name=str(raw.get("name") or raw.get("field_name") or ""),
            type=str(raw.get("type") or raw.get("field_type") or ""),
        )
    text = str(raw)
    if ":" in text:
        name, ftype = text.split(":", 1)
        return CarrierField(name=name.strip(), type=ftype.strip())
    return CarrierField(name=text.strip(), type="")


def _field_text(field: CarrierField) -> str:
    return f"{field.name} {field.type}".lower().replace("-", "_")


def _is_prop_only(field: CarrierField) -> bool:
    ftype = field.type.strip()
    return ftype == "Prop" or ftype.endswith(" Prop")


def _looks_like_free_text_type(ftype: str) -> bool:
    """Heuristic guard against prose being counted as proof evidence.

    The audit accepts hand-written ``name:type`` strings for portability, but
    the type half must look like a Lean type/expression or a named receipt. A
    lower-case sentence such as "separates parent invoice" is context, not paid
    evidence.
    """
    stripped = ftype.strip()
    if not stripped or _is_prop_only(CarrierField(name="", type=stripped)):
        return False
    if any(marker in stripped for marker in LEANISH_TYPE_MARKERS):
        return False
    compact = stripped.replace("_", "")
    has_space = any(ch.isspace() for ch in stripped)
    has_camel_or_acronym = any(ch.isupper() for ch in compact[1:])
    return has_space and not has_camel_or_acronym


def _is_paid_or_structural(field: CarrierField) -> bool:
    text = _field_text(field)
    if _is_prop_only(field):
        return False
    if field.type and _looks_like_free_text_type(field.type):
        return False
    if field.type and not _is_prop_only(field):
        return True
    return any(token in text for token in STRUCTURED_EVIDENCE_KEYWORDS)


def _compact_field_text(field: CarrierField) -> str:
    return _field_text(field).replace(" ", "")


def _field_matches(field: CarrierField, keywords: Iterable[str]) -> bool:
    text = _field_text(field)
    compact = _compact_field_text(field).replace("_", "")
    for keyword in keywords:
        normalized = str(keyword).lower().replace("-", "_")
        if normalized in text:
            return True
        if normalized.replace("_", "") in compact:
            return True
    return False


def _has_explicit_spend_variable(
    channel: str,
    fields: Iterable[CarrierField],
    spend_variable_keywords: Mapping[str, tuple[str, ...]],
) -> bool:
    variables = spend_variable_keywords.get(channel, ())
    if not variables:
        return False
    for field in fields:
        name = field.name.lower().replace("-", "_").replace("_", "")
        if any(variable.replace("_", "") in name for variable in variables):
            return True
    return False


def _has_nonnegative_witness(
    channel: str,
    fields: Iterable[CarrierField],
    spend_variable_keywords: Mapping[str, tuple[str, ...]],
) -> bool:
    variables = spend_variable_keywords.get(channel, ())
    if not variables:
        return True
    compact_vars = tuple(variable.replace("_", "") for variable in variables)
    for field in fields:
        text = _compact_field_text(field).replace("_", "")
        mentions_variable = any(variable in text for variable in compact_vars)
        mentions_nonnegative = any(token in text for token in NONNEGATIVE_KEYWORDS)
        if mentions_variable and mentions_nonnegative and not _is_prop_only(field):
            return True
    return False


def run_single_spend_carrier_audit(
    fields: Iterable[Any],
    *,
    required_channels: Iterable[str] | None = None,
    profile: CarrierAuditProfile | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Audit whether a proposed carrier exposes separated spend channels.

    Args:
        fields: field names, ``name:type`` strings, or dicts with ``name`` and
            ``type`` keys.
        required_channels: optional subset of channel ids.  Defaults to all
            channels in the selected profile.
        profile: optional channel profile.  Use this to supply substrate
            vocabulary at the call site.

    Returns a deterministic diagnostic.  ``passed`` means every required
    channel is present and all profile-blocking channels have non-Prop
    evidence.  It does not assert the estimates are true.
    """
    audit_profile = _coerce_profile(profile)
    normalized = [f for f in (_normalize_field(raw) for raw in fields) if f.name]
    required = list(required_channels or audit_profile.channel_keywords.keys())
    channel_hits: dict[str, list[dict[str, str]]] = {}
    missing: list[str] = []
    prop_only: list[str] = []
    free_text: list[str] = []
    missing_nonnegative: list[str] = []

    for channel in required:
        keywords = audit_profile.channel_keywords.get(channel, (channel,))
        hits = [
            {
                "name": field.name,
                "type": field.type,
                "kind": "paid_or_structural"
                if _is_paid_or_structural(field) else "prop_only_or_untyped",
            }
            for field in normalized
            if _field_matches(field, keywords)
        ]
        channel_hits[channel] = hits
        if not hits:
            missing.append(channel)
        elif all(hit["kind"] == "prop_only_or_untyped" for hit in hits):
            prop_only.append(channel)
        elif any(
            _looks_like_free_text_type(field.type)
            for field in normalized
            if _field_matches(field, keywords)
        ):
            free_text.append(channel)

    blocking_channels = set(audit_profile.blocking_channels)
    prop_only_blocking = sorted(set(prop_only) & blocking_channels)
    for channel in sorted(set(required) & set(audit_profile.spend_variable_keywords)):
        if (
            _has_explicit_spend_variable(
                channel,
                normalized,
                audit_profile.spend_variable_keywords,
            )
            and not _has_nonnegative_witness(
                channel,
                normalized,
                audit_profile.spend_variable_keywords,
            )
        ):
            missing_nonnegative.append(channel)

    passed = not missing and not prop_only_blocking and not missing_nonnegative

    warnings: list[str] = []
    if missing:
        warnings.append(
            "missing separated single-spend channel(s): " + ", ".join(missing)
        )
    if prop_only_blocking:
        warnings.append(
            "blocking channel(s) appear only as Prop/untyped declarations: "
            + ", ".join(prop_only_blocking)
        )
    if free_text:
        warnings.append(
            "free-text evidence ignored for channel(s): "
            + ", ".join(sorted(set(free_text)))
        )
    if missing_nonnegative:
        warnings.append(
            "explicit spend variable(s) lack typed nonnegativity witnesses: "
            + ", ".join(missing_nonnegative)
        )
    if not normalized:
        warnings.append("no carrier fields supplied")

    return {
        "gate_id": audit_profile.gate_id,
        "passed": passed,
        "advisory": True,
        "n_fields": len(normalized),
        "required_channels": required,
        "missing_channels": missing,
        "prop_only_blocking_channels": prop_only_blocking,
        "prop_only_payment_channels": prop_only_blocking,
        "free_text_evidence_channels": sorted(set(free_text)),
        "missing_nonnegative_spend_channels": missing_nonnegative,
        "channel_hits": channel_hits,
        "warnings": warnings,
        "summary": (
            "single-spend surface has separated channels"
            if passed else
            "single-spend surface is under-separated or declaration-only"
        ),
    }


def _self_test() -> None:
    good = run_single_spend_carrier_audit([
        "sourceSpend:Real",
        "sourceSpend_nonnegative:0≤sourceSpend",
        "targetChargeSpend:Real",
        "targetChargeSpend_nonnegative:0≤targetChargeSpend",
        "reserveSpend:Real",
        "reserveSpend_nonnegative:0≤reserveSpend",
        "totalBudgetPartition:sourceSpend+targetChargeSpend+reserveSpend≤totalBudget",
        "sameIndexIdentityReceipt:CarrierIdentityReceipt",
        "fixedBeforeAccounting:TimingReceipt",
        "noReuseReceipt:NoReuseReceipt",
    ])
    assert good["passed"], good

    bad = run_single_spend_carrier_audit([
        "sourceClaim:Prop",
        "reserveClaim:Prop",
    ])
    assert not bad["passed"], bad
    assert "partition" in bad["missing_channels"]
    assert "source" in bad["prop_only_blocking_channels"]

    custom_profile = {
        "channel_keywords": {
            "primary": ("primary",),
            "identity": ("identity", "same_index"),
        },
        "spend_variable_keywords": {
            "primary": ("primary_spend", "primarySpend"),
        },
        "blocking_channels": ("primary", "identity"),
    }
    weak_identity = run_single_spend_carrier_audit([
        "primarySpend:Real",
        "primarySpend_nonnegative:0≤primarySpend",
        "sameIndexIdentity:Prop",
    ], profile=custom_profile)
    assert not weak_identity["passed"], weak_identity
    assert "identity" in weak_identity["prop_only_blocking_channels"]

    weak = run_single_spend_carrier_audit([
        "sourceSpend:Real",
        "targetChargeSpend:Real",
        "reserveSpend:Real",
        "totalBudgetPartition:sourceSpend+targetChargeSpend+reserveSpend≤totalBudget",
    ], required_channels=[
        "source",
        "target_charge",
        "reserve",
        "partition",
    ])
    assert not weak["passed"], weak
    assert "source" in weak["missing_nonnegative_spend_channels"]

    prose = run_single_spend_carrier_audit([
        "sourceSpend:source reserve paid by construction",
        "targetChargeSpend:target charge is separated by prose",
        "reserveSpend:reserve exists because the argument says so",
        "totalBudgetPartition:sourceSpend+targetChargeSpend+reserveSpend≤totalBudget",
        "sameIndexIdentityReceipt:CarrierIdentityReceipt",
    ])
    assert not prose["passed"], prose
    assert "source" in prose["free_text_evidence_channels"]
    assert "source" in prose["missing_nonnegative_spend_channels"]


if __name__ == "__main__":
    _self_test()
