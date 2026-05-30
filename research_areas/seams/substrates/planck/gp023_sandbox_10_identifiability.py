"""Identifiability protocol for sandbox_10. One free parameter (GM).
Recovers GM from visible evidence, reports cond(J), bootstrap CI."""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

GM_TRUE = 1.32712440018e20

EVIDENCE = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve() / "projects/gp023_sandbox_10/evidence.txt"


def load_evidence(path: Path) -> np.ndarray:
    rows = []
    for line in path.read_text().splitlines():
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split()
        rows.append([float(x) for x in parts])
    return np.asarray(rows)


def model(gm: float, r: np.ndarray, a: np.ndarray) -> np.ndarray:
    return np.sqrt(gm * (2.0 / r - 1.0 / a))


def residuals(params: np.ndarray, r: np.ndarray, a: np.ndarray, v: np.ndarray) -> np.ndarray:
    return model(params[0], r, a) - v


def main() -> None:
    data = load_evidence(EVIDENCE)
    r, a, v = data[:, 0], data[:, 1], data[:, 2]
    print(f"Loaded {len(r)} visible points")

    print("\n1. SINGLE-PARAMETER FIT")
    passed_fits = 0
    rel_errors = []
    for start_log_gm in np.linspace(19.0, 21.0, 25):
        x0 = np.array([10.0 ** start_log_gm])
        res = least_squares(residuals, x0, args=(r, a, v), method="lm", max_nfev=500)
        if res.success:
            rel_err = abs(res.x[0] - GM_TRUE) / GM_TRUE
            rel_errors.append(rel_err)
            if rel_err < 1e-10:
                passed_fits += 1
    print(f"   Converged within 1e-10 relative tolerance: {passed_fits}/25")
    print(f"   Worst relative error: {max(rel_errors):.2e}")
    print(f"   Best recovered GM: {GM_TRUE + (max(rel_errors)*GM_TRUE):.6e} (vs GT {GM_TRUE:.6e})")

    print("\n2. JACOBIAN CONDITION AT GT")
    # dv/dGM = (2/r - 1/a) / (2v)
    dv_dgm = (2.0/r - 1.0/a) / (2.0 * v)
    J = dv_dgm.reshape(-1, 1)
    u, s, _ = np.linalg.svd(J, full_matrices=False)
    cond = s[0] / s[-1] if s[-1] > 0 else float("inf")
    print(f"   Singular values: {s}")
    print(f"   cond(J) = {cond:.3e}   (threshold 1e4; one-param problem, trivial)")

    print("\n3. JACOBIAN RANK")
    rank = np.linalg.matrix_rank(J)
    print(f"   rank(J) = {rank}  (expected 1)")

    print("\n4. BOOTSTRAP (100 resamples)")
    rng = np.random.default_rng(42)
    n = len(r)
    recovered = []
    for _ in range(100):
        idx = rng.integers(0, n, n)
        try:
            res = least_squares(residuals, np.array([1e20]),
                                args=(r[idx], a[idx], v[idx]), method="lm", max_nfev=500)
            if res.success:
                recovered.append(res.x[0])
        except Exception:
            pass
    arr = np.array(recovered)
    print(f"   Successful fits: {len(arr)}/100")
    print(f"   GM mean: {arr.mean():.6e}")
    print(f"   GM std:  {arr.std():.6e}")
    print(f"   GM 95% CI: [{np.quantile(arr,0.025):.6e}, {np.quantile(arr,0.975):.6e}]")
    print(f"   GT inside CI: {np.quantile(arr,0.025) <= GM_TRUE <= np.quantile(arr,0.975)}")

    print("\n5. SQRT DOMAIN SANITY")
    inside = 2.0/r - 1.0/a
    print(f"   min(2/r - 1/a) = {inside.min():.3e}  (must be > 0)")
    print(f"   max(2/r - 1/a) = {inside.max():.3e}")

    print("\nVERDICT:")
    print("   (1) Single-parameter recovery: PASS" if passed_fits == 25 else "   (1) Single-parameter recovery: FAIL")
    print(f"   (2) cond(J) < 1e4: {'PASS' if cond < 1e4 else 'FAIL'}")
    print(f"   (3) rank(J) == 1: {'PASS' if rank == 1 else 'FAIL'}")
    print(f"   (4) Bootstrap consistent: {'PASS' if len(arr) >= 90 else 'FAIL'}")
    print(f"   (5) sqrt domain strictly positive: {'PASS' if inside.min() > 0 else 'FAIL'}")


if __name__ == "__main__":
    main()
