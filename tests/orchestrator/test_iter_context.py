"""Tests for IterContext (GP-157 v5.0 Phase 4a)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.ztare.orchestrator import IterContext


def _make(iteration_index: int = 0, **overrides) -> IterContext:
    defaults = dict(
        iteration_index=iteration_index,
        run_id=1234567890,
        project="gp999_test",
        workspace_dir=Path("/tmp/ztare_test_workspace"),
        rubric_data={"max_iterations": 10},
    )
    defaults.update(overrides)
    return IterContext(**defaults)


class TestConstruction:
    def test_minimal_required_fields(self):
        ctx = _make()
        assert ctx.iteration_index == 0
        assert ctx.project == "gp999_test"
        assert ctx.cage_observe_mode is False
        assert ctx.cage_meta is None
        assert ctx.extras == {}

    def test_negative_iteration_index_rejected(self):
        with pytest.raises(ValueError, match="iteration_index"):
            _make(iteration_index=-1)

    def test_negative_run_id_rejected(self):
        with pytest.raises(ValueError, match="run_id"):
            _make(run_id=-1)

    def test_workspace_dir_must_be_path(self):
        with pytest.raises(TypeError, match="workspace_dir"):
            IterContext(
                iteration_index=0,
                run_id=1,
                project="p",
                workspace_dir="/tmp/not_a_path",  # type: ignore[arg-type]
                rubric_data={},
            )


class TestImmutability:
    def test_frozen(self):
        ctx = _make()
        with pytest.raises(Exception):
            ctx.iteration_index = 99  # type: ignore[misc]

    def test_with_iteration_returns_new_instance(self):
        ctx0 = _make(iteration_index=0)
        ctx1 = ctx0.with_iteration(5)
        assert ctx0.iteration_index == 0
        assert ctx1.iteration_index == 5
        assert ctx1 is not ctx0
        # Other fields preserved
        assert ctx1.run_id == ctx0.run_id
        assert ctx1.project == ctx0.project


class TestCagePlumbing:
    def test_cage_observe_mode_default_false(self):
        ctx = _make()
        assert ctx.cage_observe_mode is False

    def test_cage_meta_pass_through(self):
        meta = {"class": "nd_features", "target_convention_homogeneity": "homogeneous"}
        ctx = _make(cage_observe_mode=True, cage_meta=meta)
        assert ctx.cage_observe_mode is True
        assert ctx.cage_meta == meta

    def test_engagement_log_path(self):
        ctx = _make(workspace_dir=Path("/tmp/ws"))
        assert ctx.cage_engagement_log_path() == Path("/tmp/ws/cage_engagement.jsonl")
