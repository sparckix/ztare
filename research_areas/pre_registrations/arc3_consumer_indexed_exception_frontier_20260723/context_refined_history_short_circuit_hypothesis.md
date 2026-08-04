# Context-refined history short-circuit hypothesis

Date: 2026-07-26

Hypothesis ID: `H-ARC3-CONTEXT-REFINED-SHORT-CIRCUIT-20260726-15`

## Eigenquestion

Can the history selector test a counterexample-derived predictive coordinate
at each bounded-history candidate and stop at the first zero-ambiguity
candidate without changing the abstraction selected by exhaustive search?

## Hypothesis

Boundary ambiguity is the selector's optimization target. Once a candidate
plus an admitted predictive coordinate reaches the lower bound of zero, longer
history suffixes in that family are dominated; the other history family only
needs evaluation through the same suffix length. On the current evidence this
will evaluate at most four raw history candidates, retain the same component-
reservoir coordinate and action system as exhaustive search, and replace the
current 66-candidate scan.

## Discriminating test

Refactor predictive-coordinate discovery into candidate evaluation, preserving
the existing evidence-only component-reservoir learner. Add a fixture where
history alone cannot remove a boundary collision but the reservoir coordinate
can. Compare pruned and exhaustive selection on the fixture and on the latest
sealed ARC slice.

## Success criterion

- pruned and exhaustive modes select the same history kind and suffix length;
- predictive-context and action-system digests are identical;
- both systems have zero boundary ambiguity;
- the pruned live audit evaluates at most four raw candidates;
- graph, context, boundary, option, and frontier identities match the prior
  H14 audit.

## Kill condition

Any selected-system or coordinate drift, loss of compression eligibility,
hidden boundary ambiguity, frontier drift, or more than four raw candidates on
the current evidence.

## Claim boundary

This experiment changes selector cost only. It does not add an environmental
law, supply an action, or change the external completed-level counter.
