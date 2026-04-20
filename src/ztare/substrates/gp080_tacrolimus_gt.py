"""GP-080 Ground Truth — Division A artifact.

Population PK parameters from Størset et al. 2019 (typical adult values).
Exports f_true(x1, x2) -> float and evidence grids for generate_substrate.

Variable naming (Division A internal only — Division B sees x1, x2):
  x1 = time post-dose (hours)
  x2 = administered dose (mg)
  z  = whole-blood concentration (ng/mL)

Model: 1-compartment oral absorption (linearised from 2-compartment for identifiability).
  C(t, dose) = (F * dose / V) * (ka / (ka - ke)) * (exp(-ke*t) - exp(-ka*t))

Division B never reads this file. All domain names live here only.
"""
from __future__ import annotations

import math

# ── Population PK parameters (Størset 2019 / standard adult priors) ──────────
_KA = 1.5      # absorption rate constant (h⁻¹)
_KE = 0.07     # elimination rate constant (h⁻¹)
_F  = 0.25     # bioavailability fraction (dimensionless)
_V  = 300.0    # apparent volume of distribution (L)


_MG_L_TO_NG_ML = 1000.0  # unit conversion: 1 mg/L = 1000 ng/mL


def f_true(x1: float, x2: float) -> float:
    """Return whole-blood concentration (ng/mL) at time x1 (h) for dose x2 (mg).

    Variable names are intentionally opaque (x1, x2) for Division B compatibility.
    Formula gives mg/L; multiply by 1000 to convert to ng/mL.
    """
    t, dose = x1, x2
    if t <= 0:
        return 0.0
    scale = (_F * dose / _V) * (_KA / (_KA - _KE))
    return _MG_L_TO_NG_ML * scale * (math.exp(-_KE * t) - math.exp(-_KA * t))


def f_dominant(x1: float, x2: float) -> float:
    """Dominant (elimination) phase only — used by Component C."""
    t, dose = x1, x2
    if t <= 0:
        return 0.0
    scale = (_F * dose / _V) * (_KA / (_KA - _KE))
    return _MG_L_TO_NG_ML * scale * math.exp(-_KE * t)


# ── Evidence grids ─────────────────────────────────────────────────────────────
# Non-uniform time grid (standard clinical PK sampling schedule).
# Division B sees opaque (x1, x2, z) triples — no labels, no units.

_VISIBLE_TIMES  = [0.5, 1.0, 2.0, 4.0, 6.0, 8.0, 12.0, 24.0]   # hours
_VISIBLE_DOSES  = [1.0, 3.0, 5.0]                                  # mg
_HOLDOUT_DOSES  = [2.0, 4.0]                                        # mg (unseen)
_HOLDOUT_EXTRA_TIMES = [3.0, 10.0, 18.0]                           # sparse, dose=3


def evidence_grid() -> list[tuple[float, float]]:
    """Return (x1, x2) pairs for the visible evidence set (24 points)."""
    pairs = []
    for dose in _VISIBLE_DOSES:
        for t in _VISIBLE_TIMES:
            pairs.append((t, dose))
    return pairs


def holdout_grid() -> list[tuple[float, float]]:
    """Return (x1, x2) pairs for the holdout set (22 points)."""
    pairs = []
    # unseen doses, full time grid
    for dose in _HOLDOUT_DOSES:
        for t in _VISIBLE_TIMES:
            pairs.append((t, dose))
    # sparse times at dose=3 (same dose as visible, unseen time points)
    for t in _HOLDOUT_EXTRA_TIMES:
        pairs.append((t, 3.0))
    return pairs


if __name__ == "__main__":
    print("GP-080 GT verification (Division A)")
    print(f"Parameters: ka={_KA}, ke={_KE}, F={_F}, V={_V}")
    print()
    print("Visible grid sample:")
    for x1, x2 in evidence_grid()[:6]:
        z = f_true(x1, x2)
        print(f"  x1={x1:5.1f}  x2={x2:.0f}  z={z:.4f}")
    print(f"  ... ({len(evidence_grid())} total)")
    print()
    print("Holdout grid sample:")
    for x1, x2 in holdout_grid()[:6]:
        z = f_true(x1, x2)
        print(f"  x1={x1:5.1f}  x2={x2:.0f}  z={z:.4f}")
    print(f"  ... ({len(holdout_grid())} total)")
