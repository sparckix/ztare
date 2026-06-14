"""GP-078 grammar-guided symbolic regression synthesis.

When the primitive library exhausts (Feynman Wall), this module bootstraps
new primitives by composing existing ones under a strict AST grammar.

Three deliverables:
  1. FailurePackager — reads structural_memory after exhaustion, emits FailurePackage
  2. LibraryCompiler — compiles composition commands into new FitDeclarations
  3. CompositionMutator — LLM-guided or PySR-guided composition search

Constraints (GP-078 spec):
  - Zero-trust parity with primary loop (holdout gate unchanged)
  - No raw data to LLM — composition mutator sees FailurePackage, not (n, a(n))
  - Deterministic compilation — Library Compiler has no LLM in the loop
  - Existing AST whitelist governs (fit_primitive._validate_expression)
  - CONVOLVE = Dirichlet convolution
  - DERIVE = forward difference A(n+1) - A(n)
"""

from __future__ import annotations

import json
import logging
import math
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from src.ztare.fit.fit_primitive import (
    FitDeclaration,
    FitSuccess,
    _validate_expression,
    _build_model_callable,
    _ALLOWED_MATH_ATTRS,
    _ALLOWED_DIRECT_CALLS,
)
from src.ztare.composition.structural_memory import (
    StructuralFamilySignature,
    build_structural_family_signature,
    load_structural_memory,
)


# ---------------------------------------------------------------------------
# Wall-exit codes
# ---------------------------------------------------------------------------


class WallExitCode(str, Enum):
    WALL_DEPTH_INSUFFICIENT = "WALL_DEPTH_INSUFFICIENT"
    WALL_LIBRARY_INSUFFICIENT = "WALL_LIBRARY_INSUFFICIENT"
    WALL_BUDGET_EXHAUSTED = "WALL_BUDGET_EXHAUSTED"


# ---------------------------------------------------------------------------
# Composition commands
# ---------------------------------------------------------------------------


class CompositionCommand(str, Enum):
    NEST = "NEST"
    CONVOLVE = "CONVOLVE"
    DERIVE = "DERIVE"
    COMPOSE = "COMPOSE"
    BIVARIATE_SCALE = "BIVARIATE_SCALE"  # x2 * g(x1) — domain-agnostic linear scaling by a second variable


@dataclass(frozen=True)
class CompositionRequest:
    command: CompositionCommand
    operand_a: str  # expression string of primitive A
    operand_b: str | None = None  # expression string of primitive B (None for DERIVE)
    compose_op: str | None = None  # "+", "*", "/" for COMPOSE
    motivating_statistic: str = ""
    independent_vars: list[str] = field(default_factory=lambda: ["n"])
    parameter_names_a: list[str] = field(default_factory=list)
    parameter_names_b: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Failure Package
# ---------------------------------------------------------------------------


@dataclass
class FailurePackage:
    apex_family: StructuralFamilySignature
    apex_fit: dict[str, Any]
    residual_delta: list[tuple[float, ...]]
    residual_statistics: dict[str, Any]
    exhausted_families: list[str]
    holdout_rejection_summary: dict[str, Any]
    visible_slice_indices: list[Any]  # int for discrete, float for continuous substrates


_EPSILON = 1e-10
_MIN_MULTIPLICATIVITY_PAIRS = 5


def _compute_residual_statistics(
    residual_delta: list[tuple[float, ...]],
) -> dict[str, Any]:
    """Compute summary statistics from (index, error) pairs."""
    if not residual_delta:
        return {
            "mean": 0.0,
            "std": 0.0,
            "autocorrelation_lag1": 0.0,
            "sign_change_count": 0,
            "multiplicativity_ratio": None,
            "n_multiplicativity_pairs": 0,
            "sample_n": 0,
        }

    # Last element is the error; first element is the primary index (for discrete substrates).
    # For continuous substrates, index is a float; multiplicativity stats are skipped.
    indices = [p[0] for p in residual_delta]
    errors = [p[-1] for p in residual_delta]
    n = len(errors)

    mean_err = sum(errors) / n
    var_err = sum((e - mean_err) ** 2 for e in errors) / n if n > 1 else 0.0
    std_err = math.sqrt(var_err)

    sign_changes = sum(
        1 for i in range(1, n) if errors[i] * errors[i - 1] < 0
    )

    # Lag-1 autocorrelation
    acorr = 0.0
    if n > 2 and var_err > _EPSILON:
        acorr = sum(
            (errors[i] - mean_err) * (errors[i - 1] - mean_err)
            for i in range(1, n)
        ) / ((n - 1) * var_err)

    # Multiplicativity ratio for CONVOLVE-Dirichlet detection (discrete substrates only).
    # For continuous substrates, indices are floats — integer product arithmetic is meaningless.
    mult_ratios: list[float] = []
    try:
        int_indices = [int(p) for p in indices]
        if all(p == ip for p, ip in zip(indices, int_indices)):
            # All indices are integers — run multiplicativity probe
            index_set: set[int] = set(int_indices)
            error_by_index: dict[int, float] = dict(zip(int_indices, errors))
            for p in int_indices:
                for q in int_indices:
                    if p < 2 or q < 2 or p == q:
                        continue
                    pq = p * q
                    if pq not in index_set:
                        continue
                    denom = abs(error_by_index[p]) * abs(error_by_index[q])
                    if denom < _EPSILON:
                        continue
                    mult_ratios.append(abs(error_by_index[pq]) / denom)
    except (TypeError, ValueError):
        pass  # continuous substrate — skip multiplicativity

    mult_ratio = (
        sum(mult_ratios) / len(mult_ratios) if len(mult_ratios) >= _MIN_MULTIPLICATIVITY_PAIRS else None
    )

    return {
        "mean": mean_err,
        "std": std_err,
        "autocorrelation_lag1": acorr,
        "sign_change_count": sign_changes,
        "multiplicativity_ratio": mult_ratio,
        "n_multiplicativity_pairs": len(mult_ratios),
        "sample_n": n,
    }


def _compute_residual_delta_from_fit(
    fit_result: FitSuccess,
    declaration: FitDeclaration,
    visible_evidence: list[tuple[float, ...]],
) -> list[tuple[float, ...]]:
    """Compute pointwise (inputs..., error) residuals from a FitSuccess.

    Supports 1D (input, error) and nD (x1, x2, ..., error) evidence.
    Uses _build_model_callable to evaluate the fitted expression at each
    visible evidence point.
    """
    import numpy as np

    try:
        model_fn = _build_model_callable(declaration)
    except (ValueError, SyntaxError):
        return []

    # Support n-dimensional input: all columns except last are inputs, last is GT
    n_vars = len(visible_evidence[0]) - 1
    ground_truth = np.array([v[-1] for v in visible_evidence])
    params = [fit_result.fitted_params.get(p, 0.0) for p in declaration.parameter_names]

    try:
        if n_vars == 1:
            inputs = np.array([v[0] for v in visible_evidence])
            predicted = model_fn(inputs, *params)
        else:
            # Multivariate: pass columns as separate arrays (curve_fit convention)
            inputs = np.array([[v[i] for v in visible_evidence] for i in range(n_vars)])
            predicted = model_fn(inputs, *params)
    except Exception:
        return []

    residuals: list[tuple[float, ...]] = []
    for i, row in enumerate(visible_evidence):
        pred = predicted[i]
        if math.isfinite(pred):
            residuals.append((*row[:-1], row[-1] - pred))

    return residuals


def build_failure_package(
    workspace_dir: Path,
    visible_evidence: list[tuple[float, ...]],
    holdout_rejection_summary: dict[str, Any],
    *,
    holdout_indices: set[int] | None = None,
    apex_fit_result: FitSuccess | None = None,
    apex_declaration: FitDeclaration | None = None,
) -> FailurePackage | None:
    """Build a FailurePackage from structural memory after library exhaustion.

    Args:
        workspace_dir: project workspace containing structural_memory.json
        visible_evidence: (input, ground_truth) pairs from visible slice
        holdout_rejection_summary: gate metrics from the apex loser's holdout test
        holdout_indices: indices in the holdout region (for explicit exclusion check)
        apex_fit_result: the FitSuccess from the apex loser's best visible-slice
            fit. Required for pointwise residual computation. If None, residual_delta
            will be empty and residual statistics will be zero-valued.
        apex_declaration: the FitDeclaration for the apex loser. Required alongside
            apex_fit_result for pointwise residual computation.

    Returns:
        FailurePackage if structural memory has families, None if empty.
    """
    memory = load_structural_memory(workspace_dir)
    families = memory.get("families", [])
    if not families:
        return None

    # Find apex loser: smallest max_abs_residual among holdout failures
    apex: dict[str, Any] | None = None
    apex_residual = float("inf")
    for fam in families:
        mar = fam.get("best_visible_max_abs_residual")
        if mar is None:
            continue
        mar_f = float(mar)
        if mar_f < apex_residual:
            apex_residual = mar_f
            apex = fam

    if apex is None:
        return None

    apex_sig = StructuralFamilySignature(
        fingerprint=str(apex.get("fingerprint", "")),
        family_label=str(apex.get("family_label", "")),
    )

    # Compute residual delta using the apex loser's expression
    # For discrete substrates, v[0] is an integer index; for continuous, it's a float.
    # The holdout-leak check only applies to discrete (integer) substrates.
    visible_indices = [v[0] for v in visible_evidence]

    # Verify no holdout indices leak into visible slice (discrete substrates only)
    if holdout_indices:
        try:
            leaked = {int(v) for v in visible_indices} & holdout_indices
        except (TypeError, ValueError):
            leaked = set()  # continuous substrate — no integer index to check
        if leaked:
            raise ValueError(
                f"FailurePackage contamination: visible_slice_indices overlap "
                f"with holdout_indices at {leaked}"
            )

    # Degenerate case: zero-residual apex loser
    if apex_residual < _EPSILON:
        return FailurePackage(
            apex_family=apex_sig,
            apex_fit={
                "max_abs_residual": apex_residual,
                "expression": apex.get("example_expression", ""),
            },
            residual_delta=[],
            residual_statistics={
                "degenerate": True,
                "cause": "overfit_visible_slice",
            },
            exhausted_families=[
                str(f.get("fingerprint", "")) for f in families
            ],
            holdout_rejection_summary=holdout_rejection_summary,
            visible_slice_indices=visible_indices,
        )

    # Build residual delta from the apex loser's fitted model
    residual_delta: list[tuple[float, ...]] = []
    if apex_fit_result is not None and apex_declaration is not None:
        residual_delta = _compute_residual_delta_from_fit(
            apex_fit_result, apex_declaration, visible_evidence
        )

    stats = _compute_residual_statistics(residual_delta)

    return FailurePackage(
        apex_family=apex_sig,
        apex_fit={
            "max_abs_residual": apex_residual,
            "expression": apex.get("example_expression", ""),
            "family_label": apex.get("family_label", ""),
            "independent_vars": apex.get("independent_vars", ["n"]),
        },
        residual_delta=residual_delta,
        residual_statistics=stats,
        exhausted_families=[
            str(f.get("fingerprint", "")) for f in families
        ],
        holdout_rejection_summary=holdout_rejection_summary,
        visible_slice_indices=visible_indices,
    )


# ---------------------------------------------------------------------------
# Library Compiler
# ---------------------------------------------------------------------------


def compile_composition(request: CompositionRequest) -> FitDeclaration | str:
    """Compile a CompositionRequest into a FitDeclaration.

    Returns FitDeclaration on success, or an error string on failure.
    """
    cmd = request.command
    a_expr = request.operand_a
    b_expr = request.operand_b
    ind_vars = request.independent_vars

    # Merge parameter names with prefixed namespaces to avoid collisions
    params_a = [f"a_{p}" for p in request.parameter_names_a]
    params_b = [f"b_{p}" for p in request.parameter_names_b]

    def _sub_params(expr: str, original: list[str], prefixed: list[str]) -> str:
        """Replace parameter names in expression with prefixed versions."""
        result = expr
        for orig, pref in zip(original, prefixed):
            result = re.sub(rf'\b{re.escape(orig)}\b', pref, result)
        return result

    a_expr_prefixed = _sub_params(a_expr, request.parameter_names_a, params_a)
    b_expr_prefixed = _sub_params(b_expr or "", request.parameter_names_b, params_b) if b_expr else ""

    all_params = params_a + params_b

    if cmd == CompositionCommand.NEST:
        if not b_expr:
            return "NEST requires operand_b"
        # A(B(x)) — substitute B's expression for x in A
        var = ind_vars[0] if ind_vars else "n"
        composed = re.sub(rf'\b{re.escape(var)}\b', f'({b_expr_prefixed})', a_expr_prefixed)
        expression = composed

    elif cmd == CompositionCommand.DERIVE:
        # Forward difference: A(n+1) - A(n)
        var = ind_vars[0] if ind_vars else "n"
        a_shifted = re.sub(rf'\b{re.escape(var)}\b', f'({var} + 1)', a_expr_prefixed)
        expression = f"({a_shifted}) - ({a_expr_prefixed})"
        all_params = params_a  # No operand_b

    elif cmd == CompositionCommand.COMPOSE:
        if not b_expr:
            return "COMPOSE requires operand_b"
        op = request.compose_op
        if op not in ("+", "*", "/"):
            return f"COMPOSE op must be +, *, or /; got {op!r}"
        expression = f"({a_expr_prefixed}) {op} ({b_expr_prefixed})"

    elif cmd == CompositionCommand.CONVOLVE:
        if not b_expr:
            return "CONVOLVE requires operand_b"
        # Dirichlet convolution: sum over divisors d of n: A(d) * B(n/d)
        # This cannot be expressed as a single math expression for curve_fit.
        # It requires a runtime function. For now, return a typed failure.
        return (
            "CONVOLVE (Dirichlet) cannot be compiled to a static expression "
            "for curve_fit. Requires a runtime function wrapper. "
            "Deferred to depth-2 implementation."
        )

    elif cmd == CompositionCommand.BIVARIATE_SCALE:
        # x2 * g(x1): scale a 1D function by a second independent variable.
        # Domain-agnostic — the grammar does not encode what x2 represents.
        # Requires ind_vars to have at least two entries: [primary_var, scale_var].
        if len(ind_vars) < 2:
            return (
                "BIVARIATE_SCALE requires two independent variables [primary_var, scale_var]. "
                f"Got: {ind_vars}"
            )
        scale_var = ind_vars[1]
        expression = f"{scale_var} * ({a_expr_prefixed})"
        all_params = params_a  # No operand_b

    else:
        return f"Unknown composition command: {cmd}"

    # Validate against AST whitelist
    # "math" must be allowed since expressions use math.log, math.sin, etc.
    allowed_names = frozenset(ind_vars + all_params + ["math"])
    try:
        _validate_expression(
            expression,
            allowed_names,
            allowed_math_attrs=_ALLOWED_MATH_ATTRS,
            # Match the default grammar's empty direct-call set.
            # The fitter (_build_model_callable) uses this stricter default.
            allowed_direct_calls=frozenset(),
        )
    except ValueError as exc:
        return f"Composition failed AST validation: {exc}"

    return FitDeclaration(
        expression=expression,
        independent_vars=list(ind_vars),
        parameter_names=all_params,
    )


def register_composed_primitive(
    workspace_dir: Path,
    declaration: FitDeclaration,
    fit_result: FitSuccess,
    composition_request: CompositionRequest,
    iteration_index: int,
) -> dict[str, Any]:
    """Register a composed primitive in structural_memory.json with provenance."""
    from src.ztare.composition.structural_memory import update_structural_memory

    memory = update_structural_memory(
        workspace_dir=workspace_dir,
        declaration=declaration,
        fit_result=fit_result,
        iteration_index=iteration_index,
        diagnostic_classification="composition",
    )

    # Add composition provenance to the family entry
    sig = build_structural_family_signature(declaration)
    families = memory.get("families", [])
    for fam in families:
        if fam.get("fingerprint") == sig.fingerprint:
            fam["composition_provenance"] = {
                "command": composition_request.command.value,
                "operand_a": composition_request.operand_a,
                "operand_b": composition_request.operand_b,
                "compose_op": composition_request.compose_op,
                "motivating_statistic": composition_request.motivating_statistic,
            }
            break

    # Update composition_primitive_count and last_composition_iteration
    count = int(memory.get("composition_primitive_count", 0))
    memory["composition_primitive_count"] = count + 1
    memory["last_composition_iteration"] = iteration_index

    mem_path = workspace_dir / "structural_memory.json"
    mem_path.write_text(json.dumps(memory, indent=2) + "\n", encoding="utf-8")
    return memory


# ---------------------------------------------------------------------------
# Wall-exit assessment
# ---------------------------------------------------------------------------


def assess_wall_exit(
    composition_round_results: list[dict[str, Any]],
    budget_exhausted: bool,
    min_rounds_for_trend: int = 5,
) -> WallExitCode:
    """Determine the wall-exit code from composition round metrics."""
    if len(composition_round_results) < min_rounds_for_trend:
        return WallExitCode.WALL_BUDGET_EXHAUSTED

    # Check for visible-slice fit improvement trend
    visible_residuals = [
        r.get("visible_max_abs_residual", float("inf"))
        for r in composition_round_results
        if r.get("visible_max_abs_residual") is not None
    ]

    if len(visible_residuals) < min_rounds_for_trend:
        return WallExitCode.WALL_BUDGET_EXHAUSTED

    # Simple trend: is the best visible residual in the second half
    # better than the best in the first half?
    mid = len(visible_residuals) // 2
    first_half_best = min(visible_residuals[:mid]) if visible_residuals[:mid] else float("inf")
    second_half_best = min(visible_residuals[mid:]) if visible_residuals[mid:] else float("inf")

    if second_half_best < first_half_best * 0.9:
        return WallExitCode.WALL_DEPTH_INSUFFICIENT

    return WallExitCode.WALL_LIBRARY_INSUFFICIENT


# ---------------------------------------------------------------------------
# Universal Feynman Wall detection (substrate-agnostic)
# ---------------------------------------------------------------------------

# Default: max 50 composition attempts per wall-hit, but exit early on
# wall-exit signal (WALL_LIBRARY_INSUFFICIENT → stop immediately,
# WALL_DEPTH_INSUFFICIENT → keep going, WALL_BUDGET_EXHAUSTED → stop).
COMPOSITION_BUDGET_DEFAULT = 50
# Minimum distinct families in structural_memory before wall can fire.
# Prevents false wall triggers when the LLM has only tried 2-3 families.
WALL_MIN_FAMILIES = 6

# ---------------------------------------------------------------------------
# Deterministic ratio probes — same-family division
# ---------------------------------------------------------------------------
# The LLM composition mutator systematically avoids same-family divisions
# (preferring addition of different families).  Exponential-ratio topologies
# like coth(u) = (exp(u)+exp(-u))/(exp(u)-exp(-u)) are unreachable without
# explicit probing of COMPOSE(X, /, Y) on exponential-family primitives.

_RATIO_PROBE_PAIRS: list[tuple[str, str]] = [
    ("double_exp", "double_exp"),
    ("exp", "exp"),
    ("exp_decay", "exp_decay"),
    ("exp", "exp_decay"),
    ("double_exp", "exp"),
    ("double_exp", "exp_decay"),
    # Hyperbolic ratios: cosh/sinh = coth, sinh/cosh = tanh.
    # Fundamental in statistical mechanics, catenary, special relativity.
    ("cosh", "sinh"),
    ("sinh", "cosh"),
]

# ---------------------------------------------------------------------------
# Depth-2 composition targets
# ---------------------------------------------------------------------------
# After depth-1 (including ratio probes), compose the best depth-1 results
# with selected base primitives.  Cost: top_k × |bases| × |ops|.

_DEPTH2_BASE_TARGETS = ["reciprocal", "linear", "log", "exp_decay", "power"]
_DEPTH2_OPS = ["+", "/"]
_DEPTH2_TOP_K = 5


def detect_feynman_wall(
    workspace_dir: Path,
    stagnation_count: int,
    *,
    min_families: int = WALL_MIN_FAMILIES,
    stagnation_threshold: int = 3,
) -> bool:
    """Universal Feynman Wall detection from structural_memory.

    Returns True if the library is exhausted — meaning structural_memory
    has high family coverage and the loop is stagnating.

    This is substrate-agnostic: works for 1D sequences, 2D ODE fits,
    n-D multivariate data, or any future substrate type.

    Criteria (ALL must be true):
      1. structural_memory has >= min_families distinct families
      2. No family has improved its best_visible_max_abs_residual in the
         last `stagnation_threshold` iterations (staleness check)
      3. The loop's stagnation_count >= stagnation_threshold
    """
    memory = load_structural_memory(workspace_dir)
    families = memory.get("families", [])

    if len(families) < min_families:
        return False

    if stagnation_count < stagnation_threshold:
        return False

    # Check if any family has been improving recently: compare
    # first_seen_iteration vs last_seen_iteration spread.
    # If the most recent family was seen long ago relative to iteration
    # count, the LLM has stopped proposing new structures.
    max_last_seen = max(
        (int(f.get("last_seen_iteration", 0)) for f in families),
        default=0,
    )
    # The iteration index of the most recently updated family.
    # If this is more than stagnation_threshold behind the current
    # iteration, structural exploration has stalled.
    # We can't know the current iteration here, but the caller passes
    # stagnation_count which serves as the proxy.

    # Cooldown guard: if composition already ran, require at least
    # stagnation_threshold iterations of *new* stagnation since the last
    # composition before re-triggering.  This lets the loop try the
    # composed primitives before concluding the wall is still active.
    last_comp_iter = int(memory.get("last_composition_iteration", 0))
    if last_comp_iter > 0:
        # max_last_seen is the most recent iteration any family was
        # observed — proxy for "current iteration".  If fewer than
        # stagnation_threshold iterations have elapsed since last
        # composition, the new primitives haven't been exercised yet.
        if max_last_seen - last_comp_iter < stagnation_threshold:
            return False

    return True


def _run_ratio_probes(
    visible_evidence: list[tuple[float, ...]],
    workspace_dir: Path,
    iteration_index: int,
    var_name: str = "n",
    ind_vars: list[str] | None = None,
    failure_package: FailurePackage | None = None,
) -> list[dict[str, Any]]:
    """Deterministic ratio probes: COMPOSE(X, /, Y) for same-family primitives.

    Fires when the residual statistics suggest a ratio topology:
    bounded magnitude (no divergence) + moderate-to-high autocorrelation
    (smooth residual trend, not noise).  These are the hallmarks of a
    target that saturates with structure — a regime where additive
    compositions systematically fail but self-ratios succeed.

    When no failure package is available, probes fire unconditionally
    (conservative: never skip a cheap deterministic check).
    """
    from src.ztare.fit.fit_primitive import fit_parameters

    if ind_vars is None:
        ind_vars = [var_name]

    # Gate: only fire probes when residual suggests ratio topology.
    # Use RELATIVE residual (max|res| / max|signal|) so the gate is
    # scale-invariant across substrates.
    if failure_package is not None:
        stats = failure_package.residual_statistics
        apex_res = failure_package.apex_fit.get("max_abs_residual", float("inf"))
        autocorr = stats.get("autocorrelation_lag1", 0.0)
        sign_changes = stats.get("sign_change_count", 0)
        visible_n = len(failure_package.visible_slice_indices)
        # Compute signal scale from visible evidence for relative gating
        signal_max = max(
            (abs(row[-1]) for row in visible_evidence), default=1.0
        )
        signal_max = max(signal_max, _EPSILON)  # avoid division by zero
        relative_res = apex_res / signal_max
        # Ratio topology signal: residual is bounded relative to signal
        # (not diverging), smooth (high autocorrelation or few sign changes),
        # and the apex form already has moderate fit (not catastrophic).
        ratio_signal = (
            relative_res < 0.5  # bounded relative to signal scale
            and (autocorr > 0.3 or sign_changes < visible_n * 0.4)
        )
        if not ratio_signal:
            print(
                f"    🧬 Ratio probes: skipped (relative_res={relative_res:.3f}, "
                f"autocorr={autocorr:.3f}, sign_changes={sign_changes}/{visible_n})"
            )
            return []

    primitives_by_label = {label: (expr, params) for label, expr, params in _BASE_PRIMITIVES}
    results: list[dict[str, Any]] = []
    evidence_text = "\n".join(
        "\t".join(str(x) for x in row) for row in visible_evidence
    )

    for label_a, label_b in _RATIO_PROBE_PAIRS:
        if label_a not in primitives_by_label or label_b not in primitives_by_label:
            continue

        expr_a, params_a = primitives_by_label[label_a]
        expr_b, params_b = primitives_by_label[label_b]

        if var_name != "n":
            expr_a = re.sub(r"\bn\b", var_name, expr_a)
            expr_b = re.sub(r"\bn\b", var_name, expr_b)

        request = CompositionRequest(
            command=CompositionCommand.COMPOSE,
            operand_a=expr_a,
            operand_b=expr_b,
            parameter_names_a=params_a,
            parameter_names_b=params_b,
            compose_op="/",
            motivating_statistic="deterministic_ratio_probe",
            independent_vars=ind_vars,
        )

        compiled = compile_composition(request)
        if isinstance(compiled, str):
            continue

        fit_result = fit_parameters(compiled, evidence_text)

        if isinstance(fit_result, FitSuccess):
            print(
                f"    🧬 Ratio probe [{label_a}/{label_b}]: SUCCESS "
                f"max|res|={fit_result.max_abs_residual:.5f} "
                f"expr={compiled.expression[:60]}"
            )
            register_composed_primitive(
                workspace_dir, compiled, fit_result, request, iteration_index,
            )
            results.append({
                "round": f"ratio_probe_{label_a}_{label_b}",
                "status": "fit_success",
                "visible_max_abs_residual": fit_result.max_abs_residual,
                "expression": compiled.expression,
                "parameter_names": compiled.parameter_names,
                "command": "COMPOSE",
                "probe_type": "ratio",
            })
        else:
            print(
                f"    🧬 Ratio probe [{label_a}/{label_b}]: "
                f"{fit_result.failure_class}"
            )
            results.append({
                "round": f"ratio_probe_{label_a}_{label_b}",
                "status": "fit_failure",
                "probe_type": "ratio",
            })

    return results


def _run_depth2_pass(
    depth1_results: list[dict[str, Any]],
    visible_evidence: list[tuple[float, ...]],
    workspace_dir: Path,
    iteration_index: int,
    var_name: str = "n",
    ind_vars: list[str] | None = None,
    top_k: int = _DEPTH2_TOP_K,
) -> list[dict[str, Any]]:
    """Depth-2 composition: compose best depth-1 results with base primitives.

    Takes the top-K depth-1 successes (by visible residual) and tries
    COMPOSE(d1_result, op, base_primitive) for selected bases and operators.
    Cost: K × |bases| × |ops| ≈ 50 compositions.
    """
    from src.ztare.fit.fit_primitive import fit_parameters

    if ind_vars is None:
        ind_vars = [var_name]

    successes = [
        r for r in depth1_results
        if r.get("status") == "fit_success"
        and r.get("expression")
        and r.get("parameter_names")
    ]
    successes.sort(key=lambda r: r.get("visible_max_abs_residual", float("inf")))
    # Ratio probes bypass K-pruning: they are deterministic, cheap, and
    # structurally important.  A ratio probe whose depth-1 residual is large
    # may still be the correct "half" that depth-2 rescues.
    ratio_probes = [r for r in successes if r.get("probe_type") == "ratio"]
    non_probes = [r for r in successes if r.get("probe_type") != "ratio"]
    top_results = non_probes[:top_k]
    for rp in ratio_probes:
        if rp not in top_results:
            top_results.append(rp)

    if not top_results:
        return []

    primitives_by_label = {
        label: (expr, params) for label, expr, params in _BASE_PRIMITIVES
    }
    results: list[dict[str, Any]] = []
    evidence_text = "\n".join(
        "\t".join(str(x) for x in row) for row in visible_evidence
    )

    for d1_idx, d1 in enumerate(top_results):
        d1_expr = d1["expression"]
        d1_params = d1["parameter_names"]

        for base_label in _DEPTH2_BASE_TARGETS:
            if base_label not in primitives_by_label:
                continue
            base_expr_raw, base_params_raw = primitives_by_label[base_label]

            base_expr = base_expr_raw
            if var_name != "n":
                base_expr = re.sub(r"\bn\b", var_name, base_expr)

            # Prefix base params with "d2_" to avoid collision with depth-1 params
            d2_params = [f"d2_{p}" for p in base_params_raw]
            d2_expr = base_expr
            for orig, pref in zip(base_params_raw, d2_params):
                d2_expr = re.sub(rf"\b{re.escape(orig)}\b", pref, d2_expr)

            for op in _DEPTH2_OPS:
                composed = f"({d1_expr}) {op} ({d2_expr})"
                all_params = list(d1_params) + d2_params

                allowed = frozenset(ind_vars + all_params + ["math"])
                try:
                    _validate_expression(
                        composed,
                        allowed,
                        allowed_math_attrs=_ALLOWED_MATH_ATTRS,
                        allowed_direct_calls=frozenset(),
                    )
                except ValueError:
                    continue

                decl = FitDeclaration(
                    expression=composed,
                    independent_vars=list(ind_vars),
                    parameter_names=all_params,
                )
                fit_result = fit_parameters(decl, evidence_text)

                tag = f"d1_{d1_idx}/{base_label}/{op}"
                if isinstance(fit_result, FitSuccess):
                    print(
                        f"    🧬 Depth-2 [{tag}]: SUCCESS "
                        f"max|res|={fit_result.max_abs_residual:.5f} "
                        f"expr={composed[:70]}"
                    )
                    prov = CompositionRequest(
                        command=CompositionCommand.COMPOSE,
                        operand_a=d1_expr,
                        operand_b=d2_expr,
                        parameter_names_a=d1_params,
                        parameter_names_b=d2_params,
                        compose_op=op,
                        motivating_statistic="depth2_systematic",
                        independent_vars=ind_vars,
                    )
                    register_composed_primitive(
                        workspace_dir, decl, fit_result, prov, iteration_index,
                    )
                    results.append({
                        "round": f"depth2_{tag}",
                        "status": "fit_success",
                        "visible_max_abs_residual": fit_result.max_abs_residual,
                        "expression": composed,
                        "parameter_names": all_params,
                        "command": "COMPOSE",
                        "depth": 2,
                    })
                else:
                    results.append({
                        "round": f"depth2_{tag}",
                        "status": "fit_failure",
                        "depth": 2,
                    })

    return results


def run_composition_loop(
    workspace_dir: Path,
    visible_evidence: list[tuple[float, ...]],
    *,
    holdout_rejection_summary: dict[str, Any] | None = None,
    holdout_indices: set[int] | None = None,
    apex_fit_result: FitSuccess | None = None,
    apex_declaration: FitDeclaration | None = None,
    model_id: str = "gemini-2.5-flash",
    budget: int = COMPOSITION_BUDGET_DEFAULT,
    iteration_index: int = 0,
    runtime: Any | None = None,
    var_name: str = "n",
    ind_vars: list[str] | None = None,
) -> dict[str, Any]:
    """Run the full composition loop: FailurePackage → Mutator → Compile → Fit → Gate.

    Returns a summary dict with wall_exit_code and composition results.
    Exits early on WALL_LIBRARY_INSUFFICIENT (no point continuing).
    """
    from src.ztare.fit.fit_primitive import fit_parameters

    failure_package = build_failure_package(
        workspace_dir,
        visible_evidence,
        holdout_rejection_summary or {},
        holdout_indices=holdout_indices,
        apex_fit_result=apex_fit_result,
        apex_declaration=apex_declaration,
    )

    if failure_package is None:
        _logger.info("Symbolic-regression synthesizer: no families in structural memory, skipping")
        return {"wall_exit_code": "NO_FAMILIES", "rounds": 0}

    # Degenerate case: zero-residual apex loser
    if failure_package.residual_statistics.get("degenerate"):
        _logger.info("Symbolic-regression synthesizer: degenerate apex loser (overfit visible slice)")
        return {
            "wall_exit_code": WallExitCode.WALL_LIBRARY_INSUFFICIENT.value,
            "rounds": 0,
            "cause": "overfit_visible_slice",
        }

    round_results: list[dict[str, Any]] = []
    composition_successes = 0

    for round_idx in range(budget):
        print(f"    🧬 Composition round {round_idx + 1}/{budget}")

        # Step 1: Run composition mutator
        mutator_result = run_composition_mutator(
            failure_package,
            model_id=model_id,
            runtime=runtime,
            var_name=var_name,
            ind_vars=ind_vars,
        )

        if mutator_result.parse_error is not None:
            print(f"    🧬 Mutator error: {mutator_result.parse_error[:80]}")
            round_results.append({
                "round": round_idx + 1,
                "status": "mutator_error",
                "error": mutator_result.parse_error,
            })
            continue

        request = mutator_result.request
        if request is None:
            continue

        # Step 2: Compile the composition
        compiled = compile_composition(request)
        if isinstance(compiled, str):
            print(f"    🧬 Compile error: {compiled[:80]}")
            round_results.append({
                "round": round_idx + 1,
                "status": "compile_error",
                "error": compiled,
            })
            continue

        # Step 3: Fit the composed primitive on visible evidence
        # Rows are tab-separated: x1 [x2 ...] z — supports 1D and nD substrates.
        evidence_text_lines = []
        for row in visible_evidence:
            evidence_text_lines.append("\t".join(str(x) for x in row))
        evidence_text_for_fit = "\n".join(evidence_text_lines)

        fit_result = fit_parameters(compiled, evidence_text_for_fit)

        if isinstance(fit_result, FitSuccess):
            print(
                f"    🧬 Fit SUCCESS: max|res|={fit_result.max_abs_residual:.5f} "
                f"expr={compiled.expression[:60]}"
            )
            # Step 4: Register in structural memory with provenance
            register_composed_primitive(
                workspace_dir,
                compiled,
                fit_result,
                request,
                iteration_index,
            )
            composition_successes += 1
            round_results.append({
                "round": round_idx + 1,
                "status": "fit_success",
                "visible_max_abs_residual": fit_result.max_abs_residual,
                "expression": compiled.expression,
                "parameter_names": compiled.parameter_names,
                "command": request.command.value,
            })
        else:
            print(f"    🧬 Fit FAILURE: {fit_result.failure_class}")
            round_results.append({
                "round": round_idx + 1,
                "status": "fit_failure",
                "failure_class": fit_result.failure_class,
            })

        # Step 5: Early exit on wall-exit signal (check every 5 rounds)
        if len(round_results) >= 5 and len(round_results) % 5 == 0:
            wall_exit = assess_wall_exit(round_results, budget_exhausted=False)
            if wall_exit == WallExitCode.WALL_LIBRARY_INSUFFICIENT:
                print(f"    🧬 WALL_LIBRARY_INSUFFICIENT — stopping composition")
                break

    # ── Phase 2: Deterministic ratio probes ────────────────────────────────
    # The LLM systematically avoids same-family divisions.  Probe them now,
    # gated by residual statistics that suggest ratio topology.
    print("    🧬 Phase 2: deterministic ratio probes")
    ratio_results = _run_ratio_probes(
        visible_evidence,
        workspace_dir,
        iteration_index,
        var_name=var_name,
        ind_vars=ind_vars if ind_vars else [var_name],
        failure_package=failure_package,
    )
    ratio_successes = sum(1 for r in ratio_results if r.get("status") == "fit_success")
    all_depth1_results = round_results + ratio_results

    # ── Phase 3: Depth-2 composition ─────────────────────────────────────
    # Compose the best depth-1 outputs with base primitives.
    depth2_results: list[dict[str, Any]] = []
    depth1_successes_any = [
        r for r in all_depth1_results if r.get("status") == "fit_success"
    ]
    if depth1_successes_any:
        print("    🧬 Phase 3: depth-2 composition pass")
        depth2_results = _run_depth2_pass(
            all_depth1_results,
            visible_evidence,
            workspace_dir,
            iteration_index,
            var_name=var_name,
            ind_vars=ind_vars if ind_vars else [var_name],
        )
    depth2_successes = sum(1 for r in depth2_results if r.get("status") == "fit_success")

    all_results = all_depth1_results + depth2_results
    total_successes = composition_successes + ratio_successes + depth2_successes

    # Final wall-exit assessment (uses depth-1 results only — depth-2 is
    # an extension, not a signal that depth-1 is improving)
    wall_exit = assess_wall_exit(
        round_results, budget_exhausted=(len(round_results) >= budget)
    )

    # Stamp last_composition_iteration so the cooldown guard in
    # detect_feynman_wall knows when composition last ran.
    from src.ztare.composition.structural_memory import load_structural_memory
    _comp_mem = load_structural_memory(workspace_dir)
    _comp_mem["last_composition_iteration"] = iteration_index
    (workspace_dir / "structural_memory.json").write_text(
        json.dumps(_comp_mem, indent=2) + "\n", encoding="utf-8"
    )

    print(
        f"    🧬 Composition complete: {total_successes}/{len(all_results)} "
        f"successes (d1={composition_successes}, ratio={ratio_successes}, "
        f"d2={depth2_successes}), exit={wall_exit.value}"
    )

    return {
        "wall_exit_code": wall_exit.value,
        "rounds": len(all_results),
        "successes": total_successes,
        "round_results": all_results,
        "ratio_probe_successes": ratio_successes,
        "depth2_successes": depth2_successes,
    }


# ---------------------------------------------------------------------------
# Composition Mutator (Deliverable 2) — LLM-guided composition search
# ---------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

# The 32 base primitives the mutator can reference as operands.
# Each entry: (label, expression_template, parameter_names)
_BASE_PRIMITIVES: list[tuple[str, str, list[str]]] = [
    ("linear", "a * n + b", ["a", "b"]),
    ("quadratic", "a * n**2 + b * n + c", ["a", "b", "c"]),
    ("cubic", "a * n**3 + b * n**2 + c * n + d", ["a", "b", "c", "d"]),
    ("power", "a * n**b + c", ["a", "b", "c"]),
    ("sqrt", "a * math.sqrt(n) + b", ["a", "b"]),
    ("log", "a * math.log(n) + b", ["a", "b"]),
    ("log_quadratic", "a * math.log(n)**2 + b * math.log(n) + c", ["a", "b", "c"]),
    ("exp", "a * math.exp(b * n) + c", ["a", "b", "c"]),
    ("exp_decay", "a * math.exp(-b * n) + c", ["a", "b", "c"]),
    ("sin", "a * math.sin(b * n + c) + d", ["a", "b", "c", "d"]),
    ("cos", "a * math.cos(b * n + c) + d", ["a", "b", "c", "d"]),
    ("tan_damped", "a * math.tanh(b * n) + c", ["a", "b", "c"]),
    ("logistic", "a / (1 + math.exp(-b * (n - c)))", ["a", "b", "c"]),
    ("reciprocal", "a / n + b", ["a", "b"]),
    ("harmonic", "a / n + b / n**2 + c", ["a", "b", "c"]),
    ("sqrt_log", "a * math.sqrt(n) + b * math.log(n) + c", ["a", "b", "c"]),
    ("power_log", "a * n**b * math.log(n) + c", ["a", "b", "c"]),
    ("exp_sin", "a * math.exp(b * n) * math.sin(c * n + d)", ["a", "b", "c", "d"]),
    ("shifted_power", "a * (n - b)**c + d", ["a", "b", "c", "d"]),
    ("gamma_approx", "a * math.sqrt(n) * math.exp(-b * n) + c", ["a", "b", "c"]),
    ("cosh", "a * math.cosh(b * n) + c", ["a", "b", "c"]),
    ("sinh", "a * math.sinh(b * n) + c", ["a", "b", "c"]),
    ("log_shifted", "a * math.log(n + b) + c", ["a", "b", "c"]),
    ("double_exp", "a * math.exp(b * n) + c * math.exp(d * n)", ["a", "b", "c", "d"]),
    ("rational", "a * n / (n + b) + c", ["a", "b", "c"]),
    ("sqrt_reciprocal", "a / math.sqrt(n) + b", ["a", "b"]),
    ("power_shifted", "a * (n + b)**c", ["a", "b", "c"]),
    ("log_reciprocal", "a * math.log(n) / n + b", ["a", "b"]),
    ("exp_sqrt", "a * math.exp(b * math.sqrt(n)) + c", ["a", "b", "c"]),
    ("parity_cos", "a * math.cos(math.pi * n) + b", ["a", "b"]),
    ("floor_approx", "a * math.tanh(b * (n - c)) + d", ["a", "b", "c", "d"]),
    ("compound", "a * n**b * math.exp(c * n) + d", ["a", "b", "c", "d"]),
]


_COMPOSITION_MUTATOR_SYSTEM = """\
You are a mathematical composition engine. Your task is to propose a single \
composition of two existing primitives that might explain the residual structure \
left by a failed curve-fitting attempt.

## Rules
1. Output ONLY a JSON object — no prose, no markdown fences, no explanation.
2. The JSON must have exactly these keys:
   - "command": one of "NEST", "DERIVE", "COMPOSE", "BIVARIATE_SCALE"
   - "operand_a": label of the first primitive (from the library below)
   - "operand_b": label of the second primitive (null for DERIVE and BIVARIATE_SCALE)
   - "compose_op": one of "+", "*", "/" (required for COMPOSE, null otherwise)
   - "motivating_statistic": which residual statistic motivated this choice
3. Do NOT propose CONVOLVE — it is deferred.
4. Do NOT re-propose a composition whose structural family is already exhausted.
5. Choose the composition command based on the residual statistics:
   - High sign_change_count → periodic residual → NEST with trig operand
   - High autocorrelation_lag1 → smooth trend in residual → COMPOSE(+) or DERIVE
   - multiplicativity_ratio ≈ 1.0 (reliable) → multiplicative structure (use COMPOSE(*))
   - Low sign_change_count + monotonic growth → COMPOSE(+) with growth primitive
   - Evidence contains two independent variables and residual scales with the second → BIVARIATE_SCALE
   - Residual has bounded magnitude (no divergence) AND the apex loser already saturates
     → the target may be a RATIO of two functions of the same family.  Try COMPOSE(X, /, Y)
     where X and Y are the SAME primitive family (e.g. double_exp / double_exp, exp / exp).
     Symmetric self-ratios produce saturation-with-structure that additive compositions cannot
6. DERIVE takes only operand_a (forward difference A(n+1) - A(n)).
7. BIVARIATE_SCALE takes only operand_a: produces x2 * g(x1) where x2 is the second
   independent variable and g is the operand_a primitive of the first variable.

## Primitive Library
{primitive_table}

## Exhausted Families (do not re-propose these structural forms)
{exhausted_list}

## Failure Package
Apex loser family: {apex_label}
Apex loser expression: {apex_expression}
Apex max_abs_residual: {apex_residual}

Residual statistics (visible slice only):
{residual_stats}

Visible slice size: {visible_n} points
"""


@dataclass
class CompositionMutatorResult:
    request: CompositionRequest | None
    raw_json: str
    parse_error: str | None = None
    model_id: str | None = None


def _build_primitive_table(var_name: str = "n") -> str:
    """Return a formatted primitive table, substituting the independent variable name.

    All primitives use ``n`` internally; pass ``var_name`` to rename for continuous
    domains (e.g. ``"t"`` for time-series, ``"x"`` for spatial data).
    """
    lines = []
    for label, expr, params in _BASE_PRIMITIVES:
        if var_name != "n":
            expr = re.sub(r'\bn\b', var_name, expr)
        lines.append(f"  {label}: {expr}  (params: {', '.join(params)})")
    return "\n".join(lines)


def _format_residual_stats(stats: dict[str, Any]) -> str:
    lines = []
    for k, v in stats.items():
        if isinstance(v, float):
            lines.append(f"  {k}: {v:.6f}")
        else:
            lines.append(f"  {k}: {v}")
    return "\n".join(lines)


def build_composition_prompt(failure_package: FailurePackage, var_name: str = "n") -> str:
    """Build the LLM prompt from a FailurePackage. Public for harness testing.

    Args:
        failure_package: the FailurePackage from structural memory exhaustion.
        var_name: independent variable name used in primitives. Defaults to ``"n"``
            (discrete sequences). Pass ``"t"`` for continuous time-series data.
    """
    exhausted_list = "\n".join(
        f"  - {fp}" for fp in failure_package.exhausted_families
    ) or "  (none)"

    return _COMPOSITION_MUTATOR_SYSTEM.format(
        primitive_table=_build_primitive_table(var_name=var_name),
        exhausted_list=exhausted_list,
        apex_label=failure_package.apex_family.family_label,
        apex_expression=failure_package.apex_fit.get("expression", ""),
        apex_residual=failure_package.apex_fit.get("max_abs_residual", "?"),
        residual_stats=_format_residual_stats(failure_package.residual_statistics),
        visible_n=len(failure_package.visible_slice_indices),
    )


def _parse_composition_response(
    raw: str,
    var_name: str = "n",
    ind_vars: list[str] | None = None,
) -> CompositionRequest | tuple[None, str]:
    """Parse LLM JSON response into a CompositionRequest.

    Args:
        raw: raw LLM output string (JSON, possibly with markdown fences).
        var_name: independent variable name. Primitive expressions containing ``n``
            are rewritten to use ``var_name`` before building the request.
        ind_vars: full list of independent variables for the FitDeclaration
            (e.g. ``["t", "x2"]`` for bivariate data). Defaults to ``[var_name]``.

    Returns CompositionRequest on success, or (None, error_string) on failure.
    """
    if ind_vars is None:
        ind_vars = [var_name]

    # Strip markdown fences if the LLM ignores instructions
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        return None, f"JSON parse error: {exc}"

    if not isinstance(data, dict):
        return None, f"Expected JSON object, got {type(data).__name__}"

    command_str = data.get("command")
    valid_commands = ("NEST", "DERIVE", "COMPOSE", "BIVARIATE_SCALE")
    if command_str not in valid_commands:
        return None, f"Invalid command: {command_str!r}. Must be one of {valid_commands}"

    operand_a_label = data.get("operand_a")
    operand_b_label = data.get("operand_b")

    # Resolve labels to expressions and parameter names
    # Substitute n→var_name in primitive expressions at resolution time
    def _resolve(label: str) -> tuple[str, list[str]] | None:
        for lbl, expr, params in _BASE_PRIMITIVES:
            if lbl == label:
                if var_name != "n":
                    expr = re.sub(r'\bn\b', var_name, expr)
                return expr, params
        return None

    resolved_a = _resolve(operand_a_label)
    if resolved_a is None:
        known = [lbl for lbl, _, _ in _BASE_PRIMITIVES]
        return None, f"Unknown operand_a: {operand_a_label!r}. Known: {known}"
    a_expr, a_params = resolved_a

    b_expr: str | None = None
    b_params: list[str] = []
    if command_str not in ("DERIVE", "BIVARIATE_SCALE"):
        resolved_b = _resolve(operand_b_label)
        if resolved_b is None:
            known = [lbl for lbl, _, _ in _BASE_PRIMITIVES]
            return None, f"Unknown operand_b: {operand_b_label!r}. Known: {known}"
        b_expr, b_params = resolved_b

    compose_op = data.get("compose_op")
    if command_str == "COMPOSE" and compose_op not in ("+", "*", "/"):
        return None, f"COMPOSE requires compose_op in (+, *, /), got {compose_op!r}"

    motivating = str(data.get("motivating_statistic", ""))

    return CompositionRequest(
        command=CompositionCommand[command_str],
        operand_a=a_expr,
        operand_b=b_expr,
        compose_op=compose_op if command_str == "COMPOSE" else None,
        motivating_statistic=motivating,
        independent_vars=ind_vars,
        parameter_names_a=a_params,
        parameter_names_b=b_params,
    )


def run_composition_mutator(
    failure_package: FailurePackage,
    *,
    model_id: str = "gemini-2.5-flash",
    retries: int = 3,
    runtime: Any | None = None,
    var_name: str = "n",
    ind_vars: list[str] | None = None,
) -> CompositionMutatorResult:
    """Run the LLM composition mutator on a FailurePackage.

    Args:
        failure_package: The structured failure data from library exhaustion.
        model_id: LLM model to use for composition proposal.
        retries: Number of LLM call retries.
        runtime: An LLMRuntime instance. If None, one is created.
        var_name: Independent variable name (default "n"; use "t" for continuous domains).
        ind_vars: Full list of independent variables for multivariate compositions
            (e.g. ["t", "x2"] for bivariate data). If None, defaults to [var_name].

    Returns:
        CompositionMutatorResult with the parsed CompositionRequest or error.
    """
    from src.ztare.common.llm_runtime import LLMRuntime

    if runtime is None:
        runtime = LLMRuntime()

    prompt = build_composition_prompt(failure_package, var_name=var_name)

    try:
        response = runtime.call_text(
            prompt,
            model_id=model_id,
            retries=retries,
            max_tokens=1000,
            request_label="composition_mutator",
        )
    except Exception as exc:
        _logger.warning("Composition mutator LLM call failed: %s", exc)
        return CompositionMutatorResult(
            request=None,
            raw_json="",
            parse_error=f"LLM call failed: {exc}",
            model_id=model_id,
        )

    raw = response.text
    result = _parse_composition_response(raw, var_name=var_name, ind_vars=ind_vars)

    if isinstance(result, tuple):
        # Parse failure
        _, error = result
        _logger.warning("Composition mutator parse error: %s | raw: %s", error, raw[:200])
        return CompositionMutatorResult(
            request=None,
            raw_json=raw,
            parse_error=error,
            model_id=response.effective_model_id,
        )

    # Validate the composition compiles
    compiled = compile_composition(result)
    if isinstance(compiled, str):
        _logger.warning("Composition failed compilation: %s", compiled)
        return CompositionMutatorResult(
            request=result,
            raw_json=raw,
            parse_error=f"Compilation failed: {compiled}",
            model_id=response.effective_model_id,
        )

    return CompositionMutatorResult(
        request=result,
        raw_json=raw,
        parse_error=None,
        model_id=response.effective_model_id,
    )
