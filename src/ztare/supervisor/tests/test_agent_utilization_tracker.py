"""Unit tests for agent_utilization_tracker primitives."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pytest


def _force_root(monkeypatch, tmp_path: Path) -> Path:
    """Redirect UTIL_ROOT to a temp directory for test isolation."""
    from src.ztare.supervisor import agent_utilization_tracker as aut
    monkeypatch.setattr(aut, "UTIL_ROOT", tmp_path)
    return tmp_path


def test_record_then_get_daily_totals(monkeypatch, tmp_path):
    _force_root(monkeypatch, tmp_path)
    from src.ztare.supervisor.agent_utilization_tracker import (
        record_agent_session, get_daily_totals,
    )
    record_agent_session(
        role_id="research_director", agent_cli="claude",
        duration_seconds=300.0, output_tokens=4000, turn_count=5,
        session_id="t1",
    )
    record_agent_session(
        role_id="research_director", agent_cli="claude",
        duration_seconds=200.0, output_tokens=2000, turn_count=3,
        session_id="t2",
    )
    record_agent_session(
        role_id="manager", agent_cli="codex",
        duration_seconds=600.0, output_tokens=8000, turn_count=12,
        session_id="t3",
    )
    rd_total = get_daily_totals(role_id="research_director")
    assert rd_total["duration_seconds"] == 500.0
    assert rd_total["output_tokens"] == 6000
    assert rd_total["turn_count"] == 8
    assert rd_total["session_count"] == 2

    mgr_total = get_daily_totals(role_id="manager")
    assert mgr_total["duration_seconds"] == 600.0
    assert mgr_total["session_count"] == 1

    # Filtered by agent_cli
    claude_total = get_daily_totals(agent_cli="claude")
    assert claude_total["session_count"] == 2
    codex_total = get_daily_totals(agent_cli="codex")
    assert codex_total["session_count"] == 1


def test_check_utilization_allows_session_cap(monkeypatch, tmp_path):
    _force_root(monkeypatch, tmp_path)
    from src.ztare.supervisor.agent_utilization_tracker import check_utilization_allows
    # 10-minute estimate fits the default 90-min session cap
    ok, reasons = check_utilization_allows(
        role_id="research_director", agent_cli="claude",
        estimated_seconds=600,
    )
    assert ok is True
    assert reasons == []

    # 4-hour estimate blows the per-session cap
    ok, reasons = check_utilization_allows(
        role_id="research_director", agent_cli="claude",
        estimated_seconds=4 * 3600,
    )
    assert ok is False
    assert any("session cap" in r for r in reasons)


def test_check_utilization_allows_daily_accumulation(monkeypatch, tmp_path):
    _force_root(monkeypatch, tmp_path)
    # Use a synthetic role with no yaml on disk → falls back to module
    # defaults (3-hour daily cap). Isolates from any live role YAML edits.
    monkeypatch.chdir(tmp_path)
    from src.ztare.supervisor.agent_utilization_tracker import (
        record_agent_session, check_utilization_allows,
    )
    # Burn most of the daily duration cap (defaults: 3 hours = 10800s)
    record_agent_session(
        role_id="test_role_no_yaml", agent_cli="claude",
        duration_seconds=2.5 * 3600, session_id="long1",
    )
    # 30-min more session is fine: 2.5 + 0.5 = 3.0 hours = exactly cap
    ok, _ = check_utilization_allows(
        role_id="test_role_no_yaml", agent_cli="claude",
        estimated_seconds=30 * 60,
    )
    assert ok is True
    # 1 more hour pushes over the daily cap
    ok, reasons = check_utilization_allows(
        role_id="test_role_no_yaml", agent_cli="claude",
        estimated_seconds=60 * 60,
    )
    assert ok is False
    assert any("daily cap" in r for r in reasons)


def test_get_utilization_pct(monkeypatch, tmp_path):
    _force_root(monkeypatch, tmp_path)
    # Synthetic role with no yaml on disk → module default 3-hour daily cap.
    # Isolates from live role YAML edits.
    monkeypatch.chdir(tmp_path)
    from src.ztare.supervisor.agent_utilization_tracker import (
        record_agent_session, get_utilization_pct,
    )
    # 1 hour of duration → 1/3 of 3-hour daily cap
    record_agent_session(
        role_id="test_synthetic_role", agent_cli="claude",
        duration_seconds=3600, session_id="m1",
    )
    pct_dur = get_utilization_pct(role_id="test_synthetic_role", dimension="duration_seconds")
    assert 0.32 < pct_dur < 0.34  # ≈ 1/3
    # Token dimension untouched
    pct_tok = get_utilization_pct(role_id="test_synthetic_role", dimension="output_tokens")
    assert pct_tok == 0.0


def test_unknown_dimension_raises(monkeypatch, tmp_path):
    _force_root(monkeypatch, tmp_path)
    from src.ztare.supervisor.agent_utilization_tracker import get_utilization_pct
    with pytest.raises(ValueError):
        get_utilization_pct(role_id="manager", dimension="not_a_real_dim")


def test_aggregate_totals_in_persisted_payload(monkeypatch, tmp_path):
    _force_root(monkeypatch, tmp_path)
    from src.ztare.supervisor.agent_utilization_tracker import (
        record_agent_session, _daily_path,
    )
    record_agent_session(
        role_id="research_director", agent_cli="claude",
        duration_seconds=120, output_tokens=1000, turn_count=2,
    )
    record_agent_session(
        role_id="manager", agent_cli="codex",
        duration_seconds=180, output_tokens=2000, turn_count=4,
    )
    p = _daily_path()
    payload = json.loads(p.read_text())
    totals = payload["totals"]
    assert "by_role" in totals and "by_cli" in totals and "by_role_cli" in totals
    assert totals["by_role"]["research_director"]["session_count"] == 1
    assert totals["by_role_cli"]["manager:codex"]["duration_seconds"] == 180.0


def test_role_caps_loaded_from_yaml(monkeypatch, tmp_path):
    _force_root(monkeypatch, tmp_path)
    # Synthesize a yaml with a custom utilization block. Tracker looks at
    # `org/roles/<role>.yaml` relative to cwd, so mirror that structure.
    role_yaml_dir = tmp_path / "org" / "roles"
    role_yaml_dir.mkdir(parents=True, exist_ok=True)
    (role_yaml_dir / "test_role.yaml").write_text(
        """
schema_version: 1
role_id: test_role
agent_utilization:
  daily_cap_seconds: 600
  daily_cap_output_tokens: 1000
  daily_cap_turn_count: 5
  session_cap_seconds: 120
  absolute_ceiling_seconds: 3600
  warn_threshold_frac: 0.5
""", encoding="utf-8"
    )
    # Point _role_caps at the temp roles/ dir via cwd swap
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        from src.ztare.supervisor.agent_utilization_tracker import _role_caps
        caps = _role_caps("test_role")
        assert caps.daily_duration_seconds == 600.0
        assert caps.daily_output_tokens == 1000
        assert caps.daily_turn_count == 5
        assert caps.session_duration_seconds == 120.0
        assert caps.absolute_duration_seconds == 3600.0
        assert caps.warn_threshold_frac == 0.5
    finally:
        os.chdir(cwd)


def test_no_role_id_returns_default_caps(monkeypatch, tmp_path):
    _force_root(monkeypatch, tmp_path)
    from src.ztare.supervisor.agent_utilization_tracker import _role_caps
    caps = _role_caps(None)
    assert caps.daily_duration_seconds == 3 * 3600
    assert caps.daily_output_tokens == 500_000
