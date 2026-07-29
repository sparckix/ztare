# Associated-graded source-flow pencil

Hypothesis: `H-AXIOMPACK-JACOBIAN-FILTERED-FLOW-20260720-14`

## Eigenquestion

In the fixed target-Hamiltonian gauge, does one integrable top vector field
control the spatial degree of every coefficient of the unique formal source
lift?

## Orientation data

Set

\[
L=2t-3v,\qquad r=vL,
\]

and let `Y_n` be the ordinary `s^n` coefficient of the source substitution
computed from

\[
F_0\circ\psi_s=\exp(-sX_H)\circ F_s.
\]

The already-computed orders two through six have degrees

\[
11,13,21,23,31.
\]

Writing `top` for the highest total-degree homogeneous part gives

\[
X:=Y_2^{\rm top},\qquad
Y_3^{\rm top}=fX,\qquad f=-\frac7{18}r,
\]

with

\[
X(r)=0.
\]

Thus `X` and `fX` commute. Direct extraction through order six gives

\[
Y_4^{\rm top}=\frac12X^2,\qquad
Y_5^{\rm top}=X(fX),\qquad
Y_6^{\rm top}=\frac16X^3.
\]

## Candidate mechanism

The `X`-flow is explicitly integrable. With

\[
A=\frac3{64}v^6L^4,
\]

its action in `(v,L)` coordinates is

\[
\Phi_\tau(v,L)=
\left(v(1+A\tau)^{-1/2},\;L(1+A\tau)^{1/2}\right).
\]

The first two primitive top jets combine as

\[
\tau=s^2+fs^3.
\]

Consequently the flow predicts nonzero top coefficients and degrees

\[
d_{2k}=10k+1,\qquad d_{2k+1}=10k+3.
\]

This explains the observed alternating increments as a single mechanism.
It does not yet show that later primitive logarithm terms cannot attain the
same or a larger filtration degree.

## Prospective theorem

Let

\[
\log(\psi_s)=\sum_{j\ge2}s^j Z_j
\]

in the completed substitution group. Define the degree deficit

\[
\Delta_j=5j-(\deg Z_j-1).
\]

The required substrate estimates are

\[
\Delta_j>0\quad(j\ge4\text{ even}),\qquad
\Delta_j>3\quad(j\ge5\text{ odd}).
\]

They make the all-`X` index multiset uniquely maximal at even order and the
multiset containing exactly one `fX` uniquely maximal at odd order. There are
several placements of the odd entry; they coalesce in the associated graded
because `X(f)=0`. The closed-flow coefficients then prevent cancellation.

## Attack vectors and kill conditions

1. Derive an exact recurrence for the substitution logarithm and prove the
   deficit inequalities from the seed and family degrees.
2. Search for a later even primitive with `deg Z_j - 1 >= 5j` or a later odd
   primitive with `Delta_j <= 3`; either one kills the proposed dominance.
3. Check that the filtration composition law has no second maximal index
   multiset hidden by commutators, and check explicitly that the tied odd
   placements coalesce rather than cancel.
4. Check the nonzero binomial top coefficient in characteristic zero.
5. Keep this target-gauge result separate from the canonical source-only lift
   and from any minimization over target gauges.

## Intended formal surface

Formalize a substrate-independent filtered-substitution lemma: given primitive
deficits with the two strict bounds, the even and odd maximal index multisets
are unique and have the stated degrees. Odd placements are identified only
after passing to the commuting associated graded. Keep the family-specific
deficit proof outside that lemma until its exact recurrence is established.
