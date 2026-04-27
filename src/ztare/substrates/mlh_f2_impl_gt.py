"""Ground-truth implementation for MLH family substrate F2 (Division A).

Private. Do not reference this module from charter, rubric, or test_model.
The mutator sees only raw (n, z) pairs in evidence.txt.
"""
from __future__ import annotations


def _primefactors(n: int) -> list[int]:
    n = int(n)
    if n < 2:
        return []
    factors: list[int] = []
    d = 2
    while d * d <= n:
        if n % d == 0:
            factors.append(d)
            while n % d == 0:
                n //= d
        d += 1
    if n > 1:
        factors.append(n)
    return factors


def f_true(n: int) -> int:
    n = int(n)
    if n < 1:
        return 0
    return sum(_primefactors(n))


def f_dominant(n: int) -> float:
    """Smooth dominant-term approximation for Component C (residual fingerprinting).

    GP-135 stub: for arithmetic-function substrates the "dominant term" is not
    well-defined in the analytic sense. We return f_true(n) as a float so
    Component C's residual check (f_true - f_dominant) produces zeros and
    Component C treats the substrate as "no separable dominant term." This
    is a soft stub; the component's output on this substrate is advisory.
    """
    return float(f_true(n))
