# Same-degree equivariant rigidity of the public Jacobian map

**Status:** exact characteristic-zero calculation with provider-free LeanMill
ratification of the finite tangent and obstruction certificates.  The exact
local statement was absent from the closest public analyses checked so far;
priority remains unconfirmed pending specialist review.

## Result

After the coordinate rescaling

\[
z_{\rm public}=-2z,qquad
(F_1,F_2,F_3)\mapsto(F_1,F_2/2,F_3/2),
\]

the public three-point map is represented by

\[
\gamma=1-\frac32v+t,qquad
P=\beta\gamma,qquad Q=\alpha\gamma^2,qquad
\operatorname{Jac}_{v,t}(P,Q)=-\gamma^2,
\]

where `v=xy` and `t=x^2z`.  This is the quadratic weighted lift
`p(w)=2w-3w^2`.

Do not retain only the monomials produced by that mechanism.  Enlarge to all
equivariant monomials for which `beta/x` is polynomial of degree at most six
and `alpha/x^2` is polynomial of degree at most seven.  Equivalently,

\[
\begin{aligned}
S_\beta&=\{(i,j):i+2j\ge1,\ 2i+3j-1\le6\},\\
S_\alpha&=\{(i,j):i+2j\ge2,\ 2i+3j-2\le7\}.
\end{aligned}
\]

This adds the four coefficients

\[
b_{0,2},\qquad c_{1,2},\qquad c_{0,3},\qquad c_{0,2}
\]

that are absent from the weighted-lift formula.  Normalize
`a=-3/2` and `b_(1,0)=1/2`; these coordinates are transverse to source
`v`-scaling and determinant-one target scaling, with determinant `3/4`.

The expanded Keller condition gives 39 coefficient equations in 16 remaining
variables.  At the public map their exact rational linearization has rank 15.
Its single tangent direction has zero entries in all four newly admitted
coordinates.  Thus expanding to the complete same-degree chart creates no
new first-order direction.

The remaining tangent is not integrable.  An explicit eight-equation left
kernel functional annihilates the linearization but evaluates the required
second-order correction to

\[
\frac1{27}\ne0.
\]

Hence there is no nonconstant formal arc through the normalized public map in
the full same-degree equivariant coefficient chart.  In this precise sense,
the counterexample is locally rigid beyond its generating ansatz.

## Why this matters

This separates mechanism from accident.  The cancellations are controlled
by the larger equivariant quotient system `(P,Q,gamma)`, and the exceptional
set is the coefficient scheme transverse to the known scalings.  Searching
nearby coefficients at the same degree cannot produce a new family; the next
search must change support or change the equivariant chart.

## Claim boundary

The result is local, equivariant, and degree-bounded.  It does not classify
all Keller maps, exclude higher-degree deformations, or settle any global
Jacobian question.  Novelty remains provisional until the public construction
notes and adjacent deformation literature are checked for this exact local
statement.

The exact certificate is replayed by
[`equivariant_public_map_degree_rigidity.py`](equivariant_public_map_degree_rigidity.py).
It verifies the support completion, rank, tangent vector, left-kernel
functional, and nonzero quadratic obstruction over `QQ`.

The replay now emits the full coordinate order, base point, 15 selected raw
coefficient labels, primitive linear rows, eight obstruction labels, required
second-order right-hand sides, and left-kernel functional.  This binds the
finite certificate to the 39 coefficients derived from the displayed Keller
defect without relying on floating-point reconstruction.

## Kernel ratification

[`AxiomPackJacobianEquivariantRigidity.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianEquivariantRigidity.lean)
checks two finite consequences over `ℚ`:

1. every solution of the selected rank-15 linear system is the displayed
   one-parameter tangent;
2. the eight order-two equations imply `s^2 = 0`, excluding a lift of any
   nonzero tangent.

Both targets closed through LeanMill's carried-artifact route with zero
provider calls:

- `tangent_classification`: certificate record
  `49a80b6684f01cd73fb887ef6fd564b7fd14968c5258b8f24e4e654504822034`;
- `no_second_order_lift`: certificate record
  `edf61d08624b7619461c978bd5d3f6d3e612fade042a36cdf34f983a5784c626`.

The kernel surface intentionally checks the finite rational certificates,
while the exact sparse expansion from `(β, α, γ)` to those rows remains in the
deterministic replay.  Reimplementing general symbolic coefficient expansion
inside the proof kernel would enlarge the trusted presentation without adding
a new mathematical discriminator.
