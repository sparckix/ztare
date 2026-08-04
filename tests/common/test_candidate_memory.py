from __future__ import annotations

import hashlib
import json

from ztare.common.candidate_memory import admissible_candidate_memory_records


def test_candidate_memory_separates_behavior_and_task_artifact_roles(tmp_path) -> None:
    submissions = tmp_path / "workspace" / "submissions"
    submissions.mkdir(parents=True)
    behavior = submissions / "behavior.py"
    behavior.write_text(
        "def step(grid, action, t):\n    return grid\n",
        encoding="utf-8",
    )
    behavior_sha = hashlib.sha256(behavior.read_bytes()).hexdigest()
    task = submissions / "task.py"
    task.write_text(
        "TASK_HYPOTHESIS_PROVENANCE = {"
        "'schema': 'ztare-task-hypothesis-companion-v1'}\n"
        f"PATCH_BASE = {{'source_ref': 'workspace/submissions/behavior.py', "
        f"'sha256': '{behavior_sha}'}}\n"
        "def PATCH_DELTA(base_next, state, action):\n    return base_next\n"
        "def GOAL_PREDICATE(state):\n    return False\n",
        encoding="utf-8",
    )
    records = [
        {
            "source_type": "full_survivor",
            "artifact_role": "behavior_carrier",
            "submission": "workspace/submissions/behavior.py",
            "sha": behavior_sha,
        },
        {
            "source_type": "full_survivor",
            "artifact_role": "task_hypothesis",
            "submission": "workspace/submissions/task.py",
            "sha": hashlib.sha256(task.read_bytes()).hexdigest(),
        },
    ]

    behavior_rows = admissible_candidate_memory_records(tmp_path, records)
    task_rows = admissible_candidate_memory_records(
        tmp_path,
        records,
        artifact_roles={"task_hypothesis"},
    )

    assert [row["artifact_role"] for row in behavior_rows] == ["behavior_carrier"]
    assert [row["artifact_role"] for row in task_rows] == ["task_hypothesis"]


def test_candidate_memory_accepts_legacy_patch_base_prefix_chain(tmp_path) -> None:
    submissions = tmp_path / "workspace" / "submissions"
    submissions.mkdir(parents=True)
    base = submissions / "base.py"
    base.write_text("def step(grid, action, t):\n    return grid\n", encoding="utf-8")
    digest = hashlib.sha256(base.read_bytes()).hexdigest()
    candidate = submissions / "candidate.py"
    candidate.write_text(
        'PATCH_BASE = {"source_ref":"workspace/submissions/base.py",'
        f'"sha256":"{digest[:12]}"}}\n'
        "def PATCH_DELTA(base_next, state, action):\n"
        "    return base_next\n",
        encoding="utf-8",
    )

    rows = admissible_candidate_memory_records(
        tmp_path,
        [
            {
                "source_type": "deterministic_near_miss",
                "submission": "workspace/submissions/candidate.py",
            }
        ],
    )

    assert len(rows) == 1


def test_candidate_memory_allows_patch_base_full_digest_chain(tmp_path) -> None:
    submissions = tmp_path / "workspace" / "submissions"
    submissions.mkdir(parents=True)
    base = submissions / "base.py"
    base.write_text("def step(grid, action, t):\n    return grid\n", encoding="utf-8")
    digest = hashlib.sha256(base.read_bytes()).hexdigest()
    candidate = submissions / "candidate.py"
    candidate.write_text(
        'PATCH_BASE = {"source_ref":"workspace/submissions/base.py",'
        f'"sha256":"{digest}"}}\n'
        "def PATCH_DELTA(base_next, state, action):\n"
        "    return base_next\n",
        encoding="utf-8",
    )

    rows = admissible_candidate_memory_records(
        tmp_path,
        [
            {
                "source_type": "deterministic_near_miss",
                "submission": "workspace/submissions/candidate.py",
            }
        ],
    )

    assert len(rows) == 1


def test_candidate_memory_uses_project_transition_contract_for_patch_chain(tmp_path) -> None:
    project = tmp_path / "projects" / "demo"
    submissions = project / "workspace" / "submissions"
    submissions.mkdir(parents=True)
    rubrics = tmp_path / "rubrics"
    rubrics.mkdir()
    (rubrics / "demo.json").write_text(
        '{"dynamics_assumption":"lawful_time"}\n',
        encoding="utf-8",
    )
    base = submissions / "base.py"
    base.write_text(
        "def step(grid, action, t):\n"
        "    return grid if t >= 0 else grid\n",
        encoding="utf-8",
    )
    digest = hashlib.sha256(base.read_bytes()).hexdigest()
    candidate = submissions / "candidate.py"
    candidate.write_text(
        'PATCH_BASE = {"source_ref":"workspace/submissions/base.py",'
        f'"sha256":"{digest}"}}\n'
        "def PATCH_DELTA(base_next, state, action):\n"
        "    return base_next\n",
        encoding="utf-8",
    )

    rows = admissible_candidate_memory_records(
        project,
        [
            {
                "source_type": "deterministic_near_miss",
                "submission": "workspace/submissions/candidate.py",
            }
        ],
    )

    assert len(rows) == 1


def test_candidate_memory_shorter_prefix_survivor_is_historical_after_refutation(
    tmp_path,
) -> None:
    submissions = tmp_path / "workspace" / "submissions"
    submissions.mkdir(parents=True)
    candidate = submissions / "same.py"
    candidate.write_text("def step(grid, action, t):\n    return grid\n", encoding="utf-8")
    records = [
        {
            "source_type": "full_survivor",
            "submission": "workspace/submissions/same.py",
            "sha": "same-carrier",
            "visible_exact_rows": 10,
            "visible_checked_rows": 10,
            "observed_at_utc": "2026-07-12T00:00:00+00:00",
        },
        {
            "source_type": "deterministic_near_miss",
            "submission": "workspace/submissions/same.py",
            "sha": "same-carrier",
            "visible_exact_rows": 10,
            "visible_checked_rows": 11,
            "observed_at_utc": "2026-07-12T00:01:00+00:00",
        },
    ]

    active = admissible_candidate_memory_records(tmp_path, records)

    assert len(active) == 1
    assert active[0]["source_type"] == "deterministic_near_miss"
    assert active[0]["visible_checked_rows"] == 11


def test_candidate_memory_keeps_newest_evidence_with_content_addressed_source(
    tmp_path,
) -> None:
    submissions = tmp_path / "workspace" / "submissions"
    submissions.mkdir(parents=True)
    source = "def step(grid, action, t):\n    return grid\n"
    (submissions / "same.py").write_text(source, encoding="utf-8")
    (tmp_path / "test_model.py").write_text(source, encoding="utf-8")
    records = [
        {
            "source_type": "full_survivor",
            "submission": "workspace/submissions/same.py",
            "sha": "same-carrier",
            "visible_exact_rows": 10,
            "visible_checked_rows": 11,
            "observed_at_utc": "2026-07-12T00:01:00+00:00",
        },
        {
            "source_type": "deterministic_near_miss",
            "submission": "test_model.py",
            "sha": "same-carrier",
            "visible_exact_rows": 12,
            "visible_checked_rows": 13,
            "observed_at_utc": "2026-07-12T00:02:00+00:00",
        },
    ]

    active = admissible_candidate_memory_records(
        tmp_path,
        records,
        require_submission_source=True,
    )

    assert len(active) == 1
    assert active[0]["visible_checked_rows"] == 13
    assert active[0]["submission"] == "workspace/submissions/same.py"


def test_candidate_memory_requires_materialized_submission_source(tmp_path) -> None:
    record = {
        "source_type": "full_survivor",
        "submission": "workspace/submissions/missing.py",
        "sha": "abc123abc123",
        "source_excerpt": "def step(state, action): return state\n",
    }

    assert admissible_candidate_memory_records(
        tmp_path,
        [record],
        require_submission_source=True,
    ) == []


def test_candidate_memory_preserves_but_does_not_select_invalidated_identity(tmp_path) -> None:
    submissions = tmp_path / "workspace" / "submissions"
    submissions.mkdir(parents=True)
    candidate = submissions / "assisted.py"
    candidate.write_text("def step(grid, action, t):\n    return grid\n", encoding="utf-8")
    (tmp_path / "workspace" / "candidate_invalidations.jsonl").write_text(
        json.dumps(
            {
                "schema": "ztare-candidate-invalidation-v1",
                "candidate_sha256": "abc123",
                "selection_forbidden": True,
                "reason": "conductor_authored_diagnostic",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    records = [
        {
            "source_type": "full_survivor",
            "submission": "workspace/submissions/assisted.py",
            "sha": "abc123",
            "visible_exact_rows": 10,
            "visible_checked_rows": 10,
        }
    ]

    assert admissible_candidate_memory_records(tmp_path, records) == []


def test_candidate_memory_uses_declared_epoch_not_replay_row_extent(
    tmp_path,
) -> None:
    from ztare.common.observation_chart import capture_project_evidence_epoch

    submissions = tmp_path / "workspace" / "submissions"
    submissions.mkdir(parents=True)
    old = submissions / "old.py"
    current = submissions / "current.py"
    old.write_text("def step(grid, action, t):\n    return grid\n# old\n", encoding="utf-8")
    current.write_text("def step(grid, action, t):\n    return grid\n# current\n", encoding="utf-8")
    current_epoch = capture_project_evidence_epoch(tmp_path).epoch_sha256
    records = [
        {
            "source_type": "full_survivor",
            "submission": "workspace/submissions/old.py",
            "sha": hashlib.sha256(old.read_bytes()).hexdigest(),
            "evidence_epoch_sha256": "a" * 64,
            "visible_exact_rows": 10,
            "visible_checked_rows": 10_000,
        },
        {
            "source_type": "deterministic_near_miss",
            "submission": "workspace/submissions/current.py",
            "sha": hashlib.sha256(current.read_bytes()).hexdigest(),
            "evidence_epoch_sha256": current_epoch,
            "visible_exact_rows": 10,
            "visible_checked_rows": 11,
        },
    ]

    active = admissible_candidate_memory_records(tmp_path, records)

    assert [row["sha"] for row in active] == [
        hashlib.sha256(current.read_bytes()).hexdigest()
    ]


def test_candidate_memory_joins_current_evaluation_policy(
    monkeypatch,
    tmp_path,
) -> None:
    from ztare.common.observation_chart import capture_project_evidence_epoch

    submissions = tmp_path / "workspace" / "submissions"
    submissions.mkdir(parents=True)
    candidate = submissions / "candidate.py"
    candidate.write_text("def step(grid, action, t):\n    return grid\n", encoding="utf-8")
    candidate_sha = hashlib.sha256(candidate.read_bytes()).hexdigest()
    epoch = capture_project_evidence_epoch(tmp_path).epoch_sha256
    current_policy = "b" * 64
    monkeypatch.setattr(
        "ztare.validator.core.pre_judge_gate.evaluation_policy_sha256",
        lambda: current_policy,
    )
    records = [
        {
            "source_type": "full_survivor",
            "submission": "workspace/submissions/candidate.py",
            "sha": candidate_sha,
            "evidence_epoch_sha256": epoch,
            "evaluation_policy_sha256": "a" * 64,
            "visible_exact_rows": 10,
            "visible_checked_rows": 10,
        },
        {
            "source_type": "deterministic_near_miss",
            "submission": "workspace/submissions/candidate.py",
            "sha": candidate_sha,
            "evidence_epoch_sha256": epoch,
            "evaluation_policy_sha256": current_policy,
            "visible_exact_rows": 9,
            "visible_checked_rows": 10,
        },
    ]

    active = admissible_candidate_memory_records(tmp_path, records)

    assert len(active) == 1
    assert active[0]["source_type"] == "deterministic_near_miss"
    assert active[0]["evaluation_policy_sha256"] == current_policy
