from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ztare.orchestrator.briefing_providers.graph_focus_receipt import (
    GraphFocusReceiptProvider,
)
from ztare.orchestrator.mutator_briefing import (
    BriefingContext,
    default_briefing,
    render_default_briefing_context,
)
from ztare.workspace.evidence_gaps import evidence_gap_fingerprint


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _normalize_operator_card_routes(row: dict) -> dict:
    out = dict(row)
    routes = out.pop("operator_card_routes")
    assert len(routes) == 1
    route = routes[0]
    assert route["card_id"] == "OP-GDC-01"
    assert route["name"] == "Graph Diagnostic Carrier"
    assert route["route_mode"] in {"lexical_fallback", "semantic_atlas"}
    assert out["operator_card_ids"] == ["OP-GDC-01"]
    out["operator_card_routes"] = ["OP-GDC-01"]
    return out


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _source_row() -> dict:
    digest = _sha256_text("source claim")
    return {
        "source_id": "S001",
        "path": "source.md",
        "relative_raw_path": "source.md",
        "source_type": "source_evidence",
        "sha256": digest,
        "full_sha256": digest,
    }


def _write_raw_source(project: Path) -> None:
    (project / "raw").mkdir(parents=True, exist_ok=True)
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nsource claim\n",
        encoding="utf-8",
    )


def test_graph_focus_receipt_provider_renders_local_verification_gap(
    tmp_path: Path,
) -> None:
    project = tmp_path / "projects" / "demo"
    workspace = project / "workspace"
    _write_raw_source(project)
    _write_json(
        workspace / "source_index.json",
        {"sources": [_source_row()]},
    )
    (project / "evidence.txt").parent.mkdir(parents=True, exist_ok=True)
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    _write_json(
        workspace / "latest_evidence_gaps.json",
        {
            "evidence_gaps": [
                {
                    "id": "next-falsifier",
                    "severity": "degrading",
                    "target": "next_falsifier_execution",
                    "description": "No evidence that preflight executes the falsifier.",
                    "producer_rationale": "contract_enforcement",
                }
            ]
        },
    )
    provider = GraphFocusReceiptProvider()
    ctx = BriefingContext(project_dir=project, iter_index=2, rubric={}, workspace_dir=workspace)

    assert provider.applies(ctx) is True
    fragment = provider.fragment(ctx)

    assert "GRAPH FOCUS RECEIPT" in fragment
    assert "demo:source_claim_graph" in fragment
    assert "gap_id=next-falsifier" in fragment
    assert "next_falsifier_execution" in fragment
    assert "No evidence that preflight executes the falsifier." in fragment
    assert "Required response: encode a local discriminator in test_model.py" in fragment
    assert "assert its machine fields rather than naming the receipt file alone" in fragment
    assert "public-source fetching" in fragment
    assert [
        _normalize_operator_card_routes(row)
        for row in provider.structured_records(ctx)
    ] == [
        {
            "record_type": "graph_focus_receipt",
            "action_type": "in_loop_focus_receipt",
            "work_mode": "in_loop",
            "project": "demo",
            "graph_id": "demo:source_claim_graph",
            "reason": (
                "resolve 1 local verification gap(s) inside the autoresearch loop: "
                "next_falsifier_execution"
            ),
            "recommended_actor": "autoresearch_loop",
            "operator_card_ids": ["OP-GDC-01"],
            "operator_card_routes": ["OP-GDC-01"],
            "gap_ids": "next-falsifier",
            "targets": "next_falsifier_execution",
            "local_gap_details": [
                {
                    "gap_id": "next-falsifier",
                    "target": "next_falsifier_execution",
                    "severity": "degrading",
                    "description": "No evidence that preflight executes the falsifier.",
                    "producer": "",
                    "producer_rationale": "contract_enforcement",
                    "recovery_kind": "local_verification",
                }
            ],
            "local_verifier_receipts": [],
        }
    ]


def test_graph_focus_receipt_provider_skips_grid_submission_without_gap(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project = tmp_path / "projects" / "grid_world"
    workspace = project / "workspace"
    workspace.mkdir(parents=True)
    provider = GraphFocusReceiptProvider()
    ctx = BriefingContext(
        project_dir=project,
        iter_index=1,
        rubric={"submission_kind": "grid_dsl"},
        workspace_dir=workspace,
    )

    def explode(_ctx):
        raise AssertionError("graph actions should not compute for grid no-gap applies")

    monkeypatch.setattr(provider, "_actions", explode)

    assert provider.applies(ctx) is False


def test_graph_focus_receipt_provider_renders_packet_reference_resolution_gap(
    tmp_path: Path,
) -> None:
    project = tmp_path / "projects" / "demo"
    workspace = project / "workspace"
    _write_raw_source(project)
    _write_json(
        workspace / "source_index.json",
        {"sources": [_source_row()]},
    )
    (project / "evidence.txt").parent.mkdir(parents=True, exist_ok=True)
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    _write_json(
        workspace / "latest_evidence_gaps.json",
        {
            "evidence_gaps": [
                {
                    "severity": "degrading",
                    "target": "intake readiness",
                    "description": (
                        "Thesis commits syntactic checklist fallacy; no "
                        "demonstration that references resolve beyond naming."
                    ),
                    "producer": "meta_judge",
                }
            ]
        },
    )
    provider = GraphFocusReceiptProvider()
    ctx = BriefingContext(project_dir=project, iter_index=2, rubric={}, workspace_dir=workspace)

    fragment = provider.fragment(ctx)

    assert provider.applies(ctx) is True
    assert "intake readiness" in fragment
    assert "syntactic checklist fallacy" in fragment
    assert "Required response: encode a local discriminator in test_model.py" in fragment


def test_graph_focus_receipt_provider_fingerprints_unnamed_gap(
    tmp_path: Path,
) -> None:
    project = tmp_path / "projects" / "demo"
    workspace = project / "workspace"
    _write_raw_source(project)
    _write_json(
        workspace / "source_index.json",
        {"sources": [_source_row()]},
    )
    (project / "evidence.txt").parent.mkdir(parents=True, exist_ok=True)
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    gap = {
        "severity": "degrading",
        "target": "test_model.py",
        "description": "preflight enforcement is not proven by packet text",
        "producer": "meta_judge",
    }
    _write_json(workspace / "latest_evidence_gaps.json", {"evidence_gaps": [gap]})
    provider = GraphFocusReceiptProvider()
    ctx = BriefingContext(project_dir=project, iter_index=2, rubric={}, workspace_dir=workspace)

    fallback_id = f"gap:{evidence_gap_fingerprint(gap)[:12]}"

    assert fallback_id in provider.fragment(ctx)
    assert provider.structured_records(ctx)[0]["gap_ids"] == fallback_id
    assert provider.structured_records(ctx)[0]["local_gap_details"][0]["gap_id"] == fallback_id


def test_graph_focus_receipt_provider_surfaces_packet_falsifier_receipt(
    tmp_path: Path,
) -> None:
    project = tmp_path / "projects" / "demo"
    workspace = project / "workspace"
    _write_raw_source(project)
    _write_json(
        workspace / "source_index.json",
        {"sources": [_source_row()]},
    )
    (project / "evidence.txt").parent.mkdir(parents=True, exist_ok=True)
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    _write_json(
        workspace / "latest_evidence_gaps.json",
        {
            "evidence_gaps": [
                {
                    "severity": "degrading",
                    "target": "Preflight Routing Engine",
                    "description": "preflight enforcement is not proven by packet text",
                    "producer": "meta_judge",
                }
            ]
        },
    )
    _write_json(
        workspace / "packet_falsifier_receipt.json",
        {
            "status": "resolved",
            "command": "ztare project intake falsify --path packet.json --remove-ref 'evidence_refs[1]'",
            "remove_ref": "evidence_refs[1]",
            "removed_ref": "docs/evidence_atlas/README.md",
            "expected_failure": "evidence_refs[1] local path does not exist",
            "path_safety": {
                "absolute_local_refs_allowed": False,
                "parent_traversal_allowed": False,
                "symlink_escape_allowed": False,
            },
            "enforced_by": [
                "src/ztare/scaffold/substrate_queue.py::validate_project_packet_falsifier",
                "tests/test_substrate_queue.py::test_project_packet_falsifier_fails_when_declared_evidence_ref_is_removed",
            ],
        },
    )
    provider = GraphFocusReceiptProvider()
    ctx = BriefingContext(project_dir=project, iter_index=2, rubric={}, workspace_dir=workspace)

    fragment = provider.fragment(ctx)
    records = provider.structured_records(ctx)

    assert "Local verifier receipts available to consume" in fragment
    assert "type=project_packet_falsifier" in fragment
    assert "status=resolved" in fragment
    assert "expected_failure=evidence_refs[1] local path does not exist" in fragment
    assert "path_safety=absolute_local_refs_allowed=False" in fragment
    assert "parent_traversal_allowed=False" in fragment
    assert "symlink_escape_allowed=False" in fragment
    assert records[0]["local_verifier_receipts"] == [
        {
            "receipt_type": "project_packet_falsifier",
            "path": "workspace/packet_falsifier_receipt.json",
            "status": "resolved",
            "command": "ztare project intake falsify --path packet.json --remove-ref 'evidence_refs[1]'",
            "remove_ref": "evidence_refs[1]",
            "removed_ref": "docs/evidence_atlas/README.md",
            "expected_failure": "evidence_refs[1] local path does not exist",
            "enforced_by": [
                "src/ztare/scaffold/substrate_queue.py::validate_project_packet_falsifier",
                "tests/test_substrate_queue.py::test_project_packet_falsifier_fails_when_declared_evidence_ref_is_removed",
            ],
            "path_safety": {
                "absolute_local_refs_allowed": False,
                "parent_traversal_allowed": False,
                "symlink_escape_allowed": False,
            },
        }
    ]


def test_graph_focus_receipt_provider_renders_enabled_probability_dag_focus(
    tmp_path: Path,
) -> None:
    project = tmp_path / "projects" / "demo"
    workspace = project / "workspace"
    _write_json(
        project / "latest_probability_dag.json",
        {
            "nodes": [
                {
                    "id": "catch_rate_lift",
                    "probability": 0.7,
                    "watch_signal": "adversarial deletion catch-rate delta",
                }
            ],
            "edges": [{"from": "catch_rate_lift", "to": "outcome", "weight": 0.9}],
        },
    )
    provider = GraphFocusReceiptProvider()
    ctx = BriefingContext(
        project_dir=project,
        iter_index=2,
        rubric={"enable_dag_steering": True},
        workspace_dir=workspace,
    )

    fragment = provider.fragment(ctx)
    records = provider.structured_records(ctx)

    assert provider.applies(ctx) is True
    assert "GRAPH FOCUS RECEIPT" in fragment
    assert "demo:latest_probability_dag" in fragment
    assert "catch_rate_lift" in fragment
    assert "adversarial deletion catch-rate delta" in fragment
    assert [_normalize_operator_card_routes(row) for row in records] == [
        {
            "record_type": "graph_focus_receipt",
            "action_type": "in_loop_focus_receipt",
            "work_mode": "in_loop",
            "project": "demo",
            "graph_id": "demo:latest_probability_dag",
            "reason": (
                "DAG scoring selects node 'catch_rate_lift' as the pending "
                "in-loop focus; watch signal: adversarial deletion catch-rate delta"
            ),
            "recommended_actor": "autoresearch_loop",
            "operator_card_ids": ["OP-GDC-01"],
            "operator_card_routes": ["OP-GDC-01"],
            "local_gap_details": [],
            "local_verifier_receipts": [],
        }
    ]


def test_graph_focus_receipt_provider_respects_probability_dag_rubric_gate(
    tmp_path: Path,
) -> None:
    project = tmp_path / "projects" / "demo"
    workspace = project / "workspace"
    _write_json(
        project / "latest_probability_dag.json",
        {
            "nodes": [{"id": "n1", "probability": 0.7, "watch_signal": "source"}],
            "edges": [{"from": "n1", "to": "outcome", "weight": 0.9}],
        },
    )
    provider = GraphFocusReceiptProvider()
    ctx = BriefingContext(
        project_dir=project,
        iter_index=2,
        rubric={"enable_dag_steering": False},
        workspace_dir=workspace,
    )

    assert provider.applies(ctx) is False
    assert provider.fragment(ctx) == ""


def test_graph_focus_receipt_provider_ignores_public_fetch_gap(tmp_path: Path) -> None:
    project = tmp_path / "projects" / "demo"
    workspace = project / "workspace"
    _write_raw_source(project)
    _write_json(
        workspace / "source_index.json",
        {"sources": [_source_row()]},
    )
    (project / "evidence.txt").parent.mkdir(parents=True, exist_ok=True)
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    _write_json(
        workspace / "latest_evidence_gaps.json",
        {"evidence_gaps": [{"id": "paper", "severity": "degrading"}]},
    )
    provider = GraphFocusReceiptProvider()
    ctx = BriefingContext(project_dir=project, iter_index=2, rubric={}, workspace_dir=workspace)

    assert provider.applies(ctx) is False


def test_graph_focus_receipt_skips_targetless_local_obstruction(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project = tmp_path / "projects" / "demo"
    workspace = project / "workspace"
    _write_json(
        workspace / "latest_evidence_gaps.json",
        {
            "evidence_gaps": [
                {
                    "in_loop_consumable": True,
                    "recovery_contract": {
                        "in_loop_consumable": True,
                        "target": "",
                        "required_surface": "missing abstract selector",
                    },
                }
            ]
        },
    )
    provider = GraphFocusReceiptProvider()
    monkeypatch.setattr(
        provider,
        "_actions",
        lambda _ctx: (_ for _ in ()).throw(
            AssertionError("targetless obstruction must not build a graph")
        ),
    )
    ctx = BriefingContext(
        project_dir=project,
        iter_index=2,
        rubric={"fit_expression_grammar": "grid_dsl"},
        workspace_dir=workspace,
    )

    assert provider.applies(ctx) is False


def test_default_briefing_registers_graph_focus_provider() -> None:
    providers = {provider.name for provider in default_briefing().providers}

    assert "graph_focus_receipt" in providers


def test_default_briefing_render_persists_graph_focus_records(
    tmp_path: Path,
) -> None:
    project = tmp_path / "projects" / "demo"
    workspace = project / "workspace"
    _write_raw_source(project)
    _write_json(
        workspace / "source_index.json",
        {"sources": [_source_row()]},
    )
    (project / "evidence.txt").parent.mkdir(parents=True, exist_ok=True)
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    _write_json(
        workspace / "latest_evidence_gaps.json",
        {
            "evidence_gaps": [
                {
                    "id": "local-discriminator",
                    "severity": "degrading",
                    "target": "test_model.py",
                    "description": "No local discriminator proves packet references resolve.",
                    "producer": "meta_judge",
                }
            ]
        },
    )
    ctx = BriefingContext(
        project_dir=project,
        iter_index=4,
        rubric={},
        workspace_dir=workspace,
        mutator_model_id="kimi-k2.6",
    )

    rendered = render_default_briefing_context(ctx)

    assert "graph_focus_receipt" in rendered["active_providers"]
    assert "GRAPH FOCUS RECEIPT" in rendered["body"]
    assert rendered["diagnostics"]["structured_record_count"] == 1

    audit_path = workspace / "mutator_briefing_iter_004.md"
    records_path = workspace / "mutator_briefing_iter_004_records.json"
    assert "GRAPH FOCUS RECEIPT" in audit_path.read_text(encoding="utf-8")
    records = json.loads(records_path.read_text(encoding="utf-8"))
    assert [
        _normalize_operator_card_routes(row)
        for row in records["records"]
    ] == [
        {
            "provider": "graph_focus_receipt",
            "record_type": "graph_focus_receipt",
            "action_type": "in_loop_focus_receipt",
            "work_mode": "in_loop",
            "project": "demo",
            "graph_id": "demo:source_claim_graph",
            "reason": (
                "resolve 1 local verification gap(s) inside the autoresearch loop: "
                "test_model.py"
            ),
            "recommended_actor": "autoresearch_loop",
            "operator_card_ids": ["OP-GDC-01"],
            "operator_card_routes": ["OP-GDC-01"],
            "gap_ids": "local-discriminator",
            "targets": "test_model.py",
            "local_gap_details": [
                {
                    "gap_id": "local-discriminator",
                    "target": "test_model.py",
                    "severity": "degrading",
                    "description": (
                        "No local discriminator proves packet references resolve."
                    ),
                    "producer": "meta_judge",
                    "producer_rationale": "",
                    "recovery_kind": "local_verification",
                }
            ],
            "local_verifier_receipts": [],
        }
    ]
