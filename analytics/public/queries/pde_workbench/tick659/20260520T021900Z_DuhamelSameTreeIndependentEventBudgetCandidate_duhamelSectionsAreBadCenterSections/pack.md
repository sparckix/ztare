# PDE Estimate Workbench Pack

- Target: `DuhamelSameTreeIndependentEventBudgetCandidate`
- Field: `duhamelSectionsAreBadCenterSections`
- Scope: RD caller over existing ZTARE primitives; not a replacement workbench
- Gap type: `UNKNOWN` (low)

## Target Context

- Found in workmap: `True`
- File: `ns_L3_multiscale_YM_rescaled_increments`
- Downstream users: `None`
- Priority: `None`

## Mathlib Shelf

- (none found; this is a thin-zone warning)

## Auxiliary Families

- (none selected)

## Inequality Prefilter

- `EventWeightedGainPrefix_N <= DuhamelSameTreeReserveBudget`: `passed=True` []

## Curriculum

- Suggested transforms: DIMENSION_REDUCE, LINEARIZE

## Anti-Tautology Notes

- This pack nominates context only; it does not prove a theorem.
- If a rubric already enables GP-180 / framer / in-loop falsifiers, use those core ZTARE mechanisms rather than duplicating them here.
- Treat `Prop` fields as declarations unless paired with paid proof fields.
- Promote only compiler-checked Lean, concrete falsifiers, or named missing primitives.