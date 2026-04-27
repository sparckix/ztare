"""Inbox-velocity ratchet tests (GP-128 debate item 5)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.ztare.supervisor import inbox_velocity as iv


@pytest.fixture(autouse=True)
def _isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    gates_dir = tmp_path / "gates" / "pending"
    gates_dir.mkdir(parents=True)
    ledger = tmp_path / "daemon" / "inbox_velocity.jsonl"
    fp = tmp_path / "daemon" / "inbox_velocity_last_gate.txt"
    monkeypatch.setattr(iv, "GATES_DIR", gates_dir)
    monkeypatch.setattr(iv, "LEDGER_PATH", ledger)
    monkeypatch.setattr(iv, "FINGERPRINT_PATH", fp)
    yield gates_dir, ledger, fp


def _seed_gates(gates_dir: Path, n: int):
    for path in list(gates_dir.glob("*.json")):
        path.unlink()
    for i in range(n):
        (gates_dir / f"gate_{i}.json").write_text("{}", encoding="utf-8")


def test_weekly_snapshot_records_count(_isolated_paths):
    gates_dir, ledger, _ = _isolated_paths
    _seed_gates(gates_dir, 5)
    snap = iv.record_weekly_snapshot()
    assert snap["count"] == 5
    entries = [json.loads(line) for line in ledger.read_text().splitlines() if line]
    assert len(entries) == 1
    assert entries[0]["count"] == 5


def test_weekly_snapshot_is_idempotent_within_week(_isolated_paths):
    gates_dir, ledger, _ = _isolated_paths
    _seed_gates(gates_dir, 3)
    iv.record_weekly_snapshot()
    iv.record_weekly_snapshot()
    iv.record_weekly_snapshot()
    entries = [json.loads(line) for line in ledger.read_text().splitlines() if line]
    assert len(entries) == 1  # same week, one entry


def test_velocity_trend_no_gate_with_fewer_than_three_weeks(_isolated_paths):
    _, _, _ = _isolated_paths
    # Simulate two weeks of data
    base = datetime(2026, 4, 1, tzinfo=timezone.utc)
    iv.record_weekly_snapshot(when=base)
    iv.record_weekly_snapshot(when=base + timedelta(days=8))
    assert iv.check_velocity_trend() is None


def test_velocity_trend_fires_on_three_monotone(_isolated_paths):
    gates_dir, _, _ = _isolated_paths
    base = datetime(2026, 4, 1, tzinfo=timezone.utc)
    _seed_gates(gates_dir, 2)
    iv.record_weekly_snapshot(when=base)
    _seed_gates(gates_dir, 5)
    iv.record_weekly_snapshot(when=base + timedelta(days=8))
    _seed_gates(gates_dir, 9)
    iv.record_weekly_snapshot(when=base + timedelta(days=15))

    result = iv.check_velocity_trend(gate_dir=gates_dir)
    assert result is not None
    assert result.exists()
    payload = json.loads(result.read_text())
    assert payload["equivalent_gate_reason"] == "SCOPE_CONTRACTION_REQUIRED"


def test_velocity_trend_idempotent_on_same_trend(_isolated_paths):
    gates_dir, _, _ = _isolated_paths
    base = datetime(2026, 4, 1, tzinfo=timezone.utc)
    for offset, count in enumerate([2, 5, 9]):
        _seed_gates(gates_dir, count)
        iv.record_weekly_snapshot(when=base + timedelta(days=offset * 8))

    first = iv.check_velocity_trend(gate_dir=gates_dir)
    assert first is not None
    second = iv.check_velocity_trend(gate_dir=gates_dir)
    assert second is None  # same trend — no re-fire


def test_velocity_trend_no_gate_when_flat_or_down(_isolated_paths):
    gates_dir, _, _ = _isolated_paths
    base = datetime(2026, 4, 1, tzinfo=timezone.utc)
    for offset, count in enumerate([9, 5, 2]):  # decreasing
        _seed_gates(gates_dir, count)
        iv.record_weekly_snapshot(when=base + timedelta(days=offset * 8))
    assert iv.check_velocity_trend(gate_dir=gates_dir) is None
