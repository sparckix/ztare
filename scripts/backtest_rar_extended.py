"""Extended RAR candidate backtest — radius_log10 + piecewise + EFE forms.

SCIPY-only — no LLM. Tests ~11 NEW forms beyond scripts/backtest_rar_candidates.py.
Goal: determine whether ANY form in the gp163d substrate (with x, mass_log10,
radius_log10) achieves MRE<0.5 simultaneously on Class A holdout, Class B
clusters, and Class C wide binaries.

Critical observation discovered during data inspection:
  Class C (wide binaries): radius_log10 == -2.00 for ALL 12 rows (degenerate).
  Any radius-axis bridge treats Class C as a single radius point.
"""
from __future__ import annotations

import math
import sys
import warnings
from pathlib import Path

import numpy as np
from scipy.optimize import minimize, differential_evolution

warnings.filterwarnings("ignore")

REPO = Path("/Users/daalami/figs_activist_loop")
sys.path.insert(0, str(REPO / "projects" / "gp163d_unified_accel"))
from features import visible_rows, farther_tail_rows  # noqa: E402

NP_RNG = np.random.default_rng(42)
np.random.seed(42)
EPS = 1e-30


# ── Data ──────────────────────────────────────────────────────────────
def to_arrays(rows):
    """Return (x, y, m, r, mask_finite). Skips rows with NaN x/y/m/r."""
    x = np.array([f["x"] for _, _, f in rows], dtype=float)
    y = np.array([y_ for _, y_, _ in rows], dtype=float)
    m = np.array([f["mass_log10"] for _, _, f in rows], dtype=float)
    r = np.array([f.get("radius_log10", np.nan) for _, _, f in rows], dtype=float)
    mask = (
        np.isfinite(x) & np.isfinite(y) & np.isfinite(m) & np.isfinite(r)
        & (x > 0) & (y > 0)
    )
    return x[mask], y[mask], m[mask], r[mask], int((~mask).sum())


VIS = [r for r in visible_rows() if r[2]["system_class"] == "A"]
VIS_sorted = sorted(VIS, key=lambda r: r[0])
n = len(VIS_sorted)
cut = int(n * 0.80)
A_FIT_rows = VIS_sorted[:cut]
A_HO_rows = VIS_sorted[cut:]
FT = farther_tail_rows()
B_rows = [r for r in FT if r[2]["system_class"] == "B"]
C_rows = [r for r in FT if r[2]["system_class"] == "C"]

x_fit, y_fit, m_fit, r_fit, sk_fit = to_arrays(A_FIT_rows)
x_aho, y_aho, m_aho, r_aho, sk_aho = to_arrays(A_HO_rows)
x_b, y_b, m_b, r_b, sk_b = to_arrays(B_rows)
x_c, y_c, m_c, r_c, sk_c = to_arrays(C_rows)

print(f"Class A fit:     n={len(x_fit)} (skipped {sk_fit}), "
      f"m=[{m_fit.min():.2f},{m_fit.max():.2f}] r=[{r_fit.min():.2f},{r_fit.max():.2f}]")
print(f"Class A holdout: n={len(x_aho)} (skipped {sk_aho}), "
      f"m=[{m_aho.min():.2f},{m_aho.max():.2f}] r=[{r_aho.min():.2f},{r_aho.max():.2f}]")
print(f"Class B clusters: n={len(x_b)} (skipped {sk_b}), "
      f"m=[{m_b.min():.2f},{m_b.max():.2f}] r=[{r_b.min():.2f},{r_b.max():.2f}]")
print(f"Class C binaries: n={len(x_c)} (skipped {sk_c}), "
      f"m=[{m_c.min():.2f},{m_c.max():.2f}] r=[{r_c.min():.2f},{r_c.max():.2f}]")
print()


# ── Helpers ───────────────────────────────────────────────────────────
def safe_mre(yp, yt):
    yp = np.asarray(yp, dtype=float)
    yt = np.asarray(yt, dtype=float)
    bad = ~np.isfinite(yp) | (np.abs(yt) < EPS)
    if bad.all():
        return float("nan"), float("nan")
    rel = np.abs(yp[~bad] - yt[~bad]) / np.abs(yt[~bad])
    return float(rel.mean()), float(np.abs(yp[~bad] - yt[~bad]).max())


def mcgaugh(x, c_eff):
    c_eff = np.maximum(c_eff, 1e-30)
    return (x + np.sqrt(x * x + 4.0 * c_eff * x)) / 2.0


# ── 11 new forms ──────────────────────────────────────────────────────
def predict_radius_linear_c(x, m, r, p):
    log_c0, beta_r = p
    log_c0 = np.clip(log_c0, -30.0, -18.0)
    c_eff = np.exp(log_c0 + beta_r * r)
    return mcgaugh(x, c_eff)


def predict_radius_quadratic_c(x, m, r, p):
    log_c0, alpha_r, gamma_r = p
    log_c0 = np.clip(log_c0, -30.0, -18.0)
    expo = np.clip(alpha_r * r + gamma_r * r * r, -40.0, 40.0)
    c_eff = np.exp(log_c0 + expo)
    return mcgaugh(x, c_eff)


def predict_joint_mass_radius(x, m, r, p):
    log_c0, alpha_m, beta_r = p
    log_c0 = np.clip(log_c0, -30.0, -18.0)
    expo = np.clip(alpha_m * (m - 10.0) + beta_r * r, -40.0, 40.0)
    return mcgaugh(x, np.exp(log_c0 + expo))


def predict_joint_quadratic(x, m, r, p):
    log_c0, alpha_m, beta_r, gamma_mr = p
    log_c0 = np.clip(log_c0, -30.0, -18.0)
    expo = np.clip(alpha_m * (m - 10.0) + beta_r * r + gamma_mr * (m - 10.0) * r,
                   -40.0, 40.0)
    return mcgaugh(x, np.exp(log_c0 + expo))


def predict_gbar_threshold(x, m, r, p):
    log_g_dag, delta, alpha = p
    g_dag = np.exp(np.clip(log_g_dag, -30.0, -18.0))
    base = mcgaugh(x, g_dag)
    z = np.log10(np.maximum(x / g_dag, 1e-30))
    z = np.clip(z, -30.0, 30.0)
    return base * (1.0 + delta * np.tanh(alpha * z))


def predict_efe_linear(x, m, r, p):
    log_c0, lam, log_g_dag = p
    log_c0 = np.clip(log_c0, -30.0, -18.0)
    log_g_dag = np.clip(log_g_dag, -30.0, -18.0)
    g_dag = np.exp(log_g_dag)
    g_ext = np.exp(np.clip(lam * r, -40.0, 40.0))
    c_eff = np.exp(log_c0) / (1.0 + g_ext / g_dag)
    return mcgaugh(x, c_eff)


def predict_efe_radius_deep(x, m, r, p):
    log_c0, lam, r0 = p
    log_c0 = np.clip(log_c0, -30.0, -18.0)
    gate = (1.0 + np.tanh(np.clip(lam * (r - r0), -40.0, 40.0))) / 2.0
    c_eff = np.exp(log_c0) * gate + 1e-30
    return mcgaugh(x, c_eff)


def predict_radius_piecewise(x, m, r, p):
    """CATEGORY_SWITCH on radius: small_r → Newton-ish, large_r → deep MOND."""
    log_c_low, log_c_high, r_split = p
    log_c_low = np.clip(log_c_low, -30.0, -18.0)
    log_c_high = np.clip(log_c_high, -30.0, -18.0)
    c_low = np.exp(log_c_low)
    c_high = np.exp(log_c_high)
    c_eff = np.where(r < r_split, c_low, c_high)
    return mcgaugh(x, c_eff)


def predict_joint_interp(x, m, r, p):
    log_c0, alpha_m, beta_r, gamma_mr, m0, r0 = p
    log_c0 = np.clip(log_c0, -30.0, -18.0)
    expo = np.clip(alpha_m * (m - m0) + beta_r * (r - r0)
                   + gamma_mr * (m - m0) * (r - r0), -40.0, 40.0)
    return mcgaugh(x, np.exp(log_c0 + expo))


def predict_log_ratio_bivariate(x, m, r, p):
    """log10(y/x) = alpha + beta * log10(x/g_dag) + gamma * r."""
    alpha, beta, gamma, log_g_dag = p
    log_g_dag = np.clip(log_g_dag, -30.0, -18.0)
    g_dag = np.exp(log_g_dag)
    z = np.log10(np.maximum(x / g_dag, 1e-30))
    log_ratio = np.clip(alpha + beta * z + gamma * r, -10.0, 10.0)
    return x * np.power(10.0, log_ratio)


def predict_newton_mond_hybrid(x, m, r, p):
    """y = (x + sqrt(x^2 + 4*g_dag*x*(1+delta*r)))/2."""
    log_g_dag, delta = p
    log_g_dag = np.clip(log_g_dag, -30.0, -18.0)
    g_dag = np.exp(log_g_dag)
    factor = np.maximum(1.0 + delta * r, 1e-6)
    c_eff = g_dag * factor
    return mcgaugh(x, c_eff)


# ── Candidate registry ────────────────────────────────────────────────
def init_loguniform(lo, hi):
    return np.log(10 ** NP_RNG.uniform(np.log10(np.exp(1)) and lo, hi)) if False else None


def U(lo, hi):
    return float(NP_RNG.uniform(lo, hi))


CANDIDATES = [
    {
        "name": "RADIUS_LINEAR_C",
        "K": 2,
        "predict": predict_radius_linear_c,
        "bounds": [(-28, -18), (-2, 2)],
        "init": lambda: [U(-28, -18), U(-2, 2)],
    },
    {
        "name": "RADIUS_QUADRATIC_C",
        "K": 3,
        "predict": predict_radius_quadratic_c,
        "bounds": [(-28, -18), (-2, 2), (-1, 1)],
        "init": lambda: [U(-28, -18), U(-2, 2), U(-1, 1)],
    },
    {
        "name": "JOINT_MASS_RADIUS",
        "K": 3,
        "predict": predict_joint_mass_radius,
        "bounds": [(-28, -18), (-1, 1), (-1, 1)],
        "init": lambda: [U(-28, -18), U(-1, 1), U(-1, 1)],
    },
    {
        "name": "JOINT_QUADRATIC",
        "K": 4,
        "predict": predict_joint_quadratic,
        "bounds": [(-28, -18), (-1, 1), (-1, 1), (-0.5, 0.5)],
        "init": lambda: [U(-28, -18), U(-1, 1), U(-1, 1), U(-0.5, 0.5)],
    },
    {
        "name": "GBAR_THRESHOLD_PW",
        "K": 3,
        "predict": predict_gbar_threshold,
        "bounds": [(-28, -20), (-0.5, 0.5), (-2, 2)],
        "init": lambda: [U(-28, -20), U(-0.5, 0.5), U(-2, 2)],
    },
    {
        "name": "EFE_LINEAR",
        "K": 3,
        "predict": predict_efe_linear,
        "bounds": [(-28, -18), (-3, 3), (-28, -20)],
        "init": lambda: [U(-28, -18), U(-3, 3), U(-28, -20)],
    },
    {
        "name": "EFE_RADIUS_DEEP",
        "K": 3,
        "predict": predict_efe_radius_deep,
        "bounds": [(-28, -18), (-5, 5), (-1, 2)],
        "init": lambda: [U(-28, -18), U(-5, 5), U(-1, 2)],
    },
    {
        "name": "RADIUS_PIECEWISE",
        "K": 3,
        "predict": predict_radius_piecewise,
        "bounds": [(-28, -18), (-28, -18), (-1, 2)],
        "init": lambda: [U(-28, -18), U(-28, -18), U(-1, 2)],
    },
    {
        "name": "JOINT_INTERP",
        "K": 6,
        "predict": predict_joint_interp,
        "bounds": [(-28, -18), (-1, 1), (-1, 1), (-0.5, 0.5), (9, 11), (-0.5, 1)],
        "init": lambda: [U(-28, -18), U(-1, 1), U(-1, 1),
                         U(-0.5, 0.5), U(9, 11), U(-0.5, 1)],
    },
    {
        "name": "LOG_RATIO_BIVARIATE",
        "K": 4,
        "predict": predict_log_ratio_bivariate,
        "bounds": [(-2, 2), (-2, 2), (-2, 2), (-28, -20)],
        "init": lambda: [U(-2, 2), U(-2, 2), U(-2, 2), U(-28, -20)],
    },
    {
        "name": "NEWTON_MOND_HYBRID",
        "K": 2,
        "predict": predict_newton_mond_hybrid,
        "bounds": [(-28, -20), (-0.5, 0.5)],
        "init": lambda: [U(-28, -20), U(-0.5, 0.5)],
    },
]


# ── Fitting ───────────────────────────────────────────────────────────
def loss_log_residual(params, predict, x, y, m, r):
    try:
        yp = predict(x, m, r, params)
    except Exception:
        return 1e20
    if not np.all(np.isfinite(yp)):
        return 1e20
    yp = np.maximum(yp, EPS)
    yt = np.maximum(y, EPS)
    diff = np.log(yp) - np.log(yt)
    if not np.all(np.isfinite(diff)):
        return 1e20
    return float(np.mean(diff * diff))


def fit_candidate(cand, x, y, m, r, n_starts=5):
    best = None
    best_loss = float("inf")
    for _ in range(n_starts):
        x0 = cand["init"]()
        try:
            res = minimize(
                loss_log_residual,
                x0,
                args=(cand["predict"], x, y, m, r),
                method="L-BFGS-B",
                bounds=cand["bounds"],
                options={"maxiter": 800, "ftol": 1e-11},
            )
            if np.isfinite(res.fun) and res.fun < best_loss:
                best_loss = float(res.fun)
                best = res
        except Exception:
            pass
        # also try Nelder-Mead unbounded as a robustness pass
        try:
            res2 = minimize(
                loss_log_residual,
                x0,
                args=(cand["predict"], x, y, m, r),
                method="Nelder-Mead",
                options={"maxiter": 4000, "xatol": 1e-8, "fatol": 1e-10},
            )
            if np.isfinite(res2.fun) and res2.fun < best_loss:
                best_loss = float(res2.fun)
                best = res2
        except Exception:
            pass
    # If still poor, escalate to differential_evolution
    if best is None or best_loss > 5.0:
        try:
            res3 = differential_evolution(
                loss_log_residual,
                bounds=cand["bounds"],
                args=(cand["predict"], x, y, m, r),
                seed=42,
                maxiter=200,
                tol=1e-9,
                polish=True,
                workers=1,
            )
            if np.isfinite(res3.fun) and res3.fun < best_loss:
                best_loss = float(res3.fun)
                best = res3
        except Exception:
            pass
    return best


# ── Run ───────────────────────────────────────────────────────────────
results = []
for cand in CANDIDATES:
    res = fit_candidate(cand, x_fit, y_fit, m_fit, r_fit, n_starts=5)
    if res is None:
        results.append({
            "name": cand["name"], "K": cand["K"], "params": None,
            "converged": False,
            "fit_mre": float("nan"), "ho_mre": float("nan"),
            "b_mre": float("nan"), "c_mre": float("nan"),
            "loss": float("nan"),
        })
        continue
    p = res.x
    yp_fit = cand["predict"](x_fit, m_fit, r_fit, p)
    yp_aho = cand["predict"](x_aho, m_aho, r_aho, p)
    yp_b = cand["predict"](x_b, m_b, r_b, p)
    yp_c = cand["predict"](x_c, m_c, r_c, p)
    fit_mre, _ = safe_mre(yp_fit, y_fit)
    ho_mre, _ = safe_mre(yp_aho, y_aho)
    b_mre, _ = safe_mre(yp_b, y_b)
    c_mre, _ = safe_mre(yp_c, y_c)
    results.append({
        "name": cand["name"], "K": cand["K"], "params": p,
        "converged": bool(getattr(res, "success", True)),
        "fit_mre": fit_mre, "ho_mre": ho_mre,
        "b_mre": b_mre, "c_mre": c_mre,
        "loss": float(res.fun),
    })


# ── Table ─────────────────────────────────────────────────────────────
def fmt(v):
    if not np.isfinite(v):
        return "  nan  "
    if v >= 1e3:
        return f"{v:.2e}"
    return f"{v:7.4f}"


hdr = (f"{'form_name':<22}{'K':>3}  "
       f"{'A_fit':>8}  {'A_HO':>8}  {'B_clust':>8}  {'C_binar':>8}  "
       f"{'A<.5':>5}{'B<.5':>5}{'C<.5':>5}  {'conv':>5}")
print("=" * len(hdr))
print(hdr)
print("-" * len(hdr))
for r in results:
    a_pass = np.isfinite(r["ho_mre"]) and r["ho_mre"] < 0.5
    b_pass = np.isfinite(r["b_mre"]) and r["b_mre"] < 0.5
    c_pass = np.isfinite(r["c_mre"]) and r["c_mre"] < 0.5
    print(
        f"{r['name']:<22}{r['K']:>3}  "
        f"{fmt(r['fit_mre']):>8}  {fmt(r['ho_mre']):>8}  "
        f"{fmt(r['b_mre']):>8}  {fmt(r['c_mre']):>8}  "
        f"{'Y' if a_pass else '-':>5}{'Y' if b_pass else '-':>5}{'Y' if c_pass else '-':>5}  "
        f"{str(r['converged']):>5}"
    )
print("=" * len(hdr))

# Best per class
best_a = min((r for r in results if np.isfinite(r['ho_mre'])), key=lambda x: x['ho_mre'], default=None)
best_b = min((r for r in results if np.isfinite(r['b_mre'])), key=lambda x: x['b_mre'], default=None)
best_c = min((r for r in results if np.isfinite(r['c_mre'])), key=lambda x: x['c_mre'], default=None)
print("\nBest per class:")
if best_a: print(f"  A_HO best: {best_a['name']} = {best_a['ho_mre']:.4f}")
if best_b: print(f"  B    best: {best_b['name']} = {best_b['b_mre']:.4f}")
if best_c: print(f"  C    best: {best_c['name']} = {best_c['c_mre']:.4f}")

# Cross-class pass check
print("\nCross-class MRE<0.5 (A_HO + B + C simultaneously)?")
any_pass = False
near_misses = []
for r in results:
    ok = (np.isfinite(r["ho_mre"]) and np.isfinite(r["b_mre"]) and np.isfinite(r["c_mre"])
          and r["ho_mre"] < 0.5 and r["b_mre"] < 0.5 and r["c_mre"] < 0.5)
    if ok:
        any_pass = True
    near_misses.append((max(r['ho_mre'] if np.isfinite(r['ho_mre']) else 99,
                            r['b_mre'] if np.isfinite(r['b_mre']) else 99,
                            r['c_mre'] if np.isfinite(r['c_mre']) else 99),
                        r['name']))
    print(f"  {r['name']:<22} {'PASS' if ok else 'FAIL'}")
print(f"\nANY form passes? {any_pass}")
near_misses.sort()
print("\nTightest worst-class MREs (sorted by max-of-3):")
for worst, name in near_misses[:5]:
    print(f"  {name:<22} worst-class MRE = {worst:.4f}")

# Per-class which is the resistant one across all forms
print("\nPer-class average MRE across all forms (which class is hardest):")
for cls_label, key in [("A_HO", "ho_mre"), ("B_clust", "b_mre"), ("C_binar", "c_mre")]:
    vs = [r[key] for r in results if np.isfinite(r[key])]
    if vs:
        print(f"  {cls_label}: mean={np.mean(vs):.3f}  median={np.median(vs):.3f}  min={np.min(vs):.3f}")

print("\nFitted parameters for the best worst-class form:")
near_misses.sort()
best_name = near_misses[0][1]
best_r = next(r for r in results if r["name"] == best_name)
print(f"  {best_name}: K={best_r['K']} loss={best_r['loss']:.4e}")
print(f"  params = {[float(v) for v in best_r['params']]}")
