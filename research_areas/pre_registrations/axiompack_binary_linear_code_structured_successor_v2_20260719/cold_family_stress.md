---
description: "Independent deterministic stress test of the cold-shot high-transition QC family."
---

# Cold-family stress: high-transition QC graph family

Date: 2026-07-19

This is an out-of-campaign adversarial check of the first family proposed in
`lane_cold_family.md`. It is not an AxiomPack-authored family, does not satisfy
the campaign's authorship contract, and carries no claim about all binary
`[50,20]` codes.

## Check

The probe enumerated all `5^5` phase tuples, canonicalized the 25 cyclic shifts
of each polynomial mask, and recovered exactly 125 canonical members, as
predicted. For every member it constructed the 20 rows

\[
\bigl(x^i(1+x^5),\;x^i(1+x^5)a_\phi\bigr),
\qquad 0\le i<20,
\]

in \(\mathbf F_2[x]/(x^{25}-1)\), checked rank over \(\mathbf F_2\), and
enumerated messages in Gray-code order until it found a word of weight at most
13. The lowering reused `BinaryGeneratorMatrix` and
`gf2_rank_with_dependency` from `binary_linear_code.v1`; no new verifier was
introduced.

## Result

- canonical family size: `125`;
- rank distribution: `rank 20: 125`;
- first rejection-weight distribution:
  `weight 6: 4`, `weight 8: 12`, `weight 10: 41`, `weight 12: 68`;
- largest Gray step needed for a rejection: `30`;
- survivors: `0`;
- canonical ordered member/rejection digest:
  `ad0fd74524da72543bf1c5a27a6ea1ad96732c6ae26a88af4045247878e8438c`.

The lexicographically first member, with phase tuple `(0,0,0,0,0)`, has
generator artifact digest
`86f28b90eda7f56ffa4e6e043129f9ff511bf8e9f5f531290eebb42ef7fd3f50`.
Message `0x3` produces codeword `0x200002000063` of weight 6.

## Disposition

The family is decisively killed before any full minimum-distance scan is
needed: every member has an explicit nonzero message producing a word of
weight at most 12. The proposed design removed one anticipated weight-13
obstruction but left much cheaper two-row and few-row cancellations. The next
mathematical lever is therefore not a richer phase search inside this family;
it is a construction in which pairwise generator-row sums are constrained at
design time, or a different module ideal.

The check also validates the campaign's requested execution shape: a finite
parameter domain plus deterministic lowering plus an existing singleton
verifier is enough to dispose of a family without putting binary-code
vocabulary into the common kernel. What is missing in the live runtime is the
generic identity/coverage/provenance envelope joining those pieces.
