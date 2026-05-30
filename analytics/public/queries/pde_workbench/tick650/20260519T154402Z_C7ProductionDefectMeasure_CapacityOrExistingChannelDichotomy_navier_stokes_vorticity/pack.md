# PDE Estimate Workbench Pack

- Target: `C7ProductionDefectMeasure_CapacityOrExistingChannelDichotomy`
- Field: `navier-stokes-vorticity`
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

- (none selected)

## Inequality Prefilter

- `c * r_Q <= Cap_omega(Q) or existing_channel(Q); sum_Q Cap_omega(Q) <= C * nu * enstrophy; int_high (A_visc)_+ q (q-k)_+ <= eps * D_n + C * Y_n^(1+beta)`: `passed=True` []

## Curriculum

- ERROR: target not found in workmap

## Anti-Tautology Notes

- This pack nominates context only; it does not prove a theorem.
- If a rubric already enables GP-180 / framer / in-loop falsifiers, use those core ZTARE mechanisms rather than duplicating them here.
- Treat `Prop` fields as declarations unless paired with paid proof fields.
- Promote only compiler-checked Lean, concrete falsifiers, or named missing primitives.