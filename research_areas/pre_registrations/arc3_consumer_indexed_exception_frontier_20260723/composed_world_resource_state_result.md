# Composed world/resource state result

Date: 2026-07-26  
Hypothesis ID: `H-ARC3-COMPOSED-WORLD-RESOURCE-STATE-20260726-41`  
Verdict: refuted at inference

The audit stopped before either search. The registered construction inferred
the secondary depleted value as the modal value over the whole world region.
That mode is `4`, while every variable secondary cell has values `{3,8}`.
Consequently all twelve cells failed the required background-binary gate.

The projection already provides the correct invariant anchor:
`budget_live_value = 11`. Across every primary budget group, the complete
observed value alphabet is exactly `{11,3}`. The unique non-live value `3` is
therefore the evidence-backed depleted rendering. Inferring it from the
primary scalar transports the scalar mechanism; taking a global world mode
does not.

No target search ran and no claim about product-state sufficiency follows.
The next test changes only this inference operator.

Evidence:

- `composed_world_resource_state_audit.py`
- primary budget evidence: 1,405,106 depleted cells and 1,379,998 live cells
  across the bank
