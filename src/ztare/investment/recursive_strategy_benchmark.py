"""Sealed synthetic check for exhaustive strategy search versus hill climbing."""

from __future__ import annotations

import argparse
from collections import deque
from itertools import combinations
import json
from pathlib import Path
import random
from tempfile import TemporaryDirectory
from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256

from .strategy_options import OBJECTIVES, compile_company_strategy_frontier


SCHEMA = "jaggedthoughts-recursive-strategy-benchmark-v1"
SUITE_SCHEMA = "jaggedthoughts-recursive-strategy-benchmark-suite-v1"
AGENT_SELECTION_SCHEMA = "jaggedthoughts-recursive-strategy-agent-selection-v1"
AGENT_SUITE_SELECTION_SCHEMA = "jaggedthoughts-recursive-strategy-agent-suite-selection-v1"
START = ("incumbent_bundle",)
OPTIMUM = ("adaptive_product", "distribution_platform")


def _option(option_id: str, score: float) -> dict[str, Any]:
    return {
        "id": option_id,
        "kind": "sealed_benchmark_move",
        "description": f"Synthetic move {option_id}.",
        "addresses": ["synthetic_pressure"],
        "claim_status": "supported",
        "evidence_refs": ["sealed_landscape"],
        "scenario_effects": {"sealed_state": [score] * 4},
    }


def _interaction(interaction_id: str, option_ids: tuple[str, str], score: float) -> dict[str, Any]:
    return {
        "id": interaction_id,
        "option_ids": list(option_ids),
        "evidence_refs": ["sealed_landscape"],
        "scenario_effects": {"sealed_state": [score] * 4},
    }


SEALED_PROFILE: Mapping[str, Any] = {
    "schema": "jaggedthoughts-company-strategy-options-v1",
    "grammar_id": "jaggedthoughts.benchmark.rugged-strategy",
    "version": "1",
    "evidence_epoch": "2026-08-23T00:00:00Z",
    "max_depth": 1,
    "max_programs": 16,
    "max_bundle_size": 2,
    "company": {
        "id": "JT-RUGGED-001",
        "name": "Sealed rugged-landscape fixture",
        "data_class": "reference_fixture",
    },
    "industry_state": {
        "boundary": "Closed synthetic strategy landscape.",
        "customer_need": "Exercise exhaustive and local search under identical information.",
        "evidence_refs": ["sealed_landscape"],
        "pressures": [{
            "id": "synthetic_pressure",
            "actor_kind": "benchmark",
            "description": "Fixed pressure with no empirical interpretation.",
            "evidence_refs": ["sealed_landscape"],
        }],
    },
    "scenarios": [{
        "id": "sealed_state", "base": [0, 0, 0, 0],
        "evidence_refs": ["sealed_landscape"],
    }],
    "options": [
        _option("incumbent_bundle", 5),
        _option("adaptive_product", 2),
        _option("distribution_platform", 2),
    ],
    "interactions": [
        _interaction("incumbent_adaptive_friction", ("incumbent_bundle", "adaptive_product"), -3),
        _interaction("incumbent_distribution_friction", ("incumbent_bundle", "distribution_platform"), -3),
        _interaction("adaptive_distribution_reinforcement", OPTIMUM, 8),
    ],
    "representation": {
        "id": "sealed-rugged-landscape",
        "status": "passed",
        "evidence_refs": ["sealed_landscape"],
    },
}
SEALED_PROFILE_SHA256 = "8eb146931ded39ddcb907d45c070406dde6d2128faa859ff54fbc2cef77ac459"


def _options(row: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(sorted(map(str, row.get("unique_option_ids") or ())))


def _values(row: Mapping[str, Any]) -> tuple[float, ...]:
    values = row["objective_values"]
    return tuple(float(values[name]) for name in OBJECTIVES)


def _dominates(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return _dominates_values(_values(left), _values(right))


def _dominates_values(a: tuple[float, ...], b: tuple[float, ...]) -> bool:
    return all(x >= y for x, y in zip(a, b, strict=True)) and any(
        x > y for x, y in zip(a, b, strict=True)
    )


def _neighbors(rows: Mapping[tuple[str, ...], Mapping[str, Any]], key: tuple[str, ...]) -> list[tuple[str, ...]]:
    selected = set(key)
    return sorted(candidate for candidate in rows if len(selected.symmetric_difference(candidate)) == 1)


def _hill_climb(
    rows: Mapping[tuple[str, ...], Mapping[str, Any]],
    start: tuple[str, ...] = START,
) -> list[tuple[str, ...]]:
    path = [start]
    while True:
        better = [key for key in _neighbors(rows, path[-1]) if _dominates(rows[key], rows[path[-1]])]
        if not better:
            return path
        path.append(max(better, key=lambda key: (_values(rows[key]), key)))


def _pareto_keys(
    keys: tuple[tuple[str, ...], ...], values: Mapping[tuple[str, ...], tuple[float, ...]],
) -> tuple[tuple[str, ...], ...]:
    return tuple(sorted(
        key for key in keys
        if not any(
            other != key and _dominates_values(values[other], values[key])
            for other in keys
        )
    ))


def _solver_only_frontier(
    rows: Mapping[tuple[str, ...], Mapping[str, Any]],
    singleton_values: Mapping[str, tuple[float, ...]] | None = None,
) -> tuple[tuple[tuple[str, ...], ...], dict[tuple[str, ...], tuple[float, ...]]]:
    """Close the same feasible set using additive terminal effects only."""
    singleton = dict(singleton_values or {
        key[0]: _values(row) for key, row in rows.items() if len(key) == 1
    })
    values = {
        key: tuple(
            sum(singleton[option_id][index] for option_id in key)
            if index < len(OBJECTIVES) - 1
            else max(singleton[option_id][index] for option_id in key)
            for index in range(len(OBJECTIVES))
        )
        for key in rows
    }
    return _pareto_keys(tuple(rows), values), values


def _shortest_edit_path(
    rows: Mapping[tuple[str, ...], Mapping[str, Any]], start: tuple[str, ...], target: tuple[str, ...],
) -> list[tuple[str, ...]]:
    queue = deque([(start, [start])])
    seen = {start}
    while queue:
        current, path = queue.popleft()
        if current == target:
            return path
        for neighbor in _neighbors(rows, current):
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append((neighbor, [*path, neighbor]))
    raise AssertionError("sealed feasible graph disconnected the known optimum")


def compile_agent_only_baseline(
    raw: Mapping[str, Any] | None,
    rows: Mapping[tuple[str, ...], Mapping[str, Any]],
) -> dict[str, Any]:
    if raw is None:
        return {
            "status": "pending_recorded_agent_output",
            "included_in_comparison": False,
            "reason": (
                "No pre-score content-addressed agent selection exists; a scripted heuristic "
                "would not measure agent judgment."
            ),
            "required_artifact": "frozen_agent_selection_before_landscape_score_disclosure",
        }
    selected = tuple(sorted(map(str, raw.get("selected_option_ids") or ())))
    if (
        raw.get("schema") != AGENT_SELECTION_SCHEMA
        or raw.get("sealed_profile_sha256") != SEALED_PROFILE_SHA256
        or not selected or selected not in rows
    ):
        raise ValueError("agent selection does not name one feasible sealed program")
    rationale = str(raw.get("rationale") or "").strip()
    if not rationale:
        raise ValueError("agent selection requires a rationale")
    body = {
        "schema": AGENT_SELECTION_SCHEMA,
        "sealed_profile_sha256": SEALED_PROFILE_SHA256,
        "selected_option_ids": list(selected),
        "rationale": rationale,
    }
    return {
        **body,
        "selection_sha256": stable_sha256(body),
        "status": "scored_frozen_selection",
        "included_in_comparison": True,
        "objective_values": dict(rows[selected]["objective_values"]),
        "selected_known_optimum": selected == OPTIMUM,
    }


def run_recursive_strategy_benchmark(
    agent_selection: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the fixed apparatus and return a content-addressed comparison receipt."""
    if stable_sha256(SEALED_PROFILE) != SEALED_PROFILE_SHA256:
        raise AssertionError("sealed benchmark profile changed")
    frontier = compile_company_strategy_frontier(SEALED_PROFILE)
    rows = {_options(row): row for row in frontier["programs"]}
    if START not in rows or OPTIMUM not in rows:
        raise AssertionError("sealed benchmark programs are absent")
    exhaustive = tuple(_options(row) for row in frontier["frontier_programs"])
    if exhaustive != (OPTIMUM,):
        raise AssertionError(f"sealed optimum changed: {exhaustive}")
    full_values = {key: _values(row) for key, row in rows.items()}
    flat = _pareto_keys(tuple(key for key in rows if len(key) == 1), full_values)
    hill_path = _hill_climb(rows)
    solver_only, additive_values = _solver_only_frontier(rows)
    escape_path = _shortest_edit_path(rows, START, OPTIMUM)
    local_peaks = {
        _options(row) for row in frontier["local_peak_programs"]
    }
    choice_space_sha = frontier["choice_space_certificate"]["choice_space_sha256"]
    body = {
        "schema": SCHEMA,
        "apparatus_status": "synthetic_benchmark_only",
        "sealed_profile_sha256": SEALED_PROFILE_SHA256,
        "strategy_frontier_sha256": frontier["strategy_frontier_sha256"],
        "choice_space_sha256": choice_space_sha,
        "solver": frontier["choice_space_certificate"]["solver"],
        "feasible_program_count": len(rows),
        "start_option_ids": list(START),
        "known_optimum_option_ids": list(OPTIMUM),
        "exhaustive_search": {
            "system_role": "integrated_recursive_interaction_aware",
            "method": frontier["enumeration"]["method"],
            "choice_space_sha256": choice_space_sha,
            "recursive_bundle_search": True,
            "authored_interactions_used": True,
            "selected_option_ids": list(exhaustive[0]),
            "selected_expression": rows[OPTIMUM]["expression"],
            "objective_values": dict(rows[OPTIMUM]["objective_values"]),
        },
        "one_edit_hill_climb": {
            "system_role": "local_one_edit",
            "choice_space_sha256": choice_space_sha,
            "path": [list(key) for key in hill_path],
            "selected_option_ids": list(hill_path[-1]),
            "objective_values": dict(rows[hill_path[-1]]["objective_values"]),
            "stopped_at_local_peak": hill_path[-1] in local_peaks,
        },
        "flat_single_option_ablation": {
            "system_role": "flat_single_option",
            "choice_space_sha256": choice_space_sha,
            "recursive_bundle_search": False,
            "candidate_program_count": sum(len(key) == 1 for key in rows),
            "selected_programs": [{
                "option_ids": list(key),
                "full_landscape_objective_values": list(full_values[key]),
            } for key in flat],
            "missed_known_optimum": OPTIMUM not in flat,
        },
        "solver_only_ablation": {
            "system_role": "solver_only_additive",
            "method": "z3_feasibility_plus_additive_terminal_objectives",
            "choice_space_sha256": choice_space_sha,
            "feasible_program_count": len(rows),
            "authored_interactions_used": False,
            "adaptive_learning_used": False,
            "selected_programs": [{
                "option_ids": list(key),
                "additive_objective_values": list(additive_values[key]),
                "full_landscape_objective_values": list(_values(rows[key])),
            } for key in solver_only],
            "missed_known_optimum": OPTIMUM not in solver_only,
            "exhaustive_dominates_every_selected_on_full_landscape": all(
                _dominates(rows[OPTIMUM], rows[key]) for key in solver_only
            ),
        },
        "agent_only_baseline": compile_agent_only_baseline(agent_selection, rows),
        "comparison_status": {
            "executed_arms": [
                "integrated_recursive_interaction_aware", "flat_single_option",
                "local_one_edit", "solver_only_additive",
                *(["agent_only"] if agent_selection is not None else []),
            ],
            "pending_arms": ([] if agent_selection is not None else ["agent_only"]),
        },
        "local_peak_escape": {
            "shortest_feasible_edit_path": [list(key) for key in escape_path],
            "objective_path": [list(_values(rows[key])) for key in escape_path],
            "requires_initial_decline": _dominates(rows[START], rows[escape_path[1]]),
            "exhaustive_beats_hill_climb": _dominates(rows[OPTIMUM], rows[hill_path[-1]]),
        },
        "claim_boundary": (
            "This sealed apparatus checks search behavior on one authored landscape; "
            "it supplies no empirical strategy, return, or alpha conclusion."
        ),
        "capital_authority": False,
    }
    return {**body, "benchmark_sha256": stable_sha256(body)}


def _generated_profile(rng: random.Random, case_id: str, attempt: int) -> dict[str, Any]:
    option_ids = [f"move_{index}" for index in range(7)]
    scores = {option_id: rng.randint(-2, 7) for option_id in option_ids}
    interactions = []
    for size in (2, 3):
        for option_ids_subset in combinations(option_ids, size):
            if rng.random() > (0.58 if size == 2 else 0.22):
                continue
            score = rng.randint(-9, 13)
            if score:
                interactions.append(_interaction(
                    f"interaction_{'_'.join(option_ids_subset)}",
                    option_ids_subset, score,
                ))
    incompatible = sorted(rng.sample(option_ids, 2))
    prerequisite_option, required_option = rng.sample(option_ids, 2)
    uses = {option_id: rng.randint(1, 3) for option_id in option_ids}
    return {
        "schema": "jaggedthoughts-company-strategy-options-v1",
        "grammar_id": f"jaggedthoughts.benchmark.concealed.{case_id}",
        "version": "1",
        "evidence_epoch": "2026-08-25T00:00:00Z",
        "max_depth": 2,
        "max_programs": 256,
        "max_bundle_size": 3,
        "company": {
            "id": case_id, "name": f"Generated concealed case {case_id}",
            "data_class": "generated_reference_fixture",
        },
        "industry_state": {
            "boundary": "Generated closed strategy landscape.",
            "customer_need": "Choose the globally strongest feasible bundle.",
            "evidence_refs": [f"concealed:{case_id}:{attempt}"],
            "pressures": [{
                "id": "synthetic_pressure", "actor_kind": "benchmark",
                "description": "Generated pressure with no empirical interpretation.",
                "evidence_refs": [f"concealed:{case_id}:{attempt}"],
            }],
        },
        "scenarios": [{
            "id": "sealed_state", "base": [0, 0, 0, 0],
            "evidence_refs": [f"concealed:{case_id}:{attempt}"],
        }],
        "options": [_option(option_id, scores[option_id]) for option_id in option_ids],
        "interactions": interactions,
        "feasibility_constraints": {
            "incompatibilities": [{
                "constraint_id": "generated_incompatibility",
                "option_ids": incompatible,
                "evidence_refs": [f"concealed:{case_id}:{attempt}"],
            }],
            "prerequisites": [{
                "constraint_id": "generated_prerequisite",
                "option_id": prerequisite_option,
                "requires": [required_option],
                "evidence_refs": [f"concealed:{case_id}:{attempt}"],
            }],
            "resources": [{
                "constraint_id": "generated_resource",
                "resource_id": "execution_capacity", "unit": "capacity_unit",
                "limit": 5, "uses": uses,
                "evidence_refs": [f"concealed:{case_id}:{attempt}"],
            }],
        },
        "representation": {
            "id": f"generated:{case_id}:{attempt}", "status": "passed",
            "evidence_refs": [f"concealed:{case_id}:{attempt}"],
        },
    }


def _compile_generated_case(profile: Mapping[str, Any]) -> dict[str, Any] | None:
    frontier = compile_company_strategy_frontier(profile)
    rows = {_options(row): row for row in frontier["programs"]}
    optimums = tuple(_options(row) for row in frontier["frontier_programs"])
    if len(optimums) != 1 or len(optimums[0]) < 2:
        return None
    optimum = optimums[0]
    singletons = [key for key in rows if len(key) == 1]
    start = max(singletons, key=lambda key: (_values(rows[key]), key))
    hill_path = _hill_climb(rows, start)
    raw_singletons = {
        str(option["id"]): tuple(map(float, option["scenario_effects"]["sealed_state"])) + (1.0,)
        for option in profile["options"]
    }
    solver_only, _ = _solver_only_frontier(rows, raw_singletons)
    if (
        hill_path[-1] == optimum
        or not _dominates(rows[optimum], rows[hill_path[-1]])
        or optimum in solver_only
    ):
        return None
    certificate = frontier["choice_space_certificate"]
    body = {
        "case_id": str((profile.get("company") or {})["id"]),
        "profile": dict(profile),
        "profile_sha256": stable_sha256(profile),
        "strategy_frontier_sha256": frontier["strategy_frontier_sha256"],
        "choice_space_sha256": certificate["choice_space_sha256"],
        "feasible_program_count": len(rows),
        "known_optimum_option_ids": list(optimum),
        "known_optimum_objective_values": dict(rows[optimum]["objective_values"]),
        "hill_start_option_ids": list(start),
        "hill_selected_option_ids": list(hill_path[-1]),
        "hill_path": [list(key) for key in hill_path],
        "solver_only_selected_option_ids": [list(key) for key in solver_only],
        "predicate_count": certificate["constraint_authority"]["dossier_bound_predicate_count"],
    }
    return {**body, "case_sha256": stable_sha256(body)}


def compile_concealed_strategy_suite(
    *, seed: int, case_count: int = 6, agent_selections: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate, freeze, and score rugged cases whose answers are not hardcoded."""
    if not 1 <= case_count <= 20:
        raise ValueError("concealed suite case_count must be in [1, 20]")
    rng = random.Random(seed)
    cases = []
    for case_index in range(case_count):
        case_id = f"JT-CONCEALED-{case_index + 1:03d}"
        for attempt in range(1, 501):
            compiled = _compile_generated_case(_generated_profile(rng, case_id, attempt))
            if compiled is not None:
                cases.append(compiled)
                break
        else:
            raise RuntimeError(f"failed to generate rugged concealed case {case_id}")
    selection_rows = []
    if agent_selections is not None:
        raw_rows = agent_selections.get("selections") or ()
        by_case = {str(row.get("case_id") or ""): row for row in raw_rows}
        if (
            agent_selections.get("schema") != AGENT_SUITE_SELECTION_SCHEMA
            or set(by_case) != {row["case_id"] for row in cases}
            or len(by_case) != len(raw_rows)
        ):
            raise ValueError("agent suite selection must cover every frozen case exactly")
        for case in cases:
            raw = by_case[case["case_id"]]
            selected = sorted(map(str, raw.get("selected_option_ids") or ()))
            program_rows = {
                _options(row): row
                for row in compile_company_strategy_frontier(case["profile"])["programs"]
            }
            if tuple(selected) not in program_rows or not str(raw.get("rationale") or "").strip():
                raise ValueError("agent suite selection must name a feasible program and rationale")
            selected_values = dict(program_rows[tuple(selected)]["objective_values"])
            objective_optimal = selected_values == case["known_optimum_objective_values"]
            selection_rows.append({
                "case_id": case["case_id"], "selected_option_ids": selected,
                "selected_known_optimum": objective_optimal,
                "selected_canonical_optimum": selected == case["known_optimum_option_ids"],
                "selected_objective_values": selected_values,
                "rationale": str(raw["rationale"]).strip(),
            })
    body = {
        "schema": SUITE_SCHEMA,
        "seed": seed,
        "case_count": case_count,
        "cases": cases,
        "agent_only": {
            "status": "scored" if agent_selections is not None else "pending",
            "selections": selection_rows,
            "optimum_rate": (
                sum(row["selected_known_optimum"] for row in selection_rows) / case_count
                if selection_rows else None
            ),
        },
        "recursive_compiler_optimum_rate": 1.0,
        "hill_climb_optimum_rate": 0.0,
        "solver_only_optimum_rate": 0.0,
        "claim_boundary": (
            "Generated synthetic cases measure combinatorial reasoning under equal declared "
            "information; they imply no company-strategy or investment advantage."
        ),
        "capital_authority": False,
    }
    return {**body, "suite_sha256": stable_sha256(body)}


def run_subscription_agent_baseline(
    artifact_dir: str | Path, *, timeout_seconds: int = 900,
) -> dict[str, Any]:
    """Freeze and score one tool-disabled Codex-subscription selection."""
    from ztare.common.subscription_agent_runtime import (
        CODEX_SANDBOX_SEALED_COMPLETION,
        run_subscription_agent_with_recovery,
    )

    destination = Path(artifact_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / "agent-selection.json"
    dispatch = destination / "dispatch.json"
    schema = {
        "type": "object", "additionalProperties": False,
        "properties": {
            "schema": {"type": "string", "const": AGENT_SELECTION_SCHEMA},
            "sealed_profile_sha256": {
                "type": "string", "const": SEALED_PROFILE_SHA256,
            },
            "selected_option_ids": {
                "type": "array", "minItems": 1, "maxItems": 2,
                "items": {"type": "string"},
            },
            "rationale": {"type": "string", "minLength": 1},
        },
        "required": [
            "schema", "sealed_profile_sha256", "selected_option_ids", "rationale",
        ],
    }
    prompt = f"""Select one strategy program from the frozen synthetic case below.
You have the same declared option, scenario, and interaction information as the
formal compiler. Choose one or two option ids to maximize all four economic
coordinates. Return only the supplied JSON schema. Do not use tools or external
information. This is a benchmark selection, not investment advice.

{json.dumps(SEALED_PROFILE, sort_keys=True)}
"""
    schema_path = destination / "output.schema.json"
    schema_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with TemporaryDirectory(prefix="jt-strategy-agent-") as isolated:
        run = run_subscription_agent_with_recovery(
            runtime="codex", prompt=prompt,
            agent_id=f"jaggedthoughts-strategy-baseline::{SEALED_PROFILE_SHA256[:16]}",
            repo=isolated, session_state=None, timeout_seconds=timeout_seconds,
            default_codex_model="account-default",
            codex_sandbox=CODEX_SANDBOX_SEALED_COMPLETION,
            output_schema=schema_path, output_last_message_path=output,
            dispatch_receipt_path=dispatch,
            stdout_path=str(destination / "stdout.log"),
            stderr_path=str(destination / "stderr.log"),
        )
    (destination / "transport-result.json").write_text(json.dumps({
        "returncode": run.result.returncode,
        "stdout": run.result.stdout,
        "stderr": run.result.stderr,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if run.result.returncode != 0 or not output.is_file():
        raise RuntimeError(
            "Codex subscription strategy baseline failed: "
            f"{run.result.returncode}: {run.result.stderr[-500:]}"
        )
    result = run_recursive_strategy_benchmark(json.loads(output.read_text(encoding="utf-8")))
    receipt = destination / "benchmark.json"
    receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def run_subscription_concealed_suite(
    artifact_dir: str | Path, *, seed: int, case_count: int = 6,
    timeout_seconds: int = 1200,
) -> dict[str, Any]:
    """Freeze generated cases, then score one tool-disabled subscription call."""
    from ztare.common.subscription_agent_runtime import (
        CODEX_SANDBOX_SEALED_COMPLETION,
        run_subscription_agent_with_recovery,
    )

    destination = Path(artifact_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    pending = compile_concealed_strategy_suite(seed=seed, case_count=case_count)
    frozen_input_body = {
        "schema": "jaggedthoughts-recursive-strategy-agent-suite-input-v1",
        "seed": seed,
        "cases": [{
            "case_id": row["case_id"], "profile": row["profile"],
            "profile_sha256": row["profile_sha256"],
        } for row in pending["cases"]],
    }
    frozen_input = {
        **frozen_input_body, "input_sha256": stable_sha256(frozen_input_body),
    }
    (destination / "frozen-input.json").write_text(
        json.dumps(frozen_input, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    schema = {
        "type": "object", "additionalProperties": False,
        "properties": {
            "schema": {"type": "string", "const": AGENT_SUITE_SELECTION_SCHEMA},
            "selections": {
                "type": "array", "minItems": case_count, "maxItems": case_count,
                "items": {
                    "type": "object", "additionalProperties": False,
                    "properties": {
                        "case_id": {"type": "string"},
                        "selected_option_ids": {
                            "type": "array", "minItems": 1, "maxItems": 3,
                            "items": {"type": "string"},
                        },
                        "rationale": {"type": "string", "minLength": 1},
                    },
                    "required": ["case_id", "selected_option_ids", "rationale"],
                },
            },
        },
        "required": ["schema", "selections"],
    }
    schema_path = destination / "output.schema.json"
    output_path = destination / "agent-selections.json"
    schema_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    prompt = f"""Choose one feasible strategy bundle for every generated case.
Each case declares option effects, interaction effects, incompatibilities,
prerequisites, and a resource limit. Maximize all four economic coordinates;
all options cover the same pressure. Return exactly one row per case using the
supplied schema. Do not use tools or external information. The cases were
content-addressed before this call; their optimums are not included below.

{json.dumps(frozen_input, sort_keys=True)}
"""
    with TemporaryDirectory(prefix="jt-strategy-suite-agent-") as isolated:
        run = run_subscription_agent_with_recovery(
            runtime="codex", prompt=prompt,
            agent_id=f"jaggedthoughts-strategy-suite::{frozen_input['input_sha256'][:16]}",
            repo=isolated, session_state=None, timeout_seconds=timeout_seconds,
            default_codex_model="account-default",
            codex_sandbox=CODEX_SANDBOX_SEALED_COMPLETION,
            output_schema=schema_path, output_last_message_path=output_path,
            dispatch_receipt_path=destination / "dispatch.json",
            stdout_path=str(destination / "stdout.log"),
            stderr_path=str(destination / "stderr.log"),
        )
    if run.result.returncode != 0 or not output_path.is_file():
        raise RuntimeError(
            "Codex subscription concealed suite failed: "
            f"{run.result.returncode}: {run.result.stderr[-500:]}"
        )
    selections = json.loads(output_path.read_text(encoding="utf-8"))
    scored = compile_concealed_strategy_suite(
        seed=seed, case_count=case_count, agent_selections=selections,
    )
    if [row["profile_sha256"] for row in scored["cases"]] != [
        row["profile_sha256"] for row in pending["cases"]
    ]:
        raise AssertionError("concealed suite regenerated different frozen cases")
    (destination / "benchmark.json").write_text(
        json.dumps(scored, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    return scored


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-baseline-dir")
    parser.add_argument("--agent-suite-dir")
    parser.add_argument("--suite-seed", type=int, default=20260825)
    parser.add_argument("--suite-cases", type=int, default=6)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    args = parser.parse_args()
    result = (
        run_subscription_concealed_suite(
            args.agent_suite_dir, seed=args.suite_seed, case_count=args.suite_cases,
            timeout_seconds=args.timeout_seconds,
        ) if args.agent_suite_dir else
        run_subscription_agent_baseline(
            args.agent_baseline_dir, timeout_seconds=args.timeout_seconds,
        ) if args.agent_baseline_dir else run_recursive_strategy_benchmark()
    )
    print(json.dumps(result, indent=2, sort_keys=True))


__all__ = [
    "AGENT_SELECTION_SCHEMA", "AGENT_SUITE_SELECTION_SCHEMA", "SCHEMA",
    "SEALED_PROFILE_SHA256", "SUITE_SCHEMA", "compile_agent_only_baseline",
    "compile_concealed_strategy_suite", "run_recursive_strategy_benchmark",
    "run_subscription_agent_baseline", "run_subscription_concealed_suite",
]
