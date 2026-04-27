"""Automated metadata validator for corrector_library.py.

Empirically measures each library form's smoothness and monotonicity
across a sample range, then asserts the declared metadata matches.
Catches taxonomy errors (like round() marked is_smooth=True) before
they silently poison the sweep's candidate pool.
"""
from __future__ import annotations

import pytest

from src.ztare.gates.corrector_library import CORRECTOR_LIBRARY, CorrectorForm

SAMPLE_VS = list(range(1, 51))
SAMPLE_KS = [0.08, 0.5, 1.0, 2.0, 5.0, 12.0]
JUMP_THRESHOLD = 0.9


def _has_discontinuity(form: CorrectorForm) -> bool:
    """Check if a form produces jump discontinuities.

    Evaluates f(v, k) across fine-grained k values and checks whether
    the output jumps by >= JUMP_THRESHOLD between adjacent k values.
    A smooth function's output changes gradually; a step function snaps.
    """
    for v in [3, 7, 15, 25]:
        import numpy as np
        for k_center in [0.1, 1.0, 5.0]:
            k_vals = np.linspace(k_center - 0.5, k_center + 0.5, 1001)
            prev = None
            for k in k_vals:
                try:
                    val = form.fn(float(v), float(k))
                except (OverflowError, ValueError, ZeroDivisionError):
                    prev = None
                    continue
                if prev is not None and abs(val - prev) >= JUMP_THRESHOLD:
                    return True
                prev = val
    return False


def _is_monotone_empirical(form: CorrectorForm) -> bool:
    """Check if f(v, k) is monotone non-decreasing in v for positive k."""
    for k in SAMPLE_KS:
        prev = None
        for v in SAMPLE_VS:
            try:
                val = form.fn(float(v), k)
            except (OverflowError, ValueError, ZeroDivisionError):
                prev = None
                continue
            if prev is not None and val < prev - 0.01:
                return False
            prev = val
    return True


@pytest.mark.parametrize(
    "form",
    CORRECTOR_LIBRARY,
    ids=[f.name for f in CORRECTOR_LIBRARY],
)
def test_smoothness_matches_empirical(form: CorrectorForm):
    has_jump = _has_discontinuity(form)
    if has_jump and form.is_smooth:
        pytest.fail(
            f"'{form.name}' is declared is_smooth=True but empirically "
            f"has jump discontinuities (>= {JUMP_THRESHOLD}). "
            f"Change is_smooth to False in corrector_library.py."
        )


@pytest.mark.parametrize(
    "form",
    CORRECTOR_LIBRARY,
    ids=[f.name for f in CORRECTOR_LIBRARY],
)
def test_monotonicity_matches_empirical(form: CorrectorForm):
    empirical_monotone = _is_monotone_empirical(form)
    if form.is_monotone and not empirical_monotone:
        pytest.fail(
            f"'{form.name}' is declared is_monotone=True but empirically "
            f"decreases for some (v, k) in the sample range. "
            f"Change is_monotone to False in corrector_library.py."
        )
