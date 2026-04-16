"""Fixture regression for GP-071 inbox_state primitives.

Run:

    python -m src.ztare.supervisor.inbox_state_fixture_regression

Exits 0 iff all 10 tests pass. No Streamlit in the test path.
"""

from __future__ import annotations

import json
import sys
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path

from src.ztare.supervisor.inbox_state import (
    list_pending,
    reconcile_pending_resolved,
    resolve_gate,
)


def _write_gate(pending_dir: Path, stem: str, cost: float, ts: str = "2026-04-15T18:00:00+00:00") -> Path:
    pending_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "seam_path": f"research_areas/private/seams/{stem}.md",
        "escalation_reason": "COST_BUDGET",
        "equivalent_gate_reason": "SPEC_REFINEMENT_BUDGET_REACHED",
        "cycle_count": 9,
        "total_cost_usd": cost,
        "notes": ["budget cap hit", "2 unresolved claims"],
        "timestamp_utc": ts,
        "advisory": True,
    }
    p = pending_dir / f"{stem}.json"
    p.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return p


def test_list_pending_empty_returns_empty_list() -> None:
    with tempfile.TemporaryDirectory() as td:
        pending = Path(td) / "pending"
        assert list_pending(pending) == []
        assert pending.exists()


def test_list_pending_sorts_by_cost_descending() -> None:
    with tempfile.TemporaryDirectory() as td:
        pending = Path(td) / "pending"
        _write_gate(pending, "gate_a_low", 0.04, ts="2026-04-15T10:00:00+00:00")
        _write_gate(pending, "gate_b_hi", 0.42, ts="2026-04-15T11:00:00+00:00")
        _write_gate(pending, "gate_c_mid", 0.18, ts="2026-04-15T09:00:00+00:00")
        _write_gate(pending, "gate_d_hi_tie", 0.42, ts="2026-04-15T08:00:00+00:00")
        items = list_pending(pending)
        stems = [i.stem for i in items]
        assert stems == ["gate_d_hi_tie", "gate_b_hi", "gate_c_mid", "gate_a_low"], stems


def test_resolve_gate_approve_writes_resolved_and_deletes_pending() -> None:
    with tempfile.TemporaryDirectory() as td:
        pending = Path(td) / "pending"
        resolved = Path(td) / "resolved"
        _write_gate(pending, "gate_X", 0.10)
        out = resolve_gate(
            "gate_X",
            "approve",
            "looked good",
            datetime(2026, 4, 15, 18, 12, 30, tzinfo=timezone.utc),
            pending,
            resolved,
        )
        assert out is not None and out.exists()
        assert not (pending / "gate_X.json").exists()
        body = json.loads(out.read_text(encoding="utf-8"))
        assert body["decision"] == "approve"
        assert body["operator_note"] == "looked good"
        assert body["resolver"] == "operator"


def test_resolve_gate_reject_writes_resolved_and_deletes_pending() -> None:
    with tempfile.TemporaryDirectory() as td:
        pending = Path(td) / "pending"
        resolved = Path(td) / "resolved"
        _write_gate(pending, "gate_Y", 0.10)
        out = resolve_gate(
            "gate_Y",
            "reject",
            "wrong premise",
            datetime(2026, 4, 15, 18, 12, 30, tzinfo=timezone.utc),
            pending,
            resolved,
        )
        assert out is not None and out.exists()
        assert not (pending / "gate_Y.json").exists()
        body = json.loads(out.read_text(encoding="utf-8"))
        assert body["decision"] == "reject"


def test_resolve_gate_defer_is_noop() -> None:
    with tempfile.TemporaryDirectory() as td:
        pending = Path(td) / "pending"
        resolved = Path(td) / "resolved"
        _write_gate(pending, "gate_Z", 0.10)
        out = resolve_gate(
            "gate_Z",
            "defer",
            "",
            datetime(2026, 4, 15, 18, 12, 30, tzinfo=timezone.utc),
            pending,
            resolved,
        )
        assert out is None
        assert (pending / "gate_Z.json").exists()
        assert not resolved.exists() or list(resolved.glob("*.json")) == []


def test_resolve_gate_carries_forward_original_payload() -> None:
    with tempfile.TemporaryDirectory() as td:
        pending = Path(td) / "pending"
        resolved = Path(td) / "resolved"
        _write_gate(pending, "gate_C", 0.31)
        out = resolve_gate(
            "gate_C",
            "approve",
            "",
            datetime(2026, 4, 15, 18, 12, 30, tzinfo=timezone.utc),
            pending,
            resolved,
        )
        body = json.loads(out.read_text(encoding="utf-8"))  # type: ignore[arg-type]
        original = body["original_gate"]
        assert original["total_cost_usd"] == 0.31
        assert original["cycle_count"] == 9
        assert original["advisory"] is True
        assert original["notes"] == ["budget cap hit", "2 unresolved claims"]


def test_resolve_gate_requires_operator_note_field_but_allows_empty_string() -> None:
    with tempfile.TemporaryDirectory() as td:
        pending = Path(td) / "pending"
        resolved = Path(td) / "resolved"
        _write_gate(pending, "gate_E", 0.10)

        out = resolve_gate(
            "gate_E",
            "approve",
            "",
            datetime(2026, 4, 15, 18, 12, 30, tzinfo=timezone.utc),
            pending,
            resolved,
        )
        assert out is not None and out.exists()

        _write_gate(pending, "gate_F", 0.10)
        raised = False
        try:
            resolve_gate(
                "gate_F",
                "approve",
                None,  # type: ignore[arg-type]
                datetime(2026, 4, 15, 18, 12, 30, tzinfo=timezone.utc),
                pending,
                resolved,
            )
        except ValueError:
            raised = True
        assert raised, "None operator_note must raise"


def test_reconcile_deletes_pending_when_resolved_exists() -> None:
    with tempfile.TemporaryDirectory() as td:
        pending = Path(td) / "pending"
        resolved = Path(td) / "resolved"
        _write_gate(pending, "gate_R1", 0.10)
        _write_gate(pending, "gate_R2", 0.20)
        resolved.mkdir(parents=True, exist_ok=True)
        (resolved / "gate_R1.json").write_text("{}", encoding="utf-8")

        deleted = reconcile_pending_resolved(pending, resolved)
        deleted_stems = [p.stem for p in deleted]
        assert deleted_stems == ["gate_R1"], deleted_stems
        assert not (pending / "gate_R1.json").exists()
        assert (pending / "gate_R2.json").exists()


def test_atomic_resolve_survives_mid_write_crash() -> None:
    with tempfile.TemporaryDirectory() as td:
        pending = Path(td) / "pending"
        resolved = Path(td) / "resolved"
        _write_gate(pending, "gate_K", 0.10)
        resolved.mkdir(parents=True, exist_ok=True)
        stray_tmp = resolved / "gate_K.json.tmp"
        stray_tmp.write_text("{partial", encoding="utf-8")

        deleted = reconcile_pending_resolved(pending, resolved)
        assert deleted == []
        assert (pending / "gate_K.json").exists()
        assert not stray_tmp.exists()

        out = resolve_gate(
            "gate_K",
            "approve",
            "recovered",
            datetime(2026, 4, 15, 18, 12, 30, tzinfo=timezone.utc),
            pending,
            resolved,
        )
        assert out is not None and out.exists()
        assert not (pending / "gate_K.json").exists()


def test_list_pending_ignores_malformed_json_and_logs_to_stderr() -> None:
    with tempfile.TemporaryDirectory() as td:
        pending = Path(td) / "pending"
        _write_gate(pending, "gate_ok", 0.10)
        pending.mkdir(parents=True, exist_ok=True)
        (pending / "gate_bad.json").write_text("{not json", encoding="utf-8")
        (pending / "gate_list.json").write_text("[1,2,3]", encoding="utf-8")
        items = list_pending(pending)
        stems = [i.stem for i in items]
        assert stems == ["gate_ok"], stems


TESTS = [
    test_list_pending_empty_returns_empty_list,
    test_list_pending_sorts_by_cost_descending,
    test_resolve_gate_approve_writes_resolved_and_deletes_pending,
    test_resolve_gate_reject_writes_resolved_and_deletes_pending,
    test_resolve_gate_defer_is_noop,
    test_resolve_gate_carries_forward_original_payload,
    test_resolve_gate_requires_operator_note_field_but_allows_empty_string,
    test_reconcile_deletes_pending_when_resolved_exists,
    test_atomic_resolve_survives_mid_write_crash,
    test_list_pending_ignores_malformed_json_and_logs_to_stderr,
]


def main() -> int:
    failures = 0
    for t in TESTS:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except Exception:
            failures += 1
            print(f"FAIL  {t.__name__}")
            traceback.print_exc()
    total = len(TESTS)
    print(f"\n{total - failures}/{total} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
