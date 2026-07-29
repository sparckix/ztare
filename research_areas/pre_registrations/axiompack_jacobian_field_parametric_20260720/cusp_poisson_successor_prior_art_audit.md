# Historical-priority audit for the cusp-Poisson successor package

**Audit cutoff:** 2026-07-29
**Scope:** the exact coordinate package developed in
[`gauge_moving_poisson_section_pencil.md`](gauge_moving_poisson_section_pencil.md),
[`gauge_minimum_section_lie_cone_pencil.md`](gauge_minimum_section_lie_cone_pencil.md),
and
[`gauge_paired_cusp_defect_transfer_pencil.md`](gauge_paired_cusp_defect_transfer_pencil.md).

## Bottom line

No exact coordinate-equivalent theorem was located in the audited current
Jacobian-counterexample sources or in the targeted older sources below.  This
is a bounded literature result, rather than a certification of priority.

The audit also identifies substantial classical structure inside the package:

1. the cusp restriction
   \(\mathbb Q[X,Y]\to\mathbb Q[r^2,r^3]\) and the normal form
   \(\mathbb Q[X]\oplus Y\mathbb Q[X]\) are elementary numerical-semigroup and
   hypersurface-division facts;
2. that affine-in-\(Y\) space is the one-dimensional polynomial instance of
   the standard Lie algebra of fibrewise-affine Hamiltonians;
3. the ambient monomial bracket is a classical Hamiltonian/area-preserving
   algebra and is exactly a Block-type Lie algebra after reindexing;
4. the Euler and Hamiltonian generators of vector fields tangent to the
   semicubical cusp are standard Saito-module data;
5. source-versus-target infinitesimal transfer belongs to the classical
   right-left-equivalence framework for map germs.

The narrow priority candidates are the constraints placed on those known
objects:

- classification of **graded rank-one Poisson-closed sections** of the cusp
  restriction, including the weight-twelve exclusion and the resulting
  half-rate;
- its associated-graded promotion to the declared triangular filtered
  category;
- the minimum-section-generated Block wedge
  \(b\geq1,\ 0\leq a\leq2b\), together with the exact sharp \(3/7\) ray
  \(X^{2b}Y^b\);
- the paired, category-specific transfer
  \(DY^j\mapsto U_{w-4}\), with exact target/source costs
  \(w/3+1\) and \(2w-9\).

Three later statements sharpen the campaign boundary but do not yet carry
the same priority status:

- the exact adjacent-symbol determinant \(-w/6\) and eventual rank-two
  theorem for every cusp weight \(w\geq17\);
- the source-line transverse-tower obstruction
  \(B\geq3k-3\) for decomposing \(X_{C^k}(F_0)\) into a cone target and a
  strict source response;
- the finite moving-family phase transition at cusp weight twelve;
- the first nonzero opposite-parity class
  \([s]R_2^{\mathrm{even}}=(31-45A^2)/96\) in the exceptional-divisor
  transverse normal form.

No coordinate-equivalent statement was found in the sources already
audited, but those four items have not received a complete independent
citation-chain search.  They should be described as exact successor
theorems with priority unresolved, rather than added to the priority count.

The calibrated description is therefore **a frontier-level narrow theorem
package on a new 2026 object, with historical priority still unconfirmed**.
It should not be described as the discovery of a new Poisson algebra, a new
theory of cusps, or a completed consequence for the Jacobian counterexample.

## Exact coordinate identifications

Put

\[
D=X^3-Y^2,\qquad
\operatorname{res}(X)=r^2,\qquad
\operatorname{res}(Y)=r^3,
\]

and use

\[
\{F,G\}=\frac16(F_XG_Y-F_YG_X).
\]

Then

\[
\mathbb Q[X,Y]/(D)\cong\mathbb Q[r^2,r^3].
\]

The numerical semigroup \(\langle2,3\rangle\) has Apéry set
\(\{0,3\}\) with respect to \(2\).  Equivalently, division by the monic
polynomial \(Y^2-X^3\) gives the unique quotient representative

\[
f(X)+g(X)Y.
\]

Thus the parity representatives

\[
t_m=
\begin{cases}
X^{m/2},&m\text{ even},\\
X^{(m-3)/2}Y,&m\text{ odd}
\end{cases}
\]

are already the standard affine-in-\(Y\) normal forms of the cusp coordinate
ring.  Their Poisson closure follows from the classical affine-Hamiltonian
calculation

\[
\{f+gY,h+kY\}
=\frac16\bigl(f'k-gh'+(g'k-gk')Y\bigr).
\]

Chong states the general cotangent-bundle mechanism explicitly: fibrewise
affine functions form a Lie subalgebra under the canonical Poisson bracket
and identify with a semidirect product of vector fields and functions
([Physica D 433 (2022), §2.2](https://doi.org/10.1016/j.physd.2022.133164)).
Consequently, existence and closure of the displayed parity section should
be treated as recovery.  The campaign's stronger assertion classifies every
graded rank-one closed splitting of this particular restriction; the
standard affine-normal-form observation alone does not supply that
classification.

For monomials,

\[
\{X^aY^b,X^cY^d\}
=\frac{ad-bc}{6}X^{a+c-1}Y^{b+d-1}.
\]

Set

\[
i=b-1,\qquad \alpha=a-b,\qquad
L_{\alpha,i}\longleftrightarrow X^aY^b.
\]

The bracket becomes, up to the overall scalar and opposite sign,

\[
[L_{\alpha,i},L_{\beta,j}]
=\bigl(\beta(i+1)-\alpha(j+1)\bigr)
L_{\alpha+\beta,i+j},
\]

which is exactly the Block-type bracket used by Gao, Xu, and Yue
([arXiv:1210.6160](https://arxiv.org/abs/1210.6160)).  The same determinant
formula is also written as the classical algebra of complex Hamiltonian
symplectomorphisms of \(\mathbb C^2\) by Gaiotto and Abajian
([JHEP 03 (2025) 195, eq. (2.10)](https://doi.org/10.1007/JHEP03(2025)195)).

Under this reindexing, the campaign cone is the explicit Block wedge

\[
i\geq0,\qquad -i-1\leq\alpha\leq i+1,
\]

and its sharp ray \(a=2b\) is \(\alpha=i+1\).  The ambient algebra is
therefore established prior art.  The searched Block-algebra sources state
the full or half Block algebra, without the cusp-selected wedge, its
minimum-lift generating set, or the \(3/7\) cusp-weight extremum.

Finally, for a quasihomogeneous plane curve, Saito's logarithmic-vector-field
criterion supplies the standard module of tangent vector fields
([Saito 1980](https://doi.org/10.15083/00039637)).  In the cusp model,
Oset Sinha and Tari record generators proportional to

\[
2X\partial_X+3Y\partial_Y,\qquad
2Y\partial_X+3X^2\partial_Y
\]

([arXiv:1610.08702](https://arxiv.org/abs/1610.08702), Proposition 3.1 in
the published version).  These are the Euler direction and, up to
normalization/sign, the Hamiltonian direction used in the campaign.
Accordingly, the cusp stabilizer basis is recovery.

## Current Jacobian-counterexample sources

| Source | Exact contribution in the source | Relation to this package |
|---|---|---|
| [*A Counterexample to the Jacobian Conjecture*](https://www.ulam.ai/research/jacobian.pdf), 2026-07-20 | The explicit Keller map, binary-cubic inverse, fibre geometry, discriminant/nonproperness set, and deformation families. | It supplies the public map and global geometry. The full text has no Hamiltonian, Poisson-section, cusp-normalization, or source/target transfer theorem. |
| Alexis Gallagher, [*Weighted lifts from the Jacobian counterexample*](https://github.com/algal/jacobianfun/blob/main/RESEARCH.md), 2026-07-20 | Weighted invariants, the quotient-Jacobian identity, tangent geometry, and the one-variable seed family. | It is the closest source for the weighted lift and seed curve. It does not state the cusp Poisson splitting, Block wedge, or paired cost. |
| D. Fong and Fable, [*The State of the Jacobian Conjectures*](https://jacobianconjectures.com/jacobian/note/), v2, 2026-07-23 | The quasi-torus master equation using the planar bracket \(\{p,q\}=p_tq_w-p_wq_t\), plus global/capped deformation results. | This is the closest current use of the same planar Poisson mechanism. Its theorem concerns the quotient Keller equation, rather than sections of the semicubical cusp restriction or their Lie closure. |
| T. Shaska, [*Graded Keller maps and the Jacobian Conjecture*](https://arxiv.org/abs/2607.20210), v2, 2026-07-25 | Grading signatures, quotient geometry, and order-two vanishing of the quotient Jacobian along the contracted locus. | It supplies adjacent quotient/discriminant geometry. The inspected version states no cusp Poisson section, monomial Lie cone, or Hamiltonian source transfer. |

These version-specific comparisons were checked both by reading the stated
theorems and by full-text queries for `Poisson`, `Hamiltonian`, `cusp`,
`section`, and the distinctive formulas.  Negative term searches only
describe these documents; they do not establish historical priority.

## Older nearest literature

### Numerical-semigroup and cusp coordinate rings

Barucci and Fröberg use the standard numerical-semigroup ring

\[
\mathbb C[S]=\mathbb C[t^{d_1},\ldots,t^{d_\nu}]
\]

and study its differential operators
([arXiv:1109.6118](https://arxiv.org/abs/1109.6118)).  This is the natural
ambient category for \(\mathbb C[t^2,t^3]\).  The particular
\(\mathbb C[t^2]\)-basis \(1,t^3\) follows immediately from the Apéry set
of \(\langle2,3\rangle\).  Neither observation includes a choice of
Poisson-closed section back into \(\mathbb C[X,Y]\).

### Affine Hamiltonians and polynomial Poisson Lie algebras

The fibrewise-affine closure theorem cited above explains the parity
subalgebra.  The determinant monomial bracket is part of the classical
Hamiltonian/area-preserving algebra; the Block reindexing makes the
coordinate equivalence exact.  Arnaudova, Dimiev, Papaloucas, and Tatarova
also studied polynomial Poisson-bracket Lie subalgebras generated mostly by
monomials, including finitely and three-generated cases
([Il Nuovo Cimento B 108 (1993), 1131–1144](https://www.openarchives.gr/aggregator-openarchives/edm/pergamos/000005-uoadl%3A3045937)).
Only the accessible abstract was available for that source, so it cannot
support a claim that the cusp wedge is absent from the full article.  It is
a required citation-chain target before any first-in-literature claim about
the cone.

### Cusp-preserving and volume-preserving equivalence

Saito's logarithmic module and the explicit cusp generators above cover the
basic target stabilizer.  The source/target decomposition of an infinitesimal
map-germ orbit is standard in right-left equivalence, and modern plane-curve
work studies parametrization equivalence and determinacy directly
([Nguyen, arXiv:1901.02758](https://arxiv.org/abs/1901.02758)).
Domitrz and Rieger develop the volume-preserving
\(\mathcal A_\Omega\)-equivalence category for varieties and maps
([2005 manuscript](https://pages.mini.pw.edu.pl/~domitrzw/v--rev.pdf)).
These sources own the surrounding equivalence framework.  The exact
weighted polynomial lift \(U_k\), the minimum degree \(2k-1\), and its
coupling to the defect \(DY^j\) were not located as statements in the
audited material.

## Claim-by-claim priority disposition

| Campaign statement | Nearest established mechanism | Current disposition |
|---|---|---|
| \(X\mapsto r^2,\ Y\mapsto r^3\), kernel \((X^3-Y^2)\) | Semicubical-cusp normalization and numerical-semigroup ring \(\mathbb Q[\langle2,3\rangle]\) | Recovery |
| \(t_{2a}=X^a,\ t_{2a+3}=X^aY\) is a closed section | Unique affine-in-\(Y\) quotient remainder plus fibrewise-affine Hamiltonian closure | Recovery at the existence/closure level |
| Every graded rank-one closed section equals the parity section; degree \(\lfloor m/2\rfloor\) | No exact classification found; proof uses the \(u_6=Y^2\) countercycle and simple spectrum of \(\operatorname{ad}_{XY}\) | Narrow priority candidate |
| Associated-graded promotion to triangular rank-one sections | Standard filtered/associated-graded method | Exact cusp application is a priority candidate; its geometric promotion remains in the pencil layer |
| Ambient determinant monomial bracket | Hamiltonian/area-preserving and Block-type Lie algebra | Recovery |
| Minimum-section Lie closure lies in \(b\ge1,\ a\le2b\) | A particular wedge inside the Block algebra; general monomial Poisson-subalgebra literature | Narrow priority candidate, pending the 1993 citation chain and related Block-subalgebra classifications |
| Sharp ray \(X^{2b}Y^b\) and exact rate \(3/7\) | Elementary extremal calculation after the wedge is identified | The value is a theorem-specific invariant and plausible priority candidate; it is not a new ambient Lie algebra |
| \(DY^j\) restricts to \(r^{3j+3}T\) and transfers to \(r^{w-4}\) in the source | Saito tangent fields and the standard source/target tangent action | The geometric mechanism is classical |
| Strict weighted-volume lift has exact/minimal degree \(2w-9\) | Volume-preserving map-germ equivalence and polynomial divergence-free fields | Category-specific priority candidate |
| Adjacent cone symbols have determinant \(-w/6\); every \(w\geq17\) has rank two | Elementary determinant arithmetic inside the classical Block-type monomial algebra | Exact successor theorem; historical priority not yet audited independently |
| The complete target module contains a transverse \(C^k\) tower forcing source degree \(B\geq3k-3\) in the declared source-line quotient | Higher normal powers of the cusp equation and standard source/target tangent action | Exact category-specific obstruction; historical priority not yet audited independently |
| At moving order six the higher-rank cone saves one source degree over the parity section | Exact finite contact solve, first appearing at cusp weight twelve | Campaign evidence; no historical-priority disposition yet |
| The layer-two exceptional normal form has canonical class \([s]R_2^{\mathrm{even}}=(31-45A^2)/96\) after complete weight-five target reduction | Classical source/target tangent action plus a parity split in the graded exceptional algebra | Exact successor obstruction; historical priority not yet audited independently |
| The moving normalized family excites an unbounded defect sequence | No theorem currently established in the campaign | Open; no priority claim is available |

## Proof-status boundary

Historical priority and proof completeness are separate questions.

- The rank-one arithmetic carrier formalizes the exponent-pair
  classification, countercycle, parity recurrence, bracket scalars, and
  half-rate.  The polynomial-to-monomial simple-spectrum step and the
  filtered triangular promotion remain mathematical arguments outside that
  carrier.
- The cone carrier formalizes exponent-cone closure, the determinant
  exception, the \(3/7\) inequality, and the sharp-ray recurrence.  Its
  identification with the minimum polynomial section and its use by the
  moving family remain outside the carrier.
- The paired-transfer carrier formalizes the weight/exponent/degree
  arithmetic.  The Hamiltonian product rule on the cusp, construction and
  minimality of the strict source lift, and excitation by the moving family
  remain in the pencil argument.
- The cone-symbol carrier formalizes the adjacent determinant, complete
  exceptional-weight list, and eventual rank-two arithmetic.  Its
  interpretation as the first Hamiltonian normal jet remains in the pencil
  layer.
- The transverse-tower carrier formalizes the source-line degree endpoint
  and incompatibility inequality.  The polynomial restriction and complete
  cone-vanishing argument remain in the accompanying pencil proof.

Thus the current package contains kernel-ratified combinatorial cores and
mathematical coordinate identifications, while the full geometric theorem
is not yet represented end to end in Lean.

## Search protocol and limits

The audit used:

- theorem-level reading of the four July 2026 sources above;
- coordinate aliases \(Y^2=X^3\), \(\mathbb Q[t^2,t^3]\),
  Apéry normal forms, fibrewise-affine Hamiltonians, polynomial
  area-preserving algebras, \(w_\infty\), and Block-type algebras;
- exact reindexing of the monomial bracket into Block coordinates;
- searches for the wedge
  \(-i-1\leq\alpha\leq i+1\), the ray \(\alpha=i+1\), and the numerical
  invariant \(3/7\);
- searches for \(DY^j\), \(r^{3j+3}\), \(w-4\), \(2w-9\), cusp
  reparametrization, and volume-preserving source/target lifts.

No relevant exact-formula hit appeared for the distinctive wedge/rate or
paired-transfer formulas.  That search result narrows the public record.
It cannot exclude a differently indexed theorem in older monomial
Poisson-subalgebra, Block-subalgebra, singularity, or isochore-equivalence
literature.

## Safe external wording

The strongest wording supported by this audit is:

> For the semicubical-cusp restriction
> \(\mathbb Q[X,Y]\to\mathbb Q[r^2,r^3]\), we derived a classification of
> graded rank-one Poisson-closed splittings and an exact alternative
> higher-rank Lie cone.  The rank-one split is forced to the parity normal
> form and pays degree rate \(1/2\); the Lie algebra generated by
> minimum-degree lifts stays in a Block-type wedge with sharp rate \(3/7\).
> A specific cusp-stabilizer defect also has an exact target/source transfer
> cost.  The ambient Poisson, cusp, and Block structures are classical; the
> constrained classification, wedge extremum, and paired cost were not
> located in the current Jacobian literature or the targeted older sources.
> Historical priority and the full moving-family implication remain open.

Avoid “first proof,” “new Poisson algebra,” and any claim that the package
settles a consequence of the 2026 counterexample until the remaining
geometric steps are formalized and specialists have checked the older
monomial-Poisson and singularity-theory citation chains.
