# Second-order escape from the polynomial Hamiltonian coordinate orbit

**Status:** exact characteristic-zero result with provider-free LeanMill
ratification. Historical priority is provisional. The theorem concerns one
public weighted-lift family and one explicitly declared coordinate subgroup.

**Adversarial addendum:** allowing the full polynomial equivariant source
group removes this second-order obstruction. The residual is the pushforward
of a polynomial divergence-free source vector field satisfying the exact lift
ideals. The fixed-`gamma` result remains correct but is not a full-gauge escape
theorem; see
[`equivariant_full_gauge_third_jet_result.md`](equivariant_full_gauge_third_jet_result.md).

## Result

Let

\[
\gamma=1-\frac32v+t,\qquad P_s=\gamma\beta_s,\qquad
Q_s=\gamma^2\alpha_s
\]

be the normalized cubic weighted-lift line through the public degree-three
seed. Exact differentiation gives

\[
(\dot P,\dot Q)=\left(-\frac12Q_0,\frac1{12}P_0^2\right)
=X_H(P_0,Q_0),
\qquad H=-\frac14Q^2-\frac1{36}P^3.
\]

Thus the first jet is a polynomial target-Hamiltonian coordinate motion. Its
forced Lie-square term is

\[
X_H^2(P,Q)=\left(-\frac1{24}P^2,-\frac1{12}PQ\right).
\]

After subtracting that term, the second derivative does **not** lie in the
sum of

1. arbitrary polynomial target-Hamiltonian fields `X_K(P0,Q0)`, and
2. polynomial volume-preserving source shears
   `f(gamma) (partial_v + 3/2 partial_t)(P0,Q0)` that fix `gamma`.

Hence this family has first-order contact with the declared fixed-`gamma`
polynomial coordinate orbit and leaves that subgroup at order two.

## Canonical inverse coordinate

Put `w=(1+v)gamma`. At the seed,

\[
P=\gamma-3w^2+2w,\qquad
Q=w\gamma+w^2-2w^3,
\]

so the inverse relation is

\[
\Phi(w)=w^3-w^2+Pw-Q=0.
\]

Target Hamiltonian corrections belong to `Q[P,Q]^2`; after reduction modulo
`Phi`, they have no `w` or `w^2` residue. The second-jet residual reduces to

\[
\begin{aligned}
24\mathcal R_P\equiv{}&
(-21P+10)w^2+(29P+27Q-10)w+2P-35Q,\\
24\mathcal R_Q\equiv{}&
(5P+18Q)w^2+(16P^2-5P-21Q)w\\
&+2P^2-16PQ+3Q.
\end{aligned}
\]

For a constant source shear, the first component reduces to

\[
D_\gamma P\equiv 2(6Pw+P-9Q-2w),
\]

which has no `w^2` coefficient. Therefore the residual coefficient

\[
\frac{10-21P}{24}
\]

cannot be cancelled.

## Why higher-degree source shears cannot help

Give `(w,P,Q)` weights `(1,2,3)`. The associated-graded inverse relation is

\[
w^3+Pw-Q=0,
\]

and the leading part of `gamma` is `P+3w^2`. Specialize `P=0`; then the top
parts of the two components contributed by the leading term `gamma^n` of a
source shear are nonzero multiples of

\[
w^{2n+3},\qquad w^{2n+4}
\]

modulo `w^3-Q`. These consecutive exponents cannot both be divisible by
three. At least one component therefore retains a `w` or `w^2` residue. For
`n>=1` this occurs above the residual's component weights `(4,5)`, so no lower
source term or target-base term can cancel it. Descending on the degree forces
every positive-degree coefficient of `f` to vanish, reducing to the constant
obstruction above.

This replaces the initial weight-bounded matrix evidence with an all-degree
argument for the declared source-shear family.

## Claim boundary and priority

The public [weighted-lift
notes](https://github.com/algal/jacobianfun/blob/main/RESEARCH.md) already give
the inverse equation, generic-degree jump, and branch-at-infinity mechanism.
The base [counterexample
manuscript](https://www.ulam.ai/research/jacobian.pdf) also gives broad
polynomial deformation families. Targeted searches of those sources and
[Graded Keller maps](https://arxiv.org/abs/2607.20210) found no infinitesimal
Hamiltonian, support-filtration, or second-jet orbit calculation. This exact
filtered statement is therefore a frontier candidate relative to the closest
public record checked, not a certified priority claim.

The source group here is complete among volume-preserving infinitesimal
shears that fix `gamma`, but it is not the full group of equivariant polynomial
source automorphisms. The result does not classify all hyperbolic equivariant
Keller maps and does not add another disproof of the Jacobian conjecture.

## Replay and kernel certificate

The exact replay is
[`equivariant_hamiltonian_jet_escape.py`](equivariant_hamiltonian_jet_escape.py).
The compiled source is
[`AxiomPackJacobianHamiltonianJet.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianHamiltonianJet.lean).
The carried theorem passed provider-free governance with zero model calls:

- target:
  `AxiomPackJacobianHamiltonianJet.second_jet_escape_certificate`;
- closure certificate SHA-256:
  `6e6ef67e7dbd7945f4206e99c69a14fc3b97187b4df9fc08084bb224b64a8b6f`;
- kernel parity SHA-256:
  `4827e11ae216df82b51b5ad79179b4659cc220dc3b8dd6ca50d159bec66b9c3c`;
- governed closure:
  [`AxiomPackJacobianHamiltonianJet.second_jet_escape_certificate_85afcc751313.lean`](../../../ztare_proofs/closures/AxiomPackJacobianHamiltonianJet.second_jet_escape_certificate_85afcc751313.lean).
