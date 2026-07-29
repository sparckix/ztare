# Full equivariant coordinate contact through the third jet

**Status:** exact characteristic-zero calculation with provider-free LeanMill
ratification. A later formal-etaleness audit explains its polynomial source
contact as a general unit-Jacobian mechanism. It still supersedes any reading
of the fixed-`gamma` second-jet obstruction as an obstruction for the full
equivariant source group.

## Result

The normalized cubic weighted-lift family is coordinate-trivial through its
third formal parameter jet under:

- the target Hamiltonian flow beginning with
  `X_H(P,Q)=(-Q/2,P^2/12)`; and
- polynomial divergence-free equivariant infinitesimal source fields.

At order two and order three, the composition-correct residuals have exact
polynomial source solutions `(U2,V2)` and `(U3,V3)`. They satisfy

\[
U_k\in(v,t),\qquad V_k\in(t,v^2),
\]

which are precisely the quotient lift ideals for equivariant polynomial
source vector fields. Their total degrees are respectively `(11,11)` and
`(13,13)`.

Consequently, the fixed-`gamma` obstruction at order two detects departure
from a proper subgroup, not departure from the full polynomial equivariant
coordinate orbit. The global generic-degree jump remains invisible through
the third formal jet.

## Governing source identity

An equivariant source vector field in `(x,y,z)` may be written

\[
\begin{aligned}
\delta x&=xA(v,t),\\
\delta y&=yB(v,t)+xzC(v,t),\\
\delta z&=zD(v,t)+y^2E(v,t).
\end{aligned}
\]

Its quotient field is

\[
U=v(A+B)+tC,\qquad V=t(2A+D)+v^2E.
\]

Conversely, for any coefficient field `U in (v,t)` and `V in (t,v^2)`, choose

\[
A=\frac12(U_v+V_t)
\]

and decompose the two ideal remainders to obtain `B,C,D,E`. Direct
differentiation shows that the resulting three-variable vector field has zero
divergence. Thus the two ideals are the Lie-algebra, coefficientwise
vector-field lift test; fixing `gamma` retains only a smaller shear family. Because the
first source correction begins at order two, nonlinear determinant terms do
not enter this order-three calculation. For an all-order source map,
volume preservation comes from the full-coordinate formal-etale lift and the
chain rule, not from checking these coefficient fields separately.

## Third-order composition

Write `A2=dF0(Y2)` for the second residual. With

\[
F_s=\exp(sX_H)\circ F_0\circ
\left(\mathrm{id}+\frac{s^2}{2}Y_2+rac{s^3}{6}Y_3\right)+O(s^4),
\]

the third residual is

\[
F_3-X_H^3(F_0)-3DX_H(F_0)A_2,
\]

where

\[
X_H^3(P,Q)=\left(PQ/24,Q^2/24-P^3/144\right).
\]

Solving the exact two-by-two seed Jacobian system gives the polynomial
`Y3`. Omitting the cross term would produce a different and invalid jet.

## Canonical coordinates

In `w=(1+v)gamma`, the seed pair is

\[
P=\gamma+2w-3w^2,\qquad Q=w\gamma+w^2-2w^3,
\]

with Jacobian `-gamma`. The order-two and order-three source fields have
compact Laurent presentations whose apparent `1/gamma` denominators cancel
after `w=gamma(1+v)`. Both obey

\[
\partial_w(\gamma\dot w)+
\partial_\gamma(\gamma\dot\gamma)=0,
\]

the divergence equation for the weighted area form
`gamma dw wedge dgamma`.

## Claim boundary

This file directly checks contact only through parameter order three. Standard
formal etaleness subsequently shows that every parameter jet is
source-trivial in the `s`-adically completed, unbounded-degree coordinate
group. It does not provide an actual polynomial conjugacy at nonzero
parameter, and such a conjugacy is excluded by the public generic-degree
difference. The displayed coefficients may be absent from the closest July
2026 sources, but their existence does not support a priority claim by itself.

## Replay and governance

The deterministic replay is
[`equivariant_full_gauge_third_jet.py`](equivariant_full_gauge_third_jet.py).
The Lean source is
[`AxiomPackJacobianFullGaugeThirdJet.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianFullGaugeThirdJet.lean).
The terminal theorem passed provider-free governance with zero model calls:

- target:
  `AxiomPackJacobianFullGaugeThirdJet.full_gauge_contact_through_third_jet_certificate`;
- closure certificate SHA-256:
  `84a211449102f5ec415959d1a61a31f0b8655a11dc6667e886e526d816b1f938`;
- kernel parity SHA-256:
  `be80009f077d64b9be34c710303ca19596799192940c121b8428b451b351c23a`;
- governed closure:
  [`AxiomPackJacobianFullGaugeThirdJet.full_gauge_contact_through_third_jet_certificate_00bb11d8543f.lean`](../../../ztare_proofs/closures/AxiomPackJacobianFullGaugeThirdJet.full_gauge_contact_through_third_jet_certificate_00bb11d8543f.lean).
