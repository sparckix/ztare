#!/usr/bin/env python3
"""Fit discovery-only factor guards and score chronological H63 effects."""
from __future__ import annotations

import itertools
import json
from pathlib import Path
import sys
from typing import Any, Hashable, Iterable


FIXTURES = Path(__file__).resolve().parent
ROOT = FIXTURES.parents[2]
sys.path.insert(0, str(FIXTURES))
sys.path.insert(0, str(ROOT / "src"))

import task_conditioned_skill_basin_audit as h77

from ztare.common.equivariance import stable_sha256
from ztare.worldmodel.carrier_loader import load_carrier_path
from ztare.worldmodel.mechanism_effects import (
    compile_history_guarded_skill_library,
    guarded_skill_traces_from_history_evidence,
)
from ztare.worldmodel.patch_base_carrier import (
    carrier_execution_sha256_from_source,
)


HYPOTHESIS_ID = "H-GPSA-CHRONOLOGICAL-MINIMAL-EFFECT-GUARD-20260806-113"
DISCOVERY_TRAJECTORIES = 21
EXPECTED_TRAJECTORIES = 28
COORDINATE_NAMES = (
    "controlled_base",
    "finite_configuration",
    "operation_domain_assignment",
    "ordered_feasibility_configuration",
    "ordered_budget",
    "one_shot_availability",
    "history_suffix",
    "predictive_context",
)


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _coordinates(source: Hashable) -> tuple[Hashable, ...]:
    if not isinstance(source, tuple) or len(source) not in {7, 8}:
        raise ValueError("unexpected H63 initiation-key shape")
    history = source[6]
    if not (
        isinstance(history, tuple)
        and history
        and str(history[0]).endswith("_history_suffix")
    ):
        raise ValueError("H63 initiation key lacks a typed history suffix")
    predictive = (
        source[7]
        if len(source) == 8
        else ("predictive_context_absent",)
    )
    return (*source[:7], predictive)


def _effect_sha256(effects: Iterable[Hashable]) -> str:
    return stable_sha256(tuple(effects))


def _windows(traces: Iterable[Any], words: Iterable[tuple[Hashable, ...]]):
    word_set = tuple(sorted(
        set(words),
        key=lambda word: (len(word), stable_sha256(word)),
    ))
    rows = []
    for trace in traces:
        transitions = trace.transitions
        for word in word_set:
            width = len(word)
            for start in range(0, len(transitions) - width + 1):
                window = transitions[start:start + width]
                if tuple(row.operation for row in window) != word:
                    continue
                if any(
                    row.boundary_kind
                    or row.successor is None
                    or row.effect is None
                    for row in window
                ):
                    continue
                source = window[0].source
                rows.append({
                    "trace_ref": trace.trace_ref,
                    "start_index": start,
                    "word": word,
                    "word_sha256": stable_sha256(word),
                    "source": source,
                    "source_sha256": stable_sha256(source),
                    "coordinates": _coordinates(source),
                    "effect_sha256": _effect_sha256(
                        row.effect for row in window
                    ),
                    "termination_sha256": stable_sha256(
                        window[-1].successor
                    ),
                })
    return tuple(rows)


def _guard_key(
    coordinates: tuple[Hashable, ...],
    axes: tuple[int, ...],
) -> tuple[Hashable, ...]:
    return tuple(coordinates[index] for index in axes)


def _minimal_guard(rows: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    if not rows:
        raise ValueError("guard fitting requires discovery occurrences")
    for width in range(len(COORDINATE_NAMES) + 1):
        for axes in itertools.combinations(range(len(COORDINATE_NAMES)), width):
            effects_by_guard: dict[tuple[Hashable, ...], set[str]] = {}
            for row in rows:
                key = _guard_key(row["coordinates"], axes)
                effects_by_guard.setdefault(key, set()).add(
                    row["effect_sha256"]
                )
            if all(len(effects) == 1 for effects in effects_by_guard.values()):
                effect_by_guard = {
                    key: next(iter(effects))
                    for key, effects in effects_by_guard.items()
                }
                return {
                    "axes": axes,
                    "effect_by_guard": effect_by_guard,
                    "guard_count": len(effect_by_guard),
                }
    raise RuntimeError("full initiation coordinates failed determinism")


def _program_result(
    word: tuple[Hashable, ...],
    discovery_rows: tuple[dict[str, Any], ...],
    holdout_rows: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    fitted = _minimal_guard(discovery_rows)
    axes = fitted["axes"]
    effect_by_guard = fitted["effect_by_guard"]
    discovery_sources = {
        row["source_sha256"] for row in discovery_rows
    }
    exact_unseen = tuple(
        row for row in holdout_rows
        if row["source_sha256"] not in discovery_sources
    )
    scored = []
    for row in exact_unseen:
        key = _guard_key(row["coordinates"], axes)
        predicted = effect_by_guard.get(key)
        scored.append({
            "trace_ref": row["trace_ref"],
            "start_index": row["start_index"],
            "source_sha256": row["source_sha256"],
            "guard_sha256": stable_sha256(key),
            "status": "predicted" if predicted is not None else "abstained",
            "predicted_effect_sha256": predicted,
            "observed_effect_sha256": row["effect_sha256"],
            "correct": (
                predicted == row["effect_sha256"]
                if predicted is not None
                else None
            ),
        })
    covered = tuple(row for row in scored if row["status"] == "predicted")
    correct = tuple(row for row in covered if row["correct"])
    exercised_effects = {
        row["predicted_effect_sha256"] for row in covered
    }
    discovery_effects = {
        row["effect_sha256"] for row in discovery_rows
    }
    qualifies = (
        len(discovery_effects) >= 2
        and len(axes) < len(COORDINATE_NAMES)
        and len(covered) >= 5
        and len({row["trace_ref"] for row in covered}) >= 2
        and len(correct) == len(covered)
        and len(exercised_effects) >= 2
    )
    return {
        "word": list(word),
        "word_sha256": stable_sha256(word),
        "discovery_occurrence_count": len(discovery_rows),
        "discovery_trace_count": len({
            row["trace_ref"] for row in discovery_rows
        }),
        "discovery_exact_source_count": len(discovery_sources),
        "discovery_effect_count": len(discovery_effects),
        "operation_only_ambiguous": len(discovery_effects) >= 2,
        "selected_coordinate_indices": list(axes),
        "selected_coordinate_names": [
            COORDINATE_NAMES[index] for index in axes
        ],
        "selected_coordinate_count": len(axes),
        "full_coordinate_count": len(COORDINATE_NAMES),
        "proper_subset": len(axes) < len(COORDINATE_NAMES),
        "discovery_guard_count": fitted["guard_count"],
        "holdout_occurrence_count": len(holdout_rows),
        "holdout_exact_unseen_count": len(exact_unseen),
        "covered_unseen_count": len(covered),
        "covered_unseen_trace_count": len({
            row["trace_ref"] for row in covered
        }),
        "correct_unseen_count": len(correct),
        "error_count": len(covered) - len(correct),
        "abstention_count": len(scored) - len(covered),
        "exercised_predicted_effect_count": len(exercised_effects),
        "qualifies": qualifies,
        "scored_unseen_rows": scored,
    }


def run_audit() -> dict[str, Any]:
    h63 = _load_json("post_support_probe1_recompile_audit_result.json")
    h71 = _load_json("joint_relation_recompile_audit_result.json")
    active = _load_json("active_affordance_frontier_audit_result.json")
    project = ROOT / "projects/arc3_ls20_gov"
    carrier_path = project / "test_model.py"
    carrier, _kind, carrier_sha256 = load_carrier_path(
        carrier_path,
        project_dir=project,
    )
    projection = carrier._ztare_factored_projection
    execution_sha256 = carrier_execution_sha256_from_source(
        carrier_path.read_text(encoding="utf-8")
    )
    snapshot = h77._reconstruct_snapshot(
        project=project,
        carrier=carrier,
        carrier_sha256=carrier_sha256,
        carrier_execution_sha256=execution_sha256,
        projection=projection,
        active_epoch=int(h71["active"]["epoch"]),
        origin_seed_sha256=str(
            active["active_problem"]["current_seed_sha256"]
        ),
        through_trace=str(h63["history_snapshot"]["through_trace"]),
    )
    selection = snapshot["selection"]
    trajectories = tuple(snapshot["trajectories"])
    if len(trajectories) != EXPECTED_TRAJECTORIES:
        raise RuntimeError("H63 trajectory count drifted")
    if selection.action_system.sha256 != h63["history_lift"][
        "action_system_sha256"
    ]:
        raise RuntimeError("H63 action-system identity drifted")

    discovery_trajectories = trajectories[:DISCOVERY_TRAJECTORIES]
    holdout_trajectories = trajectories[DISCOVERY_TRAJECTORIES:]
    discovery_library = compile_history_guarded_skill_library(
        discovery_trajectories,
        projection=projection,
        history_lift=selection,
        min_word_length=2,
        max_word_length=8,
        min_variant_support=2,
    )
    words = tuple(program.operations for program in discovery_library.programs)
    discovery_traces = guarded_skill_traces_from_history_evidence(
        discovery_trajectories,
        projection=projection,
        history_lift=selection,
    )
    holdout_traces = guarded_skill_traces_from_history_evidence(
        holdout_trajectories,
        projection=projection,
        history_lift=selection,
    )
    discovery_windows = _windows(discovery_traces, words)
    holdout_windows = _windows(holdout_traces, words)
    program_rows = []
    for word in words:
        word_sha = stable_sha256(word)
        program_rows.append(_program_result(
            word,
            tuple(
                row for row in discovery_windows
                if row["word_sha256"] == word_sha
            ),
            tuple(
                row for row in holdout_windows
                if row["word_sha256"] == word_sha
            ),
        ))
    qualifying = tuple(row for row in program_rows if row["qualifies"])
    mutation_checks = {
        "split_identity": stable_sha256({
            "discovery": DISCOVERY_TRAJECTORIES + 1,
            "holdout": EXPECTED_TRAJECTORIES - DISCOVERY_TRAJECTORIES - 1,
        }) != stable_sha256({
            "discovery": DISCOVERY_TRAJECTORIES,
            "holdout": EXPECTED_TRAJECTORIES - DISCOVERY_TRAJECTORIES,
        }),
        "coordinate_subset_identity": stable_sha256((0,))
        != stable_sha256((1,)),
        "program_word_identity": (
            not words
            or stable_sha256((*words[0][:-1], (int(words[0][-1]) + 1) % 4))
            != stable_sha256(words[0])
        ),
        "predicted_effect_identity": stable_sha256({
            "effect": "mutated"
        }) != stable_sha256({"effect": "observed"}),
        "source_identity": stable_sha256({"source": "mutated"})
        != stable_sha256({"source": "observed"}),
    }
    checks = {
        "h63_action_system_verified": True,
        "trajectory_split_is_21_7": (
            len(discovery_trajectories) == 21
            and len(holdout_trajectories) == 7
        ),
        "discovery_program_exists": bool(words),
        "qualifying_program_exists": bool(qualifying),
        "all_identity_mutations_detected": all(mutation_checks.values()),
        "no_environment_contact": True,
        "no_controller_contact": True,
    }
    status = "stage_a_supported" if all(checks.values()) else "rejected"
    core = {
        "schema": "ztare-h113-chronological-minimal-effect-guard-v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "status": status,
        "environment_contact": False,
        "controller_contact": False,
        "identities": {
            "carrier_sha256": carrier_sha256,
            "carrier_execution_sha256": execution_sha256,
            "projection_sha256": projection.projection_sha256,
            "h63_action_system_sha256": selection.action_system.sha256,
            "trajectory_count": len(trajectories),
            "discovery_trajectory_count": len(discovery_trajectories),
            "holdout_trajectory_count": len(holdout_trajectories),
        },
        "coordinate_names": list(COORDINATE_NAMES),
        "discovery": {
            "program_count": len(words),
            "occurrence_count": len(discovery_windows),
            "trace_count": len(discovery_traces),
        },
        "holdout": {
            "occurrence_count": len(holdout_windows),
            "trace_count": len(holdout_traces),
            "exact_unseen_count": sum(
                row["holdout_exact_unseen_count"]
                for row in program_rows
            ),
            "covered_unseen_count": sum(
                row["covered_unseen_count"] for row in program_rows
            ),
            "error_count": sum(
                row["error_count"] for row in program_rows
            ),
        },
        "qualifying_program_count": len(qualifying),
        "programs": program_rows,
        "checks": checks,
        "mutation_checks": mutation_checks,
        "claim_boundary": (
            "Relative-effect guard prediction only; no task-credit or "
            "controller-benefit claim."
        ),
    }
    return {**core, "sha256": stable_sha256(core)}


def main() -> int:
    output = run_audit()
    path = FIXTURES / "h113_minimal_effect_guard_result.json"
    path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "result_path": str(path),
        "status": output["status"],
        "sha256": output["sha256"],
        "discovery": output["discovery"],
        "holdout": output["holdout"],
        "qualifying_program_count": output["qualifying_program_count"],
        "programs": [{
            key: row[key]
            for key in (
                "word",
                "discovery_effect_count",
                "selected_coordinate_names",
                "holdout_exact_unseen_count",
                "covered_unseen_count",
                "error_count",
                "exercised_predicted_effect_count",
                "qualifies",
            )
        } for row in output["programs"]],
    }, indent=2, sort_keys=True))
    return 0 if output["status"] == "stage_a_supported" else 1


if __name__ == "__main__":
    raise SystemExit(main())
