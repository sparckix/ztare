from __future__ import annotations

from ztare.research_director.primitive_family_registry import (
    PrimitiveFamilyCard,
    all_cards,
    build_registry_integrity_audit,
    dispatch_call_sites,
    parent_nodes,
)
from ztare.research_director.primitive_tick_surface import build_primitive_tick_surface


def test_primitive_family_registry_is_mece_for_current_cards() -> None:
    cards = all_cards()
    primitive_ids = [card.primitive_id for card in cards]
    assert len(primitive_ids) == len(set(primitive_ids))

    allowed_families = {
        "core_workbench_worker",
        "external_perspective_generator",
        "review_governance_helper",
        "composition_helper",
    }
    assert {card.family_id for card in cards} == allowed_families
    for card in cards:
        assert card.module_path
        assert card.entrypoint
        assert card.preserves_symbol_identity is True


def test_primitive_family_registry_covers_wrapped_autoresearch_call_sites() -> None:
    sites = dispatch_call_sites()
    for expected in {
        "rubric_review",
        "cold_llm_erdos_seed",
        "cold_shot_seed",
        "qualitative_evidence_cold_shot",
        "recombination_fusion",
        "evidence_gap_enrichment",
        "post_run_meta_audit",
        "charter_critic_patch",
        "frontier_script_scaffold",
        "primitive_quality_filter",
        "eigenquestion_generator",
        "substrate_recommender",
        "inverter_review",
    }:
        assert expected in sites


def test_primitive_family_registry_entrypoints_are_live() -> None:
    audit = build_registry_integrity_audit()

    assert audit.ok
    assert audit.card_count == len(all_cards())
    assert audit.dispatch_call_site_count >= 10
    assert audit.issues == ()


def test_primitive_family_registry_integrity_audit_catches_stale_card(monkeypatch) -> None:
    from ztare.research_director import primitive_family_registry as registry

    stale = PrimitiveFamilyCard(
        primitive_id="stale_card",
        family_id="core_workbench_worker",
        family_label="Core Workbench Worker",
        role="Deliberately stale test card.",
        module_path="src/ztare/research_director/primitive_family_registry.py",
        entrypoint="missing_entrypoint_for_test",
        lifecycle="test",
        call_site="stale_card",
        transport_policy="test",
        artifact_surface="test",
        trigger_surface="test",
        semantic_aliases=("test",),
    )
    monkeypatch.setattr(registry, "CARDS", registry.CARDS + (stale,))

    audit = registry.build_registry_integrity_audit()

    assert not audit.ok
    assert {issue.issue_type for issue in audit.issues} >= {"missing_entrypoint"}


def test_parent_nodes_surface_query_matches_without_hiding_children() -> None:
    nodes = parent_nodes(["cold_start", "inversion", "rubric"])
    by_id = {node.family_id: node for node in nodes}

    assert by_id["external_perspective_generator"].child_count >= 6
    assert "cold_start" in by_id["external_perspective_generator"].matched_terms
    assert by_id["review_governance_helper"].child_count >= 4
    assert "rubric" in by_id["review_governance_helper"].matched_terms
    assert by_id["external_perspective_generator"].child_primitives


def test_primitive_tick_surface_includes_semantic_parent_nodes() -> None:
    surface = build_primitive_tick_surface(
        query_terms=["cold_start", "inversion", "rubric"],
        top_n=3,
        per_bucket=1,
    )

    parent_ids = {node["family_id"] for node in surface.parent_nodes}
    assert "external_perspective_generator" in parent_ids
    assert "review_governance_helper" in parent_ids
