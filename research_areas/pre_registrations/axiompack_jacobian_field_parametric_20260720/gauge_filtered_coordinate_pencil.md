# Canonical filtered target coordinate at the second source jet

**Status:** preregistered pencil for
`H-AXIOMPACK-JACOBIAN-GAUGE-MINIMUM-20260725-20`

## Orientation

H19's finite rank conclusion survived through Hamiltonian degree twelve, but
its proposed subduction chain did not. The bounded target image has exact rank
seven at every tested bound from three through twelve. However, the target
polynomials

\[
\Theta=4P^3-18PQ+27Q^2
\]

and

\[
C=\Theta-P^2+4Q
\]

have pullback degrees eight and six respectively. Thus
\(\Delta^2+48P^5\) is not the next relevant cancellation after
\(\Delta=4P^3+27Q^2\).

The corrected route is a target-coordinate normal form rather than a finite
degree extrapolation.

## Eigenquestion

Does the coordinate \(C\) diagonalize the pullback filtration strongly enough
to classify every polynomial Hamiltonian field inside the component-degree
window `(8,10)`?

## Candidate theorem

Set

\[
\gamma=1-\frac32v+t,\qquad w=(1+v)\gamma,
\]

so that

\[
P=\gamma+2w-3w^2,\qquad
Q=w\gamma+w^2-2w^3.
\]

Give \(\gamma,w\) weights \(1,2\). Substitution into \(v,t\) preserves this
weighted degree because the leading forms are
\(\bar\gamma=t-\frac32v\) and
\(\bar w=v(t-\frac32v)\), and the resulting monomials are independent after
the linear change from \(t\) to \(\bar\gamma\).

Define

\[
C=4P^3-18PQ+27Q^2-P^2+4Q.
\]

Direct expansion predicts

\[
C(F_0)=\gamma^2(3P+\gamma-1),
\]

with leading monomial \(-9\gamma^2w^2\) and filtered degree six. Moreover,

\[
27Q^2=C+(18P-4)Q-4P^3+P^2.
\]

Consequently every polynomial in \(P,Q\) has a unique normal form

\[
A(P,C)+Q\,B(P,C).
\]

The leading monomials of
\(P^aC^c\) and \(QP^aC^c\) are respectively proportional to

\[
\gamma^{2c}w^{2a+2c},
\qquad
\gamma^{2c}w^{2a+2c+3}.
\]

They are pairwise distinct, and their filtered degrees are

\[
4a+6c,\qquad 6+4a+6c.
\]

It follows that the scalar filtered pieces are exactly

\[
\mathcal F_8
=
\langle 1,P,P^2,Q,C\rangle
\]

and

\[
\mathcal F_{10}
=
\langle 1,P,P^2,Q,PQ,C,PC\rangle.
\]

If a polynomial Hamiltonian \(K(P,Q)\) has
\(K_Q(F_0)\in\mathcal F_8\) and
\(K_P(F_0)\in\mathcal F_{10}\), integrate the displayed basis for \(K_Q\)
with respect to \(Q\), then compare \(K_P\) with the second basis. The
\(C\)-coefficient is forced to zero by the unmatched \(P^2Q\) and \(PQ^2\)
terms. The remaining integration constant has degree at most three.
Therefore, modulo constants,

\[
K\in
\langle P,Q,P^2,PQ,Q^2,P^3,P^2Q\rangle.
\]

This gives an all-degree explanation for the observed rank-seven target
image.

## Discriminating tests

1. Replay the identities defining \(C\), its pullback, and the quadratic
   normal-form relation over exact rationals.
2. Verify pairwise distinctness and degree formulas for both normal-form
   monomial families symbolically.
3. Derive the two filtered bases from the inequalities above and compare them
   with direct coefficient ranks through target degree twelve.
4. Build the exact coefficient map from all source lifts of degree at most
   four and the seven Hamiltonian basis fields. Extract a primitive rational
   dual functional that annihilates every column and evaluates nontrivially on
   the second-jet residual.
5. Replay the degree-five Hamiltonian/source witness from H18.
6. Encode the normal-form identity, filtered-basis consequence, dual
   obstruction, and upper witness in Lean. Submit the carried statement and
   artifact to the existing provider-free LeanMill ratification path.

## Kill conditions

The hypothesis is killed if the \(C\) pullback identity or weighted-degree
preservation fails; if the quadratic relation does not give a unique normal
form; if two declared normal monomials share a leading monomial; if a
Hamiltonian outside the seven-dimensional span remains inside the `(8,10)`
window; if the dual functional fails on any source or target column; or if the
degree-five witness fails the exact second-jet equation.

The finite rank data alone cannot establish the all-degree statement.

## Recurrence check and intended formal surface

The fixed-gauge degree law and the earlier degree-three/full-gauge jet files do
not contain the \(C\)-coordinate or an arbitrary-degree target normal form.
The intended formal surface is a new second-jet quotient theorem:

- a polynomial identity for \(C(F_0)\);
- a quadratic reduction identity for \(Q^2\);
- a normal-form filtration lemma;
- a finite dual obstruction against source degree at most four;
- the explicit degree-five upper witness.

It concerns this normalized family, the declared source-lift ideals, and
polynomial Hamiltonian target gauges. It does not establish an all-order
gauge-minimized rate, a new counterexample to the Jacobian conjecture, or
historical priority.
