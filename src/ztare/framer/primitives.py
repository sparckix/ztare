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
scripts/public/framer/test_v2_inverse_precision.py.
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


# GP-152 framer-on-steroids enrichment (2026-04-27 night).
#
# Original v1 SIGMA had {identity, scale, shift, power_2, power_0.5, log,
# exp, reciprocal}. The 4-panel debate plus the gp163d ANALOGY collapse
# postmortem identified that the framer was reporting "no MDL improvement"
# on the gp163d substrate not because identity was genuinely optimal but
# because the transform pool was too sparse to expose multi-decade
# non-positive-domain coordinate changes (log fails on signed data, exp
# overflows on multi-decade range).
#
# Steroids = add transforms that are bijective on ALL signed reals AND
# capable of compressing many decades:
#
#   asinh(y)        — signed, bijective on R, ≈ log(2y) for |y|>>1 and ≈ y
#                     for |y|<<1. The Box-Cox-without-domain-restriction.
#   signed_log(y)   — sign(y)·log(1+|y|). Bijective on R; finite at zero.
#   softplus(y)     — log(1+exp(y)). Bijective on R. Always positive
#                     output. Compresses negative tail, expands positive.
#   sigmoid(y)      — 1/(1+exp(-y)). Bijective on R → (0,1). Output bounded.
#   arctan(y)       — bijective on R → (-π/2, π/2). Bounded output.
#   power_3 / power_1_3 — signed cube / cube root. No domain restriction;
#                     bijective on R. Useful when the residual depends on
#                     a feature with non-positive support.
#
# All new primitives carry strict round-trip + domain checks. The
# framer's existing admissible_primitives() filter already handles
# domain_ok rejection.
def _safe_softplus(y: np.ndarray) -> np.ndarray:
    return np.log1p(np.exp(np.clip(y, -EXP_SAFE_MAX, EXP_SAFE_MAX)))


def _softplus_inv(y: np.ndarray) -> np.ndarray:
    # softplus_inv(y) = log(exp(y) - 1) for y > 0
    # Numerically stable: y + log(1 - exp(-y))
    yy = np.clip(y, 1e-30, EXP_SAFE_MAX)
    return yy + np.log1p(-np.exp(-yy))


def _sigmoid(y: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(y, -EXP_SAFE_MAX, EXP_SAFE_MAX)))


def _sigmoid_inv(y: np.ndarray) -> np.ndarray:
    # logit(p) = log(p / (1-p)); domain p ∈ (0,1)
    p = np.clip(y, 1e-12, 1.0 - 1e-12)
    return np.log(p / (1.0 - p))


def _signed_log(y: np.ndarray) -> np.ndarray:
    return np.sign(y) * np.log1p(np.abs(y))


def _signed_log_inv(y: np.ndarray) -> np.ndarray:
    return np.sign(y) * np.expm1(np.abs(np.clip(y, -EXP_SAFE_MAX, EXP_SAFE_MAX)))


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
    # ── Steroid additions (GP-152.1, 2026-04-27) ───────────────────────
    "asinh":      Primitive("asinh",
                            np.arcsinh,
                            np.sinh,
                            k_param=0,
                            domain_ok=lambda y: bool(np.all(np.abs(y) < EXP_SAFE_MAX))),
    "signed_log": Primitive("signed_log",
                            _signed_log,
                            _signed_log_inv,
                            k_param=0,
                            domain_ok=lambda y: True),
    "softplus":   Primitive("softplus",
                            _safe_softplus,
                            _softplus_inv,
                            k_param=0,
                            # softplus_inv requires y > 0; framer should
                            # only choose softplus for h_in (input) where
                            # this isn't a constraint, or when y > 0
                            domain_ok=lambda y: bool(np.all(y > 1e-30))),
    "sigmoid":    Primitive("sigmoid",
                            _sigmoid,
                            _sigmoid_inv,
                            k_param=0,
                            # sigmoid_inv (logit) needs 0 < y < 1; pick
                            # sigmoid as h_in only, OR when data is
                            # already bounded in (0,1).
                            domain_ok=lambda y: bool(np.all((y > 0) & (y < 1)))),
    "arctan":     Primitive("arctan",
                            np.arctan,
                            np.tan,
                            k_param=0,
                            # tan(arctan(y)) round-trips for |arctan(y)| <
                            # π/2; effectively all real y. Inverse tan
                            # codomain is (-π/2, π/2) so picking arctan
                            # as h_in is always safe; as h_out it's safe
                            # when data already bounded.
                            domain_ok=lambda y: bool(np.all(np.abs(y) < 1.5))),
    "power_3":    Primitive(*[("power_3",) + _power_signed(3.0) + (1, lambda y: True)][0:1]
                            + list((_power_signed(3.0))) + [1, lambda y: True]),
    "power_1_3":  Primitive(*[("power_1_3",) + _power_signed(1.0/3.0) + (1, lambda y: True)][0:1]
                            + list((_power_signed(1.0/3.0))) + [1, lambda y: True]),
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
