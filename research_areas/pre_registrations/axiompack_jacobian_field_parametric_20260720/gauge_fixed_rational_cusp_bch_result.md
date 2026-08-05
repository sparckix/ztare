# Fixed-rational cusp BCH discriminator

**Status:** exact shell algebra and all-order adjacent-shell reduction,
fixed-amplitude and symbolic positive prefixes through order forty-one;
odd-subsequence nonvanishing remains open

## Rational specialization

For

\[
C=4P^3+27Q^2,\qquad
B=-\frac{P^3+9Q^2}{36},
\]

the previously isolated normalization product is

\[
G_{\tau,\mu}
=
\exp(-\tau X_C)\exp(\tau X_{C+\mu B}).
\]

The rational amplitude

\[
\boxed{\mu=144}
\]

is an exact simplifying specialization:

\[
C+144B=-9Q^2.
\]

Thus the second factor is a linear Hamiltonian shear.  This removes the
possibility that the fixed-rational question is difficult only because both
factors contain cubic terms.

For the left velocity,

\[
G'G^{-1}
=144e^{-\tau\operatorname{ad}_C}B.
\]

The shared inverse-dexp recursion therefore computes the BCH logarithm
without enumerating free Lie words separately.

## Exact prefix

Write

\[
\log G_{\tau,144}
=\sum_{n\ge1}\tau^nX_{\Omega_n}.
\]

Through \(n=41\), every maximal ordinary-degree monomial is present, with

\[
\deg\Omega_n=\left\lfloor\frac{n+5}{2}\right\rfloor.
\]

More precisely, the top monomial is

\[
\begin{cases}
P^{(n+5)/2},&n\text{ odd},\\
P^{(n+2)/2}Q,&n\text{ even},
\end{cases}
\]

and all forty-one checked coefficients are negative.  The first terms are

\[
\begin{array}{c|c}
n&\operatorname{top}\Omega_n\\ \hline
1&-4P^3\\
2&-108P^2Q\\
3&-216P^4\\
4&-7776P^3Q\\
5&-\frac{186624}{5}P^5\\
6&-1679616P^4Q.
\end{array}
\]

If \(a_n\) denotes the displayed top coefficient, then the adjacent relation
is all-order:

\[
\boxed{
\frac{a_{2k}}{a_{2k-1}}=9(k+2)
}
\]

In particular, \(a_{2k}\) vanishes if and only if \(a_{2k-1}\) vanishes.
The compressed shell replay checks the identity independently for
\(1\le k\le20\).

To prove it, put

\[
A=-C,\qquad D=-9Q^2
\]

and form the symmetric product

\[
S_\tau
=e^{\tau X_D/2}e^{\tau X_A}e^{\tau X_D/2}.
\]

Its logarithm \(L_\tau\) is odd in \(\tau\).  Since

\[
e^{\tau X_A}e^{\tau X_D}
=e^{-\tau X_D/2}S_\tau e^{\tau X_D/2},
\]

one has, at the Hamiltonian level,

\[
\Omega_\tau
=e^{-\tau\operatorname{ad}_D/2}L_\tau.
\]

At order \(2k-1\), weighted homogeneity and parity make the unique
maximal ordinary-degree monomial \(P^{k+2}\).  Earlier odd coefficients of
\(L_\tau\) have lower ordinary degree, while \(\operatorname{ad}_D\)
preserves ordinary degree because \(D\) is quadratic.  Therefore the
coefficient of \(P^{k+2}\) in \(\Omega_{2k-1}\) equals the corresponding
coefficient in \(L_{2k-1}\).

At order \(2k\), only the first conjugation bracket of that same term can
reach degree \(k+2\).  With the campaign's Hamiltonian bracket convention,

\[
-\frac12\operatorname{ad}_{-9Q^2}(P^{k+2})
=9(k+2)P^{k+1}Q,
\]

which proves the ratio.  Thus the fixed-rational all-order problem reduces
to the odd subsequence.

## Structural checks

Let \(R(P,Q)=(P,-Q)\).  Both Hamiltonians are even in \(Q\), and \(R\) is
anti-symplectic.  Consequently the logarithm has the exact parity routing

\[
\Omega_n(P,-Q)=
\begin{cases}
\Omega_n(P,Q),&n\text{ odd},\\
-\Omega_n(P,Q),&n\text{ even}.
\end{cases}
\]

The parity explains the alternating top-monomial type.  Conjugating the
Lie--Trotter product to

\[
\exp(-9\tau X_{Q^2}/2)
\exp(-\tau X_C)
\exp(-9\tau X_{Q^2}/2)
\]

produces the time-symmetric logarithm used in the adjacent-shell proof.

## Exact evaluated shell algebra

Put

\[
X=P^3,\qquad Y=Q^2,\qquad
H_{r,s}=P^{2r-s+1}Q^{s-r+1}.
\]

Every evaluated Lie word with \(r\) copies of \(X\) and \(s\) copies of
\(Y\) is a scalar multiple of \(H_{r,s}\).  Direct differentiation gives

\[
\boxed{
[H_{r,s},H_{u,w}]
=
\left(
us+3u-wr-2w-3r+2s
\right)H_{r+u,s+w}.
}
\]

This quotient is sufficient for every critical shell.  At odd order
\(2k-1\) the relevant basis element is

\[
H_{k,k-1}=P^{k+2},
\]

and at even order \(2k\) it is

\[
H_{k,k}=P^{k+1}Q.
\]

The deterministic shell replay evaluates the complete inverse-dexp
recursion in this algebra.  It reproduces the direct polynomial calculation
through order twenty and extends the exact fixed-amplitude check through
order forty-one.

## Odd-shell differential recurrence

The shell law also gives an exact all-order reduction of the remaining
question.  For

\[
Z(e,\ell)
=
\log\!\left(
e^{-eY/2}e^{-(X+\ell Y)}e^{-eY/2}
\right),
\]

write \(z_{r,s}(e,\ell)\) for the coefficient of \(H_{r,s}\).  The campaign
coefficient satisfies

\[
a_{2k-1}
=4^k9^{k-1}z_{k,k-1}(1,3).
\]

Varying the outer shear gives

\[
\boxed{
\partial_e Z
=
-\frac{\operatorname{ad}_Z}{2}
\coth\!\left(\frac{\operatorname{ad}_Z}{2}\right)Y,
\qquad
Z(0,\ell)=-(X+\ell Y).
}
\]

Thus the odd problem is triangular in the exact two-index shell algebra,
but it is not scalar: higher-\(Q\) shells can feed the boundary coefficient.
The first boundary polynomials are

\[
\begin{aligned}
-z_{2,1}&=\frac32e,\\
-z_{3,2}&=\frac65e(3e+\ell),\\
-z_{4,3}&=\frac3{35}e
\left(132e^2+102e\ell+25\ell^2\right).
\end{aligned}
\]

A useful sign normalization is

\[
W(e,\ell;P,Q)=-Z(e,\ell;P,iQ).
\]

It obeys

\[
\partial_eW
=-Y+\sum_{m\ge1}
\frac{|B_{2m}|}{(2m)!}\operatorname{ad}_W^{2m}Y.
\]

This removes the Bernoulli sign alternation, but the cone of
coefficientwise-positive Hamiltonians is not invariant under the right-hand
side.  For example, if

\[
W=P^3-mQ^2+cP^4+dPQ^2
\quad(c,d>0),
\]

then

\[
\operatorname{ad}_W^2(Q^2)
=2\left(
16c^2P^6+24cP^5+9P^4
-8cdP^3Q^2
+24cmP^2Q^2+12mPQ^2+3d^2Q^4
\right).
\]

The negative mixed term kills a direct positivity-cone induction.  An
all-order proof must use the cross-order relations satisfied by the actual
solution \(W\), or find the first order at which those relations fail to
protect the boundary shell.

The symbolic shell replay now tests those relations directly.  With
symbolic outer and middle coefficients \(e,\ell\), every exact polynomial

\[
-z_{k,k-1}(e,\ell),\qquad 1\le k\le21,
\]

is nonzero and coefficientwise nonnegative.  More strongly, after the Wick
rotation every odd shell beyond the linear \(Q^2\) term is
coefficientwise nonnegative through logarithmic order forty-one.

This is not termwise Magnus positivity.  At logarithmic order five, the raw
velocity contribution to the boundary shell contains \(-18e\ell\); the
inverse-`dexp` contributions repair it in the completed coefficient.
The weighted-profile compression writes
\[
W_{2k-1}=P^{k+2}F_k(Q^2/P^3).
\]
At \((e,\ell)=(1,3)\), every higher \(F_k\) through \(k=21\) has simple
negative zeros, certified by rational isolating intervals, and consecutive
profiles strictly interlace.  Boundary parts of the complete bivariate even
adjoints at depths \(2,4,6,8\), as well as the first boundary Wronskian,
remain coefficientwise nonnegative through order forty-one.  Since these
adjoints are precisely the objects weighted by positive Bernoulli
coefficients in the \(e\)-differential equation, preservation of the
proper-position profile chain is the current all-order candidate.
All thirty-nine adjacent coefficient minors visible through order
twenty-one are also strictly positive, providing a rational
total-positivity shadow of that chain.
Through \(k=11\), amplitude homogeneity plus coefficient-positive
discriminants and fixed-sign adjacent resultants prove the same negative-root
and interlacing statement uniformly for every \(e,\ell>0\).

## Boundary

This result supplies a rational amplitude with a long exact critical prefix,
an exact evaluated shell algebra, and a triangular differential recurrence.
It does not prove that the odd top coefficients stay nonzero at every order.
The generic-amplitude cascade is therefore not yet promoted to a
fixed-rational all-order theorem, and this result does not determine the
unrestricted contact minimax.

The direct polynomial replay is
[`gauge_fixed_rational_cusp_bch.py`](gauge_fixed_rational_cusp_bch.py).
The compressed order-forty-one replay is
[`gauge_fixed_rational_cusp_shell_recurrence.py`](gauge_fixed_rational_cusp_shell_recurrence.py).
The symbolic boundary replays are
[`gauge_fixed_rational_odd_boundary.py`](gauge_fixed_rational_odd_boundary.py)
and
[`gauge_fixed_rational_odd_boundary_sparse.py`](gauge_fixed_rational_odd_boundary_sparse.py).
The profile/Serre replay is
[`gauge_fixed_rational_profile_cone.py`](gauge_fixed_rational_profile_cone.py).
They use the shared formal Lie-series implementation and make no provider
calls.
