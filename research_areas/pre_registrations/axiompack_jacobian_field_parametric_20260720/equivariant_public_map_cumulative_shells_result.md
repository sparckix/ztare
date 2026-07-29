# Cumulative-shell and generic-fiber analysis of the public Keller map

**Status:** exact characteristic-zero calculation around the public
dimension-three counterexample. The generic-fiber certificate is compiled in
Lean and has passed provider-free LeanMill governance. The degree jump and
branch-at-infinity mechanism are public prior art; the complete support
filtration and exact Hamiltonian-tangent calculation were not found in the
closest public sources and remain a provisional, smaller contribution.

## Result in one sentence

The known cubic weighted-lift line requires five complete equivariant support
shells for its first-order cancellations and is tangent at the seed to a
Hamiltonian formal-coordinate direction. Its generic inverse-fiber degree
jumps from three at the public seed to four at every nonzero rational
parameter, excluding one bounded-degree algebraic coordinate family while
remaining compatible with an unbounded-degree `s`-adic formal lift.

## Exact support filtration

After fixing

\[
\gamma=1-\frac32v+t
\]

and the same two scaling coordinates used in the earlier local charts, the
normalized cubic family has nonzero derivative entries in every cumulative
shell from `+1` through `+5`. Its projection fails the linearized Keller
equations until all five shells are present. The numbers of nonzero projected
residual coefficients are

\[
32,\ 33,\ 33,\ 32,\ 26,\ 0
\]

for shells `+0,...,+5`, respectively. The corresponding normalized tangent
dimensions are

\[
1,\ 2,\ 3,\ 4,\ 5,\ 7.
\]

Thus the family's cancellation radius in this complete support filtration is
exactly five. Lower-shell calculations cannot see its tangent by truncating
the formula and cannot reproduce it by selecting only the monomials visible
in the family.

The quadratic obstruction cones do not support a stronger claim that all
smaller charts are isolated. Shells `+2`, `+3`, and `+4` contain nonzero
projective quadratic survivors. In particular, their reduced obstruction
bases begin as

\[
\begin{aligned}
+2:\quad &
(36r_0+21r_1-8r_2)(36r_0+21r_1+8r_2),\\
&r_2(36r_0+21r_1-8r_2);\\[2mm]
+3:\quad &
1296r_0^2+960r_0r_1+1512r_0r_2-2496r_0r_3
+560r_1r_2+441r_2^2-1456r_2r_3+64r_3^2,\\
&(r_1-2r_3)(r_1+2r_3),\quad r_3(r_1-2r_3);\\[2mm]
+4:\quad &
12r_0r_3+2r_1^2-8r_1r_4+7r_2r_3+8r_4^2,\\
&r_1r_3,\quad r_3^2,\quad r_3r_4.
\end{aligned}
\]

These are candidates for higher-order obstruction or integration, not
certified families.

## Expansion-before-constraint gauge quotient

A monomial-by-monomial gauge check incorrectly returns rank zero because an
individual coordinate generator leaves the bounded chart. The corrected
calculation expands the bounded source-shear and target-Hamiltonian Lie
algebras into the full coefficient universe, constrains all forbidden and
frozen rows simultaneously, and only then projects into each chart.

For Hamiltonian weight bounds `W=3,4,5,6`, the normalized gauge ranks
stabilize as follows:

\[
\begin{array}{c|c|c}
\text{shell} & \text{stable gauge rank} & \text{tangent quotient dimension}\\
\hline
0,1,2,3 & 0 & 1,2,3,4\\
4 & 1 & 4\\
5 & 3 & 4
\end{array}
\]

At shell `+5`, the cubic-family tangent enters the stabilized gauge span at
weight four. Its exact nonzero generator coordinates are

\[
H(P,Q)=-\frac14Q^2-\frac1{36}P^3,
\qquad
X_H=(\partial_QH,-\partial_PH)=(-Q/2,P^2/12).
\]

Consequently the first derivative of the known family is a Hamiltonian
formal-coordinate direction. This does not imply global polynomial
conjugacy: the Hamiltonian flow need not be a polynomial automorphism, and a
first-order orbit calculation cannot decide higher-order equivalence.

## Coordinate-invariant separation by generic fiber degree

Before the invertible normalization, let

\[
\begin{aligned}
p_s(w)&=\left(2+\frac{s}{2}\right)w
       -\left(3+\frac{3s}{2}\right)w^2+s w^3,\\
R_s(w)&=\left(1+\frac{s}{4}\right)w^2
       -\left(1+\frac{s}{2}\right)w^3+\frac{s}{4}w^4.
\end{aligned}
\]

The inverse branches obey the single equation

\[
f_s(w;P,Q)=R_s(w)-wP+Q=0.
\]

The source coordinates are recovered rationally from a root:

\[
\gamma=P-p_s(w),\qquad
v=\frac{w}{\gamma}-1,\qquad
t=\gamma-1-a_sv.
\]

For each fixed rational parameter for which the map is defined, `f_s` is
irreducible over `Q(P,Q)`. Indeed, it is primitive and degree one in the
independent variable `Q` with coefficient one. Any factorization in
`Q[P,Q,w]` would have a `Q`-independent factor dividing that coefficient, so
that factor is a unit; Gauss's lemma then gives irreducibility over the
fraction field.

The leading coefficient in `w` is `s/4` for `s != 0`, while at `s=0` the
polynomial becomes cubic with leading coefficient `-1`. Since `w` generates
the source function field by the displayed recovery formulas,

\[
[\mathbb Q(v,t):\mathbb Q(P,Q)]=
\begin{cases}
3,&s=0,\\
4,&s\ne0.
\end{cases}
\]

The fixed-gamma normalization is invertible away from its exceptional
parameters `s=4,6`, so it preserves this degree wherever that chart applies.
Geometrically, the family touches a Hamiltonian coordinate orbit at first
order while a fourth generic inverse branch arrives from infinity away from
the seed.

## Priority and claim boundary

The inverse equation, the formula `generic degree = deg(p)+1`, and the escape
of a repeated inverse branch through `gamma=0` are already stated in Alexis
Gallagher's [weighted-lift
notes](https://github.com/algal/jacobianfun/blob/main/RESEARCH.md), and the base
[counterexample manuscript](https://www.ulam.ai/research/jacobian.pdf)
constructs polynomial families of arbitrary generic degree. The Lean theorem
below is therefore a formal recovery certificate for that public mechanism,
not a new mathematical result.

The remaining candidate contribution is narrower: the family needs five
complete equivariant support shells before its derivative satisfies the
linearized Keller equations, and that derivative is exactly the polynomial
Hamiltonian direction generated by
`H = -Q^2/4 - P^3/36`. No tangent-space, obstruction, or support-filtration
statement of this form was found in the closest sources, including [Graded
Keller maps](https://arxiv.org/abs/2607.20210). Priority is still provisional.

This analysis does not address the still-open dimension-two conjecture,
classify the hyperbolic equivariant family, or prove arbitrary-degree local
rigidity. Formal etaleness rules out a first escape jet in the unrestricted
coefficientwise-polynomial `s`-adic source group. The next discriminator is a
lower bound on the minimum coordinate degree needed at truncation order `N`,
or an equivalent proof that the formal lift cannot remain in any fixed degree
stage of the polynomial automorphism ind-group.

The deterministic replay is
[`equivariant_public_map_cumulative_shells.py`](equivariant_public_map_cumulative_shells.py).
It uses exact rational linear algebra, symbolic coefficient extraction, and
symbolic source recovery; no floating-point rank decision enters the stated
results. The kernel certificate is
[`AxiomPackJacobianFiberDegree.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianFiberDegree.lean),
and its governed closure is
[`AxiomPackJacobianFiberDegree.inverse_fiber_degree_certificate_73e6da5d5ad9.lean`](../../../ztare_proofs/closures/AxiomPackJacobianFiberDegree.inverse_fiber_degree_certificate_73e6da5d5ad9.lean).
