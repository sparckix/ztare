# Root-cover volume rectification

**Status:** candidate all-order construction; algebraic core replayed and
kernel-ratified, paired-flow filtered induction repaired after independent
audit

## Eigenquestion

The finite-branch Weierstrass normalization gives

\[
C_s\circ F_s=F_0\circ S_s
\]

with filtered target coefficients, but \(\det DC_s\ne1\). Its canonical
triangular volume correction has source degrees \(6n+1\). Can volume instead
be corrected inside the finite cubic cover, where the source filtration is
visible?

The construction is killed by any of:

- failure of the proposed root field to descend to the coefficient plane;
- failure of its source lift to be polynomial or to satisfy the lift ideals;
- failure of the divergence right inverse on a polynomial;
- growth above the displayed target or source filtration;
- or failure of the recursive determinant correction to preserve contact.

## The uncorrected normalization is all-order slope two

Write the generic inverse relation as

\[
R_s(W)=W^3-aW^4-bW^2-cPW-dQ.
\]

Let \(z\) be the reciprocal escaping root and put \(r=z/a\). The exact
factorization is

\[
rR_s(W)=(1-zW)D_s(W),\qquad
D_s(W)=W^3+AW^2+BW+C.
\]

After \(U=W+h\), \(h=(A+1)/3\), this becomes

\[
U^3-U^2+P'U-Q'=0.
\]

The seed coordinate recovered from this cubic is

\[
\gamma'=P'-2U+3U^2=D_s'(W)=3W^2+2AW+B.
\]

On the normalized family, direct differentiation of the quartic gives

\[
R_s'(W)=\frac{2\gamma}{s+2}.
\]

Differentiating the factorization at a finite root therefore gives the exact
unit relation

\[
\gamma'=\gamma\theta,\qquad
\theta=
\frac{2r}{(s+2)(1-zW)}.
\]

The fixed-point induction gives

\[
\deg_f [s^n]z\le2n-2,\qquad
\deg_f [s^n]r\le2n.
\]

After pullback to the family, the coefficient of \(s^n\) in \(\theta\) has
ordinary source degree at most \(2n\). Also \(h\in(P,Q)[[s]]\), so

\[
\omega:=\frac{U}{\gamma}
=\frac{W}{\gamma}+\frac{h(P_s,Q_s)}{\gamma}
\]

is coefficientwise polynomial and

\[
\deg [s^n]\omega\le2n+1.
\]

Consequently

\[
1+v'=\frac{U}{\gamma'}=\omega\theta^{-1},
\qquad
t'=\gamma'-1+\frac32v'
\]

are polynomial and obey

\[
\deg [s^n]v',\ \deg [s^n]t'\le2n+1.
\]

Thus \(S_s\) lies in the slope-two source group before volume correction.
The exact replay through order four gives component degrees

\[
(3,3),\quad(3,5),\quad(5,7),\quad(7,9).
\]

## Trace-zero root fields

For the seed cubic

\[
D(W)=W^3-W^2+PW-Q,
\]

consider

\[
f=a+bW+cW^2,\qquad a,b,c\in\mathbb Q[P,Q].
\]

The trace condition

\[
3a+b+(1-2P)c=0
\]

preserves the coefficient of \(W^2\). Reducing \(D'f\) modulo \(D\) gives a
target vector field \(Z=(Z_P,Z_Q)\):

\[
\begin{aligned}
Z_P&=\frac{
6Pb+7Pc-9Qc-2b-2c}{3},\\
Z_Q&=\frac{
2P^2c-Pb-Pc+9Qb+3Qc}{3}.
\end{aligned}
\]

Equivalently,

\[
D'(W)f+Z_PW-Z_Q=0\pmod D.
\]

This is the infinitesimal seed-contact identity.

Put \(d=b+c\). In the seed source coordinates

\[
W=(1+v)\gamma,\qquad
P=\gamma+2W-3W^2,
\]

the lifted field satisfies

\[
\begin{aligned}
Y(\gamma)&=\gamma(2b+cW+c),\\
Y(v)&=
-\frac{3bW+b+6cW^2-cW-2c\gamma+c}{3\gamma}.
\end{aligned}
\]

The only possible numerator on \(\gamma=0\) is \(b(0,0)+c(0,0)\).
Hence the root field has a polynomial equivariant source lift whenever

\[
b+c\in(P,Q).
\]

The resulting \(Y(v)\) lies in \((v,t)\), and
\(Y(t)=Y(\gamma)+\frac32Y(v)\) lies in \((t,v^2)\).

## A filtered polynomial right inverse for divergence

For arbitrary \(b,c\), direct differentiation gives

\[
\begin{aligned}
\operatorname{div}Z={}&
\left(2P-\frac23\right)b_P
+\left(3Q-\frac P3\right)b_Q+5b\\
&+\left(\frac{7P}{3}-3Q-\frac23\right)c_P
+\left(\frac{2P^2}{3}-\frac P3+Q\right)c_Q
+\frac{10}{3}c.
\end{aligned}
\]

Define

\[
\mathcal A=
5+\left(2P-\frac23\right)\partial_P
+\left(3Q-\frac P3\right)\partial_Q.
\]

For a prescribed polynomial \(\delta(P,Q)\), let

\[
q=\mathcal A^{-1}\delta,\qquad q_0=q(0,0),
\]

and choose

\[
b=q+2q_0,\qquad c=-3q_0,\qquad
a=-\frac{b+(1-2P)c}{3}.
\]

Then

\[
b+c=q-q_0\in(P,Q)
\]

and an exact substitution in the divergence formula gives

\[
\operatorname{div}Z=\delta.
\]

The inverse \(\mathcal A^{-1}\) is polynomial and filtration-preserving.
Indeed, write

\[
\mathcal A=
\underbrace{5+2P\partial_P+3Q\partial_Q}_{\mathcal A_0}
+\underbrace{\left(-\frac23\partial_P-\frac P3\partial_Q\right)}_N.
\]

For weights \(\deg_fP=4,\deg_fQ=6\), \(\mathcal A_0\) is diagonal with
nonzero eigenvalue \(5+2i+3j\) on \(P^iQ^j\), while \(N\) strictly lowers
the filtration. Therefore

\[
\mathcal A^{-1}
=\sum_{k\ge0}(-\mathcal A_0^{-1}N)^k\mathcal A_0^{-1}
\]

is a finite sum on every polynomial and does not increase filtered degree.

For the first determinant defect \(\delta=5/12\), this gives

\[
q=\frac1{12},\quad
(a,b,c)=\left(-\frac P6,\frac14,-\frac14\right).
\]

Its induced target field is

\[
\left(-\frac P{12}+\frac{3Q}{4},
-\frac{P^2}{6}+\frac Q2\right),
\]

the root-cover correction that removes the entire first source jet. This
contrasts with the triangular correction \((5P/12,0)\), whose seed lift has
degree seven.

## Source and target bounds

Put \(e=q-q_0\). The selected root field has

\[
b=3q_0+e,\qquad c=-3q_0.
\]

The source formulas simplify to

\[
\begin{aligned}
Y(\gamma)&=\gamma\bigl(3q_0(1-W)+2e\bigr),\\
Y(v)&=
-\frac{e(3W+1)+6q_0P}{3\gamma}.
\end{aligned}
\]

Because \(e\in(P,Q)\), its pullback is divisible by \(\gamma\). If
\(\deg_f\delta\le2n\), then

\[
\deg Y(v),\deg Y(t)\le2n+1.
\]

The induced target components obey

\[
\deg_f Z_P\le2n+4,\qquad
\deg_f Z_Q\le2n+6.
\]

Thus the right inverse simultaneously preserves the target filtration,
source slope two, and both lift ideals.

## Recursive determinant correction

Start with the Weierstrass pair \((C_s,S_s)\). Suppose corrections through
order \(n-1\) have produced a target map \(H^{<n}_s\) with

\[
\det DH^{<n}_s=1+s^n\delta_n+O(s^{n+1}).
\]

The filtered target group gives

\[
\deg_f\delta_n\le2n.
\]

Apply the root-cover construction to \(-\delta_n\).  If the resulting paired
infinitesimal fields are \(Z_n,Y_n\), postcompose by their formal flows

\[
\exp(s^nZ_n),\qquad \exp(s^nY_n).
\]

The seed contact identity

\[
dF_0\,Y_n=Z_n\circ F_0
\]

then integrates exactly to

\[
\exp(s^nZ_n)\circ F_0
=F_0\circ\exp(s^nY_n).
\]

Using bare maps \(\mathrm{id}+s^nZ_n\) and
\(\mathrm{id}+s^nY_n\) would leave an order-\(2n\) contact error; the paired
flows are essential.  Since the new flow is the identity below order \(n\),
its divergence \(-\delta_n\) kills the determinant defect at order \(n\).
Repeating gives compatible formal maps

\[
H_s\circ F_s=F_0\circ\Psi_s,\qquad \det DH_s=1.
\]

The determinant chain gives the corresponding source volume identity.
The target filtration is

\[
\deg_f[s^n](H_P-P)\le2n+4,\qquad
\deg_f[s^n](H_Q-Q)\le2n+6.
\]

It is preserved by composition, inverse, and formal flow.  Its Jacobian
matrix has coefficient bounds

\[
\begin{pmatrix}
2n&2n-2\\
2n+2&2n
\end{pmatrix},
\]

so \([s^n](\det DH-1)\) has filtered degree at most \(2n\), exactly the
domain of the divergence right inverse.

On the source side, the coefficient ideals

\[
Y_v\in(v,t),\qquad Y_t\in(t,v^2)
\]

are preserved by derivations, compositions, and formal flows. Composition
words of coefficient orders \(n_1,\ldots,n_r\) contain \(r-1\) spatial
derivatives, so

\[
\sum_i(2n_i+1)-(r-1)=2\sum_i n_i+1.
\]

Therefore the recursive compositions preserve

\[
\deg[s^n]\Psi_s\le2n+1.
\]

## Candidate theorem and boundary

The repaired filtered-flow induction proves an all-order area-preserving
polynomial contact
for the normalized Jacobian deformation with source coefficient bound

\[
\boxed{\deg[s^n]\Psi_s\le2n+1}.
\]

This is an upper bound in the full admissible gauge. It does not prove that
the gauge-minimized value equals \(2n+1\); the complete finite prefixes are
smaller through the currently closed orders. It also does not establish
historical priority.

The target map is Hamiltonian in the formal sense: the logarithm of a
pronilpotent area-preserving plane map is a divergence-free polynomial
derivation, hence has a polynomial Hamiltonian on the affine plane.

The generic root/contact, divergence, lift-divisibility, first correction,
and filtered arithmetic identities are encoded in
`AxiomPackJacobianRootVolumeRectifier.lean`.  Provider-free LeanMill
ratification closed
`root_volume_rectifier_certificate` with closure-record SHA-256
`8e4831cb1eebd985f71a097619e6c1e274d460e5f0b8cfbea27e8838db167751`
and kernel-parity SHA-256
`d236a65f33d7e0e78621fb17d34c320b0ae5174f931a30300f81a587cef101b6`.
The infinite filtered-flow induction remains a mathematical argument in this
artifact; the closure certificate does not encode a complete formal-power-
series library.
