from ztare.pde.engine import (
    PDEApplicabilityCardOptions,
    PDEEstimateSkeletonOptions,
    PDEEngineContextRequest,
    PDEFormalFeedbackOptions,
    PDEFormalSurfaceMapOptions,
    PDEKnowledgeServiceOptions,
    PDELeafWorkOrderOptions,
    build_pde_engine_context,
)


def test_pde_engine_context_composes_registry_leaf_and_formal_feedback() -> None:
    context = build_pde_engine_context(
        PDEEngineContextRequest(
            target="annular singular-integral payment",
            formal_feedback=PDEFormalFeedbackOptions(
                enabled=True,
                context="Riesz L1 theorem retrieval",
                top_k_mathlib=0,
                top_k_domain=0,
                top_k_own=0,
            ),
            leaf_work_order=PDELeafWorkOrderOptions(
                op_id="pec_l",
                goal="audit cancellation and projection payment",
                extra_gate_ids=("G-PDE-THEOREM-APPLICABILITY",),
            ),
        )
    )

    assert context["schema"] == "pde-engine-context-v1"
    assert context["formal_feedback"]["schema"] == "pde-formal-feedback-card-v1"
    assert context["leaf_work_order"]["schema"] == "pde-leaf-work-order-v1"
    assert context["leaf_work_order"]["formal_feedback_requested"] is True
    gate_ids = {
        gate["gate_id"]
        for gate in context["leaf_work_order"]["gate_requirements"]
    }
    assert "G-PDE-THEOREM-APPLICABILITY" in gate_ids
    assert "G-LINEAR-OBS-COERCIVITY" in gate_ids
    assert "leanmill_service" in context["service_boundaries"]


def test_pde_engine_context_passes_process_contract_to_leaf_work_order() -> None:
    context = build_pde_engine_context(
        PDEEngineContextRequest(
            target="active Carleson budget identity",
            leaf_work_order=PDELeafWorkOrderOptions(
                op_id="pec_l",
                require_process_contract=True,
                pattern_action_contract_ref="pattern.json",
                orchestration_contract_ref="orch.json",
                pencil_artifact_ref="pencil.md",
            ),
        )
    )

    refs = {
        item["artifact_key"]: item["artifact_ref"]
        for item in context["leaf_work_order"]["process_requirements"]
    }

    assert refs == {
        "pattern_action_contract": "pattern.json",
        "orchestration_contract": "orch.json",
        "pencil_artifact": "pencil.md",
    }


def test_pde_engine_context_passes_focused_gate_set_to_leaf_work_order() -> None:
    context = build_pde_engine_context(
        PDEEngineContextRequest(
            target="focused annular canary",
            leaf_work_order=PDELeafWorkOrderOptions(
                op_id="pec_l",
                only_gate_ids=(
                    "G-PDE-ANALYTIC-SUBSTANCE",
                    "G-PDE-OPERATOR-ADMISSIBILITY",
                ),
            ),
        )
    )

    gate_ids = [
        gate["gate_id"]
        for gate in context["leaf_work_order"]["gate_requirements"]
    ]

    assert gate_ids == [
        "G-PDE-ANALYTIC-SUBSTANCE",
        "G-PDE-OPERATOR-ADMISSIBILITY",
    ]
    assert any(
        "only_gate_ids supplied" in note
        for note in context["leaf_work_order"]["notes"]
    )


def test_pde_engine_context_can_emit_registry_without_optional_services() -> None:
    context = build_pde_engine_context(
        PDEEngineContextRequest(target="bare scaling audit")
    )

    assert context["gate_registry"]
    assert context["op_registry"]
    assert context["receipt_registry"]
    assert context["architecture_requirement_status_counts"]["implemented"] >= 12
    req_ids = {
        item["requirement_id"]
        for item in context["architecture_requirements"]
    }
    assert "rd.workbench.consumer" in req_ids
    assert context["currency_ledger"]["target_currency"] == "bare scaling audit"
    assert context["formal_feedback"] is None
    assert context["leaf_work_order"] is None


def test_pde_engine_context_attaches_estimate_skeletons() -> None:
    context = build_pde_engine_context(
        PDEEngineContextRequest(
            target="annular_bandlimited_riesz_l1_psd_trace_payment",
            estimate_skeletons=PDEEstimateSkeletonOptions(
                enabled=True,
                field="projection",
            ),
        )
    )

    assert context["estimate_skeletons"][0]["id"] == "projection_tail_invoice"
    assert context["currency_ledger"]["target_currency"] == (
        "annular_bandlimited_riesz_l1_psd_trace_payment"
    )


def test_pde_engine_context_applicability_cards_are_profile_obligations() -> None:
    context = build_pde_engine_context(
        PDEEngineContextRequest(
            target="annular Riesz profile",
            applicability_cards=PDEApplicabilityCardOptions(
                enabled=True,
                query="annular Riesz L1 PSD trace payment",
                available={"annular_bandlimit": True},
                source_profile="toy_pde_profile",
                top_k=1,
            ),
            theorem_db={
                "annular_riesz_profile": {
                    "requires": {
                        "annular_bandlimit": True,
                        "riesz_l1": True,
                    },
                    "concludes": {"profile_applicable": True},
                    "does_not_accept": ["raw_cz"],
                }
            },
        )
    )

    card = context["applicability_cards"][0]
    assert card["schema"] == "pde-applicability-card-v1"
    assert card["source_profile"] == "toy_pde_profile"
    assert card["applicability"]["missing_fields"] == ["riesz_l1"]
    assert "premise_shelf" not in card


def test_pde_engine_context_attaches_formal_surface_map() -> None:
    context = build_pde_engine_context(
        PDEEngineContextRequest(
            target="formal PDE surface inventory",
            formal_surface_map=PDEFormalSurfaceMapOptions(
                records=(
                    {
                        "primitive_id": "weak_solution_energy",
                        "status": "lean_statement_only",
                        "statement": "theorem weak_solution_energy : True := by trivial",
                        "lean_file": "PDE/WeakSolution.lean",
                    },
                ),
                required_primitives=("weak_solution_energy", "riesz_l1"),
                source_profile="toy_pde",
            ),
        )
    )

    surface_map = context["formal_surface_map"]
    assert surface_map["schema"] == "pde-formal-surface-map-v1"
    assert surface_map["source_profile"] == "toy_pde"
    assert surface_map["missing_required_primitives"] == ["riesz_l1"]
    assert surface_map["records"][0]["status"] == "lean_statement_only"


def test_pde_engine_context_attaches_knowledge_service() -> None:
    context = build_pde_engine_context(
        PDEEngineContextRequest(
            target="annular Riesz knowledge",
            theorem_db={
                "annular_profile": {
                    "requires": {"annular_bandlimit": True},
                    "concludes": {"usable": True},
                }
            },
            knowledge_service=PDEKnowledgeServiceOptions(
                enabled=True,
                query="annular bandlimit",
                available={"annular_bandlimit": True},
                statement="theorem annular : True := by trivial",
                top_k_mathlib=0,
                top_k_domain=0,
                top_k_own=0,
            ),
        )
    )

    knowledge = context["knowledge_context"]
    assert knowledge["schema"] == "pde-knowledge-context-v1"
    assert knowledge["theorem_profile_cards"][0]["applicability"]["verdict"] == "MATCH"
    assert "leanmill_service" in knowledge["service_boundaries"]
