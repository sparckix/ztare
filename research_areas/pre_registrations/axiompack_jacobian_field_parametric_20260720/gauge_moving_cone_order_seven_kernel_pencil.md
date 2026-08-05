# Exact order-seven affine kernel and fourth \(Z\)-shell test

**Status:** pre-computation successor pencil

## Eigenquestion

The exact instantaneous order-seven system first becomes consistent at
source cap seventeen.  Its matrix has shape \(692\times363\) and rational
rank \(342\), so the expected outgoing affine dimension is twenty-one.

Does the complete twenty-one-dimensional prefix preserve

\[
\operatorname{top}_{26}\Omega^{\rm src}_8
=\frac5{14155776}Z_8,
\]

or is the selected order-eight shell cancellable by an outgoing affine
direction?

## Exact kernel certificate

Use the already verified modular pivot square only to select 342 pivot rows
and columns.  Over \(\mathbb Q\), solve one multi-right-hand-side system:

\[
B X=
\left[
b_R\ \middle|\ -M_{R,F}
\right],
\]

where \(F\) is the set of twenty-one free columns.

The first column gives a particular solution.  Each remaining column,
together with its corresponding unit free coordinate, gives a homogeneous
direction.  Verify exactly against all 692 rows:

\[
Mx_0=b,\qquad MN=0.
\]

Only after those full identities pass may the vectors be decoded as
connection prefixes.

## Discriminating logarithmic test

1. Reconstruct the complete fourteen-dimensional input through order six.
2. Build and exactly solve the cap-seventeen multi-right-hand-side system.
3. Decode the base and all twenty-one outgoing directions.
4. Verify every contact equation through instantaneous order seven for the
   base and each homogeneous direction.
5. Retain twenty-one symbolic parameters in the right-multiplication Magnus
   recursion through logarithmic order eight.
6. Project the adapted source logarithm to degree twenty-six and decide
   whether every parameter disappears.

The invariance hypothesis succeeds only if the complete shell is a nonzero
constant multiple of \(Z_8\).  It is killed by parameter dependence; in that
case, solve the exact cancellation ideal before claiming an escape.

## Capability disposition

This is the second campaign caller for modular-pivot/rational-lift linear
certification and the first multi-right-hand-side kernel caller.  If the
method passes, promote the substrate-invariant operation to
`src/ztare/common` with:

- a typed consistency/inconsistency result;
- exact full-row verification;
- explicit separation between modular pivot selection and rational proof;
- deterministic sparse hashes; and
- small self-tests covering a consistent affine family and an inconsistent
  system.

Backend benchmarking beyond SymPy is deferred because no second exact
backend is present in the repository; that absence must be recorded rather
than simulated.

## Claim boundary

Even a fourth successive complete-affine invariant shell is finite evidence.
It does not classify all later kernels, prove a scalar recurrence, or settle
the symmetric tail statistic.

## Exact outcome

The replay
[`gauge_moving_cone_order_seven_kernel.py`](gauge_moving_cone_order_seven_kernel.py)
passes the multi-right-hand-side lift.  The exact cap-seventeen receipt is

\[
\operatorname{rank}_{\mathbb Q}M=342,\qquad
\dim\ker M=21
\]

for the \(692\times363\) system.  One particular column and all twenty-one
kernel columns replay every rational row.  After decoding, the base and all
twenty-one homogeneous connection prefixes satisfy every contact equation
through instantaneous order seven.

The projection of the outgoing kernel onto the fourteen incoming affine
coordinates has rank fourteen.  Hence every lower affine prefix extends.
All new order-seven source directions have degree at most seventeen, so the
newest velocity cannot contribute to the degree-twenty-six part of
\(\Omega^{\rm src}_8\).

Keeping all fourteen lower parameters symbolically gives

\[
\boxed{
\operatorname{top}_{26}\Omega^{\rm src}_8
=
\left(
\frac5{14155776}V^{19}G^7,
-\frac{19}{28311552}V^{18}G^8
\right)
=\frac5{14155776}Z_8.}
\]

Every affine parameter disappears.  Thus \(Z_5,Z_6,Z_7,Z_8\) are four
successive complete-affine invariant shells.

The modular-pivot/rational-lift operation now lives at
`src/ztare/common/exact_linear_system.py`.  Its API separates exact
inconsistency, one verified particular solution, and a full affine
particular-plus-kernel certificate; focused tests cover both consistent and
inconsistent systems.  SymPy remains the only exact backend currently
available, so comparative backend benchmarking remains deferred.
