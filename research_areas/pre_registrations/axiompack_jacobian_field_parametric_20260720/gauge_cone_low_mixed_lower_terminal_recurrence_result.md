# Lower-ray obstruction for the exceptional mixed representatives

## Result

The two low mixed representatives \(PQ^2C\) and \(PQ^3C\) have finite
leading logarithmic windows, but neither gives a finite-prefix escape.
Their first persistent lower rays are

\[
\begin{aligned}
\Omega_{5+2n}(PQ^2C)
&=d^{(2)}_n u^{16+9n}z^{20+9n},
&&\Gamma=(-15,-11),\\
\Omega_{5+2n}(PQ^3C)
&=d^{(3)}_n u^{22+12n}z^{26+12n},
&&\Gamma=(-18,-14).
\end{aligned}
\]

The first three coefficients are

\[
\begin{array}{c|ccc}
&d_0&d_1&d_2\\ \hline
PQ^2C&
\dfrac{3159}{1310720}&
\dfrac{28431}{587202560}&
\dfrac{255879}{7516192768}\\[2mm]
PQ^3C&
\dfrac{729}{2621440}&
-\dfrac{6561}{4697620480}&
\dfrac{59049}{150323855360}.
\end{array}
\]

The exact five-column replay agrees through depth forty.  In
particular, the pre-recorded depth-twelve coefficients agree exactly:

\[
\begin{aligned}
d^{(2)}_{12}
&=-\frac{
55615691736622684675837754865
}{
18380933703309326321702196477952
},\\
d^{(3)}_{12}
&=-\frac{
16884595808465322118653
}{
22183885503994014526192306094080
}.
\end{aligned}
\]

## Two-state quotient

At each depth, the projected core has a terminal state and one
companion state.  Bracketing by the fixed cost-two letter is diagonal
on these two states.  The terminal multipliers are

\[
\alpha^{(2)}_n=\frac{27(9n-4)}{128},
\qquad
\alpha^{(3)}_n=\frac{27(1-3n)}{128}.
\]

Their only algebraic zeros are \(4/9\) and \(1/3\), respectively, so
neither vanishes at an integer depth.

The complete current row has five one-\(C\) columns.  The columns at
offsets \(-4,-3\) disappear below the projection, leaving two affine
directions.  Offset \(-2\) cancels only the companion state.  The
higher pivots at offsets \(-1,0\) force those two coefficients to zero
before the terminal equation.  Consequently the terminal quotient is
independent of both affine parameters at every depth.

The first bracketed core has terminal coefficients

\[
q_2=\frac{3159}{131072},
\qquad
q_3=\frac{729}{262144}.
\]

After division by the nonzero adjoint orbit, both cases have the same
scalar forcing:

\[
H_n=\frac{(-1)^nq_j}{(n+2)!},
\qquad
H(x)=q_j\frac{e^{-x}-1+x}{x^2}.
\]

## All-order nontermination

The normalized right-`dexp` response satisfies

\[
2xf(x)E'(x)+(2+3f(x))E(x)=H(x),
\qquad
f(x)=\frac{1-e^{-x}}x.
\]

Its regular solution is

\[
E(x)=\frac{xJ(x)}{e^x-1},
\qquad
[x^n]\frac{J(x)}{q_j}
=\frac{n+1}{(2n+5)(n+2)!}.
\]

A rational interval evaluation uses Machin's formula for \(\pi\),
fifty exact coefficients, and the tail estimate

\[
\frac{7^N}{2(N+2)!}\frac1{1-7/(N+3)}.
\]

It proves

\[
\operatorname{Im}\frac{J(2\pi i)}{q_j}>\frac1{200}.
\]

Thus \(J(2\pi i)\ne0\), while \(e^{2\pi i}-1=0\).  The response has a
nonremovable pole and is not a polynomial.  Infinitely many terminal
coefficients are nonzero.  Their limiting source rates are nine for
\(PQ^2C\) and twelve for \(PQ^3C\).

## One-\(C\) quotient boundary

The deterministic certificate is
[`gauge_cone_low_mixed_lower_terminal_recurrence.py`](gauge_cone_low_mixed_lower_terminal_recurrence.py).

At every fixed cusp weight, reduction modulo

\[
D=4P^3+27Q^2
\]

leaves a unique monomial \(P^aQ^b\) with \(a\in\{0,1,2\}\).  The
pure-\(Q\) results cover \(a=0\); the stable mixed \(\phi_2\) theorem
covers \(a=1,b\ge4\) and \(a=2,b\ge3\); the result above covers the
remaining \(a=1,b=2,3\) representatives.  Therefore every admissible
nonzero one-\(C\) class modulo \(D\) excites an infinite source
logarithmic ray.

This does not yet show that multiplication by a positive power of
\(D\) preserves a nonzero quotient.  Finite \(D\)-adic depth and
higher powers \(C^m\), \(m\ge2\), remain outside the theorem.
