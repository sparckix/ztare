#!/usr/bin/env python3
"""Autofire watcher: poll Round N's checkpoint files; fire Round N+1 when all hit targets.

Usage:
  python scripts/public/utilities/autofire_next_round.py round1 round2

Logs to /tmp/autofire_<from>_to_<to>.log. Polls every 60s.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

# Round → list of (label, file, target_rows)
ROUND_TARGETS: dict[str, list[tuple[str, str, int]]] = {
    "round1": [
        ("v9.1",         "projects/llm_forecasting_calibration_program/llm_self_calibration_v9/workspace/pilot_v9_1_calls.jsonl", 150),
        ("v6_receiver",  "projects/llm_forecasting_calibration_program/forecast_insurance_calibration_v1/workspace/pilot_v6_receiver_forecasts.jsonl", 240),
        ("v6_control",   "projects/llm_forecasting_calibration_program/forecast_insurance_calibration_v1/workspace/pilot_v6_control_forecasts.jsonl", 120),
    ],
    "round2": [
        ("v10",          "projects/llm_forecasting_calibration_program/calibration_channel_mechanism_v10/workspace/pilot_v10_calls.jsonl", 360),
    ],
    "round3": [
        ("v10.1",        "projects/llm_forecasting_calibration_program/calibration_channel_mechanism_v10/workspace/pilot_v10_1_calls.jsonl", 480),
    ],
    "round4": [
        ("v5.1",         "projects/llm_forecasting_calibration_program/forecast_insurance_calibration_v1/workspace/pilot_v5_1_forecasts_20260524T165817Z.jsonl", 240),
    ],
}

# Round → command to fire it (as list for subprocess)
ROUND_CMDS: dict[str, str] = {
    "round2": "nohup python3 projects/llm_forecasting_calibration_program/calibration_channel_mechanism_v10/workspace/run_pilot_v10_dispatch.py --full --resume > /tmp/r2_v10.log 2>&1 &",
    "round3": "nohup python3 projects/llm_forecasting_calibration_program/calibration_channel_mechanism_v10/workspace/run_pilot_v10_1_dispatch.py --full --resume > /tmp/r3_v10_1.log 2>&1 &",
    "round4": "nohup python3 projects/llm_forecasting_calibration_program/forecast_insurance_calibration_v1/workspace/run_pilot_v5_1_skeptical_dispatch.py --full --resume --checkpoint projects/llm_forecasting_calibration_program/forecast_insurance_calibration_v1/workspace/pilot_v5_1_forecasts_20260524T165817Z.jsonl > /tmp/r4_v5_1.log 2>&1 &",
    "round5": "nohup python3 projects/lean_proof_completability_v1/workspace/run_pilot_v7_2_dispatch.py --full --resume > /tmp/r5_v7_2.log 2>&1 &",
}


def log(path: Path, msg: str) -> None:
    line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}\n"
    sys.stdout.write(line); sys.stdout.flush()
    with path.open("a") as f:
        f.write(line)


def count_rows(p: Path) -> int:
    if not p.exists():
        return 0
    return sum(1 for _ in p.open())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("from_round", help="round being watched (e.g. round1)")
    ap.add_argument("to_round",   help="round to fire when from_round completes (e.g. round2)")
    ap.add_argument("--poll-seconds", type=int, default=60)
    args = ap.parse_args()

    log_path = Path(f"/tmp/autofire_{args.from_round}_to_{args.to_round}.log")
    log_path.write_text("")
    log(log_path, f"autofire watcher: {args.from_round} → {args.to_round}")

    targets = ROUND_TARGETS.get(args.from_round)
    if targets is None:
        log(log_path, f"ERROR: unknown round '{args.from_round}'")
        return 2
    cmd = ROUND_CMDS.get(args.to_round)
    if cmd is None:
        log(log_path, f"ERROR: unknown next-round '{args.to_round}'")
        return 2

    log(log_path, f"monitoring {len(targets)} files; will fire when all reach target")

    while True:
        all_done = True
        for label, path, target in targets:
            n = count_rows(REPO / path)
            status = "✓" if n >= target else "wait"
            log(log_path, f"  {label}: {n}/{target} [{status}]")
            if n < target:
                all_done = False
        if all_done:
            log(log_path, f"ALL {args.from_round} done — firing {args.to_round}")
            log(log_path, f"  cmd: {cmd}")
            subprocess.run(["bash", "-c", cmd], cwd=str(REPO), check=False)
            log(log_path, f"{args.to_round} fired")
            return 0
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    sys.exit(main())
