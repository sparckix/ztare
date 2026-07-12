from __future__ import annotations

import copy
import shutil
import subprocess

import pytest

from ztare.leanmill.finite_model import (
    COUNTERMODEL,
    CERTIFIED_WITH_WITNESSES,
    EQUIVALENT_WITHIN_BOUND,
    INDEPENDENCE_WITNESS,
    NO_CANDIDATE_AXIOMS,
    NO_INDEPENDENCE_WITNESS_WITHIN_BOUND,
    NO_MODEL_WITHIN_BOUND,
    SAT,
    SAT_WITHOUT_COMPLETE_INDEPENDENCE_WITNESSES,
    UNKNOWN,
    FiniteModel,
    FiniteSearchBounds,
    certify_axiom_independence,
    certify_equivalence,
    certify_implication,
    certify_joint_satisfiability,
    certify_theory,
    evaluate_axiom,
    verify_receipt_hash,
    verify_certified_theory_suite,
    verify_theory_suite_hash,
)
from ztare.leanmill.theory_ir import (
    AxiomFormula,
    Binder,
    Formula,
    IRValidationError,
    OperationSymbol,
    RelationSymbol,
    SortDecl,
    Term,
    TheorySignature,
    content_hash,
    lower_conditional_pack_to_lean,
    theory_content_hash,
    validate_axiom,
)


def _relation_signature() -> TheorySignature:
    return TheorySignature(
        name="UnaryPredicates",
        sorts=(SortDecl("Carrier"),),
        relations=(
            RelationSymbol("P", ("Carrier",)),
            RelationSymbol("Q", ("Carrier",)),
        ),
    )


def _all_relation(name: str, relation: str, variable: str = "x") -> AxiomFormula:
    return AxiomFormula(
        name=name,
        formula=Formula.forall(
            (Binder(variable, "Carrier"),),
            Formula.rel(relation, Term.var(variable)),
        ),
    )


def test_false_axiom_is_bounded_absence_not_consistency_pass() -> None:
    signature = TheorySignature(name="Bare", sorts=(SortDecl("Carrier"),))
    contradiction = AxiomFormula("contradiction", Formula.falsity())

    receipt = certify_joint_satisfiability(
        signature,
        (contradiction,),
        FiniteSearchBounds(max_carrier_size=3),
    )

    assert receipt.status == NO_MODEL_WITHIN_BOUND
    assert receipt.bounded_absence is True
    assert receipt.interpretations_tested == 3
    assert receipt.witness is None
    assert "bounded finite conclusion only" in receipt.to_json()["output_summary"]


def test_satisfiable_axiom_returns_exact_replayable_model() -> None:
    signature = _relation_signature()
    all_p = _all_relation("all_p", "P")

    receipt = certify_joint_satisfiability(
        signature,
        (all_p,),
        FiniteSearchBounds(max_carrier_size=1),
    )

    assert receipt.status == SAT
    assert receipt.witness is not None
    model = FiniteModel.from_json(receipt.witness["model"])
    assert evaluate_axiom(signature, all_p, model) is True
    assert receipt.witness["model_sha256"] == model.content_hash(signature)


def test_many_sorted_terms_and_existentials_evaluate_exactly() -> None:
    signature = TheorySignature(
        name="ManySorted",
        sorts=(SortDecl("Source"), SortDecl("Target")),
        operations=(OperationSymbol("map", ("Source",), "Target"),),
        relations=(RelationSymbol("Marked", ("Target",)),),
    )
    mapped_is_marked = AxiomFormula(
        "mapped_is_marked",
        Formula.forall(
            (Binder("x", "Source"),),
            Formula.rel("Marked", Term.app("map", Term.var("x"))),
        ),
    )
    marked_exists = AxiomFormula(
        "marked_exists",
        Formula.exists(
            (Binder("y", "Target"),),
            Formula.rel("Marked", Term.var("y")),
        ),
    )
    model = FiniteModel(
        sort_sizes=(("Source", 1), ("Target", 2)),
        operations=(("map", (1,)),),
        relations=(("Marked", (False, True)),),
    )

    assert evaluate_axiom(signature, mapped_is_marked, model) is True
    assert evaluate_axiom(signature, marked_exists, model) is True


def test_redundant_axiom_has_no_independence_witness_within_bound() -> None:
    signature = _relation_signature()
    all_p = _all_relation("all_p", "P")
    duplicate = _all_relation("all_p_again", "P", variable="element")

    receipts = certify_axiom_independence(
        signature,
        (all_p, duplicate),
        FiniteSearchBounds(max_carrier_size=2),
    )

    assert [receipt.status for receipt in receipts] == [
        NO_INDEPENDENCE_WITNESS_WITHIN_BOUND,
        NO_INDEPENDENCE_WITNESS_WITHIN_BOUND,
    ]
    assert all(receipt.bounded_absence for receipt in receipts)


def test_independent_laws_receive_separate_exact_witnesses() -> None:
    signature = _relation_signature()
    all_p = _all_relation("all_p", "P")
    all_q = _all_relation("all_q", "Q")

    receipts = certify_axiom_independence(
        signature,
        (all_p, all_q),
        FiniteSearchBounds(max_carrier_size=1),
    )

    assert [receipt.status for receipt in receipts] == [
        INDEPENDENCE_WITNESS,
        INDEPENDENCE_WITNESS,
    ]
    for target, background, receipt in (
        (all_p, all_q, receipts[0]),
        (all_q, all_p, receipts[1]),
    ):
        assert receipt.witness is not None
        model = FiniteModel.from_json(receipt.witness["model"])
        assert evaluate_axiom(signature, background, model) is True
        assert evaluate_axiom(signature, target, model) is False


def test_implication_finds_countermodel_for_non_involutive_operation() -> None:
    signature = TheorySignature(
        name="UnaryOperation",
        sorts=(SortDecl("Carrier"),),
        operations=(OperationSymbol("f", ("Carrier",), "Carrier"),),
    )
    x = Term.var("x")
    involution = AxiomFormula(
        "involution",
        Formula.forall(
            (Binder("x", "Carrier"),),
            Formula.eq(Term.app("f", Term.app("f", x)), x),
        ),
    )

    receipt = certify_implication(
        signature,
        premises=(),
        conclusions=(involution,),
        bounds=FiniteSearchBounds(max_carrier_size=2),
    )

    assert receipt.status == COUNTERMODEL
    assert receipt.witness is not None
    model = FiniteModel.from_json(receipt.witness["model"])
    assert evaluate_axiom(signature, involution, model) is False


def test_equivalence_is_explicitly_bounded() -> None:
    signature = _relation_signature()
    left = _all_relation("left", "P")
    right = _all_relation("right", "P", variable="y")

    receipt = certify_equivalence(
        signature,
        (left,),
        (right,),
        FiniteSearchBounds(max_carrier_size=2),
    )

    assert receipt.status == EQUIVALENT_WITHIN_BOUND
    assert receipt.bounded_absence is True
    assert len(receipt.details["direction_receipts"]) == 2


def test_budget_exhaustion_returns_unknown_not_bounded_absence() -> None:
    signature = TheorySignature(name="Bare", sorts=(SortDecl("Carrier"),))
    contradiction = AxiomFormula("contradiction", Formula.falsity())

    receipt = certify_joint_satisfiability(
        signature,
        (contradiction,),
        FiniteSearchBounds(max_carrier_size=2, max_interpretations=1),
    )

    assert receipt.status == UNKNOWN
    assert receipt.bounded_absence is False
    assert receipt.details["unknown_reason"] == "max_interpretations_exhausted"


def test_malformed_or_ill_typed_ir_fails_closed() -> None:
    with pytest.raises(IRValidationError, match="unknown sorts"):
        TheorySignature(
            name="Broken",
            sorts=(SortDecl("Carrier"),),
            operations=(OperationSymbol("f", ("Missing",), "Carrier"),),
        )

    signature = _relation_signature()
    free_variable = AxiomFormula("free", Formula.rel("P", Term.var("x")))
    with pytest.raises(IRValidationError, match="unbound variable"):
        validate_axiom(signature, free_variable)

    malformed = {
        "name": "bad",
        "formula": {"kind": "forall", "binders": [], "body": {"kind": "true"}},
    }
    with pytest.raises(IRValidationError, match="at least one binder"):
        AxiomFormula.from_json(malformed)

    with pytest.raises(IRValidationError, match="must be a string"):
        TheorySignature.from_json(
            {"name": True, "sorts": [{"name": "Carrier"}]}
        )

    with pytest.raises(IRValidationError, match="must be an identifier"):
        SortDecl(True)  # type: ignore[arg-type]


def test_hashes_are_order_stable_and_alpha_normalized() -> None:
    signature_a = TheorySignature(
        name="Stable",
        sorts=(SortDecl("B"), SortDecl("A")),
        operations=(
            OperationSymbol("z", (), "B"),
            OperationSymbol("a", (), "A"),
        ),
    )
    signature_b = TheorySignature(
        name="Stable",
        sorts=(SortDecl("A"), SortDecl("B")),
        operations=(
            OperationSymbol("a", (), "A"),
            OperationSymbol("z", (), "B"),
        ),
    )
    assert signature_a.content_hash == signature_b.content_hash
    assert signature_a == signature_b
    assert TheorySignature.from_json(signature_a.to_json()) == signature_a

    signature = _relation_signature()
    axiom_x = _all_relation("same_name", "P", variable="x")
    axiom_element = _all_relation("same_name", "P", variable="element")
    assert axiom_x.content_hash == axiom_element.content_hash
    assert axiom_x.semantic_hash == axiom_element.semantic_hash

    all_p = _all_relation("p", "P").formula
    all_q = _all_relation("q", "Q", variable="item").formula
    conjunction_a = AxiomFormula(
        "conjunction", Formula.conjunction(all_p, all_q)
    )
    conjunction_b = AxiomFormula(
        "conjunction", Formula.conjunction(all_q, all_p)
    )
    assert conjunction_a.content_hash == conjunction_b.content_hash

    # Canonicalization deliberately preserves multiplicity.  It normalizes
    # presentation, not logical equivalence or idempotence.
    duplicated = AxiomFormula(
        "duplicated", Formula.conjunction(all_p, all_p)
    )
    single = AxiomFormula("duplicated", all_p)
    assert duplicated.semantic_hash != single.semantic_hash

    assert theory_content_hash(signature, (axiom_x,)) == theory_content_hash(
        signature, (axiom_element,)
    )


def test_receipt_hash_binds_inputs_and_witness() -> None:
    signature = _relation_signature()
    receipt = certify_joint_satisfiability(
        signature,
        (_all_relation("all_p", "P"),),
        FiniteSearchBounds(max_carrier_size=1),
    ).to_json()

    assert verify_receipt_hash(receipt) is True
    assert receipt["certificate_digest"] == receipt["receipt_sha256"]
    assert receipt["theory_digest"]
    tampered = copy.deepcopy(receipt)
    tampered["witness"]["model"]["relations"]["P"] = [False]
    assert verify_receipt_hash(tampered) is False


def test_json_roundtrip_and_conditional_lean_lowering() -> None:
    signature = _relation_signature()
    all_p = _all_relation("all_p", "P")

    assert TheorySignature.from_json(signature.to_json()) == signature
    assert AxiomFormula.from_json(all_p.to_json()) == all_p

    lean = lower_conditional_pack_to_lean(signature, (all_p,))
    assert "class UnaryPredicatesSignature" in lean
    assert "class CandidateAxiomPack" in lean
    assert "[UnaryPredicatesSignature Carrier] [Nonempty Carrier] : Prop where" in lean
    assert "all_p : (forall (x : Carrier)" in lean
    assert "axiom " not in lean


def test_theory_suite_requires_joint_and_every_independence_witness() -> None:
    signature = _relation_signature()
    all_p = _all_relation("all_p", "P")
    all_q = _all_relation("all_q", "Q")
    bounds = FiniteSearchBounds(max_carrier_size=1)

    certified = certify_theory(signature, (all_p, all_q), bounds)
    assert certified.status == CERTIFIED_WITH_WITNESSES
    assert certified.certified is True
    payload = certified.to_json()
    assert payload["theory_digest"] == theory_content_hash(
        signature, (all_p, all_q)
    )
    assert verify_theory_suite_hash(payload) is True
    assert verify_certified_theory_suite(
        signature, (all_p, all_q), payload
    ) == (True, [])
    assert certify_theory(signature, (all_q, all_p), bounds).certificate_digest == (
        certified.certificate_digest
    )

    forged = copy.deepcopy(payload)
    forged_independence = forged["independence"][0]
    forged_independence["witness"] = copy.deepcopy(
        forged["joint_satisfiability"]["witness"]
    )
    forged_independence.pop("receipt_sha256")
    forged_independence.pop("certificate_digest")
    new_nested_digest = content_hash(forged_independence)
    forged_independence["certificate_digest"] = new_nested_digest
    forged_independence["receipt_sha256"] = new_nested_digest
    forged.pop("receipt_sha256")
    forged.pop("certificate_digest")
    new_suite_digest = content_hash(forged)
    forged["certificate_digest"] = new_suite_digest
    forged["receipt_sha256"] = new_suite_digest
    ok, errors = verify_certified_theory_suite(
        signature, (all_p, all_q), forged
    )
    assert ok is False
    assert "independence_witness_does_not_refute_target:all_p" in errors

    duplicate = _all_relation("all_p_again", "P", variable="element")
    unresolved = certify_theory(signature, (all_p, duplicate), bounds)
    assert unresolved.status == SAT_WITHOUT_COMPLETE_INDEPENDENCE_WITNESSES
    assert unresolved.certified is False

    contradiction = AxiomFormula("contradiction", Formula.falsity())
    rejected = certify_theory(signature, (contradiction,), bounds)
    assert rejected.status == NO_MODEL_WITHIN_BOUND
    assert rejected.certified is False

    empty = certify_theory(signature, (), bounds)
    assert empty.status == NO_CANDIDATE_AXIOMS
    assert empty.certified is False


def test_candidate_theory_is_checked_relative_to_typed_base_axioms() -> None:
    signature = _relation_signature()
    base_all_p = _all_relation("base_all_p", "P")
    candidate_not_all_p = AxiomFormula(
        "candidate_not_all_p",
        Formula.exists(
            (Binder("x", "Carrier"),),
            Formula.negate(Formula.rel("P", Term.var("x"))),
        ),
    )
    bounds = FiniteSearchBounds(max_carrier_size=1)

    standalone = certify_theory(signature, (candidate_not_all_p,), bounds)
    relative = certify_theory(
        signature,
        (candidate_not_all_p,),
        bounds,
        base_axioms=(base_all_p,),
    )

    assert standalone.status == CERTIFIED_WITH_WITNESSES
    assert relative.status == NO_MODEL_WITHIN_BOUND
    assert standalone.theory_digest != relative.theory_digest

    candidate_all_q = _all_relation("candidate_all_q", "Q")
    positive = certify_theory(
        signature,
        (candidate_all_q,),
        bounds,
        base_axioms=(base_all_p,),
    )
    assert positive.status == CERTIFIED_WITH_WITNESSES
    assert verify_certified_theory_suite(
        signature,
        (candidate_all_q,),
        positive.to_json(),
        base_axioms=(base_all_p,),
    ) == (True, [])


def test_generated_conditional_pack_parses_in_lean_when_available() -> None:
    lean_bin = shutil.which("lean")
    if lean_bin is None:
        pytest.skip("Lean executable is unavailable")
    signature = _relation_signature()
    x = Term.var("x")
    all_both = AxiomFormula(
        "all_both",
        Formula.forall(
            (Binder("x", "Carrier"),),
            Formula.conjunction(
                Formula.rel("P", x),
                Formula.disjunction(
                    Formula.rel("Q", x), Formula.negate(Formula.rel("Q", x))
                ),
            ),
        ),
    )
    source = lower_conditional_pack_to_lean(signature, (all_both,))

    completed = subprocess.run(
        [lean_bin, "/dev/stdin"],
        input=source,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
