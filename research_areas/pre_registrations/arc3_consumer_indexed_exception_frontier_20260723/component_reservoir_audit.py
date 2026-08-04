#!/usr/bin/env python3
"""Replay the operation-1 collision through a learned component reservoir."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ztare.common.equivariance import stable_sha256
from ztare.common.partial_action_system import (
    PartialActionObservation,
    build_partial_action_system,
)
from ztare.worldmodel.carrier_loader import load_carrier_path
from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.mechanism_effects import (
    HistoryAnnotatedState,
    fiber_mechanism_effect,
    fiber_transition_key,
    transition_boundary_kind,
)
from ztare.worldmodel.persistent_component_reservoir import (
    ReservoirWitness,
    discover_component_reservoir_coordinate,
)


def _parse_ref(project: Path, reference: str):
    path_text, separator, index_text = reference.rpartition("#")
    if not separator or not index_text.isdigit():
        raise ValueError(f"unsupported evidence ref: {reference}")
    path = project / path_text
    index = int(index_text)
    return path, index, EpisodeLog.read_jsonl_indices(path, {index})[index]


def _palette_map(observations):
    values = sorted({
        value
        for observation in observations
        for row in observation
        for value in row
    })
    return {
        value: values[-index - 1] + 100
        for index, value in enumerate(values)
    }


def _transport(observation, mapping):
    return tuple(
        tuple(mapping[value] for value in row)
        for row in observation
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--collision-audit", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    project = Path(args.project).resolve()
    collision_payload = json.loads(
        Path(args.collision_audit).read_text(encoding="utf-8")
    )
    collisions = collision_payload["mechanism_action_system"][
        "noncommuting_relations"
    ]
    if len(collisions) != 1:
        raise SystemExit("expected one surviving relation")
    collision = collisions[0]
    refs = tuple(collision["relation_evidence_refs"])
    resolved = tuple(_parse_ref(project, reference) for reference in refs)
    resolved = tuple(sorted(resolved, key=lambda row: (row[2].t, row[1])))
    source_path = resolved[0][0]
    if any(path != source_path for path, _index, _row in resolved):
        raise SystemExit("collision witnesses span multiple trajectories")
    trajectory = tuple(EpisodeLog.read_jsonl(source_path))

    carrier, _kind, _sha = load_carrier_path(
        project / "test_model.py",
        project_dir=project,
    )
    projection = getattr(carrier, "_ztare_factored_projection", None)
    if projection is None:
        raise SystemExit("carrier has no factored projection")

    witnesses = []
    witness_rows = []
    for _path, index, transition in resolved:
        boundary_kind = transition_boundary_kind(transition)
        outcome = (
            ("boundary", boundary_kind)
            if boundary_kind
            else (
                "effect",
                stable_sha256(fiber_mechanism_effect(
                    projection.factor(transition.s),
                    projection.factor(transition.s_next),
                )),
            )
        )
        witnesses.append(ReservoirWitness(
            observation=transition.s,
            outcome=outcome,
            evidence_ref=refs[len(witnesses)],
        ))
        witness_rows.append({
            "index": index,
            "time": transition.t,
            "operation": transition.a,
            "source_sha256": stable_sha256(transition.s),
            "source_factor_sha256": stable_sha256(
                fiber_transition_key(projection.factor(transition.s))
            ),
            "outcome": list(outcome),
            "boundary_kind": boundary_kind,
        })
    exceptional_outcome = next(
        witness.outcome
        for witness in witnesses
        if witness.outcome[:1] == ("boundary",)
    )
    coordinate = discover_component_reservoir_coordinate(
        witnesses,
        exceptional_outcome=exceptional_outcome,
        background_observations=tuple(row.s for row in trajectory),
        max_area=32,
    )
    if coordinate is None:
        raise SystemExit("no component reservoir separates the collision")

    def compile_collision(*, refined: bool):
        observations = []
        for position, (_path, index, transition) in enumerate(resolved):
            prior_action = (
                trajectory[index - 1].a
                if index > 0
                else None
            )
            source = HistoryAnnotatedState(
                transition.s,
                (() if prior_action is None else (prior_action,)),
            )
            successor = HistoryAnnotatedState(
                transition.s_next,
                (transition.a,),
            )
            boundary_kind = transition_boundary_kind(transition)
            observations.append(PartialActionObservation(
                source=source,
                operation=transition.a,
                successor=None if boundary_kind else successor,
                evidence_ref=refs[position],
                boundary_kind=boundary_kind,
            ))

        def project(state):
            factors = projection.factor(state.observation)
            key = (
                *fiber_transition_key(factors),
                ("action_history_suffix", state.action_history[-1:]),
            )
            if refined:
                key = (
                    *key,
                    ("component_reservoir", coordinate.project(state.observation)),
                )
            return key

        def effect(source, _operation, successor, _source_key, _target_key):
            return fiber_mechanism_effect(
                projection.factor(source.observation),
                projection.factor(successor.observation),
            )

        return build_partial_action_system(
            observations,
            project=project,
            effect=effect,
            projection_id=stable_sha256({
                "base": projection.projection_sha256,
                "reservoir": (
                    coordinate.structural_sha256 if refined else None
                ),
            }),
        )

    baseline = compile_collision(refined=False)
    refined = compile_collision(refined=True)

    palette = _palette_map(tuple(witness.observation for witness in witnesses))
    transported_witnesses = tuple(
        ReservoirWitness(
            observation=_transport(witness.observation, palette),
            outcome=witness.outcome,
            evidence_ref=witness.evidence_ref,
        )
        for witness in witnesses
    )
    transported_background = tuple(
        _transport(row.s, palette) for row in trajectory
    )
    transported = discover_component_reservoir_coordinate(
        transported_witnesses,
        exceptional_outcome=exceptional_outcome,
        background_observations=transported_background,
        max_area=32,
    )

    holdout_path = (
        project
        / "raw/episodes/eval_slices/eval_20260713T093803Z.jsonl"
    )
    holdout_indices = (14276, 14298, 14320, 14342, 14364, 14386)
    holdout_rows = EpisodeLog.read_jsonl_indices(
        holdout_path,
        set(holdout_indices),
    )
    heldout = []
    for index in holdout_indices:
        transition = holdout_rows[index]
        observed_exception = bool(transition_boundary_kind(transition))
        predicted_exception = coordinate.predicts_exception(transition.s)
        heldout.append({
            "index": index,
            "operation": transition.a,
            "count": coordinate.project(transition.s),
            "observed_exception": observed_exception,
            "predicted_exception": predicted_exception,
            "passed": observed_exception == predicted_exception,
        })

    counts_over_trajectory = tuple(
        coordinate.project(row.s) for row in trajectory
    )
    changed_cells = []
    for left_position, right_position in zip(range(len(resolved) - 1), range(1, len(resolved))):
        left = resolved[left_position][2].s
        right = resolved[right_position][2].s
        cells = [
            [row, col, left[row][col], right[row][col]]
            for row in range(len(left))
            for col in range(len(left[row]))
            if left[row][col] != right[row][col]
        ]
        changed_cells.append({
            "left_ref": refs[left_position],
            "right_ref": refs[right_position],
            "changed_cell_count": len(cells),
            "changed_cells": cells,
        })

    payload = {
        "schema": "ztare-component-reservoir-audit-v1",
        "collision": {
            "source_key_sha256": collision["source_key_sha256"],
            "operation": collision["operation"],
            "witnesses": witness_rows,
            "changed_observation_cells": changed_cells,
        },
        "coordinate": coordinate.to_receipt(),
        "trajectory_compression": {
            "observation_count": len(trajectory),
            "distinct_source_sha256_count": len({
                stable_sha256(row.s) for row in trajectory
            }),
            "distinct_reservoir_context_count": len(set(counts_over_trajectory)),
            "counts": list(counts_over_trajectory),
        },
        "palette_transport": {
            "rediscovered": transported is not None,
            "same_structural_sha256": bool(
                transported is not None
                and transported.structural_sha256
                == coordinate.structural_sha256
            ),
            "same_witness_counts": bool(
                transported is not None
                and transported.witness_counts == coordinate.witness_counts
            ),
        },
        "partial_action_refinement": {
            "baseline": baseline.to_receipt(),
            "refined": refined.to_receipt(),
            "relations_preserved": (
                baseline.observation_count == refined.observation_count
                and sum(baseline.effect_support.values())
                == sum(refined.effect_support.values())
            ),
        },
        "heldout_replay": {
            "path": str(holdout_path.relative_to(project)),
            "rows": heldout,
            "passed": all(row["passed"] for row in heldout),
        },
    }
    output = Path(args.output)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(output),
        "coordinate": coordinate.to_receipt(),
        "baseline_noncommuting": len(baseline.noncommuting_relations),
        "refined_noncommuting": len(refined.noncommuting_relations),
        "palette_transport": payload["palette_transport"],
        "heldout_passed": payload["heldout_replay"]["passed"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
