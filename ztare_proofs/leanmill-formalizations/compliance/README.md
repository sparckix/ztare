# Compliance — machine-checked formalizations

Kernel-verified Lean 4 + Mathlib formalizations of contractual and regulatory logic, produced by
[LeanMill](../../../docs/concepts/leanmill_architecture.md) from a natural-language blueprint. Unlike the
mathematically clean results elsewhere in this library, a covenant is a *contested-spec* domain: proving a
property is easy, and the hard, valuable part is a faithful formalization of ambiguous legal prose. These files
demonstrate the apparatus on exactly that.

## Contents

### `RestrictedPaymentsCovenant.lean` — a high-yield restricted-payments covenant
`restricted_payments_permission_safety_invariants`. The permission logic of Section 4.07 of a public high-yield
note indenture (Chattem, Inc., SEC EDGAR `a2039699zex-4_2.txt`): a Restricted Payment (dividend, buyback,
junior-debt prepayment, restricted investment) is permitted only when **all three** conditions hold — (a) no
Default is continuing, (b) the pro-forma Fixed Charge Coverage Ratio test admits at least $1.00 of additional
debt, and (c) the payment, with all prior Restricted Payments, stays **strictly** under the builder basket
(50% of cumulative Consolidated Net Income plus add-ins, net of the clause (ii)/(iii)/(iv) carve-outs).

From the blueprint's natural-language directive, the apparatus **abstracted the accounting itself**: `NoDefault`,
`FCCRTestPasses`, `builderBasket`, `cumulativeRP`, and `amount` are opaque parameters, and the covenant is
carried as an `↔` hypothesis. Over that, it proves two safety invariants:

1. **Default block.** A continuing Default forbids every Restricted Payment, whatever the coverage or basket
   headroom (`¬ NoDefault s → ¬ Permitted s rp`).
2. **Basket exhaustion.** Once prior Restricted Payments reach the builder basket, no further positive payment
   is permitted until the basket grows (`builderBasket s ≤ cumulativeRP s → 0 < amount rp → ¬ Permitted s rp`).

Each invariant depends on the faithful structure: the default block on the three-way `∧`, the basket exhaustion
on the strict `<`. A `∨` or a `≤` misreading would make one of them false. `#print axioms` =
`[propext, Classical.choice, Quot.sound]`, no `sorry`, firewall-faithful, kernel-ratified.

### `RestrictedPaymentsFaithfulness.lean` — the faithfulness certificate
**Hand-authored** (not an autonomous closure — the header says so), kernel-checked. It shows *why* the faithful
permission logic is load-carrying by refuting each plausible misreading with a concrete distinguishing witness:

| Laundered reading | Permits a transaction that… | Witness |
|---|---|---|
| `∧ → ∨` | a company **in default** may still distribute | `NoDefault=False, FCCR=True`, basket 1, prior 0, amount 0 |
| dropped-(c) | **overspends** the builder basket | `(a),(b)` hold, basket 1, prior 1, amount 1 |
| `< → ≤` | lands **exactly at** the basket ceiling | `(a),(b)` hold, basket 1, prior 0, amount 1 |

Each row is a kernel-checked theorem: the laundered reading permits the transaction, the faithful covenant
forbids it. This is the mechanized version of "here is the payment the misreading waves through" — a
distinguishing input, proved rather than asserted.

The natural-language input is
[`restricted_payments_covenant_blueprint.md`](../blueprints/restricted_payments_covenant_blueprint.md).

## Why "compliance" (and the honest boundary)

This is contractual logic, not mathematics: the value is in the faithful translation of a real covenant, and the
proofs are short. The apparatus abstracts the accounting from a natural-language instruction and proves the
covenant's safety properties; the faithfulness certificate shows the cost of getting the translation wrong. The
boundary the whole library discloses applies here too, sharply: the kernel certifies that the invariants follow
from the covenant as formalized, not that the abstraction level (opaque accounting) or the clause reading is the
one a court would adopt. That reading is the human's, argued in the blueprint; the logic's faithfulness is
machine-checked.

### Definitions

The vocabulary these theorems are stated over — read them to check the faithfulness boundary; each is documented at the top of its file.

**`BaselLeverageRatio.lean`**
- `TotalExposureMeasure (x : ExposureComponents K) : K`
- `RiskWeightInRange (w : K) : Prop` — Effective average risk weight lies in the Basel range `[0,1]`.
- `LowRiskWeightCrossover (w : K) : Prop` — The crossover regime where the 8% risk-weighted floor does not dominate the 3% flat floor.
- `RiskWeightedExposure (exposure w : K) : K` — Risk-weighted assets from total exposure and effective risk weight.
- `LeverageCompliant (tier1 exposure : K) : Prop` — Basel leverage-ratio compliance: Tier-1 capital is at least 3% of total exposure.
- `RiskWeightedCapitalFloor (tier1 exposure w : K) : Prop`

**`RestrictedPaymentsFaithfulness.lean`**
- `Permitted (noDefault fccrPass : Prop) (builderBasket cumulativeRP amount : ℝ) : Prop` — Faithful covenant permission: (a) ∧ (b) ∧ (c), with (c) a STRICT basket inequality.
- `Permitted_or (noDefault fccrPass : Prop) (builderBasket cumulativeRP amount : ℝ) : Prop` — Laundered `∧→∨`: permit on ANY one condition.
- `Permitted_dropC (noDefault fccrPass : Prop) (_builderBasket _cumulativeRP _amount : ℝ) : Prop` — Laundered dropped-(c): omit the builder-basket cap entirely.
- `Permitted_le (noDefault fccrPass : Prop) (builderBasket cumulativeRP amount : ℝ) : Prop` — Laundered `<→≤`: allow a payment landing exactly at the basket.
