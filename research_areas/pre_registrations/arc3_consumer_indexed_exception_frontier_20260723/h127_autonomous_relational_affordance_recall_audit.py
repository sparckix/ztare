#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import replace
import hashlib
import inspect
import json
from pathlib import Path
import sys
from typing import Any, Callable


DIRECTORY = Path(__file__).resolve().parent
ROOT = DIRECTORY.parents[2]
sys.path.insert(0, str(DIRECTORY))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import h125_palette_quotiented_pose_motion_affordance_audit as h125  # noqa: E402
from ztare.common.wake_sleep_credit_router import (  # noqa: E402
    MemoryAcquisitionProvenance,
    MemoryScope,
    WakeSleepCreditState,
)
from ztare.worldmodel.episode_log import EpisodeLog, Transition  # noqa: E402
from ztare.worldmodel.relational_affordance import (  # noqa: E402
    RelationalScene,
    discover_pose_motion_relations,
    extract_relational_scene,
    learn_goal_prototype,
    scan_oriented_tokens,
    transform_scene,
)
from ztare.worldmodel.relational_affordance_recall import (  # noqa: E402
    compile_relational_affordance_recall,
    discover_relational_decision_seam,
    select_relational_affordance_recall,
)


H119_REPORT = DIRECTORY / "h119_tu93_persistent_sol_max_report.json"
H126_RESULT = DIRECTORY / "h126_relational_affordance_branch_acquisition_result.json"
H126_AUDIT = (
    DIRECTORY / "h126_relational_affordance_branch_acquisition_audit_result.json"
)
MODULE = ROOT / "src/ztare/worldmodel/relational_affordance_recall.py"
OUTPUT = DIRECTORY / "h127_autonomous_relational_affordance_recall_result.json"
H119_SHA256 = (
    "e0482a75e6d657315e43bf5860a3c15ceec51e7fbda272593dd169529e9ed2c3"
)
H126_RESULT_SHA256 = (
    "96791887bcd7b16abb89b24eec8085d08c6aca77ebc064bece10da7105257eea"
)
H126_AUDIT_SHA256 = (
    "13abfad64202814da4729797acdde765437560c03f7c95d296127135e72bfd34"
)
TARGET_OBSERVATION_SHA256 = (
    "c654ced9fcd15bcc9937e6748e64c4d55b5fe15b21547acbb982068947f7eae4"
)
TARGET_GRID_CARRIER_SHA256 = (
    "dde09802332964a1530f9c3b3509a3732aec0d69325f2d3af29cca5162c06b24"
)
SCOPE_VALUES = {
    "task_sha256": "6bdf4da8154e7633ee03143b7c3eef78e9f5ca743dc35a494e9b834cc9cb279c",
    "controller_sha256": "b2b2e90e3fa628edde404b959937d43b6f4d314b19b2cbe592aa0cc183da89fb",
    "context_sha256": TARGET_OBSERVATION_SHA256,
    "choice_set_sha256": "93526da15b2c9077798e78a874e77f8153127f29a8e0d9de1434ae4086a8981c",
    "action_vocabulary_sha256": "b067304800a27bf414739005f88c7c0e62e8f877c92982b0588c4aaa663f2770",
}
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


def _detects(callable_: Callable[[], Any]) -> bool:
    try:
        callable_()
    except (ValueError, KeyError, RuntimeError):
        return True
    return False


def _field_names(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {
            name
            for child in value.values()
            for name in _field_names(child)
        }
    if isinstance(value, list):
        return {
            name for child in value for name in _field_names(child)
        }
    return set()


def _scope(**updates: str) -> MemoryScope:
    return MemoryScope(**{**SCOPE_VALUES, **updates})


def _support(report: dict[str, Any]) -> tuple[
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
]:
    refs = tuple(f"h119:turn:{index}" for index in range(22))
    boundary_refs = (refs[-1],)
    hashes = tuple(
        _canonical_sha256({
            "source_observation_sha256": report["observations"][index]["sha256"],
            "action": int(report["turns"][index]["action"]),
            "successor_observation_sha256": report["observations"][index + 1]["sha256"],
            "transition_identity": report["turns"][index]["transition_identity"],
        })
        for index in range(22)
    )
    return refs, boundary_refs, hashes


def _compile(
    *,
    report: dict[str, Any],
    log: EpisodeLog,
    target_grid,
    target_observation_sha256: str,
    scope: MemoryScope,
    source_refs: tuple[str, ...],
    boundary_refs: tuple[str, ...],
    provenance: MemoryAcquisitionProvenance,
    budget: int = 10,
):
    return compile_relational_affordance_recall(
        log.transitions(),
        boundary_source_grid=h125._grid(report["observations"][21]),
        boundary_action=int(report["turns"][21]["action"]),
        target_grid=target_grid,
        target_observation_sha256=target_observation_sha256,
        scope=scope,
        budget=budget,
        source_support_refs=source_refs,
        boundary_support_refs=boundary_refs,
        predicted_decision_delta=2 / 3,
        retrieval_cost=0.05,
        primitive_action_cost=float(budget),
        acquisition_provenance=provenance,
    )


def _palette_variant(grid):
    remap = {8: 18, 15: 25, 14: 24}
    return tuple(
        tuple(remap.get(int(value), int(value)) for value in row)
        for row in grid
    )


def _ambiguous_goal_grid(grid, scene, goal_value, token_origins):
    adjacency = scene.adjacency()
    origin = next(
        node
        for node in scene.nodes
        if node not in set(scene.goals) | set(token_origins)
        and adjacency[node]
    )
    mutable = [list(row) for row in grid]
    for dy in range(3):
        for dx in range(3):
            mutable[origin[0] + dy][origin[1] + dx] = int(goal_value)
    return tuple(tuple(row) for row in mutable)


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("H127 output must be new")
    for path, expected in (
        (H119_REPORT, H119_SHA256),
        (H126_RESULT, H126_RESULT_SHA256),
        (H126_AUDIT, H126_AUDIT_SHA256),
    ):
        if _sha256(path) != expected:
            raise SystemExit(f"H127 frozen identity drifted: {path.name}")
    report = json.loads(H119_REPORT.read_text(encoding="utf-8"))
    target_observation = report["observations"][22]
    if str(target_observation["sha256"]) != TARGET_OBSERVATION_SHA256:
        raise SystemExit("H127 target observation identity drifted")
    if h125._canonical_sha256(
        h125._grid_carrier(target_observation)
    ) != TARGET_GRID_CARRIER_SHA256:
        raise SystemExit("H127 target grid carrier drifted")
    log = h125._log(report)
    source_refs, boundary_refs, support_hashes = _support(report)
    session_ids = sorted({
        str(turn["session_id"]) for turn in report["turns"][:22]
    })
    provenance = MemoryAcquisitionProvenance(
        episode_sha256=H119_SHA256,
        observation_sha256=str(report["observations"][21]["sha256"]),
        controller_instance_sha256=_canonical_sha256(session_ids),
        support_sha256s=support_hashes,
        boundary_support_sha256s=(support_hashes[-1],),
    )
    target_grid = h125._grid(target_observation)
    proposal = _compile(
        report=report,
        log=log,
        target_grid=target_grid,
        target_observation_sha256=TARGET_OBSERVATION_SHA256,
        scope=_scope(),
        source_refs=source_refs,
        boundary_refs=boundary_refs,
        provenance=provenance,
    )
    selected = select_relational_affordance_recall(
        proposal,
        WakeSleepCreditState(),
        consumption_scope=_scope(),
    )
    scope_drift_rows = []
    for field in SCOPE_VALUES:
        drifted_scope = _scope(**{field: f"drifted:{field}"})
        drifted = select_relational_affordance_recall(
            proposal,
            WakeSleepCreditState(),
            consumption_scope=drifted_scope,
        )
        scope_drift_rows.append({
            "field": field,
            "selected": drifted.selected,
            "candidate_count": len(drifted.recall.candidate_memory_keys),
            "selection_count": len(drifted.recall.selections),
        })

    palette_grid = _palette_variant(target_grid)
    palette_observation_sha256 = _canonical_sha256(palette_grid)
    palette_proposal = _compile(
        report=report,
        log=log,
        target_grid=palette_grid,
        target_observation_sha256=palette_observation_sha256,
        scope=_scope(context_sha256=palette_observation_sha256),
        source_refs=source_refs,
        boundary_refs=boundary_refs,
        provenance=provenance,
    )

    relation = discover_pose_motion_relations(log)[0]
    goal = learn_goal_prototype(
        h125._grid(report["observations"][21]),
        boundary_action=int(report["turns"][21]["action"]),
        relation=relation,
    )
    scene = extract_relational_scene(
        target_grid,
        relation=relation,
        goal=goal,
    )
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
    d4_rows = []
    for transform in D4_TRANSFORMS:
        transformed_scene = transform_scene(scene, transform)
        transformed_seam, _ = discover_relational_decision_seam(
            transformed_scene,
            budget=10,
        )
        d4_rows.append({
            "transform": list(transform),
            "frontier_sha256": transformed_seam.frontier_sha256,
            "selected_action": transformed_seam.selected_action,
            "selected_contact_kind": transformed_seam.selected_contact_kind,
            "memory_revision_sha256": proposal.memory_revision.sha256,
        })

    wrong_source = list(log.transitions())
    first = wrong_source[0]
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
    wrong_source[0] = Transition(
        first.t,
        first.s,
        first.a,
        h125._replace_marker_bearing(
            first.s_next,
            first_after,
            "left" if first_after.bearing != "left" else "up",
        ),
        first.identity,
    )
    malformed_grid = h125._replace_marker_bearing(
        target_grid,
        transported[0],
        "center",
    )
    ambiguous_goal_grid = _ambiguous_goal_grid(
        target_grid,
        scene,
        goal.uniform_value,
        tuple(token.origin for token in tokens),
    )
    direct_edges = tuple(
        edge for edge in scene.edges
        if all(point[0] <= scene.start[0] - scene.stride for point in edge)
        or set(edge) == {scene.start, (scene.start[0] - scene.stride, scene.start[1])}
    )
    direct_scene = RelationalScene(
        nodes=scene.nodes,
        edges=direct_edges,
        start=scene.start,
        goals=scene.goals,
        oriented_entities=scene.oriented_entities,
        stride=scene.stride,
        action_by_direction=scene.action_by_direction,
    )

    changed_scope = _scope(task_sha256="changed-task")
    changed_scope_proposal = replace(proposal, scope=changed_scope)
    changed_observation_sha256 = _canonical_sha256({
        "source": TARGET_OBSERVATION_SHA256,
        "mutation": "identity_only",
    })
    changed_observation_proposal = replace(
        proposal,
        scope=_scope(context_sha256=changed_observation_sha256),
        target_observation_sha256=changed_observation_sha256,
    )
    module_text = MODULE.read_text(encoding="utf-8")
    function_parameters = set(inspect.signature(
        compile_relational_affordance_recall
    ).parameters)
    compact_digest = json.dumps(
        selected.digest,
        sort_keys=True,
        separators=(",", ":"),
    )
    memory_receipt = proposal.memory_revision.to_receipt()
    memory_text = json.dumps(
        memory_receipt,
        sort_keys=True,
        separators=(",", ":"),
    )
    memory_fields = _field_names(memory_receipt)
    forbidden_parameters = {
        "prefix",
        "route",
        "entity_bearing",
        "entity_palette",
        "selected_action",
        "selected_direction",
    }
    checks = {
        "source_relation_support_21": (
            proposal.memory_revision.relation.support_count == 21
            and proposal.memory_revision.relation.mismatch_count == 0
        ),
        "decision_seam_approach_derived": (
            proposal.decision_seam.approach_directions
            == ("up", "right", "right")
            and proposal.decision_seam.approach_actions == (0, 3, 3)
        ),
        "decision_seam_competes": {
            branch.direction for branch in proposal.decision_seam.branches
        } == {"right", "down"},
        "decision_seam_selects_down": (
            proposal.decision_seam.selected_direction == "down"
            and proposal.decision_seam.selected_action == 1
            and proposal.decision_seam.selected_contact_kind == "transverse"
        ),
        "exact_scope_selected_once": (
            selected.selected
            and len(selected.recall.selections) == 1
            and selected.digest["selection"]["direct_injection_limit"] == 1
        ),
        "all_scope_drifts_refused": all(
            not row["selected"] and row["selection_count"] == 0
            for row in scope_drift_rows
        ),
        "source_memory_excludes_target_presentation": (
            TARGET_OBSERVATION_SHA256 not in memory_text
            and not memory_fields & {
                "target_observation_sha256",
                "controlled_body_value",
                "controlled_marker_value",
                "body_value",
                "marker_value",
                "uniform_value",
                "origin",
                "route",
            }
        ),
        "palette_target_preserves_memory": (
            palette_proposal.memory_revision.sha256
            == proposal.memory_revision.sha256
            and palette_proposal.decision_seam.frontier_sha256
            == proposal.decision_seam.frontier_sha256
            and palette_proposal.decision_seam.selected_action == 1
            and palette_proposal.sha256 != proposal.sha256
        ),
        "d4_target_preserves_memory_and_frontier": all(
            row["frontier_sha256"]
            == proposal.decision_seam.frontier_sha256
            and row["selected_action"] == 1
            and row["selected_contact_kind"] == "transverse"
            and row["memory_revision_sha256"]
            == proposal.memory_revision.sha256
            for row in d4_rows
        ),
        "observation_changes_proposal_identity": (
            changed_observation_proposal.sha256 != proposal.sha256
        ),
        "scope_changes_proposal_identity": (
            changed_scope_proposal.sha256 != proposal.sha256
        ),
        "empty_source_refused": _detects(lambda: _compile(
            report=report,
            log=EpisodeLog(),
            target_grid=target_grid,
            target_observation_sha256=TARGET_OBSERVATION_SHA256,
            scope=_scope(),
            source_refs=source_refs,
            boundary_refs=boundary_refs,
            provenance=provenance,
        )),
        "source_mismatch_refused": _detects(lambda: _compile(
            report=report,
            log=EpisodeLog(wrong_source),
            target_grid=target_grid,
            target_observation_sha256=TARGET_OBSERVATION_SHA256,
            scope=_scope(),
            source_refs=source_refs,
            boundary_refs=boundary_refs,
            provenance=provenance,
        )),
        "malformed_entity_refused": _detects(lambda: _compile(
            report=report,
            log=log,
            target_grid=malformed_grid,
            target_observation_sha256=TARGET_OBSERVATION_SHA256,
            scope=_scope(),
            source_refs=source_refs,
            boundary_refs=boundary_refs,
            provenance=provenance,
        )),
        "overbudget_safe_route_refused": _detects(lambda: _compile(
            report=report,
            log=log,
            target_grid=target_grid,
            target_observation_sha256=TARGET_OBSERVATION_SHA256,
            scope=_scope(),
            source_refs=source_refs,
            boundary_refs=boundary_refs,
            provenance=provenance,
            budget=9,
        )),
        "ambiguous_goal_refused": _detects(lambda: _compile(
            report=report,
            log=log,
            target_grid=ambiguous_goal_grid,
            target_observation_sha256=TARGET_OBSERVATION_SHA256,
            scope=_scope(),
            source_refs=source_refs,
            boundary_refs=boundary_refs,
            provenance=provenance,
        )),
        "single_route_refused": _detects(lambda: (
            discover_relational_decision_seam(direct_scene, budget=10)
        )),
        "digest_reconstructs_exactly": (
            json.loads(compact_digest) == selected.digest
        ),
        "compiler_requires_no_derived_target_arguments": not (
            function_parameters & forbidden_parameters
        ),
        "target_literal_firewall": (
            "tu93" not in module_text
            and H126_RESULT_SHA256 not in module_text
            and TARGET_GRID_CARRIER_SHA256 not in module_text
            and "(0, 3, 3)" not in module_text
        ),
        "prompt_cost_remains_unpriced": (
            proposal.to_memory_candidate().prompt_token_cost == 0
            and selected.recall.max_prompt_tokens is None
        ),
    }
    if not all(checks.values()):
        raise SystemExit(json.dumps({
            "failed_checks": [key for key, value in checks.items() if not value]
        }, sort_keys=True))
    output = {
        "schema": "ztare-h127-autonomous-relational-affordance-recall-v1",
        "hypothesis_id": (
            "H-GPSA-AUTONOMOUS-RELATIONAL-AFFORDANCE-RECALL-20260808-127"
        ),
        "status": "passed",
        "environment_contact": False,
        "controller_contact": False,
        "identities": {
            "h119_report_sha256": _sha256(H119_REPORT),
            "h126_result_sha256": _sha256(H126_RESULT),
            "h126_audit_sha256": _sha256(H126_AUDIT),
            "target_observation_sha256": TARGET_OBSERVATION_SHA256,
            "target_grid_carrier_sha256": TARGET_GRID_CARRIER_SHA256,
            "compiler_module_sha256": _sha256(MODULE),
        },
        "compiler_input_surface": sorted(function_parameters),
        "memory_revision": proposal.memory_revision.to_receipt(),
        "proposal": proposal.to_receipt(),
        "selected": selected.to_receipt(),
        "scope_drift_rows": scope_drift_rows,
        "palette_variant": {
            "target_observation_sha256": palette_observation_sha256,
            "memory_revision_sha256": palette_proposal.memory_revision.sha256,
            "proposal_sha256": palette_proposal.sha256,
            "frontier_sha256": palette_proposal.decision_seam.frontier_sha256,
        },
        "d4_rows": d4_rows,
        "mutation_receipts": {
            "changed_observation_proposal_sha256": (
                changed_observation_proposal.sha256
            ),
            "changed_scope_proposal_sha256": changed_scope_proposal.sha256,
            "ambiguous_goal_grid_sha256": _canonical_sha256(
                ambiguous_goal_grid
            ),
            "malformed_entity_grid_sha256": _canonical_sha256(malformed_grid),
        },
        "checks": checks,
        "claim_boundary": (
            "Autonomous offline proposal and exact-scope sparse selection. "
            "Controller start-state consumption, online target settlement, "
            "cross-game transfer, later acquisition catalysis, broad "
            "capability, and literature novelty remain unsettled."
        ),
    }
    OUTPUT.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": output["status"],
        "check_count": len(checks),
        "checks_passed": sum(checks.values()),
        "memory_revision_sha256": proposal.memory_revision.sha256,
        "proposal_sha256": proposal.sha256,
        "selected": selected.selected,
        "approach_directions": list(
            proposal.decision_seam.approach_directions
        ),
        "selected_direction": proposal.decision_seam.selected_direction,
        "selected_action": proposal.decision_seam.selected_action,
        "frontier_sha256": proposal.decision_seam.frontier_sha256,
        "result_path": str(OUTPUT.relative_to(ROOT)),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
