# Repaired joint-affordance search result

Date: 2026-07-26  
Hypothesis: `H-ARC3-REPAIRED-JOINT-AFFORDANCE-SEARCH-20260726-35`  
Result artifact: `repaired_joint_affordance_search_audit_result.json`

## Verdict

Refuted by a projection counterexample after calibration passed.

The repaired consumer recovered the observed target in 23 actions. Searching
the H30-selected target then generated 947 states and expanded 778 before the
common commutation guard rejected a dominance merge.

Two states had identical compiled factors and the same time, but differed at
only `(61,57)` and `(62,57)`, with values `3` versus `8`. Operation `0` sent
one state to controlled base `(45,9)` and the other to `(5,34)`. The receipt
reported `changed_factor_names: []`, so the projection had no coordinate for a
two-cell state that changes an operation image.

## Information gained

The selected target is no longer blocked by resource feasibility. Search
reached an under-specified quotient: the consumer merged states across a
finite availability distinction already present in the rendered carrier. The
guard prevented unsound pruning and supplied the exact missing discriminator.

The next test promotes only that counterexample-owned equality bit into the
existing availability category and reruns the selected target. It does not add
an action law, route, target value, or substrate noun.

## Claim boundary

This result establishes a missing factor, not selected-target unreachability.
No route was returned and no environment action occurred.
