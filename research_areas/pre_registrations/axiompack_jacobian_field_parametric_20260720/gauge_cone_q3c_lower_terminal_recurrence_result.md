# Lower-grade obstruction for the \(Q^3C\) prefix

## The leading cancellation is not an escape

The complete \(Q^3C\)-dependent source logarithm terminates through cost
nine in the leading grade window \(\Gamma\ge(-8,-8)\).  Descending one
additive layer exposes a new ray at grade \((-16,-12)\):

\[
\Omega^{\rm src}_{5+2n}
=d_nu^{18+10n}z^{22+10n}.
\]

Its first coefficients are

\[
d_0=\frac{729}{2621440},\qquad
d_1=\frac{729}{146800640},\qquad
d_2=\frac{190269}{300647710720}.
\]

The full projected staircase verifies these three rows.  The reduced
recurrence reproduces them and remains nonzero through depth forty.

## Exact cokernel and finite core

The cost-two zero-grade letter acts on the ray by

\[
\operatorname{ad}_A F_k
=\frac{9(5k-2)}{64}F_{k+1}.
\]

Five current one-\(C\) columns have two affine directions at every row.
The terminal coefficient is independent of both.  A cokernel vector
supported on the transverse and terminal states has coefficient

\[
\chi_k
=-\frac{150k^2+635k+673+\delta_{k\bmod3}}{27},
\qquad
(\delta_0,\delta_1,\delta_2)=(0,-3,3).
\]

Only three core states feed this cokernel.  Their exact transition is

\[
\begin{aligned}
T_{k+1}
&=\frac{9(10k+1)}{128}T_k,\\
C_{k+1}
&=-\frac{105(5k+3)}{128}T_k
  +\frac{9(20k-13)}{256}C_k,\\
E_{k+1}
&=\frac{51(20k+17)}{128}T_k
  -\frac{105(10k+1)}{256}C_k
  +\frac{9(5k-7)}{64}E_k,
\end{aligned}
\]

with

\[
(T_0,C_0,E_0)
=\left(-\frac{27}{2048},
\frac{57}{1024},
-\frac{191}{2048}\right).
\]

The residue-class formula for \(\chi_k\) is derived from the
\(t^4z^2\) coefficient of the normalized current \(C\)-seed.  It is
therefore independent of the two affine control parameters.

## All-order nontermination

After dividing by the adjoint orbit, write

\[
E(x)=\sum_{n\ge0}e_nx^n.
\]

The right-forward-`dexp` relation is

\[
2xf(x)E'(x)+(2+3f(x))E(x)=H(x),
\qquad
f(x)=\frac{1-e^{-x}}x.
\]

The regular solution is

\[
E(x)=\frac{xJ(x)}{e^x-1}.
\]

The normalized three-state recurrence admits the all-order bound

\[
|H_n|
\le
\frac{130(n+2)^4}{(n+2)!}.
\]

Thus \(H\) and \(J\) are entire.  Using one hundred exact coefficients,
Machin's formula for \(\pi\), alternating rational remainders, and the
displayed majorant for the omitted tail gives

\[
\boxed{\operatorname{Im}J(2\pi i)>\frac1{4000}}.
\]

Consequently \(E\) has a nonremovable pole at \(2\pi i\) and cannot be
a polynomial.  Infinitely many \(d_n\) are nonzero.  Their exponents
grow by \((10,10)\) while their costs grow by two, so the lower-grade
ray has limiting source rate ten.

## Verification and boundary

The deterministic replay is
[`gauge_cone_q3c_lower_terminal_recurrence.py`](gauge_cone_q3c_lower_terminal_recurrence.py).
It derives the residue-class cokernel, verifies the triangular
three-state transition, matches the full recurrence, proves the core
majorant by induction, and performs the rational complex-evaluation
certificate.

Together with the \(Q^2C\) recurrence and the uniform cost-four theorem
for \(Q^bC\), \(b\ge4\), this excludes every pure-\(Q\) one-\(C\)
monomial.  Mixed one-\(C\) leading combinations and powers \(C^m\) with
\(m\ge2\) remain outside the result.
