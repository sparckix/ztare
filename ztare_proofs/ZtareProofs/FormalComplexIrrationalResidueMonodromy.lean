import Mathlib.Analysis.SpecialFunctions.Complex.Log
import Mathlib.Tactic

/-!
# Infinite-order monodromy from an irrational logarithmic residue

The only input is that a complex residue is not the cast of a rational
number.  The kernel of the complex exponential then rules out every positive
torsion power of its scalar monodromy multiplier.
-/

namespace FormalComplexIrrationalResidueMonodromy

open Complex Real

/-- A complex value does not come from the rational subfield. -/
def IrrationalResidue (residue : ℂ) : Prop :=
  ∀ rational : ℚ, (rational : ℂ) ≠ residue

/-- Scalar monodromy attached to a logarithmic residue. -/
noncomputable def residueMonodromy (residue : ℂ) : ℂ :=
  Complex.exp (2 * π * I * residue)

/-- An irrational logarithmic residue gives a multiplier with no positive
torsion power. -/
theorem residueMonodromy_pow_ne_one
    (residue : ℂ) (hirrational : IrrationalResidue residue) :
    ∀ order : ℕ, 0 < order → residueMonodromy residue ^ order ≠ 1 := by
  intro order horder hpower
  have hexponential :
      Complex.exp ((order : ℂ) * (2 * π * I * residue)) = 1 := by
    rw [Complex.exp_nat_mul]
    exact hpower
  obtain ⟨period, hperiod⟩ :=
    Complex.exp_eq_one_iff.mp hexponential
  have htwoPiI : (2 * π * I : ℂ) ≠ 0 :=
    Complex.two_pi_I_ne_zero
  have hperiodReduced :
      (order : ℂ) * residue = (period : ℂ) := by
    apply mul_left_cancel₀ htwoPiI
    calc
      (2 * π * I) * ((order : ℂ) * residue) =
          (order : ℂ) * (2 * π * I * residue) := by ring
      _ = (period : ℂ) * (2 * π * I) := hperiod
      _ = (2 * π * I) * (period : ℂ) := by ring
  have horderNonzero : (order : ℂ) ≠ 0 := by
    exact_mod_cast (Nat.ne_of_gt horder)
  have hresidue : residue = (period : ℂ) / (order : ℂ) := by
    apply (eq_div_iff horderNonzero).2
    simpa [mul_comm] using hperiodReduced
  apply hirrational ((period : ℚ) / (order : ℚ))
  push_cast
  exact hresidue.symm

/-- Aggregated irrational-residue monodromy surface. -/
theorem complex_irrational_residue_monodromy_terminal_certificate :
    ∀ residue : ℂ,
      IrrationalResidue residue →
      ∀ order : ℕ, 0 < order →
        residueMonodromy residue ^ order ≠ 1 := by
  intro residue hirrational order horder
  exact residueMonodromy_pow_ne_one residue hirrational order horder

end FormalComplexIrrationalResidueMonodromy
