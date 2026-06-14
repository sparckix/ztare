from __future__ import annotations

import importlib.util
import json
import os
import time
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
MODULE = REPO / "scripts/public/control/rd_tick_brief.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("rd_tick_brief_for_test", MODULE)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_workbench_router_surface_recommends_autoresearch_for_ready_surface(capsys) -> None:
    module = _load_module()

    rc = module.autoresearch_workbench_router_surface(
        task="bounded theorem-attempt discriminator",
        project="ns_proofsearch_resupply_pincer",
        rubric="ns_proofsearch_resupply_pincer",
        subscription_worker_available=True,
    )

    out = capsys.readouterr().out
    assert rc == 0
    assert "decision=invoke_autoresearch" in out
    assert "OP-AWR-01: Autoresearch Workbench Routing" in out
    assert "ztare autoresearch run --project ns_proofsearch_resupply_pincer" in out
    assert "ztare autoresearch projection --project ns_proofsearch_resupply_pincer" in out
    assert "workbench_evidence_ref=<autoresearch-run-or-projection-artifact>" in out
    assert "ztare autoresearch route" in out
    assert "ztare action-intel record-agentic-route" in out
    assert "--route-json /tmp/autoresearch_route.json --decision-id DECISION_ID" in out
    assert "--selected-action run_out_of_loop_agent" in out


def test_workbench_router_surface_logs_prepare_surface_action(capsys) -> None:
    module = _load_module()

    rc = module.autoresearch_workbench_router_surface(
        task="bounded discriminator but no project artifact yet",
    )

    out = capsys.readouterr().out
    assert rc == 0
    assert "decision=prepare_autoresearch_surface" in out
    assert "missing-surface scaffold:" in out
    assert "stable_evaluator" in out
    assert "ztare action-intel record-agentic-route" in out
    assert "--selected-action prepare_autoresearch_surface" in out


def test_workbench_router_surface_logs_stay_out_action(capsys) -> None:
    module = _load_module()

    rc = module.autoresearch_workbench_router_surface(
        task="exploratory agenda brainstorm",
    )

    out = capsys.readouterr().out
    assert rc == 0
    assert "decision=stay_out_of_loop" in out
    assert "first surfaces to create before rerouting:" in out
    assert "ztare action-intel record-agentic-route" in out
    assert "--selected-action stay_out_of_loop" in out


def test_workbench_router_surface_warns_when_reflexive_share_lacks_route_rows(
    tmp_path: Path,
    capsys,
) -> None:
    module = _load_module()
    module.ACTION_IMPACT_LEDGER = tmp_path / "action_impact_ledger.jsonl"
    module.BIFURCATION_REPORT = tmp_path / "bifurcation_report.json"
    module.ACTION_IMPACT_LEDGER.write_text("", encoding="utf-8")
    module.BIFURCATION_REPORT.write_text(
        json.dumps(
            {
                "bifurcation": {
                    "agent_work_share": 0.803,
                    "agent_work_artifacts": 34670,
                    "iter_loop_artifacts": 8508,
                }
            }
        ),
        encoding="utf-8",
    )

    rc = module.autoresearch_workbench_router_surface(
        task="bounded theorem-attempt discriminator",
        project="ns_proofsearch_resupply_pincer",
        rubric="ns_proofsearch_resupply_pincer",
        subscription_worker_available=True,
    )

    out = capsys.readouterr().out
    assert rc == 0
    assert "route logging coverage:" in out
    assert "status=missing_route_rows_for_high_out_of_loop_share" in out
    assert "ATTENTION: reflexive mining shows substantial out-of-loop work" in out


def test_eigenquestion_rotation_surface_reports_pending_proposal(
    tmp_path: Path,
    capsys,
) -> None:
    module = _load_module()
    module.REPO = tmp_path
    project = tmp_path / "projects" / "demo_project"
    project.mkdir(parents=True)
    charter = project / "project_charter.md"
    proposal = project / "proposed_eigenquestion_20260612T000000Z.md"
    charter.write_text("## Eigenquestion\n\nold\n", encoding="utf-8")
    proposal.write_text("# Proposed Eigenquestion\n\nnew\n", encoding="utf-8")
    old = time.time() - 7200
    new = time.time() - 60
    os.utime(charter, (old, old))
    os.utime(proposal, (new, new))

    rc = module.eigenquestion_rotation_surface("demo_project")

    out = capsys.readouterr().out
    assert rc == 0
    assert "pending_newer_than_charter=1" in out
    assert "pending_review" in out
    assert "ztare eigenquestion validate --project demo_project" in out


def test_eigenquestion_rotation_surface_skips_without_project(capsys) -> None:
    module = _load_module()

    rc = module.eigenquestion_rotation_surface(None)

    out = capsys.readouterr().out
    assert rc == 0
    assert "status: skipped" in out
    assert "--autoresearch-project" in out
