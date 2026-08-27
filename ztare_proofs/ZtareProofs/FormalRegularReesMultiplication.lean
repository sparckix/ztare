import Mathlib.Tactic
import ZtareProofs.FormalDiagonalReesPolynomial

/-!
# Multiplication under regular Rees regrading

The diagonal regrading is multiplicative precisely on the nonpositive
support cone.  The proof is coefficientwise and retains the complete nested
power series in both the spatial and Rees variables.
-/

namespace ZtareProofs.FormalRegularReesMultiplication

open Polynomial PowerSeries
open ZtareProofs.FormalDiagonalReesPolynomial

noncomputable section

variable {R : Type*} [CommRing R]

/-- A row schedule has no monomial above its parameter-order diagonal. -/
def NonpositiveSupport (rows : ℕ → R[X]) : Prop :=
  ∀ parameterOrder spatialDegree,
    parameterOrder < spatialDegree →
      (rows parameterOrder).coeff spatialDegree = 0

/-- Parameter Cauchy product of two polynomial row schedules. -/
def cauchyRows (left right : ℕ → R[X]) : ℕ → R[X] :=
  fun parameterOrder =>
    ∑ pair ∈ Finset.antidiagonal parameterOrder,
      left pair.1 * right pair.2

/-- The complete regular Rees transform preserves a parameter Cauchy
product when both factors have nonpositive support. -/
theorem regularReesGerm_cauchyRows
    (left right : ℕ → R[X])
    (hleft : NonpositiveSupport left)
    (hright : NonpositiveSupport right) :
    regularReesGerm (cauchyRows left right) =
      regularReesGerm left * regularReesGerm right := by
  ext spatialDegree reesOrder
  simp only [regularReesGerm, cauchyRows, PowerSeries.coeff_mk,
    PowerSeries.coeff_mul]
  simp only [Polynomial.finset_sum_coeff, Polynomial.coeff_mul,
    map_sum, PowerSeries.coeff_mul, PowerSeries.coeff_mk]
  rw [← Finset.sum_product', ← Finset.sum_product']
  let full :=
    (Finset.antidiagonal (spatialDegree + reesOrder)).product
      (Finset.antidiagonal spatialDegree)
  let admissible := full.filter fun pair =>
    pair.2.1 ≤ pair.1.1 ∧ pair.2.2 ≤ pair.1.2
  let source :=
    (Finset.antidiagonal spatialDegree).product
      (Finset.antidiagonal reesOrder)
  let fullTerm : ((ℕ × ℕ) × (ℕ × ℕ)) → R := fun pair =>
    (left pair.1.1).coeff pair.2.1 *
      (right pair.1.2).coeff pair.2.2
  let sourceTerm : ((ℕ × ℕ) × (ℕ × ℕ)) → R := fun pair =>
    (left (pair.1.1 + pair.2.1)).coeff pair.1.1 *
      (right (pair.1.2 + pair.2.2)).coeff pair.1.2
  change (∑ pair ∈ full, fullTerm pair) =
    ∑ pair ∈ source, sourceTerm pair
  have restrictToAdmissible :
      (∑ pair ∈ admissible, fullTerm pair) =
        ∑ pair ∈ full, fullTerm pair := by
    apply Finset.sum_subset (Finset.filter_subset _ _)
    intro pair hfull hnot
    have hnotSupport :
        ¬ (pair.2.1 ≤ pair.1.1 ∧ pair.2.2 ≤ pair.1.2) := by
      intro hsupport
      exact hnot (Finset.mem_filter.mpr ⟨hfull, hsupport⟩)
    rcases not_and_or.mp hnotSupport with hleftDegree | hrightDegree
    · simp only [fullTerm, hleft pair.1.1 pair.2.1
        (Nat.lt_of_not_ge hleftDegree), zero_mul]
    · simp only [fullTerm, hright pair.1.2 pair.2.2
        (Nat.lt_of_not_ge hrightDegree), mul_zero]
  have reindex :
      (∑ pair ∈ source, sourceTerm pair) =
        ∑ pair ∈ admissible, fullTerm pair := by
    apply Finset.sum_bij
      (fun pair _ =>
        ((pair.1.1 + pair.2.1, pair.1.2 + pair.2.2), pair.1))
    · intro pair hpair
      rcases Finset.mem_product.mp hpair with ⟨hspatial, hrees⟩
      rw [Finset.mem_antidiagonal] at hspatial hrees
      apply Finset.mem_filter.mpr
      constructor
      · apply Finset.mem_product.mpr
        constructor
        · rw [Finset.mem_antidiagonal]
          change
            (pair.1.1 + pair.2.1) + (pair.1.2 + pair.2.2) =
              spatialDegree + reesOrder
          omega
        · rw [Finset.mem_antidiagonal]
          exact hspatial
      · exact ⟨Nat.le_add_right _ _, Nat.le_add_right _ _⟩
    · rintro ⟨⟨p, q⟩, ⟨u, v⟩⟩ hfirst
        ⟨⟨p', q'⟩, ⟨u', v'⟩⟩ hsecond hequal
      simp only [Prod.mk.injEq] at hequal
      rcases hequal with ⟨⟨hpu, hqv⟩, hpq⟩
      rcases hpq with ⟨rfl, rfl⟩
      have : u = u' ∧ v = v' := by omega
      rcases this with ⟨rfl, rfl⟩
      rfl
    · rintro ⟨⟨i, j⟩, ⟨p, q⟩⟩ hpair
      have hfilter :
          ((i, j), (p, q)) ∈ full ∧ p ≤ i ∧ q ≤ j := by
        simpa only [admissible, Finset.mem_filter] using hpair
      rcases hfilter with ⟨hfull, hp, hq⟩
      rcases Finset.mem_product.mp hfull with
        ⟨hparameter, hspatial⟩
      have hparameterEq : i + j = spatialDegree + reesOrder := by
        simpa only [Finset.mem_antidiagonal] using hparameter
      have hspatialEq : p + q = spatialDegree := by
        simpa only [Finset.mem_antidiagonal] using hspatial
      refine ⟨((p, q), (i - p, j - q)), ?_, ?_⟩
      · apply Finset.mem_product.mpr
        constructor
        · rw [Finset.mem_antidiagonal]
          exact hspatialEq
        · rw [Finset.mem_antidiagonal]
          change (i - p) + (j - q) = reesOrder
          omega
      · simp only [Prod.mk.injEq]
        exact ⟨⟨Nat.add_sub_of_le hp, Nat.add_sub_of_le hq⟩,
          trivial⟩
    · intro pair hpair
      rfl
  rw [← restrictToAdmissible, ← reindex]

end

end ZtareProofs.FormalRegularReesMultiplication
