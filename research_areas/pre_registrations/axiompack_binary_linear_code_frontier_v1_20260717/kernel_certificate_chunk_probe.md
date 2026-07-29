---
description: "Pre-registered performance probe for the finite binary-code Lean certificate adapter."
status: closed_killed
date: 2026-07-17
---

# Binary certificate chunk probe

## Identity boundary

The LeanMill trust boundary stays unchanged: it checks one frozen proposition,
one content-bound proof, axiom provenance, and the resulting closure receipt.
Binary-code enumeration and certificate layout belong to the registered
`binary_linear_code.v1` adapter.

## Hypothesis

The full (2^{20}-1)-message certificate is dominated by elaboration overhead
from 1,024 separate reduction theorems. Increasing the adapter's deterministic
chunk size from 1,024 to 8,192 messages will reduce the theorem count from
1,024 to 128 and allow the published \([51,20,14]\) positive control to compile
within the existing 500-second construction-ratification default.

## Discriminating test

Generate the byte-bound Lean source for the frozen positive-control matrix and
run `lake env lean` on the complete source. Record elapsed time, exit status,
target name, source digest, declared axioms, and forbidden-token audit.

## Success criterion

- exit status zero within 500 seconds;
- the target reports only Lean's standard `propext` axiom;
- no `sorry`, `admit`, `native_decide`, `bv_decide`, or `ofReduceBool` occurs;
- the emitted interval list covers exactly messages 1 through (2^{20}-1);
- dimension 21 still returns typed capability unavailability.

## Kill conditions

- the larger chunk exceeds Lean recursion or resource limits;
- full compilation still exceeds 500 seconds;
- the optimization requires a binary-specific branch in LeanMill's common
  governance or campaign state machine.

If killed, keep the current host verifier and mark full dimension-20 kernel
ratification unavailable pending a proof-producing decision-diagram, trellis,
or SAT certificate. Do not raise a global timeout solely to hide the result.

## Result

The source-layout part of the hypothesis held: 8,192-message chunks reduced the
complete source from roughly 270 KB and 1,024 reduction theorems to 42,513
bytes and 128 reduction theorems. The operational hypothesis failed. The full
positive control had not completed after a monitored window exceeding 500
seconds and was interrupted without a Lean diagnostic. The shell timing line
reported an inconsistent larger wall value after interruption, so it is not
used as an elapsed-time measurement; crossing the fixed observation window is
sufficient for the pre-registered verdict.

Frozen identifiers:

- formal input SHA-256: `53e3848619e9c9789a12665a9eb00ad4ab25d8207a3da2a38fc00b652235419f`
- target: `AxiomPack.BinaryLinearCodeCertificate.certificate_53e3848619e9c978`
- generated source SHA-256: `c3c2d2385f6bb97b4fd59a8f15e5d970f4fc57865cad927e50c23376b6b7f1a6`
- ratification-contract SHA-256: `80a6fa9a3fedd15be5aa73ec982f670857ff67918e720c4d20fde754031352fe`

The adapter now advertises only the largest end-to-end compiled exhaustive
range, (2^{14}-1) nonzero messages. Larger candidates retain exact host
verification and receive typed formal-capability unavailability. A future
adapter certificate may widen the envelope without changing LeanMill's common
kernel.

The exact published control was replayed through the production ratification
entry after the cap changed. It returned
`status=unavailable`, `stage=formal_interface`, and
`reason_code=binary_kernel_certificate_message_bound_exceeded`; the carried
task remained `open` with next obligation
`construction_artifact_ratification`. No solver or provider was invoked.
