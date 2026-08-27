# Formal local-germ and autonomous-flow kernel pencil

**Date:** 2026-08-02
**Status:** pre-registered; first formal-series lane active

## Eigenquestion and target input

Can the exact seven-node residual left by the formal-coverage compiler be
reduced by proving its three leaves from constructed formal objects, followed
by its three inference rules and direct root theorem, without replacing any
adapter statement by a weaker proposition?

No external Jacobian-conjecture axiom is admitted.  The target inputs are the
already governed rational identities for the critical algebraic connection,
the standard laws of formal power series and autonomous flows, and exact
polynomial degree identities.  The intended output remains confined to the
normalized critical Puiseux terminal already named by the coverage DAG.

## Governing identities

The local-germ object is a selected formal square root in the ramified
coordinate `u=t^2`.  Its identity consists of:

1. coefficient ring and formal parameter;
2. the equation `S(t)^2 = 24 - 3*t^2`;
3. the selected constant coefficient `2*sqrt(6)`;
4. the fixed algebraic connection and radial differential equation; and
5. normalization of the endpoint relative to its nonzero regular factor.

The flow object is a formal one-parameter substitution action together with
its side of composition, time-zero identity, semigroup law, and infinitesimal
generator.  A finite Taylor table is evidence only for orientation; it is not
the identity of an all-order flow.

The two-flow object is a composition of two polynomial autonomous time-one
maps.  Its alternatives are finite-chart continuation, a through-infinity
chart with its exact degree pair, and proportional generators reducing the
composition to one flow.

## Candidate local-germ theorem

Use Mathlib's `PowerSeries.binomialSeries` and substitution to construct

\[
S(t)=2\sqrt6\,(1-t^2/8)^{1/2}.
\]

The binomial addition law should prove

\[
S(t)^2=24-3t^2,
\qquad [t^0]S=2\sqrt6.
\]

With `x=t^2-2`, the governed radical quotient has first even coefficient
`-25/1344`; hence its product with `t*S(t)` has

\[
[t^3]V=-\frac{25}{672}\sqrt6.
\]

At the regular value `V(0)=5/448`, the first odd coefficient of

\[
L=\frac1{x(1+2xV)}
\]

is

\[
[t^3]L=\frac{2800}{34347}\sqrt6.
\]

Formal integration in `u=t^2` then gives the normalized endpoint coefficient

\[
\frac25[t^3]L=\frac{1120}{34347}\sqrt6\ne0
\]

at exponent `u^(5/2)`.  The theorem must construct `S`; a hypothesis of the
form “assume the endpoint coefficient” is forbidden.

## Candidate Julia theorem

For an autonomous formal flow `Phi`, use the semigroup identity

\[
\Phi_{s+t}(x)=\Phi_s(\Phi_t(x)).
\]

Differentiation in `s` at zero gives the generator evaluated at the endpoint;
differentiation in `t` through the outer substitution gives the spatial
derivative times the generator.  Equating the two derivatives yields

\[
f(\Phi_t(x))=\partial_x\Phi_t(x)f(x)
\]

coefficientwise, and hence at time one.  The formal surface must expose the
semigroup and infinitesimal-generator premises and derive Julia; Julia itself
may not appear among the premises.

## Candidate two-flow theorem

Let polynomial generators have degrees `d,e>1`.  Separate:

1. both time-one continuations remain in a finite chart;
2. an intermediate value reaches infinity, where reciprocal-coordinate
   leading balance either has unequal degrees and first fractional exponent
   `1+(d-e)/(d-1)` in `(1,2)`, or equal degrees; and
3. equal leading transport continues to the proportional-generator case,
   which reduces to a single autonomous flow.

The existing governed interval theorem pays only the numerical `(1,2)` step.
The new theorem must pay exhaustiveness, chart passage, and proportional
reduction.  If a nonproportional equal-degree cancellation survives, the
claimed trichotomy is false and the structural statement must be narrowed in
the coverage DAG rather than hidden.

### Reciprocal-coordinate audit before formalization

The current compiler does not yet pay that theorem: it accepts a caller-owned
`TWO_FLOW_FACTORIZATION_IDENTITY` receipt and then records the finite,
infinity, and proportional conclusions.  The equal-degree calculation can be
separated from the unresolved analytic-continuation statement.

For a degree-`d` generator

\[
f(x)=a_dx^d+\cdots+a_2x^2,
\]

put `z=1/x` and normalize

\[
\widehat f(z)=\frac{z^df(1/z)}{a_d}=1+\cdots .
\]

Its time one-form is

\[
\frac{dx}{f(x)}=-\frac{z^{d-2}}{a_d\widehat f(z)}\,dz.
\]

After the leading time scales are normalized, suppose two equal-degree
generators first differ at the largest polynomial degree `e`.  Then
`\widehat f-\widehat g` first differs in reciprocal degree `d-e`.  Since both
reciprocal denominators have constant coefficient one,

\[
\widehat f^{-1}-\widehat g^{-1}
=\widehat f^{-1}(\widehat g-\widehat f)\widehat g^{-1}
\]

has the same first degree.  Multiplication by `z^(d-2)` and formal primitive
therefore put the first normalized time-coordinate difference in degree

\[
(d-2)+(d-e)+1=2d-e-1.
\]

The common leading time coordinate has degree `d-1`, so the induced
transition exponent is

\[
\frac{2d-e-1}{d-1}=1+\frac{d-e}{d-1}.
\]

Because tangent-to-identity generators have no constant or linear term,
nonproportional normalized generators give `2 <= e < d`; if no such `e`
exists, coefficient extensionality makes them proportional.  This audit
survives the equal-degree counterattack.  It does **not** by itself prove that
every nonanalytic finite germ factorization must pass through this infinity
chart.  The formal DAG must split those two claims if the analytic route
cannot be derived from a polynomial-ODE continuation theorem.

### Proportional-flow identity split before formalization

The proportional branch contains two logically distinct steps.  If one
selected one-parameter substitution flow is written as `Phi_t`, its defining
semigroup law gives, for every scalar `c`,

\[
\Phi_1\circ\Phi_c=\Phi_{1+c}.
\]

Reparameterizing by `a` via `Psi_t=Phi_{at}` is again a substitution flow,
and its time-one endpoint is `Phi_a`.  Consequently

\[
\Phi_1\circ\Phi_c=(\operatorname{reparam}_{1+c}\Phi)_1.
\]

This is the formal semigroup/rescaling mechanism and can be proved without
an ODE existence theorem.  The separate analytic statement is that the
selected time-one branch of the proportional generator `c*f` is the branch
`Phi_c` of the same continued flow.  That statement uses local ODE
uniqueness together with branch/continuation compatibility.  A theorem that
assumes the second endpoint is already `Phi_c` may pay the first step only;
it may not be advertised as paying the analytic identification.  The
coverage DAG must expose both nodes until the uniqueness bridge is supplied.

### Selected-germ inference audit before formalization

The existing selected-series theorem proves the `t^5` coefficient but the
semantic parent also says that this is the first nonintegral term in
`u=t^2` and that the regular coefficient is nonzero.  The exact missing jet
surface is finite and forced by the already proved ODE

\[
E'(t)=2tL(t)E(t),\qquad E(0)=1.
\]

The denominator constant `-107/56` gives `L(0)=-56/107`.  Since `[t]L=0`,
coefficient comparison must give

\[
[t]E=0,\qquad [t^2]E=-56/107\ne0,\qquad [t^3]E=0,
\]

while the governed series theorem gives

\[
[t^5]E=(1120/34347)\sqrt6\ne0.
\]

Together with the exact identity `x+2=t^2`, the vanishing of the only lower
odd powers `t,t^3` makes `t^5=u^(5/2)` the first nonintegral term.  A new
aggregate theorem may pay the selected-germ parent only if its signature
contains the exact ramification identity, the nonzero `t^2` coefficient,
both lower odd vanishings, and the exact nonzero `t^5` coefficient.

### Julia-to-root-multiplicity audit before formalization

For a nonzero polynomial generator `p`, let `m` and `n` be its root
multiplicities at the input and output centers.  Translate the polynomial at
each center and divide the maximal root power:

\[
p(x_0+u)=u^m q_{in}(u),\qquad
p(y+v)=v^n q_{out}(v),
\]

with both unit constants nonzero.  In the ramified parameter, write the
output displacement and spatial derivative factor as

\[
D(t)=a t^2+\cdots+c t^5+\cdots,
\qquad
G(t)=a+\cdots+\frac52c t^3+\cdots,
\]

where the `t,t^3` coefficients of `D` and the `t` coefficient of `G`
vanish.  Julia becomes

\[
D^n q_{out}(D)=G\,t^{2m}q_{in}(t^2).
\]

Exact power-series order first forces `n=m`.  After the common `t^(2m)`
factor is cancelled, the constant coefficient gives

\[
a^m q_{out}(0)=a q_{in}(0),
\]

and the first odd coefficient gives

\[
m a^{m-1}c q_{out}(0)=\frac52 c q_{in}(0).
\]

For `m=0` the second equality is already impossible.  For `m>0`, the first
equality cancels the unit data from the second and forces `m=5/2`.  The
formal theorem must construct the translated root units using polynomial
root multiplicity and derive both coefficient equations from the full Julia
series equality; accepting either scalar equation as a premise would leave
the inference unpaid.

For the selected endpoint `E` and its nonzero output value `y`, the formal
specialization is

\[
D=y(E-1),\qquad G=yLE.
\]

The endpoint ODE itself must prove `ord(D)=2`, `[t^3]D=0`,
`[t^5]D\ne0`, `G(0)=[t^2]D`, `[t]G=0`, and
`[t^3]G=(5/2)[t^5]D`.  The only premise allowed to remain after this
specialization is the locally transported Julia equality for the selected
continued branch; that continuation/sheaf transport is a separate analytic
obligation if the ordinary zero-constant power-series API cannot express
translation to the two finite centers.

## Finite-route versus projective-escape split

### Eigenquestion

Can the last two-flow leaf be proved from the available complex-analytic ODE
kernel, or does it contain a separate maximal-continuation classification?

### Candidate theorem

For selected endpoint germs `inner` and `outer` at a finite input `x0`, prove
in the analytic kernel that

\[
\operatorname{AnalyticAt}(inner,x_0)\land
\operatorname{AnalyticAt}(outer,inner(x_0))
\Longrightarrow
\operatorname{AnalyticAt}(outer\circ inner,x_0).
\]

Its contrapositive proves that a nonanalytic finite output germ forces one of
the two selected factor germs to be nonanalytic in its finite chart.  A
second, polynomial-ODE-specific theorem must then identify every such
nonfinite selected continuation with the reciprocal infinity chart and bind
its time-coordinate transition to `FormalPolynomialFlowAtInfinity`.

If the available library has no maximal complex-ODE continuation theorem or
analytic dependence-on-initial-data theorem, version the coverage DAG by
making the composition/contraposition theorem governed and retaining only
the nonfinite-to-reciprocal-chart classification as a semantic leaf.  The
old route-exhaustion digest remains recorded as superseded; it may not be
silently assigned to the narrower theorem.

### Kill conditions

- A theorem assuming that the composition is analytic does not pay the
  finite-route implication.
- Defining “finite continuation” to mean “analytic germ” does not prove that
  polynomial ODE solutions have the property.
- One-point compactness alone does not identify the reciprocal coordinate or
  its polynomial time equation.
- A local inverse theorem at one regular point does not classify a maximal
  continuation path.
- If a finite singularity other than projective infinity can occur for a
  selected polynomial trajectory, the original dichotomy is false and the
  compiler must preserve that additional branch.

### Punctured-extension refinement

Before accepting the nonfinite-to-infinity classification as atomic, apply
Riemann's removable-singularity theorem.  Define a finite analytic extension
of a selected punctured branch `f` at `c` to be an analytic germ `g` at `c`
that agrees with `f` on a punctured neighborhood.  The candidate theorem is

\[
\text{punctured holomorphy}+\text{local boundedness}
\Longrightarrow
\text{finite analytic extension}.
\]

Its contrapositive reduces the projective residual to an unbounded selected
polynomial branch.  The proof must construct the updated value from
`limUnder`; accepting an extension as a premise does not pay this step.  The
remaining semantic leaf may then be narrowed to: every unbounded selected
branch of the polynomial autonomous factorization has the reciprocal-chart
time-coordinate germ used by the governed infinity theorem.

### Meromorphic-order refinement

If the unbounded branch is meromorphic after a declared finite ramification,
Mathlib's meromorphic order should complete the chart passage.  The candidate
theorem is:

1. no finite analytic extension forces negative meromorphic order;
2. negative order forces convergence to the cobounded filter;
3. inversion flips the order, so the reciprocal tends to zero; and
4. updating that reciprocal to zero produces an analytic germ at the branch
   point.

The theorem must construct the reciprocal analytic extension and expose its
zero value.  Its hypotheses may include meromorphicity of the already
ramified selected branch, but may not include convergence to infinity or an
analytic reciprocal chart.  After this theorem, the semantic residual is the
Newton--Puiseux/classification statement that a selected unbounded branch of
a scalar polynomial autonomous flow admits the required finite ramification,
is meromorphic there, and obeys the normalized reciprocal time-coordinate
identity.  Essential-singularity examples kill any attempt to omit that
polynomial-flow/ramification hypothesis.

### Analytic power normal form for the infinity time coordinate

Let `tau` be analytic at `c` with finite positive analytic order `n`.  The
Mathlib order factorization gives

\[
\tau(z)=(z-c)^n g(z),\qquad g(c)\ne0.
\]

Normalize the unit by `q(z)=g(z)/g(c)` and take the canonical local root

\[
r(z)=q(z)^{1/n}.
\]

Because `q(c)=1` lies in the complex slit plane, `r` is analytic at `c`,
`r(c)=1`, and Mathlib's exact `cpow_nat_inv_pow` identity gives `r^n=q`.
Hence

\[
\chi(z)=(z-c)r(z)
\]

is analytic, satisfies `chi(c)=0`, has derivative one, and puts the time
coordinate into the exact normal form

\[
\tau(z)=g(c)\chi(z)^n.
\]

The analytic inverse-function theorem then constructs an analytic inverse
coordinate at zero.  This is the reusable Newton--Puiseux step: after the
finite ramification that makes the source time difference an `n`th power,
the reciprocal branch is analytic.  It does not by itself prove that the
actual continued polynomial-flow branch satisfies the separated
time-coordinate identity or selects this inverse germ; those two statements
remain caller-owned until derived from the autonomous ODE.

Kill conditions:

- do not assume an analytic `n`th root of the unit; construct it from complex
  `cpow` at the normalized value one;
- require `n>0`, since order zero has no ramified branch point;
- prove the derivative of `chi` is nonzero before invoking local inversion;
- do not identify an arbitrary punctured branch with the constructed inverse
  without an eventual time-coordinate equality and a selected-germ
  normalization.

### Polynomial reciprocal time-coordinate constructor

For a complex polynomial `p` of exact degree `d >= 2`, its reverse polynomial
has nonzero value `leadingCoeff p` at zero.  Therefore

\[
I_p(z)=-\frac{z^{d-2}}{p^{\mathrm{rev}}(z)}
\]

is analytic at zero with analytic order exactly `d-2`.  Construct a local
primitive `T_p` on a disk, normalized by `T_p(0)=0`.  The complex primitive
theorem and the analytic derivative-order identity must then give

\[
T_p'(z)=I_p(z),\qquad
\operatorname{ord}_0(T_p)=d-1>0.
\]

This pays the existence and finite positive order of the infinity time
coordinate directly from the polynomial generator.  It still leaves the
separation identity along the continued trajectory and the selected-branch
identification; neither may be inferred from the primitive alone.

## Attack vectors and counterattacks

- **Opposite branch:** `S(0)=-2*sqrt(6)` also squares correctly.  Bind the
  selected constant coefficient and reject sign transfer.
- **Endpoint-as-premise:** a theorem can be short by assuming its conclusion.
  Inspect the normalized signature and require constructed series plus
  coefficient propagation.
- **Finite Julia promotion:** a long coefficient check can mimic a formal
  identity.  Require a universal coefficient or extensional equality theorem.
- **Composition-side error:** left and right substitution reverse a derivative
  factor.  Check the theorem against a noncommuting orientation fixture and
  name the flow equation in the interface.
- **Infinity omission:** finite analytic continuation alone does not exhaust
  polynomial flows.  Require a reciprocal-coordinate branch in the theorem.
- **Equal-degree collision:** identical degree does not imply proportionality.
  Search for a nonproportional equal-degree counterexample before composing
  the terminal inference.
- **Semantic graft:** a convenient Lean theorem cannot cover the old semantic
  node by label.  Version the DAG with its exact governed proposition identity.

## Proof sequence and stop rules

1. Audit Mathlib power-series, substitution, derivation, and flow surfaces.
2. Build and stress the selected square-root series theorem.
3. Propagate the exact odd coefficient and integration scale.
4. Governed-ratify only the narrow theorem actually proved and recompile the
   DAG to confirm that exactly one residual leaf disappears.
5. Build Julia from the autonomous-flow identity and reject finite-order
   substitutes.
6. Stress equal-degree and infinity routes before stating the two-flow leaf.
7. Only after all leaves close, formalize the three inference rules and direct
   root; otherwise leave the mechanically narrowed frontier explicit.

A lane stops when it produces either a governed exact theorem or a specific
counterexample/API obstruction that narrows the next proposition.  Compilation
success without mechanism exposure is insufficient.

## Recurrence and primitive audit

Semantic primitive retrieval ranked the existing one-flow and two-flow
Puiseux obstruction compilers first.  They own typed premise composition and
their established semantic digests must remain fixed.  No reusable formal
local-series or autonomous-flow kernel surfaced.  Mathlib already supplies
power-series coefficients, order, derivative, substitution, inverse, and the
binomial addition law; the new work will use those facilities rather than add
a parallel series datatype.  A separate reusable kernel will be introduced
only for an invariant absent from those APIs.

## Intended formal surface

Lean owns constructed local series, coefficient identities, formal-flow
extensional equalities, chart/degree alternatives, inference rules, and the
terminal theorem.  Python owns adapter extraction, governed-record replay,
coverage-DAG versioning, adversarial orchestration, and preservation of prior
semantic digests.  The compiler remains unable to issue formal authority.

## Analytic-continuation bridge refinement

### Eigenquestion

Can equality of the Julia residual on the initial time-one germ be propagated
through a finite chain of analytic continuation charts, including a final
ramified coordinate, without assuming the terminal residual equality?

### Candidate invariant and theorem

Represent one continuation chart by a connected open complex domain together
with three analytic coordinate functions

\[
b(z),\qquad F(z),\qquad J(z),
\]

where `b` is the represented input coordinate, `F` the continued endpoint,
and `J` the continued spatial derivative factor.  For a polynomial `p`, put

\[
R_p(z)=p(F(z))-J(z)p(b(z)).
\]

An edge from a left chart to a right chart carries a local analytic transition
map into the left domain and eventual compatibility of all three coordinate
functions.  If `R_p=0` on the left chart, compatibility makes the right
residual zero near the edge point; Mathlib's analytic identity theorem then
extends this equality across the connected right chart.  Finite induction
must therefore prove terminal equality from initial equality.

The final ramified chart is allowed to have `b(t)=t^2-2`; no common planar
coordinate is assumed.  This is why the edge owns a transition map rather
than pointwise equality at the same complex argument.

### Exact boundary after the theorem

This kernel will pay continuation of polynomial identities across a supplied
chart chain.  It will not by itself prove that the selected Jacobian branch
admits such a chain, that its terminal analytic Taylor series is the already
constructed formal endpoint, or that every singular two-flow branch enters
the reciprocal infinity chart.  Those realization and route-exhaustion
claims remain separate nodes until constructed.

### Kill conditions

- If the edge assumes the right residual is zero, reject it as circular.
- If connectedness or an overlap neighborhood is absent, a one-point match is
  insufficient and the theorem must fail.
- If the terminal chart is forced to share the initial coordinate, it cannot
  represent the square-root branch and the interface is too narrow.
- If `AnalyticOnNhd` cannot prove polynomial composition analyticity or the
  identity theorem cannot propagate through one edge, stop before introducing
  a parallel analytic library.

### Capability audit

The semantic primitive embedder was unavailable, so the required semantic
absence conclusion was not drawn.  Lexical retrieval again surfaced the
filtered one-flow/two-flow compilers.  Direct repository and Mathlib search
found the reusable `Filter.Germ` composition API and
`AnalyticOnNhd.eqOn_of_preconnected_of_eventuallyEq`, but no continuation-
chain object.  The proposed kernel composes these existing facilities and
adds only the missing finite-chart identity-propagation layer.

### Taylor extraction subkernel

The continuation theorem ends with equality of analytic functions on the
terminal chart, while the root-multiplicity theorem consumes an equality in
`PowerSeries`.  The non-circular bridge is coefficient representation, not a
second identity assumption.  For a scalar power series `A`, use Mathlib's

\[
\operatorname{ofScalars}(n\mapsto [X^n]A)
\]

as its one-dimensional `FormalMultilinearSeries`.  If analytic functions
`f,g` have these representations at the same center and are eventually
equal, uniqueness of analytic power-series representations plus injectivity
of `ofScalars` forces `A=B`.  A connected-chart equality supplies the needed
eventual equality because the chart domain is open at its center.

The theorem may assume the two `HasFPowerSeriesAt` realization proofs; it may
not assume `A=B` or coefficientwise equality.  The remaining selected-branch
debt after this theorem is therefore exact: construct the terminal analytic
chart and prove that its two Julia sides realize the already specified formal
power series.

### Constructed endpoint subkernel

The selected-series theorems currently quantify over any normalized endpoint
solving the linear ODE; they do not construct one.  For a characteristic-zero
field and `A in k[[X]]`, define the zero-constant formal antiderivative by

\[
[X^0]I(A)=0,\qquad [X^{n+1}]I(A)=\frac{[X^n]A}{n+1},
\]

and the normalized endpoint by

\[
E_A=\exp(I(A)).
\]

Mathlib's power-series chain rule and `derivative_exp` should prove
`E_A'=A E_A` and `E_A(0)=1`.  The selected specialization uses
`A=2tL(t)`.  This construction must precede any convergence argument: an
analytic realization cannot be bound to an endpoint that exists only as a
universal theorem variable.

The semantic capability audit was unavailable again; lexical retrieval found
no related primitive, and direct Mathlib search found exponential series and
the substitution chain rule but no zero-constant formal antiderivative.  The
new kernel therefore adds the missing antiderivative/linear-ODE constructor
over Mathlib's existing `PowerSeries` type.

### Rational uniformization of the selected quadratic cover

The selected algebraic cover does not require an abstract square-root path.
Introduce the normalization parameter

\[
q=\frac{y-6}{x},
\]

and solve the conic exactly:

\[
x(q)=-\frac{12(q-1)}{q^2+3},\qquad
y(q)=-\frac{6(q-3)(q+1)}{q^2+3}.
\]

Direct polynomial arithmetic gives

\[
y(q)^2=36+12x(q)-3x(q)^2,
\qquad
x(q)+2=\frac{2(q-3)^2}{q^2+3}.
\]

Thus `q=1` is the normalized point `(x,y)=(0,6)` and `q=3` is the
selected ramification point `(x,y)=(-2,0)`.  This replaces branch-choice
continuation by a rational chart whose excluded set is finite.

For the exact carried coefficient computed by the existing algebraic-normal
adapter, substitution into this chart yields

\[
V(q)=-\frac{(q-1)
 (13q^5-65q^4+82q^3-306q^2+1137q+675)}
 {7168q(q^2-6q-3)}
\]

and

\[
\frac{d}{dq}\log F=
-\frac{896q(q-3)(q+1)(q^2-6q-3)}
{(q-1)(39q^7-273q^6+1571q^5-6981q^4+5493q^3
-21843q^2-8703q+2025)}.
\]

The terminal denominator at `q=3` is `-739584`, while the numerator
vanishes.  Hence the endpoint equation is regular in the uniformizing chart.
These identities must be replayed independently before they become formal
premises; a rational formula copied from this pencil is not evidence.

### Canonical Taylor-algebra bridge

The remaining analytic-to-formal bridge should use canonical Taylor
coefficients rather than a parallel convergence-majorant library.  For an
analytic scalar function `f` at `a`, define

\[
T_a(f)_n=\frac{f^{(n)}(a)}{n!}.
\]

Mathlib already proves that an analytic function is represented by these
iterated-derivative coefficients.  The new kernel should prove, from that
representation and the iterated Leibniz rule,

\[
T_a(fg)=T_a(f)T_a(g),\qquad
T_a(f')=(T_a(f))',\qquad
[X^0]T_a(f)=f(a).
\]

Consequently an analytic solution of `E'=A E`, `E(a)=1` transports to a
formal solution of the identical linear ODE.  A coefficient induction then
proves uniqueness of the normalized formal solution and identifies its
Taylor series with `normalizedEndpoint (T_a(A))`.  No conclusion about the
selected endpoint is assumed in this bridge.

The intended formal surface is split in two reusable pieces:

1. `FormalAnalyticTaylorAlgebra`: canonical Taylor representation, product,
   derivative, and analytic linear-ODE transport;
2. `FormalPowerSeriesLinearODE.linear_ode_solution_unique`: equality of two
   formal solutions from equal constants and the same coefficient series.

Kill conditions:

- if the Taylor representation theorem is obtained by assuming the target
  `PowerSeries` equality, reject the route as circular;
- if the product proof silently drops the binomial/factorial conversion,
  reject it;
- if ODE uniqueness uses division by a possibly zero positive integer, keep
  the characteristic-zero hypothesis explicit;
- if the rational chart coefficient has a pole at `q=3`, the selected-chart
  route fails and the coverage leaf stays open;
- if the terminal Taylor coefficient series cannot be proved equal to the
  already ratified `selectedEndpointT`, do not count analytic continuation as
  the selected-chart realization.

## Selected Julia assembly after chart realization

### Eigenquestion

Does eventual Julia equality for the analytically continued selected endpoint
transport, by canonical Taylor algebra alone, to the exact shifted real
power-series equality consumed by the ramified root-factor theorem?

### Candidate theorem

For the constructed continuation and nonzero terminal value, let

\[
F(t)=yE(t),\qquad b(t)=t^2-2,\qquad
J(t)=yL(t)E(t).
\]

If a real polynomial `p`, complexified coefficientwise, satisfies

\[
p(F(t))=J(t)p(b(t))
\]

eventually at `t=0`, then canonical Taylor transport for polynomial
evaluation and multiplication gives the complexification of

\[
p_y\bigl(y(E-1)\bigr)
=yLE\,p_{-2}(X^2).
\]

Coefficientwise injectivity of `ℝ -> ℂ` must then recover this equality in
`ℝ[[X]]`.  The theorem may consume eventual analytic Julia equality produced
by the continuation kernel; it may not accept the target formal equality or
any finite coefficient truncation.

### Kill conditions

- Reject the theorem if the real conclusion is assumed through a
  complexification premise.
- Reject any proof that identifies polynomial evaluation with substitution
  without proving the translated input/output-center identities.
- Keep initial-to-terminal analytic propagation separate: this assembly pays
  analytic-to-formal transport, not the existence of an autonomous flow.
- If coefficientwise complexification is not injective on power series, the
  real root-factor theorem cannot consume the result and the assembly stays
  open.

## Proportional analytic trajectory identification

### Eigenquestion

If one analytic trajectory solves `x'=p(x)` and another solves
`y'=c p(y)` from the same initial value, does analytic ODE uniqueness identify
`y(1)` with `x(c)` on every connected comparison chart containing times zero
and one?

### Candidate theorem

On an open preconnected real time-domain `D` containing `0` and `1`, assume
that `t -> x(c t)` and `y(t)` are analytic, have the same value at zero, and
satisfy the same rescaled polynomial ODE.  Polynomial evaluation is `C^1`, so
it is Lipschitz on a neighborhood of the initial value.  Mathlib's local ODE
uniqueness gives equality near time zero; analytic identity propagation then
gives equality on all of `D`, hence

\[
y(1)=x(c).
\]

The formal surface should derive analyticity and the rescaled ODE of
`t -> x(c t)` from the original trajectory and the chain rule.  The theorem
must expose the connected comparison domain and cannot assume endpoint
equality.

### Kill conditions

- A global Lipschitz premise for an arbitrary polynomial is too strong; use
  only local Lipschitz near the common initial value.
- Local ODE uniqueness alone does not identify time one; connected analytic
  propagation is required.
- If the comparison domain does not contain both `0` and `1`, no endpoint
  conclusion is allowed.
- The theorem pays same-flow identification only.  Composition remains owned
  by `FormalSubstitutionFlow`.

## Polynomial reciprocal-time separation

### Eigenquestion

Does the analytic infinity-time coordinate constructed from a polynomial
vector field separate every nonvanishing reciprocal trajectory by exact
translation in time, without assuming an inverse-flow formula?

### Candidate theorem

Let `p : ℂ[X]` have exact degree `d ≥ 2`, and put

\[
I_p(z)=-\frac{z^{d-2}}{p^{\mathrm{rev}}(z)},\qquad
R_p(z)=-\frac{p^{\mathrm{rev}}(z)}{z^{d-2}}.
\]

First prove the algebraic cancellation

\[
I_p(z)R_p(z)=1
\]

whenever `z` and `p.reverse.eval z` are nonzero.  If `T'(z)=I_p(z)` and a
trajectory `z(t)` satisfies `z'(t)=R_p(z(t))`, the chain rule gives

\[
\frac{d}{dt}T(z(t))=1.
\]

On an open preconnected complex time-domain, the zero-derivative theorem then
forces

\[
T(z(t))-t=T(z(t_0))-t_0.
\]

The kernel must also derive the reciprocal equation from an original
trajectory `x'=p(x)`: for `z=x^{-1}`, polynomial reversal gives

\[
p^{\mathrm{rev}}(z)=z^d p(z^{-1}),
\]

and differentiation of inversion gives

\[
z'=-p(x)/x^2=R_p(z).
\]

This conversion is part of the certificate, not a caller-supplied equality.
The terminal surface should expose both pointwise unit-speed differentiation
and the connected-domain separated-time identity.

### Intended formal surface

`FormalPolynomialTimeSeparation` should provide:

1. exact cancellation of `reciprocalTimeIntegrand` with a typed reciprocal
   vector field;
2. a reverse-polynomial evaluation identity at every nonzero reciprocal
   coordinate;
3. conversion of `HasDerivAt x (p.eval (x t)) t` into the reciprocal ODE;
4. `HasDerivAt (T ∘ z) 1 t` by the chain rule; and
5. constancy of `T(z(t))-t` over every declared open preconnected domain.

### Kill conditions

- Reject a statement that accepts `T(z(t))=t+c` as a premise or accepts the
  reciprocal ODE without also proving the original-trajectory conversion.
- Keep all nonvanishing assumptions explicit; cancellation at a pole or at
  the reciprocal origin is invalid.
- The exact-degree hypothesis must control the reversal exponent.  A theorem
  with an unrelated caller-chosen exponent does not discharge the polynomial
  branch.
- A local derivative identity alone does not pay endpoint separation;
  connected-domain propagation is required.
- This theorem does not yet identify the selected continued branch with the
  constructed analytic inverse.  That remains a separate leaf after unit
  speed is ratified.

## Selected ramified inverse-germ uniqueness

### Eigenquestion

After reciprocal-time separation fixes only the `n`th power of the
uniformizing coordinate, does the selected first derivative determine the
root-of-unity branch and identify the trajectory with the constructed local
inverse?

### Candidate theorem

First isolate the branch selector.  If `f : ℂ → ℂ` is analytic at zero,

\[
f(0)=0,\qquad f'(0)=1,\qquad f(w)^n=w^n
\]

eventually, with `n ≠ 0`, then `f(w)=w` eventually.  The proof must not
choose complex roots globally.  Analytic order one gives

\[
f(w)=w u(w),\qquad u(0)=1.
\]

On the punctured neighborhood, power cancellation gives `u(w)^n=1`.
Factor

\[
u^n-1=(u-1)(1+u+\cdots+u^{n-1}).
\]

The second factor equals the nonzero complex number `n` at zero, hence stays
nonzero nearby; therefore `u=1`.

Now let `coordinate` be the analytic power coordinate with
`coordinate(0)=0` and derivative one, let `inverseCoordinate` be its
constructed local right inverse, and let `selected` be the analytic
uniformized reciprocal trajectory with value zero and derivative one.  If

\[
\operatorname{coordinate}(\operatorname{selected}(w))^n=w^n,
\]

the branch-selector lemma yields
`coordinate(selected(w))=w`.  The analytic inverse-function theorem makes
`coordinate` locally injective; comparing with
`coordinate(inverseCoordinate(w))=w` then gives

\[
\operatorname{selected}(w)=\operatorname{inverseCoordinate}(w)
\]

as an equality of analytic germs.

### Intended formal surface

`FormalSelectedRamifiedInverse` should expose:

1. `analytic_nth_root_branch_unique`, proving the normalized branch lemma;
2. local injectivity/equality from an analytic coordinate with nonzero
   derivative and two local right-inverse germs;
3. a terminal selected-inverse certificate consuming analyticity, center,
   derivative, power identity, and the constructed right-inverse identity;
4. no global branch cut and no assumed equality of the selected and
   constructed germs.

### Kill conditions

- Reject the theorem if `coordinate(selected w)=w` or the final germ equality
  is accepted as a premise; only its `n`th-power form plus derivative
  normalization is admissible.
- `n ≠ 0` and characteristic zero must remain explicit so the geometric
  factor at one is nonzero.
- A power equality without derivative normalization is insufficient: the
  root-of-unity multiples are counterexamples.
- A right-inverse identity alone is insufficient unless local injectivity of
  the coordinate is proved from its nonzero derivative.
- The theorem identifies germs near the ramification point.  Transport from
  the actual continued polynomial trajectory into the uniformized selected
  germ must remain visible in the eventual power premise produced from the
  separated-time certificate.

## Punctured-time to ramified-center assembly

### Eigenquestion

Can the separated-time constant proved on a finite punctured trajectory domain
be transported to the reciprocal-infinity center without assuming the value
of that constant there?

### Candidate theorem

Let `D` be an open preconnected complex time-domain on which a reciprocal
trajectory `z(t)` avoids zero and the reverse-polynomial divisor.  The
reciprocal-time kernel gives

\[
T(z(t))-t=c
\]

throughout `D`.  Let `t_\infty` be a boundary time with `z(t_\infty)=0`, and
reparameterize by

\[
t(w)=t_\infty+u w^n.
\]

Assume every sufficiently small nonzero `w` maps into `D`, while
`w \mapsto z(t(w))` is analytic at zero with the selected derivative
normalization.  Then

\[
w\longmapsto T(z(t(w)))-t(w)
\]

is continuous at zero and equals `c` on a punctured neighborhood.  The
continuous punctured-neighborhood equality theorem promotes this to a full
neighborhood equality, so evaluating at zero gives

\[
c=T(0)-t_\infty=-t_\infty.
\]

Thus the separated identity required by the selected ramified-inverse kernel
holds at the center as well, and that kernel identifies the selected
trajectory with the constructed inverse germ.

### Intended formal surface

`FormalPolynomialSelectedTrajectoryAssembly` should consume the concrete
derivative hypotheses of `FormalPolynomialTimeSeparation`, the concrete
analytic normal-form and inverse hypotheses, an eventual punctured `MapsTo`
condition for the ramified time parameter, and the selected analytic
derivative normalization.  Its proof must call both governed kernels and
derive the centered separated identity by continuity.

### Kill conditions

- Reject an assembly that assumes the separated constant equals
  `-t_\infty` or assumes the centered separated identity.
- The punctured reparameterization must map into the domain where the
  reciprocal ODE and nonvanishing hypotheses hold.
- `z(t_\infty)=0`, `T(0)=0`, analyticity of the reparameterized trajectory,
  and continuity of `T` at zero must be explicit.
- Equality on the punctured neighborhood cannot be treated as equality at the
  center without the continuity step.
- The theorem must call the exact reciprocal-time and ramified-inverse
  kernels; a duplicated algebraic premise does not pay the inference edge.

## Route-indexed two-flow structural assembly

### Eigenquestion

Can the finite/infinity/proportional mechanisms be assembled into one typed
structural theorem without treating the separate claim that every continued
factorization supplies one of those routes as if it were already proved?

### Governing identity

The assembly input is a route witness, not an untyped disjunction of desired
conclusions.  It has two constructors:

1. a finite constructor carrying analyticity of the inner germ at the input
   and of the outer germ at the intermediate value; and
2. an infinity constructor carrying two exact-degree monic normalized
   polynomial generators, tangent coefficients zero in degrees zero and one,
   a nonzero-linear transition between their normalized infinity-time
   coordinates, and the endpoint identification needed only if the
   normalized generators coincide.

The output has three distinct constructors:

1. analytic finite composition;
2. equal-degree nonproportional infinity collision, with its exact formal
   time-coordinate order and exponent in `(1,2)`; or
3. a single reparameterized substitution-flow endpoint in the proportional
   case.

The governing equality for the proportional constructor is the actual
endpoint substitution equality.  A Boolean route tag or a `Prop` named
`Escape` is not the identity of this object.

### Candidate theorem

Case induction on the route witness should prove the structural outcome.
The finite constructor calls `analyticAt_comp_of_finite_factor_germs`.  In
the infinity constructor,
`nonzero_linear_transition_forces_equal_degree` first rewrites the two exact
degrees to one `d`.  Then `monic_tangent_time_coordinate_alternative` gives
either equality of the normalized generators or a largest collision degree
`e` with exact order `2*d-e-1`.  The equal case calls
`identified_endpoints_reduce_to_reparameterized_time_one`; the collision
case calls `time_coordinate_collision_exponent_interval`.

This theorem pays the assembly of the already governed mechanisms.  It does
not prove that an arbitrary analytic continuation of a factorization creates
one of the route witnesses.  The coverage DAG must therefore expose a new
semantic leaf, `two_flow_factorization_route_realization`, until a maximal
polynomial-ODE continuation theorem constructs that witness from the bare
factorization identity.

### Kill conditions

- Reject an input constructor that stores one of the three output
  constructors directly.
- Reject a theorem whose only premise is `(finite ∨ infinity ∨
  proportional) → Outcome`; the route data and their compatibility must be
  inspectable.
- Do not infer proportionality from equality of degrees.  It follows only
  from equality of every normalized coefficient after the collision
  alternative.
- Do not report the universal phrase "every factorization" from this
  assembly.  That phrase belongs to the separate route-realization leaf.
- If rewriting the equal-degree result does not preserve both monicity and
  the transition identity, the structural interface is underspecified.

## Coefficient-field correction

### Eigenquestion

Does the governed infinity-chart theorem cover the coefficient field
quantified by the two-flow obstruction compiler?

### Audit result

The answer for the first formal surface is no.  The compiler says
"polynomial autonomous flows" over the complex analytic germ under study,
but `FormalPolynomialFlowAtInfinity` and the first route-indexed assembly
were specialized to `ℚ`.  A hypothetical complex polynomial generator need
not descend to a rational polynomial.  Therefore the rational theorem is a
useful instance, but it cannot discharge the compiler's universal claim.

### Candidate theorem

Move the reciprocal-denominator, formal primitive, substitution-order, and
coefficient-collision mechanisms to an arbitrary field `𝕜` of
characteristic zero.  The exponent arithmetic remains in `ℚ`, because it
depends only on the natural degrees.  Parameterize the structural frame,
formal endpoints, generators, transition series, and substitution flow by
the same `𝕜`.  The existing rational theorem then becomes an instance, and
the route-realization theorem may instantiate `𝕜 = ℂ` without a coefficient
restriction.

### Kill conditions

- Do not obtain the complex statement by assuming the generators have
  rational coefficients.
- Keep one coefficient field across the two generators, transition series,
  and formal endpoints.
- Do not replace exact coefficient inequality by a decidable Boolean test.
- Re-run the full infinity and structural certificates after the signature
  change; the previous governed identities no longer certify the generalized
  propositions.

## Ramified-sheet identity correction

### Eigenquestion

Can a selected infinity branch be represented by one ordinary function of
the unramified time variable and still have a derivative-one uniformizing
germ after the substitution `t = t∞ + u*w^n`, for `n > 1`?

### Counterattack

No.  If

```text
selected(w) = trajectory(t∞ + u*w^n),
```

then `selected(ζ*w) = selected(w)` for every `ζ` with `ζ^n = 1`.  For any
nontrivial such `ζ`, differentiability at zero gives

```text
ζ * selected'(0) = selected'(0),
```

and hence `selected'(0) = 0`.  The earlier selected-trajectory assembly asks
this derivative to equal one.  Its ramified premises are therefore empty for
orders greater than one.  Kernel compilation of the implication did not
certify realizability of its premise bundle.

### Correct object

The continuation is a function on a selected sheet (or directly on the
uniformizing `w`-coordinate), together with a time projection

```text
time(w) = t∞ + u*w^n.
```

The reciprocal trajectory belongs to the sheet coordinate and satisfies the
pulled-back differential equation there.  It must not be factored through a
single-valued function of the base time across the branch point.  Overlap
identification with the original finite trajectory is an edge between the
finite chart and the sheet, not equality of two global functions on the
unramified plane.

### Kill conditions

- Reject any order-`n > 1` interface that combines factorization through
  `w^n` with a nonzero derivative at the ramification center.
- Do not repair the contradiction by deleting derivative normalization;
  the object identity is wrong and must become sheet-valued.
- Preserve the time projection and the overlap equation explicitly so the
  sheet cannot be an arbitrary analytic germ unrelated to the polynomial
  flow.

## Sheet-valued polynomial-flow kernel

### Governing identity

For a polynomial generator `p`, a ramified infinity trajectory is owned by
the selected sheet.  Its data are a punctured sheet domain `D`, a reciprocal
coordinate `z(w)`, and the projection

```text
pi(w) = t_infinity + unit * w^order.
```

The differential equation lives on the sheet:

```text
z'(w) = pi'(w) * reciprocalVectorField(p, z(w)),
pi'(w) = unit * order * w^(order - 1).
```

This is compatible with `z(0)=0` and `z'(0)=1`; unlike the rejected
factor-through interface, it does not identify different sheets over the
same base-time point.

### Candidate theorem

Package the domain, anchor, reciprocal germ, punctured-neighborhood
membership, divisor avoidance, and pulled-back ODE as one
`PolynomialRamifiedTrajectorySheet`.  If `T` is the analytic reciprocal-time
coordinate and

```text
T(z) = unit * coordinate(z)^order
```

near zero, then connected-domain differentiation gives

```text
T(z(w)) - pi(w) = constant                 on D.
```

Because `D` contains a full punctured neighborhood of zero and both sides
are analytic at the sheet center, the equality extends to zero.  The center
values force the constant to be `-t_infinity`, hence

```text
T(z(w)) = unit * w^order.
```

The normalized derivative-one branch theorem then proves that `z` equals
the analytic inverse of `coordinate` as a germ.  The conclusion is local to
the selected sheet; no global single-valued base-time trajectory is asserted.

### Proof skeleton

1. Multiply the time-coordinate derivative by the pulled-back vector field
   and use the exact reciprocal cancellation identity.
2. Subtract the derivative of `pi`; the separated derivative is zero on
   `D`.
3. Apply the open/preconnected zero-derivative theorem using the sheet
   anchor.
4. Restrict to the punctured-neighborhood filter supplied by the sheet, then
   extend through zero by analyticity.
5. Evaluate at zero, obtain the centered power identity, and invoke the
   selected ramified inverse kernel.

### Exact boundary after this theorem

The theorem certifies uniqueness and normalization of any supplied selected
sheet.  It does not construct that sheet from a bare polynomial ODE, prove
that a finite continuation reaches either an ordinary point or this infinity
chart, identify overlap with the original finite trajectory, or exclude
additional continuation sheets.  Those are the remaining global
continuation/exhaustiveness obligations.

### Kill conditions

- The sheet domain must contain a full punctured neighborhood of its center;
  a single ray or chosen sequence is insufficient for analytic germ
  identification.
- The pulled-back ODE must carry the derivative of the time projection.
- Divisor avoidance is required on the punctured domain so reciprocal-time
  cancellation is valid.
- Do not infer sheet existence, overlap, or route exhaustiveness from the
  local uniqueness theorem.

## Constructing the local polynomial infinity sheet

### Eigenquestion

Does the analytic inverse coordinate already constructed from every exact
degree-`d >= 2` polynomial supply the complete local
`PolynomialRamifiedTrajectorySheet`, leaving only identification with the
incoming finite continuation?

### Candidate construction

Let `inverseCoordinate` be the analytic right inverse of the normalized
coordinate and put `order=d-1`.  On a sufficiently small punctured disk,

```text
coordinate(inverseCoordinate(w)) = w,
T(inverseCoordinate(w)) = unit * w^order.
```

Differentiate the second equality.  The time-coordinate derivative is the
reciprocal integrand, so

```text
I(inverseCoordinate(w)) * inverseCoordinate'(w)
  = unit * order * w^(order-1).
```

After shrinking the disk so `inverseCoordinate(w)` and the reversed
polynomial denominator are nonzero, the exact identity `I*R=1` gives

```text
inverseCoordinate'(w)
  = unit * order * w^(order-1) * R(inverseCoordinate(w)).
```

The punctured complex disk is open and preconnected.  It contains a full
punctured neighborhood of zero, and any nonzero point in it supplies the
sheet anchor.  Thus the inverse germ itself constructs all local sheet
fields.

### Intended formal surface

1. Prove a reusable topology lemma that a nonempty complex punctured ball is
   preconnected, using the image of `(0,r) x sphere(0,1)` under scalar
   multiplication.
2. Extract one positive radius subordinate to the finite intersection of the
   analytic, inverse, derivative, and divisor-avoidance neighborhoods.
3. Build `PolynomialRamifiedTrajectorySheet` with reciprocal coordinate
   `inverseCoordinate`.
4. Compose with `polynomial_infinity_ramification_terminal_certificate` to
   obtain sheet existence for every exact degree-`d >= 2` complex
   polynomial.

If this compiles, the v23 semantic leaf splits cleanly: local sheet existence
is paid, while overlap with the particular finite continuation remains the
single global continuation datum.

### Counterattacks and kill conditions

- A domain that is only an arbitrary eventual set is insufficient; the
  record requires an open preconnected punctured neighborhood.
- Do not use the value of division by zero at the sheet center to assert the
  ODE there; all cancellation is on the punctured disk.
- The local inverse must be shown nonzero away from zero.  This follows from
  the local right-inverse identity and must be included before cancellation.
- Local sheet existence does not identify which analytic-continuation sheet
  is reached by a given finite trajectory.  That overlap remains separate.

### Kernel outcome

The construction compiles.  The reusable topology lemma realizes a
punctured complex ball as the scalar-multiplication image of a radial
interval times the unit sphere.  The polynomial theorem then extracts one
ball on which inverse analyticity, reciprocal-time differentiation, the
power identity, reciprocal nonvanishing, and reversed-polynomial
nonvanishing all hold.  Differentiating the exact time identity and using
`reciprocalTimeIntegrand_mul_reciprocalVectorField` constructs the required
pulled-back ODE.

Thus every exact degree-`d >= 2` complex polynomial now constructs a local
ramified infinity sheet.  The unresolved leaf is strictly the finite-to-sheet
overlap/continuation identification for the selected factorization branch.

## Finite-to-sheet overlap uniqueness

### Eigenquestion

Once a selected finite continuation and the constructed ramified sheet are
represented on one connected overlap chart, does compatibility of their
reciprocal time coordinate force equality of the two reciprocal branches?

This question separates the uniqueness part of the remaining leaf from the
existence of the overlap chart.  The latter is a maximal-continuation
statement; it must not be smuggled into a theorem whose inputs already name
the chart.

### Candidate general kernel

Let `D` be an open preconnected complex domain with `a in D`.  Let `left` and
`right` be analytic on `D`, and let `T` be analytic at their common anchor
value.  Assume

```text
left(a) = right(a),
T(left(w)) = T(right(w))                 for w in D,
T'(left(a)) != 0.
```

The analytic inverse-function theorem gives a local left inverse of `T` at
`left(a)`.  Composing that inverse with the coordinate equality proves
`left = right` near `a`; the analytic identity theorem then propagates the
equality over all of `D`.

For a polynomial infinity sheet, `T'` is the reciprocal-time integrand.  At
every punctured sheet point it is nonzero because both the reciprocal
coordinate and the reversed-polynomial denominator are nonzero.  Therefore a
typed overlap record needs to own only:

1. its open preconnected domain and anchor;
2. the incoming continued reciprocal branch and its analyticity;
3. inclusion in the selected sheet domain;
4. equality of the two projected time coordinates on the overlap; and
5. equality at one anchor point.

The kernel should derive equality of reciprocal branches on the whole overlap,
not accept that equality as a field.

### Exact remaining premise

Even after this kernel, one global datum remains: every selected unbounded
finite continuation used by the two-flow factorization must construct such an
overlap chart with the local polynomial infinity sheet.  Local ODE data do not
construct that chart by themselves.  A complete proof needs either:

- a formal maximal analytic-continuation/Riemann-surface theorem for the
  separated polynomial ODE, with an infinity-end chart; or
- an equivalent explicit continuation-chain construction ending in a sector
  on which the reciprocal time coordinate has the required compatibility.

### Counterattacks and kill conditions

- A one-point branch equality without a common time-coordinate identity is
  insufficient.
- Equality of time coordinates without a noncritical anchor is insufficient;
  different ramified branches can have the same power.
- The overlap may be a connected sector.  Requiring a full punctured disk of
  the incoming finite branch would incorrectly erase monodromy.
- The uniqueness theorem pays no existence or route-exhaustiveness claim.

## Entering the sheet from an analytic reciprocal germ

### Eigenquestion

Is a separate overlap choice needed once the incoming continuation already
has an analytic reciprocal germ tending to zero, or does the constructed
normal coordinate produce the overlap chart canonically?

### Construction

Let `zeta(t)` be analytic at an approach center `t0`, with `zeta(t0)=0` and
`zeta(t) != 0` on a punctured neighborhood.  For a constructed polynomial
infinity sheet, write `c` for the derivative-one normal coordinate and `i`
for its analytic inverse.  The inverse-function theorem and the governed
right-inverse identity give the missing left-inverse identity

```text
i(c(z)) = z
```

near zero.  Define the transition into the sheet by

```text
w(t) = c(zeta(t)).
```

Then `w(t) -> 0`, it is nonzero on a smaller punctured neighborhood, and the
sheet domain contains `w(t)` there.  Moreover

```text
sheet.reciprocal(w(t)) = i(c(zeta(t))) = zeta(t).
```

Choose one punctured point and shrink to a connected open ball around it.
This constructs a coordinate-aware finite-to-sheet overlap edge without
assuming branch equality or a time-coordinate equality.

### Consequence and remaining global input

The overlap leaf can therefore be paid from an incoming analytic reciprocal
germ with a nonzero punctured representative.  The remaining global theorem
is narrower: a selected nonfinite continuation of the polynomial time-one
branch must produce such an analytic reciprocal germ after its finite
ramification.  This is the continuation-end/finite-ramification statement;
the overlap itself is local inverse geometry.

### Kill conditions

- Require punctured nonvanishing.  The identically zero reciprocal germ does
  not describe entry from a finite trajectory.
- The transition is `c o zeta`; it is not assumed to be the identity or to
  have nonzero derivative before primitive ramification is selected.
- Construct a connected open overlap, not merely a convergent sequence.
- Do not use this local chart entry as route exhaustiveness.

### Meromorphic-pole corollary

For a branch already expressed in a finite ramified coordinate, negative
meromorphic order supplies the hypotheses above.  The meromorphic infinity
kernel constructs an analytic reciprocal germ with center value zero.  Its
cobounded limit makes the original branch eventually nonzero, so the
reciprocal is nonzero on a punctured neighborhood.  Composing that result with
the chart-entry construction produces the local sheet overlap.

After this corollary, the irreducible input is no longer “overlap”: it is the
finite-ramification/meromorphic realization of the selected nonfinite
continuation.  This is the exact theorem that a scalar polynomial-ODE
continuation result must supply.

Composing the corollary with unconditional construction of the polynomial
infinity sheet removes even the supplied-sheet parameter.  For every exact
degree-`d >= 2` polynomial and every negative-order meromorphic continuation
end, the combined theorem should construct both the canonical sheet and its
reciprocal entry.  The only caller datum left is the negative-order
meromorphic end itself.

## Ramified fiber product of two analytic time germs

### Eigenquestion

Can finite ramification of a polynomial-flow endpoint be derived from the
separated time equation itself, without importing a maximal-continuation
classification theorem?

### Governing isomorphism

Suppose two pointed complex analytic germs have finite positive orders
`n` and `k`:

```text
leftTime(z)  = a * leftCoordinate(z)^n,
rightTime(x) = b * rightCoordinate(x)^k.
```

Both coordinates are tangent to the identity and therefore have analytic
local inverses.  The fiber product

```text
leftTime(z) = rightTime(x)
```

is locally isomorphic to the monomial curve `u^n = (b/a) * v^k`.  No
minimality assertion is needed.  Choose an `n`th root `lambda` of `b/a` and
normalize it by the finite parameterization

```text
rightCoordinate(x(w)) = w^n,
leftCoordinate(z(w))  = lambda * w^k.
```

Then both time germs equal `b * w^(n*k)`.  Thus `x(w)` is a finite
ramification of the source and `z(w)` is an analytic reciprocal branch.  If
the left center is zero, `z(w)` has exact order `k`; hence `z(w)^(-1)` is
meromorphic of exact negative order `-k`.

This is the normalization of the analytic fiber product, not a choice of a
global branch.  It is the local algebraic object underlying the infinity end
of a scalar polynomial flow.

### Intended formal surface

Introduce an `AnalyticRamifiedFiberProduct` owned by the equality of the two
pointed time germs.  It records the source projection, lifted reciprocal,
their analyticity and center values, the two coordinate monomials, exact time
compatibility, and the negative-order meromorphic inverse.  A terminal theorem
constructs this record from two calls to the governed analytic power-normal-
form kernel.

For the polynomial application, instantiate the left germ with the
constructed reciprocal infinity-time coordinate of order `d-1`.  The right
germ is the finite-input separated-time displacement.  The result constructs
the finite ramification and meromorphic pole demanded by the current coverage
leaf as soon as that right germ is shown analytic, zero at the endpoint, and
not locally zero.

### Counterattacks and kill conditions

- Do not assume a pre-existing meromorphic branch; it must be constructed from
  the two normal forms.
- Do not require `gcd(n,k)=1` or claim minimal ramification.  The uniform
  `n`-fold parameterization is sufficient and avoids hidden arithmetic.
- The root scalar must be constructed and proved nonzero with
  `Complex.cpow_nat_inv_pow`; an arbitrary root premise would move the work to
  the caller.
- Exact time compatibility must be derived from the two normal forms, not
  stored as an input.
- This kernel does not prove that every selected continuation obeys the same
  separated-time germ or that the right germ has finite positive order.  Those
  are the remaining continuation-to-fiber-product obligations.

## Regular finite Abel coordinate and the polynomial fiber product

### Eigenquestion

For a finite source center that is not an equilibrium of the polynomial
generator, is the positive-order source germ automatic, and does it force a
simple pole on the normalized infinity sheet?

### Candidate construction

If `p(x0) != 0`, then

```text
finiteIntegrand(x) = 1 / p(x)
```

is analytic near `x0`.  A local primitive normalized by `A(x0)=0` satisfies

```text
A'(x0) = 1 / p(x0) != 0,
analyticOrderAt A x0 = 1.
```

For an exact degree-`d >= 2` polynomial, the already governed reciprocal
infinity-time coordinate has order `d-1`.  Applying the analytic ramified
fiber-product kernel to the pair `(T_infinity, A)` therefore constructs

```text
sourceCoordinate(x(w)) = w^(d-1),
infinityCoordinate(z(w)) = lambda * w,
T_infinity(z(w)) = A(x(w)).
```

The source ramification has degree `d-1`, the reciprocal lift has exact order
one, and its inverse is meromorphic of exact order `-1`.  This is the local
normal form of every regular finite-to-infinity polynomial-flow endpoint.

### Intended formal surface

1. `FormalPolynomialFiniteTimeCoordinate` constructs `A`, its derivative
   identity, and its exact order one from `p.eval x0 != 0`.
2. `FormalPolynomialRegularInfinityFiberProduct` combines that certificate,
   the polynomial infinity-time certificate, and the governed analytic fiber
   product into one inspectable record.

### Counterattacks and kill conditions

- The finite center must expose `p.eval x0 != 0`; division at an equilibrium
  cannot enter this theorem.
- Exact order one must follow from the constructed derivative, not from a
  caller-supplied order premise.
- The inverse pole order must be exactly `-1`, not merely negative.
- The theorem constructs the local correspondence but does not prove that a
  selected continued time-one branch reaches it.  After this construction the
  remaining global datum is selected overlap/separation, plus exclusion or
  separate treatment of an equilibrium endpoint.

## Equilibrium trajectory as a zero solution of a linear ODE

### Eigenquestion

Can the equilibrium endpoint be excluded without first constructing a
parameter-dependent nonlinear flow or importing a broad holomorphic-ODE
continuation theorem?

### Governing isomorphism

If `p(center)=0`, polynomial division by `X-center` constructs a polynomial
`q` satisfying

```text
p(y) = (y-center) * q(y).
```

For an analytic complex-time trajectory `y` satisfying `y'=p(y)`, its
displacement `D=y-center` therefore obeys

```text
D' = q(y) * D.
```

The coefficient `q ∘ y` is analytic.  The zero function is another solution
of this scalar linear equation, and `D(anchor)=0` when the trajectory starts
at the equilibrium.  The governed analytic linear-ODE uniqueness theorem then
forces `D=0` throughout every open preconnected continuation domain.  Hence an
analytic branch that starts at an equilibrium is constant throughout its
finite continuation and cannot be the branch entering the reciprocal
infinity chart.

### Intended formal surface

`FormalPolynomialEquilibriumTrajectoryRigidity` should construct the quotient
with `divByMonic`, derive the evaluated factorization, convert the autonomous
ODE to the linear displacement ODE, and invoke
`FormalAnalyticLinearODEContinuation.solution_eqOn_of_eq_at`.  Its terminal
theorem concludes `EqOn trajectory (fun _ => center) domain` from polynomial
equilibrium, analytic-trajectory, ODE, connected-domain, and anchored-value
premises.

### Counterattacks and kill conditions

- The factorization must be derived from `p.eval center=0`; a caller-supplied
  divided-difference identity is forbidden.
- Nonlinear ODE uniqueness may not be assumed.  The proof must reduce to the
  already governed scalar linear-ODE uniqueness theorem.
- The conclusion must cover the complete declared preconnected continuation
  domain, not merely a neighborhood of the anchor.
- This proves equilibrium rigidity.  Applying it to the selected nonfinite
  branch still requires typed evidence that the branch is an analytic
  polynomial-ODE trajectory on a connected finite-time domain anchored at its
  source point.

## Punctured overlap transfers the fiber-product pole

### Eigenquestion

Once the selected reciprocal branch and constructed fiber-product lift share
a connected punctured chart, must equality and the exact pole order still be
assumed?

### Candidate construction

Let `selected` and `liftedTarget` be analytic on one open preconnected
punctured neighborhood of the uniformizing origin.  Assume only:

1. they meet at one anchor;
2. their target-time coordinates agree on the overlap; and
3. the target-time derivative is nonzero at the common anchor.

The analytic inverse-function theorem identifies the two germs near the
anchor, and the identity theorem propagates equality through the connected
overlap.  If the overlap domain belongs to `nhdsWithin 0 {0}ᶜ`, this equality
is an eventual equality on the punctured germ.  Meromorphic congruence then
transfers both meromorphicity and the exact order of
`(liftedTarget-targetCenter)⁻¹` to
`(selected-targetCenter)⁻¹`.

### Intended formal surface

`FormalAnalyticRamifiedFiberProductOverlap` defines a raw punctured-overlap
record containing domain topology, branch analyticity, anchor compatibility,
target-time compatibility, and the noncritical anchor.  Its terminal theorem
derives complete overlap equality, meromorphicity of the selected inverse
displacement, and exact order `-sourceOrder` by reusing
`FormalAnalyticSheetOverlap.AnalyticCoordinateOverlap` and Mathlib's
punctured-germ meromorphic congruence.

### Counterattacks and kill conditions

- Equality of branches may not be a record field.
- Meromorphicity and pole order of the selected branch may not be premises.
- The overlap must occupy a punctured neighborhood filter, not an arbitrary
  connected set disjoint from the uniformizing center.
- Construction of the raw overlap from the globally selected continuation
  remains separate; this kernel pays uniqueness and valuation transfer only.

## Julia as pullback invariance of the Abel one-form

### Eigenquestion

Must target-time compatibility on the selected finite-to-infinity overlap be
supplied globally, or is it forced by Julia's identity?

### Governing isomorphism

For a time-one endpoint `F` of `x'=p(x)`, Julia says

```text
p(F(x)) = F'(x) * p(x).
```

At regular points this is precisely invariance of the Abel differential:

```text
F*(dy / p(y)) = dx / p(x).
```

With reciprocal endpoint `z(x)=1/F(x)`, the polynomial-reversal identity
converts this into

```text
z'(x) = reciprocalVectorField(p,z(x)) / p(x).
```

The infinity-time derivative cancels the reciprocal vector field, while the
finite Abel derivative is `1/p(x)`.  Therefore

```text
d/dx (T_infinity(z(x)) - A(x)) = 0.
```

On an open preconnected overlap this difference is constant.  Equality at one
anchor gives the exact target-time compatibility consumed by the punctured
fiber-product overlap kernel.

### Intended formal surface

`FormalPolynomialFiniteInfinityAbelSeparation` should derive the reciprocal
endpoint derivative from an explicit endpoint derivative plus Julia's scalar
identity, using the existing reversal theorem.  It should then prove
connected-domain constancy of `T_infinity ∘ reciprocal - finiteTime` from
the constructed finite/infinity derivative identities.  The terminal theorem
must expose Julia, not assume the separated-time equality.

### Counterattacks and kill conditions

- Do not accept target-time compatibility as a premise.
- Do not accept the reciprocal derivative formula as a premise; derive it
  from endpoint differentiation, inversion, Julia, and polynomial reversal.
- All divisor nonvanishing conditions must be explicit on the punctured
  domain.
- The theorem pays compatibility on a supplied connected overlap; it does not
  construct the selected endpoint branch or the overlap domain.

## Typed selected regular Julia end

### Eigenquestion

Can the regular selected-continuation consequence be expressed as one typed
carrier whose fields are raw branch/domain data, with time compatibility,
branch equality, meromorphicity, and pole order all derived?

### Candidate carrier and theorem

For a constructed `PolynomialRegularInfinityFiberProduct`, record:

1. an open preconnected source overlap and an open preconnected punctured
   uniformizing overlap;
2. the selected endpoint, its derivative, and its reciprocal pullback;
3. the map from the uniformizing overlap to the source overlap;
4. endpoint differentiation plus Julia, source/endpoint/reverse divisor
   avoidance, and the two constructed coordinate derivative restrictions;
5. analyticity of the selected pullback and constructed lift on the declared
   overlap; and
6. one anchor match.

Do not record selected target-time compatibility, branch equality,
meromorphicity, or valuation.  Abel separation supplies the first.  The
punctured fiber-product overlap theorem supplies the other three, with inverse
order exactly `-1`.

The resulting `FormalPolynomialRegularJuliaFiberProductEnd` theorem is the
typed inference surface for the remaining conditional regular Julia carrier.
The only global obligation after it is to construct this carrier from the
meaning of a selected polynomial autonomous continuation.

### Kill conditions

- No conclusion field may reappear under an alias such as `compatibleEnd` or
  `selectedSheet`.
- The source and uniformizing domains must be distinct typed objects linked by
  the fiber-product source projection.
- The anchor-zero constant in Abel separation must be derived using the anchor
  match and the fiber product's own time compatibility.
- Exact selected inverse order must be inherited through punctured eventual
  equality, not recomputed by an assumed asymptotic expansion.

## Cross-Julia algebraic elimination

### Eigenquestion

Are the two remaining global continuation carriers artifacts of following
the two factors as ODE trajectories, when the factorization and the two Julia
identities already force the hidden inner endpoint to be algebraic?

### Governing isomorphism

Write the two time-one endpoints as

```text
A = exp(f d/dx)(x),
B = exp(g d/dx)(x),
F = B ∘ A.
```

Their Julia identities and the chain rule are

```text
f(A) = A' f(x),
g(B) = B' g,
F' = (B' ∘ A) A'.
```

Evaluating the second identity at `A` and eliminating both derivative
factors gives the cross identity

```text
g(F(x)) f(A(x)) = F'(x) f(x) g(A(x)).
```

For fixed `x`, define the polynomial in the hidden value `Y`

```text
K_x(Y) = g(F(x)) f(Y) - F'(x) f(x) g(Y).
```

If coefficients `i,j` witness nonproportionality,

```text
coeff_i(f) coeff_j(g) - coeff_j(f) coeff_i(g) != 0,
```

then the same determinant applied to the coefficient vector of `K_x`
cancels the `F' f(x)` term and leaves `g(F(x))` times that witness.  Hence
`K_x` is nonzero wherever `g(F(x)) != 0`.  The identity `K_x(A(x))=0`
therefore makes `A` algebraic over the function field generated by `F`.

For the critical endpoint, `F` lies in an explicit quadratic extension of
`C(x)`.  Differentiation stays in that extension.  Splitting `K(A)` into its
rational and radical parts and taking the quadratic norm should eliminate the
radical and yield a nonzero polynomial relation over `C(x)` for `A`.
Newton--Puiseux normalization would then give finite ramification and a
meromorphic selected inner branch at every finite base point.  The
proportional degeneracy is already the governed single-flow route.

### Intended formal surface

1. `FormalPolynomialCrossJuliaElimination` derives the cross identity from
   two Julia identities, endpoint composition, and the chain rule.
2. The same module constructs `K_x` and proves its evaluation at `A(x)` is
   zero.
3. A determinant lemma proves `K_x != 0` from an explicit coefficient
   nonproportionality witness and `g(F(x)) != 0`.
4. A later quadratic-norm theorem consumes the explicit algebraic critical
   endpoint and produces a bivariate annihilator over `C`.

### Counterattacks and kill conditions

- The cross identity must be derived; it may not be a carrier field.
- Composition orientation is checked symbolically and in a noncommuting
  polynomial example.
- `natDegree f = natDegree g` is not a substitute for
  nonproportionality; the theorem uses an exact coefficient determinant.
- The nonzero-polynomial proof must exhibit a coefficient, not appeal to the
  intended interpretation of `K_x`.
- A pointwise root equation alone does not grant finite ramification.  The
  subsequent norm/elimination and Newton--Puiseux steps remain explicit.
- If the quadratic norm vanishes despite a nonzero extension polynomial, the
  route is killed rather than patched by assuming algebraicity.

### Conjugate-norm refinement

The quadratic elimination need not be written in coordinates.  Let `L/K` be
a quadratic coefficient field with involution `sigma`, and let `P(Y)` be the
cross-Julia polynomial over `L`.  Its conjugate norm

```text
N(P) = P * sigma(P)
```

has three decisive properties:

1. `P != 0` implies `N(P) != 0`, because coefficient conjugation is
   injective and `L[Y]` is a domain;
2. every root of `P` in any commutative extension is a root of `N(P)`; and
3. if `sigma^2=id`, every coefficient of `N(P)` is fixed by `sigma`.

Thus the norm cannot suffer the proposed radical-elimination cancellation.
For the explicit quadratic endpoint field, fixed coefficients descend to the
rational-function base field.  `FormalPolynomialConjugateNormElimination`
should prove the three properties over arbitrary fields and commutative
extension algebras.  It does not assume or construct the later fixed-field
descent.

### Fixed-field descent refinement

Coefficientwise invariance should construct, rather than merely assert, a
polynomial over the fixed subfield

```text
K^sigma = {a : K | sigma(a)=a}.
```

Given `Q : K[Y]` and proofs that all coefficients of `Q` are fixed, sum its
monomials with subtype-valued coefficients to obtain
`Q_fixed : K^sigma[Y]`.  Mapping `Q_fixed` through the subtype embedding must
recover `Q` exactly.  Injectivity then preserves nonzeroness, and `eval₂_map`
transfers every selected root of `Q` to the descended relation.  This is a
general coefficient-descent theorem; identifying the explicit quadratic
endpoint's fixed field with `C(x)` remains the next application-specific
step.

### Endpoint-field correction after the discriminating audit

The proposed critical specialization in the preceding two refinements is
killed.  The connection's logarithmic derivative lies in the explicit
quadratic differential field, but the selected endpoint is its exponential
integral; no proof that the endpoint itself is quadratic-algebraic over
`C(x)` exists, and it must not be treated as such.  The conjugate-norm and
fixed-field theorems remain valid general kernels, but they do not instantiate
the critical endpoint route.

The corrected local coefficient field is simpler.  Pull the cross-Julia
annihilator back along the already constructed critical uniformizer.  Its
coefficients are analytic germs because they are polynomial expressions in
the selected analytic endpoint, its derivative, and the uniformized base.
Thus the required normalization theorem is local:

```text
punctured-holomorphic A
+ nonzero analytic polynomial family P(t,Y)
+ P(t,A(t)) = 0
=> A is meromorphic at t=0.
```

Choose one nonzero coefficient germ of `P`, divide all coefficients by it,
and use their finite meromorphic orders to obtain a polynomial root bound.
Multiplying `A` by a sufficiently large power of `t` makes it locally
bounded; Riemann removability then constructs a meromorphic extension.  Since
the selected continuation is already single-valued on the punctured
uniformizer, no additional fractional ramification is required at this step.
This replaces the false rational-function fixed-field specialization while
retaining the cross-Julia elimination mechanism.

### Analytic polynomial-root normalization surface

The first theorem should isolate the bounded case.  A carrier owns a family
`P_t(Y)` which is eventually monic of one fixed degree, has coefficient germs
analytic at the puncture, and annihilates a punctured-holomorphic branch.
Finite coefficient continuity bounds the Cauchy root bound uniformly;
Riemann removability then constructs a finite analytic extension of the root.

The second theorem should normalize a general nonzero analytic polynomial
family.  Choose a coefficient germ of maximal polynomial index whose
meromorphic order is the finite integer `s`.  Its analytic normal form is
`(t-c)^s u(t)` with `u(c) != 0`.  For

```text
Z(t) = (t-c)^s A(t),
```

divide the transformed relation by the common `(t-c)^s` factor.  The new
leading coefficient is `u`; division by `u` gives the monic carrier above.
Consequently `Z` extends analytically and `A` is meromorphic.  A branch with
no finite analytic extension then has negative finite order by the existing
meromorphic infinity-chart kernel.

Kill conditions:

- boundedness of the scaled root may not be a carrier field;
- the polynomial family must be nonzero as a germ, not merely nonzero at one
  remote point;
- the chosen coefficient's finite order and analytic normal form must be
  constructed;
- Cauchy's root bound must be applied to the specialized polynomial actually
  annihilating the branch;
- this local theorem consumes a single-valued punctured branch and does not
  claim global continuation or monodromy triviality.

## Ramified Julia valuation balance

### Eigenquestion

Once cross-Julia elimination supplies an algebraic hidden factor and local
normalization supplies a finite uniformizer, what exact numerical constraints
does Julia impose on a branch which passes through infinity and returns to a
finite endpoint?

### Governing isomorphism

Let the base coordinate, inner endpoint, and total endpoint have leading
orders

```text
x(t)-x0       :  q,
A(t)          : -r,
F(t)-y0       :  ell,
```

where `q,r,ell > 0`.  Let the inner generator `f` have degree `d >= 2`
and root multiplicity `m` at `x0`.  Pulling
`f(A)=A_x f(x)` back to the uniformizer gives

```text
A_t f(x(t)) = x_t f(A(t)).
```

The four exact meromorphic orders are respectively

```text
-r-1, q*m, q-1, -r*d.
```

Additivity of order therefore forces

```text
r*(d-1) = q*(1-m).
```

Positivity immediately gives `m=0`.  For the outer generator `g` of degree
`e >= 2`, with target-root multiplicity `n`, the pulled-back Julia identity

```text
F_t g(A(t)) = A_t g(F(t))
```

similarly forces

```text
ell*(1-n) = r*(e-1),
```

and hence `n=0`.  On the selected critical germ `q=ell=2`, the two balances
give `r*(d-1)=r*(e-1)=2`; since `r>0`, `d=e`.  This is the missing numerical
bridge from a finite ramified algebraic branch to the governed equal-degree
infinity collision theorem.

### Intended formal surface

1. Prove the reusable analytic lemma that a meromorphic pole of order `r>0`
   has derivative order `-r-1`, from Mathlib's meromorphic normal form; do not
   accept the derivative order as a premise.
2. Prove an order-equality kernel which derives each balance from an eventual
   Julia product identity and exact orders of the polynomial substitutions.
3. Prove the positive-arithmetic consequences, including critical equal
   degree, over natural ramification, pole, multiplicity, and degree data.
4. Keep algebraic-branch normalization separate: this theorem consumes a
   supplied finite ramified meromorphic carrier and does not claim that every
   algebraic branch has already been normalized.

### Counterattacks and kill conditions

- A carrier field equal to either final balance is forbidden.
- The derivative-order decrement must be derived from the pole normal form.
- Product-order equality must come from Julia plus meromorphic-order
  additivity, with finite orders made explicit; no cancellation heuristic is
  allowed.
- The critical equal-degree conclusion requires both the inner and outer
  balances.  One balance alone does not compare the generators.
- This kernel does not replace Newton--Puiseux normalization or identify the
  coefficient fixed field with the critical rational-function base.

## Cross-elimination and valuation results

The following fourteen general-purpose terminal surfaces now compile and have
passed LeanMill's carried-theorem ratification, source-aware negated-
conclusion control, kernel parity, and axiom allowlist:

1. `FormalPolynomialCrossJuliaElimination.polynomial_cross_julia_elimination_terminal_certificate`
   derives the cross identity, hidden-value annihilator, and determinant
   nonzeroness.  Governed record
   `d12e3cc2b9fef75e72da10d85720ef834a621ea7ab25af9703b287f0c41b21a7`;
   parity
   `e6f44bc8b320e2e47839d87bde15844ca0382be875feb75b1eb6ccd52fe2d384`;
   closure source
   `75b80cae7388`.
2. `FormalPolynomialConjugateNormElimination.polynomial_conjugate_norm_elimination_terminal_certificate`
   proves nonzero conjugate norm, root transfer, and involution-fixed
   coefficients.  Governed record
   `db1fb92250cb6d1c31ad5321e597e035e5df93b3b62cddfe670e55e62dcce1c6`;
   parity
   `2e565dd830b8fff9c7c18b21a9fe3013e4ef703a48e596303415201ed13bb558`;
   closure source
   `577add067b88`.
3. `FormalPolynomialFixedFieldDescent.polynomial_fixed_field_descent_terminal_certificate`
   constructs the fixed-subfield polynomial and preserves both nonzeroness
   and roots.  Governed record
   `3cd1857ebcac724ce61ef9065ed8f58d90cf45405f3dea433f93d1f368f9fa2a`;
   parity
   `3a54e6e77ac693ceeb318e16cc113c2fa4b78d632785c4a2ae41f1b0af6600eb`;
   closure source
   `a1cc27e9d4ee`.
4. `FormalMeromorphicPoleDerivative.meromorphic_pole_derivative_terminal_certificate`
   derives the one-step derivative order drop for every finite nonzero
   meromorphic order.  Governed record
   `b0e4b68dff9e9ccdc53f7e370325659037e153f29ea4c584b066a0226c672b84`;
   parity
   `29dff8a83e9cfb42352d65e732bf92ad7cc1e042434cfaa3f47209256fca7957`;
   closure source
   `ec9fa8a2a612`.
5. `FormalPolynomialMeromorphicOrder.polynomial_meromorphic_order_terminal_certificate`
   derives finite-center multiplicity order and infinity degree order from
   polynomial factorization and reversal.  Governed record
   `502a7ab961806440b33e80c5825cf977fd54d2984e521647f9032e8b9ec90c7c`;
   parity
   `e6936a0f4c39ccc571def08116f32cbadba6d1f47de57b28df9cdd9dd50a7c35`;
   closure source
   `a3139ba245e3`.
6. `FormalRamifiedJuliaValuationBalance.ramified_julia_valuation_balance_terminal_certificate`
   derives source and target regularity, both ramification equations, and
   equal degree at a common positive order.  Governed record
   `7743818793121cde40b7efd56be480c969bf7b12c8e4b7613b3476a2e5de8ad1`;
   parity
   `94b823593ae01dd6361f1430780b38bfae4e49fceb32ec130f4dc98a1a011a62`;
   closure source
   `9c59c8717c61`.
7. `FormalAnalyticMonicPolynomialRoot.analytic_monic_root_terminal_certificate`
   derives a uniform Cauchy root bound and a finite analytic extension from
   the coefficient germs of a monic fixed-degree family.  Governed record
   `2b3d051224b5791856e6d6f66dc43c49d17a7b4946cd5aad662b0a7fdf840f58`;
   parity
   `c198f08211337cab23e22a16da7164846ea6111a78b282769104431fe73e1b9c`;
   closure source
   `bf6267209996`.
8. `FormalScaledMonicMeromorphicRoot.scaled_monic_meromorphic_root_terminal_certificate`
   divides the finite analytic extension of a coordinate-power-scaled root
   by that coordinate power and derives a meromorphic germ.  Governed record
   `969d1f2a09b57db675f606aa5e03186a76f4ef79ae9371e9ccc74fc34490bfc1`;
   parity
   `af7db010b01a60e7072f2fce66ff6c66c417c7130590c42a21e1f61176f85388`;
   closure source
   `c8277e3da0b4`.
9. `FormalPolynomialRootScaling.polynomial_root_scaling_terminal_certificate`
   constructs the explicit degree-preserving monic polynomial annihilating
   a coordinate-power-scaled root, with only nonnegative coordinate powers
   in its lower coefficients.  Governed record
   `04aa5f6883eed3dc2c6ced156b58615f053463cdc029140125521f42f7f653c7`;
   parity
   `eb8d72532abfd71c9987b7bef9d949972a7cf2474dee4419baeb3ab51dc3589b`;
   closure source
   `a8e7379a1103`.
10. `FormalAnalyticPolynomialRootNormalization.analytic_polynomial_root_normalization_terminal_certificate`
    starts from raw analytic polynomial coefficients, finite leading-
    coefficient order, a punctured differentiable branch, and the root
    identity; it constructs the scaled monic carrier and derives
    meromorphicity.  Governed record
    `54bf8fb2bcd36ebbd3be4d4f3592598ee86d136df0391723b110052ee5e526de`;
    parity
    `ea8b4f4dc97ab5a6763c24e2b01190231dce2449ffa07a9ea073950b9be5ff1b`;
    closure source
    `076fb6257d86`.
11. `FormalAnalyticPolynomialRootSelection.analytic_polynomial_root_selection_terminal_certificate`
    selects the highest active coefficient germ inside a finite degree bound,
    proves the selected degree positive from the root identity, and derives
    its finite nonnegative analytic order.  Governed record
    `c94ef0ebd9281e00199bf1f5d7a855d5f1fc74fa4a40bac0b0ee43295b5360d0`;
    parity
    `94cab9e14b14184901f88131de2e092b80ce6957dc09b0507c91586495e45ebc`;
    closure source
    `ee5753fbab4f`.
12. `FormalAnalyticCrossJuliaMeromorphic.analytic_cross_julia_meromorphic_terminal_certificate`
    pulls the cross-Julia eliminant into an analytic parameter germ and uses
    the determinant witness plus endpoint nonvanishing to force an active
    coefficient; the hidden endpoint is therefore meromorphic.  Governed
    record
    `4fa39c09944b3f5564b6c7af3fcba4183c1e7e9dd74046cf1aea211e6e2a3d74`;
    parity
    `469fb0ee715a6d100873cc98b30e7a7823a750b70bc8b561b32f95615c9aa62f`;
    closure source
    `9be8a6f89748`.
13. `FormalAnalyticCrossJuliaPoleChart.analytic_cross_julia_pole_chart_terminal_certificate`
    turns failure of finite analytic extension into an exact positive pole
    order and an analytic reciprocal chart.  Governed record
    `00cda7274fa196dd302b2f6a8b34fae98fdbadb148b74ab0d7b5206b22679601`;
    parity
    `3dec8b88a629f413a43e3d4c47b62574c579109960cc0492c0e6f5ca18a20ddb`;
    closure source
    `4d043d962f3a`.
14. `FormalAnalyticTwoFlowRamifiedBalance.analytic_two_flow_ramified_balance_terminal_certificate`
    constructs both Julia valuation carriers on that same pole sheet and
    derives regular finite centers, both exact ramification balances, and
    equal generator degree.  Governed record
    `190fe249b1022919cb810b88180d62ef740d3758659e07b735783b2773399278`;
    parity
    `9c9acad8bafcf94054a9a10a6608890d9d2dd72e788b65bb9a12d4139206c6bc`;
    closure source
    `0b50d1535eea`.
15. `FormalRamifiedCubicCollisionExclusion.ramified_cubic_collision_exclusion_terminal_certificate`
    proves exact finite-order multiplication under formal substitution,
    collapses the critical nonproportional collision arithmetic to
    `(ramification, degree, collisionDegree, collisionOrder) = (1,3,2,3)`,
    and excludes that branch from the vanishing linear and cubic critical
    jets once the centered Abel identity is available.  Governed record
    `9a230f824ff40174bff5c3343ff3f3dc52d273e1485870f070b05cae06a2b523`;
    parity
    `e5b5d167c861da46e5824d5a28f557fba5289aea95963bca754fe8d6fedc7a9e`;
    closure source
    `ad3470fada29`.

This closes the general analytic cross-elimination-to-ramified-balance route.
The remaining bridge is now the critical two-flow consequence: bind the
selected order-two source and target germs to item 14, feed its equal-degree
conclusion into the all-order polynomial infinity-collision/proportional
alternative, and exclude both outcomes with the already constructed critical
jets.  Only that consequence can replace the two old global-continuation
leaves in the coverage DAG.

## Discrete ramified-collision collapse

### Eigenquestion

Can the equal-degree infinity alternative be transported to the selected
critical uniformizer without importing a rational Puiseux exponent as a
carrier field?

### Governing isomorphism

Let the reciprocal hidden branch have positive uniformizer order `r`, and
let the common normalized polynomial degree be `d`.  The inner Julia balance
at the critical order-two source germ is

```text
r * (d - 1) = 2.
```

There are therefore only two natural-number possibilities:

```text
(r, d) = (2, 2)  or  (r, d) = (1, 3).
```

In the normalized nonproportional branch, the largest collision degree `e`
satisfies `2 <= e < d`, and the exact infinity time-coordinate collision
order is

```text
k = 2*d - e - 1.
```

The quadratic possibility admits no such `e`.  In the cubic possibility,
`e = 2` and `k = 3`.  Exact order multiplication under formal substitution
then says that pulling the collision back along the reciprocal branch has
order `r*k = 3`.  Thus the entire nonproportional infinity family collapses
to one mandatory nonzero cubic uniformizer jet.

The selected critical source displacement is quadratic and its constructed
endpoint displacement has zero coefficients in degrees one and three.
Substitution into any analytic coordinate germ preserves this cubic absence:
all outer powers of degree at least two start in uniformizer degree four, and
the linear outer term multiplies the zero cubic coefficient.  Hence the
finite Abel-coordinate difference on the selected critical sheet has zero
cubic coefficient.  Once Julia/Abel separation identifies that difference
with the pulled-back infinity collision, the nonproportional route is
impossible.  The remaining normalized-equality route is the proportional
one and is discharged by the constructed single-flow obstruction, whose
nonzero fifth jet is already governed.

### Intended formal surface

1. Prove exact multiplication of finite `PowerSeries.order` under
   substitution over a field when the inner constant coefficient is zero.
2. Prove that a zero-constant inner series with zero coefficients one and
   three gives zero coefficient three after substitution into an arbitrary
   outer series.
3. Combine the critical balance, the exact collision order, and a supplied
   Abel-coordinate identity to exclude every nonproportional collision.
4. Keep the Abel-coordinate identity out of the carrier conclusion: it must
   be derived separately from the two Julia identities and centered local
   time primitives.

### Counterattacks and kill conditions

- A premise equal to `r = 1`, `d = 3`, `e = 2`, or pulled-back order three is
  forbidden; those are conclusions of the balance and collision equations.
- A mere lower bound on substitution order is insufficient; the leading
  coefficient must be shown nonzero.
- The cubic-zero lemma must allow arbitrary outer analytic coordinates, not
  only the identity coordinate.
- The selected critical specialization must construct the Abel-coordinate
  equality from Julia.  Supplying that equality as an unexplained adapter
  fact does not close universal continuation coverage.
- This kernel excludes the nonproportional local infinity outcome only.  It
  does not by itself identify equal normalized generators with the actual
  factor endpoints or discharge the proportional single-flow branch.

## Two Julia identities as one centered Abel collision

### Eigenquestion

Can the formal identity required by item 15 be derived over the common
uniformizer directly from the two Julia identities, without choosing a local
inverse to the quadratically ramified source coordinate?

### Isomorphism

Write the hidden factor as `A(t)`, its analytic reciprocal as `z(t)`, the
critical source as `x(t)`, and the total endpoint as `y(t)`.  On the
punctured sheet, `z=A⁻¹`.  For the inner generator `f` and outer generator
`g`, the Julia identities have the parameterized forms

```text
A' * f(x) = x' * f(A),
y' * g(A) = A' * g(y).
```

Polynomial reversal gives

```text
I_f(z) * z' = A' / f(A),
I_g(z) * z' = A' / g(A),
```

where `I_p(z) = -z^(deg p - 2) / p.reverse(z)` is the infinity Abel
integrand.  The two Julia identities therefore imply

```text
d(T_f(z(t)))/dt = d(S_f(x(t)))/dt,
d(T_g(z(t)))/dt = d(S_g(y(t)))/dt.
```

Each separated difference is constant on one punctured complex ball.  All
four coordinate compositions extend analytically to the uniformizer center;
normalizing every time coordinate to vanish at its own center identifies the
two constants.  Subtraction yields

```text
(T_g - T_f)(z(t)) = S_g(y(t)) - S_f(x(t)).
```

This is the analytic identity whose Taylor-series image is the `habel`
input of item 15.

### Intended formal surface

1. Generalize the existing one-flow finite/infinity cancellation from an
   unramified source variable to a common uniformizer and raw pointwise Julia
   data.
2. Integrate on a supplied open preconnected punctured domain and extend the
   constant across the center by analyticity.
3. Normalize at the center and subtract the two derived identities.
4. Transport the resulting eventual analytic equality to Taylor power
   series; the adapter must construct the formal substitutions or prove the
   required third-coefficient consequence.

### Counterattacks and kill conditions

- Introducing an inverse of `x(t)` is forbidden: the critical source has
  order two at the uniformizer center.
- A carrier field equal to either separated-time equality, their difference,
  or the final Abel identity is forbidden.
- The reciprocal derivative must be tied to the hidden derivative and
  polynomial reversal; an arbitrary derivative field cannot replace this
  calculation.
- Punctured constancy alone is insufficient.  Analytic extension and the
  four zero normalizations must determine the center constant.
- The sign and generator order must agree with the collision convention in
  `FormalPolynomialFlowAtInfinity`; a global sign flip is harmless for
  order, but an untracked swap is not accepted.

### Ratified two-Julia result

`FormalAnalyticTwoJuliaAbelCollision.analytic_two_julia_abel_collision_terminal_certificate`
implements the common-uniformizer calculation.  Its carrier contains the two
raw Julia identities, reciprocal/hidden differential compatibility, an open
preconnected punctured domain, and the analytic coordinate primitives.  It
contains no separated-time or Abel equality.  Governed record
`0f104267f8212ff65290ee6e6b22d9a709703e9b0b88d78df009de5d8f98ea2d`;
parity
`3c901fae389ee436e29787a6661900e3ae1c02d7c1ff26d2a822626c919c7933`;
closure source
`e964c879af67`.

## Canonical infinity-time Taylor binding

### Eigenquestion

Does the analytic infinity-time primitive used by the two-Julia carrier have
exactly the formal normalized time-coordinate series used by the all-order
polynomial collision theorem?

### Governing identification

For a monic degree-`d` generator `p`, polynomial reversal gives

```text
taylor_0 (p.reverse.eval) = reciprocalDenominator d p.
```

Consequently the canonical Taylor series of the analytic reciprocal-time
integrand is

```text
-X^(d-2) * (reciprocalDenominator d p)^(-1).
```

Any analytic primitive normalized to zero at the reciprocal origin has
Taylor series

```text
-normalizedTimeCoordinate d (reciprocalDenominator d p).
```

Thus, for source generator `p` and target generator `q`, the analytic
collision `T_q-T_p` has Taylor series

```text
normalizedTimeCoordinate(p) - normalizedTimeCoordinate(q),
```

with the same sign convention as the existing all-order collision theorem.

### Intended formal surface and counterattacks

1. Prove equality between analytic vanishing order and the order of the
   canonical Taylor power series.
2. Prove the reversed-polynomial Taylor identity coefficientwise, including
   coefficients above the natural degree.
3. Identify the normalized primitive by derivative equality plus constant
   coefficient, rather than taking its series as a carrier field.
4. A missing leading scalar is allowed only after monic normalization.  The
   sign must be derived from `z'=-A'/A^2` and retained through subtraction.

### Ratified Taylor-binding result

`FormalAnalyticPolynomialTimeTaylor.analytic_polynomial_time_taylor_terminal_certificate`
proves the order correspondence and signed primitive identification above.
The stronger helper theorem identifies the difference `T_q-T_p` with the
existing formal collision `N_p-N_q`.  Governed record
`d1f7ec472077e8c38dfd52c5733d369ac31a01e0418f66712d7f78c00c196d8b`;
parity
`8d2138996a6d5e2a85cb5b08f950692787a4efb523021bbafc034bfa91c37304`;
closure source
`4e7e9168917b`.

## Nonproportional critical branch: analytic-formal assembly

### Eigenquestion

Do the ramification balance, polynomial collision alternative, canonical
time-coordinate binding, and two-Julia Abel identity jointly force the two
normalized generators to be equal?

### Proof skeleton

Assume the normalized monic tangent generators differ.  The polynomial
collision theorem supplies `2 <= e < d` and formal collision order
`2*d-e-1`.  The critical balance `r*(d-1)=2` collapses the data to
`r=1`, `d=3`, `e=2`, so the analytic infinity-time collision has order
three.  Analytic-order composition with the reciprocal germ of order one
then gives order three for the pulled-back infinity collision.

The derived two-Julia identity identifies that pullback with the difference
of the two finite time-coordinate compositions.  Third-order Faà di Bruno
shows each finite composition has zero third derivative because its critical
inner germ has zero first and third derivatives.  The right side therefore
has zero cubic Taylor coefficient, contradicting exact order three on the
left.  Hence the normalized generators are equal.

### Counterattacks and kill conditions

- Generator equality must be a conclusion after the complete collision
  alternative; it cannot be a carrier field.
- Exact collision order must come from the all-order theorem, not a finite
  coefficient table.
- The reciprocal order and balance are supplied by the ramified Julia
  theorem; no premise may specialize them to `r=1` or `d=3`.
- The finite-side cubic cancellation must allow arbitrary analytic Abel
  coordinates and use Faà di Bruno.
- This assembly excludes the nonproportional branch.  The resulting equal
  normalized generator still has to be connected to the proportional
  single-flow obstruction in the critical root assembly.

### Ratified assembly result

`FormalAnalyticRamifiedCubicCollision.analytic_ramified_cubic_collision_terminal_certificate`
implements the full contradiction and concludes equality of the two
normalized generators.  Its only branch split is the governed all-order
polynomial coefficient alternative.  Governed record
`561601aea6b535405cf050eed5773d99340d7132fc47502a726905f158d2883b`;
parity
`571cde2bd9ac9f8e19f39ad36fead3288949a100ec1d393ca9c141c44311a9ae`;
closure source
`c790c602e2b7`.

The residual is now the proportional assembly.  A sharper local route avoids
global flow uniqueness: once the normalized generators agree, the two
parameterized Julia identities can be glued directly across the hidden pole
to produce Julia's identity for the complete source-to-target endpoint.  That
derived identity can then feed the governed constructed single-flow
obstruction.  The local glue and its critical-chart adapter remain open.

## Proportional branch as local Julia composition

### Eigenquestion

Can equal generators in the two Julia rows be converted into a Julia identity
for the complete endpoint without identifying either factor with a globally
parameterized flow?

### Algebraic reduction

Write the common generator as \(p\), the uniformized source, hidden value, and
target as \(x(t),A(t),F(t)\), and their parameter derivatives as
\(x_t,A_t,F_t\).  The two carried identities are

\[
A_t p(x)=x_t p(A),\qquad A_t p(F)=F_t p(A).
\]

If \(D(t)\) is the spatial derivative factor of the complete endpoint, so
that \(F_t=D x_t\), then

\[
A_t\bigl(p(F)-D p(x)\bigr)=0.
\]

The hidden branch is a meromorphic pole of positive order.  Its derivative
therefore has finite negative meromorphic order one step lower and is
eventually nonzero on the punctured germ.  Cancellation gives

\[
p(F)=D p(x)
\]

there.  Analyticity of both sides extends the equality across the center.

### Counterattacks and kill conditions

- Do not assume endpoint Julia as a carrier field; derive it from the two
  Julia rows, derivative compatibility, and punctured nonvanishing.
- Do not divide by the ramified source derivative, which vanishes at the
  center.  Cancel only the hidden derivative on the punctured pole sheet.
- Do not invoke autonomous-trajectory uniqueness: the desired conclusion is
  an infinitesimal intertwining identity and follows before flow
  parameterization.
- Keep the complex polynomial identity separate from descent to the named
  real critical endpoint; the latter requires an explicit real-structure
  adapter or a complexified single-flow obstruction.

### Intended formal surface

1. A pointwise algebraic Julia-gluing lemma.
2. A `TwoJuliaAbelCarrier` theorem producing punctured endpoint Julia from
   generator equality, derivative compatibility, and hidden-derivative
   nonvanishing.
3. An analytic extension theorem producing a full neighborhood identity.
4. A pole-order lemma deriving the required hidden-derivative nonvanishing
   from the nonremovable cross-Julia branch.

### Ratified local glue

`FormalAnalyticProportionalJuliaComposition.analytic_proportional_julia_composition_terminal_certificate`
derives the complete endpoint Julia identity from equal generators, the two
parameterized Julia rows, derivative compatibility, and punctured
hidden-derivative nonvanishing.  Governed record
`1a92444ef57f1b5383fcbbe0bcaa006ddc95463b22dbc4dc64d920ca372ca3da`;
parity
`150bbe5d30f10382fc9ea3438ec78175eca68d5b2dd765a39dd71babc0c44559`;
closure source `de7ec522071b`.

`FormalAnalyticCrossJuliaPoleDerivative.analytic_cross_julia_pole_derivative_terminal_certificate`
derives the cancellation premise from nonremovability and exact meromorphic
pole differentiation.  Governed record
`cd82c9e767ced88b62a30df6cfabd741a387a88307273ab399dd0301e80b2a32`;
parity
`f5641417b89b6d2482a572a468053ed9772e30c820cb8e2635bd35ee3ec21c43`;
closure source `63b739a60628`.

## Coefficient-field lift of the critical single-flow obstruction

### Eigenquestion

Does the selected ramified root-factor contradiction exclude complex
polynomial generators, as required by a factorization over \(\mathbb C\), or
only the currently exposed real-coefficient generators?

### Candidate theorem

The root-factor proof uses polynomial division, exact power-series orders,
and the impossible equality

\[
2m=5
\]

for a natural root multiplicity \(m\).  Every step is valid over an arbitrary
characteristic-zero field.  The invariant-owning theorem should therefore be
field-polymorphic; the existing real critical endpoint becomes one adapter,
and its complexification becomes another.

### Counterattacks and kill conditions

- Do not infer that a complex generator has real coefficients from the real
  structure of the endpoint.
- Do not duplicate the root-factor proof into separate real and complex
  copies.  Generalize the common theorem and retain the existing real callers
  by type inference.
- Preserve the natural-number contradiction: the cast equality in the
  coefficient field must be reflected back through characteristic-zero
  injectivity before `omega` closes it.
- The field lift alone is not the critical terminal; a complexified selected
  endpoint adapter and the local proportional Julia glue are still required.

### Ratified field lift and complex critical adapter

`FormalRamifiedJuliaObstruction.polynomial_julia_root_factor_obstruction`
now works over every characteristic-zero field.  Its governed record is
`599c8d16981c2e4c3d8004ce30577d96ca38ce39b6cbd1257e2ebd98d481886c`;
parity
`026e4f3320d1ff07e744927d9a6e97d229cb0fb85346e5a79bcee643df6a2fcb`;
closure source `a7287e351393`.

`AxiomPackJacobianCriticalPuiseuxComplexJuliaAssembly.selected_complex_single_flow_analytic_terminal_certificate`
then transports an arbitrary complex-polynomial Julia identity through the
named selected analytic chart and applies the common root-factor theorem.
Its governed source is
`af8c74ed6f957966666e03ce4310f771ed79f5e3a1d481cb79df809477bc5381`;
parity
`9f4804d8a5614d6adc05287e994a880c7277f5ade55a0bb5811d073d87325789`;
closure source `434fe3a5da86`.

## Complete local critical two-Julia sink

The nonproportional and proportional branches now assemble without a
generator-coefficient reality premise.  Given a complete
`TwoJuliaAbelCarrier` bound to the selected critical source and target, the
ramified cubic collision forces equality of the normalized complex
generators.  Local Julia composition supplies Julia for the complete
endpoint, and the complex critical single-flow theorem gives the
contradiction.

`FormalAnalyticCriticalTwoJuliaExclusion.analytic_critical_two_julia_intrinsic_exclusion_terminal_certificate`
also removes punctured nonvanishing of the hidden derivative from the input:
positive reciprocal order and meromorphic derivative order derive it.  The
intrinsic certificate has governed source
`5b4aff342642468c8af44f51b1f9482b830fde267817dacdc898b3621806d600`;
parity
`91aafad52ad2080e3f368a8b54cba1c94d328e683a81ae50a0e639cfec684373`;
closure source `adb60bd25f9c`.

The derivative sublemma
`FormalAnalyticTwoJuliaDerivativeNonvanishing.analytic_two_julia_derivative_nonvanishing_terminal_certificate`
has governed source
`25e9aa08adcb7656225543bfde6401efd1ac1f35361d8496ede2d0656381b331`;
parity
`8b2902b8d7162c5ea1bbebf173c2d5b0de315c2222e340d4b93516df6d3a0187`;
closure source `b265df4f3a17`.

### Exact authority boundary after the local sink

The v32 coverage proposition `critical_terminal_excluded` is map-level: it
quantifies over an arbitrary selected two-polynomial-flow factorization and
requires an exhaustive continuation alternative.  The new theorem instead
quantifies over a supplied, completely populated `TwoJuliaAbelCarrier`.
Consequently it closes no existing v32 node by proposition identity.  It is
a new local sink, and attaching it directly to the root would silently
replace the adversary category.

The missing implication is

\[
\text{selected two-flow factorization}
\Longrightarrow
\text{complete critical `TwoJuliaAbelCarrier`}.
\]

## Cross-Julia germ to Abel-carrier assembly

### Eigenquestion

Can the existing `TwoFlowRamifiedCrossCarrier`, which already owns both
Julia rows, analytic source and target displacements, the nonremovable hidden
branch, and the common ramified order, construct all local Abel-carrier data?

### Candidate construction

1. Cross-Julia elimination and nonremovability construct the meromorphic
   pole and an analytic reciprocal germ.
2. The valuation-balance theorem proves regularity of both finite centers,
   a positive pole order, both balance equations, and equal generator degree.
3. The finite- and infinity-time-coordinate kernels construct four
   normalized analytic primitives.
4. Intersect the finitely many punctured-neighborhood facts with one small
   punctured complex ball.  This domain is open and preconnected and has the
   explicit anchor `center + radius/2`.
5. Bind all derivatives to canonical `deriv` functions.  On the chosen
   domain, the inverse rule derives the reciprocal derivative identity; the
   carried Julia rows, divisor avoidance, and primitive identities supply
   the remaining `TwoJuliaAbelCarrier` fields.

### Counterattacks and kill conditions

- The construction must not assume finite/infinity Abel equality; that is a
  conclusion of `TwoJuliaAbelCarrier.centered_abel_collision`.
- It must use the reciprocal produced from the same hidden meromorphic germ,
  not an unrelated locally constructed infinity sheet.
- The common domain must be constructed from the finite intersection of
  eventual facts and proved open/preconnected; a bare eventual-equality
  bundle is not a `TwoJuliaAbelCarrier`.
- The resulting theorem still does not construct the cross-Julia germ from a
  maximal selected factor continuation.  If the assembly succeeds, that
  global implication becomes the single invariant-owning residual.

### Ratified cross-Julia-to-Abel construction

`FormalAnalyticTwoFlowAbelCarrierAssembly.analytic_two_flow_abel_carrier_assembly_terminal_certificate`
implements the complete construction.  In particular, finite and infinity
Abel coordinates and their centered collision are no longer caller data once
a centered `TwoFlowRamifiedCrossCarrier` exists.  The theorem returns one
carrier together with its exact pole order, reciprocal analytic order, both
degree balances, and common generator degree.  Governed record
`65e1fffc99cee4b6c047d28cecf00dc3d92b85b6b2e995136f1530fe26a9a420`;
source
`f1b63b0b6360356b046733c7876f228c6d29c5e3a3555c124a5f7bb85e9cbab6`;
parity
`77b5af83870d907bb03c2884494e1817116ef29a74d4a0638bf38685cc1a67e7`;
closure source `fb48f8f5d6d2`.

### Corrected global residual and compiler consequence

The construction removes the local carrier-population problem but does not
remove selected continuation.  No current declaration constructs an
`AnalyticCrossJuliaCarrier` or `TwoFlowRamifiedCrossCarrier` from an arbitrary
two-flow factorization.  The required upstream theorem must construct the
punctured hidden branch, analytic source dependence, both Julia rows, and the
nonremovable alternative.  In a maximal-continuation formulation it must also
identify the finite cyclic sheet at polynomial infinity; that is analytic
continuation and monodromy control, not record packaging.

This exposes a general-purpose compiler defect.  The current
`FilteredTwoFlowPuiseuxProblem` requires a
`TWO_FLOW_FACTORIZATION_IDENTITY` receipt and then marks finite/infinity route
exhaustion, equal-degree infinity passage, and proportional reduction as
true.  Factorization identity and selected-route construction are different
propositions.  A corrected evidence schema must require a separate exact
selected-continuation/route-evidence receipt and fail closed when it is
absent.  Until that interface is split and the new receipt is backed by the
global theorem, the old two-flow filtered certificate is diagnostic only.

## One-Julia reconstruction of the two-flow carrier

### Eigenquestion

Once cross-Julia elimination has made the selected hidden factor algebraic
over the endpoint germ, must a continuation theorem transport both factor
Julia rows, or can the outer row be reconstructed from the cross identity,
the inner row, and the derivative chain rule?

### Governing identity

Write the selected source, hidden factor, and total endpoint as
(x(t),A(t),F(t)), their generators as (f,g), and the spatial derivative
of the total endpoint as (D(t)).  Cross-Julia elimination and the inner
Julia row give

\[
g(F)f(A)=D f(x)g(A),
\qquad
A_t f(x)=x_t f(A).
\]

Multiplying the first equation by (x_t), substituting the second, and using
(F_t=D x_t) gives

\[
f(x)\bigl(A_tg(F)-F_tg(A)\bigr)=0.
\]

The source displacement has positive finite analytic order and (f\ne0).
The exact polynomial-substitution order theorem therefore makes (f(x(t)))
eventually nonzero on the punctured germ.  Cancellation reconstructs the
outer Julia row

\[
F_tg(A)=A_tg(F).
\]

Thus a selected continuation only needs to transport the inner factor's
Julia identity.  The outer row is forced by the cross eliminant and the
total-endpoint derivative binding.

### Proposed object and theorem

Introduce a `RamifiedCrossFrame` owning the cross-Julia carrier, finite
source/target centers and displacements, their common positive order,
generator degrees, and exact bindings.  A
`OneJuliaRamifiedCrossContinuation` adds only:

- the transported inner Julia row;
- the derivative chain rule (F_t=D x_t); and
- failure of finite analytic extension for the hidden branch.

The theorem constructs the existing `TwoFlowRamifiedCrossCarrier`; its outer
Julia field is a conclusion.  The input contains neither that carrier nor an
outer Julia premise.

### Recurrence and primitive audit

`FormalAnalyticContinuation.IdentityContinuation` already transports a
polynomial Julia residual through supplied analytic charts.
`FormalAnalyticCrossJuliaMeromorphic.AnalyticCrossJuliaCarrier` already owns
the cross identity, and `FormalPolynomialMeromorphicOrder` already computes
the finite substitution order needed for cancellation.  No new continuation
engine or meromorphic-order primitive is required.  The semantic primitive
retriever was unavailable on 2026-08-06 and its lexical fallback surfaced
the existing two-flow compiler; no absence inference is drawn from that
degraded retrieval.

### Counterattacks and kill conditions

- Reject any input containing the outer Julia row or a completed
  `TwoFlowRamifiedCrossCarrier`.
- Derive eventual nonvanishing of (f(x(t))) from nonzero (f) and the exact
  positive source order; do not add it as a caller receipt.
- Keep (F_t=D x_t) distinct from factorization identity.  It is a derivative
  compatibility field of the selected total endpoint chart.
- If cancellation needs regularity of (f) at the source center, kill the
  route: the polynomial-substitution order theorem must work for every root
  multiplicity.
- Success narrows the global residual to construction of one selected hidden
  root continuation carrying the inner Julia identity.  It does not prove
  that such a continuation reaches the critical punctured chart.

### Intended formal surface

1. A frame object separated from Julia-row evidence.
2. An eventual nonvanishing lemma for polynomial evaluation on a positive-
   order analytic displacement.
3. A pointwise cross-plus-inner-to-outer cancellation lemma.
4. A constructor and terminal certificate returning a
   `TwoFlowRamifiedCrossCarrier`.

Scratch forecast `PL-SCRATCH-97fb17059048` assigns probability (0.78) to a
compiled theorem whose input contains neither the outer Julia row nor the
completed carrier.

### Ratified one-Julia assembly outcome

`FormalAnalyticSelectedInnerCrossAssembly.analytic_selected_inner_cross_assembly_terminal_certificate`
passes the focused build and governed ratification.  Its
`SelectedInnerJuliaContinuation` contains a finite
`IdentityContinuation`, the initial inner Julia residual, terminal chart
bindings, the two derivative chain rules, and failure of finite extension.
It derives the parameterized outer Julia row and constructs the established
`TwoFlowRamifiedCrossCarrier`.

The cancellation does not assume regularity of the first generator at the
source center.  `FormalPolynomialMeromorphicOrder` computes the evaluation
order as the ramification order times the arbitrary root multiplicity, which
is finite and hence eventually nonzero on the punctured germ.

Governed closure-record SHA-256:
`96d51d087064e2d520a80f2a254d22cff21aec9bdf1c450fe3c723d555a4fc4d`;
source SHA-256:
`f7aa03b482d98f5d8a0bf4d2976f77562b5ea78844d824c0f4fd6a384bb73287`;
recompilable-probe SHA-256:
`2b825243a656d001133be1f2b8c47b1460a03db8033bd541985fc97341c7d731`;
kernel-parity SHA-256:
`e93a65997e92a20270ed9c9609d337048af4c9825f041321c83d38b45eb6b76b`.

The global residual is correspondingly smaller: construct a selected hidden
root continuation that preserves the cross-polynomial root identity and the
inner Julia identity, prove the complete endpoint derivative binding, and
show that the nonanalytic critical branch enters the no-finite-extension
alternative.  A separate continuation of the outer factor is no longer
required.

## Regular finite-flow branch descent

### Eigenquestion

Can a finite selected branch of one polynomial autonomous flow remain
ramified over the source coordinate when both its source and endpoint centers
are regular points of the generator?

### Candidate theorem

Let (x(t)) and (A(t)) be analytic parameter germs with centers (x_0)
and (A_0), and let (p(x_0)p(A_0)\ne0).  Suppose the parameterized Julia
identity holds:

\[
A_t p(x)=x_t p(A).
\]

Construct normalized finite Abel coordinates (S,T) at (x_0,A_0) with
(S'=1/p), (T'=1/p), and (S(x_0)=T(A_0)=0).  Julia gives

\[
\frac d{dt}T(A(t))=\frac d{dt}S(x(t)).
\]

On a small connected ball the two sides agree because they agree at the
center.  Since (T'(A_0)\ne0), the analytic local inverse of (T) defines

\[
H=T^{-1}\circ S
\]

near (x_0), and (A=H\circ x) as germs.  Thus every regular finite branch
descends to an ordinary analytic source-coordinate chart, regardless of the
ramification order of (x(t)).

### Counterattacks and kill conditions

- The theorem must construct (H); analyticity of (A) as a function of
  (x) cannot be an input.
- Derive Abel-time constancy from the Julia row on a connected neighborhood,
  rather than assuming a time-separation equality.
- Both regularity hypotheses are essential to this first slice.  If either
  center is a generator root, record the equilibrium case as the next
  residual instead of silently using an inverse coordinate there.
- The theorem does not yet classify monodromy through infinity.  Its role is
  to eliminate regular finite endpoints from the source of critical
  ramification.

### Intended formal surface

1. A pointwise Abel-derivative cancellation lemma.
2. Construction of the two existing finite time coordinates.
3. Equality of the composed time coordinates on a small complex ball.
4. Analytic local inversion producing the finite endpoint germ and its exact
   factorization through the source germ.

The lexical primitive fallback re-surfaced the existing two-flow compiler;
the proof reuses `FormalPolynomialFiniteTimeCoordinate` and Mathlib's
analytic inverse theorem.  Scratch forecast `PL-SCRATCH-c0263b93f62b`
assigns probability (0.68) to a compiled descent theorem with the stated
regular-center boundary.

### Ratified regular-branch outcome

`FormalAnalyticRegularFiniteFlowDescent.analytic_regular_finite_flow_descent_terminal_certificate`
passes the focused build and governed ratification.  Its branch object
assumes only parameter analyticity, the Julia identity, and nonvanishing of
the generator at the two finite centers.  It constructs the normalized Abel
coordinates, proves their parameter compositions equal on a connected ball,
and analytically inverts the endpoint coordinate.  Thus the endpoint branch
is an analytic function of the source germ.

Governed closure-record SHA-256:
`e7307cce372e27db5e102cad462b444e1347e63b6a289560c802615c85352652`;
source SHA-256:
`76f99751ee599cf7f29d8a936c6e748b93197e20db5c3c9618c4508b4425fa74`;
recompilable-probe SHA-256:
`02b28d7b8b0a38fc6d3ed9d7f4c713cf17546ffb10d40c3f86f430c244961ed6`;
kernel-parity SHA-256:
`4e324e5094b3aa8f8799e174b3abc86dea95d6b3b8de3cf0af2aef3068f2f456`.

The finite selected-continuation residual is now concentrated at generator
zeros.  Mixed regular/equilibrium endpoints are subject to an immediate
valuation mismatch; equilibrium-to-equilibrium transitions require a
separate local classification.

## Equilibrium-transition collision with the critical Puiseux signature

### Eigenquestion

Can two selected transitions between simple equilibria of polynomial
autonomous flows compose to a germ whose leading term is linear and whose
first nonintegral term has exponent (5/2)?

### Preregistered local mechanism

For one generator with simple roots (a,b), write

\[
p(a+\xi)=\lambda_a\xi+A\xi^2+\cdots,
\qquad
p(b+\eta)=\lambda_b\eta+B\eta^2+\cdots.
\]

The Julia equation for a selected equilibrium transition predicts

\[
\eta=c\xi^\alpha
  \left(1+k\xi+\ell\xi^\alpha+\cdots\right),
\qquad
\alpha=\frac{\lambda_b}{\lambda_a},
\]

with

\[
k=-\frac{\alpha A}{\lambda_a},
\qquad
\ell=\frac{Bc}{\lambda_b}.
\]

For an outer transition of exponent (\beta), the composition has leading
exponent (\alpha\beta).  Taking

\[
\alpha=\frac32,
\qquad
\beta=\frac23
\]

restores a nonzero linear term.  The predicted first fractional correction
then has absolute exponent (1+\alpha=5/2), with relative coefficient

\[
c\left(\beta\frac{B}{\lambda_b}
       -\beta\frac{A_{\rm out}}{\mu_b}\right),
\]

up to the nonzero leading scale.  It is generically nonzero if the two
quadratic equilibrium jets are independent.

### Discriminating test and kill conditions

Construct exact rational polynomials divisible by (x^2) with simple
nonzero equilibrium pairs realizing derivative ratios (3/2) and (2/3).
Solve both local Julia equations through the first competing fractional
shell and compose them.

- **Success:** a deterministic exact replay produces a nonzero linear term,
  no earlier fractional term, and a nonzero (u^{5/2}) coefficient.
- **Kill:** the rational polynomial constraints are inconsistent, the
  (u^{5/2}) coefficient cancels identically, or a lower fractional shell
  necessarily occurs.
- **Boundary:** success is a local selected-continuation adversary.  It does
  not construct a global time-one factorization of the critical holonomy.
  For the Jacobian specialization, the endpoint equilibrium would also force
  the fixed value (F(-2)) to be algebraic over (\mathbb Q); that arithmetic
  condition remains separate.

Scratch forecast `PL-SCRATCH-388e0a15270a` assigns probability (0.86) to
the exact local mechanism surviving this test.

### Exact collision outcome

The replay
[`gauge_equilibrium_transition_puiseux_collision.py`](../axiompack_jacobian_field_parametric_20260720/gauge_equilibrium_transition_puiseux_collision.py)
constructs

\[
p(z)=z^2(z-1)(z-2)(11z-19),
\qquad
q(z)=z^2(z-2)(z-3)(35z-97).
\]

Their selected simple-equilibrium derivative ratios are exactly (3/2) and
(2/3).  With (u=t^2), exact coefficientwise solution of the two
parameterized Julia identities gives

\[
H(t)-2=t^3+\frac9{16}t^5+\frac{17}{3}t^6
  +\frac{1047}{512}t^7+O(t^8)
\]

and the composed endpoint

\[
F(t)-3=t^2+\frac{77}{12}t^4+\frac{376}{81}t^5
  +\frac{2227}{48}t^6+O(t^7).
\]

The (u^{3/2}) coefficient is zero and the (u^{5/2}) coefficient is
(376/81).  Certificate SHA-256:
`7858bb75adf8f7199b894d35a41b2a9211330a40cc534aee3acbe7aefbdc3210`.

This kills the finite/infinity route-exhaustion premise used by the current
two-flow compiler.  It does not establish a global factorization of the
critical holonomy.  The sharpened Jacobian residual has two branches:

1. construct the selected nonfinite cross carrier and apply the ratified
   local exclusion; or
2. show that a finite equilibrium chain is incompatible with the global
   time-one normalization or with the arithmetic of (F(-2)).

## Finite Julia valuation classification

### Eigenquestion

Does the Julia identity itself force a finite selected branch to preserve
the regular/equilibrium status of its two centers?

### Candidate theorem

Let the source and endpoint displacements have positive analytic orders
(r,q), and let a nonzero polynomial generator have root multiplicities
(m,n) at the source and endpoint centers.  From

\[
A_t p(x)=x_t p(A)
\]

the derivative-order kernel and finite polynomial-substitution kernel should
give

\[
(q-1)+rm=(r-1)+qn,
\qquad
q(1-n)=r(1-m).
\]

Positivity then excludes the two mixed cases:

\[
m=0<n,
\qquad
n=0<m.
\]

Consequently (m=0\iff n=0).  In the regular-regular case the same balance
forces (q=r); otherwise both centers are equilibria.  No route label or
factorization exhaustiveness is an input.

### Counterattacks and kill conditions

- Derive both polynomial-evaluation orders from root multiplicity; do not
  carry the balance equation in the carrier.
- Derive the orders of both derivatives from positive analytic order.
- Use eventual equality on the Julia row and additivity of meromorphic order.
- Keep multiplicities arbitrary.  A theorem restricted to simple roots does
  not classify the selected finite route.
- This theorem classifies finite local endpoints.  It does not exclude the
  equilibrium-equilibrium branch or construct a global selected branch.

### Intended formal surface

1. `FiniteJuliaCarrier` containing analytic branch data and the Julia row.
2. A derived integer valuation-balance theorem.
3. A derived regular-status equivalence and equal-order regular case.
4. An aggregated terminal certificate exposing the full classification.

The semantic primitive retriever was unavailable; lexical fallback surfaced
the current two-flow compiler, while the proof reuses
`FormalMeromorphicPoleDerivative` and
`FormalPolynomialMeromorphicOrder`.  Scratch forecast
`PL-SCRATCH-f136c283837d` assigns probability (0.84) to the focused theorem
and governed ratification succeeding.

### Ratified finite-route outcome

`FormalFiniteJuliaValuationClassification.finite_julia_valuation_classification_terminal_certificate`
passes the focused build and governed ratification.  The carrier contains
the two analytic displacements, their positive exact orders, and the Julia
row.  It contains no root-status flag, valuation balance, or route label.
The theorem derives

\[
q(1-n)=r(1-m)
\]

and the exhaustive classification

\[
(m=n=0\ \text{and}\ q=r)
\quad\text{or}\quad
(m>0\ \text{and}\ n>0).
\]

Governed closure-record SHA-256:
`87e0e5f86155504ff835a62cb66dba4b93bce8dda8535a8c60f1facbc2f24e3c`;
source SHA-256:
`81e1ab32559e701a44a36866c14460ff8cde55592630862a402008bee8122fce`;
recompilable-probe SHA-256:
`6c9e36bd4c79ed041813b60fa6b2c304e4578fca1bcdd51ce9a503aad2ef9b8f`;
kernel-parity SHA-256:
`32447da15467bd43ee7010841f447fb9cdf3ef43d620008f0a7e656af817282c`.

This removes mixed finite endpoints from the global route theorem.  A
nonanalytic finite selected factor must enter equilibrium at both ends; the
equilibrium-transition collision is therefore the complete finite local
residual, rather than one example among unclassified finite branches.

## Infinite monodromy versus finite equilibrium sets

### Eigenquestion

Can the global analytic continuation of the critical holonomy force one
branch of every two-flow factorization into the already excluded nonfinite
carrier, even though a single finite equilibrium chain matches the local
(5/2) signature?

### Orientation calculation

The quadratic sheet

\[
w^2=36+12x-3x^2
\]

is rationalized by

\[
x=\frac{6(t^2-1)}{t^2+3},
\qquad
w=\frac{24t}{t^2+3}.
\]

The normalized path from (x=0) to the critical point (x=-2) is (t=1)
to (t=0).  Substitution turns (d\log F) into a rational differential.
An exploratory exact partial fraction calculation exposed a squarefree
degree-seven pole factor

\[
Q(t)=199t^7-1393t^6+67t^5+219t^4+5973t^3
     +10125t^2+10593t+2889.
\]

The residues at its roots are algebraic roots of an explicitly computable
degree-seven resultant polynomial.  Irreducibility and the monodromy
consequence have not yet been used as evidence.

### Preregistered discriminating test

1. derive the exact rational differential directly from the algebraic
   connection and verify the conic substitution;
2. prove (Q) squarefree and irreducible over (\mathbb Q);
3. eliminate a root of (Q) from the residue formula and prove that the
   resulting residue polynomial is irreducible of degree seven;
4. verify that the corresponding pole is separate from the normalization
   and branch endpoints.

If these checks pass, every such residue (\rho) is algebraic irrational.
Gelfond--Schneider then makes

\[
M=\exp(2\pi i\rho)=(-1)^{2\rho}
\]

transcendental and in particular not a root of unity.  Repeated continuation
around that pole gives infinitely many limiting endpoint values
(M^kF(-2)).

### Kill conditions and claim boundary

- **Success:** exact irreducibility certificates and a nonintegral algebraic
  residue produce an infinite-order scalar monodromy multiplier.
- **Kill:** all residues are rational, the exposed pole cancels from the
  logarithmic differential, or the residue polynomial has only rational
  roots.
- **Boundary:** the exact replay would prove infinite endpoint monodromy of
  the critical scalar holonomy.  Closing the Jacobian route still requires a
  continuation-transfer theorem: if all factor branches stay finite along
  the loop iterates, the ratified finite valuation classification forces the
  infinitely many endpoints into the finite root set of the outer
  generator; otherwise one iterate constructs the nonfinite cross carrier.

### Exact residue outcome and formal surface

The replay
[`gauge_critical_monodromy_residue.py`](../axiompack_jacobian_field_parametric_20260720/gauge_critical_monodromy_residue.py)
passes every preregistered check.  It derives

\[
d\log F=
\frac{896t(t-3)(t+1)(t^2-6t-3)}{(t-1)Q(t)}\,dt.
\]

The numerator, (t-1), and (Q) are pairwise coprime, and (Q) is squarefree.
Both (Q) and the exact residue resultant remain irreducible modulo (17),
with degree seven over (\mathbb Q).  Thus every residue over a root of (Q)
is algebraic irrational.  Certificate SHA-256:
`c27c46c0e1d4d83a93714ebe4fafe3dae4994320ceac592b2cfd273a5bce898d`.

The transcendence conclusion in the preregistration can be weakened to the
property actually needed.  If

\[
M=\exp(2\pi i\rho)
\]

and (M^N=1) for positive (N), the kernel of complex exponential gives
(N\rho\in\mathbb Z), hence (\rho\in\mathbb Q), a contradiction.  No
transcendence theorem is required to prove infinite order.

The intended formal surface is therefore substrate-neutral:

1. irrationality of (\rho) is represented by absence of a rational cast;
2. `Complex.exp_eq_one_iff` converts a positive torsion power into an
   integer period;
3. cancellation of (2\pi i) constructs the forbidden rational value;
4. the terminal theorem returns non-torsion of the monodromy multiplier.

The degree-seven modular irreducibility and resultant remain exact adapter
evidence.  The Lean theorem owns the universal exponential-period argument.

### Preregistered finite-root escape corollary

The no-torsion conclusion should immediately compile to the combinatorial
statement needed by the continuation route.  For nonzero (y) and nonzero
polynomial (p), define

\[
y_k=M^k y.
\]

No positive torsion power makes (k\mapsto M^k) injective; multiplication by
(y\ne0) preserves injectivity.  Its range is therefore infinite, while the
root set of (p) is finite.  Hence

\[
\exists k,\qquad p(M^k y)\ne0.
\]

The proof must use the polynomial root set, not a caller-supplied cardinality
bound.  It remains substrate-neutral and does not assert that the factor
continuation exists along every scalar loop.  A focused build fails the
route if Mathlib's finite-root and infinite-range surfaces cannot be joined
without adding an orbit-finiteness premise.

## Selected factor-monodromy lift

### Eigenquestion

Can equality of the initial two-flow germ with the critical scalar holonomy
be continued around the certified logarithmic pole so that every loop
iterate yields either finite Julia carriers for both factors or the existing
nonfinite cross carrier?

### Target global input

The Clay-equivalent analytic input in this lane is a maximal-continuation
theorem for the first-order Julia ODE

\[
A'(x)f(x)=f(A(x))
\]

and its outer counterpart.  Along a compact path avoiding the finite source
root set of (f), a selected solution can fail to continue only by leaving
every finite chart.  In that event the reciprocal infinity chart and its
polynomial degree balance must be constructed.  A named escape predicate or
a preselected finite/infinity tag is not an adequate replacement.

### Candidate theorem

Let (F=B\circ A) be the equality of analytic germs at the normalization
point, with (A) and (B) time-one germs of nonzero polynomial generators
(f,g\in x^2\mathbb Q[x]).  Let (\gamma_k) be the based path obtained by
looping (k) times around the certified irrational-residue pole and then
approaching the critical point.

For every (k), maximal continuation along (\gamma_k) should produce exactly
one of:

1. a finite hidden endpoint and finite total endpoint, together with the two
   finite Julia carriers and the continued factorization identity; or
2. a reciprocal hidden/outer chart giving a `TwoFlowRamifiedCrossCarrier`.

In the first case the critical total germ is nonanalytic, so the regular
finite descent theorem removes the regular branch and the finite valuation
classification forces an equilibrium transition.  Hence

\[
g(F_k(-2))=0.
\]

The monodromy orbit has the form

\[
F_k(-2)=M^kF_0(-2)
\]

with (M) of infinite order and (F_0(-2)\ne0).  The finite-root escape theorem
chooses (k) with (g(F_k(-2))\ne0), contradicting outcome 1.  Therefore that
iterate produces outcome 2, which the ratified local carrier sink excludes.

### Proof skeleton

1. deform the scalar loop away from the finitely many source roots of (f);
2. apply local analytic ODE existence successively along a finite path cover;
3. use maximality to convert any finite-chart failure into unboundedness;
4. compactify unboundedness by the reciprocal coordinate and reuse the
   polynomial ramified-trajectory sheet kernel;
5. continue the outer factor on the carried hidden path by the same argument;
6. transport both Julia rows and the composition identity by uniqueness on
   overlaps;
7. apply finite valuation classification or construct the nonfinite cross
   carrier;
8. use the infinite monodromy/finite-root contradiction to force the latter.

### Exact kill conditions

- A pathwise solution can have a finite nonextendable endpoint not captured
  by an equilibrium or reciprocal infinity chart.
- The factor germs have a natural boundary before the scalar loop despite
  the continued composition.
- The scalar multiplier changes the endpoint but the factorization equality
  cannot be transported to the corresponding branch.
- The reciprocal chart does not supply the existing cross carrier's
  meromorphic order or both Julia rows.
- Any proof assuming the finite/nonfinite alternative, loop lift, or route
  exhaustiveness as a field has not closed this theorem.

### Intended formal surface

The first implementation target is a path-local continuation gluing theorem
for polynomial Julia ODE solutions: local existence, overlap uniqueness, and
finite-cover gluing, with an explicit boundary statement that bounded endpoint
values extend.  Only after that theorem exists should the repeated-loop
carrier and final two-flow assembly be encoded.

## Preregistered logarithmic-loop continuation kernel

### Eigenquestion

Can a simple-pole logarithmic connection be converted into an explicit
repeated-loop solution and an infinite endpoint orbit, without carrying the
endpoint multiplier or the orbit as a premise?

### Candidate theorem

Let a circle avoid its center and let a scalar coefficient restrict to

\[
A(z)=\frac{\rho}{z-a}+h(z),
\]

where `h` has a primitive `H` along the circle.  For nonzero initial value
`y₀`, define the continuation along `N` turns by

\[
y_N(\theta)=y_0\exp\!\left(
  \rho i\theta+H(\gamma(\theta))-H(\gamma(0))
\right),\qquad 0\leq\theta\leq 2\pi N.
\]

The kernel must derive both the pulled-back ODE

\[
y_N'(\theta)=A(\gamma(\theta))\gamma'(\theta)y_N(\theta)
\]

and the endpoint formula

\[
y_N(2\pi N)=y_0\exp(2\pi i\rho)^N.
\]

If every positive power of the multiplier is nontrivial, the endpoint map
`N ↦ y_N(2πN)` must be injective.  The carrier may contain the pole
decomposition and primitive derivative; it may not contain the endpoint
formula, an orbit-injectivity callback, or any continuation conclusion.

### Discriminating test and kill conditions

Lean must check the circle derivative, the cancellation of the pole against
the circle tangent, the exponential chain rule, periodic return after every
natural number of turns, and the cancellation argument turning equal
endpoints into a positive torsion power.  The route is killed by any theorem
that omits the pulled-back ODE, assumes the multiplier action on endpoints,
or packages injectivity as input.

Passing this test supplies a general continuation kernel but does not by
itself discharge the critical coverage node.  The adapter must still
construct the regular remainder and its primitive from the exact critical
rational differential, then bind the resulting loop solutions to the
selected two-flow factorization.

## Preregistered analytic simple-root lift kernel

### Eigenquestion

Can a simple zero of a one-parameter analytic equation be lifted to a
locally analytic root germ by construction, so selected-factor continuation
is automatic away from the discriminant rather than a caller-supplied
branch?

### Candidate theorem

Let `equation : ℂ × ℂ → ℂ` be analytic at `(base, root)`, with

```text
equation (base, root) = 0
```

and invertible vertical Fréchet derivative. Mathlib's complex implicit
function theorem should construct `branch : ℂ → ℂ` satisfying

```text
AnalyticAt ℂ branch base,
branch base = root,
equation (t, branch t) = 0  eventually at base.
```

The terminal signature may carry the analytic equation, its zero, and a
proof that the vertical derivative is an equivalence. It may not carry a
root branch, a local solution callback, or the eventual root identity. The
polynomial specialization will use the derivative of evaluation at a simple
root; the invariant-owning kernel is the analytic implicit-zero constructor.

### Discriminating test and kill conditions

The focused Lean proof must instantiate `ContDiffAt.implicitFunction` at
smoothness `ω`, recover analyticity from complex `C^ω`, prove the anchor
value, and derive the eventual zero equation from the constructed implicit
function. The route is killed if the output equation is assumed, if only
continuity/differentiability is returned, or if invertibility of the
vertical derivative is silently replaced by the desired root germ.

The matched negative control removes vertical invertibility. The equation
`y^2-t=0` at `(0,0)` then has no single-valued analytic square-root germ, so
the general theorem must retain the simple-root boundary.

### Exact claim boundary

Success constructs local continuation charts on the simple-root locus. It
does not prove that a chosen root survives a complete loop, avoid or resolve
discriminant collisions, choose a projective root at leading-coefficient
degeneration, or produce a finite continuation chain. Those are the next
global and ramified obligations. Scratch forecast
`PL-SCRATCH-286a9ee1ec97` assigns probability `0.72` to focused compilation
and governed ratification at this boundary.

### Outcome: recurrence found before formalization

The complete campaign-log audit found that v40--v56 already constructed a
strictly stronger continuation/prolongation stack, while v93 later removed
the continuation requirement at the original normalization germ.  The
simple-root lift would duplicate an existing route and would not touch the
current zero-face realization seam.  No Lean module was added for this
preregistration.  The scratch forecast resolves failure on its declared
novelty/usefulness test, with prior-art recurrence as the reason.

## 2026-08-06 continuation-frontier audit

The later campaign record sharpens the boundary above in two ways.

First,
`FormalComplexMonodromyFiniteRootEscape.complex_monodromy_finite_root_escape_terminal_certificate`
has passed governed ratification.  Its closure-record SHA-256 is
`5360a484d3fdf1960e9c36bd38957c4478ab689779edd855cdf536a3441a24b9`,
its recompilable closure source is
`6a8d50b467f3c569efe8c5a15bc31099aee27c60b77ea3e49958cd23964f9f73`,
and its kernel-parity record is
`ff266df8bc81a45f6e040ce5d876d0449ff1d288a9222e13ac1e5ec64e616ce9`.
This governs escape from the roots of a fixed polynomial once the scalar
orbit is supplied.

Second, the exact cubic and Lambert-W stress models show that finite
continuation of a polynomial time-one correspondence need not land in a
fixed equilibrium set.  The finite-root theorem therefore cannot be used
through the discarded implication `finite continuation -> equilibrium`.
The active finite relation is instead the governed division-free identity

\[
q(F)p(G)=A F p(x)q(G).
\]

The continuation carrier must retain the two Julia rows that imply this
identity.  Exclusion of its complete finite algebraic-monodromy branch is a
separate theorem.

## Preregistered finite-state holomorphic continuation kernel

### Eigenquestion

Does a finite endpoint of the pulled-back polynomial factor equation admit
a holomorphic continuation germ automatically, including when the endpoint
is an equilibrium?

### Candidate theorem

For a complex polynomial `p`, a coefficient germ `c` analytic at `z0`, and
an arbitrary finite state `y0`, construct an analytic germ `y` satisfying

\[
y(z_0)=y_0,\qquad y'(z)=c(z)p(y(z)).
\]

If `p(y0) != 0`, construct the solution by composing a normalized primitive
of `c` with the analytic inverse of the finite Abel coordinate
`T'(y)=1/p(y)`.  If `p(y0)=0`, construct the constant equilibrium germ.
Two analytic solution germs with the same value at `z0` must agree near
`z0`: the regular case uses the Abel coordinate, while the equilibrium case
factors `p(y)=(y-y0)q(y)` and invokes scalar linear-ODE uniqueness.

### Discriminating test and kill conditions

Lean must construct both branches and prove the differential equation and
overlap uniqueness.  The theorem may not accept a local solution, an inverse
Abel map, a Lipschitz callback, or a regular/equilibrium route tag as input.
Failure to prove uniqueness at an equilibrium, or a construction that is
only continuously differentiable rather than complex analytic, kills this
surface.

Passing the test removes finite nonextendability as a local obstruction and
supplies the gluing law for a finite path cover.  It does not construct a
maximal continuation, preclude infinitely many finite sheets, cross an
infinity event, or establish the selected factorization continuation
carrier.

## Preregistered differential-resultant prolongation kernel

### Eigenquestion

Can the static coupled-Julia root relation be differentiated without
division so that every finite lifted factor branch is forced into a common-
root resultant, leaving only invariant algebraic components as exceptions?

### Governing identity

In the source coordinate `x`, write the finite hidden and visible branches
as `G(x)` and `F(x)`, the polynomial generators as `p,q`, and the visible
logarithmic coefficient as `A(x)`.  The three equations are

\[
p(G)=G'p(x),\qquad q(F)G'=F'q(G),\qquad F'=AF.
\]

The governed zero-th relation is

\[
R(Y)=q(F)p(Y)-AFp(x)q(Y).
\]

Differentiating `R(G)=0`, substituting the three equations, and multiplying
by `p(x)` gives the division-free first prolongation

\[
\begin{aligned}
S(Y)={}&AFp(x)q'(F)p(Y)+q(F)p'(Y)p(Y)\\
&-A'F p(x)^2q(Y)-A^2F p(x)^2q(Y)\\
&-AFp(x)p'(x)q(Y)-AFp(x)q'(Y)p(Y).
\end{aligned}
\]

Every finite analytic lift must satisfy `R(G)=S(G)=0`.  Therefore its
visible endpoint annihilates

\[
\operatorname{Res}_Y(R,S).
\]

### Discriminating test and kill conditions

The first Lean kernel must construct `S` and derive `S(G)=0` from analytic
germs carrying only the three displayed differential equations.  It may not
accept `R(G)=0`, its derivative, `S(G)=0`, or a common-root witness as an
input.  Polynomial chain rules and the derivative of `A` must be checked by
the kernel.

The successor adapter must compute the resultant as a polynomial in `F` at
the certified loop basepoint.  A nonzero resultant reduces the complete
finite branch to the governed scalar-orbit finite-root escape theorem.  If
the resultant vanishes identically, the route does not fail: its common
factor is an invariant algebraic curve and must be classified.  Proportional
flows are one expected exception, but no claim of exhaustiveness is made in
advance.

Passing the first-prolongation test supplies a reusable differential-
elimination kernel.  It does not prove that one prolongation always has
nonzero resultant, construct the loop lift, or classify every invariant
factor.

### Kernel outcomes

Both successor kernels passed focused compilation and governed ratification.

- `FormalAnalyticPolynomialControlledTrajectory` constructs a local analytic
  solution at every finite state and proves overlap uniqueness.  Its governed
  closure-record SHA-256 is
  `f42f0fb155a84be0eb978de3db8a564de7b8927158fc6407f0685aa2e2375faf`,
  its recompilable closure source is
  `57b4f34daf49eaec2f454b38c4e296ccf7afe50dc30877b6d7cd58bb36d15a10`,
  and its kernel-parity record is
  `c7e921bdffcaacfc772487d445bf7c94ebdaff48db6475567bd0a6dffd3dbf9e`.
- `FormalCoupledJuliaDifferentialProlongation` derives the zero-th coupled
  relation and its first division-free prolongation from analytic germs
  carrying only the two Julia rows and the visible logarithmic equation.  Its
  governed closure-record SHA-256 is
  `b4ea295e602ace391568b57fcae9ddda7527f64d84efb48153ae54e03e77c6d7`,
  its recompilable closure source is
  `10d6bd48dc3bf0929bf2b23e061c27c9f30123baa2d73649dad083a1fde15e3c`,
  and its kernel-parity record is
  `7390005969467ab849af43264df4ee279f91f4a1e153ca72dc5e365716eda747`.

These outcomes remove local finite-endpoint failure and the first
differentiation step from the residual.  They do not exclude finite
monodromy or construct the selected global lift.

## Preregistered saturated low-degree resultant discriminator

### Eigenquestion

After removing the universal tangent-equilibrium factor, is the first
differential resultant already nonzero for the first nonproportional
polynomial pairs?

### Discriminating test

Write

\[
p(Y)=Y^2P(Y),\qquad q(Y)=Y^2Q(Y),
\]

and, on a selected nonzero hidden branch, use the saturated relation

\[
\bar R(Y)=q(F)P(Y)-AFp(x)Q(Y).
\]

Recompute its first prolongation from the differential equations rather than
dividing the unsaturated prolongation mechanically.  Compute and factor
`Res_Y(Rbar,Sbar)` exactly for

\[
(P,Q)=(1,1+bY)
\]

and

\[
(P,Q)=(1+cY,1+dY).
\]

Success requires a nonzero symbolic resultant under explicit source-regular,
nonzero-coefficient, and nonproportionality hypotheses.  An identically zero
resultant after saturation, or a factorization whose claimed nonzero factor
can vanish under the declared hypotheses, kills the first-prolongation route.

### Claim boundary

This test covers degrees two and three only.  It cannot support an all-degree
statement.  Its job is to discriminate whether saturation exposes a viable
induction invariant or whether even the first nonproportional pairs retain an
unclassified common factor.

## Preregistered vector-field multiplicity-peeling kernel

### Eigenquestion

Does the derivation

\[
D_p(Q)=pQ'
\]

lower the multiplicity of a root `y` by exactly one whenever `p(y) != 0`, so
that a finite prolongation tower must escape every nonzero polynomial factor
away from the equilibrium locus of `p`?

### Candidate theorem

For complex polynomials `p,Q`, a point `y`, and
`m = rootMultiplicity y Q`, assume `Q != 0` and `p.eval y != 0`.  For every
`n <= m`, prove

\[
(D_p^{,n}Q)\ne0,
\qquad
\operatorname{rootMultiplicity}_y(D_p^{,n}Q)=m-n.
\]

Consequently `D_p^n Q` vanishes at `y` for `n<m`, while
`D_p^m Q` does not.  A stronger exact-value refinement may derive

\[
(D_p^mQ)(y)=p(y)^m m!\,
  \left(Q/(Y-y)^m\right)(y),
\]

but the nonvanishing terminal is the required kernel surface.

### Proof skeleton and kill conditions

Induct on `n`.  At each live root, characteristic zero gives the exact
one-step derivative multiplicity drop; multiplication by `p` adds zero root
multiplicity because `p(y) != 0`.  Nonzeroness must be proved at every step,
including the last derivative where the new multiplicity is zero.  The proof
fails if it assumes the iterated polynomial is nonzero, accepts the terminal
nonvanishing as input, or handles only simple roots.

### Intended consequence

The theorem is substrate-neutral and is the algebraic core of saturated
differential elimination.  It still leaves one separate Jacobian task:
connect the actual coupled relation's full prolongation tower to this
fiberwise operator and classify any component trapped in `p(Y)=0`.

### Low-degree and multiplicity outcomes

The exact replay
`gauge_coupled_julia_differential_resultant.py` passes with certificate
`9fef9c63a9e75f1ec58af7e33551761a49078f34ba413c001b1b4a5524ea06e6`.
The quadratic--cubic saturated resultant has endpoint degree seven and a
terminal factor with constant coefficient `-A^2 X^4`.  The cubic--cubic
resultant has endpoint degree ten; its highest endpoint-degree factor has
constant coefficient `-A^3 X^4 (1+Xc)`.  Hence both resultants are nonzero
under the preregistered regularity and nonproportionality conditions.

`FormalPolynomialVectorFieldMultiplicity` then proves the all-multiplicity
law over every characteristic-zero field and passed governed ratification.
Its closure-record SHA-256 is
`e17e20a66f02bcebdcd2eb69f3caf15511099ee6a932e8e52c06cf0f3958d125`,
its recompilable closure source is
`79829f4509d6a53de9bff7abe1ad795f4eea1bbe6b99ef305d40354537b6096d`,
and its kernel-parity record is
`c1007a82d7c3f5199128a4b07bfec5bf712688ee675bfc6af6e6914330e70b9e`.

The umbrella import remains blocked by the pre-existing absent object file
for `ZtareProofs.ns_tick669_projection_tail_persistence_bridge`; the focused
new module compiles and its isolated governed replay passed.

## Preregistered commuting-prolongation triangular bridge

### Eigenquestion

Does restriction of the total coupled prolongation to the invariant visible
divisor `F=0` expose the vector-field multiplicity operator as its leading
triangular term at every order?

### Structural identity

After dividing the zero-th coupled relation by the visible factor `F`, its
restriction to `F=0` is

\[
H_0(Y)=-a_0q(Y),\qquad a_0=A(x)p(x).
\]

The source and hidden parts of the total prolongation commute on this
divisor.  If `delta` denotes the source derivation and `D_p=p(Y)d/dY`, then

\[
(\delta+D_p)^n(a_0q)
=\sum_{j=0}^n {n\choose j}a_{n-j}D_p^jq,
\qquad a_k=\delta^ka_0.
\]

At a root `y` of multiplicity `m` with `p(y) != 0`, every term with `j<m`
vanishes, while the `j=m` term is `a_0 D_p^m q(y)`.  Thus it is nonzero when
`a_0 != 0`, independently of all higher source jets.

### Candidate formal surface and kill conditions

Define the binomial triangular prolongation over a characteristic-zero field
from `p,q`, an arbitrary scalar jet sequence, and `n`.  Prove that its
`m`-th member evaluates nonzero at a root of `q` of multiplicity `m`, assuming
only `q != 0`, `p(y) != 0`, and `jet 0 != 0`.  The theorem may not constrain
the higher jets or assume the lower vector-field iterates vanish.

The route fails if noncommuting terms survive after specialization, the top
coefficient depends on a higher jet, or the formal theorem needs a bound on
root multiplicity.  Passing it still requires a separate adapter theorem
identifying the actual normalized coupled prolongations with this triangular
family and an elimination step saturated away from `p(Y)=0`.

### Triangular-kernel outcome and finite successor

The triangular terminal passed governed ratification.  Its closure-record
SHA-256 is
`49ec02a1439d2681231c6db5770ab0f7f78ecbcfea3c286544d4aa0de11f526c`,
its recompilable closure source is
`7a3504f5ccdd6f6ac3cf952ed9dc3e8ae5fc848aa6185769d56b376ad92ed1c7`,
and its kernel-parity record is
`d8f68629c669c1d4bdfe41b46944466c9373a8c4f70fd707d01c1710932298ea`.

The next finite certificate is preregistered as follows.  Over an
algebraically closed characteristic-zero field, for every root `y` of a
nonzero `q` with `p(y) != 0`, construct

\[
n=\operatorname{rootMultiplicity}_y(q)\leq\deg q
\]

and prove that the `n`-th triangular prolongation is nonzero at `y`.  Thus no
point outside `p(Y)=0` can be a common root of the finite family indexed by
`0,...,deg q`.  The theorem may not accept the witness index or its
nonvanishing as input.  It does not yet construct an endpoint resultant; it
supplies the finite common-root exclusion from which that elimination step
must be derived.

This finite escape terminal passed governed ratification.  Its closure-record
SHA-256 is
`9089ac550986408cc211cf0e842673975df09f71be7e260363e7fbdc124c7be4`,
its recompilable closure source is
`d372999f4dc8a5cc074f255a97b1c5550f4d06cd6a6bcddba2c1c7e51bd64870`,
and its kernel-parity record is
`8c144e3632c486b9479c1db29fb37a3f1dd5bcfd18dddc8c1bb1bbff4653c372`.
The result is stronger than preregistered in one direction: algebraic closure
is unnecessary because the candidate common root is already supplied.

## Preregistered invariant-divisor total-derivation specialization kernel

### Eigenquestion

Can a polynomial total derivation be constructed from a coefficient
derivation and a polynomial velocity so that specialization along an
invariant divisor commutes with every iterate, without supplying the desired
specialized recurrence?

### Candidate formal surface

For a commutative ring `R`, a derivation `d : R -> R`, and a velocity
`v in R[X]`, construct the total polynomial derivation

\[
\widehat d_v(P)=d_{\rm coeff}(P)+vP'.
\]

For a ring homomorphism `phi : R -> S`, coefficient derivations `d_R,d_S`,
and velocities `v_R,v_S`, prove that `Polynomial.map phi` intertwines the
two total derivations whenever `phi` intertwines the coefficient derivations
and maps `v_R` to `v_S`. Deduce the corresponding equality for every natural
iterate.

The Jacobian consumer takes `R=A[F]`, specializes `F` to zero, and chooses a
visible velocity divisible by `F`. The theorem must then derive, rather than
assume, that the hidden total derivation specializes to the coefficient-plus-
`D_p` derivation on `A[Y]` at every order.

### Kill conditions

A theorem that accepts iterate compatibility, accepts the specialized tower,
checks only the first derivative, or relies on a caller-provided triangular
identity fails. The generic theorem must expose its action on constants and
the polynomial variable and must work over commutative rings. Passing this
kernel does not yet prove that the concrete coupled relation has the claimed
normalization or classify a dominant invariant component.

### Outcome

`FormalDifferentialPolynomialInvariantSpecialization` constructs the total
derivation over every commutative ring, proves its action on constants and the
polynomial variable, proves functorial compatibility under coefficient maps,
and derives compatibility of every natural iterate.  Its nested-polynomial
terminal specializes the visible variable at zero from the single derived
condition that the visible velocity vanishes there.

The terminal passed governed ratification.  Its closure-record SHA-256 is
`ac5df55300c07830f6fe1695cb3cb2bd178e9c104d05c27596efeebd8f2c69b4`,
its recompilable closure source is
`6ae7723b4d88a6cdbaaaf919d3dae8d0b7a579f9a9785d361e957d61155a855f`,
and its kernel-parity record is
`acee04551c6b44a2a8ece9393c2ea5574cfa0dda5127bc87abe01e76a0703a49`.
The content-bound coverage receipt is
`c87bc1088d9a7820c05c1c631ff472e289fda2989850f6a14fb604ee933dc4fc`.

The remaining Jacobian adapter is deliberately narrower: construct the
actual normalized tangent coupled-Julia relation, prove that its visible
velocity preserves `F=0`, identify its zeroth specialization as
`-A(x)p(x) q(Y)` with nonzero scalar coefficient, and then connect its
specialized iterates to the governed triangular family.

## Preregistered iterated-Leibniz and concrete normalization bridge

### Eigenquestion

Can the remaining exact iterated-Leibniz step and the concrete divided
coupled-Julia normalization be derived from their governing identities, so
that no caller-provided triangular recurrence remains between the actual
prolongation tower and the finite-escape kernel?

### General-purpose theorem

For every derivation `D` of a commutative ring, prove the complete binomial
Leibniz formula

\[
D^n(ab)=\sum_{i+j=n}\binom ni D^i(a)D^j(b).
\]

The proof must induct from the Leibniz law and Pascal's identity. It may not
assume the iterated product formula, restrict to ordinary polynomial
derivatives, or check a finite order. A range-indexed corollary must expose
the orientation used by `triangularProlongation`.

### Concrete nested-polynomial theorem

Let the outer tangent generator be written `q(F)=F^2 qTail(F)`. Define the
actual hidden relation

\[
R(F,Y)=q(F)p(Y)-F a_0q(Y)
\]

and its divided normalization

\[
\bar R(F,Y)=FqTail(F)p(Y)-a_0q(Y).
\]

Lean must derive `R=F*Rbar`, the visible-velocity divisibility for
`F'=bF`, and

\[
\bar R(0,Y)=-a_0q(Y).
\]

It must then combine the governed invariant-specialization theorem with the
new iterated-Leibniz theorem. Under explicit coefficient-constancy premises
for `p` and `q`, every specialized iterate must equal the exact triangular
family with jet `D^k(-a_0)`. The actual relation, base specialization, and
iterate formula may not be supplied as hypotheses.

### Kill conditions and claim boundary

Failure of `R=F*Rbar`, a visible velocity not preserving `F=0`, an extra
surviving term at specialization, reversal of the binomial jet indices, or a
constancy hypothesis strong enough to assume the specialized tower kills the
route. Passing this bridge pays actual algebraic specialization only. It does
not prove saturation produces an endpoint eliminant, classify a dominant
component, or construct continuation of a selected factorization around the
critical loop.

### Outcome

Both terminals pass governed ratification. The substrate-neutral
`FormalDerivationIteratedLeibniz` theorem derives the antidiagonal and
range-indexed binomial product laws for every derivation of a commutative
ring. Its governed record is
`b8942ecd8796511053655f85b068a5ab8394e3350630e5008d2d637f1f16cdbc`,
kernel-parity record is
`e2cc754610595297d71ed9a2b313d412db85cce98bd83f657befaf079229c8e2`,
and content-bound receipt is
`407a5a98863a3f98771b69758ed130e7dd9290209cddc5298073b226602583b2`.

`FormalCoupledJuliaAllOrderSpecialization` is stronger than the first
candidate in one respect: it constructs `qTail` from the two tangent
coefficient vanishings rather than accepting `q=X^2 qTail`. It then proves
the exact relation binding, visible factorization, special fiber, invariant
visible velocity, coefficient-constancy induction, and every triangular
prolongation. Its governed record is
`455ad189d87c9b11c1b6b2203557d7d82afca44b7757134d0eae6a40ccbefa0b`,
kernel-parity record is
`a1c70be8cd61dedc73bd62e00cbb16171868c52775fee575e5b989f9a885e8c0`,
and content-bound receipt is
`9990d58da6603873f424a06afee542ad8f2635fb4c73f84cca3229dd3727da06`.
Both matched conclusion perturbations pass and both axiom sets are confined
to `Classical.choice`, `Quot.sound`, and `propext`.

The remaining adapter premise is finite and explicit: embed the selected
critical source data in the differential coefficient field and discharge the
two tangent coefficients, the source-scalar binding and nonvanishing, and
coefficient constancy of the two polynomial generators. No all-order
recurrence remains in that semantic leaf.

## Preregistered analytic Kummer-lift classification

### Eigenquestion

Once normalization of a dominant component gives a local parameter `t` with
visible coordinate `F = unit * t^e`, does a lifted scalar monodromy necessarily
act by a single Kummer multiplier `t -> mu*t`, or can a nonlinear analytic
germ preserve the same `e`-th-power scaling?

### General-purpose theorem

Let `lifted : C -> C` be analytic at zero, fix zero, and have nonzero
derivative. For `e > 0` and `lambda != 0`, assume only the germ identity

\[
  \operatorname{lifted}(t)^e=\lambda t^e.
\]

Lean must construct `mu`, prove `mu != 0`, `mu^e = lambda`, and prove the
germ equality `lifted(t)=mu*t`. The proof should first derive analytic order
one, factor `lifted(t)=t*h(t)` with an analytic nonvanishing unit, cancel on
the punctured germ, extend the power identity across zero, and prove that an
analytic unit with locally constant positive power is itself locally
constant. The last step must be obtained from the difference-of-powers
factor and continuity, not by assuming a selected root or local constancy.

### Kill conditions

A theorem that assumes `lifted(t)=mu*t`, accepts `mu`, omits `mu^e=lambda`,
uses only a finite jet, or ignores the punctured-to-full-germ extension fails.
The zero-derivative case is outside this kernel because it is not a local
automorphism of the normalized component.

### Claim boundary and intended consumer

Passing proves the local Kummer classification after a finite normalization
and a lifted monodromy germ have been constructed. It does not normalize an
algebraic component, construct the lifted action, show finite covering over
the visible punctured line, or route the normalized boundary point to an
equilibrium, infinity, or proportional carrier. Those remain the
dominant-component adapter and global continuation obligations.

### Outcome

`FormalAnalyticKummerLift` passes focused compilation and governed
ratification. It derives analytic order one, constructs the analytic unit
quotient, performs cancellation only on the punctured germ, extends the
power identity over the center, and proves root rigidity with the
geometric-sum factor. Its governed record is
`b2c0303e108228cdabb399f493680c942e5309fec8b68dc0ff3d08ef380c1a53`,
recompilable closure source is
`e1b7bdc6f2d5d743e483f56cdafa94372c9247d61bdd0fa8e998efc22723ae83`,
kernel-parity record is
`d2b34c49d719d6ef6f9131dba952363ae75f11c929a68a568b68b2a0afb5f712`,
and content-bound receipt is
`28a3c3f934810f093e2fc0fbbd8231095e23e40d56919ba43ad3354dc4f04552`.
The matched negated-conclusion control passes. The terminal's axiom set is
`Classical.choice`, `Quot.sound`, and `propext`.

Coverage v44 uses the theorem as a governed child of dominant-component
routing. The remaining carrier leaf must construct normalization, the lifted
power-equivariant automorphism, and boundary overlaps; it cannot assume the
Kummer multiplier.

## Preregistered separated-polynomial branch valuation

### Eigenquestion

For a normalized branch of the actual divided coupled-Julia relation

\[
F(t)u(t)p(Y(t))=a_0q(Y(t)),
\]

does meromorphic order alone force the exact finite-equilibrium and infinity
ramification balances, or can a dominant branch evade the three route
classes after normalization?

### General-purpose theorem

Construct two carrier types and derive their balances rather than storing
them.

For a finite branch `Y(t)=beta+z(t)`, assume `F` and `z` are analytic of
positive exact orders `e` and `r`, `u(0) != 0`, `a0 != 0`, both polynomials
are nonzero, and the separated relation holds on the punctured germ. Prove

\[
e=r\bigl(m_q(\beta)-m_p(\beta)\bigr),
\]

then derive `m_p(beta) < m_q(beta)` and hence that `beta` is a root of `q`.

For a pole branch of exact order `-r` with an analytic reciprocal extension,
prove

\[
e=r\bigl(\deg p-\deg q\bigr),
\]

then derive `deg q < deg p`. The theorem must use the existing exact
polynomial-substitution order kernel at finite centers and poles; it may not
assume either balance or replace the polynomial evaluations by precomputed
orders.

### Kill conditions and counterattacks

A carrier field containing the desired balance, a missing nonzero-unit
condition, an uncancelled zero polynomial, an integer sign reversal at the
pole, or a conclusion that omits strict multiplicity/degree inequality kills
the theorem. Countermodels with `e=0`, `a0=0`, or a vanishing analytic unit
must remain outside the theorem and demonstrate why those hypotheses are
needed.

### Claim boundary and primitive audit

Passing classifies the boundary of a supplied normalized meromorphic branch
of the separated relation. It does not construct the branch, finite
normalization, lifted monodromy, or overlaps with the selected global
factorization. The capability-amnesia search was lexical-only because the
semantic embedder was unavailable. It surfaced the filtered obstruction
compiler and the existing two-flow Puiseux compiler; neither owns analytic
meromorphic-order transport, so the intended implementation reuses the
governed polynomial-meromorphic-order kernel instead of adding a new
`src/ztare` primitive.

### First-pass counterattack and strengthened preregistration

The first carrier draft compiled but is rejected before ratification. Its
factorization `F*u` required `u(0) != 0`, which silently restricts the outer
generator to exact quadratic tangency. If the outer generator vanishes to
order greater than two, `qTail(0)=0`; that case must remain in an
unconditional classification.

The strengthened carrier therefore replaces `F*u` by one analytic
coefficient germ `c(t)` of arbitrary positive exact order `e`. The theorem
must still derive the same finite and pole balances with this total order.
It must also remove `a0 != 0` from the carrier: finite meromorphic order makes
both `c(t)` and `p(Y(t))` eventually nonzero on the punctured germ, so the
relation itself must prove `a0 != 0`. The pole case must derive the same fact
from the exact pole-substitution order. A terminal that retains a unit-tail
or nonzero-scalar premise fails this strengthened test.

### Strengthened outcome

`FormalSeparatedPolynomialBranchValuation` passes the strengthened test and
governed ratification. Both carrier types store only the analytic or
meromorphic data and the separated relation. Each route derives
`carrier.scalar != 0` before comparing exact orders. The finite theorem then
derives the multiplicity balance, strict multiplicity increase, and the root
condition at the finite center; the pole theorem derives the degree balance
and strict degree decrease.

The terminal's governed record is
`e95beaa9fd0fad531eff65148617cdd474cc79f385e8d08dda9273389dcd431a`,
recompilable closure source is
`c24d3a16744aba2153bf3d92cc9b4197267caac38c481e21fceeb350606502aa`,
kernel-parity record is
`7b2009b293eb040c03a6cc75964cda070fc5218d60b335d26b3ad8db6fea0161`,
and content-bound receipt is
`e5e299636988d347285de47fa53d50ad0b58669e4a7e7721109b5cc9a3ee67f7`.
The matched negated-conclusion control passes; the axiom set is confined to
`Classical.choice`, `Quot.sound`, and `propext`.

Coverage v45 uses this terminal as a governed child of dominant-component
routing. The remaining semantic work is carrier construction: finite
ramified normalization, lifted power equivariance, the finite-or-pole
meromorphic branch, the separated relation, and overlap with the originally
selected factor.

## Preregistered scalar-free all-order specialization

### Eigenquestion

Does the all-order normalized coupled-Julia specialization use the premise
`a0 != 0` anywhere, or was that regular-branch condition accidentally fused
into an algebraic theorem that also applies on the source-equilibrium locus?

### Candidate theorem and proof surface

Construct a new terminal, without modifying the already ratified source,
whose inputs are exactly the two tangent coefficient vanishings, the source
scalar binding

```text
coefficient * p(source) = a0,
```

and coefficient constancy of `p` and `q`. It must construct `qTail`, the
actual and normalized relations, their visible factorization and special
fiber, divisor invariance, and every triangular prolongation for arbitrary
`a0`, including `a0=0`. Its conclusion must not echo or derive scalar
nonvanishing.

The proof should reuse the already governed relation, derivation, and
specialization lemmas. No new analytical primitive is needed: capability
retrieval was lexical-only because the semantic embedder was unavailable,
and the surfaced filtered compilers do not own this theorem.

### Kill conditions and adversary

Any surviving `a0 != 0` premise or conclusion kills the candidate. A branch
split disguised as a typeclass or carrier field also kills it. The sharp
adversary is `a0=0`: the terminal statement must remain well typed and its
algebraic conclusions must follow without contradiction or division.

### Claim boundary and intended consumer

Passing removes scalar nonvanishing from the actual-normalized-relation leaf.
It does not instantiate the selected factorization in the differential
coefficient field, prove tangency or coefficient constancy for that
factorization, classify the zero-scalar source-equilibrium route, construct a
dominant component, or continue a selected factor around the critical loop.

### Outcome

The scalar-free terminal compiles and passes governed ratification. It reuses
the constructive helper lemmas directly and never invokes the older terminal,
so no nonzero premise is smuggled through a wrapper. Its full conclusion,
including every triangular prolongation, holds for arbitrary `a0`.

The governed record is
`1fd61139d56282c44089c43943960ba28990fe7c4ca626718d4bf17e92139b26`,
recompilable closure source is
`65604fab8860aae7aced4ecfcb5116033c87ec9bfa90d5329de0d9bea6a6ab43`,
kernel-parity record is
`b2936474b087d8b9dc57f3cd90c40b3496bbac5da6a70884fb1b01d3bf24cdab`,
and content-bound receipt is
`a31da2183e7d0dc6be267051697204e6ab36f943fb7f7f83f28d078a13a61d6b`.

Coverage v46 replaces the earlier inference terminal by this stronger one.
The actual-normalized-relation leaf now owes only the differential-field
embedding, the two tangent coefficient rows, coefficient constancy, and the
exact scalar binding. It no longer assumes scalar nonvanishing.

## Preregistered algebraic-branch boundary trichotomy

### Eigenquestion

Once a single-valued punctured analytic branch is known only as a root of a
degree-bounded analytic polynomial family, can the existing local-germ
kernels construct an exhaustive boundary carrier, or must meromorphicity and
the finite/pole order still be supplied by the caller?

### Governing identity and candidate terminal

The object is a selected analytic algebraic germ, owned by
`DegreeBoundedAnalyticRootCarrier`, together with a separated-family identity

```text
P_t(Y) = visible(t) * p(Y) - scalar * q(Y).
```

The terminal must derive exactly one of three local alternatives:

1. the selected branch is locally constant at a finite value `beta`, and the
   relation forces `p(beta)=0` or `q(beta)=0`;
2. it has a finite analytic extension with nonconstant displacement of a
   constructed positive natural order, producing a
   `FiniteSeparatedRelationCarrier` and the governed multiplicity balance;
3. it has a pole of a constructed positive natural order, with an analytic
   reciprocal chart, producing a `PoleSeparatedRelationCarrier` and the
   governed degree balance.

The terminal must preserve a punctured-germ equality from the selected input
branch to the constructed finite or pole carrier. It may consume the visible
germ's positive exact order, since that belongs to the normalized base
coordinate, but it may not consume hidden meromorphicity, a hidden order, a
finite extension, a reciprocal chart, or a boundary class.

### Proof skeleton

Use analytic coefficient selection and scaled-monic normalization to derive
meromorphicity of the selected branch. Split on finite analytic extension.
For a finite extension, split again on local constancy; otherwise subtract
its center value, use convergence to zero plus finite meromorphic order to
extract a positive integer order, and assemble the finite relation carrier.
For a nonremovable puncture, use the meromorphic infinity-chart theorem,
extract the negative integer order with `natAbs`, and assemble the pole
carrier. In both nonconstant cases apply the ratified separated-polynomial
valuation terminal rather than restating its balance.

### Counterattacks and kill conditions

The locally constant branch is the sharp adversary: silently assigning it a
positive displacement order kills exhaustiveness. A theorem that assumes
meromorphicity, stores either desired balance, loses germ overlap with the
selected branch, or treats `meromorphicOrderAt = top` as a pole also fails.
The coefficient-family identity must be used to derive the separated relation;
it may not be duplicated as a second unrelated hypothesis.

### Claim boundary and capability audit

Passing constructs the local finite/constant/pole carrier after a selected
single-valued analytic algebraic branch has been supplied. It does not prove
global normalization of an irreducible component, single-valued continuation
of a selected factor around the critical loop, lift scalar monodromy to the
normalization, or prove global overlap among loop iterates.

The semantic capability retriever was unavailable. Lexical retrieval surfaced
the filtered Puiseux compilers, while direct source inspection found the
reusable analytic-root selection, scaled-monic root, meromorphic infinity
chart, and separated-polynomial valuation kernels. No `src/ztare` primitive
is added. Scratch forecast `scratch_84ae8c4bc868995d` assigns probability
`0.72` to focused compilation, governed ratification, and v46 residual
narrowing under the stated stop rule.

### Outcome

`FormalAnalyticAlgebraicBranchBoundary` passes the discriminating test and
governed ratification. Its input carrier stores the visible exact order and
one degree-bounded analytic polynomial-root carrier with the exact separated
family identity. It stores no hidden meromorphicity, finite extension,
reciprocal chart, hidden order, or boundary class.

The proof derives the separated relation from polynomial root membership and
then constructs all three alternatives. In the constant case it derives a
root of `p` when the scalar is zero and a root of `q` when the scalar is
nonzero. In the nonconstant finite case it extracts a positive natural order
from the analytic extension and constructs a
`FiniteSeparatedRelationCarrier`. In the nonremovable case it extracts the
negative integer order, constructs the analytic reciprocal chart and a
`PoleSeparatedRelationCarrier`, and applies the governed valuation results.
Both nonconstant routes retain exact punctured-germ overlap with the selected
input branch.

The governed record is
`2dba25c7e49e10d69fd7079b255909a3b14949f1cd161c08032898e5354960d9`,
recompilable closure source is
`a35d6a6525b784b09b004f92773220252dabd37c283b1d53a431542a9d450639`,
kernel-parity record is
`3043417fdff95b2e5a81e7e0069cb3a69525651ea49eb162ab4f6bc0d2ef2f77`,
and content-bound receipt is
`e0972768c378472a259c30b7e8f0819df70802344dfba0e3fb17047e932479be`.

Coverage v47 now asks the dominant-component leaf to construct a finite
ramified normalization, its lifted power identity, a selected single-valued
punctured analytic algebraic root of the exact separated family, and overlap
with the original selected factor. Meromorphicity and boundary classification
are no longer semantic premises.

## Raw separated-branch assembly

### Eigenquestion

Once continuation supplies a selected punctured analytic branch and the raw
identity

\[
v(t)p(y(t))=a_0q(y(t)),
\]

does the branch itself construct the analytic algebraic-root normalization
consumed by the v47 boundary theorem, or must the caller separately certify a
degree bound and an active coefficient germ?

### Governing identity and candidate terminal

The input object owns only nonzero polynomials `p,q`, an analytic visible germ
of exact positive order, a scalar, a punctured differentiable selected branch,
and the displayed eventual relation.  Define

```text
P_t(Y) = C(visible(t))*p - C(scalar)*q
```

and prove internally that it is a degree-bounded analytic polynomial family,
that the selected branch is its root, and that at least one coefficient germ
is active.  The resulting `SeparatedAnalyticRootCarrier` should feed the v47
trichotomy without any supplied normalization datum.

### Proof skeleton

Use `max p.natDegree q.natDegree` as the degree bound and the standard
`natDegree_sub_le`/`natDegree_C_mul_le` estimates.  Analyticity of each
coefficient is immediate from analyticity of `visible`.  Root membership is
the raw separated relation.  For activity split on the scalar:

1. if the scalar is zero, choose the leading coefficient of nonzero `p`; the
   visible germ is eventually nonzero because its exact order is finite;
2. if the scalar is nonzero, positive visible order and analyticity force
   `visible(center)=0`, so the leading `q` coefficient of the family is
   nonzero at the center and hence cannot vanish as a punctured germ.

Reuse the existing degree-bounded root selector and v47 boundary theorem.
The nearby `FormalAnalyticCrossJuliaMeromorphic` implementation supplies the
general degree-bound pattern, but its determinant/nonvanishing activity
argument belongs to the unnormalized cross-Julia family and is not duplicated
as a second carrier.

### Counterattacks and kill conditions

- Reject an input that stores `DegreeBoundedAnalyticRootCarrier`, an active
  coefficient, meromorphicity, a boundary order, or a boundary class.
- The scalar-zero case must compile; silently requiring `scalar != 0` misses
  the source-equilibrium boundary.
- The scalar-nonzero activity proof must use the center value forced by
  positive order, rather than assuming one polynomial coefficient survives.
- The conclusion must preserve the exact original branch and relation, not a
  newly selected unrelated algebraic root.

### Claim boundary and prediction

Success proves that a supplied selected analytic branch is its own local
normalization carrier for the separated relation.  It does not construct the
branch, continue it around the critical loop, normalize a global irreducible
component, or lift monodromy.  Semantic capability retrieval was unavailable;
lexical retrieval plus direct source inspection found the reusable cross-Julia
degree-bound pattern and root-selection kernel.  Scratch forecast
`scratch_d732e433290a0b40` assigns probability `0.78` to focused compilation,
ratification, and coverage narrowing.

### Outcome

`FormalSeparatedAnalyticBranchAssembly` passes the discriminating test and
governed ratification. Its raw carrier contains only the selected branch,
visible positive-order germ, scalar, nonzero `p,q`, differentiability, and the
separated relation. It constructs coefficient analyticity, the uniform degree
bound, root membership, and coefficient activity. The scalar-zero route uses
the leading coefficient of `p`; the scalar-nonzero route first derives
`visible(center)=0` and uses the leading coefficient of `q`.

The constructed degree-bounded carrier feeds the v47 boundary theorem without
changing the selected branch. Governed record:
`c41ea283911e4d1c4dfe7e6abb8ebcd7cdd79e129ecb7ba626da94c1566d0757`;
recompilable closure source:
`604b10a725463e263ddece94b8a13bb3972dc749c0327a03a1bba24e9156eb1c`;
kernel-parity record:
`662f74a7a84338104eeb282f5dd89ae0cb49ee1ae87fd56f9cb0be455bc5046e`;
content-bound receipt:
`cfd0c2aa47ee55f71e52c2db9a82d964d9a9a387cd4286a84d2c959736b3e832`.

Scratch forecast `scratch_d732e433290a0b40` resolves success. Coverage v48
has 43 governed supports and 41 bottom-up-covered nodes. The dominant carrier
leaf now owes a selected punctured analytic branch satisfying the raw
separated relation; it no longer owes a degree-bounded polynomial family or
an active coefficient witness.

## Finite-endpoint controlled-polynomial continuation

### Eigenquestion

If a selected punctured holomorphic solution of

\[
y'(z)=c(z)p(y(z))
\]

has a finite limit at a missing endpoint, does it extend as an analytic ODE
solution through that endpoint, or can the differential equation be lost at
the filled point?

### Governing identity and candidate terminal

The input owns an analytic coefficient germ `c`, a punctured differentiable
branch, its controlled-polynomial ODE on the punctured neighborhood, and
`Tendsto branch (nhdsWithin center {center}ᶜ) (nhds state)`. The theorem must
construct an extension with:

1. exact punctured-germ overlap with the branch;
2. analyticity at the endpoint;
3. endpoint value exactly `state`; and
4. the same ODE on a full neighborhood, including the filled endpoint.

The extension, its analyticity, and its ODE may not be supplied.

### Proof skeleton

Update the branch at the center to the finite limit. The limit makes the
update continuous at the center, and punctured differentiability is unchanged,
so the removable-singularity theorem makes the update analytic. Differentiate
the punctured overlap to transfer the ODE to the constructed extension away
from the center. Both its analytic derivative and
`c(z)*p(extension(z))` are continuous at the center; the punctured equality
therefore upgrades to an equality on a full neighborhood. The local analytic
derivative witnesses the extended ODE.

### Counterattacks and kill conditions

- A theorem returning only `HasFiniteAnalyticExtension` fails: it must prove
  the differential equation after filling the endpoint.
- Reject a boundedness premise when the finite limit already supplies it.
- Reject an extension premise, a center-derivative premise, or loss of exact
  punctured overlap.
- The construction must work when `p(state)=0`; finite equilibrium endpoints
  are part of the intended continuation alternative.

### Claim boundary and prediction

Passing proves the finite-limit closedness step for controlled polynomial
continuation. It does not construct a maximal trajectory, prove that a finite
limit exists, exclude unbounded oscillation, or identify the reciprocal
infinity sheet. Semantic capability retrieval was unavailable. Source audit
selected `FormalAnalyticPuncturedExtension`, Mathlib's removable-singularity
and analytic-derivative lemmas, and the existing controlled-polynomial ODE
surface. Scratch forecast `scratch_74031138ae2f3f1a` assigns probability
`0.84` to focused compilation and governed ratification.

### Outcome

`FormalAnalyticFiniteEndpointODEContinuation` passes the discriminating test
and governed ratification. It constructs the center-updated extension from the
finite limit, proves analyticity by the removable-singularity theorem,
differentiates exact local overlap at every punctured point, and upgrades the
resulting derivative identity to a full neighborhood by continuity of both
analytic sides. The theorem accepts equilibrium endpoint states.

Governed record:
`59606a1a955c9c7de78db4abb65a374b4c485ca1984b199b18be661045fe67fa`;
recompilable closure source:
`9f267319c908cbc9d243d961b20e6bc7258f30d0c471a9142d692a2bb6d308d1`;
kernel-parity record:
`8f8831e7ad1882b9cfd797cc1ea255e943c3183eba7682befdb2b5b2bd933814`;
content-bound receipt:
`4a49afa18c8bd78e47cf080e3ffd8121bd3a1b44b851a97c156e5f2b4dffaff6`.

The global continuation residual is now isolated to construction of a maximal
selected path and the compactness alternative at its endpoint: a finite limit
extends by this theorem, so a failed finite-time continuation must avoid
having a finite limit and must be routed to the reciprocal infinity chart.

Coverage v49 records this split with 44 governed supports and 42 bottom-up-
covered nodes. The former selected-factor continuation leaf is now an internal
semantic inference over the governed finite-endpoint theorem and the narrower
`two_flow_selected_factorization_maximal_path_or_escape_carrier` leaf. The
decomposition, coverage, and envelope digests are
`f84f452c6f35927543db6aeaceb6a1319126e03f9c1624763c9b3827fa354555`,
`ebc80ffb8e3c84749b12ddc2119f062f1307a3f5c4409f3324a760384fa459bd`,
and
`489e9c13c9e95a93187fc2a0f11ff80d9ae6d7d6b97ed30de5b167d177da363f`.

## Bounded-derivative endpoint compactness

### Eigenquestion

Does a trajectory on a finite half-open interval with uniformly bounded
derivative necessarily have a finite endpoint limit in every complete real
normed space?

### Candidate theorem and governing identity

Let `a < T`, let `E` be a complete normed space over `Real`, and let
`trajectory : Real -> E` be differentiable at every point of `Ioo a T`.
Assume that one nonnegative constant `C` bounds the norm of its derivative on
that interval.  The terminal must construct

```text
exists state, Tendsto trajectory (nhdsLT T) (nhds state).
```

The input carrier may own `a`, `T`, `trajectory`, `C`, differentiability, and
the derivative bound.  It may not own a Cauchy property, an endpoint state, a
convergent subsequence, trajectory boundedness, or any endpoint limit.

### Proof skeleton

Mathlib's one-dimensional mean-value theorem turns the derivative bound into
`LipschitzOnWith C trajectory (Ioo a T)`.  The left-neighborhood filter at
`T` is Cauchy because it refines `nhds T`, and `Ioo a T` belongs to that
filter.  Uniform continuity of the Lipschitz restriction therefore sends the
left-neighborhood filter to a Cauchy filter in `E`.  Completeness of `E`
constructs the endpoint state and the required limit.

### Counterattacks and kill conditions

- Bounded trajectory values without a speed bound are insufficient: bounded
  oscillatory paths can fail to converge at the endpoint.
- Reject an endpoint value, endpoint limit, Cauchy callback, compact-image
  callback, or subsequential convergence premise.
- Reject a theorem specialized to `Complex`; the compactness mechanism is
  independent of the polynomial-flow substrate.
- The conclusion must use the one-sided endpoint filter `nhdsLT T`, not a
  sequence selected by the proof.

### Claim boundary and prediction

Passing proves the compactness half of the finite-time continuation
alternative once a uniform derivative bound is available.  It does not
construct a maximal trajectory, derive a derivative bound from a polynomial
ODE and bounded state, or construct the reciprocal infinity chart.  Semantic
capability retrieval was unavailable; lexical retrieval found no matching
kernel, while direct Mathlib inspection selected the mean-value and Cauchy
filter APIs.  No `src/ztare` primitive is added.  Scratch forecast
`scratch_964544973b3602d9` assigns probability `0.88` to focused compilation,
governed ratification, and coverage narrowing.

### Outcome

`FormalBoundedDerivativeEndpointLimit` passes focused compilation and
governed ratification. It works for every complete real normed codomain. The
proof derives Lipschitz continuity on the open interval from the supplied
derivative bound, proves that the left-neighborhood filter is Cauchy and
eventually lies in the interval, and invokes completeness only after mapping
that filter through the trajectory.

Governed record:
`9bcdf8d78a402b45c78d2570e29386625f4aa855e840d8e863b4c73661abb421`;
recompilable closure source:
`33cf4d0382765aceb2acfa1141da3a7f012d5b33888e0961a0f2291104924ef3`;
kernel-parity record:
`a087563bedaf4fccd761b5ea77be5940110c956dfb69e32df201542474f9842d`;
content-bound receipt:
`af1b0f0210f871aa32ff741e1baa5ce23d0ea186b5188d5925ad5357051e12ed`.

Scratch forecast `scratch_964544973b3602d9` resolves success. Coverage v50
has 45 governed supports and 43 bottom-up-covered nodes. Four semantic leaves
remain, but the continuation leaf is mechanically narrower: it now owes a
maximal selected lift with a bounded-speed versus reciprocal-infinity
alternative. Finite-limit construction follows from this theorem, and
analytic continuation through that limit follows from the governed v49
theorem.

## Bounded controlled-polynomial endpoint compactness

### Eigenquestion

For a complex trajectory satisfying

\[
y'(t)=d(t)p(y(t))
\]

on a finite half-open real interval, do uniform bounds on the driver `d` and
the state `y` construct the speed bound and finite endpoint limit required by
v50?

### Candidate theorem and explicit bound

For `p : Complex[X]` and a nonnegative state radius `R`, define

```text
polynomialNNNormBound p R =
  sum i in p.support, nnnorm (p.coeff i) * R^i.
```

The carrier owns `a<T`, the driver and trajectory, the controlled-polynomial
ODE on `Ioo a T`, and uniform driver/state bounds `D,R`.  The terminal must
derive

```text
nnnorm (deriv trajectory t) <=
  D * polynomialNNNormBound p R
```

throughout the interval and construct a finite `nhdsLT T` limit by invoking
the governed v50 endpoint theorem.  It may not own a derivative bound,
Lipschitz witness, Cauchy witness, endpoint state, or endpoint limit.

### Proof skeleton

Expand `p.eval z` as its finite coefficient sum.  The triangle inequality,
multiplicativity of the complex norm, and `nnnorm z <= R` give the explicit
polynomial bound term by term.  The supplied ODE identifies the derivative
with `d(t)*p.eval(y(t))`; combine the driver and polynomial bounds to obtain
the speed bound.  Package that derived bound into
`BoundedDerivativeEndpointCarrier Complex` and apply the governed v50
terminal.

### Counterattacks and kill conditions

- Reject a carrier with a derivative bound or polynomial-evaluation bound.
- The coefficient sum must be constructed from `p` and `R`, rather than an
  existential continuity-on-compact callback.
- The state and driver bounds must be used only on `Ioo a T`; no endpoint
  value or continuity at `T` may be assumed.
- Constant and zero polynomials must remain admitted.

### Claim boundary and prediction

Passing proves that bounded controlled-polynomial motion on a finite interval
has a finite endpoint limit.  It does not construct a maximal selected lift,
prove that failure of bounded state supplies a reciprocal analytic chart, or
glue local ODE solutions around a loop.  Semantic capability retrieval was
unavailable; direct Mathlib inspection selected `Polynomial.eval_eq_sum`,
finite-sum norm bounds, and the governed v50 endpoint kernel.  No
`src/ztare` primitive is added.  Scratch forecast
`scratch_3b4e7ca8928d3bde` assigns probability `0.76` to focused compilation,
governed ratification, and residual narrowing.

### Outcome

`FormalBoundedControlledPolynomialEndpoint` passes focused compilation and
governed ratification. It proves the coefficient-sum evaluation bound for an
arbitrary complex polynomial, derives the explicit speed ceiling from the
ODE, and constructs the finite endpoint limit through the governed v50
kernel. The carrier stores no derivative or polynomial-evaluation bound.

Governed record:
`01b18c94801a24c0cbef421dda8c279e8168e14d94d9c751aee46daf6ed737db`;
recompilable closure source:
`b9cd249dd8ab50b0839c8dd6f7ec7daf2250f21e274e39e72eec91f3f31f29ed`;
kernel-parity record:
`213d59d16705027030b58194c5a62247db08ca0aee598fffbd2b4001981196e9`;
content-bound receipt:
`55bb145bb04cc6f05ed8b301054c1f44189da4f628cdd488f6a169ea2b47f1a5`.

Scratch forecast `scratch_3b4e7ca8928d3bde` resolves success. Coverage v51
has 46 governed supports and 44 bottom-up-covered nodes. Its continuation leaf
now owes maximal selected lifts, a bounded compact-loop driver, and a bounded-
state versus reciprocal-infinity terminal alternative. Once bounded state is
available, the speed bound, endpoint limit, and analytic continuation through
that limit are all governed.

## Arbitrary-filter norm escape to reciprocal convergence

### Eigenquestion and theorem

Does convergence of `norm (trajectory i)` to infinity along an arbitrary
filter construct both eventual nonvanishing and convergence of the reciprocal
trajectory to zero, without any ODE or endpoint assumptions?

`FormalNormEscapeReciprocalLimit` answers yes for every nontrivially normed
field. The proof transports the trajectory through the cobounded filter and
then through inversion. The terminal owns no reciprocal, nonvanishing tail,
growth schedule, sequence, ODE, or analytic-germ premise.

### Outcome

Focused compilation and governed ratification pass, including the matched
negated-conclusion control. Governed record
`67e0c54d559d3425a3156e43f04dd5cd41c91abc54b4daaee8460c8f93ea8af7`;
recompilable closure source
`f64b30ed55d13ea88da8ff146b3d71b2ffe0e6569bb781e1c2ef2213e9fefbde`;
kernel-parity record
`ec078158444523cebba177e996852ad36543fd1200a551cd59e5e004bce54475`;
content-bound receipt
`4ce398507c2ed80e4f370afa548a06f742f87376a5ed8de61d3ad8d652acf934`.
Scratch forecast `scratch_488cb8dd4d412dc7` resolves success.

The theorem supplies only the pathwise chart change. Proving norm escape for
a selected maximal lift and upgrading the reciprocal path limit to a
holomorphic reciprocal germ remain separate mathematical obligations.

## Uniform bounded-ball restart forces endpoint escape or extension

### Eigenquestion and theorem

For an abstract trajectory category on a finite half-open real interval,
does restriction stability, uniqueness on open preconnected overlaps, and a
restart time uniform over every bounded state ball force extension through
the endpoint or norm escape?

`FormalUniformRestartEndpointEscape` answers yes. A failed norm-escape
statement produces bounded returns arbitrarily close to the endpoint. The
uniform restart centered at one such return crosses the endpoint. Restricting
the original and restarted solutions to their precise open overlap and using
local uniqueness constructs eventual equality in `nhdsLT`, hence a finite
endpoint extension. The contrapositive gives norm escape for every
nonextendable trajectory.

### Outcome and boundary

Focused compilation and governed ratification pass, including the matched
negated-conclusion control. Governed record
`1c7573b2d50b3d7e3de72d9c0c9a2aa1dfb91c2ee67dfa782d179e93d1577391`;
recompilable closure source
`a709f3189b17032155e5cbb3a9c0b32167850d7dc254446c4a589db45797119b`;
kernel-parity record
`518bbfa31e9b38e284595e7d13c18ad67f82a79ef98b019707d44c6ccbb886b3`;
content-bound receipt
`ca90dc44704eae98a224ba6c95fe69289c89b2cc241021c795f1b14e5fda1c07`.
Scratch forecast `scratch_cbada169b873247e` resolves success.

The carrier contains only the solution predicate and its restriction,
overlap-uniqueness, original-solution, and bounded-ball restart laws. It does
not contain escape, extension, a bounded-return point, or restart agreement.
For the Jacobian adapter, the remaining task is to construct this carrier
from the controlled-polynomial ODE and the selected maximal lift. Coverage
v53 records 48 governed supports, 46 bottom-up-covered nodes, 40 directly
ratified nodes, five semantic leaves, and twelve semantic inferences.

## Preregistered bounded-state uniform restart for controlled polynomials

### Eigenquestion and intended formal surface

Fix `p : Complex[X]`. If `driver : Real -> Complex` is continuous and has one
global norm bound, is there, for every state radius `R`, one positive restart
time that works simultaneously for every real restart time and every complex
initial state of norm at most `R` for

```text
y'(t) = driver(t) * p.eval (y(t))?
```

The intended terminal constructs `epsilon > 0` and, for every `t0,state` in
the declared range, a curve with the exact initial value and ODE on
`Ioo (t0-epsilon) (t0+epsilon)`. The carrier may contain `p`, `driver`, its
continuity, and its global bound. It may not contain a local solution,
restart radius, Lipschitz constant, Picard rectangle, or existence callback.

### Candidate construction

On the complex ball of radius `R+1`, complex polynomial evaluation is `C^1`
as a real map and therefore has a finite Lipschitz constant. Multiplication
by `driver(t)` scales that constant by at most the declared driver bound. The
explicit coefficient sum from
`FormalBoundedControlledPolynomialEndpoint.polynomialNNNormBound` bounds the
field on the same ball. Choose a symmetric time radius small enough that this
field bound moves every initial point in the radius-`R` ball by less than the
one-unit state margin. Mathlib's Picard--Lindelof theorem then constructs the
solution on the closed time interval; restriction to its interior gives the
required `HasDerivAt` statement.

### Counterattacks and kill conditions

- Reject a restart time depending on `t0` or `state`; it may depend only on
  `p`, the driver bound, and `R`.
- Reject a supplied local solution, local-existence function, Lipschitz
  witness, or Picard--Lindelof carrier.
- Reject exclusion of equilibria, constant polynomials, or the zero
  polynomial.
- Reject a theorem that gives only `HasDerivWithinAt` on a closed interval;
  the v53 adapter requires an open restart interval.
- Continuity without a global driver bound is insufficient for a restart
  time uniform over all real centers; both hypotheses must be used.

### Recurrence check, claim boundary, and prediction

The capability-amnesia instrument fell back to lexical retrieval and found
no matching repository utility. Source audit found a nearby theorem rather
than a missing solver: `FormalAnalyticPolynomialControlledTrajectory`
constructs pointwise holomorphic germs, while Mathlib's
`IsPicardLindelof` supplies the uniform compact-cylinder construction. This
increment adds no `src/ztare` machinery and does not duplicate the existing
holomorphic germ kernel.

Passing removes the bounded-ball restart component of
`two_flow_selected_uniformly_restartable_maximal_lift_carrier`. It does not
construct the maximal lift, prove nonextendability, establish global overlap
uniqueness, or upgrade escape to a holomorphic reciprocal germ. A scratch
forecast `scratch_67de62bfa93f8379` assigns probability `0.67` to focused
compilation, governed ratification, and exact coverage narrowing.

### Outcome

`FormalControlledPolynomialUniformRestart` passes focused compilation, the
full module build, and governed adversarial ratification. For every state
radius it constructs a positive `epsilon` before quantifying over the real
restart center and complex initial state. The returned curve has the exact
initial value and satisfies the controlled-polynomial ODE throughout the
open symmetric interval. The theorem includes equilibria and zero or
constant polynomials.

The carrier stores only the polynomial, continuous driver, global driver
bound, and proof of that bound. Its polynomial Lipschitz constant and field
bound are derived from the coefficient-sum bound and the real mean-value
theorem; the local curve is then constructed by Picard--Lindelof.

Governed record:
`39f57f7f8537e0dcfe07130160bb26c3f00f1685a74d29d6e7b4de5adfd62251`;
recompilable closure source:
`118729a48f83ef86ec0b93e7356d8d5d17718d05aa85f91e7861b7882ac10589`;
kernel-parity record:
`e6490bb04a535ae9466605d9a5e405a5a190860d62d165851e014aaa0543d6e2`;
content-bound receipt:
`eea30edabd7b12f683d878baf193f806cd4ba9db05d2be38c52941d11db68da9`.
Scratch forecast `scratch_67de62bfa93f8379` resolves success.

Coverage v54 has 49 governed supports, 47 bottom-up-covered nodes, 41
directly ratified nodes, five semantic leaves, and thirteen semantic
inferences. Uniform bounded-ball restart is now a governed child of the
selected continuation chain. The remaining carrier leaf owes the selected
maximal lift, globally bounded continuous loop-driver adapter,
restriction-stable overlap uniqueness, controlled-polynomial bindings, and
nonextendability; it no longer owes local restart.

## Preregistered controlled-polynomial overlap uniqueness

### Eigenquestion and intended formal surface

Let `driver : Real -> Complex` have one global norm bound and let
`p : Complex[X]`. If two complex curves solve

```text
y'(t) = driver(t) * p.eval (y(t))
```

at every point of a preconnected real time domain and agree at one point of
that domain, must they agree on the complete domain without an assumed
solution-uniqueness law?

The intended terminal quantifies over the domain, both curves, and the
anchor. It assumes only preconnectedness, membership of the anchor, the two
pointwise ODE laws, the global driver bound, and equality at the anchor, and
returns `EqOn left right domain`. Openness, analyticity, global state bounds,
and a supplied Lipschitz witness are excluded from the interface.

### Candidate construction

For each target time, order connectedness puts the closed interval joining
the anchor to that target inside the domain. Derivative data makes both
curves continuous on this compact interval, so their images admit a common
finite state radius. The derivative polynomial has the explicit
coefficient-sum bound on the corresponding closed ball. Scaling by the
bounded driver gives a uniform local Lipschitz constant on that ball, and
the forward or time-reversed Gronwall uniqueness theorem identifies the two
curves at the target. Quantifying over targets yields `EqOn`.

### Counterattacks and kill conditions

- Reject a carrier-supplied local/global uniqueness law, state bound,
  Lipschitz constant, compactness witness, or analytic trajectory premise.
- Reject a result restricted to one neighborhood of the anchor or to a
  preselected compact interval.
- Reject global Lipschitzness of polynomial evaluation; the constant must be
  constructed separately on each compact trajectory segment.
- Constant and zero polynomials and equilibrium trajectories must remain
  admitted.
- Driver continuity may not be used to conceal uniqueness: its global norm
  bound alone should suffice for this theorem.

### Recurrence check, claim boundary, and prediction

Repository audit found the local autonomous Gronwall theorem and the
holomorphic germ-uniqueness theorem, but no theorem deriving complete
preconnected-domain uniqueness for a time-dependent bounded driver and
complex polynomial state field from the ODE laws alone. The construction
reuses Mathlib's interval Gronwall theorem and the governed polynomial
coefficient bound; no new apparatus primitive is proposed.

Passing removes the overlap-uniqueness component of
`two_flow_selected_maximal_lift_bounded_driver_local_uniqueness_carrier`.
It does not construct the selected maximal lift or driver adapter, prove
nonextendability, bind that lift to the factor branch, or upgrade reciprocal
escape to a holomorphic germ. Scratch forecast `scratch_b1cedce08fcf638a`
records `p=0.64` for focused compilation, governed ratification, and exact
coverage narrowing.

### Outcome

`FormalControlledPolynomialOverlapUniqueness` passes focused compilation, a
3,301-job focused module build, and governed adversarial ratification. Given
only the global driver bound, two pointwise ODE laws on a preconnected real
domain, and equality at one anchor, it constructs equality on the complete
domain. It assumes neither trajectory bound nor a uniqueness or Lipschitz
law. For each target the proof constructs its own compact state ball and
selects forward or time-reversed Gronwall uniqueness from the time order.

Governed record:
`9f35200f054a5351365e5b287f9868fd031343dc7eca98ba425527a8efc79da6`;
recompilable closure source:
`45a4e0d47b94c8e771f0f0ed7c3f687d26bbe6db1b4f3f2c3692f28c1d72ec11`;
kernel-parity record:
`24ca35b345f1888a1550e93df137e5296a526315def0e47f5ca6610e5b031750`;
content-bound receipt:
`419f63bac8ac57b8c6c1ba880f8d34709e372ff26bc7006f012210bbed8c68ed`.
Scratch forecast `scratch_b1cedce08fcf638a` resolves success.

Coverage v55 has 50 governed supports, 48 bottom-up-covered nodes, 42
directly ratified nodes, five semantic leaves, and fourteen semantic
inferences. The narrowed continuation leaf
`two_flow_selected_maximal_lift_bounded_driver_carrier` now owes only the
selected maximal lift, globally bounded continuous loop-driver adapter,
nonextendability, and exact ODE/endpoint bindings. Overlap uniqueness and
uniform bounded-ball restart are governed consequences.

## Preregistered canonical maximal controlled-polynomial trajectory

### Eigenquestion and intended formal surface

Does the governed uniform-restart theorem plus complete overlap uniqueness
construct a canonical maximal solution domain and trajectory through every
initial state of a continuous globally bounded controlled-polynomial field,
without Zorn data or a supplied maximal candidate?

An admissible candidate is an open preconnected real domain containing the
anchor, a complex curve with the prescribed anchor state, and the pointwise
controlled-polynomial ODE on that domain. The intended terminal constructs
one open preconnected maximal domain and curve through the initial state,
proves the ODE everywhere on it, and proves that every admissible candidate's
domain embeds into it and its curve agrees there.

### Candidate construction

Take the union of the domains of all admissible candidates. Every candidate
contains the anchor, so the union is preconnected; openness is preserved by
the union. At each time in the union choose one candidate containing that
time and define the maximal curve by its value. Complete overlap uniqueness
makes this definition independent of the choice and identifies the maximal
curve with every candidate on its complete domain. On a neighborhood of each
time, that equality transports the candidate's derivative to the maximal
curve. Uniform restart supplies the first candidate, including equilibrium
and constant-polynomial cases.

### Counterattacks and kill conditions

- Reject a supplied maximal domain, maximal curve, chain upper bound, Zorn
  witness, global solution, or candidate-compatibility field.
- Reject only existential maximality without the universal domain inclusion
  and `EqOn` law for every candidate.
- Reject a union curve whose ODE is postulated rather than transported from a
  locally selected candidate.
- Reject a theorem needing global state boundedness or excluding finite-time
  escape, equilibrium states, or zero/constant polynomials.
- The construction may use classical choice for pointwise representatives,
  but independence must follow from the governed overlap theorem.

### Recurrence check, claim boundary, and prediction

Semantic capability retrieval surfaced no maximal-ODE utility. Direct
Mathlib/repository audit found local Picard--Lindelof, overlap uniqueness, and
generic Zorn lemmas, but no maximal solution construction. The union-of-all-
compatible-germs construction avoids adding a second solver and introduces
no `src/ztare` primitive.

Passing constructs the maximal controlled-polynomial trajectory through
abstract bounded-driver initial data. It does not derive the critical-loop
driver and initial state from the selected factor branch, convert candidate
maximality into the exact finite-endpoint nonextension predicate used by v53,
or construct the reciprocal holomorphic chart. Scratch forecast
`scratch_01b0071f5e6c1e80` records `p=0.56`.
