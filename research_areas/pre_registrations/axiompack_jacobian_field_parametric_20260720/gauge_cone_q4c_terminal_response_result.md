# Delayed Bernoulli ray from the \(Q^4C\) prefix

## Result

The row-one prefix \(\lambda Q^4C\) defeats the first proposed
weight-only recurrence: its complete prefix-dependent logarithmic
coefficient at cost three is zero after the current radial and one-\(C\)
normalization.  It does not provide a finite-prefix escape.

In the deeper grading

\[
G(a,b;q)=(2a-13q-2,\ 2b-13q-6),
\]

the prefix has the unique zero-grade logarithmic letter

\[
A=-\frac9{1024}u^{14}z^{16}
\]

at cost two.  Its first surviving terminal input is instead the cost-four
velocity

\[
V_{\rm term}
=\frac5{1024}u^{14}z^{17},
\qquad
G(14,17;4)=(-26,-24).
\]

No later instantaneous input occurs at that grade.  Every negative-grade
outer letter leaves the quotient, so all later terminal brackets use
\(A\).

## Closed response

Put

\[
E_k=u^{14+13k}z^{17+13k}.
\]

Direct density-\(z^2\) Hamiltonian bracketing gives

\[
[A,E_k]
=\frac{9(7-13k)}{512}E_{k+1}.
\]

The multiplier is nonzero for every integer \(k\ge0\).  The terminal
right-Magnus response to a cost-four velocity is

\[
\phi_3(x)
=\frac{x}{e^x-1}\int_0^1t^3e^{t^2x}\,dt.
\]

Its constant coefficient is \(1/4\), and for \(k\ge1\),

\[
[x^k]\phi_3(x)
=\frac{B_{k+1}}{2(k+1)!}.
\]

Hence every odd depth \(k=2m+1\) is nonzero.  The corresponding
Hamiltonian is a nonzero multiple of

\[
u^{27+26m}z^{30+26m}
\]

at cost

\[
6+4m.
\]

The leading-amplitude source ray therefore has limiting spatial rate
thirteen.

## Verification and boundary

The complete projected staircase checks:

- exact disappearance of the prefix-dependent cost-three row;
- the cost-four velocity coefficient \(5/1024\);
- the cost-four logarithmic coefficient \(5/4096\);
- the cost-six quadratic coefficient \(105/4194304\);
- absence of any cost-six terminal velocity input.

The all-order response and held-out coefficients are replayed by
[`gauge_cone_q4c_terminal_response.py`](gauge_cone_q4c_terminal_response.py).

This excludes the first monomial for which the cost-three terminal seed
vanishes.  It does not classify arbitrary \(P^aQ^bC\), equal-weight
combinations that cancel the zero-grade letter, or higher powers of \(C\).
