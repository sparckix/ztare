# Moving cusp Poisson-section eigenquestion

**Status:** successor pencil, opened before the discriminating bracket
calculation

## Object and claim boundary

Let

\[
C=4P^3+27Q^2,\qquad
\operatorname{res}(K)=K(-3r^2,-2r^3),
\]

and let

\[
\mathcal H_{\rm lift}=\mathbb Q\oplus(P^3,PQ,Q^2).
\]

The object sought here is a filtered linear section

\[
s:\mathbb Q\oplus r^5\mathbb Q[r]\longrightarrow\mathcal H_{\rm lift},
\qquad \operatorname{res}\circ s=\operatorname{id},
\]

whose image is closed under the planar Poisson bracket and whose ordinary
polynomial degree has a uniform asymptotic bound

\[
\deg s(r^m)\le \frac m3+O(1).
\]

Such a section would give a mechanism by which the \(1/3\)-rate
instantaneous target lifts can remain \(1/3\)-rate under BCH composition.
Its existence would still not settle the full moving-family contact problem:
transverse compatibility and the paired source logarithm would remain.

The kernel of `res` is \((C)\), and \((C)\) need not be a Poisson ideal.
Consequently the defect of a section is not called a Lie-algebra cocycle
unless the calculation first proves that the required quotient bracket is
well-defined.  The primary question is the Poisson-closed splitting itself.

## Minimum-degree section

For \(m\ge5\), write \(m=3q+\epsilon\), with
\(\epsilon\in\{0,1,2\}\).  Up to the scalar needed to make the restriction
exactly \(r^m\), the unique minimum-degree monomial section is

\[
s_m^{(0)}=
\begin{cases}
Q^q,&\epsilon=0,\\
P^2Q^{q-1},&\epsilon=1,\\
PQ^q,&\epsilon=2.
\end{cases}
\]

All residue-pair brackets remain in this monomial family except the
\((1,1)\) pair.  There

\[
\{P^2Q^{q-1},P^2Q^{t-1}\}
=2(t-q)P^3Q^{q+t-3},
\]

and

\[
P^3Q^j=-\frac{27}{4}Q^{j+2}+\frac14CQ^j.
\]

Thus the first candidate defect is a \(C\)-multiple with only one extra
ordinary degree relative to the minimum section.

## Attack vectors and counterattacks

1. **Homogeneous correction recurrence.**  Replace
   \(s_m^{(0)}\) by \(s_m^{(0)}+CL_m\), preserving weighted degree, and
   solve the bracket-closure equations residue class by residue class.
   A solution with uniformly bounded ordinary-degree overhead supports a
   \(1/3\)-rate target BCH mechanism.

   **Counterattack:** exhibit a finite Jacobi-compatible cycle whose
   correction equations are inconsistent.  This kills the proposed
   splitting class without extrapolating from finite-order fitting.

2. **Kernel-ideality audit.**  Compute
   \(\{CL,s_m^{(0)}\}\bmod(C)\).  If it is nonzero, correction terms alter
   the induced restriction bracket.  Then ordinary extension-cohomology
   language is invalid, and the equations must be treated as a nonlinear
   filtered-section problem.

   **Counterattack:** if a smaller correction subspace is a Poisson ideal
   relative to the selected image, identify it explicitly before using
   cocycle or coboundary terminology.

3. **Low-degree decisive packet.**  Solve the exact equations on the
   smallest exponents containing two distinct residue-one generators and
   every residue-pair interaction they generate.  Extend only if this packet
   leaves a free compatible family.

   **Counterattack:** a passing finite packet is evidence for a recurrence,
   not an all-order theorem.  Promotion requires a closed formula and
   induction, while a single exact inconsistency is decisive.

## Success and kill conditions

- **Section success:** an explicit all-order section, exact Poisson closure,
  and a proved uniform degree-overhead bound.
- **\(1/3\)-mechanism kill:** an exact obstruction applying to every section
  with \(m/3+O(1)\) degree, or a lower bound forcing overhead linear in \(m\).
- **Terminology kill:** if \((C)\) is not a suitable relative Poisson ideal,
  drop the cocycle claim even if the minimum-section defect happens to be a
  \(C\)-multiple.
- **Campaign boundary:** neither a section nor its obstruction alone fixes
  \(\sigma_{\rm ct}\); it selects the next moving/transverse compatibility
  theorem.

## Intended verification surface

Pencil algebra and a small exact symbolic bracket replay come first.  Lean
is appropriate only after the section recurrence or a finite obstruction
has been stated independently of the implementation.

## Settled theorem: the unique graded split pays rate \(1/2\)

Introduce normalized weighted coordinates

\[
X=-\frac P3,\qquad Y=-\frac Q2.
\]

Then

\[
\operatorname{res}(X)=r^2,\qquad
\operatorname{res}(Y)=r^3,
\]

and

\[
D:=X^3-Y^2=-\frac C{108}.
\]

For the bracket convention

\[
\{K,L\}=K_PL_Q-K_QL_P,
\]

one has

\[
\{K,L\}
=\frac16(K_XL_Y-K_YL_X).
\]

This normalization removes every scalar from the restriction section.

### Exact minimum-section defect

Let

\[
s_m=X^{a_m}Y^{b_m},\qquad 2a_m+3b_m=m,
\]

where \(a_m+b_m\) is minimum.  Thus

\[
(a_m,b_m)=
\begin{cases}
(0,q),&m=3q,\\
(2,q-1),&m=3q+1,\\
(1,q),&m=3q+2.
\end{cases}
\]

For

\[
\lambda_{m,n}
=\frac{a_mb_n-b_ma_n}{6},
\qquad w=m+n-5,
\]

the restriction of \(\{s_m,s_n\}\) is
\(\lambda_{m,n}r^w\).  Hence the exact section defect is

\[
\delta_{m,n}
=\{s_m,s_n\}-\lambda_{m,n}s_w\in(C).
\]

Every residue pair has zero defect except two distinct residue-one
exponents.  If

\[
m=3p+1,\qquad n=3q+1,
\qquad p,q\ge2,
\]

then

\[
\boxed{
\delta_{m,n}
=\frac{q-p}{3}DY^{p+q-3}
=-\frac{q-p}{324}C\,Y^{p+q-3}.
}
\]

This includes the zero case \(p=q\).  Thus the minimum section is not
Poisson closed, and the failure is exactly one stabilizer direction.

There is a terminology boundary.  The target kernel \((C)\) is not a
Poisson ideal:

\[
\operatorname{res}\{C,K\}
=-18r^2\frac d{dr}\operatorname{res}(K),
\]

which is generally nonzero.  Therefore \(\delta\) is a section defect at
the Hamiltonian level.  It becomes stabilizer-valued extension data only
after the paired source action is included; ordinary quotient-Lie-algebra
cohomology does not apply to the target kernel alone.

### Explicit correction and its degree

There is an all-order correction.  Define

\[
t_m=
\begin{cases}
X^{m/2},&m\ \text{even},\\
X^{(m-3)/2}Y,&m\ \text{odd}.
\end{cases}
\]

This is the unique representative of \(r^m\) that is affine in \(Y\).
Its span is Poisson closed.  For every pair with nonzero bracket,

\[
\boxed{
\{t_m,t_n\}
=\frac{A_mB_n-B_mA_n}{6}\,t_{m+n-5},
}
\]

where \(t_j=X^{A_j}Y^{B_j}\), \(B_j\in\{0,1\}\).
The zero even-even brackets also stay in the span.
For \(m\ge5\), these representatives are either \(P^a\) with \(a\ge3\)
or \(P^aQ\) with \(a\ge1\), so they satisfy both target lift ideals.

The correction is explicitly a \(C\)-multiple.  If

\[
s_m=X^aY^{2k+\epsilon},
\qquad \epsilon\in\{0,1\},
\]

then

\[
\begin{aligned}
t_m-s_m
&=X^aY^\epsilon(X^{3k}-Y^{2k})\\
&=D\,X^aY^\epsilon
\left(
\sum_{j=0}^{k-1}
X^{3(k-1-j)}Y^{2j}
\right).
\end{aligned}
\]

Equivalently,

\[
t_m-s_m
=-\frac C{108}X^aY^\epsilon
\left(
\sum_{j=0}^{k-1}
X^{3(k-1-j)}Y^{2j}
\right).
\]

This records the exact \(C\)-adic correction rather than an equality modulo
\(C\).

The minimum section has degree

\[
\deg s_m=\left\lceil\frac m3\right\rceil,
\]

whereas

\[
\boxed{\deg t_m=\left\lfloor\frac m2\right\rfloor.}
\]

Whenever a nonzero weighted-homogeneous correction \(CL_m\) exists, it has
degree at least

\[
3+\left\lceil\frac{m-6}{3}\right\rceil
=\left\lceil\frac m3\right\rceil+1.
\]

Thus the exact minimum-degree representative is unique.  The closed
correction above has linear, rather than bounded-additive, overhead.
At weight seven the correction space itself is zero because weight one is
absent from \(\mathbb Q[P,Q]\); this only strengthens uniqueness there.

### Why the closed section is unique

Uniqueness is asserted only among graded rank-one sections: one
weighted-homogeneous representative \(u_m\) of \(r^m\) for each \(m\ge5\),
with

\[
\{u_m,u_n\}\in\mathbb Q\,u_{m+n-5}.
\]

The weight-five representative is forced:

\[
u_5=XY.
\]

The operator

\[
\operatorname{ad}_{XY}(X^aY^b)
=\frac{b-a}{6}X^aY^b
\]

has distinct eigenvalues on distinct monomials of one fixed cusp weight.
Closure with \(u_5\) therefore forces every \(u_m\) to be a monomial.

At weight six there are two possibilities, \(X^3\) and \(Y^2\).  The
\(Y^2\) branch is excluded by the following exact cycle:

\[
\begin{array}{c|c}
\text{forced weight}&\text{monomial}\\ \hline
u_6&Y^2\\
u_7&X^2Y\\
u_8&XY^2\\
u_9&Y^3\\
u_{10}&X^2Y^2
\end{array}
\]

The nonzero bracket \(\{u_7,u_{10}\}\) forces

\[
u_{12}\propto X^3Y^2,
\]

while the nonzero bracket \(\{u_8,u_9\}\) forces

\[
u_{12}\propto Y^4.
\]

These monomials are linearly independent, so no rank-one weight-twelve
space can satisfy both requirements.

Consequently \(u_6=X^3\).  The brackets with the forced
\(u_7=X^2Y\) inductively give

\[
u_{2k}=X^k.
\]

Every odd-weight monomial has positive \(Y\)-exponent.  Its nonzero bracket
with \(u_6=X^3\) must land in the already-fixed even line, forcing that
exponent to equal one.  Hence

\[
u_{2k+1}=X^{k-1}Y.
\]

This is precisely the section \(t_m\).

## Verdict and campaign boundary

The minimum-degree \(1/3\)-rate section has a nonzero stabilizer defect.
The defect can be removed by changing representatives, but every graded
rank-one Poisson-closed splitting is the parity section and has asymptotic
degree rate \(1/2\).  Therefore the proposed \(m/3+O(1)\) target BCH
mechanism is excluded in this graded rank-one category.

This does not prove a lower bound for \(\sigma_{\rm ct}\).  It does not
classify sections with several generators per weight, nonhomogeneous
filtered cancellations, the positive transverse layers, or the paired
moving-family source action.  It selects a sharper successor question:
whether the moving contact can exploit a higher-rank filtered target
algebra, or whether the \(1/2\) graded cost survives those additional
coordinates.

## Deterministic replay

[`gauge_moving_poisson_section.py`](gauge_moving_poisson_section.py) checks
the exact defect formula, divisibility by \(C\), the closed parity section,
the explicit correction, target lift ideals, the weight-twelve
contradiction, and uniqueness of the monomial section through a finite
adversarial control range.

## Formal carrier and provider-free ratification

The exponent-pair classification, the weight-six countercycle, the parity
recurrences, the exact bracket scalars, existence of the parity section, and
the degree identity

\[
\deg t_m=\left\lfloor\frac m2\right\rfloor
\]

are formalized in
[`AxiomPackJacobianMovingPoissonSectionArithmetic.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianMovingPoissonSectionArithmetic.lean).
The module compiles without `sorry`, `admit`, or declared axioms.

LeanMill ratified

`AxiomPackJacobianMovingPoissonSectionArithmetic.moving_poisson_section_arithmetic_terminal_certificate`

through the provider-free carried-artifact route with zero inference calls.
Target identity, statement integrity, the axiom allowlist, matched negative
control, governance, and kernel compilation all passed.

- source/closure SHA-256:
  `649479834fd74a3135a20ba3d02a928c7a46a412d4bd5d2ab29d2eb9b5fe7bc7`
- target-signature SHA-256:
  `fee8469ed93f3a594406de9383a68ad43d5dbae219c425adf10ea49f095efaa8`
- kernel-parity record SHA-256:
  `8430de7d0047fb08198f59d26b90d46ccf7b7e8e86f3dbc1d609a1571cd2a569`
- closure-certificate record SHA-256:
  `e3ed23c5a3e2482a7409ac41c8e0b1ef2b9d16a4bfd532f64539a087ecf13d3e`
- closure artifact:
  [`AxiomPackJacobianMovingPoissonSectionArithmetic.moving_poisson_section_arithmetic_terminal_certificate_649479834fd7.lean`](../../../ztare_proofs/closures/AxiomPackJacobianMovingPoissonSectionArithmetic.moving_poisson_section_arithmetic_terminal_certificate_649479834fd7.lean)

The formal module begins after the polynomial-to-monomial reduction.  The
simple-spectrum argument for \(\operatorname{ad}_{XY}\), the
associated-graded promotion for triangular filtered sections, and the
moving-family interpretation remain in the pencil layer.
