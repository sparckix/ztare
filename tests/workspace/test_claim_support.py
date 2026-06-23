from __future__ import annotations

import json
from pathlib import Path

from ztare.workspace.claim_support import build_claim_support_audit


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _sha256_text(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_source(
    project: Path,
    *,
    source_id: str,
    filename: str,
    body: str,
    source_type: str = "source_evidence",
) -> dict:
    (project / "raw").mkdir(parents=True, exist_ok=True)
    (project / "raw" / filename).write_text(
        f"---\nsource_type: {source_type}\n---\n{body}\n",
        encoding="utf-8",
    )
    return {
        "source_id": source_id,
        "relative_raw_path": filename,
        "source_type": source_type,
        "sha256": _sha256_text(body.strip()),
    }


def test_claim_support_classifies_source_binding_rows(tmp_path: Path) -> None:
    project = tmp_path / "demo"
    source_1 = _write_source(
        project,
        source_id="S001",
        filename="incident.md",
        body="Directly observed fact.\n\nMore incident context.",
    )
    source_2 = _write_source(
        project,
        source_id="S002",
        filename="metrics.md",
        body="Synthesized metric fact.\n",
    )
    source_3 = _write_source(
        project,
        source_id="Q001",
        filename="question.md",
        body="Question-only planning row.",
        source_type="research_question",
    )
    _write_json(
        project / "workspace" / "source_index.json",
        {"sources": [source_1, source_2, source_3]},
    )
    _write_json(
        project / "compiled_evidence_packet.json",
        {
            "project": "demo",
            "immutable_ground_truth": [
                {"statement": "Directly observed fact.", "source_ids": ["S001"]},
                {"statement": "Synthesized fact.", "source_ids": ["S001", "S002"]},
                {"statement": "Question-only row.", "source_ids": ["Q001"]},
                {"statement": "Missing row.", "source_ids": ["S999"]},
                {"statement": "Unsourced row.", "source_ids": []},
            ],
            "numerical_ranges_and_constraints": [],
            "identified_contradictions": [],
            "epistemic_voids": [],
            "provenance": [],
            "candidate_claims_to_test": [
                {"claim": "Mixed row.", "source_ids": ["S001", "Q001"]},
            ],
        },
    )

    report = build_claim_support_audit(
        project,
        evidence_readiness={"status": "fresh"},
    )

    assert report["schema"] == "ztare-claim-support-audit-v1"
    assert report["status"] == "has_demotions"
    assert report["ok"] is True
    assert report["claim_count"] == 6
    assert report["status_counts"] == {
        "direct_source_support": 1,
        "synthesized_across_sources": 1,
        "local_or_seed_support": 1,
        "unsupported_missing_sources": 1,
        "unsupported_no_sources": 1,
        "mixed_source_support": 1,
    }
    rows = {row["claim"]: row for row in report["rows"]}
    assert rows["Directly observed fact."]["source_paths"] == ["incident.md"]
    assert rows["Synthesized fact."]["support_status"] == "synthesized_across_sources"
    assert rows["Question-only row."]["support_status"] == "local_or_seed_support"
    assert rows["Missing row."]["missing_source_ids"] == ["S999"]
    assert rows["Mixed row."]["support_status"] == "mixed_source_support"
    assert report["source_context_status_counts"] == {"verified": 3}
    assert report["source_context"]["S001"]["preview"]["text"].startswith(
        "Directly observed fact."
    )


def test_claim_support_marks_readiness_block_without_overwriting_row_status(
    tmp_path: Path,
) -> None:
    project = tmp_path / "demo"
    source_1 = _write_source(
        project,
        source_id="S001",
        filename="incident.md",
        body="Directly observed fact.",
    )
    _write_json(
        project / "workspace" / "source_index.json",
        {"sources": [source_1]},
    )
    _write_json(
        project / "compiled_evidence_packet.json",
        {
            "project": "demo",
            "immutable_ground_truth": [
                {"statement": "Directly observed fact.", "source_ids": ["S001"]},
            ],
            "numerical_ranges_and_constraints": [],
            "identified_contradictions": [],
            "epistemic_voids": [],
            "provenance": [],
            "candidate_claims_to_test": [],
        },
    )

    report = build_claim_support_audit(
        project,
        evidence_readiness={"status": "blocked"},
    )

    assert report["status"] == "blocked_by_evidence_readiness"
    assert report["rows"][0]["support_status"] == "direct_source_support"


def test_claim_support_blocks_stale_source_context(tmp_path: Path) -> None:
    project = tmp_path / "demo"
    source_1 = _write_source(
        project,
        source_id="S001",
        filename="incident.md",
        body="Original fact.",
    )
    _write_json(
        project / "workspace" / "source_index.json",
        {"sources": [source_1]},
    )
    (project / "raw" / "incident.md").write_text(
        "---\nsource_type: source_evidence\n---\nEdited fact.\n",
        encoding="utf-8",
    )
    _write_json(
        project / "compiled_evidence_packet.json",
        {
            "project": "demo",
            "immutable_ground_truth": [
                {"statement": "Original fact.", "source_ids": ["S001"]},
            ],
            "numerical_ranges_and_constraints": [],
            "identified_contradictions": [],
            "epistemic_voids": [],
            "candidate_claims_to_test": [],
        },
    )

    report = build_claim_support_audit(
        project,
        evidence_readiness={"status": "fresh"},
    )

    assert report["status"] == "blocked_by_source_context"
    assert report["ok"] is False
    assert report["source_context_status_counts"] == {"hash_mismatch": 1}
    assert report["rows"][0]["support_status"] == "direct_source_support"
