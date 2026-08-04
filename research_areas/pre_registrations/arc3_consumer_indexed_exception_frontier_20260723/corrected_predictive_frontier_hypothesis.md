# Corrected predictive-frontier probe

Date: 2026-07-25

Parent tick: `tick-arc3-consumer-indexed-exception-frontier-20260723`

## Eigenquestion

Does the corrected consumer-indexed partial-action relation turn the newly
selected `[0, 2]` route into information that changes the Level 3 frontier?

## Preconditions

The replay-only audit attests:

- shortest selected state: action suffix length one;
- zero boundary-contaminated non-commuting relations;
- route `[0, 2]` contains zero non-commuting traversal edges;
- the latest `[0, 1]` observation is already admitted, so this is not the
  previous frontier pair.

## Discriminating test

Run one acquisition-only, no-worker transaction from the verified level seed
with budget two.

The environment adjudicator remains the sole task authority. The carrier may
steer but cannot declare level completion.

## Outcomes

- Level event: the route reaches an environment-adjudicated discharge edge.
- New transition: archive it with ordered predictive lineage and recompile
  the frontier.
- New task-open boundary: seal the source/operation as an undefined edge and
  recompile.
- No frame growth but a distinct ordered history witness: admit the lineage,
  then require the next offline frontier to change.
- Exact repeated route or an ambiguous traversal edge: apparatus failure;
  do not spend another environment action until the consumer is repaired.
