# Counterexample-owned availability refinement

Date: 2026-07-26  
Hypothesis ID: `H-ARC3-COUNTEREXAMPLE-AVAILABILITY-REFINEMENT-20260726-36`  
Status: preregistered

## Eigenquestion

Does the exact H35 commutation witness identify the sole missing state
coordinate needed to search the selected joint affordance soundly?

## Hypothesis

Refining the projection with one evidence-owned boolean availability
coordinate derived from the two divergent cells will prevent the H35 merge
and allow selected-target search to return `edge_found` under unchanged
bounds.

## Fixed refinement

- consume only H35's `dominance_simulation_failed` counterexample;
- require same-time merge, no changed compiled factor, and a nonempty bounded
  changed-cell list;
- form left and right value tuples over the changed coordinates;
- choose the lexicographically least tuple as a canonical reference, without
  assigning task valence;
- append one factor
  `(counterexample_availability_<receipt hash>, observed_tuple == reference)`
  to `one_shot_availability`;
- recompute projection identity from the parent projection, cells, reference,
  and H35 evidence ref;
- change no carrier prediction, target key, action set, goal predicate,
  heuristic, dominance vector, feasibility rule, or search bound.

This is an audit-local projection wrapper. Core promotion requires a passing
result and regression tests.

## Discriminating test

Rerun only the H30-selected target with the repaired admissibility and refined
projection. Replay any returned route, recompute the H30 joint code, and
report whether another commutation counterexample appears.

## Success criterion

- the H35 counterexample is structurally valid and the new bit separates its
  two images;
- selected search returns `edge_found` within depth 180 / 20,000 states;
- no new projection counterexample;
- replay reaches target base, configuration `4dd96788…`, and joint code
  `c1968343…`;
- no environment contact.

## Kill conditions

Reject on malformed receipt, failure to separate, exhaustion, a new
noncommutation witness, factor/code mismatch, target leakage into the
refinement, or environment contact.

## Claim boundary

A pass certifies one generic counterexample-guided availability refinement and
an offline selected-target route. It does not authorize execution or establish
task completion.
