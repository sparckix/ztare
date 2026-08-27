import Mathlib.Tactic
import ZtareProofs.AxiomPackJacobianRegularReesTwoFlowExclusion
import ZtareProofs.FormalDiagonalReesTangentGenerator

/-!
# Row-computed regular Rees contact for the July critical germ

Both finite critical generators are computed from coefficientwise-polynomial
row schedules.  The carrier retains only the regular Rees flow objects and
their exact endpoint composition.  It does not accept a critical polynomial
or a generator-residue binding as input.
-/

namespace AxiomPackJacobianCriticalDiagonalReesSchedule

open Polynomial PowerSeries
open FormalAutonomousFlow
open AxiomPackJacobianCriticalBaseTwoFlowExclusion
open AxiomPackJacobianCriticalHolonomyTwoFlowExclusion
open AxiomPackJacobianRegularReesTwoFlowExclusion
open ZtareProofs.FormalDiagonalReesPolynomial
open ZtareProofs.FormalDiagonalReesTangentGenerator

noncomputable section

/-- Apply the family-owned scalar normalization before the generic tangent
shift.  For the July source inverse this scalar is `-2`; target
normalization is supplied by its radial scalarization map. -/
def normalizedRows (scale : ℝ) (rows : ℕ → ℝ[X]) : ℕ → ℝ[X] :=
  fun row => Polynomial.C scale * rows row

/-- Scalar normalization cannot increase row degree. -/
theorem normalizedRows_strictAfter
    (scale : ℝ) (rows : ℕ → ℝ[X]) (cutoff : ℕ)
    (strictAfter :
      ∀ row, cutoff ≤ row → (rows row).natDegree < row) :
    ∀ row, cutoff ≤ row →
      (normalizedRows scale rows row).natDegree < row := by
  intro row hrow
  exact (Polynomial.natDegree_C_mul_le _ _).trans_lt
    (strictAfter row hrow)

/-- Complexify every polynomial coefficient row. -/
def complexRows (rows : ℕ → ℝ[X]) : ℕ → ℂ[X] :=
  fun row => baseComplexifyPolynomial (rows row)

/-- Complexification preserves the strict diagonal cutoff. -/
theorem complexRows_strictAfter
    (rows : ℕ → ℝ[X]) (cutoff : ℕ)
    (strictAfter :
      ∀ row, cutoff ≤ row → (rows row).natDegree < row) :
    ∀ row, cutoff ≤ row → (complexRows rows row).natDegree < row := by
  intro row hrow
  rw [complexRows, baseComplexifyPolynomial,
    Polynomial.natDegree_map_eq_of_injective Complex.ofReal_injective]
  exact strictAfter row hrow

/-- Complexification preserves eventual vanishing of the selected critical
diagonal. -/
theorem complexRows_diagonalZeroAfter
    (rows : ℕ → ℝ[X]) (cutoff : ℕ)
    (diagonalZeroAfter :
      ∀ row, cutoff ≤ row → (rows row).coeff row = 0) :
    ∀ row, cutoff ≤ row → (complexRows rows row).coeff row = 0 := by
  intro row hrow
  simp [complexRows, baseComplexifyPolynomial,
    Polynomial.coeff_map, diagonalZeroAfter row hrow]

/-- Shifted critical extraction commutes with real-to-complex extension. -/
theorem criticalTangentGenerator_complexRows
    (rows : ℕ → ℝ[X]) (cutoff : ℕ) :
    criticalTangentGenerator (complexRows rows) cutoff =
      baseComplexifyPolynomial
        (criticalTangentGenerator rows cutoff) := by
  simp only [criticalTangentGenerator, baseComplexifyPolynomial,
    Polynomial.map_mul, Polynomial.map_X]
  rw [criticalPolynomial_map]
  rfl

/-- A zero-positive-face row schedule retaining only the actual regular
Rees flow and composition equations not constructed by diagonal extraction. -/
structure CriticalDiagonalReesTwoFlowSchedule where
  innerRows : ℕ → ℝ[X]
  outerRows : ℕ → ℝ[X]
  innerScale : ℝ
  outerScale : ℝ
  innerCutoff : ℕ
  outerCutoff : ℕ
  innerDiagonalZeroAfter :
    ∀ row, innerCutoff ≤ row →
      (normalizedRows innerScale innerRows row).coeff row = 0
  outerDiagonalZeroAfter :
    ∀ row, outerCutoff ≤ row →
      (normalizedRows outerScale outerRows row).coeff row = 0
  innerScalar_constant :
    (criticalPolynomial
      (normalizedRows innerScale innerRows) innerCutoff).coeff 0 = 0
  outerScalar_constant :
    (criticalPolynomial
      (normalizedRows outerScale outerRows) outerCutoff).coeff 0 = 0
  innerEndpoint : ReesGerm
  outerEndpoint : ReesGerm
  innerFlow : AutonomousSubstitutionTimeOne
    (regularReesTangentGenerator
      (complexRows (normalizedRows innerScale innerRows))) innerEndpoint
  outerFlow : AutonomousSubstitutionTimeOne
    (regularReesTangentGenerator
      (complexRows (normalizedRows outerScale outerRows))) outerEndpoint
  innerZeroEndpoint :
    criticalTangentGenerator
        (normalizedRows innerScale innerRows) innerCutoff = 0 →
      PowerSeries.map criticalResidue innerEndpoint = PowerSeries.X
  outerZeroEndpoint :
    criticalTangentGenerator
        (normalizedRows outerScale outerRows) outerCutoff = 0 →
      PowerSeries.map criticalResidue outerEndpoint = PowerSeries.X
  completeResidual : ReesGerm
  completeEndpointFactorization :
    PowerSeries.subst innerEndpoint outerEndpoint = completeResidual
  criticalResidualBinding :
    PowerSeries.map criticalResidue completeResidual =
      baseCriticalHolonomy

/-- The row-computed carrier constructs the exact regular Rees contact. -/
def CriticalDiagonalReesTwoFlowSchedule.toRegularReesContact
    (schedule : CriticalDiagonalReesTwoFlowSchedule) :
    RegularReesTwoFlowContact := by
  let innerCritical :=
    criticalTangentGenerator
      (normalizedRows schedule.innerScale schedule.innerRows)
      schedule.innerCutoff
  let outerCritical :=
    criticalTangentGenerator
      (normalizedRows schedule.outerScale schedule.outerRows)
      schedule.outerCutoff
  have innerComplexDiagonalZero := complexRows_diagonalZeroAfter
    (normalizedRows schedule.innerScale schedule.innerRows)
    schedule.innerCutoff schedule.innerDiagonalZeroAfter
  have outerComplexDiagonalZero := complexRows_diagonalZeroAfter
    (normalizedRows schedule.outerScale schedule.outerRows)
    schedule.outerCutoff schedule.outerDiagonalZeroAfter
  have innerBindingComplex :=
    criticalTangentGenerator_coe_eq_of_diagonal_eventually_zero
    (complexRows (normalizedRows schedule.innerScale schedule.innerRows))
    schedule.innerCutoff innerComplexDiagonalZero
  have outerBindingComplex :=
    criticalTangentGenerator_coe_eq_of_diagonal_eventually_zero
    (complexRows (normalizedRows schedule.outerScale schedule.outerRows))
    schedule.outerCutoff outerComplexDiagonalZero
  have innerBinding :
      PowerSeries.map criticalResidue
          (regularReesTangentGenerator
            (complexRows
              (normalizedRows schedule.innerScale schedule.innerRows))) =
        ((baseComplexifyPolynomial innerCritical : ℂ[X]) : PowerSeries ℂ) := by
    rw [← criticalTangentGenerator_complexRows
      (normalizedRows schedule.innerScale schedule.innerRows)]
    exact innerBindingComplex.symm
  have outerBinding :
      PowerSeries.map criticalResidue
          (regularReesTangentGenerator
            (complexRows
              (normalizedRows schedule.outerScale schedule.outerRows))) =
        ((baseComplexifyPolynomial outerCritical : ℂ[X]) : PowerSeries ℂ) := by
    rw [← criticalTangentGenerator_complexRows
      (normalizedRows schedule.outerScale schedule.outerRows)]
    exact outerBindingComplex.symm
  exact {
    innerGenerator := regularReesTangentGenerator
      (complexRows (normalizedRows schedule.innerScale schedule.innerRows))
    outerGenerator := regularReesTangentGenerator
      (complexRows (normalizedRows schedule.outerScale schedule.outerRows))
    innerEndpoint := schedule.innerEndpoint
    outerEndpoint := schedule.outerEndpoint
    innerFlow := schedule.innerFlow
    outerFlow := schedule.outerFlow
    innerCritical := innerCritical
    outerCritical := outerCritical
    innerCriticalBinding := innerBinding
    outerCriticalBinding := outerBinding
    inner_constant := criticalTangentGenerator_coeff_zero _ _
    inner_linear := criticalTangentGenerator_coeff_one _ _
      schedule.innerScalar_constant
    outer_constant := criticalTangentGenerator_coeff_zero _ _
    outer_linear := criticalTangentGenerator_coeff_one _ _
      schedule.outerScalar_constant
    inner_zero_endpoint := schedule.innerZeroEndpoint
    outer_zero_endpoint := schedule.outerZeroEndpoint
    completeResidual := schedule.completeResidual
    completeEndpointFactorization := schedule.completeEndpointFactorization
    criticalResidualBinding := schedule.criticalResidualBinding
  }

/-- No complete row-computed regular Rees schedule realizes the July
critical holonomy. -/
theorem critical_diagonal_rees_two_flow_schedule_impossible
    (schedule : CriticalDiagonalReesTwoFlowSchedule) : False :=
  regular_rees_two_flow_contact_impossible schedule.toRegularReesContact

/-- Aggregated row-computed Rees terminal certificate. -/
theorem critical_diagonal_rees_schedule_terminal_certificate :
    ¬ Nonempty CriticalDiagonalReesTwoFlowSchedule := by
  rintro ⟨schedule⟩
  exact critical_diagonal_rees_two_flow_schedule_impossible schedule

end


end AxiomPackJacobianCriticalDiagonalReesSchedule
