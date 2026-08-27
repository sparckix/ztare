#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Callable


DIRECTORY = Path(__file__).resolve().parent
ROOT = DIRECTORY.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from ztare.worldmodel.episode_log import EpisodeLog, Transition  # noqa: E402
from ztare.worldmodel.relational_affordance import (  # noqa: E402
    GoalPrototype,
    RelationalScene,
    canonical_frontier_key,
    compile_relational_affordance_frontier,
    discover_pose_motion_relations,
    extract_relational_scene,
    learn_goal_prototype,
    learn_pose_motion_relation,
    scan_oriented_tokens,
    transform_path,
    transform_scene,
)
from ztare.worldmodel.transition_identity import TransitionIdentity  # noqa: E402


H119_REPORT = DIRECTORY / "h119_tu93_persistent_sol_max_report.json"
H122_RESULT = DIRECTORY / "h122_pose_quotiented_mover_identity_result.json"
H124_RESULT = DIRECTORY / "h124_uncertainty_bearing_identity_replication_result.json"
H124_AUDIT = DIRECTORY / "h124_uncertainty_bearing_identity_replication_audit_result.json"
MODULE = ROOT / "src/ztare/worldmodel/relational_affordance.py"
OUTPUT = DIRECTORY / "h125_palette_quotiented_pose_motion_affordance_result.json"
H119_SHA256 = "e0482a75e6d657315e43bf5860a3c15ceec51e7fbda272593dd169529e9ed2c3"
H122_SHA256 = "60dbf8f66377625a28f08a1252c07f11f99f17673848cd16dab535ae712f0dd7"
H124_SHA256 = "86a72142e1e47f4ad521bc283b27ac95d4262b854ace8f3ac84f085522b16457"
H124_AUDIT_SHA256 = "cfde30df1e2241dc46eeefd4f9b4377df0955a9402c843645aea5e1c970841a6"
TARGET_GRID_CARRIER_SHA256 = "dde09802332964a1530f9c3b3509a3732aec0d69325f2d3af29cca5162c06b24"
D4_TRANSFORMS = (
    (False, -1, -1),
    (False, -1, 1),
    (False, 1, -1),
    (False, 1, 1),
    (True, -1, -1),
    (True, -1, 1),
    (True, 1, -1),
    (True, 1, 1),
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _grid(observation) -> tuple[tuple[int, ...], ...]:
    grid = []
    for encoded in observation["grid_rle_rows"]:
        row = []
        for run in encoded.split(","):
            value, count = (int(part) for part in run.split("x"))
            row.extend([value] * count)
        grid.append(tuple(row))
    return tuple(grid)


def _grid_carrier(observation):
    return {
        "grid_shape": observation["grid_shape"],
        "grid_rle_rows": observation["grid_rle_rows"],
    }


def _log(report, *, palette_map: Callable[[int], int] | None = None):
    palette_map = palette_map or (lambda value: value)

    def mapped(observation):
        return tuple(
            tuple(palette_map(value) for value in row)
            for row in _grid(observation)
        )

    rows = []
    for index, turn in enumerate(report["turns"][:22]):
        rows.append(Transition(
            index,
            mapped(report["observations"][index]),
            int(turn["action"]),
            mapped(report["observations"][index + 1]),
            TransitionIdentity.from_dict(turn["transition_identity"]),
        ))
    return EpisodeLog(rows)


def _move(point, direction: str, stride: int):
    dy, dx = {
        "up": (-1, 0),
        "down": (1, 0),
        "left": (0, -1),
        "right": (0, 1),
    }[direction]
    return (point[0] + dy * stride, point[1] + dx * stride)


def _prefix(scene):
    rows = [scene.start]
    for direction in ("up", "right", "right"):
        rows.append(_move(rows[-1], direction, scene.stride))
    return tuple(rows)


def _palette_grid(grid, transform: Callable[[int], int]):
    return tuple(tuple(transform(value) for value in row) for row in grid)


def _replace_marker_bearing(grid, token, bearing: str):
    mutable = [list(row) for row in grid]
    offsets = {
        "up": (0, 1),
        "down": (token.size - 1, 1),
        "left": (1, 0),
        "right": (1, token.size - 1),
        "center": (1, 1),
    }
    old_dy, old_dx = offsets[token.bearing]
    new_dy, new_dx = offsets[bearing]
    mutable[token.origin[0] + old_dy][token.origin[1] + old_dx] = (
        token.body_value
    )
    mutable[token.origin[0] + new_dy][token.origin[1] + new_dx] = (
        token.marker_value
    )
    return tuple(tuple(row) for row in mutable)


def _shift_token(grid, token, *, dy: int, dx: int, baseline: int):
    mutable = [list(row) for row in grid]
    for y in range(token.origin[0], token.origin[0] + token.size):
        for x in range(token.origin[1], token.origin[1] + token.size):
            mutable[y][x] = baseline
    marker_offset = {
        "up": (0, token.size // 2),
        "down": (token.size - 1, token.size // 2),
        "left": (token.size // 2, 0),
        "right": (token.size // 2, token.size - 1),
    }[token.bearing]
    for oy in range(token.size):
        for ox in range(token.size):
            mutable[token.origin[0] + dy + oy][token.origin[1] + dx + ox] = (
                token.marker_value
                if (oy, ox) == marker_offset
                else token.body_value
            )
    return tuple(tuple(row) for row in mutable)


def _detects(callable_: Callable[[], Any]) -> bool:
    try:
        callable_()
    except (ValueError, KeyError, RuntimeError):
        return True
    return False


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("H125 output must be new")
    for path, expected in (
        (H119_REPORT, H119_SHA256),
        (H122_RESULT, H122_SHA256),
        (H124_RESULT, H124_SHA256),
        (H124_AUDIT, H124_AUDIT_SHA256),
    ):
        if _sha256(path) != expected:
            raise SystemExit(f"H125 frozen identity drifted: {path.name}")
    report = json.loads(H119_REPORT.read_text(encoding="utf-8"))
    target_observation = report["observations"][22]
    if _canonical_sha256(
        _grid_carrier(target_observation)
    ) != TARGET_GRID_CARRIER_SHA256:
        raise SystemExit("H125 target carrier drifted")

    log = _log(report)
    relations = discover_pose_motion_relations(log)
    if len(relations) != 1:
        raise SystemExit("H125 did not discover one source relation")
    relation = relations[0]
    goal = learn_goal_prototype(
        _grid(report["observations"][21]),
        boundary_action=int(report["turns"][21]["action"]),
        relation=relation,
    )
    target_grid = _grid(target_observation)
    tokens = tuple(
        token for token in scan_oriented_tokens(
            target_grid,
            expected_size=relation.token_size,
        )
        if token.structural_key == relation.structural_key
    )
    controlled = tuple(
        token for token in tokens
        if token.palette == (
            relation.controlled_body_value,
            relation.controlled_marker_value,
        )
    )
    transported = tuple(token for token in tokens if token not in controlled)
    scene = extract_relational_scene(
        target_grid,
        relation=relation,
        goal=goal,
    )
    prefix = _prefix(scene)
    frontier = compile_relational_affordance_frontier(
        scene,
        prefix=prefix,
        budget=10,
    )
    canonical_key = canonical_frontier_key(frontier)

    d4_rows = []
    for transform in D4_TRANSFORMS:
        transformed_scene = transform_scene(scene, transform)
        transformed_prefix = transform_path(
            prefix,
            anchor=scene.start,
            transform=transform,
        )
        transformed = compile_relational_affordance_frontier(
            transformed_scene,
            prefix=transformed_prefix,
            budget=10,
        )
        d4_rows.append({
            "transform": list(transform),
            "selected_direction": transformed.selected_direction,
            "selected_action": transformed.selected_action,
            "selected_contact_kind": transformed.selected.contact_kind,
            "canonical_key": canonical_frontier_key(transformed),
        })

    palette = lambda value: int(value) + 20
    palette_report_log = _log(report, palette_map=palette)
    palette_relations = discover_pose_motion_relations(palette_report_log)
    if len(palette_relations) != 1:
        raise SystemExit("H125 palette relation discovery failed")
    palette_relation = palette_relations[0]
    palette_goal = learn_goal_prototype(
        _palette_grid(_grid(report["observations"][21]), palette),
        boundary_action=int(report["turns"][21]["action"]),
        relation=palette_relation,
    )
    palette_scene = extract_relational_scene(
        _palette_grid(target_grid, palette),
        relation=palette_relation,
        goal=palette_goal,
    )
    palette_frontier = compile_relational_affordance_frontier(
        palette_scene,
        prefix=_prefix(palette_scene),
        budget=10,
    )

    # Source-law mutation: move one post-transition marker away from the
    # witnessed displacement bearing while preserving the oriented-token type.
    first = log.transitions()[0]
    first_after = next(
        token for token in scan_oriented_tokens(
            first.s_next,
            expected_size=relation.token_size,
        )
        if token.palette == (
            relation.controlled_body_value,
            relation.controlled_marker_value,
        )
    )
    wrong_bearing = "up" if first_after.bearing != "up" else "left"
    mutated_rows = list(log.transitions())
    mutated_rows[0] = Transition(
        first.t,
        first.s,
        first.a,
        _replace_marker_bearing(first.s_next, first_after, wrong_bearing),
        first.identity,
    )
    mismatch_relation = learn_pose_motion_relation(
        mutated_rows,
        controlled_body_value=relation.controlled_body_value,
        controlled_marker_value=relation.controlled_marker_value,
        expected_size=relation.token_size,
    )

    entity = transported[0] if len(transported) == 1 else None
    if entity is None:
        raise SystemExit("H125 target transported entity is ambiguous")
    malformed_grid = _replace_marker_bearing(target_grid, entity, "center")
    shifted_grid = _shift_token(
        target_grid,
        entity,
        dy=0,
        dx=1,
        baseline=relation.node_baseline_value,
    )
    broken_edges = tuple(
        edge for edge in scene.edges
        if set(edge) != {prefix[-1], _move(prefix[-1], "down", scene.stride)}
    )
    missing_alternate_scene = RelationalScene(
        nodes=scene.nodes,
        edges=broken_edges,
        start=scene.start,
        goals=scene.goals,
        oriented_entities=scene.oriented_entities,
        stride=scene.stride,
        action_by_direction=scene.action_by_direction,
    )
    missing_alternate = compile_relational_affordance_frontier(
        missing_alternate_scene,
        prefix=prefix,
        budget=10,
    )
    target_mutation = [list(row) for row in target_grid]
    target_mutation[0][0] = int(target_mutation[0][0]) + 1
    target_mutation_sha256 = _canonical_sha256(tuple(
        tuple(row) for row in target_mutation
    ))
    target_grid_sha256 = _canonical_sha256(target_grid)
    module_text = MODULE.read_text(encoding="utf-8")

    checks = {
        "one_source_relation": len(relations) == 1,
        "source_support_21": relation.support_count == 21,
        "source_pose_motion_exact": relation.mismatch_count == 0,
        "complete_action_map": set(dict(relation.action_by_direction))
        == {"up", "down", "left", "right"},
        "learned_stride_6": relation.stride == 6,
        "learned_lattice_values_distinct": len({
            relation.node_baseline_value,
            relation.connector_value,
        }) == 2,
        "one_controlled_target_token": len(controlled) == 1,
        "one_distinct_palette_transport": len(transported) == 1
        and transported[0].palette != controlled[0].palette,
        "transported_bearing_left": transported[0].bearing == "left",
        "scene_has_unique_goal": len(scene.goals) == 1,
        "scene_has_direct_and_flank": {
            row.contact_kind for row in frontier.candidates
        } >= {"head_on", "transverse"},
        "selected_down": frontier.selected_direction == "down",
        "selected_action_1": frontier.selected_action == 1,
        "selected_transverse": frontier.selected.contact_kind == "transverse",
        "selected_budget_exact": frontier.selected.action_count == 10,
        "d4_all_commute": all(
            row["canonical_key"] == canonical_key
            and row["selected_action"] == 1
            and row["selected_contact_kind"] == "transverse"
            for row in d4_rows
        ),
        "palette_semantics_preserved": (
            palette_relation.semantic_receipt()
            == relation.semantic_receipt()
            and canonical_frontier_key(palette_frontier) == canonical_key
            and palette_frontier.selected_direction == "down"
        ),
        "source_mismatch_detected": (
            mismatch_relation.mismatch_count > 0
            and not mismatch_relation.passed
        ),
        "malformed_marker_detected": _detects(lambda: extract_relational_scene(
            malformed_grid,
            relation=relation,
            goal=goal,
        )),
        "incompatible_stride_detected": _detects(lambda: extract_relational_scene(
            shifted_grid,
            relation=relation,
            goal=goal,
        )),
        "missing_alternate_changes_decision": (
            missing_alternate.selected.contact_kind == "head_on"
            and missing_alternate.selected_direction == "right"
            and canonical_frontier_key(missing_alternate) != canonical_key
        ),
        "goal_role_mutation_detected": _detects(lambda: extract_relational_scene(
            target_grid,
            relation=relation,
            goal=GoalPrototype(
                kind=goal.kind,
                size=goal.size,
                uniform_value=goal.uniform_value + 100,
            ),
        )),
        "target_mutation_changes_identity": (
            target_mutation_sha256 != target_grid_sha256
        ),
        "target_literal_firewall": (
            "tu93" not in module_text
            and TARGET_GRID_CARRIER_SHA256 not in module_text
        ),
    }
    if not all(checks.values()):
        raise SystemExit(json.dumps({
            "failed_checks": [key for key, value in checks.items() if not value]
        }, sort_keys=True))

    output = {
        "schema": "ztare-h125-palette-quotiented-pose-motion-affordance-v1",
        "hypothesis_id": (
            "H-GPSA-PALETTE-QUOTIENTED-POSE-MOTION-AFFORDANCE-20260808-125"
        ),
        "status": "passed",
        "environment_contact": False,
        "controller_contact": False,
        "identities": {
            "h119_report_sha256": _sha256(H119_REPORT),
            "h122_result_sha256": _sha256(H122_RESULT),
            "h124_result_sha256": _sha256(H124_RESULT),
            "h124_audit_sha256": _sha256(H124_AUDIT),
            "target_grid_carrier_sha256": TARGET_GRID_CARRIER_SHA256,
            "relational_affordance_module_sha256": _sha256(MODULE),
        },
        "relation": relation.evidence_receipt(),
        "goal": goal.to_receipt(),
        "target_tokens": [token.evidence_receipt() for token in tokens],
        "scene": {
            "node_count": len(scene.nodes),
            "edge_count": len(scene.edges),
            "start": list(scene.start),
            "goals": [list(point) for point in scene.goals],
            "oriented_entities": [
                [list(origin), bearing]
                for origin, bearing in scene.oriented_entities
            ],
        },
        "frontier": frontier.to_receipt(),
        "canonical_frontier_key": canonical_key,
        "d4": {
            "transform_count": len(d4_rows),
            "rows": d4_rows,
        },
        "palette_permutation": {
            "relation_semantic_sha256": _canonical_sha256(
                palette_relation.semantic_receipt()
            ),
            "frontier_key": canonical_frontier_key(palette_frontier),
            "selected_direction": palette_frontier.selected_direction,
        },
        "mutations": {
            "source_mismatch_count": mismatch_relation.mismatch_count,
            "missing_alternate_selected_contact": (
                missing_alternate.selected.contact_kind
            ),
            "missing_alternate_selected_direction": (
                missing_alternate.selected_direction
            ),
            "target_grid_sha256": target_grid_sha256,
            "mutated_target_grid_sha256": target_mutation_sha256,
        },
        "checks": checks,
        "claim_boundary": (
            "Offline relation and decision-seam compiler only. The target "
            "entity motion, contact outcome, selected route success, controller "
            "gain, cross-game transfer, compounding, broad capability, and "
            "literature novelty remain unsettled."
        ),
    }
    OUTPUT.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": output["status"],
        "relation_support": relation.support_count,
        "relation_mismatches": relation.mismatch_count,
        "target_token_count": len(tokens),
        "candidate_count": len(frontier.candidates),
        "selected_direction": frontier.selected_direction,
        "selected_action": frontier.selected_action,
        "selected_contact_kind": frontier.selected.contact_kind,
        "selected_action_count": frontier.selected.action_count,
        "canonical_frontier_key": canonical_key,
        "d4_transform_count": len(d4_rows),
        "checks_passed": sum(checks.values()),
        "check_count": len(checks),
        "result_path": str(OUTPUT.relative_to(ROOT)),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
