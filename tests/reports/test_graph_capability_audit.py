from __future__ import annotations

import json
from pathlib import Path

from ztare.reports.graph_capability_audit import (
    _operator_card_atlas_summary,
    build_graph_capability_audit,
    render_markdown,
)
from ztare.research_director.primitive_operator_cards import operator_card_catalog_entries


def test_graph_capability_audit_separates_standard_and_recombination_layers() -> None:
    report = build_graph_capability_audit()

    assert report["schema"] == "ztare-graph-capability-audit-v1"
    summary = report["summary"]
    assert "minimum_cut_bottleneck" in summary["standard_algorithm_rows"]
    assert "lean_signature_extraction" in summary["recombination_rows"]
    assert "probability_dag_trace_carrier" in summary["ready_receipt_paths"]
    assert "source_claim_graph_trace_carrier" in summary["ready_receipt_paths"]
    assert "source_freshness_graph_guard" in summary["ready_receipt_paths"]
    assert "autoresearch_probability_dag_prompt_consumer" in summary["ready_receipt_paths"]
    assert "graph_action_card_lowering" in summary["ready_receipt_paths"]
    assert "graph_carrier_rd_action_consumer" in summary["ready_receipt_paths"]
    assert "l3a_workmap_overlay" in summary["recombination_rows"]
    assert summary["missing_rows"] == []
    assert "known_refactor_needed" not in summary["status_counts"]
    assert report["verdict"]["not_framework_replacement"] is True
    assert "standard algorithms remain library-backed" in report["verdict"]["strongest_supported_claim"]
    assert "ledger/trajectory overlay" in report["verdict"]["needs_before_stronger_claim"]
    assert "operator_card_atlas" in report
    assert summary["operator_card_atlas_status"] == report["operator_card_atlas"]["status"]
    assert summary["operator_card_routing_mode"] == report["operator_card_atlas"]["routing_mode"]


def test_graph_action_card_lowering_markers_are_present() -> None:
    report = build_graph_capability_audit()
    by_id = {row["method_id"]: row for row in report["rows"]}
    row = by_id["graph_action_card_lowering"]

    assert row["present"] is True
    assert row["status"] == "ready_receipt_path"
    assert set(row["markers_found"]) == {
        "OP-GDC-01",
        "graph_diagnostic_carrier",
        "selected_action_card_or_gate",
        "operator_card_catalog_entries",
        "build_operator_card_atlas",
        "route_operator_cards_semantic",
        "operator_card_routes",
    }


def test_autoresearch_probability_dag_single_prompt_consumer_is_tracked() -> None:
    report = build_graph_capability_audit()
    by_id = {row["method_id"]: row for row in report["rows"]}
    row = by_id["autoresearch_probability_dag_prompt_consumer"]

    assert row["present"] is True
    assert row["status"] == "ready_receipt_path"
    assert "one probability_dag_context prompt block" in row["notes"]
    assert "unify autoresearch probability-DAG consumers" not in report["verdict"]["needs_before_stronger_claim"]


def test_source_claim_graph_trace_carrier_is_tracked() -> None:
    report = build_graph_capability_audit()
    by_id = {row["method_id"]: row for row in report["rows"]}
    row = by_id["source_claim_graph_trace_carrier"]

    assert row["present"] is True
    assert row["status"] == "ready_receipt_path"
    assert "source/evidence/gap graph record" in row["ztare_specific_layer"]
    assert "non-NS carrier" not in report["verdict"]["needs_before_stronger_claim"]


def test_source_freshness_graph_guard_is_tracked() -> None:
    report = build_graph_capability_audit()
    by_id = {row["method_id"]: row for row in report["rows"]}
    row = by_id["source_freshness_graph_guard"]

    assert row["present"] is True
    assert row["status"] == "ready_receipt_path"
    assert set(row["markers_found"]) == {
        "artifact_source_freshness",
        "raw_relative_path",
        "source_index_unverified",
        "evidence_compile_unverified",
        "misleading_or_noise",
    }
    assert "stale or count-only source graph signals" in row["ztare_specific_layer"]


def test_graph_carrier_rd_action_consumer_is_tracked() -> None:
    report = build_graph_capability_audit()
    by_id = {row["method_id"]: row for row in report["rows"]}
    row = by_id["graph_carrier_rd_action_consumer"]

    assert row["present"] is True
    assert row["status"] == "ready_receipt_path"
    assert "graph-card route provenance" in row["ztare_specific_layer"]
    assert {"OP-GDC-01", "operator_card_routes", "operator_card_ids"} <= set(row["markers_found"])
    assert "out-of-loop graph consumer" not in report["verdict"]["needs_before_stronger_claim"]


def test_autoresearch_loop_has_one_probability_dag_prompt_placeholder() -> None:
    text = Path("src/ztare/validator/autoresearch_loop.py").read_text(encoding="utf-8")

    assert text.count("{probability_dag_context}") == 1
    assert "{dag_steering_context}" not in text
    assert "{_dag_steering_context}" not in text


def test_graph_capability_audit_reports_absent_operator_card_atlas(tmp_path: Path) -> None:
    summary = _operator_card_atlas_summary(tmp_path)

    assert summary["status"] == "absent"
    assert summary["routing_mode"] == "lexical_fallback"
    assert summary["semantic_deployed"] is False
    assert summary["next_command"] == "make move-card-atlas-build"
    assert summary["atlas_path"] == "analytics/public/index/operator_card_atlas_embeddings.json"
    assert summary["manifest_path"] == "analytics/public/index/operator_card_atlas_manifest.json"


def test_graph_capability_audit_reports_fresh_operator_card_atlas(tmp_path: Path) -> None:
    rows = operator_card_catalog_entries()
    index_dir = tmp_path / "analytics/public/index"
    index_dir.mkdir(parents=True)
    (index_dir / "operator_card_atlas_embeddings.json").write_text(
        json.dumps(
            {
                "model": "gemini-embedding-001",
                "dimensions": 768,
                "size": len(rows),
                "meta": {row["id"]: {"card_id": row["card_id"]} for row in rows},
                "embeddings": [{"id": row["id"], "embedding": [0.1, 0.2]} for row in rows],
            }
        ),
        encoding="utf-8",
    )
    (index_dir / "operator_card_atlas_manifest.json").write_text(
        json.dumps(
            {
                "size": len(rows),
                "source": "ztare.research_director.primitive_operator_cards",
            }
        ),
        encoding="utf-8",
    )

    summary = _operator_card_atlas_summary(tmp_path)

    assert summary["status"] == "fresh"
    assert summary["routing_mode"] == "semantic_atlas"
    assert summary["semantic_deployed"] is True
    assert summary["next_command"] is None
    assert summary["embedding_count"] == len(rows)
    assert summary["manifest_size"] == len(rows)
    assert summary["size_matches_expected"] is True


def test_graph_capability_audit_reports_stale_operator_card_atlas(tmp_path: Path) -> None:
    index_dir = tmp_path / "analytics/public/index"
    index_dir.mkdir(parents=True)
    (index_dir / "operator_card_atlas_embeddings.json").write_text(
        json.dumps(
            {
                "model": "gemini-embedding-001",
                "dimensions": 768,
                "size": 1,
                "meta": {"operator_card:OP-OLD:deadbeef": {"card_id": "OP-OLD"}},
                "embeddings": [{"id": "operator_card:OP-OLD:deadbeef", "embedding": [0.1, 0.2]}],
            }
        ),
        encoding="utf-8",
    )
    (index_dir / "operator_card_atlas_manifest.json").write_text(
        json.dumps(
            {
                "size": 1,
                "source": "ztare.research_director.primitive_operator_cards",
            }
        ),
        encoding="utf-8",
    )

    summary = _operator_card_atlas_summary(tmp_path)

    assert summary["status"] == "stale"
    assert summary["routing_mode"] == "lexical_fallback"
    assert summary["semantic_deployed"] is False
    assert summary["next_command"] == "make move-card-atlas-build"
    assert summary["extra_card_ids"] == ["OP-OLD"]


def test_graph_capability_audit_markdown_surfaces_operator_card_atlas_state() -> None:
    report = build_graph_capability_audit()
    markdown = render_markdown(report)

    assert "Operator-card atlas:" in markdown
    assert report["summary"]["operator_card_atlas_status"] in markdown
    assert report["summary"]["operator_card_routing_mode"] in markdown
