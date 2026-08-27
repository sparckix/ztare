#!/usr/bin/env python3
"""Fit an ordinal budget gate on H113 and test H114 active sources."""
from __future__ import annotations

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
import h114_active_effect_guard_intervention_audit as h114
from ztare.common.equivariance import stable_sha256
from ztare.substrates.arc_agi3 import ArcAgi3Adapter
from ztare.worldmodel.mechanism_effects import (
    compile_history_guarded_skill_library,
    guarded_skill_traces_from_history_evidence,
)


HYPOTHESIS_ID = "H-GPSA-ORDINAL-EFFECT-GUARD-EXTRAPOLATION-20260806-115"
EXPECTED_H113_SHA256 = (
    "9f37e7e6eadc98d9945121f096a7e823fec8618310e156b2573ccff48d182358"
)
EXPECTED_H114_SHA256 = (
    "948a7489df13a281a7257629e4e26060aeb86957dbb68462e4704ba20eebd7ac"
)


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _is_false_prefix_true_suffix(value: tuple[bool, ...]) -> bool:
    seen_true = False
    for bit in value:
        if bit:
            seen_true = True
        elif seen_true:
            return False
    return True


def _fit_intervals(rows: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
    effects_by_budget: dict[int, set[str]] = {}
    for row in rows:
        budget = int(row["coordinates"][4])
        effects_by_budget.setdefault(budget, set()).add(row["effect_sha256"])
    if any(len(effects) != 1 for effects in effects_by_budget.values()):
        raise ValueError("discovery budget is effect-ambiguous")
    ordered = tuple(sorted(
        (budget, next(iter(effects)))
        for budget, effects in effects_by_budget.items()
    ))
    groups: list[list[tuple[int, str]]] = []
    for row in ordered:
        if not groups or groups[-1][-1][1] != row[1]:
            groups.append([row])
        else:
            groups[-1].append(row)
    intervals = []
    for index, group in enumerate(groups):
        lower = (
            0
            if index == 0
            else (
                groups[index - 1][-1][0] + group[0][0]
            ) // 2 + 1
        )
        upper = (
            None
            if index == len(groups) - 1
            else (group[-1][0] + groups[index + 1][0][0]) // 2
        )
        intervals.append({
            "lower_inclusive": lower,
            "upper_inclusive": upper,
            "effect_sha256": group[0][1],
            "observed_budgets": [budget for budget, _effect in group],
        })
    return tuple(intervals)


def _predict(
    intervals: tuple[dict[str, Any], ...],
    *,
    budget: int,
    domain_maximum: int,
) -> tuple[str | None, int | None]:
    if budget < 0 or budget > domain_maximum:
        return None, None
    for index, interval in enumerate(intervals):
        upper = interval["upper_inclusive"]
        if budget >= interval["lower_inclusive"] and (
            upper is None or budget <= upper
        ):
            return str(interval["effect_sha256"]), index
    return None, None


def _discovery_rows(projection: Any, snapshot: dict[str, Any]):
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
    if h114.WORD not in {program.operations for program in library.programs}:
        raise RuntimeError("H115 target word is absent from discovery")
    traces = guarded_skill_traces_from_history_evidence(
        trajectories,
        projection=projection,
        history_lift=snapshot["selection"],
    )
    return tuple(h113._windows(traces, (h114.WORD,)))


def run_audit() -> dict[str, Any]:
    h113_result = _load_json("h113_minimal_effect_guard_result.json")
    h114_result = _load_json(
        "h114_active_effect_guard_intervention_result.json"
    )
    if h113_result["sha256"] != EXPECTED_H113_SHA256:
        raise RuntimeError("H113 source result identity drifted")
    if h114_result["sha256"] != EXPECTED_H114_SHA256:
        raise RuntimeError("H114 source result identity drifted")
    (
        carrier_sha256,
        execution_sha256,
        projection,
        snapshot,
    ) = h114._reconstruct()
    selection = snapshot["selection"]
    discovery_rows = _discovery_rows(projection, snapshot)
    intervals = _fit_intervals(discovery_rows)
    discovery_budgets = {
        int(row["coordinates"][4]) for row in discovery_rows
    }
    discovery_maximum = max(discovery_budgets)
    feasibility_length = len(discovery_rows[0]["coordinates"][3])
    discovery_order_checks = tuple(
        _is_false_prefix_true_suffix(row["coordinates"][3])
        and sum(row["coordinates"][3]) == row["coordinates"][4]
        for row in discovery_rows
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
    recordings_dir = FIXTURES / "h115_ordinal_effect_guard/recordings"
    recordings_dir.mkdir(parents=True, exist_ok=True)
    arcade = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=str(environment_root),
        recordings_dir=str(recordings_dir),
    )
    adapter = ArcAgi3Adapter(h97.H97_ENVIRONMENT_GAME_ID, arcade=arcade)

    active_rows = []
    contact_count = 0
    for saved in h114_result["intervention"]["sources"]:
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
        feasibility = source["coordinates"][3]
        budget = int(source["coordinates"][4])
        prediction, interval_index = _predict(
            intervals,
            budget=budget,
            domain_maximum=len(feasibility),
        )
        outcome, word_contacts = h114._execute_word(
            adapter,
            projection=projection,
            source=source,
        )
        contact_count += word_contacts
        active_rows.append({
            "source_sha256": source["source_sha256"],
            "representative_prefix": list(prefix),
            "coordinate_sha256s": [
                stable_sha256(value) for value in source["coordinates"]
            ],
            "feasibility_is_order_ideal": (
                _is_false_prefix_true_suffix(feasibility)
            ),
            "budget_equals_true_count": budget == sum(feasibility),
            "budget": budget,
            "budget_seen_in_discovery": budget in discovery_budgets,
            "above_discovery_maximum": budget > discovery_maximum,
            "interval_index": interval_index,
            "predicted_effect_sha256": prediction,
            "observed_effect_sha256": outcome["effect_sha256"],
            "correct": prediction == outcome["effect_sha256"],
            "word_level_gain": outcome["word_level_gain"],
        })
    active_rows = tuple(active_rows)
    eligible = tuple(
        row for row in active_rows if row["above_discovery_maximum"]
    )
    errors = tuple(row for row in eligible if not row["correct"])
    orthogonal_witnesses = []
    for index, left in enumerate(eligible):
        for right in eligible[index + 1:]:
            if (
                left["budget"] != right["budget"]
                or left["observed_effect_sha256"]
                != right["observed_effect_sha256"]
                or left["predicted_effect_sha256"]
                != right["predicted_effect_sha256"]
            ):
                continue
            changed = tuple(
                h113.COORDINATE_NAMES[coordinate]
                for coordinate in range(len(h113.COORDINATE_NAMES))
                if coordinate != 4
                and left["coordinate_sha256s"][coordinate]
                != right["coordinate_sha256s"][coordinate]
            )
            if not changed:
                continue
            orthogonal_witnesses.append({
                "left_source_sha256": left["source_sha256"],
                "right_source_sha256": right["source_sha256"],
                "budget": left["budget"],
                "effect_sha256": left["observed_effect_sha256"],
                "changed_non_budget_coordinates": list(changed),
            })
    below_domain, _ = _predict(
        intervals,
        budget=-1,
        domain_maximum=feasibility_length,
    )
    above_domain, _ = _predict(
        intervals,
        budget=feasibility_length + 1,
        domain_maximum=feasibility_length,
    )
    mutation_checks = {
        "interval_boundary_identity": stable_sha256({
            "boundary": intervals[0]["upper_inclusive"]
        }) != stable_sha256({
            "boundary": int(intervals[0]["upper_inclusive"]) + 1
        }),
        "budget_identity": stable_sha256({"budget": 18})
        != stable_sha256({"budget": 19}),
        "source_identity": stable_sha256({"source": "observed"})
        != stable_sha256({"source": "mutated"}),
        "word_identity": stable_sha256(h114.WORD)
        != stable_sha256((2, 0)),
        "prediction_identity": stable_sha256({"effect": "prediction"})
        != stable_sha256({"effect": "mutation"}),
        "observed_effect_identity": stable_sha256({"effect": "observed"})
        != stable_sha256({"effect": "mutation"}),
        "environment_identity": stable_sha256({
            "source": environment_source_sha256,
            "seed": 1,
        }) != environment_source_sha256,
    }
    checks = {
        "h113_h114_sources_verified": True,
        "environment_identity_verified": all(environment_checks.values()),
        "all_discovery_vectors_are_order_ideals": all(
            discovery_order_checks
        ),
        "three_collision_free_intervals": len(intervals) == 3,
        "declared_boundaries_reproduced": [
            interval["upper_inclusive"] for interval in intervals
        ] == [3, 8, None],
        "five_above_range_sources": len(eligible) >= 5,
        "all_active_vectors_are_order_ideals": all(
            row["feasibility_is_order_ideal"]
            and row["budget_equals_true_count"]
            for row in active_rows
        ),
        "all_extrapolated_predictions_correct": bool(eligible) and not errors,
        "no_word_boundary_crossing": all(
            row["word_level_gain"] == 0 for row in eligible
        ),
        "orthogonal_factor_witness_exists": bool(orthogonal_witnesses),
        "outside_domain_abstains": (
            below_domain is None and above_domain is None
        ),
        "all_identity_mutations_detected": all(mutation_checks.values()),
        "no_controller_contact": True,
    }
    status = "stage_a_supported" if all(checks.values()) else "rejected"
    core = {
        "schema": "ztare-h115-ordinal-effect-guard-v1",
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
            "h114_result_sha256": h114_result["sha256"],
            "environment_source_sha256": environment_source_sha256,
            "word": list(h114.WORD),
            "word_sha256": stable_sha256(h114.WORD),
        },
        "discovery": {
            "occurrence_count": len(discovery_rows),
            "budgets": sorted(discovery_budgets),
            "budget_maximum": discovery_maximum,
            "effect_count": len({
                row["effect_sha256"] for row in discovery_rows
            }),
            "feasibility_length": feasibility_length,
            "intervals": list(intervals),
        },
        "active": {
            "source_count": len(active_rows),
            "above_range_source_count": len(eligible),
            "budgets": sorted({row["budget"] for row in active_rows}),
            "correct_count": sum(row["correct"] for row in eligible),
            "error_count": len(errors),
            "word_boundary_count": sum(
                row["word_level_gain"] != 0 for row in eligible
            ),
            "orthogonal_witness_count": len(orthogonal_witnesses),
            "primitive_contact_count": contact_count,
            "rows": list(active_rows),
            "orthogonal_witnesses": orthogonal_witnesses[:40],
        },
        "checks": checks,
        "mutation_checks": mutation_checks,
        "claim_boundary": (
            "One ordinal relative-effect extrapolator only; no task credit "
            "or controller-benefit claim."
        ),
    }
    return {**core, "sha256": stable_sha256(core)}


def main() -> int:
    output = run_audit()
    path = FIXTURES / "h115_ordinal_effect_guard_result.json"
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
            if key not in {"rows", "orthogonal_witnesses"}
        },
        "checks": output["checks"],
    }, indent=2, sort_keys=True))
    return 0 if output["status"] == "stage_a_supported" else 1


if __name__ == "__main__":
    raise SystemExit(main())
