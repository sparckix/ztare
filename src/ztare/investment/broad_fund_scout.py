"""Breadth-first public-fund acquisition over source-bound catalog cells."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import re
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, require_text
from .universe_catalog import CATALOG_SCHEMA
from .watchlist import WATCHLIST_RESULT_SCHEMA


BROAD_FUND_POLICY_SCHEMA = "jaggedthoughts-broad-fund-scout-policy-v1"
BROAD_FUND_SCOUT_SCHEMA = "jaggedthoughts-broad-fund-scout-v1"
_DIMENSIONS = ("asset_class", "region", "size", "style", "factor")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def broad_fund_scout_policy(*, max_results: int = 48, max_per_cell: int = 1) -> dict[str, Any]:
    """Return the default observable-cell policy without naming preferred funds."""

    body = {
        "schema": BROAD_FUND_POLICY_SCHEMA,
        "policy_id": "jaggedthoughts-public-fund-breadth",
        "version": "1",
        "max_results": max_results,
        "max_per_cell": max_per_cell,
        "unknown_value": "unknown",
        "exclude_name_patterns": [
            r"\b[234]x\b", r"\bdaily\b", r"\bbull\b", r"\bbear\b", r"\binverse\b",
            r"\bsingle[- ]stock\b", r"\bweeklypay\b", r"\bautocallable\b",
        ],
        "dimensions": {
            "asset_class": [
                {"value": "fixed_income", "patterns": [r"\bbond\b", r"\btreasur", r"fixed income", r"\bmunicipal\b", r"\bmortgage\b", r"\bclo\b", r"\bcredit\b"]},
                {"value": "real_assets", "patterns": [r"\bgold\b", r"\bsilver\b", r"\bcommodit", r"real estate", r"\breit\b", r"infrastructure", r"natural resources"]},
                {"value": "multi_asset", "patterns": [r"asset allocation", r"multi[- ]asset", r"\bbalanced\b"]},
                {"value": "digital_asset", "patterns": [r"\bbitcoin\b", r"\bether", r"\bcrypto"]},
                {"value": "equity", "patterns": [r"\bequit", r"\bstock", r"\bshares\b", r"\bs&p\b", r"\brussell\b", r"\bmsci\b", r"\bnasdaq\b", r"\bvalue\b", r"\bgrowth\b", r"\bdividend\b", r"\bmomentum\b", r"\bquality\b", r"\bcap\b"]},
            ],
            "region": [
                {"value": "emerging_markets", "patterns": [r"emerging market", r"\bem\b"]},
                {"value": "developed_ex_us", "patterns": [r"developed.*ex[- .]?u\.?s", r"\beafe\b"]},
                {"value": "international", "patterns": [r"international", r"ex[- .]?u\.?s", r"\bforeign\b"]},
                {"value": "global", "patterns": [r"\bglobal\b", r"\bworld\b", r"all country", r"\bacwi\b"]},
                {"value": "us", "patterns": [r"\bu\.?s\.?\b", r"\bamerican\b", r"\bs&p\b", r"\brussell\b", r"\bnasdaq\b"]},
            ],
            "size": [
                {"value": "micro", "patterns": [r"micro[- ]cap"]},
                {"value": "small_mid", "patterns": [r"small[- ]mid", r"\bsmid\b"]},
                {"value": "small", "patterns": [r"small[- ]cap", r"russell 2000"]},
                {"value": "mid", "patterns": [r"mid[- ]cap", r"s&p 400"]},
                {"value": "large", "patterns": [r"large[- ]cap", r"s&p 500", r"russell 1000"]},
                {"value": "broad", "patterns": [r"total (?:stock )?market", r"broad market", r"russell 3000", r"all[- ]cap"]},
            ],
            "style": [
                {"value": "value", "patterns": [r"\bvalue\b"]},
                {"value": "growth", "patterns": [r"\bgrowth\b"]},
                {"value": "income", "patterns": [r"\bincome\b", r"\bdividend\b"]},
                {"value": "broad_market", "patterns": [r"total (?:stock )?market", r"broad market", r"\bcore equity\b"]},
            ],
            "factor": [
                {"value": "multi_factor", "patterns": [r"multi[- ]factor", r"multifactor"]},
                {"value": "momentum", "patterns": [r"\bmomentum\b"]},
                {"value": "quality", "patterns": [r"\bquality\b"]},
                {"value": "low_volatility", "patterns": [r"low volatility", r"minimum volatility", r"\bmin vol\b"]},
                {"value": "value", "patterns": [r"\bvalue\b"]},
            ],
        },
        "required_cells": [
            {"asset_class": "equity", "region": "us", "size": size, "style": style, "factor": "*"}
            for size in ("large", "mid", "small") for style in ("value", "growth")
        ] + [
            {"asset_class": "equity", "region": region, "size": "*", "style": "*", "factor": "*"}
            for region in ("international", "developed_ex_us", "emerging_markets", "global")
        ] + [
            {"asset_class": "equity", "region": "*", "size": "*", "style": "*", "factor": factor}
            for factor in ("momentum", "quality", "low_volatility", "multi_factor")
        ] + [
            {"asset_class": asset, "region": "*", "size": "*", "style": "*", "factor": "*"}
            for asset in ("fixed_income", "real_assets", "multi_asset")
        ],
        "priority_contract": {
            "components": {
                "required_cell_match": 0.5,
                "classified_coordinate_fraction": 0.3,
                "catalog_identity_coverage": 0.2,
            },
            "tie_break": ["comparison_evidence_tier_desc", "symbol_asc"],
            "excluded_inputs": ["one_year_return", "factor_implied_return", "residual_alpha", "valuation_return"],
            "meaning": "public-data acquisition order, not expected return or portfolio preference",
        },
        "authority": "research_acquisition_only",
        "capital_authority": False,
    }
    if not 1 <= max_results <= 500 or not 1 <= max_per_cell <= 10:
        raise ValueError("broad-fund limits are outside their typed bounds")
    return {**body, "policy_sha256": stable_sha256(body)}


def _verified(raw: Mapping[str, Any], schema: str, digest_field: str) -> dict[str, Any]:
    row = dict(raw)
    if row.get("schema") != schema:
        raise ValueError(f"artifact requires {schema}")
    claimed = require_text(row.get(digest_field), digest_field)
    if claimed != stable_sha256({key: value for key, value in row.items() if key != digest_field}):
        raise ValueError(f"{digest_field} does not match its payload")
    return row


def _validate_policy(raw: Mapping[str, Any]) -> dict[str, Any]:
    policy = _verified(raw, BROAD_FUND_POLICY_SCHEMA, "policy_sha256")
    if policy.get("capital_authority") is not False:
        raise ValueError("broad-fund policy must deny capital authority")
    dimensions = policy.get("dimensions")
    if not isinstance(dimensions, Mapping) or set(dimensions) != set(_DIMENSIONS):
        raise ValueError("broad-fund policy requires the five declared dimensions")
    for dimension in _DIMENSIONS:
        rules = dimensions[dimension]
        if not isinstance(rules, list) or not rules:
            raise ValueError(f"broad-fund dimension {dimension} requires rules")
        for rule in rules:
            require_text(rule.get("value"), f"{dimension} value")
            for pattern in rule.get("patterns") or ():
                re.compile(require_text(pattern, f"{dimension} pattern"))
    if not 1 <= int(policy.get("max_results") or 0) <= 500:
        raise ValueError("broad-fund max_results is outside its typed bounds")
    if not 1 <= int(policy.get("max_per_cell") or 0) <= 10:
        raise ValueError("broad-fund max_per_cell is outside its typed bounds")
    required = policy.get("required_cells")
    if not isinstance(required, list) or any(
        not isinstance(cell, Mapping) or set(cell) != set(_DIMENSIONS) for cell in required
    ):
        raise ValueError("broad-fund required cells must declare all five dimensions")
    components = (policy.get("priority_contract") or {}).get("components")
    expected = {
        "required_cell_match", "classified_coordinate_fraction", "catalog_identity_coverage",
    }
    if not isinstance(components, Mapping) or set(components) != expected:
        raise ValueError("broad-fund priority contract has unsupported components")
    if any(float(value) < 0 for value in components.values()) or sum(float(value) for value in components.values()) <= 0:
        raise ValueError("broad-fund priority weights must be nonnegative with positive total")
    return policy


def _classify(name: str, policy: Mapping[str, Any]) -> tuple[dict[str, str], dict[str, list[str]]]:
    text = " ".join(name.lower().split())
    values, witnesses = {}, {}
    unknown = str(policy["unknown_value"])
    for dimension in _DIMENSIONS:
        match = next((
            (str(rule["value"]), [pattern for pattern in rule.get("patterns") or () if re.search(pattern, text)])
            for rule in policy["dimensions"][dimension]
            if any(re.search(pattern, text) for pattern in rule.get("patterns") or ())
        ), None)
        values[dimension] = match[0] if match else unknown
        witnesses[dimension] = match[1] if match else []
    return values, witnesses


def _cell_id(values: Mapping[str, str]) -> str:
    return "|".join(f"{dimension}:{values[dimension]}" for dimension in _DIMENSIONS)


def _matches(cell: Mapping[str, str], required: Mapping[str, str]) -> bool:
    return all(str(required[dimension]) in {"*", str(cell[dimension])} for dimension in _DIMENSIONS)


def _evidence(watchlists: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    joined: dict[str, dict[str, Any]] = {}
    for raw in watchlists:
        watchlist = _verified(raw, WATCHLIST_RESULT_SCHEMA, "watchlist_sha256")
        for candidate in watchlist.get("candidates") or ():
            if not isinstance(candidate, Mapping):
                continue
            entity_id = require_text(candidate.get("entity_id"), "fund evidence entity_id").upper()
            analysis = candidate.get("analysis")
            analysis_valid = isinstance(analysis, Mapping) and analysis.get("schema") == "jaggedthoughts-factor-analysis-v1" and str(analysis.get("candidate_entity_id") or "").upper() == entity_id and str(analysis.get("analysis_sha256") or "") == stable_sha256({key: value for key, value in analysis.items() if key != "analysis_sha256"})
            screen_qualified = candidate.get("screen_status") == "qualified"
            valuation_ready = isinstance(candidate.get("valuation"), Mapping) and bool(candidate["valuation"])
            fund = candidate.get("fund_evidence") if isinstance(candidate.get("fund_evidence"), Mapping) else {}
            metrics = set(str(key) for key in (fund.get("metrics") or {}))
            issuer_bound = bool(fund.get("source_refs"))
            concentration = bool(metrics & {"portfolio_top10_concentration", "portfolio_holdings_hhi"})
            implementation = bool(metrics & {"fund_net_assets", "median_bid_ask_spread", "average_daily_volume_30d"})
            # Screening is a decision outcome, not missing public evidence. A
            # fully observed fund remains a usable peer after it fails a screen.
            ready = analysis_valid and valuation_ready and issuer_bound and concentration and implementation
            row = {
                "watchlist_sha256": watchlist["watchlist_sha256"],
                "watchlist_as_of": watchlist["as_of"],
                "watchlist_screen_qualified": screen_qualified,
                "factor_analysis_ready": analysis_valid,
                "aggregate_valuation_ready": valuation_ready,
                "issuer_evidence_ready": issuer_bound,
                "concentration_ready": concentration,
                "implementation_ready": implementation,
                "comparison_ready": ready,
                "evidence_tier": sum((screen_qualified, analysis_valid, valuation_ready, issuer_bound, concentration, implementation)),
            }
            prior = joined.get(entity_id)
            if prior is None or (row["evidence_tier"], row["watchlist_as_of"], row["watchlist_sha256"]) > (prior["evidence_tier"], prior["watchlist_as_of"], prior["watchlist_sha256"]):
                joined[entity_id] = row
    return joined


def compile_broad_fund_scout(
    catalog: Mapping[str, Any],
    policy: Mapping[str, Any],
    *,
    watchlist_results: Iterable[Mapping[str, Any]] = (),
    completed_at: str | None = None,
) -> dict[str, Any]:
    """Compile a deterministic breadth queue; never interpret performance as opportunity."""

    source = _verified(catalog, CATALOG_SCHEMA, "catalog_sha256")
    rules = _validate_policy(policy)
    completed = canonical_timestamp(completed_at or _now(), "completed_at")
    receipts = {
        str(row.get("source_id")): row for row in source.get("source_receipts") or ()
        if isinstance(row, Mapping) and row.get("content_sha256") and row.get("raw_path")
    }
    evidence = _evidence(watchlist_results)
    required = [dict(row) for row in rules.get("required_cells") or ()]
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    rejected: Counter[str] = Counter()
    seen: set[str] = set()
    for raw in source.get("securities") or ():
        if not isinstance(raw, Mapping) or raw.get("entity_kind") != "public_fund":
            continue
        security_id = require_text(raw.get("security_id"), "fund security_id")
        if security_id in seen:
            rejected["duplicate_security_identity"] += 1
            continue
        seen.add(security_id)
        if raw.get("security_kind") != "exchange_traded_fund":
            rejected["security_kind"] += 1
            continue
        source_id = str(raw.get("source_id") or "")
        if source_id not in receipts or str(raw.get("source_path") or "") != str(receipts[source_id]["raw_path"]):
            rejected["source_receipt_missing"] += 1
            continue
        name = require_text(raw.get("name"), "fund name")
        normalized = name.lower()
        if any(re.search(pattern, normalized) for pattern in rules["exclude_name_patterns"]):
            rejected["excluded_product_form"] += 1
            continue
        price = raw.get("last_price")
        if not isinstance(price, (int, float)) or isinstance(price, bool) or float(price) <= 0:
            rejected["positive_catalog_price_missing"] += 1
            continue
        cell, witnesses = _classify(name, rules)
        cell_id = _cell_id(cell)
        required_matches = [index for index, target in enumerate(required) if _matches(cell, target)]
        coordinate_count = sum(value != rules["unknown_value"] for value in cell.values())
        identity_coverage = sum(raw.get(key) not in {None, ""} for key in ("symbol", "name", "last_price", "source_id")) / 4
        components = rules["priority_contract"]["components"]
        priority = (
            float(components["required_cell_match"]) * bool(required_matches)
            + float(components["classified_coordinate_fraction"]) * coordinate_count / len(_DIMENSIONS)
            + float(components["catalog_identity_coverage"]) * identity_coverage
        ) / sum(float(value) for value in components.values())
        entity_id = str(raw.get("symbol") or "").upper()
        evidence_row = evidence.get(entity_id, {
            "watchlist_screen_qualified": False,
            "factor_analysis_ready": False, "aggregate_valuation_ready": False,
            "issuer_evidence_ready": False, "concentration_ready": False,
            "implementation_ready": False, "comparison_ready": False, "evidence_tier": 0,
        })
        groups[cell_id].append({
            "security_id": security_id,
            "entity_id": entity_id,
            "name": name,
            "catalog_available_at": raw.get("available_at"),
            "catalog_source": {
                "source_id": source_id, "source_path": raw.get("source_path"),
                "content_sha256": receipts[source_id]["content_sha256"],
            },
            "cell_id": cell_id,
            "cell": cell,
            "classification_witnesses": witnesses,
            "required_cell_matches": required_matches,
            "acquisition_priority": round(priority, 8),
            "priority_kind": "evidence_acquisition_not_expected_return",
            "expected_return_used": False,
            "evidence": evidence_row,
            "next_stage": "compare_public_evidence" if evidence_row["comparison_ready"] else "acquire_factor_valuation_and_fund_evidence",
            "capital_authority": False,
        })

    for rows in groups.values():
        rows.sort(key=lambda row: (
            -float(row["acquisition_priority"]), -int(row["evidence"]["evidence_tier"]), row["entity_id"],
        ))
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    selected_cell_counts: Counter[str] = Counter()

    def add(row: Mapping[str, Any], reason: str) -> None:
        item = {
            **dict(row), "selection_rank": len(selected) + 1,
            "selection_reason": reason,
        }
        selected.append(item)
        selected_ids.add(str(row["security_id"]))
        selected_cell_counts[str(row["cell_id"])] += 1

    # Pay the declared coverage obligations before filling the remaining breadth budget.
    for required_index, target in enumerate(required):
        if len(selected) >= int(rules["max_results"]):
            break
        if any(_matches(row["cell"], target) for row in selected):
            continue
        eligible = [
            row for rows in groups.values() for row in rows
            if _matches(row["cell"], target)
            and row["security_id"] not in selected_ids
            and selected_cell_counts[row["cell_id"]] < int(rules["max_per_cell"])
        ]
        eligible.sort(key=lambda row: (
            -float(row["acquisition_priority"]), -int(row["evidence"]["evidence_tier"]),
            row["cell_id"], row["entity_id"],
        ))
        if eligible:
            add(eligible[0], f"required_cell_coverage:{required_index}")

    while len(selected) < int(rules["max_results"]):
        eligible = [
            rows[selected_cell_counts[cell_id]]
            for cell_id, rows in groups.items()
            if selected_cell_counts[cell_id] < min(len(rows), int(rules["max_per_cell"]))
        ]
        eligible.sort(key=lambda row: (
            -float(row["acquisition_priority"]), -int(row["evidence"]["evidence_tier"]),
            row["cell_id"], row["entity_id"],
        ))
        if not eligible:
            break
        for row in eligible:
            if len(selected) >= int(rules["max_results"]):
                break
            add(row, "breadth_round_then_declared_tie_break")

    cell_counts = Counter(row["cell_id"] for row in selected)
    observed_required = {
        index for rows in groups.values() for row in rows for index in row["required_cell_matches"]
    }
    unknown_cells = sorted(
        cell_id for cell_id, rows in groups.items()
        if any(value == rules["unknown_value"] for value in rows[0]["cell"].values())
    )
    selected_required = {
        index for row in selected for index, target in enumerate(required)
        if _matches(row["cell"], target)
    }
    all_eligible = [row for rows in groups.values() for row in rows]
    ready = [row for row in selected if row["evidence"]["comparison_ready"]]
    all_ready = [row for row in all_eligible if row["evidence"]["comparison_ready"]]
    selected_peers = Counter((row["cell"]["asset_class"], row["cell"]["region"]) for row in ready)
    eligible_peers = Counter((row["cell"]["asset_class"], row["cell"]["region"]) for row in all_ready)
    eligible_coverage = {
        dimension: dict(sorted(Counter(row["cell"][dimension] for row in all_eligible).items()))
        for dimension in _DIMENSIONS
    }
    selected_coverage = {
        dimension: dict(sorted(Counter(row["cell"][dimension] for row in selected).items()))
        for dimension in _DIMENSIONS
    }
    body = {
        "schema": BROAD_FUND_SCOUT_SCHEMA,
        "completed_at": completed,
        "catalog_sha256": source["catalog_sha256"],
        "policy_sha256": rules["policy_sha256"],
        "eligible_fund_count": sum(len(rows) for rows in groups.values()),
        "observed_cell_count": len(groups),
        "unknown_cell_count": len(unknown_cells),
        "unknown_cell_ids": unknown_cells,
        "required_cell_count": len(required),
        "covered_required_cell_count": len(observed_required),
        "selected_required_cell_count": len(selected_required),
        "coverage_holes": [
            {"required_cell_index": index, "cell": cell}
            for index, cell in enumerate(required) if index not in observed_required
        ],
        "selected_coverage_holes": [
            {"required_cell_index": index, "cell": cell}
            for index, cell in enumerate(required) if index not in selected_required
        ],
        "eligible_coverage": eligible_coverage,
        "selected_coverage": selected_coverage,
        "selected_count": len(selected),
        "selected_cell_count": len(cell_counts),
        "max_selected_in_any_cell": max(cell_counts.values(), default=0),
        "selected": selected,
        "comparison_readiness": {
            "ready_selected_count": len(ready),
            "ready_eligible_count": len(all_ready),
            "selected_ready_peer_group_count": sum(count >= 2 for count in selected_peers.values()),
            "eligible_ready_peer_group_count": sum(count >= 2 for count in eligible_peers.values()),
            "investable_comparison_supported": any(count >= 2 for count in eligible_peers.values()),
            "criterion": "at least two eligible funds in one asset-class/region peer group with factor, aggregate valuation, issuer, concentration, and implementation evidence",
        },
        "rejected_by_reason": dict(sorted(rejected.items())),
        "priority_contract": rules["priority_contract"],
        "security_ranking_use": False,
        "portfolio_weight": 0.0,
        "capital_authority": False,
    }
    return {**body, "scout_sha256": stable_sha256(body)}


__all__ = [
    "BROAD_FUND_POLICY_SCHEMA", "BROAD_FUND_SCOUT_SCHEMA",
    "broad_fund_scout_policy", "compile_broad_fund_scout",
]
