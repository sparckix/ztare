# QC support theorem to binary-code codec audit

Date: 2026-07-19

## Question and verdict

Does
`AxiomPackQCTransversalObstruction.exists_graph_word_support_weight_le_ten`
already certify that every member of the selected 125-member graph-code
family has minimum distance at most 10?

The mathematical implication is sound, but the current Lean theorem stops at
the two support cardinalities. A finite codec layer is still required to bind
those supports to the bit convention and the first 20 rows of the exact
binary generator matrix. The only nontrivial normalization gap is that the
Lean witness is a shift in `ZMod 25`; it can have representative 21, whereas
the matrix message polynomial must have degree below 20. The normalization
below removes that gap without changing either block weight.

## Exact family correspondence

Work in

\[
R=\mathbf F_2[x]/(x^{25}-1),\qquad G=1+x^5.
\]

For a phase function \(\phi:\mathbf Z/5\to\mathbf Z/5\), let

\[
A_\phi=\sum_{r=0}^4
  \left(x^{r+5\phi_r}+x^{r+5(\phi_r+2)}\right).
\]

In residue class \(r\), the support of \(GA_\phi\) has heights
\(\phi_r,\phi_r+1,\phi_r+2,\phi_r+3\). Hence, for
\(\psi_r=\phi_r+4\),

\[
\operatorname{supp}(GA_\phi)
  = \mathbf Z/25\;\mathbin\triangle\;M_\psi,
\qquad
M_\psi=\{r+5\psi_r:r\in\mathbf Z/5\}.
\]

This is the missing equation connecting the oracle's `phase_mask`, `G`, and
`second_seed` to Lean's `transversal`. The oracle's `rotate25(S,t)` sends a
position \(i\) to \(i+t\), exactly the convention used by Lean's
`translate t S`.

The support theorem applies to every phase function, so it covers all
\(5^5\) raw parameters. To bind the statement to the byte-frozen 125-member
quotient, use either of these equivalent receipts:

1. decode each canonical mask back to a phase function by checking that each
   residue fiber is the unique pair \(\{\phi_r,\phi_r+2\}\); or
2. carry a raw phase and cyclic-shift witness for each canonical mask, then
   use the corresponding coordinate permutation of the second block.

The orbit count is not needed for the inequality; it is needed only to bind
the universal statement to the exact finite-family identity and domain hash.

## Shift and degree normalization

The Lean theorem produces \(d\in\mathbf Z/25\) with \(d\equiv1\pmod5\), so

\[
d_{\mathrm{val}}\in\{1,6,11,16,21\}.
\]

Define

\[
s(d)=
\begin{cases}
d_{\mathrm{val}},&d_{\mathrm{val}}\le12,\\
25-d_{\mathrm{val}},&d_{\mathrm{val}}>12.
\end{cases}
\]

Then \(s(d)\in\{1,4,6,9,11\}\), in particular
\(1\le s(d)<20\) and \(5\nmid s(d)\). If \(d_{\mathrm{val}}\le12\), take
the message \(f=1+x^d\). Otherwise multiply both blocks by the monomial
\(x^{s(d)}\); in the cyclic ring,

\[
x^{s(d)}(1+x^d)=1+x^{s(d)}.
\]

Multiplication by a monomial is a cyclic coordinate permutation, so it
preserves both block weights. Thus the support witness always yields an
admissible message \(f=1+x^s\) using rows 0 and \(s<20\).

For this message,

\[
\operatorname{wt}(Gf)=4
\]

because \(5\nmid s\). Writing \(B=GA_\phi=\mathbf 1+\mathbf 1_M\), the
all-one supports cancel in characteristic two and

\[
\operatorname{supp}(Bf)=M\mathbin\triangle(M+s).
\]

The Lean intersection theorem bounds the latter cardinality by 6, after the
same monomial normalization. Hence the row-span contains a nonzero word of
weight at most \(4+6=10\). Nonzeroness follows already from the first block's
cardinality 4.

## Minimal formal surface

No general polynomial package is required. The smallest codec consists of:

1. `supportMulBinomial`: multiplying a binary cyclic support by
   \(1+x^d\) is symmetric difference with its translate by \(d\).
2. `phaseSecondSeedSupport`: the support of `G * phase_mask phi` is the
   complement of `transversal (phi + 4)`.
3. `normalizeShift`: the construction above returns `s : Fin 20`, a
   monomial shift, and equality of the translated binomial supports.
4. `binomialMessageRows`: the message \(1+x^s\) is exactly the XOR of
   generator rows 0 and `s` in both 25-coordinate blocks.
5. `blockWeight`: the two block embeddings into 50 coordinates are disjoint,
   so total Hamming weight is the sum of their support cardinalities.
6. `canonicalMemberPhase`: each frozen canonical multiplier either decodes
   to the phase-support predicate or carries a phase/shift witness.

This suffices for an existential low-weight row-span word and therefore the
minimum-distance upper bound. If the formal statement also calls every
matrix a `[50,20]` code, add row independence as a separate lemma. It has an
elementary triangular proof: in a vanishing XOR of rows
\(x^i(1+x^5)\), \(0\le i<20\), coordinates 0 through 4 first force the
initial five coefficients to zero, and coordinates 5 through 19 propagate
zero to all remaining coefficients. Rank is unnecessary for excluding
distance 14 once the nonzero weight-at-most-10 word is established.

## Kill conditions

Kill the literal code claim if any of the following occurs:

- `phase_mask` does not decode fiberwise as
  \(\{\phi_r,\phi_r+2\}\), or `G * phase_mask` is not the complement of
  `transversal (phi + 4)` under the oracle's bit convention;
- `rotate25` and Lean `translate` use opposite orientations without applying
  the corresponding sign conversion;
- the normalized \(s\) is not in `1 <= s < 20`, or
  \(x^{s}(1+x^d)=1+x^s\) fails in `F_2[x]/(x^25-1)` in the negative-shift
  branch;
- XOR of rows 0 and \(s\) differs from the two block supports used by the
  theorem;
- the two 25-coordinate block embeddings overlap, invalidating weight
  additivity;
- a frozen canonical parameter cannot be accompanied by either a valid
  decoded phase or a raw-phase/cyclic-shift witness;
- the first support has cardinality other than 4, since that would also lose
  the nonzero-codeword certificate.

No such failure appears in the present definitions. The exact oracle and the
19-shift spectrum independently agree with the resulting uniform bound.

## Resolution, 2026-07-20

`ZtareProofs/AxiomPackQCGraphCodeword.lean` now closes the identity/codec
obligation. Its terminal declaration
`exists_literalSelectedQC_two_row_codeword_weight_le_ten` constructs, for
every phase, a nonzero shift `s : Fin 20` and an explicit XOR of literal
generator rows `0` and `s` whose first-block weight is 4 and whose total
weight is at most 10. The right seed is no longer assumed: the file proves
that multiplying the explicit ten-point phase mask by the binary generator
support `{0,5}` yields the complement-transversal seed used by the
combinatorial obstruction.

The narrow Lean build passes, and the carried terminal declaration passed the
provider-free LeanMill ratification route with a discriminating negated
control and current governance. The content-addressed result is
`qc_literal_codec_governed_ratification.71d13fba2bb1c3b3.json`; its governed
closure-record digest is
`bb5517d1012989136ccd3c977eeaa90c18283b53d1c908672a90ec25186b0756`.

This settles the selected QC family only. It carries no ambient
`[50,20,14]` nonexistence authority. Rank 20 remains independently verified
by the exact oracle and is unnecessary for this distance-14 exclusion,
because the constructed row-span word is already nonzero.
