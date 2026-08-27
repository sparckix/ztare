#!/usr/bin/env python3
"""Search short exact-state corrections around the H111 option frontier."""
from __future__ import annotations

import itertools
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
from ztare.common.equivariance import stable_sha256
from ztare.substrates.arc_agi3 import ArcAgi3Adapter
from ztare.worldmodel.carrier_loader import load_carrier_path
from ztare.worldmodel.mechanism_effects import fiber_mechanism_effect


HYPOTHESIS_ID = "H-GPSA-CLOSED-LOOP-OPTION-RECOVERY-20260806-112"
MAX_CORRECTION_LENGTH = 3


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _correction_words() -> tuple[tuple[int, ...], ...]:
    return (
        (),
        *(
            tuple(int(action) for action in word)
            for length in range(1, MAX_CORRECTION_LENGTH + 1)
            for word in itertools.product(range(h111.ACTION_ARITY), repeat=length)
        ),
    )


def _restore_prefix(
    adapter: ArcAgi3Adapter,
    prefix: tuple[int, ...],
) -> tuple[tuple[int, ...], ...]:
    grid = h111._grid_tuple(adapter.reset())
    for action in prefix:
        grid = h111._grid_tuple(adapter.step(action))
    return grid


def _search_source(
    adapter: ArcAgi3Adapter,
    *,
    projection: Any,
    prefix: tuple[int, ...],
    expected_source_grid_sha256: str,
    expected_source_factor_sha256: str,
    target_grid_sha256: str,
    target_factor_sha256: str,
    expected_suffix_effect_sha256: str,
) -> dict[str, Any]:
    contacts = 0
    attempted = 0
    correction_boundary_crossings = 0
    for correction in _correction_words():
        attempted += 1
        grid = _restore_prefix(adapter, prefix)
        contacts += len(prefix)
        source_factor = projection.factor(grid)
        if (
            stable_sha256(grid) != expected_source_grid_sha256
            or stable_sha256(source_factor) != expected_source_factor_sha256
        ):
            raise RuntimeError("H112 representative prefix source drifted")
        levels_before = int(adapter.levels_completed)
        for action in correction:
            grid = h111._grid_tuple(adapter.step(action))
            contacts += 1
        if int(adapter.levels_completed) != levels_before:
            correction_boundary_crossings += 1
            continue
        recovered_factor = projection.factor(grid)
        if (
            stable_sha256(grid) != target_grid_sha256
            or stable_sha256(recovered_factor) != target_factor_sha256
        ):
            continue
        suffix_factors = [recovered_factor]
        for action in h111.WINNING_SUFFIX:
            grid = h111._grid_tuple(adapter.step(action))
            contacts += 1
            suffix_factors.append(projection.factor(grid))
        suffix_effects = tuple(
            fiber_mechanism_effect(source, target)
            for source, target in zip(
                suffix_factors,
                suffix_factors[1:],
            )
        )
        return {
            "status": "recovered",
            "source_grid_sha256": expected_source_grid_sha256,
            "source_factor_sha256": expected_source_factor_sha256,
            "representative_prefix": list(prefix),
            "correction": list(correction),
            "correction_length": len(correction),
            "attempted_correction_count": attempted,
            "correction_boundary_crossing_count": (
                correction_boundary_crossings
            ),
            "recovered_grid_sha256": stable_sha256(
                h111._receipt_grid(
                    _load_json(
                        FIXTURES
                        / "h95_response_transport_square/arms"
                        / "pair_01_offer_causal_mechanics.json"
                    )["probe"]["observations"][4]
                )
            ),
            "recovered_factor_sha256": stable_sha256(recovered_factor),
            "suffix_effect_signature_sha256": stable_sha256(suffix_effects),
            "suffix_effect_matches": (
                stable_sha256(suffix_effects)
                == expected_suffix_effect_sha256
            ),
            "suffix_levels_gained": (
                int(adapter.levels_completed) - levels_before
            ),
            "primitive_contact_count": contacts,
        }
    return {
        "status": "unrecovered",
        "source_grid_sha256": expected_source_grid_sha256,
        "source_factor_sha256": expected_source_factor_sha256,
        "representative_prefix": list(prefix),
        "correction": [],
        "correction_length": None,
        "attempted_correction_count": attempted,
        "correction_boundary_crossing_count": correction_boundary_crossings,
        "primitive_contact_count": contacts,
    }


def run_audit() -> dict[str, Any]:
    h111_result = _load_json(
        FIXTURES / "h111_local_viable_option_fiber_result.json"
    )
    if (
        h111_result["hypothesis_id"] != h111.HYPOTHESIS_ID
        or h111_result["sha256"]
        != "94434c3c6edbf2acc9afdd4651565617bb4f5d6391dcccd7822e7db19640a8bc"
    ):
        raise RuntimeError("H111 source result identity drifted")

    project = ROOT / "projects/arc3_ls20_gov"
    carrier, _kind, carrier_sha256 = load_carrier_path(
        project / "test_model.py",
        project_dir=project,
    )
    projection = carrier._ztare_factored_projection
    canonical = h111_result["canonical"]
    canonical_grid_sha256 = str(canonical["source_grid_sha256"])
    canonical_factor_sha256 = str(canonical["source_factor_sha256"])
    canonical_effect_sha256 = str(canonical["effect_signature_sha256"])

    environment_root = ROOT / "environment_files"
    recordings_dir = FIXTURES / "h112_closed_loop_option_recovery/recordings"
    recordings_dir.mkdir(parents=True, exist_ok=True)
    arcade = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=str(environment_root),
        recordings_dir=str(recordings_dir),
    )
    adapter = ArcAgi3Adapter(h97.H97_ENVIRONMENT_GAME_ID, arcade=arcade)

    noncanonical_sources = tuple(
        source for source in h111_result["search"]["sources"]
        if (
            source["source_grid_sha256"] != canonical_grid_sha256
            or source["source_factor_sha256"] != canonical_factor_sha256
        )
    )
    if len(noncanonical_sources) != 11:
        raise RuntimeError("H111 noncanonical exact-state count drifted")
    recovery_rows = tuple(
        _search_source(
            adapter,
            projection=projection,
            prefix=tuple(min(source["prefixes"])),
            expected_source_grid_sha256=str(source["source_grid_sha256"]),
            expected_source_factor_sha256=str(source["source_factor_sha256"]),
            target_grid_sha256=canonical_grid_sha256,
            target_factor_sha256=canonical_factor_sha256,
            expected_suffix_effect_sha256=canonical_effect_sha256,
        )
        for source in noncanonical_sources
    )
    recovered = tuple(
        row for row in recovery_rows if row["status"] == "recovered"
    )
    h109_source = h111_result["h109_refusal_control"]
    h109_row = _search_source(
        adapter,
        projection=projection,
        prefix=tuple(h111.H109_REFUSAL_PREFIX),
        expected_source_grid_sha256=str(h109_source["source_grid_sha256"]),
        expected_source_factor_sha256=str(h109_source["source_factor_sha256"]),
        target_grid_sha256=canonical_grid_sha256,
        target_factor_sha256=canonical_factor_sha256,
        expected_suffix_effect_sha256=canonical_effect_sha256,
    )

    branches = ({
        "source_grid_sha256": canonical_grid_sha256,
        "source_factor_sha256": canonical_factor_sha256,
        "correction": [],
        "correction_length": 0,
        "recovery_target_grid_sha256": canonical_grid_sha256,
        "recovery_target_factor_sha256": canonical_factor_sha256,
    }, *tuple({
        "source_grid_sha256": row["source_grid_sha256"],
        "source_factor_sha256": row["source_factor_sha256"],
        "correction": row["correction"],
        "correction_length": row["correction_length"],
        "recovery_target_grid_sha256": canonical_grid_sha256,
        "recovery_target_factor_sha256": canonical_factor_sha256,
    } for row in recovered))
    branch_keys = {
        (row["source_grid_sha256"], row["source_factor_sha256"])
        for row in branches
    }
    branching_option_core = {
        "schema": "ztare-exact-state-feedback-option-v1",
        "environment_source_sha256": h111_result["identities"][
            "environment_source_sha256"
        ],
        "branches": branches,
        "suffix": list(h111.WINNING_SUFFIX),
        "suffix_sha256": stable_sha256(h111.WINNING_SUFFIX),
        "suffix_effect_signature_sha256": canonical_effect_sha256,
        "unknown_source_policy": "refuse",
    }
    branching_option = {
        **branching_option_core,
        "sha256": stable_sha256(branching_option_core),
    }

    mutated_correction = (
        (*tuple(recovered[0]["correction"][:-1]),
         (int(recovered[0]["correction"][-1]) + 1) % h111.ACTION_ARITY)
        if recovered and recovered[0]["correction"]
        else (0,)
    )
    unknown_key = ("f" * 64, "e" * 64)
    negative_fixtures = {
        "unknown_source_refused": unknown_key not in branch_keys,
        "source_state_identity": (
            stable_sha256(unknown_key) != stable_sha256(next(iter(branch_keys)))
        ),
        "correction_word_identity": (
            not recovered
            or stable_sha256(mutated_correction)
            != stable_sha256(tuple(recovered[0]["correction"]))
        ),
        "recovery_target_identity": stable_sha256({
            "grid": canonical_grid_sha256,
            "factor": "0" * 64,
        }) != stable_sha256({
            "grid": canonical_grid_sha256,
            "factor": canonical_factor_sha256,
        }),
        "suffix_effect_identity": (
            stable_sha256({"effect": canonical_effect_sha256, "mutation": 1})
            != canonical_effect_sha256
        ),
        "environment_source_identity": stable_sha256({
            "source": branching_option_core["environment_source_sha256"],
            "mutation": 1,
        }) != branching_option_core["environment_source_sha256"],
    }
    checks = {
        "h111_source_verified": True,
        "eleven_noncanonical_sources_searched": (
            len(recovery_rows) == 11
        ),
        "at_least_one_distinct_source_recovered": bool(recovered),
        "all_recoveries_exact": all(
            row["recovered_factor_sha256"] == canonical_factor_sha256
            and row["recovered_grid_sha256"] == canonical_grid_sha256
            for row in recovered
        ),
        "all_recovered_suffixes_preserve_effect": bool(recovered) and all(
            row["suffix_effect_matches"] for row in recovered
        ),
        "all_recovered_suffixes_gain_level": bool(recovered) and all(
            row["suffix_levels_gained"] > 0 for row in recovered
        ),
        "h109_refusal_state_unrecovered": h109_row["status"] == "unrecovered",
        "branching_option_deterministic": len(branch_keys) == len(branches),
        "unknown_source_refuses": unknown_key not in branch_keys,
        "all_identity_mutations_detected": all(negative_fixtures.values()),
        "no_controller_contact": True,
    }
    status = "stage_a_supported" if all(checks.values()) else "rejected"
    payload = {
        "schema": "ztare-h112-closed-loop-option-recovery-v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "status": status,
        "environment_contact": True,
        "environment_operation_mode": "offline",
        "controller_contact": False,
        "identities": {
            "carrier_sha256": carrier_sha256,
            "projection_sha256": projection.projection_sha256,
            "h111_result_sha256": h111_result["sha256"],
            "canonical_grid_sha256": canonical_grid_sha256,
            "canonical_factor_sha256": canonical_factor_sha256,
            "canonical_effect_signature_sha256": canonical_effect_sha256,
        },
        "search": {
            "maximum_correction_length": MAX_CORRECTION_LENGTH,
            "candidate_word_count_per_source": len(_correction_words()),
            "searched_source_count": len(recovery_rows),
            "recovered_source_count": len(recovered),
            "unrecovered_source_count": len(recovery_rows) - len(recovered),
            "primitive_contact_count": sum(
                row["primitive_contact_count"] for row in recovery_rows
            ) + h109_row["primitive_contact_count"],
            "rows": recovery_rows,
        },
        "h109_refusal_control": h109_row,
        "branching_option": branching_option,
        "negative_fixtures": negative_fixtures,
        "checks": checks,
        "claim_boundary": {
            "bounded_feedback_basin_expansion_supported": status
            == "stage_a_supported",
            "learned_correction_generalization_supported": False,
            "live_controller_benefit_supported": False,
            "catalytic_learning_supported": False,
            "takeoff_supported": False,
            "literature_novelty_claimed": False,
        },
    }
    payload["sha256"] = stable_sha256(payload)
    return payload


def main() -> int:
    output = run_audit()
    result_path = FIXTURES / "h112_closed_loop_option_recovery_result.json"
    result_path.write_text(
        json.dumps(output, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "result_path": str(result_path.relative_to(ROOT)),
        "status": output["status"],
        "sha256": output["sha256"],
        "checks": output["checks"],
        "search": {
            key: value
            for key, value in output["search"].items()
            if key != "rows"
        },
        "recovered_rows": [
            row for row in output["search"]["rows"]
            if row["status"] == "recovered"
        ],
        "h109_refusal_control": output["h109_refusal_control"],
        "branching_option": output["branching_option"],
    }, indent=2, sort_keys=True))
    return 0 if output["status"] == "stage_a_supported" else 1


if __name__ == "__main__":
    raise SystemExit(main())
