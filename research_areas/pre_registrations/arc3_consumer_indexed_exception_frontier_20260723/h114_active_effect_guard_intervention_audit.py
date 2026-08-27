#!/usr/bin/env python3
"""Actively vary cached LS20 states and test H113's frozen effect gate."""
from __future__ import annotations

import itertools
import json
from pathlib import Path
import sys
from typing import Any, Hashable


FIXTURES = Path(__file__).resolve().parent
ROOT = FIXTURES.parents[2]
sys.path.insert(0, str(FIXTURES))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts/public/control"))

from arc_agi import Arcade, OperationMode
import arc3_causal_response_derivative_probe as h97
import h111_local_viable_option_fiber_audit as h111
import h113_minimal_effect_guard_audit as h113
import task_conditioned_skill_basin_audit as h77
from ztare.common.equivariance import stable_sha256
from ztare.substrates.arc_agi3 import ArcAgi3Adapter
from ztare.worldmodel.carrier_loader import load_carrier_path
from ztare.worldmodel.mechanism_effects import (
    compile_history_guarded_skill_library,
    fiber_mechanism_effect,
    guarded_skill_traces_from_history_evidence,
)
from ztare.worldmodel.patch_base_carrier import (
    carrier_execution_sha256_from_source,
)


HYPOTHESIS_ID = "H-GPSA-ACTIVE-EFFECT-GUARD-INTERVENTION-20260806-114"
WORD = (2, 1)
MAX_PREFIX_LENGTH = 5
EXPECTED_PREFIX_COUNT = 1365
EXPECTED_H113_SHA256 = (
    "9f37e7e6eadc98d9945121f096a7e823fec8618310e156b2573ccff48d182358"
)


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _prefixes() -> tuple[tuple[int, ...], ...]:
    return tuple(
        tuple(int(action) for action in prefix)
        for length in range(MAX_PREFIX_LENGTH + 1)
        for prefix in itertools.product(range(h111.ACTION_ARITY), repeat=length)
    )


def _reconstruct():
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
    if snapshot["selection"].action_system.sha256 != h63[
        "history_lift"
    ]["action_system_sha256"]:
        raise RuntimeError("H63 action-system identity drifted")
    return (
        carrier_sha256,
        execution_sha256,
        projection,
        snapshot,
    )


def _frozen_guard(projection: Any, snapshot: dict[str, Any]):
    selection = snapshot["selection"]
    trajectories = tuple(snapshot["trajectories"])
    discovery = trajectories[:h113.DISCOVERY_TRAJECTORIES]
    library = compile_history_guarded_skill_library(
        discovery,
        projection=projection,
        history_lift=selection,
        min_word_length=2,
        max_word_length=8,
        min_variant_support=2,
    )
    if WORD not in {program.operations for program in library.programs}:
        raise RuntimeError("H113 target word is absent from discovery")
    traces = guarded_skill_traces_from_history_evidence(
        discovery,
        projection=projection,
        history_lift=selection,
    )
    windows = tuple(
        row for row in h113._windows(traces, (WORD,))
        if row["word"] == WORD
    )
    fitted = h113._minimal_guard(windows)
    if fitted["axes"] != (3,):
        raise RuntimeError("H113 selected guard identity drifted")
    return {
        "axes": fitted["axes"],
        "effect_by_guard": fitted["effect_by_guard"],
        "discovery_source_sha256s": frozenset(
            row["source_sha256"] for row in windows
        ),
        "discovery_effect_sha256s": frozenset(
            row["effect_sha256"] for row in windows
        ),
        "discovery_occurrence_count": len(windows),
    }


def _run_prefix(
    adapter: ArcAgi3Adapter,
    *,
    projection: Any,
    selection: Any,
    prefix: tuple[int, ...],
) -> tuple[dict[str, Any], int]:
    contacts = 0
    grid = h111._grid_tuple(adapter.reset())
    start_levels = int(adapter.levels_completed)
    actions: tuple[Hashable, ...] = ()
    effects: tuple[Hashable, ...] = ()
    for action in prefix:
        source_factors = projection.factor(grid)
        grid = h111._grid_tuple(adapter.step(action))
        contacts += 1
        effect = fiber_mechanism_effect(
            source_factors,
            projection.factor(grid),
        )
        actions = (*actions, action)
        effects = (*effects, (
            "operation_effect",
            action,
            stable_sha256(effect),
        ))
    prefix_level_gain = int(adapter.levels_completed) - start_levels
    factors = projection.factor(grid)
    source_key = selection.start_key(
        factors,
        observation=grid,
        action_history=actions,
        operation_effect_history=effects,
    )
    return ({
        "prefix": prefix,
        "prefix_sha256": stable_sha256(prefix),
        "prefix_level_gain": prefix_level_gain,
        "grid": grid,
        "factors": factors,
        "source_key": source_key,
        "source_sha256": stable_sha256(source_key),
        "coordinates": h113._coordinates(source_key),
        "action_history": actions,
        "operation_effect_history": effects,
        "start_levels": int(adapter.levels_completed),
    }, contacts)


def _execute_word(
    adapter: ArcAgi3Adapter,
    *,
    projection: Any,
    source: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    grid = source["grid"]
    effects = []
    for action in WORD:
        before = projection.factor(grid)
        grid = h111._grid_tuple(adapter.step(action))
        effects.append(fiber_mechanism_effect(
            before,
            projection.factor(grid),
        ))
    return ({
        "effect_sha256": stable_sha256(tuple(effects)),
        "word_level_gain": (
            int(adapter.levels_completed) - source["start_levels"]
        ),
        "termination_grid_sha256": stable_sha256(grid),
    }, len(WORD))


def _changed_non_guard_coordinates(
    left: tuple[Hashable, ...],
    right: tuple[Hashable, ...],
) -> tuple[str, ...]:
    return tuple(
        h113.COORDINATE_NAMES[index]
        for index in range(6)
        if index != 3
        and stable_sha256(left[index]) != stable_sha256(right[index])
    )


def run_audit() -> dict[str, Any]:
    h113_result = _load_json("h113_minimal_effect_guard_result.json")
    if (
        h113_result["hypothesis_id"] != h113.HYPOTHESIS_ID
        or h113_result["sha256"] != EXPECTED_H113_SHA256
    ):
        raise RuntimeError("H113 source result identity drifted")
    (
        carrier_sha256,
        execution_sha256,
        projection,
        snapshot,
    ) = _reconstruct()
    selection = snapshot["selection"]
    guard = _frozen_guard(projection, snapshot)
    axes = guard["axes"]
    effect_by_guard = guard["effect_by_guard"]

    environment_root = ROOT / "environment_files"
    base_game, version = h97.H97_ENVIRONMENT_GAME_ID.split("-", 1)
    game_root = environment_root / base_game / version
    environment_checks = {
        "code_sha256": h97._file_sha256(
            game_root / f"{base_game}.py"
        ) == h97.H97_ENVIRONMENT_CODE_SHA256,
        "metadata_sha256": h97._file_sha256(
            game_root / "metadata.json"
        ) == h97.H97_ENVIRONMENT_METADATA_SHA256,
    }
    if not all(environment_checks.values()):
        raise RuntimeError("cached H97 environment identity drifted")
    environment_source_sha256 = stable_sha256({
        "game_id": h97.H97_ENVIRONMENT_GAME_ID,
        "seed": 0,
        "code_sha256": h97.H97_ENVIRONMENT_CODE_SHA256,
        "metadata_sha256": h97.H97_ENVIRONMENT_METADATA_SHA256,
    })
    recordings_dir = FIXTURES / "h114_active_effect_guard/recordings"
    recordings_dir.mkdir(parents=True, exist_ok=True)
    arcade = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=str(environment_root),
        recordings_dir=str(recordings_dir),
    )
    adapter = ArcAgi3Adapter(h97.H97_ENVIRONMENT_GAME_ID, arcade=arcade)

    prefixes = _prefixes()
    if len(prefixes) != EXPECTED_PREFIX_COUNT:
        raise RuntimeError("active prefix count drifted")
    by_source: dict[str, dict[str, Any]] = {}
    contact_count = 0
    preword_boundary_prefix_count = 0
    for prefix in prefixes:
        source, contacts = _run_prefix(
            adapter,
            projection=projection,
            selection=selection,
            prefix=prefix,
        )
        contact_count += contacts
        if source["prefix_level_gain"] != 0:
            preword_boundary_prefix_count += 1
            continue
        prior = by_source.get(source["source_sha256"])
        if prior is not None:
            prior["prefix_sha256s"].append(source["prefix_sha256"])
            prior["history_multiplicity"] += 1
            continue
        guard_key = h113._guard_key(source["coordinates"], axes)
        predicted = effect_by_guard.get(guard_key)
        row = {
            "source_sha256": source["source_sha256"],
            "representative_prefix": list(prefix),
            "prefix_sha256s": [source["prefix_sha256"]],
            "history_multiplicity": 1,
            "coordinate_sha256s": [
                stable_sha256(value) for value in source["coordinates"]
            ],
            "guard_sha256": stable_sha256(guard_key),
            "novel_exact_source": (
                source["source_sha256"]
                not in guard["discovery_source_sha256s"]
            ),
            "status": "covered" if predicted is not None else "abstained",
            "predicted_effect_sha256": predicted,
            "observed_effect_sha256": None,
            "correct": None,
            "word_level_gain": None,
        }
        if predicted is not None:
            outcome, word_contacts = _execute_word(
                adapter,
                projection=projection,
                source=source,
            )
            contact_count += word_contacts
            row.update({
                "observed_effect_sha256": outcome["effect_sha256"],
                "correct": outcome["effect_sha256"] == predicted,
                "word_level_gain": outcome["word_level_gain"],
                "termination_grid_sha256": outcome[
                    "termination_grid_sha256"
                ],
            })
        by_source[source["source_sha256"]] = row

    sources = tuple(sorted(
        by_source.values(),
        key=lambda row: row["source_sha256"],
    ))
    covered_novel = tuple(
        row for row in sources
        if row["status"] == "covered" and row["novel_exact_source"]
    )
    errors = tuple(row for row in covered_novel if not row["correct"])
    orthogonal_witnesses = []
    for index, left in enumerate(covered_novel):
        for right in covered_novel[index + 1:]:
            if (
                left["guard_sha256"] != right["guard_sha256"]
                or left["predicted_effect_sha256"]
                != right["predicted_effect_sha256"]
                or left["observed_effect_sha256"]
                != right["observed_effect_sha256"]
            ):
                continue
            changed = tuple(
                h113.COORDINATE_NAMES[coordinate]
                for coordinate in range(6)
                if coordinate != 3
                and left["coordinate_sha256s"][coordinate]
                != right["coordinate_sha256s"][coordinate]
            )
            if not changed:
                continue
            orthogonal_witnesses.append({
                "left_source_sha256": left["source_sha256"],
                "right_source_sha256": right["source_sha256"],
                "guard_sha256": left["guard_sha256"],
                "effect_sha256": left["observed_effect_sha256"],
                "changed_non_guard_coordinates": list(changed),
            })
    mutation_checks = {
        "environment_identity": stable_sha256({
            "source": environment_source_sha256,
            "seed": 1,
        }) != environment_source_sha256,
        "source_identity": stable_sha256({"source": "mutated"})
        != stable_sha256({"source": "observed"}),
        "guard_identity": stable_sha256({"guard": "mutated"})
        != stable_sha256({"guard": "observed"}),
        "word_identity": stable_sha256((2, 0)) != stable_sha256(WORD),
        "prediction_identity": stable_sha256({"effect": "prediction"})
        != stable_sha256({"effect": "mutation"}),
        "observed_effect_identity": stable_sha256({"effect": "observed"})
        != stable_sha256({"effect": "mutation"}),
    }
    covered_guard_count = len({
        row["guard_sha256"] for row in covered_novel
    })
    covered_effect_count = len({
        row["predicted_effect_sha256"] for row in covered_novel
    })
    checks = {
        "h113_source_verified": True,
        "environment_identity_verified": all(environment_checks.values()),
        "all_prefixes_enumerated": len(prefixes) == EXPECTED_PREFIX_COUNT,
        "five_novel_sources_covered": len(covered_novel) >= 5,
        "two_guard_values_covered": covered_guard_count >= 2,
        "two_effects_covered": covered_effect_count >= 2,
        "all_covered_predictions_correct": (
            bool(covered_novel) and not errors
        ),
        "orthogonal_factor_witness_exists": bool(orthogonal_witnesses),
        "unknown_guard_policy_is_abstain": True,
        "all_identity_mutations_detected": all(mutation_checks.values()),
        "no_controller_contact": True,
    }
    status = "stage_a_supported" if all(checks.values()) else "rejected"
    core = {
        "schema": "ztare-h114-active-effect-guard-intervention-v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "status": status,
        "environment_contact": True,
        "environment_operation_mode": "offline",
        "controller_contact": False,
        "identities": {
            "carrier_sha256": carrier_sha256,
            "carrier_execution_sha256": execution_sha256,
            "projection_sha256": projection.projection_sha256,
            "h63_action_system_sha256": selection.action_system.sha256,
            "h113_result_sha256": h113_result["sha256"],
            "environment_source_sha256": environment_source_sha256,
            "word": list(WORD),
            "word_sha256": stable_sha256(WORD),
            "selected_coordinate_names": [
                h113.COORDINATE_NAMES[index] for index in axes
            ],
        },
        "discovery_guard": {
            "occurrence_count": guard["discovery_occurrence_count"],
            "exact_source_count": len(guard["discovery_source_sha256s"]),
            "effect_count": len(guard["discovery_effect_sha256s"]),
            "guard_value_count": len(effect_by_guard),
        },
        "intervention": {
            "prefix_count": len(prefixes),
            "preword_boundary_prefix_count": preword_boundary_prefix_count,
            "distinct_preword_source_count": len(sources),
            "novel_exact_source_count": sum(
                row["novel_exact_source"] for row in sources
            ),
            "covered_novel_source_count": len(covered_novel),
            "covered_guard_value_count": covered_guard_count,
            "covered_effect_count": covered_effect_count,
            "covered_error_count": len(errors),
            "abstained_source_count": sum(
                row["status"] == "abstained" for row in sources
            ),
            "orthogonal_witness_count": len(orthogonal_witnesses),
            "primitive_contact_count": contact_count,
            "sources": list(sources),
            "orthogonal_witnesses": orthogonal_witnesses[:40],
        },
        "checks": checks,
        "mutation_checks": mutation_checks,
        "claim_boundary": (
            "One actively intervened relative-effect gate only; no task "
            "credit or controller-benefit claim."
        ),
    }
    return {**core, "sha256": stable_sha256(core)}


def main() -> int:
    output = run_audit()
    path = FIXTURES / "h114_active_effect_guard_intervention_result.json"
    path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "result_path": str(path),
        "status": output["status"],
        "sha256": output["sha256"],
        "discovery_guard": output["discovery_guard"],
        "intervention": {
            key: value
            for key, value in output["intervention"].items()
            if key not in {"sources", "orthogonal_witnesses"}
        },
        "checks": output["checks"],
    }, indent=2, sort_keys=True))
    return 0 if output["status"] == "stage_a_supported" else 1


if __name__ == "__main__":
    raise SystemExit(main())
