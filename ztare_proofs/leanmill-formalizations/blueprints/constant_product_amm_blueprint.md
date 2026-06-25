# Constant-product AMM — the invariant holds across ANY adversarial trade sequence

The formal core of an automated market maker (AMM): a liquidity pool holds reserves of two tokens and lets
anyone swap one for the other along a fixed curve. For a constant-product market maker the curve is `x · y = k`,
and the substantive safety property is not about one trade but about TIME: as users execute a SEQUENCE of trades
— in any order, any sizes, either direction, chosen adversarially — the product invariant `k = x·y` must never
DECREASE, and the pool must never be drained (reserves stay strictly positive). With a real trading fee the
invariant strictly grows (the fee accrues to liquidity providers), so no adversary can extract value from the
pool by trading against it. This is a temporal / inductive guarantee over a transaction sequence, not a
single-trade check — the property a kernel-checked proof should certify and a fuzz test cannot. None of this
vocabulary is in Mathlib — theory-building. A non-closure is an honest gap, never a fake closure, and never a
silent restriction.

## Domain
formalization-nonmath

## Theory file
amm_constant_product.lean

The bespoke vocabulary Mathlib lacks — establish each once, over `NNReal` (nonnegative reals), and never "prove"
a definition:
- **Pool state** — a pair of token reserves `(x, y)`. A pool is WELL-FORMED when both reserves are strictly
  positive (the regime in which the swap curve is defined and the pool is alive).
- **Fee factor** — a number `γ` with `0 < γ ≤ 1`: the fraction of the input that trades against the curve
  (`γ = 1` is the feeless boundary; a real pool has `γ < 1`, e.g. `0.997`). The fee is taken on the INPUT.
- **Trade** — a direction (swap X-for-Y, or swap Y-for-X) together with a nonnegative input amount.
- **Swap transition** — applying a trade to a pool yields the new pool, via the constant-product-with-fee rule
  (the standard Uniswap-v2 rule, fee on the input). Define it for BOTH directions.
- **Product invariant** — `k(pool) = x · y`.

## Idea
(Advisory planner context — a tractability steer, NOT a formalization mandate.) Keep this the ELEMENTARY
constant-product model over `NNReal` with an EXPLICIT swap formula; do NOT reach for a general convex / CFMM
invariant over Mathlib's `Convex`/order-theoretic machinery (faithful but proof-intractable). The load-bearing
identity that keeps it tractable and sidesteps `NNReal` truncated subtraction: for an X-for-Y swap of input `dx`
at fee `γ`, the new reserves are
    `x' = x + dx`,   `y' = x · y / (x + γ · dx)`
(derive `y'` in this closed form rather than as `y − dy`, so there is no subtraction). The product is then
    `k' = x' · y' = (x · y) · (x + dx) / (x + γ · dx) ≥ x · y = k`
because `γ ≤ 1` ⇒ `x + γ·dx ≤ x + dx` ⇒ the ratio is `≥ 1` (strict when `γ < 1` and `dx > 0`). The Y-for-X swap
is symmetric (`x'' = x·y / (y + γ·dy)`, `y'' = y + dy`). The local lever is `NNReal` division/`le_div` algebra —
the same family as the already-banked `nnreal_*` helpers, which may transfer. The TEMPORAL claim is structural
INDUCTION over a `List` of trades: if every single trade preserves "product non-decreasing AND reserves strictly
positive," then any finite sequence does — so the adversary's freedom to pick the order and sizes buys nothing.
Do NOT narrow: not feeless-only (`γ` must range over `0 < γ ≤ 1`, with `γ < 1` the real case), not one-direction
only (both X→Y and Y→X), not a single trade (the headline is the SEQUENCE), and reserves must stay STRICTLY
positive so the formula is well-defined and "the pool is not drained" has content (an empty/zero pool must NOT
make the statement vacuously true).

## Lemmas
(PINNED decomposition — the target-aligned shelf so the build is deterministic and reuses the already-proven
rungs, instead of re-inventing a fresh decomposition each run. Each is over a well-formed pool `p` with a fee
`γ ∈ (0,1]`; "real fee" means `γ < 1`.)
- **(swapXToY_wellFormed)** A single X→Y swap of any nonnegative `dx` preserves strict positivity of both reserves.
- **(swapYToX_wellFormed)** A single Y→X swap of any nonnegative `dy` preserves strict positivity of both reserves.
- **(swapXToY_product_mono)** A single X→Y swap does not decrease the constant product `k = reserveX · reserveY`.
- **(swapYToX_product_mono)** A single Y→X swap does not decrease the product `k`.
- **(swapXToY_product_strict_of_real_fee)** With a real fee (`γ < 1`) and positive input `dx`, an X→Y swap STRICTLY increases `k`.
- **(swapYToX_product_strict_of_real_fee)** With a real fee and positive input `dy`, a Y→X swap STRICTLY increases `k`.
- **(singleTradeInvariant)** Any single trade (either direction, any nonnegative amount) keeps the pool well-formed and does not decrease `k`.
- **(strictSingleTradeInvariant)** Any single trade with a real fee and positive input keeps the pool well-formed and STRICTLY increases `k`.
- **(executeTrades_keep_wellFormed)** Executing any finite sequence of trades preserves well-formedness throughout.
- **(executeTrades_product_mono)** Executing any finite sequence of trades does not decrease `k`.
- **(tradeSequenceInvariant)** THE HEADLINE: for any finite adversarial sequence of trades (arbitrary directions/amounts), the product after the whole sequence is at least the initial product and reserves stay strictly positive — no sequence drains the pool.
- **(roundTripXReturn_le_input)** An X round-trip (swap X→Y, then swap the proceeds Y→X) returns AT MOST the original input `dx`.
- **(roundTripXReturn_lt_input_of_real_fee)** With a real fee and positive `dx`, the X round-trip returns STRICTLY less than `dx`.
- **(roundTripYReturn_le_input)** A Y round-trip returns at most the original input `dy`.
- **(roundTripYReturn_lt_input_of_real_fee)** With a real fee and positive `dy`, the Y round-trip returns STRICTLY less than `dy`.

## Target
Over a constant-product pool with strictly-positive `NNReal` reserves and a fee `γ` with `0 < γ ≤ 1`, define the
fee-bearing swap (both directions) and prove BOTH:

1. **Per-trade invariant** — applying ANY single trade (either direction, any nonnegative input) to a
   well-formed pool yields a well-formed pool: the reserves stay strictly positive, and the product does not
   decrease (`k' ≥ k`), with a STRICT increase whenever the fee is real (`γ < 1`) and the input is positive.

2. **Temporal invariant — THE HEADLINE** — for ANY finite sequence of trades (arbitrary directions and amounts,
   chosen by an adversary in the worst order), the product after executing the whole sequence is at least the
   initial product (`k_final ≥ k_initial`), and the reserves remain strictly positive throughout. Equivalently:
   no sequence of trades can drain the pool or reduce its constant-product invariant. Prove by induction on the
   trade sequence.

3. **Adversarial corollary (prove if reachable; an honest gap here is acceptable)** — a round-trip (swap X→Y,
   then immediately swap the proceeds Y→X) returns AT MOST the original input, and strictly less when the fee is
   real (`γ < 1`): an adversary cannot profit by trading against the pool alone.

The result MUST hold for a real fee (`γ < 1`, not feeless-only), MUST cover BOTH swap directions, MUST be the
sequence-level claim (not merely a single trade), and MUST keep reserves strictly positive — do not assume the
pool is large enough for any particular trade, and do not let an empty/zero pool make any statement vacuously
true.
