import Mathlib.Data.Nat.Choose.Sum
import Mathlib.RingTheory.Derivation.Basic
import Mathlib.Tactic

/-!
# Iterated Leibniz rule for algebraic derivations

The ordinary Leibniz identity and Pascal recurrence determine every iterate
of a derivation on a product.  This file exposes both antidiagonal and
range-indexed forms without specializing the derivation to a differential or
polynomial substrate.
-/

namespace FormalDerivationIteratedLeibniz

open Finset Nat

universe u

variable {R : Type u} [CommRing R]

/-- The binomial Leibniz rule for every natural iterate of a derivation. -/
theorem iterate_apply_mul
    (D : Derivation ℤ R R) (n : ℕ) (a b : R) :
    D^[n] (a * b) =
      ∑ ij ∈ antidiagonal n,
        n.choose ij.1 • (D^[ij.1] a * D^[ij.2] b) := by
  induction n with
  | zero => simp
  | succ n inductionHypothesis =>
      rw [sum_antidiagonal_choose_succ_nsmul (M := R)
        (fun i j ↦ D^[i] a * D^[j] b) n]
      simp only [Function.iterate_succ_apply', inductionHypothesis,
        map_sum, map_nsmul, Derivation.leibniz, smul_add,
        sum_add_distrib]
      simp only [smul_eq_mul]
      congr 1
      refine sum_congr rfl fun ⟨i, j⟩ hij ↦ ?_
      rw [n.choose_symm_of_eq_add (mem_antidiagonal.1 hij).symm]
      ring

/-- Range-indexed form, with the first factor in degree `j` and the second
factor in degree `n-j`. Applying it to `q * a` gives the triangular source-jet
orientation after commutativity. -/
theorem iterate_apply_mul_range
    (D : Derivation ℤ R R) (n : ℕ) (a b : R) :
    D^[n] (a * b) =
      ∑ j ∈ range (n + 1),
        n.choose j • (D^[j] a * D^[n - j] b) := by
  rw [iterate_apply_mul D n a b]
  exact sum_antidiagonal_eq_sum_range_succ
    (fun i j ↦ n.choose i • (D^[i] a * D^[j] b)) n

/-- Aggregated substrate-neutral iterated-product certificate. -/
theorem derivation_iterated_leibniz_terminal_certificate :
    ∀ (D : Derivation ℤ R R) (n : ℕ) (a b : R),
      D^[n] (a * b) =
        ∑ ij ∈ antidiagonal n,
          n.choose ij.1 • (D^[ij.1] a * D^[ij.2] b) ∧
      D^[n] (a * b) =
        ∑ j ∈ range (n + 1),
          n.choose j • (D^[j] a * D^[n - j] b) := by
  intro D n a b
  exact ⟨iterate_apply_mul D n a b, iterate_apply_mul_range D n a b⟩

end FormalDerivationIteratedLeibniz
