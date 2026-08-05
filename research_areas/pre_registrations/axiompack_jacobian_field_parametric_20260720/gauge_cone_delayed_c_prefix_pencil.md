# Delayed finite \(C\)-prefix control of the negative-normal quotient

## Claim boundary

The logarithm-first radial plus one-\(C\)-layer staircase leaves a
negative-normal source quotient of slope two.  Current-row \(C\)-directions
cannot act on it directly because they begin in normal order two.  The tail
statistic, however, permits an expensive finite prefix.  This pencil tests
whether an earlier \(Q^2C\) row changes the later quotient through delayed
Magnus brackets.

## Eigenquestion

If a free coefficient

\[
\lambda Q^2C
\]

is inserted in target row one after the local logarithmic normalization,
does the leading negative-normal coefficient at target orders eight,
nine, or ten depend nontrivially on \(\lambda\)?

## Filtration mechanism

In the \((r,z)\) normal filtration, \(Q^2C(F_0)\) begins in normal order
two.  The density-\(z^2\) Hamiltonian bracket lowers the sum of normal
orders by two:

\[
\nu(\{H,K\})=\nu(H)+\nu(K)-2
\]

on nonvanishing leading symbols.  Therefore a \(C\)-prefix cannot change
the first negative-normal shell immediately, but words containing that
prefix and enough normal-one letters can reach normal order zero and then
negative order at later logarithmic costs.

The prefix is deliberately added after solving row one.  Re-normalizing its
second-normal shell at the same row would set the free parameter back to
zero and would not test the tail-relevant finite-prefix freedom.

## Discriminating replay

1. Add an optional exact rational \(\lambda Q^2C\) to target order one
   after the row-one radial and second-normal solves.
2. Keep the corrected target-lift support and assert polynomial source
   Hamiltonians at every instantaneous row.
3. Carry the logarithm-first radial and current \(C\)-normal solves through
   target order ten.
4. Evaluate at least three rational values of \(\lambda\), including zero,
   and interpolate the first affected negative-normal top coefficient.
5. If dependence is nontrivial, solve the earliest coefficient equation
   exactly and replay that value at the next two affected orders.
6. Compare source and target logarithmic degree profiles and run oriented
   round trips on any promoted prefix.

## Success and kill conditions

The delayed-control mechanism advances if a later leading
negative-normal coefficient depends nontrivially on \(\lambda\) while all
instantaneous source rows remain polynomial.  A single canceled order is
only a controllability witness; promotion below rate two requires the same
value or a finite family of prefix parameters to control an infinite tail.

The mechanism is killed at first order if every negative-normal top
coefficient through the first filtration-reachable window is independent
of \(\lambda\).  It is also killed by loss of polynomial source
admissibility, target rate matching the source rate, or cancellation that
requires infinitely many coefficients in target row one.

Even a positive finite result does not determine \(\sigma_{\rm ct}\).
The successor would need a closed delayed-control recurrence or an
invariant quotient proving that every finite \(C\)-adic prefix leaves a
nonzero slope-two orbit.

## Exact outcome

The delayed coefficient does not change the first negative-normal quotient
through target order six.  Instead it creates a higher-degree self-cascade.
For exact amplitudes \(\lambda=-1,1,2\), interpolation gives

\[
\boxed{
[u^{15}z^{18}]\Omega^{\rm src}_6
=\frac{33}{16384}\lambda^2,
}
\]

and

\[
\boxed{
[u^{19}z^{23}]\Omega^{\rm src}_7
=-\frac{1377}{9175040}\lambda^3.
}
\]

Thus every tested nonzero amplitude has logarithmic Hamiltonian degrees
\(33,42\) at these two orders, compared with \(16,16\) for
\(\lambda=0\).  All instantaneous source rows remain polynomial, so this
is a Lie-growth effect rather than a category failure.

The one-parameter delayed-control vector is therefore killed in the finite
window: it worsens the source envelope before changing the intended
quotient.  The calculation does not yet prove that its self-cascade
continues at all orders.  The successor must test whether the
highest-weight term of an arbitrary finite \(C\)-prefix always supplies a
nonzero triangular self-cascade that lower prefix terms cannot cancel.

## All-order successor

The \(Q^2C\) self-cascade does continue at infinitely many orders.  The
leading-amplitude quotient has one zero-grade letter, a positive
three-state forcing core, and an exact scalar response

\[
E(x)=\frac{xJ(x)}{e^x-1}.
\]

A rational interval certificate proves

\[
\operatorname{Im}J(2\pi i)>\frac1{200},
\]

so the response has a nonremovable pole and cannot terminate.  For every
\(\lambda\ne0\), infinitely many terminal terms

\[
\lambda^{n+2}u^{12+7n}z^{16+7n}
\]

survive at costs \(5+2n\), up to explicit nonzero rational orbit factors.
The exact reduction is in
[`gauge_cone_q2c_terminal_recurrence.py`](gauge_cone_q2c_terminal_recurrence.py),
with the theorem boundary summarized in
[`gauge_cone_q2c_terminal_recurrence_result.md`](gauge_cone_q2c_terminal_recurrence_result.md).

This settles the declared one-parameter test.  It does not settle mixed
equal-weight prefixes or higher \(C\)-adic layers.
