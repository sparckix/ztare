from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

from jsonschema import Draft202012Validator
import pytest

from ztare.leanmill.common import read_json, write_json_atomic
from ztare.leanmill.frontier_interpretation import (
    build_post_freeze_result_packet,
    post_freeze_literature_output_schema,
)
from ztare.leanmill.exploration_budget import ExplorationBudgetLedger, budget_preset
from ztare.leanmill.frontier_agent_runtime import FrontierAgentConfig
from ztare.leanmill.frontier_campaign_runner import run_post_freeze_literature_review
from ztare.leanmill.magma_law_universe import (
    anonymous_magma_signature,
    magma_laws_through_order,
)
from ztare.leanmill.theory_interpretation import (
    compose_theory_interpretation,
    interpretation_isomorphism_failure_state,
)
from ztare.leanmill.theory_ir import content_hash


def test_post_freeze_literature_schema_accepts_source_bound_review() -> None:
    laws = magma_laws_through_order(1)[:3]
    value = {
        "status": "completed",
        "formula_matches": [
            {
                "role": "premise" if index < 2 else "target",
                "formula_id": law.formula_id,
                "formula": law.postfix,
                "match_status": "not_found",
                "external_id": None,
                "source_title": None,
                "source_url": None,
                "confidence": "low",
                "evidence": "No exact match located in the bounded review.",
            }
            for index, law in enumerate(laws)
        ],
        "implication_prior_art": [],
        "recognized_theory_connections": [],
        "novelty_assessment": "not_located_in_bounded_review",
        "mechanism_analysis": {
            "key_idea": "The premises combine two independently checked roles.",
            "recombination": "One role exposes a term and the other rewrites it.",
            "invariant_or_obstruction": "The target is absent from each leave-one-out arm.",
            "premise_roles": [
                {"formula_id": law.formula_id, "role": "premise role"}
                for law in laws[:2]
            ],
            "evidence_refs": ["attribution:test"],
            "transportable_constraint": {
                "constraint_class": "two-component attributed recombination",
                "abstract_form": "two independent generators jointly cross a closure boundary",
                "invariants": [{"name": "arity", "value": "2"}],
                "home_field": "equational algebra",
            },
        },
        "summary": "No exact source match was located.",
        "limitations": ["This was a bounded search."],
        "next_checks": ["Query the project data export directly."],
    }

    Draft202012Validator(post_freeze_literature_output_schema()).validate(value)


def test_post_freeze_literature_schema_tracks_singleton_presentation() -> None:
    schema = post_freeze_literature_output_schema(formula_count=2)
    matches = schema["properties"]["formula_matches"]
    assert matches["minItems"] == 2
    assert matches["maxItems"] == 2


def test_interpretation_ladder_keeps_gloss_bound_to_verifier_and_sources() -> None:
    packet = {
        "packet_sha256": "packet:test",
        "context_hash": "context:test",
        "boundary_result_sha256": "boundary:test",
        "governance_recheck_sha256": "recheck:test",
        "formulas": [
            {"role": "premise", "formula_id": "f1"},
            {"role": "premise", "formula_id": "f2"},
        ],
        "bounded_context": {"complete_carrier_sizes": [2, 3]},
        "unrestricted_lean": {
            "status": "proved_attributed",
            "pack_synergy_status": "proved_exact_two_synergy",
            "logical_premise_ablation": {
                "status": "certified_single_premise_nonimplication"
            },
            "attribution_receipt_sha256": "attribution:test",
            "matched_arms": {"full": "pass", "empty": "fail"},
        },
    }
    literature = {
        "packet_sha256": "packet:test",
        "receipt_sha256": "literature:test",
        "review": {
            "novelty_assessment": "known_implication",
            "formula_matches": [{"formula_id": "f1", "external_id": "E1"}],
            "implication_prior_art": [{"source_url": "https://example.test"}],
            "recognized_theory_connections": ["recorded connection"],
            "mechanism_analysis": {
                "key_idea": "A premise-specific rewrite crosses the target boundary.",
                "recombination": "The premise is instantiated before its result is reused.",
                "invariant_or_obstruction": "The empty arm cannot produce the target.",
                "premise_roles": [
                    {"formula_id": "f1", "role": "rewrite generator"},
                    {"formula_id": "f2", "role": "bridge generator"},
                ],
                "evidence_refs": ["attribution:test"],
                "transportable_constraint": {
                    "constraint_class": "attributed generator reuse",
                    "abstract_form": "instantiate a generator and reuse its image to cross a closure boundary",
                    "invariants": {"uses": 2},
                    "home_field": "equational algebra",
                },
            },
            "summary": "A source-bound summary.",
            "limitations": ["bounded interpretation"],
            "next_checks": ["inspect the explicit proof chain"],
        },
    }

    result = compose_theory_interpretation(packet, literature)

    assert result["status"] == "mapped_to_recorded_knowledge"
    assert result["dependency_characterization"]["lean_status"] == "proved_attributed"
    assert result["external_alignment"]["status"] == "catalogued"
    assert result["external_alignment"]["origin_disposition"] == (
        "catalogued_recovery"
    )
    assert result["external_alignment"]["formula_matches"][0]["external_id"] == "E1"
    assert result["human_gloss"]["authority"] == (
        "source_review_constrained_by_verifier_receipts"
    )
    assert result["mechanism_characterization"]["status"] == "proposed_grounded"
    failure_state = interpretation_isomorphism_failure_state(result)
    assert failure_state == {
        "constraint_class": "attributed generator reuse",
        "abstract_form": (
            "instantiate a generator and reuse its image to cross a closure boundary"
        ),
        "home_field": "equational algebra",
        "uses": 2,
        "presentation_arity": 2,
        "premise_attributed": True,
    }

    proof_dependency_only = deepcopy(packet)
    proof_dependency_only["unrestricted_lean"].pop("pack_synergy_status")
    historical = compose_theory_interpretation(proof_dependency_only, literature)
    assert historical["mechanism_characterization"]["claim_boundary"] == (
        "saved_proof_dependency_only"
    )
    assert interpretation_isomorphism_failure_state(historical) is None

    theory_program_packet = deepcopy(packet)
    theory_program_packet["unrestricted_lean"].update(
        {
            "candidate_kind": "theory_program",
            "program_prediction_status": "kernel_verified_attributed",
            "pack_synergy_status": "not_claimed_theory_program",
        }
    )
    theory_program = compose_theory_interpretation(
        theory_program_packet, literature
    )
    assert theory_program["mechanism_characterization"]["claim_boundary"] == (
        "verified_theory_program_prediction"
    )
    assert interpretation_isomorphism_failure_state(theory_program) is not None

    wrong_premise = deepcopy(literature)
    wrong_premise["review"]["mechanism_analysis"]["premise_roles"][0][
        "formula_id"
    ] = "outside-frozen-packet"
    with pytest.raises(ValueError, match="premise roles"):
        compose_theory_interpretation(packet, wrong_premise)

    wrong_receipt = deepcopy(literature)
    wrong_receipt["review"]["mechanism_analysis"]["evidence_refs"] = [
        "unreceipted-story"
    ]
    with pytest.raises(ValueError, match="evidence outside"):
        compose_theory_interpretation(packet, wrong_receipt)


def test_post_freeze_packet_reveals_only_frozen_query(monkeypatch, tmp_path) -> None:
    laws = magma_laws_through_order(3)
    premises = laws[1:3]
    target = laws[0]
    boundary = {
        "context_hash": "context:test",
        "query_results": [
            {
                "premise_formula_ids": [row.formula_id for row in premises],
                "target_formula_id": target.formula_id,
                "pack_synergy_status": "proved_exact_two_synergy",
                "logical_premise_ablation": {
                    "status": "certified_single_premise_nonimplication"
                },
                "countermodel_searches": [
                    {"carrier_size": 4, "status": "no_countermodel_at_fixed_size", "receipt_sha256": "smt:4"}
                ],
            }
        ],
    }
    boundary["result_sha256"] = content_hash(boundary)
    recheck = {
        "boundary_result_sha256": boundary["result_sha256"],
        "query_rechecks": [
            {
                "premise_formula_ids": [row.formula_id for row in premises],
                "target_formula_id": target.formula_id,
                "recheck": {
                    "status": "proved_attributed",
                    "proof_text": "exact proof",
                    "attribution": {"receipt_sha256": "attribution:test", "arms": {}},
                },
            }
        ],
    }
    recheck["receipt_sha256"] = content_hash(recheck)
    write_json_atomic(tmp_path / "boundary_result.json", boundary)
    write_json_atomic(tmp_path / "boundary_governance_recheck.json", recheck)
    write_json_atomic(tmp_path / "blueprint.json", {"frozen": True})
    monkeypatch.setattr(
        "ztare.leanmill.frontier_interpretation.FrontierTheoryBlueprint.from_json",
        lambda _row: SimpleNamespace(
            adapter_id="magma_equational.v1",
            adapter_config={"max_total_operation_order": 3},
            eigenquestion="Which anonymous magma laws interact?",
            primitive_semantics={"operation_bindings": {"op0": "binary product"}},
            pack_arity=2,
            navigator_contract={},
            model_or_observation_strata=({"carrier_size": 2}, {"carrier_size": 3}),
        ),
    )
    monkeypatch.setattr(
        "ztare.leanmill.frontier_interpretation.load_formal_theory_context",
        lambda _path: SimpleNamespace(
            context_hash="context:test",
            signature=anonymous_magma_signature(),
            formula_profiles=tuple(
                SimpleNamespace(formula_id=row.formula_id, axiom=row.axiom)
                for row in laws
            ),
            base_axioms=(laws[3].axiom,),
        ),
    )

    packet = build_post_freeze_result_packet(tmp_path)

    assert [row["formula_id"] for row in packet["formulas"]] == [
        premises[0].formula_id, premises[1].formula_id, target.formula_id,
    ]
    assert all(row["formula"] for row in packet["formulas"])
    assert packet["schema"] == "leanmill.post_freeze_result_packet.v3"
    assert packet["interpretation_context"]["visibility"] == "post_freeze_only"
    assert packet["interpretation_context"]["base_theory"] == [
        {
            "name": laws[3].axiom.name,
            "semantic_hash": laws[3].axiom.semantic_hash,
            "formula": packet["interpretation_context"]["base_theory"][0]["formula"],
            "formula_ir": laws[3].axiom.formula.to_json(),
        }
    ]
    assert packet["unrestricted_lean"]["status"] == "proved_attributed"
    assert packet["unrestricted_lean"]["pack_synergy_status"] == (
        "proved_exact_two_synergy"
    )
    assert packet["bounded_context"]["targeted_countermodel_searches"][0][
        "sort_sizes"
    ] == {"S0": 4}


def test_post_freeze_packet_accepts_one_premise_within_blueprint_arity(
    monkeypatch, tmp_path
) -> None:
    laws = magma_laws_through_order(3)
    premise, target = laws[1], laws[0]
    boundary = {
        "context_hash": "context:test",
        "query_results": [{
            "premise_formula_ids": [premise.formula_id],
            "target_formula_id": target.formula_id,
            "countermodel_searches": [],
        }],
    }
    boundary["result_sha256"] = content_hash(boundary)
    recheck = {
        "boundary_result_sha256": boundary["result_sha256"],
        "query_rechecks": [{
            "premise_formula_ids": [premise.formula_id],
            "target_formula_id": target.formula_id,
            "recheck": {"status": "proved_attributed", "attribution": {}},
        }],
    }
    recheck["receipt_sha256"] = content_hash(recheck)
    write_json_atomic(tmp_path / "boundary_result.json", boundary)
    write_json_atomic(tmp_path / "boundary_governance_recheck.json", recheck)
    write_json_atomic(tmp_path / "blueprint.json", {"frozen": True})
    monkeypatch.setattr(
        "ztare.leanmill.frontier_interpretation.FrontierTheoryBlueprint.from_json",
        lambda _row: SimpleNamespace(
            adapter_id="magma_equational.v1",
            adapter_config={"max_total_operation_order": 3},
            pack_arity=2,
            navigator_contract={},
            model_or_observation_strata=({"carrier_size": 2}, {"carrier_size": 3}),
        ),
    )
    monkeypatch.setattr(
        "ztare.leanmill.frontier_interpretation.load_formal_theory_context",
        lambda _path: SimpleNamespace(
            context_hash="context:test",
            signature=anonymous_magma_signature(),
            formula_profiles=tuple(
                SimpleNamespace(formula_id=row.formula_id, axiom=row.axiom)
                for row in laws
            ),
        ),
    )

    packet = build_post_freeze_result_packet(tmp_path)

    assert [row["role"] for row in packet["formulas"]] == ["premise", "target"]


def test_interpretation_runner_uses_central_prompt_and_campaign_budget(
    monkeypatch, tmp_path
) -> None:
    packet = {
        "packet_sha256": "packet:test",
        "context_hash": "context:test",
        "boundary_result_sha256": "boundary:test",
        "governance_recheck_sha256": "recheck:test",
        "formulas": [{"role": "premise"}, {"role": "target"}],
    }
    monkeypatch.setattr(
        "ztare.leanmill.frontier_interpretation.build_post_freeze_result_packet",
        lambda _directory: packet,
    )
    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner.load_frontier_campaign_definition",
        lambda _path: SimpleNamespace(),
    )
    seen = []

    class Role:
        def __init__(self) -> None:
            self.config = FrontierAgentConfig()
            self.output_schema = None
            self.call_count = 0

        def __call__(self, prompt):
            seen.append(prompt)
            self.call_count += 1
            return {
                "status": "inconclusive",
                "formula_matches": [],
                "implication_prior_art": [],
                "recognized_theory_connections": [],
                "novelty_assessment": "not_located_in_bounded_review",
                "summary": "bounded review",
                "limitations": ["test"],
                "next_checks": ["test"],
            }

    role = Role()
    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner.frontier_agent_role",
        lambda *_args, **_kwargs: role,
    )
    write_json_atomic(tmp_path / "budget.json", budget_preset("smoke_20m").to_json())

    result = run_post_freeze_literature_review(tmp_path, model="fable")

    assert seen and "FROZEN RESULT PACKET" in seen[0]
    assert result["provider_calls"] == 1
    assert result["reasoning_effort"] == "medium"
    assert result["runtime"] == "claude"
    assert result["model"] == "claude-fable-5"
    assert result["requested_model"] == "fable"
    interpretation = read_json(tmp_path / "theory_interpretation.json", {})
    assert interpretation["packet_sha256"] == "packet:test"

    replay = run_post_freeze_literature_review(tmp_path, model="fable")
    assert replay == result
    assert len(seen) == 1


def test_pre_inference_interpretation_failure_releases_scientific_call_slot(
    monkeypatch, tmp_path
) -> None:
    packet = {
        "packet_sha256": "packet:test",
        "context_hash": "context:test",
        "boundary_result_sha256": "boundary:test",
        "governance_recheck_sha256": "recheck:test",
        "formulas": [{"role": "premise"}, {"role": "target"}],
    }
    monkeypatch.setattr(
        "ztare.leanmill.frontier_interpretation.build_post_freeze_result_packet",
        lambda _directory: packet,
    )
    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner.load_frontier_campaign_definition",
        lambda _path: SimpleNamespace(),
    )

    class Role:
        config = FrontierAgentConfig()
        output_schema = None
        calls = []
        call_count = 1
        provider_call_count = 0

        def __call__(self, _prompt):
            raise RuntimeError("request rejected before inference")

    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner.frontier_agent_role",
        lambda *_args, **_kwargs: Role(),
    )
    budget = budget_preset("smoke_20m")
    write_json_atomic(tmp_path / "budget.json", budget.to_json())

    with pytest.raises(RuntimeError, match="before inference"):
        run_post_freeze_literature_review(tmp_path)

    ledger = ExplorationBudgetLedger(
        tmp_path / "budget.events.jsonl", budget, attempt_id=tmp_path.name
    )
    state = ledger.state()
    assert state["usage"]["provider_calls"] == 0
    assert state["usage"]["agent_turns"] == 0
    assert state["reservations"] == {}


def test_charged_interpretation_failure_is_receipted_as_inconclusive(
    monkeypatch, tmp_path
) -> None:
    packet = {
        "packet_sha256": "packet:test",
        "context_hash": "context:test",
        "boundary_result_sha256": "boundary:test",
        "governance_recheck_sha256": "recheck:test",
        "formulas": [
            {"role": "premise", "formula_id": "formula:p", "formula": "P"},
            {"role": "target", "formula_id": "formula:t", "formula": "T"},
        ],
    }
    monkeypatch.setattr(
        "ztare.leanmill.frontier_interpretation.build_post_freeze_result_packet",
        lambda _directory: packet,
    )
    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner.load_frontier_campaign_definition",
        lambda _path: SimpleNamespace(),
    )

    class Role:
        config = FrontierAgentConfig()
        output_schema = None
        calls = []
        provider_call_count = 0

        def __call__(self, _prompt):
            self.calls.append({"provider_call_charge": 1})
            self.provider_call_count = 1
            raise RuntimeError("provider timed out after inference")

    role = Role()
    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner.frontier_agent_role",
        lambda *_args, **_kwargs: role,
    )
    write_json_atomic(tmp_path / "budget.json", budget_preset("smoke_20m").to_json())

    result = run_post_freeze_literature_review(tmp_path)

    assert result["status"] == "interpretation_inconclusive"
    assert result["review"]["novelty_assessment"] == "review_unavailable"
    assert (tmp_path / "theory_interpretation.json").is_file()
