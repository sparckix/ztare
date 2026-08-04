#!/usr/bin/env python3
"""Audit generic history lifts for non-Markov partial-action evidence."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any, Callable, Hashable

from ztare.common.equivariance import stable_sha256
from ztare.worldmodel.carrier_loader import load_carrier_path
from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.gates import env_frame_indices, law_scored_view
from ztare.worldmodel.mechanism_effects import (
    fiber_mechanism_effect,
    fiber_transition_key,
)


def _last_boundary_before(boundaries: set[int], index: int) -> int:
    return max((value for value in boundaries if value < index), default=-1)


def _history_record(
    transition,
    *,
    trajectory: tuple[Any, ...],
    index: int,
    boundaries: set[int],
    evidence_ref: str,
    outcome: Hashable,
    project_state: Callable[[Any], Hashable],
) -> dict[str, Any]:
    prior_boundary = _last_boundary_before(boundaries, index)
    segment_start = prior_boundary + 1
    actions = tuple(row.a for row in trajectory)
    segment_actions = actions[segment_start:index]
    return {
        "base": (project_state(transition.s), transition.a),
        "source": transition.s,
        "operation": transition.a,
        "time": transition.t,
        "source_epoch": getattr(transition.identity, "source_epoch", None),
        "trajectory_index": index,
        "distance_since_boundary": index - segment_start,
        "actions_before": actions[:index],
        "segment_actions_before": segment_actions,
        "outcome": outcome,
        "evidence_ref": evidence_ref,
    }


def _coordinate_candidates(
    action_alphabet: tuple[Hashable, ...],
) -> list[tuple[str, int, Callable[[dict[str, Any]], Hashable]]]:
    candidates: list[
        tuple[str, int, Callable[[dict[str, Any]], Hashable]]
    ] = [
        ("source_epoch", 1, lambda row: row["source_epoch"]),
        ("time_exact", 3, lambda row: row["time"]),
        (
            "trajectory_position",
            4,
            lambda row: row["trajectory_index"],
        ),
        (
            "distance_since_boundary",
            2,
            lambda row: row["distance_since_boundary"],
        ),
        (
            "action_counts_since_boundary",
            3,
            lambda row: tuple(
                row["segment_actions_before"].count(action)
                for action in action_alphabet
            ),
        ),
        (
            "action_counts_since_trajectory_start",
            4,
            lambda row: tuple(
                row["actions_before"].count(action)
                for action in action_alphabet
            ),
        ),
    ]
    for period in range(2, 33):
        candidates.append((
            f"time_mod_{period}",
            2,
            lambda row, period=period: (
                None
                if row["time"] is None
                else int(row["time"]) % period
            ),
        ))
    for length in range(1, 17):
        candidates.append((
            f"action_suffix_{length}",
            min(6, 1 + length),
            lambda row, length=length: tuple(
                row["segment_actions_before"][-length:]
            ),
        ))
    return candidates


def _measure(
    records: tuple[dict[str, Any], ...],
    coordinate: Callable[[dict[str, Any]], Hashable],
    *,
    named_boundary: dict[str, Any],
    named_law: dict[str, Any],
) -> dict[str, Any]:
    groups: dict[Hashable, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        groups[(row["base"], coordinate(row))].append(row)
    ambiguous = [
        rows
        for rows in groups.values()
        if len({row["outcome"] for row in rows}) > 1
    ]
    return {
        "named_pair_separated": (
            coordinate(named_boundary) != coordinate(named_law)
        ),
        "group_count": len(groups),
        "ambiguous_group_count": len(ambiguous),
        "ambiguous_row_count": sum(len(rows) for rows in ambiguous),
        "largest_ambiguous_group": max(
            (len(rows) for rows in ambiguous),
            default=0,
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--trace", required=True)
    parser.add_argument("--boundary-index", required=True, type=int)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    project = Path(args.project).resolve()
    trace_path = Path(args.trace).resolve()
    trace = EpisodeLog.read_jsonl(trace_path)
    trace_rows = tuple(trace)
    boundary_index = int(args.boundary_index)
    if boundary_index < 0 or boundary_index >= len(trace_rows):
        raise SystemExit("boundary index is outside the trace")

    carrier, _kind, carrier_sha = load_carrier_path(
        project / "test_model.py",
        project_dir=project,
    )
    projection = getattr(carrier, "_ztare_factored_projection", None)
    if projection is None:
        raise SystemExit("carrier has no factored projection")

    factor_cache: dict[int, Any] = {}

    def factors(state):
        identity = id(state)
        if identity not in factor_cache:
            factor_cache[identity] = projection.factor(state)
        return factor_cache[identity]

    def project_state(state):
        return fiber_transition_key(factors(state))

    def law_outcome(transition):
        return fiber_mechanism_effect(
            factors(transition.s),
            factors(transition.s_next),
        )

    bank = EpisodeLog.read_jsonl(
        project / "raw/episodes/episode_001.jsonl"
    )
    bank_rows = tuple(bank)
    source_epoch = (
        trace_rows[0].identity.source_epoch
        if trace_rows and trace_rows[0].identity is not None
        else None
    )
    active_rows = tuple(
        law_scored_view(bank, source_epoch=source_epoch)
        if source_epoch is not None
        else law_scored_view(bank)
    )
    bank_index_by_identity = {id(row): index for index, row in enumerate(bank_rows)}
    bank_boundaries = set(env_frame_indices(bank))
    records: list[dict[str, Any]] = []
    for active_index, transition in enumerate(active_rows):
        bank_index = bank_index_by_identity.get(id(transition))
        if bank_index is None:
            bank_index = next(
                index for index, row in enumerate(bank_rows)
                if row == transition
            )
        records.append(_history_record(
            transition,
            trajectory=bank_rows,
            index=bank_index,
            boundaries=bank_boundaries,
            evidence_ref=(
                "law_scored_view(raw/episodes/episode_001.jsonl)"
                f"#{active_index}"
            ),
            outcome=law_outcome(transition),
            project_state=project_state,
        ))

    ledger_path = project / "workspace" / "sealed_eval_slices.jsonl"
    ledger_rows = [
        json.loads(line)
        for line in ledger_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    boundary_records: list[dict[str, Any]] = []
    for ledger_row in ledger_rows:
        indices = ledger_row.get("non_discharge_edge_indices")
        if not isinstance(indices, list):
            continue
        slice_path = project / str(ledger_row.get("path") or "")
        if not slice_path.is_file():
            continue
        trajectory = EpisodeLog.read_jsonl(slice_path)
        trajectory_rows = tuple(trajectory)
        declared = {
            int(index)
            for index in indices
            if isinstance(index, int)
            and not isinstance(index, bool)
            and 0 <= index < len(trajectory_rows)
        }
        for index in sorted(declared):
            transition = trajectory_rows[index]
            record = _history_record(
                transition,
                trajectory=trajectory_rows,
                index=index,
                boundaries=declared,
                evidence_ref=f"{ledger_row['path']}#{index}",
                outcome=("boundary", "control_exclusion"),
                project_state=project_state,
            )
            boundary_records.append(record)
    records.extend(boundary_records)
    record_tuple = tuple(records)

    named_ref = f"{trace_path.relative_to(project)}#{boundary_index}"
    named_boundary = next(
        row for row in boundary_records
        if row["evidence_ref"] == named_ref
    )
    law_counterparts = [
        row for row in records
        if row["evidence_ref"].startswith("law_scored_view(")
        and row["base"] == named_boundary["base"]
        and row["source"] == named_boundary["source"]
    ]
    if not law_counterparts:
        raise SystemExit("named boundary has no identical law-owned counterpart")
    named_law = min(
        law_counterparts,
        key=lambda row: (
            abs(int(row["time"] or 0) - int(named_boundary["time"] or 0)),
            row["evidence_ref"],
        ),
    )

    action_alphabet = tuple(sorted(
        {row["operation"] for row in record_tuple},
        key=repr,
    ))
    baseline = _measure(
        record_tuple,
        lambda _row: (),
        named_boundary=named_boundary,
        named_law=named_law,
    )
    measured = []
    for name, complexity, coordinate in _coordinate_candidates(action_alphabet):
        result = _measure(
            record_tuple,
            coordinate,
            named_boundary=named_boundary,
            named_law=named_law,
        )
        measured.append({
            "coordinate": name,
            "complexity": complexity,
            **result,
        })
    measured.sort(key=lambda row: (
        not row["named_pair_separated"],
        row["ambiguous_row_count"],
        row["ambiguous_group_count"],
        row["complexity"],
        row["coordinate"],
    ))

    def context(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "evidence_ref": row["evidence_ref"],
            "time": row["time"],
            "source_epoch": row["source_epoch"],
            "trajectory_index": row["trajectory_index"],
            "distance_since_boundary": row["distance_since_boundary"],
            "action_suffix_16": list(
                row["segment_actions_before"][-16:]
            ),
            "action_counts_since_boundary": dict(Counter(
                row["segment_actions_before"]
            )),
        }

    payload = {
        "schema": "ztare-history-state-audit-v1",
        "carrier_sha256": carrier_sha,
        "projection_sha256": projection.projection_sha256,
        "source_epoch": source_epoch,
        "record_count": len(record_tuple),
        "law_record_count": len(active_rows),
        "boundary_record_count": len(boundary_records),
        "action_alphabet": [repr(value) for value in action_alphabet],
        "named_boundary": context(named_boundary),
        "named_law_counterpart": context(named_law),
        "baseline": baseline,
        "candidate_rank": measured,
    }
    output = Path(args.output)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(output),
        "record_count": payload["record_count"],
        "boundary_record_count": payload["boundary_record_count"],
        "named_boundary": payload["named_boundary"],
        "named_law_counterpart": payload["named_law_counterpart"],
        "baseline": baseline,
        "top_candidates": measured[:15],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
