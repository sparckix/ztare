import ZtareProofs.AxiomPackJacobianSeedPrefixQuotientArithmetic
import ZtareProofs.AxiomPackJacobianMovingPoissonSectionArithmetic

/-!
Arithmetic carrier for the paired transfer cost of a minimum-section cusp
defect.

For residue-one inputs `m = 3*p+1`, `n = 3*q+1`, this module records the
exact relations among

* `j = p+q-3`,
* defect weight `w = m+n-5`,
* source curve exponent `w-4`,
* strict source-field degree `2*(w-4)-1`, and
* target defect degree `j+3`.

The target leading monomial is represented by the existing exponent-pair
carrier `(3,j)`; no polynomial or cusp-map model is duplicated here.

The Hamiltonian product-rule calculation on the cusp, existence and
minimality of the weighted-volume source lift, and excitation of these
defects by the full moving family remain pencil arguments.
-/

namespace AxiomPackJacobianPairedCuspDefectTransferArithmetic

open AxiomPackJacobianMovingPoissonSectionArithmetic

/-- Exponent of `Y` in the defect `D*Y^j`. -/
def defectJ (p q : ℕ) : ℕ :=
  p + q - 3

/-- Cusp weight of the bracket defect. -/
def defectWeight (p q : ℕ) : ℕ :=
  (3 * p + 1) + (3 * q + 1) - 5

/-- Exponent of the exported source curve velocity. -/
def sourceExponent (p q : ℕ) : ℕ :=
  defectWeight p q - 4

/-- Degree of the canonical strict source field. -/
def sourceFieldDegree (p q : ℕ) : ℕ :=
  2 * sourceExponent p q - 1

/-- Derivation excess of the canonical strict source field. -/
def sourceDerivationExcess (p q : ℕ) : ℕ :=
  2 * sourceExponent p q - 2

/-- Leading target monomial `X^3*Y^j` in `D*Y^j`. -/
def targetLeadingExponent (p q : ℕ) : ExponentPair :=
  ⟨3, defectJ p q⟩

/-- Ordinary degree of the target defect. -/
def targetDefectDegree (p q : ℕ) : ℕ :=
  ordinaryDegree (targetLeadingExponent p q)

/-- Rational scalar `(q-p)/3` multiplying the defect. -/
def defectScalar (p q : ℕ) : ℚ :=
  (((q : ℤ) - (p : ℤ) : ℤ) : ℚ) / 3

theorem defect_j_positive
    (p q : ℕ) (hp : 2 ≤ p) (hq : 2 ≤ q) :
    1 ≤ defectJ p q := by
  simp only [defectJ]
  omega

theorem defect_weight_eq
    (p q : ℕ) (hp : 2 ≤ p) (hq : 2 ≤ q) :
    defectWeight p q = 3 * defectJ p q + 6 := by
  simp only [defectWeight, defectJ]
  omega

theorem source_exponent_eq
    (p q : ℕ) (hp : 2 ≤ p) (hq : 2 ≤ q) :
    sourceExponent p q =
      defectWeight p q - 4 ∧
    sourceExponent p q =
      3 * defectJ p q + 2 := by
  constructor
  · rfl
  · rw [sourceExponent, defect_weight_eq p q hp hq]
    omega

theorem source_exponent_in_strict_range
    (p q : ℕ) (hp : 2 ≤ p) (hq : 2 ≤ q) :
    5 ≤ sourceExponent p q := by
  rw [(source_exponent_eq p q hp hq).2]
  have hj := defect_j_positive p q hp hq
  omega

theorem source_field_degree_eq
    (p q : ℕ) (hp : 2 ≤ p) (hq : 2 ≤ q) :
    sourceFieldDegree p q =
      2 * (defectWeight p q - 4) - 1 ∧
    sourceFieldDegree p q =
      2 * defectWeight p q - 9 := by
  constructor
  · rfl
  · simp only [sourceFieldDegree, sourceExponent]
    have hw : 9 ≤ defectWeight p q := by
      rw [defect_weight_eq p q hp hq]
      have hj := defect_j_positive p q hp hq
      omega
    omega

theorem target_defect_degree_eq
    (p q : ℕ) :
    targetDefectDegree p q = defectJ p q + 3 := by
  simp [targetDefectDegree, targetLeadingExponent, ordinaryDegree]
  omega

theorem target_defect_weight_eq
    (p q : ℕ) (hp : 2 ≤ p) (hq : 2 ≤ q) :
    weight (targetLeadingExponent p q) = defectWeight p q := by
  simp only [targetLeadingExponent, weight]
  rw [defect_weight_eq p q hp hq]
  omega

theorem target_degree_weight_identity
    (p q : ℕ) (hp : 2 ≤ p) (hq : 2 ≤ q) :
    3 * (defectJ p q + 3) = defectWeight p q + 3 := by
  rw [defect_weight_eq p q hp hq]
  omega

theorem defect_scalar_ne_zero
    (p q : ℕ) (hpq : p ≠ q) :
    defectScalar p q ≠ 0 := by
  apply div_ne_zero
  · have hqp : (q : ℤ) ≠ (p : ℤ) := by
      exact_mod_cast (Ne.symm hpq)
    have hsub : (q : ℤ) - (p : ℤ) ≠ 0 :=
      sub_ne_zero.mpr hqp
    exact_mod_cast hsub
  · norm_num

theorem parameter_order_transfer
    (p q N : ℕ)
    (horder : defectWeight p q = N + 5) :
    sourceFieldDegree p q = 2 * N + 1 ∧
    sourceDerivationExcess p q = 2 * N := by
  simp only [sourceFieldDegree, sourceDerivationExcess,
    sourceExponent]
  omega

/-- Terminal arithmetic certificate for the paired cusp-defect transfer. -/
theorem paired_cusp_defect_transfer_arithmetic_terminal_certificate :
    (∀ p q : ℕ, 2 ≤ p → 2 ≤ q →
      defectWeight p q = 3 * defectJ p q + 6 ∧
      sourceExponent p q = defectWeight p q - 4 ∧
      sourceExponent p q = 3 * defectJ p q + 2 ∧
      5 ≤ sourceExponent p q ∧
      sourceFieldDegree p q =
        2 * (defectWeight p q - 4) - 1 ∧
      sourceFieldDegree p q =
        2 * defectWeight p q - 9 ∧
      targetDefectDegree p q = defectJ p q + 3 ∧
      weight (targetLeadingExponent p q) = defectWeight p q ∧
      3 * (defectJ p q + 3) = defectWeight p q + 3) ∧
    (∀ p q : ℕ, p ≠ q → defectScalar p q ≠ 0) ∧
    (∀ p q N : ℕ, defectWeight p q = N + 5 →
      sourceFieldDegree p q = 2 * N + 1 ∧
      sourceDerivationExcess p q = 2 * N) := by
  refine ⟨?_, defect_scalar_ne_zero, parameter_order_transfer⟩
  intro p q hp hq
  exact ⟨defect_weight_eq p q hp hq,
    (source_exponent_eq p q hp hq).1,
    (source_exponent_eq p q hp hq).2,
    source_exponent_in_strict_range p q hp hq,
    (source_field_degree_eq p q hp hq).1,
    (source_field_degree_eq p q hp hq).2,
    target_defect_degree_eq p q,
    target_defect_weight_eq p q hp hq,
    target_degree_weight_identity p q hp hq⟩

end AxiomPackJacobianPairedCuspDefectTransferArithmetic
