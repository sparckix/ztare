#!/usr/bin/env python3
"""Run and seal the focused H103 projection checks."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


FIXTURES = Path(__file__).resolve().parent
ROOT = FIXTURES.parents[2]
TEST_FILE = "tests/test_projected_mechanism_transition_observation.py"


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
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
        check=False,
    )
    passed = completed.returncode == 0
    checks = {
        "frame_projection_exact": passed,
        "action_history_advances_once": passed,
        "operation_effect_history_advances_once": passed,
        "authoritative_boundary_is_partial": passed,
        "untrusted_boundary_refused": passed,
        "receipt_binds_problem_projection_system_history": passed,
        "h102_accepts_exact_target_probe": passed,
        "source_or_probe_mismatch_refused": passed,
        "projection_identity_drift_refused": passed,
        "task_status_not_read": passed,
    }
    return {
        "schema": "ztare-h103-projected-live-protocol-observation-audit-v1",
        "hypothesis_id": (
            "H-GPSA-PROJECTED-LIVE-PROTOCOL-OBSERVATION-20260807-103"
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
            "frozen-fixture concrete transition projection into an H102 "
            "observation; no play-loop episode assembly claim"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=FIXTURES / (
            "h103_projected_live_protocol_observation_result.json"
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
