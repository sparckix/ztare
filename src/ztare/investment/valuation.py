"""Typed valuation-program grammar and deterministic interpreter.

The grammar enumerates discrete valuation specifications.  Numeric root solvers
remain operator implementations, so continuous parameter search does not
inflate the program language.  Results are assumptions-relative and carry no
position authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from statistics import median
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256
from ztare.strategy import OperatorGrammar, Program, TypedOperator, TypedTerminal
from ztare.strategy.jaggedthoughts import EnumerationResult, enumerate_typed_programs

from .contracts import require_finite, require_refs, require_text


_UNITS = {
    "MarketPrice": "currency/share",
    "OwnerEarnings": "currency/year",
    "ExcessNetCash": "currency",
    "Shares": "shares",
    "RiskFreeRate": "decimal",
    "EquityRiskPremium": "decimal",
    "EquityBeta": "multiple",
    "DiscountRate": "decimal",
    "ForecastGrowth": "decimal",
    "TerminalGrowth": "decimal",
    "Horizon": "years",
}
_RESULT_UNITS = {
    "IntrinsicValue": "currency/share",
    "EarningsPowerValue": "currency/share",
    "ImpliedGrowth": "decimal",
    "ImpliedReturn": "decimal",
}


@dataclass(frozen=True, slots=True)
class ValuationAssumption:
    assumption_id: str
    assumption_type: str
    value: float
    unit: str
    source_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "assumption_id", require_text(self.assumption_id, "valuation assumption_id"))
        kind = require_text(self.assumption_type, "valuation assumption_type")
        expected_unit = _UNITS.get(kind)
        if expected_unit is None:
            raise ValueError(f"unsupported valuation assumption type: {kind}")
        unit = require_text(self.unit, "valuation assumption unit")
        if unit != expected_unit:
            raise ValueError(f"{kind} unit must be {expected_unit}, got {unit}")
        value = require_finite(self.value, f"valuation assumption {self.assumption_id}")
        if kind in {"MarketPrice", "OwnerEarnings", "Shares", "Horizon"} and value <= 0:
            raise ValueError(f"{kind} assumption must be positive")
        if kind == "Horizon" and (int(value) != value or value > 100):
            raise ValueError("valuation horizon must be an integer in [1, 100] years")
        if kind in {"DiscountRate", "RiskFreeRate"} and value <= -1:
            raise ValueError(f"{kind} must exceed -100 percent")
        if kind in {"ForecastGrowth", "TerminalGrowth", "EquityRiskPremium"} and value <= -1:
            raise ValueError(f"{kind} must exceed -100 percent")
        if kind == "EquityBeta" and value < 0:
            raise ValueError("EquityBeta cannot be negative")
        object.__setattr__(self, "assumption_type", kind)
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "unit", unit)
        object.__setattr__(self, "source_refs", require_refs(self.source_refs, "valuation source ref"))

    @property
    def terminal_id(self) -> str:
        return f"input::{self.assumption_type}::{self.assumption_id}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "assumption_id": self.assumption_id,
            "assumption_type": self.assumption_type,
            "value": self.value,
            "unit": self.unit,
            "source_refs": list(self.source_refs),
        }


@dataclass(frozen=True, slots=True)
class ValuationScenario:
    """One strategy mechanism's coherent cash-flow assumption bundle."""

    scenario_id: str
    mechanism_id: str
    assumption_ids: tuple[str, ...]
    source_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "scenario_id", require_text(self.scenario_id, "valuation scenario_id"))
        object.__setattr__(self, "mechanism_id", require_text(self.mechanism_id, "valuation mechanism_id"))
        object.__setattr__(self, "assumption_ids", require_refs(
            self.assumption_ids, "valuation scenario assumption"
        ))
        object.__setattr__(self, "source_refs", require_refs(
            self.source_refs, "valuation scenario source ref"
        ))

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "mechanism_id": self.mechanism_id,
            "assumption_ids": list(self.assumption_ids),
            "source_refs": list(self.source_refs),
        }


@dataclass(frozen=True, slots=True)
class ProjectedCashFlows:
    starting_owner_earnings: float
    forecast_growth: float
    horizon_years: int


@dataclass(frozen=True, slots=True)
class ValuationProgramResult:
    program_id: str
    result_type: str
    expression: str
    value: float
    unit: str
    assumption_ids: tuple[str, ...]
    scenario_ids: tuple[str, ...]
    source_refs: tuple[str, ...]
    result_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        for attr in ("program_id", "result_type", "expression", "unit"):
            object.__setattr__(self, attr, require_text(getattr(self, attr), f"valuation result {attr}"))
        if self.result_type not in _RESULT_UNITS:
            raise ValueError(f"unsupported valuation result type: {self.result_type}")
        if self.unit != _RESULT_UNITS[self.result_type]:
            raise ValueError("valuation result unit does not match its type")
        object.__setattr__(self, "value", require_finite(self.value, "valuation result value"))
        object.__setattr__(self, "assumption_ids", tuple(sorted(set(self.assumption_ids))))
        object.__setattr__(self, "scenario_ids", tuple(sorted(set(self.scenario_ids))))
        object.__setattr__(self, "source_refs", require_refs(self.source_refs, "valuation result source ref"))
        object.__setattr__(self, "result_sha256", stable_sha256(self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "jaggedthoughts-valuation-program-result-v1",
            "program_id": self.program_id,
            "result_type": self.result_type,
            "expression": self.expression,
            "value": self.value,
            "unit": self.unit,
            "assumption_ids": list(self.assumption_ids),
            "scenario_ids": list(self.scenario_ids),
            "source_refs": list(self.source_refs),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "result_sha256": self.result_sha256}


@dataclass(frozen=True, slots=True)
class ValuationProgramFailure:
    program_id: str
    expression: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {
            "program_id": self.program_id,
            "expression": self.expression,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class ExpectationsFrontierPoint:
    program_id: str
    value: float
    assumption_ids: tuple[str, ...]
    scenario_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "program_id", require_text(self.program_id, "frontier program_id"))
        object.__setattr__(self, "value", require_finite(self.value, "frontier value"))
        object.__setattr__(self, "assumption_ids", tuple(sorted(set(self.assumption_ids))))
        object.__setattr__(self, "scenario_ids", tuple(sorted(set(self.scenario_ids))))

    def to_dict(self) -> dict[str, Any]:
        return {
            "program_id": self.program_id,
            "value": self.value,
            "assumption_ids": list(self.assumption_ids),
            "scenario_ids": list(self.scenario_ids),
        }


@dataclass(frozen=True, slots=True)
class ExpectationsFrontierCertificate:
    scope_closed: bool
    supporting_intrinsic_program_ids: tuple[str, ...]
    shortfall_intrinsic_program_ids: tuple[str, ...]
    implied_growth_curve: tuple[ExpectationsFrontierPoint, ...]
    implied_return_curve: tuple[ExpectationsFrontierPoint, ...]
    certificate_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        supporting = tuple(sorted(set(self.supporting_intrinsic_program_ids)))
        shortfall = tuple(sorted(set(self.shortfall_intrinsic_program_ids)))
        if set(supporting) & set(shortfall):
            raise ValueError("expectations frontier partitions overlap")
        growth = tuple(sorted(self.implied_growth_curve, key=lambda row: (row.value, row.program_id)))
        returns = tuple(sorted(self.implied_return_curve, key=lambda row: (row.value, row.program_id)))
        if not growth or not returns:
            raise ValueError("expectations frontier requires inverse valuation curves")
        object.__setattr__(self, "supporting_intrinsic_program_ids", supporting)
        object.__setattr__(self, "shortfall_intrinsic_program_ids", shortfall)
        object.__setattr__(self, "implied_growth_curve", growth)
        object.__setattr__(self, "implied_return_curve", returns)
        object.__setattr__(self, "certificate_sha256", stable_sha256(self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "jaggedthoughts-expectations-frontier-v1",
            "scope_closed": self.scope_closed,
            "supporting_intrinsic_program_ids": list(self.supporting_intrinsic_program_ids),
            "shortfall_intrinsic_program_ids": list(self.shortfall_intrinsic_program_ids),
            "implied_growth_curve": [row.to_dict() for row in self.implied_growth_curve],
            "implied_return_curve": [row.to_dict() for row in self.implied_return_curve],
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "certificate_sha256": self.certificate_sha256}


@dataclass(frozen=True, slots=True)
class ValuationEnvelope:
    envelope_id: str
    entity_id: str
    evidence_epoch: str
    assumptions: tuple[ValuationAssumption, ...]
    scenarios: tuple[ValuationScenario, ...]
    enumeration: EnumerationResult
    results: tuple[ValuationProgramResult, ...]
    failures: tuple[ValuationProgramFailure, ...]
    equivalence_classes: tuple[tuple[str, ...], ...]
    expectations_frontier: ExpectationsFrontierCertificate
    summary: tuple[tuple[str, float], ...]
    envelope_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        for attr in ("envelope_id", "entity_id", "evidence_epoch"):
            object.__setattr__(self, attr, require_text(getattr(self, attr), f"valuation envelope {attr}"))
        assumptions = tuple(sorted(self.assumptions, key=lambda row: row.assumption_id))
        scenarios = tuple(sorted(self.scenarios, key=lambda row: row.scenario_id))
        results = tuple(sorted(self.results, key=lambda row: row.program_id))
        failures = tuple(sorted(self.failures, key=lambda row: row.program_id))
        if not results:
            raise ValueError("valuation envelope requires at least one valid result")
        object.__setattr__(self, "assumptions", assumptions)
        object.__setattr__(self, "scenarios", scenarios)
        object.__setattr__(self, "results", results)
        object.__setattr__(self, "failures", failures)
        object.__setattr__(self, "equivalence_classes", tuple(sorted(
            (tuple(sorted(group)) for group in self.equivalence_classes),
            key=lambda group: group[0],
        )))
        object.__setattr__(self, "summary", tuple(sorted(
            (require_text(key, "valuation summary key"), require_finite(value, f"valuation summary {key}"))
            for key, value in self.summary
        )))
        object.__setattr__(self, "envelope_sha256", stable_sha256(self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "jaggedthoughts-valuation-envelope-v1",
            "envelope_id": self.envelope_id,
            "entity_id": self.entity_id,
            "evidence_epoch": self.evidence_epoch,
            "assumptions": [row.to_dict() for row in self.assumptions],
            "scenarios": [row.to_dict() for row in self.scenarios],
            "enumeration": self.enumeration.to_dict(),
            "results": [row.to_dict() for row in self.results],
            "failures": [row.to_dict() for row in self.failures],
            "equivalence_classes": [list(group) for group in self.equivalence_classes],
            "expectations_frontier": self.expectations_frontier.to_dict(),
            "summary": dict(self.summary),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "envelope_sha256": self.envelope_sha256}


def _valuation_operators() -> tuple[TypedOperator, ...]:
    return (
        TypedOperator(
            "cost_of_equity", ("RiskFreeRate", "EquityRiskPremium", "EquityBeta"),
            "DiscountRate", description="Compose a market-state premium and entity beta into a discount rate.",
        ),
        TypedOperator(
            "project_owner_earnings", ("OwnerEarnings", "ForecastGrowth", "Horizon"),
            "CashFlowSeries", description="Project normalized owner earnings over an explicit horizon.",
        ),
        TypedOperator(
            "present_value", ("CashFlowSeries", "DiscountRate", "TerminalGrowth"),
            "EquityValue", description="Discount projected owner earnings and continuing value.",
        ),
        TypedOperator(
            "add_excess_net_cash", ("EquityValue", "ExcessNetCash"),
            "EquityValueWithCash", description="Bridge operating equity value through declared excess net cash.",
        ),
        TypedOperator(
            "per_share", ("EquityValueWithCash", "Shares"), "IntrinsicValue",
            description="Convert equity value into per-share value.",
        ),
        TypedOperator(
            "earnings_power", ("OwnerEarnings", "DiscountRate", "ExcessNetCash", "Shares"),
            "EarningsPowerValue", description="Capitalize normalized no-growth owner earnings.",
        ),
        TypedOperator(
            "implied_growth",
            ("MarketPrice", "OwnerEarnings", "DiscountRate", "TerminalGrowth", "Horizon", "ExcessNetCash", "Shares"),
            "ImpliedGrowth", description="Solve for the explicit-period growth embedded in market price.",
        ),
        TypedOperator(
            "implied_return",
            ("MarketPrice", "OwnerEarnings", "ForecastGrowth", "TerminalGrowth", "Horizon", "ExcessNetCash", "Shares"),
            "ImpliedReturn", description="Solve for the required return embedded in market price.",
        ),
    )


def valuation_grammar_contract() -> dict[str, Any]:
    """Expose the exact variable types and recursive AST operator signatures."""
    body = {
        "schema": "jaggedthoughts-valuation-grammar-contract-v1",
        "input_types": dict(sorted(_UNITS.items())),
        "result_types": dict(sorted(_RESULT_UNITS.items())),
        "operators": [row.to_dict() for row in _valuation_operators()],
    }
    return {**body, "contract_sha256": stable_sha256(body)}


def build_valuation_grammar(
    *,
    grammar_id: str,
    version: str,
    assumptions: Iterable[ValuationAssumption],
) -> OperatorGrammar:
    rows = tuple(assumptions)
    if (
        not rows
        or len({row.terminal_id for row in rows}) != len(rows)
        or len({row.assumption_id for row in rows}) != len(rows)
    ):
        raise ValueError("valuation assumptions must be nonempty and unique")
    return OperatorGrammar(
        grammar_id=require_text(grammar_id, "valuation grammar_id"),
        version=require_text(version, "valuation grammar version"),
        terminals=tuple(
            TypedTerminal(
                terminal_id=row.terminal_id,
                output_type=row.assumption_type,
                description=f"{row.assumption_id}: {row.value} {row.unit}",
            )
            for row in rows
        ),
        operators=_valuation_operators(),
    )


def present_value_owner_earnings(
    starting_owner_earnings: float,
    forecast_growth: float,
    horizon_years: int,
    discount_rate: float,
    terminal_growth: float,
) -> float:
    """Canonical numeric carrier for the valuation grammar's DCF operator."""
    series = ProjectedCashFlows(
        require_finite(starting_owner_earnings, "starting owner earnings"),
        require_finite(forecast_growth, "forecast growth"),
        int(horizon_years),
    )
    discount = require_finite(discount_rate, "discount rate")
    terminal_growth = require_finite(terminal_growth, "terminal growth")
    if discount <= terminal_growth:
        raise ValueError("discount rate must exceed terminal growth")
    cash = series.starting_owner_earnings
    value = 0.0
    for year in range(1, series.horizon_years + 1):
        cash *= 1 + series.forecast_growth
        value += cash / (1 + discount) ** year
    terminal = cash * (1 + terminal_growth) / (discount - terminal_growth)
    return value + terminal / (1 + discount) ** series.horizon_years


def solve_implied_growth(
    *,
    market_price: float,
    owner_earnings: float,
    discount_rate: float,
    terminal_growth: float,
    horizon_years: int,
    excess_net_cash: float,
    shares: float,
) -> float:
    """Solve the explicit-period growth required by a declared market price."""
    target = require_finite(market_price, "market price") * require_finite(shares, "shares")
    target -= require_finite(excess_net_cash, "excess net cash")
    if target <= 0:
        raise ValueError("price-implied operating equity value must be positive")
    return _bisect(
        lambda growth: present_value_owner_earnings(
            owner_earnings,
            growth,
            int(horizon_years),
            discount_rate,
            terminal_growth,
        ) - target,
        -0.95,
        1.5,
        label="implied growth",
    )


def _bisect(function: Any, lower: float, upper: float, *, label: str) -> float:
    low_value = require_finite(function(lower), f"{label} lower value")
    high_value = require_finite(function(upper), f"{label} upper value")
    if low_value == 0:
        return lower
    if high_value == 0:
        return upper
    if low_value * high_value > 0:
        raise ValueError(f"{label} root is not bracketed")
    for _ in range(160):
        midpoint = (lower + upper) / 2
        value = require_finite(function(midpoint), f"{label} midpoint value")
        if abs(value) <= 1e-12:
            return midpoint
        if low_value * value <= 0:
            upper = midpoint
            high_value = value
        else:
            lower = midpoint
            low_value = value
    return (lower + upper) / 2


def _expression(program: Program) -> str:
    if program.terminal_id is not None:
        return program.terminal_id
    return f"{program.operator_id}(" + ", ".join(_expression(child) for child in program.children) + ")"


def _assumption_ids(program: Program, by_terminal: Mapping[str, ValuationAssumption]) -> tuple[str, ...]:
    if program.terminal_id is not None:
        return (by_terminal[program.terminal_id].assumption_id,)
    return tuple(sorted({
        assumption_id
        for child in program.children
        for assumption_id in _assumption_ids(child, by_terminal)
    }))


def _evaluate(program: Program, by_terminal: Mapping[str, ValuationAssumption]) -> Any:
    if program.terminal_id is not None:
        return by_terminal[program.terminal_id].value
    values = tuple(_evaluate(child, by_terminal) for child in program.children)
    operator = program.operator_id
    if operator == "cost_of_equity":
        risk_free, premium, beta = map(float, values)
        return risk_free + beta * premium
    if operator == "project_owner_earnings":
        return ProjectedCashFlows(float(values[0]), float(values[1]), int(values[2]))
    if operator == "present_value":
        return present_value_owner_earnings(
            values[0].starting_owner_earnings,
            values[0].forecast_growth,
            values[0].horizon_years,
            float(values[1]),
            float(values[2]),
        )
    if operator == "add_excess_net_cash":
        return float(values[0]) + float(values[1])
    if operator == "per_share":
        return float(values[0]) / float(values[1])
    if operator == "earnings_power":
        earnings, discount, excess_cash, shares = map(float, values)
        if discount <= 0:
            raise ValueError("earnings-power discount rate must be positive")
        return (earnings / discount + excess_cash) / shares
    if operator == "implied_growth":
        price, earnings, discount, terminal_growth, horizon, excess_cash, shares = map(float, values)
        return solve_implied_growth(
            market_price=price,
            owner_earnings=earnings,
            discount_rate=discount,
            terminal_growth=terminal_growth,
            horizon_years=int(horizon),
            excess_net_cash=excess_cash,
            shares=shares,
        )
    if operator == "implied_return":
        price, earnings, growth, terminal_growth, horizon, excess_cash, shares = map(float, values)
        target = price * shares - excess_cash
        if target <= 0:
            raise ValueError("price-implied operating equity value must be positive")
        lower = max(terminal_growth + 1e-8, -0.95)
        return _bisect(
            lambda discount: present_value_owner_earnings(
                earnings,
                growth,
                int(horizon),
                discount,
                terminal_growth,
            ) - target,
            lower,
            2.0,
            label="implied return",
        )
    raise ValueError(f"unsupported valuation operator: {operator}")


def compile_valuation_envelope(
    *,
    envelope_id: str,
    entity_id: str,
    evidence_epoch: str,
    grammar_id: str,
    grammar_version: str,
    assumptions: Iterable[ValuationAssumption],
    scenarios: Iterable[ValuationScenario] = (),
    max_depth: int = 4,
    max_programs: int = 5000,
) -> ValuationEnvelope:
    rows = tuple(assumptions)
    scenario_rows = tuple(scenarios)
    if len({row.scenario_id for row in scenario_rows}) != len(scenario_rows):
        raise ValueError("valuation scenario identities must be unique")
    assumption_by_id = {row.assumption_id: row for row in rows}
    scenario_assumption_ids: set[str] = set()
    for scenario in scenario_rows:
        unknown = set(scenario.assumption_ids) - set(assumption_by_id)
        if unknown:
            raise ValueError(
                f"valuation scenario {scenario.scenario_id} uses unknown assumptions: {sorted(unknown)}"
            )
        scenario_types = {
            assumption_by_id[assumption_id].assumption_type
            for assumption_id in scenario.assumption_ids
        }
        if not {"ForecastGrowth", "TerminalGrowth"} <= scenario_types:
            raise ValueError(
                f"valuation scenario {scenario.scenario_id} must bind forecast and terminal growth"
            )
        scenario_assumption_ids.update(scenario.assumption_ids)
    counts = {kind: sum(row.assumption_type == kind for row in rows) for kind in _UNITS}
    for singleton in ("MarketPrice", "ExcessNetCash", "Shares", "RiskFreeRate"):
        if counts[singleton] != 1:
            raise ValueError(f"valuation requires exactly one {singleton} assumption")
    for required in ("OwnerEarnings", "ForecastGrowth", "TerminalGrowth", "Horizon"):
        if counts[required] < 1:
            raise ValueError(f"valuation requires at least one {required} assumption")
    if counts["DiscountRate"] < 1 and not (
        counts["EquityRiskPremium"] >= 1 and counts["EquityBeta"] >= 1
    ):
        raise ValueError(
            "valuation requires a DiscountRate or an EquityRiskPremium plus EquityBeta"
        )
    grammar = build_valuation_grammar(
        grammar_id=grammar_id,
        version=grammar_version,
        assumptions=rows,
    )
    enumeration = enumerate_typed_programs(grammar, max_depth=max_depth, max_programs=max_programs)
    by_terminal = {row.terminal_id: row for row in rows}
    target_types = set(_RESULT_UNITS)
    results: list[ValuationProgramResult] = []
    failures: list[ValuationProgramFailure] = []
    for program in enumeration.programs:
        if program.output_type not in target_types:
            continue
        expression = _expression(program)
        assumption_ids = _assumption_ids(program, by_terminal)
        selected = [row for row in rows if row.assumption_id in assumption_ids]
        selected_scenario_assumptions = set(assumption_ids) & scenario_assumption_ids
        matching_scenarios = tuple(
            scenario for scenario in scenario_rows
            if selected_scenario_assumptions <= set(scenario.assumption_ids)
        ) if selected_scenario_assumptions else ()
        if selected_scenario_assumptions and not matching_scenarios:
            failures.append(ValuationProgramFailure(
                program.program_id,
                expression,
                "cash-flow assumptions cross declared strategy scenarios",
            ))
            continue
        try:
            value = require_finite(_evaluate(program, by_terminal), "valuation program value")
            results.append(ValuationProgramResult(
                program_id=program.program_id,
                result_type=program.output_type,
                expression=expression,
                value=value,
                unit=_RESULT_UNITS[program.output_type],
                assumption_ids=assumption_ids,
                scenario_ids=tuple(row.scenario_id for row in matching_scenarios),
                source_refs=tuple(
                    [ref for row in selected for ref in row.source_refs]
                    + [ref for scenario in matching_scenarios for ref in scenario.source_refs]
                ),
            ))
        except ValueError as error:
            failures.append(ValuationProgramFailure(program.program_id, expression, str(error)))
    grouped: dict[tuple[str, float], list[str]] = {}
    for result in results:
        grouped.setdefault((result.result_type, round(result.value, 12)), []).append(result.program_id)
    equivalence_classes = tuple(
        tuple(program_ids) for program_ids in grouped.values() if len(program_ids) > 1
    )
    by_type = {
        kind: [row.value for row in results if row.result_type == kind]
        for kind in _RESULT_UNITS
    }
    if any(not values for values in by_type.values()):
        missing = sorted(kind for kind, values in by_type.items() if not values)
        raise ValueError(f"valuation grammar produced no valid results for: {missing}")
    market_price = next(row.value for row in rows if row.assumption_type == "MarketPrice")
    risk_free = next(row.value for row in rows if row.assumption_type == "RiskFreeRate")
    conservative_epv = min(by_type["EarningsPowerValue"])
    summary = (
        ("market_price", market_price),
        ("earnings_power_value_low", conservative_epv),
        ("earnings_power_value_high", max(by_type["EarningsPowerValue"])),
        ("earnings_power_margin_of_safety", conservative_epv / market_price - 1),
        ("intrinsic_value_low", min(by_type["IntrinsicValue"])),
        ("intrinsic_value_high", max(by_type["IntrinsicValue"])),
        ("implied_growth_median", median(by_type["ImpliedGrowth"])),
        ("implied_growth_low", min(by_type["ImpliedGrowth"])),
        ("implied_growth_high", max(by_type["ImpliedGrowth"])),
        ("implied_required_return_median", median(by_type["ImpliedReturn"])),
        ("price_implied_excess_return", median(by_type["ImpliedReturn"]) - risk_free),
    )
    intrinsic_results = tuple(row for row in results if row.result_type == "IntrinsicValue")
    frontier = ExpectationsFrontierCertificate(
        scope_closed=enumeration.exhausted_within_scope,
        supporting_intrinsic_program_ids=tuple(
            row.program_id for row in intrinsic_results if row.value >= market_price
        ),
        shortfall_intrinsic_program_ids=tuple(
            row.program_id for row in intrinsic_results if row.value < market_price
        ),
        implied_growth_curve=tuple(
            ExpectationsFrontierPoint(
                row.program_id, row.value, row.assumption_ids, row.scenario_ids
            )
            for row in results if row.result_type == "ImpliedGrowth"
        ),
        implied_return_curve=tuple(
            ExpectationsFrontierPoint(
                row.program_id, row.value, row.assumption_ids, row.scenario_ids
            )
            for row in results if row.result_type == "ImpliedReturn"
        ),
    )
    return ValuationEnvelope(
        envelope_id=envelope_id,
        entity_id=entity_id,
        evidence_epoch=evidence_epoch,
        assumptions=rows,
        scenarios=scenario_rows,
        enumeration=enumeration,
        results=tuple(results),
        failures=tuple(failures),
        equivalence_classes=equivalence_classes,
        expectations_frontier=frontier,
        summary=summary,
    )


def compile_hurdle_price_frontier(
    envelope: ValuationEnvelope | Mapping[str, Any],
    *,
    excess_return_hurdle: float,
) -> dict[str, Any]:
    """Derive the purchase-price boundary for each declared cash-flow path."""
    hurdle = require_finite(excess_return_hurdle, "excess return hurdle")
    payload = envelope.to_dict() if isinstance(envelope, ValuationEnvelope) else dict(envelope)
    assumption_rows = tuple(payload.get("assumptions") or ())
    result_rows = tuple(payload.get("results") or ())
    assumptions = {str(row["assumption_id"]): row for row in assumption_rows}
    risk_free = next(float(row["value"]) for row in assumption_rows if row["assumption_type"] == "RiskFreeRate")
    market_price = next(float(row["value"]) for row in assumption_rows if row["assumption_type"] == "MarketPrice")
    required_return = risk_free + hurdle
    scenario_refs = {
        str(row["scenario_id"]): tuple(row.get("source_refs") or ())
        for row in payload.get("scenarios") or ()
    }
    needed = (
        "OwnerEarnings", "ForecastGrowth", "TerminalGrowth", "Horizon",
        "ExcessNetCash", "Shares",
    )
    unique: dict[tuple[Any, ...], dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    for result in result_rows:
        if result["result_type"] != "IntrinsicValue":
            continue
        result_assumption_ids = tuple(result.get("assumption_ids") or ())
        result_scenario_ids = tuple(result.get("scenario_ids") or ())
        selected = [assumptions[str(assumption_id)] for assumption_id in result_assumption_ids]
        by_type = {
            str(row["assumption_type"]): row
            for row in selected if row["assumption_type"] in needed
        }
        if set(by_type) != set(needed):
            continue
        terminal_growth = float(by_type["TerminalGrowth"]["value"])
        cash_flow_ids = tuple(str(by_type[kind]["assumption_id"]) for kind in needed)
        key = (*cash_flow_ids, *result_scenario_ids)
        if key in unique:
            continue
        if required_return <= terminal_growth:
            failures.append({
                "cash_flow_assumption_ids": list(cash_flow_ids),
                "scenario_ids": list(result_scenario_ids),
                "reason": "required return must exceed terminal growth",
            })
            continue
        operating_value = present_value_owner_earnings(
            float(by_type["OwnerEarnings"]["value"]),
            float(by_type["ForecastGrowth"]["value"]),
            int(float(by_type["Horizon"]["value"])),
            required_return,
            terminal_growth,
        )
        maximum_price = (
            operating_value + float(by_type["ExcessNetCash"]["value"])
        ) / float(by_type["Shares"]["value"])
        row = {
            "cash_flow_assumption_ids": list(cash_flow_ids),
            "scenario_ids": list(result_scenario_ids),
            "required_total_return": required_return,
            "maximum_price": maximum_price,
            "current_price": market_price,
            "price_gap": maximum_price / market_price - 1,
            "current_price_meets_hurdle": market_price <= maximum_price,
            "source_refs": sorted({
                *(ref for assumption in by_type.values() for ref in assumption.get("source_refs") or ()),
                *(ref for scenario_id in result_scenario_ids for ref in scenario_refs.get(str(scenario_id), ())),
            }),
        }
        unique[key] = {**row, "boundary_sha256": stable_sha256(row)}
    rows = sorted(unique.values(), key=lambda row: (row["maximum_price"], row["boundary_sha256"]))
    if not rows:
        raise ValueError("no declared cash-flow path admits the underwriting hurdle")
    prices = [float(row["maximum_price"]) for row in rows]
    body = {
        "schema": "jaggedthoughts-hurdle-price-frontier-v1",
        "entity_id": str(payload["entity_id"]),
        "evidence_epoch": str(payload["evidence_epoch"]),
        "risk_free_rate": risk_free,
        "excess_return_hurdle": hurdle,
        "required_total_return": required_return,
        "current_price": market_price,
        "cash_flow_boundaries": rows,
        "failed_cash_flow_paths": failures,
        "robust_maximum_price": min(prices),
        "median_maximum_price": median(prices),
        "optimistic_maximum_price": max(prices),
        "robust_price_gap": min(prices) / market_price - 1,
        "use_boundary": (
            "Each price is the maximum purchase price whose declared cash-flow path meets the excess-return "
            "hurdle over the matched risk-free rate. It is conditional on the frozen assumptions, not a target."
        ),
    }
    return {**body, "hurdle_price_frontier_sha256": stable_sha256(body)}


__all__ = [
    "ValuationAssumption",
    "ValuationEnvelope",
    "ExpectationsFrontierCertificate",
    "ExpectationsFrontierPoint",
    "ValuationProgramFailure",
    "ValuationProgramResult",
    "ValuationScenario",
    "build_valuation_grammar",
    "compile_hurdle_price_frontier",
    "compile_valuation_envelope",
    "present_value_owner_earnings",
    "solve_implied_growth",
    "valuation_grammar_contract",
]
