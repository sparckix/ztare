"""test_v2_inverse_precision.py — round-trip precision of h_out and h_out⁻¹.

v2.0's only new computation is the inverse. Tests that h_out⁻¹(h_out(y)) ≈ y
to machine epsilon across each primitive in Σ, plus depth-2 compositions,
on a representative range of y values.

If a primitive shows max relative error > 1e-4 it needs a precision guard
before being admitted to Σ.
"""
import sys
from typing import Callable, Tuple

import numpy as np


PRIMITIVES = {
    "identity":    (lambda y: y,                                     lambda y: y),
    "scale_2.5":   (lambda y: 2.5 * y,                                lambda y: y / 2.5),
    "shift_+3":    (lambda y: y + 3,                                  lambda y: y - 3),
    "power_0.5":   (lambda y: np.sign(y) * np.sqrt(np.abs(y) + 1e-30),
                    lambda y: np.sign(y) * y ** 2),
    "power_2":     (lambda y: y ** 2,
                    lambda y: np.sign(y) * np.sqrt(np.abs(y) + 1e-30)),
    "log":         (lambda y: np.log(np.abs(y) + 1e-30),
                    lambda y: np.exp(y)),
    "exp":         (lambda y: np.exp(np.clip(y, -50, 50)),
                    lambda y: np.log(np.abs(y) + 1e-30)),
    "reciprocal":  (lambda y: 1.0 / np.where(np.abs(y) < 1e-30, 1e-30, y),
                    lambda y: 1.0 / np.where(np.abs(y) < 1e-30, 1e-30, y)),
}


def roundtrip_error(y_test: np.ndarray, h: Callable, h_inv: Callable) -> Tuple[float, float]:
    y_back = h_inv(h(y_test))
    abs_err = float(np.max(np.abs(y_back - y_test)))
    denom = np.maximum(np.abs(y_test), 1e-30)
    rel_err = float(np.max(np.abs((y_back - y_test) / denom)))
    return abs_err, rel_err


def compose(*pairs):
    """Compose primitives left-to-right: h(y) = pairs[-1].h(...pairs[0].h(y)...)."""
    def h(y):
        for h_, _ in pairs:
            y = h_(y)
        return y

    def h_inv(y):
        for _, h_inv_ in reversed(pairs):
            y = h_inv_(y)
        return y

    return h, h_inv


def main() -> int:
    y_pos = np.linspace(0.1, 100, 50)
    y_full = np.linspace(-50, 50, 50)
    y_safe = np.linspace(0.5, 5, 50)

    print("Single primitive round-trip (h⁻¹(h(y)) − y):")
    print(f"  {'primitive':15s} {'max_abs':>12s} {'max_rel':>12s}    range  verdict")
    overall_ok = True
    for name, (h, h_inv) in PRIMITIVES.items():
        if name in ("log",):
            y = y_pos
        elif name in ("reciprocal",):
            y = y_safe
        else:
            y = y_full
        a, r = roundtrip_error(y, h, h_inv)
        if r < 1e-10:
            verdict = "OK"
        elif r < 1e-4:
            verdict = "PRECISION_LOSS"
        else:
            verdict = "BROKEN"
            overall_ok = False
        print(
            f"  {name:15s} {a:12.2e} {r:12.2e}    "
            f"[{y[0]:.2f}, {y[-1]:.2f}]   {verdict}"
        )

    print()
    print("Depth-2 composition round-trip (worst case):")
    cases = [
        ("scale_2.5 ∘ log",          PRIMITIVES["scale_2.5"], PRIMITIVES["log"]),
        ("log ∘ scale_2.5",          PRIMITIVES["log"],       PRIMITIVES["scale_2.5"]),
        ("exp ∘ shift_+3",           PRIMITIVES["exp"],       PRIMITIVES["shift_+3"]),
        ("power_2 ∘ power_0.5",      PRIMITIVES["power_2"],   PRIMITIVES["power_0.5"]),
        ("reciprocal ∘ reciprocal",  PRIMITIVES["reciprocal"], PRIMITIVES["reciprocal"]),
    ]
    for label, p1, p2 in cases:
        h, h_inv = compose(p2, p1)
        a, r = roundtrip_error(y_pos, h, h_inv)
        if r < 1e-8:
            verdict = "OK"
        elif r < 1e-3:
            verdict = "PRECISION_LOSS"
        else:
            verdict = "BROKEN"
            overall_ok = False
        print(f"  {label:30s} max_rel={r:.2e}   {verdict}")

    print()
    print("OVERALL:", "PASS" if overall_ok else "FAIL")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
