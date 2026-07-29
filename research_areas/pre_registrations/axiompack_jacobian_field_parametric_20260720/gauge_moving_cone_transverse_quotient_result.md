# Transverse-line quotient of the carried moving cone family

**Status:** exact complete-affine prefix through instantaneous order six;
order-seven residual lookahead; no all-order claim

## Quotient

Use

\[
G=t-\frac32V,\qquad \ell=\{V=-1\}.
\]

The seed restricts to

\[
F_0|_\ell=(P,Q)=(G+1,0),
\]

with

\[
\left.\partial_VQ_0\right|_\ell=(G+1)^2,
\qquad
\left.\partial_GQ_0\right|_\ell=0.
\]

Every cone Hamiltonian has the form

\[
K=c+\sum_{\substack{b\ge1\\a\le2b}}c_{a,b}P^aQ^b.
\]

Consequently

\[
(X_K)_Q(P,0)=-K_P(P,0)=0.
\]

If a new source field has component degree at most \(B\), its contribution
to the second contact equation on \(\ell\) has \(G\)-degree at most \(B+2\).
For the residual before the new \(K_j,V_j\) are added, define

\[
\Lambda_B(R_j)
=
\sum_{d>B+2}[G^d](R_j)_Q|_\ell\,G^d.
\]

The replay
[`gauge_moving_cone_transverse_quotient.py`](gauge_moving_cone_transverse_quotient.py)
carries the complete lower affine cone family from
[`gauge_moving_section_affine_extension.py`](gauge_moving_section_affine_extension.py).
For every \(B\), it solves the exact coefficient equations asking whether
the lower affine parameters can make \(\Lambda_B(R_j)\) vanish.

This is a necessary quotient test.  Its vanishing does not imply
consistency of the complete contact system at cap \(B\).

## Exact result

The carried cone caps through orders zero to six are

\[
(5,5,7,9,11,13,14).
\]

The affine dimensions entering the next equations are

\[
(0,0,0,1,3,6,10,14).
\]

The last value is the complete dimension after order six and enters the
order-seven lookahead.

| \(j\) | affine dim. in | \(\deg_G(R_j)_Q|_\ell\) | invariant leading coefficient | maximum lower-direction degree | minimum \(B\) not excluded by \(\Lambda_B\) |
|---:|---:|---:|---:|---:|---:|
| 0 | 0 | 2 | \(1/12\) | — | 0 |
| 1 | 0 | 2 | \(5/96\) | — | 0 |
| 2 | 0 | 3 | \(-1/2016\) | — | 1 |
| 3 | 1 | 3 | \(-3/896\) | 2 | 1 |
| 4 | 3 | 4 | \(115/129024\) | 2 | 2 |
| 5 | 6 | 4 | \(-4775/387072\) | 3 | 2 |
| 6 | 10 | 5 | \(-3485/688128\) | 3 | 3 |
| 7 lookahead | 14 | 5 | \(62395/1179648\) | 4 | 3 |

At every displayed order, all lower affine directions have line degree
strictly below the residual's leading degree.  The leading coefficient is
therefore invariant across the complete carried affine family.

For \(j=2,\ldots,7\), the cap immediately below the last column leaves one
uncancelled semantic row:

\[
[G^{\lfloor j/2\rfloor+2}](R_j)_Q|_\ell.
\]

Its normalized functional has support consisting of that single
\(G\)-degree.  The support hashes are:

\[
\begin{array}{c|c|c}
j&\text{degree}&\text{SHA-256}\\ \hline
2,3&3&
\texttt{f5418761324496bc2d667f15dbb19a951ef9279fe23479c7f25a1e17027c82f6}\\
4,5&4&
\texttt{9fa89c7978bd8a258f10c50f5245e45e0bdf531fb6e5497d690ac09518b79af1}\\
6,7&5&
\texttt{c4189248a95231108fac70363572959ac93d455b7fadc18cc242c996943f1bc3}
\end{array}
\]

Thus the exact finite profile is

\[
\boxed{
\min B_{\Lambda}
=(0,0,1,1,2,2,3,3)
}
\]

through the lookahead.

## Comparison with the full-system caps

The fixed caps \(B=11\) and \(B=23\) pass \(\Lambda_B\) at every displayed
order.  Their projections are empty because the restricted residual degrees
are at most five.

The immediately preceding complete-system caps also pass this quotient:

\[
(4,4,6,8,10,12,13).
\]

Yet the full contact matrices are inconsistent at those caps.  Therefore
the known one-below-minimum failures through order six are not caused by the
transverse \(C\)-adic quotient detected on \(\ell\).  Their cokernels live
in other source/target directions.

Conversely, the line quotient supplies a much smaller forced source
component inside the declared carried minimal-prefix family.  Through this
prefix it grows in pairs according to

\[
0,0,1,1,2,2,3,3.
\]

No recurrence has been derived for that sequence.  It must not be
extrapolated.

## Interpretation

The complete target-lift module contains the unbounded \(C^k\) transverse
tower exhibited in
[`gauge_cone_triangular_lift_pencil.md`](gauge_cone_triangular_lift_pencil.md).
The particular moving cone recurrence avoids exciting that tower through
all six solved orders and the next residual.  This is evidence that the
moving residual occupies a smaller module than the complete target-lift
space.

The finite result does not prove that this smaller module is invariant at
all orders.  The next theorem-level gate is a recurrence or invariant
showing that the line degree remains bounded, or an exact first order where
\(\Lambda_{11}\) becomes nonzero after carrying every lower affine
direction.

Even an all-order \(\Lambda_{11}=0\) theorem would control only one
transverse quotient of the instantaneous equation.  It would still require
the remaining higher-normal quotients and the source Magnus Lie closure
before changing the symmetric logarithmic statistic.
