import Mathlib

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

-- candidate premises (semantic shelf, cosine-similar to goal):
-- Candidate lemma shelf (semantic retrieval context only; not a negative dictionary and not proof credit):
-- - [OWN-LEDGER cos=0.9632] PROVEN rung cost_eq_statePriceWeighted_payoff — a ~similar statement is ALREADY KERNEL-PROVEN in this repo's campaigns; cite/transport it, do not re-derive
--   proof to transport (kernel-verified; adapt the skeleton, do not assume it ports verbatim):
--   ```lean
--   import Mathlib
--
--
--
--   theorem cost_eq_statePriceWeighted_payoff : ∀ {nAssets nStates : Nat}
--       (D : Fin nAssets → Fin nStates → ℝ)
--       (p : Fin nAssets → ℝ)
--       (q : Fin nStates → ℝ)
--       (θ : Fin nAssets → ℝ)
--       (h_price : ∀ i : Fin nAssets, p i = ∑ s : Fin nStates, q s * D i s), (∑ i : Fin nAssets, θ i * p i) =
--         ∑ s : Fin nStates, q s * (∑ i : Fin nAssets, θ i * D i s) := by
--     intro nAssets nStates D p q θ h_price
--     calc
--       (∑ i : Fin nAssets, θ i * p i)
--           = ∑ i : Fin nAssets, θ i * (∑ s : Fin nStates, q s * D i s) := by
--             simp [h_price]
--       _ = ∑ s : Fin nStates, q s * (∑ i : Fin nAssets, θ i * D i s) := by
--             simp_rw [Finset.mul_sum]
--             rw [Finset.sum_comm]
--             congr with s
--             congr with i
--             ring
--
--   #print axioms cost_eq_statePriceWeighted_payoff
--   ```
--   preview: theorem cost_eq_statePriceWeighted_payoff : ∀ {nAssets nStates : Nat} (D : Fin nAssets → Fin nStates → ℝ) (p : Fin nAssets → ℝ) (q : Fin nStates → ℝ) (θ : Fin nAssets → ℝ) (h_price
-- - [OWN-LEDGER cos=0.8784] PROVEN rung statePriceWeighted_payoff_pos_of_strict_state_prices — a ~similar statement is ALREADY KERNEL-PROVEN in this repo's campaigns; cite/transport it, do not re-derive
--   proof to transport (kernel-verified; adapt the skeleton, do not assume it ports verbatim):
--   ```lean
--   import Mathlib
--
--
--
--   theorem statePriceWeighted_payoff_pos_of_strict_state_prices : ∀ {nAssets nStates : Nat}
--       (D : Fin nAssets → Fin nStates → ℝ)
--       (q : Fin nStates → ℝ)
--       (θ : Fin nAssets → ℝ)
--       (hq_pos : ∀ s : Fin nStates, 0 < q s)
--       (h_payoff_nonneg :
--         ∀ s : Fin nStates, 0 ≤ ∑ i : Fin nAssets, θ i * D i s)
--       (h_payoff_pos :
--         ∃ s : Fin nStates, 0 < ∑ i : Fin nAssets, θ i * D i s), 0 < ∑ s : Fin nStates, q s * (∑ i : Fin nAssets, θ i * D i s) := by
--     intro nAssets nStates D q θ hq_pos h_payoff_nonneg h_payoff_pos
--     classical
--     refine Finset.sum_pos' ?h_nonneg ?h_pos
--     · intro s _hs
--       exact mul_nonneg (le_of_lt (hq_pos s)) (h_payoff_nonneg s)
--     · rcases h_payoff_pos with ⟨s, hs⟩
--       exact ⟨s, Finset.mem_univ s, mul_pos (hq_pos s) hs⟩
--
--   #print axioms statePriceWeighted_payoff_pos_of_strict_state_prices
--   ```
--   preview: theorem statePriceWeighted_payoff_pos_of_strict_state_prices : ∀ {nAssets nStates : Nat} (D : Fin nAssets → Fin nStates → ℝ) (q : Fin nStates → ℝ) (θ : Fin nAssets → ℝ) (hq_pos : ∀
-- - [OWN-LEDGER cos=0.8720] PROVEN rung ftap_easy_no_arbitrage_from_state_prices — a ~similar statement is ALREADY KERNEL-PROVEN in this repo's campaigns; cite/transport it, do not re-derive
--   proof to transport (kernel-verified; adapt the skeleton, do not assume it ports verbatim):
--   ```lean
--   import Mathlib
--
--
--
--   theorem ftap_easy_no_arbitrage_from_state_prices : ∀ {nAssets nStates : Nat}
--       (D : Fin nAssets → Fin nStates → ℝ)
--       (p : Fin nAssets → ℝ)
--       (q : Fin nStates → ℝ)
--       (hq_pos : ∀ s : Fin nStates, 0 < q s)
--       (h_price : ∀ i : Fin nAssets, p i = ∑ s : Fin nStates, q s * D i s), ¬ ∃ θ : Fin nAssets → ℝ,
--         (∑ i : Fin nAssets, θ i * p i) ≤ 0 ∧
--         (∀ s : Fin nStates, 0 ≤ ∑ i : Fin nAssets, θ i * D i s) ∧
--         (∃ s : Fin nStates, 0 < ∑ i : Fin nAssets, θ i * D i s) := by
--     intro nAssets nStates D p q hq_pos h_price
--     rintro ⟨θ, h_cost_nonpos, h_payoff_nonneg, h_payoff_pos⟩
--     have h_cost_eq :
--         (∑ i : Fin nAssets, θ i * p i) =
--           ∑ s : Fin nStates, q s * (∑ i : Fin nAssets, θ i * D i s) := by
--       calc
--         (∑ i : Fin nAssets, θ i * p i)
--             = ∑ i : Fin nAssets, θ i * (∑ s : Fin nStates, q s * D i s) := by
--               simp [h_price]
--         _ = ∑ s : Fin nStates, q s * (∑ i : Fin nAssets, θ i * D i s) := by
--               simp_rw [Finset.mul_sum]
--               rw [Finset.sum_comm]
--               congr with s
--               congr with i
--               ring
--     have h_weighted_pos :
--         0 < ∑ s : Fin nStates, q s * (∑ i : Fin nAssets, θ i * D i s) := by
--       refine Finset.sum_pos' ?h_nonneg ?h_pos
--       · intro s _hs
--         exact mul_nonneg (le_of_lt (hq_pos s)) (h_payoff_nonneg s)
--       · rcases h_payoff_pos with ⟨s, hs⟩
--         exact ⟨s, Finset.mem_univ s, mul_pos (hq_pos s) hs⟩
--     have h_cost_pos : 0 < ∑ i : Fin nAssets, θ i * p i := by
--       rwa [← h_cost_eq] at h_weighted_pos
--     exact (not_le_of_gt h_cost_pos) h_cost_nonpos
--
--   #print axioms ftap_easy_no_arbitrage_from_state_prices
--   ```
--   preview: theorem ftap_easy_no_arbitrage_from_state_prices : ∀ {nAssets nStates : Nat} (D : Fin nAssets → Fin nStates → ℝ) (p : Fin nAssets → ℝ) (q : Fin nStates → ℝ) (hq_pos : ∀ s : Fin nSt
-- - [OWN-LEDGER cos=0.7653] PROVEN rung iso_lemma1 — a ~similar statement is ALREADY KERNEL-PROVEN in this repo's campaigns; cite/transport it, do not re-derive
--   preview: theorem iso_lemma1 : ∀ {ι : Type*} [Fintype ι] (claims : ClaimSchedule ι) (rank : ι → ℕ) (pool : NNReal), (∑ i, PariPassuWaterfallDistribution claims rank pool i) = ∑ k ∈ Finset.un
-- - [apn cos=0.7261] lemma explicit_sum_eq domain=quantum_optics @ 35.lean
--   preview: lemma explicit_sum_eq (v0 v1 v2 v3 v4 : ZMod 5) (f0 f1 f2 f3 f4 j : Fin 11) : v0 * explicit_A f0 j + v1 * explicit_A f1 j + v2 * explicit_A f2 j + v3 * explicit_A f3 j + v4 * expli
-- - [apn cos=0.7228] lemma sum_eval_2 domain=algebraic_geometry @ hilbert_functions_2.lean
--   preview: lemma sum_eval_2 (f : ℤ → ℤ) (d : ℤ) (c : ℕ) : ∑ m ∈ Finset.range (c + 1), (f (d - m) * f (d - (c:ℤ)) - f (d - m + 1) * f (d - (c:ℤ) - 1)) = (∑ m ∈ Finset.range (c + 1), f (d - m))
-- - [apn cos=0.7225] def pmSumN domain=quantum_optics @ MonochromaticQuantumGraph.lean
--   preview: def pmSumN {α : Type} [Semiring α] (N D : Nat) (W : WeightsN N D α) (ι : V N → Fin D) : α
-- - [mathlib cos=0.7126] lemma sum_mulVec_of_mem_colStochastic @ LinearAlgebra/Matrix/Stochastic.lean
--   preview: lemma sum_mulVec_of_mem_colStochastic {M : Matrix n n R} {x : n → R} (hA : M ∈ colStochastic R n) : ∑ i, (M *ᵥ x) i = ∑ i, x i := by simp only [Matrix.mulVec, dotProduct] rw [Finse
-- - [mathlib cos=0.7122] theorem arith_mean_weighted_of_constant @ Analysis/MeanInequalities.lean
--   preview: theorem arith_mean_weighted_of_constant (w z : ι → ℝ) (x : ℝ) (hw' : ∑ i ∈ s, w i = 1) (hx : ∀ i ∈ s, w i ≠ 0 → z i = x) : ∑ i ∈ s, w i * z i = x := calc ∑ i ∈ s, w i * z i = ∑ i ∈
-- - [mathlib cos=0.7107] theorem sumZeroes_sum @ Analysis/SpecialFunctions/Trigonometric/Chebyshev/ChebyshevGauss.lean
--   preview: theorem sumZeroes_sum (n : ℕ) {ι : Type*} (s : Finset ι) (P : ι → ℝ[X]) : sumZeroes n (∑ i ∈ s, P i) = ∑ i ∈ s, sumZeroes n (P i) := by simp_rw [sumZeroes, eval_finset_sum] rw [sum
-- Retrieval degradation notes: own_ledger: 75 texts pending embed (capped at 48/call)


theorem cost_eq_statePriceWeighted_payoff : ∀ {nAssets nStates : Nat}
    (D : Fin nAssets → Fin nStates → ℝ)
    (p : Fin nAssets → ℝ)
    (q : Fin nStates → ℝ)
    (θ : Fin nAssets → ℝ)
    (h_price : ∀ i : Fin nAssets, p i = ∑ s : Fin nStates, q s * D i s), (∑ i : Fin nAssets, θ i * p i) =
      ∑ s : Fin nStates, q s * (∑ i : Fin nAssets, θ i * D i s) := by
  ```
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
```
