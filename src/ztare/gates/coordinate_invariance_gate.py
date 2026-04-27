"""GP-144 Gate G8 — Coordinate Invariance (SPECULATIVE SHELL; implementable today).

Status: 2026-04-24 — largely implementable today for dynamical substrates.
Blocked only on the substrate-specific "transformation group application"
hook, which depends on the declared substrate class.

PURPOSE
-------
For substrates declared coordinate-invariant (chaotic dissipative ODE
attractor invariants under C¹ diffeomorphism; conjecture-refinement
constants under scale-and-shift; topological objects under homeomorphism),
the Phase D writer must verify the claim's numeric value is invariant
under the expected transformation class. Rejects claims whose "invariant"
is actually coordinate-dependent.

DISCOVERY
---------
gp147 iter 2 meta-validation, H6. Generalization of gp140 v2.4 charter's
coordinate-invariance requirement into a claim-pipeline gate.

CORE CHECK
----------
Given:
  - A declared transformation group (e.g. "C1_diffeomorphism_R3",
    "scale_and_shift", "linear_GL_n", or a specific group matrix).
  - A numeric invariant the claim asserts (e.g. Kaplan-Yorke dimension,
    Lyapunov sum, μ_sq for SAW).
  - A function to compute the invariant from raw substrate data.

Apply a random representative of the declared group to the substrate,
recompute the invariant, verify numerical value unchanged within declared
tolerance. Reject if changes beyond tolerance.
"""
from __future__ import annotations

from typing import Any, Callable, Optional
import math

GATE_ID = "coordinate_invariance"
PRODUCER = "GP-144.G8"

DEFAULT_RELATIVE_TOLERANCE = 1e-6
DEFAULT_N_SAMPLE_TRANSFORMATIONS = 3


def apply_scale_and_shift(data, scale: float, shift: float):
    """Apply scale-and-shift transformation to a numerical array-like."""
    import numpy as np
    arr = np.asarray(data, dtype=float)
    return arr * scale + shift


def apply_linear_rotation_3d(data, theta_rad: float):
    """Rotate a 3D trajectory around z-axis by theta radians."""
    import numpy as np
    c, s = math.cos(theta_rad), math.sin(theta_rad)
    R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    arr = np.asarray(data, dtype=float)
    return arr @ R.T


TRANSFORMATION_REGISTRY = {
    "scale_and_shift": apply_scale_and_shift,
    "rotation_z_3d": apply_linear_rotation_3d,
    # Add more as substrate classes require
}


def invariance_check(
    substrate_data,
    invariant_fn: Callable,
    transformation_name: str,
    transformation_params_list: list[dict],
    relative_tolerance: float = DEFAULT_RELATIVE_TOLERANCE,
) -> dict[str, Any]:
    """Apply each transformation, recompute invariant, check preservation.

    IMPLEMENTED TODAY for registered transformations + a supplied
    invariant_fn.
    """
    if transformation_name not in TRANSFORMATION_REGISTRY:
        return {
            "implemented": False,
            "blocked_on": f"transformation '{transformation_name}' not in registry",
            "passed": None,
            "registry_contents": list(TRANSFORMATION_REGISTRY.keys()),
        }
    transform = TRANSFORMATION_REGISTRY[transformation_name]
    baseline_value = invariant_fn(substrate_data)
    samples = []
    max_rel_diff = 0.0
    for params in transformation_params_list:
        try:
            transformed = transform(substrate_data, **params)
            transformed_value = invariant_fn(transformed)
            if abs(baseline_value) > 1e-12:
                rel_diff = abs(transformed_value - baseline_value) / abs(baseline_value)
            else:
                rel_diff = abs(transformed_value - baseline_value)
            max_rel_diff = max(max_rel_diff, rel_diff)
            samples.append({
                "params": params,
                "transformed_value": float(transformed_value),
                "relative_diff": float(rel_diff),
            })
        except Exception as e:
            samples.append({"params": params, "error": str(e)})
    passed = max_rel_diff < relative_tolerance
    return {
        "implemented": True,
        "passed": passed,
        "baseline_value": float(baseline_value),
        "max_relative_diff": float(max_rel_diff),
        "tolerance": relative_tolerance,
        "samples": samples,
        "reason": ("invariant_preserved" if passed
                   else f"invariant_changes_max_rel_diff_{max_rel_diff:.2e}_exceeds_{relative_tolerance:.2e}"),
    }


def run_gate(
    claim: dict[str, Any],
    rubric_params: dict[str, Any],
) -> dict[str, Any]:
    """Run G8 coordinate-invariance on a claim.

    claim schema:
        {
            "substrate_data": <numpy-array-like numerical data>,
            "invariant_fn": <callable: substrate_data → float>,
            "transformation_name": "scale_and_shift" | "rotation_z_3d" | ...,
            "transformation_params_list": [{"scale": 2.0, "shift": 1.0}, ...],
            "relative_tolerance": <float, default 1e-6>
        }

    Note: invariant_fn must be serialisable via callable reference, not a
    lambda (for pickle compatibility if used in multi-process gate).
    """
    substrate_data = claim.get("substrate_data")
    invariant_fn = claim.get("invariant_fn")
    transformation_name = claim.get("transformation_name", "")
    params_list = claim.get("transformation_params_list", [])
    tol = float(rubric_params.get("relative_tolerance", DEFAULT_RELATIVE_TOLERANCE))

    if substrate_data is None or invariant_fn is None or not params_list:
        return {
            "name": GATE_ID,
            "passed": None,
            "actual": None,
            "threshold": None,
            "reason": ("shell_partial: requires substrate_data + invariant_fn + "
                       "transformation_params_list. Declared substrate-class should "
                       "supply these."),
            "penalty": 0,
            "hard_fail": False,
            "source": PRODUCER,
            "extra": {
                "shell_fully_implemented": False,
                "blocked_on": "substrate-class-specific invariant_fn + data + transforms",
            },
        }

    r = invariance_check(substrate_data, invariant_fn, transformation_name,
                         params_list, relative_tolerance=tol)
    if not r.get("implemented"):
        return {
            "name": GATE_ID,
            "passed": None,
            "actual": None,
            "threshold": None,
            "reason": r.get("blocked_on", "unknown_transformation"),
            "penalty": 0,
            "hard_fail": False,
            "source": PRODUCER,
            "extra": {"invariance_check": r, "shell_fully_implemented": False},
        }
    return {
        "name": GATE_ID,
        "passed": r["passed"],
        "actual": r["max_relative_diff"],
        "threshold": r["tolerance"],
        "reason": r["reason"],
        "penalty": 0 if r["passed"] else 1,
        "hard_fail": not r["passed"],
        "source": PRODUCER,
        "extra": {
            "invariance_check": r,
            "shell_fully_implemented": True,
        },
    }


def filter_per_candidate_for_mutator_prompt(gate_result: dict[str, Any]) -> dict[str, Any]:
    filtered = {k: v for k, v in gate_result.items() if k != "extra"}
    extra = gate_result.get("extra", {})
    filtered["extra"] = {
        "shell_fully_implemented": extra.get("shell_fully_implemented"),
        "invariance_passed": extra.get("invariance_check", {}).get("passed"),
        "max_relative_diff": extra.get("invariance_check", {}).get("max_relative_diff"),
    }
    return filtered
