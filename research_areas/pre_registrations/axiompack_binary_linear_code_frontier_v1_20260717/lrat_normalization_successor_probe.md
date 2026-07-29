---
description: "Pre-registered normalization successor for the killed opaque LRAT encoding."
status: closed_capacity_pass_policy_fail
date: 2026-07-17
---

# LRAT normalization successor probe

## Prior result

The frozen opaque-definition probe was killed because `bv_decide` abstracted
the application `encode u`. Its source and result remain unchanged in
`lrat_certificate_successor_probe.md`.

## Hypothesis

Running `simp only [encode, selectRow]` before `bv_decide?` will expose a
supported 20-input, 51-output XOR/conditional circuit. The exact distance-14
positive control will then close within 120 seconds and emit a replayable LRAT
file. The resulting declaration is still expected to depend on
`Lean.ofReduceBool`, so capacity success does not imply kernel-pure admission.

## Discriminating test

Use the same matrix, target, bit widths, timeout, and LRAT settings as the
killed attempt. Change only the proof prelude from a direct `bv_decide?` call
to explicit unfolding of `encode` and `selectRow`, followed by `bv_decide?`.
Record elapsed time, output LRAT hash/size, and `#print axioms`.

## Success criteria

- no opaque-expression diagnostic;
- distance 14 closes within 120 seconds;
- an LRAT file is emitted and can be replayed by `bv_check`;
- exact matrix bytes and target remain unchanged.

## Kill conditions

- any residual opaque matrix/weight expression;
- SAT timeout or replay timeout;
- a claimed kernel-pure close despite `Lean.ofReduceBool` appearing in the
  axiom output.

## Result

Explicit normalization removed the opaque-expression failure. The exact
distance-14 target completed in roughly 30 seconds and emitted a 56,768,354
byte binary LRAT proof. A solver-free `bv_check` replay completed in 16.52
seconds.

- generation source SHA-256:
  `bc3ee9623c918cf057b756efda77b43208f3554945876cd75186f27d1d390d2b`
- replay source SHA-256:
  `daa3894d236479ecbca185f03897c77efc0b1b8122a2a0563a4a383b6c063d8c`
- LRAT SHA-256:
  `5968f553d3cd97a8705c021523fd7bfb3288e3856ec7b36672f0b05a5ecd4531`
- provider calls: zero

Both generated declarations depend on a theorem-local private native-check
axiom named with the suffix `_native.bv_decide.ax_1_7`, in addition to the
standard allowed axioms. Lean 4.31 no longer prints that dependency literally
as `Lean.ofReduceBool`, but it has the same policy consequence: the stock
native evaluation path is outside the existing allowlist. The capacity leg
passes; formal admission remains unavailable through this tactic.

The next representation candidate is Mathlib's separate
`Mathlib.Tactic.Sat.FromLRAT.lrat_proof`, which constructs explicit proof terms
without the private native-check axiom. It requires an exact CNF artifact and a
proved bridge from that CNF to the binary minimum-distance predicate.
