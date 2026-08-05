# Complete-affine escape test for the first transverse high shell

**Status:** pre-computation pencil

## Eigenquestion

After solving the natural-weight moving cone contact through instantaneous
order four at its exact minimum caps

\[
(5,5,7,9,11),
\]

the complete affine prefix has dimension six.  Can any point in this affine
family cancel the degree-fourteen shell of the source Magnus coefficient
\(\Omega^{\rm src}_5\)?

This is the first complete-prefix test of the transverse ray seen in the
selected logarithm.  It is stronger than varying the single order-two
direction, but remains a finite-prefix question.

## Governing shell algebra

In adapted coordinates

\[
V=v,\qquad G=t-\frac32v,
\]

the leading source-volume condition is

\[
\operatorname{div}(G^2D)=0.
\]

For

\[
D_{a,b}
=
\left(
V^aG^b,
-\frac{a}{b+3}V^{a-1}G^{b+1}
\right),
\]

this condition is exact.  With

\[
W_4=D_{4,1},
\qquad
Z_m=D_{3m-5,m-1},
\]

direct differentiation predicts

\[
[W_4,D_{a,b}]
=
\frac{(b+4)(a-b-3)}{b+3}D_{a+3,b+1}
\]

and hence

\[
\operatorname{ad}_{W_4}^{\,k}Z_5
=
\frac{k+7}{7}(2k+1)!!\,Z_{5+k}\ne0.
\]

This proves nonvanishing of an escaping Lie word.  It does not prove that
its coefficient survives the complete affine connection.

## Candidate theorem or escape

Let \(\lambda_1,\ldots,\lambda_6\) coordinatize the exact affine solution
space through instantaneous order four.  Compute the full homogeneous
degree-fourteen vector shell

\[
T_5(\lambda)
=\operatorname{top}_{14}\Omega^{\rm src}_5(\lambda).
\]

There are two discriminating outcomes:

1. **obstruction:** the coefficient ideal of \(T_5\) contains a nonzero
   rational constant, so no affine prefix cancels the shell;
2. **escape:** exhibit a rational \(\lambda\) for which every degree-fourteen
   coefficient vanishes, and replay both the contact equations and the
   mixed-orientation `dexp` identity at that point.

A numerical minimizer, one-coordinate sample, or selected particular
solution does not decide the question.

## Proof skeleton

1. Reconstruct the exact affine base and complete kernel through order four.
2. Verify that the outgoing dimension is six and that every direction
   satisfies the homogeneous contact equations through the full prefix.
3. Form the source velocity with six symbolic parameters and apply the
   right-multiplication Magnus recursion through order five.
4. Transform vector components to \((V,G)\), project to total degree
   fourteen, and collect every coefficient in
   \(\mathbb Q[\lambda_1,\ldots,\lambda_6]\).
5. Compute a rational Gröbner certificate for inconsistency of the
   cancellation equations, or decode a rational zero and replay it exactly.
6. Separately verify the displayed \(D_{a,b}\) bracket and iterated
   \(W_4\)-action formulas.

## Kill conditions

The obstruction is killed by one exact rational cancelling prefix.  The
escape is killed if any omitted degree-fourteen coefficient survives, if
the proposed parameter point leaves the affine contact family, or if its
forward-`dexp` replay fails.

If the coefficient system is positive-dimensional but has no immediate
rational point, report that algebraic residual without replacing it by a
floating-point conclusion.

## Recurrence and capability check

The existing affine contact replay, equation-typed formal Lie series, exact
polynomial normalization, and SymPy rational ideal operations cover the
test.  The prior capability-amnesia query surfaced the scalar recurrence
finder, which does not own multivariate affine-shell cancellation.  No new
general primitive is introduced unless this calculation exposes a reusable
certificate boundary absent from those owners.

## Intended formal surface

If the obstruction reduces to a small rational identity, formalize only its
arithmetic spine after the pencil calculation.  If a cancelling point
exists, the executable exact replay is the primary finite certificate; no
all-order statement follows.

## Exact outcome

The obstruction outcome holds.  The replay
[`gauge_moving_cone_log_five_affine_escape.py`](gauge_moving_cone_log_five_affine_escape.py)
reconstructs the complete six-dimensional affine family, verifies the
rational base and every homogeneous contact direction, and passes the
right-multiplication forward-`dexp` round trip.

All six parameters disappear from the complete degree-fourteen shell:

\[
\boxed{
\operatorname{top}_{14}\Omega^{\rm src}_5
=
\left(
\frac7{276480}V^{10}G^4,
-\frac1{27648}V^9G^5
\right)
=\frac7{276480}Z_5.}
\]

Thus its coefficient ideal already contains the two nonzero constants
\(7/276480\) and \(-1/27648\).  No point of the complete minimum-cap affine
prefix cancels this shell over characteristic zero.

The same replay verifies the general divergence-free monomial bracket and
the iterated coefficients through \(Z_{13}\).  Algebraically,

\[
\operatorname{ad}_{W_4}^{\,k}Z_5
=\frac{k+7}{7}(2k+1)!!\,Z_{5+k},
\]

so every word on this ray is nonzero.  What remains unproved is that the
coefficient of this word survives all later compatible affine choices or
that cancelling it necessarily incurs the same asymptotic cost elsewhere.
