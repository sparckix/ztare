# Admissible polar image at the Rees node

**Status:** exact replay resolves the node class; positive-layer contact is
the regular source-only connection

## Eigenquestion

For the scaled family

\[
\widetilde F_{\varepsilon,\tau}(V,T),\qquad
\det D\widetilde F_{\varepsilon,\tau}
=-\varepsilon^6(G+\varepsilon)^2,
\quad
G=T-\frac32V,
\]

does the order-zero normal image of all finite polar source/target cascades
contain the node-separation class

\[
h_\tau(r)=-\frac14r^6+\frac{3\tau}{28}r^7,
\qquad r=VG?
\]

The cascade must satisfy the full infinitesimal admissibility equations:

- source weighted divergence zero;
- target Hamiltonian and coefficientwise polynomial;
- the complete contact equation, including every negative Laurent layer.

## Potential form of the contact equation

Put

\[
\rho_\varepsilon=(G+\varepsilon)^2.
\]

A weighted-divergence-free source field has local Hamiltonian form

\[
U_\varepsilon
=
\frac1{\rho_\varepsilon}
\left(\partial_TL_\varepsilon,-\partial_VL_\varepsilon\right).
\]

For a target Hamiltonian \(K_\varepsilon\), the contact equation

\[
\partial_\tau\widetilde F
=X_{K_\varepsilon}(\widetilde F)
+D\widetilde F\,U_\varepsilon
\]

has scalar primitive

\[
S_\varepsilon
=K_\varepsilon(\widetilde F)
-\varepsilon^6L_\varepsilon+c(\varepsilon,\tau),
\]

where

\[
dS_\varepsilon
=-\det(D\widetilde F\,d(V,T),\partial_\tau\widetilde F).
\]

On the special fiber, \(S_0=h_\tau(r)\).

## Leading polar source image

Let

\[
\ell_\varepsilon=\varepsilon^6L_\varepsilon.
\]

Polynomiality of \(U_\varepsilon\) is equivalent to

\[
\partial_V\ell_\varepsilon,
\partial_T\ell_\varepsilon
\in(\rho_\varepsilon).
\]

In the coordinates \((V,G)\), every polynomial

\[
\ell_\varepsilon=c+(G+\varepsilon)^3M_\varepsilon(V,G)
\]

satisfies these two divisibilities.  Conversely, at the leading
\(\varepsilon\)-layer, the simultaneous divisibility of both partial
derivatives by \(G^2\) forces

\[
\ell_0\in\mathbf Q+G^3\mathbf Q[V,G].
\]

The required node primitive belongs to this image:

\[
h_\tau(VG)
=G^6\left(
-\frac14V^6+\frac{3\tau}{28}V^7G
\right).
\]

Choose

\[
\boxed{
\ell_\varepsilon
=-
(G+\varepsilon)^3
\frac{h_\tau(VG)}{G^3}.
}
\]

Then \(\ell_0=-h_\tau(r)\), so the source term contributes exactly the
opposite branch separation:

\[
\ell_0(r_+)-\ell_0(r_-)
=-\frac{72\sqrt3}{7\tau^6}.
\]

Thus the node class vanishes in the associated-graded quotient by
weighted-divergence-free pole-six source fields.

## Remaining discriminators

1. Divide both derivatives of \(\ell_\varepsilon\) by
   \((G+\varepsilon)^2\) and replay weighted divergence exactly.
2. Apply the exact scaled Jacobian and take the special fiber.  Its normal
   pairing must equal that of \(\partial_\tau f_\tau\).
3. Test whether their difference is a polynomial multiple of
   \(f_\tau'(r)\).  Failure is a boundary completion obstruction; success
   gives a complete order-zero polar boundary contact.
4. Even after boundary completion, lifting the construction through all
   positive \(\varepsilon\)-layers and back to the allowed \(s\)-Rees
   lattice remains necessary for an all-order contact.

## Claim boundary

If the first three checks pass, the diagonal node cannot furnish a lower
bound for the unrestricted tail-limsup logarithmic slope: its normal class
is paid by an admissible finite polar source prefix.  This would not yet
construct a slope-below-two contact; the positive-layer recursion and
logarithmic integration would remain.

If the normal check fails, the scalar-potential sign or the assumed source
Hamiltonian convention is wrong.  If only the tangent quotient fails, the
surviving obstruction is a polynomial source-tangent divisibility class,
not node branch separation.

## Exact resolution

The existing regular source-only connection supplies the completed cascade:

\[
V_s=(DF_s)^{-1}\partial_sF_s.
\]

It is polynomial in the source coordinates, regular at \(s=0\), has degree
eleven, and obeys

\[
DF_sV_s=\partial_sF_s,\qquad
\operatorname{div}(\gamma^2V_s)=0.
\]

After diagonal scaling,

\[
\widehat V_\varepsilon
=\varepsilon^3
V_{\tau\varepsilon^2}(V/\varepsilon,T/\varepsilon)
\]

has pole order six and satisfies the scaled contact equation with target
Hamiltonian zero:

\[
D\widetilde F_{\varepsilon,\tau}\widehat V_\varepsilon
=\partial_\tau\widetilde F_{\varepsilon,\tau}.
\]

Its principal part is

\[
\boxed{
\widehat V_{-6}
=
\frac34V^5G^3(\tau r-2)\,
(-V,T-3V).
}
\]

It lies in \(\ker dr\), and

\[
\operatorname{div}(G^2\widehat V_{-6})=0
\]

because

\[
G^2\frac34V^5G^3(\tau r-2)
=\frac34r^5(\tau r-2)
=-h_\tau'(r).
\]

The principal part agrees exactly with the adjugate pole-six witness.  The
subleading terms of \(V_s\) repair the latter's weighted divergence and
complete every Laurent layer.  Therefore the admissible polar normal image
contains the full deformation class \(\partial_\tau f_\tau\); in the
one-dimensional normal quotient relevant to node separation, it is
surjective.

This kills the proposed polar-cascade annihilation theorem.  The surviving
problem is logarithmic: determine whether the path-ordered source-only flow,
or any contact obtained after quotienting its finite polar prefix, can have
ordinary symmetric logarithmic tail slope below two.
