from __future__ import annotations

import copy
from dataclasses import replace
import hashlib

from ztare.leanmill.axiom_authority import build_base_theory_resolution, pack_digest
from ztare.leanmill.axiom_pack import AxiomPack, run_semantic_cheap_filters
from ztare.leanmill.axiom_pack_promotion_campaign import (
    AxiomPackPromotionAuthorities,
    advance_axiom_pack_promotion,
    build_axiom_pack_promotion_admission,
    build_axiom_pack_source_identity,
    build_shadow_attempt_batch,
    inspect_preserved_pack_candidate,
)
from ztare.leanmill.axiom_yield import (
    ShadowAttempt,
    ShadowTask,
    build_shadow_attempt_verification,
    build_shadow_task_manifest,
    evaluate_candidate_dependency,
)
from ztare.leanmill.formal_verification_provider import generate_keypair
from ztare.leanmill.finite_model import FiniteModel
from ztare.leanmill.theory_ir import (
    AxiomFormula,
    Binder,
    Formula,
    RelationSymbol,
    SortDecl,
    Term,
    TheorySignature,
    content_hash,
    theory_content_hash,
)


_MANIFEST_PRIVATE, _MANIFEST_PUBLIC = generate_keypair()
_SHADOW_PRIVATE, _SHADOW_PUBLIC = generate_keypair()
_BASE_PRIVATE, _BASE_PUBLIC = generate_keypair()
_LOWERING_PRIVATE, _LOWERING_PUBLIC = generate_keypair()
_RATIFIER_PRIVATE, _RATIFIER_PUBLIC = generate_keypair()


def _sha(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _theory() -> tuple[TheorySignature, AxiomFormula]:
    signature = TheorySignature(
        name="Predicate",
        sorts=(SortDecl("Carrier"),),
        relations=(RelationSymbol("P", ("Carrier",)),),
    )
    axiom = AxiomFormula(
        "all_p",
        Formula.forall(
            (Binder("x", "Carrier"),),
            Formula.rel("P", Term.var("x")),
        ),
    )
    return signature, axiom


def _authorities() -> AxiomPackPromotionAuthorities:
    return AxiomPackPromotionAuthorities(
        ratifier_private_key_pem=_RATIFIER_PRIVATE,
        ratifier_public_key_pem=_RATIFIER_PUBLIC,
        base_resolver_public_key_pem=_BASE_PUBLIC,
        task_manifest_public_key_pem=_MANIFEST_PUBLIC,
        shadow_checker_public_key_pem=_SHADOW_PUBLIC,
        lowering_checker_private_key_pem=_LOWERING_PRIVATE,
        lowering_checker_public_key_pem=_LOWERING_PUBLIC,
    )


def _campaign_inputs() -> dict:
    signature, axiom = _theory()
    source_ref = "theory-program:" + content_hash({"candidate": "all_p"})
    pack = AxiomPack(
        name="predicate_candidate",
        domain="finite_algebra",
        extends_theory="explicit_empty_base",
        candidate_axioms=[
            {
                "name": axiom.name,
                "formula": axiom.formula.to_json(),
                "axiom_hash": axiom.content_hash,
            }
        ],
        intended_unlocks=["heldout-1"],
        provenance=[source_ref],
        downstream_residuals=["missing_all_p_rewrite"],
        theory_signature=signature.to_json(),
        base_theory_resolved=True,
    )
    pack = replace(
        pack,
        stress_receipts=run_semantic_cheap_filters(
            pack,
            min_carrier_size=2,
            max_carrier_size=2,
        ),
    )
    source_identity = build_axiom_pack_source_identity(
        pack=pack,
        campaign_id="campaign:promotion-test",
        attempt_id="attempt:001",
        context_hash=_sha("context"),
        context_epoch=2,
        source_pack_ref=source_ref,
        source_receipt_refs=[_sha("selection-receipt")],
    )
    admission = build_axiom_pack_promotion_admission(
        pack=pack,
        source_identity=source_identity,
        base_theory_resolution=build_base_theory_resolution(
            pack=pack,
            source_ref="test:explicit-empty-base",
            private_key_pem=_BASE_PRIVATE,
            verifier_ref="test-base-resolver",
            faithfulness_refs=[_sha("base-faithfulness")],
            explicit_empty=True,
        ),
    )
    tasks = [
        ShadowTask(
            task_id=f"heldout-{index}",
            input_digest=_sha(f"input-{index}"),
            budget_units=100,
        )
        for index in (1, 2)
    ]
    admission_digests = {
        task.task_id: _sha(f"formalization-admission:{task.task_id}")
        for task in tasks
    }
    base_digest = theory_content_hash(signature, ())
    manifest = build_shadow_task_manifest(
        tasks=tasks,
        base_theory_digest=base_digest,
        admission_digests=admission_digests,
        private_key_pem=_MANIFEST_PRIVATE,
        verifier_ref="test-manifest-checker",
        manifest_evidence_ref=_sha("manifest-evidence"),
    )
    manifest_digest = manifest["metadata"]["manifest_digest"]
    current_pack_digest = pack_digest(pack)
    baseline: list[ShadowAttempt] = []
    treatment: list[ShadowAttempt] = []
    for index, task in enumerate(tasks):
        environment = _sha(f"environment:{task.task_id}")
        left = ShadowAttempt(
            task_id=task.task_id,
            task_digest=task.content_digest,
            arm="baseline",
            budget_units=task.budget_units,
            budget_kind=task.budget_kind,
            status="failed",
            admission_digest=admission_digests[task.task_id],
            environment_ref=environment,
            transcript_ref=_sha(f"baseline:{task.task_id}"),
            failure_class="missing_lemma",
        )
        left = replace(
            left,
            verification_payload=build_shadow_attempt_verification(
                task=task,
                attempt=left,
                private_key_pem=_SHADOW_PRIVATE,
                verifier_ref="test-shadow-checker",
                task_manifest_digest=manifest_digest,
                pack_digest=current_pack_digest,
                base_theory_digest=base_digest,
                candidate_axiom_hashes=[axiom.content_hash],
            ),
        )
        if index == 0:
            right = ShadowAttempt(
                task_id=task.task_id,
                task_digest=task.content_digest,
                arm="treatment",
                budget_units=task.budget_units,
                budget_kind=task.budget_kind,
                status="solved",
                admission_digest=admission_digests[task.task_id],
                environment_ref=environment,
                transcript_ref=_sha(f"treatment:{task.task_id}"),
                kernel_checked=True,
                proof_digest=_sha(f"proof:{task.task_id}"),
                proof_size=9,
                used_axiom_hashes=(axiom.content_hash,),
            )
            dependency = evaluate_candidate_dependency(
                task_digest=task.content_digest,
                proof_digest=right.proof_digest,
                pack_digest=current_pack_digest,
                base_theory_digest=base_digest,
                candidate_axiom_hashes=[axiom.content_hash],
                replay_fn=lambda retained: retained == (axiom.content_hash,),
            )
        else:
            right = ShadowAttempt(
                task_id=task.task_id,
                task_digest=task.content_digest,
                arm="treatment",
                budget_units=task.budget_units,
                budget_kind=task.budget_kind,
                status="timeout",
                admission_digest=admission_digests[task.task_id],
                environment_ref=environment,
                transcript_ref=_sha(f"treatment:{task.task_id}"),
                failure_class="budget_exhausted",
            )
            dependency = None
        right = replace(
            right,
            verification_payload=build_shadow_attempt_verification(
                task=task,
                attempt=right,
                private_key_pem=_SHADOW_PRIVATE,
                verifier_ref="test-shadow-checker",
                task_manifest_digest=manifest_digest,
                pack_digest=current_pack_digest,
                base_theory_digest=base_digest,
                candidate_axiom_hashes=[axiom.content_hash],
                dependency_receipt=dependency,
            ),
        )
        baseline.append(left)
        treatment.append(right)
    batches = {
        "baseline": build_shadow_attempt_batch(
            arm="baseline",
            attempts=baseline,
            pack_digest_value=current_pack_digest,
            task_manifest_digest=manifest_digest,
            source_identity_sha256=source_identity["identity_sha256"],
        ),
        "treatment": build_shadow_attempt_batch(
            arm="treatment",
            attempts=treatment,
            pack_digest_value=current_pack_digest,
            task_manifest_digest=manifest_digest,
            source_identity_sha256=source_identity["identity_sha256"],
        ),
    }
    return {
        "admission": admission,
        "task_manifest": manifest,
        "baseline_batch": batches["baseline"],
        "treatment_batch": batches["treatment"],
        "authorities": _authorities(),
        "compile_fn": lambda _source: True,
    }


def test_admitted_pack_reaches_content_bound_promotion() -> None:
    result = advance_axiom_pack_promotion(**_campaign_inputs())

    assert result["status"] == "promoted"
    assert result["shadow_yield"]["ok"] is True
    assert result["conditional_lowering"]["kernel_checked"] is True
    assert result["stress_report"]["ok"] is True
    assert result["promoted_pack"]["promotion_status"] == "promoted"
    assert result["frontier_theorem_certificate_consumed"] is False
    assert result["ratification_receipt"]["pack_digest"] == result["pack_digest"]


def test_source_or_attempt_tampering_fails_closed() -> None:
    source_tamper = _campaign_inputs()
    source_tamper["admission"] = copy.deepcopy(source_tamper["admission"])
    source_tamper["admission"]["source_identity"]["context_epoch"] = 3
    rejected_source = advance_axiom_pack_promotion(**source_tamper)
    assert rejected_source["status"] == "blocked_missing_artifact"
    assert rejected_source["next_required_field"] == (
        "axiom_pack_promotion_admission.admission_sha256"
    )

    attempt_tamper = _campaign_inputs()
    treatment = [
        ShadowAttempt.from_json(row)
        for row in attempt_tamper["treatment_batch"]["attempts"]
    ]
    treatment[0] = replace(treatment[0], environment_ref=_sha("rebound-environment"))
    source_identity = attempt_tamper["admission"]["source_identity"]
    attempt_tamper["treatment_batch"] = build_shadow_attempt_batch(
        arm="treatment",
        attempts=treatment,
        pack_digest_value=attempt_tamper["admission"]["pack_digest"],
        task_manifest_digest=attempt_tamper["task_manifest"]["metadata"]["manifest_digest"],
        source_identity_sha256=source_identity["identity_sha256"],
    )
    rejected_attempt = advance_axiom_pack_promotion(**attempt_tamper)
    assert rejected_attempt["status"] == "promotion_rejected"
    assert any(
        "shadow_yield:fail" == failure for failure in rejected_attempt["failures"]
    )


def test_authority_role_collapse_is_a_typed_blocker() -> None:
    inputs = _campaign_inputs()
    authority = inputs["authorities"]
    inputs["authorities"] = replace(
        authority,
        shadow_checker_public_key_pem=authority.task_manifest_public_key_pem,
    )
    result = advance_axiom_pack_promotion(**inputs)

    assert result["status"] == "blocked_missing_artifact"
    assert result["next_required_field"] == "promotion_authorities.role_separation"


def test_finite_witness_is_replayed_after_self_hashes_are_rebuilt() -> None:
    inputs = _campaign_inputs()
    admission = copy.deepcopy(inputs["admission"])
    inputs["admission"] = admission
    receipts = admission["pack"]["stress_receipts"]
    semantic = next(row for row in receipts if row["dimension"] == "semantic_certification")
    suite = semantic["suite"]
    joint = suite["joint_satisfiability"]
    joint["witness"]["model"]["relations"]["P"][0] = False
    signature, _axiom = _theory()
    model = FiniteModel.from_json(joint["witness"]["model"])
    joint["witness"]["model_sha256"] = model.content_hash(signature)

    def rehash(row: dict) -> str:
        core = {
            key: value
            for key, value in row.items()
            if key not in {"receipt_sha256", "certificate_digest"}
        }
        digest = content_hash(core)
        row["certificate_digest"] = digest
        row["receipt_sha256"] = digest
        return digest

    rehash(joint)
    suite_digest = rehash(suite)
    for row in receipts:
        if row["dimension"] in {
            "nontriviality",
            "consistency_smoke",
            "model_or_example",
            "strength_comparison",
            "separation_or_interpretation",
        }:
            row["semantic_suite_digest"] = suite_digest
            row["receipt_sha256"] = content_hash(
                {key: value for key, value in row.items() if key != "receipt_sha256"}
            )
    semantic["receipt_sha256"] = content_hash(
        {key: value for key, value in semantic.items() if key != "receipt_sha256"}
    )
    admission["admission_sha256"] = "sha256:" + content_hash(
        {key: value for key, value in admission.items() if key != "admission_sha256"}
    )

    result = advance_axiom_pack_promotion(**inputs)
    assert result["status"] == "promotion_rejected"
    assert any("semantic_suite_replay_failed" in failure for failure in result["failures"])


def test_preserved_legacy_pack_names_first_missing_identity_field() -> None:
    result = inspect_preserved_pack_candidate(
        {
            "pack": {
                "schema": "leanmill.axiom_pack.v1",
                "name": "legacy",
                "domain": "finite_algebra",
                "extends_theory": "Base",
                "candidate_axioms": [{"name": "prose_only", "statement": "x=x"}],
                "intended_unlocks": ["heldout"],
                "provenance": ["live_agent_isomorphism"],
                "downstream_residuals": ["missing"],
                "promotion_status": "quarantined",
            }
        }
    )

    assert result["status"] == "blocked_missing_artifact"
    assert result["next_required_field"] == "pack.theory_signature"
