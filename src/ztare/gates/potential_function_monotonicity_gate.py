"""G-POTENTIAL-FUNCTION-MONOTONICITY — gate for problem-solver iterative refinement (ps_02).

Operationalizes ps_02 ("Governed Iterative Refinement") from the GP-216
problem-solving sister vocabulary: an iterative process is proven to terminate
by defining a scalar potential function that monotonically improves at each
step and is bounded by a fixed ceiling.

When a rubric runs in iterative mode (most ZTARE rubrics) and declares a
potential function in metadata, this gate verifies:

  M1. Potential function is declared in rubric metadata (forces explicit
      declaration; cannot run iterative work without naming the potential).
  M2. Potential strictly improves for ≥3 consecutive iterations OR the
      iteration is officially in stagnation-detection mode.
  M3. Potential stays bounded by declared ceiling.
  M4. If potential decreases for ≥2 consecutive iterations, fire as warning
      (potential is not monotone — either iteration is broken, or wrong
      potential function was named).

Failure modes caught:
  - Iteration without declared termination proof (forces honest declaration)
  - Score that improves but where the actual potential is not improving
    (silent stagnation hidden by score-game)
  - Out-of-bound iteration where potential exceeds declared ceiling
  - Non-monotonic potential indicating broken iteration or wrong potential

Usage
-----
  from src.ztare.gates.potential_function_monotonicity_gate import run_potential_gate
  result = run_potential_gate(iteration_history, rubric_data=rubric)
  if not result["passed"]:
      # treat as gate-strike; record violation type
      ...

Returns:
  {
    "passed": bool,
    "violations": list[dict],
    "potential_declared": bool,
    "potential_name": str | None,
    "trajectory": list[float],  # potential values over iterations
    "monotone": bool,
    "ceiling_ok": bool,
    "summary": str,
  }
"""
from __future__ import annotations

from typing import Any, Callable, Optional


def run_potential_gate(
    iteration_history: list[dict],
    rubric_data: dict[str, Any] | None = None,
    *,
    min_iterations_to_check: int = 3,
    consecutive_decrease_warning: int = 2,
    extract_potential: Optional[Callable[[dict, dict], float]] = None,
) -> dict[str, Any]:
    """Verify potential function monotonicity for an iterative refinement substrate.

    Args:
        iteration_history: list of iteration dicts; each dict should contain
          (at minimum) a `score` field. If the rubric declares a potential
          function name in metadata, that field is read instead.
        rubric_data: rubric metadata. Looks for `potential_function` key with
          schema:
            {
              "name": "<descriptive name>",  # e.g., "density_increment_total"
              "field": "<field in iteration to read>",  # e.g., "potential_value"
              "ceiling": <float>,  # max allowed value
              "monotone": "increasing" | "decreasing",  # which direction is good
              "tolerance": <float>,  # fluctuation tolerance per step
            }
        min_iterations_to_check: minimum iteration count before gate fires
        consecutive_decrease_warning: number of consecutive bad-direction steps
          before warning
        extract_potential: optional fn(iteration_dict, rubric_meta) -> float
          for custom extraction logic; defaults to reading `field` directly.

    Returns:
        Result dict with passed/violations/trajectory etc.
    """
    rubric_data = rubric_data or {}
    pf_meta = rubric_data.get("potential_function")
    violations: list[dict[str, Any]] = []

    # M1: potential function must be declared
    if not pf_meta:
        violations.append({
            "type": "potential_not_declared",
            "severity": "blocking",
            "reason": (
                "Iterative rubric is running without a declared potential function. "
                "ps_02 (Governed Iterative Refinement) requires a named potential "
                "with monotonicity proof. Add `potential_function` to rubric metadata."
            ),
        })
        return {
            "passed": False,
            "violations": violations,
            "potential_declared": False,
            "potential_name": None,
            "trajectory": [],
            "monotone": None,
            "ceiling_ok": None,
            "summary": "Potential not declared",
        }

    field = pf_meta.get("field", "score")
    name = pf_meta.get("name", field)
    ceiling = pf_meta.get("ceiling")
    monotone_dir = pf_meta.get("monotone", "increasing")
    tolerance = pf_meta.get("tolerance", 0.0)

    # M2: extract potential trajectory
    trajectory: list[float] = []
    extractor = extract_potential or (lambda it, meta: float(it.get(meta.get("field", "score"), 0.0)))
    for it in iteration_history:
        try:
            v = extractor(it, pf_meta)
            trajectory.append(float(v))
        except Exception as e:
            violations.append({
                "type": "potential_extraction_failed",
                "severity": "blocking",
                "iteration": it.get("iter", "?"),
                "reason": f"Could not extract potential field {field!r}: {type(e).__name__}: {e}",
            })

    if len(trajectory) < min_iterations_to_check:
        return {
            "passed": True,
            "violations": violations,
            "potential_declared": True,
            "potential_name": name,
            "trajectory": trajectory,
            "monotone": None,
            "ceiling_ok": None,
            "summary": f"Only {len(trajectory)} iterations; gate defers until ≥{min_iterations_to_check}",
        }

    # M3: ceiling check
    ceiling_ok = True
    if ceiling is not None:
        for i, v in enumerate(trajectory):
            if monotone_dir == "increasing" and v > ceiling + tolerance:
                ceiling_ok = False
                violations.append({
                    "type": "potential_exceeds_ceiling",
                    "severity": "blocking",
                    "iteration": i,
                    "value": v,
                    "ceiling": ceiling,
                    "reason": (
                        f"Potential {name}={v} exceeds declared ceiling {ceiling} at iter {i}. "
                        f"Either potential is wrong, ceiling is wrong, or iteration is unbounded."
                    ),
                })
            elif monotone_dir == "decreasing" and v < ceiling - tolerance:
                ceiling_ok = False
                violations.append({
                    "type": "potential_below_ceiling",
                    "severity": "blocking",
                    "iteration": i,
                    "value": v,
                    "ceiling": ceiling,
                    "reason": (
                        f"Potential {name}={v} below declared floor {ceiling} at iter {i}."
                    ),
                })

    # M4: monotonicity check
    monotone = True
    consecutive_bad = 0
    for i in range(1, len(trajectory)):
        prev, curr = trajectory[i - 1], trajectory[i]
        if monotone_dir == "increasing":
            bad_step = curr < prev - tolerance
        else:  # decreasing
            bad_step = curr > prev + tolerance
        if bad_step:
            consecutive_bad += 1
            if consecutive_bad >= consecutive_decrease_warning:
                monotone = False
                violations.append({
                    "type": "potential_non_monotone",
                    "severity": "warning",
                    "iteration": i,
                    "prev": prev,
                    "curr": curr,
                    "consecutive_bad": consecutive_bad,
                    "reason": (
                        f"Potential {name} moved in wrong direction for {consecutive_bad} consecutive "
                        f"steps (monotone={monotone_dir!r}). Either iteration is broken or wrong potential named."
                    ),
                })
        else:
            consecutive_bad = 0

    # Stagnation: no improvement for ≥3 consecutive iterations beyond tolerance
    stagnation = False
    consecutive_flat = 0
    for i in range(1, len(trajectory)):
        prev, curr = trajectory[i - 1], trajectory[i]
        improvement = curr - prev if monotone_dir == "increasing" else prev - curr
        if improvement <= tolerance:
            consecutive_flat += 1
            if consecutive_flat >= 3:
                stagnation = True
                violations.append({
                    "type": "potential_stagnation",
                    "severity": "warning",
                    "iteration": i,
                    "consecutive_flat": consecutive_flat,
                    "reason": (
                        f"Potential {name} did not improve for {consecutive_flat} consecutive iterations. "
                        f"Either iteration has converged, or potential is decoupled from real progress."
                    ),
                })
                break
        else:
            consecutive_flat = 0

    blocking = [v for v in violations if v.get("severity") == "blocking"]
    passed = len(blocking) == 0

    return {
        "passed": passed,
        "violations": violations,
        "potential_declared": True,
        "potential_name": name,
        "trajectory": trajectory,
        "monotone": monotone,
        "ceiling_ok": ceiling_ok,
        "stagnation": stagnation,
        "summary": (
            f"Potential={name}; n={len(trajectory)}; monotone={monotone}; "
            f"ceiling_ok={ceiling_ok}; stagnation={stagnation}; "
            f"blocking_violations={len(blocking)}"
        ),
    }


def _self_test() -> None:
    """Smoke test."""
    # Test 1: monotone-increasing potential, no ceiling violation
    history = [
        {"iter": 0, "potential_value": 0.10},
        {"iter": 1, "potential_value": 0.18},
        {"iter": 2, "potential_value": 0.27},
        {"iter": 3, "potential_value": 0.34},
    ]
    rubric = {"potential_function": {"name": "density_increment", "field": "potential_value",
                                      "ceiling": 1.0, "monotone": "increasing", "tolerance": 0.01}}
    r = run_potential_gate(history, rubric)
    assert r["passed"], f"Test 1 should pass: {r}"
    assert r["monotone"], "Test 1 should be monotone"
    print("  Test 1 PASS (monotone-increasing trajectory)")

    # Test 2: ceiling violation
    history2 = [
        {"iter": 0, "potential_value": 0.50},
        {"iter": 1, "potential_value": 0.80},
        {"iter": 2, "potential_value": 1.20},  # exceeds ceiling
        {"iter": 3, "potential_value": 1.50},
    ]
    r = run_potential_gate(history2, rubric)
    assert not r["passed"], f"Test 2 should fail: {r}"
    assert any(v["type"] == "potential_exceeds_ceiling" for v in r["violations"])
    print("  Test 2 PASS (ceiling violation detected)")

    # Test 3: missing declaration
    r = run_potential_gate(history, {})
    assert not r["passed"], f"Test 3 should fail: {r}"
    assert any(v["type"] == "potential_not_declared" for v in r["violations"])
    print("  Test 3 PASS (missing declaration detected)")

    # Test 4: non-monotone trajectory
    history4 = [
        {"iter": 0, "potential_value": 0.10},
        {"iter": 1, "potential_value": 0.20},
        {"iter": 2, "potential_value": 0.05},  # drops
        {"iter": 3, "potential_value": 0.02},  # drops again
    ]
    r = run_potential_gate(history4, rubric)
    assert any(v["type"] == "potential_non_monotone" for v in r["violations"])
    print("  Test 4 PASS (non-monotone trajectory detected)")

    # Test 5: stagnation
    history5 = [
        {"iter": 0, "potential_value": 0.50},
        {"iter": 1, "potential_value": 0.51},
        {"iter": 2, "potential_value": 0.51},
        {"iter": 3, "potential_value": 0.51},
        {"iter": 4, "potential_value": 0.51},
    ]
    r = run_potential_gate(history5, rubric)
    assert r["stagnation"], f"Test 5 should detect stagnation: {r}"
    print("  Test 5 PASS (stagnation detected)")

    print("All self-tests passed.")


if __name__ == "__main__":
    _self_test()
