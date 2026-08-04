from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

from ztare.common.leaf_workbench_contract import (
    LeafWorkbenchCapability,
    LeafWorkbenchContract,
)
from ztare.validator.core.pre_judge_gate import (
    _append_gate_receipt,
    bind_pre_judge_gate_payload,
    consume_pre_judge_gate_receipt,
    detect_patch_base_regression_preflight,
    evaluation_cache_key,
    load_bound_pre_judge_gate_payload,
    load_cached_evaluation,
    run_pre_judge_gate_harness,
    store_cached_evaluation,
)
from ztare.validator.core.repair_preflight import ambient_carrier_dependency_retry_message
from ztare.validator.core.repair_preflight import boundary_cegar_ready_delta_retry_message
from ztare.validator.core.repair_preflight import leaf_workbench_action_request_retry_message
from ztare.validator.core.repair_preflight import leaf_workbench_retry_message
from ztare.validator.core.repair_preflight import patch_base_regression_retry_message
from ztare.validator.core.repair_preflight import _persist_retry_frontier_candidate
from ztare.validator.core.repair_preflight import (
    blocked_control_missing_evidence_action_retry_message,
)
from ztare.validator.core.repair_preflight import strategy_card_retry_message


def _write_harness(project: Path, body: str) -> None:
    (project / "gate_harness.py").write_text(body, encoding="utf-8")


def _write_prior_submission(project: Path, name: str = "iter_001.py") -> str:
    path = project / "workspace" / "submissions" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("def step(grid, action, t): return tuple(grid)\n", encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_bound_gate_payload_preserves_identity_and_rejects_transport_mutation():
    payload = {
        "gated_sha256": "a" * 64,
        "evidence_epoch": {"epoch_sha256": "b" * 64},
        "gates": {"visible_replay_exact": {"passed": True}},
    }

    with bind_pre_judge_gate_payload(payload, base_env={}) as env:
        path = Path(env["ZTARE_CURRENT_PRE_JUDGE_GATE_PAYLOAD_PATH"])
        assert load_bound_pre_judge_gate_payload(environ=env) == payload
        path.write_text('{"gated_sha256":"altered"}', encoding="utf-8")
        with pytest.raises(RuntimeError, match="digest mismatch"):
            load_bound_pre_judge_gate_payload(environ=env)

    assert not path.exists()


def test_consumed_gate_receipt_binds_candidate_and_uses_authority_decision(tmp_path: Path):
    candidate = tmp_path / "candidate.py"
    candidate.write_text("VALUE = 1\n", encoding="utf-8")
    candidate_sha = hashlib.sha256(candidate.read_bytes()).hexdigest()
    payload = {
        "gated_sha256": candidate_sha[:16],
        "harness_ok": True,
        "gates": {"observed": {"name": "observed", "pass": True}},
        "pre_judge_decision": {
            "evaluator_authorized": True,
            "candidate_promotion_authorized": False,
            "authority_scope": "search_incumbent_selection",
            "task_discharge_authorized": False,
        },
    }

    consumed = consume_pre_judge_gate_receipt(payload, candidate_path=candidate)

    assert consumed["evaluator_authorized"] is True
    assert consumed["candidate_promotion_authorized"] is False
    assert consumed["authority_scope"] == "search_incumbent_selection"
    assert consumed["task_discharge_authorized"] is False
    assert consumed["candidate_sha256"] == candidate_sha
    candidate.write_text("VALUE = 2\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="candidate identity mismatch"):
        consume_pre_judge_gate_receipt(payload, candidate_path=candidate)


def test_gate_result_cache_survives_process_boundary_and_binds_live_bytes(tmp_path: Path):
    from ztare.validator.core import pre_judge_gate

    project = tmp_path / "project"
    workspace = project / "workspace"
    workspace.mkdir(parents=True)
    candidate = project / "test_model.py"
    candidate.write_text("def step(state, action, t): return state\n", encoding="utf-8")
    _write_harness(
        project,
        """import json
from pathlib import Path
p = Path('workspace/gate_runs.txt')
n = int(p.read_text()) + 1 if p.exists() else 1
p.write_text(str(n))
print(json.dumps({'harness_ok': True, 'gates': {'g': {'pass': True}}}))
""",
    )

    kwargs = {
        "project_dir": project,
        "python_executable": sys.executable,
        "gate_harness_path": project / "gate_harness.py",
        "candidate_path": None,
        "timeout_seconds": 10,
    }
    first = pre_judge_gate.run_gate_harness_subprocess(**kwargs)
    pre_judge_gate._GATE_RESULT_CACHE.clear()
    second = pre_judge_gate.run_gate_harness_subprocess(**kwargs)

    assert first == second
    assert (workspace / "gate_runs.txt").read_text() == "1"

    candidate.write_text("def step(state, action, t): return tuple(state)\n", encoding="utf-8")
    pre_judge_gate._GATE_RESULT_CACHE.clear()
    pre_judge_gate.run_gate_harness_subprocess(**kwargs)
    assert (workspace / "gate_runs.txt").read_text() == "2"


def test_gate_result_cache_can_be_owned_by_a_separate_writable_workspace(
    tmp_path: Path,
):
    from ztare.validator.core import pre_judge_gate

    project = tmp_path / "authority" / "project"
    project.mkdir(parents=True)
    candidate = project / "test_model.py"
    candidate.write_text(
        "def step(state, action, t): return state\n",
        encoding="utf-8",
    )
    _write_harness(
        project,
        "import json\nprint(json.dumps({'harness_ok': True, 'gates': {}}))\n",
    )
    leaf_cache = tmp_path / "leaf" / "workspace" / "gate_result_cache"

    pre_judge_gate.run_gate_harness_subprocess(
        project_dir=project,
        python_executable=sys.executable,
        gate_harness_path=project / "gate_harness.py",
        candidate_path=candidate,
        timeout_seconds=10,
        workspace_cache_dir=leaf_cache,
    )

    assert list(leaf_cache.glob("*.json"))
    assert not (project / "workspace" / "gate_result_cache").exists()


def test_gate_subprocess_resolves_slash_relative_python_before_project_cwd(
    tmp_path: Path,
):
    from ztare.validator.core import pre_judge_gate

    project = tmp_path / "project"
    project.mkdir()
    _write_harness(
        project,
        "import json\nprint(json.dumps({'harness_ok': True, 'gates': {}}))\n",
    )
    relative_python = os.path.relpath(Path(sys.executable).resolve(), Path.cwd())

    stdout = pre_judge_gate.run_gate_harness_subprocess(
        project_dir=project,
        python_executable=relative_python,
        gate_harness_path=project / "gate_harness.py",
        candidate_path=None,
        timeout_seconds=10,
    )

    assert json.loads(stdout)["harness_ok"] is True


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
            "  'candidate_promotion_authorized': False,\n"
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
    assert result.payload["pre_judge_decision"]["evaluator_authorized"] is True
    assert (
        result.payload["pre_judge_decision"]["candidate_promotion_authorized"]
        is False
    )
    assert (
        result.payload["pre_judge_decision"]["authority_scope"]
        == "search_incumbent_selection"
    )
    assert (
        result.payload["pre_judge_decision"]["task_discharge_authorized"]
        is False
    )
    assert not latest.exists()


def test_deterministic_gate_only_contract_completes_evaluation(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    latest = project / "latest_eval_results.json"
    _write_harness(
        project,
        (
            "import json\n"
            "print(json.dumps({\n"
            "  'harness_ok': True,\n"
            "  'score': 1.0,\n"
            "  'score_contract': 'deterministic_gates_only',\n"
            "  'gates': [\n"
            "    {'name': 'replay', 'tier': 'observed', 'pass': True},\n"
            "    {'name': 'rollout', 'tier': 'heldout', 'pass': True}\n"
            "  ]\n"
            "}))\n"
        ),
    )

    result = run_pre_judge_gate_harness(
        enabled=True,
        project_dir=project,
        latest_eval_results_path=latest,
        python_executable=sys.executable,
    )

    assert result.should_skip_judge is True
    assert result.payload["pre_judge_decision"]["evaluation_authority"] == (
        "deterministic_gate"
    )
    assert result.payload["pre_judge_decision"]["gate_contract_closed"] is True
    evaluation = json.loads(latest.read_text(encoding="utf-8"))
    assert evaluation["score"] == 100
    assert evaluation["raw_judge_score"] == 100
    assert evaluation["pre_judge_gate_payload"]["score_contract"] == (
        "deterministic_gates_only"
    )


def test_same_carrier_same_evidence_is_evaluable_but_not_repromoted(
    tmp_path: Path,
):
    project = tmp_path / "project"
    submissions = project / "workspace" / "submissions"
    submissions.mkdir(parents=True)
    latest = project / "latest_eval_results.json"
    candidate = submissions / "candidate.py"
    candidate.write_text("def step(state, action, t): return state\n", encoding="utf-8")
    _write_harness(
        project,
        (
            "import argparse, hashlib, json\n"
            "from pathlib import Path\n"
            "p=argparse.ArgumentParser(); p.add_argument('--emit-deterministic-gates', action='store_true'); p.add_argument('--candidate-path'); a=p.parse_args()\n"
            "sha=hashlib.sha256(Path(a.candidate_path).read_bytes()).hexdigest()[:16]\n"
            "print(json.dumps({'harness_ok':True,'gated_sha256':sha,'score':1.0,'score_contract':'deterministic_gates_only','description_length':10,'description_length_unit':'source_token_closure_v1','gates':{'visible_replay_exact':{'name':'visible_replay_exact','tier':'observed','pass':True,'diagnostics':{'checked_rows':1,'exact_rows':1,'wrong_cell_count':0}},'holdout_rollout_exact':{'name':'holdout_rollout_exact','tier':'heldout','value':1,'threshold':1,'pass':True}}}))\n"
        ),
    )

    first = run_pre_judge_gate_harness(
        enabled=True,
        project_dir=project,
        latest_eval_results_path=latest,
        python_executable=sys.executable,
        candidate_path=candidate,
    )
    second = run_pre_judge_gate_harness(
        enabled=True,
        project_dir=project,
        latest_eval_results_path=latest,
        python_executable=sys.executable,
        candidate_path=candidate,
    )

    assert first.payload["pre_judge_decision"]["candidate_promotion_authorized"] is True
    assert second.payload["pre_judge_decision"]["evaluator_authorized"] is True
    assert second.payload["pre_judge_decision"]["candidate_promotion_authorized"] is False
    assert second.payload["pre_judge_decision"]["model_selection_relation"] == (
        "same_carrier_same_evidence"
    )


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
    prior_sha = _write_prior_submission(project)
    (project / "workspace" / "candidate_memory.json").write_text(
        json.dumps({
            "schema": "ztare-candidate-memory-v1",
            "records": [{
                "source_type": "deterministic_near_miss",
                "submission": "workspace/submissions/iter_001.py",
                    "sha": prior_sha,
                    "visible_exact_rows": 10,
                    "visible_checked_rows": 12,
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


def test_task_hypothesis_tie_is_admitted_without_carrier_promotion_or_memory(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    latest = project / "latest_eval_results.json"
    candidate = project / "workspace" / "submissions" / "task_companion.py"
    candidate.parent.mkdir(parents=True)
    candidate.write_text("def step(grid, action, t): return grid\n", encoding="utf-8")
    prior_sha = _write_prior_submission(project)
    memory_path = project / "workspace" / "candidate_memory.json"
    memory_path.write_text(
        json.dumps(
            {
                "schema": "ztare-candidate-memory-v1",
                "records": [
                    {
                        "source_type": "full_survivor",
                        "submission": "workspace/submissions/iter_001.py",
                        "sha": prior_sha,
                        "visible_checked_rows": 10,
                        "visible_exact_rows": 10,
                        "visible_wrong_cells": 0,
                        "holdout_depth": 16,
                        "gate_score": 1.0,
                        "description_length": 100,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    _write_harness(
        project,
        (
            "import json\n"
            "print(json.dumps({\n"
            "  'score': 1.0, 'score_contract': 'deterministic_gates_only',\n"
            "  'description_length': 120, 'harness_ok': True, 'gates': {\n"
            "    'visible_replay_exact': {'name': 'visible_replay_exact', "
            "'tier': 'observed', 'pass': True, 'diagnostics': {"
            "'checked_rows': 10, 'exact_rows': 10, 'wrong_cell_count': 0}},\n"
            "    'holdout_rollout_exact': {'name': 'holdout_rollout_exact', "
            "'tier': 'heldout', 'value': 16, 'threshold': 16, 'pass': True}\n"
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
        artifact_role="task_hypothesis",
    )

    decision = result.payload["pre_judge_decision"]
    assert result.should_skip_judge is True
    assert decision["evaluator_authorized"] is True
    assert decision["candidate_promotion_authorized"] is False
    assert decision["authority_scope"] == "task_hypothesis_admissibility"
    assert decision["model_selection_relation"] == (
        "behaviorally_equivalent_role_companion"
    )
    records = json.loads(memory_path.read_text())["records"]
    assert len(records) == 2
    task_records = [
        row for row in records if row.get("artifact_role") == "task_hypothesis"
    ]
    assert len(task_records) == 1
    assert not (project / "workspace" / "latest_harness_weakness.json").exists()


def test_task_hypothesis_companion_cannot_remain_a_carrier_repair_task(
    tmp_path: Path,
) -> None:
    from ztare.common.leaf_workbench_executor import (
        active_workbench_task_capability_scope,
    )

    workspace = tmp_path / "workspace"
    submissions = workspace / "submissions"
    submissions.mkdir(parents=True)
    source = (
        "TASK_HYPOTHESIS_PROVENANCE = {"
        "'schema': 'ztare-task-hypothesis-companion-v1'}\n"
        "def step(state, action, t): return state\n"
    )
    candidate = submissions / "task_companion.py"
    candidate.write_text(source, encoding="utf-8")
    digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
    (workspace / "latest_harness_weakness.json").write_text(
        json.dumps(
            {
                "active_frontier": {
                    "candidate_sha": digest,
                    "source_ref": "workspace/submissions/task_companion.py",
                },
                "workbench_task": {
                    "task_id": "wrong-role-task",
                    "source_ref": "workspace/submissions/task_companion.py",
                    "source_sha256": digest,
                    "admissible_capability_ids": ["run_visible_json_probe"],
                },
            }
        ),
        encoding="utf-8",
    )

    scope, task = active_workbench_task_capability_scope(tmp_path)

    assert scope == frozenset()
    assert task == {}


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
    prior_sha = _write_prior_submission(project)
    (project / "workspace" / "candidate_memory.json").write_text(
        json.dumps({
            "schema": "ztare-candidate-memory-v1",
            "records": [{
                "source_type": "deterministic_near_miss",
                "submission": "workspace/submissions/iter_001.py",
                "sha": prior_sha,
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
    prior_sha = _write_prior_submission(project)
    (project / "workspace" / "candidate_memory.json").write_text(
        json.dumps({
            "schema": "ztare-candidate-memory-v1",
            "records": [{
                "source_type": "deterministic_near_miss",
                "submission": "workspace/submissions/iter_001.py",
                "sha": prior_sha,
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


def test_patch_base_preflight_uses_compression_to_canonicalize_behavioral_tie(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    candidate = project / "workspace" / "probe.py"
    candidate.parent.mkdir(parents=True)
    candidate.write_text("def step(grid, action, t): return grid\n", encoding="utf-8")
    prior_sha = _write_prior_submission(project)
    (project / "workspace" / "candidate_memory.json").write_text(
        json.dumps(
            {
                "schema": "ztare-candidate-memory-v1",
                "records": [
                    {
                        "source_type": "deterministic_near_miss",
                        "submission": "workspace/submissions/iter_001.py",
                        "sha": prior_sha,
                        "visible_exact_rows": 20,
                        "visible_wrong_cells": 4,
                        "holdout_depth": 0,
                        "gate_score": 0.3333,
                        "description_length": 200,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    _write_harness(
        project,
        (
            "import json\n"
            "print(json.dumps({\n"
            "  'score': 0.3333, 'description_length': 100, "
            "'description_length_unit': 'source_token_closure_v1',\n"
            "  'harness_ok': True, 'gates': {\n"
            "    'visible_replay_exact': {'name': 'visible_replay_exact', "
            "'value': 1, 'threshold': 0, 'pass': False, "
            "'diagnostics': {'checked_rows': 24, 'exact_rows': 20, "
            "'wrong_rows': 1, 'wrong_cell_count': 4, "
            "'first_mismatch': 'same behavior, shorter carrier'}},\n"
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
    assert receipt["exact_rows_delta"] == 0
    assert receipt["wrong_cells_delta"] == 0
    assert receipt["description_length_delta"] == -100


def test_best_prior_excludes_abbreviated_presentation_of_candidate_sha(
    tmp_path: Path,
) -> None:
    from ztare.validator.core.pre_judge_gate import _best_prior_candidate_record

    submissions = tmp_path / "workspace" / "submissions"
    submissions.mkdir(parents=True)
    current = submissions / "current.py"
    prior = submissions / "prior.py"
    current.write_text("def step(grid, action, t): return grid\n", encoding="utf-8")
    prior.write_text("def step(grid, action, t): return tuple(grid)\n", encoding="utf-8")
    current_sha = hashlib.sha256(current.read_bytes()).hexdigest()
    prior_sha = hashlib.sha256(prior.read_bytes()).hexdigest()
    (tmp_path / "workspace" / "candidate_memory.json").write_text(
        json.dumps(
            {
                "schema": "ztare-candidate-memory-v1",
                "records": [
                    {
                        "source_type": "full_survivor",
                        "submission": "workspace/submissions/current.py",
                        "sha": current_sha[:12],
                        "visible_checked_rows": 10,
                        "visible_exact_rows": 10,
                        "visible_wrong_cells": 0,
                        "holdout_depth": 4,
                        "gate_score": 1.0,
                    },
                    {
                        "source_type": "deterministic_near_miss",
                        "submission": "workspace/submissions/prior.py",
                        "sha": prior_sha[:12],
                        "visible_checked_rows": 10,
                        "visible_exact_rows": 9,
                        "visible_wrong_cells": 1,
                        "holdout_depth": 4,
                        "gate_score": 0.5,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    selected = _best_prior_candidate_record(tmp_path, exclude_sha=current_sha)

    assert selected is not None
    assert selected["sha"] == prior_sha[:12]


def test_patch_base_preflight_uses_receipt_owned_current_frontier(tmp_path: Path):
    from ztare.common.observation_chart import capture_project_evidence_epoch

    project = tmp_path / "project"
    submissions = project / "workspace" / "submissions"
    submissions.mkdir(parents=True)
    old_source = "def step(grid, action, t):\n    return grid\n"
    old_path = submissions / "old.py"
    old_path.write_text(old_source, encoding="utf-8")
    frontier_source = "def step(grid, action, t):\n    return [list(r) for r in grid]\n"
    frontier_path = submissions / "frontier.py"
    frontier_path.write_text(frontier_source, encoding="utf-8")
    challenger = project / "workspace" / "challenger.py"
    challenger.write_text("def step(grid, action, t):\n    return tuple(grid)\n", encoding="utf-8")
    (project / "workspace" / "candidate_memory.json").write_text(
        json.dumps({
            "schema": "ztare-candidate-memory-v1",
            "records": [{
                "source_type": "deterministic_near_miss",
                "submission": "workspace/submissions/old.py",
                "sha": hashlib.sha256(old_source.encode()).hexdigest(),
                "visible_exact_rows": 8,
                "visible_wrong_cells": 9,
                "holdout_depth": 0,
                "gate_score": 0.3333,
            }],
        }),
        encoding="utf-8",
    )
    epoch = capture_project_evidence_epoch(project)
    (project / "workspace" / "latest_patch_base_regression.json").write_text(
        json.dumps({
            "schema": "ztare-latest-patch-base-regression-v1",
            "evidence_epoch": epoch.to_dict(),
            "candidate_regression_receipt": {
                "candidate_relation": "improved_but_gate_failed",
                "candidate_submission": "workspace/submissions/frontier.py",
                "candidate_sha": hashlib.sha256(frontier_source.encode()).hexdigest(),
                "candidate_exact_rows": 9,
                "candidate_wrong_cells": 2,
                "candidate_holdout_depth": 0,
                "candidate_gate_score": 0.3333,
                "quotient_comparison": {},
            },
        }),
        encoding="utf-8",
    )
    _write_harness(
        project,
        (
            "import json\n"
            "print(json.dumps({\n"
            "  'score': 0.3333, 'harness_ok': True, 'gates': {\n"
            "    'visible_replay_exact': {'pass': False, 'diagnostics': {"
            "'checked_rows': 10, 'exact_rows': 9, 'wrong_rows': 1, "
            "'wrong_cell_count': 2, 'first_mismatch': 'same frontier'}},\n"
            "    'holdout_rollout_exact': {'pass': False, 'value': 0}\n"
            "  }\n"
            "}))\n"
        ),
    )

    result = detect_patch_base_regression_preflight(
        enabled=True,
        project_dir=project,
        candidate_path=challenger,
        python_executable=sys.executable,
    )

    assert result is not None
    receipt = result.regression_receipt
    assert receipt["candidate_relation"] == "no_strict_improvement"
    assert receipt["best_prior_submission"] == "workspace/submissions/frontier.py"
    assert receipt["best_prior_exact_rows"] == 9
    assert receipt["best_prior_wrong_cells"] == 2


def test_patch_base_preflight_preserves_comparison_for_improved_failed_candidate(
    tmp_path: Path,
):
    project = tmp_path / "project"
    project.mkdir()
    candidate = project / "workspace" / "probe.py"
    candidate.parent.mkdir(parents=True)
    candidate.write_text("def step(grid, action, t): return grid\n", encoding="utf-8")
    prior_sha = _write_prior_submission(project)
    (project / "workspace" / "candidate_memory.json").write_text(
        json.dumps({
            "schema": "ztare-candidate-memory-v1",
            "records": [{
                "source_type": "deterministic_near_miss",
                "submission": "workspace/submissions/iter_001.py",
                "sha": prior_sha,
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
    prior = project / "workspace" / "submissions" / "iter_001.py"
    prior.parent.mkdir(parents=True)
    prior_source = "def step(grid, action, t):\n    return grid\n"
    prior.write_text(prior_source, encoding="utf-8")
    prior_sha = hashlib.sha256(prior_source.encode("utf-8")).hexdigest()
    (project / "workspace" / "candidate_memory.json").write_text(
        json.dumps({
            "schema": "ztare-candidate-memory-v1",
            "records": [{
                "source_type": "deterministic_near_miss",
                "submission": "workspace/submissions/iter_001.py",
                    "sha": prior_sha,
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


def test_retry_frontier_candidate_is_content_addressed(tmp_path: Path) -> None:
    source = "def step(grid, action, t):\n    return grid\n"

    ref, digest = _persist_retry_frontier_candidate(tmp_path, source)
    ref_again, digest_again = _persist_retry_frontier_candidate(tmp_path, source)

    assert ref == ref_again
    assert digest == digest_again == hashlib.sha256(source.encode()).hexdigest()
    assert (tmp_path / ref).read_text(encoding="utf-8") == source


def test_diagnostic_receipt_write_failure_cannot_change_gate_consequence(
    tmp_path: Path,
) -> None:
    (tmp_path / "workspace").write_text("read-only boundary", encoding="utf-8")

    assert _append_gate_receipt(tmp_path, {"verdict": "failed"}) is False


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
    assert "mine_worldmodel_lowerable_selectors" in message
    assert "stateless probe" in message
    latest_weakness = json.loads(
        (project / "workspace" / "latest_harness_weakness.json").read_text(
            encoding="utf-8"
        )
    )
    assert latest_weakness["weakness_class"] == "visible_counterexample_trace_unfactored"
    assert latest_weakness["recommended_route"] == "inspect_visible_regression_trace_then_refine_or_propose_capability"
    assert latest_weakness["recommended_capability_id"] == "mine_worldmodel_lowerable_selectors"
    task = latest_weakness["workbench_task"]
    assert task["schema"] == "ztare-leaf-workbench-task-v1"
    assert task["failure_class"] == "visible_counterexample_trace_unfactored"
    assert task["admissible_capability_ids"][0] == "mine_worldmodel_lowerable_selectors"
    assert "run_visible_json_probe" in task["admissible_capability_ids"]
    assert len(task["visible_artifact_refs"]) == 1
    assert task["visible_artifact_refs"][0].startswith(
        "workspace/submissions/retry_frontier_"
    )
    assert (project / task["visible_artifact_refs"][0]).is_file()
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
    assert task_record["capability_id"] == "mine_worldmodel_lowerable_selectors"
    assert (
        f"visible_artifacts={task['visible_artifact_refs']}"
        in task_record["summary"]
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
        candidate_source="def step(grid, action, t): return grid\n",
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
    receipt_dir = project / "workspace" / "leaf_workbench_action_receipts"
    receipt_dir.mkdir(parents=True)
    capability_id = "inspect_worldmodel_counterexample_context"
    receipt_file = receipt_dir / "parent.json"
    receipt_file.write_text(
        json.dumps(
            {
                "schema": "ztare-leaf-workbench-kernel-receipt-v1",
                "capability_id": capability_id,
                "request": {"capability_id": capability_id, "input_refs": {}},
                "receipt": {"capability_id": capability_id},
            }
        ),
        encoding="utf-8",
    )
    digest = hashlib.sha256(receipt_file.read_bytes()).hexdigest()
    message = leaf_workbench_retry_message(
        enabled=True,
        project_dir=project,
        thesis_text=(
            f'LEAF_WORKBENCH_RECEIPT: {{"capability_id":"{capability_id}",'
            '"contract_sha256":"abc",'
            f'"input_hashes":{{"kernel_receipt_ref":"workspace/leaf_workbench_action_receipts/parent.json","kernel_receipt_sha256":"{digest}"}},'
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


def test_leaf_workbench_retry_joins_retained_receipt_to_candidate_identity(tmp_path: Path):
    project = tmp_path
    receipt_dir = project / "workspace" / "visible_cli_receipts"
    receipt_dir.mkdir(parents=True)
    candidate = "def step(grid, action, t):\n    return grid"
    candidate_sha = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
    receipt_ref = "workspace/visible_cli_receipts/score.json"
    (project / receipt_ref).write_text(
        json.dumps({
            "schema": "ztare-visible-workbench-cli-receipt-v1",
            "capability_id": "score_worldmodel_candidate_delta",
            "receipt": {
                "type": "LEAF_WORKBENCH_RECEIPT",
                "payload": {
                    "capability_id": "score_worldmodel_candidate_delta",
                    "input_hashes": {"source_sha256": candidate_sha},
                    "output_summary": "candidate_preflight_passed",
                    "claim_bindings": ["candidate delta"],
                },
            },
        }),
        encoding="utf-8",
    )
    thesis = json.dumps({
        "control_receipts": [{
            "type": "STRATEGY_CARD_DISCHARGE",
            "payload": {"visible_receipt_refs": [receipt_ref]},
        }],
        "thesis_markdown": "candidate preflight passed",
    })

    message = leaf_workbench_retry_message(
        enabled=True,
        project_dir=project,
        thesis_text=thesis,
        candidate_source=candidate,
        fact_markers=("candidate preflight",),
    )
    assert message is None

    stale = leaf_workbench_retry_message(
        enabled=True,
        project_dir=project,
        thesis_text=thesis,
        candidate_source=candidate + "\n# changed",
        fact_markers=("candidate preflight",),
    )
    assert stale is not None
    assert "candidate_identity_mismatch" in stale


def test_leaf_workbench_retry_accepts_verified_receipt_ref_without_reserialization(
    tmp_path: Path,
):
    project = tmp_path
    receipt_dir = project / "workspace" / "visible_cli_receipts"
    receipt_dir.mkdir(parents=True)
    receipt_ref = "workspace/visible_cli_receipts/score.json"
    candidate = (
        f"# EvidenceRef: {receipt_ref}\n"
        "def step(grid, action, t):\n    return grid"
    )
    candidate_sha = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
    (project / receipt_ref).write_text(
        json.dumps({
            "schema": "ztare-visible-workbench-cli-receipt-v1",
            "capability_id": "score_worldmodel_candidate_delta",
            "receipt": {
                "type": "LEAF_WORKBENCH_RECEIPT",
                "payload": {
                    "capability_id": "score_worldmodel_candidate_delta",
                    "input_hashes": {"source_sha256": candidate_sha},
                    "output_summary": "candidate_preflight_passed",
                    "claim_bindings": ["candidate delta"],
                },
            },
        }),
        encoding="utf-8",
    )

    message = leaf_workbench_retry_message(
        enabled=True,
        project_dir=project,
        thesis_text="candidate preflight passed",
        candidate_source=candidate,
        fact_markers=("candidate preflight",),
    )

    assert message is None


def test_candidate_bound_workbench_receipt_can_be_carried_for_control_only(
    tmp_path: Path,
):
    project = tmp_path
    receipt_dir = project / "workspace" / "leaf_workbench_action_receipts"
    receipt_dir.mkdir(parents=True)
    receipt_file = receipt_dir / "parent.json"
    receipt_file.write_text(
        json.dumps(
            {
                "schema": "ztare-leaf-workbench-kernel-receipt-v1",
                "capability_id": "run_strategy_required_gate",
                "request": {
                    "capability_id": "run_strategy_required_gate",
                    "input_refs": {"candidate_path": "test_model.py"},
                },
                "receipt": {"capability_id": "run_strategy_required_gate"},
            }
        ),
        encoding="utf-8",
    )
    digest = hashlib.sha256(receipt_file.read_bytes()).hexdigest()
    receipt = {
        "capability_id": "run_strategy_required_gate",
        "contract_sha256": "contract-sha",
        "input_hashes": {
            "kernel_receipt_ref": "workspace/leaf_workbench_action_receipts/parent.json",
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


def test_diagnostic_action_cannot_self_admit_an_operational_route(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from ztare.common import leaf_workbench_environment
    from ztare.common.leaf_workbench_executor import (
        leaf_workbench_action_request_retry_message,
    )
    from ztare.worldmodel.leaf_workbench import WORLD_MODEL_LEAF_WORKBENCH_CONTRACT

    (tmp_path / "workspace").mkdir()

    def handler(_project, _request, _row, _contract):
        return {
            "output_summary": json.dumps(
                {"observation_sha256": "diagnostic-observation"}
            ),
            "_route_production": {
                "schema_id": "ztare-counterexample-observation-triple-v1",
                "event": "materialized",
                "join_values": {
                    "observation_sha256": "diagnostic-observation"
                },
            },
        }

    monkeypatch.setattr(
        leaf_workbench_environment,
        "resolve_leaf_workbench_environment",
        lambda _adapter_id: {
            "contract": WORLD_MODEL_LEAF_WORKBENCH_CONTRACT,
            "records_fn": lambda _project: [],
            "action_handlers": {
                "inspect_worldmodel_counterexample_context": handler
            },
            "stateless_actions": {"inspect_worldmodel_counterexample_context"},
            "candidate_bound_actions": set(),
        },
    )
    request = {
        "capability_id": "inspect_worldmodel_counterexample_context",
        "input_refs": {},
        "claim_bindings": ["inspect without governed task authority"],
    }
    message = leaf_workbench_action_request_retry_message(
        enabled=True,
        project_dir=tmp_path,
        thesis_text="LEAF_WORKBENCH_ACTION_REQUEST: " + json.dumps(request),
    )

    assert message is not None and "LEAF_WORKBENCH_RECEIPT:" in message
    assert not (
        tmp_path / "workspace" / "counterexample_observation_routes.jsonl"
    ).exists()


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


def test_leaf_workbench_ignores_stale_exact_surface_when_active_candidate_has_residual(
    tmp_path: Path,
):
    import hashlib

    project = tmp_path / "project"
    workspace = project / "workspace"
    submissions = workspace / "submissions"
    submissions.mkdir(parents=True)
    source = "def step(grid, action, t):\n    return grid\n"
    candidate_path = submissions / "candidate.py"
    candidate_path.write_text(source, encoding="utf-8")
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    (project / "test_model.py").write_text(source, encoding="utf-8")
    (workspace / "candidate_memory.json").write_text(
        json.dumps(
            {
                "records": [
                    {
                        "sha": digest[:12],
                        "submission": "workspace/submissions/candidate.py",
                        "source_type": "deterministic_near_miss",
                        "visible_checked_rows": 10,
                        "visible_exact_rows": 9,
                        "visible_wrong_rows": 1,
                        "visible_wrong_cells": 4,
                        "holdout_depth": 3,
                        "counterexample_trace": {
                            "mismatch_classes": [
                                {
                                    "count": 1,
                                    "t": 71,
                                    "action": 0,
                                    "signature": {
                                        "bbox": [5, 9, 9, 38],
                                        "pair_counts": [
                                            {"predicted": 3, "real": 9, "count": 15}
                                        ],
                                    },
                                }
                            ]
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (workspace / "stale_surface_audit.json").write_text(
        json.dumps(
            {
                "schema": "ztare-worldmodel-stale-surface-audit-v1",
                "input_fingerprint": {"test_model.py": "superseded"},
                "current_replay": {
                    "checked_rows": 8,
                    "exact_rows": 8,
                    "wrong_cell_count": 0,
                },
            }
        ),
        encoding="utf-8",
    )

    from ztare.worldmodel.leaf_workbench import worldmodel_leaf_workbench_records

    residual = next(
        row
        for row in worldmodel_leaf_workbench_records(project)
        if row.get("capability_id") == "inspect_replay_residual_quotient"
    )
    assert "t=71" in residual["summary"]
    assert "current active replay exact" not in residual["summary"]
    assert residual["source_ref"] == "workspace/candidate_memory.json:active_evidence_view"


def test_leaf_workbench_task_follows_current_root_over_diagnostic_prior(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    workspace = project / "workspace"
    submissions = workspace / "submissions"
    submissions.mkdir(parents=True)
    prior_source = "def step(grid, action, t):\n    return grid\n"
    active_source = "def step(grid, action, t):\n    return [list(row) for row in grid]\n"
    prior = submissions / "prior.py"
    prior.write_text(prior_source, encoding="utf-8")
    (project / "test_model.py").write_text(active_source, encoding="utf-8")
    prior_sha = hashlib.sha256(prior_source.encode("utf-8")).hexdigest()
    active_sha = hashlib.sha256(active_source.encode("utf-8")).hexdigest()
    (workspace / "candidate_memory.json").write_text(
        json.dumps(
            {
                "records": [
                    {
                        "source_type": "deterministic_near_miss",
                        "submission": "workspace/submissions/prior.py",
                        "sha": prior_sha,
                        "visible_checked_rows": 10,
                        "visible_exact_rows": 9,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (workspace / "latest_harness_weakness.json").write_text(
        json.dumps(
            {
                "candidate_sha": active_sha,
                "active_frontier": {
                    "candidate_sha": active_sha,
                    "source_ref": "test_model.py",
                },
                "workbench_task": {
                    "schema": "ztare-leaf-workbench-task-v1",
                    "task_id": "active-task",
                    "failure_class": "counterexample_open",
                    "source_ref": "test_model.py",
                    "visible_artifact_refs": ["test_model.py"],
                    "admissible_capability_ids": [
                        "inspect_worldmodel_counterexample_context"
                    ],
                    "objective": "consume active counterexample",
                },
            }
        ),
        encoding="utf-8",
    )

    from ztare.worldmodel.leaf_workbench import worldmodel_leaf_workbench_records

    tasks = [
        row
        for row in worldmodel_leaf_workbench_records(project)
        if row.get("source_type") == "leaf_workbench_task"
    ]
    assert len(tasks) == 1
    assert tasks[0]["capability_id"] == "inspect_worldmodel_counterexample_context"


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


def test_active_workbench_task_rejects_sibling_evidence_action(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source = "def step(grid, action, t):\n    return grid\n"
    (tmp_path / "test_model.py").write_text(source, encoding="utf-8")
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    (workspace / "latest_harness_weakness.json").write_text(
        json.dumps(
            {
                "candidate_sha": digest,
                "active_frontier": {
                    "candidate_sha": digest,
                    "source_ref": "test_model.py",
                },
                "workbench_task": {
                    "schema": "ztare-leaf-workbench-task-v1",
                    "task_id": "required-context",
                    "source_ref": "test_model.py",
                    "admissible_capability_ids": [
                        "inspect_worldmodel_counterexample_context"
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    request = {
        "capability_id": "run_visible_json_probe",
        "input_refs": {"artifact_refs": ["workspace/latest_harness_weakness.json"]},
        "claim_bindings": ["substitute generic probe"],
    }

    message = leaf_workbench_action_request_retry_message(
        enabled=True,
        project_dir=tmp_path,
        thesis_text="LEAF_WORKBENCH_ACTION_REQUEST: " + json.dumps(request),
    )

    assert message is not None
    assert "active workbench task required-context" in message
    assert "inspect_worldmodel_counterexample_context" in message
    assert "outside that task scope" in message
    assert "LEAF_WORKBENCH_RECEIPT:" not in message


def test_active_workbench_task_requires_evidence_receipt_before_candidate(
    tmp_path: Path,
) -> None:
    from ztare.common.leaf_workbench_executor import required_active_task_action_error
    from ztare.validator.core.repair_preflight import leaf_workbench_retry_message

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source = "def step(grid, action, t):\n    return grid\n"
    (tmp_path / "test_model.py").write_text(source, encoding="utf-8")
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    (workspace / "latest_harness_weakness.json").write_text(
        json.dumps(
            {
                "active_frontier": {
                    "candidate_sha": digest,
                    "source_ref": "test_model.py",
                },
                "workbench_task": {
                    "schema": "ztare-leaf-workbench-task-v1",
                    "task_id": "consume-context-first",
                    "source_ref": "test_model.py",
                    "admissible_capability_ids": [
                        "inspect_worldmodel_counterexample_context"
                    ],
                    "objective": "observe the counterexample identity",
                },
            }
        ),
        encoding="utf-8",
    )

    message = leaf_workbench_retry_message(
        enabled=True,
        thesis_text="candidate without evidence action",
        candidate_source=source,
        fact_markers=("inspect_worldmodel_",),
        project_dir=tmp_path,
    )

    assert message is not None
    assert "active evidence task consume-context-first" in message
    assert "inspect_worldmodel_counterexample_context" in message
    assert "before candidate evaluation" in message
    assert "LEAF_WORKBENCH_ACTION_REQUEST" in message

    consequence = {
        "control_receipts": [
            {
                "type": "LEAF_WORKBENCH_RECEIPT",
                "payload": {
                    "capability_id": "score_worldmodel_candidate_delta",
                    "output_summary": json.dumps(
                        {
                            "status": "candidate_preflight_passed",
                            "candidate_evaluation_admissible": True,
                        }
                    ),
                },
            }
        ]
    }
    message = required_active_task_action_error(
        project_dir=tmp_path,
        thesis_text=json.dumps(consequence),
        candidate_source=source,
    )
    assert message is not None
    assert "requires a kernel receipt" in message
    assert "inspect_worldmodel_counterexample_context" in message


def test_active_workbench_task_first_fires_once_and_changes_leaf_state(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from ztare.common import leaf_workbench_environment
    from ztare.common.leaf_workbench_executor import (
        active_workbench_task_first_fire_receipt,
        leaf_workbench_receipt_preflight_message,
        required_active_task_action_error,
    )
    from ztare.worldmodel.leaf_workbench import (
        WORLD_MODEL_LEAF_WORKBENCH_CONTRACT,
        render_worldmodel_leaf_workbench_fragment,
        worldmodel_leaf_workbench_records,
    )
    from ztare.common.briefing_pack import BriefingPackRequest, build_briefing_pack

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source = "def step(grid, action, t):\n    return grid\n"
    (tmp_path / "test_model.py").write_text(source, encoding="utf-8")
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    task = {
        "schema": "ztare-leaf-workbench-task-v1",
        "task_id": "first-fire-task",
        "source_ref": "test_model.py",
        "failure_class": "missing_relation_identity",
        "admissible_capability_ids": [
            "inspect_worldmodel_counterexample_context",
            "mine_worldmodel_lowerable_selectors",
        ],
        "morphism_sequence": [
            "inspect_worldmodel_counterexample_context",
            "mine_worldmodel_lowerable_selectors",
        ],
        "objective": "consume the selected observation before proposing",
    }
    (workspace / "latest_harness_weakness.json").write_text(
        json.dumps(
            {
                "active_frontier": {
                    "candidate_sha": digest,
                    "source_ref": "test_model.py",
                },
                "workbench_task": task,
            }
        ),
        encoding="utf-8",
    )
    calls = 0

    def handler(_project, _request, _row, _contract):
        nonlocal calls
        calls += 1
        return {
            "output_summary": json.dumps(
                {
                    "observation_sha256": "observation-identity",
                    "catalog_residual_event_candidates": [
                        {
                            "schema": "ztare-catalog-residual-event-candidate-v1",
                            "authority": "diagnostic_candidate_only",
                            "operation_identity": {
                                "op": "region_event",
                                "trigger_role": "moves_under_actions",
                                "edge": "enter",
                                "consequence_relation": "remote_write",
                            },
                            "operation_identity_sha256": "operation-identity",
                            "role_evidence": {
                                "support_count": 3,
                                "interventions": [1, 2],
                                "displacements": [[0, 1], [1, 0]],
                            },
                            "lowering": {
                                "op": "region_event",
                                "mover_colors": [4, 6],
                                "rect": [1, 2, 3, 4],
                                "edge": "enter",
                                "writes": [[9, [[7, 8], [7, 9]]]],
                            },
                            "promotion_authorized": False,
                        }
                    ],
                }
            ),
            "_route_production": {
                "schema_id": "ztare-counterexample-observation-triple-v1",
                "event": "materialized",
                "join_values": {
                    "observation_sha256": "observation-identity"
                },
                "payload": {"observation_ref": "evidence:row"},
            },
        }

    environment = {
        "contract": WORLD_MODEL_LEAF_WORKBENCH_CONTRACT,
        "records_fn": lambda _project: [],
        "action_handlers": {
            "inspect_worldmodel_counterexample_context": handler
        },
        "stateless_actions": {"inspect_worldmodel_counterexample_context"},
        "candidate_bound_actions": set(),
    }
    monkeypatch.setattr(
        leaf_workbench_environment,
        "resolve_leaf_workbench_environment",
        lambda _adapter_id: environment,
    )

    first = active_workbench_task_first_fire_receipt(
        tmp_path,
        materialize=True,
    )
    second = active_workbench_task_first_fire_receipt(
        tmp_path,
        materialize=True,
    )
    # A later receipt from another admissible operation is still a distinct
    # task transition.  Set membership must not replace the selected first
    # morphism's identity in the first-fire cache.
    later_artifact = {
        "capability_id": "mine_worldmodel_lowerable_selectors",
        "request": {"input_refs": {"task_id": "first-fire-task"}},
        "receipt": {
            "capability_id": "mine_worldmodel_lowerable_selectors",
            "input_hashes": {},
            "output_summary": json.dumps({"status": "later_task_operation"}),
        },
    }
    later_path = (
        workspace / "leaf_workbench_action_receipts" / ("f" * 64 + ".json")
    )
    later_path.write_text(json.dumps(later_artifact), encoding="utf-8")
    third = active_workbench_task_first_fire_receipt(
        tmp_path,
        materialize=True,
    )

    assert first is not None and second is not None and third is not None
    assert calls == 1
    assert first["capability_id"] == "inspect_worldmodel_counterexample_context"
    assert third["capability_id"] == "inspect_worldmodel_counterexample_context"
    assert first["input_hashes"]["task_id"] == "first-fire-task"
    assert len(first["input_hashes"]["handler_implementation_sha256"]) == 64
    assert first["input_hashes"]["kernel_receipt_ref"].startswith(
        "workspace/leaf_workbench_action_receipts/"
    )
    route_rows = [
        json.loads(line)
        for line in (workspace / "counterexample_observation_routes.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    assert route_rows == [
        {
            "event": "materialized",
            "observation_sha256": "observation-identity",
            "payload": {
                "capability_id": "inspect_worldmodel_counterexample_context",
                "kernel_receipt_ref": first["input_hashes"]["kernel_receipt_ref"],
                "kernel_receipt_sha256": first["input_hashes"][
                    "kernel_receipt_sha256"
                ],
                "observation_ref": "evidence:row",
            },
            "route_id": "counterexample_observation_to_domain_refinement.v1",
            "schema": "ztare-counterexample-observation-triple-v1",
            "task_id": "first-fire-task",
        }
    ]
    cited_receipt = {
        "control_receipts": [
            {
                "type": "LEAF_WORKBENCH_RECEIPT",
                "payload": {
                    "capability_id": first["capability_id"],
                    "output_ref": first["input_hashes"]["kernel_receipt_ref"],
                    "output_sha256": first["input_hashes"][
                        "kernel_receipt_sha256"
                    ],
                    "output_summary": first["output_summary"],
                    "claim_bindings": ["consume selected observation"],
                },
            }
        ]
    }
    assert (
        leaf_workbench_receipt_preflight_message(
            project_dir=tmp_path,
            thesis_text=json.dumps(cited_receipt),
            candidate_source=source,
        )
        is None
    )
    assert (
        required_active_task_action_error(
            project_dir=tmp_path,
            thesis_text="candidate proposed after parent first-fire",
            candidate_source=source,
        )
        is None
    )
    fragment = render_worldmodel_leaf_workbench_fragment(tmp_path)
    assert len(fragment) <= 2200
    assert "parent first-fire receipt" in fragment
    assert "source_ref=test_model.py" in fragment
    assert "full artifact remains" not in fragment

    records = worldmodel_leaf_workbench_records(tmp_path)
    receipt_record = next(
        row
        for row in records
        if row.get("source_type") == "leaf_workbench_kernel_receipt"
    )
    projection = receipt_record["consumer_projection"]
    assert projection["task_id"] == "first-fire-task"
    assert projection["operation_identity"]["op"] == "region_event"
    assert projection["role_evidence"]["support_count"] == 3
    assert projection["lowering"]["writes"] == [
        {"value": 9, "row_col_runs": [[7, 8, 9]]}
    ]

    (workspace / "mutator_briefing_iter_001_records.json").write_text(
        json.dumps(
            {
                "records": [
                    {"provider": "leaf_workbench", **row} for row in records
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv(
        "ZTARE_AGENT_VISIBLE_WORKBENCH_ROOT", str(tmp_path / "visible_packs")
    )
    pack = build_briefing_pack(
        BriefingPackRequest(
            repo=tmp_path,
            agent_id="first-fire-test",
            task="propose the next candidate",
            context="",
        )
    )
    attention = (pack.workbench / "ATTENTION.md").read_text(encoding="utf-8")
    assert attention.find("consumer_projection=") < attention.find(
        "active_task=first-fire-task"
    )
    assert '"op": "region_event"' in attention
    assert '"trigger_role": "moves_under_actions"' in attention
    assert '"rect": [1, 2, 3, 4]' in attention
    assert '"row_col_runs": [[7, 8, 9]]' in attention
    manifest = json.loads(
        (pack.workbench / "MANIFEST.json").read_text(encoding="utf-8")
    )
    receipt_ref = first["input_hashes"]["kernel_receipt_ref"]
    visible = {row["ref"]: row for row in manifest["visible_artifacts"]}
    assert visible[receipt_ref]["status"] == "materialized"

    # Metamorphic lifecycle check: if a compiler bounce advances the repair
    # frontier, the new task identity must first-fire through the parent door
    # before the pre-receipt candidate can be evaluated.  A repeated preflight
    # then observes the persisted receipt instead of firing twice.
    next_task = {**task, "task_id": "second-fire-task"}
    (workspace / "latest_harness_weakness.json").write_text(
        json.dumps(
            {
                "active_frontier": {
                    "candidate_sha": digest,
                    "source_ref": "test_model.py",
                },
                "workbench_task": next_task,
            }
        ),
        encoding="utf-8",
    )
    transition_message = required_active_task_action_error(
        project_dir=tmp_path,
        thesis_text="candidate proposed before the successor task first-fire",
        candidate_source=source,
    )
    assert transition_message is not None
    assert "second-fire-task" in transition_message
    assert "parent kernel first-fired" in transition_message
    assert "LEAF_WORKBENCH_RECEIPT:" in transition_message
    assert calls == 2
    assert (
        required_active_task_action_error(
            project_dir=tmp_path,
            thesis_text=transition_message,
            candidate_source=source,
        )
        is None
    )
    assert calls == 2


def test_active_workbench_receipt_family_threads_upstream_identity_and_replays_stale_handler(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from ztare.common import leaf_workbench_environment
    from ztare.common.leaf_workbench_executor import (
        active_workbench_task_receipt_family,
    )
    from ztare.worldmodel.leaf_workbench import WORLD_MODEL_LEAF_WORKBENCH_CONTRACT

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    evidence_path = tmp_path / "raw" / "evidence.json"
    evidence_path.parent.mkdir()
    evidence_path.write_text('{"version":1}\n', encoding="utf-8")
    source = "def step(grid, action, t):\n    return grid\n"
    (tmp_path / "test_model.py").write_text(source, encoding="utf-8")
    source_sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
    task_id = "receipt-family-task"
    (workspace / "latest_harness_weakness.json").write_text(
        json.dumps(
            {
                "active_frontier": {
                    "candidate_sha": source_sha,
                    "source_ref": "test_model.py",
                },
                "workbench_task": {
                    "task_id": task_id,
                    "source_ref": "test_model.py",
                    "source_sha256": source_sha,
                    "admissible_capability_ids": [
                        "inspect_worldmodel_counterexample_context",
                        "mine_worldmodel_lowerable_selectors",
                    ],
                    "morphism_sequence": [
                        "inspect_worldmodel_counterexample_context",
                        "mine_worldmodel_lowerable_selectors",
                    ],
                    "objective": "compose a task-bound receipt family",
                },
            }
        ),
        encoding="utf-8",
    )
    calls: list[str] = []

    def inspect_handler(_project, _request, _row, _contract):
        calls.append("inspect")
        return {
            "input_hashes": {
                "evidence_ref": "raw/evidence.json",
                "evidence_sha256": hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
            },
            # An intermediate conjecture may already be syntactically
            # lowerable.  The task program still owns its downstream selector
            # transition; this property cannot terminate the receipt family.
            "output_summary": json.dumps({
                "schema": "inspection-v1",
                "candidate_delta_admissible": True,
            }),
        }

    def selector_handler(_project, request, _row, _contract):
        calls.append("selector")
        refs = request["input_refs"].get("upstream_receipt_refs") or []
        return {
            "input_hashes": {"upstream_receipt_refs": list(refs)},
            "output_summary": json.dumps({"schema": "selector-v1"}),
        }

    environment = {
        "contract": WORLD_MODEL_LEAF_WORKBENCH_CONTRACT,
        "records_fn": lambda _project: [],
        "action_handlers": {
            "inspect_worldmodel_counterexample_context": inspect_handler,
            "mine_worldmodel_lowerable_selectors": selector_handler,
        },
        "stateless_actions": {
            "inspect_worldmodel_counterexample_context",
            "mine_worldmodel_lowerable_selectors",
        },
        "candidate_bound_actions": set(),
    }
    monkeypatch.setattr(
        leaf_workbench_environment,
        "resolve_leaf_workbench_environment",
        lambda _adapter_id: environment,
    )

    family = active_workbench_task_receipt_family(tmp_path, materialize=True)
    assert calls == ["inspect", "selector"]
    first_ref = family["inspect_worldmodel_counterexample_context"][
        "input_hashes"
    ]["kernel_receipt_ref"]
    assert family["mine_worldmodel_lowerable_selectors"]["input_hashes"][
        "upstream_receipt_refs"
    ] == [first_ref]

    calls.clear()
    assert len(active_workbench_task_receipt_family(tmp_path, materialize=True)) == 2
    assert calls == []

    evidence_path.write_text('{"version":2}\n', encoding="utf-8")
    family = active_workbench_task_receipt_family(tmp_path, materialize=True)
    assert calls == ["inspect", "selector"]
    first_ref = family["inspect_worldmodel_counterexample_context"][
        "input_hashes"
    ]["kernel_receipt_ref"]
    calls.clear()

    first_path = tmp_path / first_ref
    artifact = json.loads(first_path.read_text(encoding="utf-8"))
    artifact["receipt"]["input_hashes"]["handler_implementation_sha256"] = (
        "stale-implementation"
    )
    first_path.write_text(json.dumps(artifact), encoding="utf-8")

    active_workbench_task_receipt_family(tmp_path, materialize=True)
    assert calls == ["inspect", "selector"]


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
                    "schema": "ztare-worldmodel-lowerable-selector-miner-v1",
                    "admissibility_scope": "candidate_family",
                    "candidate_family_id": "same-shaped-window-selector-v1",
                    "candidate_family_admissible": False,
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


def test_counterexample_context_accepts_gate_trace_without_prior_comparison(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    workspace = project / "workspace"
    submissions = workspace / "submissions"
    episodes = project / "raw" / "episodes"
    submissions.mkdir(parents=True)
    episodes.mkdir(parents=True)
    source = "def step(grid, action, t):\n    return [list(row) for row in grid]\n"
    candidate = submissions / "candidate.py"
    candidate.write_text(source, encoding="utf-8")
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    (episodes / "episode_001.jsonl").write_text(
        json.dumps(
            {
                "t": 4,
                "a": 1,
                "s": [[0, 0], [0, 0]],
                "s_next": [[0, 0], [7, 7]],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (project / "latest_eval_results.json").write_text(
        json.dumps(
            {
                "counterexample_trace": {
                    "gated_file": str(candidate),
                    "gated_sha256": digest,
                    "failed_gates": ["visible_replay_exact"],
                    "evidence_ref": "raw/episodes/episode_001.jsonl",
                    "exact_rows": 0,
                    "wrong_cell_count": 2,
                    "first_mismatch": "typed witness",
                    "mismatch_classes": [
                        {
                            "first_row": 0,
                            "t": 4,
                            "action": 1,
                            "count": 1,
                            "signature": {
                                "bbox": [1, 0, 1, 1],
                                "pair_counts": [
                                    {"predicted": 0, "real": 7, "count": 2}
                                ],
                            },
                        }
                    ],
                }
            }
        ),
        encoding="utf-8",
    )

    from ztare.worldmodel.leaf_workbench import (
        _regression_ref_from_input_refs,
        render_worldmodel_leaf_workbench_fragment,
        run_worldmodel_counterexample_context_probe,
        worldmodel_leaf_workbench_records,
    )

    payload = json.loads(run_worldmodel_counterexample_context_probe(project))
    explicit_payload = json.loads(
        run_worldmodel_counterexample_context_probe(
            project,
            regression_ref="latest_eval_results.json",
        )
    )
    alias = submissions / "same_carrier_other_ref.py"
    alias.write_text(source, encoding="utf-8")
    episode_alias = episodes / "episode_alias.jsonl"
    episode_alias.write_bytes((episodes / "episode_001.jsonl").read_bytes())
    alias_regression = json.loads(
        (project / "latest_eval_results.json").read_text(encoding="utf-8")
    )
    alias_regression["counterexample_trace"]["gated_file"] = str(alias)
    alias_regression["counterexample_trace"]["evidence_ref"] = (
        "raw/episodes/episode_alias.jsonl"
    )
    alias_ref = workspace / "same_observation_other_carrier_ref.json"
    alias_ref.write_text(json.dumps(alias_regression), encoding="utf-8")
    alias_payload = json.loads(
        run_worldmodel_counterexample_context_probe(
            project,
            regression_ref="workspace/same_observation_other_carrier_ref.json",
        )
    )
    observation = payload["counterexample_observation"]
    assert payload["schema"] == "ztare-counterexample-context-observation-v1"
    assert payload["observation_sha256"]
    assert observation["observation_ref"].endswith("#transition:0")
    assert observation["proposal_identity"] == {"carrier_sha": digest}
    assert observation["proposal_provenance"]["carrier_ref"].endswith(
        "candidate.py"
    )
    assert observation["objects"]["proposed_consequence"] != observation["objects"]["observed_consequence"]
    assert explicit_payload["observation_sha256"] == payload["observation_sha256"]
    assert alias_payload["observation_sha256"] == payload["observation_sha256"]
    alias_observation = alias_payload["counterexample_observation"]
    assert alias_observation["proposal_identity"] == {"carrier_sha": digest}
    assert (
        alias_observation["evidence_epoch"]["evidence_ref"]
        != observation["evidence_epoch"]["evidence_ref"]
    )
    assert alias_observation["observation_ref"] != observation["observation_ref"]
    assert (
        alias_observation["proposal_provenance"]["carrier_ref"]
        != observation["proposal_provenance"]["carrier_ref"]
    )
    assert _regression_ref_from_input_refs(project, {}) == "latest_eval_results.json"

    # A leaf-local score can be newer while retaining the prior as repair
    # frontier and omitting that prior's observable row.  It is an evaluation
    # receipt, not a usable observation identity; resolution must fall back to
    # the current gate-issued counterexample rather than following "latest".
    visible_receipts = workspace / "visible_cli_receipts"
    visible_receipts.mkdir()
    score_ref = "workspace/visible_cli_receipts/score.json"
    (project / score_ref).write_text(
        json.dumps(
            {
                "output_summary": json.dumps(
                    {
                        "candidate_regression_receipt": {
                            "candidate_relation": "no_strict_improvement",
                            "best_prior_submission": str(candidate.relative_to(project)),
                            "best_prior_sha": digest,
                            "candidate_submission": "ephemeral.py",
                            "candidate_sha": "f" * 64,
                            "quotient_comparison": {
                                "relation": "same_quotient_worse_frequency",
                                "best_prior_top_quotient": {
                                    "first_row": None,
                                    "bbox": [1, 0, 1, 1],
                                },
                                "candidate_top_quotient": {
                                    "first_row": 0,
                                    "bbox": [1, 0, 1, 1],
                                },
                            },
                        }
                    }
                )
            }
        ),
        encoding="utf-8",
    )
    assert _regression_ref_from_input_refs(
        project, {"score_receipt_ref": score_ref}
    ) == "latest_eval_results.json"


def test_counterexample_localization_preserves_cause_and_residual_support() -> None:
    from ztare.worldmodel.leaf_workbench import _triple_component_windows
    from ztare.worldmodel.retry_surface import _compact_counterexample_observation

    source = ((7, 0, 0), (0, 0, 0), (0, 0, 0))
    proposed = ((0, 7, 0), (0, 0, 0), (0, 0, 1))
    observed = ((0, 7, 0), (0, 0, 0), (0, 0, 2))

    windows = _triple_component_windows(
        source,
        proposed,
        observed,
        margin=0,
    )

    assert windows == [[0, 0, 0, 1], [2, 2, 2, 2]]

    packet = {
        "schema": "ztare-counterexample-observation-triple-v1",
        "objects": {
            "source_observation": {
                "windows": [
                    {"bbox": [0, 0, 2, 2], "values": [list(row) for row in source]},
                    {"bbox": [0, 0, 0, 1], "values": [[7, 0]]},
                ]
            },
            "proposed_consequence": {
                "windows": [
                    {"bbox": [0, 0, 2, 2], "values": [list(row) for row in proposed]},
                    {"bbox": [0, 0, 0, 1], "values": [[0, 7]]},
                ]
            },
            "observed_consequence": {
                "windows": [
                    {"bbox": [0, 0, 2, 2], "values": [list(row) for row in observed]},
                    {"bbox": [0, 0, 0, 1], "values": [[0, 7]]},
                ]
            },
        },
    }
    compact = _compact_counterexample_observation(packet)
    assert compact["residual_cell_count"] == 1
    assert compact["state_change_cell_count"] == 3
    assert compact.get("chart_overlap_conflict_count", 0) == 0
    assert compact["state_change_runs"][0] == {
        "row": 0,
        "col_start": 0,
        "col_end": 0,
        "source": 7,
        "observed": 0,
    }


def test_residual_event_identity_survives_translation_and_palette_change() -> None:
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.leaf_workbench import (
        _catalog_residual_event_candidates,
    )

    def witnessed_case(
        *, row_offset: int, col_offset: int, palette: tuple[int, int]
    ) -> dict:
        height = width = 14
        background = 0

        def state_at(left: int) -> list[list[int]]:
            grid = [[background for _ in range(width)] for _ in range(height)]
            top = 2 + row_offset
            grid[top][left : left + 2] = [palette[0], palette[0]]
            grid[top + 1][left : left + 2] = [palette[1], palette[1]]
            return grid

        positions = [1 + col_offset, 3 + col_offset, 5 + col_offset]
        log = EpisodeLog()
        for t, (left, right) in enumerate(zip(positions, positions[1:])):
            log.append(state_at(left), 3, state_at(right), t=t)

        source = state_at(positions[-1])
        destination = positions[-1] + 2
        source[2 + row_offset][destination : destination + 2] = [7, 7]
        proposed = state_at(destination)
        observed = [row[:] for row in proposed]
        observed[11 - row_offset][1 + col_offset : 4 + col_offset] = [9, 9, 9]
        log.append(source, 3, observed, t=2)
        transitions = list(log)
        candidates = _catalog_residual_event_candidates(
            list(enumerate(transitions[:-1])),
            transitions[-1],
            proposed,
            observed,
        )
        assert len(candidates) == 1
        return candidates[0]

    first = witnessed_case(row_offset=0, col_offset=0, palette=(1, 2))
    transformed = witnessed_case(row_offset=1, col_offset=1, palette=(6, 8))

    assert first["operation_identity"] == transformed["operation_identity"] == {
        "relation": "boundary_conditioned_consequence",
        "subject_role": "moves_under_actions",
        "boundary": "arrival",
        "consequence_role": "remote_effect",
    }
    assert first["operation_identity_sha256"] == transformed[
        "operation_identity_sha256"
    ]
    assert first["role_evidence"]["support_count"] == 2
    assert transformed["role_evidence"]["support_count"] == 2
    assert first["identity_status"] == "operation_recurrence_required"
    assert transformed["identity_status"] == "operation_recurrence_required"
    assert first["lowering"]["mover_colors"] != transformed["lowering"][
        "mover_colors"
    ]
    assert first["lowering"]["rect"] != transformed["lowering"]["rect"]
    assert first["promotion_authorized"] is False


def test_residual_extractor_consumes_accepted_mover_role() -> None:
    from types import SimpleNamespace

    from ztare.worldmodel.leaf_workbench import (
        _catalog_residual_event_candidates,
    )

    source = [[0] * 12 for _ in range(12)]
    proposed = [[0] * 12 for _ in range(12)]
    observed = [[0] * 12 for _ in range(12)]
    source[2][1:3] = [1, 1]
    source[3][1:3] = [2, 2]
    source[2][3] = 1
    source[3][3] = 2
    for grid in (proposed, observed):
        grid[2][3:5] = [1, 1]
        grid[3][3:5] = [2, 2]
    observed[9][1:4] = [7, 7, 7]
    transition = SimpleNamespace(
        s=tuple(tuple(row) for row in source),
        s_next=tuple(tuple(row) for row in observed),
        a=3,
        t=0,
        identity=None,
    )

    candidates = _catalog_residual_event_candidates(
        [],
        transition,
        tuple(tuple(row) for row in proposed),
        transition.s_next,
        mover_palettes=[(1, 2)],
        mover_patterns=[{"shape": [2, 2], "values": [1, 1, 2, 2]}],
    )

    assert len(candidates) == 1
    assert candidates[0]["identity_status"] == "operation_recurrence_required"
    assert candidates[0]["operation_identity"]["subject_role"] == (
        "moves_under_actions"
    )


def test_vacated_component_boundary_requires_and_uses_intervention_recurrence() -> None:
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.leaf_workbench import (
        _catalog_residual_event_candidates,
    )

    def witnessed_case(
        *, row_offset: int, col_offset: int, palette: tuple[int, int], action: int
    ) -> dict:
        height = width = 16
        background = 0
        top, left = 6 + row_offset, 6 + col_offset

        def state_at(row: int, col: int) -> list[list[int]]:
            grid = [[background for _ in range(width)] for _ in range(height)]
            grid[row][col : col + 2] = [palette[0], palette[0]]
            grid[row + 1][col : col + 2] = [palette[1], palette[1]]
            return grid

        def reveal(grid: list[list[int]]) -> None:
            grid[top][left : left + 2] = [11, 12]
            grid[top + 1][left : left + 2] = [13, 14]

        log = EpisodeLog()
        # Role support is independent of the boundary witness.
        log.append(state_at(1, 1), 3, state_at(1, 3), t=0)
        log.append(state_at(2, 1), 3, state_at(2, 3), t=1)

        source = state_at(top, left)
        prior_observed = state_at(top + 2, left)
        reveal(prior_observed)
        log.append(source, 1, prior_observed, t=2)

        proposed = state_at(top, left - 2)
        observed = [row[:] for row in proposed]
        reveal(observed)
        log.append(source, action, observed, t=3)
        transitions = list(log)
        candidates = _catalog_residual_event_candidates(
            list(enumerate(transitions[:-1])),
            transitions[-1],
            proposed,
            observed,
        )
        assert len(candidates) == 1
        return candidates[0]

    first = witnessed_case(
        row_offset=0,
        col_offset=0,
        palette=(1, 2),
        action=2,
    )
    transformed = witnessed_case(
        row_offset=1,
        col_offset=2,
        palette=(6, 8),
        action=0,
    )

    expected_identity = {
        "relation": "covered_uncovered",
        "subject_role": "moves_under_actions",
        "boundary": "departure",
        "consequence_role": "revealed_substrate",
    }
    assert first["operation_identity"] == transformed["operation_identity"] == expected_identity
    assert first["operation_identity_sha256"] == transformed[
        "operation_identity_sha256"
    ]
    assert first["identity_status"] == "catalog_operation_reuse_candidate"
    assert transformed["identity_status"] == "catalog_operation_reuse_candidate"
    assert first["boundary_evidence"]["support_count"] == 2
    assert first["boundary_evidence"]["distinct_interventions"] == 2
    assert first["lowering"]["edge"] == "exit"
    assert first["lowering"]["rect"] != transformed["lowering"]["rect"]
    assert first["lowering"]["mover_colors"] != transformed["lowering"][
        "mover_colors"
    ]
    assert "action" not in first["lowering"]


def test_operation_recurrence_obligation_rechecks_the_growing_bank(
    tmp_path: Path,
) -> None:
    from ztare.worldmodel.leaf_workbench import (
        _mine_task_operation_domain_selector,
        _stable_json_sha256,
    )

    project = tmp_path
    workspace = project / "workspace"
    episodes = project / "raw" / "episodes"
    workspace.mkdir()
    episodes.mkdir(parents=True)
    source = workspace / "frontier.py"
    source.write_text(
        "def step(state, action, t):\n"
        "    out = [list(row) for row in state]\n"
        "    out[2][0] = 0\n"
        "    out[3][0] = 0\n"
        "    out[2][2] = 1\n"
        "    out[3][2] = 2\n"
        "    return tuple(tuple(row) for row in out)\n",
        encoding="utf-8",
    )
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    task_id = "task-singleton-operation"
    (workspace / "latest_harness_weakness.json").write_text(
        json.dumps(
            {
                "workbench_task": {
                    "task_id": task_id,
                    "source_ref": "workspace/frontier.py",
                    "source_sha256": source_sha,
                }
            }
        ),
        encoding="utf-8",
    )
    operation_identity = {
        "relation": "boundary_conditioned_consequence",
        "subject_role": "moves_under_actions",
        "boundary": "arrival",
        "consequence_role": "remote_effect",
    }
    operation_sha = _stable_json_sha256(operation_identity)
    lowering = {
        "op": "region_event",
        "mover_colors": [1, 2],
        "rect": [2, 2, 3, 3],
        "edge": "enter",
        "writes": [[9, [[0, 0]]]],
    }
    identity = {
        "schema": "ztare-transition-identity-v1",
        "kind": "dynamics",
        "authority": "environment_adapter",
        "source_epoch": 4,
        "target_epoch": 4,
        "object_correspondence": [],
        "evidence_refs": ["metamorphic-fixture"],
    }

    def transition(marker: int) -> dict:
        state = [[0 for _ in range(5)] for _ in range(5)]
        state[2][0] = 1
        state[3][0] = 2
        state[4][4] = marker
        successor = [row[:] for row in state]
        successor[2][0] = 0
        successor[3][0] = 0
        successor[2][2] = 1
        successor[3][2] = 2
        successor[0][0] = 9
        return {"t": 7, "a": 2, "s": state, "s_next": successor, "identity": identity}

    episode_path = episodes / "episode_001.jsonl"
    context = {
        "task_id": task_id,
        "ref": "workspace/inspect.json",
        "sha256": "a" * 64,
        "summary": {
            "observation_sha256": "b" * 64,
            "counterexample_observation": {
                "observation_ref": "raw/episodes/episode_001.jsonl#transition:0",
                "transition_identity": {
                    "authority": "environment_adapter",
                    "kind": "unclassified",
                    "source_epoch": 4,
                    "target_epoch": 4,
                },
            },
            "catalog_residual_event_candidates": [
                {
                    "identity_status": "operation_recurrence_required",
                    "operation_identity": operation_identity,
                    "operation_identity_sha256": operation_sha,
                    "lowering_kind": "region_event",
                    "lowering": lowering,
                    "boundary_evidence": {},
                }
            ],
        },
    }
    episode_path.write_text(json.dumps(transition(3)) + "\n", encoding="utf-8")
    result = _mine_task_operation_domain_selector(
        project,
        context=context,
        episode_ref="raw/episodes/episode_001.jsonl",
        max_margin=2,
    )

    assert result is not None
    assert result["lowerability_status"] == "operation_domain_requires_recurrence"
    assert result["candidate_family_admissible"] is False
    assert result["identity_support"]["authority_granted"] is False
    assert result["acquisition_obligation"]["source_observation_ref"].endswith(
        "#transition:0"
    )
    assert result["acquisition_obligation"]["current_law_owned_observations"] == 1

    # Replaying the same packet creates another row locator, not another
    # observation identity, and therefore cannot discharge recurrence.
    episode_path.write_text(
        json.dumps(transition(3)) + "\n" + json.dumps(transition(3)) + "\n",
        encoding="utf-8",
    )
    replayed = _mine_task_operation_domain_selector(
        project,
        context=context,
        episode_ref="raw/episodes/episode_001.jsonl",
        max_margin=2,
    )
    assert replayed is not None
    assert replayed["lowerability_status"] == "operation_domain_requires_recurrence"
    assert replayed["identity_support"]["distinct_positive_observations"] == 1
    assert replayed["domain_evidence"]["operation_domain_support_count"] == 2
    assert replayed["domain_evidence"]["distinct_operation_domain_observations"] == 1

    episode_path.write_text(
        json.dumps(transition(3)) + "\n" + json.dumps(transition(4)) + "\n",
        encoding="utf-8",
    )
    recurrent = _mine_task_operation_domain_selector(
        project,
        context=context,
        episode_ref="raw/episodes/episode_001.jsonl",
        max_margin=2,
    )
    assert recurrent is not None
    assert recurrent["lowerability_status"] == "operation_domain_selector_found"
    assert recurrent["identity_support"]["distinct_positive_observations"] == 2
    assert recurrent["candidate_family_admissible"] is True
    assert "acquisition_obligation" not in recurrent


def test_operation_domain_selector_is_task_bound_and_action_label_equivariant(
    tmp_path: Path,
) -> None:
    from ztare.worldmodel.leaf_workbench import (
        _mine_task_operation_domain_selector,
        _stable_json_sha256,
    )

    operation_identity = {
        "relation": "covered_uncovered",
        "subject_role": "moves_under_actions",
        "boundary": "departure",
        "consequence_role": "revealed_substrate",
    }
    operation_sha = _stable_json_sha256(operation_identity)

    def run_case(project: Path, actions: tuple[int, int, int]) -> dict:
        workspace = project / "workspace"
        episodes = project / "raw" / "episodes"
        workspace.mkdir(parents=True)
        episodes.mkdir(parents=True)
        source = (
            "def step(state, action, t):\n"
            "    out = [list(row) for row in state]\n"
            "    for row in range(2, 4):\n"
            "        for col in range(2, 4):\n"
            "            out[row][col] = 0\n"
            "    return tuple(tuple(row) for row in out)\n"
        )
        source_path = workspace / "base.py"
        source_path.write_text(source, encoding="utf-8")
        source_sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
        task_id = f"task-{project.name}"
        (workspace / "latest_harness_weakness.json").write_text(
            json.dumps(
                {
                    "workbench_task": {
                        "task_id": task_id,
                        "source_ref": "workspace/base.py",
                        "source_sha256": source_sha,
                    }
                }
            ),
            encoding="utf-8",
        )

        def state(marker: int) -> list[list[int]]:
            grid = [[0 for _ in range(7)] for _ in range(7)]
            grid[1][1] = marker
            grid[2][2:4] = [1, 1]
            grid[3][2:4] = [2, 2]
            return grid

        def consequence(marker: int, *, reveal: bool) -> list[list[int]]:
            grid = state(marker)
            grid[2][2:4] = [0, 0]
            grid[3][2:4] = [0, 0]
            if reveal:
                grid[2][2:4] = [9, 8]
                grid[3][2:4] = [7, 6]
            return grid

        identity = {
            "schema": "ztare-transition-identity-v1",
            "kind": "dynamics",
            "authority": "environment_adapter",
            "source_epoch": 0,
            "target_epoch": 0,
            "object_correspondence": [],
            "evidence_refs": ["metamorphic-fixture"],
        }
        rows = [
            {
                "t": 101 + index * 17,
                "a": action,
                "s": state(7 if index < 2 else 6),
                "s_next": consequence(7 if index < 2 else 6, reveal=index < 2),
                "identity": identity,
            }
            for index, action in enumerate(actions)
        ]
        (episodes / "episode_001.jsonl").write_text(
            "\n".join(json.dumps(row) for row in rows) + "\n",
            encoding="utf-8",
        )
        lowering = {
            "op": "region_event",
            "mover_colors": [1, 2],
            "rect": [2, 2, 3, 3],
            "edge": "exit",
            "writes": [
                [9, [[2, 2]]],
                [8, [[2, 3]]],
                [7, [[3, 2]]],
                [6, [[3, 3]]],
            ],
        }
        event = {
            "identity_status": "catalog_operation_reuse_candidate",
            "operation_identity": operation_identity,
            "operation_identity_sha256": operation_sha,
            "lowering_kind": "region_event",
            "lowering": lowering,
            "boundary_evidence": {
                "source_rect": [2, 2, 3, 3],
                "prior_support_rows": [0],
                "support_count": 2,
                "distinct_interventions": 2,
            },
        }
        result = _mine_task_operation_domain_selector(
            project,
            context={
                "task_id": task_id,
                "ref": "workspace/inspect.json",
                "sha256": "a" * 64,
                "summary": {"catalog_residual_event_candidates": [event]},
            },
            episode_ref="raw/episodes/episode_001.jsonl",
            max_margin=2,
        )
        assert result is not None
        return result

    first = run_case(tmp_path / "case_a", (0, 1, 2))
    relabeled = run_case(tmp_path / "case_b", (3, 2, 0))

    assert first["candidate_delta_admissible"] is True
    assert relabeled["candidate_delta_admissible"] is True
    assert first["operation_identity"] == relabeled["operation_identity"]
    assert first["operation_identity_sha256"] == relabeled[
        "operation_identity_sha256"
    ]
    assert first["operation_guard"] == relabeled["operation_guard"]
    assert first["domain_evidence"]["selected_margin"] == 1
    assert first["domain_evidence"]["base_wrong_rows"] == 2
    assert first["domain_evidence"]["unguarded_wrong_rows"] == 1
    assert first["domain_evidence"]["guarded_wrong_rows"] == 0


def test_operation_domain_selector_composes_subject_with_consequence_precondition(
    tmp_path: Path,
) -> None:
    """A remote consequence state is a candidate domain factor, not a new op."""
    from ztare.worldmodel.leaf_workbench import (
        _mine_task_operation_domain_selector,
        _stable_json_sha256,
    )

    project = tmp_path / "project"
    workspace = project / "workspace"
    episodes = project / "raw" / "episodes"
    workspace.mkdir(parents=True)
    episodes.mkdir(parents=True)
    source = (
        "def step(state, action, t):\n"
        "    out = [list(row) for row in state]\n"
        "    out[2][0] = out[3][0] = 0\n"
        "    out[2][2], out[3][2] = 1, 2\n"
        "    return tuple(tuple(row) for row in out)\n"
    )
    source_path = workspace / "base.py"
    source_path.write_text(source, encoding="utf-8")
    source_sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
    task_id = "task-factored-operation-domain"
    (workspace / "latest_harness_weakness.json").write_text(
        json.dumps(
            {
                "workbench_task": {
                    "task_id": task_id,
                    "source_ref": "workspace/base.py",
                    "source_sha256": source_sha,
                }
            }
        ),
        encoding="utf-8",
    )
    operation_identity = {
        "relation": "boundary_conditioned_consequence",
        "subject_role": "moves_under_actions",
        "boundary": "arrival",
        "consequence_role": "remote_effect",
    }
    operation_sha = _stable_json_sha256(operation_identity)
    lowering = {
        "op": "region_event",
        "mover_colors": [1, 2],
        "rect": [2, 2, 3, 3],
        "edge": "enter",
        "writes": [[9, [[7, 0], [7, 1]]]],
    }
    identity = {
        "schema": "ztare-transition-identity-v1",
        "kind": "dynamics",
        "authority": "environment_adapter",
        "source_epoch": 3,
        "target_epoch": 3,
        "object_correspondence": [],
        "evidence_refs": ["metamorphic-fixture"],
    }

    def transition(marker: int, *, enabled: bool) -> dict:
        state = [[0 for _ in range(8)] for _ in range(8)]
        state[2][0], state[3][0] = 1, 2
        state[7][0:2] = [5, 6] if enabled else [6, 5]
        state[7][7] = marker
        successor = [row[:] for row in state]
        successor[2][0] = successor[3][0] = 0
        successor[2][2], successor[3][2] = 1, 2
        if enabled:
            successor[7][0:2] = [9, 9]
        return {
            "t": marker,
            "a": marker % 4,
            "s": state,
            "s_next": successor,
            "identity": identity,
        }

    rows = [
        transition(11, enabled=True),
        transition(13, enabled=True),
        transition(17, enabled=False),
        transition(19, enabled=False),
    ]
    (episodes / "episode_001.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )
    result = _mine_task_operation_domain_selector(
        project,
        context={
            "task_id": task_id,
            "ref": "workspace/inspect.json",
            "sha256": "a" * 64,
            "summary": {
                "catalog_residual_event_candidates": [
                    {
                        "identity_status": "operation_recurrence_required",
                        "operation_identity": operation_identity,
                        "operation_identity_sha256": operation_sha,
                        "lowering_kind": "region_event",
                        "lowering": lowering,
                        "boundary_evidence": {},
                    }
                ]
            },
        },
        episode_ref="raw/episodes/episode_001.jsonl",
        max_margin=2,
    )

    assert result is not None
    assert result["candidate_delta_admissible"] is True
    assert result["domain_evidence"]["selected_chart_role"] == (
        "consequence_precondition"
    )
    assert result["operation_guard"]["lowering"]["when_region"] == [
        7,
        0,
        7,
        1,
        [5, 6],
    ]
    assert result["operation_identity"] == operation_identity


def test_counterexample_context_surfaces_finite_commuting_catalog_transport(
    tmp_path: Path,
) -> None:
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.leaf_workbench import (
        render_worldmodel_leaf_workbench_fragment,
        run_worldmodel_counterexample_context_probe,
        worldmodel_leaf_workbench_records,
    )

    project = tmp_path / "project"
    workspace = project / "workspace"
    episodes = project / "raw" / "episodes"
    workspace.mkdir(parents=True)
    episodes.mkdir(parents=True)

    # The isolated singleton of the same value forces component scoping.  The
    # two exact scope presentations are deliberately left unresolved: the
    # finite square identifies the operation, not the component's identity.
    source = (
        (8, 8, 8, 8, 0),
        (0, 0, 0, 0, 0),
        (0, 0, 8, 0, 0),
    )
    transported_source = (
        (8, 8, 3, 3, 0),
        (0, 0, 0, 0, 0),
        (0, 0, 8, 0, 0),
    )
    consequence = (
        (0, 8, 8, 8, 8),
        (0, 0, 0, 0, 0),
        (0, 0, 8, 0, 0),
    )
    transported_consequence = (
        (0, 8, 8, 3, 3),
        (0, 0, 0, 0, 0),
        (0, 0, 8, 0, 0),
    )
    log = EpisodeLog()
    log.append(source, 0, consequence, t=10)
    log.append(transported_source, 0, transported_consequence, t=11)
    log.write_jsonl(episodes / "episode_001.jsonl")
    (workspace / "latest_patch_base_regression.json").write_text(
        json.dumps(
            {
                "candidate_regression_receipt": {
                    "candidate_relation": "regression",
                    "quotient_comparison": {
                        "relation": "changed_support",
                        "candidate_top_quotient": {
                            "first_row": 1,
                            "t": 11,
                            "action": 0,
                            "bbox": [0, 0, 0, 4],
                        },
                        "best_prior_top_quotient": {
                            "first_row": 0,
                            "t": 10,
                            "action": 0,
                            "bbox": [0, 0, 0, 4],
                        },
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    payload = json.loads(run_worldmodel_counterexample_context_probe(project))
    transports = payload["commuting_transports"]
    assert len(transports) == 1
    witness = transports[0]
    assert witness["observed_commutation"] is True
    assert witness["operation"] == {
        "op": "consume_extremal",
        "color": 8,
        "replacement": 3,
        "axis": "row",
        "extreme": "max",
        "count": 2,
    }
    assert witness["lifecycle_compatibility"]["basis"] == (
        "legacy_monotone_unit_clock_no_attested_boundary"
    )
    assert {
        row["select"] for row in witness["component_selector_presentations"]
    } == {"largest", "widest"}
    assert witness["component_identity_status"].startswith("property_witness_only")
    assert witness["global_equivariance_authorized"] is False
    assert witness["quotient_authorized"] is False
    assert witness["carrier_promotion_authorized"] is False

    records = worldmodel_leaf_workbench_records(project)
    surfaced = [
        row
        for row in records
        if row.get("capability_id") == "inspect_worldmodel_counterexample_context"
    ]
    assert surfaced[0]["source_type"] == "leaf_workbench_capability"
    assert "available on request" in surfaced[0]["summary"]
    assert "commuting_transports" not in surfaced[0]
    assert "behavioral_fiber" not in surfaced[0]
    fragment = render_worldmodel_leaf_workbench_fragment(project)
    assert "`inspect_worldmodel_counterexample_context`" in fragment
    assert "observed finite arrow transport" not in fragment


def test_counterexample_context_keeps_distinct_source_and_consequence_edges(
    tmp_path: Path,
) -> None:
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.leaf_workbench import (
        run_worldmodel_counterexample_context_probe,
    )

    project = tmp_path / "project"
    workspace = project / "workspace"
    episodes = project / "raw" / "episodes"
    workspace.mkdir(parents=True)
    episodes.mkdir(parents=True)

    background = [[3 for _ in range(6)] for _ in range(6)]
    source = [row[:] for row in background]
    source[0][0:2] = [12, 12]
    source[1][0:2] = [9, 9]
    transported_source = [row[:] for row in background]
    transported_source[2][3:5] = [12, 12]
    transported_source[3][3:5] = [9, 9]
    shared_consequence = [row[:] for row in background]
    shared_consequence[4][0:2] = [12, 12]
    shared_consequence[5][0:2] = [9, 9]

    log = EpisodeLog()
    log.append(source, 0, shared_consequence, t=10)
    log.append(transported_source, 0, shared_consequence, t=11)
    log.write_jsonl(episodes / "episode_001.jsonl")
    (workspace / "latest_patch_base_regression.json").write_text(
        json.dumps(
            {
                "candidate_regression_receipt": {
                    "candidate_relation": "improved_but_gate_failed",
                    "quotient_comparison": {
                        "relation": "changed_support",
                        "candidate_top_quotient": {
                            "first_row": 1,
                            "t": 11,
                            "action": 0,
                            "bbox": [2, 3, 3, 4],
                        },
                        "best_prior_top_quotient": {
                            "first_row": 0,
                            "t": 10,
                            "action": 0,
                            "bbox": [0, 0, 1, 1],
                        },
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    payload = json.loads(run_worldmodel_counterexample_context_probe(project))
    assert len(payload["commuting_transports"]) == 1
    witness = payload["commuting_transports"][0]
    assert witness["schema"] == "ztare-observed-arrow-transport-v1"
    assert witness["transport_kind"] == "arrow_morphism"
    assert witness["source_operation"]["op"] == "translate_block"
    assert witness["consequence_operation"] == {"op": "identity"}
    assert witness["observed_relation"] == "one_step_behavioral_merge"
    assert witness["operation"] == {
        "source_operation": witness["source_operation"],
        "consequence_operation": {"op": "identity"},
    }
    assert witness["quotient_authorized"] is False
    assert witness["carrier_promotion_authorized"] is False


def test_counterexample_context_surfaces_full_observed_behavior_fiber(
    tmp_path: Path,
) -> None:
    """A nearest pair must not erase other presentations of one consequence."""
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.leaf_workbench import (
        run_worldmodel_counterexample_context_probe,
    )
    from ztare.worldmodel.transition_identity import TransitionIdentity

    project = tmp_path / "project"
    workspace = project / "workspace"
    episodes = project / "raw" / "episodes"
    workspace.mkdir(parents=True)
    episodes.mkdir(parents=True)

    background = [[3 for _ in range(8)] for _ in range(8)]

    def presentation(top: int, left: int) -> list[list[int]]:
        state = [row[:] for row in background]
        state[top][left : left + 2] = [12, 12]
        state[top + 1][left : left + 2] = [9, 9]
        return state

    sources = [presentation(0, 0), presentation(2, 3), presentation(5, 1)]
    consequence = presentation(6, 6)
    identity = TransitionIdentity(
        kind="dynamics",
        authority="environment_adapter",
        source_epoch=2,
        target_epoch=2,
    )
    log = EpisodeLog()
    for action, source in enumerate(sources):
        log.append(source, action, consequence, t=85, identity=identity)
    log.write_jsonl(episodes / "episode_001.jsonl")

    submissions = workspace / "submissions"
    submissions.mkdir()
    base = submissions / "base.py"
    base.write_text(
        "def step(state, action, t):\n"
        "    return state\n",
        encoding="utf-8",
    )
    base_sha = hashlib.sha256(base.read_bytes()).hexdigest()
    first = submissions / "first.py"
    first.write_text(
        "PATCH_BASE = {\n"
        "    'source_ref': 'workspace/submissions/base.py',\n"
        f"    'sha256': '{base_sha}',\n"
        "}\n"
        f"SOURCE = {tuple(tuple(row) for row in sources[0])!r}\n"
        f"TARGET = {tuple(tuple(row) for row in consequence)!r}\n"
        "def PATCH_DELTA(base_next, state, action):\n"
        "    return TARGET if state == SOURCE else base_next\n",
        encoding="utf-8",
    )
    first_sha = hashlib.sha256(first.read_bytes()).hexdigest()
    second = submissions / "second.py"
    second.write_text(
        "PATCH_BASE = {\n"
        "    'source_ref': 'workspace/submissions/first.py',\n"
        f"    'sha256': '{first_sha}',\n"
        "}\n"
        f"SOURCE = {tuple(tuple(row) for row in sources[1])!r}\n"
        f"TARGET = {tuple(tuple(row) for row in consequence)!r}\n"
        "def PATCH_DELTA(base_next, state, action):\n"
        "    return TARGET if state == SOURCE else base_next\n",
        encoding="utf-8",
    )
    second_sha = hashlib.sha256(second.read_bytes()).hexdigest()
    (workspace / "latest_patch_base_regression.json").write_text(
        json.dumps(
            {
                "candidate_regression_receipt": {
                    "candidate_relation": "improved_but_gate_failed",
                    "candidate_submission": "workspace/submissions/second.py",
                    "candidate_sha": second_sha,
                    "candidate_exact_rows": 2,
                    "quotient_comparison": {
                        "relation": "changed_support",
                        "candidate_top_quotient": {
                            "first_row": 2,
                            "t": 85,
                            "action": 2,
                            "bbox": [5, 1, 6, 2],
                        },
                        "best_prior_top_quotient": {
                            "first_row": 1,
                            "t": 85,
                            "action": 1,
                            "bbox": [2, 3, 3, 4],
                        },
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    payload = json.loads(run_worldmodel_counterexample_context_probe(project))
    fiber = payload["behavioral_fiber"]
    assert fiber["schema"] == "ztare-observed-one-step-behavioral-fiber-v1"
    assert fiber["member_rows"] == [0, 1, 2]
    assert fiber["member_count"] == 3
    assert fiber["distinct_source_states"] == 3
    assert fiber["interventions"] == [0, 1, 2]
    assert fiber["distinct_interventions"] == 3
    assert fiber["intervention_relation"] == "varied_interventions_one_consequence"
    assert fiber["observed_relation"] == "many_presentations_one_consequence"
    assert all(
        member["lifecycle_compatibility"]["basis"]
        == "adapter_attested_same_dynamics_epoch"
        for member in fiber["members"]
    )
    assert fiber["global_equivariance_authorized"] is False
    assert fiber["quotient_authorized"] is False
    assert fiber["carrier_promotion_authorized"] is False

    chain = payload["patch_base_chain_effects"]
    assert chain["schema"] == "ztare-patch-base-behavioral-fiber-effects-v1"
    assert chain["observed_chain_relation"] == (
        "distinct_layers_add_members_of_one_observed_behavioral_fiber"
    )
    assert chain["member_rows"] == [0, 1, 2]
    assert [
        layer["added_correct_member_rows"] for layer in chain["layers"]
    ] == [[], [0], [1]]
    assert chain["distinct_rows_added_across_layers"] == [0, 1]
    assert chain["global_operation_identity_authorized"] is False
    assert chain["carrier_promotion_authorized"] is False

    from ztare.worldmodel.retry_surface import _compact_patch_base_chain_effects

    compact_chain = _compact_patch_base_chain_effects(chain)
    assert compact_chain["observed_chain_relation"] == chain["observed_chain_relation"]
    assert [
        layer["added_correct_member_rows"] for layer in compact_chain["layers"]
    ] == [[], [0], [1]]
    assert all(
        "fiber_behavior_sha256" not in layer
        for layer in compact_chain["layers"]
    )


def test_leaf_workbench_rejects_stale_pinned_repair_receipt(tmp_path: Path) -> None:
    from ztare.worldmodel.leaf_workbench import (
        _current_regression_receipt,
        _latest_counterexample_trace,
    )

    project = tmp_path / "project"
    workspace = project / "workspace"
    episodes = project / "raw" / "episodes"
    workspace.mkdir(parents=True)
    episodes.mkdir(parents=True)
    (episodes / "episode_001.jsonl").write_text("{}\n", encoding="utf-8")
    (workspace / "latest_patch_base_regression.json").write_text(
        json.dumps(
            {
                "evidence_epoch": {"epoch_sha256": "stale"},
                "candidate_regression_receipt": {"marker": "stale"},
                "counterexample_trace": {"marker": "stale"},
            }
        ),
        encoding="utf-8",
    )
    (project / "latest_eval_results.json").write_text(
        json.dumps({"candidate_regression_receipt": {"marker": "current"}}),
        encoding="utf-8",
    )

    receipt, source_ref = _current_regression_receipt(project)
    assert receipt == {"marker": "current"}
    assert source_ref == "latest_eval_results.json"
    assert _latest_counterexample_trace(project) == {}


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
    assert "candidate_delta_admissible" not in summary
    assert summary["candidate_family_admissible"] is None
    assert summary["candidate_predicates"] == []
    assert summary["lowerability_status"] == "conjecture_singleton_support"
    assert summary["identity_support"]["authority_granted"] is False
    assert summary["identity_support"]["distinct_positive_observations"] == 1
    assert summary["conjecture_predicates"]
    assert summary["conjecture_predicates"][0]["lowering_scope"] == "global_carrier_input"
    names = {
        feature["name"]
        for feature in summary["conjecture_predicates"][0]["features"]
    }
    assert "window_values" in names
    assert "action" in names


def test_lowerable_selector_consumes_kernel_receipt_through_observation_ref_alias(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from ztare.worldmodel import leaf_workbench

    project = tmp_path / "project"
    workspace = project / "workspace"
    receipts = workspace / "leaf_workbench_action_receipts"
    receipts.mkdir(parents=True)
    (project / "latest_eval_results.json").write_text("{}", encoding="utf-8")
    (workspace / "latest_harness_weakness.json").write_text(
        json.dumps(
            {
                "workbench_task": {
                    "task_id": "task-a",
                    "failure_class": "unquotiented_counterexample_chart_missing",
                }
            }
        ),
        encoding="utf-8",
    )
    donor = {
        "candidate_ref": "workspace/submissions/donor.py",
        "candidate_sha256": "d" * 64,
        "authority": "diagnostic_operation_salvage_only",
        "baseline_wrong_cells": 9,
        "donor_wrong_cells": 1,
    }
    receipt_ref = "workspace/leaf_workbench_action_receipts/inspect.json"
    (project / receipt_ref).write_text(
        json.dumps(
            {
                "schema": "ztare-leaf-workbench-kernel-receipt-v1",
                "capability_id": "inspect_worldmodel_counterexample_context",
                "request": {"input_refs": {"task_id": "task-a"}},
                "receipt": {
                    "output_summary": json.dumps(
                        {
                            "observation_sha256": "observation-a",
                            "counterexample_observation": {
                                "consumer_quotient_difference": {
                                    "changed_factor_names": ["finite_configuration"]
                                },
                                "archived_residual_donors": [donor],
                            },
                        }
                    )
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        leaf_workbench,
        "_mine_task_operation_domain_selector",
        lambda *_args, **_kwargs: None,
    )

    result = leaf_workbench._handle_lowerable_selector_action(
        project,
        {
            "input_refs": {
                "observation_ref": receipt_ref,
                "latest_eval_ref": "latest_eval_results.json",
            }
        },
        None,
        leaf_workbench.WORLD_MODEL_LEAF_WORKBENCH_CONTRACT,
    )
    summary = json.loads(result["output_summary"])

    assert result["input_hashes"]["upstream_receipt_refs"] == [receipt_ref]
    assert summary["lowerability_status"] == "consumer_quotient_available"
    assert summary["archived_residual_donors"] == [donor]


def test_active_task_fragment_surfaces_operation_donor_consequence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from ztare.worldmodel import leaf_workbench

    workspace = tmp_path / "workspace"
    submissions = workspace / "submissions"
    submissions.mkdir(parents=True)
    source_ref = "workspace/submissions/frontier.py"
    (tmp_path / source_ref).write_text("PROGRAM = None\n", encoding="utf-8")
    (workspace / "latest_harness_weakness.json").write_text(
        json.dumps(
            {
                "workbench_task": {
                    "task_id": "task-a",
                    "failure_class": "counterexample_chart",
                    "source_ref": source_ref,
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        leaf_workbench,
        "_active_task_consumed_payload",
        lambda _project: (
            {
                "capability_id": "mine_worldmodel_lowerable_selectors",
                "input_hashes": {"kernel_receipt_ref": "workspace/receipt.json"},
            },
            {
                "observation_sha256": "observation-a",
                "consumer_quotient_difference": {
                    "changed_factor_names": ["finite_configuration"]
                },
                "archived_residual_donors": [
                    {
                        "candidate_ref": "workspace/submissions/donor.py",
                        "candidate_sha256": "d" * 64,
                        "historical_disposition": "rejected",
                        "authority": "diagnostic_operation_salvage_only",
                        "baseline_wrong_cells": 150,
                        "donor_wrong_cells": 8,
                        "relation": "strictly_closer_on_counterexample",
                    }
                ],
            },
        ),
    )

    fragment = leaf_workbench._render_active_task_first_fire_fragment(tmp_path)

    assert "workspace/submissions/donor.py" in fragment
    assert "counterexample wrong cells 150→8" in fragment
    assert "salvage only the improving operation" in fragment
    assert "archived program disposition remains in force" in fragment


def test_lowerable_selector_requires_recurrence_before_granting_authority(tmp_path: Path):
    from ztare.worldmodel.leaf_workbench import (
        run_worldmodel_lowerable_selector_miner,
    )

    project = tmp_path / "arc3_ab12_gov"
    ws = project / "workspace"
    raw = project / "raw" / "episodes"
    ws.mkdir(parents=True)
    raw.mkdir(parents=True)
    source = [[5, 5, 5], [8, 8, 5], [5, 5, 5]]
    target = [[5, 5, 5], [3, 3, 5], [5, 5, 5]]
    rows = [
        {"t": 0, "a": 1, "s": source, "s_next": target},
        {"t": 1, "a": 0, "s": source, "s_next": source},
        {"t": 2, "a": 1, "s": source, "s_next": target},
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
                }
            }
        ),
        encoding="utf-8",
    )

    summary = json.loads(
        run_worldmodel_lowerable_selector_miner(
            project,
            regression_ref="workspace/latest_patch_base_regression.json",
            episode_ref="raw/episodes/episode_001.jsonl",
        )
    )

    assert summary["candidate_family_admissible"] is True
    assert summary["candidate_delta_admissible"] is True
    assert summary["candidate_predicates"]
    assert summary["conjecture_predicates"] == []
    assert summary["identity_support"]["authority_granted"] is True
    assert summary["identity_support"]["distinct_positive_observations"] == 2


def test_generic_selector_outcome_consumes_counterexample_route(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from ztare.worldmodel import leaf_workbench

    project = tmp_path / "arc3_ab12_gov"
    workspace = project / "workspace"
    episodes = project / "raw" / "episodes"
    receipts = workspace / "leaf_workbench_action_receipts"
    receipts.mkdir(parents=True)
    episodes.mkdir(parents=True)
    source = [[5, 5, 5], [8, 8, 5], [5, 5, 5]]
    target = [[5, 5, 5], [3, 3, 5], [5, 5, 5]]
    (episodes / "episode_001.jsonl").write_text(
        json.dumps({"t": 0, "a": 1, "s": source, "s_next": target}) + "\n",
        encoding="utf-8",
    )
    (workspace / "latest_patch_base_regression.json").write_text(
        json.dumps(
            {
                "counterexample_trace": {
                    "mismatch_classes": [
                        {"first_row": 0, "signature": {"bbox": [1, 0, 1, 1]}}
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    upstream = receipts / "inspect.json"
    donor = {
        "schema": "ztare-residual-donor-v1",
        "authority": "diagnostic_operation_salvage_only",
        "candidate_ref": "workspace/submissions/rejected.py",
        "candidate_sha256": "d" * 64,
        "historical_disposition": "rejected",
        "baseline_wrong_cells": 9,
        "donor_wrong_cells": 2,
        "relation": "strictly_closer_on_counterexample",
        "prediction_sha256": "e" * 64,
    }
    upstream.write_text(
        json.dumps(
            {
                "schema": "ztare-leaf-workbench-kernel-receipt-v1",
                "capability_id": "inspect_worldmodel_counterexample_context",
                "request": {"input_refs": {"task_id": "task-a"}},
                "receipt": {
                    "capability_id": "inspect_worldmodel_counterexample_context",
                    "output_summary": json.dumps(
                        {
                            "observation_sha256": "observation-a",
                            "counterexample_observation": {
                                "consumer_quotient_difference": {
                                    "schema": "ztare-consumer-quotient-difference-v1",
                                    "changed_factor_names": ["finite_configuration"],
                                },
                                "archived_residual_donors": [donor],
                            },
                        }
                    ),
                },
            }
        ),
        encoding="utf-8",
    )
    (workspace / "latest_harness_weakness.json").write_text(
        json.dumps(
            {
                "workbench_task": {
                    "task_id": "task-a",
                    "failure_class": "unquotiented_counterexample_chart_missing",
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        leaf_workbench,
        "_mine_task_operation_domain_selector",
        lambda *_args, **_kwargs: None,
    )
    summary = json.loads(
        leaf_workbench.run_worldmodel_lowerable_selector_miner(
            project,
            upstream_receipt_refs=(
                "workspace/leaf_workbench_action_receipts/inspect.json",
            ),
        )
    )
    rows = [
        json.loads(line)
        for line in (workspace / "counterexample_observation_routes.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]

    assert rows[-1]["event"] == "first_fire"
    assert rows[-1]["task_id"] == "task-a"
    assert rows[-1]["observation_sha256"] == "observation-a"
    assert rows[-1]["payload"]["outcome"] == summary["lowerability_status"]
    assert summary["lowerability_status"] == "consumer_quotient_available"
    assert summary["candidate_family_admissible"] is False
    assert summary["archived_residual_donors"] == [donor]


def test_lowerable_selector_does_not_count_epoch_boundary_as_law_recurrence(
    tmp_path: Path,
) -> None:
    from ztare.worldmodel.leaf_workbench import (
        run_worldmodel_lowerable_selector_miner,
    )

    project = tmp_path / "arc3_ab12_gov"
    workspace = project / "workspace"
    episodes = project / "raw" / "episodes"
    workspace.mkdir(parents=True)
    episodes.mkdir(parents=True)
    source = [[5, 5, 5], [8, 8, 5], [5, 5, 5]]
    target = [[5, 5, 5], [3, 3, 5], [5, 5, 5]]
    dynamics = {
        "schema": "ztare-transition-identity-v1",
        "kind": "dynamics",
        "authority": "environment_adapter",
        "source_epoch": 0,
        "target_epoch": 0,
        "object_correspondence": [],
        "evidence_refs": ["fixture:dynamics"],
    }
    boundary = {
        "schema": "ztare-transition-identity-v1",
        "kind": "epoch_boundary",
        "authority": "environment_adapter",
        "source_epoch": 0,
        "target_epoch": 1,
        "boundary_kind": "fixture:terminal",
        "object_correspondence": [],
        "evidence_refs": ["fixture:terminal"],
    }
    rows = [
        {"t": 0, "a": 1, "s": source, "s_next": target, "identity": dynamics},
        {"t": 1, "a": 1, "s": source, "s_next": target, "identity": boundary},
        {"t": 2, "a": 0, "s": source, "s_next": source, "identity": dynamics},
    ]
    (episodes / "episode_001.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )
    (workspace / "latest_patch_base_regression.json").write_text(
        json.dumps(
            {
                "counterexample_trace": {
                    "mismatch_classes": [
                        {
                            "first_row": 0,
                            "t": 0,
                            "action": 1,
                            "signature": {"bbox": [1, 0, 1, 1]},
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    summary = json.loads(
        run_worldmodel_lowerable_selector_miner(
            project,
            regression_ref="workspace/latest_patch_base_regression.json",
            episode_ref="raw/episodes/episode_001.jsonl",
        )
    )

    assert summary["excluded_transition_count"] == 1
    assert summary["identity_support"]["scope"] == "law_owned_transition"
    assert summary["identity_support"]["distinct_positive_observations"] == 1
    assert summary["identity_support"]["authority_granted"] is False
    assert summary["candidate_family_admissible"] is None
    assert summary["lowerability_status"] == "conjecture_singleton_support"


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
    source = "def step(grid, action, t): return grid\n"
    (project / "test_model.py").write_text(source)
    source_sha = hashlib.sha256(source.encode()).hexdigest()
    (ws / "latest_harness_weakness.json").write_text(
        json.dumps(
            {
                "schema": "ztare-harness-weakness-receipt-v1",
                "active_frontier": {
                    "candidate_sha": source_sha,
                    "source_ref": "test_model.py",
                },
                "workbench_task": {
                    "task_id": "strategy-gate-task",
                    "source_ref": "test_model.py",
                    "source_sha256": source_sha,
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

    message = blocked_control_missing_evidence_action_retry_message(
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

    message = blocked_control_missing_evidence_action_retry_message(
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


def test_lowerability_block_compiles_selected_parent_action_to_receipt(
    tmp_path: Path,
):
    project = tmp_path / "project"
    workspace = project / "workspace"
    workspace.mkdir(parents=True)
    source = "def step(grid, action, t):\n    return grid\n"
    (project / "test_model.py").write_text(source, encoding="utf-8")
    source_sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
    capability_id = "inspect_worldmodel_counterexample_context"
    (workspace / "latest_harness_weakness.json").write_text(
        json.dumps(
            {
                "active_frontier": {"candidate_sha": source_sha},
                "workbench_task": {
                    "schema": "ztare-leaf-workbench-task-v1",
                    "task_id": "context-task",
                    "source_ref": "test_model.py",
                    "admissible_capability_ids": [
                        capability_id,
                        "mine_worldmodel_separating_features",
                        "mine_worldmodel_lowerable_selectors",
                    ],
                    "morphism_sequence": [
                        capability_id,
                        "mine_worldmodel_separating_features",
                        "mine_worldmodel_lowerable_selectors",
                    ],
                    "objective": "observe the counterexample relation",
                },
            }
        ),
        encoding="utf-8",
    )
    seen: list[str] = []

    def fake_handler(project_dir, req, row, contract):
        requested = str(req.get("capability_id") or "")
        seen.append(requested)
        return {
            "capability_id": requested,
            "output_summary": json.dumps(
                {
                    "schema": "ztare-counterexample-observation-triple-v1",
                    "observation_sha256": "a" * 64,
                }
            ),
        }

    def blocked(next_action: str) -> str:
        return "LOWERABILITY_BLOCKED: " + json.dumps(
            {
                "next_action": next_action,
                "obstruction": "missing bounded observation",
            }
        )

    assert blocked_control_missing_evidence_action_retry_message(
        enabled=True,
        project_dir=project,
        thesis_text=blocked("request an unrelated unavailable sensor"),
        records_fn=lambda _project: [
            {"capability_id": capability_id, "source_ref": "test_model.py"}
        ],
        action_handlers={capability_id: fake_handler},
    ) is None

    # A multi-capability task plus generic prose is not an action selection.
    # In particular, mentioning an already-executed "morphism" must not reset
    # the task's program counter and replay the sequence.
    assert blocked_control_missing_evidence_action_retry_message(
        enabled=True,
        project_dir=project,
        thesis_text=blocked(
            "Request another typed observation only if its morphism inputs differ"
        ),
        records_fn=lambda _project: [
            {"capability_id": capability_id, "source_ref": "test_model.py"}
        ],
        action_handlers={capability_id: fake_handler},
    ) is None

    def failed_handler(project_dir, req, row, contract):
        raise ValueError("selected observation unavailable")

    failed = blocked_control_missing_evidence_action_retry_message(
        enabled=True,
        project_dir=project,
        thesis_text=blocked(f"Run {capability_id} through the parent kernel"),
        records_fn=lambda _project: [
            {"capability_id": capability_id, "source_ref": "test_model.py"}
        ],
        action_handlers={capability_id: failed_handler},
    )
    assert failed is not None
    assert "selected observation unavailable" in failed

    message = blocked_control_missing_evidence_action_retry_message(
        enabled=True,
        project_dir=project,
        thesis_text=blocked(f"Run {capability_id} through the parent kernel"),
        records_fn=lambda _project: [
            {"capability_id": capability_id, "source_ref": "test_model.py"}
        ],
        action_handlers={
            capability_id: fake_handler,
            "mine_worldmodel_separating_features": fake_handler,
            "mine_worldmodel_lowerable_selectors": fake_handler,
        },
    )

    assert message is not None
    assert "LEAF_WORKBENCH_RECEIPT:" in message
    assert seen == [
        capability_id,
        "mine_worldmodel_separating_features",
        "mine_worldmodel_lowerable_selectors",
    ]


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
    evaluator = key_v1["evaluator_implementation"]
    assert len(evaluator["sha256"]) == 64
    assert "worldmodel/carrier_loader.py" in evaluator["module_hashes"]
    assert "worldmodel/spec_catalog.py" in evaluator["module_hashes"]


def test_evaluator_dependency_mutation_does_not_relabel_loaded_bitmap_code(
    tmp_path: Path,
    monkeypatch,
):
    """A running process keeps the identity of code it actually loaded."""
    from ztare.validator.core import pre_judge_gate
    from ztare.worldmodel import evidence_consolidation
    from ztare.worldmodel.gates import evaluator_implementation_identity

    project = tmp_path / "project"
    project.mkdir()
    candidate = project / "test_model.py"
    candidate.write_text("def step(state, action, t): return state\n", encoding="utf-8")
    _write_harness(project, "print('{}')\n")
    gate_payload = {"harness_ok": True, "gated_sha256": "candidate", "gates": []}

    before_gate = pre_judge_gate._gate_cache_key(  # noqa: SLF001
        project,
        candidate,
        project / "gate_harness.py",
    )
    before_eval = evaluation_cache_key(
        project_dir=project,
        candidate_path=candidate,
        gate_payload=gate_payload,
    )
    before_bitmap = evidence_consolidation._row_bitmap_evaluator_sha256()  # noqa: SLF001

    spec_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "ztare"
        / "worldmodel"
        / "spec_catalog.py"
    ).resolve()
    original_read_bytes = Path.read_bytes

    def mutated_read_bytes(path: Path) -> bytes:
        content = original_read_bytes(path)
        if path.resolve() == spec_path:
            return content + b"\n# metamorphic evaluator mutation\n"
        return content

    monkeypatch.setattr(Path, "read_bytes", mutated_read_bytes)

    after_gate = pre_judge_gate._gate_cache_key(  # noqa: SLF001
        project,
        candidate,
        project / "gate_harness.py",
    )
    after_eval = evaluation_cache_key(
        project_dir=project,
        candidate_path=candidate,
        gate_payload=gate_payload,
    )
    after_bitmap = evidence_consolidation._row_bitmap_evaluator_sha256()  # noqa: SLF001

    assert before_gate and after_gate and before_gate == after_gate
    assert before_eval["key_sha256"] == after_eval["key_sha256"]
    assert before_bitmap == after_bitmap
    assert after_eval["evaluator_implementation"]["sha256"] == after_bitmap
    assert evaluator_implementation_identity()["sha256"] == after_bitmap


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
