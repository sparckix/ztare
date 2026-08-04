# Time-guarded affordance refinement

Date: 2026-07-26  
Hypothesis ID: `H-ARC3-TIME-GUARDED-AFFORDANCE-REFINEMENT-20260726-38`  
Status: refuted

## Eigenquestion

Does preserving clock identity, together with the one same-time split already
forced by H35, close the selected-target quotient?

## Hypothesis

The H30-selected target is reachable within the unchanged depth-180 /
20,000-state bounds when target search:

1. uses `(dominance_key(state), time)` because the carrier has no
   time-translation certificate; and
2. appends only the target-independent H35 same-time discriminator to the
   accepted projection.

## Discriminating test

Reconstruct the H35 discriminator from its recorded counterexample, preserve
time in the target consumer's dominance key, and rerun the exact selected
search. Replay any route and require configuration `4dd96788…`, joint code
`c1968343…`, and the target operation.

## Success criterion

- the H35 split is reconstructed and separates its source witness;
- search returns `edge_found` without a projection counterexample;
- replay stays admissible and reaches the exact selected factors and joint
  code;
- no environment contact.

## Kill conditions

Reject on cross-time merging after the guard, a new same-time projection
counterexample, ordinary exhaustion, bound exhaustion, replay mismatch,
target leakage, or environment contact.

## Claim boundary

A pass yields an offline route and evidence for restoring clock identity in
the target consumer. Core promotion and live execution remain separate.
