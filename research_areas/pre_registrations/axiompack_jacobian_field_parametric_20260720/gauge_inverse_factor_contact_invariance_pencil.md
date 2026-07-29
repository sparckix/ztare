# Contact invariance of the escaping inverse factor

**Status:** exact obstruction theorem for the completed inverse algebra;
uniform-Rees-class lower theorem; both unrestricted tail-limsup minimaxes
remain open

## Governing object, equality, and lifecycle

The object transported by a coefficientwise-polynomial formal contact is the
completed finite inverse algebra, together with its source and target
polarizations:

\[
\mathscr A=\mathbb Q[P,Q][[s]],\qquad
\mathscr C=\mathbb Q[P,Q,W][[s]].
\]

Here `[[s]]` is coefficientwise: every coefficient of \(s^n\) is a
polynomial, while its polynomial degree may grow with \(n\).  For the
normalized family, the inverse presentation is

\[
R_s(W)=W^3-aW^4-bW^2-cPW-dQ,
\]

\[
a=\frac{s}{2(s+2)},\quad
b=\frac{s+4}{2(s+2)},\quad
c=\frac{12}{(s-6)(s+2)},\quad
d=-\frac{s-4}{2(s+2)}.
\]

The contact equality

\[
H_s\circ F_s=F_0\circ\Psi_s
\]

transports the completed inverse algebra.  A chosen polynomial generator
\(W\), its quartic presentation, and a compactification at \(W=\infty\)
are extra coordinates.  Their equality relation is change of monogenic
presentation, rather than literal equality of reciprocal roots.

The lifecycle has three distinct stages:

1. the generic polynomial inverse over \(\mathbb Q((s))[P,Q]\), of degree
   four;
2. coefficientwise \(s\)-adic completion, which discards the sheet escaping
   through \(W=\infty\);
3. a Rees degeneration that remembers the chosen polarization at infinity.

Completion and passage to the generic polynomial fiber do not commute here.

## The completed algebra has rank three

Let \(z\in s\mathscr A\) be the unique fixed point

\[
z=a+bz^2+cPz^3+dQz^4,
\]

and put \(r=z/a\).  The exact Weierstrass identity is

\[
rR_s(W)=(1-zW)D_s(W),
\]

where \(r\in\mathscr A^\times\) and \(D_s\) is monic cubic.

Because \(zW\in s\mathscr C\),

\[
(1-zW)^{-1}=\sum_{j\ge0}(zW)^j
\]

belongs to \(\mathscr C\): only finitely many summands contribute to each
coefficient of \(s^n\).  Hence \(1-zW\) is a unit and

\[
\boxed{(R_s)=(D_s)\quad\text{inside }\mathscr C.}
\]

Consequently

\[
\mathscr C/(R_s)\simeq\mathscr C/(D_s)
\]

is finite free of rank three over \(\mathscr A\).

This rules out the proposed Fitting/idempotent mechanism.  The factor
\((1-zW)\) defines the zero quotient in the completed category, so it
cannot define a rank-one direct summand or a nonzero idempotent.  The
Fitting ideals are those of a free rank-three module:

\[
\operatorname{Fitt}_i=0\ (i<3),\qquad
\operatorname{Fitt}_i=\mathscr A\ (i\ge3).
\]

The degree-four generic fiber lives over
\(\mathbb Q((s))[P,Q]\).  The full series \(z\), whose \(P,Q\)-degree is
unbounded, does not belong to that polynomial ring.  Thus generic degree
four and completed rank three are compatible facts.

The intrinsic discriminant of the completed finite algebra is the cubic
trace discriminant.  A quartic discriminant that retains the escaping
factor depends on the quartic presentation and its compactification.  It is
not a Fitting invariant of the completed contact algebra.

## Exact flattening of the reciprocal root

At \(P=Q=0\), the small fixed point is

\[
z_\circ=\frac{s}{s+4}.
\]

Indeed \(z_\circ=a+bz_\circ^2\).  Subtracting the two fixed-point equations
gives

\[
(z-z_\circ)\bigl(1-b(z+z_\circ)\bigr)
=cPz^3+dQz^4.
\]

The parenthesized factor is a unit, and therefore

\[
z-z_\circ\in s^3P\mathscr A+s^4Q\mathscr A.
\]

Define

\[
\phi=\frac1{z_\circ}-\frac1z
=\frac{z-z_\circ}{zz_\circ}
\in s(P,Q)\mathscr A
\]

and change the monogenic generator by

\[
W'=W+\phi.
\]

This is an identity-normalized coefficientwise-polynomial change of
presentation.  Directly,

\[
\boxed{
1-zW=\frac z{z_\circ}(1-z_\circ W').
}
\]

Thus the entire \(P,Q\)-dependent reciprocal root, including every sharp
top shell, can be replaced by the scalar root \(s/(s+4)\).  The reciprocal
root and its coefficient family are therefore not invariants of formal
contact algebra.

The displayed translation is an \(\mathscr A\)-linear change of monogenic
presentation.  No claim is made here that it is, by itself, a full
Hamiltonian pair \((H_s,\Psi_s)\) satisfying the source lift ideals and the
weighted-volume identity.  It is already sufficient to exclude extraction
of the shell from the abstract inverse algebra, its Fitting ideals, or its
idempotents.  Implementing the same transition inside the restricted
contact group is precisely the costed-quotient problem below.

This change does carry the same Rees cost.  With

\[
x=s^2P,\qquad y=s^3Q,\qquad
z=sZ(x,y)+\text{higher Rees valuation},
\]

the associated equation is

\[
Z=\frac14-xZ^3+yZ^4.
\]

The leading part of the translation is

\[
\phi=s^{-1}\Phi(x,y)+\text{higher Rees valuation},
\qquad
\Phi=4-\frac1Z=-4xZ^2+4yZ^3.
\]

Hence a monomial \(s^mP^iQ^j\) in the sharp part of \(\phi\) obeys

\[
2i+3j=m+1,\qquad
4i+6j=2m+2.
\]

After pullback to the source it has ordinary degree \(2m+2\).  As a
polynomial in target coordinates it has ordinary degree

\[
i+j\le\frac{m+1}{2}.
\]

The same presentation transition is therefore critical on the source
filtration and much cheaper in the ordinary target filtration.  This is the
precise redistribution that the symmetric minimax must quotient.

## A weighted Rees theorem

There is still an invariant statement when the target is charged in its
natural \((4,6)\)-weighted filtration.

Put \(s=\epsilon^2\), dilate the source by

\[
(v,t)=(V/\epsilon,T/\epsilon),
\]

and dilate the target by

\[
(P,Q)=(X/\epsilon^4,Y/\epsilon^6).
\]

Let

\[
G=T-\frac32V,\qquad r=VG.
\]

The two quotient maps have the Rees limits

\[
\overline F_{\rm def}(r)
=\left(r^3-3r^2,\frac34r^4-2r^3\right),
\]

\[
\overline F_0(r)=(-3r^2,-2r^3).
\]

The first image curve has an ordinary node at

\[
(-2,1).
\]

Its two normalization parameters are \(r=1\pm\sqrt3\), and their tangent
slopes are \(1\pm\sqrt3\).  The seed image is

\[
4X^3+27Y^2=0,
\]

which has one unibranch cusp and is smooth elsewhere.

For a contact coefficient at order \(n\), define shifted weighted excess

\[
\begin{aligned}
D_n=\max\{&
\deg(\Psi_{n,v})-1,\ \deg(\Psi_{n,t})-1,\\
&\deg_f(H_{n,P})-4,\ \deg_f(H_{n,Q})-6\},
\end{aligned}
\]

where \(\deg_f(P,Q)=(4,6)\).

Call the contact Rees-admissible when \(D_n\le2n\) for every \(n\).  If,
in addition,

\[
2n-D_n\longrightarrow+\infty,
\]

then the conjugated contact maps have polynomial specializations
\(\overline H,\overline\Psi\) at \(\epsilon=0\).  Specializing the contact
identity gives

\[
\overline H\circ\overline F_{\rm def}
=\overline F_0\circ\overline\Psi.
\]

Since \(\det D H_s=1\), one has
\(\det D\overline H=1\).  Thus \(\overline H\) is étale.  It would map the
two transverse local branches of the node into the seed cusp curve.
An étale ambient map preserves the two distinct local branches, whereas the
seed curve is unibranch at its only singular point.  This is impossible.

Therefore every Rees-admissible contact satisfies

\[
\boxed{
D_n\ge2n-C
\quad\text{for infinitely many }n
}
\]

for some contact-dependent constant \(C\).

Equivalently, every contact obeys the dichotomy

\[
\boxed{
\exists n:\ D_n>2n,
\quad\text{or}\quad
D_n\ge2n-O(1)\ \text{infinitely often}.
}
\]

This separates the globally Rees-admissible class: every contact in that
class has infinitely many near-critical coefficients.  It does not close an
unrestricted tail-limsup minimax.  The first arm of the dichotomy can be
satisfied by one finite supercritical coefficient, which disappears from a
tail limsup.  Removing that finite-prefix loophole requires an additional
normalization theorem.

The existing inverse-cubic construction supplies a matching upper
coefficient envelope inside the Rees-admissible class.  Passing from
assembled maps to logarithmic generators is a further filtered exp/log
comparison.

That comparison cannot be inferred from a tail limsup alone.  If a formal
logarithm has

\[
B_s=sA+s^2B,
\]

then its instantaneous velocity contains the dexp series

\[
\operatorname{dexp}_{B_s}(\partial_sB_s)
=\sum_{k\ge0}\frac{\operatorname{ad}_{B_s}^k(\partial_sB_s)}
{(k+1)!}.
\]

Its part linear in \(B\) contains infinitely many iterates
\(\operatorname{ad}_A^kB\).  Polynomial Hamiltonian Witt fields give an
explicit nonterminating example: take Hamiltonians

\[
K_A=QP^4,\qquad K_B=QP^2.
\]

Their brackets follow the Witt rule and
\(\operatorname{ad}_{X_{K_A}}^kX_{K_B}\) has degree growing by three per
iteration.  The logarithm has only two nonzero parameter coefficients,
while its velocity has an infinite high-slope tail.

Therefore a boundary-Hamiltonian argument for logarithmic
\(\sigma_{\rm ct}\) needs one of:

1. a triangular bound on every logarithmic coefficient, including the
   finite prefix;
2. a gauge theorem removing the finite supercritical prefix; or
3. a contact-specific proof that its iterated brackets cannot populate the
   critical node-valuation shell.

## Why the ordinary symmetric minimax stays open

The campaign's symmetric logarithmic statistic charges ordinary target
degree:

\[
\sigma_{\rm ct}
=\inf\limsup_n
\frac{\max\{e(Y_n),e(X_{K_n})\}}n.
\]

The weighted theorem above charges \(P^iQ^j\) by \(4i+6j\).  Replacing that
weight by ordinary degree \(i+j\) changes the conclusion.  The sharp
transition just exhibited has source cost \(2m+O(1)\) and target cost at
most \(m/2+O(1)\).

Accordingly, the reciprocal root, its Fitting data, and the weighted
node-versus-cusp degeneration do not force

\[
\max\{\deg Y_n,\deg X_{K_n}\}\ge2n-O(1)
\]

in the ordinary symmetric metric.  They prove that any trivialization must
pay the weighted Rees shell somewhere.  The target Hamiltonian image can
carry that shell at lower ordinary degree.

The remaining invariant is a costed quotient:

\[
\frac{
\text{critical source Rees shell}
}{
\text{polynomially liftable Hamiltonian target image of ordinary degree }
<2n-O(1)
}.
\]

A lower theorem requires a nonzero class in this quotient along an infinite
subsequence, including BCH/Magnus contributions from lower orders.  A
slope-below-two construction requires an all-order representative with
finite target support at each coefficient of \(s\).  The present inverse
factor supplies neither conclusion by itself.

## Claim boundary

Established here:

1. the completed inverse algebra is rank three;
2. no rank-one Fitting or idempotent summand represents the escaping sheet;
3. an explicit identity-normalized generator change flattens the reciprocal
   root to \(s/(s+4)\);
4. that change has exact source-critical and target-cheap degree profiles;
5. a node-versus-cusp argument proves infinitely many near-critical
   coefficients inside the globally Rees-admissible class.

Still unresolved:

1. both unrestricted tail-limsup minimaxes, including the weighted
   coefficient-map version with a finite supercritical prefix;
2. the ordinary-degree symmetric logarithmic minimax;
3. whether the complete Hamiltonian target image kills both sharp parity
   families after all BCH contributions;
4. historical priority for the uniform-Rees-class obstruction.
