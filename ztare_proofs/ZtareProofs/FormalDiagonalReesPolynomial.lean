import Mathlib.RingTheory.PowerSeries.Trunc
import Mathlib.Tactic

/-!
# Canonical polynomial on a critical Rees diagonal

For coefficientwise polynomial rows `a n`, the regular Rees transform uses
the coefficient rule

`[X^d ε^e] R(a) = [X^d] a (d + e)`.

Critical evaluation `ε = 0` therefore selects the diagonal coefficient
`[X^d] a d`.  Eventual strict inequality `natDegree (a n) < n` kills that
diagonal after a finite cutoff, so its critical image is canonically a
polynomial.
-/

namespace ZtareProofs.FormalDiagonalReesPolynomial

open Polynomial PowerSeries

noncomputable section

variable {R : Type*} [CommRing R]

/-- Rees coefficients in the parameter `ε`. -/
abbrev ReesCoefficient (R : Type*) [CommRing R] := PowerSeries R

/-- Spatial germs whose coefficients are regular Rees series. -/
abbrev ReesGerm (R : Type*) [CommRing R] :=
  PowerSeries (ReesCoefficient R)

/-- The coefficientwise regular Rees transform of polynomial rows. -/
def regularReesGerm (rows : ℕ → R[X]) : ReesGerm R :=
  PowerSeries.mk fun spatialDegree =>
    PowerSeries.mk fun reesOrder =>
      (rows (spatialDegree + reesOrder)).coeff spatialDegree

/-- Evaluation at the critical Rees face. -/
def criticalResidue : ReesCoefficient R →+* R :=
  PowerSeries.constantCoeff

/-- Critical evaluation selects exactly the schedule diagonal. -/
theorem coeff_map_criticalResidue_regularReesGerm
    (rows : ℕ → R[X]) (degree : ℕ) :
    PowerSeries.coeff degree
        (PowerSeries.map criticalResidue (regularReesGerm rows)) =
      (rows degree).coeff degree := by
  simp [criticalResidue, regularReesGerm, PowerSeries.coeff_map]

/-- The canonical critical polynomial cut off before the eventually strict
tail. -/
def criticalPolynomial
    (rows : ℕ → R[X]) (cutoff : ℕ) : R[X] :=
  PowerSeries.trunc cutoff
    (PowerSeries.map criticalResidue (regularReesGerm rows))

/-- The rows whose diagonal coefficient survives critical Rees evaluation. -/
def diagonalSupport (rows : ℕ → R[X]) : Set ℕ :=
  {row | (rows row).coeff row ≠ 0}

/-! ## Pure diagonal rows and scalar coefficient sequences -/

/-- Embed a scalar coefficient sequence as polynomial rows supported on their
own Rees diagonal. -/
def pureDiagonalRows (coefficients : ℕ → R) : ℕ → R[X] :=
  fun row => Polynomial.C (coefficients row) * Polynomial.X ^ row

/-- Pure diagonal row extraction recovers the supplied scalar coefficient,
including at row zero. -/
theorem pureDiagonalRows_coeff_self
    (coefficients : ℕ → R) (row : ℕ) :
    (pureDiagonalRows coefficients row).coeff row = coefficients row := by
  simp [pureDiagonalRows]

/-- Critical Rees evaluation of pure diagonal rows is exactly the power
series with the supplied scalar coefficient sequence. -/
theorem criticalResidue_pureDiagonalRows
    (coefficients : ℕ → R) :
    PowerSeries.map criticalResidue
        (regularReesGerm (pureDiagonalRows coefficients)) =
      PowerSeries.mk coefficients := by
  ext row
  rw [coeff_map_criticalResidue_regularReesGerm]
  simp [pureDiagonalRows]

/-- Eventual diagonal vanishing is the exact hypothesis needed for critical
evaluation to equal its finite canonical truncation. -/
theorem criticalPolynomial_coe_eq_of_diagonal_eventually_zero
    (rows : ℕ → R[X]) (cutoff : ℕ)
    (diagonalZeroAfter :
      ∀ row, cutoff ≤ row → (rows row).coeff row = 0) :
    ((criticalPolynomial rows cutoff : R[X]) : PowerSeries R) =
      PowerSeries.map criticalResidue (regularReesGerm rows) := by
  ext degree
  rw [Polynomial.coeff_coe]
  change (PowerSeries.trunc cutoff
      (PowerSeries.map criticalResidue
        (regularReesGerm rows))).coeff degree = _
  rw [PowerSeries.coeff_trunc]
  split_ifs with beforeCutoff
  · rfl
  · have cutoff_le : cutoff ≤ degree := Nat.le_of_not_gt beforeCutoff
    rw [coeff_map_criticalResidue_regularReesGerm,
      diagonalZeroAfter degree cutoff_le]

/-- Eventual strict diagonal degree makes the exact critical Rees image equal
to its canonical polynomial truncation. -/
theorem criticalPolynomial_coe_eq
    (rows : ℕ → R[X]) (cutoff : ℕ)
    (strictAfter :
      ∀ row, cutoff ≤ row → (rows row).natDegree < row) :
    ((criticalPolynomial rows cutoff : R[X]) : PowerSeries R) =
      PowerSeries.map criticalResidue (regularReesGerm rows) := by
  apply criticalPolynomial_coe_eq_of_diagonal_eventually_zero
  intro row hrow
  exact Polynomial.coeff_eq_zero_of_natDegree_lt
    (strictAfter row hrow)

/-- Finite critical diagonal support produces an eventual-zero cutoff. -/
theorem diagonalSupport_finite_eventually_zero
    (rows : ℕ → R[X])
    (hfinite : (diagonalSupport rows).Finite) :
    ∃ cutoff, ∀ row, cutoff ≤ row → (rows row).coeff row = 0 := by
  by_contra hcutoff
  push Not at hcutoff
  have hinfinite : (diagonalSupport rows).Infinite :=
    Set.infinite_iff_exists_gt.mpr (by
      intro lower
      obtain ⟨row, hrow, hcoefficient⟩ := hcutoff (lower + 1)
      exact ⟨row, by simpa [diagonalSupport] using hcoefficient,
        lt_of_lt_of_le (Nat.lt_succ_self lower) hrow⟩)
  exact hinfinite hfinite

/-- Finite scalar support produces a canonical polynomial whose power-series
coercion is the complete scalar series.  This is a specialization of the
diagonal Rees truncation, not a second finite-series construction. -/
theorem finiteCoefficientSupport_has_canonicalPolynomial
    (coefficients : ℕ → R)
    (supportFinite : {row : ℕ | coefficients row ≠ 0}.Finite) :
    ∃ cutoff,
      (∀ row, cutoff ≤ row → coefficients row = 0) ∧
      ((criticalPolynomial (pureDiagonalRows coefficients) cutoff : R[X]) :
          PowerSeries R) = PowerSeries.mk coefficients := by
  have diagonalFinite :
      (diagonalSupport (pureDiagonalRows coefficients)).Finite := by
    simpa only [diagonalSupport, Set.setOf_mem_eq,
      pureDiagonalRows_coeff_self] using supportFinite
  obtain ⟨cutoff, diagonalZero⟩ :=
    diagonalSupport_finite_eventually_zero
      (pureDiagonalRows coefficients) diagonalFinite
  refine ⟨cutoff, ?_, ?_⟩
  · intro row hrow
    simpa only [pureDiagonalRows_coeff_self] using
      diagonalZero row hrow
  · calc
      ((criticalPolynomial (pureDiagonalRows coefficients) cutoff : R[X]) :
          PowerSeries R) =
          PowerSeries.map criticalResidue
            (regularReesGerm (pureDiagonalRows coefficients)) :=
        criticalPolynomial_coe_eq_of_diagonal_eventually_zero
          (pureDiagonalRows coefficients) cutoff diagonalZero
      _ = PowerSeries.mk coefficients :=
        criticalResidue_pureDiagonalRows coefficients

/-- The exact support split: the critical Rees residue is a finite canonical
polynomial, or nonzero diagonal rows occur past every cutoff. -/
theorem diagonal_rees_support_dichotomy
    (rows : ℕ → R[X]) :
    (∃ cutoff,
      (∀ row, cutoff ≤ row → (rows row).coeff row = 0) ∧
      ((criticalPolynomial rows cutoff : R[X]) : PowerSeries R) =
        PowerSeries.map criticalResidue (regularReesGerm rows)) ∨
    (∀ cutoff, ∃ row, cutoff ≤ row ∧ (rows row).coeff row ≠ 0) := by
  classical
  by_cases hfinite : (diagonalSupport rows).Finite
  · left
    obtain ⟨cutoff, hzero⟩ :=
      diagonalSupport_finite_eventually_zero rows hfinite
    exact ⟨cutoff, hzero,
      criticalPolynomial_coe_eq_of_diagonal_eventually_zero
        rows cutoff hzero⟩
  · right
    have hinfinite : (diagonalSupport rows).Infinite := hfinite
    intro cutoff
    obtain ⟨row, hrowSupport, hrowGreater⟩ := hinfinite.exists_gt cutoff
    exact ⟨row, Nat.le_of_lt hrowGreater,
      by simpa [diagonalSupport] using hrowSupport⟩

/-- A named terminal certificate for proof-identity binding. -/
theorem diagonal_rees_polynomial_terminal_certificate
    (rows : ℕ → R[X]) (cutoff : ℕ)
    (strictAfter :
      ∀ row, cutoff ≤ row → (rows row).natDegree < row) :
    ((criticalPolynomial rows cutoff : R[X]) : PowerSeries R) =
      PowerSeries.map criticalResidue (regularReesGerm rows) :=
  criticalPolynomial_coe_eq rows cutoff strictAfter

/-- Aggregated finite/infinite critical-support splitter. -/
theorem diagonal_rees_support_dichotomy_terminal_certificate :
    ∀ (rows : ℕ → R[X]),
      (∃ cutoff,
        (∀ row, cutoff ≤ row → (rows row).coeff row = 0) ∧
        ((criticalPolynomial rows cutoff : R[X]) : PowerSeries R) =
          PowerSeries.map criticalResidue (regularReesGerm rows)) ∨
      (∀ cutoff, ∃ row,
        cutoff ≤ row ∧ (rows row).coeff row ≠ 0) :=
  diagonal_rees_support_dichotomy

end

end ZtareProofs.FormalDiagonalReesPolynomial
