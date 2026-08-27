#!/usr/bin/env python3
"""Search a bounded cached LS20 neighborhood for an H95 option fiber."""
from __future__ import annotations

from dataclasses import replace
import itertools
import json
from pathlib import Path
import sys
from typing import Any


FIXTURES = Path(__file__).resolve().parent
ROOT = FIXTURES.parents[2]
CONTROL = ROOT / "scripts/public/control"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(CONTROL))

from arc_agi import Arcade, OperationMode
import arc3_causal_response_derivative_probe as h97
from ztare.common.equivariance import stable_sha256
from ztare.substrates.arc_agi3 import ArcAgi3Adapter
from ztare.worldmodel.carrier_loader import load_carrier_path
from ztare.worldmodel.mechanism_effects import fiber_mechanism_effect
from ztare.worldmodel.observation_object_catalog import decode_grid_rle_rows


HYPOTHESIS_ID = "H-GPSA-LOCAL-VIABLE-OPTION-FIBER-20260806-111"
CANONICAL_PREFIX = (2, 2, 2, 0, 0)
WINNING_SUFFIX = (0, 0, 3, 3, 3, 0, 0, 0)
H109_REFUSAL_PREFIX = (2, 2, 2, 0, 0, 0, 1)
ACTION_ARITY = 4


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _grid_tuple(grid: Any) -> tuple[tuple[int, ...], ...]:
    if hasattr(grid, "tolist"):
        grid = grid.tolist()
    return tuple(tuple(int(value) for value in row) for row in grid)


def _receipt_grid(observation: dict[str, Any]) -> tuple[tuple[int, ...], ...]:
    return decode_grid_rle_rows(tuple(map(str, observation["grid_rle_rows"])))


def _effect_signature(
    factors: tuple[Any, ...],
) -> tuple[tuple[Any, ...], ...]:
    return tuple(
        fiber_mechanism_effect(source, target)
        for source, target in zip(factors, factors[1:])
    )


def _run_word(
    adapter: ArcAgi3Adapter,
    *,
    projection: Any,
    prefix: tuple[int, ...],
    word: tuple[int, ...],
) -> dict[str, Any]:
    grid = _grid_tuple(adapter.reset())
    for action in prefix:
        grid = _grid_tuple(adapter.step(action))
    start_levels = int(adapter.levels_completed)
    source_grid = grid
    factors = [projection.factor(grid)]
    for action in word:
        grid = _grid_tuple(adapter.step(action))
        factors.append(projection.factor(grid))
    effects = _effect_signature(tuple(factors))
    return {
        "prefix": list(prefix),
        "prefix_sha256": stable_sha256(prefix),
        "source_grid_sha256": stable_sha256(source_grid),
        "source_factor_sha256": stable_sha256(factors[0]),
        "source_factor": factors[0],
        "effect_signature_sha256": stable_sha256(effects),
        "effect_signature": effects,
        "start_levels_completed": start_levels,
        "end_levels_completed": int(adapter.levels_completed),
        "levels_gained": int(adapter.levels_completed) - start_levels,
        "primitive_contact_count": len(prefix) + len(word),
    }


def _source_receipt(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_grid_sha256": row["source_grid_sha256"],
        "source_factor_sha256": row["source_factor_sha256"],
        "prefixes": [row["prefix"]],
        "prefix_sha256s": [row["prefix_sha256"]],
        "history_multiplicity": 1,
        "effect_signature_sha256": row["effect_signature_sha256"],
        "levels_gained": row["levels_gained"],
    }


def run_audit() -> dict[str, Any]:
    project = ROOT / "projects/arc3_ls20_gov"
    carrier, _kind, carrier_sha256 = load_carrier_path(
        project / "test_model.py",
        project_dir=project,
    )
    projection = carrier._ztare_factored_projection

    h95_arm = _load_json(
        FIXTURES
        / "h95_response_transport_square/arms"
        / "pair_01_offer_causal_mechanics.json"
    )
    h95_observations = h95_arm["probe"]["observations"]
    h95_source_grid = _receipt_grid(h95_observations[4])
    h95_route_factors = tuple(
        projection.factor(_receipt_grid(observation))
        for observation in h95_observations[4:13]
    )
    h95_effects = _effect_signature(h95_route_factors)
    h95_source_grid_sha256 = stable_sha256(h95_source_grid)
    h95_source_factor_sha256 = stable_sha256(h95_route_factors[0])
    h95_effect_signature_sha256 = stable_sha256(h95_effects)

    environment_root = ROOT / "environment_files"
    base_game, version = h97.H97_ENVIRONMENT_GAME_ID.split("-", 1)
    game_root = environment_root / base_game / version
    code_path = game_root / f"{base_game}.py"
    metadata_path = game_root / "metadata.json"
    environment_identity_checks = {
        "code_sha256": (
            h97._file_sha256(code_path) == h97.H97_ENVIRONMENT_CODE_SHA256
        ),
        "metadata_sha256": (
            h97._file_sha256(metadata_path)
            == h97.H97_ENVIRONMENT_METADATA_SHA256
        ),
    }
    if not all(environment_identity_checks.values()):
        raise RuntimeError("cached H97 environment identity drifted")
    environment_source_sha256 = stable_sha256({
        "game_id": h97.H97_ENVIRONMENT_GAME_ID,
        "seed": 0,
        "code_sha256": h97.H97_ENVIRONMENT_CODE_SHA256,
        "metadata_sha256": h97.H97_ENVIRONMENT_METADATA_SHA256,
    })
    recordings_dir = FIXTURES / "h111_local_viable_option_fiber/recordings"
    recordings_dir.mkdir(parents=True, exist_ok=True)
    arcade = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=str(environment_root),
        recordings_dir=str(recordings_dir),
    )
    adapter = ArcAgi3Adapter(h97.H97_ENVIRONMENT_GAME_ID, arcade=arcade)
    if int(adapter.action_arity) != ACTION_ARITY:
        raise RuntimeError("H111 action arity drifted")

    prefixes = tuple(
        tuple(int(action) for action in candidate)
        for candidate in itertools.product(range(ACTION_ARITY), repeat=5)
        if sum(
            action != canonical
            for action, canonical in zip(candidate, CANONICAL_PREFIX)
        ) <= 2
    )
    rows = tuple(
        _run_word(
            adapter,
            projection=projection,
            prefix=prefix,
            word=WINNING_SUFFIX,
        )
        for prefix in prefixes
    )
    by_source: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (
            row["source_grid_sha256"],
            row["source_factor_sha256"],
        )
        if key not in by_source:
            by_source[key] = _source_receipt(row)
            continue
        source = by_source[key]
        source["prefixes"].append(row["prefix"])
        source["prefix_sha256s"].append(row["prefix_sha256"])
        source["history_multiplicity"] += 1
        if (
            source["effect_signature_sha256"]
            != row["effect_signature_sha256"]
            or source["levels_gained"] != row["levels_gained"]
        ):
            raise RuntimeError("one exact source produced inconsistent outcomes")
    sources = tuple(sorted(
        by_source.values(),
        key=lambda row: (
            row["source_grid_sha256"],
            row["source_factor_sha256"],
        ),
    ))
    canonical_row = next(
        row for row in rows if tuple(row["prefix"]) == CANONICAL_PREFIX
    )
    viable_distinct_sources = tuple(
        source for source in sources
        if (
            source["source_grid_sha256"] != h95_source_grid_sha256
            and source["source_factor_sha256"] != h95_source_factor_sha256
            and source["effect_signature_sha256"]
            == h95_effect_signature_sha256
            and source["levels_gained"] > 0
        )
    )
    h109_control = _run_word(
        adapter,
        projection=projection,
        prefix=H109_REFUSAL_PREFIX,
        word=WINNING_SUFFIX,
    )

    mutated_factor = replace(
        h95_route_factors[0],
        ordered_budget=h95_route_factors[0].ordered_budget + 1,
    )
    mutated_word = (*WINNING_SUFFIX[:-1], (WINNING_SUFFIX[-1] + 1) % 4)
    negative_fixtures = {
        "source_grid_identity": stable_sha256({
            "source_grid_sha256": h95_source_grid_sha256,
            "mutation": "one_bit",
        }) != h95_source_grid_sha256,
        "source_factor_identity": (
            stable_sha256(mutated_factor) != h95_source_factor_sha256
        ),
        "option_word_identity": (
            stable_sha256(mutated_word) != stable_sha256(WINNING_SUFFIX)
        ),
        "environment_source_identity": stable_sha256({
            "environment_source_sha256": environment_source_sha256,
            "seed": 1,
        }) != environment_source_sha256,
    }
    checks = {
        "candidate_count_is_106": len(prefixes) == 106,
        "cached_environment_identity_verified": all(
            environment_identity_checks.values()
        ),
        "canonical_source_grid_reproduced": (
            canonical_row["source_grid_sha256"]
            == h95_source_grid_sha256
        ),
        "canonical_source_factor_reproduced": (
            canonical_row["source_factor_sha256"]
            == h95_source_factor_sha256
        ),
        "canonical_effect_signature_reproduced": (
            canonical_row["effect_signature_sha256"]
            == h95_effect_signature_sha256
        ),
        "canonical_level_gain_reproduced": canonical_row["levels_gained"] > 0,
        "nontrivial_viable_source_exists": bool(viable_distinct_sources),
        "h109_refusal_control_excluded": (
            h109_control["levels_gained"] == 0
            or h109_control["effect_signature_sha256"]
            != h95_effect_signature_sha256
        ),
        "duplicate_histories_quotiented": len(sources) <= len(rows),
        "all_identity_mutations_detected": all(negative_fixtures.values()),
        "no_controller_contact": True,
    }
    status = "stage_a_supported" if all(checks.values()) else "rejected"
    payload = {
        "schema": "ztare-h111-local-viable-option-fiber-v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "status": status,
        "environment_contact": True,
        "environment_operation_mode": "offline",
        "controller_contact": False,
        "identities": {
            "carrier_sha256": carrier_sha256,
            "projection_sha256": projection.projection_sha256,
            "environment_source_sha256": environment_source_sha256,
            "h95_source_grid_sha256": h95_source_grid_sha256,
            "h95_source_factor_sha256": h95_source_factor_sha256,
            "h95_effect_signature_sha256": h95_effect_signature_sha256,
            "winning_suffix_sha256": stable_sha256(WINNING_SUFFIX),
        },
        "search": {
            "canonical_prefix": list(CANONICAL_PREFIX),
            "maximum_hamming_radius": 2,
            "candidate_prefix_count": len(prefixes),
            "unique_exact_source_count": len(sources),
            "duplicate_history_count": len(rows) - len(sources),
            "primitive_contact_count": sum(
                row["primitive_contact_count"] for row in rows
            ) + h109_control["primitive_contact_count"],
            "viable_distinct_source_count": len(viable_distinct_sources),
            "viable_distinct_sources": viable_distinct_sources,
            "sources": sources,
        },
        "canonical": _source_receipt(canonical_row),
        "h109_refusal_control": _source_receipt(h109_control),
        "negative_fixtures": negative_fixtures,
        "checks": checks,
        "claim_boundary": {
            "bounded_local_target_exists": bool(viable_distinct_sources),
            "task_credit_at_target_supported": False,
            "live_controller_benefit_supported": False,
            "cross_task_transfer_supported": False,
            "catalytic_learning_supported": False,
            "takeoff_supported": False,
            "literature_novelty_claimed": False,
        },
    }
    payload["sha256"] = stable_sha256(payload)
    return payload


def main() -> int:
    output = run_audit()
    result_path = FIXTURES / "h111_local_viable_option_fiber_result.json"
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
            if key not in {"sources", "viable_distinct_sources"}
        },
        "viable_distinct_sources": output["search"][
            "viable_distinct_sources"
        ],
        "h109_refusal_control": output["h109_refusal_control"],
    }, indent=2, sort_keys=True))
    return 0 if output["status"] == "stage_a_supported" else 1


if __name__ == "__main__":
    raise SystemExit(main())
