# \(s\)-adic causality and the diagonal-staircase obstruction

**Status:** exact pencil lemma; the literal redistribution of the completed
canonical row is excluded, while the unrestricted symmetric tail minimax
remains open

## Eigenquestion

Can the infinitely supported \(s\)-linear canonical target normalization be
made coefficientwise polynomial by moving transverse layer \(m\) to a later
parameter order \(n(m)\), with \(n(m)\to\infty\)?

This is the direct coefficientwise-finite staircase proposed in Vector B of
[`gauge_tail_minimax_attack_vectors_pencil.md`](gauge_tail_minimax_attack_vectors_pencil.md).

## The two completions

Let \(E_m\) denote the finite-dimensional source/target coefficient space at
transverse layer \(m\).  Coefficientwise polynomial formal contacts live in

\[
\mathcal P_s
=
\prod_{n\geq1}s^n\left(\bigoplus_{m\geq0}E_m\right).
\]

Every fixed parameter row has finite transverse support.  The completed
canonical weighted normal form instead lives in the larger space

\[
\widehat{\mathcal P}_{s,g}
=
\prod_{n\geq1}s^n\left(\prod_{m\geq0}E_m\right).
\]

The distinction is visible already modulo \(s^2\).  If

\[
c_{\mathrm{can}}
=s\sum_{m\geq0}c_m,
\qquad c_m\in E_m,
\]

has infinitely many nonzero \(c_m\), then
\(c_{\mathrm{can}}\in\widehat{\mathcal P}_{s,g}\setminus\mathcal P_s\).

## Causality lemma

Let \(\nu\colon\mathbb N\to\mathbb N_{\geq1}\) have finite fibers and form
the locally finite diagonal series

\[
c_\nu=\sum_{m\geq0}s^{\nu(m)}c_m\in\mathcal P_s.
\]

If \(c_m\neq0\) for infinitely many \(m\), then

\[
\boxed{c_\nu\not\equiv c_{\mathrm{can}}\pmod {s^2}.}
\]

Indeed,

\[
[s]c_\nu=\sum_{\nu(m)=1}c_m
\]

has finite transverse support, whereas

\[
[s]c_{\mathrm{can}}=\sum_{m\geq0}c_m
\]

has infinite support.

Formal group operations cannot repair this mismatch.  For \(s\)-adically
positive Lie series \(U,V\),

\[
\nu_s[U,V]\geq\nu_s(U)+\nu_s(V),
\]

so

\[
[s]\operatorname{BCH}(U,V)=U_1+V_1.
\]

The same triangularity holds for exponential, logarithm, Magnus, and dexp:
the coefficient of \(s^N\) depends only on input rows of order at most
\(N\).  A control first appearing at order \(s^{N>1}\) cannot change the
first-order contact equation or any of its transverse quotients.

## Application to the canonical recurrence

The completed canonical normal form has

\[
r_m=[sA^m]R_m
=-\frac{3^m(m+3)(4m+1)}{216\,2^m}\neq0
\qquad(m\geq2).
\]

The exact polynomial-category consequence in
[`gauge_canonical_top_recurrence_result.md`](gauge_canonical_top_recurrence_result.md)
also shows that infinitely many canonical target weights have nonzero
\(s\)-linear coefficient.  Thus both sides of the canonical split carry an
infinite transverse row at parameter order one.

It follows that assigning its weight-\(m\) correction to
\(s^{\nu(m)}\), with \(\nu(m)\to\infty\), changes the first derivative of
the contact.  This is a different gauge path rather than an admissible
reindexing of the canonical normalizer.

Equivalently, diagonal truncations do not converge to the canonical row in
the coefficientwise \(s\)-adic topology.  Target-adic completion followed
by diagonal regrading does not commute with reduction modulo \(s^2\).

## What remains possible

Local finiteness alone gives no positive slope inequality.  Abstract support
can be placed at \(n(m)=m^2\); even a spatial cost linear in \(m\) then has
cost-to-order ratio tending to zero.  The contact equation rules out using
that support as a delayed copy of the canonical first row, but a distinct
noncanonical coupled recursion could still exist.

Any valid slope-below-two construction must therefore:

1. choose a finite polynomial first-order pair \((K_1,Y_1)\) satisfying the
   complete first-order contact equation;
2. retain its noncanonical transverse cancellations at order one;
3. solve the moving contact equation at every later order without treating
   higher rows as corrections to the canonical \(s\)-linear quotient; and
4. prove coefficientwise finiteness and the source/target logarithmic
   bounds after all BCH terms.

Conversely, a lower theorem must be uniform over the complete polynomial
first-order fiber.  The canonical recurrence by itself tests one
target-adically completed splitting and cannot supply that uniformity.

## Finite-state shadow of the canonical row

The canonical recurrence nevertheless identifies a sharper construction
test.  Put

\[
x_m=(r_m,r_{m+1},r_{m+2})^{\mathsf T}.
\]

Then

\[
x_{m+1}=Jx_m,\qquad
J=
\begin{pmatrix}
0&1&0\\
0&0&1\\
27/8&-27/4&9/2
\end{pmatrix},
\]

and

\[
\det(\lambda I-J)=(\lambda-3/2)^3.
\]

The partial-fraction formula places the tail in the principal-parts module

\[
\mathcal J_{2/3}
=
\operatorname{span}_{\mathbb Q}
\left\{
(1-\tfrac32u)^{-1},
(1-\tfrac32u)^{-2},
(1-\tfrac32u)^{-3}
\right\}.
\]

The polynomial part affects only the initial coefficients.  Coefficient
shift on \(\mathcal J_{2/3}\) is the displayed size-three Jordan block.
Thus the infinite transverse row has a three-state linear realization
concentrated at the exceptional pole \(u=2/3\).  A
plausible noncanonical staircase would have to identify this finite state
transition, or a conjugate one, with the associated-graded adjoint action of
an admissible finite first-order source/target prefix.  Repeated brackets
would then place its outputs on increasing parameter rows automatically.

This observation does not supply the contact: Magnus coefficients introduce
their own rational factors, and a candidate adjoint action would have to
preserve the lift ideals, the moving-family equation, and the source/target
degree budget.  It suggested the discriminating test:

\[
\boxed{\text{Does the complete finite first-order contact fiber contain an
adjoint module with minimal polynomial }(\lambda-3/2)^3?}
\]

The exact replay
[`gauge_first_order_adjoint_module_kill.py`](gauge_first_order_adjoint_module_kill.py)
kills this identification under its natural interpretation.  The
three-dimensional cap-seven homogeneous fiber has Hamiltonian basis

\[
\begin{aligned}
H_0&=-PQ,\\
H_1&=-\frac{4P^3+27Q^2}{12},\\
H_2&=-\frac{
24P^4-2P^3-108P^2Q+162PQ^2+24PQ+27Q^2
}{6}.
\end{aligned}
\]

It is not adjoint-invariant.  Each pairwise Poisson bracket lies outside
this span, and the corresponding source lifts have degrees \(9,13,13\).
Solving

\[
\left\{
a_0H_0+a_1H_1+a_2H_2,H_j
\right\}
\in\operatorname{span}(H_0,H_1,H_2)
\quad(j=0,1,2)
\]

forces \(a_0=a_1=a_2=0\).  Adding the affine particular Hamiltonian
\(-Q^2/4-P^3/36\) makes the preservation equations inconsistent.

The numerical \(3/2\) in this fiber is only the coefficient identity

\[
K_*=H_1-\frac32H_0.
\]

The later compatibility equations select the one-dimensional \(K_*\)
line, whose self-adjoint action is zero.  It is unrelated to the
eigenvalue of coefficient shift on \(\mathcal J_{2/3}\).

There is also a category obstruction.  The complete polynomial homogeneous
isotropy is infinite-dimensional:

\[
H_m=\frac{K_*^{m+1}}{m+1},\qquad
Z_m=(K_*\circ F_0)^m Z_*
\quad(m\ge0).
\]

The source-excess filtration is positive on every nonzero homogeneous
isotropy class and brackets add filtration degree.  Hence an adjoint action
on a finite-support graded module is nilpotent; its minimal polynomial has
the form \(\lambda^k\), not \((\lambda-\frac32)^3\).

A well-typed successor would first define canonical transverse quotients
\(Q_m\), prove that bracket action descends \(Q_m\to Q_{m+q}\), and supply
canonical grade transports.  Only then can one compare the transported
action with the coefficient-shift Jordan block and bind an input/output
pair to the exact \(r_m\).  Without those objects, a projected \(3\times3\)
matrix depends on the truncation complement.

## Bounded coupled replay

The broader noncanonical lane is not excluded at its first transition.  An
exact replay of
[`gauge_order_one_stabilizer_probe.py`](gauge_order_one_stabilizer_probe.py)
with parameter order two and source-degree bound five gives:

\[
\begin{array}{c|c}
\text{system}&\text{exact result}\\ \hline
\text{complete order-one fiber at bound five}
  &\operatorname{rank}=45,\ \operatorname{nullity}=1\\
\text{order-two complete image}
  &\operatorname{rank}=45,\
    \operatorname{rank}[\text{image}\mid\text{residual}]=45\\
\text{selected order-two extension}
  &\deg(Y_{2,v})=\deg(Y_{2,t})=5
\end{array}
\]

The unique order-one direction is the certified seed stabilizer, and the
order-two image has no quotient obstruction for any value of its parameter.
One new homogeneous direction remains at order two.

The already exhaustive continuation in
[`gauge_minimized_formal_contact_pencil.md`](gauge_minimized_formal_contact_pencil.md)
shows that source bound five forces the stabilizer parameter to zero at
order three and admits no prefix through order four.  This excludes a
uniform-degree-five realization.  It does not exclude a linearly growing
bound with asymptotic slope below two.

This finite result is useful only as a countercheck on scope: the
\(s\)-adic causality lemma does not force an early failure of every
noncanonical recursion.  An all-order construction still owes compatible
choices of the accumulating homogeneous directions and logarithmic, rather
than assembled-map, degree control.

## Replay and kill conditions

The deterministic replay
[`gauge_canonical_top_recurrence.py`](gauge_canonical_top_recurrence.py)
was rerun on 2026-07-29.  It reproduced the first twelve nonzero \(r_m\),
the rational generating function, the third-order recurrence, and the
explicit local-finiteness consequence used above.
An independent exact matrix check gave
\(\det(\lambda I-J)=(2\lambda-3)^3/8\),
\(\operatorname{rank}(J-\frac32I)=2\),
\(\operatorname{rank}(J-\frac32I)^2=1\), and
\((J-\frac32I)^3=0\).
The bounded coupled replay above was run with
`run(maximum_order=2, source_degree_bound=5)` and returned exact rational
rank computations and a full coefficient replay.

The causality lemma would fail only after changing the category to allow
negative powers of \(s\), a parameter redefinition that changes the first
jet, or target-adic rather than coefficientwise-polynomial coefficients.
Those operations are outside the declared contact statistic.

The broader Vector B lane remains live precisely at the noncanonical
coupled recursion in the four bullets above.  A finite prefix or a diagonal
support pattern without the contact equation is not evidence for a value of
\(\sigma_{\rm ct}\).
