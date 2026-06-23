from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ztare.research_director.graph_carrier_actions import graph_carrier_action_rows
from ztare.validator import source_claim_graph_carrier
from ztare.validator.source_claim_graph_carrier import (
    build_source_claim_graph_carrier,
    summarize_source_claim_graph_carrier,
)
from ztare.workspace.evidence_gaps import evidence_gap_fingerprint


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _source_row(project: Path, *, body: str = "source claim") -> dict:
    return {
        "source_id": "S001",
        "path": "source.md",
        "relative_raw_path": "source.md",
        "source_type": "source_evidence",
        "sha256": _sha256_text(body),
        "full_sha256": _sha256_text(body),
    }


def _write_raw_source(project: Path, *, body: str = "source claim") -> None:
    (project / "raw").mkdir(parents=True, exist_ok=True)
    (project / "raw" / "source.md").write_text(
        f"---\nsource_type: source_evidence\n---\n{body}\n",
        encoding="utf-8",
    )


def _without_card_provenance(row: dict) -> dict:
    out = dict(row)
    assert out.pop("operator_card_ids") == ["OP-GDC-01"]
    routes = out.pop("operator_card_routes")
    assert len(routes) == 1
    assert routes[0]["card_id"] == "OP-GDC-01"
    assert routes[0]["route_mode"] in {"lexical_fallback", "semantic_atlas"}
    return out


def test_source_claim_graph_carrier_routes_active_evidence_gaps(tmp_path: Path) -> None:
    repo = tmp_path
    project = repo / "projects" / "demo"
    workspace = project / "workspace"
    _write_raw_source(project)
    _write_json(
        workspace / "source_index.json",
        {"sources": [_source_row(project)]},
    )
    _write_json(project / "compiled_evidence_provenance.json", {"sources": [_source_row(project)]})
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    _write_json(
        workspace / "latest_evidence_gaps.json",
        {"evidence_gaps": [{"id": "gap1", "severity": "degrading"}]},
    )

    carrier = build_source_claim_graph_carrier(
        project_dir=project,
        workspace_dir=workspace,
        repo=repo,
    )

    assert carrier is not None
    assert carrier["graph_id"] == "demo:source_claim_graph"
    assert carrier["graph_kind"] == "source_claim_graph"
    assert carrier["node_count"] == 3
    assert carrier["edge_count"] == 2
    assert carrier["decision_receipt"] == {
        "effect": "strategy_change",
        "route_change": "fetch or justify 1 active evidence gap(s)",
    }
    assert carrier["validation"] == {"ok": True, "errors": [], "warnings": []}
    assert summarize_source_claim_graph_carrier(carrier)["validation"]["ok"] is True


def test_source_claim_graph_carrier_demotes_stale_source_index(tmp_path: Path) -> None:
    repo = tmp_path
    project = repo / "projects" / "demo"
    workspace = project / "workspace"
    (project / "raw").mkdir(parents=True)
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\ncurrent source\n",
        encoding="utf-8",
    )
    stale_row = _source_row(project, body="old source")
    _write_json(workspace / "source_index.json", {"sources": [stale_row]})
    _write_json(project / "compiled_evidence_provenance.json", {"sources": [stale_row]})
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")

    carrier = build_source_claim_graph_carrier(
        project_dir=project,
        workspace_dir=workspace,
        repo=repo,
    )

    assert carrier is not None
    assert carrier["decision_receipt"]["effect"] == "misleading_or_noise"
    assert "source index does not verify current raw sources" in carrier[
        "decision_receipt"
    ]["reason"]
    assert carrier["diagnostics"][0]["source_index_freshness"]["status"] == "stale"
    assert carrier["validation"]["ok"] is True
    action_rows = graph_carrier_action_rows([carrier])
    assert [_without_card_provenance(row) for row in action_rows] == [
        {
            "action_type": "demote_graph_signal",
            "work_mode": "out_of_loop_review",
            "project": "demo",
            "graph_id": "demo:source_claim_graph",
            "reason": carrier["decision_receipt"]["reason"],
            "recommended_actor": "research_director",
        }
    ]


def test_source_claim_graph_carrier_blocks_when_source_preflight_unavailable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "demo"
    workspace = project / "workspace"
    (project / "raw").mkdir(parents=True)
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nsource claim\n",
        encoding="utf-8",
    )
    source_row = _source_row(project)
    _write_json(workspace / "source_index.json", {"sources": [source_row]})
    _write_json(project / "compiled_evidence_provenance.json", {"sources": [source_row]})
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")

    monkeypatch.setattr(
        source_claim_graph_carrier,
        "check_source_project",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    carrier = build_source_claim_graph_carrier(
        project_dir=project,
        workspace_dir=workspace,
        repo=repo,
    )

    assert carrier is not None
    assert carrier["decision_receipt"]["effect"] == "misleading_or_noise"
    assert "source preflight is not satisfied" in carrier["decision_receipt"]["reason"]
    assert "RuntimeError: boom" in carrier["decision_receipt"]["reason"]
    source_preflight = carrier["diagnostics"][0]["source_preflight"]
    assert source_preflight["ok"] is False
    assert source_preflight["status"] == "unavailable_for_graph_carrier"
    assert source_preflight["blocking"] == [
        "source preflight unavailable for graph carrier: RuntimeError: boom"
    ]
    assert carrier["validation"]["ok"] is True


def test_source_claim_graph_carrier_demotes_count_only_compile_provenance(
    tmp_path: Path,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "demo"
    workspace = project / "workspace"
    (project / "raw").mkdir(parents=True)
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nsource claim\n",
        encoding="utf-8",
    )
    source_row = _source_row(project)
    _write_json(workspace / "source_index.json", {"sources": [source_row]})
    _write_json(project / "compiled_evidence_provenance.json", {"source_count": 1})
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")

    carrier = build_source_claim_graph_carrier(
        project_dir=project,
        workspace_dir=workspace,
        repo=repo,
    )

    assert carrier is not None
    assert carrier["decision_receipt"]["effect"] == "misleading_or_noise"
    assert "compile provenance does not verify current raw sources" in carrier[
        "decision_receipt"
    ]["reason"]
    assert carrier["diagnostics"][0]["compile_freshness"]["status"] == (
        "unverified_no_artifact_sources"
    )
    assert carrier["validation"]["ok"] is True


def test_source_claim_graph_carrier_records_no_strategy_change(tmp_path: Path) -> None:
    repo = tmp_path
    project = repo / "projects" / "demo"
    workspace = project / "workspace"
    _write_raw_source(project)
    _write_json(
        workspace / "source_index.json",
        {"sources": [_source_row(project)]},
    )
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    _write_json(workspace / "latest_evidence_gaps.json", {"evidence_gaps": []})

    carrier = build_source_claim_graph_carrier(
        project_dir=project,
        workspace_dir=workspace,
        repo=repo,
    )

    assert carrier is not None
    assert carrier["decision_receipt"] == {
        "effect": "no_strategy_change",
        "reason": "source/evidence chain present with no active evidence gaps",
    }
    assert carrier["validation"]["ok"] is True


def test_source_claim_graph_carrier_routes_weak_claim_support(tmp_path: Path) -> None:
    repo = tmp_path
    project = repo / "projects" / "demo"
    workspace = project / "workspace"
    _write_raw_source(project)
    _write_json(
        workspace / "source_index.json",
        {"sources": [_source_row(project)]},
    )
    _write_json(project / "compiled_evidence_provenance.json", {"sources": [_source_row(project)]})
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    _write_json(workspace / "latest_evidence_gaps.json", {"evidence_gaps": []})
    _write_json(
        project / "compiled_evidence_packet.json",
        {
            "immutable_ground_truth": [
                {"statement": "Supported fact.", "source_ids": ["S001"]},
                {"statement": "Unsupported fact.", "source_ids": []},
            ],
            "numerical_ranges_and_constraints": [],
            "candidate_claims_to_test": [],
        },
    )

    carrier = build_source_claim_graph_carrier(
        project_dir=project,
        workspace_dir=workspace,
        repo=repo,
    )

    assert carrier is not None
    assert carrier["node_count"] == 4
    assert carrier["edge_count"] == 2
    assert carrier["decision_receipt"] == {
        "effect": "strategy_change",
        "selected_next_discriminator": (
            "repair or demote 1 weak or unsourced compiled-evidence claim row(s) "
            "before report export"
        ),
    }
    assert carrier["diagnostics"][0]["claim_support"] == {
        "status": "has_demotions",
        "claim_count": 2,
        "weak_or_unsourced_count": 1,
        "source_context_blocked_count": 0,
        "status_counts": {
            "direct_source_support": 1,
            "unsupported_no_sources": 1,
        },
        "source_context_status_counts": {"verified": 1},
    }
    assert "unsupported_no_sources" in carrier["node_vocabulary"]
    assert "source_to_compiled_claim" in carrier["edge_vocabulary"]
    assert carrier["validation"]["ok"] is True


def test_source_claim_graph_carrier_routes_stale_claim_source_context(
    tmp_path: Path,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "demo"
    workspace = project / "workspace"
    _write_raw_source(project, body="original source claim")
    source_row = _source_row(project, body="original source claim")
    _write_json(
        workspace / "source_index.json",
        {"sources": [source_row]},
    )
    _write_json(project / "compiled_evidence_provenance.json", {"sources": [source_row]})
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    _write_json(workspace / "latest_evidence_gaps.json", {"evidence_gaps": []})
    _write_json(
        project / "compiled_evidence_packet.json",
        {
            "immutable_ground_truth": [
                {"statement": "Supported fact.", "source_ids": ["S001"]},
            ],
            "numerical_ranges_and_constraints": [],
            "candidate_claims_to_test": [],
        },
    )
    _write_raw_source(project, body="edited source claim")

    carrier = build_source_claim_graph_carrier(
        project_dir=project,
        workspace_dir=workspace,
        repo=repo,
    )

    assert carrier is not None
    assert carrier["decision_receipt"] == {
        "effect": "misleading_or_noise",
        "reason": (
            "source-claim graph source index does not verify current raw sources "
            "(stale); binding contract is not satisfied; refresh source-index "
            "before graph routing"
        ),
    }
    assert carrier["diagnostics"][0]["claim_support"]["source_context_status_counts"] == {
        "hash_mismatch": 1
    }
    assert carrier["validation"]["ok"] is True


def test_source_claim_graph_carrier_ignores_inactive_evidence_gaps(tmp_path: Path) -> None:
    repo = tmp_path
    project = repo / "projects" / "demo"
    workspace = project / "workspace"
    _write_raw_source(project)
    _write_json(
        workspace / "source_index.json",
        {"sources": [_source_row(project)]},
    )
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    _write_json(
        workspace / "latest_evidence_gaps.json",
        {
            "evidence_gaps": [
                {"id": "gap1", "severity": "degrading", "status": "resolved"},
                {
                    "id": "gap2",
                    "severity": "degrading",
                    "justified_at": "2026-06-20T00:00:00Z",
                },
            ]
        },
    )

    carrier = build_source_claim_graph_carrier(
        project_dir=project,
        workspace_dir=workspace,
        repo=repo,
    )

    assert carrier is not None
    assert carrier["node_count"] == 2
    assert carrier["edge_count"] == 1
    assert carrier["decision_receipt"] == {
        "effect": "no_strategy_change",
        "reason": "source/evidence chain present with no active evidence gaps",
    }
    assert carrier["diagnostics"][0]["result_summary"] == (
        "1 source row(s), 0 active evidence gap(s), evidence_exists=True"
    )


def test_source_claim_graph_carrier_ignores_repaired_local_artifact_gap(
    tmp_path: Path,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "demo"
    workspace = project / "workspace"
    _write_raw_source(project)
    _write_json(
        workspace / "source_index.json",
        {"sources": [_source_row(project)]},
    )
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    (project / "test_model.py").write_text(
        "def I_model():\n    return 1.0\n",
        encoding="utf-8",
    )
    _write_json(
        workspace / "latest_evidence_gaps.json",
        {
            "evidence_gaps": [
                {
                    "id": "missing-suite",
                    "severity": "degrading",
                    "target": "test_model.py",
                    "description": "The falsification suite is missing.",
                }
            ]
        },
    )

    carrier = build_source_claim_graph_carrier(
        project_dir=project,
        workspace_dir=workspace,
        repo=repo,
    )

    assert carrier is not None
    assert carrier["decision_receipt"] == {
        "effect": "no_strategy_change",
        "reason": "source/evidence chain present with no active evidence gaps",
    }
    assert carrier["diagnostics"][0]["locally_resolved_gap_count"] == 1


def test_source_claim_graph_carrier_keeps_local_verification_gap_in_loop(
    tmp_path: Path,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "demo"
    workspace = project / "workspace"
    _write_raw_source(project)
    _write_json(
        workspace / "source_index.json",
        {"sources": [_source_row(project)]},
    )
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    _write_json(
        workspace / "latest_evidence_gaps.json",
        {
            "evidence_gaps": [
                {
                    "id": "next-falsifier",
                    "severity": "degrading",
                    "target": "next_falsifier_execution",
                    "description": "No evidence that the preflight executes the falsifier.",
                    "producer_rationale": "contract_enforcement",
                }
            ]
        },
    )

    carrier = build_source_claim_graph_carrier(
        project_dir=project,
        workspace_dir=workspace,
        repo=repo,
    )

    assert carrier is not None
    assert carrier["decision_receipt"] == {
        "effect": "strategy_change",
        "selected_next_discriminator": (
            "resolve 1 local verification gap(s) inside the autoresearch loop: "
            "next_falsifier_execution"
        ),
        "selected_gap_ids": ["next-falsifier"],
        "selected_targets": ["next_falsifier_execution"],
        "runtime_consumable": True,
    }
    assert carrier["diagnostics"][0]["public_evidence_gap_count"] == 0
    assert carrier["diagnostics"][0]["local_verification_gap_count"] == 1


def test_source_claim_graph_carrier_keeps_reference_integrity_gap_in_loop(
    tmp_path: Path,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "demo"
    workspace = project / "workspace"
    _write_raw_source(project)
    _write_json(
        workspace / "source_index.json",
        {"sources": [_source_row(project)]},
    )
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    _write_json(
        workspace / "latest_evidence_gaps.json",
        {
            "evidence_gaps": [
                {
                    "id": "packet-elements",
                    "severity": "degrading",
                    "target": "packet_elements",
                    "description": (
                        "No evidence that source/evidence references were actually "
                        "checked for existence and correctness beyond their being named."
                    ),
                    "producer_rationale": "Existence of labels treated as proof",
                }
            ]
        },
    )

    carrier = build_source_claim_graph_carrier(
        project_dir=project,
        workspace_dir=workspace,
        repo=repo,
    )

    assert carrier is not None
    assert carrier["decision_receipt"] == {
        "effect": "strategy_change",
        "selected_next_discriminator": (
            "resolve 1 local verification gap(s) inside the autoresearch loop: "
            "packet_elements"
        ),
        "selected_gap_ids": ["packet-elements"],
        "selected_targets": ["packet_elements"],
        "runtime_consumable": True,
    }


def test_source_claim_graph_carrier_dedupes_intake_gap_target_variants(
    tmp_path: Path,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "demo"
    workspace = project / "workspace"
    _write_raw_source(project)
    _write_json(
        workspace / "source_index.json",
        {"sources": [_source_row(project)]},
    )
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    _write_json(
        workspace / "latest_evidence_gaps.json",
        {
            "evidence_gaps": [
                {
                    "id": "chg142",
                    "severity": "degrading",
                    "target": "CHG-142 batching flag mechanism",
                    "description": "Local verifier fixture is missing.",
                    "recovery_kind": "local_verification",
                }
            ]
        },
    )

    carrier = build_source_claim_graph_carrier(
        project_dir=project,
        workspace_dir=workspace,
        repo=repo,
        intake_gap_contracts=[
            {
                "target": "chg_142_batching_flag_mechanism",
                "recovery_kind": "local_verification",
                "recovery_channel": "in_loop_focus_receipt",
                "required_surface": "fixture_row_or_local_verifier",
                "can_public_fetch": False,
                "in_loop_consumable": True,
            }
        ],
        intake_gap_contract_source="projects/demo/demo_intake.json",
    )

    assert carrier is not None
    assert carrier["diagnostics"][0]["local_verification_gap_count"] == 1
    assert carrier["decision_receipt"]["selected_gap_ids"] == ["chg142"]
    assert carrier["decision_receipt"]["selected_targets"] == [
        "CHG-142 batching flag mechanism"
    ]


def test_source_claim_graph_carrier_fingerprints_unnamed_local_gap(
    tmp_path: Path,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "demo"
    workspace = project / "workspace"
    _write_raw_source(project)
    _write_json(
        workspace / "source_index.json",
        {"sources": [_source_row(project)]},
    )
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    gap = {
        "severity": "degrading",
        "target": "test_model.py",
        "description": "No evidence that the preflight executes the falsifier.",
        "producer_rationale": "contract_enforcement",
    }
    _write_json(workspace / "latest_evidence_gaps.json", {"evidence_gaps": [gap]})

    carrier = build_source_claim_graph_carrier(
        project_dir=project,
        workspace_dir=workspace,
        repo=repo,
    )

    assert carrier is not None
    fallback_id = f"gap:{evidence_gap_fingerprint(gap)[:12]}"
    assert carrier["decision_receipt"]["selected_gap_ids"] == [fallback_id]
    action_rows = graph_carrier_action_rows([summarize_source_claim_graph_carrier(carrier)])
    assert [_without_card_provenance(row) for row in action_rows] == [
        {
            "action_type": "in_loop_focus_receipt",
            "work_mode": "in_loop",
            "project": "demo",
            "graph_id": "demo:source_claim_graph",
            "reason": "resolve 1 local verification gap(s) inside the autoresearch loop: test_model.py",
            "recommended_actor": "autoresearch_loop",
            "gap_ids": fallback_id,
            "targets": "test_model.py",
        }
    ]


def test_source_claim_graph_carrier_retires_path_gap_with_local_receipt(
    tmp_path: Path,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "demo"
    workspace = project / "workspace"
    _write_raw_source(project)
    _write_json(
        workspace / "source_index.json",
        {"sources": [_source_row(project)]},
    )
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    _write_json(
        workspace / "latest_evidence_gaps.json",
        {
            "evidence_gaps": [
                {
                    "id": "preflight-path-resolution",
                    "severity": "degrading",
                    "target": "preflight path resolution",
                    "description": (
                        "No test of malicious symlinks, ../ traversals, or circular "
                        "references that could bypass local-path checks."
                    ),
                    "producer_rationale": "Path validation must be machine-enforced.",
                    "recovery_kind": "local_verification",
                }
            ]
        },
    )
    _write_json(
        workspace / "packet_falsifier_receipt.json",
        {
            "status": "resolved",
            "path_safety": {
                "absolute_local_refs_allowed": False,
                "parent_traversal_allowed": False,
                "symlink_escape_allowed": False,
            },
        },
    )

    carrier = build_source_claim_graph_carrier(
        project_dir=project,
        workspace_dir=workspace,
        repo=repo,
    )

    assert carrier is not None
    assert carrier["decision_receipt"] == {
        "effect": "no_strategy_change",
        "reason": "source/evidence chain present with no active evidence gaps",
    }
    assert carrier["diagnostics"][0]["locally_resolved_gap_count"] == 1
    assert carrier["diagnostics"][0]["local_verification_gap_count"] == 0


def test_source_claim_graph_carrier_routes_legacy_evidence_without_index(
    tmp_path: Path,
) -> None:
    project = tmp_path / "projects" / "demo"
    _write_raw_source(project)
    (project / "evidence.txt").parent.mkdir(parents=True, exist_ok=True)
    (project / "evidence.txt").write_text("legacy evidence\n", encoding="utf-8")

    carrier = build_source_claim_graph_carrier(project_dir=project, repo=tmp_path)

    assert carrier is not None
    assert carrier["decision_receipt"] == {
        "effect": "strategy_change",
        "route_change": "run evidence-prepare to bind evidence text to source rows",
    }
    assert carrier["validation"]["ok"] is True
