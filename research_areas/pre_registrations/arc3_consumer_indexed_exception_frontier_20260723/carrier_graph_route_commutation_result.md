# Carrier/evidence-route commutation result

Date: 2026-07-26  
Hypothesis: `H-ARC3-CARRIER-GRAPH-ROUTE-COMMUTATION-20260726-32`  
Result artifact: `carrier_graph_route_commutation_audit_result.json`

## Verdict

Confirmed for the terminal key.

The active graph reconstructed with the frozen H29 identity: 130 nodes, 145
relations, ten boundaries, six context transitions, 127 reachable nodes, and
zero ambiguous relations. The recovered prefix had the expected 28 operations
and every edge was deterministic, non-boundary, and evidence-backed.

Carrier replay preserved `(controlled_base, finite_configuration)` at all 28
steps and the final predicted state satisfied the observed H29 target for
operation `1`. H31's calibration failure therefore came from search
equality/dominance, not inability of the carrier to transport the terminal
coordinates along that route.

## Exceptional factor

The first nonterminal difference occurred at step 11:

```text
operation: 3
graph effect:   controlled + (0,5), feasibility +11, budget +11
carrier effect: controlled + (0,5), feasibility  -1, budget  -1
```

The controlled position and configuration still agreed. The offset persisted
until the carrier produced a 21-unit renewal at step 21 while the graph edge
decremented by one. Motion and configuration continued to commute through the
final source.

This delayed renewal makes clock identity consequential to route search.
`CompiledFiberSearchProblem` currently has no `dominance_key_at`, so common
factored search merges different times for this consumer even though no
time-translation certificate is attached. Other compiled-fiber consumers keep
time in equality unless such a certificate exists.

## Claim boundary

The result localizes H31 to target-search state identity and nominates missing
clock identity as the next discriminator. It does not yet prove that adding
time recovers the route or that the H30-selected target is carrier-reachable.
