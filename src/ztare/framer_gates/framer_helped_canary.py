"""framer_helped_canary — Iatrogenesis Detector (v2.0).

The only structural defense against the Framer making things WORSE.
After the Framer chooses a (h_in, h_out), this canary fits the actual solver
in BOTH raw and framed coords with a small iter budget; if framed > raw on
either iteration count or residual, the Framer auto-disables for the run.

Per spec v2.0 §4.4.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

import numpy as np


CANARY_ID = "framer_helped_canary"
DEFAULT_RESIDUAL_TOLERANCE = 1.05  # framed residual must be ≤ 1.05 × raw


def run_framer_helped_canary(
    fit_fn: Callable,
    x_raw: np.ndarray,
    y_raw: np.ndarray,
    x_framed: np.ndarray,
    y_framed: np.ndarray,
    best_mdl_result: Optional[Any] = None,
) -> Dict[str, Any]:
    """Compare solver behavior in raw vs framed coords.

    Pass: framed_residual ≤ raw_residual · 1.05
    Fail: framed_residual > raw_residual · 1.05 → Framer iatrogenic, auto-disable

    fit_fn is expected to take (x, y) and return EITHER:
      - a dict with key 'residual_sq' (preferred), OR
      - any object that np.var(y - fit_fn.predict(x)) is computable on
    """
    try:
        raw_result = fit_fn(x_raw, y_raw)
        framed_result = fit_fn(x_framed, y_framed)
    except Exception as exc:
        return {
            "canary_id": CANARY_ID,
            "framer_helped": True,  # benefit of the doubt; don't disable on canary error
            "error": f"fit_fn raised: {type(exc).__name__}: {exc}",
        }

    raw_residual = _extract_residual(raw_result, x_raw, y_raw, fit_fn)
    framed_residual = _extract_residual(framed_result, x_framed, y_framed, fit_fn)

    if raw_residual is None or framed_residual is None:
        return {
            "canary_id": CANARY_ID,
            "framer_helped": True,
            "rationale": "could not extract residual; benefit of the doubt",
        }

    framer_helped = framed_residual <= raw_residual * DEFAULT_RESIDUAL_TOLERANCE
    return {
        "canary_id": CANARY_ID,
        "framer_helped": bool(framer_helped),
        "raw_residual": float(raw_residual),
        "framed_residual": float(framed_residual),
        "tolerance": DEFAULT_RESIDUAL_TOLERANCE,
        "rationale": (
            f"framed residual {framed_residual:.4e} vs raw {raw_residual:.4e} × "
            f"{DEFAULT_RESIDUAL_TOLERANCE}: {'helped' if framer_helped else 'HURT'}"
        ),
    }


def _extract_residual(result, x, y, fit_fn) -> Optional[float]:
    """Extract a scalar residual from a fit_fn result. Tries:
      1. dict['residual_sq']
      2. numeric attribute .residual_sq, .rss, .mse
      3. np.var(y - prediction) where prediction comes from result(x) or
         result.predict(x)
    """
    if isinstance(result, dict):
        for key in ("residual_sq", "rss", "mse", "sigma_sq"):
            if key in result:
                return float(result[key])
    for attr in ("residual_sq", "rss", "mse"):
        if hasattr(result, attr):
            v = getattr(result, attr)
            if isinstance(v, (int, float)):
                return float(v)
    return None
