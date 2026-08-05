# Successive complete-affine invariance of the transverse \(Z\)-ray

**Status:** pre-computation successor pencil

## Eigenquestion

The complete six-dimensional minimum-cap prefix fixes

\[
\operatorname{top}_{14}\Omega^{\rm src}_5
=\frac7{276480}Z_5.
\]

After carrying the complete affine family through instantaneous orders five
and six, do all ten and fourteen affine parameters also disappear from the
degree-eighteen and degree-twenty-two shells of
\(\Omega^{\rm src}_6\) and \(\Omega^{\rm src}_7\)?

## Candidate recurrence

For

\[
D_{a,b}
=
\left(
V^aG^b,
-\frac{a}{b+3}V^{a-1}G^{b+1}
\right),
\qquad
Z_m=D_{3m-5,m-1},
\]

the exact bracket law

\[
[W_4,D_{a,b}]
=
\frac{(b+4)(a-b-3)}{b+3}D_{a+3,b+1}
\]

advances \(Z_m\) to \(Z_{m+1}\).  The selected prefix suggests

\[
\operatorname{top}_{4m-6}\Omega^{\rm src}_m
=c_mZ_m
\qquad(m=5,6,7).
\]

This test asks whether \(c_6,c_7\) are invariants of the complete
minimum-cap affine solution spaces, not whether the displayed relation
continues indefinitely.

## Discriminating test

1. Reconstruct the complete affine carries with caps
   \((5,5,7,9,11,13)\) and
   \((5,5,7,9,11,13,14)\).
2. Verify the rational base and every homogeneous contact direction.
3. Introduce all ten, respectively fourteen, affine parameters.
4. Apply the source right-multiplication Magnus recursion through orders six
   and seven and pass its forward-`dexp` round trip.
5. Transform to \((V,G)\) and collect every coefficient at degrees eighteen
   and twenty-two.
6. Report a constant-coefficient obstruction, an exact rational cancelling
   point, or the remaining rational ideal.

## Success and kill conditions

Success for affine invariance requires every parameter to disappear from the
complete high shell and at least one rational coefficient to remain nonzero.
One selected solution, parameter sampling, or agreement with the
\(W_4\)-word coefficient is insufficient.

The hypothesis is killed by an exact parameter-dependent coefficient.  If
that occurs, solve the cancellation equations rather than treating
dependence alone as an escape.

## All-order boundary

Two additional invariant shells would support an associated-graded
induction, but would not prove it.  An all-order result still needs:

- a filtration theorem excluding new instantaneous controls from the
  \(Z_m\) quotient;
- the exact induced Magnus recurrence for \(c_m\); and
- a proof that any cancellation route pays the symmetric source/target
  statistic elsewhere.

No tail-minimax conclusion is permitted from this finite test.

## Exact outcome

The successor replay
[`gauge_moving_cone_z_ray_affine_invariance.py`](gauge_moving_cone_z_ray_affine_invariance.py)
passes both cases.  It verifies every rational base and homogeneous contact
direction, retains all affine parameters symbolically in the source Magnus
recursion, and passes both right-multiplication forward-`dexp` round trips.

For the complete ten-dimensional affine family through instantaneous order
five,

\[
\boxed{
\operatorname{top}_{18}\Omega^{\rm src}_6
=-\frac1{184320}Z_6.}
\]

For the complete fourteen-dimensional affine family through instantaneous
order six,

\[
\boxed{
\operatorname{top}_{22}\Omega^{\rm src}_7
=-\frac1{1376256}Z_7.}
\]

Every affine parameter disappears from both complete shells.  Together with
the predecessor, the exact invariant sequence is therefore

\[
\operatorname{top}_{4m-6}\Omega^{\rm src}_m=c_mZ_m,
\qquad
(c_5,c_6,c_7)
=\left(
\frac7{276480},
-\frac1{184320},
-\frac1{1376256}
\right).
\]

An exact forward-`dexp` decomposition at order six prevents a premature
one-generator recurrence.  The degree-eighteen cancellation uses bracket
depths zero through four; the first-component contributions are

\[
-\frac1{30720},\quad
-\frac1{23040},\quad
\frac1{6144},\quad
-\frac1{18432},\quad
-\frac1{30720},
\]

which sum to zero.  Thus repeated \(W_4\)-action on the leading \(Z_5\)
shell is only one contributor.  An all-order recurrence must retain the
relevant lower \(Z_j\)-projections of the complete low-order logarithm.

The order-seven kernel successor extends the invariant sequence once more:

\[
\operatorname{top}_{26}\Omega^{\rm src}_8
=\frac5{14155776}Z_8
\]

across the complete twenty-one-dimensional outgoing affine family.
