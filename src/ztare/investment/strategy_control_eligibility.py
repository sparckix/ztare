"""Deterministic admission frontier for strategy-law control histories."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

from ztare.common.equivariance import stable_sha256

from .institutional_learning import CAUSAL_PANEL_ROW_SCHEMA
from .strategy_learning import (
    STRATEGY_COHORT_PLAN_SCHEMA,
    resolve_strategy_cohort_results,
)


STRATEGY_CONTROL_ELIGIBILITY_FRONTIER_SCHEMA = (
    "jaggedthoughts-strategy-control-eligibility-frontier-v1"
)


def _checked_hash(row: Mapping[str, Any], field: str, label: str) -> str:
    body = dict(row)
    declared = str(body.pop(field, ""))
    if declared != stable_sha256(body):
        raise ValueError(f"{label} content hash mismatch")
    return declared


def _unit_rows(panel_rows: Iterable[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    units: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for raw in panel_rows:
        row = dict(raw)
        if row.get("schema") != CAUSAL_PANEL_ROW_SCHEMA:
            raise ValueError(f"control admission requires {CAUSAL_PANEL_ROW_SCHEMA}")
        units[str(row.get("unit_id") or "")].append(row)
    for unit_id, rows in units.items():
        periods = [int(row["period_index"]) for row in rows]
        if not unit_id or len(periods) != len(set(periods)):
            raise ValueError("control admission found a missing unit or duplicate unit-period")
    return units


def _history_audit(
    unit_id: str, rows: list[dict[str, Any]], *, metric_id: str, unit: str,
    minimum_pre: int, minimum_post: int,
) -> dict[str, Any]:
    treated = {bool(row.get("treated_group")) for row in rows}
    periods = sorted(int(row["period_index"]) for row in rows)
    treatment_periods = {row.get("treatment_period") for row in rows}
    event_shas = {row.get("treatment_event_sha256") for row in rows}
    environments = {stable_sha256(dict(row.get("environment") or {})) for row in rows}
    metrics = {(str(row.get("outcome_metric_id")), str(row.get("outcome_unit"))) for row in rows}
    if len(treated) != 1 or len(treatment_periods) != 1 or len(event_shas) != 1 or len(environments) != 1:
        raise ValueError("causal history changes treatment or environment identity within a unit")
    if metrics != {(metric_id, unit)}:
        raise ValueError("causal history changed the outcome metric or unit")
    treatment_period = next(iter(treatment_periods))
    is_treated = next(iter(treated))
    if is_treated and (
        treatment_period is None
        or next(iter(event_shas)) is None
        or {row.get("treatment_timing_status") for row in rows} != {"exact_adoption_event"}
    ):
        raise ValueError("treated causal history lacks exact adoption timing")
    if not is_treated and (treatment_period is not None or next(iter(event_shas)) is not None):
        raise ValueError("control history carries treatment identity")
    pre = [period for period in periods if treatment_period is not None and period < int(treatment_period)]
    post = [period for period in periods if treatment_period is not None and period >= int(treatment_period)]
    return {
        "unit_id": unit_id,
        "entity_id": unit_id.rsplit(":", 1)[-1],
        "treated_group": is_treated,
        "treatment_period": treatment_period,
        "treatment_event_sha256": next(iter(event_shas)),
        "periods": periods,
        "pre_period_count": len(pre),
        "post_period_count": len(post),
        "pre_period_ready": len(pre) >= minimum_pre if is_treated else None,
        "post_period_ready": len(post) >= minimum_post if is_treated else None,
        "environment": dict(rows[0].get("environment") or {}),
        "environment_sha256": next(iter(environments)),
        "outcome_metric_id": metric_id,
        "outcome_unit": unit,
    }


def compile_strategy_control_eligibility_frontier(
    plan: Mapping[str, Any], results: Iterable[Mapping[str, Any]],
    panel_rows: Iterable[Mapping[str, Any]], law: Mapping[str, Any], *,
    terminal_gap_request_sha256s: Iterable[str] = (),
    readiness: Mapping[str, Any] | None = None,
    historical_requests: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Admit only bounded non-adopters with compatible pre-period histories."""
    if plan.get("schema") != STRATEGY_COHORT_PLAN_SCHEMA:
        raise ValueError(f"control admission requires {STRATEGY_COHORT_PLAN_SCHEMA}")
    plan_sha = _checked_hash(plan, "plan_sha256", "strategy cohort plan")
    requests = {str(row["request_sha256"]): dict(row) for row in plan.get("requests") or ()}
    if len(requests) != int(plan.get("request_count", -1)):
        raise ValueError("strategy cohort plan has duplicate or missing requests")
    for request_sha, request in requests.items():
        if stable_sha256({key: value for key, value in request.items() if key != "request_sha256"}) != request_sha:
            raise ValueError("strategy cohort request content hash mismatch")

    result_rows = [dict(row) for row in results]
    current_results, coverage_chain = resolve_strategy_cohort_results(
        plan, result_rows, historical_requests=historical_requests,
    )

    validation = dict(law.get("validation") or {})
    metric_id = str(law.get("outcome_metric_id") or "")
    minimum_pre = int(validation.get("minimum_pre_periods", 2))
    minimum_post = int(validation.get("minimum_post_periods", 1))
    units = _unit_rows(panel_rows)
    treated_rows = [row for rows in units.values() for row in rows if row.get("treated_group")]
    treated_units = sorted({str(row["unit_id"]) for row in treated_rows})
    units_seen = {str(row.get("outcome_unit") or "") for row in treated_rows}
    if not metric_id or len(units_seen) != 1:
        raise ValueError("treated histories do not bind one law metric and unit")
    outcome_unit = next(iter(units_seen))
    histories = {
        unit_id: _history_audit(
            unit_id, rows, metric_id=metric_id, unit=outcome_unit,
            minimum_pre=minimum_pre, minimum_post=minimum_post,
        )
        for unit_id, rows in units.items()
    }
    treated_histories = [histories[unit_id] for unit_id in treated_units]
    treatment_periods = sorted({
        int(row["treatment_period"]) for row in treated_histories
        if row["treatment_period"] is not None
    })

    terminal_gaps = set(terminal_gap_request_sha256s) & set(requests)
    readiness_status = {
        str(row.get("entity_id") or "").upper(): dict(row)
        for row in (readiness or {}).get("history_status") or ()
        if isinstance(row, Mapping) and row.get("entity_id")
    }
    peer_rows, source_requests = [], []
    for request_sha, request in sorted(requests.items(), key=lambda item: str(item[1]["peer_entity_id"])):
        entity = str(request["peer_entity_id"]).upper()
        result = current_results.get(request_sha)
        classification = str((result or {}).get("classification") or "")
        reasons = []
        stage = "request_bound"
        if result is None:
            reasons.append(
                "non_adoption_source_coverage_missing"
                if request_sha in terminal_gaps else "adoption_classification_missing"
            )
        elif classification == "phenotype_adoption_found":
            reasons.append("exact_phenotype_adoption_contaminates_control")
        elif classification == "family_adoption_only":
            reasons.append("related_family_adoption_contaminates_control")
        elif classification == "insufficient_source_coverage":
            reasons.append("non_adoption_source_coverage_missing")
        elif classification != "no_family_adoption_found":
            reasons.append("unsupported_adoption_relation")
        else:
            stage = "adoption_relation_bound"
            coverage = dict(result.get("coverage") or {})
            if (
                result.get("panel_role") != "not_yet_treated_candidate"
                or result.get("events")
                or not coverage.get("sec_filings_searched")
                or not coverage.get("issuer_materials_searched")
                or coverage.get("search_start_at") != request.get("search_start_at")
                or coverage.get("search_end_at") != request.get("search_end_at")
                or not result.get("sources")
            ):
                reasons.append("bounded_non_adoption_evidence_invalid")

        expected_environment = {
            "industry_id": request["industry_id"],
            "mechanism_signature_sha256": request["mechanism_signature_sha256"],
            "mechanism_phenotype_sha256": request["mechanism_phenotype_sha256"],
        }
        eligible_periods: list[int] = []
        unit_id = f"{str(request['mechanism_phenotype_sha256'])[:12]}:{entity}"
        history = histories.get(unit_id)
        if not reasons:
            if history is None or history["treated_group"]:
                reasons.append("pre_period_outcome_history_missing")
            elif history["environment"] != expected_environment:
                reasons.append("environment_moderator_mismatch")
            else:
                stage = "moderator_bound"
                periods = set(history["periods"])
                eligible_periods = [
                    treatment_period for treatment_period in treatment_periods
                    if {treatment_period - 2, treatment_period - 1}.issubset(periods)
                ]
                if not eligible_periods:
                    reasons.append("pre_period_outcome_support_missing")
                elif any(
                    row.get("treatment_period") is not None
                    or row.get("treatment_event_sha256") is not None
                    or row.get("treatment_timing_status") != "never_treated_as_of_panel"
                    for row in units[unit_id]
                ):
                    reasons.append("control_treatment_timing_invalid")
                else:
                    stage = "admissible"

        if reasons and request_sha not in terminal_gaps and reasons[0] in {
            "adoption_classification_missing", "non_adoption_source_coverage_missing",
        }:
            needs = ["bounded_adoption_relation", "non_adoption_primary_source_coverage"]
            history_row = readiness_status.get(entity, {})
            if int(history_row.get("period_count") or 0) < minimum_pre:
                needs.append("pre_period_earnings_durability_history")
            source_requests.append({
                "request_id": f"control-admission:{request_sha}",
                "request_sha256": request_sha,
                "peer_entity_id": entity,
                "search_start_at": request["search_start_at"],
                "search_end_at": request["search_end_at"],
                "required_source_classes": request["required_source_classes"],
                "required_evidence": needs,
            })
        elif reasons and reasons[0] in {
            "pre_period_outcome_history_missing", "pre_period_outcome_support_missing",
        }:
            source_requests.append({
                "request_id": f"control-history:{request_sha}",
                "request_sha256": request_sha,
                "peer_entity_id": entity,
                "required_source_classes": ["sec_filings"],
                "required_evidence": [
                    f"{metric_id}:{outcome_unit}:periods_before:{','.join(map(str, treatment_periods))}",
                ],
            })
        peer_rows.append({
            "peer_entity_id": entity,
            "request_sha256": request_sha,
            "classification": classification or (
                "terminal_source_gap" if request_sha in terminal_gaps else "pending"
            ),
            "mechanism_signature_sha256": request["mechanism_signature_sha256"],
            "mechanism_phenotype_sha256": request["mechanism_phenotype_sha256"],
            "environment": expected_environment,
            "environment_sha256": stable_sha256(expected_environment),
            "outcome_metric_id": metric_id,
            "outcome_unit": outcome_unit,
            "non_adoption_evidence_sha256": (
                result.get("result_sha256") if classification == "no_family_adoption_found" else None
            ),
            "eligible_treatment_periods": eligible_periods,
            "frontier_stage": stage,
            "admissible_control": not reasons,
            "kill_reasons": reasons,
        })

    reason_counts = Counter(reason for row in peer_rows for reason in row["kill_reasons"])
    missing_counts = {
        reason: count for reason, count in reason_counts.items()
        if reason in {
            "adoption_classification_missing", "non_adoption_source_coverage_missing",
            "bounded_non_adoption_evidence_invalid", "pre_period_outcome_history_missing",
            "pre_period_outcome_support_missing", "environment_moderator_mismatch",
        }
    }
    dominant_missing = max(
        missing_counts, key=lambda reason: (missing_counts[reason], reason), default=None,
    )
    admissible = [row for row in peer_rows if row["admissible_control"]]
    body = {
        "schema": STRATEGY_CONTROL_ELIGIBILITY_FRONTIER_SCHEMA,
        "plan_sha256": plan_sha,
        "law_contract_sha256": stable_sha256(law),
        "as_of": min(str(row["search_end_at"]) for row in requests.values()),
        "outcome_contract": {
            "metric_id": metric_id, "unit": outcome_unit,
            "minimum_pre_periods": minimum_pre, "minimum_post_periods": minimum_post,
        },
        "audit": {
            "peer_request_count": len(requests),
            "current_result_count": len(current_results),
            "recovered_compatible_result_count": coverage_chain[
                "recovered_compatible_result_count"
            ],
            "stale_result_artifact_count": coverage_chain[
                "rejected_changed_identity_count"
            ] + coverage_chain["rejected_invalid_artifact_count"],
            "terminal_source_gap_count": len(terminal_gaps),
            "pending_classification_count": len(requests) - len(current_results) - len(terminal_gaps),
            "treated_history_count": len(treated_histories),
            "admissible_control_count": len(admissible),
            "kill_reason_counts": dict(sorted(reason_counts.items())),
        },
        "treatment_histories": treated_histories,
        "treatment_periods": treatment_periods,
        "peer_eligibility": peer_rows,
        "admissible_controls": admissible,
        "next_source_requests": source_requests,
        "dominant_missing_evidence": ({
            "reason": dominant_missing,
            "count": missing_counts[dominant_missing],
            "peer_entity_ids": sorted(
                row["peer_entity_id"] for row in peer_rows
                if dominant_missing in row["kill_reasons"]
            ),
        } if dominant_missing else None),
        "causal_estimation_status": "blocked_invalid_control_set",
        "causal_estimate_ran": False,
        "capital_authority": False,
    }
    return {**body, "control_frontier_sha256": stable_sha256(body)}


def compile_workspace_strategy_control_eligibility(workspace: str | Path) -> dict[str, Any]:
    root = Path(workspace).expanduser().resolve()
    cohort = root / "institutional_learning" / "strategy_cohorts"
    plan = json.loads((cohort / "latest.json").read_text(encoding="utf-8"))
    readiness = json.loads((cohort / "panel-readiness.json").read_text(encoding="utf-8"))
    _checked_hash(readiness, "readiness_sha256", "strategy panel readiness")
    results = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((cohort / "results").glob("*.json"))]
    historical_requests = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((root / "research_jobs" / "strategy_cohorts" / "requests").glob("*.json"))
    ]
    panel_path = root / str(readiness["panel_path"])
    panel_rows = [json.loads(line) for line in panel_path.read_text(encoding="utf-8").splitlines() if line]
    catalog = yaml.safe_load((root / "institutional_learning" / "laws.yaml").read_text(encoding="utf-8"))
    law = next(row for row in catalog["candidates"] if row["law_id"] == "reinforcing-strategy-choice-durability")
    source_gap_entities = {
        str(row["entity_id"]).upper() for row in readiness.get("history_status") or ()
        if row.get("status") == "excluded_source_gap"
    }
    terminal_gaps = {
        str(row["request_sha256"]) for row in plan["requests"]
        if str(row["peer_entity_id"]).upper() in source_gap_entities
    }
    return compile_strategy_control_eligibility_frontier(
        plan, results, panel_rows, law,
        terminal_gap_request_sha256s=terminal_gaps, readiness=readiness,
        historical_requests=historical_requests,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    result = compile_workspace_strategy_control_eligibility(args.workspace)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        destination = Path(args.output).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "STRATEGY_CONTROL_ELIGIBILITY_FRONTIER_SCHEMA",
    "compile_strategy_control_eligibility_frontier",
    "compile_workspace_strategy_control_eligibility",
]
