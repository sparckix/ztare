---
description: "Pre-registered parity-factored LRAT certificate probe for the [51,20,14] control."
status: closed_killed
date: 2026-07-17
---

# Parity-factored LRAT probe

## Eigenquestion

Does exposing the known parity-extension construction shrink the axiom-clean
certificate enough to verify the `[51,20,14]` control compositionally rather
than certifying its full distance predicate in one generic SAT instance?

## Mathematical factorization

Let `C` be the frozen length-50 code and define

\[
\operatorname{ext}(c)=(c,\operatorname{wt}(c)\bmod 2).
\]

If every nonzero `c` has weight at least 13, then:

- odd `wt(c)` gains one parity coordinate and has extended weight at least 14;
- even `wt(c)` cannot equal 13, so `wt(c) >= 14` before extension.

Thus a base `[50,20,>=13]` certificate plus this reusable lemma proves the
extended `[51,20,>=14]` lower bound. The known base weight-13 message supplies
the matching upper-bound witness after extension.

## Hypothesis

The base bad-word CNF (`u != 0`, `c = uG`, `wt(c) <= 12`) will yield a textual
LRAT trace no larger than 60% of the 92,168,978-byte direct extended-code trace.
Mathlib's explicit `lrat_proof` constructor will check it within 180 seconds
under the existing axiom allowlist.

## Discriminating test

1. Generate the base distance-13 CNF from the frozen 20-by-50 matrix using the
   same XOR and sequential-counter encodings as the direct probe.
2. Require UNSAT at distance 13 and a replayed weight-13 SAT witness at
   distance 14.
3. Record exact CNF/LRAT hashes and sizes.
4. If the size criterion passes, run explicit `lrat_proof` construction and
   audit axioms.
5. Only after the base certificate passes, encode the parity-extension lemma
   as a reusable formal bridge; do not hardcode this matrix into that lemma.

## Success criteria

- exact base controls distinguish distance 13 from 14;
- base LRAT bytes are at most 60% of the direct trace;
- explicit proof construction finishes within 180 seconds;
- no generated native-check or other unallowed axiom;
- the later parity bridge consumes the base certificate without enumerating
  messages again.

## Kill conditions

- CNF/model replay mismatch;
- less than 40% LRAT byte reduction;
- explicit proof-term timeout or extra axiom;
- parity composition requires matrix-specific common-kernel code.

The common ratifier and allowlist are frozen throughout.

## Result

The base controls behaved as required. The distance-13 CNF has 880 variables
and 2,227 clauses; CaDiCaL returned UNSAT in 11.19 seconds. The distance-14 CNF
returned SAT, and independent full-clause replay assigned all 930 variables and
reconstructed message `0x80000`, base codeword `0x1840d6e180000`, and weight
13.

The base textual LRAT trace is 63,999,990 bytes, or 69.44% of the 92,168,978
byte direct trace. That is only a 30.56% reduction, below the preregistered 40%
threshold, so the experiment stops without another explicit proof-term run.

- base distance-13 CNF SHA-256:
  `cfc73acb5af9b422729fa75a057eed79494d7a91912cb4cc98bb341ff8b5c32b`
- base distance-13 LRAT SHA-256:
  `2532a4c3bda86b0bbcae2b73204ddae64ff4176683391110936cf89768a68ea3`
- base encoder source SHA-256:
  `e20aa5b5a3c510cb22255462104c94fdcd4805828009856cfd2c0bbbb714834c`
- generic SAT-model replay source SHA-256:
  `8a8ad441cd6f75773ff684954696b1306e9b74dd15cfe2c1b7c6ed8299322983`
- provider calls: zero

Parity factorization remains the clean mathematical bridge, but it does not
shrink this particular generic LRAT certificate enough. A different base-code
certificate—QC orbit representatives, a specialized algebraic bound, or a
proof-producing checker with better sharing—is required before revisiting the
full ratification route.
