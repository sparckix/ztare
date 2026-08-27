"""Freeze a strategy-action -> company-state path -> operating-outcome experiment."""

from __future__ import annotations

from argparse import ArgumentParser
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import yaml

from ztare.common.equivariance import stable_sha256

from .company_state_flow import decompose_transition_counts
from .company_state_path_action import COMPANY_STATE_PATH_ACTION_RUN_SCHEMA
from .contracts import canonical_timestamp, require_finite, require_text, timestamp_key
from .strategy_learning import (
    STRATEGY_COHORT_PLAN_SCHEMA,
    STRATEGY_MOVE_LIBRARY_SCHEMA,
)


STRATEGY_STATE_EXPERIMENT_PROFILE_SCHEMA = (
    "jaggedthoughts-strategy-state-experiment-profile-v1"
)
STRATEGY_STATE_EXPERIMENT_SCHEMA = "jaggedthoughts-strategy-state-experiment-v1"


def _resolve(root: Path, value: Any, label: str) -> Path:
    path = Path(require_text(value, label)).expanduser()
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    repository = Path(__file__).resolve().parents[3]
    if not any(path.is_relative_to(base) for base in (root, repository)):
        raise ValueError(f"{label} escapes the repository")
    return path


def _read(root: Path, value: Any, label: str) -> dict[str, Any]:
    path = _resolve(root, value, label)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{label} must contain an object")
    return dict(payload)


def _transition_counts_from_receipt(
    root: Path, value: Any, *, path_run_sha: str, partition_sha: str,
) -> tuple[list[list[int]], dict[str, Any]]:
    receipt_path = _resolve(root, value, "transition_evidence_receipt_path")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if (
        receipt.get("schema") != "jaggedthoughts-company-state-path-newton-evidence-v1"
        or receipt.get("deterministic_seed_run_sha256") != path_run_sha
        or receipt.get("partition_sha256") != partition_sha
        or receipt.get("point_in_time_authority")
        != "retrospective_current_universe_diagnostic_only"
    ):
        raise ValueError("company-state transition evidence identity mismatch")
    evidence_path = receipt_path.with_name("evidence.txt")
    content = evidence_path.read_bytes()
    evidence_sha = hashlib.sha256(content).hexdigest()
    if evidence_sha != (receipt.get("partition_file_sha256") or {}).get("evidence.txt"):
        raise ValueError("company-state transition evidence content hash mismatch")
    state_ids = list(map(str, receipt.get("state_ids") or ()))
    index = {state_id: offset for offset, state_id in enumerate(state_ids)}
    counts = [[0] * len(state_ids) for _ in state_ids]
    for row in csv.DictReader(content.decode("utf-8").splitlines(), delimiter="\t"):
        for left, right in (
            (row["source_state_id"], row["intermediate_state_id"]),
            (row["intermediate_state_id"], row["terminal_state_id"]),
        ):
            counts[index[left]][index[right]] += 1
    return counts, {
        "receipt_file_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
        "evidence_file_sha256": evidence_sha,
        "frozen_at": receipt["frozen_at"],
        "visible_row_count": int((receipt.get("row_counts") or {}).get("visible", 0)),
    }


def _checked_hash(payload: Mapping[str, Any], field: str, label: str) -> str:
    body = dict(payload)
    declared = str(body.pop(field, ""))
    if declared != stable_sha256(body):
        raise ValueError(f"{label} content hash mismatch")
    return declared


def _contract(body: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(body)
    row["contract_sha256"] = stable_sha256(row)
    return row


def _cohort_controls(
    root: Path, plan: Mapping[str, Any], phenotype_sha: str,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    results_root = root / "institutional_learning" / "strategy_cohorts" / "results"
    controls: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for request in plan.get("requests") or ():
        if str(request.get("mechanism_phenotype_sha256") or "") != phenotype_sha:
            continue
        request_sha = str(request.get("request_sha256") or "")
        path = results_root / f"{request_sha}.json"
        if not path.exists():
            counts["unresolved"] = counts.get("unresolved", 0) + 1
            continue
        result = json.loads(path.read_text(encoding="utf-8"))
        _checked_hash(result, "result_sha256", "strategy cohort result")
        if result.get("request_sha256") != request_sha:
            raise ValueError("strategy cohort result/request identity mismatch")
        classification = str(result.get("classification") or "unresolved")
        counts[classification] = counts.get(classification, 0) + 1
        coverage = dict(result.get("coverage") or {})
        if (
            classification == "no_family_adoption_found"
            and result.get("panel_role") in {
                "control_candidate", "provisional_not_yet_treated",
            }
            and coverage.get("sec_filings_searched") is True
            and coverage.get("issuer_materials_searched") is True
        ):
            controls.append({
                "entity_id": require_text(result.get("peer_entity_id"), "control entity"),
                "request_sha256": request_sha,
                "result_sha256": result["result_sha256"],
                "classification": "provisional_not_yet_treated",
                "coverage": coverage,
            })
    return sorted(controls, key=lambda row: row["entity_id"]), dict(sorted(counts.items()))


def compile_strategy_state_experiment(
    profile_path: str | Path, *, workspace: str | Path,
) -> dict[str, Any]:
    """Freeze identities and contracts; leave unsupported controls fail-closed."""
    root = Path(workspace).expanduser().resolve()
    source = Path(profile_path).expanduser()
    if not source.is_absolute():
        source = root / source
    profile = yaml.safe_load(source.resolve().read_text(encoding="utf-8"))
    if (
        not isinstance(profile, Mapping)
        or profile.get("schema") != STRATEGY_STATE_EXPERIMENT_PROFILE_SCHEMA
    ):
        raise ValueError(
            f"strategy-state profile schema must be {STRATEGY_STATE_EXPERIMENT_PROFILE_SCHEMA}"
        )

    path_run = _read(root, profile.get("path_run_path"), "path_run_path")
    if path_run.get("schema") != COMPANY_STATE_PATH_ACTION_RUN_SCHEMA:
        raise ValueError("strategy-state experiment requires a company-state path-action run")
    path_run_sha = _checked_hash(path_run, "run_sha256", "company-state path-action run")
    if any(path_run.get(key) is not False for key in (
        "signal_authority", "model_fit_authority", "capital_authority",
    )):
        raise ValueError("source company-state path run carries forbidden authority")

    library = _read(root, profile.get("move_library_path"), "move_library_path")
    if library.get("schema") != STRATEGY_MOVE_LIBRARY_SCHEMA:
        raise ValueError("strategy-state experiment requires the strategy move library")
    library_sha = _checked_hash(library, "library_sha256", "strategy move library")
    cohort_plan = _read(root, profile.get("cohort_plan_path"), "cohort_plan_path")
    if cohort_plan.get("schema") != STRATEGY_COHORT_PLAN_SCHEMA:
        raise ValueError("strategy-state experiment requires the strategy cohort plan")
    plan_sha = _checked_hash(cohort_plan, "plan_sha256", "strategy cohort plan")

    action = dict(profile.get("action") or {})
    entity_id = require_text(action.get("entity_id"), "action.entity_id").upper()
    phenotype_sha = require_text(
        action.get("mechanism_phenotype_sha256"), "action.mechanism_phenotype_sha256",
    )
    requested_moves = sorted({
        require_text(value, "action.move_sha256") for value in action.get("move_sha256s") or ()
    })
    if not requested_moves:
        raise ValueError("strategy-state action requires at least one exact move")
    moves = {
        str(row.get("move_sha256")): row for row in library.get("moves") or ()
        if str(row.get("move_sha256")) in requested_moves
    }
    if set(moves) != set(requested_moves):
        raise ValueError("strategy-state action move is absent from the bound library")
    events, source_refs = [], set()
    for move_sha in requested_moves:
        move = moves[move_sha]
        if (
            str(move.get("entity_id") or "").upper() != entity_id
            or move.get("mechanism_phenotype_sha256") != phenotype_sha
        ):
            raise ValueError("strategy-state action bundle crossed entity or phenotype identity")
        event = dict(move.get("implementation_event") or {})
        if event.get("treatment_timing_status") != "exact_adoption_event":
            raise ValueError("strategy-state experiment requires exact adoption timing")
        event_body = dict(event)
        event_sha = str(event_body.pop("implementation_event_sha256", ""))
        if event_sha != stable_sha256(event_body):
            raise ValueError("strategy implementation event content hash mismatch")
        events.append({
            "move_sha256": move_sha,
            "implementation_event_sha256": event_sha,
            "occurred_at": event["occurred_at"],
            "available_at": event["available_at"],
            "source_refs": sorted(map(str, event.get("source_refs") or ())),
        })
        source_refs.update(map(str, event.get("source_refs") or ()))
    if not source_refs:
        raise ValueError("strategy-state action must bind public source refs")

    opened_at = canonical_timestamp(profile.get("opened_at"), "strategy-state opened_at")
    assignments = {
        str(row["entity_id"]).upper(): dict(row)
        for row in (path_run.get("source_snapshot") or {}).get("assignments") or ()
    }
    if entity_id not in assignments:
        raise ValueError("strategy action entity is absent from the frozen company-state cohort")
    if max(timestamp_key(row["available_at"]) for row in events) > timestamp_key(opened_at):
        raise ValueError("strategy action was not public when the experiment opened")
    path_contracts = {str(row["leg"]): dict(row) for row in path_run.get("outcome_contracts") or ()}
    if set(path_contracts) != {"intermediate", "terminal"}:
        raise ValueError("strategy-state experiment requires both frozen company-state legs")
    for row in path_contracts.values():
        _checked_hash(row, "contract_sha256", "company-state outcome contract")
    if not (
        timestamp_key(opened_at)
        < timestamp_key(path_contracts["intermediate"]["settlement_not_before"])
        < timestamp_key(path_contracts["terminal"]["settlement_not_before"])
    ):
        raise ValueError("strategy-state experiment opened outside the state outcome horizons")

    frontier = _read(root, profile.get("partition_frontier_path"), "partition_frontier_path")
    frontier_sha = _checked_hash(
        frontier, "partition_frontier_sha256", "company-state partition frontier",
    )
    partition_id = str((frontier.get("activation") or {}).get("partition_id") or "")
    partition = next(
        (row for row in frontier.get("candidate_partitions") or ()
         if row.get("partition_id") == partition_id), None,
    )
    if not partition or frontier["activation"].get("partition_sha256") != path_run.get("partition_sha256"):
        raise ValueError("strategy-state partition identity does not match the path run")
    counts, transition_evidence = _transition_counts_from_receipt(
        root, profile.get("transition_evidence_receipt_path"),
        path_run_sha=path_run_sha, partition_sha=path_run["partition_sha256"],
    )
    decomposition = decompose_transition_counts(counts, pseudocount=1.0)
    counts_sha = stable_sha256(counts)

    controls, classifications = _cohort_controls(root, cohort_plan, phenotype_sha)
    industry = next((
        str(row.get("industry_id") or "")
        for row in cohort_plan.get("mechanism_environments") or ()
        if row.get("mechanism_phenotype_sha256") == phenotype_sha
    ), "")
    if not industry:
        raise ValueError("strategy-state action has no bound industry environment")

    outcome = dict(profile.get("operating_outcome") or {})
    outcome_due = canonical_timestamp(
        outcome.get("settlement_not_before"), "operating outcome settlement_not_before",
    )
    if timestamp_key(outcome_due) <= timestamp_key(
        path_contracts["terminal"]["settlement_not_before"],
    ):
        raise ValueError("operating outcome must follow the terminal state observation")
    operating_contract = _contract({
        "schema": "jaggedthoughts-strategy-state-operating-outcome-contract-v1",
        "status": "prospective_shadow_open",
        "opened_at": opened_at,
        "settlement_not_before": outcome_due,
        "entity_id": entity_id,
        "action_bundle_sha256": stable_sha256(events),
        "metric_id": require_text(outcome.get("metric_id"), "operating_outcome.metric_id"),
        "unit": require_text(outcome.get("unit"), "operating_outcome.unit"),
        "direction": require_text(outcome.get("direction"), "operating_outcome.direction"),
        "minimum_effect": require_finite(
            outcome.get("minimum_effect"), "operating_outcome.minimum_effect",
        ),
        "baseline_rule": require_text(
            outcome.get("baseline_rule"), "operating_outcome.baseline_rule",
        ),
        "outcome_rule": require_text(outcome.get("outcome_rule"), "operating_outcome.outcome_rule"),
        "required_source_class": "sec_companyfacts",
        "signal_authority": False,
        "capital_authority": False,
    })

    control_rows = [
        {
            "control_id": "first_order_markov",
            "status": "ready",
            "compiler": "company_state_flow.decompose_transition_counts.directed_transition",
            "transition_counts_sha256": counts_sha,
            "transition_sha256": stable_sha256(decomposition["directed_transition"]),
        },
        {
            "control_id": "reversible_markov",
            "status": "ready",
            "compiler": "company_state_flow.decompose_transition_counts.reversible_transition",
            "transition_counts_sha256": counts_sha,
            "transition_sha256": stable_sha256(decomposition["reversible_transition"]),
        },
        {
            "control_id": "industry_state_markov",
            "status": "acquisition_required",
            "industry_id": industry,
            "reason": "No point-in-time industry-conditioned transition-count artifact is bound.",
        },
        {
            "control_id": "persistence",
            "status": "ready",
            "definition": "intermediate_state_id == terminal_state_id == source_state_id",
        },
        {
            "control_id": "no_move_not_yet_treated",
            "status": "ready" if controls else "acquisition_required",
            "eligible_units": controls,
            "classification_counts": classifications,
            "reason": None if controls else (
                "No source-bounded no-family result is presently eligible; family-only peers are excluded."
            ),
        },
    ]
    missing = [row["control_id"] for row in control_rows if row["status"] != "ready"]
    body: dict[str, Any] = {
        "schema": STRATEGY_STATE_EXPERIMENT_SCHEMA,
        "experiment_id": require_text(profile.get("experiment_id"), "experiment_id"),
        "opened_at": opened_at,
        "status": "frozen_awaiting_control_acquisition" if missing else "prospective_shadow_open",
        "authority": "research_design_only",
        "input_identity": {
            "profile_sha256": stable_sha256(profile),
            "path_run_sha256": path_run_sha,
            "partition_frontier_sha256": frontier_sha,
            "move_library_sha256": library_sha,
            "cohort_plan_sha256": plan_sha,
            "transition_evidence": transition_evidence,
        },
        "strategy_action": {
            "entity_id": entity_id,
            "mechanism_phenotype_sha256": phenotype_sha,
            "move_sha256s": requested_moves,
            "events": events,
            "action_bundle_sha256": stable_sha256(events),
            "source_refs": sorted(source_refs),
        },
        "source_company_state": assignments[entity_id],
        "persistent_state_path": {
            "partition_id": partition_id,
            "partition_sha256": path_run["partition_sha256"],
            "intermediate_contract_sha256": path_contracts["intermediate"]["contract_sha256"],
            "terminal_contract_sha256": path_contracts["terminal"]["contract_sha256"],
            "persistence_observation": "intermediate_state_id == terminal_state_id",
            "causal_interpretation": False,
        },
        "later_operating_outcome": operating_contract,
        "controls": control_rows,
        "missing_control_ids": missing,
        "evaluation_contract": {
            "primary_question": (
                "Does the source-bound action phenotype improve persistent state-path prediction "
                "beyond every frozen same-information control, followed by the declared operating outcome?"
            ),
            "state_scoring_rule": "multiclass_brier_lower_is_better",
            "causal_estimate_status": "not_run",
            "promotion_eligible": False,
        },
        "next_activation": (
            "Acquire point-in-time industry-state counts and source-bounded no-family peers."
            if missing else "Wait for both company-state legs and the later operating outcome."
        ),
        "signal_authority": False,
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    body["experiment_sha256"] = stable_sha256(body)
    return body


def main() -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("profile")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    result = compile_strategy_state_experiment(args.profile, workspace=args.workspace)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        destination = Path(args.output).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.tmp")
        temporary.write_text(rendered, encoding="utf-8")
        temporary.replace(destination)
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "STRATEGY_STATE_EXPERIMENT_PROFILE_SCHEMA",
    "STRATEGY_STATE_EXPERIMENT_SCHEMA",
    "compile_strategy_state_experiment",
]
