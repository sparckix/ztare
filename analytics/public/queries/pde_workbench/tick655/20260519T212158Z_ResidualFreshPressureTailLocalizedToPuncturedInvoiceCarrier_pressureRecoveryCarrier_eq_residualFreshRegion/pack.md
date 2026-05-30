# PDE Estimate Workbench Pack

- Target: `ResidualFreshPressureTailLocalizedToPuncturedInvoiceCarrier`
- Field: `pressureRecoveryCarrier_eq_residualFreshRegion`
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

- `dual_test_construct`: v solving L*v = g, then ⟨u, g⟩ = ⟨Lu, v⟩

## Inequality Prefilter

- `pressureRecoveryCarrier(eventIndex(Q)) = freshRegion(Q)`: `passed=True` []

## Curriculum

- Suggested transforms: DIMENSION_REDUCE, LINEARIZE

## Anti-Tautology Notes

- This pack nominates context only; it does not prove a theorem.
- If a rubric already enables GP-180 / framer / in-loop falsifiers, use those core ZTARE mechanisms rather than duplicating them here.
- Treat `Prop` fields as declarations unless paired with paid proof fields.
- Promote only compiler-checked Lean, concrete falsifiers, or named missing primitives.