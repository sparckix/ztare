#!/usr/bin/env python3
"""Run and seal the focused H101 compatible-yield checks."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


FIXTURES = Path(__file__).resolve().parent
ROOT = FIXTURES.parents[2]
TEST_FILE = "tests/common/test_protocol_information_yield.py"


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
        "predicted_identification_is_0_75": passed,
        "common_cell_realized_yield_is_0_5": passed,
        "singleton_cell_realized_yield_is_1": passed,
        "expected_realized_equals_predicted": passed,
        "forecast_identity_binds_committee_and_partition": passed,
        "missing_observation_evidence_refused": passed,
        "unseen_response_refutes_committee": passed,
        "task_credit_authority_absent": passed,
        "protocol_cost_unchanged": passed,
        "singleton_measure_is_zero": passed,
    }
    return {
        "schema": "ztare-h101-realized-protocol-information-yield-audit-v1",
        "hypothesis_id": (
            "H-GPSA-REALIZED-PROTOCOL-INFORMATION-YIELD-20260807-101"
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
            "compatible protocol forecast/observation units over a frozen "
            "response partition; no ARC post-intervention response claim"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=FIXTURES / (
            "h101_realized_protocol_information_yield_result.json"
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
