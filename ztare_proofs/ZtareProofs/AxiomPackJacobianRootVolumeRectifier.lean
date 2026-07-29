import Mathlib.Tactic

/-!
Invariant algebra behind the root-cover volume rectifier for the normalized
Jacobian deformation.

The finite inverse cover is the cubic

  W^3 - W^2 + P W - Q = 0.

A trace-zero quadratic root field induces a vector field on `(P,Q)`.  The
selected divergence right inverse has a polynomial source lift because its
two free root coefficients sum to an element of `(P,Q)`.  This file checks
the root-contact identity, the divergence reduction, the divisibility
identity, the first correction, and the arithmetic behind the filtered
inverse.  Construction of the compatible infinite formal maps is the
coefficient induction documented with the source artifact.
-/

namespace AxiomPackJacobianRootVolumeRectifier

def cubic (P Q W : ℚ) : ℚ := W^3 - W^2 + P * W - Q

def cubicDerivative (P W : ℚ) : ℚ := 3 * W^2 - 2 * W + P

def rootA (P b c : ℚ) : ℚ := -(b + (1 - 2 * P) * c) / 3

def rootField (P W b c : ℚ) : ℚ :=
  rootA P b c + b * W + c * W^2

def targetP (P Q b c : ℚ) : ℚ :=
  (6 * P * b + 7 * P * c - 9 * Q * c - 2 * b - 2 * c) / 3

def targetQ (P Q b c : ℚ) : ℚ :=
  (2 * P^2 * c - P * b - P * c + 9 * Q * b + 3 * Q * c) / 3

/-- A trace-zero quadratic field on the roots descends to the displayed
coefficient field.  The identity is polynomial, before imposing the cubic
relation. -/
theorem root_contact_polynomial_identity (P Q W b c : ℚ) :
    cubicDerivative P W * rootField P W b c
        + targetP P Q b c * W - targetQ P Q b c =
      (3 * W * c + 3 * b + c) * cubic P Q W := by
  simp [cubicDerivative, rootField, rootA, targetP, targetQ, cubic]
  ring

theorem root_contact_on_finite_sheet
    (P Q W b c : ℚ) (hroot : cubic P Q W = 0) :
    cubicDerivative P W * rootField P W b c
        + targetP P Q b c * W - targetQ P Q b c = 0 := by
  rw [root_contact_polynomial_identity, hroot, mul_zero]

/-- Algebraic value of the coordinate divergence when `bP,bQ,cP,cQ`
denote the four formal partial derivatives. -/
def targetDivergenceJet
    (P Q b c bP bQ cP cQ : ℚ) : ℚ :=
  (
    6 * b + 6 * P * bP + 7 * c + 7 * P * cP
      - 9 * Q * cP - 2 * bP - 2 * cP
    + 2 * P^2 * cQ - P * bQ - P * cQ
      + 9 * b + 9 * Q * bQ + 3 * c + 3 * Q * cQ
  ) / 3

def filteredOperatorValue (P Q q qP qQ : ℚ) : ℚ :=
  5 * q + (2 * P - 2 / 3) * qP + (3 * Q - P / 3) * qQ

/-- If `b=q+2q0` and `c=-3q0`, the divergence loses the auxiliary scalar
and is exactly the triangular filtered operator applied to `q`. -/
theorem selected_divergence_identity
    (P Q q q0 qP qQ : ℚ) :
    targetDivergenceJet P Q (q + 2 * q0) (-3 * q0) qP qQ 0 0 =
      filteredOperatorValue P Q q qP qQ := by
  simp [targetDivergenceJet, filteredOperatorValue]
  ring

/-- The source-polynomiality condition is automatic for the selected
right-inverse coefficients once `q0` is the constant part of `q`. -/
theorem selected_liftability_identity (q q0 : ℚ) :
    (q + 2 * q0) + (-3 * q0) = q - q0 := by
  ring

def sourceGamma (W gamma b c : ℚ) : ℚ :=
  gamma * (2 * b + c * W + c)

/-- Cleared numerator of the lifted `v` component. -/
def sourceVNumerator (P W gamma b c : ℚ) : ℚ :=
  gamma * rootField P W b c - W * sourceGamma W gamma b c

/-- For `q=e+q0`, the selected root field exposes exactly one factor of the
exceptional coordinate `gamma`. -/
theorem selected_source_divisibility
    (P W gamma e q0 : ℚ)
    (hP : P = gamma + 2 * W - 3 * W ^ 2) :
    sourceVNumerator P W gamma (e + 3 * q0) (-3 * q0) =
      -(gamma / 3) * (e * (3 * W + 1) + 6 * q0 * P) := by
  rw [hP]
  simp [sourceVNumerator, sourceGamma, rootField, rootA]
  ring

/-- If both `e` and `P` carry the exceptional factor, the quotient source
component is polynomial. -/
theorem selected_source_polynomial_quotient
    (P W gamma e eBar pBar q0 : ℚ)
    (hP : P = gamma * pBar)
    (he : e = gamma * eBar) :
    -(gamma / 3) * (e * (3 * W + 1) + 6 * q0 * P) =
      gamma^2 * (-(eBar * (3 * W + 1) + 6 * q0 * pBar) / 3) := by
  rw [hP, he]
  ring

/-- The diagonal coefficient in the filtered inverse is never zero in
characteristic zero. -/
theorem filtered_diagonal_nonzero (i j : ℕ) :
    (5 + 2 * (i : ℚ) + 3 * (j : ℚ)) ≠ 0 := by
  positivity

/-- The constant derivative term strictly lowers the `(4,6)` filtration. -/
theorem filtered_lowering_P
    (i j : ℕ) (hi : 0 < i) :
    4 * (i - 1) + 6 * j < 4 * i + 6 * j := by
  omega

/-- The `P * d/dQ` term also strictly lowers the `(4,6)` filtration. -/
theorem filtered_lowering_Q
    (i j : ℕ) (hj : 0 < j) :
    4 * (i + 1) + 6 * (j - 1) < 4 * i + 6 * j := by
  omega

/-- Composition of `r` slope-two coefficients and the `r-1` derivatives in
a substitution word stays in the same slope-two envelope. -/
theorem slope_two_word_envelope
    (n r degreeSum : ℕ)
    (hr : 0 < r)
    (hdegree : degreeSum ≤ 2 * n + r) :
    degreeSum - (r - 1) ≤ 2 * n + 1 := by
  omega

/-!
The reciprocal escaping root has a sharp associated-graded shell.  With
`x=s²P`, `y=s³Q`, and `z=sZ+…`, its lowest-Rees equation is

  `Z = 1/4 - x Z³ + y Z⁴`.

Lagrange inversion gives the two coefficient families below.  The formal
series extraction is checked by the deterministic replay; this section
certifies their nonvanishing and exact filtration arithmetic.
-/

def oddEscapingRootCoefficient (k : ℕ) : ℚ :=
  ((-1 : ℚ)^k * (Nat.choose (3 * k) k : ℚ)) /
    (4 * 16^k * (2 * (k : ℚ) + 1))

def evenEscapingRootCoefficient (k : ℕ) : ℚ :=
  ((-1 : ℚ)^k * (2 * (k : ℚ) + 5) *
      (Nat.choose (3 * k + 5) k : ℚ)) /
    ((3 * (k : ℚ) + 5) * 4^(2 * k + 4))

theorem odd_escaping_root_coefficient_ne_zero (k : ℕ) :
    oddEscapingRootCoefficient k ≠ 0 := by
  unfold oddEscapingRootCoefficient
  apply div_ne_zero
  · apply mul_ne_zero
    · exact pow_ne_zero k (by norm_num)
    · exact_mod_cast
        (Nat.choose_pos (by omega : k ≤ 3 * k)).ne'
  · positivity

theorem even_escaping_root_coefficient_ne_zero (k : ℕ) :
    evenEscapingRootCoefficient k ≠ 0 := by
  unfold evenEscapingRootCoefficient
  apply div_ne_zero
  · apply mul_ne_zero
    · apply mul_ne_zero
      · exact pow_ne_zero k (by norm_num)
      · exact ne_of_gt (by positivity :
          (0 : ℚ) < 2 * (k : ℚ) + 5)
    · exact_mod_cast
        (Nat.choose_pos (by omega : k ≤ 3 * k + 5)).ne'
  · positivity

theorem odd_escaping_root_sharp_degree (k : ℕ) :
    4 * k = 2 * (2 * k + 1) - 2 := by
  omega

theorem even_escaping_root_sharp_degree (k : ℕ) :
    4 * k + 6 = 2 * (2 * k + 4) - 2 := by
  omega

theorem escaping_root_sharp_shell_arithmetic_certificate :
    (∀ k : ℕ, oddEscapingRootCoefficient k ≠ 0) ∧
      (∀ k : ℕ, evenEscapingRootCoefficient k ≠ 0) ∧
      (∀ k : ℕ, 4 * k = 2 * (2 * k + 1) - 2) ∧
      (∀ k : ℕ, 4 * k + 6 = 2 * (2 * k + 4) - 2) := by
  exact ⟨odd_escaping_root_coefficient_ne_zero,
    even_escaping_root_coefficient_ne_zero,
    odd_escaping_root_sharp_degree,
    even_escaping_root_sharp_degree⟩

section FirstRectifier

def firstA (P : ℚ) : ℚ := -P / 6
def firstB : ℚ := 1 / 4
def firstC : ℚ := -1 / 4

theorem first_trace_zero (P : ℚ) :
    3 * firstA P + firstB + (1 - 2 * P) * firstC = 0 := by
  simp [firstA, firstB, firstC]
  ring

theorem first_target_field (P Q : ℚ) :
    targetP P Q firstB firstC = -P / 12 + 3 * Q / 4 ∧
      targetQ P Q firstB firstC = -P^2 / 6 + Q / 2 := by
  constructor <;> simp [targetP, targetQ, firstB, firstC] <;> ring

theorem first_divergence :
    targetDivergenceJet 0 0 firstB firstC 0 0 0 0 = 5 / 12 := by
  norm_num [targetDivergenceJet, firstB, firstC]

end FirstRectifier

/-- Terminal aggregation of the invariant root-cover rectifier checks. -/
theorem root_volume_rectifier_certificate (P Q W : ℚ) :
    cubicDerivative P W * rootField P W firstB firstC
          + targetP P Q firstB firstC * W
          - targetQ P Q firstB firstC =
        (3 * W * firstC + 3 * firstB + firstC) * cubic P Q W ∧
      targetP P Q firstB firstC = -P / 12 + 3 * Q / 4 ∧
      targetQ P Q firstB firstC = -P^2 / 6 + Q / 2 ∧
      targetDivergenceJet 0 0 firstB firstC 0 0 0 0 = 5 / 12 := by
  refine ⟨root_contact_polynomial_identity P Q W firstB firstC, ?_⟩
  exact ⟨(first_target_field P Q).1, (first_target_field P Q).2,
    first_divergence⟩

end AxiomPackJacobianRootVolumeRectifier
