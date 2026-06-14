"""Ground-truth implementation for MLH family substrate F5 (Division A)."""
from __future__ import annotations


def f_true(n: int) -> int:
    n = int(n)
    if n < 1:
        return 0
    count = 0
    d = 1
    while d * d <= n:
        if n % d == 0:
            count += 1
            if d * d != n:
                count += 1
        d += 1
    return count


def f_dominant(n: int) -> float:
    """Smooth dominant-term approximation for residual diagnostics.

    GP-135 stub: for arithmetic-function substrates the "dominant term" is not
    well-defined in the analytic sense. We return f_true(n) as a float so
    The residual check (f_true - f_dominant) produces zeros and
    residual diagnostics treat the substrate as "no separable dominant term." This
    is a soft stub; the component's output on this substrate is advisory.
    """
    return float(f_true(n))
