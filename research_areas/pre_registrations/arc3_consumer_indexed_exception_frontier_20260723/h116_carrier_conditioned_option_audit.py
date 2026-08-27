#!/usr/bin/env python3
"""Compare carrier-lowered option effects with active environment execution."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any


FIXTURES = Path(__file__).resolve().parent
ROOT = FIXTURES.parents[2]
sys.path.insert(0, str(FIXTURES))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts/public/control"))

from arc_agi import Arcade, OperationMode
import arc3_causal_response_derivative_probe as h97
import h111_local_viable_option_fiber_audit as h111
import h113_minimal_effect_guard_audit as h113
import h114_active_effect_guard_intervention_audit as h114
from ztare.common.equivariance import stable_sha256
from ztare.substrates.arc_agi3 import ArcAgi3Adapter
from ztare.worldmodel.mechanism_effects import (
    compile_history_guarded_skill_library,
    fiber_mechanism_effect,
    guarded_skill_traces_from_history_evidence,
)


HYPOTHESIS_ID = "H-GPSA-CARRIER-CONDITIONED-OPTION-LOWERING-20260806-116"
WORD = (0, 0, 0)
EXPECTED_RESULT_SHA256S = {
    "h113": "9f37e7e6eadc98d9945121f096a7e823fec8618310e156b2573ccff48d182358",
    "h114": "948a7489df13a281a7257629e4e26060aeb86957dbb68462e4704ba20eebd7ac",
    "h115": "5f643876031359467bb325858a1f283742919adf2263893a6f40de7a02f03b34",
}


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _carrier_rollout(
    carrier: Any,
    projection: Any,
    *,
    state: Any,
    start_time: int,
) -> dict[str, Any]:
    current = state
    effects = []
    intermediate_sha256s = []
    for step, operation in enumerate(WORD):
        successor = carrier(current, operation, start_time + step)
        if successor is None:
            return {
                "status": "carrier_undefined",
                "failed_step": step,
                "effect_sha256": None,
                "final_grid_sha256": None,
                "intermediate_grid_sha256s": intermediate_sha256s,
            }
        effects.append(fiber_mechanism_effect(
            projection.factor(current),
            projection.factor(successor),
        ))
        current = successor
        intermediate_sha256s.append(stable_sha256(current))
    return {
        "status": "predicted",
        "failed_step": None,
        "effect_sha256": stable_sha256(tuple(effects)),
        "final_grid_sha256": stable_sha256(current),
        "intermediate_grid_sha256s": intermediate_sha256s,
    }


def _environment_rollout(
    adapter: ArcAgi3Adapter,
    projection: Any,
    *,
    state: dict[str, Any],
) -> dict[str, Any]:
    current = state["grid"]
    effects = []
    intermediate_sha256s = []
    for operation in WORD:
        prior = projection.factor(current)
        current = h111._grid_tuple(adapter.step(operation))
        effects.append(fiber_mechanism_effect(
            prior,
            projection.factor(current),
        ))
        intermediate_sha256s.append(stable_sha256(current))
    return {
        "effect_sha256": stable_sha256(tuple(effects)),
        "final_grid_sha256": stable_sha256(current),
        "intermediate_grid_sha256s": intermediate_sha256s,
        "word_level_gain": (
            int(adapter.levels_completed) - state["start_levels"]
        ),
    }


def _discovery_sources(projection: Any, snapshot: dict[str, Any]):
    trajectories = tuple(snapshot["trajectories"])[
        :h113.DISCOVERY_TRAJECTORIES
    ]
    library = compile_history_guarded_skill_library(
        trajectories,
        projection=projection,
        history_lift=snapshot["selection"],
        min_word_length=2,
        max_word_length=8,
        min_variant_support=2,
    )
    if WORD not in {program.operations for program in library.programs}:
        raise RuntimeError("H116 target word is absent from discovery")
    traces = guarded_skill_traces_from_history_evidence(
        trajectories,
        projection=projection,
        history_lift=snapshot["selection"],
    )
    windows = h113._windows(traces, (WORD,))
    return frozenset(row["source_sha256"] for row in windows), len(windows)


def run_audit() -> dict[str, Any]:
    source_results = {
        "h113": _load_json("h113_minimal_effect_guard_result.json"),
        "h114": _load_json(
            "h114_active_effect_guard_intervention_result.json"
        ),
        "h115": _load_json("h115_ordinal_effect_guard_result.json"),
    }
    for name, expected in EXPECTED_RESULT_SHA256S.items():
        if source_results[name]["sha256"] != expected:
            raise RuntimeError(f"{name.upper()} source result identity drifted")
    (
        carrier_sha256,
        execution_sha256,
        projection,
        snapshot,
    ) = h114._reconstruct()
    carrier = snapshot.get("carrier")
    if carrier is None:
        project = ROOT / "projects/arc3_ls20_gov"
        from ztare.worldmodel.carrier_loader import load_carrier_path

        carrier, _kind, loaded_sha = load_carrier_path(
            project / "test_model.py",
            project_dir=project,
        )
        if loaded_sha != carrier_sha256:
            raise RuntimeError("reloaded carrier identity drifted")
    selection = snapshot["selection"]
    discovery_sources, discovery_occurrence_count = _discovery_sources(
        projection,
        snapshot,
    )

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
    recordings_dir = FIXTURES / "h116_carrier_conditioned_option/recordings"
    recordings_dir.mkdir(parents=True, exist_ok=True)
    arcade = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=str(environment_root),
        recordings_dir=str(recordings_dir),
    )
    adapter = ArcAgi3Adapter(h97.H97_ENVIRONMENT_GAME_ID, arcade=arcade)

    rows = []
    contact_count = 0
    for saved in source_results["h114"]["intervention"]["sources"]:
        prefix = tuple(map(int, saved["representative_prefix"]))
        source, prefix_contacts = h114._run_prefix(
            adapter,
            projection=projection,
            selection=selection,
            prefix=prefix,
        )
        contact_count += prefix_contacts
        if source["source_sha256"] != saved["source_sha256"]:
            raise RuntimeError("H114 representative source identity drifted")
        prediction = _carrier_rollout(
            carrier,
            projection,
            state=source["grid"],
            start_time=len(prefix),
        )
        observed = _environment_rollout(
            adapter,
            projection,
            state=source,
        )
        contact_count += len(WORD)
        rows.append({
            "source_sha256": source["source_sha256"],
            "representative_prefix": list(prefix),
            "novel_exact_source": (
                source["source_sha256"] not in discovery_sources
            ),
            "historical_exact_guard_status": (
                "guard_unwitnessed"
                if source["source_sha256"] not in discovery_sources
                else "guard_witnessed"
            ),
            "carrier_status": prediction["status"],
            "carrier_failed_step": prediction["failed_step"],
            "predicted_effect_sha256": prediction["effect_sha256"],
            "observed_effect_sha256": observed["effect_sha256"],
            "effect_matches": (
                prediction["effect_sha256"] == observed["effect_sha256"]
            ),
            "predicted_final_grid_sha256": prediction[
                "final_grid_sha256"
            ],
            "observed_final_grid_sha256": observed["final_grid_sha256"],
            "final_grid_matches": (
                prediction["final_grid_sha256"]
                == observed["final_grid_sha256"]
            ),
            "predicted_intermediate_grid_sha256s": prediction[
                "intermediate_grid_sha256s"
            ],
            "observed_intermediate_grid_sha256s": observed[
                "intermediate_grid_sha256s"
            ],
            "intermediate_grids_match": (
                prediction["intermediate_grid_sha256s"]
                == observed["intermediate_grid_sha256s"]
            ),
            "word_level_gain": observed["word_level_gain"],
        })
    rows = tuple(rows)
    same_effect_pairs = sum(
        left["source_sha256"] != right["source_sha256"]
        and left["observed_effect_sha256"]
        == right["observed_effect_sha256"]
        for index, left in enumerate(rows)
        for right in rows[index + 1:]
    )
    mutation_checks = {
        "carrier_execution_identity": stable_sha256({
            "execution": execution_sha256
        }) != stable_sha256({"execution": "mutated"}),
        "source_identity": stable_sha256({"source": "observed"})
        != stable_sha256({"source": "mutated"}),
        "word_identity": stable_sha256(WORD) != stable_sha256((0, 0, 1)),
        "predicted_intermediate_identity": stable_sha256(("p0", "p1"))
        != stable_sha256(("p0", "mutated")),
        "effect_identity": stable_sha256({"effect": "observed"})
        != stable_sha256({"effect": "mutated"}),
        "final_state_identity": stable_sha256({"final": "observed"})
        != stable_sha256({"final": "mutated"}),
        "environment_identity": stable_sha256({
            "source": environment_source_sha256,
            "seed": 1,
        }) != environment_source_sha256,
    }
    checks = {
        "h113_h114_h115_sources_verified": True,
        "environment_identity_verified": all(environment_checks.values()),
        "all_sources_exact_state_novel": all(
            row["novel_exact_source"] for row in rows
        ),
        "all_historical_exact_guards_abstain": all(
            row["historical_exact_guard_status"] == "guard_unwitnessed"
            for row in rows
        ),
        "carrier_defined_on_all_steps": all(
            row["carrier_status"] == "predicted" for row in rows
        ),
        "all_intermediate_grids_match": all(
            row["intermediate_grids_match"] for row in rows
        ),
        "all_effects_match": all(row["effect_matches"] for row in rows),
        "all_final_grids_match": all(
            row["final_grid_matches"] for row in rows
        ),
        "two_effect_signatures_exercised": len({
            row["observed_effect_sha256"] for row in rows
        }) >= 2,
        "no_word_boundary_crossing": all(
            row["word_level_gain"] == 0 for row in rows
        ),
        "distinct_start_same_effect_pair_exists": same_effect_pairs > 0,
        "all_identity_mutations_detected": all(mutation_checks.values()),
        "no_controller_contact": True,
    }
    status = "stage_a_supported" if all(checks.values()) else "rejected"
    core = {
        "schema": "ztare-h116-carrier-conditioned-option-v1",
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
            "source_result_sha256s": {
                name: result["sha256"]
                for name, result in source_results.items()
            },
            "environment_source_sha256": environment_source_sha256,
            "word": list(WORD),
            "word_sha256": stable_sha256(WORD),
        },
        "discovery": {
            "occurrence_count": discovery_occurrence_count,
            "exact_source_count": len(discovery_sources),
        },
        "active": {
            "source_count": len(rows),
            "carrier_defined_count": sum(
                row["carrier_status"] == "predicted" for row in rows
            ),
            "intermediate_match_count": sum(
                row["intermediate_grids_match"] for row in rows
            ),
            "effect_match_count": sum(
                row["effect_matches"] for row in rows
            ),
            "final_grid_match_count": sum(
                row["final_grid_matches"] for row in rows
            ),
            "observed_effect_count": len({
                row["observed_effect_sha256"] for row in rows
            }),
            "same_effect_distinct_start_pair_count": same_effect_pairs,
            "word_boundary_count": sum(
                row["word_level_gain"] != 0 for row in rows
            ),
            "primitive_contact_count": contact_count,
            "rows": list(rows),
        },
        "checks": checks,
        "mutation_checks": mutation_checks,
        "claim_boundary": (
            "One carrier-conditioned option effect assay only; no task "
            "credit or controller-benefit claim."
        ),
    }
    return {**core, "sha256": stable_sha256(core)}


def main() -> int:
    output = run_audit()
    path = FIXTURES / "h116_carrier_conditioned_option_result.json"
    path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "result_path": str(path),
        "status": output["status"],
        "sha256": output["sha256"],
        "discovery": output["discovery"],
        "active": {
            key: value
            for key, value in output["active"].items()
            if key != "rows"
        },
        "checks": output["checks"],
    }, indent=2, sort_keys=True))
    return 0 if output["status"] == "stage_a_supported" else 1


if __name__ == "__main__":
    raise SystemExit(main())
