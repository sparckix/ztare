"""Covenant-recompute RECHECK capability (PLUGIN) for the `activist-short` scenario. Re-executes the SEC-covenant
arithmetic from the issuer's filed line items and REPORTS whether the thesis's re-executable (W1) support holds
— the honest home for what the deleted `demo_activist.py` script wrongly bolted on. PURE: it reports pass/fail,
the recheck driver (`scenarios.warrant_recheck`) is the single writer, so the W1 warrant is minted by this check
re-running green, never by fiat. Deleting this file removes the capability with zero kernel change (the rot
test); the covenant math is settled, only the guided Q4 EBITDA input is contested (that is what the map's
management-guidance CONTRADICTS edge attacks — which is why the verdict stays CONTESTED, not settled)."""
from __future__ import annotations

from ztare.scenarios.registry import capability

# MFC Q3 FY25 Form 10-Q (period ended Sep 30, 2025), USD millions — the BOUND data (see projects/mfc_covenant_short
# /project_charter.md). Fictional issuer, internally-consistent numbers.
_Q3_TOTAL_DEBT = 980.0
_Q3_CASH = 45.0
_Q3_TTM_EBITDA = 217.0          # as filed => (980-45)/217 = 4.31x ~ the reported 4.3x
_COVENANT = 4.50                # Consolidated Net Leverage cap, 4.50:1.00, tested quarterly
_Q4_GUIDED_TTM_EBITDA = 202.0   # the company's own guided-softer freight-recession path


@capability("recheck", "covenant_recompute")
class CovenantRecompute:
    """Recompute MFC's net-leverage covenant and confirm (a) the arithmetic reproduces the as-filed 4.3x and
    (b) the guided-softer Q4 path breaches 4.50x. A PASS licenses W1 on the recompute→thesis support edge."""

    name = "covenant_recompute"

    def recheck(self, project: str) -> "dict":
        net_debt = _Q3_TOTAL_DEBT - _Q3_CASH
        current = net_debt / _Q3_TTM_EBITDA
        projected = net_debt / _Q4_GUIDED_TTM_EBITDA
        passed = abs(current - 4.3) < 0.05 and projected > _COVENANT
        text = (f"Recomputed from the Q3 FY25 10-Q: net leverage = ({_Q3_TOTAL_DEBT:.0f}-{_Q3_CASH:.0f})/EBITDA; "
                f"reproduces the filed {current:.2f}x at ${_Q3_TTM_EBITDA:.0f}M TTM EBITDA and rises to "
                f"{projected:.2f}x on the guided ${_Q4_GUIDED_TTM_EBITDA:.0f}M Q4 path — above the "
                f"{_COVENANT:.2f}x covenant.")
        return {"passed": passed, "warrant": "W1",
                "target": {"src": "ev.recheck.covenant_recompute", "kind": "SUPPORTS", "dst": "thesis", "text": text},
                "detail": f"current {current:.2f}x, projected {projected:.2f}x vs covenant {_COVENANT:.2f}x"}
