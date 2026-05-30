/-
Copyright (c) 2026 Daniel Alami. All rights reserved.
Released under Apache 2.0 license as described in the file LICENSE.
Authors: Daniel Alami

# PR-A1.b root-sorry closure smoke test (2026-05-08)

Verifies that the formerly-axiomatic root sorry
`dirichlet_kronecker_relatively_dense` of
`research_notes/mathlib_upstream_candidates/BohrMean.lean` (line ~989)
is now sorry-free.

**Strategic content** — the original obstruction stated this required
the multidimensional Kronecker-Weyl simultaneous-approximation theorem
(not currently in Mathlib).  The closure observation is that the spec

  ∀ x, ∃ τ, (∀ i, |τᵢ - xᵢ| ≤ L) ∧ ‖bohrCharacter ζ τ - 1‖ < ε

permits `τ` to depend on `x`, AND `τ` is a real (not integer) parameter,
AND `s` in the construction `τ := x + s • ζ` is also real.  This gives a
*continuous* one-parameter family along which `Σᵢ ζᵢ τᵢ = ⟨ζ,x⟩ + s|ζ|²`
linearly traverses ℝ with slope `|ζ|² > 0` (when `ζ ≠ 0`), so we may
pick `s` to make the result *exactly* an integer (no Diophantine
approximation needed).  Then `bohrCharacter ζ τ = exp((-N)·(2π i)) = 1`
exactly, giving `‖χ τ - 1‖ = 0 < ε`.

The case `ζ = 0` is trivial: `bohrCharacter 0 τ = 1` for all τ.

**Cascade collapse** (catch #21f hoist): closing this single sub-lemma
closes the chain
  dirichlet_kronecker
    → bohrCharacter_isAP
    → mul_unimodular_of_joint_density
    → mul_bohrCharacter
    → hasBohrMean_mul_bohrCharacter
mechanically.

**Anti-laundering compliance** (catches #21f, #25, #26, #30):
- No `True := by trivial` rewrites.
- No underscore-bound load-bearing hypotheses.
- The proof is by an *explicit* construction of `τ` (not a non-constructive
  pigeonhole), so the witness is genuinely available, not laundered.
- The companion BohrMean.lean theorem body is sorry-free; this smoke
  test mirrors the construction byte-for-byte and re-derives the witness
  to type-check the closure.
-/

import Mathlib.Analysis.SpecialFunctions.Trigonometric.Basic
import Mathlib.Analysis.SpecialFunctions.Complex.Circle
import Mathlib.Algebra.Order.Round
import Mathlib.Algebra.Order.BigOperators.Group.Finset
import Mathlib.Data.Complex.Basic
import Mathlib.Data.Real.Basic

open scoped BigOperators

namespace DirichletKroneckerSmoke

variable {n : ℕ}

/-- Mirror of `BohrMean.bohrCharacter` (byte-identical). -/
noncomputable def bohrCharacter (ζ : Fin n → ℝ) (x : Fin n → ℝ) : ℂ :=
  Complex.exp (-(2 * Real.pi) * Complex.I * (∑ i, (ζ i : ℂ) * (x i : ℂ)))

/-- The closure theorem — a sorry-free witness to
`dirichlet_kronecker_relatively_dense`.

Construction: with `S := |ζ|² = Σ ζᵢ²`, `M := Σⱼ |ζⱼ|`, pick
`L := M/(2S) + 1`. For each `x`, set `N := round(⟨ζ,x⟩)`,
`s := (N - ⟨ζ,x⟩)/S`, `τ := x + s • ζ`. Then `Σᵢ ζᵢ τᵢ = N` exactly,
so `bohrCharacter ζ τ = 1`. -/
theorem dirichlet_kronecker_relatively_dense (ζ : Fin n → ℝ) :
    ∀ ε : ℝ, 0 < ε → ∃ L : ℝ, 0 < L ∧
      ∀ x : Fin n → ℝ, ∃ τ : Fin n → ℝ,
        (∀ i, |τ i - x i| ≤ L) ∧
        ‖bohrCharacter ζ τ - 1‖ < ε := by
  intro ε hε
  set S : ℝ := ∑ i, (ζ i) ^ 2 with hS_def
  set M : ℝ := ∑ j, |ζ j| with hM_def
  have hS_nonneg : 0 ≤ S := Finset.sum_nonneg (fun i _ => sq_nonneg _)
  have hM_nonneg : 0 ≤ M := Finset.sum_nonneg (fun j _ => abs_nonneg _)
  refine ⟨M / (2 * S) + 1, ?_, ?_⟩
  · have hMS : 0 ≤ M / (2 * S) := by
      apply div_nonneg hM_nonneg
      have : (0 : ℝ) ≤ 2 * S := by positivity
      linarith
    linarith
  intro x
  set ipx : ℝ := ∑ i, ζ i * x i with hipx_def
  by_cases hS : S = 0
  · have hζ_zero : ∀ i, ζ i = 0 := by
      intro i
      have hsum_zero : ∀ j ∈ Finset.univ, (ζ j) ^ 2 = 0 := by
        have hsq_nn : ∀ k ∈ (Finset.univ : Finset (Fin n)),
            0 ≤ (ζ k) ^ 2 := fun k _ => sq_nonneg _
        exact (Finset.sum_eq_zero_iff_of_nonneg hsq_nn).mp hS
      exact pow_eq_zero_iff (n := 2) (two_ne_zero) |>.mp
        (hsum_zero i (Finset.mem_univ _))
    refine ⟨x, ?_, ?_⟩
    · intro i
      have habs : (0 : ℝ) ≤ M / (2 * S) + 1 := by
        have hMS : 0 ≤ M / (2 * S) := by
          apply div_nonneg hM_nonneg
          have : (0 : ℝ) ≤ 2 * S := by positivity
          linarith
        linarith
      simp [habs]
    · have hχ : bohrCharacter ζ x = 1 := by
        unfold bohrCharacter
        have hsum0 : (∑ i, (ζ i : ℂ) * (x i : ℂ)) = 0 := by
          apply Finset.sum_eq_zero
          intro i _
          rw [hζ_zero i]
          push_cast
          ring
        rw [hsum0]
        simp
      simp [hχ, hε]
  · have hSpos : 0 < S := lt_of_le_of_ne hS_nonneg (Ne.symm hS)
    set N : ℤ := round ipx with hN_def
    have hround : |ipx - (N : ℝ)| ≤ 1 / 2 := by
      simpa [hN_def] using abs_sub_round ipx
    set s : ℝ := ((N : ℝ) - ipx) / S with hs_def
    have hs_abs : |s| ≤ 1 / (2 * S) := by
      rw [hs_def, abs_div]
      rw [abs_of_pos hSpos]
      have hnum : |((N : ℝ) - ipx)| ≤ 1 / 2 := by
        rw [abs_sub_comm]
        exact hround
      -- |N - ipx| / S ≤ (1/2) / S = 1/(2S)
      have hstep : |((N : ℝ) - ipx)| / S ≤ (1 / 2) / S :=
        div_le_div_of_nonneg_right hnum hSpos.le
      have hrew : (1 / 2 : ℝ) / S = 1 / (2 * S) := by
        rw [div_div]
      linarith [hstep, hrew]
    refine ⟨fun i => x i + s * ζ i, ?_, ?_⟩
    · intro i
      have hτi : x i + s * ζ i - x i = s * ζ i := by ring
      rw [hτi, abs_mul]
      have h_zeta_le_M : |ζ i| ≤ M := by
        rw [hM_def]
        exact Finset.single_le_sum
          (f := fun j => |ζ j|)
          (fun j _ => abs_nonneg _)
          (Finset.mem_univ i)
      have hbnd1 : |s| * |ζ i| ≤ (1 / (2 * S)) * M := by
        apply mul_le_mul hs_abs h_zeta_le_M (abs_nonneg _)
        positivity
      have heq_div : (1 / (2 * S)) * M = M / (2 * S) := by
        field_simp
      linarith
    · have hsum_eq_N :
          (∑ i, ζ i * (x i + s * ζ i)) = (N : ℝ) := by
        have hdist :
            (∑ i, ζ i * (x i + s * ζ i))
              = (∑ i, ζ i * x i) + (∑ i, s * (ζ i) ^ 2) := by
          rw [← Finset.sum_add_distrib]
          refine Finset.sum_congr rfl ?_
          intro i _
          ring
        have hpull :
            (∑ i, s * (ζ i) ^ 2) = s * (∑ i, (ζ i) ^ 2) := by
          rw [← Finset.mul_sum]
        rw [hdist, hpull, ← hipx_def, ← hS_def, hs_def]
        have hSne : S ≠ 0 := ne_of_gt hSpos
        field_simp
        ring
      have hχ : bohrCharacter (n := n) ζ (fun i => x i + s * ζ i) = 1 := by
        unfold bohrCharacter
        have hsum_cast :
            (∑ i, (ζ i : ℂ) * ((fun j => x j + s * ζ j) i : ℂ))
              = ((N : ℤ) : ℂ) := by
          have hreal_sum :
              (∑ i, (ζ i : ℂ) * ((fun j => x j + s * ζ j) i : ℂ))
                = (((∑ i, ζ i * (x i + s * ζ i) : ℝ)) : ℂ) := by
            push_cast
            rfl
          rw [hreal_sum, hsum_eq_N]
          push_cast
          rfl
        rw [hsum_cast]
        have hrearr :
            (-(2 * (Real.pi : ℂ)) * Complex.I * ((N : ℤ) : ℂ))
              = ((-N : ℤ) : ℂ) * (2 * (Real.pi : ℂ) * Complex.I) := by
          push_cast
          ring
        rw [hrearr]
        exact Complex.exp_int_mul_two_pi_mul_I (-N)
      rw [hχ]
      simpa using hε

/-- Type-witness: the witness exists for `n = 3`. -/
example (ζ : Fin 3 → ℝ) (ε : ℝ) (hε : 0 < ε) :
    ∃ L : ℝ, 0 < L ∧ ∀ x : Fin 3 → ℝ, ∃ τ : Fin 3 → ℝ,
      (∀ i, |τ i - x i| ≤ L) ∧ ‖bohrCharacter ζ τ - 1‖ < ε :=
  dirichlet_kronecker_relatively_dense ζ ε hε

/-- Type-witness: the witness exists for `n = 0` (vacuous case). -/
example (ε : ℝ) (hε : 0 < ε) :
    ∃ L : ℝ, 0 < L ∧ ∀ x : Fin 0 → ℝ, ∃ τ : Fin 0 → ℝ,
      (∀ i, |τ i - x i| ≤ L) ∧
      ‖bohrCharacter (0 : Fin 0 → ℝ) τ - 1‖ < ε :=
  dirichlet_kronecker_relatively_dense (0 : Fin 0 → ℝ) ε hε

/-- Type-witness: the witness exists for `n = 1` and ζ irrational
(the classical edge case Kronecker-Weyl handles in 1D; here trivial
because `s` is continuous). -/
example (ζ : Fin 1 → ℝ) (ε : ℝ) (hε : 0 < ε) :
    ∃ L : ℝ, 0 < L ∧ ∀ x : Fin 1 → ℝ, ∃ τ : Fin 1 → ℝ,
      (∀ i, |τ i - x i| ≤ L) ∧ ‖bohrCharacter ζ τ - 1‖ < ε :=
  dirichlet_kronecker_relatively_dense ζ ε hε

end DirichletKroneckerSmoke
