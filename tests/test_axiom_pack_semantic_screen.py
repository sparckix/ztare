from __future__ import annotations

import copy
from dataclasses import replace

from ztare.leanmill.axiom_pack import (
    AxiomPack,
    generate_candidate_axiom_pack,
    lint_axiom_pack_blueprint,
    priority_uncrossed_order_blueprint,
)
from ztare.leanmill.axiom_pack_semantic_screen import (
    SAT,
    UNKNOWN,
    UNSAT,
    run_fixed_size_smt_screen,
    verify_fixed_size_smt_screen,
)
from ztare.leanmill.finite_model import FiniteModel
from ztare.leanmill.finite_table_model_finder import FiniteModelSearchReceipt
from ztare.leanmill.theory_ir import (
    AxiomFormula,
    Binder,
    Formula,
    RelationSymbol,
    SortDecl,
    Term,
    TheorySignature,
    content_hash,
)


def _predicate_pack(*, false_base: bool = False) -> tuple[
    AxiomPack,
    TheorySignature,
    tuple[AxiomFormula, ...],
    tuple[AxiomFormula, ...],
]:
    signature = TheorySignature(
        name="PredicateScreen",
        sorts=(SortDecl("Carrier"),),
        relations=(RelationSymbol("P", ("Carrier",)),),
    )
    target = AxiomFormula(
        "all_p",
        Formula.forall(
            (Binder("x", "Carrier"),),
            Formula.rel("P", Term.var("x")),
        ),
    )
    base_axioms = (
        (AxiomFormula("false_base", Formula.falsity()),) if false_base else ()
    )
    pack = AxiomPack(
        name="predicate_screen_pack",
        domain="finite_predicates",
        extends_theory="typed finite predicates",
        candidate_axioms=[target.to_json()],
        intended_unlocks=["classify a finite implication query"],
        provenance=["unit_test"],
        downstream_residuals=["finite implication status"],
        theory_signature=signature.to_json(),
        base_axioms=[row.to_json() for row in base_axioms],
        base_theory_resolved=True,
    )
    return pack, signature, base_axioms, (target,)


def _policy(
    *,
    maximum: int = 2,
    enumerative_maximum: int = 1,
    budget: int = 1,
    require_countermodel: bool = False,
) -> dict[str, object]:
    return {
        "max_finite_carrier_size": maximum,
        "filter_budget_k": budget,
        "semantic_max_carrier_size": enumerative_maximum,
        "fixed_size_smt_timeout_ms": 5_000,
        "require_countermodel_strata": require_countermodel,
    }


def _rehash(row: dict[str, object]) -> None:
    row["receipt_sha256"] = content_hash(
        {key: value for key, value in row.items() if key != "receipt_sha256"}
    )


def test_priority_screen_spends_policy_budget_at_size_five_and_replays_sat() -> None:
    blueprint = priority_uncrossed_order_blueprint()
    pack, generation = generate_candidate_axiom_pack(blueprint)
    assert generation["ok"] is True

    from ztare.leanmill.axiom_pack import _pack_formal_theory

    signature, base_axioms, candidate_axioms = _pack_formal_theory(pack)
    screen = run_fixed_size_smt_screen(
        pack=pack,
        signature=signature,
        base_axioms=base_axioms,
        candidate_axioms=candidate_axioms,
        policy=blueprint.cheap_filter_policy,
    )

    assert screen["status"] == "pass"
    assert screen["scheduled_query_count"] == 4
    assert screen["filter_budget_k"] == 4
    assert screen["filter_budget_used"] == 4
    assert screen["available_query_count"] == 12
    assert screen["budget_exhausted"] is True
    assert [row["target_axiom"]["candidate_index"] for row in screen["queries"]] == [
        0,
        1,
        2,
        3,
    ]
    assert all(row["sort_sizes"] == {"Element": 5} for row in screen["queries"])
    assert screen["summary"]["verdict_counts"] == {
        SAT: 3,
        UNSAT: 1,
        UNKNOWN: 0,
    }
    assert all(
        row["host_replay"]["countermodel_confirmed"] is True
        for row in screen["queries"]
        if row["smt_verdict"] == SAT
    )
    fixed_unsat = next(row for row in screen["queries"] if row["smt_verdict"] == UNSAT)
    assert fixed_unsat["outcome"] == "no_countermodel_at_fixed_size"
    assert fixed_unsat["premise_model_status"] == SAT
    assert fixed_unsat["proof_credit_eligible"] is False

    valid, failures = verify_fixed_size_smt_screen(
        pack=pack,
        signature=signature,
        base_axioms=base_axioms,
        candidate_axioms=candidate_axioms,
        receipt=screen,
    )
    assert valid is True
    assert failures == []


def test_rehashed_countermodel_tamper_fails_deterministic_replay() -> None:
    blueprint = priority_uncrossed_order_blueprint()
    pack, _ = generate_candidate_axiom_pack(blueprint)
    from ztare.leanmill.axiom_pack import _pack_formal_theory

    signature, base_axioms, candidate_axioms = _pack_formal_theory(pack)
    screen = run_fixed_size_smt_screen(
        pack=pack,
        signature=signature,
        base_axioms=base_axioms,
        candidate_axioms=candidate_axioms,
        policy=blueprint.cheap_filter_policy,
    )
    tampered = copy.deepcopy(screen)
    query = tampered["queries"][0]
    assert query["smt_verdict"] == SAT
    finder = query["finder_receipt"]
    priority_table = finder["witness"]["relations"]["priority"]
    finder["witness"]["relations"]["priority"] = [True] * len(priority_table)
    _rehash(finder)
    _rehash(query)
    _rehash(tampered)

    valid, failures = verify_fixed_size_smt_screen(
        pack=pack,
        signature=signature,
        base_axioms=base_axioms,
        candidate_axioms=candidate_axioms,
        receipt=tampered,
    )
    assert valid is False
    assert "query_0:deterministic_replay" in failures


def test_forged_sat_witness_and_runtime_gap_become_typed_unknown() -> None:
    pack, signature, base_axioms, candidate_axioms = _predicate_pack()
    target = candidate_axioms[0]
    bad_witness = FiniteModel(
        sort_sizes=(("Carrier", 2),),
        relations=(("P", (True, True)),),
    )

    def forged_finder(*_args: object, **kwargs: object) -> FiniteModelSearchReceipt:
        return FiniteModelSearchReceipt(
            status="countermodel_found",
            signature_hash=signature.content_hash,
            sort_sizes=(("Carrier", 2),),
            base_formula_ids=(),
            premise_formula_ids=(),
            target_formula_id="formula:" + target.semantic_hash,
            solver="test-forged-solver",
            timeout_ms=int(kwargs["timeout_ms"]),
            witness=bad_witness,
        )

    forged = run_fixed_size_smt_screen(
        pack=pack,
        signature=signature,
        base_axioms=base_axioms,
        candidate_axioms=candidate_axioms,
        policy=_policy(),
        countermodel_finder=forged_finder,
    )
    forged_query = forged["queries"][0]
    assert forged_query["smt_verdict"] == UNKNOWN
    assert forged_query["outcome"] == "countermodel_witness_replay_failed"
    assert forged_query["host_replay"]["target_holds"] is True
    assert forged_query["host_replay"]["countermodel_confirmed"] is False

    def unavailable_finder(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("solver runtime missing")

    unavailable = run_fixed_size_smt_screen(
        pack=pack,
        signature=signature,
        base_axioms=base_axioms,
        candidate_axioms=candidate_axioms,
        policy=_policy(maximum=5, enumerative_maximum=2, budget=2),
        countermodel_finder=unavailable_finder,
    )
    assert [row["smt_verdict"] for row in unavailable["queries"]] == [
        UNKNOWN,
        UNKNOWN,
    ]
    assert [row["sort_sizes"] for row in unavailable["queries"]] == [
        {"Carrier": 5},
        {"Carrier": 4},
    ]
    assert unavailable["status"] == "inconclusive"
    valid, failures = verify_fixed_size_smt_screen(
        pack=pack,
        signature=signature,
        base_axioms=base_axioms,
        candidate_axioms=candidate_axioms,
        receipt=unavailable,
    )
    assert valid is True
    assert failures == []


def test_vacuous_fixed_size_unsat_is_not_an_implication_edge() -> None:
    pack, signature, base_axioms, candidate_axioms = _predicate_pack(false_base=True)
    screen = run_fixed_size_smt_screen(
        pack=pack,
        signature=signature,
        base_axioms=base_axioms,
        candidate_axioms=candidate_axioms,
        policy=_policy(),
    )
    query = screen["queries"][0]

    assert query["smt_verdict"] == UNSAT
    assert query["outcome"] == "no_premise_model_at_fixed_size"
    assert query["premise_model_status"] == UNSAT
    assert screen["summary"]["fixed_size_implication_edges"] == []
    assert screen["summary"]["all_candidates_classified"] is False
    assert screen["status"] == "inconclusive"


def test_blueprint_lint_rejects_inoperative_or_malformed_screen_policy() -> None:
    blueprint = priority_uncrossed_order_blueprint()
    too_small = replace(
        blueprint,
        cheap_filter_policy={
            **blueprint.cheap_filter_policy,
            "max_finite_carrier_size": 1,
        },
    )
    zero_budget = replace(
        blueprint,
        cheap_filter_policy={
            **blueprint.cheap_filter_policy,
            "filter_budget_k": 0,
        },
    )

    assert any(
        "max_finite_carrier_size must be at least semantic_max_carrier_size" in row
        for row in lint_axiom_pack_blueprint(too_small)["violations"]
    )
    assert any(
        "filter_budget_k must be a positive integer" in row
        for row in lint_axiom_pack_blueprint(zero_budget)["violations"]
    )
