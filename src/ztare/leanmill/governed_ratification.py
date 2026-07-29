"""Reusable validation for one carried theorem's governed Lean certificate."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from ztare.leanmill.lean_source import (
    extract_signature,
    open_decl_for_ratification,
    strip_comments,
)
from ztare.leanmill.theory_ir import content_hash
from ztare.leanmill.solver.closed_artifact import finalized_ratification_eligible


def normalized_target_signature(source: str, target: str) -> str:
    """Return a whitespace-normalized, comment-free target signature."""

    signature = extract_signature(source or "", target)
    return " ".join(strip_comments(signature or "").split())


def _positive_receipt(value: Any, *, label: str) -> Mapping[str, Any]:
    if (
        not isinstance(value, Mapping)
        or value.get("available") is not True
        or value.get("passed") is not True
    ):
        raise ValueError(f"governed ratification {label} did not pass")
    tail = str(value.get("tail") or "").lower()
    if any(word in tail for word in ("fail-open", "error", "skipped", "inconclusive")):
        raise ValueError(f"governed ratification {label} is not positive")
    return value


def validate_governed_ratification_record(
    record: Mapping[str, Any],
    *,
    target: str,
    expected_signature: str,
    posed_source: str,
    proof_text: str,
    goal: str,
    expected_provider: str | None = None,
) -> dict[str, Any]:
    """Validate one exact append-only carried-theorem certificate.

    The caller already owns the formalization bridge.  This function checks
    that the bounded theorem-ratification executor governed those exact source,
    proof, target, and goal bytes and produced every positive trust receipt.
    """

    row = dict(record)
    governance = row.get("governance")
    governance = governance if isinstance(governance, Mapping) else {}
    kernel = governance.get("governance_kernel")
    kernel = kernel if isinstance(kernel, Mapping) else {}
    integrity = governance.get("statement_integrity")
    integrity = integrity if isinstance(integrity, Mapping) else {}
    discrimination = (
        (((governance.get("margin_of_safety") or {}).get("tests") or {}).get(
            "conclusion_discrimination"
        ) or {})
        if isinstance(governance.get("margin_of_safety"), Mapping)
        else {}
    )
    detail = discrimination.get("detail")
    detail = detail if isinstance(detail, Mapping) else {}
    validation = row.get("solver_validation")
    validation = validation if isinstance(validation, Mapping) else {}
    receipts = validation.get("receipts")
    receipts = receipts if isinstance(receipts, Mapping) else {}
    probe = str(row.get("recompilable_probe") or "")
    carried_proof = str(row.get("proof_text") or "").strip()
    expected_proof = str(proof_text or "").strip()
    expected_statement = " ".join(str(expected_signature or "").split())
    expected_statement_hash = hashlib.sha256(
        expected_statement.encode("utf-8")
    ).hexdigest()

    if (
        row.get("certificate_schema") != "leanmill.governed_closure.v2"
        or row.get("target") != target
        or row.get("outcome") != "closed"
        or row.get("checker") != "lean_lake"
        or row.get("ratification_only") is not True
        or kernel.get("available") is not True
        or kernel.get("passed") is not True
        or integrity.get("ok") is not True
        or governance.get("integrity_unverified") is True
        or detail.get("differential") != "confirmed"
        or (row.get("matched_negative_control") or {}).get("passed") is not True
        or not finalized_ratification_eligible(dict(validation))
        or validation.get("positive_axiom_receipt_required") is not True
        or validation.get("axiom_tier") != "kernel_pure"
        or not probe
        or not str(row.get("closure_lean") or "")
        or carried_proof != expected_proof
        or row.get("posed_target_signature_sha256") != expected_statement_hash
        or row.get("closed_target_signature_sha256") != expected_statement_hash
        or (expected_provider is not None and row.get("provider") != expected_provider)
    ):
        raise ValueError("closure record is not the required governed ratification")

    for name in (
        "kernel_compile_receipt",
        "matched_negative_control_receipt",
        "governance_kernel_receipt",
        "axiom_allowlist_receipt",
    ):
        _positive_receipt(receipts.get(name), label=name)

    if row.get("source_sha256") != hashlib.sha256(
        (posed_source or "").encode("utf-8")
    ).hexdigest():
        raise ValueError("closure record crossed the posed source")
    if row.get("proof_sha256") != hashlib.sha256(
        expected_proof.encode("utf-8")
    ).hexdigest():
        raise ValueError("closure record crossed the carried proof")
    if row.get("goal_sha256") != hashlib.sha256(
        (goal or "").encode("utf-8")
    ).hexdigest():
        raise ValueError("closure record crossed the ratification goal")
    if row.get("recompilable_probe_sha256") != hashlib.sha256(
        probe.encode("utf-8")
    ).hexdigest():
        raise ValueError("closure record probe digest mismatch")
    if normalized_target_signature(probe, target) != expected_statement:
        raise ValueError("closure record proves a different target signature")
    _opened, recorded_proof = open_decl_for_ratification(probe, target)
    if recorded_proof.strip() != expected_proof:
        raise ValueError("closure record carries different proof bytes")
    return row


def resolve_content_addressed_ratification_record(
    ledger_ref: str | Path,
    record_sha256: str,
    *,
    repo_root: str | Path | None = None,
) -> tuple[Path, dict[str, Any]]:
    """Resolve exactly one JSONL certificate by its canonical record digest."""

    digest = str(record_sha256 or "")
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise ValueError("ratification record digest is malformed")
    path = Path(ledger_ref)
    if not path.is_absolute():
        root = (
            Path(repo_root).resolve()
            if repo_root is not None
            else Path(__file__).resolve().parents[3]
        )
        path = (root / path).resolve()
    if not path.is_file():
        raise ValueError("ratification certificate ledger is unavailable")
    matches: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError("ratification certificate ledger is malformed") from exc
        if isinstance(value, Mapping) and content_hash(value) == digest:
            matches.append(dict(value))
    if len(matches) != 1:
        raise ValueError("ratification record digest does not select exactly one record")
    return path, matches[0]


__all__ = [
    "normalized_target_signature",
    "resolve_content_addressed_ratification_record",
    "validate_governed_ratification_record",
]
