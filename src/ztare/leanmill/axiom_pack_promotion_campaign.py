"""Campaign-owned transition from an admitted AxiomPack to promotion.

The candidate producer, shadow solver, evidence checkers, and ratifier retain
separate authorities.  This module owns only the state transition: it binds
their artifacts, creates the shadow-yield and conditional-lowering receipts,
replays the promotion evidence, and calls ``promote_axiom_pack``.  Frontier
theorem certificates are deliberately outside this input algebra.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from ztare.leanmill.axiom_authority import (
    build_ratification_receipt,
    pack_digest,
)
from ztare.leanmill.axiom_lowering import certify_conditional_lowering
from ztare.leanmill.axiom_pack import (
    AXIOM_PACK_SCHEMA,
    AxiomPack,
    promote_axiom_pack,
    stress_axiom_pack,
)
from ztare.leanmill.axiom_yield import (
    ShadowAttempt,
    evaluate_shadow_ab,
    verify_shadow_task_manifest,
)
from ztare.leanmill.common import read_json, write_json_atomic
from ztare.leanmill.digest_ref import is_sha256_digest
from ztare.leanmill.theory_ir import (
    AxiomFormula,
    TheorySignature,
    content_hash,
    theory_content_hash,
    validate_axioms,
)


PROMOTION_ADMISSION_SCHEMA = "leanmill.axiom_pack_promotion_admission.v1"
PROMOTION_SOURCE_IDENTITY_SCHEMA = "leanmill.axiom_pack_source_identity.v1"
SHADOW_ATTEMPT_BATCH_SCHEMA = "leanmill.axiom_pack_shadow_attempt_batch.v1"
PROMOTION_TRANSITION_SCHEMA = "leanmill.axiom_pack_promotion_transition.v1"
PROMOTION_BLOCKER_SCHEMA = "leanmill.axiom_pack_promotion_blocker.v1"

ADMISSION_FILE = "axiom_pack_promotion_admission.json"
MANIFEST_FILE = "axiom_pack_shadow_task_manifest.json"
BASELINE_FILE = "axiom_pack_shadow_attempts.baseline.json"
TREATMENT_FILE = "axiom_pack_shadow_attempts.treatment.json"


def _sha(value: Any) -> str:
    return "sha256:" + content_hash(value)


def _receipt(core: Mapping[str, Any]) -> dict[str, Any]:
    return {**dict(core), "receipt_sha256": content_hash(dict(core))}


def _public_fingerprint(public_key_pem: str) -> str:
    from cryptography.hazmat.primitives import serialization

    key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
    der = key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return content_hash({"public_key_der_hex": der.hex()})


def _private_fingerprint(private_key_pem: str) -> str:
    from cryptography.hazmat.primitives import serialization

    key = serialization.load_pem_private_key(
        private_key_pem.encode("utf-8"), password=None
    )
    der = key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return content_hash({"public_key_der_hex": der.hex()})


@dataclass(frozen=True)
class AxiomPackPromotionAuthorities:
    """Configured role keys; no trust key is accepted from a receipt."""

    ratifier_private_key_pem: str
    ratifier_public_key_pem: str
    base_resolver_public_key_pem: str
    task_manifest_public_key_pem: str
    shadow_checker_public_key_pem: str
    lowering_checker_private_key_pem: str
    lowering_checker_public_key_pem: str
    semantic_fidelity_public_key_pem: str = ""
    ratifier_ref: str = "leanmill-axiom-pack-ratifier"
    lowering_checker_ref: str = "leanmill-axiom-lowering-checker"

    def failures(self, *, semantic_fidelity_required: bool) -> list[str]:
        values = {
            "ratifier": self.ratifier_public_key_pem,
            "base_resolver": self.base_resolver_public_key_pem,
            "task_manifest": self.task_manifest_public_key_pem,
            "shadow_checker": self.shadow_checker_public_key_pem,
            "lowering_checker": self.lowering_checker_public_key_pem,
        }
        if semantic_fidelity_required:
            values["semantic_fidelity_checker"] = self.semantic_fidelity_public_key_pem
        failures = [
            f"promotion_authorities.{role}_public_key_pem"
            for role, value in values.items()
            if not str(value).strip()
        ]
        if not self.ratifier_private_key_pem.strip():
            failures.append("promotion_authorities.ratifier_private_key_pem")
        if not self.lowering_checker_private_key_pem.strip():
            failures.append("promotion_authorities.lowering_checker_private_key_pem")
        if failures:
            return failures
        try:
            fingerprints = {role: _public_fingerprint(value) for role, value in values.items()}
            if _private_fingerprint(self.ratifier_private_key_pem) != fingerprints["ratifier"]:
                failures.append("promotion_authorities.ratifier_keypair")
            if (
                _private_fingerprint(self.lowering_checker_private_key_pem)
                != fingerprints["lowering_checker"]
            ):
                failures.append("promotion_authorities.lowering_checker_keypair")
            if len(set(fingerprints.values())) != len(fingerprints):
                failures.append("promotion_authorities.role_separation")
        except (TypeError, ValueError):
            failures.append("promotion_authorities.invalid_key_material")
        if not self.ratifier_ref.strip():
            failures.append("promotion_authorities.ratifier_ref")
        if not self.lowering_checker_ref.strip():
            failures.append("promotion_authorities.lowering_checker_ref")
        return failures

    @classmethod
    def from_directory(cls, directory: str | Path) -> "AxiomPackPromotionAuthorities":
        root = Path(directory)

        def required(name: str) -> str:
            path = root / name
            if not path.is_file():
                return ""
            return path.read_text(encoding="utf-8")

        return cls(
            ratifier_private_key_pem=required("ratifier.private.pem"),
            ratifier_public_key_pem=required("ratifier.public.pem"),
            base_resolver_public_key_pem=required("base_resolver.public.pem"),
            task_manifest_public_key_pem=required("task_manifest.public.pem"),
            shadow_checker_public_key_pem=required("shadow_checker.public.pem"),
            lowering_checker_private_key_pem=required("lowering_checker.private.pem"),
            lowering_checker_public_key_pem=required("lowering_checker.public.pem"),
            semantic_fidelity_public_key_pem=required("semantic_fidelity.public.pem"),
        )


def _typed_candidate_evidence_required(pack: AxiomPack) -> bool:
    markers = {"agent_authored_blueprint_trial", "structural_isomorphism_move_card"}
    bound_fields = {
        "source_conjecture_sha256",
        "typed_proposal_sha256",
        "semantic_fidelity_verdict_sha256",
        "semantic_fidelity_checker_ref",
    }
    return bool(markers & set(pack.provenance)) or any(
        any(candidate.get(field) is not None for field in bound_fields)
        for candidate in pack.candidate_axioms
    )


def _formal_theory(
    pack: AxiomPack,
) -> tuple[TheorySignature, tuple[AxiomFormula, ...], tuple[AxiomFormula, ...]]:
    signature = TheorySignature.from_json(pack.theory_signature)

    def parse(rows: Sequence[Mapping[str, Any]], kind: str) -> tuple[AxiomFormula, ...]:
        parsed: list[AxiomFormula] = []
        for index, row in enumerate(rows):
            if not isinstance(row.get("formula"), Mapping):
                raise ValueError(f"pack.{kind}[{index}].formula")
            axiom = AxiomFormula.from_json(
                {"name": row.get("name"), "formula": row.get("formula")}
            )
            if row.get("axiom_hash") not in {None, axiom.content_hash}:
                raise ValueError(f"pack.{kind}[{index}].axiom_hash")
            parsed.append(axiom)
        return tuple(parsed)

    base = parse(pack.base_axioms, "base_axioms")
    candidates = parse(pack.candidate_axioms, "candidate_axioms")
    if not candidates:
        raise ValueError("pack.candidate_axioms")
    validate_axioms(signature, (*base, *candidates))
    return signature, base, candidates


def _pack_identity_failures(pack: AxiomPack) -> list[str]:
    ordered = (
        ("pack.schema", pack.schema == AXIOM_PACK_SCHEMA),
        ("pack.name", bool(pack.name.strip())),
        ("pack.domain", bool(pack.domain.strip())),
        ("pack.extends_theory", bool(pack.extends_theory.strip())),
        ("pack.theory_signature", bool(pack.theory_signature)),
        ("pack.base_theory_resolved", pack.base_theory_resolved is True),
        ("pack.candidate_axioms", bool(pack.candidate_axioms)),
        ("pack.intended_unlocks", bool(pack.intended_unlocks)),
        ("pack.provenance", bool(pack.provenance)),
        ("pack.downstream_residuals", bool(pack.downstream_residuals)),
        ("pack.promotion_status", pack.promotion_status == "quarantined"),
    )
    failures = [field for field, passed in ordered if not passed]
    failures.extend(
        f"pack.candidate_axioms[{index}].formula"
        for index, row in enumerate(pack.candidate_axioms)
        if not isinstance(row.get("formula"), Mapping)
    )
    failures.extend(
        f"pack.base_axioms[{index}].formula"
        for index, row in enumerate(pack.base_axioms)
        if not isinstance(row.get("formula"), Mapping)
    )
    if failures:
        return failures
    try:
        _formal_theory(pack)
    except (TypeError, ValueError) as exc:
        failures.append(str(exc))
    return failures


def build_axiom_pack_source_identity(
    *,
    pack: AxiomPack | Mapping[str, Any],
    campaign_id: str,
    attempt_id: str,
    context_hash: str,
    context_epoch: int,
    source_pack_ref: str,
    source_receipt_refs: Sequence[str],
) -> dict[str, Any]:
    candidate = pack if isinstance(pack, AxiomPack) else AxiomPack.from_json(dict(pack))
    if source_pack_ref not in candidate.provenance:
        raise ValueError("source_pack_ref must be carried in pack.provenance")
    refs = [str(value) for value in source_receipt_refs]
    if not all((campaign_id, attempt_id, context_hash, source_pack_ref)):
        raise ValueError("source identity fields are required")
    if context_epoch < 0 or not refs or not all(
        is_sha256_digest(value) for value in refs
    ):
        raise ValueError("source identity requires an epoch and canonical receipt refs")
    core = {
        "schema": PROMOTION_SOURCE_IDENTITY_SCHEMA,
        "campaign_id": campaign_id,
        "attempt_id": attempt_id,
        "context_hash": context_hash,
        "context_epoch": context_epoch,
        "source_pack_ref": source_pack_ref,
        "source_receipt_refs": refs,
        "pack_digest": pack_digest(candidate),
    }
    return {**core, "identity_sha256": _sha(core)}


def build_axiom_pack_promotion_admission(
    *,
    pack: AxiomPack | Mapping[str, Any],
    source_identity: Mapping[str, Any],
    base_theory_resolution: Mapping[str, Any],
    typed_candidate_evidence: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    candidate = pack if isinstance(pack, AxiomPack) else AxiomPack.from_json(dict(pack))
    failures = _pack_identity_failures(candidate)
    if failures:
        raise ValueError(f"pack admission failed: {failures}")
    core = {
        "schema": PROMOTION_ADMISSION_SCHEMA,
        "source_identity": dict(source_identity),
        "pack_digest": pack_digest(candidate),
        "pack": candidate.to_json(),
        "base_theory_resolution": dict(base_theory_resolution),
        "typed_candidate_evidence": [dict(row) for row in typed_candidate_evidence],
        "frontier_theorem_certificate": None,
    }
    return {**core, "admission_sha256": _sha(core)}


def build_axiom_pack_promotion_admission_from_birth(
    *,
    candidate_birth: Mapping[str, Any],
    campaign_id: str,
    attempt_id: str,
    context_hash: str,
    context_epoch: int,
    base_theory_resolution: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind a candidate-birth receipt to one promotion campaign context."""

    from ztare.leanmill.axiom_pack_candidate_birth import (
        verify_axiom_pack_candidate_birth,
    )

    birth_ok, birth_failures = verify_axiom_pack_candidate_birth(candidate_birth)
    if not birth_ok:
        raise ValueError(f"candidate birth rejected: {birth_failures}")
    pack = AxiomPack.from_json(dict(candidate_birth["pack"]))
    source_identity = build_axiom_pack_source_identity(
        pack=pack,
        campaign_id=campaign_id,
        attempt_id=attempt_id,
        context_hash=context_hash,
        context_epoch=context_epoch,
        source_pack_ref=str(candidate_birth["source_pack_ref"]),
        source_receipt_refs=[
            str(candidate_birth["source_receipt_sha256"]),
            str(candidate_birth["receipt_sha256"]),
        ],
    )
    return build_axiom_pack_promotion_admission(
        pack=pack,
        source_identity=source_identity,
        base_theory_resolution=base_theory_resolution,
        typed_candidate_evidence=[
            dict(row) for row in candidate_birth["typed_candidate_evidence"]
        ],
    )


def build_shadow_attempt_batch(
    *,
    arm: str,
    attempts: Sequence[ShadowAttempt | Mapping[str, Any]],
    pack_digest_value: str,
    task_manifest_digest: str,
    source_identity_sha256: str,
) -> dict[str, Any]:
    if arm not in {"baseline", "treatment"}:
        raise ValueError("shadow attempt batch arm")
    rows = [
        value.to_json() if isinstance(value, ShadowAttempt) else dict(value)
        for value in attempts
    ]
    if any(ShadowAttempt.from_json(row).arm != arm for row in rows):
        raise ValueError("shadow attempt crossed arm identity")
    core = {
        "schema": SHADOW_ATTEMPT_BATCH_SCHEMA,
        "arm": arm,
        "pack_digest": pack_digest_value,
        "task_manifest_digest": task_manifest_digest,
        "source_identity_sha256": source_identity_sha256,
        "attempts": rows,
    }
    return {**core, "batch_sha256": _sha(core)}


def _blocker(
    *,
    stage: str,
    missing: Sequence[str],
    pack_digest_value: str = "",
    failures: Sequence[str] = (),
) -> dict[str, Any]:
    fields = [str(value) for value in missing]
    core = {
        "schema": PROMOTION_BLOCKER_SCHEMA,
        "status": "blocked_missing_artifact" if fields else "promotion_rejected",
        "stage": stage,
        "pack_digest": pack_digest_value,
        "missing_artifacts": [
            {"field": field, "owner": field.split(".", 1)[0]}
            for field in fields
        ],
        "next_required_field": fields[0] if fields else "",
        "failures": [str(value) for value in failures],
        "promotion_kind": "axiom_pack_contract_lane",
        "frontier_theorem_certificate_consumed": False,
        "proof_credit_eligible": False,
        "theorem_campaign_admissible": False,
    }
    return _receipt(core)


def inspect_preserved_pack_candidate(value: Mapping[str, Any]) -> dict[str, Any]:
    """Return the exact first missing promotion field for a preserved report."""

    pack_row: Any = value.get("pack")
    if not isinstance(pack_row, Mapping):
        primary = value.get("primary")
        pack_row = primary.get("pack") if isinstance(primary, Mapping) else None
    if not isinstance(pack_row, Mapping):
        return _blocker(stage="candidate_intake", missing=["pack"])
    pack = AxiomPack.from_json(dict(pack_row))
    failures = _pack_identity_failures(pack)
    if failures:
        return _blocker(
            stage="candidate_intake",
            missing=failures,
            pack_digest_value=pack_digest(pack),
        )
    return _blocker(
        stage="candidate_intake",
        missing=["axiom_pack_promotion_admission.source_identity"],
        pack_digest_value=pack_digest(pack),
    )


def _validate_source_identity(
    source: Mapping[str, Any], pack: AxiomPack
) -> list[str]:
    required = {
        "schema",
        "campaign_id",
        "attempt_id",
        "context_hash",
        "context_epoch",
        "source_pack_ref",
        "source_receipt_refs",
        "pack_digest",
        "identity_sha256",
    }
    failures: list[str] = []
    if set(source) != required:
        return ["axiom_pack_promotion_admission.source_identity.fields"]
    core = {key: value for key, value in source.items() if key != "identity_sha256"}
    checks = {
        "schema": source.get("schema") == PROMOTION_SOURCE_IDENTITY_SCHEMA,
        "identity_sha256": source.get("identity_sha256") == _sha(core),
        "pack_digest": source.get("pack_digest") == pack_digest(pack),
        "source_pack_ref": source.get("source_pack_ref") in pack.provenance,
        "campaign_id": bool(str(source.get("campaign_id") or "").strip()),
        "attempt_id": bool(str(source.get("attempt_id") or "").strip()),
        "context_hash": bool(str(source.get("context_hash") or "").strip()),
        "context_epoch": isinstance(source.get("context_epoch"), int)
        and int(source["context_epoch"]) >= 0,
        "source_receipt_refs": isinstance(source.get("source_receipt_refs"), list)
        and bool(source["source_receipt_refs"])
        and all(
            is_sha256_digest(value) for value in source["source_receipt_refs"]
        ),
    }
    failures.extend(
        f"axiom_pack_promotion_admission.source_identity.{name}"
        for name, passed in checks.items()
        if not passed
    )
    return failures


def _validate_admission(
    admission: Mapping[str, Any],
) -> tuple[AxiomPack | None, list[str]]:
    required = {
        "schema",
        "source_identity",
        "pack_digest",
        "pack",
        "base_theory_resolution",
        "typed_candidate_evidence",
        "frontier_theorem_certificate",
        "admission_sha256",
    }
    if set(admission) != required:
        return None, ["axiom_pack_promotion_admission.fields"]
    core = {key: value for key, value in admission.items() if key != "admission_sha256"}
    failures: list[str] = []
    if admission.get("schema") != PROMOTION_ADMISSION_SCHEMA:
        failures.append("axiom_pack_promotion_admission.schema")
    if admission.get("admission_sha256") != _sha(core):
        failures.append("axiom_pack_promotion_admission.admission_sha256")
    if admission.get("frontier_theorem_certificate") is not None:
        failures.append("axiom_pack_promotion_admission.frontier_theorem_certificate")
    pack_row = admission.get("pack")
    if not isinstance(pack_row, Mapping):
        return None, [*failures, "axiom_pack_promotion_admission.pack"]
    pack = AxiomPack.from_json(dict(pack_row))
    failures.extend(_pack_identity_failures(pack))
    if admission.get("pack_digest") != pack_digest(pack):
        failures.append("axiom_pack_promotion_admission.pack_digest")
    source = admission.get("source_identity")
    if not isinstance(source, Mapping):
        failures.append("axiom_pack_promotion_admission.source_identity")
    else:
        failures.extend(_validate_source_identity(source, pack))
    if not isinstance(admission.get("base_theory_resolution"), Mapping):
        failures.append("axiom_pack_promotion_admission.base_theory_resolution")
    if not isinstance(admission.get("typed_candidate_evidence"), list):
        failures.append("axiom_pack_promotion_admission.typed_candidate_evidence")
    return pack, failures


def _batch_attempts(
    batch: Mapping[str, Any],
    *,
    arm: str,
    pack_digest_value: str,
    manifest_digest: str,
    source_identity_sha256: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    required = {
        "schema",
        "arm",
        "pack_digest",
        "task_manifest_digest",
        "source_identity_sha256",
        "attempts",
        "batch_sha256",
    }
    if set(batch) != required:
        return [], [f"shadow_attempts.{arm}.fields"]
    core = {key: value for key, value in batch.items() if key != "batch_sha256"}
    checks = {
        "schema": batch.get("schema") == SHADOW_ATTEMPT_BATCH_SCHEMA,
        "arm": batch.get("arm") == arm,
        "pack_digest": batch.get("pack_digest") == pack_digest_value,
        "task_manifest_digest": batch.get("task_manifest_digest") == manifest_digest,
        "source_identity_sha256": batch.get("source_identity_sha256")
        == source_identity_sha256,
        "batch_sha256": batch.get("batch_sha256") == _sha(core),
        "attempts": isinstance(batch.get("attempts"), list),
    }
    failures = [
        f"shadow_attempts.{arm}.{name}" for name, passed in checks.items() if not passed
    ]
    rows = [dict(row) for row in batch.get("attempts") or () if isinstance(row, Mapping)]
    if isinstance(batch.get("attempts"), list) and len(rows) != len(batch["attempts"]):
        failures.append(f"shadow_attempts.{arm}.attempt_shape")
    try:
        if any(ShadowAttempt.from_json(row).arm != arm for row in rows):
            failures.append(f"shadow_attempts.{arm}.attempt_arm")
    except (TypeError, ValueError):
        failures.append(f"shadow_attempts.{arm}.attempt_parse")
    return rows, failures


def advance_axiom_pack_promotion(
    *,
    admission: Mapping[str, Any] | None,
    task_manifest: Mapping[str, Any] | None,
    baseline_batch: Mapping[str, Any] | None,
    treatment_batch: Mapping[str, Any] | None,
    authorities: AxiomPackPromotionAuthorities | None,
    compile_fn: Callable[[str], bool | None] | None = None,
    lean_root: str | Path | None = None,
) -> dict[str, Any]:
    """Advance one complete contract-lane promotion input, failing closed."""

    missing = []
    for field, value in (
        ("axiom_pack_promotion_admission", admission),
        ("axiom_pack_shadow_task_manifest", task_manifest),
        ("axiom_pack_shadow_attempts.baseline", baseline_batch),
        ("axiom_pack_shadow_attempts.treatment", treatment_batch),
        ("promotion_authorities", authorities),
    ):
        if value is None:
            missing.append(field)
    if compile_fn is None and lean_root is None:
        missing.append("conditional_lowering.compile_fn_or_lean_root")
    if missing:
        return _blocker(stage="input", missing=missing)

    assert admission is not None and task_manifest is not None
    assert baseline_batch is not None and treatment_batch is not None
    assert authorities is not None
    pack, failures = _validate_admission(admission)
    if pack is None or failures:
        return _blocker(
            stage="admission",
            missing=failures,
            pack_digest_value=pack_digest(pack) if pack is not None else "",
        )
    current_pack_digest = pack_digest(pack)
    authority_failures = authorities.failures(
        semantic_fidelity_required=_typed_candidate_evidence_required(pack)
    )
    if authority_failures:
        return _blocker(
            stage="authorities",
            missing=authority_failures,
            pack_digest_value=current_pack_digest,
        )

    signature, base_axioms, candidate_axioms = _formal_theory(pack)
    base_digest = theory_content_hash(signature, base_axioms)
    manifest_ok, manifest_failures = verify_shadow_task_manifest(
        task_manifest,
        base_theory_digest=base_digest,
        trusted_public_key_pem=authorities.task_manifest_public_key_pem,
    )
    if not manifest_ok:
        return _blocker(
            stage="task_manifest",
            missing=[],
            failures=[f"task_manifest.{value}" for value in manifest_failures],
            pack_digest_value=current_pack_digest,
        )
    metadata = task_manifest.get("metadata")
    manifest_digest = str(
        metadata.get("manifest_digest") if isinstance(metadata, Mapping) else ""
    )
    source_identity = admission["source_identity"]
    source_identity_sha = str(source_identity["identity_sha256"])
    baseline, baseline_failures = _batch_attempts(
        baseline_batch,
        arm="baseline",
        pack_digest_value=current_pack_digest,
        manifest_digest=manifest_digest,
        source_identity_sha256=source_identity_sha,
    )
    treatment, treatment_failures = _batch_attempts(
        treatment_batch,
        arm="treatment",
        pack_digest_value=current_pack_digest,
        manifest_digest=manifest_digest,
        source_identity_sha256=source_identity_sha,
    )
    if baseline_failures or treatment_failures:
        return _blocker(
            stage="shadow_attempt_batches",
            missing=[],
            failures=[*baseline_failures, *treatment_failures],
            pack_digest_value=current_pack_digest,
        )

    shadow = evaluate_shadow_ab(
        pack_digest=current_pack_digest,
        base_theory_digest=base_digest,
        allowed_axiom_hashes=[axiom.content_hash for axiom in candidate_axioms],
        task_manifest=task_manifest,
        baseline_attempts=baseline,
        treatment_attempts=treatment,
        trusted_checker_public_key_pem=authorities.shadow_checker_public_key_pem,
        trusted_manifest_public_key_pem=authorities.task_manifest_public_key_pem,
    )
    lowering = certify_conditional_lowering(
        signature,
        candidate_axioms,
        base_axioms=base_axioms,
        lean_root=lean_root,
        compile_fn=compile_fn,
        checker_private_key_pem=authorities.lowering_checker_private_key_pem,
        verifier_ref=authorities.lowering_checker_ref,
    )
    retained_receipts = [
        dict(row)
        for row in pack.stress_receipts
        if isinstance(row, Mapping) and row.get("dimension") != "downstream_yield"
    ]
    evaluated_pack = replace(pack, stress_receipts=[*retained_receipts, shadow])
    stress = stress_axiom_pack(
        evaluated_pack,
        trusted_task_manifest_public_key_pem=authorities.task_manifest_public_key_pem,
        trusted_shadow_checker_public_key_pem=authorities.shadow_checker_public_key_pem,
    )
    semantic_rows = [
        row
        for row in evaluated_pack.stress_receipts
        if row.get("dimension") == "semantic_certification"
        and isinstance(row.get("suite"), Mapping)
    ]
    stage_failures: list[str] = []
    if shadow.get("ok") is not True:
        stage_failures.append(f"shadow_yield:{shadow.get('status') or 'failed'}")
    if lowering.get("status") != "pass" or lowering.get("kernel_checked") is not True:
        stage_failures.append(f"conditional_lowering:{lowering.get('status') or 'failed'}")
    if stress.get("ok") is not True:
        stage_failures.extend(
            f"stress:{value}" for value in stress.get("missing_stress_receipts") or ()
        )
        stage_failures.extend(
            f"stress:{row.get('dimension')}:{row.get('reason')}"
            for row in stress.get("invalid_stress_receipts") or ()
            if isinstance(row, Mapping)
        )
    if len(semantic_rows) != 1:
        stage_failures.append("semantic_certification:exactly_one_suite_required")
    if stage_failures:
        core = {
            "schema": PROMOTION_TRANSITION_SCHEMA,
            "status": "promotion_rejected",
            "stage": "evidence_production",
            "pack_digest": current_pack_digest,
            "source_identity_sha256": source_identity_sha,
            "shadow_yield": shadow,
            "conditional_lowering": lowering,
            "stress_report": stress,
            "failures": stage_failures,
            "promotion_kind": "axiom_pack_contract_lane",
            "frontier_theorem_certificate_consumed": False,
            "proof_credit_eligible": False,
            "theorem_campaign_admissible": False,
        }
        return _receipt(core)

    evidence = {
        "promotion_source_identity": dict(source_identity),
        "base_theory_resolution": dict(admission["base_theory_resolution"]),
        "stress_report": stress,
        "semantic_certification": dict(semantic_rows[0]["suite"]),
        "downstream_yield": shadow,
        "lean_lowering": lowering,
        "typed_candidate_evidence": [
            dict(row) for row in admission["typed_candidate_evidence"]
        ],
    }
    try:
        ratification = build_ratification_receipt(
            pack=evaluated_pack,
            evidence_bundle=evidence,
            private_key_pem=authorities.ratifier_private_key_pem,
            ratifier_ref=authorities.ratifier_ref,
            faithfulness_refs=list(source_identity["source_receipt_refs"]),
            checker_evidence_refs=[
                str(shadow["receipt_digest"]),
                str(lowering["receipt_sha256"]),
            ],
            trusted_base_resolver_public_key_pem=authorities.base_resolver_public_key_pem,
            trusted_task_manifest_public_key_pem=authorities.task_manifest_public_key_pem,
            trusted_shadow_checker_public_key_pem=authorities.shadow_checker_public_key_pem,
            trusted_lowering_checker_public_key_pem=authorities.lowering_checker_public_key_pem,
            trusted_semantic_fidelity_public_key_pem=(
                authorities.semantic_fidelity_public_key_pem or None
            ),
            run_id=f"{source_identity['campaign_id']}:{source_identity['attempt_id']}",
        )
        promoted = promote_axiom_pack(
            evaluated_pack,
            ratification,
            trusted_public_key_pem=authorities.ratifier_public_key_pem,
            trusted_base_resolver_public_key_pem=authorities.base_resolver_public_key_pem,
            trusted_task_manifest_public_key_pem=authorities.task_manifest_public_key_pem,
            trusted_shadow_checker_public_key_pem=authorities.shadow_checker_public_key_pem,
            trusted_lowering_checker_public_key_pem=authorities.lowering_checker_public_key_pem,
            trusted_semantic_fidelity_public_key_pem=(
                authorities.semantic_fidelity_public_key_pem or None
            ),
        )
    except (TypeError, ValueError) as exc:
        core = {
            "schema": PROMOTION_TRANSITION_SCHEMA,
            "status": "promotion_rejected",
            "stage": "ratification",
            "pack_digest": current_pack_digest,
            "source_identity_sha256": source_identity_sha,
            "shadow_yield": shadow,
            "conditional_lowering": lowering,
            "stress_report": stress,
            "failures": [f"{type(exc).__name__}:{exc}"],
            "promotion_kind": "axiom_pack_contract_lane",
            "frontier_theorem_certificate_consumed": False,
            "proof_credit_eligible": False,
            "theorem_campaign_admissible": False,
        }
        return _receipt(core)

    core = {
        "schema": PROMOTION_TRANSITION_SCHEMA,
        "status": "promoted",
        "stage": "complete",
        "pack_digest": current_pack_digest,
        "source_identity_sha256": source_identity_sha,
        "shadow_yield": shadow,
        "conditional_lowering": lowering,
        "stress_report": stress,
        "ratification_receipt": ratification,
        "promoted_pack": promoted.to_json(),
        "promotion_kind": "axiom_pack_contract_lane",
        "frontier_theorem_certificate_consumed": False,
        "proof_credit_eligible": False,
        "theorem_campaign_admissible": True,
    }
    return _receipt(core)


def advance_axiom_pack_promotion_directory(
    campaign_dir: str | Path,
    *,
    authorities: AxiomPackPromotionAuthorities | None,
    compile_fn: Callable[[str], bool | None] | None = None,
    lean_root: str | Path | None = None,
) -> Path:
    """Load canonical stage artifacts and persist one immutable transition."""

    directory = Path(campaign_dir)
    admission = read_json(directory / ADMISSION_FILE, None)
    manifest = read_json(directory / MANIFEST_FILE, None)
    baseline = read_json(directory / BASELINE_FILE, None)
    treatment = read_json(directory / TREATMENT_FILE, None)
    state = {
        "admission": admission,
        "task_manifest": manifest,
        "baseline_batch": baseline,
        "treatment_batch": treatment,
    }
    state_digest = content_hash(state)
    output = directory / f"axiom_pack_promotion_transition.{state_digest[:16]}.json"
    if output.is_file():
        prior = read_json(output, None)
        if isinstance(prior, Mapping):
            core = {key: value for key, value in prior.items() if key != "receipt_sha256"}
            if prior.get("receipt_sha256") == content_hash(core):
                return output
        raise ValueError("persisted AxiomPack promotion transition does not replay")
    result = advance_axiom_pack_promotion(
        admission=admission if isinstance(admission, Mapping) else None,
        task_manifest=manifest if isinstance(manifest, Mapping) else None,
        baseline_batch=baseline if isinstance(baseline, Mapping) else None,
        treatment_batch=treatment if isinstance(treatment, Mapping) else None,
        authorities=authorities,
        compile_fn=compile_fn,
        lean_root=lean_root,
    )
    write_json_atomic(output, result)
    if result.get("status") == "promoted":
        write_json_atomic(
            directory / f"axiom_pack_promoted.{state_digest[:16]}.json",
            result["promoted_pack"],
        )
    return output


__all__ = [
    "ADMISSION_FILE",
    "BASELINE_FILE",
    "MANIFEST_FILE",
    "PROMOTION_ADMISSION_SCHEMA",
    "PROMOTION_BLOCKER_SCHEMA",
    "PROMOTION_SOURCE_IDENTITY_SCHEMA",
    "PROMOTION_TRANSITION_SCHEMA",
    "SHADOW_ATTEMPT_BATCH_SCHEMA",
    "TREATMENT_FILE",
    "AxiomPackPromotionAuthorities",
    "advance_axiom_pack_promotion",
    "advance_axiom_pack_promotion_directory",
    "build_axiom_pack_promotion_admission",
    "build_axiom_pack_promotion_admission_from_birth",
    "build_axiom_pack_source_identity",
    "build_shadow_attempt_batch",
    "inspect_preserved_pack_candidate",
]
