"""GP-157 v5.0 Phase 1 — substrate-evaluation utility.

Consolidates the per-row evaluation logic, crash-rate harness-defect
propagation, and graduated near-miss band that today's per-project
gate_harness.py files re-implement (Bugs #16, #18, #21 from 2026-04-25
session). This module is the single source of truth for those invariants.

Per-project `gate_harness.py` files reduce from ~250 lines to ~40:
parse evidence, call `evaluate_set` + `assert_or_propagate_defect`,
print canonical-schema JSON.

Per the GP-157 v5 spec §4 Phase 1, this module is ADDITIVE — existing
gate_harness.py files continue to work; migration is opt-in per substrate.

Magic-number invariants exposed via per-substrate metadata (D3 fix):
- `near_miss_factor`: read from substrate.meta if present; default 1.5
- `crash_threshold`: 0.5 (≥50% crash → harness defect, not falsification)
- pathology threshold: scales with substrate y range (handled by fit primitive)

Key deviation from per-project copy-paste:
- Per-row residual breakdown by categorical feature (Bug #31 closed-loop)
- Crash-class histogram surfaced to judge prompt (D5 sharp diagnostic)
- Canonical schema includes BOTH legacy keys (`harness_ok`, `gates`) AND
  GP-156-shape keys (`holdout`, `farther_tail`, `all_gates_pass`,
  `any_near_miss`) — readers of either parse correctly during migration.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class EvalResult:
    """Per-gate evaluation result. Canonical schema for v5.0."""

    n: int
    mean_relative_error: float
    max_relative_error: float
    per_row: list[dict] = field(default_factory=list)
    crash_count: int = 0
    crash_rate: float = 0.0
    nonfinite_count: int = 0
    crash_classes: dict[str, int] = field(default_factory=dict)
    passed: bool = False
    near_miss: bool = False
    threshold: float = float("nan")
    near_miss_factor: float = 1.5
    # Bug #31 residual feedback (carried over from fit_features result):
    residual_by_category: dict[str, dict[str, dict[str, float]]] = field(default_factory=dict)


def _relative_error(predicted: float, actual: float) -> float:
    if actual == 0:
        return abs(predicted)
    return abs(predicted - actual) / abs(actual)


def evaluate_set(
    rows: list[tuple[int, float]],
    i_model: Callable[[dict], float],
    features_module: Any,
    *,
    threshold: float,
    near_miss_factor: float = 1.5,
    crash_threshold: float = 0.5,
    compute_residual_breakdown: bool = True,
) -> EvalResult:
    """Evaluate I_model against a list of (row_id, y_observed) rows.

    Closes Bugs #16 (silent-crash invisibility), #18 (graduated near-miss),
    and Bug #31 (per-categorical-feature residual breakdown) at the
    consolidated layer.

    Parameters
    ----------
    rows : list[(row_id, y_observed)]
    i_model : Callable[[dict], float]
        The mutator's predictor; takes a feature dict, returns scalar y.
    features_module : module-like
        Substrate's features.py with `get_features(row_id) -> dict`.
    threshold : float
        Mean-relative-error threshold for `passed`.
    near_miss_factor : float
        Multiplier defining the near-miss band [threshold, factor*threshold).
        Read from substrate.meta in v5.0; default 1.5 for back-compat.
    crash_threshold : float
        Crash-rate fraction (default 0.5) above which `assert_or_propagate_defect`
        propagates as RuntimeError (harness defect) rather than AssertionError
        (falsification). This is the line between "model fit poorly" and "model
        crashed on every row."
    compute_residual_breakdown : bool
        If True, group residuals by each categorical feature value and report
        worst groups in `residual_by_category`. Used by Bug #31 closed-loop.

    Returns
    -------
    EvalResult
        Populated with all per-row outcomes, crash classes, near-miss tag,
        and (optionally) per-category residual breakdown.
    """
    errors: list[float] = []
    per_row: list[dict] = []
    crash_classes: dict[str, int] = {}
    nonfinite_count = 0
    rows_with_features: list[tuple[dict, float, float]] = []  # (features, y_true, residual)

    for row_id, y_true in rows:
        try:
            feats = features_module.get_features(row_id)
        except KeyError:
            per_row.append({
                "id": row_id,
                "error": "no features for id",
                "rel_err": 1.0,
            })
            errors.append(1.0)
            continue

        try:
            y_pred = float(i_model(feats))
        except Exception as exc:  # noqa: BLE001
            cls = type(exc).__name__
            crash_classes[cls] = crash_classes.get(cls, 0) + 1
            per_row.append({
                "id": row_id,
                "y_true": y_true,
                "y_pred": None,
                "rel_err": 1.0,
                "exception": cls,
            })
            errors.append(1.0)
            continue

        if math.isnan(y_pred) or math.isinf(y_pred):
            nonfinite_count += 1
            per_row.append({
                "id": row_id,
                "y_true": y_true,
                "y_pred": None,
                "rel_err": 1.0,
                "note": "NaN or Inf",
            })
            errors.append(1.0)
            continue

        err = _relative_error(y_pred, y_true)
        per_row.append({
            "id": row_id,
            "y_true": y_true,
            "y_pred": y_pred,
            "rel_err": err,
        })
        errors.append(err)
        rows_with_features.append((feats, y_true, err))

    n = len(errors) or 1
    mean_re = sum(errors) / n
    max_re = max(errors) if errors else 1.0
    crash_count = sum(crash_classes.values())
    crash_rate = (crash_count + nonfinite_count) / n
    passed = mean_re < threshold
    near_miss = (not passed) and (mean_re < threshold * near_miss_factor)

    residual_by_category: dict[str, dict[str, dict[str, float]]] = {}
    if compute_residual_breakdown and rows_with_features:
        seen_keys: set[str] = set()
        for feats, _, _ in rows_with_features:
            for fk, fv in feats.items():
                if isinstance(fv, str):
                    seen_keys.add(fk)
        for fk in seen_keys:
            residual_by_category[fk] = {}
            groups: dict[str, list[float]] = {}
            for feats, _, r in rows_with_features:
                fv = feats.get(fk)
                if not isinstance(fv, str) or not math.isfinite(r):
                    continue
                groups.setdefault(fv, []).append(r)
            for fv, rs in groups.items():
                residual_by_category[fk][fv] = {
                    "n": len(rs),
                    "mean_abs_res": sum(rs) / len(rs),
                    "max_abs_res": max(rs),
                }

    return EvalResult(
        n=len(errors),
        mean_relative_error=mean_re,
        max_relative_error=max_re,
        per_row=per_row,
        crash_count=crash_count,
        crash_rate=crash_rate,
        nonfinite_count=nonfinite_count,
        crash_classes=crash_classes,
        passed=passed,
        near_miss=near_miss,
        threshold=threshold,
        near_miss_factor=near_miss_factor,
        residual_by_category=residual_by_category,
    )


def assert_or_propagate_defect(
    result: EvalResult,
    gate_name: str,
    *,
    crash_threshold: float = 0.5,
    is_preflight: bool = False,
) -> None:
    """Decide whether a gate result is a falsification (AssertionError) or
    a harness defect (RuntimeError). Skipped under is_preflight.

    Per Bug #16 (silent-crash bypass): when crash_rate ≥ crash_threshold,
    the model never produced predictions — surface as RuntimeError so the
    judge sees "harness defect: <crash class summary>" instead of
    "MRE=1.0 looks like model fit poorly".

    Per Bug #18 (graduated near-miss): tag failure as `[near_miss]` or
    `[hard_miss]` so the apparatus's downstream logic (test_thesis.py
    holdout-hard-gate) can apply the floor=30 instead of zero.
    """
    if is_preflight:
        return  # smoke tests against baseline stubs run with 100% crash; do not propagate

    if result.crash_rate >= crash_threshold and result.n > 0:
        raise RuntimeError(
            f"{gate_name} harness defect: I_model crashed on "
            f"{result.crash_count}/{result.n} rows + {result.nonfinite_count} "
            f"non-finite outputs (crash_rate={result.crash_rate:.2%} >= "
            f"{crash_threshold:.0%}). Exception classes: {result.crash_classes}. "
            f"This is NOT a thesis falsification — the model never produced "
            f"predictions to falsify. Likely cause: PARAMETRIC_FORM declared "
            f"but MODEL_PARAMS unfilled (fit primitive failed to engage), OR "
            f"I_model uses params[...] without GP-156 contract declaration, "
            f"OR form references a feature key absent from features.py."
        )

    if not result.passed:
        tag = "[near_miss — REFINE this form, do not redesign]" if result.near_miss else "[hard_miss]"
        raise AssertionError(
            f"{gate_name} gate FAILED {tag}: mean_relative_error="
            f"{result.mean_relative_error:.4f} >= "
            f"threshold={result.threshold} (near_miss_factor="
            f"{result.near_miss_factor}). "
            f"n={result.n}, max_rel_err={result.max_relative_error:.4f}."
        )


def to_canonical_schema(
    results: dict[str, EvalResult],
    *,
    extra_fields: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build the canonical JSON schema readable by BOTH legacy and v5.0
    consumers. Legacy parsers read `harness_ok` + `gates: [...]`. v5.0
    parsers read per-gate keys + `all_gates_pass` + `any_near_miss`.

    Parameters
    ----------
    results : {gate_name: EvalResult}
    extra_fields : optional substrate-specific fields (e.g. asymptotic_bound
        for gp155) to merge into the top-level dict.
    """
    out: dict[str, Any] = {}
    gates_list: list[dict[str, Any]] = []
    all_pass = True
    any_near = False

    for name, r in results.items():
        per_gate = {
            "n": r.n,
            "mean_relative_error": r.mean_relative_error,
            "max_relative_error": r.max_relative_error,
            "threshold": r.threshold,
            "near_miss_factor": r.near_miss_factor,
            "passed": r.passed,
            "near_miss": r.near_miss,
            "crash_count": r.crash_count,
            "crash_rate": r.crash_rate,
            "nonfinite_count": r.nonfinite_count,
            "crash_classes": r.crash_classes,
            "per_row": r.per_row,
            "residual_by_category": r.residual_by_category,
        }
        out[name.lower()] = per_gate
        # Legacy-shape entry for back-compat with test_thesis.py:2335-2470 parser
        gates_list.append({
            "name": name.upper(),
            "passed": r.passed,
            "near_miss": r.near_miss,
            "value": r.mean_relative_error,
            "threshold": r.threshold,
            "operator": "<",
        })
        all_pass = all_pass and r.passed
        any_near = any_near or r.near_miss

    out["harness_ok"] = True
    out["gates"] = gates_list
    out["all_gates_pass"] = all_pass
    out["any_near_miss"] = any_near
    if extra_fields:
        out.update(extra_fields)
    return out
