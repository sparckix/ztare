# Recoverable-zero target-search calibration

Date: 2026-07-26  
Hypothesis ID: `H-ARC3-RECOVERABLE-ZERO-TARGET-SEARCH-20260726-34`  
Status: preregistered

## Eigenquestion

Did target search lose the known route because it mistakes a recoverable
zero-resource state for an inadmissible terminal state?

## Hypothesis

Allowing any projection-domain state into target search, while leaving the
goal's positive-budget requirement unchanged, recovers the observed H29 target
within the H31 bounds. The route will cross one zero-budget state and then an
evidence-aligned positive renewal.

## Fixed ablation

- exact H31 start, carrier, observed target, operation, heuristic, dominance
  key/vector, four interventions, depth 180, and 20,000-state cap;
- audit-local subclass of `CompiledFiberSearchProblem`;
- the only override is:

```python
def admissible(self, state):
    return self.projection.in_domain(state)
```

- `goal_edge` remains inherited and still requires `ordered_budget > 0`;
- replay the returned route and report the budget sequence, zero states,
  renewal effects, target factors, and goal result;
- bind H32's known route as the positive-control witness, but allow search to
  find another route.

## Success criterion

- `edge_found` with no projection counterexample;
- replay stays in domain and reaches the H29 terminal key/edge;
- the route includes at least one zero-budget state followed by a positive
  budget state;
- every zero-to-positive transition has an explicit carrier effect and the
  positive-control known route retains its depth-21 zero/depth-22 renewal;
- no behavior besides target-search admissibility changes.

## Kill conditions

Reject on exhaustion, noncommutation, out-of-domain replay, no recoverable-zero
witness, goal mismatch, broader consumer change, or environment contact.

## Claim boundary

A pass certifies that zero resource is a recoverable mechanism state for this
general consumer and justifies a narrow core repair plus regression tests. It
does not yet test the H30-selected target.
