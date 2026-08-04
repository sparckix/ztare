#!/usr/bin/env python3
"""Audit terminal object/configuration/destination relations across epochs."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any

import success_predecessor_mechanism_audit as predecessor

from ztare.common.equivariance import stable_sha256
from ztare.worldmodel.carrier_loader import load_carrier_path
from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.mechanism_effects import fiber_mechanism_effect


OUTSIDE = ("structural_role", "outside")
CONTROLLED = ("structural_role", "controlled_object")


def _translation(effect: Any) -> tuple[int, int] | None:
    for item in effect if isinstance(effect, tuple) else ():
        if (
            isinstance(item, tuple)
            and item[:1] == ("controlled_base",)
            and len(item) >= 2
            and isinstance(item[1], tuple)
            and item[1][:1] == ("translate",)
            and len(item[1]) >= 3
        ):
            return int(item[1][1]), int(item[1][2])
    return None


def _operation_maps(
    boundary_rows: list[dict[str, Any]],
    *,
    projection: Any,
) -> dict[int, dict[str, Any]]:
    by_epoch: dict[int, dict[Any, Counter]] = defaultdict(
        lambda: defaultdict(Counter)
    )
    seen: dict[int, set[int]] = defaultdict(set)
    for row in boundary_rows:
        epoch = row["source_epoch"]
        for bank_index, transition in row["section"][:-1]:
            if bank_index in seen[epoch]:
                continue
            seen[epoch].add(bank_index)
            effect = fiber_mechanism_effect(
                projection.factor(transition.s),
                projection.factor(transition.s_next),
            )
            vector = _translation(effect)
            if vector is not None:
                by_epoch[epoch][transition.a][vector] += 1

    output: dict[int, dict[str, Any]] = {}
    for epoch, operations in by_epoch.items():
        operation_rows = {}
        for operation, counts in operations.items():
            ranked = sorted(
                counts.items(),
                key=lambda item: (-item[1], repr(item[0])),
            )
            best_vector, best_support = ranked[0]
            second_support = ranked[1][1] if len(ranked) > 1 else 0
            admitted = best_support >= 2 and best_support > second_support
            operation_rows[repr(operation)] = {
                "operation": repr(operation),
                "vector": best_vector,
                "support": best_support,
                "runner_up_support": second_support,
                "admitted": admitted,
                "alternatives": [
                    {"vector": vector, "support": support}
                    for vector, support in ranked
                ],
            }
        output[epoch] = operation_rows
    return output


def _rotate(matrix: tuple[tuple[Any, ...], ...]) -> tuple[tuple[Any, ...], ...]:
    return tuple(tuple(row) for row in zip(*matrix[::-1]))


def _reflect(matrix: tuple[tuple[Any, ...], ...]) -> tuple[tuple[Any, ...], ...]:
    return tuple(tuple(reversed(row)) for row in matrix)


def _dihedral_images(
    matrix: tuple[tuple[Any, ...], ...],
) -> tuple[tuple[str, tuple[tuple[Any, ...], ...]], ...]:
    images = []
    current = matrix
    for turns in range(4):
        images.append((f"rotate_{90 * turns}", current))
        images.append((f"rotate_{90 * turns}_reflect", _reflect(current)))
        current = _rotate(current)
    return tuple(images)


def _partition_matrix(
    matrix: tuple[tuple[Any, ...], ...],
) -> tuple[tuple[Any, ...], ...]:
    labels: dict[int, int] = {}
    output = []
    for row in matrix:
        next_row = []
        for value in row:
            if value in {OUTSIDE, CONTROLLED}:
                next_row.append(value)
                continue
            raw = int(value)
            if raw not in labels:
                labels[raw] = len(labels)
            next_row.append(("palette_class", labels[raw]))
        output.append(tuple(next_row))
    return tuple(output)


def _canonical_matrix(
    matrix: tuple[tuple[Any, ...], ...],
) -> tuple[tuple[tuple[Any, ...], ...], str]:
    candidates = []
    for transform, image in _dihedral_images(matrix):
        partition = _partition_matrix(image)
        candidates.append((repr(partition), transform, partition))
    _key, transform, partition = min(candidates)
    return partition, transform


def _configuration_partition(values: tuple[Any, ...]) -> tuple[int, ...]:
    labels = {}
    output = []
    for value in values:
        key = repr(value)
        if key not in labels:
            labels[key] = len(labels)
        output.append(labels[key])
    return tuple(output)


def _window(
    grid: Any,
    *,
    top: int,
    left: int,
    size: int,
    current_origin: tuple[int, int],
    sprite_shape: tuple[int, int],
) -> tuple[tuple[Any, ...], ...]:
    current_row, current_col = current_origin
    height, width = sprite_shape
    rows = []
    for offset_row in range(size):
        row = []
        grid_row = top + offset_row
        for offset_col in range(size):
            grid_col = left + offset_col
            if (
                current_row <= grid_row < current_row + height
                and current_col <= grid_col < current_col + width
            ):
                row.append(CONTROLLED)
            elif (
                grid_row < 0
                or grid_col < 0
                or grid_row >= len(grid)
                or grid_col >= len(grid[grid_row])
            ):
                row.append(OUTSIDE)
            else:
                row.append(int(grid[grid_row][grid_col]))
        rows.append(tuple(row))
    return tuple(rows)


def _descriptor(
    row: dict[str, Any],
    *,
    projection: Any,
    operation_maps: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    _terminal_index, terminal = row["section"][-1]
    operation = repr(terminal.a)
    operation_row = operation_maps.get(row["source_epoch"], {}).get(operation)
    factors = projection.factor(terminal.s)
    origins = tuple(factors.controlled_base)
    base = {
        "operation": operation,
        "operation_map": operation_row,
        "controlled_origin_count": len(origins),
        "controlled_origin_sha256s": [
            stable_sha256(origin) for origin in origins
        ],
    }
    if operation_row is None or not operation_row["admitted"] or len(origins) != 1:
        return {**base, "admissible": False, "descriptors": {}}

    origin = origins[0]
    delta_row, delta_col = operation_row["vector"]
    attempted = (origin[0] + delta_row, origin[1] + delta_col)
    height = len(projection.sprite)
    width = len(projection.sprite[0])
    span = max(height, width)
    footprint_raw = _window(
        terminal.s,
        top=attempted[0],
        left=attempted[1],
        size=span,
        current_origin=origin,
        sprite_shape=(height, width),
    )
    shell_raw = _window(
        terminal.s,
        top=attempted[0] - span,
        left=attempted[1] - span,
        size=3 * span,
        current_origin=origin,
        sprite_shape=(height, width),
    )
    footprint, footprint_transform = _canonical_matrix(footprint_raw)
    shell, shell_transform = _canonical_matrix(shell_raw)
    configuration = _configuration_partition(
        tuple(factors.finite_configuration)
    )
    descriptor_values = {
        "footprint": ("footprint", footprint),
        "footprint_plus_configuration": (
            "footprint_plus_configuration",
            footprint,
            configuration,
        ),
        "shell": ("shell", shell),
        "shell_plus_configuration": (
            "shell_plus_configuration",
            shell,
            configuration,
        ),
        "configuration_only": ("configuration_only", configuration),
    }
    return {
        **base,
        "admissible": True,
        "controlled_origin": origin,
        "attempted_origin": attempted,
        "sprite_shape": (height, width),
        "footprint_transform": footprint_transform,
        "shell_transform": shell_transform,
        "configuration_sha256": stable_sha256(configuration),
        "descriptors": {
            name: {
                "sha256": stable_sha256(value),
                "value": value,
            }
            for name, value in descriptor_values.items()
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    project = Path(args.project).resolve()
    carrier, _kind, _sha = load_carrier_path(
        project / "test_model.py",
        project_dir=project,
    )
    projection = getattr(carrier, "_ztare_factored_projection", None)
    if projection is None:
        raise SystemExit("carrier has no factored projection")

    bank_path = project / "raw/episodes/episode_001.jsonl"
    bank = tuple(EpisodeLog.read_jsonl(bank_path))
    boundaries = []
    for index, transition in enumerate(bank):
        identity = getattr(transition, "identity", None)
        if (
            identity is None
            or not identity.is_authoritative
            or not identity.is_boundary
            or identity.source_epoch not in {0, 1}
        ):
            continue
        boundaries.append({
            "boundary_index": index,
            "source_epoch": int(identity.source_epoch),
            "target_epoch": int(identity.target_epoch),
            "boundary_kind": str(identity.boundary_kind),
            "positive": str(identity.boundary_kind) == "level_completed",
            "section": predecessor._boundary_section(bank, index),
            "evidence_ref": f"raw/episodes/episode_001.jsonl#{index}",
        })

    operation_maps = _operation_maps(boundaries, projection=projection)
    for row in boundaries:
        row["relation"] = _descriptor(
            row,
            projection=projection,
            operation_maps=operation_maps,
        )

    templates = [
        row for row in boundaries
        if row["source_epoch"] == 0 and row["positive"]
    ]
    holdouts = [row for row in boundaries if row["source_epoch"] == 1]
    if len(templates) != 1:
        raise SystemExit(
            f"expected one epoch-0 completion, found {len(templates)}"
        )
    template = templates[0]

    descriptor_results = []
    for name in (
        "footprint",
        "footprint_plus_configuration",
        "shell",
        "shell_plus_configuration",
        "configuration_only",
    ):
        template_descriptor = template["relation"]["descriptors"].get(name)
        matches = []
        for holdout in holdouts:
            candidate = holdout["relation"]["descriptors"].get(name)
            matched = bool(
                template_descriptor is not None
                and candidate is not None
                and template_descriptor["sha256"] == candidate["sha256"]
            )
            matches.append({
                "boundary_index": holdout["boundary_index"],
                "boundary_kind": holdout["boundary_kind"],
                "positive": holdout["positive"],
                "admissible": holdout["relation"]["admissible"],
                "descriptor_sha256": (
                    candidate["sha256"] if candidate is not None else None
                ),
                "matched": matched,
                "evidence_ref": holdout["evidence_ref"],
            })
        positive_matches = [
            row for row in matches if row["positive"] and row["matched"]
        ]
        negative_matches = [
            row for row in matches if not row["positive"] and row["matched"]
        ]
        product = name in {
            "footprint_plus_configuration",
            "shell_plus_configuration",
        }
        passed = bool(
            product
            and template_descriptor is not None
            and template["relation"]["admissible"]
            and len(positive_matches) == 1
            and not negative_matches
        )
        descriptor_results.append({
            "descriptor": name,
            "template_sha256": (
                template_descriptor["sha256"]
                if template_descriptor is not None
                else None
            ),
            "positive_match_count": len(positive_matches),
            "negative_match_count": len(negative_matches),
            "passed": passed,
            "holdouts": matches,
        })

    passing = [row for row in descriptor_results if row["passed"]]
    payload = {
        "schema": "ztare-terminal-affordance-relation-audit-v1",
        "operation_maps": operation_maps,
        "template": {
            "boundary_index": template["boundary_index"],
            "boundary_kind": template["boundary_kind"],
            "evidence_ref": template["evidence_ref"],
            "relation": template["relation"],
        },
        "holdout_relations": [
            {
                "boundary_index": row["boundary_index"],
                "boundary_kind": row["boundary_kind"],
                "positive": row["positive"],
                "evidence_ref": row["evidence_ref"],
                "relation": row["relation"],
            }
            for row in holdouts
        ],
        "descriptor_results": descriptor_results,
        "passing_descriptors": [row["descriptor"] for row in passing],
        "status": (
            "terminal_affordance_relation_confirmed"
            if passing
            else "terminal_affordance_relation_refuted"
        ),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": payload["status"],
        "operation_maps": operation_maps,
        "template": {
            "boundary_index": template["boundary_index"],
            "relation": {
                key: value
                for key, value in template["relation"].items()
                if key != "descriptors"
            },
        },
        "passing_descriptors": payload["passing_descriptors"],
        "descriptor_results": descriptor_results,
        "output": str(output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
