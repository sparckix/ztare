from __future__ import annotations

import json
import sys
from pathlib import Path

from src.ztare.validator.core.pre_judge_gate import run_pre_judge_gate_harness


def _write_harness(project: Path, body: str) -> None:
    (project / "gate_harness.py").write_text(body, encoding="utf-8")


def test_pre_judge_gate_flag_absent_is_noop_even_if_harness_exists(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    latest = project / "latest_eval_results.json"
    _write_harness(
        project,
        "raise SystemExit('this harness must not run when flag is absent')\n",
    )

    result = run_pre_judge_gate_harness(
        enabled=False,
        project_dir=project,
        latest_eval_results_path=latest,
        python_executable=sys.executable,
    )

    assert result.enabled is False
    assert result.ran is False
    assert result.should_skip_judge is False
    assert not latest.exists()


def test_pre_judge_gate_pass_allows_judge_path(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    latest = project / "latest_eval_results.json"
    _write_harness(
        project,
        (
            "import json\n"
            "print(json.dumps({\n"
            "  'harness_ok': True,\n"
            "  'gates': [{'name': 'holdout', 'value': 'pass', 'threshold': 'x', "
            "'operator': 'must_satisfy', 'passed': True}]\n"
            "}))\n"
        ),
    )

    result = run_pre_judge_gate_harness(
        enabled=True,
        project_dir=project,
        latest_eval_results_path=latest,
        python_executable=sys.executable,
    )

    assert result.ran is True
    assert result.should_skip_judge is False
    assert result.message == "✅ Pre-judge gate harness passed."
    assert not latest.exists()


def test_pre_judge_gate_uses_candidate_snapshot_path(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    latest = project / "latest_eval_results.json"
    live_candidate = project / "test_model.py"
    snapshot_candidate = project / "workspace" / "submissions" / "iter_001.py"
    snapshot_candidate.parent.mkdir(parents=True)
    live_candidate.write_text("LIVE_FAIL\n", encoding="utf-8")
    snapshot_candidate.write_text("SNAPSHOT_PASS\n", encoding="utf-8")
    _write_harness(
        project,
        (
            "import argparse, json\n"
            "from pathlib import Path\n"
            "parser = argparse.ArgumentParser()\n"
            "parser.add_argument('--emit-deterministic-gates', action='store_true')\n"
            "parser.add_argument('--candidate-path', default='test_model.py')\n"
            "args = parser.parse_args()\n"
            "source = Path(args.candidate_path).read_text()\n"
            "passed = 'SNAPSHOT_PASS' in source\n"
            "print(json.dumps({\n"
            "  'harness_ok': True,\n"
            "  'gates': [{'name': 'HOLDOUT', 'value': args.candidate_path, "
            "'threshold': 'snapshot', 'operator': 'must_satisfy', "
            "'passed': passed}]\n"
            "}))\n"
        ),
    )

    result = run_pre_judge_gate_harness(
        enabled=True,
        project_dir=project,
        latest_eval_results_path=latest,
        python_executable=sys.executable,
        candidate_path=snapshot_candidate,
    )

    assert result.should_skip_judge is False
    assert result.payload is not None
    assert result.payload["gates"][0]["passed"] is True
    assert not latest.exists()


def test_pre_judge_gate_failure_writes_score_zero_and_skips_judge(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    latest = project / "latest_eval_results.json"
    _write_harness(
        project,
        (
            "import json\n"
            "print(json.dumps({\n"
            "  'harness_ok': True,\n"
            "  'gates': [{'name': 'HOLDOUT', 'value': 'bad candidate', "
            "'threshold': 'non_tautology', 'operator': 'must_satisfy', "
            "'passed': False}]\n"
            "}))\n"
        ),
    )

    result = run_pre_judge_gate_harness(
        enabled=True,
        project_dir=project,
        latest_eval_results_path=latest,
        python_executable=sys.executable,
    )

    payload = json.loads(latest.read_text(encoding="utf-8"))
    assert result.should_skip_judge is True
    assert result.score_cap_reason == "pre_judge_gate_harness_failed"
    assert payload["score"] == 0
    assert payload["score_cap_reason"] == "pre_judge_gate_harness_failed"
    assert payload["holdout_hard_gate_fired"] is True
    assert "PRE_JUDGE_HARD_GATE" in payload["weakest_point"]
    assert "bad candidate" in payload["weakest_point"]


def test_pre_judge_gate_malformed_json_fails_closed_before_judge(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    latest = project / "latest_eval_results.json"
    _write_harness(project, "print('not json')\n")

    result = run_pre_judge_gate_harness(
        enabled=True,
        project_dir=project,
        latest_eval_results_path=latest,
        python_executable=sys.executable,
    )

    payload = json.loads(latest.read_text(encoding="utf-8"))
    assert result.should_skip_judge is True
    assert result.score_cap_reason == "pre_judge_gate_harness_error"
    assert payload["score"] == 0
    assert payload["score_cap_reason"] == "pre_judge_gate_harness_error"
    assert payload["holdout_hard_gate_fired"] is True
    assert "PRE_JUDGE_HARD_GATE_ERROR" in payload["weakest_point"]


def test_pre_judge_gate_empty_gate_list_fails_closed(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    latest = project / "latest_eval_results.json"
    _write_harness(
        project,
        "import json\nprint(json.dumps({'harness_ok': True, 'gates': []}))\n",
    )

    result = run_pre_judge_gate_harness(
        enabled=True,
        project_dir=project,
        latest_eval_results_path=latest,
        python_executable=sys.executable,
    )

    payload = json.loads(latest.read_text(encoding="utf-8"))
    assert result.should_skip_judge is True
    assert payload["score_cap_reason"] == "pre_judge_gate_harness_failed"
    assert "no gates emitted" in payload["weakest_point"]
