"""GP-157 v5.0 Layer 3 — declarative gate manifest.

Per Gemini Pro architectural review (2026-04-25): the iatrogenic-free
fix for the gp160-class intent/mechanism translation gap is to remove
operator-authored imperative gate code (`gate_harness.py`) entirely and
replace it with a declarative gate manifest in the rubric. The Cage
dispatcher reads the manifest and dynamically instantiates pre-verified,
unit-tested gate classes.

This eliminates:
  - "operator copy-pastes gate_harness.py and updates the comment but not
    the gate" — the gp160-class intent-mechanism mismatch.
  - LLM-based docstring-vs-AST 'semantic alignment' meta-gates (Gemini
    flagged: hallucinatory, non-deterministic, footgun).
  - Per-substrate boilerplate drift across 80+ projects.

Rubric declares `evaluative_gates: [{type: GateType, target_variable: str,
parameters: {...}}, ...]`. Each gate type is a closed-set enum with
strict-typed parameters. Schema validation rejects malformed declarations
at seal time. The mechanism IS the type — operator cannot declare
BOUNDS_CHECK and execute MRE.

This module ships the foundation:
  - `GateType` enum (10 unanimous-WIRE gates triaged earlier)
  - `EvaluativeGateSpec` frozen dataclass
  - `GATE_REGISTRY: dict[GateType, GateImpl]` with stubs + 3 reference impls
  - Per-gate parameter schemas

Wire-in (separate ship): the Cage dispatcher reads
`rubric_data["evaluative_gates"]`, instantiates each spec, runs against
the FrozenFittedModel from Phase 1. `gate_harness.py` files are deprecated
in favor of this declarative path.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping, Optional, Protocol, Sequence


class GateType(Enum):
    """Closed enumeration of evaluative gates available to substrates.

    Linux-syscall discipline: monotonic numbering, never renumbered.
    Adding a new gate type = appending an enum value + registering an
    impl. Removing/renaming requires DECISION_LOG entry + substrate
    migration.

    Per panel triage (2026-04-25), 10 unanimous-WIRE gates:
    """

    BOUNDS_CHECK = 1
    """Predicted y must lie in [min_val, max_val] at given probe points.
    Noise-immune: only checks model output, never noisy data. Used by
    asymptotic-bound substrates (gp160 family). Required parameters:
    min_val (float), max_val (float), probe_points (list[float])."""

    HOLDOUT_MRE = 2
    """Mean relative error on a held-out subset must be below threshold.
    The standard test for fit quality. Required parameters: threshold
    (float)."""

    EXTRAPOLATION_MRE = 3
    """MRE on data points beyond the visible-set range. Catches forms
    that fit visible but blow up at the tail. Caveat: noise dominates
    at large d for low-signal-amplitude forms — prefer BOUNDS_CHECK
    for asymptotic-bound substrates. Required parameters: threshold,
    far_tail_min_d (float)."""

    ASYMPTOTIC_DISCIPLINE = 4
    """Predicted y must converge to a declared limit as d → ∞ (or → 0).
    Required parameters: limit_value (float), limit_direction
    ('+inf' | '-inf' | '0+' | '0-'), tolerance (float)."""

    MONOTONICITY = 5
    """Predicted y must be monotone in a specified independent variable
    over a probe range. Required parameters: variable (str), direction
    ('increasing' | 'decreasing'), probe_range (tuple[float, float])."""

    POSITIVITY = 6
    """Predicted y must be > 0 (or >= 0) over a probe range.
    Required parameters: strict (bool), probe_range (tuple[float, float])."""

    PARAMETER_COUNT = 7
    """K_law (free parameter count) must be ≤ K_max. Enforces algorithmic
    parsimony / Solomonoff-MDL. Required parameters: k_max (int)."""

    ANTI_RETRIEVAL = 8
    """Predicted y at given probe points must NOT match a list of known
    literature values within tolerance. Catches the LLM 'discovering'
    constants by retrieval rather than fitting. Required parameters:
    probe_points (list[float]), forbidden_values (list[float]),
    tolerance (float)."""

    FRAME_INVARIANCE = 9
    """Predicted y must be invariant under a declared coordinate
    transform (e.g., log(x) → log(x) + c). Required parameters:
    transform (str), tolerance (float). Used by GP-152 framer-class
    substrates."""

    DIMENSIONAL_CONSISTENCY = 10
    """Predicted y's units (declared via Pint or symbolic) must match
    the substrate's target units. Required parameters: target_units
    (str). Used by physics-class substrates."""


@dataclass(frozen=True)
class EvaluativeGateSpec:
    """Frozen specification for one evaluative gate.

    Substrate's rubric declares a list of these. The Cage dispatcher
    reads, validates parameters against the per-type schema, instantiates
    pre-verified gate classes, runs against the FrozenFittedModel from
    Phase 1.
    """

    type: GateType
    """One of GateType — drives parameter validation + dispatch."""

    target_variable: str = "y"
    """The model output column this gate evaluates. Default 'y'."""

    parameters: Mapping[str, Any] = field(default_factory=dict)
    """Strict-typed kwargs per gate type. Validated against the per-type
    schema in PARAMETER_SCHEMAS."""

    binding: bool = True
    """When True, gate failure causes hard-gate revert. When False,
    gate is advisory-only (computed + reported, no revert). Default True
    matches existing behavior; set False for diagnostics."""

    docstring: str = ""
    """Human-readable description for evidence-template rendering."""


# ── Per-type parameter schemas ────────────────────────────────────────────
# Each entry: required key → (type, optional human description).
# Validated at substrate-seal time. Strict — no extra keys, no missing.

PARAMETER_SCHEMAS: dict[GateType, dict[str, type]] = {
    GateType.BOUNDS_CHECK: {
        "min_val": float,
        "max_val": float,
        "probe_points": list,
    },
    GateType.HOLDOUT_MRE: {
        "threshold": float,
    },
    GateType.EXTRAPOLATION_MRE: {
        "threshold": float,
        "far_tail_min_d": float,
    },
    GateType.ASYMPTOTIC_DISCIPLINE: {
        "limit_value": float,
        "limit_direction": str,
        "tolerance": float,
    },
    GateType.MONOTONICITY: {
        "variable": str,
        "direction": str,
        "probe_range": (list, tuple),  # 2-tuple or 2-list
    },
    GateType.POSITIVITY: {
        "strict": bool,
        "probe_range": (list, tuple),
    },
    GateType.PARAMETER_COUNT: {
        "k_max": int,
    },
    GateType.ANTI_RETRIEVAL: {
        "probe_points": list,
        "forbidden_values": list,
        "tolerance": float,
    },
    GateType.FRAME_INVARIANCE: {
        "transform": str,
        "tolerance": float,
    },
    GateType.DIMENSIONAL_CONSISTENCY: {
        "target_units": str,
    },
}


class GateContractError(Exception):
    """Raised when an evaluative gate spec is malformed."""

    def __init__(self, code: str, gate_type: Optional[GateType] = None, detail: str = "") -> None:
        self.code = code
        self.gate_type = gate_type
        msg = f"GateContractError[{code}]"
        if gate_type:
            msg += f" type={gate_type.name}"
        if detail:
            msg += f": {detail}"
        super().__init__(msg)


GATE_ERROR_CODES: frozenset[str] = frozenset({
    "UNKNOWN_GATE_TYPE",
    "MISSING_PARAMETER",
    "WRONG_PARAMETER_TYPE",
    "EXTRA_PARAMETER",
    "GATE_TYPE_NOT_REGISTERED",
})


def validate_gate_spec(spec_dict: Mapping[str, Any]) -> EvaluativeGateSpec:
    """Parse + validate a gate spec dict (from rubric.json) into a
    typed EvaluativeGateSpec. Raises GateContractError on malformation.

    Strict: every required parameter present, no extras, types match.
    """
    type_name = (spec_dict.get("type") or "").strip()
    try:
        gate_type = GateType[type_name]
    except KeyError:
        raise GateContractError("UNKNOWN_GATE_TYPE", detail=f"got {type_name!r}, expected one of {[t.name for t in GateType]}")

    parameters = dict(spec_dict.get("parameters") or {})
    schema = PARAMETER_SCHEMAS.get(gate_type)
    if schema is None:
        raise GateContractError("GATE_TYPE_NOT_REGISTERED", gate_type=gate_type)

    for key, expected_type in schema.items():
        if key not in parameters:
            raise GateContractError(
                "MISSING_PARAMETER",
                gate_type=gate_type,
                detail=f"missing key {key!r} (expected type {expected_type})",
            )
        value = parameters[key]
        if isinstance(expected_type, tuple):
            if not isinstance(value, expected_type):
                raise GateContractError(
                    "WRONG_PARAMETER_TYPE",
                    gate_type=gate_type,
                    detail=f"key {key!r} got {type(value).__name__}, expected one of {[t.__name__ for t in expected_type]}",
                )
        elif not isinstance(value, expected_type):
            raise GateContractError(
                "WRONG_PARAMETER_TYPE",
                gate_type=gate_type,
                detail=f"key {key!r} got {type(value).__name__}, expected {expected_type.__name__}",
            )

    extras = set(parameters.keys()) - set(schema.keys())
    if extras:
        raise GateContractError(
            "EXTRA_PARAMETER",
            gate_type=gate_type,
            detail=f"unexpected keys {sorted(extras)}",
        )

    return EvaluativeGateSpec(
        type=gate_type,
        target_variable=spec_dict.get("target_variable", "y"),
        parameters=dict(parameters),
        binding=bool(spec_dict.get("binding", True)),
        docstring=spec_dict.get("docstring", ""),
    )


# ── Gate implementations ─────────────────────────────────────────────────
# Each impl: GateContext → dict[str, Any] result. Pre-verified, unit-tested.


class GateContext(Protocol):
    """The minimal view of the FrozenFittedModel + visible/holdout/probe
    data that gate impls need. Constructed by the Cage dispatcher."""

    @property
    def I_model(self) -> Callable[..., float]: ...

    @property
    def visible_rows(self) -> Sequence[tuple]: ...

    @property
    def holdout_rows(self) -> Sequence[tuple]: ...


def _eval_bounds_check(ctx: GateContext, spec: EvaluativeGateSpec) -> dict:
    p = spec.parameters
    min_val = float(p["min_val"])
    max_val = float(p["max_val"])
    probes = list(p["probe_points"])
    violations = []
    for d in probes:
        try:
            y = float(ctx.I_model(d))
        except Exception as exc:
            violations.append({"d": d, "y": None, "violation": f"{type(exc).__name__}: {exc}"})
            continue
        if math.isnan(y) or math.isinf(y):
            violations.append({"d": d, "y": y, "violation": "NaN/Inf"})
        elif y < min_val or y > max_val:
            violations.append({"d": d, "y": y, "violation": f"out of [{min_val}, {max_val}]"})
    return {
        "type": "BOUNDS_CHECK",
        "probe_points": probes,
        "bounds": (min_val, max_val),
        "violations": violations,
        "passed": len(violations) == 0,
    }


def _eval_holdout_mre(ctx: GateContext, spec: EvaluativeGateSpec) -> dict:
    threshold = float(spec.parameters["threshold"])
    errors = []
    for row in ctx.holdout_rows:
        if not isinstance(row, (tuple, list)) or len(row) < 2:
            continue
        # Expect (id, d, y) or (d, y) tuple shapes
        if len(row) >= 3 and isinstance(row[0], int) and isinstance(row[1], (int, float)):
            d, y_true = row[1], row[2]
        elif len(row) == 2:
            d, y_true = row[0], row[1]
        else:
            continue
        try:
            y_pred = float(ctx.I_model(d))
        except Exception:
            errors.append(1.0)
            continue
        if math.isnan(y_pred) or math.isinf(y_pred):
            errors.append(1.0)
        elif y_true == 0:
            errors.append(abs(y_pred))
        else:
            errors.append(abs(y_pred - y_true) / abs(y_true))
    n = len(errors) or 1
    mre = sum(errors) / n
    return {
        "type": "HOLDOUT_MRE",
        "n": len(errors),
        "mean_relative_error": mre,
        "threshold": threshold,
        "passed": mre < threshold,
    }


def _eval_anti_retrieval(ctx: GateContext, spec: EvaluativeGateSpec) -> dict:
    p = spec.parameters
    probes = list(p["probe_points"])
    forbidden = list(p["forbidden_values"])
    tol = float(p["tolerance"])
    breaches = []
    for d in probes:
        try:
            y = float(ctx.I_model(d))
        except Exception:
            continue
        for forbidden_val in forbidden:
            if abs(y - forbidden_val) < tol:
                breaches.append({"d": d, "y": y, "matched_forbidden": forbidden_val})
                break
    return {
        "type": "ANTI_RETRIEVAL",
        "probe_points": probes,
        "forbidden_values": forbidden,
        "breaches": breaches,
        "passed": len(breaches) == 0,
    }


# Registry — only 3 impls shipped in this commit (BOUNDS_CHECK,
# HOLDOUT_MRE, ANTI_RETRIEVAL). Other 7 gate types validated via
# spec but raise GATE_TYPE_NOT_REGISTERED if invoked. Add impls
# incrementally as substrates need them.

GateImpl = Callable[[GateContext, EvaluativeGateSpec], dict]

GATE_REGISTRY: dict[GateType, GateImpl] = {
    GateType.BOUNDS_CHECK: _eval_bounds_check,
    GateType.HOLDOUT_MRE: _eval_holdout_mre,
    GateType.ANTI_RETRIEVAL: _eval_anti_retrieval,
}


def evaluate_gate(ctx: GateContext, spec: EvaluativeGateSpec) -> dict:
    """Dispatch one validated EvaluativeGateSpec through the registry."""
    impl = GATE_REGISTRY.get(spec.type)
    if impl is None:
        raise GateContractError(
            "GATE_TYPE_NOT_REGISTERED",
            gate_type=spec.type,
            detail=f"no impl registered yet (validated spec only)",
        )
    return impl(ctx, spec)


def list_gate_types() -> tuple[str, ...]:
    return tuple(t.name for t in GateType)


def list_registered_gate_types() -> tuple[str, ...]:
    """Subset of GateType that has a working impl shipped."""
    return tuple(t.name for t in GATE_REGISTRY)
