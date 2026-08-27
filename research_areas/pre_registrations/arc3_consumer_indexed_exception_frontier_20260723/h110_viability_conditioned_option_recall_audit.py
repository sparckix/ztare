#!/usr/bin/env python3
"""Audit H110 on frozen H63, H95, H96, and H109 evidence."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import sys
from typing import Any


FIXTURES = Path(__file__).resolve().parent
ROOT = FIXTURES.parents[2]
sys.path.insert(0, str(FIXTURES))
sys.path.insert(0, str(ROOT / "src"))

import task_conditioned_skill_basin_audit as h77

from ztare.common.boundary_reachability import (
    OptionProgramSpec,
    compile_boundary_reachability_fibers,
    compile_effect_option_families,
    plan_boundary_reachability_frontier,
    reindex_option_program,
    reindex_option_programs,
)
from ztare.common.continual_skill_memory import (
    empty_continual_skill_memory,
    judge_effect_option_task_credit,
    record_task_choice_experience,
)
from ztare.common.equivariance import stable_sha256
from ztare.common.partial_action_system import (
    PartialActionObservation,
    build_partial_action_system,
)
from ztare.worldmodel.carrier_loader import load_carrier_path
from ztare.worldmodel.mechanism_effects import fiber_mechanism_effect
from ztare.worldmodel.observation_object_catalog import decode_grid_rle_rows
from ztare.worldmodel.patch_base_carrier import (
    carrier_execution_sha256_from_source,
)


HYPOTHESIS_ID = (
    "H-GPSA-VIABILITY-CONDITIONED-OPTION-RECALL-20260806-110"
)
TASK_CONTRACT_SHA256 = stable_sha256({
    "schema": "ztare-h110-task-contract-v1",
    "game": "ls20",
    "objective": "first_level_completion",
    "horizon": 12,
    "source_experiment": "h95_response_transport_square",
})
EFFECT_NAMESPACE = "h110-factored-option-effects-v1"
OPERATIONS = (0, 1, 2, 3)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _grid(observation: dict[str, Any]) -> tuple[tuple[int, ...], ...]:
    return decode_grid_rle_rows(tuple(
        str(row) for row in observation["grid_rle_rows"]
    ))


def _factor(projection: Any, observation: dict[str, Any]) -> Any:
    return projection.factor(_grid(observation))


def _option_node(projection: Any, observation: dict[str, Any]) -> tuple[Any, str]:
    grid = _grid(observation)
    return projection.factor(grid), stable_sha256(grid)


def _arm_rows(directory: Path) -> tuple[tuple[Path, dict[str, Any]], ...]:
    return tuple(
        (path, _load_json(path))
        for path in sorted((directory / "arms").glob("*.json"))
    )


def _arm_actions(arm: dict[str, Any]) -> tuple[int, ...]:
    return tuple(int(row["action"]) for row in arm["probe"]["turns"])


def _arm_factors(
    projection: Any,
    arm: dict[str, Any],
) -> tuple[Any, ...]:
    return tuple(
        _factor(projection, observation)
        for observation in arm["probe"]["observations"]
    )


def _build_option_system(
    rows: tuple[tuple[Path, dict[str, Any]], ...],
    *,
    projection: Any,
    horizon_by_experiment: dict[str, int],
) -> Any:
    observations = []
    for path, arm in rows:
        experiment = str(arm["experiment_sha256"])
        horizon = min(
            horizon_by_experiment[experiment],
            len(arm["probe"]["turns"]),
        )
        nodes = tuple(
            _option_node(projection, observation)
            for observation in arm["probe"]["observations"]
        )
        actions = _arm_actions(arm)
        for index in range(horizon):
            observations.append(PartialActionObservation(
                source=nodes[index],
                operation=actions[index],
                successor=nodes[index + 1],
                evidence_ref=f"{path.relative_to(ROOT)}#{index}",
                context={
                    "pair_index": int(arm["pair_index"]),
                    "assignment": str(arm["assignment"]),
                    "index": index,
                },
            ))
    return build_partial_action_system(
        observations,
        project=lambda factor: factor,
        effect=lambda source, _operation, successor, _source_key, _target_key: (
            fiber_mechanism_effect(source[0], successor[0])
        ),
        projection_id="h110-exact-observation-with-factor-v1",
    )


def _option_identity(
    option_sha256: str,
    families: tuple[Any, ...],
) -> tuple[str, str]:
    identities = {
        (family.family_sha256, context_variant.variant_sha256)
        for family in families
        for context_variant in family.context_variants
        for implementation in context_variant.implementations
        if implementation.source_option_sha256 == option_sha256
    }
    if len(identities) != 1:
        raise RuntimeError(
            "one deterministic option must have one effect/context identity: "
            f"option={option_sha256}, identities={sorted(identities)}"
        )
    return next(iter(identities))


def _factor_differences(left: Any, right: Any) -> dict[str, Any]:
    result = {}
    for name in (
        "controlled_base",
        "finite_configuration",
        "presentation_assignment",
        "ordered_budget",
        "one_shot_availability",
        "ordered_feasibility_configuration",
        "operation_domain_assignment",
    ):
        a = getattr(left, name)
        b = getattr(right, name)
        if a == b:
            continue
        if (
            isinstance(a, tuple)
            and isinstance(b, tuple)
            and len(a) == len(b)
            and len(a) > 8
        ):
            indices = [
                index for index, (x, y) in enumerate(zip(a, b))
                if x != y
            ]
            result[name] = {
                "differing_indices": indices,
                "source_values": [a[index] for index in indices],
                "target_values": [b[index] for index in indices],
            }
        else:
            result[name] = {
                "source": a,
                "target": b,
            }
    return result


def _reconstruct_h63(
    *,
    project: Path,
    carrier: Any,
    carrier_sha256: str,
    carrier_execution_sha256: str,
    projection: Any,
) -> dict[str, Any]:
    h63 = _load_json(FIXTURES / "post_support_probe1_recompile_audit_result.json")
    h71 = _load_json(FIXTURES / "joint_relation_recompile_audit_result.json")
    active = _load_json(FIXTURES / "active_affordance_frontier_audit_result.json")
    snapshot = h77._reconstruct_snapshot(
        project=project,
        carrier=carrier,
        carrier_sha256=carrier_sha256,
        carrier_execution_sha256=carrier_execution_sha256,
        projection=projection,
        active_epoch=int(h71["active"]["epoch"]),
        origin_seed_sha256=str(
            active["active_problem"]["current_seed_sha256"]
        ),
        through_trace=str(h63["history_snapshot"]["through_trace"]),
    )
    if (
        snapshot["selection"].action_system.sha256
        != h63["history_lift"]["action_system_sha256"]
    ):
        raise RuntimeError("H63 action-system reconstruction drifted")
    return snapshot


def run_audit() -> dict[str, Any]:
    project = ROOT / "projects/arc3_ls20_gov"
    carrier_path = project / "test_model.py"
    carrier, _kind, carrier_sha256 = load_carrier_path(
        carrier_path,
        project_dir=project,
    )
    projection = carrier._ztare_factored_projection
    carrier_execution_sha256 = carrier_execution_sha256_from_source(
        carrier_path.read_text(encoding="utf-8")
    )

    h95_dir = FIXTURES / "h95_response_transport_square"
    h109_dir = FIXTURES / "h109_restored_sensorimotor_chronology_app_server"
    h95_rows = _arm_rows(h95_dir)
    h109_rows = _arm_rows(h109_dir)
    offers = tuple(
        (path, arm) for path, arm in h95_rows
        if arm["assignment"] == "offer"
    )
    withholds = tuple(
        (path, arm) for path, arm in h95_rows
        if arm["assignment"] == "withhold"
    )
    if len(offers) != 2 or len(withholds) != 2:
        raise RuntimeError("H95 matched-pair cardinality drifted")

    completion_horizons = tuple(
        int(arm["probe"]["first_level_action"])
        for _path, arm in offers
    )
    winning_words = tuple(
        _arm_actions(arm)[:horizon]
        for (_path, arm), horizon in zip(offers, completion_horizons)
    )
    winning_word = winning_words[0]
    if len(set(winning_words)) != 1:
        raise RuntimeError("H95 offers no longer share a winning word")
    if completion_horizons != (12, 12):
        raise RuntimeError("H95 completion horizon drifted")

    h95_experiment = str(offers[0][1]["experiment_sha256"])
    h109_experiment = str(h109_rows[0][1]["experiment_sha256"])
    option_system = _build_option_system(
        (*h95_rows, *h109_rows),
        projection=projection,
        horizon_by_experiment={
            h95_experiment: 12,
            h109_experiment: 8,
        },
    )
    option_fibers = compile_boundary_reachability_fibers(
        option_system,
        operations=OPERATIONS,
        context_key=lambda node: (
            node[0].presentation_assignment,
            node[0].finite_configuration,
            node[0].one_shot_availability,
            node[0].ordered_feasibility_configuration,
        ),
        support_key=lambda node: node,
        source_lineage_keys=lambda node: (node,),
    )

    source_factors = _arm_factors(projection, offers[0][1])
    source_initial = source_factors[0]
    source_initial_node = _option_node(
        projection,
        offers[0][1]["probe"]["observations"][0],
    )
    prefix = _load_json(
        FIXTURES / "h96_causal_object_lineage" / "manifest.json"
    )["descendant_prefix"]
    target_observation = prefix["observations"][-1]
    target_grid = _grid(target_observation)
    target_factor = projection.factor(target_grid)
    target_node = (target_factor, stable_sha256(target_grid))
    aligned_indices = tuple(
        index for index, factor in enumerate(source_factors[:13])
        if factor.controlled_base == target_factor.controlled_base
    )
    if len(aligned_indices) != 1:
        raise RuntimeError("position-only H95/H109 alignment is ambiguous")
    alignment_index = aligned_indices[0]
    winning_suffix = winning_word[alignment_index:]
    target_offer_actions = tuple(
        _arm_actions(arm)[:len(winning_suffix)]
        for _path, arm in h109_rows
        if arm["assignment"] == "offer"
    )
    target_offer_factor_paths = tuple(
        _arm_factors(projection, arm)[:len(winning_suffix) + 1]
        for _path, arm in h109_rows
        if arm["assignment"] == "offer"
    )

    full_source_spec = OptionProgramSpec(
        operations=winning_word,
        initiation_source_sha256s=(stable_sha256(source_initial_node),),
        lineage_refs=tuple(str(path.relative_to(ROOT)) for path, _ in offers),
        imported_ref="h95_matched_winning_word",
    )
    target_full_spec = OptionProgramSpec(
        operations=winning_word,
        initiation_source_sha256s=(stable_sha256(target_node),),
        lineage_refs=(
            "h96_causal_object_lineage/manifest.json#descendant_prefix",
        ),
        imported_ref="h95_full_word_at_h109_target",
    )
    target_suffix_spec = OptionProgramSpec(
        operations=winning_suffix,
        initiation_source_sha256s=(stable_sha256(target_node),),
        lineage_refs=tuple(
            str(path.relative_to(ROOT)) for path, arm in h109_rows
            if arm["assignment"] == "offer"
        ),
        imported_ref="position_only_h95_suffix_at_h109_target",
    )
    withhold_specs = tuple(
        OptionProgramSpec(
            operations=_arm_actions(arm)[:12],
            initiation_source_sha256s=(stable_sha256(source_initial_node),),
            lineage_refs=(str(path.relative_to(ROOT)),),
            imported_ref=f"h95_withhold_pair_{int(arm['pair_index']):02d}",
        )
        for path, arm in withholds
    )
    option_specs = (
        full_source_spec,
        target_suffix_spec,
        *withhold_specs,
    )
    reindexed = reindex_option_programs(option_specs, fibers=option_fibers)
    reindexed_by_sha = {row.option_sha256: row for row in reindexed}
    source_option = reindexed_by_sha[full_source_spec.option_sha256]
    target_suffix_option = reindexed_by_sha[target_suffix_spec.option_sha256]
    target_full_option = reindex_option_program(
        target_full_spec,
        fibers=option_fibers,
    )
    effect_families = compile_effect_option_families(
        reindexed,
        effect_namespace=EFFECT_NAMESPACE,
    )
    source_family, source_variant = _option_identity(
        source_option.option_sha256,
        effect_families,
    )
    target_family, target_variant = _option_identity(
        target_suffix_option.option_sha256,
        effect_families,
    )
    withhold_identities = tuple(
        _option_identity(spec.option_sha256, effect_families)
        for spec in withhold_specs
    )
    available_h95_families = tuple(sorted({
        source_family,
        *(family for family, _variant in withhold_identities),
    }))

    memory = empty_continual_skill_memory()
    choice_context_sha256 = stable_sha256({
        "schema": "ztare-h110-choice-context-v1",
        "source_factor": source_initial,
        "restored_prefix_sha256": stable_sha256(
            offers[0][1]["probe"]["restored_prefix"]
        ),
    })
    continuation_context_sha256 = stable_sha256({
        "schema": "ztare-h110-continuation-context-v1",
        "horizon": 12,
        "controller": "h95_response_transport_square",
    })
    by_pair = {
        int(arm["pair_index"]): (path, arm)
        for path, arm in withholds
    }
    for offer_path, offer_arm in offers:
        pair_index = int(offer_arm["pair_index"])
        withhold_path, withhold_arm = by_pair[pair_index]
        withhold_family, withhold_variant = withhold_identities[
            pair_index - 1
        ]
        for path, arm, family, variant, outcome in (
            (
                offer_path,
                offer_arm,
                source_family,
                source_variant,
                "attained",
            ),
            (
                withhold_path,
                withhold_arm,
                withhold_family,
                withhold_variant,
                "open",
            ),
        ):
            memory = record_task_choice_experience(
                memory,
                task_contract_sha256=TASK_CONTRACT_SHA256,
                trace_ref=str(path.relative_to(ROOT)),
                choice_index=0,
                outcome=outcome,
                choice_context_sha256=choice_context_sha256,
                continuation_context_sha256=continuation_context_sha256,
                chosen_effect_option_family_sha256=family,
                chosen_effect_option_variant_sha256=variant,
                available_effect_option_family_sha256s=(
                    available_h95_families
                ),
                evidence_ref=(
                    str(path.relative_to(ROOT))
                    + "#external_level_at_horizon_12="
                    + str(arm["probe"]["observations"][12][
                        "levels_completed"
                    ])
                ),
            )
    source_judgment = judge_effect_option_task_credit(
        memory,
        effect_option_family_sha256=source_family,
        task_contract_sha256=TASK_CONTRACT_SHA256,
        source_family_sha256s=(),
    )
    target_judgment = judge_effect_option_task_credit(
        memory,
        effect_option_family_sha256=target_family,
        task_contract_sha256=TASK_CONTRACT_SHA256,
        source_family_sha256s=(),
    )

    snapshot = _reconstruct_h63(
        project=project,
        carrier=carrier,
        carrier_sha256=carrier_sha256,
        carrier_execution_sha256=carrier_execution_sha256,
        projection=projection,
    )
    selection = snapshot["selection"]
    h63_system = selection.action_system
    target_key = selection.start_key(
        target_factor,
        observation=target_grid,
        action_history=tuple(prefix["actions"]),
    )
    h63_fibers = compile_boundary_reachability_fibers(
        h63_system,
        operations=OPERATIONS,
        context_key=lambda source: (
            projection.acquisition_key(projection.factor(getattr(
                h63_system.representative(source),
                "observation",
                h63_system.representative(source),
            ))),
            selection.predictive_context_key(getattr(
                h63_system.representative(source),
                "observation",
                h63_system.representative(source),
            )),
        ),
        support_key=lambda source: stable_sha256(getattr(
            h63_system.representative(source),
            "observation",
            h63_system.representative(source),
        )),
        source_lineage_keys=selection.source_lineage_keys,
    )
    h63_plan = plan_boundary_reachability_frontier(
        h63_fibers,
        start_key=target_key,
    )
    controlled_only_matches = tuple(
        source for source in h63_system.fibers
        if projection.factor(getattr(
            h63_system.representative(source),
            "observation",
            h63_system.representative(source),
        )).controlled_base == target_factor.controlled_base
    )

    source_aligned_factor = source_factors[alignment_index]
    factor_differences = _factor_differences(
        source_aligned_factor,
        target_factor,
    )
    route_factor_differences = tuple(
        tuple(
            _factor_differences(
                source_factors[alignment_index + step],
                target_path[step],
            )
            for step in range(len(winning_suffix) + 1)
        )
        for target_path in target_offer_factor_paths
    )
    route_difference_fields = tuple(sorted({
        field
        for path in route_factor_differences
        for step in path
        for field in step
    }))
    target_levels_after_suffix = tuple(
        arm["probe"]["observations"][len(winning_suffix)][
            "levels_completed"
        ]
        for _path, arm in h109_rows
        if arm["assignment"] == "offer"
    )
    source_levels_after_word = tuple(
        arm["probe"]["observations"][12]["levels_completed"]
        for _path, arm in offers
    )

    mutated_configuration = list(source_aligned_factor.finite_configuration)
    mutated_configuration[0] = 1 - int(mutated_configuration[0])
    mutated_feasibility = list(
        source_aligned_factor.ordered_feasibility_configuration
    )
    mutated_feasibility[0] = not mutated_feasibility[0]
    factor_mutations = {
        "position": replace(
            source_aligned_factor,
            controlled_base=((999, 999),),
        ),
        "configuration": replace(
            source_aligned_factor,
            finite_configuration=tuple(mutated_configuration),
        ),
        "budget": replace(
            source_aligned_factor,
            ordered_budget=source_aligned_factor.ordered_budget + 1,
        ),
        "feasibility": replace(
            source_aligned_factor,
            ordered_feasibility_configuration=tuple(mutated_feasibility),
        ),
    }
    negative_fixtures = {
        name: stable_sha256(value) != stable_sha256(source_aligned_factor)
        for name, value in factor_mutations.items()
    }
    changed_word_spec = OptionProgramSpec(
        operations=(*winning_suffix[:-1], (winning_suffix[-1] + 1) % 4),
        initiation_source_sha256s=(stable_sha256(target_node),),
        lineage_refs=("h110_negative_changed_word",),
    )
    changed_word = reindex_option_program(
        changed_word_spec,
        fibers=option_fibers,
    )
    negative_fixtures["option_word"] = (
        changed_word.option_sha256 != target_suffix_option.option_sha256
    )
    changed_lineage = reindex_option_program(
        OptionProgramSpec(
            operations=winning_word,
            initiation_source_sha256s=("0" * 64,),
            lineage_refs=("h110_negative_changed_lineage",),
        ),
        fibers=option_fibers,
    )
    negative_fixtures["source_lineage"] = (
        changed_lineage.status == "unsupported"
        and "initiation_source_absent" in changed_lineage.failure_kinds
    )
    wrong_task = judge_effect_option_task_credit(
        memory,
        effect_option_family_sha256=source_family,
        task_contract_sha256="f" * 64,
        source_family_sha256s=(),
    )
    negative_fixtures["success_authority"] = wrong_task.status == "uncredited"

    checks = {
        "h95_common_winning_word": len(set(winning_words)) == 1,
        "h95_both_complete_at_twelve": (
            completion_horizons == (12, 12)
            and source_levels_after_word == (1, 1)
        ),
        "position_only_alignment_unique": aligned_indices == (4,),
        "h109_executes_position_suffix": (
            target_offer_actions == (winning_suffix, winning_suffix)
        ),
        "required_nonspatial_factor_differs": bool(
            "finite_configuration" in factor_differences
            and {
                "finite_configuration",
                "ordered_budget",
                "ordered_feasibility_configuration",
            } <= set(route_difference_fields)
        ),
        "h63_exact_target_unwitnessed": (
            target_key not in h63_system.fibers
            and h63_plan.status == "start_fiber_unwitnessed"
        ),
        "h95_full_option_reindexed": source_option.status == "stable",
        "h95_full_option_refused_at_target": (
            target_full_option.status == "unsupported"
            and "operation_unsupported" in target_full_option.failure_kinds
        ),
        "position_suffix_is_distinct_effect_family": (
            target_suffix_option.status == "stable"
            and target_family != source_family
        ),
        "h95_effect_family_task_credited": (
            source_judgment.status == "task_credited"
            and source_judgment.enable_support == 4
        ),
        "h109_suffix_effect_family_uncredited": (
            target_judgment.status == "uncredited"
        ),
        "position_coarsening_false_admission": (
            target_offer_actions == (winning_suffix, winning_suffix)
            and target_levels_after_suffix == (0, 0)
            and source_levels_after_word == (1, 1)
        ),
        "all_negative_fixtures_detected": all(negative_fixtures.values()),
        "no_new_controller_or_environment_contact": True,
    }
    status = "stage_a_supported" if all(checks.values()) else "rejected"
    payload = {
        "schema": "ztare-h110-viability-conditioned-option-recall-v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "status": status,
        "environment_contact": False,
        "controller_contact": False,
        "identities": {
            "carrier_sha256": carrier_sha256,
            "carrier_execution_sha256": carrier_execution_sha256,
            "projection_sha256": projection.projection_sha256,
            "h63_action_system_sha256": h63_system.sha256,
            "task_contract_sha256": TASK_CONTRACT_SHA256,
            "h95_experiment_sha256": h95_experiment,
            "h109_experiment_sha256": h109_experiment,
            "target_observation_sha256": target_observation["sha256"],
            "target_factor_sha256": stable_sha256(target_factor),
            "target_h63_key_sha256": stable_sha256(target_key),
        },
        "winning_option": {
            "completion_horizons": list(completion_horizons),
            "operations": list(winning_word),
            "operation_count": len(winning_word),
            "source_option_sha256": source_option.option_sha256,
            "source_option_status": source_option.status,
            "source_effect_family_sha256": source_family,
            "source_effect_variant_sha256": source_variant,
            "source_task_judgment": source_judgment.to_receipt(),
        },
        "position_coarsening_counterexample": {
            "alignment_index": alignment_index,
            "controlled_base": target_factor.controlled_base,
            "winning_suffix": list(winning_suffix),
            "h109_offer_suffixes": [list(row) for row in target_offer_actions],
            "source_levels_after_word": list(source_levels_after_word),
            "target_levels_after_suffix": list(target_levels_after_suffix),
            "factor_differences": factor_differences,
            "route_difference_fields": list(route_difference_fields),
            "route_factor_differences": route_factor_differences,
        },
        "target_option": {
            "full_word_reindex": target_full_option.to_receipt(),
            "position_suffix_reindex": target_suffix_option.to_receipt(),
            "position_suffix_effect_family_sha256": target_family,
            "position_suffix_effect_variant_sha256": target_variant,
            "position_suffix_task_judgment": target_judgment.to_receipt(),
            "refusal": (
                "full_option_initiation_effect_unsupported;"
                "position_suffix_effect_family_uncredited"
            ),
        },
        "frozen_history_viability": {
            "h63_node_count": len(h63_system.fibers),
            "target_exact_node_present": target_key in h63_system.fibers,
            "target_boundary_plan_status": h63_plan.status,
            "controlled_position_match_count": len(controlled_only_matches),
            "exact_viability_authority": "witnessed_paths_only",
        },
        "negative_fixtures": negative_fixtures,
        "checks": checks,
        "claim_boundary": {
            "one_frozen_graph_refusal_supported": status == "stage_a_supported",
            "global_unrecoverability_supported": False,
            "benchmark_improvement_supported": False,
            "compounding_supported": False,
            "takeoff_supported": False,
            "literature_novelty_claimed": False,
        },
    }
    payload["sha256"] = stable_sha256(payload)
    return payload


def main() -> int:
    output = run_audit()
    result_path = FIXTURES / "h110_viability_conditioned_option_recall_result.json"
    result_path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "result_path": str(result_path.relative_to(ROOT)),
        "status": output["status"],
        "sha256": output["sha256"],
        "checks": output["checks"],
        "winning_option": output["winning_option"],
        "target_option": output["target_option"],
        "frozen_history_viability": output["frozen_history_viability"],
    }, indent=2, sort_keys=True))
    return 0 if output["status"] == "stage_a_supported" else 1


if __name__ == "__main__":
    raise SystemExit(main())
