"""Prospective experiment slots for exact strategy phenotypes."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable, Mapping

import yaml

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, timestamp_key
from .golden_store import GoldenStore
from .strategy_learning import (
    candidate_bound_strategy_move,
    compatible_strategy_source_request_sha256s,
    covered_strategy_source_request_sha256s,
    strategy_choice_admission_status,
    unique_current_candidates_by_entity,
)
from .strategy_event_refinement import effective_exact_implementation_event
from .strategy_measurement_contract import strategy_alpha_operating_contract


STRATEGY_ALPHA_ELIGIBILITY_SCHEMA = "jaggedthoughts-strategy-alpha-episode-eligibility-v1"
STRATEGY_ALPHA_NOMINATION_SCHEMA = "jaggedthoughts-strategy-alpha-episode-nomination-v1"
STRATEGY_ALPHA_SCHEDULE_SCHEMA = "jaggedthoughts-strategy-alpha-episode-schedule-v1"
STRATEGY_DUAL_OUTCOME_CONTRACT_SCHEMA = "jaggedthoughts-strategy-dual-outcome-contract-v1"
STRATEGY_ALPHA_OPEN_ISSUER_LIMIT = 8
STRATEGY_ALPHA_COHORT_ENROLLMENT_DAYS = 1
_LEARNING_ADMISSIBLE_SCREEN_STATUSES = {"qualified", "monitor"}
_LINEAGE_REPAIR_JOB_KINDS = {
    "jaggedthoughts_subscription_activation_research",
    "jaggedthoughts_subscription_research",
    "jaggedthoughts_strategy_frontier_research",
}


def strategy_alpha_issuance_blockers(
    episodes: Iterable[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    """Return unsettled episodes that can still enter the current tournament ABI."""

    return tuple(
        dict(row) for row in episodes
        if not row.get("settled")
        and row.get("compatibility_abi") == "dual_outcome_contract"
    )


def strategy_alpha_issuance_vetoes(
    episodes: Iterable[Mapping[str, Any]], *, proposed_entity_id: str, proposed_at: str,
    open_issuer_limit: int = STRATEGY_ALPHA_OPEN_ISSUER_LIMIT,
    enrollment_days: int = STRATEGY_ALPHA_COHORT_ENROLLMENT_DAYS,
) -> tuple[dict[str, Any], ...]:
    """Veto duplicate active issuers or a full prospective cohort."""

    active = strategy_alpha_issuance_blockers(episodes)
    entity_id = proposed_entity_id.upper()
    same_issuer = tuple(
        row for row in active if str(row.get("entity_id") or "").upper() == entity_id
    )
    if same_issuer:
        return same_issuer
    gate = strategy_alpha_cohort_gate(
        active, evaluated_at=proposed_at, open_issuer_limit=open_issuer_limit,
        enrollment_days=enrollment_days,
    )
    if not gate["admission_available"]:
        return active
    return ()


def strategy_alpha_cohort_gate(
    episodes: Iterable[Mapping[str, Any]], *, evaluated_at: str,
    open_issuer_limit: int = STRATEGY_ALPHA_OPEN_ISSUER_LIMIT,
    enrollment_days: int = STRATEGY_ALPHA_COHORT_ENROLLMENT_DAYS,
) -> dict[str, Any]:
    """Expose bounded cohort headroom without chaining return blocks forever."""

    if open_issuer_limit < 1 or enrollment_days < 1:
        raise ValueError("strategy-alpha cohort bounds must be positive")
    active = strategy_alpha_issuance_blockers(episodes)
    evaluated = canonical_timestamp(evaluated_at, "cohort evaluated_at")
    issuers = sorted({str(row.get("entity_id") or "").upper() for row in active})
    capacity = max(0, open_issuer_limit - len(issuers))
    enrollment_closes_at = None
    enrollment_open = not active
    if active:
        opened_at = min(
            canonical_timestamp(row.get("opened_at"), "cohort opened_at")
            for row in active
        )
        enrollment_closes_at = (
            timestamp_key(opened_at) + timedelta(days=enrollment_days)
        ).isoformat().replace("+00:00", "Z")
        enrollment_open = timestamp_key(evaluated) <= timestamp_key(enrollment_closes_at)
    admission_available = bool(capacity and enrollment_open)
    return {
        "open_issuer_limit": open_issuer_limit,
        "open_issuer_count": len(issuers),
        "open_issuer_ids": issuers,
        "open_issuer_capacity": capacity,
        "cohort_enrollment_days": enrollment_days,
        "cohort_enrollment_closes_at": enrollment_closes_at,
        "cohort_enrollment_open": enrollment_open,
        "admission_available": admission_available,
        "experiment_not_before": (
            max(str(row["scheduled_exit_at"]) for row in active)
            if active and not admission_available else None
        ),
    }


def strategy_alpha_cohort_policy(root: str | Path) -> dict[str, int]:
    """Read the shared scheduler/open-lock cohort bounds."""

    try:
        raw = yaml.safe_load(
            (Path(root) / "capital_cycle.yaml").read_text(encoding="utf-8")
        )
        policy = (raw or {}).get("strategy_alpha_cohort") or {}
        values = {
            "open_issuer_limit": int(
                policy.get("open_issuer_limit", STRATEGY_ALPHA_OPEN_ISSUER_LIMIT)
            ),
            "enrollment_days": int(
                policy.get("enrollment_days", STRATEGY_ALPHA_COHORT_ENROLLMENT_DAYS)
            ),
        }
    except (OSError, TypeError, ValueError, yaml.YAMLError):
        values = {
            "open_issuer_limit": STRATEGY_ALPHA_OPEN_ISSUER_LIMIT,
            "enrollment_days": STRATEGY_ALPHA_COHORT_ENROLLMENT_DAYS,
        }
    if min(values.values()) < 1:
        raise ValueError("strategy-alpha cohort policy bounds must be positive")
    return values


def compile_strategy_alpha_source_readiness(root: str | Path) -> dict[str, Any]:
    """Explain whether exact strategy evidence can enter prospective issuance."""

    workspace = Path(root).expanduser().resolve()
    library = _read(workspace / "institutional_learning" / "strategy_moves" / "latest.json")
    discovery = _read(workspace / "discovery" / "latest.json")
    record = _read(workspace / "discovery" / "latest_record.json")
    candidates, ambiguous_entities = unique_current_candidates_by_entity(
        discovery.get("candidates") or (),
    )
    leaves = record.get("candidate_leaves") if isinstance(record.get("candidate_leaves"), Mapping) else {}
    compatible: dict[str, frozenset[str]] = {}
    rows = []
    acquisition_rows = []
    latest_epoch = {
        str(move.get("entity_id") or "").upper(): max(
            canonical_timestamp(candidate.get("evidence_epoch"), "strategy move epoch")
            for candidate in library.get("moves") or ()
            if isinstance(candidate, Mapping) and str(candidate.get("entity_id") or "").upper()
            == str(move.get("entity_id") or "").upper()
        )
        for move in library.get("moves") or () if isinstance(move, Mapping)
    }
    for move in library.get("moves") or ():
        if not isinstance(move, Mapping):
            continue
        entity_id = str(move.get("entity_id") or "").upper()
        if canonical_timestamp(move.get("evidence_epoch"), "strategy move epoch") != latest_epoch.get(entity_id):
            continue
        event = effective_exact_implementation_event(move) or {}
        direct_contracts = [
            contract for contract in move.get("outcome_contracts") or ()
            if isinstance(contract, Mapping) and strategy_alpha_operating_contract(contract)
        ]
        if (
            event.get("treatment_timing_status") != "exact_adoption_event"
            or move.get("claim_status") != "supported"
        ):
            continue
        candidate = candidates.get(entity_id) or {}
        candidate_leaf = str(leaves.get(str(candidate.get("candidate_id") or "")) or "")
        if entity_id not in compatible:
            compatible[entity_id] = compatible_strategy_source_request_sha256s(
                workspace, candidate_id=str(candidate.get("candidate_id") or ""),
                candidate_leaf=candidate_leaf,
                candidate_sha256=str(candidate.get("candidate_sha256") or ""),
            ) | covered_strategy_source_request_sha256s(
                workspace, candidate_leaf=candidate_leaf,
            )
        choice_status = strategy_choice_admission_status(library, move)
        lineage_ready = candidate_bound_strategy_move(
            move, candidate_leaf=candidate_leaf,
            candidate_sha256=str(candidate.get("candidate_sha256") or ""),
            compatible_source_request_sha256s=compatible[entity_id],
        )
        gaps = []
        if not candidate:
            gaps.append(
                "current_candidate_ambiguous"
                if entity_id in ambiguous_entities else "current_candidate_missing"
            )
        if choice_status is None:
            gaps.append("typed_choice_identity_missing_or_stale")
        if not lineage_ready:
            gaps.append("current_or_compatible_business_lineage_missing")
        gaps = []
        if not direct_contracts:
            gaps.append("valuation_compatible_terminal_contract_missing")
        if not candidate:
            gaps.append(
                "current_candidate_ambiguous"
                if entity_id in ambiguous_entities else "current_candidate_missing"
            )
        if choice_status is None:
            gaps.append("typed_choice_identity_missing_or_stale")
        if not lineage_ready:
            gaps.append("current_or_compatible_business_lineage_missing")
        acquisition_row = {
            "entity_id": entity_id,
            "move_sha256": move.get("move_sha256"),
            "option_id": move.get("option_id"),
            "metric_ids": sorted({str(row.get("metric_id")) for row in direct_contracts}),
            "choice_identity_status": choice_status,
            "lineage_ready": lineage_ready,
            "gaps": gaps,
            "eligible_source": not gaps,
            "next_transition": (
                "issue_prospective_episode" if not gaps
                else "restore_current_candidate_identity" if not candidate
                else "refresh_current_candidate_strategy_frontier"
                if choice_status is None or not lineage_ready
                else "acquire_valuation_compatible_terminal_contract"
                if not direct_contracts
                else "resolve_source_readiness_gap"
            ),
        }
        acquisition_rows.append(acquisition_row)
        if direct_contracts:
            rows.append(acquisition_row)
    gap_counts = Counter(gap for row in acquisition_rows for gap in row["gaps"])
    eligible_count = sum(row["eligible_source"] for row in rows)
    repair_entities = {
        row["entity_id"] for row in acquisition_rows
        if "current_or_compatible_business_lineage_missing" in row["gaps"]
        and not any(gap in row["gaps"] for gap in (
            "current_candidate_missing", "current_candidate_ambiguous",
        ))
    }
    queued_repairs = []
    queued_acquisitions = []
    queued_event_refinements = []
    try:
        connection = sqlite3.connect(workspace / "state" / "research_jobs.sqlite3")
        connection.row_factory = sqlite3.Row
        for queue_row in connection.execute(
            "SELECT work_id, kind, priority, status, payload_json FROM work_items "
            "WHERE status IN ('queued', 'claimed') ORDER BY priority DESC, created_at ASC"
        ):
            payload = json.loads(str(queue_row["payload_json"] or "{}"))
            entity_id = str(payload.get("entity_id") or "").upper()
            if str(queue_row["kind"]) == "jaggedthoughts_strategy_measurement_research":
                queued_acquisitions.append({
                    "work_id": str(queue_row["work_id"]),
                    "kind": str(queue_row["kind"]),
                    "priority": int(queue_row["priority"]),
                    "status": str(queue_row["status"]),
                    "entity_id": entity_id,
                    "option_id": str(payload.get("option_id") or ""),
                })
                continue
            if str(queue_row["kind"]) == "jaggedthoughts_strategy_event_refinement_research":
                queued_event_refinements.append({
                    "work_id": str(queue_row["work_id"]),
                    "priority": int(queue_row["priority"]),
                    "status": str(queue_row["status"]),
                    "entity_id": entity_id,
                })
                continue
            if (
                entity_id not in repair_entities
                or str(queue_row["kind"]) not in _LINEAGE_REPAIR_JOB_KINDS
            ):
                continue
            queued_repairs.append({
                "work_id": str(queue_row["work_id"]),
                "kind": str(queue_row["kind"]),
                "priority": int(queue_row["priority"]),
                "status": str(queue_row["status"]),
                "entity_id": entity_id,
            })
    except (OSError, sqlite3.Error, TypeError, ValueError):
        queued_repairs = []
        queued_acquisitions = []
        queued_event_refinements = []
    finally:
        if "connection" in locals():
            connection.close()
    service = _read(workspace / "state" / "research_agent_service.json")
    next_dispatch_at = None
    if service.get("last_action") == "daily_dispatch_budget_exhausted":
        next_dispatch_at = (
            datetime.now(timezone.utc) + timedelta(days=1)
        ).replace(hour=0, minute=0, second=0, microsecond=0).isoformat().replace(
            "+00:00", "Z"
        )
    body = {
        "schema": "jaggedthoughts-strategy-alpha-source-readiness-v1",
        "exact_direct_source_count": len(rows),
        "exact_event_source_count": len(acquisition_rows),
        "exact_event_issuer_count": len({row["entity_id"] for row in acquisition_rows}),
        "lineage_repair_entity_ids": sorted(repair_entities),
        "eligible_source_count": eligible_count,
        "gap_counts": dict(sorted(gap_counts.items())),
        "rows": rows,
        "acquisition_rows": acquisition_rows,
        "activation": {
            "owner": "subscription_research_service",
            "service_status": service.get("status"),
            "last_action": service.get("last_action"),
            "next_dispatch_at": next_dispatch_at,
            "queued_acquisitions": queued_acquisitions,
            "queued_event_refinements": queued_event_refinements,
            "queued_repairs": queued_repairs,
        },
        "status": (
            "ready_for_prospective_issuance" if eligible_count
            else "awaiting_candidate_bound_strategy_frontier" if rows
            else "awaiting_exact_measurable_strategy_event"
        ),
        "next_activation": (
            "Schedule the highest-information exact strategy experiment."
            if eligible_count else
            "Refresh the strategy dossier and frontier through the subscription worker."
            if rows else
            "Acquire an exact strategy event with a valuation-compatible operating hurdle."
        ),
        "capital_authority": False,
    }
    return _hashed(body, "readiness_sha256")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _hashed(payload: Mapping[str, Any], field: str) -> dict[str, Any]:
    body = dict(payload)
    return {**body, field: stable_sha256(body)}


def _valid_hash(payload: Mapping[str, Any], field: str) -> bool:
    claimed = str(payload.get(field) or "")
    return bool(claimed) and claimed == stable_sha256({
        key: value for key, value in payload.items() if key != field
    })


def _gap(code: str, **context: Any) -> dict[str, Any]:
    return _hashed({"code": code, **context}, "gap_sha256")


def _store(root: Path) -> tuple[GoldenStore | None, str]:
    try:
        raw = yaml.safe_load((root / "workspace.yaml").read_text(encoding="utf-8"))
        config = dict(raw) if isinstance(raw, Mapping) else {}
        path = root / str(config.get("golden_store") or "state/golden_store.sqlite3")
        return (GoldenStore(path) if path.is_file() else None), str(
            config.get("owner") or "operator-paper-book"
        )
    except (OSError, TypeError, ValueError, yaml.YAMLError):
        return None, "operator-paper-book"


def _exact_phenotypes(
    root: Path, library: Mapping[str, Any], *, evaluated_at: str,
    candidates: Mapping[str, Mapping[str, Any]], leaves: Mapping[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    events: dict[tuple[str, str], list[dict[str, Any]]] = {}
    compatible_requests = {
        entity_id: compatible_strategy_source_request_sha256s(
            root,
            candidate_id=str(candidate.get("candidate_id") or ""),
            candidate_leaf=str(leaves.get(str(candidate.get("candidate_id") or "")) or ""),
            candidate_sha256=str(candidate.get("candidate_sha256") or ""),
        ) | covered_strategy_source_request_sha256s(
            root, candidate_leaf=str(leaves.get(str(candidate.get("candidate_id") or "")) or ""),
        )
        for entity_id, candidate in candidates.items()
    }
    for move in library.get("moves") or ():
        if not isinstance(move, Mapping):
            continue
        entity_id = str(move.get("entity_id") or "").upper()
        candidate = candidates.get(entity_id) or {}
        candidate_leaf = str(leaves.get(str(candidate.get("candidate_id") or "")) or "")
        if timestamp_key(canonical_timestamp(
            move.get("evidence_epoch"), "move.evidence_epoch",
        )) > timestamp_key(evaluated_at):
            continue
        if not candidate_bound_strategy_move(
            move,
            candidate_leaf=candidate_leaf,
            candidate_sha256=str(candidate.get("candidate_sha256") or ""),
            compatible_source_request_sha256s=compatible_requests.get(entity_id, ()),
        ):
            continue
        event = effective_exact_implementation_event(move)
        if (
            not isinstance(event, Mapping)
            or event.get("treatment_timing_status") != "exact_adoption_event"
            or not _valid_hash(event, "implementation_event_sha256")
            or not event.get("source_refs")
        ):
            continue
        choice_identity = str(move.get("strategy_choice_identity_sha256") or "")
        choice_status = strategy_choice_admission_status(
            library, move, as_of=evaluated_at,
        )
        if not choice_identity or choice_status is None:
            continue
        try:
            available_at = canonical_timestamp(event.get("available_at"), "event.available_at")
        except ValueError:
            continue
        if timestamp_key(available_at) > timestamp_key(evaluated_at):
            continue
        key = (
            entity_id,
            str(move.get("mechanism_phenotype_sha256") or ""),
        )
        events.setdefault(key, []).append({
            "move_sha256": str(move.get("move_sha256") or ""),
            "implementation_event_sha256": str(event.get("implementation_event_sha256") or ""),
            "candidate_leaf": candidate_leaf,
            "candidate_sha256": str(candidate.get("candidate_sha256") or ""),
            "candidate_epoch_relation": (
                "exact_market_epoch"
                if move.get("candidate_leaf") == candidate_leaf
                and move.get("candidate_sha256") == candidate.get("candidate_sha256")
                else "qualitative_business_basis_compatible"
            ),
            "strategy_choice_identity_sha256": choice_identity,
            "choice_identity_status": choice_status,
            "available_at": available_at,
            "source_refs": sorted(str(value) for value in event.get("source_refs") or ()),
            "strategy_program_attribution": dict(
                move.get("strategy_program_attribution") or {
                    "strategy_frontier_sha256": move.get("strategy_frontier_sha256"),
                    "frontier_program_ids": [], "local_peak_program_ids": [],
                    "scope_closed": False, "decision_closed": False,
                    "status": "legacy_option_event_without_program_lineage",
                    "program_adoption_evidence_required": True,
                    "recursive_frontier_credit_eligible": False,
                }
            ),
            "outcome_contracts": [
                dict(contract) for contract in move.get("outcome_contracts") or ()
                if isinstance(contract, Mapping) and contract.get("contract_sha256")
            ],
        })
    by_entity: dict[str, list[dict[str, Any]]] = {}
    for phenotype in library.get("mechanism_phenotypes") or ():
        if not isinstance(phenotype, Mapping) or int(phenotype.get("exact_adoption_count") or 0) <= 0:
            continue
        phenotype_sha = str(phenotype.get("mechanism_phenotype_sha256") or "")
        for raw_entity in phenotype.get("entity_ids") or ():
            entity_id = str(raw_entity).upper()
            matching = events.get((entity_id, phenotype_sha), [])
            if matching:
                by_entity.setdefault(entity_id, []).append({
                    "mechanism_phenotype_sha256": phenotype_sha,
                    "implementation_events": matching,
                })
    return by_entity


def _security_control_contract(
    candidate: Mapping[str, Any], *, benchmark_id: str, frozen_at: str,
) -> dict[str, Any]:
    """Freeze the current sourced factor vector, or the declared benchmark alone."""

    beta_receipt = candidate.get("beta_receipt")
    analysis = (
        beta_receipt.get("analysis")
        if isinstance(beta_receipt, Mapping) and isinstance(beta_receipt.get("analysis"), Mapping)
        else {}
    )
    factors = list(analysis.get("factors") or ())
    betas = dict((analysis.get("coefficients") or {}).get("betas") or {})
    analysis_valid = (
        beta_receipt.get("status") == "estimated"
        if isinstance(beta_receipt, Mapping) else False
    ) and _valid_hash(analysis, "analysis_sha256")
    if analysis_valid:
        analysis_available = canonical_timestamp(
            analysis.get("available_at"), "factor analysis available_at",
        )
        analysis_valid = timestamp_key(analysis_available) <= timestamp_key(frozen_at)
    factor_ids = {str(row.get("factor_id") or "") for row in factors if isinstance(row, Mapping)}
    if analysis_valid and factor_ids and factor_ids == set(betas):
        body = {
            "kind": "frozen_factor_beta_vector",
            "benchmark_entity_id": benchmark_id,
            "factor_analysis_sha256": analysis["analysis_sha256"],
            "factor_analysis_available_at": analysis_available,
            "factors": sorted((dict(row) for row in factors), key=lambda row: row["factor_id"]),
            "betas": {key: float(betas[key]) for key in sorted(betas)},
            "factor_return_formula": "long total price return minus short total price return",
            "factor_controlled_return_formula": "entity total price return minus frozen beta dot realized factor returns",
            "benchmark_active_return_formula": "entity total price return minus benchmark total price return",
            "frozen_at": frozen_at,
            "source_refs": sorted(str(value) for value in analysis.get("source_refs") or ()),
        }
    else:
        body = {
            "kind": "declared_benchmark_only",
            "benchmark_entity_id": benchmark_id,
            "benchmark_active_return_formula": "entity total price return minus benchmark total price return",
            "factor_controlled_return_formula": None,
            "frozen_at": frozen_at,
            "source_refs": [],
        }
    return _hashed(body, "security_control_sha256")


def _dual_outcome_contract(
    *, entity_id: str, candidate_leaf: str, candidate_sha256: str,
    phenotype_sha256: str, event: Mapping[str, Any],
    operating_contract: Mapping[str, Any], security_horizon_days: int,
    security_control: Mapping[str, Any], frozen_at: str,
) -> dict[str, Any]:
    episode_key = stable_sha256({
        "entity_id": entity_id,
        "candidate_leaf": candidate_leaf,
        "candidate_sha256": candidate_sha256,
        "move_sha256": str(event["move_sha256"]),
        "strategy_choice_identity_sha256": str(
            event["strategy_choice_identity_sha256"]
        ),
        "mechanism_phenotype_sha256": phenotype_sha256,
        "implementation_event_sha256": str(event["implementation_event_sha256"]),
        "operating_contract_sha256": str(operating_contract["contract_sha256"]),
        "security_horizon_days": security_horizon_days,
        "benchmark_entity_id": security_control["benchmark_entity_id"],
    })
    body = {
        "schema": STRATEGY_DUAL_OUTCOME_CONTRACT_SCHEMA,
        "dual_outcome_episode_key_sha256": episode_key,
        "entity_id": entity_id,
        "candidate_leaf": candidate_leaf,
        "candidate_sha256": candidate_sha256,
        "move_sha256": str(event["move_sha256"]),
        "strategy_choice_identity_sha256": str(
            event["strategy_choice_identity_sha256"]
        ),
        "mechanism_phenotype_sha256": phenotype_sha256,
        "implementation_event_sha256": str(event["implementation_event_sha256"]),
        "strategy_program_attribution": dict(event["strategy_program_attribution"]),
        "implementation_available_at": str(event["available_at"]),
        "operating_outcome": {
            key: operating_contract.get(key) for key in (
                "contract_sha256", "metric_id", "unit", "direction", "minimum_effect",
                "comparator", "measurement_start_at", "due_at", "outcome_role",
            )
        },
        "security_outcome": {
            "horizon_days": security_horizon_days,
            "control": dict(security_control),
            "settlement_runtime": "closed_book",
        },
        "source_refs": sorted({
            *(str(value) for value in event.get("source_refs") or ()),
            *(str(value) for value in operating_contract.get("evidence_refs") or ()),
            *(str(value) for value in security_control.get("source_refs") or ()),
        }),
        "frozen_at": frozen_at,
        "outcomes_are_distinct": True,
        "tested_strategy_object": "exact_option_phenotype",
        "permitted_downstream_effect": "promotion_gated_research_priority_only",
        "direct_research_priority_adjustment": 0.0,
        "portfolio_weight": 0.0,
        "capital_authority": False,
    }
    return _hashed(body, "dual_outcome_contract_sha256")


def _preopen_family_identity(dual: Mapping[str, Any]) -> str:
    operating = dict(dual.get("operating_outcome") or {})
    security = dict(dual.get("security_outcome") or {})
    control = dict(security.get("control") or {})
    return stable_sha256({
        "schema": "jaggedthoughts-strategy-alpha-preopen-family-v1",
        "mechanism_phenotype_sha256": dual.get("mechanism_phenotype_sha256"),
        "horizon_days": security.get("horizon_days"),
        "settlement_runtime": security.get("settlement_runtime"),
        "benchmark_entity_id": control.get("benchmark_entity_id"),
        "factor_basis": sorted(
            str(row.get("factor_id") or "")
            for row in control.get("factors") or () if isinstance(row, Mapping)
        ),
        "operating_hurdle": {
            key: operating.get(key) for key in (
                "metric_id", "unit", "direction", "comparator", "outcome_role",
            )
        },
    })


def compile_strategy_alpha_episode_history(root: Path) -> dict[str, Any]:
    """Compile validated strategy-alpha run identities and settlement state."""

    episodes = []
    for path in sorted((root / "closed_book" / "runs").glob("*.json")):
        run = _read(path)
        if (
            run.get("schema") != "jaggedthoughts-closed-book-forecast-run-v1"
            or path.stem != str(run.get("run_id") or "")
            or not _valid_hash(run, "run_sha256")
        ):
            continue
        packet = dict(run.get("evidence_packet") or {})
        if (
            packet.get("schema") != "jaggedthoughts-closed-book-evidence-packet-v1"
            or not _valid_hash(packet, "packet_sha256")
        ):
            continue
        nomination = dict((packet.get("discovery_summary") or {}).get(
            "strategy_experiment_nomination"
        ) or {})
        contract = dict(nomination.get("dual_outcome_contract") or {})
        subject = dict(packet.get("subject") or {})
        entity = dict(packet.get("entity") or {})
        security = dict(contract.get("security_outcome") or {})
        try:
            nominated_at = canonical_timestamp(
                nomination["nominated_at"], "nomination.nominated_at",
            )
            opened_at = canonical_timestamp(run["opened_at"], "run.opened_at")
        except (KeyError, TypeError, ValueError):
            continue
        if (
            nomination.get("schema") != STRATEGY_ALPHA_NOMINATION_SCHEMA
            or not _valid_hash(nomination, "nomination_sha256")
            or timestamp_key(nominated_at) > timestamp_key(opened_at)
            or any(str(left or "") != str(right or "") for left, right in (
                (nomination.get("entity_id"), entity.get("entity_id")),
                (nomination.get("candidate_id"), subject.get("subject_id")),
                (nomination.get("candidate_leaf"), subject.get("candidate_leaf")),
                (nomination.get("candidate_sha256"), subject.get("subject_sha256")),
                (nomination.get("horizon_days"), packet.get("horizon_days")),
                (nomination.get("horizon_days"), run.get("horizon_days")),
            ))
        ):
            continue
        if contract:
            identity = str(contract.get("dual_outcome_episode_key_sha256") or "")
            phenotype_sha = str(contract.get("mechanism_phenotype_sha256") or "")
            identity_fields = {
                "entity_id": str(contract.get("entity_id") or ""),
                "move_sha256": str(contract.get("move_sha256") or ""),
                "mechanism_phenotype_sha256": phenotype_sha,
                "implementation_event_sha256": str(
                    contract.get("implementation_event_sha256") or ""
                ),
                "operating_contract_sha256": str(
                    (contract.get("operating_outcome") or {}).get(
                        "contract_sha256"
                    ) or ""
                ),
                "security_horizon_days": int(security.get("horizon_days") or 0),
                "benchmark_entity_id": str(
                    (security.get("control") or {}).get("benchmark_entity_id") or ""
                ),
            }
            current_identity = all(
                contract.get(field) is not None for field in (
                    "candidate_leaf", "candidate_sha256",
                    "strategy_choice_identity_sha256",
                )
            )
            if current_identity:
                identity_fields.update({
                    "candidate_leaf": str(contract.get("candidate_leaf") or ""),
                    "candidate_sha256": str(contract.get("candidate_sha256") or ""),
                    "strategy_choice_identity_sha256": str(
                        contract.get("strategy_choice_identity_sha256") or ""
                    ),
                })
            if (
                contract.get("schema") != STRATEGY_DUAL_OUTCOME_CONTRACT_SCHEMA
                or not _valid_hash(contract, "dual_outcome_contract_sha256")
                or len(identity) != 64 or len(phenotype_sha) != 64
                or stable_sha256(identity_fields) != identity
                or str(nomination.get("entity_id") or "")
                != str(contract.get("entity_id") or "")
                or str(nomination.get("horizon_days") or "")
                != str(security.get("horizon_days") or "")
                or (
                    current_identity and any(
                        str(contract.get(field) or "")
                        != str(nomination.get(field) or "")
                        for field in ("candidate_leaf", "candidate_sha256")
                    )
                )
            ):
                continue
            compatibility_abi = (
                "dual_outcome_contract" if current_identity
                else "legacy_dual_outcome_contract"
            )
            preopen_family_sha = _preopen_family_identity(contract)
        else:
            phenotypes = sorted({
                str(value) for value in nomination.get(
                    "mechanism_phenotype_sha256s"
                ) or () if len(str(value)) == 64
            })
            if len(phenotypes) != 1:
                continue
            phenotype_sha = phenotypes[0]
            identity = stable_sha256({
                "legacy_strategy_nomination_sha256": nomination["nomination_sha256"],
            })
            compatibility_abi = "legacy_nomination"
            preopen_family_sha = None
        settlement = _read(root / "closed_book" / "settlements" / f"{run['run_id']}.json")
        settled = (
            settlement.get("schema") == "jaggedthoughts-closed-book-settlement-v1"
            and settlement.get("run_id") == run.get("run_id")
            and settlement.get("run_sha256") == run.get("run_sha256")
            and _valid_hash(settlement, "settlement_sha256")
        )
        window_envelope = _read(
            root / "closed_book" / "return_windows" / f"{run['run_id']}.json"
        )
        binding = dict(window_envelope.get("binding") or {})
        try:
            scheduled_exit_at = canonical_timestamp(
                (
                    binding.get("scheduled_exit_at")
                    if binding.get("schema")
                    == "jaggedthoughts-prospective-return-window-binding-v1"
                    and _valid_hash(binding, "binding_sha256")
                    else None
                ) or packet.get("end_at") or run.get("end_at"),
                "strategy-alpha scheduled exit",
            )
        except ValueError:
            continue
        episodes.append({
            "run_id": str(run["run_id"]),
            "dual_outcome_episode_key_sha256": identity,
            "entity_id": str(nomination["entity_id"]).upper(),
            "mechanism_phenotype_sha256": phenotype_sha,
            "compatibility_abi": compatibility_abi,
            "preopen_family_sha256": preopen_family_sha,
            "opened_at": opened_at,
            "scheduled_exit_at": scheduled_exit_at,
            "settled": settled,
            "settlement_sha256": (
                settlement.get("settlement_sha256") if settled else None
            ),
        })
    blockers = strategy_alpha_issuance_blockers(episodes)
    body = {
        "schema": "jaggedthoughts-strategy-alpha-episode-history-v1",
        "episodes": sorted(
            episodes, key=lambda row: (row["opened_at"], row["run_id"]),
        ),
        "issuance_blocking_run_ids": sorted(row["run_id"] for row in blockers),
        "nonblocking_legacy_unsettled_run_ids": sorted(
            row["run_id"] for row in episodes
            if not row["settled"]
            and row["compatibility_abi"] != "dual_outcome_contract"
        ),
        "capital_authority": False,
    }
    return _hashed(body, "history_sha256")


def _opened_dual_contracts(root: Path) -> set[str]:
    return {
        str(row["dual_outcome_episode_key_sha256"])
        for row in compile_strategy_alpha_episode_history(root)["episodes"]
    }


def _recent_deferred_nominations(
    root: Path, *, evaluated_at: str,
) -> dict[tuple[str, int, str, str], dict[str, Any]]:
    """Reuse one failed pre-open request for 24 hours so transport repair is resumable."""
    cycle = _read(root / "capital_cycles" / "latest.json")
    cutoff = timestamp_key(evaluated_at) - timedelta(hours=24)
    rows = {}
    for deferred in cycle.get("strategy_alpha_preopen_actions") or ():
        if not isinstance(deferred, Mapping) or deferred.get("status") != "deferred_preopen_action":
            continue
        nomination = deferred.get("strategy_experiment_nomination")
        if not isinstance(nomination, Mapping) or not _valid_hash(nomination, "nomination_sha256"):
            continue
        nominated_at = canonical_timestamp(nomination.get("nominated_at"), "nomination.nominated_at")
        if not cutoff <= timestamp_key(nominated_at) <= timestamp_key(evaluated_at):
            continue
        dual = dict(nomination.get("dual_outcome_contract") or {})
        key = (
            str(nomination.get("entity_id") or "").upper(),
            int(nomination.get("horizon_days") or 0),
            str(nomination.get("candidate_leaf") or ""),
            str(dual.get("dual_outcome_episode_key_sha256") or ""),
        )
        if all(key):
            rows[key] = dict(nomination)
    return rows


def _matched_security_horizon(
    operating_contract: Mapping[str, Any], windows: Iterable[Mapping[str, Any]],
) -> int:
    """Select one declared security horizon for an operating contract."""

    choices = sorted({int(row["horizon_days"]) for row in windows})
    if not choices:
        raise ValueError("strategy-alpha policy requires a security horizon")
    operating_horizon = operating_contract.get("horizon_days")
    if operating_horizon is None:
        start = timestamp_key(canonical_timestamp(
            operating_contract.get("measurement_start_at"),
            "operating measurement_start_at",
        ))
        due = timestamp_key(canonical_timestamp(
            operating_contract.get("due_at"), "operating due_at",
        ))
        operating_horizon = max(1, int(round((due - start).total_seconds() / 86400)))
    target = int(operating_horizon)
    return min(choices, key=lambda value: (abs(value - target), value))


def _candidate_eligibility(
    root: Path,
    *,
    candidate: Mapping[str, Any] | None,
    candidate_leaf: str,
    entity_id: str,
    phenotypes: list[dict[str, Any]],
    evaluated_at: str,
    store: GoldenStore | None,
    owner: str,
) -> dict[str, Any]:
    gaps = []
    candidate = dict(candidate or {})
    if not candidate:
        gaps.append(_gap("discovery_candidate_missing", entity_id=entity_id))
    elif candidate.get("entity_kind") != "public_equity":
        gaps.append(_gap("candidate_not_public_equity", entity_id=entity_id))
    if candidate and candidate.get("screen_status") not in _LEARNING_ADMISSIBLE_SCREEN_STATUSES:
        gaps.append(_gap(
            "candidate_status_not_learning_admissible", entity_id=entity_id,
            screen_status=candidate.get("screen_status"),
        ))
    if candidate and not _valid_hash(candidate, "candidate_sha256"):
        gaps.append(_gap("candidate_hash_invalid", entity_id=entity_id))
    try:
        if candidate and timestamp_key(canonical_timestamp(candidate.get("as_of"), "candidate.as_of")) > timestamp_key(evaluated_at):
            gaps.append(_gap("candidate_post_issue", entity_id=entity_id))
    except ValueError:
        gaps.append(_gap("candidate_timestamp_invalid", entity_id=entity_id))
    if not candidate_leaf:
        gaps.append(_gap("candidate_leaf_missing", entity_id=entity_id))
    elif store is None:
        gaps.append(_gap("golden_store_unavailable", entity_id=entity_id))
    else:
        try:
            leaf = store.get_leaf(candidate_leaf)
            if (
                leaf.get("owner") != owner
                or leaf.get("object_kind") != "discovery_candidate"
                or str(leaf.get("object_id") or "") != str(candidate.get("candidate_id") or "")
                or str(leaf.get("epoch") or "") != str(candidate.get("candidate_sha256") or "")
            ):
                gaps.append(_gap("candidate_leaf_identity_mismatch", entity_id=entity_id))
        except KeyError:
            gaps.append(_gap("candidate_leaf_not_in_golden_store", entity_id=entity_id))
    quality = _read(root / "quality" / f"{entity_id.lower()}.json")
    if not quality:
        gaps.append(_gap("company_quality_missing", entity_id=entity_id))
    elif str(quality.get("quality_report_sha256") or "") != str(
        candidate.get("quality_report_sha256") or ""
    ):
        gaps.append(_gap(
            "candidate_quality_epoch_mismatch",
            entity_id=entity_id,
            candidate_quality_report_sha256=candidate.get("quality_report_sha256"),
            current_quality_report_sha256=quality.get("quality_report_sha256"),
        ))
    if not phenotypes:
        gaps.append(_gap("exact_phenotype_missing", entity_id=entity_id))
    elif not any(
        any(
            isinstance(contract, Mapping) and strategy_alpha_operating_contract(contract)
            for contract in event.get("outcome_contracts") or ()
        )
        for phenotype in phenotypes for event in phenotype.get("implementation_events") or ()
    ):
        gaps.append(_gap("declared_operating_outcome_missing", entity_id=entity_id))
    body = {
        "schema": STRATEGY_ALPHA_ELIGIBILITY_SCHEMA,
        "entity_id": entity_id,
        "candidate_id": candidate.get("candidate_id"),
        "candidate_sha256": candidate.get("candidate_sha256"),
        "candidate_leaf": candidate_leaf or None,
        "discovery_rank": candidate.get("rank"),
        "screen_status": candidate.get("screen_status"),
        "strategy_learning_population_eligible": (
            candidate.get("screen_status") in _LEARNING_ADMISSIBLE_SCREEN_STATUSES
        ),
        "ordinary_discovery_path_eligible": candidate.get("screen_status") == "qualified",
        "capital_activation_eligible": candidate.get("screen_status") == "qualified",
        "exact_phenotype_sha256s": sorted(
            row["mechanism_phenotype_sha256"] for row in phenotypes
        ),
        "eligible": not gaps,
        "gaps": sorted(gaps, key=lambda row: row["code"]),
        "evaluated_at": evaluated_at,
        "rank_changed": False,
        "expected_return_rank_used": False,
        "portfolio_weight": 0.0,
        "capital_authority": False,
    }
    return _hashed(body, "eligibility_sha256")


def schedule_strategy_alpha_prospective_episodes(
    root: Path,
    *,
    base_windows: Iterable[Mapping[str, Any]],
    policy: Mapping[str, Any],
    budget: int,
    evaluated_at: str | None = None,
) -> dict[str, Any]:
    """Reserve at most one zero-weight exact-phenotype experiment slot."""

    if budget < 0:
        raise ValueError("strategy-alpha forecast budget cannot be negative")
    evaluation_at = canonical_timestamp(evaluated_at or _now(), "evaluated_at")
    discovery = _read(root / "discovery" / "latest.json")
    record = _read(root / "discovery" / "latest_record.json")
    library = _read(root / "institutional_learning" / "strategy_moves" / "latest.json")
    global_gaps = []
    if discovery.get("schema") != "jaggedthoughts-discovery-run-v1" or not _valid_hash(discovery, "run_sha256"):
        global_gaps.append(_gap("discovery_run_missing_or_invalid"))
    if library.get("schema") != "jaggedthoughts-strategy-move-library-v1" or not _valid_hash(library, "library_sha256"):
        global_gaps.append(_gap("strategy_move_library_missing_or_invalid"))
    candidates, ambiguous_entities = unique_current_candidates_by_entity(
        discovery.get("candidates") or (),
    )
    global_gaps.extend(
        _gap("discovery_entity_candidate_ambiguous", entity_id=entity_id)
        for entity_id in sorted(ambiguous_entities)
    )
    leaves = record.get("candidate_leaves") if isinstance(record.get("candidate_leaves"), Mapping) else {}
    exact = _exact_phenotypes(
        root, library, evaluated_at=evaluation_at, candidates=candidates, leaves=leaves,
    ) if not global_gaps else {}
    store, owner = _store(root)
    eligibility = [
        _candidate_eligibility(
            root,
            candidate=candidates.get(entity_id),
            candidate_leaf=str(leaves.get(str((candidates.get(entity_id) or {}).get("candidate_id") or "")) or ""),
            entity_id=entity_id,
            phenotypes=phenotypes,
            evaluated_at=evaluation_at,
            store=store,
            owner=owner,
        )
        for entity_id, phenotypes in sorted(exact.items())
    ] if not global_gaps else []
    eligible_by_entity = {row["entity_id"]: row for row in eligibility if row["eligible"]}
    episode_history = compile_strategy_alpha_episode_history(root)
    history_rows = list(episode_history["episodes"])
    opened_dual_contracts = {
        str(row["dual_outcome_episode_key_sha256"]) for row in history_rows
    }
    unsettled_history = list(strategy_alpha_issuance_blockers(history_rows))
    cohort_gate = strategy_alpha_cohort_gate(
        unsettled_history, evaluated_at=evaluation_at,
        **strategy_alpha_cohort_policy(root),
    )
    active_issuer_ids = set(cohort_gate["open_issuer_ids"])
    deferred_nominations = _recent_deferred_nominations(
        root, evaluated_at=evaluation_at,
    )
    base = [dict(row) for row in base_windows]
    base_keys = {(str(row.get("entity_id") or "").upper(), int(row.get("horizon_days") or 0)) for row in base}
    nominations = []
    for entity_id, row in eligible_by_entity.items():
        candidate = candidates[entity_id]
        phenotypes = exact[entity_id]
        benchmark_id = str(policy.get("discovery_benchmark_id") or "SPY").upper()
        security_control = _security_control_contract(
            candidate, benchmark_id=benchmark_id, frozen_at=evaluation_at,
        )
        for window in policy.get("forecast_windows") or ():
            horizon = int(window["horizon_days"])
            key = (entity_id, horizon)
            if key in base_keys:
                continue
            for phenotype in phenotypes:
                for event in phenotype["implementation_events"]:
                    for operating_contract in event["outcome_contracts"]:
                        if not strategy_alpha_operating_contract(operating_contract):
                            continue
                        if horizon != _matched_security_horizon(
                            operating_contract, policy.get("forecast_windows") or (),
                        ):
                            continue
                        dual_contract = _dual_outcome_contract(
                            entity_id=entity_id,
                            candidate_leaf=str(row["candidate_leaf"]),
                            candidate_sha256=str(candidate["candidate_sha256"]),
                            phenotype_sha256=phenotype["mechanism_phenotype_sha256"],
                            event=event,
                            operating_contract=operating_contract,
                            security_horizon_days=horizon,
                            security_control=security_control,
                            frozen_at=evaluation_at,
                        )
                        if dual_contract["dual_outcome_episode_key_sha256"] in opened_dual_contracts:
                            continue
                        deferred_key = (
                            entity_id, horizon, str(row["candidate_leaf"]),
                            str(dual_contract["dual_outcome_episode_key_sha256"]),
                        )
                        prior_nomination = deferred_nominations.get(deferred_key)
                        nomination_body = {
                            "schema": STRATEGY_ALPHA_NOMINATION_SCHEMA,
                            "entity_id": entity_id,
                            "candidate_id": candidate["candidate_id"],
                            "candidate_sha256": candidate["candidate_sha256"],
                            "candidate_leaf": row["candidate_leaf"],
                            "discovery_rank": int(candidate.get("rank") or 10**9),
                            "screen_status": candidate.get("screen_status"),
                            "horizon_days": horizon,
                            "mechanism_phenotype_sha256s": [
                                phenotype["mechanism_phenotype_sha256"]
                            ],
                            "implementation_event_sha256s": [
                                event["implementation_event_sha256"]
                            ],
                            "dual_outcome_contract": dual_contract,
                            "source_refs": dual_contract["source_refs"],
                            "nominated_at": evaluation_at,
                            "selection_basis": "dedicated_exact_phenotype_learning_slot",
                            "rank_changed": False,
                            "expected_return_rank_used": False,
                            "portfolio_weight": 0.0,
                            "capital_authority": False,
                        }
                        nomination = (
                            prior_nomination
                            if prior_nomination is not None
                            and prior_nomination.get("candidate_sha256") == candidate["candidate_sha256"]
                            else _hashed(nomination_body, "nomination_sha256")
                        )
                        nominations.append({
                            "subject_kind": "strategy_phenotype_experiment",
                            "decision_id": None,
                            "candidate_id": candidate["candidate_id"],
                            "candidate_leaf": row["candidate_leaf"],
                            "entity_id": entity_id,
                            "profile_stage": "strategy_phenotype_experiment",
                            "rank": candidate.get("rank"),
                            "horizon_days": horizon,
                            "cadence_days": int(window["cadence_days"]),
                            "prior_opened_at": None,
                            "strategy_experiment_nomination": nomination,
                            "portfolio_weight": 0.0,
                        })
    issuer_count = Counter(str(row["entity_id"]) for row in history_rows)
    family_issuers: dict[str, set[str]] = {}
    for row in history_rows:
        if row.get("compatibility_abi") != "dual_outcome_contract":
            continue
        family_issuers.setdefault(
            str(row["preopen_family_sha256"]), set(),
        ).add(str(row["entity_id"]))
    nominations.sort(key=lambda row: (
        str(row["entity_id"]) in family_issuers.get(
            _preopen_family_identity(
                row["strategy_experiment_nomination"]["dual_outcome_contract"]
            ), set(),
        ),
        -len(family_issuers.get(
            _preopen_family_identity(
                row["strategy_experiment_nomination"]["dual_outcome_contract"]
            ), set(),
        )),
        issuer_count[str(row["entity_id"])],
        int(row.get("rank") or 10**9), int(row["horizon_days"]),
        str(row["entity_id"]),
        str(row["strategy_experiment_nomination"]["dual_outcome_contract"][
            "dual_outcome_contract_sha256"
        ]),
    ))
    nominations = [
        row for row in nominations
        if str(row["entity_id"]).upper() not in active_issuer_ids
    ]
    experiment_slots = min(
        1, int(cohort_gate["admission_available"]), budget, len(nominations),
    )
    base_slots = max(0, budget - experiment_slots)
    scheduled = base[:base_slots] + nominations[:experiment_slots]
    body = {
        "schema": STRATEGY_ALPHA_SCHEDULE_SCHEMA,
        "evaluated_at": evaluation_at,
        "budget": budget,
        "experiment_slot_limit": 1,
        **cohort_gate,
        "experiment_issuance_status": (
            "awaiting_strategy_alpha_cohort_capacity"
            if not cohort_gate["admission_available"] else
            "cohort_capacity_available" if nominations else
            "awaiting_eligible_strategy_source"
        ),
        "strategy_alpha_episode_history_sha256": episode_history["history_sha256"],
        "admission_scope": "current_qualified_or_monitor_public_equity_candidates",
        "scheduled_windows": scheduled,
        "deferred_base_windows": base[base_slots:],
        "deferred_experiment_windows": nominations[experiment_slots:],
        "eligibility": eligibility,
        "global_gaps": global_gaps,
        "rank_changed": False,
        "expected_return_rank_used": False,
        "portfolio_weight_granted": False,
        "capital_authority": False,
    }
    return _hashed(body, "schedule_sha256")


__all__ = [
    "STRATEGY_ALPHA_ELIGIBILITY_SCHEMA",
    "STRATEGY_ALPHA_NOMINATION_SCHEMA",
    "STRATEGY_ALPHA_SCHEDULE_SCHEMA",
    "STRATEGY_DUAL_OUTCOME_CONTRACT_SCHEMA",
    "STRATEGY_ALPHA_OPEN_ISSUER_LIMIT",
    "STRATEGY_ALPHA_COHORT_ENROLLMENT_DAYS",
    "compile_strategy_alpha_episode_history",
    "compile_strategy_alpha_source_readiness",
    "schedule_strategy_alpha_prospective_episodes",
    "strategy_alpha_issuance_blockers",
    "strategy_alpha_cohort_gate",
    "strategy_alpha_cohort_policy",
    "strategy_alpha_issuance_vetoes",
]
