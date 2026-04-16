"""GP-070 Synthetic test module — permanent fixture (C-5).

Two stages, one gate. Exercises the full orchestrator cycle:
create → advance → gate escalation → resume → advance → close.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_cli(*args: str) -> dict:
    result = subprocess.run(
        [sys.executable, "-m", "src.ztare.orchestration.cli", *args],
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 1, 2):
        raise RuntimeError(f"CLI failed: {result.stderr}")
    try:
        return json.loads(result.stdout) if result.stdout.strip() else {}
    except json.JSONDecodeError:
        raise RuntimeError(f"CLI returned invalid JSON: {result.stdout[:200]}\nstderr: {result.stderr[:200]}")


def test_full_cycle() -> bool:
    """Exercise the full goal lifecycle against the synthetic_test config."""
    print("=== GP-070 Synthetic Test Module ===")
    print()

    # 1. Validate config
    print("1. Validating synthetic_test config...")
    result = run_cli("validate", "research_areas/private/goal_types/synthetic_test.yaml")
    if not result.get("valid"):
        print(f"   FAIL: {result.get('errors')}")
        return False
    print(f"   OK: {result['stages']}")

    # 2. Create goal
    print("2. Creating test goal...")
    result = run_cli(
        "create", "synthetic_test_run",
        "--type", "synthetic_test",
        "--description", "Integration test of the orchestrator core",
    )
    if not result.get("created"):
        print(f"   FAIL: {result}")
        return False
    slug = result["slug"]
    print(f"   OK: slug={slug}, stage={result['current_stage']}")

    # 3. Advance to WORKING
    print("3. Advancing to WORKING...")
    result = run_cli("advance", slug, "--to", "WORKING")
    if not result.get("accepted"):
        print(f"   FAIL: {result.get('reason')}")
        return False
    print(f"   OK: stage={result['current_stage']}, gate_pending={result['gate_pending']}")

    # 4. Advance to REVIEW (gate)
    print("4. Advancing to REVIEW (gate)...")
    result = run_cli("advance", slug, "--to", "REVIEW")
    if not result.get("accepted"):
        print(f"   FAIL: {result.get('reason')}")
        return False
    assert result["gate_pending"], "REVIEW should be a gate"
    print(f"   OK: gate_pending={result['gate_pending']}")

    # 5. Check status (should be gate_pending)
    print("5. Checking status...")
    result = run_cli("status", slug)
    assert result["status"] == "gate_pending", f"Expected gate_pending, got {result['status']}"
    print(f"   OK: status={result['status']}, stage={result['current_stage']}")

    # 6. Try to advance while gate-pending (should fail)
    print("6. Attempting advance while gate-pending (should fail)...")
    result = run_cli("advance", slug, "--to", "CLOSED")
    assert not result.get("accepted"), "Should not accept advance while gate-pending"
    print(f"   OK: correctly rejected — {result.get('reason', '')[:60]}")

    # 7. Resume (clear gate — advances past REVIEW to CLOSED)
    print("7. Resuming (clearing gate)...")
    result = run_cli("resume", slug)
    if not result.get("accepted"):
        print(f"   FAIL: {result}")
        return False
    print(f"   OK: stage={result['current_stage']}")

    # 8. Verify final status
    print("8. Verifying final status...")
    result = run_cli("status", slug)
    assert result["current_stage"] == "CLOSED", f"Expected CLOSED, got {result['current_stage']}"
    print(f"   OK: final stage={result['current_stage']}")

    print()
    print("=== ALL TESTS PASSED ===")
    return True


if __name__ == "__main__":
    success = test_full_cycle()
    raise SystemExit(0 if success else 1)
