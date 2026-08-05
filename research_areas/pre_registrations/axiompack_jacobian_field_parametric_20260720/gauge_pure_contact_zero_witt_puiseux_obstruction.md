# Pure contact-zero Witt Puiseux obstruction

## Result

For the canonical pure-parity radial normalization, the critical
normal-two logarithm has infinitely many nonzero coefficients.  This is an
all-index statement, rather than an inference from the checked recurrence
rows.

Let \(V(x)\) be the exact algebraic normal-two instantaneous connection and
let \(F\) be the inverse radial holonomy.  The radial characteristic equation
gives

\[
\frac{F'(x)}{F(x)}=\frac1{x(1+2xV(x))}.
\]

At \(x=-2\), with \(u=x+2\), the velocity has

\[
V(x)=V_{\rm an}(u)-\frac{25\sqrt6}{672}u^{3/2}
+O(u^{5/2}),
\]

and

\[
1+2xV(x)\big|_{x=-2}=\frac{107}{112}\ne0.
\]

Consequently

\[
F(x)=F(-2)+F'(-2)u+\cdots
+F(-2)\frac{1120\sqrt6}{34347}u^{5/2}
+O(u^3),
\]

where \(F(-2)\ne0\) and \(F'(-2)\ne0\).

Suppose the critical Witt logarithm were polynomial, and write its inverse
flow generator as \(f(x)\partial_x\).  Its time-one map obeys Julia's
equation

\[
f(F(x))=F'(x)f(x).
\]

If \(f(-2)\ne0\), the right side has a nonzero \(u^{3/2}\) term while the
left side first sees the branch at \(u^{5/2}\), a contradiction.  Hence
\(f\) must vanish at \(-2\).  If its root multiplicity is \(m\), the leading
analytic term of \(F\) forces \(F(-2)\) to be a root of the same
multiplicity.  After the common \(u^m\) factor is removed, the first
fractional coefficient is

\[
m\frac c{F'(-2)}
\quad\text{on the left, and}\quad
\frac52\frac c{F'(-2)}
\quad\text{on the right},
\]

with \(c\ne0\).  Thus \(m=5/2\), impossible for a polynomial root.

The deterministic replay
[gauge_pure_contact_zero_witt_puiseux_obstruction.py](gauge_pure_contact_zero_witt_puiseux_obstruction.py)
checks the exact branch coefficients, the radial characteristic equation,
and the Julia equation against the typed Magnus recurrence.

## Two-sided finite critical factorization

The same branch also excludes arbitrary finite critical prefixes on both
sides.  Suppose the critical special fiber factored as

\[
F=\exp(g\partial_x)\circ\exp(f\partial_x)(x),
\qquad f,g\in x^2\mathbb Q[x].
\]

If both factors remain finite at (x=-2), analytic dependence for a
polynomial ODE makes the composition analytic there.  Otherwise the inner
flow reaches infinity and the outer flow returns from infinity.  For a
degree-(d) polynomial field, its time coordinate at infinity starts in
degree (z^{-(d-1)}).  The nonzero linear term of (F) therefore forces
the two polynomial degrees to agree.

Normalize their leading coefficients and let (e\ge2) be the largest
degree at which the two generators differ.  Comparing their time
coordinates at infinity gives the first fractional exponent

\[
1+\frac{d-e}{d-1},
\]

which lies strictly between one and two.  It cannot equal the first
fractional exponent (5/2) of (F).  If no such (e) exists, the two
generators are proportional, their flows combine into one polynomial flow,
and the Julia obstruction above applies.

This is an all-degree argument.  The Filtered Obstruction Compiler emits a
separate two-flow Puiseux certificate binding the regular route, the
through-infinity degree comparison, and the proportional reduction.

## Boundary

The two-sided finite critical special fiber is excluded.  The remaining
unrestricted step is finite supercritical/polar-prefix removal: one must
show that every such prefix either creates a same-order rate-two payment or
descends, after an exact inverse-flow boundary, to the critical
factorization handled here.
