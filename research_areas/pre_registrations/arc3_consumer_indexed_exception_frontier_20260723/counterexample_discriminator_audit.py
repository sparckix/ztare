#!/usr/bin/env python3
"""Compare a boundary/law source pair and test minimal factor refinements."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ztare.common.equivariance import stable_sha256
from ztare.common.partial_action_system import (
    PartialActionObservation,
    build_partial_action_system,
    plan_observed_action_frontier,
)
from ztare.worldmodel.carrier_loader import load_carrier_path
from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.gates import law_scored_view
from ztare.worldmodel.mechanism_effects import (
    fiber_exception_weight,
    fiber_mechanism_effect,
)


_BASE_KEY_FIELDS = (
    "controlled_base",
    "finite_configuration",
    "operation_domain_assignment",
    "ordered_feasibility_configuration",
    "ordered_budget",
    "one_shot_availability",
)


def _difference_cells(first, second) -> int:
    if (
        not isinstance(first, (tuple, list))
        or not isinstance(second, (tuple, list))
    ):
        return int(first != second)
    difference = abs(len(first) - len(second))
    for first_item, second_item in zip(first, second):
        difference += _difference_cells(first_item, second_item)
    return difference


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
    rows = tuple(trace)
    boundary_index = int(args.boundary_index)
    if boundary_index < 0 or boundary_index >= len(rows):
        raise SystemExit("boundary index is outside the trace")

    carrier, _kind, carrier_sha = load_carrier_path(
        project / "test_model.py",
        project_dir=project,
    )
    projection = getattr(carrier, "_ztare_factored_projection", None)
    if projection is None:
        raise SystemExit("carrier has no factored projection")

    boundary_source = rows[boundary_index].s
    boundary_operation = rows[boundary_index].a
    boundary_factors = projection.factor(boundary_source)
    boundary_mapping = dict(boundary_factors.as_mapping())
    boundary_base_key = tuple(
        boundary_mapping[name] for name in _BASE_KEY_FIELDS
    )

    bank = EpisodeLog.read_jsonl(
        project / "raw/episodes/episode_001.jsonl"
    )
    source_epoch = (
        rows[0].identity.source_epoch
        if rows and rows[0].identity is not None
        else None
    )
    active_rows = tuple(
        law_scored_view(bank, source_epoch=source_epoch)
        if source_epoch is not None
        else law_scored_view(bank)
    )
    law_counterparts = []
    for index, transition in enumerate(active_rows):
        if transition.a != boundary_operation:
            continue
        candidate_mapping = projection.factor(transition.s).as_mapping()
        candidate_key = tuple(
            candidate_mapping[name] for name in _BASE_KEY_FIELDS
        )
        if candidate_key != boundary_base_key:
            continue
        law_counterparts.append((
            _difference_cells(boundary_source, transition.s),
            index,
            transition,
        ))
    if not law_counterparts:
        raise SystemExit(
            "no law-owned source shares the boundary projected key/operation"
        )
    _, law_counterpart_index, law_counterpart = min(
        law_counterparts,
        key=lambda row: (row[0], row[1]),
    )
    law_source = law_counterpart.s
    law_operation = law_counterpart.a
    law_factors = projection.factor(law_source)
    law_mapping = dict(law_factors.as_mapping())
    factor_comparison = {
        name: {
            "equal": boundary_mapping[name] == law_mapping[name],
            "boundary_sha256": stable_sha256(boundary_mapping[name]),
            "law_sha256": stable_sha256(law_mapping[name]),
            "boundary": repr(boundary_mapping[name]),
            "law": repr(law_mapping[name]),
        }
        for name in boundary_mapping
    }
    differing_fields = tuple(
        name for name, row in factor_comparison.items()
        if not row["equal"]
    )
    omitted_differing_fields = tuple(
        name for name in differing_fields
        if name not in _BASE_KEY_FIELDS
    )

    observations = [
        PartialActionObservation(
            source=transition.s,
            operation=transition.a,
            successor=transition.s_next,
            evidence_ref=(
                "law_scored_view(raw/episodes/episode_001.jsonl)"
                f"#{index}"
            ),
        )
        for index, transition in enumerate(active_rows)
    ]
    observations.append(PartialActionObservation(
        source=boundary_source,
        operation=boundary_operation,
        successor=None,
        evidence_ref=(
            f"{trace_path.relative_to(project)}#{boundary_index}"
        ),
        boundary_kind="control_exclusion",
    ))

    factor_cache: dict[int, object] = {}

    def factors(state):
        identity = id(state)
        if identity not in factor_cache:
            factor_cache[identity] = projection.factor(state)
        return factor_cache[identity]

    def compile_candidate(fields: tuple[str, ...]) -> dict:
        def project(state):
            mapping = factors(state).as_mapping()
            return tuple(mapping[name] for name in fields)

        def effect(source, _operation, successor, _source_key, _target_key):
            return fiber_mechanism_effect(
                factors(source),
                factors(successor),
            )

        system = build_partial_action_system(
            observations,
            project=project,
            effect=effect,
            projection_id=stable_sha256({
                "projection_sha256": projection.projection_sha256,
                "fields": fields,
            }),
            exceptional_weight=fiber_exception_weight,
        )
        start_key = project(rows[0].s)
        frontier = plan_observed_action_frontier(
            system,
            start_key=start_key,
            operations=(0, 1, 2, 3),
            max_depth=128,
        )
        pair_key = (project(boundary_source), boundary_operation)
        return {
            "fields": list(fields),
            "pair_sources_separated": (
                project(boundary_source) != project(law_source)
            ),
            "pair_relation_noncommuting": (
                pair_key in system.noncommuting_relations
            ),
            "fiber_count": len(system.fibers),
            "relation_count": len(system.relation_effects),
            "noncommuting_relation_count": len(
                system.noncommuting_relations
            ),
            "boundary_class_count": len(system.boundary_kinds),
            "frontier": frontier.to_receipt(),
        }

    candidate_field_sets = [_BASE_KEY_FIELDS]
    candidate_field_sets.extend(
        (*_BASE_KEY_FIELDS, field)
        for field in omitted_differing_fields
    )
    if len(omitted_differing_fields) > 1:
        candidate_field_sets.append(
            (*_BASE_KEY_FIELDS, *omitted_differing_fields)
        )
    candidates = [
        compile_candidate(tuple(fields))
        for fields in dict.fromkeys(candidate_field_sets)
    ]
    payload = {
        "schema": "ztare-counterexample-discriminator-audit-v1",
        "carrier_sha256": carrier_sha,
        "projection_sha256": projection.projection_sha256,
        "trace": str(trace_path.relative_to(project)),
        "boundary_index": boundary_index,
        "boundary_operation": repr(boundary_operation),
        "law_counterpart": {
            "active_row_index": law_counterpart_index,
            "operation": repr(law_operation),
            "evidence_ref": (
                "law_scored_view(raw/episodes/episode_001.jsonl)"
                f"#{law_counterpart_index}"
            ),
            "candidate_count": len(law_counterparts),
        },
        "same_operation": boundary_operation == law_operation,
        "raw_sources_equal": boundary_source == law_source,
        "raw_source_difference_cells": _difference_cells(
            boundary_source,
            law_source,
        ),
        "factor_comparison": factor_comparison,
        "differing_fields": list(differing_fields),
        "omitted_differing_fields": list(omitted_differing_fields),
        "candidates": candidates,
    }
    output = Path(args.output)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(output),
        "same_operation": payload["same_operation"],
        "raw_source_difference_cells": payload[
            "raw_source_difference_cells"
        ],
        "differing_fields": payload["differing_fields"],
        "omitted_differing_fields": payload[
            "omitted_differing_fields"
        ],
        "candidates": candidates,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
