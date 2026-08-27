"""Private planning surface for the household-to-investment allocation boundary."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, require_finite, require_refs, require_text


HOUSEHOLD_INTAKE_SCHEMA = "jaggedthoughts-household-capital-intake-v1"
HOUSEHOLD_GOAL_SURFACE_SCHEMA = "jaggedthoughts-household-goal-surface-v1"


def _number(value: Any) -> float | None:
    if value is None or str(value).strip().lower() in {"", "unknown", "unresolved"}:
        return None
    return require_finite(value, "household intake amount")


def _rate(raw: Mapping[str, Any], currency: str) -> float:
    value = require_finite(raw.get(currency), f"fx_to_base.{currency}")
    if value <= 0:
        raise ValueError("FX rates must be positive")
    return value


def _terminal_wealth(start: float, contribution: float, annual_return: float, years: int) -> float:
    wealth = start
    for _ in range(years):
        wealth = wealth * (1 + annual_return) + contribution
    return wealth


def _required_return(start: float, contribution: float, target: float, years: int) -> float | None:
    if _terminal_wealth(start, contribution, 0, years) >= target:
        return 0.0
    low, high = 0.0, 1.0
    while _terminal_wealth(start, contribution, high, years) < target and high < 16:
        high *= 2
    if _terminal_wealth(start, contribution, high, years) < target:
        return None
    for _ in range(100):
        middle = (low + high) / 2
        if _terminal_wealth(start, contribution, middle, years) >= target:
            high = middle
        else:
            low = middle
    return high


def compile_household_goal_surface(
    intake: Mapping[str, Any], *, base_currency: str, fx_to_base: Mapping[str, Any],
    fx_source_refs: tuple[str, ...], as_of: str,
    horizon_grid: tuple[int, ...] = (15, 20, 25, 30),
    contribution_grid: tuple[float, ...] = (75_000, 100_000, 150_000),
) -> dict[str, Any]:
    """Turn partial private intake into a hurdle matrix and exact missing fields."""
    if intake.get("schema") != HOUSEHOLD_INTAKE_SCHEMA:
        raise ValueError(f"household intake schema must be {HOUSEHOLD_INTAKE_SCHEMA}")
    base = require_text(base_currency, "base_currency").upper()
    epoch = canonical_timestamp(as_of, "household goal surface as_of")
    fx_refs = require_refs(fx_source_refs, "household FX source refs")
    known_assets, known_liabilities = 0.0, 0.0
    investable_assets = 0.0
    asset_rows: list[dict[str, Any]] = []
    for row in intake.get("assets") or ():
        value = _number(row.get("value"))
        currency = str(row.get("currency") or "").upper()
        if value is None or not currency or currency == "UNRESOLVED":
            continue
        base_value = value * (1 if currency == base else _rate(fx_to_base, currency))
        known_assets += base_value
        asset_rows.append({
            "asset_id": str(row.get("asset_id") or ""),
            "kind": str(row.get("kind") or ""),
            "value": value,
            "currency": currency,
            "value_base": base_value,
        })
        if str(row.get("kind") or "") == "liquidity":
            investable_assets += base_value
    liability_rows: list[dict[str, Any]] = []
    for row in intake.get("liabilities") or ():
        value = _number(row.get("balance"))
        currency = str(row.get("currency") or "").upper()
        if value is None or not currency or currency == "UNRESOLVED":
            continue
        base_value = value * (1 if currency == base else _rate(fx_to_base, currency))
        known_liabilities += base_value
        liability_rows.append({
            "liability_id": str(row.get("liability_id") or ""),
            "kind": str(row.get("kind") or ""),
            "balance": value,
            "currency": currency,
            "balance_base": base_value,
            "annual_rate": _number(row.get("annual_rate")),
        })
    goal = dict(intake.get("goal") or {})
    target = _number(goal.get("target_net_worth"))
    target_currency = str(goal.get("currency") or "").upper()
    if target is None:
        raise ValueError("household goal target_net_worth must be known")
    if not target_currency or target_currency == "UNRESOLVED":
        # Hurdle grid is interpretable in the chosen base while goal currency stays a blocker.
        target_base = target
    else:
        target_base = target * (
            1 if target_currency == base else _rate(fx_to_base, target_currency)
        )

    rows = []
    for years in horizon_grid:
        if years < 1:
            raise ValueError("horizon grid must be positive")
        for annual_contribution in contribution_grid:
            if annual_contribution < 0:
                raise ValueError("contribution grid cannot be negative")
            rows.append({
                "horizon_years": years,
                "annual_contribution_base": annual_contribution,
                "required_constant_nominal_return": _required_return(
                    investable_assets, annual_contribution, target_base, years,
                ),
            })
    unresolved = sorted({
        str(value) for value in intake.get("known_but_not_yet_bound") or () if str(value)
    })
    body = {
        "schema": HOUSEHOLD_GOAL_SURFACE_SCHEMA,
        "as_of": epoch,
        "base_currency": base,
        "intake_sha256": stable_sha256(intake),
        "fx_to_base": {
            str(currency).upper(): require_finite(rate, f"fx_to_base.{currency}")
            for currency, rate in sorted(fx_to_base.items())
        },
        "fx_source_refs": list(fx_refs),
        "known_balance_sheet": {
            "known_assets_base": known_assets,
            "known_liabilities_base": known_liabilities,
            "known_net_position_base": known_assets - known_liabilities,
            "net_worth_base": None,
            "known_investable_liquidity_base": investable_assets,
            "assets": asset_rows,
            "liabilities": liability_rows,
            "complete": False,
        },
        "goal": {
            "target_base": target_base,
            "declared_currency": target_currency or None,
            "currency_resolved": bool(target_currency and target_currency != "UNRESOLVED"),
            "declared_basis": "net_worth",
            "hurdle_basis": "investable_portfolio_only",
            "nonportfolio_terminal_value_included": False,
        },
        "hurdle_matrix": rows,
        "readiness": {"complete": False, "missing": unresolved},
        "interpretation": (
            "Each cell is the constant nominal return required on current known investable "
            "liquidity plus the declared annual contribution. The full declared net-worth "
            "target is provisionally assigned to the portfolio because property value, debt "
            "amortization, and other terminal assets are unresolved. It is a conservative "
            "portfolio-only hurdle, not a forecast or a completed net-worth projection."
        ),
        "authority": "private_planning_projection_only",
        "capital_authority": False,
        "brokerage_authority": False,
    }
    return {**body, "surface_sha256": stable_sha256(body)}


def compile_private_household_workspace(
    intake_path: str | Path, *, fx_to_base: Mapping[str, Any], base_currency: str,
    fx_source_refs: tuple[str, ...], as_of: str,
    budget_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    raw = yaml.safe_load(Path(intake_path).expanduser().read_text(encoding="utf-8"))
    surface = compile_household_goal_surface(
        raw, base_currency=base_currency, fx_to_base=fx_to_base,
        fx_source_refs=fx_source_refs, as_of=as_of,
    )
    if budget_evidence is None:
        for candidate in raw.get("source_candidates") or ():
            if str(candidate.get("kind") or "") not in {
                "spreadsheet", "household_budget_workbook",
            }:
                continue
            try:
                from .household_budget_evidence import compile_household_budget_evidence
                budget_evidence = compile_household_budget_evidence(
                    candidate.get("path"), source_id=str(candidate.get("source_id") or "budget"),
                )
            except (KeyError, OSError, TypeError, ValueError):
                budget_evidence = {"status": "unavailable", "capital_authority": False}
            break
    body = dict(surface)
    body.pop("surface_sha256", None)
    body["budget_evidence"] = budget_evidence
    return {**body, "surface_sha256": stable_sha256(body)}


__all__ = [
    "HOUSEHOLD_GOAL_SURFACE_SCHEMA",
    "HOUSEHOLD_INTAKE_SCHEMA",
    "compile_household_goal_surface",
    "compile_private_household_workspace",
]
