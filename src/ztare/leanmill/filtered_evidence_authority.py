"""One-way governed Lean ratification authority for common evidence receipts.

The common evidence layer can carry a formal-kernel binding but cannot
authorize it.  This module is the sole public positive bridge: it resolves
append-only LeanMill records, replays the existing governed theorem validator,
checks the current toolchain and persisted kernel-parity identity, and only
then asks the common layer to construct the theorem-scoped receipt.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from ztare.common.content_bound_evidence import (
    RATIFIED_KERNEL_BINDING_SCHEMA,
    ContentBoundEvidenceReceipt,
    _make_ratified_kernel_evidence,
    _replay_ratified_kernel_evidence,
)
from ztare.common.content_identity import content_sha256, require_sha256_digest
from ztare.leanmill.governed_ratification import (
    resolve_content_addressed_ratification_record,
    validate_governed_ratification_record,
)
from ztare.leanmill.solver.closed_artifact import closure_toolchain_identity


KERNEL_PARITY_SCHEMA = "leanmill.kernel_parity_record.v2"
TOOLCHAIN_SCHEMA = "leanmill.closure_toolchain_identity.v1"


class FilteredEvidenceAuthorityError(ValueError):
    """A failed LeanMill-to-filtered-evidence authority transition."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def _require_digest(value: Any, *, code: str, context: str) -> str:
    try:
        return require_sha256_digest(value, context=context)
    except ValueError as error:
        raise FilteredEvidenceAuthorityError(code, str(error)) from error


def _resolve_kernel_parity_record(
    ledger_ref: str | Path,
    record_sha256: str,
    *,
    repo_root: str | Path | None,
) -> dict[str, Any]:
    digest = _require_digest(
        record_sha256,
        code="kernel_parity_digest_malformed",
        context="kernel parity record",
    )
    path = Path(ledger_ref)
    if not path.is_absolute():
        root = (
            Path(repo_root).resolve()
            if repo_root is not None
            else Path(__file__).resolve().parents[3]
        )
        path = (root / path).resolve()
    if not path.is_file():
        raise FilteredEvidenceAuthorityError(
            "kernel_parity_ledger_unavailable",
            "the kernel-parity ledger is unavailable",
        )
    matches: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise FilteredEvidenceAuthorityError(
                "kernel_parity_ledger_malformed",
                "the kernel-parity ledger is not valid JSONL",
            ) from error
        if isinstance(value, Mapping) and value.get("record_sha256") == digest:
            matches.append(dict(value))
    if len(matches) != 1:
        raise FilteredEvidenceAuthorityError(
            "kernel_parity_identity_not_unique",
            "the parity digest does not select exactly one record",
        )
    parity = matches[0]
    core = {key: value for key, value in parity.items() if key != "record_sha256"}
    if content_sha256(core) != digest:
        raise FilteredEvidenceAuthorityError(
            "kernel_parity_digest_mismatch",
            "the kernel-parity record content does not replay",
        )
    return parity


def _validate_toolchain_identity(
    recorded: Any,
    *,
    current: Mapping[str, Any],
) -> str:
    if not isinstance(recorded, Mapping):
        raise FilteredEvidenceAuthorityError(
            "toolchain_identity_missing",
            "the governed record has no toolchain identity",
        )
    toolchain = dict(recorded)
    if (
        toolchain.get("schema") != TOOLCHAIN_SCHEMA
        or toolchain.get("complete") is not True
    ):
        raise FilteredEvidenceAuthorityError(
            "toolchain_identity_incomplete",
            "the governed record's toolchain identity is incomplete",
        )
    recorded_digest = _require_digest(
        toolchain.get("identity_sha256"),
        code="toolchain_identity_digest_malformed",
        context="governed toolchain identity",
    )
    recorded_core = {
        key: value for key, value in toolchain.items() if key != "identity_sha256"
    }
    if content_sha256(recorded_core) != recorded_digest:
        raise FilteredEvidenceAuthorityError(
            "toolchain_identity_digest_mismatch",
            "the governed toolchain content does not replay",
        )
    current_identity = dict(current)
    if (
        current_identity.get("schema") != TOOLCHAIN_SCHEMA
        or current_identity.get("complete") is not True
    ):
        raise FilteredEvidenceAuthorityError(
            "current_toolchain_identity_incomplete",
            "the current Lean toolchain identity is incomplete",
        )
    current_digest = _require_digest(
        current_identity.get("identity_sha256"),
        code="current_toolchain_identity_digest_malformed",
        context="current Lean toolchain identity",
    )
    current_core = {
        key: value
        for key, value in current_identity.items()
        if key != "identity_sha256"
    }
    if content_sha256(current_core) != current_digest:
        raise FilteredEvidenceAuthorityError(
            "current_toolchain_identity_digest_mismatch",
            "the current Lean toolchain content does not replay",
        )
    if current_digest != recorded_digest:
        raise FilteredEvidenceAuthorityError(
            "stale_toolchain_identity",
            "the governed record belongs to another Lean toolchain identity",
        )
    return recorded_digest


def _validate_parity_binding(
    parity: Mapping[str, Any],
    governed: Mapping[str, Any],
    *,
    parity_digest: str,
    toolchain_digest: str,
) -> None:
    if (
        parity.get("schema") != KERNEL_PARITY_SCHEMA
        or parity.get("record_sha256") != parity_digest
        or parity.get("target") != governed.get("target")
        or parity.get("kernel_blocked") is not False
        or (parity.get("kernel") or {}).get("available") is not True
        or (parity.get("kernel") or {}).get("passed") is not True
        or (parity.get("hand_wired") or {}).get("kc") is not True
        or (parity.get("hand_wired") or {}).get("mnc") is not True
        or parity.get("toolchain_identity_sha256") != toolchain_digest
    ):
        raise FilteredEvidenceAuthorityError(
            "kernel_parity_not_positive",
            "the kernel-parity record is not a positive matching decision",
        )
    for field in (
        "goal_sha256",
        "source_sha256",
        "recompilable_probe_sha256",
        "posed_target_signature_sha256",
        "closed_target_signature_sha256",
    ):
        if parity.get(field) != governed.get(field):
            raise FilteredEvidenceAuthorityError(
                "kernel_parity_crossed_certificate",
                f"the parity record crossed governed field {field}",
            )
    validation = governed.get("solver_validation")
    validation = validation if isinstance(validation, Mapping) else {}
    if (
        parity.get("final_authority_roster_sha256")
        != validation.get("final_authority_roster_sha256")
        or parity.get("final_authority_disposition")
        != validation.get("final_authority_disposition")
    ):
        raise FilteredEvidenceAuthorityError(
            "kernel_parity_crossed_governance",
            "the parity record crossed the governed authority decision",
        )


def _binding_from_governed_records(
    governed: Mapping[str, Any],
    *,
    governed_record_sha256: str,
    parity: Mapping[str, Any],
    parity_record_sha256: str,
    current_toolchain: Mapping[str, Any],
) -> dict[str, Any]:
    if governed.get("kernel_parity_record_persisted") is not True:
        raise FilteredEvidenceAuthorityError(
            "kernel_parity_not_persisted",
            "the governed record does not attest durable parity persistence",
        )
    if governed.get("kernel_parity_record_sha256") != parity_record_sha256:
        raise FilteredEvidenceAuthorityError(
            "kernel_parity_crossed_certificate",
            "the governed and parity record identities differ",
        )
    toolchain_digest = _validate_toolchain_identity(
        governed.get("toolchain_identity"),
        current=current_toolchain,
    )
    _validate_parity_binding(
        parity,
        governed,
        parity_digest=parity_record_sha256,
        toolchain_digest=toolchain_digest,
    )
    validation = governed.get("solver_validation")
    validation = validation if isinstance(validation, Mapping) else {}
    governance = governed.get("governance")
    governance = governance if isinstance(governance, Mapping) else {}
    receipts = validation.get("receipts")
    receipts = receipts if isinstance(receipts, Mapping) else {}
    axiom = receipts.get("axiom_allowlist_receipt")
    if not isinstance(axiom, Mapping):
        raise FilteredEvidenceAuthorityError(
            "axiom_receipt_missing",
            "the governed record has no axiom allowlist receipt",
        )
    core = {
        "schema": RATIFIED_KERNEL_BINDING_SCHEMA,
        "governed_record_sha256": governed_record_sha256,
        "target_id": str(governed.get("target") or ""),
        "target_signature_sha256": str(
            governed.get("posed_target_signature_sha256") or ""
        ),
        "source_sha256": str(governed.get("source_sha256") or ""),
        "proof_sha256": str(governed.get("proof_sha256") or ""),
        "goal_sha256": str(governed.get("goal_sha256") or ""),
        "toolchain_identity_sha256": toolchain_digest,
        "kernel_parity_record_sha256": parity_record_sha256,
        "solver_validation_sha256": content_sha256(validation),
        "governance_sha256": content_sha256(governance),
        "axiom_allowlist_receipt_sha256": content_sha256(axiom),
    }
    for field, value in core.items():
        if field not in {"schema", "target_id"}:
            _require_digest(
                value,
                code="governed_identity_digest_malformed",
                context=f"governed {field}",
            )
    if not core["target_id"]:
        raise FilteredEvidenceAuthorityError(
            "governed_target_empty",
            "the governed target identity must be nonempty",
        )
    return {**core, "binding_sha256": content_sha256(core)}


def make_content_bound_evidence_from_governed_ratification(
    *,
    certificate_ledger: str | Path,
    governed_record_sha256: str,
    parity_ledger: str | Path,
    target: str,
    expected_signature: str,
    posed_source: str,
    proof_text: str,
    goal: str,
    lean_root: str | Path,
    repo_root: str | Path | None = None,
    expected_provider: str | None = None,
) -> ContentBoundEvidenceReceipt:
    """Project one exact governed theorem into theorem-scoped evidence."""

    record_digest = _require_digest(
        governed_record_sha256,
        code="governed_record_digest_malformed",
        context="governed ratification record",
    )
    try:
        _path, selected = resolve_content_addressed_ratification_record(
            certificate_ledger,
            record_digest,
            repo_root=repo_root,
        )
        governed = validate_governed_ratification_record(
            selected,
            target=target,
            expected_signature=expected_signature,
            posed_source=posed_source,
            proof_text=proof_text,
            goal=goal,
            expected_provider=expected_provider,
        )
    except ValueError as error:
        raise FilteredEvidenceAuthorityError(
            "governed_ratification_replay_failed",
            str(error),
        ) from error
    if content_sha256(governed) != record_digest:
        raise FilteredEvidenceAuthorityError(
            "governed_record_digest_mismatch",
            "the governed ratification content does not replay",
        )
    parity_digest = _require_digest(
        governed.get("kernel_parity_record_sha256"),
        code="kernel_parity_digest_malformed",
        context="governed kernel parity record",
    )
    parity = _resolve_kernel_parity_record(
        parity_ledger,
        parity_digest,
        repo_root=repo_root,
    )
    current_toolchain = closure_toolchain_identity(lean_root)
    binding = _binding_from_governed_records(
        governed,
        governed_record_sha256=record_digest,
        parity=parity,
        parity_record_sha256=parity_digest,
        current_toolchain=current_toolchain,
    )
    return _make_ratified_kernel_evidence(binding)


def replay_content_bound_evidence_from_governed_ratification(
    receipt: ContentBoundEvidenceReceipt,
    **ratification: Any,
) -> ContentBoundEvidenceReceipt:
    """Replay a formal receipt through the same external authority records."""

    expected = make_content_bound_evidence_from_governed_ratification(
        **ratification
    )
    if receipt != expected:
        raise FilteredEvidenceAuthorityError(
            "formal_kernel_receipt_mismatch",
            "the formal receipt differs from the governed record projection",
        )
    return _replay_ratified_kernel_evidence(receipt)


__all__ = [
    "FilteredEvidenceAuthorityError",
    "make_content_bound_evidence_from_governed_ratification",
    "replay_content_bound_evidence_from_governed_ratification",
]
