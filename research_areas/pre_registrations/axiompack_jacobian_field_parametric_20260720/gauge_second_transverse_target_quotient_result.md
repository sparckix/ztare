# Second transverse target quotient

**Status:** exact layer-two obstruction with scalar associated-graded replay
and provider-free kernel ratification of its arithmetic spine; all-order
propagation remains open

## Statement

After the exceptional-divisor and first-transverse target normalizations,
write the source connection in

\[
R=\mathbb Q[[s]][y,g],\qquad
D_f^{(m)}
=g^mf(y)\partial_y-\frac{g^{m+1}f'(y)}{m+3}\partial_g.
\]

For the affine exceptional coordinate

\[
A(s,y)
=-\frac{3s^2y-5s^2-48y}{48},
\]

the complete weight-five target image in layer two is the three-dimensional
odd subspace

\[
\operatorname{span}\{A,A^3,A^5\}.
\]

The normalized family residual does not belong to that image.  Its exact
coefficient matrix has

\[
\operatorname{rank}M=3,\qquad
\operatorname{rank}[M\mid r]=4,
\]

with seed odd minor \(-125/8\).

The rank jump already appears in the seed-linearized augmented system.  One
exact four-row witness is

\[
\begin{pmatrix}
0&0&0&31/96\\
0&0&-5/8&-25/128\\
0&5/2&5/4&55/192\\
-10&-5/2&-5/8&7/128
\end{pmatrix},
\qquad
\det=\frac{3875}{768}\ne0.
\]

Projecting the tangential residual onto the opposite parity gives the
canonical nonzero class

\[
\boxed{
\begin{aligned}
R_2^{\mathrm{even}}(s,A)
={}&
\frac{64s}
{3(s-6)^2(s-4)^2(s+4)^6}\\
&\cdot\Bigl[
(-900s^3+7200s^2-34560s-51840)A^2\\
&\hspace{16mm}
+25s^6-329s^5+880s^4+3212s^3\\
&\hspace{16mm}
-10336s^2-17664s+35712
\Bigr].
\end{aligned}}
\]

In particular,

\[
\boxed{
[s]R_2^{\mathrm{even}}(s,A)
=\frac{31-45A^2}{96}\ne0.}
\]

Thus the first possible secondary obstruction survives: it is not removed
by any regular weight-five Hamiltonian target control preserving the fixed
slice.

Its top coefficient is

\[
[sA^2]R_2^{\mathrm{even}}=-\frac{15}{32},
\]

which agrees independently with \(r_2\) in the already proved
[`gauge_canonical_top_recurrence_result.md`](gauge_canonical_top_recurrence_result.md).
That theorem gives

\[
r_m=-\frac{3^m(m+3)(4m+1)}{216\,2^m}\ne0
\qquad(m\ge2)
\]

for the completed canonical normal form.  The present rank computation
anchors its first nontrivial term to the complete regular target quotient,
but it does not remove the canonical-versus-minimax boundary.

## Parity mechanism

The graded bracket is

\[
[D_f^{(m)},D_h^{(n)}]
=D_{B_{m,n}(f,h)}^{(m+n)},
\]

\[
B_{m,n}(f,h)
=(m+n+3)
\left(\frac{fh'}{n+3}-\frac{hf'}{m+3}\right).
\]

The target image in layer \(m\) has parity \(m+1\) in \(A\); its canonical
complement has parity \(m\).  Derivation reverses parity, so the ambient
parity routing is

\[
\begin{aligned}
[\mathrm{target}_m,\mathrm{target}_n]
&\subseteq\mathrm{target}_{m+n},\\
[\mathrm{target}_m,\mathrm{residue}_n]
&\subseteq\mathrm{residue}_{m+n},\\
[\mathrm{residue}_m,\mathrm{residue}_n]
&\subseteq\mathrm{target}_{m+n}.
\end{aligned}
\]

This is the symmetric-pair pattern behind the next Magnus calculation.
Parity alone does not prove that the finite degree windows are closed under
every mixed bracket, and it does not turn the single layer-two class into an
asymptotic lower bound.

## Replay and implementation boundary

The exact replay is
[`gauge_second_transverse_target_quotient.py`](gauge_second_transverse_target_quotient.py).
It uses the scalar pullback identity

\[
(dF_s)^{-1}X_H(F_s)
=X_{-2H(F_s)}^{\,g^2dy\wedge dg}.
\]

Layer \(m\) therefore depends only on
\([g^{m+3}]H(F_s)\).  Extracting that coefficient before constructing the
field avoids repeated dense inverse-Jacobian cancellation and keeps the
calculation aligned with the associated-graded object being tested.

The replay checks the lower normalized layers, the complete weight-five
image formula, the unit seed minor, the rank jump, the canonical parity
projection, and the displayed seed-linear class.

The arithmetic carrier is
[`AxiomPackJacobianSecondTransverseQuotientArithmetic.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianSecondTransverseQuotientArithmetic.lean).
The first carried proof used `native_decide`; governance rejected its
generated native-code axiom.  Replacing it with a kernel-reduced Laplace
expansion closed provider-free with:

- governed closure SHA-256
  `c9dbbeab907c9c7170f2ed76bcc87ed025cec0e31d2c8d322ac2b9e77a3cf3d7`;
- closure-record SHA-256
  `a04e2cba150dd20553dfd870bafbcc3afde145bca12fd4c17cbe45d13a499238`;
- kernel-parity SHA-256
  `1b8da5ad17a609a1bb0fb55df9d81573db2622db32850318dcab0d59383232b5`;
- zero provider calls, a discriminating negated-conclusion control, and a
  passing axiom allowlist.

The remaining gate is all-order.  One must include the target-exact lower
layers and their mixed brackets, then prove either:

1. a nonzero sequence of canonical opposite-parity Magnus residues; or
2. a finite-degree coupled source/target factorization that absorbs them.

This result alone does not determine \(\sigma_{\rm ct}\).
