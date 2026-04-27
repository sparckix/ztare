#!/usr/bin/env python3
"""GP-154i — convention-pair overlap census + offline T feasibility test
(2026-04-25 night, post void-family null).

Per user request "v4 conversion transform alive — how to test?":

The v4 charter reframes the target as
    T(α_observed, source_conv, target_conv, N, D, C) → α_target_conv
This is mathematically distinct from `α = f(features)` (which gp154h killed).
But T's testability on the existing 94-row dataset depends on:

  (1) Do convention pairs share enough (log_N, log_D) overlap that
      paired α-comparisons exist?
  (2) If yes, does a low-K transform fit those pairs at HOLDOUT MRE
      below the v4 charter threshold (0.25)?

This script answers both. If census fails (no/few overlap pairs), v4
dies cheaply tonight without a run — its dataset support is too thin.
If census passes and fits work, v4 has signal worth an apparatus run
(or T14 external holdout to validate).
"""
from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
PROJECT_DIR = _REPO / "projects" / "gp154_scaling_law_exponents"
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(PROJECT_DIR))

import features as _feats  # noqa: E402

FEATURES = _feats.FEATURES


def load_attributed_alphas() -> dict[int, float]:
    out: dict[int, float] = {}
    text_v = (PROJECT_DIR / "evidence.txt").read_text(encoding="utf-8")
    section = "VISIBLE"
    for raw in text_v.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            if "===" in line:
                upper = line.upper()
                section = "VISIBLE" if "VISIBLE_SET" in upper or "VISIBLE-SET" in upper else "OTHER"
            continue
        if section != "VISIBLE":
            continue
        parts = line.split("\t") if "\t" in line else line.split()
        if len(parts) < 2:
            continue
        try:
            out[int(parts[0])] = float(parts[1])
        except (ValueError, IndexError):
            continue
    section = None
    for raw in (PROJECT_DIR / "evidence_holdout.txt").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            if "===" in line:
                upper = line.upper()
                section = "H" if "HOLDOUT_SET" in upper and "FARTHER" not in upper else None
            continue
        if section != "H":
            continue
        parts = line.split("\t") if "\t" in line else line.split()
        if len(parts) < 2:
            continue
        try:
            out[int(parts[0])] = float(parts[1])
        except (ValueError, IndexError):
            continue
    return out


ALPHAS = load_attributed_alphas()
try:
    for rid, y, _ in _feats.visible_rows():
        if rid not in ALPHAS and y is not None:
            ALPHAS[int(rid)] = float(y)
except Exception:
    pass


def get_log_N(rid: int) -> float | None:
    fd = FEATURES.get(rid, {})
    v = fd.get("log10_N_params")
    return float(v) if v is not None else None


def get_log_D(rid: int) -> float | None:
    fd = FEATURES.get(rid, {})
    v = fd.get("dataset_log10_tokens")
    return float(v) if v is not None else None


def get_conv(rid: int) -> str:
    return FEATURES.get(rid, {}).get("fit_convention", "") or "unknown"


# ── PHASE 1: Convention-pair overlap census ─────────────────────────────
# Bin by log_N (Δ=0.5 dex) only — D is unavailable for most rows.
# A "pair" = two rows from different conventions in the same log_N bin.

print("=" * 80)
print("GP-154i — v4 conversion-transform feasibility test")
print(f"Pool: {len(ALPHAS)} attributed rows")
print("=" * 80)
print()

print("── Phase 1: Convention-pair overlap census (bin by log_N, Δ=0.5 dex) ──")
print()

# Build (conv, log_N_bin) → list[(rid, alpha, log_N, log_D)]
bin_index: dict[tuple[str, int], list[tuple[int, float, float, float | None]]] = defaultdict(list)
for rid, alpha in ALPHAS.items():
    log_N = get_log_N(rid)
    if log_N is None:
        continue
    conv = get_conv(rid)
    log_N_bin = round(log_N * 2) / 2  # 0.5-dex binning
    bin_index[(conv, log_N_bin)].append((rid, alpha, log_N, get_log_D(rid)))

# All conventions present
conventions = sorted({c for (c, _) in bin_index.keys()})
print(f"Conventions present (n={len(conventions)}):")
for c in conventions:
    n = sum(len(v) for (cc, _), v in bin_index.items() if cc == c)
    print(f"  {c!r}: {n} rows")
print()

# Pair census: for each ordered convention pair (A, B), count rows in shared bins
print(f"{'Source → Target':<48} {'n_pairs':<10} {'n_bins_shared':<15}")
print("-" * 76)
pair_counts: dict[tuple[str, str], list[tuple[int, int, float, float, float, float | None, float | None]]] = defaultdict(list)
# Each pair entry: (rid_A, rid_B, alpha_A, alpha_B, log_N (avg), log_D_A, log_D_B)

for (conv_A, conv_B) in combinations(conventions, 2):
    # Find shared log_N bins
    bins_A = {b for (c, b) in bin_index.keys() if c == conv_A}
    bins_B = {b for (c, b) in bin_index.keys() if c == conv_B}
    shared_bins = bins_A & bins_B
    n_pairs = 0
    for b in shared_bins:
        for (rid_A, alpha_A, lN_A, lD_A) in bin_index[(conv_A, b)]:
            for (rid_B, alpha_B, lN_B, lD_B) in bin_index[(conv_B, b)]:
                pair_counts[(conv_A, conv_B)].append(
                    (rid_A, rid_B, alpha_A, alpha_B, (lN_A + lN_B) / 2, lD_A, lD_B)
                )
                n_pairs += 1
    if n_pairs > 0:
        print(f"  {conv_A} → {conv_B:<28} {n_pairs:<10} {len(shared_bins):<15}")

print()

# Identify viable pairs (>= 5 pair instances for K=2 fit, >= 10 for K=4)
viable_K2 = [(p, len(v)) for p, v in pair_counts.items() if len(v) >= 5]
viable_K4 = [(p, len(v)) for p, v in pair_counts.items() if len(v) >= 10]

print(f"Viable pairs for K=2 transform (≥5 pairs): {len(viable_K2)}")
for (p, n) in viable_K2:
    print(f"  {p[0]} → {p[1]}: {n} pair instances")
print()
print(f"Viable pairs for K=4 transform (≥10 pairs): {len(viable_K4)}")
for (p, n) in viable_K4:
    print(f"  {p[0]} → {p[1]}: {n} pair instances")
print()

if not viable_K2:
    print("=" * 80)
    print(">>> CENSUS FAILS — no convention pair has ≥5 overlap instances.")
    print("    The v4 conversion-transform target is EMPIRICALLY UNTESTABLE on")
    print("    the existing 94-row dataset. T14 external holdout is the ONLY")
    print("    path to a v4 validation claim.")
    print("=" * 80)
    sys.exit(0)


# ── PHASE 2: Offline transform fit for each viable pair ──────────────────
# For each viable pair (A, B):
#   K=2:  alpha_B = a + b * alpha_A
#   K=4:  alpha_B = a + b * alpha_A + c * log_N + d * (log_D if both have it else 0)
# 5-fold CV with simple shuffled folds (overlap pairs are too few for stratification).

import random


def fit_linear(X: list[list[float]], y: list[float]) -> list[float]:
    """Naive least-squares via normal equations. X is N×K, y is N×1."""
    K = len(X[0])
    N = len(X)
    # X^T X (K×K)
    XtX = [[0.0] * K for _ in range(K)]
    Xty = [0.0] * K
    for i in range(N):
        for j in range(K):
            for k in range(K):
                XtX[j][k] += X[i][j] * X[i][k]
            Xty[j] += X[i][j] * y[i]
    # Tikhonov regularization to handle near-singular pairs
    for j in range(K):
        XtX[j][j] += 1e-6
    # Gaussian elimination
    M = [row[:] + [Xty[j]] for j, row in enumerate(XtX)]
    for j in range(K):
        # Pivot
        max_row = j
        for r in range(j + 1, K):
            if abs(M[r][j]) > abs(M[max_row][j]):
                max_row = r
        M[j], M[max_row] = M[max_row], M[j]
        if abs(M[j][j]) < 1e-12:
            return [0.0] * K
        for r in range(K):
            if r != j:
                factor = M[r][j] / M[j][j]
                for c in range(K + 1):
                    M[r][c] -= factor * M[j][c]
    return [M[j][K] / M[j][j] for j in range(K)]


def kfold_mre(features: list[list[float]], y: list[float], k: int = 5, seed: int = 42) -> tuple[float, float]:
    rng = random.Random(seed)
    idx = list(range(len(y)))
    rng.shuffle(idx)
    folds = [idx[i::k] for i in range(k)]
    fold_mres = []
    for fi in range(k):
        test_idx = set(folds[fi])
        Xtr = [features[i] for i in range(len(y)) if i not in test_idx]
        ytr = [y[i] for i in range(len(y)) if i not in test_idx]
        Xte = [features[i] for i in test_idx]
        yte = [y[i] for i in test_idx]
        if len(Xtr) < len(Xtr[0]):
            continue
        beta = fit_linear(Xtr, ytr)
        errs = []
        for x_i, y_i in zip(Xte, yte):
            pred = sum(b * x for b, x in zip(beta, x_i))
            denom = abs(y_i) if y_i != 0 else 1e-12
            errs.append(abs(pred - y_i) / denom)
        if errs:
            fold_mres.append(sum(errs) / len(errs))
    if not fold_mres:
        return float("inf"), float("inf")
    mean = sum(fold_mres) / len(fold_mres)
    var = sum((m - mean) ** 2 for m in fold_mres) / len(fold_mres)
    return mean, math.sqrt(var)


print("── Phase 2: Offline transform fit per viable pair ──")
print()
print(f"{'Pair':<55} {'K':<3} {'mean MRE':<11} {'std':<10} {'n':<5}")
print("-" * 90)

best = (float("inf"), None, None)

for (conv_A, conv_B), pairs in pair_counts.items():
    if len(pairs) < 5:
        continue

    # K=2: alpha_B = a + b * alpha_A
    X_K2 = [[1.0, alpha_A] for (_, _, alpha_A, _, _, _, _) in pairs]
    y = [alpha_B for (_, _, _, alpha_B, _, _, _) in pairs]
    mean, std = kfold_mre(X_K2, y, k=min(5, len(pairs)))
    print(f"  {conv_A} → {conv_B:<32} K=2  {mean:<11.4f} {std:<10.4f} {len(pairs):<5}")
    if mean < best[0]:
        best = (mean, f"{conv_A} → {conv_B}", "K=2 linear")

    # K=4: alpha_B = a + b * alpha_A + c * log_N + d * (log_D if available else 0)
    if len(pairs) >= 10:
        X_K4 = []
        for (_, _, alpha_A, _, log_N, lD_A, lD_B) in pairs:
            d_term = 0.0
            if lD_A is not None and lD_B is not None:
                d_term = (lD_A + lD_B) / 2
            X_K4.append([1.0, alpha_A, log_N, d_term])
        mean4, std4 = kfold_mre(X_K4, y, k=min(5, len(pairs)))
        print(f"  {conv_A} → {conv_B:<32} K=4  {mean4:<11.4f} {std4:<10.4f} {len(pairs):<5}")
        if mean4 < best[0]:
            best = (mean4, f"{conv_A} → {conv_B}", "K=4 modulated")

print()
print("=" * 80)
print(f"BEST: {best[1]} ({best[2]}) → mean CV MRE = {best[0]:.4f}")
print()
print("Charter v4 success threshold:    < 0.25")
print(f"Best offline result:             {best[0]:.4f}")
print()
if best[0] < 0.25:
    print(">>> v4 PASSES OFFLINE on existing data.")
    print("    Conversion transform is empirically supported. Apparatus run")
    print("    on v4 charter is justified. (Caveat: T14 external holdout still")
    print("    required for confirmatory Nature MI claim per panel verdict.)")
elif best[0] < 1.0:
    print(">>> v4 SUGGESTIVE — transform exists but doesn't hit 0.25 threshold.")
    print("    Worth running apparatus to see if it can find a non-linear T.")
    print("    External holdout (T14) needed for any validation claim.")
else:
    print(">>> v4 OFFLINE NULL — even paired α's between conventions don't")
    print("    admit a low-K linear transform at the v4 threshold.")
    print("    Either: (a) T is highly non-linear and the apparatus might")
    print("    find it, or (b) the conversion-transform target is also")
    print("    K≤7-impossible on this data and v4 needs T14 to even start.")
print("=" * 80)
