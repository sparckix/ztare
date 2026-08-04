# Counterexample-guided coordinate refinement

Date: 2026-07-25

Parent tick: `tick-arc3-consumer-indexed-exception-frontier-20260723`

## Eigenquestion

Which omitted factor separates the boundary presentation from the post-reset
presentation when both currently share a partial-action source-operation
identity?

## Hypothesis

The relation failed because `fiber_transition_key` quotients at least one
factor without an action-commutation certificate. Comparing the two raw
presentations through the full `FiberFactors` mapping will expose a small
separating set. The preferred discriminator is the smallest factor set that:

1. differs across the boundary and law-owned source presentations;
2. is already produced by the accepted consumer projection;
3. removes the observed source-operation non-commutation;
4. does not contain a substrate constant;
5. has an explicit symmetry/equivariance interpretation.

The first candidate is `presentation_assignment`, which the factor projection
already emits but `fiber_transition_key` currently erases. It may be promoted
only if the paired-source audit shows that the retained factors are equal and
presentation assignment differs, or if another smaller existing factor is
ruled out.

## Discriminating checks

1. Reconstruct the boundary source at sealed index 15 and the following
   law-owned source.
2. Compare every named factor and record the minimal differing field set.
3. Confirm whether the existing transition key merges the pair.
4. Add each differing field independently and test pair separation.
5. Rebuild the active partial-action relation under the smallest admissible
   refinement and measure non-commuting relation count, reachable fibers, and
   frontier target.

## Kill conditions

Reject the candidate discriminator if:

- it does not separate the paired sources;
- it is derived from task discharge or hidden environment code;
- it merely memorizes a raw state or action sequence;
- it increases state count without removing the named non-commutation;
- its claimed symmetry relation is unsupported by a transport check.
