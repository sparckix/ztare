"""Walk-forward audit of an enumerated company-state representation."""

from __future__ import annotations

from argparse import ArgumentParser
import json
import math
from pathlib import Path
from statistics import mean
from typing import Any, Mapping, Sequence

import yaml

from ztare.common.equivariance import stable_sha256
from ztare.experiment_stats import paired_permutation_test

from .company_state_flow import (
    _load_state_observations,
    _quarter_ends,
    _state_panel,
    decompose_transition_counts,
)
from .company_state_partition_frontier import (
    COMPANY_STATE_PARTITION_FRONTIER_SCHEMA,
    OBJECTIVES,
    _candidate,
    _partition_panel,
    _state_ids,
)


COMPANY_STATE_REPRESENTATION_REPLAY_SCHEMA = (
    "jaggedthoughts-company-state-representation-replay-v1"
)
_CROSS_PARTITIONS = ((2, 2), (2, 3), (3, 2), (3, 3))


def _probabilities(counts: Sequence[Sequence[int]], pseudocount: float) -> list[list[float]]:
    return [
        [
            (float(value) + pseudocount)
            / (sum(float(item) for item in row) + pseudocount * len(row))
            for value in row
        ]
        for row in counts
    ]


def _cross_entropy(rows: Sequence[tuple[int, int]], probabilities: Sequence[Sequence[float]]) -> float:
    return -mean(math.log(max(float(probabilities[source][target]), 1e-15)) for source, target in rows)


def _dominates(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    left_values = tuple(float(left["objectives"][name]) for name in OBJECTIVES)
    right_values = tuple(float(right["objectives"][name]) for name in OBJECTIVES)
    return all(a >= b for a, b in zip(left_values, right_values, strict=True)) and any(
        a > b for a, b in zip(left_values, right_values, strict=True)
    )


def _select_partition(training_panels: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    candidates = [_candidate(training_panels, value, durability)[0] for value, durability in _CROSS_PARTITIONS]
    supported = [row for row in candidates if row["support_valid"]]
    frontier = [
        row for row in supported
        if not any(_dominates(other, row) for other in supported if other is not row)
    ]
    if not frontier:
        raise ValueError("no supported cross-axis partition in the training window")
    return max(frontier, key=lambda row: (
        int(row["metrics"]["state_count"]),
        float(row["objectives"]["transition_selectivity"]),
        float(row["objectives"]["panel_coverage"]),
        -int(row["metrics"]["description_units"]),
        str(row["partition_id"]),
    ))


def _transition_rows(
    panels: Sequence[Mapping[str, Any]], value_levels: int, durability_levels: int,
) -> tuple[list[list[tuple[int, int]]], tuple[str, ...]]:
    state_ids = _state_ids(value_levels, durability_levels)
    state_index = {state_id: index for index, state_id in enumerate(state_ids)}
    partitioned = [_partition_panel(panel, value_levels, durability_levels) for panel in panels]
    blocks = []
    for source, target in zip(partitioned, partitioned[1:], strict=False):
        common = sorted(set(source["assignments"]) & set(target["assignments"]))
        blocks.append([
            (state_index[source["assignments"][entity]], state_index[target["assignments"][entity]])
            for entity in common
        ])
    return blocks, state_ids


def _score_block(
    panels: Sequence[Mapping[str, Any]], *, evaluation_offset: int,
    selected: Mapping[str, Any], pseudocount: float,
) -> dict[str, Any]:
    value_levels = int(selected["value_levels"])
    durability_levels = int(selected["durability_levels"])
    blocks, state_ids = _transition_rows(panels[: evaluation_offset + 2], value_levels, durability_levels)
    training = [transition for block in blocks[:-1] for transition in block]
    evaluation = blocks[-1]
    state_count = len(state_ids)
    joint_counts = [[0] * state_count for _ in range(state_count)]
    value_counts = [[0] * value_levels for _ in range(value_levels)]
    durability_counts = [[0] * durability_levels for _ in range(durability_levels)]
    for source, target in training:
        joint_counts[source][target] += 1
        source_value, source_durability = divmod(source, durability_levels)
        target_value, target_durability = divmod(target, durability_levels)
        value_counts[source_value][target_value] += 1
        durability_counts[source_durability][target_durability] += 1

    decomposition = decompose_transition_counts(joint_counts, pseudocount=pseudocount)
    value_probabilities = _probabilities(value_counts, pseudocount)
    durability_probabilities = _probabilities(durability_counts, pseudocount)
    factorized = [
        [
            value_probabilities[source // durability_levels][target // durability_levels]
            * durability_probabilities[source % durability_levels][target % durability_levels]
            for target in range(state_count)
        ]
        for source in range(state_count)
    ]
    losses = {
        "directed_joint": _cross_entropy(evaluation, decomposition["directed_transition"]),
        "factorized_axes": _cross_entropy(evaluation, factorized),
        "reversible_joint": _cross_entropy(evaluation, decomposition["reversible_transition"]),
    }
    return {
        "inference_block_id": str(panels[evaluation_offset + 1]["epoch"]),
        "source_epoch": str(panels[evaluation_offset]["epoch"]),
        "target_epoch": str(panels[evaluation_offset + 1]["epoch"]),
        "partition_id": selected["partition_id"],
        "state_count": state_count,
        "training_transition_count": len(training),
        "evaluation_transition_count": len(evaluation),
        "circulation_strength": decomposition["circulation_strength"],
        "losses": losses,
    }


def compile_company_state_representation_replay(
    frontier_path: str | Path, profile_path: str | Path, *, workspace: str | Path,
) -> dict[str, Any]:
    """Select grammar partitions on prior panels and score the next transition block."""
    root = Path(workspace).expanduser().resolve()
    frontier_source = Path(frontier_path).expanduser()
    profile_source = Path(profile_path).expanduser()
    if not frontier_source.is_absolute():
        frontier_source = root / frontier_source
    if not profile_source.is_absolute():
        profile_source = root / profile_source
    frontier = json.loads(frontier_source.read_text(encoding="utf-8"))
    profile = yaml.safe_load(profile_source.read_text(encoding="utf-8"))
    if frontier.get("schema") != COMPANY_STATE_PARTITION_FRONTIER_SCHEMA:
        raise ValueError(f"representation replay requires {COMPANY_STATE_PARTITION_FRONTIER_SCHEMA}")
    frontier_body = dict(frontier)
    frontier_sha256 = str(frontier_body.pop("partition_frontier_sha256", ""))
    if frontier_sha256 != stable_sha256(frontier_body):
        raise ValueError("company-state partition frontier content hash mismatch")

    pseudocount = float(profile.get("pseudocount", 1.0))
    minimum_training_blocks = int(profile.get("minimum_training_blocks", 4))
    panels, universe = _state_panel(
        _load_state_observations(
            root / "data" / "observations.csv",
            _quarter_ends(str(profile["start_date"]), str(profile["end_date"])),
            source_as_of=str(frontier["as_of"]),
        ),
        _quarter_ends(str(profile["start_date"]), str(profile["end_date"])),
        source_as_of=str(frontier["as_of"]),
        min_years=int(profile.get("min_years", 3)),
        min_cross_section=int(profile.get("min_cross_section", 20)),
        benchmark_id=str(profile["benchmark_id"]),
    )
    blocks = []
    for evaluation_offset in range(minimum_training_blocks, len(panels) - 1):
        selected = _select_partition(panels[: evaluation_offset + 1])
        blocks.append(_score_block(
            panels, evaluation_offset=evaluation_offset, selected=selected,
            pseudocount=pseudocount,
        ))
    if len(blocks) < 8:
        raise ValueError("representation replay requires at least eight next-quarter blocks")

    losses = {
        model: [float(row["losses"][model]) for row in blocks]
        for model in ("directed_joint", "factorized_axes", "reversible_joint")
    }
    comparisons = {}
    for control in ("factorized_axes", "reversible_joint"):
        inference = paired_permutation_test(
            losses["directed_joint"], losses[control], n_perm=10_000, seed=254,
        )
        comparisons[control] = {
            **inference,
            "directed_joint_win_rate": mean(
                candidate < comparator
                for candidate, comparator in zip(
                    losses["directed_joint"], losses[control], strict=True,
                )
            ),
        }
    gates = {
        "minimum_independent_blocks": len(blocks) >= 8,
        "cross_axis_interaction": (
            mean(losses["directed_joint"]) < mean(losses["factorized_axes"])
            and float(comparisons["factorized_axes"]["p_value"]) < 0.05
            and comparisons["factorized_axes"]["directed_joint_win_rate"] >= 0.625
        ),
        "directionality": (
            mean(losses["directed_joint"]) < mean(losses["reversible_joint"])
            and float(comparisons["reversible_joint"]["p_value"]) < 0.05
            and comparisons["reversible_joint"]["directed_joint_win_rate"] >= 0.625
        ),
    }
    supported = all(gates.values())
    body: dict[str, Any] = {
        "schema": COMPANY_STATE_REPRESENTATION_REPLAY_SCHEMA,
        "experiment_id": "company-state-representation-replay",
        "as_of": frontier["as_of"],
        "mode": "expanding_window_next_transition_replay",
        "authority": "retrospective_representation_diagnostic",
        "frontier_sha256": frontier_sha256,
        "profile_sha256": stable_sha256(profile),
        "universe": universe,
        "selection_rule": (
            "enumerate four typed cross-axis partitions; retain the support-valid Pareto frontier "
            "using prior panels only; choose maximum state granularity, then selectivity, coverage, "
            "and description efficiency"
        ),
        "target": "next-quarter joint valuation and durable-earnings state",
        "inference_block_count": len(blocks),
        "minimum_inference_blocks": 8,
        "selected_partition_counts": {
            partition_id: sum(row["partition_id"] == partition_id for row in blocks)
            for partition_id in sorted({str(row["partition_id"]) for row in blocks})
        },
        "mean_cross_entropy": {model: mean(values) for model, values in losses.items()},
        "comparisons": comparisons,
        "gates": gates,
        "representation_supported": supported,
        "status": "supported" if supported else "rejected_by_declared_controls",
        "capital_authority": False,
        "positive_alpha_evidence": False,
        "blocks": blocks,
        "use_boundary": (
            "Each partition is selected before its target block, but the historical company universe "
            "comes from the current store and historical prices were retrieved later. This can reject "
            "the representation mechanism; a positive result could only nominate a separately sealed trial."
        ),
    }
    return {**body, "replay_sha256": stable_sha256(body)}


def main() -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument(
        "--frontier", default="experiments/results/company-state-partition-frontier.json",
    )
    parser.add_argument(
        "--profile", default="experiments/company_state_probability_current.yaml",
    )
    parser.add_argument("--output")
    args = parser.parse_args()
    result = compile_company_state_representation_replay(
        args.frontier, args.profile, workspace=args.workspace,
    )
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        destination = Path(args.output).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "COMPANY_STATE_REPRESENTATION_REPLAY_SCHEMA",
    "compile_company_state_representation_replay",
]
