# H114: active effect-guard intervention

Date: 2026-08-06

Hypothesis:
`H-GPSA-ACTIVE-EFFECT-GUARD-INTERVENTION-20260806-114`

Status: pre-registered after H113 settlement and before active prefix
enumeration or effect scoring

## Trigger

H113 found that chronological replay supplied no unseen initiation states. On
discovery data, the two-action word `(2,1)` had three relative effects and
`ordered_feasibility_configuration` alone separated them without collision.
That coordinate may govern the effect, or merely correlate with an unvaried
coordinate. Passive replay cannot decide.

## Eigenquestion

Does the discovery-selected feasibility coordinate retain predictive authority
when active prefixes vary the other factor coordinates and create exact states
absent from the H63 discovery corpus?

## Hypothesis

Among all cached-environment prefixes of length zero through five, at least
five novel exact initiation states across at least two feasibility-guard values
will share a guard value learned by H113. Executing frozen word `(2,1)` will
match the discovery-predicted ordered effect on every covered state, including
at least one pair that holds the feasibility guard fixed while another factor
coordinate changes.

## Discriminating test

Using the same cached `ls20` source, fixed seed, H63 carrier/projection, and no
controller:

1. verify the H113 result and reconstruct its discovery-only `(2,1)` guard;
2. enumerate all 1,365 action prefixes of length zero through five in
   length-then-lexicographic order;
3. reset and execute each prefix, discarding cases that cross a level boundary
   before the test word;
4. construct the exact H63 factor/history initiation key and quotient duplicate
   source states before scoring;
5. mark states absent from the 21-trajectory H113 discovery set;
6. if the frozen feasibility guard key was witnessed in discovery, execute
   `(2,1)` and compare its ordered relative-effect signature with the frozen
   prediction; otherwise record typed abstention;
7. require an intervention witness pair with equal feasibility guard and
   effect but a changed non-guard factor coordinate;
8. mutate environment, source, guard, word, prediction, and effect identities
   in receipt-only controls.

Every cached-environment action is charged. Discovery effects are frozen
before prefix enumeration; active outcomes cannot revise the gate in this
test.

## Success criterion

Stage A is supported only if:

- at least five distinct exact sources absent from H113 discovery are covered;
- covered sources span at least two learned feasibility-guard values and at
  least two predicted effects;
- every covered source matches its frozen predicted effect;
- at least one equal-guard witness pair changes a non-guard factor coordinate
  while preserving the prediction and observed effect;
- absent guard values abstain; and
- all identity mutations are detected.

## Kill and refinement rule

Reject on any covered effect error, insufficient exact-state or guard-value
variation, no orthogonal-coordinate witness, boundary leakage, post-outcome
gate revision, or mutation leakage. An effect error falsifies the one-
coordinate causal gate and supplies the counterexample needed for refinement.
Insufficient state variation redirects acquisition to a different environment
or explicit state constructor rather than more replay.

## Claim boundary

Passing would establish one actively intervened relative-effect gate for one
word in one cached game. It would not establish task credit, task transfer,
controller benefit, benchmark gain, catalytic learning, criticality, takeoff,
or literature novelty.
