---
description: "Pre-registered axiom-clean LRAT proof-term probe for the binary-code certificate successor."
status: closed_killed
date: 2026-07-17
---

# Explicit LRAT proof-term probe

## Identity boundary

The untrusted producer may translate one frozen matrix predicate to CNF and ask
CaDiCaL for an LRAT trace. Mathlib's `lrat_proof` command must reconstruct an
explicit Lean proof term from the exact CNF/LRAT bytes. LeanMill's common
ratifier and axiom allowlist remain unchanged.

## Eigenquestion

Does explicit LRAT proof construction remove the private native-check axiom
observed in the fast `bv_decide`/`bv_check` diagnostic while retaining workable
verification cost on the exact `[51,20,14]` control?

## Hypothesis

A deterministic Tseitin encoding of

\[
u\ne0\quad\land\quad c=uG\quad\land\quad \operatorname{wt}(c)\le13
\]

will be UNSAT. CaDiCaL will emit a textual LRAT trace within 120 seconds, and
`Mathlib.Tactic.Sat.FromLRAT.lrat_proof` will construct and kernel-check its
proof term within 180 seconds with axioms contained in
`{propext, Classical.choice, Quot.sound}`.

## Frozen encoding

- message variables: 20;
- codeword variables: 51;
- each codeword coordinate is connected to its selected message bits by a
  chained four-clause XOR Tseitin encoding;
- `u != 0` is one positive clause over all message variables;
- `weight(c) <= 13` uses the one-directional sequential-counter encoding whose
  auxiliary variables witness prefix counts;
- bit `i` remains coordinate `i` throughout.

The experiment-local encoder records the variable map, clause count, and CNF
hash. It is not a runtime capability.

## Discriminating test

1. Generate exact distance-14 and distance-15 CNFs from the same frozen matrix.
2. Ask CaDiCaL for a textual LRAT trace for distance 14 and a SAT assignment for
   distance 15.
3. Replay both outcomes against the CNF and binary semantics.
4. Run `lrat_proof` over `include_str`-bound CNF/LRAT files and audit the
   resulting theorem's axioms.
5. Flip one literal in a copied LRAT step and require proof construction to
   fail.

## Success criteria

- distance-14 CNF is UNSAT and distance-15 CNF is SAT;
- the SAT assignment selects a nonzero message whose codeword has weight 14;
- explicit LRAT proof construction finishes within 180 seconds;
- axiom output is a subset of the existing allowlist and contains no generated
  native-check axiom;
- tampered LRAT is rejected;
- all matrix, predicate, CNF, LRAT, and source bytes are content-addressed.

## Kill conditions

- the CNF encoding fails its model replay or distinguishes the controls
  incorrectly;
- CaDiCaL or Lean exceeds the stated bounds;
- Mathlib's proof constructor cannot consume the emitted LRAT dialect;
- any extra axiom appears;
- connecting CNF UNSAT back to minimum distance would require exhaustive
  `2^20` replay rather than a reusable encoder-correctness theorem.

Passing this probe establishes the certificate substrate only. Construction
ratification additionally requires the adapter-local CNF soundness bridge and
the usual content-bound closure route.

## Result

The deterministic encoding produced 952 variables and 2,388 clauses for
distance 14. CaDiCaL returned UNSAT in 8.54 seconds and wrote a 92,168,978-byte
text LRAT trace. The distance-15 sibling produced 1,003 variables and 2,488
clauses and returned SAT immediately; its message variables select only bit 19,
matching message `0x80000` and the known weight-14 codeword.

- distance-14 CNF SHA-256:
  `5b4b5b50c2a700b759adbf124974c76722a78cd75742c39d9cf9a2dc924a8c3c`
- distance-14 LRAT SHA-256:
  `7aadd90de32b55d0a3fc534d5f4d812bfa8434f413cef4a96c2e8299bbae424f`
- distance-15 CNF SHA-256:
  `08c88cb43cdec38091e5d6b4377498ff09ab099824fa846c4b31ca6b4308b2ef`
- encoder source SHA-256:
  `1dac501ff3aae33345fcd913e3362699f43b825dab3812d3ddf9430e12a82160`
- Lean probe source SHA-256:
  `17db31b3d40a5574b77bdfff0ed13e75fe244f62ba623b7faac41a13ee84192e`
- SAT-model replay source SHA-256:
  `b23d44602018a9827d217ffc50c7ea5f98b40e03a15809e621d4fd3cb03eef2b`
- generalized SAT-model replay source SHA-256:
  `8a8ad441cd6f75773ff684954696b1306e9b74dd15cfe2c1b7c6ed8299322983`
- provider calls: zero

The independent SAT-model replay assigns all 1,003 variables, satisfies every
distance-15 CNF clause, and reconstructs message `0x80000`, codeword
`0x5840d6e180000`, and weight 14 from the frozen generator rows.
The generalized replay reads generator rows from the content-bound metadata
and reproduces the same result.

Mathlib accepted the LRAT dialect and began explicit proof construction, but
the untrimmed trace crossed the 180-second bound without completing and was
interrupted. This kills the untrimmed representation. The verified LRAT
trimmer already present in Lean 4.31 is the remaining narrow successor; it
must materially reduce proof size before another explicit proof-term run.
