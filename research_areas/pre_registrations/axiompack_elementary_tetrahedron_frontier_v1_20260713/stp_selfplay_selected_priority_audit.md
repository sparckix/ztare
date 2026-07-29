# STP self-play selected results: targeted priority audit

Date: 2026-07-17

## Verdict

The four kernel-checked statements are mathematically valid at their declared
boundaries. This audit does not support a frontier-novelty claim for the group
as a whole.

Three statements are exact bookkeeping results for the published extraction
map:

1. an orbit-action extraction samples only the basepoint row and column, modulo
   equality of the induced actions;
2. reconstruction through an action is label factorization modulo the action
   kernel;
3. at common extraction coordinates, the reconstructed ternary operation and
   the four extracted operations are mutually recoverable.

No source inspected states these three in the campaign's notation. Each is,
however, a short specialization of standard machinery: direct evaluation of
the Bardakov extraction, equality in the image of a group action, or mutual
term definability. Their value is as semantic and formalization receipts. A
standalone mathematical-priority claim is implausible.

The fourth statement has a different status. The exact theorem

\[
\begin{gathered}
T(x,x,z)=x,\qquad T(x,y,x)=y,\qquad
y\mapsto T(x,y,z)\text{ injective},
\end{gathered}
\]

together with admissible Bardakov extraction and reconstruction at one
basepoint, is equivalent to `T(x,y,z)=y`. No tetrahedron equation is used.
No exact recurrence was found. Its two diagonal identities are adjacent to the
semiprojection literature, while their coordinate-incidence fingerprint differs
from the published hemisemiprojection pair. This leaves **low-to-moderate
plausible priority for the exact no-go lemma**, pending an author or specialist
check. Search silence does not upgrade that assessment to novelty.

Calibrated result table:

| Result | Exact recurrence located | Immediate older principle | Priority assessment |
|---|---:|---|---|
| orbit-action extraction fiber | no | direct extraction evaluation; restricted `LZ∘LZ` coordinates | very low |
| reconstruction modulo action kernel + witness | no | kernel of `G -> Sym(X)`; pair-groupoid factorization in the image | excluded as a standalone claim |
| reconstructed equality iff four extracted operations agree | no | mutual term definability at fixed coordinates | very low |
| diagonal + middle-injective reconstruction iff middle projection | no | adjacent partial-semiprojection and retract/decomposition theory | low-to-moderate, unconfirmed |

The strongest currently defensible wording for the fourth result is
"an apparently unstated extraction no-go lemma." The words "new" and
"frontier" require external priority review.

## Exact formal statements audited

The compiled artifacts are:

- `ZtareProofs/AxiomPackOrbitActionExtractionFiber.lean`;
- `ZtareProofs/AxiomPackT2ExtractionInvariant.lean`;
- `ZtareProofs/AxiomPackT2DiagonalReconstruction.lean`.

The definitions of the four extracted operations and the reconstructed ternary
operation are in `ZtareProofs/AxiomPackT2ReconstructionCounterexample.lean`.

### 1. Orbit-action extraction fiber

For

\[
T_\kappa(x,y,z)=\kappa(o(x),o(z))\mathbin{\cdot}y
\]

and identity auxiliary map, extraction at `c` gives

\[
\begin{aligned}
x\star y=x\mathbin{\rhd}y
  &=\kappa(o(x),o(c))\mathbin{\cdot}y,\\
x\circ z=x\mathbin{\lhd}z
  &=\kappa(o(c),o(z))\mathbin{\cdot}x.
\end{aligned}
\]

Consequently, two labels have the same four extracted operations exactly when
their basepoint column and row induce the same maps on the carrier for all orbit
indices hit by carrier elements. Labels away from this cross, labels on unused
values of the orbit codomain, and label differences in an action kernel are
invisible.

This theorem needs only an `SMul`; it is a definitional fiber calculation rather
than a classification theorem.

### 2. Reconstruction modulo the action kernel

Let `G` act on `X`, and put

\[
d_c(x,z)=
  \bigl(\kappa(o(x),o(c))\kappa(o(c),o(z))\bigr)^{-1}
  \kappa(o(x),o(z)).
\]

Then Bardakov reconstruction holds exactly when

\[
d_c(x,z)\mathbin{\cdot}y=y
\qquad\text{for every }x,z,y.
\]

Faithfulness is unnecessary. The compiled `C_2`/`Bool` witness uses the trivial
action and a constant nonidentity label: ternary reconstruction holds while
equality of the abstract group labels fails.

### 3. Equality of reconstructed operations

For ternary operations `T,U` satisfying the extraction hypotheses at the same
`c` and auxiliary map `brace`, write `R_T,R_U` for their reconstructed
operations. The inverse-slice clauses give

\[
\begin{aligned}
\circ_T(y,z)&=R_T(c,y,z),\\
\star_T(x,y)&=R_T(x,y,c),\\
\rhd_T(x,y)&=R_T(x,\operatorname{brace}(y),c),\\
\lhd_T(x,y)&=R_T(c,\operatorname{brace}(x),y).
\end{aligned}
\]

Thus `R_T=R_U` exactly when all four extracted operations agree. The reverse
direction uses only `circle` and `right`, because reconstruction is their
composition.

The common `c` and common `brace` are part of the theorem's identity. Dropping
that common-coordinate condition would define a different comparison problem.

### 4. Diagonal reconstruction collapse

For an arbitrary carrier, assume middle-slice injectivity and

\[
T(x,x,z)=x,\qquad T(x,y,x)=y.
\]

At every fixed `c`, the following are equivalent:

\[
\begin{split}
&\text{there exists an auxiliary map satisfying the five extraction clauses}\\
&\quad\text{and reconstructing }T\text{ through }c;
\end{split}
\]

and

\[
T(x,y,z)=y.
\]

The forward proof first forces the auxiliary map to be the identity, then
reduces reconstruction to

\[
T(x,y,z)=T(x,T(c,y,z),c).
\]

Middle cancellation against the diagonal law yields `T(c,y,z)=y`; a final use
of reconstruction and the second diagonal law yields the middle projection.

## Comparison with the primary literature

### Bardakov extraction and its printed question

Bardakov et al. define the second tetrahedral four-groupoid, extract four
binary operations from an elementary type-2 tetrahedron map using a basepoint
and an inverse-slice map, and ask whether the reconstructed middle coordinate
always equals the original one:

\[
[x,y,z]=x\mathbin{\rhd}(y\mathbin{\circ}z).
\]

Primary records:

- V. Bardakov et al., [Set-theoretical solutions of simplex
  equations](https://arxiv.org/abs/2206.08906), preprint Question 9.12;
- [peer-reviewed Russian publication and full
  text](https://www.mathnet.ru/eng/mt697), Question 9.69,
  DOI [10.25205/1560-750X-2024-27-1-5-72](https://doi.org/10.25205/1560-750X-2024-27-1-5-72);
- English translation, DOI
  [10.1134/S1055134424010012](https://doi.org/10.1134/S1055134424010012).

The source gives the extraction and reconstruction formulas. It does not state
the row/column fiber, the action-kernel refinement, the common-coordinate
invariant, or the diagonal collapse theorem.

The earlier campaign audit established that the broad negative answer to the
printed question is already an immediate consequence of published
associative-ring tetrahedron maps. The four results here must therefore be
assessed as refinements of the extraction interface, rather than as priority
for the negative answer. See
`t2_reconstruction_question_prior_art_audit.md`.

### Differential modes and semiprojections

Kravchenko, Pilitowska, Romanowska, and Stanovský construct ternary
differential modes as `LZ∘LZ` sums. On a disjoint union of blocks `A_i`, their
operation has the form

\[
f(a_i,b_j,c_k)=h_{i,jk}(a_i),
\]

where the maps with fixed source block commute. Their Theorem 3.5 reconstructs
every differential mode from a suitable left-zero quotient and its blocks;
Example 3.10 records the finite labeled-graph presentation. See
A. V. Kravchenko et al., [Differential
Modes](https://pages.mini.pw.edu.pl/~pilitowskaa/Diff_KPRS.pdf),
*International Journal of Algebra and Computation* 18(3), 2008,
DOI [10.1142/S0218196708004561](https://doi.org/10.1142/S0218196708004561).

After the coordinate exchange

\[
F(a,b,c)=T(b,a,c),
\]

the orbit-action family is a restricted, permutation-valued instance of this
construction. The extraction row/column theorem becomes the observation that
fixing one quotient coordinate samples the corresponding cross of the maps
`h`. KPRS do not formulate Bardakov extraction, which appeared later, but their
representation makes a priority claim for this sampling observation weak.

KPRS define a hemisemiprojection differential mode by

\[
F(x,x,y)=F(x,y,x)=x
\]

and a semiprojection by adding `F(x,y,y)=x`. Their Proposition 4.5 and Example
4.10 analyze the resulting varieties and nonprojection examples. Pilitowska,
Romanowska, and Stanovský later study the Szendrei subvarieties in
[Varieties of differential modes embeddable into
semimodules](https://www.karlin.mff.cuni.cz/~stanovsk/math/diffmod_szendrei.pdf),
*International Journal of Algebra and Computation* 19(5), 2009, 669--680.

The diagonal theorem has the coordinate-exchanged fingerprint

\[
F(x,x,z)=x,\qquad F(x,y,y)=x,
\]

with injectivity in the first coordinate. This pair is contained in the full
semiprojection laws. It is not the KPRS hemisemiprojection pair under an input
permutation preserving the designated output coordinate: in the KPRS pair the
designated coordinate belongs to both repeated-coordinate pairs, whereas here
it belongs to only one. That incidence count is permutation-invariant.

The commutative-minimal-clone literature supplies broader semiprojection
context:

- K. A. Kearnes and Á. Szendrei,
  [The classification of commutative minimal
  clones](https://math.colorado.edu/~kearnes/Papers/commincl.pdf),
  *Discussiones Mathematicae* 19 (1999), 147--178;
- M. Pouzet and I. G. Rosenberg,
  [Small clones and the projection
  property](https://arxiv.org/abs/0705.1519).

These sources treat semiprojections and projection-valued identification
minors. They do not give the partial two-diagonal, middle-cancellation,
Bardakov-reconstruction criterion proved here. The adjacent clone theory does
make a projection-collapse conclusion less surprising and lowers the plausible
priority of the exact lemma.

### Action kernels and cocycle factorization

A group action is a homomorphism

\[
\rho:G\longrightarrow\operatorname{Sym}(X),
\]

and faithfulness means `ker rho` is trivial. Therefore

\[
g\mathbin{\cdot}y=h\mathbin{\cdot}y\text{ for all }y
\quad\Longleftrightarrow\quad h^{-1}g\in\ker\rho.
\]

This is the full mathematical content needed to pass from exact label
factorization to the compiled action-kernel criterion. A concise institutional
reference is R. A. Bailey's [Group actions
notes](https://maths.qmul.ac.uk/~rab/MTH6104/action.pdf), which defines an
action as a homomorphism to a permutation group and identifies its kernel and
faithfulness.

The exact factorization

\[
\kappa(A,B)=\kappa(A,C)\kappa(C,B)
\]

is also the composition law for a group-valued functor on the pair groupoid;
choosing `C` is a basepoint trivialization. Standard groupoid cohomology calls
homomorphisms to an additive group 1-cocycles and basepoint differences
coboundaries; see B. Mesland, [Groupoid cocycles and
K-theory](https://arxiv.org/abs/1005.3677), Section 3.1. The campaign theorem
compares this factorization only after applying `rho`.

The trivial-action `C_2` witness is a correct finite boundary example. It is
the canonical consequence of allowing a nontrivial kernel, so it carries no
plausible independent priority.

### Mutual term definitions and reconstruction from retracts

The common-coordinate invariant is an instance of mutual term definability:
the reconstructed operation is a term in `right` and `circle`, while the four
binary operations are recovered by specializing the reconstructed operation
and applying the fixed auxiliary map. Universal algebra treats structures with
the same term operations as term-equivalent; see C. Bergman, D. Juedes, and
G. Slutzki, [Computational complexity of
term-equivalence](https://doi.org/10.1142/S0218196799000084),
*International Journal of Algebra and Computation* 9(1), 1999, 113--128.

There is also a substantial reconstruction literature for multary quasigroups
and function minors:

- D. Krotov, [On reducibility of n-ary
  quasigroups](https://arxiv.org/abs/math/0607284);
- D. Krotov, V. Potapov, and P. Sokolova,
  [On reconstructing reducible n-ary quasigroups and switching
  subquasigroups](https://arxiv.org/abs/math/0608269);
- E. Lehtonen,
  [Totally symmetric functions are reconstructible from identification
  minors](https://doi.org/10.37236/2863),
  *Electronic Journal of Combinatorics* 21(2), 2014.

Those results concern full quasigroup invertibility, decks of retracts, or
identification minors, often with arity or cardinality conditions. The compiled
theorem concerns one fixed basepoint, one fixed unary coordinate, and a
specific syntactic reconstruction term on an arbitrary carrier. They are
adjacent precedents, not exact recurrences.

## Query and coordinate-variant log

The audit inspected the full primary texts above and ran the following bounded
query families over arXiv, publisher records, author-hosted papers, and general
web indices:

| Query family | Outcome |
|---|---|
| `"T_2-groupoid" reconstruction`, `"second tetrahedral 4-groupoid"`, `"elementary 2-solution"` | returned Bardakov et al.; no later exact theorem located |
| `"Question 9.12" "Set-theoretical solutions of simplex equations"`, `"Question 9.69" tetrahedron` | no independent resolution located |
| displayed reconstruction identity and its nested form | no exact match beyond the source/campaign artifacts |
| all six input permutations of the two diagonal identities | differential-mode and semiprojection sources were the only relevant algebraic matches |
| `"(xxy)=x" "(xyy)=x"`, `hemisemiprojection`, `semiprojection injective` | located KPRS and clone-theory context; no Bardakov reconstruction criterion |
| `group action kernel faithful`, `pair groupoid cocycle basepoint` | located the standard kernel and cocycle principles used above |
| `n-ary quasigroup retract reconstruction`, `binary retracts`, `identification minors reconstructible` | located the adjacent Krotov and Lehtonen reconstruction lanes |
| `term-equivalence mutual definitions` | located the standard universal-algebraic comparison |

The absence of an indexed match has limited evidential force. Equational
results can occur under different signatures, parastrophes, non-English
terminology, books, or unindexed proceedings. The coordinate-incidence check
rules out the most immediate input-permutation match for the diagonal theorem;
it does not rule out a more general parastrophic or categorical reformulation.

## Claim boundary and next priority check

Supported:

- all four theorem statements at their compiled assumptions;
- the row/column and kernel diagnoses of information lost by extraction;
- the common-coordinate mutual-recovery theorem;
- a narrow diagonal no-go lemma that is logically independent of the
  tetrahedron equation;
- no exact statement of the diagonal lemma in the primary sources inspected.

Unsupported:

- priority for the broad negative answer to the Bardakov question;
- novelty of the orbit/differential-mode representation;
- a standalone novelty claim for any of the first three results;
- a claim that the diagonal lemma is absent from all semiprojection,
  quasigroup, clone, or universal-algebra literature;
- a frontier-mathematics label for this four-result wave.

The next discriminating priority action is a short theorem-only inquiry to the
Bardakov authors and one differential-mode/clone specialist. It should include
the two diagonal laws, middle-slice injectivity, the five extraction clauses,
and the reconstruction formula on one page. A response identifying the lemma
as routine or known would close the priority lane; a response that the exact
criterion is new would justify a second bibliographic pass before any public
novelty wording.
