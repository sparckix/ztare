# Uniform cost-four transfer for \(Q^bC\), \(b\ge4\)

## Symbolic source quotient

For the covariantly completed target prefix

\[
G_b=Q^bC,
\qquad b\ge6,
\]

use the fixed source chart \(r=uz\) and factor the common leading scale
\((-1/4)^b r^{3b}\).  Exact generalized-binomial reduction through
cost four gives, at radial offset two,

\[
\operatorname{coeff}_{r^{3b+2}z^2}=0,
\qquad
\operatorname{coeff}_{r^{3b+2}z^3}
=\frac{9b+4}{32}.
\]

Restoring the common scale yields the source-velocity coefficient

\[
\boxed{
B_b=\frac{(-1)^b(9b+4)}{2^{2b+5}}}
\]

on \(u^{3b+2}z^{3b+5}\).  It is nonzero for every integer \(b\ge6\).
The quotient is symbolic in \(b\); the values \(b=6,\ldots,12\) are
instantiations of the identity rather than interpolation inputs.

The two smaller delayed cases agree with the same formula.  The
\(b=4\) certificate is the previously established \(Q^4C\) response.
For \(b=5\), the complete replay inserts the only cone-valued covariant
successor \(G_1\) and gives

\[
\operatorname{term}V_4
=-\frac{49}{32768}u^{17}z^{20},
\qquad
\operatorname{term}V_6=0,
\]

and

\[
[u^{33}z^{36}]\Omega^{\rm src}_6
=\frac{2499}{1073741824}.
\]

Thus the cost-four transfer formula holds for every \(b\ge4\).

## All-order terminal response

The zero-grade logarithmic letter is

\[
A_b=
\frac{(-1)^{b+1}9}{2^{2b+2}}
u^{3b+2}z^{3b+4}.
\]

Put

\[
E_{b,k}
=u^{3b+2+(3b+1)k}
z^{3b+5+(3b+1)k}.
\]

The density-\(z^2\) bracket gives

\[
[A_b,E_{b,k}]
=\frac{(-1)^b9
\bigl(3b+2-2(3b+1)k\bigr)}
{2^{2b+2}}E_{b,k+1}.
\]

The multiplier has no integral zero.  The cost-four right-Magnus
response is

\[
\phi_3(x)
=\frac{x}{e^x-1}\int_0^1t^3e^{t^2x}\,dt,
\]

whose positive-depth coefficients are

\[
[x^k]\phi_3(x)=\frac{B_{k+1}}{2(k+1)!}.
\]

Every odd depth \(k=2m+1\) survives.  The corresponding logarithmic
Hamiltonians occur at costs \(6+4m\), with exponents

\[
\bigl(
6b+3+2(3b+1)m,\
6b+6+2(3b+1)m
\bigr).
\]

Their limiting source rate is \(3b+1\).

## Verification and boundary

The symbolic replay is
[`gauge_cone_qbc_uniform_cost_four.py`](gauge_cone_qbc_uniform_cost_four.py).
It derives the source family coefficients, the target covariant rows
\(G_0,G_1,G_2\), both triangular current normalizers, the displayed
terminal quotient, and the odd-depth response.

Together with the \(Q^4C\) and \(Q^5C\) projected checks, this excludes
every delayed pure-\(Q\) one-\(C\) prefix \(Q^bC\) with \(b\ge4\).
The immediate-exit \(Q^2C\) prefix is covered by its separate
three-state theorem, and \(Q^3C\) by its lower-grade recurrence.
Mixed one-\(C\) leading terms and powers \(C^m\) with \(m\ge2\) are
outside this result.
