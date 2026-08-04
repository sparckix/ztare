# Counterexample-owned availability refinement result

Date: 2026-07-26  
Hypothesis: `H-ARC3-COUNTEREXAMPLE-AVAILABILITY-REFINEMENT-20260726-36`  
Result artifact: `counterexample_availability_refinement_audit_result.json`

## Verdict

Refuted as a single-split repair.

The H35-derived bit over `(61,57),(62,57)` separated the original divergent
states. Rerunning selected-target search then produced a new commutation
counterexample after 293 generated / 190 expanded states. The new witness
differed at adjacent cells `(61,56),(62,56)` while every current factor,
including the first refinement bit, agreed.

Operation `2` gave the two states different successor availability images.
The first split therefore identified one coordinate of a larger finite
availability carrier, not the whole carrier.

## Next discriminator

Use the commutation guard as a bounded CEGAR producer. Each new no-known-factor
counterexample contributes one symmetric, target-independent availability
split; rerun search until it commutes, returns an edge, repeats a split, or
reaches a fixed cap. This tests mechanism closure rather than guessing the
remaining rendered region.

## Claim boundary

The single split remains a valid separator for H35 but is insufficient for
selected-target search. No core refinement API was promoted.
