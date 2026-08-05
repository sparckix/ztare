# Finite-dimensional orbit test

**Status:** complete obstruction to finite-dimensional polynomial
source/target formal-flow orbits; infinite-dimensional tail minimax remains
open

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

Both categories are excluded below.  The second requires an
associated-graded source argument because generic-time maps of polynomial
vector fields need not remain polynomial.

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

## Affine-divisor \(P^3\) control

There is a distinct one-dimensional target candidate from the complete
divisor calculation:

\[
K_s=a(s)P^3,\qquad
a(s)=
-\frac{192(s^2-3s-8)}
{(s-6)^3(s-4)^2(s+4)^2}.
\]

Its divisor source connection lies in
\(\langle\partial_y,y\partial_y\rangle\), so both the target and divisor
Lie algebras are finite-dimensional.  The full source connection is not.
Its first leading Hamiltonians are

\[
h_{V_0}=\frac18(vg)^6,\qquad
h_{V_1}=-\frac3{56}(vg)^7.
\]

Although their first bracket has radial top shell \((vg)^8/32\), the next
adjoint gives

\[
\operatorname{top}h_{\operatorname{ad}_{V_0}^2V_1}
=-\frac3{128}v^{11}g^{10}.
\]

The same weighted-monomial calculation gives

\[
c_{j+1}=\frac34(2j+1)c_j,\qquad
\deg=18+8j.
\]

Thus this affine-divisor candidate also has infinite-dimensional source
Lie closure.

## Complete target-algebra classification

Put

\[
H=P^3+9Q^2,
\]

which is a nonzero scalar multiple of the normalized target seed.  Give
\((P,Q)\) cusp weights \((2,3)\).  Then
\(\operatorname{ad}_H\) raises weight by one.

On the cusp \(H=0\), use

\[
P=-9u^2,\qquad Q=9u^3.
\]

The induced derivation is

\[
\left.\operatorname{ad}_H\right|_{H=0}
=-9u^2\frac d{du}.
\]

Its iterates kill only constants in \(\mathbb Q[u]\).  Therefore
\((\operatorname{ad}_H)^NG=0\) implies \(G-c\in(H)\).  Since
\(\operatorname{ad}_H(H)=0\), repeated division gives

\[
\boxed{
\bigcup_{N\ge1}\ker(\operatorname{ad}_H^N)=\mathbb Q[H].}
\]

If a finite-dimensional polynomial Hamiltonian algebra contains \(H\),
every adjoint orbit in it must terminate: otherwise the strictly increasing
cusp weights exceed the algebra's finite weight ceiling.  Hence the algebra
is contained modulo constants in \(\mathbb Q[H]\), and is abelian.

This also subsumes the lowest-weight mixed-pair alternatives.  Directly,
if \(P^3+rQ^2\), \(r\ne0\), has any independent partner in
\(\langle P^3,PQ,Q^2\rangle\), a symplectic shear and spectral projection
recover \(X^3,Y^2\).  They generate

\[
\operatorname{ad}_{X^3Y}^{\,j}(X^4)
=c_jX^{4+2j},
\qquad c_{j+1}=(4+2j)c_j\ne0.
\]

## Complete centralizer-valued source obstruction

Write a finite target connection as

\[
K_s=\sum_{k=1}^M u_k(s)H_0^k.
\]

Powers \(H_0^k\), \(k\ge2\), vanish on the exceptional divisor.  Its source
connection therefore depends only on \(u_1(s)\).  The exact divisor
classification has one finite-Lie profile:

\[
u_1(s)=
\frac{6912(s^2-3s-8)}
{(s-6)^3(s-4)^2(s+4)^2}.
\]

It gives an affine divisor field.  If the cubic remains, its coefficient
ratio is

\[
\frac{c_2}{c_3}
=-\frac{5s^2}{(s-4)(s+4)},
\]

so it cannot lie in a shifted plane
\(\langle z\partial_z,z^3\partial_z\rangle\) with fixed center.  The
one-dimensional fixed-line equations have rank four.  These exhaust the
finite-dimensional polynomial line-field possibilities when a cubic is
present; if it is absent, the displayed profile is forced.

It remains to allow every higher power of \(H_0\) in the full source.  Use

\[
y=2v+3,\qquad g=1-\frac32v+t,
\]

and the volume-preserving normal layers

\[
D_f^{(m)}
=g^mf\partial_y-\frac{g^{m+1}f'}{m+3}\partial_g.
\]

The first two source coefficients \(A=[s]V_s\), \(B=[s^2]V_s\) have
immutable lower jets

\[
\operatorname{gr}_0 A
=D_{-(9y-10)/48}^{(0)},
\]

\[
\operatorname{gr}_1 B
=D_{-(y-1)(21y^3+21y^2+5y-31)/192}^{(1)}.
\]

Indeed \(H_0(F_0)\) has normal valuation three, so \(H_0^k\), \(k\ge2\),
first changes the tangential field in layer \(3k-3\ge3\).

Set \(z=y-10/9\).  The action of \(\operatorname{gr}_0 A\) on layer-one
monomials is diagonal:

\[
\operatorname{ad}_{\operatorname{gr}_0A}
D_{z^d}^{(1)}
=\frac{4-3d}{16}D_{z^d}^{(1)}.
\]

All five coefficients \(z^0,\ldots,z^4\) occur in
\(\operatorname{gr}_1B\).  Lagrange spectral projectors in
\(\operatorname{ad}_A\) therefore produce source Lie elements with leading
terms

\[
E_4=-\frac7{64}D_{z^4}^{(1)},
\qquad
E_3=-\frac{35}{72}D_{z^3}^{(1)}.
\]

Their bracket starts with

\[
[E_4,E_3]
=-\frac{1225}{18432}D_{z^6}^{(2)}.
\]

The graded bracket law gives the infinite ray

\[
\operatorname{gr}\!
\left(\operatorname{ad}_{E_4}^{\,j}[E_4,E_3]\right)
=c_jD_{z^{6+3j}}^{(2+j)},
\]

\[
\frac{c_{j+1}}{c_j}
=-\frac{7(j+6)(2j+1)}{64(j+5)}\ne0.
\]

Its source degrees are

\[
\boxed{8+4j}.
\]

Higher-centralizer additions cannot change the leading layer of this word.
Thus every finite-dimensional polynomial target Hamiltonian algebra
compatible with the seed has an infinite-dimensional source projection.
The argument is also stable under nonconstant formal reparameterization:
the substituted coefficient series is triangular at its first nonzero
parameter order, so it contains the same \(A,B\) coefficient span.

## Consequence for formal flows

A bounded-degree polynomial vector field can have a coefficientwise
polynomial formal exponential whose generic-time sum is rational rather
than polynomial.  The standard one-variable example is

\[
\exp(u\,w^2\partial_w)(w)=\frac{w}{1-uw}.
\]

The function-field degree argument alone misses such flows.  The
centralizer and source graded-ray arguments do not: they work directly on
the coefficient Lie algebra.  Therefore Vector C is closed for
finite-dimensional polynomial source/target algebras.

This does not close the tail statistic.  A coefficientwise-finite target
staircase may use an infinite-dimensional algebra whose degree grows with
parameter order.  Vectors A and B remain the live asymptotic attacks.

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

[`gauge_affine_divisor_p3_bracket_escape.py`](gauge_affine_divisor_p3_bracket_escape.py)
checks the regular \(P^3\)-only affine-divisor connection and its
\(18+8j\) source bracket ray.

[`gauge_low_weight_target_lie_classification.py`](gauge_low_weight_target_lie_classification.py)
checks the mixed-pair spectral projections and target monomial ray.

[`gauge_cusp_hamiltonian_finite_lie_classification.py`](gauge_cusp_hamiltonian_finite_lie_classification.py)
checks the cusp restriction, generalized kernel, and weight shift.

[`gauge_centralizer_divisor_profile.py`](gauge_centralizer_divisor_profile.py)
classifies the finite-Lie scalar divisor profiles from the exact carried
divisor identity.

[`gauge_centralizer_source_lie_escape.py`](gauge_centralizer_source_lie_escape.py)
checks the immutable source jets, the spectral projectors, and the
\(8+4j\) all-order graded ray.

The recurrence multiplier, its nonvanishing, and the strictly increasing
degree sequence are kernel-checked in
[`AxiomPackJacobianFiniteTargetLieEscapeArithmetic.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianFiniteTargetLieEscapeArithmetic.lean).

Its terminal certificate passed provider-free LeanMill ratification with:

- governed closure record SHA-256
  `04768fc7785290ab0d477c6271a1339f8cffb63c2eb614ede600318c8f4b9942`;
- kernel-parity SHA-256
  `24ec0f7819ffd30ed8ff51496aba31f0906b87ea935175ba8776c391a4f0cd1b`;
- zero provider calls, a matched negated-conclusion control, statement
  integrity, and the axiom allowlist all passing.

The governed closure is
[`AxiomPackJacobianFiniteTargetLieEscapeArithmetic.finite_target_lie_escape_arithmetic_terminal_certificate_8b1c791416a2.lean`](../../../ztare_proofs/closures/AxiomPackJacobianFiniteTargetLieEscapeArithmetic.finite_target_lie_escape_arithmetic_terminal_certificate_8b1c791416a2.lean).
