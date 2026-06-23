"""Neutral prediction-contract read model for scoreable forecast receipts.

This module is deliberately source-surface agnostic, but it is not a new
forecast dialect. It normalizes the field names already used by the forecast
pool, PATTERN-012 prediction ledger mirrors, and project-local autoresearch
workspaces into one read model for validation and Brier scoring.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ALLOWED_TIERS = {1, 2, 3}
SOURCE_SURFACES = {
    "prediction_ledger",
    "forecast_pool",
    "autoresearch_workspace",
    "scratch_contract",
}
PROVENANCE_MODES = {
    "in_loop",
    "out_of_loop",
    "forecast_pool",
    "external",
}
REQUIRED_FIELDS = (
    "prediction_id",
    "predicted_at",
    "predictor",
    "subject",
    "event",
    "p_success",
    "horizon",
    "resolution_rule",
    "tier",
)
SEAL_FIELDS = (
    "sealed_inputs_sha256",
    "source_context_sha256",
    "prediction_artifact_sha256",
)


@dataclass(frozen=True)
class PredictionContractDefaults:
    """Defaults supplied by a consumer that imports source-local rows."""

    subject: str | None = None
    source_surface: str | None = None
    provenance_mode: str | None = None
    producer: str | None = None
    tier: int | None = None


@dataclass(frozen=True)
class PredictionIssue:
    row: str
    severity: str
    code: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {
            "row": self.row,
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }


def read_prediction_rows(path: Path) -> tuple[list[dict[str, Any]], list[PredictionIssue]]:
    """Read JSONL prediction rows and return recoverable parse issues."""
    if not path.exists():
        return [], []
    rows: list[dict[str, Any]] = []
    issues: list[PredictionIssue] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            issues.append(
                PredictionIssue(
                    row=f"line:{line_no}",
                    severity="error",
                    code="malformed_json",
                    message=str(exc),
                )
            )
            continue
        if not isinstance(payload, dict):
            issues.append(
                PredictionIssue(
                    row=f"line:{line_no}",
                    severity="error",
                    code="non_object_row",
                    message="prediction rows must be JSON objects",
                )
            )
            continue
        rows.append(payload)
    return rows, issues


def normalize_prediction_contract(
    row: dict[str, Any],
    *,
    defaults: PredictionContractDefaults | None = None,
) -> dict[str, Any]:
    """Return a copy with canonical subject/provenance fields filled."""
    defaults = defaults or PredictionContractDefaults()
    normalized = dict(row)
    if not _nonempty_string(normalized.get("prediction_id")):
        normalized["prediction_id"] = _derived_prediction_id(normalized)
    if not _nonempty_string(normalized.get("predicted_at")):
        normalized["predicted_at"] = (
            normalized.get("forecasted_at")
            or normalized.get("created_at")
        )
    if not _nonempty_string(normalized.get("predictor")):
        normalized["predictor"] = (
            normalized.get("owner")
            or normalized.get("agent_id")
            or normalized.get("created_by")
        )
    if not _nonempty_string(normalized.get("subject")):
        normalized["subject"] = (
            normalized.get("substrate")
            or normalized.get("domain")
            or normalized.get("contract_id")
            or normalized.get("linked_scratch_id")
            or normalized.get("scratch_id")
            or defaults.subject
        )
    if not _nonempty_string(normalized.get("event")):
        normalized["event"] = (
            normalized.get("question")
            or normalized.get("contract_question")
            or normalized.get("success_threshold")
        )
    if not _nonempty_string(normalized.get("horizon")):
        normalized["horizon"] = (
            normalized.get("forecast_horizon")
            or normalized.get("resolution_predicate")
            or normalized.get("pre_registered_thresholds")
        )
    if not _nonempty_string(normalized.get("resolution_rule")):
        normalized["resolution_rule"] = _derived_resolution_rule(normalized)
    if normalized.get("tier") is None and defaults.tier is not None:
        normalized["tier"] = defaults.tier

    provenance = normalized.get("provenance")
    if not isinstance(provenance, dict):
        provenance = {}
    provenance = dict(provenance)
    if not _nonempty_string(provenance.get("source_surface")):
        provenance["source_surface"] = (
            normalized.get("source_surface")
            or _derived_source_surface(normalized)
            or defaults.source_surface
            or "prediction_ledger"
        )
    if not _nonempty_string(provenance.get("mode")):
        provenance["mode"] = (
            normalized.get("provenance_mode")
            or normalized.get("work_mode")
            or _derived_provenance_mode(normalized, provenance)
            or defaults.provenance_mode
            or "out_of_loop"
        )
    if not _nonempty_string(provenance.get("producer")):
        provenance["producer"] = (
            normalized.get("producer")
            or normalized.get("agent_id")
            or normalized.get("owner")
            or defaults.producer
            or normalized.get("predictor")
            or "unknown"
        )
    if "certified" not in provenance and "certified" in normalized:
        provenance["certified"] = bool(normalized.get("certified"))
    if "excluded_from_calibration" not in provenance and "excluded_from_calibration" in normalized:
        provenance["excluded_from_calibration"] = bool(normalized.get("excluded_from_calibration"))
    if "can_satisfy_membrane" not in provenance and "can_satisfy_membrane" in normalized:
        provenance["can_satisfy_membrane"] = bool(normalized.get("can_satisfy_membrane"))
    forecast_pool_semantics = normalized.get("forecast_pool_semantics")
    if isinstance(forecast_pool_semantics, dict):
        for key in ("certified", "excluded_from_calibration", "can_satisfy_membrane"):
            if key not in provenance and key in forecast_pool_semantics:
                provenance[key] = bool(forecast_pool_semantics.get(key))
    normalized["provenance"] = provenance
    return normalized


def validate_prediction_contract(
    row: dict[str, Any],
    *,
    defaults: PredictionContractDefaults | None = None,
) -> list[PredictionIssue]:
    """Validate one normalized scoreable prediction contract."""
    normalized = normalize_prediction_contract(row, defaults=defaults)
    row_id = str(normalized.get("prediction_id") or "<missing>")
    issues: list[PredictionIssue] = []
    for field in REQUIRED_FIELDS:
        value = normalized.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            issues.append(
                PredictionIssue(
                    row=row_id,
                    severity="error",
                    code="missing_required_field",
                    message=f"{field} is required",
                )
            )

    p_success = _coerce_float(normalized.get("p_success"))
    if p_success is None or not 0.0 <= p_success <= 1.0:
        issues.append(
            PredictionIssue(
                row=row_id,
                severity="error",
                code="invalid_probability",
                message="p_success must be a number in [0, 1]",
            )
        )

    tier = normalized.get("tier")
    if tier not in ALLOWED_TIERS:
        issues.append(
            PredictionIssue(
                row=row_id,
                severity="error",
                code="invalid_tier",
                message="tier must be 1, 2, or 3",
            )
        )

    provenance = normalized.get("provenance")
    if not isinstance(provenance, dict):
        issues.append(
            PredictionIssue(
                row=row_id,
                severity="error",
                code="invalid_provenance",
                message="provenance must be an object",
            )
        )
    else:
        source_surface = provenance.get("source_surface")
        mode = provenance.get("mode")
        producer = provenance.get("producer")
        if source_surface not in SOURCE_SURFACES:
            issues.append(
                PredictionIssue(
                    row=row_id,
                    severity="error",
                    code="invalid_source_surface",
                    message="source_surface must be prediction_ledger, forecast_pool, autoresearch_workspace, or scratch_contract",
                )
            )
        if mode not in PROVENANCE_MODES:
            issues.append(
                PredictionIssue(
                    row=row_id,
                    severity="error",
                    code="invalid_provenance_mode",
                    message="provenance.mode must be in_loop, out_of_loop, forecast_pool, or external",
                )
            )
        if not _nonempty_string(producer):
            issues.append(
                PredictionIssue(
                    row=row_id,
                    severity="error",
                    code="missing_producer",
                    message="provenance.producer is required",
                )
            )
        forecast_pool_surface = _is_forecast_pool_surface(provenance)
        forecast_pool_anchor = _has_forecast_pool_anchor(normalized)
        non_contract_scratch = _declares_non_contract_scratch(normalized)
        forecast_pool_authority = _has_forecast_pool_authority(normalized, provenance)
        if (
            forecast_pool_surface
            and (provenance.get("certified") is True or provenance.get("can_satisfy_membrane") is True)
            and not forecast_pool_anchor
        ):
            issues.append(
                PredictionIssue(
                    row=row_id,
                    severity="error",
                    code="missing_forecast_pool_authority_anchor",
                    message=(
                        "certified forecast-pool rows need contract_id plus "
                        "forecasted_at/agent_id or an explicit forecast_artifact_path"
                    ),
                )
            )
        if (
            forecast_pool_surface
            and non_contract_scratch
            and (provenance.get("certified") is True or provenance.get("can_satisfy_membrane") is True)
        ):
            issues.append(
                PredictionIssue(
                    row=row_id,
                    severity="error",
                    code="invalid_scratch_certification_claim",
                    message=(
                        "forecast_pool scratch mirrors marked not_a_gp230_contract "
                        "cannot claim certification or membrane eligibility"
                    ),
                )
            )
        if provenance.get("certified") is True and not forecast_pool_authority:
            issues.append(
                PredictionIssue(
                    row=row_id,
                    severity="error",
                    code="invalid_certification_claim",
                    message=(
                        "certified prediction rows must come from the certified "
                        "forecast_pool surface and forecast_pool mode"
                    ),
                )
            )
        if provenance.get("can_satisfy_membrane") is True and not forecast_pool_authority:
            issues.append(
                PredictionIssue(
                    row=row_id,
                    severity="error",
                    code="invalid_membrane_claim",
                    message=(
                        "only certified forecast_pool rows can claim membrane "
                        "eligibility; scratch and in-loop rows are measurement-only"
                    ),
                )
            )
        routing_authority_claim = (
            normalized.get("routing_authority")
            or provenance.get("routing_authority")
        )
        if (
            _nonempty_string(routing_authority_claim)
            and routing_authority_claim != "none_trace_does_not_route_work"
        ):
            issues.append(
                PredictionIssue(
                    row=row_id,
                    severity="error",
                    code="invalid_routing_authority_claim",
                    message=(
                        "prediction rows cannot claim routing authority; "
                        "routing requires a separate decision-use record"
                    ),
                )
            )
        if (
            normalized.get("can_route_work") is True
            or normalized.get("routes_work") is True
            or normalized.get("route_autoresearch") is True
            or provenance.get("can_route_work") is True
            or provenance.get("routes_work") is True
            or provenance.get("route_autoresearch") is True
        ):
            issues.append(
                PredictionIssue(
                    row=row_id,
                    severity="error",
                    code="invalid_routing_authority_claim",
                    message=(
                        "prediction rows cannot route work; route changes need "
                        "decision-use provenance"
                    ),
                )
            )
        if (
            normalized.get("decision_use_required_for_routing") is False
            or provenance.get("decision_use_required_for_routing") is False
        ):
            issues.append(
                PredictionIssue(
                    row=row_id,
                    severity="error",
                    code="invalid_decision_use_bypass_claim",
                    message=(
                        "prediction rows cannot waive decision-use evidence for routing"
                    ),
                )
            )
        if (
            provenance.get("can_satisfy_membrane") is True
            and provenance.get("certified") is not True
        ):
            issues.append(
                PredictionIssue(
                    row=row_id,
                    severity="error",
                    code="membrane_claim_requires_certification",
                    message="membrane-eligible forecast rows must also be certified",
                )
            )

    if not is_sealed_prediction(normalized):
        issues.append(
            PredictionIssue(
                row=row_id,
                severity="warning",
                code="unsealed_prediction",
                message=(
                    "row needs sealed_at plus one content hash before it can be "
                    "used as a calibration receipt"
                ),
            )
        )

    issues.extend(_validate_temporal_order(normalized, row_id=row_id))

    if is_resolved_prediction(normalized) and _resolved_success(normalized) is None:
        issues.append(
            PredictionIssue(
                row=row_id,
                severity="error",
                code="unscoreable_resolution",
                message="resolved rows need actual_success or a success/failure actual_outcome",
            )
        )

    return issues


def is_sealed_prediction(row: dict[str, Any]) -> bool:
    """Return True when the row carries a pre-resolution seal."""
    if not _nonempty_string(row.get("sealed_at")):
        has_timestamp = bool(row.get("predicted_at") or row.get("forecasted_at") or row.get("created_at"))
    else:
        has_timestamp = True
    return has_timestamp and any(
        _nonempty_string(row.get(field))
        for field in (
            *SEAL_FIELDS,
            "prediction_artifact_path",
            "forecast_artifact_path",
            "linked_scratch_id",
            "scratch_id",
            "contract_id",
        )
    )


def is_certified_prediction_contract(row: dict[str, Any]) -> bool:
    """Return True only for explicit certified forecast-pool provenance."""
    provenance = row.get("provenance")
    return (
        isinstance(provenance, dict)
        and _has_forecast_pool_authority(row, provenance)
        and provenance.get("certified") is True
        and provenance.get("excluded_from_calibration") is not True
    )


def can_satisfy_membrane(row: dict[str, Any]) -> bool:
    """Return True only when forecast-pool certification grants close authority."""
    provenance = row.get("provenance")
    return (
        is_certified_prediction_contract(row)
        and is_resolved_prediction(row)
        and isinstance(provenance, dict)
        and provenance.get("can_satisfy_membrane") is True
    )


def is_resolved_prediction(row: dict[str, Any]) -> bool:
    """Return True when a row claims an outcome has landed."""
    return _nonempty_string(row.get("resolved_at")) or row.get("actual_success") is not None


def score_binary_prediction_contract(row: dict[str, Any]) -> dict[str, Any] | None:
    """Return binary Brier score data for one resolved prediction."""
    p_success = _coerce_float(row.get("p_success"))
    actual = _resolved_success(row)
    if p_success is None or actual is None:
        return None
    y = 1.0 if actual else 0.0
    brier = (p_success - y) ** 2
    return {
        "prediction_id": str(row.get("prediction_id") or ""),
        "p_success": p_success,
        "actual_success": actual,
        "brier": brier,
        "uniform_brier": 0.25,
    }


def summarize_prediction_contract_rows(
    rows: list[dict[str, Any]],
    *,
    parse_issues: list[PredictionIssue] | None = None,
    defaults: PredictionContractDefaults | None = None,
) -> dict[str, Any]:
    """Summarize contract health and binary Brier readiness for a row set."""
    validation_issues: list[PredictionIssue] = list(parse_issues or [])
    normalized_rows = [
        normalize_prediction_contract(row, defaults=defaults)
        for row in rows
    ]
    valid_count = 0
    sealed_count = 0
    unresolved_count = 0
    resolved_count = 0
    source_surface_counts: dict[str, int] = {}
    provenance_mode_counts: dict[str, int] = {}
    producer_counts: dict[str, int] = {}
    certified_count = 0
    excluded_from_calibration_count = 0
    membrane_eligible_count = 0
    score_rows: list[dict[str, Any]] = []
    for row in normalized_rows:
        row_issues = validate_prediction_contract(row)
        validation_issues.extend(row_issues)
        has_error = any(issue.severity == "error" for issue in row_issues)
        if not has_error:
            valid_count += 1
        sealed = is_sealed_prediction(row)
        if sealed:
            sealed_count += 1
        resolved = is_resolved_prediction(row)
        if resolved:
            resolved_count += 1
        else:
            unresolved_count += 1
        provenance = row.get("provenance")
        excluded_from_calibration = False
        if isinstance(provenance, dict):
            _inc(source_surface_counts, str(provenance.get("source_surface") or "unknown"))
            _inc(provenance_mode_counts, str(provenance.get("mode") or "unknown"))
            _inc(producer_counts, str(provenance.get("producer") or "unknown"))
            if not has_error and is_certified_prediction_contract(row):
                certified_count += 1
            if provenance.get("excluded_from_calibration") is True:
                excluded_from_calibration = True
                excluded_from_calibration_count += 1
            if not has_error and can_satisfy_membrane(row):
                membrane_eligible_count += 1
        if not has_error and sealed and resolved and not excluded_from_calibration:
            score = score_binary_prediction_contract(row)
            if score is not None:
                score_rows.append(score)

    invalid_count = len(normalized_rows) - valid_count + len(parse_issues or [])
    mean_brier = _mean([float(row["brier"]) for row in score_rows])
    mean_uniform = _mean([float(row["uniform_brier"]) for row in score_rows])
    if invalid_count:
        status = "needs_attention"
    elif score_rows:
        status = "scoreable_measurement_lane"
    elif resolved_count:
        status = "resolved_no_calibration_rows"
    elif normalized_rows:
        status = "ready_for_resolution"
    else:
        status = "empty_prediction_contracts"
    authority = _prediction_authority_summary(
        certified_count=certified_count,
        membrane_eligible_count=membrane_eligible_count,
        scoreable_count=len(score_rows),
    )

    return {
        "status": status,
        "row_count": len(normalized_rows),
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "sealed_count": sealed_count,
        "unresolved_count": unresolved_count,
        "resolved_count": resolved_count,
        "scoreable_count": len(score_rows),
        "mean_brier": _round_or_none(mean_brier),
        "mean_uniform_brier": _round_or_none(mean_uniform),
        "beats_uniform_baseline": (
            mean_brier < mean_uniform if mean_brier is not None and mean_uniform is not None else None
        ),
        "source_surfaces": dict(sorted(source_surface_counts.items())),
        "provenance_modes": dict(sorted(provenance_mode_counts.items())),
        "producers": dict(sorted(producer_counts.items())),
        "certified_count": certified_count,
        "excluded_from_calibration_count": excluded_from_calibration_count,
        "membrane_eligible_count": membrane_eligible_count,
        "authority": authority,
        "issues": [issue.as_dict() for issue in validation_issues[:20]],
    }


def _prediction_authority_summary(
    *,
    certified_count: int,
    membrane_eligible_count: int,
    scoreable_count: int,
) -> dict[str, Any]:
    return {
        "score_authority": (
            "scoreable_binary_brier_rows"
            if scoreable_count
            else "not_scoreable_yet"
        ),
        "calibration_authority": (
            "certified_forecast_pool_rows"
            if certified_count
            else "not_calibration_authority"
        ),
        "membrane_authority": (
            "resolved_certified_forecast_pool_rows"
            if membrane_eligible_count
            else "not_membrane_evidence"
        ),
        "routing_authority": "none_trace_does_not_route_work",
        "decision_use_required_for_routing": True,
    }


def _derived_prediction_id(row: dict[str, Any]) -> str | None:
    scratch_id = row.get("linked_scratch_id") or row.get("scratch_id")
    if _nonempty_string(scratch_id):
        return str(scratch_id)
    contract_id = row.get("contract_id")
    agent_id = row.get("agent_id") or row.get("predictor") or row.get("owner")
    if _nonempty_string(contract_id) and _nonempty_string(agent_id):
        return f"{contract_id}:{agent_id}"
    if _nonempty_string(contract_id):
        return str(contract_id)
    return None


def _derived_resolution_rule(row: dict[str, Any]) -> str | None:
    if _nonempty_string(row.get("resolution_predicate")):
        return str(row["resolution_predicate"])
    if _nonempty_string(row.get("pre_registered_thresholds")):
        return str(row["pre_registered_thresholds"])
    objective = row.get("objective_resolver")
    threshold = row.get("success_threshold")
    if _nonempty_string(objective) or _nonempty_string(threshold):
        return f"resolver={objective or '?'}; success_threshold={threshold or '?'}"
    return None


def _derived_source_surface(row: dict[str, Any]) -> str | None:
    semantics = row.get("forecast_pool_semantics")
    if isinstance(semantics, dict) and semantics.get("source") == "forecast_pool scratch-forecast":
        return "scratch_contract"
    if row.get("excluded_from_calibration") is True or _nonempty_string(row.get("scratch_id")):
        return "scratch_contract"
    if _nonempty_string(row.get("linked_scratch_id")):
        return "scratch_contract"
    if _nonempty_string(row.get("contract_id")) or _nonempty_string(row.get("forecast_artifact_path")):
        return "forecast_pool"
    return None


def _derived_provenance_mode(row: dict[str, Any], provenance: dict[str, Any]) -> str | None:
    source_surface = provenance.get("source_surface") or _derived_source_surface(row)
    if source_surface == "forecast_pool":
        return "forecast_pool"
    if source_surface == "scratch_contract":
        return "out_of_loop"
    return None


def _is_forecast_pool_surface(provenance: dict[str, Any]) -> bool:
    return (
        provenance.get("source_surface") == "forecast_pool"
        and provenance.get("mode") == "forecast_pool"
    )


def _has_forecast_pool_anchor(row: dict[str, Any]) -> bool:
    if not _nonempty_string(row.get("contract_id")):
        return False
    if _nonempty_string(row.get("forecast_artifact_path")):
        return True
    return _nonempty_string(row.get("forecasted_at")) and _nonempty_string(row.get("agent_id"))


def _declares_non_contract_scratch(row: dict[str, Any]) -> bool:
    semantics = row.get("forecast_pool_semantics")
    return isinstance(semantics, dict) and semantics.get("not_a_gp230_contract") is True


def _has_forecast_pool_authority(row: dict[str, Any], provenance: dict[str, Any]) -> bool:
    return (
        _is_forecast_pool_surface(provenance)
        and _has_forecast_pool_anchor(row)
        and not _declares_non_contract_scratch(row)
    )


def _validate_temporal_order(row: dict[str, Any], *, row_id: str) -> list[PredictionIssue]:
    issues: list[PredictionIssue] = []
    predicted = _parse_timestamp(row.get("predicted_at"))
    forecasted = _parse_timestamp(row.get("forecasted_at"))
    sealed = _parse_timestamp(row.get("sealed_at"))
    resolved = _parse_timestamp(row.get("resolved_at"))

    for field, parsed in (
        ("predicted_at", predicted),
        ("forecasted_at", forecasted),
        ("sealed_at", sealed),
        ("resolved_at", resolved),
    ):
        value = row.get(field)
        if _nonempty_string(value) and parsed is None:
            issues.append(
                PredictionIssue(
                    row=row_id,
                    severity="error",
                    code="invalid_timestamp",
                    message=f"{field} must be an ISO timestamp",
                )
            )

    if predicted and forecasted and predicted != forecasted:
        issues.append(
            PredictionIssue(
                row=row_id,
                severity="error",
                code="prediction_forecast_time_mismatch",
                message="predicted_at and forecasted_at must name the same forecast instant",
            )
        )
    forecast_time = forecasted or predicted
    if forecast_time and sealed and sealed < forecast_time:
        issues.append(
            PredictionIssue(
                row=row_id,
                severity="error",
                code="noncausal_seal_order",
                message="sealed_at cannot precede predicted_at/forecasted_at",
            )
        )
    if forecast_time and resolved and forecast_time >= resolved:
        issues.append(
            PredictionIssue(
                row=row_id,
                severity="error",
                code="noncausal_resolution_order",
                message="prediction timestamp must strictly precede resolved_at",
            )
        )
    if sealed and resolved and sealed >= resolved:
        issues.append(
            PredictionIssue(
                row=row_id,
                severity="error",
                code="noncausal_seal_resolution_order",
                message="sealed_at must strictly precede resolved_at",
            )
        )
    return issues


def _resolved_success(row: dict[str, Any]) -> bool | None:
    actual = row.get("actual_success")
    if isinstance(actual, bool):
        return actual
    if isinstance(actual, int) and actual in {0, 1}:
        return bool(actual)
    label = str(row.get("actual_outcome") or "").strip().lower()
    if label in {"success", "succeeded", "pass", "passed", "true", "yes", "1"}:
        return True
    if label in {"failure", "failed", "fail", "false", "no", "0"}:
        return False
    return None


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _coerce_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_timestamp(value: Any) -> datetime | None:
    if not _nonempty_string(value):
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _round_or_none(value: float | None) -> float | None:
    return round(value, 4) if value is not None else None


def _inc(counts: dict[str, int], key: str) -> None:
    counts[key] = counts.get(key, 0) + 1
