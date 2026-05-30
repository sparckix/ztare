# GP-098 Evidence Compressor: Variance-Stabilizing Transform Enumeration

## Status

Draft — opened 2026-04-19

## Seam

`research_areas/private/seams/GP-098_evidence_compressor_seam.md`

## Scope

- Deterministic evidence preprocessor that enumerates variance-stabilizing transforms (VSTs) on Z before synthesis
- Three exact-inverse transforms: identity (passthrough), log, sqrt
- Holdout evaluation in original coordinates (non-negotiable)
- Pipeline placement: GP-098 → GP-097 → 1D synthesis
- Inverse-transform chain for decompression

Does not cover:

- Kinematic Compressor for ODE substrates (deferred to v2, when a real ODE substrate demands it)
- ODE detection (Durbin-Watson or sequential-vs-random) — deferred
- Local-std VST (violates exact-inverse constraint)
- Breusch-Pagan pre-filter (deferred to WB-001 product mode)
- Changes to gate thresholds (relative gates are Phase 2 logged diagnostic)
- Changes to Component D grammar or 1D synthesizer internals

## Decision

Enumerate three variance-stabilizing transforms on evidence Z values, run the engine under each, inverse-transform results, evaluate all candidates on holdout in original coordinates. The holdout adjudicates noise model selection. No model selection logic, no noise model assumptions.

## Problem

ZTARE's engine assumes homoscedastic noise: absolute-residual gates compare |Z_pred - Z_obs| against a fixed epsilon. This breaks on two common real-world data regimes:

1. **Multiplicative noise** (variance scales with mean): photon counting, economic data, biological growth. High-Z points have larger variance. Absolute gates systematically penalize the high-magnitude regime, executing the true law.

2. **Poisson noise** (variance scales with sqrt of mean): count data, radioactive decay, traffic counts. Similar failure mode but with sqrt scaling.

The homoscedasticity assumption is embedded in three layers:
- `global_gates.py`: absolute residual thresholds
- `gate_harness.py`: extrapolation_gap gate
- GP-097 `manifold_compressor.py`: intra-bin Z-variance threshold for ratio collapse validation

### Why transforms, not gate reform

Fixing the gates (relative thresholds) addresses the symptom. Transforming the data addresses the root cause: the noise profile. With a VST, the transformed data *is* homoscedastic, so the existing gates work correctly. The engine, gates, and synthesizer all operate in a coordinate system where their assumptions hold.

Gate reform (relative residual diagnostic) is Phase 2 — collect data under VSTs first, then evaluate whether relative gates add discriminating power beyond what VSTs provide.

## Why It Matters

Without variance stabilization, ZTARE will fail on any substrate with magnitude-dependent noise. This is the majority of real-world physics data. The engine will reject the true law because the gates interpret natural variance as structural error.

GP-097's ratio sweep inherits this failure: the intra-bin Z-variance threshold (`_VARIANCE_COLLAPSE_THRESHOLD = 0.02`) is absolute. Valid ratio collapses on heteroscedastic data will exceed this threshold in high-value bins, producing false WALL_ENTANGLEMENT exits.

## Constraints

1. **Zero oracle contamination.** Transforms use only Z values from evidence. No GT, no variable names, no domain knowledge.
2. **Exact deterministic inverse.** Each transform must have an exact inverse: `Z = inverse(transform(Z))` with no approximation. This is decisive for holdout evaluation in original coordinates.
3. **Holdout in original coordinates.** The final candidate is evaluated by inverse-transforming the predicted Z' back to original Z, then computing residuals against original evidence. Holdout in transformed space is insufficient.
4. **Engine-agnostic.** The compressor warps evidence before the engine sees it. The engine, GP-097 manifold compressor, gates, and synthesizer operate unchanged.
5. **Enumerate, don't select.** No noise model selection. Try all three transforms, let holdout adjudicate.

## Architecture

```text
evidence.txt → (X, Z) pairs
     │
     ▼
┌─────────────────────────────────────────────────┐
│  evidence_compressor.py                         │
│                                                 │
│  transforms = [                                 │
│    ("identity", Z,        Z'),                  │
│    ("log",      log(Z),   exp(Z')),             │
│    ("sqrt",     sqrt(Z),  Z'²),                 │
│  ]                                              │
│                                                 │
│  For each (name, forward, inverse):             │
│  ├─ Apply forward to all Z values               │
│  ├─ Yield transformed evidence                  │
│  └─ Store inverse for decompression             │
│                                                 │
│  Returns: list of TransformedEvidence objects    │
└─────────────────────────────────────────────────┘
     │
     ▼ (one per transform)
GP-097 Manifold Compressor (if N-D)
     │
     ▼
1D Synthesizer (Component D)
     │
     ▼
Inverse-transform predicted Z' → Z
     │
     ▼
Holdout evaluation in original coordinates
     │
     ▼
Best candidate across all transforms wins
```

## Design

### Transform Table

| Name | Forward | Inverse | Assumption | Domain guard |
|------|---------|---------|------------|-------------|
| identity | Z' = Z | Z = Z' | Homoscedastic | None |
| log | Z' = log(Z) | Z = exp(Z') | Multiplicative noise | Z > 0 |
| sqrt | Z' = sqrt(Z) | Z = Z'² | Poisson noise | Z ≥ 0 |

### Domain Guards

- **log**: Requires all Z > `Z_FLOOR` (default `Z_FLOOR = 1e-6`). If any Z ≤ `Z_FLOOR`, skip this transform. The floor prevents extreme Z' values (log(1e-10) = -23) that distort curve_fit initialization. Don't shift data to satisfy the guard — shifting changes the noise model and the inverse is no longer exact.
- **sqrt**: Requires all Z ≥ 0. If any Z < 0, skip this transform. **Inverse guard**: after synthesis, if any predicted Z' < 0, flag a warning — squaring negative Z' produces correct magnitude but loses the sign. The synthesizer's output sign must be validated before inverse application.
- **identity**: Always valid.

### Return Types

```python
@dataclass
class TransformedEvidence:
    """Evidence after applying a VST."""
    transform_name: str           # "identity" | "log" | "sqrt"
    evidence: list[tuple]         # transformed (X1, ..., Z') tuples
    original_evidence: list[tuple] # original (X1, ..., Z) tuples
    inverse_fn: Callable[[float], float]  # Z' → Z
    forward_fn: Callable[[float], float]  # Z → Z'

@dataclass
class TransformResult:
    """A synthesis result in original coordinates."""
    transform_name: str
    expression_original: str      # expression in original Z coordinates
    expression_transformed: str   # expression in Z' coordinates
    params: dict[str, float]
    holdout_residual: float       # max |Z_pred - Z_obs| in original coords
```

### Integration with autoresearch_loop.py

The compressor does NOT run the engine itself. It prepares transformed evidence that the existing pipeline consumes:

```python
from ztare.validator.evidence_compressor import enumerate_transforms

# At evidence load time:
transforms = enumerate_transforms(evidence, ind_vars)
# transforms is a list of TransformedEvidence objects

# The main loop picks one transform per iteration (or runs all):
for t in transforms:
    # Pass t.evidence to the existing pipeline
    # After synthesis, inverse-transform: Z = t.inverse_fn(Z_predicted)
    # Evaluate on holdout in original coordinates
```

**Wiring options (choose one at integration time):**

1. **Sequential enumeration**: Run full pipeline on identity first. If holdout fails, try log. If holdout fails, try sqrt. Cheapest but misses cases where non-identity is strictly better but identity also passes.

2. **Parallel quick-scan**: Run 3 quick iterations under each transform. Commit full budget to the winning transform. Costs 3× for the scan phase but avoids wasting full budget on wrong transform. **Convergence metric for scan**: best visible max|residual| after 3 iterations. The transform whose best-so-far champion has the lowest max|residual| on visible evidence wins the budget. This is a proxy — the final holdout evaluation in original coordinates is the real adjudication, applied at the end.

3. **Full enumeration**: Run full pipeline under all three. Compare holdout scores. Most expensive but most correct.

Recommendation: **Option 2 (parallel quick-scan)** for v1. Three quick iterations cost ~$6 total. The scan identifies which transform converges fastest. Full budget goes to the winner.

### GP-097 Interaction

The evidence compressor transforms Z values only. X values are unchanged. This means:
- GP-097's variable slicing, topology matching, and ratio sweep operate on transformed Z'
- GP-097's holdout evaluation operates on transformed Z'
- The final decompression chain is: GP-097 inverse (compressed → N-D in Z' space) → GP-098 inverse (Z' → Z)

**Inverse composition contract**: GP-097 outputs `assembly_expression` (a string) and `assembly_params` (a dict). This expression predicts Z' (transformed). The evidence compressor applies its scalar inverse to each predicted value: `Z_pred = inverse_fn(Z'_pred)`. This is a pointwise scalar operation — no string rewriting of the expression is needed. The `expression_original` field in `TransformResult` is for human documentation only; the actual inverse path is `eval(assembly_expression) → inverse_fn()`.

### Holdout Adjudication

**For synthetic validation substrates**: GT is available. Holdout Z_obs comes from GT at holdout points. Adjudication: max |inverse_fn(Z'_pred) - Z_obs_original| across holdout points.

**For real-evidence runs**: No GT at holdout points. Two adjudication strategies:
1. **Leave-one-out on visible evidence**: Hold out 20% of visible evidence, train on 80%, evaluate inverse-transformed predictions against held-out Z_obs in original coordinates. Repeat for each transform.
2. **Farther-tail extrapolation**: If `evidence_farther_tail.txt` exists, evaluate inverse-transformed predictions against farther-tail Z_obs. This is the standard ZTARE holdout mechanism and requires no modification.

Strategy 2 is preferred when farther-tail evidence exists (most rubric configurations). Strategy 1 is the fallback for rubrics without farther-tail.

### Validation Substrates

Three synthetic substrates, each with known GT:

**Substrate 1 — Homoscedastic baseline:**
```
Z = a * exp(-b * X) + c
noise: N(0, sigma) with sigma = 0.1 (constant)
```
Expected: identity transform wins. Log/sqrt should not improve.

**Substrate 2 — Multiplicative noise:**
```
Z = a * exp(-b * X) + c
noise: N(0, sigma(X)) with sigma(X) = 0.1 * Z(X)  (10% of signal)
```
Expected: log transform wins. Identity penalizes high-Z regime.

**Substrate 3 — Poisson noise:**
```
Z = a * X^2 + b * X + c  (all Z > 0)
noise: Poisson-like: N(0, sqrt(Z(X)))
```
Expected: sqrt transform wins. Identity penalizes high-Z regime.

**Validation criteria:**
- Each substrate: best holdout score should come from the correct transform
- Identity baseline: log/sqrt should not degrade homoscedastic data (max 5% holdout increase vs identity)
- Wrong-transform penalty: applying log to homoscedastic data should produce worse holdout than identity (demonstrating that enumeration + holdout correctly selects)

## Implementation Phases

### Phase 1 (this spec): VST enumeration module
- `evidence_compressor.py`: ~150 lines
- Three transforms with exact inverses
- Domain guards (Z > 0 for log, Z ≥ 0 for sqrt)
- `enumerate_transforms()` returns list of TransformedEvidence
- Unit tests on three synthetic substrates

### Phase 2 (future): Relative gate diagnostic
- Add `|residual| / max(|Z_obs|, epsilon_floor)` to gate output
- No behavior change — logged diagnostic only
- Collect data for 3 sandbox runs
- Evaluate whether relative gates add discriminating power beyond VSTs

### Phase 3 (future): Kinematic Compressor
- Savitzky-Golay differentiation of evidence
- ODE detection (Durbin-Watson or sequential-vs-random fit)
- Pipeline ordering: VST → Kinematic → GP-097 → 1D synthesis
- Only built when a real ODE substrate demands it

### Phase 4 (future, WB-001): Cost optimization
- Breusch-Pagan pre-filter for heteroscedasticity detection
- Skip non-identity transforms when test accepts homoscedasticity at p < 0.05
- Reduces product cost by 2-3× for homoscedastic substrates

## File Map

| File | Purpose |
|------|---------|
| `src/ztare/validator/evidence_compressor.py` | Module: transforms, domain guards, enumeration |
| `tests/validator/test_evidence_compressor.py` | Three synthetic substrates + edge cases |
| `research_areas/private/seams/GP-098_evidence_compressor_seam.md` | Debate log (9 turns) |
| `research_areas/private/specs/active/GP-098_evidence_compressor_spec.md` | This spec |

## Risks

1. **Log/sqrt distort function topology.** If Z = sin(X) (negative values), log is undefined. Domain guards catch this, but edge cases (Z very close to 0) may produce numerically unstable transforms. Mitigation: skip transforms where any Z is within epsilon of the domain boundary.

2. **Transform-dependent convergence.** The engine may converge to different families under different transforms (e.g., power law under log becomes linear). This is a feature, not a bug — the holdout adjudicates.

3. **Cost multiplier.** Three transforms × full runs = 3× cost. Mitigated by quick-scan approach (3 iterations per transform, ~$6 total, then full budget on winner).
