# Gauge-minimized formal contact: compatible all-order pencil

**Status:** BCH-stable all-prefix invariant closed; tail-limsup refinement
active following the exact second-jet
minimum

## Eigenquestion

For the normalized polynomial family \(F_s\), does there exist a compatible
formal target/source contact whose source logarithm has uniformly bounded
polynomial degree, or must the best possible prefix degree grow with the
parameter order?

The quantity to compute is

\[
c_n=\min\left\{
\max_{2\leq j\leq n}\deg Y_j:
F_s=\exp(B_s)\bigl(\exp(A_s)(\mathrm{id})\circ F_0\bigr)
\pmod {s^{n+1}}
\right\},
\]

where

\[
A_s=\sum_{j\geq1}\frac{s^j}{j!}X_{K_j},
\qquad
B_s=\sum_{j\geq2}\frac{s^j}{j!}Y_j.
\]

Each \(K_j\in\mathbb Q[P,Q]\), so \(X_{K_j}\) is Hamiltonian.  Each quotient
source field \(Y_j=(U_j,V_j)\) obeys

\[
U_j\in(v,t),\qquad V_j\in(t,v^2),
\]

the exact lift ideals for an equivariant divergence-free source logarithm.
This pencil fixes the first-order slice

\[
X_{K_1}=X_1=(-Q/2,P^2/12).
\]

It also fixes \(Y_1=0\).  The family tangent has other decompositions
obtained from contact isotropy of \(F_0\), so the displayed choice is a
declared normalization.  Unless stated otherwise, \(c_n\) below denotes the
minimum within this slice.

The logarithmic convention matters.  It makes compatibility across orders a
group identity: higher corrections are not independent per-jet subtractions,
and all BCH cross-terms are retained.

## First post-second-jet equation

Write \(J=dF_0\), \(X_j=X_{K_j}\), and let juxtaposition denote composition of
derivations on target coordinate functions.  Coefficient comparison gives

\[
F_2=X_1^2(F_0)+X_2(F_0)+JY_2
\]

and

\[
\begin{aligned}
F_3={}&X_1^3(F_0)
+\frac32(X_1X_2+X_2X_1)(F_0)+X_3(F_0)\\
&+3Y_2(X_1\circ F_0)+JY_3.
\end{aligned}
\]

The second equation is linear in the complete second-order solution
\((K_2,Y_2)\) and the new variables \((K_3,Y_3)\).  Therefore \(c_3\) can be
computed by one exact coupled coefficient system, rather than by freezing the
particular degree-five witness.

At order four the target coefficient is

\[
\begin{aligned}
T_4={}&X_1^4
+2(X_1^2X_2+X_1X_2X_1+X_2X_1^2)+3X_2^2\\
&+2(X_1X_3+X_3X_1)+X_4,
\end{aligned}
\]

and source composition contributes

\[
6Y_2(T_2\circ F_0)+4Y_3(X_1\circ F_0)
+3Y_2^2(F_0)+JY_4.
\]

This is the first nonlinear compatibility test because it contains squares of
lower-order choices.

## Coordinate mechanism

Use

\[
C=4P^3-P^2-18PQ+27Q^2+4Q,
\]

with

\[
C(F_0)=\gamma^2(3P+\gamma-1),\qquad
27Q^2=C+(18P-4)Q-4P^3+P^2.
\]

Every polynomial target coefficient has the normal form
\(A(P,C)+QB(P,C)\), with filtered degrees

\[
\deg_f(P^aC^c)=4a+6c,\qquad
\deg_f(QP^aC^c)=6+4a+6c.
\]

This will replace arbitrary Hamiltonian-degree cutoffs by a finite target
window at each source bound.

## Attack vectors and counterattacks

1. **Bounded normal form.**  Solve the coupled order-two/order-three system
   under a common source bound.  It is killed if \(c_3>5\).
2. **Growth obstruction.**  Extract a dual functional after quotienting every
   target Hamiltonian allowed by the \(C\)-filtration.  It is killed by an
   explicit compatible degree-five prefix.
3. **Recursive cancellation.**  Search for a rule expressing \(K_n,Y_n\)
   from the exceptional coordinate \(C\) and earlier jets.  It is killed by
   the first rank or polynomial-consistency obstruction.
4. **Apparent finite stabilization.**  Increase the generated Hamiltonian
   window only as a check.  No all-degree conclusion may rely on a tested
   cutoff; the \(C\)-normal form must certify the final finite basis.
5. **Coordinate artifact.**  Compare logarithmic and direct-map expansions.
   A discrepancy kills the computation before any formal statement is
   promoted.

## First discriminating computation

Build the exact joint system for orders two and three.  For each candidate
bound \(d\):

- include every admissible \(Y_2,Y_3\) monomial of degree at most \(d\);
- include every Hamiltonian direction whose pullback can enter the resulting
  component windows;
- require both displayed equations simultaneously;
- compare coefficient rank with augmented rank;
- extract a rational witness at the first consistent \(d\);
- replay both jet identities directly from the exponentials.

The prior theorem fixes \(c_2=5\).  A compatible \(c_3=5\) would support a
bounded-normal-form lane.  An exact \(c_3>5\), after all-degree target-window
certification, would be the first growth obstruction within the declared
first-order slice.

## Claim boundary

Finite prefix values do not determine the all-order sequence.  Kernel
ratification can certify an exact coefficient theorem but cannot establish
historical priority.  A result here concerns the normalized family and the
declared polynomial Hamiltonian/equivariant formal-contact category; it is
not another counterexample to the Jacobian conjecture.

## Exact normalized-slice minimax update through order seven

The complete fixed-bound compatibility families give

\[
(c_2,c_3,c_4,c_5,c_6,c_7)=(5,5,6,7,8,9).
\]

These are quotient-coordinate values with \(Y_1=0\) and the displayed
\(X_1\).  They are not yet minima over every first-order contact
decomposition.  The order-one stabilizer has source degree five and its BCH
action does not preserve the source-degree filtration, so removing the
slice requires another computation.

The last two values require allowing every earlier logarithmic source jet to
use the same prefix bound.  Freezing earlier jets at their individual minima
gave the spurious estimates \(c_5=8,c_6=10\).

For \(c_5\), the complete degree-six family through order four has
compatibility ideal \((1)\) at order five.  The complete degree-seven family
has two linear compatibility equations and admits a rational prefix replay
through order five.

For \(c_6\), the complete degree-seven family through order five again has a
constant quotient obstruction.  At degree eight the sixth-order
compatibility ideal contains the square

\[
\left(a_2+\frac{4729}{40320}\right)^2
\]

together with two linear relations.  The resulting rational branch has a
coefficient-by-coefficient replay through order six.

## Compactification of the exceptional shell

Put

\[
z=\frac1{1+v},\qquad u=3w-1.
\]

In the cusp target coordinates

\[
X=1-3P,\qquad Y=\frac{9P-27Q-2}{2},
\]

the seed becomes

\[
X=u^2-(u+1)z,\qquad
Y=u^3-\frac32u(u+1)z,
\]

and

\[
\det \frac{\partial(X,Y)}{\partial(z,u)}
=\frac32z(u+1)^2.
\]

Thus the affine infinity problem is concentrated at the simple ramification
divisor \(z=0\), whose critical image is the semicubical cusp
\((X,Y)=(u^2,u^3)\).

For a source field \(Y_j=(U_j,V_j)\), its compactified components are

\[
\dot z=-z^2U_j,\qquad
\dot u=\frac{3(V_j-\frac32U_j)}z+(u+1)zU_j.
\]

The replayed degree-eight prefix has simple-pole residue degrees in \(u\)

\[
\deg_u\operatorname{Res}_{z=0}(\dot u)
=(-\infty,1,2,3,4)
\]

for orders \(2,\ldots,6\).  This identifies a likely recursive shell, but it
also blocks an automatic extrapolation from \(c_n=n+2\): the conversion from
affine degree to compactified residue degree must be classified, and target
Hamiltonians can change the residue.  Order seven, or an all-order local
module calculation, is the next discriminator.

The first order-seven probe is adverse to the extrapolation
\(c_n=\max(5,n+2)\).  For one exact degree-eight prefix, the
target-annihilating joint simple-pole shell

\[
\mathcal I(Y)=(u+1)\operatorname{Res}_{z=0}(z\dot z)
             -2u\operatorname{Res}_{z=0}(z\dot u)
\]

has degree six, with leading coefficient \(3946777/62705664\).  Every
affine source field of degree \(D\) obeys

\[
\deg_u\mathcal I(Y)\le \left\lfloor D/2\right\rfloor+1.
\]

Therefore this frozen prefix has no degree-nine extension at order seven.
The coefficient is not invariant under compatible lower-prefix changes.
Let \(Z\) be the degree-five source part of the seed stabilizer and insert it
at parameter order three with coefficient \(\lambda\).  After reducing the
induced order-six bracket by an exact degree-nine stabilizer, BCH changes the
leading shell to

\[
c(\lambda)=\frac{3946777}{62705664}-\frac{115}{648}\lambda.
\]

The rational value

\[
\lambda=\frac{171599}{483840}
\]

cancels it exactly while every lower source jet remains of degree at most
nine.  This kills the branchwise lower bound.  It does not yet construct a
degree-nine order-seven extension, because the remaining joint shell and
the subsequent Laurent coefficients must also lie in the full order-seven
image.

The complete calculation settles that residual.  The degree-eight family
through order six has compatibility ideal containing \(1\) at order seven.
The degree-nine family has dimension \(18\) through order six and only four
linear order-seven conditions.  A rational solution gives source degrees

\[
(5,7,9,9,9,9)
\]

at orders \(2,\ldots,7\), a coefficient-by-coefficient replay through order
seven, and target fields satisfying the full three-variable lift ideals at
every order.  Hence \(c_7=9\) in the fixed first-order slice.

## Category boundary

The lower-bound matrices allow every quotient Hamiltonian target field,
which is broader than the target fields lifting to the full equivariant
three-variable category.  The additional target lift ideals are

\[
\dot P\in(P,Q),\qquad \dot Q\in(Q,P^2).
\]

Every explicit upper witness through order six satisfies them.  The finite
equalities therefore have liftable infinitesimal witnesses in the declared
slice, while a quotient replay alone does not certify a three-variable
group-level contact.

## Unrestricted first-order gauge: two distinct filtrations

The displayed quantity \(c_n\) is meaningful only after the first-order slice
has been fixed.  The seed has polynomial contact isotropy.  In particular,
with

\[
K_*=-\frac{4P^3-18PQ+27Q^2}{12},
\qquad
X_{K_*}=\left(\frac32P-\frac92Q,\;P^2-\frac32Q\right),
\]

the polynomial source field

\[
Z_*=-\,dF_0^{-1}\bigl(X_{K_*}\circ F_0\bigr)
\]

has component degrees \((5,5)\), satisfies the source lift ideals, and obeys

\[
dF_0\,Z_*+X_{K_*}\circ F_0=0.
\]

Its target/source flows are an exact formal stabilizer of \(F_0\).  More
strongly, for every \(m\geq0\),

\[
H_m=\frac{K_*^{m+1}}{m+1},\qquad
X_m=K_*^mX_{K_*},\qquad
Z_m=(K_*\circ F_0)^mZ_*
\]

is another polynomial Hamiltonian/liftable stabilizer.  Since
\(\deg(K_*\circ F_0)=8\), the source degrees are \(5+8m\).  Thus the
first-order isotropy is already infinite-dimensional.  Any minimization that
charges only \(Y_2,\ldots,Y_n\) gives this isotropy an unbounded, uncharged
degree budget.

Including \(Y_1\) gives the finite-window, chart-dependent minimax

\[
\widetilde c_n=\min\left\{
\max_{1\le j\le n}\deg Y_j:
F_s=\exp(B_s)\bigl(\exp(A_s)(\mathrm{id})\circ F_0\bigr)
\pmod{s^{n+1}}
\right\}.
\]

This repairs the uncharged direction, but raw polynomial degree is not a Lie
filtration.  For polynomial source fields,

\[
\deg [Y,Z]-1\leq(\deg Y-1)+(\deg Z-1).
\]

Use the convention \(\deg0=-\infty\) and \(e(0)=0\).  For a nonzero
polynomial vector field, put \(e(Y)=\max(0,\deg Y-1)\).  The
BCH-compatible excess and slope are therefore

\[
\rho_n(F_s;F_0)=
\inf\max_{1\leq j\leq n}\frac{e(Y_j)}j ,
\]

where the infimum ranges over every polynomial Hamiltonian/liftable contact
decomposition through order \(n\).  The triangular spaces

\[
\deg Y_j\leq 1+rj
\]

are closed under BCH through every finite order.  The normalized \(c_n\) and
the unrestricted \(\widetilde c_n\) remain useful affine-coordinate
statistics, but only \(\rho_n\) is compatible with the source contact-group
filtration.

### First unrestricted discriminator

Let

\[
H_\lambda=-\frac{Q^2}{4}-\frac{P^3}{36}+\lambda K_*.
\]

Keep only the autonomous first-order target generator \(X_{H_\lambda}\), and
use formal étale recursion to determine the unique source logarithm through
order four.  Compute every coefficient symbolically in \(\lambda\), then
intersect the exact coefficient ideals of all source monomials of degree
greater than five.

- A common rational root supplies a degree-five bounded contact through order
  four and kills the extrapolation from the normalized sequence.
- A unit ideal excludes this one-parameter canonical-stabilizer mechanism but
  does not prove \(\widetilde c_4>5\), because independent higher target
  Hamiltonians remain available.
- Denominator failure or a mismatch under direct exponential replay kills the
  computation.

### Exact unrestricted update through order four

The complete filtered order-one systems give:

- at source bound four, rank \(33\), augmented rank \(33\), and nullity zero;
- at source bound five, rank \(45\), augmented rank \(45\), and nullity one.

The unique degree-five direction is exactly the displayed seed stabilizer:
both its Hamiltonian and source components have proportionality factor one
against \((K_*,Z_*)\).

The autonomous target generator \(H_\lambda\) alone does not provide a
bounded normal form.  Through order four its unique source logarithm has
component degrees

\[
(5,5),\ (11,11),\ (13,13),\ (15,15),
\]

and the \(319\) coefficients above degree five generate the unit ideal in
\(\mathbb Q[\lambda]\).

Allowing the complete degree-five order-two source/target image changes the
picture but does not rescue nonzero first-order isotropy.  Order two has no
quotient obstruction for any \(\lambda\), and its homogeneous solution space
is one-dimensional.  After retaining that full direction, the order-three
quotient obstruction is exactly

\[
\lambda=0.
\]

Thus every source-degree-five contact prefix through order three returns to
the normalized first-order slice.  In that slice, the complete degree-five
family through order three has order-four compatibility obstructions

\[
1,\qquad a_0,
\]

so no degree-five prefix reaches order four.  The already replayed
degree-six normalized witness gives the matching upper bound.  Therefore the
filtration-aware unrestricted values are

\[
(\widetilde c_2,\widetilde c_3,\widetilde c_4)=(5,5,6).
\]

This is an exact all-Hamiltonian result at the finite filtered windows
certified by the \(C\)-normal form.  It does not yet determine
\(\widetilde c_n\) for \(n\geq5\).

The same calculation one bound higher settles the next term.  At source bound
six, the complete order-one system has rank \(59\), augmented rank \(59\),
and nullity one; its unique direction is again exactly
\((K_*,Z_*)\).  The complete degree-six families have no obstruction at
orders two and three.  At order four their quotient obstructions are

\[
\lambda,\qquad \lambda^2,
\]

so any degree-six prefix reaching order four again has \(\lambda=0\).  The
complete normalized degree-six family through order four then has order-five
compatibility obstructions

\[
1,\qquad a_0,
\]

with Gröbner basis \((1)\).  The normalized degree-seven witness supplies the
upper bound.  Hence

\[
(\widetilde c_2,\widetilde c_3,\widetilde c_4,\widetilde c_5)
=(5,5,6,7).
\]

At source bound seven the order-one isotropy space grows from one to three
dimensions, so the one-parameter reduction above cannot be extrapolated to
\(\widetilde c_6\).

### Complete three-parameter isotropy calculation

The complete order-one affine fiber resolves that ambiguity.  At order three
its compatibility equations are

\[
\ell_2=0,\qquad 2\ell_0+3\ell_1=0.
\]

After substituting \(\ell_0=-3\ell_1/2\) and \(\ell_2=0\), the complete
order-four quotient contains

\[
\ell_1^2,\qquad h_{2,2},\qquad
\frac{-1680h_{2,0}-2520h_{2,1}+777\ell_1+179}{179}.
\]

Consequently every degree-seven prefix reaching order four has
\(\ell_0=\ell_1=\ell_2=0\).  In the normalized slice, the complete
degree-seven order-six compatibility ideal contains

\[
1,\quad b_2,\quad
-\frac{37a_3-40b_0-60b_1}{60},\quad a_2,\quad a_2^2.
\]

The normalized degree-eight replay supplies the upper bound, so

\[
(\widetilde c_2,\widetilde c_3,\widetilde c_4,
  \widetilde c_5,\widetilde c_6)=(5,5,6,7,8).
\]

These equalities are exact finite filtered calculations.  They should not be
read as growth of contact-group complexity: \(\widetilde c_n\) is not
BCH-stable.

### Lie-filtered result through order eight

The normalized order-seven witness has source degree profile

\[
(\deg Y_2,\ldots,\deg Y_7)=(5,7,9,9,9,9)
\]

and \(Y_1=0\).  It lies in the slope-two triangular filtration
\(\deg Y_j\leq1+2j\), so it gives \(\rho_n\leq2\) for every
\(2\leq n\leq7\).

The same prefix extends at order eight with

\[
\deg Y_8=17=2\cdot8+1.
\]

The exact order-eight coefficient image has rank \(345\), nullity \(18\),
and residual component degrees \((20,22)\).  Its \(C\)-normal target window
has dimension \(24\); the selected target field satisfies the
three-variable lift ideals, and direct exponential replay is coefficientwise
zero through order eight.

Conversely, \(\rho_n<2\) would force \(\deg Y_1\leq2\).  The complete
order-one fiber has no nonzero source stabilizer even through degree four,
so \(Y_1=0\).  It would then force \(\deg Y_2\leq4\), contradicting the exact
second-jet lower bound.  Therefore

\[
\boxed{\rho_n=2\quad\text{for every }2\leq n\leq8.}
\]

### All-order closure of the BCH-stable invariant

The finite computation is no longer the upper endpoint.  The root-cover
volume rectifier constructs one identity-normalized compatible formal contact

\[
H_s\circ F_s=F_0\circ\Psi_s,\qquad \det DH_s=1,
\]

with

\[
\deg [s^j](\Psi_s-\operatorname{id})\leq2j+1
\qquad(j\geq1).
\]

The source substitution group with coefficient constraints

\[
\deg [s^j](\Phi_s-\operatorname{id})\leq2j+1
\]

is closed under composition and inverse.  Indeed, a substitution word with
coefficient orders \(j_1,\ldots,j_r\) contains \(r-1\) spatial derivatives,
so its degree is at most

\[
\sum_{\ell=1}^r(2j_\ell+1)-(r-1)
=2\sum_{\ell=1}^rj_\ell+1.
\]

For completeness, let

\[
\Delta=\Psi_s^*-\operatorname{id}
\]

act on the polynomial coordinate ring.  If \(p\) has degree \(d\), the same
substitution count gives

\[
\deg[s^n]\Delta(p)\le d+2n.
\]

Since

\[
\log(\Psi_s^*)=
\sum_{r\ge1}\frac{(-1)^{r+1}}r\Delta^r,
\]

only finitely many words contribute at each parameter order, and applying
them to a coordinate gives degree at most \(2n+1\).  The source subgroup
preserves the lift ideals \((v,t)\) and \((t,v^2)\), hence its logarithm does
as well.  On the target, \(\det DH_s=1\) makes \(\log H_s\)
divergence-free; over \(\mathbb Q[P,Q]\), every polynomial
divergence-free plane field has a polynomial Hamiltonian.  Thus the
rectifier supplies a single all-order admissible decomposition with

\[
\deg Y_j\leq2j+1,
\]

and hence \(\rho_n\leq2\) for every \(n\).

For the reverse inequality, suppose \(n\geq2\) and a decomposition had
prefix slope strictly below two.  Integrality of polynomial degree gives

\[
\deg Y_1\leq2,\qquad \deg Y_2\leq4.
\]

The complete order-one contact fiber has no nonzero source component in the
first window, so \(Y_1=0\).  The kernel-checked second-jet dual certificate
then excludes every degree-four source lift even with the complete
polynomial Hamiltonian target window; an admissible degree-five lift exists.
Consequently every admissible prefix has slope at least two.  Combining the
two directions,

\[
\boxed{\rho_n(F_s;F_0)=2\quad\text{for every }n\geq2},
\qquad
\boxed{\rho_\infty:=\sup_{n\geq2}\rho_n=2}.
\]

The infimum causes no attainment loophole: every admissible prefix value is
at least two, while the one all-order rectifier realizes value at most two
on every prefix.

The Lean artifacts certify the family-specific second-jet obstruction and
witness, the root-cover identities, the substitution-word degree envelope,
and injectivity of the complete \(15\times15\) low first-order contact
minor.  The terminal arithmetic aggregation passed provider-free LeanMill
ratification with kernel-parity SHA-256
`065f305d012a7f94e69e439fd91ca2dfb4caa9617d5b802a9b5b4e063f675664`.
The completed substitution-group exp/log passage is the standard filtered
argument displayed above; it is not represented as a full
formal-power-series group object in the current Lean library.

This prefix maximum is deliberately a group-filtration membership test.  Its
value is already saturated by \(Y_2\), so it cannot distinguish a uniformly
bounded tail from linear degree growth.  The asymptotic source question is

\[
\sigma_{\rm src}=
\inf_{\text{all-order contacts}}
\limsup_{j\to\infty}\frac{e(Y_j)}j.
\]

To prevent all escape from being moved into an uncharged target gauge, the
symmetric contact version uses ordinary polynomial derivation excess on both
sides:

\[
\sigma_{\rm ct}=
\inf_{\text{all-order contacts}}
\limsup_{j\to\infty}
\frac{\max(e(Y_j),\,\max(0,\deg X_{K_j}-1))}{j}.
\]

Both ordinary-degree excesses are subadditive under Lie brackets.  No finite
prefix computed here determines either asymptotic infimum.  The based uniform
statistics \(c_n\) answer a different question—whether the logarithmic
generators can remain in one finite polynomial-degree space—and remain worth
computing despite their dependence on the declared first-order chart.

### Rees-Lie reformulation of the slope-two problem

The triangular filtration is more than a convenient cutoff.  If

\[
\mathcal F_r\mathfrak g
=\{Y:\deg Y-1\leq r\},
\]

then

\[
[\mathcal F_r\mathfrak g,\mathcal F_u\mathfrak g]
\subseteq\mathcal F_{r+u}\mathfrak g.
\]

Consequently

\[
\mathfrak g^{(2)}
=\left\{\sum_{n\geq1}s^nY_n:
          Y_n\in\mathcal F_{2n}\mathfrak g\right\}
\]

is a complete Rees Lie algebra.  Exponential, logarithm, BCH, and
logarithmic differentiation preserve the corresponding completed group.
More explicitly, if a source logarithm begins at order two and satisfies
\(\deg Y_n\leq2n+1\), then its right logarithmic velocity

\[
V(s)=\sum_{m\geq1}s^mV_m
\]

satisfies

\[
\deg V_m\leq2m+3.
\]

Conversely, integrating a velocity in this shifted Rees module produces a
source logarithm with the same slope-two bound.  The stronger velocity
estimate is essential: the weaker excess bound \(e(V_m)\leq2m+4\) gives only
the generic Magnus envelope \(3n+O(1)\), and explicit one-variable brackets
attain that larger envelope.

This changes the computational category.  Instead of solving nonlinear BCH
compatibility for all logarithmic coefficients simultaneously, solve the
linear infinitesimal contact equation

\[
\partial_sF_s=X_s(F_s)+dF_sV_s
\]

inside the shifted Rees modules.  At coefficient \(s^m\), the new source
window is exactly \(\deg V_m\leq2m+3\); the exhaustive \(C\)-normal target
window supplies the Hamiltonian quotient.  A compatible all-order linear
recursion integrates to the required contact.  A nonzero saturation class in
this complete Rees lane is an obstruction to it.

This equivalence also identifies the correct mechanized object: a filtered
orbit-map module over \(\mathbb Q[[s]]\), with exact cokernel and
\(s\)-torsion receipts.  Raw fixed-degree instantaneous connections are not
closed under logarithmic differentiation and cannot decide the slope
question.

### Candidate all-order cusp mechanism

The exceptional-set calculation has an exact integrated normal form, not
only a fitted coefficient pattern.  Put \(y=3z-1\), choose the branch

\[
d^2=3s^2+12s+36,\qquad
\alpha=\frac{s+6-d}{2s},\qquad y=\xi+\alpha,
\]

and define

\[
\eta=\xi\sqrt{\frac d6}
       \sqrt{1-\frac{2s\xi}{3d}}.
\]

For the displayed family polynomials \(p_s,q_s\), exact reduction modulo the
quadratic equation for \(d\) gives

\[
p_s(\xi+\alpha)-p_s(\alpha)=-\frac{\eta^2}{3}
\]

and

\[
\begin{aligned}
q_s(\xi+\alpha)-q_s(\alpha)
&-\frac{\alpha+1}{3}
  \bigl(p_s(\xi+\alpha)-p_s(\alpha)\bigr)\\
&=\frac{\xi^3(-4d+3s\xi)}{324}.
\end{aligned}
\]

The coefficient of \(s^n\) in \(\eta\) has \(\xi\)-degree at most \(n+1\).
Since the cusp parameter is quadratic in the affine source coordinates and
passing to its logarithmic vector field removes one spatial degree, this
predicts the triangular bound \(\deg Y_n\leq2n+1\).

The missing bridge is precise: extend this one-dimensional critical-curve
normalization to a global polynomial Hamiltonian target contact and an
admissible source lift without enlarging the triangular filtration.  Failure
of the second-coordinate symplectic extension, a lift-ideal violation, or an
order-\(n\) coefficient outside degree \(2n+1\) kills the mechanism.

The first two bridge coefficients now pass after one necessary correction.
The curve-only projective Padé coordinate is excluded at order one by an
exact \(40\times6\) coefficient system of rank \(6\) and augmented rank \(7\).
Its dual evaluates to \(-729\).  Allowing the geometrically natural
off-critical-curve term

\[
U_s=U_s^{\mathrm{cusp}}+\gamma A_s
\]

removes that obstruction.  At order one,

\[
U^{\mathrm{cusp}}_1
=\frac{\gamma}{4}-\frac{(x+1)(2x-1)}{36},
\qquad
A_1=-\frac14+\frac{(1+v)(2x-1)}{12},
\]

and \(U^{\mathrm{cusp}}_1+\gamma A_1=0\).  The source jet is zero and the
entire tangent is the fixed target Hamiltonian \(X_1\).

At order two,

\[
U^{\mathrm{cusp}}_2
=-\frac{(x-2)(18\gamma+x^2-7x-8)}{324}.
\]

For the certified degree-five velocity \(Y_2\), the quotient

\[
A_2=\frac{Y_2(x)-U^{\mathrm{cusp}}_2}{\gamma}
\]

is polynomial of degree five.  Its weighted-area companion
\(R_2=\gamma Y_2(\gamma)\) has zero weighted divergence, recovers \(Y_2\)
exactly, and the remaining response descends to the Hamiltonian

\[
K_2=-\frac{5P^3}{1512}-\frac{P^2Q}{168}
    -\frac{11PQ}{120}+\frac{29Q^2}{168}.
\]

Thus the target-relative Padé construction passes orders one and two in the
shifted Rees filtration.  The next discriminating coefficient is order
three; the theorem-level residual is persistence of \(\gamma\)-divisibility,
weighted-area solvability, and polynomial target descent.

### A regular-singular contact connection

There is a complementary exact explanation for why a low-degree generic
chart does not immediately give a formal chart at the special fiber.  Write
\(F_s=(P_s,Q_s)\) for the normalized quotient family and use the target
scaling Hamiltonian \(K=PQ\), whose field is \((P,-Q)\).  In the one-parameter
scaling lane, requiring

\[
\partial_sF_s
=X_{a(s)PQ}(F_s)+dF_s\,V_s
\]

to have \(\deg V_s\leq10\) forces

\[
a(s)=
\frac{4(2s^2-11s+6)}{7s(s-6)(s-4)}
=\frac1{7s}-\frac{17}{84}+O(s).
\]

The resulting \(V_s\) has degree nine in both components over
\(\mathbb Q(s)\), whereas the regular source-only connection
\((dF_s)^{-1}\partial_sF_s\) has degree eleven.  The apparent improvement is
singular: \(V_s\) also has a simple pole at \(s=0\).  If

\[
R=\operatorname{Res}_{s=0}V_s,
\]

then \(\deg R=7\) and its pole cancels precisely because

\[
dF_0R+\frac17X_{PQ}(F_0)=0.
\]

Thus the residue is a polynomial contact-stabilizer of the seed.  The
low-degree connection lives on the punctured parameter line and cannot be
used as an \(s\)-adically regular contact.  This concentrates the formal
complexity question into a regular-singular extension problem: determine
whether transporting and regularizing the isotropy residue forces unbounded
logarithmic degree, or whether a different regular gauge absorbs it.

The exact replay is `gauge_regular_singular_connection.py`.  Its uniqueness
claim is currently restricted to the target scaling lane \(K=a(s)PQ\);
completeness over every Hamiltonian target direction remains a separate
quotient calculation.

### First order-eight uniform-cutoff discriminator

The selected rational degree-nine prefix through order seven has
order-eight residual component degrees \((20,22)\).  The exhaustive
order-eight \(C\)-normal image at source bound nine does not contain that
residual.  Hence this particular prefix does not extend with a uniform
degree-nine cutoff.  This is branchwise evidence only: \(c_8>9\) requires
eliminating the complete degree-nine family through order seven, including
its order-seven nullspace parameters.

That complete transition has now been computed.  The degree-nine family has
dimension \(18\) through order six.  Its four affine-linear order-seven
compatibility equations have exact RREF rank four; after adjoining the
six-dimensional order-seven homogeneous fiber, the complete family through
order seven has dimension \(20\).  At order eight the image has rank \(129\),
nullity \(6\), and cokernel dimension \(10\).  One cokernel pairing is the
literal constant \(1\).  Therefore the entire degree-nine compatibility
locus is empty and

\[
\boxed{c_8>9}
\]

in the fixed first-order slice.  Together with the degree-seventeen
continuation,

\[
10\leq c_8\leq17.
\]

The reusable transition admits a `compatible` family state only for an exact
linear-RREF graph or a separately certified complete decomposition.
Nonlinear graphs merely returned by a symbolic solver are typed as partial
coverage and cannot support a minimax claim.

The all-prefix eigenquestion is now closed by the root-cover rectifier and
the second-jet obstruction:

\[
\rho_\infty=2.
\]

The surviving successor question is the finite-prefix-insensitive symmetric
tail invariant \(\sigma_{\rm ct}\).  The Rees node/cusp separation theorem
controls contacts that remain in one global triangular class, while the
exact pole-six source connection shows that unrestricted polar prefixes can
span the node motion.  The cusp-stabilizer calculation adds the complementary
fact that removing a critical finite target prefix can itself create a
nonzero infinite BCH tail.  Closing \(\sigma_{\rm ct}\) therefore requires a
classification of arbitrary source/target prefix normalizations or a
gauge-independent tail quotient; it is a successor refinement rather than a
missing case of the all-prefix theorem.
