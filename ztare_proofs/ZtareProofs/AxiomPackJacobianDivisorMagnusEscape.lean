import Mathlib.Tactic

/-!
Kernel endpoints for the exceptional-divisor Magnus escape theorem.

The deterministic bridge restricts the regular source-only connection to
`γ = 0`, changes coordinate to `y = 2v + 3`, and identifies the first three
Witt fields.  The top Magnus coefficient is the even part of
`x / (2 * (exp x - 1))`.  Its absolute coefficients obey the positive
convolution recurrence below.  The leading iterated-Witt coefficient obeys
the second recurrence below.
-/

namespace AxiomPackJacobianDivisorMagnusEscape

open scoped BigOperators

/-- The elementary absolute-value recurrence for the even coefficients of
`(x / 2) * coth (x / 2)` is strictly positive at every positive index. -/
theorem positive_even_coefficient_recurrence
    (a : ℕ → ℚ)
    (hOne : a 1 = 1 / 12)
    (hRec :
      ∀ m : ℕ, 2 ≤ m →
        a m =
          (∑ i ∈ Finset.Icc 1 (m - 1), a i * a (m - i)) /
            (2 * (m : ℚ) + 1)) :
    ∀ m : ℕ, 1 ≤ m → 0 < a m := by
  intro m
  induction m using Nat.strong_induction_on with
  | h m ih =>
      intro hm
      by_cases hmOne : m = 1
      · subst m
        rw [hOne]
        norm_num
      · have hmTwo : 2 ≤ m := by omega
        rw [hRec m hmTwo]
        apply div_pos
        · apply Finset.sum_pos
          · intro i hi
            have hiBounds := Finset.mem_Icc.mp hi
            have hiLt : i < m := by omega
            have hmiLt : m - i < m := by omega
            exact mul_pos
              (ih i hiLt hiBounds.1)
              (ih (m - i) hmiLt (by omega))
          · refine ⟨1, ?_⟩
            exact Finset.mem_Icc.mpr ⟨by omega, by omega⟩
        · positivity

/-- The leading coefficient of `ad_A^k B` cannot vanish once the exact
Witt recurrence starts at depth two. -/
theorem witt_chain_leading_nonzero
    (r : ℕ → ℚ)
    (hTwo : r 2 ≠ 0)
    (hRec :
      ∀ k : ℕ, 2 ≤ k →
        r (k + 1) =
          (1 / 6) * (2 * (k : ℚ) - 3) * r k) :
    ∀ k : ℕ, 2 ≤ k → r k ≠ 0 := by
  intro k hk
  induction k, hk using Nat.le_induction with
  | base => exact hTwo
  | succ k hk ih =>
      rw [hRec k hk]
      exact mul_ne_zero
        (mul_ne_zero (by norm_num) (by
          have hkQ : (2 : ℚ) ≤ (k : ℚ) := by
            exact_mod_cast hk
          have : (0 : ℚ) < 2 * (k : ℚ) - 3 := by
            linarith
          exact ne_of_gt this))
        ih

/-- In the Witt coordinate, the `C` top chain is exactly `-1/2` of the
matching `B` chain. -/
theorem first_second_witt_chain_ratio :
    -(5 / 96 : ℚ) / (3 * (5 / 24) * (1 / 6)) = -1 / 2 := by
  norm_num

/-- The even logarithm order `n = 2m + 2` and bracket depth `k = 2m`
produce divisor degree `2n - 4 = 4m`. -/
theorem even_order_degree_arithmetic (m : ℕ) :
    2 * (2 * m + 2) - 4 = 4 * m := by
  omega

/-- The top coefficient is a product of a positive even
generating-function coefficient and a nonzero Witt-chain coefficient. -/
theorem even_magnus_top_nonzero
    (a r : ℕ → ℚ)
    (hOne : a 1 = 1 / 12)
    (hARec :
      ∀ m : ℕ, 2 ≤ m →
        a m =
          (∑ i ∈ Finset.Icc 1 (m - 1), a i * a (m - i)) /
            (2 * (m : ℚ) + 1))
    (hTwo : r 2 ≠ 0)
    (hRRec :
      ∀ k : ℕ, 2 ≤ k →
        r (k + 1) =
          (1 / 6) * (2 * (k : ℚ) - 3) * r k)
    (m : ℕ)
    (hm : 1 ≤ m) :
    (a m / 2) * r (2 * m) ≠ 0 := by
  have haPos : 0 < a m :=
    positive_even_coefficient_recurrence a hOne hARec m hm
  have hk : 2 ≤ 2 * m := by omega
  have hr : r (2 * m) ≠ 0 :=
    witt_chain_leading_nonzero r hTwo hRRec (2 * m) hk
  exact mul_ne_zero (div_ne_zero (ne_of_gt haPos) (by norm_num)) hr

/-- Aggregated arithmetic certificate used by provider-free governance. -/
theorem divisor_magnus_escape_terminal_certificate
    (a r : ℕ → ℚ)
    (hOne : a 1 = 1 / 12)
    (hARec :
      ∀ m : ℕ, 2 ≤ m →
        a m =
          (∑ i ∈ Finset.Icc 1 (m - 1), a i * a (m - i)) /
            (2 * (m : ℚ) + 1))
    (hTwo : r 2 ≠ 0)
    (hRRec :
      ∀ k : ℕ, 2 ≤ k →
        r (k + 1) =
          (1 / 6) * (2 * (k : ℚ) - 3) * r k) :
    (∀ m : ℕ, 1 ≤ m → 0 < a m) ∧
      (∀ k : ℕ, 2 ≤ k → r k ≠ 0) ∧
      (∀ m : ℕ, 1 ≤ m →
        (a m / 2) * r (2 * m) ≠ 0) ∧
      (∀ m : ℕ, 2 * (2 * m + 2) - 4 = 4 * m) := by
  exact ⟨positive_even_coefficient_recurrence a hOne hARec,
    witt_chain_leading_nonzero r hTwo hRRec,
    even_magnus_top_nonzero a r hOne hARec hTwo hRRec,
    even_order_degree_arithmetic⟩

/-!
The source-only escape above is removable by the complete lowest-weight
target action.  The next identities encode the weighted exceptional
coordinates

  `P_s = γ p_s(y) + O(γ²)`,
  `Q_s = γ² q_s(y) + O(γ³)`.

The Hamiltonians `P³` and `P*Q` contribute divisor fields `-6p³` and
`-6pq`.  The displayed rational coefficients reduce the controlled
connection to a translation.
-/

/-- Exact weighted-leading cancellation identity for the regular
`P³`/`P*Q` target control.  The second equality says that the uncontrolled
divisor velocity plus the two target fields is the constant `c`. -/
theorem divisor_translation_control_identity
    (s y : ℚ)
    (hs6 : s ≠ 6)
    (hs4 : s ≠ 4)
    (hsm4 : s ≠ -4) :
    let pN := -3 * s^2 * y + 5 * s^2 + 48 * y
    let p := pN / 48
    let ps := (-6 * s * y + 10 * s) / 48
    let py := (48 - 3 * s^2) / 48
    let qN :=
      (-3 * s * y + 5 * s + 12 * y - 12) *
        (3 * s^2 * y - 5 * s^2 + 8 * s - 48 * y - 48)
    let qD := 16 * (s - 6)^2 * (s - 4)
    let q := qN / qD
    let qNs :=
      -27 * s^2 * y^2 + 90 * s^2 * y - 75 * s^2 +
        72 * s * y^2 - 240 * s * y + 200 * s +
        144 * y^2 - 336
    let qNy := -6 * (s - 4) * (3 * s^2 * y - 5 * s^2 - 48 * y)
    let qDs := 16 * (s - 6) * (3 * s - 14)
    let qs := (qNs * qD - qN * qDs) / qD^2
    let qy := qNy / qD
    let jac := 2 * q * py - p * qy
    let sourceNumerator := 2 * q * ps - p * qs
    let a :=
      96 * (s^2 - 12 * s + 16) /
        ((s - 6)^3 * (s - 4)^2 * (s + 4)^2)
    let b := 2 * s / ((s - 4) * (s + 4))
    let c := 160 * s / (3 * (s - 4)^2 * (s + 4)^2)
    jac = -1 / 2 ∧
      sourceNumerator = jac * (c - 6 * a * p^3 - 6 * b * p * q) := by
  dsimp
  have hs6z : s - 6 ≠ 0 := sub_ne_zero.mpr hs6
  have hs4z : s - 4 ≠ 0 := sub_ne_zero.mpr hs4
  have hsp4 : s + 4 ≠ 0 := by
    intro h
    apply hsm4
    linarith
  constructor <;>
    field_simp [hs6z, hs4z, hsp4] <;>
    ring

/-- One-variable affine polynomial fields are closed under bracket; their
bracket is a translation field. -/
theorem affine_field_bracket_is_constant
    (a b c d y : ℚ) :
    (a + b * y) * d - (c + d * y) * b = a * d - c * b := by
  ring

/-- Translation fields commute. -/
theorem translation_fields_commute (a c : ℚ) :
    a * (0 : ℚ) - c * 0 = 0 := by
  ring

/-- Provider-free endpoint for the gauge disposition of the divisor
Magnus theorem.  It records both the exact translation normal form and the
finite Lie-algebra consequence. -/
theorem divisor_magnus_gauge_kill_terminal_certificate
    (s y : ℚ)
    (hs6 : s ≠ 6)
    (hs4 : s ≠ 4)
    (hsm4 : s ≠ -4) :
    (let pN := -3 * s^2 * y + 5 * s^2 + 48 * y
     let p := pN / 48
     let ps := (-6 * s * y + 10 * s) / 48
     let py := (48 - 3 * s^2) / 48
     let qN :=
       (-3 * s * y + 5 * s + 12 * y - 12) *
         (3 * s^2 * y - 5 * s^2 + 8 * s - 48 * y - 48)
     let qD := 16 * (s - 6)^2 * (s - 4)
     let q := qN / qD
     let qNs :=
       -27 * s^2 * y^2 + 90 * s^2 * y - 75 * s^2 +
         72 * s * y^2 - 240 * s * y + 200 * s +
         144 * y^2 - 336
     let qNy := -6 * (s - 4) * (3 * s^2 * y - 5 * s^2 - 48 * y)
     let qDs := 16 * (s - 6) * (3 * s - 14)
     let qs := (qNs * qD - qN * qDs) / qD^2
     let qy := qNy / qD
     let jac := 2 * q * py - p * qy
     let sourceNumerator := 2 * q * ps - p * qs
     let a :=
       96 * (s^2 - 12 * s + 16) /
         ((s - 6)^3 * (s - 4)^2 * (s + 4)^2)
     let b := 2 * s / ((s - 4) * (s + 4))
     let c := 160 * s / (3 * (s - 4)^2 * (s + 4)^2)
     jac = -1 / 2 ∧
       sourceNumerator = jac * (c - 6 * a * p^3 - 6 * b * p * q)) ∧
      (∀ a b c d y : ℚ,
        (a + b * y) * d - (c + d * y) * b = a * d - c * b) := by
  exact ⟨divisor_translation_control_identity s y hs6 hs4 hsm4,
    affine_field_bracket_is_constant⟩

/-!
The divisor and first-transverse calculations are instances of one
weighted-layer identity.  If

  `P = γ A(y) + O(γ²)` and `Q = γ² D(y) + O(γ³)`,

then `A * D' - 2 * A' * D = 1/2`.  For a weighted-homogeneous target
Hamiltonian of degree `d`, Euler's identity and the two pulled-back
component equations force the tangential layer coefficient to be
`-2 * d * H(A,D)`.
-/

/-- Algebraic elimination behind the complete target image at every
exceptional layer. -/
theorem weighted_hamiltonian_layer_elimination
    (d A Ay D Dy f fy HP HQ H : ℚ)
    (hJac : A * Dy - 2 * Ay * D = 1 / 2)
    (hP : Ay * f - A * fy / d = HQ)
    (hQ : Dy * f - 2 * D * fy / d = -HP)
    (hEuler : A * HP + 2 * D * HQ = d * H) :
    f = -2 * d * H := by
  have hElim :
      (A * Dy - 2 * Ay * D) * f =
        -(A * HP + 2 * D * HQ) := by
    linear_combination A * hQ - 2 * D * hP
  calc
    f = 2 * (A * Dy - 2 * Ay * D) * f := by
      rw [hJac]
      ring
    _ = 2 * ((A * Dy - 2 * Ay * D) * f) := by ring
    _ = 2 * (-(A * HP + 2 * D * HQ)) := by
      rw [hElim]
    _ = -2 * (A * HP + 2 * D * HQ) := by ring
    _ = -2 * d * H := by
      rw [hEuler]
      ring

/-- Bracket law for the tangential coefficients of two homogeneous
weighted-volume fields. -/
theorem weighted_layer_bracket_coefficient
    (m n f h fp hp : ℚ)
    (hm : m + 3 ≠ 0)
    (hn : n + 3 ≠ 0) :
    f * hp - h * fp - n * fp * h / (m + 3) +
        m * hp * f / (n + 3) =
      (m + n + 3) *
        (f * hp / (n + 3) - h * fp / (m + 3)) := by
  field_simp [hm, hn]
  ring

/-- The first-layer affine residue brackets a constant into the next
exceptional layer with nonzero coefficient. -/
theorem first_layer_secondary_constant :
    ((1 + 1 + 3 : ℚ) *
      ((1 * 0) / (1 + 3) - (1 * 1) / (1 + 3))) =
      -5 / 4 := by
  norm_num

/-- The seed weight-four target image has unit determinant in the
`(1,y²,y⁴)` coefficient coordinates. -/
theorem weight_four_seed_image_unit_minor :
    0 * (2 * (-1 / 2) - 1 * (-2)) -
        0 * (0 * (-1 / 2) - 1 * (-8)) +
        (-(1 / 2 : ℚ)) * (0 * (-2) - 2 * (-8)) =
      -8 := by
  norm_num

/-- Provider-free endpoint for the all-layer weighted target mechanism and
the first secondary bracket. -/
theorem weighted_target_layer_terminal_certificate
    (d A Ay D Dy f fy HP HQ H : ℚ)
    (hJac : A * Dy - 2 * Ay * D = 1 / 2)
    (hP : Ay * f - A * fy / d = HQ)
    (hQ : Dy * f - 2 * D * fy / d = -HP)
    (hEuler : A * HP + 2 * D * HQ = d * H) :
    f = -2 * d * H ∧
      ((1 + 1 + 3 : ℚ) *
        ((1 * 0) / (1 + 3) - (1 * 1) / (1 + 3))) =
        -5 / 4 ∧
      0 * (2 * (-1 / 2) - 1 * (-2)) -
          0 * (0 * (-1 / 2) - 1 * (-8)) +
          (-(1 / 2 : ℚ)) * (0 * (-2) - 2 * (-8)) =
        -8 := by
  exact ⟨weighted_hamiltonian_layer_elimination
      d A Ay D Dy f fy HP HQ H hJac hP hQ hEuler,
    first_layer_secondary_constant,
    weight_four_seed_image_unit_minor⟩

/-!
The all-layer calculation reduces the defect-three top shell to a rational
generating function.  The definitions below certify its arithmetic surface.
Binding this surface to the canonical parity normal form uses the separate
adapted-coordinate triangular calculation in `(ξ, N)`; these lemmas do not
assert a symmetric source/target minimax theorem.
-/

/-- Closed form for the canonical top-shell tail.  The all-layer
calculation identifies the actual coefficient with this expression from
layer two onward. -/
def canonicalTopShellTail (m : ℕ) : ℚ :=
  -((3 / 2 : ℚ)^m * ((m : ℚ) + 3) * (4 * (m : ℚ) + 1)) / 216

/-- The repeated-root recurrence associated with the triple pole at
`u = 2/3`. -/
theorem canonical_top_shell_tail_recurrence (m : ℕ) :
    8 * canonicalTopShellTail (m + 3) -
        36 * canonicalTopShellTail (m + 2) +
        54 * canonicalTopShellTail (m + 1) -
        27 * canonicalTopShellTail m = 0 := by
  simp only [canonicalTopShellTail, Nat.cast_add, Nat.cast_ofNat, pow_add]
  ring

/-- Every coefficient in the closed-form tail is nonzero. -/
theorem canonical_top_shell_tail_ne_zero (m : ℕ) :
    canonicalTopShellTail m ≠ 0 := by
  unfold canonicalTopShellTail
  apply div_ne_zero
  · apply neg_ne_zero.mpr
    apply mul_ne_zero
    · apply mul_ne_zero
      · exact pow_ne_zero m (by norm_num)
      · exact ne_of_gt (by positivity :
          (0 : ℚ) < (m : ℚ) + 3)
    · exact ne_of_gt (by positivity :
        (0 : ℚ) < 4 * (m : ℚ) + 1)
  · norm_num

def topShellHamiltonian (u : ℚ) : ℚ :=
  (9 * u^3 - 36 * u^2 + 39 * u - 10) /
    (72 * (3 * u - 2)^2)

def topShellHamiltonianDerivative (u : ℚ) : ℚ :=
  ((27 * u^2 - 72 * u + 39) * (3 * u - 2) -
      6 * (9 * u^3 - 36 * u^2 + 39 * u - 10)) /
    (72 * (3 * u - 2)^3)

def topShellGeneratingFunction (u : ℚ) : ℚ :=
  (18 * u^4 - 72 * u^3 + 99 * u^2 - 57 * u + 10) /
    (6 * (2 - 3 * u)^3)

/-- Exact Hamiltonian-to-vector-field conversion for the rational
top-shell generating function. -/
theorem top_shell_generating_function_identity
    (u : ℚ) (hu : 3 * u - 2 ≠ 0) :
    -2 * (3 * topShellHamiltonian u +
      u * topShellHamiltonianDerivative u) =
        topShellGeneratingFunction u := by
  simp only [topShellHamiltonian, topShellHamiltonianDerivative,
    topShellGeneratingFunction]
  have hu' : 2 - 3 * u ≠ 0 := by
    intro h
    apply hu
    linarith
  field_simp [hu, hu']
  ring

/-- A bracket of two coefficients whose degrees are bounded by their layer
indices cannot reach the top degree of the combined positive layer. -/
theorem lower_layer_bracket_misses_top_degree
    (m n df dh : ℕ)
    (hdf : df ≤ m)
    (hdh : dh ≤ n)
    (hpositive : 0 < m + n) :
    df + dh - 1 < m + n := by
  omega

/-- Provider-free arithmetic endpoint for the canonical top-shell
recurrence. -/
theorem canonical_top_shell_arithmetic_terminal_certificate :
    (∀ m : ℕ, canonicalTopShellTail m ≠ 0) ∧
    (∀ m : ℕ,
      8 * canonicalTopShellTail (m + 3) -
          36 * canonicalTopShellTail (m + 2) +
          54 * canonicalTopShellTail (m + 1) -
          27 * canonicalTopShellTail m = 0) := by
  exact ⟨canonical_top_shell_tail_ne_zero,
    canonical_top_shell_tail_recurrence⟩

end AxiomPackJacobianDivisorMagnusEscape
