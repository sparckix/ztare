#!/usr/bin/env python3
"""Read-only audit for the partial-action transport hypothesis."""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
from dataclasses import replace
import hashlib
from itertools import combinations
import json
from pathlib import Path

from ztare.common.equivariance import stable_sha256
from ztare.common.factored_search import search_factored
from ztare.common.guarded_skill_compiler import (
    compile_guarded_execution_plan,
)
from ztare.common.guarded_experiment_protocol import (
    ProtocolYieldWeights,
)
from ztare.common.boundary_reachability import (
    OptionProgramSpec,
    compile_boundary_reachability_fibers,
    plan_boundary_reachability_frontier,
    reindex_option_programs,
)
from ztare.common.partial_action_system import plan_observed_action_frontier
from ztare.common.predictive_quotient import (
    compile_predictive_compatibility,
    compile_predictive_quotient,
    plan_predictive_support_frontier,
    plan_predictive_quotient_frontier,
)
from ztare.worldmodel.carrier_loader import load_carrier_path
from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.gates import law_scored_view
from ztare.worldmodel.mechanism_effects import (
    HistoryTrajectoryEvidence,
    build_fiber_action_system,
    compile_history_guarded_skill_library,
    fiber_mechanism_effect,
    fiber_transition_key,
    predictive_prefixes_from_transitions,
)
from ztare.worldmodel.patch_base_carrier import (
    carrier_execution_sha256_from_source,
)
from ztare.worldmodel.mechanism_protocols import (
    MechanismAcquisitionFrontiers,
    select_acquisition_protocols,
    select_witnessed_protocols,
)
from ztare.worldmodel.policy import W_COMPRESSION, W_COVERAGE, W_EIG


def _support_rank(system, cap: int = 30) -> list[dict]:
    rows = []
    for effect_class, support in system.effect_support.most_common(cap):
        operation, effect = effect_class
        rows.append({
            "operation": repr(operation),
            "effect": repr(effect),
            "effect_sha256": stable_sha256(effect),
            "support": support,
            "source_count": len(system.effect_sources[effect_class]),
            "boundary_kind": system.boundary_kinds.get(effect_class, ""),
        })
    return rows


def _failure_quotient(carrier, projection, bank: EpisodeLog, system) -> dict:
    ranked = {
        row.class_key: row
        for row in system.ranked
    }
    groups: dict[tuple, dict] = {}
    mechanism_failures = render_only_failures = 0
    scored_rows = tuple(law_scored_view(bank))
    for index, transition in enumerate(scored_rows):
        predicted = carrier(transition.s, transition.a, transition.t)
        if predicted == transition.s_next:
            continue
        source_factors = projection.factor(transition.s)
        actual_factors = projection.factor(transition.s_next)
        actual_effect = fiber_mechanism_effect(
            source_factors,
            actual_factors,
        )
        predicted_effect = (
            fiber_mechanism_effect(
                source_factors,
                projection.factor(predicted),
            )
            if predicted is not None
            else ("undefined",)
        )
        factor_match = (
            predicted is not None
            and fiber_transition_key(projection.factor(predicted))
            == fiber_transition_key(actual_factors)
        )
        kind = "render_only" if factor_match else "mechanism"
        if factor_match:
            render_only_failures += 1
        else:
            mechanism_failures += 1
        effect_class = (transition.a, actual_effect)
        key = (
            kind,
            transition.a,
            stable_sha256(actual_effect),
            stable_sha256(predicted_effect),
        )
        group = groups.setdefault(key, {
            "kind": kind,
            "operation": repr(transition.a),
            "actual_effect": repr(actual_effect),
            "actual_effect_sha256": stable_sha256(actual_effect),
            "predicted_effect": repr(predicted_effect),
            "predicted_effect_sha256": stable_sha256(predicted_effect),
            "count": 0,
            "wrong_cell_count": 0,
            "first_scored_row": index,
            "evidence_refs": [],
            "actual_effect_support": system.effect_support.get(
                effect_class, 0
            ),
            "exception_score": (
                ranked[effect_class].score
                if effect_class in ranked
                else 0.0
            ),
        })
        group["count"] += 1
        group["wrong_cell_count"] += (
            sum(
                left != right
                for left_row, right_row in zip(predicted, transition.s_next)
                for left, right in zip(left_row, right_row)
            )
            if predicted is not None
            else sum(len(row) for row in transition.s_next)
        )
        if len(group["evidence_refs"]) < 8:
            group["evidence_refs"].append(
                f"law_scored_view(episode_001.jsonl)#{index}"
            )
    ordered = sorted(
        groups.values(),
        key=lambda row: (
            -row["count"],
            -row["exception_score"],
            row["actual_effect_sha256"],
        ),
    )
    return {
        "scored_rows": len(scored_rows),
        "failed_rows": mechanism_failures + render_only_failures,
        "mechanism_failed_rows": mechanism_failures,
        "render_only_failed_rows": render_only_failures,
        "failure_group_count": len(ordered),
        "groups": ordered[:80],
    }


def _renewal_coordinate_audit(projection, bank: EpisodeLog) -> dict:
    """Compare translation and retraction coordinates on positive renewals."""
    rows = []
    for index, transition in enumerate(law_scored_view(bank)):
        source = projection.factor(transition.s)
        target = projection.factor(transition.s_next)
        delta = target.ordered_budget - source.ordered_budget
        if delta <= 0:
            continue
        source_base = source.controlled_base
        target_base = target.controlled_base
        translation = None
        if len(source_base) == len(target_base) == 1:
            translation = (
                target_base[0][0] - source_base[0][0],
                target_base[0][1] - source_base[0][1],
            )
        rows.append({
            "index": index,
            "operation": transition.a,
            "budget_delta": delta,
            "source_base": source_base,
            "target_base": target_base,
            "translation": translation,
            "source_configuration": source.finite_configuration,
            "target_configuration": target.finite_configuration,
            "source_presentation": source.presentation_assignment,
            "source_operation_domain": source.operation_domain_assignment,
            "source_availability": source.one_shot_availability,
            "source_budget": source.ordered_budget,
        })

    def frequency(key):
        counts: dict[str, dict] = {}
        for row in rows:
            value = row[key]
            digest = stable_sha256(value)
            item = counts.setdefault(digest, {
                "value": repr(value),
                "sha256": digest,
                "count": 0,
            })
            item["count"] += 1
        return sorted(
            counts.values(),
            key=lambda item: (-item["count"], item["sha256"]),
        )

    target_rank = frequency("target_base")
    translation_rank = frequency("translation")
    feature_names = (
        "operation",
        "source_configuration",
        "source_presentation",
        "source_operation_domain",
        "source_availability",
        "source_budget",
    )
    unique_rows = {}
    for row in rows:
        identity = tuple(row[name] for name in feature_names), row["target_base"]
        unique_rows[stable_sha256(identity)] = row
    determinant_rows = []
    for size in range(1, len(feature_names) + 1):
        for selected in combinations(feature_names, size):
            groups: dict[tuple, Counter] = defaultdict(Counter)
            for row in unique_rows.values():
                groups[tuple(row[name] for name in selected)][
                    row["target_base"]
                ] += 1
            errors = sum(
                sum(counts.values()) - max(counts.values())
                for counts in groups.values()
            )
            determinant_rows.append({
                "features": list(selected),
                "error_rows": errors,
                "distinct_inputs": len(groups),
                "distinct_evidence_rows": len(unique_rows),
            })
    determinant_rows.sort(
        key=lambda row: (
            row["error_rows"],
            len(row["features"]),
            row["distinct_inputs"],
            row["features"],
        )
    )
    return {
        "renewal_rows": len(rows),
        "unique_source_bases": len({
            stable_sha256(row["source_base"]) for row in rows
        }),
        "unique_target_bases": len(target_rank),
        "unique_translations": len(translation_rank),
        "unique_target_configurations": len({
            stable_sha256(row["target_configuration"]) for row in rows
        }),
        "unique_source_configurations": len({
            stable_sha256(row["source_configuration"]) for row in rows
        }),
        "target_base_rank": target_rank[:20],
        "translation_rank": translation_rank[:20],
        "prediction_time_determinants": determinant_rows[:30],
        "description_preference": (
            "target_anchor"
            if len(target_rank) < len(translation_rank)
            else "translation"
            if len(translation_rank) < len(target_rank)
            else "tied"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--trace", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--active-only",
        action="store_true",
        help="skip full-bank failure quotient and renewal analysis",
    )
    parser.add_argument(
        "--skip-model-search",
        action="store_true",
        help="compile the witnessed relation without bounded carrier search",
    )
    parser.add_argument(
        "--skip-predictive-analysis",
        action="store_true",
        help=(
            "skip quotient and pairwise compatibility diagnostics when the "
            "registered question concerns only the reachability fibers"
        ),
    )
    parser.add_argument(
        "--exhaustive-history-candidates",
        action="store_true",
        help="evaluate dominated history suffixes for equivalence audits",
    )
    parser.add_argument(
        "--inspect-pair-sha256",
        nargs=2,
        metavar=("LEFT", "RIGHT"),
        help="inspect one concrete source pair by stable SHA-256",
    )
    parser.add_argument(
        "--option-receipt",
        help=(
            "prior audit JSON whose predictive_quotient options should be "
            "reindexed by concrete initiation lineage"
        ),
    )
    args = parser.parse_args()

    project = Path(args.project).resolve()
    carrier, _kind, carrier_sha = load_carrier_path(
        project / "test_model.py",
        project_dir=project,
    )
    projection = getattr(carrier, "_ztare_factored_projection", None)
    if projection is None:
        raise SystemExit("carrier has no factored projection")
    carrier_execution_sha = carrier_execution_sha256_from_source(
        (project / "test_model.py").read_text(encoding="utf-8")
    )

    bank_path = project / "raw/episodes/episode_001.jsonl"
    bank = EpisodeLog.read_jsonl(bank_path)
    bank_rows = tuple(bank)
    bank_system = None
    failure_quotient = None
    renewal_coordinate_audit = None
    if not args.active_only:
        bank_system = build_fiber_action_system(
            bank_rows,
            projection=projection,
            evidence_ref="raw/episodes/episode_001.jsonl",
        )
        failure_quotient = _failure_quotient(
            carrier,
            projection,
            bank,
            bank_system,
        )
        renewal_coordinate_audit = _renewal_coordinate_audit(
            projection,
            bank,
        )

    trace_path = Path(args.trace).resolve()
    trace_ref = str(trace_path.relative_to(project))
    trace = EpisodeLog.read_jsonl(trace_path)
    trace_rows = tuple(trace)
    active_epoch = (
        trace_rows[0].identity.source_epoch
        if trace_rows
        and trace_rows[0].identity is not None
        else None
    )
    active_rows = tuple(
        law_scored_view(bank, source_epoch=active_epoch)
        if active_epoch is not None
        else law_scored_view(bank)
    )
    known_law_triples = {
        (transition.s, transition.a, transition.s_next)
        for transition in active_rows
    }
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    if isinstance(report.get("cycles"), list):
        play = next(
            (
                row
                for row in reversed(report["cycles"])
                if isinstance(row, dict)
                and "non_discharge_edge_indices" in row
                and (
                    not isinstance(row.get("eval_slice"), dict)
                    or row["eval_slice"].get("path") == trace_ref
                )
            ),
            next(
                row
                for row in reversed(report["cycles"])
                if isinstance(row, dict)
                and "non_discharge_edge_indices" in row
            ),
        )
    else:
        play = report
    declared_boundary_indices = frozenset(
        int(value)
        for value in (play.get("non_discharge_edge_indices") or ())
    )
    boundary_indices = frozenset(
        index
        for index in declared_boundary_indices
        if (
            0 <= index < len(trace_rows)
            and (
                trace_rows[index].s,
                trace_rows[index].a,
                trace_rows[index].s_next,
            ) not in known_law_triples
        )
    )
    active_segment_index = next(
        (
            index
            for index, segment in enumerate(
                play.get("execution_segments") or ()
            )
            if isinstance(segment, dict)
            and segment.get("segment_kind") == "active_control"
        ),
        0,
    )
    history_prefix = tuple(
        play.get("active_action_history_prefix")
        or (
            action
            for segment in (
                play.get("execution_segments") or ()
            )[:active_segment_index]
            if isinstance(segment, dict)
            and segment.get("segment_kind") != "verified_origin"
            for action in (segment.get("actions") or ())
        )
    )
    operation_effect_prefix = tuple(
        tuple(token)
        for token in (
            play.get("active_operation_effect_history_prefix") or ()
        )
    )
    boundary_edges = tuple(
        (
            trace_rows[index].s,
            trace_rows[index].a,
            f"{trace_path.relative_to(project)}#{index}",
            tuple((
                *history_prefix,
                *(row.a for row in trace_rows[:index]),
            )),
            predictive_prefixes_from_transitions(
                trace_rows[:index],
                projection=projection,
                action_prefix=history_prefix,
                operation_effect_prefix=operation_effect_prefix,
            )[1],
        )
        for index in sorted(boundary_indices)
        if 0 <= index < len(trace_rows)
    )
    current_seed_sha = str(
        (play.get("seed_replay") or {}).get("seed_sha256") or ""
    )
    if not current_seed_sha:
        try:
            current_seed_sha = hashlib.sha256(
                (
                    project
                    / "workspace"
                    / "latest_level_boundary_seed.json"
                ).read_bytes()
            ).hexdigest()
        except OSError:
            current_seed_sha = ""
    ledger_path = project / "workspace" / "sealed_eval_slices.jsonl"
    history_trajectories = []
    ledger_rows = list(
        json.loads(line)
        for line in ledger_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
    trace_ledger_positions = [
        index
        for index, ledger_row in enumerate(ledger_rows)
        if str(ledger_row.get("path") or "") == trace_ref
    ]
    excluded_future_history_count = 0
    if trace_ledger_positions:
        cut = trace_ledger_positions[-1] + 1
        excluded_future_history_count = len(ledger_rows) - cut
        ledger_rows = ledger_rows[:cut]
    for ledger_row in ledger_rows:
        declared = ledger_row.get("non_discharge_edge_indices")
        if (
            (
                ledger_row.get("source_carrier_sha256") != carrier_sha
                and ledger_row.get("source_carrier_execution_sha256")
                != carrier_execution_sha
            )
            or ledger_row.get("source_epoch") != active_epoch
            or (
                current_seed_sha
                and ledger_row.get("origin_seed_sha256")
                != current_seed_sha
            )
        ):
            continue
        slice_path = project / str(ledger_row.get("path") or "")
        if not slice_path.is_file():
            continue
        trajectory_rows = tuple(EpisodeLog.read_jsonl(slice_path))
        declared = declared if isinstance(declared, list) else []
        indices = frozenset(
            int(index)
            for index in declared
            if isinstance(index, int)
            and not isinstance(index, bool)
            and 0 <= index < len(trajectory_rows)
            and (
                trajectory_rows[index].s,
                trajectory_rows[index].a,
                trajectory_rows[index].s_next,
            ) not in known_law_triples
        )
        stored_effect_prefix = tuple(
            tuple(token)
            for token in (
                ledger_row.get("history_prefix_operation_effects") or ()
            )
        )
        stored_action_prefix = tuple(
            ledger_row.get("history_prefix_actions") or ()
        )
        if (
            current_seed_sha
            and ledger_row.get("origin_seed_sha256") == current_seed_sha
            and not stored_effect_prefix
        ):
            stored_action_prefix = ()
        history_trajectories.append(HistoryTrajectoryEvidence(
            transitions=trajectory_rows,
            action_prefix=stored_action_prefix or history_prefix,
            operation_effect_prefix=(
                stored_effect_prefix or operation_effect_prefix
            ),
            boundary_indices=indices,
            evidence_ref=str(ledger_row.get("path") or "sealed_slice"),
        ))

    active_system = build_fiber_action_system(
        active_rows,
        projection=projection,
        evidence_ref=(
            f"law_scored_view(raw/episodes/episode_001.jsonl,"
            f"source_epoch={active_epoch!r})"
        ),
        explicit_boundary_edges=boundary_edges,
    )
    trace_system = build_fiber_action_system(
        trace_rows,
        projection=projection,
        evidence_ref=str(trace_path.relative_to(project)),
        explicit_boundary_indices=boundary_indices,
    )
    mechanism_problem = projection.mechanism_acquisition_problem(
        start=trace_rows[0].s,
        evidence_transitions=active_rows,
        predict=carrier,
        evidence_ref="raw/episodes/episode_001.jsonl",
        boundary_edges=boundary_edges,
        history_trajectories=tuple(history_trajectories),
        exhaustive_history_candidates=(
            args.exhaustive_history_candidates
        ),
    )
    mechanism_search = (
        search_factored(
            predict=mechanism_problem.predict,
            start=trace_rows[0].s,
            interventions=(0, 1, 2, 3),
            problem=mechanism_problem,
            start_time=trace_rows[0].t,
            max_depth=120,
            max_states=5000,
        )
        if mechanism_problem is not None and not args.skip_model_search
        else None
    )
    mechanism_start_key = (
        mechanism_problem.observed_start_key(
            trace_rows[0].s,
            history_prefix,
            operation_effect_prefix,
        )
        if mechanism_problem is not None
        else fiber_transition_key(
            projection.factor(trace_rows[0].s)
        )
    )
    observed_frontier_plan = plan_observed_action_frontier(
        (
            mechanism_problem.action_system
            if mechanism_problem is not None
            else active_system
        ),
        start_key=mechanism_start_key,
        operations=(0, 1, 2, 3),
        max_depth=128,
    )
    predictive_quotient = (
        compile_predictive_quotient(
            mechanism_problem.action_system,
            operations=(0, 1, 2, 3),
        )
        if mechanism_problem is not None
        and not args.skip_predictive_analysis
        else None
    )
    predictive_frontier_plan = (
        plan_predictive_quotient_frontier(
            predictive_quotient,
            source_system=mechanism_problem.action_system,
            start_source_key=mechanism_start_key,
            operations=(0, 1, 2, 3),
            max_depth=128,
        )
        if predictive_quotient is not None
        else None
    )
    predictive_compatibility = (
        compile_predictive_compatibility(
            mechanism_problem.action_system,
            operations=(0, 1, 2, 3),
        )
        if mechanism_problem is not None
        and not args.skip_predictive_analysis
        else None
    )
    predictive_support_plan = (
        plan_predictive_support_frontier(
            predictive_compatibility,
            source_system=mechanism_problem.action_system,
            start_source_key=mechanism_start_key,
            operations=(0, 1, 2, 3),
            max_depth=128,
        )
        if predictive_compatibility is not None
        else None
    )
    guarded_skill_library = (
        compile_history_guarded_skill_library(
            tuple(history_trajectories),
            projection=projection,
            history_lift=(
                mechanism_problem.history_lift
                if mechanism_problem is not None
                else None
            ),
            min_word_length=2,
            max_word_length=8,
            min_variant_support=2,
        )
        if history_trajectories
        else None
    )
    reversed_guarded_skill_library = (
        compile_history_guarded_skill_library(
            tuple(reversed(history_trajectories)),
            projection=projection,
            history_lift=(
                mechanism_problem.history_lift
                if mechanism_problem is not None
                else None
            ),
            min_word_length=2,
            max_word_length=8,
            min_variant_support=2,
        )
        if history_trajectories
        else None
    )
    guarded_skill_order_invariant = (
        guarded_skill_library is None
        and reversed_guarded_skill_library is None
    ) or (
        guarded_skill_library is not None
        and reversed_guarded_skill_library is not None
        and guarded_skill_library.to_receipt()
        == reversed_guarded_skill_library.to_receipt()
    )
    guarded_frontier_prefix_plan = None
    guarded_frontier_prefix_order_invariant = None
    if (
        guarded_skill_library is not None
        and mechanism_problem is not None
        and observed_frontier_plan.actions
    ):
        source_system = mechanism_problem.action_system
        boundary_classes = frozenset(source_system.boundary_kinds)

        def witnessed_successor(source_key, operation):
            relation_key = source_key, operation
            effects = source_system.relation_effects.get(relation_key, ())
            targets = source_system.relation_targets.get(relation_key, ())
            if (
                len(effects) != 1
                or len(targets) != 1
                or any(
                    (operation, effect) in boundary_classes
                    for effect in effects
                )
            ):
                return None
            return next(iter(targets))

        witnessed_prefix = tuple(observed_frontier_plan.actions[:-1])
        guarded_frontier_prefix_plan = compile_guarded_execution_plan(
            guarded_skill_library,
            start_key=mechanism_start_key,
            operations=witnessed_prefix,
            transition=witnessed_successor,
        )
        reversed_library = replace(
            guarded_skill_library,
            programs=tuple(reversed(guarded_skill_library.programs)),
        )
        reversed_plan = compile_guarded_execution_plan(
            reversed_library,
            start_key=mechanism_start_key,
            operations=witnessed_prefix,
            transition=witnessed_successor,
        )
        guarded_frontier_prefix_order_invariant = (
            guarded_frontier_prefix_plan.to_receipt()
            == reversed_plan.to_receipt()
        )
    reachability_fibers = None
    reachability_plan = None
    reindexed_options = ()
    if mechanism_problem is not None:
        source_system = mechanism_problem.action_system

        reachability_fibers = compile_boundary_reachability_fibers(
            source_system,
            operations=(0, 1, 2, 3),
            context_key=mechanism_problem.acquisition_context_key,
            support_key=lambda source_key: stable_sha256(
                getattr(
                    source_system.representative(source_key),
                    "observation",
                    source_system.representative(source_key),
                )
            ),
            source_lineage_keys=mechanism_problem.source_lineage_keys,
        )
        reachability_plan = plan_boundary_reachability_frontier(
            reachability_fibers,
            start_key=mechanism_start_key,
            max_depth=128,
        )
        if args.option_receipt:
            option_path = Path(args.option_receipt).resolve()
            prior_payload = json.loads(
                option_path.read_text(encoding="utf-8")
            )
            prior_quotient = prior_payload.get(
                "predictive_quotient",
                prior_payload,
            )
            members_by_class = {
                str(row["class_id"]): tuple(
                    str(value)
                    for value in row.get("member_sha256s") or ()
                )
                for row in prior_quotient.get("classes") or ()
                if isinstance(row, dict) and row.get("class_id")
            }
            option_specs = []
            for row in prior_quotient.get("options") or ():
                if not isinstance(row, dict):
                    continue
                try:
                    operations = tuple(
                        ast.literal_eval(value)
                        for value in row.get("operations") or ()
                    )
                except (SyntaxError, ValueError) as exc:
                    raise ValueError(
                        "option receipt contains a non-literal operation"
                    ) from exc
                option_specs.append(OptionProgramSpec(
                    operations=operations,
                    initiation_source_sha256s=members_by_class.get(
                        str(row.get("initiation_class") or ""),
                        (),
                    ),
                    lineage_refs=tuple(
                        str(value)
                        for value in row.get("evidence_refs") or ()
                    ),
                    imported_ref=str(option_path),
                ))
            reindexed_options = reindex_option_programs(
                option_specs,
                fibers=reachability_fibers,
            )
    guarded_protocol_lowerings = ()
    guarded_protocol_selection = None
    guarded_protocol_order_invariant = None
    if predictive_compatibility is not None and mechanism_problem is not None:
        protocol_weights = ProtocolYieldWeights(
            identification=W_EIG,
            compression=W_COMPRESSION,
            novelty=W_COVERAGE,
        )
        acquisition_frontiers = MechanismAcquisitionFrontiers(
            observed=observed_frontier_plan,
            boundary=reachability_plan,
            predictive_quotient=predictive_frontier_plan,
            predictive_support=predictive_support_plan,
            predictive_quotient_is_orbit_completion=False,
        )
        guarded_protocol_portfolio = select_acquisition_protocols(
            mechanism_problem.action_system,
            predictive_compatibility,
            start_key=mechanism_start_key,
            frontiers=acquisition_frontiers,
            weights=protocol_weights,
            skill_library=guarded_skill_library,
        )
        guarded_protocol_lowerings = (
            guarded_protocol_portfolio.lowerings
        )
        guarded_protocol_selection = (
            guarded_protocol_portfolio.selection
        )
        reversed_protocol_portfolio = select_witnessed_protocols(
            mechanism_problem.action_system,
            predictive_compatibility,
            start_key=mechanism_start_key,
            routes=(
                (protocol_id, frontier.actions)
                for protocol_id, frontier
                in reversed(acquisition_frontiers.named_frontiers())
            ),
            weights=protocol_weights,
            skill_library=guarded_skill_library,
        )
        guarded_protocol_order_invariant = (
            guarded_protocol_selection.to_receipt()
            == reversed_protocol_portfolio.selection.to_receipt()
        )
    inspected_pair = None
    if (
        predictive_compatibility is not None
        and args.inspect_pair_sha256 is not None
    ):
        sources_by_sha = {
            stable_sha256(source): source
            for source in predictive_compatibility.sources
        }
        missing = [
            digest for digest in args.inspect_pair_sha256
            if digest not in sources_by_sha
        ]
        if missing:
            raise SystemExit(
                "inspect-pair source SHA-256 not found: "
                + ", ".join(missing)
            )
        inspected_pair = predictive_compatibility.pair_receipt(
            *(sources_by_sha[digest] for digest in args.inspect_pair_sha256)
        )

    discriminators = {
        "trace_section_passed": trace_system.passed_section,
        "trace_noncommuting_relations": len(
            trace_system.noncommuting_relations
        ),
        "trace_boundary_classes": len(trace_system.boundary_kinds),
    }
    if bank_system is not None:
        discriminators.update({
            "bank_section_passed": bank_system.passed_section,
            "bank_noncommuting_relations": len(
                bank_system.noncommuting_relations
            ),
            "support_top_effect_sha256": (
                stable_sha256(
                    bank_system.effect_support.most_common(1)[0][0][1]
                )
                if bank_system.effect_support else ""
            ),
            "exception_top_effect_sha256": (
                stable_sha256(bank_system.ranked[0].effect)
                if bank_system.ranked else ""
            ),
            "mechanism_failed_rows": failure_quotient[
                "mechanism_failed_rows"
            ],
            "render_only_failed_rows": failure_quotient[
                "render_only_failed_rows"
            ],
            "renewal_description_preference": (
                renewal_coordinate_audit["description_preference"]
            ),
        })
    payload = {
        "schema": "ztare-partial-action-audit-v1",
        "carrier_sha256": carrier_sha,
        "projection_sha256": projection.projection_sha256,
        "bank": (
            {
                "receipt": bank_system.to_receipt(rank_cap=50),
                "support_rank": _support_rank(bank_system),
                "carrier_failure_quotient": failure_quotient,
                "renewal_coordinate_audit": renewal_coordinate_audit,
            }
            if bank_system is not None
            else {"status": "skipped_active_only"}
        ),
        "latest_trace": {
            "path": trace_ref,
            "declared_non_discharge_indices": sorted(
                declared_boundary_indices
            ),
            "boundary_indices": sorted(boundary_indices),
            "receipt": trace_system.to_receipt(rank_cap=50),
            "support_rank": _support_rank(trace_system),
        },
        "history_snapshot": {
            "through_trace": trace_ref,
            "ledger_row_count": len(ledger_rows),
            "excluded_future_row_count": excluded_future_history_count,
            "matched_trace_boundary": bool(trace_ledger_positions),
        },
        "active_epoch": {
            "source_epoch": active_epoch,
            "receipt": active_system.to_receipt(rank_cap=50),
            "support_rank": _support_rank(active_system),
        },
        "discriminators": discriminators,
        "offline_mechanism_search": (
            {
                "problem_id": mechanism_problem.problem_id,
                "status": mechanism_search.status,
                "generated": mechanism_search.generated,
                "expanded": mechanism_search.expanded,
                "deepest_depth": mechanism_search.deepest_depth,
                "action_count": len(mechanism_search.actions),
                "continuation_length": len(
                    mechanism_search.continuation_actions
                ),
                "projection_counterexample": (
                    mechanism_search.projection_counterexample
                ),
            }
            if mechanism_search is not None
            else {
                "status": (
                    "skipped"
                    if args.skip_model_search and mechanism_problem is not None
                    else "no_problem"
                )
            }
        ),
        "offline_observed_frontier": observed_frontier_plan.to_receipt(),
        "predictive_quotient": (
            predictive_quotient.to_receipt()
            if predictive_quotient is not None
            else None
        ),
        "offline_predictive_frontier": (
            predictive_frontier_plan.to_receipt()
            if predictive_frontier_plan is not None
            else None
        ),
        "predictive_compatibility": (
            predictive_compatibility.to_receipt()
            if predictive_compatibility is not None
            else None
        ),
        "predictive_support_frontier": (
            predictive_support_plan.to_receipt()
            if predictive_support_plan is not None
            else None
        ),
        "guarded_skill_library": (
            guarded_skill_library.to_receipt()
            if guarded_skill_library is not None
            else None
        ),
        "guarded_skill_order_invariant": (
            guarded_skill_order_invariant
        ),
        "guarded_frontier_prefix_plan": (
            guarded_frontier_prefix_plan.to_receipt()
            if guarded_frontier_prefix_plan is not None
            else None
        ),
        "guarded_frontier_prefix_order_invariant": (
            guarded_frontier_prefix_order_invariant
        ),
        "guarded_frontier_target_operation": (
            repr(observed_frontier_plan.actions[-1])
            if observed_frontier_plan.actions
            else None
        ),
        "guarded_protocol_lowerings": [
            lowering.to_receipt()
            for lowering in guarded_protocol_lowerings
        ],
        "guarded_protocol_selection": (
            guarded_protocol_selection.to_receipt()
            if guarded_protocol_selection is not None
            else None
        ),
        "guarded_protocol_order_invariant": (
            guarded_protocol_order_invariant
        ),
        "boundary_reachability_fibers": (
            reachability_fibers.to_receipt(
                edge_cap=len(reachability_fibers.edges),
                option_programs=reindexed_options,
            )
            if reachability_fibers is not None
            else None
        ),
        "boundary_reachability_frontier": (
            reachability_plan.to_receipt()
            if reachability_plan is not None
            else None
        ),
        "inspected_predictive_pair": inspected_pair,
        "history_lift": (
            mechanism_problem.history_lift.to_receipt()
            if mechanism_problem is not None
            and mechanism_problem.history_lift is not None
            else None
        ),
        "mechanism_action_system": (
            mechanism_problem.action_system.to_receipt(rank_cap=50)
            if mechanism_problem is not None
            else None
        ),
    }
    output = Path(args.output)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "output": str(output),
        **payload["discriminators"],
        "trace_fibers": payload["latest_trace"]["receipt"]["fiber_count"],
        "trace_effect_classes": payload["latest_trace"]["receipt"][
            "effect_class_count"
        ],
        "offline_mechanism_search": payload["offline_mechanism_search"],
        "offline_observed_frontier": payload[
            "offline_observed_frontier"
        ],
        "predictive_quotient": (
            {
                "class_count": payload["predictive_quotient"][
                    "class_count"
                ],
                "source_fiber_count": payload["predictive_quotient"][
                    "source_fiber_count"
                ],
                "option_count": payload["predictive_quotient"][
                    "option_count"
                ],
                "section": payload["predictive_quotient"]["section"][
                    "status"
                ],
                "transport": payload["predictive_quotient"]["transport"][
                    "status"
                ],
            }
            if payload["predictive_quotient"] is not None
            else None
        ),
        "offline_predictive_frontier": payload[
            "offline_predictive_frontier"
        ],
        "predictive_compatibility": (
            {
                "source_count": payload["predictive_compatibility"][
                    "source_count"
                ],
                "distinct_compatible_pair_count": payload[
                    "predictive_compatibility"
                ]["distinct_compatible_pair_count"],
                "incompatibility_count": payload[
                    "predictive_compatibility"
                ]["incompatibility_count"],
                "support_gap_count": payload[
                    "predictive_compatibility"
                ]["support_gap_count"],
                "refinement_rounds": payload[
                    "predictive_compatibility"
                ]["refinement_rounds"],
            }
            if payload["predictive_compatibility"] is not None
            else None
        ),
        "predictive_support_frontier": payload[
            "predictive_support_frontier"
        ],
        "guarded_skill_library": (
            {
                key: payload["guarded_skill_library"][key]
                for key in (
                    "program_count",
                    "primitive_token_count",
                    "encoded_token_count",
                    "dictionary_token_count",
                    "description_length",
                    "compression_gain",
                    "exact_reconstruction",
                    "trace_count",
                )
            }
            if payload["guarded_skill_library"] is not None
            else None
        ),
        "guarded_skill_order_invariant": payload[
            "guarded_skill_order_invariant"
        ],
        "guarded_frontier_prefix_plan": payload[
            "guarded_frontier_prefix_plan"
        ],
        "guarded_frontier_prefix_order_invariant": payload[
            "guarded_frontier_prefix_order_invariant"
        ],
        "guarded_frontier_target_operation": payload[
            "guarded_frontier_target_operation"
        ],
        "boundary_reachability_fibers": (
            {
                key: payload["boundary_reachability_fibers"][key]
                for key in (
                    "node_count",
                    "relation_count",
                    "source_operation_frontier_count",
                    "context_count",
                    "support_identity_count",
                    "context_transition_edge_count",
                    "boundary_edge_count",
                    "deterministic_edge_count",
                    "ambiguous_edge_count",
                    "option_program_count",
                )
            }
            if payload["boundary_reachability_fibers"] is not None
            else None
        ),
        "boundary_reachability_frontier": payload[
            "boundary_reachability_frontier"
        ],
        "reindexed_option_statuses": dict(Counter(
            option.status for option in reindexed_options
        )),
        "inspected_predictive_pair": payload[
            "inspected_predictive_pair"
        ],
    }
    if bank_system is not None:
        summary.update({
            "bank_fibers": payload["bank"]["receipt"]["fiber_count"],
            "bank_effect_classes": payload["bank"]["receipt"][
                "effect_class_count"
            ],
        })
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
