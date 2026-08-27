"""Scheduled, point-in-time opportunity discovery for JaggedThoughts Capital.

The discovery run is an immutable analytical object.  It enumerates every
entity in a declared universe, evaluates only evidence available at the run
epoch, and emits ranked candidate leaves.  It may request research; it has no
authority to activate a paper position or route an order.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Mapping

import yaml

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, require_finite, require_text, timestamp_key
from .factor_analysis import PricePoint, FactorDefinition, analyze_factor_exposure, load_price_points
from .observation_index import load_observation_rows
from .public_capital_market_basis import public_sleeve_proxies
from .sources import load_source_manifest
from .valuation import (
    ValuationAssumption,
    ValuationScenario,
    compile_valuation_envelope,
)
from .watchlist import (
    bound_fund_valuation_coordinates,
    fund_evidence_vote_receipt,
    fund_potential_family_score,
    verify_fund_evidence_vote_receipt,
)


DISCOVERY_POLICY_SCHEMA = "jaggedthoughts-discovery-policy-v1"
DISCOVERY_RUN_SCHEMA = "jaggedthoughts-discovery-run-v1"
DISCOVERY_ENGINE_VERSION = "2026-08-14.evidence-vote-quotient-v12"
DISCOVERY_CANDIDATE_SCHEMA = "jaggedthoughts-discovery-candidate-v1"
DISCOVERY_QUALITY_FRESHNESS_SCHEMA = "jaggedthoughts-discovery-quality-freshness-v1"

_EQUITY_DOCTRINE_WEIGHTS = {
    "quality_expectations_balanced": {
        "accounting_durability": 0.50, "valuation_and_expectations": 0.50,
    },
    "quality_only": {
        "accounting_durability": 1.0, "valuation_and_expectations": 0.0,
    },
    "expectations_only": {
        "accounting_durability": 0.0, "valuation_and_expectations": 1.0,
    },
}


class _DiscoveryPolicy(dict[str, Any]):
    def __init__(self, payload: Mapping[str, Any], source_path: Path) -> None:
        super().__init__(payload)
        self.source_path = source_path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def activation_map() -> list[dict[str, Any]]:
    """Expose each state-changing boundary and the identity that owns it."""
    return [
        {
            "id": "schedule",
            "owner": "workbench_service",
            "mode": "supervised_due_check",
            "input": "discovery policy",
            "output": "due discovery run",
            "meaning": "The user-session workbench service keeps the server alive; its discovery, research, and capital-cycle children apply the configured due checks and resume after process failure or login.",
        },
        {
            "id": "bounded_public_enrichment",
            "owner": "enrichment_kernel",
            "mode": "automatic_under_policy",
            "input": "saved scout queues plus frozen acquisition budgets",
            "output": "leased source-enrichment jobs",
            "meaning": "Diversity, sector, source-call, and research-time limits determine which public identities enter deep analysis.",
        },
        {
            "id": "public_evidence_refresh",
            "owner": "discovery_kernel",
            "mode": "automatic",
            "input": "enabled public-source manifest",
            "output": "point-in-time source epoch",
            "meaning": "Provider bytes are cached before normalization and carry availability times.",
        },
        {
            "id": "screen_and_rank",
            "owner": "discovery_kernel",
            "mode": "automatic",
            "input": "source epoch plus declared universes and policy",
            "output": "immutable candidate leaves",
            "meaning": (
                "Equity doctrine programs rank the same equity population and interleave ordinal "
                "leaders; funds rank only inside comparable implementation sleeves. Candidate and "
                "fund-lane ranks share research attention without treating native scores as commensurable."
            ),
        },
        {
            "id": "rank_program_tournament",
            "owner": "prospective_learning_kernel",
            "mode": "automatic_on_new_complete_discovery_population",
            "input": "same full pre-truncation eligible population and later point-in-time outcomes",
            "output": "paired fixed-program rank settlement",
            "meaning": "Every applicable doctrine and sensitivity program sees identical frozen inputs; prospective settlements can support an explicit policy review but cannot change attention policy themselves.",
        },
        {
            "id": "candidate_research",
            "owner": "leased_subscription_agent_or_operator",
            "mode": "automatic_when_agent_research_policy_enabled",
            "input": "one candidate leaf, immutable request, and lineage",
            "output": "typed research dossier",
            "meaning": "A web-research worker may consume the request under a daily budget; kernel validation owns dossier admission.",
        },
        {
            "id": "company_strategy_frontier",
            "owner": "strategy_kernel_after_subscription_proposal",
            "mode": "automatic_after_validated_dossier",
            "input": "source-bound industry state, choice grammar, and scenario mechanisms",
            "output": "compatible strategy systems, local peaks, and scope-relative frontier",
            "meaning": "The agent proposes company-specific choices; typed enumeration, incompatibilities, and closure certificates decide what entered the declared search space.",
        },
        {
            "id": "strategy_peer_search",
            "owner": "leased_subscription_agent_plus_cohort_kernel",
            "mode": "automatic_after_exact_implementation_event",
            "input": "exact move phenotype, environment, frozen peer set, and primary-source window",
            "output": "exact adoption, related treatment, provisional control, or source gap",
            "meaning": "Related moves and exhausted searches stay out of the control group; weak comparison support widens the peer search without changing the treatment definition.",
        },
        {
            "id": "strategy_law_challenge",
            "owner": "institutional_learning_kernel",
            "mode": "automatic_after_classification_or_outcome",
            "input": "strategy phenotype, dated implementation, operating histories, and comparison group",
            "output": "context-bounded law evaluation and counterexamples",
            "meaning": "Business-move laws remain conjectures until point-in-time operating outcomes, pretrend checks, and held-out transfer evidence discriminate them.",
        },
        {
            "id": "strategy_outcome_settlement",
            "owner": "strategy_learning_kernel",
            "mode": "automatic_when_declared_outcome_is_due_and_observed",
            "input": "exact move, frozen outcome contract, and later public observations",
            "output": "source-bound operating outcome episode",
            "meaning": "An operating episode can support, contradict, or leave a move inconclusive; it cannot attribute a stock return to that move.",
        },
        {
            "id": "strategy_transfer_index",
            "owner": "strategy_transfer_kernel",
            "mode": "automatic_after_learning_state_change",
            "input": "exact phenotype laws, moderators, evaluations, and operating episodes",
            "output": "queryable law cards and counterexamples",
            "meaning": "Transfer memory preserves the environments where a move worked and the break cases where it did not.",
        },
        {
            "id": "strategy_alpha_tournament",
            "owner": "world_model_tournament_kernel",
            "mode": "automatic_when_compatible_settled_blocks_meet_the_floor",
            "input": "identical frozen valuation, durability, phenotype, and later-return packets",
            "output": "nested incremental-value verdict",
            "meaning": "The phenotype arm must beat valuation-only and valuation-plus-durability controls before it can enter prospective paper settlement.",
        },
        {
            "id": "paper_activation",
            "owner": "paper_activation_kernel_under_operator_policy",
            "mode": "manual_or_bounded_standing_policy",
            "input": "exact current eligible zero-weight proposal",
            "output": "active zero-weight paper watch",
            "meaning": "The kernel may apply the operator's standing policy after every proposal gate clears; candidates and research agents cannot write this transition, and it grants no position or order authority.",
        },
        {
            "id": "paper_portfolio_assembly",
            "owner": "portfolio_kernel",
            "mode": "automatic_after_activation",
            "input": "active paper profiles and constraints",
            "output": "paper allocation proposal",
            "meaning": "Enumeration and dominance operate only over operator-activated paper candidates.",
        },
        {
            "id": "paper_forecast_settlement",
            "owner": "capital_cycle_kernel",
            "mode": "automatic_when_horizon_matures",
            "input": "frozen paper forecast, later public prices, benchmark, and costs",
            "output": "settled active return, model score, and learning episode",
            "meaning": "Later outcomes may update research priority and model evidence; they cannot rewrite the decision-time packet.",
        },
        {
            "id": "capital_execution",
            "owner": "external_brokerage_process",
            "mode": "unavailable",
            "input": "none",
            "output": "none",
            "meaning": "This workbench has no brokerage credentials or order-routing authority.",
        },
    ]


def default_discovery_policy() -> dict[str, Any]:
    return {
        "schema": DISCOVERY_POLICY_SCHEMA,
        "enabled": True,
        "cadence_hours": 24,
        "max_ranked_candidates": 100,
        "equities": {
            "enabled": True,
            "universe": "enrolled_sec_companies",
            "benchmark_entity_id": "SPY",
            "input_max_age_days": {
                "price": 14,
                "annual_fundamentals": 550,
                "balance_sheet": 550,
                "market_state": 45,
            },
            "min_factor_observations": 120,
            "fallback_beta": 1.0,
            "forecast_growth_rates": [-0.02, 0.0, 0.03, 0.06],
            "terminal_growth_rates": [0.015, 0.025],
            "horizons_years": [5, 10],
            "minimum_score": 0.50,
            "criteria": [
                {"id": "quality-floor", "path": "quality", "operator": "ge", "value": 0.45},
                {"id": "excess-return-floor", "path": "price_implied_excess_return", "operator": "ge", "value": 0.03},
                {"id": "earnings-power-floor", "path": "earnings_power_margin", "operator": "ge", "value": -0.35},
            ],
        },
        "funds": {
            "enabled": True,
            "universe": "compiled_watchlists",
            "minimum_score": 0.50,
            "criteria": [
                {"id": "fund-return-floor", "path": "factor_implied_return", "operator": "ge", "value": 0.06},
                {"id": "fund-earnings-power-floor", "path": "earnings_power_margin", "operator": "ge", "value": -0.35},
                {"id": "fund-implied-growth-ceiling", "path": "implied_growth", "operator": "le", "value": 0.08},
            ],
        },
    }


def load_discovery_policy(path: str | Path) -> Mapping[str, Any]:
    policy_path = Path(path).expanduser().resolve()
    payload = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping) or payload.get("schema") != DISCOVERY_POLICY_SCHEMA:
        raise ValueError(f"discovery policy schema must be {DISCOVERY_POLICY_SCHEMA}")
    cadence = require_finite(payload.get("cadence_hours", 24), "discovery cadence_hours")
    if cadence <= 0:
        raise ValueError("discovery cadence_hours must be positive")
    equities = payload.get("equities") if isinstance(payload.get("equities"), Mapping) else {}
    age_limits = equities.get("input_max_age_days") if isinstance(equities.get("input_max_age_days"), Mapping) else {}
    for age_class, value in age_limits.items():
        if require_finite(value, f"discovery input age {age_class}") <= 0:
            raise ValueError(f"discovery input age {age_class} must be positive")
    return _DiscoveryPolicy(payload, policy_path)


def project_discovery_quality_freshness(
    workspace: str | Path,
    *,
    latest_run: Mapping[str, Any] | None,
    now: str | None = None,
) -> dict[str, Any]:
    """Project candidate bindings invalidated by a current quality head."""

    root = Path(workspace).expanduser().resolve()
    checked_at = canonical_timestamp(now or _utc_now(), "quality freshness now")
    invalidations = []
    gaps = []
    run = dict(latest_run or {})
    valid_run = not run or (
        run.get("schema") == DISCOVERY_RUN_SCHEMA
        and str(run.get("run_sha256") or "") == stable_sha256({
            key: value for key, value in run.items() if key != "run_sha256"
        })
    )
    if not valid_run:
        gaps.append(_freshness_gap("discovery_run_identity_invalid"))
    for candidate in run.get("candidates") or () if valid_run else ():
        if not isinstance(candidate, Mapping) or candidate.get("entity_kind") != "public_equity":
            continue
        entity_id = str(candidate.get("entity_id") or "").upper()
        if str(candidate.get("candidate_sha256") or "") != stable_sha256({
            key: value for key, value in candidate.items() if key != "candidate_sha256"
        }):
            gaps.append(_freshness_gap("discovery_candidate_identity_invalid", entity_id=entity_id))
            continue
        bound_sha = str(candidate.get("quality_report_sha256") or "")
        if not entity_id or not bound_sha:
            gaps.append(_freshness_gap(
                "candidate_quality_binding_missing",
                entity_id=entity_id or None,
                candidate_id=candidate.get("candidate_id"),
            ))
            continue
        quality_path = root / "quality" / f"{entity_id.lower()}.json"
        try:
            quality = json.loads(quality_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            gaps.append(_freshness_gap("current_quality_head_missing", entity_id=entity_id))
            continue
        current_sha = str(quality.get("quality_report_sha256") or "")
        if not current_sha or current_sha != stable_sha256({
            key: value for key, value in quality.items() if key != "quality_report_sha256"
        }):
            gaps.append(_freshness_gap("current_quality_head_invalid", entity_id=entity_id))
            continue
        try:
            current_as_of = canonical_timestamp(quality.get("as_of"), "quality.as_of")
            candidate_as_of = canonical_timestamp(candidate.get("as_of"), "candidate.as_of")
            available_at = canonical_timestamp(quality.get("available_at"), "quality.available_at")
        except ValueError:
            gaps.append(_freshness_gap("quality_freshness_timestamp_invalid", entity_id=entity_id))
            continue
        if timestamp_key(available_at) > timestamp_key(checked_at):
            gaps.append(_freshness_gap("current_quality_head_not_yet_available", entity_id=entity_id))
            continue
        if current_sha == bound_sha:
            continue
        identity = {
            "entity_id": entity_id,
            "candidate_id": candidate.get("candidate_id"),
            "candidate_sha256": candidate.get("candidate_sha256"),
            "candidate_as_of": candidate_as_of,
            "bound_quality_report_sha256": bound_sha,
            "current_quality_as_of": current_as_of,
            "current_quality_report_sha256": current_sha,
        }
        if timestamp_key(current_as_of) < timestamp_key(candidate_as_of):
            gaps.append(_freshness_gap("current_quality_head_older_than_candidate", **identity))
            continue
        invalidations.append({
            **identity,
            "activation": "refresh_discovery_epoch",
            "invalidation_sha256": stable_sha256(identity),
        })
    body = {
        "schema": DISCOVERY_QUALITY_FRESHNESS_SCHEMA,
        "checked_at": checked_at,
        "refresh_due": bool(invalidations),
        "invalidation_count": len(invalidations),
        "invalidations": sorted(invalidations, key=lambda row: row["entity_id"]),
        "gaps": sorted(gaps, key=lambda row: (row["code"], str(row.get("entity_id") or ""))),
        "activation": "refresh_discovery_epoch" if invalidations else None,
        "mutates_candidates": False,
        "fetches_sources": False,
        "capital_authority": False,
    }
    return {**body, "freshness_sha256": stable_sha256(body)}


def _freshness_gap(code: str, **context: Any) -> dict[str, Any]:
    body = {"code": code, **context}
    return {**body, "gap_sha256": stable_sha256(body)}


def discovery_schedule_status(
    *,
    policy: Mapping[str, Any],
    latest_run: Mapping[str, Any] | None,
    now: str | None = None,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    current = canonical_timestamp(now or _utc_now(), "discovery schedule now")
    enabled = bool(policy.get("enabled", True))
    cadence_hours = require_finite(policy.get("cadence_hours", 24), "discovery cadence_hours")
    last_completed = str((latest_run or {}).get("completed_at") or "")
    if last_completed:
        due_at_dt = datetime.fromisoformat(last_completed.replace("Z", "+00:00")) + timedelta(hours=cadence_hours)
        next_due_at = due_at_dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        cadence_due = enabled and timestamp_key(current) >= timestamp_key(next_due_at)
    else:
        next_due_at = current
        cadence_due = enabled
    policy_source = getattr(policy, "source_path", None)
    freshness_root = workspace or (Path(policy_source).parent if policy_source else None)
    freshness = (
        project_discovery_quality_freshness(freshness_root, latest_run=latest_run, now=current)
        if freshness_root is not None else None
    )
    freshness_due = enabled and bool((freshness or {}).get("refresh_due"))
    due_reasons = [
        reason for reason, active in (
            ("cadence_elapsed", cadence_due),
            ("candidate_quality_epoch_changed", freshness_due),
        ) if active
    ]
    return {
        "enabled": enabled,
        "cadence_hours": cadence_hours,
        "checked_at": current,
        "last_completed_at": last_completed or None,
        "next_due_at": next_due_at,
        "due": bool(due_reasons),
        "due_reasons": due_reasons,
        "quality_freshness": freshness,
        "service_mode": "periodic_due_check",
    }


def _latest_observations(
    path: Path,
    as_of: str,
    *,
    entity_ids: Iterable[str] | None = None,
) -> dict[tuple[str, str], dict[str, Any]]:
    cutoff = canonical_timestamp(as_of, "discovery as_of")
    wanted = {entity_id.upper() for entity_id in entity_ids or ()}
    rows = load_observation_rows(
        path, as_of=cutoff, entity_ids=wanted, latest_per_metric=True,
    )
    return {
        (str(row["entity_id"]).upper(), str(row["metric_id"])): dict(row)
        for row in rows
    }


def _need(
    latest: Mapping[tuple[str, str], Mapping[str, Any]], entity_id: str, metric_id: str
) -> Mapping[str, Any]:
    key = (entity_id.upper(), metric_id)
    if key not in latest:
        raise ValueError(f"discovery requires {key[0]}.{metric_id}")
    return latest[key]


def _need_compatible(
    latest: Mapping[tuple[str, str], Mapping[str, Any]], entity_id: str,
    metric_id: str, *, as_of: str, max_age_days: int,
) -> tuple[Mapping[str, Any], dict[str, Any]]:
    row = _need(latest, entity_id, metric_id)
    age_days = (timestamp_key(as_of) - timestamp_key(str(row["observed_at"]))).total_seconds() / 86_400
    if age_days < 0 or age_days > max_age_days:
        raise ValueError(
            f"discovery rejects incompatible {entity_id.upper()}.{metric_id}: "
            f"observation age {age_days:.1f} days exceeds [0, {max_age_days}]"
        )
    return row, {
        "entity_id": entity_id.upper(), "metric_id": metric_id,
        "observed_at": row["observed_at"], "available_at": row["available_at"],
        "age_days": age_days, "max_age_days": max_age_days,
        "compatible": True,
    }


def _select_share_basis(
    latest: Mapping[tuple[str, str], Mapping[str, Any]], entity_id: str,
    *, price: Mapping[str, Any], as_of: str, max_age_days: int,
) -> tuple[Mapping[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """Select the freshest typed share grain and reject split-basis mismatches."""
    candidates = []
    witnesses = []
    rejected = []
    for metric_id in ("diluted_shares", "diluted_shares_current"):
        if (entity_id.upper(), metric_id) not in latest:
            continue
        try:
            row, witness = _need_compatible(
                latest, entity_id, metric_id, as_of=as_of,
                max_age_days=max_age_days,
            )
        except ValueError as error:
            rejected.append(str(error))
            continue
        candidates.append((row, metric_id))
        witnesses.append(witness)
    if not candidates:
        raise ValueError(
            "; ".join(rejected)
            or f"discovery requires {entity_id.upper()}.diluted_shares"
        )
    shares, metric_id = max(candidates, key=lambda item: (
        timestamp_key(str(item[0]["observed_at"])),
        timestamp_key(str(item[0]["available_at"])),
        str(item[0].get("observation_id") or ""),
    ))
    split = latest.get((entity_id.upper(), "stock_split_ratio"))
    split_between = bool(
        split
        and timestamp_key(str(shares["observed_at"]))
        < timestamp_key(str(split["observed_at"]))
        <= timestamp_key(str(price["observed_at"]))
    )
    receipt = {
        "schema": "jaggedthoughts-share-basis-compatibility-v1",
        "entity_id": entity_id.upper(),
        "selected_metric_id": metric_id,
        "shares_observation_id": shares.get("observation_id"),
        "shares_observed_at": shares["observed_at"],
        "shares_available_at": shares["available_at"],
        "price_observation_id": price.get("observation_id"),
        "price_observed_at": price["observed_at"],
        "latest_split": ({
            "observation_id": split.get("observation_id"),
            "ratio": float(split["value"]),
            "observed_at": split["observed_at"],
            "available_at": split["available_at"],
            "source_ref": split["source_ref"],
        } if split else None),
        "compatible": not split_between,
        "status": (
            "post_split_share_basis" if split and not split_between
            else "no_intervening_split" if not split
            else "intervening_split_unresolved"
        ),
        "capital_authority": False,
    }
    receipt["receipt_sha256"] = stable_sha256(receipt)
    if split_between:
        raise ValueError(
            "corporate_action_share_basis_incompatible: stock split lies between "
            f"{metric_id} ({shares['observed_at']}) and price ({price['observed_at']})"
        )
    return shares, receipt, witnesses


def _criterion(paths: Mapping[str, float], raw: Mapping[str, Any]) -> dict[str, Any]:
    criterion_id = require_text(raw.get("id"), "discovery criterion id")
    path = require_text(raw.get("path"), f"criterion {criterion_id} path")
    operator = require_text(raw.get("operator"), f"criterion {criterion_id} operator")
    threshold = require_finite(raw.get("value"), f"criterion {criterion_id} value")
    if path not in paths:
        raise ValueError(f"criterion {criterion_id} references unavailable path {path}")
    observed = require_finite(paths[path], f"criterion {criterion_id} observed")
    comparisons = {
        "ge": observed >= threshold,
        "gt": observed > threshold,
        "le": observed <= threshold,
        "lt": observed < threshold,
    }
    if operator not in comparisons:
        raise ValueError(f"unsupported discovery criterion operator: {operator}")
    return {
        "criterion_id": criterion_id, "path": path, "operator": operator,
        "threshold": threshold, "observed": observed, "passed": comparisons[operator],
    }


def _scale(value: float, low: float, high: float, *, inverse: bool = False) -> float:
    if high <= low:
        raise ValueError("discovery scale high must exceed low")
    score = min(1.0, max(0.0, (value - low) / (high - low)))
    return 1.0 - score if inverse else score


def _candidate(body: Mapping[str, Any]) -> dict[str, Any]:
    payload = {"schema": DISCOVERY_CANDIDATE_SCHEMA, **dict(body)}
    return {**payload, "candidate_sha256": stable_sha256(payload)}


def _policy_ref(policy: Mapping[str, Any]) -> str:
    return f"discovery_policy:{stable_sha256(policy)}"


def _equity_beta(
    *, entity_id: str, benchmark_id: str, price_points: Iterable[PricePoint], as_of: str,
    min_observations: int, fallback_beta: float, policy_ref: str,
) -> tuple[float, dict[str, Any]]:
    try:
        analysis = analyze_factor_exposure(
            analysis_id=f"discovery-beta:{entity_id}:{as_of}",
            candidate_entity_id=entity_id,
            factors=(FactorDefinition("market", benchmark_id, expected_annual_premium=0.0),),
            price_points=price_points,
            as_of=as_of,
            min_observations=min_observations,
        )
        return float(analysis["coefficients"]["betas"]["market"]), {
            "status": "estimated", "analysis": analysis,
            "source_refs": list(analysis.get("source_refs") or ()),
        }
    except (KeyError, TypeError, ValueError) as error:
        beta = require_finite(fallback_beta, "discovery fallback_beta")
        if beta < 0:
            raise ValueError("discovery fallback_beta cannot be negative") from error
        return beta, {
            "status": "declared_fallback", "value": beta, "reason": str(error),
            "source_refs": [policy_ref],
        }


def _assumption(
    assumption_id: str, kind: str, value: float, unit: str, refs: Iterable[str]
) -> ValuationAssumption:
    return ValuationAssumption(assumption_id, kind, value, unit, tuple(sorted(set(refs))))


def _compile_equity(
    *,
    entity_id: str,
    quality: Mapping[str, Any],
    latest: Mapping[tuple[str, str], Mapping[str, Any]],
    price_points_by_entity: Mapping[str, tuple[PricePoint, ...]],
    as_of: str,
    config: Mapping[str, Any],
    policy: Mapping[str, Any],
    input_leaf: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    entity = require_text(entity_id, "discovery equity entity_id").upper()
    benchmark = str(config.get("benchmark_entity_id") or "SPY").upper()
    policy_ref = _policy_ref(policy)
    raw_limits = config.get("input_max_age_days")
    limits = dict(raw_limits) if isinstance(raw_limits, Mapping) else {}
    default_limits = {
        "price": 14, "annual_fundamentals": 550,
        "balance_sheet": 550, "market_state": 45,
    }
    compatibility: list[dict[str, Any]] = []

    def compatible(metric_id: str, age_class: str, owner: str = entity) -> Mapping[str, Any]:
        row, witness = _need_compatible(
            latest, owner, metric_id, as_of=as_of,
            max_age_days=int(limits.get(age_class, default_limits[age_class])),
        )
        compatibility.append(witness)
        return row

    price = compatible("price", "price")
    owner_earnings = compatible("normalized_owner_earnings", "annual_fundamentals")
    excess_cash = compatible("excess_net_cash", "balance_sheet")
    cash = compatible("cash", "balance_sheet")
    total_debt = compatible("total_debt", "balance_sheet")
    shares, share_basis, share_witnesses = _select_share_basis(
        latest, entity, price=price, as_of=as_of,
        max_age_days=int(limits.get(
            "annual_fundamentals", default_limits["annual_fundamentals"],
        )),
    )
    compatibility.extend(share_witnesses)
    compatibility.append(share_basis)
    risk_free = compatible("risk_free_rate", "market_state", "US-MARKET")
    erp = compatible("implied_equity_risk_premium", "market_state", "US-MARKET")
    beta, beta_receipt = _equity_beta(
        entity_id=entity, benchmark_id=benchmark,
        price_points=(*price_points_by_entity.get(entity, ()), *price_points_by_entity.get(benchmark, ())),
        as_of=as_of, min_observations=int(config.get("min_factor_observations", 120)),
        fallback_beta=float(config.get("fallback_beta", 1.0)), policy_ref=policy_ref,
    )
    assumptions = [
        _assumption("market-price", "MarketPrice", float(price["value"]), "currency/share", [str(price["source_ref"])]),
        _assumption("owner-earnings", "OwnerEarnings", float(owner_earnings["value"]), "currency/year", [str(owner_earnings["source_ref"])]),
        _assumption("excess-net-cash", "ExcessNetCash", float(excess_cash["value"]), "currency", [str(excess_cash["source_ref"])]),
        _assumption("diluted-shares", "Shares", float(shares["value"]), "shares", [str(shares["source_ref"])]),
        _assumption("risk-free", "RiskFreeRate", float(risk_free["value"]), "decimal", [str(risk_free["source_ref"])]),
        _assumption("implied-erp", "EquityRiskPremium", float(erp["value"]), "decimal", [str(erp["source_ref"])]),
        _assumption("equity-beta", "EquityBeta", beta, "multiple", beta_receipt["source_refs"]),
    ]
    growth_ids: list[str] = []
    for index, value in enumerate(config.get("forecast_growth_rates") or [-0.02, 0.0, 0.03, 0.06]):
        assumption_id = f"forecast-growth-{index + 1}"
        growth_ids.append(assumption_id)
        assumptions.append(_assumption(assumption_id, "ForecastGrowth", float(value), "decimal", [policy_ref]))
    terminal_ids: list[str] = []
    for index, value in enumerate(config.get("terminal_growth_rates") or [0.015, 0.025]):
        assumption_id = f"terminal-growth-{index + 1}"
        terminal_ids.append(assumption_id)
        assumptions.append(_assumption(assumption_id, "TerminalGrowth", float(value), "decimal", [policy_ref]))
    for index, value in enumerate(config.get("horizons_years") or [5, 10]):
        assumptions.append(_assumption(f"horizon-{index + 1}", "Horizon", float(value), "years", [policy_ref]))
    scenarios = tuple(
        ValuationScenario(
            scenario_id=f"cashflow-{growth_id}-{terminal_id}",
            mechanism_id="durable_or_mean_reverting_earnings",
            assumption_ids=(growth_id, terminal_id),
            source_refs=(policy_ref, *tuple(quality.get("source_refs") or ())),
        )
        for growth_id in growth_ids for terminal_id in terminal_ids
    )
    envelope = compile_valuation_envelope(
        envelope_id=f"discovery:{entity}:{as_of}", entity_id=entity,
        evidence_epoch=as_of, grammar_id="jaggedthoughts.discovery.equity-valuation",
        grammar_version="1", assumptions=assumptions, scenarios=scenarios,
        max_depth=4, max_programs=5000,
    ).to_dict()
    summary = {key: float(value) for key, value in envelope["summary"].items()}
    quality_scores = quality["scores"]
    quality_score = float(quality_scores["durable_earnings_power"])
    paths = {
        "quality": quality_score,
        "earnings_power_margin": summary["earnings_power_margin_of_safety"],
        "implied_growth": summary["implied_growth_median"],
        "implied_required_return": summary["implied_required_return_median"],
        "price_implied_excess_return": summary["price_implied_excess_return"],
    }
    criteria = [
        _criterion(paths, raw) for raw in config.get("criteria", []) if isinstance(raw, Mapping)
    ]
    components = {
        "revenue_durability": float(quality_scores["revenue_durability"]),
        "earnings_quality": float(quality_scores["earnings_quality"]),
        "balance_sheet_resilience": float(quality_scores["balance_sheet_resilience"]),
        "durable_earnings_power": quality_score,
        "price_implied_excess_return": _scale(paths["price_implied_excess_return"], -0.02, 0.12),
        "earnings_power_margin": _scale(paths["earnings_power_margin"], -0.60, 0.50),
        "low_implied_growth": _scale(paths["implied_growth"], -0.05, 0.15, inverse=True),
        "evidence_coverage": 1.0 if quality.get("coverage", {}).get("status") == "sufficient_for_screen" else 0.5,
    }
    score_families = {
        "accounting_durability": components["durable_earnings_power"],
        "valuation_and_expectations": sum(components[name] for name in (
            "price_implied_excess_return", "earnings_power_margin", "low_implied_growth",
        )) / 3,
    }
    family_weights = {"accounting_durability": 0.45, "valuation_and_expectations": 0.55}
    score = sum(family_weights[name] * value for name, value in score_families.items())
    doctrine_scores = {
        doctrine_id: sum(weights[name] * score_families[name] for name in weights)
        for doctrine_id, weights in _EQUITY_DOCTRINE_WEIGHTS.items()
    }
    minimum = float(config.get("minimum_score", 0.50))
    factor_evidence_pass = beta_receipt.get("status") == "estimated"
    passed = (
        all(row["passed"] for row in criteria)
        and score >= minimum
        and quality.get("coverage", {}).get("status") == "sufficient_for_screen"
        and factor_evidence_pass
    )
    source_refs = sorted(set(
        list(quality.get("source_refs") or ())
        + [str(row["source_ref"]) for row in (
            price, owner_earnings, excess_cash, cash, total_debt, shares, risk_free, erp,
        )]
        + ([str(share_basis["latest_split"]["source_ref"])]
           if share_basis.get("latest_split") else [])
        + list(beta_receipt.get("source_refs") or ())
    ))
    candidate = _candidate({
        "candidate_id": f"equity:{entity}", "entity_id": entity,
        "entity_kind": "public_equity", "name": entity, "as_of": as_of,
        "analysis_kind": "durable_earnings_and_formal_valuation",
        "screen_status": "qualified" if passed else "monitor",
        "rank_score": score, "score_components": components,
        "score_families": score_families, "family_weights": family_weights,
        "doctrine_scores": doctrine_scores,
        "criteria": criteria, "metrics": paths,
        "admission_gates": {
            "factor_evidence_pass": factor_evidence_pass,
            "share_basis_compatible": share_basis["compatible"],
        },
        "input_compatibility": compatibility,
        "quality_report_sha256": quality.get("quality_report_sha256"),
        "valuation": {
            "envelope_sha256": envelope["envelope_sha256"],
            "summary": summary,
            "enumeration": envelope["enumeration"],
            "expectations_frontier": envelope["expectations_frontier"],
            "share_basis": share_basis,
        },
        "beta_receipt": beta_receipt,
        "source_refs": source_refs,
        "input_golden_leaves": [input_leaf] if input_leaf else [],
        "next_activation": (
            "candidate_research" if passed else
            "collect_factor_history" if not factor_evidence_pass else
            "monitor_next_source_epoch"
        ),
        "research_prompt": (
            "Test whether the measured earnings power is protected by a reinforcing choice system; "
            "state the strongest rival, industry response, capital-allocation evidence, and decisive falsifier."
        ),
    })
    return candidate, envelope


def _fund_score(row: Mapping[str, Any]) -> tuple[float | None, dict[str, float]]:
    valuation, valuation_blockers = bound_fund_valuation_coordinates(row.get("valuation"))
    if valuation_blockers:
        return None, {}
    potential = row.get("investment_potential")
    if isinstance(potential, Mapping) and potential.get("score") is not None:
        components = {
            f"potential_{name}": float(value)
            for name, value in (potential.get("component_scores") or {}).items()
        }
        required = {
            "potential_earnings_yield", "potential_book_to_price",
            "potential_factor_return_per_volatility",
            "potential_drawdown_resilience", "potential_fee_efficiency",
        }
        if (
            not required.issubset(components)
            or not verify_fund_evidence_vote_receipt(
                potential.get("evidence_vote_receipt")
            )
        ):
            return None, {}
        return float(potential["score"]), components
    if isinstance(potential, Mapping):
        return None, {}
    analysis = row["analysis"]
    fit = float(analysis["fit"]["leave_one_out_r2"])
    implied_return = float(analysis["assumption_implied"]["return_without_residual_alpha"])
    drawdown = float(analysis["historical"]["maximum_drawdown"])
    volatility = float(analysis["historical"]["candidate_annualized_volatility"])
    expense = valuation["expense_ratio"]
    components = {
        "earnings_yield": _scale(valuation["earnings_yield"], 0.02, 0.10),
        "book_to_price": _scale(valuation["book_to_price"], 0.10, 0.80),
        "factor_return_after_fee": _scale(implied_return - expense, 0.02, 0.12),
        "factor_return_per_volatility": _scale(implied_return / volatility, 0.10, 0.80) if volatility > 0 else 0.0,
        "drawdown_resilience": _scale(drawdown, -0.60, -0.10),
        "fee_efficiency": _scale(expense, 0.0, 0.02, inverse=True),
        "factor_fit_coverage": _scale(fit, -0.10, 0.60),
    }
    score, _ = fund_potential_family_score(components)
    return score, components


def _rank_candidate_lanes(
    candidates: list[dict[str, Any]], *, minimum_fund_score: float = 0.50,
) -> None:
    """Rank potential inside comparable lanes, then interleave research attention."""
    equity_rows = [
        row for row in candidates if row["entity_kind"] == "public_equity"
    ]
    fund_rows = [
        row for row in candidates if row["entity_kind"] == "public_fund"
    ]

    def rank_lane(lane: str, rows: list[dict[str, Any]]) -> None:
        ranked = sorted(
            (row for row in rows if row.get("rank_score") is not None),
            key=lambda row: (-float(row["rank_score"]), str(row["candidate_id"])),
        )
        for lane_rank, row in enumerate(ranked, start=1):
            row["potential_rank"] = {
                "scope": lane,
                "rank": lane_rank,
                "ranked_count": len(ranked),
                "native_score": float(row["rank_score"]),
            }
    equity_with_doctrines = [
        row for row in equity_rows
        if set(row.get("doctrine_scores") or ()) == set(_EQUITY_DOCTRINE_WEIGHTS)
    ]
    if equity_with_doctrines:
        for doctrine_id in _EQUITY_DOCTRINE_WEIGHTS:
            doctrine_ranked = sorted(
                equity_with_doctrines,
                key=lambda row: (
                    -float(row["doctrine_scores"][doctrine_id]),
                    str(row["candidate_id"]),
                ),
            )
            for doctrine_rank, row in enumerate(doctrine_ranked, 1):
                row.setdefault("doctrine_ranks", {})[doctrine_id] = doctrine_rank
        equity_with_doctrines.sort(key=lambda row: (
            min(row["doctrine_ranks"].values()),
            row["doctrine_ranks"]["quality_expectations_balanced"],
            str(row["candidate_id"]),
        ))
        for lane_rank, row in enumerate(equity_with_doctrines, 1):
            best_rank = min(row["doctrine_ranks"].values())
            leading = sorted(
                doctrine_id for doctrine_id, rank in row["doctrine_ranks"].items()
                if rank == best_rank
            )
            row["potential_rank"] = {
                "scope": "public_equity", "rank": lane_rank,
                "ranked_count": len(equity_with_doctrines),
                "native_score": float(row["rank_score"]),
                "ordering_basis": "best_doctrine_rank_then_balanced_rank",
                "best_doctrine_rank": best_rank,
                "leading_doctrines": leading,
                "doctrine_ranks": dict(sorted(row["doctrine_ranks"].items())),
                "rank_disagreement": max(row["doctrine_ranks"].values()) - best_rank,
            }
    else:
        rank_lane("public_equity", equity_rows)

    fund_peer_groups: dict[str, list[dict[str, Any]]] = {}
    for row in fund_rows:
        peer_group = str(
            (row.get("investment_potential") or {}).get("peer_group") or "unbound"
        )
        fund_peer_groups.setdefault(peer_group, []).append(row)

    def percentile(sample: list[float], value: float) -> float:
        ordered = sorted(sample)
        below = sum(candidate < value for candidate in ordered)
        equal = sum(candidate == value for candidate in ordered)
        return (below + 0.5 * equal) / len(ordered)

    for peer_group, rows in fund_peer_groups.items():
        coordinates_by_entity: dict[str, dict[str, float]] = {}
        for row in sorted(rows, key=lambda item: str(item["candidate_id"])):
            if row.get("rank_score") is None:
                continue
            raw = (row.get("investment_potential") or {}).get("coordinates")
            if not isinstance(raw, Mapping):
                continue
            coordinates = {
                str(name): float(value) for name, value in raw.items()
                if not isinstance(value, bool) and math.isfinite(float(value))
            }
            if coordinates and len(coordinates) == len(raw):
                coordinates_by_entity.setdefault(str(row["entity_id"]), coordinates)
        if not coordinates_by_entity:
            continue
        coordinate_names = set.intersection(*(
            set(values) for values in coordinates_by_entity.values()
        ))
        population = len(coordinates_by_entity)
        for row in rows:
            coordinates = coordinates_by_entity.get(str(row["entity_id"]))
            if not coordinates or not coordinate_names:
                continue
            component_scores = {
                name: percentile(
                    [values[name] for values in coordinates_by_entity.values()],
                    coordinates[name],
                )
                for name in sorted(coordinate_names)
            }
            score, family_scores = fund_potential_family_score(component_scores)
            row["rank_score"] = score
            row["score_components"] = {
                f"potential_{name}": value
                for name, value in component_scores.items()
            }
            row["investment_potential"] = {
                **dict(row.get("investment_potential") or {}),
                "score": score,
                "component_scores": component_scores,
                "family_scores": family_scores,
                "family_weights": {
                    "valuation": 0.50,
                    "factor_return_and_risk": 0.40,
                    "implementation_cost": 0.10,
                },
                "evidence_vote_receipt": (
                    (row.get("investment_potential") or {}).get("evidence_vote_receipt")
                    if verify_fund_evidence_vote_receipt(
                        (row.get("investment_potential") or {}).get("evidence_vote_receipt")
                    ) else None
                ),
                "normalization_population": population,
                "normalization_basis": "merged_unique_entities_within_implementation_sleeve",
                "peer_group": peer_group,
            }
            if row.get("screen_status") in {"qualified", "monitor"}:
                qualified = (
                    score >= minimum_fund_score
                    and all(bool(item.get("passed")) for item in row.get("criteria") or ())
                )
                row["screen_status"] = "qualified" if qualified else "monitor"
                row["next_activation"] = (
                    "candidate_research" if qualified else "monitor_next_source_epoch"
                )
    peer_ranked: list[tuple[int, str, dict[str, Any], int]] = []
    for peer_group, rows in fund_peer_groups.items():
        ranked = sorted(
            (row for row in rows if row.get("rank_score") is not None),
            key=lambda row: (-float(row["rank_score"]), str(row["candidate_id"])),
        )
        peer_ranked.extend(
            (peer_rank, peer_group, row, len(ranked))
            for peer_rank, row in enumerate(ranked, start=1)
        )
    peer_ranked.sort(key=lambda item: (item[0], item[1], str(item[2]["candidate_id"])))
    for fund_rank, (peer_rank, peer_group, row, peer_count) in enumerate(
        peer_ranked, start=1,
    ):
        row["investment_potential"] = {
            **dict(row.get("investment_potential") or {}),
            "rank": peer_rank,
            "ranked_count": peer_count,
            "rank_scope": f"implementation_sleeve:{peer_group}",
        }
        row["potential_rank"] = {
            "scope": "public_fund",
            "rank": fund_rank,
            "ranked_count": len(peer_ranked),
            "native_score": float(row["rank_score"]),
            "comparison_scope": f"implementation_sleeve:{peer_group}",
            "peer_rank": peer_rank,
            "peer_ranked_count": peer_count,
            "within_fund_order": "round_robin_by_peer_rank_then_sleeve",
        }
    candidates.sort(key=lambda row: (
        row.get("potential_rank") is None,
        int((row.get("potential_rank") or {}).get("rank") or 10**9),
        str(row["entity_kind"]),
        str(row["candidate_id"]),
    ))


def _assign_research_ranks(candidates: Iterable[dict[str, Any]]) -> None:
    """Rank only admitted survivors, preserving the potential-order audit trail."""
    research_rank = 0
    for row in candidates:
        row.pop("research_rank", None)
        if row.get("screen_status") == "qualified":
            research_rank += 1
            row["research_rank"] = research_rank


def _compile_rank_program_input(
    candidates: Iterable[Mapping[str, Any]], *, run_id: str, as_of: str,
    equity_benchmark_id: str,
) -> dict[str, Any]:
    """Freeze the full score-independent population used by rank challengers."""
    from .rank_program_tournament import compile_rank_program_input

    required_components = {
        "public_equity": (
            "durable_earnings_power", "price_implied_excess_return",
            "earnings_power_margin", "low_implied_growth",
        ),
        "public_fund": (
            "earnings_yield", "book_to_price",
            "factor_return_after_fee",
            "factor_return_per_volatility", "drawdown_resilience",
            "fee_efficiency",
        ),
    }
    lanes: dict[str, dict[str, Any]] = {}
    sleeve_benchmarks = {
        str(row["sleeve_id"]): str(row["symbol"]).upper()
        for row in public_sleeve_proxies()
    }
    all_source_refs: set[str] = set()
    for candidate in candidates:
        kind = str(candidate.get("entity_kind") or "")
        if kind not in required_components:
            continue
        if kind == "public_equity":
            lane_id = "public_equity"
            benchmark_id = equity_benchmark_id
            raw_components = candidate.get("score_components")
        else:
            potential = candidate.get("investment_potential")
            potential = potential if isinstance(potential, Mapping) else {}
            peer_group = str(potential.get("peer_group") or "unbound")
            lane_id = f"public_fund:{peer_group}"
            benchmark_id = sleeve_benchmarks.get(peer_group, "UNBOUND")
            raw_components = potential.get("component_scores")
        raw_components = raw_components if isinstance(raw_components, Mapping) else {}
        components = {
            name: float(raw_components[name])
            for name in required_components[kind]
            if name in raw_components and not isinstance(raw_components[name], bool)
            and math.isfinite(float(raw_components[name]))
        }
        source_refs = sorted({str(ref) for ref in candidate.get("source_refs") or () if ref})
        all_source_refs.update(source_refs)
        criteria = candidate.get("criteria")
        criteria = criteria if isinstance(criteria, list) else []
        screen_thresholds_pass = bool(criteria) and all(
            isinstance(item, Mapping) and item.get("passed") is True for item in criteria
        )
        component_contract_complete = len(components) == len(required_components[kind])
        factor_evidence_pass = (
            (candidate.get("beta_receipt") or {}).get("status") == "estimated"
            if kind == "public_equity" else True
        )
        evidence_contract_pass = (
            float((candidate.get("score_components") or {}).get("evidence_coverage", 0.0)) == 1.0
            and factor_evidence_pass
            if kind == "public_equity" else
            len(candidate.get("input_golden_leaves") or ()) == 1
            and verify_fund_evidence_vote_receipt(
                (candidate.get("investment_potential") or {}).get("evidence_vote_receipt")
            )
        )
        row_body = {
            "candidate_id": str(candidate.get("candidate_id") or ""),
            "entity_id": str(candidate.get("entity_id") or ""),
            "rank_program_eligible": bool(
                component_contract_complete and evidence_contract_pass
            ),
            "eligibility_checks": {
                "component_contract_complete": component_contract_complete,
                "evidence_contract_pass": evidence_contract_pass,
                "factor_evidence_pass": factor_evidence_pass,
                "screen_thresholds_pass": screen_thresholds_pass,
            },
            "components": components,
            "source_refs": source_refs,
        }
        row = {**row_body, "candidate_sha256": stable_sha256(row_body)}
        lane = lanes.setdefault(lane_id, {
            "lane_id": lane_id,
            "entity_kind": kind,
            "benchmark_id": benchmark_id,
            "candidates": [],
        })
        lane["candidates"].append(row)
    frozen_lanes = []
    for lane_id in sorted(lanes):
        lane = lanes[lane_id]
        lane["candidates"].sort(key=lambda row: (row["entity_id"], row["candidate_id"]))
        frozen_lanes.append(lane)
    return compile_rank_program_input(
        discovery_run_id=run_id,
        as_of=as_of,
        compiler_version=DISCOVERY_ENGINE_VERSION,
        eligibility_policy_id="evidence-and-component-completeness-v4",
        lanes=frozen_lanes,
        enumerated_candidate_count=sum(
            len(lane["candidates"]) for lane in frozen_lanes
        ),
        source_refs=sorted(all_source_refs),
    )


def _compile_fund(
    *, row: Mapping[str, Any], watchlist_id: str, as_of: str,
    config: Mapping[str, Any], input_leaf: str | None,
) -> dict[str, Any]:
    fund_identity = f"fund:{watchlist_id}:{row['entity_id']}"
    score, components = _fund_score(row)
    raw_valuation = row.get("valuation")
    _valuation_coordinates, valuation_blockers = bound_fund_valuation_coordinates(
        raw_valuation
    )
    valuation = (
        dict(raw_valuation)
        if not valuation_blockers and isinstance(raw_valuation, Mapping) else None
    )
    valued = bool(row.get("valuation_claim_allowed")) and valuation is not None
    analysis = row["analysis"]
    input_potential = dict(row.get("investment_potential") or {})
    if input_potential:
        vote_receipt = input_potential.get("evidence_vote_receipt")
    else:
        vote_receipt = (
            fund_evidence_vote_receipt(
                components,
                analysis_sha256=str(analysis.get("analysis_sha256") or "") or None,
                valuation_source_refs=list((valuation or {}).get("source_refs") or ()),
            )
            if components else None
        )
    evidence_vote_pass = verify_fund_evidence_vote_receipt(vote_receipt)
    paths = {
        "factor_implied_return": float(analysis["assumption_implied"]["return_without_residual_alpha"]),
        "maximum_drawdown": float(analysis["historical"]["maximum_drawdown"]),
        "leave_one_out_r2": float(analysis["fit"]["leave_one_out_r2"]),
    }
    if valuation:
        paths.update({
            "earnings_power_margin": float(valuation["earnings_power_margin"]),
            "implied_growth": float(valuation["implied_growth_median"]),
        })
    discovery_criteria = [
        _criterion(paths, raw) for raw in config.get("criteria", [])
        if isinstance(raw, Mapping) and str(raw.get("path") or "") in paths
    ]
    current_watchlist = bool(input_leaf)
    qualified = (
        row.get("screen_status") == "qualified" and valued
        and len(discovery_criteria) == len(config.get("criteria", []))
        and all(item["passed"] for item in discovery_criteria)
        and score is not None
        and score >= float(config.get("minimum_score", 0.50))
        and current_watchlist
        and evidence_vote_pass
    )
    refs = sorted(set(
        list(analysis.get("source_refs") or ())
        + list((valuation or {}).get("source_refs") or ())
        + list((row.get("fund_evidence") or {}).get("source_refs") or ())
    ))
    return _candidate({
        "candidate_id": fund_identity, "entity_id": str(row["entity_id"]),
        "entity_kind": "public_fund", "name": str(row.get("name") or row["entity_id"]),
        "as_of": as_of, "analysis_kind": "factor_decomposition_and_aggregate_valuation",
        "screen_status": (
            "qualified" if qualified else
            "blocked_watchlist_lineage" if not current_watchlist else
            "blocked_missing_aggregate_valuation"
            if valuation_blockers == ("aggregate_valuation_absent",) else
            "blocked_incompatible_valuation_lineage" if valuation_blockers else
            "blocked_evidence_vote_lineage" if not evidence_vote_pass else
            "needs_valuation_evidence" if not valued else "monitor"
        ),
        "rank_score": score, "score_components": components,
        "criteria": [*list(row.get("criteria") or ()), *discovery_criteria],
        "metrics": {
            "factor_implied_return": paths["factor_implied_return"],
            "residual_alpha": analysis["historical"]["residual_alpha_annualized"],
            "maximum_drawdown": analysis["historical"]["maximum_drawdown"],
            "leave_one_out_r2": analysis["fit"]["leave_one_out_r2"],
            "earnings_power_margin": (valuation or {}).get("earnings_power_margin"),
            "implied_growth": (valuation or {}).get("implied_growth_median"),
        },
        "watchlist_id": watchlist_id, "watchlist_candidate_id": row.get("candidate_id"),
        "investment_potential": {
            **input_potential,
            "evidence_vote_receipt": vote_receipt,
        },
        "valuation": valuation,
        "valuation_coordinate_blockers": list(valuation_blockers),
        "factor_analysis_sha256": analysis.get("analysis_sha256"),
        "fund_evidence": dict(row.get("fund_evidence") or {}),
        "source_refs": refs, "input_golden_leaves": [input_leaf] if input_leaf else [],
        "next_activation": (
            "candidate_research" if qualified else
            "rebuild_current_watchlist" if not current_watchlist else
            "rebuild_current_watchlist" if not evidence_vote_pass else
            "configure_aggregate_or_holdings_valuation" if not valued else
            "monitor_next_source_epoch"
        ),
        "research_prompt": str(row.get("thesis_prompt") or row.get("next_evidence_request") or ""),
    })


def compile_discovery_run(
    *, workspace: str | Path, workspace_config: Mapping[str, Any], policy: Mapping[str, Any],
    completed_at: str | None = None,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Enumerate the configured universe and return a run plus full valuation artifacts."""
    root = Path(workspace).expanduser().resolve()
    source_run = json.loads((root / "data" / "latest_source_run.json").read_text(encoding="utf-8"))
    as_of = canonical_timestamp(source_run.get("as_of"), "discovery source as_of")
    completion = canonical_timestamp(completed_at or _utc_now(), "discovery completed_at")
    equity_config = policy.get("equities") if isinstance(policy.get("equities"), Mapping) else {}
    manifest = load_source_manifest(
        root / str(workspace_config.get("source_manifest") or "sources.yaml")
    )
    configured_equity_ids = sorted({
        str(row.get("entity_id") or "").upper()
        for row in manifest.get("sources", [])
        if isinstance(row, Mapping) and row.get("enabled", True) is not False
        and row.get("adapter") == "sec_companyfacts" and row.get("entity_id")
    })
    equity_ids = (
        configured_equity_ids
        if policy.get("enabled", True) and equity_config.get("enabled", True)
        else []
    )
    benchmark_id = str(equity_config.get("benchmark_entity_id") or "SPY").upper()
    latest = _latest_observations(
        root / "data" / "observations.csv", as_of,
        entity_ids={*equity_ids, benchmark_id, "US-MARKET"},
    )
    latest_build_path = root / "state" / "latest_build.json"
    latest_build = json.loads(latest_build_path.read_text(encoding="utf-8")) if latest_build_path.is_file() else {}
    quality_leaves = {
        str(row.get("entity_id")): str(row.get("golden_leaf"))
        for row in latest_build.get("company_quality_statuses", [])
        if isinstance(row, Mapping) and row.get("status") == "compiled" and row.get("golden_leaf")
    }
    watchlist_leaves = {
        str(row.get("watchlist_id")): str(row.get("golden_leaf"))
        for row in latest_build.get("watchlist_statuses", [])
        if isinstance(row, Mapping) and row.get("status") == "compiled" and row.get("golden_leaf")
    }
    candidates: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    valuations: dict[str, dict[str, Any]] = {}
    policy_ref = _policy_ref(policy)
    if policy.get("enabled", True) and equity_config.get("enabled", True):
        price_point_rows: dict[str, list[PricePoint]] = {}
        for point in load_price_points(
            root / "data" / "observations.csv", as_of=as_of,
            metric_id="adjusted_price",
            entity_ids={*equity_ids, benchmark_id},
        ):
            price_point_rows.setdefault(point.entity_id, []).append(point)
        price_points_by_entity = {
            entity_id: tuple(points) for entity_id, points in price_point_rows.items()
        }
        for entity_id in equity_ids:
            quality_path = root / "quality" / f"{entity_id.lower()}.json"
            try:
                quality = json.loads(quality_path.read_text(encoding="utf-8"))
                candidate, envelope = _compile_equity(
                    entity_id=entity_id, quality=quality, latest=latest,
                    price_points_by_entity=price_points_by_entity, as_of=as_of,
                    config=equity_config, policy=policy,
                    input_leaf=quality_leaves.get(entity_id),
                )
                candidates.append(candidate)
                valuations[entity_id] = envelope
            except (KeyError, OSError, TypeError, ValueError) as error:
                failures.append({"candidate_id": f"equity:{entity_id}", "reason": str(error)})
                candidates.append(_candidate({
                    "candidate_id": f"equity:{entity_id}", "entity_id": entity_id,
                    "entity_kind": "public_equity", "name": entity_id, "as_of": as_of,
                    "analysis_kind": "durable_earnings_and_formal_valuation",
                    "screen_status": "blocked", "rank_score": None,
                    "score_components": {}, "criteria": [], "metrics": {},
                    "source_refs": [
                        policy_ref,
                        f"source_run:{str(source_run.get('run_sha256') or 'unavailable')}",
                    ],
                    "input_golden_leaves": [],
                    "next_activation": "repair_evidence_contract", "error": str(error),
                }))
    fund_ids: list[str] = []
    funds_config = policy.get("funds") if isinstance(policy.get("funds"), Mapping) else {}
    if policy.get("enabled", True) and funds_config.get("enabled", True):
        for result_path in sorted((root / "watchlists" / "results").glob("*.json")):
            try:
                result = json.loads(result_path.read_text(encoding="utf-8"))
                watchlist_id = str(result["watchlist_id"])
                for row in result.get("candidates", []):
                    if not isinstance(row, Mapping):
                        continue
                    fund_ids.append(f"{watchlist_id}:{row['entity_id']}")
                    candidates.append(_compile_fund(
                        row=row, watchlist_id=watchlist_id, as_of=as_of,
                        config=funds_config,
                        input_leaf=watchlist_leaves.get(watchlist_id),
                    ))
            except (KeyError, OSError, TypeError, ValueError) as error:
                failures.append({"candidate_id": f"watchlist:{result_path.stem}", "reason": str(error)})
    failed_source_rows = [
        dict(row) for row in source_run.get("source_statuses", [])
        if isinstance(row, Mapping) and row.get("status") == "failed"
    ]
    source_status_by_id = {
        str(row.get("source_id") or ""): str(row.get("status") or "")
        for row in source_run.get("source_statuses", [])
        if isinstance(row, Mapping) and row.get("source_id")
    }
    failed_source_ids = {
        source_id for source_id, status in source_status_by_id.items()
        if status == "failed"
    }
    for candidate in candidates:
        affected = sorted(set(candidate.get("source_refs") or ()) & failed_source_ids)
        if not affected:
            continue
        candidate["status_before_freshness_gate"] = candidate.get("screen_status")
        candidate["screen_status"] = "stale_evidence"
        candidate["stale_source_ids"] = affected
        candidate["next_activation"] = "repair_source_refresh"
        candidate.pop("candidate_sha256", None)
        candidate["candidate_sha256"] = stable_sha256(candidate)
    _rank_candidate_lanes(
        candidates,
        minimum_fund_score=float(funds_config.get("minimum_score", 0.50)),
    )
    run_id = (
        f"discovery-{completion.translate(str.maketrans('', '', '-:TZ'))}-"
        f"{stable_sha256({'source': source_run.get('run_sha256'), 'policy': policy})[:8]}"
    )
    rank_program_input = _compile_rank_program_input(
        candidates,
        run_id=run_id,
        as_of=as_of,
        equity_benchmark_id=benchmark_id,
    )
    capacity = int(policy.get("max_ranked_candidates", 100))
    qualified = [row for row in candidates if row.get("screen_status") == "qualified"]
    other_states = [row for row in candidates if row.get("screen_status") != "qualified"]
    limited = qualified + other_states[:max(0, capacity - len(qualified))]
    for rank, row in enumerate(limited, start=1):
        row["rank"] = rank
    _assign_research_ranks(limited)
    for row in limited:
        body = {key: value for key, value in row.items() if key != "candidate_sha256"}
        row["candidate_sha256"] = stable_sha256(body)
    scope_closed = not failures and len(candidates) == len(equity_ids) + len(fund_ids)
    body: dict[str, Any] = {
        "schema": DISCOVERY_RUN_SCHEMA,
        "compiler_version": DISCOVERY_ENGINE_VERSION,
        "run_id": run_id,
        "workspace_name": str(workspace_config.get("name") or "JaggedThoughts Capital Workbench"),
        "owner": str(workspace_config.get("owner") or "operator-paper-book"),
        "as_of": as_of, "completed_at": completion,
        "source_run_sha256": source_run.get("run_sha256"),
        "policy_sha256": stable_sha256(policy),
        "authority": "analysis_and_research_request_only",
        "evidence_refresh": {
            "complete": not failed_source_rows,
            "failed_sources": failed_source_rows,
            "not_scheduled_source_ids": sorted(
                source_id for source_id, status in source_status_by_id.items()
                if status == "not_scheduled"
            ),
            "meaning": (
                "Complete means every source selected for this bounded refresh succeeded. "
                "A failed dependency blocks its candidate; a source outside this bounded refresh "
                "retains its last point-in-time observation subject to typed input-age gates."
            ),
        },
        "enumeration": {
            "method": "declared_universe_recursive_analysis",
            "equity_universe": equity_ids, "fund_universe": sorted(fund_ids),
            "enumerated_count": len(candidates), "ranked_count": len(limited),
            "truncated": len(limited) < len(candidates),
            "ranking_contract": {
                "potential_scope": "public_equity_or_fund_implementation_sleeve",
                "equity_order": "best_doctrine_rank_then_balanced_rank",
                "cross_lane_order": "ordinal_potential_rank_then_entity_kind",
                "presentation_truncation": (
                    "qualified_survivors_first_then_other_states_preserving_potential_order"
                ),
                "meaning": (
                    "Equity doctrine ranks compare the same equity population without blending "
                    "doctrine-native scores. Fund scores compare only the same "
                    "implementation sleeve; sleeve ranks are interleaved before the fund lane "
                    "is interleaved with equities. Unlike return concepts are never averaged."
                ),
            },
        },
        "frontier_closure": {
            "scope_closed": scope_closed,
            "scope": "configured enrolled equities plus compiled fund watchlists at one evidence epoch",
            "represented_candidate_ids": [str(row["candidate_id"]) for row in candidates],
            "failures": failures,
            "meaning": "Closure applies only to the declared finite universe and assumption grids.",
        },
        "qualified_count": sum(row.get("screen_status") == "qualified" for row in limited),
        "candidate_count": len(limited), "candidates": limited,
        "rank_program_input": rank_program_input,
        "activation_points": activation_map(),
    }
    return {**body, "run_sha256": stable_sha256(body)}, valuations


__all__ = [
    "DISCOVERY_CANDIDATE_SCHEMA", "DISCOVERY_ENGINE_VERSION", "DISCOVERY_POLICY_SCHEMA",
    "DISCOVERY_QUALITY_FRESHNESS_SCHEMA", "DISCOVERY_RUN_SCHEMA",
    "activation_map", "compile_discovery_run", "default_discovery_policy",
    "discovery_schedule_status", "load_discovery_policy",
    "project_discovery_quality_freshness",
]
