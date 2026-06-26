# Finite one-period asset pricing — no arbitrage from state prices (FTAP, easy direction)

The first tractable slice of the finance shortlist (the Fundamental Theorem of Asset Pricing). The full FTAP says
a finite one-period market is arbitrage-free **if and only if** there is a strictly positive state-price (risk-
neutral) vector pricing every asset. This blueprint targets the **easy direction** — *state prices ⇒ no
arbitrage* — which is elementary (a sum rearrangement plus a positivity argument) and self-contained on Mathlib
(`Finset` sums over `Fin n`, ordered-field arithmetic, `Finset.sum_pos`). The hard direction (no arbitrage ⇒ such
prices exist) is the Farkas / hyperplane-separation slice and comes later. Probe Mathlib with Loogle and the warm
checker; cite the existing `Finset` sum API. Build only a small market scaffold if it genuinely helps.

Assumption-accounting note: the conclusion should depend on the state prices being **strictly** positive — a
merely nonnegative state-price vector does not force the contradiction. Surface that dependence honestly.

## Theory file
ftap_theory.lean

## Target
Consider a one-period market with finitely many states and finitely many assets. Asset i has a real payoff D(i, s)
in state s and a real price p(i). Suppose there is a strictly positive state-price vector q — one real number
q(s) > 0 per state — that prices every asset, meaning p(i) equals the sum over states s of q(s) · D(i, s). Then
the market admits no arbitrage: there is no portfolio (a real holding θ(i) per asset) whose cost, the sum over
assets i of θ(i) · p(i), is at most zero, whose payoff in every state s, the sum over assets i of θ(i) · D(i, s),
is at least zero, and whose payoff is strictly positive in at least one state. Equivalently, any portfolio that
is nonnegative in every state and strictly positive in some state must cost strictly more than zero.

## Lemmas
- **(cost equals state-price-weighted payoff)** Under the pricing hypothesis p(i) = Σ_s q(s)·D(i, s), the cost of
  any portfolio θ, Σ_i θ(i)·p(i), equals the state-price-weighted total payoff Σ_s q(s)·(Σ_i θ(i)·D(i, s)) — i.e.
  Σ_s q(s) · payoff(s), obtained by substituting the prices and exchanging the order of the two finite sums.
- **(no-arbitrage from strict positivity)** If every state payoff Σ_i θ(i)·D(i, s) is ≥ 0 and at least one is
  > 0, then with all q(s) > 0 the state-price-weighted total Σ_s q(s)·payoff(s) is strictly positive; combined
  with the cost identity above, the cost is strictly positive, so no such cost-≤-0 arbitrage portfolio exists.

## Idea
The whole argument is: cost = Σ_i θ(i)·p(i) = Σ_i θ(i)·(Σ_s q(s)·D(i, s)) = Σ_s q(s)·(Σ_i θ(i)·D(i, s)) =
Σ_s q(s)·payoff(s). Each summand q(s)·payoff(s) is ≥ 0 (q(s) > 0, payoff(s) ≥ 0), and the strictly-positive state
contributes a strictly positive term, so by `Finset.sum_pos` (or `Finset.sum_lt_sum`) the weighted total is > 0,
contradicting cost ≤ 0. The order-exchange step is `Finset.sum_comm` together with `Finset.mul_sum` /
`Finset.sum_mul`. No bespoke theory is required, but a tiny `OnePeriodMarket` structure (states, assets, payoff,
price) may be defined if it makes the statement cleaner — keep any built definition faithful (a market whose
fields are the literal payoff/price data, not a shell that trivializes the claim). Decompose as the kernel
teaches; a non-closure is an honest gap, never a fake closure.
