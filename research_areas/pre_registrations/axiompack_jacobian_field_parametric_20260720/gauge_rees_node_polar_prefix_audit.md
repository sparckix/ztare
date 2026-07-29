# Polar-prefix audit of the Rees node obstruction

**Status:** exact adversarial audit; the uniform map-level theorem survives;
the unrestricted tail-limsup transfer needs a polar-prefix normalization
theorem

## Scope

Let

\[
\widetilde F_{\varepsilon,\tau}(V,T)=
\left(
\varepsilon^4F_{\tau\varepsilon^2,P}(V/\varepsilon,T/\varepsilon),
\varepsilon^6F_{\tau\varepsilon^2,Q}(V/\varepsilon,T/\varepsilon)
\right).
\]

Put

\[
G=T-\frac32V,\qquad r=VG.
\]

The special fiber is

\[
f_\tau(r)=
\left(\tau r^3-3r^2,\frac34\tau r^4-2r^3\right).
\]

The node-separation calculation is exact for a target Hamiltonian whose
node evaluation exists and a source action whose Rees specialization is a
regular vector field.  This audit asks whether a finite polar source prefix
can survive the rank-one degeneration and contribute to the normal class.

## The apparent second-layer counterterm cancels

Write

\[
\widetilde F_{\varepsilon,\tau}
=F_0+\varepsilon F_1+\varepsilon^2F_2+\cdots,
\qquad F_0=f_\tau(r).
\]

Exact expansion gives

\[
F_1=a\,f_\tau'(r),\qquad
a=T-\frac12V.
\]

The polynomial vector

\[
k=(-V,T-3V)
\]

generates \(\ker dr\).  Since

\[
k(a)=T-\frac52V,
\]

the constant vector

\[
c=\left(-1,-\frac12\right)
\]

satisfies

\[
dr(c)=-k(a).
\]

Consequently

\[
dF_1(k)+dF_0(c)=0.
\]

If \(F_2\) is inspected in isolation, its normal pairing is nonzero:

\[
\det\!\left(
f_\tau'(r),dF_2(k)
\right)
=
\frac{
9r^2(r^2-V^4)(\tau r-2)^2
}{V^2}.
\]

That expression is not the normal class of a completed polar cascade.
Including the forced coefficient \(c\) gives the exact cancellation

\[
\boxed{
\det\!\left(
f_\tau'(r),dF_2(k)+dF_1(c)
\right)=0.
}
\]

Thus the first-layer calculation cannot be used as a counterexample to the
node theorem.

## Exact six-layer polar source

Let

\[
J_\varepsilon=D_{V,T}\widetilde F_{\varepsilon,\tau}.
\]

The quotient Jacobian identity gives

\[
\boxed{
\det J_\varepsilon
=-\varepsilon^6(G+\varepsilon)^2.
}
\]

Define

\[
w=
\begin{pmatrix}
-V^3G\\[2mm]
-\frac34V^4G^2
\end{pmatrix},
\qquad
U_\varepsilon
=\varepsilon^{-6}\operatorname{adj}(J_\varepsilon)w.
\]

Then the adjugate identity gives, without truncation,

\[
J_\varepsilon U_\varepsilon
=-(G+\varepsilon)^2w.
\]

Its special value is the full boundary parameter motion:

\[
\boxed{
\left.J_\varepsilon U_\varepsilon\right|_{\varepsilon=0}
=
\begin{pmatrix}
r^3\\[1mm]
\frac34r^4
\end{pmatrix}
=\partial_\tau f_\tau(r).
}
\]

This Laurent field is the Rees transform of a coefficientwise-polynomial
source series.  If \(g=t-\frac32v\) and \(DF_s\) is the original source
Jacobian, put

\[
Z_s=
\operatorname{adj}(DF_s)
\begin{pmatrix}
-v^3g\\[1mm]
-\frac34v^4g^2
\end{pmatrix}.
\]

Then

\[
U_\varepsilon
=\varepsilon^3
Z_{\tau\varepsilon^2}(V/\varepsilon,T/\varepsilon).
\]

The two components of \(Z_s\) are polynomial in \((v,t)\), have degree at
most eleven, and have coefficients regular at \(s=0\).  Hence
coefficientwise polynomiality and a bounded tail degree do not imply a
regular source Rees specialization.  A finite high-degree prefix can hide
behind the six vanishing Jacobian layers and reappear as normal boundary
motion.

This particular \(Z_s\) is not, by itself, an admissible contact source
field:

\[
\partial_v(\gamma^2Z_{s,v})
+\partial_t(\gamma^2Z_{s,t})\ne0.
\]

Its principal part is nevertheless the principal part of an exact
admissible field.  Let

\[
V_s=(DF_s)^{-1}\partial_sF_s
\]

be the regular source-only connection already computed for the normalized
family.  It is coefficientwise polynomial, regular at \(s=0\), has source
degree eleven, and satisfies

\[
DF_sV_s=\partial_sF_s,\qquad
\partial_v(\gamma^2V_{s,v})
+\partial_t(\gamma^2V_{s,t})=0.
\]

Under the diagonal scaling, put

\[
\widehat V_\varepsilon
=\varepsilon^3
V_{\tau\varepsilon^2}(V/\varepsilon,T/\varepsilon).
\]

Then

\[
D\widetilde F_{\varepsilon,\tau}\widehat V_\varepsilon
=\partial_\tau\widetilde F_{\varepsilon,\tau}
\]

identically, its scaled weighted divergence is zero, and it has a pole of
order six.  Moreover,

\[
\lim_{\varepsilon\to0}\varepsilon^6\widehat V_\varepsilon
=
\lim_{\varepsilon\to0}\varepsilon^6U_\varepsilon.
\]

Thus the subleading terms of the regular source-only connection repair the
adjugate witness's divergence while retaining its polar principal part.
This is a complete admissible source cascade with target Hamiltonian zero,
and it spans the full node motion.

## Correct theorem boundary

The instantaneous node theorem applies under both conditions:

1. the target Hamiltonian is evaluable at
   \((P,Q)=(-2\tau^{-2},\tau^{-3})\);
2. the complete rescaled source action is regular at \(\varepsilon=0\), so
   its special value lies in the tangent image of \(df_\tau\).

Under those hypotheses the branch separation
\(72\sqrt3/(7\tau^6)\) is a contradiction.  Without the second condition,
the determinant with \(f_\tau'\) does not remove a polar kernel cascade.

The assembled-map statement has a stronger and valid hypothesis.  If

\[
D_n\le2n\quad\text{for every }n,
\qquad
2n-D_n\longrightarrow+\infty,
\]

then the conjugated source and target maps specialize polynomially.  The
target special map has Jacobian one, and its local étaleness cannot send the
two transverse node branches into the unibranch seed cusp.  This proves that
no contact in that global triangular class has an escaping gap.

It does not by itself prove a tail-limsup lower bound for every contact.
A contact with one finite supercritical coefficient satisfies the first arm
of

\[
\exists n:\ D_n>2n
\quad\text{or}\quad
D_n\ge2n-O(1)\ \text{infinitely often},
\]

while that finite coefficient is invisible to a tail limsup.

## Precise surviving normalization statement

To transfer the node obstruction to the unrestricted logarithmic symmetric
slope, one must prove a contact-specific polar-prefix removal theorem.

### Polar-prefix removal

Every compatible logarithmic contact with tail slope \(<2\) is equivalent,
without increasing that tail slope, to a contact whose complete source and
target Rees series have nonnegative valuation and whose source special
action is tangent to \(f_\tau\).

The alternative claim that admissibility annihilates every polar normal
class is false: the exact source-only connection is
weighted-divergence-free, satisfies the complete contact equation, and
maps onto \(\partial_\tau f_\tau\).  Any normalization theorem must quotient
this actual connection while controlling the logarithm of its
path-ordered flow.  Coefficientwise polynomiality, bounded velocity degree,
and the rank-one special fiber do not provide that control.

## Consequences retained

- The diagonal boundary, its two cusps, its node, and the Hamiltonian branch
  separation are exact.
- The étale node-versus-cusp obstruction is valid for globally
  Rees-admissible assembled maps.
- The instantaneous weighted target lower rate is valid when the source
  action has a regular Rees specialization.
- The complete admissible polar source image contains the node normal
  class; node separation cannot prove a tail-limsup bound without a
  normalization theorem.
- Neither result currently proves the unrestricted ordinary logarithmic
  slope two.
