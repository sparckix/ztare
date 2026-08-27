import Mathlib.Algebra.Polynomial.FieldDivision
import Mathlib.Analysis.Analytic.Polynomial
import Mathlib.Analysis.Complex.HasPrimitives
import Mathlib.Tactic
import ZtareProofs.FormalAnalyticLogarithmicLoop
import ZtareProofs.FormalCriticalConnectionRationalization
import ZtareProofs.FormalCriticalMonodromyResidueBinding

/-!
# Critical rational differential realized as an infinite loop orbit

The exact critical numerator and pole polynomials are complexified.  At the
governed simple real pole, two divisions by `X - a` construct the removable
regular part of the logarithmic differential.  Analyticity supplies a local
primitive, so the general logarithmic-loop kernel produces explicit repeated
continuations and an injective endpoint orbit.
-/

namespace FormalCriticalHolonomyLoop

open Complex Filter Metric Polynomial Set
open FormalAnalyticLogarithmicLoop
open scoped Topology

noncomputable def criticalPolePolynomial : ℂ[X] :=
  FormalCriticalMonodromyResidueBinding.polePolynomial.map
    Complex.ofRealHom

noncomputable def criticalNumeratorPolynomial : ℂ[X] :=
  FormalCriticalMonodromyResidueBinding.numeratorPolynomial.map
    Complex.ofRealHom

noncomputable def criticalCoefficient (z : ℂ) : ℂ :=
  criticalNumeratorPolynomial.eval z /
    ((z - 1) * criticalPolePolynomial.eval z)

noncomputable def poleQuotient (a : ℂ) : ℂ[X] :=
  criticalPolePolynomial /ₘ (X - C a)

noncomputable def reducedDenominatorPolynomial (a : ℂ) : ℂ[X] :=
  (X - C 1) * poleQuotient a

noncomputable def criticalResidue (a : ℂ) : ℂ :=
  criticalNumeratorPolynomial.eval a /
    (reducedDenominatorPolynomial a).eval a

noncomputable def crossNumeratorPolynomial (a : ℂ) : ℂ[X] :=
  criticalNumeratorPolynomial *
      C ((reducedDenominatorPolynomial a).eval a) -
    C (criticalNumeratorPolynomial.eval a) *
      reducedDenominatorPolynomial a

noncomputable def regularNumeratorPolynomial (a : ℂ) : ℂ[X] :=
  crossNumeratorPolynomial a /ₘ (X - C a)

noncomputable def criticalRegularCoefficient (a z : ℂ) : ℂ :=
  (regularNumeratorPolynomial a).eval z /
    ((reducedDenominatorPolynomial a).eval z *
      (reducedDenominatorPolynomial a).eval a)

@[simp] theorem criticalPolePolynomial_eval_ofReal (a : ℝ) :
    criticalPolePolynomial.eval (a : ℂ) =
      (FormalCriticalMonodromyResidueBinding.poleValue a : ℂ) := by
  unfold criticalPolePolynomial
    FormalCriticalMonodromyResidueBinding.poleValue
  exact Polynomial.eval_map_apply Complex.ofRealHom a

@[simp] theorem criticalNumeratorPolynomial_eval_ofReal (a : ℝ) :
    criticalNumeratorPolynomial.eval (a : ℂ) =
      (FormalCriticalMonodromyResidueBinding.numeratorValue a : ℂ) := by
  unfold criticalNumeratorPolynomial
    FormalCriticalMonodromyResidueBinding.numeratorValue
  exact Polynomial.eval_map_apply Complex.ofRealHom a

@[simp] theorem criticalPolePolynomial_derivative_eval_ofReal (a : ℝ) :
    criticalPolePolynomial.derivative.eval (a : ℂ) =
      (FormalCriticalMonodromyResidueBinding.poleDerivativeValue a : ℂ) := by
  unfold criticalPolePolynomial
    FormalCriticalMonodromyResidueBinding.poleDerivativeValue
  rw [derivative_map]
  exact Polynomial.eval_map_apply Complex.ofRealHom a

/-- Division by `X-a` exactly removes a selected root of the pole
polynomial. -/
theorem pole_factorization {a : ℂ}
    (hroot : criticalPolePolynomial.eval a = 0) :
    (X - C a) * poleQuotient a = criticalPolePolynomial := by
  rw [poleQuotient,
    X_sub_C_mul_divByMonic_eq_sub_modByMonic,
    modByMonic_X_sub_C_eq_C_eval, hroot, C_0, sub_zero]

/-- The quotient evaluated at a root is the derivative of the pole
polynomial there. -/
theorem poleQuotient_eval_root {a : ℂ}
    (_hroot : criticalPolePolynomial.eval a = 0) :
    (poleQuotient a).eval a =
      criticalPolePolynomial.derivative.eval a := by
  have hderivative :=
    divByMonic_add_X_sub_C_mul_derivative_divByMonic_eq_derivative
      criticalPolePolynomial a
  have heval := congrArg (fun p : ℂ[X] => p.eval a) hderivative
  simpa [poleQuotient] using heval

theorem reducedDenominator_eval_root {a : ℂ}
    (hroot : criticalPolePolynomial.eval a = 0) :
    (reducedDenominatorPolynomial a).eval a =
      (a - 1) * criticalPolePolynomial.derivative.eval a := by
  rw [reducedDenominatorPolynomial, eval_mul, eval_sub, eval_X, eval_C,
    poleQuotient_eval_root hroot]

theorem reducedDenominator_eval_real_root
    {a : ℝ}
    (hroot : FormalCriticalMonodromyResidueBinding.poleValue a = 0) :
    (reducedDenominatorPolynomial (a : ℂ)).eval (a : ℂ) =
      (FormalCriticalMonodromyResidueBinding.residueDenominator a : ℂ) := by
  rw [reducedDenominator_eval_root (by simpa using congrArg Complex.ofReal hroot)]
  simp [FormalCriticalMonodromyResidueBinding.residueDenominator]

theorem criticalResidue_real_root
    {a rho : ℝ}
    (hroot : FormalCriticalMonodromyResidueBinding.poleValue a = 0)
    (hrho : rho = FormalCriticalMonodromyResidueBinding.residueAt a) :
    criticalResidue (a : ℂ) = (rho : ℂ) := by
  rw [criticalResidue, reducedDenominator_eval_real_root hroot,
    criticalNumeratorPolynomial_eval_ofReal, hrho]
  simp [FormalCriticalMonodromyResidueBinding.residueAt,
    FormalCriticalMonodromyResidueBinding.numeratorValue]

@[simp] theorem crossNumeratorPolynomial_eval_center (a : ℂ) :
    (crossNumeratorPolynomial a).eval a = 0 := by
  simp [crossNumeratorPolynomial]

/-- The cross numerator has its center factor removed without a remainder. -/
theorem cross_numerator_factorization (a : ℂ) :
    (X - C a) * regularNumeratorPolynomial a =
      crossNumeratorPolynomial a := by
  rw [regularNumeratorPolynomial,
    X_sub_C_mul_divByMonic_eq_sub_modByMonic,
    modByMonic_X_sub_C_eq_C_eval,
    crossNumeratorPolynomial_eval_center, C_0, sub_zero]

/-- Exact pointwise pole-plus-regular decomposition away from the selected
pole and the remaining reduced denominator. -/
theorem critical_coefficient_decomposition
    {a z : ℂ}
    (hroot : criticalPolePolynomial.eval a = 0)
    (hza : z - a ≠ 0)
    (hBa : (reducedDenominatorPolynomial a).eval a ≠ 0)
    (hBz : (reducedDenominatorPolynomial a).eval z ≠ 0) :
    criticalCoefficient z =
      criticalResidue a / (z - a) + criticalRegularCoefficient a z := by
  have hpole := congrArg (fun p : ℂ[X] => p.eval z)
    (pole_factorization hroot)
  have hpoleEval :
      criticalPolePolynomial.eval z =
        (z - a) * (poleQuotient a).eval z := by
    simpa using hpole.symm
  have hdenominator :
      (z - 1) * criticalPolePolynomial.eval z =
        (z - a) * (reducedDenominatorPolynomial a).eval z := by
    rw [hpoleEval, reducedDenominatorPolynomial, eval_mul, eval_sub,
      eval_X, eval_C]
    ring
  have hcross := congrArg (fun p : ℂ[X] => p.eval z)
    (cross_numerator_factorization a)
  have hcrossEval :
      (z - a) * (regularNumeratorPolynomial a).eval z =
        criticalNumeratorPolynomial.eval z *
            (reducedDenominatorPolynomial a).eval a -
          criticalNumeratorPolynomial.eval a *
            (reducedDenominatorPolynomial a).eval z := by
    simpa [crossNumeratorPolynomial] using hcross
  rw [criticalCoefficient, hdenominator, criticalResidue,
    criticalRegularCoefficient]
  field_simp [hza, hBa, hBz]
  rw [hcrossEval]
  ring

theorem criticalRegularCoefficient_analyticAt
    {a : ℂ}
    (hBa : (reducedDenominatorPolynomial a).eval a ≠ 0) :
    AnalyticAt ℂ (criticalRegularCoefficient a) a := by
  have hnum : AnalyticAt ℂ
      (fun z : ℂ => (regularNumeratorPolynomial a).eval z) a := by
    simpa [aeval_def] using
      (analyticAt_id.aeval_polynomial (regularNumeratorPolynomial a))
  have hdenPolynomial : AnalyticAt ℂ
      (fun z : ℂ => (reducedDenominatorPolynomial a).eval z) a := by
    simpa [aeval_def] using
      (analyticAt_id.aeval_polynomial (reducedDenominatorPolynomial a))
  have hden : AnalyticAt ℂ
      (fun z : ℂ => (reducedDenominatorPolynomial a).eval z *
        (reducedDenominatorPolynomial a).eval a) a := by
    exact hdenPolynomial.mul analyticAt_const
  exact hnum.div hden (mul_ne_zero hBa hBa)

/-- A completed local loop realization for the exact critical rational
differential.  All fields below are constructed by the existence theorem. -/
structure CriticalLoopRealization where
  pole : ℝ
  residue : ℝ
  pole_mem : pole ∈ Icc (-(2 : ℝ) / 5) (-(3 : ℝ) / 10)
  pole_root : FormalCriticalMonodromyResidueBinding.poleValue pole = 0
  residue_binding :
    residue = FormalCriticalMonodromyResidueBinding.residueAt pole
  residue_irrational : Irrational residue
  carrier : LogarithmicCircleCarrier
  center_binding : carrier.center = (pole : ℂ)
  residue_carrier_binding : carrier.residue = (residue : ℂ)
  coefficient_on_circle : ∀ theta : ℝ,
    carrier.coefficient
        (circleMap carrier.center carrier.radius theta) =
      criticalCoefficient
        (circleMap carrier.center carrier.radius theta)
  multiplier_binding :
    carrier.multiplier =
      FormalComplexMonodromyNonTorsion.monodromyMultiplier residue
  multiplier_non_torsion : ∀ N : ℕ, 0 < N → carrier.multiplier ^ N ≠ 1

/-- The exact pole theorem, polynomial cancellation, and local primitive
construction produce the critical circle carrier. -/
theorem exists_criticalLoopRealization :
    Nonempty CriticalLoopRealization := by
  obtain ⟨a, rho, ha, hroot, _hnum, hresidueDenominator,
      hrho, _heliminant, hirrational, hnontorsion⟩ :=
    FormalCriticalMonodromyResidueBinding.exists_critical_irrational_residue_with_infinite_monodromy
  let ac : ℂ := (a : ℂ)
  have hrootC : criticalPolePolynomial.eval ac = 0 := by
    simpa [ac] using congrArg Complex.ofReal hroot
  have hBa : (reducedDenominatorPolynomial ac).eval ac ≠ 0 := by
    rw [show ac = (a : ℂ) by rfl,
      reducedDenominator_eval_real_root hroot]
    exact Complex.ofReal_ne_zero.mpr hresidueDenominator
  have hregular := criticalRegularCoefficient_analyticAt hBa
  have hBcontinuous : ContinuousAt
      (fun z : ℂ => (reducedDenominatorPolynomial ac).eval z) ac := by
    fun_prop
  have hlocal : ∀ᶠ z in 𝓝 ac,
      AnalyticAt ℂ (criticalRegularCoefficient ac) z ∧
      (reducedDenominatorPolynomial ac).eval z ≠ 0 :=
    hregular.eventually_analyticAt.and (hBcontinuous.eventually_ne hBa)
  obtain ⟨radius, hradius, hball⟩ :=
    Metric.eventually_nhds_iff_ball.mp hlocal
  have hdifferentiableOn : DifferentiableOn ℂ
      (criticalRegularCoefficient ac) (ball ac radius) := by
    intro z hz
    exact (hball z hz).1.differentiableAt.differentiableWithinAt
  obtain ⟨primitive, _hprimitiveCenter, hprimitive⟩ :=
    hdifferentiableOn.isExactOn_ball.with_val_at ac 0
  have hhalfPositive : 0 < radius / 2 := by positivity
  have hhalfNe : radius / 2 ≠ 0 := ne_of_gt hhalfPositive
  have hcircleMem : ∀ theta : ℝ,
      circleMap ac (radius / 2) theta ∈ ball ac radius := by
    intro theta
    rw [mem_ball, dist_eq_norm, circleMap_sub_center,
      norm_circleMap_zero, abs_of_pos hhalfPositive]
    linarith
  let carrier : LogarithmicCircleCarrier :=
    { center := ac
      radius := radius / 2
      radius_ne_zero := hhalfNe
      residue := (rho : ℂ)
      regularCoefficient := criticalRegularCoefficient ac
      regularPrimitive := primitive
      regularPrimitive_derivative := fun theta =>
        hprimitive _ (hcircleMem theta) }
  have hcoefficient : ∀ theta : ℝ,
      carrier.coefficient
          (circleMap carrier.center carrier.radius theta) =
        criticalCoefficient
          (circleMap carrier.center carrier.radius theta) := by
    intro theta
    have hza :
        circleMap ac (radius / 2) theta - ac ≠ 0 := by
      exact sub_ne_zero.mpr (circleMap_ne_center hhalfNe)
    have hBz :
        (reducedDenominatorPolynomial ac).eval
            (circleMap ac (radius / 2) theta) ≠ 0 :=
      (hball _ (hcircleMem theta)).2
    have hdecomp := critical_coefficient_decomposition
      hrootC hza hBa hBz
    change (rho : ℂ) /
          (circleMap ac (radius / 2) theta - ac) +
        criticalRegularCoefficient ac
          (circleMap ac (radius / 2) theta) =
      criticalCoefficient (circleMap ac (radius / 2) theta)
    rw [← criticalResidue_real_root hroot hrho]
    exact hdecomp.symm
  have hmultiplier : carrier.multiplier =
      FormalComplexMonodromyNonTorsion.monodromyMultiplier rho := by
    simp [carrier, LogarithmicCircleCarrier.multiplier,
      FormalComplexMonodromyNonTorsion.monodromyMultiplier]
  have hcarrierNontorsion : ∀ N : ℕ, 0 < N →
      carrier.multiplier ^ N ≠ 1 := by
    intro N hN
    rw [hmultiplier]
    exact hnontorsion N hN
  exact ⟨{
    pole := a
    residue := rho
    pole_mem := ha
    pole_root := hroot
    residue_binding := hrho
    residue_irrational := hirrational
    carrier := carrier
    center_binding := rfl
    residue_carrier_binding := rfl
    coefficient_on_circle := hcoefficient
    multiplier_binding := hmultiplier
    multiplier_non_torsion := hcarrierNontorsion }⟩

/-- Every nonzero initial value acquires an explicit critical-differential
continuation with an injective natural endpoint orbit. -/
theorem CriticalLoopRealization.explicit_critical_orbit
    (realization : CriticalLoopRealization)
    (initial : ℂ) (hinitial : initial ≠ 0) :
    (∀ theta : ℝ,
      HasDerivAt (realization.carrier.continuedValue initial)
        (criticalCoefficient
            (circleMap realization.carrier.center
              realization.carrier.radius theta) *
          (circleMap 0 realization.carrier.radius theta * I) *
          realization.carrier.continuedValue initial theta)
        theta) ∧
    (∀ N : ℕ,
      realization.carrier.continuedValue initial
          ((N : ℝ) * (2 * Real.pi)) =
        initial *
          FormalComplexMonodromyNonTorsion.monodromyMultiplier
            realization.residue ^ N) ∧
    Function.Injective
      (fun N : ℕ => realization.carrier.continuedValue initial
        ((N : ℝ) * (2 * Real.pi))) := by
  constructor
  · intro theta
    have h := realization.carrier.continuedValue_hasDerivAt initial theta
    rw [realization.coefficient_on_circle theta] at h
    exact h
  constructor
  · intro N
    rw [realization.carrier.continuedValue_nat_turns initial N,
      realization.multiplier_binding]
  · exact realization.carrier.endpoint_orbit_injective initial hinitial
      realization.multiplier_non_torsion

/-- Aggregated critical scalar-holonomy loop certificate. -/
theorem critical_holonomy_loop_terminal_certificate :
    ∃ realization : CriticalLoopRealization,
      ∀ initial : ℂ, initial ≠ 0 →
        (∀ theta : ℝ,
          HasDerivAt (realization.carrier.continuedValue initial)
            (criticalCoefficient
                (circleMap realization.carrier.center
                  realization.carrier.radius theta) *
              (circleMap 0 realization.carrier.radius theta * I) *
              realization.carrier.continuedValue initial theta)
            theta) ∧
        (∀ N : ℕ,
          realization.carrier.continuedValue initial
              ((N : ℝ) * (2 * Real.pi)) =
            initial *
              FormalComplexMonodromyNonTorsion.monodromyMultiplier
                realization.residue ^ N) ∧
        Function.Injective
          (fun N : ℕ => realization.carrier.continuedValue initial
            ((N : ℝ) * (2 * Real.pi))) := by
  obtain ⟨realization⟩ := exists_criticalLoopRealization
  exact ⟨realization, realization.explicit_critical_orbit⟩

/-- The original critical algebraic connection is the rational differential
whose explicit scalar continuations have the injective endpoint orbit above. -/
theorem critical_connection_holonomy_loop_terminal_certificate :
    FormalCriticalConnectionRationalization.connectionLogarithmicDifferential =
        FormalCriticalConnectionRationalization.explicitRationalDifferential ∧
      ∃ realization : CriticalLoopRealization,
        ∀ initial : ℂ, initial ≠ 0 →
          (∀ theta : ℝ,
            HasDerivAt (realization.carrier.continuedValue initial)
              (criticalCoefficient
                  (circleMap realization.carrier.center
                    realization.carrier.radius theta) *
                (circleMap 0 realization.carrier.radius theta * I) *
                realization.carrier.continuedValue initial theta)
              theta) ∧
          (∀ N : ℕ,
            realization.carrier.continuedValue initial
                ((N : ℝ) * (2 * Real.pi)) =
              initial *
                FormalComplexMonodromyNonTorsion.monodromyMultiplier
                  realization.residue ^ N) ∧
          Function.Injective
            (fun N : ℕ => realization.carrier.continuedValue initial
              ((N : ℝ) * (2 * Real.pi))) := by
  exact ⟨FormalCriticalConnectionRationalization.critical_connection_rational_differential_identity,
    critical_holonomy_loop_terminal_certificate⟩

end FormalCriticalHolonomyLoop
