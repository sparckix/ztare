# No locally finite positive-contact continuation of the normalized background

## Claim boundary

Let a coefficientwise-polynomial connection continue the normalized radial
background, and suppose one of its target coefficients has positive
\(C\)-adic valuation.  Then its source Magnus logarithm has an infinite
subsequence of limiting Hamiltonian rate strictly above two, or a strictly
higher source pivot at the same parameter order.

This does not cover a replacement of the contact-zero backbone.  It
therefore narrows the noncanonical staircase problem without deciding the
unrestricted symmetric tail minimax.

## Robust classes

The seed pullback identifies the filtrations:

\[
\nu_z(H(P_0,Q_0))=2\nu_C(H).
\]

At the least contact depth \(m>0\), the first nonzero axial coefficient is
a finite polynomial \(g(r)\).  If its highest degree is \(w\), the robust
odd transfer acts there by

\[
3w+4m,
\]

which is nonzero.  Different contact depths cannot cancel this coefficient.

A current column containing the odd terminal has source-factor offsets
\(t\ge h\ge1\).  Its leading even pivot has strictly positive radial
margin \(t\) and nonnegative total-degree margin \(t-h\).  Finite affine
combinations are triangular at their first nonzero contact/radial symbol,
so either the terminal or a higher same-order source shell survives.

## Exceptional classes

The five exceptional \(d=0\) states have corrected radial offsets

\[
(2,1,1,1,2)
\]

and nonzero primary amplitudes

\[
\begin{array}{c|c}
(a,\ell)&\text{normalized amplitude}\\ \hline
(0,0)&m(81m-46)/256\\
(0,1)&(3m+1)(153m^2+114m+73)/256\\
(0,2)&(3m+2)(153m^2+192m+112)/256\\
(0,3)&3(m+1)(153m^2+270m+169)/256\\
(1,0)&-(m+1)(81m+127)/256.
\end{array}
\]

Their adjoint multiplier

\[
2m\delta_{a,\ell}+2k(S-m)
\]

is positive for \(k\ge0\).  If an exceptional ray is canceled, the
corrected transition equation has no exceptional-to-exceptional
\(d=0\) edge.  Since a nonempty set of cancellation orders has a least
element, the first cancellation enters the robust case.  If there is no
cancellation, the exceptional \(\phi_2\) ray survives.

## Rate

With cone slack

\[
2b=a+3d+3m+\ell,
\]

both the robust and exceptional rays have limiting source Hamiltonian rate

\[
L
=\frac{7a+19d+15m+3\ell-4}{2}.
\]

For \(m\ge1\),

\[
L\ge\frac{11}{2}>2.
\]

## Replays

- [`gauge_positive_contact_locally_finite_obstruction.py`](gauge_positive_contact_locally_finite_obstruction.py)
  checks contact valuation, finite-affine Euler injectivity, pivot margins,
  the corrected exceptional graph, and the rate formula.
- [`gauge_cone_boundary_contact_classes.py`](gauge_cone_boundary_contact_classes.py)
  supplies the fifth-depth exceptional amplitude checks.
- [`AxiomPackJacobianFiniteContactPrefixArithmetic.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianFiniteContactPrefixArithmetic.lean)
  kernel-checks the amplitude positivity, transition exit, nonresonance,
  maximum-contact inequality, and \(L\ge11/2\).

The remaining Vector-B object is an arbitrary noncanonical contact-zero
backbone together with its coupled higher-contact recursion.
