# GP-143 — Continuous-Chaotic Kernel Integration (Seam)

> **Seam metadata** · `seam_id:` GP-143 · `track:` engine · `status:` draft (debate open) · `last_updated:` 2026-05-08


**Status:** draft (debate open)
**Owner:** kernel-architecture
**Depends on:** GP-053 (seam-spec invariant), GP-086 (cage/kernel hardening), GP-035 (fit contract), GP-099 (vocabulary floor), INV-3 (Layer-3 exclusive), INV-10 (seam→spec→impl ordering)
**Triggered by:** gp140_ztare_discovery trajectory under aggressive judge reaching stable Method-B (MDL-W1-Pareto) across 2+ iterations at 65→72; Gemini-Pro BKZ-upgrade critique of AVOCADO Method-A scaling
**Visibility:** private (no first-mover IP leakage; promotion-track artifact)

---

## 1. Problem statement

The current ZTARE kernel fits scalar functions on grids via `compress_champion.py` + `fit_primitive.py` (BIC search over closed-form expressions). It has no code path that consumes raw trajectory data `X(t) ∈ ℝ^d` and emits mechanism-certified ODE candidates. This is the continuous-chaotic substrate gap.

gp140_ztare_discovery iter 7 (LATTICE-LE, 64) produced the first Method-A/Method-B decomposition the apparatus had not seen before; iter 12 (MRA-LLL + XPHIC, 78) and the aggressive-judge run iter 3 (AVOCADO + MDL-W1-Pareto-v2, 72) have now stabilized Method B (Wasserstein-1 on persistence diagrams + BIC Pareto) across multiple iterations while Method A remains volatile (log-radius grid → CWT adaptive → exponential Babai dilation; Gemini-Pro signals a further LLL → BKZ move for iter 7+).

The stability asymmetry is the seam trigger: Method B is ready for kernel promotion; Method A remains in the incubator until it stops mutating.

## 2. Objective

Design the kernel-integration surface that:
1. Exposes a continuous-chaotic solver pipeline to any future project declaring the substrate class.
2. Registers the Wasserstein-persistence gate as a first-class `gate_harness.py` entry per GP-086.
3. Bifurcates `autoresearch_loop.py` PHASE C / PHASE D cleanly without disturbing the scalar-function path (monotone_decay_01 neural scaling, OEIS asymptotics, Hofstadter recurrences).
4. Parameterizes over Method A so the solver can evolve (LLL / BKZ / AVOCADO / successor) without re-opening the integration seam.
5. Respects INV-3 (no LLM `def f()`; deterministic model writing) under JSONL-emitting solvers.

## 3. Invariants and constraints

- **INV-3 (Layer-3 exclusive):** when the fit primitive is enabled, the apparatus writes a deterministic `test_model.py`; LLM Python `def f()` is forbidden.
- **INV-10 (seam→spec→impl):** no `autoresearch_loop.py` edits until spec converges on this seam.
- **GP-086:** deterministic gates register in `gate_harness.py` ecosystem, not inside solver modules.
- **GP-053:** seams contain debate; specs contain blueprints; no cross-contamination.
- **GP-099 vocabulary floor:** any new primitive must declare what is reachable now; must not be injected ahead of its declared reachability.
- **Paper 5 draft.md:552 principle:** each substrate class requires a fresh A+B primitive pair. Implementation placement must be substrate-class-typed without requiring a new top-level source directory.

## 4. Forward-looking Method-A volatility note

At seam open, Method A is confirmed volatile:
- iter 11 (60): SCAFFOLD-LLL with Morlet CWT adaptive scale selection.
- iter 12 (78): MRA-LLL with CWT energy scan per-band ≥2 supports.
- iter 3 aggressive-judge (72): AVOCADO with exponential Babai dilation + online σ estimation.
- Gemini-Pro critique signals iter 7+ will likely move LLL → BKZ for tighter orthogonality defect and shrunk Babai radius.

Method B has been stable across iter 11–12 and aggressive-judge iter 1–3: MDL-W1-Pareto on persistence diagrams with BIC / Wasserstein-1 Pareto ranking. This is the surface we lock. Method A goes behind an interface that can swap implementations.

## 5. Simulated multi-turn expert panel debate

### Round 1 — opening positions

**Kernel Architect (KA):** Placement is `src/ztare/fit/continuous_chaotic/` alongside `compress_champion.py`. That directory already hosts substrate-class-specific solvers; adding a new top-level `src/ztare/substrate_generators/` would orphan a class of solvers from the directory that already defines their convention. The registry entry keyed on substrate-class lives in `primitives/primitive_library.py` (metadata-level, tokenized retrieval) while the code lives in `fit/`. These are two distinct surfaces and should not be collapsed.

**Gate Owner (GO):** Wasserstein-persistence is a gate. Per GP-086 it registers in `gate_harness.py` as a formal entry. The current `gate_harness.py` contract returns boolean pass/fail; this needs extension. Either (a) the new gate returns `GateResult(pass: bool, metric: float, threshold: float)` and legacy gates degenerate to `metric=None`, or (b) a parallel `continuous_metric_gate` interface is introduced. I lean (a); fewer concepts, back-compat via degeneracy.

**Mutator Adversary (MA):** Whatever I see in the prompt, I will game. If the Wasserstein threshold is computed from an intrinsic-noise-floor calibration routine that itself depends on candidate simulation, a hostile mutator could propose a candidate whose simulated attractor artificially shrinks the calibration floor, effectively widening its own admission envelope. The threshold derivation MUST be reference-fixed (driven by the TRUE rule or a substrate-class norm), never by the candidate-under-test.

**Operator (OP):** The dispatch mechanism must be auditable from the rubric. Existing rubric flags I can grep: `fit_score_mode: "discrete_exact"` (py_exec number theory), default scalar regression. Adding `fit_score_mode: "dynamical_lattice"` (Gemini's name) fits this convention. Rubric declares substrate; loop dispatches; operator sees the decision.

**Formal Verifier (FV):** INV-3 compliance is decisive. JSONL-emitting solvers do not produce a closed-form `def f()`; they produce a parameter matrix plus a gate result. The deterministic `test_model.py` INV-3 requires becomes a loader: read the JSONL, replay the gate, assert pass. This is INV-3-compliant by construction because no LLM-authored `def f()` is written; the apparatus writes the loader deterministically from the JSONL schema.

**Adversarial Skeptic (AS — Munger inversion):** Invert: what guarantees this kernel promotion makes the apparatus *worse*? Three failure modes. First, if Method A evolves (LLL→BKZ) and the `fit_score_mode: "dynamical_lattice"` handler is hardcoded to LLL, promotion locks in obsolescence. Second, if the gate's Wasserstein threshold is derived at kernel-integration time and never revisited, every future continuous-chaotic substrate inherits the gp140-Lorenz-holdout calibration. Third, if PHASE C bifurcation does not isolate the scalar-function path cleanly, monotone_decay_01 regresses. All three must be mitigated in the spec.

### Round 2 — response and counter-response

**KA → GO:** Agree on `GateResult` degeneracy. Concretely: `GateResult = {pass: bool, metric: Optional[float], threshold: Optional[float], producer: str, rationale: str}`. Existing boolean gates return `metric=None, threshold=None`. `wasserstein_persistence_gate` returns all four. Registration in `gate_harness.py` follows the existing pattern (decorator or explicit dict entry).

**GO → AS:** On Method A obsolescence: the gate interface is Method-A-agnostic. The gate consumes `(candidate_coefficients, observation_trajectory, threshold_calibration)` and returns the `GateResult`. Method A produces candidates in a standardized JSONL schema; whether that's LLL, BKZ, AVOCADO, or a future successor is immaterial to the gate. The volatility is absorbed by the interface, not exposed to it.

**MA → AS:** On threshold calibration hijack: the spec MUST require calibration by substrate-class reference, not by candidate-under-test. For continuous-chaotic: calibrate Wasserstein threshold against an ensemble of true-rule simulations from perturbed initial conditions, OR against a substrate-class-declared noise envelope σ via the Fasy et al. 2014 stability bound τ_W = 2σ√T. Either is reference-fixed. The candidate cannot influence its own threshold.

**OP → MA:** I would prefer the Fasy-bound route because it is stateless — the rubric declares σ, the threshold is computed once, no simulation budget consumed per project. The perturbed-IC calibration is a valid alternative when σ is not declared, but it opens a gaming vector (candidate-selected perturbation size) unless the perturbation itself is rubric-declared.

**FV → OP:** Agreed. Rubric schema extension:
```
"fit_score_mode": "dynamical_lattice",
"dynamical_lattice": {
  "substrate_class": "continuous_chaotic_polynomial_ode",
  "noise_envelope_sigma": 0.03,
  "wasserstein_admit_factor": 2.0,  // multiplier on Fasy bound
  "observation_T": 20.0,
  "grammar_degree_cap": 4             // e.g., quartic for QCCF
}
```
Noise envelope is operator-declared; threshold is `2·σ·√T·admit_factor` and cannot be influenced by the candidate.

**AS → FV:** This closes the third Munger inversion concern (candidate-influenced threshold). Remaining: PHASE C bifurcation isolation. The new path must not touch `fit_primitive.py` state. Add a function-level branch on `rubric_data["fit_score_mode"]`: `"dynamical_lattice"` dispatches to `run_continuous_chaotic_pipeline(...)`; the default path is unmodified.

### Round 3 — convergence and residual disagreement

**KA:** Converged. Solver at `src/ztare/fit/continuous_chaotic/`, gate at `src/ztare/gates/wasserstein_persistence_gate.py`, rubric flag `fit_score_mode: "dynamical_lattice"`, PHASE C bifurcation in `autoresearch_loop.py`.

**GO:** Converged on `GateResult` extension. Spec must enumerate the five boolean-returning gates currently in `gate_harness.py` and show their degenerate-form under the new dataclass, to guarantee no regression on existing rubrics.

**MA:** Residual concern. The judge must not see both the candidate AND the gate's W₁ value in numeric form; seeing the exact metric allows a mutator to propose a tuned candidate engineered to land just under threshold without structural correctness. The gate's `pass: bool` + `rationale` is mutator-visible; `metric` stays in the result JSON for operator/judge-internal use but is not injected into the mutator prompt.

**OP:** Agreed on the metric-visibility boundary. Rubric + judge see the full GateResult. Mutator sees pass/fail + rationale only.

**FV:** One last contract concern. The JSONL emitted by Method A must include a SHA-256 hash commitment BEFORE the gate runs, to preserve hash-commitment discipline (reviewer-stance requirement in gp140 evidence.txt). The gate reads the hash, verifies the candidate set has not been mutated, then runs. If hash mismatch → gate returns `pass=False, rationale="hash_commitment_violation"`.

**AS:** Satisfied. All three inversion concerns mitigated:
1. Method-A obsolescence: interface-absorbed.
2. Threshold obsolescence: rubric-declared σ plus Fasy bound.
3. PHASE C regression risk: function-level branch, default path untouched.

### Round 4 — the one thing we disagree on

**KA vs GO:** PHASE D output. KA wants PHASE D to read the gate's JSONL and emit a single-row champion + supporting pareto-front. GO wants PHASE D to emit the full certified-subset JSON and let downstream ranking (GP-119 inverter, supervisor registry) consume it.

**Debate:**
- KA: single-row champion matches existing `FitResult` shape; keeps downstream code unchanged.
- GO: the whole point of a law-certification gate is that it admits a *set*, not a single winner. Collapsing to single row loses the structural information that makes W1-PH better than argmin-L (iter 12's XPHIC explicitly demands multi-candidate preservation).

**Resolution:** PHASE D emits the full certified-subset JSON AND a designated champion (argmin-BIC within the certified subset). The existing `FitResult` shape is extended with an optional `certified_subset: list[dict]` field; legacy consumers ignore it; inverter/supervisor/ranking consumers read it. Both positions accommodated.

## 6. Design converged from debate

### 6.1 Directory and file layout

```
src/ztare/fit/
├── compress_champion.py                            # unchanged (scalar-function substrate)
├── fit_primitive.py                                # unchanged (scalar-function estimator)
└── continuous_chaotic/                             # NEW
    ├── __init__.py                                 # declares substrate_class, registry entry
    ├── generator.py                                # Method A dispatcher (LLL | BKZ | AVOCADO)
    ├── autocorrelation.py                          # τ_decorr extraction
    ├── weak_form_sindy.py                          # current reference Method A
    └── lyapunov.py                                 # ergodic / flow-invariant utilities

src/ztare/gates/
└── wasserstein_persistence_gate.py                 # NEW (GP-086 registration)

src/ztare/gates/gate_harness.py                     # EXTEND GateResult dataclass
```

### 6.2 Rubric schema extension

```json
{
  "fit_score_mode": "dynamical_lattice",
  "dynamical_lattice": {
    "substrate_class": "continuous_chaotic_polynomial_ode",
    "noise_envelope_sigma": 0.03,
    "observation_T": 20.0,
    "wasserstein_admit_factor": 2.0,
    "grammar_degree_cap": 4,
    "method_a_variant": "weak_form_sindy_auto_radii",
    "method_a_params": { "n_centers": 40, "thresholds": [0.01, 0.02, 0.05, 0.1, 0.15, 0.2, 0.3] }
  }
}
```

### 6.3 GateResult contract (gate_harness extension)

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

Legacy boolean gates return `metric=None, threshold=None, extra={}`. Wasserstein-persistence returns all four.

### 6.4 Method A → Method B interface (JSONL pipe)

One JSON object per line:
```json
{
  "candidate_id": "uuid",
  "method_a_variant": "weak_form_sindy_auto_radii",
  "coefficient_matrix": [[...],[...],[...]],
  "covariance_matrix": [[...], ...],
  "basis_labels": ["1","x","y","z","x*x","x*y","x*z","y*y","y*z","z*z"],
  "nonzero_terms_k": 10,
  "residual_norm_per_dim": [..., ..., ...],
  "threshold_lambda": 0.02,
  "sha256_commitment": "hex...",
  "metadata": {"tau_decorr": 0.16, "radii_grid": [...]}
}
```

SHA-256 is computed over the sorted-key JSON of every other field in the candidate record.

### 6.5 Mutator-visibility boundary (MA residual)

- Mutator sees: `fit_score_mode`, rubric declarations, evidence.txt (including GateResult rationale text).
- Mutator does NOT see: raw `metric` or `threshold` numeric values per-candidate (hides the exact distance-to-admission).
- Judge sees: full GateResult including metric and threshold (for scoring the primitive's claim quality).
- Operator sees: everything (debugging).

### 6.6 PHASE C bifurcation (sketch, spec provides exact patch)

```python
# autoresearch_loop.py, ~line 3070 (PHASE C entry)
if rubric_data.get("fit_score_mode") == "dynamical_lattice":
    from src.ztare.fit.continuous_chaotic import run_pipeline
    fit_result = run_pipeline(
        trajectory=_load_holdout_trajectory(),
        dt=rubric_data["dynamical_lattice"]["observation_dt"],
        rubric_params=rubric_data["dynamical_lattice"],
    )
    # fit_result: FitResult with certified_subset populated
else:
    # legacy path: fit_parameters(...) unchanged
    fit_result = fit_parameters(...)
```

### 6.7 PHASE D INV-3 compliance path

Apparatus writes a deterministic `test_model.py` that:
1. Loads the certified-subset JSONL emitted by PHASE C.
2. Recomputes the SHA-256 commitment for each candidate; asserts match.
3. Replays the Wasserstein-persistence gate against the locked holdout.
4. Asserts `verdict == True` for the designated champion.

This is INV-3-compliant because no LLM-authored Python function body is written; the entire `test_model.py` is produced by the apparatus from the JSONL schema.

## 7. Alignment check with 72 champion

Iter-3 aggressive-judge champion is AVOCADO (Method A) + MDL-W1-Pareto-v2 (Method B).

- **Method B alignment:** full. Seam 6.3 / 6.4 accommodate MDL-W1-Pareto directly. BIC → L_bits field; Wasserstein-1 → metric field; Pareto ranking → `extra.pareto_rank`.
- **Method A alignment:** interface-level. AVOCADO's exponential Babai dilation + online σ estimation fits under `method_a_variant: "avocado_adaptive_lattice"` with its own params block. The JSONL schema is Method-A-agnostic; AVOCADO just populates `method_a_variant` and `metadata.babai_radius_estimate` fields.
- **Gemini-BKZ forward nudge:** if iter 7+ replaces LLL with BKZ, `method_a_variant: "bkz_reduced_lattice"` slots in. The seam's interface absorbs the Method-A evolution; the gate does not need re-specification.

**Conclusion:** seam is aligned with the 72 champion AND forward-compatible with the BKZ nudge. No spec rewrite required on Method-A evolution.

## 8. Open questions deferred to spec (6.x numbered)

- **OQ-1:** Exact `GateResult` migration path for the five existing boolean gates. Spec enumerates each, writes the degenerate form, runs regression against fixtures.
- **OQ-2:** Whether `certified_subset` in `FitResult` is list[CandidateRecord] or `Path` to the JSONL file. Memory vs disk tradeoff at ~100 candidates.
- **OQ-3:** Whether the rubric's `method_a_variant` allows "auto" (dispatch by heuristic) or must be explicit. Explicit recommended for audit, auto convenient for operator.
- **OQ-4:** Hash-commitment replay order in PHASE D — before or after gate verdict replay. Spec decides.
- **OQ-5:** How `fit_score_mode: "dynamical_lattice"` interacts with GP-078 Component D topology synthesizer. Component D operates on AST composition of scalar-function primitives; continuous-chaotic substrate bypasses Component D entirely. Spec makes this explicit.

## 9. Promotion gate (non-normative)

This seam should not be implemented until:
- gp140 reaches 3 consecutive iterations ≥ 85 under the aggressive judge on the current substrate, AND
- At least one cross-substrate validation run (second continuous-chaotic project with different holdout parameters), AND
- Cross-model blind panel (different mutator family + different judge family) does not invert the champion.

Current state: iter 3 aggressive-judge = 72. Two iters shy of a single ≥85, nine iters shy of three consecutive. Seam work is preparatory; implementation waits.

## 10. Reviewer stance

Reject any spec that:
- Puts solver code in `src/ztare/primitives/` (metadata retrieval only).
- Embeds the Wasserstein gate inside the solver module (GP-086 violation).
- Touches `autoresearch_loop.py` before spec convergence (INV-10 violation).
- Exposes raw metric/threshold to the mutator prompt (gaming vector).
- Locks the solver interface to a specific Method A variant (Method-A obsolescence risk).

Accept any spec that satisfies all Round-3 convergence points AND resolves OQ-1 through OQ-5.

---

**Convergence declaration:** this seam is CONVERGED on placement, gate contract, dispatch, interface, INV-3 path, mutator-visibility. Spec inherits the convergence points; OQ-1 through OQ-5 are the only items spec resolves.
