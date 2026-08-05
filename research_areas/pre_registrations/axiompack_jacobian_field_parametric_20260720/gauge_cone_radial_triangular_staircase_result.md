# A coefficientwise-finite cone staircase of rate at most two

## Result

There is a recursively defined cone-valued polynomial Hamiltonian connection

\[
K_s=\sum_{n\ge1}s^nK_n(P,Q)
\]

whose source right-logarithmic velocity lies in the shifted slope-two Rees
module.  Consequently its integrated polynomial contact satisfies

\[
\deg Y_q\le2q+1,
\qquad
\deg X_{\Omega_q^{\rm tgt}}\le q+1,
\]

and the symmetric tail statistic obeys

\[
\boxed{\sigma_{\rm ct}\le2}.
\]

Each \(K_n\) is a finite linear combination of target-lift-compatible cone
monomials \(P^aQ^b\), \(b\ge1,\ a\le2b\), excluding the bare monomial
\(Q\).  The construction therefore stays inside
\(\mathbb Q[P,Q][[s]]\); it does not use the infinitely supported first row
of the completed canonical normalizer.

This is an upper-bound construction.  It does not prove
\(\sigma_{\rm ct}\ge2\).

## Two-layer family identity

Put

\[
U_s=1+\frac{3(s-4)}{2(s-6)}v,
\qquad z=2+2t-3v,
\qquad r=U_sz.
\]

In this moving affine source chart, the exact family has

\[
P_s=A_s(r)+a_s z,
\qquad
Q_s=B_s(r)+b_srz,
\]

where

\[
\begin{aligned}
A_s(r)
={}&-\frac{s(s-6)}{48}r^3
+\frac{(s-6)(s+2)}{16}r^2
-\frac{(s-6)(s+4)}{24}r,\\
a_s={}&-\frac{s-6}{12},\\
B_s(r)
={}&-\frac{3s}{16(s-4)}r^4
+\frac{s+2}{2(s-4)}r^3
-\frac{s+4}{4(s-4)}r^2,\\
b_s={}&-\frac1{s-4}.
\end{aligned}
\]

Their radial and first-normal layers satisfy the exact moving tangency

\[
A_s'(r)=L_s(r)a_s,
\qquad
B_s'(r)=L_s(r)b_sr,
\]

with

\[
L_s(r)
=\frac{3sr^2-6sr-12r+2s+8}{4}
=L_0(r)+sL_1(r).
\]

Thus, for every polynomial target Hamiltonian \(K\), if

\[
K(P_s,Q_s)=R_s(r)+zN_s(r)+O(z^2),
\]

then

\[
\boxed{R_s'(r)=L_s(r)N_s(r).}
\]

The first-normal response is controlled by the radial restriction rather
than being an independent high-degree layer.

## Finite radial recursion

At the seed,

\[
\operatorname{top}P_0=-\frac34r^2,
\qquad
\operatorname{top}Q_0=-\frac14r^3.
\]

The leading radial symbol of \(P^aQ^b\) has weight \(2a+3b\) and a nonzero
coefficient.  The weights represented by the cone together with the
target-lift condition are exactly

\[
\boxed{\{w:w\ge5\}}.
\]

Suppose rows below \(n\) have been chosen.  The coefficient of \(s^n\) in
the carried source Hamiltonian has radial degree at most \(n+6\).  Descending
through its radial degrees, subtract the canonical cone monomial of the same
weight whenever the weight lies in the displayed semigroup.  The leading
radial symbol is diagonal, so this process terminates and leaves only the
bounded weights \(0,1,2,3,4\).  In the actual rows the nonzero radial
remainder is supported at weights three and four.

The resulting \(K_n\) uses only weights at most \(n+6\).  Hence every row is
finite.  In the selected normalization the first five row dimensions are

\[
\boxed{(3,4,5,6,7)},
\]

and the source Hamiltonian degrees at velocity costs two through six are

\[
(8,10,12,14,16).
\]

The omitted column is exactly \(Q\).  Since \(P_s\in(z)\) and
\(Q_s\in(z^2)\), every retained nonconstant target monomial has pullback
order \(a+2b\ge3\).  Its density-\(z^2\) Hamiltonian field is therefore
polynomial.  The finite replay checks this condition at every row.

## Rees induction

For a target monomial of seed weight \(w=2a+3b\), the coefficient of
\(s^\delta z^j\) in

\[
P_s^aQ_s^b
\]

has \(r\)-degree at most

\[
w+\delta-2j.
\]

This follows directly from the two-layer formulas: every parameter order
raises radial degree by at most one, while every normal factor lowers it by
at least two.

The finite coefficient replay uses the fixed chart \(u=v+1\).  The
transition

\[
U_s=\mu_su+(1-\mu_s),
\qquad
\mu_s=\frac{3(s-4)}{2(s-6)},
\]

is affine in space, analytic and invertible at \(s=0\), and has \(U_0=u\).
Substituting it coefficientwise cannot increase spatial degree; in
\(r=U_sz\), it can only raise the fixed-chart normal order.  The moving
Rees estimate therefore transfers to the fixed chart.  The induced frame
velocity is affine and does not affect the tail rate.

At row \(n\), every earlier target term therefore has, for \(j\ge2\),

\[
\deg_r[z^j]H_n\le n+6-2j,
\]

and hence

\[
2\deg_r[z^j]H_n+j\le2n+6.
\]

The radial row has already been reduced to bounded degree.  For the
first-normal layer, write \(R_n,N_n\) for the target radial and \(z^1\)
coefficients.  The moving tangency gives

\[
L_0N_n=R_n'-L_1N_{n-1}.
\]

After radial reduction, induction from
\(\deg_rN_{n-1}\le n+1\) yields

\[
\deg_rN_n\le n+2.
\]

The source-only Hamiltonian has uniform spatial degree at most eighteen.
It is therefore inside the same bound from \(n=6\) onward; the first five
rows are the exact finite base calculation above.

Combining the radial, first-normal, and higher-normal layers gives

\[
\boxed{\deg H_n^{\rm src}\le2n+6}
\]

for every coefficient \(s^n\).  Its density-\(z^2\) Hamiltonian vector field
has degree at most \(2n+3\).  The shifted Rees module is closed under
right-Magnus integration, so at logarithmic order \(q=n+1\),

\[
\deg Y_q\le2q+1.
\]

On the target, every row monomial has ordinary degree at most \(n+3\).
The constant-density Hamiltonian grading is bracket-additive, giving target
logarithmic rate at most one.

## Verification and boundary

The deterministic replay
[`gauge_cone_radial_triangular_staircase.py`](gauge_cone_radial_triangular_staircase.py)
constructs the rows over \(\mathbb Q\), checks exact radial cancellation,
target-lift support and polynomial-source divisibility, the moving
tangency identity, normal-layer profiles, and side-typed source and target
`dexp` round trips.  The first five rows are a finite stress test; the
all-order conclusion uses the explicit two-layer and degree induction
above.

The arithmetic endpoint
[`AxiomPackJacobianConeRadialStaircaseArithmetic.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianConeRadialStaircaseArithmetic.lean)
kernel-checks the cone-weight families, target-degree inequality,
higher-normal and first-normal Rees bounds, and the
Hamiltonian-to-vector degree translation.

The construction proves that the earlier rates \(5,4,7/2,\ldots\) were
properties of incomplete radial normalizations.

### Subsequent lower-bound comparison

The later pure contact-zero tensor induction and least-positive-contact
moving-backbone induction exhaust the declared coefficientwise-polynomial
category and prove the matching lower bound.  Their composition is recorded
in
[`gauge_unrestricted_tail_minimax_result.md`](gauge_unrestricted_tail_minimax_result.md).
Thus this staircase supplies the upper half of \(\sigma_{\rm ct}=2\); its
finite replay remains only a stress test for the all-order Rees argument.
