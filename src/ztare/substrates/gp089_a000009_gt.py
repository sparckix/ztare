"""Ground-truth module for A000009 log-scaled sequence recovery (GP-089).

Division A artifact — GT identity and formula withheld from mutator.
The mutator sees only raw (n, z) pairs in evidence.txt.
"""
from __future__ import annotations

import math

SCALE = 1000

# A000009: number of partitions of n into distinct parts (= q(n))
# Equivalent: number of partitions of n into odd parts (Euler's theorem)
# OEIS A000009: 1, 1, 1, 2, 2, 3, 4, 5, 6, 8, 10, 12, 15, 18, 22, ...

def _compute_distinct_partitions(max_n: int) -> list[int]:
    dp = [0] * (max_n + 1)
    dp[0] = 1
    for k in range(1, max_n + 1):
        for j in range(max_n, k - 1, -1):
            dp[j] += dp[j - k]
    return dp


_Q = _compute_distinct_partitions(120)


def q(n: int) -> int:
    """Return q(n) = number of partitions of n into distinct parts."""
    return _Q[n]


def f_true(n: int) -> int:
    """Log-scaled A000009: round(1000 * ln(q(n))).

    Defined for n >= 3 where q(n) >= 2.
    """
    val = _Q[n]
    if val <= 0:
        return 0
    return round(SCALE * math.log(val))


def f_dominant(n: int) -> int:
    """Hardy-Ramanujan asymptotic for ln(q(n)).

    ln(q(n)) ~ pi*sqrt(n/3) - (3/4)*ln(n) - ln(4*3^(1/4))

    The constant: -ln(4) - (1/4)*ln(3) = -1.6609...
    """
    if n < 3:
        return 0
    asymptotic_const = -math.log(4) - 0.25 * math.log(3)
    log_q = (math.pi * math.sqrt(n / 3)
             - 0.75 * math.log(n)
             + asymptotic_const)
    return round(SCALE * log_q)


if __name__ == "__main__":
    print("n   q(n)     true_z   dom_z   residual")
    for n in range(3, 83):
        true_z = f_true(n)
        dom_z = f_dominant(n)
        print(f"{n:3d}  {q(n):8d}  {true_z:6d}  {dom_z:6d}  {true_z - dom_z:+5d}")
