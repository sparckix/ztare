# Completed inverse factor and Rees-node boundary

**Status:** deterministic replay passes; exact completed-algebra and
uniform-Rees-class results; unrestricted tail-limsup claims remain open;
historical priority unassessed

## Verdict

The escaping reciprocal root does not define a rank-one summand of the
coefficientwise \(s\)-adic inverse algebra.  Its linear factor is a unit,
the completed algebra is free of rank three, and an explicit
identity-normalized generator translation removes every \(P,Q\)-dependent
coefficient of that reciprocal root.

The chosen polarization still leaves a boundary invariant.  Under the
diagonal Rees scaling, the deformed map has a nodal image curve and the seed
map has a cuspidal image curve.  This forces infinitely many near-critical
coefficients for contacts that stay inside the global slope-two Rees class.

There is no unrestricted tail-limsup conclusion.  A single finite
supercritical coefficient enters the other arm of the exact dichotomy and
is invisible to a tail limsup.  The logarithmic version has an additional
dexp/BCH loophole.

## Completed inverse algebra

Work in

\[
\mathscr A=\mathbb Q[P,Q][[s]],\qquad
\mathscr C=\mathbb Q[P,Q,W][[s]].
\]

For the inverse quartic

\[
R_s(W)=W^3-aW^4-bW^2-cPW-dQ
\]

and the unique reciprocal root

\[
z=a+bz^2+cPz^3+dQz^4,
\]

the replay checks

\[
\frac zaR_s(W)
=(1-zW)(W^3+AW^2+BW+C).
\]

The unreduced symbolic residual is exactly

\[
\frac{2(s+2)}sW^3
\left(z-a-bz^2-cPz^3-dQz^4\right).
\]

Since \(z\in s\mathscr A\),

\[
(1-zW)^{-1}=\sum_{j\ge0}(zW)^j
\]

belongs to \(\mathscr C\).  Therefore

\[
(R_s)=(W^3+AW^2+BW+C)
\]

and

\[
\boxed{
\mathscr C/(R_s)\ \text{is free of rank three over }\mathscr A.
}
\]

The completed Fitting ideals consequently contain no rank-one component.
The generic degree-four inverse over
\(\mathbb Q((s))[P,Q]\) belongs to a different lifecycle: the full
unbounded-degree series \(z\) is absent from that polynomial ring.

## Exact reciprocal-root flattening

At the target origin,

\[
z_\circ=\frac{s}{s+4}.
\]

Subtracting its scalar fixed-point equation from the general one gives

\[
(z-z_\circ)(1-b(z+z_\circ))
=cPz^3+dQz^4.
\]

Thus

\[
\phi=\frac1{z_\circ}-\frac1z\in s(P,Q)\mathscr A.
\]

For

\[
W'=W+\phi,
\]

the replay checks the exact identity

\[
\boxed{
1-zW=\frac z{z_\circ}(1-z_\circ W').
}
\]

The first translation coefficients are

\[
\begin{aligned}
[s]\phi&=-\frac P4,\\
[s^2]\phi&=\frac{P+3Q}{48},\\
[s^3]\phi&=\frac{18P^2-7P-27Q}{576}.
\end{aligned}
\]

For the associated equation

\[
Z=\frac14-xZ^3+yZ^4,\qquad x=s^2P,\quad y=s^3Q,
\]

the leading translation is

\[
\Phi=4-\frac1Z=-4xZ^2+4yZ^3.
\]

Every sharp monomial \(s^mP^iQ^j\) satisfies

\[
2i+3j=m+1.
\]

Its pullback/filtered cost is

\[
4i+6j=2m+2,
\]

while its ordinary target degree obeys

\[
i+j\le\frac{m+1}{2}.
\]

This is a change of monogenic presentation.  The replay does not assert
that this translation alone satisfies the Hamiltonian, source-lift, and
weighted-volume contact constraints.  It proves that the reciprocal root
cannot be extracted from the abstract algebra by Fitting ideals or
idempotents, and it exhibits the exact source/target cost asymmetry.

## Rees node versus seed cusp

Put

\[
s=\tau\epsilon^2,\qquad
(v,t)=(V/\epsilon,T/\epsilon),
\]

and scale target coordinates by \((\epsilon^4,\epsilon^6)\).  With

\[
r=V\left(T-\frac32V\right),
\]

direct substitution into the normalized family gives

\[
f_\tau(r)=
\left(\tau r^3-3r^2,\frac34\tau r^4-2r^3\right).
\]

The seed boundary is

\[
f_0(r)=(-3r^2,-2r^3),
\qquad
4P^3+27Q^2=0.
\]

The deformed boundary has two normalization points

\[
r_\pm=\frac{1\pm\sqrt3}{\tau}
\]

with common image

\[
f_\tau(r_\pm)=
\left(-\frac2{\tau^2},\frac1{\tau^3}\right).
\]

Their tangent determinant is

\[
\boxed{
\det(f_\tau'(r_+),f_\tau'(r_-))
=-\frac{72\sqrt3}{\tau^3}\ne0.
}
\]

Thus the image has a transverse node.  The seed curve has one unibranch
cusp and is smooth elsewhere.

Let \(D_n\) be the maximum shifted degree at contact order \(n\), using
ordinary source degree and target weights \((4,6)\):

\[
\begin{aligned}
D_n=\max\{&
\deg(\Psi_{n,v})-1,\deg(\Psi_{n,t})-1,\\
&\deg_f(H_{n,P})-4,\deg_f(H_{n,Q})-6\}.
\end{aligned}
\]

If \(D_n\le2n\) for every \(n\) and
\(2n-D_n\to+\infty\), the conjugated contact has polynomial
\(\epsilon=0\) specializations \(\overline H,\overline\Psi\).  The contact
identity specializes to

\[
\overline H\circ f_\tau=f_0\circ\overline\Psi,
\qquad
\det D\overline H=1.
\]

An étale target map preserves the two independent node tangents.  It cannot
send that node into the unibranch seed curve.  Hence every globally
Rees-admissible contact satisfies

\[
\boxed{
D_n\ge2n-C
\quad\text{for infinitely many }n
}
\]

for some constant \(C\).

For unrestricted contacts the exact result is only

\[
\boxed{
\exists n:\ D_n>2n,
\quad\text{or}\quad
D_n\ge2n-O(1)\ \text{infinitely often}.
}
\]

The first arm may consist of one finite coefficient.  It does not imply a
tail-limsup lower bound.

## Logarithmic limsup loophole

The boundary equation naturally uses instantaneous target/source
velocities.  A logarithmic tail bound does not automatically transfer to
those velocities.

Take polynomial Hamiltonians

\[
K_A=QP^4,\qquad K_B=QP^2
\]

and a finite logarithm

\[
B_s=sX_{K_A}+s^2X_{K_B}.
\]

The dexp series for its instantaneous velocity contains
\(\operatorname{ad}_{X_{K_A}}^kX_{K_B}\) at every depth.  The replay checks
the Hamiltonian sequence

\[
P^2Q,\ 2P^5Q,\ -2P^8Q,\ 8P^{11}Q,\ldots
\]

whose field degrees are

\[
2,\ 5,\ 8,\ 11,\ldots,\ 2+3k.
\]

Thus two finite logarithmic coefficients can create an infinite
instantaneous-velocity tail of slope three.  A logarithmic node-separation
theorem requires one of:

1. a global triangular bound that includes the finite prefix;
2. a normalization removing finite supercritical terms; or
3. a theorem excluding their critical iterated brackets in this contact
   stabilizer.

None of those three bridges is claimed here.

## Verification

The deterministic replay is
[`gauge_inverse_factor_rees_boundary.py`](gauge_inverse_factor_rees_boundary.py).
It checks:

- the exact quartic-to-cubic factorization modulo the fixed-point equation;
- the coefficientwise unit inverse;
- the scalar-root and generator-flattening identities;
- the first translation shells and their two degree profiles;
- direct Rees specialization of the normalized family and seed;
- node images, tangent separation, and the seed cusp;
- preservation of tangent separation by an invertible target Jacobian;
- and a concrete nonterminating Witt bracket cascade.

The replay and Python bytecode compilation pass.  At this revision the
replay SHA-256 is

`e19560219bc71dd843c5a436a2d15880fb38e80fc519c993f3a8949b23f7ccd0`.

## Claim boundary

Established:

- completed inverse rank three;
- absence of a rank-one Fitting/idempotent factor;
- exact presentation-level reciprocal-root flattening;
- exact source-critical versus target-cheap shell costs;
- node/cusp separation inside the global Rees-admissible class;
- the finite-prefix dexp loophole.

Open:

- unrestricted weighted coefficient-map tail limsup;
- ordinary-degree symmetric logarithmic tail limsup;
- contact-group implementation of the flattening translation;
- historical priority.
