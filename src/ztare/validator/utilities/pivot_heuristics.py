from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PivotProfile:
    name: str
    modules: tuple[str, ...]
    instruction: str


@dataclass(frozen=True)
class PivotState:
    profile: PivotProfile | None
    loop_control_action: str
    event_type: str | None
    pivot_threshold: int
    emergency_threshold: int | None


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
        "a minimalist purist, and an overclaim hunter."
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
    "category_switch": (
        "14. CATEGORY SWITCH: If three consecutive proposals have all lived in the same mathematical "
        "category (e.g., all polynomial-rational-logarithmic functions of a continuous index) and all "
        "have failed, the target likely lives in a DIFFERENT category, not a different parameter "
        "setting within the same category. Before proposing the next form, explicitly name the "
        "category your current proposal inhabits and then name a DIFFERENT category the next proposal "
        "will inhabit. Categories are not topologies — 'sqrt instead of log' is a topology change "
        "within the same category (smooth functions). Categories differ in the underlying objects the "
        "function is defined over: functions of a continuous index, functions on a discrete lattice, "
        "functions defined by inclusion-exclusion over a divisibility order, functions specified by "
        "recurrence, functions specified as fixed points of another operator. State the category "
        "shift explicitly; a proposal that returns to the prior category after stating the switch is "
        "non-compliant."
    ),
    "fixed_point_scan": (
        "15. FIXED-POINT SCAN: Before proposing a general law f for the entire index set, identify "
        "the subset on which f(n) equals some canonical value (0, 1, n itself, or any other "
        "distinguished constant). That subset is a structural fingerprint: it characterises f up to "
        "an equivalence class of laws that share the fingerprint. State the fixed-point / distinguished-"
        "value subset observed in the evidence, explain why it narrows the law's search space, and "
        "design the next proposal to respect it exactly."
    ),
    "collision_exploit": (
        "16. COLLISION AS SIGNAL: When two distinct inputs produce identical outputs, that is not "
        "noise — it is a structural identity the law must satisfy. For each non-trivial collision "
        "f(a) == f(b) with a != b in the evidence, state the relationship between a and b (are they "
        "coprime? do they share a factor? do they differ by a specific transformation?) and what "
        "this implies about the law's invariants. A law that does not reproduce all observed "
        "collisions is wrong; a law that reproduces a collision by coincidence must justify why the "
        "coincidence is structural rather than accidental."
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
    # GP-134 (2026-04-23): Newton-mode discovery profile. Adds category_switch,
    # fixed_point_scan, and collision_exploit on top of the bounded_discriminator
    # base. These three modules target the space ceiling (as distinct from the
    # grammar ceiling) — when the mutator is stuck, these ask it to re-examine
    # the mathematical category / fingerprint subsets / structural identities
    # rather than only reparameterize within the current category.
    "newton_discovery": (
        "state_incompatibility",
        "primary_degree_of_freedom",
        "failure_topology",
        "entropy_stripping",
        "reciprocal_variable",
        "interface_discipline",
        "inversion",
        "coordinate_compression",
        "category_switch",
        "fixed_point_scan",
        "collision_exploit",
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


def get_pivot_thresholds(
    *,
    is_v4_project: bool,
    rubric_mode: str | None = None,
    rubric_stagnation_override: int | None = None,
) -> tuple[int, int | None]:
    """Return (pivot_threshold, emergency_threshold) for the current regime.

    GP-134 (2026-04-23): lowered stagnation threshold from 3 to 2 for
    Newton-mode rubrics, and route Newton-mode to the newton_discovery
    profile which includes category_switch, fixed_point_scan, and
    collision_exploit modules. Rationale: discovery-class substrates
    with blind-feedback loops waste iterations at score 0 before the
    pivot fires; Newton-mode runs benefit from earlier + category-level
    (not just parameter-level) reconfiguration. Kepler / calibration /
    unset modes keep the original >=3 threshold and legacy profiles.

    GP-134 addendum: rubric-specific ``composition_stagnation_threshold``
    overrides the hardcoded Newton/default thresholds when set.  This
    lets individual rubrics opt into longer patience windows (e.g.
    ztare_on_ztare at 5) without losing the Newton pivot profile.
    """
    if is_v4_project:
        # V4 does not use the generic emergency pivot. Once stagnation crosses
        # the threshold, it stays in bounded-mutation override mode.
        return 3, None

    # Rubric-specific override takes precedence over mode-based defaults.
    if rubric_stagnation_override is not None and rubric_stagnation_override > 0:
        pivot_threshold = rubric_stagnation_override
        return pivot_threshold, pivot_threshold + 1

    _mode = (rubric_mode or "").strip().lower()
    newton_threshold = 2
    default_threshold = 3
    pivot_threshold = newton_threshold if _mode == "newton" else default_threshold
    # Preserve the one-step escalation gap from the legacy behavior:
    # default 3→4, newton 2→3.
    return pivot_threshold, pivot_threshold + 1


def select_pivot_profile(
    *,
    is_v4_project: bool,
    falsification_mode: str | None,
    stagnation_count: int,
    rubric_mode: str | None = None,
    rubric_stagnation_override: int | None = None,
) -> PivotProfile | None:
    """Return pivot profile when stagnation warrants it; None otherwise."""
    _mode = (rubric_mode or "").strip().lower()
    pivot_threshold, _ = get_pivot_thresholds(
        is_v4_project=is_v4_project,
        rubric_mode=rubric_mode,
        rubric_stagnation_override=rubric_stagnation_override,
    )
    if stagnation_count < pivot_threshold:
        return None

    if is_v4_project:
        name = "kernel_bounded"
    elif _mode == "newton":
        name = "newton_discovery"
    else:
        fmode = (falsification_mode or "numerical_proof").strip().lower()
        name = "bounded_discriminator" if fmode == "bounded_discriminator" else "legacy_generic"

    return PivotProfile(
        name=name,
        modules=PROFILE_MODULES[name],
        instruction=render_pivot_instruction(name),
    )


def resolve_stagnation_pivot_state(
    *,
    is_v4_project: bool,
    falsification_mode: str | None,
    stagnation_count: int,
    rubric_mode: str | None = None,
    rubric_stagnation_override: int | None = None,
) -> PivotState:
    """Return the active stagnation-phase state for prompt/event/loop wiring."""
    pivot_threshold, emergency_threshold = get_pivot_thresholds(
        is_v4_project=is_v4_project,
        rubric_mode=rubric_mode,
        rubric_stagnation_override=rubric_stagnation_override,
    )
    profile = select_pivot_profile(
        is_v4_project=is_v4_project,
        falsification_mode=falsification_mode,
        stagnation_count=stagnation_count,
        rubric_mode=rubric_mode,
        rubric_stagnation_override=rubric_stagnation_override,
    )

    if is_v4_project and stagnation_count >= pivot_threshold:
        return PivotState(
            profile=profile,
            loop_control_action="stagnation_pivot",
            event_type="v4_bounded_mutation_override",
            pivot_threshold=pivot_threshold,
            emergency_threshold=emergency_threshold,
        )
    if emergency_threshold is not None and stagnation_count >= emergency_threshold:
        return PivotState(
            profile=profile,
            loop_control_action="emergency_pivot",
            event_type="topological_pivot_emergency",
            pivot_threshold=pivot_threshold,
            emergency_threshold=emergency_threshold,
        )
    if stagnation_count >= pivot_threshold:
        return PivotState(
            profile=profile,
            loop_control_action="stagnation_pivot",
            event_type="topological_pivot_profile_injected",
            pivot_threshold=pivot_threshold,
            emergency_threshold=emergency_threshold,
        )
    return PivotState(
        profile=None,
        loop_control_action="normal",
        event_type=None,
        pivot_threshold=pivot_threshold,
        emergency_threshold=emergency_threshold,
    )
