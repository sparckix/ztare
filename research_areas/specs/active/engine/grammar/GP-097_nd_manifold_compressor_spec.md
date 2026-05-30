# GP-097 N-D Manifold Compressor: Topological Coordinate Descent

## Status

Draft — opened 2026-04-19

## Seam

`research_areas/private/seams/GP-097_nd_manifold_compressor_seam.md`

## Scope

- Orchestration layer that compresses N-D datasets to 1D manifolds before synthesis
- Pass 1: Topological Coordinate Descent (slice-based separation of variables)
- Pass 2: Ratio Sweep (pairwise variable combination collapse)
- Pass 3: Entanglement Wall exit (WALL_ENTANGLEMENT)
- Decompression of synthesized 1D law back to original N-D coordinates
- N-D farther-tail holdout evaluation
- Five synthetic validation substrates

Does not cover:

- Changes to the 1D synthesizer (Component D) or its AST grammar
- LLM-guided compression (Phase C, flagged, not in core pipeline)
- Power-law scaling (Z = X₂^α · g(X₁)) — deferred to Pass 1.5 variant
- More than 3 independent variables
- Cross-term gate promotion to hard block (needs ≥3 empirical runs)

## Decision

Compress N-D datasets to 1D manifolds deterministically before they reach the topology synthesizer. Use Topological Coordinate Descent (sequential variable isolation via slicing) as the primary mechanism, with a pairwise ratio sweep fallback. No LLM involvement. All gates evaluate the final assembled law in original N-D coordinates, not in compressed space.

## Problem

ZTARE's topology synthesizer was designed for 1D substrates. Naively extending it to N-D triggers three independent failure modes:

1. **Combinatorial death.** Depth-1 AST search in 1D is O(|Prims|² × |Ops|). In 2D it exponentiates because each composition must decide whether to use f(X), g(Y), or cross f(X) with g(Y).

2. **Sparsity death.** 24 data points give dense 1D coverage but empty 3D voids. High-parameter rational forms warp to hit sparse points without revealing true shape. The farther-tail gate loses discrimination power.

3. **Optimizer death.** Levenberg-Marquardt (curve_fit) with nonlinear N-D composed terms produces pathologically singular Jacobians. Near-universal `Covariance could not be estimated` failures.

## Why It Matters

Without a compression layer, ZTARE cannot address any N-D physics substrate: fluid dynamics, thermodynamics, coupled reaction kinetics, multi-variable materials science. The 1D results (KWW, Langevin, OEIS) demonstrate the engine works. N-D is the generalization test.

## Constraints

1. **Zero oracle contamination.** The compressor must use only evidence pairs (X₁, X₂, ..., Z). No GT function calls. No variable name interpretation.
2. **Deterministic.** No LLM involvement in the compression pipeline (contamination via variable name → domain retrieval). LLM-guided compression is a flagged Phase C accelerator only.
3. **Existing gates preserved.** The 1D synthesizer, holdout gate, parsimony gate, and contamination gate must operate unchanged on the compressed manifold.
4. **Holdout in original space.** The final holdout evaluation must be on the decompressed N-D law in original coordinates. Holdout in compressed space is insufficient (compression may absorb errors that extrapolation would reveal).
5. **GP-076 GT dependency removed.** The existing divergence sweep uses `f_true` (GT). The production compressor must replace this with `Z_observed - f_dominant(u,v)`.

## Options

### Option A — Naive N-D Synthesizer Upgrade

Extend Component D's AST grammar to handle multi-variable compositions directly.

**Pros:** Single architecture for 1D and N-D.

**Cons:** Combinatorial, sparsity, and optimizer deaths are fundamental, not engineering problems. The AST search space exponentiates. The holdout gate loses power. curve_fit fails. Three independent unsolvable problems.

**Verdict:** Rejected. The three deaths are mathematical limits, not engineering gaps.

### Option B — Phase 0 Manifold Compressor (original proposal)

New standalone preprocessing module that tests canonical compressions, selects the best, and passes a compressed 1D manifold to the synthesizer.

**Pros:** Clean separation. Handles all compression types.

**Cons:** Overbuilt. Creates a new architectural layer when orchestration of existing machinery suffices. "Phase 0" framing implies a large module when the actual work is ~200 lines.

**Verdict:** Superseded by Option C (Gemini's inversion).

### Option C — Topological Coordinate Descent + Ratio Sweep

Run the existing 1D synthesizer N times via sequential variable isolation (coordinate descent). Fallback to pairwise ratio sweep if separation fails. Entanglement wall exit if neither works.

**Pros:**
- Reuses existing 1D synthesizer unchanged
- All existing gates apply
- Entanglement detection comes free (1D engine hits WALL_LIBRARY_INSUFFICIENT)
- Computationally trivial (a few extra 1D synthesis runs)
- Zero contamination risk
- Catches separable laws (majority of physics) in Pass 1 and ratio-coupled laws in Pass 2

**Cons:**
- Cannot handle genuinely entangled N-D laws — but this is correct behavior (WALL_ENTANGLEMENT)
- Requires slicing (Y-binning) which needs sufficient data density per bin

**Verdict:** Recommended.

## Recommendation

Adopt Option C.

## Implementation Sketch

### Module: `src/ztare/validator/manifold_compressor.py`

New module (~200 lines). Clean interface:

```python
@dataclass
class CompressedManifold:
    evidence_1d: list[tuple[float, float]]  # (U, Z) pairs
    compression_map: str  # human-readable: "multiplicative, X first"
    compression_type: str  # "additive" | "multiplicative" | "ratio_collapse"
    inverse_map: Callable  # deterministic: 1D expression → N-D expression
    compression_residual: float  # cross-term metric: max |∂²R/∂X_i∂X_j| (via finite differences)
    original_vars: list[str]  # ["X", "Y"]
    compressed_var: str  # "U"

class EntanglementWall:
    pass_1_failures: list[str]  # why each separation failed
    pass_2_failures: list[str]  # why each ratio collapse failed
    message: str  # "WALL_ENTANGLEMENT: variables genuinely entangled"

def compress(
    evidence: list[tuple[float, ...]],  # N-D evidence tuples
    ind_vars: list[str],
) -> CompressedManifold | EntanglementWall:
    ...
```

### Pass 1: Topological Coordinate Descent

For each ordered pair of variables (X_i, X_j):

1. **Slice by X_j.** Bin the dataset by X_j values. For each bin (X_j = y₀ ± ε), extract the (X_i, Z) pairs.

2. **Library sweep on X_i slice (not full synthesis).** Run `fit_primitive.py` library sweep: fit all 32 primitives against the slice via curve_fit. Pick the top 3 by RMSE. Cost: ~1 second per slice, no LLM calls. The full autoresearch loop only runs on the final compressed manifold, not on intermediate slices.

3. **Topology consistency check.** Run the same library sweep on a *different* X_j bin (X_j = y₁ ± ε). If the top-fitting primitive family matches across slices (same expression template, different parameters), g(X_i) is verified as separable along X_i. If topology changes between slices, this is an entanglement signal — fall through to Pass 2.

4. **Compute residual.**
   - Additive: R = Z - g(X_i)
   - Multiplicative: R = Z / g(X_i)

5. **Library sweep on X_j residual.** Run the 32-primitive library sweep on (X_j, R) to find h(X_j).

6. **Assemble.**
   - Additive: Z = g(X_i) + h(X_j)
   - Multiplicative: Z = g(X_i) · h(X_j)

7. **N-D holdout evaluation.** Evaluate the assembled law on holdout points generated at 1.5× the bounding box in all dimensions simultaneously (corner extrapolation). Only assemblies that pass this holdout survive.

All variable orderings are tested exhaustively (2 orderings for 2 vars, 6 for 3 vars). Both additive and multiplicative assemblies are tested. The holdout selects the winner.

**Intermediate 1D holdout gates are bypassed.** The intermediate g(X_i) is a building block, not a final answer. Only the assembled N-D law is holdout-evaluated.

### Pass 2: Ratio Sweep

Only runs if Pass 1 produces no assembly that passes the N-D holdout.

1. **Generate candidate collapse variables.** For each pair (X_i, X_j), try:
   - U = X_i / X_j
   - U = X_i · X_j
   - U = X_i² / X_j
   - U = X_j / X_i
   - U = X_i · X_j²

2. **1D collapse check.** For each candidate U, compute U for all evidence points. Bin the U values and compute Z-variance within each bin. If max intra-bin variance < threshold, the collapse is valid. This is structural (tests whether similar U values produce similar Z values), not fit-based, and immune to the Padé trap.

3. **1D synthesis on U.** Pass (U, Z) to the existing synthesizer. Find f(U).

4. **Decompress.** Express the law in original coordinates: Z = f(X_i/X_j) or Z = f(X_i·X_j), etc. The decompression is exact (algebraic substitution).

5. **N-D holdout evaluation.** Same holdout as Pass 1 — bounding-box extension, corner extrapolation, original coordinates.

### Pass 3: Entanglement Wall

If neither Pass 1 nor Pass 2 produces a law that passes the N-D holdout, emit `EntanglementWall` with diagnostic information about which separations were attempted and why each failed.

This is a high-value negative result: the dataset represents a non-separable system. The engine correctly refuses to produce a confidently wrong separable approximation.

### Integration with autoresearch_loop.py

The orchestrator call sits at the top of the synthesis loop, before the mutator:

```python
from src.ztare.validator.manifold_compressor import compress, CompressedManifold, EntanglementWall

if len(ind_vars) > 1:
    compression_result = compress(evidence, ind_vars)
    if isinstance(compression_result, EntanglementWall):
        # Log and halt — non-separable system
        print(f"WALL_ENTANGLEMENT: {compression_result.message}")
        break
    # Replace evidence with compressed 1D manifold
    evidence_1d = compression_result.evidence_1d
    ind_vars_1d = [compression_result.compressed_var]
    # Store inverse map for decompression after synthesis
    _inverse_map = compression_result.inverse_map
```

After synthesis completes, decompress the result:

```python
if _inverse_map is not None:
    final_expression = _inverse_map(synthesized_1d_expression)
    # Evaluate on N-D holdout in original coordinates
    holdout_result = evaluate_nd_holdout(final_expression, original_evidence, holdout_points)
```

### Decompression Contract

The inverse map is a pure algebraic substitution:

| Compression | Inverse map |
|---|---|
| Additive, X first | Z = g(X) + h(Y) → substitute directly |
| Multiplicative, X first | Z = g(X) · h(Y) → substitute directly |
| Ratio collapse, U = X/Y | Z = f(U) → Z = f(X/Y) |
| Ratio collapse, U = X·Y | Z = f(U) → Z = f(X·Y) |

The inverse map operates on the expression string (AST transformation), not on numerical values. It is deterministic and exact.

### N-D Holdout Gate

Holdout points are generated at the corners of the extended bounding box:

```python
def generate_nd_holdout(evidence, ind_vars, extension_factor=1.5):
    """Generate holdout points at 1.5x bounding box in all dimensions."""
    bounds = {}
    for var_idx, var in enumerate(ind_vars):
        values = [e[var_idx] for e in evidence]
        lo, hi = min(values), max(values)
        width = hi - lo
        bounds[var] = (lo - extension_factor * width, hi + extension_factor * width)

    # Corner points: all combinations of extended bounds
    corners = list(itertools.product(
        *[(bounds[v][0], bounds[v][1]) for v in ind_vars]
    ))
    # Add axis-extension points (extend one dim, keep others at midpoint)
    for var_idx, var in enumerate(ind_vars):
        mid = [(bounds[v][0] + bounds[v][1]) / 2 for v in ind_vars]
        for extreme in [bounds[var][0], bounds[var][1]]:
            pt = list(mid)
            pt[var_idx] = extreme
            corners.append(tuple(pt))
    return corners
```

Starting multiplier: 1.5×. Calibrate after 3 sandbox runs by logging the holdout distance at which each candidate first diverges from GT.

### Validation Substrates

Five synthetic 2D functions, all absent from physics textbooks:

| # | Function | Type | Expected outcome |
|---|---|---|---|
| 1 | Z = tanh(X)/X + Y²/exp(Y) | Additive separable | Pass 1 succeeds |
| 2 | Z = exp(-X²) · sin(Y)/(1+Y²) | Multiplicative separable | Pass 1 succeeds |
| 3 | Z = 1/(1 + exp(-(X/Y))) | Ratio-coupled | Pass 2 succeeds |
| 4 | Z = sin(X·Y) + exp(X/Y) | Genuinely entangled | WALL_ENTANGLEMENT |
| 5 | Z = tanh(X)/X + Y²/exp(Y) + 0.01·sin(X·Y) | Near-separable (stress test) | Pass 1 succeeds but cross-term residual logged |

Substrate 5 is the Padé-trap-at-compression-layer test: does the engine detect a small cross-term or confidently report an almost-correct additive decomposition?

### Bin Width Heuristic for Y-Slicing

Minimum 5 data points per bin. Maximum bins = ceil(N_unique_Y_values / 3). If the dataset has fewer than 15 total points, slicing is infeasible — skip Pass 1 and fall through to Pass 2 directly.

### Cost Analysis

| Step | Cost (2 variables) |
|---|---|
| Pass 1 intermediate slicing (library sweep) | ~4 sweeps × 1 sec = 4 sec, $0.00 |
| Pass 1 assembly + N-D holdout | ~1 sec, $0.00 |
| Pass 2 ratio sweep (if needed) | ~10 candidates × 1 sec = 10 sec, $0.00 |
| Final full synthesis on compressed manifold | 1 run × 10 iters × ~$0.50 = $5.00 |
| **Total** | **~15 sec + $5.00** |

The compression phase is effectively free. Only the final synthesis on the winning compressed manifold incurs LLM costs.

## Open Questions

1. **Holdout multiplier calibration.** 1.5× is a starting point. After 3 sandbox runs, review holdout distance vs. candidate divergence to calibrate.
2. **Cross-term gate promotion.** The mixed-partial-derivative gate (Turn 6, seam) starts as a logged diagnostic. Promote to hard gate after ≥3 runs show prevalence above 10%.
3. **Topology consistency tolerance.** "Same expression template" is the starting definition. If empirical runs show parameter-count-only matching is more robust, revisit.
4. **Power-law scaling.** Z = X₂^α · g(X₁) is a natural extension of multiplicative separation. Deferred but should be the first Pass 1.5 addition after initial validation.
