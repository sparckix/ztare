"""Deterministic evidence-surface generator for sandbox_09 (RC step response).

Generates the three frozen evidence files from sealed GT values:

    V(t, R) = V_inf * (1 - math.exp(-t / (R * C))) + V_offset

Sealed GT (per sandbox_09 pre-reg):
    V_inf    = 0.95
    C        = 0.00082   (farads)
    V_offset = 0.14

R sweeps (v2):       {1000, 3160, 10000, 31600, 100000}

Visible t grid (v2):       {0.0, 0.05, 0.1, 0.2, 0.4, 0.8}
Hidden holdout t (v2):     {0.025, 0.15, 0.6}
Farther-tail hidden t:     {25.6, 51.2}

v2 grid shift (2026-04-15): fastest sweep raised to R=1000 so τ_min=0.82,
visible t truncated to t_max=0.8 < τ_min so no sweep reaches its plateau.
Hides V_inf and V_offset from direct reading off evidence.txt. See v2
amendment §A1 in the sandbox_09 pre-reg.

Do NOT re-run this script after seal. The three evidence files are frozen.
"""
from __future__ import annotations

import math
from pathlib import Path

V_INF = 0.95
C = 0.00082
V_OFFSET = 0.14

R_SWEEPS = [1000, 3160, 10000, 31600, 100000]
VISIBLE_T = [0.0, 0.05, 0.1, 0.2, 0.4, 0.8]
HOLDOUT_T = [0.025, 0.15, 0.6]
FARTHER_TAIL_T = [25.6, 51.2]

_REPO_ROOT = Path(__file__).resolve().parents[3]
PROJECT_DIR = _REPO_ROOT / "projects" / "gp023_sandbox_09"


def V(t: float, R: float) -> float:
    return V_INF * (1.0 - math.exp(-t / (R * C))) + V_OFFSET


def _render(path: Path, header: str, t_grid: list[float]) -> None:
    lines = [header, ""]
    for R in R_SWEEPS:
        lines.append(f"=== R = {R} ===")
        lines.append("t\tV_obs")
        for t in t_grid:
            lines.append(f"{t:.4f}\t{V(t, R):.6f}")
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    visible_header = (
        "GP-023 SANDBOX 09 — OBSERVED RESPONSE V(t, R) [VISIBLE SLICE]\n"
        "\n"
        "Setup: closed measurement system. t is a non-negative ordinal\n"
        "with t=0 as the configuration reference. R is a sweep-constant\n"
        "control parameter held fixed within each block. V_obs is the\n"
        "observed response at that (t, R).\n"
        "\n"
        "Five sweeps at R in {1000, 3160, 10000, 31600, 100000}. All three\n"
        "parameters of the true generator are shared across sweeps; the\n"
        "functional form is NOT disclosed in this file.\n"
        "\n"
        "NOTE: This file contains the visible subset. A hidden in-range\n"
        "holdout and a farther-tail holdout exist on disk for deterministic\n"
        "scoring. Do not attempt to reconstruct either hidden surface; any\n"
        "model tuned only to this visible grid will still be scored on both\n"
        "hidden surfaces.\n"
    )
    holdout_header = (
        "GP-023 SANDBOX 09 — HIDDEN HOLDOUT V(t, R) [IN-RANGE]\n"
        "\n"
        "Deterministic in-range holdout at t values distinct from the\n"
        "visible grid. Do not use this file during fitting; it is scored\n"
        "by the gate harness only.\n"
    )
    farther_header = (
        "GP-023 SANDBOX 09 — FARTHER-TAIL HOLDOUT V(t, R)\n"
        "\n"
        "Deterministic out-of-window holdout at t values beyond the\n"
        "visible boundary. Scored by the gate harness only.\n"
    )

    _render(PROJECT_DIR / "evidence.txt", visible_header, VISIBLE_T)
    _render(PROJECT_DIR / "evidence_holdout.txt", holdout_header, HOLDOUT_T)
    _render(PROJECT_DIR / "evidence_farther_tail.txt", farther_header, FARTHER_TAIL_T)
    print("wrote evidence.txt, evidence_holdout.txt, evidence_farther_tail.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
