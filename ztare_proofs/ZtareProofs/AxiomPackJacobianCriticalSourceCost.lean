import Mathlib.Tactic
import Mathlib.RingTheory.PowerSeries.Derivative
import ZtareProofs.FilteredCriticalSupport
import ZtareProofs.FormalDiagonalReesPolynomial

/-!
# Critical source cost for the July Jacobian family

At critical row `n`, the split source logarithm can have a normal-two
coordinate of radial degree `n + 2` and a normal-three coordinate of radial
degree `n`.  In the moving chart, `r^a z^j = u^a z^(a+j)`.  For the source
density `z^2`, its vector-field degree is `2*a + j - 3`.  The two critical
degrees are therefore `2*n + 3` and `2*n`; their common lower charge is
exactly `2*n`.

This file keeps the family arithmetic separate from the generic filtered
support theorem.  Visibility of a nonzero coordinate in the complete source
row is an explicit premise: the adapter does not identify a coordinate cost
with the complete row cost by definition.
-/

namespace AxiomPackJacobianCriticalSourceCost

open ZtareProofs.FilteredCriticalSupport

/-- Radial degree of the normal-two critical coordinate in row `row`. -/
def normalTwoCriticalRadialDegree (row : ℕ) : ℕ := row + 2

/-- Radial degree of the normal-three critical coordinate in row `row`. -/
def normalThreeCriticalRadialDegree (row : ℕ) : ℕ := row

/-- Total polynomial degree after rewriting `r^a z^j` in `(u,z)`. -/
def movingHamiltonianDegree (radialDegree normalOrder : ℕ) : ℕ :=
  2 * radialDegree + normalOrder

/-- Degree of the Hamiltonian vector field for source density `z^2`. -/
def sourceVectorDegree (radialDegree normalOrder : ℕ) : ℕ :=
  movingHamiltonianDegree radialDegree normalOrder - 3

/-- Exact vector degree of the critical normal-two coordinate. -/
def normalTwoCriticalVectorDegree (row : ℕ) : ℕ :=
  sourceVectorDegree (normalTwoCriticalRadialDegree row) 2

/-- Exact vector degree of the critical normal-three coordinate. -/
def normalThreeCriticalVectorDegree (row : ℕ) : ℕ :=
  sourceVectorDegree (normalThreeCriticalRadialDegree row) 3

/-- The critical normal-two coordinate lies three degrees above the common
rate-two charge. -/
theorem normalTwoCriticalVectorDegree_eq (row : ℕ) :
    normalTwoCriticalVectorDegree row = 2 * row + 3 := by
  simp only [normalTwoCriticalVectorDegree, sourceVectorDegree,
    movingHamiltonianDegree, normalTwoCriticalRadialDegree]
  omega

/-- The critical normal-three coordinate exactly saturates the rate-two
charge. -/
theorem normalThreeCriticalVectorDegree_eq (row : ℕ) :
    normalThreeCriticalVectorDegree row = 2 * row := by
  simp only [normalThreeCriticalVectorDegree, sourceVectorDegree,
    movingHamiltonianDegree, normalThreeCriticalRadialDegree]
  omega

/-- Both split coordinates pay at least the common rate-two charge. -/
theorem criticalVectorDegree_lower_charge (row : ℕ) :
    2 * row ≤ normalTwoCriticalVectorDegree row ∧
      2 * row ≤ normalThreeCriticalVectorDegree row := by
  rw [normalTwoCriticalVectorDegree_eq,
    normalThreeCriticalVectorDegree_eq]
  omega

/-- A complete source Hamiltonian row, represented after equal monomial
exponents have already been combined. -/
abbrev SparseSourceHamiltonian (R : Type*) [Zero R] :=
  (ℕ × ℕ) →₀ R

/-- Density-adjusted source-vector cost of the Hamiltonian monomial
`u^a z^b`.  The subtraction by three is the source-density shift. -/
def sourceHamiltonianExponentCost (exponent : ℕ × ℕ) : ℕ :=
  exponent.1 + exponent.2 - 3

/-- The complete source-vector degree read directly from the finite
coefficient support of one Hamiltonian row. -/
def completeSourceVectorDegree
    {R : Type*} [Zero R] [DecidableEq R]
    (hamiltonian : SparseSourceHamiltonian R) : ℕ :=
  hamiltonian.support.sup sourceHamiltonianExponentCost

/-- Moving-chart exponent conversion `r^a z^j = u^a z^(a+j)`. -/
def movingExponent (radialDegree normalOrder : ℕ) : ℕ × ℕ :=
  (radialDegree, radialDegree + normalOrder)

/-- Exponent of the row-`row` normal-two critical coordinate. -/
def normalTwoCriticalExponent (row : ℕ) : ℕ × ℕ :=
  movingExponent (normalTwoCriticalRadialDegree row) 2

/-- Exponent of the row-`row` normal-three critical coordinate. -/
def normalThreeCriticalExponent (row : ℕ) : ℕ × ℕ :=
  movingExponent (normalThreeCriticalRadialDegree row) 3

/-- The exponent support cost recovers the already-audited normal-two
critical vector degree. -/
theorem normalTwoCriticalExponent_cost (row : ℕ) :
    sourceHamiltonianExponentCost (normalTwoCriticalExponent row) =
      normalTwoCriticalVectorDegree row := by
  simp only [sourceHamiltonianExponentCost, normalTwoCriticalExponent,
    movingExponent, normalTwoCriticalVectorDegree, sourceVectorDegree,
    movingHamiltonianDegree, normalTwoCriticalRadialDegree]
  omega

/-- The exponent support cost recovers the already-audited normal-three
critical vector degree. -/
theorem normalThreeCriticalExponent_cost (row : ℕ) :
    sourceHamiltonianExponentCost (normalThreeCriticalExponent row) =
      normalThreeCriticalVectorDegree row := by
  simp only [sourceHamiltonianExponentCost, normalThreeCriticalExponent,
    movingExponent, normalThreeCriticalVectorDegree, sourceVectorDegree,
    movingHamiltonianDegree, normalThreeCriticalRadialDegree]
  omega

/-- Any nonzero coefficient is visible in the support supremum of the same
sparse row.  No separate monomial noncancellation premise is needed because
equal exponents have already been combined by the coefficient map. -/
theorem coefficientCost_le_completeSourceVectorDegree
    {R : Type*} [Zero R] [DecidableEq R]
    (hamiltonian : SparseSourceHamiltonian R) (exponent : ℕ × ℕ)
    (coefficient_ne : hamiltonian exponent ≠ 0) :
    sourceHamiltonianExponentCost exponent ≤
      completeSourceVectorDegree hamiltonian := by
  exact Finset.le_sup (Finsupp.mem_support_iff.mpr coefficient_ne)

/-- The normal-two critical coefficient of a complete source-log row is
nonzero. -/
def sparseNormalTwoCoefficient
    {R : Type*} [Zero R]
    (rows : ℕ → SparseSourceHamiltonian R) (row : ℕ) : R :=
  rows (row + 1) (normalTwoCriticalExponent row)

/-- The normal-two critical coefficient of a complete source-log row is
nonzero. -/
def sparseNormalTwoNonzero
    {R : Type*} [Zero R]
    (rows : ℕ → SparseSourceHamiltonian R) (row : ℕ) : Prop :=
  sparseNormalTwoCoefficient rows row ≠ 0

/-- The normal-three critical coefficient of a complete source-log row is
nonzero. -/
def sparseNormalThreeCoefficient
    {R : Type*} [Zero R]
    (rows : ℕ → SparseSourceHamiltonian R) (row : ℕ) : R :=
  rows (row + 1) (normalThreeCriticalExponent row)

/-- The normal-three critical coefficient of a complete source-log row is
nonzero. -/
def sparseNormalThreeNonzero
    {R : Type*} [Zero R]
    (rows : ℕ → SparseSourceHamiltonian R) (row : ℕ) : Prop :=
  sparseNormalThreeCoefficient rows row ≠ 0

/-- Complete source cost of a sparse logarithmic row. -/
def sparseCompleteSourceCost
    {R : Type*} [Zero R] [DecidableEq R]
    (rows : ℕ → SparseSourceHamiltonian R) (order : ℕ) : ℕ :=
  completeSourceVectorDegree (rows order)

/-- Sparse coefficient identity derives normal-two visibility rather than
asking the schedule adapter for it. -/
theorem sparseNormalTwoCostVisible
    {R : Type*} [Zero R] [DecidableEq R]
    (rows : ℕ → SparseSourceHamiltonian R) (row : ℕ)
    (critical_ne : sparseNormalTwoNonzero rows row) :
    normalTwoCriticalVectorDegree row ≤
      sparseCompleteSourceCost rows (row + 1) := by
  rw [← normalTwoCriticalExponent_cost]
  exact coefficientCost_le_completeSourceVectorDegree
    (rows (row + 1)) (normalTwoCriticalExponent row) critical_ne

/-- Sparse coefficient identity derives normal-three visibility rather than
asking the schedule adapter for it. -/
theorem sparseNormalThreeCostVisible
    {R : Type*} [Zero R] [DecidableEq R]
    (rows : ℕ → SparseSourceHamiltonian R) (row : ℕ)
    (critical_ne : sparseNormalThreeNonzero rows row) :
    normalThreeCriticalVectorDegree row ≤
      sparseCompleteSourceCost rows (row + 1) := by
  rw [← normalThreeCriticalExponent_cost]
  exact coefficientCost_le_completeSourceVectorDegree
    (rows (row + 1)) (normalThreeCriticalExponent row) critical_ne

/-- A critical source row is present when either split coordinate is
nonzero. -/
def criticalSourceSupport
    (normalTwoNonzero normalThreeNonzero : ℕ → Prop) (row : ℕ) : Prop :=
  normalTwoNonzero row ∨ normalThreeNonzero row

/-- Explicit visibility of either split coordinate in the complete row cost
gives the exact rate-two support charge. -/
theorem criticalSourceSupport_costs
    (normalTwoNonzero normalThreeNonzero : ℕ → Prop)
    (completeSourceCost : ℕ → ℕ)
    (normalTwoCostVisible : ∀ row, normalTwoNonzero row →
      normalTwoCriticalVectorDegree row ≤ completeSourceCost (row + 1))
    (normalThreeCostVisible : ∀ row, normalThreeNonzero row →
      normalThreeCriticalVectorDegree row ≤ completeSourceCost (row + 1)) :
    ∀ row, criticalSourceSupport normalTwoNonzero normalThreeNonzero row →
      2 * row ≤ completeSourceCost (row + 1) := by
  intro row hsupport
  rcases hsupport with htwo | hthree
  · exact (criticalVectorDegree_lower_charge row).1.trans
      (normalTwoCostVisible row htwo)
  · exact (criticalVectorDegree_lower_charge row).2.trans
      (normalThreeCostVisible row hthree)

/-- A positive asymptotic margin below rate two makes the critical source
support finite once coordinate visibility in the complete source cost is
supplied. -/
theorem criticalSourceSupport_finite_of_positive_margin
    (normalTwoNonzero normalThreeNonzero : ℕ → Prop)
    (completeSourceCost : ℕ → ℕ)
    (margin denominator cutoff : ℕ)
    (margin_pos : 0 < margin)
    (marginTail : ∀ row, cutoff ≤ row →
      denominator * completeSourceCost (row + 1) + margin * (row + 1) ≤
        denominator * 2 * (row + 1))
    (normalTwoCostVisible : ∀ row, normalTwoNonzero row →
      normalTwoCriticalVectorDegree row ≤ completeSourceCost (row + 1))
    (normalThreeCostVisible : ∀ row, normalThreeNonzero row →
      normalThreeCriticalVectorDegree row ≤ completeSourceCost (row + 1)) :
    {row : ℕ |
      criticalSourceSupport normalTwoNonzero normalThreeNonzero row}.Finite := by
  exact rowSupport_finite_of_positive_margin
    (criticalSourceSupport normalTwoNonzero normalThreeNonzero)
    completeSourceCost 2 margin denominator cutoff margin_pos marginTail
    (criticalSourceSupport_costs normalTwoNonzero normalThreeNonzero
      completeSourceCost normalTwoCostVisible normalThreeCostVisible)

/-- A positive affine margin makes the coefficient-defined sparse critical
source support finite.  Unlike the abstract adapter above, this theorem has
no coordinate-visibility callbacks. -/
theorem sparseCriticalSourceSupport_finite_of_positive_margin
    {R : Type*} [Zero R] [DecidableEq R]
    (rows : ℕ → SparseSourceHamiltonian R)
    (margin denominator cutoff : ℕ)
    (margin_pos : 0 < margin)
    (marginTail : ∀ row, cutoff ≤ row →
      denominator * sparseCompleteSourceCost rows (row + 1) +
          margin * (row + 1) ≤ denominator * 2 * (row + 1)) :
    {row : ℕ | criticalSourceSupport
      (sparseNormalTwoNonzero rows)
      (sparseNormalThreeNonzero rows) row}.Finite := by
  exact criticalSourceSupport_finite_of_positive_margin
    (sparseNormalTwoNonzero rows) (sparseNormalThreeNonzero rows)
    (sparseCompleteSourceCost rows) margin denominator cutoff margin_pos
    marginTail (sparseNormalTwoCostVisible rows)
    (sparseNormalThreeCostVisible rows)

/-- The campaign's ordinary unshifted source upper linear growth below rate
two makes the coefficient-defined sparse critical support finite.  The affine
row/order shift is discharged by the generic filtered-support owner. -/
theorem sparseCriticalSourceSupport_finite_of_linearGrowthSup_lt
    {R : Type*} [Zero R] [DecidableEq R]
    (rows : ℕ → SparseSourceHamiltonian R)
    (subcritical :
      LinearGrowth.linearGrowthSup
          (fun order => (sparseCompleteSourceCost rows order : EReal)) <
        (2 : EReal)) :
    {row : ℕ | criticalSourceSupport
      (sparseNormalTwoNonzero rows)
      (sparseNormalThreeNonzero rows) row}.Finite := by
  exact rowSupport_finite_of_linearGrowthSup_lt
    (criticalSourceSupport
      (sparseNormalTwoNonzero rows)
      (sparseNormalThreeNonzero rows))
    (sparseCompleteSourceCost rows) 2 subcritical
    (criticalSourceSupport_costs
      (sparseNormalTwoNonzero rows)
      (sparseNormalThreeNonzero rows)
      (sparseCompleteSourceCost rows)
      (sparseNormalTwoCostVisible rows)
      (sparseNormalThreeCostVisible rows))

/-- Named family certificate binding the declared source statistic directly
to finite coefficient-defined critical support. -/
theorem critical_source_sparse_linear_growth_terminal_certificate
    {R : Type*} [Zero R] [DecidableEq R] :
    ∀ (rows : ℕ → SparseSourceHamiltonian R),
      LinearGrowth.linearGrowthSup
          (fun order => (sparseCompleteSourceCost rows order : EReal)) <
        (2 : EReal) →
      {row : ℕ | criticalSourceSupport
        (sparseNormalTwoNonzero rows)
        (sparseNormalThreeNonzero rows) row}.Finite :=
  sparseCriticalSourceSupport_finite_of_linearGrowthSup_lt

/-! ## Canonical polynomial packaging of the two source coordinates -/

open ZtareProofs.FormalDiagonalReesPolynomial
open Polynomial PowerSeries

/-- Strict source linear growth makes both declared critical coordinate
series canonical polynomials.  The theorem packages only row-indexed scalar
coordinates; the July actor/density normalization remains downstream. -/
theorem critical_source_sparse_polynomial_coordinates_terminal_certificate
    {R : Type*} [CommRing R] [DecidableEq R]
    (rows : ℕ → SparseSourceHamiltonian R)
    (subcritical :
      LinearGrowth.linearGrowthSup
          (fun order => (sparseCompleteSourceCost rows order : EReal)) <
        (2 : EReal)) :
    ∃ normalTwoCutoff normalThreeCutoff,
      (∀ row, normalTwoCutoff ≤ row →
        sparseNormalTwoCoefficient rows row = 0) ∧
      ((criticalPolynomial
          (pureDiagonalRows (sparseNormalTwoCoefficient rows))
          normalTwoCutoff : Polynomial R) : PowerSeries R) =
        PowerSeries.mk (sparseNormalTwoCoefficient rows) ∧
      (∀ row, normalThreeCutoff ≤ row →
        sparseNormalThreeCoefficient rows row = 0) ∧
      ((criticalPolynomial
          (pureDiagonalRows (sparseNormalThreeCoefficient rows))
          normalThreeCutoff : Polynomial R) : PowerSeries R) =
        PowerSeries.mk (sparseNormalThreeCoefficient rows) := by
  have unionFinite :=
    sparseCriticalSourceSupport_finite_of_linearGrowthSup_lt
      rows subcritical
  have normalTwoFinite :
      {row : ℕ | sparseNormalTwoCoefficient rows row ≠ 0}.Finite := by
    apply unionFinite.subset
    intro row hrow
    exact Or.inl hrow
  have normalThreeFinite :
      {row : ℕ | sparseNormalThreeCoefficient rows row ≠ 0}.Finite := by
    apply unionFinite.subset
    intro row hrow
    exact Or.inr hrow
  obtain ⟨normalTwoCutoff, normalTwoZero, normalTwoPolynomial⟩ :=
    finiteCoefficientSupport_has_canonicalPolynomial
      (sparseNormalTwoCoefficient rows) normalTwoFinite
  obtain ⟨normalThreeCutoff, normalThreeZero, normalThreePolynomial⟩ :=
    finiteCoefficientSupport_has_canonicalPolynomial
      (sparseNormalThreeCoefficient rows) normalThreeFinite
  exact ⟨normalTwoCutoff, normalThreeCutoff,
    normalTwoZero, normalTwoPolynomial,
    normalThreeZero, normalThreePolynomial⟩

/-! ## Exact July finite Lie-coordinate normalization -/

noncomputable section

/-- Canonical normal-two scalar polynomial extracted from the sparse source
rows. -/
def normalTwoScalarPolynomial
    (rows : ℕ → SparseSourceHamiltonian ℚ) (cutoff : ℕ) : ℚ[X] :=
  criticalPolynomial
    (pureDiagonalRows (sparseNormalTwoCoefficient rows)) cutoff

/-- Canonical normal-three scalar polynomial extracted from the sparse source
rows. -/
def normalThreeScalarPolynomial
    (rows : ℕ → SparseSourceHamiltonian ℚ) (cutoff : ℕ) : ℚ[X] :=
  criticalPolynomial
    (pureDiagonalRows (sparseNormalThreeCoefficient rows)) cutoff

/-- Tangent Witt generator in the audited July normalization.  The outer
coordinate factor and scalar `2` are part of the category identity. -/
def sourceWittLiePolynomial
    (rows : ℕ → SparseSourceHamiltonian ℚ) (normalTwoCutoff : ℕ) : ℚ[X] :=
  Polynomial.C 2 * Polynomial.X *
    normalTwoScalarPolynomial rows normalTwoCutoff

/-- Row-indexed split scalar
`j=b+(3*X*a'+8*a)/9`. -/
def sourceTensorScalarPolynomial
    (normalTwo normalThree : ℚ[X]) : ℚ[X] :=
  normalThree + Polynomial.C (1 / 9) *
    (Polynomial.C 3 * (Polynomial.X * normalTwo.derivative) +
      Polynomial.C 8 * normalTwo)

/-- Intrinsic tensor Lie coordinate.  The outer `X` converts the row-indexed
scalar `j` to `J`. -/
def sourceTensorLiePolynomial
    (rows : ℕ → SparseSourceHamiltonian ℚ)
    (normalTwoCutoff normalThreeCutoff : ℕ) : ℚ[X] :=
  Polynomial.X * sourceTensorScalarPolynomial
    (normalTwoScalarPolynomial rows normalTwoCutoff)
    (normalThreeScalarPolynomial rows normalThreeCutoff)

/-- Exact coefficient form of the corrected `+8` row-indexed split. -/
theorem coeff_sourceTensorScalarPolynomial
    (normalTwo normalThree : ℚ[X]) (row : ℕ) :
    (sourceTensorScalarPolynomial normalTwo normalThree).coeff row =
      normalThree.coeff row +
        ((3 * row + 8 : ℕ) : ℚ) / 9 * normalTwo.coeff row := by
  cases row with
  | zero =>
      simp [sourceTensorScalarPolynomial]
      ring
  | succ row =>
      simp only [sourceTensorScalarPolynomial, Polynomial.coeff_add,
        Polynomial.coeff_C_mul, Polynomial.coeff_X_mul,
        Polynomial.coeff_derivative]
      push_cast
      ring

/-- The intrinsic tensor coefficient has the mandatory one-power shift. -/
theorem coeff_sourceTensorLiePolynomial
    (rows : ℕ → SparseSourceHamiltonian ℚ)
    (normalTwoCutoff normalThreeCutoff row : ℕ) :
    (sourceTensorLiePolynomial rows normalTwoCutoff normalThreeCutoff).coeff
        (row + 1) =
      (normalThreeScalarPolynomial rows normalThreeCutoff).coeff row +
        ((3 * row + 8 : ℕ) : ℚ) / 9 *
          (normalTwoScalarPolynomial rows normalTwoCutoff).coeff row := by
  rw [sourceTensorLiePolynomial, Polynomial.coeff_X_mul]
  exact coeff_sourceTensorScalarPolynomial _ _ row

/-- Polynomial coercion preserves the tangent normalization exactly. -/
theorem coe_sourceWittLiePolynomial
    (rows : ℕ → SparseSourceHamiltonian ℚ) (normalTwoCutoff : ℕ) :
    ((sourceWittLiePolynomial rows normalTwoCutoff : ℚ[X]) : ℚ⟦X⟧) =
      PowerSeries.C 2 * PowerSeries.X *
        (normalTwoScalarPolynomial rows normalTwoCutoff : ℚ⟦X⟧) := by
  simp only [sourceWittLiePolynomial, Polynomial.coe_mul,
    Polynomial.coe_C, Polynomial.coe_X]

/-- Polynomial coercion preserves the corrected tensor normalization and its
derivative. -/
theorem coe_sourceTensorLiePolynomial
    (rows : ℕ → SparseSourceHamiltonian ℚ)
    (normalTwoCutoff normalThreeCutoff : ℕ) :
    ((sourceTensorLiePolynomial rows normalTwoCutoff normalThreeCutoff :
        ℚ[X]) : ℚ⟦X⟧) =
      PowerSeries.X *
        ((normalThreeScalarPolynomial rows normalThreeCutoff : ℚ⟦X⟧) +
          PowerSeries.C (1 / 9) *
            (PowerSeries.C 3 * (PowerSeries.X *
                d⁄dX ℚ
                  (normalTwoScalarPolynomial rows normalTwoCutoff : ℚ⟦X⟧)) +
              PowerSeries.C 8 *
                (normalTwoScalarPolynomial rows normalTwoCutoff :
                  ℚ⟦X⟧))) := by
  simp only [sourceTensorLiePolynomial, sourceTensorScalarPolynomial,
    Polynomial.coe_mul, Polynomial.coe_add, Polynomial.coe_C,
    Polynomial.coe_X, PowerSeries.derivative_coe]

/-- Strict source growth canonically produces the finite polynomial July Lie
pair `(f,J)`.  No polynomial witness is accepted as an input. -/
theorem critical_source_finite_lie_coordinates_terminal_certificate
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
      ((sourceWittLiePolynomial rows normalTwoCutoff : ℚ[X]) : ℚ⟦X⟧) =
        PowerSeries.C 2 * PowerSeries.X *
          PowerSeries.mk (sparseNormalTwoCoefficient rows) ∧
      ((sourceTensorLiePolynomial rows normalTwoCutoff normalThreeCutoff :
          ℚ[X]) : ℚ⟦X⟧) =
        PowerSeries.X *
          (PowerSeries.mk (sparseNormalThreeCoefficient rows) +
            PowerSeries.C (1 / 9) *
              (PowerSeries.C 3 * (PowerSeries.X *
                  d⁄dX ℚ
                    (PowerSeries.mk (sparseNormalTwoCoefficient rows))) +
                PowerSeries.C 8 * PowerSeries.mk
                  (sparseNormalTwoCoefficient rows))) ∧
      (∀ row,
        (sourceTensorLiePolynomial rows normalTwoCutoff normalThreeCutoff).coeff
            (row + 1) =
          (normalThreeScalarPolynomial rows normalThreeCutoff).coeff row +
            ((3 * row + 8 : ℕ) : ℚ) / 9 *
              (normalTwoScalarPolynomial rows normalTwoCutoff).coeff row) := by
  obtain ⟨normalTwoCutoff, normalThreeCutoff,
      normalTwoZero, normalTwoBinding,
      normalThreeZero, normalThreeBinding⟩ :=
    critical_source_sparse_polynomial_coordinates_terminal_certificate
      rows subcritical
  refine ⟨normalTwoCutoff, normalThreeCutoff,
    normalTwoZero, ?_, normalThreeZero, ?_, ?_, ?_, ?_⟩
  · simpa [normalTwoScalarPolynomial] using normalTwoBinding
  · simpa [normalThreeScalarPolynomial] using normalThreeBinding
  · rw [coe_sourceWittLiePolynomial]
    simpa [normalTwoScalarPolynomial] using normalTwoBinding
  · rw [coe_sourceTensorLiePolynomial]
    rw [show
      ((normalTwoScalarPolynomial rows normalTwoCutoff : ℚ[X]) : ℚ⟦X⟧) =
        PowerSeries.mk (sparseNormalTwoCoefficient rows) by
          simpa [normalTwoScalarPolynomial] using normalTwoBinding]
    rw [show
      ((normalThreeScalarPolynomial rows normalThreeCutoff : ℚ[X]) : ℚ⟦X⟧) =
        PowerSeries.mk (sparseNormalThreeCoefficient rows) by
          simpa [normalThreeScalarPolynomial] using normalThreeBinding]
  · exact coeff_sourceTensorLiePolynomial rows normalTwoCutoff
      normalThreeCutoff

end

/-- Aggregated July source-cost adapter.  Complete-row visibility remains a
premise and is therefore visible in the terminal signature. -/
theorem critical_source_cost_terminal_certificate :
    (∀ row, normalTwoCriticalVectorDegree row = 2 * row + 3) ∧
    (∀ row, normalThreeCriticalVectorDegree row = 2 * row) ∧
    (∀ row, 2 * row ≤ normalTwoCriticalVectorDegree row ∧
      2 * row ≤ normalThreeCriticalVectorDegree row) ∧
    (∀ (normalTwoNonzero normalThreeNonzero : ℕ → Prop)
        (completeSourceCost : ℕ → ℕ)
        (margin denominator cutoff : ℕ),
      0 < margin →
      (∀ row, cutoff ≤ row →
        denominator * completeSourceCost (row + 1) + margin * (row + 1) ≤
          denominator * 2 * (row + 1)) →
      (∀ row, normalTwoNonzero row →
        normalTwoCriticalVectorDegree row ≤ completeSourceCost (row + 1)) →
      (∀ row, normalThreeNonzero row →
        normalThreeCriticalVectorDegree row ≤
          completeSourceCost (row + 1)) →
      {row : ℕ |
        criticalSourceSupport normalTwoNonzero normalThreeNonzero row}.Finite) := by
  exact ⟨normalTwoCriticalVectorDegree_eq,
    normalThreeCriticalVectorDegree_eq,
    criticalVectorDegree_lower_charge,
    criticalSourceSupport_finite_of_positive_margin⟩

/-- Aggregated sparse-row visibility certificate.  The terminal binds
critical support to coefficients of the same complete source rows and hence
contains no external visibility premise. -/
theorem critical_source_sparse_visibility_terminal_certificate
    {R : Type*} [Zero R] [DecidableEq R] :
    (∀ row, sourceHamiltonianExponentCost
      (normalTwoCriticalExponent row) =
        normalTwoCriticalVectorDegree row) ∧
    (∀ row, sourceHamiltonianExponentCost
      (normalThreeCriticalExponent row) =
        normalThreeCriticalVectorDegree row) ∧
    (∀ (hamiltonian : SparseSourceHamiltonian R) exponent,
      hamiltonian exponent ≠ 0 →
      sourceHamiltonianExponentCost exponent ≤
        completeSourceVectorDegree hamiltonian) ∧
    (∀ (rows : ℕ → SparseSourceHamiltonian R)
        (margin denominator cutoff : ℕ),
      0 < margin →
      (∀ row, cutoff ≤ row →
        denominator * sparseCompleteSourceCost rows (row + 1) +
            margin * (row + 1) ≤ denominator * 2 * (row + 1)) →
      {row : ℕ | criticalSourceSupport
        (sparseNormalTwoNonzero rows)
        (sparseNormalThreeNonzero rows) row}.Finite) := by
  exact ⟨normalTwoCriticalExponent_cost,
    normalThreeCriticalExponent_cost,
    coefficientCost_le_completeSourceVectorDegree,
    sparseCriticalSourceSupport_finite_of_positive_margin⟩

end AxiomPackJacobianCriticalSourceCost
