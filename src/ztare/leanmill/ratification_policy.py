"""Finite authority roster for theorem ratification.

Candidate producers and theory adapters are extensible.  Final theorem credit
is decided only by the authorities named here; adding an authority is a policy
change with a new roster digest, not a runtime plugin action.
"""

from __future__ import annotations

import hashlib


ANTI_LAUNDERING_ORGAN_NAMES = frozenset({
    "v33_consequence_exposure_gate",
    "v33_currency_mismatch_gate",
    "v33_indirect_leakage_gate",
    "v33_paraphrase_gate",
    "v33_preflight_risk_detector",
    "v33_single_lemma_exact_gate",
})

TARGET_GOVERNANCE_AUTHORITIES = frozenset({
    *ANTI_LAUNDERING_ORGAN_NAMES,
    "target_identity",
    "target_declaration",
    "target_signature",
    "statement_integrity",
    "canonical_reelaboration",
})

FINAL_RATIFICATION_RECEIPT_AUTHORITIES = frozenset({
    "kernel_compile_receipt",
    "matched_negative_control_receipt",
    "axiom_allowlist_receipt",
})

FINAL_RATIFICATION_AUTHORITIES = frozenset({
    *TARGET_GOVERNANCE_AUTHORITIES,
    *FINAL_RATIFICATION_RECEIPT_AUTHORITIES,
})


def _roster_sha256(authorities: frozenset[str]) -> str:
    return hashlib.sha256(
        "\n".join(sorted(authorities)).encode("utf-8")
    ).hexdigest()


TARGET_GOVERNANCE_AUTHORITY_ROSTER_SHA256 = _roster_sha256(
    TARGET_GOVERNANCE_AUTHORITIES
)
FINAL_RATIFICATION_AUTHORITY_ROSTER_SHA256 = _roster_sha256(
    FINAL_RATIFICATION_AUTHORITIES
)
