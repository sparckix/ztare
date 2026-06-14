from src.ztare.research_director.primitive_tick_surface import (
    BUCKET_TERMS,
    DEFAULT_QUERY_TERMS,
    SCOPE_QUERY_TERMS,
    build_primitive_tick_surface,
    expand_query_terms,
    query_terms_for_scope,
    render_text,
)


def test_query_and_bucket_terms_have_no_internal_duplicates() -> None:
    term_sets = {
        "DEFAULT_QUERY_TERMS": DEFAULT_QUERY_TERMS,
        **{f"SCOPE_QUERY_TERMS[{key}]": terms for key, terms in SCOPE_QUERY_TERMS.items()},
        **{f"BUCKET_TERMS[{key}]": terms for key, terms in BUCKET_TERMS.items()},
    }

    for name, terms in term_sets.items():
        assert len(terms) == len(set(terms)), name


def test_natural_query_text_expands_to_retrieval_terms() -> None:
    terms = expand_query_terms([
        "The loop has stagnated; inspect thesis_control_mode and information yield before another iteration."
    ])

    assert "stagnated" in terms
    assert "thesis_control_mode" in terms
    assert "thesis control mode" in terms
    assert "information yield" in terms
    assert "information_yield" in terms
    assert "the" not in terms


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


def test_surface_renders_catalog_parent_node_examples() -> None:
    surface = build_primitive_tick_surface(query_terms=["gate"], top_n=5)
    catalog_nodes = [
        node
        for node in surface.parent_nodes
        if node.get("scope") == "catalog" and node.get("example_ids")
    ]
    text = render_text(surface)

    assert catalog_nodes
    assert "examples:" in text
    assert str(catalog_nodes[0]["example_ids"][0]) in text


def test_natural_rd_query_routes_parent_node_and_child() -> None:
    surface = build_primitive_tick_surface(
        query_terms=[
            "The loop has stagnated; inspect thesis_control_mode and information yield before another iteration."
        ],
        top_n=12,
    )
    catalog_nodes = [
        node for node in surface.parent_nodes
        if node.get("scope") == "catalog"
    ]
    top_ids = {hit.id for hit in surface.top_hits}

    assert catalog_nodes[0]["family_id"] == "evidence_governance_gate"
    assert {"ITERATIONSIGNAL", "EVALUATE-INFORMATION-YIELD"} & top_ids
