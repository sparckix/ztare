# ARC3 consumer-indexed exception frontier

Date: 2026-07-23

Tick: `tick-arc3-consumer-indexed-exception-frontier-20260723`

Forecast contract: `arc3-consumer-indexed-exception-frontier-meso-20260723`

Frozen goal:

> Determine whether the Level 3 acquisition stall is caused by conflating transition-state equality with acquisition support, and either repair the consumer-indexed state-action frontier without substrate-specific coordinates or falsify that route with a replayable counterexample.

## Governing identities

| Object | Job and owner | Lifecycle and authority | Compatibility relation |
|---|---|---|---|
| Transition state | Preserve states whose predicted futures can differ; owned by the transition planner | Scoped to the active evidence epoch; steering only | Equal only under the transition carrier's admitted abstraction |
| Acquisition support | Record which consumer-visible operation contexts have observed evidence; owned by witness-gap acquisition | Grows monotonically from observed transitions in the active evidence scope; steering only | Equal under the caller's coverage projection |
| Task discharge | Decide whether the level advanced | Owned by the environment adapter | Environment-attested level event only |

The transition-state identity and acquisition-support identity may coincide, but neither owns the other. The planner must therefore carry both explicitly.

## Hypothesis

The Level 3 stall is partly caused by `plan_witness_gap` using the transition abstraction for two incompatible jobs: graph-search deduplication and observed state-action support. Supplying a separate acquisition-support projection will preserve transition-distinct routes while targeting missing consumer-visible operations. On the current bank this should prevent the frontier from being dominated by aliases and should produce either:

1. a newly observed consumer support pair or an informative carrier divergence; or
2. a bounded counterexample showing that consumer-indexed support is already exhausted.

No game-specific cell, color, coordinate, object name, or level rule is admissible in the repair.

## Discriminating tests

1. **Aliased-support counterexample.** Construct two transition-distinct states with the same support identity, where only the second state reaches a missing support pair. Search must retain both transition states and return the route through the second.
2. **Identity fallback.** With no coverage projection, witnessed-pair construction and search must retain the prior transition-abstraction behavior.
3. **Observed-support update.** After a live observation, the support index must add the caller-projected state-action pair rather than its transition carrier.
4. **Current-bank replay audit.** Compare transition node counts, support node counts, witnessed pairs, and missing pairs on the active Level 3 epoch without taking an environment action.
5. **Governed acquisition leg.** Run the existing no-worker play loop after the above pass. Acceptable yield is a new support pair, a carrier divergence, a level event, or a bounded exhaustion receipt tied to the consumer projection.

## Kill conditions

Reject or revise this route if any of the following occurs:

- the repair requires a substrate constant;
- the support projection is used for graph-search deduplication and erases a necessary route;
- the transition abstraction is used to claim consumer support;
- the current-bank audit has no missing consumer pair reachable under the carrier;
- the live leg repeats one intervention without growing support, divergence evidence, or a bounded exhaustion receipt;
- a predicted quotient fails to commute on a witnessed transition.

## Exceptional-set rank

Support volume and exceptional-set novelty are opposing ranks. The test therefore reports both frequent support gaps and low-support/nondeterministic pairs. A frequent alias cannot suppress an exceptional pair merely because both share a consumer support key; transition identity remains the search coordinate.

