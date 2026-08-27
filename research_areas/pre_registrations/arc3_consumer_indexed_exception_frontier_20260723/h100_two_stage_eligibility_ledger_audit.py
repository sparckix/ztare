#!/usr/bin/env python3
"""Run and seal the focused H100 two-stage eligibility checks."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


FIXTURES = Path(__file__).resolve().parent
ROOT = FIXTURES.parents[2]
TEST_FILE = "tests/common/test_two_stage_eligibility_ledger.py"


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
            **__import__("os").environ,
            "PYTHONPATH": "src",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    stdout = completed.stdout
    stderr = completed.stderr
    passed = completed.returncode == 0
    checks = {
        "draft_collection_denies_task_credit": passed,
        "sealed_exact_source_pair_binds": passed,
        "distal_preferences_reconstructed": passed,
        "authority_and_source_edits_refused": passed,
        "undeclared_or_wrong_arm_refused": passed,
        "expired_trace_refused": passed,
        "missing_observed_yield_evidence_refused": passed,
        "equal_outcomes_uninformative": passed,
        "primitive_cost_unchanged": passed,
        "yield_calibration_separate": passed,
    }
    return {
        "schema": "ztare-h100-two-stage-eligibility-ledger-audit-v1",
        "hypothesis_id": (
            "H-GPSA-TWO-STAGE-ELIGIBILITY-LEDGER-20260807-100"
        ),
        "research_isomorphism_candidate_sha256": (
            "8c61f401aeb4fc808257690939e516f024a5c5867489a28b4a8de7e57e15fed8"
        ),
        "status": (
            "supported" if all(checks.values()) else "refuted"
        ),
        "environment_contact": False,
        "checks": checks,
        "verification": {
            "command": command,
            "returncode": completed.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "stdout_sha256": hashlib.sha256(
                stdout.encode("utf-8")
            ).hexdigest(),
            "stderr_sha256": hashlib.sha256(
                stderr.encode("utf-8")
            ).hexdigest(),
        },
        "claim_boundary": (
            "controller-neutral offline episode collection and sealed replay "
            "binding; no ARC observed-yield instrument or live score claim"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=FIXTURES / (
            "h100_two_stage_eligibility_ledger_result.json"
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
