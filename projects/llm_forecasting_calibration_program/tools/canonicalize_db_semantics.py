#!/usr/bin/env python3
"""Canonicalize semantic labels in forecaster_calibration.db.

This is intentionally narrow: it fixes labels, not measurements. Raw JSON,
contract rows, probabilities, and outcomes are left untouched.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
DB = REPO / "analytics/public/calibration/forecaster_calibration.db"

FAMILY_ALIASES = {
    "codex_mini": "codex_54mini",
}

PRIMITIVE_BASE_BY_PILOT = {
    "v28_novel_bias_smokes_n42_diversified": "novel_bias_smoke",
    "v28_novel_bias_smokes_n30": "novel_bias_smoke",
    "f104_freq_inheritance_DI_panel_n15": "freq_inheritance",
    "f104_freq_inheritance_n15": "freq_inheritance",
}


def run(*, dry_run: bool) -> dict:
    con = sqlite3.connect(DB)
    changes: list[dict] = []
    for old, new in FAMILY_ALIASES.items():
        n = con.execute("SELECT COUNT(*) FROM pilot_calls WHERE family = ?", (old,)).fetchone()[0]
        changes.append({"kind": "family", "from": old, "to": new, "rows": n})
        if not dry_run and n:
            con.execute("UPDATE pilot_calls SET family = ? WHERE family = ?", (new, old))
    for pilot_id, primitive_base in PRIMITIVE_BASE_BY_PILOT.items():
        n = con.execute(
            """
            SELECT COUNT(*)
            FROM pilot_calls
            WHERE pilot_id = ? AND COALESCE(primitive_base, '') != ?
            """,
            (pilot_id, primitive_base),
        ).fetchone()[0]
        changes.append(
            {
                "kind": "primitive_base",
                "pilot_id": pilot_id,
                "to": primitive_base,
                "rows": n,
            }
        )
        if not dry_run and n:
            con.execute(
                "UPDATE pilot_calls SET primitive_base = ? WHERE pilot_id = ?",
                (primitive_base, pilot_id),
            )
    if not dry_run:
        con.commit()
    suspicious = con.execute(
        """
        SELECT primitive_base, COUNT(*)
        FROM pilot_calls
        WHERE LENGTH(COALESCE(primitive_base, '')) = 1
        GROUP BY primitive_base
        ORDER BY COUNT(*) DESC
        """
    ).fetchall()
    family_counts = con.execute(
        "SELECT family, COUNT(*) FROM pilot_calls GROUP BY family ORDER BY family"
    ).fetchall()
    con.close()
    return {
        "dry_run": dry_run,
        "changes": changes,
        "remaining_one_letter_primitive_base": [
            {"primitive_base": row[0], "rows": row[1]} for row in suspicious
        ],
        "family_counts": {str(row[0]): row[1] for row in family_counts},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(dry_run=args.dry_run), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

