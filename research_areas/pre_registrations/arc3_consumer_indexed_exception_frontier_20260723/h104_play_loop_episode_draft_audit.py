#!/usr/bin/env python3
"""Run and seal the focused H104 play-loop episode checks."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


FIXTURES = Path(__file__).resolve().parent
ROOT = FIXTURES.parents[2]
TEST_FILE = "tests/test_play_loop_episode_draft.py"


def run_audit() -> dict:
    command = [
        str(ROOT / "venv/bin/python"),
        "-m",
        "pytest",
        TEST_FILE,
        "-q",
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env={
            **os.environ,
            "PYTHONPATH": "src",
            "MPLCONFIGDIR": "/private/tmp/mplconfig",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    passed = completed.returncode == 0
    checks = {
        "chronological_windows_form_draft": passed,
        "adjacency_and_terminal_state_preserved": passed,
        "draft_hash_round_trips": passed,
        "play_loop_persists_draft": passed,
        "repeated_episode_is_idempotent": passed,
        "unavailable_or_cross_forecast_yield_refused": passed,
        "measure_or_evidence_drift_refused": passed,
        "environment_and_prefix_required": passed,
        "no_temporal_chain_or_task_preference_created": passed,
        "immediate_choice_recording_preserved": passed,
    }
    return {
        "schema": "ztare-h104-play-loop-episode-draft-audit-v1",
        "hypothesis_id": (
            "H-GPSA-PLAY-LOOP-EPISODE-DRAFT-20260807-104"
        ),
        "status": (
            "supported" if all(checks.values()) else "refuted"
        ),
        "environment_contact": False,
        "checks": checks,
        "verification": {
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "stdout_sha256": hashlib.sha256(
                completed.stdout.encode("utf-8")
            ).hexdigest(),
            "stderr_sha256": hashlib.sha256(
                completed.stderr.encode("utf-8")
            ).hexdigest(),
        },
        "claim_boundary": (
            "offline ARC play-loop episode-draft collection; no live replay "
            "contract or counterfactual arm execution claim"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=FIXTURES / (
            "h104_play_loop_episode_draft_result.json"
        ),
    )
    args = parser.parse_args()
    result = run_audit()
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(args.output),
        "status": result["status"],
        "checks": result["checks"],
        "verification": {
            "returncode": result["verification"]["returncode"],
            "stdout": result["verification"]["stdout"],
        },
    }, indent=2, sort_keys=True))
    if result["status"] != "supported":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
