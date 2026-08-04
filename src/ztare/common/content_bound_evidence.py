"""Immutable content-bound proof-evidence identities for common compilers."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import json
from typing import Any, Mapping

from ztare.common.content_identity import (
    canonical_json,
    content_sha256,
    require_sha256_digest,
)


EVIDENCE_RECEIPT_SCHEMA = "ztare.content_bound_evidence_receipt.v1"
RATIFIED_KERNEL_BINDING_SCHEMA = "ztare.ratified_kernel_binding.v1"
FORMAL_KERNEL_CLAIM_ID = "lean_theorem_ratified"
FORMAL_KERNEL_SCOPE_ID = "exact_lean_target_signature"


class ContentBoundEvidenceError(ValueError):
    """A typed identity failure in a content-bound evidence receipt."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


class EvidenceAuthority(str, Enum):
    """The lifecycle that owns the proposition carried by a receipt."""

    ADAPTER_EXACT = "adapter_exact"
    FILTERED_COMPILER = "filtered_obstruction_compiler"
    FINITE_EXPERIMENT = "finite_experiment"
    FORMAL_KERNEL = "formal_kernel"


@dataclass(frozen=True)
class ContentBoundEvidenceReceipt:
    """One proposition bound to context, subject, evidence, and authority."""

    schema: str
    claim_id: str
    subject_id: str
    context_sha256: str
    authority: EvidenceAuthority
    scope_id: str
    conclusion_json: str
    evidence_sha256: str
    receipt_sha256: str
    authority_binding_json: str | None = None

    def conclusion(self) -> dict[str, Any]:
        value = json.loads(self.conclusion_json)
        if not isinstance(value, dict):
            raise ContentBoundEvidenceError(
                "evidence_conclusion_not_mapping",
                "the evidence conclusion must be a JSON object",
            )
        return value

    def core_payload(self) -> dict[str, Any]:
        authority = (
            self.authority.value
            if isinstance(self.authority, EvidenceAuthority)
            else self.authority
        )
        payload = {
            "schema": self.schema,
            "claim_id": self.claim_id,
            "subject_id": self.subject_id,
            "context_sha256": self.context_sha256,
            "authority": authority,
            "scope_id": self.scope_id,
            "conclusion": self.conclusion(),
            "evidence_sha256": self.evidence_sha256,
        }
        if self.authority_binding_json is not None:
            try:
                binding = json.loads(self.authority_binding_json)
            except json.JSONDecodeError as error:
                raise ContentBoundEvidenceError(
                    "formal_kernel_binding_malformed",
                    "the formal-kernel binding is not valid JSON",
                ) from error
            payload["authority_binding"] = binding
        return payload

    def to_dict(self) -> dict[str, Any]:
        return {**self.core_payload(), "receipt_sha256": self.receipt_sha256}


def _replay_ratified_kernel_binding_json(binding_json: str) -> dict[str, Any]:
    """Replay the immutable projection of a governed LeanMill record.

    This checks only the carried identity shape.  The LeanMill bridge remains
    responsible for resolving the referenced append-only records and replaying
    kernel, axiom, source, proof, goal, and toolchain authority.
    """

    try:
        binding = json.loads(binding_json)
    except (TypeError, json.JSONDecodeError) as error:
        raise ContentBoundEvidenceError(
            "formal_kernel_binding_malformed",
            "the formal-kernel binding is not valid JSON",
        ) from error
    expected_fields = {
        "schema",
        "governed_record_sha256",
        "target_id",
        "target_signature_sha256",
        "source_sha256",
        "proof_sha256",
        "goal_sha256",
        "toolchain_identity_sha256",
        "kernel_parity_record_sha256",
        "solver_validation_sha256",
        "governance_sha256",
        "axiom_allowlist_receipt_sha256",
        "binding_sha256",
    }
    if not isinstance(binding, dict) or set(binding) != expected_fields:
        raise ContentBoundEvidenceError(
            "formal_kernel_binding_fields_mismatch",
            "the formal-kernel binding has the wrong identity fields",
        )
    if binding.get("schema") != RATIFIED_KERNEL_BINDING_SCHEMA:
        raise ContentBoundEvidenceError(
            "formal_kernel_binding_schema_mismatch",
            "the formal-kernel binding schema is not recognized",
        )
    target = binding.get("target_id")
    if not isinstance(target, str) or not target.strip():
        raise ContentBoundEvidenceError(
            "formal_kernel_binding_target_empty",
            "the formal-kernel target identity must be nonempty",
        )
    for field_name in sorted(expected_fields - {"schema", "target_id"}):
        try:
            require_sha256_digest(
                binding.get(field_name),
                context=f"formal-kernel {field_name}",
            )
        except ValueError as error:
            raise ContentBoundEvidenceError(
                "formal_kernel_binding_digest_malformed",
                str(error),
            ) from error
    core = {
        key: value for key, value in binding.items() if key != "binding_sha256"
    }
    if content_sha256(core) != binding["binding_sha256"]:
        raise ContentBoundEvidenceError(
            "formal_kernel_binding_digest_mismatch",
            "the formal-kernel binding content does not replay",
        )
    if canonical_json(binding) != binding_json:
        raise ContentBoundEvidenceError(
            "formal_kernel_binding_not_canonical",
            "the formal-kernel binding changed canonical identity",
        )
    return binding


def _replay_content_bound_evidence(
    receipt: ContentBoundEvidenceReceipt,
    *,
    allow_ratified_kernel: bool,
) -> ContentBoundEvidenceReceipt:
    """Replay one receipt after the caller declares its authority boundary."""

    if receipt.schema != EVIDENCE_RECEIPT_SCHEMA:
        raise ContentBoundEvidenceError(
            "evidence_schema_mismatch",
            "the evidence receipt schema is not recognized",
        )
    if not isinstance(receipt.authority, EvidenceAuthority):
        raise ContentBoundEvidenceError(
            "evidence_authority_unknown",
            "the evidence authority is not in the closed authority category",
        )
    formal_binding: dict[str, Any] | None = None
    if receipt.authority is EvidenceAuthority.FORMAL_KERNEL:
        if receipt.authority_binding_json is None:
            raise ContentBoundEvidenceError(
                "formal_kernel_binding_missing",
                "formal-kernel evidence requires a governed ratification binding",
            )
        formal_binding = _replay_ratified_kernel_binding_json(
            receipt.authority_binding_json
        )
        if not allow_ratified_kernel:
            raise ContentBoundEvidenceError(
                "formal_kernel_authority_requires_ratification",
                "formal-kernel evidence must be replayed by the LeanMill "
                "authority bridge",
            )
    elif receipt.authority_binding_json is not None:
        raise ContentBoundEvidenceError(
            "unexpected_authority_binding",
            "only formal-kernel evidence may carry a ratification binding",
        )
    for field_name, value in (
        ("claim_id", receipt.claim_id),
        ("subject_id", receipt.subject_id),
        ("scope_id", receipt.scope_id),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ContentBoundEvidenceError(
                "evidence_identity_empty",
                f"{field_name} must be a nonempty string",
            )
    try:
        require_sha256_digest(
            receipt.context_sha256,
            context="evidence context",
        )
        require_sha256_digest(
            receipt.evidence_sha256,
            context="evidence artifact",
        )
        require_sha256_digest(
            receipt.receipt_sha256,
            context="evidence receipt",
        )
    except ValueError as error:
        raise ContentBoundEvidenceError(
            "evidence_digest_malformed",
            str(error),
        ) from error
    try:
        conclusion = receipt.conclusion()
    except (
        TypeError,
        json.JSONDecodeError,
        ContentBoundEvidenceError,
    ) as error:
        if isinstance(error, ContentBoundEvidenceError):
            raise
        raise ContentBoundEvidenceError(
            "evidence_conclusion_malformed",
            "the evidence conclusion is not valid JSON",
        ) from error
    if canonical_json(conclusion) != receipt.conclusion_json:
        raise ContentBoundEvidenceError(
            "evidence_conclusion_not_canonical",
            "the evidence conclusion changed canonical identity",
        )
    if formal_binding is not None:
        expected_conclusion = {
            "ratified": True,
            "target": formal_binding["target_id"],
            "target_signature_sha256": formal_binding[
                "target_signature_sha256"
            ],
        }
        if (
            receipt.claim_id != FORMAL_KERNEL_CLAIM_ID
            or receipt.subject_id != formal_binding["target_id"]
            or receipt.context_sha256 != formal_binding["binding_sha256"]
            or receipt.scope_id != FORMAL_KERNEL_SCOPE_ID
            or conclusion != expected_conclusion
            or receipt.evidence_sha256
            != formal_binding["governed_record_sha256"]
        ):
            raise ContentBoundEvidenceError(
                "formal_kernel_receipt_scope_mismatch",
                "the formal-kernel receipt exceeds or crosses its exact Lean target",
            )
    if content_sha256(receipt.core_payload()) != receipt.receipt_sha256:
        raise ContentBoundEvidenceError(
            "evidence_receipt_digest_mismatch",
            "the evidence receipt content does not replay",
        )
    return receipt


def replay_content_bound_evidence(
    receipt: ContentBoundEvidenceReceipt,
) -> ContentBoundEvidenceReceipt:
    """Replay ordinary evidence; formal authority stays LeanMill-owned."""

    return _replay_content_bound_evidence(
        receipt,
        allow_ratified_kernel=False,
    )


def _make_ratified_kernel_evidence(
    binding: Mapping[str, Any],
) -> ContentBoundEvidenceReceipt:
    """Internal constructor used only after LeanMill validates its records."""

    raw_binding = dict(binding)
    binding_json = canonical_json(raw_binding)
    replayed = _replay_ratified_kernel_binding_json(binding_json)
    conclusion_json = canonical_json({
        "ratified": True,
        "target": replayed["target_id"],
        "target_signature_sha256": replayed["target_signature_sha256"],
    })
    provisional = ContentBoundEvidenceReceipt(
        schema=EVIDENCE_RECEIPT_SCHEMA,
        claim_id=FORMAL_KERNEL_CLAIM_ID,
        subject_id=replayed["target_id"],
        context_sha256=replayed["binding_sha256"],
        authority=EvidenceAuthority.FORMAL_KERNEL,
        scope_id=FORMAL_KERNEL_SCOPE_ID,
        conclusion_json=conclusion_json,
        evidence_sha256=replayed["governed_record_sha256"],
        receipt_sha256="0" * 64,
        authority_binding_json=binding_json,
    )
    receipt = replace(
        provisional,
        receipt_sha256=content_sha256(provisional.core_payload()),
    )
    return _replay_content_bound_evidence(
        receipt,
        allow_ratified_kernel=True,
    )


def _replay_ratified_kernel_evidence(
    receipt: ContentBoundEvidenceReceipt,
) -> ContentBoundEvidenceReceipt:
    """Internal structural replay after LeanMill replays external authority."""

    return _replay_content_bound_evidence(
        receipt,
        allow_ratified_kernel=True,
    )


def make_content_bound_evidence(
    *,
    claim_id: str,
    subject_id: str,
    context_sha256: str,
    authority: EvidenceAuthority,
    scope_id: str,
    conclusion: Mapping[str, Any],
    evidence_sha256: str,
) -> ContentBoundEvidenceReceipt:
    """Create and replay one canonical evidence receipt."""

    if authority is EvidenceAuthority.FORMAL_KERNEL:
        raise ContentBoundEvidenceError(
            "formal_kernel_authority_requires_ratification",
            "formal-kernel evidence must be constructed by the LeanMill "
            "authority bridge",
        )

    conclusion_json = canonical_json(dict(conclusion))
    provisional = ContentBoundEvidenceReceipt(
        schema=EVIDENCE_RECEIPT_SCHEMA,
        claim_id=claim_id,
        subject_id=subject_id,
        context_sha256=context_sha256,
        authority=authority,
        scope_id=scope_id,
        conclusion_json=conclusion_json,
        evidence_sha256=evidence_sha256,
        receipt_sha256="0" * 64,
    )
    receipt = replace(
        provisional,
        receipt_sha256=content_sha256(provisional.core_payload()),
    )
    return replay_content_bound_evidence(receipt)


__all__ = [
    "ContentBoundEvidenceReceipt",
    "EVIDENCE_RECEIPT_SCHEMA",
    "EvidenceAuthority",
    "ContentBoundEvidenceError",
    "FORMAL_KERNEL_CLAIM_ID",
    "FORMAL_KERNEL_SCOPE_ID",
    "RATIFIED_KERNEL_BINDING_SCHEMA",
    "make_content_bound_evidence",
    "replay_content_bound_evidence",
]
