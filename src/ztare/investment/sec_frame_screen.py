"""Bulk SEC XBRL-frame accounting screen for the public-equity catalog."""

from __future__ import annotations

import argparse
from bisect import bisect_left, bisect_right
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
from typing import Any, Callable, Iterable, Mapping

from ztare.common.equivariance import stable_sha256

from .broad_equity_acquisition import (
    compile_broad_equity_acquisition,
    default_broad_equity_policy,
)
from .contracts import MetricObservation, canonical_timestamp
from .sources import (
    DEFAULT_SEC_USER_AGENT,
    SourceReceipt,
    _atomic_json,
    _atomic_write,
    _cache_raw,
    _fetch_sec,
)
from .universe_catalog import CATALOG_SCHEMA


SCREEN_SCHEMA = "jaggedthoughts-sec-frame-screen-v1"
PRIORITY_CANDIDATES_SCHEMA = "jaggedthoughts-sec-frame-priority-candidates-v1"
REGISTRY_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
MIN_RESEARCH_MARKET_CAP = 300_000_000.0
MIN_RESEARCH_DAILY_VOLUME = 100_000.0
Fetch = Callable[[str], bytes]

_SCREEN_DOCTRINE_WEIGHTS = {
    "balanced_quality_value_proxy": {
        "cheapness": 0.25, "earnings_power": 0.25,
        "quality": 0.25, "balance_sheet_risk": 0.25,
    },
    "quality_resilience_proxy": {
        "cheapness": 0.0, "earnings_power": 1 / 3,
        "quality": 1 / 3, "balance_sheet_risk": 1 / 3,
    },
    "value_proxy": {
        "cheapness": 1.0, "earnings_power": 0.0,
        "quality": 0.0, "balance_sheet_risk": 0.0,
    },
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _frame_specs(frame: str) -> tuple[tuple[str, str, str], ...]:
    if not re.fullmatch(r"CY\d{4}", frame):
        raise ValueError("SEC annual frame must have form CY####")
    return (
        ("revenue", "RevenueFromContractWithCustomerExcludingAssessedTax", frame),
        ("revenue", "Revenues", frame),
        ("net_income", "NetIncomeLoss", frame),
        ("operating_cash_flow", "NetCashProvidedByUsedInOperatingActivities", frame),
        ("capital_expenditure", "PaymentsToAcquirePropertyPlantAndEquipment", frame),
        ("assets", "Assets", f"{frame}Q4I"),
        ("liabilities", "Liabilities", f"{frame}Q4I"),
        ("cash", "CashAndCashEquivalentsAtCarryingValue", f"{frame}Q4I"),
    )


def _frame_url(tag: str, frame: str) -> str:
    return f"https://data.sec.gov/api/xbrl/frames/us-gaap/{tag}/USD/{frame}.json"


def _ticker_key(value: Any) -> str:
    return str(value or "").strip().upper().replace(".", "-")


def _registry(payload: Mapping[str, Any]) -> dict[str, int]:
    fields = payload.get("fields")
    rows = payload.get("data")
    if not isinstance(fields, list) or not isinstance(rows, list):
        raise ValueError("SEC ticker registry has no fields/data arrays")
    indexes = {str(field): index for index, field in enumerate(fields)}
    if not {"cik", "ticker"}.issubset(indexes):
        raise ValueError("SEC ticker registry omits cik or ticker")
    candidates: dict[str, set[int]] = {}
    for row in rows:
        if not isinstance(row, list) or len(row) <= max(indexes.values()):
            continue
        key = _ticker_key(row[indexes["ticker"]])
        try:
            cik = int(row[indexes["cik"]])
        except (TypeError, ValueError):
            continue
        if key and cik > 0:
            candidates.setdefault(key, set()).add(cik)
    return {ticker: next(iter(ciks)) for ticker, ciks in candidates.items() if len(ciks) == 1}


def _fact_rows(
    payload: Mapping[str, Any], *, metric_id: str, tag: str, frame: str, source_ref: str,
) -> dict[int, dict[str, Any]]:
    if (
        payload.get("taxonomy") != "us-gaap"
        or payload.get("tag") != tag
        or payload.get("ccp") != frame
        or payload.get("uom") != "USD"
    ):
        raise ValueError(f"SEC frame identity mismatch for {tag}/{frame}")
    rows = payload.get("data")
    if not isinstance(rows, list):
        raise ValueError(f"SEC frame {tag}/{frame} has no data array")
    result: dict[int, dict[str, Any]] = {}
    for raw in sorted(
        (row for row in rows if isinstance(row, Mapping)),
        key=lambda row: (str(row.get("end") or ""), str(row.get("accn") or "")),
        reverse=True,
    ):
        try:
            cik, value = int(raw["cik"]), float(raw["val"])
        except (KeyError, TypeError, ValueError):
            continue
        end, accession = str(raw.get("end") or ""), str(raw.get("accn") or "")
        if cik <= 0 or not math.isfinite(value) or not end or not accession:
            continue
        result.setdefault(cik, {
            "metric_id": metric_id, "concept": tag, "value": value,
            "observed_at": f"{end}T23:59:59Z", "accession": accession,
            "source_ref": source_ref,
        })
    return result


def _percentile(value: float, sample: list[float]) -> float:
    if len(sample) == 1:
        return 0.5
    ordered = sorted(sample)
    midpoint = (bisect_left(ordered, value) + bisect_right(ordered, value) - 1) / 2
    return midpoint / (len(ordered) - 1)


def compile_sec_frame_priority_candidates(
    screen: Mapping[str, Any], catalog: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Adapt source-feasible potential rows to broad-acquisition priorities."""
    if screen.get("schema") != SCREEN_SCHEMA:
        raise ValueError(f"SEC frame screen schema must be {SCREEN_SCHEMA}")
    screen_sha256 = str(screen.get("screen_sha256") or "")
    if len(screen_sha256) != 64:
        raise ValueError("SEC frame screen requires screen_sha256")
    source_rows = list(screen.get("research_queue") or ())
    scope = "top_decile_research_queue"
    if catalog is not None and screen.get("ranked_candidates"):
        volume = {
            str(row.get("security_id") or ""): float(row.get("volume") or 0.0)
            for row in catalog.get("securities") or () if isinstance(row, Mapping)
        }
        source_rows = [
            row for row in screen.get("ranked_candidates") or ()
            if isinstance(row, Mapping)
            and float(row.get("market_cap") or 0.0) >= MIN_RESEARCH_MARKET_CAP
            and volume.get(str(row.get("security_id") or ""), 0.0)
            >= MIN_RESEARCH_DAILY_VOLUME
        ]
        scope = "full_investable_ranked_frontier"
    candidates = [{
        "security_id": row["security_id"], "symbol": row["symbol"],
        "base_priority": row["research_priority_score"],
        "research_priority_score": row["research_priority_score"],
        "component_scores": dict(row["component_scores"]),
        "doctrine_scores": dict(row.get("doctrine_scores") or {}),
        "doctrine_ranks": dict(row.get("doctrine_ranks") or {}),
        "best_doctrine_rank": row.get("best_doctrine_rank"),
        "leading_doctrines": list(row.get("leading_doctrines") or ()),
        "unresolved_residuals": list(row.get("unresolved_residuals") or (
            "multi_period_earnings_durability", "debt_maturity_and_dilution_risk",
            "market_implied_growth_cross_check", "strategy_and_industry_evidence",
        )),
        "potential_screen_sha256": screen_sha256,
    } for row in source_rows]
    body = {
        "schema": PRIORITY_CANDIDATES_SCHEMA, "screen_sha256": screen_sha256,
        "catalog_sha256": screen.get("catalog_sha256"),
        "authority": "research_queue_priority_only", "capital_authority": False,
        "candidate_scope": scope,
        "candidate_count": len(candidates), "candidates": candidates,
    }
    return {**body, "priority_candidates_sha256": stable_sha256(body)}


def compile_sec_frame_acquisition_run(
    catalog: Mapping[str, Any], screen: Mapping[str, Any], *,
    policy: Mapping[str, Any] | None = None,
    enrolled_security_ids: Iterable[Any] = (),
    current_security_ids: Iterable[Any] = (),
    completed_at: str | None = None,
) -> dict[str, Any]:
    """Apply existing diversity closure only inside the high-potential queue."""
    priorities = compile_sec_frame_priority_candidates(screen, catalog)
    admitted = {str(row["security_id"]) for row in priorities["candidates"]}
    scoped_catalog = {
        **dict(catalog),
        "securities": [
            dict(row) for row in catalog.get("securities") or ()
            if isinstance(row, Mapping) and str(row.get("security_id") or "") in admitted
        ],
    }
    result = compile_broad_equity_acquisition(
        catalog=scoped_catalog, policy=policy or default_broad_equity_policy(),
        priority_candidates=priorities["candidates"],
        enrolled_security_ids=enrolled_security_ids,
        current_security_ids=current_security_ids,
        completed_at=completed_at or str(screen["retrieved_at"]),
    )
    body = {
        **result,
        "intent": {
            **dict(result["intent"]),
            "query": "SEC-frame multi-doctrine potential residuals",
            "ranking_objectives": [
                "cheapness", "earnings_power", "quality", "balance_sheet_risk",
            ],
        },
        "selection_contract": {
            **dict(result["selection_contract"]),
            "first_stage": "full_complete_investable_SEC_frame_doctrine_interleave",
            "second_stage": "country_sector_and_size_diversity_closure",
            "coverage_or_liquidity_only_candidates_admitted": False,
        },
        "potential_screen_sha256": screen["screen_sha256"],
        "potential_candidate_count": priorities["candidate_count"],
        "potential_candidate_scope": priorities["candidate_scope"],
        "potential_scope_only": True,
    }
    body.pop("run_sha256", None)
    return {**body, "run_sha256": stable_sha256(body)}


def hydrate_sec_annual_frame_screen(
    workspace: str | Path,
    *,
    frame: str | None = None,
    retrieved_at: str | None = None,
    fetch: Fetch | None = None,
) -> dict[str, Any]:
    """Fetch bounded bulk SEC frames and rank fully comparable catalog equities."""
    root = Path(workspace).expanduser().resolve()
    retrieval = canonical_timestamp(retrieved_at or _utc_now(), "SEC frame retrieved_at")
    annual_frame = frame or f"CY{int(retrieval[:4]) - 1}"
    specs = _frame_specs(annual_frame)
    catalog_path = root / "universe" / "catalog-latest.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if catalog.get("schema") != CATALOG_SCHEMA:
        raise ValueError(f"catalog schema must be {CATALOG_SCHEMA}")
    fetcher = fetch or (
        lambda url: _fetch_sec(url, user_agent=DEFAULT_SEC_USER_AGENT, timeout=60)[0]
    )
    urls = [REGISTRY_URL, *(_frame_url(tag, ccp) for _, tag, ccp in specs)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        contents = dict(zip(urls, pool.map(fetcher, urls), strict=True))

    receipts: list[dict[str, Any]] = []
    registry_path, registry_digest = _cache_raw(
        root, "sec_ticker_registry", "sec-ticker-registry", contents[REGISTRY_URL], ".json",
    )
    registry_payload = json.loads(contents[REGISTRY_URL])
    tickers = _registry(registry_payload)
    receipts.append(SourceReceipt(
        source_id="sec_ticker_registry", adapter="sec_ticker_registry",
        canonical_url=REGISTRY_URL, retrieved_at=retrieval,
        content_sha256=registry_digest, raw_path=registry_path,
        media_type="application/json", availability_mode="retrieval_only",
        observation_count=len(tickers),
        provider_note="SEC ticker/CIK association snapshot; admissible from retrieval time.",
    ).to_dict())

    facts: dict[int, dict[str, dict[str, Any]]] = {}
    frame_coverage: list[dict[str, Any]] = []
    for metric_id, tag, ccp in specs:
        url = _frame_url(tag, ccp)
        source_ref = f"sec_frame_{ccp}_{metric_id}_{stable_sha256(tag)[:8]}"
        relative, digest = _cache_raw(root, source_ref, "sec-xbrl-frame", contents[url], ".json")
        payload = json.loads(contents[url])
        parsed = _fact_rows(
            payload, metric_id=metric_id, tag=tag, frame=ccp, source_ref=source_ref,
        )
        added = 0
        for cik, row in parsed.items():
            if metric_id not in facts.setdefault(cik, {}):
                facts[cik][metric_id] = row
                added += 1
        receipt = SourceReceipt(
            source_id=source_ref, adapter="sec_xbrl_frame", canonical_url=url,
            retrieved_at=retrieval, content_sha256=digest, raw_path=relative,
            media_type="application/json", availability_mode="retrieval_only",
            observation_count=len(parsed),
            provider_note=(
                "SEC cross-company XBRL frame; economic period retained, historical "
                "admissibility begins at this retrieval because the frame omits filing dates."
            ),
        ).to_dict()
        receipts.append(receipt)
        frame_coverage.append({
            "metric_id": metric_id, "concept": tag, "frame": ccp,
            "filer_count": len(parsed), "new_metric_filer_count": added,
            "source_ref": source_ref, "receipt_sha256": receipt["receipt_sha256"],
        })

    catalog_rows = [
        dict(row) for row in catalog.get("securities") or ()
        if isinstance(row, Mapping)
        and row.get("entity_kind") == "public_equity"
        and row.get("security_kind") == "common_equity"
    ]
    mapped = []
    for security in catalog_rows:
        cik = tickers.get(_ticker_key(security.get("symbol")))
        if cik is not None:
            mapped.append((security, cik))
    cik_counts = Counter(cik for _, cik in mapped)
    duplicate_share_class_ciks = {cik for cik, count in cik_counts.items() if count > 1}
    joined, observations = [], []
    for security, cik in mapped:
        if cik in duplicate_share_class_ciks:
            continue
        metric_facts = facts.get(cik, {})
        metric_values = {key: float(row["value"]) for key, row in metric_facts.items()}
        for metric_id, row in sorted(metric_facts.items()):
            observation = MetricObservation(
                observation_id=(
                    f"{row['source_ref']}:{security['symbol']}:"
                    f"{stable_sha256({'cik': cik, 'metric': metric_id, 'accn': row['accession'], 'value': row['value']})[:20]}"
                ),
                entity_id=str(security["symbol"]), metric_id=metric_id,
                value=row["value"], unit="USD", observed_at=row["observed_at"],
                available_at=retrieval, source_ref=row["source_ref"],
            )
            observations.append(observation.to_dict())
        joined.append({
            "security": security, "cik": cik, "metrics": metric_values,
            "metric_lineage": {key: dict(value) for key, value in sorted(metric_facts.items())},
        })

    comparable: list[dict[str, Any]] = []
    financial_model_exclusions = temporal_alignment_exclusions = 0
    for row in joined:
        security, metrics = row["security"], row["metrics"]
        if str(security.get("sector") or "").strip().lower() == "finance":
            financial_model_exclusions += 1
            continue
        market_cap = security.get("market_cap")
        required = {
            "revenue", "net_income", "operating_cash_flow", "capital_expenditure",
            "assets", "liabilities", "cash",
        }
        if not required.issubset(metrics) or market_cap is None:
            continue
        market_cap = float(market_cap)
        if (
            market_cap <= 0 or metrics["revenue"] <= 0 or metrics["assets"] <= 0
            or metrics["capital_expenditure"] < 0 or metrics["liabilities"] < 0
            or metrics["cash"] < 0
        ):
            continue
        period_ends = [
            datetime.fromisoformat(value["observed_at"][:10])
            for value in row["metric_lineage"].values()
        ]
        if (max(period_ends) - min(period_ends)).days > 45:
            temporal_alignment_exclusions += 1
            continue
        coordinates = {
            "earnings_yield": metrics["net_income"] / market_cap,
            "free_cash_flow_yield_proxy": (
                metrics["operating_cash_flow"] - metrics["capital_expenditure"]
            ) / market_cap,
            "return_on_assets": metrics["net_income"] / metrics["assets"],
            "operating_cash_margin": metrics["operating_cash_flow"] / metrics["revenue"],
            "cash_backing_of_earnings": (
                metrics["operating_cash_flow"] - metrics["net_income"]
            ) / metrics["assets"],
            "equity_to_assets": (
                metrics["assets"] - metrics["liabilities"]
            ) / metrics["assets"],
            "cash_to_assets": metrics["cash"] / metrics["assets"],
        }
        if all(math.isfinite(value) for value in coordinates.values()):
            comparable.append({**row, "coordinates": coordinates})

    coordinate_ids = (
        "earnings_yield", "free_cash_flow_yield_proxy",
        "return_on_assets", "operating_cash_margin", "cash_backing_of_earnings",
        "equity_to_assets", "cash_to_assets",
    )
    global_samples = {
        key: [row["coordinates"][key] for row in comparable] for key in coordinate_ids
    }
    sector_samples: dict[tuple[str, str], list[float]] = {}
    for row in comparable:
        sector = str(row["security"].get("sector") or "unknown")
        for key in coordinate_ids:
            sector_samples.setdefault((sector, key), []).append(row["coordinates"][key])
    ranked: list[dict[str, Any]] = []
    for row in comparable:
        security, sector = row["security"], str(row["security"].get("sector") or "unknown")
        percentiles = {}
        for key in coordinate_ids:
            sample = sector_samples.get((sector, key), [])
            if len(sample) < 10:
                sample = global_samples[key]
            percentiles[key] = _percentile(row["coordinates"][key], sample)
        component_scores = {
            "cheapness": (percentiles["earnings_yield"] + percentiles["free_cash_flow_yield_proxy"]) / 2,
            "earnings_power": (percentiles["return_on_assets"] + percentiles["operating_cash_margin"]) / 2,
            "quality": percentiles["cash_backing_of_earnings"],
            "balance_sheet_risk": (percentiles["equity_to_assets"] + percentiles["cash_to_assets"]) / 2,
        }
        doctrine_scores = {
            doctrine_id: sum(
                weights[name] * component_scores[name] for name in component_scores
            )
            for doctrine_id, weights in _SCREEN_DOCTRINE_WEIGHTS.items()
        }
        ranked.append({
            "security_id": security["security_id"], "symbol": security["symbol"],
            "name": security["name"], "cik": row["cik"], "sector": sector,
            "industry": security.get("industry"), "market_cap": security["market_cap"],
            "coordinates": row["coordinates"], "within_sector_percentiles": percentiles,
            "component_scores": component_scores,
            "research_priority_score": doctrine_scores["balanced_quality_value_proxy"],
            "doctrine_scores": doctrine_scores,
            "coverage": {"observed_metric_count": 7, "required_metric_count": 7, "ratio": 1.0},
            "metric_lineage": row["metric_lineage"],
        })
    for doctrine_id in _SCREEN_DOCTRINE_WEIGHTS:
        doctrine_ranked = sorted(
            ranked,
            key=lambda row: (-row["doctrine_scores"][doctrine_id], row["security_id"]),
        )
        for doctrine_rank, row in enumerate(doctrine_ranked, 1):
            row.setdefault("doctrine_ranks", {})[doctrine_id] = doctrine_rank
    ranked.sort(key=lambda row: (
        min(row["doctrine_ranks"].values()),
        row["doctrine_ranks"]["balanced_quality_value_proxy"],
        row["security_id"],
    ))
    for rank, row in enumerate(ranked, 1):
        row["rank"] = rank
        best_rank = min(row["doctrine_ranks"].values())
        row["best_doctrine_rank"] = best_rank
        row["leading_doctrines"] = sorted(
            doctrine_id for doctrine_id, value in row["doctrine_ranks"].items()
            if value == best_rank
        )
        row["research_priority_score"] = 1.0 - (rank - 1) / max(1, len(ranked))

    metric_join_coverage = {
        metric_id: sum(metric_id in row["metrics"] for row in joined)
        for metric_id in (
            "revenue", "net_income", "operating_cash_flow", "capital_expenditure",
            "assets", "liabilities", "cash",
        )
    }
    volume_by_security = {
        str(security["security_id"]): float(security.get("volume") or 0.0)
        for security in catalog_rows
    }
    investable_ranked = [
        row for row in ranked
        if float(row["market_cap"]) >= MIN_RESEARCH_MARKET_CAP
        and volume_by_security.get(str(row["security_id"]), 0.0)
        >= MIN_RESEARCH_DAILY_VOLUME
    ]
    queue_size = min(100, max(1, math.ceil(len(investable_ranked) * 0.1))) if investable_ranked else 0
    research_queue = [{
        "rank": row["rank"], "security_id": row["security_id"], "symbol": row["symbol"],
        "cik": row["cik"], "research_priority_score": row["research_priority_score"],
        "component_scores": row["component_scores"],
        "doctrine_scores": row["doctrine_scores"],
        "doctrine_ranks": row["doctrine_ranks"],
        "best_doctrine_rank": row["best_doctrine_rank"],
        "leading_doctrines": row["leading_doctrines"],
        "selection_reason": "top_decile_doctrine_interleave_complete_frame",
        "unresolved_residuals": [
            "multi_period_earnings_durability", "debt_maturity_and_dilution_risk",
            "market_implied_growth_cross_check", "strategy_and_industry_evidence",
        ],
    } for row in investable_ranked[:queue_size]]
    body = {
        "schema": SCREEN_SCHEMA, "frame": annual_frame, "retrieved_at": retrieval,
        "available_at": retrieval, "authority": "research_queue_only",
        "capital_authority": False, "catalog_sha256": catalog.get("catalog_sha256"),
        "catalog_retrieved_at": catalog.get("retrieved_at"),
        "source_receipts": receipts, "frame_coverage": frame_coverage,
        "coverage": {
            "catalog_common_equity_count": len(catalog_rows),
            "ticker_cik_join_count": len(mapped),
            "ticker_cik_join_ratio": len(mapped) / len(catalog_rows) if catalog_rows else 0.0,
            "ticker_registry_gap_count": len(catalog_rows) - len(mapped),
            "unique_cik_accounting_candidate_count": len(joined),
            "joined_security_count_by_metric": metric_join_coverage,
            "fully_comparable_ranked_count": len(ranked),
            "investable_ranked_count": len(investable_ranked),
            "research_queue_count": len(research_queue),
        },
        "typed_exclusions": {
            "duplicate_share_class_security_count": sum(
                cik_counts[cik] for cik in duplicate_share_class_ciks
            ),
            "duplicate_share_class_cik_count": len(duplicate_share_class_ciks),
            "financial_business_model_count": financial_model_exclusions,
            "fiscal_period_alignment_count": temporal_alignment_exclusions,
            "research_queue_below_market_cap_floor_count": sum(
                float(row["market_cap"]) < MIN_RESEARCH_MARKET_CAP for row in ranked
            ),
            "research_queue_below_volume_floor_count": sum(
                volume_by_security.get(str(row["security_id"]), 0.0)
                < MIN_RESEARCH_DAILY_VOLUME for row in ranked
            ),
        },
        "ranking_contract": {
            "name": "ordinal_interleave_of_fixed_investment_doctrines",
            "coordinates": list(coordinate_ids), "minimum_sector_sample": 10,
            "fallback": "global_coordinate_percentile",
            "components": {
                "cheapness": ["earnings_yield", "free_cash_flow_yield_proxy"],
                "earnings_power": ["return_on_assets", "operating_cash_margin"],
                "quality": ["cash_backing_of_earnings"],
                "balance_sheet_risk": ["equity_to_assets", "cash_to_assets"],
            },
            "doctrines": _SCREEN_DOCTRINE_WEIGHTS,
            "interleave": "best_doctrine_rank_then_balanced_rank_then_security_id",
            "component_weighting": "fixed_within_doctrine_after_within_sector_percentiles",
            "free_cash_flow_definition": "operating_cash_flow_minus_capital_expenditure",
            "is_expected_return": False,
            "purpose": "prioritize primary-source underwriting and web research",
        },
        "ranked_candidates": ranked, "research_queue": research_queue,
        "research_queue_contract": {
            "selection": "top_decile_by_doctrine_interleave_rank", "maximum_count": 100,
            "requires_complete_metric_count": 7,
            "minimum_market_cap": MIN_RESEARCH_MARKET_CAP,
            "minimum_current_daily_volume": MIN_RESEARCH_DAILY_VOLUME,
            "excluded_business_models": ["catalog_sector:Finance"],
            "excluded_identity_shapes": ["multiple_catalog_share_classes_per_cik"],
            "maximum_metric_period_end_spread_days": 45,
            "coverage_or_liquidity_only_candidates_admitted": False,
        },
        "uncertainty": {
            "temporal_depth": "single_annual_frame",
            "availability_mode": "retrieval_only",
            "accounting_comparability": "standard_taxonomy_whole_entity_facts_within_coarse_catalog_sector",
            "not_measured": [
                "multi_year_durability", "segment_mix", "debt_maturities", "dilution",
                "strategy", "market_implied_growth", "future_return",
                "bank_and_insurer_cross-sectional_accounting",
            ],
        },
        "historical_use_boundary": (
            "Every SEC frame fact and ticker association is retrieval-only because these bulk "
            "responses omit filing dates. Use this screen from available_at forward; do not backdate it."
        ),
        "next_activation": "research highest-ranked source-complete candidates through the typed dossier screen",
    }
    result = {**body, "screen_sha256": stable_sha256(body)}
    priority_candidates = compile_sec_frame_priority_candidates(result, catalog)
    acquisition_run = compile_sec_frame_acquisition_run(catalog, result)
    output_dir = root / "data" / "sec_frames"
    result_path = output_dir / f"annual-{annual_frame}-{result['screen_sha256'][:20]}.json"
    observations_path = output_dir / f"annual-{annual_frame}-observations.jsonl"
    _atomic_json(result_path, result)
    _atomic_json(output_dir / "latest.json", result)
    _atomic_json(output_dir / "priority-candidates.json", priority_candidates)
    _atomic_json(output_dir / "research-acquisition.json", acquisition_run)
    _atomic_write(
        observations_path,
        ("".join(json.dumps(row, sort_keys=True) + "\n" for row in sorted(
            observations, key=lambda row: (row["entity_id"], row["metric_id"], row["observation_id"]),
        ))).encode("utf-8"),
    )
    return {
        **result,
        "paths": {
            "screen": result_path.relative_to(root).as_posix(),
            "latest": "data/sec_frames/latest.json",
            "observations": observations_path.relative_to(root).as_posix(),
            "priority_candidates": "data/sec_frames/priority-candidates.json",
            "research_acquisition": "data/sec_frames/research-acquisition.json",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace")
    parser.add_argument("--frame")
    parser.add_argument("--retrieved-at")
    args = parser.parse_args(argv)
    result = hydrate_sec_annual_frame_screen(
        args.workspace, frame=args.frame, retrieved_at=args.retrieved_at,
    )
    print(json.dumps({
        "frame": result["frame"], "coverage": result["coverage"],
        "typed_exclusions": result["typed_exclusions"],
        "top_research_candidates": [{
            key: row[key] for key in (
                "rank", "symbol", "research_priority_score", "component_scores",
                "unresolved_residuals",
            )
        } for row in result["research_queue"][:10]],
        "paths": result["paths"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
