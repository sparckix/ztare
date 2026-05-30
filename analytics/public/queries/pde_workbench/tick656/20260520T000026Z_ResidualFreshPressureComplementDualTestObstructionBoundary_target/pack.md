# PDE Estimate Workbench Pack

- Target: `ResidualFreshPressureComplementDualTestObstructionBoundary`
- Field: ``
- Scope: RD caller over existing ZTARE primitives; not a replacement workbench
- Gap type: `UNKNOWN` (low)

## Target Context

- Found in workmap: `False`
- File: `None`
- Downstream users: `None`
- Priority: `None`

## Mathlib Shelf

- (none found; this is a thin-zone warning)

## Auxiliary Families

- `exponential_majorant`: B(x) = C₁ exp(C₂ φ(x))  for some convex φ
- `conformal_weight`: w(x) = (1 + |x|²)^α  for some α tuned to scaling
- `cutoff_partition`: ψ ∈ C_c^∞(ℝ^d), 0 ≤ ψ ≤ 1, ψ = 1 on K, supp(ψ) ⊂ K'
- `test_function_oscillating`: φ_n(x) = α_n cos(λ_n x) χ_n(x)  (disjointly supported)
- `sign_changing_periodic`: ψ_per(x) = Σ_k a_k χ_{[kπ, (k+1)π]}(x)  with Σa_k = 0

## Inequality Prefilter

- `PressureCollarPairing_Q <= C * (HarmonicReserve_Q + ChildCollarReserve_Q + InheritedPressureReserve_Q + MomentCancellationDefect_Q)`: `passed=True` []

## Curriculum

- Suggested transforms: DIMENSION_REDUCE, LINEARIZE

## Anti-Tautology Notes

- This pack nominates context only; it does not prove a theorem.
- If a rubric already enables GP-180 / framer / in-loop falsifiers, use those core ZTARE mechanisms rather than duplicating them here.
- Treat `Prop` fields as declarations unless paired with paid proof fields.
- Promote only compiler-checked Lean, concrete falsifiers, or named missing primitives.