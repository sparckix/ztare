from __future__ import annotations

import json
from pathlib import Path

from src.ztare.research_director.primitive_catalog_taxonomy import (
    catalog_health,
    catalog_parent_nodes,
    enrich_row,
    normalize_catalog_path,
    semantic_family_for_row,
    source_category_for_path,
)


def test_source_category_is_path_derived() -> None:
    assert source_category_for_path("src/ztare/fit/analogy.py") == "fit/regime"
    assert source_category_for_path("src/ztare/gates/cage.py") == "gate"
    assert source_category_for_path("src/ztare/reports/autoresearch_kernel_health.py") == "report"
    assert source_category_for_path("src/ztare/research_director/eigenquestion_generator.py") == "research-operator"


def test_normalize_catalog_path_repairs_known_relocations() -> None:
    assert normalize_catalog_path("scripts/mining/mine_climb_triggers.py") == (
        "scripts/public/mining/mine_climb_triggers.py"
    )
    assert normalize_catalog_path("scripts/mining/mine_closure_patterns.py") == (
        "scripts/public/mining/research_mode/mine_closure_patterns.py"
    )
    assert normalize_catalog_path("scripts/projects/ns/CAS_W6_verification.py") == (
        "projects/ns_millennium_hunt/scripts/CAS_W6_verification.py"
    )
    assert normalize_catalog_path("src/ztare/orchestrator/briefing_providers/path_b_promotion_floor.py") == (
        "src/ztare/orchestrator/briefing_providers/variational_promotion_floor.py"
    )


def test_semantic_family_is_single_axis_over_source_category_and_kind() -> None:
    family, reason = semantic_family_for_row({
        "id": "CAGE",
        "path": "src/ztare/gates/cage.py",
        "kind": "gate",
        "description": "deterministic gate orchestration",
    })
    assert family == "evidence_governance_gate"
    assert reason

    family, _ = semantic_family_for_row({
        "id": "ANALOGY-PRIMITIVE",
        "path": "src/ztare/fit/analogy.py",
        "kind": "primitive",
        "description": "cross-domain analogy proposer",
    })
    assert family == "model_fit_structure_probe"

    family, _ = semantic_family_for_row({
        "id": "AUTORESEARCH-KERNEL-HEALTH",
        "path": "src/ztare/reports/autoresearch_kernel_health.py",
        "kind": "primitive",
        "description": "Aggregate autoresearch kernel health read model.",
    })
    assert family == "mining_operations_intelligence"


def test_enrich_row_adds_generated_taxonomy_without_dropping_fields() -> None:
    row = {
        "id": "EIGENQUESTION-GENERATOR",
        "path": "src/ztare/research_director/eigenquestion_generator.py",
        "kind": "primitive",
        "description": "Generate an orthogonal question.",
        "applicability": ["eigenquestion"],
        "impact_factor_expost": 3,
        "last_used": "",
        "dependencies": [],
    }
    enriched = enrich_row(row)

    assert enriched["id"] == row["id"]
    assert enriched["source_category"] == "research-operator"
    assert enriched["semantic_family"] == "research_move_operator"
    assert enriched["semantic_family_reason"]


def test_catalog_parent_nodes_are_full_catalog_families() -> None:
    rows = [
        {"id": "CAGE", "path": "src/ztare/gates/cage.py", "kind": "gate", "description": ""},
        {"id": "FIT-ENGINE", "path": "src/ztare/fit/fit_engine.py", "kind": "primitive", "description": ""},
        {"id": "PATTERN-001", "path": "org/patterns/example.md", "kind": "pattern", "description": ""},
    ]
    nodes = catalog_parent_nodes(rows, ["gate", "fit"])
    by_id = {node.family_id: node for node in nodes}

    assert by_id["evidence_governance_gate"].child_count == 1
    assert by_id["model_fit_structure_probe"].child_count == 1
    assert by_id["pattern_memory"].child_count == 1
    assert "gate" in by_id["evidence_governance_gate"].matched_terms


def test_catalog_health_reports_duplicates_and_stale_outputs(tmp_path: Path) -> None:
    catalog = tmp_path / "architecture_index.jsonl"
    atlas = tmp_path / "primitive_atlas_embeddings.json"
    rendered = tmp_path / "INDEX.md"
    rows = [
        {
            "id": "DUP",
            "path": "src/ztare/gates/cage.py",
            "kind": "gate",
            "description": "a",
            "signature": "sig",
        },
        {
            "id": "DUP",
            "path": "src/ztare/gates/cage.py",
            "kind": "gate",
            "description": "b",
            "signature": "sig",
        },
    ]
    catalog.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    atlas.write_text("{}")
    rendered.write_text("# stale\n")

    health = catalog_health(
        catalog_path=catalog,
        atlas_path=atlas,
        rendered_index_path=rendered,
    )

    assert not health.ok
    assert health.duplicate_ids == {"DUP": 2}
    assert health.duplicate_signatures == {"sig": 2}


def test_catalog_health_checks_missing_paths_after_known_renames(tmp_path: Path) -> None:
    catalog = tmp_path / "architecture_index.jsonl"
    atlas = tmp_path / "primitive_atlas_embeddings.json"
    rendered = tmp_path / "INDEX.md"
    row = {
        "id": "VARIATIONAL-PROMOTION-FLOOR-PROVIDER",
        "path": "src/ztare/orchestrator/briefing_providers/path_b_promotion_floor.py",
        "kind": "orchestrator",
        "description": "Variational-promotion floor provider.",
        "signature": "provider",
    }
    catalog.write_text(json.dumps(row) + "\n")
    atlas.write_text("{}")
    rendered.write_text("# current\n")

    health = catalog_health(
        catalog_path=catalog,
        atlas_path=atlas,
        rendered_index_path=rendered,
    )

    assert health.missing_paths == ()
