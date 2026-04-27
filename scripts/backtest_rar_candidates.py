"""Backtest RAR candidate forms on gp163d_unified_accel.

SCIPY-only — no LLM. Fits 6 candidate forms on Class A visible rows
(80% fit / 20% holdout), then evaluates per-class MRE on Class A holdout,
Class B (clusters), and Class C (wide binaries).

Question: does ANY form achieve MRE < 0.5 simultaneously on all 3 classes?
If no, the gp163d 50-cap is a substrate-fundamental Newton-step ceiling
rather than mutator laziness.
"""
from __future__ import annotations

import math
import os
import sys
import warnings
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

warnings.filterwarnings("ignore")

# ── Path & data load ─────────────────────────────────────────────────
REPO = Path("/Users/daalami/figs_activist_loop")
sys.path.insert(0, str(REPO / "projects" / "gp163d_unified_accel"))
from features import visible_rows, farther_tail_rows  # noqa: E402

NP_RNG = np.random.default_rng(42)
np.random.seed(42)

EPS = 1e-30


def to_arrays(rows):
    x = np.array([f["x"] for _, _, f in rows], dtype=float)
    y = np.array([y_ for _, y_, _ in rows], dtype=float)
    m = np.array([f["mass_log10"] for _, _, f in rows], dtype=float)
    return x, y, m


# Class A visible rows
VIS = visible_rows()
VIS = [r for r in VIS if r[2]["system_class"] == "A"]
# Order by id for reproducibility, then 80/20 split
VIS_sorted = sorted(VIS, key=lambda r: r[0])
n = len(VIS_sorted)
cut = int(n * 0.80)
A_FIT = VIS_sorted[:cut]
A_HO = VIS_sorted[cut:]

FT = farther_tail_rows()
B_ROWS = [r for r in FT if r[2]["system_class"] == "B"]
C_ROWS = [r for r in FT if r[2]["system_class"] == "C"]

x_fit, y_fit, m_fit = to_arrays(A_FIT)
x_aho, y_aho, m_aho = to_arrays(A_HO)
x_b, y_b, m_b = to_arrays(B_ROWS)
x_c, y_c, m_c = to_arrays(C_ROWS)

print(f"Class A fit:     {len(A_FIT)} rows, mass {m_fit.min():.2f}–{m_fit.max():.2f}")
print(f"Class A holdout: {len(A_HO)} rows, mass {m_aho.min():.2f}–{m_aho.max():.2f}")
print(f"Class B (clusters): {len(B_ROWS)} rows, mass {m_b.min():.2f}–{m_b.max():.2f}")
print(f"Class C (binaries): {len(C_ROWS)} rows, mass {m_c.min():.2f}–{m_c.max():.2f}")
print()


# ── Candidate forms ──────────────────────────────────────────────────
def safe_mre(y_pred, y_true):
    yp = np.asarray(y_pred, dtype=float)
    yt = np.asarray(y_true, dtype=float)
    bad = ~np.isfinite(yp) | (np.abs(yt) < EPS)
    if bad.all():
        return float("nan"), float("nan")
    rel = np.abs(yp[~bad] - yt[~bad]) / np.abs(yt[~bad])
    if rel.size == 0:
        return float("nan"), float("nan")
    return float(rel.mean()), float(np.abs(yp[~bad] - yt[~bad]).max())


def predict_mcgaugh(x, m, p):
    (cA,) = p
    cA = max(cA, 1e-14)
    return (x + np.sqrt(x * x + 4.0 * cA * x)) / 2.0


def predict_f1_rg(x, m, p):
    g_star, gamma, M0, u0 = p
    g_star = max(g_star, 1e-14)
    # exponent: 1 + gamma*(m - M0)
    expo = 1.0 + gamma * (m - M0)
    ratio = np.maximum(x / g_star, 1e-30)
    # Use safe power via log
    with np.errstate(over="ignore", invalid="ignore"):
        pw = np.exp(np.clip(expo * np.log(ratio), -60.0, 60.0))
    denom = 1.0 + pw
    return x / denom + u0 * x + x  # u0 captures small residual baseline tilt


def predict_f3_multifractal(x, m, p):
    g_star, alpha0, c2, q0, M_star, delta = p
    g_star = max(g_star, 1e-14)
    L = np.log10(np.maximum(x, EPS) / g_star)
    log_ratio = alpha0 * L + c2 * (L + q0) ** 2 + delta * (m - M_star)
    log_ratio = np.clip(log_ratio, -20.0, 20.0)
    return x * np.power(10.0, log_ratio)


def predict_tanh_bump(x, m, p):
    c0, amp, m0, width = p
    width = max(width, 0.1)  # enforce positivity
    c0 = max(c0, 1e-14)
    c_eff = c0 * np.exp(np.clip(amp * np.tanh((m - m0) / width), -20.0, 20.0))
    return (x + np.sqrt(x * x + 4.0 * c_eff * x)) / 2.0


def predict_quad_logc(x, m, p):
    log_c0, alpha, beta = p
    log_c = log_c0 + alpha * (m - 10.5) - beta * (m - 10.5) ** 2
    log_c = np.clip(log_c, -30.0, -18.0)
    c_eff = np.exp(log_c)
    return (x + np.sqrt(x * x + 4.0 * c_eff * x)) / 2.0


def predict_hill(x, m, p):
    a, n_, K, b, gamma = p
    a = max(a, 1e-12)
    K = max(K, 1e-14)
    n_ = max(n_, 0.05)
    with np.errstate(over="ignore", invalid="ignore"):
        xn = np.exp(np.clip(n_ * np.log(np.maximum(x, EPS)), -200.0, 200.0))
        Kn = np.exp(np.clip(n_ * np.log(K), -200.0, 200.0))
        xg = np.exp(np.clip(gamma * np.log(np.maximum(x, EPS)), -200.0, 200.0))
    return a * xn / (Kn + xn) * (1.0 + b * xg)


CANDIDATES = [
    {
        "name": "McGAUGH_UNIVERSAL",
        "K": 1,
        "predict": predict_mcgaugh,
        "bounds": [(1e-12, 1e-8)],
        "init": lambda: [10 ** NP_RNG.uniform(-12, -8)],
    },
    {
        "name": "F1_RG_FLOW",
        "K": 4,
        "predict": predict_f1_rg,
        "bounds": [(1e-12, 1e-9), (-0.5, 0.5), (5.0, 12.0), (-1.0, 1.0)],
        "init": lambda: [
            10 ** NP_RNG.uniform(-12, -9),
            NP_RNG.uniform(-0.5, 0.5),
            NP_RNG.uniform(5, 12),
            NP_RNG.uniform(-1, 1),
        ],
    },
    {
        "name": "F3_MULTIFRACTAL",
        "K": 6,
        "predict": predict_f3_multifractal,
        "bounds": [(1e-12, 1e-9), (-2, 2), (-1, 1), (-2, 2), (5, 12), (-1, 1)],
        "init": lambda: [
            10 ** NP_RNG.uniform(-12, -9),
            NP_RNG.uniform(-2, 2),
            NP_RNG.uniform(-1, 1),
            NP_RNG.uniform(-2, 2),
            NP_RNG.uniform(5, 12),
            NP_RNG.uniform(-1, 1),
        ],
    },
    {
        "name": "SMOOTH_TANH_BUMP",
        "K": 4,
        "predict": predict_tanh_bump,
        "bounds": [(1e-12, 1e-8), (-4, 4), (7.5, 12), (0.25, 5)],
        "init": lambda: [
            10 ** NP_RNG.uniform(-12, -8),
            NP_RNG.uniform(-4, 4),
            NP_RNG.uniform(7.5, 12),
            NP_RNG.uniform(0.25, 5),
        ],
    },
    {
        "name": "QUADRATIC_LOG_C",
        "K": 3,
        "predict": predict_quad_logc,
        "bounds": [(-25, -20), (-0.5, 0.5), (-0.2, 0.2)],
        "init": lambda: [
            NP_RNG.uniform(-25, -20),
            NP_RNG.uniform(-0.5, 0.5),
            NP_RNG.uniform(-0.2, 0.2),
        ],
    },
    {
        "name": "HILL_ALLOMETRIC",
        "K": 5,
        "predict": predict_hill,
        "bounds": [(1e-9, 1e-7), (0.5, 2), (1e-10, 1e-8), (-1, 1), (-1, 1)],
        "init": lambda: [
            10 ** NP_RNG.uniform(-9, -7),
            NP_RNG.uniform(0.5, 2),
            10 ** NP_RNG.uniform(-10, -8),
            NP_RNG.uniform(-1, 1),
            NP_RNG.uniform(-1, 1),
        ],
    },
]


def loss_log_residual(params, predict, x, y, m):
    """Sum of squared log-residuals (relative) — robust over 5+ dex."""
    try:
        yp = predict(x, m, params)
    except Exception:
        return 1e20
    if not np.all(np.isfinite(yp)):
        return 1e20
    yp = np.maximum(yp, EPS)
    yt = np.maximum(y, EPS)
    r = np.log(yp) - np.log(yt)
    if not np.all(np.isfinite(r)):
        return 1e20
    return float(np.mean(r * r))


def fit_candidate(cand, x, y, m, n_starts=5):
    best = None
    best_loss = float("inf")
    for _ in range(n_starts):
        x0 = cand["init"]()
        try:
            res = minimize(
                loss_log_residual,
                x0,
                args=(cand["predict"], x, y, m),
                method="L-BFGS-B",
                bounds=cand["bounds"],
                options={"maxiter": 500, "ftol": 1e-10},
            )
        except Exception:
            continue
        if res.fun < best_loss and np.isfinite(res.fun):
            best_loss = float(res.fun)
            best = res
    return best


# ── Run fits ─────────────────────────────────────────────────────────
results = []
for cand in CANDIDATES:
    res = fit_candidate(cand, x_fit, y_fit, m_fit, n_starts=5)
    if res is None:
        results.append(
            {
                "name": cand["name"],
                "K": cand["K"],
                "params": None,
                "converged": False,
                "fit_mre": float("nan"),
                "ho_mre": float("nan"),
                "b_mre": float("nan"),
                "c_mre": float("nan"),
                "fit_max": float("nan"),
                "ho_max": float("nan"),
                "b_max": float("nan"),
                "c_max": float("nan"),
                "loss": float("nan"),
            }
        )
        continue
    p = res.x
    yp_fit = cand["predict"](x_fit, m_fit, p)
    yp_aho = cand["predict"](x_aho, m_aho, p)
    yp_b = cand["predict"](x_b, m_b, p)
    yp_c = cand["predict"](x_c, m_c, p)
    fit_mre, fit_max = safe_mre(yp_fit, y_fit)
    ho_mre, ho_max = safe_mre(yp_aho, y_aho)
    b_mre, b_max = safe_mre(yp_b, y_b)
    c_mre, c_max = safe_mre(yp_c, y_c)
    results.append(
        {
            "name": cand["name"],
            "K": cand["K"],
            "params": p,
            "converged": bool(res.success),
            "fit_mre": fit_mre,
            "ho_mre": ho_mre,
            "b_mre": b_mre,
            "c_mre": c_mre,
            "fit_max": fit_max,
            "ho_max": ho_max,
            "b_max": b_max,
            "c_max": c_max,
            "loss": float(res.fun),
        }
    )


# ── Print table ──────────────────────────────────────────────────────
def fmt(v):
    if not np.isfinite(v):
        return "  nan  "
    if v >= 1e3:
        return f"{v:.2e}"
    return f"{v:7.4f}"


hdr = (
    f"{'form_name':<22}{'K':>3}  "
    f"{'A_fit':>8}  {'A_holdout':>10}  {'B_clust':>8}  {'C_binar':>8}  "
    f"{'conv':>5}"
)
print("=" * len(hdr))
print(hdr)
print("-" * len(hdr))
for r in results:
    print(
        f"{r['name']:<22}{r['K']:>3}  "
        f"{fmt(r['fit_mre']):>8}  {fmt(r['ho_mre']):>10}  "
        f"{fmt(r['b_mre']):>8}  {fmt(r['c_mre']):>8}  "
        f"{str(r['converged']):>5}"
    )
print("=" * len(hdr))

print("\nMax |residual| per class (m/s²):")
print(f"{'form_name':<22}{'A_fit_max':>14}{'A_HO_max':>14}{'B_max':>14}{'C_max':>14}")
for r in results:
    print(
        f"{r['name']:<22}{r['fit_max']:>14.3e}{r['ho_max']:>14.3e}"
        f"{r['b_max']:>14.3e}{r['c_max']:>14.3e}"
    )

print("\nFitted parameters:")
for r in results:
    print(f"  {r['name']}: loss={r['loss']:.4e}")
    if r["params"] is None:
        print("    FAILED")
        continue
    print(f"    params = {[float(v) for v in r['params']]}")

# Pass/fail per row: MRE<0.5 on all three OOD classes (HO + B + C)
print("\nCross-class MRE<0.5 simultaneously?")
any_pass = False
for r in results:
    ok = (
        np.isfinite(r["ho_mre"])
        and np.isfinite(r["b_mre"])
        and np.isfinite(r["c_mre"])
        and r["ho_mre"] < 0.5
        and r["b_mre"] < 0.5
        and r["c_mre"] < 0.5
    )
    if ok:
        any_pass = True
    print(f"  {r['name']:<22} {'PASS' if ok else 'FAIL'}")
print(f"\nANY form passes cross-class < 0.5 ? {any_pass}")
