"""PDE proof-currency facade."""
from __future__ import annotations

from typing import Any

from ztare.research_director.pde_currency_ledger import (
    DEFAULT_EXCHANGE_RATES,
    currency_ledger_template,
)


def pde_currency_ledger_template(target_currency: str | None = None) -> dict[str, Any]:
    """Return the PDE currency ledger template for one target currency."""
    return currency_ledger_template(target_currency)


def pde_exchange_rate_obligations() -> dict[str, str]:
    """Return named PDE exchange-rate obligations."""
    return dict(DEFAULT_EXCHANGE_RATES)


def missing_pde_exchange_obligations(
    required: list[str] | tuple[str, ...],
    available: dict[str, Any] | None = None,
) -> list[str]:
    """Return required exchange obligations not supplied by an available map."""
    available = available or {}
    return [
        str(name) for name in required
        if not available.get(str(name))
    ]
