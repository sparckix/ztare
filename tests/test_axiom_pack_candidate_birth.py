from __future__ import annotations

import copy
from dataclasses import replace
import hashlib
import json

import pytest

from ztare.leanmill.axiom_authority import build_base_theory_resolution
from ztare.leanmill.axiom_pack import (
    AxiomPack,
    append_axiom_pack_event,
    main as axiom_pack_main,
    priority_uncrossed_order_blueprint,
    run_axiom_pack_discovery_eval,
    run_live_axiom_pack_isomorphism,
)
from ztare.leanmill.axiom_pack_candidate_birth import (
    materialize_typed_axiom_pack_candidate,
    verify_axiom_pack_candidate_birth,
)
from ztare.leanmill.axiom_pack_live_producer import (
    build_live_typed_axiom_pack_runtime,
    build_typed_axiom_proposer_view,
    semantic_checker_output_schema,
    typed_axiom_producer_output_schema,
)
from ztare.leanmill.axiom_pack_promotion_campaign import (
    advance_axiom_pack_promotion,
    build_axiom_pack_promotion_admission_from_birth,
)
from ztare.leanmill.formal_verification_provider import generate_keypair, sha256_ref
from ztare.leanmill.axiom_yield import ShadowTask, build_shadow_task_manifest
from ztare.leanmill.theory_ir import (
    AxiomFormula,
    TheorySignature,
    theory_content_hash,
)
from ztare.leanmill.typed_axiom_proposal import (
    build_semantic_fidelity_verdict,
    build_typed_axiom_proposal,
)


def _canonical_digest(value: object) -> str:
    text = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return sha256_ref(text)


def _eligible_packet(base_digest: str) -> dict:
    core = {
        "schema": "leanmill.axiom_pack_escalation_eligibility.v1",
        "status": "eligible_for_candidate_routing",
        "eligible": True,
        "routing_only": True,
        "promotion_status": "quarantined",
        "proof_credit_eligible": False,
        "theorem_campaign_admissible": False,
        "theory_mutation_allowed": False,
        "registered_family_digest": sha256_ref("candidate-family"),
        "base_theory_digest": base_digest,
        "substrate_digest": sha256_ref("candidate-substrate"),
        "evidence_receipt_digests": [sha256_ref("gap-1"), sha256_ref("gap-2")],
        "distinct_target_count": 2,
        "distinct_admission_count": 2,
        "distinct_task_count": 2,
        "required_next_gates": [
            {"requirement": "signed_unseen_task_manifest", "satisfied": False},
            {"requirement": "typed_axiom_proposals", "satisfied": False},
        ],
        "violations": [],
    }
    return {**core, "routing_receipt_digest": _canonical_digest(core)}


def _typed_source_receipt() -> tuple[dict, str]:
    base = priority_uncrossed_order_blueprint()
    source = {
        "schema": "common.structural_conjecture.v1",
        "mother_structure": "priority-compatible join",
        "kill_condition": "a finite typed countermodel rejects the candidate",
    }
    template = base.candidate_axiom_templates[0]
    axiom = AxiomFormula.from_json(
        {"name": "born_priority_candidate", "formula": template["formula"]}
    )
    proposal = build_typed_axiom_proposal(
        source_conjecture=source,
        theory_signature=TheorySignature.from_json(base.theory_signature),
        axiom=axiom,
        nl_intent="Priority is total on the frozen finite carrier.",
        kill_condition="Reject when a finite model has incomparable elements.",
    )
    private_key, public_key = generate_keypair()
    verdict = build_semantic_fidelity_verdict(
        proposal,
        faithful=True,
        rationale="The typed relation formula matches the source conjecture.",
        evidence_refs=["test:candidate-birth-semantic-review"],
        private_key_pem=private_key,
        verifier_ref="test-candidate-birth-checker",
    )
    return (
        {
            "schema": "leanmill.agent_tool.structural_isomorphism_receipt.v1",
            "status": "ok",
            "mode": "conjecture",
            "trial_source": "typed-test-producer",
            "result": {
                "candidate_count": 1,
                "typed_axiom_proposals": [
                    {
                        "source_conjecture": source,
                        "typed_axiom_proposal": proposal.to_json(),
                        "semantic_fidelity_verdict": verdict.to_json(),
                    }
                ],
            },
        },
        public_key,
    )


def _birth() -> dict:
    receipt, public_key = _typed_source_receipt()
    return materialize_typed_axiom_pack_candidate(
        base_blueprint=priority_uncrossed_order_blueprint(),
        source_receipt=receipt,
        trusted_semantic_fidelity_public_key_pem=public_key,
        expected_semantic_fidelity_verifier_ref="test-candidate-birth-checker",
    )


def _live_runtime() -> tuple[
    object,
    object,
    str,
    list[str],
]:
    base = priority_uncrossed_order_blueprint()
    view = build_typed_axiom_proposer_view(base)
    base_identity = view["base_theory"]
    base_digest = base_identity["base_theory_digest"]
    manifest_private, manifest_public = generate_keypair()
    task = ShadowTask(
        task_id="heldout-live-1",
        input_digest=sha256_ref("heldout-live-input"),
        budget_units=20,
    )
    manifest = build_shadow_task_manifest(
        tasks=[task],
        base_theory_digest=base_digest,
        admission_digests={task.task_id: sha256_ref("heldout-live-admission")},
        private_key_pem=manifest_private,
        verifier_ref="test-live-manifest-checker",
        manifest_evidence_ref=sha256_ref("test-live-manifest-evidence"),
    )
    semantic_private, semantic_public = generate_keypair()
    template = base.candidate_axiom_templates[0]
    candidate = AxiomFormula.from_json(
        {"name": template["name"], "formula": template["formula"]}
    )
    prompts: list[str] = []

    def proposer_call(prompt: str) -> dict:
        prompts.append(prompt)
        return {
            "schema": "leanmill.axiom_pack_typed_producer_output.v1",
            "outcome": "typed_proposals",
            "typed_axiom_proposals": [
                {
                    "source_conjecture": {
                        "schema": "leanmill.axiom_pack_structural_conjecture.v1",
                        "name": "priority_totality_candidate",
                        "statement": "priority comparisons are total",
                        "rationale": "totality may compress the unresolved comparison cases",
                        "kill_condition": "a finite carrier contains an incomparable pair",
                    },
                    "theory_signature_sha256": base_identity[
                        "theory_signature_sha256"
                    ],
                    "base_theory_digest": base_digest,
                    "axiom_formula_json": json.dumps(candidate.to_json()),
                    "nl_intent": "Priority is total on the frozen signature.",
                    "kill_condition": "Reject on a finite incomparable pair.",
                }
            ],
            "no_candidate_reason": "",
            "language_capability_gap": "",
        }

    def semantic_checker_call(_prompt: str) -> dict:
        return {
            "faithful": True,
            "rationale": (
                "The authored relation formula matches the structural conjecture."
            ),
            "evidence_refs": [sha256_ref("test-live-semantic-evidence")],
        }

    runtime = build_live_typed_axiom_pack_runtime(
        escalation=_eligible_packet(base_digest),
        task_manifest=manifest,
        trusted_manifest_public_key_pem=manifest_public,
        semantic_checker_private_key_pem=semantic_private,
        trusted_semantic_fidelity_public_key_pem=semantic_public,
        expected_semantic_fidelity_verifier_ref="test-live-semantic-checker",
        proposer_call=proposer_call,
        semantic_checker_call=semantic_checker_call,
    )
    return base, runtime, semantic_public, prompts


def test_typed_producer_births_identity_complete_pack_and_reaches_promotion(
    tmp_path,
) -> None:
    birth = _birth()

    assert birth["status"] == "candidate_born"
    ok, failures = verify_axiom_pack_candidate_birth(birth)
    assert ok is True
    assert failures == []
    pack = AxiomPack.from_json(birth["pack"])
    assert pack.base_theory_resolved is True
    assert pack.theory_signature["schema"] == "leanmill.theory_signature.v1"
    assert pack.base_axioms and all(row.get("formula") for row in pack.base_axioms)
    assert all(row.get("formula") for row in pack.candidate_axioms)
    assert birth["source_pack_ref"] in pack.provenance

    base_private, _base_public = generate_keypair()
    base_resolution = build_base_theory_resolution(
        pack=pack,
        source_ref="test:priority-base-resolution",
        private_key_pem=base_private,
        verifier_ref="test-priority-base-resolver",
        faithfulness_refs=[
            "sha256:" + hashlib.sha256(b"priority-base").hexdigest()
        ],
    )
    admission = build_axiom_pack_promotion_admission_from_birth(
        candidate_birth=birth,
        campaign_id="campaign:candidate-birth",
        attempt_id="attempt:001",
        context_hash="sha256:" + hashlib.sha256(b"context").hexdigest(),
        context_epoch=1,
        base_theory_resolution=base_resolution,
    )
    assert admission["source_identity"]["source_pack_ref"] == birth["source_pack_ref"]
    assert admission["typed_candidate_evidence"] == birth["typed_candidate_evidence"]
    transition = advance_axiom_pack_promotion(
        admission=admission,
        task_manifest=None,
        baseline_batch=None,
        treatment_batch=None,
        authorities=None,
        compile_fn=lambda _source: True,
    )
    assert transition["stage"] == "input"
    assert transition["next_required_field"] == "axiom_pack_shadow_task_manifest"

    store = tmp_path / "candidate_store.jsonl"
    event = append_axiom_pack_event(
        store,
        pack=pack,
        stress={"ok": False, "missing_stress_receipts": ["downstream_yield"]},
        candidate_birth=birth,
        generation=birth["generation"],
    )
    assert event["candidate_birth"]["receipt_sha256"] == birth["receipt_sha256"]
    assert store.is_file()


def test_prose_only_producer_returns_exact_capability_blocker_and_is_not_stored(
    tmp_path,
) -> None:
    source_receipt = {
        "schema": "leanmill.agent_tool.structural_isomorphism_receipt.v1",
        "status": "ok",
        "trial_source": "live_agent_isomorphism",
        "result": {
            "candidate_count": 1,
            "candidates": [{"statement": "a prose-only proposed law"}],
        },
    }
    blocker = materialize_typed_axiom_pack_candidate(
        base_blueprint=priority_uncrossed_order_blueprint(),
        source_receipt=source_receipt,
        trusted_semantic_fidelity_public_key_pem=None,
        expected_semantic_fidelity_verifier_ref=None,
    )

    assert blocker["status"] == "blocked_missing_capability"
    assert blocker["stage"] == "executable_language"
    assert blocker["next_required_field"] == (
        "producer_output.result.typed_axiom_proposals"
    )
    assert blocker["can_persist_pack"] is False

    prose_pack = AxiomPack(
        name="prose_only",
        domain="diagnostic",
        extends_theory="unresolved",
        candidate_axioms=[{"name": "candidate", "statement": "prose"}],
        intended_unlocks=["residual"],
        provenance=["live_agent_isomorphism"],
        downstream_residuals=["residual"],
    )
    store = tmp_path / "candidate_store.jsonl"
    with pytest.raises(ValueError, match="executable typed pack"):
        append_axiom_pack_event(store, pack=prose_pack, stress={})
    assert not store.exists()


def test_candidate_birth_tamper_remains_rejected_after_rehash() -> None:
    birth = _birth()
    tampered = copy.deepcopy(birth)
    tampered["base_identity"]["base_theory_digest"] = (
        "sha256:" + hashlib.sha256(b"other-base").hexdigest()
    )
    core = {key: value for key, value in tampered.items() if key != "receipt_sha256"}
    tampered["receipt_sha256"] = _canonical_digest(core)

    ok, failures = verify_axiom_pack_candidate_birth(tampered)
    assert ok is False
    assert "candidate_birth.base_identity" in failures
    with pytest.raises(ValueError, match="candidate_birth.base_identity"):
        build_axiom_pack_promotion_admission_from_birth(
            candidate_birth=tampered,
            campaign_id="campaign:tamper",
            attempt_id="attempt:001",
            context_hash="sha256:" + hashlib.sha256(b"context").hexdigest(),
            context_epoch=1,
            base_theory_resolution={},
        )


def test_calibration_receipt_cannot_birth_campaign_pack() -> None:
    receipt, public_key = _typed_source_receipt()
    receipt["orchestration"] = {"calibration_only": True}

    blocker = materialize_typed_axiom_pack_candidate(
        base_blueprint=priority_uncrossed_order_blueprint(),
        source_receipt=receipt,
        trusted_semantic_fidelity_public_key_pem=public_key,
        expected_semantic_fidelity_verifier_ref="test-candidate-birth-checker",
    )

    assert blocker["status"] == "blocked_missing_capability"
    assert blocker["stage"] == "producer_identity"
    assert blocker["next_required_field"] == (
        "producer_receipt.orchestration.calibration_only=false"
    )


def test_live_producer_schema_authors_formula_ir_and_routes_to_candidate_birth() -> None:
    base, runtime, semantic_public, prompts = _live_runtime()

    class StructuredRole:
        def __init__(self, call):
            self.call = call
            self.output_schema = None

        def __call__(self, prompt):
            return self.call(prompt)

    proposer_role = StructuredRole(runtime.proposer_call)
    runtime = replace(runtime, proposer_call=proposer_role)

    receipt = run_live_axiom_pack_isomorphism(
        base,
        model="test-provider",
        typed_producer_runtime=runtime,
    )

    assert receipt["status"] == "ok"
    assert receipt["canonical_engine"] == "ztare.leanmill.axiom_pack_orchestration"
    assert len(prompts) == 1
    assert "axiom_formula_json" in prompts[0]
    assert "language_capability_gap" in prompts[0]
    schema = typed_axiom_producer_output_schema()
    assert set(schema["required"]) == set(schema["properties"])
    assert proposer_role.output_schema == schema
    birth = materialize_typed_axiom_pack_candidate(
        base_blueprint=base,
        source_receipt=receipt,
        trusted_semantic_fidelity_public_key_pem=semantic_public,
        expected_semantic_fidelity_verifier_ref="test-live-semantic-checker",
    )
    assert birth["status"] == "candidate_born"
    pack = AxiomPack.from_json(birth["pack"])
    assert pack.theory_signature == base.theory_signature
    assert pack.base_axioms == [
        {**row, "axiom_hash": birth["generation"]["blueprint_lint"]["base_axiom_hashes"][index]}
        for index, row in enumerate(base.base_axioms)
    ]
    assert pack.candidate_axioms[0]["formula"]
    discovery = run_axiom_pack_discovery_eval(
        domain="priority",
        live_isomorphism=True,
        include_second_domain=False,
        live_typed_producer_runtime=runtime,
    )
    assert discovery["primary"]["candidate_birth"]["status"] == "candidate_born"


def test_live_cli_constructs_reviewed_runtime_and_births_candidate_provider_free(
    tmp_path,
    monkeypatch,
) -> None:
    from ztare.leanmill.frontier_agent_runtime import SubscriptionJSONRole

    base = priority_uncrossed_order_blueprint()
    view = build_typed_axiom_proposer_view(base)
    base_identity = view["base_theory"]
    base_digest = base_identity["base_theory_digest"]
    manifest_private, manifest_public = generate_keypair()
    task = ShadowTask(
        task_id="heldout-cli-1",
        input_digest=sha256_ref("heldout-cli-input"),
        budget_units=20,
    )
    manifest = build_shadow_task_manifest(
        tasks=[task],
        base_theory_digest=base_digest,
        admission_digests={task.task_id: sha256_ref("heldout-cli-admission")},
        private_key_pem=manifest_private,
        verifier_ref="test-cli-manifest-checker",
        manifest_evidence_ref=sha256_ref("test-cli-manifest-evidence"),
    )
    semantic_private, semantic_public = generate_keypair()
    candidate_template = base.candidate_axiom_templates[0]
    candidate = AxiomFormula.from_json(
        {
            "name": candidate_template["name"],
            "formula": candidate_template["formula"],
        }
    )
    calls: list[str] = []

    def provider_free_role_call(self, _prompt: str) -> dict:
        calls.append(self.role)
        if self.role == "axiom_pack_typed_proposer":
            assert self.output_schema == typed_axiom_producer_output_schema()
            return {
                "schema": "leanmill.axiom_pack_typed_producer_output.v1",
                "outcome": "typed_proposals",
                "typed_axiom_proposals": [
                    {
                        "source_conjecture": {
                            "schema": (
                                "leanmill.axiom_pack_structural_conjecture.v1"
                            ),
                            "name": "cli_priority_totality_candidate",
                            "statement": "priority comparisons are total",
                            "rationale": (
                                "totality may compress the unresolved comparison cases"
                            ),
                            "kill_condition": (
                                "a finite carrier contains an incomparable pair"
                            ),
                        },
                        "theory_signature_sha256": base_identity[
                            "theory_signature_sha256"
                        ],
                        "base_theory_digest": base_digest,
                        "axiom_formula_json": json.dumps(candidate.to_json()),
                        "nl_intent": "Priority is total on the frozen signature.",
                        "kill_condition": "Reject on a finite incomparable pair.",
                    }
                ],
                "no_candidate_reason": "",
                "language_capability_gap": "",
            }
        assert self.role == "axiom_pack_semantic_checker"
        assert self.output_schema == semantic_checker_output_schema()
        return {
            "faithful": True,
            "rationale": "The typed formula matches the authored conjecture.",
            "evidence_refs": [sha256_ref("test-cli-semantic-evidence")],
        }

    monkeypatch.setattr(SubscriptionJSONRole, "__call__", provider_free_role_call)
    escalation_path = tmp_path / "escalation.json"
    manifest_path = tmp_path / "manifest.json"
    manifest_public_path = tmp_path / "manifest_public.pem"
    semantic_private_path = tmp_path / "semantic_private.pem"
    semantic_public_path = tmp_path / "semantic_public.pem"
    report_path = tmp_path / "report.json"
    escalation_path.write_text(
        json.dumps(_eligible_packet(base_digest)), encoding="utf-8"
    )
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    manifest_public_path.write_text(manifest_public, encoding="utf-8")
    semantic_private_path.write_text(semantic_private, encoding="utf-8")
    semantic_public_path.write_text(semantic_public, encoding="utf-8")

    returncode = axiom_pack_main(
        [
            "--discovery-eval-priority",
            "--live-isomorphism",
            "--live-escalation",
            str(escalation_path),
            "--live-task-manifest",
            str(manifest_path),
            "--task-manifest-public-key",
            str(manifest_public_path),
            "--semantic-fidelity-private-key",
            str(semantic_private_path),
            "--semantic-fidelity-public-key",
            str(semantic_public_path),
            "--semantic-fidelity-verifier-ref",
            "test-cli-semantic-checker",
            "--live-artifact-dir",
            str(tmp_path / "role_artifacts"),
            "--subscription-model",
            "provider-free-test",
            "--no-second-domain",
            "--out",
            str(report_path),
        ]
    )

    assert returncode in {0, 1}
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["mode"] == "live"
    assert report["primary"]["candidate_birth"]["status"] == "candidate_born"
    assert calls == ["axiom_pack_typed_proposer", "axiom_pack_semantic_checker"]


def test_live_cli_refuses_unowned_legacy_flag_instead_of_returning_a_gap() -> None:
    with pytest.raises(SystemExit) as stopped:
        axiom_pack_main(
            ["--discovery-eval-priority", "--live-isomorphism", "--no-second-domain"]
        )

    assert stopped.value.code == 2


def test_live_producer_typed_terminal_outcomes_and_prose_feedback() -> None:
    base, runtime, semantic_public, _prompts = _live_runtime()
    checker_calls: list[dict] = []
    no_candidate_runtime = replace(
        runtime,
        proposer_call=lambda _prompt: {
            "schema": "leanmill.axiom_pack_typed_producer_output.v1",
            "outcome": "no_candidate",
            "typed_axiom_proposals": [],
            "no_candidate_reason": "every candidate in the bounded grammar was trivial",
            "language_capability_gap": "",
        },
        semantic_checker_fn=lambda payload: checker_calls.append(payload) or {},
    )
    no_candidate_receipt = run_live_axiom_pack_isomorphism(
        base,
        typed_producer_runtime=no_candidate_runtime,
    )
    assert no_candidate_receipt["status"] == "no_candidates"
    assert checker_calls == []
    no_candidate = materialize_typed_axiom_pack_candidate(
        base_blueprint=base,
        source_receipt=no_candidate_receipt,
        trusted_semantic_fidelity_public_key_pem=semantic_public,
        expected_semantic_fidelity_verifier_ref="test-live-semantic-checker",
    )
    assert no_candidate["status"] == "no_candidate"
    assert no_candidate["can_persist_pack"] is False

    gap_runtime = replace(
        runtime,
        proposer_call=lambda _prompt: {
            "schema": "leanmill.axiom_pack_typed_producer_output.v1",
            "outcome": "language_capability_gap",
            "typed_axiom_proposals": [],
            "no_candidate_reason": "",
            "language_capability_gap": "the requested higher-order binder is outside Formula IR",
        },
    )
    gap_receipt = run_live_axiom_pack_isomorphism(
        base,
        typed_producer_runtime=gap_runtime,
    )
    assert gap_receipt["status"] == "language_capability_gap"
    gap_blocker = materialize_typed_axiom_pack_candidate(
        base_blueprint=base,
        source_receipt=gap_receipt,
        trusted_semantic_fidelity_public_key_pem=semantic_public,
        expected_semantic_fidelity_verifier_ref="test-live-semantic-checker",
    )
    assert gap_blocker["next_required_field"] == (
        "producer_output.typed_axiom_proposals[*].axiom_formula_json"
    )

    prose_runtime = replace(
        runtime,
        proposer_call=lambda _prompt: {
            "candidate_axiom_templates": [
                {"name": "prose", "statement": "an untyped statement"}
            ]
        },
    )
    prose_receipt = run_live_axiom_pack_isomorphism(
        base,
        typed_producer_runtime=prose_runtime,
    )
    assert prose_receipt["status"] == "rejected"
    failures = prose_receipt["orchestration"]["failures"]
    assert "producer_contract:prose_only_output_rejected" in failures
    prose_blocker = materialize_typed_axiom_pack_candidate(
        base_blueprint=base,
        source_receipt=prose_receipt,
        trusted_semantic_fidelity_public_key_pem=semantic_public,
        expected_semantic_fidelity_verifier_ref="test-live-semantic-checker",
    )
    assert prose_blocker["can_persist_pack"] is False
