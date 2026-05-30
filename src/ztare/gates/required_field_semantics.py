"""Shared required-field text semantics for deterministic gates.

The helper is conservative: exact falsey tokens are missing, and proof-bearing
fields reject explicit non-claim language.  It does not use prefix matching.
"""
from __future__ import annotations

from typing import Any


FALSE_EXACT_MATCHES = {
    "",
    "0",
    "absent",
    "false",
    "missing",
    "no",
    "none",
    "not provided",
    "not supplied",
    "null",
    "owed",
    "todo",
    "unknown",
    "unpaid",
}

PROOF_BEARING_FIELD_TOKENS = (
    "bound",
    "card",
    "eq",
    "equality",
    "exists",
    "iff",
    "injective",
    "membership",
    "proof",
    "source",
    "totality",
)

NON_CLAIM_PHRASES = (
    "does not claim",
    "is not claimed",
    "no injectivity is claimed",
    "not applicable",
    "not needed",
    "not required",
    "not used",
    "without claiming",
)


def is_present(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() not in FALSE_EXACT_MATCHES
    return value not in (None, "", [], {}, False)


def is_proof_bearing_field(field: str) -> bool:
    lowered = field.lower()
    return any(token in lowered for token in PROOF_BEARING_FIELD_TOKENS)


def has_non_claim_language(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    lowered = " ".join(value.lower().split())
    return any(phrase in lowered for phrase in NON_CLAIM_PHRASES)


def is_semantically_present(value: Any, *, field: str = "") -> bool:
    if not is_present(value):
        return False
    if field and is_proof_bearing_field(field) and has_non_claim_language(value):
        return False
    return True


def self_test() -> None:
    assert not is_semantically_present("missing", field="injective_on_domain")
    assert is_semantically_present("missing lemma", field="artifact_note")
    assert not is_semantically_present(
        "no injectivity is claimed; multiplicity is explicit",
        field="injective_on_domain",
    )
    assert not is_semantically_present(
        "not used; this bridge preserves multiplicity",
        field="card_image_eq_domain_card",
    )
    assert is_semantically_present(
        "Finset.card_image_of_injective h",
        field="card_image_eq_domain_card",
    )

