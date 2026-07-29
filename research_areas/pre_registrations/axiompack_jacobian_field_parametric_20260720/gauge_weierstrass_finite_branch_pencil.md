# Finite-branch Weierstrass normalization

**Status:** active mechanism pencil; the quotient factorization is exact and
the volume correction remains open

## Eigenquestion

Does the fourth inverse sheet of the normalized deformation account for all
of the apparent all-order complexity, so that removing its invertible
`s`-adic factor leaves a slope-two formal contact with the cubic seed?

The construction is killed as a contact theorem if either:

- the finite factor cannot be normalized inside the equivariant lift ideals;
- volume normalization requires coefficients outside the same shifted Rees
  filtration;
- or the induced source lift is nonpolynomial or exceeds slope two.

## The inverse relation and the exceptional sheet

In the target coordinates `P,Q` and inverse coordinate `W`, the generic
relation is

\[
R_s(W)=W^3-aW^4-bW^2-cPW-dQ,
\]

where

\[
a=\frac{s}{2(s+2)},\qquad
b=\frac{s+4}{2(s+2)},\qquad
c=\frac{12}{(s-6)(s+2)},\qquad
d=-\frac{s-4}{2(s+2)}.
\]

The coefficient of \(W^4\) vanishes at \(s=0\), while the coefficient of
\(W^3\) is a unit. The reciprocal of the sheet escaping to infinity is the
unique series

\[
z\in s\mathbb Q[P,Q][[s]]
\]

solving

\[
z=a+bz^2+cPz^3+dQz^4.
\]

The fixed-point map is `s`-adically contractive. Successive approximation
therefore constructs a unique \(z\), and \(1-zW\) is a unit in the completed
source algebra.

Put \(r=z/a\). Then

\[
\begin{aligned}
A&=-r(b+cPz+dQz^2),\\
B&=-r(cP+dQz),\\
C&=-rdQ.
\end{aligned}
\]

Direct expansion gives the factorization

\[
\frac za R_s(W)
=(1-zW)(W^3+AW^2+BW+C).
\]

Since the first factor on the right is invertible, the completed finite
branch is governed by the monic cubic

\[
D_s(W)=W^3+AW^2+BW+C.
\]

At \(s=0\), this is the seed inverse cubic

\[
W^3-W^2+PW-Q.
\]

## Filtered mechanism

Give \(P,Q,W\) affine weights \(4,6,2\). Coefficient induction in the fixed
point equation gives

\[
\deg_f[s^n]z\le 2n-2.
\]

Because \(z/a=4z/s+2z\),

\[
\deg_f[s^n]r\le 2n.
\]

The cubic coefficients consequently satisfy

\[
\begin{aligned}
\deg_f[s^n]A&\le2n+2,\\
\deg_f[s^n]B&\le2n+4,\\
\deg_f[s^n]C&\le2n+6.
\end{aligned}
\]

Every increase of inverse-root degree consumes one parameter order and adds
two affine degrees. This is the structural source of the slope-two envelope.

## Coefficient normalization

Set

\[
h=\frac{A+1}{3},\qquad U=W+h.
\]

Then

\[
D_s(W)=U^3-U^2+P'U-Q',
\]

with

\[
\begin{aligned}
P'&=B+\frac{1-A^2}{3},\\
Q'&=-C+\frac{A+1}{3}B
-\frac{(A+1)^2(2A-1)}{27}.
\end{aligned}
\]

The coefficients obey

\[
\deg_f[s^n]h\le2n+2,\quad
\deg_f[s^n]P'\le2n+4,\quad
\deg_f[s^n]Q'\le2n+6.
\]

They also remain inside the quotient lift ideals:

\[
P'-P\in(P,Q)[[s]],\qquad
(Q'-Q)|_{Q=0}\in(P^2)[[s]].
\]

Thus the inverse relation has an exact liftable formal right-left
normalization with the desired filtration.

## Contact obstruction and next discriminator

The coefficient normalization is not area-preserving by itself. Its target
Jacobian begins

\[
\det\frac{\partial(P',Q')}{\partial(P,Q)}
=1-\frac5{12}s+O(s^2).
\]

The next discriminator is a volume correction within the same liftable
target group. For a prescribed density \(\rho(P,Q)\), the triangular field

\[
\left(\int_0^P\rho(u,Q)\,du,\ 0\right)
\]

lies in the first target lift ideal and has divergence \(\rho\). This makes
coefficientwise volume normalization plausible. It must still be shown that:

1. the full nonlinear Jacobian correction remains within the displayed
   filtered bounds;
2. its lift through the seed preserves polynomiality and the source lift
   ideals;
3. the resulting source substitution logarithm has the claimed slope-two
   bound.

`gauge_weierstrass_finite_branch.py` checks the factorization, coefficient
normalization, lift ideals, filtered inequalities, and first volume defect by
exact arithmetic through a declared truncation. The all-order bounds above
come from the fixed-point induction, not from truncation.
