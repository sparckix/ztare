"""GP-074 Component C — Residual Analyzer.

Implements the 2-bit categorical shape descriptor pipeline:
  Phase A: perturbation probing + descriptor extraction + gates
  Phase B: parameter fitting is GP-035 (not duplicated here)

Pipeline:
  1. Check degeneracy (visible residual < epsilon)
  2. If degenerate: generate perturbation probes, compute discrepancy
  3. Extract 2-bit descriptor: {continuity, monotonicity}
  4. Stagnation gate (O(1)) — fires only after K consecutive failures
  5. Contamination gate (O(library)) — suppresses if descriptor too narrow
  6. Emit or suppress

State persistence: component_c_state.json in workspace_dir.
Artifact: residual_fingerprint.json in workspace_dir.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

from src.ztare.gates.corrector_library import filter_by_descriptor


DEFAULT_K = 3
DEFAULT_N = 5
DEFAULT_EPSILON = 1e-8
DEFAULT_PROBE_COUNT = 20


@dataclass(frozen=True)
class ShapeDescriptor:
    continuity: str  # "smooth" | "step_function"
    monotonicity: str  # "monotone" | "non_monotone"


@dataclass(frozen=True)
class AnalyzerResult:
    status: str
    descriptor: ShapeDescriptor | None = None
    candidate_count: int | None = None
    stagnation_count: int = 0
    iteration_index: int = 0
    probe_count: int = 0

    def to_dict(self) -> dict:
        d: dict = {
            "status": self.status,
            "stagnation_count": self.stagnation_count,
            "iteration_index": self.iteration_index,
        }
        if self.descriptor is not None:
            d["descriptor"] = {
                "continuity": self.descriptor.continuity,
                "monotonicity": self.descriptor.monotonicity,
            }
        if self.candidate_count is not None:
            d["candidate_count"] = self.candidate_count
        if self.probe_count > 0:
            d["probe_count"] = self.probe_count
        return d


def _load_state(workspace_dir: Path) -> dict:
    state_path = workspace_dir / "component_c_state.json"
    if state_path.exists():
        return json.loads(state_path.read_text(encoding="utf-8"))
    return {"stagnation_count": 0, "last_emitted_iter": -1}


def _save_state(workspace_dir: Path, state: dict) -> None:
    state_path = workspace_dir / "component_c_state.json"
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _save_fingerprint(workspace_dir: Path, result: AnalyzerResult) -> None:
    path = workspace_dir / "residual_fingerprint.json"
    path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")


def _generate_probes(
    v_range: tuple[int, int],
    u_range: tuple[int, int],
    iteration_index: int,
    substrate_id: str,
    count: int = DEFAULT_PROBE_COUNT,
) -> list[tuple[int, int]]:
    seed_str = f"{iteration_index}:{substrate_id}:component_c"
    seed = int(hashlib.sha256(seed_str.encode()).hexdigest()[:8], 16)
    rng = np.random.RandomState(seed)

    v_lo, v_hi = v_range
    u_lo, u_hi = u_range
    v_ext = max(v_hi * 2, v_hi + 10)
    u_ext = max(u_hi * 2, u_hi + 5)

    probes = []
    for _ in range(count * 3):
        v = int(rng.randint(v_lo, v_ext + 1))
        u = int(rng.randint(u_lo, u_ext + 1))
        if (u, v) not in probes:
            probes.append((u, v))
        if len(probes) >= count:
            break
    return probes[:count]


def _classify_continuity(discrepancies: list[tuple[int, float]]) -> str:
    if len(discrepancies) < 3:
        return "smooth"
    sorted_d = sorted(discrepancies, key=lambda x: x[0])
    slopes: list[float] = []
    for i in range(len(sorted_d) - 1):
        dv = sorted_d[i + 1][0] - sorted_d[i][0]
        if dv == 0:
            continue
        slopes.append(abs(sorted_d[i + 1][1] - sorted_d[i][1]) / dv)
    if not slopes:
        return "smooth"
    max_slope = max(slopes)
    mean_slope = sum(slopes) / len(slopes)
    if mean_slope == 0:
        return "smooth"
    jump_ratio = max_slope / mean_slope
    return "step_function" if jump_ratio > 3.0 else "smooth"


def _classify_monotonicity(discrepancies: list[tuple[int, float]]) -> str:
    if len(discrepancies) < 2:
        return "monotone"
    sorted_d = sorted(discrepancies, key=lambda x: x[0])
    vals = [d[1] for d in sorted_d]
    increasing = all(vals[i + 1] >= vals[i] - 1e-12 for i in range(len(vals) - 1))
    decreasing = all(vals[i + 1] <= vals[i] + 1e-12 for i in range(len(vals) - 1))
    return "monotone" if (increasing or decreasing) else "non_monotone"


def _check_contamination_gate(
    descriptor: ShapeDescriptor,
    suppression_threshold: int = DEFAULT_N,
) -> tuple[bool, int]:
    matching_forms = filter_by_descriptor(
        is_smooth=(descriptor.continuity == "smooth"),
        is_monotone=(descriptor.monotonicity == "monotone"),
    )
    candidate_count = len(matching_forms)
    passed = candidate_count >= suppression_threshold
    return passed, candidate_count


def analyze_residual(
    *,
    workspace_dir: Path,
    iteration_index: int,
    f_model: Callable[[int, int], int],
    f_true: Callable[[int, int], int],
    f_dominant: Callable[[int, int], int],
    evidence_triples: list[tuple[int, int, int]],
    max_abs_residual: float,
    substrate_id: str = "default",
    stagnation_k: int = DEFAULT_K,
    suppression_n: int = DEFAULT_N,
    epsilon: float = DEFAULT_EPSILON,
    probe_count: int = DEFAULT_PROBE_COUNT,
) -> AnalyzerResult:
    """Run the Component C residual analysis pipeline.

    Returns an AnalyzerResult with status:
      - not_fired: non-degenerate residual or stagnation gate not reached
      - suppressed_candidate_count: contamination gate suppressed
      - suppressed_probe_failure: probe evaluation error
      - emitted: descriptor delivered to mutator
    """
    state = _load_state(workspace_dir)
    stag_count = state.get("stagnation_count", 0)

    obs_values = [z for _, _, z in evidence_triples]
    obs_std = float(np.std(obs_values)) if obs_values else 1.0
    threshold = epsilon * max(1.0, obs_std)

    if max_abs_residual >= threshold:
        result = AnalyzerResult(
            status="not_fired",
            stagnation_count=stag_count,
            iteration_index=iteration_index,
        )
        _save_fingerprint(workspace_dir, result)
        return result

    stag_count += 1
    state["stagnation_count"] = stag_count
    _save_state(workspace_dir, state)

    if stag_count < stagnation_k:
        result = AnalyzerResult(
            status="not_fired",
            stagnation_count=stag_count,
            iteration_index=iteration_index,
        )
        _save_fingerprint(workspace_dir, result)
        return result

    v_values = [v for _, v, _ in evidence_triples]
    u_values = [u for u, _, _ in evidence_triples]
    v_range = (min(v_values), max(v_values))
    u_range = (min(u_values), max(u_values))

    probes = _generate_probes(
        v_range=v_range,
        u_range=u_range,
        iteration_index=iteration_index,
        substrate_id=substrate_id,
        count=probe_count,
    )

    # Mutator-Dominant Subtraction: isolate the GT corrector shape.
    # The degeneracy condition (visible residual < epsilon) guarantees
    # the mutator's dominant term matches GT's dominant. So
    # f_true(u,v) - f_dominant(u,v) = GT corrector at (u,v).
    # This gives the descriptor the TRUE corrector shape (e.g. smooth+
    # monotone for round(0.08v)), not the confounded discrepancy between
    # two different correctors.
    discrepancies: list[tuple[int, float]] = []
    try:
        for u, v in probes:
            true_val = f_true(u, v)
            dominant_val = f_dominant(u, v)
            discrepancies.append((v, float(true_val - dominant_val)))
    except Exception:
        result = AnalyzerResult(
            status="suppressed_probe_failure",
            stagnation_count=stag_count,
            iteration_index=iteration_index,
            probe_count=len(probes),
        )
        _save_fingerprint(workspace_dir, result)
        return result

    if not discrepancies or all(d[1] == 0.0 for d in discrepancies):
        result = AnalyzerResult(
            status="not_fired",
            stagnation_count=stag_count,
            iteration_index=iteration_index,
            probe_count=len(probes),
        )
        _save_fingerprint(workspace_dir, result)
        return result

    continuity = _classify_continuity(discrepancies)
    monotonicity = _classify_monotonicity(discrepancies)
    descriptor = ShapeDescriptor(continuity=continuity, monotonicity=monotonicity)

    gate_passed, candidate_count = _check_contamination_gate(
        descriptor=descriptor,
        suppression_threshold=suppression_n,
    )

    if not gate_passed:
        state["stagnation_count"] = 0
        _save_state(workspace_dir, state)
        result = AnalyzerResult(
            status="suppressed_candidate_count",
            descriptor=descriptor,
            candidate_count=candidate_count,
            stagnation_count=0,
            iteration_index=iteration_index,
            probe_count=len(probes),
        )
        _save_fingerprint(workspace_dir, result)
        return result

    state["stagnation_count"] = 0
    state["last_emitted_iter"] = iteration_index
    _save_state(workspace_dir, state)

    result = AnalyzerResult(
        status="emitted",
        descriptor=descriptor,
        candidate_count=candidate_count,
        stagnation_count=0,
        iteration_index=iteration_index,
        probe_count=len(probes),
    )
    _save_fingerprint(workspace_dir, result)
    return result


def reset_stagnation_on_holdout_pass(workspace_dir: Path) -> None:
    """Call when holdout gate passes to reset the stagnation counter."""
    state = _load_state(workspace_dir)
    state["stagnation_count"] = 0
    _save_state(workspace_dir, state)


def format_descriptor_for_prompt(descriptor: ShapeDescriptor) -> str:
    """Format the 2-bit descriptor for injection into the mutator prompt."""
    return (
        "COMPONENT C RESIDUAL SHAPE ANALYSIS:\n"
        "The validator has detected that your current formula achieves perfect fit "
        "on the visible data but fails on holdout points. Perturbation analysis of "
        "the residual pattern reveals the following geometric properties:\n"
        f'  - Continuity: {descriptor.continuity.upper()}\n'
        f'  - Monotonicity: {descriptor.monotonicity.upper()}\n'
        "Use this information to guide your structural search. Propose your formula "
        "with free parameters (e.g., MODEL_PARAMS = {\"k\": 1.0}) and a "
        "FIT_DECLARATION block. The parameter fitting stage will optimize constants "
        "on visible data — do NOT hardcode coefficient guesses.\n"
    )
