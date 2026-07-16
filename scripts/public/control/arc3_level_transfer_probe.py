#!/usr/bin/env python3
"""Bounded ARC-AGI-3 level-boundary transfer probe.

Given a saved level-completion seed and a candidate transition model, replay the
completion sequence from reset, then test the first post-boundary transition for
each action. This spends a small, explicit number of live actions and writes a
machine-readable receipt; it does not claim a solve.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from ztare.substrates.arc_agi3 import ArcAgi3Adapter, list_games  # noqa: E402
from ztare.worldmodel.carrier_loader import load_carrier_from_source  # noqa: E402
from ztare.worldmodel.level_boundary_seed import (  # noqa: E402
    load_seed,
    seed_receipt_fields,
)


def _resolve_game_id(game: str) -> str | None:
    game = str(game or "").strip()
    if "-" in game:
        return game
    return next((g for g in list_games() if g.startswith(game)), None)


def _load_candidate(path: Path, *, project: Path):
    source = path.read_text()
    return load_carrier_from_source(
        source,
        path,
        project,
        attach_projection=False,
    )


def _grid_lists(grid) -> list[list[int]]:
    return [list(row) for row in grid]


def _diff_cells(predicted, observed) -> list[dict[str, int]]:
    out: list[dict[str, int]] = []
    for y, (ra, rb) in enumerate(zip(predicted, observed)):
        for x, (ca, cb) in enumerate(zip(ra, rb)):
            if ca != cb:
                out.append({"y": y, "x": x, "predicted": int(ca), "observed": int(cb)})
    return out


def _local_patch_witness(
    before_grid: list[list[int]],
    predicted_grid: list[list[int]],
    observed_grid: list[list[int]],
    diffs: list[dict[str, int]],
    *,
    pad: int = 2,
    max_side: int = 9,
) -> dict[str, Any]:
    if not diffs:
        return {}
    rows = [int(d["y"]) for d in diffs]
    cols = [int(d["x"]) for d in diffs]
    h = len(before_grid)
    w = len(before_grid[0]) if h else 0
    if h <= 0 or w <= 0:
        return {}
    r0 = max(0, min(rows) - max(0, pad))
    c0 = max(0, min(cols) - max(0, pad))
    r1 = min(h - 1, max(rows) + max(0, pad))
    c1 = min(w - 1, max(cols) + max(0, pad))
    if r1 - r0 + 1 > max_side or c1 - c0 + 1 > max_side:
        return {
            "schema": "ztare-local-patch-witness-v1",
            "status": "too_wide_for_single_patch",
            "bbox": [r0, c0, r1, c1],
            "diff_cells": [
                {
                    "row": int(d["y"]),
                    "col": int(d["x"]),
                    "before": int(before_grid[int(d["y"])][int(d["x"])]),
                    "predicted": int(d["predicted"]),
                    "observed": int(d["observed"]),
                }
                for d in diffs[:24]
            ],
            "before_patch": [],
            "predicted_patch": [],
            "observed_patch": [],
            "reason": "diff support exceeds max_side; use component_patch_witnesses",
        }

    def patch(grid: list[list[int]]) -> list[list[int]]:
        return [
            [int(grid[r][c]) for c in range(c0, c1 + 1)]
            for r in range(r0, r1 + 1)
        ]

    return {
        "schema": "ztare-local-patch-witness-v1",
        "bbox": [r0, c0, r1, c1],
        "diff_cells": [
            {
                "row": int(d["y"]),
                "col": int(d["x"]),
                "before": int(before_grid[int(d["y"])][int(d["x"])]),
                "predicted": int(d["predicted"]),
                "observed": int(d["observed"]),
            }
            for d in diffs[:24]
        ],
        "before_patch": patch(before_grid),
        "predicted_patch": patch(predicted_grid),
        "observed_patch": patch(observed_grid),
    }


def _diff_components(diffs: list[dict[str, int]]) -> list[list[dict[str, int]]]:
    """Return 4-neighbour components over diff-cell coordinates."""
    remaining = {
        (int(d["y"]), int(d["x"])): d
        for d in diffs
        if "y" in d and "x" in d
    }
    out: list[list[dict[str, int]]] = []
    while remaining:
        start = next(iter(remaining))
        stack = [start]
        cells: list[dict[str, int]] = []
        while stack:
            key = stack.pop()
            row = remaining.pop(key, None)
            if row is None:
                continue
            cells.append(row)
            y, x = key
            for nxt in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if nxt in remaining:
                    stack.append(nxt)
        cells.sort(key=lambda d: (int(d["y"]), int(d["x"])))
        out.append(cells)
    out.sort(key=lambda comp: (len(comp), int(comp[0]["y"]), int(comp[0]["x"])))
    return out


def _component_patch_witnesses(
    before_grid: list[list[int]],
    predicted_grid: list[list[int]],
    observed_grid: list[list[int]],
    diffs: list[dict[str, int]],
    *,
    pad: int = 2,
    max_side: int = 9,
) -> list[dict[str, Any]]:
    witnesses = []
    for comp in _diff_components(diffs):
        witness = _local_patch_witness(
            before_grid,
            predicted_grid,
            observed_grid,
            comp,
            pad=pad,
            max_side=max_side,
        )
        if witness:
            witness["component_cell_count"] = len(comp)
            witnesses.append(witness)
    return witnesses


def _boundary_residue_quotient(
    diffs_by_action: dict[int, list[dict[str, int]]],
    *,
    action_arity: int,
) -> dict[str, Any]:
    by_cell: dict[tuple[int, int], list[dict[str, int]]] = {}
    for action, diffs in diffs_by_action.items():
        for diff in diffs:
            key = (int(diff["y"]), int(diff["x"]))
            row = dict(diff)
            row["action"] = int(action)
            by_cell.setdefault(key, []).append(row)

    cells = []
    for (y, x), records in sorted(by_cell.items()):
        actions = sorted({int(r["action"]) for r in records})
        predicted = sorted({int(r["predicted"]) for r in records})
        observed = sorted({int(r["observed"]) for r in records})
        boundary = sorted({int(r["boundary"]) for r in records
                           if "boundary" in r})
        cells.append({
            "y": y,
            "x": x,
            "actions": actions,
            "predicted_values": predicted,
            "observed_values": observed,
            "boundary_values": boundary,
            "action_invariant": (
                len(actions) == int(action_arity)
                and len(predicted) == 1
                and len(observed) == 1
            ),
            "predicted_equals_boundary": (
                bool(boundary) and predicted == boundary
            ),
        })

    all_action_invariant = bool(cells) and all(c["action_invariant"] for c in cells)
    all_boundary_preserving = bool(cells) and all(c["predicted_equals_boundary"] for c in cells)
    if not cells:
        residue_class = "none"
    elif all_action_invariant and all_boundary_preserving:
        residue_class = "action_independent_boundary_update"
    elif all_action_invariant:
        residue_class = "action_independent_transition_update"
    else:
        residue_class = "action_dependent_transition_residue"
    return {
        "schema": "ztare-boundary-residue-quotient-v1",
        "residue_class": residue_class,
        "all_action_invariant": all_action_invariant,
        "all_predicted_equals_boundary": all_boundary_preserving,
        "cell_count": len(cells),
        "cells": cells,
    }


def _quotient_repair_certificate(
    diffs_by_action: dict[int, list[dict[str, int]]],
    residue_quotient: dict[str, Any],
) -> dict[str, Any]:
    """Sufficiency certificate for compact first-step residues.

    This does not adopt a model patch. It proves whether the whole bounded
    mismatch is explainable by one action-independent rewrite class over the
    quotient cells, so a later repair card has a precise target and scope.
    """
    cells = residue_quotient.get("cells") or []
    repair_map = []
    for cell in cells:
        observed = cell.get("observed_values") or []
        predicted = cell.get("predicted_values") or []
        boundary = cell.get("boundary_values") or []
        if len(observed) != 1 or len(predicted) != 1:
            continue
        repair_map.append({
            "y": int(cell["y"]),
            "x": int(cell["x"]),
            "from_predicted": int(predicted[0]),
            "from_boundary": int(boundary[0]) if len(boundary) == 1 else None,
            "to_observed": int(observed[0]),
        })
    repair_cells = {(r["y"], r["x"]) for r in repair_map}
    diff_cells = {
        (int(d["y"]), int(d["x"]))
        for diffs in diffs_by_action.values()
        for d in diffs
    }
    sufficient = (
        bool(repair_map)
        and repair_cells == diff_cells
        and bool(residue_quotient.get("all_action_invariant"))
    )
    return {
        "schema": "ztare-boundary-residue-repair-certificate-v1",
        "repair_class": (
            "action_independent_cell_rewrite"
            if sufficient else "not_compact_action_independent_rewrite"
        ),
        "sufficient_for_first_step": sufficient,
        "scope": "first post-boundary transition after the supplied completion sequence",
        "repair_map": repair_map,
        "authority": (
            "bounded sufficiency certificate only; it does not claim level solve "
            "or authorize canonical model adoption"
        ),
    }


def _remaining_after_repair(diffs: list[dict[str, int]],
                            repair_map: list[dict[str, int]]) -> int:
    repairs = {
        (int(r["y"]), int(r["x"]), int(r["from_predicted"]), int(r["to_observed"]))
        for r in repair_map
        if r.get("from_predicted") is not None and r.get("to_observed") is not None
    }
    remaining = 0
    for d in diffs:
        key = (int(d["y"]), int(d["x"]), int(d["predicted"]), int(d["observed"]))
        if key not in repairs:
            remaining += 1
    return remaining


def _local_transfer_summary(
    local_rows: list[dict[str, Any]],
    repair_certificate: dict[str, Any],
) -> dict[str, Any]:
    repair_map = repair_certificate.get("repair_map") or []
    exact = sum(1 for row in local_rows if int(row.get("wrong_cells") or 0) == 0)
    after_repair = [
        _remaining_after_repair(row.get("first_diffs") or [], repair_map)
        for row in local_rows
    ]
    exact_after_repair = sum(1 for n in after_repair if n == 0)
    first_failed = next(
        (row for row in local_rows if int(row.get("wrong_cells") or 0) != 0),
        None,
    )
    first_failed_after_repair = next(
        (row for row, n in zip(local_rows, after_repair) if n != 0),
        None,
    )
    return {
        "schema": "ztare-local-level-transfer-summary-v1",
        "steps_tested": len(local_rows),
        "exact_steps": exact,
        "exact_steps_after_first_step_repair": exact_after_repair,
        "first_failed": None if first_failed is None else {
            "initial_action": first_failed.get("initial_action"),
            "post_step": first_failed.get("post_step"),
            "action": first_failed.get("action"),
            "wrong_cells": first_failed.get("wrong_cells"),
        },
        "first_failed_after_first_step_repair": (
            None if first_failed_after_repair is None else {
                "initial_action": first_failed_after_repair.get("initial_action"),
                "post_step": first_failed_after_repair.get("post_step"),
                "action": first_failed_after_repair.get("action"),
                "wrong_cells_after_repair": after_repair[
                    local_rows.index(first_failed_after_repair)
                ],
            }
        ),
        "first_step_repair_generalizes_to_depth": (
            bool(local_rows) and exact_after_repair == len(local_rows)
        ),
    }


def _spatial_signature(cells: "set[tuple[int, int]]") -> dict[str, Any]:
    by_row: dict[int, list[int]] = {}
    by_col: dict[int, list[int]] = {}
    for y, x in cells:
        by_row.setdefault(int(y), []).append(int(x))
        by_col.setdefault(int(x), []).append(int(y))

    row_runs = []
    for y, xs0 in sorted(by_row.items()):
        xs = sorted(set(xs0))
        runs = []
        start = prev = None
        for x in xs:
            if start is None:
                start = prev = x
            elif x == prev + 1:
                prev = x
            else:
                runs.append([start, prev])
                start = prev = x
        if start is not None:
            runs.append([start, prev])
        row_runs.append({"y": y, "runs": runs})

    return {
        "rows": sorted(by_row),
        "cols": sorted(by_col),
        "row_runs": row_runs,
        "row_count": len(by_row),
        "col_count": len(by_col),
    }


def _local_refinement_hint(rec: dict[str, Any]) -> dict[str, Any] | None:
    """Map a local residue quotient class to an existing catalog primitive.

    This is deliberately only a target-selection hint. It does not rewrite the
    model; it tells the next repair worker which already-supported abstraction
    should be tried and then rerun through the probe/replay gates.
    """
    if rec.get("relation") != "underpredicted_update":
        return None
    cells = rec.get("cells") or set()
    if not cells:
        return None
    sig = _spatial_signature(cells)
    if sig["row_count"] < 1 or sig["col_count"] < 1:
        return None
    if len(rec.get("actions") or []) <= 1 or len(rec.get("post_steps") or []) <= 1:
        return None
    return {
        "schema": "ztare-local-refinement-hint-v1",
        "candidate_class": "component_scoped_extremal_count_or_rate_refinement_candidate",
        "existing_catalog_primitive": "consume_extremal.count_or_rate",
        "missing_generalization": (
            "scope extremal updates to the evidence-induced component/role, "
            "not every same-color cell in the whole grid"
        ),
        "why": (
            "the same before->observed depletion class recurs across actions "
            "and post-steps; try increasing the extremal consumption count/rate "
            "inside the selected component before broad search"
        ),
        "spatial_signature": sig,
        "authority": (
            "target-selection hint only; model adoption still requires rerun "
            "probe exactness plus normal replay/holdout gates"
        ),
    }


def _local_residue_quotient(local_rows: list[dict[str, Any]]) -> dict[str, Any]:
    classes: dict[str, dict[str, Any]] = {}
    for row in local_rows:
        for diff in row.get("first_diffs") or []:
            before = diff.get("before")
            predicted = diff.get("predicted")
            observed = diff.get("observed")
            if before == predicted and observed != predicted:
                rel = "underpredicted_update"
            elif before == observed and predicted != observed:
                rel = "overpredicted_update"
            else:
                rel = "value_mismatch"
            key = f"{rel}|before={before}|predicted={predicted}|observed={observed}"
            rec = classes.setdefault(key, {
                "relation": rel,
                "before": before,
                "predicted": predicted,
                "observed": observed,
                "occurrences": 0,
                "cells": set(),
                "post_steps": set(),
                "initial_actions": set(),
                "actions": set(),
            })
            rec["occurrences"] += 1
            rec["cells"].add((int(diff["y"]), int(diff["x"])))
            rec["post_steps"].add(int(row.get("post_step") or 0))
            rec["initial_actions"].add(int(row.get("initial_action") or 0))
            rec["actions"].add(int(row.get("action") or 0))

    out = []
    for rec in classes.values():
        cells = sorted(rec.pop("cells"))
        post_steps = sorted(rec.pop("post_steps"))
        initial_actions = sorted(rec.pop("initial_actions"))
        actions = sorted(rec.pop("actions"))
        rec_cells = set(cells)
        hint = _local_refinement_hint({**rec, "cells": rec_cells,
                                       "post_steps": post_steps, "actions": actions})
        out.append({
            **rec,
            "cell_count": len(cells),
            "coordinate_contract": {
                "cell_basis": "row_col",
                "legacy_aliases": {"y": "row", "x": "col"},
            },
            "example_cells": [
                {"row": y, "col": x, "y": y, "x": x}
                for y, x in cells[:12]
            ],
            "post_steps": post_steps,
            "initial_actions": initial_actions,
            "actions": actions,
            "initial_action_invariant": bool(initial_actions) and len(initial_actions) > 1,
            **({"refinement_hint": hint} if hint is not None else {}),
        })
    out.sort(key=lambda c: (-int(c["occurrences"]), c["relation"], str(c["before"])))
    status = (
        "none" if not out else
        "single_class_local_residue" if len(out) == 1 else
        "multi_class_local_residue"
    )
    return {
        "schema": "ztare-local-residue-quotient-v1",
        "status": status,
        "class_count": len(out),
        "total_occurrences": sum(int(c["occurrences"]) for c in out),
        "classes": out,
    }


def _state_name(adapter: ArcAgi3Adapter) -> str:
    return getattr(adapter._state, "name", str(adapter._state))


def _sequence_from_seed(seed: dict[str, Any]) -> list[int]:
    seq = seed.get("full_sequence_from_reset") or seed.get("action_sequence") or seed.get("sequence")
    if not isinstance(seq, list) or not all(isinstance(a, int) for a in seq):
        raise RuntimeError("seed must contain full_sequence_from_reset/action_sequence/sequence as a list[int]")
    return seq


def _project_from_candidate(candidate_path: Path) -> Path:
    path = candidate_path.resolve()
    for root in [path.parent, *path.parents]:
        if (root / "workspace").is_dir() and (root / "test_model.py").exists():
            return root
    for root in [path.parent, *path.parents]:
        if root.name.startswith("arc3_") and (root / "workspace").is_dir():
            return root
    return path.parent


def run_probe(
    *,
    game: str,
    seed_path: Path,
    candidate_path: Path,
    max_first_diffs: int = 12,
    post_depth: int = 1,
) -> dict[str, Any]:
    game_id = _resolve_game_id(game)
    if game_id is None:
        raise RuntimeError(f"game {game!r} not found")
    _seed, sequence, raw_seed, seed_sha256 = load_seed(seed_path)
    project = _project_from_candidate(candidate_path)
    model = _load_candidate(candidate_path, project=project)

    rows = []
    local_rows = []
    diffs_by_action: dict[int, list[dict[str, int]]] = {}
    min_wrong: int | None = None
    max_wrong = 0
    levels_after_replay: set[int] = set()
    action_arity = ArcAgi3Adapter(game_id).action_arity
    depth = max(1, int(post_depth))
    for initial_action in range(action_arity):
        adapter = ArcAgi3Adapter(game_id)
        adapter.reset()
        levels_before = int(getattr(adapter, "levels_completed", 0) or 0)
        for replay_action in sequence:
            adapter.step(replay_action)
        boundary_state = adapter.state
        boundary_t = adapter.t
        boundary_levels = int(getattr(adapter, "levels_completed", 0) or 0)
        levels_after_replay.add(boundary_levels)

        for post_step in range(1, depth + 1):
            action = (initial_action + post_step - 1) % action_arity
            before_state = adapter.state
            before_t = adapter.t
            before_levels = int(getattr(adapter, "levels_completed", 0) or 0)
            observed = adapter.step(action)
            predicted = model(_grid_lists(before_state), action, before_t)
            before_grid = _grid_lists(before_state)
            predicted_grid = _grid_lists(predicted)
            observed_grid = _grid_lists(observed)
            diffs = _diff_cells(predicted_grid, observed_grid)
            diffs_with_before = []
            for diff in diffs:
                enriched = dict(diff)
                enriched["before"] = int(before_grid[diff["y"]][diff["x"]])
                if post_step == 1:
                    enriched["boundary"] = enriched["before"]
                diffs_with_before.append(enriched)
            wrong = len(diffs)
            local_row = {
                "initial_action": initial_action,
                "post_step": post_step,
                "action": action,
                "t": before_t,
                "levels_before_action": before_levels,
                "levels_after_action": int(getattr(adapter, "levels_completed", 0) or 0),
                "state_after_action": _state_name(adapter),
                "wrong_cells": wrong,
                "first_diffs": diffs_with_before[:max_first_diffs],
                "local_patch_witness": _local_patch_witness(
                    before_grid,
                    predicted_grid,
                    observed_grid,
                    diffs,
                ),
                "component_patch_witnesses": _component_patch_witnesses(
                    before_grid,
                    predicted_grid,
                    observed_grid,
                    diffs,
                ),
            }
            local_rows.append(local_row)
            if post_step == 1:
                diffs_by_action[initial_action] = diffs_with_before
                min_wrong = wrong if min_wrong is None else min(min_wrong, wrong)
                max_wrong = max(max_wrong, wrong)
                rows.append({
                    "action": initial_action,
                    "boundary_t": boundary_t,
                    "levels_before_replay": levels_before,
                    "levels_at_boundary": boundary_levels,
                    "state_at_boundary": _state_name(adapter),
                    "levels_after_action": int(getattr(adapter, "levels_completed", 0) or 0),
                    "state_after_action": _state_name(adapter),
                    "wrong_cells": wrong,
                    "first_diffs": diffs_with_before[:max_first_diffs],
                    "local_patch_witness": local_row["local_patch_witness"],
                    "component_patch_witnesses": local_row["component_patch_witnesses"],
                })

    exact_actions = sum(1 for row in rows if row["wrong_cells"] == 0)
    residue_quotient = _boundary_residue_quotient(
        diffs_by_action, action_arity=len(rows))
    repair_certificate = _quotient_repair_certificate(diffs_by_action, residue_quotient)
    local_transfer = _local_transfer_summary(local_rows, repair_certificate)
    local_residue_quotient = _local_residue_quotient(local_rows)
    status = (
        "exact_local_transfer_depth"
        if depth > 1
        and local_transfer.get("steps_tested")
        and local_transfer.get("exact_steps") == local_transfer.get("steps_tested")
        else "exact_first_step_transfer"
        if exact_actions == len(rows)
        else "bounded_mismatch"
    )
    kernel_role_bindings = [{
        "term": "level_boundary_transfer",
        "roles": ["verification", "counterexample_routing", "model_update"],
        "source": "arc3_level_transfer_probe",
    }]
    if exact_actions != len(rows):
        kernel_role_bindings.append({
            "term": "first_step_boundary_residue",
            "roles": ["representation", "compression", "model_update"],
            "source": "arc3_level_transfer_probe",
        })
        kernel_role_bindings.append({
            "term": "boundary_residue_quotient",
            "roles": ["compression", "counterexample_routing", "selection"],
            "source": "arc3_level_transfer_probe",
        })
    return {
        "schema": "ztare-arc3-level-transfer-probe-v1",
        "game": game_id,
        **seed_receipt_fields(
            project=project,
            seed_path=seed_path,
            raw_seed=raw_seed,
            seed_sha256=seed_sha256,
        ),
        "candidate_path": str(candidate_path),
        "replay_sequence_len": len(sequence),
        "replay_reaches_level": sorted(levels_after_replay),
        "actions_tested": len(rows),
        "exact_actions": exact_actions,
        "min_wrong_cells": min_wrong if min_wrong is not None else 0,
        "max_wrong_cells": max_wrong,
        "status": status,
        "residue_quotient": residue_quotient,
        "repair_certificate": repair_certificate,
        "local_transfer": local_transfer,
        "local_residue_quotient": local_residue_quotient,
        "post_depth": depth,
        "kernel_role_bindings": kernel_role_bindings,
        "learning_pressure": (
            "closed level produced a post-boundary transition residue; feed the "
            "quotiented residue into abduction/reflex before claiming cross-level skill"
            if exact_actions != len(rows)
            else "first post-boundary transitions agree with the supplied carrier"
        ),
        "rows": rows,
        "local_rows": local_rows,
        "authority": (
            "bounded live level-boundary probe; proves only first-step transfer "
            "after the supplied completion sequence unless post_depth > 1, "
            "which additionally probes local post-boundary transitions"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", required=True)
    ap.add_argument("--seed-path", required=True)
    ap.add_argument("--candidate-path", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--no-persist", action="store_true")
    ap.add_argument("--max-first-diffs", type=int, default=12)
    ap.add_argument("--post-depth", type=int, default=1)
    args = ap.parse_args(argv)

    receipt = run_probe(
        game=args.game,
        seed_path=Path(args.seed_path),
        candidate_path=Path(args.candidate_path),
        max_first_diffs=args.max_first_diffs,
        post_depth=args.post_depth,
    )
    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if not args.no_persist:
        project = _project_from_candidate(Path(args.candidate_path))
        latest = project / "workspace" / "latest_level_transfer_probe.json"
        latest.parent.mkdir(parents=True, exist_ok=True)
        latest.write_text(text)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
