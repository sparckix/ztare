"""Point-in-time durable-earnings analysis over public company facts.

The report separates measured accounting persistence from unobserved business
quality.  Filing dates remain the availability boundary, revisions replace
earlier values only for later analysis epochs, and every summary retains the
observation identities that produced it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from statistics import median, pstdev
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import MetricObservation, canonical_timestamp, require_text, timestamp_key
from .observation_index import load_observation_rows


COMPANY_QUALITY_SCHEMA = "jaggedthoughts-company-quality-report-v1"
_FLOW_METRICS = (
    "revenue_fy",
    "operating_cash_flow_fy",
    "capital_expenditure_fy",
    "net_income_fy",
)


class InsufficientCompanyHistoryError(ValueError):
    """The source epoch cannot support the minimum aligned quality history."""


@dataclass(frozen=True, slots=True)
class FundamentalYear:
    observed_at: str
    revenue: float
    operating_cash_flow: float
    capital_expenditure: float
    net_income: float
    assets: float | None
    observation_ids: tuple[str, ...]
    source_refs: tuple[str, ...]
    available_at: str

    @property
    def owner_earnings(self) -> float:
        return self.operating_cash_flow - self.capital_expenditure

    def to_dict(self) -> dict[str, Any]:
        owner_earnings = self.owner_earnings
        return {
            "observed_at": self.observed_at,
            "revenue": self.revenue,
            "operating_cash_flow": self.operating_cash_flow,
            "capital_expenditure": self.capital_expenditure,
            "net_income": self.net_income,
            "assets": self.assets,
            "owner_earnings": owner_earnings,
            "owner_earnings_margin": owner_earnings / self.revenue if self.revenue else None,
            "cash_conversion": self.operating_cash_flow / self.net_income if self.net_income else None,
            "observation_ids": list(self.observation_ids),
            "source_refs": list(self.source_refs),
            "available_at": self.available_at,
        }


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return min(high, max(low, value))


def _finite_values(values: Iterable[float | None]) -> list[float]:
    return [float(value) for value in values if value is not None]


def load_company_fundamentals(
    observations_path: str | Path, *, entity_id: str, as_of: str
) -> tuple[MetricObservation, ...]:
    """Load the latest known revision of each company fact at an analysis epoch."""
    entity = require_text(entity_id, "company quality entity_id").upper()
    return load_company_fundamentals_index(
        observations_path, as_of=as_of, entity_ids=(entity,),
    ).get(entity, ())


def load_company_fundamentals_index(
    observations_path: str | Path, *, as_of: str,
    entity_ids: Iterable[str] | None = None,
) -> dict[str, tuple[MetricObservation, ...]]:
    """Read one observation epoch once and index latest revisions by company."""
    entities = (
        {require_text(entity_id, "company quality entity_id").upper() for entity_id in entity_ids}
        if entity_ids is not None else None
    )
    cutoff = timestamp_key(canonical_timestamp(as_of, "company quality as_of"))
    latest: dict[tuple[str, str, str], MetricObservation] = {}
    for raw in load_observation_rows(
        observations_path, as_of=cutoff.isoformat().replace("+00:00", "Z"),
        entity_ids=entities, effective_per_observed=True,
    ):
        row = MetricObservation(
            observation_id=str(raw["observation_id"]), entity_id=str(raw["entity_id"]),
            metric_id=str(raw["metric_id"]), value=float(raw["value"]),
            unit=str(raw["unit"]), observed_at=str(raw["observed_at"]),
            available_at=str(raw["available_at"]), source_ref=str(raw["source_ref"]),
        )
        latest[(row.entity_id, row.metric_id, row.observed_at)] = row
    grouped: dict[str, list[MetricObservation]] = {}
    for (entity, _metric, _observed), row in latest.items():
        grouped.setdefault(entity, []).append(row)
    return {
        entity: tuple(sorted(rows, key=lambda row: (
            row.observed_at, row.metric_id, row.available_at, row.observation_id,
        )))
        for entity, rows in sorted(grouped.items())
    }


def select_company_fundamentals(
    observations: Iterable[MetricObservation], *, entity_id: str, as_of: str,
) -> tuple[MetricObservation, ...]:
    """Select one company's latest-known fact revisions from an in-memory store."""
    entity = require_text(entity_id, "company quality entity_id").upper()
    cutoff = timestamp_key(canonical_timestamp(as_of, "company quality as_of"))
    latest: dict[tuple[str, str], MetricObservation] = {}
    for row in observations:
        if row.entity_id.upper() != entity or timestamp_key(row.available_at) > cutoff:
            continue
        key = (row.metric_id, row.observed_at)
        current = latest.get(key)
        if current is None or (row.available_at, row.observation_id) > (
            current.available_at, current.observation_id,
        ):
            latest[key] = row
    return tuple(sorted(latest.values(), key=lambda row: (
        row.observed_at, row.metric_id, row.available_at, row.observation_id,
    )))


def _annual_rows(points: Iterable[MetricObservation]) -> tuple[FundamentalYear, ...]:
    by_key = {(row.metric_id, row.observed_at): row for row in points}
    dates = sorted(set.intersection(*(
        {observed for metric, observed in by_key if metric == metric_id}
        for metric_id in _FLOW_METRICS
    )))
    rows: list[FundamentalYear] = []
    for observed_at in dates:
        facts = [by_key[(metric_id, observed_at)] for metric_id in _FLOW_METRICS]
        assets = by_key.get(("assets", observed_at))
        evidence = [*facts, *([assets] if assets else [])]
        rows.append(FundamentalYear(
            observed_at=observed_at,
            revenue=facts[0].value,
            operating_cash_flow=facts[1].value,
            capital_expenditure=facts[2].value,
            net_income=facts[3].value,
            assets=assets.value if assets else None,
            observation_ids=tuple(sorted(row.observation_id for row in evidence)),
            source_refs=tuple(sorted({row.source_ref for row in evidence})),
            available_at=max(row.available_at for row in evidence),
        ))
    return tuple(rows)


def _latest_metric(points: Iterable[MetricObservation], metric_id: str) -> MetricObservation | None:
    candidates = [row for row in points if row.metric_id == metric_id]
    return max(candidates, key=lambda row: (row.observed_at, row.available_at, row.observation_id), default=None)


def _compile_company_quality_report(
    *,
    entity_id: str,
    as_of: str,
    points: Iterable[MetricObservation],
    min_years: int = 3,
) -> dict[str, Any]:
    """Compile accounting durability from already selected company facts."""
    entity = require_text(entity_id, "company quality entity_id").upper()
    epoch = canonical_timestamp(as_of, "company quality as_of")
    if min_years < 2:
        raise ValueError("company quality min_years must be at least two")
    selected = tuple(points)
    years = _annual_rows(selected)
    if len(years) < 2:
        raise InsufficientCompanyHistoryError(
            f"{entity} needs at least two aligned annual fundamental periods"
        )

    revenues = [row.revenue for row in years]
    revenue_growth = [
        revenues[index] / revenues[index - 1] - 1
        for index in range(1, len(revenues)) if revenues[index - 1] > 0
    ]
    elapsed_years = max(1.0, (timestamp_key(years[-1].observed_at) - timestamp_key(years[0].observed_at)).days / 365.25)
    revenue_cagr = (revenues[-1] / revenues[0]) ** (1.0 / elapsed_years) - 1 if revenues[0] > 0 and revenues[-1] > 0 else None
    owner_earnings = [row.owner_earnings for row in years]
    owner_margins = [row.owner_earnings / row.revenue if row.revenue else None for row in years]
    cash_conversion = [row.operating_cash_flow / row.net_income if row.net_income else None for row in years]
    accrual_ratios: list[float] = []
    for index, row in enumerate(years):
        if row.assets is None or row.assets <= 0:
            continue
        prior_assets = years[index - 1].assets if index > 0 else None
        denominator = (row.assets + prior_assets) / 2 if prior_assets and prior_assets > 0 else row.assets
        accrual_ratios.append((row.net_income - row.operating_cash_flow) / denominator)

    positive_growth_share = sum(value > 0 for value in revenue_growth) / len(revenue_growth) if revenue_growth else 0.0
    growth_volatility = pstdev(revenue_growth) if len(revenue_growth) > 1 else 0.0
    positive_owner_earnings_share = sum(value > 0 for value in owner_earnings) / len(owner_earnings)
    conversion_values = _finite_values(cash_conversion)
    margin_values = _finite_values(owner_margins)
    median_conversion = median(conversion_values) if conversion_values else None
    median_margin = median(margin_values) if margin_values else None
    median_accrual = median(accrual_ratios) if accrual_ratios else None
    owner_mean_abs = sum(abs(value) for value in owner_earnings) / len(owner_earnings)
    owner_variability = pstdev(owner_earnings) / owner_mean_abs if len(owner_earnings) > 1 and owner_mean_abs else None

    cash = _latest_metric(selected, "cash")
    debt_current = _latest_metric(selected, "debt_current")
    debt_noncurrent = _latest_metric(selected, "debt_noncurrent")
    total_debt = sum(row.value for row in (debt_current, debt_noncurrent) if row is not None)
    latest_owner = owner_earnings[-1]
    net_debt = total_debt - (cash.value if cash else 0.0)
    net_debt_to_owner_earnings = net_debt / latest_owner if latest_owner > 0 else None

    revenue_score = (
        0.35 * _clamp(((revenue_cagr or -0.05) + 0.05) / 0.15)
        + 0.35 * positive_growth_share
        + 0.30 * (1.0 - _clamp(growth_volatility / 0.20))
    )
    earnings_score = (
        0.35 * positive_owner_earnings_share
        + 0.25 * _clamp(((median_conversion or 0.0) - 0.50) / 0.75)
        + 0.20 * _clamp((0.10 - (median_accrual if median_accrual is not None else 0.10)) / 0.20)
        + 0.20 * (1.0 - _clamp((owner_variability if owner_variability is not None else 1.0) / 1.50))
    )
    balance_score = (
        _clamp((6.0 - net_debt_to_owner_earnings) / 6.0)
        if net_debt_to_owner_earnings is not None else 0.0
    )
    composite = 0.40 * revenue_score + 0.40 * earnings_score + 0.20 * balance_score
    coverage = {
        "aligned_annual_periods": len(years),
        "required_annual_periods": min_years,
        "status": "sufficient_for_screen" if len(years) >= min_years else "partial_history",
        "accrual_periods": len(accrual_ratios),
        "current_cash_available": cash is not None,
        "current_debt_available": debt_current is not None or debt_noncurrent is not None,
    }
    selected_ids = sorted({observation_id for year in years for observation_id in year.observation_ids})
    balance_points = [row for row in (cash, debt_current, debt_noncurrent) if row is not None]
    selected_ids.extend(row.observation_id for row in balance_points)
    source_refs = sorted({row.source_ref for row in selected if row.observation_id in set(selected_ids)})
    available_at = max([year.available_at for year in years] + [row.available_at for row in balance_points])
    body: dict[str, Any] = {
        "schema": COMPANY_QUALITY_SCHEMA,
        "report_id": f"{entity}:durable-earnings:{epoch}",
        "entity_id": entity,
        "as_of": epoch,
        "available_at": available_at,
        "coverage": coverage,
        "formulas": {
            "owner_earnings": "operating_cash_flow_fy - capital_expenditure_fy",
            "cash_conversion": "operating_cash_flow_fy / net_income_fy",
            "accrual_ratio": "(net_income_fy - operating_cash_flow_fy) / average_assets",
            "net_debt_to_owner_earnings": "(debt_current + debt_noncurrent - cash) / latest_owner_earnings",
        },
        "history": [row.to_dict() for row in years],
        "metrics": {
            "revenue_cagr": revenue_cagr,
            "positive_revenue_growth_share": positive_growth_share,
            "revenue_growth_volatility": growth_volatility,
            "positive_owner_earnings_share": positive_owner_earnings_share,
            "median_owner_earnings_margin": median_margin,
            "median_cash_conversion": median_conversion,
            "median_accrual_ratio": median_accrual,
            "owner_earnings_variability": owner_variability,
            "latest_net_debt": net_debt,
            "net_debt_to_owner_earnings": net_debt_to_owner_earnings,
        },
        "scores": {
            "revenue_durability": revenue_score,
            "earnings_quality": earnings_score,
            "balance_sheet_resilience": balance_score,
            "durable_earnings_power": composite,
        },
        "observation_ids": sorted(set(selected_ids)),
        "source_refs": source_refs,
        "residuals": [
            "Accounting persistence does not establish competitive advantage or management quality.",
            "Revenue concentration, segment economics, pricing power, customer retention, and reinvestment returns need additional sourced evidence.",
            "Owner earnings is an unadjusted cash-flow proxy; working-capital cycles, stock compensation, acquisitions, and maintenance versus growth capital spending remain review items.",
        ],
        "use_boundary": "Eligible for opportunity triage and underwriting prompts; insufficient by itself for a valuation or capital decision.",
    }
    return {**body, "quality_report_sha256": stable_sha256(body)}


def compile_company_quality_report(
    *, entity_id: str, observations_path: str | Path, as_of: str, min_years: int = 3,
) -> dict[str, Any]:
    """Compile accounting durability, earnings quality, and balance-sheet resilience."""
    points = load_company_fundamentals(observations_path, entity_id=entity_id, as_of=as_of)
    return _compile_company_quality_report(
        entity_id=entity_id, as_of=as_of, points=points, min_years=min_years,
    )


def compile_company_quality_from_observations(
    *, entity_id: str, observations: Iterable[MetricObservation], as_of: str,
    min_years: int = 3,
) -> dict[str, Any]:
    """Compile the same report without rescanning a shared observation file."""
    points = select_company_fundamentals(observations, entity_id=entity_id, as_of=as_of)
    return _compile_company_quality_report(
        entity_id=entity_id, as_of=as_of, points=points, min_years=min_years,
    )


def compile_company_quality_history(
    *, entity_id: str, observations_path: str | Path, as_of: str, min_years: int = 3,
) -> tuple[dict[str, Any], ...]:
    """Compile the first point-in-time quality report for each fiscal-year head."""
    return compile_company_quality_histories(
        entity_ids=(entity_id,), observations_path=observations_path,
        as_of=as_of, min_years=min_years,
    ).get(require_text(entity_id, "company quality entity_id").upper(), ())


def _company_quality_history_from_rows(
    entity: str, rows: Iterable[MetricObservation], *, min_years: int,
) -> tuple[dict[str, Any], ...]:
    selected = tuple(rows)
    epochs = sorted({row.available_at for row in selected if row.metric_id in _FLOW_METRICS})
    first_by_fiscal_head: dict[str, dict[str, Any]] = {}
    for epoch in epochs:
        try:
            report = compile_company_quality_from_observations(
                entity_id=entity, observations=selected, as_of=epoch, min_years=min_years,
            )
        except InsufficientCompanyHistoryError:
            continue
        fiscal_head = str(report["history"][-1]["observed_at"])
        first_by_fiscal_head.setdefault(fiscal_head, report)
    return tuple(first_by_fiscal_head[key] for key in sorted(first_by_fiscal_head))


def compile_company_quality_histories(
    *, entity_ids: Iterable[str], observations_path: str | Path,
    as_of: str, min_years: int = 3,
) -> dict[str, tuple[dict[str, Any], ...]]:
    """Compile point-in-time histories from one bounded observation query."""
    path = Path(observations_path).expanduser().resolve()
    entities = {
        require_text(entity_id, "company quality entity_id").upper()
        for entity_id in entity_ids
    }
    if not entities:
        return {}
    epoch = canonical_timestamp(as_of, "company quality history as_of")
    grouped: dict[str, list[MetricObservation]] = {entity: [] for entity in entities}
    for raw in load_observation_rows(
        path, as_of=epoch, entity_ids=entities,
        metric_ids=(*_FLOW_METRICS, "assets", "cash", "debt_current", "debt_noncurrent"),
    ):
        row = MetricObservation(
            observation_id=str(raw["observation_id"]), entity_id=str(raw["entity_id"]),
            metric_id=str(raw["metric_id"]), value=float(raw["value"]), unit=str(raw["unit"]),
            observed_at=str(raw["observed_at"]), available_at=str(raw["available_at"]),
            source_ref=str(raw["source_ref"]),
        )
        grouped[row.entity_id].append(row)
    return {
        entity: _company_quality_history_from_rows(entity, grouped[entity], min_years=min_years)
        for entity in sorted(entities)
    }


def compile_company_quality_histories_from_observations(
    *, entity_ids: Iterable[str], observations: Iterable[MetricObservation],
    as_of: str, min_years: int = 3,
) -> dict[str, tuple[dict[str, Any], ...]]:
    """Compile filing-time histories from an already bounded evidence packet."""
    entities = {
        require_text(entity_id, "company quality entity_id").upper()
        for entity_id in entity_ids
    }
    cutoff = timestamp_key(canonical_timestamp(as_of, "company quality history as_of"))
    grouped: dict[str, list[MetricObservation]] = {entity: [] for entity in entities}
    for row in observations:
        if row.entity_id in grouped and timestamp_key(row.available_at) <= cutoff:
            grouped[row.entity_id].append(row)
    return {
        entity: _company_quality_history_from_rows(entity, grouped[entity], min_years=min_years)
        for entity in sorted(entities)
    }


__all__ = [
    "COMPANY_QUALITY_SCHEMA",
    "FundamentalYear",
    "compile_company_quality_from_observations",
    "compile_company_quality_histories",
    "compile_company_quality_histories_from_observations",
    "compile_company_quality_history",
    "compile_company_quality_report",
    "load_company_fundamentals",
    "select_company_fundamentals",
]
