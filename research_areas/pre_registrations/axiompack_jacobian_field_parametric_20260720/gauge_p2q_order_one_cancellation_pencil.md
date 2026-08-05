# Minimum-Newton-weight order-one cancellation

## Claim boundary

This pencil tests the exact target perturbation

\[
K_s^{P^2Q}=K_s-\frac{s}{168}P^2Q.
\]

It is the lowest seed-Newton-weight monomial found to span the original
rate-five source defect.  The test can accept or exclude this connection;
it does not classify arbitrary linear combinations on the full order-one
cancellation hyperplane.

## Seed calculation

In the translated seed chart,

\[
P_0=-\frac z4(3u^2z-4u-2),\qquad
Q_0=-\frac{uz^2}{4}(u^2z-u-1).
\]

An order-one target coefficient \(M\) changes the cost-two source
logarithm by \(4M(P_0,Q_0)\).  Exact coefficient extraction gives

\[
[u^7z^7]\,4P_0^2Q_0=-\frac9{16}.
\]

Hence

\[
-\frac3{896}
-\frac1{168}\left(-\frac9{16}\right)=0.
\]

The full source Hamiltonian perturbation is

\[
-\frac{s}{21}P_s^2Q_s.
\]

Unlike the \(Q^3\) and \(H_0^2\) directions, its seed top face has the same
degree as the generator it cancels.

## Eigenquestion

Does the complete source/target logarithm of this connection have a
smaller asymptotic degree rate, or does another closed Newton face acquire
a nonzero radial Magnus response?

## Discriminating test

1. Reconstruct the exact source velocity with \(-sP_s^2Q_s/21\).
2. Enumerate its complete instantaneous Newton support and determine every
   maximal degree-per-cost face after the \(u^7z^7\) cancellation.
3. Use an additive grading for the first surviving face and prove a support
   cutoff for omitted later velocity coefficients.
4. Replay the correctly right-placed source Magnus series and derive any
   persistent module from forward-`dexp`.
5. Independently bound the left-placed target logarithm from its
   instantaneous Newton support.

## Success and kill conditions

The candidate is excluded by one closed quotient with a nonzero all-order
source or target subsequence.  A bounded prefix is only candidate evidence.

A positive construction requires all-order upper bounds on both logarithms;
canceling the original coefficient without those bounds is insufficient.

## Exact Newton-support outcome

The cancellation removes the complete degree-fourteen cost-two face.  The
largest source Hamiltonian degrees by costs two through six are

\[
(12,16,18,20,20),
\]

so the bracket-adjusted ratios \((\deg H-4)/q\) are

\[
\left(4,4,\frac72,\frac{16}{5},\frac83\right).
\]

The two maximal terms are radial:

\[
-\frac{325}{2688}u^6z^6
\quad\text{at cost two},\qquad
-\frac1{14336}u^8z^8
\quad\text{at cost three}.
\]

They commute.  The exact perturbation Hamiltonian has total degree at most
twenty, so every cost \(q\ge4\) automatically satisfies

\[
\deg H\le4q+4.
\]

Together with the explicit costs two and three, the additive grading

\[
G_4=a+b-4q-4
\]

is nonpositive on the complete instantaneous connection.  Hence every
source logarithmic Hamiltonian obeys

\[
\deg\Omega_n^{\rm src}\le4n+4.
\]

On the target side, every instantaneous Hamiltonian has
\(\deg H-q-2\le0\).  Since the ordinary target Poisson bracket subtracts
two from total degree,

\[
\deg\Omega_n^{\rm tgt}\le n+2.
\]

Thus this exact connection has symmetric logarithmic upper rate at most
four.

The lower-bound test is the largest negative \(G_4\)-module under the two
commuting radial generators.  A nonzero orbit makes rate four sharp for
this connection; cancellation of all such modules would force a lower
Newton face.

## Excess-\(-7\) module outcome

The first persistent filtered module is \(G_4=-7\).  The exact replay is
nonzero at every logarithmic order from seven through thirty-six.  The two
zero-excess logarithmic generators are

\[
A=-\frac{325}{5376}u^6z^6
\quad\text{at cost two},\qquad
B=-\frac1{43008}u^8z^8
\quad\text{at cost three}.
\]

They commute.  On a monomial with exponent difference \(d=a-b\),

\[
\operatorname{ad}_A
\quad\text{multiplies by}\quad
-\frac{325}{896}d,
\]

and

\[
\operatorname{ad}_B
\quad\text{multiplies by}\quad
-\frac1{5376}d.
\]

Their scalar ratio is \(1/1950\).  In the \((q,d)\)-lattice, they act by

\[
(q,d)\mapsto(q+2,d+2),
\qquad
(q,d)\mapsto(q+3,d+2).
\]

Removing both radial origins leaves a finite \(G_4=-7\) core supported at
costs two through eleven.  Thus the all-order residual is a finite-core
module over two commuting shifts.

An attempted one-generator boundary reduction starts from
\(E_0=u^{13}z^{12}\) and follows \(\operatorname{ad}_A^kE_0\).  Its
polynomial-log forcing has the exact generating function

\[
\frac{65e^{-x}}{2774532096x^3}
\left(
5x^3e^x+20x^3-91x^2e^x+85x^2
-24xe^x-36x+60e^x-60
\right).
\]

For \(k\ge1\), the normalized forcing coefficient is

\[
\frac{65(-1)^k}{2774532096}
\frac{20k^3+35k^2-241k-438}{(k+3)!}.
\]

The scalar response equation fails first at adjoint depth three: a
neighboring \(G_4=-7\) orbit feeds the same boundary monomial.  Therefore
the nonzero prefix is not promoted to an all-order lower bound.

That coupling does not reach the first persistent triangular boundary.
Put

\[
h=q-(a-b).
\]

The cost-two adjoint \(A\) preserves \(h\), while the cost-three adjoint
\(B\) raises it by one.  The minimum boundary \(h=4\) terminates after the
single logarithmic term

\[
\frac{157}{2016}u^4z^5s^3.
\]

The next boundary \(h=5\) is closed under \(A\) and receives no feedback
from larger \(h\).  Use the orbit

\[
E_0=uz^4,\qquad
E_{k+1}=[A,E_k].
\]

Then

\[
E_k\ \text{has cost }2+2k
\quad\text{and exponent}\quad
(1+5k,4+3k).
\]

After division by the nonzero adjoint multipliers, let \(D(x)\) be the
logarithm on this orbit.  The finite-core elimination gives

\[
F(x)=\frac{227}{23400}(e^{-x}-1+x)
\]

for the external velocity and

\[
V(x)=-\frac1{336}+\frac{779}{23400}x
\]

for the actual instantaneous velocity.  The right-forward-`dexp` equation
is exactly

\[
2D+2(1-e^{-x})D'+F-V=0.
\]

Equivalently,

\[
\bigl((e^x-1)D\bigr)'=\frac12e^x(V-F).
\]

The regular solution is

\[
\boxed{
D(x)=
-\frac{221}{26208}
+\frac{23}{1950}x
+\frac{13}{1872}\frac{x}{e^x-1}.}
\]

Consequently, for \(k\ge2\),

\[
[x^k]D(x)
=\frac{13}{1872}\frac{B_k}{k!}.
\]

At \(k=2m\), \(m\ge1\), even-Bernoulli nonvanishing and the recurrence

\[
E_{k+1}
=-\frac{325}{896}(2k-3)E_k
\]

give a nonzero source Hamiltonian at logarithmic order

\[
n=2+4m
\]

with exponent \((1+10m,4+6m)\).  Its source derivation degree is

\[
(1+10m)+(4+6m)-3
=4n-6.
\]

The source rate is therefore exactly four for this connection.  Since the
target rate is at most one, its symmetric logarithmic rate is also exactly
four.

This improves the campaign-wide upper bound on the minimax statistic to
four.  It does not prove that every cone-compatible connection has rate at
least four; a richer cancellation direction could still lower the
minimax.

The replay, core enumeration, scalar equation, and held-out coefficient
checks are in
[`gauge_p2q_source_newton_modules.py`](gauge_p2q_source_newton_modules.py).
