#!/usr/bin/env python3
"""Audit continual guarded-skill reuse on the frozen H63 evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


FIXTURES = Path(__file__).resolve().parent
ROOT = FIXTURES.parents[2]
sys.path.insert(0, str(FIXTURES))
sys.path.insert(0, str(ROOT / "src"))

import task_conditioned_skill_basin_audit as h77

from ztare.common.continual_skill_memory import (
    IntrinsicLearningSignal,
    consumable_skill_revision_sha256s,
    empty_continual_skill_memory,
    judge_effect_option_task_credit,
    merge_guarded_skill_library,
    record_intrinsic_signal,
    record_library_quotient_transport,
)
from ztare.common.boundary_reachability import (
    compile_effect_option_families,
    compile_boundary_reachability_fibers,
    reindex_option_programs,
)
from ztare.common.equivariance import stable_sha256
from ztare.common.guarded_skill_compiler import (
    compile_guarded_execution_plan,
)
from ztare.common.predictive_quotient import compile_predictive_quotient
from ztare.worldmodel.carrier_loader import load_carrier_path
from ztare.worldmodel.mechanism_effects import (
    compile_history_guarded_skill_library,
    guarded_skill_option_specs,
    guarded_skill_traces_from_history_evidence,
)
from ztare.worldmodel.patch_base_carrier import (
    carrier_execution_sha256_from_source,
)


NAMESPACE = "arc3-intervention-algebra-v1:arity=4"
CHECKPOINTS = (1, 2, 4, 8, 12, 16, 20, 24, 28)


def _load_json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _compile(rows, *, projection, history_lift):
    return compile_history_guarded_skill_library(
        tuple(rows),
        projection=projection,
        history_lift=history_lift,
        min_word_length=2,
        max_word_length=8,
        min_variant_support=2,
    )


def _ordinary_prefix(trace):
    rows = []
    for transition in trace.transitions:
        if transition.boundary_kind or transition.successor is None:
            break
        rows.append(transition)
    return tuple(rows)


def _plan_trace(library, trace, allowed):
    ordinary = _ordinary_prefix(trace)
    if not ordinary:
        return None
    relation = {
        (row.source, row.operation): row.successor for row in ordinary
    }
    return compile_guarded_execution_plan(
        library,
        start_key=ordinary[0].source,
        operations=tuple(row.operation for row in ordinary),
        transition=lambda source, operation: relation.get(
            (source, operation)
        ),
        allowed_skill_sha256s=allowed,
    )


def run_audit() -> dict:
    h63 = _load_json("post_support_probe1_recompile_audit_result.json")
    h71 = _load_json("joint_relation_recompile_audit_result.json")
    active = _load_json("active_affordance_frontier_audit_result.json")
    task = _load_json("exact_relational_search_audit_result.json")["task"]
    project = ROOT / "projects/arc3_ls20_gov"
    carrier_path = project / "test_model.py"
    carrier, _kind, carrier_sha = load_carrier_path(
        carrier_path,
        project_dir=project,
    )
    projection = carrier._ztare_factored_projection
    execution_sha = carrier_execution_sha256_from_source(
        carrier_path.read_text(encoding="utf-8")
    )
    active_epoch = int(h71["active"]["epoch"])
    origin_seed = str(active["active_problem"]["current_seed_sha256"])
    through_trace = str(h63["history_snapshot"]["through_trace"])
    snapshot = h77._reconstruct_snapshot(
        project=project,
        carrier=carrier,
        carrier_sha256=carrier_sha,
        carrier_execution_sha256=execution_sha,
        projection=projection,
        active_epoch=active_epoch,
        origin_seed_sha256=origin_seed,
        through_trace=through_trace,
    )
    selection = snapshot["selection"]
    system = selection.action_system
    if system.sha256 != h63["history_lift"]["action_system_sha256"]:
        raise RuntimeError("H63 source-system identity drifted")
    trajectories = tuple(snapshot["trajectories"])
    context = (
        "arc3-frozen-h63",
        projection.projection_sha256,
        execution_sha,
        active_epoch,
    )

    full_library = _compile(
        trajectories,
        projection=projection,
        history_lift=selection,
    )
    fibers = compile_boundary_reachability_fibers(
        system,
        operations=(0, 1, 2, 3),
        context_key=lambda source: (
            projection.acquisition_key(projection.factor(
                getattr(
                    system.representative(source),
                    "observation",
                    system.representative(source),
                )
            )),
            selection.predictive_context_key(getattr(
                system.representative(source),
                "observation",
                system.representative(source),
            )),
        ),
        support_key=lambda source: stable_sha256(getattr(
            system.representative(source),
            "observation",
            system.representative(source),
        )),
        source_lineage_keys=selection.source_lineage_keys,
    )
    option_specs = guarded_skill_option_specs(
        full_library,
        operation_namespace=NAMESPACE,
    )
    reindexed_options = reindex_option_programs(
        option_specs,
        fibers=fibers,
    )
    effect_option_families = compile_effect_option_families(
        reindexed_options,
        effect_namespace=(
            "compiled-fiber-effects-v1:"
            + projection.projection_sha256
        ),
    )
    effect_option_rows = []
    for option in reindexed_options:
        effect_option_rows.append({
            "family_sha256": option.source_family_sha256,
            "revision_sha256": option.source_revision_sha256,
            "operations": list(option.operations),
            "operation_count": len(option.operations),
            "status": option.status,
            "requested_initiation_count": (
                option.requested_initiation_count
            ),
            "resolved_initiation_count": (
                option.resolved_initiation_count
            ),
            "effect_variant_count": len(option.variants),
            "failure_kinds": list(option.failure_kinds),
        })
    quotient = compile_predictive_quotient(
        system,
        operations=(0, 1, 2, 3),
    )
    memory = merge_guarded_skill_library(
        empty_continual_skill_memory(),
        full_library,
        operation_namespace=NAMESPACE,
        context_key=context,
    )
    memory, quotient_receipt = record_library_quotient_transport(
        memory,
        full_library,
        operation_namespace=NAMESPACE,
        context_key=context,
        predictive_quotient=quotient,
    )
    allowed, consumption = consumable_skill_revision_sha256s(
        memory,
        full_library,
        operation_namespace=NAMESPACE,
        context_key=context,
    )
    effect_task_judgments = tuple(
        judge_effect_option_task_credit(
            memory,
            effect_option_family_sha256=family.family_sha256,
            task_contract_sha256=task["contract_sha256"],
            source_family_sha256s=tuple(sorted({
                implementation.source_family_sha256
                for implementation in family.implementations
                if implementation.source_family_sha256
            })),
        )
        for family in effect_option_families
    )
    decision_pricing_invocations = frozenset(
        (
            implementation.source_revision_sha256,
            source_sha256,
        )
        for family, judgment in zip(
            effect_option_families,
            effect_task_judgments,
        )
        if judgment.status == "task_credited"
        for implementation in family.implementations
        if implementation.source_revision_sha256 in allowed
        for source_sha256, _target_sha256
        in implementation.source_target_sha256_pairs
    )

    checkpoint_rows = []
    checkpoint_memory = empty_continual_skill_memory()
    for count in CHECKPOINTS:
        if count > len(trajectories):
            continue
        library = _compile(
            trajectories[:count],
            projection=projection,
            history_lift=selection,
        )
        checkpoint_memory = merge_guarded_skill_library(
            checkpoint_memory,
            library,
            operation_namespace=NAMESPACE,
            context_key=context,
        )
        checkpoint_rows.append({
            "trajectory_count": count,
            "fresh_program_count": len(library.programs),
            "cumulative_family_count": len(
                checkpoint_memory.families
            ),
            "sampled_revision_count": sum(
                len(family.revision_sha256s)
                for family in checkpoint_memory.families
            ),
            "primitive_tokens": library.primitive_token_count,
            "description_length": library.description_length,
            "compression_gain": library.compression_gain,
        })

    split = max(1, (len(trajectories) * 3) // 4)
    discovery = _compile(
        trajectories[:split],
        projection=projection,
        history_lift=selection,
    )
    discovery_memory = merge_guarded_skill_library(
        empty_continual_skill_memory(),
        discovery,
        operation_namespace=NAMESPACE,
        context_key=context,
    )
    discovery_memory, _transport = record_library_quotient_transport(
        discovery_memory,
        discovery,
        operation_namespace=NAMESPACE,
        context_key=context,
        predictive_quotient=quotient,
    )
    discovery_allowed, _receipt = consumable_skill_revision_sha256s(
        discovery_memory,
        discovery,
        operation_namespace=NAMESPACE,
        context_key=context,
    )
    holdout_traces = guarded_skill_traces_from_history_evidence(
        trajectories[split:],
        projection=projection,
        history_lift=selection,
    )
    holdout_rows = []
    planned = []
    for trace in holdout_traces:
        plan = _plan_trace(discovery, trace, discovery_allowed)
        if plan is None:
            continue
        planned.append((trace, plan))
        holdout_rows.append({
            "trace_ref": trace.trace_ref,
            "operation_count": len(plan.primitive_operations),
            "status": plan.status,
            "skill_token_count": plan.skill_token_count,
            "control_token_count": len(plan.tokens),
            "control_token_savings": plan.token_savings,
        })

    negative_control = {
        "status": "not_applicable",
        "reason": "no held-out plan consumed a skill revision",
    }
    selected = next(
        (
            (trace, plan, token)
            for trace, plan in planned
            for token in plan.tokens
            if token.kind == "skill"
        ),
        None,
    )
    if selected is not None:
        trace, before_plan, token = selected
        program = next(
            row for row in discovery.programs
            if row.skill_sha256 == token.skill_sha256
        )
        family_sha = program.structural_sha256(NAMESPACE)
        counterexample = IntrinsicLearningSignal(
            family_sha256=family_sha,
            revision_sha256=program.skill_sha256,
            context_sha256=stable_sha256(context),
            evidence_epoch_sha256="offline-negative-control",
            kind="cegar_counterexample",
            disposition="requires_refinement",
            failed_step=0,
            evidence_refs=("offline-negative-control#0",),
        )
        revoked_memory = record_intrinsic_signal(
            discovery_memory,
            counterexample,
        )
        revoked_allowed, revoked_receipt = (
            consumable_skill_revision_sha256s(
                revoked_memory,
                discovery,
                operation_namespace=NAMESPACE,
                context_key=context,
            )
        )
        after_plan = _plan_trace(
            discovery,
            trace,
            revoked_allowed,
        )
        if after_plan is None:
            raise RuntimeError("negative-control route became undefined")
        negative_control = {
            "status": "passed",
            "synthetic_counterexample": True,
            "revoked_revision_sha256": program.skill_sha256,
            "before_skill_token_count": before_plan.skill_token_count,
            "after_skill_token_count": after_plan.skill_token_count,
            "before_control_token_count": len(before_plan.tokens),
            "after_control_token_count": len(after_plan.tokens),
            "revision_remained_allowed": (
                program.skill_sha256 in revoked_allowed
            ),
            "judgment": next(
                row for row in revoked_receipt["judgments"]
                if row["revision_sha256"] == program.skill_sha256
            ),
        }

    return {
        "schema": "ztare-frozen-arc-continual-skill-audit-v4",
        "status": "offline_complete",
        "environment_contact": False,
        "identities": {
            "h63_action_system_sha256": system.sha256,
            "projection_sha256": projection.projection_sha256,
            "carrier_execution_sha256": execution_sha,
            "trajectory_count": len(trajectories),
        },
        "current": {
            "program_count": len(full_library.programs),
            "family_count": len(memory.families),
            "revision_count": sum(
                len(family.revision_sha256s)
                for family in memory.families
            ),
            "primitive_token_count": full_library.primitive_token_count,
            "description_length": full_library.description_length,
            "compression_gain": full_library.compression_gain,
            "predictive_quotient": {
                "passed_section": quotient.passed_section,
                "passed_transport": quotient.passed_transport,
                "source_fiber_count": quotient.source_fiber_count,
                "class_count": quotient.class_count,
                "noncommuting_relation_count": sum(
                    len(effects) > 1
                    for effects in quotient.relation_effects.values()
                ),
            },
            "quotient_transport_status": quotient_receipt["status"],
            "consumable_revision_count": len(allowed),
            "consumption_status_counts": {
                status: sum(
                    row["status"] == status
                    for row in consumption["judgments"]
                )
                for status in sorted({
                    row["status"] for row in consumption["judgments"]
                })
            },
        },
        "chronology": {
            "checkpoints": checkpoint_rows,
            "final_sampled_family_count": len(
                checkpoint_memory.families
            ),
            "final_sampled_revision_count": sum(
                len(family.revision_sha256s)
                for family in checkpoint_memory.families
            ),
        },
        "effect_option_reindex": {
            "program_count": len(effect_option_rows),
            "status_counts": {
                status: sum(
                    row["status"] == status
                    for row in effect_option_rows
                )
                for status in sorted({
                    row["status"] for row in effect_option_rows
                })
            },
            "single_effect_variant_count": sum(
                row["effect_variant_count"] == 1
                for row in effect_option_rows
            ),
            "effect_schema_count": len(effect_option_families),
            "effect_context_variant_count": sum(
                len(family.context_variants)
                for family in effect_option_families
            ),
            "effect_family_rows": [
                {
                    "family_sha256": family.family_sha256,
                    "effect_trace_sha256": stable_sha256(
                        family.effect_trace
                    ),
                    "context_variant_count": len(
                        family.context_variants
                    ),
                    "terminal_context_sha256s": sorted({
                        stable_sha256(variant.terminal_context)
                        for variant in family.context_variants
                    }),
                    "implementation_count": len(family.implementations),
                    "initiation_count": len({
                        source_sha256
                        for implementation in family.implementations
                        for source_sha256, _target_sha256
                        in implementation.source_target_sha256_pairs
                    }),
                    "source_revision_sha256s": sorted({
                        implementation.source_revision_sha256
                        for implementation in family.implementations
                    }),
                }
                for family in effect_option_families
            ],
            "effect_trace_class_count": len({
                stable_sha256(family.effect_trace)
                for family in effect_option_families
            }),
            "effect_trace_context_multiplicity": [
                {
                    "effect_trace_sha256": stable_sha256(
                        family.effect_trace
                    ),
                    "terminal_context_count": len({
                        stable_sha256(variant.terminal_context)
                        for variant in family.context_variants
                    }),
                    "context_variant_count": len(
                        family.context_variants
                    ),
                }
                for family in effect_option_families
            ],
            "task_contract_sha256": task["contract_sha256"],
            "task_judgment_status_counts": {
                status: sum(
                    judgment.status == status
                    for judgment in effect_task_judgments
                )
                for status in sorted({
                    judgment.status
                    for judgment in effect_task_judgments
                })
            },
            "task_credited_effect_family_count": sum(
                judgment.status == "task_credited"
                for judgment in effect_task_judgments
            ),
            "decision_pricing_invocation_count": len(
                decision_pricing_invocations
            ),
            "rows": effect_option_rows,
        },
        "holdout": {
            "discovery_trajectory_count": split,
            "holdout_trajectory_count": len(trajectories) - split,
            "lowered_segment_count": len(holdout_rows),
            "compiled_segment_count": sum(
                row["status"] == "compiled_plan"
                for row in holdout_rows
            ),
            "primitive_operation_count": sum(
                row["operation_count"] for row in holdout_rows
            ),
            "control_token_count": sum(
                row["control_token_count"] for row in holdout_rows
            ),
            "control_token_savings": sum(
                row["control_token_savings"] for row in holdout_rows
            ),
            "environment_interventions_saved": 0,
            "rows": holdout_rows,
        },
        "counterexample_negative_control": negative_control,
        "claim_boundary": (
            "Held-out savings are planner control tokens. Primitive "
            "environment interventions remain unchanged."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=FIXTURES / "continual_skill_memory_audit_result.json",
    )
    args = parser.parse_args()
    result = run_audit()
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(args.output),
        "status": result["status"],
        "current": result["current"],
        "holdout": {
            key: value
            for key, value in result["holdout"].items()
            if key != "rows"
        },
        "counterexample_negative_control": result[
            "counterexample_negative_control"
        ],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
