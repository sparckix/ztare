# Availability CEGAR closure

Date: 2026-07-26  
Hypothesis ID: `H-ARC3-AVAILABILITY-CEGAR-CLOSURE-20260726-37`  
Status: refuted

## Eigenquestion

Does bounded counterexample-guided splitting recover the finite availability
carrier needed for sound selected-target search without naming or preselecting
its rendered region?

## Hypothesis

Starting from the accepted projection and H35 receipt, iteratively adding one
canonical availability bit per new no-known-factor commutation counterexample
will reach `edge_found` for the H30-selected target within at most eight
refinements.

## Fixed loop

1. Validate a `dominance_simulation_failed` receipt with a bounded nonempty
   changed-cell list and no changed current factor.
2. Canonically order the cells and their left/right value tuples.
3. Choose the lexicographically least tuple as reference; append one boolean
   equality bit to `one_shot_availability`.
4. Recompute projection identity from parent identity, split identity, and
   receipt lineage.
5. Rerun the exact H35 selected-target search from scratch.
6. Stop on `edge_found`, non-refinable/noncommuting receipt, repeated split,
   ordinary exhaustion, or eight splits.

No target field, action valence, route prefix, game vocabulary, or environment
result enters a split. Search bounds remain depth 180 and 20,000 states per
iteration.

## Discriminating test

Record each split, cells, canonical reference, search counts, and next receipt.
On `edge_found`, replay through the carrier and require selected configuration
`4dd96788…`, joint code `c1968343…`, and the target edge.

## Success criterion

- every split separates its producing witness and is new;
- closure occurs within eight splits;
- final search returns `edge_found` with no counterexample;
- replay reaches the exact selected factors/code;
- no environment contact.

## Kill conditions

Reject on malformed or repeated receipt, a counterexample whose states already
differ on represented factors, ordinary frontier/bound exhaustion, more than
eight splits, final replay mismatch, target leakage, or environment contact.

## Claim boundary

A pass certifies bounded generic CEGAR closure and an offline route. Core
promotion and live execution remain separate.
