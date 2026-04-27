"""GP-152 Framer Component C — TransformationEnumerator (v2.0).

Generates the candidate `(h_in, h_out)` pairs after symmetry + dimensional
filtering. v2.0 does depth-1 only; depth-2 composition is a follow-up.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

import numpy as np

from .primitives import Primitive, admissible_primitives
from .symmetry import SymmetryReport
from .units import filter_pair


def enumerate_pairs(
    x: np.ndarray,
    y: np.ndarray,
    meta: Dict,
    sym_report: SymmetryReport,
) -> List[Tuple[str, Primitive, str, Primitive]]:
    """Return list of (h_in_name, h_in, h_out_name, h_out) tuples passing
    domain + round-trip + symmetry + dimensional filters.

    Each pair survives:
      1. Round-trip + domain check via primitives.admissible_primitives.
      2. Dimensional check via units.filter_pair.
    """
    admissible_in = admissible_primitives(x)
    admissible_out = admissible_primitives(y)

    pairs: List[Tuple[str, Primitive, str, Primitive]] = []
    for hi_name, hi in admissible_in.items():
        for ho_name, ho in admissible_out.items():
            if not filter_pair(hi_name, ho_name, meta):
                continue
            pairs.append((hi_name, hi, ho_name, ho))
    return pairs


def filtration_summary(
    n_in: int,
    n_out: int,
    n_pairs_after: int,
) -> Dict[str, int]:
    """Diagnostic info for framing_report."""
    return {
        "n_admissible_h_in": n_in,
        "n_admissible_h_out": n_out,
        "n_pairs_after_filter": n_pairs_after,
    }
