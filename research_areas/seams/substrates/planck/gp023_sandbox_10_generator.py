"""Sealed generator for sandbox_10.

Writes evidence.txt, evidence_holdout.txt, evidence_farther_tail.txt into
projects/gp023_sandbox_10/. Deterministic, no noise, IEEE double.

The generator is the only file in the repo that names the sealed ground
truth. It lives under research_areas/private/seams/ and is never read by
any live mutator or downstream cold process.
"""
from __future__ import annotations

import math
from pathlib import Path

# Sealed ground truth (vis-viva)
# GM = solar standard gravitational parameter (IAU 2009)
GM = 1.32712440018e20  # m^3 / s^2
AU = 1.495978707e11    # m

# Sealed grid
A_SWEEPS_AU = [0.8, 1.0, 1.3, 1.7, 2.2]
ECC = 0.15

VISIBLE_E = [0.3, 0.8, 1.2, 1.8, 2.4, 2.9]     # radians
HOLDOUT_E = [0.5, 1.5, 2.6]
FARTHER_TAIL_E = [0.05, 3.05]

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent.parent / "projects" / "gp023_sandbox_10"


def vis_viva(r: float, a: float) -> float:
    """v = sqrt(GM * (2/r - 1/a))"""
    inside = GM * (2.0 / r - 1.0 / a)
    assert inside > 0, f"sqrt-domain violation at r={r}, a={a}, inside={inside}"
    return math.sqrt(inside)


def r_of_E(a: float, E: float) -> float:
    """r(E) = a * (1 - e*cos(E))"""
    return a * (1.0 - ECC * math.cos(E))


def build_rows(e_list: list[float]) -> list[tuple[float, float, float]]:
    rows = []
    for a_au in A_SWEEPS_AU:
        a = a_au * AU
        for E in e_list:
            r = r_of_E(a, E)
            v = vis_viva(r, a)
            rows.append((r, a, v))
    return rows


def write_evidence(filename: str, rows: list[tuple[float, float, float]]) -> None:
    path = OUTPUT_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        f.write("# x1 x2 y\n")
        for r, a, v in rows:
            f.write(f"{r:.12e} {a:.12e} {v:.12e}\n")


def main() -> None:
    visible = build_rows(VISIBLE_E)
    holdout = build_rows(HOLDOUT_E)
    farther_tail = build_rows(FARTHER_TAIL_E)

    write_evidence("evidence.txt", visible)
    write_evidence("evidence_holdout.txt", holdout)
    write_evidence("evidence_farther_tail.txt", farther_tail)

    print(f"Wrote {len(visible)} visible points to {OUTPUT_DIR/'evidence.txt'}")
    print(f"Wrote {len(holdout)} holdout points to {OUTPUT_DIR/'evidence_holdout.txt'}")
    print(f"Wrote {len(farther_tail)} farther-tail points to {OUTPUT_DIR/'evidence_farther_tail.txt'}")

    # Sanity checks at write time
    for r, a, v in visible + holdout + farther_tail:
        assert GM * (2/r - 1/a) > 0, f"sealed point violates sqrt domain: r={r}, a={a}"
        assert v > 0, f"non-positive v at r={r}, a={a}"

    v_range = [v for _, _, v in visible]
    print(f"v range (visible): {min(v_range):.4e} to {max(v_range):.4e} m/s")


if __name__ == "__main__":
    main()
