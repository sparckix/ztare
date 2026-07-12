"""Content-bound ratification for quarantined AxiomPacks.

Ratification reuses LeanMill's existing signed
``formal-verification-provider/v1`` envelope.  The signed subject is the pack's
scientific content; the signed certificate is the complete evidence bundle.
The trusted public key is supplied by the consumer and is never read from the
receipt being verified.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from ztare.leanmill.formal_verification_provider import (
    attach_signature,
    build_payload,
    sha256_ref,
    verify_payload_signature,
)
from ztare.leanmill.finite_model import (
    CERTIFIED_WITH_WITNESSES,
    THEORY_SUITE_SCHEMA,
    verify_certified_theory_suite,
    verify_theory_suite_hash,
)
from ztare.leanmill.theory_ir import (
    AxiomFormula,
    TheorySignature,
    relative_theory_content_hash,
    theory_content_hash,
)
from ztare.leanmill.axiom_yield import verify_shadow_yield_receipt


AXIOM_RATIFICATION_SCHEMA = "leanmill.axiom_pack_ratification.v2"
BASE_THEORY_RESOLUTION_SCHEMA = "leanmill.base_theory_resolution.v1"
RATIFICATION_PURPOSE = "axiom_pack_ratification"
_REQUIRED_STRESS_DIMENSIONS = {
    "nontriviality",
    "consistency_smoke",
    "model_or_example",
    "strength_comparison",
    "separation_or_interpretation",
    "downstream_yield",
}

_PACK_SUBJECT_FIELDS = (
    "schema",
    "name",
    "domain",
    "extends_theory",
    "theory_signature",
    "base_axioms",
    "base_theory_resolved",
    "candidate_axioms",
    "intended_unlocks",
    "provenance",
    "downstream_residuals",
)

_TYPED_CANDIDATE_FIELDS = (
    "name",
    "statement",
    "formula",
    "kill_condition",
    "source_conjecture_sha256",
    "typed_proposal_sha256",
    "semantic_fidelity_verdict_sha256",
    "semantic_fidelity_checker_ref",
)
_AGENT_PROVENANCE_MARKERS = {
    "agent_authored_blueprint_trial",
    "structural_isomorphism_move_card",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _public_key_fingerprint(public_key_pem: str | None) -> str:
    if not public_key_pem:
        return ""
    try:
        from cryptography.hazmat.primitives import serialization

        key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
        der = key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    except (TypeError, ValueError):
        return ""
    return hashlib.sha256(der).hexdigest()


def _private_key_public_fingerprint(private_key_pem: str) -> str:
    try:
        from cryptography.hazmat.primitives import serialization

        key = serialization.load_pem_private_key(
            private_key_pem.encode("utf-8"), password=None
        )
        der = key.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    except (TypeError, ValueError):
        return ""
    return hashlib.sha256(der).hexdigest()


def _as_pack_json(pack: Any) -> dict[str, Any]:
    if hasattr(pack, "to_json"):
        value = pack.to_json()
    else:
        value = dict(pack) if isinstance(pack, Mapping) else {}
    if not isinstance(value, dict):
        raise ValueError("pack must be a JSON object or expose to_json()")
    return value


def pack_subject(pack: Any) -> dict[str, Any]:
    """Return the promotion-invariant pack content covered by ratification."""

    row = _as_pack_json(pack)
    return {field: row.get(field) for field in _PACK_SUBJECT_FIELDS}


def pack_digest(pack: Any) -> str:
    return _digest_text(_canonical_json(pack_subject(pack)))


def evidence_digest(evidence_bundle: Mapping[str, Any]) -> str:
    return _digest_text(_canonical_json(dict(evidence_bundle)))


def _typed_candidate_evidence_required(pack: Any) -> bool:
    row = _as_pack_json(pack)
    provenance = {str(value) for value in row.get("provenance") or []}
    candidates = [value for value in row.get("candidate_axioms") or [] if isinstance(value, Mapping)]
    return bool(provenance & _AGENT_PROVENANCE_MARKERS) or any(
        any(candidate.get(field) is not None for field in _TYPED_CANDIDATE_FIELDS[4:])
        for candidate in candidates
    )


def _validate_typed_candidate_evidence(
    *,
    pack: Any,
    evidence: Any,
    trusted_public_key_pem: str | None,
) -> list[str]:
    """Replay every agent-origin proposal against the candidate stored in the pack."""

    if not _typed_candidate_evidence_required(pack):
        return []
    failures: list[str] = []
    if not isinstance(evidence, list):
        return ["typed_candidate_evidence_missing"]
    if not trusted_public_key_pem:
        failures.append("typed_candidate_trusted_key_missing")

    pack_row = _as_pack_json(pack)
    candidates = [value for value in pack_row.get("candidate_axioms") or [] if isinstance(value, Mapping)]
    expected: dict[str, Mapping[str, Any]] = {}
    for index, candidate in enumerate(candidates):
        proposal_sha256 = candidate.get("typed_proposal_sha256")
        if not isinstance(proposal_sha256, str) or not proposal_sha256:
            failures.append(f"typed_candidate[{index}]:proposal_digest_missing")
            continue
        if proposal_sha256 in expected:
            failures.append(f"typed_candidate[{index}]:duplicate_proposal_digest")
        expected[proposal_sha256] = candidate

    seen: set[str] = set()
    for index, row in enumerate(evidence):
        if not isinstance(row, Mapping):
            failures.append(f"typed_candidate_evidence[{index}]:row_must_be_object")
            continue
        source = row.get("source_conjecture")
        proposal = row.get("typed_axiom_proposal")
        verdict = row.get("semantic_fidelity_verdict")
        if not isinstance(source, Mapping):
            failures.append(f"typed_candidate_evidence[{index}]:source_conjecture_missing")
            continue
        try:
            from ztare.leanmill.typed_axiom_proposal import (
                TypedAxiomProposal,
                admit_axiom_template,
            )

            parsed = TypedAxiomProposal.from_json(proposal)
            candidate = expected.get(parsed.content_hash)
            if candidate is None:
                failures.append(f"typed_candidate_evidence[{index}]:proposal_not_in_pack")
                continue
            if parsed.content_hash in seen:
                failures.append(f"typed_candidate_evidence[{index}]:duplicate_proposal_row")
                continue
            seen.add(parsed.content_hash)
            admitted = admit_axiom_template(
                parsed,
                verdict,
                trusted_public_key_pem=str(trusted_public_key_pem or ""),
                source_conjecture=source,
                expected_verifier_ref=str(candidate.get("semantic_fidelity_checker_ref") or ""),
            )
        except (TypeError, ValueError) as exc:
            failures.append(f"typed_candidate_evidence[{index}]:verification:{exc}")
            continue
        mismatches = [
            field for field in _TYPED_CANDIDATE_FIELDS if candidate.get(field) != admitted.get(field)
        ]
        if mismatches:
            failures.append(
                f"typed_candidate_evidence[{index}]:candidate_mismatch:{','.join(mismatches)}"
            )

    missing = sorted(set(expected) - seen)
    if missing:
        failures.append(f"typed_candidate_evidence_incomplete:{','.join(missing)}")
    return failures


def _base_resolution_subject(pack: Any) -> dict[str, Any]:
    row = _as_pack_json(pack)
    signature, base_axioms, _candidates = _formal_theory_objects(pack)
    return {
        "extends_theory": str(row.get("extends_theory") or ""),
        "mode": "typed" if base_axioms else "explicit_empty",
        "signature_sha256": signature.content_hash,
        "base_axiom_sha256s": sorted(axiom.content_hash for axiom in base_axioms),
        "base_theory_digest": theory_content_hash(signature, base_axioms),
    }


def build_base_theory_resolution(
    *,
    pack: Any,
    source_ref: str,
    private_key_pem: str,
    verifier_ref: str,
    faithfulness_refs: list[str],
    explicit_empty: bool = False,
) -> dict[str, Any]:
    """Sign the correspondence between a named base and its typed laws."""

    subject = _base_resolution_subject(pack)
    if subject["mode"] == "explicit_empty" and explicit_empty is not True:
        raise ValueError("an empty base requires an explicit_empty resolution")
    if not source_ref or not faithfulness_refs:
        raise ValueError("base resolution requires a source_ref and faithfulness refs")
    subject_text = _canonical_json(subject)
    payload = build_payload(
        formal_system="lean",
        property_class="math",
        verdict="verified",
        subject_ref=f"base-theory:{subject['extends_theory']}",
        subject_text=subject_text,
        claim_ref=f"resolve-base:{subject['base_theory_digest']}",
        certificate_ref=source_ref,
        certificate_text=source_ref,
        verifier_ref=verifier_ref,
        verification_summary="Named base theory was resolved to the bound signature and typed laws.",
        faithfulness_refs=faithfulness_refs,
        checker_evidence_refs=[source_ref],
        input_refs=[subject["signature_sha256"], *subject["base_axiom_sha256s"]],
        output_refs=[subject["base_theory_digest"]],
        extra_metadata={
            "purpose": "axiom_pack_base_theory_resolution",
            "resolution_subject": subject,
            "explicit_empty": explicit_empty,
        },
    )
    attach_signature(payload, private_key_pem)
    return {
        "schema": BASE_THEORY_RESOLUTION_SCHEMA,
        "subject": subject,
        "source_ref": source_ref,
        "provider_payload": payload,
    }


def verify_base_theory_resolution(
    *,
    pack: Any,
    receipt: Mapping[str, Any] | None,
    trusted_public_key_pem: str | None,
) -> tuple[bool, list[str]]:
    failures: list[str] = []
    row = dict(receipt or {})
    try:
        subject = _base_resolution_subject(pack)
    except (TypeError, ValueError) as exc:
        return False, [f"base_resolution_pack:{exc}"]
    if row.get("schema") != BASE_THEORY_RESOLUTION_SCHEMA:
        failures.append("schema")
    if row.get("subject") != subject:
        failures.append("subject")
    payload = row.get("provider_payload")
    if not isinstance(payload, Mapping) or not trusted_public_key_pem:
        return False, [*failures, "trusted_provider_payload"]
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), Mapping) else {}
    if metadata.get("purpose") != "axiom_pack_base_theory_resolution":
        failures.append("purpose")
    if metadata.get("resolution_subject") != subject:
        failures.append("metadata_subject")
    if subject["mode"] == "explicit_empty" and metadata.get("explicit_empty") is not True:
        failures.append("explicit_empty")
    if payload.get("verdict") != "verified":
        failures.append("verdict")
    if payload.get("subject_ref") != f"base-theory:{subject['extends_theory']}":
        failures.append("subject_ref")
    if payload.get("subject_digest") != sha256_ref(_canonical_json(subject)):
        failures.append("subject_digest")
    if payload.get("certificate_ref") != row.get("source_ref"):
        failures.append("source_ref")
    if payload.get("input_refs") != [
        subject["signature_sha256"],
        *subject["base_axiom_sha256s"],
    ]:
        failures.append("input_refs")
    if payload.get("output_refs") != [subject["base_theory_digest"]]:
        failures.append("output_refs")
    try:
        signature_ok = verify_payload_signature(dict(payload), trusted_public_key_pem)
    except (TypeError, ValueError):
        signature_ok = False
    if not signature_ok:
        failures.append("signature")
    return not failures, failures


def _receipt_statuses(stress_report: Mapping[str, Any]) -> list[str]:
    rows = stress_report.get("validated_receipts")
    if not isinstance(rows, list):
        rows = stress_report.get("stress_receipts")
    if not isinstance(rows, list):
        return []
    return [str(row.get("status") or "") for row in rows if isinstance(row, Mapping)]


def _formal_theory_objects(
    pack: Any,
) -> tuple[TheorySignature, list[AxiomFormula], list[AxiomFormula]]:
    row = _as_pack_json(pack)
    raw_signature = row.get("theory_signature")
    if not isinstance(raw_signature, Mapping):
        raise ValueError("pack has no theory_signature")
    signature = TheorySignature.from_json(raw_signature)
    if row.get("base_theory_resolved") is not True:
        raise ValueError("pack base theory is unresolved")
    base_axioms: list[AxiomFormula] = []
    for base in row.get("base_axioms") or []:
        if not isinstance(base, Mapping) or not isinstance(base.get("formula"), Mapping):
            raise ValueError("base axiom has no typed formula")
        parsed = AxiomFormula.from_json(
            {"name": base.get("name"), "formula": base.get("formula")}
        )
        if "axiom_hash" in base and base.get("axiom_hash") != parsed.content_hash:
            raise ValueError(f"base axiom {parsed.name!r} declared axiom_hash mismatch")
        base_axioms.append(parsed)
    axioms: list[AxiomFormula] = []
    for candidate in row.get("candidate_axioms") or []:
        if not isinstance(candidate, Mapping) or not isinstance(candidate.get("formula"), Mapping):
            raise ValueError("candidate axiom has no typed formula")
        parsed = AxiomFormula.from_json(
            {
                "name": candidate.get("name"),
                "formula": candidate.get("formula"),
            }
        )
        if "axiom_hash" in candidate and candidate.get("axiom_hash") != parsed.content_hash:
            raise ValueError(f"candidate axiom {parsed.name!r} declared axiom_hash mismatch")
        axioms.append(parsed)
    if not axioms:
        raise ValueError("pack has no typed candidate axioms")
    return signature, base_axioms, axioms


def _formal_theory_from_pack(pack: Any) -> tuple[str, str, list[str], list[str]]:
    signature, base_axioms, axioms = _formal_theory_objects(pack)
    return (
        relative_theory_content_hash(signature, axioms, base_axioms=base_axioms),
        signature.content_hash,
        sorted(axiom.content_hash for axiom in base_axioms),
        sorted(axiom.content_hash for axiom in axioms),
    )


def _replay_semantic_suite(pack: Any, semantic: Mapping[str, Any]) -> list[str]:
    """Replay every positive finite witness inside the signing process.

    Self-hashes only bind bytes; they do not authenticate the producer.  The
    signer therefore reconstructs the exact theory and declared bounds before
    it signs a promotion receipt.
    """

    try:
        signature, base_axioms, axioms = _formal_theory_objects(pack)
        verified, errors = verify_certified_theory_suite(
            signature,
            axioms,
            semantic,
            base_axioms=base_axioms,
        )
    except (AttributeError, TypeError, ValueError) as exc:
        return [f"semantic_ratifier_replay_failed:{exc}"]
    if verified:
        return []
    return [f"semantic_ratifier_replay:{error}" for error in errors]


def _validate_semantic_suite(semantic: Any, *, pack: Any | None = None) -> list[str]:
    if not isinstance(semantic, Mapping):
        return ["semantic_certification_missing"]
    failures: list[str] = []
    if semantic.get("schema") != THEORY_SUITE_SCHEMA:
        failures.append("semantic_certification_schema")
    if semantic.get("status") != CERTIFIED_WITH_WITNESSES or semantic.get("certified") is not True:
        failures.append("semantic_certification_not_witness_certified")
    if not verify_theory_suite_hash(semantic):
        failures.append("semantic_certification_hash")

    joint = semantic.get("joint_satisfiability")
    if not isinstance(joint, Mapping):
        failures.append("semantic_joint_satisfiability_missing")
    else:
        witness = joint.get("witness") if isinstance(joint.get("witness"), Mapping) else {}
        model = witness.get("model") if isinstance(witness.get("model"), Mapping) else {}
        sort_sizes = model.get("sort_sizes") if isinstance(model.get("sort_sizes"), Mapping) else {}
        nontrivial = False
        for size in sort_sizes.values():
            try:
                nontrivial = nontrivial or int(size) > 1
            except (TypeError, ValueError):
                continue
        if not nontrivial:
            failures.append("semantic_joint_satisfiability_trivial_carrier")
    if not semantic.get("theory_digest") or not semantic.get("certificate_digest"):
        failures.append("semantic_certification_unbound")
    if pack is not None:
        failures.extend(_replay_semantic_suite(pack, semantic))
    return failures


def validate_evidence_bundle(
    evidence_bundle: Mapping[str, Any],
    *,
    pack: Any | None = None,
    trusted_base_resolver_public_key_pem: str | None = None,
    trusted_task_manifest_public_key_pem: str | None = None,
    trusted_shadow_checker_public_key_pem: str | None = None,
    trusted_lowering_checker_public_key_pem: str | None = None,
    trusted_semantic_fidelity_public_key_pem: str | None = None,
) -> list[str]:
    """Return fail-closed evidence violations for a promotion attempt."""

    failures: list[str] = []
    stress = evidence_bundle.get("stress_report")
    semantic = evidence_bundle.get("semantic_certification")
    shadow = evidence_bundle.get("downstream_yield")
    lowering = evidence_bundle.get("lean_lowering")
    base_resolution = evidence_bundle.get("base_theory_resolution")
    evidence_keys = {
        "base_resolver": trusted_base_resolver_public_key_pem,
        "task_manifest": trusted_task_manifest_public_key_pem,
        "shadow_checker": trusted_shadow_checker_public_key_pem,
        "lowering_checker": trusted_lowering_checker_public_key_pem,
    }
    if pack is not None and _typed_candidate_evidence_required(pack):
        evidence_keys["semantic_fidelity_checker"] = trusted_semantic_fidelity_public_key_pem
    for role, key in evidence_keys.items():
        if not key:
            failures.append(f"trusted_evidence_key_missing:{role}")
    present_keys = [_public_key_fingerprint(key) for key in evidence_keys.values() if key]
    if (
        len(present_keys) == len(evidence_keys)
        and all(present_keys)
        and len(set(present_keys)) != len(evidence_keys)
    ):
        failures.append("trusted_evidence_checker_keys_not_role_separated")

    if pack is None:
        failures.append("base_theory_resolution_pack_missing")
    else:
        base_verified, base_failures = verify_base_theory_resolution(
            pack=pack,
            receipt=base_resolution if isinstance(base_resolution, Mapping) else None,
            trusted_public_key_pem=trusted_base_resolver_public_key_pem,
        )
        if not base_verified:
            failures.extend(
                f"base_theory_resolution:{item}" for item in base_failures
            )

    if (
        not isinstance(stress, Mapping)
        or stress.get("schema") != "leanmill.axiom_pack_stress.v1"
        or stress.get("ok") is not True
    ):
        failures.append("stress_report_not_passed")
    elif stress.get("missing_stress_receipts"):
        failures.append("stress_receipts_missing")
    else:
        if pack is not None and stress.get("pack_digest") != pack_digest(pack):
            failures.append("stress_report_pack_digest_mismatch")
        statuses = _receipt_statuses(stress)
        if statuses and any(status != "pass" for status in statuses):
            failures.append("stress_receipt_not_passed")
        validated = stress.get("validated_receipts")
        dimensions = [
            str(row.get("dimension") or "")
            for row in validated or []
            if isinstance(row, Mapping)
        ]
        if set(dimensions) != _REQUIRED_STRESS_DIMENSIONS or len(dimensions) != len(
            _REQUIRED_STRESS_DIMENSIONS
        ):
            failures.append("stress_dimension_set_mismatch")

    failures.extend(_validate_semantic_suite(semantic, pack=pack))

    if pack is not None:
        failures.extend(
            _validate_typed_candidate_evidence(
                pack=pack,
                evidence=evidence_bundle.get("typed_candidate_evidence"),
                trusted_public_key_pem=trusted_semantic_fidelity_public_key_pem,
            )
        )

    if (
        not isinstance(shadow, Mapping)
        or shadow.get("status") != "pass"
        or shadow.get("ok") is not True
        or not shadow.get("receipt_digest")
    ):
        failures.append("downstream_yield_not_passed")
    elif pack is not None and shadow.get("pack_digest") != pack_digest(pack):
        failures.append("downstream_yield_pack_digest_mismatch")
    else:
        if not verify_shadow_yield_receipt(
            shadow,
            trusted_checker_public_key_pem=trusted_shadow_checker_public_key_pem,
            trusted_manifest_public_key_pem=trusted_task_manifest_public_key_pem,
        ):
            failures.append("downstream_yield_checker_verification_failed")
        if pack is not None:
            try:
                signature, base_axioms, _candidates = _formal_theory_objects(pack)
                _theory, _signature, _base_hashes, expected_axioms = _formal_theory_from_pack(pack)
            except (TypeError, ValueError):
                pass
            else:
                if shadow.get("base_theory_digest") != theory_content_hash(
                    signature, base_axioms
                ):
                    failures.append("downstream_yield_base_theory_digest_mismatch")
                actual_axioms = sorted(str(x) for x in shadow.get("allowed_axiom_hashes") or [])
                if actual_axioms != expected_axioms:
                    failures.append("downstream_yield_axiom_digest_mismatch")

    if not isinstance(lowering, Mapping) or lowering.get("kernel_checked") is not True:
        failures.append("lean_lowering_not_kernel_checked")
    elif lowering.get("contains_global_axiom") is not False:
        failures.append("lean_lowering_global_axiom_not_excluded")
    elif not lowering.get("artifact_digest"):
        failures.append("lean_lowering_unbound")
    elif pack is not None:
        try:
            from ztare.leanmill.axiom_lowering import verify_conditional_lowering_receipt

            signature, base_axioms, candidate_axioms = _formal_theory_objects(pack)
            verified, lowering_failures = verify_conditional_lowering_receipt(
                signature,
                candidate_axioms,
                dict(lowering),
                base_axioms=base_axioms,
                trusted_checker_public_key_pem=trusted_lowering_checker_public_key_pem,
            )
        except (TypeError, ValueError) as exc:
            failures.append(f"lean_lowering_verification_error:{exc}")
        else:
            if not verified:
                failures.extend(
                    f"lean_lowering_verification:{item}" for item in lowering_failures
                )

    return failures


def build_ratification_receipt(
    *,
    pack: Any,
    evidence_bundle: Mapping[str, Any],
    private_key_pem: str,
    ratifier_ref: str,
    faithfulness_refs: list[str],
    checker_evidence_refs: list[str],
    trusted_base_resolver_public_key_pem: str,
    trusted_task_manifest_public_key_pem: str,
    trusted_shadow_checker_public_key_pem: str,
    trusted_lowering_checker_public_key_pem: str,
    trusted_semantic_fidelity_public_key_pem: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Build and sign a ratification receipt after all evidence gates pass."""

    evidence_keys = [
        trusted_base_resolver_public_key_pem,
        trusted_task_manifest_public_key_pem,
        trusted_shadow_checker_public_key_pem,
        trusted_lowering_checker_public_key_pem,
    ]
    if _typed_candidate_evidence_required(pack):
        evidence_keys.append(trusted_semantic_fidelity_public_key_pem)
    ratifier_fingerprint = _private_key_public_fingerprint(private_key_pem)
    if ratifier_fingerprint and ratifier_fingerprint in {
        _public_key_fingerprint(key) for key in evidence_keys
    }:
        raise ValueError("ratifier key must be separate from evidence checker keys")

    failures = validate_evidence_bundle(
        evidence_bundle,
        pack=pack,
        trusted_base_resolver_public_key_pem=trusted_base_resolver_public_key_pem,
        trusted_task_manifest_public_key_pem=trusted_task_manifest_public_key_pem,
        trusted_shadow_checker_public_key_pem=trusted_shadow_checker_public_key_pem,
        trusted_lowering_checker_public_key_pem=trusted_lowering_checker_public_key_pem,
        trusted_semantic_fidelity_public_key_pem=trusted_semantic_fidelity_public_key_pem,
    )
    if failures:
        raise ValueError(f"ratification evidence failed: {failures}")
    if not faithfulness_refs or not checker_evidence_refs:
        raise ValueError("ratification requires faithfulness and checker evidence refs")

    subject = pack_subject(pack)
    subject_text = _canonical_json(subject)
    evidence = dict(evidence_bundle)
    certificate_text = _canonical_json(evidence)
    subject_digest = pack_digest(pack)
    cert_digest = evidence_digest(evidence)
    provider_payload = build_payload(
        formal_system="lean",
        property_class="math",
        verdict="verified",
        subject_ref=f"axiom-pack:{subject.get('name') or subject_digest}",
        subject_text=subject_text,
        claim_ref=f"ratify:{subject_digest}",
        certificate_ref=f"axiom-pack-evidence:{cert_digest}",
        certificate_text=certificate_text,
        verifier_ref=str(ratifier_ref),
        verification_summary="Candidate pack passed semantic, shadow-yield, and conditional Lean lowering gates.",
        faithfulness_refs=list(faithfulness_refs),
        checker_evidence_refs=list(checker_evidence_refs),
        input_refs=[subject_digest],
        output_refs=[cert_digest],
        extra_metadata={
            "purpose": RATIFICATION_PURPOSE,
            "pack_digest": subject_digest,
            "evidence_digest": cert_digest,
            "promotion_gate": "separate_ratification",
            "kernel_checked": True,
            "semantic_witnesses_replayed": True,
            "task_manifest_verified": True,
            "shadow_checker_verified": True,
            "lowering_checker_verified": True,
            "base_theory_resolution_verified": True,
            "role_separated_evidence_checkers": True,
        },
        run_id=run_id,
    )
    attach_signature(provider_payload, private_key_pem)
    return {
        "schema": AXIOM_RATIFICATION_SCHEMA,
        "pack_digest": subject_digest,
        "evidence_digest": cert_digest,
        "evidence_bundle": evidence,
        "provider_payload": provider_payload,
    }


def verify_ratification_receipt(
    *,
    pack: Any,
    receipt: Mapping[str, Any] | None,
    trusted_public_key_pem: str | None,
    trusted_base_resolver_public_key_pem: str | None,
    trusted_task_manifest_public_key_pem: str | None,
    trusted_shadow_checker_public_key_pem: str | None,
    trusted_lowering_checker_public_key_pem: str | None,
    trusted_semantic_fidelity_public_key_pem: str | None = None,
) -> dict[str, Any]:
    """Verify signature, content binding, and every promotion prerequisite."""

    failures: list[str] = []
    row = dict(receipt or {})
    evidence = row.get("evidence_bundle")
    provider = row.get("provider_payload")
    expected_pack_digest = pack_digest(pack)
    evidence_keys = [
        trusted_base_resolver_public_key_pem,
        trusted_task_manifest_public_key_pem,
        trusted_shadow_checker_public_key_pem,
        trusted_lowering_checker_public_key_pem,
    ]
    if _typed_candidate_evidence_required(pack):
        evidence_keys.append(trusted_semantic_fidelity_public_key_pem)
    ratifier_fingerprint = _public_key_fingerprint(trusted_public_key_pem)
    if ratifier_fingerprint and ratifier_fingerprint in {
        _public_key_fingerprint(key) for key in evidence_keys
    }:
        failures.append("ratifier_key_not_role_separated")
    if row.get("schema") != AXIOM_RATIFICATION_SCHEMA:
        failures.append("ratification_schema")
    if not isinstance(evidence, Mapping):
        failures.append("missing_evidence_bundle")
        evidence = {}
    if not isinstance(provider, Mapping):
        failures.append("missing_provider_payload")
        provider = {}

    expected_evidence_digest = evidence_digest(evidence)
    if row.get("pack_digest") != expected_pack_digest:
        failures.append("pack_digest_mismatch")
    if row.get("evidence_digest") != expected_evidence_digest:
        failures.append("evidence_digest_mismatch")

    metadata = provider.get("metadata") if isinstance(provider.get("metadata"), Mapping) else {}
    checks = {
        "provider_schema": provider.get("schema_version") == "formal-verification-provider/v1",
        "provider_identity": provider.get("provider") == "leanmill",
        "verified_verdict": provider.get("verdict") == "verified",
        "subject_digest": provider.get("subject_digest") == sha256_ref(_canonical_json(pack_subject(pack))),
        "certificate_digest": provider.get("certificate_digest") == sha256_ref(_canonical_json(dict(evidence))),
        "purpose": metadata.get("purpose") == RATIFICATION_PURPOSE,
        "metadata_pack_digest": metadata.get("pack_digest") == expected_pack_digest,
        "metadata_evidence_digest": metadata.get("evidence_digest") == expected_evidence_digest,
        "promotion_gate": metadata.get("promotion_gate") == "separate_ratification",
        "kernel_checked": metadata.get("kernel_checked") is True,
        "semantic_witnesses_replayed": metadata.get("semantic_witnesses_replayed") is True,
        "task_manifest_verified": metadata.get("task_manifest_verified") is True,
        "shadow_checker_verified": metadata.get("shadow_checker_verified") is True,
        "lowering_checker_verified": metadata.get("lowering_checker_verified") is True,
        "base_theory_resolution_verified": metadata.get(
            "base_theory_resolution_verified"
        )
        is True,
        "role_separated_evidence_checkers": metadata.get(
            "role_separated_evidence_checkers"
        )
        is True,
        "faithfulness_refs": bool(provider.get("faithfulness_refs")),
        "checker_evidence_refs": bool(provider.get("checker_evidence_refs")),
    }
    failures.extend(name for name, passed in checks.items() if not passed)
    failures.extend(
        validate_evidence_bundle(
            evidence,
            pack=pack,
            trusted_base_resolver_public_key_pem=trusted_base_resolver_public_key_pem,
            trusted_task_manifest_public_key_pem=trusted_task_manifest_public_key_pem,
            trusted_shadow_checker_public_key_pem=trusted_shadow_checker_public_key_pem,
            trusted_lowering_checker_public_key_pem=trusted_lowering_checker_public_key_pem,
            trusted_semantic_fidelity_public_key_pem=trusted_semantic_fidelity_public_key_pem,
        )
    )

    signature_ok = False
    if not trusted_public_key_pem:
        failures.append("trusted_public_key_missing")
    elif provider:
        try:
            signature_ok = verify_payload_signature(dict(provider), trusted_public_key_pem)
        except (TypeError, ValueError):
            signature_ok = False
        if not signature_ok:
            failures.append("provider_signature_invalid")

    return {
        "schema": "leanmill.axiom_pack_ratification_verification.v1",
        "allowed": not failures,
        "pack_digest": expected_pack_digest,
        "evidence_digest": expected_evidence_digest,
        "signature_verified": signature_ok,
        "failures": failures,
    }


__all__ = [
    "AXIOM_RATIFICATION_SCHEMA",
    "BASE_THEORY_RESOLUTION_SCHEMA",
    "RATIFICATION_PURPOSE",
    "build_base_theory_resolution",
    "build_ratification_receipt",
    "evidence_digest",
    "pack_digest",
    "pack_subject",
    "validate_evidence_bundle",
    "verify_base_theory_resolution",
    "verify_ratification_receipt",
]
