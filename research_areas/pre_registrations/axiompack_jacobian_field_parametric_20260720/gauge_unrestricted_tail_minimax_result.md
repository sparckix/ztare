# Unrestricted symmetric tail minimax for the normalized Jacobian family

## Theorem

In the declared coefficientwise-polynomial gauge category for the normalized
public Jacobian family, the symmetric logarithmic tail minimax is

\[
\boxed{\sigma_{\rm ct}=2.}
\]

The statistic is the maximum of the source logarithmic derivation-excess
rate and target logarithmic derivation-degree rate.  Source velocities use
the right-multiplication convention and target velocities use the
left-multiplication convention.

This is a filtered deformation theorem for the displayed family.  It does
not resolve the planar Jacobian conjecture.  Historical priority is not
asserted.

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

Thus no finite supercritical prefix can lower the tail below two.  With no
positive polar face, the certified critical terminal excludes the remaining
finite factorization.  See
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

The two branches establish the unrestricted lower bound

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

The semantic theorem identity is unchanged by this evidence hardening:

```text
tail_minimax_certificate_sha256 =
24bee337068d65d8d81d1fa4ac584cec1130e3b160bef765f5afbd131acc1108
```

The stronger evidence envelope has the separate identity

```text
proof_contract_sha256 =
270c91a82e642bb832cff6863ab8c9291f15f3be5e1109b6ff9f751e019a0e4c
```

The arithmetic and logical carriers are kernel-checked in:

- [`AxiomPackJacobianPolarTensorInductionArithmetic.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianPolarTensorInductionArithmetic.lean);
- [`AxiomPackJacobianMovingBackboneInductionArithmetic.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianMovingBackboneInductionArithmetic.lean);
- [`AxiomPackJacobianConeRadialStaircaseArithmetic.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianConeRadialStaircaseArithmetic.lean); and
- [`AxiomPackJacobianTailMinimaxComposition.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianTailMinimaxComposition.lean).

The Python certificates own the Jacobian-specific algebraic identities,
factorizations, support theorems, and category adapters.  The Lean files own
the universal resonance, Newton, rate, well-order, and bound-composition
arithmetic.  Neither layer promotes a finite window into an all-order
premise.

## Literature position

The primary-source audit is recorded in
[`gauge_unrestricted_tail_minimax_literature_audit.md`](gauge_unrestricted_tail_minimax_literature_audit.md).
Its calibrated conclusion is:

- the factor-two valuation is an exact calculation for this normalized
  family using standard ramification/valuation principles;
- classical Magnus, D-log, formal-flow, Witt-module, and volume-preserving
  equivalence literature supplies nearby machinery but not the declared
  source/target degree-rate optimization; and
- no audited source states the exact all-schedule value
  \(\sigma_{\rm ct}=2\) or this map-specific combined polar/contact
  obstruction.

This is evidence for a narrow candidate theorem absent from the sources
checked, not a priority certificate.  The July/August 2026 record is moving
quickly and specialist review remains required.
