"""Configurable public-equity universe enrollment from the SEC registry.

Enrollment creates source configuration, not an investment candidate.  A
later source run creates observations, the quality screen creates a screened
object, and underwriting creates a draft object.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

import yaml
import requests

from ztare.common.equivariance import stable_sha256

from .contracts import require_refs, require_text
from .public_capital_market_basis import PUBLIC_SLEEVE_IDS
from .sources import DEFAULT_SEC_USER_AGENT, MAX_SOURCE_BYTES, PUBLIC_SOURCE_MANIFEST_SCHEMA


SEC_TICKER_REGISTRY_URL = "https://www.sec.gov/files/company_tickers.json"


def _atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def _atomic_yaml(path: Path, payload: Mapping[str, Any]) -> None:
    _atomic_bytes(path, yaml.safe_dump(payload, sort_keys=False, allow_unicode=True).encode("utf-8"))


def _symbol(value: str) -> str:
    symbol = require_text(value, "public equity ticker").upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9.-]{0,14}", symbol):
        raise ValueError("public equity ticker contains unsupported characters")
    return symbol


def _fetch_sec_registry(
    *, user_agent: str, workspace: str | Path, timeout_seconds: float = 30.0,
) -> tuple[Mapping[str, Any], dict[str, str]]:
    """Fetch and cache the registry once for a bounded enrollment batch."""
    try:
        response = requests.get(
            SEC_TICKER_REGISTRY_URL,
            headers={
                "User-Agent": require_text(user_agent, "SEC user agent"),
                "Accept": "application/json",
            },
            timeout=(10, timeout_seconds),
        )
        response.raise_for_status()
        content = response.content
    except requests.RequestException as error:
        raise ValueError(f"SEC ticker registry request failed: {error}") from error
    if len(content) > MAX_SOURCE_BYTES:
        raise ValueError("SEC ticker registry response exceeds the source-size limit")
    digest = hashlib.sha256(content).hexdigest()
    root = Path(workspace).expanduser().resolve()
    relative = Path("sources") / "registry" / f"sec-company-tickers-{digest[:20]}.json"
    destination = root / relative
    if not destination.exists():
        _atomic_bytes(destination, content)
    payload = json.loads(content.decode("utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("SEC ticker registry must be a JSON object")
    receipt = {
        "registry_url": SEC_TICKER_REGISTRY_URL,
        "registry_path": relative.as_posix(),
        "registry_sha256": digest,
    }
    return payload, receipt


def resolve_sec_companies(
    tickers: Iterable[str], *, user_agent: str, workspace: str | Path,
    timeout_seconds: float = 30.0,
) -> list[dict[str, Any]]:
    """Resolve several symbols against one exact SEC registry snapshot."""
    symbols = tuple(dict.fromkeys(_symbol(value) for value in tickers))
    if not symbols:
        return []
    payload, receipt = _fetch_sec_registry(
        user_agent=user_agent, workspace=workspace, timeout_seconds=timeout_seconds,
    )
    by_symbol: dict[str, list[Mapping[str, Any]]] = {}
    for row in payload.values():
        if not isinstance(row, Mapping):
            continue
        by_symbol.setdefault(str(row.get("ticker") or "").upper(), []).append(row)
    results: list[dict[str, Any]] = []
    for symbol in symbols:
        matches = by_symbol.get(symbol, [])
        if len(matches) != 1:
            raise ValueError(f"SEC ticker registry resolved {len(matches)} matches for {symbol}")
        row = matches[0]
        results.append({
            "schema": "jaggedthoughts-sec-company-resolution-v1",
            "ticker": symbol,
            "cik": f"{int(row['cik_str']):010d}",
            "name": require_text(row.get("title"), "SEC company title"),
            **receipt,
        })
    return results


def resolve_sec_company(
    ticker: str, *, user_agent: str, workspace: str | Path, timeout_seconds: float = 30.0
) -> dict[str, Any]:
    """Resolve one ticker to SEC identity and cache the exact registry bytes."""
    return resolve_sec_companies(
        (ticker,), user_agent=user_agent, workspace=workspace,
        timeout_seconds=timeout_seconds,
    )[0]


def _quarterly_sec_selections() -> list[dict[str, Any]]:
    return [
        {"metric_id": "revenue_q", "taxonomy": "us-gaap", "concept": "RevenueFromContractWithCustomerExcludingAssessedTax", "fallback_concepts": ["Revenues", "SalesRevenueNet"], "source_unit": "USD", "unit": "USD/quarter", "period": "quarter"},
        {"metric_id": "operating_income_q", "taxonomy": "us-gaap", "concept": "OperatingIncomeLoss", "source_unit": "USD", "unit": "USD/quarter", "period": "quarter"},
        {"metric_id": "net_income_q", "taxonomy": "us-gaap", "concept": "NetIncomeLoss", "source_unit": "USD", "unit": "USD/quarter", "period": "quarter"},
    ]


def _sec_source(symbol: str, cik: str) -> dict[str, Any]:
    return {
        "id": f"sec_{symbol.lower()}_companyfacts",
        "adapter": "sec_companyfacts",
        "enabled": True,
        "required": False,
        "cik": cik,
        "entity_id": symbol,
        "user_agent_env": "ZTARE_SEC_USER_AGENT",
        "selections": [
            *_quarterly_sec_selections(),
            {"metric_id": "revenue_fy", "taxonomy": "us-gaap", "concept": "RevenueFromContractWithCustomerExcludingAssessedTax", "fallback_concepts": ["Revenues", "SalesRevenueNet"], "source_unit": "USD", "unit": "USD/year", "period": "annual"},
            {"metric_id": "operating_cash_flow_fy", "taxonomy": "us-gaap", "concept": "NetCashProvidedByUsedInOperatingActivities", "source_unit": "USD", "unit": "USD/year", "period": "annual"},
            {"metric_id": "capital_expenditure_fy", "taxonomy": "us-gaap", "concept": "PaymentsToAcquirePropertyPlantAndEquipment", "fallback_concepts": ["PaymentsForAdditionsToPropertyPlantAndEquipment"], "source_unit": "USD", "unit": "USD/year", "period": "annual"},
            {"metric_id": "net_income_fy", "taxonomy": "us-gaap", "concept": "NetIncomeLoss", "source_unit": "USD", "unit": "USD/year", "period": "annual"},
            {"metric_id": "cash", "taxonomy": "us-gaap", "concept": "CashAndCashEquivalentsAtCarryingValue", "fallback_concepts": ["CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"], "source_unit": "USD", "unit": "USD", "period": "instant"},
            {"metric_id": "assets", "taxonomy": "us-gaap", "concept": "Assets", "source_unit": "USD", "unit": "USD", "period": "instant"},
            {"metric_id": "debt_current", "taxonomy": "us-gaap", "concept": "LongTermDebtAndCapitalLeaseObligationsCurrent", "fallback_concepts": ["LongTermDebtCurrent", "ShortTermBorrowings", "FinanceLeaseLiabilityCurrent"], "source_unit": "USD", "unit": "USD", "period": "instant"},
            {"metric_id": "debt_noncurrent", "taxonomy": "us-gaap", "concept": "LongTermDebtAndCapitalLeaseObligations", "fallback_concepts": ["LongTermDebtNoncurrent", "LongTermDebt", "FinanceLeaseLiabilityNoncurrent"], "source_unit": "USD", "unit": "USD", "period": "instant"},
            {"metric_id": "diluted_shares", "taxonomy": "us-gaap", "concept": "WeightedAverageNumberOfDilutedSharesOutstanding", "source_unit": "shares", "unit": "shares", "period": "annual"},
            {"metric_id": "diluted_shares_current", "taxonomy": "us-gaap", "concept": "WeightedAverageNumberOfDilutedSharesOutstanding", "source_unit": "shares", "unit": "shares", "period": "any"},
        ],
    }


def _sec_submissions_source(symbol: str, cik: str) -> dict[str, Any]:
    return {
        "id": f"sec_{symbol.lower()}_submissions",
        "adapter": "sec_submissions",
        "enabled": True,
        "required": False,
        "cik": cik,
        "entity_id": symbol,
        "user_agent_env": "ZTARE_SEC_USER_AGENT",
    }


def repair_public_equity_monitor_sources(workspace: str | Path) -> dict[str, Any]:
    """Add the filing-index event sensor to already enrolled public equities."""
    root = Path(workspace).expanduser().resolve()
    path = root / "sources.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != PUBLIC_SOURCE_MANIFEST_SCHEMA:
        raise ValueError(f"source manifest schema must be {PUBLIC_SOURCE_MANIFEST_SCHEMA}")
    sources = payload.setdefault("sources", [])
    if not isinstance(sources, list):
        raise ValueError("source manifest sources must be a list")
    existing_ids = {
        str(row.get("id") or "") for row in sources if isinstance(row, Mapping)
    }
    monitored_entities = {
        str(row.get("entity_id") or "").upper()
        for row in sources
        if isinstance(row, Mapping) and row.get("adapter") == "sec_submissions"
    }
    added: list[str] = []
    for row in tuple(sources):
        if not isinstance(row, Mapping) or row.get("adapter") != "sec_companyfacts":
            continue
        symbol = _symbol(str(row.get("entity_id") or ""))
        if symbol in monitored_entities:
            continue
        source = _sec_submissions_source(symbol, require_text(row.get("cik"), "SEC source cik"))
        if source["id"] in existing_ids:
            raise ValueError(f"source id collision while repairing equity monitor {symbol}")
        sources.append(source)
        existing_ids.add(source["id"])
        monitored_entities.add(symbol)
        added.append(source["id"])
    if added:
        _atomic_yaml(path, payload)
    body = {
        "schema": "jaggedthoughts-public-equity-monitor-source-repair-v1",
        "added_source_ids": added,
        "added_source_count": len(added),
        "manifest_sha256": stable_sha256(payload),
    }
    return {**body, "repair_sha256": stable_sha256(body)}


def repair_public_equity_quarterly_sources(workspace: str | Path) -> dict[str, Any]:
    """Add quarterly operating facts to already enrolled company-facts sources."""
    root = Path(workspace).expanduser().resolve()
    path = root / "sources.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != PUBLIC_SOURCE_MANIFEST_SCHEMA:
        raise ValueError(f"source manifest schema must be {PUBLIC_SOURCE_MANIFEST_SCHEMA}")
    sources = payload.get("sources")
    if not isinstance(sources, list):
        raise ValueError("source manifest sources must be a list")
    additions: list[dict[str, str]] = []
    for source in sources:
        if not isinstance(source, dict) or source.get("adapter") != "sec_companyfacts":
            continue
        selections = source.setdefault("selections", [])
        if not isinstance(selections, list):
            raise ValueError("SEC company-facts selections must be a list")
        present = {
            str(row.get("metric_id") or "")
            for row in selections if isinstance(row, Mapping)
        }
        missing = [row for row in _quarterly_sec_selections() if row["metric_id"] not in present]
        selections.extend(missing)
        additions.extend({"source_id": str(source.get("id") or ""), "metric_id": row["metric_id"]} for row in missing)
    if additions:
        _atomic_yaml(path, payload)
    body = {
        "schema": "jaggedthoughts-public-equity-quarterly-source-repair-v1",
        "additions": additions,
        "manifest_sha256": stable_sha256(payload),
    }
    return {**body, "repair_sha256": stable_sha256(body)}


def _price_source(symbol: str) -> dict[str, Any]:
    return {
        "id": f"yahoo_{symbol.lower()}_daily", "adapter": "yahoo_chart_daily",
        "enabled": True, "required": False, "symbol": symbol,
        "entity_id": symbol, "metric_id": "price", "unit": "USD",
        "range": "5y", "interval": "1d", "price_kind": "close",
    }


FUND_VALUATION_INPUTS = (
    "portfolio_price_to_earnings",
    "portfolio_price_to_book",
    "expense_ratio",
    "portfolio_earnings_yield",
    "portfolio_book_to_price",
    "portfolio_net_earnings_yield",
)


def _fund_issuer_source(symbol: str, name: str) -> dict[str, Any] | None:
    """Return a provider adapter from issuer identity, never from a security score."""
    normalized = re.sub(r"\s+", " ", name).strip().lower()
    if normalized.startswith("vanguard "):
        return {
            "id": f"vanguard_{symbol.lower()}_fundamentals",
            "adapter": "vanguard_fundamentals",
            "enabled": True,
            "required": False,
            "symbol": symbol,
            "entity_id": symbol,
        }
    if normalized.startswith("ishares "):
        return {
            "id": f"ishares_{symbol.lower()}_fundamentals",
            "adapter": "ishares_fundamentals",
            "enabled": True,
            "required": False,
            "symbol": symbol,
            "entity_id": symbol,
        }
    if normalized.startswith("harbor "):
        return {
            "id": f"harbor_{symbol.lower()}_fundamentals",
            "adapter": "harbor_fundamentals",
            "enabled": True,
            "required": False,
            "symbol": symbol,
            "entity_id": symbol,
        }
    if normalized.startswith("avantis "):
        slug = re.sub(r"[^a-z0-9]+", "-", normalized.replace("u.s.", "us")).strip("-")
        return {
            "id": f"avantis_{symbol.lower()}_fundamentals",
            "adapter": "avantis_fundamentals",
            "enabled": True,
            "required": False,
            "symbol": symbol,
            "entity_id": symbol,
            "url": f"https://www.avantisinvestors.com/avantis-investments/{slug}/",
        }
    if normalized.startswith("first trust "):
        return {
            "id": f"first_trust_{symbol.lower()}_fundamentals",
            "adapter": "first_trust_fundamentals",
            "enabled": True,
            "required": False,
            "symbol": symbol,
            "entity_id": symbol,
        }
    return None


def repair_public_fund_sources(workspace: str | Path) -> dict[str, Any]:
    """Attach supported issuer adapters to existing fund identities atomically."""
    root = Path(workspace).expanduser().resolve()
    source_path = root / "sources.yaml"
    manifest = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("schema") != PUBLIC_SOURCE_MANIFEST_SCHEMA:
        raise ValueError(f"source manifest schema must be {PUBLIC_SOURCE_MANIFEST_SCHEMA}")
    sources = manifest.setdefault("sources", [])
    if not isinstance(sources, list):
        raise ValueError("fund repair requires a source list")
    watchlists: list[tuple[Path, dict[str, Any]]] = []
    owner_by_entity: dict[str, str] = {}
    for path in sorted((root / "watchlists").glob("*.yaml")):
        watchlist = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(watchlist, dict) or watchlist.get("schema") != "jaggedthoughts-opportunity-watchlist-v1":
            raise ValueError("public fund watchlist has an unsupported schema")
        candidates = watchlist.setdefault("candidates", [])
        if not isinstance(candidates, list):
            raise ValueError("fund repair requires watchlist candidate lists")
        relative = path.relative_to(root).as_posix()
        for candidate in candidates:
            if not isinstance(candidate, Mapping):
                continue
            symbol = _symbol(str(candidate.get("entity_id") or ""))
            prior = owner_by_entity.setdefault(symbol, relative)
            if prior != relative:
                raise ValueError(f"public fund {symbol} appears in multiple watchlists: {prior}, {relative}")
        watchlists.append((path, watchlist))
    supported_adapters = {
        "avantis_fundamentals", "first_trust_fundamentals", "harbor_fundamentals",
        "ishares_fundamentals", "vanguard_fundamentals",
    }
    evidence_adapters = {*supported_adapters, "first_trust_holdings"}
    source_ids = {str(row.get("id") or "") for row in sources if isinstance(row, Mapping)}
    by_entity = {
        str(row.get("entity_id") or "").upper(): row
        for row in sources
        if isinstance(row, Mapping) and row.get("adapter") in supported_adapters
    }
    evidence_by_entity: dict[str, set[str]] = {}
    for row in sources:
        if not isinstance(row, Mapping) or row.get("adapter") not in evidence_adapters:
            continue
        entity = str(row.get("entity_id") or "").upper()
        source_id = str(row.get("id") or "")
        if entity and source_id:
            evidence_by_entity.setdefault(entity, set()).add(source_id)
    added: list[str] = []
    configured: list[dict[str, Any]] = []
    unresolved: list[dict[str, str]] = []
    watchlist_hashes: dict[str, str] = {}
    for watchlist_path, watchlist in watchlists:
        watchlist_changed = False
        for candidate in watchlist["candidates"]:
            if not isinstance(candidate, dict):
                continue
            symbol = _symbol(str(candidate.get("entity_id") or ""))
            name = require_text(candidate.get("name"), f"fund {symbol} name")
            issuer_source = by_entity.get(symbol)
            if issuer_source is None:
                issuer_source = _fund_issuer_source(symbol, name)
                if issuer_source is not None:
                    if issuer_source["id"] in source_ids:
                        raise ValueError(f"source id collision while repairing fund {symbol}")
                    sources.append(issuer_source)
                    source_ids.add(str(issuer_source["id"]))
                    by_entity[symbol] = issuer_source
                    evidence_by_entity.setdefault(symbol, set()).add(str(issuer_source["id"]))
                    added.append(str(issuer_source["id"]))
            if issuer_source is None:
                unresolved.append({
                    "ticker": symbol, "name": name,
                    "watchlist_path": watchlist_path.relative_to(root).as_posix(),
                    "reason": "issuer_adapter_not_registered",
                })
                continue
            valuation_inputs = list(FUND_VALUATION_INPUTS)
            if candidate.get("valuation_inputs") != valuation_inputs:
                candidate["valuation_inputs"] = valuation_inputs
                watchlist_changed = True
            configured.append({
                "ticker": symbol,
                "watchlist_path": watchlist_path.relative_to(root).as_posix(),
                "source_id": str(issuer_source["id"]),
                "evidence_source_ids": sorted(evidence_by_entity.get(symbol, {str(issuer_source["id"])})),
                "price_source_id": f"yahoo_{symbol.lower()}_daily",
                "adapter": str(issuer_source["adapter"]),
                "valuation_inputs": valuation_inputs,
            })
        if watchlist_changed:
            _atomic_yaml(watchlist_path, watchlist)
        watchlist_hashes[watchlist_path.relative_to(root).as_posix()] = stable_sha256(watchlist)
    if added:
        _atomic_yaml(source_path, manifest)
    aggregate_watchlist_sha256 = stable_sha256(watchlist_hashes)
    body = {
        "schema": "jaggedthoughts-public-fund-source-repair-v1",
        "configured": configured,
        "configured_count": len(configured),
        "added_source_ids": sorted(added),
        "refresh_source_ids": sorted({
            source_id
            for row in configured
            for source_id in (*row["evidence_source_ids"], row["price_source_id"])
        }),
        "unresolved": unresolved,
        "unresolved_count": len(unresolved),
        "source_manifest_sha256": stable_sha256(manifest),
        "watchlist_sha256s": watchlist_hashes,
        "watchlist_sha256": aggregate_watchlist_sha256,
        "capital_authority": False,
    }
    return {**body, "repair_sha256": stable_sha256(body)}


def _signal_rows(symbol: str) -> list[dict[str, Any]]:
    prefix = symbol.lower().replace(".", "_").replace("-", "_")
    definitions = (
        ("owner_earnings", "normalized_owner_earnings", "aligned_subtract", "USD/year", ["operating_cash_flow_fy", "capital_expenditure_fy"], "Annual operating cash flow less reported capital expenditure from the same fiscal period."),
        ("cash_conversion", "cash_conversion", "ratio", "multiple", ["operating_cash_flow_fy", "net_income_fy"], "Annual operating cash flow divided by annual net income."),
        ("return_on_assets", "return_on_assets", "ratio", "decimal", ["net_income_fy", "assets"], "Annual net income divided by reported assets."),
        ("cash_to_assets", "cash_to_assets", "ratio", "decimal", ["cash", "assets"], "Cash and equivalents divided by reported assets."),
        ("total_debt", "total_debt", "add", "USD", ["debt_current", "debt_noncurrent"], "Current and noncurrent reported debt."),
        ("excess_net_cash", "excess_net_cash", "subtract", "USD", ["cash", "total_debt"], "Cash and equivalents less total reported debt."),
        ("net_debt", "net_debt", "negative", "USD", ["excess_net_cash"], "Total reported debt less cash and equivalents."),
        ("market_cap", "market_cap", "multiply", "USD", ["price", "diluted_shares_current"], "Latest retrieved price times the freshest filed diluted-share basis."),
        ("owner_earnings_yield", "owner_earnings_yield", "yield", "decimal", ["normalized_owner_earnings", "market_cap"], "Normalized owner earnings divided by source-derived market capitalization."),
        ("net_debt_to_owner_earnings", "net_debt_to_owner_earnings", "ratio", "multiple", ["net_debt", "normalized_owner_earnings"], "Reported debt less cash, divided by normalized owner earnings."),
    )
    return [{
        "schema": "jaggedthoughts-signal-definition-v1",
        "id": f"{prefix}_{suffix}", "required": False,
        "entity_id": symbol, "metric_id": metric_id, "operator": operator,
        "unit": unit, "description": description,
        "arguments": [{"metric": metric} for metric in arguments],
    } for suffix, metric_id, operator, unit, arguments, description in definitions]


def public_equity_is_enrolled(workspace: str | Path, ticker: str) -> bool:
    root = Path(workspace).expanduser().resolve()
    payload = yaml.safe_load((root / "sources.yaml").read_text(encoding="utf-8"))
    symbol = _symbol(ticker)
    return any(
        isinstance(row, Mapping)
        and row.get("adapter") == "sec_companyfacts"
        and str(row.get("entity_id") or "").upper() == symbol
        for row in (payload.get("sources") or [])
    )


def enroll_public_equities(
    workspace: str | Path, *, tickers: Sequence[str], user_agent: str | None = None,
) -> dict[str, Any]:
    """Atomically add several SEC/Yahoo bundles using one registry request."""
    root = Path(workspace).expanduser().resolve()
    path = root / "sources.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != PUBLIC_SOURCE_MANIFEST_SCHEMA:
        raise ValueError(f"source manifest schema must be {PUBLIC_SOURCE_MANIFEST_SCHEMA}")
    symbols = tuple(dict.fromkeys(_symbol(value) for value in tickers))
    if not symbols:
        return {
            "schema": "jaggedthoughts-public-equity-enrollment-batch-v1",
            "enrollments": [], "registry_source_calls": 0,
            "added_source_count": 0, "added_signal_count": 0,
            "manifest_sha256": stable_sha256(payload),
        }
    sources = payload.setdefault("sources", [])
    signals = payload.setdefault("signals", [])
    if not isinstance(sources, list) or not isinstance(signals, list):
        raise ValueError("source manifest sources and signals must be lists")
    enrolled = {
        str(row.get("entity_id") or "").upper()
        for row in sources if isinstance(row, Mapping)
        and row.get("adapter") == "sec_companyfacts"
    }
    duplicates = sorted(set(symbols) & enrolled)
    if duplicates:
        raise FileExistsError(
            "public-equity universe already contains: " + ", ".join(duplicates)
        )
    agent = str(
        user_agent or os.environ.get("ZTARE_SEC_USER_AGENT") or DEFAULT_SEC_USER_AGENT
    ).strip()
    resolutions = resolve_sec_companies(symbols, user_agent=agent, workspace=root)
    resolution_by_symbol = {str(row["ticker"]): row for row in resolutions}
    new_sources = [
        source
        for symbol in symbols
        for source in (
            _sec_source(symbol, str(resolution_by_symbol[symbol]["cik"])),
            _sec_submissions_source(symbol, str(resolution_by_symbol[symbol]["cik"])),
            _price_source(symbol),
        )
    ]
    new_signals = [row for symbol in symbols for row in _signal_rows(symbol)]
    existing_source_ids = {str(row.get("id")) for row in sources if isinstance(row, Mapping)}
    existing_signal_ids = {str(row.get("id")) for row in signals if isinstance(row, Mapping)}
    source_collisions = sorted(existing_source_ids.intersection(str(row["id"]) for row in new_sources))
    signal_collisions = sorted(existing_signal_ids.intersection(str(row["id"]) for row in new_signals))
    if source_collisions:
        raise ValueError("source id collision while enrolling batch: " + ", ".join(source_collisions))
    if signal_collisions:
        raise ValueError("signal id collision while enrolling batch: " + ", ".join(signal_collisions))
    sources.extend(new_sources)
    signals.extend(new_signals)
    _atomic_yaml(path, payload)
    manifest_sha256 = stable_sha256(payload)
    enrollments: list[dict[str, Any]] = []
    for symbol in symbols:
        resolution = resolution_by_symbol[symbol]
        body = {
            "schema": "jaggedthoughts-public-equity-enrollment-v1",
            "ticker": symbol,
            "entity_name": resolution["name"],
            "cik": resolution["cik"],
            "source_ids": [
                f"sec_{symbol.lower()}_companyfacts",
                f"sec_{symbol.lower()}_submissions",
                f"yahoo_{symbol.lower()}_daily",
            ],
            "signal_ids": [row["id"] for row in _signal_rows(symbol)],
            "registry_path": resolution["registry_path"],
            "registry_sha256": resolution["registry_sha256"],
            "manifest_sha256": manifest_sha256,
        }
        enrollments.append({**body, "enrollment_sha256": stable_sha256(body)})
    batch_body = {
        "schema": "jaggedthoughts-public-equity-enrollment-batch-v1",
        "enrollments": enrollments,
        "registry_source_calls": 1,
        "added_source_count": len(new_sources),
        "added_signal_count": len(new_signals),
        "manifest_sha256": manifest_sha256,
    }
    return {**batch_body, "batch_sha256": stable_sha256(batch_body)}


def enroll_public_equity(
    workspace: str | Path, *, ticker: str, user_agent: str | None = None
) -> dict[str, Any]:
    """Add one SEC/Yahoo source bundle and deterministic derived-signal set."""
    return enroll_public_equities(
        workspace, tickers=(ticker,), user_agent=user_agent,
    )["enrollments"][0]


def enroll_public_funds(
    workspace: str | Path,
    *,
    funds: Sequence[Mapping[str, Any]],
    watchlist_path: str | Path = "watchlists/public_fund_opportunities.yaml",
) -> dict[str, Any]:
    """Atomically add several fund price and watchlist identities."""
    root = Path(workspace).expanduser().resolve()
    normalized = [
        {
            "ticker": _symbol(str(row.get("ticker") or "")),
            "name": require_text(row.get("name"), "public fund name"),
            "category": str(row.get("category") or "public ETF catalog candidate"),
            "implementation_sleeve_id": str(row.get("implementation_sleeve_id") or ""),
            "implementation_sleeve_source_refs": tuple(require_refs(
                refs, "public fund implementation_sleeve_source_refs",
            )) if (refs := row.get("implementation_sleeve_source_refs") or ()) else (),
            "peer_group_id": str(row.get("peer_group_id") or ""),
            "comparison_cell": dict(row.get("comparison_cell") or {}),
        }
        for row in funds
    ]
    for row in normalized:
        sleeve_id = row["implementation_sleeve_id"]
        if sleeve_id and sleeve_id not in PUBLIC_SLEEVE_IDS:
            raise ValueError(f"unknown public implementation sleeve: {sleeve_id}")
        if bool(sleeve_id) != bool(row["implementation_sleeve_source_refs"]):
            raise ValueError("public fund implementation sleeve identity requires source refs")
        if row["comparison_cell"] and row["comparison_cell"].get("asset_class") != "equity":
            raise ValueError("equity fund watchlists cannot enroll non-equity comparison cells")
        if bool(row["peer_group_id"]) != bool(row["comparison_cell"]):
            raise ValueError("fund peer-group identity requires its exact comparison cell")
    symbols = [row["ticker"] for row in normalized]
    if len(set(symbols)) != len(symbols):
        raise ValueError("fund enrollment batch contains duplicate tickers")
    source_path = root / "sources.yaml"
    source_manifest = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    if not isinstance(source_manifest, dict) or source_manifest.get("schema") != PUBLIC_SOURCE_MANIFEST_SCHEMA:
        raise ValueError(f"source manifest schema must be {PUBLIC_SOURCE_MANIFEST_SCHEMA}")
    sources = source_manifest.setdefault("sources", [])
    if not isinstance(sources, list):
        raise ValueError("source manifest sources must be a list")
    relative_watchlist = Path(watchlist_path)
    if relative_watchlist.is_absolute():
        raise ValueError("public fund watchlist_path must be workspace-relative")
    if relative_watchlist.suffix.lower() not in {".yaml", ".yml"}:
        raise ValueError("public fund watchlist_path must be YAML")
    watchlist_path = (root / relative_watchlist).resolve()
    try:
        watchlist_path.relative_to(root / "watchlists")
    except ValueError as error:
        raise ValueError("public fund watchlist_path must stay under watchlists/") from error
    watchlist = yaml.safe_load(watchlist_path.read_text(encoding="utf-8"))
    if not isinstance(watchlist, dict) or watchlist.get("schema") != "jaggedthoughts-opportunity-watchlist-v1":
        raise ValueError("public fund watchlist has an unsupported schema")
    candidates = watchlist.setdefault("candidates", [])
    if not isinstance(candidates, list):
        raise ValueError("public fund watchlist candidates must be a list")
    existing_candidates = {
        str(row.get("entity_id") or "").upper()
        for path in sorted((root / "watchlists").rglob("*.yaml"))
        for profile in [yaml.safe_load(path.read_text(encoding="utf-8"))]
        if isinstance(profile, Mapping)
        for row in profile.get("candidates") or ()
        if isinstance(row, Mapping)
    }
    duplicates = sorted(set(symbols) & existing_candidates)
    if duplicates:
        raise FileExistsError("public fund watchlist already contains: " + ", ".join(duplicates))
    existing_source_ids = {
        str(row.get("id") or "") for row in sources if isinstance(row, Mapping)
    }
    enrollments: list[dict[str, Any]] = []
    for row in normalized:
        symbol = row["ticker"]
        price_source = _price_source(symbol)
        issuer_source = _fund_issuer_source(symbol, row["name"])
        price_exists = any(
            isinstance(source, Mapping)
            and source.get("adapter") == "yahoo_chart_daily"
            and str(source.get("entity_id") or "").upper() == symbol
            for source in sources
        )
        if not price_exists:
            if price_source["id"] in existing_source_ids:
                raise ValueError(f"source id collision while enrolling fund {symbol}")
            sources.append(price_source)
            existing_source_ids.add(price_source["id"])
        issuer_source_added = False
        issuer_source_added_count = 0
        issuer_source_ids: list[str] = []
        if issuer_source is not None:
            evidence_sources = [issuer_source]
            if issuer_source["adapter"] == "first_trust_fundamentals":
                evidence_sources.append({
                    "id": f"first_trust_{symbol.lower()}_holdings",
                    "adapter": "first_trust_holdings", "enabled": True, "required": False,
                    "symbol": symbol, "entity_id": symbol,
                })
            for evidence_source in evidence_sources:
                issuer_source_ids.append(str(evidence_source["id"]))
                issuer_exists = any(
                    isinstance(source, Mapping)
                    and source.get("adapter") == evidence_source["adapter"]
                    and str(source.get("entity_id") or "").upper() == symbol
                    for source in sources
                )
                if issuer_exists:
                    continue
                if evidence_source["id"] in existing_source_ids:
                    raise ValueError(f"source id collision while enrolling fund {symbol}")
                sources.append(evidence_source)
                existing_source_ids.add(str(evidence_source["id"]))
                issuer_source_added_count += 1
            issuer_source_added = bool(issuer_source_added_count)
        candidate = {
            "id": f"catalog-{symbol.lower()}",
            "entity_id": symbol,
            "name": row["name"],
            "category": row["category"],
            "vehicle_kind": "exchange_traded_fund",
            "alpha_persistence_weight": 0.0,
            "valuation_inputs": list(FUND_VALUATION_INPUTS) if issuer_source else [],
            "thesis_prompt": (
                "Does this vehicle offer useful factor exposure after fees, drawdown, liquidity, "
                "holdings concentration, and a separately sourced portfolio-valuation review?"
            ),
        }
        if row["implementation_sleeve_id"]:
            candidate.update({
                "implementation_sleeve_id": row["implementation_sleeve_id"],
                "implementation_sleeve_source_refs": list(
                    row["implementation_sleeve_source_refs"]
                ),
            })
        if row["peer_group_id"]:
            candidate.update({
                "peer_group_id": row["peer_group_id"],
                "comparison_cell": row["comparison_cell"],
            })
        candidates.append(candidate)
        enrollments.append({
            "ticker": symbol, "name": row["name"], "category": row["category"],
            "source_id": price_source["id"], "price_source_added": not price_exists,
            "source_ids": [
                price_source["id"],
                *issuer_source_ids,
            ],
            "issuer_source_id": str(issuer_source["id"]) if issuer_source else None,
            "issuer_source_added": issuer_source_added,
            "issuer_source_added_count": issuer_source_added_count,
            "candidate_id": candidate["id"],
            "implementation_sleeve_id": row["implementation_sleeve_id"] or None,
            "implementation_sleeve_source_refs": list(
                row["implementation_sleeve_source_refs"]
            ),
            "peer_group_id": row["peer_group_id"] or None,
            "comparison_cell": row["comparison_cell"] or None,
        })
    _atomic_yaml(source_path, source_manifest)
    _atomic_yaml(watchlist_path, watchlist)
    source_manifest_sha256 = stable_sha256(source_manifest)
    watchlist_sha256 = stable_sha256(watchlist)
    completed: list[dict[str, Any]] = []
    for row in enrollments:
        body = {
            "schema": "jaggedthoughts-public-fund-enrollment-v1",
            **row,
            "watchlist_id": watchlist["watchlist_id"],
            "source_manifest_sha256": source_manifest_sha256,
            "watchlist_sha256": watchlist_sha256,
            "valuation_status": (
                "issuer_source_configured"
                if row.get("issuer_source_id")
                else "requires_issuer_or_holdings_evidence"
            ),
        }
        completed.append({**body, "enrollment_sha256": stable_sha256(body)})
    batch_body = {
        "schema": "jaggedthoughts-public-fund-enrollment-batch-v1",
        "enrollments": completed,
        "registry_source_calls": 0,
        "added_source_count": sum(
            bool(row["price_source_added"]) + int(row["issuer_source_added_count"])
            for row in enrollments
        ),
        "watchlist_id": watchlist["watchlist_id"],
        "watchlist_path": watchlist_path.relative_to(root).as_posix(),
        "source_manifest_sha256": source_manifest_sha256,
        "watchlist_sha256": watchlist_sha256,
    }
    return {**batch_body, "batch_sha256": stable_sha256(batch_body)}


def enroll_public_fund(
    workspace: str | Path,
    *,
    ticker: str,
    name: str,
    category: str = "public ETF catalog candidate",
) -> dict[str, Any]:
    """Add one fund price series and factor-watchlist identity."""
    return enroll_public_funds(workspace, funds=({
        "ticker": ticker, "name": name, "category": category,
    },))["enrollments"][0]


__all__ = [
    "SEC_TICKER_REGISTRY_URL",
    "enroll_public_equity",
    "enroll_public_equities",
    "enroll_public_fund",
    "enroll_public_funds",
    "public_equity_is_enrolled",
    "repair_public_equity_monitor_sources",
    "repair_public_equity_quarterly_sources",
    "repair_public_fund_sources",
    "resolve_sec_company",
    "resolve_sec_companies",
]
