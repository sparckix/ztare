# Availability CEGAR closure result

Date: 2026-07-26  
Hypothesis ID: `H-ARC3-AVAILABILITY-CEGAR-CLOSURE-20260726-37`  
Verdict: refuted

The bounded loop consumed all eight refinements without finding the selected
edge. Every split was new, target-independent, and separated its producing
witness, but the final search still returned
`dominance_simulation_failed`.

The first receipt was the same-time two-cell witness from H35. After splitting
it, seven further receipts appeared:

- six merged states were reached at different carrier times;
- one additional same-time witness differed over a structured 3×3 region;
- changed regions included adjacent two-row strips, compact 3×3 geometry, and
  line-shaped geometry rather than one stable set of independent cells;
- every receipt still reported zero changed represented factors.

Generated-state counts grew as high as 5,122 before another unsound merge,
showing that the splits restored distinctions but did not identify a closed
state object. The pointwise Boolean model is therefore rejected. The receipts
concentrate the remaining ambiguity into two missing identities: carrier time
or phase, because the predictor is time-dependent, and a same-time structured
world object. The next test must preserve time identity and refine only
same-time residuals; adding more independent cell bits under the old quotient
is disallowed.

Evidence:

- `availability_cegar_closure_audit_result.json`
- `availability_cegar_closure_audit.py`
