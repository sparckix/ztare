from __future__ import annotations

import pytest

from ztare.leanmill.adapter_forge import AdapterGapRequired
from ztare.leanmill.adapters import magma_equational
from ztare.leanmill.axiompack_leaf_workbench import AXIOMPACK_LEAF_WORKBENCH_CONTRACT
from ztare.leanmill.frontier_blueprint import (
    FrontierExplorationBrief,
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
    )
    blueprint = compile_frontier_blueprint(
        brief,
        draft_fn=lambda _brief: _draft(),
        semantic_review_fn=lambda _payload: {
            "accepted": True,
            "candidate_law_leakage": False,
            "rationale": "The typed signature preserves the requested compositional surface.",
            "evidence_refs": [brief.brief_id],
        },
        compiler_ref="compiler-agent-a",
        reviewer_ref="reviewer-agent-b",
    )
    assert blueprint.compiler_receipt["compiler_ref"] == "compiler-agent-a"
    assert blueprint.semantic_review_receipt["reviewer_ref"] == "reviewer-agent-b"


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
        "executable_condition": {
            "kind": "distinct_survivor_count",
            "minimum": 3,
            "required_carrier_size": 5,
        },
    }
    with pytest.raises(ValueError, match="approve"):
        compile_frontier_blueprint(
            brief,
            draft_fn=lambda _brief: lowered,
            semantic_review_fn=lambda _payload: {
                "accepted": True,
                "candidate_law_leakage": False,
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
            "rationale": "the stop condition is receipt-observable",
            "evidence_refs": [brief.brief_id],
            "stop_rule_aligned": True,
        },
        compiler_ref="a",
        reviewer_ref="b",
    )
    assert blueprint.stop_rule["user_instruction"] == instruction
