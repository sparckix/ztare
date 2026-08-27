# H115: ordinal effect-guard extrapolation

Date: 2026-08-06

Hypothesis:
`H-GPSA-ORDINAL-EFFECT-GUARD-EXTRAPOLATION-20260806-115`

Status: pre-registered after H114 settlement and structural inspection, before
executing `(2,1)` on any H114 active source

## Trigger

H114 actively generated 51 novel states, but exact equality on the full
Boolean feasibility vector abstained everywhere. Structural inspection shows
that every observed vector is a false-prefix/true-suffix order ideal. Its
true-count is the already represented scalar `ordered_budget`. In H113
discovery, budgets `1`, `6`, and `{10,11,13}` map respectively to three effects;
the active sources have unseen higher budgets `{18,19,20,21}`.

## Eigenquestion

Is the `(2,1)` effect governed by an ordinal budget regime that extrapolates
beyond the discovery maximum, or did exact-vector equality hide another
state-dependent mechanism?

## Hypothesis

The minimum discovery-consistent contiguous threshold classifier has three
intervals: budget at most `3`, budget `4` through `8`, and budget at least `9`.
Every actively generated source above the discovery maximum will realize the
third interval's frozen effect under `(2,1)`.

## Discriminating test

Using the frozen H113 discovery set and H114's 51 representative prefixes:

1. verify H113/H114 result identities and the cached environment;
2. confirm every discovery and active feasibility vector is a false-prefix/
   true-suffix order ideal and that `ordered_budget` equals true-count;
3. fit the minimum number of contiguous integer intervals whose discovery
   budgets map to one effect each; place a boundary at the integer midpoint
   between adjacent differently labelled observed budgets;
4. freeze the interval/effect map before environment execution;
5. replay each H114 representative prefix, verify exact source identity and
   pre-word boundary status, then execute `(2,1)`;
6. score only sources whose budget was absent from discovery and require the
   extrapolating interval selected before execution;
7. find an equal-budget witness pair that changes another factor coordinate
   while preserving prediction and observed effect;
8. mutate interval boundary, budget, source, word, prediction, effect, and
   environment identities in receipt-only controls.

All cached-environment actions are charged. Active outcomes cannot alter an
interval or its effect label.

## Success criterion

Stage A is supported only if:

- discovery fitting yields exactly three collision-free contiguous intervals;
- at least five exact active sources have budgets above the discovery maximum;
- every eligible source matches the frozen extrapolated effect and crosses no
  task boundary during the word;
- at least one equal-budget witness pair varies a non-budget factor coordinate
  while preserving effect;
- unsupported scalar regimes retain typed abstention; and
- all identity mutations are detected.

## Kill and refinement rule

Reject on one eligible effect error, non-order-ideal feasibility, budget/count
drift, boundary crossing, no orthogonal witness, post-outcome interval change,
or mutation leakage. A mismatch becomes a typed counterexample requiring an
additional causal coordinate. A pass licenses an ordinal effect gate for
prospective use, not task credit.

## Claim boundary

Passing would establish active out-of-range effect extrapolation for one word
in one cached game. It would not establish task credit, task transfer,
controller benefit, benchmark gain, catalytic learning, criticality, takeoff,
or literature novelty.
