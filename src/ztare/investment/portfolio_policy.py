"""Prospective tournaments over complete paper-allocation policies."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256
from ztare.worldmodel.evaluation import EvaluationScore, conservative_paired_survivor_set

from .contracts import canonical_timestamp, require_finite, timestamp_key
from .factor_analysis import PricePoint, compile_return_covariance, load_price_points
from .fund_sleeve_comparison import FUND_PROGRAM_TOURNAMENT_INPUT_SCHEMA
from .golden_store import GoldenEdge, GoldenLeaf, GoldenStore
from .portfolio_risk_challenger import (
    compile_walk_forward_ridge_risk_challenger,
    minimum_variance_weights,
)
from .prospective_return_window import (
    RETURN_WINDOW_BINDING_SCHEMA,
    RETURN_WINDOW_SCHEMA,
    bind_prospective_return_window,
    compile_prospective_return_window,
    settle_prospective_return_window,
)


PORTFOLIO_POLICY_RUN_SCHEMA = "jaggedthoughts-portfolio-policy-run-v1"
PORTFOLIO_POLICY_SETTLEMENT_SCHEMA = "jaggedthoughts-portfolio-policy-settlement-v1"
PORTFOLIO_POLICY_STATUS_SCHEMA = "jaggedthoughts-portfolio-policy-status-v1"
PORTFOLIO_POLICY_REVIEW_SCHEMA = "jaggedthoughts-portfolio-policy-review-v1"
OPPORTUNITY_RANKING_TICKET_SCHEMA = "jaggedthoughts-opportunity-ranking-ticket-v1"
PRIMARY_HORIZON_DAYS = 365
_POLICY_VERSION = "8"
_SCORE_CONTRACT_VERSION = "4"
_RETURN_PRICE_IDENTITY = "adjusted_close_total_return_proxy"
_COST_APPLICATION = "round_trip_once_in_prospective_return_window"
_TRANSACTION_COST_SENSITIVITY_BPS = (0.0, 5.0, 10.0, 25.0, 50.0)
_RISK_CHALLENGER_ID = "equity_walk_forward_ridge_minimum_variance"
_RISK_COMPARATOR_ID = "equity_minimum_variance"

_RANKING_CLAIMS = {
    "discovery_priority": (
        "research_priority_score", ("point_in_time_discovery_rank",),
    ),
    "learned_law_priority": (
        "learned_research_priority_score",
        ("point_in_time_discovery_rank", "eligible_strategy_law_adjustment"),
    ),
    "factor_implied_return_control": (
        "factor_implied_return", ("point_in_time_factor_implied_return",),
    ),
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _valid_hash(payload: Mapping[str, Any], field: str) -> bool:
    claimed = str(payload.get(field) or "")
    return bool(claimed) and claimed == stable_sha256({
        key: value for key, value in payload.items() if key != field
    })


def _estimand_role(horizon_days: int) -> str:
    return (
        "primary_patient_capital_policy_evidence"
        if int(horizon_days) == PRIMARY_HORIZON_DAYS else "diagnostic_only"
    )


def _current_run_identity(run: Mapping[str, Any]) -> bool:
    settlement = run.get("settlement_contract") or {}
    window = settlement.get("prospective_return_window") or {}
    risk_evaluation = settlement.get("risk_challenger_evaluation") or {}
    try:
        cost_matches = float(settlement.get("transaction_cost_bps")) == float(
            window.get("transaction_cost_bps")
        )
    except (TypeError, ValueError):
        return False
    versions = (run.get("trial_family") or {}).get("policy_versions") or {}
    return bool(
        run.get("schema") == PORTFOLIO_POLICY_RUN_SCHEMA
        and versions
        and all(str(version) == _POLICY_VERSION for version in versions.values())
        and settlement.get("score_contract_version") == _SCORE_CONTRACT_VERSION
        and settlement.get("cost_application") == _COST_APPLICATION
        and risk_evaluation.get("schema")
        == "jaggedthoughts-portfolio-risk-evaluation-contract-v1"
        and _valid_hash(risk_evaluation, "risk_evaluation_contract_sha256")
        and window.get("schema") == RETURN_WINDOW_SCHEMA
        and window.get("price_identity") == _RETURN_PRICE_IDENTITY
        and cost_matches
        and run.get("estimand_role") == _estimand_role(int(run.get("horizon_days") or 0))
    )


def _supersession_path(base: Path, run_id: str) -> Path:
    return base / "supersessions" / f"{run_id}.json"


def _entry_is_bound(base: Path, run_id: str) -> bool:
    envelope = _read_json(base / "return_windows" / f"{run_id}.json") or {}
    return (envelope.get("binding") or {}).get("status") == "bound"


def _point_dict(point: PricePoint) -> dict[str, Any]:
    return {
        "entity_id": point.entity_id,
        "price": point.value,
        "observed_at": point.observed_at,
        "available_at": point.available_at,
        "observation_id": point.observation_id,
        "source_ref": point.source_ref,
    }


def _price_series(
    root: Path, as_of: str, entity_ids: Iterable[str] | None = None,
) -> dict[str, list[PricePoint]]:
    scope = (
        {str(entity_id).upper() for entity_id in entity_ids if str(entity_id)}
        if entity_ids is not None else None
    )
    if scope == set():
        return {}
    points = load_price_points(
        root / "data" / "observations.csv", as_of=as_of,
        metric_id="adjusted_price", entity_ids=scope,
    )
    cutoff = timestamp_key(as_of)
    by_entity_date: dict[tuple[str, str], PricePoint] = {}
    for point in points:
        if timestamp_key(point.observed_at) > cutoff:
            continue
        key = (point.entity_id.upper(), point.date_key)
        current = by_entity_date.get(key)
        if current is None or (point.available_at, point.observed_at, point.observation_id) > (
            current.available_at, current.observed_at, current.observation_id
        ):
            by_entity_date[key] = point
    series: dict[str, list[PricePoint]] = {}
    for (entity_id, _date), point in by_entity_date.items():
        series.setdefault(entity_id, []).append(point)
    for rows in series.values():
        rows.sort(key=lambda row: (row.observed_at, row.available_at, row.observation_id))
    return series


def _cash_yield(root: Path, horizon_days: int, *, as_of: str) -> tuple[float, str]:
    cutoff = timestamp_key(as_of)
    snapshots = [
        row for path in (root / "market_state" / "snapshots").glob("*.json")
        if (row := _read_json(path)) and row.get("cash_yields")
        and timestamp_key(
            str((row.get("point_in_time_snapshot") or {}).get("as_of") or "9999-12-31T00:00:00Z")
        ) <= cutoff
    ]
    latest = max(
        snapshots,
        key=lambda row: str((row.get("point_in_time_snapshot") or {}).get("as_of") or ""),
        default=None,
    )
    if not latest:
        return 0.0, "cash-yield-unavailable"
    key = "90" if horizon_days <= 180 else "365"
    return float(latest["cash_yields"][key]), str(latest["snapshot_artifact_sha256"])


def _allocate(scores: Mapping[str, float], *, gross: float, maximum: float) -> dict[str, float]:
    positive = {key: max(0.0, float(value)) for key, value in scores.items()}
    total = sum(positive.values())
    if not positive:
        return {}
    if total <= 0:
        positive = {key: 1.0 for key in positive}
        total = float(len(positive))
    return {
        key: min(maximum, gross * value / total)
        for key, value in sorted(positive.items())
    }


def _policy(
    policy_id: str, method: str, weights: Mapping[str, float], source_refs: Iterable[str],
    *, expected_return_claim: bool | None = None, evaluation_role: str | None = None,
    promotion_eligible: bool | None = None,
) -> dict[str, Any]:
    clean = {key: float(value) for key, value in sorted(weights.items()) if float(value) > 1e-12}
    body = {
        "policy_id": policy_id,
        "version": _POLICY_VERSION,
        "method": method,
        "weights": clean,
        "gross_weight": sum(clean.values()),
        "cash_weight": 1.0 - sum(clean.values()),
        "source_refs": sorted(set(source_refs)),
        "authority": "prospective_shadow",
        "capital_authority": False,
    }
    if expected_return_claim is not None:
        body["expected_return_claim"] = expected_return_claim
    if evaluation_role is not None:
        body["evaluation_role"] = evaluation_role
    if promotion_eligible is not None:
        body["promotion_eligible_under_current_score_contract"] = promotion_eligible
    return {**body, "policy_sha256": stable_sha256(body)}


def _risk_model(
    series: Mapping[str, list[PricePoint]], entity_ids: Iterable[str], *, as_of: str,
) -> dict[str, Any]:
    identities = tuple(sorted(set(entity_ids)))
    covariance = compile_return_covariance(
        price_series={
            entity_id: {point.date_key: point.value for point in series[entity_id]}
            for entity_id in identities
        },
        as_of=as_of,
    )
    common_days = set.intersection(*(
        {point.date_key for point in series[entity_id]} for entity_id in identities
    ))
    used = [
        point
        for entity_id in identities
        for point in series[entity_id]
        if point.date_key in common_days
        and covariance["window_start"] <= point.date_key <= covariance["window_end"]
    ]
    observation_tuples = sorted([
        (
            point.entity_id, point.observed_at, point.available_at, point.value,
            point.observation_id, point.source_ref,
        )
        for point in used
    ])
    evidence = {
        "observation_count": len(used),
        "observation_ids_sha256": stable_sha256(sorted(point.observation_id for point in used)),
        "point_in_time_observation_tuples_sha256": stable_sha256(observation_tuples),
        "return_covariance_sha256": covariance["return_covariance_sha256"],
        "source_refs": sorted({point.source_ref for point in used}),
    }
    body = {
        "schema": "jaggedthoughts-portfolio-policy-risk-model-v1",
        "return_covariance": covariance,
        "source_evidence": evidence,
        "historical_mean_used_as_forecast": False,
        "expected_return_claim": False,
    }
    return {**body, "risk_model_sha256": stable_sha256(body)}


def _minimum_variance_weights(
    risk_model: Mapping[str, Any], *, gross: float, maximum: float,
) -> dict[str, float]:
    covariance = risk_model["return_covariance"]
    entity_ids = tuple(map(str, covariance["entity_ids"]))
    return minimum_variance_weights(
        covariance["covariance_matrix"], entity_ids,
        gross_weight=gross, maximum_weight=maximum,
    )


def _assembly_policies(
    assembly: Mapping[str, Any] | None,
    universe_ids: set[str],
    *,
    opened_at: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not assembly:
        return [], []
    body = dict(assembly)
    declared = str(body.pop("portfolio_assembly_sha256", ""))
    reason = None
    if declared != stable_sha256(body):
        reason = "portfolio_assembly_hash_mismatch"
    elif body.get("schema") != "jaggedthoughts-portfolio-assembly-v1":
        reason = "unsupported_portfolio_assembly_schema"
    elif body.get("authority") != "paper" or body.get("scope_closed") is not True:
        reason = "portfolio_assembly_not_closed_paper_authority"
    elif timestamp_key(str(body.get("as_of") or "")) > timestamp_key(opened_at):
        reason = "portfolio_assembly_not_available_at_open"
    if reason:
        return [], [{"policy_id": "portfolio_assembly", "reason": reason}]

    fixed = {
        str(key).upper(): float(value)
        for key, value in (body.get("fixed_position_weights") or {}).items()
        if float(value) > 1e-12
    }
    candidates: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for policy_id, method, field in (
        ("mechanism_safe_assembly", "frozen_mechanism_safe_underwriting", "selected_target_weights"),
        ("nominal_assembly", "frozen_nominal_underwriting", "nominal_selected_target_weights"),
    ):
        weights = dict(fixed)
        for key, value in (body.get(field) or {}).items():
            identity = str(key).upper()
            weights[identity] = weights.get(identity, 0.0) + float(value)
        if any(value < 0 for value in weights.values()) or sum(weights.values()) > 1 + 1e-12:
            excluded.append({"policy_id": policy_id, "reason": "invalid_assembly_weight_vector"})
            continue
        missing = sorted(key for key, value in weights.items() if value > 1e-12 and key not in universe_ids)
        if missing:
            excluded.append({
                "policy_id": policy_id,
                "reason": "assembly_entity_outside_priced_tournament_universe",
                "entity_ids": missing,
            })
            continue
        candidates.append(_policy(policy_id, method, weights, (declared,)))
    return candidates, excluded


def _admission_policy_scores(
    admissions: Mapping[str, Any] | None,
    universe_ids: set[str],
    *,
    opened_at: str,
    horizon_days: int,
    benchmark_id: str,
) -> tuple[
    dict[str, float], dict[str, float], list[dict[str, Any]], str | None,
    list[dict[str, Any]],
]:
    """Verify admissions and expose equity scores plus single-fund challengers."""
    if not admissions:
        return {}, {}, [], None, []
    body = dict(admissions)
    declared = str(body.pop("workspace_admissions_sha256", ""))
    if (
        body.get("schema") != "jaggedthoughts-workspace-instrument-portfolio-admissions-v1"
        or len(declared) != 64 or stable_sha256(body) != declared
    ):
        raise ValueError("instrument portfolio admissions hash or schema is invalid")
    if timestamp_key(str(body.get("compiled_at") or "")) > timestamp_key(opened_at):
        raise ValueError("instrument portfolio admissions were unavailable at policy open")
    expected: dict[str, float] = {}
    risk_adjusted: dict[str, float] = {}
    funds: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for raw in body.get("admissions") or ():
        admission = dict(raw)
        admission_sha = str(admission.pop("admission_sha256", ""))
        if len(admission_sha) != 64 or stable_sha256(admission) != admission_sha:
            raise ValueError("instrument portfolio admission content hash mismatch")
        subject = dict(admission.get("subject") or {})
        entity_id = str(subject.get("subject_id") or "").upper()
        entity_kind = str(subject.get("entity_kind") or "")
        if entity_kind not in {"public_equity", "public_fund"}:
            continue
        if entity_id not in universe_ids:
            excluded.append({
                "policy_id": "instrument_admission_expected_return",
                "entity_id": entity_id,
                "reason": "admitted_entity_outside_priced_tournament_universe",
            })
            continue
        eligibility = dict(admission.get("eligibility") or {})
        if eligibility.get("research_paper_portfolio_candidate") is not True:
            continue
        projection = dict(admission.get("portfolio_projection") or {})
        downside = require_finite(
            projection.get("downside_risk"), "admission downside risk",
        )
        claims = list(projection.get("expected_active_return_claims") or ())
        compatible: list[tuple[dict[str, Any], str]] = []
        reason = None
        if not claims:
            reason = "prospective_active_return_claim_absent"
        for raw_claim in claims:
            claim = dict(raw_claim)
            claim_sha = str(claim.pop("claim_sha256", ""))
            if (
                claim.get("schema") != "jaggedthoughts-prospective-active-return-claim-v1"
                or len(claim_sha) != 64
                or stable_sha256(claim) != claim_sha
                or claim.get("estimand") != "annualized_active_return"
                or any(len(str(claim.get(field) or "")) != 64 for field in (
                    "forecast_sha256", "run_sha256", "packet_sha256",
                    "paper_decision_sha256",
                ))
            ):
                reason = "prospective_active_return_claim_invalid"
                break
            if claim.get("authority") != "prospective_shadow" or claim.get("capital_authority") is not False:
                reason = "prospective_active_return_claim_authority_invalid"
                break
            if str(claim.get("subject_entity_id") or "").upper() != entity_id:
                reason = "prospective_active_return_claim_subject_mismatch"
                break
            if timestamp_key(str(claim.get("sealed_at") or "")) > timestamp_key(opened_at):
                reason = "prospective_active_return_claim_not_available_at_open"
                break
            underperformance = require_finite(
                claim.get("underperformance_probability"),
                "admission underperformance probability",
            )
            if not 0 <= underperformance <= 1:
                reason = "prospective_active_return_claim_invalid"
                break
            if (
                str(claim.get("benchmark_entity_id") or "").upper() == benchmark_id.upper()
                and int(claim.get("horizon_days") or 0) == int(horizon_days)
            ):
                compatible.append((claim, claim_sha))
        if reason is None and len(compatible) != 1:
            reason = (
                "prospective_active_return_claim_horizon_or_benchmark_absent"
                if not compatible else "prospective_active_return_claim_ambiguous"
            )
        if reason:
            excluded.append({
                "policy_id": "instrument_admission_prospective_active_return",
                "entity_id": entity_id,
                "reason": reason,
            })
            continue
        claim, claim_sha = compatible[0]
        active_return = require_finite(
            claim.get("value"), "admission prospective active return",
        )
        if entity_kind == "public_equity":
            expected[entity_id] = max(0.0, active_return)
            risk_adjusted[entity_id] = max(0.0, active_return) / max(downside, 1e-6)
            continue
        if active_return <= 0:
            excluded.append({
                "policy_id": f"fund_admission:{entity_id}",
                "entity_id": entity_id,
                "reason": "nonpositive_prospective_active_return",
            })
            continue
        cap = require_finite(
            projection.get("target_weight_cap"), "fund admission target weight cap",
        )
        if not 0 < cap <= 1:
            raise ValueError("fund admission target weight cap must be in (0, 1]")
        funds.append({
            "entity_id": entity_id,
            "sleeve_id": str(subject.get("implementation_sleeve_id") or "unassigned"),
            "target_weight_cap": cap,
            "expected_active_return": active_return,
            "expected_active_return_claim_sha256": claim_sha,
            "downside_risk": downside,
            "admission_sha256": admission_sha,
        })
    return expected, risk_adjusted, funds, declared, excluded


def _candidate_policies(
    book: Mapping[str, Any],
    universe: list[Mapping[str, Any]],
    *,
    gross: float,
    maximum: float,
    opened_at: str,
    horizon_days: int,
    benchmark_id: str,
    portfolio_assembly: Mapping[str, Any] | None = None,
    paper_proposal_audits: Iterable[Mapping[str, Any]] = (),
    risk_model: Mapping[str, Any] | None = None,
    risk_challenger: Mapping[str, Any] | None = None,
    instrument_portfolio_admissions: Mapping[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    # Funds are same-sleeve implementation challengers. Combining them with
    # single-company weights would double-count equity exposure and answer a
    # different allocation question.
    allocation_universe = [
        row for row in universe if row.get("entity_kind") == "public_equity"
    ]
    entity_ids = [str(row["entity_id"]).upper() for row in allocation_universe]
    base = {
        str(row["entity_id"]).upper(): float(row.get("research_priority_score") or 0.0)
        for row in allocation_universe
    }
    learned = {
        str(row["entity_id"]).upper(): float(row.get("learned_research_priority_score") or 0.0)
        for row in allocation_universe
    }
    factor = {
        str(row["entity_id"]).upper(): float(value)
        for row in allocation_universe
        if (value := (row.get("economic_coordinates") or {}).get("factor_implied_return"))
        is not None
    }
    candidates = [
        _policy("cash_control", "cash_only", {}, (str(book["book_sha256"]),)),
        _policy(
            "equity_equal_weight", "equal_weight_qualified_public_equities",
            _allocate({entity_id: 1.0 for entity_id in entity_ids}, gross=gross, maximum=maximum),
            (str(book["book_sha256"]),),
        ),
        _policy(
            "equity_discovery_priority", "proportional_equity_discovery_priority",
            _allocate(base, gross=gross, maximum=maximum),
            (str(book["book_sha256"]),),
        ),
        _policy(
            "equity_learned_law_priority", "proportional_equity_law_adjusted_priority",
            _allocate(learned, gross=gross, maximum=maximum),
            (
                str(book["book_sha256"]),
                str((book.get("law_policy_influence") or {}).get("influence_sha256") or ""),
                str((book.get("causal_law_target_influence") or {}).get(
                    "influence_set_sha256"
                ) or ""),
            ),
        ),
    ]
    exclusions: list[dict[str, Any]] = []
    all_entity_ids = {str(row["entity_id"]).upper() for row in universe}
    (
        admission_scores, admission_risk_scores, fund_admissions, admission_sha,
        admission_exclusions,
    ) = (
        _admission_policy_scores(
            instrument_portfolio_admissions, all_entity_ids, opened_at=opened_at,
            horizon_days=horizon_days, benchmark_id=benchmark_id,
        )
    )
    exclusions.extend(admission_exclusions)
    if len(admission_scores) >= 2 and sum(admission_scores.values()) > 0 and admission_sha:
        candidates.extend((
            _policy(
                "equity_admission_prospective_active_return",
                "proportional_exact_horizon_sealed_active_return",
                _allocate(admission_scores, gross=gross, maximum=maximum),
                (admission_sha,), expected_return_claim=True,
            ),
            _policy(
                "equity_admission_active_return_to_downside",
                "proportional_exact_horizon_sealed_active_return_to_downside",
                _allocate(admission_risk_scores, gross=gross, maximum=maximum),
                (admission_sha,), expected_return_claim=True,
            ),
        ))
    if admission_sha:
        for fund in fund_admissions:
            weight = min(gross, maximum, float(fund["target_weight_cap"]))
            candidates.append(_policy(
                f"fund_admission:{fund['sleeve_id']}:{fund['entity_id']}",
                "capped_single_fund_sleeve_challenger",
                {str(fund["entity_id"]): weight},
                (admission_sha, str(fund["admission_sha256"])),
                expected_return_claim=True,
                evaluation_role="fund_sleeve_vs_cash_and_policy_challenger",
                promotion_eligible=False,
            ))
    if risk_model is not None:
        try:
            candidates.append(_policy(
                "equity_minimum_variance",
                "minimum_variance_qualified_public_equities",
                _minimum_variance_weights(risk_model, gross=gross, maximum=maximum),
                (f"return-covariance:{risk_model['risk_model_sha256']}",),
                expected_return_claim=False,
                evaluation_role="diagnostic_risk_comparator",
                promotion_eligible=False,
            ))
        except ValueError as exc:
            exclusions.append({
                "policy_id": "equity_minimum_variance",
                "reason": "minimum_variance_solver_failed",
                "detail": str(exc),
            })
    if risk_challenger is not None:
        candidates.append(_policy(
            "equity_walk_forward_ridge_minimum_variance",
            "chronological_validation_selected_ridge_minimum_variance",
            risk_challenger["weights"],
            (f"portfolio-risk-challenger:{risk_challenger['risk_challenger_sha256']}",),
            expected_return_claim=False,
            evaluation_role="diagnostic_risk_comparator",
            promotion_eligible=False,
        ))
    if len(factor) >= 2:
        candidates.append(_policy(
            "equity_factor_implied_return_control", "proportional_equity_factor_implied_return",
            _allocate(factor, gross=gross, maximum=maximum),
            (str(book["book_sha256"]),),
        ))
    admitted: set[str] = set()
    proposal_refs: set[str] = set()
    for audit in paper_proposal_audits:
        if not _valid_hash(audit, "audit_sha256"):
            raise ValueError("paper proposal audit hash is invalid")
        if (
            book.get("discovery_run_sha256")
            and audit.get("discovery_run_sha256") != book.get("discovery_run_sha256")
        ):
            raise ValueError("paper proposal audit and opportunity book use different discovery epochs")
        proposal_refs.add(str(audit["audit_sha256"]))
        for row in audit.get("rows") or ():
            proposal = row.get("proposal") if isinstance(row.get("proposal"), Mapping) else None
            if (
                not proposal
                or proposal.get("schema") != "jaggedthoughts-public-equity-paper-proposal-v1"
                or not _valid_hash(proposal, "proposal_sha256")
                or row.get("activation_eligible") is not True
                or row.get("blockers")
                or proposal.get("activation_blockers")
            ):
                continue
            position = proposal.get("position_admission") or {}
            entity_id = str((proposal.get("entity") or {}).get("entity_id") or "").upper()
            if position.get("eligible") is True and not position.get("blockers") and entity_id in entity_ids:
                admitted.add(entity_id)
                proposal_refs.add(str(proposal["proposal_sha256"]))
    if len(admitted) >= 2:
        candidates.append(_policy(
            "equity_fully_gated_equal_weight",
            "equal_weight_current_position_admissible_public_equities",
            _allocate({entity_id: 1.0 for entity_id in admitted}, gross=gross, maximum=maximum),
            proposal_refs,
        ))
    active = {
        str(row.get("entity_id") or "").upper(): float(row.get("target_weight") or 0.0)
        for row in book.get("active_positions") or () if row.get("entity_id")
    }
    if active:
        candidates.append(_policy(
            "operator_active_book", "frozen_operator_weights", active,
            (str(book["book_sha256"]),),
        ))
    assembly_candidates, assembly_exclusions = _assembly_policies(
        portfolio_assembly, set(entity_ids), opened_at=opened_at,
    )
    exclusions.extend(assembly_exclusions)
    candidates.extend(assembly_candidates)
    representatives: list[dict[str, Any]] = []
    by_weights: dict[str, dict[str, Any]] = {}
    equivalence: list[dict[str, Any]] = []
    for candidate in candidates:
        weights_sha = stable_sha256(candidate["weights"])
        representative = by_weights.get(weights_sha)
        if representative is None:
            by_weights[weights_sha] = candidate
            representatives.append(candidate)
        else:
            equivalent = {
                "policy_id": candidate["policy_id"],
                "representative_policy_id": representative["policy_id"],
                "witness": "identical_weight_vector",
                "weights_sha256": weights_sha,
            }
            if candidate.get("promotion_eligible_under_current_score_contract") is False:
                equivalent.update({
                    "evaluation_role": candidate.get("evaluation_role"),
                    "promotion_eligible_under_current_score_contract": False,
                })
            equivalence.append(equivalent)
    return representatives, equivalence, exclusions


def _ranking_tickets(
    book: Mapping[str, Any], universe: Iterable[Mapping[str, Any]], *,
    opened_at: str, end_at: str, benchmark_id: str,
) -> list[dict[str, Any]]:
    """Freeze the three rank claims already carried by the policy tournament."""

    tickets = []
    for claim_id, (field, mechanisms) in _RANKING_CLAIMS.items():
        ranked = []
        for candidate in universe:
            if candidate.get("entity_kind") != "public_equity":
                continue
            value = (
                (candidate.get("economic_coordinates") or {}).get(field)
                if claim_id == "factor_implied_return_control"
                else candidate.get(field)
            )
            if value is None:
                continue
            ranked.append({
                "entity_id": str(candidate["entity_id"]).upper(),
                "entity_kind": str(candidate["entity_kind"]),
                "candidate_sha256": str(candidate["candidate_sha256"]),
                "score": float(value),
                "source_refs": sorted(set(candidate.get("source_refs") or ())),
                "mechanism_refs": sorted({
                    str(row.get("law_key"))
                    for row in ((candidate.get("law_policy_influence") or {}).get("contributions") or ())
                    if row.get("law_key")
                } | {
                    str(value)
                    for value in ((candidate.get("causal_law_target_influence") or {}).get(
                        "influence_sha256s"
                    ) or ())
                }) if claim_id == "learned_law_priority" else [],
            })
        if len(ranked) < 2:
            continue
        ranked.sort(key=lambda row: (-row["score"], row["entity_id"]))
        ranked = [{**row, "rank": index} for index, row in enumerate(ranked, 1)]
        body = {
            "schema": OPPORTUNITY_RANKING_TICKET_SCHEMA,
            "claim_id": claim_id,
            "source_cutoff": opened_at,
            "outcome_window": {
                "earliest_start_at": opened_at,
                "nominal_end_at": end_at,
                "start_rule": "first_synchronized_observation_on_or_after_run_seal",
                "end_rule": "first_synchronized_observation_on_or_after_entry_plus_horizon",
            },
            "benchmark_id": benchmark_id,
            "ranked_candidates": ranked,
            "expected_mechanism_ids": list(mechanisms),
            "score_semantics": (
                "factor_implied_expected_return"
                if claim_id == "factor_implied_return_control"
                else "research_priority_not_expected_return"
            ),
            "source_refs": sorted({
                f"opportunity-book:{book['book_sha256']}",
                *(ref for row in ranked for ref in row["source_refs"]),
            }),
            "settlement_contract": {
                "outcome": "benchmark_relative_total_return",
                "calibration": "mean_absolute_rank_percentile_error",
                "regret": "top_1_active_return_regret",
            },
            "status": "unresolved",
            "candidate_set_sha256": stable_sha256([
                row["candidate_sha256"] for row in sorted(
                    ranked, key=lambda candidate: candidate["candidate_sha256"]
                )
            ]),
            "authority": "paper_shadow",
            "capital_authority": False,
        }
        tickets.append({
            **body,
            "ticket_id": f"{claim_id}-{stable_sha256(body)[:20]}",
            "ticket_sha256": stable_sha256(body),
        })
    return tickets


def _fund_program_ranking_tickets(
    raw: Mapping[str, Any] | None, *, series: Mapping[str, list[PricePoint]],
    opened_at: str, end_at: str, benchmark_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, str]]]:
    if raw is None:
        return [], [], []
    evidence = dict(raw)
    declared = str(evidence.pop("tournament_input_sha256", ""))
    if (
        evidence.get("schema") != FUND_PROGRAM_TOURNAMENT_INPUT_SCHEMA
        or stable_sha256(evidence) != declared
    ):
        raise ValueError("fund program tournament input hash is invalid")
    if timestamp_key(str(evidence["as_of"])) > timestamp_key(opened_at):
        raise ValueError("fund program tournament input was unavailable at open")
    claims = {
        str(row["claim_id"]): dict(row)
        for row in evidence.get("selection_claims") or ()
    }
    tickets = []
    universe: dict[str, dict[str, Any]] = {}
    excluded = []
    for sleeve in evidence.get("sleeves") or ():
        sleeve_id = str(sleeve["sleeve_id"])
        for claim_id, claim in sorted(claims.items()):
            require_lookthrough = claim_id == "lookthrough_durable_earnings_power"
            ranked = []
            for program in sleeve.get("programs") or ():
                ready = program.get(
                    "lookthrough_quality_ready" if require_lookthrough
                    else "same_information_core_ready"
                )
                coordinate = (program.get("ranking_coordinates") or {}).get(
                    claim["coordinate"]
                )
                entity_id = str(program.get("entity_id") or "").upper()
                if not ready or coordinate is None:
                    continue
                if not series.get(entity_id):
                    excluded.append({
                        "entity_id": entity_id,
                        "reason": "fund_program_start_price_unavailable",
                    })
                    continue
                row = {
                    "entity_id": entity_id,
                    "entity_kind": "public_fund",
                    "candidate_sha256": str(program["program_sha256"]),
                    "program_id": str(program["program_id"]),
                    "score": float(coordinate),
                    "source_refs": [f"fund-program:{program['program_sha256']}"],
                    "mechanism_refs": [],
                }
                ranked.append(row)
                universe[entity_id] = {
                    "entity_id": entity_id,
                    "entity_kind": "public_fund",
                    "program_id": row["program_id"],
                    "program_sha256": row["candidate_sha256"],
                    "sleeve_id": sleeve_id,
                }
            if len(ranked) < 2:
                continue
            ranked.sort(key=lambda row: (-row["score"], row["entity_id"]))
            ranked = [{**row, "rank": index} for index, row in enumerate(ranked, 1)]
            body = {
                "schema": OPPORTUNITY_RANKING_TICKET_SCHEMA,
                "claim_id": f"fund::{sleeve_id}::{claim_id}",
                "source_cutoff": opened_at,
                "outcome_window": {
                    "earliest_start_at": opened_at, "nominal_end_at": end_at,
                    "start_rule": "first_synchronized_observation_on_or_after_run_seal",
                    "end_rule": "first_synchronized_observation_on_or_after_entry_plus_horizon",
                },
                "benchmark_id": benchmark_id,
                "ranked_candidates": ranked,
                "expected_mechanism_ids": [claim_id],
                "score_semantics": str(claim["semantics"]),
                "source_refs": sorted({
                    f"fund-program-input:{declared}",
                    *(ref for row in ranked for ref in row["source_refs"]),
                }),
                "settlement_contract": {
                    "outcome": "benchmark_relative_total_return",
                    "calibration": "mean_absolute_rank_percentile_error",
                    "regret": "top_1_active_return_regret",
                },
                "status": "unresolved",
                "candidate_set_sha256": stable_sha256([
                    row["candidate_sha256"] for row in sorted(
                        ranked, key=lambda candidate: candidate["candidate_sha256"]
                    )
                ]),
                "authority": "paper_shadow",
                "capital_authority": False,
            }
            tickets.append({
                **body,
                "ticket_id": f"fund-{sleeve_id}-{claim_id}-{stable_sha256(body)[:16]}",
                "ticket_sha256": stable_sha256(body),
            })
    return tickets, list(sorted(universe.values(), key=lambda row: row["entity_id"])), excluded


def _score_ranking_ticket(
    ticket: Mapping[str, Any], returns: Mapping[str, float], benchmark_return: float,
) -> dict[str, Any]:
    frozen = [
        row for row in ticket.get("ranked_candidates") or ()
        if str(row.get("entity_id") or "") in returns
    ]
    if len(frozen) < 2:
        raise ValueError("ranking ticket settlement requires two realized candidates")
    actual = sorted(
        frozen,
        key=lambda row: (-float(returns[str(row["entity_id"])]), str(row["entity_id"])),
    )
    actual_rank = {str(row["entity_id"]): index for index, row in enumerate(actual, 1)}
    scale = len(frozen) - 1
    calibration = sum(
        abs(int(row["rank"]) - actual_rank[str(row["entity_id"])]) / scale
        for row in frozen
    ) / len(frozen)
    concordance = []
    for left_index, left in enumerate(frozen):
        for right in frozen[left_index + 1:]:
            left_return = float(returns[str(left["entity_id"])])
            right_return = float(returns[str(right["entity_id"])])
            concordance.append(0.5 if left_return == right_return else float(left_return > right_return))
    leader = str(frozen[0]["entity_id"])
    best = max(float(returns[str(row["entity_id"])]) for row in frozen)
    body = {
        "ticket_id": str(ticket["ticket_id"]),
        "ticket_sha256": str(ticket["ticket_sha256"]),
        "claim_id": str(ticket["claim_id"]),
        "candidate_set_sha256": ticket.get("candidate_set_sha256"),
        "candidate_count": len(frozen),
        "rank_calibration": {
            "metric": "mean_absolute_rank_percentile_error",
            "value": calibration,
        },
        "pairwise_rank_accuracy": sum(concordance) / len(concordance),
        "regret": {
            "metric": "top_1_active_return_regret",
            "value": best - float(returns[leader]),
        },
        "top_ranked_entity_id": leader,
        "top_ranked_active_return": float(returns[leader]) - benchmark_return,
        "realized_ranking": [
            {
                "rank": index,
                "entity_id": str(row["entity_id"]),
                "total_return": float(returns[str(row["entity_id"])]),
                "active_return": float(returns[str(row["entity_id"])]) - benchmark_return,
            }
            for index, row in enumerate(actual, 1)
        ],
        "mechanism_settlement_authority": "predictive_bundle_only",
        "capital_authority": False,
    }
    return {**body, "ranking_score_sha256": stable_sha256(body)}


def _trial_family(run: Mapping[str, Any]) -> dict[str, Any]:
    policies = {
        str(row["policy_id"]): str(row.get("version") or _POLICY_VERSION)
        for row in run.get("policies") or ()
    }
    policies.update({
        str(row["policy_id"]): _POLICY_VERSION
        for row in run.get("equivalent_policies") or ()
    })
    body = {
        "schema": "jaggedthoughts-portfolio-policy-trial-family-v1",
        "policy_versions": dict(sorted(policies.items())),
        "horizon_days": int(run.get("horizon_days") or 0),
        "estimand_role": str(run.get("estimand_role") or "legacy_unspecified"),
        "benchmark_id": str((run.get("benchmark") or {}).get("entity_id") or ""),
        "score_contract_version": str(
            (run.get("settlement_contract") or {}).get("score_contract_version") or ""
        ),
        "return_price_identity": str(
            ((run.get("settlement_contract") or {}).get("prospective_return_window") or {}).get(
                "price_identity"
            ) or ""
        ),
        "cost_application": str(
            (run.get("settlement_contract") or {}).get("cost_application") or ""
        ),
        "transaction_cost_bps": float(
            (run.get("settlement_contract") or {}).get("transaction_cost_bps") or 0.0
        ),
        "risk_evaluation_contract_sha256": str(
            ((run.get("settlement_contract") or {}).get("risk_challenger_evaluation") or {}).get(
                "risk_evaluation_contract_sha256"
            ) or ""
        ),
    }
    return {**body, "trial_family_id": stable_sha256(body)}


def _expanded_policy_scores(
    run: Mapping[str, Any], settlement: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    scores = {
        str(row["policy_id"]): dict(row) for row in settlement.get("policy_scores") or ()
    }
    for row in run.get("equivalent_policies") or ():
        representative = scores.get(str(row["representative_policy_id"]))
        if representative:
            scores[str(row["policy_id"])] = {
                **representative,
                "policy_id": str(row["policy_id"]),
                "equivalent_representative_policy_id": str(row["representative_policy_id"]),
            }
    return scores


def _transaction_cost_sensitivity(
    *, policies: Iterable[Mapping[str, Any]], gross_returns: Mapping[str, float],
    benchmark_id: str, cash_return: float, declared_bps: float,
) -> dict[str, Any]:
    """Reprice frozen policy weights and gross returns over one compact cost grid."""

    def after_cost(gross_return: float, bps: float) -> float:
        one_way = bps / 10_000.0
        return (1.0 + gross_return) * (1.0 - one_way) ** 2 - 1.0

    benchmark_gross = float(gross_returns[benchmark_id])
    rows = []
    for policy in policies:
        weights = {str(key): float(value) for key, value in policy["weights"].items()}
        gross_weight = sum(weights.values())
        cash_weight = 1.0 - gross_weight
        gross_return = cash_weight * cash_return + sum(
            weight * float(gross_returns[entity_id])
            for entity_id, weight in weights.items()
        )
        points = []
        for bps in _TRANSACTION_COST_SENSITIVITY_BPS:
            benchmark_net = after_cost(benchmark_gross, bps)
            net_return = cash_weight * cash_return + sum(
                weight * after_cost(float(gross_returns[entity_id]), bps)
                for entity_id, weight in weights.items()
            )
            points.append({
                "transaction_cost_bps": bps,
                "net_return": net_return,
                "excess_return_vs_benchmark": net_return - benchmark_net,
                "cost_drag_vs_zero_bps": gross_return - net_return,
            })
        invested_terminal = sum(
            weight * (1.0 + float(gross_returns[entity_id]))
            for entity_id, weight in weights.items()
        )
        relative_terminal_delta = invested_terminal - (1.0 + benchmark_gross)
        break_even = None
        if not math.isclose(relative_terminal_delta, 0.0, abs_tol=1e-15):
            squared_retention = -cash_weight * (1.0 + cash_return) / relative_terminal_delta
            if 0.0 <= squared_retention <= 1.0:
                break_even = 10_000.0 * (1.0 - math.sqrt(squared_retention))
        rows.append({
            "policy_id": str(policy["policy_id"]),
            "turnover_basis": {
                "one_way_gross_weight": gross_weight,
                "round_trip_weight": 2.0 * gross_weight,
                "cash_weight": cash_weight,
                "weights_frozen": True,
            },
            "gross_return_before_cost": gross_return,
            "break_even_bps_vs_benchmark": break_even,
            "break_even_within_declared_grid": bool(
                break_even is not None
                and _TRANSACTION_COST_SENSITIVITY_BPS[0] <= break_even
                <= _TRANSACTION_COST_SENSITIVITY_BPS[-1]
            ),
            "points": points,
        })
    order_by_bps = []
    for index, bps in enumerate(_TRANSACTION_COST_SENSITIVITY_BPS):
        ordered = sorted(
            rows,
            key=lambda row: (
                -float(row["points"][index]["excess_return_vs_benchmark"]),
                str(row["policy_id"]),
            ),
        )
        order_by_bps.append({
            "transaction_cost_bps": bps,
            "policy_ids": [str(row["policy_id"]) for row in ordered],
        })
    comparable = len(rows) > 1
    return {
        "transaction_cost_bps_grid": list(_TRANSACTION_COST_SENSITIVITY_BPS),
        "declared_settlement_bps": float(declared_bps),
        "cost_application": _COST_APPLICATION,
        "benchmark_id": benchmark_id,
        "benchmark_turnover_basis": {
            "one_way_gross_weight": 1.0, "round_trip_weight": 2.0,
        },
        "policies": rows,
        "ordering": {
            "comparable_policy_count": len(rows),
            "policy_order_by_bps": order_by_bps,
            "stable_across_grid": (
                all(row["policy_ids"] == order_by_bps[0]["policy_ids"] for row in order_by_bps[1:])
                if comparable else None
            ),
        },
    }


def _policy_weights(
    policies: Iterable[Mapping[str, Any]],
    equivalent_policies: Iterable[Mapping[str, Any]],
    policy_id: str,
) -> dict[str, float] | None:
    by_id = {str(row["policy_id"]): row for row in policies}
    policy = by_id.get(policy_id)
    if policy is None:
        equivalent = next(
            (row for row in equivalent_policies if row.get("policy_id") == policy_id),
            None,
        )
        policy = by_id.get(str((equivalent or {}).get("representative_policy_id") or ""))
    if policy is None:
        return None
    return {str(key): float(value) for key, value in policy["weights"].items()}


def _risk_evaluation_contract(
    policies: Iterable[Mapping[str, Any]],
    equivalent_policies: Iterable[Mapping[str, Any]],
    *,
    risk_aversion: float,
) -> dict[str, Any]:
    aversion = require_finite(risk_aversion, "portfolio policy risk_aversion")
    if not 0 <= aversion <= 100:
        raise ValueError("portfolio policy risk_aversion must be in [0, 100]")
    enabled = all(
        _policy_weights(policies, equivalent_policies, policy_id) is not None
        for policy_id in (_RISK_CHALLENGER_ID, _RISK_COMPARATOR_ID)
    )
    body = {
        "schema": "jaggedthoughts-portfolio-risk-evaluation-contract-v1",
        "status": "enabled" if enabled else "unavailable_at_open",
        "challenger_policy_id": _RISK_CHALLENGER_ID,
        "comparator_policy_id": _RISK_COMPARATOR_ID,
        "path_rule": (
            "exact_common_observed_at_from_bound_entry_through_bound_exit;"
            "available_by_settlement"
        ),
        "price_identity": _RETURN_PRICE_IDENTITY,
        "minimum_path_observations": 3,
        "periods_per_year": 252,
        "round_trip_turnover_identity": "cash_to_frozen_weights_to_cash",
        "after_cost_utility": {
            "identity": "horizon_mean_variance_utility",
            "risk_aversion": aversion,
            "formula": "net_total_return-0.5*risk_aversion*annualized_volatility^2*horizon_years",
        },
        "loss_dimensions": [
            "realized_volatility",
            "drawdown_severity",
            "round_trip_turnover",
            "negative_after_cost_mean_variance_utility",
        ],
        "minimum_independent_blocks": 8,
        "automatic_policy_change": False,
        "authority": "evaluation_only",
        "capital_authority": False,
    }
    return {**body, "risk_evaluation_contract_sha256": stable_sha256(body)}


def _settle_risk_challenger_evaluation(
    run: Mapping[str, Any],
    *,
    series: Mapping[str, list[PricePoint]],
    binding: Mapping[str, Any],
    window: Mapping[str, Any],
    scores: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any] | None:
    contract = (run.get("settlement_contract") or {}).get("risk_challenger_evaluation")
    if not isinstance(contract, Mapping):
        return None
    if not _valid_hash(contract, "risk_evaluation_contract_sha256"):
        raise ValueError("portfolio risk-evaluation contract hash is invalid")
    common = {
        "schema": "jaggedthoughts-portfolio-risk-challenger-evaluation-v1",
        "risk_evaluation_contract_sha256": contract["risk_evaluation_contract_sha256"],
        "challenger_policy_id": contract["challenger_policy_id"],
        "comparator_policy_id": contract["comparator_policy_id"],
        "inference_block_id": run["inference_block_id"],
        "evaluated_at": window["evaluated_at"],
        "automatic_policy_change": False,
        "capital_authority": False,
    }
    if contract.get("status") != "enabled":
        body = {**common, "status": "unavailable_at_open"}
        return {**body, "risk_evaluation_sha256": stable_sha256(body)}

    policy_weights = {
        policy_id: _policy_weights(
            run.get("policies") or (), run.get("equivalent_policies") or (), policy_id,
        )
        for policy_id in (str(contract["challenger_policy_id"]), str(contract["comparator_policy_id"]))
    }
    if any(weights is None for weights in policy_weights.values()):
        raise ValueError("frozen risk-evaluation policies are unavailable")
    entity_ids = sorted({
        entity_id for weights in policy_weights.values() for entity_id in (weights or {})
    })
    entry_at = str(binding["entry_observed_at"])
    exit_at = str(window["exit_observed_at"])
    indexed = {
        entity_id: {
            point.observed_at: point
            for point in series.get(entity_id, ())
            if timestamp_key(entry_at) <= timestamp_key(point.observed_at) <= timestamp_key(exit_at)
        }
        for entity_id in entity_ids
    }
    for entity_id in entity_ids:
        entry = binding["entry_points"][entity_id]
        exit_point = window["exit_points"][entity_id]
        indexed[entity_id][entry_at] = PricePoint(
            entity_id=entity_id,
            observed_at=str(entry["observed_at"]),
            available_at=str(entry["available_at"]),
            value=float(entry["price"]),
            observation_id=str(entry["observation_id"]),
            source_ref=str(entry["source_ref"]),
        )
        indexed[entity_id][exit_at] = PricePoint(
            entity_id=entity_id,
            observed_at=str(exit_point["observed_at"]),
            available_at=str(exit_point["available_at"]),
            value=float(exit_point["price"]),
            observation_id=str(exit_point["observation_id"]),
            source_ref=str(exit_point["source_ref"]),
        )
    common_times = sorted(
        set.intersection(*(set(indexed[entity_id]) for entity_id in entity_ids)),
        key=timestamp_key,
    )
    minimum = int(contract["minimum_path_observations"])
    if len(common_times) < minimum or entry_at not in common_times or exit_at not in common_times:
        body = {
            **common,
            "status": "insufficient_path_observations",
            "observed_path_count": len(common_times),
            "minimum_path_observations": minimum,
        }
        return {**body, "risk_evaluation_sha256": stable_sha256(body)}

    start = datetime.fromisoformat(entry_at.replace("Z", "+00:00"))
    horizon_days = int(run["horizon_days"])
    annual_yield = float(run["cash_contract"]["annual_yield"])
    one_way_cost = float(run["settlement_contract"]["transaction_cost_bps"]) / 10_000.0
    periods_per_year = int(contract["periods_per_year"])
    risk_aversion = float(contract["after_cost_utility"]["risk_aversion"])
    rows = []
    for policy_id, raw_weights in policy_weights.items():
        weights = raw_weights or {}
        gross = sum(weights.values())
        wealth = [1.0]
        for observed_at in common_times:
            elapsed_days = max(0.0, (
                datetime.fromisoformat(observed_at.replace("Z", "+00:00")) - start
            ).total_seconds() / 86_400.0)
            cash_factor = (1.0 + annual_yield) ** (
                min(elapsed_days, float(horizon_days)) / 365.25
            )
            retention = (1.0 - one_way_cost) * (
                1.0 - one_way_cost if observed_at == exit_at else 1.0
            )
            wealth.append(
                (1.0 - gross) * cash_factor
                + sum(
                    weight
                    * indexed[entity_id][observed_at].value
                    / float(binding["entry_points"][entity_id]["price"])
                    * retention
                    for entity_id, weight in weights.items()
                )
            )
        expected_terminal = 1.0 + float(scores[policy_id]["portfolio_return_after_cost"])
        if not math.isclose(wealth[-1], expected_terminal, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError(f"risk path does not reconcile with settled return: {policy_id}")
        realized_returns = [right / left - 1.0 for left, right in zip(wealth, wealth[1:])]
        mean = sum(realized_returns) / len(realized_returns)
        variance = sum((value - mean) ** 2 for value in realized_returns) / max(
            1, len(realized_returns) - 1,
        )
        volatility = math.sqrt(variance * periods_per_year)
        peak = wealth[0]
        maximum_drawdown = 0.0
        for value in wealth[1:]:
            peak = max(peak, value)
            maximum_drawdown = min(maximum_drawdown, value / peak - 1.0)
        total_return = float(scores[policy_id]["portfolio_return_after_cost"])
        utility = total_return - 0.5 * risk_aversion * volatility ** 2 * (
            horizon_days / 365.25
        )
        rows.append({
            "policy_id": policy_id,
            "realized_volatility": volatility,
            "maximum_drawdown": maximum_drawdown,
            "round_trip_turnover": 2.0 * gross,
            "after_cost_mean_variance_utility": utility,
            "portfolio_return_after_cost": total_return,
            "terminal_wealth": wealth[-1],
        })
    by_policy = {row["policy_id"]: row for row in rows}
    challenger = by_policy[str(contract["challenger_policy_id"])]
    comparator = by_policy[str(contract["comparator_policy_id"])]
    path_points = sorted(
        (
            entity_id, observed_at, indexed[entity_id][observed_at].available_at,
            indexed[entity_id][observed_at].value,
            indexed[entity_id][observed_at].observation_id,
            indexed[entity_id][observed_at].source_ref,
        )
        for entity_id in entity_ids for observed_at in common_times
    )
    body = {
        **common,
        "status": "settled",
        "path_evidence": {
            "entity_ids": entity_ids,
            "entry_observed_at": entry_at,
            "exit_observed_at": exit_at,
            "synchronized_observation_count": len(common_times),
            "observation_ids_sha256": stable_sha256(path_points),
            "source_refs": sorted({
                indexed[entity_id][observed_at].source_ref
                for entity_id in entity_ids for observed_at in common_times
            }),
        },
        "policy_metrics": rows,
        "challenger_minus_comparator": {
            "realized_volatility": (
                challenger["realized_volatility"] - comparator["realized_volatility"]
            ),
            "maximum_drawdown": (
                challenger["maximum_drawdown"] - comparator["maximum_drawdown"]
            ),
            "round_trip_turnover": (
                challenger["round_trip_turnover"] - comparator["round_trip_turnover"]
            ),
            "after_cost_mean_variance_utility": (
                challenger["after_cost_mean_variance_utility"]
                - comparator["after_cost_mean_variance_utility"]
            ),
        },
    }
    return {**body, "risk_evaluation_sha256": stable_sha256(body)}


def _compile_risk_challenger_review(
    pairs: list[tuple[Mapping[str, Any], Mapping[str, Any]]],
) -> dict[str, Any]:
    evaluations = [
        settlement["risk_challenger_evaluation"]
        for _run, settlement in pairs
        if (settlement.get("risk_challenger_evaluation") or {}).get("status") == "settled"
    ]
    if not evaluations:
        return {
            "status": "awaiting_settled_path",
            "settled_independent_block_count": 0,
            "minimum_independent_blocks": 8,
            "automatic_policy_change": False,
            "capital_authority": False,
        }
    scores = []
    for run, settlement in pairs:
        evaluation = settlement.get("risk_challenger_evaluation") or {}
        if evaluation.get("status") != "settled":
            continue
        for row in evaluation["policy_metrics"]:
            scores.append(EvaluationScore(
                model_id=str(row["policy_id"]),
                episode_id=str(run["run_id"]),
                inference_block_id=str(settlement["inference_block_id"]),
                losses={
                    "realized_volatility": float(row["realized_volatility"]),
                    "drawdown_severity": -float(row["maximum_drawdown"]),
                    "round_trip_turnover": float(row["round_trip_turnover"]),
                    "negative_after_cost_mean_variance_utility": -float(
                        row["after_cost_mean_variance_utility"]
                    ),
                },
            ))
    survivor = conservative_paired_survivor_set(
        scores=scores,
        model_ids=(_RISK_CHALLENGER_ID, _RISK_COMPARATOR_ID),
        episode_ids=(
            str(run["run_id"])
            for run, settlement in pairs
            if (settlement.get("risk_challenger_evaluation") or {}).get("status") == "settled"
        ),
        dimensions=(
            "realized_volatility", "drawdown_severity", "round_trip_turnover",
            "negative_after_cost_mean_variance_utility",
        ),
        min_inference_blocks=8,
    )
    body = {
        "status": (
            "eligible_for_research_review"
            if survivor["inference_sufficient"] else "collecting_independent_blocks"
        ),
        "settled_independent_block_count": survivor["inference_block_count"],
        "minimum_independent_blocks": survivor["min_inference_blocks"],
        "survivor_set": survivor,
        "statistical_survivor_policy_id": (
            survivor["survivor_model_ids"][0]
            if survivor["inference_sufficient"] and len(survivor["survivor_model_ids"]) == 1
            else None
        ),
        "automatic_policy_change": False,
        "capital_authority": False,
    }
    return {**body, "risk_challenger_review_sha256": stable_sha256(body)}


def _compile_policy_review(
    family: Mapping[str, Any],
    pairs: list[tuple[Mapping[str, Any], Mapping[str, Any]]],
) -> dict[str, Any]:
    policy_ids = tuple(sorted((family.get("policy_versions") or {}).keys()))
    scores = []
    for run, settlement in pairs:
        expanded = _expanded_policy_scores(run, settlement)
        if set(expanded) != set(policy_ids):
            raise ValueError("portfolio policy review requires a complete trial-family score matrix")
        for policy_id in policy_ids:
            row = expanded[policy_id]
            scores.append(EvaluationScore(
                model_id=policy_id,
                episode_id=str(run["run_id"]),
                inference_block_id=str(settlement["inference_block_id"]),
                losses={
                    "negative_portfolio_excess_return_after_cost": -float(
                        row["portfolio_excess_return_after_cost"]
                    ),
                    "negative_selection_active_contribution_after_cost": -float(
                        row["selection_active_contribution_after_cost"]
                    ),
                },
            ))
    survivor = conservative_paired_survivor_set(
        scores=scores,
        model_ids=policy_ids,
        episode_ids=(str(run["run_id"]) for run, _settlement in pairs),
        dimensions=(
            "negative_portfolio_excess_return_after_cost",
            "negative_selection_active_contribution_after_cost",
        ),
        min_inference_blocks=8,
    )
    is_primary = (
        int(family.get("horizon_days") or 0) == PRIMARY_HORIZON_DAYS
        and family.get("estimand_role") == "primary_patient_capital_policy_evidence"
    )
    promotion_ineligible = {
        str(policy["policy_id"])
        for run, _settlement in pairs
        for policy in (*run.get("policies", ()), *run.get("equivalent_policies", ()))
        if policy.get("promotion_eligible_under_current_score_contract") is False
    }
    unique = (
        survivor["survivor_model_ids"][0]
        if is_primary
        and survivor["inference_sufficient"]
        and len(survivor["survivor_model_ids"]) == 1
        and survivor["survivor_model_ids"][0] not in promotion_ineligible
        else None
    )
    diagnostic_only_survivor = bool(
        is_primary
        and survivor["inference_sufficient"]
        and len(survivor["survivor_model_ids"]) == 1
        and survivor["survivor_model_ids"][0] in promotion_ineligible
    )
    sensitivities = [
        settlement["transaction_cost_sensitivity"]
        for _run, settlement in pairs
        if isinstance(settlement.get("transaction_cost_sensitivity"), Mapping)
    ]
    comparable_orderings = [
        row["ordering"]["stable_across_grid"] for row in sensitivities
        if (row.get("ordering") or {}).get("stable_across_grid") is not None
    ]
    body = {
        "schema": PORTFOLIO_POLICY_REVIEW_SCHEMA,
        "trial_family": dict(family),
        "run_ids": [str(run["run_id"]) for run, _settlement in pairs],
        "last_evaluated_at": max(
            str(settlement["evaluated_at"]) for _run, settlement in pairs
        ),
        "settlement_sha256s": [
            str(settlement["settlement_sha256"]) for _run, settlement in pairs
        ],
        "survivor_set": survivor,
        "recommended_policy_id": unique,
        "promotion_ineligible_policy_ids": sorted(promotion_ineligible),
        "activation_status": (
            "diagnostic_horizon_only"
            if not is_primary else
            "collecting_independent_blocks"
            if not survivor["inference_sufficient"] else
            "diagnostic_survivor_requires_risk_outcomes"
            if diagnostic_only_survivor else
            "eligible_for_paper_policy_review"
            if unique else
            "no_unique_statistical_survivor"
        ),
        "transaction_cost_sensitivity": {
            "transaction_cost_bps_grid": list(_TRANSACTION_COST_SENSITIVITY_BPS),
            "settled_episode_count": len(sensitivities),
            "comparable_episode_count": len(comparable_orderings),
            "stable_episode_count": sum(bool(value) for value in comparable_orderings),
            "ordering_stable_in_all_comparable_episodes": (
                all(comparable_orderings) if comparable_orderings else None
            ),
        },
        "risk_challenger_evaluation": _compile_risk_challenger_review(pairs),
        "automatic_policy_change": False,
        "capital_authority": False,
    }
    return {**body, "policy_review_sha256": stable_sha256(body)}


def _paper_policy_incumbent_routing(
    *, trial_family: Mapping[str, Any], policies: Iterable[Mapping[str, Any]],
    equivalent_policies: Iterable[Mapping[str, Any]],
    reviews: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Route one exact-family settled survivor into the next shadow tournament."""

    def family_identity(raw: Mapping[str, Any]) -> str:
        claimed = str(raw.get("trial_family_id") or "")
        body = {key: value for key, value in raw.items() if key != "trial_family_id"}
        return claimed if claimed and stable_sha256(body) == claimed else ""

    family_id = family_identity(trial_family)
    matches = [
        dict(review) for review in reviews
        if review.get("schema") == PORTFOLIO_POLICY_REVIEW_SCHEMA
        and _valid_hash(review, "policy_review_sha256")
        and family_identity(review.get("trial_family") or {}) == family_id
    ] if family_id else []
    review = matches[0] if len(matches) == 1 else None
    recommended = str((review or {}).get("recommended_policy_id") or "")
    settlement_shas = list(map(str, (review or {}).get("settlement_sha256s") or ()))
    representatives = {str(row["policy_id"]): dict(row) for row in policies}
    aliases = {
        str(row["policy_id"]): str(row["representative_policy_id"])
        for row in equivalent_policies
    }
    selected = representatives.get(aliases.get(recommended, recommended))
    eligible = bool(
        review
        and review.get("activation_status") == "eligible_for_paper_policy_review"
        and review.get("automatic_policy_change") is False
        and review.get("capital_authority") is False
        and len(set(settlement_shas)) >= 8
        and all(len(value) == 64 for value in settlement_shas)
        and selected
        and _valid_hash(selected, "policy_sha256")
    )
    body = {
        "schema": "jaggedthoughts-paper-policy-incumbent-routing-v1",
        "status": "settled_survivor_incumbent" if eligible else "no_eligible_exact_family_survivor",
        "trial_family_id": family_id,
        "recommended_policy_id": recommended if eligible else None,
        "selected_policy_id": str(selected["policy_id"]) if eligible else None,
        "selected_policy_sha256": str(selected["policy_sha256"]) if eligible else None,
        "weights": dict(selected["weights"]) if eligible else {},
        "source_policy_review_sha256": (
            str(review["policy_review_sha256"]) if eligible else None
        ),
        "source_settlement_sha256s": (
            settlement_shas if eligible else []
        ),
        "routing_scope": "next_prospective_paper_shadow_tournament_only",
        "automatic_live_policy_change": False,
        "capital_authority": False,
    }
    return {**body, "routing_sha256": stable_sha256(body)}


def _attribution_contract(
    policies: Iterable[Mapping[str, Any]], universe: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    policies = tuple(policies)
    candidates = {str(row["entity_id"]).upper(): row for row in universe}
    reference = next((row for row in policies if row.get("policy_id") in {
        "equity_equal_weight", "equal_weight_qualified",
    }), None)
    if reference is None:
        raise ValueError("portfolio policy attribution requires the equal-weight reference")
    by_policy = {str(row["policy_id"]): row for row in policies}
    equal_weight_id = str(reference["policy_id"])
    desired_references = {
        "cash_control": equal_weight_id,
        "equity_discovery_priority": "equity_equal_weight",
        "equity_minimum_variance": "equity_equal_weight",
        "equity_walk_forward_ridge_minimum_variance": "equity_minimum_variance",
        "equity_learned_law_priority": "equity_discovery_priority",
        "equity_factor_implied_return_control": "equity_equal_weight",
        "equity_fully_gated_equal_weight": "equity_equal_weight",
        "operator_active_book": "equity_discovery_priority",
        "nominal_assembly": "equity_equal_weight",
        "mechanism_safe_assembly": "nominal_assembly",
        "discovery_priority": equal_weight_id,
        "learned_law_priority": "discovery_priority",
        "factor_implied_return_control": equal_weight_id,
    }
    comparisons = []
    rows = []
    for policy in policies:
        policy_id = str(policy["policy_id"])
        if policy_id == reference["policy_id"]:
            continue
        reference_id = (
            "cash_control" if policy_id.startswith("fund_admission:")
            else desired_references.get(policy_id, str(reference["policy_id"]))
        )
        if reference_id not in by_policy:
            reference_id = str(reference["policy_id"])
        comparison_id = f"{policy_id}__vs__{reference_id}"
        comparison_weights = {
            str(key): float(value)
            for key, value in by_policy[reference_id]["weights"].items()
        }
        comparisons.append({
            "comparison_id": comparison_id,
            "policy_id": policy_id,
            "reference_policy_id": reference_id,
        })
        weights = {str(key): float(value) for key, value in policy["weights"].items()}
        for entity_id, candidate in sorted(candidates.items()):
            delta = weights.get(entity_id, 0.0) - comparison_weights.get(entity_id, 0.0)
            if abs(delta) <= 1e-12:
                continue
            influence = candidate.get("law_policy_influence") or {}
            causal_influence = candidate.get("causal_law_target_influence") or {}
            rows.append({
                "comparison_id": comparison_id,
                "policy_id": policy_id,
                "reference_policy_id": reference_id,
                "entity_id": entity_id,
                "candidate_sha256": candidate["candidate_sha256"],
                "reference_weight": comparison_weights.get(entity_id, 0.0),
                "policy_weight": weights.get(entity_id, 0.0),
                "delta_weight_vs_reference": delta,
                "discovery_priority_score": candidate.get("research_priority_score"),
                "learned_priority_score": candidate.get("learned_research_priority_score"),
                "law_contributions": list(influence.get("contributions") or ()),
                "causal_law_influence_sha256s": list(
                    causal_influence.get("influence_sha256s") or ()
                ),
                "research_question": str((candidate.get("research") or {}).get("research_prompt") or ""),
                "source_refs": sorted(set(candidate.get("source_refs") or ())),
            })
    body = {
        "reference_policy_id": reference["policy_id"],
        "identity": "frozen_weight_delta_to_later_active_return",
        "comparisons": comparisons,
        "rows": rows,
        "boundary": (
            "This is exact decision-path accounting. Shared sources and questions do not "
            "receive causal credit without separately varied prospective policies."
        ),
        "capital_authority": False,
    }
    return {**body, "attribution_sha256": stable_sha256(body)}


def _run_attribution_contract(root: Path, run: Mapping[str, Any]) -> dict[str, Any]:
    frozen = run.get("attribution_contract")
    if isinstance(frozen, Mapping) and frozen.get("comparisons"):
        return dict(frozen)
    book_sha = str(run.get("opportunity_book_sha256") or "")
    book = next(
        (
            row for path in (root / "opportunity_books").glob("*.json")
            if (row := _read_json(path)) and row.get("book_sha256") == book_sha
        ),
        None,
    )
    frozen_candidates = {
        str(row["candidate_sha256"]): row for row in run.get("universe") or ()
    }
    candidates = [
        row for row in (book or {}).get("candidates") or ()
        if str(row.get("candidate_sha256") or "") in frozen_candidates
    ]
    if len(candidates) != len(frozen_candidates):
        candidates = [{
            "entity_id": row["entity_id"],
            "candidate_sha256": row["candidate_sha256"],
            "research_priority_score": None,
            "learned_research_priority_score": None,
            "law_policy_influence": {},
            "research": {},
            "source_refs": (),
        } for row in run.get("universe") or ()]
    return _attribution_contract(run["policies"], candidates)


def open_portfolio_policy_tournament(
    root: Path,
    *,
    owner: str,
    store_path: Path,
    opportunity_book: Mapping[str, Any],
    horizon_days: int = PRIMARY_HORIZON_DAYS,
    benchmark_id: str = "SPY",
    generated_at: str | None = None,
    gross_weight: float = 0.50,
    max_position_weight: float = 0.15,
    transaction_cost_bps: float = 10.0,
    risk_aversion: float = 3.0,
    portfolio_assembly: Mapping[str, Any] | None = None,
    fund_program_tournament_input: Mapping[str, Any] | None = None,
    paper_proposal_audits: Iterable[Mapping[str, Any]] = (),
    instrument_portfolio_admissions: Mapping[str, Any] | None = None,
    sealed_at: str | None = None,
) -> dict[str, Any]:
    """Freeze one common-universe tournament without assigning capital authority."""

    if horizon_days < 7 or horizon_days > 730:
        raise ValueError("portfolio policy horizon_days must be in [7, 730]")
    opened_at = canonical_timestamp(generated_at or _utc_now(), "portfolio policy opened_at")
    if not _valid_hash(opportunity_book, "book_sha256"):
        raise ValueError("opportunity book hash is invalid")
    book_generated_at = canonical_timestamp(
        opportunity_book.get("generated_at"), "opportunity book generated_at",
    )
    if timestamp_key(book_generated_at) > timestamp_key(opened_at):
        raise ValueError("opportunity book was unavailable at the source cutoff")
    end_at = (
        datetime.fromisoformat(opened_at.replace("Z", "+00:00")) + timedelta(days=horizon_days)
    ).isoformat(timespec="seconds").replace("+00:00", "Z")
    base = root / "portfolio_policy"
    superseded_priors: list[dict[str, Any]] = []
    for path in (base / "runs").glob("*.json"):
        prior = _read_json(path)
        if not prior or not _valid_hash(prior, "run_sha256"):
            continue
        run_id = str(prior["run_id"])
        if (
            (base / "settlements" / f"{run_id}.json").is_file()
            or _supersession_path(base, run_id).is_file()
        ):
            continue
        overlaps = (
            int(prior.get("horizon_days") or 0) == horizon_days
            and timestamp_key(str(prior.get("end_at") or "")) > timestamp_key(opened_at)
        )
        if overlaps and _current_run_identity(prior):
            return {**prior, "ok": True, "activation_status": "blocked_overlap", "replayed": True}
        if not _current_run_identity(prior) and not _entry_is_bound(base, run_id):
            superseded_priors.append(prior)
    benchmark = benchmark_id.upper()
    priced_scope = {
        benchmark,
        *(
            str(candidate.get("entity_id") or "").upper()
            for candidate in opportunity_book.get("candidates") or ()
            if candidate.get("screen_status") == "qualified"
        ),
        *(
            str(program.get("entity_id") or "").upper()
            for sleeve in (fund_program_tournament_input or {}).get("sleeves") or ()
            for program in sleeve.get("programs") or ()
        ),
    }
    series = _price_series(root, opened_at, priced_scope)
    if not series.get(benchmark):
        raise ValueError(f"portfolio policy benchmark price unavailable: {benchmark}")
    universe: list[dict[str, Any]] = []
    excluded: list[dict[str, str]] = []
    for candidate in opportunity_book.get("candidates") or ():
        if candidate.get("screen_status") != "qualified":
            continue
        entity_id = str(candidate.get("entity_id") or "").upper()
        if not series.get(entity_id):
            excluded.append({"entity_id": entity_id, "reason": "start_price_unavailable"})
            continue
        universe.append({**dict(candidate), "entity_id": entity_id})
    if len(universe) < 2:
        raise ValueError("portfolio policy tournament requires two qualified priced candidates")
    if not any(row.get("entity_kind") == "public_equity" for row in universe):
        raise ValueError("portfolio policy tournament requires a qualified priced public equity")
    proposal_audits = tuple(
        dict(row) for row in paper_proposal_audits
        if row.get("schema") == "jaggedthoughts-public-equity-paper-proposal-audit-v1"
    )
    allocation_ids = [
        str(row["entity_id"]) for row in universe
        if row.get("entity_kind") == "public_equity"
    ]
    risk_model = None
    risk_challenger = None
    risk_model_exclusion = None
    risk_challenger_exclusion = None
    try:
        risk_model = _risk_model(series, allocation_ids, as_of=opened_at)
    except ValueError as exc:
        risk_model_exclusion = {
            "policy_id": "equity_minimum_variance",
            "reason": "return_covariance_unavailable",
            "detail": str(exc),
        }
    if risk_model is not None:
        try:
            risk_challenger = compile_walk_forward_ridge_risk_challenger(
                price_series={
                    entity_id: {point.date_key: point.value for point in series[entity_id]}
                    for entity_id in allocation_ids
                },
                as_of=opened_at,
                source_risk_model_sha256=str(risk_model["risk_model_sha256"]),
                gross_weight=gross_weight,
                maximum_weight=max_position_weight,
            )
        except ValueError as exc:
            risk_challenger_exclusion = {
                "policy_id": "equity_walk_forward_ridge_minimum_variance",
                "reason": "chronological_risk_selection_unavailable",
                "detail": str(exc),
            }
    policies, equivalence, policy_exclusions = _candidate_policies(
        opportunity_book,
        universe,
        gross=gross_weight,
        maximum=max_position_weight,
        opened_at=opened_at,
        horizon_days=horizon_days,
        benchmark_id=benchmark,
        portfolio_assembly=portfolio_assembly,
        paper_proposal_audits=proposal_audits,
        risk_model=risk_model,
        risk_challenger=risk_challenger,
        instrument_portfolio_admissions=instrument_portfolio_admissions,
    )
    if risk_model_exclusion:
        policy_exclusions.append(risk_model_exclusion)
    if risk_challenger_exclusion:
        policy_exclusions.append(risk_challenger_exclusion)
    ranking_tickets = _ranking_tickets(
        opportunity_book, universe, opened_at=opened_at, end_at=end_at,
        benchmark_id=benchmark,
    )
    fund_tickets, fund_universe, fund_exclusions = _fund_program_ranking_tickets(
        fund_program_tournament_input, series=series, opened_at=opened_at,
        end_at=end_at, benchmark_id=benchmark,
    )
    ranking_tickets.extend(fund_tickets)
    attribution = _attribution_contract(policies, universe)
    annual_cash, cash_source = _cash_yield(root, horizon_days, as_of=opened_at)
    sealed = canonical_timestamp(sealed_at or _utc_now(), "portfolio policy sealed_at")
    if timestamp_key(sealed) < timestamp_key(opened_at):
        raise ValueError("portfolio policy seal cannot precede opening")
    observed_entity_ids = tuple(dict.fromkeys((
        benchmark,
        *(str(row["entity_id"]) for row in universe),
        *(str(row["entity_id"]) for row in fund_universe),
    )))
    return_window = compile_prospective_return_window(
        sealed_at=sealed, horizon_days=horizon_days,
        entity_ids=observed_entity_ids,
        transaction_cost_bps=transaction_cost_bps,
        price_identity=_RETURN_PRICE_IDENTITY,
    )
    risk_evaluation = _risk_evaluation_contract(
        policies, equivalence, risk_aversion=risk_aversion,
    )
    estimand_role = _estimand_role(horizon_days)
    settlement_contract = {
        "score_contract_version": _SCORE_CONTRACT_VERSION,
        "prospective_return_window": return_window,
        "transaction_cost_bps": transaction_cost_bps,
        "cost_application": _COST_APPLICATION,
        "primary_outcome": "portfolio_excess_return_after_cost",
        "ranking_outcomes": [
            "mean_absolute_rank_percentile_error",
            "top_1_active_return_regret",
        ],
        "factor_comparator_claim_id": "factor_implied_return_control",
        "minimum_inference_blocks": 8,
        "risk_comparator_promotion_contract": {
            "policy_id": "equity_minimum_variance",
            "current_status": "diagnostic_only",
            "required_unscored_outcomes": [
                "realized_volatility", "maximum_drawdown", "turnover",
            ],
        },
        "walk_forward_ridge_promotion_contract": {
            "policy_id": "equity_walk_forward_ridge_minimum_variance",
            "current_status": "diagnostic_only",
            "minimum_independent_blocks": 8,
            "required_unscored_outcomes": [
                "realized_volatility", "maximum_drawdown", "turnover",
            ],
        },
        "risk_challenger_evaluation": risk_evaluation,
    }
    trial_family = _trial_family({
        "policies": policies,
        "equivalent_policies": equivalence,
        "horizon_days": horizon_days,
        "estimand_role": estimand_role,
        "benchmark": {"entity_id": benchmark},
        "settlement_contract": settlement_contract,
    })
    prior_reviews = (
        (portfolio_policy_status(root).get("scoreboard") or {}).get("policy_reviews") or ()
    )
    incumbent_routing = _paper_policy_incumbent_routing(
        trial_family=trial_family, policies=policies,
        equivalent_policies=equivalence, reviews=prior_reviews,
    )
    incumbent_sha = str(incumbent_routing.get("selected_policy_sha256") or "")
    if incumbent_sha:
        policies.sort(key=lambda row: row.get("policy_sha256") != incumbent_sha)
    run_identity = {
        "book_sha256": opportunity_book["book_sha256"],
        "opened_at": opened_at,
        "horizon_days": horizon_days,
        "estimand_role": estimand_role,
        "policy_version": _POLICY_VERSION,
        "score_contract_version": _SCORE_CONTRACT_VERSION,
        "return_window_sha256": return_window["return_window_sha256"],
        "policy_sha256s": [row["policy_sha256"] for row in policies],
        "risk_model_sha256": str((risk_model or {}).get("risk_model_sha256") or ""),
        "risk_challenger_sha256": str(
            (risk_challenger or {}).get("risk_challenger_sha256") or ""
        ),
        "risk_evaluation_contract_sha256": risk_evaluation[
            "risk_evaluation_contract_sha256"
        ],
        "paper_policy_incumbent_routing_sha256": incumbent_routing["routing_sha256"],
        "portfolio_assembly_sha256": str(
            (portfolio_assembly or {}).get("portfolio_assembly_sha256") or ""
        ),
        "fund_program_tournament_input_sha256": str(
            (fund_program_tournament_input or {}).get("tournament_input_sha256") or ""
        ),
        "paper_proposal_audit_sha256s": sorted(
            str(row.get("audit_sha256") or "") for row in proposal_audits
        ),
        "instrument_portfolio_admissions_sha256": str(
            (instrument_portfolio_admissions or {}).get(
                "workspace_admissions_sha256"
            ) or ""
        ),
    }
    run_id = f"portfolio-policy-{stable_sha256(run_identity)[:20]}"
    body = {
        "schema": PORTFOLIO_POLICY_RUN_SCHEMA,
        "run_id": run_id,
        "status": "pending_outcome",
        "opened_at": opened_at,
        "sealed_at": sealed,
        "end_at": end_at,
        "horizon_days": horizon_days,
        "estimand_role": estimand_role,
        "inference_block_id": stable_sha256({
            "issue_date": opened_at[:10], "horizon_days": horizon_days, "benchmark_id": benchmark,
        }),
        "opportunity_book_id": opportunity_book["book_id"],
        "opportunity_book_sha256": opportunity_book["book_sha256"],
        "benchmark": {"entity_id": benchmark, "start": _point_dict(series[benchmark][-1])},
        "universe": [
            {
                "entity_id": row["entity_id"], "entity_kind": row["entity_kind"],
                "candidate_id": row["candidate_id"], "candidate_sha256": row["candidate_sha256"],
                "start": _point_dict(series[str(row["entity_id"]).upper()][-1]),
            }
            for row in universe
        ],
        "allocation_universe": {
            "identity": "public_equity_satellite",
            "entity_ids": [
                row["entity_id"] for row in universe
                if row.get("entity_kind") == "public_equity"
            ],
            "fund_boundary": (
                "one_fund_at_a_time_capped_shadow_sleeve_challengers;"
                "no_cross_fund_or_equity_fund_mixing"
            ),
            "fund_shadow_policy_ids": [
                row["policy_id"] for row in policies
                if str(row["policy_id"]).startswith("fund_admission:")
            ],
            "household_boundary": "broad_sleeve_allocation_owned_by_household_mandate",
        },
        "instrument_portfolio_admissions_sha256": str(
            (instrument_portfolio_admissions or {}).get(
                "workspace_admissions_sha256"
            ) or ""
        ),
        "excluded": excluded,
        "fund_program_universe": fund_universe,
        "fund_program_excluded": fund_exclusions,
        "observed_entity_ids": list(observed_entity_ids),
        "policies": policies,
        "equivalent_policies": equivalence,
        "policy_exclusions": policy_exclusions,
        "risk_model": risk_model,
        "risk_challenger": risk_challenger,
        "ranking_tickets": ranking_tickets,
        "attribution_contract": attribution,
        "paper_policy_incumbent_routing": incumbent_routing,
        "cash_contract": {"annual_yield": annual_cash, "source_ref": cash_source},
        "settlement_contract": settlement_contract,
        "authority": "prospective_shadow",
        "capital_authority": False,
    }
    body["trial_family"] = trial_family
    run = {**body, "run_sha256": stable_sha256(body)}
    path = base / "runs" / f"{run_id}.json"
    _atomic_json(path, run)
    leaf = GoldenLeaf(
        owner=owner, object_kind="portfolio_policy_run", object_id=run_id,
        epoch=run["run_sha256"], occurred_at=opened_at, available_at=sealed,
        payload=run,
        source_refs=tuple(ref for ref in (
            f"opportunity-book:{opportunity_book['book_sha256']}",
            (
                f"portfolio-policy-review:{incumbent_routing['source_policy_review_sha256']}"
                if incumbent_routing.get("source_policy_review_sha256") else ""
            ),
            (
                f"fund-program-input:"
                f"{(fund_program_tournament_input or {}).get('tournament_input_sha256')}"
                if (fund_program_tournament_input or {}).get("tournament_input_sha256")
                else ""
            ),
            cash_source,
            str((portfolio_assembly or {}).get("portfolio_assembly_sha256") or ""),
            str((instrument_portfolio_admissions or {}).get(
                "workspace_admissions_sha256"
            ) or ""),
            (
                f"portfolio-policy-risk-model:{risk_model['risk_model_sha256']}"
                if risk_model else ""
            ),
            (
                f"portfolio-risk-challenger:{risk_challenger['risk_challenger_sha256']}"
                if risk_challenger else ""
            ),
            *(str(row.get("audit_sha256") or "") for row in proposal_audits),
        ) if ref),
    )
    GoldenStore(store_path).append_bundle((leaf,), (), make_heads=True)
    for prior in superseded_priors:
        supersession_body = {
            "schema": "jaggedthoughts-portfolio-policy-supersession-v1",
            "prior_run_id": prior["run_id"],
            "prior_run_sha256": prior["run_sha256"],
            "successor_run_id": run_id,
            "successor_run_sha256": run["run_sha256"],
            "recorded_at": sealed,
            "reason": "incompatible_policy_or_return_identity_superseded_before_entry_binding",
            "capital_authority": False,
        }
        supersession = {
            **supersession_body,
            "supersession_sha256": stable_sha256(supersession_body),
        }
        _atomic_json(_supersession_path(base, str(prior["run_id"])), supersession)
        GoldenStore(store_path).append_leaf(GoldenLeaf(
            owner=owner, object_kind="portfolio_policy_supersession",
            object_id=str(prior["run_id"]), epoch=supersession["supersession_sha256"],
            occurred_at=sealed, available_at=sealed, payload=supersession,
            source_refs=(
                f"portfolio-policy-run:{prior['run_sha256']}",
                f"portfolio-policy-run:{run['run_sha256']}",
            ),
        ))
    return {
        **run, "ok": True, "replayed": False,
        "run_path": path.relative_to(root).as_posix(),
        "golden_leaf_sha256": leaf.leaf_sha256,
        "superseded_run_ids": [str(row["run_id"]) for row in superseded_priors],
    }


def _horizon_return(annual_yield: float, horizon_days: int) -> float:
    return (1.0 + annual_yield) ** (horizon_days / 365.25) - 1.0


def _persist_policy_reviews(
    root: Path,
    *,
    owner: str,
    store_path: Path,
    reviews: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    recorded = []
    store = GoldenStore(store_path)
    for raw in reviews:
        review = dict(raw)
        family_id = str((review.get("trial_family") or {})["trial_family_id"])
        path = root / "portfolio_policy" / "reviews" / f"{family_id}.json"
        prior = _read_json(path)
        if prior and prior.get("policy_review_sha256") == review.get("policy_review_sha256"):
            recorded.append({"trial_family_id": family_id, "status": "replayed"})
            continue
        _atomic_json(path, review)
        leaf = GoldenLeaf(
            owner=owner,
            object_kind="portfolio_policy_review",
            object_id=family_id,
            epoch=str(review["policy_review_sha256"]),
            occurred_at=str(review["last_evaluated_at"]),
            available_at=str(review["last_evaluated_at"]),
            payload=review,
            source_refs=tuple(str(row) for row in review.get("settlement_sha256s") or ()),
        )
        edges = []
        for run_id in review.get("run_ids") or ():
            try:
                settlement_leaf = store.head(
                    owner, "portfolio_policy_settlement", f"{run_id}::settlement",
                )
            except KeyError:
                continue
            edges.append(GoldenEdge(
                leaf.leaf_sha256, str(settlement_leaf["leaf_sha256"]), "derived_from",
            ))
        store.append_bundle((leaf,), tuple(edges), make_heads=True)
        recorded.append({
            "trial_family_id": family_id,
            "status": "recorded",
            "policy_review_sha256": review["policy_review_sha256"],
            "golden_leaf_sha256": leaf.leaf_sha256,
        })
    return recorded


def settle_portfolio_policy_tournaments(
    root: Path, *, owner: str, store_path: Path, as_of: str | None = None,
) -> dict[str, Any]:
    """Settle due complete-policy blocks from one later point-in-time price store."""

    evaluated_at = canonical_timestamp(as_of or _utc_now(), "portfolio policy settlement as_of")
    price_scope: set[str] = set()
    for path in sorted((root / "portfolio_policy" / "runs").glob("*.json")):
        run = _read_json(path)
        if (
            not run
            or (root / "portfolio_policy" / "settlements" / f"{run.get('run_id')}.json").is_file()
        ):
            continue
        price_scope.update({
            str((run.get("benchmark") or {}).get("entity_id") or "").upper(),
            *(str(row.get("entity_id") or "").upper() for row in run.get("universe") or ()),
            *(str(row.get("entity_id") or "").upper() for row in run.get("fund_program_universe") or ()),
        })
    series = _price_series(root, evaluated_at, price_scope)
    settled: list[dict[str, Any]] = []
    pending: list[dict[str, str]] = []
    base = root / "portfolio_policy"
    for path in sorted((base / "runs").glob("*.json")):
        run = _read_json(path)
        if not run or run.get("schema") != PORTFOLIO_POLICY_RUN_SCHEMA:
            continue
        if not _valid_hash(run, "run_sha256"):
            raise ValueError(f"portfolio policy run hash is invalid: {run.get('run_id')}")
        run_id = str(run["run_id"])
        if _supersession_path(base, run_id).is_file():
            continue
        if not _current_run_identity(run) and not _entry_is_bound(base, run_id):
            continue
        settlement_path = base / "settlements" / f"{run_id}.json"
        prior = _read_json(settlement_path)
        if prior:
            if not _valid_hash(prior, "settlement_sha256"):
                raise ValueError(f"portfolio policy settlement hash is invalid: {run['run_id']}")
            settled.append(prior)
            continue
        contract = dict(
            (run.get("settlement_contract") or {}).get("prospective_return_window") or {}
        )
        required = list(dict.fromkeys((
            str(run["benchmark"]["entity_id"]),
            *(str(row["entity_id"]) for row in run["universe"]),
            *(str(row["entity_id"]) for row in run.get("fund_program_universe") or ()),
        )))
        binding_path = base / "return_windows" / f"{run_id}.json"
        prior_binding = _read_json(binding_path)
        reusable_binding = bool(
            prior_binding and isinstance(prior_binding.get("binding"), Mapping)
            and (prior_binding["binding"]).get("schema") == RETURN_WINDOW_BINDING_SCHEMA
            and (prior_binding["binding"]).get("return_window_sha256") == contract.get("return_window_sha256")
        )
        binding = (
            dict(prior_binding["binding"])
            if reusable_binding
            else bind_prospective_return_window(
                contract, points={key: series.get(key, ()) for key in required},
                as_of=evaluated_at,
            )
        )
        if binding["status"] != "bound":
            pending.append({"run_id": str(run["run_id"]), "reason": "entry_price_unavailable"})
            continue
        if not reusable_binding:
            envelope = {
                "schema": "jaggedthoughts-prospective-return-window-binding-envelope-v1",
                "contract": contract, "binding": binding,
            }
            _atomic_json(binding_path, envelope)
            leaf = GoldenLeaf(
                owner=owner, object_kind="prospective_return_window_binding",
                object_id=f"{run['run_id']}::return-window",
                epoch=str(contract["return_window_sha256"]),
                occurred_at=str(binding["entry_observed_at"]),
                available_at=str(binding["evaluated_at"]), payload=envelope,
                source_refs=tuple(sorted({
                    str(row["source_ref"]) for row in binding["entry_points"].values()
                })),
            )
            try:
                run_leaf = GoldenStore(store_path).head(
                    owner, "portfolio_policy_run", str(run["run_id"]),
                )
                edges = (GoldenEdge(leaf.leaf_sha256, str(run_leaf["leaf_sha256"]), "derived_from"),)
            except KeyError:
                edges = ()
            GoldenStore(store_path).append_bundle((leaf,), edges, make_heads=True)
        window = settle_prospective_return_window(
            contract, binding, points={key: series.get(key, ()) for key in required},
            as_of=evaluated_at,
        )
        if window["status"] != "settled":
            reason = (
                "horizon_not_reached"
                if timestamp_key(str(binding["scheduled_exit_at"])) > timestamp_key(evaluated_at)
                else "outcome_price_unavailable"
            )
            pending.append({"run_id": str(run["run_id"]), "reason": reason})
            continue
        complete_ends = {
            key: PricePoint(
                entity_id=value["entity_id"], observed_at=value["observed_at"],
                available_at=value["available_at"], value=float(value["price"]),
                observation_id=value["observation_id"], source_ref=value["source_ref"],
            )
            for key, value in window["exit_points"].items()
        }
        benchmark_id = str(run["benchmark"]["entity_id"])
        benchmark_return = float(window["returns"][benchmark_id])
        returns = {
            entity_id: float(window["returns"][entity_id])
            for entity_id in required if entity_id != benchmark_id
        }
        cash_return = _horizon_return(float(run["cash_contract"]["annual_yield"]), int(run["horizon_days"]))
        scores = []
        for policy in run["policies"]:
            weights = {str(key): float(value) for key, value in policy["weights"].items()}
            gross = sum(weights.values())
            one_way_cost = float(run["settlement_contract"]["transaction_cost_bps"]) / 10_000
            embedded_cost = gross * (1.0 - (1.0 - one_way_cost) ** 2)
            portfolio_return = (1.0 - gross) * cash_return + sum(
                weight * returns[entity_id] for entity_id, weight in weights.items()
            )
            scores.append({
                "policy_id": policy["policy_id"],
                "policy_sha256": policy["policy_sha256"],
                "portfolio_return_after_cost": portfolio_return,
                "portfolio_excess_return_after_cost": portfolio_return - benchmark_return,
                "selection_active_contribution_after_cost": sum(
                    weight * (returns[entity_id] - benchmark_return)
                    for entity_id, weight in weights.items()
                ),
                "cash_return": cash_return,
                "transaction_cost": embedded_cost,
                "transaction_cost_bps_included_in_asset_returns": float(
                    run["settlement_contract"]["transaction_cost_bps"]
                ),
            })
        by_policy = {str(row["policy_id"]): row for row in scores}
        attribution_contract = _run_attribution_contract(root, run)
        attribution_rows = attribution_contract.get("rows") or ()
        comparisons = {
            str(row["policy_id"]): row
            for row in attribution_contract.get("comparisons") or ()
        }
        for score in scores:
            policy_id = str(score["policy_id"])
            comparison = comparisons.get(policy_id)
            if not comparison:
                continue
            reference_id = str(comparison["reference_policy_id"])
            reference_score = by_policy[reference_id]
            realized_rows = []
            for row in attribution_rows:
                if row.get("policy_id") != policy_id:
                    continue
                entity_id = str(row["entity_id"])
                realized_rows.append({
                    **row,
                    "realized_active_return": returns[entity_id] - benchmark_return,
                    "realized_selection_contribution": (
                        float(row["delta_weight_vs_reference"])
                        * (returns[entity_id] - benchmark_return)
                    ),
                })
            incremental_cost = (
                float(score["transaction_cost"])
                - float(reference_score["transaction_cost"])
            )
            accounted = sum(
                float(row["realized_selection_contribution"])
                for row in realized_rows
            )
            observed = (
                float(score["selection_active_contribution_after_cost"])
                - float(reference_score["selection_active_contribution_after_cost"])
            )
            residual = observed - accounted
            if not math.isclose(residual, 0.0, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError(
                    f"portfolio policy attribution failed to reconcile: {comparison['comparison_id']}"
                )
            score["incremental_vs_reference_policy"] = {
                "comparison_id": comparison["comparison_id"],
                "reference_policy_id": reference_id,
                "selection_contribution_after_cost": observed,
                "incremental_transaction_cost_embedded": incremental_cost,
                "rows": realized_rows,
                "accounting_residual": residual,
                "causal_credit_authorized": False,
            }
        ranking_scores = [
            _score_ranking_ticket(ticket, returns, benchmark_return)
            for ticket in run.get("ranking_tickets") or ()
        ]
        factor_control = next(
            (
                row for row in ranking_scores
                if row["claim_id"] == "factor_implied_return_control"
            ),
            None,
        )
        if factor_control:
            for row in ranking_scores:
                if row.get("candidate_set_sha256") != factor_control.get(
                    "candidate_set_sha256"
                ):
                    continue
                row["comparison_to_factor_control"] = {
                    "rank_calibration_error_delta": (
                        float(row["rank_calibration"]["value"])
                        - float(factor_control["rank_calibration"]["value"])
                    ),
                    "top_1_regret_delta": (
                        float(row["regret"]["value"])
                        - float(factor_control["regret"]["value"])
                    ),
                    "negative_is_better": True,
                }
                row["ranking_score_sha256"] = stable_sha256({
                    key: value for key, value in row.items()
                    if key != "ranking_score_sha256"
                })
        cost_sensitivity = _transaction_cost_sensitivity(
            policies=run["policies"], gross_returns=window["gross_returns"],
            benchmark_id=benchmark_id, cash_return=cash_return,
            declared_bps=float(run["settlement_contract"]["transaction_cost_bps"]),
        )
        risk_evaluation = _settle_risk_challenger_evaluation(
            run,
            series=series,
            binding=binding,
            window=window,
            scores=_expanded_policy_scores(run, {"policy_scores": scores}),
        )
        body = {
            "schema": PORTFOLIO_POLICY_SETTLEMENT_SCHEMA,
            "settlement_id": f"{run['run_id']}::settlement",
            "run_id": run["run_id"], "run_sha256": run["run_sha256"],
            "inference_block_id": run["inference_block_id"],
            "evaluated_at": evaluated_at,
            "prospective_return_window": contract,
            "return_window_binding": binding,
            "return_window_settlement": window,
            "start_prices": dict(binding["entry_points"]),
            "actual_returns": returns,
            "benchmark_return": benchmark_return,
            "end_prices": {key: _point_dict(value) for key, value in complete_ends.items()},
            "policy_scores": scores,
            "transaction_cost_sensitivity": cost_sensitivity,
            "ranking_scores": ranking_scores,
            **(
                {"risk_challenger_evaluation": risk_evaluation}
                if risk_evaluation is not None else {}
            ),
            "trial_family_id": str(
                (run.get("trial_family") or _trial_family(run))["trial_family_id"]
            ),
            "capital_authority": False,
        }
        settlement = {**body, "settlement_sha256": stable_sha256(body)}
        _atomic_json(settlement_path, settlement)
        leaf = GoldenLeaf(
            owner=owner, object_kind="portfolio_policy_settlement",
            object_id=str(body["settlement_id"]), epoch=str(run["run_sha256"]),
            occurred_at=evaluated_at, available_at=evaluated_at, payload=settlement,
            source_refs=tuple(sorted({point.source_ref for point in complete_ends.values()})),
        )
        try:
            run_leaf = GoldenStore(store_path).head(owner, "portfolio_policy_run", str(run["run_id"]))
            edges = (GoldenEdge(leaf.leaf_sha256, str(run_leaf["leaf_sha256"]), "settles"),)
        except KeyError:
            edges = ()
        GoldenStore(store_path).append_bundle((leaf,), edges, make_heads=True)
        settled.append(settlement)
    reviews = portfolio_policy_status(root)["scoreboard"]["policy_reviews"]
    review_records = _persist_policy_reviews(
        root, owner=owner, store_path=store_path, reviews=reviews,
    )
    return {
        "ok": True,
        "evaluated_at": evaluated_at,
        "settled": settled,
        "pending": pending,
        "policy_reviews": reviews,
        "policy_review_records": review_records,
        "capital_authority": False,
    }


def portfolio_policy_price_refresh_entity_ids(
    root: Path, *, as_of: str | None = None,
) -> list[str]:
    """Return identities needed to bind an entry or observe a due exit."""

    evaluated = canonical_timestamp(as_of or _utc_now(), "portfolio policy price refresh as_of")
    base = root / "portfolio_policy"
    superseded = {
        str(row.get("prior_run_id") or "")
        for path in (base / "supersessions").glob("*.json")
        if (row := _read_json(path))
    }
    settled = {
        str(row.get("run_id") or "")
        for path in (base / "settlements").glob("*.json")
        if (row := _read_json(path))
    }
    entity_ids: set[str] = set()
    for path in sorted((base / "runs").glob("*.json")):
        run = _read_json(path)
        run_id = str((run or {}).get("run_id") or "")
        if (
            not run
            or run.get("schema") != PORTFOLIO_POLICY_RUN_SCHEMA
            or run_id in superseded | settled
        ):
            continue
        if not _valid_hash(run, "run_sha256"):
            raise ValueError(f"portfolio policy run hash is invalid: {run_id}")
        binding = dict((_read_json(
            base / "return_windows" / f"{run_id}.json"
        ) or {}).get("binding") or {})
        if not _current_run_identity(run) and binding.get("status") != "bound":
            continue
        if (
            binding.get("status") == "bound"
            and timestamp_key(evaluated) < timestamp_key(str(binding["scheduled_exit_at"]))
        ):
            continue
        entity_ids.update({
            str((run.get("benchmark") or {}).get("entity_id") or "").upper(),
            *(str(row.get("entity_id") or "").upper() for row in run.get("universe") or ()),
            *(str(row.get("entity_id") or "").upper() for row in run.get("fund_program_universe") or ()),
        })
    return sorted(entity_id for entity_id in entity_ids if entity_id)


def portfolio_policy_status(root: Path) -> dict[str, Any]:
    base = root / "portfolio_policy"
    runs = [row for path in sorted((base / "runs").glob("*.json")) if (row := _read_json(path))]
    all_settlements = [
        row for path in sorted((base / "settlements").glob("*.json"))
        if (row := _read_json(path))
    ]
    superseded_ids = {
        str(row["prior_run_id"])
        for path in (base / "supersessions").glob("*.json")
        if (row := _read_json(path)) and row.get("prior_run_id")
    }
    eligible_runs = [
        row for row in runs
        if _valid_hash(row, "run_sha256")
        and _current_run_identity(row)
        and str(row.get("run_id") or "") not in superseded_ids
    ]
    runs_by_id = {str(row["run_id"]): row for row in eligible_runs}
    settlements = [
        row for row in all_settlements
        if str(row.get("run_id") or "") in runs_by_id
        and _valid_hash(row, "settlement_sha256")
    ]
    settled_run_ids = {str(row["run_id"]) for row in settlements}
    by_policy: dict[str, list[float]] = {}
    by_comparison: dict[str, list[float]] = {}
    by_ranking_claim: dict[str, list[tuple[float, float, float]]] = {}
    review_groups: dict[str, list[tuple[Mapping[str, Any], Mapping[str, Any]]]] = {}
    families: dict[str, dict[str, Any]] = {}
    for settlement in settlements:
        run = runs_by_id.get(str(settlement.get("run_id") or ""))
        if not run:
            continue
        family = dict(run.get("trial_family") or _trial_family(run))
        family_id = str(family["trial_family_id"])
        families[family_id] = family
        review_groups.setdefault(family_id, []).append((run, settlement))
        if run.get("estimand_role") != "primary_patient_capital_policy_evidence":
            continue
        for score in settlement.get("ranking_scores") or ():
            by_ranking_claim.setdefault(str(score["claim_id"]), []).append((
                float(score["rank_calibration"]["value"]),
                float(score["regret"]["value"]),
                float(score["pairwise_rank_accuracy"]),
            ))
        for score in _expanded_policy_scores(run, settlement).values():
            by_policy.setdefault(str(score["policy_id"]), []).append(float(score["portfolio_excess_return_after_cost"]))
            attribution = score.get("incremental_vs_reference_policy") or {}
            if attribution.get("comparison_id"):
                by_comparison.setdefault(str(attribution["comparison_id"]), []).append(
                    float(attribution["selection_contribution_after_cost"])
                )
    rows = [
        {"policy_id": key, "episode_count": len(values), "mean_portfolio_excess_return_after_cost": sum(values) / len(values)}
        for key, values in sorted(by_policy.items())
    ]
    comparison_rows = [
        {
            "comparison_id": key,
            "episode_count": len(values),
            "mean_incremental_selection_contribution_after_cost": sum(values) / len(values),
        }
        for key, values in sorted(by_comparison.items())
    ]
    ranking_rows = [
        {
            "claim_id": key,
            "episode_count": len(values),
            "mean_rank_calibration_error": sum(row[0] for row in values) / len(values),
            "mean_top_1_regret": sum(row[1] for row in values) / len(values),
            "mean_pairwise_rank_accuracy": sum(row[2] for row in values) / len(values),
        }
        for key, values in sorted(by_ranking_claim.items())
    ]
    reviews = [
        _compile_policy_review(families[family_id], sorted(
            pairs, key=lambda pair: str(pair[1].get("evaluated_at") or ""),
        ))
        for family_id, pairs in sorted(review_groups.items())
    ]
    primary_reviews = [
        row for row in reviews
        if (row.get("trial_family") or {}).get("estimand_role")
        == "primary_patient_capital_policy_evidence"
    ]
    latest_review = max(
        primary_reviews,
        key=lambda row: str(row["last_evaluated_at"]),
        default=None,
    )
    latest = max(
        eligible_runs,
        key=lambda row: str(row.get("opened_at") or ""), default=None,
    )
    if latest and not latest.get("attribution_contract"):
        latest = {**latest, "attribution_projection": _run_attribution_contract(root, latest)}
    body = {
        "schema": PORTFOLIO_POLICY_STATUS_SCHEMA,
        "primary_horizon_days": PRIMARY_HORIZON_DAYS,
        "run_count": len(eligible_runs),
        "historical_run_count": len(runs),
        "eligible_run_count": len(eligible_runs),
        "superseded_run_count": len(superseded_ids),
        "quarantined_legacy_run_count": len(runs) - len(eligible_runs),
        "settled_count": len(settlements),
        "historical_settled_count": len(all_settlements),
        "pending_count": sum(
            str(row["run_id"]) not in settled_run_ids for row in eligible_runs
        ),
        "latest_run": latest,
        "scoreboard": {
            "rows": rows,
            "ranking_claims": ranking_rows,
            "attribution_comparisons": comparison_rows,
            "inference_block_count": len({row.get("inference_block_id") for row in settlements}),
            "minimum_inference_blocks": 8,
            "comparison_ready": any(
                bool(row["survivor_set"]["inference_sufficient"])
                for row in primary_reviews
            ),
            "policy_reviews": reviews,
            "diagnostic_policy_reviews": [
                row for row in reviews if row not in primary_reviews
            ],
            "latest_policy_review": latest_review,
            "next_activation": (
                str(latest_review["activation_status"])
                if latest_review else "settle_the_first_complete_policy_block"
            ),
        },
        "capital_authority": False,
    }
    return body


__all__ = [
    "OPPORTUNITY_RANKING_TICKET_SCHEMA",
    "PRIMARY_HORIZON_DAYS",
    "PORTFOLIO_POLICY_RUN_SCHEMA", "PORTFOLIO_POLICY_SETTLEMENT_SCHEMA",
    "PORTFOLIO_POLICY_STATUS_SCHEMA", "PORTFOLIO_POLICY_REVIEW_SCHEMA",
    "open_portfolio_policy_tournament",
    "portfolio_policy_price_refresh_entity_ids",
    "settle_portfolio_policy_tournaments", "portfolio_policy_status",
]
