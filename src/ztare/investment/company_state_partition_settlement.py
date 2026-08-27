"""Acquire and settle one frozen company-state transition contract."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256

from .company_state_flow import _load_state_observations, _state_panel
from .company_state_partition_frontier import (
    COMPANY_STATE_PARTITION_FRONTIER_SCHEMA,
    NEXT_TRANSITION_EVIDENCE_SCHEMA,
    _partition_panel,
)
from .contracts import canonical_timestamp, timestamp_key
from .strategy_outcome_acquisition import _source_bindings


COMPANY_STATE_PARTITION_STATUS_SCHEMA = "jaggedthoughts-company-state-partition-status-v1"
COMPANY_STATE_PARTITION_SETTLEMENT_SCHEMA = "jaggedthoughts-company-state-partition-settlement-v1"


def _validated_contract(frontier: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    if frontier.get("schema") != COMPANY_STATE_PARTITION_FRONTIER_SCHEMA:
        raise ValueError(f"partition settlement requires {COMPANY_STATE_PARTITION_FRONTIER_SCHEMA}")
    frontier_body = dict(frontier)
    frontier_sha = str(frontier_body.pop("partition_frontier_sha256", ""))
    if frontier_sha != stable_sha256(frontier_body):
        raise ValueError("partition frontier content hash mismatch")

    activation = dict(frontier.get("activation") or {})
    activation_body = dict(activation)
    activation_sha = str(activation_body.pop("activation_sha256", ""))
    if activation_sha != stable_sha256(activation_body):
        raise ValueError("company-state activation content hash mismatch")
    if activation.get("status") != "future_research_activation":
        raise ValueError("company-state partition has no active future evidence contract")
    if any(activation.get(key) is not False for key in (
        "signal_authority", "model_fit_authority", "capital_authority",
    )):
        raise ValueError("company-state activation cannot carry decision authority")

    next_evidence = dict(activation.get("next_evidence_identity") or {})
    if next_evidence.get("schema") != NEXT_TRANSITION_EVIDENCE_SCHEMA:
        raise ValueError(f"next evidence identity must be {NEXT_TRANSITION_EVIDENCE_SCHEMA}")
    if next_evidence.get("signal_authority") is not False or next_evidence.get("capital_authority") is not False:
        raise ValueError("next transition evidence cannot carry decision authority")
    expected_evidence_id = (
        f"company-state-transition:{next_evidence.get('source_epoch')}:"
        f"{next_evidence.get('target_epoch')}:"
        f"{stable_sha256({key: value for key, value in next_evidence.items() if key != 'evidence_id'})[:16]}"
    )
    if next_evidence.get("evidence_id") != expected_evidence_id:
        raise ValueError("next transition evidence identity mismatch")

    candidates = [
        dict(row) for row in frontier.get("candidate_partitions") or ()
        if row.get("partition_id") == activation.get("partition_id")
    ]
    if len(candidates) != 1:
        raise ValueError("activation must resolve to one partition candidate")
    candidate = candidates[0]
    if candidate.get("support_valid") is not True or candidate.get("program_id") not in (
        frontier.get("closure", {}).get("frontier_program_ids") or ()
    ):
        raise ValueError("activated partition is outside the supported frontier")
    partition_identity = {
        "partition_id": candidate["partition_id"],
        "value_levels": candidate["value_levels"],
        "durability_levels": candidate["durability_levels"],
        "definition": candidate["definition"],
        "state_ids": candidate["state_ids"],
        "grammar_digest": frontier["grammar"]["grammar_digest"],
    }
    partition_sha = stable_sha256(partition_identity)
    if partition_sha != activation.get("partition_sha256") or partition_sha != next_evidence.get("partition_sha256"):
        raise ValueError("activated partition identity mismatch")

    snapshot = dict(activation.get("source_snapshot") or {})
    assignments = list(snapshot.get("assignments") or ())
    entity_ids = [str(row["entity_id"]) for row in assignments]
    if (
        len(entity_ids) != len(set(entity_ids))
        or snapshot.get("epoch") != next_evidence.get("source_epoch")
        or any(not row.get("evidence_sha256") or not row.get("source_refs") for row in assignments)
    ):
        raise ValueError("source snapshot identity mismatch")
    if (
        stable_sha256(assignments) != next_evidence.get("source_assignments_sha256")
        or stable_sha256(entity_ids) != next_evidence.get("source_entity_ids_sha256")
        or len(entity_ids) != int(next_evidence.get("source_entity_count", -1))
    ):
        raise ValueError("source cohort hash mismatch")
    return activation, next_evidence, candidate, snapshot


def _status(
    activation: Mapping[str, Any], next_evidence: Mapping[str, Any], *,
    as_of: str, status: str, **extra: Any,
) -> dict[str, Any]:
    body = {
        "schema": COMPANY_STATE_PARTITION_STATUS_SCHEMA,
        "status": status,
        "as_of": as_of,
        "activation_sha256": activation["activation_sha256"],
        "evidence_id": next_evidence["evidence_id"],
        "source_epoch": next_evidence["source_epoch"],
        "target_epoch": next_evidence["target_epoch"],
        "settlement_not_before": next_evidence["settlement_not_before"],
        "signal_authority": False,
        "capital_authority": False,
        **extra,
    }
    return {**body, "status_sha256": stable_sha256(body)}


def _validated_successor_contract(
    base: Mapping[str, Any], successor: Mapping[str, Any],
) -> dict[str, Any]:
    contract = dict(successor)
    body = dict(contract)
    contract_sha = str(body.pop("contract_sha256", ""))
    if contract_sha != stable_sha256(body):
        raise ValueError("company-state successor contract content hash mismatch")
    leg = contract.get("leg")
    if leg not in {"intermediate", "terminal"} or any(
        contract.get(key) is not False for key in ("signal_authority", "capital_authority")
    ):
        raise ValueError("company-state successor must be a zero-authority outcome contract")
    frozen_fields = (
        "partition_sha256", "benchmark_id", "min_years", "source_entity_count",
        "source_entity_ids_sha256", "source_assignments_sha256", "membership_rule",
        "target_threshold_population", "minimum_target_entity_count", "availability_rule",
    )
    if any(contract.get(key) != base.get(key) for key in frozen_fields):
        raise ValueError("company-state successor changed the frozen evidence identity")
    same_intermediate_epoch = (
        contract.get("source_epoch") == base.get("source_epoch")
        and contract.get("target_epoch") == base.get("target_epoch")
    )
    later_terminal_epoch = (
        contract.get("source_epoch") == base.get("source_epoch")
        and str(contract.get("intermediate_epoch")) == str(base.get("target_epoch"))
        and str(contract.get("target_epoch")) > str(base.get("target_epoch"))
    )
    if (leg == "intermediate" and not same_intermediate_epoch) or (
        leg == "terminal" and not later_terminal_epoch
    ):
        raise ValueError("company-state successor epoch identity mismatch")
    return contract


def compile_company_state_partition_status(
    frontier: Mapping[str, Any], *, workspace: str | Path, as_of: str | None = None,
    successor_contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Report horizon status or compile one admitted-evidence transition settlement."""
    activation, contract, candidate, source_snapshot = _validated_contract(frontier)
    if successor_contract is not None:
        contract = _validated_successor_contract(contract, successor_contract)
    root = Path(workspace).expanduser().resolve()
    source_run_path = root / "data" / "latest_source_run.json"
    if as_of is None:
        if not source_run_path.exists():
            raise ValueError("an explicit as_of is required when no source run exists")
        as_of = json.loads(source_run_path.read_text(encoding="utf-8"))["as_of"]
    evaluated_at = canonical_timestamp(as_of, "company-state settlement as_of")
    due_at = canonical_timestamp(contract["settlement_not_before"], "company-state settlement horizon")
    if timestamp_key(evaluated_at) < timestamp_key(due_at):
        return _status(activation, contract, as_of=evaluated_at, status="horizon_not_reached")
    if not source_run_path.exists():
        return _status(
            activation, contract, as_of=evaluated_at, status="evidence_unavailable",
            reason="source_run_absent",
        )

    source_run = json.loads(source_run_path.read_text(encoding="utf-8"))
    source_run_body = dict(source_run)
    source_run_sha = str(source_run_body.pop("run_sha256", ""))
    if source_run_sha != stable_sha256(source_run_body):
        raise ValueError("company-state source run content hash mismatch")
    source_as_of = canonical_timestamp(source_run.get("as_of"), "company-state source run as_of")
    if timestamp_key(source_as_of) < timestamp_key(due_at):
        return _status(
            activation, contract, as_of=evaluated_at, status="evidence_unavailable",
            reason="source_run_precedes_horizon", source_run_sha256=source_run_sha,
        )
    if timestamp_key(source_as_of) > timestamp_key(evaluated_at):
        raise ValueError("company-state source run cannot be later than settlement as_of")
    observations_path = root / "data" / "observations.csv"
    if not observations_path.exists():
        return _status(
            activation, contract, as_of=evaluated_at, status="evidence_unavailable",
            reason="observations_absent", source_run_sha256=source_run_sha,
        )

    admitted_sources = _source_bindings(source_run)
    observations = tuple(
        row for row in _load_state_observations(
            observations_path, (str(contract["target_epoch"]),),
            source_as_of=source_as_of,
        )
        if row.source_ref in admitted_sources and timestamp_key(row.available_at) <= timestamp_key(source_as_of)
    )
    panels, _ = _state_panel(
        observations, (str(contract["target_epoch"]),), source_as_of=source_as_of,
        min_years=int(contract["min_years"]), min_cross_section=1,
        benchmark_id=str(contract["benchmark_id"]),
    )
    target_rows = [] if not panels else list(panels[0]["companies"])
    source_entities = {str(row["entity_id"]) for row in source_snapshot["assignments"]}
    target_rows = sorted(
        (row for row in target_rows if str(row["entity_id"]) in source_entities),
        key=lambda row: str(row["entity_id"]),
    )
    minimum_count = int(contract["minimum_target_entity_count"])
    if len(target_rows) < minimum_count:
        target_entities = {str(row["entity_id"]) for row in target_rows}
        missing_receipts = sorted({
            str(source_ref)
            for row in source_snapshot["assignments"]
            if str(row["entity_id"]) not in target_entities
            for source_ref in row["source_refs"]
            if str(source_ref) not in admitted_sources
        })
        if missing_receipts:
            return _status(
                activation, contract, as_of=evaluated_at, status="evidence_unavailable",
                reason="frozen_cohort_sources_not_admitted",
                missing_source_ref_count=len(missing_receipts),
                missing_source_refs_sha256=stable_sha256(missing_receipts),
                target_entity_count=len(target_rows), minimum_target_entity_count=minimum_count,
                source_run_sha256=source_run_sha,
            )
        return _status(
            activation, contract, as_of=evaluated_at, status="coverage_kill",
            reason="frozen_cohort_target_coverage_below_contract",
            target_entity_count=len(target_rows), minimum_target_entity_count=minimum_count,
            source_run_sha256=source_run_sha,
        )

    target = _partition_panel(
        {"epoch": contract["target_epoch"], "companies": target_rows},
        int(candidate["value_levels"]), int(candidate["durability_levels"]),
    )
    target_by_id = {str(row["entity_id"]): row for row in target_rows}
    target_assignments = [{
        "entity_id": entity_id,
        "state_id": state_id,
        "evidence_sha256": target_by_id[entity_id]["evidence_sha256"],
    } for entity_id, state_id in sorted(target["assignments"].items())]
    source_assignments = {
        str(row["entity_id"]): str(row["state_id"])
        for row in source_snapshot["assignments"]
    }
    state_ids = [str(value) for value in candidate["state_ids"]]
    counts = Counter(
        (source_assignments[row["entity_id"]], row["state_id"])
        for row in target_assignments
    )
    matrix = [[counts[(source, target_state)] for target_state in state_ids] for source in state_ids]
    settlement_body = {
        "schema": COMPANY_STATE_PARTITION_SETTLEMENT_SCHEMA,
        "activation_sha256": activation["activation_sha256"],
        "evidence_id": contract["evidence_id"],
        "partition_sha256": activation["partition_sha256"],
        "source_epoch": contract["source_epoch"],
        "target_epoch": contract["target_epoch"],
        "settled_at": evaluated_at,
        "source_run_sha256": source_run_sha,
        "state_ids": state_ids,
        "transition_counts": matrix,
        "transition_count": len(target_assignments),
        "target_entity_count": len(target_assignments),
        "target_thresholds": target["thresholds"],
        "target_assignments": target_assignments,
        "target_assignments_sha256": stable_sha256(target_assignments),
        "admitted_source_refs": sorted({
            source_ref for row in target_rows for source_ref in row["source_refs"]
        }),
        "signal_authority": False,
        "capital_authority": False,
    }
    settlement = {**settlement_body, "settlement_sha256": stable_sha256(settlement_body)}
    return _status(
        activation, contract, as_of=evaluated_at, status="settled", settlement=settlement,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace")
    parser.add_argument("--frontier", default="experiments/results/company-state-partition-frontier.json")
    parser.add_argument("--as-of")
    args = parser.parse_args(argv)
    root = Path(args.workspace).expanduser().resolve()
    frontier = json.loads((root / args.frontier).read_text(encoding="utf-8"))
    result = compile_company_state_partition_status(frontier, workspace=root, as_of=args.as_of)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "COMPANY_STATE_PARTITION_SETTLEMENT_SCHEMA",
    "COMPANY_STATE_PARTITION_STATUS_SCHEMA",
    "compile_company_state_partition_status",
]
