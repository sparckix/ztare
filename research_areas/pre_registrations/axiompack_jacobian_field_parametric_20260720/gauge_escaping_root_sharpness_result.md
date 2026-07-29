# Sharp escaping-root filtration

**Status:** exact all-order theorem for the canonical finite-branch
factorization; deterministic replay and kernel arithmetic certificate pass;
symmetric-contact implication remains open; historical priority unconfirmed

## Theorem

Let \(z\in s\mathbb Q[P,Q][[s]]\) be the unique solution of

\[
z=a(s)+b(s)z^2+c(s)Pz^3+d(s)Qz^4,
\]

where

\[
a=\frac{s}{2(s+2)},\quad
b=\frac{s+4}{2(s+2)},\quad
c=\frac{12}{(s-6)(s+2)},\quad
d=-\frac{s-4}{2(s+2)}.
\]

For the filtration \(\deg_f(P,Q)=(4,6)\),

\[
\boxed{\deg_f[s^n]z=2n-2\qquad(n\ge3).}
\]

Thus the slope-two upper bound used by the finite-branch construction is
sharp at every coefficient of its reciprocal escaping root.

## Associated-graded mechanism

Give \(s^nP^iQ^j\) Rees valuation

\[
\nu=n-2i-3j.
\]

The fixed point has \(\nu(z)=1\).  Put

\[
x=s^2P,\qquad y=s^3Q,\qquad z=sZ(x,y)+
\text{terms of valuation greater than one}.
\]

The \(bz^2\) term has valuation two.  The leading coefficients

\[
[s]a=\frac14,\qquad c(0)=-1,\qquad d(0)=1
\]

therefore give the exact associated-graded equation

\[
\boxed{Z=\frac14-xZ^3+yZ^4.}
\]

This equation has a unique solution in \(\mathbb Q[[x,y]]\).

## Two nonvanishing coefficient families

For odd orders, set \(y=0\) and write \(W=4Z\).  Then

\[
W=1-\frac{x}{16}W^3.
\]

Lagrange inversion gives

\[
[x^k]Z
=
\frac{(-1)^k}{4\cdot16^k(2k+1)}
\binom{3k}{k}\ne0.
\]

This is the coefficient of \(P^k\) in \([s^{2k+1}]z\), and its filtered
degree is

\[
4k=2(2k+1)-2.
\]

For even orders, let \(Z_a\) solve \(Z_a=a-xZ_a^3\).  Differentiating the
two-variable equation at \(y=0\) gives

\[
\left.\partial_yZ\right|_{y=0}
=\frac{Z_{1/4}^4}{1+3xZ_{1/4}^2}
=\left.\frac15\partial_a Z_a^5\right|_{a=1/4}.
\]

Again by Lagrange inversion,

\[
[x^k]\left.\partial_yZ\right|_{y=0}
=
\frac{(-1)^k(2k+5)}{(3k+5)4^{2k+4}}
\binom{3k+5}{k}\ne0.
\]

This is the coefficient of \(P^kQ\) in \([s^{2k+4}]z\), with

\[
4k+6=2(2k+4)-2.
\]

The odd and even families cover every \(n\ge3\), proving the theorem.

## Verification

The updated replay
[`gauge_weierstrass_finite_branch.py`](gauge_weierstrass_finite_branch.py)
checks the fixed-point equation, finite-cubic factorization, both closed
forms, and the sharp coefficients through order nine.  The all-order proof
is the associated-graded reduction and Lagrange-inversion calculation
above; the finite prefix is a regression check.

The Lean source
[`AxiomPackJacobianRootVolumeRectifier.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianRootVolumeRectifier.lean)
encodes both rational coefficient families, proves that every term is
nonzero, and checks the odd/even filtration arithmetic.  The terminal target
is
`AxiomPackJacobianRootVolumeRectifier.escaping_root_sharp_shell_arithmetic_certificate`.
Provider-free LeanMill governance used zero provider calls and closed with:

- closure-record SHA-256
  `f3fe60f7e8bc9e9f6f4dd78e12f31e0ff60fd2b3d066c4dd74f00adf9ff80589`;
- kernel-parity SHA-256
  `beb4a6f6b63ff9ba0b7f68b94e4d281589edb9e9aeafe3684232a40808328677`;
- governed closure SHA-256
  `8e71a986037be5a518175bdd42624c6c4220e5b1085e5d7518e0834f1993e373`;
- matched negated-conclusion control, target identity, statement integrity,
  and axiom allowlist passed.

The governed closure is
[`AxiomPackJacobianRootVolumeRectifier.escaping_root_sharp_shell_arithmetic_certificate_8e71a986037b.lean`](../../../ztare_proofs/closures/AxiomPackJacobianRootVolumeRectifier.escaping_root_sharp_shell_arithmetic_certificate_8e71a986037b.lean).

## Contact-complexity boundary

This theorem is intrinsic to the canonical Weierstrass factorization of the
inverse quartic.  It makes the construction's slope-two mechanism exact,
rather than a loose degree estimate.

It does not yet prove that every compatible source/target contact must carry
the same shell.  A different contact can distribute the escaping sheet
between its two sides.  A symmetric lower bound requires an invariance
theorem for that rank-one factor under coefficientwise-polynomial formal
contact.  Until that bridge is proved, the established campaign envelope is:

\[
\text{one contact has degree }2n+O(1),
\qquad
\text{no contact has a joint uniform degree ceiling}.
\]
