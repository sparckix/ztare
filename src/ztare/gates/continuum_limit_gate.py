"""GP-144 Gate G1 — Continuum-Limit Reality (SPECULATIVE SHELL).

Status: 2026-04-24 — speculative shell; full implementation deferred until a
PDE-class substrate enters the roadmap. The shell documents the API and
returns a well-defined "blocked on substrate" result when invoked with a
non-PDE claim.

PURPOSE
-------
Verify that a claimed PDE singularity / blow-up is a CONTINUUM-LIMIT
phenomenon and not a finite-resolution pseudo-singularity that dissolves
under mesh refinement.

Three sub-gates when fully implemented:
  1. Resolution-refinement invariant: re-extract candidate at >=3 grid
     resolutions with refinement ratio >=2. Candidate's Lean-verified
     blow-up must persist across all resolutions. Dissolution at higher h
     → rejected.
  2. BKM criterion: compute integral_{0}^{T} ||omega(.,t)||_inf dt from
     simulation data. Bounded → guaranteed no blow-up (Beale-Kato-Majda
     1984). Unbounded → candidate survives.
  3. Leray-scaling sub-gate: candidate must exhibit self-similar scaling
     u(x,t) = (T-t)^{-1/2} U(x/(T-t)^{1/2}). No such fit → rejected.

ADDITIONALLY (RMS Chaos Trap, 2026-04-24 layer-4 enforcement):
The fully-implemented gate MUST reject any Method-A fitness rule that uses
trajectory-level RMS over window T where T*lambda_max > 5. Per
docs/concepts/chaos_substrate_primitives.md Principle 1.

STATUS OF EACH CONTRACT
-----------------------
Shell signature stable. All three sub-gates return
{"implemented": False, "blocked_on": "PDE substrate roadmap"}.

INTEGRATION
-----------
Called from (future) autoresearch_loop.py PHASE D INV-3 writer when
assembling test_model.py for a substrate with declared class
"continuous_pde_*". Currently no such substrate exists in the repo.
"""
from __future__ import annotations

from typing import Any, Optional

GATE_ID = "continuum_limit"
PRODUCER = "GP-144.G1"


def resolution_refinement_check(
    candidate: dict[str, Any],
    resolutions: list[float],
    refinement_ratio_min: float = 2.0,
) -> dict[str, Any]:
    """Placeholder — would re-extract candidate at each resolution, verify
    the Lean-verified blow-up persists across all.

    Currently returns {"implemented": False, "blocked_on": "PDE substrate roadmap"}.
    """
    return {
        "implemented": False,
        "blocked_on": "PDE substrate roadmap",
        "reason": "Requires PDE simulation at 3+ resolutions; no such substrate in repo yet.",
    }


def bkm_criterion_check(
    vorticity_norm_series: Optional[list[float]],
    dt: float,
) -> dict[str, Any]:
    """Placeholder for Beale-Kato-Majda criterion. Would compute
    integral_{0}^{T} ||omega(.,t)||_inf dt and check divergence.

    Currently returns {"implemented": False, "blocked_on": "vorticity data
    extraction"}.
    """
    return {
        "implemented": False,
        "blocked_on": "vorticity data extraction pipeline",
        "reason": "Requires omega(x,t) extraction from PDE sim output; substrate-specific.",
    }


def leray_scaling_check(
    trajectory: Optional[list[float]],
    blow_up_time_estimate: Optional[float],
) -> dict[str, Any]:
    """Placeholder for Leray self-similarity check. Would fit
    u(x,t) = (T-t)^{-1/2} U(x/(T-t)^{1/2}) ansatz and verify the fit.

    Currently returns {"implemented": False, "blocked_on": "Leray ansatz fitter"}.
    """
    return {
        "implemented": False,
        "blocked_on": "Leray-self-similar ansatz fitter",
        "reason": "Requires a scaling-exponent fit routine; not built.",
    }


def rms_chaos_trap_precheck(
    candidate: dict[str, Any],
    rubric_params: dict[str, Any],
) -> dict[str, Any]:
    """ALREADY specifiable — checks the Method-A fitness rule does not use
    trajectory-level RMS when substrate has positive lambda_max.

    This is the one sub-gate that can be implemented today. It's a
    static check over the candidate's declared fitness method.
    """
    fitness_method = candidate.get("fitness_method", "")
    lambda_max = rubric_params.get("lambda_max_declared")
    window_T = rubric_params.get("observation_T")
    if "rms" in fitness_method.lower() and "trajectory" in fitness_method.lower():
        if lambda_max is not None and window_T is not None:
            if window_T * lambda_max > 5:
                return {
                    "passed": False,
                    "reason": (f"RMS-chaos-trap: trajectory RMS over T={window_T} "
                               f"with lambda_max={lambda_max} (T*lambda_max="
                               f"{window_T * lambda_max:.1f} > 5) mathematically "
                               f"explodes even for correct generator. See "
                               f"docs/concepts/chaos_substrate_primitives.md Principle 1."),
                    "check": "rms_chaos_trap_precheck",
                }
    return {"passed": True, "reason": "rms_chaos_trap_precheck_ok"}


def run_gate(
    claim: dict[str, Any],
    rubric_params: dict[str, Any],
) -> dict[str, Any]:
    """Run the G1 continuum-limit gate on a claim.

    Currently: runs the rms_chaos_trap_precheck (implemented) and returns
    a "shell_not_fully_implemented" verdict for the rest. When PDE
    substrate exists + vorticity extraction + Leray fitter are built,
    this will become a real 3-sub-gate composite.
    """
    pre = rms_chaos_trap_precheck(claim, rubric_params)
    if not pre.get("passed"):
        return {
            "name": GATE_ID,
            "passed": False,
            "actual": None,
            "threshold": None,
            "reason": pre["reason"],
            "penalty": 1,
            "hard_fail": True,
            "source": PRODUCER,
            "extra": {"precheck_failed": True, "precheck": pre,
                      "shell_fully_implemented": False},
        }
    # Three sub-gates deferred
    r_refine = resolution_refinement_check(claim, resolutions=[], refinement_ratio_min=2.0)
    r_bkm = bkm_criterion_check(None, 0.0)
    r_leray = leray_scaling_check(None, None)
    return {
        "name": GATE_ID,
        "passed": None,  # undecided; shell
        "actual": None,
        "threshold": None,
        "reason": ("shell_not_fully_implemented: RMS-chaos-trap precheck passed, "
                   "but resolution/BKM/Leray sub-gates are blocked on PDE infra."),
        "penalty": 0,
        "hard_fail": False,
        "source": PRODUCER,
        "extra": {
            "precheck": pre,
            "resolution_refinement": r_refine,
            "bkm": r_bkm,
            "leray_scaling": r_leray,
            "shell_fully_implemented": False,
        },
    }


def filter_per_candidate_for_mutator_prompt(gate_result: dict[str, Any]) -> dict[str, Any]:
    """Mutator-view filter: strip sub-gate internals, keep verdict + categories."""
    filtered = {k: v for k, v in gate_result.items() if k != "extra"}
    extra = gate_result.get("extra", {})
    filtered["extra"] = {
        "shell_fully_implemented": extra.get("shell_fully_implemented"),
        "precheck_passed": extra.get("precheck", {}).get("passed"),
    }
    return filtered
