from __future__ import annotations

import json
from pathlib import Path

from ztare.orchestrator.briefing_providers.tried_failed_digest import (
    TriedFailedDigestProvider,
)
from ztare.orchestrator.mutator_briefing import BriefingContext
from ztare.orchestrator.mutator_briefing import default_briefing


def _append_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_tried_failed_digest_summarizes_negative_workspace_artifacts(tmp_path: Path) -> None:
    project = tmp_path / "project"
    workspace = project / "workspace"
    r1_dir = workspace / "r1_debug"
    r1_dir.mkdir(parents=True)
    (r1_dir / "iter_001_r1_attempts.md").write_text(
        "**Rejection reason:**\n```Module-level I_model call detected during import.```\n",
        encoding="utf-8",
    )
    _append_jsonl(
        workspace / "contract_violations.jsonl",
        [{"iter": 1, "active_contract": "C", "adheres": False, "violations": ["missing_imodel_def"]}],
    )
    (workspace / "fit_result_iter_001.json").write_text(
        json.dumps(
            {
                "status": "failure",
                "failure_class": "solver_diverged",
                "solver_diagnostics": "residual plateaued after every multistart",
            }
        ),
        encoding="utf-8",
    )
    _append_jsonl(
        workspace / "eval_history.jsonl",
        [
            {"iteration": 1, "score": 40, "weakest_point": "initial"},
            {"iteration": 2, "score": 35, "weakest_point": "same boundary mismatch recurred"},
            {"iteration": 3, "score": 34, "weakest_point": "same boundary mismatch recurred"},
        ],
    )
    _append_jsonl(
        workspace / "dag_steering_log.jsonl",
        [
            {"selected_node_id": "alpha"},
            {"selected_node_id": "beta"},
            {"selected_node_id": "beta"},
        ],
    )

    provider = TriedFailedDigestProvider()
    ctx = BriefingContext(project_dir=project, workspace_dir=workspace, iter_index=3, rubric={})

    assert provider.applies(ctx) is True
    fragment = provider.fragment(ctx)

    assert "Tried-and-Failed Digest" in fragment
    assert "R1 rejected iter 1" in fragment
    assert "missing_imodel_def" in fragment
    assert "solver_diverged" in fragment
    assert "same boundary mismatch recurred" in fragment
    assert "negative constraint" in fragment
    assert "branch cues [beta]" in fragment
    assert "frontier constraint" in fragment
    assert "accepted spine is still open here" in fragment

    records = provider.structured_records(ctx)
    assert {record["source_type"] for record in records} >= {
        "r1_rejection",
        "mutation_contract_mismatch",
        "fit_failure",
        "non_improving_eval",
        "projection_negative_constraint",
        "projection_frontier_constraint",
    }
    projection_record = next(
        record
        for record in records
        if record["source_type"] == "projection_negative_constraint"
    )
    assert projection_record["action_constraint"] == "exclude_or_alter_repeated_failed_branch"
    assert projection_record["branch_cues"] == ["beta"]


def test_default_briefing_persists_negative_constraint_records(tmp_path: Path) -> None:
    project = tmp_path / "project"
    workspace = project / "workspace"
    r1_dir = workspace / "r1_debug"
    r1_dir.mkdir(parents=True)
    (r1_dir / "iter_001_r1_attempts.md").write_text(
        "**Rejection reason:**\n```Top-level schema omitted I_model.```\n",
        encoding="utf-8",
    )
    _append_jsonl(
        workspace / "eval_history.jsonl",
        [
            {"iteration": 1, "score": 40, "weakest_point": "initial"},
            {"iteration": 2, "score": 38, "weakest_point": "schema omission recurred"},
        ],
    )

    ctx = BriefingContext(project_dir=project, workspace_dir=workspace, iter_index=3, rubric={})
    body = default_briefing().render(ctx)

    assert "Tried-and-Failed Digest" in body
    records_path = workspace / "mutator_briefing_iter_003_records.json"
    records_payload = json.loads(records_path.read_text(encoding="utf-8"))
    records = records_payload["records"]
    assert records_payload["schema_version"] == 1
    assert records_payload["iter_index"] == 3
    assert any(
        record["provider"] == "tried_failed_digest"
        and record["source_type"] == "r1_rejection"
        and record["action_constraint"] == "change_contract_shape_before_retry"
        for record in records
    )
