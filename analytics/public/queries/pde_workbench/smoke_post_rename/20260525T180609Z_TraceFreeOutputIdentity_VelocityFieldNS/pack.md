# PDE Estimate Workbench Pack

- Target: `TraceFreeOutputIdentity`
- Field: `VelocityFieldNS`
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

## ZTARE Primitive Suggestions

- `pec_a` Auxiliary Comparison Object Construction: construct the missing carrier/test object explicitly before proving estimates (src/ztare/gates/auxiliary_object_declaration_gate.py)
- `pec_e` Sharpness / Failure-Witness Construction: build the hostile witness or sharpness model before accepting the route (no shipped gate)
- `pec_l` Symbol / Cancellation Coercivity Audit: audit that the claimed signed/symbol cancellation pays the positive target quantity (no shipped gate)

## Estimate Skeletons

- (none selected)

## Residual Normal Form

- Classification: `NEW`
- Best match: `ScaleFreshCriticalDebit` (score `0.0`)
- Required next move: supply a same-carrier fresh no-reuse theorem or a new packet family that defeats nested reuse

## Limit-Passage Gate

- (not selected)

## Moment Ratio Surplus

- (not requested)

## Bounded Ratio Support

- (not requested)

## Finite Prefix Selection

- (not requested)

## Event Family Binding

- (not requested)

## Positive Variation Bridge

- (not requested)

## Positive Variation Quotient Wash

- (not requested)

## Quotient Minimal Carrier Payment

- (not requested)

## Quadratic Quotient Descent

- (not requested)

## Nonadaptive Source Selection

- (not requested)

## No-Rebilling Freshness

- (not requested)

## Same-Carrier Packing

- (not requested)

## Metric Covering Selection

- (not requested)

## Pi-Group Forcing

- (not requested)

## Dimensionless Exponent Source

- (not requested)

## Linear Observable Coercivity

- (not requested)

## Single-Spend Carrier Audit

- (not requested)

## Receipt Strength Audit

- (not requested)

## Owner-Preimage Prefix Gate

- (not selected)

## Scaled-Transfer Numeric Receipt Gate

- (not selected)

## Owner-Geometry Core Receipt Gate

- (not selected)

## Fresh-Annular Anti-Laundering Gate

- (not selected)

## Fresh-Annular Non-Disguise Gate

- (not selected)

## Fresh-Annular Innovation Gate

- (not selected)

## Section-Fixed Unsigned Variation Gate

- (not selected)

## Inequality Prefilter

- (no candidate inequalities supplied)

## Curriculum

- Suggested transforms: DIMENSION_REDUCE, LINEARIZE

## Anti-Tautology Notes

- This pack nominates context only; it does not prove a theorem.
- If a rubric already enables GP-180 / framer / in-loop falsifiers, use those core ZTARE mechanisms rather than duplicating them here.
- Treat `Prop` fields as declarations unless paired with paid proof fields.
- Promote only compiler-checked Lean, concrete falsifiers, or named missing primitives.