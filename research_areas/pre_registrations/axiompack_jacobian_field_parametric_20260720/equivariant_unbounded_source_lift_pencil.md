# Unbounded spatial degree of the formal source lift

**Status:** pre-proof pencil for
`H-AXIOMPACK-JACOBIAN-UNBOUNDED-LIFT-20260720-13`

## Eigenquestion

Formal etaleness makes every polynomial deformation through the public seed
source-trivial over each Artin parameter quotient.  What prevents these
compatible lifts from living in one fixed degree stage of the polynomial-map
ind-scheme?

## Candidate theorem

Let `k` be characteristic zero and `K=k((s))`.  Let `F_0` be the public seed
with generic degree three, and let `F_s` denote the generic member of the
public family over `K`, with generic degree four.  Formal etaleness gives a
unique source series

\[
\psi_s=x+\sum_{n\ge1}s^nY_n(x),
\qquad F_s=F_0\circ\psi_s.
\]

Then the set of spatial degrees `deg_x Y_n` is unbounded.

## Proof skeleton

Assume `deg_x Y_n <= D` for every `n`.  Only finitely many source monomials
have degree at most `D`, so their coefficient series assemble into

\[
\psi\in k[[s]][x_1,x_2,x_3]^3.
\]

After extending scalars, obtain a polynomial map `psi_K` over `K`.  The chain
rule and the unit Jacobians of `F_s` and `F_0` give `det D psi_K=1`, hence
`psi_K` is dominant and has a positive finite generic degree `m`.

The composition identity gives a tower

\[
K(F_s)\subseteq K(\psi_K)\subseteq K(x_1,x_2,x_3).
\]

Substitution by the algebraically independent coordinates of `psi_K`
identifies

\[
[K(\psi_K):K(F_0(\psi_K))]
= [K(x):K(F_0(x))]=3.
\]

The other tower degree is

\[
[K(x):K(\psi_K)]=m\ge1.
\]

Therefore

\[
4=[K(x):K(F_s)]=3m,
\]

which is impossible.

## Why no inverse is assumed

The recent dimension-three counterexample forbids using unit Jacobian as a
polynomial-invertibility criterion.  The proof needs only dominance and the
finite function-field degree `m`.  Indeed, noninvertibility would make
`m>1`; it cannot repair divisibility by three.

## Attack vectors and counterattacks

1. **Formal-to-polynomial passage.** Counterattack: an infinite set of
   monomials survives despite a uniform total-degree bound.  In finitely many
   variables this cannot occur.
2. **Coefficient field.** Counterattack: the normalized rational functions of
   `s` have poles at the origin.  Their denominators are units at `s=0`; the
   exceptional parameters are `4,6`, not zero.
3. **Dominance.** Counterattack: `psi_K` could have zero generic degree.  Its
   Jacobian determinant is one by the chain rule.
4. **Tower identification.** Counterattack: substitution changes the seed's
   generic degree.  Algebraic independence of the coordinates of `psi_K`
   makes substitution an isomorphism of rational function fields onto
   `K(psi_K)`.
5. **Gauge dependence.** Counterattack: higher target corrections change the
   source coefficients.  The theorem fixes the canonical source-only lift;
   broader right-left minimization is a separate question.

## Exact kill conditions

- generic degree four fails over `K=k((s))`;
- the source-only formal identity does not extend to an equality in `K[x]`
  under the bounded-degree assumption;
- `psi_K` is not dominant or generically finite;
- the intermediate extension has degree different from the seed degree;
- or the degree tower is infinite.

## Intended formal surface

Formalize the field-tower arithmetic at its invariant level: finite
extensions of degrees three and `m` cannot compose to degree four.  Bind that
kernel theorem to the already checked generic degrees and the explicit
formal-etale construction in the result artifact.  Do not encode the
order-six coefficient tables again.
