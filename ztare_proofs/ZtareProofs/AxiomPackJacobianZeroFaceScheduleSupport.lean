import ZtareProofs.AxiomPackJacobianCriticalSourceCost
import ZtareProofs.AxiomPackJacobianCriticalSourceTransfer
import ZtareProofs.FormalDiagonalReesPolynomial

/-!
# July zero-face schedule support

This file binds the two support statements needed before the zero-face
realization split:

* a positive affine margin makes the coefficient-defined critical source
  support finite; and
* the target Rees diagonal is either eventually zero, with its exact
  canonical polynomial residue, or survives past every cutoff.

The result is deliberately a conjunction and a proposition-level branch.
It supplies no flow, endpoint, factorization, semidirect equation, or
residual field.  Those belong to the later realization theorems.
-/

namespace AxiomPackJacobianZeroFaceScheduleSupport

open AxiomPackJacobianCriticalSourceCost
open AxiomPackJacobianCriticalSourceTransfer
open ZtareProofs.FormalDiagonalReesPolynomial

noncomputable section

variable {R : Type*} [CommRing R] [DecidableEq R]

/-- The support-level zero-face partition for one pair of carried source and
target row families.  Its hypotheses concern only the source margin; the
target alternative is the unconditional diagonal support dichotomy. -/
theorem zero_face_schedule_support_terminal_certificate
    (sourceRows : ℕ → SparseSourceHamiltonian R)
    (targetRows : ℕ → Polynomial R)
    (margin denominator cutoff : ℕ)
    (margin_pos : 0 < margin)
    (marginTail : ∀ row, cutoff ≤ row →
      denominator * sparseCompleteSourceCost sourceRows (row + 1) +
          margin * (row + 1) ≤ denominator * 2 * (row + 1)) :
    {row : ℕ | criticalSourceSupport
      (sparseNormalTwoNonzero sourceRows)
      (sparseNormalThreeNonzero sourceRows) row}.Finite ∧
    ((∃ targetCutoff,
      (∀ row, targetCutoff ≤ row → (targetRows row).coeff row = 0) ∧
      ((criticalPolynomial targetRows targetCutoff : Polynomial R) :
          PowerSeries R) =
        PowerSeries.map criticalResidue (regularReesGerm targetRows)) ∨
    (∀ targetCutoff, ∃ row,
      targetCutoff ≤ row ∧ (targetRows row).coeff row ≠ 0)) := by
  constructor
  · exact sparseCriticalSourceSupport_finite_of_positive_margin
      sourceRows margin denominator cutoff margin_pos marginTail
  · exact diagonal_rees_support_dichotomy targetRows

/-- The same exact support partition, now bound to the campaign's ordinary
unshifted source upper linear-growth statistic rather than adapter-supplied
margin data. -/
theorem zero_face_schedule_support_of_linearGrowthSup_terminal_certificate
    (sourceRows : ℕ → SparseSourceHamiltonian R)
    (targetRows : ℕ → Polynomial R)
    (subcritical :
      LinearGrowth.linearGrowthSup
          (fun order =>
            (sparseCompleteSourceCost sourceRows order : EReal)) <
        (2 : EReal)) :
    {row : ℕ | criticalSourceSupport
      (sparseNormalTwoNonzero sourceRows)
      (sparseNormalThreeNonzero sourceRows) row}.Finite ∧
    ((∃ targetCutoff,
      (∀ row, targetCutoff ≤ row → (targetRows row).coeff row = 0) ∧
      ((criticalPolynomial targetRows targetCutoff : Polynomial R) :
          PowerSeries R) =
        PowerSeries.map criticalResidue (regularReesGerm targetRows)) ∨
    (∀ targetCutoff, ∃ row,
      targetCutoff ≤ row ∧ (targetRows row).coeff row ≠ 0)) := by
  exact ⟨sparseCriticalSourceSupport_finite_of_linearGrowthSup_lt
      sourceRows subcritical,
    diagonal_rees_support_dichotomy targetRows⟩

/-- Exact proposition-level target diagonal partition.  The finite side
contains only the canonical polynomial residue; the infinite side contains
only unbounded diagonal support. -/
def TargetDiagonalSupportSplit (targetRows : ℕ → Polynomial ℚ) : Prop :=
  (∃ targetCutoff,
    (∀ row, targetCutoff ≤ row → (targetRows row).coeff row = 0) ∧
    ((criticalPolynomial targetRows targetCutoff : Polynomial ℚ) :
        PowerSeries ℚ) =
      PowerSeries.map criticalResidue (regularReesGerm targetRows)) ∨
  (∀ targetCutoff, ∃ row,
    targetCutoff ≤ row ∧ (targetRows row).coeff row ≠ 0)

/-- Same-row zero-face partition: strict source growth constructs the
canonical actor/module transfer, while the supplied target rows enter their
exact support dichotomy.  No realization carrier is accepted or returned. -/
theorem zero_face_same_row_transfer_partition_terminal_certificate
    (sourceRows : ℕ → SparseSourceHamiltonian ℚ)
    (targetRows : ℕ → Polynomial ℚ)
    (subcritical :
      LinearGrowth.linearGrowthSup
          (fun order =>
            (sparseCompleteSourceCost sourceRows order : EReal)) <
        (2 : EReal)) :
    CanonicalSourceTransfer sourceRows ∧
      TargetDiagonalSupportSplit targetRows := by
  constructor
  · exact canonicalSourceTransfer_of_linearGrowthSup_lt
      sourceRows subcritical
  · exact diagonal_rees_support_dichotomy targetRows

end

end AxiomPackJacobianZeroFaceScheduleSupport
