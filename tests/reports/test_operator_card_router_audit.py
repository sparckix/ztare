from __future__ import annotations

import json
from pathlib import Path

from ztare.reports.operator_card_router_audit import (
    CASES,
    build_operator_card_router_audit,
    render_markdown,
)
from ztare.research_director.primitive_operator_cards import (
    CARDS,
    operator_card_atlas_freshness,
    operator_card_catalog_entries,
)


def test_operator_card_router_audit_covers_all_current_cards() -> None:
    expected = {case.expected_card_id for case in CASES}
    actual = {card.card_id for card in CARDS}

    assert expected == actual


def test_operator_card_router_audit_routes_fixed_paraphrases() -> None:
    report = build_operator_card_router_audit()

    assert report["schema"] == "ztare-move-card-router-audit-v1"
    summary = report["summary"]
    assert summary["case_count"] == 13
    assert summary["mode"] == "deterministic_lexical"
    assert summary["semantic_requested"] is False
    assert summary["semantic_exercised"] is False
    assert summary["semantic_error_count"] == 0
    assert summary["semantic_atlas_status"] in {"absent", "fresh"}
    assert summary["semantic_audit_next_command"] == (
        "make move-card-router-audit SEMANTIC=1 STRICT=1"
    )
    assert summary["ok"] is True
    assert summary["primary_failures"] == []
    assert summary["top_n_failures"] == []


def test_operator_card_router_audit_rejects_stale_semantic_atlas(tmp_path: Path, monkeypatch) -> None:
    import ztare.reports.operator_card_router_audit as audit

    atlas_path = tmp_path / "operator_card_atlas_embeddings.json"
    manifest_path = tmp_path / "operator_card_atlas_manifest.json"
    atlas_path.write_text(
        json.dumps(
            {
                "model": "gemini-embedding-001",
                "dimensions": 768,
                "size": 1,
                "meta": {"operator_card:OP-OLD:deadbeef": {"card_id": "OP-OLD"}},
                "embeddings": [{"id": "operator_card:OP-OLD:deadbeef", "embedding": [0.1]}],
            }
        ),
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps({"size": 1, "source": "ztare.research_director.primitive_operator_cards"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(audit, "OPERATOR_CARD_ATLAS_PATH", atlas_path)
    monkeypatch.setattr(
        audit,
        "operator_card_atlas_freshness",
        lambda: operator_card_atlas_freshness(
            atlas_path=atlas_path,
            manifest_path=manifest_path,
        ),
    )

    report = build_operator_card_router_audit()
    summary = report["summary"]

    assert summary["semantic_atlas_status"] == "stale"
    assert summary["semantic_atlas_fresh"] is False
    assert summary["ok"] is False
    assert report["semantic_atlas_contract"]["extra_card_ids"] == ["OP-OLD"]


def test_operator_card_router_audit_accepts_fresh_semantic_atlas(tmp_path: Path, monkeypatch) -> None:
    import ztare.reports.operator_card_router_audit as audit

    rows = operator_card_catalog_entries()
    atlas_path = tmp_path / "operator_card_atlas_embeddings.json"
    manifest_path = tmp_path / "operator_card_atlas_manifest.json"
    atlas_path.write_text(
        json.dumps(
            {
                "model": "gemini-embedding-001",
                "dimensions": 768,
                "size": len(rows),
                "meta": {row["id"]: {"card_id": row["card_id"]} for row in rows},
                "embeddings": [{"id": row["id"], "embedding": [0.1]} for row in rows],
            }
        ),
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps(
            {
                "size": len(rows),
                "source": "ztare.research_director.primitive_operator_cards",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(audit, "OPERATOR_CARD_ATLAS_PATH", atlas_path)
    monkeypatch.setattr(
        audit,
        "operator_card_atlas_freshness",
        lambda: operator_card_atlas_freshness(
            atlas_path=atlas_path,
            manifest_path=manifest_path,
        ),
    )

    report = build_operator_card_router_audit()
    summary = report["summary"]

    assert summary["semantic_atlas_status"] == "fresh"
    assert summary["semantic_atlas_fresh"] is True
    assert summary["ok"] is True


def test_operator_card_router_audit_surfaces_semantic_failures(monkeypatch) -> None:
    import ztare.reports.operator_card_router_audit as audit

    def failing_router(**_kwargs):
        raise RuntimeError("provider failed for key sk-secret-value")

    monkeypatch.setattr(audit, "route_operator_cards_semantic", failing_router)

    report = build_operator_card_router_audit(semantic_live=True)
    summary = report["summary"]

    assert summary["mode"] == "semantic_live"
    assert summary["semantic_error_count"] == summary["case_count"]
    assert summary["semantic_exercised"] is False
    assert summary["ok"] is False
    assert report["cases"][0]["route_mode"] == "semantic_error_lexical_fallback"
    assert "[redacted]" in report["cases"][0]["semantic_error"]
    assert "sk-secret-value" not in report["cases"][0]["semantic_error"]


def test_operator_card_router_audit_keeps_semantic_boundary_conservative() -> None:
    report = build_operator_card_router_audit()
    verdict = report["verdict"]

    assert verdict["deterministic_router_is_baseline"] is True
    assert verdict["semantic_router_is_advisory"] is True
    assert "not evidence that the move-card taxonomy is complete" in verdict["release_boundary"]
    assert "miss logging" in verdict["needs_before_stronger_claim"]


def test_operator_card_router_markdown_surfaces_summary() -> None:
    report = build_operator_card_router_audit()
    markdown = render_markdown(report)

    assert "# Operator-Card Router Audit" in markdown
    assert "Primary pass: 13/13" in markdown
    assert "Semantic exercised: False" in markdown
    assert "make move-card-router-audit SEMANTIC=1 STRICT=1" in markdown
    assert "graph_diagnostic_carrier" in markdown
