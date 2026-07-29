"""Bounded provider-free ratification of one carried Lean theorem.

This executor owns a different lifecycle from proof search.  Its input already
contains proof bytes; the only admissible transitions are exact target binding,
kernel compilation, fixed governance checks, and certificate persistence.
"""
from __future__ import annotations

import hashlib
import re
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ztare.gates.lean_compile_primitives import (
    AXIOM_ALLOWLIST,
    audit_axioms_subset,
    ensure_elan_on_path,
    run_lake_compile_source,
)
from ztare.gates.lean_proof_gate import run_anti_laundering_kernel
from ztare.leanmill.common import (
    append_jsonl_locked,
    public_path,
    write_text_atomic,
)
from ztare.leanmill.lean_source import (
    ensure_import_header,
    has_sorry,
    replace_decl_proof,
    resolve_theorem_target,
    strip_print_axioms_commands,
)
from ztare.leanmill.ratification_policy import (
    TARGET_GOVERNANCE_AUTHORITIES,
    TARGET_GOVERNANCE_AUTHORITY_ROSTER_SHA256,
)
from ztare.leanmill.solver.closed_artifact import (
    build_kernel_parity_record,
    build_verified_closure_artifact,
    closure_certificate_identity,
    closure_toolchain_identity,
    finalize_solver_validation,
    finalized_artifact_outcome,
    finalized_ratification_eligible,
    governance_ratification_eligible,
)
from ztare.leanmill.solver.proof_margin_of_safety import (
    bind_conclusion_discrimination_receipt,
    conclusion_discrimination_control,
)
from ztare.leanmill.theory_ir import content_hash


SCHEMA = "leanmill.carried_theorem_ratification.v1"
CERTIFICATE_SCHEMA = "leanmill.governed_closure.v2"
REPO = Path(__file__).resolve().parents[3]
DEFAULT_OUT = REPO / "analytics" / "public" / "queries"
DEFAULT_CERTIFICATE_LEDGER = DEFAULT_OUT / "adhoc_closure_certificates.jsonl"
DEFAULT_PARITY_LEDGER = DEFAULT_OUT / "kernel_parity.jsonl"


def _sha256(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


def _proof_is_term(proof_text: str) -> bool:
    proof = (proof_text or "").strip()
    return bool(proof and not re.match(r"by(?:\s|\Z)", proof))


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    if isinstance(value, Path):
        return public_path(value, REPO)
    if isinstance(value, str):
        return value.replace(str(REPO), ".").replace(str(Path.home()), "<home>")
    return value


def _positive_receipt(
    *, passed: bool | None, tail: str, **evidence: Any
) -> dict[str, Any]:
    return {
        "available": passed is not None,
        "passed": passed,
        "status": (
            "pass" if passed is True else "rejected" if passed is False else "unavailable"
        ),
        "tail": str(tail or "")[-300:],
        **evidence,
    }


def _governance_record(kernel: dict[str, Any], mnc: dict[str, Any]) -> dict[str, Any]:
    detail = kernel.get("detail") if isinstance(kernel.get("detail"), dict) else {}
    integrity = detail.get("statement_integrity")
    integrity = integrity if isinstance(integrity, dict) else {}
    kernel_available = kernel.get("available") is True
    return {
        "governance_kernel": dict(kernel),
        "statement_integrity": integrity,
        "integrity_unverified": not (
            kernel_available and isinstance(integrity, dict) and "ok" in integrity
        ),
        "matched_negative_control_binding": {
            "status": (
                "validated_for_single_execution"
                if mnc.get("available") is True and mnc.get("passed") is True
                else "unavailable"
            ),
            "target": mnc.get("target_identity"),
        },
        "margin_of_safety": {
            "target": mnc.get("target_identity"),
            "kind": "proof_margin_of_safety",
            "advisory": False,
            "tests": {
                "conclusion_discrimination": {
                    "verdict": (
                        "strengthen" if mnc.get("passed") is True else "weaken"
                        if mnc.get("passed") is False else "inconclusive"
                    ),
                    "detail": dict(mnc),
                }
            },
        },
    }


def _unavailable_kernel(reason: str) -> dict[str, Any]:
    return {
        "available": False,
        "passed": None,
        "flags": ["governance_organ_unavailable"],
        "confirmed": [],
        "unavailable_organs": sorted(TARGET_GOVERNANCE_AUTHORITIES),
        "policy_profile": "target_ratification",
        "required_authorities": sorted(TARGET_GOVERNANCE_AUTHORITIES),
        "authority_disposition": {
            authority: "unavailable"
            for authority in TARGET_GOVERNANCE_AUTHORITIES
        },
        "authority_roster_sha256": TARGET_GOVERNANCE_AUTHORITY_ROSTER_SHA256,
        "detail": {
            "reason": str(reason or "")[:240],
            "statement_integrity": {"ok": False, "status": "unavailable"},
        },
    }


def _producer_validation(
    kernel_receipt: dict[str, Any],
    mnc: dict[str, Any],
    axiom_receipt: dict[str, Any],
) -> dict[str, Any]:
    producer_ready = bool(
        kernel_receipt.get("passed") is True
        and mnc.get("available") is True
        and mnc.get("passed") is True
        and mnc.get("admitted_under_policy") is True
        and axiom_receipt.get("available") is True
        and axiom_receipt.get("passed") is True
    )
    return {
        "contract_schema": SCHEMA,
        "receipts": {
            "kernel_compile_receipt": kernel_receipt,
            "matched_negative_control_receipt": mnc,
            "axiom_allowlist_receipt": axiom_receipt,
            "governance_kernel_receipt": {
                "available": False,
                "passed": None,
                "status": "deferred_to_closed_artifact_finalizer",
            },
            "l3_anti_pattern_receipt": {
                "available": False,
                "passed": None,
                "status": "deferred_to_closed_artifact_finalizer",
            },
        },
        "credit_ready_at_solver_layer": producer_ready,
        "required_receipts_all_passed_at_solver_layer": producer_ready,
        "axiom_tier": (
            "kernel_pure" if axiom_receipt.get("passed") is True else
            "true_modulo_banned_axioms"
            if axiom_receipt.get("passed") is False else
            "inconclusive"
        ),
        "positive_axiom_receipt_required": True,
        "discriminating_mnc_required": True,
        "authoritative_kernel_deferred": True,
    }


def _result(
    *,
    row_id: str,
    target: str,
    goal: str,
    provider_label: str,
    elapsed_s: float,
    proof_text: str,
    outcome: str,
    validation: dict[str, Any],
    governance: dict[str, Any],
    compile_tail: str,
) -> dict[str, Any]:
    primary = {
        "row_id": row_id,
        "name": row_id,
        "target_name": target,
        "target_theorem_name": target,
        "goal": goal,
        "outcome": outcome,
        "compile_ok": (
            ((validation.get("receipts") or {}).get("kernel_compile_receipt") or {}).get(
                "passed"
            )
            is True
        ),
        "compile_tail": str(compile_tail or "")[-400:],
        "exit_code": 0 if outcome == "closed" else 1,
        "proof_text": proof_text,
        "provider": provider_label,
        "winner": provider_label,
        "provider_wallclock_s": elapsed_s,
        "providers_tried": [{
            "provider": provider_label,
            "outcome": "compiled" if outcome != "failed_compile" else "failed_compile",
            "compile_ok": outcome != "failed_compile",
            "provider_wallclock_s": elapsed_s,
            "agent_kind": "preverified_champion",
        }],
        "contract_validation": validation,
        "matched_negative_control": (
            (validation.get("receipts") or {}).get("matched_negative_control_receipt")
        ),
    }
    return {
        "schema": SCHEMA,
        "results": [primary],
        "outcome": outcome,
        "closure_candidates": 1 if outcome == "closed" else 0,
        "ratification_only": True,
        "provider_calls": 0,
        "governance": governance,
        "governance_ratification_eligible": bool(
            outcome == "closed" and governance_ratification_eligible(governance)
        ),
    }


def _ledger_contains_once(path: Path, digest: str) -> bool:
    matches = 0
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            import json

            value = json.loads(line)
            if isinstance(value, dict) and content_hash(value) == digest:
                matches += 1
    except (OSError, ValueError):
        return False
    return matches == 1


def ratify_carried_theorem(
    target: str,
    posed_source: str,
    proof_text: str,
    goal: str,
    *,
    lean_root: str | Path,
    timeout_s: int = 240,
    provider_label: str = "carried_theorem_artifact",
    run_id: str | None = None,
    certificate_ledger: str | Path | None = None,
    parity_ledger: str | Path | None = None,
) -> dict[str, Any]:
    """Ratify one exact proof artifact without entering a search lifecycle."""

    started = time.perf_counter()
    started_at = datetime.now(timezone.utc).isoformat()
    target = str(target or "").strip()
    proof = str(proof_text or "").strip()
    posed = ensure_import_header(strip_print_axioms_commands(posed_source or ""))
    root = Path(lean_root).resolve()
    if not target or not proof or not posed.strip():
        raise ValueError("ratification requires target, posed source, and proof bytes")
    if has_sorry(proof):
        raise ValueError("carried proof is open")
    posed_identity = resolve_theorem_target(posed, target)
    if posed_identity is None:
        raise ValueError("ratification target is absent or ambiguous")
    closure = replace_decl_proof(
        posed,
        target,
        proof,
        proof_is_term=_proof_is_term(proof),
    )
    closed_identity = resolve_theorem_target(closure, target) if closure else None
    if (
        closed_identity is None
        or posed_identity.qualified_name != closed_identity.qualified_name
        or has_sorry(closure)
    ):
        raise ValueError("exact carried artifact could not be closed")

    row_id = str(run_id or "").strip() or (
        f"ratify::{closed_identity.qualified_name}::{_sha256(posed + proof)[:16]}"
    )
    ensure_elan_on_path()
    compile_ok, compile_tail = run_lake_compile_source(
        closure,
        root,
        timeout_s=max(1, int(timeout_s)),
        prefix="leanmill_carried_ratification_",
    )
    kernel_receipt = _positive_receipt(
        passed=compile_ok,
        tail=(
            "compiled exact carried artifact"
            if compile_ok is True
            else "exact carried artifact did not compile"
        ),
        checker="lean_lake",
    )
    if compile_ok is not True:
        mnc = _positive_receipt(
            passed=None,
            tail="matched control skipped after compile failure",
            kind="source_aware_conclusion_perturbation",
            admitted_under_policy=False,
            discriminating=False,
            policy="require_discriminating_control",
        )
        axiom_receipt = _positive_receipt(
            passed=None,
            tail="target axiom audit skipped after compile failure",
            axioms=[],
            allowed_axioms=sorted(AXIOM_ALLOWLIST),
        )
        governance = _governance_record(
            _unavailable_kernel("exact carried artifact did not compile"),
            mnc,
        )
        validation = finalize_solver_validation(
            _producer_validation(kernel_receipt, mnc, axiom_receipt),
            governance,
        )
        return _result(
            row_id=row_id,
            target=target,
            goal=goal,
            provider_label=provider_label,
            elapsed_s=round(time.perf_counter() - started, 6),
            proof_text=proof,
            outcome="failed_compile",
            validation=validation,
            governance=governance,
            compile_tail=compile_tail,
        )

    raw_mnc = conclusion_discrimination_control(
        closure,
        target,
        root,
        timeout_s=max(1, min(int(timeout_s), 180)),
    )
    mnc = bind_conclusion_discrimination_receipt(
        raw_mnc,
        closure,
        target,
        posed_source=posed,
    )
    if mnc is None:
        mnc = _positive_receipt(
            passed=None,
            tail=str(raw_mnc.get("reason") or "matched control unavailable"),
            kind="source_aware_conclusion_perturbation",
            admitted_under_policy=False,
            discriminating=False,
            policy="require_discriminating_control",
        )

    with tempfile.TemporaryDirectory(prefix="leanmill_carried_axioms_") as td:
        axiom_clean, axiom_bad, axioms = audit_axioms_subset(
            closure,
            target,
            Path(td) / "AxiomAudit.lean",
            root,
            timeout_s=max(1, min(int(timeout_s), 180)),
        )
    axiom_passed = True if axiom_clean else False if axiom_bad else None
    axiom_receipt = _positive_receipt(
        passed=axiom_passed,
        tail=(
            "clean target axiom set"
            if axiom_clean
            else "rejected target axiom set"
            if axiom_bad
            else "target axiom audit unavailable"
        ),
        axioms=axioms,
        allowed_axioms=sorted(AXIOM_ALLOWLIST),
    )

    try:
        kernel = run_anti_laundering_kernel(
            closure,
            root / "_carried_ratification_kernel.lean",
            root,
            original_source=posed,
            target_name=target,
        )
    except Exception as exc:  # noqa: BLE001 - typed authority outage
        kernel = _unavailable_kernel(type(exc).__name__)
    governance = _governance_record(kernel, mnc)
    validation = finalize_solver_validation(
        _producer_validation(kernel_receipt, mnc, axiom_receipt), governance
    )
    eligible = finalized_ratification_eligible(validation)
    outcome = finalized_artifact_outcome(validation)
    if (outcome == "closed") is not eligible:
        raise RuntimeError("finalized outcome projection disagrees with eligibility")
    elapsed = round(time.perf_counter() - started, 6)
    result = _result(
        row_id=row_id,
        target=target,
        goal=goal,
        provider_label=provider_label,
        elapsed_s=elapsed,
        proof_text=proof,
        outcome=outcome,
        validation=validation,
        governance=governance,
        compile_tail=compile_tail,
    )
    result["verified_closure_artifact"] = build_verified_closure_artifact(
        target, closure, posed
    )
    if outcome != "closed":
        result["rejected_reason"] = (
            "fixed ratification authorities rejected or could not evaluate the artifact"
        )
        return _sanitize(result)

    closure_dir = root / "closures"
    safe_target = re.sub(r"[^A-Za-z0-9_.-]+", "_", target)
    closure_path = closure_dir / f"{safe_target}_{_sha256(closure)[:12]}.lean"
    write_text_atomic(closure_path, closure)
    environment_parity = {
        "attempted": False,
        "reason": "isolated_ratification_no_environment_mutation",
    }
    identity = closure_certificate_identity(
        row_id=row_id,
        run_tag=row_id,
        target=target,
        goal=goal,
        source=posed,
        probe=closure,
        proof=proof,
    )
    toolchain = closure_toolchain_identity(root)
    parity = build_kernel_parity_record(
        target=target,
        timestamp=started_at,
        certificate_identity=identity,
        solver_validation=validation,
        governance=governance,
        toolchain_identity=toolchain,
        environment_parity=environment_parity,
    )
    parity_path = Path(parity_ledger or DEFAULT_PARITY_LEDGER)
    append_jsonl_locked(parity_path, _sanitize(parity))
    certificate = {
        "certificate_schema": CERTIFICATE_SCHEMA,
        "ts": started_at,
        **identity,
        "target": target,
        "outcome": "closed",
        "provider": provider_label,
        "proof_text": proof,
        "recompilable_probe": closure,
        "recompilable_probe_reconstructed": False,
        "closure_lean": public_path(closure_path, REPO),
        "governance": _sanitize(governance),
        "solver_validation": _sanitize(validation),
        "matched_negative_control": mnc,
        "ratification_only": True,
        "substrate": public_path(root, REPO),
        "checker": "lean_lake",
        "toolchain_identity": toolchain,
        "kernel_parity_record_sha256": parity["record_sha256"],
        "kernel_parity_record_persisted": _ledger_contains_once(
            parity_path, content_hash(_sanitize(parity))
        ),
        "environment_parity": environment_parity,
        "wall_s": elapsed,
        "cited_from_cache": False,
    }
    public_certificate = _sanitize(certificate)
    certificate_path = Path(certificate_ledger or DEFAULT_CERTIFICATE_LEDGER)
    append_jsonl_locked(certificate_path, public_certificate)
    certificate_digest = content_hash(public_certificate)
    if not _ledger_contains_once(certificate_path, certificate_digest):
        result["results"][0]["outcome"] = "governance_unavailable"
        result["outcome"] = "governance_unavailable"
        result["closure_candidates"] = 0
        result["governance_ratification_eligible"] = False
        result["rejected_reason"] = "content-addressed certificate persistence unavailable"
        return _sanitize(result)
    result.update({
        "closure_certificate": public_path(certificate_path, REPO),
        "closure_certificate_record_sha256": certificate_digest,
        "closure_lean": public_path(closure_path, REPO),
        "environment_parity": environment_parity,
        "kernel_parity_record_sha256": parity["record_sha256"],
    })
    return _sanitize(result)


__all__ = ["ratify_carried_theorem"]
