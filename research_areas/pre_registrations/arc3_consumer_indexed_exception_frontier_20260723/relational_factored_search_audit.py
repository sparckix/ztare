#!/usr/bin/env python3
"""Run the preregistered H72 relation-valued factored-search audit."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

import active_affordance_frontier_audit as active
import joint_equivariant_affordance_audit as joint

from ztare.common.equivariance import stable_sha256
from ztare.common.factored_search import search_factored
from ztare.common.relational_task_contract import (
    EdgeTaskHypothesis,
    TaskHypothesisVersionSpace,
)
from ztare.common.task_discharge import TaskDischargeContract
from ztare.common.transition_congruence import (
    LabeledSuccessorRefinementProblem,
)
from ztare.worldmodel.carrier_loader import load_carrier_path
from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.gates import law_scored_view
from ztare.worldmodel.goal_abduction import RelationalGoalEdgeHypothesisSet
from ztare.worldmodel.patch_base_carrier import (
    carrier_execution_sha256_from_source,
)


EXPECTED_JOINT_SHA256 = (
    "c19683438c8aebf80055531bc063ab560e2cd5538de63675345cff4614438072"
)
EXPECTED_ACTIVE_CONFIGURATION_SHA256 = (
    "4dd96788ba556af49abb6b84a143ff58f4e933b8c8c331159017b9c91d77a000"
)
OPERATIONS = (0, 1, 2, 3)


def _latest_seed_trace(
    *,
    project: Path,
    active_epoch: int,
    seed_sha256: str,
    carrier_sha256: str,
    carrier_execution_sha256: str,
) -> tuple[dict[str, Any], tuple[Any, ...]]:
    ledger_path = project / "workspace/sealed_eval_slices.jsonl"
    ledger = [
        json.loads(line)
        for line in ledger_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for row in reversed(ledger):
        if (
            row.get("source_epoch") != active_epoch
            or row.get("origin_seed_sha256") != seed_sha256
            or (
                row.get("source_carrier_sha256") != carrier_sha256
                and row.get("source_carrier_execution_sha256")
                != carrier_execution_sha256
            )
        ):
            continue
        trace_path = project / str(row.get("path") or "")
        if not trace_path.is_file():
            continue
        transitions = tuple(EpisodeLog.read_jsonl(trace_path))
        if not transitions:
            continue
        identity = transitions[0].identity
        if identity is None or identity.source_epoch != active_epoch:
            continue
        return row, transitions
    raise ValueError("no sealed trace binds the current seed and carrier chart")


def _descriptor_receipt(
    source: Any,
    operation: Any,
    *,
    projection: Any,
    operation_maps: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    operation_row = operation_maps.get(repr(operation))
    if operation_row is None or not operation_row.get("admitted"):
        return {
            "status": "inadmissible_operation",
            "operation": repr(operation),
        }
    try:
        factors = projection.factor(source)
        origins = tuple(factors.controlled_base)
        configuration = joint._square(tuple(factors.finite_configuration))
        if len(origins) != 1:
            return {
                "status": "controlled_origin_not_unique",
                "operation": repr(operation),
                "controlled_origin_count": len(origins),
            }
        if configuration is None:
            return {
                "status": "nonsquare_configuration",
                "operation": repr(operation),
                "configuration_length": len(factors.finite_configuration),
            }
        origin = origins[0]
        delta_row, delta_col = operation_row["vector"]
        attempted = origin[0] + delta_row, origin[1] + delta_col
        height = len(projection.sprite)
        width = len(projection.sprite[0])
        footprint = joint.affordance._window(
            source,
            top=attempted[0],
            left=attempted[1],
            size=max(height, width),
            current_origin=origin,
            sprite_shape=(height, width),
        )
        codes = joint._codes(footprint, configuration)
        return {
            "status": "admissible",
            "operation": repr(operation),
            "controlled_origin": origin,
            "attempted_origin": attempted,
            "configuration_sha256": stable_sha256(
                joint.affordance._configuration_partition(
                    tuple(factors.finite_configuration)
                )
            ),
            "joint_sha256": codes["joint"]["sha256"],
            "joint_transform": codes["joint"]["transform"],
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "descriptor_error",
            "operation": repr(operation),
            "error_type": type(exc).__name__,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--joint-result", required=True)
    parser.add_argument("--active-result", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-depth", type=int, default=180)
    parser.add_argument("--max-states", type=int, default=20_000)
    parser.add_argument(
        "--state-equality",
        choices=("factored", "exact", "behavioral-1", "behavioral-2"),
        default="factored",
    )
    parser.add_argument(
        "--hypothesis-id",
        default="H-GPSA-RELATIONAL-FACTORED-SEARCH-20260727-72",
    )
    args = parser.parse_args()

    project = Path(args.project).resolve()
    joint_result_path = Path(args.joint_result).resolve()
    joint_payload = json.loads(
        joint_result_path.read_text(encoding="utf-8")
    )
    active_payload = json.loads(
        Path(args.active_result).read_text(encoding="utf-8")
    )
    if joint_payload.get("status") != "joint_equivariant_affordance_confirmed":
        raise SystemExit("H71 joint relation is not confirmed")
    target_sha256 = str(
        joint_payload["prior_tests"]["joint"]["template_sha256"]
    )
    if target_sha256 != EXPECTED_JOINT_SHA256:
        raise SystemExit("H71 joint relation identity drifted")
    active_matches = joint_payload["active"]["matches"]["joint"]
    if {
        str(row["configuration_sha256"]) for row in active_matches
    } != {EXPECTED_ACTIVE_CONFIGURATION_SHA256}:
        raise SystemExit("H71 active relational preimage drifted")

    carrier_path = project / "test_model.py"
    carrier, carrier_kind, carrier_sha256 = load_carrier_path(
        carrier_path,
        project_dir=project,
    )
    projection = getattr(carrier, "_ztare_factored_projection", None)
    if projection is None:
        raise SystemExit("current carrier has no compiled fiber projection")
    carrier_execution_sha256 = carrier_execution_sha256_from_source(
        carrier_path.read_text(encoding="utf-8")
    )

    active_epoch = int(joint_payload["active"]["epoch"])
    bank = EpisodeLog.read_jsonl(
        project / "raw/episodes/episode_001.jsonl"
    )
    active_rows = tuple(law_scored_view(bank, source_epoch=active_epoch))
    operation_maps = active._operation_maps(
        active_rows,
        projection=projection,
    )
    operations = tuple(
        operation
        for operation in OPERATIONS
        if operation_maps[repr(operation)].get("admitted")
    )
    if operations != OPERATIONS:
        raise SystemExit("current evidence does not admit all four operations")

    seed_sha256 = str(
        active_payload["active_problem"]["current_seed_sha256"]
    )
    seed_ledger_row, seed_trace = _latest_seed_trace(
        project=project,
        active_epoch=active_epoch,
        seed_sha256=seed_sha256,
        carrier_sha256=carrier_sha256,
        carrier_execution_sha256=carrier_execution_sha256,
    )
    start = seed_trace[0].s
    start_time = seed_trace[0].t
    if not projection.in_domain(start):
        raise SystemExit("current seed lies outside the compiled projection")

    profile = json.loads(
        (project / "play_config.json").read_text(encoding="utf-8")
    )
    task_contract = TaskDischargeContract.from_dict(
        profile["task_discharge"]
    )

    def describe_edge(source: Any, operation: Any, _time: Any) -> str:
        receipt = _descriptor_receipt(
            source,
            operation,
            projection=projection,
            operation_maps=operation_maps,
        )
        if receipt["status"] != "admissible":
            return "descriptor:" + stable_sha256(receipt)
        return str(receipt["joint_sha256"])

    hypothesis = EdgeTaskHypothesis(
        hypothesis_id="joint_affordance:" + target_sha256,
        predicate=lambda _source, _operation, descriptor: (
            descriptor == target_sha256
        ),
        spec={
            "schema": "ztare-joint-affordance-hypothesis-v1",
            "descriptor_sha256": target_sha256,
            "compiler_result": str(joint_result_path),
        },
    )
    goal = RelationalGoalEdgeHypothesisSet(
        hypotheses=TaskHypothesisVersionSpace(
            edge_hypotheses=(hypothesis,),
            source_epoch=active_epoch,
            task_contract_sha256=task_contract.sha256,
        ),
        describe_edge=describe_edge,
        descriptor_id=(
            "joint-equivariant-affordance:"
            + target_sha256
        ),
        operations=operations,
        evidence_refs=(
            str(joint_result_path.relative_to(Path.cwd())),
            str(seed_ledger_row["path"]),
        ),
    )
    parent_problem = projection.problem_for(goal, start)
    if args.state_equality == "exact":
        problem = projection.exact_relational_problem_for(goal, start)
    elif args.state_equality in {"behavioral-1", "behavioral-2"}:
        problem = (
            LabeledSuccessorRefinementProblem(
                parent=parent_problem,
                predict=carrier,
                operations=operations,
                carrier_execution_sha256=carrier_execution_sha256,
                refinement_depth=int(args.state_equality.rsplit("-", 1)[1]),
            )
            if parent_problem is not None
            else None
        )
    else:
        problem = parent_problem
    if problem is None:
        raise SystemExit("relational factored problem did not compile")

    result = search_factored(
        predict=getattr(problem, "predict", carrier),
        start=start,
        interventions=operations,
        problem=problem,
        start_time=start_time,
        max_depth=args.max_depth,
        max_states=args.max_states,
    )

    captured = getattr(problem, "last_projection_counterexample", None)
    if result.status == "projection_noncommuting" and captured is not None:
        (
            left_source,
            right_source,
            outer_operation,
            left_time,
            right_time,
            _capture_payload,
        ) = captured
        witness = {
            "left_source_sha256": stable_sha256(left_source),
            "right_source_sha256": stable_sha256(right_source),
            "outer_operation": outer_operation,
            "left_time": left_time,
            "right_time": right_time,
        }
        if left_time == right_time:
            left_successor = problem.predict(
                left_source,
                outer_operation,
                left_time,
            )
            right_successor = problem.predict(
                right_source,
                outer_operation,
                right_time,
            )
            if left_successor is not None and right_successor is not None:
                suffix = problem.distinguishing_word(
                    left_successor,
                    right_successor,
                    problem.advance_time(left_time),
                    max_depth=problem.refinement_depth,
                )
                if suffix is not None:
                    witness["distinguishing_word"] = [
                        outer_operation,
                        *suffix,
                    ]
                    witness["word_length"] = 1 + len(suffix)
                    witness["left_successor_sha256"] = stable_sha256(
                        left_successor
                    )
                    witness["right_successor_sha256"] = stable_sha256(
                        right_successor
                    )
        result.projection_counterexample[
            "behavioral_witness"
        ] = witness

    action_word = (
        result.actions
        if result.status == "edge_found"
        else result.continuation_actions
    )
    replay_state = start
    replay_time = start_time
    replayed_prefix: list[Any] = []
    terminal_receipt: dict[str, Any] | None = None
    replay_status = "no_action_word"
    for index, operation in enumerate(action_word):
        if result.status == "edge_found" and index == len(action_word) - 1:
            terminal_receipt = _descriptor_receipt(
                replay_state,
                operation,
                projection=projection,
                operation_maps=operation_maps,
            )
            replay_status = (
                "verified_relational_edge"
                if goal(replay_state, operation, replay_time)
                and terminal_receipt.get("joint_sha256") == target_sha256
                else "relational_edge_missed"
            )
            break
        successor = carrier(replay_state, operation, replay_time)
        if successor is None:
            replay_status = "undefined_prefix_image"
            break
        replay_state = successor
        replay_time += 1
        replayed_prefix.append(operation)
    else:
        if action_word:
            replay_status = "continuation_replayed"

    if result.status == "edge_found" and replay_status != (
        "verified_relational_edge"
    ):
        raise SystemExit("search edge did not replay to the bound relation")

    payload = {
        "schema": "ztare-relational-factored-search-audit-v1",
        "hypothesis_id": args.hypothesis_id,
        "carrier": {
            "kind": carrier_kind,
            "source_sha256": carrier_sha256,
            "execution_sha256": carrier_execution_sha256,
            "projection_sha256": projection.projection_sha256,
        },
        "task": {
            "contract_sha256": task_contract.sha256,
            "active_epoch": active_epoch,
            "target_descriptor_sha256": target_sha256,
            "goal_identity_sha256": goal.identity_sha256,
            "active_hypothesis_ids": list(goal.hypotheses.active_ids),
            "operations": list(operations),
            "evidence_refs": list(goal.evidence_refs),
        },
        "seed": {
            "origin_seed_sha256": seed_sha256,
            "trace_ref": seed_ledger_row["path"],
            "start_state_sha256": stable_sha256(start),
            "start_time": start_time,
        },
        "operation_maps": operation_maps,
        "problem": {
            "problem_id": problem.problem_id,
            "factor_names": list(problem.factor_names),
            "terminal_factor_names": list(problem.terminal_factor_names),
            "feasibility_factor_names": list(
                problem.feasibility_factor_names
            ),
            "availability_factor_names": list(
                problem.availability_factor_names
            ),
            "evidence_refs": list(problem.evidence_refs),
        },
        "search_bounds": {
            "max_depth": args.max_depth,
            "max_states": args.max_states,
            "state_equality": args.state_equality,
        },
        "search_result": asdict(result),
        "replay": {
            "status": replay_status,
            "action_word": list(action_word),
            "replayed_prefix": replayed_prefix,
            "source_state_sha256": stable_sha256(replay_state),
            "source_time": replay_time,
            "terminal_relation": terminal_receipt,
        },
        "environment_contact": False,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": result.status,
        "actions": list(result.actions),
        "continuation_length": len(result.continuation_actions),
        "generated": result.generated,
        "expanded": result.expanded,
        "deepest_depth": result.deepest_depth,
        "frontier_remaining": result.frontier_remaining,
        "replay": payload["replay"],
        "output": str(output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
