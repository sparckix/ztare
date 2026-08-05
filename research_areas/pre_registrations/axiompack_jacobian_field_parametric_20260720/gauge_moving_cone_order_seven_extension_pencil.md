# Moving cone order-seven extension

**Status:** pre-computation pencil for the first unseen complete-affine order

## Eigenquestion

For the natural-weight moving Hamiltonian cone, the exact minimum source
caps through instantaneous order six are

\[
(5,5,7,9,11,13,14).
\]

After carrying the complete lower affine kernel, is source cap fifteen the
minimum at instantaneous order seven?

This is a finite discriminator for the selected moving connection.  It
tests whether the apparent cap saturation after order six persists; it does
not infer an asymptotic logarithmic rate.

## Exact certificate strategy

The direct rational augmented-rank calculation at order seven is much
larger than the preceding systems.  A finite-field calculation may select
pivot rows and columns, but it may not by itself certify a
characteristic-zero rank or solution.

For a rational system \(Mx=b\), use a prime only to choose a square pivot
minor \(B=M_{R,C}\).

### Consistency certificate

Solve

\[
Bx_C=b_R
\]

over \(\mathbb Q\), set every other coordinate to zero, and verify exactly

\[
M_{*,C}x_C=b.
\]

The final equality against every original row is the certificate.  The
modular calculation is only a pivot selector.

### Inconsistency certificate

Choose a nonpivot row \(i\).  Solve over \(\mathbb Q\)

\[
\alpha B=M_{i,C}.
\]

Verify exactly

\[
\alpha M_{R,*}=M_{i,*},
\qquad
\alpha b_R\ne b_i.
\]

Then the supported row functional

\[
y=e_i-\sum_{r\in R}\alpha_r e_r
\]

satisfies \(yM=0\) and \(yb\ne0\).  This certifies inconsistency without
forming a complete rational row reduction.

## Discriminating test

1. Reconstruct the selected base point and complete affine directions
   through order six using the established caps.
2. Build the exact order-seven systems at caps fourteen and fifteen.
3. Produce a rational inconsistency functional for cap fourteen.
4. Produce a rational particular solution for cap fifteen and replay every
   equation.
5. Decode the new target Hamiltonian and source field, then extend the
   mixed-orientation Magnus logarithm through order eight.
6. Record the complete affine nullity only if an exact rational kernel is
   computationally available.  A particular solution alone cannot support
   an order-eight complete-affine continuation.

## Success and kill conditions

The minimum cap is fifteen only if both rational certificates pass.  A
modular rank match, sampled residual, or partial row check is insufficient.

The test is killed if cap fourteen is consistent, cap fifteen has no
rational solution, or the decoded solution fails the full instantaneous
contact replay.

## Capability boundary

The pivot-and-verify method is implemented campaign-locally for this single
large system.  Promotion to `src/ztare` is deferred until it has a second
caller and comparative backend tests; the existing recurrence primitive
does not own sparse rational linear-system certification.

## Claim boundary

Even a successful order-seven extension remains finite-prefix evidence.
It does not prove that every later affine choice preserves an escaping
Magnus shell, and it does not settle the symmetric tail minimax.

## Exact outcome

The preregistered cap-fifteen expectation was false.  The replay
[`gauge_moving_cone_order_seven_extension.py`](gauge_moving_cone_order_seven_extension.py)
found modular ranks

\[
(243,244),\ (273,274),\ (307,308),\ (342,342)
\]

for the matrix and augmented matrix at source caps \(14,15,16,17\).
These modular computations selected pivots only.  Their rational lifts give
the exact nonzero right-hand-side residuals

\[
-\frac{2835}{32},\qquad
-\frac{315}{32},\qquad
-\frac{55360305}{1024}
\]

at caps \(14,15,16\), respectively.  At cap \(17\), a rational square solve
with 342 pivots replays all 692 original equations.  Therefore the exact
minimum at instantaneous order seven is

\[
\boxed{17}.
\]

Repeating the calculation with primes \(1000003\) and \(1000033\) selected
the same pivots and lifted to the same rational certificates.  The incoming
complete affine family has dimension fourteen.

For the selected cap-seventeen extension, the mixed-orientation logarithmic
degree profiles through order eight are

\[
\deg\Omega^{\rm src}_{1,\ldots,8}
=(5,5,9,11,14,18,22,26)
\]

and

\[
\deg\Omega^{\rm tar}_{1,\ldots,8}
=(2,3,3,3,4,4,5,5).
\]

Both forward-`dexp` round trips pass.  In adapted coordinates
\(V=v,\ G=t-\tfrac32v\), the new source top shell is

\[
\operatorname{top}\Omega^{\rm src}_8
=
\frac{V^{18}G^7}{28311552}
\left(10V,-19G\right).
\]

Unlike the first \(W_m\) shells, this shell is transverse:

\[
d(VG)\!\left(\operatorname{top}\Omega^{\rm src}_8\right)
=-\frac{V^{19}G^8}{3145728}\ne0.
\]

The extension replay itself does not classify the outgoing affine kernel.
The successor
[`gauge_moving_cone_order_seven_kernel_pencil.md`](gauge_moving_cone_order_seven_kernel_pencil.md)
now supplies that classification and the complete-affine order-eight shell.
