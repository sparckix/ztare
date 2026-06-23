"""GP-115: Residual-Driven Grammar Expansion (Layer 1).

Analyzes residual structure from a failed compression and suggests
missing templates mechanically. No LLM, no operator judgment.

The residual signature IS the specification for the missing template.

Usage:
    from ztare.fit.residual_grammar_expander import suggest_from_residuals
    suggestions = suggest_from_residuals(residuals, x_values, var="n")
"""

from __future__ import annotations

import math
import numpy as np
from scipy.optimize import curve_fit
from scipy.stats import linregress


def suggest_from_residuals(
    residuals: np.ndarray,
    x_values: np.ndarray,
    var: str = "n",
    min_improvement: float = 1.5,
) -> list[dict]:
    """Analyze residual structure and suggest missing templates.

    Returns a list of dicts with keys: name, expression, params, rationale.
    Each suggestion is a template the grammar is missing, diagnosed from
    the residual pattern.
    """
    suggestions = []

    # 1. Reciprocal envelope: do residuals scale as ~1/n?
    sig = _check_reciprocal_envelope(residuals, x_values, var)
    if sig:
        suggestions.append(sig)

    # 2. Shifted reciprocal: monotone decay with nonzero asymptote
    sig = _check_shifted_reciprocal(residuals, x_values, var)
    if sig:
        suggestions.append(sig)

    # 3. Log-quadratic: do residuals have curvature in log(n)?
    sig = _check_log_quadratic(residuals, x_values, var)
    if sig:
        suggestions.append(sig)

    # 4. Exponential decay in residuals
    sig = _check_exp_decay(residuals, x_values, var)
    if sig:
        suggestions.append(sig)

    # 5. Power-law envelope: residuals scale as n^(-alpha)
    sig = _check_power_envelope(residuals, x_values, var)
    if sig:
        suggestions.append(sig)

    # 6. U-shape / parabolic: residuals have a minimum in the interior
    sig = _check_parabolic(residuals, x_values, var)
    if sig:
        suggestions.append(sig)

    # 7. Log-convergent: residuals fit a/log(n) + b (Mertens-type convergence)
    sig = _check_log_convergent(residuals, x_values, var)
    if sig:
        suggestions.append(sig)

    return suggestions


def _fit_improvement(residuals: np.ndarray, x: np.ndarray,
                     model_fn, p0: list, n_params: int) -> float:
    """Return the improvement ratio: original_rms / fitted_rms."""
    try:
        popt, _ = curve_fit(model_fn, x, residuals, p0=p0, maxfev=5000)
        fitted = model_fn(x, *popt)
        rms_before = np.sqrt(np.mean(residuals**2))
        rms_after = np.sqrt(np.mean((residuals - fitted)**2))
        if rms_after < 1e-15:
            return 999.0
        return rms_before / rms_after
    except Exception:
        return 1.0


def _check_reciprocal_envelope(r: np.ndarray, x: np.ndarray, var: str) -> dict | None:
    """Check if |residuals| ~ a/n."""
    abs_r = np.abs(r)
    try:
        def model(n, a, b):
            return a / n + b
        improvement = _fit_improvement(abs_r, x, model, [1.0, 0.0], 2)
        if improvement > 1.5:
            return {
                "name": "auto_reciprocal",
                "expression": f"a / {var} + b",
                "params": ["a", "b"],
                "rationale": f"Residual amplitude scales as 1/n (improvement {improvement:.1f}x)",
                "improvement": round(improvement, 2),
            }
    except Exception:
        pass
    return None


def _check_shifted_reciprocal(r: np.ndarray, x: np.ndarray, var: str) -> dict | None:
    """Check if residuals fit a/(n+b) + c."""
    try:
        def model(n, a, b, c):
            return a / (n + b) + c
        improvement = _fit_improvement(r, x, model, [1.0, 100.0, 0.0], 3)
        if improvement > 1.5:
            return {
                "name": "auto_shifted_reciprocal",
                "expression": f"a / ({var} + b) + c",
                "params": ["a", "b", "c"],
                "rationale": f"Residuals fit shifted reciprocal (improvement {improvement:.1f}x)",
                "improvement": round(improvement, 2),
            }
    except Exception:
        pass
    return None


def _check_log_quadratic(r: np.ndarray, x: np.ndarray, var: str) -> dict | None:
    """Check if residuals have curvature in log(n)."""
    log_x = np.log(x)
    try:
        def model(log_n, a, b):
            return a * log_n**2 + b
        improvement = _fit_improvement(r, log_x, model, [0.001, 0.0], 2)
        if improvement > 1.5:
            return {
                "name": "auto_log_squared",
                "expression": f"a * math.log({var})**2 + b",
                "params": ["a", "b"],
                "rationale": f"Residuals have log-quadratic curvature (improvement {improvement:.1f}x)",
                "improvement": round(improvement, 2),
            }
    except Exception:
        pass
    return None


def _check_exp_decay(r: np.ndarray, x: np.ndarray, var: str) -> dict | None:
    """Check if residuals decay exponentially."""
    try:
        def model(n, a, b, c):
            return a * np.exp(-b * n) + c
        improvement = _fit_improvement(r, x, model, [1.0, 0.001, 0.0], 3)
        if improvement > 1.5:
            return {
                "name": "auto_exp_decay",
                "expression": f"a * math.exp(-b * {var}) + c",
                "params": ["a", "b", "c"],
                "rationale": f"Residuals decay exponentially (improvement {improvement:.1f}x)",
                "improvement": round(improvement, 2),
            }
    except Exception:
        pass
    return None


def _check_power_envelope(r: np.ndarray, x: np.ndarray, var: str) -> dict | None:
    """Check if |residuals| ~ a * n^(-alpha)."""
    abs_r = np.abs(r)
    # Avoid zeros
    mask = abs_r > 0
    if mask.sum() < 10:
        return None
    try:
        log_x = np.log(x[mask])
        log_r = np.log(abs_r[mask])
        slope, intercept, rv, _, _ = linregress(log_x, log_r)
        if rv**2 > 0.5 and slope < -0.3:
            return {
                "name": "auto_power_decay",
                "expression": f"a * {var}**(-b) + c",
                "params": ["a", "b", "c"],
                "rationale": f"Residual amplitude ~ n^({slope:.2f}), R2={rv**2:.2f}",
                "improvement": round(rv**2 * 3, 2),  # rough proxy
            }
    except Exception:
        pass
    return None


def _check_parabolic(r: np.ndarray, x: np.ndarray, var: str) -> dict | None:
    """Check if data has a U-shape (minimum in the interior)."""
    try:
        def model(n, a, b, c):
            return a * (n - b)**2 + c
        improvement = _fit_improvement(r, x, model, [0.01, np.mean(x), np.min(r)], 3)
        if improvement > 1.5:
            return {
                "name": "auto_parabolic",
                "expression": f"a * ({var} - b)**2 + c",
                "params": ["a", "b", "c"],
                "rationale": f"Data has U-shaped / parabolic structure (improvement {improvement:.1f}x)",
                "improvement": round(improvement, 2),
            }
    except Exception:
        pass
    return None


def _check_log_convergent(r: np.ndarray, x: np.ndarray, var: str) -> dict | None:
    """Check if residuals fit a/log(n) + b (Mertens / abundant density convergence).

    Triggered when a slowly-converging series approaches a constant and the
    leading correction is 1/log(n) rather than 1/n.  Fires when improvement
    over the flat baseline exceeds min_improvement.
    """
    # Guard: log(x) must be defined (x > 1)
    if np.any(x <= 1):
        return None
    try:
        def model(n, a, b):
            return a / np.log(n) + b
        improvement = _fit_improvement(r, x, model, [0.1, 0.0], 2)
        if improvement > 1.5:
            return {
                "name": "auto_log_convergent",
                "expression": f"a / math.log({var}) + b",
                "params": ["a", "b"],
                "rationale": f"Residuals fit 1/log(n) log-convergent form (improvement {improvement:.1f}x)",
                "improvement": round(improvement, 2),
            }
    except Exception:
        pass
    return None
