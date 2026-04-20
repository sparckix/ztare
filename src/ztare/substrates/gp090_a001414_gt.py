"""Ground-truth module for A001414 direct sequence recovery (GP-090).

Division A artifact — GT identity and structure withheld from mutator.
The mutator sees only raw (n, z) pairs in evidence.txt.

A001414: sopfr(n) = sum of prime factors of n counted with multiplicity.
Examples: sopfr(12) = 2+2+3 = 7, sopfr(30) = 2+3+5 = 10, sopfr(p) = p.
"""
from __future__ import annotations


def _sopfr(n: int) -> int:
    """Sum of prime factors of n with multiplicity."""
    total = 0
    d = 2
    while d * d <= n:
        while n % d == 0:
            total += d
            n //= d
        d += 1
    if n > 1:
        total += n
    return total


def f_true(n: int) -> int:
    """Direct A001414 value: sopfr(n)."""
    return _sopfr(n)


def f_dominant(n: int) -> int:
    """Smooth approximation to average sopfr behavior.

    Average sopfr(n) ≈ log(n) * Σ_{p prime} p/(p-1) — but this series
    diverges. Empirical average grows roughly as c * log(n) for small n.
    Using linear log fit: approximately 4.5 * log(n) - 3.0 from n=2..80 data.
    This is a very rough dominant term; residual structure is highly irregular.
    """
    import math
    if n < 2:
        return 0
    return round(4.5 * math.log(n) - 3.0)


if __name__ == "__main__":
    print("n   sopfr(n)   dominant   residual")
    for n in range(2, 51):
        true_z = f_true(n)
        dom_z = f_dominant(n)
        print(f"{n:3d}  {true_z:8d}  {dom_z:8d}  {true_z - dom_z:+6d}")
