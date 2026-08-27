#!/usr/bin/env python3
"""Run and seal the focused H102 response-readout checks."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


FIXTURES = Path(__file__).resolve().parent
ROOT = FIXTURES.parents[2]
TEST_FILE = "tests/test_witnessed_protocol_response_readout.py"


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
        "direct_equals_augmented_recompilation": passed,
        "known_response_selects_frozen_cell": passed,
        "new_effect_refutes_committee": passed,
        "boundary_remains_typed": passed,
        "source_mismatch_refused": passed,
        "probe_mismatch_refused": passed,
        "observation_evidence_required": passed,
        "existing_relation_is_unioned": passed,
        "task_credit_authority_absent": passed,
        "protocol_cost_unchanged": passed,
    }
    return {
        "schema": "ztare-h102-witnessed-protocol-response-readout-audit-v1",
        "hypothesis_id": (
            "H-GPSA-WITNESSED-PROTOCOL-RESPONSE-READOUT-20260807-102"
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
            "common abstract partial-action response readout; no ARC "
            "transition-to-abstract-observation extraction claim"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=FIXTURES / (
            "h102_witnessed_protocol_response_readout_result.json"
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
