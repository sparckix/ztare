from __future__ import annotations

import copy

import pytest

from ztare.leanmill.formal_verification_provider import (
    attach_signature,
    generate_keypair,
)
from ztare.leanmill.theory_ir import (
    AxiomFormula,
    Binder,
    Formula,
    RelationSymbol,
    SortDecl,
    Term,
    TheorySignature,
)
from ztare.leanmill.typed_axiom_proposal import (
    SEMANTIC_FIDELITY_CHECKER_ROLE,
    admit_axiom_template,
    build_semantic_fidelity_verdict,
    build_typed_axiom_proposal,
    semantic_fidelity_verdict_digest,
    verify_semantic_fidelity_verdict,
)


def _candidate() -> tuple[dict, TheorySignature, AxiomFormula]:
    source = {
        "schema": "common.structural_conjecture.v1",
        "mother_structure": "a unary predicate covers the carrier",
        "kill_conditions": {"countermodel": "find an element outside P"},
    }
    signature = TheorySignature(
        name="PredicateTheory",
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
    return source, signature, axiom


def _proposal_and_verdict():
    source, signature, axiom = _candidate()
    private_key, public_key = generate_keypair()
    proposal = build_typed_axiom_proposal(
        source_conjecture=source,
        theory_signature=signature,
        axiom=axiom,
        nl_intent="Every carrier element satisfies P.",
        kill_condition="Reject when a finite model contains an element outside P.",
    )
    verdict = build_semantic_fidelity_verdict(
        proposal,
        faithful=True,
        rationale="The universal binder and predicate application match the intent.",
        evidence_refs=["test:semantic-fidelity-review"],
        private_key_pem=private_key,
        verifier_ref="test-semantic-fidelity-checker",
    )
    return source, proposal, verdict, private_key, public_key


def _verify(source, proposal, verdict, public_key):
    return verify_semantic_fidelity_verdict(
        proposal,
        verdict,
        trusted_public_key_pem=public_key,
        source_conjecture=source,
        expected_verifier_ref="test-semantic-fidelity-checker",
    )


def test_typed_proposal_admits_only_after_signed_fidelity_review() -> None:
    source, proposal, verdict, _private_key, public_key = _proposal_and_verdict()

    verified = _verify(source, proposal, verdict, public_key)
    assert verified["allowed"] is True
    assert verified["signature_verified"] is True
    assert verified["authority_role"] == SEMANTIC_FIDELITY_CHECKER_ROLE

    template = admit_axiom_template(
        proposal,
        verdict,
        trusted_public_key_pem=public_key,
        source_conjecture=source,
        expected_verifier_ref="test-semantic-fidelity-checker",
    )
    assert template["name"] == "all_p"
    assert template["formula"] == proposal.axiom.formula.to_json()
    assert template["typed_proposal_sha256"] == proposal.content_hash
    assert template["semantic_fidelity_verdict_sha256"] == (
        semantic_fidelity_verdict_digest(verdict)
    )
    assert (
        template["semantic_fidelity_checker_ref"]
        == "test-semantic-fidelity-checker"
    )
    assert "PUBLIC KEY" not in repr(template)


def test_source_tamper_is_rejected() -> None:
    source, proposal, verdict, _private_key, public_key = _proposal_and_verdict()
    changed_source = copy.deepcopy(source)
    changed_source["mother_structure"] = "a different structural conjecture"

    result = _verify(changed_source, proposal, verdict, public_key)

    assert result["allowed"] is False
    assert "source_conjecture_sha256" in result["failures"]


def test_frozen_theory_signature_tamper_is_rejected_even_with_updated_hash() -> None:
    source, proposal, verdict, _private_key, public_key = _proposal_and_verdict()
    changed = proposal.to_json()
    changed["theory_signature"]["relations"].append(
        {"name": "Q", "arg_sorts": ["Carrier"]}
    )
    changed_signature = TheorySignature.from_json(changed["theory_signature"])
    changed["theory_signature_sha256"] = changed_signature.content_hash

    result = _verify(source, changed, verdict, public_key)

    assert result["allowed"] is False
    assert "proposal_sha256" in result["failures"]
    assert "provider_payload:content_binding" in result["failures"]


def test_formula_tamper_is_rejected_even_with_updated_axiom_hash() -> None:
    source, proposal, verdict, _private_key, public_key = _proposal_and_verdict()
    changed = proposal.to_json()
    changed["axiom"]["formula"] = Formula.truth().to_json()
    changed_axiom = AxiomFormula.from_json(changed["axiom"])
    changed["axiom_sha256"] = changed_axiom.content_hash

    result = _verify(source, changed, verdict, public_key)

    assert result["allowed"] is False
    assert "proposal_sha256" in result["failures"]
    assert "provider_payload:content_binding" in result["failures"]


def test_signature_tamper_and_wrong_key_are_rejected() -> None:
    source, proposal, verdict, _private_key, public_key = _proposal_and_verdict()
    changed = verdict.to_json()
    signature = changed["provider_payload"]["metadata"][
        "provider_payload_signature"
    ]
    changed["provider_payload"]["metadata"]["provider_payload_signature"] = (
        signature[:-1] + ("0" if signature[-1] != "0" else "1")
    )

    tampered = _verify(source, proposal, changed, public_key)
    assert tampered["allowed"] is False
    assert tampered["signature_verified"] is False
    assert "provider_payload:signature" in tampered["failures"]

    _, wrong_public_key = generate_keypair()
    wrong_key = _verify(source, proposal, verdict, wrong_public_key)
    assert wrong_key["allowed"] is False
    assert wrong_key["signature_verified"] is False
    assert "provider_payload:signature" in wrong_key["failures"]


def test_correctly_signed_wrong_authority_role_is_rejected() -> None:
    source, proposal, verdict, private_key, public_key = _proposal_and_verdict()
    changed = verdict.to_json()
    changed["authority_role"] = "axiom_proposer"
    changed["provider_payload"]["metadata"]["authority_role"] = "axiom_proposer"
    attach_signature(changed["provider_payload"], private_key)

    result = _verify(source, proposal, changed, public_key)

    assert result["signature_verified"] is True
    assert result["allowed"] is False
    assert "authority_role" in result["failures"]
    assert "provider_payload:content_binding" in result["failures"]


def test_builder_rejects_axiom_outside_the_frozen_signature() -> None:
    source, signature, _axiom = _candidate()
    untyped = AxiomFormula(
        "all_q",
        Formula.forall(
            (Binder("x", "Carrier"),),
            Formula.rel("Q", Term.var("x")),
        ),
    )

    with pytest.raises(ValueError, match="unknown relation"):
        build_typed_axiom_proposal(
            source_conjecture=source,
            theory_signature=signature,
            axiom=untyped,
            nl_intent="Every carrier element satisfies Q.",
            kill_condition="Reject on a countermodel.",
        )
