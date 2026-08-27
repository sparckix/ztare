import Mathlib.Algebra.Polynomial.Degree.IsMonicOfDegree
import Mathlib.RingTheory.PowerSeries.Inverse
import Mathlib.RingTheory.PowerSeries.Order
import Mathlib.RingTheory.PowerSeries.Substitution
import Mathlib.Tactic

/-!
Formal reciprocal-coordinate bookkeeping for one-variable polynomial flows.

For a monic degree-`d` polynomial generator `p`, `reciprocalDenominator d p`
is the formal series `z^d p(1/z)`.  Its constant coefficient is one.  The
formal time coordinate at infinity is the zero-constant primitive of

`z^(d-2) / reciprocalDenominator d p`.

The main theorem proves the coefficient-collision calculation used in
two-flow Puiseux arguments.  If two monic generators, both with zero constant
and linear coefficients, first differ at their largest polynomial degree
`e`, then their normalized time coordinates first differ in reciprocal degree
`2*d-e-1`.  The proof is all-order: inverse-series order is transported by an
exact algebraic identity, rather than inferred from a finite coefficient
table.

This file does not assert that every singular analytic continuation of a
polynomial ODE passes through the selected infinity chart.
-/

namespace FormalPolynomialFlowAtInfinity

open Polynomial PowerSeries

section CoefficientField

variable {𝕜 : Type*} [Field 𝕜]

/-- Formal primitive with zero constant coefficient. -/
noncomputable def zeroConstantPrimitive (f : 𝕜⟦X⟧) : 𝕜⟦X⟧ :=
  PowerSeries.mk fun
    | 0 => 0
    | n + 1 => PowerSeries.coeff n f / (n + 1 : 𝕜)

@[simp]
theorem coeff_zero_zeroConstantPrimitive (f : 𝕜⟦X⟧) :
    PowerSeries.coeff 0 (zeroConstantPrimitive f) = 0 := by
  simp [zeroConstantPrimitive]

@[simp]
theorem coeff_succ_zeroConstantPrimitive (f : 𝕜⟦X⟧) (n : ℕ) :
    PowerSeries.coeff (n + 1) (zeroConstantPrimitive f) =
      PowerSeries.coeff n f / (n + 1 : 𝕜) := by
  simp [zeroConstantPrimitive]

@[simp]
theorem constantCoeff_zeroConstantPrimitive (f : 𝕜⟦X⟧) :
    PowerSeries.constantCoeff (zeroConstantPrimitive f) = 0 := by
  rw [← PowerSeries.coeff_zero_eq_constantCoeff]
  exact coeff_zero_zeroConstantPrimitive f

theorem zeroConstantPrimitive_sub (f g : 𝕜⟦X⟧) :
    zeroConstantPrimitive (f - g) =
      zeroConstantPrimitive f - zeroConstantPrimitive g := by
  apply PowerSeries.ext
  intro n
  cases n with
  | zero =>
      simp [constantCoeff_zeroConstantPrimitive]
  | succ n => simp [sub_div]

/-- A zero-constant primitive raises every finite nonzero order by exactly
one over a characteristic-zero field. -/
theorem order_zeroConstantPrimitive {f : 𝕜⟦X⟧} {n : ℕ}
    [CharZero 𝕜]
    (horder : PowerSeries.order f = n) :
    PowerSeries.order (zeroConstantPrimitive f) = ((n + 1 : ℕ) : ℕ∞) := by
  apply (PowerSeries.order_eq_nat).2
  constructor
  · simp only [coeff_succ_zeroConstantPrimitive]
    have hcast : (((n + 1 : ℕ) : 𝕜)) ≠ 0 :=
      Nat.cast_ne_zero.mpr (Nat.succ_ne_zero n)
    exact div_ne_zero (PowerSeries.order_eq_nat.mp horder).1
      (by simpa [Nat.cast_add, Nat.cast_one] using hcast)
  · intro i hi
    cases i with
    | zero => simp
    | succ j =>
        rw [coeff_succ_zeroConstantPrimitive]
        have hj : j < n := by omega
        rw [(PowerSeries.order_eq_nat.mp horder).2 j hj]
        simp

/-- Reciprocal polynomial denominator `z^d p(1/z)`.  Values beyond degree
`d` are zero, so the definition is a power series without choosing a second
polynomial representation. -/
noncomputable def reciprocalDenominator (d : ℕ) (p : 𝕜[X]) : 𝕜⟦X⟧ :=
  PowerSeries.mk fun n =>
    if n ≤ d then p.coeff (d - n) else 0

theorem coeff_reciprocalDenominator (d n : ℕ) (p : 𝕜[X]) :
    PowerSeries.coeff n (reciprocalDenominator d p) =
      if n ≤ d then p.coeff (d - n) else 0 := by
  simp [reciprocalDenominator]

theorem constantCoeff_reciprocalDenominator_of_monic
    {d : ℕ} {p : 𝕜[X]} (hp : Polynomial.IsMonicOfDegree p d) :
    PowerSeries.constantCoeff (reciprocalDenominator d p) = 1 := by
  rw [← PowerSeries.coeff_zero_eq_constantCoeff,
    coeff_reciprocalDenominator]
  simp only [zero_le, ↓reduceIte, Nat.sub_zero]
  rw [← hp.natDegree_eq, Polynomial.coeff_natDegree,
    hp.leadingCoeff_eq]

/-- The normalized polynomial collision is exhaustive.  Equal monic
generators are the proportional case before normalization.  Otherwise their
largest differing coefficient has degree `e` with `2 ≤ e < d`, and every
higher coefficient agrees. -/
theorem monic_tangent_collision_alternative
    {p q : 𝕜[X]} {d : ℕ} (hd : 2 ≤ d)
    (hp : Polynomial.IsMonicOfDegree p d)
    (hq : Polynomial.IsMonicOfDegree q d)
    (hp0 : p.coeff 0 = 0) (hq0 : q.coeff 0 = 0)
    (hp1 : p.coeff 1 = 0) (hq1 : q.coeff 1 = 0) :
    p = q ∨
      ∃ e : ℕ,
        2 ≤ e ∧ e < d ∧ p.coeff e ≠ q.coeff e ∧
          ∀ n : ℕ, e < n → p.coeff n = q.coeff n := by
  by_cases hpq : p = q
  · exact Or.inl hpq
  · right
    let r : 𝕜[X] := p - q
    have hr : r ≠ 0 := sub_ne_zero.mpr hpq
    let e := r.natDegree
    have he_lt : e < d := by
      exact hp.natDegree_sub_lt (by omega) hq
    have he_coeff : p.coeff e ≠ q.coeff e := by
      intro heq
      have hz : r.coeff e = 0 := by simpa [r] using sub_eq_zero.mpr heq
      have hnz : r.coeff e ≠ 0 := by
        rw [show e = r.natDegree by rfl, Polynomial.coeff_natDegree]
        exact Polynomial.leadingCoeff_ne_zero.mpr hr
      exact hnz hz
    have he_two : 2 ≤ e := by
      by_contra hnot
      have he : e = 0 ∨ e = 1 := by omega
      rcases he with he | he
      · rw [he] at he_coeff
        exact he_coeff (hp0.trans hq0.symm)
      · rw [he] at he_coeff
        exact he_coeff (hp1.trans hq1.symm)
    refine ⟨e, he_two, he_lt, he_coeff, ?_⟩
    intro n hen
    have hz : r.coeff n = 0 :=
      Polynomial.coeff_eq_zero_of_natDegree_lt hen
    simpa [r, sub_eq_zero] using hz

/-- A largest polynomial collision in degree `e` becomes a first reciprocal
denominator collision in degree `d-e`. -/
theorem reciprocalDenominator_difference_order
    {p q : 𝕜[X]} {d e : ℕ} (he : e ≤ d)
    (hcoeff : p.coeff e ≠ q.coeff e)
    (hhigher : ∀ n : ℕ, e < n → p.coeff n = q.coeff n) :
    PowerSeries.order
        (reciprocalDenominator d p - reciprocalDenominator d q) =
      ((d - e : ℕ) : ℕ∞) := by
  apply (PowerSeries.order_eq_nat).2
  constructor
  · simp only [map_sub, coeff_reciprocalDenominator]
    simp only [if_pos (Nat.sub_le d e), Nat.sub_sub_self he]
    exact sub_ne_zero.mpr hcoeff
  · intro n hn
    have hnd : n ≤ d := by omega
    simp only [map_sub, coeff_reciprocalDenominator, if_pos hnd]
    have hdegree : e < d - n := by omega
    rw [hhigher (d - n) hdegree]
    simp

private theorem order_inv_of_constantCoeff_one (f : 𝕜⟦X⟧)
    (hconstant : PowerSeries.constantCoeff f = 1) :
    PowerSeries.order f⁻¹ = ((0 : ℕ) : ℕ∞) := by
  apply (PowerSeries.order_eq_nat).2
  constructor
  · rw [PowerSeries.coeff_zero_eq_constantCoeff,
      PowerSeries.constantCoeff_inv, hconstant]
    norm_num
  · intro i hi
    omega

private theorem order_eq_zero_of_constantCoeff_ne_zero (f : 𝕜⟦X⟧)
    (hconstant : PowerSeries.constantCoeff f ≠ 0) :
    PowerSeries.order f = ((0 : ℕ) : ℕ∞) := by
  apply (PowerSeries.order_eq_nat).2
  constructor
  · simpa [PowerSeries.coeff_zero_eq_constantCoeff]
  · intro i hi
    omega

theorem constantCoeff_subst_of_inner_constantCoeff_zero
    (inner outer : 𝕜⟦X⟧)
    (hinner : PowerSeries.constantCoeff inner = 0) :
    PowerSeries.constantCoeff (outer.subst inner) =
      PowerSeries.constantCoeff outer := by
  let c := PowerSeries.constantCoeff outer
  have houterZero :
      PowerSeries.constantCoeff (outer - PowerSeries.C c) = 0 := by
    simp [c]
  have hsubstZero := PowerSeries.constantCoeff_subst_eq_zero
    hinner (outer - PowerSeries.C c) houterZero
  have hhas : PowerSeries.HasSubst inner :=
    PowerSeries.HasSubst.of_constantCoeff_zero' hinner
  rw [PowerSeries.subst_sub hhas] at hsubstZero
  have heq := sub_eq_zero.mp hsubstZero
  simpa [c] using heq

private noncomputable def shiftSeries (f : 𝕜⟦X⟧) : 𝕜⟦X⟧ :=
  PowerSeries.mk fun n => PowerSeries.coeff (n + 1) f

private theorem constantCoeff_shiftSeries (f : 𝕜⟦X⟧) :
    PowerSeries.constantCoeff (shiftSeries f) = PowerSeries.coeff 1 f := by
  simp [shiftSeries]

/-- A formal transition germ with zero constant and nonzero linear
coefficient preserves the order of every nonconstant inner germ. -/
theorem order_subst_of_nonzero_linear
    (inner transition : 𝕜⟦X⟧)
    (hinner : PowerSeries.constantCoeff inner = 0)
    (htransition : PowerSeries.constantCoeff transition = 0)
    (hlinear : PowerSeries.coeff 1 transition ≠ 0) :
    PowerSeries.order (transition.subst inner) =
      PowerSeries.order inner := by
  have hhas : PowerSeries.HasSubst inner :=
    PowerSeries.HasSubst.of_constantCoeff_zero' hinner
  have hsplit := PowerSeries.eq_shift_mul_X_add_const transition
  have htransitionEq : transition = shiftSeries transition * PowerSeries.X := by
    simpa [shiftSeries, htransition] using hsplit
  have hshiftConstant :
      PowerSeries.constantCoeff ((shiftSeries transition).subst inner) =
        PowerSeries.coeff 1 transition := by
    rw [constantCoeff_subst_of_inner_constantCoeff_zero _ _ hinner,
      constantCoeff_shiftSeries]
  rw [htransitionEq, PowerSeries.subst_mul hhas,
    PowerSeries.subst_X hhas, PowerSeries.order_mul,
    order_eq_zero_of_constantCoeff_ne_zero _ (hshiftConstant.trans_ne hlinear)]
  simp

private theorem inv_sub_inv_identity (f g : 𝕜⟦X⟧)
    (hf : PowerSeries.constantCoeff f = 1)
    (hg : PowerSeries.constantCoeff g = 1) :
    f⁻¹ - g⁻¹ = f⁻¹ * (g - f) * g⁻¹ := by
  have hfnz : PowerSeries.constantCoeff f ≠ 0 := by simp [hf]
  have hgnz : PowerSeries.constantCoeff g ≠ 0 := by simp [hg]
  calc
    f⁻¹ - g⁻¹ = f⁻¹ * 1 - 1 * g⁻¹ := by ring
    _ = f⁻¹ * (g * g⁻¹) - (f⁻¹ * f) * g⁻¹ := by
      rw [PowerSeries.mul_inv_cancel g hgnz,
        PowerSeries.inv_mul_cancel f hfnz]
    _ = f⁻¹ * (g - f) * g⁻¹ := by ring

/-- Inversion by unit power series preserves the first order at which two
normalized reciprocal denominators differ. -/
theorem inverse_difference_order
    {f g : 𝕜⟦X⟧} {k : ℕ}
    (hf : PowerSeries.constantCoeff f = 1)
    (hg : PowerSeries.constantCoeff g = 1)
    (hdifference : PowerSeries.order (g - f) = k) :
    PowerSeries.order (f⁻¹ - g⁻¹) = k := by
  rw [inv_sub_inv_identity f g hf hg,
    PowerSeries.order_mul, PowerSeries.order_mul,
    order_inv_of_constantCoeff_one f hf,
    order_inv_of_constantCoeff_one g hg,
    hdifference]
  simp

/-- Normalized formal time coordinate at infinity.  The omitted nonzero
leading scalar does not affect its order. -/
noncomputable def normalizedTimeCoordinate (d : ℕ) (denominator : 𝕜⟦X⟧) :
    𝕜⟦X⟧ :=
  zeroConstantPrimitive
    ((PowerSeries.X : 𝕜⟦X⟧) ^ (d - 2) * denominator⁻¹)

theorem constantCoeff_normalizedTimeCoordinate (d : ℕ)
    (denominator : 𝕜⟦X⟧) :
    PowerSeries.constantCoeff (normalizedTimeCoordinate d denominator) = 0 := by
  rw [← PowerSeries.coeff_zero_eq_constantCoeff]
  simp [normalizedTimeCoordinate]

theorem normalizedTimeCoordinate_order
    [CharZero 𝕜] {d : ℕ} (hd : 2 ≤ d) {denominator : 𝕜⟦X⟧}
    (hconstant : PowerSeries.constantCoeff denominator = 1) :
    PowerSeries.order (normalizedTimeCoordinate d denominator) =
      ((d - 1 : ℕ) : ℕ∞) := by
  have hinverse : PowerSeries.order denominator⁻¹ = ((0 : ℕ) : ℕ∞) :=
    order_inv_of_constantCoeff_one denominator hconstant
  have hderivative :
      PowerSeries.order
          ((PowerSeries.X : 𝕜⟦X⟧) ^ (d - 2) * denominator⁻¹) =
        ((d - 2 : ℕ) : ℕ∞) := by
    rw [PowerSeries.order_mul, PowerSeries.order_X_pow, hinverse]
    simp
  rw [normalizedTimeCoordinate, order_zeroConstantPrimitive hderivative]
  norm_cast
  omega

/-- A nonzero-linear transition between two normalized infinity time
coordinates forces their polynomial degrees to agree. -/
theorem nonzero_linear_transition_forces_equal_degree
    [CharZero 𝕜] {p q : 𝕜[X]} {d e : ℕ}
    (hd : 2 ≤ d) (he : 2 ≤ e)
    (hp : Polynomial.IsMonicOfDegree p d)
    (hq : Polynomial.IsMonicOfDegree q e)
    (transition : 𝕜⟦X⟧)
    (htransitionConstant : PowerSeries.constantCoeff transition = 0)
    (htransitionLinear : PowerSeries.coeff 1 transition ≠ 0)
    (htransition :
      normalizedTimeCoordinate e (reciprocalDenominator e q) =
        transition.subst
          (normalizedTimeCoordinate d (reciprocalDenominator d p))) :
    d = e := by
  have hpconstant := constantCoeff_reciprocalDenominator_of_monic hp
  have hqconstant := constantCoeff_reciprocalDenominator_of_monic hq
  have hporder := normalizedTimeCoordinate_order hd hpconstant
  have hqorder := normalizedTimeCoordinate_order he hqconstant
  have hinner := constantCoeff_normalizedTimeCoordinate d
    (reciprocalDenominator d p)
  have hsubstOrder := order_subst_of_nonzero_linear
    (normalizedTimeCoordinate d (reciprocalDenominator d p)) transition
    hinner htransitionConstant htransitionLinear
  rw [← htransition, hporder, hqorder] at hsubstOrder
  norm_cast at hsubstOrder
  omega

theorem normalizedTimeCoordinate_sub
    (d : ℕ) (f g : 𝕜⟦X⟧) :
    normalizedTimeCoordinate d f - normalizedTimeCoordinate d g =
      zeroConstantPrimitive
        ((PowerSeries.X : 𝕜⟦X⟧) ^ (d - 2) * (f⁻¹ - g⁻¹)) := by
  simp only [normalizedTimeCoordinate]
  rw [← zeroConstantPrimitive_sub]
  congr 1
  ring

/-- Exact all-order time-coordinate collision order. -/
theorem normalizedTimeCoordinate_difference_order
    [CharZero 𝕜] {f g : 𝕜⟦X⟧} {d e : ℕ}
    (hd : 2 ≤ d) (he : e < d)
    (hf : PowerSeries.constantCoeff f = 1)
    (hg : PowerSeries.constantCoeff g = 1)
    (hdifference : PowerSeries.order (g - f) = ((d - e : ℕ) : ℕ∞)) :
    PowerSeries.order
        (normalizedTimeCoordinate d f - normalizedTimeCoordinate d g) =
      ((2 * d - e - 1 : ℕ) : ℕ∞) := by
  rw [normalizedTimeCoordinate_sub]
  have hinverse : PowerSeries.order (f⁻¹ - g⁻¹) = d - e :=
    inverse_difference_order hf hg hdifference
  have hderivative :
      PowerSeries.order
          ((PowerSeries.X : 𝕜⟦X⟧) ^ (d - 2) * (f⁻¹ - g⁻¹)) =
        (((d - 2) + (d - e) : ℕ) : ℕ∞) := by
    rw [PowerSeries.order_mul, PowerSeries.order_X_pow, hinverse]
    norm_num
  rw [order_zeroConstantPrimitive hderivative]
  norm_cast
  omega

/-- For two distinct monic tangent generators, the largest polynomial
collision controls the exact first reciprocal time-coordinate collision. -/
theorem monic_tangent_time_coordinate_alternative
    [CharZero 𝕜] {p q : 𝕜[X]} {d : ℕ} (hd : 2 ≤ d)
    (hp : Polynomial.IsMonicOfDegree p d)
    (hq : Polynomial.IsMonicOfDegree q d)
    (hp0 : p.coeff 0 = 0) (hq0 : q.coeff 0 = 0)
    (hp1 : p.coeff 1 = 0) (hq1 : q.coeff 1 = 0) :
    p = q ∨
      ∃ e : ℕ,
        2 ≤ e ∧ e < d ∧
          PowerSeries.order
              (normalizedTimeCoordinate d (reciprocalDenominator d p) -
                normalizedTimeCoordinate d (reciprocalDenominator d q)) =
            ((2 * d - e - 1 : ℕ) : ℕ∞) := by
  rcases monic_tangent_collision_alternative hd hp hq hp0 hq0 hp1 hq1 with
    hpq | ⟨e, he_two, he_lt, he_coeff, he_higher⟩
  · exact Or.inl hpq
  · right
    refine ⟨e, he_two, he_lt, ?_⟩
    apply normalizedTimeCoordinate_difference_order hd he_lt
    · exact constantCoeff_reciprocalDenominator_of_monic hp
    · exact constantCoeff_reciprocalDenominator_of_monic hq
    · have hreciprocal := reciprocalDenominator_difference_order
        (p := q) (q := p) (d := d) (e := e) (Nat.le_of_lt he_lt)
        (Ne.symm he_coeff) (fun n hn => (he_higher n hn).symm)
      exact hreciprocal

end CoefficientField

/-- The common reciprocal leading order `d-1` converts collision order
`2*d-e-1` into the standard transition exponent. -/
theorem time_coordinate_collision_exponent
    {d e : ℕ} (hd : 2 ≤ d) (_he_two : 2 ≤ e) (he_lt : e < d) :
    ((2 * d - e - 1 : ℕ) : ℚ) / ((d - 1 : ℕ) : ℚ) =
      1 + (((d : ℚ) - e) / ((d : ℚ) - 1)) := by
  have hsum : 2 * d - e - 1 = (d - 1) + (d - e) := by omega
  have hdsub : ((d - 1 : ℕ) : ℚ) = (d : ℚ) - 1 := by
    rw [Nat.cast_sub (by omega : 1 ≤ d)]
    norm_num
  have hesum : ((d - e : ℕ) : ℚ) = (d : ℚ) - e := by
    rw [Nat.cast_sub (Nat.le_of_lt he_lt)]
  rw [hsum, Nat.cast_add, hdsub, hesum]
  have hden : (d : ℚ) - 1 ≠ 0 := by
    have : (1 : ℚ) < d := by exact_mod_cast (show 1 < d by omega)
    linarith
  field_simp

/-- The nonproportional normalized collision exponent lies strictly between
one and two. -/
theorem time_coordinate_collision_exponent_interval
    {d e : ℕ} (hd : 2 ≤ d) (he_two : 2 ≤ e) (he_lt : e < d) :
    1 < ((2 * d - e - 1 : ℕ) : ℚ) / ((d - 1 : ℕ) : ℚ) ∧
      ((2 * d - e - 1 : ℕ) : ℚ) / ((d - 1 : ℕ) : ℚ) < 2 := by
  rw [time_coordinate_collision_exponent hd he_two he_lt]
  have hdq : (1 : ℚ) < d := by exact_mod_cast (show 1 < d by omega)
  have heq : (1 : ℚ) < e := by exact_mod_cast (show 1 < e by omega)
  have hedq : (e : ℚ) < d := by exact_mod_cast he_lt
  constructor
  · have : 0 < ((d : ℚ) - e) / ((d : ℚ) - 1) :=
      div_pos (sub_pos.mpr hedq) (sub_pos.mpr hdq)
    linarith
  · have hnum : (d : ℚ) - e < (d : ℚ) - 1 := by linarith
    have : ((d : ℚ) - e) / ((d : ℚ) - 1) < 1 :=
      (div_lt_one (sub_pos.mpr hdq)).2 hnum
    linarith

/-- Aggregated infinity-chart endpoint.  It pays the equal-degree step and
the complete normalized-coefficient alternative, including the exact
all-order collision and its `(1,2)` exponent interval.  Analytic route
exhaustion and autonomous-flow composition remain separate propositions. -/
theorem polynomial_infinity_chart_terminal_certificate :
    ∀ (𝕜 : Type*) [Field 𝕜] [CharZero 𝕜],
    (∀ (p q : 𝕜[X]) (d e : ℕ), 2 ≤ d → 2 ≤ e →
      Polynomial.IsMonicOfDegree p d →
      Polynomial.IsMonicOfDegree q e →
      ∀ transition : 𝕜⟦X⟧,
        PowerSeries.constantCoeff transition = 0 →
        PowerSeries.coeff 1 transition ≠ 0 →
        normalizedTimeCoordinate e (reciprocalDenominator e q) =
          transition.subst
            (normalizedTimeCoordinate d (reciprocalDenominator d p)) →
        d = e) ∧
    (∀ (p q : 𝕜[X]) (d : ℕ), 2 ≤ d →
      Polynomial.IsMonicOfDegree p d →
      Polynomial.IsMonicOfDegree q d →
      p.coeff 0 = 0 → q.coeff 0 = 0 →
      p.coeff 1 = 0 → q.coeff 1 = 0 →
      p = q ∨
        ∃ collisionDegree : ℕ,
          2 ≤ collisionDegree ∧ collisionDegree < d ∧
          PowerSeries.order
              (normalizedTimeCoordinate d (reciprocalDenominator d p) -
                normalizedTimeCoordinate d (reciprocalDenominator d q)) =
            ((2 * d - collisionDegree - 1 : ℕ) : ℕ∞) ∧
          (1 <
              ((2 * d - collisionDegree - 1 : ℕ) : ℚ) /
                ((d - 1 : ℕ) : ℚ) ∧
            ((2 * d - collisionDegree - 1 : ℕ) : ℚ) /
                ((d - 1 : ℕ) : ℚ) < 2)) := by
  intro 𝕜 _ _
  constructor
  · intro p q d e hd he hp hq transition hconstant hlinear htransition
    exact nonzero_linear_transition_forces_equal_degree
      hd he hp hq transition hconstant hlinear htransition
  · intro p q d hd hp hq hp0 hq0 hp1 hq1
    rcases monic_tangent_time_coordinate_alternative
        hd hp hq hp0 hq0 hp1 hq1 with hpq | ⟨e, he2, hed, horder⟩
    · exact Or.inl hpq
    · exact Or.inr ⟨e, he2, hed, horder,
        time_coordinate_collision_exponent_interval hd he2 hed⟩

end FormalPolynomialFlowAtInfinity
