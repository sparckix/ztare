"""Content-bound compile receipt for conditional AxiomPack lowering."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Sequence

from ztare.leanmill import lean_source
from ztare.leanmill.theory_ir import (
    AxiomFormula,
    TheorySignature,
    content_hash,
    lower_conditional_pack_to_lean,
)
from ztare.leanmill.formal_verification_provider import (
    attach_signature,
    build_payload,
    sha256_ref,
    verify_payload_signature,
)


LOWERING_RECEIPT_SCHEMA = "leanmill.axiom_pack_lean_lowering.v1"


def certify_conditional_lowering(
    signature: TheorySignature,
    axioms: Sequence[AxiomFormula],
    *,
    base_axioms: Sequence[AxiomFormula] = (),
    lean_root: str | Path | None = None,
    timeout_s: int = 180,
    compile_fn: Callable[[str], bool | None] | None = None,
    checker_private_key_pem: str | None = None,
    verifier_ref: str = "leanmill-axiom-lowering-checker",
) -> dict[str, Any]:
    """Lower and elaborate a candidate pack without asserting any global axiom.

    ``compile_fn`` is an injectable compile boundary for tests and remote
    workers.  The default uses LeanMill's campaign-aware compile primitive.
    ``None`` means the compiler was unavailable, never success.
    """

    base_axioms = tuple(base_axioms)
    axioms = tuple(axioms)
    generated = lower_conditional_pack_to_lean(
        signature,
        axioms,
        base_axioms=base_axioms,
    )
    source = "import Mathlib\n\n" + generated
    blocks = lean_source.decl_blocks(source)
    contains_global_axiom = any(
        lean_source.decl_kind(block) == "axiom" for _name, block in blocks
    )
    contains_sorry = lean_source.has_sorry(source)
    compile_error = ""
    compiled: bool | None
    if contains_global_axiom or contains_sorry:
        compiled = False
        compile_error = "forbidden_global_axiom_or_sorry"
    else:
        try:
            if compile_fn is not None:
                compiled = compile_fn(source)
            elif lean_root is not None:
                from ztare.gates.v33_preflight_risk_detector import _compile_probe

                compiled = _compile_probe(
                    source,
                    Path(lean_root),
                    "AxiomPackLowering",
                    int(timeout_s),
                )
            else:
                compiled = None
                compile_error = "lean_root_or_compile_fn_required"
        except Exception as exc:  # noqa: BLE001 - receipt records an unavailable compiler
            compiled = None
            compile_error = f"{type(exc).__name__}: {exc}"[:300]

    core: dict[str, Any] = {
        "schema": LOWERING_RECEIPT_SCHEMA,
        "status": "pass" if compiled is True else "fail" if compiled is False else "unknown",
        "kernel_checked": compiled is True,
        "contains_global_axiom": contains_global_axiom,
        "contains_sorry": contains_sorry,
        "artifact_digest": content_hash({"lean_source": source}),
        "signature_sha256": signature.content_hash,
        "base_axiom_sha256s": [axiom.content_hash for axiom in base_axioms],
        "axiom_sha256s": [axiom.content_hash for axiom in axioms],
        "conditional_pack": True,
        "compile_error": compile_error,
        "proof_credit_eligible": False,
        "theorem_campaign_admissible": False,
    }
    receipt: dict[str, Any] = {**core, "source": source}
    if compiled is True and checker_private_key_pem:
        payload = build_payload(
            formal_system="lean",
            property_class="math",
            verdict="verified",
            subject_ref="axiom-pack-conditional-lowering",
            subject_text=source,
            claim_ref=f"elaborates:{core['artifact_digest']}",
            certificate_ref=f"lean-elaboration:{core['artifact_digest']}",
            certificate_text=core["artifact_digest"],
            verifier_ref=verifier_ref,
            verification_summary="Conditional signature, base theory, and candidate pack elaborated without global axioms.",
            faithfulness_refs=[core["signature_sha256"]],
            checker_evidence_refs=[core["artifact_digest"]],
            input_refs=[*core["base_axiom_sha256s"], *core["axiom_sha256s"]],
            output_refs=[core["artifact_digest"]],
            extra_metadata={
                "purpose": "axiom_pack_conditional_lowering",
                "artifact_digest": core["artifact_digest"],
                "signature_sha256": core["signature_sha256"],
                "base_axiom_sha256s": core["base_axiom_sha256s"],
                "axiom_sha256s": core["axiom_sha256s"],
                "contains_global_axiom": False,
                "contains_sorry": False,
            },
        )
        attach_signature(payload, checker_private_key_pem)
        receipt["verification_payload"] = payload
    receipt["receipt_sha256"] = content_hash(receipt)
    return receipt


def verify_conditional_lowering_receipt(
    signature: TheorySignature,
    axioms: Sequence[AxiomFormula],
    receipt: dict[str, Any],
    *,
    base_axioms: Sequence[AxiomFormula] = (),
    trusted_checker_public_key_pem: str | None,
) -> tuple[bool, list[str]]:
    """Reconstruct source and verify the independent checker's signature."""

    failures: list[str] = []
    source = "import Mathlib\n\n" + lower_conditional_pack_to_lean(
        signature,
        tuple(axioms),
        base_axioms=tuple(base_axioms),
    )
    expected_artifact = content_hash({"lean_source": source})
    expected_base = [axiom.content_hash for axiom in base_axioms]
    expected_axioms = [axiom.content_hash for axiom in axioms]
    expected_receipt_hash = receipt.get("receipt_sha256")
    unsigned = dict(receipt)
    unsigned.pop("receipt_sha256", None)
    if expected_receipt_hash != content_hash(unsigned):
        failures.append("receipt_hash")
    for name, expected in (
        ("source", source),
        ("artifact_digest", expected_artifact),
        ("signature_sha256", signature.content_hash),
        ("base_axiom_sha256s", expected_base),
        ("axiom_sha256s", expected_axioms),
        ("status", "pass"),
        ("kernel_checked", True),
        ("contains_global_axiom", False),
        ("contains_sorry", False),
    ):
        if receipt.get(name) != expected:
            failures.append(name)
    payload = receipt.get("verification_payload")
    if not isinstance(payload, dict) or not trusted_checker_public_key_pem:
        failures.append("trusted_verification_payload")
        return False, failures
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    expected_metadata = {
        "purpose": "axiom_pack_conditional_lowering",
        "artifact_digest": expected_artifact,
        "signature_sha256": signature.content_hash,
        "base_axiom_sha256s": expected_base,
        "axiom_sha256s": expected_axioms,
        "contains_global_axiom": False,
        "contains_sorry": False,
    }
    failures.extend(
        f"metadata.{name}" for name, value in expected_metadata.items() if metadata.get(name) != value
    )
    if payload.get("verdict") != "verified":
        failures.append("provider_verdict")
    if payload.get("subject_digest") != sha256_ref(source):
        failures.append("provider_subject_digest")
    if payload.get("certificate_digest") != sha256_ref(expected_artifact):
        failures.append("provider_certificate_digest")
    try:
        signature_ok = verify_payload_signature(payload, trusted_checker_public_key_pem)
    except (TypeError, ValueError):
        signature_ok = False
    if not signature_ok:
        failures.append("provider_signature")
    return not failures, failures


__all__ = [
    "LOWERING_RECEIPT_SCHEMA",
    "certify_conditional_lowering",
    "verify_conditional_lowering_receipt",
]
