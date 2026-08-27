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
sys.path[:0] = [str(DIRECTORY), str(ROOT), str(ROOT / "src")]

import h125_palette_quotiented_pose_motion_affordance_audit as h125  # noqa: E402
import h127_autonomous_relational_affordance_recall_audit as h127  # noqa: E402
import h128_compiler_native_start_state_acquisition_probe as h128  # noqa: E402
from ztare.worldmodel.relational_affordance import (  # noqa: E402
    canonical_frontier_key,
    compile_relational_affordance_frontier,
    extract_relational_scene,
    transform_scene,
)
from ztare.worldmodel.relational_affordance_recall import (  # noqa: E402
    ActiveRelationalWorkingRevision,
    SettledResidualWorkingRevision,
    advance_relational_working_revision,
    compile_active_relational_working_revision,
)
import ztare.worldmodel.relational_affordance_recall as working_module  # noqa: E402


H127_RESULT = DIRECTORY / "h127_autonomous_relational_affordance_recall_result.json"
H128_RESULT = DIRECTORY / "h128_compiler_native_start_state_acquisition_result.json"
H128_AUDIT = DIRECTORY / "h128_compiler_native_start_state_acquisition_audit_result.json"
OUTPUT = DIRECTORY / "h129_recurrent_relational_working_memory_result.json"
H127_SHA256 = "9a61127622e25ad4f16fb16edffa2ccf6f8ea2f2e835dda89281d1c52422df4b"
H128_SHA256 = "8d6d47e71712d7cd1a2ddd051dc86bb54cd7f0644713c941be518e7c9447a932"
H128_AUDIT_SHA256 = "6114f5b6bd9101d86f6a9ef442d9b600fa96999eadc72430ac45485678f3b93a"
MEMORY_SHA256 = "858791e0752c25121f1f04c0c702346b91bd104a93a6e140ad2784243f0dc935"
ORACLE_ACTIONS = (0, 3, 3, 1, 3, 3, 0, 3, 3, 0)
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
    except (ValueError, RuntimeError, KeyError):
        return True
    return False


def _report(replication: int) -> dict[str, Any]:
    path = h128.OUTPUT_DIR / (
        f"replication_{replication}_compiler_native_recall_report.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def _scope(observation_sha256: str):
    return h127._scope(context_sha256=str(observation_sha256))


def _compile_initial(memory, report):
    observation = report["observations"][0]
    return compile_active_relational_working_revision(
        memory,
        target_grid=h125._grid(observation),
        observation_sha256=str(observation["sha256"]),
        scope=_scope(str(observation["sha256"])),
        remaining_budget=10,
    )


def _successful_chain(memory) -> dict[str, Any]:
    report = _report(1)
    actual = tuple(int(row["action"]) for row in report["turns"])
    if actual != ORACLE_ACTIONS or int(report["levels_gained"]) != 1:
        raise RuntimeError("H129 successful frozen treatment drifted")
    revision = _compile_initial(memory, report)
    rows = []
    nontrivial_settlements = []
    all_settlements = []
    revision_sha256s = []
    source_memory_sha256s = []
    for index, expected_action in enumerate(ORACLE_ACTIONS):
        rows.append({
            "turn": index,
            "revision_schema": revision.to_receipt()["schema"],
            "working_revision_sha256": revision.sha256,
            "observation_sha256": revision.observation_sha256,
            "remaining_budget": revision.remaining_budget,
            "selected_action": revision.selected_action,
            "expected_action": expected_action,
            "selected_direction": revision.selected_direction,
        })
        revision_sha256s.append(revision.sha256)
        source_memory_sha256s.append(revision.memory_revision.sha256)
        if revision.selected_action != expected_action:
            raise RuntimeError(f"H129 action mismatch at turn {index}")
        if index == len(ORACLE_ACTIONS) - 1:
            break
        successor = report["observations"][index + 1]
        advance = advance_relational_working_revision(
            revision,
            successor_grid=h125._grid(successor),
            successor_observation_sha256=str(successor["sha256"]),
            successor_scope=_scope(str(successor["sha256"])),
            remaining_budget=9 - index,
        )
        if advance.predecessor_revision_sha256 != revision.sha256:
            raise RuntimeError("H129 predecessor chain drifted")
        if advance.settlement is not None:
            all_settlements.append(advance.settlement)
            if advance.settlement.status != "not_tested":
                nontrivial_settlements.append(advance.settlement)
        revision = advance.revision
    if len(nontrivial_settlements) != 1:
        raise RuntimeError("H129 target settlement was not unique")
    settlement = nontrivial_settlements[0]
    if (
        settlement.status != "target_transport_refuted"
        or settlement.reason != "target absent after direct contact"
        or settlement.observed_target_entities
    ):
        raise RuntimeError("H129 target transport disposition drifted")
    return {
        "oracle_action_count": sum(
            row["selected_action"] == row["expected_action"] for row in rows
        ),
        "rows": rows,
        "working_revision_count": len(rows),
        "unique_working_revision_count": len(set(revision_sha256s)),
        "source_memory_sha256s": sorted(set(source_memory_sha256s)),
        "transition_settlement_count": len(all_settlements),
        "target_settlement_count": len(nontrivial_settlements),
        "target_settlement": settlement.to_receipt(),
        "active_revision_count": sum(
            row["revision_schema"]
            == "ztare-active-relational-working-revision-v1"
            for row in rows
        ),
        "residual_revision_count": sum(
            row["revision_schema"]
            == "ztare-settled-residual-working-revision-v1"
            for row in rows
        ),
    }


def _first_divergence(memory, replication: int) -> dict[str, Any]:
    report = _report(replication)
    revision = _compile_initial(memory, report)
    for index, turn in enumerate(report["turns"]):
        actual = int(turn["action"])
        if actual != revision.selected_action:
            return {
                "replication": replication,
                "turn": index,
                "actual_action": actual,
                "compiled_action": revision.selected_action,
                "oracle_action": ORACLE_ACTIONS[index],
                "corrects_divergence": (
                    revision.selected_action == ORACLE_ACTIONS[index]
                ),
                "revision_schema": revision.to_receipt()["schema"],
                "working_revision_sha256": revision.sha256,
            }
        if index == len(report["turns"]) - 1:
            break
        successor = report["observations"][index + 1]
        revision = advance_relational_working_revision(
            revision,
            successor_grid=h125._grid(successor),
            successor_observation_sha256=str(successor["sha256"]),
            successor_scope=_scope(str(successor["sha256"])),
            remaining_budget=9 - index,
        ).revision
    raise RuntimeError(f"H129 replication {replication} has no divergence")


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("H129 output must be new")
    for path, expected in (
        (H127_RESULT, H127_SHA256),
        (H128_RESULT, H128_SHA256),
        (H128_AUDIT, H128_AUDIT_SHA256),
    ):
        if _sha256(path) != expected:
            raise SystemExit(f"H129 frozen identity drifted: {path.name}")

    proposal, _selected, _digest = h128._compile_fresh_digest()
    memory = proposal.memory_revision
    if memory.sha256 != MEMORY_SHA256:
        raise SystemExit("H129 source memory identity drifted")

    success = _successful_chain(memory)
    divergences = [_first_divergence(memory, replication) for replication in (2, 3)]
    if [row["turn"] for row in divergences] != [6, 7]:
        raise RuntimeError("H129 frozen divergence positions drifted")

    initial_report = _report(1)
    initial_observation = initial_report["observations"][0]
    initial_grid = h125._grid(initial_observation)
    initial_revision = _compile_initial(memory, initial_report)
    palette_grid = h127._palette_variant(initial_grid)
    palette_sha256 = _canonical_sha256(palette_grid)
    palette_revision = compile_active_relational_working_revision(
        memory,
        target_grid=palette_grid,
        observation_sha256=palette_sha256,
        scope=_scope(palette_sha256),
        remaining_budget=10,
    )

    goal = working_module._goal_from_memory(memory)
    scene = extract_relational_scene(
        initial_grid,
        relation=memory.relation,
        goal=goal,
    )
    frontier = compile_relational_affordance_frontier(
        scene,
        prefix=(scene.start,),
        budget=10,
    )
    d4_rows = []
    for transform in D4_TRANSFORMS:
        transformed_scene = transform_scene(scene, transform)
        transformed = compile_relational_affordance_frontier(
            transformed_scene,
            prefix=(transformed_scene.start,),
            budget=10,
        )
        d4_rows.append({
            "transform": list(transform),
            "selected_action": transformed.selected_action,
            "frontier_sha256": canonical_frontier_key(transformed),
        })

    stale_scope_refused = _detects(lambda: (
        compile_active_relational_working_revision(
            memory,
            target_grid=initial_grid,
            observation_sha256=str(initial_observation["sha256"]),
            scope=replace(
                _scope(str(initial_observation["sha256"])),
                context_sha256="stale-observation",
            ),
            remaining_budget=10,
        )
    ))
    post_contact = _report(1)["observations"][7]
    active_after_settlement_refused = _detects(lambda: (
        compile_active_relational_working_revision(
            memory,
            target_grid=h125._grid(post_contact),
            observation_sha256=str(post_contact["sha256"]),
            scope=_scope(str(post_contact["sha256"])),
            remaining_budget=3,
        )
    ))

    source = inspect.getsource(working_module)
    source_oracle_firewall = all(
        literal not in source
        for literal in (
            "ORACLE_ACTIONS",
            "[0, 3, 3, 1, 3, 3, 0, 3, 3, 0]",
            "tu93",
            "H128",
        )
    )
    checks = {
        "successful_path_10_of_10": success["oracle_action_count"] == 10,
        "working_revision_identity_changes": (
            success["unique_working_revision_count"] == 10
        ),
        "source_memory_identity_stable": (
            success["source_memory_sha256s"] == [MEMORY_SHA256]
        ),
        "one_target_settlement": success["target_settlement_count"] == 1,
        "target_transport_refuted": (
            success["target_settlement"]["status"]
            == "target_transport_refuted"
        ),
        "target_absence_is_observed": (
            success["target_settlement"]["observed_target_entities"] == []
        ),
        "active_then_residual_types": (
            success["active_revision_count"] == 7
            and success["residual_revision_count"] == 3
        ),
        "both_failed_divergences_corrected": all(
            row["corrects_divergence"] for row in divergences
        ),
        "stale_scope_refused": stale_scope_refused,
        "active_authority_refused_after_settlement": (
            active_after_settlement_refused
        ),
        "palette_preserves_action_and_frontier": (
            palette_revision.memory_revision.sha256 == MEMORY_SHA256
            and palette_revision.selected_action
            == initial_revision.selected_action
            and palette_revision.frontier_sha256
            == initial_revision.frontier_sha256
        ),
        "d4_preserves_action_and_frontier": all(
            row["selected_action"] == initial_revision.selected_action
            and row["frontier_sha256"] == canonical_frontier_key(frontier)
            for row in d4_rows
        ),
        "source_oracle_firewall": source_oracle_firewall,
        "distinct_revision_schemas": (
            ActiveRelationalWorkingRevision.__name__
            != SettledResidualWorkingRevision.__name__
            and ActiveRelationalWorkingRevision(
                **{
                    field: getattr(initial_revision, field)
                    for field in initial_revision.__dataclass_fields__
                }
            ).to_receipt()["schema"]
            != success["rows"][7]["revision_schema"]
        ),
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    if failed:
        raise RuntimeError(f"H129 checks failed: {failed}")

    output = {
        "schema": "ztare-h129-recurrent-relational-working-memory-v1",
        "hypothesis_id": (
            "H-GPSA-RECURRENT-RELATIONAL-WORKING-MEMORY-20260808-129"
        ),
        "status": "passed_offline",
        "environment_contact": False,
        "controller_contact": False,
        "identities": {
            "h127_result_sha256": H127_SHA256,
            "h128_result_sha256": H128_SHA256,
            "h128_audit_sha256": H128_AUDIT_SHA256,
            "source_memory_sha256": MEMORY_SHA256,
        },
        "check_count": len(checks),
        "checks": checks,
        "successful_chain": success,
        "failed_path_first_divergences": divergences,
        "palette_variant": {
            "observation_sha256": palette_sha256,
            "working_revision_sha256": palette_revision.sha256,
            "frontier_sha256": palette_revision.frontier_sha256,
            "selected_action": palette_revision.selected_action,
        },
        "d4_rows": d4_rows,
        "claim_boundary": (
            "Frozen-trajectory architectural sufficiency only. Live recurrent "
            "causality, cross-game transfer, later acquisition savings, "
            "critical mass, biological fidelity, and novelty remain unsettled."
        ),
    }
    OUTPUT.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": output["status"],
        "check_count": output["check_count"],
        "oracle_action_count": success["oracle_action_count"],
        "target_settlement_count": success["target_settlement_count"],
        "active_revision_count": success["active_revision_count"],
        "residual_revision_count": success["residual_revision_count"],
        "failed_path_first_divergences": divergences,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
