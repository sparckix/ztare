# Joint-affordance synthetic-target search result

Date: 2026-07-26  
Hypothesis: `H-ARC3-JOINT-AFFORDANCE-SEARCH-20260726-31`  
Result artifact: `joint_affordance_search_audit_result.json`

## Verdict

Refuted at the positive control.

The H30-selected configuration has one raw rendering with direct evidence, so
target construction was unambiguous. The common factored search generated 457
states and exhausted the carrier's projected frontier for both targets:

| Target | Search status | Generated | Expanded |
|---|---|---:|---:|
| observed H29 non-discharge target | `projected_frontier_exhausted` | 457 | 458 |
| H30 selected-configuration target | `projected_frontier_exhausted` | 457 | 458 |

Neither search returned an action route or a projection counterexample. No
environment action was issued.

## Information gained

Failure is upstream of target composition. The accepted carrier cannot reach
an exact target already reachable by a 29-operation path in the
evidence-compiled partial action system. The selected target therefore did not
receive a calibrated planning test.

The next discriminator is a stepwise comparison between the evidence graph's
known H29 route and carrier replay of the same operations. The first divergent
factor and its owning transition identify whether the repair belongs to the
predictive carrier, the graph-to-carrier lowering, or a consumer equality that
merged states the carrier cannot transport.

## Claim boundary

This result rejects the current carrier as a route generator for this target
pair. It does not reject the H30 joint invariant or show that the selected
configuration is unreachable in the evidence graph.
