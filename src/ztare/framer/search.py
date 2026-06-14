"""GP-152 Framer — BranchAndBoundMDLSearch (v2.0).

Computes MDL_v2.0 = N · log(σ̂²_raw) + K_total · log(N), where σ̂²_raw is
the residual variance in RAW y coordinates after fitting the law in framed
coords and inverting the prediction:

    σ̂²_raw = Var( y - h_out⁻¹( f̂( h_in(x) ) ) )

This is frame-invariant by construction (proof: spec v2.0 §3, backtest:
scripts/public/framer/backtest_framer_mdl_v2_vs_v1.py).

No Jacobian. No σ_noise floor. No log-J clip. No ε-perturbation rank check.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

import numpy as np

from .primitives import Primitive, admissible_primitives

# Polynomial degree for the framed-coord fit (controls K_law)
DEFAULT_FIT_DEGREE = 3
# σ̂² floor — guards against numerical zero-residual collapse on noiseless data
SIGMA_SQ_FLOOR = 1e-30
# Top-K candidates carried into depth-2 expansion
TOP_K_DEPTH1 = 5


@dataclass(frozen=True)
class CandidatePair:
    h_in: Primitive
    h_out: Primitive

    @property
    def k_total_primitives(self) -> int:
        return self.h_in.k_param + self.h_out.k_param

    def label(self) -> str:
        return f"{self.h_in.name}/{self.h_out.name}"


@dataclass(frozen=True)
class MDLResult:
    pair: CandidatePair
    mdl: float
    sigma_sq_raw: float
    k_law: int

    def label(self) -> str:
        return self.pair.label()


def _fit_polynomial_in_framed(x_framed: np.ndarray, y_framed: np.ndarray, deg: int):
    """Fit polynomial in normalized framed coords. Returns (coeffs, x_mean, x_std)."""
    x_mean = float(np.mean(x_framed))
    x_std = float(np.std(x_framed)) or 1.0
    xn = (x_framed - x_mean) / x_std
    coeffs = np.polyfit(xn, y_framed, deg)
    return coeffs, x_mean, x_std


def _predict_raw(
    x: np.ndarray,
    pair: CandidatePair,
    coeffs: np.ndarray,
    x_mean: float,
    x_std: float,
) -> np.ndarray:
    """Compose: x → h_in(x) → poly_fit → h_out⁻¹ → raw_y."""
    x_framed = pair.h_in.h(x)
    xn = (x_framed - x_mean) / x_std
    y_framed_pred = np.polyval(coeffs, xn)
    return pair.h_out.h_inv(y_framed_pred)


def evaluate_pair(
    x: np.ndarray,
    y: np.ndarray,
    pair: CandidatePair,
    deg: int = DEFAULT_FIT_DEGREE,
) -> Optional[MDLResult]:
    """Compute MDL_v2 for one (h_in, h_out) pair. Returns None if pair is
    inadmissible on this data (domain failure or NaN/Inf in fit/predict).
    """
    if not pair.h_in.domain_ok(x):
        return None
    if not pair.h_out.domain_ok(y):
        return None
    try:
        x_framed = pair.h_in.h(x)
        y_framed = pair.h_out.h(y)
        if not np.all(np.isfinite(x_framed)) or not np.all(np.isfinite(y_framed)):
            return None
        coeffs, x_mean, x_std = _fit_polynomial_in_framed(x_framed, y_framed, deg)
        y_raw_pred = _predict_raw(x, pair, coeffs, x_mean, x_std)
        if not np.all(np.isfinite(y_raw_pred)):
            return None
        residuals = y - y_raw_pred
        sigma_sq = max(float(np.var(residuals)), SIGMA_SQ_FLOOR)
    except Exception:
        return None
    n = len(y)
    k_law = deg + 1
    k_total = k_law + pair.k_total_primitives
    mdl = n * math.log(sigma_sq) + k_total * math.log(n)
    return MDLResult(pair=pair, mdl=mdl, sigma_sq_raw=sigma_sq, k_law=k_law)


def evaluate_all_pairs(
    x: np.ndarray,
    y: np.ndarray,
    primitives: Iterable[Tuple[str, Primitive]],
    deg: int = DEFAULT_FIT_DEGREE,
) -> List[MDLResult]:
    """Evaluate every (h_in, h_out) cross-product. Sort ascending by MDL."""
    prim_list = list(primitives)
    results: List[MDLResult] = []
    for _, hi in prim_list:
        for _, ho in prim_list:
            r = evaluate_pair(x, y, CandidatePair(h_in=hi, h_out=ho), deg=deg)
            if r is not None:
                results.append(r)
    results.sort(key=lambda r: r.mdl)
    return results


def branch_and_bound_search(
    x: np.ndarray,
    y: np.ndarray,
    deg: int = DEFAULT_FIT_DEGREE,
    top_k: int = TOP_K_DEPTH1,
) -> List[MDLResult]:
    """Depth-1 branch-and-bound over admissible Σ × Σ.

    v2.0 spec: complete enumeration at depth 1 (≤ |Σ|² candidates), top-K
    expanded to depth 2. For now, depth 1 only — depth-2 composition is a
    follow-up that requires composing primitives into new (h, h_inv) pairs.

    Returns the sorted list of admissible MDLResults; the first is the best.
    """
    admissible = admissible_primitives(y).items()
    return evaluate_all_pairs(x, y, admissible, deg=deg)
