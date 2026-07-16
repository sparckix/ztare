"""Terminal-verifier counterexample receipts.

A terminal verifier event can certify an outcome, but reusable model knowledge
comes from the observed transition. This module builds a small normal form for
the transition mismatch so repeated failures can be deduped by behavior rather
than by coordinates or prose labels.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter

from ztare.worldmodel.grid_dsl import Grid


TERMINAL_WITNESS_KERNEL_ROLE_BINDINGS = [
    {
        "term": "terminal_witness",
        "roles": ["counterexample_routing", "representation", "model_update"],
        "evidence": (
            "normalized transition mismatch receipt routes terminal-edge "
            "counterexamples back to law refinement"
        ),
    },
    {
        "term": "translation_quotient",
        "roles": ["compression", "representation", "counterexample_routing"],
        "evidence": (
            "absolute coordinates are removed while mismatch shape/context "
            "remain available for replay-class dedupe"
        ),
    },
]


def _bbox(cells: "list[tuple[int, int]]") -> "tuple[int, int, int, int] | None":
    if not cells:
        return None
    ys = [y for y, _x in cells]
    xs = [x for _y, x in cells]
    return min(ys), min(xs), max(ys), max(xs)


def _cell(grid: Grid, y: int, x: int):
    if y < 0 or x < 0:
        return None
    try:
        return grid[y][x]
    except Exception:  # noqa: BLE001 - receipt code must not crash pursuit
        return None


def _normalized_context(state: Grid, cells: "list[tuple[int, int]]",
                        *, radius: int = 1) -> "list[tuple[int, int, int | None]]":
    box = _bbox(cells)
    if box is None:
        return []
    y0, x0, y1, x1 = box
    out = []
    for y in range(y0 - radius, y1 + radius + 1):
        for x in range(x0 - radius, x1 + radius + 1):
            out.append((y - y0, x - x0, _cell(state, y, x)))
    return out


def terminal_witness_fingerprint(*, action: int, step: int, state: Grid,
                                 predicted: "Grid | None", observed: Grid,
                                 certified_period: "int | None" = None) -> dict:
    """Return a translation-quotiented mismatch receipt plus stable sha.

    The hash includes the action, an exact step by default, normalized
    predicted/observed mismatch cells, and local pre-state context around those
    cells.  A phase quotient is admitted only with an explicit positive period
    certificate. It excludes absolute coordinates and any terminal-verifier
    vocabulary.
    """
    if certified_period is not None:
        if (
            not isinstance(certified_period, int)
            or isinstance(certified_period, bool)
            or certified_period <= 0
        ):
            raise ValueError("certified_period must be a positive integer")
        temporal_coordinate = {
            "phase": step % certified_period,
            "certified_period": certified_period,
        }
    else:
        temporal_coordinate = {"step": step}
    if predicted is None:
        payload = {
            "schema": "ztare-terminal-witness-v2",
            "kind": "prediction_none",
            "action": action,
            **temporal_coordinate,
            "kernel_role_bindings": TERMINAL_WITNESS_KERNEL_ROLE_BINDINGS,
        }
    else:
        try:
            cells = [
                (y, x)
                for y in range(len(observed))
                for x in range(len(observed[0]))
                if predicted[y][x] != observed[y][x]
            ]
        except Exception:  # noqa: BLE001
            cells = []
        box = _bbox(cells)
        if box is None:
            norm_cells = []
            context = []
        else:
            y0, x0, _y1, _x1 = box
            norm_cells = [
                (y - y0, x - x0, _cell(state, y, x),
                 _cell(predicted, y, x), _cell(observed, y, x))
                for y, x in cells
            ]
            context = _normalized_context(state, cells)
        pair_counts = Counter(
            (_cell(predicted, y, x), _cell(observed, y, x))
            for y, x in cells
        )
        payload = {
            "schema": "ztare-terminal-witness-v2",
            "kind": "grid_transition_mismatch",
            "action": action,
            **temporal_coordinate,
            "kernel_role_bindings": TERMINAL_WITNESS_KERNEL_ROLE_BINDINGS,
            "mismatch_count": len(cells),
            "shape": None if box is None else [box[2] - box[0] + 1,
                                                box[3] - box[1] + 1],
            "cells": sorted(norm_cells),
            "pre_context_r1": sorted(context),
            "pair_counts": [
                {"predicted": p, "observed": o, "count": n}
                for (p, o), n in sorted(pair_counts.items(),
                                        key=lambda item: (str(item[0][0]), str(item[0][1])))
            ],
        }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["sha256"] = hashlib.sha256(encoded).hexdigest()
    return payload
