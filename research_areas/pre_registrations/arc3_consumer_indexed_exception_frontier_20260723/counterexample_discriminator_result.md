# Counterexample coordinate audit result

Date: 2026-07-25

Parent hypothesis: `counterexample_discriminator_hypothesis.md`

## Outcome

The candidate coordinate-refinement route is falsified for the newest
counterexample.

The sealed boundary source at index 15 and its sole law-owned counterpart at
active-row index 324 have:

- byte-identical rendered observations;
- the same operation (`2`);
- zero differing raw cells;
- equal values for every existing `FiberFactors` field.

The base relation therefore reports one non-commuting source-operation class,
but no observation-derived factor can separate its two consequences.

Evidence:
`counterexample_discriminator_audit_result.json`.

## Verdict

The rendered observation is not a Markov state for this operation. Adding
another coordinate computed only from the current frame cannot repair the
relation. The object must expand to a history-bearing state or predictive
equivalence class, after which observation coordinates may be quotiented only
when their future operation consequences commute.
