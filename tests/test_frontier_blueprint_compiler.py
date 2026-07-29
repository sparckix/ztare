from __future__ import annotations

import pytest

from ztare.leanmill.adapter_forge import AdapterGapRequired
from ztare.leanmill.adapters import magma_equational
from ztare.leanmill.axiompack_leaf_workbench import AXIOMPACK_LEAF_WORKBENCH_CONTRACT
from ztare.leanmill.frontier_blueprint import (
    FrontierExplorationBrief,
    THEORY_TASK_CAPABILITY_SCOPE_SCHEMA,
    cold_navigator_manifest,
    host_isolated_lineage_count,
    navigator_selection_mode,
    topology_presentation_size,
)
from ztare.leanmill.frontier_blueprint_compiler import (
    compile_frontier_blueprint,
    compile_structure_first_blueprint,
)
from ztare.leanmill.magma_law_universe import anonymous_magma_signature
from ztare.leanmill.theory_ir import AxiomFormula, Binder, Formula, Term


def _draft():
    return {
        "mode": "anonymous_signature_census",
        "eigenquestion": "Which two-formula regions create joint consequences?",
        "signature": anonymous_magma_signature().to_json(),
        "primitive_semantics": {
            "operation_bindings": {"op0": "total finite binary operation table"},
            "relation_bindings": {},
        },
        "base_axioms": (),
        "base_theory_status": "explicit_empty",
        "adapter_id": "magma_equational.v1",
        "adapter_config": {"max_total_operation_order": 2},
        "formula_grammar": {"kind": "canonical_magma_equations", "max_order": 2},
        "model_or_observation_strata": ({"carrier_size": 2},),
        "pack_arity": 2,
        "collapse_controls": (),
        "visible_evidence_manifest": {"source_refs": []},
        "sealed_evidence_manifest_digest": "sha256:" + "0" * 64,
        "deanchoring_policy": {"cold_after_signature_compilation": True},
        "navigator_contract": {
            "schema": AXIOMPACK_LEAF_WORKBENCH_CONTRACT.schema,
            "fingerprint": AXIOMPACK_LEAF_WORKBENCH_CONTRACT.fingerprint(),
        },
        "query_budget": {"max_finalists": 4},
        "stop_rule": {"freeze_after_finalists": 4},
        "verification_plan": {"finite": [2], "larger_model": [3], "lean": True},
        "codec_versions": {"formula": "magma-postfix-v1"},
        "authority_refs": ("campaign-authority",),
    }


def test_structure_first_compiles_without_model_call_and_cold_view_hides_names():
    brief = FrontierExplorationBrief(
        direction="Explore one anonymous binary operation without seeded laws.",
        source_mode="structure_first",
    )
    blueprint = compile_structure_first_blueprint(brief, _draft())
    assert blueprint.adapter_id == "magma_equational.v1"
    assert navigator_selection_mode(blueprint) == "theory_program"
    assert blueprint.executable_preflight_receipt["adapter_preflight"]["formula_count"] == 46
    cold = cold_navigator_manifest(blueprint)
    assert cold["interpretation_labels_visible"] is False
    assert cold["signature_shape"]["operations"][0]["id"] == "op_0"
    assert "AnonymousMagma" not in str(cold)


def test_blueprint_can_freeze_an_empty_adapter_scoped_task_catalog():
    brief = FrontierExplorationBrief(
        direction="Explore one anonymous binary operation without task calls.",
        source_mode="structure_first",
    )
    draft = _draft()
    draft["navigator_contract"] = {
        **draft["navigator_contract"],
        "theory_task_capability_scope": {
            "schema": THEORY_TASK_CAPABILITY_SCOPE_SCHEMA,
            "adapter_id": "magma_equational.v1",
            "allowed_capability_ids": [],
        },
    }

    blueprint = compile_structure_first_blueprint(brief, draft)

    assert blueprint.executable_preflight_receipt[
        "theory_task_capability_scope"
    ]["allowed_capability_ids"] == []


def test_blueprint_task_scope_rejects_unregistered_capability_ids():
    brief = FrontierExplorationBrief(
        direction="Explore one anonymous binary operation.",
        source_mode="structure_first",
    )
    draft = _draft()
    draft["navigator_contract"] = {
        **draft["navigator_contract"],
        "theory_task_capability_scope": {
            "schema": THEORY_TASK_CAPABILITY_SCOPE_SCHEMA,
            "adapter_id": "magma_equational.v1",
            "allowed_capability_ids": ["invented_task"],
        },
    }

    with pytest.raises(ValueError, match="unregistered IDs: invented_task"):
        compile_structure_first_blueprint(brief, draft)


def test_blueprint_container_types_fail_with_field_name():
    brief = FrontierExplorationBrief("Explore typed structure.", source_mode="structure_first")
    draft = _draft()
    draft["verification_plan"] = [{"kind": "lean"}]
    with pytest.raises(ValueError, match="verification_plan must be an object"):
        compile_structure_first_blueprint(brief, draft)


def test_blueprint_canonicalizes_holdout_strata_to_executable_key():
    brief = FrontierExplorationBrief(
        "Explore typed structure.", source_mode="structure_first"
    )
    draft = _draft()
    draft["verification_plan"] = {
        "holdout_strata": [{"sort_sizes": {"S0": 3}}]
    }

    blueprint = compile_structure_first_blueprint(brief, draft)

    assert "holdout_strata" not in blueprint.verification_plan
    assert blueprint.verification_plan["heldout_strata"] == [
        {"sort_sizes": {"S0": 3}}
    ]


def test_blueprint_rejects_conflicting_holdout_spellings():
    brief = FrontierExplorationBrief(
        "Explore typed structure.", source_mode="structure_first"
    )
    draft = _draft()
    draft["verification_plan"] = {
        "holdout_strata": [{"sort_sizes": {"S0": 3}}],
        "heldout_strata": [{"sort_sizes": {"S0": 4}}],
    }

    with pytest.raises(ValueError, match="holdout and heldout strata disagree"):
        compile_structure_first_blueprint(brief, draft)


def test_blueprint_objective_requires_instruction_and_condition_together():
    brief = FrontierExplorationBrief("Explore typed structure.", source_mode="structure_first")
    draft = _draft()
    draft["stop_rule"] = {
        "user_instruction": "",
        "executable_condition": {"kind": "late_lineage_objective_review"},
    }
    with pytest.raises(ValueError, match="requires both nonempty"):
        compile_structure_first_blueprint(brief, draft)


def test_nl_compiler_canonicalizes_nested_stop_instruction():
    brief = FrontierExplorationBrief(
        "Explore and stop for a persistent law.", source_mode="human_directed"
    )
    draft = _draft()
    instruction = "Stop for a persistent law."
    draft["stop_rule"] = {
        "executable_condition": {
            "kind": "late_lineage_objective_review",
            "user_instruction": instruction,
        }
    }
    blueprint = compile_frontier_blueprint(
        brief,
        draft_fn=lambda _brief: draft,
        semantic_review_fn=lambda _payload: {
            "accepted": True,
            "candidate_law_leakage": False,
            "substrate_constraints_executable": True,
            "rationale": "The condition preserves the requested stopping sentence.",
            "evidence_refs": [brief.brief_id],
        },
        compiler_ref="a",
        reviewer_ref="b",
    )
    assert blueprint.stop_rule == {
        "user_instruction": instruction,
        "executable_condition": {"kind": "late_lineage_objective_review"},
    }


def test_base_axioms_are_parsed_before_semantic_review():
    brief = FrontierExplorationBrief("Explore typed structure.", source_mode="structure_first")
    draft = _draft()
    draft["base_axioms"] = ({
        "schema": "leanmill.axiom_formula.v1",
        "formula": "forall x, x = x",
    },)
    draft["base_theory_status"] = "typed_resolved"
    with pytest.raises(ValueError, match="axiom formula"):
        compile_structure_first_blueprint(brief, draft)


def test_duplicate_base_semantics_fail_before_review():
    brief = FrontierExplorationBrief("Explore typed structure.", source_mode="structure_first")
    draft = _draft()
    x = Term.var("x")
    axiom = AxiomFormula(
        "first_copy",
        Formula.forall((Binder("x", "B"),), Formula.eq(x, x)),
    )
    duplicate = AxiomFormula("second_copy", axiom.formula)
    draft["base_axioms"] = (axiom.to_json(), duplicate.to_json())
    draft["base_theory_status"] = "typed_resolved"
    with pytest.raises(ValueError, match="duplicate semantic formulas"):
        compile_structure_first_blueprint(brief, draft)


def test_cold_view_exposes_base_equations_without_theory_names():
    brief = FrontierExplorationBrief(
        direction="Explore an anonymous binary operation with a frozen base law.",
        source_mode="structure_first",
    )
    draft = _draft()
    x, y, z = Term.var("x"), Term.var("y"), Term.var("z")
    mul = lambda left, right: Term.app("op0", left, right)
    base = AxiomFormula(
        "secret_associativity_label",
        Formula.forall(
            (Binder("x", "S0"), Binder("y", "S0"), Binder("z", "S0")),
            Formula.eq(mul(mul(x, y), z), mul(x, mul(y, z))),
        ),
    )
    draft["base_axioms"] = (base.to_json(),)
    draft["base_theory_status"] = "typed_resolved"

    cold = cold_navigator_manifest(
        compile_structure_first_blueprint(brief, draft)
    )

    assert cold["schema"] == "leanmill.frontier_cold_navigator_manifest.v2"
    assert len(cold["anonymous_base_theory"]) == 1
    rendered = str(cold["anonymous_base_theory"])
    assert "op_0" in rendered
    assert "secret_associativity_label" not in rendered
    assert "AnonymousMagma" not in rendered


def test_requested_adapter_property_becomes_capability_gap_not_new_identity(monkeypatch):
    brief = FrontierExplorationBrief(
        direction="Compare exact-two consequences with a frozen source relation.",
        source_mode="structure_first",
    )
    draft = _draft()
    draft["verification_plan"] = {
        **draft["verification_plan"],
        "single_premise_oracle": {"source_ref": "fixture:relation"},
    }
    monkeypatch.setattr(magma_equational, "CAPABILITIES", {})
    with pytest.raises(AdapterGapRequired) as caught:
        compile_structure_first_blueprint(brief, draft)
    gap = caught.value.gap
    assert gap.gap_kind == "capability_missing"
    assert gap.proposed_adapter_id == "magma_equational.v1"
    assert gap.missing_capabilities == ("single_premise_implication_oracle",)


def test_blueprint_binds_campaign_presentation_size_without_changing_pack_cap():
    brief = FrontierExplorationBrief(
        direction="Explore interactions between exactly two laws.",
        source_mode="structure_first",
    )
    draft = _draft()
    draft["navigator_contract"] = {
        **draft["navigator_contract"],
        "presentation_size": {"minimum": 2, "maximum": 2},
    }
    blueprint = compile_structure_first_blueprint(brief, draft)

    assert blueprint.pack_arity == 2
    assert cold_navigator_manifest(blueprint)["presentation_size"] == {
        "minimum": 2,
        "maximum": 2,
    }

    invalid = _draft()
    invalid["navigator_contract"] = {
        **invalid["navigator_contract"],
        "presentation_size": {"minimum": 2, "maximum": 3},
    }
    with pytest.raises(ValueError, match="within pack_arity"):
        compile_structure_first_blueprint(brief, invalid)

    impossible = _draft()
    impossible["pack_arity"] = 47
    with pytest.raises(ValueError, match="fit the preflighted formula universe"):
        compile_structure_first_blueprint(brief, impossible)


def test_blueprint_binds_host_isolated_lineage_count_without_changing_theory_semantics():
    brief = FrontierExplorationBrief(
        direction="Explore independent anonymous conjectural lineages.",
        source_mode="structure_first",
    )
    draft = _draft()
    draft["navigator_contract"] = {
        **draft["navigator_contract"],
        "selection_mode": "theory_program",
        "host_isolated_lineages": 3,
    }
    blueprint = compile_structure_first_blueprint(brief, draft)

    assert host_isolated_lineage_count(blueprint) == 3
    assert cold_navigator_manifest(blueprint)["host_isolated_lineages"] == 3

    draft["navigator_contract"]["host_isolated_lineages"] = 0
    with pytest.raises(ValueError, match="integer from 1 to 8"):
        compile_structure_first_blueprint(brief, draft)


def test_blueprint_separates_topology_overview_from_candidate_width():
    brief = FrontierExplorationBrief(
        direction="Map pairs while allowing wider agent-authored theories.",
        source_mode="structure_first",
    )
    draft = _draft()
    draft["pack_arity"] = 4
    draft["navigator_contract"] = {
        **draft["navigator_contract"],
        "presentation_size": {"minimum": 2, "maximum": 4},
        "topology_presentation_size": 2,
    }
    blueprint = compile_structure_first_blueprint(brief, draft)
    assert topology_presentation_size(blueprint) == 2
    assert cold_navigator_manifest(blueprint)["topology_presentation_size"] == 2

    draft["navigator_contract"]["topology_presentation_size"] = 5
    with pytest.raises(ValueError, match="within pack_arity"):
        compile_structure_first_blueprint(brief, draft)


def test_nl_compiler_and_reviewer_are_injected_separate_roles():
    brief = FrontierExplorationBrief(
        direction="Explore small anonymous compositional laws.",
        source_mode="human_directed",
        resource_envelope={
            "budget_contract": {"hard_caps": {"context_models": 120}},
        },
    )
    blueprint = compile_frontier_blueprint(
        brief,
        draft_fn=lambda _brief: _draft(),
        semantic_review_fn=lambda _payload: {
            "accepted": True,
            "candidate_law_leakage": False,
            "substrate_constraints_executable": True,
            "rationale": "The typed signature preserves the requested compositional surface.",
            "evidence_refs": [brief.brief_id],
        },
        compiler_ref="compiler-agent-a",
        reviewer_ref="reviewer-agent-b",
    )
    assert blueprint.compiler_receipt["compiler_ref"] == "compiler-agent-a"
    assert blueprint.semantic_review_receipt["reviewer_ref"] == "reviewer-agent-b"
    assert blueprint.authority_refs == (brief.brief_id,)
    assert blueprint.visible_evidence_manifest["brief_id"] == brief.brief_id


def test_nl_compiler_repairs_candidate_width_before_semantic_review():
    brief = FrontierExplorationBrief(
        direction="Explore small anonymous compositional laws.",
        source_mode="human_directed",
        resource_envelope={
            "budget_contract": {"hard_caps": {"context_models": 120}},
        },
    )
    invalid = _draft()
    invalid["pack_arity"] = 2
    invalid["navigator_contract"] = {
        **invalid["navigator_contract"],
        "presentation_size": {"minimum": 1, "maximum": 4},
    }
    fixed = {
        **invalid,
        "navigator_contract": {
            **invalid["navigator_contract"],
            "presentation_size": {"minimum": 1, "maximum": 2},
        },
    }
    compiler_inputs = []
    review_inputs = []

    def compile_call(payload):
        compiler_inputs.append(payload)
        if len(compiler_inputs) == 1:
            return invalid
        assert "within pack_arity" in payload["compiler_feedback"]["error"]
        assert payload["prior_draft"] == invalid
        return fixed

    blueprint = compile_frontier_blueprint(
        brief,
        draft_fn=compile_call,
        semantic_review_fn=lambda payload: review_inputs.append(payload) or {
            "accepted": True,
            "candidate_law_leakage": False,
            "substrate_constraints_executable": True,
            "rationale": "The repaired search width stays inside the compiled pack arity.",
            "evidence_refs": [brief.brief_id],
        },
        compiler_ref="compiler-agent-a",
        reviewer_ref="reviewer-agent-b",
    )

    assert len(compiler_inputs) == 2
    assert len(review_inputs) == 1
    assert review_inputs[0]["executable_preflight"]["ok"] is True
    assert review_inputs[0]["executable_preflight"]["adapter_id"] == (
        "magma_equational.v1"
    )
    assert blueprint.navigator_contract["presentation_size"] == {
        "minimum": 1,
        "maximum": 2,
    }


def test_nl_compiler_context_cap_is_host_budget_owned(monkeypatch):
    brief = FrontierExplorationBrief(
        direction="Explore a finite first-order surface.",
        source_mode="human_directed",
        resource_envelope={
            "budget_contract": {"hard_caps": {"context_models": 120}},
        },
    )
    draft = _draft()
    draft["adapter_config"] = {
        "model_generation": {
            "mode": "smt_exact",
            "max_canonical_models_per_stratum": 2,
            "timeout_ms_per_stratum": 10_000,
        }
    }
    draft["navigator_contract"] = {
        **draft["navigator_contract"],
        "topology_presentation_size": {"minimum": 1, "maximum": 3},
    }
    monkeypatch.setattr(
        "ztare.leanmill.frontier_blueprint_compiler._executable_preflight",
        lambda _brief, row: {
            "ok": True,
            "authority_role": "test-preflight",
            "adapter_preflight": {
                "context_model_budget_upper_bound": (
                    row["adapter_config"]["model_generation"]
                    ["max_canonical_models_per_stratum"] * 6
                ),
            },
        },
    )
    blueprint = compile_frontier_blueprint(
        brief,
        draft_fn=lambda _brief: draft,
        semantic_review_fn=lambda _payload: {
            "accepted": True,
            "candidate_law_leakage": False,
            "substrate_constraints_executable": True,
            "rationale": "The executable surface matches the brief.",
            "evidence_refs": [brief.brief_id],
        },
        compiler_ref="a",
        reviewer_ref="b",
    )
    assert (
        blueprint.adapter_config["model_generation"][
            "max_canonical_models_per_stratum"
        ]
        == 20
    )
    assert "topology_presentation_size" not in blueprint.navigator_contract


def test_cold_compiler_rejects_candidate_law_leakage_and_same_role_review():
    brief = FrontierExplorationBrief(direction="Explore laws.", source_mode="human_directed")
    leaked = _draft()
    leaked["adapter_config"] = {
        **leaked["adapter_config"],
        "candidate_axioms": [{"name": "associativity"}],
    }
    with pytest.raises(ValueError, match="candidate-law leakage"):
        compile_frontier_blueprint(
            brief,
            draft_fn=lambda _brief: leaked,
            semantic_review_fn=lambda _payload: {},
            compiler_ref="a",
            reviewer_ref="b",
        )
    with pytest.raises(ValueError, match="distinct"):
        compile_frontier_blueprint(
            brief,
            draft_fn=lambda _brief: _draft(),
            semantic_review_fn=lambda _payload: {},
            compiler_ref="same",
            reviewer_ref="same",
        )


def test_delegated_nl_stop_must_be_preserved_lowered_and_reviewed():
    instruction = "three structurally distinct theories survive size five"
    brief = FrontierExplorationBrief(
        direction="Explore anonymous laws and stop when " + instruction,
        source_mode="human_directed",
        resource_envelope={
            "budget_preference_compilation": {
                "delegated_stop_instruction": instruction,
            }
        },
    )
    missing = _draft()
    with pytest.raises(ValueError, match="preserve"):
        compile_frontier_blueprint(
            brief,
            draft_fn=lambda _brief: missing,
            semantic_review_fn=lambda _payload: {},
            compiler_ref="a",
            reviewer_ref="b",
        )
    lowered = _draft()
    lowered["stop_rule"] = {
        "user_instruction": instruction,
        "executable_condition": {"kind": "late_lineage_objective_review"},
    }
    with pytest.raises(ValueError, match="approve"):
        compile_frontier_blueprint(
            brief,
            draft_fn=lambda _brief: lowered,
            semantic_review_fn=lambda _payload: {
                "accepted": True,
                "candidate_law_leakage": False,
                "substrate_constraints_executable": True,
                "rationale": "lowering is plausible",
                "evidence_refs": [brief.brief_id],
                "stop_rule_aligned": False,
            },
            compiler_ref="a",
            reviewer_ref="b",
        )
    blueprint = compile_frontier_blueprint(
        brief,
        draft_fn=lambda _brief: lowered,
        semantic_review_fn=lambda _payload: {
            "accepted": True,
            "candidate_law_leakage": False,
            "substrate_constraints_executable": True,
            "rationale": "the stop condition is receipt-observable",
            "evidence_refs": [brief.brief_id],
            "stop_rule_aligned": True,
        },
        compiler_ref="a",
        reviewer_ref="b",
    )
    assert blueprint.stop_rule["user_instruction"] == instruction
