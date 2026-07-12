from __future__ import annotations

from itertools import combinations
import json
from jsonschema import Draft202012Validator

from ztare.common.leaf_workbench_environment import (
    leaf_workbench_environment_ids,
    resolve_leaf_workbench_environment,
)
from ztare.common.finite_incidence_context import build_incidence_context
from ztare.leanmill.evidence_theory_context import (
    EvidenceHypothesisProfile,
    EvidenceObjectRecord,
    EvidenceTheoryContext,
)
from ztare.leanmill.finite_model_census import enumerate_magma_model_universe
from ztare.leanmill.finite_theory_context import build_formal_theory_context
from ztare.leanmill.adapters.generic_finite_evidence import build_evidence_context
from ztare.leanmill.magma_law_universe import anonymous_magma_signature, magma_laws_through_order
from ztare.leanmill.axiompack_leaf_workbench import navigator_decision_output_schema
from ztare.leanmill.theory_interest import DIRECT_EQUATIONAL_BASELINE_REF
from ztare.leanmill.theory_ir import SortDecl, TheorySignature


def _context():
    signature = anonymous_magma_signature()
    laws = magma_laws_through_order(1)
    return build_formal_theory_context(
        signature=signature,
        formulas=tuple(row.axiom for row in laws),
        universe=enumerate_magma_model_universe(signature, carrier_sizes=(2,)),
    )


def _run(environment, capability_id, input_refs):
    return environment["action_handlers"][capability_id](
        ".", {"input_refs": input_refs}, None, environment["contract"]
    )


def test_sampled_workbench_exposes_prediction_profiles_without_exact_closure():
    incidence = build_incidence_context(
        object_ids=("o0", "o1"),
        attribute_truth_bits={"h0": 0b01, "h1": 0b01},
        exact=False,
    )
    context = EvidenceTheoryContext(
        signature=TheorySignature(name="Evidence", sorts=(SortDecl("Observation"),)),
        adapter_id="sampled-test.v1",
        incidence=incidence,
        formula_profiles=tuple(
            EvidenceHypothesisProfile(
                formula_id=row.attribute_id,
                truth_bits=row.truth_bits,
                anonymous_shape={"slot": index},
                payload={},
            )
            for index, row in enumerate(incidence.profiles)
        ),
        object_records=(
            EvidenceObjectRecord("o0", "sample", {}),
            EvidenceObjectRecord("o1", "sample", {}),
        ),
        completeness_receipt_digest="sampled:unclaimed",
    )
    env = resolve_leaf_workbench_environment(
        "axiompack", context=context, selection_mode="theory_program"
    )
    assert "list_theory_nodes" not in env["contract"].registry()
    selected = _run(
        env,
        "select_theory_presentation",
        {"formula_ids": ["h0"], "prediction_formula_ids": ["h1"]},
    )["output_summary"]
    assert selected["closure_size"] is None
    assert selected["prediction_profile"]["context_exact"] is False
    assert selected["prediction_profile"]["predictions"][0]["chart_status"] == (
        "holds_on_observed_context"
    )


def test_static_environment_resolver_supports_worldmodel_and_axiompack():
    assert leaf_workbench_environment_ids() == ("axiompack", "worldmodel")
    env = resolve_leaf_workbench_environment("axiompack", context=_context())
    assert env["adapter_id"] == "axiompack"
    assert set(env["action_handlers"]) == set(env["contract"].registry())
    assert env["contract"].resolve_capability_ref("list_theory_nodes@v1") == (
        "list_theory_nodes"
    )


def test_navigator_result_schema_is_strict_and_accepts_typed_envelopes():
    schema = navigator_decision_output_schema()
    assert "uniqueItems" not in json.dumps(schema)
    validator = Draft202012Validator(schema)
    validator.validate({
        "decision": "request",
        "rationale": "Inspect the first node page.",
        "capability_id": "list_theory_nodes@v1",
        "input_refs": {"offset": 0, "limit": 16},
        "formula_ids": None,
        "boundary_target_ids": None,
    })
    validator.validate({
        "decision": "request",
        "rationale": "The current signature cannot express the observed distinction.",
        "capability_id": "propose_theory_language_expansion",
        "input_refs": {
            "change_kind": "new_observable",
            "blind_spot": "Two objects share every current formula profile.",
            "proposed_interface": "One executable orbit-length observable.",
            "evidence_refs": ["object:a", "object:b"],
            "discriminating_test": "The observable separates the pair.",
            "kill_condition": "The observable does not separate the pair.",
        },
        "formula_ids": None,
        "boundary_target_ids": None,
    })
    validator.validate({
        "decision": "request",
        "rationale": "Name a repeated term before testing its iterate.",
        "capability_id": "propose_frontier_formula",
        "input_refs": {
            "structural_conjecture": "A derived diagonal may expose a hidden period.",
            "axiom_name": "derived_period_candidate",
            "variables": [{"name": "x0", "sort": "sort_0"}],
            "formula_tokens": ["x0", "aux_0", "aux_0", "x0", "eq"],
            "definitions": [{
                "name": "aux_0",
                "parameters": [{"name": "z", "sort": "sort_0"}],
                "body_tokens": ["z", "z", "op_0"],
            }],
            "nl_intent": "The second iterate of the derived diagonal fixes every point.",
            "kill_condition": "A finite structure has a longer derived orbit.",
            "contrast_object_ids": None,
        },
        "formula_ids": None,
        "boundary_target_ids": None,
    })
    validator.validate({
        "decision": "request",
        "rationale": "The relation language needs a quantified coordinate.",
        "capability_id": "propose_frontier_formula",
        "input_refs": {
            "structural_conjecture": "Two equations may hold or fail together.",
            "axiom_name": "coupled_candidate",
            "variables": [
                {"name": "x0", "sort": "sort_0"},
                {"name": "x1", "sort": "sort_0"},
            ],
            "formula_tokens": [
                "x0", "x1", "op_0", "x0", "eq",
                "x1", "x0", "op_0", "x1", "eq", "iff",
            ],
            "nl_intent": "The two directional absorption equations are equivalent.",
            "kill_condition": "A finite structure satisfies exactly one direction.",
            "contrast_object_ids": None,
        },
        "formula_ids": None,
        "boundary_target_ids": None,
    })
    validator.validate({
        "decision": "freeze",
        "rationale": "Independent pair with a joint-only consequence.",
        "capability_id": None,
        "input_refs": {},
        "formula_ids": ["formula:a", "formula:b"],
        "boundary_target_ids": ["formula:c"],
    })
    validator.validate({
        "decision": "reject_all",
        "rationale": "The host baseline explains every inspected candidate.",
        "capability_id": None,
        "input_refs": {},
        "formula_ids": None,
        "boundary_target_ids": None,
    })
    validator.validate({
        "decision": "request",
        "rationale": "The seed band cannot express associativity.",
        "capability_id": "propose_frontier_formula",
        "input_refs": {
            "structural_conjecture": "Compare the two binary bracketing shapes.",
            "axiom_name": "assoc_candidate",
            "variables": [
                {"name": "x0", "sort": "sort_0"},
                {"name": "x1", "sort": "sort_0"},
                {"name": "x2", "sort": "sort_0"},
            ],
            "lhs_tokens": ["x0", "x1", "op_0", "x2", "op_0"],
            "rhs_tokens": ["x0", "x1", "x2", "op_0", "op_0"],
            "nl_intent": "The binary operation is associative.",
            "kill_condition": "A finite table separates the bracketings.",
            "contrast_object_ids": ["object:a", "object:b"],
        },
        "formula_ids": None,
        "boundary_target_ids": None,
    })


def test_anonymous_node_navigation_and_presentation_selection():
    context = _context()
    env = resolve_leaf_workbench_environment("axiompack", context=context)
    nodes = context.generated_theory_nodes(max_presentation_size=2)
    inspected = _run(env, "inspect_theory_node", {"node_id": nodes[0].node_id})
    assert inspected["context_hash"] == context.context_hash
    assert "minimal_generators" in inspected["output_summary"]

    pair = next(
        row for row in combinations(context.formula_ids, 2)
        if context.synergy_ids(row)
    )
    synergy = _run(env, "select_theory_presentation", {"formula_ids": list(pair)})
    selected = _run(env, "select_theory_presentation", {"formula_ids": list(pair)})
    assert synergy["output_summary"]["synergy_formula_ids"]
    assert synergy["output_summary"]["residual_yield"]["baseline_ref"] == (
        DIRECT_EQUATIONAL_BASELINE_REF
    )
    assert "residual_synergy_formula_ids" in synergy["output_summary"]
    assert selected["output_summary"]["node_id"] in {row.node_id for row in nodes}


def test_topology_overview_width_does_not_cap_candidate_width():
    context = _context()
    env = resolve_leaf_workbench_environment(
        "axiompack",
        context=context,
        max_presentation_size=3,
        topology_presentation_size=1,
    )
    page = _run(env, "list_theory_nodes", {"offset": 0, "limit": 64})[
        "output_summary"
    ]
    expected = context.generated_theory_nodes(
        max_presentation_size=1, semantic_quotient=True
    )
    assert page["total"] == len(expected)
    assert "through_width_1" in page["topology_policy"]

    selected = _run(
        env,
        "select_theory_presentation",
        {"formula_ids": list(context.formula_ids[:3])},
    )["output_summary"]
    assert selected["node_id"]


def test_language_identity_change_is_receipted_as_outbound_request():
    context = _context()
    env = resolve_leaf_workbench_environment(
        "axiompack", context=context, context_epoch=4
    )
    output = _run(
        env,
        "propose_theory_language_expansion",
        {
            "change_kind": "new_observable",
            "blind_spot": "Current equations alias objects with different orbit lengths.",
            "proposed_interface": "An executable orbit-length observation over the current carrier.",
            "evidence_refs": [context.object_ids[0]],
            "discriminating_test": "The observation splits one current object class.",
            "kill_condition": "It duplicates the current observational partition.",
        },
    )["output_summary"]

    assert output["status"] == "outbound_blueprint_request"
    assert output["request"]["source_epoch"] == 4
    assert output["request"]["authority"] == "proposal_only"
    assert output["next_route"] == "frontier_blueprint_compiler_or_adapter_forge"


def test_malformed_language_request_is_receipted_without_mutating_context():
    context = _context()
    env = resolve_leaf_workbench_environment("axiompack", context=context)
    output = _run(
        env,
        "propose_theory_language_expansion",
        {"blind_spot": "missing observable"},
    )["output_summary"]

    assert output["status"] == "rejected_invalid_language_request"
    assert output["error_code"] == "language_request_decode_failed"
    assert output["request_id"] is None
    assert output["claim_boundary"].startswith("malformed model proposal rejected")


def test_compare_nodes_returns_a_bounded_separation_model():
    context = _context()
    env = resolve_leaf_workbench_environment("axiompack", context=context)
    nodes = context.generated_theory_nodes(max_presentation_size=2)
    left, right = next(
        (a, b) for a, b in combinations(nodes, 2) if a.extent_bits != b.extent_bits
    )
    receipt = _run(
        env,
        "compare_theory_nodes",
        {"left_node_id": left.node_id, "right_node_id": right.node_id},
    )
    assert receipt["output_summary"]["extent_distance"] > 0
    assert receipt["output_summary"]["separation_model_id"] in context.universe.model_ids


def test_contrastive_formula_proposal_refines_an_anonymous_object_class():
    context = _context()
    env = resolve_leaf_workbench_environment("axiompack", context=context)
    blind_spot = _run(
        env,
        "show_indistinguishable_objects",
        {"offset": 0, "limit": 1},
    )["output_summary"]

    assert blind_spot["status"] == "available"
    assert blind_spot["pair_count"] > 0
    pair = blind_spot["pairs"][0]
    assert pair["objects"][0]["object_kind"] == "finite_structure"
    assert pair["objects"][0]["operations"][0]["symbol"] == "op_0"
    assert context.object_contrast_admissible is True

    failed = _run(
        env,
        "propose_frontier_formula",
        {
            "structural_conjecture": "A reflexive term comparison may separate them.",
            "axiom_name": "failed_contrast_candidate",
            "variables": [{"name": "x0", "sort": "sort_0"}],
            "lhs_tokens": ["x0", "x0", "op_0"],
            "rhs_tokens": ["x0", "x0", "op_0"],
            "nl_intent": "The same diagonal term equals itself.",
            "kill_condition": "The displayed objects give the same truth value.",
            "contrast_object_ids": pair["object_ids"],
        },
    )["output_summary"]
    assert failed["status"] == "proposed_formula_failed_contrast"
    assert failed["formula_identity_new"] is True
    assert failed["semantic_profile_new_witness"] is None

    receipt = _run(
        env,
        "propose_frontier_formula",
        {
            "structural_conjecture": (
                "A short diagonal iterate may distinguish these anonymous structures."
            ),
            "axiom_name": "contrastive_diagonal_candidate",
            "variables": [{"name": "x0", "sort": "sort_0"}],
            "lhs_tokens": ["x0"],
            "rhs_tokens": ["x0", "x0", "x0", "op_0", "op_0"],
            "nl_intent": "A three-occurrence diagonal iterate fixes every element.",
            "kill_condition": "The displayed objects give the same truth value.",
            "contrast_object_ids": pair["object_ids"],
        },
    )["output_summary"]

    assert receipt["status"] == "proposed_new_formula"
    assert receipt["separates_contrast"] is True
    assert len(set(receipt["contrast_truth_values"].values())) == 2
    assert receipt["semantic_profile_new_witness"]["object_ids"] == pair["object_ids"]


def test_indistinguishable_object_surface_is_shared_with_evidence_contexts():
    context = build_evidence_context(
        TheorySignature(name="Evidence", sorts=(SortDecl("Observation"),)),
        adapter_config={
            "completeness_ref": "fixture:complete",
            "objects": [
                {"object_id": "o0", "payload": {"state": "left"}},
                {"object_id": "o1", "payload": {"state": "right"}},
            ],
            "hypotheses": [
                {
                    "hypothesis_id": "h0",
                    "satisfied_object_ids": ["o0", "o1"],
                    "anonymous_shape": {"kind": "predicate", "slot": 0},
                },
                {
                    "hypothesis_id": "h1",
                    "satisfied_object_ids": ["o0", "o1"],
                    "anonymous_shape": {"kind": "predicate", "slot": 1},
                },
            ],
        },
        strata=(),
    )
    env = resolve_leaf_workbench_environment("axiompack", context=context)

    output = _run(
        env,
        "show_indistinguishable_objects",
        {"offset": 0, "limit": 1},
    )["output_summary"]

    assert output["status"] == "available"
    assert output["pairs"][0]["object_ids"] == ["o0", "o1"]
    assert [row["object_kind"] for row in output["pairs"][0]["objects"]] == [
        "evidence_record",
        "evidence_record",
    ]


def test_typed_formula_proposal_escapes_seed_band_without_leaking_signature_names():
    context = _context()
    env = resolve_leaf_workbench_environment("axiompack", context=context)
    receipt = _run(
        env,
        "propose_frontier_formula",
        {
            "structural_conjecture": "The two ternary bracketing shapes may separate models.",
            "axiom_name": "assoc_candidate",
            "variables": [
                {"name": "x0", "sort": "sort_0"},
                {"name": "x1", "sort": "sort_0"},
                {"name": "x2", "sort": "sort_0"},
            ],
            "lhs_tokens": ["x0", "x1", "op_0", "x2", "op_0"],
            "rhs_tokens": ["x0", "x1", "x2", "op_0", "op_0"],
            "nl_intent": "The binary operation is associative.",
            "kill_condition": "A finite table refutes the equation.",
        },
    )

    output = receipt["output_summary"]
    assert output["status"] == "proposed_new_formula"
    assert output["formula_identity_new"] is True
    assert output["formula_id"] not in context.formula_ids
    assert output["typed_proposal_sha256"]
    assert "theory_signature" not in output
    assert "axiom" not in output

    general = _run(
        env,
        "propose_frontier_formula",
        {
            "structural_conjecture": "Two directional equations may be coupled.",
            "axiom_name": "coupled_candidate",
            "variables": [
                {"name": "x0", "sort": "sort_0"},
                {"name": "x1", "sort": "sort_0"},
            ],
            "formula_tokens": [
                "x0", "x1", "op_0", "x0", "eq",
                "x1", "x0", "op_0", "x1", "eq", "iff",
            ],
            "nl_intent": "Two directional absorption equations are equivalent.",
            "kill_condition": "A finite table satisfies exactly one direction.",
        },
    )["output_summary"]
    assert general["status"] == "proposed_new_formula"
    assert general["codec"] == "leanmill.typed_postfix_formula.v1"

    represented = _run(
        env,
        "propose_frontier_formula",
        {
            "structural_conjecture": "A derived diagonal may expose a hidden period.",
            "axiom_name": "derived_period_candidate",
            "variables": [{"name": "x0", "sort": "sort_0"}],
            "formula_tokens": ["x0", "aux_0", "aux_0", "x0", "eq"],
            "definitions": [{
                "name": "aux_0",
                "parameters": [{"name": "z", "sort": "sort_0"}],
                "body_tokens": ["z", "z", "op_0"],
            }],
            "nl_intent": "The second derived diagonal iterate is the identity.",
            "kill_condition": "A finite table has a longer diagonal orbit.",
        },
    )["output_summary"]
    assert represented["definition_ids"]
    assert represented["definitions_expand_to_prior_signature"] is True


def test_malformed_typed_formula_is_receipted_instead_of_escaping_the_action_boundary():
    context = _context()
    env = resolve_leaf_workbench_environment("axiompack", context=context)
    receipt = _run(
        env,
        "propose_frontier_formula",
        {
            "structural_conjecture": "A quantified diagonal may expose a fixed point.",
            "axiom_name": "bad_quantifier_order",
            "variables": [{"name": "x0", "sort": "sort_0"}],
            "formula_tokens": ["exists:x0", "x0", "x0", "op_0", "eq"],
            "nl_intent": "Test a fixed-point coordinate.",
            "kill_condition": "The typed proposal is rejected or does not separate a model.",
        },
    )

    output = receipt["output_summary"]
    assert output["status"] == "rejected_invalid_typed_formula"
    assert output["error_code"] == "typed_formula_decode_failed"
    assert output["formula_id"] is None
    assert output["typed_proposal_sha256"] == ""
    assert output["claim_boundary"].startswith("malformed model proposal rejected")
