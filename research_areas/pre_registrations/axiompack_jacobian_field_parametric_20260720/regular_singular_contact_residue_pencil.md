# Regular-singular contact residue and filtered extension

**Status:** exact restricted-lane mechanism; no all-order obstruction follows
without a completeness and filtration-preservation theorem

## Eigenquestion

The target-scaling lane \(K=a(s)PQ\) lowers the instantaneous source degree
from eleven to nine only by using

\[
a(s)=
\frac{4(2s^2-11s+6)}
     {7s(s-6)(s-4)}
=\frac1{7s}-\frac{17}{84}+O(s).
\]

Does this forced pole obstruct every all-order contact whose source logarithm
has uniformly bounded polynomial degree?

**No, not from the present hypotheses.**  It obstructs an \(s\)-adically
regular degree-nine connection in the declared one-dimensional target lane.
A bounded logarithmic contact can coexist through another connection lane,
and a singular stabilizer connection can coexist even with the identity
contact.

## Exact residue

Let \(F_s\) be the normalized quotient family and write

\[
\partial_sF_s
=X_{a(s)PQ}(F_s)+dF_s\,V_s.
\]

The exact top-shell equation is, up to a nonzero scalar factor,

\[
7s(s-4)(s-6)a(s)=4(2s^2-11s+6).
\]

The coefficient of \(a\) is \(s\) times a unit at \(s=0\), while the
right-hand side has value \(24\).  Therefore no
\(a(s)\in\mathbb Q[[s]]\) solves this equation, and its unique solution over
\(\mathbb Q((s))\) has residue \(1/7\).

If

\[
R=\operatorname{Res}_{s=0}V_s,
\]

then the replay proves

\[
\deg R=7,\qquad
dF_0R+\frac17X_{PQ}(F_0)=0.
\]

Thus

\[
\mathcal R=\left(\frac17X_{PQ},R\right)
\]

belongs to the infinitesimal contact stabilizer of \(F_0\).  Both components
of \(R\) satisfy the quotient lift ideals.  Its source linearization at the
origin is

\[
DR(0)=
\begin{pmatrix}
-1/7&12/7\\
0&1/7
\end{pmatrix},
\]

with eigenvalues \(\{-1/7,1/7\}\).

## Connection and residue invariance

Let \(\mathfrak c_s\) be the Lie algebra of allowed target/source contact
directions and

\[
L_s:\mathfrak c_s\longrightarrow T_{F_s}\mathcal M,\qquad
L_s(X,Y)=X\circ F_s+dF_sY
\]

the infinitesimal orbit map.  Its kernel

\[
\mathfrak h_s=\ker L_s
\]

is the contact stabilizer algebra.

A meromorphic contact connection

\[
C(s)=\frac{\mathcal R}{s}+C_0+C_1s+\cdots
\]

can map to the regular tangent \(\partial_sF_s\) only if

\[
L_0\mathcal R=0.
\]

Under a gauge \(g(s)\) that is regular and invertible at \(s=0\), the residue
changes only by

\[
\mathcal R\longmapsto\operatorname{Ad}_{g(0)}\mathcal R.
\]

The derivative term \(g^{-1}g'\) is regular and cannot remove a \(1/s\)
coefficient.  Hence a nonzero residue cannot be gauged to zero by a regular
gauge within the same connection category.

For the target \(PQ\)-scaling subgroup, the residue is the fractional class

\[
\frac17\pmod{\mathbb Z},
\]

up to the left/right sign convention.  A Laurent scaling \(s^k\) shifts a
residue only by an integer.  Integrating the singular coefficient instead
produces

\[
P\longmapsto s^{1/7}P,\qquad
Q\longmapsto s^{-1/7}Q.
\]

Analytically its linear monodromy has eigenvalues
\(e^{\pm2\pi i/7}\).  It is not a single-valued regular gauge on the
parameter disc.  A seven-fold ramification makes the fractional power
integral but still does not make both scaling factors units at the special
fiber.

This monodromy is an invariant of the **chosen regular-singular
connection**, not of the family \(F_s\) by itself.

## Residue transport and the saturation class

The gauge-invariant algebraic object is the failure of the filtered orbit
map to be saturated over the parameter DVR.

Let \(A=\mathbb Q[[s]]\), let \(E_D\) be a finite free module of all contact
directions allowed by a declared filtration, and let

\[
L(s)=L_0+sL_1+s^2L_2+\cdots:E_D\to T_D.
\]

For a regular tangent \(b(s)=b_0+b_1s+\cdots\), suppose a punctured solution
has the form

\[
c(s)=\frac r s+c_0+c_1s+\cdots .
\]

Comparing the pole and constant coefficients in \(L(s)c(s)=b(s)\) gives

\[
L_0r=0
\]

and

\[
b_0=L_0c_0+L_1r.
\]

Therefore

\[
[b_0]=[L_1r]\quad\text{in }\operatorname{coker}L_0.
\]

The class \([L_1r]\) is the first residue-transport obstruction.  If \(r\)
extends to a regular stabilizer section

\[
r(s)=r+sr_1+\cdots,\qquad L(s)r(s)=0,
\]

then

\[
L_1r=-L_0r_1
\]

and its transport class vanishes.  A nonzero class says precisely that the
special-fiber isotropy direction fails to transport inside the declared
filtered lane.

Equivalently, the class

\[
[b]\in\operatorname{coker}L
\]

is nonzero \(s\)-torsion: it vanishes after passing to
\(\mathbb Q((s))\) but not over \(\mathbb Q[[s]]\).  The elementary divisors
or Smith valuations of \(L\) over the DVR are invariant under regular changes
of source and target bases.  They are stronger and more intrinsic than a
particular meromorphic lift or its displayed residue.

In the one-dimensional scaling equation above, the elementary divisor is
exactly one factor of \(s\), and the normalized leading preimage is \(1/7\).

## When the pole would obstruct a bounded logarithmic contact

Fix a filtered contact category \(\mathcal G_D\).  A forced pole proves
nonexistence of a bounded logarithmic contact only if all of the following
hold:

1. **Lane completeness.**  \(E_D\) contains every target Hamiltonian and
   source direction that can occur in a contact with the claimed bound.
2. **Logarithmic-derivative closure.**  The logarithmic derivative of every
   \(A\)-regular bounded logarithm in \(\mathcal G_D\) lies in \(E_D(A)\).
3. **Regular exponential/log comparison.**  Every claimed formal contact
   produces a regular connection solving \(L(s)c(s)=\partial_sF_s\).
4. **Nonzero full saturation class.**
   \([\partial_sF_s]\neq0\) in the full
   \(\operatorname{coker}L\), not merely after projecting to a preferred
   target coordinate.
5. **All recursive transports.**  The first residue class and every
   higher-order lifting obstruction are computed in the same filtered
   module.

Under these hypotheses, a bounded logarithmic contact would supply a regular
solution, contradicting the nonzero saturation class.

The current calculation does not meet hypotheses 1 or 2:

- uniqueness is only within \(K=a(s)PQ\);
- a regular source-only connection already exists with degree eleven;
- a common raw degree cutoff is not closed under BCH or logarithmic
  differentiation.

Consequently the residue does not currently obstruct an all-order uniformly
bounded logarithm.

## Exact counterexamples

### A singular residue can coexist with a zero logarithm

Use the exact stabilizer pair \(\mathcal R\) above and take the constant
family \(F_s=F_0\).  Then

\[
C(s)=\frac{\mathcal R}{s}
\]

is a regular-singular contact connection because

\[
L_0\mathcal R=0.
\]

The same family also has the identity contact with target and source
logarithms identically zero.  Thus a nonzero regular-singular residue is not
an invariant obstruction of the family.

### A forced pole in a restricted lane can coexist with a regular full lane

Let \(A=\mathbb Q[[s]]\), \(T=A\), and

\[
L:Ae_1\oplus Ae_2\longrightarrow A,\qquad
L(xe_1+ye_2)=sx+y.
\]

For \(b=1\), the restricted lane \(Ae_1\) has the unique punctured solution

\[
x=\frac1s
\]

and no regular solution.  The full lane has the regular solution

\[
y=1.
\]

Taking the contact group to be abelian integrates the full regular
connection to a bounded linear logarithm, while the restricted connection
integrates to a logarithmic singularity.  This is the exact module pattern
of a low-degree preferred lane sitting inside a larger regular lane.

### A bounded logarithm need not have a uniformly bounded instantaneous field

For polynomial vector fields, BCH and logarithmic differentiation contain
brackets satisfying

\[
\deg[Y,Z]-1\leq(\deg Y-1)+(\deg Z-1).
\]

A logarithm whose coefficient degrees obey a triangular slope bound can
therefore have instantaneous coefficients of larger raw degree.  Absence of
a uniform-degree instantaneous connection does not contradict existence of
a bounded-log or slope-bounded contact unless the chosen filtration is
proved closed under logarithmic differentiation.

## Discriminating next tests

1. Replace the \(PQ\) lane by the exhaustive Hamiltonian/source
   \(C\)-normal window for the proposed filtered bound and compute the
   saturation or Smith data over \(\mathbb Q[[s]]/(s^N)\).
2. Starting from \(\mathcal R\), solve recursively for a regular stabilizer
   section \(r(s)\) in that same filtered lane.  The first failure is the
   transport class \([L_1r]\).
3. Compare the full saturation class with the independent triangular
   bounded-log search.  Agreement would connect the connection obstruction
   to logarithmic contact; disagreement identifies the missing lane.
4. Keep the fractional target monodromy as a connection invariant, but do
   not promote it to a family invariant without proving uniqueness of the
   full filtered connection.

## Kill conditions

The proposed all-order obstruction is killed by any one of:

- a regular solution in another Hamiltonian target direction;
- a bounded logarithm whose logarithmic derivative leaves the tested
  raw-degree lane;
- a regular transport of the residue stabilizer in the full filtered
  stabilizer bundle;
- vanishing of the full DVR saturation class after enlarging the lane;
- an allowed ramified or logarithmic gauge category in which the fractional
  monodromy is intentionally quotiented out.

Conversely, the bounded-contact route is killed only after the full filtered
orbit module has a nonzero saturation class and the log-to-connection closure
theorem has been proved.
