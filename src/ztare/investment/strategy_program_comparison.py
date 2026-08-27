"""Compare source-bound integrated programs with matched operating controls."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, timestamp_key
from .strategy_learning import STRATEGY_PROGRAM_OUTCOME_PLAN_SCHEMA
from .strategy_outcome_acquisition import (
    STRATEGY_PROGRAM_CONTROL_OUTCOME_EPISODE_SCHEMA,
    STRATEGY_PROGRAM_OUTCOME_EPISODE_SCHEMA,
)
from .strategy_transfer import STRATEGY_PROGRAM_TRANSFER_INDEX_SCHEMA
from .strategy_transfer_acquisition import STRATEGY_PROGRAM_CONTROL_ACQUISITION_SCHEMA


STRATEGY_PROGRAM_OPERATING_COMPARISON_SCHEMA = (
    "jaggedthoughts-strategy-program-operating-comparison-v1"
)
_MIN_ARM_ENTITIES = 4
_MIN_SHARED_ENVIRONMENTS = 2


def _valid_hashed(row: Mapping[str, Any], schema: str, hash_field: str) -> bool:
    return bool(
        row.get("schema") == schema
        and row.get(hash_field) == stable_sha256({
            key: value for key, value in row.items() if key != hash_field
        })
    )


def _environment(row: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(sorted(map(str, row.get("environment_boundaries") or ())))


def _signed_effect(row: Mapping[str, Any]) -> float:
    effect = float(row["observed_effect"])
    return effect if row["direction"] == "increase" else -effect


def _comparison(
    treated: list[dict[str, Any]], controls: list[dict[str, Any]], *,
    control_identity: str, minimum_effect: float,
) -> dict[str, Any]:
    treated_by_environment: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    control_by_environment: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in treated:
        treated_by_environment[_environment(row)].append(row)
    for row in controls:
        if row["control_identity"] == control_identity:
            control_by_environment[_environment(row)].append(row)
    shared = sorted(set(treated_by_environment) & set(control_by_environment))
    strata = []
    for environment in shared:
        left, right = treated_by_environment[environment], control_by_environment[environment]
        treated_mean = mean(_signed_effect(row) for row in left)
        control_mean = mean(_signed_effect(row) for row in right)
        delta = treated_mean - control_mean
        strata.append({
            "environment_boundaries": list(environment),
            "treated_entity_ids": sorted({str(row["entity_id"]) for row in left}),
            "control_entity_ids": sorted({str(row["entity_id"]) for row in right}),
            "treated_mean_signed_effect": treated_mean,
            "control_mean_signed_effect": control_mean,
            "operating_association": delta,
            "threshold_normalized_association": (
                delta / minimum_effect if minimum_effect > 0 else None
            ),
        })
    treated_entities = {
        str(row["entity_id"]) for environment in shared
        for row in treated_by_environment[environment]
    }
    control_entities = {
        str(row["entity_id"]) for environment in shared
        for row in control_by_environment[environment]
    }
    ready = bool(
        len(treated_entities) >= _MIN_ARM_ENTITIES
        and len(control_entities) >= _MIN_ARM_ENTITIES
        and len(shared) >= _MIN_SHARED_ENVIRONMENTS
    )
    return {
        "control_identity": control_identity,
        "treated_entity_count": len(treated_entities),
        "control_entity_count": len(control_entities),
        "shared_environment_count": len(shared),
        "minimum_arm_entities": _MIN_ARM_ENTITIES,
        "minimum_shared_environments": _MIN_SHARED_ENVIRONMENTS,
        "environment_strata": strata,
        "equal_weight_environment_association": (
            mean(row["operating_association"] for row in strata) if strata else None
        ),
        "equal_weight_threshold_normalized_association": (
            mean(row["threshold_normalized_association"] for row in strata)
            if strata and minimum_effect > 0 else None
        ),
        "operating_association_reviewable": ready,
        "causal_program_credit_eligible": False,
    }


def compile_strategy_program_operating_comparison(
    *, program_transfer: Mapping[str, Any],
    control_acquisition: Mapping[str, Any],
    program_plans: Iterable[Mapping[str, Any]],
    program_episodes: Iterable[Mapping[str, Any]],
    control_episodes: Iterable[Mapping[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    """Estimate exact-environment operating associations; never causal credit."""
    if program_transfer.get("schema") != STRATEGY_PROGRAM_TRANSFER_INDEX_SCHEMA:
        raise ValueError("program comparison requires a program-transfer index")
    if program_transfer.get("index_sha256") != stable_sha256({
        key: value for key, value in program_transfer.items() if key != "index_sha256"
    }):
        raise ValueError("program comparison transfer-index hash mismatch")
    if control_acquisition.get("schema") != STRATEGY_PROGRAM_CONTROL_ACQUISITION_SCHEMA:
        raise ValueError("program comparison requires program-control acquisition")
    if control_acquisition.get("acquisition_sha256") != stable_sha256({
        key: value for key, value in control_acquisition.items()
        if key != "acquisition_sha256"
    }):
        raise ValueError("program comparison control-acquisition hash mismatch")
    if control_acquisition.get("program_transfer_sha256") != program_transfer.get("index_sha256"):
        raise ValueError("program comparison inputs cross transfer identities")
    epoch = canonical_timestamp(generated_at, "program comparison generated_at")

    plans = {
        str(row["plan_sha256"]): dict(row)
        for row in program_plans if isinstance(row, Mapping)
        and _valid_hashed(row, STRATEGY_PROGRAM_OUTCOME_PLAN_SCHEMA, "plan_sha256")
    }
    program_outcomes: dict[str, dict[str, Any]] = {}
    for row in program_episodes:
        if not isinstance(row, Mapping) or not _valid_hashed(
            row, STRATEGY_PROGRAM_OUTCOME_EPISODE_SCHEMA, "episode_sha256",
        ) or timestamp_key(str(row["available_at"])) > timestamp_key(epoch):
            continue
        readout_sha = str(row["readout_sha256"])
        if readout_sha in program_outcomes:
            raise ValueError("program comparison received duplicate treated readout")
        plan = plans.get(str(row["plan_sha256"]))
        if plan is None or readout_sha not in {
            str(readout.get("readout_sha256")) for readout in plan.get("readouts") or ()
        }:
            raise ValueError("program comparison outcome crossed prospective plan")
        program_outcomes[readout_sha] = {**dict(row), **{
            "program_phenotype_sha256": plan["program_phenotype_sha256"],
            "program_roles": list(plan.get("program_roles") or ()),
            "environment_boundaries": list(plan.get("environment_boundaries") or ()),
        }}
    control_outcomes: dict[str, dict[str, Any]] = {}
    for row in control_episodes:
        if not isinstance(row, Mapping) or not _valid_hashed(
            row, STRATEGY_PROGRAM_CONTROL_OUTCOME_EPISODE_SCHEMA, "episode_sha256",
        ) or timestamp_key(str(row["available_at"])) > timestamp_key(epoch):
            continue
        plan_sha = str(row["control_plan_sha256"])
        if plan_sha in control_outcomes:
            raise ValueError("program comparison received duplicate control readout")
        if row.get("program_control_acquisition_sha256") != control_acquisition.get(
            "acquisition_sha256"
        ):
            raise ValueError("program comparison control outcome crossed acquisition")
        control_outcomes[plan_sha] = dict(row)

    acquisition_by_transfer = {
        str(row.get("transfer_card_sha256")): row
        for row in control_acquisition.get("cards") or () if isinstance(row, Mapping)
    }
    cards = []
    for transfer_card in program_transfer.get("cards") or ():
        if not isinstance(transfer_card, Mapping):
            continue
        card_sha = str(transfer_card.get("card_sha256") or "")
        acquisition_card = acquisition_by_transfer.get(card_sha) or {}
        treated_episode_ids = set(map(str, transfer_card.get("episode_sha256s") or ()))
        treated = [
            row for row in program_outcomes.values()
            if str(row["episode_sha256"]) in treated_episode_ids
            and row["program_phenotype_sha256"] == transfer_card.get("program_phenotype_sha256")
            and "global_frontier" in row["program_roles"]
            and str(row["metric_id"]) == str(transfer_card["metric_id"])
            and str(row["unit"]) == str(transfer_card["unit"])
            and str(row["direction"]) == str(transfer_card["direction"])
            and float(row["minimum_effect"]) == float(transfer_card["minimum_effect"])
        ]
        controls = [
            row for row in control_outcomes.values()
            if row.get("transfer_card_sha256") == card_sha
            and str(row["metric_id"]) == str(transfer_card["metric_id"])
            and str(row["unit"]) == str(transfer_card["unit"])
            and str(row["direction"]) == str(transfer_card["direction"])
            and float(row["minimum_effect"]) == float(transfer_card["minimum_effect"])
            and int(row.get("horizon_days") or 0) == int(transfer_card["horizon_days"])
            and str(row.get("outcome_role") or "terminal_operating")
            == str(transfer_card.get("outcome_role") or "terminal_operating")
            and str(row.get("acquisition_mode") or "subscription_primary_document")
            == str(transfer_card.get("acquisition_mode") or "subscription_primary_document")
            and str(row.get("source_definition_sha256") or "")
            == str(transfer_card.get("source_definition_sha256") or "")
        ]
        comparisons = [
            _comparison(
                treated, controls, control_identity=identity,
                minimum_effect=float(transfer_card["minimum_effect"]),
            ) for identity in (
                "same_constituents_without_joint_evidence", "one_choice_base_program",
                "same_size_local_peak",
            )
        ]
        body = {
            "transfer_card_sha256": card_sha,
            "acquisition_card_sha256": acquisition_card.get("acquisition_card_sha256"),
            "program_phenotype_sha256": transfer_card.get("program_phenotype_sha256"),
            "readout_signature": {
                key: transfer_card.get(key) for key in (
                    "metric_id", "unit", "direction", "minimum_effect", "horizon_days",
                    "outcome_role", "acquisition_mode", "source_definition_sha256",
                )
            },
            "treated_episode_sha256s": sorted(str(row["episode_sha256"]) for row in treated),
            "control_episode_sha256s": sorted(str(row["episode_sha256"]) for row in controls),
            "comparisons": comparisons,
            "operating_association_reviewable": any(
                row["operating_association_reviewable"] for row in comparisons
            ),
            "causal_program_credit_eligible": False,
            "security_return_credit_eligible": False,
            "rank_authority": False, "portfolio_weight": 0.0,
            "capital_authority": False,
        }
        cards.append({**body, "comparison_card_sha256": stable_sha256(body)})
    composition = [
        comparison for card in cards for comparison in card["comparisons"]
        if comparison["control_identity"] == "same_constituents_without_joint_evidence"
    ]
    one_choice = [
        comparison for card in cards for comparison in card["comparisons"]
        if comparison["control_identity"] == "one_choice_base_program"
    ]
    reviewable = [comparison for card in cards for comparison in card["comparisons"]]
    body = {
        "schema": STRATEGY_PROGRAM_OPERATING_COMPARISON_SCHEMA,
        "generated_at": epoch,
        "program_transfer_sha256": program_transfer.get("index_sha256"),
        "program_control_acquisition_sha256": control_acquisition.get("acquisition_sha256"),
        "card_count": len(cards),
        "treated_episode_count": sum(len(row["treated_episode_sha256s"]) for row in cards),
        "control_episode_count": sum(len(row["control_episode_sha256s"]) for row in cards),
        "reviewable_composition_card_count": sum(
            row["operating_association_reviewable"] for row in composition
        ),
        "reviewable_one_choice_card_count": sum(
            row["operating_association_reviewable"] for row in one_choice
        ),
        "cards": cards,
        "status": (
            "operating_association_reviewable"
            if any(row["operating_association_reviewable"] for row in reviewable)
            else "awaiting_matched_control_outcomes"
            if any(row["settled_episode_count"] for row in program_transfer.get("cards") or ())
            else "awaiting_integrated_program_outcomes"
        ),
        "next_activation": (
            "Review the source-bound operating association; causal and security-return credit remain separate."
            if any(row["operating_association_reviewable"] for row in reviewable)
            else "Settle assessment-time integrated and matched-control readouts in exact environment strata."
        ),
        "operating_association_reviewable": any(
            row["operating_association_reviewable"] for row in reviewable
        ),
        "causal_program_credit": False, "security_return_credit": False,
        "rank_authority": False, "portfolio_weight": 0.0,
        "capital_authority": False,
    }
    return {**body, "comparison_sha256": stable_sha256(body)}


__all__ = [
    "STRATEGY_PROGRAM_OPERATING_COMPARISON_SCHEMA",
    "compile_strategy_program_operating_comparison",
]
