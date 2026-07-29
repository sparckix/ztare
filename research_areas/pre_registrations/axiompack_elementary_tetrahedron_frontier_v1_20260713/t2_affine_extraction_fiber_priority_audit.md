# T2 affine extraction fiber: theorem and priority audit

Date: 2026-07-19

## Status

The pencil theorem has now been packaged in
`ZtareProofs/AxiomPackT2AffineExtractionFiber.lean` and the module compiles.
This audit separates that exact structural statement from constructions
already present in the tetrahedron-map catalogues. The literature verdict is
still a priority screen, not a proof that no earlier equivalent formulation
exists.

## Eigenquestion

Within the centered biadditive-affine chart, what is the exact fiber of the
Bardakov extraction, and which part remains after known associative-ring maps
and the complete two-color catalogue are taken into account?

## Exact theorem candidate

Let `A` be an additive abelian group. For an additive automorphism
`a : A -> A`, define

\[
\operatorname{Prod}_a(A)=
\left\{\mu:A\times A\to A:
\begin{array}{l}
\mu\text{ is biadditive},\\
\mu(\mu(x,z),q)=\mu(x,\mu(z,q)),\\
a\mu(x,z)=\mu(ax,z)=\mu(x,az)
\end{array}
\right\}.
\]

For `mu` in this set, put

\[
T_{a,\mu}(x,y,z)=a(y)+\mu(x,z),
\qquad
R_{a,\mu}(x,y,z)=(x,T_{a,\mu}(x,y,z),z).
\]

The proposed **affine extraction-fiber theorem** has five parts.

1. `R_(a,mu)` satisfies the tetrahedron equation if and only if `mu` is
   associative and `a` obeys the two displayed centroid identities. The
   forward direction follows by zero specializations; the reverse direction
   follows by expansion.
2. With basepoint zero and unary map `a^{-1}`, all five hypotheses in the
   Bardakov extraction hold. The extracted operations are

   \[
   x\star y=a(y),\qquad x\circ y=a(x),\qquad
   x\mathbin{\lhd}y=x,\qquad x\mathbin{\rhd}y=y.
   \]

3. Hence extraction on this chart is the split projection

   \[
   \mathcal C(A)=
   \{(a,\mu):a\in\operatorname{Aut}_{+}(A),
                   \mu\in\operatorname{Prod}_a(A)\}
   \longrightarrow \operatorname{Aut}_{+}(A),
   \qquad (a,\mu)\longmapsto a,
   \]

   with zero-product section `a |-> (a,0)`. Its fiber over `a` is exactly
   `Prod_a(A)`, rather than merely containing examples from that set.
4. The ternary operation itself recovers the omitted coordinate uniquely:

   \[
   a(y)=T(0,y,0),\qquad \mu(x,z)=T(x,0,z).
   \]

   Thus `mu |-> T_(a,mu)` is injective, while the extracted four-groupoid
   forgets all of `mu`. The published reconstruction is the zero-product
   section

   \[
   \widehat T_{a,\mu}(x,y,z)=a(y),
   \]

   and `T_(a,mu)=widehat T_(a,mu)` exactly when `mu=0`.
5. If `f : A -> B` is an additive isomorphism, then it intertwines
   `T_(a,mu)` and `T_(b,nu)` exactly when

   \[
   f\,a=b\,f,
   \qquad
   f(\mu(x,z))=\nu(fx,fz).
   \]

   This is an additive-conjugacy criterion. It does not claim classification
   under arbitrary set bijections.

The fourth part supplies the exact inverse to the fiber parametrization; the
fifth identifies the appropriate equivalence relation within the affine
chart. In particular, for `a=id`, the extraction fiber is the full set of
possibly nonunital, noncommutative associative biadditive products on the
underlying additive group `A`.

## Proof skeleton and stress tests

The two tetrahedron composites have middle terms

\[
a^2t+a\mu(x,p)+\mu(ay,q)+\mu(\mu(x,z),q)
\]

and

\[
a^2t+a\mu(y,q)+\mu(x,ap)+\mu(x,\mu(z,q)).
\]

Setting the unused variables to zero separates associativity and the two
centroid identities. Substituting them back proves sufficiency. Biadditivity
then reduces every extraction law to an inverse identity for `a`.

For the conjugacy criterion, set `x=z=0` in the ternary intertwining law to
recover `f a = b f`, and set `y=0` to recover multiplication transport. The
converse is direct.

Declared kill conditions:

- an additional term in the tetrahedron expansion;
- a source-orientation mismatch in any extraction operation;
- a prior source stating the same converse fiber and conjugacy theorem;
- use of arbitrary ternary isomorphisms where only additive isomorphisms were
  proved.

The first two tests have already survived independent symbolic and kernel
checks recorded in `t2_affine_hidden_fiber_pencil.md`. The latter two remain
claim-boundary constraints.

## Primary-source comparison

### Associative-ring maps

Sergeev's classified local-Yang--Baxter family already includes the scalar
specialization `(x, k y + x z, z)`
([arXiv:solv-int/9709006](https://arxiv.org/abs/solv-int/9709006)). This is an
earlier construction-level antecedent of the centered chart.

Igonin proves that, for any associative ring, both

\[
(X,Y,Z)\mapsto(X,Y+XZ,Z)
\]

and the more general `(X,Y,Z) |-> (X,Y+XMZ,Z)` are tetrahedron maps
([arXiv:2203.05552](https://arxiv.org/abs/2203.05552), Proposition 2 and
Theorem 1). The proof constructs an associative product `P*Q=PMQ`; it is a
sufficiency construction and does not state the converse affine criterion or
the later Bardakov extraction fiber.

Consequently, the following claims are absorbed by prior art or direct
consequence replay:

- existence of the `Y+XZ` family;
- the first negative answer to the reconstruction question;
- the observation that associative multiplication can be invisible to the
  later extraction when `a=id`.

What remains beyond those maps is the exact converse and split-fiber
description for all `a`, together with its additive-conjugacy criterion.

The exact arbitrary-`a` equivalence

\[
\mathrm{TE}(T_{a,\mu})\iff
\bigl(\mu\text{ associative}\bigr)\wedge
\bigl(a\text{ satisfies both centroid laws}\bigr)
\]

was not located in the inspected primary sources. Nor were the statement that
the four extracted operations forget exactly `mu`, the complete fixed-`a`
fiber, or the simultaneous additive-conjugacy criterion. These are the
new-looking components; their priority remains externally unconfirmed.

### Complete two-color catalogue

Sadykov exhaustively classifies every set-theoretic tetrahedron operator on a
two-element set
([arXiv:1504.03314](https://arxiv.org/abs/1504.03314)). In the bijective
elementary subfamily with first and third coordinates fixed, the catalogue
contains exactly

\[
\begin{array}{ll}
R_{381}=(x,y,z), & R_{384}=(x,y+1,z),\\
R_{397}=(x,y+xz,z), &
R_{398}=(x,y+xz+x+y+z+1,z).
\end{array}
\]

The fixed-basepoint condition removes `R_384`; `R_397` and `R_398` are the
two pointed presentations of the same nonprojection form, related by the
catalogue's global color-complement symmetry. Thus the campaign's pointed
dichotomy

\[
T=y\quad\text{or}\quad T=y+xz
\]

is a filtered corollary of a published complete catalogue. The nonprojection
example and cardinality-two minimality are also already implicit there. They
remain useful finite regression certificates, but carry no viable priority
claim.

Hietarinta's permutation-type classification concerns coordinate-affine maps
over `Z_D`; Sadykov's full Boolean polynomial catalogue is the decisive source
for the nonlinear `xz` entry.

### Bardakov extraction

Bardakov et al. introduce the extraction and ask whether its reconstructed
solution equals the original
([arXiv:2206.08906](https://arxiv.org/abs/2206.08906), preprint Question
9.12; published Question 9.69). The inspected source states neither a fiber
classification nor the affine converse above. The old nonzero-product maps
therefore yield a negative answer when combined with the checked extraction
formula, but the counterexample object is not new. Before assigning priority
to the negative-answer observation itself, confirm the cross-paper inference
with Bardakov or another specialist.

### Differential-mode boundary

The differential-mode literature explains the earlier finalist witnesses
after coordinate or shallow-term changes, but does not absorb this arbitrary
affine chart: differential modes impose idempotence, entropy, and the relevant
normal/reductive identities. The affine theorem should not be presented as a
new differential-mode classification.

## Priority assessment

The viable statement is:

> On centered biadditive-affine elementary tetrahedron maps, the Bardakov
> extraction is a split forgetful projection. Its fiber over an additive
> automorphism `a` is precisely the set of associative biadditive products
> centralized by `a`, and the proposed reconstruction is its zero-product
> section.

This statement is kernel-checked and more precise than the prior construction
results. The source audit found no matching converse, fiber, or
additive-conjugacy theorem. Priority remains unconfirmed:
an expert may regard the result as a short structural corollary obtained by
combining Igonin's family with Bardakov's later extraction. Current rating:

- mathematical validity: high;
- distinctness from the exact statements inspected: moderate to high;
- publication priority without author/expert confirmation: low to moderate;
- two-point classification/minimality priority: excluded.

## Formal surface now present

The completed packaging contains:

1. the type of centroid-compatible associative biadditive products;
2. extraction equality if and only if the additive automorphisms agree;
3. the fiber equivalence with inverse `T |-> ((x,z) |-> T(x,0,z))`;
4. the additive-conjugacy criterion.

Do not spend a separate theorem lane on the Boolean dichotomy. Cite Sadykov's
catalogue and keep the finite result as a regression test. Current public
claim boundary:

> Kernel-checked classification within the centered biadditive-affine chart
> `T(x,y,z)=a(y)+mu(x,z)`, together with a complete description of the product
> information forgotten by T2-groupoid extraction on that chart. Known
> associative-ring examples lie inside the class; the arbitrary-centroid iff
> theorem and fixed-extraction fiber were not located in the audited primary
> literature.
