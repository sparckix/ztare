# Unrestricted symmetric tail minimax for the normalized Jacobian family

## Current theorem boundary

In the declared coefficientwise-polynomial gauge category for the normalized
public Jacobian family, the radial staircase establishes

\[
\boxed{\sigma_{\rm ct}\le2.}
\]

The statistic is the maximum of the source logarithmic derivation-excess
rate and target logarithmic derivation-degree rate.  Source velocities use
the right-multiplication convention and target velocities use the
left-multiplication convention.

The matching lower bound is conditional on a schedule-level route theorem.
The zero-positive-face terminal must first split by target critical support.
Finite support must construct the regular Rees two-flow carrier already
excluded by the kernel theorem.  Infinite support must construct an
actual-schedule transfer-aware semidirect orbit from the finite polynomial
Lie pair `(A,J)`, followed by an all-degree exclusion appropriate to its
generally nonpolynomial group-module coordinate.  The former finite-`(f,L)`
density-clock route does not follow: v123 kernel-checks a polynomial Lie pair
whose exponential module coordinate has infinite support.  Strict ordinary
target rate alone cannot supply the support split:
the v105 kernel exhibits infinitely many critical rows at strict ordinary
rate below two, although that counterfamily is not itself a coupled gauge
schedule.

Inside the finite branch, polynomial-flow continuation need not enter an
equilibrium chain: exact cubic and Lambert-W models have finite regular
sheets, including infinitely many distinct finite sheets in the latter
model.  The route must therefore preserve the coupled two-Julia relation
rather than assume finite-to-equilibrium descent.
The scalar holonomy now has an exact infinite-order monodromy multiplier,
and the reusable finite-root kernel forces its endpoint orbit to escape every
fixed polynomial root set.  New governed kernels derive the first
differential prolongation, prove exact root-multiplicity peeling for
`D_p=p(Y)d/dY`, and show that a degree-bounded triangular prolongation family
has no common root outside the equilibrium locus.  The remaining finite-route
step must identify the actual normalized coupled prolongations with that
triangular family and construct a nonzero endpoint elimination polynomial.
The global proposition must also lift the scalar loop iterates through the
selected two-flow factorization and turn a nonfinite iterate into the excluded
cross carrier.  These finite-branch tasks no longer exhaust the residual:
the infinite target-critical branch remains separate.
The previous compiler certificate omitted this route and treated cross-
carrier construction as part of a factorization-identity receipt.  That
receipt supplies neither proposition.  Consequently the exact equality
\(\sigma_{\rm ct}=2\)
remains a candidate theorem for this displayed family.  No conclusion about
the planar Jacobian conjecture or historical priority follows here.

## Exhaustive lower bound

Exact parity/divisor factorization gives two exhaustive branches for a
coefficientwise-polynomial schedule.

### No positive-contact coefficient

The schedule lies in the complete contact-zero lift algebra

\[
\mathcal L_0=\mathbb Q+(P^3,PQ,Q^2).
\]

The split critical coordinate

\[
J=B+\frac{3xA'+5A}{9}
\]

vanishes on every target-kernel factor.  Moving the Witt logarithm to the
target leaves an abelian source residual whose exact quadratic-field ODE has
no rational solution.  Its critical series therefore has infinite support.

For an arbitrary maximal polar prefix monomial \(s^{-h}x^d\), the tensor orbit
has only four possible positive resonant start exponents.  A fresh Newton
class from the infinite critical residual yields an infinite source orbit of
rate

\[
\frac{2d}{d-h}>2.
\]

Thus no finite supercritical prefix can lower the tail below two before the
descent reaches the zero-positive-face terminal.  Excluding that terminal
requires the finite/infinite target-critical dichotomy and the corresponding
Rees or twisted-clock schedule carrier.  See
[`gauge_pure_contact_zero_polar_tensor_induction_result.md`](gauge_pure_contact_zero_polar_tensor_induction_result.md).

### A positive-contact coefficient exists

Natural parameter order and finite contact depth give a least positive
occurrence.  Exact group factorization removes the complete lower
contact-zero connection before that layer is compared.  The all-depth
moving-backbone induction has only:

- a terminal source ray of limiting rate at least \(11/2\);
- a same-order source cancellation payment of rate at least two; or
- one exceptional uncharged face descent, followed by one of those charged
  outcomes.

The result holds over every coefficientwise-polynomial moving contact-zero
backbone, is invariant under shifts of the least index, and does not bill a
finite prefix as a tail occurrence.  See
[`gauge_least_positive_contact_moving_backbone_result.md`](gauge_least_positive_contact_moving_backbone_result.md).

Conditional on exclusion of both target-critical routes, the two branches establish

\[
\sigma_{\rm ct}\ge2.
\]

## Matching upper bound

The radial triangular staircase is an admissible pure contact-zero schedule.
It uses finite combinations of cone monomials \(P^aQ^b\), with \(b\ge1\),
\(a\le2b\), and the bare \(Q\) excluded.  These monomials belong to
\((PQ,Q^2)\subset\mathcal L_0\).  The exact moving two-layer identity, radial
semigroup division, and normal-layer Rees induction give

\[
\deg Y_q\le2q+1,
\qquad
\deg X_{\Omega_q^{\rm tgt}}\le q+1.
\]

Hence \(\sigma_{\rm ct}\le2\).  The finite staircase replay is an orientation
and coefficient stress test; the rate-two conclusion comes from the
all-order induction, not its observed finite Newton slope.  See
[`gauge_cone_radial_triangular_staircase_result.md`](gauge_cone_radial_triangular_staircase_result.md).

## Replay and formal carriers

[`gauge_unrestricted_tail_minimax.py`](gauge_unrestricted_tail_minimax.py)
re-runs and binds the two lower certificates, the typed source/target
round trips of the upper construction, the common schedule category, and
the exhaustive branch partition.  Its proof-carrying composition interface
contains no caller-supplied exhaustiveness, compatibility, all-order,
prefix-uniformity, or admissibility Booleans.  Instead, a content-bound tail
context names the category, statistic, and compiler-owned occurrence order,
and exactly three authority-typed receipts bind the two lower theorems and
the admissible upper construction.  The compiler derives the zero-or-least-
positive partition from the natural-number lexicographic order and rejects
missing, duplicate, finite-window, wrong-context, or tampered evidence.

The historical composition replay has semantic identity

```text
tail_minimax_certificate_sha256 =
24bee337068d65d8d81d1fa4ac584cec1130e3b160bef765f5afbd131acc1108
```

and its historical evidence envelope has identity

```text
proof_contract_sha256 =
270c91a82e642bb832cff6863ab8c9291f15f3be5e1109b6ff9f751e019a0e4c
```

These hashes identify the earlier compiler output; they are not evidence for
the missing schedule dichotomy or either carrier construction.  The
arithmetic and logical carriers used by the conditional composition are
kernel-checked in:

- [`AxiomPackJacobianPolarTensorInductionArithmetic.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianPolarTensorInductionArithmetic.lean);
- [`AxiomPackJacobianMovingBackboneInductionArithmetic.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianMovingBackboneInductionArithmetic.lean);
- [`AxiomPackJacobianConeRadialStaircaseArithmetic.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianConeRadialStaircaseArithmetic.lean); and
- [`AxiomPackJacobianTailMinimaxComposition.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianTailMinimaxComposition.lean).

The Python certificates own the Jacobian-specific algebraic identities,
factorizations, support theorems, and category adapters.  The Lean files own
the universal resonance, Newton, rate, well-order, and bound-composition
arithmetic.  The local-germ kernel additionally excludes a fully constructed
critical two-Julia nonfinite carrier.  No current layer constructs that
carrier from every selected global two-flow factorization, converts the
finite all-order prolongation inconsistency into the required visible-endpoint
polynomial, or constructs the infinite-support twisted-clock carrier from an
actual strict schedule.  Local existence and overlap uniqueness hold at
every finite state, while the finite-sheet countermodels show why that local
theorem alone cannot exclude finite monodromy.

## Literature position

The primary-source audit is recorded in
[`gauge_unrestricted_tail_minimax_literature_audit.md`](gauge_unrestricted_tail_minimax_literature_audit.md).
Its calibrated conclusion is:

- the factor-two valuation is an exact calculation for this normalized
  family using standard ramification/valuation principles;
- classical Magnus, D-log, formal-flow, Witt-module, and volume-preserving
  equivalence literature supplies nearby machinery but not the declared
  source/target degree-rate optimization; and
- no audited source states the candidate all-schedule value
  \(\sigma_{\rm ct}=2\) or this map-specific combined polar/contact
  obstruction.

This is evidence that the narrow candidate theorem was absent from the
sources checked, not evidence that its remaining continuation theorem holds
or that priority is established.  The July/August 2026 record is moving
quickly and specialist review remains required.
