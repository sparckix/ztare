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

## Conditional two-sided finite critical factorization

The same branch supplies the local obstruction needed to exclude arbitrary
finite critical prefixes on both sides, once a selected two-flow
factorization has been continued to the punctured critical chart with both
Julia rows.  Suppose that continuation data give a factorization

\[
F=\exp(g\partial_x)\circ\exp(f\partial_x)(x),
\qquad f,g\in x^2\mathbb Q[x].
\]

If both selected factor branches remain finite and regular at their endpoint
centers, analytic Abel-coordinate descent makes the composition analytic
there.  This does not cover a branch that moves between two finite
equilibria.  If instead the inner flow reaches infinity and the outer flow
returns from infinity, then for a
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

The degree comparison and collision argument are all-degree.  They do not
construct the selected punctured branch from a bare factorization identity.
They also do not exclude equilibrium-to-equilibrium continuation.  The exact
replay
[`gauge_equilibrium_transition_puiseux_collision.py`](gauge_equilibrium_transition_puiseux_collision.py)
constructs generators in (x^2\mathbb Q[x]) whose two local Julia branches
have exponent ratios (3/2) and (2/3) and compose as

\[
u+\frac{77}{12}u^2+\frac{376}{81}u^{5/2}+O(u^3).
\]

Thus the critical linear-plus-(5/2) signature does not separate this finite
equilibrium route.  The Jacobian specialization still imposes the additional
arithmetic condition that the fixed endpoint value (F(-2)) be algebraic if
it is a root of a polynomial over (\mathbb Q).

The exact rationalized-monodromy replay supplies a stronger global lever.
On the conic parameter (x=6(t^2-1)/(t^2+3)),

\[
d\log F=
\frac{896t(t-3)(t+1)(t^2-6t-3)}{(t-1)Q(t)}\,dt,
\]

where the degree-seven (Q) and its degree-seven residue resultant are both
irreducible modulo (17).  A residue (\rho) over a root of (Q) is therefore
irrational, so (\exp(2\pi i\rho)) has infinite order: a positive torsion
power would force (\rho\in\mathbb Q) through the kernel of complex
exponential.  Thus the scalar critical endpoint has an infinite monodromy
orbit.

This does not yet lift the repeated scalar loops through an arbitrary
two-factor continuation.  Once that lift is constructed, finite iterates
cannot all be equilibrium transitions because the outer generator has a
finite root set; some iterate must enter the nonfinite carrier already
excluded by the local kernel.

The current Filtered Obstruction Compiler certificate conflates those two
propositions: its factorization-identity receipt also triggers the regular
route, through-infinity degree comparison, and proportional reduction.  That
certificate omits the equilibrium-transition branch and therefore records a
conditional implication rather than an unconditional exclusion.

## Boundary

The one-flow critical special fiber is excluded.  The two-flow local sink is
also kernel-checked after construction of a
`TwoFlowRamifiedCrossCarrier`, but the global selected-continuation theorem
that constructs this carrier from an arbitrary finite factorization remains
open.  An arbitrary selected factorization may instead enter the newly
identified equilibrium-transition route, whose global time normalization
and endpoint arithmetic are unresolved.  The scalar endpoint's infinite
monodromy orbit is exact; the remaining proposition is its transfer through
the selected factorization.  Finite supercritical/polar-prefix
removal is proved conditionally on a terminal that excludes both branches:
every such prefix either creates a same-order rate-two payment or descends to
the unresolved selected critical factorization.
