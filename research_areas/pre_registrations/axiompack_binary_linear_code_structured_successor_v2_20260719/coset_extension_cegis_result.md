# Coset-extension CEGIS pilot result

Date: 2026-07-20

Hypothesis: `H-AXIOMPACK-BLC-20260720-02`

Artifacts:

- pencil: `coset_extension_pencil.md`
- executable: `coset_extension_cegis.py`
- receipt: `coset_extension_cegis_receipt.json`
- receipt digest: `7a6670df8d147e93a334b9e82d16cd31322df3a1a300f430a09f030314a3086b`

## Result

The pilot fixed coordinate-zero shortening of the frozen binary
`[51,20,14]` control, replayed it as a rank-19 length-50 code, placed its
quotient in the canonical 31-bit gauge, and ran exact counterexample-guided
search for a coset at distance at least 14.

The inner referee exhaustively examined all `2^19` words for every proposed
representative. In 300,011 ms it completed 210 proposals and accumulated 211
distinct exact cardinality constraints. The observed minimum coset distances
were:

| minimum distance | proposals |
|---:|---:|
| 6 | 3 |
| 8 | 80 |
| 10 | 127 |

No proposal reached distance 12 or 14. The outer Z3 query ended with
`solver_unavailable:canceled` at the frozen time cap. This is neither a
counterexample to existence nor an exhaustion of the shortening's extension
cone.

## Information gained

The quotient chart is computationally viable at the referee boundary: each
candidate receives an exhaustive low-weight witness, and the stored center
replays as a member of the frozen shortening. The observed bottleneck is the
incremental outer cardinality search after roughly two hundred cuts. The
pilot therefore discriminates chart semantics from solver encoding; it does
not justify returning to raw 20-by-50 matrix search.

The next bounded discriminator keeps the same mathematical instance and
replaces the linear-arithmetic encoding of Hamming distance by native
pseudo-Boolean cardinality constraints. A witness still requires exhaustive
adapter replay. An `UNSAT` response still requires an independently checkable
certificate before it can support the one-shortening covering-radius claim.

## Native pseudo-Boolean follow-up

The same frozen instance was replayed with native pseudo-Boolean cardinality
constraints. Its receipt is `coset_extension_cegis_pb_receipt.json`, digest
`019ee454238653aaea3df31d4efb6e52e71455ad23c4464a05dff1941ee63e69`.
Under the same 300-second cap it completed 385 exact referee iterations, an
83.3% throughput increase over the 210-iteration linear-arithmetic run. The
minimum-distance histogram was 7 proposals at distance 6, 165 at distance 8,
and 213 at distance 10. Again no proposal reached 12 or 14, and the solver
ended unavailable at the time cap.

This confirms that the encoding was one bottleneck but does not make the
incremental-cut chart decisive. The next mathematical discriminator should
use the parity-check/syndrome representation or a certificate-producing
covering formulation, rather than spending another capped run on the same
incremental proposal order.

## Random-landscape control after the quotient audit

The later common-carrier audit supplied a cheap control on the same
coordinate-zero shortening. Four deterministic `random.Random` streams
(seeds `0,1,2,3`) proposed 100,000 50-bit representatives each. Every
proposal was scored against all `2^19` shortening words using the same frozen
matrix and exact integer popcount semantics (CPython 3.13.5, NumPy 2.4.3).
The aggregate exact-distance histogram was

`2:1, 3:3, 4:43, 5:403, 6:2995, 7:18175, 8:82293, 9:169571,`
`10:115080, 11:11435, 12:1`.

The unique distance-12 representative was `0x13e78a0e278f6`. Complete replay
examined 524,288 words and returned reducing message `0x01876`, codeword
`0x03e70e6301876`, and weight-12 coset word `0x1000846d26080`.
No sampled representative reached 13 or 14. This explains the observed
distance-12 attractor and supplies no covering bound: the 400,000 samples are
not an exhaustive or proof-producing chart.

## Claim boundary

This result concerns one byte-frozen shortening and one capped solver trace.
It grants no authority over the existence of a binary `[50,20,14]` code, the
other 50 shortenings, the full quotient, kernel ratification, or novelty.
