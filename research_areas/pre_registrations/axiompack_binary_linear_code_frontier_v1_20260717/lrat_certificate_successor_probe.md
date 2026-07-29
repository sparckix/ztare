---
description: "Pre-registered LRAT successor-certificate probe for the binary-code formal boundary."
status: closed_killed
date: 2026-07-17
---

# LRAT certificate successor probe

## Identity boundary

LeanMill continues to ratify one frozen target, carried proof artifact, axiom
set, and closure identity. The binary adapter may change how it represents a
minimum-distance certificate. It may not add a binary-code branch to the
common ratifier or silently widen the accepted axiom tier.

## Eigenquestion

Can the published binary `[51,20,14]` control be reduced to a succinct SAT/LRAT
certificate whose verification avoids expanding all `2^20 - 1` messages into
the Lean source, while keeping the certificate's target and matrix bytes
content-bound?

## Hypothesis

Bit-blasting the closed claim

\[
\forall u\in\mathbf F_2^{20},\quad
u\ne0\Longrightarrow \operatorname{wt}(uG)\ge14
\]

and checking an LRAT UNSAT certificate will finish within 120 seconds on the
published positive control. The stock Lean 4.31 `bv_decide`/`bv_check` path is
expected to add `Lean.ofReduceBool`; if so, it establishes a useful certificate
shape but remains ineligible under the current kernel-pure policy.

## Discriminating test

1. Encode the exact frozen 20-by-51 matrix as fixed-width bit-vector
   expressions, with one 20-bit universally quantified message and a 51-bit
   encoded word.
2. Run `bv_decide` with an LRAT output path and a 120-second SAT timeout.
3. Record source and matrix hashes, elapsed time, LRAT size, theorem target,
   and `#print axioms` output.
4. If the solver finishes, replay the emitted LRAT through `bv_check` without
   invoking the solver and compare the theorem/axiom identity.

No result from this probe is admitted as a construction certificate unless it
passes the existing allowlist unchanged.

## Success criteria

- the exact positive control closes and its saved LRAT replays within 120
  seconds each;
- changing the required distance from 14 to 15 yields a concrete SAT
  counterexample rather than an UNSAT certificate;
- target, matrix, predicate, CNF, and LRAT hashes are separately recorded;
- no common LeanMill governance or campaign module changes.

## Kill conditions

- bit-vector normalization abstracts any matrix/weight operation as an opaque
  symbol;
- the SAT or replay leg exceeds 120 seconds;
- the distance-15 negative control is not distinguished;
- accepting the result would require allowing `Lean.ofReduceBool` or another
  compiler-trust axiom in the existing kernel-pure tier.

If the capacity leg succeeds but the axiom leg fails, retain LRAT as the
certificate representation candidate and next test a proof-producing or
kernel-reduced checker. Do not weaken the current allowlist to make this probe
pass.

## Result

The first representation hit the first kill condition in 13.38 seconds. Lean
treated the custom `encode u` call as an unsupported opaque expression and
returned a potentially spurious SAT assignment instead of bit-blasting the
fixed XOR circuit. The failed declaration consequently carried `sorryAx` and
earned no certificate credit.

- source SHA-256:
  `03392a610dbcf52aa0888c1c393f6f35f0adeffdd57d20decdd661e1f5e79553`
- frozen control-panel SHA-256:
  `65363aa5bdfc86e328d03ee4f0a6cc45e84f528bf466ef19b65b6c11a1bf30f1`
- diagnostic abstraction: `encode u`
- provider calls: zero

This kills the opaque-definition encoding only. The next probe separately
tests whether an explicit normalization step exposes the same fixed circuit to
the stock bit-vector frontend.
