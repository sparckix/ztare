"""Ground-truth module for A002865 log-scaled sequence recovery (GP-077 Component C)."""
from __future__ import annotations

import math

SCALE = 1000


def _partition_count(N: int) -> list[int]:
    p = [0] * (N + 1)
    p[0] = 1
    for k in range(1, N + 1):
        for n in range(k, N + 1):
            p[n] += p[n - k]
    return p


_P = _partition_count(200)


def _a002865(n: int) -> int:
    if n == 0:
        return 1
    return _P[n] - _P[n - 1]


def f_true(n: int) -> int:
    """Log-scaled A002865: round(1000 * ln(a(n)))."""
    val = _a002865(n)
    if val <= 0:
        return 0
    return round(SCALE * math.log(val))


def f_dominant(n: int) -> int:
    """Hardy-Ramanujan leading term adapted for A002865."""
    if n < 2:
        return 0
    log_pn = math.pi * math.sqrt(2 * n / 3) - math.log(4 * n * math.sqrt(3))
    correction = math.log(1 - math.exp(-math.pi / math.sqrt(6 * n)))
    return round(SCALE * (log_pn + correction))


if __name__ == "__main__":
    for n in range(2, 41):
        print(f"n={n:3d}  true={f_true(n):6d}  dom={f_dominant(n):6d}  res={f_true(n) - f_dominant(n):+5d}")
