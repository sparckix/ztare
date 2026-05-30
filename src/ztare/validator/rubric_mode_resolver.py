"""Rubric mode → flag resolution.

Single entry point: `apply_rubric_mode_defaults(rubric_data)`. Called once
at rubric-load time in autoresearch_loop. Reads `rubric_data["rubric_mode"]`
and fills in mode-implied flag defaults WITHOUT overwriting explicit
operator-set values.

Why this module exists
----------------------
Rubric modes (`newton`, `kepler`, `factory`, and now `invariant_search`)
are operator-facing labels for clusters of related apparatus toggles.
Without a resolver, every consumer of `enable_lagrangian_derivation` /
`enable_buckingham_pi_gate` / `noether_variance_weight` has to read
`rubric_mode` and back-fill defaults — that is the spaghetti pattern
flagged in the GP-153/GP-167 architecture audit. This file owns the
mapping and runs ONCE; downstream code reads only the flags.

Modes
-----
- `invariant_search` (GP-180/GP-181, 2026-04-28): the action-principle
  pivot. Activates Lagrangian derivation, Buckingham π gate (soft),
  Noether variance loss, and DAG steering. Operator may override any
  individual flag in the rubric — explicit settings win.

Operator override rule
----------------------
If `rubric_data` already has a key `K` set to a non-None value, this
resolver will NOT overwrite it. Modes apply defaults, not mandates.
This is the behavior every existing rubric flag uses (anchor_lambda,
k_law_max, etc.) and keeps the resolver from surprising operators who
set a flag explicitly.
"""
from __future__ import annotations

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
        else:
            parts.append(f"{m!r} (no defaults registered)")
    return "rubric_modes: " + " ; ".join(parts)
