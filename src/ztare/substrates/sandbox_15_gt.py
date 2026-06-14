"""Ground-truth module for sandbox_15 integer substrate.

GT: f(u, v) = u^2 * v - u + round(0.08 * v)
  dominant term:  u^2 * v - u
  corrector:      round(0.08 * v)
"""
from __future__ import annotations


def f_true(u: int, v: int) -> int:
    """Full ground-truth function."""
    return u * u * v - u + round(0.08 * v)


def f_dominant(u: int, v: int) -> int:
    """Dominant (structural) term only, without corrector."""
    return u * u * v - u


if __name__ == "__main__":
    print("sandbox_15 GT verification")
    print(f"{'u':>3} {'v':>3} {'f_true':>10} {'f_dominant':>10} {'corrector':>10}")
    print("-" * 42)
    for u in [1, 2, 3, 5]:
        for v in [1, 5, 10, 15]:
            ft = f_true(u, v)
            fd = f_dominant(u, v)
            print(f"{u:3d} {v:3d} {ft:10d} {fd:10d} {ft - fd:10d}")
