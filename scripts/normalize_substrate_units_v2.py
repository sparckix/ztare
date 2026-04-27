"""Substrate v2 unit normalization for gp163d_unified_accel.

Iter 2 of the enriched run revealed a latent unit inconsistency: Class C
(wide binaries) carries mass_log10 in raw-kg units (range 30.0-31.09)
while Class A (SPARC disks) carries it in solar units (range 7.7-11.4).
The mutator dodged this by choosing radius_log10 as the cross-class
bridge (the only feature in comparable units across all three classes),
but a future iter wanting to use mass_log10 as a bridge would extrapolate
from Class A's solar-unit range to Class C's kg-unit range and produce
nonsense.

Fix: convert Class C mass_log10 by subtracting log10(M_sun in kg) =
log10(1.989e30) = 30.299. After conversion, Class C masses sit in the
range -0.30 to 0.79 (solar units), i.e. 0.5 to 6 solar masses, which is
correct for wide-binary stellar pairs.

Class B (clusters) is left at the existing collapsed 14.5 because (a)
14.5 is already in solar units (10^14.5 M_sun is a reasonable cluster
total mass) and (b) per-cluster enrichment from CLASH would require
column-documentation verification on the table that we don't have at
hand.

Output is written to a NEW file (unified_rar_enriched_v2.csv) so the
live run can continue undisturbed. Operator swaps the files when ready.

Run:
    python scripts/normalize_substrate_units_v2.py
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
IN_PATH = REPO_ROOT / "projects/gp163d_unified_accel/raw/unified_rar_enriched.csv"
OUT_PATH = REPO_ROOT / "projects/gp163d_unified_accel/raw/unified_rar_enriched_v2.csv"

# log10 of solar mass in kg
M_SUN_KG = 1.989e30
LOG10_M_SUN_KG = math.log10(M_SUN_KG)


def fmt(x: float, ndigits: int = 4) -> str:
    if x is None:
        return ""
    return f"{x:.{ndigits}f}"


def main() -> None:
    print(f"Reading {IN_PATH.name} ...")
    rows = list(csv.DictReader(open(IN_PATH)))
    print(f"  → {len(rows)} rows")

    fields = list(rows[0].keys())
    n_class_c_normalized = 0
    n_class_b_passthrough = 0
    n_class_a_passthrough = 0
    class_c_old_range = []
    class_c_new_range = []

    for r in rows:
        cls = r["system_class"]
        if cls == "binary":
            old_mass_str = r["mass_log10_real"] or r["mass_log10"]
            try:
                old_mass = float(old_mass_str)
            except ValueError:
                continue
            new_mass = old_mass - LOG10_M_SUN_KG
            r["mass_log10_real"] = fmt(new_mass, 4)
            r["mass_log10"] = fmt(new_mass, 4)
            r["mass_log10_source"] = "kg_to_solar_normalized_v2"
            class_c_old_range.append(old_mass)
            class_c_new_range.append(new_mass)
            n_class_c_normalized += 1
        elif cls == "cluster":
            r["mass_log10_source"] = (r.get("mass_log10_source") or "") + "+v2_left_in_solar_units"
            n_class_b_passthrough += 1
        else:
            n_class_a_passthrough += 1

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"\nWrote {OUT_PATH}")
    print(f"  Class A passthrough: {n_class_a_passthrough} rows")
    print(f"  Class B passthrough: {n_class_b_passthrough} rows (mass_log10 left at 14.5, already solar)")
    print(f"  Class C normalized:  {n_class_c_normalized} rows")
    if class_c_new_range:
        print(f"\nClass C mass_log10:")
        print(f"  OLD (kg-base):    [{min(class_c_old_range):.2f}, {max(class_c_old_range):.2f}]  span={max(class_c_old_range)-min(class_c_old_range):.2f} dex")
        print(f"  NEW (solar-base): [{min(class_c_new_range):.2f}, {max(class_c_new_range):.2f}]  span={max(class_c_new_range)-min(class_c_new_range):.2f} dex")
        print(f"  Subtracted log10(M_sun in kg) = {LOG10_M_SUN_KG:.3f}")
    print(f"\nLive CSV (unified_rar_enriched.csv) is UNCHANGED. To activate v2:")
    print(f"  1. Stop the current gp163d run (Ctrl-C after iter completes)")
    print(f"  2. mv unified_rar_enriched.csv unified_rar_enriched_v1.csv")
    print(f"  3. mv unified_rar_enriched_v2.csv unified_rar_enriched.csv")
    print(f"  4. Run freeze + reset on gp163d, then relaunch")


if __name__ == "__main__":
    main()
