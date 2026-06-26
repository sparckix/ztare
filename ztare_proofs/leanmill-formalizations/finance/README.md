# Finance — machine-checked formalizations

Kernel-verified Lean 4 + Mathlib formalizations of finance results, produced end-to-end by
[LeanMill](../../../docs/concepts/leanmill_architecture.md) from natural-language blueprints (through the
faithfulness firewall: each statement compiles, is non-trivial, and is round-trip faithful to the NL; each proof
is independently kernel-ratified with a matched-negative-control receipt and an axiom audit). Every file is
self-contained (`import Mathlib`) and carries a GENERATED provenance header (outcome, axioms, real elapsed,
phases, reuse) emitted by `promote_campaign_artifact.py` — not hand-authored.

> **Time accounting (honest wall).** Headers report **`campaign span`** = real elapsed (last − first attempt),
> the honest wall; **`cost-to-closure total`** = summed active-solve time only (smaller — it omits formalization,
> Mathlib imports, warm-env builds, and inter-attempt gaps). For a milestone worked across several re-runs, the
> `milestone` line reports the combined real span across the family.

## Contents

### `FtapEasy.lean` — Fundamental Theorem of Asset Pricing (easy direction)
In a one-period market with finitely many assets and states: if a **strictly positive** state-price vector `q`
prices every asset (`p i = ∑ s, q s · D i s`), then there is **no arbitrage**. The cornerstone of asset pricing —
the bridge from "no free lunch" to "price = discounted expected payoff." Lean status was a confirmed gap; this is
the elementary half (the hard direction is the Farkas/separation slice). 3 theorems, axiom-clean. Assumption
accounting is explicit: strict positivity of `q` is load-bearing, and the market is frictionless (no bid–ask
spread). [roadmap §4.1]

### `constant_product_amm.lean` — constant-product AMM temporal + no-arbitrage invariants
`constantProductAMM_temporal_invariant_and_no_roundTrip_profit`. For an `x·y = k` pool with fee `γ ∈ (0,1]`:
the product `k` **never decreases** across any adversarial finite trade sequence, and a single round-trip returns
**at most** the input (strictly less with a real fee `γ < 1`). The pool is safe against the curve. Proven fresh
(no reuse) over `NNReal` reserves; real elapsed ≈ 5.1h.

### `amm_no_cyclic_arbitrage.lean` — no round-trip arbitrage at ANY reachable state
`no_history_enables_round_trip_arbitrage`. The DeFi-security companion to the above: **no trade history**
(flash-loan / sandwich / cyclic path) ever maneuvers the pool into a state where a round-trip becomes profitable —
at every state reachable by any finite prior sequence, a round-trip in either direction returns at most the input,
strictly less under a real fee. **A deliberate compounding demonstration:** it *cites* the banked constant-product
rungs (`executeTrades_keep_wellFormed`, the `roundTrip…_le_input` / `…_lt_input_of_real_fee` lemmas) rather than
re-deriving them — the new content is the quantification over reachable states. Axiom-clean. (Filed run closed by
reusing those rungs; the genuine no-cyclic proving + the engine remediation it surfaced span ~1.3h active across
the campaign family, atop the ~5.1h constant-product foundation.)

### `corporate_waterfall_absolute_priority.lean` — Absolute Priority Rule (APR) waterfall
`waterfallDistribution_feasible_of_linearOrder`. Capital-structure / bankruptcy claim priority: under a strict
ranking of claims, the absolute-priority waterfall distribution is feasible — senior claims paid before any junior
claim receives anything, subject to the available estate. Domain-stamped `finance`.

### `corporate_waterfall_pari_passu_apr.lean` — pari-passu + APR
`pariPassuWaterfallDistribution_feasible_and_ranked_absolutePriority`. Extends the waterfall to **pari-passu**
(equal-ranking) tranches: the distribution is feasible AND respects ranked absolute priority across tranches with
pro-rata sharing within a tranche.

## Provenance & trust

- **Autoformalized, not hand-written** — the NL blueprint was the operator input; the apparatus produced the Lean
  statements + proofs, gated by the faithfulness firewall.
- **Kernel-ratified + axiom-clean** — every filed theorem is an independently ratified closure; `#print axioms`
  reports only `propext`, `Classical.choice`, `Quot.sound` and **no `sorryAx`** (verify per file below).

## Verify it yourself

From a Lean project with Mathlib on the toolchain:

```
lake env lean <file>.lean
```

It should elaborate with no errors and print the axiom audit (standard axioms only).
