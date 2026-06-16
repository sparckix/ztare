import Aesop

set_option maxHeartbeats 0

open BigOperators Real Nat Topology Rat

-- candidate premises (semantic shelf, cosine-similar to goal):
-- Candidate lemma shelf (semantic retrieval context only; not a negative dictionary and not proof credit):
-- - [OWN-LEDGER cos=0.7496] PROVEN rung mathd_algebra_125 — a ~similar statement is ALREADY KERNEL-PROVEN in this repo's campaigns; cite/transport it, do not re-derive
--   preview: theorem mathd_algebra_125 (x y : ℕ) (h₀ : 0 < x ∧ 0 < y) (h₁ : 5 * x = y) (h₂ : ↑x - (3 : ℤ) + (y - (3 : ℤ)) = 30) : x = 6
-- - [OWN-LEDGER cos=0.7478] PROVEN rung mathd_algebra_478 — a ~similar statement is ALREADY KERNEL-PROVEN in this repo's campaigns; cite/transport it, do not re-derive
--   preview: theorem mathd_algebra_478 (b h v : ℝ) (h₀ : 0 < b ∧ 0 < h ∧ 0 < v) (h₁ : v = 1 / 3 * (b * h)) (h₂ : b = 30) (h₃ : h = 13 / 2) : v = 65
-- - [OWN-LEDGER cos=0.7411] PROVEN rung mathd_algebra_141 — a ~similar statement is ALREADY KERNEL-PROVEN in this repo's campaigns; cite/transport it, do not re-derive
--   preview: theorem mathd_algebra_141 (a b : ℝ) (h₁ : a * b = 180) (h₂ : 2 * (a + b) = 54) : a ^ 2 + b ^ 2 = 369
-- - [OWN-LEDGER cos=0.7400] PROVEN rung mathd_algebra_362 — a ~similar statement is ALREADY KERNEL-PROVEN in this repo's campaigns; cite/transport it, do not re-derive
--   preview: theorem mathd_algebra_362 (a b : ℝ) (h₀ : a ^ 2 * b ^ 3 = 32 / 27) (h₁ : a / b ^ 3 = 27 / 4) : a + b = 8 / 3
-- - [apn cos=0.7277] lemma ratio_identity domain=oeis @ oeis_A258667_conjecture_0.lean
--   preview: lemma ratio_identity (n : ℕ) (h : 2 < n) : (n : ℝ) / (n - 2) = 1 + 2 / (n - 2)
-- - [apn cos=0.7178] lemma K_bounds domain=oeis @ oeis_227582_conjecture_0.lean
--   preview: lemma K_bounds (n : ℕ) (hn : 1 ≤ n) : (6 * (n : ℝ)^2 + 6 * (n : ℝ) - 5) / 5 ≤ (((6 * n^2 + 6 * n - 1) / 5 : ℕ) : ℝ) ∧ (((6 * n^2 + 6 * n - 1) / 5 : ℕ) : ℝ) ≤ (6 * (n : ℝ)^2 + 6 * (
-- - [apn cos=0.7122] lemma k_ineq domain=oeis @ oeis_a211417_conjecture_specific.lean
--   preview: lemma k_ineq (k : ℕ) (hk : k ≤ 29) : k / 2 + k / 3 + k / 5 ≤ k
-- - [mathlib cos=0.7107] theorem eq_of_xn_modEq_lem2 @ NumberTheory/PellMatiyasevic.lean
--   preview: theorem eq_of_xn_modEq_lem2 {n} (h : 2 * xn a1 n = xn a1 (n + 1)) : a = 2 ∧ n = 0 := by rw [xn_succ, mul_comm] at h have : n = 0 := n.eq_zero_or_pos.resolve_right fun np => _root_.
-- - [mathlib cos=0.7025] theorem xz_succ_succ @ NumberTheory/PellMatiyasevic.lean
--   preview: theorem xz_succ_succ (n) : xz a1 (n + 2) = (2 * a : ℕ) * xz a1 (n + 1) - xz a1 n := eq_sub_of_add_eq <| by delta xz; rw [← Int.natCast_add, ← Int.natCast_mul, xn_succ_succ]
-- - [mathlib cos=0.7005] theorem xn_modEq_x2n_add_lem @ NumberTheory/PellMatiyasevic.lean
--   preview: theorem xn_modEq_x2n_add_lem (n j) : xn a1 n ∣ d a1 * yn a1 n * (yn a1 n * xn a1 j) + xn a1 j := by have h1 : d a1 * yn a1 n * (yn a1 n * xn a1 j) + xn a1 j = (d a1 * yn a1 n * yn


theorem mathd_algebra_160  (n x : ℝ) (h₀ : n + x = 97) (h₁ : n + 5 * x = 265) : n + 2 * x = 139 := by
  linarith
#print axioms mathd_algebra_160
