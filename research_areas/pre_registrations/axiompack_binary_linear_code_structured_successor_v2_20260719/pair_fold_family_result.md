# Complete pair-fold family result

Date: 2026-07-20

## Outcome

The exact referee exhausted all

\[
\binom{51}{2}=1{,}275
\]

unordered coordinate pairs of the frozen binary `[51,20,14]` control. Its
source-span replay examined all `2^20 - 1 = 1,048,575` nonzero messages and
recovered 1,595 words of minimum weight 14. Their two-shadow covers every
coordinate pair.

For every pair `{p,q}`, the receipt supplies a weight-14 source word containing
both coordinates. Under the fold

\[
(z_p,z_q)\longmapsto z_p+z_q,
\]

that word loses exactly two support points and becomes a nonzero word of
weight 12. Direct GF(2) elimination independently confirms rank 20 for every
folded generator. Thus all 1,275 members fail the `[50,20,14]` predicate.

The deterministic replay produced byte-identical receipts twice. Canonical
receipt digest:
`bb6e373f24bc9de3b9882fd9f8a3d3fe02377b98246d8d07a1ef13466431a89d`.

Artifacts:

- `pair_fold_family_oracle.py`
- `pair_fold_family_oracle_receipt.json`

## Claim boundary

This is an exhaustive result only for the pair-fold descendants of the one
byte-frozen source code. It neither proves nonexistence of binary
`[50,20,14]` codes nor supplies a novelty claim.

## Representation consequence

The puncture, shortening, and pair-fold families now jointly close the
one-coordinate and two-coordinate descendant routes from this source. The
selected quasicyclic graph family is independently closed by the weight-10
transversal obstruction. A successor should therefore change construction
identity—rather than apply another local coordinate lowering or matrix
perturbation to either frozen seed—and retain the registered exact binary-code
verifier as referee.
