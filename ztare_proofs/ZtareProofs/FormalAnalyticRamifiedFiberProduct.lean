import Mathlib.Analysis.Meromorphic.Order
import Mathlib.Analysis.SpecialFunctions.Complex.Analytic
import Mathlib.Tactic
import ZtareProofs.FormalAnalyticPowerNormalForm

/-!
# Ramified fiber products of pointed analytic germs

Two finite positive-order complex analytic germs admit power normal forms.
Their local fiber product is therefore the normalization of a monomial
curve.  This file constructs one uniform finite parameterization and proves
that the inverse of the lifted target displacement is meromorphic of exact
negative order.

No analytic-continuation or global branch-classification theorem is assumed.
-/

namespace FormalAnalyticRamifiedFiberProduct

open Filter
open scoped Topology

open FormalAnalyticPowerNormalForm

/-- The normalized local fiber product of two pointed analytic time germs.

The source projection has ramification degree `targetOrder`; the lifted
target displacement has order `sourceOrder`.  This parameterization need not
be minimal, but it is always finite. -/
structure AnalyticRamifiedFiberProduct
    (targetTime sourceTime : ℂ → ℂ)
    (targetCenter sourceCenter : ℂ)
    (targetOrder sourceOrder : ℕ) where
  targetUnit : ℂ
  sourceUnit : ℂ
  root : ℂ
  targetCoordinate : ℂ → ℂ
  sourceCoordinate : ℂ → ℂ
  sourceProjection : ℂ → ℂ
  liftedTarget : ℂ → ℂ
  targetUnit_ne : targetUnit ≠ 0
  sourceUnit_ne : sourceUnit ≠ 0
  root_ne : root ≠ 0
  root_power : root ^ targetOrder = sourceUnit / targetUnit
  sourceProjection_analytic : AnalyticAt ℂ sourceProjection 0
  sourceProjection_zero : sourceProjection 0 = sourceCenter
  liftedTarget_analytic : AnalyticAt ℂ liftedTarget 0
  liftedTarget_zero : liftedTarget 0 = targetCenter
  source_coordinate_projection :
    sourceCoordinate ∘ sourceProjection =ᶠ[𝓝 0]
      fun w ↦ w ^ targetOrder
  target_coordinate_lift :
    targetCoordinate ∘ liftedTarget =ᶠ[𝓝 0]
      fun w ↦ root * w ^ sourceOrder
  time_compatible :
    targetTime ∘ liftedTarget =ᶠ[𝓝 0]
      sourceTime ∘ sourceProjection
  lifted_displacement_order :
    analyticOrderAt (fun w ↦ liftedTarget w - targetCenter) 0 =
      (sourceOrder : ℕ∞)
  inverse_displacement_meromorphic :
    MeromorphicAt ((fun w ↦ liftedTarget w - targetCenter)⁻¹) 0
  inverse_displacement_order :
    meromorphicOrderAt
        ((fun w ↦ liftedTarget w - targetCenter)⁻¹) 0 =
      ((-(sourceOrder : ℤ) : ℤ) : WithTop ℤ)

/-- Two finite positive-order analytic germs have a normalized finite
ramified fiber product. -/
theorem AnalyticRamifiedFiberProduct.exists_ofPositiveOrders
    (targetTime sourceTime : ℂ → ℂ)
    (targetCenter sourceCenter : ℂ)
    (targetOrder sourceOrder : ℕ)
    (htargetAnalytic : AnalyticAt ℂ targetTime targetCenter)
    (htargetOrder :
      analyticOrderAt targetTime targetCenter = targetOrder)
    (htargetPositive : targetOrder ≠ 0)
    (hsourceAnalytic : AnalyticAt ℂ sourceTime sourceCenter)
    (hsourceOrder :
      analyticOrderAt sourceTime sourceCenter = sourceOrder)
    (hsourcePositive : sourceOrder ≠ 0) :
    Nonempty (AnalyticRamifiedFiberProduct targetTime sourceTime
      targetCenter sourceCenter targetOrder sourceOrder) := by
  obtain ⟨targetUnit, targetCoordinate, targetInverse,
      htargetUnit, htargetCoordinateAnalytic, htargetCoordinateZero,
      htargetCoordinateDerivative, htargetNormal,
      htargetInverseAnalytic, htargetInverseZero,
      htargetRightInverse⟩ :=
    analytic_power_normal_form_terminal_certificate
      targetTime targetCenter targetOrder htargetAnalytic htargetOrder
        htargetPositive
  obtain ⟨sourceUnit, sourceCoordinate, sourceInverse,
      hsourceUnit, hsourceCoordinateAnalytic, hsourceCoordinateZero,
      _hsourceCoordinateDerivative, hsourceNormal,
      hsourceInverseAnalytic, hsourceInverseZero,
      hsourceRightInverse⟩ :=
    analytic_power_normal_form_terminal_certificate
      sourceTime sourceCenter sourceOrder hsourceAnalytic hsourceOrder
        hsourcePositive
  let root : ℂ :=
    (sourceUnit / targetUnit) ^ ((targetOrder : ℂ)⁻¹)
  have hrootPower : root ^ targetOrder = sourceUnit / targetUnit := by
    exact Complex.cpow_nat_inv_pow
      (sourceUnit / targetUnit) htargetPositive
  have hratio : sourceUnit / targetUnit ≠ 0 :=
    div_ne_zero hsourceUnit htargetUnit
  have hroot : root ≠ 0 := by
    intro hzero
    apply hratio
    rw [← hrootPower, hzero]
    exact zero_pow htargetPositive
  let targetPower : ℂ → ℂ :=
    fun w ↦ root * w ^ sourceOrder
  let sourcePower : ℂ → ℂ :=
    fun w ↦ w ^ targetOrder
  have htargetPowerAnalytic : AnalyticAt ℂ targetPower 0 := by
    dsimp only [targetPower]
    fun_prop
  have hsourcePowerAnalytic : AnalyticAt ℂ sourcePower 0 := by
    dsimp only [sourcePower]
    fun_prop
  have htargetPowerZero : targetPower 0 = 0 := by
    simp [targetPower, hsourcePositive]
  have hsourcePowerZero : sourcePower 0 = 0 := by
    simp [sourcePower, htargetPositive]
  let liftedTarget : ℂ → ℂ := targetInverse ∘ targetPower
  let sourceProjection : ℂ → ℂ := sourceInverse ∘ sourcePower
  have hliftedAnalytic : AnalyticAt ℂ liftedTarget 0 := by
    exact htargetInverseAnalytic.comp_of_eq htargetPowerAnalytic
      htargetPowerZero
  have hprojectionAnalytic : AnalyticAt ℂ sourceProjection 0 := by
    exact hsourceInverseAnalytic.comp_of_eq hsourcePowerAnalytic
      hsourcePowerZero
  have hliftedZero : liftedTarget 0 = targetCenter := by
    simp only [liftedTarget, Function.comp_apply, htargetPowerZero,
      htargetInverseZero]
  have hprojectionZero : sourceProjection 0 = sourceCenter := by
    simp only [sourceProjection, Function.comp_apply, hsourcePowerZero,
      hsourceInverseZero]
  have htargetPowerTendsto : Tendsto targetPower (𝓝 0) (𝓝 0) := by
    have hcontinuous := htargetPowerAnalytic.continuousAt
    change Tendsto targetPower (𝓝 0) (𝓝 (targetPower 0)) at hcontinuous
    simpa only [htargetPowerZero] using hcontinuous
  have hsourcePowerTendsto : Tendsto sourcePower (𝓝 0) (𝓝 0) := by
    have hcontinuous := hsourcePowerAnalytic.continuousAt
    change Tendsto sourcePower (𝓝 0) (𝓝 (sourcePower 0)) at hcontinuous
    simpa only [hsourcePowerZero] using hcontinuous
  have hliftedTendsto : Tendsto liftedTarget (𝓝 0) (𝓝 targetCenter) := by
    have hcontinuous := hliftedAnalytic.continuousAt
    change Tendsto liftedTarget (𝓝 0) (𝓝 (liftedTarget 0)) at hcontinuous
    simpa only [hliftedZero] using hcontinuous
  have hprojectionTendsto :
      Tendsto sourceProjection (𝓝 0) (𝓝 sourceCenter) := by
    have hcontinuous := hprojectionAnalytic.continuousAt
    change Tendsto sourceProjection (𝓝 0)
      (𝓝 (sourceProjection 0)) at hcontinuous
    simpa only [hprojectionZero] using hcontinuous
  have htargetCoordinateLift :
      targetCoordinate ∘ liftedTarget =ᶠ[𝓝 0] targetPower := by
    simpa only [liftedTarget, Function.comp_assoc] using
      EventuallyEq.comp_tendsto htargetRightInverse htargetPowerTendsto
  have hsourceCoordinateProjection :
      sourceCoordinate ∘ sourceProjection =ᶠ[𝓝 0] sourcePower := by
    simpa only [sourceProjection, Function.comp_assoc] using
      EventuallyEq.comp_tendsto hsourceRightInverse hsourcePowerTendsto
  have htargetNormalLift : targetTime ∘ liftedTarget =ᶠ[𝓝 0]
      fun w ↦ targetUnit * targetCoordinate (liftedTarget w) ^
        targetOrder := by
    simpa only [Function.comp_apply] using
      EventuallyEq.comp_tendsto htargetNormal hliftedTendsto
  have hsourceNormalProjection : sourceTime ∘ sourceProjection =ᶠ[𝓝 0]
      fun w ↦ sourceUnit * sourceCoordinate (sourceProjection w) ^
        sourceOrder := by
    simpa only [Function.comp_apply] using
      EventuallyEq.comp_tendsto hsourceNormal hprojectionTendsto
  have hscalar : targetUnit * root ^ targetOrder = sourceUnit := by
    rw [hrootPower]
    field_simp
  have htimeCompatible : targetTime ∘ liftedTarget =ᶠ[𝓝 0]
      sourceTime ∘ sourceProjection := by
    filter_upwards [htargetNormalLift, hsourceNormalProjection,
      htargetCoordinateLift, hsourceCoordinateProjection]
      with w htarget hsource htargetCoordinate hsourceCoordinate
    rw [htarget, hsource]
    simp only [Function.comp_apply] at htargetCoordinate hsourceCoordinate
    rw [htargetCoordinate, hsourceCoordinate]
    simp only [targetPower, sourcePower, mul_pow]
    calc
      targetUnit * (root ^ targetOrder *
          (w ^ sourceOrder) ^ targetOrder) =
          (targetUnit * root ^ targetOrder) *
            (w ^ sourceOrder) ^ targetOrder := by ring
      _ = sourceUnit * (w ^ sourceOrder) ^ targetOrder := by
        rw [hscalar]
      _ = sourceUnit * w ^ (sourceOrder * targetOrder) := by
        rw [pow_mul]
      _ = sourceUnit * w ^ (targetOrder * sourceOrder) := by
        rw [Nat.mul_comm sourceOrder targetOrder]
      _ = sourceUnit * (w ^ targetOrder) ^ sourceOrder := by
        rw [pow_mul]
  have htargetInverseDerivative : deriv targetInverse 0 = 1 := by
    have htargetCoordinateHasDeriv :
        HasDerivAt targetCoordinate 1 targetCenter := by
      simpa only [htargetCoordinateDerivative] using
        htargetCoordinateAnalytic.differentiableAt.hasDerivAt
    have htargetInverseHasDeriv : HasDerivAt targetInverse
        (deriv targetInverse 0) 0 :=
      htargetInverseAnalytic.differentiableAt.hasDerivAt
    have htargetCoordinateAtInverse :
        HasDerivAt targetCoordinate 1 (targetInverse 0) := by
      simpa only [htargetInverseZero] using htargetCoordinateHasDeriv
    have hcomposition :=
      (htargetCoordinateAtInverse.comp 0 htargetInverseHasDeriv).deriv
    have hrightFunctions :
        targetCoordinate ∘ targetInverse =ᶠ[𝓝 0] fun w ↦ w := by
      simpa only [Function.comp_apply] using htargetRightInverse
    calc
      deriv targetInverse 0 = 1 * deriv targetInverse 0 := by ring
      _ = deriv (targetCoordinate ∘ targetInverse) 0 :=
        hcomposition.symm
      _ = deriv (fun w : ℂ ↦ w) 0 := hrightFunctions.deriv_eq
      _ = 1 := by simp
  let shiftedInverse : ℂ → ℂ :=
    fun u ↦ targetInverse u - targetCenter
  have hshiftedInverseAnalytic : AnalyticAt ℂ shiftedInverse 0 := by
    dsimp only [shiftedInverse]
    fun_prop
  have hshiftedInverseZero : shiftedInverse 0 = 0 := by
    simp [shiftedInverse, htargetInverseZero]
  have hshiftedInverseDerivative : deriv shiftedInverse 0 = 1 := by
    have hhas : HasDerivAt shiftedInverse 1 0 := by
      simpa only [shiftedInverse, htargetInverseDerivative] using
        htargetInverseAnalytic.differentiableAt.hasDerivAt.sub_const
          targetCenter
    exact hhas.deriv
  have hshiftedInverseOrder :
      analyticOrderAt shiftedInverse 0 = (1 : ℕ) :=
    hshiftedInverseAnalytic.analyticOrderAt_eq_one_of_zero_deriv_ne_zero
      hshiftedInverseZero (by simp [hshiftedInverseDerivative])
  have htargetPowerOrder :
      analyticOrderAt targetPower 0 = (sourceOrder : ℕ) := by
    apply htargetPowerAnalytic.analyticOrderAt_eq_natCast.mpr
    refine ⟨fun _ ↦ root, analyticAt_const, hroot, ?_⟩
    filter_upwards with w
    simp only [targetPower, sub_zero, smul_eq_mul]
    ring
  have hdisplacementIdentity :
      (fun w ↦ liftedTarget w - targetCenter) =
        shiftedInverse ∘ targetPower := by
    rfl
  have hdisplacementOrder :
      analyticOrderAt (fun w ↦ liftedTarget w - targetCenter) 0 =
        (sourceOrder : ℕ) := by
    have hshiftedAtPower :
        AnalyticAt ℂ shiftedInverse (targetPower 0) := by
      simpa only [htargetPowerZero] using hshiftedInverseAnalytic
    have htargetPowerDifferenceOrder :
        analyticOrderAt (fun w ↦ targetPower w - targetPower 0) 0 =
          (sourceOrder : ℕ) := by
      simpa only [htargetPowerZero, sub_zero] using htargetPowerOrder
    have hshiftedInverseOrderAtPower :
        analyticOrderAt shiftedInverse (targetPower 0) = (1 : ℕ) := by
      simpa only [htargetPowerZero] using hshiftedInverseOrder
    rw [hdisplacementIdentity,
      hshiftedAtPower.analyticOrderAt_comp htargetPowerAnalytic,
      hshiftedInverseOrderAtPower,
      htargetPowerDifferenceOrder]
    simp
  have hdisplacementAnalytic :
      AnalyticAt ℂ (fun w ↦ liftedTarget w - targetCenter) 0 := by
    fun_prop
  have hinverseMeromorphic :
      MeromorphicAt ((fun w ↦ liftedTarget w - targetCenter)⁻¹) 0 :=
    hdisplacementAnalytic.meromorphicAt.inv
  have hinverseOrder :
      meromorphicOrderAt
          ((fun w ↦ liftedTarget w - targetCenter)⁻¹) 0 =
        ((-(sourceOrder : ℤ) : ℤ) : WithTop ℤ) := by
    rw [meromorphicOrderAt_inv,
      hdisplacementAnalytic.meromorphicOrderAt_eq,
      hdisplacementOrder]
    rfl
  exact ⟨{
    targetUnit := targetUnit
    sourceUnit := sourceUnit
    root := root
    targetCoordinate := targetCoordinate
    sourceCoordinate := sourceCoordinate
    sourceProjection := sourceProjection
    liftedTarget := liftedTarget
    targetUnit_ne := htargetUnit
    sourceUnit_ne := hsourceUnit
    root_ne := hroot
    root_power := hrootPower
    sourceProjection_analytic := hprojectionAnalytic
    sourceProjection_zero := hprojectionZero
    liftedTarget_analytic := hliftedAnalytic
    liftedTarget_zero := hliftedZero
    source_coordinate_projection := by
      simpa only [sourcePower] using hsourceCoordinateProjection
    target_coordinate_lift := by
      simpa only [targetPower] using htargetCoordinateLift
    time_compatible := htimeCompatible
    lifted_displacement_order := hdisplacementOrder
    inverse_displacement_meromorphic := hinverseMeromorphic
    inverse_displacement_order := hinverseOrder
  }⟩

/-- Aggregated reusable certificate for analytic ramified fiber products. -/
theorem analytic_ramified_fiber_product_terminal_certificate :
    ∀ (targetTime sourceTime : ℂ → ℂ)
      (targetCenter sourceCenter : ℂ)
      (targetOrder sourceOrder : ℕ),
      AnalyticAt ℂ targetTime targetCenter →
      analyticOrderAt targetTime targetCenter = targetOrder →
      targetOrder ≠ 0 →
      AnalyticAt ℂ sourceTime sourceCenter →
      analyticOrderAt sourceTime sourceCenter = sourceOrder →
      sourceOrder ≠ 0 →
      Nonempty (AnalyticRamifiedFiberProduct targetTime sourceTime
        targetCenter sourceCenter targetOrder sourceOrder) := by
  intro targetTime sourceTime targetCenter sourceCenter
    targetOrder sourceOrder htargetAnalytic htargetOrder htargetPositive
    hsourceAnalytic hsourceOrder hsourcePositive
  exact AnalyticRamifiedFiberProduct.exists_ofPositiveOrders
    targetTime sourceTime targetCenter sourceCenter targetOrder sourceOrder
    htargetAnalytic htargetOrder htargetPositive
    hsourceAnalytic hsourceOrder hsourcePositive

end FormalAnalyticRamifiedFiberProduct
