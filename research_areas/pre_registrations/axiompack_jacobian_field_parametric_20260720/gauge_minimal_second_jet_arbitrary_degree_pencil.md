# Arbitrary-degree Hamiltonian boundary at the second source jet

**Status:** preregistered pencil for
`H-AXIOMPACK-JACOBIAN-GAUGE-MINIMUM-20260725-19`

## Orientation

The degree-eleven prediction in H18 is false. Exact coefficient solving found

\[
K(P,Q)=
-\frac{P^2Q}{168}
-\frac{179PQ}{1680}
+\frac{131Q^2}{672},
\]

whose Hamiltonian field, combined with a source pair in the full equivariant
lift ideals, lowers both second source components to total degree five.
Hamiltonian degree bounds three and four both give minimum source degree five;
source degrees at most four remain inconsistent by one exact rank.

This finite-degree result does not exclude a higher-degree Hamiltonian whose
high pullback terms cancel and lower the source degree further.

## Eigenquestion

Does the space of target Hamiltonian fields whose pullbacks can contribute
within component-degree bounds `(8,10)` stabilize after Hamiltonian degree
four?

For a source pair of degree at most four,

\[
\deg (DF_0Y)_P\le7,\qquad \deg (DF_0Y)_Q\le9,
\]

while the residual has component degrees `(8,10)`. Any helpful target field
must therefore have pullback component degrees at most `(8,10)` after all
cancellations.

## Filtration mechanism

The top seed forms are

\[
P^{\rm top}=-\frac34u^2,\qquad
Q^{\rm top}=-\frac14u^3,\qquad
u=v(2t-3v).
\]

The first subduction is

\[
\Delta=4P^3+27Q^2,
\qquad
\deg_{v,t}\Delta(P,Q)=10,
\qquad
\Delta^{\rm top}=\frac{27}{8}u^5.
\]

The next cancellation,

\[
\Delta^2+48P^5,
\]

has pullback degree eighteen. The working prediction is that this is the next
new filtered generator, so no Hamiltonian of higher target degree creates a
new pullback direction inside the `(8,10)` window.

## Discriminating test

1. Generate every target Hamiltonian monomial through total degrees
   `4,5,...,12`.
2. Expand its Hamiltonian field at `F0` before imposing bounds.
3. Constrain jointly all first-component coefficients above degree eight and
   second-component coefficients above degree ten.
4. Project the constrained target image to the bounded coefficient window and
   report its exact rank and basis at every degree bound.
5. Add every source monomial of degree at most four satisfying
   `U in (v,t)` and `V in (t,v^2)`. Test the exact residual for membership.
6. If the constrained target image stabilizes, extract a rational left-kernel
   functional that annihilates the stabilized source-plus-target image and is
   nonzero on `R2`.
7. Prove the stabilization symbolically from the displayed subduction chain;
   bounded rank stabilization alone is not an all-degree theorem.

## Success and kill conditions

Success requires both a stabilized exact finite image and an all-degree
filtration argument showing that the next target generator enters above the
component window. Together with the degree-five witness, this proves the
Hamiltonian gauge minimum is five at the second source jet.

The hypothesis is killed if any higher Hamiltonian degree adds a bounded
pullback direction that absorbs the residual with source degree at most four,
if the next subduction enters degree ten or below, or if the source component
bounds omit a Jacobian term.

The result remains a second-jet quotient-degree theorem. It does not imply an
all-order gauge-minimized growth rate.
