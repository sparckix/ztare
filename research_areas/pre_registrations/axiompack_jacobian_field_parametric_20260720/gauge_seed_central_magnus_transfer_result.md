# Seed-central Magnus transfer

## Result

Let

\[
H_0=-\frac1{36}P^3-\frac14Q^2
\]

be the target Hamiltonian at the distinguished fiber of the normalized
global connection.  The order-one perturbation

\[
K_s^{\rm cent}=K_s-\frac9{28}sH_0^2
\]

cancels the previously identified source zero-grade generator.  It does
not give a bounded logarithm.  The complete source pullback

\[
-\frac{18}{7}sH_0(P_s,Q_s)^2
\]

creates a second closed quotient with a nonzero source-logarithmic
subsequence.

For every \(m\ge0\), at logarithmic order

\[
n=6+4m
\]

the source Hamiltonian contains a nonzero multiple of

\[
u^{23+22m}z^{22+18m}.
\]

The corresponding source derivation degree is

\[
\boxed{10n-18}.
\]

Consequently the seed-central cancellation candidate has unbounded source
logarithmic degree.

## Closed quotient

For \(u^az^b\) at parameter cost \(q\), use

\[
(I,J)=(2a-11q-2,\ 2b-9q-6).
\]

In the southwest rectangle with terminal grade \((-22,-16)\), only
instantaneous costs two and four survive.  The cost-two logarithm has the
unique zero-grade generator

\[
A=-\frac9{458752}u^{12}z^{12}.
\]

The direct terminal cost-four coefficient is

\[
-\frac{111}{3670016}u^{12}z^{13}.
\]

The other negative-grade terms alter its first radial iterate by the exact
nonzero factor \(-12/37\).  Once the terminal grade is reached, every later
outer bracket is forced to use \(A\).  The iterated coefficients therefore
obey the nonvanishing recurrence

\[
r_{k+1}
=-\frac{27}{114688}(2k-1)r_k
\qquad(k\ge1).
\]

## Magnus response

The terminal right-Magnus response is

\[
\phi_3(x)
=\frac{x}{e^x-1}\int_0^1t^3e^{t^2x}\,dt
=\frac12+
\frac1{2x}\left(\frac{x}{e^x-1}-1\right).
\]

For \(k\ge1\),

\[
[x^k]\phi_3(x)=\frac{B_{k+1}}{2(k+1)!}.
\]

At odd depths \(k=2m+1\), the Bernoulli index is positive and even, so its
coefficient is nonzero.  The exponent recurrence is

\[
(a_k,b_k)=(12+11k,\ 13+9k),
\]

which gives the displayed order and degree formula.

## Verification and boundary

The exact replay is
[`gauge_seed_central_magnus_transfer.py`](gauge_seed_central_magnus_transfer.py).
It reconstructs the perturbation from the family, verifies the quotient
support, checks the finite-core factor, derives the universal response, and
replays the orbit through depth twenty.

The Lean endpoint
[`AxiomPackJacobianSeedCentralMagnusTransferArithmetic.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianSeedCentralMagnusTransferArithmetic.lean)
checks the recurrence nonvanishing, Bernoulli-factor transfer, degree
arithmetic, and unbounded certified subsequence.  It does not encode the
symbolic Hamiltonian projection.

This excludes one exact cancellation direction.  It does not prove a
minimax lower bound over arbitrary coefficientwise-polynomial
source/target connections.
