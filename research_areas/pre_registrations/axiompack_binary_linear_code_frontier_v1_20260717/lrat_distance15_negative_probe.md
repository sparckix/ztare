---
description: "Pre-registered SAT negative control for the normalized binary-code circuit."
status: closed_pass
date: 2026-07-17
---

# LRAT distance-15 negative probe

## Hypothesis

With the matrix circuit explicitly normalized, changing only the threshold
from 14 to 15 will make the universal claim false. The SAT frontend will return
a concrete 20-bit message within 30 seconds, and host replay of that message
will produce a codeword of weight 14.

## Discriminating test

Use the byte-identical 20-by-51 matrix and proof prelude from the successful
normalization probe. Ask `bv_decide?` to close the false distance-15 claim in
counterexample mode. Record the diagnostic assignment and replay it through
the existing exact binary verifier.

## Success criteria

- Lean rejects the false theorem with a concrete message assignment;
- the assigned message is nonzero and encodes to weight exactly 14;
- no LRAT UNSAT certificate or closure receipt is minted.

## Kill conditions

- the frontend reports an opaque expression;
- the assigned message does not reproduce the diagnostic in the host verifier;
- the false target is accepted.

## Result

Lean rejected the false distance-15 theorem after 17.95 seconds and returned
the concrete message `524288#20` (`0x80000`). That message selects generator
row 19, yielding codeword `0x5840d6e180000` of Hamming weight 14. The existing
host semantics therefore reproduces the SAT diagnostic exactly. No closure or
UNSAT certificate was minted.

- source SHA-256:
  `00555af245beff9ff4367975d590c55dd445c3689f62baf09bd9e0530c3eaa0c`
- diagnostic message: `0x80000`
- diagnostic codeword: `0x5840d6e180000`
- observed weight: `14`
- provider calls: zero
