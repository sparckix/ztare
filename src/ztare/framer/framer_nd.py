"""GP-152/GP-164 N-D framer adapter.

The 1D framer in `active_framer.py` accepts (x, y) numpy arrays and
returns (framed_x, framed_y, report). N-D substrates (gp154, gp155,
gp156, gp158, gp163d, ...) carry feature-DICT rows: each row is a
`features: dict` plus a scalar `y_observed`. The 1D framer cannot
consume that shape directly.

This adapter projects a feature-dict substrate onto a 1D (x, y)
projection along a single declared "primary feature key," runs the
1D framer on the projection, and returns the framing report. Other
features pass through unchanged in the substrate's own data structure;
the framer's recommendation applies only to the primary axis.

Operator contract:

  * Rubric flag `framer_primary_feature_key` (string) selects the
    feature to project on. If absent, the adapter heuristically picks
    the feature with the most distinct numeric values among rows.
  * The framer runs in OBSERVE mode (the same mode the 1D path
    defaults to). The framing_report is written to
    `workspace/framing_report.json`; it does NOT modify the data flow
    into the fit primitive. A separate BriefingProvider surfaces the
    framer's recommendation to the next-iter mutator prompt.
  * "Active" engagement on N-D substrates is therefore: framer
    proposes a coordinate transform; mutator briefing surfaces it;
    mutator chooses whether to integrate it into PARAMETRIC_FORM.
    The holdout gate validates the result. Same separation-of-
    concerns as 1D.

Public API:
  frame_nd(visible_data, primary_feature_key, meta, rubric_data) ->
      (framing_report, primary_feature_key_used)
"""
from __future__ import annotations

from typing import Any, Iterable, Optional

import numpy as np

from ztare.framer.active_framer import frame as _frame_1d


def _pick_primary_feature(
    visible_data: list[tuple[dict, float]],
    declared_key: Optional[str] = None,
) -> Optional[str]:
    """Choose the feature key to project on.

    Decision order:
      1. operator-declared key (if present in every row's features dict)
      2. feature named 'x' (substrate convention for primary axis)
      3. feature with the most distinct numeric values across rows
    """
    if not visible_data:
        return None
    sample_keys = list(visible_data[0][0].keys()) if visible_data[0][0] else []
    if not sample_keys:
        return None

    if declared_key and declared_key in sample_keys:
        # Verify the key has numeric values in most rows
        numeric_count = sum(
            1 for f, _ in visible_data
            if isinstance(f.get(declared_key), (int, float))
            and not isinstance(f.get(declared_key), bool)
        )
        if numeric_count >= len(visible_data) * 0.9:
            return declared_key

    if "x" in sample_keys:
        numeric_count = sum(
            1 for f, _ in visible_data
            if isinstance(f.get("x"), (int, float))
            and not isinstance(f.get("x"), bool)
        )
        if numeric_count >= len(visible_data) * 0.9:
            return "x"

    # Fallback: feature with most distinct numeric values
    best_key = None
    best_distinct = 0
    for k in sample_keys:
        vals = set()
        for f, _ in visible_data:
            v = f.get(k)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                vals.add(round(v, 12))
        if len(vals) > best_distinct:
            best_distinct = len(vals)
            best_key = k
    return best_key


def frame_nd(
    visible_data: list[tuple[dict, float]],
    *,
    primary_feature_key: Optional[str] = None,
    meta: Optional[dict] = None,
    rubric_data: Optional[dict] = None,
) -> tuple[dict, Optional[str]]:
    """Run the 1D framer on a feature-dict substrate's primary axis
    projection.

    Args:
        visible_data: list of (features_dict, y_observed) pairs.
        primary_feature_key: operator-declared primary axis. If None,
            uses heuristic (looks for 'x' first, then most-distinct-
            numeric feature).
        meta: passed through to 1D framer (units / dimensions).
        rubric_data: passed through to 1D framer (scope checks).

    Returns:
        (framing_report, primary_feature_key_used).
        On failure (no visible data, no numeric primary key, etc.),
        framing_report contains `{"framer_engaged": False,
        "disabled_reason": "..."}` and the second element is None.
    """
    if not visible_data:
        return (
            {
                "framer_engaged": False,
                "disabled_reason": "no_visible_data",
                "shape": "n_d",
            },
            None,
        )

    primary = _pick_primary_feature(visible_data, primary_feature_key)
    if primary is None:
        return (
            {
                "framer_engaged": False,
                "disabled_reason": "no_numeric_primary_feature",
                "shape": "n_d",
            },
            None,
        )

    # Project to 1D
    x_list: list[float] = []
    y_list: list[float] = []
    for feats, y_obs in visible_data:
        v = feats.get(primary)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            try:
                x_list.append(float(v))
                y_list.append(float(y_obs))
            except (TypeError, ValueError):
                continue

    if len(x_list) < 80:
        return (
            {
                "framer_engaged": False,
                "disabled_reason": f"too_few_rows_after_projection({len(x_list)}<80)",
                "shape": "n_d",
                "primary_feature_key": primary,
            },
            primary,
        )

    x_arr = np.asarray(x_list, dtype=float)
    y_arr = np.asarray(y_list, dtype=float)

    try:
        _, _, report = _frame_1d(
            x=x_arr,
            y=y_arr,
            meta=meta or {},
            rubric_data=rubric_data or {},
        )
    except Exception as e:
        return (
            {
                "framer_engaged": False,
                "disabled_reason": f"frame_1d_raised({type(e).__name__})",
                "shape": "n_d",
                "primary_feature_key": primary,
                "error": str(e)[:200],
            },
            primary,
        )

    # Augment the 1D report with N-D context so the operator + briefing
    # provider know which axis was framed.
    report["shape"] = "n_d"
    report["primary_feature_key"] = primary
    report["projected_n_rows"] = len(x_list)
    return report, primary
