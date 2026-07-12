from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from ztare.common.leaf_workbench_contract import (
    LeafWorkbenchCapability,
    LeafWorkbenchContract,
)
from ztare.validator.core.pre_judge_gate import (
    detect_patch_base_regression_preflight,
    evaluation_cache_key,
    load_cached_evaluation,
    run_pre_judge_gate_harness,
    store_cached_evaluation,
)
from ztare.validator.core.repair_preflight import ambient_carrier_dependency_retry_message
from ztare.validator.core.repair_preflight import boundary_cegar_ready_delta_retry_message
from ztare.validator.core.repair_preflight import leaf_workbench_action_request_retry_message
from ztare.validator.core.repair_preflight import leaf_workbench_retry_message
from ztare.validator.core.repair_preflight import patch_base_regression_retry_message
from ztare.validator.core.repair_preflight import (
    strategy_discharge_missing_evidence_action_retry_message,
)
from ztare.validator.core.repair_preflight import strategy_card_retry_message


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


def test_corrupt_cache_returns_typed_verdict_and_receipt(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "workspace").mkdir()
    cache = project / "workspace" / "evaluation_by_candidate_sha.json"
    cache.write_text("{not-json", encoding="utf-8")
    key = {"key_sha256": "abc123"}

    cached = load_cached_evaluation(project, key)

    assert cached is not None
    assert cached["cache_verdict"] == "corrupt_cache"
    receipt_path = project / "workspace" / "pre_judge_gate_receipts.jsonl"
    assert receipt_path.exists()
    assert "corrupt_cache" in receipt_path.read_text(encoding="utf-8")


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
    candidate = project / "test_model.py"
    candidate.write_text("def step(grid, action, t): return grid\n", encoding="utf-8")
    _write_harness(
        project,
        (
            "import json\n"
            "print(json.dumps({\n"
            "  'score': 0.3333,\n"
            "  'harness_ok': True,\n"
            "  'gates': {\n"
            "    'grid_dsl_expressible': {'name': 'grid_dsl_expressible', "
            "'value': 1, 'threshold': 1, 'pass': True},\n"
            "    'visible_replay_exact': {'name': 'visible_replay_exact', "
            "'value': 'bad candidate', 'threshold': 0, 'pass': False, "
            "'diagnostics': {'checked_rows': 10, 'exact_rows': 7, "
            "'wrong_rows': 3, 'wrong_cell_count': 12, "
            "'first_mismatch': 'bad candidate', "
            "'mismatch_classes': [{'count': 3, 'first_row': 2, 't': 8, "
            "'action': 1, 'signature': {'bbox': [1, 2, 1, 3], "
            "'pair_counts': [{'predicted': 8, 'real': 3, 'count': 2}]}}]}}\n"
            "  }\n"
            "}))\n"
        ),
    )

    result = run_pre_judge_gate_harness(
        enabled=True,
        project_dir=project,
        latest_eval_results_path=latest,
        python_executable=sys.executable,
        candidate_path=candidate,
    )

    payload = json.loads(latest.read_text(encoding="utf-8"))
    memory = json.loads((project / "workspace" / "candidate_memory.json").read_text())
    cards = [
        json.loads(line)
        for line in (project / "workspace" / "strategy_experiments.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]
    assert result.should_skip_judge is True
    assert result.score_cap_reason == "pre_judge_gate_harness_failed"
    assert payload["score"] == 0
    assert payload["score_cap_reason"] == "pre_judge_gate_harness_failed"
    assert payload["holdout_hard_gate_fired"] is True
    assert "PRE_JUDGE_HARD_GATE" in payload["weakest_point"]
    assert "bad candidate" in payload["weakest_point"]
    assert payload["counterexample_trace"]["schema"] == "ztare-counterexample-trace-v1"
    assert payload["counterexample_trace"]["wrong_cell_count"] == 12
    assert payload["counterexample_trace"]["first_mismatch"] == "bad candidate"
    assert payload["counterexample_trace"]["mismatch_classes"][0]["count"] == 3
    assert payload["counterexample_trace"]["holdout_witness"] == {}
    assert payload["replay_residual_repair_sync"]["cards_written"] == 1
    assert cards[0]["kind"] == "compressed_counterexample_repair"
    assert cards[0]["action_plan"]["residue_quotient"]["bbox"] == [1, 2, 1, 3]
    assert memory["records"][0]["source_type"] == "deterministic_near_miss"
    assert memory["records"][0]["visible_exact_rows"] == 7


def test_pre_judge_gate_harness_threads_holdout_witness_into_counterexample_trace(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    latest = project / "latest_eval_results.json"
    candidate = project / "workspace" / "submissions" / "iter_001.py"
    candidate.parent.mkdir(parents=True)
    candidate.write_text("def step(grid, action, t): return grid\n", encoding="utf-8")
    _write_harness(
        project,
        (
            "import json\n"
            "print(json.dumps({\n"
            "  'score': 0.5,\n"
            "  'harness_ok': True,\n"
            "  'gates': {\n"
            "    'visible_replay_exact': {'name': 'visible_replay_exact', "
            "'value': 1, 'threshold': 0, 'pass': False, "
            "'diagnostics': {'checked_rows': 1, 'exact_rows': 1, "
            "'wrong_rows': 0, 'wrong_cell_count': 0, 'first_mismatch': '', "
            "'mismatch_classes': []}},\n"
            "    'holdout_rollout_exact': {'name': 'holdout_rollout_exact', "
            "'value': 0, 'threshold': 10, 'pass': False, "
            "'holdout_witness': {'step_index': 0, 't': 7, 'action': 1, "
            "'entry_context_note': 'holdout starts mid-episode at its first row t=7', "
            "'divergent_cells': [{'row': 0, 'col': 0, 'predicted': 9, 'actual': 2}]}}\n"
            "  }\n"
            "}))\n"
        ),
    )

    result = run_pre_judge_gate_harness(
        enabled=True,
        project_dir=project,
        latest_eval_results_path=latest,
        python_executable=sys.executable,
        candidate_path=candidate,
    )

    payload = json.loads(latest.read_text(encoding="utf-8"))
    assert result.should_skip_judge is True
    assert payload["counterexample_trace"]["holdout_witness"]["step_index"] == 0
    assert payload["counterexample_trace"]["holdout_witness"]["divergent_cells"][0]["actual"] == 2


def test_pre_judge_gate_submission_failure_does_not_open_canonical_strategy_card(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    latest = project / "latest_eval_results.json"
    candidate = project / "workspace" / "submissions" / "iter_001.py"
    candidate.parent.mkdir(parents=True)
    candidate.write_text("def step(grid, action, t): return grid\n", encoding="utf-8")
    _write_harness(
        project,
        (
            "import json\n"
            "print(json.dumps({\n"
            "  'score': 0.3333,\n"
            "  'harness_ok': True,\n"
            "  'gates': {\n"
            "    'visible_replay_exact': {'name': 'visible_replay_exact', "
            "'value': 1, 'threshold': 0, 'pass': False, "
            "'diagnostics': {'checked_rows': 12, 'exact_rows': 10, "
            "'wrong_rows': 2, 'wrong_cell_count': 4, "
            "'first_mismatch': 'candidate-local residue', "
            "'mismatch_classes': [{'count': 2, 'first_row': 3, 't': 5, "
            "'action': 1, 'signature': {'bbox': [6, 7, 6, 8], "
            "'pair_counts': [{'predicted': 8, 'real': 3, 'count': 2}]}}]}},\n"
            "    'holdout_rollout_exact': {'name': 'holdout_rollout_exact', "
            "'value': 0, 'threshold': 10, 'pass': False}\n"
            "  }\n"
            "}))\n"
        ),
    )

    result = run_pre_judge_gate_harness(
        enabled=True,
        project_dir=project,
        latest_eval_results_path=latest,
        python_executable=sys.executable,
        candidate_path=candidate,
    )

    payload = json.loads(latest.read_text(encoding="utf-8"))
    memory = json.loads((project / "workspace" / "candidate_memory.json").read_text())
    assert result.should_skip_judge is True
    assert payload["counterexample_trace"]["first_mismatch"] == "candidate-local residue"
    assert payload["replay_residual_repair_sync"]["schema"] == (
        "ztare-replay-residual-repair-sync-skipped-v1"
    )
    assert payload["replay_residual_repair_sync"]["reason"] == (
        "unpromoted_candidate_pre_judge_diagnostic"
    )
    assert memory["records"][0]["source_type"] == "deterministic_near_miss"
    assert memory["records"][0]["visible_exact_rows"] == 10
    assert not (project / "workspace" / "strategy_experiments.jsonl").exists()


def test_pre_judge_gate_marks_regression_against_best_cached_candidate(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    latest = project / "latest_eval_results.json"
    candidate = project / "workspace" / "submissions" / "iter_002.py"
    candidate.parent.mkdir(parents=True)
    candidate.write_text("def step(grid, action, t): return grid\n", encoding="utf-8")
    (project / "workspace" / "candidate_memory.json").write_text(
        json.dumps({
            "schema": "ztare-candidate-memory-v1",
            "records": [{
                "source_type": "deterministic_near_miss",
                "submission": "workspace/submissions/iter_001.py",
                "sha": "bestsha",
                "visible_exact_rows": 10,
                "visible_wrong_cells": 4,
                "holdout_depth": 0,
                "gate_score": 0.3333,
                "mismatch_classes": [{
                    "count": 1,
                    "first_row": 0,
                    "t": 0,
                    "action": 0,
                    "signature": {
                        "bbox": [1, 2, 1, 3],
                        "pair_counts": [{"predicted": 8, "real": 3, "count": 2}],
                    },
                }],
            }],
        }),
        encoding="utf-8",
    )
    _write_harness(
        project,
        (
            "import json\n"
            "print(json.dumps({\n"
            "  'score': 0.3333,\n"
            "  'harness_ok': True,\n"
            "  'gates': {\n"
            "    'visible_replay_exact': {'name': 'visible_replay_exact', "
            "'value': 1, 'threshold': 0, 'pass': False, "
            "'diagnostics': {'checked_rows': 12, 'exact_rows': 7, "
            "'wrong_rows': 5, 'wrong_cell_count': 19, "
            "'first_mismatch': 'bad broad edit', "
            "'mismatch_classes': [{'count': 5, 'first_row': 0, 't': 0, "
            "'action': 0, 'signature': {'bbox': [1, 2, 1, 3], "
            "'pair_counts': [{'predicted': 3, 'real': 8, 'count': 2}]}}]}},\n"
            "    'holdout_rollout_exact': {'name': 'holdout_rollout_exact', "
            "'value': 0, 'threshold': 10, 'pass': False}\n"
            "  }\n"
            "}))\n"
        ),
    )

    result = run_pre_judge_gate_harness(
        enabled=True,
        project_dir=project,
        latest_eval_results_path=latest,
        python_executable=sys.executable,
        candidate_path=candidate,
    )

    payload = json.loads(latest.read_text(encoding="utf-8"))
    receipt = payload["candidate_regression_receipt"]
    assert result.should_skip_judge is True
    assert "REGRESSION_FROM_PATCH_BASE" in payload["weakest_point"]
    assert receipt["candidate_exact_rows"] == 7
    assert receipt["best_prior_exact_rows"] == 10
    assert receipt["exact_rows_delta"] == -3
    assert receipt["wrong_cells_delta"] == 15
    assert receipt["quotient_comparison"]["relation"] == "same_support_changed_pairs"
    assert receipt["quotient_comparison"]["candidate_top_quotient"]["bbox"] == [1, 2, 1, 3]
    assert receipt["quotient_comparison"]["best_prior_top_quotient"]["bbox"] == [1, 2, 1, 3]
    assert receipt["quotient_comparison"]["candidate_top_quotient"]["pair_counts"] == [
        {"predicted": 3, "real": 8, "count": 2}
    ]
    assert receipt["quotient_comparison"]["best_prior_top_quotient"]["pair_counts"] == [
        {"predicted": 8, "real": 3, "count": 2}
    ]
    assert payload["replay_residual_repair_sync"]["schema"] == (
        "ztare-replay-residual-repair-sync-skipped-v1"
    )
    assert payload["replay_residual_repair_sync"]["reason"] == (
        "candidate_regressed_against_best_prior"
    )
    assert not (project / "workspace" / "strategy_experiments.jsonl").exists()


def test_pre_judge_gate_ignores_impure_cached_candidate_memory(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    latest = project / "latest_eval_results.json"
    candidate = project / "workspace" / "submissions" / "iter_002.py"
    candidate.parent.mkdir(parents=True)
    candidate.write_text("def step(grid, action, t): return grid\n", encoding="utf-8")
    (project / "workspace" / "candidate_memory.json").write_text(
        json.dumps({
            "schema": "ztare-candidate-memory-v1",
            "records": [{
                "source_type": "deterministic_near_miss",
                "submission": "workspace/submissions/impure.py",
                "sha": "impure",
                "visible_exact_rows": 10,
                "visible_wrong_cells": 1,
                "holdout_depth": 0,
                "gate_score": 0.6667,
                "source_excerpt": (
                    "_COUNT = 0\n"
                    "def PATCH_DELTA(base_next, state, action, t):\n"
                    "    global _COUNT\n"
                    "    _COUNT += 1\n"
                    "    return base_next\n"
                ),
            }],
        }),
        encoding="utf-8",
    )
    _write_harness(
        project,
        (
            "import json\n"
            "print(json.dumps({\n"
            "  'score': 0.3333,\n"
            "  'harness_ok': True,\n"
            "  'gates': {\n"
            "    'visible_replay_exact': {'name': 'visible_replay_exact', "
            "'value': 1, 'threshold': 0, 'pass': False, "
            "'diagnostics': {'checked_rows': 12, 'exact_rows': 7, "
            "'wrong_rows': 5, 'wrong_cell_count': 19, "
            "'first_mismatch': 'candidate residue', 'mismatch_classes': []}},\n"
            "    'holdout_rollout_exact': {'name': 'holdout_rollout_exact', "
            "'value': 0, 'threshold': 10, 'pass': False}\n"
            "  }\n"
            "}))\n"
        ),
    )

    result = run_pre_judge_gate_harness(
        enabled=True,
        project_dir=project,
        latest_eval_results_path=latest,
        python_executable=sys.executable,
        candidate_path=candidate,
    )

    payload = json.loads(latest.read_text(encoding="utf-8"))
    assert result.should_skip_judge is True
    assert "candidate_regression_receipt" not in payload
    assert "REGRESSION_FROM_PATCH_BASE" not in payload["weakest_point"]


def test_patch_base_regression_preflight_is_read_only(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    candidate = project / "workspace" / "probe.py"
    candidate.parent.mkdir(parents=True)
    candidate.write_text("def step(grid, action, t): return grid\n", encoding="utf-8")
    (project / "workspace" / "candidate_memory.json").write_text(
        json.dumps({
            "schema": "ztare-candidate-memory-v1",
            "records": [{
                "source_type": "deterministic_near_miss",
                "submission": "workspace/submissions/iter_001.py",
                "sha": "bestsha",
                "visible_exact_rows": 20,
                "visible_wrong_cells": 4,
                "holdout_depth": 0,
                "gate_score": 0.3333,
                "mismatch_classes": [{
                    "count": 1,
                    "first_row": 0,
                    "t": 0,
                    "action": 0,
                    "signature": {
                        "bbox": [1, 2, 3, 4],
                        "pair_counts": [{"predicted": 8, "real": 3, "count": 2}],
                    },
                }],
            }],
        }),
        encoding="utf-8",
    )
    _write_harness(
        project,
        (
            "import json\n"
            "print(json.dumps({\n"
            "  'score': 0.3333,\n"
            "  'harness_ok': True,\n"
            "  'gates': {\n"
            "    'visible_replay_exact': {'name': 'visible_replay_exact', "
            "'value': 1, 'threshold': 0, 'pass': False, "
            "'diagnostics': {'checked_rows': 24, 'exact_rows': 8, "
            "'wrong_rows': 16, 'wrong_cell_count': 80, "
            "'first_mismatch': 'lost carrier', "
            "'first_mismatch_signature': {'bbox': [1, 2, 3, 4]}, "
            "'mismatch_classes': [{'count': 16, 'first_row': 0, 't': 0, "
            "'action': 0, 'signature': {'bbox': [1, 2, 3, 4], "
            "'pair_counts': [{'predicted': 3, 'real': 8, 'count': 2}]}}]}},\n"
            "    'holdout_rollout_exact': {'name': 'holdout_rollout_exact', "
            "'value': 0, 'threshold': 10, 'pass': False}\n"
            "  }\n"
            "}))\n"
        ),
    )

    result = detect_patch_base_regression_preflight(
        enabled=True,
        project_dir=project,
        candidate_path=candidate,
        python_executable=sys.executable,
    )

    assert result is not None
    assert result.regression_receipt["candidate_relation"] == "regression"
    assert result.regression_receipt["candidate_exact_rows"] == 8
    assert result.regression_receipt["best_prior_exact_rows"] == 20
    assert result.counterexample_trace["first_mismatch"] == "lost carrier"
    assert not (project / "latest_eval_results.json").exists()
    assert not (project / "workspace" / "strategy_experiments.jsonl").exists()


def test_patch_base_preflight_rejects_no_strict_improvement(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    candidate = project / "workspace" / "probe.py"
    candidate.parent.mkdir(parents=True)
    candidate.write_text("def step(grid, action, t): return grid\n", encoding="utf-8")
    (project / "workspace" / "candidate_memory.json").write_text(
        json.dumps({
            "schema": "ztare-candidate-memory-v1",
            "records": [{
                "source_type": "deterministic_near_miss",
                "submission": "workspace/submissions/iter_001.py",
                "sha": "bestsha",
                "visible_exact_rows": 20,
                "visible_wrong_cells": 4,
                "holdout_depth": 0,
                "gate_score": 0.3333,
                "mismatch_classes": [{
                    "count": 1,
                    "first_row": 0,
                    "t": 0,
                    "action": 0,
                    "signature": {
                        "bbox": [1, 2, 3, 4],
                        "pair_counts": [{"predicted": 8, "real": 3, "count": 2}],
                    },
                }],
            }],
        }),
        encoding="utf-8",
    )
    _write_harness(
        project,
        (
            "import json\n"
            "print(json.dumps({\n"
            "  'score': 0.3333,\n"
            "  'harness_ok': True,\n"
            "  'gates': {\n"
            "    'visible_replay_exact': {'name': 'visible_replay_exact', "
            "'value': 1, 'threshold': 0, 'pass': False, "
            "'diagnostics': {'checked_rows': 24, 'exact_rows': 20, "
            "'wrong_rows': 1, 'wrong_cell_count': 4, "
            "'first_mismatch': 'same plateau'}},\n"
            "    'holdout_rollout_exact': {'name': 'holdout_rollout_exact', "
            "'value': 0, 'threshold': 10, 'pass': False}\n"
            "  }\n"
            "}))\n"
        ),
    )

    result = detect_patch_base_regression_preflight(
        enabled=True,
        project_dir=project,
        candidate_path=candidate,
        python_executable=sys.executable,
    )

    assert result is not None
    assert result.regression_receipt["candidate_relation"] == "no_strict_improvement"
    assert result.regression_receipt["exact_rows_delta"] == 0
    assert result.regression_receipt["wrong_cells_delta"] == 0
    assert result.counterexample_trace["first_mismatch"] == "same plateau"
    assert not (project / "latest_eval_results.json").exists()


def test_patch_base_preflight_preserves_comparison_for_improved_failed_candidate(
    tmp_path: Path,
):
    project = tmp_path / "project"
    project.mkdir()
    candidate = project / "workspace" / "probe.py"
    candidate.parent.mkdir(parents=True)
    candidate.write_text("def step(grid, action, t): return grid\n", encoding="utf-8")
    (project / "workspace" / "candidate_memory.json").write_text(
        json.dumps({
            "schema": "ztare-candidate-memory-v1",
            "records": [{
                "source_type": "deterministic_near_miss",
                "submission": "workspace/submissions/iter_001.py",
                "sha": "bestsha",
                "visible_exact_rows": 20,
                "visible_wrong_cells": 4,
                "holdout_depth": 0,
                "gate_score": 0.3333,
                "mismatch_classes": [{
                    "count": 1,
                    "first_row": 0,
                    "t": 0,
                    "action": 0,
                    "signature": {
                        "bbox": [1, 2, 3, 4],
                        "pair_counts": [{"predicted": 8, "real": 3, "count": 2}],
                    },
                }],
            }],
        }),
        encoding="utf-8",
    )
    _write_harness(
        project,
        (
            "import json\n"
            "print(json.dumps({\n"
            "  'score': 0.3333,\n"
            "  'harness_ok': True,\n"
            "  'gates': {\n"
            "    'visible_replay_exact': {'name': 'visible_replay_exact', "
            "'value': 1, 'threshold': 0, 'pass': False, "
            "'diagnostics': {'checked_rows': 24, 'exact_rows': 21, "
            "'wrong_rows': 1, 'wrong_cell_count': 3, "
            "'first_mismatch': 'better visible but not closed', "
            "'mismatch_classes': [{'count': 1, 'first_row': 0, 't': 0, "
            "'action': 0, 'signature': {'bbox': [1, 2, 3, 5], "
            "'pair_counts': [{'predicted': 8, 'real': 3, 'count': 1}]}}]}},\n"
            "    'holdout_rollout_exact': {'name': 'holdout_rollout_exact', "
            "'value': 0, 'threshold': 10, 'pass': False}\n"
            "  }\n"
            "}))\n"
        ),
    )

    result = detect_patch_base_regression_preflight(
        enabled=True,
        project_dir=project,
        candidate_path=candidate,
        python_executable=sys.executable,
    )

    assert result is not None
    receipt = result.regression_receipt
    assert receipt["candidate_relation"] == "improved_but_gate_failed"
    assert receipt["candidate_exact_rows"] == 21
    assert receipt["best_prior_exact_rows"] == 20
    assert receipt["exact_rows_delta"] == 1
    assert receipt["wrong_cells_delta"] == -1
    assert receipt["quotient_comparison"]["best_prior_top_quotient"]
    assert receipt["quotient_comparison"]["candidate_top_quotient"]


def test_patch_base_regression_retry_message_owns_probe_file(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "workspace").mkdir()
    (project / "workspace" / "candidate_memory.json").write_text(
        json.dumps({
            "schema": "ztare-candidate-memory-v1",
            "records": [{
                "source_type": "deterministic_near_miss",
                "submission": "workspace/submissions/iter_001.py",
                "sha": "bestsha",
                "visible_exact_rows": 20,
                "visible_wrong_cells": 4,
                "holdout_depth": 0,
                "gate_score": 0.3333,
                "mismatch_classes": [{
                    "count": 1,
                    "first_row": 0,
                    "t": 0,
                    "action": 0,
                    "signature": {
                        "bbox": [1, 2, 3, 4],
                        "pair_counts": [{"predicted": 8, "real": 3, "count": 2}],
                    },
                }],
            }],
        }),
        encoding="utf-8",
    )
    _write_harness(
        project,
        (
            "import json\n"
            "print(json.dumps({\n"
            "  'score': 0.3333,\n"
            "  'harness_ok': True,\n"
            "  'gates': {\n"
            "    'visible_replay_exact': {'name': 'visible_replay_exact', "
            "'value': 1, 'threshold': 0, 'pass': False, "
            "'diagnostics': {'checked_rows': 24, 'exact_rows': 8, "
            "'wrong_rows': 16, 'wrong_cell_count': 80, "
            "'first_mismatch': 'lost carrier', "
            "'mismatch_classes': [{'count': 16, 'first_row': 0, 't': 0, "
            "'action': 0, 'signature': {'bbox': [1, 2, 3, 4], "
            "'pair_counts': [{'predicted': 3, 'real': 8, 'count': 2}]}}]}},\n"
            "    'holdout_rollout_exact': {'name': 'holdout_rollout_exact', "
            "'value': 0, 'threshold': 10, 'pass': False}\n"
            "  }\n"
            "}))\n"
        ),
    )

    message = patch_base_regression_retry_message(
        enabled=True,
        project_dir=project,
        candidate_source="def step(grid, action, t): return grid\n",
        python_executable=sys.executable,
    )

    assert message is not None
    assert "PATCH_BASE_IMPROVEMENT_PRECHECK" in message
    assert "exact_rows 8 vs 20" in message
    assert "holdout 0 vs 0" in message
    assert "lost carrier" in message
    assert "quotient_relation=same_support_changed_pairs" in message
    assert "candidate_top=" in message
    assert "best_prior_top=" in message
    assert "PATCH_BASE_QUOTIENT_RECEIPT: " in message
    receipt_line = next(
        line for line in message.splitlines()
        if line.startswith("PATCH_BASE_QUOTIENT_RECEIPT: ")
    )
    quotient = json.loads(receipt_line.split(": ", 1)[1])
    assert quotient["schema"] == "ztare-regression-quotient-comparison-v1"
    assert quotient["relation"] == "same_support_changed_pairs"
    assert quotient["candidate_top_quotient"]["bbox"] == [1, 2, 3, 4]
    assert quotient["best_prior_top_quotient"]["bbox"] == [1, 2, 3, 4]
    latest = json.loads(
        (project / "workspace" / "latest_patch_base_regression.json").read_text(
            encoding="utf-8"
        )
    )
    assert latest["schema"] == "ztare-latest-patch-base-regression-v1"
    assert latest["candidate_regression_receipt"]["quotient_comparison"]["relation"] == (
        "same_support_changed_pairs"
    )
    assert not (project / "workspace" / "_pre_judge_probe_test_model.py").exists()


def test_patch_base_hard_gate_routes_to_executable_workbench_probe(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "workspace").mkdir()
    _write_harness(
        project,
        (
            "import json\n"
            "print(json.dumps({\n"
            "  'score': 0.0,\n"
            "  'harness_ok': True,\n"
            "  'gates': {\n"
            "    'visible_replay_exact': {'name': 'visible_replay_exact', "
            "'value': 1, 'threshold': 0, 'pass': False, "
            "'diagnostics': {'checked_rows': 24, 'exact_rows': 8, "
            "'wrong_rows': 16, 'wrong_cell_count': 80, "
            "'first_mismatch': 'unquotiented carrier failure', "
            "'mismatch_classes': [{'count': 16, 'first_row': 0, 't': 0, "
            "'action': 1, 'signature': {'bbox': [61, 57, 62, 57], "
            "'pair_counts': [{'predicted': 8, 'real': 3, 'count': 2}]}}]}},\n"
            "    'holdout_rollout_exact': {'name': 'holdout_rollout_exact', "
            "'value': 0, 'threshold': 10, 'pass': False}\n"
            "  }\n"
            "}))\n"
        ),
    )

    message = patch_base_regression_retry_message(
        enabled=True,
        project_dir=project,
        candidate_source="def step(grid, action, t): return grid\n",
        python_executable=sys.executable,
    )

    assert message is not None
    assert "relation=hard_gate_failure" in message
    assert "Do not retreat to an identity PATCH_DELTA" in message
    assert "mine_worldmodel_separating_features" in message
    assert "stateless probe" in message
    latest_weakness = json.loads(
        (project / "workspace" / "latest_harness_weakness.json").read_text(
            encoding="utf-8"
        )
    )
    assert latest_weakness["weakness_class"] == "visible_counterexample_trace_unfactored"
    assert latest_weakness["recommended_route"] == "inspect_visible_regression_trace_then_refine_or_propose_capability"
    assert latest_weakness["recommended_capability_id"] == "mine_worldmodel_separating_features"
    task = latest_weakness["workbench_task"]
    assert task["schema"] == "ztare-leaf-workbench-task-v1"
    assert task["failure_class"] == "visible_counterexample_trace_unfactored"
    assert task["admissible_capability_ids"][0] == "mine_worldmodel_separating_features"
    assert "run_visible_json_probe" in task["admissible_capability_ids"]
    assert task["visible_artifact_refs"] == ["workspace/latest_patch_base_regression.json"]
    latest_regression = json.loads(
        (project / "workspace" / "latest_patch_base_regression.json").read_text(
            encoding="utf-8"
        )
    )
    assert latest_regression["candidate_regression_receipt"]["candidate_relation"] == (
        "hard_gate_failure"
    )
    assert latest_regression["counterexample_trace"]["first_mismatch"] == (
        "unquotiented carrier failure"
    )
    from ztare.worldmodel.leaf_workbench import worldmodel_leaf_workbench_records

    records = worldmodel_leaf_workbench_records(project)
    task_record = next(
        row for row in records
        if row.get("source_type") == "leaf_workbench_task"
    )
    assert task_record["capability_id"] == "mine_worldmodel_separating_features"
    assert "visible_artifacts=['workspace/latest_patch_base_regression.json']" in (
        task_record["summary"]
    )


def test_patch_base_holdout_only_failure_routes_to_boundary_gate(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "workspace").mkdir()
    _write_harness(
        project,
        (
            "import json\n"
            "print(json.dumps({\n"
            "  'score': 0.6667,\n"
            "  'harness_ok': True,\n"
            "  'gates': {\n"
            "    'visible_replay_exact': {'name': 'visible_replay_exact', "
            "'value': 0, 'threshold': 0, 'pass': True, "
            "'diagnostics': {'checked_rows': 24, 'exact_rows': 24, "
            "'wrong_rows': 0, 'wrong_cell_count': 0, "
            "'first_mismatch': '', 'mismatch_classes': []}},\n"
            "    'holdout_rollout_exact': {'name': 'holdout_rollout_exact', "
            "'value': 0, 'threshold': 10, 'pass': False}\n"
            "  }\n"
            "}))\n"
        ),
    )

    message = patch_base_regression_retry_message(
        enabled=True,
        project_dir=project,
        candidate_source="def step(grid, action, t): return grid\n",
        python_executable=sys.executable,
    )

    assert message is not None
    assert "no visible replay counterexample left" in message
    assert "run_strategy_required_gate" in message
    assert "run_visible_json_probe" not in message
    latest_weakness = json.loads(
        (project / "workspace" / "latest_harness_weakness.json").read_text(
            encoding="utf-8"
        )
    )
    assert latest_weakness["weakness_class"] == "boundary_evidence_missing"
    assert latest_weakness["recommended_route"] == "run_or_return_substrate_boundary_gate"
    assert latest_weakness["recommended_capability_id"] == "run_strategy_required_gate"
    task = latest_weakness["workbench_task"]
    assert task["failure_class"] == "boundary_evidence_missing"
    assert task["admissible_capability_ids"] == ["run_strategy_required_gate"]
    assert "no remaining counterexample" in task["objective"]
    latest_regression = json.loads(
        (project / "workspace" / "latest_patch_base_regression.json").read_text(
            encoding="utf-8"
        )
    )
    trace = latest_regression["counterexample_trace"]
    assert trace["exact_rows"] == 24
    assert trace["checked_rows"] == 24
    assert trace["wrong_cell_count"] == 0

    from ztare.worldmodel.leaf_workbench import worldmodel_leaf_workbench_records

    task_record = next(
        row for row in worldmodel_leaf_workbench_records(project)
        if row.get("source_type") == "leaf_workbench_task"
    )
    assert task_record["capability_id"] == "run_strategy_required_gate"


def test_patch_base_no_visible_quotient_prefers_declared_strategy_gate(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    workspace = project / "workspace"
    workspace.mkdir()
    (workspace / "strategy_experiments.jsonl").write_text(
        json.dumps(
            {
                "schema": "strategy-experiment-v1",
                "kind": "compressed_counterexample_repair",
                "failure_family": "family-a",
                "failure_family_sha": "sha-a",
                "action_plan": {
                    "required_next_gate": {
                        "command": "arc3_level_transfer_probe",
                        "success_status": "exact_local_transfer_depth",
                    }
                },
                "disposition": "open",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _write_harness(
        project,
        (
            "import json\n"
            "print(json.dumps({\n"
            "  'score': 0,\n"
            "  'harness_ok': True,\n"
            "  'gates': {\n"
            "    'grid_dsl_expressible': {'name': 'grid_dsl_expressible', "
            "'value': -1, 'threshold': 1, 'pass': False},\n"
            "    'visible_replay_exact': {'name': 'visible_replay_exact', "
            "'value': -1, 'threshold': 0, 'pass': False},\n"
            "    'holdout_rollout_exact': {'name': 'holdout_rollout_exact', "
            "'value': -1, 'threshold': 0, 'pass': False}\n"
            "  }\n"
            "}))\n"
        ),
    )

    message = patch_base_regression_retry_message(
        enabled=True,
        project_dir=project,
        candidate_source="",
        python_executable=sys.executable,
    )

    assert message is not None
    assert "run_strategy_required_gate" in message
    latest_weakness = json.loads(
        (project / "workspace" / "latest_harness_weakness.json").read_text(
            encoding="utf-8"
        )
    )
    assert latest_weakness["weakness_class"] == "declared_gate_obligation_open"
    assert latest_weakness["recommended_route"] == (
        "run_declared_strategy_gate_before_new_visible_probe"
    )
    assert latest_weakness["recommended_capability_id"] == "run_strategy_required_gate"
    assert latest_weakness["workbench_task"]["admissible_capability_ids"] == [
        "run_strategy_required_gate"
    ]


def test_strategy_card_retry_message_rejects_invalid_outcome(tmp_path: Path):
    card = {
        "schema": "strategy-experiment-v1",
        "kind": "compressed_counterexample_repair",
        "failure_family": "family-a",
        "rationale": "compact residual quotient",
        "falsifiable_prediction": "remove quotient or route card",
        "action_plan": {
            "residue_quotient": {"residue_class": "replay_mismatch_quotient"},
            "required_next_gate": {
                "command": "replay_diagnostics",
                "success_status": "residual_class_removed_or_operator_carded",
            },
        },
        "kill_condition": "current replay diagnostics no longer contain this quotient",
        "disposition": "open",
    }
    from ztare.common.operator_proposal_contract import write_proposal_cards

    written = write_proposal_cards(tmp_path / "workspace" / "strategy_experiments.jsonl", [card])
    receipt = {
        "failure_family_sha": written[0]["failure_family_sha"],
        "outcome": "resubmit",
        "observed_status": "minimal executable carrier repair around the preserved model",
        "evidence_refs": ["workspace/submissions/iter_001.py"],
    }

    message = strategy_card_retry_message(
        project_dir=tmp_path,
        thesis_text=f"STRATEGY_CARD_DISCHARGE: {json.dumps(receipt)}",
        candidate_source="",
    )

    assert message is not None
    assert "STRATEGY_CARD_RECEIPT_PRECHECK" in message
    assert "missing_or_invalid_outcome" in message
    assert "satisfied|refuted|blocked" in message

    carrier_message = strategy_card_retry_message(
        project_dir=tmp_path,
        thesis_text=f"STRATEGY_CARD_DISCHARGE: {json.dumps(receipt)}",
        candidate_source="def step(grid, action, t): return grid\n",
    )
    assert carrier_message is None


def test_ambient_carrier_dependency_retry_message_rejects_file_import_base():
    message = ambient_carrier_dependency_retry_message(
        enabled=True,
        candidate_source=(
            "import importlib.util\n"
            "from pathlib import Path\n"
            "BASE = Path(__file__).resolve().parent / 'workspace/submissions/base.py'\n"
            "spec = importlib.util.spec_from_file_location('base', BASE)\n"
            "spec.loader.exec_module(module)\n"
            "def step(grid, action, t): return grid\n"
        ),
    )

    assert message is not None
    assert "AMBIENT_CARRIER_DEPENDENCY_PRECHECK" in message


def test_leaf_workbench_retry_message_is_marker_injected_not_worldmodel_hardcoded():
    assert leaf_workbench_retry_message(
        enabled=True,
        thesis_text="uses mandatory patch base and residual quotient",
        candidate_source="",
        fact_markers=(),
    ) is None

    message = leaf_workbench_retry_message(
        enabled=True,
        thesis_text="uses mandatory patch base and residual quotient",
        candidate_source="",
        fact_markers=("mandatory patch base", "residual quotient"),
    )

    assert message is not None
    assert "LEAF_WORKBENCH_RECEIPT_PRECHECK" in message


def test_leaf_workbench_retry_message_ignores_carrier_patch_base_terms():
    message = leaf_workbench_retry_message(
        enabled=True,
        thesis_text="minimal executable patch carrier",
        candidate_source=(
            'PATCH_BASE = {"source_ref":"workspace/submissions/base.py","sha256":"abc"}\n'
            "def PATCH_DELTA(base_next, state, action, t): return base_next\n"
        ),
        fact_markers=("patch base", "workspace/submissions/"),
    )

    assert message is None


def test_leaf_workbench_retry_allows_executable_carrier_to_reach_gate(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "latest_harness_weakness.json").write_text(
        json.dumps(
            {
                "schema": "ztare-harness-weakness-receipt-v1",
                "workbench_task": {
                    "admissible_capability_ids": ["run_strategy_required_gate"],
                    "objective": "run the declared gate against the current carrier",
                },
            }
        ),
        encoding="utf-8",
    )

    message = leaf_workbench_retry_message(
        enabled=True,
        thesis_text="candidate attempts a carrier",
        candidate_source="def step(grid, action, t): return grid\n",
        fact_markers=("run_strategy_required_gate",),
        project_dir=tmp_path,
    )

    assert message is None


def test_leaf_workbench_retry_accepts_visible_admissibility_diagnostic_receipt(tmp_path: Path):
    project = tmp_path
    (project / "workspace").mkdir()
    for capability_id in ("check_worldmodel_carrier_contract", "route_action"):
        receipt = {
            "capability_id": capability_id,
            "input_hashes": {
                "source_ref": "stdin",
                "source_sha256": "abc",
            },
            "output_summary": "visible diagnostic passed",
            "claim_bindings": ["visible CLI diagnostic check"],
        }

        message = leaf_workbench_retry_message(
            enabled=True,
            project_dir=project,
            thesis_text="LEAF_WORKBENCH_RECEIPT: " + json.dumps(receipt),
            candidate_source="def PATCH_DELTA(base_next, state, action):\n    return base_next\n",
            fact_markers=(capability_id,),
        )

        assert message is None


def test_leaf_workbench_retry_message_rejects_malformed_receipt_prose():
    message = leaf_workbench_retry_message(
        enabled=True,
        thesis_text="LEAF_WORKBENCH_RECEIPT inspect_worldmodel_patch_base@v1:\n  capability_id: x",
        candidate_source="",
        fact_markers=("inspect_worldmodel_",),
    )

    assert message is not None
    assert "control_receipts" in message
    assert "not prose, YAML, or Python variables" in message


def test_leaf_workbench_retry_message_accepts_typed_receipt():
    message = leaf_workbench_retry_message(
        enabled=True,
        thesis_text=(
            'LEAF_WORKBENCH_RECEIPT: {"capability_id":"inspect_worldmodel_patch_base",'
            '"input_hashes":{"source_ref":"sha256:abc"},"output_summary":"seen",'
            '"claim_bindings":["patch base preserved"]}\n'
            "uses mandatory patch base"
        ),
        candidate_source="",
        fact_markers=("mandatory patch base",),
    )

    assert message is None


def test_leaf_workbench_retry_message_rejects_unbound_self_authored_receipt(tmp_path: Path):
    project = tmp_path
    (project / "workspace").mkdir()
    message = leaf_workbench_retry_message(
        enabled=True,
        project_dir=project,
        thesis_text=(
            'LEAF_WORKBENCH_RECEIPT: {"capability_id":"inspect_worldmodel_counterexample_context",'
            '"contract_sha256":"abc",'
            '"input_hashes":{"source_ref":"latest_eval_results.json:candidate_regression_receipt"},'
            '"output_summary":"candidate support differs from prior support",'
            '"claim_bindings":["context separates regression"]}'
        ),
        candidate_source="",
        fact_markers=("inspect_worldmodel_",),
    )

    assert message is not None
    assert "LEAF_WORKBENCH_RECEIPT_PROVENANCE_PRECHECK" in message
    assert "request the action" in message


def test_leaf_workbench_retry_message_accepts_hash_bound_receipt(tmp_path: Path):
    project = tmp_path
    ws = project / "workspace"
    ws.mkdir()
    receipt_file = ws / "probe.json"
    receipt_file.write_text('{"status":"ok"}', encoding="utf-8")
    digest = hashlib.sha256(receipt_file.read_bytes()).hexdigest()
    message = leaf_workbench_retry_message(
        enabled=True,
        project_dir=project,
        thesis_text=(
            'LEAF_WORKBENCH_RECEIPT: {"capability_id":"inspect_worldmodel_counterexample_context",'
            '"contract_sha256":"abc",'
            f'"input_hashes":{{"receipt_ref":"workspace/probe.json","receipt_sha256":"{digest}"}},'
            '"output_summary":"candidate support differs from prior support",'
            '"claim_bindings":["context separates regression"]}'
        ),
        candidate_source="",
        fact_markers=("inspect_worldmodel_",),
    )

    assert message is None


def test_candidate_bound_workbench_receipt_requires_candidate_identity(tmp_path: Path):
    project = tmp_path
    ws = project / "workspace"
    ws.mkdir()
    receipt_file = ws / "kernel_receipt.json"
    receipt_file.write_text("{}", encoding="utf-8")
    digest = hashlib.sha256(receipt_file.read_bytes()).hexdigest()
    receipt = {
        "capability_id": "run_strategy_required_gate",
        "contract_sha256": "contract-sha",
        "input_hashes": {
            "kernel_receipt_ref": "workspace/kernel_receipt.json",
            "kernel_receipt_sha256": digest,
            "request": json.dumps(
                {
                    "capability_id": "run_strategy_required_gate",
                    "input_refs": {
                        "candidate_path": "test_model.py",
                        "command": "arc3_level_transfer_probe",
                    },
                }
            ),
        },
        "output_summary": "status=bounded_mismatch",
        "claim_bindings": ["run required Strategy gate"],
    }

    message = leaf_workbench_retry_message(
        enabled=True,
        project_dir=project,
        thesis_text="LEAF_WORKBENCH_RECEIPT: " + json.dumps(receipt),
        candidate_source="def step(grid, action, t): return grid\n",
        fact_markers=("run_strategy_required_gate",),
    )

    assert message is not None
    assert "predates content-addressed candidate binding" in message


def test_candidate_bound_workbench_receipt_auto_replays_current_candidate(tmp_path: Path):
    project = tmp_path
    ws = project / "workspace"
    ws.mkdir()
    receipt_file = ws / "kernel_receipt.json"
    receipt_file.write_text("{}", encoding="utf-8")
    digest = hashlib.sha256(receipt_file.read_bytes()).hexdigest()
    old_request = {
        "capability_id": "run_strategy_required_gate",
        "input_refs": {
            "candidate_path": "test_model.py",
            "command": "arc3_level_transfer_probe",
        },
        "claim_bindings": ["run required Strategy gate"],
    }
    stale_receipt = {
        "capability_id": "run_strategy_required_gate",
        "contract_sha256": "contract-sha",
        "input_hashes": {
            "kernel_receipt_ref": "workspace/kernel_receipt.json",
            "kernel_receipt_sha256": digest,
            "request": json.dumps(old_request),
        },
        "output_summary": "status=bounded_mismatch",
        "claim_bindings": ["run required Strategy gate"],
    }
    contract = LeafWorkbenchContract(
        capabilities=(
            LeafWorkbenchCapability(
                capability_id="run_strategy_required_gate",
                purpose="test",
                authority="bounded_world_probe",
                secret_policy="sealed_aggregate_only",
                input_contract=["candidate_path"],
                output_contract=["summary"],
            ),
        )
    )
    captured: list[dict[str, Any]] = []

    def _records(_project: str | Path) -> list[dict[str, Any]]:
        return []

    def _handler(
        _project: str | Path,
        req: dict[str, Any],
        _row: dict[str, Any] | None,
        _contract: LeafWorkbenchContract,
    ) -> dict[str, Any]:
        captured.append(req)
        return {
            "input_hashes": {"request": json.dumps(req, sort_keys=True)},
            "output_summary": "reran for current candidate",
        }

    source = "def step(grid, action, t): return grid\n"
    message = leaf_workbench_retry_message(
        enabled=True,
        project_dir=project,
        thesis_text="LEAF_WORKBENCH_RECEIPT: " + json.dumps(stale_receipt),
        candidate_source=source,
        fact_markers=("run_strategy_required_gate",),
        contract=contract,
        records_fn=_records,
        action_handlers={"run_strategy_required_gate": _handler},
        stateless_actions={"run_strategy_required_gate"},
    )

    assert message is not None
    assert "stale candidate-bound receipt normalized" in message
    assert "LEAF_WORKBENCH_RECEIPT:" in message
    assert captured
    refs = captured[0]["input_refs"]
    assert refs["candidate_identity"] == "current_submission"
    assert refs["candidate_sha256"] == hashlib.sha256(source.strip().encode("utf-8")).hexdigest()
    assert refs["candidate_path"].startswith("workspace/leaf_workbench_action_candidates/")


def test_leaf_workbench_score_candidate_delta_executes_registered_handler(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "workspace").mkdir()
    (project / "workspace" / "candidate_memory.json").write_text(
        json.dumps({
            "schema": "ztare-candidate-memory-v1",
            "records": [{
                "source_type": "deterministic_near_miss",
                "submission": "workspace/submissions/iter_001.py",
                "sha": "bestsha",
                "visible_exact_rows": 20,
                "visible_wrong_cells": 4,
                "holdout_depth": 0,
                "gate_score": 0.3333,
                "mismatch_classes": [{
                    "count": 1,
                    "first_row": 0,
                    "t": 0,
                    "action": 0,
                    "signature": {
                        "bbox": [1, 2, 3, 4],
                        "pair_counts": [{"predicted": 8, "real": 3, "count": 2}],
                    },
                }],
            }],
        }),
        encoding="utf-8",
    )
    _write_harness(
        project,
        (
            "import json\n"
            "print(json.dumps({\n"
            "  'score': 0.25,\n"
            "  'harness_ok': True,\n"
            "  'gates': {\n"
            "    'visible_replay_exact': {'name': 'visible_replay_exact', "
            "'value': 1, 'threshold': 0, 'pass': False, "
            "'diagnostics': {'checked_rows': 24, 'exact_rows': 8, "
            "'wrong_rows': 16, 'wrong_cell_count': 80, "
            "'first_mismatch': 'lost carrier', "
            "'mismatch_classes': [{'count': 16, 'first_row': 0, 't': 0, "
            "'action': 0, 'signature': {'bbox': [1, 2, 3, 4], "
            "'pair_counts': [{'predicted': 3, 'real': 8, 'count': 2}]}}]}},\n"
            "    'holdout_rollout_exact': {'name': 'holdout_rollout_exact', "
            "'value': 0, 'threshold': 10, 'pass': False}\n"
            "  }\n"
            "}))\n"
        ),
    )
    from ztare.worldmodel.leaf_workbench import worldmodel_leaf_workbench_action_environment

    env = worldmodel_leaf_workbench_action_environment()
    request = {
        "type": "LEAF_WORKBENCH_ACTION_REQUEST",
        "payload": {
            "capability_id": "score_worldmodel_candidate_delta",
            "input_refs": {"candidate_path": "test_model.py"},
            "claim_bindings": ["score current candidate delta"],
        },
    }
    candidate_source = "def step(grid, action, t): return grid\n"
    message = leaf_workbench_retry_message(
        enabled=True,
        project_dir=project,
        thesis_text="LEAF_WORKBENCH_ACTION_REQUEST: " + json.dumps(request),
        candidate_source=candidate_source,
        contract=env["contract"],
        records_fn=env["records_fn"],
        action_handlers=env["action_handlers"],
        stateless_actions=env["stateless_actions"],
    )

    assert message is not None
    assert "LEAF_WORKBENCH_RECEIPT:" in message
    assert "score_worldmodel_candidate_delta" in message
    assert "lost carrier" in message
    assert "workspace/leaf_workbench_action_candidates/" in message


def test_boundary_cegar_ready_delta_does_not_promote_diagnostic_family_coverage() -> None:
    receipt_a = {
        "type": "LEAF_WORKBENCH_RECEIPT",
        "payload": {
            "capability_id": "mine_a",
            "input_hashes": {"source_ref": "sha256:a"},
            "output_summary": json.dumps(
                {
                    "candidate_delta_admissible": False,
                    "source_receipt": "workspace/probe.json",
                    "candidate_label_coverage": {
                        "required": ["left", "right"],
                        "covered": ["left"],
                    },
                }
            ),
            "claim_bindings": ["left selector"],
        },
    }
    receipt_b = {
        "type": "LEAF_WORKBENCH_RECEIPT",
        "payload": {
            "capability_id": "mine_b",
            "input_hashes": {"source_ref": "sha256:b"},
            "output_summary": json.dumps(
                {
                    "candidate_delta_admissible": False,
                    "source_receipt": "workspace/probe.json",
                    "candidate_label_coverage": {
                        "required": ["left", "right"],
                        "covered": ["right"],
                    },
                }
            ),
            "claim_bindings": ["right selector"],
        },
    }
    thesis = "\n".join(
        "LEAF_WORKBENCH_RECEIPT: " + json.dumps(row["payload"])
        for row in (receipt_a, receipt_b)
    )

    message = boundary_cegar_ready_delta_retry_message(
        enabled=True,
        thesis_text=thesis,
        candidate_source="",
    )

    assert message is None


def test_leaf_workbench_retry_rejects_prose_only_stored_receipt_ref(tmp_path: Path):
    project = tmp_path
    receipt_dir = project / "workspace" / "leaf_workbench_action_receipts"
    receipt_dir.mkdir(parents=True)
    digest = "a" * 64
    (receipt_dir / f"{digest}.json").write_text(
        json.dumps({"capability_id": "mine_worldmodel_lowerable_selectors"}),
        encoding="utf-8",
    )

    message = leaf_workbench_retry_message(
        enabled=True,
        project_dir=project,
        thesis_text=f"candidate cites receipt {digest} as selector evidence",
        candidate_source="def step(grid, action, t):\n    return grid",
        fact_markers=(),
    )

    assert message is not None
    assert "candidate cites stored workbench receipt identity" in message
    assert digest in message


def test_candidate_bound_workbench_receipt_can_be_carried_for_control_only(
    tmp_path: Path,
):
    project = tmp_path
    ws = project / "workspace"
    ws.mkdir()
    receipt_file = ws / "kernel_receipt.json"
    receipt_file.write_text("{}", encoding="utf-8")
    digest = hashlib.sha256(receipt_file.read_bytes()).hexdigest()
    receipt = {
        "capability_id": "run_strategy_required_gate",
        "contract_sha256": "contract-sha",
        "input_hashes": {
            "kernel_receipt_ref": "workspace/kernel_receipt.json",
            "kernel_receipt_sha256": digest,
            "request": json.dumps(
                {
                    "capability_id": "run_strategy_required_gate",
                    "input_refs": {
                        "candidate_path": "test_model.py",
                        "command": "arc3_level_transfer_probe",
                    },
                }
            ),
        },
        "output_summary": "status=bounded_mismatch",
        "claim_bindings": ["run required Strategy gate"],
    }

    message = leaf_workbench_retry_message(
        enabled=True,
        project_dir=project,
        thesis_text="LEAF_WORKBENCH_RECEIPT: " + json.dumps(receipt),
        candidate_source="",
        fact_markers=("run_strategy_required_gate",),
    )

    assert message is None


def test_candidate_bound_workbench_receipt_with_candidate_identity_passes(tmp_path: Path):
    project = tmp_path
    ws = project / "workspace"
    ws.mkdir()
    receipt_file = ws / "kernel_receipt.json"
    receipt_file.write_text("{}", encoding="utf-8")
    digest = hashlib.sha256(receipt_file.read_bytes()).hexdigest()
    receipt = {
        "capability_id": "run_strategy_required_gate",
        "contract_sha256": "contract-sha",
        "input_hashes": {
            "kernel_receipt_ref": "workspace/kernel_receipt.json",
            "kernel_receipt_sha256": digest,
            "request": json.dumps(
                {
                    "capability_id": "run_strategy_required_gate",
                    "input_refs": {
                        "candidate_identity": "current_submission",
                        "candidate_path": "workspace/leaf_workbench_action_candidates/abc.py",
                        "candidate_sha256": "abc",
                        "command": "arc3_level_transfer_probe",
                    },
                }
            ),
        },
        "output_summary": "status=bounded_mismatch",
        "claim_bindings": ["run required Strategy gate"],
    }

    message = leaf_workbench_retry_message(
        enabled=True,
        project_dir=project,
        thesis_text="LEAF_WORKBENCH_RECEIPT: " + json.dumps(receipt),
        candidate_source="def step(grid, action, t): return grid\n",
        fact_markers=("run_strategy_required_gate",),
    )

    assert message is None


def test_leaf_workbench_action_request_executes_registered_record(tmp_path: Path):
    project = tmp_path
    ws = project / "workspace"
    ws.mkdir()
    (ws / "latest_replay_diagnostics_after_abduce.json").write_text(
        json.dumps(
            {
                "mismatch_classes": [
                    {
                        "count": 3,
                        "t": 8,
                        "action": 1,
                        "signature": {
                            "bbox": [1, 2, 1, 3],
                            "pair_counts": [{"predicted": 8, "real": 3, "count": 2}],
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    thesis = (
        'LEAF_WORKBENCH_ACTION_REQUEST: {"capability_id":"inspect_replay_residual_quotient",'
        '"input_refs":{"diagnostics_ref":"workspace/latest_replay_diagnostics_after_abduce.json"},'
        '"claim_bindings":["need residual quotient"]}'
    )

    message = leaf_workbench_action_request_retry_message(
        enabled=True,
        project_dir=project,
        thesis_text=thesis,
    )

    assert message is not None
    assert "LEAF_WORKBENCH_ACTION_REQUEST_PRECHECK" in message
    assert "LEAF_WORKBENCH_RECEIPT:" in message
    assert "inspect_replay_residual_quotient" in message
    assert "class_count=3" in message


def test_leaf_workbench_action_request_accepts_multiline_json(tmp_path: Path):
    project = tmp_path
    ws = project / "workspace"
    ws.mkdir()
    (ws / "latest_replay_diagnostics_after_abduce.json").write_text(
        json.dumps(
            {
                "mismatch_classes": [
                    {
                        "count": 2,
                        "t": 4,
                        "action": 0,
                        "signature": {
                            "bbox": [1, 1, 1, 2],
                            "pair_counts": [{"predicted": 11, "real": 3, "count": 2}],
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    thesis = """
LEAF_WORKBENCH_ACTION_REQUEST: {
  "capability_id": "inspect_replay_residual_quotient",
  "input_refs": {
    "diagnostics_ref": "workspace/latest_replay_diagnostics_after_abduce.json"
  },
  "claim_bindings": ["need residual quotient"]
}
Trailing prose should not be consumed.
"""

    message = leaf_workbench_action_request_retry_message(
        enabled=True,
        project_dir=project,
        thesis_text=thesis,
    )

    assert message is not None
    assert "LEAF_WORKBENCH_RECEIPT:" in message
    assert "class_count=2" in message


def test_leaf_workbench_action_request_runs_visible_json_probe(tmp_path: Path):
    project = tmp_path
    ws = project / "workspace"
    ws.mkdir()
    (ws / "probe_input.json").write_text(
        json.dumps({"classes": [{"count": 2}, {"count": 4}]}),
        encoding="utf-8",
    )
    request = {
        "capability_id": "run_visible_json_probe",
        "input_refs": {
            "artifact_refs": ["workspace/probe_input.json"],
            "probe_py": (
                'rows = ARTIFACTS["workspace/probe_input.json"]["classes"]\n'
                'RESULT = {"total": sum(row["count"] for row in rows)}\n'
            ),
        },
        "claim_bindings": ["need visible aggregate"],
    }
    thesis = "LEAF_WORKBENCH_ACTION_REQUEST: " + json.dumps(request)

    message = leaf_workbench_action_request_retry_message(
        enabled=True,
        project_dir=project,
        thesis_text=thesis,
    )

    assert message is not None
    assert "LEAF_WORKBENCH_ACTION_REQUEST_PRECHECK" in message
    assert "LEAF_WORKBENCH_RECEIPT:" in message
    assert "run_visible_json_probe" in message
    receipt_line = next(line for line in message.splitlines() if line.startswith("LEAF_WORKBENCH_RECEIPT:"))
    receipt = json.loads(receipt_line.split(":", 1)[1].strip())
    assert receipt["output_summary"] == '{"total":6}'
    assert receipt["input_hashes"]["kernel_receipt_ref"].startswith(
        "workspace/leaf_workbench_action_receipts/"
    )
    stamped = project / receipt["input_hashes"]["kernel_receipt_ref"]
    assert stamped.is_file()
    assert hashlib.sha256(stamped.read_bytes()).hexdigest() == receipt["input_hashes"]["kernel_receipt_sha256"]


def test_leaf_workbench_action_request_surfaces_lowerability_yield_exhaustion(tmp_path: Path):
    project = tmp_path / "arc3_ab12_gov"
    (project / "workspace").mkdir(parents=True)
    request = {
        "capability_id": "mine_worldmodel_lowerable_selectors",
        "input_refs": {"latest_regression_ref": "workspace/latest_patch_base_regression.json"},
        "claim_bindings": ["mine lowerable selectors"],
    }
    thesis = "LEAF_WORKBENCH_ACTION_REQUEST: " + json.dumps(request)

    def fake_handler(project_dir, req, row, contract):
        return {
            "capability_id": "mine_worldmodel_lowerable_selectors",
            "output_summary": json.dumps(
                {
                    "candidate_delta_admissible": False,
                    "candidate_predicates": [],
                    "lowerability_status": "no_zero_error_selector_found",
                }
            ),
        }

    message = leaf_workbench_action_request_retry_message(
        enabled=True,
        project_dir=project,
        thesis_text=thesis,
        records_fn=lambda _project: [
            {
                "capability_id": "mine_worldmodel_lowerable_selectors",
                "source_ref": "workspace/latest_patch_base_regression.json",
                "source_sha": "sha",
                "summary": "lowerability miner",
            }
        ],
        action_handlers={"mine_worldmodel_lowerable_selectors": fake_handler},
    )

    assert message is not None
    assert "WORKBENCH_OBSERVATION_YIELD_EXHAUSTED" in message
    assert "LOWERABILITY_BLOCKED" in message


def test_leaf_workbench_action_request_runs_separating_feature_miner(tmp_path: Path):
    project = tmp_path / "arc3_ab12_gov"
    ws = project / "workspace"
    raw = project / "raw" / "episodes"
    ws.mkdir(parents=True)
    raw.mkdir(parents=True)
    rows = [
            {
                "t": 0,
                "a": 1,
                "s": [[8, 8, 5], [3, 3, 5], [5, 5, 5]],
                "s_next": [[8, 8, 5], [8, 8, 5], [5, 5, 5]],
            },
        {
            "t": 1,
            "a": 1,
            "s": [[3, 3, 5], [8, 8, 5], [3, 3, 5]],
            "s_next": [[3, 3, 5], [3, 3, 5], [3, 3, 5]],
        },
    ]
    (raw / "episode_001.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )
    (ws / "latest_patch_base_regression.json").write_text(
        json.dumps(
            {
                "counterexample_trace": {
                    "first_mismatch_signature": {"bbox": [1, 0, 1, 1]},
                    "mismatch_classes": [
                        {
                            "first_row": 1,
                            "t": 1,
                            "action": 1,
                            "signature": {"bbox": [1, 0, 1, 1]},
                        }
                    ],
                },
                "candidate_regression_receipt": {
                    "candidate_relation": "hard_gate_failure",
                    "quotient_comparison": {
                        "relation": "hard_gate_failure_without_visible_quotient"
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    request = {
        "capability_id": "mine_worldmodel_separating_features",
        "input_refs": {
            "latest_regression_ref": "workspace/latest_patch_base_regression.json",
            "episode_log_ref": "raw/episodes/episode_001.jsonl",
        },
        "claim_bindings": ["mine separator"],
    }

    message = leaf_workbench_action_request_retry_message(
        enabled=True,
        project_dir=project,
        thesis_text="LEAF_WORKBENCH_ACTION_REQUEST: " + json.dumps(request),
    )

    assert message is not None
    receipt_line = next(line for line in message.splitlines() if line.startswith("LEAF_WORKBENCH_RECEIPT:"))
    receipt = json.loads(receipt_line.split(":", 1)[1].strip())
    assert receipt["capability_id"] == "mine_worldmodel_separating_features"
    assert "ztare-worldmodel-separating-feature-miner-v1" in receipt["output_summary"]
    assert '"perfect_on_visible_log":true' in receipt["output_summary"]
    assert '"candidate_predicates":[]' in receipt["output_summary"]
    assert '"support_scoped_predicates":' in receipt["output_summary"]
    assert '"lowering_scope":"quotient_chart_only"' in receipt["output_summary"]


def test_leaf_workbench_action_request_runs_lowerable_selector_miner(tmp_path: Path):
    project = tmp_path / "arc3_ab12_gov"
    ws = project / "workspace"
    raw = project / "raw" / "episodes"
    ws.mkdir(parents=True)
    raw.mkdir(parents=True)
    positive_grid = [[5, 5, 5], [8, 8, 5], [5, 5, 5]]
    rows = [
        {
            "t": 0,
            "a": 1,
            "s": positive_grid,
            "s_next": [[5, 5, 5], [3, 3, 5], [5, 5, 5]],
        },
        {
            "t": 1,
            "a": 0,
            "s": positive_grid,
            "s_next": positive_grid,
        },
        {
            "t": 2,
            "a": 1,
            "s": [[4, 4, 4], [8, 8, 4], [4, 4, 4]],
            "s_next": [[4, 4, 4], [8, 8, 4], [4, 4, 4]],
        },
    ]
    (raw / "episode_001.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )
    (ws / "latest_patch_base_regression.json").write_text(
        json.dumps(
            {
                "counterexample_trace": {
                    "first_mismatch_signature": {"bbox": [1, 0, 1, 1]},
                    "mismatch_classes": [
                        {
                            "first_row": 0,
                            "t": 0,
                            "action": 1,
                            "signature": {"bbox": [1, 0, 1, 1]},
                        }
                    ],
                },
                "candidate_regression_receipt": {
                    "candidate_relation": "hard_gate_failure",
                    "quotient_comparison": {
                        "relation": "hard_gate_failure_without_visible_quotient"
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    request = {
        "capability_id": "mine_worldmodel_lowerable_selectors",
        "input_refs": {
            "latest_regression_ref": "workspace/latest_patch_base_regression.json",
            "episode_log_ref": "raw/episodes/episode_001.jsonl",
        },
        "claim_bindings": ["mine lowerable selector"],
    }

    message = leaf_workbench_action_request_retry_message(
        enabled=True,
        project_dir=project,
        thesis_text="LEAF_WORKBENCH_ACTION_REQUEST: " + json.dumps(request),
    )

    assert message is not None
    receipt_line = next(line for line in message.splitlines() if line.startswith("LEAF_WORKBENCH_RECEIPT:"))
    receipt = json.loads(receipt_line.split(":", 1)[1].strip())
    assert receipt["capability_id"] == "mine_worldmodel_lowerable_selectors"
    summary = json.loads(receipt["output_summary"])
    assert summary["schema"] == "ztare-worldmodel-lowerable-selector-miner-v1"
    assert summary["candidate_delta_admissible"] is True
    assert summary["candidate_predicates"]
    assert summary["candidate_predicates"][0]["lowering_scope"] == "global_carrier_input"
    names = {
        feature["name"]
        for feature in summary["candidate_predicates"][0]["features"]
    }
    assert "window_values" in names
    assert "action" in names


def test_leaf_workbench_action_request_runs_global_carrier_selector_miner(tmp_path: Path):
    project = tmp_path / "arc3_ab12_gov"
    ws = project / "workspace"
    ws.mkdir(parents=True)
    (ws / "latest_level_transfer_probe.json").write_text(
        json.dumps(
            {
                "schema": "ztare-arc3-level-transfer-probe-v1",
                "local_rows": [
                    {
                        "action": 0,
                        "first_diffs": [
                            {"before": 11, "predicted": 11, "observed": 3, "y": 1, "x": 0},
                        ],
                            "local_patch_witness": {
                                "schema": "ztare-local-patch-witness-v1",
                                "bbox": [0, 0, 4, 4],
                                "diff_cells": [
                                    {
                                        "row": 2,
                                        "col": 2,
                                        "before": 11,
                                        "predicted": 11,
                                        "observed": 3,
                                    }
                                ],
                                "before_patch": [
                                    [5, 5, 5, 5, 5],
                                    [5, 4, 4, 4, 5],
                                    [5, 4, 11, 4, 5],
                                    [5, 4, 5, 4, 5],
                                    [5, 5, 5, 5, 5],
                                ],
                                "predicted_patch": [
                                    [5, 5, 5, 5, 5],
                                    [5, 4, 4, 4, 5],
                                    [5, 4, 11, 4, 5],
                                    [5, 4, 5, 4, 5],
                                    [5, 5, 5, 5, 5],
                                ],
                                "observed_patch": [
                                    [5, 5, 5, 5, 5],
                                    [5, 4, 4, 4, 5],
                                    [5, 4, 3, 4, 5],
                                    [5, 4, 5, 4, 5],
                                    [5, 5, 5, 5, 5],
                                ],
                            },
                        },
                        {
                            "action": 1,
                            "first_diffs": [
                                {"before": 8, "predicted": 3, "observed": 8, "y": 2, "x": 2},
                            ],
                            "local_patch_witness": {
                                "schema": "ztare-local-patch-witness-v1",
                                "bbox": [0, 0, 4, 4],
                                "diff_cells": [
                                    {
                                        "row": 2,
                                        "col": 2,
                                        "before": 8,
                                        "predicted": 3,
                                        "observed": 8,
                                    }
                                ],
                                "before_patch": [
                                    [5, 5, 5, 5, 5],
                                    [5, 4, 4, 4, 5],
                                    [5, 4, 8, 4, 5],
                                    [5, 4, 5, 4, 5],
                                    [5, 5, 5, 5, 5],
                                ],
                                "predicted_patch": [
                                    [5, 5, 5, 5, 5],
                                    [5, 4, 4, 4, 5],
                                    [5, 4, 3, 4, 5],
                                    [5, 4, 5, 4, 5],
                                    [5, 5, 5, 5, 5],
                                ],
                                "observed_patch": [
                                    [5, 5, 5, 5, 5],
                                    [5, 4, 4, 4, 5],
                                    [5, 4, 8, 4, 5],
                                    [5, 4, 5, 4, 5],
                                    [5, 5, 5, 5, 5],
                                ],
                            },
                        },
                ],
            }
        ),
        encoding="utf-8",
    )
    request = {
        "capability_id": "mine_worldmodel_global_carrier_selectors_from_observable_context",
        "input_refs": {
            "strategy_gate_receipt_ref": "workspace/latest_level_transfer_probe.json",
        },
        "claim_bindings": ["mine global carrier selector"],
    }

    message = leaf_workbench_action_request_retry_message(
        enabled=True,
        project_dir=project,
        thesis_text="LEAF_WORKBENCH_ACTION_REQUEST: " + json.dumps(request),
    )

    assert message is not None
    receipt_line = next(line for line in message.splitlines() if line.startswith("LEAF_WORKBENCH_RECEIPT:"))
    receipt = json.loads(receipt_line.split(":", 1)[1].strip())
    assert (
        receipt["capability_id"]
        == "mine_worldmodel_global_carrier_selectors_from_observable_context"
    )
    summary = json.loads(receipt["output_summary"])
    assert summary["schema"] == "ztare-worldmodel-global-carrier-selector-miner-v1"
    assert summary["candidate_delta_admissible"] is True
    assert summary["candidate_predicates"]
    assert summary["candidate_predicates"][0]["rewrite"]["observed"] in {3, 8}
    names = {
        feature["name"]
        for feature in summary["candidate_predicates"][0]["features"]
    }
    assert "before_predicted_pair" in names
    assert names & {"cell_before_window", "cell_predicted_window", "cell_before_predicted_window"}


def test_leaf_workbench_action_request_rejects_registered_but_inapplicable_probe(tmp_path: Path):
    project = tmp_path
    (project / "workspace").mkdir()
    request = {
        "capability_id": "inspect_worldmodel_counterexample_context",
        "input_refs": {"latest_eval_ref": "latest_eval_results.json"},
        "claim_bindings": ["need context features"],
    }
    thesis = "LEAF_WORKBENCH_ACTION_REQUEST: " + json.dumps(request)

    message = leaf_workbench_action_request_retry_message(
        enabled=True,
        project_dir=project,
        thesis_text=thesis,
    )

    assert message is not None
    assert "registered_but_not_applicable" in message
    assert "inspect_worldmodel_counterexample_context failed" not in message
    assert "Current applicable action_ids" in message


def test_leaf_workbench_action_request_runs_structural_isomorphism(
    tmp_path: Path,
    monkeypatch,
):
    project = tmp_path
    (project / "workspace").mkdir()

    import ztare.common.leaf_workbench_isomorphism as lwi

    def fake_isomorphism(project_dir, input_refs=None):
        latest = Path(project_dir) / "workspace" / "latest_structural_isomorphism.json"
        latest.write_text(
            json.dumps(
                {
                    "schema": "ztare-leaf-workbench-structural-isomorphism-v1",
                    "mode": "conjecture",
                    "status": "ok",
                }
            ),
            encoding="utf-8",
        )
        return {
            "schema": "ztare-leaf-workbench-structural-isomorphism-v1",
            "mode": "conjecture",
            "status": "ok",
            "receipt_ref": "workspace/latest_structural_isomorphism.json",
            "receipt_sha256": "abc123",
            "input_fingerprint": "fp123",
            "result": {
                "candidate_count": 1,
                "conjectures": [
                    {
                        "mother_structure": "quotient counterexample loop",
                        "prediction_cards": [{"id": "p1"}],
                    }
                ],
            },
        }

    monkeypatch.setattr(lwi, "run_structural_isomorphism_action", fake_isomorphism)
    request = {
        "capability_id": "run_structural_isomorphism",
        "input_refs": {
            "mode": "conjecture",
            "allow_live_query": True,
            "model": "codex",
            "left_state": {"constraint_class": "residual tool mismatch"},
            "right_state": {"constraint_class": "metacognitive skill acquisition"},
        },
        "claim_bindings": ["surface structural instrument"],
    }

    message = leaf_workbench_action_request_retry_message(
        enabled=True,
        project_dir=project,
        thesis_text="LEAF_WORKBENCH_ACTION_REQUEST: " + json.dumps(request),
    )

    assert message is not None
    assert "LEAF_WORKBENCH_RECEIPT:" in message
    assert "run_structural_isomorphism" in message
    assert "mother_structure=quotient counterexample loop" in message


def test_leaf_workbench_action_request_runs_strategy_required_gate(
    tmp_path: Path,
    monkeypatch,
):
    project = tmp_path / "arc3_ls20_gov"
    ws = project / "workspace"
    ws.mkdir(parents=True)
    (project / "test_model.py").write_text("def step(grid, action, t): return grid\n")
    (ws / "level2_seed.json").write_text(json.dumps({"full_sequence_from_reset": [0]}))
    (ws / "strategy_experiments.jsonl").write_text(
        json.dumps(
            {
                "schema": "strategy-experiment-v1",
                "kind": "compressed_counterexample_repair",
                "failure_family": "transfer-card",
                "failure_family_sha": "cardsha",
                "disposition": "open",
                "action_plan": {
                    "seed_prerequisite": {"seed_path": "workspace/level2_seed.json"},
                    "required_next_gate": {
                        "command": "arc3_level_transfer_probe",
                        "success_status": "exact_local_transfer_depth",
                    },
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    import ztare.worldmodel.strategy_gate_actions as sga

    seen_refs: dict[str, object] = {}

    def fake_action(project_dir, input_refs=None):
        seen_refs.update(input_refs or {})
        latest = Path(project_dir) / "workspace" / "latest_level_transfer_probe.json"
        latest.write_text(
            json.dumps(
                {
                    "schema": "ztare-arc3-level-transfer-probe-v1",
                    "status": "exact_local_transfer_depth",
                    "game": "ls20-9607627b",
                }
            ),
            encoding="utf-8",
        )
        return {
            "schema": "ztare-leaf-workbench-arc-level-transfer-probe-result-v1",
            "receipt_ref": "workspace/latest_level_transfer_probe.json",
            "receipt_sha256": "abc123",
            "status": "exact_local_transfer_depth",
            "exact_actions": 4,
            "exact_steps": 16,
            "steps_tested": 16,
        }

    monkeypatch.setattr(sga, "run_strategy_required_gate_action", fake_action)
    request = {
        "capability_id": "run_strategy_required_gate",
        "input_refs": {
            "failure_family_sha": "cardsha",
            "command": "arc3_level_transfer_probe",
            "candidate_path": "test_model.py",
            "post_depth": 4,
        },
        "claim_bindings": ["run required Strategy gate"],
    }
    thesis = "LEAF_WORKBENCH_ACTION_REQUEST: " + json.dumps(request)

    message = leaf_workbench_action_request_retry_message(
        enabled=True,
        project_dir=project,
        thesis_text=thesis,
        candidate_source="def step(grid, action, t):\n    return 'current-candidate'\n",
    )

    assert message is not None
    assert "LEAF_WORKBENCH_RECEIPT:" in message
    assert "run_strategy_required_gate" in message
    assert "exact_local_transfer_depth" in message
    receipt_line = next(line for line in message.splitlines() if line.startswith("LEAF_WORKBENCH_RECEIPT:"))
    receipt = json.loads(receipt_line.split(":", 1)[1].strip())
    assert receipt["capability_id"] == "run_strategy_required_gate"
    assert receipt["input_hashes"]["receipt_ref"] == "workspace/latest_level_transfer_probe.json"
    assert seen_refs["candidate_identity"] == "current_submission"
    assert seen_refs["candidate_path"] != "test_model.py"
    bound_candidate = project / str(seen_refs["candidate_path"])
    assert bound_candidate.is_file()
    assert "current-candidate" in bound_candidate.read_text()
    assert hashlib.sha256(bound_candidate.read_bytes()).hexdigest() == seen_refs["candidate_sha256"]


def test_missing_evidence_strategy_discharge_runs_current_workbench_action(
    tmp_path: Path,
    monkeypatch,
):
    project = tmp_path / "arc3_ls20_gov"
    ws = project / "workspace"
    ws.mkdir(parents=True)
    (project / "test_model.py").write_text("def step(grid, action, t): return grid\n")
    (ws / "latest_harness_weakness.json").write_text(
        json.dumps(
            {
                "schema": "ztare-harness-weakness-receipt-v1",
                "workbench_task": {
                    "admissible_capability_ids": ["run_strategy_required_gate"],
                    "objective": "run the declared Strategy gate",
                },
            }
        ),
        encoding="utf-8",
    )
    (ws / "strategy_experiments.jsonl").write_text(
        json.dumps(
            {
                "schema": "strategy-experiment-v1",
                "kind": "compressed_counterexample_repair",
                "failure_family_sha": "cardsha",
                "disposition": "open",
                "action_plan": {
                    "required_next_gate": {
                        "command": "arc3_level_transfer_probe",
                        "success_status": "exact_local_transfer_depth",
                    },
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    import ztare.worldmodel.strategy_gate_actions as sga

    seen_refs: dict[str, object] = {}

    def fake_action(project_dir, input_refs=None):
        seen_refs.update(input_refs or {})
        latest = Path(project_dir) / "workspace" / "latest_level_transfer_probe.json"
        latest.write_text(
            json.dumps(
                {
                    "schema": "ztare-arc3-level-transfer-probe-v1",
                    "status": "bounded_mismatch",
                }
            ),
            encoding="utf-8",
        )
        return {
            "schema": "ztare-leaf-workbench-arc-level-transfer-probe-result-v1",
            "receipt_ref": "workspace/latest_level_transfer_probe.json",
            "receipt_sha256": hashlib.sha256(latest.read_bytes()).hexdigest(),
            "status": "bounded_mismatch",
            "exact_steps": 0,
            "steps_tested": 4,
        }

    monkeypatch.setattr(sga, "run_strategy_required_gate_action", fake_action)
    receipt = {
        "failure_family_sha": "cardsha",
        "outcome": "blocked",
        "blocker_kind": "missing_evidence",
        "evidence_refs": ["workspace/strategy_experiments.jsonl"],
        "next_action": "run registered gate",
    }
    thesis = "STRATEGY_CARD_DISCHARGE: " + json.dumps(receipt)

    message = strategy_discharge_missing_evidence_action_retry_message(
        enabled=True,
        project_dir=project,
        thesis_text=thesis,
    )

    assert message is not None
    assert "LEAF_WORKBENCH_ACTION_REQUEST_PRECHECK" in message
    assert "LEAF_WORKBENCH_RECEIPT:" in message
    assert "run_strategy_required_gate" in message
    assert seen_refs["candidate_path"] == "test_model.py"


def test_blocked_strategy_discharge_after_gate_runs_next_receipt_morphism(
    tmp_path: Path,
):
    project = tmp_path / "arc3_ls20_gov"
    ws = project / "workspace"
    ws.mkdir(parents=True)
    (ws / "latest_level_transfer_probe.json").write_text(
        json.dumps({"schema": "ztare-arc3-level-transfer-probe-v1", "status": "bounded_mismatch"}),
        encoding="utf-8",
    )
    (ws / "strategy_experiments.jsonl").write_text(
        json.dumps(
            {
                "schema": "strategy-experiment-v1",
                "kind": "compressed_counterexample_repair",
                "failure_family_sha": "cardsha",
                "disposition": "open",
                "action_plan": {
                    "source_receipt": "workspace/latest_level_transfer_probe.json",
                    "required_next_gate": {
                        "command": "arc3_level_transfer_probe",
                        "success_status": "exact_local_transfer_depth",
                    },
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    thesis = "\n".join(
        [
            "LEAF_WORKBENCH_RECEIPT: "
            + json.dumps(
                {
                    "capability_id": "run_strategy_required_gate",
                    "output_summary": "status=bounded_mismatch",
                }
            ),
            "STRATEGY_CARD_DISCHARGE: "
            + json.dumps(
                {
                    "failure_family_sha": "cardsha",
                    "outcome": "blocked",
                    "blocker_kind": "attempted_probe_failed",
                    "evidence_refs": ["workspace/strategy_experiments.jsonl"],
                    "next_action": "next registered boundary morphism",
                }
            ),
        ]
    )
    seen: dict[str, object] = {}

    def fake_handler(project_dir, req, row, contract):
        seen.update(req.get("input_refs") or {})
        return {
            "capability_id": "mine_worldmodel_global_carrier_selectors_from_observable_context",
            "output_summary": json.dumps(
                {
                    "candidate_delta_admissible": False,
                    "lowerability_status": "no_zero_error_selector_found",
                }
            ),
        }

    message = strategy_discharge_missing_evidence_action_retry_message(
        enabled=True,
        project_dir=project,
        thesis_text=thesis,
        records_fn=lambda _project: [
            {
                "capability_id": "mine_worldmodel_global_carrier_selectors_from_observable_context",
                "source_ref": "workspace/latest_level_transfer_probe.json",
                "source_sha": "sha",
                "summary": "selector miner",
            }
        ],
        action_handlers={
            "mine_worldmodel_global_carrier_selectors_from_observable_context": fake_handler,
        },
    )

    assert message is not None
    assert "LEAF_WORKBENCH_ACTION_REQUEST_PRECHECK" in message
    assert "mine_worldmodel_global_carrier_selectors_from_observable_context" in message
    assert seen["strategy_gate_receipt_ref"] == "workspace/latest_level_transfer_probe.json"
    assert seen["source_card_sha"] == "cardsha"


def test_leaf_workbench_action_request_chains_unique_boundary_morphism(tmp_path: Path):
    project = tmp_path / "arc3_ls20_gov"
    ws = project / "workspace"
    ws.mkdir(parents=True)
    (ws / "strategy_experiments.jsonl").write_text(
        json.dumps(
            {
                "schema": "strategy-experiment-v1",
                "kind": "compressed_counterexample_repair",
                "failure_family_sha": "cardsha",
                "disposition": "open",
                "action_plan": {
                    "source_receipt": "workspace/latest_level_transfer_probe.json",
                    "required_next_gate": {
                        "command": "arc3_level_transfer_probe",
                        "success_status": "exact_local_transfer_depth",
                    },
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    request = {
        "capability_id": "run_strategy_required_gate",
        "input_refs": {
            "command": "arc3_level_transfer_probe",
            "failure_family_sha": "cardsha",
        },
        "claim_bindings": ["run required gate"],
    }
    seen: list[str] = []

    def fake_gate(project_dir, req, row, contract):
        seen.append("gate")
        Path(project_dir, "workspace", "latest_level_transfer_probe.json").write_text(
            json.dumps({"schema": "ztare-arc3-level-transfer-probe-v1", "status": "bounded_mismatch"}),
            encoding="utf-8",
        )
        return {
            "capability_id": "run_strategy_required_gate",
            "output_summary": "status=bounded_mismatch",
        }

    def fake_selector(project_dir, req, row, contract):
        seen.append("selector")
        return {
            "capability_id": "mine_worldmodel_global_carrier_selectors_from_observable_context",
            "output_summary": json.dumps(
                {
                    "candidate_delta_admissible": False,
                    "lowerability_status": "no_zero_error_selector_found",
                }
            ),
        }

    message = leaf_workbench_action_request_retry_message(
        enabled=True,
        project_dir=project,
        thesis_text="LEAF_WORKBENCH_ACTION_REQUEST: " + json.dumps(request),
        records_fn=lambda _project: [
            {
                "capability_id": "run_strategy_required_gate",
                "source_ref": "workspace/strategy_experiments.jsonl",
                "source_sha": "sha",
                "summary": "gate",
            },
            {
                "capability_id": "mine_worldmodel_global_carrier_selectors_from_observable_context",
                "source_ref": "workspace/latest_level_transfer_probe.json",
                "source_sha": "sha",
                "summary": "selector",
            },
        ],
        action_handlers={
            "run_strategy_required_gate": fake_gate,
            "mine_worldmodel_global_carrier_selectors_from_observable_context": fake_selector,
        },
    )

    assert message is not None
    assert "unique boundary follow-up" in message
    assert seen == ["gate", "selector"]
    assert message.count("LEAF_WORKBENCH_RECEIPT:") == 2


def test_leaf_workbench_action_request_runs_carrier_contract_on_current_candidate(tmp_path: Path):
    project = tmp_path / "arc3_ls20_gov"
    (project / "workspace").mkdir(parents=True)
    request = {
        "capability_id": "check_worldmodel_carrier_contract",
        "input_refs": {"candidate_path": "test_model.py"},
        "claim_bindings": ["check current carrier contract"],
    }
    thesis = "LEAF_WORKBENCH_ACTION_REQUEST: " + json.dumps(request)
    candidate_source = (
        "def PATCH_DELTA(base_next, state, action, t):\n"
        "    if t == 1:\n"
        "        return base_next\n"
        "    return base_next\n"
    )

    message = leaf_workbench_action_request_retry_message(
        enabled=True,
        project_dir=project,
        thesis_text=thesis,
        candidate_source=candidate_source,
    )

    assert message is not None
    receipt_line = next(line for line in message.splitlines() if line.startswith("LEAF_WORKBENCH_RECEIPT:"))
    receipt = json.loads(receipt_line.split(":", 1)[1].strip())
    assert receipt["capability_id"] == "check_worldmodel_carrier_contract"
    assert receipt["input_hashes"]["source_ref"].startswith("workspace/leaf_workbench_action_candidates/")
    assert "temporal admissibility reject" in receipt["output_summary"]


def test_strategy_required_gate_action_is_content_cached(tmp_path: Path, monkeypatch):
    project = tmp_path / "arc3_ls20_gov"
    ws = project / "workspace"
    ws.mkdir(parents=True)
    (project / "test_model.py").write_text("def step(grid, action, t): return grid\n")
    (ws / "level2_seed.json").write_text(json.dumps({"full_sequence_from_reset": [0]}))
    (ws / "strategy_experiments.jsonl").write_text(
        json.dumps(
            {
                "schema": "strategy-experiment-v1",
                "kind": "compressed_counterexample_repair",
                "failure_family_sha": "cardsha",
                "disposition": "open",
                "action_plan": {
                    "seed_prerequisite": {"seed_path": "workspace/level2_seed.json"},
                    "required_next_gate": {
                        "command": "arc3_level_transfer_probe",
                        "success_status": "exact_local_transfer_depth",
                        "post_depth": 4,
                    },
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    import ztare.worldmodel.strategy_gate_actions as sga

    calls = {"n": 0}

    def fake_handler(project_dir, card, refs):
        calls["n"] += 1
        latest = Path(project_dir) / "workspace" / "latest_level_transfer_probe.json"
        latest.write_text(json.dumps({"status": "bounded_mismatch"}), encoding="utf-8")
        return {
            "receipt_ref": "workspace/latest_level_transfer_probe.json",
            "receipt_sha256": "abc123",
            "status": "bounded_mismatch",
        }

    monkeypatch.setattr(sga, "_run_arc3_level_transfer_probe", fake_handler)
    refs = {
        "failure_family_sha": "cardsha",
        "command": "arc3_level_transfer_probe",
        "candidate_path": "test_model.py",
        "post_depth": 4,
    }

    first = sga.run_strategy_required_gate_action(project, refs)
    latest_digest = hashlib.sha256((ws / "latest_level_transfer_probe.json").read_bytes()).hexdigest()
    assert first["receipt_sha256"] == latest_digest
    assert first["receipt_ref"].startswith(
        "workspace/strategy_gate_receipts/arc3_level_transfer_probe/"
    )
    assert first["result"]["mutable_receipt_ref"] == "workspace/latest_level_transfer_probe.json"
    immutable = project / first["receipt_ref"]
    assert immutable.is_file()

    (ws / "latest_level_transfer_probe.json").write_text(
        json.dumps({"status": "overwritten_elsewhere"}),
        encoding="utf-8",
    )
    second = sga.run_strategy_required_gate_action(project, refs)

    assert calls["n"] == 1
    assert second["cache_hit"] is True
    assert second["receipt_ref"] == first["receipt_ref"]
    assert second["receipt_sha256"] == first["receipt_sha256"]
    cache = json.loads((ws / "strategy_gate_action_cache.json").read_text())
    assert len(cache["entries"]) == 1

    immutable.write_text("corrupt", encoding="utf-8")
    third = sga.run_strategy_required_gate_action(project, refs)
    assert calls["n"] == 2
    assert third.get("cache_hit") is not True


def test_strategy_gate_cache_key_inherits_plan_level_probe_parameters(tmp_path: Path):
    project = tmp_path / "arc3_ls20_gov"
    ws = project / "workspace"
    ws.mkdir(parents=True)
    seed = ws / "level2_seed.json"
    candidate = project / "test_model.py"
    seed.write_text(json.dumps({"full_sequence_from_reset": [0]}), encoding="utf-8")
    candidate.write_text("def step(grid, action, t): return grid\n", encoding="utf-8")
    card = {
        "schema": "strategy-experiment-v1",
        "failure_family_sha": "cardsha",
        "action_plan": {
            "post_depth": 4,
            "max_first_diffs": 17,
            "seed_prerequisite": {"seed_path": "workspace/level2_seed.json"},
            "required_next_gate": {
                "command": "arc3_level_transfer_probe",
                "success_status": "exact_local_transfer_depth",
            },
        },
    }

    import ztare.worldmodel.strategy_gate_actions as sga

    key = sga._strategy_gate_cache_key(  # noqa: SLF001 - cache ABI regression
        project,
        "arc3_level_transfer_probe",
        card,
        {"candidate_path": "test_model.py"},
    )

    assert key["params"]["post_depth"] == 4
    assert key["params"]["max_first_diffs"] == 17
    assert key["card_canonical_sha256"]
    assert "strategy_ledger_sha256" in key


def test_strategy_gate_ref_resolution_confines_paths_to_project(tmp_path: Path):
    project = tmp_path / "arc3_ls20_gov"
    ws = project / "workspace"
    ws.mkdir(parents=True)
    inside = ws / "seed.json"
    inside.write_text("{}", encoding="utf-8")
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")

    import ztare.worldmodel.strategy_gate_actions as sga

    assert sga._resolve_project_ref(project, "workspace/seed.json") == inside.resolve()  # noqa: SLF001
    assert sga._resolve_project_ref(  # noqa: SLF001
        project,
        f"projects/{project.name}/workspace/seed.json",
    ) == inside.resolve()
    with pytest.raises(ValueError, match="escapes project"):
        sga._resolve_project_ref(project, str(outside))  # noqa: SLF001
    with pytest.raises(ValueError, match="escapes project"):
        sga._resolve_project_ref(project, "../outside.json")  # noqa: SLF001


def test_strategy_gate_selection_ignores_unregistered_open_cards_for_unqualified_request(
    tmp_path: Path,
):
    project = tmp_path / "arc3_ls20_gov"
    ws = project / "workspace"
    ws.mkdir(parents=True)
    (ws / "strategy_experiments.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "schema": "strategy-experiment-v1",
                        "failure_family_sha": "old",
                        "disposition": "open",
                        "action_plan": {
                            "required_next_gate": {
                                "command": "replay_diagnostics",
                            },
                        },
                    }
                ),
                json.dumps(
                    {
                        "schema": "strategy-experiment-v1",
                        "failure_family_sha": "active",
                        "disposition": "open",
                        "action_plan": {
                            "seed_prerequisite": {"seed_path": "workspace/level2_seed.json"},
                            "required_next_gate": {
                                "command": "arc3_level_transfer_probe",
                                "success_status": "exact_local_transfer_depth",
                            },
                        },
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    import ztare.worldmodel.strategy_gate_actions as sga

    selected = sga._select_strategy_card(project, {})  # noqa: SLF001 - selection ABI regression

    assert selected["failure_family_sha"] == "active"


def test_strategy_gate_workbench_surface_comes_from_strategy_card(tmp_path: Path):
    project = tmp_path / "arc3_ab12_gov"
    ws = project / "workspace"
    ws.mkdir(parents=True)
    seed = ws / "level_boundary_seed_current.json"
    seed.write_text(json.dumps({"full_sequence_from_reset": [0, 1]}), encoding="utf-8")
    (ws / "strategy_experiments.jsonl").write_text(
        json.dumps(
            {
                "schema": "strategy-experiment-v1",
                "kind": "compressed_counterexample_repair",
                "failure_family": "transfer-card",
                "disposition": "open",
                "action_plan": {
                    "seed_prerequisite": {
                        "seed_path": "projects/arc3_ab12_gov/workspace/level_boundary_seed_current.json"
                    },
                    "required_next_gate": {
                        "command": "arc3_level_transfer_probe",
                        "success_status": "exact_local_transfer_depth",
                    },
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    from ztare.worldmodel.leaf_workbench import (
        render_worldmodel_leaf_workbench_fragment,
        worldmodel_leaf_workbench_records,
    )

    rows = worldmodel_leaf_workbench_records(project)
    transfer = next(row for row in rows if row["capability_id"] == "run_strategy_required_gate")
    assert transfer["source_ref"] == "workspace/strategy_experiments.jsonl"
    assert transfer["command"] == "arc3_level_transfer_probe"
    assert transfer["failure_family_sha"]
    assert "workspace/level_boundary_seed_current.json" in transfer["summary"]
    assert "level2_seed" not in transfer["summary"]
    fragment = render_worldmodel_leaf_workbench_fragment(project)
    assert "current candidate-bound action request(s)" in fragment
    assert '"capability_id":"run_strategy_required_gate"' in fragment
    assert '"candidate_path":"test_model.py"' in fragment
    assert f'"failure_family_sha":"{transfer["failure_family_sha"]}"' in fragment


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


def test_evaluation_cache_key_changes_when_harness_changes(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    candidate = project / "test_model.py"
    rubric = project / "rubric.json"
    evidence = project / "evidence.txt"
    candidate.write_text("def step(grid, action, t): return grid\n", encoding="utf-8")
    rubric.write_text('{"rubric_id": "x"}\n', encoding="utf-8")
    evidence.write_text("episode-sha=a\n", encoding="utf-8")
    gate_payload = {
        "harness_ok": True,
        "gated_sha256": "candidate",
        "gates": [{"name": "visible", "pass": True}],
    }

    _write_harness(project, "print('v1')\n")
    key_v1 = evaluation_cache_key(
        project_dir=project,
        candidate_path=candidate,
        gate_payload=gate_payload,
        rubric_path=rubric,
        extra_paths=[evidence],
    )
    _write_harness(project, "print('v2')\n")
    key_v2 = evaluation_cache_key(
        project_dir=project,
        candidate_path=candidate,
        gate_payload=gate_payload,
        rubric_path=rubric,
        extra_paths=[evidence],
    )

    assert key_v1["key_sha256"] != key_v2["key_sha256"]
    assert key_v1["project_gate_harness_sha256"] != key_v2["project_gate_harness_sha256"]
    assert key_v1["pre_judge_gate_module_sha256"]
    assert key_v1["test_thesis_module_sha256"]
    assert key_v1["autoresearch_loop_module_sha256"]
    assert key_v1["worldmodel_gates_module_sha256"]
    assert key_v1["patch_base_carrier_module_sha256"]


def test_evaluation_cache_round_trip_requires_exact_key(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "workspace").mkdir()
    candidate = project / "test_model.py"
    rubric = project / "rubric.json"
    candidate.write_text("def step(grid, action, t): return grid\n", encoding="utf-8")
    rubric.write_text('{"rubric_id": "x"}\n', encoding="utf-8")
    _write_harness(project, "print('stable')\n")
    gate_payload = {
        "harness_ok": True,
        "gated_sha256": "candidate",
        "gates": [{"name": "visible", "pass": True}],
    }
    key = evaluation_cache_key(
        project_dir=project,
        candidate_path=candidate,
        gate_payload=gate_payload,
        rubric_path=rubric,
    )

    store_cached_evaluation(
        project_dir=project,
        cache_key=key,
        evaluation={"score": 80, "weakest_point": "bounded status"},
    )

    cached = load_cached_evaluation(project, key)
    assert cached is not None
    assert cached["score"] == 80
    assert cached["evaluation_cache_hit"] is True
    assert cached["cache_verdict"] == "cache_hit"

    changed_payload = dict(gate_payload)
    changed_payload["score"] = 1.0
    changed_key = evaluation_cache_key(
        project_dir=project,
        candidate_path=candidate,
        gate_payload=changed_payload,
        rubric_path=rubric,
    )
    assert changed_key["key_sha256"] != key["key_sha256"]
    changed = load_cached_evaluation(project, changed_key)
    assert changed is None or changed.get("cache_verdict") == "corrupt_cache"


def test_rollout_timeout_appends_complexity_verdict_receipt(tmp_path: Path):
    """A harness that sleeps past the budget must append a gate_complexity_verdict receipt.

    Uses a 1-second budget and a harness that sleeps 10 seconds. The timeout fires
    in run_gate_harness_subprocess, which must:
      1. Write a receipt row with schema ztare.gate_complexity_verdict.v1 and verdict=timeout.
      2. Include candidate_ref and budget_seconds so the receipt identifies the candidate.
      3. Re-raise (as RuntimeError) so run_pre_judge_gate_harness fails closed.
    """
    project = tmp_path / "project"
    project.mkdir()
    (project / "workspace").mkdir()
    latest = project / "latest_eval_results.json"
    candidate = project / "slow_candidate.py"
    candidate.write_text("def step(s, a, t): return s\n", encoding="utf-8")

    # Harness sleeps forever — will be killed by the budget
    _write_harness(project, "import time\ntime.sleep(9999)\n")

    result = run_pre_judge_gate_harness(
        enabled=True,
        project_dir=project,
        latest_eval_results_path=latest,
        python_executable=sys.executable,
        timeout_seconds=1,
        candidate_path=candidate,
    )

    # Gate must fail closed
    assert result.should_skip_judge is True
    assert result.score_cap_reason in (
        "pre_judge_gate_harness_error",
        "pre_judge_gate_harness_failed",
    )

    # Receipt must exist with the complexity verdict
    receipt_path = project / "workspace" / "pre_judge_gate_receipts.jsonl"
    assert receipt_path.exists(), "pre_judge_gate_receipts.jsonl must be written on timeout"
    rows = [json.loads(l) for l in receipt_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    timeout_rows = [r for r in rows if r.get("schema") == "ztare.gate_complexity_verdict.v1"]
    assert timeout_rows, f"no gate_complexity_verdict.v1 row found; got: {rows}"
    row = timeout_rows[-1]
    assert row["verdict"] == "timeout"
    assert row["budget_seconds"] == 1
    assert row["candidate_ref"] == str(candidate)
    assert row["stage"] == "gate_harness_subprocess"
    # Example receipt for documentation
    # {"schema": "ztare.gate_complexity_verdict.v1", "verdict": "timeout",
    #  "stage": "gate_harness_subprocess", "budget_seconds": 1,
    #  "candidate_ref": "...", "candidate_sha": "..."}
