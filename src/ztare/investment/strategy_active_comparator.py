"""Pre-outcome eligibility frontier for active strategy comparators."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256

from .company_quality import compile_company_quality_history
from .contracts import canonical_timestamp, timestamp_key
from .strategy_learning import (
    STRATEGY_COHORT_PLAN_SCHEMA,
    STRATEGY_PHENOTYPE_DIMENSIONS,
    resolve_strategy_cohort_results,
)


STRATEGY_ACTIVE_COMPARATOR_FRONTIER_SCHEMA = (
    "jaggedthoughts-strategy-active-comparator-frontier-v1"
)
_PROJECTION_SCHEMA = "jaggedthoughts-strategy-phenotype-projection-frontier-v1"
_ACTIVE_STATES = {"operational", "completed"}


def _checked_hash(row: Mapping[str, Any], field: str, label: str) -> str:
    body = dict(row)
    declared = str(body.pop(field, ""))
    if declared != stable_sha256(body):
        raise ValueError(f"{label} content hash mismatch")
    return declared


def _history_periods(reports: Iterable[Mapping[str, Any]]) -> tuple[list[int], list[datetime]]:
    heads = sorted({
        timestamp_key(str(report["history"][-1]["observed_at"]))
        for report in reports if report.get("history")
    })
    return sorted({value.year for value in heads}), heads


def _full_fiscal_period(event_at: datetime, fiscal_heads: list[datetime]) -> int:
    same_year = [value for value in fiscal_heads if value.year == event_at.year]
    if same_year:
        partial = event_at.year + (max(same_year) < event_at)
    else:
        month_day = max(value.strftime("%m-%d") for value in fiscal_heads)
        partial = event_at.year + (event_at.strftime("%m-%d") > month_day)
    return partial + 1


def _relation_class(event: Mapping[str, Any], fields: tuple[str, ...]) -> str:
    relation = dict(event.get("focal_relation") or {})
    if event.get("source_role") == "focal_move":
        return "P"
    if set(relation) != set(STRATEGY_PHENOTYPE_DIMENSIONS) or "unclear" in relation.values():
        return "ambiguous"
    if all(relation[field] == "same" for field in STRATEGY_PHENOTYPE_DIMENSIONS):
        return "P"
    return "Q" if any(relation[field] != "same" for field in fields) else "projection_ambiguous"


def _event_row(raw: Mapping[str, Any], *, source_role: str) -> dict[str, Any]:
    event = dict(raw)
    state = str(event.get("implementation_state") or event.get("status_after") or "")
    timing = str(event.get("timing_precision") or "")
    exact = timing == "date" or event.get("treatment_timing_status") == "exact_adoption_event"
    return {
        **event,
        "source_role": source_role,
        "implementation_state": state,
        "exact_event_date": exact,
        "event_sha256": str(
            event.get("event_sha256") or event.get("implementation_event_sha256") or ""
        ),
    }


def _select_entity(
    entity: str, events: list[dict[str, Any]], fields: tuple[str, ...],
    reports: Iterable[Mapping[str, Any]], *, industry: str, evidence_epoch: str,
    minimum_pre: int, minimum_post: int, washout_days: int,
) -> dict[str, Any]:
    reasons: list[str] = []
    active = [
        event for event in events
        if event["implementation_state"] in _ACTIVE_STATES and event["exact_event_date"]
        and timestamp_key(str(event["available_at"])) <= timestamp_key(evidence_epoch)
    ]
    if not active:
        if any(not event["exact_event_date"] for event in events):
            reasons.append("exact_event_date_missing")
        if any(event["implementation_state"] not in _ACTIVE_STATES for event in events):
            reasons.append("implementation_not_operational_or_completed")
        if any(timestamp_key(str(event["available_at"])) > timestamp_key(evidence_epoch) for event in events):
            reasons.append("event_after_evidence_epoch")
        reasons.append("no_eligible_active_event")
    classes = {_relation_class(event, fields) for event in active}
    if "ambiguous" in classes:
        reasons.append("P_Q_relation_ambiguity")
    if "projection_ambiguous" in classes:
        reasons.append("projection_collapses_P_and_Q")
    if {"P", "Q"}.issubset(classes):
        reasons.append("P_Q_crossover_contamination")
    dates: dict[str, int] = Counter(str(event.get("occurred_at"))[:10] for event in active)
    if any(count > 1 for count in dates.values()):
        reasons.append("same_date_event_bundle")
    ordered = sorted(active, key=lambda event: (str(event["occurred_at"]), event["event_sha256"]))
    if len(ordered) > 1 and any(
        abs((timestamp_key(str(right["occurred_at"])) - timestamp_key(str(left["occurred_at"]))).days)
        <= washout_days
        for left, right in zip(ordered, ordered[1:])
    ):
        reasons.append("active_event_washout_failed")
    elif len(ordered) > 1:
        reasons.append("repeated_active_event_contamination")

    index = ordered[0] if len(ordered) == 1 and not reasons else None
    periods, fiscal_heads = _history_periods(reports)
    treatment_period = _full_fiscal_period(
        timestamp_key(str(index["occurred_at"])), fiscal_heads,
    ) if index and fiscal_heads else None
    pre = sum(period < treatment_period for period in periods) if treatment_period else 0
    post = sum(period >= treatment_period for period in periods) if treatment_period else 0
    if index and pre < minimum_pre:
        reasons.append("company_facts_pre_history_floor_missing")
    if index and pre >= minimum_pre and post < minimum_post:
        reasons.append("post_outcome_not_yet_available")
    relation_class = _relation_class(index, fields) if index else None
    partition = (
        "missing_history" if index and pre < minimum_pre else
        "awaiting_post_outcome" if index and post < minimum_post else
        "focal" if index and relation_class == "P" and not reasons else
        "eligible_active_alternative" if index and relation_class == "Q" and not reasons else
        "ambiguous_or_contaminated"
    )
    return {
        "entity_id": entity, "industry_id": industry,
        "calendar_risk_year": int(str(index["occurred_at"])[:4]) if index else None,
        "relation_class": relation_class,
        "q_phenotype_sha256": None,
        "q_identity_status": "relation_to_P_only_full_Q_phenotype_not_observed",
        "index_event": ({
            "event_sha256": index["event_sha256"],
            "occurred_at": index["occurred_at"], "available_at": index["available_at"],
            "implementation_state": index["implementation_state"],
            "focal_relation": index.get("focal_relation"),
        } if index else None),
        "index_selection_rule": "sole_operational_or_completed_exact_date_event_pre_outcome",
        "history": {
            "periods": periods, "treatment_period": treatment_period,
            "pre_period_count": pre, "post_period_count": post,
        },
        "partition": partition, "kill_reasons": sorted(set(reasons)),
    }


def compile_strategy_active_comparator_frontier(
    plan: Mapping[str, Any], projection_frontier: Mapping[str, Any],
    results: Iterable[Mapping[str, Any]],
    histories: Mapping[str, Iterable[Mapping[str, Any]]], *,
    historical_requests: Iterable[Mapping[str, Any]] = (),
    minimum_pre_periods: int = 2, minimum_post_periods: int = 1,
    minimum_independent_focal_firms: int = 2,
    minimum_independent_alternative_firms: int = 2,
    washout_days: int = 365,
) -> dict[str, Any]:
    """Partition P and relation-only Q events without estimating an effect."""
    if plan.get("schema") != STRATEGY_COHORT_PLAN_SCHEMA:
        raise ValueError(f"active comparators require {STRATEGY_COHORT_PLAN_SCHEMA}")
    if projection_frontier.get("schema") != _PROJECTION_SCHEMA:
        raise ValueError(f"active comparators require {_PROJECTION_SCHEMA}")
    plan_sha = _checked_hash(plan, "plan_sha256", "strategy cohort plan")
    projection_sha = _checked_hash(
        projection_frontier, "projection_frontier_sha256", "strategy projection frontier",
    )
    if projection_frontier.get("plan_sha256") != plan_sha:
        raise ValueError("strategy projection frontier crossed its cohort-plan identity")
    evidence_epoch = canonical_timestamp(
        (projection_frontier.get("certificate") or {}).get("scope", {}).get("evidence_epoch"),
        "active comparator evidence epoch",
    )
    outcome_contract = {
        "metric_id": "earnings_durability",
        "unit": "score",
        "fiscal_alignment": "first_full_fiscal_period_after_index_event",
        "minimum_post_periods": minimum_post_periods,
        "aggregation": "independent_firm_equal_weight_within_industry_calendar_cell",
    }
    outcome_contract_sha = stable_sha256(outcome_contract)
    resolved, coverage = resolve_strategy_cohort_results(
        plan, results, historical_requests=historical_requests,
    )
    requests = {str(row["request_sha256"]): row for row in plan.get("requests") or ()}
    frontier_programs = [
        row for row in projection_frontier.get("projections") or ()
        if row.get("frontier_status") == "frontier"
    ]
    groups = []
    missing_entities: set[str] = set()
    for environment in plan.get("mechanism_environments") or ():
        phenotype = str(environment["mechanism_phenotype_sha256"])
        family = str(environment["mechanism_signature_sha256"])
        industry = str(environment["industry_id"])
        base_events: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for move in environment.get("focal_moves") or ():
            base_events[str(move["entity_id"]).upper()].append(
                _event_row(move["implementation_event"], source_role="focal_move")
            )
        for request_sha, result in resolved.items():
            request = requests[request_sha]
            if (
                request.get("mechanism_phenotype_sha256") != phenotype
                or request.get("industry_id") != industry
            ):
                continue
            entity = str(request["peer_entity_id"]).upper()
            for event in result.get("events") or ():
                base_events[entity].append(_event_row(event, source_role="cohort_event"))
        for request in requests.values():
            if (
                request.get("mechanism_phenotype_sha256") == phenotype
                and request.get("industry_id") == industry
            ):
                base_events.setdefault(str(request["peer_entity_id"]).upper(), [])
        for projection in frontier_programs:
            fields = tuple(map(str, projection.get("required_relation_fields") or ()))
            rows = [
                _select_entity(
                    entity, events, fields, histories.get(entity, ()), industry=industry,
                    evidence_epoch=evidence_epoch, minimum_pre=minimum_pre_periods,
                    minimum_post=minimum_post_periods, washout_days=washout_days,
                )
                for entity, events in sorted(base_events.items())
            ]
            missing_entities.update(
                row["entity_id"] for row in rows if row["partition"] == "missing_history"
            )
            risk_cells = []
            by_cell: dict[int, list[dict[str, Any]]] = defaultdict(list)
            for row in rows:
                if row["calendar_risk_year"] is not None:
                    by_cell[int(row["calendar_risk_year"])].append(row)
            for year, members in sorted(by_cell.items()):
                focal = sorted(row["entity_id"] for row in members if row["partition"] == "focal")
                alternative = sorted(
                    row["entity_id"] for row in members
                    if row["partition"] == "eligible_active_alternative"
                )
                risk_cells.append({
                    "industry_id": industry, "calendar_risk_year": year,
                    "focal_entity_ids": focal, "active_alternative_entity_ids": alternative,
                    "independent_focal_firm_count": len(focal),
                    "independent_alternative_firm_count": len(alternative),
                    "declared_floor_met": (
                        len(focal) >= minimum_independent_focal_firms
                        and len(alternative) >= minimum_independent_alternative_firms
                    ),
                })
            identity = {
                "mechanism_phenotype_sha256": phenotype,
                "mechanism_signature_sha256": family,
                "projection_program_id": projection["program_id"],
                "required_relation_fields": list(fields),
                "industry_id": industry, "evidence_epoch": evidence_epoch,
                "outcome_contract_sha256": outcome_contract_sha,
            }
            groups.append({
                "comparison_identity": identity,
                "comparison_identity_sha256": stable_sha256(identity),
                "entities": rows, "same_industry_calendar_risk_cells": risk_cells,
                "floor_ready_cell_count": sum(cell["declared_floor_met"] for cell in risk_cells),
            })
    partitions = Counter(
        row["partition"] for group in groups for row in group["entities"]
    )
    body = {
        "schema": STRATEGY_ACTIVE_COMPARATOR_FRONTIER_SCHEMA,
        "input_identity": {
            "cohort_plan_sha256": plan_sha,
            "projection_frontier_sha256": projection_sha,
            "coverage_chain_sha256": coverage["coverage_chain_sha256"],
            "evidence_epoch": evidence_epoch,
        },
        "relation_contract": {
            "focal_class": "P", "active_alternative_class": "Q",
            "Q_semantics": "typed_relation_to_P_only",
            "full_Q_phenotype_available": False,
            "dimensions": list(STRATEGY_PHENOTYPE_DIMENSIONS),
        },
        "outcome_contract": {
            **outcome_contract, "outcome_contract_sha256": outcome_contract_sha,
        },
        "selection_contract": {
            "outcome_used_for_selection": False,
            "allowed_states": sorted(_ACTIVE_STATES), "timing_precision": "exact_date",
            "one_index_event_per_firm": True, "washout_days": washout_days,
            "minimum_pre_periods": minimum_pre_periods,
            "minimum_post_periods": minimum_post_periods,
            "minimum_independent_focal_firms": minimum_independent_focal_firms,
            "minimum_independent_alternative_firms": minimum_independent_alternative_firms,
        },
        "comparison_groups": groups,
        "audit": {
            "comparison_group_count": len(groups),
            "partition_counts": dict(sorted(partitions.items())),
            "floor_ready_cell_count": sum(
                group["floor_ready_cell_count"] for group in groups
            ),
        },
        "next_company_facts_acquisition_entities": sorted(missing_entities),
        "selection_status": "frontier_only_no_effect_estimate",
        "causal_estimate_ran": False, "rank_authority": False,
        "law_authority": False, "capital_authority": False,
    }
    return {**body, "active_comparator_frontier_sha256": stable_sha256(body)}


def compile_workspace_strategy_active_comparator(workspace: str | Path) -> dict[str, Any]:
    root = Path(workspace).expanduser().resolve()
    cohort = root / "institutional_learning" / "strategy_cohorts"
    plan = json.loads((cohort / "latest.json").read_text(encoding="utf-8"))
    projection = json.loads((cohort / "projection-frontier.json").read_text(encoding="utf-8"))
    results = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((cohort / "results").glob("*.json"))
    ]
    historical_requests = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((root / "research_jobs" / "strategy_cohorts" / "requests").glob("*.json"))
    ]
    entities = {
        str(move["entity_id"]).upper()
        for group in plan.get("mechanism_environments") or ()
        for move in group.get("focal_moves") or ()
    } | {str(row["peer_entity_id"]).upper() for row in plan.get("requests") or ()}
    epoch = (projection.get("certificate") or {}).get("scope", {}).get("evidence_epoch")
    histories = {}
    for entity in sorted(entities):
        try:
            histories[entity] = compile_company_quality_history(
                entity_id=entity, observations_path=root / "data" / "observations.csv",
                as_of=str(epoch), min_years=2,
            )
        except (FileNotFoundError, OSError, TypeError, ValueError):
            histories[entity] = ()
    result = compile_strategy_active_comparator_frontier(
        plan, projection, results, histories, historical_requests=historical_requests,
    )
    receipt_heads = json.loads(
        (root / "data" / "source_receipt_heads.json").read_text(encoding="utf-8")
    ) if (root / "data" / "source_receipt_heads.json").is_file() else {}
    receipts = {
        str(row.get("source_id") or ""): row
        for row in receipt_heads.get("receipts") or () if isinstance(row, Mapping)
    }
    missing = list(result["next_company_facts_acquisition_entities"])
    terminal_source_gaps = [
        entity for entity in missing if f"sec_{entity.lower()}_companyfacts" in receipts
    ]
    body = {
        key: value for key, value in result.items()
        if key != "active_comparator_frontier_sha256"
    }
    body.update({
        "next_company_facts_acquisition_entities": [
            entity for entity in missing if entity not in terminal_source_gaps
        ],
        "company_facts_source_gap_entities": terminal_source_gaps,
        "company_facts_source_receipts": {
            entity: receipts[f"sec_{entity.lower()}_companyfacts"]["receipt_sha256"]
            for entity in terminal_source_gaps
        },
    })
    result = {**body, "active_comparator_frontier_sha256": stable_sha256(body)}
    destination = cohort / "active-comparator-frontier.json"
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(destination)
    return result


__all__ = [
    "STRATEGY_ACTIVE_COMPARATOR_FRONTIER_SCHEMA",
    "compile_strategy_active_comparator_frontier",
    "compile_workspace_strategy_active_comparator",
]
