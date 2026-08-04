# Continuation-composed target search

Date: 2026-07-26  
Hypothesis ID: `H-ARC3-CONTINUATION-COMPOSED-SEARCH-20260726-43`  
Status: preregistered

## Eigenquestion

Can the common search consumer's explicit bounded continuation contract compose
the H42 product graph into an offline selected-target route?

## Hypothesis

Starting from H42's exact product projection and initial state, replaying the
best continuation after each 20,000-state exhaustion and replanning from the
resulting carrier state will return the selected edge within at most four
segments.

## Fixed procedure

1. Reconstruct the exact H42 projection, selected target, and time-guarded
   problem; require both projection and problem hashes to equal H42.
2. Consume H42's recorded selected search as immutable segment 1 and replay
   its continuation.
3. On `edge_found`, append its actions and stop.
4. On `search_budget_exhausted`, require a nonempty
   `continuation_actions`; replay it through the carrier, checking every
   successor and projection-domain admission, then replan.
5. Stop on any other status, counterexample, repeated boundary
   `(dominance_key,time)`, missing successor, or four segments.

Per-segment bounds, heuristic, interventions, target, factors, and carrier are
unchanged. No environment contact occurs.

## Success criterion

- all segment transitions/replays are admitted;
- no projection counterexample or repeated boundary occurs;
- `edge_found` occurs within four segments;
- full-route replay reaches configuration `4dd96788…`, joint code
  `c1968343…`, and the target operation.

## Kill conditions

Any failed procedure guard, no edge within four segments, or final replay
mismatch rejects the hypothesis.

## Claim boundary

A pass yields an offline route proposal only. Core promotion, route
certification against live authority, and execution remain separate.
