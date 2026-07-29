import ZtareProofs.AxiomPackJacobianGaugeMinimum

/-!
Kernel arithmetic for the first unrestricted contact-gauge obstruction of the
normalized Jacobian deformation.

The accompanying exact filtered linear-algebra certificate establishes that
the complete source-degree-five order-one fiber is the affine line generated
by the stabilizer below, that the complete order-three quotient obstruction is
`lambda`, and that after `lambda = 0` the complete order-four quotient contains
the constant obstruction `1`.  This file checks the polynomial stabilizer and
the terminal reduced obstruction algebra.  Exhaustiveness of the filtered
matrices remains a separate carried finite certificate.
-/

namespace AxiomPackJacobianUnrestrictedGaugeFourth

open AxiomPackJacobianGaugeMinimum

def stabilizerHamiltonian (P Q : ℚ) : ℚ :=
  -P^3 / 3 + 3 * P * Q / 2 - 9 * Q^2 / 4

def stabilizerTargetP (P Q : ℚ) : ℚ :=
  3 * P / 2 - 9 * Q / 2

def stabilizerTargetQ (P Q : ℚ) : ℚ :=
  P^2 - 3 * Q / 2

theorem stabilizer_target_components (P Q : ℚ) :
    stabilizerTargetP P Q =
        (3 * P / 2 - 9 * Q / 2) ∧
      stabilizerTargetQ P Q = P^2 - 3 * Q / 2 := by
  simp [stabilizerTargetP, stabilizerTargetQ]

def stabilizerSourceU (v t : ℚ) : ℚ :=
  -v * (
    6 * t * v^3 + 24 * t * v^2 + 30 * t * v + 12 * t -
    9 * v^4 - 30 * v^3 - 23 * v^2 + 3 * v + 3
  ) / 2

def stabilizerSourceV (v t : ℚ) : ℚ :=
  (
    24 * t^2 * v^3 + 72 * t^2 * v^2 + 60 * t^2 * v +
    12 * t^2 - 108 * t * v^4 - 312 * t * v^3 -
    224 * t * v^2 - 12 * t * v + 12 * t +
    108 * v^5 + 270 * v^4 + 93 * v^3 - 71 * v^2
  ) / 8

/-- The order-one source field lies in the two quotient lift ideals:
`U ∈ (v,t)` and `V ∈ (t,v²)`. -/
theorem stabilizer_source_lift_ideals (v : ℚ) :
    stabilizerSourceU 0 0 = 0 ∧
    stabilizerSourceV 0 0 = 0 ∧
    stabilizerSourceV v 0 =
      v^2 * (108 * v^3 + 270 * v^2 + 93 * v - 71) / 8 := by
  constructor
  · norm_num [stabilizerSourceU]
  constructor
  · norm_num [stabilizerSourceV]
  · simp [stabilizerSourceV]
    ring

/-- Exact infinitesimal contact isotropy:
`dF₀ Z_* + X_{K_*} ∘ F₀ = 0`. -/
theorem seed_stabilizer_equation (v t : ℚ) :
    jacPVValue v t * stabilizerSourceU v t +
        jacPTValue v t * stabilizerSourceV v t +
        stabilizerTargetP (seedPValue v t) (seedQValue v t) = 0 ∧
    jacQVValue v t * stabilizerSourceU v t +
        jacQTValue v t * stabilizerSourceV v t +
        stabilizerTargetQ (seedPValue v t) (seedQValue v t) = 0 := by
  constructor <;>
    simp [jacPVValue, jacPTValue, jacQVValue, jacQTValue,
      stabilizerSourceU, stabilizerSourceV, stabilizerTargetP,
      stabilizerTargetQ, seedPValue, seedQValue, seedP, seedQ,
      gammaValue, wValue] <;>
    ring

def reducedOrderThreeObstruction (lambda : ℚ) : ℚ := lambda

/-- The complete reduced degree-five order-three condition forces the
order-one stabilizer coordinate back to the normalized slice. -/
theorem reduced_order_three_forces_normalized (lambda : ℚ) :
    reducedOrderThreeObstruction lambda = 0 ↔ lambda = 0 := by
  simp [reducedOrderThreeObstruction]

def reducedOrderFourObstructions (a0 : ℚ) : ℚ × ℚ := (1, a0)

/-- Once the order-three obstruction has set `lambda = 0`, the normalized
degree-five order-four quotient contains a constant obstruction. -/
theorem reduced_order_four_is_inconsistent :
    ¬ ∃ a0 : ℚ,
      (reducedOrderFourObstructions a0).1 = 0 ∧
      (reducedOrderFourObstructions a0).2 = 0 := by
  simp [reducedOrderFourObstructions]

/-- Compact kernel payload joining the explicit isotropy and the two reduced
obstruction equations. -/
theorem unrestricted_degree_five_reduced_certificate :
    (∀ v t : ℚ,
      jacPVValue v t * stabilizerSourceU v t +
          jacPTValue v t * stabilizerSourceV v t +
          stabilizerTargetP (seedPValue v t) (seedQValue v t) = 0 ∧
      jacQVValue v t * stabilizerSourceU v t +
          jacQTValue v t * stabilizerSourceV v t +
          stabilizerTargetQ (seedPValue v t) (seedQValue v t) = 0) ∧
    (∀ lambda : ℚ,
      reducedOrderThreeObstruction lambda = 0 ↔ lambda = 0) ∧
    (¬ ∃ a0 : ℚ,
      (reducedOrderFourObstructions a0).1 = 0 ∧
      (reducedOrderFourObstructions a0).2 = 0) := by
  exact ⟨seed_stabilizer_equation,
    reduced_order_three_forces_normalized,
    reduced_order_four_is_inconsistent⟩

def reducedBoundSixOrderFourObstructions
    (lambda : ℚ) : ℚ × ℚ := (lambda, lambda^2)

theorem reduced_bound_six_order_four_forces_normalized (lambda : ℚ) :
    ((reducedBoundSixOrderFourObstructions lambda).1 = 0 ∧
      (reducedBoundSixOrderFourObstructions lambda).2 = 0) ↔
      lambda = 0 := by
  simp [reducedBoundSixOrderFourObstructions]

def reducedBoundSixOrderFiveObstructions
    (a0 : ℚ) : ℚ × ℚ := (1, a0)

theorem reduced_bound_six_order_five_is_inconsistent :
    ¬ ∃ a0 : ℚ,
      (reducedBoundSixOrderFiveObstructions a0).1 = 0 ∧
      (reducedBoundSixOrderFiveObstructions a0).2 = 0 := by
  simp [reducedBoundSixOrderFiveObstructions]

/-- Reduced arithmetic payload for the next unrestricted step: degree six
forces the order-one stabilizer parameter to zero at order four, after which
the complete normalized order-five quotient contains `1`. -/
theorem unrestricted_degree_six_reduced_certificate :
    (∀ lambda : ℚ,
      ((reducedBoundSixOrderFourObstructions lambda).1 = 0 ∧
        (reducedBoundSixOrderFourObstructions lambda).2 = 0) ↔
        lambda = 0) ∧
    (¬ ∃ a0 : ℚ,
      (reducedBoundSixOrderFiveObstructions a0).1 = 0 ∧
      (reducedBoundSixOrderFiveObstructions a0).2 = 0) := by
  exact ⟨reduced_bound_six_order_four_forces_normalized,
    reduced_bound_six_order_five_is_inconsistent⟩

/-- At source bound seven, the complete order-three quotient leaves at most
one first-order isotropy coordinate. -/
theorem reduced_bound_seven_order_three
    (l0 l1 l2 : ℚ)
    (h2 : l2 = 0)
    (h01 : (2 * l0 + 3 * l1) / 3 = 0) :
    l0 = -3 * l1 / 2 ∧ l2 = 0 := by
  constructor
  · linarith
  · exact h2

/-- The square obstruction in the complete order-four quotient kills the
remaining first-order isotropy coordinate. -/
theorem reduced_bound_seven_order_four_forces_normalized
    (l0 l1 l2 h20 h21 h22 : ℚ)
    (h2 : l2 = 0)
    (h01 : (2 * l0 + 3 * l1) / 3 = 0)
    (_hlinear :
      (-1680 * h20 - 2520 * h21 + 777 * l1 + 179) / 179 = 0)
    (_h22 : h22 = 0)
    (hsquare : l1 ^ 2 = 0) :
    l0 = 0 ∧ l1 = 0 ∧ l2 = 0 := by
  have hl1 : l1 = 0 := by nlinarith
  constructor
  · linarith
  constructor
  · exact hl1
  · exact h2

/-- The normalized source-degree-seven order-six quotient contains the
constant obstruction `1`. -/
theorem reduced_bound_seven_order_six_is_inconsistent :
    ¬ ∃ a2 a3 b0 b1 b2 : ℚ,
      (1 : ℚ) = 0 ∧
      b2 = 0 ∧
      -(37 * a3 - 40 * b0 - 60 * b1) / 60 = 0 ∧
      a2 = 0 ∧
      a2 ^ 2 = 0 := by
  simp

/-- Arithmetic part of the slope-two upper certificate for the replayed
orders two through seven, whose source degrees are `(5,7,9,9,9,9)`. -/
theorem order_seven_source_profile_has_slope_two :
    ((5 - 1 : ℚ) / 2 = 2) ∧
    ((7 - 1 : ℚ) / 3 ≤ 2) ∧
    ((9 - 1 : ℚ) / 4 ≤ 2) ∧
    ((9 - 1 : ℚ) / 5 ≤ 2) ∧
    ((9 - 1 : ℚ) / 6 ≤ 2) ∧
    ((9 - 1 : ℚ) / 7 ≤ 2) := by
  norm_num

/-- Reduced kernel payload for the three-parameter source-bound-seven
calculation and the Lie-filtered source-degree profile.  Matrix
exhaustiveness and the full polynomial replay remain carried finite
certificates outside this arithmetic theorem. -/
theorem unrestricted_degree_seven_reduced_certificate :
    (∀ l0 l1 l2 h20 h21 h22 : ℚ,
      l2 = 0 →
      (2 * l0 + 3 * l1) / 3 = 0 →
      (-1680 * h20 - 2520 * h21 + 777 * l1 + 179) / 179 = 0 →
      h22 = 0 →
      l1 ^ 2 = 0 →
      l0 = 0 ∧ l1 = 0 ∧ l2 = 0) ∧
    (¬ ∃ a2 a3 b0 b1 b2 : ℚ,
      (1 : ℚ) = 0 ∧
      b2 = 0 ∧
      -(37 * a3 - 40 * b0 - 60 * b1) / 60 = 0 ∧
      a2 = 0 ∧
      a2 ^ 2 = 0) ∧
    (((5 - 1 : ℚ) / 2 = 2) ∧
      ((7 - 1 : ℚ) / 3 ≤ 2) ∧
      ((9 - 1 : ℚ) / 4 ≤ 2) ∧
      ((9 - 1 : ℚ) / 5 ≤ 2) ∧
      ((9 - 1 : ℚ) / 6 ≤ 2) ∧
      ((9 - 1 : ℚ) / 7 ≤ 2)) := by
  exact ⟨
    fun l0 l1 l2 h20 h21 h22 =>
      reduced_bound_seven_order_four_forces_normalized
        l0 l1 l2 h20 h21 h22,
    reduced_bound_seven_order_six_is_inconsistent,
    order_seven_source_profile_has_slope_two
  ⟩

/-- Arithmetic extension of the slope-two profile to the exact order-eight
source degree `17`. -/
theorem order_eight_source_profile_has_slope_two :
    (((5 - 1 : ℚ) / 2 = 2) ∧
      ((7 - 1 : ℚ) / 3 ≤ 2) ∧
      ((9 - 1 : ℚ) / 4 ≤ 2) ∧
      ((9 - 1 : ℚ) / 5 ≤ 2) ∧
      ((9 - 1 : ℚ) / 6 ≤ 2) ∧
      ((9 - 1 : ℚ) / 7 ≤ 2)) ∧
    ((17 - 1 : ℚ) / 8 = 2) := by
  exact ⟨order_seven_source_profile_has_slope_two, by norm_num⟩

/-- Provider-free ratification target for the reduced bound-seven
obstruction together with the order-eight slope arithmetic.  The exact
order-eight matrix solve and coefficientwise replay are separate finite
certificates. -/
theorem unrestricted_degree_eight_slope_reduced_certificate :
    (∀ l0 l1 l2 h20 h21 h22 : ℚ,
      l2 = 0 →
      (2 * l0 + 3 * l1) / 3 = 0 →
      (-1680 * h20 - 2520 * h21 + 777 * l1 + 179) / 179 = 0 →
      h22 = 0 →
      l1 ^ 2 = 0 →
      l0 = 0 ∧ l1 = 0 ∧ l2 = 0) ∧
    ((((5 - 1 : ℚ) / 2 = 2) ∧
      ((7 - 1 : ℚ) / 3 ≤ 2) ∧
      ((9 - 1 : ℚ) / 4 ≤ 2) ∧
      ((9 - 1 : ℚ) / 5 ≤ 2) ∧
      ((9 - 1 : ℚ) / 6 ≤ 2) ∧
      ((9 - 1 : ℚ) / 7 ≤ 2)) ∧
      ((17 - 1 : ℚ) / 8 = 2)) := by
  exact ⟨
    fun l0 l1 l2 h20 h21 h22 =>
      reduced_bound_seven_order_four_forces_normalized
        l0 l1 l2 h20 h21 h22,
    order_eight_source_profile_has_slope_two
  ⟩

end AxiomPackJacobianUnrestrictedGaugeFourth
