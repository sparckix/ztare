import Mathlib.Algebra.Polynomial.Roots
import Mathlib.Tactic
import ZtareProofs.FormalComplexIrrationalResidueMonodromy

/-!
# Escape of an infinite monodromy orbit from finite polynomial roots

An irrational logarithmic residue gives a multiplier with no positive
torsion power.  Its nonzero scaled natural-power orbit is injective and
therefore cannot be contained in the finite root set of a nonzero
polynomial.
-/

namespace FormalComplexMonodromyFiniteRootEscape

open Complex Polynomial Set

open FormalComplexIrrationalResidueMonodromy

/-- A multiplier with no positive torsion power has an injective nonzero
scaled natural-power orbit. -/
theorem scaled_power_orbit_injective
    (multiplier base : ℂ)
    (hmultiplier : multiplier ≠ 0)
    (hbase : base ≠ 0)
    (hnoTorsion : ∀ order : ℕ, 0 < order → multiplier ^ order ≠ 1) :
    Function.Injective (fun order : ℕ ↦ multiplier ^ order * base) := by
  intro first second heq
  have hpowers : multiplier ^ first = multiplier ^ second := by
    exact mul_right_cancel₀ hbase heq
  by_contra hne
  rcases lt_or_gt_of_ne hne with hfirstSecond | hsecondFirst
  · have hpower : multiplier ^ (second - first) = 1 := by
      apply mul_left_cancel₀ (pow_ne_zero first hmultiplier)
      calc
        multiplier ^ first * multiplier ^ (second - first) =
            multiplier ^ second := by
          rw [← pow_add]
          congr
          omega
        _ = multiplier ^ first := hpowers.symm
        _ = multiplier ^ first * 1 := by simp
    exact hnoTorsion (second - first)
      (Nat.sub_pos_of_lt hfirstSecond) hpower
  · have hpower : multiplier ^ (first - second) = 1 := by
      apply mul_left_cancel₀ (pow_ne_zero second hmultiplier)
      calc
        multiplier ^ second * multiplier ^ (first - second) =
            multiplier ^ first := by
          rw [← pow_add]
          congr
          omega
        _ = multiplier ^ second := hpowers
        _ = multiplier ^ second * 1 := by simp
    exact hnoTorsion (first - second)
      (Nat.sub_pos_of_lt hsecondFirst) hpower

/-- The scalar orbit attached to an irrational residue escapes the root set
of every nonzero complex polynomial. -/
theorem exists_monodromy_iterate_polynomial_ne_zero
    (residue base : ℂ)
    (hirrational : IrrationalResidue residue)
    (hbase : base ≠ 0)
    (p : ℂ[X]) (hp : p ≠ 0) :
    ∃ order : ℕ,
      p.eval (residueMonodromy residue ^ order * base) ≠ 0 := by
  have hmultiplier : residueMonodromy residue ≠ 0 := by
    exact Complex.exp_ne_zero _
  have hinjective : Function.Injective
      (fun order : ℕ ↦ residueMonodromy residue ^ order * base) :=
    scaled_power_orbit_injective
      (residueMonodromy residue) base hmultiplier hbase
      (residueMonodromy_pow_ne_one residue hirrational)
  by_contra hescape
  push Not at hescape
  have horbitInfinite :
      (Set.range
        (fun order : ℕ ↦ residueMonodromy residue ^ order * base)).Infinite :=
    Set.infinite_range_of_injective hinjective
  have horbitSubset :
      Set.range
          (fun order : ℕ ↦ residueMonodromy residue ^ order * base) ⊆
        p.rootSet ℂ := by
    rintro value ⟨order, rfl⟩
    apply (Polynomial.mem_rootSet_of_ne hp).2
    simpa [Polynomial.aeval_def] using hescape order
  exact horbitInfinite ((p.rootSet_finite ℂ).subset horbitSubset)

/-- Aggregated finite-root escape surface. -/
theorem complex_monodromy_finite_root_escape_terminal_certificate :
    ∀ (residue base : ℂ),
      IrrationalResidue residue →
      base ≠ 0 →
      ∀ (p : ℂ[X]), p ≠ 0 →
        ∃ order : ℕ,
          p.eval (residueMonodromy residue ^ order * base) ≠ 0 := by
  intro residue base hirrational hbase p hp
  exact exists_monodromy_iterate_polynomial_ne_zero
    residue base hirrational hbase p hp

end FormalComplexMonodromyFiniteRootEscape
