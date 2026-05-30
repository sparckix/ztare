# PDE Estimate Workbench Pack

- Target: `C7-upper fresh viscous-alignment-surplus no-reuse budget`
- Field: `navier-stokes vorticity-direction`
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

## Inequality Prefilter

- `int_fresh (A_visc)_+ |omega|^2 <= R_n - R_{n+1} + eps nu int_fresh |grad omega|^2`: `passed=False` [{'kind': 'endpoint_unbound', 'unbound': ['eps', 'A_visc', 'grad', 'int_fresh', 'R_n', 'omega']}]

## Curriculum

- Suggested transforms: DIMENSION_REDUCE, LINEARIZE

## Anti-Tautology Notes

- This pack nominates context only; it does not prove a theorem.
- If a rubric already enables GP-180 / framer / in-loop falsifiers, use those core ZTARE mechanisms rather than duplicating them here.
- Treat `Prop` fields as declarations unless paired with paid proof fields.
- Promote only compiler-checked Lean, concrete falsifiers, or named missing primitives.