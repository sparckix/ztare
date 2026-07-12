from __future__ import annotations

import copy
from dataclasses import replace
import hashlib

import pytest

from ztare.leanmill.axiom_authority import (
    build_base_theory_resolution,
    build_ratification_receipt,
    pack_digest,
    verify_base_theory_resolution,
    verify_ratification_receipt,
)
from ztare.leanmill.axiom_yield import (
    ShadowAttempt,
    ShadowTask,
    build_shadow_attempt_verification,
    build_shadow_task_manifest,
    evaluate_candidate_dependency,
    evaluate_shadow_ab,
    rank_shadow_tasks,
    verify_shadow_yield_receipt,
)
from ztare.leanmill.axiom_lowering import (
    certify_conditional_lowering,
    verify_conditional_lowering_receipt,
)
from ztare.leanmill.formal_verification_provider import generate_keypair
from ztare.leanmill.axiom_pack import (
    AxiomPack,
    promote_axiom_pack,
    stress_axiom_pack,
    stress_pack_for_domain,
    theorem_campaign_consumption_gate,
)
from ztare.leanmill.finite_model import FiniteSearchBounds, certify_theory
from ztare.leanmill.theory_ir import (
    AxiomFormula,
    Binder,
    Formula,
    RelationSymbol,
    SortDecl,
    Term,
    TheorySignature,
    theory_content_hash,
)
from ztare.leanmill.typed_axiom_proposal import (
    admit_axiom_template,
    build_semantic_fidelity_verdict,
    build_typed_axiom_proposal,
)
from ztare.research_signals import engine_registry


_SHADOW_MANIFEST_PRIVATE, _SHADOW_MANIFEST_PUBLIC = generate_keypair()
_SHADOW_CHECKER_PRIVATE, _SHADOW_CHECKER_PUBLIC = generate_keypair()
_BASE_RESOLVER_PRIVATE, _BASE_RESOLVER_PUBLIC = generate_keypair()
_LOWERING_CHECKER_PRIVATE, _LOWERING_CHECKER_PUBLIC = generate_keypair()

_TRUSTED_EVIDENCE_KEYS = {
    "trusted_base_resolver_public_key_pem": _BASE_RESOLVER_PUBLIC,
    "trusted_task_manifest_public_key_pem": _SHADOW_MANIFEST_PUBLIC,
    "trusted_shadow_checker_public_key_pem": _SHADOW_CHECKER_PUBLIC,
    "trusted_lowering_checker_public_key_pem": _LOWERING_CHECKER_PUBLIC,
}


def _sha(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _admission_digest(task_id: str) -> str:
    return _sha(f"formalization-admission:{task_id}")


def _signature_and_axiom() -> tuple[TheorySignature, AxiomFormula]:
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


def _shadow_report(
    *,
    pack: dict | None = None,
    budget_delta: int = 0,
    used_hash: str | None = None,
    task_count: int = 2,
    unsigned_baseline: bool = False,
    admission_mismatch: bool = False,
    environment_mismatch: bool = False,
    tamper_manifest_split: bool = False,
    collapse_authority_roles: bool = False,
) -> dict:
    pack = pack or _pack()
    signature, axiom = _signature_and_axiom()
    used_hash = used_hash or axiom.content_hash
    current_pack_digest = pack_digest(pack)
    base_digest = theory_content_hash(signature, ())
    tasks = [
        ShadowTask(
            task_id=f"heldout-{index}",
            input_digest=_sha(f"input-{index}"),
            budget_units=100,
        )
        for index in range(1, task_count + 1)
    ]
    admission_digests = {
        task.task_id: _admission_digest(task.task_id) for task in tasks
    }
    manifest = build_shadow_task_manifest(
        tasks=tasks,
        base_theory_digest=base_digest,
        admission_digests=admission_digests,
        private_key_pem=(
            _SHADOW_CHECKER_PRIVATE if collapse_authority_roles else _SHADOW_MANIFEST_PRIVATE
        ),
        verifier_ref="test-shadow-manifest-checker",
        manifest_evidence_ref=_sha("shadow-task-manifest-evidence"),
    )
    manifest_digest = manifest["metadata"]["manifest_digest"]
    baseline_attempts: list[ShadowAttempt] = []
    treatment_attempts: list[ShadowAttempt] = []
    for index, task in enumerate(tasks):
        environment_ref = _sha(f"environment-{task.task_id}")
        baseline = ShadowAttempt(
            task_id=task.task_id,
            task_digest=task.content_digest,
            arm="baseline",
            budget_units=100,
            budget_kind="tokens",
            status="failed",
            admission_digest=admission_digests[task.task_id],
            environment_ref=environment_ref,
            transcript_ref=_sha(f"baseline-transcript-{task.task_id}"),
            failure_class="missing_lemma",
        )
        baseline = replace(
            baseline,
            verification_payload=build_shadow_attempt_verification(
                task=task,
                attempt=baseline,
                private_key_pem=_SHADOW_CHECKER_PRIVATE,
                verifier_ref="test-shadow-checker",
                task_manifest_digest=manifest_digest,
                pack_digest=current_pack_digest,
                base_theory_digest=base_digest,
                candidate_axiom_hashes=[axiom.content_hash],
            ),
        )
        if unsigned_baseline and index == 0:
            baseline = replace(baseline, verification_payload={})
        if index == 0:
            treatment = ShadowAttempt(
                task_id=task.task_id,
                task_digest=task.content_digest,
                arm="treatment",
                budget_units=100,
                budget_kind="tokens",
                status="solved",
                admission_digest=admission_digests[task.task_id],
                environment_ref=environment_ref,
                transcript_ref=_sha(f"treatment-transcript-{task.task_id}"),
                kernel_checked=True,
                proof_digest=_sha(f"proof-{task.task_id}"),
                proof_size=12,
                used_axiom_hashes=(used_hash,),
            )
            dependency = evaluate_candidate_dependency(
                task_digest=task.content_digest,
                proof_digest=treatment.proof_digest,
                pack_digest=current_pack_digest,
                base_theory_digest=base_digest,
                candidate_axiom_hashes=[axiom.content_hash],
                replay_fn=lambda retained: retained == (axiom.content_hash,),
            )
        else:
            treatment = ShadowAttempt(
                task_id=task.task_id,
                task_digest=task.content_digest,
                arm="treatment",
                budget_units=100,
                budget_kind="tokens",
                status="timeout",
                admission_digest=admission_digests[task.task_id],
                environment_ref=environment_ref,
                transcript_ref=_sha(f"treatment-transcript-{task.task_id}"),
                failure_class="budget_exhausted",
            )
            dependency = None
        treatment = replace(
            treatment,
            verification_payload=build_shadow_attempt_verification(
                task=task,
                attempt=treatment,
                private_key_pem=_SHADOW_CHECKER_PRIVATE,
                verifier_ref="test-shadow-checker",
                task_manifest_digest=manifest_digest,
                pack_digest=current_pack_digest,
                base_theory_digest=base_digest,
                candidate_axiom_hashes=[axiom.content_hash],
                dependency_receipt=dependency,
            ),
        )
        if index == 0 and budget_delta:
            treatment = replace(treatment, budget_units=100 + budget_delta)
        if index == 0 and admission_mismatch:
            treatment = replace(
                treatment,
                admission_digest=(
                    admission_digests[tasks[1].task_id]
                    if len(tasks) > 1
                    else _sha("other-admission")
                ),
            )
        if index == 0 and environment_mismatch:
            treatment = replace(treatment, environment_ref=_sha("other-environment"))
        baseline_attempts.append(baseline)
        treatment_attempts.append(treatment)
    if tamper_manifest_split:
        manifest = copy.deepcopy(manifest)
        manifest["metadata"]["manifest"]["tasks"][0]["split"] = "discovery"
    return evaluate_shadow_ab(
        pack_digest=current_pack_digest,
        base_theory_digest=base_digest,
        allowed_axiom_hashes=[axiom.content_hash],
        task_manifest=manifest,
        baseline_attempts=baseline_attempts,
        treatment_attempts=treatment_attempts,
        trusted_checker_public_key_pem=_SHADOW_CHECKER_PUBLIC,
        trusted_manifest_public_key_pem=(
            _SHADOW_CHECKER_PUBLIC if collapse_authority_roles else _SHADOW_MANIFEST_PUBLIC
        ),
    )


def _pack() -> dict:
    signature, axiom = _signature_and_axiom()
    return {
        "schema": "leanmill.axiom_pack.v1",
        "name": "candidate",
        "domain": "finite_algebra",
        "extends_theory": "Base",
        "theory_signature": signature.to_json(),
        "base_axioms": [],
        "base_theory_resolved": True,
        "candidate_axioms": [
            {
                "name": axiom.name,
                "formula": axiom.formula.to_json(),
                "axiom_hash": axiom.content_hash,
            }
        ],
        "intended_unlocks": ["heldout-1"],
        "provenance": ["test"],
        "downstream_residuals": ["missing_lemma"],
        "promotion_status": "quarantined",
    }


def _evidence(pack: dict | None = None) -> dict:
    pack = pack or _pack()
    signature, axiom = _signature_and_axiom()
    return {
        "base_theory_resolution": build_base_theory_resolution(
            pack=pack,
            source_ref="test:explicit-empty-base",
            private_key_pem=_BASE_RESOLVER_PRIVATE,
            verifier_ref="test-base-resolver",
            faithfulness_refs=["test:base-resolution-faithfulness"],
            explicit_empty=True,
        ),
        "stress_report": {
            "schema": "leanmill.axiom_pack_stress.v1",
            "ok": True,
            "pack_digest": pack_digest(pack),
            "missing_stress_receipts": [],
            "validated_receipts": [
                {"dimension": "nontriviality", "status": "pass"},
                {"dimension": "consistency_smoke", "status": "pass"},
                {"dimension": "model_or_example", "status": "pass"},
                {"dimension": "strength_comparison", "status": "pass"},
                {"dimension": "separation_or_interpretation", "status": "pass"},
                {"dimension": "downstream_yield", "status": "pass"},
            ],
        },
        "semantic_certification": certify_theory(
            signature,
            (axiom,),
            FiniteSearchBounds(min_carrier_size=2, max_carrier_size=2),
        ).to_json(),
        "downstream_yield": _shadow_report(pack=pack),
        "lean_lowering": certify_conditional_lowering(
            signature,
            (axiom,),
            compile_fn=lambda _source: True,
            checker_private_key_pem=_LOWERING_CHECKER_PRIVATE,
        ),
    }


def test_research_signal_facade_names_canonical_engines() -> None:
    registry = engine_registry()
    assert set(registry) == {
        "loop_control",
        "experiment_pricing",
        "residual_information_yield",
        "compression_progress",
        "mdl_library",
    }
    assert registry["loop_control"]["callable_ref"].endswith("evaluate_information_yield")
    assert registry["residual_information_yield"]["callable_ref"].endswith(
        "residual_information_yield"
    )


def test_shadow_ab_requires_matched_budget_and_bound_axiom_use() -> None:
    good = _shadow_report()
    assert good["ok"] is True
    assert good["attributable_improvements"] == 1
    assert good["task_count"] == 2
    assert good["admission_digests"] == {
        "heldout-1": _admission_digest("heldout-1"),
        "heldout-2": _admission_digest("heldout-2"),
    }
    assert "pack_digest" not in good["task_manifest"]["metadata"]["manifest"]
    assert good["paired_results"][1]["treatment_status"] == "timeout"
    assert verify_shadow_yield_receipt(
        good,
        trusted_checker_public_key_pem=_SHADOW_CHECKER_PUBLIC,
        trusted_manifest_public_key_pem=_SHADOW_MANIFEST_PUBLIC,
    ) is True
    assert verify_shadow_yield_receipt(
        good,
        trusted_checker_public_key_pem=_SHADOW_CHECKER_PUBLIC,
        trusted_manifest_public_key_pem=_SHADOW_CHECKER_PUBLIC,
    ) is False
    assert good["loop_control"]["treatment"]["canonical_engine"].endswith(
        "evaluate_information_yield"
    )

    mismatched = _shadow_report(budget_delta=1)
    assert mismatched["ok"] is False
    assert "budget_mismatch" in {row["type"] for row in mismatched["violations"]}

    with pytest.raises(ValueError, match="used_axiom_hashes"):
        _shadow_report(used_hash="sha256:other")


def test_shadow_ab_rejects_unsigned_or_rebound_outcomes() -> None:
    unsigned = _shadow_report(unsigned_baseline=True)
    assert unsigned["ok"] is False
    assert "shadow_attempt_verification_missing" in {
        row["type"] for row in unsigned["violations"]
    }

    rebound_admission = _shadow_report(admission_mismatch=True)
    assert rebound_admission["ok"] is False
    assert {"admission_digest", "arm_admission_mismatch"} <= {
        row["type"] for row in rebound_admission["violations"]
    }

    rebound_environment = _shadow_report(environment_mismatch=True)
    assert rebound_environment["ok"] is False
    assert "arm_environment_mismatch" in {
        row["type"] for row in rebound_environment["violations"]
    }


def test_shadow_ab_requires_signed_frozen_manifest_and_two_eval_tasks() -> None:
    one_task = _shadow_report(task_count=1)
    assert one_task["ok"] is False
    assert "insufficient_eval_tasks" in {row["type"] for row in one_task["violations"]}

    altered_split = _shadow_report(tamper_manifest_split=True)
    assert altered_split["ok"] is False
    assert "task_manifest.provider_signature" in {
        row["type"] for row in altered_split["violations"]
    }

    collapsed_roles = _shadow_report(collapse_authority_roles=True)
    assert collapsed_roles["ok"] is False
    assert "authority_role_collapse" in {
        row["type"] for row in collapsed_roles["violations"]
    }


def test_shadow_manifest_does_not_count_duplicated_tasks_or_admissions() -> None:
    signature, _axiom = _signature_and_axiom()
    duplicate_tasks = [
        ShadowTask("heldout-a", _sha("same-input"), 100),
        ShadowTask("heldout-b", _sha("same-input"), 100),
    ]
    with pytest.raises(ValueError, match="distinct input digests"):
        build_shadow_task_manifest(
            tasks=duplicate_tasks,
            base_theory_digest=theory_content_hash(signature, ()),
            admission_digests={
                "heldout-a": _sha("admission-a"),
                "heldout-b": _sha("admission-b"),
            },
            private_key_pem=_SHADOW_MANIFEST_PRIVATE,
            verifier_ref="test-shadow-manifest-checker",
            manifest_evidence_ref=_sha("manifest-evidence"),
        )

    distinct_tasks = [
        ShadowTask("heldout-a", _sha("input-a"), 100),
        ShadowTask("heldout-b", _sha("input-b"), 100),
    ]
    with pytest.raises(ValueError, match="distinct admission digests"):
        build_shadow_task_manifest(
            tasks=distinct_tasks,
            base_theory_digest=theory_content_hash(signature, ()),
            admission_digests={
                "heldout-a": _sha("same-admission"),
                "heldout-b": _sha("same-admission"),
            },
            private_key_pem=_SHADOW_MANIFEST_PRIVATE,
            verifier_ref="test-shadow-manifest-checker",
            manifest_evidence_ref=_sha("manifest-evidence"),
        )


def test_shadow_task_ranking_reuses_canonical_experiment_pricer() -> None:
    tasks = [
        ShadowTask("same", "sha256:same", 10),
        ShadowTask("split", "sha256:split", 10),
    ]
    committee = [{"id": 0}, {"id": 1}]
    report = rank_shadow_tasks(
        committee=committee,
        tasks=tasks,
        predict=lambda member, task: 0 if task.task_id == "same" else member["id"],
        size_fn=lambda _member: 1,
        previously_observed_task_ids=["same", "split"],
    )
    assert report["canonical_engine"].endswith("price_experiment")
    assert [row["task_id"] for row in report["ranked_tasks"]] == ["split", "same"]


def test_dependency_ablation_does_not_invent_minimal_hashes_under_redundancy() -> None:
    receipt = evaluate_candidate_dependency(
        task_digest="sha256:task",
        proof_digest="sha256:proof",
        pack_digest="sha256:pack",
        base_theory_digest="sha256:base",
        candidate_axiom_hashes=["a", "b"],
        replay_fn=lambda retained: bool(retained),
    )
    assert receipt["status"] == "pass"
    assert receipt["pack_required"] is True
    assert receipt["indispensable_axiom_hashes"] == []


def test_dependency_ablation_exception_is_inconclusive() -> None:
    def replay(retained: tuple[str, ...]) -> bool:
        if not retained:
            raise TimeoutError("checker unavailable")
        return True

    receipt = evaluate_candidate_dependency(
        task_digest="sha256:task",
        proof_digest="sha256:proof",
        pack_digest="sha256:pack",
        base_theory_digest="sha256:base",
        candidate_axiom_hashes=["a"],
        replay_fn=replay,
    )
    assert receipt["status"] == "inconclusive"
    assert receipt["replay_complete"] is False


def test_conditional_lowering_receipt_binds_compiled_source_without_global_axioms() -> None:
    signature, axiom = _signature_and_axiom()
    seen: list[str] = []
    receipt = certify_conditional_lowering(
        signature,
        (axiom,),
        compile_fn=lambda source: seen.append(source) or True,
        checker_private_key_pem=_LOWERING_CHECKER_PRIVATE,
    )
    assert receipt["status"] == "pass"
    assert receipt["kernel_checked"] is True
    assert receipt["contains_global_axiom"] is False
    assert receipt["contains_sorry"] is False
    assert "class CandidateAxiomPack" in seen[0]
    assert verify_conditional_lowering_receipt(
        signature,
        (axiom,),
        receipt,
        trusted_checker_public_key_pem=_LOWERING_CHECKER_PUBLIC,
    )[0] is True
    altered = copy.deepcopy(receipt)
    altered["source"] += "\n-- changed"
    assert verify_conditional_lowering_receipt(
        signature,
        (axiom,),
        altered,
        trusted_checker_public_key_pem=_LOWERING_CHECKER_PUBLIC,
    )[0] is False


def test_signed_ratification_is_bound_to_pack_and_evidence() -> None:
    pack = _pack()
    private_key, public_key = generate_keypair()
    with pytest.raises(ValueError, match="ratifier key must be separate"):
        build_ratification_receipt(
            pack=pack,
            evidence_bundle=_evidence(pack),
            private_key_pem=_BASE_RESOLVER_PRIVATE,
            ratifier_ref="collapsed-ratifier",
            faithfulness_refs=["semantic:sha256:semantic"],
            checker_evidence_refs=["lean:sha256:lean"],
            **_TRUSTED_EVIDENCE_KEYS,
        )
    receipt = build_ratification_receipt(
        pack=pack,
        evidence_bundle=_evidence(pack),
        private_key_pem=private_key,
        ratifier_ref="test-ratifier",
        faithfulness_refs=["semantic:sha256:semantic"],
        checker_evidence_refs=["lean:sha256:lean"],
        **_TRUSTED_EVIDENCE_KEYS,
    )
    verified = verify_ratification_receipt(
        pack=pack,
        receipt=receipt,
        trusted_public_key_pem=public_key,
        **_TRUSTED_EVIDENCE_KEYS,
    )
    assert verified["allowed"] is True
    assert verified["signature_verified"] is True

    base_receipt = receipt["evidence_bundle"]["base_theory_resolution"]
    assert verify_base_theory_resolution(
        pack=pack,
        receipt=base_receipt,
        trusted_public_key_pem=_BASE_RESOLVER_PUBLIC,
    )[0] is True

    promoted = promote_axiom_pack(
        AxiomPack.from_json(pack),
        receipt,
        trusted_public_key_pem=public_key,
        **_TRUSTED_EVIDENCE_KEYS,
    )
    assert promoted.promotion_status == "promoted"
    assert theorem_campaign_consumption_gate(
        promoted,
        receipt,
        trusted_public_key_pem=public_key,
        **_TRUSTED_EVIDENCE_KEYS,
    )["allowed"] is True
    assert theorem_campaign_consumption_gate(
        replace(promoted, name="forged"),
        receipt,
        trusted_public_key_pem=public_key,
        **_TRUSTED_EVIDENCE_KEYS,
    )["allowed"] is False

    altered_pack = _pack()
    altered_pack["candidate_axioms"][0]["formula"] = {"kind": "false"}
    assert verify_ratification_receipt(
        pack=altered_pack,
        receipt=receipt,
        trusted_public_key_pem=public_key,
        **_TRUSTED_EVIDENCE_KEYS,
    )["allowed"] is False

    altered_receipt = copy.deepcopy(receipt)
    altered_receipt["evidence_bundle"]["downstream_yield"]["solve_delta"] = 999
    assert verify_ratification_receipt(
        pack=pack,
        receipt=altered_receipt,
        trusted_public_key_pem=public_key,
        **_TRUSTED_EVIDENCE_KEYS,
    )["allowed"] is False

    altered_base = copy.deepcopy(receipt)
    altered_base["evidence_bundle"]["base_theory_resolution"]["subject"][
        "extends_theory"
    ] = "OtherBase"
    assert verify_ratification_receipt(
        pack=pack,
        receipt=altered_base,
        trusted_public_key_pem=public_key,
        **_TRUSTED_EVIDENCE_KEYS,
    )["allowed"] is False

    _, wrong_public_key = generate_keypair()
    assert verify_ratification_receipt(
        pack=pack,
        receipt=receipt,
        trusted_public_key_pem=wrong_public_key,
        **_TRUSTED_EVIDENCE_KEYS,
    )["allowed"] is False


def test_authority_rejects_declared_axiom_hash_formula_split() -> None:
    pack = _pack()
    pack["candidate_axioms"][0]["axiom_hash"] = "sha256:not-the-formula-hash"

    with pytest.raises(ValueError, match="declared axiom_hash mismatch"):
        build_base_theory_resolution(
            pack=pack,
            source_ref="test:explicit-empty-base",
            private_key_pem=_SHADOW_CHECKER_PRIVATE,
            verifier_ref="test-base-resolver",
            faithfulness_refs=["test:base-resolution-faithfulness"],
            explicit_empty=True,
        )


def test_one_axiom_pack_closes_semantic_and_signed_shadow_stress_contract() -> None:
    pack = replace(
        AxiomPack.from_json(_pack()),
        stress_receipts=[_shadow_report()],
    )
    stressed = stress_pack_for_domain(pack)
    report = stress_axiom_pack(
        stressed,
        trusted_task_manifest_public_key_pem=_SHADOW_MANIFEST_PUBLIC,
        trusted_shadow_checker_public_key_pem=_SHADOW_CHECKER_PUBLIC,
    )
    assert report["ok"] is True
    assert report["missing_stress_receipts"] == []
    assert report["semantic_certification"]["status"] == "pass"

def test_ratification_refuses_failed_receipt_status() -> None:
    pack = _pack()
    private_key, _ = generate_keypair()
    evidence = _evidence(pack)
    evidence["stress_report"]["validated_receipts"][0]["status"] = "fail"
    with pytest.raises(ValueError, match="stress_receipt_not_passed"):
        build_ratification_receipt(
            pack=pack,
            evidence_bundle=evidence,
            private_key_pem=private_key,
            ratifier_ref="test-ratifier",
            faithfulness_refs=["semantic:sha256:semantic"],
            checker_evidence_refs=["lean:sha256:lean"],
            **_TRUSTED_EVIDENCE_KEYS,
        )


def test_agent_origin_ratification_replays_typed_proposal_evidence() -> None:
    pack = _pack()
    signature, axiom = _signature_and_axiom()
    source = {
        "schema": "common.structural_conjecture.v1",
        "mother_structure": "the predicate covers the finite carrier",
        "kill_condition": "find a carrier element outside the predicate",
    }
    semantic_private, semantic_public = generate_keypair()
    proposal = build_typed_axiom_proposal(
        source_conjecture=source,
        theory_signature=signature,
        axiom=axiom,
        nl_intent="Every carrier element satisfies the predicate.",
        kill_condition="Reject on a finite model with an element outside P.",
    )
    verdict = build_semantic_fidelity_verdict(
        proposal,
        faithful=True,
        rationale="The universal typed formula matches the conjecture.",
        evidence_refs=["test:typed-candidate-review"],
        private_key_pem=semantic_private,
        verifier_ref="test-semantic-fidelity-checker",
    )
    template = admit_axiom_template(
        proposal,
        verdict,
        trusted_public_key_pem=semantic_public,
        source_conjecture=source,
        expected_verifier_ref="test-semantic-fidelity-checker",
    )
    pack["candidate_axioms"][0] = {
        **template,
        "axiom_hash": axiom.content_hash,
    }
    pack["provenance"].append("agent_authored_blueprint_trial")
    evidence = _evidence(pack)
    evidence["typed_candidate_evidence"] = [
        {
            "source_conjecture": source,
            "typed_axiom_proposal": proposal.to_json(),
            "semantic_fidelity_verdict": verdict.to_json(),
        }
    ]
    ratifier_private, ratifier_public = generate_keypair()
    keys = {
        **_TRUSTED_EVIDENCE_KEYS,
        "trusted_semantic_fidelity_public_key_pem": semantic_public,
    }

    receipt = build_ratification_receipt(
        pack=pack,
        evidence_bundle=evidence,
        private_key_pem=ratifier_private,
        ratifier_ref="test-ratifier",
        faithfulness_refs=["test:semantic-suite"],
        checker_evidence_refs=["test:lean-lowering"],
        **keys,
    )
    assert verify_ratification_receipt(
        pack=pack,
        receipt=receipt,
        trusted_public_key_pem=ratifier_public,
        **keys,
    )["allowed"] is True

    missing = copy.deepcopy(evidence)
    missing.pop("typed_candidate_evidence")
    with pytest.raises(ValueError, match="typed_candidate_evidence_missing"):
        build_ratification_receipt(
            pack=pack,
            evidence_bundle=missing,
            private_key_pem=ratifier_private,
            ratifier_ref="test-ratifier",
            faithfulness_refs=["test:semantic-suite"],
            checker_evidence_refs=["test:lean-lowering"],
            **keys,
        )

    _, wrong_semantic_public = generate_keypair()
    assert verify_ratification_receipt(
        pack=pack,
        receipt=receipt,
        trusted_public_key_pem=ratifier_public,
        **{
            **_TRUSTED_EVIDENCE_KEYS,
            "trusted_semantic_fidelity_public_key_pem": wrong_semantic_public,
        },
    )["allowed"] is False
