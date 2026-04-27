"""GP-167 Option C: enrich unified_rar_with_sigma.csv with substrate variables.

Motivation: gp163d_unified_accel iter 7/8 (gpt-5.5, scored 100) hit a
substrate ceiling — Class A (SPARC disks) had mass_log10 collapsed to a
single value (10.5), so the mutator could only express class-dependent
behavior via hardcoded if/else multipliers (10× for clusters, 0.1× for
binaries). This forces the discovery of a truly physical law to a
follow-up: any law dependent on mass, gas content, or surface
brightness was algebraically unreachable from the collapsed substrate.

This script un-collapses Class A mass and adds two new per-row
substrate variables (gas_fraction, SBdisk):

  Per-galaxy (from /tmp/sparc_galaxy_properties.json):
    * log_lum   3.6μm luminosity                  (10⁹ L_⊙)
    * log_mhi   total HI mass                     (10⁹ M_⊙)
    * log_sbeff effective surface brightness      (L_⊙/pc²)
    Derived:
      M_star      = 0.5 · 10^log_lum  (M_⊙, 3.6μm M/L=0.5)
      M_HI_helium = 1.33 · 10^log_mhi (helium correction)
      M_bary      = M_star + M_HI_helium
      mass_log10  = log10(M_bary)
      gas_fraction= M_HI_helium / M_bary

  Per-row (from /tmp/sparc_raw/<galaxy>_rotmod.dat):
    * SBdisk   disk surface brightness at R       (L_⊙/pc²)
    * SBbul    bulge surface brightness at R      (L_⊙/pc²)
    Derived:
      SBdisk_log10 = log10(max(SBdisk + SBbul, 1e-3))

For Classes B (clusters) and C (binaries): pass through existing
mass_log10 unchanged (no SPARC analogue), gas_fraction set to NaN and
flagged via gas_fraction_source so the substrate critic and mutator
can route around them. Per-row SBdisk is undefined for B/C and
recorded as NaN. The visible class is A; this is sufficient.

Input:
    projects/gp163d_unified_accel/raw/unified_rar_with_sigma.csv
Output:
    projects/gp163d_unified_accel/raw/unified_rar_enriched.csv

Run:
    python scripts/enrich_unified_rar_substrate.py
"""
from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SPARC_DIR = Path("/tmp/sparc_raw")
SPARC_PROPS = Path("/tmp/sparc_galaxy_properties.json")
UNIFIED_IN = REPO_ROOT / "projects/gp163d_unified_accel/raw/unified_rar_with_sigma.csv"
UNIFIED_OUT = REPO_ROOT / "projects/gp163d_unified_accel/raw/unified_rar_enriched.csv"

ML_RATIO_36UM = 0.5      # standard SPARC stellar M/L at 3.6μm
HELIUM_CORRECTION = 1.33  # H + He gas mass = 1.33 · M_HI


def load_galaxy_properties() -> dict[str, dict[str, float]]:
    if not SPARC_PROPS.exists():
        raise FileNotFoundError(f"SPARC props not found: {SPARC_PROPS}")
    with open(SPARC_PROPS) as f:
        return json.load(f)


def derive_galaxy_substrate(p: dict[str, float]) -> dict[str, float | None]:
    log_lum = p.get("log_lum")
    log_mhi = p.get("log_mhi")
    if log_lum is None:
        return {"mass_log10": None, "gas_fraction": None, "log_sbeff": p.get("log_sbeff")}
    M_star = ML_RATIO_36UM * (10.0 ** log_lum)
    M_gas = HELIUM_CORRECTION * (10.0 ** log_mhi) if log_mhi is not None else 0.0
    M_bary = M_star + M_gas
    mass_log10 = math.log10(M_bary) if M_bary > 0 else None
    gas_fraction = (M_gas / M_bary) if M_bary > 0 else None
    return {
        "mass_log10": mass_log10,
        "gas_fraction": gas_fraction,
        "log_sbeff": p.get("log_sbeff"),
    }


def load_sparc_sb_table() -> dict[tuple[str, float], tuple[float, float]]:
    """Map (galaxy_id, R_kpc rounded) → (SBdisk, SBbul) from rotmod.dat."""
    table: dict[tuple[str, float], tuple[float, float]] = {}
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
                if len(parts) < 8:
                    continue
                try:
                    R = float(parts[0])
                    SBdisk = float(parts[6])
                    SBbul = float(parts[7])
                except ValueError:
                    continue
                if R <= 0:
                    continue
                table[(galaxy, round(R, 5))] = (SBdisk, SBbul)
    return table


def lookup_sb(
    galaxy: str, R_kpc: float, sb_table: dict[tuple[str, float], tuple[float, float]]
) -> tuple[float | None, float | None, str]:
    key = (galaxy, round(R_kpc, 5))
    if key in sb_table:
        SBd, SBb = sb_table[key]
        return SBd, SBb, "sparc_rotmod_exact"
    candidates = [(R_, sb) for (g_, R_), sb in sb_table.items() if g_ == galaxy]
    if not candidates:
        return None, None, "sparc_galaxy_not_found"
    nearest = min(candidates, key=lambda x: abs(x[0] - R_kpc))
    if abs(nearest[0] - R_kpc) < 0.01:
        SBd, SBb = nearest[1]
        return SBd, SBb, "sparc_rotmod_nearest"
    return None, None, f"sparc_no_match_within_tol(nearest_dR={abs(nearest[0]-R_kpc):.4f}kpc)"


def fmt(x: float | None, ndigits: int = 4) -> str:
    if x is None:
        return ""
    return f"{x:.{ndigits}f}"


def main() -> None:
    print(f"Loading SPARC galaxy properties from {SPARC_PROPS} ...")
    props = load_galaxy_properties()
    print(f"  → {len(props)} galaxies")

    print(f"Loading SPARC SBdisk/SBbul table from {SPARC_DIR} ...")
    sb_table = load_sparc_sb_table()
    print(f"  → {len(sb_table)} per-row SB entries from "
          f"{len({g for g, _ in sb_table})} galaxies")

    print(f"Reading {UNIFIED_IN.name} ...")
    in_rows = list(csv.DictReader(open(UNIFIED_IN)))
    print(f"  → {len(in_rows)} rows")

    base_fields = list(in_rows[0].keys())
    new_fields = [
        "mass_log10_real",
        "mass_log10_source",
        "gas_fraction",
        "gas_fraction_source",
        "SBdisk",
        "SBbul",
        "SB_total_log10",
        "SB_source",
    ]
    out_fields = base_fields + new_fields

    counts = {"disk_mass": 0, "disk_gas": 0, "disk_sb": 0,
              "cluster_passthrough": 0, "binary_passthrough": 0,
              "missing_props": 0, "missing_sb": 0}
    mass_distribution: list[float] = []

    with open(UNIFIED_OUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        for row in in_rows:
            cls = row["system_class"]
            out = dict(row)
            out.update({k: "" for k in new_fields})

            if cls == "disk":
                gid = row["system_id"]
                p = props.get(gid)
                if p is None:
                    out["mass_log10_real"] = row["mass_log10"]
                    out["mass_log10_source"] = "fallback_csv_collapsed"
                    out["gas_fraction_source"] = "missing_galaxy_props"
                    counts["missing_props"] += 1
                else:
                    derived = derive_galaxy_substrate(p)
                    if derived["mass_log10"] is not None:
                        out["mass_log10_real"] = fmt(derived["mass_log10"], 4)
                        out["mass_log10_source"] = "sparc_props_log_lum_log_mhi"
                        mass_distribution.append(derived["mass_log10"])
                        counts["disk_mass"] += 1
                    else:
                        out["mass_log10_real"] = row["mass_log10"]
                        out["mass_log10_source"] = "fallback_csv_collapsed"
                    if derived["gas_fraction"] is not None:
                        out["gas_fraction"] = fmt(derived["gas_fraction"], 4)
                        out["gas_fraction_source"] = "M_HI/M_bary"
                        counts["disk_gas"] += 1
                    else:
                        out["gas_fraction_source"] = "no_M_HI_in_props"

                R = float(row["radius_kpc"])
                SBd, SBb, sb_src = lookup_sb(gid, R, sb_table)
                if SBd is not None:
                    out["SBdisk"] = fmt(SBd, 4)
                    out["SBbul"] = fmt(SBb if SBb is not None else 0.0, 4)
                    sb_total = max((SBd or 0.0) + (SBb or 0.0), 1e-3)
                    out["SB_total_log10"] = fmt(math.log10(sb_total), 4)
                    out["SB_source"] = sb_src
                    counts["disk_sb"] += 1
                else:
                    out["SB_source"] = sb_src
                    counts["missing_sb"] += 1

            elif cls == "cluster":
                out["mass_log10_real"] = row["mass_log10"]
                out["mass_log10_source"] = "passthrough_class_B"
                out["gas_fraction_source"] = "undefined_class_B"
                out["SB_source"] = "undefined_class_B"
                counts["cluster_passthrough"] += 1
            elif cls == "binary":
                out["mass_log10_real"] = row["mass_log10"]
                out["mass_log10_source"] = "passthrough_class_C"
                out["gas_fraction_source"] = "undefined_class_C"
                out["SB_source"] = "undefined_class_C"
                counts["binary_passthrough"] += 1

            writer.writerow(out)

    print(f"\nWrote enriched CSV → {UNIFIED_OUT}")
    print(f"Match counts: {counts}")
    if mass_distribution:
        mass_distribution.sort()
        print(f"\nClass A real mass_log10 distribution ({len(mass_distribution)} rows):")
        print(f"  min={mass_distribution[0]:.2f}  max={mass_distribution[-1]:.2f}  "
              f"span={mass_distribution[-1] - mass_distribution[0]:.2f} dex")
        n = len(mass_distribution)
        print(f"  median={mass_distribution[n // 2]:.2f}  "
              f"mean={sum(mass_distribution) / n:.2f}")
        unique_galaxies = len(set(round(m, 4) for m in mass_distribution))
        print(f"  unique values≈{unique_galaxies} (should track #galaxies)")


if __name__ == "__main__":
    main()
