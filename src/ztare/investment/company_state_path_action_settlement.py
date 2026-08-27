"""Settle a frozen company-state path-action run without mutating its forecast."""

from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256

from .company_state_partition_settlement import compile_company_state_partition_status
from .company_state_path_action import (
    COMPANY_STATE_PATH_ACTION_RUN_SCHEMA,
    _validate_distributions,
)
from .contracts import canonical_timestamp, timestamp_key


COMPANY_STATE_PATH_ACTION_STATUS_SCHEMA = "jaggedthoughts-company-state-path-action-status-v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _validated_run(run: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if run.get("schema") != COMPANY_STATE_PATH_ACTION_RUN_SCHEMA:
        raise ValueError(f"path-action settlement requires {COMPANY_STATE_PATH_ACTION_RUN_SCHEMA}")
    body = dict(run)
    run_sha = str(body.pop("run_sha256", ""))
    if run_sha != stable_sha256(body):
        raise ValueError("company-state path-action run content hash mismatch")
    if any(run.get(key) is not False for key in (
        "signal_authority", "model_fit_authority", "capital_authority",
    )):
        raise ValueError("company-state path-action run cannot carry decision authority")
    if (run.get("settlement_scoring") or {}).get("rule") != "multiclass_brier_lower_is_better":
        raise ValueError("company-state path-action scoring rule changed")
    models = list(run.get("models") or ())
    state_ids = tuple(str(value) for value in run.get("state_ids") or ())
    _validate_distributions(models, state_ids)
    source_assignments = list((run.get("source_snapshot") or {}).get("assignments") or ())
    if stable_sha256(source_assignments) != run.get("source_assignments_sha256"):
        raise ValueError("company-state path-action source assignment identity mismatch")
    model_ids = {str(model["model_id"]) for model in models}
    required = {"path_action_current", *map(str, run.get("required_control_ids") or ())}
    if model_ids != required or any(
        model.get("signal_authority") is not False or model.get("capital_authority") is not False
        for model in models
    ):
        raise ValueError("company-state path-action frozen model set mismatch")
    contracts = {str(row.get("leg")): dict(row) for row in run.get("outcome_contracts") or ()}
    if set(contracts) != {"intermediate", "terminal"}:
        raise ValueError("company-state path-action requires intermediate and terminal contracts")
    for contract in contracts.values():
        contract_body = dict(contract)
        contract_sha = str(contract_body.pop("contract_sha256", ""))
        if contract_sha != stable_sha256(contract_body):
            raise ValueError("company-state path-action outcome contract hash mismatch")
        if contract.get("signal_authority") is not False or contract.get("capital_authority") is not False:
            raise ValueError("company-state path-action outcome contract cannot carry authority")
    if not (
        timestamp_key(str(run["opened_at"]))
        < timestamp_key(str(contracts["intermediate"]["settlement_not_before"]))
        < timestamp_key(str(contracts["terminal"]["settlement_not_before"]))
    ):
        raise ValueError("company-state path-action outcome chronology mismatch")
    freeze = dict(run.get("candidate_freeze") or {})
    if freeze:
        freeze_body = dict(freeze)
        freeze_sha = str(freeze_body.pop("freeze_sha256", ""))
        provenance = dict(freeze.get("candidate_provenance") or {})
        candidate_sha = str(freeze.get("candidate_sha256") or "")
        archive = dict(run.get("evidence_manifest_ref") or {})
        archive_body = dict(archive)
        archive_sha = str(archive_body.pop("ref_sha256", ""))
        if freeze_sha != stable_sha256(freeze_body):
            raise ValueError("company-state Newton candidate freeze hash mismatch")
        if hashlib.sha256(str(freeze.get("candidate_code", "")).encode()).hexdigest() != candidate_sha:
            raise ValueError("company-state Newton candidate code hash mismatch")
        if (
            provenance.get("status") != "resolved"
            or provenance.get("origin") != "subscription_newton_submission"
            or provenance.get("candidate_sha256") != candidate_sha
        ):
            raise ValueError("company-state Newton candidate provenance mismatch")
        if (
            archive_sha != stable_sha256(archive_body)
            or archive.get("status") != "covered"
            or archive.get("archive_authority") != "point_in_time_archive"
            or archive.get("required_source_ids") != sorted(map(str, run.get("source_refs") or ()))
        ):
            raise ValueError("company-state Newton evidence archive mismatch")
        if any(
            contract.get("candidate_sha256") != candidate_sha
            or contract.get("evidence_manifest_ref_sha256") != archive_sha
            for contract in contracts.values()
        ):
            raise ValueError("company-state Newton outcome contract candidate binding mismatch")
        source_contracts = {
            str(row["leg"]): dict(row) for row in run.get("source_outcome_contract_refs") or ()
        }
        if set(source_contracts) != set(contracts) or any(
            contracts[leg].get("base_evidence_id") == contracts[leg].get("evidence_id")
            or contracts[leg].get("base_evidence_id") != source_contracts[leg].get("evidence_id")
            or contracts[leg].get("source_contract_sha256") != source_contracts[leg].get("contract_sha256")
            for leg in contracts
        ):
            raise ValueError("company-state Newton successor reused or lost its source contracts")
    return contracts["intermediate"], contracts["terminal"]


def _validated_settlement(row: Mapping[str, Any]) -> dict[str, Any]:
    settlement = dict(row)
    body = dict(settlement)
    settlement_sha = str(body.pop("settlement_sha256", ""))
    if settlement_sha != stable_sha256(body):
        raise ValueError("company-state assignment settlement content hash mismatch")
    if settlement.get("signal_authority") is not False or settlement.get("capital_authority") is not False:
        raise ValueError("company-state assignment settlement cannot carry authority")
    return settlement


def _validated_prior(prior: Mapping[str, Any] | None, run: Mapping[str, Any]) -> dict[str, Any]:
    if not prior:
        return {}
    if prior.get("schema") != COMPANY_STATE_PATH_ACTION_STATUS_SCHEMA:
        raise ValueError("company-state path-action prior status schema mismatch")
    body = dict(prior)
    status_sha = str(body.pop("status_sha256", ""))
    if status_sha != stable_sha256(body) or prior.get("run_sha256") != run.get("run_sha256"):
        raise ValueError("company-state path-action prior status identity mismatch")
    if prior.get("signal_authority") is not False or prior.get("capital_authority") is not False:
        raise ValueError("company-state path-action prior status cannot carry authority")
    for leg in ("intermediate", "terminal"):
        row = prior.get(leg) or {}
        if row.get("status") == "settled":
            _validated_settlement(row["settlement"])
    return dict(prior)


def _assignment_map(settlement: Mapping[str, Any]) -> dict[str, str]:
    return {
        str(row["entity_id"]): str(row["state_id"])
        for row in settlement.get("target_assignments") or ()
    }


def score_company_state_path_models(
    run: Mapping[str, Any], *,
    intermediate_assignments: Mapping[str, str],
    terminal_assignments: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Score every frozen model on intermediate marginals or completed joint paths."""
    source_assignments = {
        str(row["entity_id"]): str(row["state_id"])
        for row in (run.get("source_snapshot") or {}).get("assignments") or ()
    }
    state_ids = tuple(str(value) for value in run["state_ids"])
    terminal = dict(terminal_assignments or {})
    entity_ids = sorted(set(source_assignments) & set(intermediate_assignments))
    unit = "intermediate_state"
    if terminal_assignments is not None:
        entity_ids = sorted(set(entity_ids) & set(terminal))
        unit = "joint_intermediate_terminal_path"
    if not entity_ids:
        raise ValueError("company-state path scoring has no settled frozen-cohort entities")

    scores = []
    for model in run["models"]:
        by_source = {
            str(row["source_state_id"]): list(row["paths"])
            for row in model["conditional_path_distributions"]
        }
        losses = []
        for entity_id in entity_ids:
            paths = by_source[source_assignments[entity_id]]
            if terminal_assignments is None:
                probabilities = {
                    state_id: math.fsum(
                        float(row["probability"]) for row in paths
                        if row["intermediate_state_id"] == state_id
                    ) for state_id in state_ids
                }
                actual = intermediate_assignments[entity_id]
                losses.append(math.fsum(
                    (probabilities[state_id] - float(state_id == actual)) ** 2
                    for state_id in state_ids
                ))
            else:
                actual = (intermediate_assignments[entity_id], terminal[entity_id])
                losses.append(math.fsum(
                    (float(row["probability"]) - float(
                        (row["intermediate_state_id"], row["terminal_state_id"]) == actual
                    )) ** 2 for row in paths
                ))
        scores.append({
            "model_id": model["model_id"],
            "role": model["role"],
            "mean_brier": math.fsum(losses) / len(losses),
            "entity_count": len(losses),
        })
    body = {
        "rule": "multiclass_brier_lower_is_better",
        "unit": unit,
        "scores": scores,
        "best_model_ids": sorted(
            row["model_id"] for row in scores
            if row["mean_brier"] == min(value["mean_brier"] for value in scores)
        ),
        "signal_authority": False,
        "capital_authority": False,
    }
    return {**body, "score_sha256": stable_sha256(body)}


def _leg_from_partition_status(status: Mapping[str, Any]) -> dict[str, Any]:
    row = {
        "status": status["status"],
        "as_of": status["as_of"],
        "evidence_id": status["evidence_id"],
        "target_epoch": status["target_epoch"],
        "settlement_not_before": status["settlement_not_before"],
    }
    for key in (
        "reason", "target_entity_count", "minimum_target_entity_count",
        "missing_source_ref_count", "missing_source_refs_sha256", "source_run_sha256",
        "settlement",
    ):
        if key in status:
            row[key] = status[key]
    return row


def compile_model_research_activation(
    run: Mapping[str, Any], terminal_score: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Route a settled path challenger without confusing survival with admission."""
    empirical_control_present = "empirical_markov_path_control" in {
        str(model["model_id"]) for model in run["models"]
    }
    activation: dict[str, Any] = {
        "run_sha256": run["run_sha256"],
        "terminal_score_sha256": (
            terminal_score.get("score_sha256") if terminal_score else None
        ),
        "status": (
            "awaiting_prospective_outcomes" if empirical_control_present
            else "awaiting_outcomes_with_legacy_control_gap"
        ),
        "action": "none_before_settlement",
        "reason": (
            "The frozen path candidate and controls have no observable outcome yet."
            if empirical_control_present else
            "The immutable run predates the empirical same-information Markov control. Do not "
            "amend or overlap it; open that comparison only if this candidate survives settlement."
        ),
        "empirical_markov_control_present": empirical_control_present,
        "automatic_model_mutation": False,
        "capital_authority": False,
    }
    if terminal_score is not None:
        scores = {
            row["model_id"]: row["mean_brier"] for row in terminal_score["scores"]
        }
        challenger_wins = scores["path_action_current"] < min(
            score for model_id, score in scores.items()
            if model_id != "path_action_current"
        )
        if challenger_wins and not empirical_control_present:
            activation.update({
                "status": "successor_research_due",
                "action": "open_nonoverlapping_empirical_markov_comparison",
                "reason": (
                    "The legacy path candidate survived its frozen controls, but its evidence bytes "
                    "did not contain an empirical same-information Markov control. Freeze that control "
                    "in a distinct later source epoch before any equation search."
                ),
            })
        elif challenger_wins:
            activation.update({
                "status": "successor_research_due",
                "action": "subscription_newton_successor_project",
                "reason": (
                    "The path action beat every frozen ordinary control; a separately identified "
                    "subscription research project may search the next action carrier."
                ),
            })
        else:
            activation.update({
                "status": "retire_research_due",
                "action": "retire_path_action_identity",
                "reason": "The frozen path action failed at least one simpler prospective control.",
            })
    activation["activation_sha256"] = stable_sha256(activation)
    return activation


def compile_company_state_path_action_status(
    run: Mapping[str, Any], frontier: Mapping[str, Any], *,
    workspace: str | Path,
    as_of: str | None = None,
    prior_status: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Bind each due leg once, then score the unchanged prospective run."""
    intermediate_contract, terminal_contract = _validated_run(run)
    activation = dict(frontier.get("activation") or {})
    frontier_identity = dict(activation.get("next_evidence_identity") or {})
    if (
        dict(intermediate_contract.get("frontier_evidence_identity") or {}) != frontier_identity
        or dict(run.get("source_snapshot") or {}) != dict(activation.get("source_snapshot") or {})
    ):
        raise ValueError("company-state path-action run no longer matches its frozen frontier")
    prior = _validated_prior(prior_status, run)
    root = Path(workspace).expanduser().resolve()
    explicit_as_of = as_of is not None
    if as_of is None:
        as_of = _utc_now()
    evaluated_at = canonical_timestamp(as_of, "company-state path-action status as_of")
    opened_at = canonical_timestamp(run["opened_at"], "company-state path-action opened_at")
    if timestamp_key(evaluated_at) < timestamp_key(opened_at):
        if explicit_as_of:
            raise ValueError("company-state path-action status cannot precede the frozen run")
        evaluated_at = opened_at
    if prior and not explicit_as_of and timestamp_key(evaluated_at) < timestamp_key(str(prior["as_of"])):
        evaluated_at = str(prior["as_of"])
    if prior and timestamp_key(evaluated_at) < timestamp_key(str(prior["as_of"])):
        raise ValueError("company-state path-action status cannot move backward in time")

    intermediate = dict(prior.get("intermediate") or {})
    if intermediate.get("status") != "settled":
        intermediate_successor = (
            intermediate_contract
            if intermediate_contract.get("evidence_id") != frontier_identity.get("evidence_id")
            else None
        )
        intermediate = _leg_from_partition_status(compile_company_state_partition_status(
            frontier, workspace=root, as_of=evaluated_at,
            successor_contract=intermediate_successor,
        ))
    intermediate_score = None
    if intermediate.get("status") == "settled":
        intermediate_settlement = _validated_settlement(intermediate["settlement"])
        intermediate_score = score_company_state_path_models(
            run, intermediate_assignments=_assignment_map(intermediate_settlement),
        )

    terminal = dict(prior.get("terminal") or {})
    if intermediate.get("status") != "settled":
        terminal = {
            "status": (
                "blocked_on_intermediate_and_horizon"
                if timestamp_key(evaluated_at) < timestamp_key(
                    str(terminal_contract["settlement_not_before"])
                ) else "blocked_on_intermediate"
            ),
            "as_of": evaluated_at,
            "evidence_id": terminal_contract["evidence_id"],
            "target_epoch": terminal_contract["target_epoch"],
            "settlement_not_before": terminal_contract["settlement_not_before"],
        }
    elif terminal.get("status") != "settled":
        terminal = _leg_from_partition_status(compile_company_state_partition_status(
            frontier, workspace=root, as_of=evaluated_at,
            successor_contract=terminal_contract,
        ))

    terminal_score = None
    if terminal.get("status") == "settled":
        terminal_settlement = _validated_settlement(terminal["settlement"])
        terminal_score = score_company_state_path_models(
            run,
            intermediate_assignments=_assignment_map(intermediate["settlement"]),
            terminal_assignments=_assignment_map(terminal_settlement),
        )

    if intermediate.get("status") != "settled":
        status = (
            "awaiting_intermediate_horizon"
            if intermediate.get("status") == "horizon_not_reached"
            else "intermediate_coverage_kill"
            if intermediate.get("status") == "coverage_kill"
            else "awaiting_intermediate_evidence"
        )
        next_due_at = intermediate_contract["settlement_not_before"]
    elif terminal.get("status") != "settled":
        status = (
            "intermediate_bound_awaiting_terminal_horizon"
            if terminal.get("status") == "horizon_not_reached"
            else "terminal_coverage_kill"
            if terminal.get("status") == "coverage_kill"
            else "awaiting_terminal_evidence"
        )
        next_due_at = terminal_contract["settlement_not_before"]
    else:
        status, next_due_at = "settled", None

    research_activation = compile_model_research_activation(run, terminal_score)

    body: dict[str, Any] = {
        "schema": COMPANY_STATE_PATH_ACTION_STATUS_SCHEMA,
        "run_id": run["run_id"],
        "run_sha256": run["run_sha256"],
        "generation_mode": run.get("generation_mode", "deterministic_declared_seed"),
        "subscription_newton_searched": bool(run.get("subscription_newton_searched", False)),
        "status": status,
        "as_of": evaluated_at,
        "due_dates": {
            "intermediate": intermediate_contract["settlement_not_before"],
            "terminal": terminal_contract["settlement_not_before"],
        },
        "next_due_at": next_due_at,
        "intermediate": intermediate,
        "terminal": terminal,
        "scores": {
            "intermediate": intermediate_score,
            "terminal": terminal_score,
        },
        "model_research_activation": research_activation,
        "run_unchanged": True,
        "signal_authority": False,
        "capital_authority": False,
    }
    return {**body, "status_sha256": stable_sha256(body)}


def main() -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("workspace")
    parser.add_argument("run")
    parser.add_argument("--frontier", default="experiments/results/company-state-partition-frontier.json")
    parser.add_argument("--prior-status")
    parser.add_argument("--as-of")
    args = parser.parse_args()
    root = Path(args.workspace).expanduser().resolve()
    run = json.loads(Path(args.run).expanduser().resolve().read_text(encoding="utf-8"))
    frontier = json.loads((root / args.frontier).read_text(encoding="utf-8"))
    prior = (
        json.loads(Path(args.prior_status).expanduser().resolve().read_text(encoding="utf-8"))
        if args.prior_status else None
    )
    result = compile_company_state_path_action_status(
        run, frontier, workspace=root, as_of=args.as_of, prior_status=prior,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "COMPANY_STATE_PATH_ACTION_STATUS_SCHEMA",
    "compile_model_research_activation",
    "compile_company_state_path_action_status",
    "score_company_state_path_models",
]
