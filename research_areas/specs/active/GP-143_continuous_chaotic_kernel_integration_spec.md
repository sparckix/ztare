# GP-143 — Continuous-Chaotic Kernel Integration (Spec)

**Status:** draft
**Seam:** `research_areas/private/seams/engine/GP-143_continuous_chaotic_kernel_integration_seam.md` (converged)
**Invariants inherited:** INV-3, INV-10, GP-053, GP-086, GP-099

This spec is a blueprint. No debate. Debate lives in the seam. If you want to change the design, update the seam and reflect the resolution here.

---

## 1. Deliverables

1. **New package** `src/ztare/fit/continuous_chaotic/` with solver code.
2. **New gate module** `src/ztare/gates/wasserstein_persistence_gate.py`.
3. **Extended** `src/ztare/gates/gate_harness.py`: `GateResult` dataclass, backward-compatible registration.
4. **Rubric schema** extension: `fit_score_mode: "dynamical_lattice"` block.
5. **`autoresearch_loop.py`** PHASE C bifurcation and PHASE D INV-3 path.
6. **Regression fixture** `src/ztare/validator/tests/continuous_chaotic_fixture_regression.py`.

## 2. Package `src/ztare/fit/continuous_chaotic/`

### 2.1 `__init__.py`

Exports:
```python
from .pipeline import run_pipeline
from .types import ContinuousChaoticResult, CandidateRecord

SUBSTRATE_CLASS = "continuous_chaotic_polynomial_ode"

METHOD_A_REGISTRY = {
    "weak_form_sindy_auto_radii": "weak_form_sindy.run_weak_form",
    "avocado_adaptive_lattice": "avocado.run_avocado",   # stub for iter-3 72 champion
    "bkz_reduced_lattice": "bkz.run_bkz",                # stub for Gemini forward nudge
}
```

Registers `SUBSTRATE_CLASS` in `src/ztare/primitives/primitive_library.py` via an approved-primitive JSON at `global_primitives/approved/GP-143_continuous_chaotic.json` (tokenized retrieval, metadata only; no code).

### 2.2 `types.py`

```python
@dataclass
class CandidateRecord:
    candidate_id: str
    method_a_variant: str
    coefficient_matrix: list[list[float]]
    covariance_matrix: Optional[list[list[float]]]
    basis_labels: list[str]
    nonzero_terms_k: int
    residual_norm_per_dim: list[float]
    threshold_lambda: float
    sha256_commitment: str
    metadata: dict[str, Any]

@dataclass
class ContinuousChaoticResult:
    method_a_variant: str
    candidates: list[CandidateRecord]
    certified_subset: list[CandidateRecord]
    champion: Optional[CandidateRecord]
    pareto_front: list[CandidateRecord]
    gate_result: "GateResult"
    tau_decorr: float
    noise_envelope_sigma: float
    wasserstein_threshold: float
```

### 2.3 `pipeline.py` — `run_pipeline()` contract

**Decisive constraint (added 2026-04-24, layer 3 of RMS Chaos Trap enforcement):**
`run_pipeline()` docstring and implementation MUST explicitly reject any Method-A variant whose fitness rule is trajectory-level RMS over window T·λ_max > 5. Acceptable fitness forms enumerated in `docs/concepts/chaos_substrate_primitives.md` Principle 1. Violation of this constraint at runtime: `run_pipeline()` raises `ValueError("GP-143 RMS-chaos-trap violation: fitness_rule=%s on chaotic substrate")`. Enforced via static check of the rubric's `method_a_params` block AND via runtime inspection of the solver's fitness-evaluation call site.



```python
def run_pipeline(
    trajectory: np.ndarray,       # shape (N, d)
    dt: float,
    rubric_params: dict,          # rubric_data["dynamical_lattice"]
    holdout_path: Optional[Path] = None,  # for deterministic replay
) -> ContinuousChaoticResult:
    ...
```

Steps:
1. Load Method A via `METHOD_A_REGISTRY[rubric_params["method_a_variant"]]`.
2. Extract τ_decorr via `autocorrelation.decorrelation_time(trajectory, dt)`.
3. Run Method A → list[CandidateRecord].
4. For each candidate: compute SHA-256 commitment, populate `sha256_commitment`.
5. Invoke `wasserstein_persistence_gate.run_gate(candidates, trajectory, rubric_params)` → `GateResult`.
6. Filter to certified subset (GateResult.verdict per-candidate via `extra.per_candidate_verdicts`).
7. Select champion = argmin BIC within certified subset.
8. Compute Pareto front over (BIC, Wasserstein-1).
9. Return `ContinuousChaoticResult`.

### 2.4 `weak_form_sindy.py`, `autocorrelation.py`, `lyapunov.py`

Ports from `projects/lorenz_bridge_test/apparatus_candidate/apparatus_v5_correct.py`. Interface preserved; imports updated to kernel paths.

## 3. Gate module `src/ztare/gates/wasserstein_persistence_gate.py`

### 3.1 Public API

```python
def run_gate(
    candidates: list[CandidateRecord],
    observation_trajectory: np.ndarray,
    rubric_params: dict,
) -> GateResult:
    ...
```

Behavior:
1. Compute `pd_obs = persistence_diagram(observation_trajectory)` once.
2. Compute `threshold = 2 * sigma * sqrt(T) * admit_factor` (Fasy 2014 bound, rubric-declared σ and T, factor from rubric).
3. For each candidate:
   a. Simulate attractor from locked holdout IC.
   b. Compute `pd_cand = persistence_diagram(sim_traj)`.
   c. Compute `W1 = wasserstein_1(pd_cand, pd_obs)` (H₀ + H₁ summed).
   d. `verdict = W1 <= threshold`.
4. Compute ensemble-level verdict: `GateResult.verdict = any(per_candidate_verdicts)`.
5. `GateResult.metric = min(W1 per candidate)`.
6. `GateResult.extra["per_candidate"] = [...]`.

### 3.2 Hash-commitment verification

Before running step 3 for each candidate:
```python
computed = sha256(json.dumps(candidate_without_sha, sort_keys=True).encode()).hexdigest()
if computed != candidate.sha256_commitment:
    # hash violation: verdict false, rationale = "hash_commitment_violation"
```

### 3.3 Gate registration in `gate_harness.py`

```python
REGISTERED_GATES["wasserstein_persistence"] = {
    "module": "src.ztare.gates.wasserstein_persistence_gate",
    "function": "run_gate",
    "returns_continuous_metric": True,
    "producer": "GP-143",
}
```

## 4. `gate_harness.py` extension

### 4.1 `GateResult` dataclass

```python
@dataclass
class GateResult:
    gate_id: str
    verdict: bool
    metric: Optional[float] = None
    threshold: Optional[float] = None
    producer: str = ""
    rationale: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)
```

### 4.2 Legacy gate migration (OQ-1 resolution)

The five existing boolean gates migrate by wrapping their existing `bool` return in `GateResult(verdict=existing_bool, metric=None, threshold=None)`. Regression fixture at `src/ztare/validator/tests/gate_harness_fixture_regression.py` ensures:
- Each legacy gate returns `GateResult` with identical `verdict` to pre-migration boolean.
- Existing consumers that check `result is True` or `if result:` still pass (via `GateResult.__bool__ = lambda self: self.verdict`).

### 4.3 Backward-compatible `__bool__`

```python
def __bool__(self) -> bool:
    return self.verdict
```

## 5. Rubric schema extension

### 5.1 New keys

Two threshold-derivation routes, resolved at run time in precedence order:

1. **Calibrated-floor route** (preferred for chaotic substrates): rubric declares `wasserstein_noise_floor` from a pre-run calibration (W1 between true-rule simulations from perturbed ICs). Threshold = `admit_factor * noise_floor`. Correct for intrinsic attractor-sampling variance.
2. **Fasy-bound fallback** (for additive-observation-noise substrates): rubric declares `noise_envelope_sigma` and `observation_T`. Threshold = `admit_factor * 2 * sigma * sqrt(T)`.

Refinement driven by smoke test: the Fasy bound is derived for additive observation noise. Chaotic-attractor intrinsic variance (W1 ≈ 170 for the lorenz_bridge_test holdout) vastly exceeds it, causing false negatives on the true rule. The calibrated-floor route is the correct primary path for this substrate class.

```json
{
  "fit_score_mode": "dynamical_lattice",
  "dynamical_lattice": {
    "substrate_class": "continuous_chaotic_polynomial_ode",
    "observation_dt": 0.01,
    "observation_T": 20.0,

    "wasserstein_noise_floor": 172.0,
    "wasserstein_admit_factor": 2.0,

    "noise_envelope_sigma": 0.03,

    "grammar_degree_cap": 4,
    "method_a_variant": "weak_form_sindy_auto_radii",
    "method_a_params": {
      "n_centers": 40,
      "thresholds": [0.01, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30],
      "n_radii": 5
    }
  }
}
```

Precedence: if `wasserstein_noise_floor` is present, it wins. Otherwise fall back to Fasy bound.

### 5.2 Rubric validator extension

`src/ztare/rubrics/review_rubric.py` adds a validator:
```python
if rubric.get("fit_score_mode") == "dynamical_lattice":
    assert "dynamical_lattice" in rubric
    dl = rubric["dynamical_lattice"]
    for key in ("substrate_class", "observation_dt", "observation_T",
               "noise_envelope_sigma", "wasserstein_admit_factor",
               "method_a_variant"):
        assert key in dl, f"dynamical_lattice missing required key: {key}"
    assert dl["method_a_variant"] in METHOD_A_REGISTRY
```

### 5.3 OQ-3 resolution: explicit only

`method_a_variant: "auto"` is rejected. Rubric must name the variant. Operator audit requirement.

## 6. `autoresearch_loop.py` PHASE C bifurcation

### 6.1 Exact patch location

At PHASE C entry (~line 3070, after `rubric_data` is loaded and before the current `fit_parameters(...)` call).

### 6.2 Patch body

```python
# GP-143: dynamical_lattice bifurcation (continuous-chaotic substrate)
if rubric_data.get("fit_score_mode") == "dynamical_lattice":
    from src.ztare.fit.continuous_chaotic import run_pipeline
    cc_params = rubric_data["dynamical_lattice"]
    trajectory = _load_dynamical_lattice_holdout(project_dir, cc_params)
    cc_result = run_pipeline(
        trajectory=trajectory,
        dt=cc_params["observation_dt"],
        rubric_params=cc_params,
        holdout_path=project_dir / "_holdout_locked",
    )
    _fit_result = _adapt_continuous_chaotic_to_fit_result(cc_result)
    # _fit_result is a FitResult with:
    #   .coefficients = cc_result.champion.coefficient_matrix
    #   .certified_subset = cc_result.certified_subset
    #   .gate_result = cc_result.gate_result
else:
    # legacy path (scalar-function substrate)
    _fit_result = fit_parameters(...)
```

### 6.3 New helpers

- `_load_dynamical_lattice_holdout(project_dir, cc_params)`: loads trajectory from `{project_dir}/_holdout_locked/trajectories/traj_*.npy` and `truth.json`. Raises if `observation_dt` mismatch.
- `_adapt_continuous_chaotic_to_fit_result(cc_result)`: constructs existing `FitResult` shape with the extension fields populated.

## 7. `autoresearch_loop.py` PHASE D INV-3 path

### 7.1 Deterministic `test_model.py` writer

When `cc_result.champion` is not None, PHASE D writes `{project_dir}/test_model.py`:

```python
# AUTO-GENERATED by GP-143 PHASE D INV-3 writer. Do not edit by hand.
import json
from pathlib import Path
import hashlib
import numpy as np

def test_champion_certified():
    certified = json.loads(Path(__file__).parent.joinpath(
        "certified_subset.json").read_text())
    champion_id = "{champion_id}"
    champion = next(c for c in certified if c["candidate_id"] == champion_id)

    # Hash-commitment replay (OQ-4 resolution: BEFORE verdict replay)
    payload = {k: v for k, v in champion.items() if k != "sha256_commitment"}
    import json as _j
    computed = hashlib.sha256(
        _j.dumps(payload, sort_keys=True).encode()).hexdigest()
    assert computed == champion["sha256_commitment"], \
        "hash_commitment_violation — candidate mutated post-emission"

    # Gate verdict replay
    from src.ztare.gates.wasserstein_persistence_gate import run_gate
    holdout = np.load(Path(__file__).parent.joinpath(
        "_holdout_locked/trajectories/traj_5.npy"))
    result = run_gate([champion], holdout, {{RUBRIC_PARAMS}})
    assert result.verdict, f"gate verdict replay failed: {{result.rationale}}"

if __name__ == "__main__":
    test_champion_certified()
    print("GP-143 PHASE D replay: PASS")
```

`{champion_id}` and `{RUBRIC_PARAMS}` are interpolated by the writer. No LLM produces any line; the writer is deterministic Python in `autoresearch_loop.py`.

### 7.2 OQ-4 resolution

Hash-commitment replay runs BEFORE gate verdict replay. If the candidate is mutated post-emission, the gate reruns on a different object than the one committed; correct failure is "hash_commitment_violation," not a gate-level false pass. This is a strictly-more-paranoid ordering.

## 8. OQ-2 resolution: `certified_subset` is `list[CandidateRecord]` in `FitResult`; the JSONL on disk is written in parallel for PHASE D replay. ~100 candidates × ~2 KB each = ~200 KB in memory. Acceptable.

## 9. OQ-5 resolution: `fit_score_mode: "dynamical_lattice"` bypasses Component D entirely. Component D operates on AST composition of scalar-function primitives; the continuous-chaotic pipeline does not synthesize grammar. Explicit guard at PHASE C entry:

```python
if rubric_data.get("fit_score_mode") == "dynamical_lattice":
    if rubric_data.get("enable_component_d"):
        raise RuntimeError(
            "GP-143: Component D is incompatible with dynamical_lattice; "
            "disable enable_component_d in rubric.")
```

## 10. Regression fixture

`src/ztare/validator/tests/continuous_chaotic_fixture_regression.py`:

1. Loads the locked `lorenz_bridge_test` holdout.
2. Constructs a rubric with `fit_score_mode: "dynamical_lattice"`.
3. Calls `run_pipeline(...)`.
4. Asserts:
   - `len(result.certified_subset) >= 1`
   - `result.champion.nonzero_terms_k == 10` (matches true rule sparsity)
   - `result.gate_result.verdict == True`
   - `result.gate_result.metric < result.wasserstein_threshold`
5. Hash-commitment round-trip: writes JSONL, re-reads, re-runs gate, asserts identical verdict.

## 11. Implementation ordering (respects INV-10)

1. Seam converges (DONE — this spec references it as converged).
2. Spec approved (this document).
3. Implement `src/ztare/gates/gate_harness.py` `GateResult` extension + migration.
4. Implement `src/ztare/gates/wasserstein_persistence_gate.py`.
5. Implement `src/ztare/fit/continuous_chaotic/` package (port from `apparatus_candidate/`).
6. Implement rubric validator extension.
7. Implement `autoresearch_loop.py` PHASE C/D patches.
8. Write regression fixture; run.
9. Paper 5 reference-implementation lineage pointer updated.

Do NOT execute steps 4-9 until gp140 promotion gate clears (3 consecutive iters ≥ 85, cross-substrate validation, cross-model panel).

## 12. Acceptance criteria

- All five existing boolean gates pass their regression fixtures after `GateResult` migration.
- Regression fixture (Section 10) passes on lorenz_bridge_test holdout.
- `test_model.py` writer produces a file that executes successfully and emits "GP-143 PHASE D replay: PASS".
- `autoresearch_loop.py` legacy path (scalar-function substrate: run monotone_decay_01 rubric) produces bit-identical output to pre-patch.
- Mutator prompt does NOT contain raw `metric` or `threshold` numerics from the Wasserstein gate (mutator-visibility boundary holds).

## 13. Rollback

If any acceptance criterion fails:
- Revert `gate_harness.py` to the pre-migration boolean-returning contract via a feature flag `GATE_RESULT_DATACLASS_ENABLED = False`.
- Skip the `dynamical_lattice` branch; leave the code in place but dormant.
- Reopen the seam; add a Round 5 debate section.
