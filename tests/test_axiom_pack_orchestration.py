from __future__ import annotations

import hashlib

from ztare.leanmill.axiom_pack_orchestration import (
    make_json_proposer,
    make_signed_semantic_checker,
    orchestrate_typed_axiom_proposals,
    recover_valid_quarantined_rows,
)
from ztare.leanmill.solver import prompts
from ztare.leanmill.axiom_yield import ShadowTask, build_shadow_task_manifest
from ztare.leanmill.formal_verification_provider import generate_keypair
from ztare.leanmill.typed_axiom_proposal import (
    build_semantic_fidelity_verdict,
    build_typed_axiom_proposal,
)
from ztare.leanmill.theory_ir import Binder, Formula, SortDecl, Term, TheorySignature, AxiomFormula


def _sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def _packet(base_digest: str) -> dict:
    core = {
        "schema": "leanmill.axiom_pack_escalation_eligibility.v1",
        "status": "eligible_for_candidate_routing",
        "eligible": True,
        "routing_only": True,
        "promotion_status": "quarantined",
        "proof_credit_eligible": False,
        "theorem_campaign_admissible": False,
        "theory_mutation_allowed": False,
        "registered_family_digest": _sha("family"),
        "base_theory_digest": base_digest,
        "substrate_digest": _sha("substrate"),
        "evidence_receipt_digests": [_sha("receipt-1"), _sha("receipt-2")],
        "distinct_target_count": 2,
        "distinct_admission_count": 2,
        "distinct_task_count": 2,
        "required_next_gates": [
            {"requirement": "signed_unseen_task_manifest", "satisfied": False},
            {"requirement": "typed_axiom_proposals", "satisfied": False},
        ],
        "violations": [],
    }
    digest = _sha(__import__("json").dumps(core, sort_keys=True, separators=(",", ":")))
    return {**core, "routing_receipt_digest": digest}


def _fixture():
    signature = TheorySignature(name="P", sorts=(SortDecl("Carrier"),))
    axiom = AxiomFormula(
        "all_eq",
        Formula.forall((Binder("x", "Carrier"),), Formula.eq(Term.var("x"), Term.var("x"))),
    )
    base_digest = "sha256:" + hashlib.sha256(
        __import__("json").dumps({"base": True}, sort_keys=True).encode()
    ).hexdigest()
    manifest_private, manifest_public = generate_keypair()
    task = ShadowTask(task_id="heldout-1", input_digest=_sha("input"), budget_units=10)
    manifest = build_shadow_task_manifest(
        tasks=[task],
        base_theory_digest=base_digest,
        admission_digests={task.task_id: _sha("admission")},
        private_key_pem=manifest_private,
        verifier_ref="manifest-checker",
        manifest_evidence_ref=_sha("manifest-evidence"),
    )
    proposal_private, proposal_public = generate_keypair()
    source = {"kind": "structural_conjecture", "id": "source-1"}
    proposal = build_typed_axiom_proposal(
        source_conjecture=source,
        theory_signature=signature,
        axiom=axiom,
        nl_intent="all carriers are reflexive under the declared relation",
        kill_condition="a two-element countermodel breaks reflexivity",
    )
    verdict = build_semantic_fidelity_verdict(
        proposal,
        faithful=True,
        rationale="The typed formula matches the stated intent.",
        evidence_refs=[_sha("semantic-evidence")],
        private_key_pem=proposal_private,
        verifier_ref="semantic-checker",
    )
    return base_digest, manifest, manifest_public, proposal_public, source, proposal, verdict


def test_orchestration_verifies_manifest_before_typed_checker() -> None:
    base_digest, manifest, manifest_public, semantic_public, source, proposal, verdict = _fixture()
    calls = []
    result = orchestrate_typed_axiom_proposals(
        escalation=_packet(base_digest),
        proposer_view={
            "schema": "safe",
            "base_theory_digest": base_digest,
            "base_theory": {"signature": proposal.to_json()["theory_signature"]},
            "grammar": {"max": 6},
        },
        task_manifest=manifest,
        trusted_manifest_public_key_pem=manifest_public,
        trusted_semantic_fidelity_public_key_pem=semantic_public,
        expected_semantic_fidelity_verifier_ref="semantic-checker",
        proposer_fn=lambda view: calls.append(("proposer", view)) or {
            "typed_axiom_proposals": [{
                "source_conjecture": source,
                "typed_axiom_proposal": {
                    "axiom": proposal.to_json()["axiom"],
                    "nl_intent": proposal.to_json()["nl_intent"],
                    "kill_condition": proposal.to_json()["kill_condition"],
                },
            }]
        },
        semantic_checker_fn=lambda payload: calls.append(("checker", payload)) or {
            "semantic_fidelity_verdict": verdict.to_json()
        },
    )
    assert result["ok"] is True
    assert [name for name, _ in calls] == ["proposer", "checker"]
    assert "task_manifest" not in calls[0][1]
    assert "semantic_fidelity_verdict" in result["receipt"]["result"]["typed_axiom_proposals"][0]


def test_prose_only_and_sensitive_views_are_rejected() -> None:
    base_digest, manifest, manifest_public, semantic_public, _source, _proposal, _verdict = _fixture()
    common = dict(
        escalation=_packet(base_digest),
        task_manifest=manifest,
        trusted_manifest_public_key_pem=manifest_public,
        trusted_semantic_fidelity_public_key_pem=semantic_public,
        expected_semantic_fidelity_verifier_ref="semantic-checker",
        proposer_fn=lambda _view: {"candidate_axiom_templates": [{"statement": "x"}]},
        semantic_checker_fn=lambda _payload: {},
    )
    prose = orchestrate_typed_axiom_proposals(
        proposer_view={"schema": "safe", "base_theory_digest": base_digest}, **common
    )
    assert prose["ok"] is False
    assert "prose_only_output_rejected" in prose["failures"]
    sensitive = orchestrate_typed_axiom_proposals(
        proposer_view={"schema": "safe", "heldout_tasks": []}, **common
    )
    assert sensitive["stage"] == "proposer_view"


def test_bad_manifest_stops_before_proposer() -> None:
    base_digest, manifest, manifest_public, semantic_public, _source, _proposal, _verdict = _fixture()
    called = []
    result = orchestrate_typed_axiom_proposals(
        escalation=_packet(base_digest),
        proposer_view={"schema": "safe"},
        task_manifest={**manifest, "metadata": {**manifest["metadata"], "manifest_digest": _sha("tampered")}},
        trusted_manifest_public_key_pem=manifest_public,
        trusted_semantic_fidelity_public_key_pem=semantic_public,
        expected_semantic_fidelity_verifier_ref="semantic-checker",
        proposer_fn=lambda _view: called.append(True) or {},
        semantic_checker_fn=lambda _payload: {},
    )
    assert result["stage"] == "manifest"
    assert called == []


def test_callback_adapters_parse_model_text_and_sign_only_in_code() -> None:
    _base, _manifest, _manifest_public, _semantic_public, source, proposal, _verdict = _fixture()
    proposer = make_json_proposer(
        lambda prompt: '{"typed_axiom_proposals":[{"source_conjecture":'
        + __import__("json").dumps(source)
        + ',"typed_axiom_proposal":'
        + __import__("json").dumps(proposal.to_json())
        + '}]}',
    )
    proposed = proposer({"schema": "safe"})
    assert proposed["typed_axiom_proposals"][0]["typed_axiom_proposal"] == proposal.to_json()
    private, public = generate_keypair()
    checker = make_signed_semantic_checker(
        lambda _prompt: {"faithful": True, "rationale": "matches", "evidence_refs": [_sha("evidence")]},
        private_key_pem=private,
        verifier_ref="adapter-checker",
    )
    verdict = checker({"source_conjecture": source, "typed_axiom_proposal": proposal.to_json()})
    assert verdict["semantic_fidelity_verdict"]["authority_role"] == "semantic_fidelity_checker"
    assert public.startswith("-----BEGIN PUBLIC KEY-----")


def test_generic_proposer_prompt_is_not_the_band_word_codec() -> None:
    assert "source_conjecture" in prompts.AXIOM_PACK_TYPED_PROPOSER_PROMPT
    assert "lhs_word" not in prompts.AXIOM_PACK_TYPED_PROPOSER_PROMPT
    assert "lhs_word" in prompts.AXIOM_PACK_BAND_WORD_PROPOSER_PROMPT


def test_full_batch_preflights_before_any_semantic_checker() -> None:
    base, manifest, manifest_public, semantic_public, source, proposal, _verdict = _fixture()
    checker_calls = []
    result = orchestrate_typed_axiom_proposals(
        escalation=_packet(base),
        proposer_view={
            "schema": "safe",
            "base_theory": {"signature": proposal.to_json()["theory_signature"]},
        },
        task_manifest=manifest,
        trusted_manifest_public_key_pem=manifest_public,
        trusted_semantic_fidelity_public_key_pem=semantic_public,
        expected_semantic_fidelity_verifier_ref="semantic-checker",
        proposer_fn=lambda _view: {
            "typed_axiom_proposals": [
                {"source_conjecture": source, "typed_axiom_proposal": proposal.to_json()},
                {"source_conjecture": source, "unexpected": {}},
            ]
        },
        semantic_checker_fn=lambda payload: checker_calls.append(payload) or {},
    )
    assert result["stage"] == "proposer_preflight"
    assert checker_calls == []


def test_rejected_batch_rows_can_be_recovered_without_provider_replay() -> None:
    base, manifest, manifest_public, semantic_public, source, proposal, verdict = _fixture()
    successful = orchestrate_typed_axiom_proposals(
        escalation=_packet(base),
        proposer_view={
            "schema": "safe",
            "base_theory": {"signature": proposal.to_json()["theory_signature"]},
        },
        task_manifest=manifest,
        trusted_manifest_public_key_pem=manifest_public,
        trusted_semantic_fidelity_public_key_pem=semantic_public,
        expected_semantic_fidelity_verifier_ref="semantic-checker",
        proposer_fn=lambda _view: {
            "typed_axiom_proposals": [
                {"source_conjecture": source, "typed_axiom_proposal": proposal.to_json()}
            ]
        },
        semantic_checker_fn=lambda _payload: {
            "semantic_fidelity_verdict": verdict.to_json()
        },
    )
    row = successful["receipt"]["result"]["typed_axiom_proposals"][0]
    rejected = {
        **successful,
        "ok": False,
        "stage": "semantic_checker",
        "failures": ["row.1.proposal_policy:duplicate"],
        "receipt": {
            **successful["receipt"],
            "status": "rejected",
            "result": {
                "candidate_count": 2,
                "typed_axiom_proposals": [row, row],
            },
        },
    }
    seen = [0]

    def validator(_proposal):
        seen[0] += 1
        if seen[0] == 2:
            raise ValueError("duplicate")

    recovery = recover_valid_quarantined_rows(
        rejected,
        trusted_semantic_fidelity_public_key_pem=semantic_public,
        expected_semantic_fidelity_verifier_ref="semantic-checker",
        proposal_validator=validator,
    )
    assert recovery["accepted_count"] == 1
    assert recovery["rejected_count"] == 1
    assert recovery["provider_calls"] == 0
