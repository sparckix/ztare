from __future__ import annotations

import sqlite3
from pathlib import Path

from ztare.leanmill.solver import move_calibration
from ztare.leanmill.solver.governed_dag_search import MOVE_NATIVE_HAMMER


def _attempts_db(path: Path) -> None:
    with sqlite3.connect(path) as con:
        con.execute(
            """CREATE TABLE attempts (
                provider TEXT,
                error_class TEXT,
                carrier_live INTEGER,
                attempt_at TEXT,
                compile_ok INTEGER,
                ratified INTEGER,
                move TEXT,
                outcome TEXT,
                wallclock_s REAL,
                run_tag TEXT
            )"""
        )
        rows = [
            # The two admissible observations: one governed close and one miss.
            ("native_hammer", None, None, "2026-07-19T00:00:01+00:00", 1, 1,
             MOVE_NATIVE_HAMMER, "closed", 2.0, "fresh"),
            ("native_hammer", None, None, "2026-07-19T00:00:02+00:00", 0, None,
             MOVE_NATIVE_HAMMER, "failed_compile", 3.0, "fresh"),
            # Modern explicit carrier health.
            ("native_hammer", None, 0, "2026-07-19T00:00:03+00:00", 0, None,
             MOVE_NATIVE_HAMMER, "failed_compile", 5.0, "fresh"),
            # Modern typed outcome with legacy NULL health.
            ("native_hammer", None, None, "2026-07-19T00:00:04+00:00", 0, None,
             MOVE_NATIVE_HAMMER, "inadmissible_provider_dead", 7.0, "fresh"),
            # Historical positive-control failure with no typed health/error class.
            ("native_hammer", None, None, "2026-07-19T00:00:05+00:00", 0, None,
             MOVE_NATIVE_HAMMER, "harness_dead", 11.0, "fresh"),
            # Apparatus failures remain excluded through the same predicate.
            ("native_hammer", "timeout", None, "2026-07-19T00:00:06+00:00", 0, None,
             MOVE_NATIVE_HAMMER, "failed_compile", 13.0, "fresh"),
            ("native_hammer", "capability_unavailable", None,
             "2026-07-19T00:00:07+00:00", 0, None,
             MOVE_NATIVE_HAMMER, "failed_compile", 17.0, "fresh"),
        ]
        con.executemany("INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?,?,?)", rows)


def test_dead_carrier_rows_are_excluded_from_posterior_and_telemetry(
    tmp_path: Path, monkeypatch
) -> None:
    db = tmp_path / "attempts.db"
    _attempts_db(db)
    monkeypatch.delenv("ZTARE_LEANMILL_CALIBRATION_ADMISSIBLE", raising=False)
    monkeypatch.setenv("ZTARE_LEANMILL_CALIBRATION_SINCE", "2026-07-19T00:00:00+00:00")

    _cells, per_move = move_calibration._cells_from_db(db, effective=True)
    assert per_move[MOVE_NATIVE_HAMMER] == (1, 2)

    telemetry = move_calibration.exogenous_move_telemetry(
        db, run_tag="fresh", min_attempts=1
    )["by_move"][MOVE_NATIVE_HAMMER]
    assert telemetry["attempts"] == 2
    assert telemetry["useful_exits"] == 1
    assert telemetry["ratified_closes"] == 1
    assert telemetry["no_positive"] == 1
    assert telemetry["budget_s"] == 5.0
