# Cusp normalization versus a filtered contact generator

**Status:** pencil; the curve-only Padé extension is excluded, the corrected
target-relative construction passes complete infinitesimal orders one through
four, and arbitrary-order target descent is reduced to two inverse-cubic
module coordinates

## Eigenquestion

Can the normalized family be written

\[
\partial_sF_s=X_{H_s}(F_s)+dF_sV_s
\]

so that the resulting source substitution logarithm has

\[
\deg Y_n\leq 2n+1
\]

at every parameter order?

Map coefficients, instantaneous fields \(V_s\), and logarithmic fields
\(Y_n\) are kept separate below.

## Exact curve coordinate

Put

\[
a=1-\frac{s}{6},\qquad \ell=1-\frac{s}{4},\qquad
\mu=\frac{\ell}{a},\qquad x=3w-1.
\]

The family coordinate is

\[
x_s=\frac{\ell x-\frac{s}{12}(1-3\gamma)}{a},
\qquad
x_s=x+s\left(\frac{\gamma}{4}-\frac{x+1}{12}\right)+O(s^2).
\]

With

\[
d^2=3s^2+12s+36,\qquad
\alpha=\frac{s+6-d}{2s},
\]

define

\[
\phi_s(y)=(y-\alpha)\sqrt{\frac d6}
 \sqrt{1-\frac{2s(y-\alpha)}{3d}}.
\]

The identities checked in `gauge_cusp_pade_mechanism.py` give

\[
p_s(y)-p_s(\alpha)=-\frac{\phi_s(y)^2}{3}
\]

and the exact tangent remainder

\[
q_s(y)-q_s(\alpha)
-\frac{\alpha+1}{3}\bigl(p_s(y)-p_s(\alpha)\bigr)
=\frac{(y-\alpha)^3(-4d+3s(y-\alpha))}{324}.
\]

Consequently

\[
[s^n]\phi_s(y)\in\mathbb Q[y],
\qquad
\deg_y[s^n]\phi_s\leq n+1.
\]

The associated cusp discriminant discrepancy is divisible by the sixth
power of the curve parameter:

\[
\left(\frac{\xi^3(-4d+3s\xi)}{324}\right)^2
-\frac{4}{729}
\left(
 \frac{d\xi^2}{6}
 \left(1-\frac{2s\xi}{3d}\right)
\right)^3
\in s\,\xi^6\mathbb Q[[s]][\xi].
\]

Thus the curve-level normal displacement has no low cusp-semigroup
obstruction.

## Projective normalization and its filtration

Let

\[
A_s=\phi_s(-1),\qquad B_s=\phi_s(2),
\qquad
\kappa_s=
\frac{a(B_s-A_s)}{3\phi_s'(2)}.
\]

The unique Möbius normalization fixing the contracted affine line, fixing
the source origin, and imposing derivative \(a\) at the origin is

\[
M_s(\eta)=
\frac{2(\eta-A_s)+\kappa_s(\eta-B_s)}
     {(\eta-A_s)-\kappa_s(\eta-B_s)}.
\]

It satisfies

\[
M_s(A_s)=-1,\qquad M_s(B_s)=2,\qquad
\frac{d}{dy}M_s(\phi_s(y))\bigg|_{y=2}=a.
\]

Moreover \(\kappa_s=1+O(s^2)\).  In the denominator, the coefficient of
\(s^n\) has \(y\)-degree at most \(n-1\); in the numerator it has degree at
most \(n+1\). Formal division therefore gives

\[
U_s(y):=M_s(\phi_s(y)),\qquad
\deg_y[s^n]U_s\leq n+1.
\]

Since \(U_s(-1)=-1\), its divided difference

\[
D_s(y)=\frac{U_s(y)+1}{y+1}
\]

obeys

\[
\deg_y[s^n]D_s\leq n.
\]

Using the exact identity

\[
x_s+1=3\gamma(1+\mu v),
\]

the direct source coordinate

\[
1+\widehat v_s=(1+\mu v)D_s(x_s)
\]

has affine coefficients of degree at most \(2n+1\). This is the positive
filtration mechanism behind the finite slope-two prefixes.

## Map-to-generator lemma

Suppose a source substitution has

\[
\Psi_s=\mathrm{id}+\sum_{n\geq1}s^nf_n,\qquad
\deg f_n\leq2n+1.
\]

Every coefficient of its instantaneous velocity

\[
V_s=(D\Psi_s)^{-1}\partial_s\Psi_s
\]

and every coefficient of its substitution logarithm is a sum of rooted
composition words. A word with \(r\) coefficient occurrences of total
parameter order \(n\) contains \(r-1\) spatial derivatives. Hence

\[
\deg(\text{word})
\leq\sum_{i=1}^r(2n_i+1)-(r-1)=2n+1.
\]

Therefore the direct-map filtration would imply the same bound for the
instantaneous and logarithmic generators. This implication cannot be used
until the map is admitted by the contact equation.

## Shifted Rees formulation

Let

\[
\mathcal F_r=\{Z:\deg Z\leq r+1\}.
\]

Polynomial vector fields satisfy

\[
[\mathcal F_r,\mathcal F_k]\subseteq\mathcal F_{r+k}.
\]

Consequently

\[
\prod_{n\geq1}s^n\mathcal F_{2n}
\]

is a Lie algebra. If a source logarithm has
\(Y_n\in\mathcal F_{2n}\), then the coefficient of \(s^m\) in its
instantaneous velocity lies in

\[
\mathcal F_{2m+2},
\qquad
\deg [s^m]V_s\leq2m+3.
\]

Conversely, a Magnus word in velocity coefficients \(V_{m_i}\) contributing
at logarithmic order \(n\) has

\[
n=\sum_i(m_i+1),\qquad
\sum_i(2m_i+2)=2n,
\]

so the same instantaneous bound integrates back into the slope-two
logarithmic algebra.

This changes the all-order task from a nonlinear BCH search into a
coefficientwise infinitesimal contact recursion:

\[
\partial_sF_s=X_s(F_s)+dF_sV_s.
\]

After lower coefficients are fixed, the new \(X_m,V_m\) enter this equation
linearly in the shifted Rees windows.

## Generic gamma-divisible weighted-area lift

Write a polynomial source velocity in \((v,\gamma)\) coordinates as
\(V=(a,b)\), where \(b=V(\gamma)\). Preservation of
\(\gamma^2\,dv\wedge d\gamma\) is equivalent to

\[
2b+\gamma(\partial_va+\partial_\gamma b)=0.
\]

For

\[
x=3(1+v)\gamma-1,\qquad R=\frac{\gamma^2}{2},
\]

this forces the exact factorizations

\[
\begin{aligned}
V(x)
&=3\gamma a+3(1+v)b\\
&=\gamma\left(
3a-\frac32(1+v)\operatorname{div}V
\right),\\
V(R)&=\gamma b
=-\frac{\gamma^2}{2}\operatorname{div}V.
\end{aligned}
\]

The induced pair \(u=V(x)\), \(r=V(R)\) satisfies the linear canonical-area
equation

\[
\partial_\gamma r\big|_x
+\gamma\,\partial_xu\big|_\gamma=0.
\]

The family coordinate also obeys

\[
x_s\big|_{x=-1,\gamma=0}=-1,
\]

and the projective Padé normalization fixes \(-1\). Hence every positive
parameter coefficient of the cusp coordinate vanishes on the exceptional
divisor. Since \(\gamma\) is linear, the difference between that coefficient
and any admissible \(V(x)\) is polynomially divisible by \(\gamma\).

If \([s^m]V_s\) has degree at most \(2m+3\), the quotient has the same
degree bound: both numerators have degree at most \(2m+4\), and division by
\(\gamma\) removes one degree. Thus gamma divisibility and the weighted-area
companion are automatic for every shifted-Rees velocity. The remaining
mathematical obstruction is target descent.

`gauge_cusp_rees_lift_identity.py` replays these identities symbolically for
generic coefficient functions.

## First-order obstruction to the direct Padé contact

Both \(F_s\) and \(F_0\) have quotient Jacobian \(-\gamma^2\), while target
Hamiltonian flows preserve area. Any source contact must therefore preserve

\[
\gamma^2\,dv\wedge dt.
\]

In \((x,\gamma)\) coordinates this form is
\(\frac{\gamma}{3}dx\wedge d\gamma\). If the corrected source coordinates
are \((U,\Gamma)\), put \(R=\Gamma^2/2\). The exact area equation is

\[
U_xR_\gamma-U_\gamma R_x=\gamma.
\]

At first order, every projective postnormalization of the Padé coordinate
has

\[
U_1=\frac{\gamma}{4}+p_2(x),
\qquad \deg p_2\leq2.
\]

The \(\gamma/4\) term comes from \(x_s\) and cannot be removed by a
projective transformation depending only on the curve coordinate. Solving
the area equation gives

\[
R_1=-\frac{\gamma^2}{2}p_2'(x)+f(x).
\]

Affine polynomiality of the recovered \(v\)-coordinate requires

\[
f(x)=(x+1)^2h(x).
\]

If the first source field has degree at most five, then
\(\deg h\leq1\). Thus the complete first-order Padé/area family has six
scalar coordinates: the three coefficients of \(p_2\), the two
coefficients of \(h\), and a possible multiple \(\lambda Z_*\) of the
unique degree-five seed stabilizer.

Exact coefficient comparison of

\[
Y_1=\lambda Z_*
\]

has coefficient-matrix rank \(6\) and augmented rank \(7\). A compact dual
certificate can be stated as follows. Clear the first-component denominator:

\[
N=12(2t-3v+2)\bigl(Y_{1,v}-\lambda Z_{*,v}\bigr).
\]

For every choice of the six scalars,

\[
\begin{aligned}
&-413[v^6]N-765[v^4]N-405[v^3t]N+351[v^3]N\\
&\hspace{35mm}-81[v^2]N+243[v]N=-729.
\end{aligned}
\]

Therefore the curve-only projective extension of the Padé normalization
cannot be the source part of a Hamiltonian contact, even though its map
coefficients have the desired filtration. This does not exclude adding
terms divisible by \(\gamma\), which leave the critical curve unchanged.

## Corrected route and kill conditions

The family tangent is already the fixed target Hamiltonian field

\[
X_1=(-Q/2,P^2/12),
\]

with normalized source tangent zero. The next construction may first remove
this target motion, or equivalently add target-relative off-curve terms to
the Padé coordinate. A suitable triangular ansatz is

\[
U_s(x,\gamma)=U_s^{\mathrm{cusp}}(x_s)
+\gamma A_s(x,\gamma),
\]

where \(U_s^{\mathrm{cusp}}\) is the projective Padé coordinate and
\([s^n]A_s\) is required to have affine degree compatible with the
\(2n+1\) window. The \(\gamma A_s\) term can cancel the first-order
\(\gamma/4\) without changing the normalized critical curve.

The construction succeeds only if all of the following hold:

1. the target-relative Padé coordinate begins at source order two;
2. the weighted-area equation has coefficientwise polynomial solutions in
   the affine lift ideals;
3. the remaining response descends through \(F_0\) to a polynomial
   Hamiltonian, certified by the \(C\)-normal form or the inverse cubic;
4. both source and target instantaneous fields lie in the slope-two Lie
   filtration.

A nonzero first-order source class after the target-relative normal
correction, failure of polynomial descent at any order, or a coefficient
above degree \(2n+1\) kills the all-order mechanism.

## Executable first-order correction

`gauge_cusp_generator_first_order_replay.py` independently reconstructs the
rank-\(6\)/augmented-rank-\(7\) curve-only system and evaluates the displayed
dual functional to \(-729\).

For the actual projective Padé coordinate, composition with \(x_s\) gives

\[
U^{\mathrm{cusp}}_1
=\frac{\gamma}{4}
-\frac{(x+1)(2x-1)}{36}.
\]

Since \(x+1=3\gamma(1+v)\), the off-curve coefficient

\[
A_1=-\frac14+\frac{(1+v)(2x-1)}{12}
\]

is polynomial in the affine source coordinates and satisfies

\[
U^{\mathrm{cusp}}_1+\gamma A_1=0.
\]

Taking \(R_1=0\) then solves the order-one weighted-area equation and
recovers the zero source jet. The family tangent is exactly

\[
X_{-Q^2/4-P^3/36}\circ F_0.
\]

Thus the corrected target-relative construction passes order one. Its first
open coefficient is order two.

## Order-two corrected Padé coefficient

`gauge_cusp_generator_order_two_replay.py` performs the next linear
infinitesimal step. In derivative-normalized convention, the uncorrected
projective coefficient is

\[
U^{\mathrm{cusp}}_2
=-\frac{(x-2)(18\gamma+x^2-7x-8)}{324}.
\]

For the degree-five source field \(Y_2\) from the certified contact prefix,
put

\[
U^{\mathrm{desired}}_2=Y_2(x).
\]

Exact division gives

\[
A_2=\frac{Y_2(x)-U^{\mathrm{cusp}}_2}{\gamma}
\in\mathbb Q[v,t],
\qquad \deg A_2=5.
\]

Thus

\[
U^{\mathrm{cusp}}_2+\gamma A_2=Y_2(x)
\]

inside the required shifted Rees window. Its weighted-area companion is

\[
R_2=Y_2\left(\frac{\gamma^2}{2}\right)
=\gamma Y_2(\gamma),
\]

and the exact weighted divergence vanishes:

\[
\partial_v(\gamma^2Y_{2,v})
+\partial_t(\gamma^2Y_{2,t})=0.
\]

Recovering affine coordinates from \((U_2,R_2)\) returns \(Y_2\) exactly.
With

\[
K_2=-\frac{5P^3}{1512}-\frac{P^2Q}{168}
-\frac{11PQ}{120}+\frac{29Q^2}{168},
\]

the target descent replay is

\[
F_2=X_1^2(F_0)+X_{K_2}(F_0)+dF_0Y_2.
\]

The corrected Padé construction therefore passes orders one and two. The
generic lift identity above settles gamma divisibility and weighted area
conditionally on the Rees velocity; polynomial target descent remains.

## Order-three linear Rees solve

`gauge_cusp_generator_order_three_replay.py` derives the third coefficient
from the instantaneous equation without reading the carried logarithmic
\(Y_3\). After subtracting the settled lower transport, the residual
component degrees are \((10,12)\). The complete degree-seven weighted-area
source window has \(69\) columns; the exhaustive \((10,12)\) \(C\)-normal
Hamiltonian target window has \(9\).

The combined exact system has shape \(199\times78\), rank \(75\), augmented
rank \(75\), and nullity \(3\). Source caps two, three, and four are
inconsistent; cap five is the first consistent window. A cap-five
instantaneous solution has component degrees \((5,5)\) and target
Hamiltonian

\[
\begin{aligned}
H_3^{\mathrm{vel}}
={}&\frac{P^4}{224}-\frac{5P^3}{13608}
-\frac{17P^2Q}{1008}+\frac{5PQ^2}{168}\\
&-\frac{1049PQ}{60480}-\frac{2419Q^2}{40320}.
\end{aligned}
\]

The exact third derivative of the uncorrected projective coordinate is

\[
U^{\mathrm{cusp}}_3
=-\frac{
81\gamma^2+27\gamma x^2-270\gamma
+2x^4-23x^3+6x^2+80x+49
}{3888}.
\]

For the solved velocity \(V_2\),

\[
A_3=\frac{V_2(x)-U^{\mathrm{cusp}}_3}{\gamma}
\]

is polynomial of degree seven. Its numerator restricts to zero on
\(\gamma=0\), the weighted divergence vanishes, the companion
\(R_3=\gamma V_2(\gamma)\) recovers \(V_2\), and the full third
infinitesimal contact equation replays exactly.

Thus the corrected Padé construction passes orders one through three. The
generic lift identity removes gamma divisibility and weighted area from the
open list; arbitrary-order polynomial target descent is the surviving
scientific boundary.

## Order-four Rees solve and the first nonlinear map term

`gauge_cusp_generator_order_four_replay.py` continues the instantaneous
recursion. The residual component degrees are \((12,14)\). The complete
degree-nine weighted-area source window contributes \(107\) columns and the
exhaustive \((12,14)\) \(C\)-normal target window contributes \(12\).

The combined \(274\times119\) system has rank and augmented rank \(113\),
with nullity \(6\). Source caps through five are inconsistent; cap six is
the first consistent window. The selected velocity has component degrees
\((6,6)\).

Because the source velocity begins with \(sV_1\), the fourth direct-map
coefficient is no longer the new velocity alone. On the \(x\) coordinate it
is

\[
U^{\mathrm{desired}}_4
=V_3(x)+3V_1(V_1(x)).
\]

The exact projective coefficient is

\[
U^{\mathrm{cusp}}_4
=-\frac{
243\gamma^2x+729\gamma^2
+72\gamma x^3-378\gamma x^2+108\gamma x-1710\gamma
+5x^5-56x^4+85x^3+98x^2+277x+325
}{34992}.
\]

Their difference vanishes on \(\gamma=0\), and

\[
A_4=\frac{U^{\mathrm{desired}}_4-U^{\mathrm{cusp}}_4}{\gamma}
\]

is polynomial of degree nine, exactly the fourth logarithmic Rees allowance.
The target Hamiltonian reduces to

\[
\begin{aligned}
H_4^{\mathrm{vel}}={}&
-\frac{149}{27216}CP+\frac{19}{4536}CQ
+\frac{2867}{78382080}C+\frac{281}{27216}P^4\\
&+\frac{37}{9072}P^3Q-\frac{8021}{2799360}P^3
-\frac{14501}{725760}P^2Q+\frac{2867}{78382080}P^2\\
&-\frac{323}{68040}PQ-\frac{2867}{19595520}Q.
\end{aligned}
\]

Thus order four passes while introducing no target coordinate outside the
same \(C\)-normal algebra.

## Fixed inverse-cubic descent module

The inverse cubic gives a finite target-descent test:

\[
\mathcal B
=\mathbb Q[P,Q,w]/(w^3-w^2+Pw-Q)
=\mathbb Q[P,Q]\langle1,w,w^2\rangle.
\]

Every source-side expression has a unique reduction

\[
f=f_0(P,Q)+w f_1(P,Q)+w^2f_2(P,Q).
\]

It descends to the target exactly when

\[
f_1=f_2=0.
\]

Multiplication by \(w\) on coefficient vectors is the fixed companion
matrix

\[
\begin{pmatrix}
0&0&Q\\
1&0&-P\\
0&1&1
\end{pmatrix},
\]

and powers obey

\[
w^{n+3}=w^{n+2}-Pw^{n+1}+Qw^n.
\]

Equivalently,

\[
\sum_{n\geq0}w^nz^n
\equiv
\frac{
1-z+Pz^2+(z-z^2)w+z^2w^2
}{
1-z+Pz^2-Qz^3
}
\pmod{w^3-w^2+Pw-Q}.
\]

So the all-order descent obstruction is a two-coordinate recurrence, rather
than an expanding table of source monomials.

The target side is finite over the canonical coordinate ring:

\[
\mathbb Q[P,Q]
=\mathbb Q[P,C]\oplus Q\,\mathbb Q[P,C].
\]

For \(K=A(P,C)+QB(P,C)\), the chain and product rules give

\[
X_K
=A_PX_P+A_CX_C+B X_Q
+Q B_PX_P+Q B_CX_C.
\]

Hence all polynomial Hamiltonian target fields form the
\(\mathbb Q[P,C]\)-module generated by

\[
X_P,\quad X_Q,\quad X_C,\quad QX_P,\quad QX_C.
\]

The exact filtered target dimensions in consecutive Rees windows begin

\[
6,7,9,12,14,17,21,24,28
\]

and satisfy the tested cumulative recurrence with candidate Hilbert series

\[
\frac{
6+z-4z^2-4z^3-z^4+4z^5
}{
(1-z)(1-z^2)(1-z^3)
}.
\]

`gauge_inverse_cubic_target_module.py` replays the cubic recurrence, the
rank-three reduction, the five-generator target identity, and these exact
finite-window dimensions. The remaining theorem is that the two nonbase
coordinates of the family forcing vanish, or can be killed inside the
shifted Rees source window, at every order.

## Claim boundary

The Padé identity supplies a curve normalization and a sharp degree
mechanism. It does not yet supply an all-order contact decomposition. The
curve-only source interpretation is excluded. The corrected normal extension
and weighted-area companion are now forced for every admissible shifted-Rees
velocity, and complete orders one through four pass. Polynomial target
descent is reduced to the \(w,w^2\) coordinates of a fixed rank-three
inverse-cubic module. Proving their all-order vanishing or cancellability in
every shifted Rees window is the remaining mathematical problem.
