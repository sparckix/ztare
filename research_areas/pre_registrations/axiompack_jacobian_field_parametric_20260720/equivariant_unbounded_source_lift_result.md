# The formal source lift has unbounded spatial degree

**Status:** theorem proved; field-tower obstruction kernel-ratified; historical
priority provisional

## Theorem

Let `F_0` be the degree-three public seed and `F_s` the generic degree-four
member over `K=k((s))`.  Let

\[
F_s=F_0\circ\psi_s,
\qquad
\psi_s=x+\sum_{n\ge1}s^nY_n(x)
\]

be the unique source-only formal lift supplied by formal etaleness.  Then

\[
\sup_n\deg_xY_n=\infty.
\]

Thus every finite Artin parameter jet is polynomially removable, while no
fixed spatial-degree stage contains the compatible tower of removals.

## Proof

Assume `deg_x Y_n <= D` for every `n`.  Finitely many source monomials have
degree at most `D`, so the coefficient series assemble into a polynomial map

\[
\psi\in k[[s]][x_1,x_2,x_3]^3
\]

and hence a polynomial map `psi_K` over `K`.

The chain rule applied to `F_s=F_0 o psi_K`, together with the constant unit
Jacobians of `F_s` and `F_0`, gives `det D psi_K=1`.  This proves dominance and
generic finiteness; it does not assume polynomial invertibility.  Put

\[
m=[K(x):K(\psi_K)]\ge1.
\]

The composition identity yields

\[
K(F_s)\subseteq K(\psi_K)\subseteq K(x).
\]

Because the coordinates of `psi_K` are algebraically independent,
substitution identifies the relative extension

\[
K(\psi_K)/K(F_0(\psi_K))
\]

with the seed extension, of degree three.  The field-tower law now gives

\[
4=[K(x):K(F_s)]=3m,
\]

which is impossible.  Therefore the coefficient degrees are unbounded.

## Why this survives the formal-etale demotion

Formal etaleness explains existence and uniqueness of every finite-order
lift.  It places no uniform bound on spatial degree.  The theorem uses the
public global degree jump to prove that such a bound cannot exist.  It is the
failure of the two limits to commute:

\[
\varprojlim_N\varinjlim_D
\quad\text{contains the lift, while no fixed }D\text{ contains all of it.}
\]

The observed degrees `11,13,21,23,31` illustrate the escape but are not used
in the proof and remain gauge-dependent.

## Kernel and governance

[`AxiomPackJacobianUnboundedLift.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianUnboundedLift.lean)
formalizes the invariant tower step: a finite field extension of degree four
cannot factor through one of degree three.  The theorem uses Mathlib's
`Module.finrank_mul_finrank`; it does not assume a Keller map is invertible.

Provider-free LeanMill governance closed the field-tower theorem with:

- zero provider calls;
- closure-record SHA-256
  `824ffb395c67ff9d451e90355bed18fcf5791091dad7e2ab3e302aa85a88a89f`;
- parity-record SHA-256
  `a9f48454db3b6ab35cbb722bab55b49d4012ab745adc8c951c04768688aa871d`;
- governed closure
  [`AxiomPackJacobianUnboundedLift.degree_four_cannot_factor_through_degree_three_33656e44214c.lean`](../../../ztare_proofs/closures/AxiomPackJacobianUnboundedLift.degree_four_cannot_factor_through_degree_three_33656e44214c.lean).

The geometric bridge from a uniform degree bound to the displayed function
field tower is proved above and uses the already certified degree-three and
degree-four calculations.

## Priority boundary

Formal-etale lifting is standard, and the public sources own the weighted-lift
family, inverse equation, generic degrees, and branch at infinity.  The
Stacks Project supplies the nilpotent lifting theorem, while polynomial
automorphism ind-groups and failures of Lie data to determine global orbits
are classical context.  A targeted search found no source stating this exact
unbounded-degree corollary for the public family.  That absence is insufficient
for a priority claim; specialist review is still needed.

This theorem gives a qualitative obstruction, not a sharp rate, a
classification of nearby Keller maps, or another counterexample.
