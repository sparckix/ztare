# \(Q^3\)-cancellation source Magnus escape

## Result

Consider the normalized global target connection with the order-one
perturbation

\[
K_s^{\rm new}=K_s-\frac{s}{56}Q^3.
\]

This perturbation cancels the original rate-five source generator.  Its
first rate-seven source face also has zero Magnus response.  Nevertheless,
the next closed source excess module survives at every order

\[
n=6+4m.
\]

At those orders the source logarithm contains a nonzero multiple of

\[
u^{17+16m}z^{16+12m},
\]

so its source derivation degree is

\[
\boxed{7n-12}.
\]

The \(Q^3\) cancellation therefore has unbounded source logarithmic degree.

## Closed excess quotient

For \(u^az^b\) at parameter cost \(q\), define

\[
G=a+b-7q-4.
\]

The Hamiltonian bracket for density \(z^2\) adds this excess.  The unique
zero-excess logarithmic generator is

\[
A=\frac1{896}u^9z^9.
\]

The exact family has base Hamiltonian exponents at most nine.  The
perturbation source Hamiltonian is \(-sQ_s^3/7\), and the exponents of
\(Q_s\) are at most four, so its cube has exponents at most twelve.  Total
Hamiltonian degree is therefore at most \(24\).  Costs six and above lie
strictly below \(G=-20\), making the declared filtered replay independent
of later velocity coefficients.

The first surviving orbit is at \(G=-13\).  With

\[
E_0=u^{17}z^{16},\qquad E_{k+1}=[A,E_k],
\]

one has

\[
E_k=
\left(
\prod_{j=0}^{k-1}\frac{9(2j+1)}{896}
\right)
u^{17+8k}z^{16+6k}.
\]

## Exact response

Outside this orbit, the filtered logarithm stops at cost five.  Its exact
forward-`dexp` forcing is

\[
F(x)
=-\frac{27}{12845056}
\frac{x-1+e^{-x}}{x^2}.
\]

Writing the orbit correction as \(s^6D(x)E_0\), with
\(x=s^2\operatorname{ad}_A\), gives

\[
2D+\frac{1-e^{-x}}x(4D+2xD')+F=0.
\]

The diagonal coefficient is \(2(k+3)\), and the unique solution is

\[
D(x)
=\frac{27}{12845056x^2}
\left(
\frac{x}{e^x-1}-1+\frac x2
\right).
\]

Thus the depth-\(k\) coefficient is

\[
\frac{27}{12845056}
\frac{B_{k+2}}{(k+2)!}
\prod_{j=0}^{k-1}\frac{9(2j+1)}{896}.
\]

For \(k=2m\), every factor is nonzero.

## Verification and boundary

The replay
[`gauge_q3_source_excess_modules.py`](gauge_q3_source_excess_modules.py)
reconstructs the family, proves the support cutoff, checks the finite
forcing coefficient formula, verifies the formal response identity, and
independently replays the orbit through order thirty-six.

The Lean endpoint
[`AxiomPackJacobianQ3SourceMagnusEscapeArithmetic.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianQ3SourceMagnusEscapeArithmetic.lean)
checks radial-chain nonvanishing, transfer of the positive even-Bernoulli
recurrence, the degree identity, and the unbounded certified subsequence.
It does not encode the Hamiltonian quotient.

This excludes this exact order-one cancellation.  It does not give a
minimax lower bound over later coefficientwise-polynomial moving
connections.
