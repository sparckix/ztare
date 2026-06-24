# FTAP (easy direction) — state prices ⇒ no arbitrage

A machine-checked formalization of the **easy direction of the finite Fundamental Theorem of Asset Pricing**,
produced end-to-end by [LeanMill](../../../docs/concepts/leanmill_architecture.md) from natural-language notes.
This is [§4.1 of the formalization roadmap](../../../docs/concepts/leanmill_formalization_roadmap.md) — the lead
achievable target of the finance shortlist.

- **Proof:** [`FtapEasy.lean`](./FtapEasy.lean) — one self-contained file, `import Mathlib`, 3 theorems.

## The theorem

In a one-period market with finitely many assets (`Fin nAssets`) and states (`Fin nStates`), with asset payoffs
`D i s : ℝ`, prices `p i : ℝ`, and a state-price vector `q s : ℝ`:

> If `q` is **strictly positive** (`∀ s, 0 < q s`) and prices every asset (`p i = ∑ s, q s · D i s`), then the
> market admits **no arbitrage** — there is no portfolio `θ` whose cost `∑ i, θ i · p i` is `≤ 0`, whose payoff
> `∑ i, θ i · D i s` is `≥ 0` in every state, and `> 0` in some state.

The argument: cost `= ∑ i, θ i · p i = ∑ s, q s · (∑ i, θ i · D i s)` (substitute prices, swap the two finite
sums), and that weighted total is strictly positive (every term `≥ 0`, one term `> 0`), contradicting cost `≤ 0`.

## Why it matters

The cornerstone of modern asset pricing — the bridge from "no free lunch" to "price = discounted expected
payoff," and finance's most-taught theorem. Its Lean status was a confirmed **gap** (no prior Mathlib/Lean
formalization found). The hard direction (no arbitrage ⇒ such prices exist) is the Farkas / hyperplane-separation
slice and comes later; this easy direction is the elementary half.

## Assumption accounting (the LeanMill differentiator)

The interest of the result *is* its assumption-sensitivity, and the kernel makes the dependence explicit and
minimal: the conclusion needs `q s > 0` for **every** state (strict positivity, used via `mul_pos`), not merely
`q s ≥ 0`. A nonnegative state-price vector does **not** force the contradiction. Finiteness is used through the
`Finset` sum API (`Finset.sum_comm`, `Finset.mul_sum`, `Finset.sum_pos'`).

**Frictionless-market scope (honest boundary).** Portfolios are `θ : Fin nAssets → ℝ` and the price is the exact
linear functional `∑ i, θ i · p i`. This bakes in a *frictionless* market: infinite divisibility, unbounded
short-selling, and **no bid–ask spread** (with spreads the cost is sublinear and the pricing equality becomes an
inequality). The theorem is the standard frictionless FTAP; relaxing this is future work. (Degenerate
`nStates = 0` / `nAssets = 0` instances are vacuously covered by the `∀` and are financially meaningless.)

## Provenance & trust

- **Autoformalized, not hand-written.** The NL blueprint was the operator input; the apparatus produced the Lean
  statements (through the faithfulness firewall: compiles, non-trivial, round-trip faithful) and all three proofs.
- **One hand edit (composition).** As originally produced, the target *re-derived* the two lemmas inline rather
  than citing them — a cohesion gap (the campaign proves each target as a standalone probe, so the shelf lemmas
  weren't in the target's compile scope to cite). The target proof here was hand-refactored to **cite** the two
  lemmas (`have h_cost_eq := cost_eq_statePriceWeighted_payoff …`); re-verified to compile and stay axiom-clean.
  The apparatus-level fix (prove the target with the proven shelf in scope so it composes automatically) is
  tracked separately.
- **Kernel-ratified.** Each of the 3 theorems is an independently ratified closure with a matched-negative-control
  receipt (`context_stripped`) and a passing governance kernel. Closure certificate timestamps: 2026-06-23.
- **Axiom-clean.** `#print axioms` (in the file) reports only the standard Mathlib axioms — `propext`,
  `Classical.choice`, `Quot.sound` — and **no `sorryAx`**. Every proof is sorry-free.

## Verify it yourself

From a Lean project with Mathlib on the toolchain:

```
lake env lean FtapEasy.lean
```

It should elaborate with no errors and print the three axiom audits (standard axioms only).
