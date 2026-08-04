#!/usr/bin/env python3
"""Audit one shared D4 action on target geometry and finite configuration."""
from __future__ import annotations

import argparse
from collections import defaultdict
from math import isqrt
import json
from pathlib import Path
from typing import Any

import success_predecessor_mechanism_audit as predecessor
import terminal_affordance_relation_audit as affordance

from ztare.common.equivariance import stable_sha256
from ztare.worldmodel.carrier_loader import load_carrier_path
from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.gates import law_scored_view


WRONG_ACTIVE_CONFIGURATION = (
    "293fb91ad721cdd6f9126d2d6e9e0750b257c86ae5f3802e1ce11c814ab8f94b"
)
EXPECTED_FOOTPRINT = (
    "5f332d7e3f1cf374998f1da7bc323ebe6cee405acb23268c60992eb8f7760bec"
)


def _square(values: tuple[Any, ...]) -> tuple[tuple[Any, ...], ...] | None:
    side = isqrt(len(values))
    if side == 0 or side * side != len(values):
        return None
    return tuple(
        tuple(values[offset : offset + side])
        for offset in range(0, len(values), side)
    )


def _images_by_name(
    matrix: tuple[tuple[Any, ...], ...],
) -> dict[str, tuple[tuple[Any, ...], ...]]:
    return dict(affordance._dihedral_images(matrix))


def _canonical_value(
    tag: str,
    matrix: tuple[tuple[Any, ...], ...],
) -> dict[str, Any]:
    partition, transform = affordance._canonical_matrix(matrix)
    value = (tag, partition)
    return {
        "sha256": stable_sha256(value),
        "transform": transform,
        "value": value,
    }


def _joint_code(
    footprint: tuple[tuple[Any, ...], ...],
    configuration: tuple[tuple[Any, ...], ...],
) -> dict[str, Any]:
    footprints = _images_by_name(footprint)
    configurations = _images_by_name(configuration)
    if footprints.keys() != configurations.keys():
        raise ValueError("D4 transform names differ across joint factors")
    candidates = []
    for transform in sorted(footprints):
        footprint_partition = affordance._partition_matrix(
            footprints[transform]
        )
        configuration_partition = affordance._partition_matrix(
            configurations[transform]
        )
        value = (
            "joint_affordance",
            footprint_partition,
            configuration_partition,
        )
        candidates.append((repr(value), transform, value))
    _key, transform, value = min(candidates)
    return {
        "sha256": stable_sha256(value),
        "transform": transform,
        "value": value,
    }


def _codes(
    footprint: tuple[tuple[Any, ...], ...],
    configuration: tuple[tuple[Any, ...], ...],
) -> dict[str, dict[str, Any]]:
    footprint_only = _canonical_value("footprint", footprint)
    configuration_only = _canonical_value(
        "configuration",
        configuration,
    )
    independent_value = (
        "independent_product",
        footprint_only["value"],
        configuration_only["value"],
    )
    return {
        "joint": _joint_code(footprint, configuration),
        "footprint_only": footprint_only,
        "configuration_only": configuration_only,
        "independent_product": {
            "sha256": stable_sha256(independent_value),
            "footprint_transform": footprint_only["transform"],
            "configuration_transform": configuration_only["transform"],
            "value": independent_value,
        },
    }


def _raw_relation(
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
    }
    if operation_row is None or not operation_row["admitted"] or len(origins) != 1:
        return {**base, "admissible": False}

    configuration_values = tuple(factors.finite_configuration)
    configuration = _square(configuration_values)
    if configuration is None:
        return {
            **base,
            "admissible": False,
            "configuration_length": len(configuration_values),
            "reason": "nonsquare_configuration",
        }

    origin = origins[0]
    delta_row, delta_col = operation_row["vector"]
    attempted = origin[0] + delta_row, origin[1] + delta_col
    height = len(projection.sprite)
    width = len(projection.sprite[0])
    span = max(height, width)
    footprint = affordance._window(
        terminal.s,
        top=attempted[0],
        left=attempted[1],
        size=span,
        current_origin=origin,
        sprite_shape=(height, width),
    )
    configuration_partition = affordance._configuration_partition(
        configuration_values
    )
    return {
        **base,
        "admissible": True,
        "controlled_origin": origin,
        "attempted_origin": attempted,
        "configuration_sha256": stable_sha256(configuration_partition),
        "configuration_shape": (len(configuration), len(configuration[0])),
        "raw_configuration_partition": _square(configuration_partition),
        "codes": _codes(footprint, configuration),
    }


def _terminal_rows(
    bank: Any,
) -> list[dict[str, Any]]:
    rows = []
    for index, transition in enumerate(bank):
        identity = getattr(transition, "identity", None)
        if (
            identity is None
            or not identity.is_authoritative
            or not identity.is_boundary
            or identity.source_epoch not in {0, 1}
        ):
            continue
        rows.append({
            "boundary_index": index,
            "source_epoch": int(identity.source_epoch),
            "target_epoch": int(identity.target_epoch),
            "boundary_kind": str(identity.boundary_kind),
            "positive": str(identity.boundary_kind) == "level_completed",
            "section": predecessor._boundary_section(bank, index),
            "evidence_ref": f"raw/episodes/episode_001.jsonl#{index}",
        })
    return rows


def _active_target(
    *,
    project: Path,
    projection: Any,
    active_result: dict[str, Any],
) -> dict[str, Any]:
    matches = active_result.get("matches") or []
    if len(matches) != 1:
        raise ValueError(f"expected one frozen H29 match, found {len(matches)}")
    match = matches[0]
    if (
        match.get("disposition") != "observed_law"
        or match.get("operation") != "1"
        or match.get("relation", {}).get("descriptor_sha256")
        != EXPECTED_FOOTPRINT
    ):
        raise ValueError("H29 target identity drifted")
    evidence_ref = str(match["source_representative_evidence_ref"])
    path_text, row_text = evidence_ref.rsplit("#", 1)
    rows = tuple(EpisodeLog.read_jsonl(project / path_text))
    row_index = int(row_text)
    if not 0 <= row_index < len(rows):
        raise ValueError("H29 source representative index is out of range")
    transition = rows[row_index]
    frozen_representative_sha = str(
        match["source_representative_sha256"]
    )
    representatives = [
        state
        for state in (transition.s, transition.s_next)
        if stable_sha256(state) == frozen_representative_sha
    ]
    if len(representatives) != 1:
        raise ValueError(
            "H29 evidence edge does not identify one frozen representative"
        )
    grid = representatives[0]
    factors = projection.factor(grid)
    origins = tuple(factors.controlled_base)
    operation_map = active_result["operation_maps"]["1"]
    if not operation_map.get("admitted") or len(origins) != 1:
        raise ValueError("H29 active target is no longer admissible")
    origin = origins[0]
    delta_row, delta_col = operation_map["vector"]
    attempted = origin[0] + delta_row, origin[1] + delta_col
    height = len(projection.sprite)
    width = len(projection.sprite[0])
    footprint = affordance._window(
        grid,
        top=attempted[0],
        left=attempted[1],
        size=max(height, width),
        current_origin=origin,
        sprite_shape=(height, width),
    )
    canonical, transform = affordance._canonical_matrix(footprint)
    descriptor_sha = stable_sha256(("footprint", canonical))
    if descriptor_sha != EXPECTED_FOOTPRINT:
        raise ValueError("reconstructed H29 footprint does not match template")
    return {
        "evidence_ref": evidence_ref,
        "grid": grid,
        "footprint": footprint,
        "controlled_origin": origin,
        "attempted_origin": attempted,
        "canonical_transform": transform,
        "descriptor_sha256": descriptor_sha,
    }


def _transition_key(transition: Any) -> str:
    identity = getattr(transition, "identity", None)
    identity_value = None
    if identity is not None:
        identity_value = (
            identity.source_epoch,
            identity.target_epoch,
            identity.boundary_kind,
            identity.authority,
        )
    return stable_sha256((
        transition.s,
        transition.a,
        transition.s_next,
        identity_value,
    ))


def _active_configurations(
    *,
    bank: Any,
    projection: Any,
    active_epoch: int,
) -> list[dict[str, Any]]:
    admitted = tuple(law_scored_view(bank, source_epoch=active_epoch))
    admitted_keys = {_transition_key(row) for row in admitted}
    state_refs: dict[str, set[str]] = defaultdict(set)
    states: dict[str, Any] = {}
    for index, transition in enumerate(bank):
        if _transition_key(transition) not in admitted_keys:
            continue
        for suffix, state in (("s", transition.s), ("s_next", transition.s_next)):
            state_sha = stable_sha256(state)
            states[state_sha] = state
            state_refs[state_sha].add(
                f"raw/episodes/episode_001.jsonl#{index}:{suffix}"
            )

    by_configuration: dict[str, dict[str, Any]] = {}
    nonsquare = []
    for state_sha, state in states.items():
        factors = projection.factor(state)
        values = tuple(factors.finite_configuration)
        matrix = _square(values)
        if matrix is None:
            nonsquare.append({
                "state_sha256": state_sha,
                "configuration_length": len(values),
            })
            continue
        partition = affordance._configuration_partition(values)
        configuration_sha = stable_sha256(partition)
        row = by_configuration.setdefault(configuration_sha, {
            "configuration_sha256": configuration_sha,
            "matrix": matrix,
            "partition_matrix": _square(partition),
            "state_sha256s": [],
            "evidence_refs": set(),
        })
        row["state_sha256s"].append(state_sha)
        row["evidence_refs"].update(state_refs[state_sha])

    if nonsquare:
        raise ValueError(
            f"active evidence has {len(nonsquare)} nonsquare configurations"
        )
    output = []
    for row in by_configuration.values():
        output.append({
            **row,
            "state_sha256s": sorted(set(row["state_sha256s"])),
            "evidence_refs": sorted(row["evidence_refs"]),
        })
    return sorted(output, key=lambda row: row["configuration_sha256"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--active-result", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    project = Path(args.project).resolve()
    carrier, _kind, _carrier_sha = load_carrier_path(
        project / "test_model.py",
        project_dir=project,
    )
    projection = getattr(carrier, "_ztare_factored_projection", None)
    if projection is None:
        raise SystemExit("carrier has no factored projection")
    log = EpisodeLog.read_jsonl(
        project / "raw/episodes/episode_001.jsonl"
    )
    bank = tuple(log)

    terminals = _terminal_rows(bank)
    operation_maps = affordance._operation_maps(
        terminals,
        projection=projection,
    )
    for row in terminals:
        row["relation"] = _raw_relation(
            row,
            projection=projection,
            operation_maps=operation_maps,
        )
    templates = [
        row for row in terminals
        if row["source_epoch"] == 0 and row["positive"]
    ]
    holdouts = [row for row in terminals if row["source_epoch"] == 1]
    if len(templates) != 1:
        raise SystemExit(
            f"expected one epoch-0 completion, found {len(templates)}"
        )
    template = templates[0]
    if not template["relation"]["admissible"]:
        raise SystemExit("epoch-0 template relation is inadmissible")

    prior_tests = {}
    for code_name in (
        "joint",
        "footprint_only",
        "configuration_only",
        "independent_product",
    ):
        template_sha = template["relation"]["codes"][code_name]["sha256"]
        rows = []
        for holdout in holdouts:
            candidate = (
                holdout["relation"].get("codes", {}).get(code_name, {})
            )
            matched = candidate.get("sha256") == template_sha
            rows.append({
                "boundary_index": holdout["boundary_index"],
                "boundary_kind": holdout["boundary_kind"],
                "positive": holdout["positive"],
                "admissible": holdout["relation"]["admissible"],
                "matched": matched,
                "sha256": candidate.get("sha256"),
                "transform": candidate.get("transform"),
                "evidence_ref": holdout["evidence_ref"],
            })
        prior_tests[code_name] = {
            "template_sha256": template_sha,
            "positive_match_count": sum(
                row["positive"] and row["matched"] for row in rows
            ),
            "negative_match_count": sum(
                not row["positive"] and row["matched"] for row in rows
            ),
            "holdouts": rows,
        }

    active_payload = json.loads(
        Path(args.active_result).read_text(encoding="utf-8")
    )
    active_epoch = int(active_payload["active_problem"]["active_epoch"])
    target = _active_target(
        project=project,
        projection=projection,
        active_result=active_payload,
    )
    configurations = _active_configurations(
        bank=log,
        projection=projection,
        active_epoch=active_epoch,
    )
    active_matches: dict[str, list[dict[str, Any]]] = {
        name: [] for name in prior_tests
    }
    active_rows = []
    for configuration in configurations:
        codes = _codes(target["footprint"], configuration["matrix"])
        code_matches = {}
        for code_name, code in codes.items():
            matched = (
                code["sha256"]
                == prior_tests[code_name]["template_sha256"]
            )
            code_matches[code_name] = matched
            if matched:
                active_matches[code_name].append({
                    "configuration_sha256": configuration[
                        "configuration_sha256"
                    ],
                    "code_sha256": code["sha256"],
                    "transform": code.get("transform"),
                    "state_count": len(configuration["state_sha256s"]),
                    "state_sha256s": configuration["state_sha256s"],
                    "evidence_refs": configuration["evidence_refs"],
                })
        active_rows.append({
            "configuration_sha256": configuration["configuration_sha256"],
            "partition_matrix": configuration["partition_matrix"],
            "state_count": len(configuration["state_sha256s"]),
            "evidence_refs": configuration["evidence_refs"],
            "matches": code_matches,
            "codes": {
                name: {
                    key: value
                    for key, value in code.items()
                    if key != "value"
                }
                for name, code in codes.items()
            },
        })

    joint_prior = prior_tests["joint"]
    joint_active = active_matches["joint"]
    distinct_active = [
        row for row in joint_active
        if row["configuration_sha256"] != WRONG_ACTIVE_CONFIGURATION
    ]
    joint_active_set = {
        row["configuration_sha256"] for row in joint_active
    }
    independent_active_set = {
        row["configuration_sha256"]
        for row in active_matches["independent_product"]
    }
    independent_inferior = bool(
        joint_active_set
        and (
            independent_active_set > joint_active_set
            or (
                WRONG_ACTIVE_CONFIGURATION in independent_active_set
                and WRONG_ACTIVE_CONFIGURATION not in joint_active_set
            )
        )
    )
    all_admissible = all(
        row["relation"]["admissible"] for row in [template, *holdouts]
    )
    passed = bool(
        all_admissible
        and joint_prior["positive_match_count"] == 1
        and joint_prior["negative_match_count"] == 0
        and distinct_active
        and independent_inferior
    )
    payload = {
        "schema": "ztare-joint-equivariant-affordance-audit-v1",
        "status": (
            "joint_equivariant_affordance_confirmed"
            if passed
            else "joint_equivariant_affordance_refuted"
        ),
        "operation_maps": operation_maps,
        "template": {
            "boundary_index": template["boundary_index"],
            "evidence_ref": template["evidence_ref"],
            "configuration_sha256": template["relation"][
                "configuration_sha256"
            ],
            "raw_configuration_partition": template["relation"][
                "raw_configuration_partition"
            ],
            "codes": template["relation"]["codes"],
        },
        "prior_tests": prior_tests,
        "active": {
            "epoch": active_epoch,
            "target": {
                key: value
                for key, value in target.items()
                if key not in {"grid", "footprint"}
            },
            "configuration_count": len(configurations),
            "configurations": active_rows,
            "matches": active_matches,
            "joint_distinct_match_count": len(distinct_active),
            "independent_product_inferior": independent_inferior,
        },
        "criteria": {
            "all_terminal_inputs_admissible": all_admissible,
            "unique_prior_positive": (
                joint_prior["positive_match_count"] == 1
            ),
            "zero_prior_failures": (
                joint_prior["negative_match_count"] == 0
            ),
            "distinct_active_preimage": bool(distinct_active),
            "independent_product_inferior": independent_inferior,
        },
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": payload["status"],
        "criteria": payload["criteria"],
        "prior_joint": {
            key: value
            for key, value in joint_prior.items()
            if key != "holdouts"
        },
        "active_configuration_count": len(configurations),
        "active_match_counts": {
            name: len(rows) for name, rows in active_matches.items()
        },
        "joint_active_configuration_sha256s": [
            row["configuration_sha256"] for row in joint_active
        ],
        "output": str(output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
