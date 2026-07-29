---
description: "Pre-registered closed-artifact state-transition probe for unavailable governance."
status: closed_pass
date: 2026-07-18
---

# Closed-artifact authority-state probe

## Identity boundary

The producer may carry a compiled candidate and deferred receipts. The
closed-artifact finalizer alone owns the authoritative governance transition.
Its result must replace the producer's provisional validation and outcome
before any certificate, campaign consumer, cache, or training ledger reads the
artifact.

## Hypothesis

The finalizer currently treats an omitted `available` field as availability,
drops that field when copying the kernel result, and records the finalized
validation only inside the certificate. A governance exception can therefore
leave the primary result labeled `closed` with stale producer credit. Requiring
explicit availability, rerunning governance on the exact carried artifact,
and writing the finalized validation back to the primary result will eliminate
that split state.

## Discriminating test

1. Give the finalizer `passed=true` with no explicit availability and require
   no credit.
2. Inject unavailable outer governance after a deferred producer pass and
   require the primary outcome and finalized validation to withhold closure.
3. Require the formal-task consumer to reject a nonempty but unavailable
   governance record.
4. Replay the positive carried-artifact route with `available=true` and the
   exact target identity.

## Success criterion

- only `available is true` and `passed is true` can authorize the final state;
- the outer finalizer always reruns the exact carried artifact rather than
  trusting an unbound producer receipt;
- the primary result, certificate, parity record, and campaign consumer see
  the same finalized validation;
- focused positive and rejection controls preserve their intended verdicts.

## Kill conditions

- the repair requires a domain-specific branch;
- the producer becomes able to set the final governance state;
- unavailable governance is mislabeled as mathematical rejection.

If killed, retain the candidate as an explicit open/unavailable artifact and
forbid all downstream positive effects.

## Result

Passed. The producer now carries a version-two closure artifact binding the
qualified target, posed and closed source hashes, and both normalized target
signature hashes. The outer boundary replays governance on those exact bytes,
then replaces the root producer validation before certificate, cache, corpus,
or campaign consumers run.

The finalizer requires explicit kernel availability and all fourteen authority
dispositions. A finalizer exception constructs a complete fourteen-authority
unavailable record and changes the root outcome to `governance_unavailable`.
Positive, rejection, omitted-availability, runtime-unavailability, and
finalizer-fault controls pass in `tests/test_closed_artifact_finalizer.py`.
