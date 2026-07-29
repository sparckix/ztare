# Gauge-minimal second source jet

**Status:** preregistered pencil for
`H-AXIOMPACK-JACOBIAN-GAUGE-MINIMUM-20260725-18`

## Eigenquestion

After fixing the public first target-Hamiltonian jet, is the degree-eleven
second source correction already minimal under every admissible second-order
target gauge?

Write the seed quotient map as

\[
F_0=(P,Q):\mathbb A^2_{v,t}\longrightarrow\mathbb A^2_{P,Q}.
\]

After subtracting the forced square of
\(X_H=(-Q/2,P^2/12)\), let \(R_2\) be the exact second derivative residual.
A second-order target change contributes a vector field \(Z(P,Q)\), while a
source change contributes \(DF_0Y(v,t)\). The governing equation is

\[
R_2=Z(F_0)+DF_0Y.
\]

The test deliberately relaxes \(Z\) from a polynomial Hamiltonian field to an
arbitrary pair in the rational base field \(\mathbb Q(P,Q)^2\). Failure under
this larger target class is therefore a lower bound for every polynomial,
Hamiltonian, volume-preserving, or equivariant target subgroup.

## Canonical function-field coordinate

Use

\[
w=(1+v)\gamma,\qquad \gamma=1-\frac32v+t,
\]

for which

\[
P=\gamma+2w-3w^2,\qquad
Q=w\gamma+w^2-2w^3,
\]

and

\[
\Phi(w)=w^3-w^2+Pw-Q=0.
\]

Thus

\[
\gamma=P-2w+3w^2,\qquad
v=\frac{w}{\gamma}-1,\qquad
t=\gamma-1+\frac32v.
\]

For a polynomial source field \(Y\), substitute these expressions into
\(R_2-DF_0Y\), clear denominators, and reduce modulo \(\Phi\). Membership in
the base field requires the coefficients of \(w\) and \(w^2\) in both
components to vanish. Polynomial target membership is not required for the
lower-bound direction.

## Prediction

No polynomial pair \(Y=(U,V)\) of quotient total degree at most ten makes
\(R_2-DF_0Y\) base-field valued. The known degree-eleven correction does.
Therefore the gauge-minimized second source degree is exactly eleven, even
after allowing arbitrary rational target vector fields.

## Attack vectors and counterattacks

1. **Exact linear solve over all source monomials.** For each
   \(D=0,\ldots,10\), include every \(v^it^j\) with \(i+j\le D\) independently
   in both components. Counterattack: a missing monomial or a symmetry
   restriction invalidates the lower bound.
2. **Cubic remainder invariant.** Reduce only after substituting the exact
   inverse coordinate and clearing a common denominator. Counterattack:
   reduction of separate summands with inconsistent denominators can create a
   false obstruction.
3. **Relaxed target class.** Require only base-field membership.
   Counterattack: this cannot prove the target correction is polynomial at a
   positive solution; it is used only to exclude lower-degree solutions.
4. **Composition convention.** Construct \(R_2\) from the exact family jets
   after subtracting \(X_H^2(F_0)\). Counterattack: using the raw second
   derivative tests the wrong gauge class.
5. **Degree-eleven witness.** Replay the existing \(Y_2\), its polynomiality,
   and the exact equation. Counterattack: an exclusion through degree ten
   without a degree-eleven witness proves only a lower bound.

## Kill conditions

The prediction is killed by any exact solution of degree at most ten, by a
failure of the displayed cubic/inverse identities, by a nonzero residual for
the known degree-eleven source field, or by discovering an omitted
second-order composition term that is not base-field valued.

Field membership must not be promoted to polynomial target membership.
Second-jet minimality must not be promoted to the all-order gauge-minimized
rate.

## Intended formal surface

If the finite exact solve excludes degrees at most ten, the kernel artifact
should certify a compressed obstruction functional: a linear functional on
the cubic-remainder coefficients that vanishes on
\(DF_0Y+\mathbb Q(P,Q)^2\) for every source monomial through degree ten and is
nonzero on \(R_2\). A separate exact witness certifies the degree-eleven upper
bound. Lean should check the finite certificate, not reproduce symbolic
elimination.
