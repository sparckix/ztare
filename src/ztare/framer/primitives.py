"""GP-152 Framer Σ primitive registry.

Σ = {identity, shift, scale, power_k, log, exp, reciprocal}

Each primitive carries:
  - h:        forward transformation y → h(y)
  - h_inv:    inverse transformation h(y) → y (must be exact in float64)
  - k_param:  description-length cost (1 per scalar parameter, 0 for parameter-free)
  - domain_ok(y_array) -> bool: precondition check (e.g., y > 0 for log)

The Framer rejects pairs whose (h, h_inv) round-trip exceeds 1e-8 max relative
error on the data range, OR whose domain_ok fails on the data. This blocks the
power_2/asinh and exp-overflow failure modes surfaced by
scripts/framer/test_v2_inverse_precision.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict

import numpy as np

# Round-trip tolerance: max |h_inv(h(y)) - y| / max(|y|, 1)
ROUNDTRIP_RTOL = 1e-8

# Max safe exp argument to avoid float64 overflow (exp(700) ≈ 1e304)
EXP_SAFE_MAX = 50.0


@dataclass
class Primitive:
    name: str
    h: Callable[[np.ndarray], np.ndarray]
    h_inv: Callable[[np.ndarray], np.ndarray]
    k_param: int
    domain_ok: Callable[[np.ndarray], bool]


def _no_zero(y: np.ndarray) -> np.ndarray:
    """Avoid division-by-zero by clamping near-zero values."""
    eps = 1e-30
    return np.where(np.abs(y) < eps, np.sign(y) * eps + (y == 0) * eps, y)


def _safe_log(y: np.ndarray) -> np.ndarray:
    return np.log(np.abs(y) + 1e-30)


def _safe_exp(y: np.ndarray) -> np.ndarray:
    return np.exp(np.clip(y, -EXP_SAFE_MAX, EXP_SAFE_MAX))


def _power_signed(p: float):
    """Sign-preserving power: sign(y) · |y|^p. Bijective on signed reals for p>0."""
    def fwd(y):
        return np.sign(y) * np.abs(y) ** p
    def inv(y):
        return np.sign(y) * np.abs(y) ** (1.0 / p)
    return fwd, inv


# Σ registry
SIGMA: Dict[str, Primitive] = {
    "identity":   Primitive("identity",
                            lambda y: y,
                            lambda y: y,
                            k_param=0,
                            domain_ok=lambda y: True),
    "scale":      Primitive("scale",  # parameterized; depth-1 use only
                            lambda y: 2.0 * y,    # default c=2; search would vary
                            lambda y: y / 2.0,
                            k_param=1,
                            domain_ok=lambda y: True),
    "shift":      Primitive("shift",
                            lambda y: y + 1.0,    # default b=1; search would vary
                            lambda y: y - 1.0,
                            k_param=1,
                            domain_ok=lambda y: True),
    "power_2":    Primitive(*[("power_2",) + _power_signed(2.0) + (1, lambda y: True)][0:1]
                            + list((_power_signed(2.0))) + [1, lambda y: True]),
    "power_0.5":  Primitive(*[("power_0.5",) + _power_signed(0.5) + (1, lambda y: True)][0:1]
                            + list((_power_signed(0.5))) + [1, lambda y: True]),
    "log":        Primitive("log",
                            _safe_log,
                            _safe_exp,
                            k_param=0,
                            domain_ok=lambda y: bool(np.all(y > 0))),
    "exp":        Primitive("exp",
                            _safe_exp,
                            _safe_log,
                            k_param=0,
                            # exp domain restriction: input must stay below EXP_SAFE_MAX
                            domain_ok=lambda y: bool(np.all(np.abs(y) < EXP_SAFE_MAX))),
    "reciprocal": Primitive("reciprocal",
                            lambda y: 1.0 / _no_zero(y),
                            lambda y: 1.0 / _no_zero(y),
                            k_param=0,
                            domain_ok=lambda y: bool(np.all(np.abs(y) > 1e-10))),
}


def roundtrip_ok(p: Primitive, y: np.ndarray) -> bool:
    """Verify h_inv(h(y)) ≈ y to ROUNDTRIP_RTOL on this data."""
    if not p.domain_ok(y):
        return False
    try:
        y_back = p.h_inv(p.h(y))
        denom = np.maximum(np.abs(y), 1.0)
        rel_err = float(np.max(np.abs((y_back - y) / denom)))
        return rel_err < ROUNDTRIP_RTOL
    except Exception:
        return False


def admissible_primitives(y: np.ndarray) -> Dict[str, Primitive]:
    """Filter SIGMA to primitives whose round-trip is exact on this data."""
    return {name: p for name, p in SIGMA.items() if roundtrip_ok(p, y)}


def _self_test() -> None:
    """Smoke test — verify each Σ primitive round-trips on its valid domain."""
    test_cases = {
        "identity":   np.linspace(-50, 50, 50),
        "scale":      np.linspace(-50, 50, 50),
        "shift":      np.linspace(-50, 50, 50),
        "power_2":    np.linspace(-10, 10, 50),
        "power_0.5":  np.linspace(-10, 10, 50),
        "log":        np.linspace(0.1, 100, 50),
        "exp":        np.linspace(-10, 10, 50),
        "reciprocal": np.linspace(0.5, 5, 50),
    }
    print("Σ primitive round-trip self-test:")
    for name, y in test_cases.items():
        p = SIGMA[name]
        ok = roundtrip_ok(p, y)
        print(f"  {name:12s} {'OK' if ok else 'FAIL'}")
        assert ok, f"{name} failed round-trip"
    print("All Σ primitives round-trip OK on valid domains.")


if __name__ == "__main__":
    _self_test()
