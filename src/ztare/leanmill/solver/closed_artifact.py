"""Identity and credit rules for one finalized Lean closure artifact."""

from __future__ import annotations

import hashlib
import json
import subprocess
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

from ztare.leanmill.lean_source import resolve_theorem_target
from ztare.leanmill.ratification_policy import (
    FINAL_RATIFICATION_AUTHORITIES,
    FINAL_RATIFICATION_AUTHORITY_ROSTER_SHA256,
    FINAL_RATIFICATION_RECEIPT_AUTHORITIES,
    TARGET_GOVERNANCE_AUTHORITIES,
    TARGET_GOVERNANCE_AUTHORITY_ROSTER_SHA256,
)


SCHEMA = "leanmill.verified_closure_artifact.v2"
TOOLCHAIN_SCHEMA = "leanmill.closure_toolchain_identity.v1"
TOOLCHAIN_PROBE_TIMEOUT_SECONDS = 30
KERNEL_PARITY_SCHEMA = "leanmill.kernel_parity_record.v2"


def build_verified_closure_artifact(
    target_name: str,
    closure_source: str,
    posed_source: str,
) -> dict[str, Any] | None:
    if not target_name or not closure_source.strip() or not posed_source.strip():
        return None
    try:
        posed = resolve_theorem_target(posed_source, target_name)
        closed = resolve_theorem_target(closure_source, target_name)
        from ztare.leanmill.governed_ratification import normalized_target_signature

        posed_signature = normalized_target_signature(posed_source, target_name)
        closed_signature = normalized_target_signature(closure_source, target_name)
    except Exception:
        return None
    if (
        posed is None
        or closed is None
        or posed.qualified_name != closed.qualified_name
        or not posed_signature
        or posed_signature != closed_signature
    ):
        return None
    return {
        "schema": SCHEMA,
        "target_name": target_name,
        "target_qualified_name": closed.qualified_name,
        "closure_source": closure_source,
        "posed_source": posed_source,
        "closure_sha256": _sha256(closure_source),
        "posed_sha256": _sha256(posed_source),
        "posed_target_signature_sha256": _sha256(posed_signature),
        "closed_target_signature_sha256": _sha256(closed_signature),
    }


def validate_verified_closure_artifact(
    artifact: object,
    target_name: str,
) -> dict[str, Any] | None:
    if not isinstance(artifact, dict) or artifact.get("schema") != SCHEMA:
        return None
    if artifact.get("target_name") != target_name:
        return None
    identity = str(
        artifact.get("target_qualified_name") or artifact.get("target_name") or ""
    )
    closure_source = artifact.get("closure_source")
    posed_source = artifact.get("posed_source")
    if not identity or not isinstance(closure_source, str) or not isinstance(posed_source, str):
        return None
    try:
        posed = resolve_theorem_target(posed_source, identity)
        closed = resolve_theorem_target(closure_source, identity)
        from ztare.leanmill.governed_ratification import normalized_target_signature

        posed_signature = normalized_target_signature(posed_source, identity)
        closed_signature = normalized_target_signature(closure_source, identity)
    except Exception:
        return None
    if (
        posed is None
        or closed is None
        or posed.qualified_name != identity
        or closed.qualified_name != identity
        or not posed_signature
        or posed_signature != closed_signature
        or _sha256(closure_source) != artifact.get("closure_sha256")
        or _sha256(posed_source) != artifact.get("posed_sha256")
        or _sha256(posed_signature)
        != artifact.get("posed_target_signature_sha256")
        or _sha256(closed_signature)
        != artifact.get("closed_target_signature_sha256")
    ):
        return None
    return artifact


def dag_governance_axes(validation: dict[str, Any]) -> tuple[bool, bool, bool]:
    receipts = validation.get("receipts") or {}
    kernel = receipts.get("kernel_compile_receipt") or {}
    matched = receipts.get("matched_negative_control_receipt") or {}
    return (
        bool(kernel.get("available") is True and kernel.get("passed") is True),
        bool(
            matched.get("available") is True
            and matched.get("passed") is True
            and matched.get("admitted_under_policy") is True
        ),
        bool(validation.get("credit_ready_at_solver_layer")),
    )


def governance_ratification_eligible(governance: object) -> bool:
    if not isinstance(governance, dict):
        return False
    kernel = governance.get("governance_kernel")
    integrity = governance.get("statement_integrity")
    required = kernel.get("required_authorities") if isinstance(kernel, dict) else None
    disposition = kernel.get("authority_disposition") if isinstance(kernel, dict) else None
    return bool(
        governance.get("integrity_unverified") is not True
        and isinstance(kernel, dict)
        and kernel.get("available") is True
        and kernel.get("passed") is True
        and kernel.get("policy_profile") == "target_ratification"
        and kernel.get("authority_roster_sha256")
        == TARGET_GOVERNANCE_AUTHORITY_ROSTER_SHA256
        and isinstance(required, list)
        and set(required) == TARGET_GOVERNANCE_AUTHORITIES
        and isinstance(disposition, dict)
        and set(disposition) == TARGET_GOVERNANCE_AUTHORITIES
        and all(
            disposition.get(authority) == "passed"
            for authority in TARGET_GOVERNANCE_AUTHORITIES
        )
        and isinstance(integrity, dict)
        and integrity.get("ok") is True
    )


def authority_receipts_eligible(validation: object) -> bool:
    """Require every non-governance authority receipt to be explicitly positive."""

    if not isinstance(validation, dict):
        return False
    receipts = validation.get("receipts")
    if not isinstance(receipts, dict):
        return False
    kernel_compile = receipts.get("kernel_compile_receipt")
    matched_control = receipts.get("matched_negative_control_receipt")
    axiom_allowlist = receipts.get("axiom_allowlist_receipt")
    return bool(
        isinstance(kernel_compile, dict)
        and kernel_compile.get("available") is True
        and kernel_compile.get("passed") is True
        and isinstance(matched_control, dict)
        and matched_control.get("available") is True
        and matched_control.get("passed") is True
        and isinstance(axiom_allowlist, dict)
        and axiom_allowlist.get("available") is True
        and axiom_allowlist.get("passed") is True
    )


def _receipt_disposition(receipt: object) -> str:
    if (
        not isinstance(receipt, dict)
        or receipt.get("available") is not True
        or receipt.get("passed") is None
    ):
        return "unavailable"
    return "passed" if receipt.get("passed") is True else "rejected"


def finalized_ratification_eligible(validation: object) -> bool:
    """Validate the complete finite authority algebra on a final artifact."""

    if not isinstance(validation, dict):
        return False
    disposition = validation.get("final_authority_disposition")
    receipts = validation.get("receipts")
    governance_receipt = (
        receipts.get("governance_kernel_receipt")
        if isinstance(receipts, dict)
        else None
    )
    return bool(
        validation.get("finalized_at_closed_artifact_boundary") is True
        and validation.get("final_ratification_eligible") is True
        and validation.get("credit_ready_at_solver_layer") is True
        and validation.get("final_authority_roster_sha256")
        == FINAL_RATIFICATION_AUTHORITY_ROSTER_SHA256
        and set(validation.get("final_required_authorities") or [])
        == FINAL_RATIFICATION_AUTHORITIES
        and isinstance(disposition, dict)
        and set(disposition) == FINAL_RATIFICATION_AUTHORITIES
        and all(
            disposition.get(authority) == "passed"
            for authority in FINAL_RATIFICATION_AUTHORITIES
        )
        and authority_receipts_eligible(validation)
        and isinstance(governance_receipt, dict)
        and governance_receipt.get("available") is True
        and governance_receipt.get("passed") is True
        and governance_receipt.get("authority_roster_sha256")
        == TARGET_GOVERNANCE_AUTHORITY_ROSTER_SHA256
    )


def finalized_artifact_outcome(validation: object) -> str:
    """Project the finite final-authority algebra to one stable outcome label."""

    if finalized_ratification_eligible(validation):
        return "closed"
    if not isinstance(validation, dict):
        return "uncredited_no_validation"
    required = set(validation.get("final_required_authorities") or [])
    disposition = validation.get("final_authority_disposition")
    if (
        required != FINAL_RATIFICATION_AUTHORITIES
        or not isinstance(disposition, dict)
        or set(disposition) != FINAL_RATIFICATION_AUTHORITIES
    ):
        return "governance_unavailable"
    rejected = {
        authority
        for authority, status in disposition.items()
        if status == "rejected"
    }
    unavailable = {
        authority
        for authority, status in disposition.items()
        if status == "unavailable"
    }
    if unavailable == {"axiom_allowlist_receipt"}:
        return "rejected_axiom_inconclusive"
    if unavailable == {"matched_negative_control_receipt"}:
        return "rejected_mnc_inconclusive"
    if unavailable:
        return "governance_unavailable"
    if rejected == {"kernel_compile_receipt"}:
        return "rejected_compile"
    if rejected == {"axiom_allowlist_receipt"}:
        return "rejected_banned_axiom"
    if rejected == {"matched_negative_control_receipt"}:
        return "rejected_mnc_leakage"
    if rejected and rejected.issubset(TARGET_GOVERNANCE_AUTHORITIES):
        return "rejected_governance"
    if rejected:
        return "rejected_multiple_authorities"
    return "uncredited_validated_closure_dropped"


def finalize_solver_validation(
    solver_validation: object,
    governance: object,
) -> dict[str, Any]:
    """Resolve deferred producer receipts at the closure authority boundary.

    The solver owns compilation and matched-control receipts, while the common
    closed-artifact finalizer owns the authoritative governance kernel.  A
    release certificate must carry one completed validation algebra rather
    than the producer's ``passed: None`` placeholders beside a separate
    governance report.
    """

    validation = (
        deepcopy(solver_validation) if isinstance(solver_validation, dict) else {}
    )
    receipts = validation.get("receipts")
    receipts = deepcopy(receipts) if isinstance(receipts, dict) else {}
    governed = governance if isinstance(governance, dict) else {}
    kernel = governed.get("governance_kernel")
    kernel = kernel if isinstance(kernel, dict) else {}
    governance_eligible = governance_ratification_eligible(governed)
    receipts_eligible = authority_receipts_eligible(validation)
    kernel_disposition = kernel.get("authority_disposition")
    kernel_disposition = (
        kernel_disposition if isinstance(kernel_disposition, dict) else {}
    )
    final_disposition = {
        authority: kernel_disposition.get(authority, "unavailable")
        for authority in TARGET_GOVERNANCE_AUTHORITIES
    }
    final_disposition.update({
        authority: _receipt_disposition(receipts.get(authority))
        for authority in FINAL_RATIFICATION_RECEIPT_AUTHORITIES
    })
    eligible = bool(
        governance_eligible
        and receipts_eligible
        and all(
            final_disposition.get(authority) == "passed"
            for authority in FINAL_RATIFICATION_AUTHORITIES
        )
    )

    prior_kernel = receipts.get("governance_kernel_receipt")
    prior_l3 = receipts.get("l3_anti_pattern_receipt")
    authoritative = {
        "passed": governance_eligible,
        "available": kernel.get("available") is True,
        "status": "finalized_by_closed_artifact_governance",
        "authority": "common_closed_artifact_finalizer",
        "confirmed": list(kernel.get("confirmed") or []),
        "flags": list(kernel.get("flags") or []),
        "unavailable_organs": list(kernel.get("unavailable_organs") or []),
        "detail": deepcopy(kernel.get("detail") or {}),
        "policy_profile": kernel.get("policy_profile"),
        "required_authorities": list(kernel.get("required_authorities") or []),
        "authority_disposition": deepcopy(kernel_disposition),
        "authority_roster_sha256": kernel.get("authority_roster_sha256"),
    }
    if isinstance(prior_kernel, dict):
        authoritative["producer_receipt"] = deepcopy(prior_kernel)
    receipts["governance_kernel_receipt"] = authoritative

    l3_receipt = {
        "passed": governance_eligible,
        "available": kernel.get("available") is True,
        "status": "finalized_by_closed_artifact_governance",
        "authority": "common_closed_artifact_finalizer",
        "confirmed": list(kernel.get("confirmed") or []),
    }
    if isinstance(prior_l3, dict):
        l3_receipt["producer_receipt"] = deepcopy(prior_l3)
    receipts["l3_anti_pattern_receipt"] = l3_receipt

    producer_credit = validation.get("credit_ready_at_solver_layer") is True
    validation["producer_positive_axiom_receipt_required"] = bool(
        validation.get("positive_axiom_receipt_required")
    )
    validation["producer_discriminating_mnc_required"] = bool(
        validation.get("discriminating_mnc_required")
    )
    validation["positive_axiom_receipt_required"] = True
    validation["discriminating_mnc_required"] = True
    validation["producer_credit_ready_at_solver_layer"] = producer_credit
    validation["credit_ready_at_solver_layer"] = bool(producer_credit and eligible)
    validation["finalized_at_closed_artifact_boundary"] = True
    validation["final_governance_ratification_eligible"] = governance_eligible
    validation["final_authority_receipts_eligible"] = receipts_eligible
    validation["final_required_authorities"] = sorted(
        FINAL_RATIFICATION_AUTHORITIES
    )
    validation["final_authority_disposition"] = final_disposition
    validation["final_authority_roster_sha256"] = (
        FINAL_RATIFICATION_AUTHORITY_ROSTER_SHA256
    )
    validation["final_ratification_eligible"] = eligible
    validation["receipts"] = receipts
    return validation


def unavailable_finalized_validation(reason: object) -> dict[str, Any]:
    """Construct a complete no-credit final state after finalizer failure."""

    governance = {
        "integrity_unverified": True,
        "statement_integrity": {"ok": False, "status": "unavailable"},
        "governance_kernel": {
            "available": False,
            "passed": None,
            "confirmed": [],
            "flags": ["closed_artifact_finalizer_unavailable"],
            "unavailable_organs": ["closed_artifact_finalizer"],
            "detail": {"reason": str(reason or "")[:240]},
            "policy_profile": "target_ratification",
            "required_authorities": sorted(TARGET_GOVERNANCE_AUTHORITIES),
            "authority_disposition": {
                authority: "unavailable"
                for authority in TARGET_GOVERNANCE_AUTHORITIES
            },
            "authority_roster_sha256": (
                TARGET_GOVERNANCE_AUTHORITY_ROSTER_SHA256
            ),
        },
    }
    validation = finalize_solver_validation({}, governance)
    validation["finalizer_unavailable_reason"] = str(reason or "")[:240]
    return validation


def closure_certificate_identity(
    *,
    row_id: object,
    run_tag: object,
    target: str,
    goal: str,
    source: str,
    probe: str,
    proof: str,
) -> dict[str, str]:
    job_id = str(row_id or "").strip()
    if not job_id:
        raise ValueError("closure certificate requires an existing row identity")
    resolved_run_tag = str(run_tag or "").strip() or job_id
    goal_hash = _sha256(goal)
    from ztare.leanmill.governed_ratification import normalized_target_signature

    posed_signature = normalized_target_signature(source, target)
    closed_signature = normalized_target_signature(probe, target)
    return {
        "job_id": job_id,
        "run_tag": resolved_run_tag,
        "goal_sha": goal_hash[:16],
        "goal_sha256": goal_hash,
        "source_sha256": _sha256(source),
        "recompilable_probe_sha256": _sha256(probe),
        "proof_sha256": _sha256(proof),
        "posed_target_signature_sha256": _sha256(posed_signature),
        "closed_target_signature_sha256": _sha256(closed_signature),
    }


def closure_toolchain_identity(lean_root: str | Path) -> dict[str, Any]:
    """Content-address the Lean environment that checked one closure.

    The certificate's owner is the finalized closure artifact, so dependency
    identity belongs here rather than in a benchmark runner.  Package commits
    alone are insufficient when a checkout is dirty; the status and binary
    diff are hashed as part of the identity.
    """

    return dict(_closure_toolchain_identity_cached(str(Path(lean_root).resolve())))


@lru_cache(maxsize=8)
def _closure_toolchain_identity_cached(root_text: str) -> dict[str, Any]:
    root = Path(root_text)
    toolchain = _read_text(root / "lean-toolchain")
    lean_version = _run_text(("lake", "env", "lean", "--version"), cwd=root)
    files: dict[str, str] = {}
    for name in ("lean-toolchain", "lakefile.lean", "lakefile.toml", "lake-manifest.json"):
        path = root / name
        if path.is_file():
            files[name] = _file_sha256(path)
    packages: dict[str, dict[str, Any]] = {}
    package_root = root / ".lake" / "packages"
    if package_root.is_dir():
        for package in sorted(package_root.iterdir(), key=lambda item: item.name):
            if not package.is_dir() or not (package / ".git").exists():
                continue
            revision = _run_text(("git", "-C", str(package), "rev-parse", "HEAD"))
            status = _run_text(
                (
                    "git",
                    "-C",
                    str(package),
                    "status",
                    "--porcelain=v1",
                    "--untracked-files=all",
                )
            )
            diff = _run_text(
                ("git", "-C", str(package), "diff", "--binary", "HEAD")
            )
            packages[package.name] = {
                "commit": revision,
                "dirty": bool(status),
                "status_sha256": _sha256(status),
                "tracked_diff_sha256": _sha256(diff),
            }
    core: dict[str, Any] = {
        "schema": TOOLCHAIN_SCHEMA,
        "project": root.name,
        "lean_toolchain": toolchain,
        "lean_toolchain_sha256": _sha256(toolchain),
        "lean_version": lean_version,
        "lean_version_sha256": _sha256(lean_version),
        "project_file_sha256s": files,
        "package_revisions": packages,
        "complete": bool(toolchain and lean_version and files),
    }
    return {**core, "identity_sha256": _canonical_sha256(core)}


def build_kernel_parity_record(
    *,
    target: str,
    timestamp: str,
    certificate_identity: dict[str, str],
    solver_validation: object,
    governance: object,
    toolchain_identity: object,
    environment_parity: object,
) -> dict[str, Any]:
    """Bind one root kernel-parity decision to its closure and toolchain."""

    validation = solver_validation if isinstance(solver_validation, dict) else {}
    receipts = validation.get("receipts")
    receipts = receipts if isinstance(receipts, dict) else {}
    kernel_receipt = receipts.get("kernel_compile_receipt")
    kernel_receipt = kernel_receipt if isinstance(kernel_receipt, dict) else {}
    mnc_receipt = receipts.get("matched_negative_control_receipt")
    mnc_receipt = mnc_receipt if isinstance(mnc_receipt, dict) else {}
    governed = governance if isinstance(governance, dict) else {}
    kernel = governed.get("governance_kernel")
    kernel = kernel if isinstance(kernel, dict) else {}
    toolchain = toolchain_identity if isinstance(toolchain_identity, dict) else {}
    parity = environment_parity if isinstance(environment_parity, dict) else {}
    core: dict[str, Any] = {
        "schema": KERNEL_PARITY_SCHEMA,
        "ts": str(timestamp or ""),
        "target": str(target or ""),
        "job_id": str(certificate_identity.get("job_id") or ""),
        "run_tag": str(certificate_identity.get("run_tag") or ""),
        "goal_sha256": str(certificate_identity.get("goal_sha256") or ""),
        "source_sha256": str(certificate_identity.get("source_sha256") or ""),
        "recompilable_probe_sha256": str(
            certificate_identity.get("recompilable_probe_sha256") or ""
        ),
        "posed_target_signature_sha256": str(
            certificate_identity.get("posed_target_signature_sha256") or ""
        ),
        "closed_target_signature_sha256": str(
            certificate_identity.get("closed_target_signature_sha256") or ""
        ),
        "final_authority_roster_sha256": str(
            validation.get("final_authority_roster_sha256") or ""
        ),
        "final_authority_disposition": deepcopy(
            validation.get("final_authority_disposition") or {}
        ),
        "hand_wired": {
            "kc": (
                kernel_receipt.get("available") is True
                and kernel_receipt.get("passed") is True
            ),
            "mnc": (
                mnc_receipt.get("available") is True
                and mnc_receipt.get("passed") is True
            ),
        },
        "kernel": {
            "available": kernel.get("available") is True,
            "passed": (
                kernel.get("available") is True
                and kernel.get("passed") is True
            ),
            "confirmed": list(kernel.get("confirmed") or []),
        },
        "kernel_blocked": (
            kernel.get("available") is not True
            or kernel.get("passed") is not True
        ),
        "toolchain_identity_sha256": str(toolchain.get("identity_sha256") or ""),
        "environment_parity": parity,
    }
    return {**core, "record_sha256": _canonical_sha256(core)}


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return _sha256(payload)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def _file_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def _run_text(command: tuple[str, ...], *, cwd: Path | None = None) -> str:
    try:
        completed = subprocess.run(
            list(command),
            cwd=str(cwd) if cwd is not None else None,
            capture_output=True,
            text=True,
            timeout=TOOLCHAIN_PROBE_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if completed.returncode != 0:
        return ""
    return (completed.stdout or completed.stderr or "").strip()
