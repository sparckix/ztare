import Mathlib.Analysis.SpecialFunctions.Complex.Log
import Mathlib.NumberTheory.Real.Irrational
import Mathlib.Tactic

/-!
# Irrational exponential periods have infinite multiplicative order

This is the substrate-neutral monodromy kernel used by the critical Puiseux
campaign.  It needs no transcendence theorem: a positive torsion power of
`exp (2 * pi * I * rho)` would put the real parameter `rho` in `ℚ` by the
period classification of the complex exponential.
-/

namespace FormalComplexMonodromyNonTorsion

/-- The scalar multiplier acquired from a logarithmic residue `rho`. -/
noncomputable def monodromyMultiplier (rho : ℝ) : ℂ :=
  Complex.exp ((2 * (Real.pi : ℂ) * Complex.I) * (rho : ℂ))

/-- An irrational real residue gives a multiplier with no positive torsion
power.  Positivity is explicit so the vacuous zeroth power is excluded. -/
theorem monodromyMultiplier_pow_ne_one
    (rho : ℝ) (hrho : Irrational rho) (N : ℕ) (hN : 0 < N) :
    monodromyMultiplier rho ^ N ≠ 1 := by
  intro htorsion
  have hexp :
      Complex.exp
          ((N : ℂ) *
            ((2 * (Real.pi : ℂ) * Complex.I) * (rho : ℂ))) = 1 := by
    rw [Complex.exp_nat_mul]
    exact htorsion
  obtain ⟨k, hk⟩ := Complex.exp_eq_one_iff.mp hexp
  have hscaled :
      ((N : ℂ) * (rho : ℂ)) *
          (2 * (Real.pi : ℂ) * Complex.I) =
        (k : ℂ) * (2 * (Real.pi : ℂ) * Complex.I) := by
    calc
      ((N : ℂ) * (rho : ℂ)) *
          (2 * (Real.pi : ℂ) * Complex.I) =
          (N : ℂ) *
            ((2 * (Real.pi : ℂ) * Complex.I) * (rho : ℂ)) := by ring
      _ = (k : ℂ) * (2 * (Real.pi : ℂ) * Complex.I) := hk
  have hcomplex : (N : ℂ) * (rho : ℂ) = (k : ℂ) :=
    mul_right_cancel₀ Complex.two_pi_I_ne_zero hscaled
  have hreal : (N : ℝ) * rho = (k : ℝ) := by
    simpa using congrArg Complex.re hcomplex
  have hN0 : (N : ℝ) ≠ 0 := by
    exact_mod_cast (Nat.ne_of_gt hN)
  have hrational : rho = (k : ℝ) / (N : ℝ) := by
    apply (eq_div_iff hN0).2
    simpa [mul_comm] using hreal
  exact hrho.ne_rational k (N : ℤ) (by simpa using hrational)

/-- Aggregated theorem-scoped surface for governed coverage receipts. -/
theorem complex_monodromy_non_torsion_terminal_certificate :
    ∀ rho : ℝ, Irrational rho →
      ∀ N : ℕ, 0 < N → monodromyMultiplier rho ^ N ≠ 1 := by
  exact monodromyMultiplier_pow_ne_one

end FormalComplexMonodromyNonTorsion
