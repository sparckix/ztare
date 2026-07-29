# Weighted lifts across coefficient fields

**Status:** active mathematical pencil for
`H-AXIOMPACK-JACOBIAN-FIELDS-20260720-04`

## Eigenquestion

What is the smallest field-independent mechanism behind the weighted-lift
Keller maps, and which conclusions may pass between `Q` and `GF(p)`?

## Replace the integral by algebraic mechanism

Let `K` be a field. Choose units `b,c : K` and polynomials `p,q : K[w]`
such that

\[
p(0)=q(0)=0,\qquad p(1)=-c,\qquad q(1)=-1,
\qquad c q'(w)=w p'(w).
\]

Put

\[
\kappa=p'(1)/c,\qquad
a=-\frac{1+\kappa}{2+\kappa},
\]

with `2 + kappa` a unit. For

\[
v=xy,\quad t=x^2z,\quad u=1+v,\quad
\gamma=1+av+bt,\quad w=u\gamma,
\]

define

\[
\beta=c+\frac{p(w)}{\gamma},\qquad
\alpha=u+\frac{q(w)}{\gamma^2},\qquad
F_{p,q}(x,y,z)=\left(\frac{\alpha}{x^2},
\frac{\beta}{x},x\gamma\right).
\]

These displayed quotients are polynomial:

- `p(0)=0` makes `p(u gamma)/gamma` polynomial;
- `c q' = w p'` and `q(0)=0` give `q'(0)=0`, so
  `q(u gamma)/gamma^2` is polynomial;
- `p(1)=-c` removes the constant term of `beta`;
- `q(1)=-1` removes the constant term of `alpha`;
- the definition of `a` removes the forbidden term linear in `v` from
  `alpha`.

Set

\[
P=\beta\gamma=c\gamma+p(w),\qquad
Q=\alpha\gamma^2=w\gamma+q(w).
\]

Then

\[
\det\frac{\partial(P,Q)}{\partial(w,\gamma)}=-c\gamma,
\qquad
\det JF_{p,q}=bc.
\]

The inverse equation is also algebraic. Define

\[
R(w)=wp(w)-cq(w).
\]

The differential relation gives `R' = p`, without selecting an
antiderivative, and every inverse branch satisfies

\[
R(w)=wP-cQ.
\]

Over characteristic zero this recovers
`R(w) = integral_0^w p(s) ds`. The `(p,q)` presentation is the canonical
cross-characteristic object because it remains meaningful when coefficient
division by an exponent is unavailable.

## Coefficient exceptional locus

For

\[
p(w)=\sum_{i\ge1}p_iw^i,\qquad
q(w)=\sum_{j\ge1}q_jw^j,
\]

the differential relation reads

\[
c(i+1)q_{i+1}=i p_i.
\]

Thus a procedure that constructs `q` from `p` by division is undefined in
characteristic `ell` whenever `ell | (i+1)` and the right side survives.
Terms in `w^{ell k}` also lie in the derivative kernel, so `q` is not unique
unless a Frobenius-kernel gauge is declared. Carrying both `p` and `q` avoids
that hidden choice; the host checks their relation exactly.

There is also a denominator-free chart that is better suited to sibling
fields. After scaling `c` to one, write

\[
p(w)=2w-3w^2+\sum_{k=1}^{d-2}\theta_k\Psi_k(w),
\qquad
\Psi_k(w)=w(1-w)\big((k+2)(k+3)w^k-6\big).
\]

Every basis vector has both the endpoint and zero-moment conditions built
in. Its integral and its contribution to `q = wp-R` have integer
coefficients:

\[
R_k=(k+3)w^{k+2}-(k+2)w^{k+3}-3w^2+2w^3,
\]

\[
Q_k=(k+1)(k+3)w^{k+2}-(k+2)^2w^{k+3}-3w^2+4w^3.
\]

Consequently the fixed identities specialize coefficientwise without
formal integration or exponent division. A small prime may still collapse
the rank or degree of this parameter chart; that is a chart exception, not
an undefined reduction of a fixed integral polynomial pair.

For a fixed rational instance, exceptional behavior is typed rather than
collapsed into one `bad_prime` flag:

1. **undefined reduction:** a coefficient or witness denominator vanishes;
2. **Keller degeneration:** `b`, `c`, or
   `D = p'(1)+2c = sum (i-2) A_i` vanishes;
3. **chart-rank loss:** the denominator-free basis ceases to parameterize the
   same coefficient space;
4. **fiber-degree or separability loss:** a declared leading coefficient or
   the relevant resultant/discriminant vanishes;
5. **collision loss:** a factor of `prod_(i<j)(w_i-w_j)` or
   `prod_i gamma_i` vanishes.

Outside the candidate-specific finite set, reduction preserves the
polynomial identities, Jacobian constant, declared degree, separability, and
displayed collision. A receipt must name those five checks separately. It
does not carry a finite-field verdict back to characteristic zero.

## Directional transport logic

For the same frozen rational assignment and a good prime:

- failure of an equality modulo `p` refutes that rational equality;
- satisfaction of an equality modulo `p` is only a modular survivor;
- satisfaction of a disequality modulo `p` certifies the corresponding
  rational disequality;
- failure of a disequality modulo `p` is inconclusive over `Q`;
- ordered relations have no field-independent reduction and must be rejected
  by the prime-field capability.

This relation-sensitive table belongs in the reduction receipt. A blanket
`GF(p) -> Q` verdict is unsound.

Modular unsatisfiability transfers only for a frozen finite rational chart
when every candidate in that chart has a certified specialization into the
modular problem. It does not prove that an ambient rational variety is empty.

## First nontrivial coefficient chart

With `c=1` and a cubic seed

\[
p_t(w)=a_1w+a_2w^2+tw^3,
\]

the endpoint and zero-integral equations give

\[
a_1=2+t/2,\qquad a_2=-3-3t/2,
\qquad \kappa=-4+t/2.
\]

The lift excludes `t=4`; exact cubic degree excludes `t=0`. The published
degree-four follow-on uses `t=-2`, giving `p(w)=w-2w^3`.

The `t`-line first tests whether the visible coefficient freedom is a
coordinate gauge or contains inequivalent quartic function-field extensions.
A useful discriminator must be invariant under source and target polynomial
automorphisms; raw coefficient differences do not qualify. Candidate
discriminators are the branch-curve/function-field data of

\[
R_t(w)-wP+Q=0
\]

and its exceptional specializations. Finite-field scouting may locate
degenerate `t` values and primes, but it cannot by itself establish
characteristic-zero inequivalence.

The stronger held-out classification question does not assume the
weighted-lift form. Normalize `b=c=1`, put

\[
\gamma=1+av+t,
\]

freeze the first sparse support for equivariant polynomials `P(v,t)` and
`Q(v,t)`, and impose

\[
\operatorname{Jac}_{v,t}(P,Q)=-\gamma^2
\]

together with the divisibility and low-weight cancellations needed to lift
back to a polynomial three-variable map. Is the resulting saturated
coefficient ideal exactly the weighted-lift locus, modulo equivariant
polynomial coordinate changes? One rational off-locus point with a finite
collision gives a new family. Equality of the saturated ideals gives a
bounded classification theorem. This is the scientific target; replaying
the already-public map is only an adapter calibration.

## Adjacent-support discriminator (2026-07-20, pre-run)

The same-degree chart around the public quadratic-seed map is formally
isolated after quotienting the two scaling directions: its unique remaining
tangent is obstructed at order two. The next eigenquestion is whether this
is merely a degree-ceiling artifact.

Increase each component-degree ceiling by exactly one. The first omitted
equivariant shell consists of

\[
b_{4,0},\quad b_{1,2},\quad c_{5,0},\quad c_{2,2}.
\]

At the unchanged public base point, compute the exact rational tangent space
for every nonempty subset of this four-coordinate shell and for the full
shell. The discriminating outcomes are:

- if every tangent has zero shell coordinates, the existing quadratic
  obstruction proves rigidity through the adjacent support shell;
- if a tangent uses a shell coordinate, compute the cokernel-valued quadratic
  obstruction on the full tangent space rather than optimizing a numerical
  residual;
- a projective tangent annihilating all quadratic obstructions is the first
  admissible off-locus mechanism and must be tested at the next formal order;
- inconsistency of the projective quadratic obstruction cone is a bounded
  next-degree rigidity theorem, not evidence about arbitrary-degree maps.

The test is killed if the shell is selected from the weighted-lift formula
rather than from the complete equivariant degree lattice, if gauge directions
are counted as families, or if rank or compatibility is inferred numerically.

## Cumulative-shell cancellation-radius discriminator (2026-07-20, pre-run)

The adjacent-shell obstruction does not imply isolation at arbitrary degree.
There is an independently known exact cubic seed line

\[
p_s(w)=\left(2+\frac{s}{2}\right)w
      +\left(-3-\frac{3s}{2}\right)w^2+s w^3,
\]

with

\[
q_s(w)=\left(1+\frac{s}{4}\right)w^2-(2+s)w^3
       +\frac{3s}{4}w^4,
\quad
\kappa_s=-4+\frac{s}{2}.
\]

Using

\[
\mu_s=\frac{3(s-4)}{2(s-6)},\qquad
\lambda_s=-\frac{s-4}{4},
\]

normalize the associated components by

\[
\widehat\beta_s(v,t)=
  \lambda_s\mu_s^{-1}\beta_s(\mu_s v,t),\qquad
\widehat\alpha_s(v,t)=
  \lambda_s^{-1}\alpha_s(\mu_s v,t),
\]

so that `gamma = 1 - 3v/2 + t` and the two frozen scaling coordinates agree
with the prior charts.  Direct expansion predicts that its derivative at
`s=0` first fits the complete cumulative `+5` component-degree chart.  Its
nonzero new-shell entries are

\[
\begin{array}{c|l}
+1 & b_{4,0}=15/4,\ b_{1,2}=3,\ c_{5,0}=9/2,\ c_{2,2}=9/2\\
+2 & b_{3,1}=-7,\ c_{4,1}=-15/2\\
+3 & b_{5,0}=9/4,\ b_{2,2}=3,\ c_{6,0}=27/16,\ c_{3,2}=3\\
+4 & b_{4,1}=-3,\ c_{5,1}=-9/4\\
+5 & b_{3,2}=1,\ c_{4,2}=3/4.
\end{array}
\]

The complete shell lattice to test is

\[
\begin{array}{c|l|l}
 & \beta & \alpha\\
+2 & (3,1),(0,3) & (4,1),(1,3)\\
+3 & (5,0),(2,2) & (6,0),(3,2),(0,4)\\
+4 & (4,1),(1,3) & (5,1),(2,3)\\
+5 & (6,0),(3,2),(0,4) & (7,0),(4,2),(1,4).
\end{array}
\]

This supplies two independent checks.  First, cumulative `+5` must recover
the displayed tangent and the exact rational family; failure there diagnoses
an incomplete support lattice or inconsistent normalization.  Second, the
complete cumulative charts `+2` through `+4` test a sharper prediction: no
nonconstant formal arc occurs before the known family's cancellations become
available.  Any earlier integrable tangent is retained as an off-family
candidate rather than forced into this seed line.

## Coordinate-orbit quotient discriminator (2026-07-20, pre-run)

The tangent dimensions observed after the cumulative-support run grow as
`1,2,3,4,5,7`.  Before treating those dimensions as moduli, quotient the two
coordinate mechanisms that preserve the Keller equation.

In source coordinates `(v,gamma)`, with
`gamma = 1 - 3v/2 + t`, every shear

\[
(v,\gamma)\longmapsto(v+\varepsilon f(\gamma),\gamma)
\]

has unit Jacobian and fixes the density `gamma^2`.  Its derivative acts on
`(P,Q)` by the directional derivative at fixed `gamma`.

In target coordinates, a Hamiltonian monomial `H(P,Q)=P^iQ^j` induces

\[
\delta P=\partial_QH(P_0,Q_0),\qquad
\delta Q=-\partial_PH(P_0,Q_0).
\]

Because `P_0=gamma beta_0` and `Q_0=gamma^2 alpha_0`, both
`delta P/gamma` and `delta Q/gamma^2` are polynomial whenever
`i+2j>=3`; `H=PQ` supplies the target scaling direction.  Only generators
whose complete support lies in a tested chart are admissible.  Their linear
combinations must satisfy the frozen `b_(1,0)` coordinate exactly.

The prediction is that these source and target coordinate directions span
the full normalized tangent kernels through cumulative `+4`, and span a
codimension-one subspace at `+5`.  The cubic-family derivative should
represent the missing class.  Membership of that derivative in the gauge
span kills the proposed modulus; any earlier quotient tangent exposes a
different mechanism and supersedes the lower-shell rigidity conjecture.

### Expansion-before-constraint correction (pre-run)

The monomial-local version of the preceding test produced normalized gauge
rank zero: every individual source shear or Hamiltonian monomial either left
the chart or moved the frozen coefficient.  This does not exclude a linear
combination whose forbidden coefficients cancel.

The corrected discriminator therefore expands the full bounded generator
family first.  For Hamiltonian weight bounds `W=3,4,5,6`, form one coefficient
matrix from all `P^iQ^j` with `3 <= i+2j <= W` and source shears
`gamma^m`, `0 <= m <= 8`.  Take the kernel of the complete block consisting
of every out-of-chart coefficient row plus the frozen `b_(1,0)` row.  Only
then project the constrained image into chart coordinates.  A quotient rank
is admissible only if the sequence stabilizes across successive `W`; deleting
forbidden rows before the kernel calculation is a failed test.

## Generic-fiber degree discriminator (2026-07-20, pre-run)

The expanded coordinate calculation identifies the cubic-family derivative
with the target Hamiltonian

\[
H(P,Q)=-\frac14Q^2-\frac1{36}P^3,
\qquad X_H=(-Q/2,P^2/12).
\]

This is an infinitesimal statement.  The global discriminator is the degree
of the induced function-field extension.  Before normalization, put

\[
R_s(w)=\left(1+\frac{s}{4}\right)w^2
       -\left(1+\frac{s}{2}\right)w^3+\frac{s}{4}w^4.
\]

Every inverse branch satisfies

\[
R_s(w)-wP+Q=0,
\]

and `gamma=P-p_s(w)` recovers `gamma`; then `v=w/gamma-1` and the affine
formula for `gamma` recovers `t`.  Thus `w` generates the source function
field over `Q(P,Q)` whenever the displayed polynomial is irreducible.

For fixed rational `s`, irreducibility has a short coefficient-variable
argument.  The leading coefficient is a nonzero rational (`s/4` if `s!=0`,
`-1` at `s=0`), so Gauss reduction permits a factorization in
`Q[P,Q,w]`.  Since the polynomial has degree one in the independent variable
`Q` with coefficient one, one factor must be `Q`-independent; comparing the
`Q` coefficient forces that factor to be a unit.  Hence the generic fiber
degree is four for `s!=0` and three for `s=0`.  The invertible source/target
normalizations do not change it.

If these checks pass, the cubic line is tangent to a Hamiltonian coordinate
orbit but leaves that orbit at higher order by creating a fourth branch at
infinity.  This distinguishes infinitesimal gauge from global conjugacy.

## Kill conditions

- A determinant expansion contradicts `det JF = bc` under the stated
  hypotheses.
- Polynomiality requires an additional coefficient condition.
- A reduction receipt omits denominator, unit, degree, determinant, or
  collision-separation checks.
- A modular acceptance is promoted to a characteristic-zero construction.
- Modular UNSAT is generalized beyond the explicitly covered frozen rational
  assignments.
- The campaign runner branches on a field identifier; field semantics must
  stay in a reviewed adapter capability.
- The `t` discriminator changes under an allowed coordinate automorphism.
- The sparse off-locus search omits saturation by the Keller, degree,
  separability, or finite-collision factors.

## Intended executable surface

The first executable slice is a registered prime-field construction backend
for rational ansatz assignments. It reduces canonical rational constraints,
evaluates only equality/disequality atoms in `GF(p)`, emits the directional
transport classification above, and sends survivors to the existing exact
rational verifier. A separate specialization object may later group the `Q`
and `GF(p)` children; each child retains its own content identity.
