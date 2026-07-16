# AxiomPack elementary-tetrahedron prior-art audit

Date: 2026-07-15

## Verdict

The broad abelian-orbit classification claim is a recovery.  After the
coordinate exchange

\[
F(a,b,c)=T(b,a,c),
\]

the campaign's structural laws place the operation in the ternary
differential-mode setting of Kravchenko--Pilitowska--Romanowska--Stanovský
(2008).  That paper already supplies commuting right maps, orbit/block
structure, and the LZ∘LZ reconstruction.

One narrower claim remains unresolved by this audit: the elementary type-2
tetrahedron identity, together with either frozen normalization pack (and
middle injectivity for finalist one), forces differential-mode structure after
the coordinate exchange.  No primary source stating that cross-theory
implication was located.  This is a bounded-search outcome, not a novelty
certificate.

## Exact recurrence

- Finalist zero becomes the hemisemiprojection specialization.  Its order-three
  witness is the published order-three differential-mode example up to carrier
  relabeling.
- Finalist one becomes a differential mode with the last-pair projection law;
  it need not be a semiprojection.
- The finalist-one witness is not related to the published example by a carrier
  relabeling plus one global input permutation.  On the displayed three-element
  carrier the two operations are mutually depth-two term definable:

  \[
  f(x,y,z)=e(e(x,y,y),y,z),\qquad
  e(x,y,z)=f(f(x,y,x),y,z).
  \]

  This statement concerns one finite algebra pair.  It does not establish
  equivalence of the associated varieties.

## Formal boundary

- `AxiomPackFinalistZeroBridge.lean`: the raw finalist-zero laws and ET force
  source fixing and global commutation without injectivity.
- `AxiomPackFinalistOneBridge.lean`: finalist one requires middle injectivity
  for the same conclusion.
- `AxiomPackOrbitAction.lean`: permutation-valued translations admit canonical
  orbit labels and exact reconstruction.
- `AxiomPackFinalistOrbitClassification.lean`: converse operation-level
  constructions are proved; no classification up to ternary-algebra
  isomorphism, parameter conjugacy criterion, counting theorem, or generator
  completeness theorem is asserted.
- `AxiomPackDifferentialModeBridge.lean`: coordinate exchange, differential-mode
  bridge, finalist specializations, published-example match, and both finite
  term interpretations.

The abstract bridge theorems compile with no nonstandard axioms beyond the
ordinary quotient axioms used by the orbit layer.  The explicit order-three
table comparisons use `native_decide` and therefore carry its compiler-trust
boundary.

## Primary sources checked

- A. V. Kravchenko, A. Pilitowska, A. B. Romanowska, D. Stanovský,
  [Differential Modes](https://pages.mini.pw.edu.pl/~pilitowskaa/Diff_KPRS.pdf),
  *International Journal of Algebra and Computation* 18(3), 2008,
  DOI 10.1142/S0218196708004561.
- V. Bardakov et al.,
  [Set-theoretical solutions of simplex equations](https://arxiv.org/abs/2206.08906),
  for the elementary type-2 tetrahedron identity.

Exact terminology searches for the conjunction of elementary 2-solutions,
tetrahedron equations, differential modes, hemisemiprojections, left normality,
and left reductivity did not locate the narrow bridge.  A broader bibliographic
and expert review is still required before using “new” in a publication claim.

## Separate successor result

A later discriminator found a stronger, differently scoped result: the
finalist-one witness negatively answers preprint Question 9.12 / published
Question 9.69 about reconstruction from the extracted T2-groupoid.  Its source
match and forward-citation boundary are recorded in
`t2_reconstruction_question_prior_art_audit.md`.  That result should not be
conflated with the recovered differential-mode classification audited here.
