# Proof-carrying associated-graded obstruction compiler

**Date:** 2026-08-02
**Status:** supported; implementation, transfer, and rejection tests pass

## Eigenquestion

Can the filtered-obstruction core replace caller-supplied completeness and
compatibility Booleans by content-bound, authority-typed premise receipts,
while recovering the unrestricted Jacobian tail-minimax certificate and
transferring unchanged to unrelated filtered problems?

## Governing identity

The new object is an immutable **evidence receipt**. Its job is to bind one
named proposition to one subject, one mathematical context, one evidence
artifact, and one authority class. Its lifecycle begins when a compiler or
adapter emits canonical content and ends when a downstream compiler replays
that content hash. Equality is canonical-content equality. Compatibility
requires the same context identity; a matching digest shape or a true Boolean
does not establish compatibility.

The filtered-obstruction compiler owns theorem composition and exact
arithmetic. Substrate adapters own the translation from their mathematical
objects into typed contexts and evidence. A formal checker may strengthen an
adapter receipt's authority, but a label alone cannot do so.

## Target input and candidate theorem

The first target is the exhaustive tail-minimax composition. Replace its
eight independent truth flags and four untyped digests by:

1. one content-bound tail context naming the schedule category, statistic,
   and a compiler-recognized well-order on positive occurrences;
2. exactly one all-order, finite-prefix-uniform lower-bound receipt for the
   empty-positive-support branch;
3. exactly one such receipt for the least-positive-occurrence branch; and
4. exactly one admissible upper-construction receipt in the same context.

For the recognized natural-number lexicographic occurrence order, the core
derives the zero-or-least-positive partition. If both lower receipts prove a
bound at least `T` and the upper receipt proves a bound exactly `T`, the core
emits a content-bound minimax certificate with value `T`.

## Proof skeleton

1. Canonicalize JSON-compatible content and replay every receipt digest.
2. Require exact receipt fields and a closed authority vocabulary.
3. Replay the tail context and derive the partition from the recognized
   well-order identity.
4. Require the exact claim set
   `{pure_lower, least_positive_lower, admissible_upper}` with no duplicate.
5. Require every receipt's subject and context digest to match the problem.
6. Check scope and authority admissibility for each claim.
7. Check rational bound inequalities and equality.
8. Hash the context, ordered premise identities, and conclusion into the
   output certificate.

The existing Jacobian component certificates remain the mathematical
authorities for the two lower branches and the staircase construction. The
new kernel changes their composition contract, not their theorem content.

## Discriminating tests

- Recover the Jacobian value `2` with the same component certificate digests.
- Transfer the composition theorem to a filtered polynomial-degree tail.
- Transfer it to an unrelated valuation/support tail.
- Reject a forged receipt whose content was changed without rehashing.
- Reject a receipt rehashed under the wrong context.
- Reject duplicate claims, a missing branch, an unknown authority, a finite
  window offered as all-order evidence, a statistic mismatch, and a weak
  lower or nonmatching upper bound.

## Attack vectors and counterattacks

- **Typed flag laundering:** encoding each old Boolean as a receipt claim.
  Kill by deriving the branch partition inside the core and by using closed
  scope/authority identities rather than arbitrary proposition strings.
- **Hash-shaped authority:** accepting any 64-character string as proof.
  Kill by replaying a receipt over its full claim, context, subject, evidence,
  and authority content.
- **Cross-context graft:** combining correct certificates for incompatible
  statistics or categories. Kill by exact context-digest equality.
- **Duplicate-claim masking:** supplying two receipts for one branch and none
  for another. Kill by exact claim-set equality.
- **Parallel receipt dialect:** adding filtered-only hashing while LeanMill
  keeps another canonical identity rule. Kill by extracting the existing
  canonical JSON content identity into `ztare.common` and retaining LeanMill
  compatibility through a re-export.
- **Jacobian overfitting:** a contract works only for the contact filtration.
  Kill unless two alien domains pass without substrate-specific fields in the
  receipt kernel.

## Exact kill conditions

The proposal is rejected if it preserves the old Boolean assertions under new
names, cannot distinguish incompatible contexts, accepts replay or duplicate
attacks, changes the Jacobian component digests or minimax value, needs
Jacobian vocabulary below the adapter layer, or requires separate receipt
implementations in the common and LeanMill kernels.

## Recurrence and amnesia check

`primitive_amnesia` surfaced the existing filtered quotient, symbol-cokernel,
graph-quotient, and fixed-grade compilers. Repository inspection also found
LeanMill content-bound receipt replay in `protocol_validation.py` and
`frontier_campaign_runner.py`. The semantic retriever was unavailable, so
absence of further primitives is not inferred. This campaign will extract
and reuse the existing content-identity rule before adding the filtered
contract.

## Intended formal surface

Python owns receipt replay, exact claim-set coverage, context compatibility,
and certificate production. A small Lean carrier should encode the finite
composition theorem: exhaustive two-branch lower bounds plus a matching
admissible upper bound imply equality. Substrate factorization and
all-orderness remain explicit premises unless separately formalized.

## Outcome

The tail problem now has one replayed context and exactly three receipts; no
Boolean premise remains.  Polynomial-degree and valuation/support fixtures
transfer without substrate vocabulary in the receipt kernel.  All declared
identity, scope, authority, duplicate, missing-claim, statistic, and bound
attacks are rejected.  The Jacobian semantic digest remains
`24bee337068d65d8d81d1fa4ac584cec1130e3b160bef765f5afbd131acc1108`;
the proof contract is
`270c91a82e642bb832cff6863ab8c9291f15f3be5e1109b6ff9f751e019a0e4c`.
