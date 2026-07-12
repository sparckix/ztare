"""Tests for ztare.common.adapter_width.

8+ tests covering:
  - ADAPTER_FIELDS registry completeness
  - declare_adapter_contract: bad status rejected
  - declare_adapter_contract: unknown field rejected
  - declare_adapter_contract: missing field rejected
  - declare_adapter_contract: abduced_validated without receipt rejected
  - width count correctness
  - history trend appends on repeated declarations
  - worldmodel declaration produces 6-or-7/7 with honest notes
  - report CLI shape (--report)
  - declare-worldmodel CLI produces JSON with width key
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ztare.common.adapter_width import (
    ADAPTER_FIELDS,
    adapter_width,
    declare_adapter_contract,
    declare_worldmodel,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CANONICAL = list(ADAPTER_FIELDS.keys())

_EXPECTED_FIELDS = {
    "variables",
    "actions",
    "success_signal",
    "reset_semantics",
    "time_structure",
    "observability",
    "verification_oracle",
}


def _all_given(supplied_by: str = "test") -> dict[str, dict]:
    """Minimal valid contract with all fields as 'given'."""
    return {
        f: {"status": "given", "supplied_by": supplied_by, "abduced_by": None, "validated_by": None}
        for f in _CANONICAL
    }


# ---------------------------------------------------------------------------
# Registry completeness
# ---------------------------------------------------------------------------


def test_registry_has_all_expected_fields() -> None:
    assert set(ADAPTER_FIELDS.keys()) == _EXPECTED_FIELDS


def test_registry_fields_have_nonempty_definitions() -> None:
    for name, defn in ADAPTER_FIELDS.items():
        assert isinstance(defn, str) and len(defn) > 10, f"Field '{name}' has no definition"


# ---------------------------------------------------------------------------
# Validation: bad inputs rejected
# ---------------------------------------------------------------------------


def test_bad_status_rejected(tmp_path: Path) -> None:
    fields = _all_given()
    fields["actions"]["status"] = "speculative"  # type: ignore[index]
    with mock.patch("ztare.common.adapter_width._LEDGER_DIR", tmp_path):
        with pytest.raises(ValueError, match="invalid status"):
            declare_adapter_contract("test_sub", fields)


def test_unknown_field_rejected(tmp_path: Path) -> None:
    fields = _all_given()
    fields["bogus_field"] = {"status": "given", "supplied_by": "x", "abduced_by": None, "validated_by": None}
    with mock.patch("ztare.common.adapter_width._LEDGER_DIR", tmp_path):
        with pytest.raises(ValueError, match="Unknown adapter fields"):
            declare_adapter_contract("test_sub", fields)


def test_missing_field_rejected(tmp_path: Path) -> None:
    fields = _all_given()
    del fields["observability"]
    with mock.patch("ztare.common.adapter_width._LEDGER_DIR", tmp_path):
        with pytest.raises(ValueError, match="Missing canonical fields"):
            declare_adapter_contract("test_sub", fields)


def test_abduced_validated_without_receipt_rejected(tmp_path: Path) -> None:
    fields = _all_given()
    fields["variables"] = {
        "status": "abduced_validated",
        "supplied_by": "x",
        "abduced_by": "organ",
        "validated_by": None,  # missing receipt
    }
    with mock.patch("ztare.common.adapter_width._LEDGER_DIR", tmp_path):
        with pytest.raises(ValueError, match="abduced_validated but lacks"):
            declare_adapter_contract("test_sub", fields)


# ---------------------------------------------------------------------------
# Width count correctness
# ---------------------------------------------------------------------------


def test_width_count_all_given(tmp_path: Path) -> None:
    with mock.patch("ztare.common.adapter_width._LEDGER_DIR", tmp_path):
        entry = declare_adapter_contract("s1", _all_given())
    assert entry["width"] == 7
    assert entry["total"] == 7


def test_width_count_with_abduced_candidate(tmp_path: Path) -> None:
    fields = _all_given()
    fields["variables"] = {
        "status": "abduced_candidate",
        "supplied_by": "hand",
        "abduced_by": "some_organ",
        "validated_by": None,
    }
    with mock.patch("ztare.common.adapter_width._LEDGER_DIR", tmp_path):
        entry = declare_adapter_contract("s2", fields)
    assert entry["width"] == 6  # variables not counted as given


def test_width_count_with_abduced_validated(tmp_path: Path) -> None:
    fields = _all_given()
    fields["variables"] = {
        "status": "abduced_validated",
        "supplied_by": "hand",
        "abduced_by": "some_organ",
        "validated_by": "receipt://v1",
    }
    with mock.patch("ztare.common.adapter_width._LEDGER_DIR", tmp_path):
        entry = declare_adapter_contract("s3", fields)
    assert entry["width"] == 6  # validated also not "given"


# ---------------------------------------------------------------------------
# History trend appends
# ---------------------------------------------------------------------------


def test_history_trend_appends(tmp_path: Path) -> None:
    with mock.patch("ztare.common.adapter_width._LEDGER_DIR", tmp_path):
        declare_adapter_contract("trend_sub", _all_given())

        fields2 = _all_given()
        fields2["variables"] = {
            "status": "abduced_candidate",
            "supplied_by": "x",
            "abduced_by": "organ",
            "validated_by": None,
        }
        declare_adapter_contract("trend_sub", fields2)

        report = adapter_width("trend_sub")

    assert report["trend"] == [7, 6], f"Unexpected trend: {report['trend']}"
    assert len(report["trend"]) == 2


# ---------------------------------------------------------------------------
# Worldmodel declaration
# ---------------------------------------------------------------------------


def test_worldmodel_declaration_width_range(tmp_path: Path) -> None:
    """Width must be 6 or 7 depending on causal_objects.jsonl presence."""
    with mock.patch("ztare.common.adapter_width._LEDGER_DIR", tmp_path):
        entry = declare_worldmodel()
    assert entry["total"] == 7
    assert entry["width"] in (6, 7), f"Expected 6 or 7, got {entry['width']}"


def test_worldmodel_all_canonical_fields_present(tmp_path: Path) -> None:
    with mock.patch("ztare.common.adapter_width._LEDGER_DIR", tmp_path):
        entry = declare_worldmodel()
    assert set(entry["fields"].keys()) == _EXPECTED_FIELDS


def test_worldmodel_reset_semantics_has_honest_note(tmp_path: Path) -> None:
    with mock.patch("ztare.common.adapter_width._LEDGER_DIR", tmp_path):
        entry = declare_worldmodel()
    note = entry["fields"]["reset_semantics"].get("note", "")
    assert "cold-review finding 6" in note or "UNTESTED" in note, (
        f"reset_semantics note missing cold-review finding 6 citation: {note!r}"
    )


# ---------------------------------------------------------------------------
# adapter_width() report shape
# ---------------------------------------------------------------------------


def test_adapter_width_report_shape(tmp_path: Path) -> None:
    with mock.patch("ztare.common.adapter_width._LEDGER_DIR", tmp_path):
        declare_adapter_contract("shape_sub", _all_given())
        report = adapter_width("shape_sub")
    assert "width" in report
    assert "total" in report
    assert "fields" in report
    assert "trend" in report
    assert isinstance(report["trend"], list)


def test_adapter_width_missing_substrate_raises(tmp_path: Path) -> None:
    with mock.patch("ztare.common.adapter_width._LEDGER_DIR", tmp_path):
        with pytest.raises(FileNotFoundError):
            adapter_width("nonexistent_substrate")


# ---------------------------------------------------------------------------
# CLI smoke tests
# ---------------------------------------------------------------------------


def test_cli_declare_worldmodel_produces_json() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ztare.common.adapter_width", "--declare-worldmodel"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parents[1]),
        env={**__import__("os").environ, "PYTHONPATH": "src"},
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert "width" in data
    assert data["total"] == 7


def test_cli_report_after_declare() -> None:
    # declare first so ledger exists, then report
    subprocess.run(
        [sys.executable, "-m", "ztare.common.adapter_width", "--declare-worldmodel"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parents[1]),
        env={**__import__("os").environ, "PYTHONPATH": "src"},
    )
    result = subprocess.run(
        [sys.executable, "-m", "ztare.common.adapter_width", "--report", "worldmodel"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parents[1]),
        env={**__import__("os").environ, "PYTHONPATH": "src"},
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert "width" in data
    assert "trend" in data
    assert isinstance(data["trend"], list) and len(data["trend"]) >= 1
