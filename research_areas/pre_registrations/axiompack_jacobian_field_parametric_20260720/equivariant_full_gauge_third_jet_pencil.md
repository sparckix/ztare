# Full equivariant gauge: third-jet discriminator

**Status:** pre-run pencil for
`H-AXIOMPACK-JACOBIAN-FULL-GAUGE-20260720-10`

## Post-hoc orientation from the second jet

The fixed-`gamma` source-shear obstruction is not an obstruction for the full
equivariant source group.  A polynomial equivariant infinitesimal source
coordinate change descends to a quotient vector field

\[
Y=U(v,t)\partial_v+V(v,t)\partial_t
\]

with the lift ideals

\[
U\in(v,t),\qquad V\in(t,v^2).
\]

Every such pair has a divergence-free infinitesimal lift to `(x,y,z)`: taking

\[
A=\frac12(\partial_vU+\partial_tV)
\]

and decomposing `U-vA` in `(v,t)` and `V-2tA` in `(t,v^2)` supplies the
remaining equivariant vector-field components.  This is the governing source
identity; restricting to `U=f(gamma), V=3f(gamma)/2` tests only the
fixed-`gamma` subgroup.

Solving

\[
d(P_0,Q_0)Y_2=\mathcal R_2
\]

for the previously computed second residual gives a polynomial `(U2,V2)` in
the lift ideals.  In `(w,gamma)` coordinates the same field is compact:

\[
\begin{aligned}
\dot w={}&\frac{1}{24\gamma}
\left(2\gamma^2-4\gamma w^3-6\gamma w^2+4\gamma w
+3w^5+15w^4-21w^3+7w^2\right),\\
\dot\gamma={}&\frac{1}{24\gamma}
\left(6\gamma^2w^2+6\gamma^2w-2\gamma^2
-15\gamma w^4-60\gamma w^3+63\gamma w^2-14\gamma w\\
&\hspace{31mm}+18w^6+84w^5-156w^4+84w^3-14w^2\right).
\end{aligned}
\]

The apparent denominators cancel after `w=gamma(1+v)`, and

\[
\partial_w(\gamma\dot w)+
\partial_\gamma(\gamma\dot\gamma)=0.
\]

Thus the Lie-algebra source correction carries contact through order two. This was an
adversarial post-hoc audit of H09, not a preregistered H09 outcome.

## Third-jet eigenquestion

Is the generic-degree jump invisible to the third formal parameter jet under
the full polynomial equivariant source group and polynomial target
Hamiltonians?

Let

\[
X_H(P,Q)=(-Q/2,P^2/12)=:V_H(P,Q)
\]

and let `A2=dF0(Y2)` be the second residual.  Use the gauge choice with fixed
target flow `exp(s V_H)` and source path

\[
\psi_s=\operatorname{id}+\frac{s^2}{2}Y_2+rac{s^3}{6}Y_3+O(s^4).
\]

Expanding

\[
F_s=\exp(sV_H)\circ F_0\circ\psi_s+O(s^4)
\]

shows that the forced third derivative is

\[
V_H^3(F_0)+3\,DV_H(F_0)A_2+dF_0(Y_3),
\]

where

\[
V_H^3(P,Q)=\left(PQ/24,Q^2/24-P^3/144\right)
\]

and

\[
3DV_H(A_2)=\left(-3A_{2,Q}/2,PA_{2,P}/2\right).
\]

## Discriminating test

1. Differentiate the exact normalized family three times independently.
2. Recheck `Y2` by exact substitution, its lift ideals, and its weighted
   divergence identity.
3. Form the third residual using the displayed composition formula; do not
   use the raw third derivative.
4. Solve `dF0(Y3)=R3` exactly.  If `(U3,V3)` is polynomial and lies in
   `(v,t) x (t,v^2)`, third-order contact is established.
5. If direct source solving has denominators or violates lift ideals, allow an
   arbitrary polynomial target Hamiltonian correction before declaring an
   obstruction.
6. Preserve the smallest canonical-coordinate expression and formalize only
   the terminal identities.

## Prediction and kill conditions

The working prediction is that third-order contact also survives, with source
degree increasing.  Confirmation would support a nonperturbative mechanism:
every finite formal jet may look coordinate-trivial even though the generic
fiber degree changes for every nonzero parameter.  A denominator or lift-ideal
failure surviving target-Hamiltonian correction falsifies that prediction and
locates the first full-gauge escape jet.

The test is killed if it omits the `3 DV_H A2` term, treats a rational quotient
field vector field as a polynomial source automorphism, ignores the two lift
ideals, treats coefficientwise divergence as a group-level Jacobian
certificate beyond order three, or promotes finite-order contact to an actual
polynomial conjugacy at nonzero parameter.

## Intended formal surface

The kernel artifact should check the compact `(w,gamma)` identities, exact
third-jet composition equation, lift-ideal witnesses in `(v,t)`, and weighted
divergence.  It should not encode the symbolic differentiator.
