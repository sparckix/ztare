from __future__ import annotations

from pathlib import Path

import pytest

from ztare.leanmill.adapters import generic_fol_finite
from ztare.leanmill.adapters.generic_finite_evidence import (
    build_evidence_context,
)
from ztare.leanmill.adapters.generic_fol_finite import build_model_universe
from ztare.leanmill.common import read_json
from ztare.leanmill.equational_formula_universe import (
    EQUATIONAL_GRAMMAR_SCHEMA,
    enumerate_universal_equations,
)
from ztare.leanmill.evidence_theory_context import EvidenceTheoryContext
from ztare.leanmill.explore_axiom_space import (
    execute_frontier_boundaries,
    explore_axiom_space,
)
from ztare.leanmill.finite_model import (
    FiniteModel,
    canonicalize_finite_model,
    evaluate_axiom,
)
from ztare.leanmill.finite_table_model_finder import enumerate_finite_models_smt
from ztare.leanmill.finite_theory_context import (
    build_formal_theory_context,
    load_formal_theory_context,
    save_formal_theory_context,
)
from ztare.leanmill.formal_verification_provider import generate_keypair
from ztare.leanmill.frontier_blueprint import FrontierExplorationBrief
from ztare.leanmill.frontier_campaign import sign_frontier_campaign
from ztare.leanmill.frontier_boundary import larger_model_strata
from ztare.leanmill.magma_law_universe import anonymous_magma_signature
from ztare.leanmill.theory_ir import (
    AxiomFormula,
    Binder,
    Formula,
    OperationSymbol,
    SortDecl,
    Term,
    TheorySignature,
    content_hash,
)
from ztare.leanmill.theory_language import (
    TheoryLanguageExpansionRequest,
    compile_theory_language_expansion,
)


def _fixture():
    signature = TheorySignature(
        name="UnarySystem",
        sorts=(SortDecl("S"),),
        operations=(OperationSymbol("step", ("S",), "S"),),
    )
    reflexive = AxiomFormula(
        "reflexive",
        Formula.forall((Binder("x", "S"),), Formula.eq(Term.var("x"), Term.var("x"))),
    )
    idempotent = AxiomFormula(
        "step_idempotent",
        Formula.forall(
            (Binder("x", "S"),),
            Formula.eq(
                Term.app("step", Term.app("step", Term.var("x"))),
                Term.app("step", Term.var("x")),
            ),
        ),
    )
    return signature, (reflexive, idempotent)


def test_heldout_strata_lower_to_executable_countermodel_sizes():
    signature, _ = _fixture()
    assert larger_model_strata(
        signature,
        {
            "heldout_strata": [
                {"sort_sizes": {"S": 4}, "checks": ["counterexample_search"]},
                {"sort_sizes": {"S": 5}, "checks": ["formal_translation"]},
            ]
        },
    ) == ((("S", 4),), (("S", 5),))


def test_generic_adapter_builds_non_magma_context_and_replays(tmp_path):
    signature, formulas = _fixture()
    universe = build_model_universe(
        signature, strata=({"sort_sizes": {"S": 2}},)
    )
    assert len(universe.models) == 3
    assert sum(row.multiplicity for row in universe.models) == 4
    assert universe.receipt.quotient_policy == (
        "sortwise_isomorphism_canonicalization.v1"
    )
    context = build_formal_theory_context(
        signature=signature, formulas=formulas, universe=universe
    )
    assert context.incidence.exact
    path = save_formal_theory_context(context, tmp_path / "generic.json")
    assert load_formal_theory_context(path).context_hash == context.context_hash


def test_reviewed_functor_image_compiles_from_evidence_incidence_context():
    source_signature = TheorySignature(
        name="ExactObservations",
        sorts=(SortDecl("Observation"),),
    )
    source = build_evidence_context(
        source_signature,
        adapter_config={
            "completeness_ref": "fixture:three-observations",
            "objects": [
                {"object_id": "o0", "payload": {"order": 0}},
                {"object_id": "o1", "payload": {"order": 1}},
                {"object_id": "o2", "payload": {"order": 2}},
            ],
            "hypotheses": [
                {
                    "hypothesis_id": "h0",
                    "satisfied_object_ids": ["o0", "o1", "o2"],
                    "anonymous_shape": {"kind": "exact_observation"},
                }
            ],
        },
        strata=(),
    )
    target_signature = TheorySignature(
        name="MechanismCoordinate",
        sorts=(SortDecl("S"),),
        operations=(OperationSymbol("step", ("S",), "S"),),
    )
    identity = FiniteModel(
        sort_sizes=(("S", 2),),
        operations=(("step", (0, 1)),),
    )
    constant_zero = FiniteModel(
        sort_sizes=(("S", 2),),
        operations=(("step", (0, 0)),),
    )
    target_grammar = _equation_grammar(2)
    application_core = {
        "schema": "leanmill.finite_model_functor_application.v2",
        "gap_id": "gap:evidence-mechanism",
        "context_hash": source.context_hash,
        "context_kind": "evidence_incidence",
        "functor_id": "fixture:evidence-mechanism-coordinate",
        "signature": target_signature.to_json(),
        "formula_grammar": target_grammar,
        "models": {
            "o0": identity.to_json(),
            "o1": constant_zero.to_json(),
            "o2": constant_zero.to_json(),
        },
    }
    application = {
        **application_core,
        "receipt_sha256": content_hash(application_core),
    }

    compiled = generic_fol_finite.compile_theory_language_expansion(
        request=object(),
        source_context=source,
        formula_grammar={},
        approved_application=application,
    )

    assert compiled["status"] == "compiled"
    transition = compiled["transition"]
    assert transition["source_context_hash"] == source.context_hash
    assert transition["source_context_kind"] == "evidence_incidence"
    assert transition["source_object_count"] == 3
    assert transition["canonical_image_model_count"] == 2
    assert sum(
        row.multiplicity for row in compiled["context"].universe.models
    ) == 3
    assert transition["successor_formula_grammar"] == target_grammar

    polynomial_source = EvidenceTheoryContext(
        signature=source.signature,
        adapter_id="rational_polynomial_map.v1",
        incidence=source.incidence,
        formula_profiles=source.formula_profiles,
        object_records=source.object_records,
        completeness_receipt_digest=source.completeness_receipt_digest,
        base_axioms=source.base_axioms,
    )
    polynomial_application_core = {
        **application_core,
        "context_hash": polynomial_source.context_hash,
    }
    polynomial_application = {
        **polynomial_application_core,
        "receipt_sha256": content_hash(polynomial_application_core),
    }
    request = TheoryLanguageExpansionRequest(
        source_context_hash=polynomial_source.context_hash,
        source_epoch=0,
        change_kind="quotient_or_coordinate_change",
        blind_spot="Exact polynomial observations alias in the current chart.",
        proposed_interface="A reviewed finite mechanism coordinate.",
        evidence_refs=("fixture:polynomial-observation-receipt",),
        discriminating_test="The target chart separates the aliased observations.",
        kill_condition="The image is partial or lacks a target grammar.",
    )

    dispatched = compile_theory_language_expansion(
        request,
        source_context=polynomial_source,
        source_adapter_id="rational_polynomial_map.v1",
        formula_grammar={},
        approved_application=polynomial_application,
    )

    assert dispatched.status == "compiled"
    assert dispatched.adapter_id == "generic_fol_finite.v1"
    assert dispatched.attempts[0] == {
        "adapter_id": "rational_polynomial_map.v1",
        "status": "unavailable",
        "reason": "compiler_capability_absent",
    }


def test_evidence_functor_image_without_target_grammar_is_rejected():
    source_signature = TheorySignature(
        name="ExactObservations",
        sorts=(SortDecl("Observation"),),
    )
    source = build_evidence_context(
        source_signature,
        adapter_config={
            "completeness_ref": "fixture:one-observation",
            "objects": [{"object_id": "o0", "payload": {"order": 0}}],
            "hypotheses": [
                {
                    "hypothesis_id": "h0",
                    "satisfied_object_ids": ["o0"],
                    "anonymous_shape": {"kind": "exact_observation"},
                }
            ],
        },
        strata=(),
    )
    target_signature = TheorySignature(
        name="MechanismCoordinate",
        sorts=(SortDecl("S"),),
        operations=(OperationSymbol("step", ("S",), "S"),),
    )
    identity = FiniteModel(
        sort_sizes=(("S", 2),),
        operations=(("step", (0, 1)),),
    )
    application_core = {
        "schema": "leanmill.finite_model_functor_application.v1",
        "gap_id": "gap:missing-target-grammar",
        "context_hash": source.context_hash,
        "context_kind": "evidence_incidence",
        "functor_id": "fixture:missing-target-grammar",
        "signature": target_signature.to_json(),
        "models": {"o0": identity.to_json()},
    }
    application = {
        **application_core,
        "receipt_sha256": content_hash(application_core),
    }

    compiled = generic_fol_finite.compile_theory_language_expansion(
        request=object(),
        source_context=source,
        formula_grammar=_equation_grammar(2),
        approved_application=application,
    )

    assert compiled == {
        "status": "rejected",
        "reason": (
            "evidence functor application must declare its target formula grammar"
        ),
    }


def test_exact_smt_census_matches_exhaustive_isomorphism_classes(tmp_path) -> None:
    signature, formulas = _fixture()
    exhaustive = build_model_universe(
        signature, strata=({"sort_sizes": {"S": 3}},)
    )
    solver_enumerated = build_model_universe(
        signature,
        strata=({"sort_sizes": {"S": 3}},),
        adapter_config={
            "model_generation": {
                "mode": "smt_exact",
                "max_canonical_models_per_stratum": 20,
                "timeout_ms_per_stratum": 10_000,
            }
        },
    )

    assert [
        (row.model.to_json(), row.multiplicity) for row in solver_enumerated.models
    ] == [(row.model.to_json(), row.multiplicity) for row in exhaustive.models]
    assert solver_enumerated.receipt.generation_policy == (
        "smt_isomorphism_class_enumeration.v1"
    )
    solver_receipt = solver_enumerated.receipt.stratum_enumeration_receipts[0]
    assert solver_receipt["status"] == "exhausted"
    assert solver_receipt["complete"] is True
    assert solver_receipt["solver_checks"] == len(solver_enumerated.models) + 1

    context = build_formal_theory_context(
        signature=signature,
        formulas=formulas,
        universe=solver_enumerated,
    )
    path = save_formal_theory_context(context, tmp_path / "solver-enumerated.json")
    assert load_formal_theory_context(path).context_hash == context.context_hash


def test_smt_census_cap_cannot_be_laundered_as_exact() -> None:
    signature, _formulas = _fixture()
    partial = enumerate_finite_models_smt(
        signature,
        sort_sizes={"S": 3},
        max_canonical_models=1,
        timeout_ms=10_000,
    )
    assert partial.receipt.status == "model_cap_reached"
    assert partial.receipt.complete is False
    assert partial.receipt.solver_checks == 2

    with pytest.raises(
        generic_fol_finite.IncompleteFiniteModelUniverseError,
        match="model_cap_reached",
    ) as caught:
        build_model_universe(
            signature,
            strata=({"sort_sizes": {"S": 3}},),
            adapter_config={
                "model_generation": {
                    "mode": "smt_exact",
                    "max_canonical_models_per_stratum": 1,
                    "timeout_ms_per_stratum": 10_000,
                }
            },
        )
    failure = caught.value.failure_receipt()
    assert failure["status"] == "incomplete"
    assert failure["enumeration_receipt"]["canonical_model_count"] == 1
    assert failure["enumeration_receipt"]["complete"] is False
    partial_snapshot = caught.value.partial_snapshot()
    assert len(partial_snapshot["model_classes"]) == 1
    assert partial_snapshot["receipt_sha256"]


def test_signature_generic_smt_reproduces_small_cycle_structure_counts() -> None:
    signature = TheorySignature(
        name="AnonymousCycleStructure",
        sorts=(SortDecl("S"),),
        operations=(
            OperationSymbol("op", ("S", "S"), "S"),
            OperationSymbol("ldiv", ("S", "S"), "S"),
            OperationSymbol("undiag", ("S",), "S"),
        ),
    )
    x, y, z = (Term.var(name) for name in ("x", "y", "z"))

    def op(left, right):
        return Term.app("op", left, right)

    def ldiv(left, right):
        return Term.app("ldiv", left, right)

    def undiag(value):
        return Term.app("undiag", value)

    def axiom(name, variables, left, right):
        return AxiomFormula(
            name,
            Formula.forall(
                tuple(Binder(variable, "S") for variable in variables),
                Formula.eq(left, right),
            ),
        )

    base_axioms = (
        axiom("base_0", "xy", op(x, ldiv(x, y)), y),
        axiom("base_1", "xy", ldiv(x, op(x, y)), y),
        axiom(
            "base_2",
            "xyz",
            op(op(x, y), op(x, z)),
            op(op(y, x), op(y, z)),
        ),
        axiom("base_3", "x", undiag(op(x, x)), x),
        axiom("base_4", "x", op(undiag(x), undiag(x)), x),
    )
    config = {
        "model_generation": {
            "mode": "smt_exact",
            "max_canonical_models_per_stratum": 32,
            "timeout_ms_per_stratum": 10_000,
        }
    }

    counts = []
    for carrier_size in (2, 3, 4):
        universe = build_model_universe(
            signature,
            strata=({"sort_sizes": {"S": carrier_size}},),
            base_axioms=base_axioms,
            adapter_config=config,
        )
        counts.append(len(universe.models))
        assert universe.receipt.stratum_enumeration_receipts[0]["status"] == (
            "exhausted"
        )
    assert counts == [2, 5, 23]


def test_generic_context_source_has_no_magma_dependency():
    source = (
        Path(__file__).parents[1] / "src/ztare/leanmill/finite_theory_context.py"
    ).read_text(encoding="utf-8")
    assert "magma" not in source.lower()


def test_generic_isomorphism_quotient_is_signature_property() -> None:
    signature, _formulas = _fixture()
    left = FiniteModel(
        sort_sizes=(("S", 2),),
        operations=(("step", (0, 0)),),
    )
    right = FiniteModel(
        sort_sizes=(("S", 2),),
        operations=(("step", (1, 1)),),
    )

    assert canonicalize_finite_model(signature, left) == canonicalize_finite_model(
        signature, right
    )


def _equation_grammar(order: int) -> dict[str, object]:
    return {
        "schema": EQUATIONAL_GRAMMAR_SCHEMA,
        "max_total_operation_order": order,
        "max_formulas": 10_000,
        "variable_renaming_quotient": True,
        "equation_side_quotient": True,
        "exclude_nonvariable_reflexive": True,
    }


def test_signature_driven_equation_band_reproduces_magma_counts() -> None:
    signature = anonymous_magma_signature()
    rows = enumerate_universal_equations(signature, _equation_grammar(3))
    counts = [
        sum(row.exact_operation_order == order for row in rows)
        for order in range(4)
    ]
    assert counts == [2, 5, 39, 364]
    assert len({row.formula_id for row in rows}) == 410


def test_non_magma_public_campaign_reuses_snapshot_and_runs_generic_smt(
    tmp_path, monkeypatch
) -> None:
    signature = TheorySignature(
        name="UnaryBinary",
        sorts=(SortDecl("S"),),
        operations=(
            OperationSymbol("inv", ("S",), "S"),
            OperationSymbol("mul", ("S", "S"), "S"),
        ),
    )
    draft = {
        "mode": "anonymous_signature_census",
        "eigenquestion": "Which anonymous two-formula regions have residual consequences?",
        "signature": signature.to_json(),
        "primitive_semantics": {
            "operation_bindings": {
                "inv": "total finite unary operation table",
                "mul": "total finite binary operation table",
            },
            "relation_bindings": {},
        },
        "base_axioms": [],
        "base_theory_status": "explicit_empty",
        "adapter_id": "generic_fol_finite.v1",
        "adapter_config": {
            "model_generation": {
                "mode": "smt_exact",
                "max_canonical_models_per_stratum": 64,
                "timeout_ms_per_stratum": 20_000,
            }
        },
        "formula_grammar": _equation_grammar(2),
        "model_or_observation_strata": [{"sort_sizes": {"S": 2}}],
        "pack_arity": 2,
        "collapse_controls": [],
        "visible_evidence_manifest": {},
        "sealed_evidence_manifest_digest": "sha256:" + "0" * 64,
        "deanchoring_policy": {"cold_after_signature_compilation": True},
        "navigator_contract": {
            "adapter_id": "axiompack",
            "selection_mode": "compact_axiom_pack",
        },
        "query_budget": {
            "max_finalists": 2,
            "max_ranked_queries": 4,
            "larger_model_queries": 1,
        },
        "stop_rule": {"freeze_after_finalists": 2},
        "verification_plan": {
            "larger_model_strata": [{"sort_sizes": {"S": 3}}],
            "conditional_lean": False,
            "smt_timeout_ms": 2_000,
        },
        "codec_versions": {"formula": "generic-equation-v1"},
        "authority_refs": ["test-campaign-authority"],
    }
    private, _public = generate_keypair()

    def signer(packet):
        return sign_frontier_campaign(
            packet,
            private_key_pem=private,
            signer_ref="test-campaign-authority",
        )

    first = tmp_path / "first"
    run = explore_axiom_space(
        FrontierExplorationBrief(
            "Explore an anonymous unary-binary signature.",
            source_mode="structure_first",
        ),
        attempt_dir=first,
        typed_draft=draft,
        packet_signer=signer,
        budget="smoke_20m",
    )
    assert run.status == "frontier_candidates_frozen_awaiting_boundary_approval"
    assert run.context_summary["formula_count"] == 71
    assert load_formal_theory_context(first / "formal_context.json").universe.receipt.schema == (
        "leanmill.generic_finite_model_universe.v3"
    )
    boundary = execute_frontier_boundaries(first)
    searches = [
        search
        for row in boundary["boundary_result"]["query_results"]
        for search in row["countermodel_searches"]
    ]
    query_rows = boundary["boundary_result"]["query_results"]
    assert query_rows
    assert all(
        row["logical_premise_ablation"]["schema"]
        == "leanmill.finite_context_single_premise_ablation.v1"
        and row["logical_premise_ablation"]["status"]
        == "certified_single_premise_nonimplication"
        for row in query_rows
    )
    assert searches
    assert all(row["schema"] == "leanmill.finite_model_search.v1" for row in searches)
    assert all(row["sort_sizes"] == {"S": 3} for row in searches)
    countermodels = [row for row in searches if row["status"] == "countermodel_found"]
    context = load_formal_theory_context(first / "formal_context.json")
    formulas = {row.formula_id: row.axiom for row in context.formula_profiles}
    for row in countermodels:
        witness = FiniteModel.from_json(row["witness"])
        assert row["host_replay_status"] == "passed"
        assert row["signature_sha256"] == signature.content_hash
        assert all(
            evaluate_axiom(signature, formulas[formula_id], witness)
            for formula_id in row["premise_formula_ids"]
        )
        assert not evaluate_axiom(
            signature, formulas[row["target_formula_id"]], witness
        )

    snapshot = read_json(first / "formal_context.json", {})
    monkeypatch.setattr(
        generic_fol_finite,
        "build_model_universe",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("compatible snapshot must skip model enumeration")
        ),
    )
    second = tmp_path / "second"
    replay = explore_axiom_space(
        FrontierExplorationBrief(
            "Explore an anonymous unary-binary signature.",
            source_mode="structure_first",
        ),
        attempt_dir=second,
        typed_draft=draft,
        packet_signer=signer,
        budget="smoke_20m",
        frozen_context_ref={
            "path": str(first / "formal_context.json"),
            "context_hash": snapshot["context_hash"],
            "snapshot_sha256": snapshot["snapshot_sha256"],
        },
    )
    assert replay.context_hash == run.context_hash
    assert read_json(second / "context_reuse_receipt.json", {})["provider_calls"] == 0
