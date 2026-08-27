# Filtered Obstruction Compiler and the moving contact-zero backbone

**Status:** exact finite quotient, induction, one-flow Puiseux, local
two-flow carrier, and finite polar-prefix descent; selected two-flow
continuation remains open

## Governing identity

The proposed reusable object is an exact finite associated-graded quotient
problem over \(\mathbb Q\).  Its job is to decide whether a distinguished
class survives relations and graded action images.  Its identity consists of:

- an immutable named basis with declared filtration degrees;
- an immutable relation family;
- exact rational linear actions with declared degree shifts;
- optional velocities of the relation generators for a moving quotient;
- a distinguished vector whose class is the obstruction candidate.

The core owns compatibility, rational rank, quotient dimension, and explicit
annihilating witnesses.  Polynomial variables, cusp/contact names, cone
inequalities, and Magnus multiplication placement belong to adapters.  The
existing side-typed Magnus engine is composed after a graded action is
validated; it is not copied into this compiler.

## Eigenquestion

Can this contract both reject the fixed-contact quotient for the arbitrary
contact-zero Jacobian backbone and validate its first moving-contact repair,
before any finite coinvariant is interpreted as an all-order obstruction?

## Exact category obstruction

Use the target Poisson convention

\[
\{H,K\}=H_P K_Q-H_Q K_P
\]

and the exact contact polynomial

\[
C=4P^3-P^2-18PQ+27Q^2+4Q.
\]

The contact-zero Hamiltonians \(P\) and \(Q\) are cone-compatible.  Directly,

\[
\{Q,C\}=-C_P=-12P^2+2P+18Q,
\]

and

\[
\{P,C\}=C_Q=-18P+54Q+4.
\]

Neither polynomial is divisible by \(C\).  Hence the full contact-zero cone
does not normalize the fixed ideal \((C)\), and it has no action on the fixed
associated graded \(\operatorname{gr}_C\).  A finite coinvariant computation
that omits this check is outside the unrestricted moving-family category.

Bare \(Q\) is not in the exact target-lift ideal, so the executable paired
regression uses the cleaner admissible Hamiltonian

\[
H=Q^2.
\]

It belongs to both the cone and target-lift algebra.  For the least
positive-contact witness \(B=Q^2C\),

\[
\boxed{\{Q^2,Q^2C\}=-4Q^3(6P^2-P-9Q)}.
\]

The right side is not divisible by \(C\).  Under the cusp normalization

\[
P=r-\frac34r^2,\qquad Q=\frac14r^2(1-r),
\]

it becomes

\[
\frac1{128}r^7(r-1)^3(3r-2)^3\ne0.
\]

Thus a cone- and lift-compatible contact-zero generator lowers contact depth
one to depth zero in a single target bracket.  Fixed-grade coinvariants are
therefore not merely incomplete; they are undefined for this action.

The infinitesimal moving-divisor repair is exact.  If the divisor velocity is

\[
\dot C=-\{H,C\},
\]

then for every polynomial \(f\),

\[
\{H,Cf\}+\dot C f=C\{H,f\}\in(C).
\]

Thus the pair consisting of the ambient action and the relation velocity,
rather than the ambient action alone, preserves the moving quotient.

## Candidate compiler theorem

For a finite rational vector space \(M\), relation columns \(R\), graded
actions \(A_i\), and relation-velocity columns \(\dot R_i\):

1. reject a nonzero matrix entry whose declared filtration shift is wrong;
2. reject an action unless
   \(A_iR+\dot R_i\subseteq\operatorname{span}(R)\);
3. on compatible input, compute
   \[
   M/(R+\sum_i\operatorname{im}A_i);
   \]
4. if a distinguished vector \(v\) survives, return an exact row functional
   \(\lambda\) with
   \[
   \lambda R=0,\qquad \lambda A_i=0,\qquad \lambda(v)\ne0.
   \]

The functional, rather than quotient dimension alone, is the replayable
obstruction certificate.

## Alien control and counterattacks

The non-Jacobian control uses three graded basis vectors.  Relations remove
the first two, leaving a known one-dimensional quotient.  A compatible action
preserves those relations and leaves the third vector as the distinguished
class.

Two controls must fail:

1. one nonzero action entry is assigned the wrong filtration shift;
2. a relation is carried outside the relation span with no compensating
   velocity.

The second control must pass after the exact compensating relation velocity is
added.  Basis permutation must preserve quotient dimension and the normalized
witness pairing.

Further counterattacks:

- A finite polynomial window can hide incoming action columns.  The compiler
  output is therefore finite unless the adapter supplies a separate
  completeness proof; no stabilization claim follows from repeated ranks.
- A moving relation can preserve the target quotient while its paired source
  lift has unbounded cost.  The moving-quotient receipt does not pay that
  source cost.
- Different Hamiltonians can transport different divisor frames.  Coupled
  parameter-order compatibility remains a connection problem, not a list of
  independent quotient checks.

## Intended Jacobian use

Loop one compiles the exact quotient machinery and makes the fixed-contact
failure, sharp \(Q^2C\) leakage, and moving-divisor repair executable for
\(H=Q^2\).

Loop two must represent the arbitrary contact-zero backbone as a connection
on a moving relation family and expose the induced first-positive-contact
operator together with the paired source transfer.  The decisive successor
question is whether that coupled operator has a prefix-independent
annihilating functional or whether an admissible backbone produces an exact
cancellation schedule.

## Exact cross-grade outcome

The fixed-grade route fails, but its cross-grade replacement has an exact
all-polynomial target calculation.  On the normalization

\[
P=r-\frac34r^2,
\qquad
Q=\frac14r^2(1-r),
\]

the Hamiltonian characteristic of \(C\) satisfies

\[
X_C=(3r-2)^2\frac d{dr}.
\]

Consequently

\[
\{H,C\}\big|_{C=0}
=(3r-2)^2\frac d{dr}H(P(r),Q(r)).
\]

The exact target-lift algebra is

\[
\mathcal H_{\rm lift}=\mathbb Q+(P^3,PQ,Q^2).
\]

Every nonconstant restriction from this algebra is divisible by \(r^3\),
and every derivative through \((P(r),Q(r))\) is divisible by \(3r-2\).
The filtration-order-minus-one image is therefore contained in

\[
r^2(3r-2)^3\mathbb Q[r].
\]

The containment is equality.  The generator leaks are

\[
\begin{aligned}
\{P^3,C\}|_{C=0}
&=-\frac3{32}r^2(3r-4)^2(3r-2)^3,\\
\{PQ,C\}|_{C=0}
&=\frac1{16}r^2(3r-2)^3(5r-6),\\
\{Q^2,C\}|_{C=0}
&=\frac18r^3(r-1)(3r-2)^3,
\end{aligned}
\]

and the exact Bezout identity is

\[
-\frac{200}{3}\{P^3,C\}
-12(15r-22)\{PQ,C\}
=r^2(3r-2)^3.
\]

Thus on every positive contact grade in characteristic zero, the arbitrary
lift-compatible contact-zero target algebra has the universal cokernel

\[
\boxed{
\mathbb Q[r]/\bigl(r^2(3r-2)^3\bigr),
\qquad \dim=5.}
\]

The paired leading source pole is smaller by the axis value of the contact
unit.  If \(Y_H(z)=S_H(r)z^{-1}+O(1)\) in the \(r=uz\) blow-up chart, then

\[
S_H(r)=8\frac d{dr}H(P(r),Q(r)),
\]

so its image ideal is

\[
r^2(3r-2)\mathbb Q[r]
\]

and its cokernel has dimension three.  Multiplication by the axis contact
unit gives the exact sequence

\[
0\longrightarrow
\frac{\mathbb Q[r]}{r^2(3r-2)}
\xrightarrow{\ (3r-2)^2\ }
\frac{\mathbb Q[r]}{r^2(3r-2)^3}
\longrightarrow
\frac{\mathbb Q[r]}{(3r-2)^2}
\longrightarrow0.
\]

The paired comparison therefore leaves a two-dimensional ramification
quotient.  This is not yet the unrestricted logarithmic obstruction:
independent polynomial source symbols, with their source-excess cost, must
also be included.

That source counterattack is now exact at the scalar contact-lowering row.
For the density \(z^2,du\wedge dz\), a source Hamiltonian monomial

\[
G=u^az^b
\]

has, in the blow-up coordinate \(r=uz\),

\[
Y_r=(b-a)r^az^{b-a-2},
\qquad
Y_z=-ar^{a-1}z^{b-a-1}.
\]

Only the diagonal \(a=b\) can enter the contact-zero scalar row.  Polynomial
components force \(a=b\ge3\).  Since

\[
C\circ F_0
=z^2\left(-\frac{(3r-2)^2}{16}+\frac z2\right),
\]

the exact independent source image is

\[
\boxed{r^2(3r-2)^2\mathbb Q[r].}
\]

It contains the contact-zero target leak ideal but still leaves

\[
\frac{\mathbb Q[r]}{r^2(3r-2)^2}
\cong
\frac{\mathbb Q[r]}{r^2}
\oplus
\frac{\mathbb Q[r]}{(3r-2)^2}.
\]

The second summand is the same two-dimensional ramification quotient; no
polynomial weighted-volume source field reaches its value or first jet.
Moreover, the diagonal source Hamiltonian \(G=r^{k+1}\), \(k\ge2\), has
component degree \(2k-1\) and produces a scalar row of radial degree
\(w=k+2\).  The source price is therefore sharp:

\[
\boxed{\deg Y=2w-5.}
\]

An off-diagonal polar source monomial appears to threaten this quotient, but
its earlier Rees layer is triangular.  Write its Hamiltonian as

\[
G=z^{-d}g(r),\qquad d\ge1.
\]

The leading negative scalar layer is

\[
T_d(g)=-dU'(r)g-2U(r)g',
\qquad
U(r)=-\frac{(3r-2)^2}{16}.
\]

For a polynomial \(g\) of degree \(n\), the top coefficient of \(T_d(g)\)
is multiplied by

\[
\frac98(n+d)\ne0.
\]

Hence \(T_d\) has zero polynomial kernel for every \(d\ge1\).  In a finite
coefficient row of a homogeneous source/target gauge difference, choose the
largest polar offset.  Its leading negative layer has no target or smaller
offset source competitor, so the coefficient must vanish.  Descending in
\(d\) removes every polar offset.  The two ramification classes therefore
survive complete finite polar gauge differences, not merely the regular
diagonal slice.

This is the slope-two transfer law needed by the compiler.  The unresolved
step is family excitation: project the arbitrary contact-zero connection and
the least positive-contact multiplier into the two ramification jets and
show that a nonzero class recurs infinitely often, or construct a locally
finite schedule whose covariant jet eventually vanishes.

That instantaneous projection is now complete and rules out the simplest
version of the proposed obstruction.  Put

\[
\tau=3r-2.
\]

The ramification summand is the local algebra

\[
\mathbb Q[\tau]/(\tau^2).
\]

Every lift-compatible contact-zero target leak is divisible by \(\tau^3\),
and the complete polynomial source image is divisible by \(\tau^2\).
Therefore the arbitrary contact-zero backbone acts trivially on both local
jets.

On the other hand,

\[
P'(2/3)=Q'(2/3)=0.
\]

The chain rule shows that every polynomial positive-contact multiplier
\(M(P,Q)\) has zero first \(\tau\)-jet.  Its image lies on the value line.
That line is fully controllable because

\[
Q(2/3)^2=\frac1{729}\ne0,
\]

and \(Q^2C\) is admissible.  The compiler consequently returns rank one
and cokernel dimension one for the map from the \(Q^2C\) control to the two
ramification jets; the surviving class is the first-jet coordinate, but no
polynomial instantaneous multiplier excites it.

Thus the first nonzero coinvariant is a valid structural quotient but not an
instantaneous family obstruction.  The required successor is a covariant
parameter recursion: decide whether transport or BCH creates the dormant
first jet after value-line cancellations, while retaining the known
\(Q^2C\) self-cascade and arbitrary contact-zero backbone.

The covariant target operator after moving-divisor compensation is

\[
\nabla_HM=\{H,M\}|_{C=0}.
\]

Every iterated Poisson bracket is again a polynomial in \(P,Q\), so its
restriction has zero first \(\tau\)-jet by the same chain-rule argument.
The coefficientwise-polynomial target Magnus series cannot excite the
surviving line.  Polynomial weighted-volume source fields are bracket-closed,
and their complete scalar image remains divisible by \(\tau^2\), so the
source Magnus series cannot excite it either.

The reachability compiler makes the distinction explicit.  After quotienting
by the \(Q^2C\) value control it reports ambient cokernel dimension one but
reachable cokernel dimension zero for the complete polynomial-multiplier
forcing span.  The ramification route is therefore closed as an unreachable
coinvariant.  The active successor is the higher source shell created by the
\(Q^2C\) cancellation itself: its known terminal self-cascade must be compiled
modulo an arbitrary coefficientwise-polynomial contact-zero backbone.

The replay is
[`filtered_obstruction_compiler_jacobian_leak_symbol.py`](filtered_obstruction_compiler_jacobian_leak_symbol.py).
It compiles target dimensions five, source dimensions three, and the paired
dimension two in exact rational windows, with basis-permutation controls.

## Critical normalization-node separator

The pure contact-zero adapter supplies an exact all-finite critical velocity
certificate.  With

\[
\widehat P=\frac{x^2(x-6)}8,
\qquad
\widehat Q=\frac{x^3(3x-16)}{64},
\]

the two normalization points (x_\pm=2\pm2\sqrt3) have the same target
image ((-2,1)).  After multiplication by (x^6), every finite critical
target velocity belongs to \(\mathbb Q[\widehat P,\widehat Q]\) and is
therefore node-equal.  The required radial primitive has branch difference

\[
G(x_+)-G(x_-)=\frac{72\sqrt3}{7}.
\]

The fixed-grade compiler records this as an exact separator quotient.  This
settles the finite-velocity span, but forward-`dexp` of a finite logarithm
may contain infinitely many velocity coefficients.

## Puiseux flow lifecycles

### 2026-08-06 authority correction

The one-flow implication is complete.  The two-flow compiler currently has
only a `TWO_FLOW_FACTORIZATION_IDENTITY` receipt, yet it derives regular
finite-route analyticity, equal infinity degrees, the first unequal
infinity exponent, proportional reduction, and final exclusion.  A bare
factorization identity does not construct the selected punctured hidden
branch or prove that its continuation exhausts the finite and infinity
routes.

The local half is now kernel-checked: a constructed
`TwoFlowRamifiedCrossCarrier` builds a complete `TwoJuliaAbelCarrier`, and
the selected critical jets exclude that carrier.  The compiler's two-flow
output must remain conditional until a separate content-bound proposition
constructs the cross carrier from an arbitrary selected polynomial-flow
factorization.  Model identity cannot discharge that proposition.

The compiler now owns two substrate-neutral all-index implications.

For one polynomial generator, a regular germ

\[
F(u)=y+au+cu^\lambda+\cdots,
\qquad a,c\ne0,
\]

with first nonintegral \(\lambda>1\) cannot satisfy Julia's equation for a
polynomial generator: the nonroot branch exposes \(\lambda-1\) one order
too early, while the root branch forces its integer multiplicity to equal
\(\lambda\).

For a product of two polynomial flows whose generators vanish to order at
least two, a through-infinity factorization with nonzero local derivative
forces equal generator degrees.  If their normalized coefficients first
differ in degree (e\ge2), the time-coordinate transition has first
fractional exponent

\[
1+\frac{d-e}{d-1}\in(1,2).
\]

If they are proportional, their product is one polynomial flow.  Therefore
a first nonintegral exponent greater than two excludes any two-sided finite
factorization whose selected continuation supplies the declared
finite/infinity alternative.

That alternative is not exhaustive.  Two finite selected branches can move
between simple equilibria.  Their local exponents are ratios of generator
derivatives, and reciprocal ratios can restore a linear composition.  The
exact equilibrium-transition replay constructs rational generators in
(x^2\mathbb Q[x]) with ratios (3/2) and (2/3) and obtains

\[
u+\frac{77}{12}u^2+\frac{376}{81}u^{5/2}+O(u^3).
\]

The first fractional exponent therefore collides exactly with the Jacobian
critical germ.  This is a local Julia carrier, not a global time-one
factorization, but it invalidates the compiler's finite/infinity route
exhaustion as a general implication.

The critical scalar holonomy nevertheless has an exact infinite-monodromy
escape.  Rationalizing its quadratic sheet produces a degree-seven pole
whose residue polynomial is irreducible modulo (17).  The residue is
irrational, so its exponential multiplier has no positive torsion power.
The reusable finite-root kernel then guarantees an iterate outside the root
set of any fixed nonzero outer generator.  The compiler still needs a
content-bound continuation receipt that lifts these scalar loop iterates to
the two factor branches; a bare factorization identity cannot supply it.

The Jacobian inverse radial holonomy has first fractional exponent (5/2)
with a nonzero coefficient.  The one-flow compiler receipt closes the
prefix-free critical case.  The two-flow receipt closes only the conditional
nonfinite local alternative above.  The Jacobian adapter still owes the
passage from a below-rate-two critical pair to either a selected punctured
cross carrier or an exhaustive finite-equilibrium carrier, followed by
exclusion of the branch produced.  Infinite scalar monodromy reduces that
global task to the loop-transfer proposition.

The remaining category is a finite **positive Rees-grade** prefix.  Its
specialization is polar, so it must be routed through a well-founded
source/target graph-boundary induction before the critical Puiseux theorem
applies.

## Tensor-density polar-factorization lifecycle

The plain Witt lifecycle is insufficient for the Jacobian adapter because
the normal-two target image is not bracket-invariant without its
normal-three companion.  The compiler now has a separate split-module
lifecycle with invariant coordinate

\[
\rho(A)J=2xAJ'-3xA'J-5AJ,
\qquad J_{\rm target}=0.
\]

Its substrate-neutral inputs bind:

- finite positive Rees support under the strict tail hypothesis;
- finite first-defect support on a maximal face;
- the exact split tensor Newton quotient and source cost dictionary;
- an infinite-support critical module certificate; and
- the zero-positive-face terminal certificate.

The compiler owns the all-index recurrence

\[
\rho(x^d)^k(x^e)=
\prod_{i=0}^{k-1}(2e+(2i-3)d-5)x^{e+kd}.
\]

If an orbit terminates, its positive starting exponent has the form

\[
e=\frac{3d+5}{2}-id.
\]

Positivity forces (i\le3), so at most four exponents resonate.  Infinite
critical support supplies a seed outside those exponents and the finitely
many tied Newton classes.  The invariant (he+d\nu) prevents cross-face
cancellation, while (z/(1-e^{-z})) supplies infinitely many nonzero even
depths.  Because the target module vanishes, those coefficients remain on
the source factor.  The resulting slope

\[
\frac{2d}{d-h}>2
\]

eliminates the maximal positive face.  Finite induction reaches the critical
terminal, whose exclusion retains the selected-continuation dependency.

The alien suite checks the positive lifecycle and rejects missing support,
quotient, target-module, cost, infinite-support, terminal, and rate
premises.  The Jacobian adapter is
[`gauge_pure_contact_zero_polar_tensor_induction.py`](gauge_pure_contact_zero_polar_tensor_induction.py).
The older plain-Witt adapter remains fail-closed and documents why the
tensor lifecycle is a distinct category rather than another flag on the
same certificate.

## Exhaustive tail-minimax composition

The final reusable lifecycle composes rather than re-proves its inputs.  A
coefficientwise-finite graded schedule has either empty positive support or a
least positive occurrence.  The compiler requires an all-order lower
certificate for each branch, verifies finite-prefix uniformity and common
statistic/category identity, and accepts an upper construction only when its
bound exactly matches the declared threshold.  Missing branches, finite-only
premises, category mismatches, weak lower bounds, and a nonmatching upper
bound are rejecting tests.

The Jacobian adapter binds the pure tensor induction, the least-positive
moving-backbone induction, and the radial staircase.  Its exact unrestricted
value-two output is conditional because the pure tensor receipt inherits the
unproved critical-terminal transition.  The composition layer remains
substrate-neutral and reusable once every lower-branch receipt has the
authority its proposition requires.

## Kill and stop conditions

- Kill the fixed-coinvariant route if any admissible contact-zero generator
  fails to normalize \((C)\); the displayed \(P,Q\) calculation already does.
- Kill the compiler design if it accepts the wrong-shift or static
  non-invariant-relation controls, depends on Jacobian vocabulary, or changes
  its certificate under basis permutation.
- Stop loop one only after an alien replay, both negative controls, the moving
  repair, and a Jacobian adapter replay pass.
- Do not close the Jacobian campaign on the finite critical certificate.  The
  polar-prefix removal/charge induction is available, while the selected
  two-flow continuation-to-cross-carrier theorem remains live.

## Intended formal surface

Lean formalization, if promoted, should separate three reusable kernels:
finite rational quotient linear algebra, well-founded transition-graph
composition, and the exact rational inequalities in the one-/two-flow
Puiseux alternatives.  The polynomial time-coordinate expansion and
all-order completeness of the Jacobian adapter remain separate obligations.
