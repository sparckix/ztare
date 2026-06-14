"""GP-152 Framer — DimensionalFilter (v2.0).

Buckingham-π filtering on candidate transformation pairs based on declared
units in meta["units"]. When units are unspecified, this is a no-op
(returns all primitives admissible).

The richer Buckingham-π reduction (which combines x and y into dimensionless
groups) is v2.1+; v2.0 just rejects pairs that produce dimensionally illegal
operations (e.g., log of a dimensional quantity).
"""
from __future__ import annotations

from typing import Dict, Set

import numpy as np


# Primitives that require dimensionless input (their domain is a pure number)
DIMENSIONLESS_REQUIRED: Set[str] = {"log", "exp"}

# Primitives that produce dimensionless output regardless of input
DIMENSIONLESS_OUTPUT: Set[str] = {"log", "exp"}


def filter_by_units(
    primitive_names: Set[str],
    axis_units: str | None,
) -> Set[str]:
    """Drop primitives that violate dimensional consistency on this axis.

    axis_units = None → no filtering (caller didn't supply units metadata).
    axis_units = "dimensionless" → all primitives admissible.
    axis_units = anything else (e.g. "m", "kg", "s") → drop log/exp.

    The Framer is conservative: when in doubt, admit. Operators who care
    about strict Buckingham-π should declare units explicitly.
    """
    if axis_units is None or axis_units.lower() in ("dimensionless", "1", ""):
        return set(primitive_names)
    return set(primitive_names) - DIMENSIONLESS_REQUIRED


def filter_pair(
    h_in_name: str,
    h_out_name: str,
    meta: Dict,
) -> bool:
    """Return True if (h_in, h_out) is dimensionally admissible per meta."""
    units = meta.get("units") or {}
    x_units = units.get("x")
    y_units = units.get("y")
    in_admissible = filter_by_units({h_in_name}, x_units)
    out_admissible = filter_by_units({h_out_name}, y_units)
    return h_in_name in in_admissible and h_out_name in out_admissible
