# Global Bernoulli-ray defect perturbation pencil

## Claim boundary

This pencil varies the exact normalized global connection only by regular
order-three target-Hamiltonian terms.  It can determine whether the new
terminal Bernoulli ray is rigid or cancellable in that finite-dimensional
perturbation window.  It cannot control arbitrary later target coefficients
or prove a minimax lower bound.

## Derived scalar defect

In the translated closed quotient, let

\[
A=-\frac3{896}(uz)^7,\qquad
E_0=u^7z^8,\qquad E_1=[A,E_0].
\]

Write \(H\) for the coefficient of \(E_0\) in the cost-four instantaneous
velocity.  Let

\[
N=
\frac{2[L_2,L_4^{\rm nonterminal}]}{E_1}
\]

denote the normalized even terminal seed, including the factor two from
\([\Omega_{\rm poly},\Omega_{\rm poly}']\).  The complete terminal equation
with constants \(H,N\) has solution

\[
D(x)=\frac H4+
\left(\frac H2+N\right)
\frac1x
\left(
\frac{x}{e^x-1}-1+\frac x2
\right).
\]

Thus the all-order tail is controlled by

\[
\boxed{\Delta=H+2N.}
\]

For the normalized global connection,

\[
H=\frac7{3072},\qquad
N=-\frac1{1536},\qquad
\Delta=\frac1{1024}.
\]

## Eigenquestion

Add

\[
s^3(\alpha P^3+\beta PQ+\gamma Q^2)
\]

to the target Hamiltonian.  Do the three induced source pullbacks span the
defect scalar \(\Delta\)?

## Discriminating test

1. Compute each seed pullback at \(s=0\) with the exact inverse Jacobian.
2. Convert it to the \(z^2\)-Hamiltonian chart and then to \(u=1+v\).
3. Project at cost four to \(I\ge-6,\ J\ge-3\).
4. Recompute \(H\), \(N\), and the affine defect
   \(\Delta(\alpha,\beta,\gamma)\).
5. If a cancellation exists, substitute the exact rational parameter back
   into the quotient and replay beyond the first four previously nonzero
   Bernoulli orders.  Record the next surviving grade rather than treating
   one killed ray as boundedness.

## Kill and success conditions

The rigidity claim is killed if any allowed direction has nonzero defect
slope.  A cancellation candidate succeeds only if the exact symbolic defect
is zero and the terminal replay loses the complete \(n=6+4m\) subsequence.
It is rejected as a bounded-log candidate if another quotient ray grows
after the cancellation.

## Exact low-weight outcome

The three preregistered directions have zero projected defect slope:

\[
\partial_{P^3}\Delta
=\partial_{PQ}\Delta
=\partial_{Q^2}\Delta
=0.
\]

Their seed pullbacks do not enter the \((-6,-3)\) rectangle at parameter
cost four.  The same diagnostic gives zero defect slope for \(P^4\) and
\(P^2Q\); \(P^4\) has one retained nonterminal monomial, but its bracket
with \(L_2\) does not reach the terminal orbit.

Thus the Bernoulli ray is rigid under the complete displayed low-weight
target algebra.  This is a category-bounded result: higher target
Hamiltonians can have larger seed pullbacks.

## Successor eigenquestion

Among monomials \(P^aQ^b\) of increasing ordinary degree that satisfy the
target lift ideals, what is the first one with

\[
\partial_{P^aQ^b}\Delta\ne0?
\]

The next test enumerates a declared finite monomial window, records the
first nonzero slope and its source Hamiltonian support, and then checks
whether the exact rational cancellation merely transfers growth to a
different terminal grade.  Absence in that finite window is not promoted to
unrestricted rigidity.

## Exhaustive polynomial order-three outcome

The finite-window pattern has an exact unrestricted explanation.  In the
translated seed chart,

\[
P_0=-\frac z4(3u^2z-4u-2),\qquad
Q_0=-\frac{uz^2}{4}(u^2z-u-1),
\]

and

\[
dP_0\wedge dQ_0=-\frac{z^2}{8}\,du\wedge dz.
\]

Therefore adding \(s^3M(P,Q)\) changes the cost-four source Hamiltonian by

\[
8M(P_0,Q_0).
\]

The defect functional uses only nine source coefficients, all with
\(z\)-exponent at most eleven.  Since

\[
\operatorname{ord}_z(P_0^aQ_0^b)=a+2b,
\]

only the 42 pairs \(a+2b\le11\) can contribute for an arbitrary polynomial
\(M\).  Exact enumeration gives

\[
\partial_{P^aQ^b}\Delta=0
\]

for all 42 pairs.  Every remaining monomial has too large a \(z\)-order.
By linearity,

\[
\boxed{
\Delta\text{ is invariant under every polynomial perturbation }
s^3M(P,Q).
}
\]

The replay is
[`gauge_global_ray_defect_perturbation.py`](gauge_global_ray_defect_perturbation.py).
This exhausts the order-three target coefficient, not the gauge problem:
earlier coefficients can change \(L_2\) or \(L_3\), while later coefficients
can inject new terminal velocities.

## Order-one successor pencil

The next earlier slot is

\[
K_s\longmapsto K_s+sM(P,Q).
\]

Its seed pullback changes \(L_2\), including potentially the grade-zero
generator

\[
A=-\frac3{896}(uz)^7.
\]

The successor eigenquestion is whether the polynomial target image spans
the coefficient of \(u^7z^7\).  The first discriminating pass enumerates
all monomials that can reach that coefficient by seed \(z\)-order.  If the
coefficient is rigid, the radial mechanism survives every polynomial
order-one perturbation.  If it is movable, the exact rational cancellation
must be carried through costs three and four using the full parameter
dependence of \(M(P_s,Q_s)\); canceling the seed coefficient alone is not
treated as a logarithmic escape.

### Seed calculation and cancellation candidate

The order-one target image does span the zero-grade coefficient.  Thirteen
seed monomials with \(a+2b\le7\) have nonzero \(u^7z^7\) coefficient.
The smallest convenient direction is

\[
M=Q^3,\qquad
[u^7z^7]\,\Delta L_2=-\frac3{16}.
\]

Hence the exact candidate

\[
\boxed{
K_s^{\rm new}=K_s-\frac{s}{56}Q^3
}
\]

cancels

\[
-\frac3{896}-\frac1{56}\left(-\frac3{16}\right)=0.
\]

The candidate test must use the full perturbation

\[
-\frac{8s}{56}Q_s^3
\]

in the source Hamiltonian, expand all induced later costs, and replay both
source and target with their correct velocity placements.  The candidate is
killed if another zero-grade generator appears, if a different closed
quotient has a nonzero unbounded adjoint ray, or if the target logarithm
acquires the dominant tail.  A bounded finite replay is recorded only as an
escape candidate.

### Exact terminal-ray disposition

The full source perturbation is

\[
-\frac{s}{7}Q_s^3.
\]

After it is added, the translated \((-6,-3)\) quotient has instantaneous
support only at costs two through five, with respectively

\[
15,\ 13,\ 8,\ 4
\]

retained monomials.  Every retained grade is strictly negative in at least
one coordinate; there is no zero-grade input at any of those costs.

Hence the fixed terminal grade cannot receive an infinite adjoint orbit.
Deleting the zero-grade letter leaves at most nine letters in a word that
sums to \((-6,-3)\), and the total cost of such a word is at most \(45\).
Thus the complete Bernoulli terminal component vanishes beyond a finite
order.  The candidate kills the all-order ray, not just its checked prefix.

This does not yet give a bounded-log connection.  The perturbation
Hamiltonian \(Q_s^3\) raises the source instantaneous spatial degree, and a
different moving grade can carry an unbounded Lie-closure cascade.  The next
attack is therefore the top homogeneous Lie face of the perturbed
connection.

### Transferred top-face attack

The cancellation perturbation has a higher Newton face.  At the seed,

\[
\operatorname{top}Q_0=-\frac14(uz)^3,
\]

so the cost-two perturbation Hamiltonian begins with

\[
\operatorname{top}\Delta V_2
=\frac1{448}(uz)^9,
\qquad
\operatorname{top}\Delta L_2
=\frac1{896}(uz)^9.
\]

The radial top monomial commutes with itself.  Use the additive excess

\[
G=\deg_{\!u,z}H-7q-4
\]

at parameter cost \(q\).  The radial cost-two term has \(G=0\).

The successor eigenquestion is whether the first nonradial shell \(B\) in
the later perturbation coefficients has a nonzero orbit

\[
\operatorname{ad}_{(uz)^9}^{\,k}B
\]

and a surviving Magnus response.  A nonzero infinite subsequence would
transfer the logarithmic rate from five to seven and kill the
\(-sQ^3/56\) escape candidate.  The attack is rejected if the shell
commutes, its universal response cancels, or another word reaches the same
top face and cancels it.

### Source top-face outcome

The first nonradial perturbation shell is

\[
B=\frac5{3584}u^8z^9
\]

in \(L_3\), while the radial grade-zero generator for the slope-seven
grading is

\[
A_7=\frac1{896}u^9z^9
\]

in \(L_2\).  The monomial orbit
\(\operatorname{ad}_{A_7}^kB\) is nonzero as a Lie word.  It nevertheless
does not survive the full logarithm: the exact \(A_7\)-free terminal core at
cost five cancels the first response, and the complete closed quotient has
terminal terms only at costs two and three.

Thus neither the old slope-five ray nor this first slope-seven source face
kills the candidate.  The cancellation is structural in the checked closed
quotients rather than a short-prefix zero.

### Target alternating-cubic pencil

The target perturbation introduces \(Q^3\) beside the constant \(P^3\)
direction.  Their Hamiltonian Lie algebra is infinite.  Put

\[
A=P^3,\qquad C=Q^3,\qquad
W_m=P^{3m}Q^3.
\]

The exact monomial bracket gives

\[
\operatorname{ad}_{C}\operatorname{ad}_{A}^{\,2}W_m
=162(3m+4)W_{m+1}\ne0.
\]

The word \(W_m\) has parameter cost \(2+4m\), Hamiltonian degree \(3m+3\),
and target derivation degree \(3m+2\).  If its left-Magnus coefficient
survives, the candidate still has unbounded target logarithmic degree with
limiting rate \(3/4\).

The discriminating replay carries the complete rational \(P^3/PQ/Q^2\)
target connection plus \(-sQ^3/56\), uses left placement, and reserves
orders beyond the first apparent recurrence as held-out checks.  A nonzero
Lie word alone is not promoted; its Magnus coefficient must be derived or
replayed exactly.

### Second source-excess outcome

The target coefficient question is no longer needed to dispose of the
\(Q^3\) candidate.  The first slope-seven source face cancels, but the next
closed source module does not.

With excess

\[
G=a+b-7q-4,
\]

the unique zero-grade source logarithmic term is
\(A=u^9z^9/896\).  At \(G=-13\), put

\[
E_0=u^{17}z^{16},\qquad E_{k+1}=[A,E_k].
\]

The complete finite forcing core and right-forward-`dexp` equation give

\[
[E_k]\Omega_{6+2k}^{\rm src}
=
\frac{27}{12845056}
\frac{B_{k+2}}{(k+2)!}
\prod_{j=0}^{k-1}\frac{9(2j+1)}{896}.
\]

For \(k=2m\), this is nonzero.  Thus at every \(n=6+4m\) the source
Hamiltonian contains a nonzero multiple of

\[
u^{17+16m}z^{16+12m},
\]

of derivation degree \(7n-12\).  The \(Q^3\) cancellation is therefore
excluded at all orders.  The target count-algebra prefix remains useful as
a separate replay, but it is no longer the candidate's deciding
obstruction.

### Seed-central alternate candidate

The \(Q^3\) direction is not the only order-one cancellation.  Let

\[
H_0=-\frac1{36}P^3-\frac14Q^2
\]

be the fixed target Hamiltonian at the distinguished fiber.  Exact seed
coefficient extraction gives

\[
[u^7z^7]\,\Delta L_2(H_0^2)=-\frac1{96}.
\]

Therefore

\[
\boxed{
K_s^{\rm cent}
=K_s-\frac9{28}sH_0^2
}
\]

cancels the source grade-zero coefficient:

\[
-\frac3{896}
-\frac9{28}\left(-\frac1{96}\right)=0.
\]

Unlike \(Q^3\), the new direction commutes with \(H_0\).  This removes the
immediate two-cubic target counterattack.  The discriminating test carries
the full source pullback

\[
-\frac{18}{7}s\,H_0(P_s,Q_s)^2
\]

and the matching target left-Magnus connection.  It is killed by any new
source zero-grade ray, any nonzero moving-grade recurrence, or unbounded
target shells.  Finite boundedness remains candidate evidence only.

### Exact seed-central disposition

The full source pullback produces a new radial face rather than a bounded
logarithm.  For a Hamiltonian monomial \(u^az^b\) at parameter cost \(q\),
put

\[
(I,J)=(2a-11q-2,\ 2b-9q-6).
\]

In the rectangle down to \((-22,-16)\), the instantaneous connection has
only costs two and four.  The cost-two logarithm has the unique zero-grade
term

\[
A=-\frac9{458752}u^{12}z^{12},
\]

and the cost-four velocity is exactly

\[
\frac9{1048576}u^{14}z^{14}
+\frac{123}{1835008}u^{13}z^{13}
-\frac{111}{3670016}u^{12}z^{13}.
\]

The last monomial is terminal.  Bracketing the complete cost-two logarithm
with the complete cost-four velocity gives the first terminal iterate

\[
\frac{243}{105226698752}u^{23}z^{22}.
\]

Relative to the orbit obtained from the radial term \(A\) and the direct
terminal seed alone, this is the nonzero factor

\[
-\frac{12}{37}.
\]

After this first terminal bracket, every strictly negative-grade outer
letter exits the quotient.  Hence all later brackets use \(A\), with
recurrence multiplier

\[
-\frac{27}{114688}(2k-1).
\]

The right-Magnus terminal response to a cost-four velocity is

\[
\phi_3(x)
=\frac{x}{e^x-1}\int_0^1t^3e^{t^2x}\,dt
=\frac12+
\frac1{2x}\left(\frac{x}{e^x-1}-1\right).
\]

Its constant coefficient is \(1/4\), and for \(k\ge1\),

\[
[x^k]\phi_3(x)=\frac{B_{k+1}}{2(k+1)!}.
\]

Thus every odd depth \(k=2m+1\) is nonzero.  At logarithmic order

\[
n=4+2k=6+4m
\]

the surviving Hamiltonian is a nonzero multiple of

\[
u^{23+22m}z^{22+18m}
=u^{(11n-20)/2}z^{(9n-10)/2}.
\]

Its source derivation degree is

\[
(23+22m)+(22+18m)-3
=10n-18.
\]

Therefore the seed-central perturbation cancels the earlier rate-five ray
but creates an all-order rate-ten source ray.  It is excluded as a
bounded-log connection.  This remains a theorem about this exact
order-one cancellation, not about all coefficientwise-polynomial moving
connections.

The exact reconstruction, quotient checks, finite-core ratio, and orbit
replay are in
[`gauge_seed_central_magnus_transfer.py`](gauge_seed_central_magnus_transfer.py).
