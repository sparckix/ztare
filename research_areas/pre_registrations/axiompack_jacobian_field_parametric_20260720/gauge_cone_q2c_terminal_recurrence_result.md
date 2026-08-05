# All-order terminal ray from the delayed \(Q^2C\) prefix

## Result

Insert a nonzero row-one target prefix

\[
\lambda Q^2C,
\qquad
C=4P^3-P^2-18PQ+27Q^2+4Q,
\]

into the corrected logarithm-first radial cone staircase.  At the highest
power of \(\lambda\), the complete source logarithm has infinitely many
nonzero terminal Hamiltonians

\[
u^{12+7n}z^{16+7n}
\]

at costs \(5+2n\).  Their coefficients are

\[
\lambda^{n+2}p_ne_n,
\]

where

\[
p_0=1,\qquad
p_n=\frac98
\left(-\frac{63}{32}\right)^{n-1}
\left(\frac37\right)_{n-1}
\quad(n\ge1),
\]

and infinitely many \(e_n\) are nonzero.  Hence every
\(\lambda\ne0\) produces an unbounded source logarithm with limiting
spatial rate seven on this ray.

## Exact quotient

The prefix grading

\[
G(a,b;q)=(2a-7q-2,\ 2b-7q-6)
\]

has terminal grade \((-13,-9)\).  Every connection grade is
componentwise nonpositive, and the unique zero-grade logarithmic letter is

\[
A=-\frac9{64}u^8z^{10}.
\]

After the finite costs two and three, only three finite-core states can
reach the terminal grade.  Current \(C\)-seed columns have an exact
one-dimensional cokernel, and the remaining terminal feedback is linear.

At amplitude index \(k\), its cokernel ratio is

\[
\chi_k=
\frac{147k^2+49k+\delta_{k\bmod3}}
{6(21k+8)},
\qquad
(\delta_0,\delta_1,\delta_2)=(0,12,6).
\]

After sign rotation, the three-state transition is positive for
\(k\ge3\).  The scalar finite-core forcing \(D_k\) obeys

\[
D_{k+1}
=\frac{9(7k-18)}{32(k+1)}D_k
+\gamma_k\kappa_k,
\qquad
D_3=\frac{81}{16384},
\]

where \(\kappa_k>0\) and

\[
\gamma_k=
\begin{cases}
0,&k\equiv0\pmod3,\\[1mm]
\dfrac{189(k-2)}{32(k+1)(21k+8)},
&k\equiv1\pmod3,\\[3mm]
\dfrac{27(7k-10)}{32(k+1)(21k+8)},
&k\equiv2\pmod3.
\end{cases}
\]

Thus \(D_k>0\) for every \(k\ge3\).

## Response nontermination

Normalize the terminal coefficients by \(p_n\), and write

\[
E(x)=\sum_{n\ge0}e_nx^n.
\]

The exact right-forward-`dexp` equation reduces to

\[
2xf(x)E'(x)+(2+3f(x))E(x)=H(x),
\qquad
f(x)=\frac{1-e^{-x}}x.
\]

Its regular solution is

\[
E(x)=\frac{xJ(x)}{e^x-1},
\qquad
J(x)=
\frac1{2x^{5/2}}
\int_0^x e^t t^{3/2}H(t)\,dt.
\]

The positive core gives

\[
|H_n|\le\frac{2(n+2)^4}{(n+2)!},
\]

so \(H\) and \(J\) are entire.  An exact rational interval calculation
using Machin's formula for \(\pi\), one hundred coefficients, and the
displayed all-order tail bound proves

\[
\operatorname{Im}J(2\pi i)>\frac1{200}.
\]

Therefore \(E\) has a nonremovable pole at \(2\pi i\) and cannot be a
polynomial.  This proves that its terminal coefficient sequence has
infinite support.

## Verification and boundary

The deterministic replay is
[`gauge_cone_q2c_terminal_recurrence.py`](gauge_cone_q2c_terminal_recurrence.py).
It:

- derives the three residue-class cokernel formulas symbolically;
- checks the positive three-state recurrence;
- matches the scalar response to the full sparse quotient through depth
  forty;
- reproduces the unfiltered coefficients through cost eleven;
- certifies the complex evaluation and its infinite tail with rational
  bounds.

The theorem excludes the smallest delayed one-\(C\) escape.  It does not
classify arbitrary equal-weight discriminant combinations, arbitrary
finite one-\(C\) prefixes, or prefixes involving \(C^m\) with \(m\ge2\).
Those remain the unresolved finite-prefix classes behind a matching lower
bound for \(\sigma_{\rm ct}\).
