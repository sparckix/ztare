# Time-guarded affordance refinement result

Date: 2026-07-26  
Hypothesis ID: `H-ARC3-TIME-GUARDED-AFFORDANCE-REFINEMENT-20260726-38`  
Verdict: refuted

The clock guard eliminated the cross-time witness family, but the H35 split
did not close the quotient. Search stopped after 340 generated / 231 expanded
states at a same-time (`85 == 85`) dominance-simulation counterexample.

Both source states had equal represented factors. Their only concrete
difference was a compact 3×3 region at rows 46–48 and columns 30–32: one state
contained a structured multivalue object and the other contained background.
Under operation 1 both successors moved to the same controlled base and
renewed to the same budget, but only the object-present predecessor changed
the previously learned H35 marker bit.

This identifies an explicit mechanism: a one-shot world object controls a
later rendered marker. The projection currently observes the marker but
erases the causal object's availability. The next test must factor persistent
object availability from evidence-backed object identity and lifecycle; a
second raw cell predicate is disallowed.

Evidence:

- `time_guarded_affordance_refinement_audit_result.json`
- `time_guarded_affordance_refinement_audit.py`
