# Complete target image on the exceptional divisor

**Status:** exact all-parameter kill of the source-only divisor cascade;
algebraic endpoint provider-free kernel-ratified; historical priority
unassessed

## Verdict

The Bernoulli--Witt cascade in the source-only connection does not survive
the complete admissible polynomial Hamiltonian target image.

At the seed, that image is exactly

\[
\boxed{
\operatorname{im}\rho_0
=
\left\langle
y\partial_y,\ y^3\partial_y
\right\rangle ,
}
\]

where

\[
\rho_0(K)=
\left.(dF_0)^{-1}(X_K\circ F_0)\right|_{\gamma=0},
\qquad y=2v+3.
\]

For the complete parameter family, a regular Hamiltonian

\[
K_s=a(s)P^3+b(s)PQ
\]

makes the target-relative source connection restrict to the one-dimensional
translation algebra.  Its divisor logarithm consequently has degree zero at
every order.

## Completeness of the seed image

Put \(r=1+v\), \(g=\gamma\), and \(y=2r+1\).  The seed is

\[
P=yg-\frac34(y-1)^2g^2,\qquad
Q=\frac14(y^2-1)g^2-\frac14(y-1)^3g^3,
\]

with

\[
\det\frac{\partial(P,Q)}{\partial(r,g)}=-g^2.
\]

The quotient target-lift ideals for

\[
X_K=(K_Q,-K_P)
\]

say:

- \(K_Q\) has no constant term;
- \(-K_P\) has no constant term;
- \(-K_P\) has no \(P\)-linear term.

Equivalently, the \(Q,P,P^2\) coefficients of \(K\) vanish.  Constants do
not affect \(X_K\).  Under

\[
\operatorname{wt}(P,Q)=(1,2),
\]

every remaining monomial has weight at least three.

Write \(P=gA\) and \(Q=g^2B\).  The adjugate-Jacobian formula shows that a
Hamiltonian monomial of weight \(d\ge3\) has polynomial pullback, with

\[
W_r\in g^{d-3}\mathbb Q[r,g],
\qquad
W_g\in g^{d-2}\mathbb Q[r,g].
\]

Thus every target-lift Hamiltonian descends polynomially and preserves the
ideal \((g)\).  Only weight \(d=3\) can restrict nontrivially to \(g=0\).
The two weight-three monomials give

\[
\begin{aligned}
\rho_0(P^3)&=-6y^3\partial_y,\\
\rho_0(PQ)&=-\frac32(y^3-y)\partial_y.
\end{aligned}
\]

Their coefficient matrix in the basis
\((y^3\partial_y,y\partial_y)\) has determinant \(-9\).  Therefore the
displayed image is exact.  Its kernel consists of constants and
Hamiltonians whose \(P^3\) and \(PQ\) coefficients vanish.  In the
four-dimensional cubic-field space, the cokernel is

\[
\left\langle
\partial_y,\ y^2\partial_y
\right\rangle.
\]

## Independent \(C\)-normal check

The inverse-cubic module has basis

\[
1,\ w,\ w^2
\]

over \(\mathbb Q[P,Q]\), while every target polynomial has the canonical
form

\[
K=A(P,C)+QB(P,C),
\]

where

\[
C=4P^3-P^2-18PQ+27Q^2+4Q.
\]

The three target-lift conditions force

\[
A_P(0,0)=0,\qquad
A_{PP}(0,0)=2A_C(0,0),\qquad
B(0,0)=-4A_C(0,0).
\]

The apparently lower-weight part therefore combines to

\[
A_C(0,0)(C+P^2-4Q)
=A_C(0,0)(4P^3-18PQ+27Q^2).
\]

This recovers the same two weight-three directions and rules out a hidden
direction from a different target presentation.

## Volume and divisor preservation

Every pullback in the image satisfies the full source lift ideals

\[
U\in(v,t),\qquad V\in(t,v^2).
\]

It also preserves the pulled-back area form:

\[
\partial_v(\gamma^2U)+\partial_t(\gamma^2V)=0.
\]

Consequently

\[
W(\gamma)=V-\frac32U\in(\gamma),
\]

so the exceptional divisor is invariant.

There is a category correction here.  The determinant identity gives
preservation of the divisor ideal; it does not give
\(W(\gamma)=0\) away from the divisor.  The two nonzero controls above have
nonzero normal component off \(\gamma=0\).  Pointwise fixing of the
\(\gamma\) coordinate would define a smaller gauge category and would also
exclude the normalized first target Hamiltonian used by the campaign.

## All-parameter target gauge

Let \(V_s\) be the regular source-only connection.  The single control

\[
\widetilde a(s)P^3,\qquad
\widetilde a(s)=
-\frac{192(s^2-3s-8)}
{(s-6)^3(s-4)^2(s+4)^2},
\]

has \(\widetilde a(0)=-1/36\) and reduces the divisor connection to the
affine field

\[
\frac{s(9s^2y-15s^2-144y+160)}
{3(s-4)^2(s+4)^2}\partial_y.
\]

Using the complete two-dimensional image gives the sharper control

\[
\begin{aligned}
a(s)&=
\frac{96(s^2-12s+16)}
{(s-6)^3(s-4)^2(s+4)^2},\\
b(s)&=\frac{2s}{(s-4)(s+4)}.
\end{aligned}
\]

Both coefficients are regular at \(s=0\), with

\[
a(0)=-\frac1{36},\qquad b(0)=0.
\]

The exact identity is

\[
\left.
\left(
V_s
-a(s)(dF_s)^{-1}X_{P^3}(F_s)
-b(s)(dF_s)^{-1}X_{PQ}(F_s)
\right)
\right|_{\gamma=0}
=
\frac{160s}{3(s-4)^2(s+4)^2}\partial_y.
\]

The Hamiltonian \(Q^2\) lies in the divisor kernel for every \(s\).  Hence
the control can also be chosen as

\[
\widehat K_s=a(s)P^3+b(s)PQ-\frac14Q^2.
\]

It obeys

\[
\widehat K_0=-\frac1{36}P^3-\frac14Q^2,
\]

which is exactly the campaign's normalized first target Hamiltonian.  The
corresponding full source connection vanishes at \(s=0\), while its divisor
restriction remains the same translation.  The kill therefore does not
depend on leaving the declared first-order slice.

The two full pullbacks are polynomial in \((v,t)\), satisfy both source lift
ideals, preserve \(\gamma^2\,dv\wedge dt\), and are tangent to
\(\gamma=0\).  The controlled full source field passes the same checks.

Since translation fields commute, the divisor restriction of the Magnus
logarithm is

\[
\left(
\int_0^s
\frac{160u}{3(u-4)^2(u+4)^2}\,du
\right)\partial_y.
\]

Every coefficient has degree zero in \(y\).  The target Hamiltonians
\(\langle P^3,PQ\rangle\) also form a two-dimensional Lie algebra under the
Poisson bracket, so compatibility does not require an expanding target
Hamiltonian vocabulary.

## Consequence and boundary

The source-only even law

\[
\deg(Y_n|_{\gamma=0})=2n-4
\]

remains valid in its declared gauge.  It cannot supply a
gauge-independent lower bound: an admissible regular target gauge changes
the same divisor logarithm into translations.

The surviving campaign residual is the symmetric source/target filtration
away from the divisor and the complete prefix minimax \(c_n\).  This result
does not decide whether the full two-variable source logarithm has
gauge-minimized unbounded degree.

## Replay and kernel governance

The deterministic replay
[`gauge_target_divisor_image.py`](gauge_target_divisor_image.py) checks the
complete seed image, the regular all-parameter controls, polynomial descent,
both source lift ideals, weighted divergence, divisor tangency, and the
normalized \(Q^2\) slice.

The algebraic endpoint
`AxiomPackJacobianDivisorMagnusEscape.divisor_magnus_gauge_kill_terminal_certificate`
passed provider-free LeanMill governance with zero provider calls:

- closure-record SHA-256
  `f37ff2f024aaa49eadbbf248219f5ba0e863211cda7042442faa07de577931a3`;
- kernel-parity SHA-256
  `73991f5339ba33d3d47522a009e7b0311997e85761299dcffe52a3e1652e388d`;
- governed closure SHA-256
  `2919a0cbccd5084cc4066e2db19b4bd9cea5091cc6d485658c67d08b41af85f1`;
- matched negated-conclusion control, target identity, statement integrity,
  and axiom allowlist passed.

The governed closure is
[`AxiomPackJacobianDivisorMagnusEscape.divisor_magnus_gauge_kill_terminal_certificate_2919a0cbccd5.lean`](../../../ztare_proofs/closures/AxiomPackJacobianDivisorMagnusEscape.divisor_magnus_gauge_kill_terminal_certificate_2919a0cbccd5.lean).

## Replay

[`gauge_target_divisor_image.py`](gauge_target_divisor_image.py) checks:

- the inverse-cubic and \(C\)-normal exhaustiveness inputs;
- the seed blow-up formulas and determinant;
- the exact \(P^3,PQ,Q^2\) restriction table;
- polynomial descent;
- both source lift ideals;
- the pulled-back volume identity;
- divisor tangency and failure of pointwise \(\gamma\)-fixing;
- regularity of \(a(s),b(s)\) at the distinguished parameter;
- compatibility with the normalized first-order target slice after adding
  the divisor-kernel Hamiltonian \(-Q^2/4\);
- and the all-parameter translation identity.

The controlled source component hashes are:

- `8338f6cd063d2645f63d7d4c34fb7a0007e422405e19cde564f1651566e9a721`;
- `4c502f7fe1102fc177bb66bf3d871ada5d0e732acf1d76e7991148c7cdebd0e9`.

After adding the fixed-slice term \(-Q^2/4\), they are:

- `600221c5acc9aab34c53fd76c68167263e993d8b43ed5ad455f7a7d9e88f8d39`;
- `540e8b7117ff772043eb5126948c29c13d418aa734e25078595bc84313686f0e`.
