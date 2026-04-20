"""Ground-truth module for GP-078 dark parity-gate sequence (Division A artifact).

NOT mutator-visible. This file defines the generating law.

Recurrence:
  a(1) = 1, a(2) = 1
  even n: a(n) = a(n - a(n-1)) + a(n - a(n-2))
  odd n:  a(n) = a(n - a(n-1)) + a(floor(n/2))
"""
from __future__ import annotations

_CACHE: dict[int, int] = {}


def _compute(N: int) -> None:
    if N in _CACHE:
        return
    a = [0] * (N + 1)
    a[1] = 1
    a[2] = 1
    for n in range(3, N + 1):
        idx1 = n - a[n - 1]
        if n % 2 == 0:
            idx2 = n - a[n - 2]
            a[n] = a[idx1] + a[idx2]
        else:
            a[n] = a[idx1] + a[n // 2]
    for i in range(1, N + 1):
        _CACHE[i] = a[i]


def f_true(n: int) -> int:
    if n not in _CACHE:
        _compute(max(n, 200))
    return _CACHE[n]


def f_dominant(n: int) -> int:
    return f_true(n)


if __name__ == "__main__":
    print("GT module verification — parity-gate dark sequence")
    _compute(80)
    for n in range(1, 81):
        print(f"  n={n}: f_true={_CACHE[n]}")
