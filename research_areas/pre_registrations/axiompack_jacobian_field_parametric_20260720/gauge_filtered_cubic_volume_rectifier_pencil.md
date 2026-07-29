# Filtered inverse-cubic volume rectifier

**Status:** exact all-order filtered volume-preserving cubic contact after
paired-flow repair; algebraic core replayed

## Eigenquestion

Let the Weierstrass finite factor have already been put in trace-one cubic
form.  Its target map has the shifted bounds

\[
\deg_f P_n\leq 2n+4,\qquad \deg_f Q_n\leq 2n+6,
\]

but its determinant need not be one.  Can the determinant be corrected
without introducing a source coefficient above \(2n+1\)?

The triangular target-density primitive fails this test at order one.  The
right control space is instead the two-dimensional trace-zero part of the
rank-three inverse-cubic algebra.

## The seed cubic and its two controls

Work over

\[
\mathcal B=\mathbb Q[P,Q,W]/(W^3-W^2+PW-Q).
\]

Its trace satisfies

\[
\operatorname{tr}(1)=3,\qquad
\operatorname{tr}(W)=1,\qquad
\operatorname{tr}(W^2)=1-2P.
\]

For \(b,c\in\mathbb Q[P,Q]\), put

\[
\delta U=a+bW+cW^2,\qquad
a=-\frac{b+(1-2P)c}{3}.
\]

Then \(\operatorname{tr}(\delta U)=0\).  If \(U=W+\epsilon\delta U\),
the characteristic polynomial of \(U\) remains

\[
U^3-U^2+(P+\epsilon\delta P)U-(Q+\epsilon\delta Q)
\]

to first order.  Reduction modulo the seed cubic gives

\[
\begin{aligned}
\delta P&=bE_1^P+cE_2^P,\\
\delta Q&=bE_1^Q+cE_2^Q,
\end{aligned}
\]

where

\[
\begin{aligned}
E_1&=\frac{6P-2}{3}\partial_P
     \frac{9Q-P}{3}\partial_Q,\\
E_2&=\frac{7P-9Q-2}{3}\partial_P
     \frac{2P^2-P+3Q}{3}\partial_Q.
\end{aligned}
\]

The target divergence of this correction is

\[
\mathcal L(b,c)
=E_1(b)+5b+E_2(c)+\frac{10}{3}c.
\]

The affine lift boundary is exactly

\[
b(0,0)+c(0,0)=0.
\]

It makes \(\delta P(0,0)=0\), removes the forbidden \(P\)-linear term
from \(\delta Q\), and cancels the apparent source pole along
\(\gamma=0\).

## Explicit filtered right inverse

The first control has a diagonal normal form.  Set

\[
p=P-\frac13,\qquad
r=Q-\frac P3+\frac{2}{27}.
\]

Then

\[
E_1=2p\partial_p+3r\partial_r.
\]

Consequently \(T=E_1+5\) is invertible on the whole polynomial ring:
if

\[
d=\sum_{i,j}d_{ij}p^ir^j,
\]

then

\[
T^{-1}d=
\sum_{i,j}\frac{d_{ij}}{2i+3j+5}p^ir^j.
\]

For a prescribed divergence \(d\), define

\[
u=T^{-1}d,\qquad k=u(0,0),\qquad
b=u+2k,\qquad c=-3k.
\]

Here \(k\) is evaluation at the original target origin
\((P,Q)=(0,0)\), which is \((p,r)=(-1/3,2/27)\) in the diagonal
coordinates.

Now \(b(0,0)+c(0,0)=0\), and

\[
\begin{aligned}
\mathcal L(b,c)
&=T(u+2k)+\frac{10}{3}(-3k)\\
&=d.
\end{aligned}
\]

This is an exact right inverse, not a finite-rank observation.

Give \(P,Q,W\) filtered degrees \(4,6,2\).  The coordinate change
\((P,Q)\leftrightarrow(p,r)\) does not increase filtered degree.  Therefore

\[
\deg_f d\leq2n
\quad\Longrightarrow\quad
\deg_f b\leq2n,\qquad c\in\mathbb Q,
\]

and hence

\[
\deg_f\delta U\leq2n+2,
\]

\[
\deg_f\delta P\leq2n+4,\qquad
\deg_f\delta Q\leq2n+6.
\]

## Sharp source bound

On the affine seed cover, write

\[
W=\gamma(1+v),
\]

\[
P_0=\gamma+2W-3W^2,\qquad
Q_0=\gamma W+W^2-2W^3.
\]

The source lift of \(E_1\) has a simple \(\gamma\)-pole:

\[
Z_1^v=-\frac{3\gamma v+3\gamma+1}{3\gamma}.
\]

The \(t\)-component has the same pole order and numerator degree two.
The paired generator \(E_1-E_2\) is polynomial and has source degree
three.

Decompose the right-inverse correction as

\[
bE_1+cE_2=(u-k)E_1+3k(E_1-E_2).
\]

Since \(u-k\) vanishes at \((P,Q)=(0,0)\), its pullback is divisible by
\(\gamma\): \(P_0\in(\gamma)\) and \(Q_0\in(\gamma^2)\).  If a target
monomial has filtered degree \(m\), division by this \(\gamma\) lowers its
ordinary source degree by one, while the numerator of \(Z_1\) adds two.
Thus its source lift has degree at most \(m+1\).  The paired constant term
has degree three.  For the order-\(n\) correction,

\[
\deg \delta V_n,\ \deg \delta T_n
\leq\max(2n+1,3)=2n+1.
\]

This proves that volume rectification itself preserves the desired source
slope.

## Nonlinear induction

Let \(U^{(<n)}\) be a trace-one element of the deformed rank-three cubic
algebra, with induced target map \(H^{(<n)}\), and suppose

\[
\det DH^{(<n)}=1\pmod {s^n}.
\]

The order-\(n\) defect

\[
\epsilon_n=[s^n](\det DH^{(<n)}-1)
\]

has filtered degree at most \(2n\).  This follows termwise from the shifted
target bounds: every product in the determinant loses total filtered
degree ten under one \(P\)- and one \(Q\)-derivative.

Apply the displayed right inverse to \(d=-\epsilon_n\).  Let \(Z_n,Y_n\)
be the resulting paired target/root fields and postcompose by

\[
\exp(s^nZ_n),\qquad \exp(s^nY_n).
\]

At the order-\(n\) characteristic-element level, the flow has linear term

\[
U^{(<n)}\longmapsto U^{(<n)}+s^n\delta U_n.
\]

Only the seed trace and seed characteristic polynomial enter at this
order.  Therefore trace one is preserved, the induced target coefficient
changes by \((\delta P_n,\delta Q_n)\), and its determinant defect changes
by \(\mathcal L(b_n,c_n)=-\epsilon_n\).  The target filtration, affine lift
boundary, polynomial source lift, and \(2n+1\) source increment bound are
all preserved.

The flows, rather than the bare maps
\(\mathrm{id}+s^nZ_n,\mathrm{id}+s^nY_n\), preserve contact at every higher
order.  The latter pair agrees only through order \(n\) and leaves a possible
order-\(2n\) error.

Induction constructs an area-preserving trace-one cubic normalization at
every order.  Once the uncorrected source bound is supplied, every
rectifying increment stays in the same \(2n+1\) envelope.

## The uncorrected source bound

The missing premise follows directly from differentiating the exact
Weierstrass factorization.  Let \(W_s=(1+\mu_s v)\gamma\) be the inverse
root on the normalized family, and let

\[
U_s=W_s+h_s(P_s,Q_s),\qquad h_s=\frac{A_s+1}{3}
\]

be the affine trace normalization.  If

\[
\Gamma_s=P'_s-2U_s+3U_s^2,
\]

then \(\Gamma_s\) is the derivative of the normalized seed cubic at
\(U_s\).

The factorization

\[
\frac{z}{a}R_s(W)
=(1-zW)D_s(W)
\]

and the exact family identity

\[
R_s'(W_s)=\frac{2\gamma}{s+2}
\]

give, after differentiation at the root,

\[
\Gamma_s=\gamma\theta_s,\qquad
\theta_s=
\frac{2(z/a)}{(s+2)(1-zW_s)}
=\frac{4z}{s(1-zW_s)}.
\]

The fixed-point estimate

\[
\deg_f[s^n]z\leq2n-2
\]

implies, after the shift by \(1/s\), pullback to the family, and inversion
of the unit \(1-zW_s\),

\[
\deg[s^n]\theta_s\leq2n,\qquad
\deg[s^n]\theta_s^{-1}\leq2n.
\]

The affine shift has no target-constant term.  Indeed, at \(P=Q=0\), the
fixed-point equation has the unique small solution \(z=a/b\), because
\(a+b=1\).  Hence \(A=-1\) there and

\[
h_s\in(P,Q)\mathbb Q[P,Q][[s]].
\]

The family itself satisfies

\[
P_s\in(\gamma),\qquad Q_s\in(\gamma^2),
\]

and its coefficient pullback raises ordinary degree by at most twice the
additional parameter order.  Combining this with
\(\deg_f h_n\leq2n+2\) shows that

\[
\omega_s=\frac{W_s+h_s(P_s,Q_s)}{\gamma}
\]

is a polynomial series with

\[
\deg[s^n]\omega_s\leq2n+1.
\]

The induced uncorrected source coordinates now have the exact formulas

\[
V_s+1=\frac{U_s}{\Gamma_s}
=\omega_s\theta_s^{-1},
\qquad
T_s=\Gamma_s-1+\frac32V_s.
\]

Therefore

\[
\deg V_n,\ \deg T_n\leq2n+1
\]

at every order.  Polynomiality and the degree bound come from the
exceptional factor \(\gamma\) and the escaping-sheet unit
\(\theta_s\), rather than from extrapolating the computed prefix.

Together with the trace-zero rectifier induction, this proves the same
all-order bound for the volume-preserving contact.

## First coefficient

The uncorrected cubic target coefficient is

\[
C_1(P,Q)=
\left(\frac{P-3Q}{12},\frac{P^2-6Q}{12}\right),
\]

with determinant defect \(-5/12\).  For \(d=5/12\), the right inverse gives

\[
u=\frac1{12},\qquad b=\frac14,\qquad c=-\frac14.
\]

The correction is

\[
\delta C_1=
\left(\frac{-P+9Q}{12},
\frac Q2-\frac{P^2}{6}\right).
\]

Therefore

\[
H_1=C_1+\delta C_1
=\left(\frac Q2,-\frac{P^2}{12}\right).
\]

This field is Hamiltonian, and direct substitution in
\(F_0\circ S=H\circ F_s\) gives

\[
S_1=0.
\]

It recovers the known first-order control (with the sign dictated by
postcomposition) and shows why the triangular primitive selected the wrong
source shell.

## Claim boundary and checked kill conditions

The volume gate has an all-order filtered right inverse inside the
inverse-cubic algebra.  This removes the \(6n+1\) shell as a gauge
obstruction: that shell belongs to the triangular primitive.

The complete quotient formal-contact construction is now all-order:
finite-branch normalization, polynomial source lift, volume rectification,
and the \(2n+1\) source bound.  Historical priority and a kernel
formalization of the general induction remain separate gates.

The construction would have been killed if:

1. the nonlinear order-\(n\) determinant variation is not the seed
   divergence \(\mathcal L\);
2. the trace-zero correction fails to define the characteristic target
   coefficients at some order;
3. the affine pole cancellation requires more than
   \(b(0,0)+c(0,0)=0\); or
4. the uncorrected source quotient introduced a coefficient above
   \(2n+1\).

The first three are the algebraic identities above.  The differentiated
factorization and the \(\omega_s\theta_s^{-1}\) formula exclude the fourth.
