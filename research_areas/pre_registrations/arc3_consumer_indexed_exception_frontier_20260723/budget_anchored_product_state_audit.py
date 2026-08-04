#!/usr/bin/env python3
"""Rerun H41 with secondary depletion anchored to the primary scalar."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

import composed_world_resource_state_audit as base


def _infer_secondary_budget_anchor(
    parent: Any,
    rows: tuple[Any, ...],
) -> dict[str, Any]:
    budget_rows = sorted({
        int(row)
        for group in parent.budget_groups
        for row, _col in group
    })
    budget_cols = [
        int(col)
        for group in parent.budget_groups
        for _row, col in group
    ]
    if not budget_rows or not budget_cols:
        raise ValueError("primary budget rendering is empty")
    primary_values = {
        state[row][col]
        for transition in rows
        for state in (transition.s, transition.s_next)
        for group in parent.budget_groups
        for row, col in group
    }
    live = parent.budget_live_value
    if live not in primary_values or len(primary_values) != 2:
        raise ValueError(
            "primary scalar does not expose one unique depleted value"
        )
    background = next(value for value in primary_values if value != live)
    boundary = max(budget_cols)
    first = rows[0].s
    candidates = [
        (row, col)
        for row in budget_rows
        for col in range(boundary + 1, len(first[row]))
    ]
    values = {
        cell: {
            state[cell[0]][cell[1]]
            for transition in rows
            for state in (transition.s, transition.s_next)
        }
        for cell in candidates
    }
    cells = tuple(
        cell for cell in candidates if len(values[cell]) >= 2
    )
    if not cells:
        raise ValueError("secondary resource has no variable cells")
    invalid = {
        cell: sorted(values[cell], key=repr)
        for cell in cells
        if len(values[cell]) != 2 or background not in values[cell]
    }
    if invalid:
        raise ValueError(f"secondary cells are not depletion-binary: {invalid}")
    return {
        "budget_rows": tuple(budget_rows),
        "primary_boundary_col": boundary,
        "primary_live_value": live,
        "primary_alphabet": sorted(primary_values, key=repr),
        "background": background,
        "cells": cells,
        "cell_values": {
            repr(cell): sorted(values[cell], key=repr)
            for cell in cells
        },
        "background_authority": "unique_primary_non_live_value",
    }


def main() -> int:
    output_value = None
    for index, argument in enumerate(sys.argv):
        if argument == "--output" and index + 1 < len(sys.argv):
            output_value = sys.argv[index + 1]
            break
    if not output_value:
        raise SystemExit("--output is required")
    base._infer_secondary = _infer_secondary_budget_anchor
    status = base.main()
    output = Path(output_value)
    payload = json.loads(output.read_text(encoding="utf-8"))
    confirmed = payload["status"] == "composed_world_resource_state_confirmed"
    payload["schema"] = "ztare-budget-anchored-product-state-audit-v1"
    payload["status"] = (
        "budget_anchored_product_state_confirmed"
        if confirmed
        else "budget_anchored_product_state_refuted"
    )
    payload["parent_audit"] = "composed_world_resource_state_audit.py"
    payload["only_change"] = (
        "global_modal_background_to_unique_primary_non_live_value"
    )
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": payload["status"],
        "criteria": payload["criteria"],
        "background_authority": payload["inference"][
            "background_authority"
        ],
        "output": str(output),
    }, indent=2))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
