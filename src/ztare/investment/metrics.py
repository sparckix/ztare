"""Canonical investment metrics over the existing signal and valuation grammars."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import MetricObservation, require_text
from .signals import SIGNAL_OPERATOR_CONTRACT, SignalArgument, SignalDefinition, derive_signals_partial
from .valuation import valuation_grammar_contract


METRIC_UNIVERSE_SCHEMA = "jaggedthoughts-investment-metric-universe-v1"
METRIC_ALIASES = {"portfolio_holding_hhi": "portfolio_holdings_hhi"}


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    metric_id: str
    semantic_type: str
    unit: str
    temporal_type: str
    producer: str
    entity_kinds: tuple[str, ...]
    description: str

    def __post_init__(self) -> None:
        for name in ("metric_id", "semantic_type", "unit", "temporal_type", "producer", "description"):
            object.__setattr__(self, name, require_text(getattr(self, name), f"metric.{name}"))
        kinds = tuple(sorted({require_text(row, "metric entity kind") for row in self.entity_kinds}))
        if not kinds:
            raise ValueError("metric entity_kinds must be nonempty")
        object.__setattr__(self, "entity_kinds", kinds)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id, "semantic_type": self.semantic_type,
            "unit": self.unit, "temporal_type": self.temporal_type,
            "producer": self.producer, "entity_kinds": list(self.entity_kinds),
            "description": self.description,
        }


def _m(
    metric_id: str, semantic_type: str, unit: str, temporal_type: str,
    producer: str, entity_kinds: str, description: str,
) -> MetricDefinition:
    return MetricDefinition(
        metric_id, semantic_type, unit, temporal_type, producer,
        tuple(entity_kinds.split("|")), description,
    )


STANDARD_METRICS = tuple(sorted((
    _m("price", "price", "USD", "instant", "source_adapter", "public_equity|public_fund|index", "Security price at an identified market epoch."),
    _m("adjusted_price", "price", "USD", "instant", "source_adapter", "public_equity|public_fund|index", "Split- and distribution-adjusted historical close used for return analysis, not execution."),
    _m("risk_free_rate", "rate", "decimal", "instant", "source_adapter", "market|macro", "Declared horizon-matched risk-free rate."),
    _m("risk_free_10y", "rate", "decimal", "instant", "source_adapter", "market|macro", "Ten-year Treasury yield."),
    _m("treasury_3m_yield", "rate", "decimal", "instant", "source_adapter", "macro", "Three-month nominal Treasury market yield."),
    _m("treasury_1y_yield", "rate", "decimal", "instant", "source_adapter", "macro", "One-year nominal Treasury market yield."),
    _m("treasury_10y_real_yield", "rate", "decimal", "instant", "source_adapter", "macro", "Ten-year inflation-indexed Treasury real yield."),
    _m("breakeven_inflation_10y", "rate", "decimal", "instant", "source_adapter", "macro", "Ten-year market breakeven inflation rate."),
    _m("term_spread_10y_3m", "rate", "decimal", "instant", "source_adapter", "macro", "Ten-year less three-month nominal Treasury spread."),
    _m("treasury_10y_nominal_recomposed", "rate", "decimal", "instant", "signal_ast", "market", "Nominal ten-year yield recomposed from matched TIPS real yield and breakeven inflation."),
    _m("implied_equity_risk_premium", "rate", "decimal", "instant", "model_observation", "market", "Forward-looking premium from an identified implied-ERP model."),
    _m("implied_erp_ttm_cash_yield", "rate", "decimal", "instant", "model_observation", "market", "Cash-flow-implied ERP variant using trailing twelve-month cash yield."),
    _m("implied_erp_10y_average_cash_flow_yield", "rate", "decimal", "instant", "model_observation", "market", "Cash-flow-implied ERP variant using ten-year average cash-flow yield."),
    _m("implied_erp_net_cash_yield", "rate", "decimal", "instant", "model_observation", "market", "Cash-flow-implied ERP variant using net cash yield."),
    _m("implied_erp_normalized_earnings_payout", "rate", "decimal", "instant", "model_observation", "market", "Cash-flow-implied ERP variant using normalized earnings and payout."),
    _m("historical_equity_risk_premium", "rate", "decimal", "window", "factor_model", "market", "Annualized realized equity premium over a declared window."),
    _m("equity_risk_premium_consensus", "rate", "decimal", "assumption", "committee", "market", "Weighted ERP committee estimate with component provenance."),
    _m("market_required_return", "rate", "decimal", "instant", "signal_ast", "market", "Risk-free rate plus implied ERP."),
    _m("sp500_forward_earnings_yield", "rate", "decimal", "instant", "source_adapter", "market", "Reciprocal of an identified forward S&P 500 earnings multiple."),
    _m("sp500_trailing_earnings_yield", "rate", "decimal", "instant", "source_adapter", "market", "Trailing reported S&P 500 earnings divided by index price."),
    _m("sp500_trailing_dividend_yield", "rate", "decimal", "window", "source_adapter", "market", "Trailing S&P 500 cash dividends divided by index price."),
    _m("forward_earnings_yield_minus_nominal_10y", "rate_spread", "decimal", "instant", "signal_ast", "market", "Forward earnings yield less the nominal ten-year yield recomposed from TIPS and breakeven inflation; a valuation diagnostic, not expected return."),
    _m("trailing_earnings_yield_minus_tips_diagnostic", "rate_spread", "decimal", "instant", "signal_ast", "market", "Trailing earnings yield less ten-year TIPS real yield; omits growth and payout mechanics."),
    _m("dividend_yield_minus_tips_income_diagnostic", "rate_spread", "decimal", "instant", "signal_ast", "market", "Trailing dividend yield less ten-year TIPS real yield; an income spread that omits retained earnings and buybacks."),
    _m("equity_beta", "multiple", "multiple", "window", "factor_model", "public_equity", "Point-in-time beta against a declared benchmark and return window."),
    _m("cost_of_equity", "rate", "decimal", "assumption", "valuation_grammar", "public_equity", "Risk-free rate plus beta-scaled ERP."),
    _m("revenue_q", "currency_flow", "USD/quarter", "period", "source_adapter", "public_equity", "Revenue for one standalone fiscal quarter."),
    _m("operating_income_q", "currency_flow", "USD/quarter", "period", "source_adapter", "public_equity", "Operating income for one standalone fiscal quarter."),
    _m("net_income_q", "currency_flow", "USD/quarter", "period", "source_adapter", "public_equity", "Net income for one standalone fiscal quarter."),
    _m("operating_margin_q", "rate", "decimal", "period", "signal_ast", "public_equity", "Quarterly operating income divided by quarterly revenue."),
    _m("revenue_fy", "currency_flow", "USD/year", "period", "source_adapter", "public_equity", "Revenue for one fiscal period."),
    _m("operating_cash_flow_fy", "currency_flow", "USD/year", "period", "source_adapter", "public_equity", "Operating cash flow for one fiscal period."),
    _m("capital_expenditure_fy", "currency_flow", "USD/year", "period", "source_adapter", "public_equity", "Capital expenditure for one fiscal period."),
    _m("net_income_fy", "currency_flow", "USD/year", "period", "source_adapter", "public_equity", "Net income for one fiscal period."),
    _m("cash", "currency", "USD", "instant", "source_adapter", "public_equity", "Cash and equivalents at a balance-sheet date."),
    _m("assets", "currency", "USD", "instant", "source_adapter", "public_equity", "Total assets at a balance-sheet date."),
    _m("debt_current", "currency", "USD", "instant", "source_adapter", "public_equity", "Current interest-bearing debt."),
    _m("debt_noncurrent", "currency", "USD", "instant", "source_adapter", "public_equity", "Non-current interest-bearing debt."),
    _m("diluted_shares", "shares", "shares", "period", "source_adapter", "public_equity", "Weighted-average diluted shares."),
    _m("diluted_shares_current", "shares", "shares", "period", "source_adapter", "public_equity", "Freshest filed weighted-average diluted-share basis across available filing periods."),
    _m("stock_split_ratio", "share_ratio", "new_shares/old_share", "event", "source_adapter", "public_equity|public_fund", "Declared new shares per old share at a stock-split event, retrieval-bound when provider vintages are unavailable."),
    _m("normalized_owner_earnings", "currency_flow", "USD/year", "period", "signal_ast", "public_equity", "Operating cash flow less declared capital expenditure before qualitative normalization."),
    _m("total_debt", "currency", "USD", "instant", "signal_ast", "public_equity", "Current plus non-current debt."),
    _m("excess_net_cash", "currency", "USD", "instant", "signal_ast", "public_equity", "Cash less current and non-current debt."),
    _m("owner_earnings_margin", "rate", "decimal", "period", "signal_ast", "public_equity", "Normalized owner earnings divided by revenue."),
    _m("owner_earnings_balance", "score", "score", "period", "signal_ast", "public_equity", "Unit-invariant symmetric bound m/(1+|m|) of owner-earnings margin; a tail-sensitivity score, not a substitute economic estimand."),
    _m("return_on_assets", "rate", "decimal", "period", "signal_ast", "public_equity", "Net income divided by ending assets; a screening proxy."),
    _m("cash_conversion", "multiple", "multiple", "period", "signal_ast", "public_equity", "Operating cash flow divided by net income for the same fiscal period."),
    _m("cash_to_assets", "rate", "decimal", "instant", "signal_ast", "public_equity", "Cash and equivalents divided by total assets at a balance-sheet date."),
    _m("net_debt", "currency", "USD", "instant", "signal_ast", "public_equity", "Current and non-current debt less cash and equivalents."),
    _m("market_cap", "currency", "USD", "instant", "signal_ast", "public_equity", "Current price times the latest available diluted share count; an explicitly source-bounded approximation."),
    _m("owner_earnings_yield", "rate", "decimal", "instant", "signal_ast", "public_equity", "Normalized annual owner earnings divided by source-bounded market capitalization."),
    _m("net_debt_to_owner_earnings", "multiple", "multiple", "period", "signal_ast", "public_equity", "Net debt divided by normalized annual owner earnings."),
    _m("portfolio_price_to_earnings", "multiple", "multiple", "instant", "issuer_adapter", "public_fund", "Issuer-reported aggregate portfolio price/earnings."),
    _m("portfolio_price_to_book", "multiple", "multiple", "instant", "issuer_adapter", "public_fund", "Issuer-reported aggregate portfolio price/book."),
    _m("portfolio_return_on_equity", "rate", "decimal", "instant", "issuer_adapter", "public_fund", "Issuer-reported aggregate portfolio return on equity."),
    _m("portfolio_earnings_growth", "rate", "decimal", "instant", "issuer_adapter", "public_fund", "Issuer-reported portfolio earnings growth."),
    _m("portfolio_holdings_count", "count", "count", "instant", "issuer_adapter", "public_fund", "Number of portfolio holdings."),
    _m("portfolio_turnover", "rate", "decimal", "period", "issuer_adapter", "public_fund", "Portfolio turnover for the issuer-declared period."),
    _m("expense_ratio", "rate", "decimal", "period", "issuer_adapter", "public_fund", "Annual fund expense ratio."),
    _m("portfolio_top10_concentration", "rate", "decimal", "instant", "issuer_adapter", "public_fund", "Sum of the ten largest disclosed weights."),
    _m("portfolio_max_holding_weight", "rate", "decimal", "instant", "issuer_adapter", "public_fund", "Largest disclosed portfolio weight."),
    _m("portfolio_holdings_hhi", "score", "score", "instant", "issuer_adapter", "public_fund", "Herfindahl concentration of disclosed weights."),
    _m("portfolio_sector_hhi", "score", "score", "instant", "issuer_adapter", "public_fund", "Herfindahl concentration of disclosed sector weights."),
    _m("portfolio_top_sector_weight", "rate", "decimal", "instant", "issuer_adapter", "public_fund", "Largest disclosed sector weight."),
    _m("fund_net_assets", "currency", "USD", "instant", "issuer_adapter", "public_fund", "Issuer-reported fund net assets."),
    _m("median_bid_ask_spread", "rate", "decimal", "window", "issuer_adapter", "public_fund", "Issuer-reported median bid/ask spread over its declared window."),
    _m("average_daily_volume_30d", "count", "shares/day", "window", "issuer_adapter", "public_fund", "Issuer-reported average daily share volume over 30 days."),
    _m("portfolio_earnings_yield", "rate", "decimal", "instant", "signal_ast", "public_fund", "Reciprocal of aggregate portfolio price/earnings."),
    _m("portfolio_book_to_price", "rate", "decimal", "instant", "signal_ast", "public_fund", "Reciprocal of aggregate portfolio price/book."),
    _m("portfolio_net_earnings_yield", "rate", "decimal", "instant", "signal_ast", "public_fund", "Portfolio earnings yield less expense ratio."),
    _m("portfolio_equity_beta", "multiple", "multiple", "window", "issuer_adapter", "public_fund", "Issuer-reported equity beta under the provider's stated methodology; distinct from a kernel factor estimate."),
    _m("portfolio_standard_deviation_3y", "rate", "decimal", "window", "issuer_adapter", "public_fund", "Issuer-reported annualized three-year return standard deviation."),
    _m("portfolio_trailing_yield", "rate", "decimal", "window", "issuer_adapter", "public_fund", "Issuer-reported trailing portfolio distribution yield."),
    _m("factor_beta_market", "multiple", "multiple", "window", "factor_model", "public_equity|public_fund|index", "Estimated market-factor exposure."),
    _m("factor_beta_value", "multiple", "multiple", "window", "factor_model", "public_equity|public_fund|index", "Estimated value-factor exposure."),
    _m("factor_beta_size", "multiple", "multiple", "window", "factor_model", "public_equity|public_fund|index", "Estimated size-factor exposure."),
    _m("factor_beta_momentum", "multiple", "multiple", "window", "factor_model", "public_equity|public_fund|index", "Estimated momentum-factor exposure."),
    _m("factor_beta_quality", "multiple", "multiple", "window", "factor_model", "public_equity|public_fund|index", "Estimated quality-factor exposure."),
    _m("factor_residual_alpha", "rate", "decimal", "window", "factor_model", "public_equity|public_fund|index", "Historical annualized intercept after factor decomposition."),
    _m("factor_tracking_error", "rate", "decimal", "window", "factor_model", "public_equity|public_fund|index", "Annualized residual volatility."),
    _m("maximum_drawdown", "rate", "decimal", "window", "factor_model", "public_equity|public_fund|index", "Maximum peak-to-trough return over the declared window."),
    _m("factor_implied_return", "rate", "decimal", "assumption", "factor_model", "public_equity|public_fund|index", "Expected return assembled from factor premiums and exposures."),
    _m("earnings_power_value", "price", "currency/share", "assumption", "valuation_grammar", "public_equity", "Capitalized no-growth owner earnings plus declared excess cash."),
    _m("intrinsic_value", "price", "currency/share", "assumption", "valuation_grammar", "public_equity", "Present value from one enumerated cash-flow program."),
    _m("earnings_power_margin_of_safety", "rate", "decimal", "assumption", "valuation_grammar", "public_equity", "Earnings-power value divided by price less one."),
    _m("implied_growth", "rate", "decimal", "assumption", "valuation_grammar", "public_equity|public_fund", "Growth rate that solves the declared price equation."),
    _m("implied_required_return", "rate", "decimal", "assumption", "valuation_grammar", "public_equity", "Discount rate that solves the declared price equation."),
    _m("price_implied_excess_return", "rate", "decimal", "assumption", "valuation_grammar", "public_equity", "Price-implied required return less risk-free rate."),
    _m("earnings_durability", "score", "score", "window", "quality_model", "public_equity", "Evidence-weighted persistence and business-quality score."),
    _m("earnings_fragility", "score", "score", "window", "quality_model", "public_equity", "Evidence-weighted concentration, cyclicality, and financing fragility score."),
), key=lambda row: row.metric_id))


def standard_signal_definitions(entity_id: str, entity_kind: str) -> tuple[SignalDefinition, ...]:
    """Return the small, executable metric DAG for one typed entity."""
    entity = require_text(entity_id, "metric entity_id")

    def definition(metric_id: str, operator: str, arguments: tuple[SignalArgument, ...], unit: str) -> SignalDefinition:
        return SignalDefinition(
            signal_id=f"standard:{entity}:{metric_id}", entity_id=entity,
            metric_id=metric_id, operator=operator, arguments=arguments, unit=unit,
            description=f"Standard typed derivation for {metric_id}.",
        )

    local = lambda metric: SignalArgument(metric_id=metric)
    external = lambda owner, metric: SignalArgument(metric_id=metric, entity_id=owner)
    if entity_kind == "public_fund":
        return (
            definition("portfolio_earnings_yield", "reciprocal", (local("portfolio_price_to_earnings"),), "decimal"),
            definition("portfolio_book_to_price", "reciprocal", (local("portfolio_price_to_book"),), "decimal"),
            definition("portfolio_net_earnings_yield", "subtract", (local("portfolio_earnings_yield"), local("expense_ratio")), "decimal"),
        )
    if entity_kind == "market":
        return (
            definition(
                "market_required_return", "add",
                (local("risk_free_rate"), local("implied_equity_risk_premium")), "decimal",
            ),
            definition(
                "treasury_10y_nominal_recomposed", "compound_rates",
                (external("US-MACRO", "treasury_10y_real_yield"), external("US-MACRO", "breakeven_inflation_10y")),
                "decimal",
            ),
            definition(
                "forward_earnings_yield_minus_nominal_10y", "subtract",
                (local("sp500_forward_earnings_yield"), local("treasury_10y_nominal_recomposed")),
                "decimal",
            ),
            definition(
                "trailing_earnings_yield_minus_tips_diagnostic", "subtract",
                (local("sp500_trailing_earnings_yield"), external("US-MACRO", "treasury_10y_real_yield")),
                "decimal",
            ),
            definition(
                "dividend_yield_minus_tips_income_diagnostic", "subtract",
                (local("sp500_trailing_dividend_yield"), external("US-MACRO", "treasury_10y_real_yield")),
                "decimal",
            ),
        )
    if entity_kind != "public_equity":
        return ()
    return (
        definition("operating_margin_q", "divide", (local("operating_income_q"), local("revenue_q")), "decimal"),
        definition("normalized_owner_earnings", "aligned_subtract", (local("operating_cash_flow_fy"), local("capital_expenditure_fy")), "USD/year"),
        definition("cash_conversion", "ratio", (local("operating_cash_flow_fy"), local("net_income_fy")), "multiple"),
        definition("total_debt", "add", (local("debt_current"), local("debt_noncurrent")), "USD"),
        definition("excess_net_cash", "subtract", (local("cash"), local("total_debt")), "USD"),
        definition("net_debt", "negative", (local("excess_net_cash"),), "USD"),
        definition("market_cap", "multiply", (local("price"), local("diluted_shares_current")), "USD"),
        definition("owner_earnings_yield", "yield", (local("normalized_owner_earnings"), local("market_cap")), "decimal"),
        definition("net_debt_to_owner_earnings", "ratio", (local("net_debt"), local("normalized_owner_earnings")), "multiple"),
        definition("owner_earnings_margin", "divide", (local("normalized_owner_earnings"), local("revenue_fy")), "decimal"),
        definition("owner_earnings_balance", "symmetric_bound", (local("owner_earnings_margin"),), "score"),
        definition("return_on_assets", "divide", (local("net_income_fy"), local("assets")), "decimal"),
        definition("cash_to_assets", "ratio", (local("cash"), local("assets")), "decimal"),
    )


def derive_standard_metrics(
    observations: Iterable[MetricObservation], *, as_of: str,
    configured_outputs: Iterable[tuple[str, str]] = (),
) -> tuple[tuple[MetricObservation, ...], tuple[Any, ...], tuple[dict[str, str], ...]]:
    """Apply the standard DAG wherever provider observations identify an entity kind."""
    rows = tuple(observations)
    metrics_by_entity: dict[str, set[str]] = {}
    for row in rows:
        metrics_by_entity.setdefault(row.entity_id, set()).add(row.metric_id)
    definitions: list[SignalDefinition] = []
    excluded = set(configured_outputs)
    for entity_id, metric_ids in sorted(metrics_by_entity.items()):
        entity_kind = (
            "market" if entity_id == "US-MARKET"
            else "public_fund" if "portfolio_price_to_earnings" in metric_ids
            else "public_equity" if metric_ids & {
                "revenue_q", "operating_income_q", "net_income_q",
                "revenue_fy", "operating_cash_flow_fy", "net_income_fy",
            }
            else ""
        )
        definitions.extend(
            row for row in standard_signal_definitions(entity_id, entity_kind)
            if (entity_id, row.metric_id) not in excluded
        )
    return derive_signals_partial(rows, definitions, as_of=as_of) if definitions else (rows, (), ())


def metric_universe_surface(observations: Iterable[Mapping[str, Any]] = ()) -> dict[str, Any]:
    """Expose the typed metric registry and the two AST contracts to the workbench."""
    rows = tuple(observations)
    observed_ids = {str(row.get("metric_id") or "") for row in rows}
    registered_ids = {row.metric_id for row in STANDARD_METRICS}
    canonical_observed_ids = {METRIC_ALIASES.get(metric_id, metric_id) for metric_id in observed_ids}
    definitions = [
        {**row.to_dict(), "observed": row.metric_id in canonical_observed_ids}
        for row in STANDARD_METRICS
    ]
    signal_examples = (
        *standard_signal_definitions("$SELF", "public_fund"),
        *standard_signal_definitions("$SELF", "public_equity"),
        *standard_signal_definitions("US-MARKET", "market"),
    )
    body = {
        "schema": METRIC_UNIVERSE_SCHEMA,
        "metric_count": len(definitions),
        "observed_registered_count": len(canonical_observed_ids & registered_ids),
        "observed_aliases": [
            {"observed_metric_id": metric_id, "canonical_metric_id": METRIC_ALIASES[metric_id]}
            for metric_id in sorted(observed_ids & METRIC_ALIASES.keys())
        ],
        "unregistered_observed_metric_ids": sorted(
            observed_ids - registered_ids - METRIC_ALIASES.keys()
        ),
        "metrics": definitions,
        "signal_ast_contract": {
            "schema": "jaggedthoughts-signal-definition-v1",
            "operators": SIGNAL_OPERATOR_CONTRACT,
            "standard_nodes": [row.to_dict() for row in signal_examples],
            "composition": "A metric reference may target another derived node; the acyclic definition graph is the recursive AST.",
        },
        "valuation_ast_contract": valuation_grammar_contract(),
        "boundary": "Computability and lineage do not establish predictive power or capital authority.",
    }
    return {**body, "metric_universe_sha256": stable_sha256(body)}


__all__ = [
    "METRIC_ALIASES", "METRIC_UNIVERSE_SCHEMA", "MetricDefinition", "STANDARD_METRICS",
    "derive_standard_metrics", "metric_universe_surface", "standard_signal_definitions",
]
