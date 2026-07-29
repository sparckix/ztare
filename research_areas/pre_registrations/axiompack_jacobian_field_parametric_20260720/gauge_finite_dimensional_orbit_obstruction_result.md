# Finite-dimensional orbit test

**Status:** algebraic, canonical-translation, and complete affine-normalized
low-weight formal-flow mechanisms excluded; higher-isotropy and non-affine
formal-flow categories remain open

## Eigenquestion

Can a rational reparameterization of the normalized family be placed on a
finite-dimensional source/target orbit

\[
H_u\circ F_{\rho(u)}=F_0\circ\Psi_u
\]

whose logarithmic generators have uniformly bounded spatial degree?

There are two distinct meanings of “finite-dimensional orbit” here:

1. an algebraic polynomial action, evaluable over the rational function
   field in the parameter; and
2. a coefficientwise formal flow of a finite-dimensional polynomial Lie
   algebra whose generic-time maps need not be polynomial.

The first category and the canonical generator-translation route are
excluded below.  The second category is narrower than the original search
but is not excluded.

## Polynomial algebraic orbit obstruction

In target coordinates \(P,Q\) and inverse coordinate \(W\), the generic
family has inverse equation

\[
R_s(W)
=W^3-\frac{s}{2(s+2)}W^4
-\frac{s+4}{2(s+2)}W^2
-\frac{12}{(s-6)(s+2)}PW
+\frac{s-4}{2(s+2)}Q.
\]

Over \(\mathbb Q(s,P,Q)\), this has generic degree four.  At \(s=0\),

\[
R_0(W)=W^3-W^2+PW-Q
\]

has degree three.  These are the already established generic fiber degrees
of \(F_s\) and \(F_0\).

Let \(\rho(u)\in\mathbb Q(u)\) be nonconstant.  Base change
\(s\mapsto\rho(u)\) preserves the generic degree four.  If

\[
H_u,\Psi_u\in\operatorname{Aut}_{\mathbb Q(u)}\mathbb A^2
\]

were polynomial automorphisms satisfying

\[
H_u\circ F_{\rho(u)}=F_0\circ\Psi_u,
\]

then the two sides would induce isomorphic function-field extensions.
Polynomial automorphisms on source and target do not change their degrees,
so the left side would have degree four and the right side degree three.
This is impossible.

Consequently the family is not contained, after any nonconstant rational
reparameterization, in a finite-dimensional algebraic polynomial
source/target orbit of the seed.  The same argument excludes a
finite-dimensional polynomial Lie algebra when its action integrates to a
polynomial algebraic group action.

This does not conflict with the coefficientwise formal contact.  Its
unbounded spatial-degree coefficients do not assemble into polynomial
automorphisms over \(\mathbb Q(s)\).

## Canonical translation algebra obstruction

The reciprocal escaping root can be flattened inside the completed inverse
presentation.  Let

\[
z_\circ=\frac{s}{s+4},\qquad
\phi=\frac1{z_\circ}-\frac1z.
\]

Then

\[
W'=W+\phi(P,Q,s)
\]

satisfies

\[
1-zW=\frac z{z_\circ}(1-z_\circ W').
\]

These changes form the abelian vertical-translation group

\[
T_\phi(P,Q,W)=(P,Q,W+\phi(P,Q)),
\qquad
T_\phi T_\psi=T_{\phi+\psi}.
\]

Its Lie algebra is

\[
\mathbb Q[P,Q]\partial_W,\qquad
[f(P,Q)\partial_W,g(P,Q)\partial_W]=0.
\]

The associated escaping-root equation is

\[
Z=\frac14-xZ^3+yZ^4,\qquad
x=s^2P,\quad y=s^3Q,
\]

and the sharp part of the translation is

\[
\Phi(x,y)=4-\frac1Z=-4xZ^2+4yZ^3,
\qquad
\phi=s^{-1}\Phi(s^2P,s^3Q)+\text{higher Rees valuation}.
\]

On \(y=0\), put \(U=4Z\).  Then

\[
U=1-\frac{x}{16}U^3.
\]

Lagrange inversion gives, for every \(k\ge1\),

\[
\boxed{
[s^{2k-1}P^k]\phi
=
\frac{(-1)^k}{2\,16^{k-1}(3k-1)}
\binom{3k-1}{k-1}
\ne0.
}
\]

Thus

\[
\deg_{P,Q}[s^{2k-1}]\phi\ge k
\]

on an infinite sequence.  A finite-dimensional subspace of
\(\mathbb Q[P,Q]\partial_W\) has a uniform polynomial-degree ceiling.
Therefore the canonical reciprocal-root flattening is not a curve in any
finite-dimensional Lie subgroup of vertical generator translations.

This is an all-order obstruction derived from the generating equation.  It
does not rely on the replayed coefficient prefix.

## Solvable two-control bracket escape

The complete lowest-weight target normal form uses the solvable Hamiltonian
algebra

\[
\mathfrak a=\operatorname{span}\{P^3,PQ\},
\qquad
[PQ,P^3]=-3P^3.
\]

Let \(A=V_0\) and \(B=V_1\) be the first two coefficient fields of the exact
source connection induced by this normalization.  In the adapted source
coordinates

\[
g=2t-3v,
\]

their top weighted Hamiltonians, for density \(g^2\), are

\[
h_A=\frac18(vg)^6,
\qquad
h_B=-\frac3{56}(vg)^7.
\]

The top parts commute, so a one-bracket test would miss the obstruction.
The first surviving word is

\[
C=\operatorname{ad}_A^2B,
\qquad
\operatorname{top}h_C
=-\frac3{128}v^{11}g^{10}.
\]

For weighted monomial Hamiltonians,

\[
\left[
X_{cv^ag^b},
X_{dv^Ag^B}
\right]_{\rm top}
=
X_{cd(bA-aB)v^{a+A-1}g^{b+B-3}}.
\]

It follows inductively that

\[
\operatorname{top}h_{\operatorname{ad}_A^jC}
=c_jv^{11+5j}g^{10+3j},
\qquad
c_{j+1}=\frac34(2j+1)c_j.
\]

Every \(c_j\) is nonzero, and the source-field degrees are

\[
\boxed{18+8j}.
\]

Thus the source projection of this exact connection has
infinite-dimensional Lie closure.  No finite-dimensional source/target Lie
algebra can contain it, because projection to the source factor is a Lie
homomorphism.

## Complete affine-normalized weight-three lines

The strongest one-dimensional candidate is the normalized abelian line

\[
H_0=-\frac1{36}P^3-\frac14Q^2.
\]

The unique scalar control making its source connection affine on the
exceptional divisor is

\[
u(s)=
\frac{6912(s^2-3s-8)}
{(s-6)^3(s-4)^2(s+4)^2}.
\]

The connection vanishes at \(s=0\).  If

\[
A=[s]V_s,\qquad B=[s^2]V_s,
\]

then

\[
h_A=-\frac3{448}(vg)^7,
\qquad
h_B=\frac7{2048}(vg)^8.
\]

Again the top parts commute, but

\[
\operatorname{top}h_{\operatorname{ad}_A^2B}
=-\frac{23}{262144}v^{14}g^{13}.
\]

Subsequent brackets obey

\[
c_{j+1}=-\frac3{64}(2j+1)c_j\ne0,
\qquad
\deg\!\left(\operatorname{ad}_A^j
\operatorname{ad}_A^2B\right)=24+10j.
\]

The same computation classifies every first-order seed-isotropy shift

\[
H_\lambda
=-\frac14Q^2-\frac1{36}P^3+\lambda K_*.
\]

For \(\lambda\ne0,2/3\), the unique scalar profile removing the divisor
cubic is regular at \(s=0\), and the source connection has

\[
\operatorname{top}h_{V_0}
=\frac{3\lambda}{32(3\lambda-2)}(vg)^6,
\]

\[
\operatorname{top}h_{[V_0,V_2]}
=
\frac{27\lambda^2}{4096(3\lambda-2)^2}
v^{11}g^{10}.
\]

The all-order ray is

\[
\operatorname{top}h_j
=c_jv^{11+5j}g^{10+3j},
\qquad
c_{j+1}
=
\frac{9\lambda(2j+1)}
{16(3\lambda-2)}c_j,
\]

so it has nonzero source degrees \(18+8j\).  The case \(\lambda=0\) is the
abelian calculation above.  At \(\lambda=2/3\), the target divisor cubic
vanishes at \(s=0\) while the source cubic does not, so no regular scalar
profile supplies the affine normalization.

Consequently every affine-normalized weight-three target line, together
with the complete lowest-weight two-control algebra, is excluded from a
finite-dimensional formal source/target orbit.

## Remaining formal-flow category

A bounded-degree polynomial vector field can have a coefficientwise
polynomial formal exponential whose generic-time sum is rational rather
than polynomial.  The standard one-variable example is

\[
\exp(u\,w^2\partial_w)(w)=\frac{w}{1-uw}.
\]

Such a one-dimensional formal Lie orbit can change generic polynomial
degree because it is absent from
\(\operatorname{Aut}_{\mathbb Q(u)}\mathbb A^2\).  The generic-degree
argument therefore does not exclude it.  Nor does the vertical-translation
argument exclude a nonlinear flow that moves \(P,Q,W\) together.

The surviving Vector C question is now narrower:

> Is there a finite-dimensional bracket-closed algebra using higher
> seed-isotropy weights, or a non-affine exceptional-divisor profile, whose
> coefficientwise formal action gives the contact even though its
> generic-time maps are nonpolynomial?

Any positive answer must exhibit the algebra, its bracket table, and an exact
integration identity.  Any negative answer needs a gauge-independent
associated-graded class outside every such algebra.  Existing finite Magnus
prefixes do not decide this.

## Replay

[`gauge_finite_dimensional_orbit_obstruction.py`](gauge_finite_dimensional_orbit_obstruction.py)
checks:

- the quartic/generic and cubic/seed inverse degrees;
- the structural identity \(q_s'=Wp_s'\);
- the abelian vertical-translation bracket;
- and the displayed nonzero sharp coefficient formula against the exact
  fixed-point recursion through a declared regression range.

The coefficient formula and the function-field degree argument are the
all-order proofs; the finite range is only a deterministic consistency
check.

[`gauge_finite_lie_orbit_bracket_escape.py`](gauge_finite_lie_orbit_bracket_escape.py)
checks the exact \(\langle P^3,PQ\rangle\) source connection, its first
surviving word, and the \(18+8j\) weighted leading ray.

[`gauge_finite_abelian_orbit_bracket_escape.py`](gauge_finite_abelian_orbit_bracket_escape.py)
checks the normalized abelian line, its affine divisor restriction, and the
\(24+10j\) ray.

[`gauge_weight_three_line_bracket_escape.py`](gauge_weight_three_line_bracket_escape.py)
checks the symbolic \(\lambda\)-family and its two exceptional parameters.
