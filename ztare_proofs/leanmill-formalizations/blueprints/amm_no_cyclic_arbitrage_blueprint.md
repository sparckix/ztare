# Constant-product AMM — no round-trip arbitrage at ANY reachable pool state

The DeFi-security companion to the constant-product temporal invariant. The headline theorem proved the POOL is
safe (the product `k = x·y` never decreases across any adversarial trade sequence). This proves the TRADER
cannot extract value, and — the new content — that this holds at EVERY state the pool can reach: no flash-loan,
sandwich, or cyclic trade PATH ever maneuvers the pool into a state where a round-trip becomes profitable. A
round-trip (swap a token out and immediately swap the proceeds back) returns AT MOST the input, and STRICTLY
less when the fee is real — at the initial pool, and after ANY prior trade history. The fee accrues to the pool
(`k` grows), so the trader strictly loses it; there is no closed loop against the curve alone that yields a
strictly positive risk-free return.

This target **reuses the already-proven constant-product theory** (`amm_constant_product.lean`), composing its
banked, kernel-clean rungs — the round-trip-≤-input lemmas (the per-state no-arbitrage) with the sequence
invariant (every reachable state is well-formed). The new content is the QUANTIFICATION over trade histories,
cited from those rungs, not re-derived. A deliberate compounding demonstration.

## Domain
formalization-nonmath

## Theory file
amm_constant_product.lean

This campaign EXTENDS the existing, proven constant-product theory — it must CITE its banked decls, never
restate them. Established vocabulary (do not re-define): `ConstantProductPool` (reserves over `NNReal`),
`PoolWellFormed`, `productInvariant`/`poolProduct`, `FeeFactor` (`γ` with `0 < γ ≤ 1`), `FeeIsReal` (`γ < 1`),
`Trade`, `applyTrade`, `executeTrades` (finite trade list folded over the pool), `swapXToY`/`swapYToX`,
`roundTripXReturn`/`roundTripYReturn`. The banked results to build on:
- `executeTrades_keep_wellFormed` — executing any finite trade list preserves well-formedness (strictly
  positive reserves) throughout; so every reachable pool is well-formed.
- `tradeSequenceInvariant` — for any finite trade list the pool stays well-formed and `productInvariant` does
  not decrease.
- `roundTripXReturn_le_input` / `roundTripYReturn_le_input` — at a well-formed pool, a single X (resp. Y)
  round-trip returns at most the input.
- `roundTripXReturn_lt_input_of_real_fee` / `roundTripYReturn_lt_input_of_real_fee` — with a real fee (`γ < 1`)
  and a positive input, the round-trip returns STRICTLY less than the input.

## Idea
(Advisory planner context — a tractability steer, not a mandate; the kernel still gates.) The per-state result
is banked: at a well-formed pool the round-trip loses (weakly always, strictly with a real fee). The new step is
to quantify over the pool a trader actually faces, which is `executeTrades γ p ts` for SOME prior history `ts`.
That pool is well-formed by `executeTrades_keep_wellFormed`, so the banked round-trip lemma applies to it
verbatim — `roundTripXReturn γ (executeTrades γ p ts) dx ≤ dx`. The proof is a one-step composition: instantiate
the banked round-trip lemma at the reachable pool, discharging its well-formedness hypothesis with
`executeTrades_keep_wellFormed`. Cover both directions and the strict real-fee case (cite the `_lt_…` rungs).
Keep `dx` arbitrary nonnegative (the weak bound) and `0 < dx` only for the strict bound, so neither statement is
vacuous: the strict real-fee round-trip with positive input is a genuine, non-empty case (the banked `_lt_…`
lemmas already exhibit it). Do not require the pool to RETURN to its initial reserves — with a real fee that
forces the trivial (zero-input) loop and the strict claim would be vacuous; the faithful object is the trader's
token round-trip, where the pool legitimately keeps the fee.

## Lemmas
- **(reachable_pool_wellFormed)** For any well-formed pool `p` and any finite trade list `ts`, the reached pool
  `executeTrades γ p ts` is well-formed (cite `executeTrades_keep_wellFormed`).
- **(roundTripX_le_input_at_reachable)** For any well-formed `p`, any history `ts`, and any `dx`, the X
  round-trip at the reached pool returns at most `dx`: `roundTripXReturn γ (executeTrades γ p ts) dx ≤ dx`
  (instantiate `roundTripXReturn_le_input` at the reachable pool via `reachable_pool_wellFormed`).
- **(roundTripY_le_input_at_reachable)** The Y-direction counterpart (cite `roundTripYReturn_le_input`).
- **(roundTripX_lt_input_at_reachable_real_fee)** With a real fee (`γ < 1`) and `0 < dx`, the X round-trip at any
  reachable pool returns STRICTLY less than `dx` (cite `roundTripXReturn_lt_input_of_real_fee`); and the Y
  counterpart.
- **(no_history_enables_round_trip_arbitrage)** THE HEADLINE: for every well-formed pool, every finite prior
  trade history, every direction, and every input, a round-trip at the reached pool returns at most the input —
  and strictly less when the fee is real and the input is positive. No trade path against the constant-product
  pool ever creates a round-trip that yields a strictly positive risk-free return.

## Target
Over a constant-product pool with strictly-positive `NNReal` reserves and a fee `γ` with `0 < γ ≤ 1`, prove that
NO TRADE HISTORY ENABLES ROUND-TRIP ARBITRAGE: for every well-formed initial pool, every finite prior sequence
of trades (arbitrary directions and amounts — a flash-loan / sandwich / cyclic path), and every subsequent
round-trip in EITHER direction, the round-trip returns AT MOST the original input — and STRICTLY less whenever
the fee is real (`γ < 1`) and the input is positive. Equivalently: at no state reachable by any trade path can a
trader close a loop against the pool for a strictly positive risk-free return. The result MUST cover both swap
directions, MUST hold for a real fee (not feeless-only), MUST keep reserves strictly positive throughout, and
MUST be non-vacuous (the strict real-fee, positive-input case is genuinely inhabited). It must CITE the banked
constant-product rungs (`executeTrades_keep_wellFormed`, the `roundTrip…_le_input` and `…_lt_input_of_real_fee`
lemmas), not re-derive them. A non-closure is an honest gap, never a fake closure.
