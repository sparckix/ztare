"""Reusable statistical utilities for experimental discipline.

Domain-agnostic. Importable by any ZTARE experimental program. Forecasting-
specific wrappers live in the per-project workspace (e.g. calibration_stats.py).

Public API
----------
Power:
  n_required_for_rho(rho, alpha, power, spearman)        -> N
  detectable_rho_at_n(n, alpha, power, spearman)         -> |ρ|
  n_required_for_brier_delta(delta, sd_brier, alpha, power) -> N

Inference:
  bootstrap_ci(values, statistic, n_boot, ci, seed)      -> (point, lo, hi)
  paired_permutation_test(a, b, n_perm, seed, ci_level)  -> dict
  spearman_rho(xs, ys)                                   -> ρ
  spearman_rho_with_ci(xs, ys, ci)                       -> (ρ, lo, hi)

Equivalence / FDR / verdicts:
  tost_equivalence(a, b, equiv_bound, n_boot, seed)      -> dict
  bh_fdr(p_values_with_labels, alpha)                    -> list of dicts
  power_aware_verdict(rho, n, target_rho, alpha, power)  -> (verdict, note)

Bayesian:
  bf_bic_paired_t(a, b)                                  -> dict

Reproducibility:
  reproducibility_hash(prompt_template, dispatcher_version, ...) -> str
"""
from __future__ import annotations
import hashlib
import json
import math
import random
from statistics import mean, stdev
from typing import Callable, Iterable, Sequence

# ======================== Power calculations ========================

_Z = {
    ("alpha", 0.05): 1.959963984540054,
    ("alpha", 0.01): 2.5758293035489004,
    ("alpha", 0.10): 1.6448536269514722,
    ("power", 0.80): 0.8416212335729143,
    ("power", 0.90): 1.2815515655446004,
    ("power", 0.95): 1.6448536269514722,
}
_SPEARMAN_CORRECTION = 1.06  # ~6% SE inflation vs Pearson r


def _z_alpha_power(alpha: float, power: float) -> tuple:
    za = _Z.get(("alpha", alpha)); zp = _Z.get(("power", power))
    if za is None or zp is None:
        raise ValueError(f"unsupported alpha={alpha} or power={power}")
    return za, zp


def n_required_for_rho(rho_target: float, alpha: float = 0.05,
                        power: float = 0.80, spearman: bool = True) -> int | None:
    """Approximate N for a target correlation ρ at α / power. Fisher-z based."""
    if abs(rho_target) >= 1.0 or rho_target == 0:
        return None
    za, zp = _z_alpha_power(alpha, power)
    fz = 0.5 * math.log((1 + abs(rho_target)) / (1 - abs(rho_target)))
    n = ((za + zp) / fz) ** 2 + 3
    if spearman:
        n *= _SPEARMAN_CORRECTION
    return int(math.ceil(n))


def detectable_rho_at_n(n: int, alpha: float = 0.05,
                         power: float = 0.80, spearman: bool = True) -> float | None:
    """Smallest |ρ| detectable at this N. Inverse of n_required_for_rho."""
    if n <= 3:
        return None
    za, zp = _z_alpha_power(alpha, power)
    n_eff = (n - 3) / (_SPEARMAN_CORRECTION if spearman else 1.0)
    fz = (za + zp) / math.sqrt(n_eff)
    return (math.exp(2 * fz) - 1) / (math.exp(2 * fz) + 1)


def n_required_for_brier_delta(delta_target: float, sd_brier: float = 0.20,
                                 alpha: float = 0.05, power: float = 0.80) -> int | None:
    """Paired-design N for a target Brier-delta. Assumes Gaussian per-contract diffs."""
    if delta_target == 0:
        return None
    za, zp = _z_alpha_power(alpha, power)
    n = 2 * ((za + zp) ** 2) * (sd_brier / abs(delta_target)) ** 2
    return int(math.ceil(n))


# ======================== Bootstrap CI ========================

def bootstrap_ci(values: Sequence[float],
                 statistic: Callable[[Sequence[float]], float] | None = None,
                 n_boot: int = 2000, ci: float = 0.95, seed: int = 42) -> tuple:
    """Percentile bootstrap CI on a statistic. Default statistic is mean."""
    if not values:
        return None, None, None
    if statistic is None:
        statistic = lambda xs: sum(xs) / len(xs)
    n = len(values)
    point = statistic(values)
    if n < 2:
        return point, None, None
    rng = random.Random(seed)
    estimates = []
    for _ in range(n_boot):
        sample = [values[rng.randint(0, n - 1)] for _ in range(n)]
        estimates.append(statistic(sample))
    estimates.sort()
    lo_idx = int((1 - ci) / 2 * n_boot)
    hi_idx = min(int((1 + ci) / 2 * n_boot), n_boot - 1)
    return point, estimates[lo_idx], estimates[hi_idx]


# ======================== Paired permutation test ========================

def paired_permutation_test(values_a: Sequence[float], values_b: Sequence[float],
                             n_perm: int = 5000, seed: int = 42,
                             ci_level: float = 0.95) -> dict:
    """Sign-flip permutation test on paired differences."""
    if len(values_a) != len(values_b):
        return {"error": "paired length mismatch"}
    n = len(values_a)
    if n < 5:
        return {"n_paired": n, "observed_delta": None, "p_value": None,
                "note": f"insufficient paired observations (n={n} < 5)"}
    diffs = [a - b for a, b in zip(values_a, values_b)]
    obs = sum(diffs) / n
    rng = random.Random(seed)
    n_extreme = 0
    for _ in range(n_perm):
        signs = [1 if rng.random() < 0.5 else -1 for _ in diffs]
        perm = sum(s * d for s, d in zip(signs, diffs)) / n
        if abs(perm) >= abs(obs):
            n_extreme += 1
    p_value = (n_extreme + 1) / (n_perm + 1)
    _, lo, hi = bootstrap_ci(diffs, ci=ci_level, seed=seed)
    return {"n_paired": n, "observed_delta": round(obs, 4),
            "ci_lo": round(lo, 4) if lo is not None else None,
            "ci_hi": round(hi, 4) if hi is not None else None,
            "p_value": round(p_value, 4)}


# ======================== Spearman ρ ========================

def _average_ranks(vs: Sequence[float]) -> list:
    idx = sorted(range(len(vs)), key=lambda i: vs[i])
    ranks = [0.0] * len(vs)
    i = 0
    while i < len(idx):
        j = i
        while j + 1 < len(idx) and vs[idx[j + 1]] == vs[idx[i]]:
            j += 1
        avg_rank = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[idx[k]] = avg_rank
        i = j + 1
    return ranks


def spearman_rho(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 4:
        return None
    rx, ry = _average_ranks(xs), _average_ranks(ys)
    n = len(rx)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
    dx = math.sqrt(sum((v - mx) ** 2 for v in rx))
    dy = math.sqrt(sum((v - my) ** 2 for v in ry))
    if dx * dy == 0:
        return 0.0
    return num / (dx * dy)


def spearman_rho_with_ci(xs: Sequence[float], ys: Sequence[float],
                          ci: float = 0.95) -> tuple:
    rho = spearman_rho(xs, ys)
    if rho is None or abs(rho) >= 1.0:
        return rho, None, None
    n = len(xs)
    if n < 4:
        return rho, None, None
    z_crit = _Z[("alpha", 1 - ci)] if (1 - ci) in (0.05, 0.01, 0.10) else 1.96
    fz = 0.5 * math.log((1 + rho) / (1 - rho))
    se = 1.0 / math.sqrt(n - 3)
    z_lo, z_hi = fz - z_crit * se, fz + z_crit * se
    return rho, (math.exp(2 * z_lo) - 1) / (math.exp(2 * z_lo) + 1), \
                (math.exp(2 * z_hi) - 1) / (math.exp(2 * z_hi) + 1)


# ======================== TOST equivalence ========================

def tost_equivalence(values_a: Sequence[float], values_b: Sequence[float],
                      equiv_bound: float, n_boot: int = 5000, seed: int = 42) -> dict:
    """Two One-Sided Tests via 90% paired bootstrap CI.

    A 90% CI inside (-bound, +bound) ⇔ both one-sided 5% tests reject
    non-equivalence — the standard TOST framing.

    verdict ∈ {'equivalent_within_bound', 'not_equivalent', 'inconclusive'}
    """
    if len(values_a) != len(values_b):
        return {"error": "paired length mismatch"}
    n = len(values_a)
    if n < 4:
        return {"error": f"n={n} < 4"}
    diffs = [a - b for a, b in zip(values_a, values_b)]
    obs = sum(diffs) / n
    rng = random.Random(seed)
    estimates = []
    for _ in range(n_boot):
        sample = [diffs[rng.randint(0, n - 1)] for _ in range(n)]
        estimates.append(sum(sample) / n)
    estimates.sort()
    lo = estimates[int(0.05 * n_boot)]
    hi = estimates[min(int(0.95 * n_boot), n_boot - 1)]
    equivalent = (-equiv_bound < lo) and (hi < equiv_bound)
    not_equiv = (lo > equiv_bound) or (hi < -equiv_bound)
    verdict = ("equivalent_within_bound" if equivalent
               else ("not_equivalent" if not_equiv else "inconclusive"))
    return {"n": n, "diff": round(obs, 4),
            "ci_lo_90": round(lo, 4), "ci_hi_90": round(hi, 4),
            "equiv_bound": equiv_bound, "verdict": verdict,
            "equivalent": equivalent}


# ======================== Benjamini-Hochberg FDR ========================

def bh_fdr(p_values: Iterable[tuple], alpha: float = 0.05) -> list:
    """BH step-up. Input: iterable of (label, raw_p) tuples."""
    p_list = list(p_values)
    if not p_list:
        return []
    n = len(p_list)
    indexed = sorted(enumerate(p_list), key=lambda kv: kv[1][1])
    max_rejected = -1
    for rank, (_, (_, p)) in enumerate(indexed):
        if p <= alpha * (rank + 1) / n:
            max_rejected = rank
    out = [None] * n
    for rank, (orig_i, (label, p)) in enumerate(indexed):
        bh_crit = alpha * (rank + 1) / n
        rejected = rank <= max_rejected
        q = min(p * n / (rank + 1), 1.0)
        out[orig_i] = {"label": label, "raw_p": p,
                       "bh_critical": round(bh_crit, 5),
                       "rejected_at_alpha": rejected,
                       "q_value": round(q, 5)}
    return out


# ======================== Power-aware verdict ========================

def power_aware_verdict(observed_rho: float, n: int,
                         target_rho: float = 0.30,
                         alpha: float = 0.05, power: float = 0.80) -> tuple:
    """Resolve to ('h1_supported' | 'h0_kept' | 'inconclusive_underpowered', note).

    h1_supported              — 95% CI on ρ excludes 0 (any direction)
    h0_kept                   — 95% CI on ρ wholly within (-target, +target)
    inconclusive_underpowered — observed |ρ| below detectability; CI wide
    """
    if n <= 3:
        return "invalid_run", "n <= 3"
    detectable = detectable_rho_at_n(n, alpha=alpha, power=power)
    if abs(observed_rho) >= 1.0:
        return "h1_supported", "|ρ|=1.0"
    fz = 0.5 * math.log((1 + observed_rho) / (1 - observed_rho))
    se = 1.0 / math.sqrt(n - 3)
    z_lo, z_hi = fz - 1.96 * se, fz + 1.96 * se
    ci_lo = (math.exp(2 * z_lo) - 1) / (math.exp(2 * z_lo) + 1)
    ci_hi = (math.exp(2 * z_hi) - 1) / (math.exp(2 * z_hi) + 1)
    target = abs(target_rho)
    if ci_lo > 0 or ci_hi < 0:
        return "h1_supported", f"observed ρ={observed_rho:+.3f}; 95% CI [{ci_lo:+.3f}, {ci_hi:+.3f}] excludes 0"
    if ci_lo > -target and ci_hi < target:
        return "h0_kept", f"observed ρ={observed_rho:+.3f}; 95% CI [{ci_lo:+.3f}, {ci_hi:+.3f}] excludes ±{target}"
    return ("inconclusive_underpowered",
            f"observed |ρ|={abs(observed_rho):.3f} below N={n} detectability "
            f"|ρ|≥{detectable:.3f}; CI [{ci_lo:+.3f}, {ci_hi:+.3f}] includes both 0 and ±{target}")


# ======================== Bayes factor (BIC approximation) ========================

def bf_bic_paired_t(values_a: Sequence[float], values_b: Sequence[float]) -> dict:
    """BIC-approximation paired-t Bayes factor (Wagenmakers 2007)."""
    if len(values_a) != len(values_b):
        return {"error": "paired length mismatch"}
    n = len(values_a)
    if n < 4:
        return {"error": f"n={n} < 4"}
    diffs = [a - b for a, b in zip(values_a, values_b)]
    m = mean(diffs)
    s = stdev(diffs) if n > 1 else 0
    if s == 0:
        return {"error": "zero variance"}
    t = m / (s / math.sqrt(n))
    bic_diff = n * math.log(1 + (t ** 2) / (n - 1)) - math.log(n)
    bf_10 = math.exp(bic_diff / 2)
    if bf_10 > 10: interp = "strong evidence for H1"
    elif bf_10 > 3: interp = "moderate evidence for H1"
    elif bf_10 > 1: interp = "anecdotal evidence for H1"
    elif bf_10 > 1/3: interp = "anecdotal evidence for H0"
    elif bf_10 > 1/10: interp = "moderate evidence for H0"
    else: interp = "strong evidence for H0"
    return {"n": n, "t": round(t, 3), "bf_10": round(bf_10, 3),
            "bf_01": round(1 / bf_10, 3), "interpretation": interp}


# ======================== Multi-channel OLS R² with adjusted + LOO-CV ========================

def _ols_fit(xs_cols: Sequence[Sequence[float]], ys: Sequence[float]) -> tuple:
    """Plain OLS via normal equations. xs_cols: list of k columns (each length n).

    Returns (beta_with_intercept, y_hat). beta[0] is intercept.
    """
    n = len(ys)
    k = len(xs_cols)
    if any(len(c) != n for c in xs_cols):
        raise ValueError("column length mismatch")
    # X = [1, x1, x2, ...] as row-major nested list
    X = [[1.0] + [float(xs_cols[j][i]) for j in range(k)] for i in range(n)]
    # XtX (k+1 x k+1)
    p = k + 1
    XtX = [[sum(X[i][a] * X[i][b] for i in range(n)) for b in range(p)] for a in range(p)]
    Xty = [sum(X[i][a] * ys[i] for i in range(n)) for a in range(p)]
    # Gauss-Jordan inverse on XtX, then beta = XtX^-1 Xty.
    aug = [
        row[:] + [float(i == j) for j in range(p)]
        for i, row in enumerate(XtX)
    ]
    for i in range(p):
        pivot = aug[i][i]
        if abs(pivot) < 1e-12:
            # find swap row
            for r in range(i + 1, p):
                if abs(aug[r][i]) > 1e-12:
                    aug[i], aug[r] = aug[r], aug[i]
                    pivot = aug[i][i]
                    break
            else:
                raise ValueError("singular design matrix (collinear channels)")
        for c in range(i, 2 * p):
            aug[i][c] /= pivot
        for r in range(p):
            if r == i: continue
            factor = aug[r][i]
            if factor == 0: continue
            for c in range(i, 2 * p):
                aug[r][c] -= factor * aug[i][c]
    inverse = [row[p:] for row in aug]
    beta = [sum(inverse[i][j] * Xty[j] for j in range(p)) for i in range(p)]
    y_hat = [sum(X[i][a] * beta[a] for a in range(p)) for i in range(n)]
    leverage = [
        sum(X[i][a] * inverse[a][b] * X[i][b] for a in range(p) for b in range(p))
        for i in range(n)
    ]
    return beta, y_hat, leverage


def ols_multichannel_r2(xs_cols: Sequence[Sequence[float]], ys: Sequence[float],
                         channel_names: Sequence[str] | None = None) -> dict:
    """OLS regress ys on k channels with intercept. Reports R², adjusted R²,
    and leave-one-out cross-validated R² (Q²). LOO-CV strips the optimism bias
    that makes small-N R² unreliable.

    Returns dict with: n, k, r2, r2_adj, r2_loo, beta (display-rounded),
    beta_exact (for downstream calculations), residual_rmse, channel_names.
    r2_loo < 0 means the model predicts WORSE than the mean — overfit.
    """
    n = len(ys)
    k = len(xs_cols)
    if n < k + 2:
        return {"error": f"n={n} < k+2={k+2} (would have no residual dof)"}
    y_mean = sum(ys) / n
    ss_tot = sum((y - y_mean) ** 2 for y in ys)
    if ss_tot == 0:
        return {"error": "zero variance in ys"}

    beta, y_hat, leverage = _ols_fit(xs_cols, ys)
    ss_res = sum((ys[i] - y_hat[i]) ** 2 for i in range(n))
    r2 = 1.0 - ss_res / ss_tot
    r2_adj = 1.0 - (1.0 - r2) * (n - 1) / (n - k - 1)

    # Exact ordinary-least-squares PRESS identity: deleted residual eᵢ/(1-hᵢᵢ).
    if any(1.0 - value <= 1e-12 for value in leverage):
        return {"error": "singular design matrix in LOO fold"}
    press = sum(
        ((ys[index] - y_hat[index]) / (1.0 - leverage[index])) ** 2
        for index in range(n)
    )
    r2_loo = 1.0 - press / ss_tot

    return {
        "n": n, "k": k,
        "r2": round(r2, 4),
        "r2_adj": round(r2_adj, 4),
        "r2_loo": round(r2_loo, 4),
        "beta": [round(b, 4) for b in beta],
        "beta_exact": beta,
        "residual_rmse": math.sqrt(ss_res / max(1, n - k - 1)),
        "channel_names": list(channel_names) if channel_names else [f"x{i+1}" for i in range(k)],
    }


# ======================== Reproducibility manifest ========================

def reproducibility_hash(prompt_template: str, dispatcher_version: str,
                          corpus_row: dict, agent_id: str,
                          agent_version: str | None = None,
                          extra: dict | None = None) -> str:
    """SHA-256(16-char prefix) of inputs that produced an experimental call."""
    payload = {
        "prompt_template": prompt_template,
        "dispatcher_version": dispatcher_version,
        "corpus_row": corpus_row,
        "agent_id": agent_id,
        "agent_version": agent_version,
        "extra": extra or {},
    }
    blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]
