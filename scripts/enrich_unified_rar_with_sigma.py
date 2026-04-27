"""GP-164 wMDL: enrich unified_rar.csv with per-row σ_g_obs.

Source σ data (operator-provided, downloaded to /tmp 2026-04-25):
  * SPARC disk galaxies: errV (km/s) per (galaxy, R_kpc) bin in
    /tmp/sparc_raw/<galaxy>_rotmod.dat. Convert to acceleration σ
    via error propagation on g = V²/R:
        σ_g = (2·V·σ_V) / R          [km²/s² per kpc]
        σ_g = σ_g · (1e6 / 3.0857e19) [→ m/s²]
  * CLASH clusters: e_log(gtot) (dex) in /tmp/clash_fig2.dat col 6.
    Convert from log-space to linear:
        σ_g = g_obs · ln(10) · e_log_gtot
  * Wide binaries (Chae): per-bin γ-fit residual scatter not directly
    available per row; the Chae 2023 binned analysis quotes
    +0.10/-0.09 stat error on γ at low-acceleration end. Use
    fractional σ_g/g_obs ≈ 0.07 (mean of stat-error band) as a
    conservative homoscedastic floor across the 12 binary bins.
    This is intentionally a class-floor, not a per-row estimate —
    flagged in the output as `sigma_source="binary_bin_floor"`.

Output:
  * projects/gp163d_unified_accel/raw/unified_rar_with_sigma.csv
    with the original 8 columns + new `sigma_g_obs` (absolute,
    m/s²) and `sigma_source` (provenance tag for audit).

Run:
    python scripts/enrich_unified_rar_with_sigma.py
"""
from __future__ import annotations

import csv
import math
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SPARC_DIR = Path("/tmp/sparc_raw")
CLASH_FILE = Path("/tmp/clash_fig2.dat")
UNIFIED_IN = REPO_ROOT / "projects/gp163d_unified_accel/raw/unified_rar.csv"
UNIFIED_OUT = REPO_ROOT / "projects/gp163d_unified_accel/raw/unified_rar_with_sigma.csv"

# Unit conversion: (km/s)² / kpc → m/s²
# 1 km = 1000 m → (km/s)² = 1e6 (m/s)²
# 1 kpc = 3.0857e19 m
KMS2_PER_KPC_TO_MS2 = 1e6 / 3.0857e19

# Wide-binary class floor from Chae 2023 binned analysis (γ stat error band).
BINARY_BIN_FRAC_SIGMA = 0.07


def load_sparc_sigma_table() -> dict[tuple[str, float], float]:
    """Map (galaxy_id, R_kpc) → σ_g_obs in m/s²."""
    table: dict[tuple[str, float], float] = {}
    if not SPARC_DIR.exists():
        raise FileNotFoundError(f"SPARC raw dir not found: {SPARC_DIR}")
    for fn in sorted(os.listdir(SPARC_DIR)):
        if not fn.endswith("_rotmod.dat"):
            continue
        galaxy = fn.replace("_rotmod.dat", "")
        path = SPARC_DIR / fn
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) < 4:
                    continue
                try:
                    R = float(parts[0])         # kpc
                    Vobs = float(parts[1])      # km/s
                    errV = float(parts[2])      # km/s
                except ValueError:
                    continue
                if R <= 0 or Vobs <= 0:
                    continue
                # σ_g = 2·V·errV / R  in (km/s)²/kpc → convert to m/s²
                sigma_g = (2.0 * Vobs * errV) / R * KMS2_PER_KPC_TO_MS2
                # Round R to 5 decimals for stable lookup match
                table[(galaxy, round(R, 5))] = sigma_g
    return table


def load_clash_sigma_table() -> dict[str, list[tuple[float, float]]]:
    """Map cluster_id → list of (log_g_bar, σ_g_obs) for nearest-log_g_bar matching.

    CLASH file columns (per operator brief):
      col 0: cluster_id
      col 1: ?
      col 2: log_g_bar
      col 3: log_g_tot
      col 4: e_log_g_bar
      col 5: e_log_g_tot
    """
    LN10 = math.log(10.0)
    table: dict[str, list[tuple[float, float]]] = {}
    if not CLASH_FILE.exists():
        raise FileNotFoundError(f"CLASH file not found: {CLASH_FILE}")
    with open(CLASH_FILE) as f:
        for line in f:
            parts = line.split()
            if len(parts) < 6:
                continue
            try:
                cluster = parts[0]
                log_g_bar = float(parts[2])
                log_g_tot = float(parts[3])
                e_log_g_tot = float(parts[5])
            except ValueError:
                continue
            g_obs = 10.0 ** log_g_tot
            sigma_g = g_obs * LN10 * e_log_g_tot
            table.setdefault(cluster, []).append((log_g_bar, sigma_g))
    return table


def lookup_sparc_sigma(
    galaxy: str, R_kpc: float, sparc_table: dict[tuple[str, float], float]
) -> tuple[float | None, str]:
    """Exact-match first, then nearest-R within 0.01 kpc tolerance."""
    key_exact = (galaxy, round(R_kpc, 5))
    if key_exact in sparc_table:
        return sparc_table[key_exact], "sparc_rotmod_exact"
    candidates = [(R_, s) for (g_, R_), s in sparc_table.items() if g_ == galaxy]
    if not candidates:
        return None, "sparc_galaxy_not_found"
    nearest = min(candidates, key=lambda x: abs(x[0] - R_kpc))
    if abs(nearest[0] - R_kpc) < 0.01:
        return nearest[1], "sparc_rotmod_nearest"
    return None, f"sparc_no_match_within_tol(nearest_dR={abs(nearest[0]-R_kpc):.4f}kpc)"


def lookup_clash_sigma(
    cluster: str, log_g_bar: float, clash_table: dict[str, list[tuple[float, float]]]
) -> tuple[float | None, str]:
    """Match cluster_id and nearest log_g_bar within 0.05 dex tolerance."""
    if cluster not in clash_table:
        return None, "clash_cluster_not_found"
    candidates = clash_table[cluster]
    nearest = min(candidates, key=lambda x: abs(x[0] - log_g_bar))
    if abs(nearest[0] - log_g_bar) < 0.05:
        return nearest[1], "clash_fig2_nearest_logbar"
    return None, f"clash_no_match_within_tol(nearest_dlog={abs(nearest[0]-log_g_bar):.3f})"


def main() -> None:
    print(f"Loading SPARC σ table from {SPARC_DIR} ...")
    sparc_table = load_sparc_sigma_table()
    print(f"  → {len(sparc_table)} (galaxy, R_kpc) σ entries from "
          f"{len({g for g,_ in sparc_table})} galaxies")

    print(f"Loading CLASH σ table from {CLASH_FILE} ...")
    clash_table = load_clash_sigma_table()
    print(f"  → {sum(len(v) for v in clash_table.values())} σ entries "
          f"across {len(clash_table)} clusters")

    in_rows = list(csv.DictReader(open(UNIFIED_IN)))
    print(f"Reading unified_rar.csv: {len(in_rows)} rows")

    out_fields = list(in_rows[0].keys()) + ["sigma_g_obs", "sigma_source"]
    matched_disk = matched_cluster = matched_binary = unmatched = 0

    with open(UNIFIED_OUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        for row in in_rows:
            cls = row["system_class"]
            sigma: float | None = None
            source = "missing"
            if cls == "disk":
                R = float(row["radius_kpc"])
                sigma, source = lookup_sparc_sigma(row["system_id"], R, sparc_table)
                if sigma is not None:
                    matched_disk += 1
            elif cls == "cluster":
                log_g_bar = float(row["log_g_bar"])
                sigma, source = lookup_clash_sigma(row["system_id"], log_g_bar, clash_table)
                if sigma is not None:
                    matched_cluster += 1
            elif cls == "binary":
                g_obs = float(row["g_obs"])
                sigma = g_obs * BINARY_BIN_FRAC_SIGMA
                source = "binary_bin_floor"
                matched_binary += 1
            else:
                source = f"unknown_class({cls})"
            if sigma is None:
                unmatched += 1
                # Fallback: 10% fractional σ as conservative floor so
                # the row is not dropped from weighted χ² (operator can
                # filter `sigma_source != "missing"` rows in features
                # adapter if strict).
                try:
                    sigma = float(row["g_obs"]) * 0.10
                    source = f"fallback_10pct({source})"
                except ValueError:
                    sigma = 0.0
                    source = f"unparseable_g_obs({source})"
            out_row = dict(row)
            out_row["sigma_g_obs"] = f"{sigma:.6e}"
            out_row["sigma_source"] = source
            writer.writerow(out_row)

    print(f"\nMatched: disk={matched_disk}, cluster={matched_cluster}, binary={matched_binary}")
    print(f"Unmatched (using fallback): {unmatched}")
    print(f"Wrote: {UNIFIED_OUT}")


if __name__ == "__main__":
    main()
