#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.object_roles import induce_roles, object_signature
from ztare.worldmodel.transition_identity import TransitionIdentity


DIRECTORY = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]
REPORT = DIRECTORY / "h119_tu93_persistent_sol_max_report.json"
OBJECT_ROLES = ROOT / "src/ztare/worldmodel/object_roles.py"
RESULT = DIRECTORY / "h122_pose_quotiented_mover_identity_result.json"
H119_SHA256 = (
    "e0482a75e6d657315e43bf5860a3c15ceec51e7fbda272593dd169529e9ed2c3"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _grid(observation):
    grid = []
    for encoded in observation["grid_rle_rows"]:
        row = []
        for run in encoded.split(","):
            value, count = (int(part) for part in run.split("x"))
            row.extend([value] * count)
        grid.append(tuple(row))
    return tuple(grid)


def main() -> int:
    if _sha256(REPORT) != H119_SHA256:
        raise SystemExit("frozen H119 report identity drifted")
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    log = EpisodeLog()
    for index, turn in enumerate(report["turns"][:22]):
        log.append(
            _grid(report["observations"][index]),
            int(turn["action"]),
            _grid(report["observations"][index + 1]),
            t=index,
            identity=TransitionIdentity.from_dict(
                turn["transition_identity"]
            ),
        )
    roles = induce_roles(log, 4).roles
    mover_role = next(
        role for role in roles if role.name == "moves_under_actions"
    )
    if len(mover_role.members) != 1:
        raise SystemExit("H122 did not compile one mover identity")
    mover = mover_role.members[0]
    expected = [
        [0, -6, 0, 3],
        [1, 6, 0, 7],
        [2, 0, -6, 3],
        [3, 0, 6, 8],
    ]
    if mover["action_displacements"] != expected:
        raise SystemExit("H122 cardinal action map is incomplete or wrong")
    signature_rows = []
    for index, observation in enumerate(report["observations"][:22]):
        agent, _resource, _reactive = object_signature(
            _grid(observation), roles
        )
        member_ids = sorted({int(row[0]) for row in agent})
        signature_rows.append({
            "observation_index": index,
            "located_mover_count": len(agent),
            "member_ids": member_ids,
            "pose_ids": sorted({int(row[3]) for row in agent}),
        })
    if any(
        row["located_mover_count"] != 1 or row["member_ids"] != [0]
        for row in signature_rows
    ):
        raise SystemExit("H122 mover identity was not stable across poses")
    output = {
        "schema": "ztare-h122-pose-quotiented-mover-identity-v1",
        "hypothesis_id": (
            "H-GPSA-POSE-QUOTIENTED-MOVER-IDENTITY-20260808-122"
        ),
        "status": "passed",
        "environment_contact": False,
        "controller_contact": False,
        "identities": {
            "h119_report_sha256": _sha256(REPORT),
            "object_roles_sha256": _sha256(OBJECT_ROLES),
            "source_epoch": 0,
            "source_transition_count": 21,
        },
        "baseline": {
            "mover_identity_count": 2,
            "represented_action_indices": [1, 3],
            "identity_relation": "exact_colored_shape",
        },
        "pose_quotient": {
            "identity_relation": mover["shape_equivalence"],
            "mover_identity_count": len(mover_role.members),
            "observed_pose_count": len(mover["observed_pose_shapes"]),
            "support": int(mover["support"]),
            "action_displacements": mover["action_displacements"],
            "stable_signature_observation_count": sum(
                row["located_mover_count"] == 1
                and row["member_ids"] == [0]
                for row in signature_rows
            ),
            "signature_observation_count": len(signature_rows),
            "observed_pose_ids": sorted({
                pose
                for row in signature_rows
                for pose in row["pose_ids"]
            }),
        },
        "checks": {
            "one_mover_identity": len(mover_role.members) == 1,
            "complete_cardinal_action_map": (
                mover["action_displacements"] == expected
            ),
            "stable_member_identity_all_observations": all(
                row["located_mover_count"] == 1
                and row["member_ids"] == [0]
                for row in signature_rows
            ),
            "pose_retained_as_state": len({
                pose
                for row in signature_rows
                for pose in row["pose_ids"]
            }) == 4,
        },
        "claim_boundary": (
            "Repairs pose-invariant mover identity and action-map induction "
            "on the frozen H119 Level-1 evidence. No task-transfer or memory "
            "benefit is implied."
        ),
    }
    RESULT.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
