from __future__ import annotations

import copy
import json

from ztare.leanmill.axiom_pack import (
    AxiomPackBlueprint,
    blueprint_from_agent_isomorphism_receipt,
    generate_candidate_axiom_pack,
    priority_uncrossed_order_blueprint,
    run_axiom_pack_discovery_eval,
)
from ztare.leanmill.formal_verification_provider import generate_keypair
from ztare.leanmill.theory_ir import AxiomFormula, TheorySignature
from ztare.leanmill.typed_axiom_proposal import (
    build_semantic_fidelity_verdict,
    build_typed_axiom_proposal,
    semantic_fidelity_verdict_digest,
)


def _typed_receipt(
    *,
    axiom_name: str = "typed_priority_candidate",
    signature_name: str | None = None,
):
    base = priority_uncrossed_order_blueprint()
    source = {
        "schema": "common.structural_conjecture.v1",
        "mother_structure": "priority-compatible join",
        "kill_condition": "find a finite order model that violates the proposed law",
    }
    template = base.candidate_axiom_templates[0]
    signature = TheorySignature.from_json(base.theory_signature)
    if signature_name is not None:
        signature_json = signature.to_json()
        signature_json["name"] = signature_name
        signature = TheorySignature.from_json(signature_json)
    axiom = AxiomFormula.from_json(
        {"name": axiom_name, "formula": template["formula"]}
    )
    private_key, public_key = generate_keypair()
    proposal = build_typed_axiom_proposal(
        source_conjecture=source,
        theory_signature=signature,
        axiom=axiom,
        nl_intent="The proposed join law preserves the frozen priority relation.",
        kill_condition="Reject on a finite countermodel over the frozen signature.",
    )
    verdict = build_semantic_fidelity_verdict(
        proposal,
        faithful=True,
        rationale="The quantified typed formula matches the stated join law.",
        evidence_refs=["test:typed-priority-review"],
        private_key_pem=private_key,
        verifier_ref="test-axiom-semantic-checker",
    )
    receipt = {
        "status": "ok",
        "model": "test-proposer",
        "trial_source": "typed-test",
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
    }
    return base, receipt, public_key


def test_typed_isomorphism_proposal_crosses_into_blueprint_under_configured_key() -> None:
    base, receipt, public_key = _typed_receipt()

    row = blueprint_from_agent_isomorphism_receipt(
        base,
        receipt,
        trusted_semantic_fidelity_public_key_pem=public_key,
        expected_semantic_fidelity_verifier_ref="test-axiom-semantic-checker",
    )

    assert row["ok"] is True
    assert row["construction_ready"] is True
    assert row["lint"]["ok"] is True
    assert row["typed_candidate_admission"]["accepted"] == 1
    candidate = row["blueprint"]["candidate_axiom_templates"][0]
    assert candidate["name"] == "typed_priority_candidate"
    evidence = row["typed_candidate_evidence"][0]
    assert candidate["semantic_fidelity_verdict_sha256"] == semantic_fidelity_verdict_digest(
        evidence["semantic_fidelity_verdict"]
    )
    assert candidate["semantic_fidelity_checker_ref"] == "test-axiom-semantic-checker"
    pack, generation = generate_candidate_axiom_pack(
        AxiomPackBlueprint.from_json(row["blueprint"]),
        isomorphism_receipt=receipt,
        trusted_semantic_fidelity_public_key_pem=public_key,
    )
    assert generation["ok"] is True
    assert generation["typed_blueprint_construction"]["ok"] is True
    assert [axiom["name"] for axiom in pack.candidate_axioms] == [
        "typed_priority_candidate"
    ]


def test_typed_isomorphism_proposal_cannot_supply_its_own_trust_root() -> None:
    base, receipt, public_key = _typed_receipt()
    receipt["trusted_semantic_fidelity_public_key_pem"] = public_key
    receipt["result"]["trusted_semantic_fidelity_public_key_pem"] = public_key

    row = blueprint_from_agent_isomorphism_receipt(base, receipt)

    assert row["ok"] is False
    assert row["typed_candidate_admission"]["accepted"] == 0
    assert row["typed_candidate_admission"]["trust_root_from_receipt"] is False
    assert "candidate_axiom_templates" in row["lint"]["missing_fields"]


def test_typed_source_tamper_and_non_ok_receipt_are_rejected() -> None:
    base, receipt, public_key = _typed_receipt()
    receipt["result"]["typed_axiom_proposals"][0]["source_conjecture"][
        "mother_structure"
    ] = "stale or substituted source"

    stale = blueprint_from_agent_isomorphism_receipt(
        base,
        receipt,
        trusted_semantic_fidelity_public_key_pem=public_key,
    )
    assert stale["ok"] is False
    stale_failures = stale["typed_candidate_admission"]["rejected"][0]["failures"]
    assert any("source_conjecture_sha256" in failure for failure in stale_failures)

    _base, non_ok_receipt, non_ok_key = _typed_receipt()
    non_ok_receipt["status"] = "error"
    non_ok = blueprint_from_agent_isomorphism_receipt(
        _base,
        non_ok_receipt,
        trusted_semantic_fidelity_public_key_pem=non_ok_key,
    )
    assert non_ok["ok"] is False
    assert non_ok["typed_candidate_admission"]["accepted"] == 0
    assert non_ok["typed_candidate_admission"]["rejected"][0]["failures"] == [
        "source_receipt_status_not_ok"
    ]


def test_typed_proposal_for_an_alternate_signature_is_rejected() -> None:
    base, receipt, public_key = _typed_receipt(signature_name="OtherSignature")

    row = blueprint_from_agent_isomorphism_receipt(
        base,
        receipt,
        trusted_semantic_fidelity_public_key_pem=public_key,
    )

    assert row["ok"] is False
    failures = row["typed_candidate_admission"]["rejected"][0]["failures"]
    assert failures == ["proposal_theory_signature_mismatch"]


def test_duplicate_typed_proposal_and_axiom_name_are_rejected_before_blueprint() -> None:
    base, receipt, public_key = _typed_receipt()
    receipt["result"]["typed_axiom_proposals"].append(
        copy.deepcopy(receipt["result"]["typed_axiom_proposals"][0])
    )
    receipt["result"]["candidate_count"] = 2

    row = blueprint_from_agent_isomorphism_receipt(
        base,
        receipt,
        trusted_semantic_fidelity_public_key_pem=public_key,
        expected_semantic_fidelity_verifier_ref="test-axiom-semantic-checker",
    )

    assert row["ok"] is False
    assert row["construction_ready"] is False
    assert row["typed_candidate_admission"]["accepted"] == 1
    failures = row["typed_candidate_admission"]["rejected"][0]["failures"]
    assert "duplicate_typed_proposal" in failures
    assert "duplicate_typed_axiom_name" in failures
    candidates = row["blueprint"]["candidate_axiom_templates"]
    assert [candidate["name"] for candidate in candidates] == [
        "typed_priority_candidate"
    ]


def test_signed_typed_axiom_name_is_preserved_byte_for_byte() -> None:
    base, receipt, public_key = _typed_receipt(axiom_name="TypedPriorityCandidate")

    row = blueprint_from_agent_isomorphism_receipt(
        base,
        receipt,
        trusted_semantic_fidelity_public_key_pem=public_key,
    )

    assert row["ok"] is True
    assert row["blueprint"]["candidate_axiom_templates"][0]["name"] == (
        "TypedPriorityCandidate"
    )


def test_post_construction_formula_tamper_is_blocked_before_pack_generation() -> None:
    base, receipt, public_key = _typed_receipt()
    row = blueprint_from_agent_isomorphism_receipt(
        base,
        receipt,
        trusted_semantic_fidelity_public_key_pem=public_key,
    )
    tampered = copy.deepcopy(row["blueprint"])
    tampered["candidate_axiom_templates"][0]["formula"] = {"kind": "true"}

    pack, generation = generate_candidate_axiom_pack(
        AxiomPackBlueprint.from_json(tampered),
        isomorphism_receipt=receipt,
        trusted_semantic_fidelity_public_key_pem=public_key,
    )

    assert generation["ok"] is False
    assert generation["reason"] == "typed_blueprint_construction_unverified"
    assert "typed_candidate_templates_do_not_replay" in generation[
        "typed_blueprint_construction"
    ]["failures"]
    assert pack.candidate_axioms == []


def test_discovery_eval_accepts_configured_semantic_checker_key(tmp_path) -> None:
    _base, receipt, public_key = _typed_receipt()
    path = tmp_path / "typed_receipt.json"
    path.write_text(json.dumps(receipt), encoding="utf-8")

    report = run_axiom_pack_discovery_eval(
        domain="priority",
        receipt_path=path,
        include_second_domain=False,
        trusted_semantic_fidelity_public_key_pem=public_key,
        expected_semantic_fidelity_verifier_ref="test-axiom-semantic-checker",
    )

    trial = report["primary"]["agent_blueprint_trial"]
    assert trial["construction_ready"] is True
    assert report["primary"]["generation"]["ok"] is True
    assert report["primary"]["generation"]["typed_blueprint_construction"]["ok"] is True
