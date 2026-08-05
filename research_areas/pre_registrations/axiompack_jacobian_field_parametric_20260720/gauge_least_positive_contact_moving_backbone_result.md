# Moving-backbone graph quotient and current-row support

## Result boundary

Two exact statements are now separated.

First, an unpaired positive target row can leave a strong finite
opposite-parity source residue, but that residue is not a class until the
coupled boundary graph is removed.  For `Q2C`, `Q6C`, and `Q3C2`, the exact
pair

\[
(8H(P_0,Q_0),H)
\]

compresses to zero under ((L,H)\mapsto L-8H(P_0,Q_0)).  Stable unpaired
annihilators are retained as rejecting fixtures.

Second, put (u=v+1) and (z=2+2t-3v).  The exact rational family satisfies

\[
P_s,Q_s\in\mathbb Q(s)[u^az^b:b\ge a].
\]

The semigroup is closed under products and parameter-coefficient extraction,
so

\[
H_s(P_s,Q_s)\in
\mathbb Q[u^az^b:b\ge a][[s]]
\]

for every coefficientwise-polynomial target Hamiltonian series.  In
contrast, the transverse (Z_m) Hamiltonian has exponent

\[
(3m-5,m+2)
\]

and normal order (7-2m<0) for (m\ge4).  No current target coefficient of
any polynomial degree reaches that coordinate.

## Compiler changes

`FilteredSurplusProjectionProblem` now supports an affine surplus demand and
distinguishes:

- an unreachable surplus demand;
- a reachable surplus with separated terminal residue; and
- an exact common control solving both equations.

`FilteredGraphQuotientProblem` compiles a source/target direct sum modulo the
graph of a homogeneous boundary map.  It reindexes the target filtration by
the map shift, validates relation descent through the existing symbol
compiler, and independently checks the canonical compression

\[
(s,t)\longmapsto s-\Phi(t).
\]

The focused compiler suite has 27 passing tests, including affine positive
and negative controls, exact graph boundaries, a nonzero compressed class,
nonzero filtration shift, bad relation descent, and moving-boundary refusal.

## Replays

- [`gauge_least_positive_contact_moving_backbone.py`](gauge_least_positive_contact_moving_backbone.py)
  owns the finite affine and exact-boundary comparison.
- [`gauge_moving_pullback_normal_semigroup.py`](gauge_moving_pullback_normal_semigroup.py)
  owns the exact rational support theorem and graph stress windows.
- [`filtered_obstruction.py`](../../../src/ztare/common/filtered_obstruction.py)
  owns the substrate-neutral compilers.

## Remaining obstruction

This excludes same-order target cancellation at all weights.  It does not
exclude a lower target coefficient whose transported source letter enters
the negative-normal layer after Magnus brackets.  The unrestricted symmetric
tail minimax therefore remains open.  The successor is the all-order
triangular transport complex on normal layers, with source and target budgets
retained through every edge.

## Defect-five causal theorem

The successor transport edge now has an all-order cutoff.  For

\[
E_{a,n}=u^az^{a+n},
\]

the exact density-(z^2) bracket is

\[
[E_{a,m},E_{b,n}]
=(mb-an)E_{a+b-1,m+n-2}.
\]

If a Magnus word uses instantaneous derivative orders (j_i) and normal
orders (n_i), define (\delta_i=n_i+2j_i).  At logarithmic order (q),

\[
n_{\rm out}+2q=2+\sum_i\delta_i.
\]

The (Z_q) terminal has (n_{\rm out}=7-2q), hence

\[
\sum_i\delta_i=5.
\]

All instantaneous normal orders are nonnegative by the exact source-only and
moving-pullback support theorems.  Thus every contributing derivative order
satisfies (j_i\le2).  No later moving-backbone coefficient can alter this
ray.

The deterministic replay is
[`gauge_normal_defect_five_causality.py`](gauge_normal_defect_five_causality.py).
It derives the exact source-only Hamiltonian, checks its thirty-monomial
support and Hamilton equations, proves the monomial bracket symbolically,
and includes a negative-normal rejecting control.

The former infinite scheduling problem is now a finite-row problem with
unbounded radial degree: classify all admissible velocity rows (j=0,1,2)
in the defect-five quotient and decide whether their induced Magnus tail is
nonzero or transfers an asymptotic payment to the target side.

## Two-jet discriminator

That finite-row coefficient is not invariant.  Exact right-Magnus replay
through order ten compares the source-only, controlled-source-zero, and
minimum-cap two-jets.  The first and third have nonzero \(Z_q\) coefficients
at every checked order \(5\le q\le10\); the controlled two-jet has zero
coefficient throughout the same window.  Order five alone is a rejecting
fixture for any compiler that treats the \(Z_q\) coordinate as a class
before quotienting the complete two-jet contact fiber.

Thus the defect theorem reduces the dependency to three instantaneous rows,
but the \(Z\)-ray does not survive their coupled quotient.  The next carrier
must be selected only after compiling that quotient.  The existing
controlled bigraded terminal is a candidate because it has an exact
all-order escape law, but its complete order-one cancellation fiber and the
corresponding transferred costs must be included before any minimax claim.

## Complete-shell interpolation quotient

The one-parameter source-only-to-controlled interpolation removes more than
the named (Z_q) coordinate.  At logarithmic orders five and six, every
homogeneous source-Hamiltonian grade on or above the rate-two face has zero
linear cokernel modulo the span of exact interpolation differences.  The
checked Hamiltonian degree ranges are (13\ldots29) and (15\ldots37),
respectively.  Held-out rational interpolation values and reversed monomial
bases preserve every rank, while the target logarithm remains below rate
two in the same windows.

This is a rejecting fixture for fixed-grade linear carrier searches.  It is
not an exact cancellation schedule, because different grades may use
different linear combinations of interpolation samples.  A viable successor
has to compile cross-grade nonlinear compatibility and the charged Newton
surplus produced by cancellation, rather than quotient each terminal
coordinate independently.

## Shared-control correction

Enforcing one interpolation control across all homogeneous grades reverses
the grade-by-grade verdict.  The complete retained bundles have dimensions
30 and 52 at orders five and six.  Their common variation map has rank four,
and the source-only bundle raises the augmented rank to five at both orders.
Because the (lambda)-dependence has degree four and the exact Vandermonde
matrix has rank four, this separation applies to every rational
specialization on the declared interpolation, not only the sampled values.

Thus some source derivation degree at least (2q) survives at each checked
order for every member of this one-parameter family, while the target side
stays below rate two.  This is the first carrier that survives changing the
representative: it is a compatibility functional on the full grade bundle,
rather than a coefficient in one grade.  Its scope remains the controlled
interpolation at two finite orders; the complete finite contact fiber and
all-order propagation are still required.

## Complete low-weight tangent

The shared-control separator also survives the controlled column together
with every canonical row-one contact-zero symbol through cusp weight
thirteen.  Weights five through eleven give control rank eight and augmented
rank nine; held-out weights twelve and thirteen give control rank ten and
augmented rank eleven.  The same ranks occur at logarithmic orders five and
six, in ambient bundles of dimensions 124 and 164.  All checked target
columns stay below the rate-two face.

This excludes every single-direction finite difference in the declared
window.  It does not yet exclude mixed direction terms or higher parameter
rows, so it is not an arbitrary-backbone theorem.  The immediate successor
is the quadratic common-domain closure, followed by a multivariate
Vandermonde certificate if the separation persists.

## Quadratic common-domain closure

The separator survives a stronger relaxation in which every linear and
quadratic Taylor monomial in the controlled and row-one directions receives
an independent common column.  In the held-out weight-thirteen window, 65
columns have ranks 42 and 55 at orders five and six; the source-only bundle
raises the augmented ranks to 43 and 56.  Every corresponding target
coefficient has derivation degree at most six.

This excludes the full quadratic Taylor span in the declared finite
direction window.  Weighted control cost now gives a finite exact successor:
retain every monomial of cost at most the logarithmic order, using cost one
for the controlled direction and cost two for row-one symbols.  That will
close all nonlinear dependence in these two orders before any extrapolation
in weight or logarithmic order.

## Complete weighted monomial relaxation

The complete weighted relaxation reverses the quadratic verdict.  At order
five, training and held-out common-control ranks are 36 and 48, and adjoining
the source-only bundle raises neither rank.  At order six the corresponding
ranks are 58 and 82, again unchanged by adjoining the bundle.  The declared
domains contain 89/131 weighted monomials at order five and 209/351 at order
six.  Permuting blocks and bases leaves these certificates unchanged.

This kills the finite linear compatibility carrier once all admissible
weighted monomial columns are granted independent coefficients.  It does not
provide a control schedule: coefficients of an actual polynomial family lie
on the monomial parameter variety and cannot be chosen independently.  The
distinction matters because the quadratic relaxation survives while the
higher weighted relaxation reaches the bundle.

At order five, some reaching columns also attain target derivation degree
ten, so they must be charged in a two-sided rate-face quotient.  At order six
all target columns have derivation degree at most ten, below the threshold
twelve.  The next exact object is therefore a filtered polynomial fiber:
source and target quotient equations evaluated on one shared control point,
with their monomial identities preserved.  Linear-span membership is now a
rejecting proxy for admissible cancellation.

## Polynomial-fiber repair

Preserving the monomial identities reverses the relaxed-span verdict.  The
order-five training and held-out systems have 36 and 49 independent quotient
equations; the order-six systems have 58 and 82.  All four exact rational
Groebner bases are \(\{1\}\).  Hence the polynomial fiber is empty even after
extension of scalars to an algebraic closure, and in particular there is no
rational amplitude tuple canceling the complete retained rate face.

The order-five compilation includes its one target Hamiltonian grade on the
rate-two face.  Order six has no target grade at that threshold, yet its
source fiber is still empty.  The result explains the previous discrepancy:
the relaxed decomposition gives unrelated values to a control amplitude and
its powers, while an admissible parameter point must satisfy all monomial
identities.

The general-purpose compiler now distinguishes three outcomes: a unit ideal,
a verified rational point, and a proper algebraic ideal with unresolved
rational locus.  Its block validation and exact row reduction reuse the
existing filtered compiler rather than introducing a Jacobian-specific
linear algebra path.

For the Jacobian problem this is still a row-one finite-window theorem.  An
arbitrary coefficientwise-polynomial contact-zero backbone has independent
Hamiltonians in every parameter row.  The next replay must include all rows
below the checked logarithmic order, with control cost equal to row plus one;
only after that finite coefficient jet is compiled can weight or order be
propagated.

## Complete finite coefficient jet

The complete parameter-row replay now includes an independent canonical
contact-zero Hamiltonian in every row below the tested logarithmic order.
For cusp weights five and six, the source-only rate face survives even the
independent-monomial relaxation at orders five and six.  The exact polynomial
fibers are empty.

Adding the held-out weight seven makes the linear relaxations reach, but does
not create a parameter point.  The order-five and order-six ideals both
reduce to \(\{1\}\).  At order six, the direct top-shell equation
\(c_{0,7}^4=0\) forces the new row-zero amplitude to vanish; subsequent exact
eliminations reduce the obstruction to a two-equation rational unit core.

Thus every coefficient row relevant to the finite orders q5/q6 is covered
through weight seven, including all nonlinear interactions of weighted cost
at most the order.  This strictly supersedes the earlier row-one result.  Its
remaining boundary is unbounded cusp weight and logarithmic order.

The compiler improvement is reusable: polynomial fibers now exploit
constant-linear quotient projection, rational triangular pivots, and
pure-power radical zeros before Groebner reduction.  A finite-field pass may
select a smaller likely unit core, but the reported empty-fiber certificate
always comes from an exact recomputation over \(\mathbb Q\).

## Unconditional least-positive-contact induction

The finite coefficient-jet route has now been replaced by an all-index
transition theorem.  The exact cusp-section projection sends

\[
P^aQ^{2d+\epsilon}\longmapsto
\left(-\frac4{27}\right)^dP^{a+3d}Q^\epsilon,
\]

and the identity

\[
P^aQ^{2d+\epsilon}
=\frac{P^aQ^\epsilon}{27^d}
  \sum_{j=0}^d\binom djD^j(-4P^3)^{d-j},
\qquad D=4P^3+27Q^2,
\]

splits every polynomial coefficient row into one parity term and finitely
many positive-\(D\) terms.  The parity section is Poisson closed.  With

\[
\gamma(w,j)=2(w-j-5),
\]

its bracket is grade-additive.

On the weighted face \(\operatorname{wt}(r,z,s)=(1,2,-1)\), the radial
section follows

\[
(a,b)\mapsto(a-1,b+3),\quad\frac{81}{8}quad(a>0),
\]

and

\[
(0,b)\mapsto(2,b+1),\quad-\frac32.
\]

If \(\alpha\in\{0,1,2\}\) is the final \(P\)-exponent after \(m\) steps,
the complete normal-three coefficient is

\[
\left(-\frac34\right)^a
\left(-\frac14\right)^b
\left(\frac{27}{128}\right)^m
\left[-\frac{
(6a+9b+21m-10)
(16am+4a-4\alpha+18bm+37m^2-29m)
}{324}\right].
\]

Its earlier proof sketch incorrectly used \(\alpha\le a\), which fails on
the transient \(0\to2\).  The corrected argument uses
\(0\le\alpha\le2\) and lift admissibility: either \(a\ge1\), or
\(a=0,b\ge2\).  Both factors are then strictly positive before the displayed
nonzero common scale.  The top radial degree is \(w+7m-6\), strictly
increasing in the coefficient-row weight.

The complete same-weight face has one exceptional family:

\[
m=1,\qquad W=6k,
\]

with kernel

\[
K_k=\sum_{\ell=0}^k
9^\ell\binom{k+\tfrac14}{\ell}
P^{3(k-\ell)}Q^{2\ell}.
\]

It exits on the next lower face with the pure coefficient

\[
[z^{3k+3}]R_1(K_k)=-\frac3{2^{3k+4}}\ne0.
\]

Every positive-\(D\) term is already covered by the robust/exceptional
positive-contact transition theorem.  The combined induction therefore has
maximum uncharged descent length one.

## Asymptotic composition and rate

The general compiler now has a separate asymptotic-induction lifecycle.  It
requires an infinite unbounded occurrence family, one exact rate witness for
every closing transition, and payment at the same parameter order.  It
rejects finite support, missing branches, subcritical endpoints, payment
reuse, side mismatches, and nondecreasing uncharged edges.  The same-order
map is injective, so a finite prefix cannot be billed as infinitely many tail
payments.

The infinite-support premise is no longer a Boolean plus an unattached
digest.  It is a content-bound proposition whose context is the compiled
transition graph
`e0935e13bc4525f3e0e0707331cfac5e9a8f2a3cd0674a5e7dfdd0a6925d914d`.
The semantic certificate remains
`83ed836310d28e2468175866d8b74a18a1d6257e1de43309c93ed9635ea7110b`;
the graph-bound proof envelope is
`e4b1e94132e3e054c5e06a9eb1cefe358360981e8011045e7944b99135055108`.

For this adapter, terminal branches inherit the positive-contact limiting
source rate at least \(11/2\).  Every cancellation branch produces a
same-order source payment of rate at least two.  Hence every nonzero least
positive-contact coefficient over an arbitrary coefficientwise-polynomial
moving contact-zero backbone forces

\[
\limsup_n
\frac{\max\{e(Y_n),e(X_{K_n})\}}{n}\ge2.
\]

The conclusion is invariant under shifting the least coefficient index and
under fixed rational specialization because those operations change only
finite affine intercepts after the complete coefficient rows are assembled.
A finite supercritical backbone prefix remains an actor in the local
transition certificates; it is never counted as an asymptotic payment.

The replays are
[`gauge_moving_divisor_odd_remainder_all_depth.py`](gauge_moving_divisor_odd_remainder_all_depth.py)
and
[`gauge_moving_backbone_unconditional_induction.py`](gauge_moving_backbone_unconditional_induction.py).
The proof-carrying compiler campaign has 155 focused passing tests.  The arithmetic
spine is kernel-checked in
[`AxiomPackJacobianMovingBackboneInductionArithmetic.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianMovingBackboneInductionArithmetic.lean).

## Remaining global branch

This theorem is conditional only on the existence of a nonzero
positive-contact coefficient.  A contact whose factorized residual is
entirely contact zero makes the induction vacuous.  The unrestricted
symmetric minimax therefore still requires the pure contact-zero lower
theorem and its comparison with the existing slope-two construction.

### Subsequent completion of that branch

The split tensor-density polar induction now supplies the missing pure
contact-zero theorem, including arbitrary finite supercritical prefixes.
The exhaustive comparison with this result and the radial staircase is
recorded in
[`gauge_unrestricted_tail_minimax_result.md`](gauge_unrestricted_tail_minimax_result.md).
