"""Broad public-market catalog and typed research-intent compiler.

The catalog is a cheap, retrieval-time discovery layer.  It owns security
identity and coarse eligibility.  Fundamental claims, factor exposure,
valuation, company strategy, and portfolio admission remain later objects.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Callable, Mapping

import requests

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, require_text
from .sources import MAX_SOURCE_BYTES


CATALOG_SCHEMA = "jaggedthoughts-public-market-catalog-v1"
INTENT_SCHEMA = "jaggedthoughts-market-research-intent-v1"
SCOUT_SCHEMA = "jaggedthoughts-market-scout-run-v1"

NASDAQ_STOCK_SCREENER_URL = (
    "https://api.nasdaq.com/api/screener/stocks"
    "?tableonly=true&limit=25&offset=0&download=true"
)
NASDAQ_ETF_SCREENER_URL = (
    "https://api.nasdaq.com/api/screener/etf"
    "?tableonly=true&limit=25&offset=0&download=true"
)

Fetch = Callable[[str], bytes]

_CAP_BANDS = {
    "micro": (50_000_000.0, 300_000_000.0),
    "small": (300_000_000.0, 2_000_000_000.0),
    "mid": (2_000_000_000.0, 10_000_000_000.0),
    "large": (10_000_000_000.0, 200_000_000_000.0),
    "mega": (200_000_000_000.0, None),
}
_STYLE_TERMS = {
    "value": ("value", "undervalued", "cheap", "low implied growth"),
    "quality": ("quality", "durable", "earnings power", "profitable"),
    "growth": ("growth",),
    "momentum": ("momentum",),
    "income": ("income", "dividend", "yield"),
    "low_volatility": ("low volatility", "minimum volatility", "min vol"),
}
# Parser conveniences for common catalog language.  The typed intent also
# accepts arbitrary ``theme_terms`` supplied by an operator or research agent;
# this map is not the universe of themes the kernel can represent.
_CATALOG_THEME_ALIASES = {
    "technology": ("technology", "software", "computer", "internet"),
    "semiconductors": ("semiconductor", "chip"),
    "healthcare": ("health care", "healthcare", "medical", "pharmaceutical"),
    "biotechnology": ("biotech", "biotechnology"),
    "finance": ("finance", "financial", "bank", "insurance"),
    "energy": ("energy", "oil", "gas", "petroleum"),
    "industrials": ("industrial", "manufacturing", "machinery"),
    "consumer": ("consumer", "retail", "restaurant", "food"),
    "real_estate": ("real estate", "reit"),
    "utilities": ("utility", "utilities", "electric power"),
    "communications": ("telecom", "communications", "broadcasting"),
    "materials": ("materials", "mining", "chemicals", "steel", "aluminum"),
}
_REJECTED_SECURITY_WORDS = (
    " warrant", " warrants", " right", " rights", " unit", " units",
    " preferred", " depositary", " notes due ", " acquisition corp",
    " acquisition company",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    _atomic_bytes(
        path,
        (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"),
    )


def _number(value: Any) -> float | None:
    text = str(value or "").strip().replace("$", "").replace(",", "").replace("%", "")
    if not text or text.lower() in {"n/a", "na", "none", "--"}:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _nasdaq_fetch(url: str) -> bytes:
    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 JaggedThoughts/1.0",
                "Origin": "https://www.nasdaq.com",
                "Referer": "https://www.nasdaq.com/",
                "Accept": "application/json, text/plain, */*",
            },
            timeout=(10, 30),
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise ValueError(f"Nasdaq catalog request failed: {error}") from error
    content = response.content
    if len(content) > MAX_SOURCE_BYTES:
        raise ValueError(f"Nasdaq catalog response exceeds {MAX_SOURCE_BYTES} bytes")
    return content


def _rows(payload: Mapping[str, Any], *, kind: str) -> list[Mapping[str, Any]]:
    data = payload.get("data")
    if not isinstance(data, Mapping):
        raise ValueError(f"Nasdaq {kind} response has no data object")
    if kind == "public_fund":
        data = data.get("data")
        if not isinstance(data, Mapping):
            raise ValueError("Nasdaq fund response has no nested data object")
    rows = data.get("rows")
    if not isinstance(rows, list):
        raise ValueError(f"Nasdaq {kind} response has no rows")
    return [row for row in rows if isinstance(row, Mapping)]


def _equity_security_kind(name: str) -> str:
    lower = f" {name.lower()} "
    if any(token in lower for token in _REJECTED_SECURITY_WORDS):
        return "other_listed_security"
    return "common_equity"


def refresh_public_market_catalog(
    workspace: str | Path,
    *,
    retrieved_at: str | None = None,
    fetch: Fetch | None = None,
) -> dict[str, Any]:
    """Fetch two broad Nasdaq catalogs and materialize normalized security rows."""
    root = Path(workspace).expanduser().resolve()
    retrieval = canonical_timestamp(retrieved_at or _utc_now(), "catalog retrieved_at")
    fetcher = fetch or _nasdaq_fetch
    raw_payloads: list[tuple[str, str, bytes]] = []
    for source_id, url in (
        ("nasdaq_us_listed_equities", NASDAQ_STOCK_SCREENER_URL),
        ("nasdaq_exchange_traded_funds", NASDAQ_ETF_SCREENER_URL),
    ):
        raw_payloads.append((source_id, url, fetcher(url)))

    securities: dict[str, dict[str, Any]] = {}
    receipts: list[dict[str, Any]] = []
    for source_id, url, content in raw_payloads:
        digest = hashlib.sha256(content).hexdigest()
        relative = Path("universe") / "raw" / f"{source_id}-{digest[:20]}.json"
        _atomic_bytes(root / relative, content)
        payload = json.loads(content.decode("utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError(f"{source_id} response must be a JSON object")
        kind = "public_fund" if source_id.endswith("funds") else "public_equity"
        source_rows = _rows(payload, kind=kind)
        for raw in source_rows:
            symbol = str(raw.get("symbol") or "").strip().upper()
            if not re.fullmatch(r"[A-Z0-9][A-Z0-9.-]{0,14}", symbol):
                continue
            name = str(raw.get("companyName") or raw.get("name") or symbol).strip()
            row = {
                "security_id": f"{kind}:{symbol}",
                "symbol": symbol,
                "name": name,
                "entity_kind": kind,
                "security_kind": "exchange_traded_fund" if kind == "public_fund" else _equity_security_kind(name),
                "last_price": _number(raw.get("lastSalePrice") or raw.get("lastsale")),
                "one_year_return": (
                    (_number(raw.get("oneYearPercentage")) or 0.0) / 100.0
                    if raw.get("oneYearPercentage") not in {None, ""} else None
                ),
                "market_cap": _number(raw.get("marketCap")),
                "volume": _number(raw.get("volume")),
                "country": str(raw.get("country") or "").strip(),
                "sector": str(raw.get("sector") or "").strip(),
                "industry": str(raw.get("industry") or "").strip(),
                "ipo_year": int(raw["ipoyear"]) if str(raw.get("ipoyear") or "").isdigit() else None,
                "available_at": retrieval,
                "availability_mode": "retrieval_only",
                "source_id": source_id,
                "source_path": relative.as_posix(),
            }
            # The ETF catalog owns a symbol if Nasdaq happens to expose it in both feeds.
            if symbol not in securities or kind == "public_fund":
                securities[symbol] = row
        receipts.append({
            "source_id": source_id,
            "canonical_url": url,
            "retrieved_at": retrieval,
            "content_sha256": digest,
            "raw_path": relative.as_posix(),
            "row_count": len(source_rows),
            "availability_mode": "retrieval_only",
        })

    normalized = sorted(securities.values(), key=lambda row: (row["entity_kind"], row["symbol"]))
    counts = Counter(str(row["entity_kind"]) for row in normalized)
    body: dict[str, Any] = {
        "schema": CATALOG_SCHEMA,
        "retrieved_at": retrieval,
        "availability_mode": "retrieval_only",
        "provider": "Nasdaq public screeners",
        "security_count": len(normalized),
        "eligible_common_equity_count": sum(row["security_kind"] == "common_equity" for row in normalized),
        "counts_by_entity_kind": dict(sorted(counts.items())),
        "source_receipts": receipts,
        "securities": normalized,
        "use_boundary": (
            "This retrieval-time catalog supports broad identity and coarse screening. "
            "A security needs later point-in-time fundamental, valuation, strategy, and risk evidence before underwriting."
        ),
    }
    catalog = {**body, "catalog_sha256": stable_sha256(body)}
    destination = root / "universe" / "catalog-latest.json"
    _atomic_json(destination, catalog)
    return catalog


def _text_list(value: Any, field: str, *, maximum: int = 64) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field} must be a list")
    result = list(dict.fromkeys(require_text(item, field) for item in value))
    if len(result) > maximum:
        raise ValueError(f"{field} cannot contain more than {maximum} values")
    return result


def compile_research_intent(
    query: str,
    *,
    max_results: int = 50,
    overrides: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Lower market language plus optional agent/operator structure into an intent."""
    text = require_text(query, "market research query")
    normalized = " ".join(text.lower().split())
    supplied = dict(overrides or {})
    if max_results < 1 or max_results > 500:
        raise ValueError("max_results must be between 1 and 500")
    fund_language = any(token in normalized for token in ("fund", "etf", "index", "vehicle"))
    equity_language = any(token in normalized for token in ("company", "companies", "stock", "ticker", "equity", "business"))
    entity_kinds = (
        ["public_fund"] if fund_language and not equity_language
        else ["public_equity"] if equity_language and not fund_language
        else ["public_equity", "public_fund"]
    )
    capitalization = next((name for name in _CAP_BANDS if re.search(rf"\b{name}(?:[- ]cap)?\b", normalized)), None)
    styles = sorted(
        style for style, terms in _STYLE_TERMS.items()
        if any(term in normalized for term in terms)
    )
    themes = sorted(
        theme for theme, terms in _CATALOG_THEME_ALIASES.items()
        if any(term in normalized for term in terms)
    )
    supplied_themes = _text_list(supplied.get("themes"), "intent themes", maximum=24)
    themes = list(dict.fromkeys([*themes, *supplied_themes]))
    alias_terms = [
        term
        for theme in themes
        for term in _CATALOG_THEME_ALIASES.get(theme, (theme.replace("_", " "),))
    ]
    explicit_theme_terms = [
        term.lower() for term in _text_list(
            supplied.get("theme_terms"), "intent theme_terms", maximum=64,
        )
    ]
    # Explicit structure has precedence over the convenience parser so an
    # agent can narrow, rather than accidentally union with, a coarse alias.
    theme_terms = list(dict.fromkeys(explicit_theme_terms or alias_terms))
    direct_symbols = sorted(set(
        token.upper() for token in re.findall(r"(?:\$|ticker\s+)([A-Za-z][A-Za-z0-9.-]{0,14})", text)
    ))
    if supplied.get("entity_kinds") is not None:
        entity_kinds = _text_list(supplied["entity_kinds"], "intent entity_kinds", maximum=2)
        if not entity_kinds or not set(entity_kinds).issubset({"public_equity", "public_fund"}):
            raise ValueError("intent entity_kinds must contain public_equity and/or public_fund")
    if supplied.get("capitalization") is not None:
        capitalization = require_text(supplied["capitalization"], "intent capitalization").lower()
        if capitalization not in _CAP_BANDS:
            raise ValueError(f"unsupported capitalization: {capitalization}")
    if supplied.get("styles") is not None:
        styles = _text_list(supplied["styles"], "intent styles", maximum=24)
    if supplied.get("direct_symbols") is not None:
        direct_symbols = sorted({
            require_text(value, "intent direct_symbols").upper()
            for value in supplied["direct_symbols"]
        })
    countries = ["United States"] if re.search(r"\b(us|u\.s\.|united states)\b", normalized) else []
    if supplied.get("countries") is not None:
        countries = _text_list(supplied["countries"], "intent countries", maximum=32)
    objectives: list[str] = []
    if "value" in styles:
        objectives += ["earnings_power_margin", "low_implied_growth", "price_implied_excess_return"]
    if "quality" in styles:
        objectives += ["earnings_durability", "cash_conversion", "balance_sheet_resilience"]
    if "growth" in styles:
        objectives += ["growth_duration", "reinvestment_return"]
    if "momentum" in styles:
        objectives += ["momentum_exposure", "reversal_risk"]
    if "income" in styles:
        objectives += ["distribution_yield", "distribution_durability"]
    if "low_volatility" in styles:
        objectives += ["drawdown", "residual_volatility"]
    if supplied.get("ranking_objectives") is not None:
        objectives = _text_list(
            supplied["ranking_objectives"], "intent ranking_objectives", maximum=64,
        )
    if supplied.get("max_results") is not None:
        max_results = int(supplied["max_results"])
        if max_results < 1 or max_results > 500:
            raise ValueError("intent max_results must be between 1 and 500")
    body = {
        "schema": INTENT_SCHEMA,
        "query": text,
        "entity_kinds": entity_kinds,
        "capitalization": capitalization,
        "market_cap_min": _CAP_BANDS[capitalization][0] if capitalization else None,
        "market_cap_max": _CAP_BANDS[capitalization][1] if capitalization else None,
        "styles": styles,
        "themes": themes,
        "theme_terms": theme_terms,
        "direct_symbols": direct_symbols,
        "countries": countries,
        "ranking_objectives": list(dict.fromkeys(objectives)) or ["evidence_coverage", "valuation_support", "downside_resilience"],
        "max_results": max_results,
        "compiler_boundary": (
            "Language selects catalog scope and downstream measurements. "
            "It does not convert adjectives such as value or quality into unsupported catalog facts."
        ),
        "translation": {
            "common_aliases": True,
            "structured_override": bool(supplied),
            "open_theme_terms": bool(supplied.get("theme_terms") or supplied_themes),
        },
    }
    return {**body, "intent_sha256": stable_sha256(body)}


def _theme_match(row: Mapping[str, Any], intent: Mapping[str, Any]) -> bool:
    terms = list(intent.get("theme_terms") or ())
    if not terms:  # Backward compatibility for previously materialized intents.
        terms = [
            token
            for theme in intent.get("themes") or ()
            for token in _CATALOG_THEME_ALIASES.get(str(theme), (str(theme),))
        ]
    if not terms:
        return True
    haystack = " ".join(str(row.get(key) or "").lower() for key in ("name", "sector", "industry"))
    return any(str(token).lower() in haystack for token in terms)


def _fund_style_match(row: Mapping[str, Any], intent: Mapping[str, Any]) -> bool:
    terms = list(intent.get("styles") or [])
    capitalization = str(intent.get("capitalization") or "")
    if capitalization:
        terms.append(capitalization)
    if not terms:
        return True
    name = str(row.get("name") or "").lower().replace("-", " ")
    return all(term.replace("_", " ") in name for term in terms)


def compile_market_scout(
    catalog: Mapping[str, Any],
    intent: Mapping[str, Any],
    *,
    completed_at: str | None = None,
) -> dict[str, Any]:
    """Evaluate every catalog member and return a bounded enrichment queue."""
    if catalog.get("schema") != CATALOG_SCHEMA:
        raise ValueError(f"catalog schema must be {CATALOG_SCHEMA}")
    if intent.get("schema") != INTENT_SCHEMA:
        raise ValueError(f"intent schema must be {INTENT_SCHEMA}")
    allowed_kinds = set(intent.get("entity_kinds") or ())
    direct = set(intent.get("direct_symbols") or ())
    countries = set(intent.get("countries") or ())
    rejected: Counter[str] = Counter()
    selected: list[dict[str, Any]] = []
    for row in catalog.get("securities") or ():
        if not isinstance(row, Mapping):
            rejected["invalid_catalog_row"] += 1
            continue
        if row.get("entity_kind") not in allowed_kinds:
            rejected["entity_kind"] += 1
            continue
        if direct and row.get("symbol") not in direct:
            rejected["direct_symbol"] += 1
            continue
        if row.get("entity_kind") == "public_equity" and row.get("security_kind") != "common_equity":
            rejected["security_kind"] += 1
            continue
        if (
            countries
            and row.get("entity_kind") == "public_equity"
            and row.get("country") not in countries
        ):
            rejected["country"] += 1
            continue
        if not _theme_match(row, intent):
            rejected["theme"] += 1
            continue
        if row.get("entity_kind") == "public_equity":
            market_cap = row.get("market_cap")
            minimum = intent.get("market_cap_min")
            maximum = intent.get("market_cap_max")
            if minimum is not None and (market_cap is None or float(market_cap) < float(minimum)):
                rejected["market_cap"] += 1
                continue
            if maximum is not None and (market_cap is None or float(market_cap) >= float(maximum)):
                rejected["market_cap"] += 1
                continue
        elif not _fund_style_match(row, intent):
            rejected["fund_name_style"] += 1
            continue
        selected.append({
            **dict(row),
            "catalog_status": "eligible_for_enrichment",
            "requested_measurements": list(intent.get("ranking_objectives") or ()),
            "next_stage": (
                "sec_fundamentals_valuation_and_strategy"
                if row.get("entity_kind") == "public_equity"
                else "factor_holdings_and_aggregate_valuation"
            ),
        })
    selected.sort(key=lambda row: (
        row["entity_kind"] != "public_equity",
        -(float(row.get("market_cap")) if row.get("market_cap") is not None else -1.0),
        str(row["symbol"]),
    ))
    maximum_results = int(intent.get("max_results") or 50)
    queue = selected[:maximum_results]
    completed = canonical_timestamp(completed_at or _utc_now(), "scout completed_at")
    body: dict[str, Any] = {
        "schema": SCOUT_SCHEMA,
        "completed_at": completed,
        "catalog_sha256": catalog["catalog_sha256"],
        "catalog_retrieved_at": catalog["retrieved_at"],
        "intent": dict(intent),
        "authority": "research_queue_only",
        "population": {
            "catalog_count": int(catalog["security_count"]),
            "evaluated_count": len(catalog.get("securities") or ()),
            "eligible_count": len(selected),
            "returned_count": len(queue),
            "truncated": len(queue) < len(selected),
            "rejected_by_reason": dict(sorted(rejected.items())),
        },
        "candidates": queue,
        "frontier_closure": {
            "scope_closed": True,
            "scope": "catalog identity and declared coarse filters at one retrieval epoch",
            "represented_count": len(selected),
            "excluded_claims": [
                "fundamental value", "earnings quality", "factor alpha",
                "company strategic advantage", "fund holdings geography",
                "portfolio fit",
            ],
        },
        "next_activation": "enrich_shortlist",
    }
    return {**body, "scout_sha256": stable_sha256(body)}


def run_market_scout(
    workspace: str | Path,
    query: str,
    *,
    max_results: int = 50,
    refresh_catalog: bool = False,
    write_latest: bool = True,
    intent_overrides: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(workspace).expanduser().resolve()
    catalog_path = root / "universe" / "catalog-latest.json"
    if refresh_catalog or not catalog_path.is_file():
        catalog = refresh_public_market_catalog(root)
    else:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    intent = compile_research_intent(
        query, max_results=max_results, overrides=intent_overrides,
    )
    result = compile_market_scout(catalog, intent)
    run_id = f"scout-{result['completed_at'].translate(str.maketrans('', '', '-:TZ'))}-{result['scout_sha256'][:8]}"
    result = {**result, "run_id": run_id}
    run_path = root / "research_jobs" / "runs" / f"{run_id}.json"
    _atomic_json(run_path, result)
    if write_latest:
        _atomic_json(root / "research_jobs" / "latest.json", result)
    return {
        **result,
        "run_path": run_path.relative_to(root).as_posix(),
        "catalog_path": "universe/catalog-latest.json",
    }


__all__ = [
    "CATALOG_SCHEMA",
    "INTENT_SCHEMA",
    "NASDAQ_ETF_SCREENER_URL",
    "NASDAQ_STOCK_SCREENER_URL",
    "SCOUT_SCHEMA",
    "compile_market_scout",
    "compile_research_intent",
    "refresh_public_market_catalog",
    "run_market_scout",
]
