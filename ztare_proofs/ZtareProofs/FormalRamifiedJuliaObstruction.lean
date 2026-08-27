import Mathlib.Algebra.Polynomial.Div
import Mathlib.RingTheory.PowerSeries.Order
import Mathlib.RingTheory.PowerSeries.Substitution
import Mathlib.Tactic

/-!
All-order ramified Julia obstruction for one polynomial generator.

The proof translates a nonzero polynomial at the input and output centers,
divides its exact root multiplicities, and compares the first odd coefficient
of the resulting formal Julia identity.  Polynomial root units are
constructed with `divByMonic`; no multiplicity or coefficient balance is
accepted as a premise.
-/

namespace FormalRamifiedJuliaObstruction

open PowerSeries

variable {𝕜 : Type*} [Field 𝕜] [CharZero 𝕜]

noncomputable def shiftedPolynomial
    (p : Polynomial 𝕜) (center : 𝕜) : Polynomial 𝕜 :=
  p.comp (Polynomial.X + Polynomial.C center)

noncomputable def shiftedRootUnit
    (p : Polynomial 𝕜) (center : 𝕜) : Polynomial 𝕜 :=
  (p /ₘ (Polynomial.X - Polynomial.C center) ^
      p.rootMultiplicity center).comp
    (Polynomial.X + Polynomial.C center)

theorem shiftedPolynomial_eq_rootPower_mul_unit
    (p : Polynomial 𝕜) (center : 𝕜) :
    shiftedPolynomial p center =
      Polynomial.X ^ p.rootMultiplicity center *
        shiftedRootUnit p center := by
  have h := p.pow_mul_divByMonic_rootMultiplicity_eq center
  have hc := congrArg (fun q : Polynomial 𝕜 =>
    q.comp (Polynomial.X + Polynomial.C center)) h
  simpa [shiftedPolynomial, shiftedRootUnit, Polynomial.mul_comp,
    Polynomial.pow_comp, Polynomial.sub_comp] using hc.symm

theorem shiftedRootUnit_constantCoeff_ne_zero
    {p : Polynomial 𝕜} (hp : p ≠ 0) (center : 𝕜) :
    (shiftedRootUnit p center).coeff 0 ≠ 0 := by
  rw [Polynomial.coeff_zero_eq_eval_zero, shiftedRootUnit,
    Polynomial.eval_comp, Polynomial.eval_add, Polynomial.eval_X,
    Polynomial.eval_C, zero_add]
  exact Polynomial.eval_divByMonic_pow_rootMultiplicity_ne_zero center hp

private theorem constantCoeff_subst_of_constantCoeff_zero
    (inner outer : 𝕜⟦X⟧) (hinner : constantCoeff inner = 0) :
    constantCoeff (outer.subst inner) = constantCoeff outer := by
  let c := constantCoeff outer
  have houter : constantCoeff (outer - PowerSeries.C c) = 0 := by simp [c]
  have hzero := PowerSeries.constantCoeff_subst_eq_zero
    hinner (outer - PowerSeries.C c) houter
  have hhas := HasSubst.of_constantCoeff_zero' hinner
  rw [PowerSeries.subst_sub hhas] at hzero
  have heq := sub_eq_zero.mp hzero
  simpa [c] using heq

private theorem coeff_one_subst_of_order_two
    (inner outer : 𝕜⟦X⟧) (horder : order inner = (2 : ℕ)) :
    coeff 1 (outer.subst inner) = 0 := by
  have hinner : constantCoeff inner = 0 := by
    rw [← coeff_zero_eq_constantCoeff]
    exact PowerSeries.coeff_of_lt_order 0 (φ := inner)
      (by simpa [horder])
  rw [PowerSeries.coeff_subst'
    (HasSubst.of_constantCoeff_zero' hinner)]
  apply finsum_eq_zero_of_forall_eq_zero
  intro d
  cases d with
  | zero => simp
  | succ d =>
      rw [PowerSeries.coeff_of_lt_order 1
        (φ := inner ^ (d + 1))]
      · simp
      · rw [PowerSeries.order_pow, horder]
        simp only [nsmul_eq_mul]
        norm_cast
        omega

private theorem coeff_three_subst_of_order_two
    (inner outer : 𝕜⟦X⟧) (horder : order inner = (2 : ℕ))
    (hthree : coeff 3 inner = 0) :
    coeff 3 (outer.subst inner) = 0 := by
  have hinner : constantCoeff inner = 0 := by
    rw [← coeff_zero_eq_constantCoeff]
    exact PowerSeries.coeff_of_lt_order 0 (φ := inner)
      (by simpa [horder])
  rw [PowerSeries.coeff_subst'
    (HasSubst.of_constantCoeff_zero' hinner)]
  apply finsum_eq_zero_of_forall_eq_zero
  intro d
  cases d with
  | zero => simp
  | succ d =>
      cases d with
      | zero => simp [hthree]
      | succ d =>
          rw [PowerSeries.coeff_of_lt_order 3
            (φ := inner ^ (d + 2))]
          · simp
          · rw [PowerSeries.order_pow, horder]
            simp only [nsmul_eq_mul]
            norm_cast
            omega

private theorem coeff_three_mul_of_coeff_one_zero
    (f g : 𝕜⟦X⟧) (hfOne : coeff 1 f = 0)
    (hgOne : coeff 1 g = 0) :
    coeff 3 (f * g) =
      coeff 3 f * constantCoeff g +
        constantCoeff f * coeff 3 g := by
  norm_num [PowerSeries.coeff_mul, Finset.antidiagonal, hfOne, hgOne]
  ring

private theorem coeff_three_pow_of_coeff_one_zero
    (f : 𝕜⟦X⟧) (n : ℕ) (hOne : coeff 1 f = 0) :
    coeff 3 (f ^ n) =
      (n : 𝕜) * coeff 3 f * constantCoeff f ^ (n - 1) := by
  induction n with
  | zero => simp
  | succ n ih =>
      rw [pow_succ,
        coeff_three_mul_of_coeff_one_zero (f ^ n) f]
      · rw [ih]
        simp only [map_pow]
        rcases n with _ | n
        · simp
        · simp only [Nat.cast_add, Nat.cast_one,
            Nat.add_sub_cancel, pow_succ]
          ring
      · simpa [PowerSeries.coeff_one_pow, hOne]
      · exact hOne

private theorem order_eq_zero_of_constantCoeff_ne_zero
    (f : 𝕜⟦X⟧) (hconstant : constantCoeff f ≠ 0) :
    order f = ((0 : ℕ) : ℕ∞) := by
  apply (PowerSeries.order_eq_nat).2
  constructor
  · simpa [PowerSeries.coeff_zero_eq_constantCoeff]
  · intro i hi
    omega

private theorem shifted_substitution_factorization
    (p : Polynomial 𝕜) (center : 𝕜) (inner : 𝕜⟦X⟧)
    (hinner : constantCoeff inner = 0) :
    ((shiftedPolynomial p center : 𝕜⟦X⟧).subst inner) =
      inner ^ p.rootMultiplicity center *
        ((shiftedRootUnit p center : 𝕜⟦X⟧).subst inner) := by
  have hfactor := shiftedPolynomial_eq_rootPower_mul_unit p center
  have hhas := HasSubst.of_constantCoeff_zero' hinner
  have h := congrArg
    (fun q : Polynomial 𝕜 => ((q : 𝕜⟦X⟧).subst inner)) hfactor
  simpa [map_mul, map_pow, PowerSeries.subst_mul hhas,
    PowerSeries.subst_pow hhas, PowerSeries.subst_X hhas] using h

set_option maxHeartbeats 800000 in
-- Symbolic root-unit substitution and coefficient normalization need more elaboration fuel.
/-- A nonzero polynomial cannot satisfy Julia's local identity against a
ramified displacement with first odd relative offset three. -/
theorem polynomial_julia_root_factor_obstruction
    (p : Polynomial 𝕜) (hp : p ≠ 0)
    (inputCenter outputCenter : 𝕜)
    (displacement derivativeFactor : 𝕜⟦X⟧)
    (hDisplacementOrder : order displacement = (2 : ℕ))
    (hDisplacementThree : coeff 3 displacement = 0)
    (hDisplacementFive : coeff 5 displacement ≠ 0)
    (hDerivativeConstant :
      constantCoeff derivativeFactor = coeff 2 displacement)
    (hDerivativeOne : coeff 1 derivativeFactor = 0)
    (hDerivativeThree :
      coeff 3 derivativeFactor =
        (5 / 2 : 𝕜) * coeff 5 displacement)
    (hJulia :
      ((shiftedPolynomial p outputCenter : 𝕜⟦X⟧).subst displacement) =
        derivativeFactor *
          ((shiftedPolynomial p inputCenter : 𝕜⟦X⟧).subst (X ^ 2))) :
    False := by
  let n := p.rootMultiplicity outputCenter
  let m := p.rootMultiplicity inputCenter
  let outUnit : 𝕜⟦X⟧ :=
    (shiftedRootUnit p outputCenter : 𝕜⟦X⟧).subst displacement
  let inUnit : 𝕜⟦X⟧ :=
    (shiftedRootUnit p inputCenter : 𝕜⟦X⟧).subst (X ^ 2)
  let leadingUnit := displacement.divXPowOrder

  have hDisplacementZero : constantCoeff displacement = 0 := by
    rw [← coeff_zero_eq_constantCoeff]
    exact PowerSeries.coeff_of_lt_order 0 (φ := displacement)
      (by simpa [hDisplacementOrder])
  have hDisplacementOne : coeff 1 displacement = 0 :=
    PowerSeries.coeff_of_lt_order 1 (φ := displacement)
      (by simpa [hDisplacementOrder])
  have hLeadingFactor : X ^ 2 * leadingUnit = displacement := by
    simpa [leadingUnit, hDisplacementOrder] using
      (PowerSeries.X_pow_order_mul_divXPowOrder
        (f := displacement))
  have hLeadingZero : constantCoeff leadingUnit = coeff 2 displacement := by
    change constantCoeff displacement.divXPowOrder = coeff 2 displacement
    rw [PowerSeries.constantCoeff_divXPowOrder]
    simp [hDisplacementOrder]
  have hLeadingOne : coeff 1 leadingUnit = 0 := by
    simpa [leadingUnit, hDisplacementOrder] using hDisplacementThree
  have hLeadingThree : coeff 3 leadingUnit = coeff 5 displacement := by
    simp [leadingUnit, hDisplacementOrder]
  have hLeadingNonzero : coeff 2 displacement ≠ 0 := by
    exact (PowerSeries.order_eq_nat.mp hDisplacementOrder).1

  have hOutConstant :
      constantCoeff outUnit =
        (shiftedRootUnit p outputCenter).coeff 0 := by
    dsimp [outUnit]
    rw [constantCoeff_subst_of_constantCoeff_zero _ _ hDisplacementZero]
    rfl
  have hInConstant :
      constantCoeff inUnit =
        (shiftedRootUnit p inputCenter).coeff 0 := by
    dsimp [inUnit]
    rw [constantCoeff_subst_of_constantCoeff_zero]
    · rfl
    · simp
  have hOutConstantNonzero : constantCoeff outUnit ≠ 0 := by
    rw [hOutConstant]
    exact shiftedRootUnit_constantCoeff_ne_zero hp outputCenter
  have hInConstantNonzero : constantCoeff inUnit ≠ 0 := by
    rw [hInConstant]
    exact shiftedRootUnit_constantCoeff_ne_zero hp inputCenter
  have hOutOne : coeff 1 outUnit = 0 := by
    exact coeff_one_subst_of_order_two displacement _ hDisplacementOrder
  have hOutThree : coeff 3 outUnit = 0 := by
    exact coeff_three_subst_of_order_two displacement _
      hDisplacementOrder hDisplacementThree
  have hInOne : coeff 1 inUnit = 0 := by
    exact coeff_one_subst_of_order_two (X ^ 2) _ (by simp)
  have hInThree : coeff 3 inUnit = 0 := by
    exact coeff_three_subst_of_order_two (X ^ 2) _ (by simp)
      (by norm_num [PowerSeries.coeff_X_pow])

  have hOutputFactor := shifted_substitution_factorization
    p outputCenter displacement hDisplacementZero
  have hInputFactor := shifted_substitution_factorization
    p inputCenter (X ^ 2) (by simp)
  have hFactored :
      X ^ (2 * n) * (leadingUnit ^ n * outUnit) =
        X ^ (2 * m) * (derivativeFactor * inUnit) := by
    rw [hOutputFactor, hInputFactor] at hJulia
    change displacement ^ n * outUnit =
      derivativeFactor * ((X ^ 2) ^ m * inUnit) at hJulia
    rw [← hLeadingFactor] at hJulia
    calc
      X ^ (2 * n) * (leadingUnit ^ n * outUnit) =
          (X ^ 2 * leadingUnit) ^ n * outUnit := by ring
      _ = derivativeFactor * ((X ^ 2) ^ m * inUnit) := hJulia
      _ = X ^ (2 * m) * (derivativeFactor * inUnit) := by ring

  have hLeftUnitConstant :
      constantCoeff (leadingUnit ^ n * outUnit) ≠ 0 := by
    simp only [map_mul, map_pow, hLeadingZero]
    exact mul_ne_zero (pow_ne_zero n hLeadingNonzero) hOutConstantNonzero
  have hRightUnitConstant :
      constantCoeff (derivativeFactor * inUnit) ≠ 0 := by
    rw [map_mul, hDerivativeConstant]
    exact mul_ne_zero hLeadingNonzero hInConstantNonzero
  have hLeftUnitOrder := order_eq_zero_of_constantCoeff_ne_zero
    (leadingUnit ^ n * outUnit) hLeftUnitConstant
  have hRightUnitOrder := order_eq_zero_of_constantCoeff_ne_zero
    (derivativeFactor * inUnit) hRightUnitConstant
  have hnm : n = m := by
    have horders := congrArg PowerSeries.order hFactored
    rw [PowerSeries.order_mul, PowerSeries.order_X_pow,
      hLeftUnitOrder, PowerSeries.order_mul,
      PowerSeries.order_X_pow, hRightUnitOrder] at horders
    norm_cast at horders
    omega
  rw [hnm] at hFactored
  change X ^ (2 * m) * (leadingUnit ^ m * outUnit) =
    X ^ (2 * m) * (derivativeFactor * inUnit) at hFactored
  have hUnits :
      leadingUnit ^ m * outUnit = derivativeFactor * inUnit := by
    exact (PowerSeries.X_pow_mul_inj (k := 2 * m)).mp hFactored

  have hPowerOne : coeff 1 (leadingUnit ^ m) = 0 := by
    simpa [PowerSeries.coeff_one_pow, hLeadingOne]
  have hLeadingBalance := congrArg constantCoeff hUnits
  simp only [map_mul, map_pow, hLeadingZero,
    hDerivativeConstant] at hLeadingBalance
  have hBranchBalance := congrArg (coeff 3) hUnits
  rw [coeff_three_mul_of_coeff_one_zero
        (leadingUnit ^ m) outUnit hPowerOne hOutOne,
      coeff_three_mul_of_coeff_one_zero
        derivativeFactor inUnit hDerivativeOne hInOne,
      coeff_three_pow_of_coeff_one_zero leadingUnit m hLeadingOne,
      hLeadingThree, hLeadingZero, hDerivativeThree] at hBranchBalance
  simp only [hOutThree, hInThree, mul_zero, add_zero] at hBranchBalance

  rcases Nat.eq_zero_or_pos m with hmZero | hmPositive
  · rw [hmZero] at hBranchBalance
    norm_num at hBranchBalance
    rcases hBranchBalance with hzero | hzero
    · exact hDisplacementFive hzero
    · exact hInConstantNonzero hzero
  · have hPowerRewrite :
        coeff 2 displacement ^ m =
          coeff 2 displacement * coeff 2 displacement ^ (m - 1) := by
      conv_lhs => rw [show m = (m - 1) + 1 by omega]
      rw [pow_succ]
      ring
    have hUnitRelation :
        constantCoeff inUnit =
          coeff 2 displacement ^ (m - 1) * constantCoeff outUnit := by
      rw [hPowerRewrite] at hLeadingBalance
      have hcancel :
          coeff 2 displacement ^ (m - 1) * constantCoeff outUnit =
            constantCoeff inUnit :=
        mul_left_cancel₀ hLeadingNonzero
          (by simpa [mul_assoc] using hLeadingBalance)
      exact hcancel.symm
    rw [hUnitRelation] at hBranchBalance
    have hCommonNonzero :
        coeff 5 displacement *
            (coeff 2 displacement ^ (m - 1) * constantCoeff outUnit) ≠ 0 :=
      mul_ne_zero hDisplacementFive
        (mul_ne_zero (pow_ne_zero _ hLeadingNonzero) hOutConstantNonzero)
    have hMultiplicity : (m : 𝕜) = 5 / 2 := by
      have hzero :
          ((m : 𝕜) - 5 / 2) *
              (coeff 5 displacement *
                (coeff 2 displacement ^ (m - 1) *
                  constantCoeff outUnit)) = 0 := by
        calc
          ((m : 𝕜) - 5 / 2) *
              (coeff 5 displacement *
                (coeff 2 displacement ^ (m - 1) *
                  constantCoeff outUnit)) =
              (m : 𝕜) * coeff 5 displacement *
                  coeff 2 displacement ^ (m - 1) *
                    constantCoeff outUnit -
                (5 / 2 : 𝕜) * coeff 5 displacement *
                  (coeff 2 displacement ^ (m - 1) *
                    constantCoeff outUnit) := by ring
          _ = 0 := sub_eq_zero.mpr hBranchBalance
      exact (sub_eq_zero.mp <| (mul_eq_zero.mp hzero).resolve_right
        hCommonNonzero)
    have hdoubleField : (2 : 𝕜) * m = 5 := by
      rw [hMultiplicity]
      norm_num
    have hdoubleNat : 2 * m = 5 := by exact_mod_cast hdoubleField
    omega

end FormalRamifiedJuliaObstruction
