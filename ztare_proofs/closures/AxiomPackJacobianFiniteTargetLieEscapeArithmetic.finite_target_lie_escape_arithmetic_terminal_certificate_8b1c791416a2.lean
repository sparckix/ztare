import ZtareProofs.AxiomPackJacobianSecondTransverseQuotientArithmetic

/-!
Arithmetic carrier for the complete finite-target Lie escape.

After the target-algebra and exceptional-divisor classifications, the first
two immutable source jets have layer-one spectral components in degrees
three and four.  Their bracket starts the graded ray

`c_j * D_(z^(6+3*j))^(2+j)`,

with source degree `8+4*j` and coefficient multiplier

`-7*(j+6)*(2*j+1)/(64*(j+5))`.

The cusp-centralizer classification, divisor-profile completeness, source
jet extraction, and identification of the graded bracket remain in the
deterministic replays and pencil proof.  This file checks the exact spectral
arithmetic and proves that the carried recurrence never vanishes.
-/

namespace AxiomPackJacobianFiniteTargetLieEscapeArithmetic

/-- Eigenvalue of the affine layer-zero action on `z^d` in layer one. -/
def layerOneEigenvalue (d : ℕ) : ℚ :=
  (4 - 3 * (d : ℚ)) / 16

theorem layer_one_eigenvalues :
    layerOneEigenvalue 0 = 1 / 4 ∧
    layerOneEigenvalue 1 = 1 / 16 ∧
    layerOneEigenvalue 2 = -1 / 8 ∧
    layerOneEigenvalue 3 = -5 / 16 ∧
    layerOneEigenvalue 4 = -1 / 2 := by
  norm_num [layerOneEigenvalue]

theorem degree_three_four_eigenvalues_distinct :
    layerOneEigenvalue 3 ≠ layerOneEigenvalue 4 := by
  norm_num [layerOneEigenvalue]

/-- Multiplier from one further bracket with the projected `z^4` field. -/
def rayMultiplier (j : ℕ) : ℚ :=
  -7 * ((j : ℚ) + 6) * (2 * (j : ℚ) + 1) /
    (64 * ((j : ℚ) + 5))

theorem ray_multiplier_nonzero (j : ℕ) :
    rayMultiplier j ≠ 0 := by
  unfold rayMultiplier
  positivity

/-- Exact rational coefficient sequence of the associated-graded ray. -/
def rayCoefficient : ℕ → ℚ
  | 0 => -1225 / 18432
  | j + 1 => rayCoefficient j * rayMultiplier j

theorem ray_coefficient_zero :
    rayCoefficient 0 = -1225 / 18432 := by
  norm_num [rayCoefficient]

theorem ray_coefficient_nonzero (j : ℕ) :
    rayCoefficient j ≠ 0 := by
  induction j with
  | zero =>
      norm_num [rayCoefficient]
  | succ j inductionHypothesis =>
      simp only [rayCoefficient]
      exact mul_ne_zero inductionHypothesis (ray_multiplier_nonzero j)

/-- Spatial degree of the `j`-th source field in the ray. -/
def rayDegree (j : ℕ) : ℕ :=
  8 + 4 * j

theorem ray_degree_step (j : ℕ) :
    rayDegree (j + 1) = rayDegree j + 4 := by
  simp [rayDegree]
  omega

theorem ray_degree_strictMono :
    StrictMono rayDegree := by
  intro first second h
  simp [rayDegree]
  omega

theorem ray_degree_unbounded (bound : ℕ) :
    ∃ j : ℕ, bound < rayDegree j := by
  refine ⟨bound + 1, ?_⟩
  simp [rayDegree]
  omega

/-- Terminal arithmetic certificate for the nonzero unbounded source ray. -/
theorem finite_target_lie_escape_arithmetic_terminal_certificate :
    (layerOneEigenvalue 3 = -5 / 16) ∧
    (layerOneEigenvalue 4 = -1 / 2) ∧
    (layerOneEigenvalue 3 ≠ layerOneEigenvalue 4) ∧
    (rayCoefficient 0 = -1225 / 18432) ∧
    (∀ j : ℕ, rayCoefficient j ≠ 0) ∧
    (∀ j : ℕ, rayDegree (j + 1) = rayDegree j + 4) ∧
    (∀ bound : ℕ, ∃ j : ℕ, bound < rayDegree j) := by
  exact ⟨layer_one_eigenvalues.2.2.2.1,
    layer_one_eigenvalues.2.2.2.2,
    degree_three_four_eigenvalues_distinct,
    ray_coefficient_zero,
    ray_coefficient_nonzero,
    ray_degree_step,
    ray_degree_unbounded⟩

end AxiomPackJacobianFiniteTargetLieEscapeArithmetic
