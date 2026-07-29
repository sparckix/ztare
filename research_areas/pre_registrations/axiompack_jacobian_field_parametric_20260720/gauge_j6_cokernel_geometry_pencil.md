# Geometric identity of the order-six moving-section cokernels

**Status:** preregistered before adapted-chart and boundary-symbol tests

## Eigenquestion

At instantaneous order six, the complete-affine cone system one source
degree below solvability has primitive dual

\[
\lambda_{\rm cone}
=25[v^8t^9]R_P+2[v^9t^8]R_P,
\]

whereas the corresponding parity system has

\[
\lambda_{\rm parity}=[v^9t^9]R_P.
\]

Are these functionals recognizable geometric quotients of the cusp/contact
problem, or only coefficient-row representatives tied to the chosen
\((v,t)\) basis?

## Candidate adapted symbols

Put

\[
V=v,\qquad G=t-\frac32v,
\]

and define the constant directional derivatives

\[
A=\partial_V-\frac32\partial_G,\qquad N=\partial_G.
\]

The coefficient formulas suggest

\[
\lambda_{\rm cone}\ \sim\
A^8N^8(\partial_V+11\partial_G),
\qquad
\lambda_{\rm parity}\ \sim\ A^9N^9.
\]

This factorization must be checked on a generic homogeneous binary form,
including the factorial normalization.

## Discriminating tests

1. **Adapted-coordinate covariance.**  Transform generic degree-seventeen
   and degree-eighteen forms exactly and recover both differential symbols.

2. **Exceptional line.**  The exceptional divisor is
   \(\gamma=1+G=0\).  Test whether either functional is a restriction or a
   finite normal jet intrinsic to that affine line.  Translation by
   \(G\mapsto G+1\) must be retained; its leading direction \(G=0\) is not
   automatically the same object.

3. **Top cusp directions.**  The leading seed depends on \(r=VG\):

   \[
   \overline P=-3r^2,\qquad\overline Q=-2r^3.
   \]

   Compare the projective factors of each dual symbol with the tangent and
   normal axes of \(VG=0\).  A third projective direction would rule out a
   pure cusp-normal or cusp-tangent name.

4. **Weighted source boundary.**  For a homogeneous source field
   \(Z=(a,b)\), impose the leading weighted-divergence equation

   \[
   \partial_V(G^2a)+\partial_G(G^2b)=0
   \]

   and compute \(\lambda(d\overline P(Z))\).  This tests whether the dual is
   the principal source-boundary quotient that becomes available upon
   increasing the source cap.

5. **Coordinate dependence.**  Apply the residual torus
   \(V\mapsto cV,\ G\mapsto c^{-1}G\), which preserves \(VG\).  If the third
   direction moves relative to the cusp axes, only the binary-form orbit,
   not the number \(11\), is geometrically meaningful without the full
   normalized chart.

## Success and kill conditions

- **Named quotient:** the functional factors through one canonical
  restriction, normal jet, tangent jet, or weighted-boundary coordinate.
- **Covariant but not canonical:** its projective binary symbol is exact,
  while a coefficient such as \(11\) changes under residual chart
  automorphisms.
- **Basis artifact:** two admissible changes preserving all declared
  geometry turn it into inequivalent projective root data.

The calculation is finite and local to the \(j=6\) cokernels.  It will not
be extrapolated to \(j\ge7\).

## Exact result

The compact replay is
[`gauge_j6_cokernel_geometry.py`](gauge_j6_cokernel_geometry.py).  On generic
homogeneous binary forms it verifies, including factorials,

\[
\boxed{
\lambda_{\rm cone}
=\frac{2}{8!\,9!}
\left(\partial_V-\frac32\partial_G\right)^8
\partial_G^8
\left(\partial_V+11\partial_G\right)}
\]

at the origin, and

\[
\boxed{
\lambda_{\rm parity}
=\frac{1}{(9!)^2}
\left(\partial_V-\frac32\partial_G\right)^9
\partial_G^9.}
\]

Thus the cone dual is a degree-seventeen projective polar with root
multiplicities \((8,8,1)\); parity is the degree-eighteen balanced polar
with multiplicities \((9,9)\).  Only \(\partial_G\) is one of the two
adapted cusp-axis directions.  The cone's third direction rules out a pure
cusp-tangent or cusp-normal interpretation.

### Exceptional-line kill

Neither functional factors through restriction to
\(\gamma=1+G=0\), nor through any proper normal jet there.  For every
\(k<17\), the replay constructs a degree-seventeen polynomial divisible by
\((G+1)^{k+1}\) whose cone functional is nonzero.  For parity the analogous
statement holds for every \(k<18\).  The simplest cone witness is

\[
G^7V^9(G+1),
\]

which vanishes on the exceptional line but has
\(\lambda_{\rm cone}=2\).

Consequently this cokernel is not an exceptional-divisor residue or a
finite exceptional-line jet.

### Weighted source boundary

Let \(Z=(a,b)\) be homogeneous and impose

\[
\partial_V(G^2a)+\partial_G(G^2b)=0.
\]

For source degree fourteen,
\(\lambda_{\rm cone}(d\overline P(Z))\) is a nonzero linear form in exactly
the first nine free source-symbol coordinates \(a_0,\ldots,a_8\).  For
parity, the corresponding degree-fifteen pullback is likewise nonzero in
the first nine coordinates.  This proves the operational meaning of the
two rows: each detects the first new weighted-divergence-free source
principal symbol that appears when its source cap is raised.

The cone's extra weight-twelve target symbol removes the parity
degree-eighteen balanced polar.  What remains is the degree-seventeen
three-direction polar above, so cone solvability arrives one source degree
earlier.

### Coordinate status and lower-bound status

Under the residual cusp torus

\[
V\mapsto cV,\qquad G\mapsto c^{-1}G,
\]

the numerical slopes of the two nonvertical cone directions rescale, while
their ratio remains

\[
-\frac{22}{3}.
\]

Therefore the integer \(11\) alone is not an invariant.  The projective
root configuration, together with the normalized chart or its residual
torus class, is the covariant datum.

This gives a natural **filtered finite quotient** and recovers the exact
order-six lower bounds

\[
\deg V_6^{\rm cone}\ge14,\qquad
\deg V_6^{\rm parity}\ge15
\]

inside the declared normalized moving-contact categories.  It does not
give a coordinate-free invariant of arbitrary contact presentations, an
exceptional-set obstruction, or an all-order/asymptotic lower bound.  Those
stronger interpretations are killed by the exceptional-jet witnesses and
the third projective direction.
