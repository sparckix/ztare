# Coupled radial triangular cone staircase

## Claim boundary

This pencil tests whether the successive \(4,7/2,10/3\) Newton drops are the
first rows of a coefficientwise-finite triangular construction.  It does
not assume that removing every instantaneous radial face controls the
nonradial Magnus logarithm.

## Eigenquestion

At each parameter cost, can all extremal radial source monomials be canceled
simultaneously by the finite set of cone monomials having the same seed
radial weights, and does the resulting Newton slope continue to drop?

## Seed diagonal

In the adapted source chart,

\[
\operatorname{top}P_0=-\frac34u^2z^2,
\qquad
\operatorname{top}Q_0=-\frac14u^3z^3.
\]

Thus a cone monomial \(P^aQ^b\) has a nonzero diagonal radial symbol

\[
8\,\operatorname{top}(P_0^aQ_0^b)
=8\left(-\frac34\right)^a
\left(-\frac14\right)^b
u^{2a+3b}z^{2a+3b}.
\]

At a fixed parameter order, distinct weights \(2a+3b\) do not mix on this
top radial symbol.  Each row is therefore a finite triangular cancellation
problem, provided only finitely many radial weights are extremal.

## First coupled row

The order-one coefficients are fixed as

\[
-\frac1{168}P^2Q+\frac{325}{1344}Q^2.
\]

At order two, two independent weights are needed:

\[
\boxed{
\frac{11}{2016}P^2Q-\frac1{5376}PQ^2.
}
\]

The first term cancels the cost-three \(u^7z^7\) velocity; the second cancels
the cost-three \(u^8z^8\) velocity.

The exact cost-four residual must then be recomputed before choosing the
order-three row.  Do not reuse the \(Q^3\)-only coefficient, because the new
order-two \(P^2Q\) term changes the next carried residual.

## Discriminating computation

1. Reconstruct the unfiltered source velocity with the coupled order-two
   row.
2. Verify simultaneous disappearance of the cost-three radial weights seven
   and eight.
3. Enumerate the complete cost-four radial residual.
4. Solve its exact diagonal system using the finite cone monomials of the
   same weights.
5. Repeat through at least two further rows, recording the row dimensions,
   coefficients, instantaneous degree profile, and Newton polygon after each
   solve.
6. At every row, verify source and target forward-`dexp` round trips.
7. Search the first nonradial zero-grade quotient after radial
   normalization; a falling instantaneous polygon is not sufficient.

## Success and kill conditions

The triangular mechanism advances if every tested row has an exact rational
solution, row support remains finite, and the symmetric Newton slope drops
strictly without a nonradial logarithmic shell restoring an earlier slope.

It is killed by a radial weight outside the seed cone semigroup, a
same-weight rank failure, row support that becomes infinite, a target
envelope at least as large as the source improvement, or a persistent
nonradial quotient whose rate stops decreasing.

An all-order construction additionally owes a recurrence proving local
finiteness and a uniform logarithmic estimate.  Finite row solvability alone
does not determine \(\sigma_{\rm ct}\).

## Five-row exact outcome

The first five rows solve over \(\mathbb Q\).  A later target-lift audit
removed the bare \(Q\) column, which was in the cone but outside the
declared target-lift category.  The corrected dimensions are

\[
\boxed{(3,4,5,6,7)},
\]

and row \(n\) uses precisely the cone-and-lift weights

\[
\{5,6,\ldots,n+6\}.
\]

The first two rows begin

\[
\begin{aligned}
K_1={}&-\frac1{168}P^2Q
+\frac{325}{1344}Q^2
-\frac{43}{3360}PQ,\\
K_2={}&-\frac1{5376}PQ^2
+\frac{11}{2016}P^2Q
-\frac{8347}{107520}Q^2\\
&+\frac{883}{161280}PQ.
\end{aligned}
\]

After each row, the only radial Hamiltonian monomials left are \(r^3,r^4\),
where \(r=uz\); weights three and four do not lie in the corrected
cone-and-target-lift semigroup.  Every nonconstant source Hamiltonian
monomial has \(z\)-exponent at least three and therefore defines a
polynomial density-\(z^2\) field.
The complete source Hamiltonian degree profile is

\[
\boxed{(8,10,12,14,16)}
\]

at velocity costs two through six.  The top nonradial terms are

\[
r^{q+1}z^2
=u^{q+1}z^{q+3},
\]

so every checked row satisfies

\[
\deg H_q=2q+4.
\]

The target rows remain in logarithmic rate at most one.  Thus the finite
radial normalization reaches exactly the shifted slope-two Rees envelope
required by the contact statistic.

## All-order structural target

For the all-order estimate, use the moving affine source coordinate

\[
U_s=1+\frac{3(s-4)}{2(s-6)}v,
\qquad r=U_sz,
\]

rather than the fixed coefficient-extraction coordinate \(u=v+1\).  The
adapted family then has the exact two-layer form

\[
\begin{aligned}
P_s&=A_s(r)+a_s z,\\
Q_s&=B_s(r)+b_s rz,
\end{aligned}
\]

with \(\deg_rA_s\le3\) and \(\deg_rB_s\le4\).  This identifies the prospective
induction:

1. the radial coefficient at row \(n\) has degree at most \(n+6\);
2. the seed cone-and-lift semigroup contains every degree from five to
   \(n+6\), so a finite triangular row leaves only the bounded
   \(r^3,r^4\) remainder;
3. after separating the bounded \(r^3,r^4\) remainder, the normal residual
   is divisible by \(z^2\);
4. its \(z^j\) coefficient obeys
   \[
   2\deg_r+j\le2n+6.
   \]

These four statements would prove a coefficientwise-finite instantaneous
connection with

\[
\deg H_q\le2q+4
\quad\text{for every }q.
\]

The shifted Rees Magnus lemma would then give source logarithmic rate at
most two, while the target remains at most one.

The chart transition is affine in the spatial variable, is analytic and
invertible at \(s=0\), and satisfies \(U_0=u\).  Expanding
\(r=U_sz\) in the fixed chart can only preserve or lower spatial degree and
can only raise normal order.  Hence a coefficientwise Rees bound proved in
the moving chart transfers to the fixed chart used by the finite replay.

The exact family has \(P_s\in(z)\) and \(Q_s\in(z^2)\).  Every retained
nonconstant target monomial satisfies \(a+2b\ge3\), so its pulled-back
Hamiltonian lies in \((z^3)\).  This is the polynomial-source gate missed
by the first version of the finite replay.

The next kill test is the normal-layer induction, not another radial rank
table.  A \(z^1\) term above the displayed bound, a \(z^j\) coefficient
whose \(r\)-degree grows too quickly, or a row whose radial degree exceeds
\(n+6\) kills this construction.  If the induction passes, the remaining
question is whether the tail statistic has a universal lower bound two.

The deterministic finite replay is
[`gauge_cone_radial_triangular_staircase.py`](gauge_cone_radial_triangular_staircase.py).
