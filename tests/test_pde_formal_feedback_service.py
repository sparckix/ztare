from ztare.pde.formal_feedback import (
    build_pde_formal_feedback_card,
    render_pde_formal_feedback_card,
)


def test_pde_formal_feedback_card_reuses_leanmill_shelf_with_injected_embedder() -> None:
    def embedder(text: str):
        text = text.lower()
        return [1.0, 0.0, 0.0] if "pressure" in text or "riesz" in text else [0.0, 1.0, 0.0]

    card = build_pde_formal_feedback_card(
        target="localized pressure Riesz estimate",
        statement="theorem pressure_riesz_bound : True := by trivial",
        context="Calderon-Zygmund pressure tail",
        embedder=embedder,
        top_k_mathlib=2,
        top_k_domain=0,
        top_k_own=0,
        threshold=0.0,
    )

    assert card["schema"] == "pde-formal-feedback-card-v1"
    assert card["formal_surface_status"] == "lean_statement_candidate"
    assert "semantic_premise_shelf" in card["leanmill_services_used"]
    assert "advisory_only_no_proof_credit" in card["credit_boundary"]
    assert "mathlib" in card["premise_shelf"]["corpus_sizes"]
    rendered = render_pde_formal_feedback_card(card)
    assert "PDE formal feedback" in rendered
    assert "Candidate lemma shelf" in rendered


def test_pde_formal_feedback_card_respects_compile_result_status() -> None:
    card = build_pde_formal_feedback_card(
        target="routine compiled lemma",
        statement="theorem routine_compiled_lemma : True := by trivial",
        compile_result={"success": True, "log": "ok"},
        embedder=lambda _text: [1.0, 0.0],
        top_k_mathlib=0,
        top_k_domain=0,
        top_k_own=0,
    )

    assert card["formal_surface_status"] == "lean_compile_passed"
    assert "governance/faithfulness" in card["recommended_next_leaf"]
