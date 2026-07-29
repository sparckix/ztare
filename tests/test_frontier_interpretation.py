from __future__ import annotations

from copy import deepcopy
import json
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
from ztare.leanmill.finite_model import FiniteModel
from ztare.leanmill.frontier_campaign_runner import (
    _active_objective_finalists,
    consume_post_freeze_interpretation_for_search,
    deliver_post_freeze_mechanism_feedback,
    next_frontier_campaign_action,
    run_post_freeze_literature_review,
)
from ztare.common.schema_routes import audit_project_schema_routes
from ztare.common.target_predicate import TargetPredicateContract
from ztare.leanmill.magma_law_universe import (
    anonymous_magma_signature,
    magma_laws_through_order,
)
from ztare.leanmill.theory_interpretation import (
    compose_theory_interpretation,
    interpretation_isomorphism_failure_state,
)
from ztare.leanmill.theory_lineage_synthesis import lineage_synthesis_input
from ztare.leanmill.theory_program import TheoryProgram
from ztare.leanmill.theory_ir import (
    Binder,
    Formula,
    Term,
    content_hash,
    operation_argument_permutation_variants,
    render_formula_plain,
)


def _temporal_search_coverage(
    *,
    review_as_of_date: str = "2026-07-16",
    problem_status: str = "not_an_open_problem",
    unavailable_leg: str | None = None,
) -> dict:
    leg_ids = (
        "formula_and_coordinate",
        "problem_statement",
        "citation_backward",
        "citation_forward",
        "latest_version",
    )
    source_url = "https://example.test/current-primary-source"
    status_has_source = problem_status in {"resolved", "open_as_of_cutoff"}
    return {
        "review_as_of_date": review_as_of_date,
        "anchor_sources": ([{
            "source_title": "Current primary source",
            "source_url": source_url,
            "source_date": "2026-05-07",
            "latest_revision_date": "2026-05-07",
            "relationship": "current status evidence",
        }] if status_has_source else []),
        "search_legs": [
            {
                "leg_id": leg_id,
                "status": "unavailable" if leg_id == unavailable_leg else "completed",
                "queries": [f"query:{leg_id}"],
                "evidence_urls": ([source_url] if status_has_source else []),
                "limitation": (
                    "citation graph unavailable" if leg_id == unavailable_leg else None
                ),
            }
            for leg_id in leg_ids
        ],
        "problem_status": problem_status,
        "status_evidence_urls": [source_url] if status_has_source else [],
        "latest_relevant_source_date": (
            "2026-05-07" if status_has_source else None
        ),
        "limitations": [],
    }


def test_operation_coordinate_variants_are_typed_and_executable() -> None:
    signature = anonymous_magma_signature()
    x, y = Term.var("x"), Term.var("y")
    formula = Formula.forall(
        (Binder("x", "S0"), Binder("y", "S0")),
        Formula.eq(Term.app("op0", x, y), x),
    )

    variants = operation_argument_permutation_variants(signature, formula)

    assert len(variants) == 1
    mapping, transformed = variants[0]
    assert mapping == (("op0", (1, 0)),)
    assert render_formula_plain(transformed) == (
        "forall x:S0, y:S0, op0(y, x) = x"
    )


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
                "equivalence_kind": "none",
                "coordinate_variant_id": None,
            }
            for index, law in enumerate(laws)
        ],
        "implication_prior_art": [],
        "recognized_theory_connections": [],
        "finite_witness_matches": [],
        "novelty_assessment": "not_located_in_bounded_review",
        "search_coverage": _temporal_search_coverage(),
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

    schema = post_freeze_literature_output_schema(
        premise_formula_ids=[row.formula_id for row in laws[:2]]
    )
    assert "uniqueItems" not in json.dumps(schema)
    Draft202012Validator(schema).validate(value)

    wrong = deepcopy(value)
    wrong["mechanism_analysis"]["premise_roles"][0]["formula_id"] = "base:ambient"
    assert list(Draft202012Validator(schema).iter_errors(wrong))


def test_post_freeze_literature_schema_tracks_singleton_presentation() -> None:
    schema = post_freeze_literature_output_schema(formula_count=2)
    matches = schema["properties"]["formula_matches"]
    assert matches["minItems"] == 2
    assert matches["maxItems"] == 2


def test_v5_interpretation_requires_currentness_before_unmapped_status() -> None:
    packet = {
        "schema": "leanmill.post_freeze_result_packet.v5",
        "packet_sha256": "packet:test",
        "context_hash": "context:test",
        "formulas": [
            {"role": "premise", "formula_id": "f1"},
            {"role": "target", "formula_id": "f2"},
        ],
        "structural_source_search": {
            "operation_coordinate_variants": [],
            "finite_witnesses": [],
        },
        "unrestricted_lean": {"status": "proved_attributed"},
        "literature_search_protocol": {
            "review_as_of_date": "2026-07-16",
            "required_search_legs": [
                "formula_and_coordinate",
                "problem_statement",
                "citation_backward",
                "citation_forward",
                "latest_version",
            ],
        },
    }

    def literature(novelty: str, coverage: dict) -> dict:
        core = {
            "schema": "leanmill.post_freeze_interpretation.v1",
            "packet_sha256": "packet:test",
            "finite_witness_host_checks": [],
            "review": {
                "novelty_assessment": novelty,
                "formula_matches": [
                    {
                        "formula_id": formula_id,
                        "match_status": "not_found",
                        "equivalence_kind": "none",
                        "coordinate_variant_id": None,
                    }
                    for formula_id in ("f1", "f2")
                ],
                "implication_prior_art": [],
                "recognized_theory_connections": [],
                "finite_witness_matches": [],
                "search_coverage": coverage,
                "mechanism_analysis": {},
                "summary": "test",
                "limitations": ["bounded"],
                "next_checks": ["none"],
            },
        }
        return {**core, "receipt_sha256": content_hash(core)}

    incomplete = literature(
        "not_located_in_bounded_review",
        _temporal_search_coverage(unavailable_leg="citation_forward"),
    )
    with pytest.raises(ValueError, match="complete temporal search legs"):
        compose_theory_interpretation(packet, incomplete)

    stale_open_claim = literature(
        "not_located_in_bounded_review",
        _temporal_search_coverage(problem_status="resolved"),
    )
    with pytest.raises(ValueError, match="resolved prior art"):
        compose_theory_interpretation(packet, stale_open_claim)

    mapped = literature(
        "known_implication",
        _temporal_search_coverage(problem_status="resolved"),
    )
    result = compose_theory_interpretation(packet, mapped)
    assert result["external_alignment"]["search_coverage"]["problem_status"] == (
        "resolved"
    )


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


def _write_post_freeze_objective_run(monkeypatch, directory) -> dict:
    objective = {
        "schema": "leanmill.frontier_objective_contract.v1",
        "instruction": "Find a representation that predicts beyond the frozen chart.",
        "review_stage": "post_lineage_freeze_pre_boundary",
        "authority": "independent_leaf_choice_host_receipt_validation",
    }
    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner.FrontierTheoryBlueprint.from_json",
        lambda _row: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner.frontier_objective_contract",
        lambda _blueprint: objective,
    )
    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner.host_isolated_lineage_count",
        lambda _blueprint: 2,
    )
    write_json_atomic(directory / "blueprint.json", {"frozen": True})
    program_zero = TheoryProgram(
        campaign_id="campaign:test",
        lineage_id="lineage:zero",
        context_hash="context:test",
        context_epoch=0,
        presentation_formula_ids=("formula:zero",),
        prediction_formula_ids=("formula:target:zero",),
        selection_receipt_id="selection:zero",
    )
    program_zero_refined = TheoryProgram(
        campaign_id="campaign:test",
        lineage_id="lineage:zero",
        context_hash="context:test",
        context_epoch=0,
        presentation_formula_ids=("formula:zero-refined",),
        prediction_formula_ids=("formula:target:zero-refined",),
        selection_receipt_id="selection:zero-refined",
    )
    program = TheoryProgram(
        campaign_id="campaign:test",
        lineage_id="lineage:one",
        context_hash="context:test",
        context_epoch=0,
        presentation_formula_ids=("formula:p",),
        prediction_formula_ids=("formula:target",),
        selection_receipt_id="selection:one",
    )
    run_core = {
        "status": "frontier_candidates_frozen_awaiting_boundary_approval",
        "context_hash": "context:test",
        "context_summary": {"context_epoch": 0},
        "navigation": {
            "context_hash": "context:test",
            "context_epoch": 0,
            "search_wave": 2,
            "finalists": [
                {
                    "node_id": "node:zero",
                    "theory_program_id": program_zero.program_id,
                    "theory_program": program_zero.to_json(),
                },
                {
                    "node_id": "node:one",
                    "theory_program_id": program.program_id,
                    "theory_program": program.to_json(),
                }
            ],
            "objective_survivors": [{
                "node_id": "node:zero-refined",
                "theory_program_id": program_zero_refined.program_id,
                "theory_program": program_zero_refined.to_json(),
            }],
            "objective_review_history": [{
                "schema": "leanmill.boundary_search_feedback.v1",
                "receipt_sha256": "feedback:zero",
                "program_ids": [program_zero.program_id],
                "prediction_outcomes": [{
                    "program_ids": [program_zero.program_id],
                    "target_formula_id": "formula:target:zero",
                    "status": "pending",
                }],
            }],
        },
    }
    write_json_atomic(
        directory / "run.json",
        {**run_core, "run_digest": content_hash(run_core)},
    )
    write_json_atomic(directory / "boundary_result.json", {"result": "frozen"})
    return objective


def _verified_finite_recurrence_check() -> dict:
    equivalence_core = {
        "schema": "leanmill.finite_operation_equivalence.v1",
        "status": "completed",
        "relation": "mutual_term_equivalent",
        "scope": "finite_witness_only",
        "carrier_size": 3,
        "operation_arity": 3,
        "max_term_depth": 2,
    }
    equivalence = {
        **equivalence_core,
        "receipt_sha256": content_hash(equivalence_core),
    }
    check_core = {
        "schema": "leanmill.finite_witness_source_match_check.v1",
        "packet_sha256": "packet:test",
        "context_hash": "context:test",
        "proposal_sha256": "proposal:test",
        "candidate_model_id": "model:hidden",
        "source_url": "https://example.test/hidden-source",
        "claimed_relation": "mutual_term_equivalent",
        "status": "verified",
        "computed_relation": "mutual_term_equivalent",
        "equivalence_receipt": equivalence,
        "reason": None,
        "authority": "deterministic_host_table_replay",
        "claim_boundary": "one finite algebra pair only",
    }
    return {**check_core, "receipt_sha256": content_hash(check_core)}


def test_verified_recurrence_routes_typed_residual_without_mechanism(
    monkeypatch, tmp_path
) -> None:
    objective = _write_post_freeze_objective_run(monkeypatch, tmp_path)
    check = _verified_finite_recurrence_check()
    literature_core = {
        "schema": "leanmill.post_freeze_interpretation.v1",
        "packet_sha256": "packet:test",
        "finite_witness_host_checks": [check],
        "review": {
            "novelty_assessment": "not_located_in_bounded_review",
            "implication_prior_art": [
                {
                    "source_title": "Hidden Source Title",
                    "source_url": "https://example.test/hidden-source",
                }
            ],
            "formula_matches": [],
            "recognized_theory_connections": [],
        },
    }
    literature = {
        **literature_core,
        "receipt_sha256": content_hash(literature_core),
    }
    interpretation_core = {
        "schema": "leanmill.theory_interpretation.v1",
        "status": "mechanically_characterized_unmapped",
        "context_hash": "context:test",
        "packet_sha256": "packet:test",
        "literature_receipt_sha256": literature["receipt_sha256"],
        "operational_characterization": {
            "formulas": [
                {"role": "premise", "formula_id": "formula:p"},
                {"role": "target", "formula_id": "formula:target"},
            ]
        },
        "mechanism_characterization": {"status": "not_emitted"},
        "external_alignment": {
            "status": "unresolved",
            "origin_disposition": "recorded_components_unmapped_recombination",
            "origin_claim_boundary": "unmapped never certifies novelty",
            "structural_recurrence": {
                "status": "verified_finite_recurrence",
                "checks": [check],
                "claim_boundary": (
                    "finite-algebra recurrence only; does not establish theory, "
                    "variety, implication, or universal-source equivalence"
                ),
            },
        },
    }
    interpretation = {
        **interpretation_core,
        "receipt_sha256": content_hash(interpretation_core),
    }

    feedback = consume_post_freeze_interpretation_for_search(
        tmp_path, literature, interpretation
    )

    assert feedback is not None
    assert feedback["schema"] == "leanmill.post_freeze_research_disposition.v1"
    assert feedback["mechanism_projection"] is None
    disposition = feedback["research_disposition"]
    assert disposition["typed_residual"] == (
        "separate_unmapped_implication_from_recurrent_finite_structure"
    )
    assert disposition["outer_objective_credit"] == (
        "withheld_pending_distinct_residual"
    )
    relation = disposition["structural_recurrence"]["verified_relations"][0]
    assert relation["relation"] == "mutual_term_equivalent"
    rendered = json.dumps(feedback, sort_keys=True)
    assert "Hidden Source Title" not in rendered
    assert "https://example.test/hidden-source" not in rendered
    assert "model:hidden" not in rendered
    assert next_frontier_campaign_action(tmp_path) == "resume_navigation"
    assert consume_post_freeze_interpretation_for_search(
        tmp_path, literature, interpretation
    ) == feedback
    updated = read_json(tmp_path / "run.json", {})
    assert deliver_post_freeze_mechanism_feedback(
        tmp_path, updated, context_hash="context:test"
    ) == feedback
    synthesis = lineage_synthesis_input(
        {
            "context_hash": "context:test",
            "context_epoch": 0,
            "post_freeze_research_disposition": feedback,
        },
        objective_contract=objective,
    )
    assert synthesis["post_freeze_research_disposition"] == feedback
    route = next(
        row for row in audit_project_schema_routes(tmp_path)["routes"]
        if row["route_id"]
        == "post_freeze_research_disposition_to_theory_navigation.v1"
    )
    assert route["unconsumed_count"] == 0


def test_catalogued_alignment_routes_distinct_residual_without_source_leak(
    monkeypatch, tmp_path
) -> None:
    _write_post_freeze_objective_run(monkeypatch, tmp_path)
    literature_core = {
        "schema": "leanmill.post_freeze_interpretation.v1",
        "packet_sha256": "packet:test",
        "finite_witness_host_checks": [],
        "review": {
            "novelty_assessment": "known_implication",
            "implication_prior_art": [
                {
                    "source_title": "Hidden Catalogue",
                    "source_url": "https://example.test/catalogue",
                }
            ],
            "formula_matches": [],
            "recognized_theory_connections": [],
        },
    }
    literature = {
        **literature_core,
        "receipt_sha256": content_hash(literature_core),
    }
    interpretation_core = {
        "schema": "leanmill.theory_interpretation.v1",
        "status": "mapped_to_recorded_knowledge",
        "context_hash": "context:test",
        "packet_sha256": "packet:test",
        "literature_receipt_sha256": literature["receipt_sha256"],
        "operational_characterization": {
            "formulas": [
                {"role": "premise", "formula_id": "formula:p"},
                {"role": "target", "formula_id": "formula:target"},
            ]
        },
        "mechanism_characterization": {"status": "not_emitted"},
        "external_alignment": {
            "status": "catalogued",
            "origin_disposition": "catalogued_recovery",
            "origin_claim_boundary": "source-bound classification",
            "structural_recurrence": {
                "status": "none_verified",
                "checks": [],
                "claim_boundary": "no finite relation asserted",
            },
        },
    }
    interpretation = {
        **interpretation_core,
        "receipt_sha256": content_hash(interpretation_core),
    }

    feedback = consume_post_freeze_interpretation_for_search(
        tmp_path, literature, interpretation
    )

    assert feedback is not None
    assert feedback["research_disposition"]["typed_residual"] == (
        "distinguish_from_catalogued_result_or_change_objective"
    )
    assert "Hidden Catalogue" not in json.dumps(feedback, sort_keys=True)


def test_unverified_recurrence_cannot_resume_without_mechanism(tmp_path) -> None:
    literature_core = {
        "schema": "leanmill.post_freeze_interpretation.v1",
        "packet_sha256": "packet:test",
        "finite_witness_host_checks": [],
        "review": {
            "novelty_assessment": "not_located_in_bounded_review",
            "implication_prior_art": [],
            "formula_matches": [],
            "recognized_theory_connections": [],
        },
    }
    literature = {
        **literature_core,
        "receipt_sha256": content_hash(literature_core),
    }
    interpretation_core = {
        "schema": "leanmill.theory_interpretation.v1",
        "status": "inconclusive",
        "context_hash": "context:test",
        "packet_sha256": "packet:test",
        "literature_receipt_sha256": literature["receipt_sha256"],
        "mechanism_characterization": {"status": "not_emitted"},
        "external_alignment": {
            "status": "unresolved",
            "origin_disposition": "unmapped_candidate",
            "origin_claim_boundary": "unmapped never certifies novelty",
            "structural_recurrence": {
                "status": "none_verified",
                "checks": [],
                "claim_boundary": "no finite relation asserted",
            },
        },
    }
    interpretation = {
        **interpretation_core,
        "receipt_sha256": content_hash(interpretation_core),
    }

    assert consume_post_freeze_interpretation_for_search(
        tmp_path, literature, interpretation
    ) is None


def test_post_freeze_mechanism_reaches_existing_navigation_without_provider(
    monkeypatch, tmp_path
) -> None:
    objective = {
        "schema": "leanmill.frontier_objective_contract.v1",
        "instruction": "Find a representation that predicts beyond the frozen chart.",
        "review_stage": "post_lineage_freeze_pre_boundary",
        "authority": "independent_leaf_choice_host_receipt_validation",
    }
    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner.FrontierTheoryBlueprint.from_json",
        lambda _row: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner.frontier_objective_contract",
        lambda _blueprint: objective,
    )
    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner.host_isolated_lineage_count",
        lambda _blueprint: 2,
    )
    write_json_atomic(tmp_path / "blueprint.json", {"frozen": True})
    program_zero = TheoryProgram(
        campaign_id="campaign:test",
        lineage_id="lineage:zero",
        context_hash="context:test",
        context_epoch=0,
        presentation_formula_ids=("formula:zero",),
        prediction_formula_ids=("formula:target:zero",),
        selection_receipt_id="selection:zero",
    )
    program_zero_refined = TheoryProgram(
        campaign_id="campaign:test",
        lineage_id="lineage:zero",
        context_hash="context:test",
        context_epoch=0,
        presentation_formula_ids=("formula:zero-refined",),
        prediction_formula_ids=("formula:target:zero-refined",),
        selection_receipt_id="selection:zero-refined",
    )
    program = TheoryProgram(
        campaign_id="campaign:test",
        lineage_id="lineage:one",
        context_hash="context:test",
        context_epoch=0,
        presentation_formula_ids=("formula:p",),
        prediction_formula_ids=("formula:target",),
        selection_receipt_id="selection:one",
    )
    run_core = {
        "status": "frontier_candidates_frozen_awaiting_boundary_approval",
        "context_hash": "context:test",
        "context_summary": {"context_epoch": 0},
        "navigation": {
            "context_hash": "context:test",
            "context_epoch": 0,
            "search_wave": 2,
            "finalists": [
                {
                    "node_id": "node:zero",
                    "theory_program_id": program_zero.program_id,
                    "theory_program": program_zero.to_json(),
                },
                {
                    "node_id": "node:one",
                    "theory_program_id": program.program_id,
                    "theory_program": program.to_json(),
                }
            ],
            "objective_survivors": [{
                "node_id": "node:zero-refined",
                "theory_program_id": program_zero_refined.program_id,
                "theory_program": program_zero_refined.to_json(),
            }],
            "objective_review_history": [{
                "schema": "leanmill.boundary_search_feedback.v1",
                "receipt_sha256": "feedback:zero",
                "program_ids": [program_zero.program_id],
                "prediction_outcomes": [{
                    "program_ids": [program_zero.program_id],
                    "target_formula_id": "formula:target:zero",
                    "status": "pending",
                }],
            }],
        },
    }
    run = {**run_core, "run_digest": content_hash(run_core)}
    write_json_atomic(tmp_path / "run.json", run)
    write_json_atomic(tmp_path / "boundary_result.json", {"result": "frozen"})
    write_json_atomic(tmp_path / "boundary_completion.json", {"status": "done"})

    literature_core = {
        "schema": "leanmill.post_freeze_interpretation.v1",
        "packet_sha256": "packet:test",
        "review": {"status": "completed"},
    }
    literature = {
        **literature_core,
        "receipt_sha256": content_hash(literature_core),
    }
    interpretation_core = {
        "schema": "leanmill.theory_interpretation.v1",
        "status": "mechanically_characterized_unmapped",
        "context_hash": "context:test",
        "packet_sha256": "packet:test",
        "literature_receipt_sha256": literature["receipt_sha256"],
        "operational_characterization": {
            "formulas": [
                {"role": "premise", "formula_id": "formula:p"},
                {"role": "target", "formula_id": "formula:target"},
            ]
        },
        "mechanism_characterization": {
            "status": "proposed_grounded",
            "premise_roles": [
                {"formula_id": "formula:p", "role": "commuting action"}
            ],
            "evidence_refs": ["receipt:kernel"],
            "transportable_constraint": {
                "constraint_class": "commuting action factorization",
                "abstract_form": "factor a family of endomorphisms through its orbit quotient",
                "invariants": {"commutes": True},
                "home_field": "hidden-from-successor",
            },
            "claim_boundary": "verified_theory_program_prediction",
            "transport_authority": "advisory_pending_destination_replay",
        },
    }
    interpretation = {
        **interpretation_core,
        "receipt_sha256": content_hash(interpretation_core),
    }

    feedback = consume_post_freeze_interpretation_for_search(
        tmp_path, literature, interpretation
    )

    assert feedback is not None
    assert feedback["lineage_ids"] == ["lineage:one"]
    assert feedback["program_ids"] == [program.program_id]
    assert feedback["reviewed_presentation_formula_ids"] == ["formula:p"]
    assert feedback["mechanism_projection"]["abstract_form"].startswith("factor")
    assert "home_field" not in feedback["mechanism_projection"]
    assert not (tmp_path / "boundary_result.json").exists()
    assert (tmp_path / "boundary_result.post-freeze-wave-002.json").is_file()
    updated = read_json(tmp_path / "run.json", {})
    assert updated["status"] == "frontier_objective_unmet"
    assert updated["navigation"]["objective_review_history"][-1] == feedback
    assert [
        row["theory_program_id"]
        for row in _active_objective_finalists(updated["navigation"])
    ] == [program_zero_refined.program_id, program.program_id]
    assert consume_post_freeze_interpretation_for_search(
        tmp_path, literature, interpretation
    ) == feedback
    delivered = deliver_post_freeze_mechanism_feedback(
        tmp_path, updated, context_hash="context:test"
    )
    assert delivered == feedback
    route = next(
        row for row in audit_project_schema_routes(tmp_path)["routes"]
        if row["route_id"] == "post_freeze_mechanism_to_theory_navigation.v1"
    )
    assert route["unconsumed_count"] == 0


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
    target_predicate = TargetPredicateContract(
        contract_id="fixture:post-freeze-target",
        owner="fixture objective epoch",
        lifecycle_scope="context:test",
        context_hash="context:test",
        adapter_id="magma_equational.v1",
        evaluator_capability="fixture_target_evaluator",
        predicate_ir={"kind": "fixture_derived_consequence"},
        input_schema={"type": "object", "minProperties": 1},
    )
    write_json_atomic(
        tmp_path / "target_predicate_contract.json",
        target_predicate.to_dict(),
    )
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
    witness_model = FiniteModel(
        sort_sizes=(("S0", 2),),
        operations=(("op0", (0, 1, 1, 0)),),
    )
    witness_record = SimpleNamespace(
        model_id="model:witness",
        stratum_id="carrier_size:2",
        model=witness_model,
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
            extent_models=lambda _premise_ids: (witness_record,),
        ),
    )

    packet = build_post_freeze_result_packet(tmp_path)

    assert [row["formula_id"] for row in packet["formulas"]] == [
        premises[0].formula_id, premises[1].formula_id, target.formula_id,
    ]
    assert all(row["formula"] for row in packet["formulas"])
    assert packet["schema"] == "leanmill.post_freeze_result_packet.v5"
    assert packet["interpretation_context"]["visibility"] == "post_freeze_only"
    assert packet["target_predicate_contract"] == {
        **target_predicate.to_dict(),
        "contract_sha256": target_predicate.sha256,
    }
    assert packet["structural_source_search"]["coordinate_variant_receipt"][
        "status"
    ] == "available"
    assert packet["structural_source_search"]["operation_coordinate_variants"]
    assert packet["structural_source_search"]["finite_witness_receipt"][
        "status"
    ] == "complete_extent"
    assert packet["structural_source_search"]["finite_witnesses"][0][
        "candidate_model_id"
    ] == "model:witness"
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


def test_post_freeze_packet_accepts_receipted_boundary_refutation(
    monkeypatch, tmp_path
) -> None:
    laws = magma_laws_through_order(3)
    premise, target = laws[1], laws[0]
    boundary = {
        "context_hash": "context:test",
        "query_results": [{
            "premise_formula_ids": [premise.formula_id],
            "target_formula_id": target.formula_id,
            "candidate_kind": "theory_program",
            "program_prediction_status": "refuted_by_larger_model",
            "countermodel_searches": [{
                "carrier_size": 4,
                "status": "countermodel_found",
                "host_replay_status": "passed",
                "witness": {"carrier_size": 4, "operations": {}},
                "receipt_sha256": "smt:countermodel",
            }],
        }],
    }
    boundary["result_sha256"] = content_hash(boundary)
    write_json_atomic(tmp_path / "boundary_result.json", boundary)
    write_json_atomic(tmp_path / "blueprint.json", {"frozen": True})
    monkeypatch.setattr(
        "ztare.leanmill.frontier_interpretation.FrontierTheoryBlueprint.from_json",
        lambda _row: SimpleNamespace(
            adapter_id="magma_equational.v1",
            adapter_config={},
            pack_arity=2,
            navigator_contract={},
            model_or_observation_strata=({"carrier_size": 3},),
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
            base_axioms=(),
        ),
    )

    packet = build_post_freeze_result_packet(tmp_path)

    assert packet["governance_recheck_sha256"] is None
    assert packet["query_selection"]["evidence_mode"] == "boundary_disposition"
    assert packet["unrestricted_lean"]["status"] == "refuted_by_larger_model"
    assert packet["bounded_context"]["targeted_countermodel_searches"][0][
        "witness"
    ]["carrier_size"] == 4


def test_interpretation_runner_uses_central_prompt_and_campaign_budget(
    monkeypatch, tmp_path
) -> None:
    packet = {
        "packet_sha256": "packet:test",
        "context_hash": "context:test",
        "boundary_result_sha256": "boundary:test",
        "governance_recheck_sha256": "recheck:test",
        "formulas": [
            {"role": "premise", "formula_id": "formula:premise"},
            {"role": "target", "formula_id": "formula:target"},
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
        "formulas": [
            {"role": "premise", "formula_id": "formula:premise"},
            {"role": "target", "formula_id": "formula:target"},
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
