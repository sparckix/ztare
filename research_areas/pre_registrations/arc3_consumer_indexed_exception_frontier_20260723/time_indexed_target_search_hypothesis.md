# Time-indexed target-search calibration

Date: 2026-07-26  
Hypothesis ID: `H-ARC3-TIME-INDEXED-TARGET-SEARCH-20260726-33`  
Status: preregistered

## Eigenquestion

Did H31 lose a valid target route because `CompiledFiberSearchProblem` merges
states reached at different carrier times without a time-translation
certificate?

## Hypothesis

Keeping time in target-search equality, while changing no state factor,
dominance vector, heuristic, prediction, target, or search bound, recovers the
observed H29 positive-control route that the unindexed consumer exhausts.

## Fixed ablation

- use the exact H31 start, carrier, observed target, terminal operation, depth
  180, state cap 20,000, and four interventions;
- baseline is the frozen H31 result:
  `projected_frontier_exhausted`, 457 generated states;
- create an audit-local subclass of `CompiledFiberSearchProblem` whose only
  override is:

```python
def dominance_key_at(self, state, time_value):
    return self.dominance_key(state), time_value
```

- run common `search_factored` once;
- carrier-replay any returned route and require the same terminal key and goal
  edge as H32;
- compare the route with H29's known evidence route, but do not require route
  identity.

## Success criterion

- time-indexed search returns `edge_found` within the frozen bounds;
- no projection counterexample;
- replay satisfies the observed target base/configuration and terminal edge;
- the baseline remains bound to H31's exhausted result;
- no other consumer or carrier behavior changes.

## Kill conditions

Reject on baseline drift, bound exhaustion, projection noncommutation, replay
mismatch, goal miss, any change beyond clock identity, or environment contact.

## Claim boundary

A pass certifies a missing clock-identity guard in the general
`CompiledFiberSearchProblem`. Core repair and selected-target search require
separate steps.
