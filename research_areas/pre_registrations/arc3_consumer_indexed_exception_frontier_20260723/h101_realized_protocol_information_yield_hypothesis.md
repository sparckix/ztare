# H101 realized protocol information yield

Date: 2026-08-07

Hypothesis:
`H-GPSA-REALIZED-PROTOCOL-INFORMATION-YIELD-20260807-101`

Status: pre-registered; controller-neutral and offline

## Eigenquestion

Can the protocol selector's predicted identification value and a later
evidence-owned response be expressed in the same information-yield units,
without importing task reward or changing intervention cost?

## Hypothesis

For a priced committee of size `n` partitioned by predicted protocol response,
the selector's normalized identification is the expected normalized posterior
reduction. If an observed response selects a partition cell of size `k`, its
realized yield is:

`log2(n / k) / log2(n)`

for `n > 1`, and zero for a singleton committee. The uniform expectation of
that realized quantity over committee members equals the existing predicted
identification value.

An observed response absent from the forecast partition eliminates the
forecast committee and receives status `committee_refuted`; it may report
bounded realized yield one for diagnostics, but it cannot create task credit.

## Discriminating test

Construct a four-hypothesis protocol committee with response-cell sizes
`(2, 1, 1)`. Compile its existing guarded-protocol price and a frozen
information-yield forecast.

1. Verify predicted normalized identification is `0.75`.
2. Observe the size-two response and verify realized yield `0.5`.
3. Observe each singleton response and verify realized yield `1.0`.
4. Average realized yield uniformly over all four committee members and compare
   it to the predicted value.
5. Observe an out-of-partition response and verify committee-refutation status.
6. Attempt observation without evidence, and attempt forecast construction
   after changing committee or partition identity.
7. Pass forecast and observation values into an H100 decision window and
   verify the window remains task-unauthorized.

## Success criterion

1. Predicted and expected realized yield agree to numerical tolerance.
2. Common and rare response cells produce the frozen `0.5` and `1.0` values.
3. Forecast identity binds protocol, committee, partition, and one invariant
   measure identity.
4. Missing observation evidence is rejected.
5. Committee or partition drift is rejected.
6. An unseen response reports committee refutation rather than being assigned
   to a known cell.
7. Every forecast and observation receipt denies task-credit authority.
8. Protocol primitive and control costs remain unchanged.

## Kill conditions

- expected realized reduction differs from predicted identification;
- observed yield depends on task status or level gain;
- a response can silently cross committee or partition identity;
- an unseen response is forced into an existing cell;
- evidence-free observation is admitted;
- the measure receipt grants task value; or
- calibration changes protocol cost.

## Claim boundary

Passing establishes a controller-neutral compatible prediction/observation
measure over a witnessed response partition. It does not establish that ARC
currently emits the required post-intervention response object, automatic
play-loop collection, live replay pairs, H97 support, or score gain.
