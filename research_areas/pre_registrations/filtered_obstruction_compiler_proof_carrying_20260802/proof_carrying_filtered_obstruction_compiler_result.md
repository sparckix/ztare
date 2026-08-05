# Proof-carrying filtered-obstruction compiler result

**Date:** 2026-08-02
**Status:** supported in the declared exact-evidence category

## Outcome

The filtered-obstruction subsystem now has content-bound premise identity
from adapter boundary to composed certificate.  The migrated problem inputs
contain zero Boolean premise fields.  A permanent reflection test enumerates
every `Filtered*Problem` dataclass and fails if a Boolean field returns.

The migration removed 29 caller truth fields across five theorem lifecycles:

| Lifecycle | Former Boolean premises | Replacement |
|---|---:|---|
| Exhaustive tail minimax | 8 | one tail context and three exact bound receipts |
| Split polar-tensor induction | 9 | one recognized representation and three proposition receipts |
| Asymptotic induction | 1 | one infinite-support receipt bound to the compiled transition graph |
| Single-/two-flow Puiseux pair | 6 | one shared germ context and four reusable propositions |
| Polar-Witt factorization | 5 | one recognized model and three proposition receipts |

This is a compression of propositions as well as types.  For example, the
three finite-face assertions in the former polar-Witt input are one
maximal-face decomposition theorem; the model identity does not manufacture
the separately required semidirect-quotient theorem.

## Identity architecture

`ztare.common.content_identity` now owns canonical JSON and SHA-256 content
identity.  LeanMill re-exports the same function, preserving its existing
wire hash.  `ztare.common.content_bound_evidence` owns proof-evidence
receipts.  The older `ztare.orchestrator.evidence_contract` continues to own
tabular evidence formats; module names and error classes are distinct.

Each proof receipt binds:

- claim identity;
- subject identity;
- context identity;
- authority lifecycle;
- mathematical scope;
- canonical conclusion; and
- source-evidence digest.

Composition rejects tampering, cross-context grafts, duplicate or missing
claims, claim substitution, finite scope, finite-experiment authority,
unknown models, wrong evidence owners, and insufficient rate arithmetic.

`formal_kernel` is deliberately absent from the caller-mintable authority
enum.  Kernel promotion must consume the existing LeanMill carried-theorem
ratification receipt in a later bridge; a string label cannot confer kernel
authority.

## Semantic identity preservation

The proof envelopes changed because they now include contexts and receipts.
The mathematical certificate digests remained fixed:

| Certificate | SHA-256 |
|---|---|
| Jacobian critical single-flow Puiseux | `6c3a97ebae223d4c0dbf6762d1399d242ea951459d3e7ae44255be2575931926` |
| Jacobian critical two-flow Puiseux | `190c7ff996246b663dc6ab94435aaea81fa8f8e4c009188badac06ec88bc963c` |
| Jacobian pure-contact polar tensor | `2790198e149ffbd07ef7e677c45fff7df2d4e539d02af9ce3081bb67ebdab632` |
| Jacobian least-positive asymptotic induction | `83ed836310d28e2468175866d8b74a18a1d6257e1de43309c93ed9635ea7110b` |
| Jacobian admissible staircase upper bound | `fd635b6d5250108ffceb46e7627c136ca47dd07686717d16fa937b3a2003ff71` |
| Jacobian unrestricted tail minimax | `24bee337068d65d8d81d1fa4ac584cec1130e3b160bef765f5afbd131acc1108` |

The global proof-contract digest is
`270c91a82e642bb832cff6863ab8c9291f15f3be5e1109b6ff9f751e019a0e4c`.
The new graph-bound least-positive proof envelope is
`e4b1e94132e3e054c5e06a9eb1cefe358360981e8011045e7944b99135055108`.

The invalid plain normal-two Jacobian polar-Witt adapter remains rejected
with `missing_semidirect_newton_quotient`; typed model identity did not erase
the missing invariant-module proposition.

## Transfer and rejection matrix

The tail composition theorem transfers unchanged to two unrelated fixtures:
a polynomial-degree tail and a valuation/support tail.  Independent alien
fixtures also pin the asymptotic, Puiseux, polar-Witt, and polar-tensor
semantic hashes.  Adversarial fixtures cover every identity and authority
edge introduced above.

The final focused matrix reports 155 Python tests passing.  The four relevant
Lean targets build across 8,316 jobs:

- `AxiomPackJacobianPolarTensorInductionArithmetic`;
- `AxiomPackJacobianMovingBackboneInductionArithmetic`;
- `AxiomPackJacobianConeRadialStaircaseArithmetic`; and
- `AxiomPackJacobianTailMinimaxComposition`.

Both source/right and target/left Magnus orientation harnesses pass their
forward-`dexp` round trips.  The corrected controlled-global replay reaches
order eight, and the moving-cone replay reaches its complete declared prefix.

## Jacobian claim boundary and literature

The unrestricted result is an all-order theorem for the normalized public
family and the declared coefficientwise-polynomial gauge category:

\[
\sigma_{\rm ct}=2.
\]

It is not a finite extrapolation.  The two lower branches are all-order and
uniform under arbitrary finite prefixes; the upper branch is an all-order
admissible staircase.  This does not resolve the planar Jacobian conjecture.

The accompanying primary-source audit did not find this gauge-minimax
statistic or theorem in the checked literature.  Historical priority remains
unestablished.  The valuation identity is a sharp normalized-family
calculation using standard ramification principles.

## Next-campaign selection rule

Boolean-premise debt is now zero, so the next score is

\[
(\text{unratified adapter receipts})
\times(\text{downstream semantic consumers})
\times(\text{branch criticality}).
\]

The first candidate is the kernel-ratification bridge: validate an existing
LeanMill carried-theorem receipt, bind its theorem/source/toolchain hashes to
a content-bound evidence receipt, and only then introduce a non-mintable
kernel authority.  The first Jacobian promotions should be the
least-positive infinite-support recurrence, the critical Puiseux germ, and
the radial-staircase arithmetic because together they touch every global
branch.  After that bridge, the same compiler can be applied to an alien
campaign selected by the same consequence-weighted score.
