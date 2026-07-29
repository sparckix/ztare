# Recursive formal-contact depth for the cubic weighted lift

**Status:** pre-run pencil for
`H-AXIOMPACK-JACOBIAN-FORMAL-DEPTH-20260720-11`

## Eigenquestion

Does the public cubic weighted-lift line remain equivalent to its quadratic
seed at every finite parameter jet inside the `s`-adically completed group of
polynomial equivariant coordinate changes, even though no nonzero member can
be polynomially conjugate to the seed because its generic degree is four
rather than three?

The first target jet, second full-source jet, and third full-source jet are now
exact.  The next discriminating step is a recursive construction rather than
another hand-derived Faà di Bruno formula.

## Canonical recursion

Let

\[
V_H=-\frac Q2\partial_P+\frac{P^2}{12}\partial_Q
\]

and write `phi_s=exp(s V_H)`.  Remove the target motion from the exact family:

\[
G_s=\phi_{-s}(F_s).
\]

Seek a source series

\[
\psi_s=(v,t)+\sum_{n\ge2}s^n(a_n,b_n)
\]

such that

\[
F_0\circ\psi_s=G_s.
\]

At order `n`, all nonlinear terms involve only earlier coefficients.  The new
coefficient occurs linearly:

\[
dF_0(a_n,b_n)=
[s^n]G_s-[s^n]F_0\left((v,t)+\sum_{2\le j<n}s^j(a_j,b_j)\right).
\]

The seed quotient Jacobian is `-gamma^2`, so the unique rational solution is
obtained by a two-by-two inversion.  The scientific discriminator is whether
its apparent denominator cancels and the result lies in the lift ideals

\[
a_n\in(v,t),\qquad b_n\in(t,v^2).
\]

These conditions give coefficientwise quotient fields with divergence-free
infinitesimal lifts in the original three variables. They do not by themselves
assemble to a Jacobian-one coordinate series from order four onward. A full
lift must come from the three-coordinate adjugate recursion or from a proved
logarithm/lift/exponential integration lemma.

## Bounded prediction

Construct the recursion exactly through order six. The preregistered
prediction is:

1. every coefficient through order six is polynomial and satisfies both lift
   ideals;
2. orders two and three reproduce `Y2/2!` and `Y3/3!` from the independent
   jet calculation;
3. source total degree follows `2n+7`, giving `11,13,15,17,19` for orders
   `2,...,6`;
4. every truncated identity `F0 o psi = phi_-s o Fs mod s^(N+1)` vanishes
   coefficientwise over `Q[v,t]`.

A first denominator, ideal failure, or degree-law failure is retained as the
exceptional order.  Success through six is bounded evidence for all-order
formal triviality, not its proof.

## Mechanism sought after the bounded run

If the pattern survives, inspect the recursion in `w=(1+v)gamma`.  The desired
theorem is a divisibility induction: the order-`n` residual should carry the
exact powers of `gamma` needed to cancel `det dF0=-gamma^2`, while its source
degree rises with `n`.  Such an induction would explain both facts at once:

- every finite jet is removable in the `s`-adic completion;
- the resulting coordinate series has unbounded polynomial degree and does
  not specialize to a polynomial automorphism at nonzero `s`.

This is the formal/global separation suggested by the branch entering from
infinity.

## Kill conditions

- target-flow substitution is approximated numerically;
- ordinary series coefficients are confused with derivatives and factorials;
- the recursion omits nonlinear contributions of earlier source
  coefficients;
- rationality is accepted without denominator cancellation;
- lift ideals are tested only at sample points;
- coefficientwise divergence-free fields are treated as a volume-preserving
  map: for example `Id+s^2(x,-y,0)` has a divergence-free coefficient but
  determinant `1-s^4`;
- success through order six is called all-order equivalence;
- an infinite `s`-adic, unbounded-source-degree coordinate series is called a
  polynomial conjugacy for fixed nonzero `s`.

## Intended formal surface

If the bounded pattern survives, the kernel artifact should check one compact
new order beyond the existing third-jet theorem plus the recursive identity
schema.  A later all-order theorem should formalize the divisibility
induction, not paste orders four through six as large coefficient tables.
