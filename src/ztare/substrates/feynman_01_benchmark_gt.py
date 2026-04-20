"""Ground-truth module (Division A artifact — not mutator-visible).

GT: f(m, v) = round(m * v / math.sqrt(1 - v*v/225))
Dominant: m * v
"""
from __future__ import annotations

import math


def f_true(m: int, v: int) -> int:
    return int(round(m * v / math.sqrt(1 - v*v/225)))


def f_dominant(m: int, v: int) -> int:
    return int(m * v)


if __name__ == "__main__":
    print("GT module verification")
    for m in [1, 3, 5]:
        for v in [1, 5, 10]:
            ft = f_true(m, v)
            fd = f_dominant(m, v)
            print(f"  m={m}, v={v}: f_true={ft}, f_dominant={fd}, diff={ft-fd}")
