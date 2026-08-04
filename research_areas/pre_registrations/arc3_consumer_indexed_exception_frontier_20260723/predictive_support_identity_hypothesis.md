# Predictive identity versus acquisition support

Date: 2026-07-26

Parent tick: `tick-arc3-consumer-indexed-exception-frontier-20260723`

Parent result: `unresolved_predictive_generator_result.md`

## Eigenquestion

Did direct operation `[1]` reveal incompatible future behavior between the
two former initiation members, or did the quotient split them only because
one member acquired support for a test that remains unknown on the other?

## Claim

Behavioral incompatibility and acquisition support are separate relations.
Two partial predictive states are incompatible only when a jointly witnessed
future operation/effect/boundary test contradicts. A test witnessed on one
state and absent on the other is a consumer-indexed support gap, not a
behavioral output.

The current total partition violates this distinction by encoding `unknown`
as a refinement color. That predicts the observed `74 -> 75` class increase
and the `6 -> 0` option collapse even when no contradictory behavior occurred.

## Discriminating test

Compile a support-aware predictive compatibility relation over the same
partial action system:

1. initialize every source pair as potentially compatible;
2. remove a pair only when a jointly witnessed operation has disjoint effects,
   incompatible boundary status, or successors with no compatible pairing;
3. iterate to a greatest fixed point;
4. record asymmetric source-operation coverage as support gaps;
5. inspect the two former initiation members.

## Predictions

Support-only split:
the two members remain compatible; no jointly witnessed operation refutes
them; direct operation `1` appears as an asymmetric support gap. The current
quotient’s extra class is epistemic coverage encoded as behavioral identity.

Behavioral split:
a jointly witnessed future test yields disjoint effects or incompatible
successors. The partition split is retained and the exact refuting test is
recorded.

## Success criterion

The compiler returns concrete source-pair witnesses, refuting operations for
incompatibilities, and consumer-indexed support gaps without assigning missing
tests a negative or positive behavioral result.

## Kill conditions

- compatibility is asserted from sensory similarity alone;
- missing evidence is copied between sources;
- the relation cannot return concrete inverse witnesses;
- boundary status is discarded;
- a greedy clustering choice is presented as canonical equivalence;
- option programs remain identified solely by mutable quotient class IDs.

