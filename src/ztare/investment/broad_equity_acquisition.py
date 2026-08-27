"""Deterministic, diversity-bounded public-equity acquisition queue."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import math
from typing import Any, Iterable, Mapping, Sequence

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp
from .research_jobs import default_enrichment_policy
from .universe_breadth import equity_size_band
from .universe_catalog import CATALOG_SCHEMA, INTENT_SCHEMA


POLICY_SCHEMA = "jaggedthoughts-broad-equity-acquisition-policy-v1"
RUN_SCHEMA = "jaggedthoughts-broad-equity-acquisition-run-v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def default_broad_equity_policy() -> dict[str, Any]:
    """Return a broad queue policy compatible with the enrichment score contract."""
    enrichment = default_enrichment_policy()
    return {
        "schema": POLICY_SCHEMA,
        "max_selected": 50,
        "max_frontier_candidates": 500,
        "max_per_sector": 4,
        "max_per_country": 8,
        "max_per_size_sector_cell": 1,
        "unknown_cell_quota": 2,
        "score_weights": dict(enrichment["score_weights"]),
        "incremental_source_calls": enrichment["cost_model"]["public_equity"]["incremental_source_calls"],
        "authority": "research_queue_only",
    }


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _identity(row: Mapping[str, Any]) -> str:
    symbol = str(row.get("symbol") or row.get("entity_id") or "").strip().upper()
    security_id = str(row.get("security_id") or "")
    if not symbol and ":" in security_id:
        symbol = security_id.rsplit(":", 1)[-1].upper()
    return symbol


def _normalized_ids(values: Iterable[Any]) -> set[str]:
    normalized = set()
    for value in values:
        text = str(value or "").strip()
        identity = _identity({"security_id": text}) or text.upper()
        if identity:
            normalized.add(identity)
    return normalized


def _classification(row: Mapping[str, Any]) -> tuple[str, str, str, str]:
    country = str(row.get("country") or "").strip() or "unknown"
    sector = str(row.get("sector") or "").strip() or "unknown"
    size = equity_size_band(row.get("market_cap"))
    return size, country, sector, f"{size}|{sector}"


def _profile(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    sizes, countries, sectors, cells = (
        zip(*(_classification(row) for row in rows)) if rows else ((), (), (), ())
    )
    return {
        "count": len(rows),
        "size_counts": dict(sorted(Counter(sizes).items())),
        "country_counts": dict(sorted(Counter(countries).items())),
        "sector_counts": dict(sorted(Counter(sectors).items())),
        "size_sector_cell_counts": dict(sorted(Counter(cells).items())),
        "known_size_count": sum(value != "unknown" for value in sizes),
        "known_country_count": sum(value != "unknown" for value in countries),
        "known_sector_count": sum(value != "unknown" for value in sectors),
        "known_cell_count": sum(
            size != "unknown" and country != "unknown" and sector != "unknown"
            for size, country, sector in zip(sizes, countries, sectors)
        ),
        "unknown_cell_count": sum(
            size == "unknown" or country == "unknown" or sector == "unknown"
            for size, country, sector in zip(sizes, countries, sectors)
        ),
    }


def _identity_coverage(row: Mapping[str, Any]) -> float:
    fields = (
        "symbol", "name", "last_price", "volume", "market_cap", "country", "sector", "industry",
    )
    return sum(row.get(field) not in {None, ""} for field in fields) / len(fields)


def _validated_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
    if policy.get("schema") != POLICY_SCHEMA:
        raise ValueError(f"broad equity policy schema must be {POLICY_SCHEMA}")
    integers = {}
    for key in (
        "max_selected", "max_per_sector", "max_per_size_sector_cell",
        "unknown_cell_quota",
    ):
        value = policy.get(key, -1)
        if isinstance(value, bool):
            raise ValueError(f"{key} must be an integer")
        integers[key] = int(value)
    frontier_limit = policy.get(
        "max_frontier_candidates", integers["max_selected"] * 10,
    )
    if isinstance(frontier_limit, bool):
        raise ValueError("max_frontier_candidates must be an integer")
    integers["max_frontier_candidates"] = int(frontier_limit)
    if integers["max_selected"] < 1 or integers["max_per_sector"] < 1 or integers["max_per_size_sector_cell"] < 1:
        raise ValueError("broad equity selection and known-cell caps must be positive")
    if not integers["max_selected"] <= integers["max_frontier_candidates"] <= 5_000:
        raise ValueError("max_frontier_candidates must be between max_selected and 5000")
    country_cap = policy.get("max_per_country", integers["max_selected"])
    if isinstance(country_cap, bool) or int(country_cap) < 1:
        raise ValueError("max_per_country must be a positive integer")
    integers["max_per_country"] = int(country_cap)
    if not 0 <= integers["unknown_cell_quota"] <= integers["max_selected"]:
        raise ValueError("unknown_cell_quota must be between zero and max_selected")
    weights = {key: _number(value) for key, value in (policy.get("score_weights") or {}).items()}
    required = {"measurement_value_proxy", "request_specificity", "identity_coverage", "liquidity", "source_efficiency"}
    if set(weights) != required or any(value is None or value < 0 for value in weights.values()):
        raise ValueError("score_weights must contain the nonnegative enrichment acquisition coordinates")
    if sum(value for value in weights.values() if value is not None) <= 0:
        raise ValueError("score_weights must have positive mass")
    calls = int(policy.get("incremental_source_calls", 0))
    if calls < 1:
        raise ValueError("incremental_source_calls must be positive")
    return {**integers, "weights": weights, "incremental_source_calls": calls}


def _priority_overrides(rows: Iterable[Mapping[str, Any]]) -> dict[str, tuple[float, str]]:
    overrides: dict[str, tuple[float, str]] = {}
    for row in rows:
        identity = _identity(row)
        base = _number(row.get("base_priority"))
        acquisition = _number(row.get("acquisition_priority"))
        coordinate = base if base is not None else acquisition
        if not identity or coordinate is None:
            continue
        source = "existing_base_priority" if base is not None else "existing_acquisition_priority"
        if identity not in overrides or coordinate > overrides[identity][0]:
            overrides[identity] = (coordinate, source)
    return overrides


def _computed_priority(
    row: Mapping[str, Any], *, max_log_volume: float,
    weights: Mapping[str, float], incremental_source_calls: int,
) -> tuple[float, dict[str, float]]:
    components = {
        "measurement_value_proxy": 0.0,
        "request_specificity": 0.0,
        "identity_coverage": _identity_coverage(row),
        "liquidity": math.log1p(max(0.0, _number(row.get("volume")) or 0.0)) / max_log_volume,
        "source_efficiency": 1.0 / incremental_source_calls,
    }
    total = sum(weights.values())
    return sum(weights[key] * value for key, value in components.items()) / total, components


def _pick(
    rows: Sequence[dict[str, Any]], *, limit: int,
    country_cap: int, sector_cap: int, cell_cap: int,
    initial: Sequence[Mapping[str, Any]] = (),
) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    selected: list[dict[str, Any]] = []
    countries = Counter(_classification(row)[1] for row in initial)
    sectors = Counter(_classification(row)[2] for row in initial)
    cells = Counter(_classification(row)[3] for row in initial)
    for row in rows:
        _, country, sector, cell = _classification(row)
        if (
            countries[country] >= country_cap
            or sectors[sector] >= sector_cap
            or cells[cell] >= cell_cap
        ):
            continue
        selected.append(row)
        countries[country] += 1
        sectors[sector] += 1
        cells[cell] += 1
        if len(selected) == limit:
            break
    return selected


def compile_broad_equity_acquisition(
    *,
    catalog: Mapping[str, Any],
    policy: Mapping[str, Any],
    priority_candidates: Iterable[Mapping[str, Any]] = (),
    enrolled_security_ids: Iterable[Any] = (),
    current_security_ids: Iterable[Any] = (),
    completed_at: str | None = None,
) -> dict[str, Any]:
    """Select a broad, source-supported research queue with no capital authority."""
    if catalog.get("schema") != CATALOG_SCHEMA:
        raise ValueError(f"catalog schema must be {CATALOG_SCHEMA}")
    parsed = _validated_policy(policy)
    completed = canonical_timestamp(completed_at or _utc_now(), "broad acquisition completed_at")
    eligible_rows = [dict(row) for row in catalog.get("securities") or ()
                     if isinstance(row, Mapping)
                     and row.get("entity_kind") == "public_equity"
                     and row.get("security_kind") == "common_equity"
                     and _identity(row)]

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in eligible_rows:
        grouped.setdefault(_identity(row), []).append(row)
    distinct = [sorted(rows, key=stable_sha256)[0] for _, rows in sorted(grouped.items())]
    enrolled = _normalized_ids(enrolled_security_ids)
    current = _normalized_ids(current_security_ids)
    selectable = [row for row in distinct if _identity(row) not in enrolled | current]

    max_log_volume = max((math.log1p(max(0.0, _number(row.get("volume")) or 0.0))
                          for row in distinct), default=1.0) or 1.0
    overrides = _priority_overrides([*priority_candidates, *eligible_rows])
    scored: list[dict[str, Any]] = []
    for row in selectable:
        identity = _identity(row)
        computed, components = _computed_priority(
            row, max_log_volume=max_log_volume, weights=parsed["weights"],
            incremental_source_calls=parsed["incremental_source_calls"],
        )
        priority, source = overrides.get(identity, (computed, "catalog_supported_components"))
        size, country, sector, cell = _classification(row)
        scored.append({
            **row,
            "size": size,
            "country": country,
            "sector": sector,
            "size_sector_cell": cell,
            "score_components": {key: round(value, 8) for key, value in components.items()},
            "base_priority": round(priority, 8),
            "acquisition_priority": round(priority, 8),
            "priority_coordinate_source": source,
            "requested_measurements": ["identity_coverage", "liquidity", "source_efficiency"],
            "catalog_status": "eligible_for_enrichment",
            "next_stage": "sec_fundamentals_valuation_and_strategy",
        })
    scored.sort(key=lambda row: (-row["acquisition_priority"], str(row["security_id"])))
    unknown = [
        row for row in scored
        if "unknown" in {row["size"], row["country"], row["sector"]}
    ]
    known = [
        row for row in scored
        if "unknown" not in {row["size"], row["country"], row["sector"]}
    ]
    known_selected = _pick(
        known, limit=parsed["max_selected"] - parsed["unknown_cell_quota"],
        country_cap=parsed["max_per_country"], sector_cap=parsed["max_per_sector"],
        cell_cap=parsed["max_per_size_sector_cell"],
    )
    unknown_selected = _pick(
        unknown, limit=parsed["unknown_cell_quota"],
        country_cap=parsed["max_per_country"], sector_cap=parsed["max_per_sector"],
        cell_cap=parsed["max_per_size_sector_cell"], initial=known_selected,
    )
    selected_ids = {_identity(row) for row in [*known_selected, *unknown_selected]}
    known_fill = _pick(
        [row for row in known if _identity(row) not in selected_ids],
        limit=parsed["max_selected"] - len(known_selected) - len(unknown_selected),
        country_cap=parsed["max_per_country"], sector_cap=parsed["max_per_sector"],
        cell_cap=parsed["max_per_size_sector_cell"],
        initial=[*known_selected, *unknown_selected],
    )
    selected = sorted([*known_selected, *unknown_selected, *known_fill],
                      key=lambda row: (-row["acquisition_priority"], str(row["security_id"])))
    for rank, row in enumerate(selected, 1):
        row["selection_rank"] = rank
        row["selection_status"] = "selected"
        row["selection_reason"] = (
            "explicit_unknown_identity_exploration_slot"
            if row in unknown_selected else "potential_exploitation_with_diversity_caps"
        )
    selected_ids = {_identity(row) for row in selected}
    enrichment_frontier = []
    for rank, row in enumerate(scored[:parsed["max_frontier_candidates"]], 1):
        frontier_row = dict(row)
        initial_rank = frontier_row.pop("selection_rank", None)
        enrichment_frontier.append({
            **frontier_row,
            "frontier_rank": rank,
            "initial_diversity_selection": _identity(row) in selected_ids,
            "initial_diversity_selection_rank": initial_rank,
            "selection_status": "eligible",
            "selection_reason": "eligible_source_feasible_successor_frontier",
        })

    population_profile = _profile(distinct)
    selectable_profile = _profile(selectable)
    selected_profile = _profile(selected)
    selected_known_countries = {row["country"] for row in selected if row["country"] != "unknown"}
    selectable_known_countries = {
        str(row.get("country") or "") for row in selectable if row.get("country")
    }
    selected_known_sectors = {row["sector"] for row in selected if row["sector"] != "unknown"}
    selectable_known_sectors = {str(row.get("sector") or "") for row in selectable if row.get("sector")}
    selected_known_cells = {row["size_sector_cell"] for row in selected
                            if row["size"] != "unknown" and row["sector"] != "unknown"}
    selectable_known_cells = {
        _classification(row)[3] for row in selectable
        if "unknown" not in _classification(row)[:3]
    }
    catalog_sha256 = catalog.get("catalog_sha256") or stable_sha256({
        **dict(catalog),
        "securities": sorted(
            (dict(row) for row in catalog.get("securities") or () if isinstance(row, Mapping)),
            key=stable_sha256,
        ),
    })
    seed = stable_sha256({
        "catalog_sha256": catalog_sha256,
        "policy_sha256": stable_sha256(policy),
        "completed_at": completed,
        "enrolled": sorted(enrolled), "current": sorted(current),
    })
    body = {
        "schema": RUN_SCHEMA,
        "run_id": f"broad-equity-{seed[:20]}",
        "completed_at": completed,
        "authority": "research_queue_only",
        "catalog_sha256": catalog_sha256,
        "policy_sha256": stable_sha256(policy),
        "intent": {
            "schema": INTENT_SCHEMA,
            "intent_sha256": seed,
            "query": "Broad supported-field public-equity acquisition",
            "entity_kinds": ["public_equity"],
            "capitalization": None, "styles": [], "countries": [],
            "ranking_objectives": ["identity_coverage", "liquidity", "source_efficiency"],
            "max_results": parsed["max_selected"],
        },
        "population": {
            "catalog_count": len(catalog.get("securities") or ()),
            "eligible_equity_row_count": len(eligible_rows),
            "distinct_eligible_equity_count": len(distinct),
            "duplicate_row_count": len(eligible_rows) - len(distinct),
            "enrolled_excluded_count": sum(_identity(row) in enrolled for row in distinct),
            "current_excluded_count": sum(_identity(row) in current for row in distinct),
            "exclusion_overlap_count": sum(_identity(row) in enrolled & current for row in distinct),
            "distinct_excluded_count": len(distinct) - len(selectable),
            "selectable_count": len(selectable),
            "selected_count": len(selected),
            "enrichment_frontier_count": len(enrichment_frontier),
        },
        "selected_security_ids": [str(row["security_id"]) for row in selected],
        "enrichment_frontier_security_ids": [
            str(row["security_id"]) for row in enrichment_frontier
        ],
        "coverage": {
            "eligible_population": population_profile,
            "selectable_population": selectable_profile,
            "selected": selected_profile,
            "selected_known_country_coverage_ratio": (
                len(selected_known_countries) / len(selectable_known_countries)
                if selectable_known_countries else 0.0
            ),
            "selected_known_sector_coverage_ratio": (
                len(selected_known_sectors) / len(selectable_known_sectors)
                if selectable_known_sectors else 0.0
            ),
            "selected_known_cell_coverage_ratio": (
                len(selected_known_cells) / len(selectable_known_cells)
                if selectable_known_cells else 0.0
            ),
        },
        "classification_support": {
            "size": {"source_field": "market_cap", "known_count": population_profile["known_size_count"],
                     "unknown_count": len(distinct) - population_profile["known_size_count"]},
            "geography": {
                "source_field": "country",
                "known_count": population_profile["known_country_count"],
                "unknown_count": len(distinct) - population_profile["known_country_count"],
            },
            "sector": {"source_field": "sector", "known_count": population_profile["known_sector_count"],
                       "unknown_count": len(distinct) - population_profile["known_sector_count"]},
            "style": {"source_field": None, "known_count": 0, "unknown_count": len(distinct)},
            "factor_exposure": {"source_field": None, "known_count": 0, "unknown_count": len(distinct)},
            "industry": {"source_field": "industry",
                         "known_count": sum(bool(str(row.get("industry") or "").strip()) for row in distinct),
                         "unknown_count": sum(not bool(str(row.get("industry") or "").strip()) for row in distinct),
                         "used_for_selection": False},
        },
        "priority_coverage": {
            "selectable": dict(sorted(Counter(row["priority_coordinate_source"] for row in scored).items())),
            "selected": dict(sorted(Counter(row["priority_coordinate_source"] for row in selected).items())),
        },
        "selection_contract": {
            "max_selected": parsed["max_selected"],
            "max_frontier_candidates": parsed["max_frontier_candidates"],
            "max_per_country": parsed["max_per_country"],
            "max_per_sector": parsed["max_per_sector"],
            "max_per_size_sector_cell": parsed["max_per_size_sector_cell"],
            "unknown_cell_quota": parsed["unknown_cell_quota"],
            "selection_order": "potential_exploitation_then_explicit_unknown_identity_exploration",
            "priority": "existing acquisition/base priority, else the existing supported acquisition components",
            "is_expected_return": False,
            "tie_break": ["acquisition_priority_desc", "security_id_asc"],
            "frontier_purpose": (
                "bounded successor supply for enrichment-time enrollment, cooldown, "
                "source-capability, diversity, and budget gates"
            ),
        },
        "candidates": selected,
        "enrichment_frontier": enrichment_frontier,
        "next_activation": "compile_enrichment_cycle(scout_runs=[this_run], ...)",
    }
    return {**body, "run_sha256": stable_sha256(body)}


__all__ = ["compile_broad_equity_acquisition", "default_broad_equity_policy"]
