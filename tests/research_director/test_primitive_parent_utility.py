from __future__ import annotations

from dataclasses import asdict

from ztare.research_director.primitive_parent_utility import (
    build_parent_utility_audit,
    render_parent_utility_audit,
)
from ztare.research_director.primitive_tick_surface import (
    build_primitive_tick_surface,
    render_text,
)


def test_parent_utility_audit_checks_family_rank_and_child_recall() -> None:
    audit = build_parent_utility_audit()

    assert audit.ok
    assert audit.case_count >= 10
    assert audit.catalog_rank_recall == 1.0
    assert audit.worker_rank_recall == 1.0
    assert audit.child_recall == 1.0

    by_case = {result.case_id: result for result in audit.results}
    assert by_case["loop_stagnation_information_yield"].catalog_family_rank == 1
    assert "EVALUATE-INFORMATION-YIELD" in by_case["loop_stagnation_information_yield"].matched_child_ids
    assert by_case["cold_start_deanchor_seed"].worker_family_rank == 1
    assert by_case["rubric_review_pre_run"].worker_family_rank == 1
    assert by_case["natural_rd_eigenquestion_rotation"].catalog_family_rank == 1
    assert "EIGENQUESTION-GENERATOR" in by_case["natural_rd_eigenquestion_rotation"].matched_child_ids
    assert by_case["natural_rd_stagnation_control"].catalog_family_rank == 1
    assert "EVALUATE-INFORMATION-YIELD" in by_case["natural_rd_stagnation_control"].matched_child_ids
    assert by_case["natural_rd_operations_source_health"].catalog_family_rank == 1
    assert "CROSS-SOURCE-DIVERGENCE-AUDIT" in by_case["natural_rd_operations_source_health"].matched_child_ids
    assert by_case["natural_rd_proof_goal_surface"].catalog_family_rank == 1
    assert "PROOF-STATE-SIGNAL" in by_case["natural_rd_proof_goal_surface"].matched_child_ids


def test_parent_utility_audit_json_shape_is_stable() -> None:
    payload = asdict(build_parent_utility_audit())

    assert payload["ok"] is True
    assert payload["results"]
    assert {
        "case_id",
        "ok",
        "catalog_family_rank",
        "worker_family_rank",
        "matched_child_ids",
    }.issubset(payload["results"][0])


def test_parent_utility_text_names_failures_and_matches() -> None:
    rendered = render_parent_utility_audit(build_parent_utility_audit())

    assert "Primitive parent utility status=ok" in rendered
    assert "loop_stagnation_information_yield: ok" in rendered
    assert "cold_start_deanchor_seed: ok" in rendered
    assert "natural_rd_stagnation_control: ok" in rendered


def test_tick_surface_renders_catalog_and_worker_families_separately() -> None:
    surface = build_primitive_tick_surface(
        query_terms=["cold_start", "deanchor", "inversion", "cross-domain", "seed"],
        top_n=5,
        per_bucket=1,
    )
    rendered = render_text(surface)

    assert "catalog parent nodes:" in rendered
    assert "worker family nodes:" in rendered
    assert "external_perspective_generator" in rendered
    assert "cold_llm_erdos_seed" in rendered
