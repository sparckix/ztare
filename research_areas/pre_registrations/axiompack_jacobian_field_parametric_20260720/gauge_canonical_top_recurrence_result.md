# Canonical transverse top recurrence

**Status:** exact all-order coefficient law for the completed canonical
weighted target normal form; deterministic symbolic replay passed; symmetric
source/target minimax remains open

## Result

Let \(R_m(A)\) be the opposite-parity representative at transverse layer
\(m\), after all lower layers have been put in the canonical weighted target
normal form, and define

\[
r_m=[sA^m]R_m(A).
\]

Then

\[
\sum_{m\geq 0}r_mu^m
=
\frac{18u^4-72u^3+99u^2-57u+10}
     {6(2-3u)^3}.
\]

In particular,

\[
r_0=\frac5{24},\qquad r_1=-\frac14,
\]

and, for every \(m\geq2\),

\[
\boxed{
r_m
=-\frac{3^m(m+3)(4m+1)}{216\,2^m}
\neq0.
}
\]

Equivalently,

\[
8r_{m+3}-36r_{m+2}+54r_{m+1}-27r_m=0
\qquad(m\geq2).
\]

The repeated characteristic root is \(3/2\).  The exceptional denominator
\(2-3u\) therefore explains both the recurrence and the
\(m^2(3/2)^m\) coefficient growth.

This proves that the observed residual degrees \(0,1,2\) continue as
\(0,1,2,\ldots\) in this canonical completed normal form.  It does not turn
that canonical statistic into a symmetric minimax invariant.

## Seed Hamiltonian

At \(s=0\), in the canonical exceptional coordinates \((A,g)\),

\[
\begin{aligned}
P_0&=gA-\frac34g^2(A-1)^2,\\
Q_0&=\frac14g^2(A^2-1)-\frac14g^3(A-1)^3,
\end{aligned}
\]

and

\[
\det d(P_0,Q_0)=-\frac{g^2}{2}.
\]

Subtract the fixed first target Hamiltonian

\[
K_0=-\frac{P^3}{36}-\frac{Q^2}{4}.
\]

The remaining connection vanishes at \(s=0\).  Its parameter-linear
tangential component is

\[
f^{(1)}(A,g)=\sum_{m=0}^{4}g^mf_m(A),
\]

where

\[
\begin{aligned}
f_0&=\frac{7A^3-9A+10}{48},\\
f_1&=-\frac{(A-1)^2(7A^2-3)}{16},\\
f_2&=\frac{(A-1)^3(78A^2-81A-17)}{192},\\
f_3&=-\frac{(A-1)^5(7A-10)}{64},\\
f_4&=-\frac{3(A-1)^7}{256}.
\end{aligned}
\]

The normal component is forced by

\[
[g^{m+1}]\,V_g^{(1)}=-\frac{f_m'}{m+3}.
\]

Consequently the scalar source Hamiltonian is explicitly

\[
\boxed{
\Phi_1(A,g)
=-\sum_{m=0}^{4}\frac{g^{m+3}}{2(m+3)}f_m(A),
}
\]

with

\[
V_A^{(1)}=-\frac2{g^2}\partial_g\Phi_1,
\qquad
V_g^{(1)}=\frac2{g^2}\partial_A\Phi_1.
\]

The replay derives these expressions from the full parameter family rather
than taking them as inputs.

## Inverse-cubic check

Put

\[
W=\frac{A-1}{2}g.
\]

Then

\[
P_0=g+2W-3W^2,\qquad
Q_0=gW+W^2-2W^3,
\]

and eliminating \(g\) gives

\[
\boxed{W^3-W^2+PW-Q=0.}
\]

After substituting \(g=P-2W+3W^2\) and reducing \(\Phi_1\) modulo this
cubic, the remainder is

\[
a(P,Q)+b(P,Q)W+c(P,Q)W^2,
\]

where

\[
\begin{aligned}
a={}&-\frac{
70P^3-480P^2Q-51PQ+1770Q^2-4Q
}{2520},\\
b={}&-\frac{
480P^3-159P^2-2070PQ+4P-1215Q^2+696Q
}{2520},\\
c={}&-\frac{
135P^2+1485PQ-12P-684Q-4
}{2520}.
\end{aligned}
\]

Let \(W'\) be the other small root and let \(R\) be the root near one.  With

\[
\Delta=(1-3W)^2-4g,
\]

\[
W'=\frac{1-W-\sqrt\Delta}{2},
\qquad
R=\frac{1-W+\sqrt\Delta}{2}.
\]

Thus the branch exchange \(W\leftrightarrow W'\) has anti-trace

\[
\frac{\Phi_1(W)-\Phi_1(W')}{2}
=\frac{W-W'}2\bigl(b+c(W+W')\bigr).
\]

In the defect scaling

\[
A=\frac ug,\qquad W=\frac{u-g}{2},
\]

the exact first coefficients are

\[
\begin{aligned}
W-W'&=\frac{2}{3u-2}g+O(g^2),\\
W+W'&=
u-\frac{3u}{3u-2}g
-\frac{2(9u-2)}{(3u-2)^3}g^2+O(g^3),
\end{aligned}
\]

and direct substitution gives

\[
b+c(W+W')
=
\frac{9u^3-36u^2+39u-10}{72(3u-2)}g^2
+O(g^3).
\]

The branch calculation therefore predicts the defect-three Hamiltonian
shell

\[
C(u)
=
\frac{9u^3-36u^2+39u-10}
     {72(3u-2)^2}.
\]

Because branch trace and canonical source-coordinate parity are different
normal forms below the top shell, this calculation is retained as an
independent check.  The next section derives the same \(C(u)\) directly in
the canonical normal form.

## Direct canonical derivation

The simultaneous sign involution

\[
\iota(A,g)=(-A,-g)
\]

fixes \(u=gA\).  A Hamiltonian monomial \(g^dA^k\) has defect
\(\delta=d-k\).  At layer \(m\), \(d=m+3\), while the canonical residual has
\(k\equiv m\pmod2\).  Hence every canonical residual Hamiltonian monomial
has odd defect:

\[
\delta\equiv(m+3)-m\equiv1\pmod2.
\]

Under \(A=u/g\), write the seed target map as

\[
\begin{aligned}
P_0&=p(u)+\frac32ug-\frac34g^2,\\
Q_0&=q(u)+\frac34u^2g
     -\left(\frac14+\frac34u\right)g^2
     +\frac14g^3,
\end{aligned}
\]

where

\[
p(u)=u-\frac34u^2,\qquad
q(u)=\frac14u^2-\frac14u^3.
\]

Since \(p'(0)=1\), the pair
\(\xi=p^{-1}(P)\), \(N=Q-q(\xi)\) is a complete formal target-coordinate
system near the seed cusp.

Choose the cusp coordinate

\[
\xi
=u+\alpha_1g+\alpha_2g^2+\alpha_3g^3+O(g^4)
\]

so that \(p(\xi)=P_0\).  Exact coefficient comparison gives

\[
\begin{aligned}
\alpha_1&=-\frac{3u}{3u-2},\\
\alpha_2&=-\frac{6(3u-1)}{(3u-2)^3},\\
\alpha_3&=-\frac{54u(3u-1)}{(3u-2)^5}.
\end{aligned}
\]

The transverse coordinate

\[
N=Q_0-q(\xi)
\]

starts two defects later:

\[
N
=\frac{g^2}{2(3u-2)}
 +\frac{9u-4}{2(3u-2)^3}g^3
 +O(g^4).
\]

Expand the source Hamiltonian in defect:

\[
\Phi_1(u/g,g)
=\phi_0(u)+g\phi_1(u)+g^2\phi_2(u)+g^3\phi_3(u)+\cdots.
\]

The coefficients needed for defect three are

\[
\begin{aligned}
\phi_0={}&
\frac{
u^3(135u^4+1470u^3-6552u^2+8820u-3920)
}{161280},\\
\phi_2={}&
\frac{
u(27u^4+240u^3-368u^2+48u+48)
}{1536},\\
\phi_3={}&
-\frac{
135u^4+1020u^3-648u^2-216u+160
}{4608}.
\end{aligned}
\]

Through defect three, any target Hamiltonian has the complete local form

\[
H(P,Q)=H_0(\xi)+N H_1(\xi)+O(N^2).
\]

Odd-defect residual parity forces the even defects zero and two to match.
Thus

\[
H_0=\phi_0
\]

and the defect-two equation uniquely gives

\[
H_1(u)
=
\frac{u(9u^3-64u^2+108u-48)}{384}.
\]

Substitution through \(g^3\) yields

\[
[g^3]\,H(P_0,Q_0)
=
-\frac{
u(405u^5+2520u^4-5844u^3+3496u^2-288u-96)
}{1536(3u-2)^2}.
\]

Subtracting this from \(\phi_3\) gives

\[
\boxed{
C(u)
=
\frac{9u^3-36u^2+39u-10}
     {72(3u-2)^2}.
}
\]

This calculation is complete at defect three because \(N=O(g^2)\), hence

\[
N^2=O(g^4).
\]

No higher normal coefficient of the target Hamiltonian enters the
\(g^3\) equation.

## A killed shortcut

It is false that each source-coordinate correction of defect at least four
is individually unable to feed defect three.  Define

\[
\overline G
=\frac{Q_0-P_0^2/4}{g^2}
=-\frac14+gC_3+g^2C_4,
\]

where

\[
C_3=\frac{(A-1)^2(A+2)}8,
\qquad
C_4=-\frac9{64}(A-1)^4.
\]

The first constant-cleaning correction between the trace and canonical
gauges is proportional to

\[
\frac56(Q-P^2/4)^2.
\]

After removing its leading \(g^4\), the \(g^2A^3\) coefficient is

\[
\boxed{
[g^2A^3]\,\frac56\overline G^2=-\frac{35}{192}.
}
\]

At total weight six this is a defect-three term.  Therefore the recurrence
cannot be justified by termwise defect preservation.  The adapted
\((\xi,N)\) calculation above incorporates the full triangular
cancellations and is the proof used here.

## From Hamiltonian shell to vector-field recurrence

For a defect-three Hamiltonian shell \(g^3C(gA)\), differentiation at fixed
\(A\) gives

\[
-\frac2{g^2}\partial_g\bigl(g^3C(gA)\bigr)
=-2(3C(u)+uC'(u)).
\]

Therefore

\[
\begin{aligned}
\sum_{m\ge0}r_mu^m
&=-2(3C+uC')\\
&=
\frac{18u^4-72u^3+99u^2-57u+10}
     {6(2-3u)^3}.
\end{aligned}
\]

The partial-fraction identity

\[
\begin{aligned}
\sum_{m\ge0}r_mu^m
={}&-\frac u9+\frac29
+\frac1{18(2-3u)}
-\frac1{54(2-3u)^2}
-\frac8{27(2-3u)^3}
\end{aligned}
\]

gives the displayed closed coefficient formula for every \(m\ge2\).

The replayed prefix is

\[
\frac5{24},-\frac14,-\frac{15}{32},-\frac{39}{32},
-\frac{357}{128},-\frac{189}{32},-\frac{6075}{512},
-\frac{11745}{512},\ldots
\]

and agrees with the independent recursive computation.

## Polynomial-category consequence

The \(s\)-linear source connection before canonical minimization is a
polynomial of \(g\)-degree four.  The pullback of each individual polynomial
target Hamiltonian also has finite \(g\)-support.  If only finitely many
target weights had a nonzero coefficient of \(s\), the fully normalized
\(s\)-linear residual would therefore have finite \(g\)-support.

But \(r_m\neq0\) for every \(m\ge2\).  Hence infinitely many target weights
have a nonzero \(s\)-linear coefficient.  The inverse-limit normalization is
not an element of

\[
\mathbb Q[P,Q][[s]],
\]

where each coefficient of \(s\) must be a polynomial.  It is admitted only
after target-adic completion.  Every finite transverse quotient remains a
valid polynomial calculation.

## Claim boundary

This result proves an all-order law for the completed **canonical weighted
normal form**.  It does not prove that every source/target decomposition has
unbounded degree.  A bounded noncanonical representative may retain terms
that the greedy target projection removes.  The symmetric contact slope
\(\sigma_{\rm ct}\) and the associated minimax obstruction remain separate
questions.

The exact replay is
[`gauge_canonical_top_recurrence.py`](gauge_canonical_top_recurrence.py).
It derives the seed family, source Hamiltonian, cubic remainder, branch
check, canonical cusp-coordinate shell, killed shortcut, rational generating
function, recurrence, and first twelve coefficients.

## Kernel ratification

The Lean source
[`AxiomPackJacobianDivisorMagnusEscape.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianDivisorMagnusEscape.lean)
encodes the coefficient family, proves every term is nonzero, verifies its
third-order recurrence, checks the rational generating function, and
certifies that lower-layer brackets miss the top degree.  The terminal
target is
`AxiomPackJacobianDivisorMagnusEscape.canonical_top_shell_arithmetic_terminal_certificate`.
Provider-free LeanMill governance used zero provider calls and closed with:

- closure-record SHA-256
  `8423396455ad99c2ac012e7fcbc005d2603c2920ed8a55f8d89021905e4f4911`;
- kernel-parity SHA-256
  `f078dfdd9e62c6e324c3aeb066fda8cea3b70bd053474a18d5b5538e039fa59b`;
- governed closure SHA-256
  `8c41309f50c3d7f345a14d320812daa58bb6e540a983ed92956ba451ce3580f3`;
- matched negated-conclusion control, target identity, statement integrity,
  and axiom allowlist passed.

The governed closure is
[`AxiomPackJacobianDivisorMagnusEscape.canonical_top_shell_arithmetic_terminal_certificate_8c41309f50c3.lean`](../../../ztare_proofs/closures/AxiomPackJacobianDivisorMagnusEscape.canonical_top_shell_arithmetic_terminal_certificate_8c41309f50c3.lean).
