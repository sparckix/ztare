from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PivotProfile:
    name: str
    modules: tuple[str, ...]
    instruction: str


MODULE_TEXT = {
    "state_incompatibility": (
        "1. STATE INCOMPATIBILITY: Treat the current critique as an invariant of the environment. "
        "If that constraint is absolute, what architecture still reaches the target state?"
    ),
    "primary_degree_of_freedom": (
        "2. PRIMARY DEGREE OF FREEDOM: Identify the single variable whose state change would force "
        "a deterministic reconfiguration of the rest of the system."
    ),
    "failure_topology": (
        "3. FAILURE TOPOLOGY: Fast-forward to collapse. Name the 3 concrete failure nodes, erase "
        "the assumptions supporting them, and design a bypass that does not depend on their stability."
    ),
    "entropy_stripping": (
        "4. ENTROPY STRIPPING: Remove narrative comfort language. Restate the system only in terms "
        "of observable transfers, thresholds, and control points."
    ),
    "dimensional_shift": (
        "5. DIMENSIONAL SHIFT: If the current object class makes the problem unsolvable, consider "
        "a higher-dimensional reframe only if it stays testable and auditable."
    ),
    "reciprocal_variable": (
        "6. RECIPROCAL VARIABLE: If the primary variable is locked, identify the reciprocal variable "
        "that can still force the same resultant state."
    ),
    "adversarial_stress_test": (
        "7. ADVERSARIAL STRESS-TEST: Pressure-test the candidate design against a forensic skeptic, "
        "a minimalist purist, and a moat hunter."
    ),
    "success_liability": (
        "8. SUCCESS LIABILITY: If the mechanism works, what new technical, legal, or competitive "
        "resistance is created by that success?"
    ),
    "coercive_leverage": (
        "9. COERCIVE LEVERAGE: Identify the veto player and derive the asymmetric leverage that makes "
        "the status quo more painful than the transition."
    ),
    "back_pressure": (
        "10. BACK PRESSURE: Assume non-zero systemic friction and specify how implementation lag or "
        "organizational resistance degrades the near-term trajectory."
    ),
    "interface_discipline": (
        "11. INTERFACE DISCIPLINE: Keep the mutation at the interface/gate layer. Do not solve a local "
        "failure by inventing a new global ontology or replacing the whole architecture."
    ),
    "inversion": (
        "12. INVERSION (always invert): Stop asking how to make the hypothesis work. Ask what "
        "single observation, input, or condition would destroy it. If direct optimization of the "
        "target variable has stalled, optimize its inverse, its rate of change, or the error "
        "between prediction and observation. The question that breaks the deadlock is almost never "
        "the question you have been asking."
    ),
    "coordinate_compression": (
        "13. COORDINATE COMPRESSION: If the gap between model and reality spans orders of magnitude "
        "or grows without bound, you are working in the wrong units. Change the coordinate system: "
        "absolute values to ratios, levels to rates of change, raw magnitudes to log-scale. The "
        "transform must be justified by the observed structure of the failure — state what pattern "
        "you see in the residual and why this specific change of coordinates makes it bounded. "
        "After transforming, check for hidden structure (periodicity, alternating sign, phase "
        "transitions) that was invisible in the original coordinates."
    ),
}


PROFILE_MODULES = {
    "legacy_generic": (
        "state_incompatibility",
        "primary_degree_of_freedom",
        "failure_topology",
        "entropy_stripping",
        "dimensional_shift",
        "reciprocal_variable",
        "adversarial_stress_test",
        "success_liability",
        "coercive_leverage",
        "back_pressure",
    ),
    "bounded_discriminator": (
        "state_incompatibility",
        "primary_degree_of_freedom",
        "failure_topology",
        "entropy_stripping",
        "dimensional_shift",
        "reciprocal_variable",
        "success_liability",
        "back_pressure",
        "interface_discipline",
        "inversion",
        "coordinate_compression",
    ),
    "kernel_bounded": (
        "failure_topology",
        "success_liability",
        "interface_discipline",
    ),
}


def render_pivot_instruction(profile_name: str) -> str:
    modules = PROFILE_MODULES[profile_name]
    body = "\n        ".join(MODULE_TEXT[key] for key in modules)
    return f"""
                ### PIVOT PROFILE: {profile_name}
        Apply the following heuristic modules:

        {body}

        TASK:
        - Execute a structural mutation rather than cosmetic iteration.
        - Keep the resulting thesis auditable against the current evidence boundary.
        - Name the trade-offs created by the new mechanism instead of hiding them.
        """


def select_pivot_profile(
    *,
    is_v4_project: bool,
    falsification_mode: str | None,
    stagnation_count: int,
) -> PivotProfile | None:
    if stagnation_count < 3:
        return None

    if is_v4_project:
        name = "kernel_bounded"
    else:
        fmode = (falsification_mode or "numerical_proof").strip().lower()
        name = "bounded_discriminator" if fmode == "bounded_discriminator" else "legacy_generic"

    return PivotProfile(
        name=name,
        modules=PROFILE_MODULES[name],
        instruction=render_pivot_instruction(name),
    )
