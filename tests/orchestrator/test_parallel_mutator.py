"""Tests for orchestrator/parallel_mutator.py."""

from __future__ import annotations

import time

import pytest

from src.ztare.orchestrator.parallel_mutator import (
    DEFAULT_PARALLEL_PERSONAS,
    MutatorResult,
    MutatorTask,
    build_default_tasks,
    pick_best_candidate,
    run_parallel_mutators,
)


# ── build_default_tasks ──────────────────────────────────────────────────


class TestBuildDefaultTasks:
    def test_zero_returns_empty(self):
        assert build_default_tasks(0) == []

    def test_negative_returns_empty(self):
        assert build_default_tasks(-3) == []

    def test_k3_returns_three_distinct_personas(self):
        tasks = build_default_tasks(3)
        assert len(tasks) == 3
        personas = {t.persona for t in tasks}
        assert len(personas) == 3, "K=3 should produce 3 distinct personas"
        assert personas <= set(DEFAULT_PARALLEL_PERSONAS)

    def test_k5_wraps_persona_pool(self):
        tasks = build_default_tasks(5)
        assert len(tasks) == 5
        # Workers 0,1,2 cycle the pool; workers 3,4 wrap
        assert tasks[0].persona == tasks[3].persona
        assert tasks[1].persona == tasks[4].persona

    def test_worker_ids_are_zero_indexed_and_unique(self):
        tasks = build_default_tasks(4)
        assert [t.worker_id for t in tasks] == [0, 1, 2, 3]


# ── run_parallel_mutators ────────────────────────────────────────────────


class TestRunParallelMutators:
    def test_empty_tasks_returns_empty(self):
        assert run_parallel_mutators([], mutator_fn=lambda t: None) == []

    def test_results_in_worker_id_order(self):
        # Even if completion order varies (sleeps), output is sorted
        # by worker_id for reproducibility.
        def slow_mutator(t: MutatorTask) -> MutatorResult:
            # Earlier worker_ids sleep longer → reverse completion order
            time.sleep(0.01 * (3 - t.worker_id))
            return MutatorResult(
                worker_id=t.worker_id,
                persona=t.persona,
                thesis_text=f"thesis {t.worker_id}",
                test_model_text=f"# tm {t.worker_id}",
            )

        tasks = build_default_tasks(3)
        results = run_parallel_mutators(tasks, mutator_fn=slow_mutator)
        assert [r.worker_id for r in results] == [0, 1, 2]
        assert results[1].thesis_text == "thesis 1"

    def test_failed_worker_recorded_not_propagated(self):
        def maybe_fail(t: MutatorTask) -> MutatorResult:
            if t.worker_id == 1:
                raise RuntimeError("simulated failure")
            return MutatorResult(
                worker_id=t.worker_id,
                persona=t.persona,
                thesis_text=f"thesis {t.worker_id}",
                test_model_text="",
            )

        tasks = build_default_tasks(3)
        results = run_parallel_mutators(tasks, mutator_fn=maybe_fail)
        assert len(results) == 3
        # Worker 1 produced an __error__ entry
        assert results[1].thesis_text == ""
        assert "__error__" in results[1].extras
        assert "RuntimeError" in results[1].extras["__error__"]
        # Workers 0 and 2 are intact
        assert results[0].thesis_text == "thesis 0"
        assert results[2].thesis_text == "thesis 2"


# ── pick_best_candidate ──────────────────────────────────────────────────


class TestPickBestCandidate:
    def _make(self, worker_id, score=None, thesis="t"):
        return MutatorResult(
            worker_id=worker_id,
            persona="p",
            thesis_text=thesis,
            test_model_text="tm",
            score=score,
        )

    def test_empty_returns_none(self):
        assert pick_best_candidate([]) is None

    def test_all_failed_returns_none(self):
        results = [
            self._make(0, thesis=""),
            self._make(1, thesis=""),
        ]
        assert pick_best_candidate(results) is None

    def test_pre_scored_picks_max(self):
        results = [
            self._make(0, score=10),
            self._make(1, score=85),
            self._make(2, score=42),
        ]
        winner = pick_best_candidate(results)
        assert winner is not None
        assert winner.worker_id == 1
        assert winner.score == 85

    def test_scoring_fn_overrides_pre_scored(self):
        # If a scoring_fn is provided, it always wins over `result.score`.
        results = [
            self._make(0, score=99),  # would win without scoring_fn
            self._make(1, score=10),
        ]
        winner = pick_best_candidate(results, scoring_fn=lambda r: 100 - (r.score or 0))
        assert winner.worker_id == 1, "scoring_fn should override pre-scored"

    def test_unscored_falls_back_to_first_non_empty(self):
        results = [
            self._make(2, score=None, thesis=""),  # empty → skipped
            self._make(0, score=None),
            self._make(1, score=None),
        ]
        winner = pick_best_candidate(results)
        assert winner is not None
        # Among unscored viable, pick lowest worker_id (deterministic)
        assert winner.worker_id == 0

    def test_mixed_scored_and_unscored(self):
        # If ANY candidate has a score, winner comes from the scored set —
        # unscored candidates do not silently win.
        results = [
            self._make(0, score=None),
            self._make(1, score=42),
        ]
        winner = pick_best_candidate(results)
        assert winner.worker_id == 1
