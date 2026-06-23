"""Autoemitter tests (GP-128 post-ship debate items 3 + 4)."""

from __future__ import annotations

import json
from pathlib import Path

from ztare.signals import autoemit, damage


def _write_meta(session_dir: Path, session_id: str, end_utc=None):
    session_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "session_id": session_id,
        "member_id": "test_member",
        "role_id": "test_role",
        "substrate": "test_substrate",
        "start_utc": "2026-04-23T12:00:00+00:00",
        "end_utc": end_utc,
        "notes": [],
    }
    (session_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def test_mandate_drift_first_call_baselines(tmp_path: Path):
    session_dir = tmp_path / "sess1"
    _write_meta(session_dir, "s1")
    mandate = tmp_path / "mandate.md"
    mandate.write_text("# mandate v1\n", encoding="utf-8")

    ok = autoemit.check_mandate_drift(
        session_dir=session_dir, mandate_path=mandate, role_id="test_role"
    )
    assert ok is True

    meta = json.loads((session_dir / "meta.json").read_text())
    assert "mandate_hash" in meta
    assert meta["mandate_hash"].startswith(("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "a", "b", "c", "d", "e", "f"))


def test_mandate_drift_second_call_unchanged(tmp_path: Path):
    session_dir = tmp_path / "sess2"
    _write_meta(session_dir, "s2")
    mandate = tmp_path / "mandate.md"
    mandate.write_text("# mandate v1\n", encoding="utf-8")

    autoemit.check_mandate_drift(
        session_dir=session_dir, mandate_path=mandate, role_id="test_role"
    )
    ok = autoemit.check_mandate_drift(
        session_dir=session_dir, mandate_path=mandate, role_id="test_role"
    )
    assert ok is True  # no drift


def test_mandate_drift_detected_when_file_changes(tmp_path: Path):
    session_dir = tmp_path / "sess3"
    _write_meta(session_dir, "s3")
    mandate = tmp_path / "mandate.md"
    mandate.write_text("# mandate v1\n", encoding="utf-8")

    damage.clear(reason="pre-test cleanup")

    autoemit.check_mandate_drift(
        session_dir=session_dir, mandate_path=mandate, role_id="test_role"
    )
    # Now mutate the mandate
    mandate.write_text("# mandate v2 — different content\n", encoding="utf-8")

    ok = autoemit.check_mandate_drift(
        session_dir=session_dir, mandate_path=mandate, role_id="test_role"
    )
    assert ok is False  # drift detected

    # Damage signal should have fired
    sigs = damage.list_recent(limit=5)
    kinds = [s.kind for s in sigs]
    assert "mandate_drift" in kinds

    # Stored hash updated
    meta = json.loads((session_dir / "meta.json").read_text())
    assert meta.get("mandate_drift_count") == 1

    damage.clear(reason="post-test cleanup")


def test_session_id_forgery_none_is_tolerated():
    ok = autoemit.check_session_id_authenticity(
        session_id=None, context="unit test"
    )
    assert ok is True


def test_session_id_forgery_empty_is_tolerated():
    ok = autoemit.check_session_id_authenticity(
        session_id="", context="unit test"
    )
    assert ok is True


def test_session_id_forgery_unknown_id_flags_critical():
    """An id that matches no live session must fire critical signal."""
    damage.clear(reason="pre-test cleanup")

    bogus = "2099-01-01T00-00-00Z_ghost_session"
    ok = autoemit.check_session_id_authenticity(
        session_id=bogus, context="unit test forgery"
    )
    assert ok is False

    sigs = damage.list_recent(limit=5)
    forgery_sigs = [s for s in sigs if s.kind == "session_id_forgery"]
    assert len(forgery_sigs) >= 1
    assert forgery_sigs[0].severity == "critical"

    damage.clear(reason="post-test cleanup")
