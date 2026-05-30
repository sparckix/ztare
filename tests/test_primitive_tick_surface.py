from src.ztare.research_director.primitive_tick_surface import (
    build_primitive_tick_surface,
    query_terms_for_scope,
    render_text,
)


def test_ns_scope_surfaces_nonadaptive_source_selection_terms() -> None:
    terms = query_terms_for_scope("ns")

    assert "source_selection" in terms
    assert "nonadaptive" in terms
    assert "no_post_hoc" in terms
    assert "stopping_time" in terms
    assert "no_reuse" in terms
    assert "packing" in terms
    assert "injection" in terms
    assert "phase_space" in terms
    assert "owner_preimage" in terms
    assert "packet_ownership" in terms
    assert "null_form" in terms
    assert "signed_cancellation" in terms
    assert "positive_source_square" in terms
    assert "symbol_audit" in terms


def test_ns_surface_retains_pde_estimate_craft_ops_for_source_selection() -> None:
    terms = query_terms_for_scope("ns")
    surface = build_primitive_tick_surface(query_terms=terms, top_n=25)
    hit_ids = {hit.id for hit in surface.top_hits}

    assert "PDE-ESTIMATE-CRAFT-OPS" in hit_ids


def test_surface_renders_action_constraint_receipt_fields() -> None:
    surface = build_primitive_tick_surface(query_terms=["claim", "boundary"], top_n=5)
    text = render_text(surface)

    assert "action-constraint receipt fields" in text
    assert "receipt slots" not in text

def test_surface_renders_action_target_source_guard() -> None:
    surface = build_primitive_tick_surface(query_terms=["claim", "boundary"], top_n=5)
    text = render_text(surface)

    assert "infer the action target from source facts" in text
    assert "task/check-menu wording" in text

