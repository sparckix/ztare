"""GP-152 Framer — SymmetryScanner (v2.0).

Empirical detection of:
  - Power-law scaling: y ∝ x^α (estimate α via log-log slope)
  - Additive separability: f(x_1 + x_2) ≈ f(x_1) + f(x_2)
  - Translation invariance: f(x + c) ≈ f(x)

Outputs hints to the TransformationEnumerator about which (h_in, h_out) pairs
are most likely to compress the data. The actual gate (G-SYM-FN) lives at
src/ztare/framer_gates/symmetry_false_negative_gate.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np


@dataclass
class SymmetryReport:
    power_law_alpha: float | None = None  # estimated α if y ≈ const · x^α
    is_power_law: bool = False
    additive_separable: bool = False
    translation_invariant: bool = False
    notes: List[str] = field(default_factory=list)
    suggested_h_in: List[str] = field(default_factory=list)
    suggested_h_out: List[str] = field(default_factory=list)


def scan_symmetries(x: np.ndarray, y: np.ndarray, sigma_noise: float = 0.0) -> SymmetryReport:
    """Run symmetry probes on (x, y); return hints + flags."""
    report = SymmetryReport()
    n = len(x)
    if n < 20:
        report.notes.append("N too small for symmetry detection")
        return report

    # Power-law detection: log y vs log x, check linearity
    if np.all(x > 0) and np.all(y > 0):
        log_x = np.log(x)
        log_y = np.log(y)
        slope, intercept = float(np.polyfit(log_x, log_y, 1)[0]), float(np.polyfit(log_x, log_y, 1)[1])
        log_y_pred = slope * log_x + intercept
        rss = float(np.sum((log_y - log_y_pred) ** 2))
        tss = float(np.sum((log_y - log_y.mean()) ** 2))
        r_sq_loglog = 1.0 - rss / tss if tss > 0 else 0.0
        if r_sq_loglog > 0.95:
            report.power_law_alpha = slope
            report.is_power_law = True
            report.notes.append(
                f"power-law detected: y ≈ const · x^{slope:.3f} (log-log R²={r_sq_loglog:.3f})"
            )
            report.suggested_h_in.append("log")
            report.suggested_h_out.append("log")

    # Translation invariance: check if y(x+δ) ≈ y(x) for small δ
    if n >= 50:
        sorted_idx = np.argsort(x)
        xs, ys = x[sorted_idx], y[sorted_idx]
        # Shift comparison: compare y differences at adjacent x's
        dy = np.abs(np.diff(ys))
        dy_normalized = dy / (np.std(ys) + 1e-30)
        if float(np.mean(dy_normalized)) < 0.1:
            report.translation_invariant = True
            report.notes.append("translation-invariant (y nearly constant in x)")

    # Additive separability is hard to detect on (x, y) alone — defer to Framer
    # search; we only report y range/sign hints here.
    if np.all(y > 0):
        report.suggested_h_out.append("log")
    if np.any(y < 0) and np.any(y > 0):
        report.notes.append("y crosses zero — log/reciprocal h_out excluded")

    return report
