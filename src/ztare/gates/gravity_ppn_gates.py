"""Solar-System / PPN gates for modified-gravity candidates.

Background
----------
Any candidate radial-acceleration form y(g_bar) that claims to describe
matter dynamics across cosmological scales must reduce to Newtonian
gravity (GR's weak-field limit) in the Solar-System regime. This module
adds two cheap analytic gates that fire on substrates which declare
themselves modified-gravity candidates (rubric flag
``enable_solar_system_ppn_gates``):

  * G-CASSINI-PPN — Bertotti, Iess, Tortora (2003) Cassini Shapiro
    time-delay constraint: |γ − 1| < 2.3e-5. Operationalized here as
    max |y(g_bar)/g_bar − 1| over Solar-System probe accelerations
    in [1e-3, 1e-1] m/s² (Jupiter through Mercury orbit ranges).

  * G-MERCURY-PRECESSION — perihelion-precession constraint. GR
    predicts 43.0 arcsec/century, observation matches to <= 0.5%.
    A candidate that deviates fractionally from g_bar by ε at
    Mercury's orbit produces a per-orbit precession anomaly of order
    2π · ε rad/orbit. The 0.5% tolerance on 43.0 arcsec/century
    (415 orbits/century, 5.0185e-7 rad GR shift) admits an extra
    2.5e-9 rad/orbit — i.e. ε <= 4e-10 in principle. We use a
    practical bound of 1e-7 here so that smooth interpolating
    forms whose high-x asymptote is y → x by construction still
    pass even when their finite-eta correction term is non-zero
    at Solar-System x. Forms with ε > 1e-7 would already produce
    measurably anomalous orbits and are flagged.

Engagement / wire-up
--------------------
Both gates engage only when the rubric declares
``enable_solar_system_ppn_gates: true``. They do NOT fire on
substrates with no gravitational claim (galaxy-scale fits, OEIS
sequences, audit substrates, …). The gates are pure-analytic: no
scipy/numpy dependency — `math` is sufficient, candidate is
evaluated as the candidate's own f() function or the rubric's
PARAMETRIC_FORM string.

The gates are wired into the v5.0 Cage gate registry (see
src/ztare/gates/registry.py) for nd_features substrates whose
cage_meta declares modified-gravity intent via the rubric flag.
"""
from __future__ import annotations

import math
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Physical constants (SI)
# ---------------------------------------------------------------------------

G_NEWTON = 6.674e-11           # m^3 kg^-1 s^-2
M_SUN_KG = 1.989e30            # kg
SPEED_OF_LIGHT = 2.998e8       # m/s
GM_SUN = G_NEWTON * M_SUN_KG   # ≈ 1.327e20 m^3/s^2

# Mercury orbital elements
MERCURY_A_M = 5.79e10          # semi-major axis in meters
MERCURY_E = 0.2056             # eccentricity
MERCURY_ORBITS_PER_CENTURY = 415

# Empirical PPN bounds
CASSINI_GAMMA_BOUND = 2.3e-5            # Bertotti, Iess, Tortora (2003)
MERCURY_PRECESSION_TOLERANCE = 0.005    # 0.5% of GR's 43.0 arcsec/century
# Strict fractional-deviation bound on y/g_bar at Mercury's orbit.
# Derived from 0.005 × GR per-orbit shift propagated through the
# perturbation formula 2π·ε ≤ 0.005 · 5.0185e-7 rad → ε ≈ 4e-10.
# The strict bound is the empirically correct one: any candidate form
# whose finite-x deviation at Mercury's g_bar exceeds 4e-10 already
# produces a Mercury perihelion anomaly larger than astronomy's 0.5%
# tolerance. Operator flipped from the loose 1e-7 default to strict
# on 2026-04-27 after the gp163d iter-8 bridge form (verified axiom)
# was found to fail Mercury precession by ~22× (4.8 arcsec/century vs
# the 0.215 arcsec/century allowed). Letting the bridge fail this gate
# honestly forces the next iter (Tier-3 reach) to find a form that
# closes the Solar-System gap — which is what the Galaxy-Cluster
# Bridge needs to become a Tier-3 candidate fundamental claim.
# Substrates wanting the looser operational bound can override via
# rubric key `mercury_precession_relative_bound`.
MERCURY_RELATIVE_BOUND_DEFAULT = 4e-10

# Solar-System probe accelerations (m/s^2). Spans Jupiter (~10^-3)
# through Mercury orbit (~4·10^-2) through closer-Sun probes.
SOLAR_SYSTEM_PROBE_GBARS = (
    1.0e-3,
    3.0e-3,
    1.0e-2,
    2.0e-2,
    3.95e-2,    # Mercury orbit
    5.93e-3,    # Earth orbit (1 AU): GM_sun / (1.496e11)^2 ≈ 5.93e-3
    2.65e-3,    # Mars orbit
    1.0e-1,
    3.0e-1,
)


# ---------------------------------------------------------------------------
# Gate result helper (matches global_gates._gate shape)
# ---------------------------------------------------------------------------

def _gate(
    name: str,
    passed: bool,
    actual: Any,
    threshold: Any,
    reason: str,
    severity: str = "hard_fail",
) -> dict[str, Any]:
    return {
        "name": name,
        "rule": name,
        "passed": passed,
        "flagged": (not passed),
        "actual": actual,
        "threshold": threshold,
        "reason": reason,
        "severity": severity,
        "hard_fail": (severity == "hard_fail") and (not passed),
        "source": "gravity_ppn_gates",
        "evidence": {"actual": actual, "threshold": threshold, "reason": reason},
    }


# ---------------------------------------------------------------------------
# Engagement predicate
# ---------------------------------------------------------------------------

def can_handle(ctx: dict) -> bool:
    """Engage only when the substrate declares it makes gravitational claims.

    The rubric must opt in explicitly via `enable_solar_system_ppn_gates: true`.
    Substrates without a gravitational interpretation (OEIS, queueing,
    dimensional-analysis, audit) leave this flag absent or false and the
    gate skips silently.
    """
    rubric = ctx.get("rubric_data") or ctx.get("rubric") or {}
    if not isinstance(rubric, dict):
        return False
    return bool(rubric.get("enable_solar_system_ppn_gates", False))


# ---------------------------------------------------------------------------
# Candidate evaluation
# ---------------------------------------------------------------------------

def _evaluator_from_context(
    parametric_form: str,
    params: dict,
    context: dict,
) -> Callable[[float, float, float], float] | None:
    """Build a y(g_bar, mass_log10, radius_log10) evaluator.

    Three sources, in priority order:
      1. context['model_fn']: a precompiled callable (preferred — bypasses
         string parsing entirely; this is what gp163d's gate_harness
         already loads).
      2. context['features']: a dict of additional feature defaults to
         substitute when the form references features['k'].
      3. parametric_form string: parsed via eval() with a math-safe
         globals dict and the row's features. This path is used only
         when no compiled callable is provided.
    """
    fn = context.get("model_fn")
    if callable(fn):
        return fn

    if not parametric_form or not isinstance(parametric_form, str):
        return None

    extra_features = context.get("features") or {}
    if not isinstance(extra_features, dict):
        extra_features = {}

    # Gate-time primitive prelude — kept in sync with GP-157
    # `_SAFE_NS_BASE` and the gate harness namespace. v3.5 update
    # (2026-04-27 night): tanh / sinh / cosh / atan2 / log1p / expm1 /
    # log2 added so PPN gates do not crash on hyperbolic-saturation forms
    # the K=3 blitz personas naturally propose.
    safe_globals = {
        "__builtins__": {},
        "math": math,
        "exp": math.exp,
        "log": math.log,
        "log10": math.log10,
        "log2": math.log2,
        "log1p": math.log1p,
        "expm1": math.expm1,
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "tanh": math.tanh,
        "sinh": math.sinh,
        "cosh": math.cosh,
        "atan": math.atan,
        "atan2": math.atan2,
        "asinh": math.asinh,
        "acosh": math.acosh,
        "atanh": math.atanh,
        "asin": math.asin,
        "acos": math.acos,
        "abs": abs,
        "min": min,
        "max": max,
        "pi": math.pi,
        "e": math.e,
        "sigmoid": lambda z, k=1.0, b=0.0: 1.0 / (1.0 + math.exp(-(k * (z - b)))),
    }

    def _evaluate(g_bar: float, mass_log10: float, radius_log10: float) -> float:
        # Patch (2026-04-28): Solar System probe defaults for v3.5 substrate
        # features. Forms that use rho_local_log10 / gas_fraction / sigma /
        # M_gas_log10 (per Evidence Set L) crash here with KeyError otherwise
        # because the PPN gate doesn't pass through substrate columns.
        # Solar System lives in Galactic ISM ≈ 1e8 M_sun/kpc³ → log10 ≈ 8.0
        # (matches the v3.5 substrate's class-S rows). gas_fraction → 0
        # (no gas at planet orbits). sigma → small relative noise.
        features = {
            "x": g_bar,
            "g_bar": g_bar,
            "mass_log10": mass_log10,
            "radius_log10": radius_log10,
            "rho_local_log10": 8.0,            # Solar neighborhood Galactic ISM
            "rho_local_source": "ppn_solar_neighborhood",
            "gas_fraction": 0.0,               # planet orbit, no ICM
            "gas_source": "ppn_solar_default",
            "M_gas_log10": float("nan"),       # not applicable
            "M_gas_source": "ppn_solar_default",
            "SBdisk_log10": float("nan"),
            "sb_source": "ppn_solar_default",
            "M_500c_uncertainty_dex": 0.0,     # Solar System has no cluster mass uncertainty
            "sigma": 1e-10 * abs(g_bar),       # 1e-10 relative — Cassini bound
            "sigma_source": "ppn_solar_default",
            "system_class": "S",
            "system_id": "ppn_anchor",
            "id": -1000,
            "mass_source": "ppn_solar_default",
            "radius_source": "ppn_solar_default",
        }
        features.update(extra_features)        # operator override wins
        local_ns = {
            "features": features,
            "params": dict(params or {}),
            "p": dict(params or {}),
            "x": g_bar,
        }
        return float(eval(parametric_form, safe_globals, local_ns))  # noqa: S307

    return _evaluate


# ---------------------------------------------------------------------------
# G-CASSINI-PPN
# ---------------------------------------------------------------------------

def check_cassini_ppn(
    parametric_form: str,
    params: dict,
    *,
    context: dict | None = None,
) -> dict[str, Any]:
    """Cassini Shapiro time-delay PPN-gamma gate.

    Strategy: evaluate the candidate's predicted y(g_bar) at a fixed set
    of Solar-System probe accelerations (Jupiter through Mercury orbit
    range, ~10^-3 to 10^-1 m/s^2) and check that y/g_bar reduces to 1
    within CASSINI_GAMMA_BOUND (2.3e-5). The "PPN gamma" in this regime
    is operationalized as max |y(g_bar)/g_bar - 1| over the probe set.

    Solar-System mass and radius coordinates are not unique inputs in
    this radial-acceleration framework (g_bar already encodes GM/r^2).
    For substrates whose form additionally depends on (mass_log10,
    radius_log10), we evaluate at the rubric-declared
    `solar_system_probe_coordinates` if present, else fall back to
    Solar-System-typical values (mass_log10=0, radius_log10=-3 — i.e.
    well outside the modified-gravity activation regime).
    """
    name = "G-CASSINI-PPN"
    context = context or {}
    rubric = context.get("rubric_data") or context.get("rubric") or {}
    bound = float(rubric.get("cassini_gamma_bound", CASSINI_GAMMA_BOUND))

    evaluator = _evaluator_from_context(parametric_form, params, context)
    if evaluator is None:
        return _gate(
            name, passed=False, actual=None, threshold=bound,
            reason=(
                f"{name}: no evaluator could be constructed from "
                f"parametric_form (got {type(parametric_form).__name__}) "
                f"and context.model_fn was not callable."
            ),
            severity="hard_fail",
        )

    probe_coords = rubric.get("solar_system_probe_coordinates") or {
        "mass_log10": 0.0,
        "radius_log10": -3.0,
    }
    m_log = float(probe_coords.get("mass_log10", 0.0))
    r_log = float(probe_coords.get("radius_log10", -3.0))

    probes = rubric.get("solar_system_probe_gbars") or SOLAR_SYSTEM_PROBE_GBARS
    deviations: list[tuple[float, float]] = []
    eval_errors: list[str] = []
    for g in probes:
        try:
            y = evaluator(float(g), m_log, r_log)
        except Exception as exc:  # noqa: BLE001
            eval_errors.append(f"g={g:.3e}: {type(exc).__name__}: {exc}")
            continue
        if not math.isfinite(y) or g <= 0.0:
            eval_errors.append(f"g={g:.3e}: non-finite y={y}")
            continue
        deviations.append((float(g), abs(y / float(g) - 1.0)))

    if not deviations:
        return _gate(
            name, passed=False, actual=None, threshold=bound,
            reason=f"{name}: candidate evaluation failed on all probes ({eval_errors})",
            severity="hard_fail",
        )

    worst_g, worst_dev = max(deviations, key=lambda t: t[1])
    passed = worst_dev < bound
    return _gate(
        name=name,
        passed=passed,
        actual=worst_dev,
        threshold=bound,
        reason=(
            f"{name}: max |y/g_bar - 1| = {worst_dev:.3e} at g_bar={worst_g:.3e} m/s^2 "
            f"{'<' if passed else '>='} CASSINI_GAMMA_BOUND={bound:.1e} "
            f"(Bertotti, Iess, Tortora 2003): {'PASS' if passed else 'FAIL — candidate violates Solar-System weak-field GR limit'}"
        ),
        severity="hard_fail",
    )


# ---------------------------------------------------------------------------
# G-MERCURY-PRECESSION
# ---------------------------------------------------------------------------

def check_mercury_perihelion(
    parametric_form: str,
    params: dict,
    *,
    context: dict | None = None,
) -> dict[str, Any]:
    """Mercury perihelion precession gate.

    GR predicts a per-orbit advance of
        Δω_GR = 6πGM / (c²·a·(1−e²))
              ≈ 5.0185e-7 rad/orbit
    × 415 orbits/century × (180/π × 3600 arcsec/rad) ≈ 43.0 arcsec/century.
    Observation matches GR to ≤ 0.5%.

    Approximation: any extra fractional deviation ε in the radial
    acceleration at Mercury's orbit, y/g_bar = 1 + ε, induces a
    per-orbit precession anomaly of order 2π·ε rad/orbit (standard
    perturbation for a small radial force perturbation in a Keplerian
    orbit). The 0.5% tolerance bounds 2π·ε ≤ 0.005·5.0185e-7 ⇒
    ε ≤ ~4e-10 in the strictest limit. The default operational bound
    (`mercury_precession_relative_bound = 1e-7`) is somewhat looser to
    admit smooth interpolating candidates whose finite-η correction
    survives at Solar-System x but whose high-x asymptote is exactly
    Newtonian; rubrics demanding the strict bound override the key.

    Returns: a gate-result dict with the GR per-orbit shift, the
    candidate's per-orbit shift, and the corresponding arcsec/century
    conversion for telemetry.
    """
    name = "G-MERCURY-PRECESSION"
    context = context or {}
    rubric = context.get("rubric_data") or context.get("rubric") or {}
    rel_bound = float(rubric.get(
        "mercury_precession_relative_bound",
        MERCURY_RELATIVE_BOUND_DEFAULT,
    ))
    precession_tol = float(rubric.get(
        "mercury_precession_tolerance",
        MERCURY_PRECESSION_TOLERANCE,
    ))

    evaluator = _evaluator_from_context(parametric_form, params, context)
    if evaluator is None:
        return _gate(
            name, passed=False, actual=None, threshold=rel_bound,
            reason=f"{name}: no evaluator could be constructed",
            severity="hard_fail",
        )

    probe_coords = rubric.get("solar_system_probe_coordinates") or {
        "mass_log10": 0.0,
        "radius_log10": -3.0,
    }
    m_log = float(probe_coords.get("mass_log10", 0.0))
    r_log = float(probe_coords.get("radius_log10", -3.0))

    g_bar_mercury = GM_SUN / MERCURY_A_M ** 2  # ≈ 3.96e-2 m/s^2
    try:
        y_mercury = evaluator(g_bar_mercury, m_log, r_log)
    except Exception as exc:  # noqa: BLE001
        return _gate(
            name, passed=False, actual=None, threshold=rel_bound,
            reason=f"{name}: candidate evaluation raised {type(exc).__name__}: {exc}",
            severity="hard_fail",
        )

    if not math.isfinite(y_mercury):
        return _gate(
            name, passed=False, actual=None, threshold=rel_bound,
            reason=f"{name}: candidate produced non-finite y at Mercury g_bar={g_bar_mercury:.3e}",
            severity="hard_fail",
        )

    epsilon = abs(y_mercury / g_bar_mercury - 1.0)

    # Translate to per-orbit and per-century shifts
    gr_per_orbit_rad = (
        6.0 * math.pi * GM_SUN
        / (SPEED_OF_LIGHT ** 2 * MERCURY_A_M * (1.0 - MERCURY_E ** 2))
    )
    candidate_extra_per_orbit_rad = 2.0 * math.pi * epsilon
    rad_to_arcsec = (180.0 / math.pi) * 3600.0
    gr_arcsec_per_century = (
        gr_per_orbit_rad * MERCURY_ORBITS_PER_CENTURY * rad_to_arcsec
    )
    candidate_arcsec_per_century = (
        candidate_extra_per_orbit_rad * MERCURY_ORBITS_PER_CENTURY * rad_to_arcsec
    )
    fractional_anomaly = (
        candidate_arcsec_per_century / gr_arcsec_per_century
        if gr_arcsec_per_century > 0 else float("inf")
    )

    passed = epsilon < rel_bound
    return _gate(
        name=name,
        passed=passed,
        actual={
            "epsilon_at_mercury": epsilon,
            "candidate_arcsec_per_century_extra": candidate_arcsec_per_century,
            "gr_arcsec_per_century": gr_arcsec_per_century,
            "fractional_precession_anomaly": fractional_anomaly,
            "g_bar_mercury": g_bar_mercury,
        },
        threshold={
            "relative_bound_at_mercury": rel_bound,
            "precession_tolerance_fraction": precession_tol,
        },
        reason=(
            f"{name}: |y/g_bar - 1|={epsilon:.3e} at Mercury g_bar={g_bar_mercury:.3e} m/s^2 "
            f"{'<' if passed else '>='} bound={rel_bound:.1e}; "
            f"GR precession={gr_arcsec_per_century:.3f} arcsec/century, "
            f"candidate extra={candidate_arcsec_per_century:.3e} arcsec/century "
            f"({fractional_anomaly*100:.4f}% of GR shift; "
            f"observed tolerance {precession_tol*100:.2f}%): "
            f"{'PASS' if passed else 'FAIL — would produce anomalous Mercury perihelion'}"
        ),
        severity="hard_fail",
    )


# ---------------------------------------------------------------------------
# Cage registration (legacy-style — used by older harness aggregators)
# ---------------------------------------------------------------------------

def register_gravity_ppn_gates(instance) -> None:
    """Register both PPN gates with a Cage-like instance.

    Used by harnesses that consume `instance.register_gate(name=, check=,
    can_handle=, severity=, priority=)`. The v5.0 Cage at
    src/ztare/gates/registry.py wires these gates separately via
    `Gate(name=..., can_handle=..., run=...)`; both wirings call the
    same underlying functions.
    """
    instance.register_gate(
        name="G-CASSINI-PPN",
        check=check_cassini_ppn,
        can_handle=can_handle,
        severity="hard_fail",
        priority=20,  # cheap analytic — runs early
    )
    instance.register_gate(
        name="G-MERCURY-PRECESSION",
        check=check_mercury_perihelion,
        can_handle=can_handle,
        severity="hard_fail",
        priority=21,
    )


# ---------------------------------------------------------------------------
# v5.0 Cage adapter (registry.py-style)
# ---------------------------------------------------------------------------

def _cage_can_handle(substrate: Any, _candidate: Any) -> tuple[bool, str]:
    """Cage-style engagement predicate."""
    rubric = getattr(substrate, "rubric_data", None)
    if not isinstance(rubric, dict):
        rubric = getattr(substrate, "rubric", None)
    if not isinstance(rubric, dict):
        return False, "substrate exposes no rubric_data dict"
    if not rubric.get("enable_solar_system_ppn_gates", False):
        return False, "rubric.enable_solar_system_ppn_gates is not true"
    return True, "engaged: rubric.enable_solar_system_ppn_gates=True"


def cage_run_cassini(substrate: Any, candidate: Any) -> dict[str, Any]:
    """Cage adapter for G-CASSINI-PPN. Extracts parametric_form, params,
    and a model_fn from the candidate / substrate and calls the gate."""
    pf = (
        getattr(candidate, "parametric_form", None)
        or (candidate.get("parametric_form") if isinstance(candidate, dict) else None)
        or ""
    )
    params = (
        getattr(candidate, "fitted_params", None)
        or (candidate.get("fitted_params") if isinstance(candidate, dict) else None)
        or {}
    )
    model_fn = (
        getattr(candidate, "model_fn", None)
        or (candidate.get("model_fn") if isinstance(candidate, dict) else None)
    )
    rubric = getattr(substrate, "rubric_data", None) or getattr(substrate, "rubric", None) or {}
    return check_cassini_ppn(
        pf, params, context={"rubric_data": rubric, "model_fn": model_fn}
    )


def cage_run_mercury(substrate: Any, candidate: Any) -> dict[str, Any]:
    """Cage adapter for G-MERCURY-PRECESSION."""
    pf = (
        getattr(candidate, "parametric_form", None)
        or (candidate.get("parametric_form") if isinstance(candidate, dict) else None)
        or ""
    )
    params = (
        getattr(candidate, "fitted_params", None)
        or (candidate.get("fitted_params") if isinstance(candidate, dict) else None)
        or {}
    )
    model_fn = (
        getattr(candidate, "model_fn", None)
        or (candidate.get("model_fn") if isinstance(candidate, dict) else None)
    )
    rubric = getattr(substrate, "rubric_data", None) or getattr(substrate, "rubric", None) or {}
    return check_mercury_perihelion(
        pf, params, context={"rubric_data": rubric, "model_fn": model_fn}
    )


__all__ = [
    "CASSINI_GAMMA_BOUND",
    "MERCURY_PRECESSION_TOLERANCE",
    "MERCURY_RELATIVE_BOUND_DEFAULT",
    "SOLAR_SYSTEM_PROBE_GBARS",
    "can_handle",
    "check_cassini_ppn",
    "check_mercury_perihelion",
    "register_gravity_ppn_gates",
    "cage_run_cassini",
    "cage_run_mercury",
]
