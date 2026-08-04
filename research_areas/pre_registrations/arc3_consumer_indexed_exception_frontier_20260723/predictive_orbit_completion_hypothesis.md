# Predictive-operation orbit completion

Date: 2026-07-26

Parent tick: `tick-arc3-consumer-indexed-exception-frontier-20260723`

Parent quotient:
`boundary_segmented_predictive_quotient_audit_result.json`

## Eigenquestion

At a predictive state where operations `1` and `2` have different immediate
effects but the same future-test class, does operation `3` join that local
behavioral orbit or expose the exceptional mechanism?

## Evidence

From the verified Level 3 origin, operation `0` reaches predictive class
`b6e27e05259baebdf1d94e4ea8bbb9059bf9ce89d8e9f92995936dd1792f7a18`.

At that class:

- operation `1` is witnessed;
- operation `2` is witnessed;
- both reach class
  `e99a101bf89a2462402300b6899ac5da13e55b191206b383b106bcac7f156482`;
- operation `3` is unknown;
- the route `[0, 3]` contains no ambiguous traversal edge.

## Discriminating test

Execute one no-worker acquisition transaction with exact budget two.

## Predictions

Orbit completion:
operation `3` has its own immediate effect but reaches the same predictive
target class as operations `1` and `2`. The learner may then register the
parameterized local option family `[0, q]` for the witnessed orbit
`q in {1, 2, 3}`.

Exceptional operation:
operation `3` reaches a different predictive class, an environment boundary,
or a non-commuting consequence. The orbit conjecture is rejected and this
operation becomes the concentrated exceptional set.

Task event:
the external adjudicator reports a level increment. This supersedes the
mechanism classification for task status but the transition remains evidence.

## Kill conditions

- the online compiler admits a stale epoch or origin seed;
- the planner does not label the query as an orbit-completion discriminator;
- the route contains a non-commuting traversal edge;
- `[0, 3]` is already present under the same predictive source identity;
- no ordered lineage is archived.
