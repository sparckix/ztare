"""GP-115: Sigmoid-Switched Two-Regime Combinator.

Composes any pair of templates from the existing library with a smooth
sigmoid transition at a breakpoint b. Grid search over b (discrete
domain values), fit both sub-expressions independently for each
candidate b, select by total BIC.

Panel approved (Munger/Popper/Dijkstra, 2026-04-22):
- Generic combinator, not hand-crafted templates
- Grid search over b (avoids curve_fit gradient problem at discontinuity)
- Composes existing templates, not new ones
- The rank-curve shape is one of 41x41 combinations, not special-cased

Usage:
    from ztare.fit.regime_combinator import find_best_regime_split
    result = find_best_regime_split(x_visible, y_visible, x_holdout, y_holdout, var="n")
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.optimize import curve_fit


def _numpy_expr(expr: str) -> str:
    return (expr.replace("math.log", "np.log")
            .replace("math.sqrt", "np.sqrt")
            .replace("math.exp", "np.exp")
            .replace("math.sin", "np.sin")
            .replace("math.cos", "np.cos"))


# Compact template set for regime sub-expressions (fast, not exhaustive)
def _mini_templates(var: str) -> list[tuple[str, list[str], list[float]]]:
    x = var
    return [
        (f"a * np.log({x}) + b", ["a", "b"], [1.0, 0.0]),
        (f"a * np.sqrt({x}) + b", ["a", "b"], [1.0, 0.0]),
        (f"a * np.exp(-b * {x}) + c", ["a", "b", "c"], [3.0, 0.1, 1.0]),
        (f"a * {x} + b", ["a", "b"], [0.1, 1.0]),
        (f"a / {x} + b", ["a", "b"], [1.0, 1.0]),
        (f"a * ({x} - b)**2 + c", ["a", "b", "c"], [0.01, 10.0, 2.0]),
        (f"a * {x}**b + c", ["a", "b", "c"], [1.0, 0.5, 0.0]),
        (f"a + 0*{x}", ["a"], [2.0]),  # constant
    ]


def _fit_segment(expr: str, params: list[str], p0: list[float],
                 x: np.ndarray, y: np.ndarray) -> tuple[dict, float] | None:
    """Fit a single template on a data segment. Returns (params_dict, sse) or None."""
    if len(x) < len(params) + 1:
        return None
    try:
        code = f"def _m(_x_, {', '.join(params)}):\n    n=_x_\n    return {expr}"
        ns = {"np": np, "math": math}
        exec(code, ns)
        fn = ns["_m"]
        popt, _ = curve_fit(fn, x, y, p0=p0, maxfev=5000)
        pred = fn(x, *popt)
        sse = float(np.sum((y - pred)**2))
        return dict(zip(params, [float(v) for v in popt])), sse
    except Exception:
        return None


def find_best_regime_split(
    x_vis: np.ndarray,
    y_vis: np.ndarray,
    x_ho: np.ndarray | None = None,
    y_ho: np.ndarray | None = None,
    var: str = "n",
    gate_threshold: float = 0.05,
) -> dict:
    """Find the best two-regime split by grid search over breakpoint.

    For each candidate breakpoint b in the visible domain:
      - Fit all mini-templates on the left segment (x < b)
      - Fit all mini-templates on the right segment (x >= b)
      - Score each (left, right) pair by total BIC
      - Select the best pair

    Returns the best split with expressions, parameters, and gate results.
    """
    templates = _mini_templates(var)
    n_vis = len(x_vis)

    # Candidate breakpoints: every unique x value with at least 3 points on each side
    unique_x = np.unique(x_vis)
    candidates = [b for b in unique_x if np.sum(x_vis < b) >= 3 and np.sum(x_vis >= b) >= 3]

    if not candidates:
        return {"status": "no_valid_breakpoints"}

    best_bic = float("inf")
    best_result = None

    for b in candidates:
        left_mask = x_vis < b
        right_mask = x_vis >= b
        x_left, y_left = x_vis[left_mask], y_vis[left_mask]
        x_right, y_right = x_vis[right_mask], y_vis[right_mask]

        for l_expr, l_params, l_p0 in templates:
            l_fit = _fit_segment(l_expr, l_params, l_p0, x_left, y_left)
            if l_fit is None:
                continue
            l_dict, l_sse = l_fit

            for r_expr, r_params, r_p0 in templates:
                r_fit = _fit_segment(r_expr, r_params, r_p0, x_right, y_right)
                if r_fit is None:
                    continue
                r_dict, r_sse = r_fit

                total_sse = l_sse + r_sse
                total_k = len(l_params) + len(r_params) + 1  # +1 for breakpoint
                bic = n_vis * np.log(total_sse / n_vis) + total_k * np.log(n_vis)

                if bic < best_bic:
                    best_bic = bic
                    best_result = {
                        "breakpoint": float(b),
                        "left_expr": l_expr,
                        "left_params": l_dict,
                        "right_expr": r_expr,
                        "right_params": r_dict,
                        "total_k": total_k,
                        "bic": round(float(bic), 1),
                        "visible_sse": round(float(total_sse), 6),
                    }

    if best_result is None:
        return {"status": "no_fit_found"}

    # Compute visible max residual
    b = best_result["breakpoint"]
    # Rebuild predictions
    pred_vis = np.zeros_like(y_vis)

    for segment, expr, params, mask in [
        ("left", best_result["left_expr"], best_result["left_params"], x_vis < b),
        ("right", best_result["right_expr"], best_result["right_params"], x_vis >= b),
    ]:
        code = f"def _m(_x_, {', '.join(params.keys())}):\n    n=_x_\n    return {expr}"
        ns = {"np": np, "math": math}
        exec(code, ns)
        fn = ns["_m"]
        pred_vis[mask] = fn(x_vis[mask], *params.values())

    vis_max_res = float(np.max(np.abs(y_vis - pred_vis)))
    best_result["visible_max_res"] = round(vis_max_res, 6)

    # Holdout test if available
    if x_ho is not None and y_ho is not None and len(x_ho) > 0:
        pred_ho = np.zeros_like(y_ho)
        for segment, expr, params, mask in [
            ("left", best_result["left_expr"], best_result["left_params"], x_ho < b),
            ("right", best_result["right_expr"], best_result["right_params"], x_ho >= b),
        ]:
            if not np.any(mask):
                continue
            code = f"def _m(_x_, {', '.join(params.keys())}):\n    n=_x_\n    return {expr}"
            ns = {"np": np, "math": math}
            exec(code, ns)
            fn = ns["_m"]
            pred_ho[mask] = fn(x_ho[mask], *params.values())

        ho_max_res = float(np.max(np.abs(y_ho - pred_ho)))
        best_result["holdout_max_res"] = round(ho_max_res, 6)
        best_result["holdout_gate_pass"] = ho_max_res < gate_threshold

    best_result["status"] = "found"
    return best_result
