"""GP-076 Predictive Divergence Sweep.

Breaks corrector degeneracy when residual diagnostics narrow the library to N
candidates that all achieve zero residual on visible data.

Pipeline:
  Step 1: Fit all N library forms to visible corrector residuals via SciPy
  Step 2: Tree-size soft ranking (soft prior, never eliminates)
  Step 3: Stagnation gate (>= 3 consecutive zero-improvement iterations)
  Step 4: Divergence point computation (max sum-of-pairwise-differences)
  Step 5: Contamination gate (worst-case suppression)
  Step 6: Single-point query + elimination
  Step 7: Feynman Wall fallback (library_exhausted flag)
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np
from scipy.optimize import minimize_scalar, minimize

from ztare.gates.corrector_library import (
    CORRECTOR_LIBRARY,
    CorrectorForm,
    filter_by_descriptor,
)


RESIDUAL_EPSILON = 1.0
STAGNATION_THRESHOLD = 3


@dataclass(frozen=True)
class FittedCandidate:
    form: CorrectorForm
    fitted_k: float
    max_abs_residual: float
    predictions: dict[int, float]
    tree_size: int = 0


@dataclass(frozen=True)
class SweepResult:
    status: str
    survivors: tuple[FittedCandidate, ...]
    query_point: int | None = None
    query_observed: float | None = None
    eliminated: tuple[str, ...] = ()
    divergence_scores: dict[int, float] = field(default_factory=dict)
    contamination_suppressed: bool = False
    library_exhausted: bool = False
    message: str = ""

    def to_dict(self) -> dict:
        d: dict = {
            "status": self.status,
            "survivor_count": len(self.survivors),
            "survivor_names": [s.form.name for s in self.survivors],
            "message": self.message,
        }
        if self.query_point is not None:
            d["query_point"] = self.query_point
            d["query_observed"] = self.query_observed
        if self.eliminated:
            d["eliminated"] = list(self.eliminated)
        if self.contamination_suppressed:
            d["contamination_suppressed"] = True
        if self.library_exhausted:
            d["library_exhausted"] = True
        return d


def _estimate_tree_size(name: str) -> int:
    """Rough node count for expression tree ranking."""
    simple = {"heaviside(v >= k)": 3, "step at v=k": 3, "constant k": 1}
    if name in simple:
        return simple[name]
    if "round" in name or "floor" in name or "ceil" in name:
        return 4
    return 5


def fit_library_forms(
    corrector_data: list[tuple[int, float]],
    forms: tuple[CorrectorForm, ...] | None = None,
    epsilon: float = RESIDUAL_EPSILON,
) -> list[FittedCandidate]:
    """Step 1: Fit all library forms to corrector residual data.

    corrector_data: list of (v, corrector_value) pairs.
    Returns candidates with max_abs_residual < epsilon.
    """
    if forms is None:
        forms = CORRECTOR_LIBRARY

    v_values = [v for v, _ in corrector_data]
    z_values = np.array([z for _, z in corrector_data])
    candidates: list[FittedCandidate] = []

    for form in forms:
        best_k, best_residual = _fit_single_form(form, v_values, z_values)
        if best_residual <= epsilon:
            preds = {v: form.fn(float(v), best_k) for v in v_values}
            candidates.append(
                FittedCandidate(
                    form=form,
                    fitted_k=best_k,
                    max_abs_residual=best_residual,
                    predictions=preds,
                    tree_size=_estimate_tree_size(form.name),
                )
            )

    candidates.sort(key=lambda c: (c.tree_size, c.form.name))
    return candidates


def _fit_single_form(
    form: CorrectorForm,
    v_values: list[int],
    z_values: np.ndarray,
) -> tuple[float, float]:
    """Fit a single library form f(v, k) to data by optimizing k."""
    def objective(k: float) -> float:
        try:
            preds = np.array([form.fn(float(v), k) for v in v_values])
            return float(np.max(np.abs(preds - z_values)))
        except (OverflowError, ValueError, ZeroDivisionError):
            return 1e12

    best_k = 0.0
    best_res = 1e12

    if form.is_smooth:
        for k0 in np.linspace(-5, 20, 51):
            try:
                result = minimize_scalar(
                    objective,
                    bounds=(k0 - 2, k0 + 2),
                    method="bounded",
                )
                if result.fun < best_res:
                    best_res = result.fun
                    best_k = result.x
            except Exception:
                continue
    else:
        for k_val in np.linspace(-5, 20, 2501):
            res = objective(k_val)
            if res < best_res:
                best_res = res
                best_k = k_val

    # Integer grid as safety net for forms with integer-optimal k
    for k_int in range(-10, 30):
        k_f = float(k_int)
        res = objective(k_f)
        if res < best_res:
            best_res = res
            best_k = k_f

    return best_k, best_res


def compute_divergence_point(
    candidates: list[FittedCandidate],
    v_max_visible: int,
) -> tuple[int, dict[int, float]]:
    """Step 4: Find v where candidates maximally disagree.

    Search domain: integers in [1, v_max_visible + len(candidates)].
    Aggregation: sum of pairwise absolute differences.
    """
    v_max_extended = v_max_visible + len(candidates)
    scores: dict[int, float] = {}
    best_v = 1
    best_score = -1.0

    for v in range(1, v_max_extended + 1):
        preds = []
        for c in candidates:
            try:
                preds.append(c.form.fn(float(v), c.fitted_k))
            except (OverflowError, ValueError, ZeroDivisionError):
                preds.append(float("nan"))

        pairwise_sum = 0.0
        n = len(preds)
        for i in range(n):
            for j in range(i + 1, n):
                if math.isfinite(preds[i]) and math.isfinite(preds[j]):
                    pairwise_sum += abs(preds[i] - preds[j])

        scores[v] = pairwise_sum
        if pairwise_sum > best_score:
            best_score = pairwise_sum
            best_v = v

    return best_v, scores


def check_contamination_gate(
    candidates: list[FittedCandidate],
    query_v: int,
) -> bool:
    """Step 5: Worst-case suppression.

    Returns True if query is PERMITTED, False if SUPPRESSED.
    Suppress if ANY possible observed value would uniquely determine
    the GT form with zero free parameters remaining.
    """
    predicted_values: set[float] = set()
    for c in candidates:
        try:
            predicted_values.add(c.form.fn(float(query_v), c.fitted_k))
        except (OverflowError, ValueError, ZeroDivisionError):
            continue

    for possible_obs in predicted_values:
        consistent = [
            c for c in candidates
            if _matches(c.form.fn(float(query_v), c.fitted_k), possible_obs)
        ]
        if len(consistent) == 1:
            # Would uniquely determine — check if free parameters remain.
            # For our library, k is the only free parameter. If k is fully
            # determined by existing data + this observation, suppress.
            # Conservative: if only 1 candidate survives, suppress.
            return False

    return True


def _matches(predicted: float, observed: float, epsilon: float = RESIDUAL_EPSILON) -> bool:
    return abs(float(predicted) - float(observed)) <= epsilon


def execute_query(
    candidates: list[FittedCandidate],
    query_v: int,
    f_true_corrector: Callable[[int], float],
    epsilon: float = RESIDUAL_EPSILON,
) -> tuple[float, list[FittedCandidate], list[str]]:
    """Step 6: Query f_true at divergence point, eliminate mismatches.

    Returns (observed_value, survivors, eliminated_names).
    """
    observed = f_true_corrector(query_v)
    survivors: list[FittedCandidate] = []
    eliminated: list[str] = []

    for c in candidates:
        try:
            predicted = c.form.fn(float(query_v), c.fitted_k)
        except (OverflowError, ValueError, ZeroDivisionError):
            eliminated.append(c.form.name)
            continue

        if _is_integer_form(c.form):
            if predicted == observed:
                survivors.append(c)
            else:
                eliminated.append(c.form.name)
        else:
            if abs(predicted - observed) <= epsilon:
                survivors.append(c)
            else:
                eliminated.append(c.form.name)

    return observed, survivors, eliminated


def _is_integer_form(form: CorrectorForm) -> bool:
    """Check if a form produces integer outputs (step/round/floor/ceil)."""
    indicators = ["round", "floor", "ceil", "heaviside", "step", "mod"]
    name_lower = form.name.lower()
    return any(ind in name_lower for ind in indicators)


def load_sweep_state(workspace_dir: Path) -> dict:
    path = workspace_dir / "sweep_state.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "library_exhausted": False,
        "query_history": [],
        "total_queries": 0,
    }


def save_sweep_state(workspace_dir: Path, state: dict) -> None:
    path = workspace_dir / "sweep_state.json"
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def run_sweep(
    *,
    corrector_data: list[tuple[int, float]],
    f_true_corrector: Callable[[int], float],
    descriptor_forms: tuple[CorrectorForm, ...] | None = None,
    v_max_visible: int,
    stagnation_count: int,
    run_length: int,
    workspace_dir: Path | None = None,
    epsilon: float = RESIDUAL_EPSILON,
    holdout_checker: Callable[[CorrectorForm, float], bool] | None = None,
) -> SweepResult:
    """Full GP-076 pipeline: Steps 1-7.

    Args:
        corrector_data: (v, corrector_value) pairs from visible evidence.
        f_true_corrector: callable(v) -> true corrector value (one-point query).
        descriptor_forms: narrowed library forms (from residual diagnostics). None = full library.
        v_max_visible: largest v in visible evidence.
        stagnation_count: consecutive iterations with no score improvement.
        run_length: total iterations in the run (for query budget).
        workspace_dir: for sweep_state.json persistence.
        epsilon: residual threshold (shared with Step 1 and Step 6).
        holdout_checker: optional callable(form, k) -> bool for holdout gate.
    """
    sweep_state = load_sweep_state(workspace_dir) if workspace_dir else {
        "library_exhausted": False, "query_history": [], "total_queries": 0,
    }

    if sweep_state.get("library_exhausted", False):
        return SweepResult(
            status="library_exhausted_prior",
            survivors=(),
            library_exhausted=True,
            message="Library already exhausted in prior sweep. LLM topology proposal mode.",
        )

    # Step 3: stagnation gate
    if stagnation_count < STAGNATION_THRESHOLD:
        return SweepResult(
            status="stagnation_gate_not_reached",
            survivors=(),
            message=f"Stagnation count {stagnation_count} < {STAGNATION_THRESHOLD}. Sweep not triggered.",
        )

    query_budget = max(1, run_length // 3)
    total_queries = sweep_state.get("total_queries", 0)
    if total_queries >= query_budget:
        return SweepResult(
            status="query_budget_exhausted",
            survivors=(),
            message=f"Query budget exhausted ({total_queries}/{query_budget}). Escalating to LLM.",
        )

    # Step 1: fit all library forms
    candidates = fit_library_forms(corrector_data, forms=descriptor_forms, epsilon=epsilon)

    if len(candidates) <= 1:
        return SweepResult(
            status="no_degeneracy",
            survivors=tuple(candidates),
            message=f"Only {len(candidates)} candidate(s) survive fitting. No sweep needed.",
        )

    # Step 4: divergence point
    query_v, div_scores = compute_divergence_point(candidates, v_max_visible)

    if div_scores.get(query_v, 0.0) == 0.0:
        return SweepResult(
            status="no_divergence",
            survivors=tuple(candidates),
            divergence_scores=div_scores,
            message=f"{len(candidates)} candidates agree everywhere in search domain. Cannot discriminate.",
        )

    # Step 5: contamination gate — try alternatives if best point suppressed
    gate_permitted = check_contamination_gate(candidates, query_v)
    if not gate_permitted:
        for alt_v, _ in sorted(div_scores.items(), key=lambda x: -x[1]):
            if alt_v == query_v:
                continue
            if div_scores[alt_v] == 0.0:
                break
            if check_contamination_gate(candidates, alt_v):
                query_v = alt_v
                gate_permitted = True
                break

    if not gate_permitted:
        return SweepResult(
            status="contamination_suppressed",
            survivors=tuple(candidates),
            query_point=query_v,
            contamination_suppressed=True,
            divergence_scores=div_scores,
            message=f"All divergence points suppressed by contamination gate.",
        )

    # Step 6: query and eliminate
    observed, survivors, eliminated = execute_query(
        candidates, query_v, f_true_corrector, epsilon=epsilon,
    )

    # Record query
    sweep_state["total_queries"] = total_queries + 1
    sweep_state["query_history"].append({
        "query_v": query_v,
        "observed": observed,
        "eliminated": eliminated,
        "survivors_before": len(candidates),
        "survivors_after": len(survivors),
        "surviving_forms": [s.form.name for s in survivors],
        "surviving_k_values": {s.form.name: round(s.fitted_k, 6) for s in survivors},
    })

    # Step 7: Feynman Wall fallback
    library_exhausted = False
    if holdout_checker and survivors:
        holdout_survivors = [
            s for s in survivors
            if holdout_checker(s.form, s.fitted_k)
        ]
        if not holdout_survivors:
            library_exhausted = True
            sweep_state["library_exhausted"] = True
    elif not survivors:
        library_exhausted = True
        sweep_state["library_exhausted"] = True

    if workspace_dir:
        save_sweep_state(workspace_dir, sweep_state)

    return SweepResult(
        status="query_executed",
        survivors=tuple(survivors),
        query_point=query_v,
        query_observed=observed,
        eliminated=tuple(eliminated),
        divergence_scores=div_scores,
        library_exhausted=library_exhausted,
        message=(
            f"Queried v={query_v}, observed={observed}. "
            f"Eliminated {len(eliminated)}, {len(survivors)} survive."
            + (" LIBRARY EXHAUSTED." if library_exhausted else "")
        ),
    )


def backtest_sandbox_15_full_library() -> SweepResult:
    """Scenario A: full library, no residual-diagnostics filtering."""
    def gt_corrector(v: int) -> float:
        return float(round(0.08 * v))
    corrector_data = [(v, gt_corrector(v)) for v in range(1, 17)]
    return run_sweep(
        corrector_data=corrector_data,
        f_true_corrector=gt_corrector,
        descriptor_forms=None,
        v_max_visible=15,
        stagnation_count=5,
        run_length=15,
        epsilon=RESIDUAL_EPSILON,
    )


def backtest_sandbox_15_component_c() -> SweepResult:
    """Scenario B: residual diagnostics narrowed to non-smooth+monotone (7 forms).

    GT is smooth but visible data looks step-like → GT excluded from
    narrowed set → sweep should exhaust and trigger Feynman Wall.
    """
    def gt_corrector(v: int) -> float:
        return float(round(0.08 * v))
    corrector_data = [(v, gt_corrector(v)) for v in range(1, 17)]
    descriptor_forms = filter_by_descriptor(is_smooth=False, is_monotone=True)
    return run_sweep(
        corrector_data=corrector_data,
        f_true_corrector=gt_corrector,
        descriptor_forms=descriptor_forms,
        v_max_visible=15,
        stagnation_count=5,
        run_length=15,
        epsilon=RESIDUAL_EPSILON,
    )


def _print_step_by_step(
    label: str,
    corrector_data: list[tuple[int, float]],
    gt_corrector: Callable[[int], float],
    forms: tuple[CorrectorForm, ...] | None,
) -> None:
    """Detailed step-by-step backtest output."""
    print(f"\n{'=' * 72}")
    print(f"  {label}")
    print(f"{'=' * 72}")

    form_desc = "full library (26 forms)" if forms is None else f"{len(forms)} forms"
    print(f"\n--- Step 1: Fit library forms ({form_desc}) ---")
    candidates = fit_library_forms(corrector_data, forms=forms)
    zero_res = [c for c in candidates if c.max_abs_residual == 0.0]
    nonzero = [c for c in candidates if c.max_abs_residual > 0.0]
    print(f"  {len(candidates)} survive (epsilon={RESIDUAL_EPSILON})")
    print(f"    {len(zero_res)} exact (residual=0.0):")
    for c in zero_res:
        print(f"      {c.form.name:40s}  k={c.fitted_k:8.4f}")
    if nonzero:
        print(f"    {len(nonzero)} approximate (0 < residual <= {RESIDUAL_EPSILON}):")
        for c in nonzero:
            print(f"      {c.form.name:40s}  k={c.fitted_k:8.4f}  res={c.max_abs_residual:.4f}")

    if len(candidates) <= 1:
        print("  No degeneracy. Done.")
        return

    print(f"\n--- Step 4: Divergence point computation ---")
    query_v, div_scores = compute_divergence_point(candidates, v_max_visible=15)
    top_5 = sorted(div_scores.items(), key=lambda x: -x[1])[:5]
    for v, score in top_5:
        print(f"    v={v:3d}  disagreement={score:8.2f}")
    print(f"  >> Best: v={query_v} (score={div_scores[query_v]:.2f})")

    print(f"\n--- Step 5: Contamination gate ---")
    permitted = check_contamination_gate(candidates, query_v)
    print(f"  v={query_v}: {'PERMITTED' if permitted else 'SUPPRESSED'}")
    if not permitted:
        for alt_v, alt_score in sorted(div_scores.items(), key=lambda x: -x[1]):
            if alt_v == query_v:
                continue
            if check_contamination_gate(candidates, alt_v):
                print(f"  Next permitted: v={alt_v} (score={alt_score:.2f})")
                query_v = alt_v
                break

    print(f"\n--- Step 6: Query at v={query_v} ---")
    observed = gt_corrector(query_v)
    print(f"  GT corrector({query_v}) = {observed}")
    for c in candidates:
        pred = c.form.fn(float(query_v), c.fitted_k)
        if _is_integer_form(c.form):
            match = "MATCH" if pred == observed else "MISS"
        else:
            match = "MATCH" if _matches(pred, observed) else "MISS"
        print(f"    {c.form.name:40s}  pred={pred:6.1f}  {match}")

    _, survivors, eliminated = execute_query(candidates, query_v, gt_corrector)
    print(f"\n  Result: {len(candidates)} -> {len(survivors)} survivors, {len(eliminated)} eliminated")

    gt_survived = any(s.form.name == "round(k*v)" for s in survivors)
    print(f"  GT form 'round(k*v)' survived: {gt_survived}")


if __name__ == "__main__":
    print("GP-076 Predictive Divergence Sweep — Sandbox 15 Backtest")
    print("GT: f(u,v) = u^2*v - u + round(0.08*v)")
    print("Corrector on v=1..16: [0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1]")
    print("Key insight: visible data looks step-like but GT form is smooth")

    def gt_corrector(v: int) -> float:
        return float(round(0.08 * v))
    corrector_data = [(v, gt_corrector(v)) for v in range(1, 17)]

    # Scenario A: full library
    _print_step_by_step(
        "SCENARIO A: Full library (no residual-diagnostics filtering)",
        corrector_data, gt_corrector, forms=None,
    )

    # Scenario B: residual diagnostics narrowed
    narrowed = filter_by_descriptor(is_smooth=False, is_monotone=True)
    _print_step_by_step(
        f"SCENARIO B: residual diagnostics narrowed ({len(narrowed)} non-smooth+monotone)",
        corrector_data, gt_corrector, forms=narrowed,
    )

    # Full pipeline results
    print(f"\n{'=' * 72}")
    print("  FULL PIPELINE RESULTS")
    print(f"{'=' * 72}")

    print("\nScenario A (full library):")
    result_a = backtest_sandbox_15_full_library()
    print(f"  Status: {result_a.status}")
    print(f"  Message: {result_a.message}")
    if result_a.survivors:
        print(f"  Survivors: {[s.form.name for s in result_a.survivors]}")

    print("\nScenario B (residual diagnostics narrowed):")
    result_b = backtest_sandbox_15_component_c()
    print(f"  Status: {result_b.status}")
    print(f"  Message: {result_b.message}")
    if result_b.survivors:
        print(f"  Survivors: {[s.form.name for s in result_b.survivors]}")
    if result_b.library_exhausted:
        print("  >> FEYNMAN WALL: Library exhausted. Escalation to LLM topology proposal.")

    print(f"\n{'=' * 72}")
    print("CONCLUSION")
    print(f"{'=' * 72}")
    gt_in_a = any(s.form.name == "round(k*v)" for s in result_a.survivors)
    print(f"  Scenario A: GT survived = {gt_in_a}")
    print(f"  Scenario B: Library exhausted = {result_b.library_exhausted}")
    print(f"  Both outcomes are correct GP-076 behavior:")
    print(f"    A: Sweep breaks degeneracy, GT wins")
    print(f"    B: residual diagnostics excluded GT → sweep exhausts → Feynman Wall fires")
    print(f"{'=' * 72}")
