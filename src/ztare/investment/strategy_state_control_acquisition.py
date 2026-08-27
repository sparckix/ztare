"""Bind point-in-time control research to a frozen strategy-state experiment."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, timestamp_key
from .strategy_control_research import STRATEGY_CONTROL_RESEARCH_REQUEST_SCHEMA
from .strategy_learning import (
    STRATEGY_COHORT_REQUEST_SCHEMA,
    STRATEGY_COHORT_RESULT_SCHEMA,
)
from .strategy_state_experiment import STRATEGY_STATE_EXPERIMENT_SCHEMA


STRATEGY_STATE_CONTROL_ACQUISITION_SCHEMA = (
    "jaggedthoughts-strategy-state-control-acquisition-v1"
)
_TRANSFER_ROLE = "cross_environment_transfer_discovery"
_CLASSIFICATIONS = {
    "phenotype_adoption_found",
    "family_adoption_only",
    "no_family_adoption_found",
    "insufficient_source_coverage",
}


def _checked_hash(row: Mapping[str, Any], field: str, label: str) -> str:
    body = dict(row)
    declared = str(body.pop(field, ""))
    if declared != stable_sha256(body):
        raise ValueError(f"{label} content hash mismatch")
    return declared


def _after(value: Any, opened_at: str, label: str) -> bool:
    return timestamp_key(canonical_timestamp(value, label)) > timestamp_key(opened_at)


def _index(
    rows: Iterable[Mapping[str, Any]], field: str, label: str,
) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for source in rows:
        row = dict(source)
        identity = str(row.get(field) or "")
        if not identity:
            continue
        if identity in indexed:
            raise ValueError(f"duplicate {label} identity")
        indexed[identity] = row
    return indexed


def compile_strategy_state_control_acquisition(
    *,
    experiment: Mapping[str, Any],
    control_requests: Iterable[Mapping[str, Any]],
    cohort_requests: Iterable[Mapping[str, Any]],
    cohort_results: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Compile eligible controls without changing the frozen experiment."""
    if experiment.get("schema") != STRATEGY_STATE_EXPERIMENT_SCHEMA:
        raise ValueError("control acquisition requires a strategy-state experiment")
    experiment_sha = _checked_hash(
        experiment, "experiment_sha256", "strategy-state experiment",
    )
    if (
        experiment.get("signal_authority") is not False
        or experiment.get("paper_policy_authority") is not False
        or experiment.get("capital_authority") is not False
        or (experiment.get("persistent_state_path") or {}).get("causal_interpretation")
        is not False
    ):
        raise ValueError("strategy-state experiment carries forbidden authority")

    opened_at = canonical_timestamp(
        experiment.get("opened_at"), "strategy-state experiment opened_at",
    )
    plan_sha = str((experiment.get("input_identity") or {}).get("cohort_plan_sha256") or "")
    phenotype_sha = str(
        (experiment.get("strategy_action") or {}).get("mechanism_phenotype_sha256") or ""
    )
    industry_rows = [
        row for row in experiment.get("controls") or ()
        if isinstance(row, Mapping) and row.get("control_id") == "industry_state_markov"
    ]
    if not plan_sha or not phenotype_sha or len(industry_rows) != 1:
        raise ValueError("strategy-state experiment lacks one control identity")
    industry_id = str(industry_rows[0].get("industry_id") or "")
    if not industry_id:
        raise ValueError("strategy-state experiment lacks its industry identity")

    request_index = _index(cohort_requests, "request_sha256", "cohort request")
    result_index = _index(cohort_results, "request_sha256", "cohort result")
    adapters = [
        dict(row) for row in control_requests
        if row.get("schema") == STRATEGY_CONTROL_RESEARCH_REQUEST_SCHEMA
    ]
    exact = [row for row in adapters if row.get("cohort_plan_sha256") == plan_sha]
    excluded, bound, eligible = [], [], []
    reasons_seen: Counter[str] = Counter()
    classifications: Counter[str] = Counter()
    seen_cohort_requests: set[str] = set()

    for adapter in sorted(exact, key=lambda row: str(row.get("request_sha256") or "")):
        adapter_sha = _checked_hash(
            adapter, "request_sha256", "strategy control research request",
        )
        cohort_sha = str(adapter.get("cohort_request_sha256") or "")
        if cohort_sha in seen_cohort_requests:
            raise ValueError("cohort request has multiple exact-plan control bindings")
        seen_cohort_requests.add(cohort_sha)
        request = request_index.get(cohort_sha)
        reasons: list[str] = []
        if request is None:
            reasons.append("cohort_request_missing")
        else:
            if request.get("schema") != STRATEGY_COHORT_REQUEST_SCHEMA:
                raise ValueError("control binding targets an unsupported cohort request")
            _checked_hash(request, "request_sha256", "strategy cohort request")
            environment = dict(adapter.get("environment") or {})
            move_phenotype = dict(adapter.get("move_phenotype") or {})
            if (
                adapter.get("peer_entity_id") != request.get("peer_entity_id")
                or environment.get("industry_id") != request.get("industry_id")
                or move_phenotype.get("mechanism_phenotype_sha256")
                != request.get("mechanism_phenotype_sha256")
                or adapter.get("adoption_search_window") != {
                    "start_at": request.get("search_start_at"),
                    "end_at": request.get("search_end_at"),
                }
            ):
                raise ValueError("control adapter crossed its cohort request identity")
            if request.get("search_role") == _TRANSFER_ROLE:
                reasons.append("cross_environment_transfer_discovery")
            if request.get("mechanism_phenotype_sha256") != phenotype_sha:
                reasons.append("phenotype_mismatch")
            if request.get("industry_id") != industry_id:
                reasons.append("industry_mismatch")
            if any(
                _after(value, opened_at, label)
                for value, label in (
                    (adapter.get("created_at"), "control request created_at"),
                    ((adapter.get("adoption_search_window") or {}).get("end_at"),
                     "control request search end"),
                    (request.get("created_at"), "cohort request created_at"),
                    (request.get("search_end_at"), "cohort request search end"),
                )
            ):
                reasons.append("request_after_experiment_open")
            if adapter.get("capital_authority") is not False or request.get(
                "capital_authority"
            ) is not False:
                raise ValueError("control request carries capital authority")

        if reasons:
            reasons = sorted(set(reasons))
            reasons_seen.update(reasons)
            excluded.append({
                "control_request_sha256": adapter_sha,
                "cohort_request_sha256": cohort_sha,
                "peer_entity_id": adapter.get("peer_entity_id"),
                "reasons": reasons,
            })
            continue

        assert request is not None
        result = result_index.get(cohort_sha)
        result_reasons: list[str] = []
        classification = None
        result_sha = None
        if result is None:
            result_reasons.append("classification_missing")
        else:
            if result.get("schema") != STRATEGY_COHORT_RESULT_SCHEMA:
                raise ValueError("control binding targets an unsupported cohort result")
            result_sha = _checked_hash(result, "result_sha256", "strategy cohort result")
            classification = str(result.get("classification") or "")
            if (
                result.get("request_sha256") != cohort_sha
                or result.get("peer_entity_id") != request.get("peer_entity_id")
                or result.get("mechanism_phenotype_sha256") != phenotype_sha
            ):
                raise ValueError("strategy cohort result crossed the control identity")
            if classification not in _CLASSIFICATIONS:
                raise ValueError("strategy cohort result classification is unsupported")
            classifications[classification] += 1
            chronology = [
                (result.get("assessed_at"), "cohort result assessed_at"),
                ((result.get("coverage") or {}).get("search_end_at"),
                 "cohort result search end"),
                *[(row.get("published_at"), "cohort source published_at")
                  for row in result.get("sources") or ()],
                *[(row.get("available_at"), "cohort event available_at")
                  for row in result.get("events") or ()],
            ]
            if any(_after(value, opened_at, label) for value, label in chronology):
                result_reasons.append("result_after_experiment_open")
            coverage = dict(result.get("coverage") or {})
            if classification == "no_family_adoption_found" and not (
                result.get("panel_role") == "not_yet_treated_candidate"
                and not result.get("events")
                and coverage.get("sec_filings_searched") is True
                and coverage.get("issuer_materials_searched") is True
                and coverage.get("search_start_at") == request.get("search_start_at")
                and coverage.get("search_end_at") == request.get("search_end_at")
                and result.get("sources")
            ):
                result_reasons.append("no_family_evidence_contract_failed")

        row = {
            "control_request_sha256": adapter_sha,
            "cohort_request_sha256": cohort_sha,
            "peer_entity_id": request["peer_entity_id"],
            "classification": classification,
            "result_sha256": result_sha,
            "eligible_no_family_control": bool(
                classification == "no_family_adoption_found" and not result_reasons
            ),
            "reasons": sorted(set(result_reasons)),
        }
        bound.append(row)
        reasons_seen.update(row["reasons"])
        if row["eligible_no_family_control"]:
            eligible.append({
                "entity_id": row["peer_entity_id"],
                "cohort_request_sha256": cohort_sha,
                "result_sha256": result_sha,
            })

    body = {
        "schema": STRATEGY_STATE_CONTROL_ACQUISITION_SCHEMA,
        "experiment_sha256": experiment_sha,
        "opened_at": opened_at,
        "cohort_plan_sha256": plan_sha,
        "frozen_experiment_missing_control_ids": list(
            experiment.get("missing_control_ids") or ()
        ),
        "control_identity": {
            "mechanism_phenotype_sha256": phenotype_sha,
            "industry_id": industry_id,
            "excluded_search_role": _TRANSFER_ROLE,
        },
        "industry_state_control": {
            "status": industry_rows[0].get("status"),
            "reason": industry_rows[0].get("reason"),
        },
        "eligible_no_family_controls_exist": bool(eligible),
        "eligible_controls": eligible,
        "bound_requests": bound,
        "excluded_requests": excluded,
        "audit": {
            "control_request_artifact_count": len(adapters),
            "other_cohort_plan_count": len(adapters) - len(exact),
            "exact_cohort_plan_count": len(exact),
            "bound_request_count": len(bound),
            "eligible_control_count": len(eligible),
            "classification_counts": dict(sorted(classifications.items())),
            "reason_counts": dict(sorted(reasons_seen.items())),
        },
        "causal_interpretation": False,
        "causal_estimate_ran": False,
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    unresolved_results = reasons_seen.get("classification_missing", 0)
    body["status"] = (
        "eligible_no_family_controls_acquired"
        if eligible
        else "awaiting_point_in_time_classifications"
        if unresolved_results
        else "no_eligible_same_environment_control"
    )
    body["next_activation"] = (
        "Bind the remaining point-in-time classifications."
        if unresolved_results
        else (
            "Freeze a successor experiment with a new same-industry cohort and industry-state "
            "snapshot, or use a design that does not require untreated peers; do not relabel "
            "family-only or transfer peers."
        )
    )
    return {**body, "acquisition_sha256": stable_sha256(body)}


def compile_workspace_strategy_state_control_acquisition(
    workspace: str | Path, experiment_path: str | Path,
) -> dict[str, Any]:
    """Read immutable workspace artifacts and compile the point-in-time control view."""
    root = Path(workspace).expanduser().resolve()
    source = Path(experiment_path).expanduser()
    if not source.is_absolute():
        source = root / source
    experiment = json.loads(source.resolve().read_text(encoding="utf-8"))

    def rows(relative: str) -> list[dict[str, Any]]:
        return [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted((root / relative).glob("*.json"))
        ]

    return compile_strategy_state_control_acquisition(
        experiment=experiment,
        control_requests=rows("research_jobs/strategy_controls/requests"),
        cohort_requests=rows("research_jobs/strategy_cohorts/requests"),
        cohort_results=rows("institutional_learning/strategy_cohorts/results"),
    )


__all__ = [
    "STRATEGY_STATE_CONTROL_ACQUISITION_SCHEMA",
    "compile_strategy_state_control_acquisition",
    "compile_workspace_strategy_state_control_acquisition",
]
