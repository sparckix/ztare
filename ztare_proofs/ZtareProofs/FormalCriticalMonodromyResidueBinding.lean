import Mathlib.Analysis.Polynomial.Order
import Mathlib.Tactic
import ZtareProofs.FormalCriticalResidueIrrationality
import ZtareProofs.FormalComplexMonodromyNonTorsion

/-!
# Exact pole-to-eliminant binding for the critical logarithmic differential

This file binds a concrete real pole of the rational differential
`N(t) / ((t - 1) Q(t))` to the degree-seven residue eliminant.  The large
factor quotient is certificate data checked by normalization; it is not a
premise of the theorem.
-/

namespace FormalCriticalMonodromyResidueBinding

open Polynomial Set

/-- Degree-seven pole polynomial of the rationalized critical differential. -/
noncomputable def polePolynomial : ℝ[X] :=
    C 199 * X ^ 7
  + C (-1393) * X ^ 6
  + C 67 * X ^ 5
  + C 219 * X ^ 4
  + C 5973 * X ^ 3
  + C 10125 * X ^ 2
  + C 10593 * X
  + C 2889

/-- Numerator of the rationalized logarithmic differential. -/
noncomputable def numeratorPolynomial : ℝ[X] :=
  C 896 * X * (X - C 3) * (X + C 1) * (X ^ 2 - C 6 * X - C 3)

noncomputable def poleValue (t : ℝ) : ℝ := polePolynomial.eval t

noncomputable def numeratorValue (t : ℝ) : ℝ :=
  numeratorPolynomial.eval t

noncomputable def poleDerivativeValue (t : ℝ) : ℝ :=
  polePolynomial.derivative.eval t

noncomputable def residueDenominator (t : ℝ) : ℝ :=
  (t - 1) * poleDerivativeValue t

noncomputable def residueAt (t : ℝ) : ℝ :=
  numeratorValue t / residueDenominator t

/-- The pole polynomial has a real root in a small rational interval. -/
theorem exists_real_pole :
    ∃ a ∈ Icc (-(2 : ℝ) / 5) (-(3 : ℝ) / 10), poleValue a = 0 := by
  have hab : (-(2 : ℝ) / 5) ≤ (-(3 : ℝ) / 10) := by norm_num
  have hzero :
      (0 : ℝ) ∈ Icc
        (polePolynomial.eval (-(2 : ℝ) / 5))
        (polePolynomial.eval (-(3 : ℝ) / 10)) := by
    constructor <;> norm_num [polePolynomial]
  obtain ⟨a, ha, hroot⟩ := (Set.mem_image ..).mp
    (intermediate_value_Icc hab
      polePolynomial.continuous.continuousOn hzero)
  exact ⟨a, ha, by simpa [poleValue] using hroot⟩

/-- Bezout coefficient multiplying the pole polynomial in the
squarefreeness certificate. -/
noncomputable def derivativeBezoutPole (t : ℝ) : ℝ :=
    (-11510914833122929) * t ^ 5
  + 75457276985108221 * t ^ 4
  + (-44605810977466658) * t ^ 3
  + 15288997185969698 * t ^ 2
  + (-141309496207899549) * t
  + (-117644966848997871)

/-- Bezout coefficient multiplying the derivative in the squarefreeness
certificate. -/
noncomputable def derivativeBezoutDerivative (t : ℝ) : ℝ :=
    1644416404731847 * t ^ 6
  + (-12424027402604450) * t ^ 5
  + 7443556347478601 * t ^ 4
  + (-1994521162680412) * t ^ 3
  + 48018416362976265 * t ^ 2
  + 61712473261723998 * t
  + 49419063659980935

theorem derivative_bezout_identity (t : ℝ) :
    derivativeBezoutPole t * poleValue t
      + derivativeBezoutDerivative t * poleDerivativeValue t
      = 183619832123423195136 := by
  simp [
    derivativeBezoutPole,
    derivativeBezoutDerivative,
    poleValue,
    poleDerivativeValue,
    polePolynomial,
  ]
  ring

/-- Bezout coefficient multiplying the pole polynomial in the numerator
coprimality certificate. -/
noncomputable def numeratorBezoutPole (t : ℝ) : ℝ :=
    296668226176 * t ^ 4
  + (-2492682577280) * t ^ 3
  + 2785294866816 * t ^ 2
  + 5981380927872 * t
  + 257635123200

/-- Bezout coefficient multiplying the numerator in its coprimality
certificate with the pole polynomial. -/
noncomputable def numeratorBezoutNumerator (t : ℝ) : ℝ :=
    (-65889483269) * t ^ 6
  + 487730865926 * t ^ 5
  + (-218951529899) * t ^ 4
  + 19042502964 * t ^ 3
  + (-1981220988171) * t ^ 2
  + (-2561731774938) * t
  + (-2481316760997)

theorem numerator_bezout_identity (t : ℝ) :
    numeratorBezoutPole t * poleValue t
      + numeratorBezoutNumerator t * numeratorValue t
      = 744307870924800 := by
  simp [
    numeratorBezoutPole,
    numeratorBezoutNumerator,
    poleValue,
    numeratorValue,
    polePolynomial,
    numeratorPolynomial,
  ]
  ring

theorem poleDerivativeValue_ne_zero_of_root
    {a : ℝ} (hroot : poleValue a = 0) :
    poleDerivativeValue a ≠ 0 := by
  intro hzero
  have hbez := derivative_bezout_identity a
  rw [hroot, hzero] at hbez
  norm_num at hbez

theorem numeratorValue_ne_zero_of_root
    {a : ℝ} (hroot : poleValue a = 0) :
    numeratorValue a ≠ 0 := by
  intro hzero
  have hbez := numerator_bezout_identity a
  rw [hroot, hzero] at hbez
  norm_num at hbez

theorem pole_sub_one_ne_zero_of_root
    {a : ℝ} (hroot : poleValue a = 0) :
    a - 1 ≠ 0 := by
  intro hzero
  have ha : a = 1 := sub_eq_zero.mp hzero
  subst a
  norm_num [poleValue, polePolynomial] at hroot

theorem residueDenominator_ne_zero_of_root
    {a : ℝ} (hroot : poleValue a = 0) :
    residueDenominator a ≠ 0 := by
  exact mul_ne_zero
    (pole_sub_one_ne_zero_of_root hroot)
    (poleDerivativeValue_ne_zero_of_root hroot)

/-- The residue eliminant after clearing the seventh power of its
denominator. -/
noncomputable def clearedResidueEliminant (t : ℝ) : ℝ :=
    (-77175) * residueDenominator t ^ 7
  + 19332313 * numeratorValue t * residueDenominator t ^ 6
  + (-227127817) * numeratorValue t ^ 2 * residueDenominator t ^ 5
  + (-2078539001) * numeratorValue t ^ 3 * residueDenominator t ^ 4
  + 2967370224 * numeratorValue t ^ 4 * residueDenominator t ^ 3
  + 4562281392 * numeratorValue t ^ 5 * residueDenominator t ^ 2
  + (-5328693312) * numeratorValue t ^ 6 * residueDenominator t
  + (-5328693312) * numeratorValue t ^ 7

/-- Exact quotient in the divisibility certificate
`clearedResidueEliminant = poleValue * residueFactorQuotient`. -/
noncomputable def residueFactorQuotient (t : ℝ) : ℝ :=
    (-3947129513325589854701025) * t ^ 42
  + 165779439559674773897443050 * t ^ 41
  + (-2436252447861993642319684477) * t ^ 40
  + 5711987264096050164534282136 * t ^ 39
  + 283156661457858544984068150598 * t ^ 38
  + (-4351916939982805118734885654228) * t ^ 37
  + 31473287343862153784116295387046 * t ^ 36
  + (-124778120175036642795435750625704) * t ^ 35
  + 198927593705668665020294963964791 * t ^ 34
  + 556868253272870637816084473757154 * t ^ 33
  + (-4220135360838601605793651245393533) * t ^ 32
  + 12594399357841715418717997607162336 * t ^ 31
  + (-22006446005030024870319992383275288) * t ^ 30
  + 13193787538472035863594020371846416 * t ^ 29
  + 45487703970845663473360082395260968 * t ^ 28
  + (-104845159928522344097111821718284448) * t ^ 27
  + (-22549234687210790239353488494817474) * t ^ 26
  + 199919224337740375118781021746670452 * t ^ 25
  + 134575356075563848412809031546305446 * t ^ 24
  + (-319274695126980822330357191675620272) * t ^ 23
  + (-475533656576603538957916152333519228) * t ^ 22
  + (-151195169201123166480035689675651704) * t ^ 21
  + 908393434589257912608693924260206980 * t ^ 20
  + 2560365326759588183654378936748331344 * t ^ 19
  + (-185758318760679821747434071744071514) * t ^ 18
  + (-6617356349311638697228094333928293388) * t ^ 17
  + (-4226071926345331829066381240374807746) * t ^ 16
  + 7477758159798044790846105725349103968 * t ^ 15
  + 10612903411949700805917518860981712424 * t ^ 14
  + (-233044302347713595349300686954534640) * t ^ 13
  + (-9524284057777239555717949567014676248) * t ^ 12
  + (-7280002282776381577379396967394330656) * t ^ 11
  + (-271239588618717001271513823497771901) * t ^ 10
  + 2861548444464491177874126561931004322 * t ^ 9
  + 1841110433742656775173202718518564855 * t ^ 8
  + 260375135679795657801249680212150488 * t ^ 7
  + (-258301587700054785793404500728599258) * t ^ 6
  + (-160296711437348145677043194568392916) * t ^ 5
  + (-34514162362402783081199486433784890) * t ^ 4
  + (-15319121871065218916647087230696) * t ^ 3
  + 1023672212784968015606009817219075 * t ^ 2
  + 77328544003609308149346747409962 * t
  + 399817594855146808800248255775

theorem cleared_residue_eliminant_factorization (t : ℝ) :
    clearedResidueEliminant t =
      poleValue t * residueFactorQuotient t := by
  simp [
    clearedResidueEliminant,
    residueFactorQuotient,
    residueDenominator,
    numeratorValue,
    poleDerivativeValue,
    poleValue,
    numeratorPolynomial,
    polePolynomial,
  ]
  ring

theorem residuePolynomial_eval_residueAt_eq_zero_of_root
    {a : ℝ} (hroot : poleValue a = 0) :
    (FormalCriticalResidueIrrationality.residuePolynomial.map
      (Int.castRingHom ℝ)).eval (residueAt a) = 0 := by
  have hden := residueDenominator_ne_zero_of_root hroot
  have hfactor := cleared_residue_eliminant_factorization a
  rw [hroot, zero_mul] at hfactor
  have hscaled :
      residueDenominator a ^ 7 *
          (FormalCriticalResidueIrrationality.residuePolynomial.map
            (Int.castRingHom ℝ)).eval (residueAt a) =
        clearedResidueEliminant a := by
    simp [
      FormalCriticalResidueIrrationality.residuePolynomial,
      clearedResidueEliminant,
      residueAt,
    ]
    field_simp [hden]
    ring
  have hproduct :
      residueDenominator a ^ 7 *
          (FormalCriticalResidueIrrationality.residuePolynomial.map
            (Int.castRingHom ℝ)).eval (residueAt a) = 0 := by
    exact hscaled.trans hfactor
  exact (mul_eq_zero.mp hproduct).resolve_left (pow_ne_zero 7 hden)

/-- The explicit rational differential has a noncancelling real pole whose
residue is irrational and whose exponential multiplier has infinite order. -/
theorem exists_critical_irrational_residue_with_infinite_monodromy :
    ∃ a rho : ℝ,
      a ∈ Icc (-(2 : ℝ) / 5) (-(3 : ℝ) / 10)
      ∧ poleValue a = 0
      ∧ numeratorValue a ≠ 0
      ∧ residueDenominator a ≠ 0
      ∧ rho = residueAt a
      ∧ (FormalCriticalResidueIrrationality.residuePolynomial.map
          (Int.castRingHom ℝ)).eval rho = 0
      ∧ Irrational rho
      ∧ ∀ N : ℕ, 0 < N →
          FormalComplexMonodromyNonTorsion.monodromyMultiplier rho ^ N ≠ 1 := by
  obtain ⟨a, ha, hroot⟩ := exists_real_pole
  let rho := residueAt a
  have hnum := numeratorValue_ne_zero_of_root hroot
  have hden := residueDenominator_ne_zero_of_root hroot
  have hpoly := residuePolynomial_eval_residueAt_eq_zero_of_root hroot
  have hirr : Irrational rho :=
    FormalCriticalResidueIrrationality.residue_polynomial_root_irrational
      rho hpoly
  refine ⟨a, rho, ha, hroot, hnum, hden, rfl, hpoly, hirr, ?_⟩
  intro N hN
  exact FormalComplexMonodromyNonTorsion.monodromyMultiplier_pow_ne_one
    rho hirr N hN

/-- The theorem-scoped surface used by governed coverage receipts. -/
theorem critical_monodromy_residue_binding_terminal_certificate :
    ∃ a rho : ℝ,
      a ∈ Icc (-(2 : ℝ) / 5) (-(3 : ℝ) / 10)
      ∧ poleValue a = 0
      ∧ numeratorValue a ≠ 0
      ∧ residueDenominator a ≠ 0
      ∧ rho = residueAt a
      ∧ (FormalCriticalResidueIrrationality.residuePolynomial.map
          (Int.castRingHom ℝ)).eval rho = 0
      ∧ Irrational rho
      ∧ ∀ N : ℕ, 0 < N →
          FormalComplexMonodromyNonTorsion.monodromyMultiplier rho ^ N ≠ 1 := by
  exact exists_critical_irrational_residue_with_infinite_monodromy

end FormalCriticalMonodromyResidueBinding
