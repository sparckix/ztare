# Pure contact-zero radial/normal tail induction

## Eigenquestion

Let every positive-contact coefficient vanish.  For an arbitrary
coefficientwise-polynomial target connection in the complete contact-zero
lift algebra

\[
\mathcal L_0=\mathbb Q+(P^3,PQ,Q^2),
\]

does the paired source/target logarithm necessarily satisfy

\[
\max\left\{
\limsup_{q\to\infty}\frac{\deg Y_q}{q},
\limsup_{q\to\infty}\frac{\deg X_{\Omega_q^{\rm tgt}}}{q}
\right\}\ge2,
\]

even after an arbitrary finite supercritical prefix?  Or is there an exact
coefficientwise-polynomial pure contact-zero schedule with both rates below
two?

The known radial staircase gives the matching upper bound
\(\sigma_{\rm ct}\le2\).  This tick seeks the missing lower induction or the
opposite construction.  The least-positive-contact result cannot be invoked:
its defining least layer does not exist here.

## Governing identity and category

The moving affine chart gives

\[
P_s=A_s(r)+a_sz,
\qquad
Q_s=B_s(r)+b_srz,
\qquad
r=U_sz,
\]

and for every target Hamiltonian

\[
K(P_s,Q_s)=R_s(r)+zN_s(r)+O(z^2)
\]

the first two layers satisfy

\[
R_s'(r)=L_s(r)N_s(r),
\qquad L_s=L_0+sL_1.
\]

For a seed cusp weight \(w\), the Rees support bound is

\[
\deg_r[s^\delta z^j]K(P_s,Q_s)\le w+\delta-2j.
\]

The identity owner is therefore the complete radial/normal coefficient
complex, not a selected normalizer row.  Radial restriction owns the
weight-diagonal symbol; tangency owns the first-normal layer; the loss-two
Rees bound owns all higher normal layers; typed forward-`dexp` owns passage
from velocity to logarithm.

## Candidate critical grade

For a source monomial \(r^dz^j\) at parameter order \(n\), use

\[
\Gamma(r^dz^j s^n)=2d+j-2n.
\]

The radial staircase shows that row \(n\) can be reduced using target weights
at most \(n+6\), while its source Hamiltonian degree is at most \(2n+6\).
The lower induction should prove one of the following at every unbounded
sequence of rows:

1. a nonzero critical radial coefficient requires weight \(n+O(1)\), hence a
   same-order source payment of rate two;
2. radial cancellation transfers, through \(R'=LN\), to a nonzero
   first-normal critical coefficient with the same payment;
3. the first two layers cancel, and a higher-normal Rees leader survives at
   \(\Gamma\ge-O(1)\);
4. the cancellation uses a finite supercritical prefix whose complete
   adjoint cascade itself supplies rate at least two;
5. every critical coefficient vanishes, giving an exact schedule to test for
   rate strictly below two.

No finite prefix may be counted as a tail payment.  It may only enter as an
actor whose infinitely many distinct descendants are charged at their own
orders.

## Attack vectors and counterattacks

### A. Critical radial/normal diagonal — root lane

Derive the \(m=0\) weighted-face transition by projecting the complete
parameter coefficient equation to the largest radial weight and then to the
first normal layer.  The target cusp symbol is one-dimensional at every
weight \(w\ge5\), so the top radial map should be diagonal.  Use
\(R'=LN\) to exclude an independent first-normal cancellation and the
loss-two Rees estimate to route higher normal terms.

Counterattack / kill condition: a same-grade kernel survives both radial and
first-normal projection; the critical coefficient is not forced by the
normalized source-only connection; or a higher-normal column returns to the
same grade without a rate-two payment.

### B. Finite supercritical-prefix cascade — adversarial lane

Classify the highest slope-two Newton face of a finite radial connection.
Radial Hamiltonians commute, so their complete action on an odd-normal
terminal has the exact form

\[
\exp(-\operatorname{ad}_{F_s})\bigl(z^ng(r)\bigr)
=\sum_{k\ge0}\frac{(-1)^k}{k!}
\prod_{i=0}^{k-1}(n-2i)
z^{n-2k}(F_s'(r))^kg(r).
\]

For odd \(n\), the scalar product never vanishes.  The initial form of
\((F_s')^k\) is the \(k\)-th power of the initial form in the integral domain
\(\mathbb Q[s,r]\).  Determine whether the actual source-only background has
a canonical odd-normal terminal on which this gives an injective
occurrence-to-payment map.

Counterattack / kill condition: the actual background has no such terminal;
mixed radial letters cancel the tied Newton face; nonradial contact-zero
letters reach the same descendant; or the occurrence order grows faster than
the source degree so the cascade is subcritical.

### C. Target parity algebra and mixed-prefix collisions — independent lane

On the cusp, use the even/odd families

\[
E_a=P^a,
\qquad O_a=P^aQ,
\]

with

\[
[E_a,E_c]=0,
\quad [O_a,E_c]=-cE_{a+c-1},
\quad [O_a,O_c]=(a-c)O_{a+c-1}.
\]

Classify finite positive-grade prefixes modulo the radial abelian ideal and
ask whether mixed words can cancel the radial Newton-face descendants without
creating a target-degree or source-normal payment.

Counterattack / kill condition: an infinite path remains in the critical
quotient with bounded target degree and source grade; parity fails under the
complete moving pullback; or two distinct words share the same occurrence
identity and cancel for a rational coefficient choice.

### D. Exact below-rate-two schedule search — independent construction lane

Treat the radial staircase as a recurrence with free higher-normal rows.
Compile the exact parameter fiber at increasing orders and weights, but use
the finite windows only to infer a candidate symbolic recurrence.  If the
critical diagonal vanishes, solve the resulting radial/normal equations and
apply typed source and target forward-`dexp` replay.

Counterattack / kill condition: a candidate schedule requires infinitely many
terms in one parameter coefficient, fails polynomial source divisibility,
uses the omitted bare \(Q\), disagrees between source and target conventions,
or has hidden rate two after logarithmic integration.

## Proof skeleton

1. Factor the contact-zero coefficient complex by exact lower-row
   velocity/logarithm boundaries.
2. Choose the maximum \(\Gamma\)-grade among the current radial, first-normal,
   and higher-normal blocks.
3. Prove that the current-row symbol is triangular: radial first,
   tangency-determined normal one second, strict Rees descent thereafter.
4. If the current diagonal is nonzero at infinitely many rows, bind each row
   to a same-order source or target rate witness.
5. If only finitely many current diagonals are nonzero, classify the finite
   prefix.  A nonzero highest Newton face acting on the first odd-normal
   background terminal must generate infinitely many injectively owned
   descendants of rate at least two.
6. If the finite prefix action is nil in the critical quotient, remove it by
   an exact boundary and restart at the next prefix grade.
7. Well-founded descent must end in a paid branch or an explicit recurrence
   with every critical block zero.  In the latter case, solve and replay the
   schedule and compute both logarithmic rates.

## Recurrence and capability amnesia check

The semantic capability retriever was unavailable and lexical fallback was
used.  It surfaced the existing `compile_filtered_symbol_cokernel`, the
Filtered Obstruction Compiler basis lifecycle, `SAME-CARRIER-PACKING-GATE`,
and `FINITE-PREFIX-SELECTION-GATE`.  The new work must extend those identity
owners; it must not create a second quotient, reachability, or no-rebilling
engine.

Existing campaign components already cover:

- the radial staircase upper construction and exact two-layer identity;
- finite coupled parameter fibers through order six;
- pure row-zero top-weight probes at orders five and six;
- the all-order radial-word formula on an odd-normal terminal;
- the node-versus-cusp Rees dichotomy with its finite-prefix loophole; and
- the least-positive-contact induction for every \(m\ge1\).

They do not supply the \(m=0\) complete critical-row induction.  Finite
stabilization, wordwise nonvanishing without collision control, and the Rees
node theorem without finite-prefix classification are recurrence aliases and
must not be reported as the missing result.

## Intended formal surface

Formalization begins only after the pencil transition is fixed.  The minimal
arithmetic surface should check:

- additivity of \(\Gamma\) under the radial/odd-normal bracket;
- nonvanishing of odd-normal falling products;
- injectivity of affine occurrence orders;
- positivity of the derived source-degree/order slope;
- the triangular radial/normal grade inequalities; and
- the exact exceptional-set classification, if any.

The symbolic adapter must own the Jacobian-specific two-layer formulas and
the complete coefficient map.  The reusable compiler should receive only a
typed finite induction graph plus asymptotic occurrence/payment witnesses.

## Frozen success and stop rules

Success requires one of two exact outcomes:

1. an all-index induction proves symmetric logarithmic limsup at least two
   for every coefficientwise-polynomial pure contact-zero schedule, including
   arbitrary finite supercritical prefixes; or
2. an explicit coefficientwise-polynomial pure contact-zero schedule has
   both logarithmic rates strictly below two and passes arbitrary-depth typed
   replay.

The tick cannot stop on a larger finite window, a single nonzero Lie word, an
upper construction, or unbounded degree without a quantitative rate.  A
decisive kill of one attack vector redirects to the surviving vectors rather
than ending the campaign.

## Exact counterattacks and corrected carrier

The first-normal radial-word proposal fails in the complete coupled block.
At the seed, both the source-only pair and every target pullback satisfy

\[
R'=(2-3r)N.
\]

Consequently the normal-minus-one bracket face is

\[
N_0R'-R_0'N=0.
\]

This cancels the radial/background path against the
normal-companion/radial-background path on the same Newton coordinate.  It
is a polynomial identity, not an exceptional amplitude.  The target parity
algebra has an additional exact Euler family

\[
H_d=\lambda P^{d+1}Q+\mu P^d,
\qquad [H_d,PQ]=dH_d,
\qquad \operatorname{ad}_{H_d}^2(PQ)=0,
\]

so a blanket rule charging every finite critical prefix is false.  A finite
logarithm can also have an infinite forward-`dexp` velocity tail while its
own higher logarithmic coefficients vanish.

After the normalized row-zero cancellation

\[
K_0=-P^3/36-Q^2/4,
\]

the row-one radial and first-normal blocks can be removed by an exact current
contact-zero row, but a normal-two/normal-three compatibility class remains.
Put

\[
L=2-3r,
\qquad
\Delta(H)=L^2N_3-LN_2'+2N_2
\]

for (H=\sum_jz^jN_j(r)).  The exact seed cusp identity

\[
C(P_0,Q_0)=-\frac{z^2}{16}(L^2-8z)
\]

implies

\[
\Delta\bigl(C(P_0,Q_0)G(P_0,Q_0)\bigr)=0
\]

for every polynomial (G).  This is the complete same-row kernel after the
radial restriction is fixed.  Conversely, a target radial leader of cusp
weight (w\ge5) has the nonzero diagonal

\[
[r^{w-4}]\Delta
=\frac{w(w-2)(w-3)}9[r^w]R.
\]

Thus a (C)-multiple can move a representative between normal orders two
and three but cannot erase its compatibility class.

## Exact critical recurrence reduction

Set

\[
x=sr,
\qquad \eta=z/r^2.
\]

The entire slope-two initial form of the family is carried by two finite
polynomials (P_{\rm crit}(x,\eta)) and
(Q_{\rm crit}(x,\eta)).  The deterministic replay
[`gauge_pure_contact_zero_delta_critical_recurrence.py`](gauge_pure_contact_zero_delta_critical_recurrence.py)
extracts them from the exact family rather than fitting rows.  It reduces
radial normalization to one scalar triangular recurrence: at row (n), the
new diagonal is the seed radial coefficient of the canonical cusp weight
(n+6), and is nonzero.

Once radial and first-normal critical terms are removed, normal order at
least four is a Lie ideal.  The quotient through normal three is the exact
semidirect algebra

\[
\begin{aligned}
[r^az^2,r^bz^2]&=2(b-a)r^{a+b-1}z^2,\\
[r^az^2,r^bz^3]&=(2b-3a)r^{a+b-1}z^3.
\end{aligned}
\]

If (A_n) and (B_n) are the logarithmic normal-two and normal-three
leaders at order (n+1), then

\[
\boxed{\delta_n=(3n+8)A_n+9B_n}
\]

is exactly ([r^{n+2}]\Delta).  The reduced typed Magnus/forward-`dexp`
round trip passes.  A category audit showed that the old full-cone staircase
ceases to represent the pure quotient after row three.  The corrected
recurrence uses the unique parity section

\[
P^{w/2}\quad(w\text{ even}),
\qquad
P^{(w-3)/2}Q\quad(w\text{ odd}).
\]

Its first corrected values after the shared three rows are

\[
-\frac{155}{258048},\quad
-\frac{4237}{37158912},\quad
-\frac{43177}{2427715584},\quad
-\frac{20117}{6242697216}.
\]

Every value through row fifty is nonzero; from row eight onward the signs
alternate in the computed window.  These facts are diagnostics rather than
an induction.

The kernel of the leading functional has a useful intrinsic form.  In the
critical chart the logarithm is

\[
\Omega_{\rm crit}=rz^2A(x)+\frac{z^3}{r}B(x),
\qquad x=sr.
\]

The normal-two component is the Witt algebra

\[
[A,C]=2x(AC'-A'C),
\]

and it acts on the normal-three component by

\[
\rho(A)B=2xAB'-3xA'B-5AB.
\]

The representation identity holds exactly.  With basepoint \(h=1/9\), put

\[
J=B-\rho(A)(h)=B+\frac{3xA'+5A}{9}.
\]

Then the compatibility series is exactly

\[
\Delta(\Omega_{\rm crit})=9J.
\]

Thus the obstruction is a split tensor-density module over the critical
Witt algebra.  An infinite sequence of critical kernel controls already pays
source rate two.  Therefore a below-rate-two counterexample can use only a
finite critical kernel prefix; all later controls must be strictly
subcritical.

## Exact algebraic parity connection

The pure parity section is a rank-two module over

\[
y=x^2P_{\rm crit}(x,0)=\frac{x^2(x-6)}8.
\]

Its local deck involution is

\[
\iota(x)=\frac{6-x-\sqrt{-3(x+2)(x-6)}}2.
\]

Solving the two parity coordinates in this quadratic function field gives
the complete normal-two instantaneous connection

\[
A_{\rm vel}(x)=R(x)+S(x)\sqrt{-3(x-6)(x+2)},
\]

where

\[
R(x)=\frac{21x^6-124x^5+456x^4-2048x^3-6768x^2+22464x+44928}
{896x^3(x-4)(x^2-4x-8)}
\]

and

\[
S(x)=\frac{(x-6)(x+2)(7x^3-42x^2+624)}
{896x^3(x-4)(x^2-4x-8)}.
\]

At the nearest branch point \(x=-2\),

\[
\frac{-3(x-6)(x+2)}{x+2}\bigg|_{x=-2}=24,
\qquad
\frac{S(x)}{x+2}\bigg|_{x=-2}=-\frac{25}{1344}.
\]

Hence the connection has a nonzero Puiseux term of order \(3/2\), proving
that its velocity series is infinite.  The companion replay is
[`gauge_pure_contact_zero_parity_algebraic_connection.py`](gauge_pure_contact_zero_parity_algebraic_connection.py).
This singularity does not alone prove an infinite Magnus logarithm: a finite
logarithm may have an infinite forward-`dexp` velocity.  The next lemma must
For the prefix-free connection that Magnus passage is now exact.  If \(F\)
is the inverse radial holonomy, then

\[
\frac{F'}F=\frac1{x(1+2xA_{\rm vel})}.
\]

The velocity branch integrates to a nonzero \(u^{5/2}\) term in \(F\), where
\(u=x+2\).  If a polynomial Witt generator \(f\) existed, Julia's equation
\(f(F)=F'f\) would first force \(f(-2)=0\).  If that root had multiplicity
\(m\), comparison of the first fractional coefficient would give
\(m=5/2\), which is impossible.  The exact coefficient audit and typed
Magnus orientation check are in the companion Witt Puiseux replay.  Thus the
canonical prefix-free critical Witt logarithm is infinite by an all-index
argument.

The finite critical orbit can be followed through the group action.  If a
below-rate-two pair had finite critical source and target logarithms, the
inverse radial holonomy would factor as a product of two polynomial Witt
flows tangent to the identity.  At a finite branch point such a product is
analytic unless it passes through infinity.  In the latter case, comparison
of the two polynomial time coordinates shows that a nonzero linear term
forces equal degrees.  If the normalized generators first differ in degree
(e\ge2), their first fractional exponent is

\[
1+\frac{d-e}{d-1}\in(1,2).
\]

If they never differ, they are proportional and reduce to the one-flow
Julia case.  Neither branch produces the canonical first fractional
exponent (5/2).  Thus the two-sided finite critical special fiber is now
excluded by an all-degree argument.

### Two-sided finite-log factorization residual

The correct critical special-fiber statement is a group factorization
problem.  If both logarithmic tails had rate strictly below two, their Rees
specializations would be finite polynomial Witt generators (f) and (g).
After the positive-grade and strictly negative-grade pieces are removed by
the filtered induction, the canonical inverse radial holonomy (F) would
have to satisfy, up to the already fixed orientation,

\[
F=\exp(g\partial_x)\circ\exp(f\partial_x)(x).
\]

This is stronger than asking whether (F) itself is one polynomial flow,
which is the prefix-free Julia theorem above.  An arbitrary finite
supercritical prefix does not yet lie in this regular critical special
fiber: its Rees specialization is polar and must first be removed or
charged.

The remaining discriminating test is therefore:

1. choose the maximum positive Rees grade of a finite polar prefix;
2. compile its complete seed-cusp graph class, including the strict scalar
   obstruction and the cusp-stabilizer ambiguity;
3. prove that each exhaustive outcome is a same-order rate-two payment or
   an exact inverse-flow removal to a strictly lower positive grade;
4. iterate until the now-closed critical special fiber is reached.

Success is a well-founded polar-prefix induction with a bound on every
uncharged descent.  A bounded pole-depth solve, or a seed quotient without
the moving-family BCH cost, remains partial.

The corrected all-index residual is now the polar descent, rather than a
finite critical recurrence.  For a finite prefix, let (h>0) be its maximum
positive Rees grade.  Prove an exhaustive transition at grade (h): a
source or target coefficient is paid at rate at least two, or an exact
inverse-flow graph boundary removes the grade and decreases (h).  Finite
descent then reaches the critical two-flow obstruction above.  The only
opposite outcome is an exact polar stabilizer cycle with no paid descendant;
such a cycle must be replayed as a candidate below-rate-two contact rather
than dismissed by a finite jet.

### Preregistered maximal-polar-face test

The next test works in the one-variable Witt group rather than charging a
forward-`dexp` velocity.  Write the normal-two logarithms after (x=sr) as
Laurent-Rees series.  A positive face of grade (h) has the form

\[
s^{-h}a(x),\qquad a\in x\mathbb Q[x].
\]

If both logarithmic limsups are strictly below two, only finitely many
positive faces occur.  At the maximal grade, the two factors have opposite
faces because their product is critical.  Put (X=s^{-h}a).  In the quotient
where terms containing two non-(X) letters vanish, the latter letters form
an abelian (\operatorname{ad}_X)-module.  For factor logarithms
(-X+C) and (X+B), the exact semidirect product law is

\[
Z=\frac{1-e^{-\operatorname{ad}_X}}
        {\operatorname{ad}_X}(B+C),
\qquad
B+C=\frac{\operatorname{ad}_X}
           {1-e^{-\operatorname{ad}_X}}Z.
\]

The inverse series has nonzero coefficients at every positive even depth:

\[
\frac{z}{1-e^{-z}}
=1+\frac z2+\sum_{k\ge1}
  \frac{B_{2k}}{(2k)!}z^{2k}.
\]

Let (d) be the least (x)-degree of (a), and subtract a scalar multiple of
(a) from the first defect until its least degree differs from (d).  Then
the least term of every iterated Witt bracket
(\operatorname{ad}_a^k Z) is nonzero.  Its parameter order and source
degree have slopes

\[
d-h\quad\text{and}\quad 2d,
\]

so its limiting source rate is

\[
\frac{2d}{d-h}>2.
\]

The preregistered exhaustive outcomes are therefore:

1. a noncentral polar or critical defect gives infinitely many same-factor
   logarithmic payments along the even adjoint orbit;
2. every defect through critical grade centralizes (a), hence is a scalar
   multiple of (a); the polar scalar flows cancel and descent lowers the
   maximal grade;
3. at critical grade the entire canonical logarithm is a scalar multiple of
   (a), reducing the holonomy to the already excluded one-flow case.

The discriminating replay must verify the semidirect exponential identity,
the least-term nonvanishing recurrence, the exact order/degree conversion,
and the centralizer reduction.  Kill this route if lower positive faces can
contribute to the same *maximal-grade, least-(x)-degree* orbit, if the
normal-two factorization does not descend to the declared semidirect
quotient, or if an even inverse-series coefficient vanishes in
characteristic zero.  No finite bracket window counts as the result.

### Outcome of the plain-Witt adapter test

The universal maximal-face calculation passes, including the invariant

\[
\chi=he+d\nu,
\]

the exact semidirect transfer, and the all-index fact that
(zP(z)/(1-e^{-z})) is nonpolynomial for every nonzero polynomial (P).
The first Jacobian adapter nevertheless hits its declared kill condition.
The normal-two image of a target control is not invariant under the plain
Witt bracket after radial normalization: its omitted normal-three companion
contributes to the bracket.  In ordinary target degree, an infinite target
Witt orbit can also be cheaper than rate two, so charging its induced source
degree would be invalid.

The fail-closed compiler therefore rejects
(`semidirect_newton_quotient_applies=False`) rather than certifying the
unrestricted result.  The corrected invariant object is the already derived
split pair

\[
(A,J),\qquad
J=B+\frac{3xA'+5A}{9},
\qquad
\rho(A)J=2xAJ'-3xA'J-5AJ.
\]

Here every same-row target-kernel control has (J=0), and the (J)-coordinate
is a source-paid quotient.  The maximal polar induction must be rerun in
this tensor-density module.  Its monomial orbit has the exact recurrence

\[
\rho(x^d)^k(x^e)
=\left(\prod_{i=0}^{k-1}
  \bigl(2e+(2i-3)d-5\bigr)\right)x^{e+kd}.
\]

There is at most one resonant factor.  A nonresonant Newton face supplies the
same strict rate (2d/(d-h)>2); a resonant finite orbit is an uncharged
boundary that must enter the descent rank rather than being counted as a
tail payment.  The remaining proof obligation is to show that repeated
removal of these finite generalized-kernel faces terminates at the critical
two-flow obstruction, or else produces a nonresonant (J)-face.

### Preregistered tensor-density infinitude test

For a fixed nonzero polynomial (A\in x\mathbb Q[x]), the locally nilpotent
subspace of

\[
\rho(A)=2xA\partial_x-(3xA'+5A)
\]

inside (x\mathbb Q[[x]]) is finite-dimensional.  At the least monomial
(a_dx^d), a terminating chain must hit the unique kernel exponent

\[
e_*=\frac{3d+5}{2},
\]

after finitely many shifts by (d); hence only the positive exponents
(e_*-jd) can start such a chain.  Higher terms of (A) determine the rest of
each chain triangularly and do not create new starting exponents.

The next discriminating test is to construct the exact algebraic
normal-three instantaneous connection, form

\[
J_{\rm vel}=B_{\rm vel}
+\frac{3xA_{\rm vel}'+5A_{\rm vel}}9,
\]

integrate the associated tensor-density holonomy, and prove that its Magnus
logarithm (J_{\log}) is not a polynomial.  A nonzero fractional local term,
or an exact differential relation reducing polynomial (J_{\log}) to the
already excluded polynomial Witt logarithm, is sufficient.  This result,
together with finite-dimensional local nilpotence, would force a
nonresonant (J)-face for every polar actor.

Kill conditions: (J_{\log}) is polynomial; the canonical group endpoint
lies entirely in the (J=0) stabilizer graph; the normal-three algebraic
connection does not match the exact recurrence; or the locally nilpotent
subspace admits infinitely many independent starting exponents.  Checked
nonzero (\delta_n) rows alone do not pass this test.

### Outcome: exact critical module and maximal-face induction

The algebraic normal-three replay requires one indexing distinction.  If
(a,b,j) are the row-indexed coefficient functions, while the intrinsic
tensor coordinates are shifted by one radial power, then

\[
\widehat A=xa,\qquad \widehat B=xb,\qquad \widehat J=xj.
\]

Consequently the two equivalent split formulas are

\[
\widehat J=\widehat B+
\frac{3x\widehat A'+5\widehat A}{9},
\qquad
j=b+\frac{3xa'+8a}{9}.
\]

Using (+5) directly on the unshifted row series fails the typed BCH/ODE
round trip.  The corrected (+8) formula passes it exactly.

Move the complete Witt logarithm to the target-kernel factor:

\[
\exp(A,J)=\exp(A,0)\exp(0,K).
\]

The residual subgroup is abelian.  For the right velocity, its row-indexed
critical series (k) satisfies

\[
\boxed{
x(1+2xa)k'
=j+(6xa+3x^2a'-1)k.}
\]

Both (a) and (j) belong to the exact quadratic field
(\mathbb Q(x,\sqrt{36+12x-3x^2})).  If (k) were rational, separation into
rational and radical rows would give two linear equations for ((k',k)).
Their determinant is nonzero, so Cramer's rule gives a unique rational
candidate.  Exact differentiation of that candidate disagrees with the
forced (k') row; the compatibility numerator is nonzero.  Hence (k) is not
rational and, in particular, is not polynomial.  Its critical source
logarithm has infinite support and limiting rate two.

For a maximal positive Rees monomial

\[
X=s^{-h}x^d,\qquad h>0,\quad d>h,
\]

the tensor orbit is

\[
\rho(x^d)^k(x^e)=
\left(\prod_{i=0}^{k-1}
  (2e+(2i-3)d-5)\right)x^{e+kd}.
\]

A terminating positive starting exponent must obey

\[
2e=(3-2i)d+5.
\]

Since (e,d\ge1), this forces (i\le3); there are at most four resonant
starting exponents, uniformly in (d).  The other first-defect terms on the
finite maximal face occupy only finitely many Newton classes.  Infinite
support of (K) therefore supplies a nonzero coefficient outside both finite
sets.  Its invariant

\[
\chi=he+d\nu
\]

separates the full orbit from every tied defect.  The inverse semidirect
transfer (z/(1-e^{-z})) has a nonzero coefficient at every positive even
depth, so this orbit produces infinitely many nonzero factor coefficients.
The target factor has (J=0), leaving the complete module orbit on the source
side.  Its order and source-degree increments are

\[
d-h\quad\hbox{and}\quad 2d,
\]

and its limiting rate is therefore

\[
\boxed{\frac{2d}{d-h}>2.}
\]

Thus a strict below-two pair has no positive Rees face.  Finite maximal-face
descent reaches the separately certified critical two-flow terminal.  This
closes the arbitrary-finite-prefix induction for the complete pure
contact-zero category.  It does not yet settle positive-contact corrections
coupled to an arbitrary contact-zero backbone.

The exact replays are
[`gauge_pure_contact_zero_tensor_density_holonomy.py`](gauge_pure_contact_zero_tensor_density_holonomy.py)
and
[`gauge_pure_contact_zero_polar_tensor_induction.py`](gauge_pure_contact_zero_polar_tensor_induction.py).

## Radial-normalization audit of the finite jet counterattack

The finite correction

\[
K_*=-\frac{13}{648}P^3+\frac1{36}PQ
\]

annihilates the value and first \(\tau=3r-2\) jet of \(\Delta\), but it is
not a perturbation of an already radial-normalized row.  Directly,

\[
K_*(P_0,Q_0)|_{z=0}
=\frac{r^3(3r-4)(117r^2-240r+136)}{41472}\ne0.
\]

Thus it trades the ramification jet for new radial and first-normal
obligations.  Once the radial restriction is prescribed, any two target
lifts differ by \(C G\), and the exact identity \(\Delta(C G)=0\) makes
the normalized \(\Delta\) coordinate lift-independent.  This rescues the
coupled current-row quotient while rejecting the stronger claim that
\(\Delta\bmod(3r-2)^2\) is invariant before radial normalization.

The remaining prefix quantifier is temporal rather than same-row: a finite
critical kernel logarithm can act on later \(\Delta\)-rows through the
semidirect Magnus representation.  The induction must prove that this
finite action cannot make the normalized quotient sequence eventually
zero, or exhibit the prefix that does.
