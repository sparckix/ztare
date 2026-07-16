from __future__ import annotations

import re

import pytest

from ztare.common.schema_routes import audit_project_schema_routes
from ztare.leanmill.adapter_forge import (
    AdapterGap,
    AdapterGapRequired,
    execute_adapter_forge_attempt,
    host_capability_conformance,
    render_adapter_forge_prompt,
    run_adapter_forge,
    stage_adapter_forge_workspace,
)
from ztare.leanmill.common import read_json, write_json_atomic, write_text_atomic
from ztare.leanmill.exploration_budget import budget_preset
from ztare.leanmill.explore_axiom_space import explore_axiom_space
from ztare.leanmill.finite_model import FiniteModel, evaluate_axiom
from ztare.leanmill.finite_theory_context import load_formal_theory_context
from ztare.leanmill.formal_verification_provider import generate_keypair
from ztare.leanmill.frontier_campaign import sign_frontier_campaign
from ztare.leanmill.frontier_campaign_definition import FrontierCampaignDefinition
from ztare.leanmill.frontier_blueprint import FrontierExplorationBrief
from ztare.leanmill.frontier_blueprint_compiler import compile_frontier_blueprint
from ztare.leanmill.frontier_campaign_runner import (
    advance_frontier_language_expansion,
)
from ztare.leanmill.generative_representation import (
    CANDIDATE_SCHEMA,
    ISOMORPHISM_POLICY,
)
from ztare.leanmill.magma_law_universe import anonymous_magma_signature
from ztare.leanmill.theory_ir import OperationSymbol, TheorySignature
from ztare.leanmill.theory_navigator import run_interactive_theory_navigator
from ztare.leanmill.theory_adapter_registry import registered_theory_adapter_ids
from ztare.leanmill.theory_adapter_registry import materialize_theory_adapter_capability
from ztare.leanmill.theory_ir import content_hash

from test_explore_axiom_space import _draft


def _unknown_draft():
    return {
        "mode": "anonymous_signature_census",
        "eigenquestion": "Which regions form?",
        "signature": anonymous_magma_signature().to_json(),
        "primitive_semantics": {
            "operation_bindings": {"op0": "custom executable binary law"},
            "relation_bindings": {},
        },
        "base_axioms": (), "base_theory_status": "explicit_empty",
        "adapter_id": "unbuilt_custom_substrate.v1",
        "adapter_config": {}, "formula_grammar": {"kind": "bounded"},
        "model_or_observation_strata": ({"carrier_size": 2},),
        "pack_arity": 2, "collapse_controls": (),
        "visible_evidence_manifest": {},
        "sealed_evidence_manifest_digest": "sha256:" + "0" * 64,
        "deanchoring_policy": {"cold": True}, "navigator_contract": {},
        "query_budget": {}, "stop_rule": {}, "verification_plan": {},
        "codec_versions": {}, "authority_refs": ("authority",),
    }


def test_unknown_adapter_becomes_typed_gap_not_guessed_campaign():
    brief = FrontierExplorationBrief(
        direction="Explore a custom finite substrate.",
        source_mode="human_directed",
        evidence_refs=("fixture:one",),
    )
    with pytest.raises(AdapterGapRequired) as caught:
        compile_frontier_blueprint(
            brief,
            draft_fn=lambda _brief: _unknown_draft(),
            semantic_review_fn=lambda _payload: {
                "accepted": True, "candidate_law_leakage": False,
                "rationale": "direction preserved", "evidence_refs": ["fixture:one"],
            },
            compiler_ref="compiler", reviewer_ref="reviewer",
        )
    gap = caught.value.gap
    assert gap.raw_fixture_refs == ("fixture:one",)
    assert gap.required_context_kind == "exact"
    assert "candidate axioms" in render_adapter_forge_prompt(gap)


def test_adapter_forge_only_emits_quarantined_proposal():
    brief = FrontierExplorationBrief(direction="Explore custom.", source_mode="human_directed")
    try:
        compile_frontier_blueprint(
            brief, draft_fn=lambda _brief: _unknown_draft(),
            semantic_review_fn=lambda _payload: {
                "accepted": True, "candidate_law_leakage": False,
                "rationale": "preserved", "evidence_refs": [brief.brief_id],
            }, compiler_ref="a", reviewer_ref="b",
        )
    except AdapterGapRequired as exc:
        gap = exc.gap
    receipt = run_adapter_forge(
        gap,
        coding_agent_fn=lambda _prompt: {
            "source_paths": ["adapter.py"], "test_paths": ["test_adapter.py"],
            "manifest": {"adapter_id": gap.proposed_adapter_id},
            "self_test_receipts": ["sha256:test"],
        },
        host_conformance_fn=lambda _proposal, _gap: {
            "ok": True,
            "tests": 8,
            "receipt_sha256": content_hash({"ok": True, "tests": 8}),
        },
        independent_review_fn=lambda payload: {
            "accepted": True,
            "reviewer_ref": "cold-reviewer",
            "evidence_refs": [
                payload["host_conformance"]["receipt_sha256"]
            ],
        },
    )
    assert receipt["status"] == "quarantined_registry_proposal"
    assert receipt["live_registry_mutated"] is False
    assert receipt["exactness_authority_granted"] is False


def test_adapter_forge_host_conformance_rejection_is_typed_without_review():
    gap = AdapterGap(
        brief_digest="brief:test",
        proposed_adapter_id="magma_equational.v1",
        primitive_semantics_contract={"test": "frozen"},
        raw_fixture_refs=("sha256:fixture",),
        required_context_kind="exact",
        required_operations=("lower_theory_language_request",),
        required_receipts=("determinism",),
        forbidden_authorities=("live_registry_mutation",),
        acceptance_tests=("cover every frozen object",),
        gap_kind="capability_missing",
        missing_capabilities=("theory_language:new_observable",),
    )
    review_calls = 0

    def review(_payload):
        nonlocal review_calls
        review_calls += 1
        raise AssertionError("host-rejected proposal must not reach review")

    receipt = run_adapter_forge(
        gap,
        coding_agent_fn=lambda _prompt: {
            "source_paths": ["coordinate.py"],
            "test_paths": ["test_coordinate.py"],
            "manifest": {"request_id": "campaign-local-coordinate"},
            "self_test_receipts": ["sha256:deterministic"],
            "registry_mutation": False,
        },
        host_conformance_fn=lambda _proposal, _gap: (_ for _ in ()).throw(
            ValueError("capability coordinates do not cover the frozen objects exactly")
        ),
        independent_review_fn=review,
    )

    assert review_calls == 0
    assert receipt["status"] == "quarantined_capability_rejected"
    assert receipt["next_step"] == "return_rejection_to_theory_search"
    assert receipt["host_conformance"]["schema"] == (
        "leanmill.adapter_forge_host_rejection.v1"
    )
    assert receipt["independent_review"]["accepted"] is False
    assert receipt["review_evidence_binding"] is None


def test_blocked_public_campaign_resumes_through_adapter_forge_quarantine(tmp_path):
    attempt = tmp_path / "new-substrate"
    run = explore_axiom_space(
        FrontierCampaignDefinition(
            direction="Explore a finite colored-composition substrate with executable fixtures.",
            source_mode="structure_first",
            budget=budget_preset("smoke"),
        ),
        attempt_dir=attempt,
        typed_draft=_unknown_draft(),
    )
    assert run.status == "blocked_adapter_gap"
    before = registered_theory_adapter_ids()
    calls = {"coding": 0, "review": 0, "host": 0}

    def coding(_prompt):
        calls["coding"] += 1
        return {
            "source_paths": ["quarantine/finite_color_adapter.py"],
            "test_paths": ["quarantine/test_finite_color_adapter.py"],
            "manifest": {"adapter_id": "unbuilt_custom_substrate.v1"},
            "self_test_receipts": ["sha256:determinism", "sha256:roundtrip"],
        }

    def conformance(_proposal, _gap):
        calls["host"] += 1
        core = {"ok": True, "tests": 9, "fixture_replay": True}
        return {**core, "receipt_sha256": content_hash(core)}

    def review(payload):
        calls["review"] += 1
        return {
            "accepted": True,
            "reviewer_ref": "independent-adapter-reviewer",
            "rationale": "typed semantics and claim boundary match the frozen gap",
            "evidence_refs": [payload["host_conformance"]["receipt_sha256"]],
        }

    completion = execute_adapter_forge_attempt(
        attempt,
        coding_agent_fn=coding,
        host_conformance_fn=conformance,
        independent_review_fn=review,
    )
    assert completion["status"] == (
        "quarantined_adapter_proposal_requires_authority_and_new_attempt"
    )
    assert completion["provider_calls"] == 2
    assert registered_theory_adapter_ids() == before
    assert calls == {"coding": 1, "review": 1, "host": 1}
    assert execute_adapter_forge_attempt(
        attempt,
        coding_agent_fn=lambda _prompt: (_ for _ in ()).throw(AssertionError("called")),
        host_conformance_fn=lambda _proposal, _gap: (_ for _ in ()).throw(AssertionError("called")),
        independent_review_fn=lambda _payload: (_ for _ in ()).throw(AssertionError("called")),
    ) == completion


def _language_attempt(
    tmp_path,
    name="language-successor",
    expected_status="frontier_language_expansion_requested",
):
    attempt = tmp_path / name
    private, public = generate_keypair()

    def navigator(context, blueprint, journal, *, budget_ledger):
        calls = 0

        def decide(prompt):
            nonlocal calls
            calls += 1
            if calls == 1:
                return {
                    "decision": "request",
                    "capability_id": "inspect_presentation_extent",
                    "input_refs": {"formula_ids": [], "offset": 0, "limit": 2},
                    "rationale": "Freeze an evidence receipt for the language request.",
                }
            refs = re.findall(r'"receipt_id":"(sha256:[0-9a-f]{64})"', prompt)
            assert refs
            return {
                "decision": "request",
                "capability_id": "propose_theory_language_expansion",
                "input_refs": {
                    "change_kind": "new_operation",
                    "blind_spot": "Current equations alias the receipted source extent.",
                    "proposed_interface": "One executable unary structural coordinate.",
                    "evidence_refs": [refs[-1]],
                    "discriminating_test": "The new coordinate refines the receipted extent.",
                    "kill_condition": "The coordinate is absent, partial, or source-injective.",
                },
                "rationale": "Request a successor chart rather than mutate this epoch.",
            }

        return run_interactive_theory_navigator(
            context,
            blueprint,
            journal,
            agent_fn=decide,
            attempt_id=attempt.name,
            campaign_id="campaign:" + blueprint.blueprint_id.split(":", 1)[1][:24],
            budget_ledger=budget_ledger,
            max_rounds=2,
        )

    navigator.accepts_budget_ledger = True
    run = explore_axiom_space(
        FrontierCampaignDefinition(
            direction="Explore an anonymous finite language and invent a successor chart.",
            source_mode="structure_first",
            budget=budget_preset("smoke_20m"),
        ),
        attempt_dir=attempt,
        typed_draft=_draft(),
        packet_signer=lambda packet: sign_frontier_campaign(
            packet, private_key_pem=private, signer_ref="campaign-authority"
        ),
        navigator_fn=navigator,
    )
    assert run.status == expected_status
    (attempt / "private").mkdir(exist_ok=True)
    write_text_atomic(attempt / "private" / "campaign_signer.pem", private)
    write_text_atomic(attempt / "campaign_signer_public.pem", public)
    return attempt


def _coordinate_application(source, gap_id: str) -> dict:
    source_sort = source.signature.sorts[0].name
    signature = TheorySignature(
        name=source.signature.name,
        sorts=source.signature.sorts,
        operations=(
            *source.signature.operations,
            OperationSymbol("coordinate", (source_sort,), source_sort),
        ),
        relations=source.signature.relations,
    )
    models = {}
    for record in source.universe.models:
        model = record.model
        size = dict(model.sort_sizes)[source_sort]
        image = FiniteModel(
            sort_sizes=model.sort_sizes,
            operations=(*model.operations, ("coordinate", tuple(range(size)))),
            relations=model.relations,
        )
        models[record.model_id] = image.to_json()
    core = {
        "schema": "leanmill.finite_model_functor_application.v1",
        "gap_id": gap_id,
        "context_hash": source.context_hash,
        "functor_id": "campaign-local:test-coordinate",
        "signature": signature.to_json(),
        "models": models,
    }
    return {**core, "receipt_sha256": content_hash(core)}


def _materialized_coordinate_generator(source, gap: AdapterGap) -> dict:
    image = _coordinate_application(source, gap.gap_id)
    raw_sort = source.signature.sorts[0].name
    raw_model = FiniteModel(
        sort_sizes=((raw_sort, 3),),
        operations=((source.signature.operations[0].name, (0,) * 9),),
    )
    abstract_signature = TheorySignature.from_json(image["signature"])
    abstract_model = FiniteModel(
        sort_sizes=raw_model.sort_sizes,
        operations=(*raw_model.operations, ("coordinate", (0, 1, 2))),
    )
    request = gap.primitive_semantics_contract["theory_language_request"]
    core = {
        "schema": CANDIDATE_SCHEMA,
        "request_id": request["request_id"],
        "gap_id": gap.gap_id,
        "context_hash": source.context_hash,
        "codec_id": "campaign-local:coordinate-factorization",
        "raw_signature": source.signature.to_json(),
        "abstract_signature": abstract_signature.to_json(),
        "raw_base_axioms": [row.to_json() for row in source.base_axioms],
        "source_alpha_models": image["models"],
        "source_lowered_models": {
            row.model_id: row.model.to_json() for row in source.universe.models
        },
        "generated_batches": [
            {
                "raw_sort_sizes": {raw_sort: 3},
                "abstract_sort_sizes": {raw_sort: 3},
                "models": [{
                    "abstract_model": abstract_model.to_json(),
                    "raw_model": raw_model.to_json(),
                }],
                "generator_ref": "fixture:order-three-coordinate-construction",
            }
        ],
        "generator_provenance_refs": ["fixture:construction-replay"],
        "max_relabelings": 720,
        "isomorphism_policy": ISOMORPHISM_POLICY,
    }
    return {**core, "receipt_sha256": content_hash(core)}


def test_functor_application_requires_exact_source_coverage(tmp_path):
    from ztare.leanmill.adapters.generic_fol_finite import (
        build_context_from_functor_application,
    )

    attempt = _language_attempt(tmp_path, "partial-functor-image")
    source = load_formal_theory_context(attempt / "formal_context.json")
    application = _coordinate_application(source, "partial-image")
    application["models"].pop(next(iter(application["models"])))
    core = {key: value for key, value in application.items() if key != "receipt_sha256"}
    application["receipt_sha256"] = content_hash(core)
    with pytest.raises(ValueError, match="cover every source object exactly"):
        build_context_from_functor_application(
            source,
            application,
            formula_grammar={
                "schema": "leanmill.universal_equation_grammar.v1",
                "max_total_operation_order": 2,
            },
        )


def test_language_request_forge_review_builds_successor_and_resumes_without_provider(tmp_path):
    attempt = _language_attempt(tmp_path)
    source = load_formal_theory_context(attempt / "formal_context.json")

    def forge(path, *, _attempt_lease):
        def host(_proposal, typed_gap):
            application = _coordinate_application(source, typed_gap.gap_id)
            write_json_atomic(path / "theory_language_functor_image.json", application)
            core = {
                "ok": True,
                "context_hash": source.context_hash,
                "functor_image_receipt_sha256": application["receipt_sha256"],
            }
            return {**core, "receipt_sha256": content_hash(core)}

        return execute_adapter_forge_attempt(
            path,
                coding_agent_fn=lambda _prompt: {
                    "source_paths": ["coordinate.py"],
                    "test_paths": ["test_coordinate.py"],
                    "manifest": {"request_id": "campaign-local-coordinate"},
                "self_test_receipts": ["sha256:deterministic"],
                "registry_mutation": False,
            },
            host_conformance_fn=host,
            independent_review_fn=lambda payload: {
                "accepted": True,
                "reviewer_ref": "independent-language-reviewer",
                "rationale": "The total finite image passes the frozen host boundary.",
                "evidence_refs": [payload["host_conformance"]["receipt_sha256"]],
            },
        )

    resumed = []

    def resume(path, *, _attempt_lease):
        checkpoint = read_json(path / "navigation_epoch_checkpoint.json", {})
        resumed.append(checkpoint["trace"][0]["decision"])
        return path

    result = advance_frontier_language_expansion(
        attempt, forge_fn=forge, resume_fn=resume
    )
    assert result["status"] == "successor_epoch_admitted"
    assert result["target_epoch"] == 1
    assert resumed == ["language_successor_admitted"]
    assert not (attempt / "run.json").exists()
    assert (attempt / "formal_context.epoch-001.json").is_file()
    successor = load_formal_theory_context(attempt / "formal_context.epoch-001.json")
    assert "coordinate" in successor.signature.operation_map
    successor_blueprint = read_json(attempt / "blueprint.epoch-001.json", {})
    verification = successor_blueprint["verification_plan"]
    assert not {
        "larger_carriers", "larger_model_strata", "heldout_strata"
    }.intersection(verification)
    assert verification["successor_claim_boundary"]["model_scope"] == (
        "exact_frozen_source_functor_image"
    )
    assert "fixed_size_countermodel_finder" not in successor_blueprint[
        "executable_preflight_receipt"
    ]["adapter_capabilities"]
    consumption = read_json(
        attempt / "theory_language_successor_consumption.epoch-001.json", {}
    )
    assert consumption["global_registry_mutated"] is False
    audit = audit_project_schema_routes(attempt)
    route = next(
        row for row in audit["routes"]
        if row["route_id"] == "theory_language_compilation_outcome_totality.v1"
    )
    assert route["unconsumed_count"] == 0
    assert route["produced_count"] == route["consumed_count"] == 2


def test_blocked_language_request_consumes_reviewed_data_only_generator(tmp_path):
    attempt = _language_attempt(tmp_path, "generative-language-successor")
    source = load_formal_theory_context(attempt / "formal_context.json")
    registry_before = registered_theory_adapter_ids()

    def forge(path, *, _attempt_lease):
        gap = AdapterGap.from_json(read_json(path / "adapter_gap.json", {}))
        workspace = stage_adapter_forge_workspace(path, gap)
        candidate = _materialized_coordinate_generator(source, gap)
        write_json_atomic(workspace / "generative_candidate.json", candidate)
        write_json_atomic(
            workspace / "candidate_checks.json",
            {"candidate_receipt_sha256": candidate["receipt_sha256"]},
        )

        def host(proposal, typed_gap):
            return host_capability_conformance(
                proposal,
                typed_gap,
                workspace=workspace,
                output_path=path / "theory_language_coordinates.json",
            )

        return execute_adapter_forge_attempt(
            path,
            coding_agent_fn=lambda _prompt: {
                "source_paths": ["generative_candidate.json"],
                "test_paths": ["candidate_checks.json"],
                "manifest": {
                    "capability_source": "generative_candidate.json",
                    "interface": CANDIDATE_SCHEMA,
                    "request_id": candidate["request_id"],
                    "observable_paths": [],
                },
                "self_test_receipts": [candidate["receipt_sha256"]],
                "registry_mutation": False,
            },
            host_conformance_fn=host,
            independent_review_fn=lambda payload: {
                "accepted": True,
                "reviewer_ref": "fixture:independent-generative-review",
                "rationale": "The fixed materialization replays through the host.",
                "evidence_refs": [
                    payload["host_conformance"]["receipt_sha256"]
                ],
            },
        )

    result = advance_frontier_language_expansion(attempt, forge_fn=forge)
    assert result["status"] == "successor_epoch_admitted"
    assert registered_theory_adapter_ids() == registry_before
    assert (attempt / "theory_language_generative_candidate.json").is_file()
    assert (attempt / "theory_language_generative_application.json").is_file()

    successor = load_formal_theory_context(attempt / "formal_context.epoch-001.json")
    blueprint = read_json(attempt / "blueprint.epoch-001.json", {})
    representation = blueprint["adapter_config"]["generative_representation"]
    assert blueprint["verification_plan"]["heldout_strata"] == [
        {"sort_sizes": {successor.signature.sorts[0].name: 3}}
    ]
    generated = FiniteModel.from_json(
        representation["candidate"]["generated_batches"][0]["models"][0][
            "abstract_model"
        ]
    )
    target = next(
        row.axiom
        for row in successor.formula_profiles
        if not evaluate_axiom(successor.signature, row.axiom, generated)
    )
    finder = materialize_theory_adapter_capability(
        blueprint["adapter_id"],
        "fixed_size_countermodel_finder",
        signature=successor.signature,
        adapter_config=blueprint["adapter_config"],
    )
    boundary = finder(
        (),
        target,
        sort_sizes=dict(generated.sort_sizes),
        base_axioms=successor.base_axioms,
        timeout_ms=1,
    )
    assert boundary.status == "countermodel_found"
    assert boundary.solver.startswith("reviewed_generative_representation:")


def test_registered_language_compiler_admits_successor_without_forge(
    tmp_path, monkeypatch
):
    from ztare.leanmill.adapters import generic_fol_finite

    compiler = generic_fol_finite.compile_theory_language_expansion

    def registered_compiler(**kwargs):
        application = _coordinate_application(
            kwargs["source_context"], "registered-compiler"
        )
        return compiler(**{**kwargs, "approved_application": application})

    monkeypatch.setitem(
        generic_fol_finite.CAPABILITIES,
        "theory_language_expansion_compiler",
        registered_compiler,
    )
    attempt = _language_attempt(
        tmp_path,
        "registered-language-successor",
        expected_status="frontier_language_expansion_requested",
    )
    resumed = []
    result = advance_frontier_language_expansion(
        attempt,
        forge_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("registered compiler must bypass AdapterForge")
        ),
    )
    assert result["status"] == "successor_epoch_admitted"
    assert (attempt / "theory_language_successor_commit.json").is_file()
    recovered = advance_frontier_language_expansion(
        attempt,
        forge_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("committed successor must bypass AdapterForge")
        ),
        resume_fn=lambda path, **_kwargs: resumed.append(path),
    )
    assert recovered["recovered"] is True
    assert len(resumed) == 1
    assert not (attempt / "theory_language_successor_commit.json").exists()
    assert (attempt / "theory_language_successor_commit.epoch-001.json").is_file()
    successor = load_formal_theory_context(attempt / "formal_context.epoch-001.json")
    assert "coordinate" in successor.signature.operation_map
    admission = read_json(attempt / "registered_language_compiler_admission.json", {})
    assert admission["authority"] == "leanmill.theory_adapter_registry"
    audit = audit_project_schema_routes(attempt)
    route = next(
        row for row in audit["routes"]
        if row["route_id"] == "theory_language_compilation_outcome_totality.v1"
    )
    assert route["unconsumed_count"] == 0
    assert route["produced_count"] == route["consumed_count"] == 1


@pytest.mark.parametrize(
    ("forge_outcome", "expected_outcome"),
    [
        ("rejected", "rejected"),
        ("unavailable", "unavailable"),
        ("coordinate_only", "unavailable"),
    ],
)
def test_language_advancement_returns_nonadmitted_outcomes_to_navigation(
    tmp_path, forge_outcome, expected_outcome
):
    attempt = _language_attempt(tmp_path, f"language-{forge_outcome}")
    resumed = []

    def forge(path, *, _attempt_lease):
        if forge_outcome == "coordinate_only":
            return execute_adapter_forge_attempt(
                path,
                coding_agent_fn=lambda _prompt: {
                    "source_paths": ["coordinate.py"],
                    "test_paths": ["test_coordinate.py"],
                    "manifest": {"request_id": "coordinate-only"},
                    "self_test_receipts": ["sha256:deterministic"],
                    "registry_mutation": False,
                },
                host_conformance_fn=lambda _proposal, _gap: (
                    lambda core: {**core, "receipt_sha256": content_hash(core)}
                )({"ok": True, "coordinate_receipt_sha256": "sha256:" + "a" * 64}),
                independent_review_fn=lambda payload: {
                    "accepted": True,
                    "reviewer_ref": "coordinate-reviewer",
                    "rationale": "Coordinate bytes pass, but no functor image was supplied.",
                    "evidence_refs": [payload["host_conformance"]["receipt_sha256"]],
                },
            )
        return {
            "status": (
                "adapter_proposal_rejected_return_to_search"
                if forge_outcome == "rejected"
                else "unavailable"
            ),
            "reason": f"fixture_{forge_outcome}",
            "evidence_refs": [f"receipt:{forge_outcome}"],
        }

    advance_frontier_language_expansion(
        attempt,
        forge_fn=forge,
        resume_fn=lambda path, **_kwargs: resumed.append(path),
    )
    run = read_json(attempt / "run.json", {})
    assert run["status"] == "frontier_objective_unmet"
    feedback = run["navigation"]["objective_review_history"][-1]
    assert feedback["outcome"] == expected_outcome
    assert feedback["request_id"].startswith("theory-language-request:")
    assert feedback["repeat_requires_new_evidence"] is True
    assert "next_discriminator" not in feedback
    assert "kill_condition" not in feedback
    assert len(resumed) == 1
    audit = audit_project_schema_routes(attempt)
    route = next(
        row for row in audit["routes"]
        if row["route_id"] == "theory_language_compilation_outcome_totality.v1"
    )
    assert route["unconsumed_count"] == 0


def test_direct_compiler_rejection_becomes_feedback_without_forge(tmp_path, monkeypatch):
    from ztare.leanmill.adapters import generic_fol_finite
    from ztare.leanmill.frontier_campaign_actions import replay_frontier_campaign

    monkeypatch.setitem(
        generic_fol_finite.CAPABILITIES,
        "theory_language_expansion_compiler",
        lambda **_kwargs: {"status": "rejected", "reason": "typed_fixture_rejection"},
    )
    attempt = _language_attempt(
        tmp_path,
        "language-direct-rejected",
        expected_status="frontier_language_expansion_requested",
    )
    result = advance_frontier_language_expansion(
        attempt,
        forge_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("compiler rejection must bypass AdapterForge")
        ),
    )
    assert result["status"] == "rejected"
    run = read_json(attempt / "run.json", {})
    feedback = run["navigation"]["objective_review_history"][-1]
    assert feedback["outcome"] == "rejected"
    assert feedback["repeat_requires_new_evidence"] is True
    assert not (attempt / "adapter_gap.json").exists()
    replay = replay_frontier_campaign(attempt)
    assert replay["ok"] is True
    assert replay["language_compilation_feedback_check"]["outcome"] == "rejected"
    audit = audit_project_schema_routes(attempt)
    route = next(
        row for row in audit["routes"]
        if row["route_id"] == "theory_language_compilation_outcome_totality.v1"
    )
    assert route["unconsumed_count"] == 0
