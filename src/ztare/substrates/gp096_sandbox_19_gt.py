"""Ground-truth module — Division A artifact, not mutator-visible.

Substrate: continuous single-variable empirical dataset.
Source: Shanbhag (2019) MTS paper, test case 3 (40-point log-spaced downsample).
GT type: tabulated empirical data + scipy interpolation.
No analytical symbolic expression exists — the GT is the data itself.

f_true(t) returns the reference G value for any t via log-log interpolation.
Used by residual diagnostics and by evidence_holdout / evidence_farther_tail evaluation.
"""
from __future__ import annotations

import math


# 40-point log-spaced downsample of the source dataset.
# Columns: (t [s], G_ref)
# Split: indices 0-19 → visible; 20-29 → holdout; 30-39 → farther tail
_RAW_DATA: list[tuple[float, float]] = [
    (1.000000e-04, 2.379378e+02),
    (1.588565e-04, 2.363096e+02),
    (2.523539e-04, 2.340055e+02),
    (4.008806e-04, 2.308590e+02),
    (6.368250e-04, 2.267321e+02),
    (1.109752e-03, 2.203857e+02),
    (1.762914e-03, 2.139661e+02),
    (2.800504e-03, 2.066583e+02),
    (4.448783e-03, 1.986804e+02),
    (7.067181e-03, 1.902953e+02),
    (1.122668e-02, 1.817667e+02),
    (1.783431e-02, 1.733218e+02),
    (2.833096e-02, 1.651280e+02),
    (4.500558e-02, 1.572848e+02),
    (7.149429e-02, 1.498288e+02),
    (1.245883e-01, 1.413695e+02),
    (1.979167e-01, 1.346637e+02),
    (3.144035e-01, 1.281876e+02),
    (4.994505e-01, 1.218514e+02),
    (7.934097e-01, 1.155609e+02),
    # holdout
    (1.260383e+00, 1.092231e+02),
    (2.002200e+00, 1.027500e+02),
    (3.180626e+00, 9.606389e+01),
    (5.052631e+00, 8.910176e+01),
    (8.026434e+00, 8.182225e+01),
    (1.398713e+01, 7.265353e+01),
    (2.221947e+01, 6.468747e+01),
    (3.529707e+01, 5.651036e+01),
    (5.607170e+01, 4.825605e+01),
    (8.907355e+01, 4.010863e+01),
    # farther tail
    (1.414991e+02, 3.229178e+01),
    (2.247806e+02, 2.504759e+01),
    (3.570786e+02, 1.860562e+01),
    (5.672426e+02, 1.314725e+01),
    (9.011018e+02, 8.773277e+00),
    (1.570290e+03, 4.950266e+00),
    (2.494508e+03, 2.828945e+00),
    (3.962689e+03, 1.484570e+00),
    (6.294989e+03, 7.081372e-01),
    (1.000000e+04, 3.036843e-01),
]

_LOG_T = [math.log(t) for t, _ in _RAW_DATA]
_LOG_G = [math.log(G) for _, G in _RAW_DATA]


def f_true(t: float) -> float:
    """Return reference G(t) via log-log linear interpolation.

    Clamps to boundary values for t outside the data range.
    """
    log_t = math.log(t)
    if log_t <= _LOG_T[0]:
        return math.exp(_LOG_G[0])
    if log_t >= _LOG_T[-1]:
        return math.exp(_LOG_G[-1])
    # Binary search for bracket
    lo, hi = 0, len(_LOG_T) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if _LOG_T[mid] <= log_t:
            lo = mid
        else:
            hi = mid
    # Log-log linear interpolation
    frac = (log_t - _LOG_T[lo]) / (_LOG_T[hi] - _LOG_T[lo])
    log_g = _LOG_G[lo] + frac * (_LOG_G[hi] - _LOG_G[lo])
    return math.exp(log_g)


def f_dominant(t: float) -> float:
    """Dominant term proxy — same as f_true (no dominant factorisation exists)."""
    return f_true(t)


def evidence_grid() -> list[tuple[float]]:
    """Visible evidence points (indices 0-19)."""
    return [(t,) for t, _ in _RAW_DATA[:20]]


def holdout_grid() -> list[tuple[float]]:
    """Holdout points (indices 20-29)."""
    return [(t,) for t, _ in _RAW_DATA[20:30]]


def farther_tail_grid() -> list[tuple[float]]:
    """Farther-tail points (indices 30-39)."""
    return [(t,) for t, _ in _RAW_DATA[30:]]


if __name__ == "__main__":
    print("GT module verification — spot-check 5 visible points:")
    for t, G_ref in _RAW_DATA[:5]:
        G_pred = f_true(t)
        err_pct = 100 * abs(G_pred - G_ref) / G_ref
        print(f"  t={t:.4e}: ref={G_ref:.4f}, pred={G_pred:.4f}, err={err_pct:.4f}%")
    print("All errors should be < 0.01% (interpolation exact at knot points).")
