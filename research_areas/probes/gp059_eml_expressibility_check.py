"""GP-059 EML expressibility probe for sandbox_07 ground truth.

Answers the binary question: can the sandbox_07 ground-truth functional
form be expressed and fit under the eml_only grammar at depth-1, to a
residual tolerance below the 0.05 gate threshold?

GT (from the sealed pre-reg, not the charter):
    I(phi, psi) = A * phi**p / (exp((gamma*phi/psi)**q) - 1) + offset
    (A, p, gamma, q, offset) = (0.95, 2.30, 0.72, 1.30, 0.06)

Depth-1 EML representation (grammar-legal):
    eml(z, math.e) = exp(z) - log(math.e) = exp(z) - 1
    =>  I(phi, psi) = A * phi**p / eml((gamma*phi/psi)**q, math.e) + offset

This probe:
1. Loads the sandbox_07 visible slice from evidence.txt.
2. Fits the depth-1 EML form from a blind initial guess (not the sealed
   values) using scipy.optimize.curve_fit.
3. Reports fit parameters, max |residual|, and whether the fit would
   clear the gate at the 0.05 visible-slice threshold.

Outcome interpretation:
- Fit succeeds with max |res| << 0.05:
  -> eml_only grammar is NOT over-specified. The target is reachable.
  -> The sandbox_07 mutator search was the bottleneck, not the grammar.
  -> Running more iters with the same config is plausibly productive.
- Fit fails OR max |res| >= 0.05:
  -> eml_only grammar over-specifies. The target is not reachable at
     depth-1 and the grammar should be relaxed or deepened.
  -> Open GP-059 as a grammar over-specification finding.

Run:
    python research_areas/private/probes/gp059_eml_expressibility_check.py

This probe must not be checked in to the mutator-visible surface. It
lives under research_areas/private/ because it contains the GT form.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np
from scipy.optimize import curve_fit


EVIDENCE_PATH = Path("projects/gp023_planck_sandbox_07/evidence.txt")
GATE_THRESHOLD = 0.05


def load_visible_slice(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Parse evidence.txt into (phi, psi, I_obs) arrays.

    evidence.txt uses ``=== psi = X ===`` section headers and
    tab-separated ``phi\\tI_obs`` rows beneath each header.
    """
    phis: list[float] = []
    psis: list[float] = []
    i_obs: list[float] = []

    current_psi: float | None = None
    psi_header = re.compile(r"===\s*psi\s*=\s*([0-9.]+)\s*===")
    data_row = re.compile(r"^\s*([0-9.]+)\s+([0-9.]+)\s*$")

    for line in path.read_text().splitlines():
        m = psi_header.search(line)
        if m:
            current_psi = float(m.group(1))
            continue
        if current_psi is None:
            continue
        if line.strip().lower().startswith("phi"):
            continue
        m = data_row.match(line)
        if not m:
            continue
        phi_val = float(m.group(1))
        i_val = float(m.group(2))
        phis.append(phi_val)
        psis.append(current_psi)
        i_obs.append(i_val)

    return np.array(phis), np.array(psis), np.array(i_obs)


def eml(x: float, y: float) -> float:
    """The sandbox_07 eml_only primitive."""
    return math.exp(x) - math.log(y)


def model_depth1_eml(xdata: np.ndarray, A: float, p: float, gamma: float,
                      q: float, offset: float) -> np.ndarray:
    """I(phi, psi) via depth-1 eml composition.

    Grammar-legal expression:
        A * phi**p / eml((gamma*phi/psi)**q, math.e) + offset
    """
    phi = xdata[0]
    psi = xdata[1]
    chi = gamma * phi / psi
    # Use vectorized numpy ops; the eml primitive is exp(z) - 1 when y=e.
    z = chi ** q
    denom = np.exp(z) - 1.0  # == eml(z, math.e) elementwise
    return A * phi ** p / denom + offset


def main() -> int:
    if not EVIDENCE_PATH.exists():
        print(f"ERROR: evidence file not found at {EVIDENCE_PATH}")
        return 1

    phi, psi, i_obs = load_visible_slice(EVIDENCE_PATH)
    print(f"Loaded {len(phi)} visible-slice points from {EVIDENCE_PATH}")
    print(f"  psi levels: {sorted(set(psi.tolist()))}")
    print(f"  phi range:  [{phi.min():.4f}, {phi.max():.4f}]")
    print(f"  I_obs range: [{i_obs.min():.4f}, {i_obs.max():.4f}]")
    print()

    xdata = np.vstack([phi, psi])

    # Blind initial guess — deliberately not the sealed values.
    # The point is to show a generic fit lands on the right form.
    p0 = [1.0, 2.0, 1.0, 1.0, 0.0]
    bounds = (
        [0.1, 0.5, 0.1, 0.3, 0.0],
        [10.0, 5.0, 5.0, 5.0, 1.0],
    )

    try:
        popt, pcov = curve_fit(
            model_depth1_eml,
            xdata,
            i_obs,
            p0=p0,
            bounds=bounds,
            maxfev=20000,
        )
    except Exception as exc:
        print(f"FIT FAILED: {exc}")
        print("=> Depth-1 EML form could not be fit from this blind guess.")
        print("=> Does NOT prove the grammar is over-specified; try more guesses.")
        return 2

    A, p, gamma, q, offset = popt
    pred = model_depth1_eml(xdata, *popt)
    residuals = i_obs - pred
    max_abs_res = float(np.max(np.abs(residuals)))
    mean_abs_res = float(np.mean(np.abs(residuals)))
    rms_res = float(np.sqrt(np.mean(residuals ** 2)))

    print("Fit succeeded.")
    print(f"  A      = {A:.6f}")
    print(f"  p      = {p:.6f}")
    print(f"  gamma  = {gamma:.6f}")
    print(f"  q      = {q:.6f}")
    print(f"  offset = {offset:.6f}")
    print()
    print(f"  max |residual|  = {max_abs_res:.6f}")
    print(f"  mean |residual| = {mean_abs_res:.6f}")
    print(f"  rms residual    = {rms_res:.6f}")
    print()

    # Worst-residual point for context
    worst_idx = int(np.argmax(np.abs(residuals)))
    print(
        f"  worst point:    phi={phi[worst_idx]:.4f}, psi={psi[worst_idx]:.4f}, "
        f"I_obs={i_obs[worst_idx]:.5f}, I_model={pred[worst_idx]:.5f}, "
        f"res={residuals[worst_idx]:+.5f}"
    )
    print()

    gate_passes = max_abs_res < GATE_THRESHOLD
    print(f"Visible-slice gate threshold: {GATE_THRESHOLD}")
    print(f"Gate verdict: {'PASS' if gate_passes else 'FAIL'}")
    print()

    if gate_passes:
        print("=> Depth-1 eml_only expression reaches the target under the gate.")
        print("=> Grammar is NOT over-specified. The sandbox_07 bottleneck was")
        print("   mutator search, not grammar reachability.")
        print("=> More iters with the same config are plausibly productive.")
        return 0
    else:
        print("=> Depth-1 eml_only expression does NOT clear the gate even")
        print("   from a fit-optimal parametrization. This suggests grammar")
        print("   over-specification unless a deeper composition is reachable.")
        print("=> Try depth-2/3 compositions or open GP-059.")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
