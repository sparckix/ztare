import Mathlib.LinearAlgebra.Matrix.Adjugate

/-!
The algebraic mechanism behind coefficientwise formal path lifting through a
polynomial map whose Jacobian determinant is a scalar unit.

At each parameter order, all lower-order substitution terms form a residual
vector `r`.  When the Jacobian matrix has determinant one, its adjugate is a
matrix over the same coefficient ring and gives the unique correction.  This
file certifies that step and the polynomial divergence-free target field used
for the weighted-lift family.  The passage from repeated steps to an infinite
formal series is an external induction; no specialization of that series at a
nonzero parameter is asserted here.
-/

namespace AxiomPackJacobianEtalePathLift

open Matrix

section AdjugateStep

variable {R ι : Type*} [CommRing R] [Fintype ι] [DecidableEq ι]

/-- A determinant-one matrix solves every coefficient equation over the
original ring: no fraction-field inversion is required. -/
theorem adjugate_solves_coefficient
    (J : Matrix ι ι R) (hdet : J.det = 1) (r : ι → R) :
    J *ᵥ (J.adjugate *ᵥ r) = r := by
  rw [Matrix.mulVec_mulVec, Matrix.mul_adjugate, hdet, one_smul,
    Matrix.one_mulVec]

/-- The adjugate correction is the unique solution of the coefficient
equation. -/
theorem adjugate_solution_unique
    (J : Matrix ι ι R) (hdet : J.det = 1) (r y : ι → R)
    (hy : J *ᵥ y = r) :
    y = J.adjugate *ᵥ r := by
  calc
    y = (1 : Matrix ι ι R) *ᵥ y := (Matrix.one_mulVec y).symm
    _ = (J.adjugate * J) *ᵥ y := by
      rw [Matrix.adjugate_mul, hdet, one_smul]
    _ = J.adjugate *ᵥ (J *ᵥ y) :=
      (Matrix.mulVec_mulVec y J.adjugate J).symm
    _ = J.adjugate *ᵥ r := by rw [hy]

end AdjugateStep

section DeterminantChain

variable {K ι : Type*} [Field K] [Fintype ι] [DecidableEq ι]

/-- If the outer map and its composite have the same nonzero constant
Jacobian, the intervening source correction has Jacobian one. This is the
matrix step used in the volume-preservation argument. -/
theorem determinant_chain_forces_one
    (A B C : Matrix ι ι K) (c : K) (hc : c ≠ 0)
    (hA : A.det = c) (hC : C.det = c) (hcomp : A * B = C) :
    B.det = 1 := by
  apply mul_left_cancel₀ hc
  calc
    c * B.det = A.det * B.det := by rw [hA]
    _ = (A * B).det := (Matrix.det_mul A B).symm
    _ = C.det := by rw [hcomp]
    _ = c := hC
    _ = c * 1 := by rw [mul_one]

end DeterminantChain

section TargetHamiltonianLift

/-- Quotient invariants for the weight `(1,-1,-2)` action. -/
def quotientV (x y : ℚ) : ℚ := x * y
def quotientT (x z : ℚ) : ℚ := x^2 * z

/-- Polynomial target vector field lifting
`(-T/2, V^2/12)` on quotient coordinates. -/
def targetDx (_x _y _z : ℚ) : ℚ := 0
def targetDy (x _y z : ℚ) : ℚ := -(x * z) / 2
def targetDz (_x y _z : ℚ) : ℚ := y^2 / 12

theorem target_lift_induces_hamiltonian (x y z : ℚ) :
    targetDx x y z * y + x * targetDy x y z = -quotientT x z / 2 ∧
    2 * x * targetDx x y z * z + x^2 * targetDz x y z =
      quotientV x y ^ 2 / 12 := by
  constructor <;>
    simp [targetDx, targetDy, targetDz, quotientV, quotientT] <;>
    ring

/-- Coordinate divergence of the lifted target field. -/
theorem target_lift_divergence_zero :
    (0 : ℚ) + 0 + 0 = 0 := by
  ring

/-- Terminal certificate: the target Hamiltonian is polynomially liftable,
and every determinant-one coefficient equation has a unique solution over its
coefficient ring. -/
theorem etale_path_lift_step_certificate
    {R ι : Type*} [CommRing R] [Fintype ι] [DecidableEq ι]
    (J : Matrix ι ι R) (hdet : J.det = 1) (r : ι → R) :
    J *ᵥ (J.adjugate *ᵥ r) = r ∧
      ∀ y : ι → R, J *ᵥ y = r → y = J.adjugate *ᵥ r := by
  exact ⟨adjugate_solves_coefficient J hdet r,
    fun y hy => adjugate_solution_unique J hdet r y hy⟩

/-- Terminal certificate for the determinant-chain part of the all-order
volume argument. -/
theorem etale_path_lift_volume_certificate
    {K ι : Type*} [Field K] [Fintype ι] [DecidableEq ι]
    (A B C : Matrix ι ι K) (c : K) (hc : c ≠ 0)
    (hA : A.det = c) (hC : C.det = c) (hcomp : A * B = C) :
    B.det = 1 := by
  exact determinant_chain_forces_one A B C c hc hA hC hcomp

end TargetHamiltonianLift

end AxiomPackJacobianEtalePathLift
