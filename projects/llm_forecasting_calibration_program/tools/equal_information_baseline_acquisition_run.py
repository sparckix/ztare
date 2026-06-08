#!/usr/bin/env python3
"""Run the no-call equal-information baseline acquisition/check loop.

This is a stable wrapper intended for one-time permission approval. It performs
network only through the existing Polymarket post-cutoff price probe, then
refreshes the dependent no-mutation status reports.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
TOOLS = REPO / "projects/llm_forecasting_calibration_program/tools"


def run_step(label: str, argv: list[str]) -> int:
    print(f"\n== {label} ==")
    print(" ".join(argv))
    completed = subprocess.run(argv, cwd=REPO, check=False)
    if completed.returncode != 0:
        print(f"{label} failed with exit code {completed.returncode}", file=sys.stderr)
    return int(completed.returncode)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sleep-ms", type=int, default=150)
    parser.add_argument(
        "--skip-network-probe",
        action="store_true",
        help="Refresh downstream reports from existing probe artifacts only.",
    )
    args = parser.parse_args()

    steps: list[tuple[str, list[str]]] = []
    if not args.skip_network_probe:
        steps.append(
            (
                "polymarket-post-cutoff-price-probe",
                [
                    sys.executable,
                    str(TOOLS / "cutoff_polymarket_post_price_probe.py"),
                    "--sleep-ms",
                    str(args.sleep_ms),
                ],
            )
        )
    steps.extend(
        [
            (
                "polymarket-base-rate-availability",
                [sys.executable, str(TOOLS / "cutoff_polymarket_base_rate_availability.py")],
            ),
            (
                "equal-information-baseline-void",
                [sys.executable, str(TOOLS / "equal_information_baseline_void_audit.py")],
            ),
            (
                "paper-readiness-exhaustion",
                [sys.executable, str(TOOLS / "paper_readiness_exhaustion_audit.py")],
            ),
        ]
    )
    for label, argv in steps:
        code = run_step(label, argv)
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
