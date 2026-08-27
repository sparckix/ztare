import ZtareProofs.FormalDiagonalReesPolynomial

/-!
# Tangent-generator binding on a critical Rees diagonal

The scalar row schedule is shifted by one spatial coordinate when it is
interpreted as a tangent vector-field generator.  This module preserves that
offset and binds the computed diagonal polynomial to the residue of the
complete regular Rees generator.  The unshifted extractor remains the
separate, source-stable theorem owner.
-/

namespace ZtareProofs.FormalDiagonalReesTangentGenerator

open Polynomial PowerSeries
open ZtareProofs.FormalDiagonalReesPolynomial

noncomputable section

variable {R : Type*} [CommRing R]

/-- Coefficient extension commutes with the complete regular Rees germ. -/
theorem regularReesGerm_map
    {S : Type*} [CommRing S]
    (hom : R →+* S) (rows : ℕ → R[X]) :
    PowerSeries.map (PowerSeries.map hom) (regularReesGerm rows) =
      regularReesGerm (fun row => (rows row).map hom) := by
  ext spatialDegree reesOrder
  simp [regularReesGerm, PowerSeries.coeff_map,
    Polynomial.coeff_map]

/-- Coefficient extension commutes with the canonical critical
polynomial. -/
theorem criticalPolynomial_map
    {S : Type*} [CommRing S]
    (hom : R →+* S) (rows : ℕ → R[X]) (cutoff : ℕ) :
    (criticalPolynomial rows cutoff).map hom =
      criticalPolynomial (fun row => (rows row).map hom) cutoff := by
  ext degree
  by_cases hdegree : degree < cutoff
  · simp [criticalPolynomial, PowerSeries.coeff_trunc, hdegree,
      criticalResidue, regularReesGerm, Polynomial.coeff_map]
  · simp [criticalPolynomial, PowerSeries.coeff_trunc, hdegree,
      criticalResidue, regularReesGerm,
      Polynomial.coeff_map]

/-- The actual tangent generator retains the outer coordinate factor. -/
def regularReesTangentGenerator
    (rows : ℕ → R[X]) : ReesGerm R :=
  PowerSeries.X * regularReesGerm rows

/-- Canonical polynomial generator on the critical tangent face. -/
def criticalTangentGenerator
    (rows : ℕ → R[X]) (cutoff : ℕ) : R[X] :=
  Polynomial.X * criticalPolynomial rows cutoff

/-- Eventual vanishing of the selected diagonal, rather than a bound on the
whole row degree, is enough to bind the finite tangent generator. -/
theorem criticalTangentGenerator_coe_eq_of_diagonal_eventually_zero
    (rows : ℕ → R[X]) (cutoff : ℕ)
    (diagonalZeroAfter :
      ∀ row, cutoff ≤ row → (rows row).coeff row = 0) :
    ((criticalTangentGenerator rows cutoff : R[X]) : PowerSeries R) =
      PowerSeries.map criticalResidue
        (regularReesTangentGenerator rows) := by
  rw [criticalTangentGenerator, regularReesTangentGenerator, map_mul]
  rw [Polynomial.coe_mul, Polynomial.coe_X]
  rw [criticalPolynomial_coe_eq_of_diagonal_eventually_zero
    rows cutoff diagonalZeroAfter]
  simp

/-- The computed tangent polynomial is exactly the residue of the complete
regular Rees tangent generator. -/
theorem criticalTangentGenerator_coe_eq
    (rows : ℕ → R[X]) (cutoff : ℕ)
    (strictAfter :
      ∀ row, cutoff ≤ row → (rows row).natDegree < row) :
    ((criticalTangentGenerator rows cutoff : R[X]) : PowerSeries R) =
      PowerSeries.map criticalResidue
        (regularReesTangentGenerator rows) := by
  apply criticalTangentGenerator_coe_eq_of_diagonal_eventually_zero
  intro row hrow
  exact Polynomial.coeff_eq_zero_of_natDegree_lt
    (strictAfter row hrow)

/-- Below the cutoff, tangent degree `d+1` is exactly the scalar schedule
diagonal in degree `d`. -/
theorem coeff_succ_criticalTangentGenerator
    (rows : ℕ → R[X]) (cutoff degree : ℕ)
    (hdegree : degree < cutoff) :
    (criticalTangentGenerator rows cutoff).coeff (degree + 1) =
      (rows degree).coeff degree := by
  rw [criticalTangentGenerator, Polynomial.coeff_X_mul]
  rw [criticalPolynomial, PowerSeries.coeff_trunc, if_pos hdegree]
  exact coeff_map_criticalResidue_regularReesGerm rows degree

/-- Every shifted critical generator has zero constant coefficient. -/
theorem criticalTangentGenerator_coeff_zero
    (rows : ℕ → R[X]) (cutoff : ℕ) :
    (criticalTangentGenerator rows cutoff).coeff 0 = 0 := by
  simp [criticalTangentGenerator]

/-- A zero scalar constant diagonal gives a tangent generator with zero
linear coefficient. -/
theorem criticalTangentGenerator_coeff_one
    (rows : ℕ → R[X]) (cutoff : ℕ)
    (hconstant : (criticalPolynomial rows cutoff).coeff 0 = 0) :
    (criticalTangentGenerator rows cutoff).coeff 1 = 0 := by
  simpa [criticalTangentGenerator] using hconstant

section Domain

variable [IsDomain R]

/-- A nonzero scalar diagonal remains nonzero after the tangent shift. -/
theorem criticalTangentGenerator_ne_zero
    (rows : ℕ → R[X]) (cutoff : ℕ)
    (hnonzero : criticalPolynomial rows cutoff ≠ 0) :
    criticalTangentGenerator rows cutoff ≠ 0 := by
  exact mul_ne_zero Polynomial.X_ne_zero hnonzero

end Domain

/-- Aggregated shifted-diagonal certificate. -/
theorem tangent_diagonal_rees_terminal_certificate
    (rows : ℕ → R[X]) (cutoff degree : ℕ)
    (strictAfter :
      ∀ row, cutoff ≤ row → (rows row).natDegree < row)
    (hdegree : degree < cutoff)
    (hconstant : (criticalPolynomial rows cutoff).coeff 0 = 0) :
    ((criticalTangentGenerator rows cutoff : R[X]) : PowerSeries R) =
        PowerSeries.map criticalResidue
          (regularReesTangentGenerator rows) ∧
      (criticalTangentGenerator rows cutoff).coeff (degree + 1) =
        (rows degree).coeff degree ∧
      (criticalTangentGenerator rows cutoff).coeff 0 = 0 ∧
      (criticalTangentGenerator rows cutoff).coeff 1 = 0 := by
  exact ⟨criticalTangentGenerator_coe_eq rows cutoff strictAfter,
    coeff_succ_criticalTangentGenerator rows cutoff degree hdegree,
    criticalTangentGenerator_coeff_zero rows cutoff,
    criticalTangentGenerator_coeff_one rows cutoff hconstant⟩

end


end ZtareProofs.FormalDiagonalReesTangentGenerator
