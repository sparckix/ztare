#!/usr/bin/env python3
"""Read-only factor-signature audit for authoritative task-boundary edges."""
from __future__ import annotations

import argparse
from itertools import combinations
import json
from pathlib import Path
from typing import Any

from ztare.common.equivariance import stable_sha256
from ztare.worldmodel.adapter import episode_log_path
from ztare.worldmodel.carrier_loader import (
    load_carrier_path,
    project_dynamics_assumption,
)
from ztare.worldmodel.episode_log import EpisodeLog


def _anchor(cells: tuple[tuple[int, int], ...]) -> tuple[int, int]:
    return (
        min((row for row, _col in cells), default=0),
        min((col for _row, col in cells), default=0),
    )


def _relative(
    cells: tuple[tuple[int, int], ...],
    anchor: tuple[int, int],
) -> tuple[tuple[int, int], ...]:
    row0, col0 = anchor
    return tuple(sorted((row - row0, col - col0) for row, col in cells))


def _features(factors: Any, intervention: Any) -> dict[str, Any]:
    base = tuple(factors.controlled_base)
    base_anchor = _anchor(base)
    base_set = set(base)
    domains = tuple(factors.operation_domain_assignment)
    nearest = []
    overlap = []
    relative_domains = []
    for identity, raw_cells in domains:
        cells = tuple(raw_cells)
        offsets = _relative(cells, base_anchor)
        relative_domains.append((identity, offsets))
        overlap.append((identity, bool(base_set.intersection(cells))))
        nearest.append((
            identity,
            min(
                offsets,
                key=lambda value: (
                    abs(value[0]) + abs(value[1]),
                    value,
                ),
                default=(0, 0),
            ),
        ))
    return {
        "intervention": intervention,
        "finite_configuration": factors.finite_configuration,
        "ordered_budget": factors.ordered_budget,
        "budget_positive": bool(factors.ordered_budget > 0),
        "one_shot_availability": factors.one_shot_availability,
        "availability_pattern": tuple(
            value for _identity, value in factors.one_shot_availability
        ),
        "ordered_feasibility_configuration": (
            factors.ordered_feasibility_configuration
        ),
        "controlled_shape": _relative(base, base_anchor),
        "operation_domain_overlap": tuple(overlap),
        "nearest_operation_domain_vectors": tuple(nearest),
        "relative_operation_domain_geometry": tuple(relative_domains),
    }


def _task_success(transition: Any) -> bool:
    identity = transition.identity
    return bool(
        identity is not None
        and identity.is_authoritative
        and identity.kind == "epoch_boundary"
        and identity.boundary_kind == "level_completed"
    )


def _task_open_comparison(
    transition: Any,
    completed_epochs: frozenset[Any],
) -> bool:
    identity = transition.identity
    return bool(
        identity is not None
        and identity.is_authoritative
        and not identity.is_boundary
        and identity.source_epoch in completed_epochs
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    project = Path(args.project).resolve()
    carrier_path = project / "test_model.py"
    carrier, _kind, carrier_sha = load_carrier_path(
        carrier_path,
        project_dir=project,
        dynamics_assumption=project_dynamics_assumption(project),
    )
    projection = getattr(carrier, "_ztare_factored_projection", None)
    if projection is None:
        raise RuntimeError("accepted carrier has no factored projection")
    log = EpisodeLog.read_jsonl(episode_log_path(project))
    positives = [
        (index, transition)
        for index, transition in enumerate(log)
        if _task_success(transition)
    ]
    completed_epochs = frozenset(
        transition.identity.source_epoch
        for _index, transition in positives
    )
    negatives = [
        (index, transition)
        for index, transition in enumerate(log)
        if _task_open_comparison(transition, completed_epochs)
    ]
    positive_features = [
        (index, transition, _features(
            projection.factor(transition.s),
            transition.a,
        ))
        for index, transition in positives
        if projection.in_domain(transition.s)
    ]
    negative_features = [
        (index, transition, _features(
            projection.factor(transition.s),
            transition.a,
        ))
        for index, transition in negatives
        if projection.in_domain(transition.s)
    ]

    feature_names = tuple(sorted(
        set.intersection(*(
            set(features)
            for _index, _transition, features in positive_features
        ))
    )) if positive_features else ()
    shared_names = tuple(
        name
        for name in feature_names
        if len({
            stable_sha256(features[name])
            for _index, _transition, features in positive_features
        }) == 1
    )
    survivors = []
    for width in range(1, len(shared_names) + 1):
        for names in combinations(shared_names, width):
            signature = tuple(
                positive_features[0][2][name] for name in names
            )
            negative_matches = [
                index
                for index, _transition, features in negative_features
                if tuple(features[name] for name in names) == signature
            ]
            if negative_matches:
                continue
            survivors.append({
                "feature_names": list(names),
                "signature": {
                    name: positive_features[0][2][name]
                    for name in names
                },
                "negative_match_count": 0,
                "leave_one_success_out": all(
                    all(
                        row_features[name]
                        == positive_features[held_out][2][name]
                        for name in names
                    )
                    for held_out in range(len(positive_features))
                    for row_index, (_row, _transition, row_features)
                    in enumerate(positive_features)
                    if row_index != held_out
                ),
            })
        if survivors:
            break

    payload = {
        "schema": "ztare-terminal-factor-transport-audit-v1",
        "carrier_sha256": carrier_sha,
        "projection_sha256": projection.projection_sha256,
        "positive_count": len(positive_features),
        "completed_epochs": sorted(
            completed_epochs,
            key=lambda value: repr(value),
        ),
        "negative_count": len(negative_features),
        "feature_names": list(feature_names),
        "shared_feature_names": list(shared_names),
        "minimal_signature_width": (
            len(survivors[0]["feature_names"]) if survivors else None
        ),
        "minimal_survivors": survivors,
        "positive_rows": [
            {
                "row_index": index,
                "source_epoch": transition.identity.source_epoch,
                "target_epoch": transition.identity.target_epoch,
                "intervention": transition.a,
                "evidence_refs": list(transition.identity.evidence_refs),
                "feature_sha256": stable_sha256(features),
                "features": features,
            }
            for index, transition, features in positive_features
        ],
        "forbidden_coordinates": [
            "raw_grid",
            "source_epoch",
            "controlled_base_absolute",
            "presentation_assignment",
        ],
    }
    output = Path(args.output)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "schema": payload["schema"],
        "positive_count": payload["positive_count"],
        "completed_epochs": payload["completed_epochs"],
        "negative_count": payload["negative_count"],
        "shared_feature_names": payload["shared_feature_names"],
        "minimal_signature_width": payload["minimal_signature_width"],
        "minimal_survivors": payload["minimal_survivors"],
        "output": str(output),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
