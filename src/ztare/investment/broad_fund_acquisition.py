"""Information-yield acquisition plans for broad public-fund peer cells."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import re
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256

from .broad_fund_scout import (
    BROAD_FUND_SCOUT_SCHEMA,
    _classify,
    _cell_id,
    _evidence,
    _validate_policy,
)
from .contracts import canonical_timestamp, require_text, timestamp_key
from .household_allocation import CAPITAL_MARKET_BASIS_SCHEMA
from .public_capital_market_basis import PUBLIC_SLEEVE_IDS, public_sleeve_proxies
from .sources import PUBLIC_SOURCE_MANIFEST_SCHEMA, SOURCE_RUN_SCHEMA
from .universe import _fund_issuer_source
from .universe_catalog import CATALOG_SCHEMA


BROAD_FUND_ACQUISITION_PLAN_SCHEMA = "jaggedthoughts-broad-fund-acquisition-plan-v2"
_COORDINATES = (
    "factor_analysis", "aggregate_valuation", "issuer_evidence", "concentration",
    "implementation",
)
_ADAPTER_CAPABILITIES = {
    "avantis_fundamentals": {"aggregate_valuation", "issuer_evidence", "concentration"},
    "first_trust_fundamentals": {"aggregate_valuation", "issuer_evidence", "implementation"},
    "first_trust_holdings": {"concentration"},
    "harbor_fundamentals": {"aggregate_valuation", "issuer_evidence", "concentration"},
    "ishares_fundamentals": {"aggregate_valuation", "issuer_evidence", "concentration", "implementation"},
    "vanguard_fundamentals": {"aggregate_valuation", "issuer_evidence"},
    "yahoo_chart_daily": {"factor_analysis"},
}
_FACTOR_SOURCE_IDS = (
    "nyu_us_implied_erp", "yahoo_spy_daily", "yahoo_iwd_daily", "yahoo_iwf_daily",
    "yahoo_ijr_daily", "yahoo_mtum_daily", "yahoo_qual_daily",
)
_EQUITY_SLEEVES = {"us_equity", "international_equity"}
_CASH_PATTERN = re.compile(
    r"\b(t-?bills?|treasury bills?|0[- ]?3 month treasury|1[- ]?3 month t-?bill|"
    r"cash management|money market)\b"
)
_TIPS_PATTERN = re.compile(r"\b(tips|inflation[- ]protected)\b")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _verified(raw: Mapping[str, Any], schema: str, digest_field: str) -> dict[str, Any]:
    row = dict(raw)
    if row.get("schema") != schema:
        raise ValueError(f"artifact requires {schema}")
    claimed = require_text(row.get(digest_field), digest_field)
    if claimed != stable_sha256({key: value for key, value in row.items() if key != digest_field}):
        raise ValueError(f"{digest_field} does not match its payload")
    return row


def _current_coordinates(evidence: Mapping[str, Any]) -> set[str]:
    return {
        coordinate for coordinate, field in (
            ("factor_analysis", "factor_analysis_ready"),
            ("aggregate_valuation", "aggregate_valuation_ready"),
            ("issuer_evidence", "issuer_evidence_ready"),
            ("concentration", "concentration_ready"),
            ("implementation", "implementation_ready"),
        ) if evidence.get(field)
    }


def _source_rows(
    fund: Mapping[str, Any], existing: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    entity_id = str(fund["symbol"]).upper()
    rows = [
        dict(row) for row in existing
        if isinstance(row, Mapping) and str(row.get("entity_id") or "").upper() == entity_id
        and row.get("enabled", True)
    ]
    adapters = {str(row.get("adapter") or "") for row in rows}
    if "yahoo_chart_daily" not in adapters:
        rows.append({
            "id": f"yahoo_{entity_id.lower()}_daily", "adapter": "yahoo_chart_daily",
            "entity_id": entity_id, "status": "prospective_enrollment",
        })
    issuer = _fund_issuer_source(entity_id, str(fund["name"]))
    if issuer is not None and issuer["adapter"] not in adapters:
        rows.append({**issuer, "status": "prospective_enrollment"})
    if issuer is not None and issuer["adapter"] == "first_trust_fundamentals" and "first_trust_holdings" not in adapters:
        rows.append({
            "id": f"first_trust_{entity_id.lower()}_holdings",
            "adapter": "first_trust_holdings", "entity_id": entity_id,
            "status": "prospective_enrollment",
        })
    return rows


def _implementation_sleeve(cell: Mapping[str, str], name: str) -> str | None:
    """Map observable fund identity to the exact public allocation sleeve."""
    asset_class = cell.get("asset_class")
    region = cell.get("region")
    normalized = " ".join(name.lower().split())
    if asset_class == "equity":
        if region == "us":
            return "us_equity"
        if region in {"international", "developed_ex_us", "emerging_markets"}:
            return "international_equity"
        return None
    if asset_class != "fixed_income" or region in {
        "international", "developed_ex_us", "emerging_markets", "global",
    }:
        return None
    if _TIPS_PATTERN.search(normalized):
        return "us_tips"
    if _CASH_PATTERN.search(normalized):
        return "cash"
    return "usd_bonds"


def _basis_view(raw: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Accept the validated basis or its public-acquisition envelope."""
    if not raw:
        return None
    basis = raw.get("capital_market_basis") if isinstance(
        raw.get("capital_market_basis"), Mapping
    ) else raw
    if not isinstance(basis, Mapping) or basis.get("schema") != CAPITAL_MARKET_BASIS_SCHEMA:
        raise ValueError(f"capital market basis requires {CAPITAL_MARKET_BASIS_SCHEMA}")
    row = dict(basis)
    claimed = require_text(row.get("basis_sha256"), "basis_sha256")
    if claimed != stable_sha256({key: value for key, value in row.items() if key != "basis_sha256"}):
        raise ValueError("basis_sha256 does not match its payload")
    assets = {
        str(value.get("asset_id")): dict(value)
        for value in row.get("asset_classes") or () if isinstance(value, Mapping)
    }
    if set(assets) != set(PUBLIC_SLEEVE_IDS):
        raise ValueError("capital market basis must cover the exact public sleeve universe")
    if row.get("capital_authority") is not False:
        raise ValueError("capital market basis must deny capital authority")
    scenario = next((
        dict(value) for value in row.get("return_scenarios") or ()
        if isinstance(value, Mapping) and value.get("scenario_id") == "current_source_anchor"
    ), None)
    if scenario is None:
        raise ValueError("capital market basis lacks current_source_anchor")
    if scenario.get("expected_return_claim") is not False or not scenario.get("source_refs"):
        raise ValueError("capital market assumptions require source refs and no return claim")
    returns = dict(scenario.get("expected_returns") or {})
    if set(PUBLIC_SLEEVE_IDS) - set(returns):
        raise ValueError("capital market basis does not cover the public sleeve universe")
    return {
        "basis_id": row.get("basis_id"), "basis_sha256": claimed,
        "as_of": canonical_timestamp(row.get("as_of"), "capital market basis as_of"),
        "asset_classes": assets,
        "scenario_id": scenario["scenario_id"],
        "expected_returns": {key: float(returns[key]) for key in PUBLIC_SLEEVE_IDS},
        "source_refs": sorted(str(value) for value in scenario.get("source_refs") or ()),
        "expected_return_claim": False,
    }


def _member(
    fund: Mapping[str, Any], *, cell: Mapping[str, str], evidence: Mapping[str, Any],
    source_rows: Iterable[Mapping[str, Any]], active_jobs: set[str], catalog_sha256: str,
) -> dict[str, Any]:
    current = _current_coordinates(evidence)
    sources = [dict(row) for row in source_rows]
    supported = set().union(*(
        _ADAPTER_CAPABILITIES.get(str(row.get("adapter") or ""), set()) for row in sources
    )) if sources else set()
    required = set(_COORDINATES)
    if cell.get("asset_class") != "equity":
        required.discard("aggregate_valuation")
        supported.discard("aggregate_valuation")
    missing = required - current
    unsupported = sorted(missing - supported)
    requested = sorted(missing & supported)
    security_id = str(fund["security_id"])
    active = security_id in active_jobs
    needs_job = bool(requested) and not active
    source_ids = sorted({str(row.get("id") or "") for row in sources if row.get("id")})
    sleeve_id = _implementation_sleeve(cell, str(fund["name"]))
    body = {
        "security_id": security_id,
        "entity_id": fund["symbol"],
        "name": fund["name"],
        "cell": dict(cell),
        "current_coordinates": sorted(current),
        "requested_coordinates": requested,
        "unsupported_coordinates": unsupported,
        "source_requirements": source_ids,
        "source_adapters": sorted({str(row.get("adapter") or "") for row in sources}),
        "existing_active_job": active,
        "new_job_required": needs_job,
        "completion_possible_with_registered_adapters": not unsupported,
        "implementation_sleeve_id": sleeve_id,
        "implementation_sleeve_source_refs": (
            [f"catalog:{catalog_sha256}:security:{security_id}"] if sleeve_id else []
        ),
        "expected_return_used": False,
        "capital_authority": False,
    }
    return {**body, "member_sha256": stable_sha256(body)}


def compile_broad_fund_acquisition_plan(
    *,
    scout: Mapping[str, Any],
    catalog: Mapping[str, Any],
    policy: Mapping[str, Any],
    source_manifest: Mapping[str, Any],
    source_run: Mapping[str, Any],
    watchlist_results: Iterable[Mapping[str, Any]] = (),
    existing_jobs: Iterable[Mapping[str, Any]] = (),
    capital_market_basis: Mapping[str, Any] | None = None,
    target_group_count: int = 2,
    compiled_at: str | None = None,
) -> dict[str, Any]:
    """Choose the least-blocked diverse peer cells without performing acquisition."""

    if not 1 <= target_group_count <= 2:
        raise ValueError("target_group_count must be one or two")
    broad = _verified(scout, BROAD_FUND_SCOUT_SCHEMA, "scout_sha256")
    market = _verified(catalog, CATALOG_SCHEMA, "catalog_sha256")
    rules = _validate_policy(policy)
    if broad.get("catalog_sha256") != market["catalog_sha256"]:
        raise ValueError("broad scout and catalog identities differ")
    if broad.get("policy_sha256") != rules["policy_sha256"]:
        raise ValueError("broad scout and policy identities differ")
    if source_manifest.get("schema") != PUBLIC_SOURCE_MANIFEST_SCHEMA:
        raise ValueError(f"source manifest requires {PUBLIC_SOURCE_MANIFEST_SCHEMA}")
    source_epoch = _verified(source_run, SOURCE_RUN_SCHEMA, "run_sha256")
    basis = _basis_view(capital_market_basis)
    if basis and timestamp_key(basis["as_of"]) > timestamp_key(str(source_epoch["as_of"])):
        raise ValueError("capital market basis is later than the acquisition source epoch")
    sources = [row for row in source_manifest.get("sources") or () if isinstance(row, Mapping)]
    source_manifest_sha = stable_sha256(source_manifest)
    all_watchlists = list(watchlist_results)
    watchlists = [
        row for row in all_watchlists
        if timestamp_key(canonical_timestamp(row.get("as_of"), "fund watchlist as_of"))
        <= timestamp_key(str(source_epoch["as_of"]))
    ]
    evidence = _evidence(watchlists)
    watchlist_shas = sorted(str(row["watchlist_sha256"]) for row in watchlists)
    active_jobs = {
        str(row.get("security_id") or (row.get("payload") or {}).get("security_id") or "")
        for row in existing_jobs if isinstance(row, Mapping)
        and str(row.get("status") or "") in {"queued", "pending", "running", "claimed"}
    }
    cells: dict[str, dict[str, str]] = {}
    funds_by_cell: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for fund in market.get("securities") or ():
        if not isinstance(fund, Mapping) or fund.get("entity_kind") != "public_fund":
            continue
        name = str(fund.get("name") or "")
        if (
            fund.get("security_kind") != "exchange_traded_fund"
            or not fund.get("last_price")
            or any(re.search(pattern, name.lower()) for pattern in rules["exclude_name_patterns"])
        ):
            continue
        cell = _classify(name, rules)[0]
        cell_id = _cell_id(cell)
        sleeve_id = _implementation_sleeve(cell, name)
        if cell.get("asset_class") == "fixed_income" and sleeve_id:
            cell_id = f"sleeve:{sleeve_id}|{cell_id}"
        cells[cell_id] = cell
        funds_by_cell[cell_id].append(fund)

    groups: list[dict[str, Any]] = []
    singleton_cells: list[str] = []
    all_members_by_sleeve: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for cell_id, funds in sorted(funds_by_cell.items()):
        members = [
            _member(
                fund, cell=cells[cell_id], evidence=evidence.get(str(fund["symbol"]).upper(), {}),
                source_rows=_source_rows(fund, sources), active_jobs=active_jobs,
                catalog_sha256=market["catalog_sha256"],
            ) for fund in funds
        ]
        for member in members:
            if member.get("implementation_sleeve_id"):
                all_members_by_sleeve[member["implementation_sleeve_id"]].append(member)
        if len(members) < 2:
            singleton_cells.append(cell_id)
            continue
        ready = sorted(
            (row for row in members if not row["requested_coordinates"] and not row["unsupported_coordinates"]),
            key=lambda row: str(row["security_id"]),
        )
        ranked = sorted(members, key=lambda row: (
            len(row["unsupported_coordinates"]), bool(row["new_job_required"]),
            -len(row["requested_coordinates"]), str(row["security_id"]),
        ))
        pair = ready[:2] if len(ready) >= 2 else ranked[:2]
        adapter_gaps = {
            f"{adapter}:{coordinate}"
            for row in pair
            for coordinate in row["unsupported_coordinates"]
            for adapter in ([
                value for value in row["source_adapters"] if value != "yahoo_chart_daily"
            ] or ["unbound_public_source"])
        }
        jobs = sum(bool(row["new_job_required"]) for row in pair)
        fillable = sum(len(row["requested_coordinates"]) for row in pair)
        pair_sleeves = {row["implementation_sleeve_id"] for row in pair}
        sleeve_id = next(iter(pair_sleeves)) if len(pair_sleeves) == 1 else None
        groups.append({
            "peer_group_id": cell_id,
            "peer_group": dict(cells[cell_id]),
            "implementation_sleeve_id": sleeve_id,
            "selected_cell_ids": [cell_id],
            "members": pair,
            "comparison_ready": len(ready) >= 2,
            "unsupported_coordinate_count": sum(len(row["unsupported_coordinates"]) for row in pair),
            "adapter_capability_gaps": sorted(adapter_gaps),
            "new_job_count": jobs,
            "fillable_coordinate_count": fillable,
            "information_yield_per_new_job": round(fillable / max(1, jobs), 8),
        })

    completed_groups = [row for row in groups if row["comparison_ready"]]
    uncovered_groups = [row for row in groups if not row["comparison_ready"]]
    completed_by_sleeve = Counter(
        row["implementation_sleeve_id"] for row in completed_groups
        if row.get("implementation_sleeve_id")
    )
    queue_eligible = [
        row for row in uncovered_groups
        if row.get("implementation_sleeve_id") in _EQUITY_SLEEVES
    ]
    ordered = sorted(queue_eligible, key=lambda group: (
        completed_by_sleeve[group["implementation_sleeve_id"]],
        bool(group["adapter_capability_gaps"]) and not group["new_job_count"],
        int(group["new_job_count"]) + len(group["adapter_capability_gaps"]),
        len(group["adapter_capability_gaps"]),
        -int(group["fillable_coordinate_count"]),
        str(group["peer_group_id"]),
        tuple(str(row["security_id"]) for row in group["members"]),
    ))
    chosen = []
    for group in ordered:
        if any(
            prior["implementation_sleeve_id"] == group["implementation_sleeve_id"]
            for prior in chosen
        ):
            continue
        chosen.append(group)
        if len(chosen) == target_group_count:
            break
    if len(chosen) < target_group_count:
        chosen_ids = {row["peer_group_id"] for row in chosen}
        chosen.extend(
            row for row in ordered if row["peer_group_id"] not in chosen_ids
        )
        chosen = chosen[:target_group_count]

    proxy_by_sleeve = {row["sleeve_id"]: row for row in public_sleeve_proxies()}
    same_sleeve_cohorts = []
    for sleeve_id in PUBLIC_SLEEVE_IDS:
        proxy = proxy_by_sleeve[sleeve_id]
        candidates = [
            row for row in all_members_by_sleeve[sleeve_id]
            if str(row["entity_id"]).upper() != proxy["symbol"]
        ]
        ranked = sorted(candidates, key=lambda row: (
            len(row["unsupported_coordinates"]),
            -len(row["current_coordinates"]),
            -len(row["requested_coordinates"]),
            str(row["security_id"]),
        ))
        expected = basis["expected_returns"][sleeve_id] if basis else None
        cash_hurdle = basis["expected_returns"]["cash"] if basis else None
        equity_lane = sleeve_id in _EQUITY_SLEEVES
        cohort_body = {
            "sleeve_id": sleeve_id,
            "basis_proxy": dict(proxy),
            "catalog_candidate_count": len(candidates),
            "research_candidates": [{
                "research_rank": index + 1,
                **{key: row[key] for key in (
                    "security_id", "entity_id", "name", "member_sha256",
                )},
                "current_coordinate_count": len(row["current_coordinates"]),
                "fillable_coordinate_count": len(row["requested_coordinates"]),
                "unsupported_coordinates": row["unsupported_coordinates"],
                "ranking_basis": "evidence_closeness_and_fillable_information_yield",
                "expected_return_used": False,
                "alpha_claim": False,
            } for index, row in enumerate(ranked[:5])],
            "basis_sha256": basis["basis_sha256"] if basis else None,
            "basis_scenario_id": basis["scenario_id"] if basis else None,
            "basis_expected_annual_return": expected,
            "cash_hurdle_expected_annual_return": cash_hurdle,
            "assumption_spread_to_cash": (
                round(expected - cash_hurdle, 12)
                if expected is not None and cash_hurdle is not None else None
            ),
            "assumption_spread_identity": (
                "shared_sleeve_scenario_assumption_not_security_alpha"
                if basis else "capital_market_basis_unavailable"
            ),
            "state_price_use": "none_without_candidate_payoff_claims",
            "research_queue": "investment_broad_fund_source_acquisition",
            "tournament_lane": "factor_return_after_fee_v1" if equity_lane else None,
            "status": (
                "existing_queue_and_tournament"
                if equity_lane else "research_cohort_only"
            ),
            "next_activation": (
                "acquire_then_compare_in_existing_fund_tournament"
                if equity_lane else
                "compile_defensive_fee_duration_credit_liquidity_comparison_contract"
            ),
            "expected_return_used_for_research_rank": False,
            "alpha_claim": False,
            "capital_authority": False,
        }
        same_sleeve_cohorts.append({
            **cohort_body, "cohort_sha256": stable_sha256(cohort_body),
        })

    planned_members = {
        str(member["security_id"]): {
            **member,
            "peer_group_id": group["peer_group_id"],
            "comparison_cell": dict(group["peer_group"]),
        }
        for group in chosen for member in group["members"]
    }
    jobs = []
    # ``planned_members`` retains selected-cell/member order. Preserve it so a
    # bounded acquisition batch finishes one comparable pair before opening
    # the next cell.
    for member in planned_members.values():
        if not member["new_job_required"]:
            continue
        job_body = {
            "schema": "jaggedthoughts-broad-fund-acquisition-job-v1",
            "security_id": member["security_id"], "entity_id": member["entity_id"],
            "name": member["name"],
            "member_sha256": member["member_sha256"],
            "source_run_sha256": source_epoch["run_sha256"],
            "requested_coordinates": member["requested_coordinates"],
            "source_requirements": member["source_requirements"],
            "peer_group_id": member["peer_group_id"],
            "comparison_cell": member["comparison_cell"],
            "implementation_sleeve_id": member["implementation_sleeve_id"],
            "implementation_sleeve_source_refs": member["implementation_sleeve_source_refs"],
            "expected_exit": "comparison_ready_or_typed_source_gap",
            "required_capability": "public_market_source_enrichment",
            "expected_return_used": False, "capital_authority": False,
        }
        jobs.append({**job_body, "job_sha256": stable_sha256(job_body)})

    planned_source_ids = {source_id for job in jobs for source_id in job["source_requirements"]}
    existing_source_ids = {str(row.get("id") or "") for row in sources}
    factor_needed = any("factor_analysis" in row["requested_coordinates"] for row in planned_members.values())
    unsupported = [
        {"security_id": member["security_id"], "entity_id": member["entity_id"], "coordinates": member["unsupported_coordinates"]}
        for member in planned_members.values() if member["unsupported_coordinates"]
    ]
    adapter_gaps = sorted({gap for group in chosen for gap in group["adapter_capability_gaps"]})
    waiting_on_active_jobs = any(
        member["existing_active_job"] and member["requested_coordinates"]
        for group in chosen for member in group["members"]
    )
    completed = canonical_timestamp(compiled_at or _now(), "compiled_at")
    coverage = {
        "observed_cell_count": len(funds_by_cell),
        "comparable_peer_group_count": len(groups),
        "completed_peer_group_count": len(completed_groups),
        "residual_peer_group_count": len(uncovered_groups),
        "blocked_peer_group_count": sum(
            bool(row["adapter_capability_gaps"]) and not row["new_job_count"]
            for row in uncovered_groups
        ),
        "singleton_cell_count": len(singleton_cells),
        "singleton_cell_ids": singleton_cells,
        "comparison_coverage_fraction": (
            len(completed_groups) / len(groups) if groups else 0.0
        ),
    }
    body = {
        "schema": BROAD_FUND_ACQUISITION_PLAN_SCHEMA,
        "compiled_at": completed,
        "catalog_sha256": market["catalog_sha256"],
        "scout_sha256": broad["scout_sha256"],
        "policy_sha256": rules["policy_sha256"],
        "source_manifest_sha256": source_manifest_sha,
        "source_run_sha256": source_epoch["run_sha256"],
        "watchlist_sha256s": watchlist_shas,
        "selection_epoch": {
            "compiled_at": completed,
            "catalog_sha256": market["catalog_sha256"],
            "source_run_sha256": source_epoch["run_sha256"],
            "source_as_of": source_epoch.get("as_of"),
            "watchlist_sha256s": watchlist_shas,
            "ignored_future_watchlist_count": len(all_watchlists) - len(watchlists),
        },
        "target_group_count": target_group_count,
        "selected_group_count": len(chosen),
        "selected_groups": chosen,
        "completed_peer_groups": completed_groups,
        "same_sleeve_research_cohorts": same_sleeve_cohorts,
        "same_sleeve_contract": {
            "sleeve_ids": list(PUBLIC_SLEEVE_IDS),
            "single_queue": "investment_broad_fund_source_acquisition",
            "single_tournament": "fund_program_rank_tournament",
            "tournament_eligible_sleeves": sorted(_EQUITY_SLEEVES),
            "research_only_sleeves": ["cash", "usd_bonds", "us_tips"],
            "cross_sleeve_security_ranking": False,
            "expected_return_assumption_is_alpha": False,
        },
        "coverage": coverage,
        "new_job_count": len(jobs),
        "minimum_acquisition_count": len(jobs) + len(adapter_gaps),
        "jobs": jobs,
        "required_capability_acquisitions": [
            {
                "capability_gap": gap,
                "required_capability": "public_market_source_adapter_extension",
                "expected_exit": "typed_adapter_capability_or_public_evidence_impossibility",
                "capital_authority": False,
            }
            for gap in adapter_gaps
        ],
        "shared_source_batches": {
            "factor_benchmarks": {
                "required": factor_needed,
                "source_ids": list(_FACTOR_SOURCE_IDS) if factor_needed else [],
                "missing_source_ids": sorted(set(_FACTOR_SOURCE_IDS) - existing_source_ids) if factor_needed else [],
            },
            "fund_sources": {
                "source_ids": sorted(planned_source_ids),
                "already_registered": sorted(planned_source_ids & existing_source_ids),
                "prospective_enrollment": sorted(planned_source_ids - existing_source_ids),
            },
        },
        "unsupported_public_evidence": unsupported,
        "missing_adapter_capabilities": adapter_gaps,
        "status": (
            "comparison_coverage_ready" if not uncovered_groups
            else "ready_to_enqueue" if jobs
            else "acquisition_in_progress" if waiting_on_active_jobs
            else "blocked_unsupported_public_evidence"
        ),
        "comparisons_when_completed": [
            {
                "peer_group_id": group["peer_group_id"], "peer_group": group["peer_group"],
                "selected_cell_ids": group["selected_cell_ids"],
                "member_security_ids": [row["security_id"] for row in group["members"]],
                "currently_schedulable_jobs_are_sufficient": not group["adapter_capability_gaps"],
                "remaining_adapter_capability_gaps": group["adapter_capability_gaps"],
            }
            for group in chosen
        ],
        "selection_objective": (
            "rotate the two typed equity implementation sleeves through one queue; within each "
            "sleeve exclude completed exact cells, minimize source and adapter cost, then maximize "
            "fillable evidence with deterministic cell and security tie-breaks"
        ),
        "next_activation": (
            "coverage_complete" if not uncovered_groups else
            "acquire_selected_peer_groups" if jobs else
            "await_active_peer_group_acquisition" if waiting_on_active_jobs else
            "extend_public_source_adapters"
        ),
        "expected_return_used": False,
        "security_rank_override": False,
        "portfolio_weight": 0.0,
        "capital_authority": False,
    }
    return {**body, "plan_sha256": stable_sha256(body)}


__all__ = ["BROAD_FUND_ACQUISITION_PLAN_SCHEMA", "compile_broad_fund_acquisition_plan"]
