#!/usr/bin/env python3
"""Read-only coverage audit over immutable candidate carrier projections."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from ztare.worldmodel.adapter import episode_log_path
from ztare.worldmodel.carrier_loader import (
    load_carrier_path,
    project_dynamics_assumption,
)
from ztare.worldmodel.episode_log import EpisodeLog


def _completion(transition: Any) -> bool:
    identity = transition.identity
    return bool(
        identity is not None
        and identity.is_authoritative
        and identity.kind == "epoch_boundary"
        and identity.boundary_kind == "level_completed"
    )


def _task_open(transition: Any, epochs: frozenset[Any]) -> bool:
    identity = transition.identity
    return bool(
        identity is not None
        and identity.is_authoritative
        and not identity.is_boundary
        and identity.source_epoch in epochs
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    project = Path(args.project).resolve()
    log = EpisodeLog.read_jsonl(episode_log_path(project))
    indexed = tuple(enumerate(log))
    completions = tuple(
        (index, transition)
        for index, transition in indexed
        if _completion(transition)
    )
    completed_epochs = frozenset(
        transition.identity.source_epoch
        for _index, transition in completions
    )
    comparison = tuple(
        (index, transition)
        for index, transition in indexed
        if _task_open(transition, completed_epochs)
    )
    epochs_of_interest = tuple(sorted(
        {*completed_epochs, 2},
        key=repr,
    ))
    state_rows = {
        epoch: tuple(
            (index, transition.s)
            for index, transition in indexed
            if transition.identity is not None
            and transition.identity.source_epoch == epoch
        )
        for epoch in epochs_of_interest
    }

    memory_path = project / "workspace" / "candidate_memory.json"
    memory = json.loads(memory_path.read_text(encoding="utf-8"))
    records = [
        row
        for row in memory.get("records") or ()
        if isinstance(row, dict)
        and float(row.get("gate_score") or 0.0) >= 1.0
        and str(row.get("submission") or "").strip()
    ]
    candidates = [(
        "current_accepted_carrier",
        project / "test_model.py",
        {
            "source_type": "current_accepted_carrier",
            "gate_score": 1.0,
        },
    )]
    seen_paths = {candidates[0][1].resolve()}
    for record in records:
        path = project / str(record["submission"])
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved in seen_paths or not resolved.is_file():
            continue
        seen_paths.add(resolved)
        candidates.append((
            str(record["submission"]),
            resolved,
            record,
        ))

    load_failures = []
    by_projection: dict[str, dict[str, Any]] = {}
    coverage_sets: dict[str, frozenset[int]] = {}
    all_states = tuple(
        (index, state, epoch)
        for epoch, rows in state_rows.items()
        for index, state in rows
    )
    for source_ref, path, record in candidates:
        try:
            carrier, _kind, carrier_sha = load_carrier_path(
                path,
                project_dir=project,
                dynamics_assumption=project_dynamics_assumption(project),
            )
            projection = getattr(
                carrier,
                "_ztare_factored_projection",
                None,
            )
            if projection is None:
                continue
            projection_id = projection.projection_sha256
            if projection_id in by_projection:
                by_projection[projection_id]["equivalent_sources"].append(
                    source_ref
                )
                continue
            covered_rows = frozenset(
                index
                for index, state, _epoch in all_states
                if projection.in_domain(state)
            )
            completion_rows = [
                index
                for index, transition in completions
                if projection.in_domain(transition.s)
            ]
            comparison_rows = [
                index
                for index, transition in comparison
                if projection.in_domain(transition.s)
            ]
            row = {
                "projection_sha256": projection_id,
                "carrier_sha256": carrier_sha,
                "source_ref": source_ref,
                "source_file_sha256": hashlib.sha256(
                    path.read_bytes()
                ).hexdigest(),
                "source_type": str(record.get("source_type") or ""),
                "gate_score": float(record.get("gate_score") or 0.0),
                "observed_at_utc": str(
                    record.get("observed_at_utc") or ""
                ),
                "equivalent_sources": [],
                "completion_rows": completion_rows,
                "completion_epochs": [
                    transition.identity.source_epoch
                    for index, transition in completions
                    if index in completion_rows
                ],
                "task_open_comparison_count": len(comparison_rows),
                "task_open_comparison_by_epoch": {
                    str(epoch): sum(
                        1
                        for index, transition in comparison
                        if (
                            index in comparison_rows
                            and transition.identity.source_epoch == epoch
                        )
                    )
                    for epoch in completed_epochs
                },
                "state_coverage_by_epoch": {
                    str(epoch): sum(
                        1 for index, _state in state_rows[epoch]
                        if index in covered_rows
                    )
                    for epoch in epochs_of_interest
                },
            }
            by_projection[projection_id] = row
            coverage_sets[projection_id] = covered_rows
        except Exception as exc:  # noqa: BLE001
            load_failures.append({
                "source_ref": source_ref,
                "error_type": type(exc).__name__,
                "error": str(exc)[:300],
            })

    overlaps = []
    projection_ids = sorted(by_projection)
    for left_index, left in enumerate(projection_ids):
        for right in projection_ids[left_index + 1:]:
            overlap = coverage_sets[left].intersection(
                coverage_sets[right]
            )
            if overlap:
                overlaps.append({
                    "left_projection_sha256": left,
                    "right_projection_sha256": right,
                    "shared_state_row_count": len(overlap),
                    "shared_state_rows": sorted(overlap)[:20],
                })
    completion_union = sorted({
        row_index
        for row in by_projection.values()
        for row_index in row["completion_rows"]
    })
    payload = {
        "schema": "ztare-carrier-atlas-coverage-audit-v1",
        "candidate_source_count": len(candidates),
        "loaded_projection_count": len(by_projection),
        "load_failures": load_failures,
        "completion_rows": [index for index, _row in completions],
        "completion_epochs": sorted(completed_epochs, key=repr),
        "completion_union_rows": completion_union,
        "completion_union_complete": (
            completion_union == [index for index, _row in completions]
        ),
        "projections": [
            by_projection[projection_id]
            for projection_id in projection_ids
        ],
        "pairwise_overlaps": overlaps,
        "pairwise_overlap_count": len(overlaps),
    }
    output = Path(args.output)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "schema": payload["schema"],
        "candidate_source_count": payload["candidate_source_count"],
        "loaded_projection_count": payload["loaded_projection_count"],
        "load_failure_count": len(load_failures),
        "completion_rows": payload["completion_rows"],
        "completion_union_rows": payload["completion_union_rows"],
        "completion_union_complete": payload[
            "completion_union_complete"
        ],
        "completion_covering_projections": [
            row
            for row in payload["projections"]
            if row["completion_rows"]
        ],
        "pairwise_overlap_count": payload["pairwise_overlap_count"],
        "output": str(output),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
