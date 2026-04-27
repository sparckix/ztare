"""GP-152 Framer solver wrapper — `fit_with_framer()` (v2.0).

Public API:
  fit_with_framer(fit_fn, x, y, meta, rubric_data) -> (fit_result, framing_report)

This is the integration boundary between the existing fit_primitive pipeline
and the Framer. When `enable_framer=True` in the rubric AND scope checks pass,
the Framer transforms (x, y) → (framed_x, framed_y) and the solver runs in
framed coords. The fit_result.coefficients are reported in framed coords;
to get raw-coord predictions, the caller should compose via h_out_inv.

When `enable_framer=False` or scope checks fail, this is a pass-through
to fit_fn(x, y) with no framing.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple

import numpy as np

from .active_framer import frame


def fit_with_framer(
    fit_fn: Callable[[np.ndarray, np.ndarray], Any],
    x: np.ndarray,
    y: np.ndarray,
    meta: Optional[Dict[str, Any]] = None,
    rubric_data: Optional[Dict[str, Any]] = None,
) -> Tuple[Any, Dict[str, Any]]:
    """Wrap a solver fit call with Framer pre-processing (when enabled).

    Returns (fit_result, framing_report). The fit_result is in framed coords;
    framing_report["h_out_inv"] tells the caller how to recover raw-coord
    predictions.
    """
    rubric_data = rubric_data or {}
    if not rubric_data.get("enable_framer", False):
        return fit_fn(x, y), {"framer_engaged": False, "disabled_reason": "rubric_flag_off"}

    framed_x, framed_y, framing_report = frame(
        x=x, y=y,
        meta=meta or {},
        rubric_data=rubric_data,
        fit_fn=fit_fn,
    )
    return fit_fn(framed_x, framed_y), framing_report
