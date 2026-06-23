from __future__ import annotations

import json
from pathlib import Path

from ztare.reports.autoresearch_carrier_replay import build_carrier_replay, main


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _complete_eval_row(
    *,
    iteration: int,
    score: int,
    weakest_point: str,
    artifact: str,
) -> dict:
    return {
        "iteration": iteration,
        "score": score,
        "weakest_point": weakest_point,
        "timestamp": f"2026-06-20T00:0{iteration}:00Z",
        "artifact_refs": [artifact],
        "worker_archetype": "bounded_worker",
        "worker_capability": "llm",
        "worker_state": "fresh_context",
        "worker_identity": f"worker_{iteration}",
        "transport": "api",
    }


def test_carrier_replay_audits_clean_latest_only_and_stale_projects(tmp_path: Path):
    repo = tmp_path
    stable = repo / "projects" / "stable_project"
    stable_artifact = "projects/stable_project/workspace/evidence.md"
    _write_jsonl(
        stable / "workspace" / "eval_history.jsonl",
        [
            _complete_eval_row(
                iteration=1,
                score=10,
                weakest_point="First candidate still needs an independent source check.",
                artifact=stable_artifact,
            ),
            _complete_eval_row(
                iteration=2,
                score=15,
                weakest_point="Second candidate keeps the source check but needs holdout.",
                artifact=stable_artifact,
            ),
        ],
    )
    _write_json(
        stable / "workspace" / "latest_eval_results.json",
        {
            "iteration": 2,
            "score": 15,
            "weakest_point": "Second candidate keeps the source check but needs holdout.",
            "timestamp": "2026-06-20T00:02:00Z",
        },
    )
    _write_jsonl(
        repo / "analytics/public/ledgers/action_intelligence/action_impact_ledger.jsonl",
        [
            {
                "action_impact_id": "ai_stable_001",
                "selected_action": "run_autoresearch_projection",
                "decision_point": {
                    "decision_id": "stable_projection",
                    "project_id": "stable_project",
                },
                "context_features": {"project_family": "stable_project"},
                "source_refs": {"source_refs": [stable_artifact]},
            }
        ],
    )

    latest_only = repo / "projects" / "latest_only_project"
    _write_json(
        latest_only / "latest_eval_results.json",
        {
            "iteration": 0,
            "score": 41,
            "weakest_point": "Latest result exists before history materialization.",
            "gate_failure_count": 1,
            "failed_gate_ids": ["history_materialization_missing"],
            "timestamp": "2026-06-20T00:00:00Z",
        },
    )

    stale = repo / "projects" / "stale_history_project"
    _write_jsonl(
        stale / "workspace" / "eval_history.jsonl",
        [
            _complete_eval_row(
                iteration=1,
                score=20,
                weakest_point="Earlier source gap.",
                artifact="projects/stale_history_project/workspace/evidence.md",
            )
        ],
    )
    _write_json(
        stale / "latest_eval_results.json",
        {
            "iteration": 2,
            "score": 55,
            "weakest_point": "New latest eval is not in history yet.",
            "timestamp": "2026-06-20T00:10:00Z",
        },
    )

    mixed_legacy = repo / "projects" / "mixed_legacy_project"
    _write_jsonl(
        mixed_legacy / "workspace" / "eval_history.jsonl",
        [
            {
                "iteration": 1,
                "score": 5,
                "weakest_point": "Legacy row before artifact refs existed.",
                "timestamp": "2026-06-19T00:01:00Z",
                "worker_archetype": "bounded_worker",
                "worker_capability": "llm",
                "worker_state": "fresh_context",
                "worker_identity": "legacy_worker",
                "transport": "api",
            },
            _complete_eval_row(
                iteration=2,
                score=12,
                weakest_point="Current row has the carrier fields.",
                artifact="projects/mixed_legacy_project/workspace/evidence.md",
            ),
        ],
    )
    _write_json(
        mixed_legacy / "workspace" / "latest_eval_results.json",
        {
            "iteration": 2,
            "score": 12,
            "weakest_point": "Current row has the carrier fields.",
            "timestamp": "2026-06-20T00:02:00Z",
        },
    )

    report = build_carrier_replay(
        repo=repo,
        projects=[
            "stable_project",
            "latest_only_project",
            "stale_history_project",
            "mixed_legacy_project",
        ],
    )

    assert report["schema"] == "ztare-autoresearch-carrier-replay-v1"
    assert report["summary"]["project_count"] == 4
    assert report["summary"]["ok_count"] == 1
    assert report["summary"]["attention_count"] == 3
    assert report["summary"]["error_count"] == 0
    assert report["summary"]["current_carrier_complete_count"] == 3
    assert report["summary"]["current_carrier_missing_count"] == 0
    rows = {row["project"]: row for row in report["projects"]}

    stable_row = rows["stable_project"]
    assert stable_row["status"] == "ok"
    assert stable_row["node_count"] == 2
    assert stable_row["latest_eval_status"] == "covered_by_eval_history"
    assert stable_row["current_carrier"]["status"] == "complete"
    assert stable_row["action_intelligence_link_count"] == 2
    assert stable_row["missing_carrier_fields"]["artifact_refs"] == 0
    assert stable_row["missing_carrier_fields"]["transport"] == 0
    assert stable_row["next_action"] == "none"

    latest_row = rows["latest_only_project"]
    assert latest_row["status"] == "attention"
    assert latest_row["node_count"] == 0
    assert latest_row["latest_eval_status"] == "latest_eval_without_eval_history"
    assert latest_row["current_carrier"]["status"] == "no_projection_nodes"
    assert latest_row["next_action"] == "append_latest_eval_to_eval_history_or_replay_iteration"

    stale_row = rows["stale_history_project"]
    assert stale_row["status"] == "attention"
    assert stale_row["latest_eval_status"] == "latest_eval_not_in_eval_history"
    assert stale_row["current_carrier"]["status"] == "complete"
    assert stale_row["next_action"] == "replay_or_append_latest_eval_before_using_projection"

    mixed_row = rows["mixed_legacy_project"]
    assert mixed_row["status"] == "attention"
    assert mixed_row["latest_eval_status"] == "covered_by_eval_history"
    assert mixed_row["current_carrier"]["status"] == "complete"
    assert mixed_row["missing_carrier_fields"]["artifact_refs"] == 1
    assert mixed_row["next_action"] == "legacy_carrier_backfill_optional_current_rows_ok"


def test_carrier_replay_reports_missing_project_as_error(tmp_path: Path):
    report = build_carrier_replay(repo=tmp_path, projects=["missing_project"])

    assert report["summary"]["error_count"] == 1
    row = report["projects"][0]
    assert row["project"] == "missing_project"
    assert row["status"] == "error"
    assert row["next_action"] == "repair_or_restore_eval_history"


def test_carrier_replay_cli_strict_exits_on_attention(
    tmp_path: Path,
    capsys,
):
    project = tmp_path / "projects" / "latest_only_project"
    _write_json(
        project / "latest_eval_results.json",
        {
            "iteration": 0,
            "score": 41,
            "weakest_point": "Latest result exists before history materialization.",
        },
    )

    exit_code = main([
        "--repo",
        str(tmp_path),
        "--project",
        "latest_only_project",
        "--strict",
    ])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "latest_eval_without_eval_history" in captured.out
