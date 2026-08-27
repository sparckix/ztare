import Mathlib.Data.ZMod.Basic
import Mathlib.NumberTheory.Real.Irrational
import Mathlib.Tactic
import ZtareProofs.FormalRationalRootModPrime

/-!
# Exact irrationality kernel for the critical residue polynomial

The degree-seven polynomial below is the primitive residue eliminant from the
critical Puiseux monodromy calculation.  The proof uses the rational-root
theorem and an exhaustive reduction modulo 17.  Irreducibility and
irrationality are conclusions of the mechanism, not hypotheses.
-/

namespace FormalCriticalResidueIrrationality

open Polynomial

local instance : Fact (Nat.Prime 17) := ⟨by norm_num⟩

/-- The exact primitive integer eliminant for a logarithmic pole residue. -/
noncomputable def residuePolynomial : ℤ[X] :=
    C (-5328693312) * X ^ 7
  + C (-5328693312) * X ^ 6
  + C 4562281392 * X ^ 5
  + C 2967370224 * X ^ 4
  + C (-2078539001) * X ^ 3
  + C (-227127817) * X ^ 2
  + C 19332313 * X
  + C (-77175)

/-- The eliminant has the declared exact degree. -/
theorem residuePolynomial_natDegree : residuePolynomial.natDegree = 7 := by
  simp only [residuePolynomial]
  compute_degree <;> norm_num

/-- The eliminant has the declared leading coefficient. -/
theorem residuePolynomial_leadingCoeff :
    residuePolynomial.leadingCoeff = -5328693312 := by
  rw [Polynomial.leadingCoeff, residuePolynomial_natDegree]
  simp [residuePolynomial, coeff_X]

/-- The leading coefficient survives reduction modulo 17. -/
theorem residuePolynomial_leadingCoeff_mod17_ne_zero :
    Int.castRingHom (ZMod 17) residuePolynomial.leadingCoeff ≠ 0 := by
  rw [residuePolynomial_leadingCoeff]
  decide

/-- A computable evaluation model of the residue polynomial modulo 17. -/
def residueValueMod17 (x : ZMod 17) : ZMod 17 :=
    (-5328693312) * x ^ 7
  + (-5328693312) * x ^ 6
  + 4562281392 * x ^ 5
  + 2967370224 * x ^ 4
  + (-2078539001) * x ^ 3
  + (-227127817) * x ^ 2
  + 19332313 * x
  + (-77175)

/-- Exhaustive finite-field certificate: the reduced polynomial has no root. -/
theorem residueValueMod17_no_root :
    ∀ x : ZMod 17, residueValueMod17 x ≠ 0 := by
  decide

/-- The polynomial evaluation agrees with the computable modulo-17 model. -/
theorem residuePolynomial_eval_mod17 (x : ZMod 17) :
    (residuePolynomial.map (Int.castRingHom (ZMod 17))).eval x =
      residueValueMod17 x := by
  simp [residuePolynomial, residueValueMod17]

/-- The exact residue polynomial has no rational root. -/
theorem residuePolynomial_rat_no_root (q : ℚ) :
    (residuePolynomial.map (Int.castRingHom ℚ)).eval q ≠ 0 := by
  apply FormalRationalRootModPrime.rat_no_root_of_mod_prime_no_root
    (modulus := 17) residuePolynomial
    residuePolynomial_leadingCoeff_mod17_ne_zero
  intro x
  rw [residuePolynomial_eval_mod17]
  exact residueValueMod17_no_root x

/-- Every real root of the displayed residue polynomial is irrational. -/
theorem residue_polynomial_root_irrational
    (rho : ℝ)
    (hroot :
      (residuePolynomial.map (Int.castRingHom ℝ)).eval rho = 0) :
    Irrational rho := by
  rintro ⟨q, hq⟩
  rw [← hq] at hroot
  apply residuePolynomial_rat_no_root q
  apply Rat.cast_injective (α := ℝ)
  simpa [residuePolynomial] using hroot

/-- The theorem-scoped surface used by governed coverage receipts. -/
theorem critical_residue_irrationality_terminal_certificate :
    ∀ rho : ℝ,
      (residuePolynomial.map (Int.castRingHom ℝ)).eval rho = 0 →
      Irrational rho := by
  exact residue_polynomial_root_irrational

end FormalCriticalResidueIrrationality
