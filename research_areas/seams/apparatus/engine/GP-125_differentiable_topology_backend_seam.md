# GP-125 — Differentiable Topology Backend for ZTARE

**Status:** OPEN — implementation pending panel review
**Opened:** 2026-04-22
**Category:** Apparatus / Engine / Architectural Extension

## The Insight

ZTARE is already a dual-loop optimizer:
- Outer loop: LLM proposes structural topology (discrete)
- Inner loop: SciPy fits parameters (continuous)
- Gates verify quality
- BIC penalizes complexity

The Millennium Problem gap is NOT the architecture — it's the
BACKEND. The inner loop uses curve_fit on 1D scalar templates.
For operator discovery (Hilbert-Pólya), it needs torch.linalg.eigh
on N×N matrix generators with backpropagation.

Same brain, different hands.

## The Implementation

### New file: `src/ztare/fit/operator_backend.py`

A PyTorch/JAX backend that:
1. Takes a parameterized matrix generator function
2. Computes eigenvalues via differentiable eigh
3. Computes loss = MSE(eigenvalues, target_spectrum) + α·complexity
4. Runs AdamW gradient descent on the generator parameters
5. Returns the optimized parameters and loss

### Route in compress_champion.py

```python
if rubric_data.get("substrate_type") == "continuous_operator":
    from src.ztare.fit.operator_backend import fit_operator
    result = fit_operator(generator_fn, target_spectrum, ...)
else:
    # existing curve_fit path
```

### Matrix generator templates

The LLM proposes the STRUCTURE (which terms appear in the matrix).
The backend fits the PARAMETERS (coefficients, boundary conditions).

Initial template family: Berry-Keating Hamiltonian
  H(p) = x·p + p·x + V(x; params)
where V(x; params) is a potential parameterized by a few coefficients.

### Complexity ledger (Goodhart defense)

BIC penalty on generator complexity = number of terms in V(x).
A diagonal matrix with 10,000 explicit zeros has k=10,000 → BIC ≈ ∞.
A 5-parameter generator with low BIC that matches the zeros IS the
discovery.

## Technical Risks

1. **Eigenvalue gradient instability:** When eigenvalues cross
   (degenerate), gradients of eigh explode to NaN. Fix: add small
   regularization ε·I to the matrix, or use SVD-based stable
   eigendecomposition.

2. **Trivial solution (Goodhart):** LLM proposes diagonal matrix
   populated with the zeros. BIC penalty handles this — diagonal
   matrix has k = N parameters.

3. **Local minima:** The loss landscape for operator parameters
   may have many local minima. Fix: multi-start optimization
   (ZTARE already has GP-095 multi-start).

4. **Compute:** eigh on N×N matrix is O(N³). For N=1000 (matching
   1000 zeros), each forward pass is ~1 second. 1000 gradient steps
   = ~17 minutes. Feasible on M2.

## Connection to Existing Architecture

| ZTARE Component | Current (1D scalar) | New (operator) |
|----------------|--------------------|--------------------|
| LLM outer loop | Proposes template f(n) | Proposes generator G(params) |
| Inner loop | curve_fit on f(n) | AdamW on eigh(G(params)) |
| Evidence | n → z(n) | target eigenvalue spectrum |
| Gates | max residual < threshold | eigenvalue MSE < threshold |
| BIC | k = # params in f | k = # params in G |
| Inverter | Attacks the form | Attacks the generator |
| Lean REPL | Verifies f(n) identity | Verifies G is Hermitian |

## Constant Recognition Pipeline (2026-04-22)

### The Precision Trap (Gemini Pro)

AdamW converges to ~7 stable digits. PSLQ needs 15-20 digits to avoid
the "Law of Small Numbers" — a spurious fraction like 43π/211 fits
7 digits perfectly but diverges at digit 8. This is a structural risk,
not a corner case.

### Three-Stage Pipeline

```
Stage 1: AdamW convergence     → ~7 digits  (operator_backend.py)
Stage 2: L-BFGS precision polish → ≥15 digits (constant_recognition.py)
Stage 3: PSLQ + mpmath.identify → algebraic identifications
```

**Stage 2 details:** Freeze topology, switch from AdamW to L-BFGS
(quasi-Newton, quadratic convergence), run in float64. L-BFGS uses
approximate Hessian — near a minimum it converges quadratically
vs AdamW's linear. Tolerance set to 1e-15.

**Stage 3 details:** Two parallel strategies:
1. `mpmath.identify()`: pattern matching against fractions, algebraics,
   exp/log of algebraics, combinations of base constants
2. `PSLQ`: integer relation detection against a basis of 20 constants
   (π, e, γ, ln2, √2, √3, ζ(3), Catalan, etc.)

Confidence scoring: relation complexity × coefficient size × digits
available. Refuses to run below 8 stable digits.

### Implementation

New file: `src/ztare/fit/constant_recognition.py`
- `precision_polish()`: L-BFGS in float64
- `recognize_constants()`: PSLQ + identify on param dict
- `full_pipeline()`: polish → recognize (recommended entry point)

### Exit Conditions for GPU Run

| Loss plateau   | Action                                    |
|---------------|-------------------------------------------|
| > 0.3         | Manifold lacks complexity → expand grammar |
| 0.01 – 0.3    | Viable but not converged → more restarts   |
| < 0.01        | Run precision_polish() → constant_recognition |
| < 1e-6        | High-confidence PSLQ viable                |

### Reality Check (2026-04-22, Gemini Pro)

Current best loss across 5 generators: ~0.23. Constant recognition
activates at < 0.01 — two orders of magnitude away. The recognition
pipeline is correct engineering but cannot bail out the current run.

The bottleneck is the GENERATOR GRAMMAR, not parameter precision.
Sierra-Townsend-style logarithmic confinement is mathematically too
restrictive to encode the GUE statistics of Riemann zeros. Breaking
below 0.05 requires:

1. **Larger matrix size** (N=500-1000) — cost O(N³)
2. **Different operator class** — modified BBM, Berry-Connes,
   or Connes' adelic operator
3. **Per-zero adaptive optimization** — decompose spectrum into
   spectral bands, fit each separately
4. **Non-polynomial confinement** — log-based or number-theoretic
   potentials (Mangoldt function, prime-counting step functions)

The constant recognition is a DEPOSIT for when the grammar catches up.

### Checkbox

- [x] operator_backend.py (Berry-Keating + spectral basis)
- [x] GPU script (riemann_operator_search_gpu.py)
- [x] constant_recognition.py (PSLQ + identify + L-BFGS polish)
- [ ] GPU run on Lambda A100/GH200
- [ ] Precision polish on best result
- [ ] Constant recognition on polished coefficients
- [ ] Lean stub for any high-confidence identification

## Debate Questions for Panel

1. Is the differentiable eigenvalue backend the right primitive,
   or should we use a different continuous optimization target?
2. Can the existing BIC penalty adequately prevent Goodhart on
   operator search, or do we need a graph-depth metric?
3. Is Berry-Keating the right starting family, or should we search
   over a broader class of operators?
4. How many zeros do we need to match for the result to be
   meaningful? 100? 1000? 10000?
5. Does this require GPU, or can MPS handle N=1000 eigh?
