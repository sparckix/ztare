"""GP-080 Stage 2 GT — Noisy variant of the bi-exponential substrate.

Adds proportional Gaussian noise (5% of signal) to f_true outputs.
Fixed seed for reproducibility. Division A artifact.

Variable naming (Division A internal only — Division B sees x1, x2):
  x1 = time post-dose (hours)
  x2 = administered dose (mg)
  z  = whole-blood concentration (ng/mL) + noise
"""
from __future__ import annotations

import math
import random

from src.ztare.substrates.gp080_tacrolimus_gt import (
    evidence_grid as _clean_evidence_grid,
    f_true as _f_true_clean,
    holdout_grid as _clean_holdout_grid,
)

_NOISE_FRACTION = 0.05  # 5% proportional noise
_VISIBLE_SEED = 42
_HOLDOUT_SEED = 137


def f_true(x1: float, x2: float) -> float:
    """Clean GT — used by residual diagnostics and internal checks."""
    return _f_true_clean(x1, x2)


def f_dominant(x1: float, x2: float) -> float:
    """Dominant phase — re-export for residual diagnostics."""
    from src.ztare.substrates.gp080_tacrolimus_gt import f_dominant as _fd
    return _fd(x1, x2)


def _noisy_value(x1: float, x2: float, rng: random.Random) -> float:
    """Add proportional Gaussian noise to clean value."""
    clean = _f_true_clean(x1, x2)
    noise = rng.gauss(0, _NOISE_FRACTION * abs(clean)) if clean != 0 else 0.0
    return clean + noise


def evidence_grid() -> list[tuple[float, float]]:
    return _clean_evidence_grid()


def holdout_grid() -> list[tuple[float, float]]:
    return _clean_holdout_grid()


def evidence_triples_noisy() -> list[tuple[float, float, float]]:
    """Visible evidence with noise applied (fixed seed)."""
    rng = random.Random(_VISIBLE_SEED)
    return [(x1, x2, _noisy_value(x1, x2, rng)) for x1, x2 in evidence_grid()]


def holdout_triples_noisy() -> list[tuple[float, float, float]]:
    """Holdout evidence with noise applied (different fixed seed)."""
    rng = random.Random(_HOLDOUT_SEED)
    return [(x1, x2, _noisy_value(x1, x2, rng)) for x1, x2 in holdout_grid()]


def holdout_triples_clean() -> list[tuple[float, float, float]]:
    """Holdout evidence WITHOUT noise — tests form recovery."""
    return [(x1, x2, _f_true_clean(x1, x2)) for x1, x2 in holdout_grid()]


if __name__ == "__main__":
    print(f"GP-080 Stage 2 GT (noise={_NOISE_FRACTION*100:.0f}%)")
    print()
    triples = evidence_triples_noisy()
    clean_vals = [_f_true_clean(x1, x2) for x1, x2 in evidence_grid()]
    noisy_vals = [z for _, _, z in triples]
    diffs = [abs(n - c) for n, c in zip(noisy_vals, clean_vals)]
    rmse = math.sqrt(sum(d**2 for d in diffs) / len(diffs))
    print(f"Visible set: {len(triples)} points, noise RMSE = {rmse:.6f}")
    print(f"Mean |z| = {sum(abs(c) for c in clean_vals)/len(clean_vals):.4f}")
    print()
    for x1, x2, z in triples[:6]:
        clean = _f_true_clean(x1, x2)
        print(f"  x1={x1:5.1f}  x2={x2:.0f}  z_clean={clean:.6f}  z_noisy={z:.6f}  diff={z-clean:+.6f}")
    print(f"  ... ({len(triples)} total)")
