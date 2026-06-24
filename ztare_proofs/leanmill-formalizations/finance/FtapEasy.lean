/-
LeanMill campaign provenance — cost_eq_statePriceWeighted_payoff
The theorem(s) below are the VERBATIM machine-checked closure. This header is GENERATED from run
telemetry (run_tag=ftap_easy) by promote_campaign_artifact.py — not hand-authored.

  outcome     : closed · faithful · axioms [propext, Classical.choice, Quot.sound]
  domain      : finance
  time        : time-to-closure 336.46s (first 103.35s · p50 317.49s · p95 588.53s) · campaign span 588.53s (lead —s)
  compute     : cost-to-closure 170.21s mean · 241.67s total
  yield       : 3/9 attempts closed (3 failed)
  phases      : —
  reuse       : cited 0 banked rung(s)
  moves       : proposer_pool×3 · native_hammer×3 · claude_warm×3
-/
/-
Finite Fundamental Theorem of Asset Pricing — EASY direction (state prices ⇒ no arbitrage).

PROVENANCE. Autoformalized from natural-language notes by LeanMill (`autoformalize_from_notes`) on 2026-06-23 —
the Lean statements and proofs below were produced by the apparatus (NL → faithful Lean statement → governed
proof → kernel ratification), not hand-written. Each theorem is an independently kernel-ratified closure with a
matched-negative-control receipt and a `#print axioms` audit (standard Mathlib axioms only: `propext`,
`Classical.choice`, `Quot.sound` — no `sorryAx`). See README.md for the assumption accounting + roadmap link.

WHAT IT SAYS. In a one-period market with finitely many assets and states, if there is a STRICTLY positive
state-price vector `q` that prices every asset (`p i = ∑ s, q s * D i s`), then the market admits NO arbitrage:
no portfolio `θ` can have cost ≤ 0 while paying off ≥ 0 in every state and > 0 in some state.

ASSUMPTION ACCOUNTING (the LeanMill point). The conclusion genuinely needs `q s > 0` for EVERY state (strict
positivity), not merely `q s ≥ 0` — a nonnegative state-price vector does not force the contradiction. The kernel
confirms `hq_pos : ∀ s, 0 < q s` is used (via `mul_pos`).
-/
import Mathlib

/-- Lemma 1 (cost identity). Under the pricing hypothesis, a portfolio's cost equals the state-price-weighted
total payoff — by substituting prices and exchanging the order of the two finite sums. -/
theorem cost_eq_statePriceWeighted_payoff : ∀ {nAssets nStates : Nat}
    (D : Fin nAssets → Fin nStates → ℝ)
    (p : Fin nAssets → ℝ)
    (q : Fin nStates → ℝ)
    (θ : Fin nAssets → ℝ)
    (h_price : ∀ i : Fin nAssets, p i = ∑ s : Fin nStates, q s * D i s), (∑ i : Fin nAssets, θ i * p i) =
      ∑ s : Fin nStates, q s * (∑ i : Fin nAssets, θ i * D i s) := by
  intro nAssets nStates D p q θ h_price
  calc
    (∑ i : Fin nAssets, θ i * p i)
        = ∑ i : Fin nAssets, θ i * (∑ s : Fin nStates, q s * D i s) := by
          simp [h_price]
    _ = ∑ s : Fin nStates, q s * (∑ i : Fin nAssets, θ i * D i s) := by
          simp_rw [Finset.mul_sum]
          rw [Finset.sum_comm]
          congr with s
          congr with i
          ring

#print axioms cost_eq_statePriceWeighted_payoff

/-- Lemma 2 (strict positivity). With every state price strictly positive, a payoff that is ≥ 0 in every state
and > 0 in some state has a strictly positive state-price-weighted total. -/
theorem statePriceWeighted_payoff_pos_of_strict_state_prices : ∀ {nAssets nStates : Nat}
    (D : Fin nAssets → Fin nStates → ℝ)
    (q : Fin nStates → ℝ)
    (θ : Fin nAssets → ℝ)
    (hq_pos : ∀ s : Fin nStates, 0 < q s)
    (h_payoff_nonneg :
      ∀ s : Fin nStates, 0 ≤ ∑ i : Fin nAssets, θ i * D i s)
    (h_payoff_pos :
      ∃ s : Fin nStates, 0 < ∑ i : Fin nAssets, θ i * D i s), 0 < ∑ s : Fin nStates, q s * (∑ i : Fin nAssets, θ i * D i s) := by
  intro nAssets nStates D q θ hq_pos h_payoff_nonneg h_payoff_pos
  classical
  refine Finset.sum_pos' ?h_nonneg ?h_pos
  · intro s _hs
    exact mul_nonneg (le_of_lt (hq_pos s)) (h_payoff_nonneg s)
  · rcases h_payoff_pos with ⟨s, hs⟩
    exact ⟨s, Finset.mem_univ s, mul_pos (hq_pos s) hs⟩

#print axioms statePriceWeighted_payoff_pos_of_strict_state_prices

/-- THEOREM (FTAP, easy direction). A strictly positive state-price vector pricing every asset rules out
arbitrage: no portfolio is cost ≤ 0, payoff ≥ 0 everywhere, and payoff > 0 somewhere. -/
theorem ftap_easy_no_arbitrage_from_state_prices : ∀ {nAssets nStates : Nat}
    (D : Fin nAssets → Fin nStates → ℝ)
    (p : Fin nAssets → ℝ)
    (q : Fin nStates → ℝ)
    (hq_pos : ∀ s : Fin nStates, 0 < q s)
    (h_price : ∀ i : Fin nAssets, p i = ∑ s : Fin nStates, q s * D i s), ¬ ∃ θ : Fin nAssets → ℝ,
      (∑ i : Fin nAssets, θ i * p i) ≤ 0 ∧
      (∀ s : Fin nStates, 0 ≤ ∑ i : Fin nAssets, θ i * D i s) ∧
      (∃ s : Fin nStates, 0 < ∑ i : Fin nAssets, θ i * D i s) := by
  intro nAssets nStates D p q hq_pos h_price
  rintro ⟨θ, h_cost_nonpos, h_payoff_nonneg, h_payoff_pos⟩
  -- COMPOSED: cite the two proven lemmas above instead of re-deriving them inline (a true dependency graph).
  have h_cost_eq := cost_eq_statePriceWeighted_payoff D p q θ h_price
  have h_weighted_pos :=
    statePriceWeighted_payoff_pos_of_strict_state_prices D q θ hq_pos h_payoff_nonneg h_payoff_pos
  have h_cost_pos : 0 < ∑ i : Fin nAssets, θ i * p i := by
    rwa [← h_cost_eq] at h_weighted_pos
  exact (not_le_of_gt h_cost_pos) h_cost_nonpos

#print axioms ftap_easy_no_arbitrage_from_state_prices
