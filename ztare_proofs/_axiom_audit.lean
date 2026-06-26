import Mathlib

open Polynomial
open scoped BigOperators

-- candidate premises (semantic shelf, cosine-similar to goal):
-- Candidate lemma shelf (semantic retrieval context only; not a negative dictionary and not proof credit):
-- - [OWN-LEDGER cos=0.8712] PROVEN rung iso_lemma_map_split_denominator_product — a ~similar statement is ALREADY KERNEL-PROVEN in this repo's campaigns; cite/transport it, do not re-derive
--   proof to transport (kernel-verified; adapt the skeleton, do not assume it ports verbatim):
--   ```lean
--   import Mathlib
--
--   open Polynomial
--   open scoped BigOperators
--
--   theorem iso_lemma_map_split_denominator_product
--       {K : Type*} [Field K] {ι : Type*} [Fintype ι]
--       (num : K[X]) (a : ι → K) (m : ι → ℕ)
--       (hnum : num = ∏ j : ι, (X - C (a j)) ^ m j) :
--       algebraMap K[X] (FractionRing K[X]) num =
--         ∏ j : ι,
--           algebraMap K[X] (FractionRing K[X]) ((X - C (a j)) ^ m j) := by
--     simp_all
--   ```
--   preview: theorem iso_lemma_map_split_denominator_product {K : Type*} [Field K] {ι : Type*} [Fintype ι] (num : K[X]) (a : ι → K) (m : ι → ℕ) (hnum : num = ∏ j : ι, (X - C (a j)) ^ m j) : alg
-- - [OWN-LEDGER cos=0.8640] PROVEN rung iso_lemma_map_cleared_partial_fraction_identity — a ~similar statement is ALREADY KERNEL-PROVEN in this repo's campaigns; cite/transport it, do not re-derive
--   proof to transport (kernel-verified; adapt the skeleton, do not assume it ports verbatim):
--   ```lean
--   import Mathlib
--
--   open Polynomial
--   open scoped BigOperators
--
--   theorem iso_lemma_map_cleared_partial_fraction_identity
--       {K : Type*} [Field K] {ι : Type*} [Fintype ι] [DecidableEq ι]
--       (r : K[X]) (a : ι → K) (m : ι → ℕ) (s : ι → K[X])
--       (hclear :
--         r =
--           ∑ j : ι,
--             (s j) * (∏ i ∈ Finset.univ.erase j, (X - C (a i)) ^ m i)) :
--       algebraMap K[X] (FractionRing K[X]) r =
--         ∑ j : ι,
--           algebraMap K[X] (FractionRing K[X]) (s j) *
--             (∏ i ∈ Finset.univ.erase j,
--               algebraMap K[X] (FractionRing K[X]) ((X - C (a i)) ^ m i)) := by
--     simp_all
--   ```
--   preview: theorem iso_lemma_map_cleared_partial_fraction_identity {K : Type*} [Field K] {ι : Type*} [Fintype ι] [DecidableEq ι] (r : K[X]) (a : ι → K) (m : ι → ℕ) (s : ι → K[X]) (hclear : r
-- - [OWN-LEDGER cos=0.8063] PROVEN rung iso_lemma_map_polynomial_division_identity — a ~similar statement is ALREADY KERNEL-PROVEN in this repo's campaigns; cite/transport it, do not re-derive
--   preview: theorem iso_lemma_map_polynomial_division_identity {K : Type*} [Field K] (den num P r : K[X]) (hdiv : den = P * num + r) : algebraMap K[X] (FractionRing K[X]) den = algebraMap K[X]
-- - [OWN-LEDGER cos=0.7880] PROVEN rung iso_lemma_roots_multiset_to_distinct_count_product — a ~similar statement is ALREADY KERNEL-PROVEN in this repo's campaigns; cite/transport it, do not re-derive
--   preview: theorem iso_lemma_roots_multiset_to_distinct_count_product {K : Type*} [Field K] [DecidableEq K] (num : K[X]) : (num.roots.map fun a => X - C a).prod = ∏ a ∈ num.roots.toFinset, (X
-- - [mathlib cos=0.7188] lemma nnrpow_map_pi shapes=LE,POSITIVE @ Analysis/SpecialFunctions/ContinuousFunctionalCalculus/Rpow/Basic.lean
--   preview: lemma nnrpow_map_pi {c : ∀ i, C i} {x : ℝ≥0} (hc : ∀ i, 0 ≤ c i := by cfc_tac) : nnrpow c x = fun i => (c i) ^ x := by simp only [nnrpow_def] unfold nnrpow exact cfcₙ_map_pi (S :=
-- - [mathlib cos=0.7129] lemma cfc_polynomial @ Analysis/CStarAlgebra/ContinuousFunctionalCalculus/Unital.lean
--   preview: lemma cfc_polynomial (q : R[X]) (a : A) (ha : p a := by cfc_tac) : cfc q.eval a = aeval a q := by rw [cfc_map_polynomial .., cfc_id' ..] end Polynomial section Comp variable [Uniqu
-- - [mathlib cos=0.7110] lemma rpow_map_pi shapes=LE,POSITIVE @ Analysis/SpecialFunctions/ContinuousFunctionalCalculus/Rpow/Basic.lean
--   preview: lemma rpow_map_pi {c : ∀ i, C i} {x : ℝ} (hc : ∀ i, IsUnit (c i)) (hc' : ∀ i, 0 ≤ c i := by cfc_tac) : rpow c x = fun i => (c i) ^ x := by have hc'' : ∀ i, 0 ∉ spectrum ℝ≥0 (c i) :
-- - [mathlib cos=0.7097] lemma cfc_eval_C @ Analysis/CStarAlgebra/ContinuousFunctionalCalculus/Unital.lean
--   preview: lemma cfc_eval_C (r : R) (a : A) (ha : p a := by cfc_tac) : cfc (C r).eval a = algebraMap R A r := by simp [cfc_const r a]
-- - [apn cos=0.7089] lemma coeff_P_poly domain=oeis @ oeis_51293_conjecture_0.lean
--   preview: lemma coeff_P_poly (n k : ℕ) (ω : ℂ) : (P_poly n ω).coeff k = ∑ S ∈ (Finset.Icc 1 n).powerset.filter (fun S => S.card = k), ω ^ (S.sum id)
-- - [apn cos=0.7088] lemma sum_eval_1 domain=algebraic_geometry @ hilbert_functions_2.lean
--   preview: lemma sum_eval_1 (f : ℤ → ℤ) (d : ℤ) (c : ℕ) : ∑ m ∈ Finset.range c, (f d * f (d - m) - f (d + 1) * f (d - m - 1)) = f d * (∑ m ∈ Finset.range c, f (d - m)) - f (d + 1) * (∑ m ∈ Fi


theorem iso_lemma_fraction_expand_single_map_numerator {K : Type*} [Field K] (a : K) (m : ℕ) (c : ℕ → K) :
    algebraMap K[X] (FractionRing K[X])
        (∑ k ∈ Finset.Icc 1 m,
          C (c k) * (X - C a) ^ (m - k)) =
      ∑ k ∈ Finset.Icc 1 m,
        algebraMap K[X] (FractionRing K[X]) (C (c k)) *
          (algebraMap K[X] (FractionRing K[X]) (X - C a)) ^ (m - k) :=
by norm_num
#print axioms iso_lemma_fraction_expand_single_map_numerator
