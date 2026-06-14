"""Rubric mode → flag resolution.

Single entry point: `apply_rubric_mode_defaults(rubric_data)`. Called once
at rubric-load time in autoresearch_loop. Reads `rubric_data["rubric_mode"]`
and fills in mode-implied flag defaults WITHOUT overwriting explicit
operator-set values.

Why this module exists
----------------------
Rubric modes use two related fields. `rubric_mode` is the primary scoring
discipline (`newton`, `kepler`, or `calibration`) validated at launch.
`rubric_modes` is an optional list of secondary apparatus profiles such
as `invariant_search`.
Without a resolver, every consumer of `enable_lagrangian_derivation` /
`enable_buckingham_pi_gate` / `noether_variance_weight` has to read
`rubric_mode` and back-fill defaults — exactly the duplicated-flag
drift flagged in the GP-153/GP-167 architecture audit. This file owns the
mapping and runs ONCE; downstream code reads only the flags.

Modes
-----
- `newton`: primary discovery-class scoring discipline. Launch requires
  a Generative Yield dimension.
- `kepler`: primary descriptive-fit scoring discipline. No Generative
  Yield requirement.
- `calibration`: primary apparatus-characterization discipline. Discovery
  claims are suppressed.
- `invariant_search` (GP-180/GP-181, 2026-04-28): the action-principle
  secondary profile. Activates Lagrangian derivation, Buckingham π gate
  (soft), Noether variance loss, and DAG steering. Operator may override
  any individual flag in the rubric — explicit settings win.

Operator override rule
----------------------
If `rubric_data` already has a key `K` set to a non-None value, this
resolver will NOT overwrite it. Modes apply defaults, not mandates.
This is the behavior every existing rubric flag uses (anchor_lambda,
k_law_max, etc.) and keeps the resolver from surprising operators who
set a flag explicitly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# Mode → {flag_name: default_value}. Add new modes here, not in
# autoresearch_loop. Keep this dict small and readable; if a mode needs
# more than ~6 flags, it is probably trying to do too much.
_MODE_DEFAULTS: dict[str, dict[str, Any]] = {
    "invariant_search": {
        # GP-180 — replace mutator PARAMETRIC_FORM with sympy-derived form
        # whenever the mutator declares a LAGRANGIAN.
        "enable_lagrangian_derivation": True,
        # GP-179 — reject transcendentals with raw dimensional arguments.
        # Soft mode: surface to briefing, do not skip the fit.
        "enable_buckingham_pi_gate": True,
        "buckingham_strict": False,
        # GP-180 Noether-variance loss — penalize inconstant Π across
        # rows. 0.3 is the calibration default; rubric can override.
        "noether_variance_weight": 0.3,
        # GP-134 closed-loop DAG steering — surface the weakest claim
        # to the mutator's briefing.
        "enable_dag_steering": True,
        # GP-184 cold-shot structural-seed primitive (paper 7 §11.14).
        # Pre-iter-1 single LLM call with substrate context +
        # falsification gates as constraints. Default ON under
        # invariant_search because the cold-shot synthesizes the kind
        # of structural prior the iterative mutator fails to reach
        # under briefing-density pressure.
        "enable_cold_shot_seed": True,
        # GP-183 C1 — harden G-LAGRANGIAN-NONTRIVIAL gate. When the
        # mutator declares a trivially-substituted Lagrangian
        # (q = single_background), discard the derived form and revert
        # to the mutator's PARAMETRIC_FORM rather than fitting a
        # cosmetic substitution.
        "require_nontrivial_lagrangian": True,
    },
}

_PRIMARY_MODE_DESCRIPTIONS: dict[str, str] = {
    "newton": "primary discovery scoring; requires Generative Yield",
    "kepler": "primary descriptive-fit scoring; no Generative Yield gate",
    "calibration": "primary apparatus-characterization scoring",
}


def _collect_active_modes(rubric_data: dict) -> list[str]:
    """Return the list of mode names active on this rubric.

    Layering rules:
    - `rubric_mode: "X"` (string)         — single mode, primary.
    - `rubric_modes: ["X", "Y"]` (list)   — explicit composition.
    - Both forms compose: a rubric can carry `rubric_mode: "newton"`
      AND `rubric_modes: ["invariant_search"]`. Order matters only
      for tie-breaks (later wins on overlapping defaults).
    """
    out: list[str] = []
    primary = rubric_data.get("rubric_mode")
    if isinstance(primary, str) and primary.strip():
        out.append(primary.strip().lower())
    secondary = rubric_data.get("rubric_modes")
    if isinstance(secondary, list):
        for s in secondary:
            if isinstance(s, str) and s.strip():
                m = s.strip().lower()
                if m not in out:
                    out.append(m)
    return out


def apply_rubric_mode_defaults(rubric_data: dict) -> dict:
    """Mutate `rubric_data` in place to fill mode-implied flag defaults.

    Operator-set values WIN. Modes compose left-to-right: each mode's
    defaults apply only to flags still unset after the prior mode.
    Returns the same dict for fluent use.
    """
    for mode in _collect_active_modes(rubric_data):
        defaults = _MODE_DEFAULTS.get(mode)
        if not defaults:
            continue
        for k, v in defaults.items():
            if rubric_data.get(k) is None:
                rubric_data[k] = v
    return rubric_data


def describe_rubric_mode(rubric_data: dict) -> str:
    """Human-readable line for the run banner."""
    modes = _collect_active_modes(rubric_data)
    if not modes:
        return "rubric_mode=<unset>"
    parts = []
    for m in modes:
        if m in _MODE_DEFAULTS:
            flags = ", ".join(f"{k}={rubric_data.get(k)}" for k in _MODE_DEFAULTS[m])
            parts.append(f"{m!r} → {flags}")
        elif m in _PRIMARY_MODE_DESCRIPTIONS:
            parts.append(f"{m!r} ({_PRIMARY_MODE_DESCRIPTIONS[m]})")
        else:
            parts.append(f"{m!r} (no defaults registered)")
    return "rubric_modes: " + " ; ".join(parts)


@dataclass(frozen=True)
class RubricModeContractResult:
    """Launch-time validation result for the primary rubric mode."""

    ok: bool
    mode: str
    message: str


def _dimension_weight(dimension: dict[str, Any]) -> float:
    try:
        return float(dimension.get("weight", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def _has_generative_yield_dimension(rubric_data: dict) -> bool:
    dimensions = rubric_data.get("dimensions", []) or []
    return any(
        isinstance(dimension, dict)
        and "generative yield" in str(dimension.get("name", "")).lower()
        and _dimension_weight(dimension) >= 15
        for dimension in dimensions
    )


def validate_rubric_mode_contract(rubric_data: dict) -> RubricModeContractResult:
    """Validate the launch contract implied by ``rubric_mode``.

    This owns the GP-133 Round 4 mode gate formerly embedded directly in
    autoresearch_loop. ``rubric_mode`` is the primary scoring discipline;
    optional ``rubric_modes`` remain compositional feature profiles handled
    by ``apply_rubric_mode_defaults``.
    """

    mode = str(rubric_data.get("rubric_mode", "") or "").strip().lower()
    if not mode:
        return RubricModeContractResult(
            ok=True,
            mode="",
            message="",
        )
    if mode == "newton":
        if not _has_generative_yield_dimension(rubric_data):
            return RubricModeContractResult(
                ok=False,
                mode=mode,
                message=(
                    "GP-133 R4 GATE FAIL: rubric declares rubric_mode='newton' but does NOT "
                    "include a dimension whose name contains 'Generative Yield' with weight "
                    ">= 15%. Newton-mode is meaningless without the dimension that enforces "
                    "it. Either add the Generative Yield dimension (see docs/concepts/"
                    "rubric_specification.md § 18) or downgrade the rubric to "
                    "rubric_mode='kepler'. Refusing to launch."
                ),
            )
        return RubricModeContractResult(
            ok=True,
            mode=mode,
            message=(
                "🧭 Newton-mode rubric detected (rubric_mode='newton'). Generative Yield "
                "dimension present. Judge will penalize proposals predicting no secondary "
                "observable beyond the primary fitting target."
            ),
        )
    if mode == "kepler":
        return RubricModeContractResult(
            ok=True,
            mode=mode,
            message="📐 Kepler-mode rubric (descriptive-fit-only). Generative Yield not enforced.",
        )
    if mode == "calibration":
        return RubricModeContractResult(
            ok=True,
            mode=mode,
            message="🔧 Calibration-mode rubric (instrument-characterization). Discovery claims suppressed.",
        )
    return RubricModeContractResult(
        ok=False,
        mode=mode,
        message=(
            f"GP-133 R4 GATE FAIL: rubric_mode={mode!r} is not a recognized value. "
            f"Valid: 'newton', 'kepler', 'calibration'. Refusing to launch."
        ),
    )
