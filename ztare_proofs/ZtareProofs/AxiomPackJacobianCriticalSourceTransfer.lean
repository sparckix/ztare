import Mathlib.Tactic
import ZtareProofs.AxiomPackJacobianCriticalSourceCost
import ZtareProofs.AxiomPackJacobianPolarTensorInductionArithmetic

/-!
# Strict-source transfer for the July critical tensor quotient

This interface composes the canonical finite Lie coordinates produced by the
July source-cost theorem with the locally finite target-left semidirect
transfer.  The tensor action uses the intrinsic actor `Ahat = X*a`; the
tangent Witt generator is `f = 2*Ahat`.

The terminal does not identify the constructed transfer with the fixed July
residual.  That schedule-to-group equality remains a separate proposition.
-/

namespace AxiomPackJacobianCriticalSourceTransfer

open Polynomial PowerSeries
open AxiomPackJacobianCriticalSourceCost
open AxiomPackJacobianPolarTensorInductionArithmetic
open _root_.FormalSemidirectFactorizationOrbit

noncomputable section

/-- Intrinsic actor consumed by the row-indexed tensor action. -/
def sourceTensorActorPolynomial
    (rows : ℕ → SparseSourceHamiltonian ℚ)
    (normalTwoCutoff : ℕ) : ℚ[X] :=
  Polynomial.X * normalTwoScalarPolynomial rows normalTwoCutoff

/-- The tangent Witt generator is exactly twice the intrinsic actor. -/
theorem sourceWittLiePolynomial_eq_two_mul_actor
    (rows : ℕ → SparseSourceHamiltonian ℚ)
    (normalTwoCutoff : ℕ) :
    sourceWittLiePolynomial rows normalTwoCutoff =
      Polynomial.C 2 *
        sourceTensorActorPolynomial rows normalTwoCutoff := by
  simp only [sourceWittLiePolynomial, sourceTensorActorPolynomial]
  ring

/-- The intrinsic actor belongs to the origin ideal without an extra
schedule premise. -/
theorem X_dvd_sourceTensorActorPolynomial
    (rows : ℕ → SparseSourceHamiltonian ℚ)
    (normalTwoCutoff : ℕ) :
    Polynomial.X ∣ sourceTensorActorPolynomial rows normalTwoCutoff := by
  exact ⟨normalTwoScalarPolynomial rows normalTwoCutoff, rfl⟩

/-- The intrinsic tensor module also belongs to the origin ideal. -/
theorem X_dvd_sourceTensorLiePolynomial
    (rows : ℕ → SparseSourceHamiltonian ℚ)
    (normalTwoCutoff normalThreeCutoff : ℕ) :
    Polynomial.X ∣
      sourceTensorLiePolynomial rows normalTwoCutoff normalThreeCutoff := by
  exact ⟨sourceTensorScalarPolynomial
      (normalTwoScalarPolynomial rows normalTwoCutoff)
      (normalThreeScalarPolynomial rows normalThreeCutoff), rfl⟩

/-- Named proposition for the complete source-row-indexed output of the
strict-source transfer theorem.  Every polynomial and coefficient is a
canonical definition from `rows`; this proposition introduces no independent
carrier data. -/
def CanonicalSourceTransfer
    (rows : ℕ → SparseSourceHamiltonian ℚ) : Prop :=
  ∃ normalTwoCutoff normalThreeCutoff,
    (∀ row, normalTwoCutoff ≤ row →
      sparseNormalTwoCoefficient rows row = 0) ∧
    ((normalTwoScalarPolynomial rows normalTwoCutoff : ℚ[X]) : ℚ⟦X⟧) =
      PowerSeries.mk (sparseNormalTwoCoefficient rows) ∧
    (∀ row, normalThreeCutoff ≤ row →
      sparseNormalThreeCoefficient rows row = 0) ∧
    ((normalThreeScalarPolynomial rows normalThreeCutoff : ℚ[X]) :
        ℚ⟦X⟧) =
      PowerSeries.mk (sparseNormalThreeCoefficient rows) ∧
    sourceWittLiePolynomial rows normalTwoCutoff =
      Polynomial.C 2 * sourceTensorActorPolynomial rows normalTwoCutoff ∧
    Polynomial.X ∣ sourceTensorActorPolynomial rows normalTwoCutoff ∧
    Polynomial.X ∣
      sourceTensorLiePolynomial rows normalTwoCutoff normalThreeCutoff ∧
    (∀ row,
      (sourceTensorLiePolynomial rows normalTwoCutoff normalThreeCutoff).coeff
          (row + 1) =
        (normalThreeScalarPolynomial rows normalThreeCutoff).coeff row +
          ((3 * row + 8 : ℕ) : ℚ) / 9 *
            (normalTwoScalarPolynomial rows normalTwoCutoff).coeff row) ∧
    (∀ spatialDegree cutoff,
      spatialDegree + 1 ≤ cutoff →
      PowerSeries.coeff spatialDegree
          (targetLeftTensorDuhamelTransfer
            (sourceTensorActorPolynomial rows normalTwoCutoff)
            (sourceTensorLiePolynomial rows normalTwoCutoff
              normalThreeCutoff)) =
        ∑ depth ∈ Finset.range cutoff,
          (targetLeftSemidirectExponentialCoefficient
            (rowIndexedTensorActionLinearMap
              (sourceTensorActorPolynomial rows normalTwoCutoff))
            (sourceTensorLiePolynomial rows normalTwoCutoff
              normalThreeCutoff)
            depth).coeff spatialDegree)

/-- Strict source growth constructs the canonical finite actor/module pair
and its complete coefficientwise target-left Duhamel transfer. -/
theorem critical_source_lie_to_transfer_terminal_certificate
    (rows : ℕ → SparseSourceHamiltonian ℚ)
    (subcritical :
      LinearGrowth.linearGrowthSup
          (fun order => (sparseCompleteSourceCost rows order : EReal)) <
        (2 : EReal)) :
    ∃ normalTwoCutoff normalThreeCutoff,
      (∀ row, normalTwoCutoff ≤ row →
        sparseNormalTwoCoefficient rows row = 0) ∧
      ((normalTwoScalarPolynomial rows normalTwoCutoff : ℚ[X]) : ℚ⟦X⟧) =
        PowerSeries.mk (sparseNormalTwoCoefficient rows) ∧
      (∀ row, normalThreeCutoff ≤ row →
        sparseNormalThreeCoefficient rows row = 0) ∧
      ((normalThreeScalarPolynomial rows normalThreeCutoff : ℚ[X]) :
          ℚ⟦X⟧) =
        PowerSeries.mk (sparseNormalThreeCoefficient rows) ∧
      sourceWittLiePolynomial rows normalTwoCutoff =
        Polynomial.C 2 * sourceTensorActorPolynomial rows normalTwoCutoff ∧
      Polynomial.X ∣ sourceTensorActorPolynomial rows normalTwoCutoff ∧
      Polynomial.X ∣
        sourceTensorLiePolynomial rows normalTwoCutoff normalThreeCutoff ∧
      (∀ row,
        (sourceTensorLiePolynomial rows normalTwoCutoff normalThreeCutoff).coeff
            (row + 1) =
          (normalThreeScalarPolynomial rows normalThreeCutoff).coeff row +
            ((3 * row + 8 : ℕ) : ℚ) / 9 *
              (normalTwoScalarPolynomial rows normalTwoCutoff).coeff row) ∧
      (∀ spatialDegree cutoff,
        spatialDegree + 1 ≤ cutoff →
        PowerSeries.coeff spatialDegree
            (targetLeftTensorDuhamelTransfer
              (sourceTensorActorPolynomial rows normalTwoCutoff)
              (sourceTensorLiePolynomial rows normalTwoCutoff
                normalThreeCutoff)) =
          ∑ depth ∈ Finset.range cutoff,
            (targetLeftSemidirectExponentialCoefficient
              (rowIndexedTensorActionLinearMap
                (sourceTensorActorPolynomial rows normalTwoCutoff))
              (sourceTensorLiePolynomial rows normalTwoCutoff
                normalThreeCutoff)
              depth).coeff spatialDegree) := by
  obtain ⟨normalTwoCutoff, normalThreeCutoff,
      normalTwoZero, normalTwoBinding,
      normalThreeZero, normalThreeBinding,
      _sourceWittBinding, _sourceTensorBinding,
      sourceTensorCoefficients⟩ :=
    critical_source_finite_lie_coordinates_terminal_certificate
      rows subcritical
  have actorDivisible :=
    X_dvd_sourceTensorActorPolynomial rows normalTwoCutoff
  have moduleDivisible :=
    X_dvd_sourceTensorLiePolynomial rows normalTwoCutoff normalThreeCutoff
  refine ⟨normalTwoCutoff, normalThreeCutoff,
    normalTwoZero, normalTwoBinding,
    normalThreeZero, normalThreeBinding,
    sourceWittLiePolynomial_eq_two_mul_actor rows normalTwoCutoff,
    actorDivisible, moduleDivisible,
    sourceTensorCoefficients, ?_⟩
  intro spatialDegree cutoff cutoffBeyond
  exact coeff_targetLeftTensorDuhamelTransfer_eq_sum_range
    (sourceTensorActorPolynomial rows normalTwoCutoff)
    (sourceTensorLiePolynomial rows normalTwoCutoff normalThreeCutoff)
    actorDivisible moduleDivisible spatialDegree cutoff cutoffBeyond

/-- The expanded terminal constructs the named same-row proposition without
changing the ratified terminal's statement identity. -/
theorem canonicalSourceTransfer_of_linearGrowthSup_lt
    (rows : ℕ → SparseSourceHamiltonian ℚ)
    (subcritical :
      LinearGrowth.linearGrowthSup
          (fun order => (sparseCompleteSourceCost rows order : EReal)) <
        (2 : EReal)) :
    CanonicalSourceTransfer rows := by
  simpa only [CanonicalSourceTransfer] using
    critical_source_lie_to_transfer_terminal_certificate rows subcritical

end

end AxiomPackJacobianCriticalSourceTransfer
