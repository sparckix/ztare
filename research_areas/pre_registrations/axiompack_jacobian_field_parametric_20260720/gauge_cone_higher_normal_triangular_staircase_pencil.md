# Higher-normal cone staircase below the radial rate-two envelope

## Claim boundary

The radial triangular construction gives a coefficientwise-finite
cone-valued connection of symmetric rate at most two.  This pencil tests
whether unused same-weight cone directions can cancel its growing
second-normal layer.  It does not infer a sub-two rate from one kernel
direction.

## Eigenquestion

Does the cone intersection with the seed cusp ideal provide enough finite
directions at every sufficiently large row to reduce the \(z^2\) layer from
degree \(2q+4\) to a strictly smaller linear envelope?

## First kernel direction

Let

\[
C=4P^3-P^2-18PQ+27Q^2+4Q.
\]

At the seed,

\[
C(F_0)=\frac{z^2}{4}\left(3P_0+\frac z2-1\right),
\]

so

\[
\operatorname{top}C(F_0)=-\frac9{16}r^2z^2.
\]

The polynomial \(C\) itself is not in the cone because of its pure \(P\)
terms.  Multiplication by \(Q^2\) repairs every cone inequality:

\[
\boxed{
Q^2C
=4P^3Q^2-P^2Q^2-18PQ^3+27Q^4+4Q^3
\in\mathfrak c.
}
\]

Its source pullback begins with

\[
\operatorname{top}(Q^2C)(F_0)
=-\frac9{256}r^8z^2.
\]

Thus the first unused cone-kernel direction appears exactly at the
cost-seven row, where the radial staircase top is \(r^8z^2\).

## Eventual second-normal coverage

A multiplier \(P^aQ^bC\) lies in the cone whenever

\[
b\ge1,\qquad a+3\le2b.
\]

Its multiplier radial weight is \(2a+3b\).  These weights include

\[
6,8,9,\quad\text{and every integer }w\ge11.
\]

Therefore, apart from finitely many low rows, cone multiples of \(C\) have
the correct leading \(z^2\) symbols to cancel every sufficiently high
\(r\)-degree in the second-normal layer.  The solve must be triangular in
normal order: first radial, then \(z^2\), while preserving the already fixed
radial and \(z^1\) layers.

## Discriminating replay

1. Extend the radial staircase through the cost-seven row.
2. Add the homogeneous direction \(Q^2C\) and solve its coefficient from the
   exact \(r^8z^2\) residual.
3. Verify that radial and first-normal coefficients remain unchanged.
4. Carry at least four more rows using all available \(P^aQ^bC\) directions,
   recording the finite exceptional multiplier weights.
5. Recompute the source Newton polygon and target degree envelope after the
   second-normal solve.
6. Test the next uncontrolled normal layer and determine whether its slope
   is strictly below two.
7. Perform side-typed source and target forward-`dexp` round trips.

## Success and kill conditions

The lane advances only if the second-normal solve is rational,
coefficientwise finite, triangular with respect to lower normal layers, and
lowers the asymptotic source envelope without pushing the target rate back to
two.

It is killed by a nonzero lower-normal feedback, an infinite row, an
eventual gap in the multiplier semigroup, a target-degree tradeoff of rate
two or larger, or a higher-normal source layer that retains slope two.

Even a successful \(z^2\) solve does not determine the tail value.  The
successor would need a \(C\)-adic scheduling inequality across all normal
orders.

## Exact corrected outcome

The first calculation exposed the omitted target-lift condition.  After
removing every bare-\(Q\) column and rerunning on the polynomial-source
background, the higher shells and all displayed coefficients below are
unchanged; only the bounded radial remainder changes from weights two and
four to weights three and four.

The seed-level second-normal solve succeeds.  At target order six, the
unique \(Q^2C\) coefficient that removes the instantaneous \(r^8z^2\)
shell is

\[
\boxed{-\frac{2945}{132120576}}.
\]

It preserves the radial and first-normal seed layers and lowers the
instantaneous Hamiltonian degree at velocity cost seven from \(18\) to
\(16\).  Source/right and target/left forward-`dexp` round trips both pass.

The logarithmic countercheck kills the velocity-first normalization as a
sub-two argument.  At logarithmic order seven, BCH restores degree \(18\)
with complete top shell

\[
\frac{1186929}{2014104780800}u^9z^9
+
\frac{232227}{1611283824640}u^8z^{10}.
\]

The first term is radial and cannot be changed by a seed direction
divisible by \(C\).  Hence retuning \(Q^2C\) alone cannot remove the
complete shell.

The multiplier coverage itself behaves as predicted.  Through target order
ten, the finite gaps \(w=7,10\) appear and the available \(C\)-multiples
cancel every tested representable \(z^2\) radial degree.  Higher and
first-normal layers retain slope two.  The next live construction must
normalize the source logarithm row by row: ordinary cone directions remove
its radial shell first, followed by \(C\)-directions on the second-normal
shell.

That logarithm-first replay is now complete through target order ten.  At
target order six its \(Q^2C\) coefficient is

\[
-\frac{1210823}{64739082240},
\]

and it lowers logarithmic order seven from Hamiltonian degree \(18\) to
\(16\).  Across target orders five through ten the logarithmic degrees are

\[
\boxed{(16,16,20,20,21,26)}.
\]

The values \(20,26\) occur at the finite multiplier gaps.  Away from those
gaps, a negative-normal quotient appears with Hamiltonian degree
\(2n+3\) at target orders \(n=8,9,10\).  It is outside the direct image of
the current radial and \(C\)-normal diagonals and retains slope two.
Therefore the one-\(C\)-layer lane is a finite negative for a sub-two
claim.  Delayed controls from higher powers \(C^k\) remain a separate
all-order question.

## Successor after the complete one-\(C\) classification

The one-\(C\) finite-prefix problem is now closed, including every
positive power of \(D=4P^3+27Q^2\).  The governing new object is the
contact filtration

\[
(C^m)/(C^{m+1}),\qquad m\ge2,
\]

not another discriminant residue.

The first cone-compatible test prefix is

\[
Q^3C^2.
\]

Its cost-two source top is

\[
4(Q_0^3C_0^2)_{\rm top}
=-\frac{81}{4096}u^{13}z^{17}.
\]

Unlike the one-\(C\) zero-grade letters, this Hamiltonian has normal
order four.  Bracketing by it raises normal order by two.  Therefore a
surviving cost-three normal-six quotient would generate a different
triangular orbit rather than another fixed-normal \(\phi_2\) ray.

### First \(C^2\) discriminator

Compute the first delayed coefficient of \(Q^3C^2\) in the exact fixed
chart and normalize it successively by:

1. ordinary cone monomials on normal order zero;
2. cone-compatible \(C\)-multiples on normal order two;
3. cone-compatible \(C^2\)-multiples on normal order four.

The normalizers must use the complete canonical cone column at each
radial degree.  The discriminating outcomes are:

- a nonzero normal-six terminal, which opens an adjoint-orbit and
  current-column support calculation;
- exact cancellation through normal six, which moves the test to the
  first deeper radial deficit; or
- failure of a required \(C^2\) control to lie in the cone, which is
  itself a finite contact-filtration obstruction.

The local replay must reproduce the known one-\(C\) normal-four
quotients when \(m=1\) before its \(m=2\) output is used.  A finite
\(Q^3C^2\) coefficient is orientation evidence only; promotion requires
an all-\(m\) identity or an infinite Magnus orbit with complete current
freedom.

### Exact first-quotient scan and the pure-\(Q\) cancellation branch

The exact sparse replay through \(m=6\) corrects the proposed
normal-six expectation.  For the least cone-compatible \(Q\)-exponents,
complete current normalization through \(C^m\) leaves its highest row at
normal order \(2m\), not \(2m+2\).  For example,

\[
\begin{aligned}
[u^{14}z^{18}]\Omega_3(Q^3C^2)&=\frac{243}{32768},\\
[u^{22}z^{28}]\Omega_3(Q^5C^3)&=-\frac{3645}{8388608}.
\end{aligned}
\]

Across the checked boundary representatives the terminal radial exponent
is

\[
R=3b+2m+1.
\]

After division by the leading scale

\[
L_{a,b,m}
=\left(-\frac34\right)^a
 \left(-\frac14\right)^b
 \left(-\frac9{16}\right)^m,
\]

the normal-\(2m\) coefficient is consistent with

\[
-\frac b2\left(-\frac13\right)^a.
\]

For \(a=2\), the same radial exponent also carries a normal-\(2m+2\)
row with normalized coefficient \(-b/6\).

This first law is only a boundary-strip law.  Once the canonical
\(C^m\) control at radial degree \(R\) enters the cone, namely when

\[
b\ge \left\lceil\frac{3m+4}{2}\right\rceil,
\]

the pure-\(Q\) first quotient cancels completely in the full finite
polynomial replay.  The first held-out case is

\[
Q^5C^2.
\]

This repeats the mechanism already seen for \(Q^bC\), \(b\ge4\):
cost three is an exact current image, while cost four can still transfer
to a deeper normal row.

### Preregistered higher-contact cost-four discriminator

Compute the covariantly completed rows \(G_0,G_1,G_2\) for

\[
G_0=Q^bC^m
\]

and apply the complete ordinary and \(C^j\), \(1\le j\le m\), current
normalizers at costs three and four.  The replay must first reproduce
the symbolic one-\(C\) coefficient

\[
\frac{(-1)^b(9b+4)}{2^{2b+5}}
\]

on \(u^{3b+2}z^{3b+5}\).

The first new tests are \(Q^5C^2,Q^6C^2,Q^7C^2\).  The discriminator is:

- a nonzero common terminal row with a rational formula in \(b\), opening
  an all-\(b\) and then all-\(m\) response calculation;
- complete cost-four cancellation, moving the branch to the first later
  covariant row; or
- a residue whose normal order exceeds \(2m\), which is already outside
  the current image of a prefix having maximal contact depth \(m\).

No formula in \(m\) will be inferred from a finite scan.  Promotion
requires a symbolic generalized-binomial identity or a triangular
maximal-contact argument plus a nonterminating Magnus response.

### Stable higher-contact theorem

The covariant cost-four calculation has a stable cone range

\[
2b\ge a+3m+8.
\]

An exact total-degree-two polynomial-identity certificate, with ten
unisolvent \((a,b,m)\) rows and three held-out rows, gives

\[
\boxed{
[u^Sz^{S+2m+1}]V_4
=
\left(-\frac34\right)^a
\left(-\frac14\right)^b
\left(-\frac9{16}\right)^{m-1}
\frac{6a+9b+4m}{32}},
\qquad
S=2a+3b+2m.
\]

The same certificate shows this is the unique northeast corner of the
complete cost-four residual.  Its zero-grade cost-two letter is

\[
A_0u^Sz^{S+2m},
\qquad
A_0=
4\left(-\frac34\right)^a
 \left(-\frac14\right)^b
 \left(-\frac9{16}\right)^m.
\]

At adjoint depth \(k\), the terminal has

\[
\begin{aligned}
r_k&=S+k(S-1),\\
n_k&=2m+1+2(m-1)k,
\end{aligned}
\]

and its bracket multiplier, after removing \(A_0\), is

\[
2(S-m)k-S.
\]

The only algebraic zero is

\[
\frac{S}{2(S-m)}\in(0,1).
\]

Every fixed-chart factor \(P,Q,D,C\), in its \(D\)-adic leading basis,
obeys

\[
t\ge h\ge0
\]

between radial deficit \(t\) and extra normal order \(h\).  If a later
current column contains the terminal, its even-normal leading pivot is
above the terminal by grade margins

\[
(2t,\,2(t-h)).
\]

The terminal normal order is odd, so \(t=h=0\) is impossible.  The
unique-corner recursion therefore forces the current coefficient to zero
before the terminal equation.  This covers arbitrary later powers of
\(D\) and \(C\).

After orbit division the right-Magnus response is

\[
\phi_3(x)
=\frac{x}{e^x-1}\int_0^1t^3e^{t^2x}\,dt.
\]

Every odd adjoint depth survives, at costs \(6+4\ell\), and the limiting
source Hamiltonian rate is

\[
\boxed{2a+3b+3m-2}.
\]

The exact certificates are
[`gauge_cone_higher_contact_cost_four_symbolic.py`](gauge_cone_higher_contact_cost_four_symbolic.py)
and
[`gauge_cone_higher_contact_phi3.py`](gauge_cone_higher_contact_phi3.py).

### Preregistered \(D\)-adic stable extension

Equal-weight cancellation requires the basis

\[
P^aQ^bD^dC^m,\qquad
D=4P^3+27Q^2.
\]

Extend the covariant cost-four replay to \(d>0\), in the stable range

\[
2b\ge a+3d+3m+8.
\]

The predicted terminal has

\[
S=2a+3b+5d+2m
\]

and coefficient

\[
\left(-\frac34\right)^a
\left(-\frac14\right)^b
\left(\frac{27}{8}\right)^d
\left(-\frac9{16}\right)^{m-1}
\frac{6a+9b+18d+4m}{32}.
\]

The \(18d\) term is forced if the cost-four quotient acts on the
weight-six target discriminant through the same Euler symbol as on
\(P^3\) and \(Q^2\).  The first tests are \(d=1,2\) in all three
\(a\)-residue classes.  A different coefficient or exponent kills this
Euler-symbol extrapolation but leaves the \(D\)-adic stable layer as a
separate finite-dimensional polynomial-identity problem.

### Corrected \(D\)-adic stable outcome

The \(18d\) prediction is false.  The exact quadratic certificate gives

\[
\boxed{
[u^Sz^{S+2m+1}]V_4
=
\left(-\frac34\right)^a
\left(-\frac14\right)^b
\left(\frac{27}{8}\right)^d
\left(-\frac9{16}\right)^{m-1}
\frac{6a+9b+15d+4m}{32}},
\]

where

\[
S=2a+3b+5d+2m.
\]

Before the next contact normalization, the same radial degree has an
even companion whose coefficient after removal of the common leading
scale is

\[
\frac{d(d-1)}{64}.
\]

A single \(C^{m+1}\) row removes this companion and leaves the
normal-\((2m+1)\) terminal unchanged.  The unique-corner and current-pivot
argument then gives the same \(\phi_3\) response, now with limiting rate

\[
\boxed{2a+3b+5d+3m-2}.
\]

Using the admissibility-first covariant replay extends the same odd
terminal formula through every checked cone-slack class

\[
\ell=2b-a-3d-3m\ge4,
\]

even when the formal second covariant successor is not itself in the
cone.  Thus only \(\ell=0,1,2,3\) remain as transfer states.

### Preregistered boundary transfer graph

For a primary even-normal boundary terminal with

\[
r_0=S+1-2a,\qquad n_0=2m,
\]

its depth-\(k\) orbit has

\[
r_k=r_0+k(S-1),\qquad
j_k=\frac{n_k}{2}=m+(m-1)k.
\]

If it is canceled directly by a new \(D\)-adic current class

\[
P^{a'}Q^{b'}D^{d'}C^{j_k}
\]

whose new slack \(\ell'\) also lies in \(0,\ldots,3\), elimination of
\(b'\) gives the exact transition equation

\[
\boxed{
7a'+19d'+3\ell'
=
3a+19d+3\ell+2
+k(7a+19d+3\ell+11)}.
\]

The contact exponent \(m\) cancels from this equation.  The first graph
test will enumerate \(a,a'\in\{0,1,2\}\),
\(\ell,\ell'\in\{0,1,2,3\}\), and \(k\bmod19\), then impose
nonnegativity and parity of \(b'\).

The boundary lane is excluded if every infinite path is forced into
\(\ell'\ge4\), where the stable odd theorem applies.  It remains live if
there is a recurrent boundary component; in that case the successor must
carry exact amplitudes through the transition, because graph reachability
alone does not construct a canceling connection.

### Exact boundary graph outcome

The residue graph is recurrent, but recurrence is not the relevant
finite-prefix criterion.  Exact cost-four certificates give:

- for every \(d\ge1\) and every boundary state
  \(a\in\{0,1,2\}\), \(\ell\in\{0,1,2,3\}\), a nonzero odd corner with
  normalized coefficient

  \[
  -\frac{21a+57d+35m+9\ell}{36};
  \]

- at \(d=0\), seven of the twelve states have the same odd-corner
  obstruction;
- the only exceptional states are

  \[
  (a,\ell)\in
  \{(0,0),(0,1),(0,2),(0,3),(1,0)\}.
  \]

For an exceptional state, the primary even terminal has the
nonresonant \(\phi_2\) orbit recorded above.  Exhaustive solution of the
transition equation shows that every direct cancellation either has
\(d'>0\) or lands outside the exceptional state set.  No edge remains
inside exceptional \(d=0\).

This closes finite affine combinations by invariant contact depth.
Every nonzero polynomial coefficient has an intrinsic
\(\nu_C\), and a finite prefix has a maximum such depth \(M\).  A
depth-\(k\) cancellation of the primary orbit requires contact

\[
M+(M-1)k.
\]

For \(M>1\) and \(k\ge1\), this exceeds the maximum.  For \(M=1\), the
contact depth is unchanged, but the transition leaves the exceptional
set and encounters the odd-corner obstruction.  A \(k=0\) cancellation
also exits immediately.

Within a fixed contact and radial grade, the odd transfer is a nonzero
scalar.  Equal-grade affine cancellation therefore exposes the next
nonzero \(D\)-adic radial grade; the finite expansion cannot continue
indefinitely.

Hence every boundary monomial and every finite linear combination is
excluded.  Together with the stable and one-\(C\) theorems, no nonzero
finite polynomial contact prefix escapes.  The remaining lane is an
infinite coefficientwise-finite contact schedule.

### Adversarial combined-prefix audit: preregistration

The preceding passage uses a triangularity step that has not yet been
tested on a sum containing both an exceptional even-terminal class and a
robust odd-terminal class at the same source-radial grade.  Until that
test passes, the finite-linear-combination sentence is provisional.

Use the canonical \(D\)-adic basis

\[
P^aQ^bD^dC^m,\qquad
a\in\{0,1,2\},\quad d\ge0,\quad m\ge1,
\]

with cone condition \(a+3d+3m\le2b\).  Start both covariant rows from
zero and apply the fixed canonical current eliminator through one
contact level beyond the largest \(m\).  This defines one linear
cost-three/four quotient map on arbitrary finite sums, without making a
monomial-dependent admissibility choice.

For each finite weight/contact rectangle, assemble the complete sparse
cost-three and cost-four residuals as columns.  Independently normalize
several nontrivial linear combinations and require exact equality with
the corresponding column sums.

The finite-combination claim advances only if:

1. direct normalization is exactly linear on the tested combinations;
2. every tested canonical-basis rectangle has full column rank; and
3. mixed exceptional/robust equal-grade fibers have no kernel.

A single nonzero canonical prefix in the joint kernel kills the claimed
finite-prefix argument.  A rank defect caused only by truncating the
reported residual support also kills the harness.  Full rank on finite
rectangles is still diagnostic rather than an all-rectangle proof; the
symbolic target remains a filtration argument using
\(\ker(\mathbb Q[P,Q]\to\mathbb Q[r])=(C)\) and the injective Euler
operator

\[
\frac1{32}\left(3r\frac d{dr}+4m\right)
\]

on the first nonzero \(C\)-adic coefficient.

The first two rectangles pass:

\[
\begin{array}{c|c|c|c|c}
M&R_{\max}&\text{displayed columns}&
\operatorname{rank}_{\rm tgt}&\operatorname{rank}_{\rm src}\\ \hline
1&18&10&10&10\\
2&24&31&25&25\\
3&24&34&27&27
\end{array}
\]

The missing target dimensions in the last two rows are exact polynomial
identities involving higher powers of \(C\); no further kernel appears
in the source quotient.  A direct mixed-\(C\)-depth combination also agrees
with the sum of its separately normalized columns.  This supports the
linear quotient model and supplies the intended adversarial check, but
the all-rectangle conclusion still rests on the symbolic filtration.

### Boundary \(d=0\) symbolic audit: preregistration

The current boundary replay proves the positive-\(d\) rows by a
parity-separated polynomial identity in \((d,m)\), but its \(d=0\)
classification presently samples only three contact depths per parity.
Before treating the five exceptional families as uniform in \(m\),
upgrade that row to the same symbolic standard.

For every fixed \((a,\ell)\) and admissible parity, extract the proposed
primary even slot

\[
(r,n)=(S+1-2a,2m)
\]

at four contact depths.  The first three determine the degree-at-most-two
polynomial in \(m\); the fourth is held out.  The exceptional theorem
survives only if the slot remains the unique northeast leading row and
the solved coefficient has no positive integral zero of the required
parity.  A changed leading slot, a failed held-out value, or a permitted
root kills the uniform exceptional-orbit claim.

The location audit falsifies the proposed uniform
\(S+1-2a\) offset.  The exact offsets are

\[
\delta_{0,0}=2,\quad
\delta_{0,1}=\delta_{0,2}=\delta_{0,3}=1,\quad
\delta_{1,0}=2.
\]

The corresponding bracket factor is therefore

\[
2m\delta_{a,\ell}+2k(S-m),
\]

which has no nonnegative resonance.  The transition equation must be
replaced by

\[
7a'+19d'+3\ell'
=7a+19d+3\ell+2\delta_{a,\ell}
+k(7a+19d+3\ell+11).
\]

The quadratic coefficient prediction also fails for
\((a,\ell)=(0,1),(0,2),(0,3)\), with the same fourth-point discrepancy
\(1377/16\).  Four exact values instead give the preregistered cubic
candidates

\[
\begin{array}{c|c}
(a,\ell)&\text{normalized primary coefficient}\\ \hline
(0,1)&(3m+1)(153m^2+114m+73)/256\\
(0,2)&(3m+2)(153m^2+192m+112)/256\\
(0,3)&3(m+1)(153m^2+270m+169)/256.
\end{array}
\]

The fifth same-parity contact depth is now held out.  Agreement plus
negative discriminant of the quadratic factor proves nonvanishing on
positive \(m\) once the fixed-parity pivot pattern supplies the cubic
degree bound.  Disagreement kills these formulas and reopens the
exceptional classification.

### Boundary \(d=0\) symbolic audit: falsification

The first full-residual check fails before interpolation.  For

\[
(a,\ell,m,d)=(0,0,2,0),
\]

the proposed primary key is \((r,n)=(14,4)\), but the normalized cost-four
residual also contains

\[
[r^{15}z^4]V_4=-\frac{2349}{524288}.
\]

Thus \((14,4)\) is not the northeast leader.  The earlier transition graph
is an exact arithmetic statement about the proposed subleading orbit, but it
does not close the finite-prefix argument.  At this audit stage the
finite-polynomial conclusion was withdrawn pending classification of the
actual leading boundary module; the corrected outcome below restores it.

### Actual leading boundary module: preregistration

For each of the five exceptional \(d=0\) states and each permitted contact
parity, extract the northeast support of the complete cost-four residual,
without presupposing its radial coordinate.  Use three contact depths to fit
the radial law and normalized amplitude, with a fourth depth held out.

If the leader is even-normal, derive its density-\(z^2\) adjoint recurrence
and the cancellation Diophantine equation from the observed radial law.  Then
enumerate the corrected boundary graph with the same nonnegativity and parity
constraints as before.

The finite-prefix lane survives only if every leading coefficient is nonzero,
every resulting Magnus orbit is nonresonant, and every direct cancellation
leaves the corrected exceptional module or exceeds maximum contact depth.  A
zero amplitude, an integral bracket resonance, or a recurrent corrected
exceptional component keeps the finite-prefix escape open.

### Corrected leading boundary module: exact outcome

The held-out rows agree.  The exact radial offsets are

\[
\delta_{0,0}=2,\quad
\delta_{0,1}=\delta_{0,2}=\delta_{0,3}=1,\quad
\delta_{1,0}=2,
\]

and every primary key \((S+\delta_{a,\ell},2m)\) is the unique northeast
corner.  After removal of the common leading scale, the five amplitudes
are

\[
\begin{array}{c|c}
(a,\ell)&\text{normalized primary coefficient}\\ \hline
(0,0)&m(81m-46)/256\\
(0,1)&(3m+1)(153m^2+114m+73)/256\\
(0,2)&(3m+2)(153m^2+192m+112)/256\\
(0,3)&3(m+1)(153m^2+270m+169)/256\\
(1,0)&-(m+1)(81m+127)/256.
\end{array}
\]

The fifth same-parity contact depth agrees in every row.  The displayed
factors have no zero at an admissible positive \(m\).  The bracket
multiplier is

\[
2m\delta_{a,\ell}+2k(S-m)>0
\qquad(k\ge0),
\]

and direct cancellation obeys

\[
7a'+19d'+3\ell'
=7a+3\ell+2\delta_{a,\ell}
+k(7a+3\ell+11).
\]

The corrected residue enumeration has 11 or 12 admissible edges from
each exceptional state and no edge returning to exceptional \(d'=0\).
Consequently the maximum-contact induction survives the falsified
leader:

- for \(M>1\) and \(k\ge1\), a canceler requires contact
  \(M+(M-1)k>M\);
- a depth-zero cancellation, and every cancellation at \(M=1\), exits
  to a class with the current-independent odd terminal;
- fixed-contact/radial cancellation in that odd quotient is injective
  on the first nonzero \(D\)-adic symbol.

This restores exclusion of every nonzero finite polynomial contact
prefix.  An infinite coefficientwise-finite contact schedule remains
outside the result.
