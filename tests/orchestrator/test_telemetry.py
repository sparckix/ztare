"""Tests for orchestrator/telemetry.py (GP-157 v5.0 Phase 4b)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from ztare.orchestrator import (
    CageEngagementRecord,
    IterContext,
    append_jsonl,
    emit_cage_engagement,
    format_cage_observe_summary,
)


def _make_ctx(workspace_dir: Path, iteration_index: int = 0) -> IterContext:
    return IterContext(
        iteration_index=iteration_index,
        run_id=1234567890,
        project="gp999_test",
        workspace_dir=workspace_dir,
        rubric_data={},
    )


def _fake_engagement_matrix(*, valid: bool = True) -> Any:  # type: ignore[name-defined]
    """Construct a stand-in for the real EngagementMatrix dataclass.

    Avoids importing the Cage to keep telemetry tests independent.
    The real EngagementMatrix has substrate_meta_valid,
    substrate_meta_diagnostics, topo_order, engagements — the SimpleNamespace
    matches that surface area.
    """
    return SimpleNamespace(
        substrate_meta_valid=valid,
        substrate_meta_diagnostics=["all good"] if valid else ["missing class"],
        topo_order=["g_a", "g_b", "g_c"],
        engagements={
            "g_a": (True, "engaged"),
            "g_b": (False, "wrong substrate class"),
            "g_c": (True, "engaged"),
        },
    )


# Resolve forward-reference Any
from typing import Any  # noqa: E402


class TestAppendJsonl:
    def test_creates_parent_dir(self, tmp_path):
        target = tmp_path / "subdir" / "log.jsonl"
        append_jsonl(target, json.dumps({"k": 1}))
        assert target.exists()
        assert target.read_text().strip() == '{"k": 1}'

    def test_appends_not_overwrites(self, tmp_path):
        target = tmp_path / "log.jsonl"
        append_jsonl(target, json.dumps({"i": 1}))
        append_jsonl(target, json.dumps({"i": 2}))
        lines = target.read_text().strip().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["i"] == 1
        assert json.loads(lines[1])["i"] == 2


class TestEmitCageEngagement:
    def test_emits_jsonl_line(self, tmp_path):
        ctx = _make_ctx(tmp_path)
        em = _fake_engagement_matrix()
        rec = emit_cage_engagement(ctx, utc="2026-04-25T22:00:00Z", engagement_matrix=em)

        # Returned record reflects the matrix
        assert isinstance(rec, CageEngagementRecord)
        assert rec.iter == 1  # iteration_index 0 → iter 1 (1-based for log)
        assert rec.engaged == ["g_a", "g_c"]
        assert rec.engaged_count == 2
        assert rec.substrate_meta_valid is True

        # JSONL written to canonical path
        log_path = ctx.cage_engagement_log_path()
        line = log_path.read_text().strip()
        payload = json.loads(line)
        assert payload["iter"] == 1
        assert payload["engaged_count"] == 2
        assert payload["engagements"]["g_b"]["ok"] is False

    def test_invalid_meta_serialized(self, tmp_path):
        ctx = _make_ctx(tmp_path)
        em = _fake_engagement_matrix(valid=False)
        rec = emit_cage_engagement(ctx, utc="t", engagement_matrix=em)
        assert rec.substrate_meta_valid is False
        payload = json.loads(ctx.cage_engagement_log_path().read_text().strip())
        assert payload["substrate_meta_valid"] is False
        assert payload["substrate_meta_diagnostics"] == ["missing class"]

    def test_two_iters_two_lines(self, tmp_path):
        ctx0 = _make_ctx(tmp_path, iteration_index=0)
        ctx1 = _make_ctx(tmp_path, iteration_index=1)
        emit_cage_engagement(ctx0, utc="t0", engagement_matrix=_fake_engagement_matrix())
        emit_cage_engagement(ctx1, utc="t1", engagement_matrix=_fake_engagement_matrix())
        lines = ctx0.cage_engagement_log_path().read_text().strip().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["iter"] == 1
        assert json.loads(lines[1])["iter"] == 2


class TestFormatCageObserveSummary:
    def test_valid_summary(self):
        rec = CageEngagementRecord(
            iter=3,
            utc="t",
            substrate_meta_valid=True,
            substrate_meta_diagnostics=[],
            topo_order=["a", "b", "c", "d"],
            engagements={},
            engaged_count=2,
            engaged=["a", "c"],
        )
        s = format_cage_observe_summary(rec)
        assert "2/4 gates" in s
        assert "['a', 'c']" in s
        assert "INVALID" not in s

    def test_invalid_summary(self):
        rec = CageEngagementRecord(
            iter=1,
            utc="t",
            substrate_meta_valid=False,
            substrate_meta_diagnostics=["missing class", "missing min_rows", "x"],
            topo_order=[],
            engagements={},
            engaged_count=0,
            engaged=[],
        )
        s = format_cage_observe_summary(rec)
        assert "INVALID" in s
        assert "missing class" in s

    def test_summary_truncates_long_engaged_list(self):
        rec = CageEngagementRecord(
            iter=1,
            utc="t",
            substrate_meta_valid=True,
            substrate_meta_diagnostics=[],
            topo_order=["a"] * 12,
            engagements={},
            engaged_count=8,
            engaged=["g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8"],
        )
        s = format_cage_observe_summary(rec)
        assert "…" in s
        # First 5 engaged shown, rest truncated
        assert "g6" not in s
