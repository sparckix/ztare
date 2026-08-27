import Mathlib.Analysis.Calculus.IteratedDeriv.FaaDiBruno
import Mathlib.Tactic
import ZtareProofs.FormalAnalyticPolynomialTimeTaylor
import ZtareProofs.FormalAnalyticTwoJuliaAbelCollision
import ZtareProofs.FormalRamifiedCubicCollisionExclusion

/-!
# Analytic assembly of the critical ramified cubic collision

The exact polynomial infinity-collision order, critical ramification balance,
canonical analytic/formal time-coordinate binding, and the two-Julia Abel
identity jointly exclude distinct normalized generators.  The cubic
cancellation on the finite side is a direct third-order Faà di Bruno
calculation and allows arbitrary analytic finite Abel coordinates.
-/

namespace FormalAnalyticRamifiedCubicCollision

open Filter Polynomial PowerSeries
open scoped Topology

open FormalAnalyticPolynomialTimeTaylor
open FormalAnalyticTaylorAlgebra
open FormalAnalyticTwoJuliaAbelCollision
open FormalPolynomialFlowAtInfinity
open FormalPolynomialInfinityTimeCoordinate
open FormalRamifiedCubicCollisionExclusion

/-- An analytic outer coordinate composed with a critical inner germ having
zero first and third derivatives also has zero third derivative. -/
theorem iteratedDeriv_three_comp_eq_zero_of_critical_jets
    {outer inner : ℂ → ℂ} {center innerCenter : ℂ}
    (houter : AnalyticAt ℂ outer innerCenter)
    (hinner : AnalyticAt ℂ inner center)
    (hinnerCenter : inner center = innerCenter)
    (hlinear : deriv inner center = 0)
    (hcubic : iteratedDeriv 3 inner center = 0) :
    iteratedDeriv 3 (outer ∘ inner) center = 0 := by
  have houterAtInner : ContDiffAt ℂ 3 outer (inner center) := by
    simpa only [hinnerCenter] using houter.contDiffAt
  rw [iteratedDeriv_comp_three houterAtInner hinner.contDiffAt,
    hlinear, hcubic]
  ring

/-- The finite Abel-coordinate difference of two critical inner germs has
zero cubic Taylor coefficient. -/
theorem coeff_three_finite_collision_eq_zero
    {source target sourceCoordinate targetCoordinate : ℂ → ℂ}
    {center sourceCenter targetCenter : ℂ}
    (hsourceCoordinate : AnalyticAt ℂ sourceCoordinate sourceCenter)
    (htargetCoordinate : AnalyticAt ℂ targetCoordinate targetCenter)
    (hsource : AnalyticAt ℂ source center)
    (htarget : AnalyticAt ℂ target center)
    (hsourceCenter : source center = sourceCenter)
    (htargetCenter : target center = targetCenter)
    (hsourceLinear : deriv source center = 0)
    (htargetLinear : deriv target center = 0)
    (hsourceCubic : iteratedDeriv 3 source center = 0)
    (htargetCubic : iteratedDeriv 3 target center = 0) :
    PowerSeries.coeff 3
      (taylorPowerSeries
        (fun t ↦ targetCoordinate (target t) -
          sourceCoordinate (source t)) center) = 0 := by
  have hsourceComp := iteratedDeriv_three_comp_eq_zero_of_critical_jets
    hsourceCoordinate hsource hsourceCenter hsourceLinear hsourceCubic
  have htargetComp := iteratedDeriv_three_comp_eq_zero_of_critical_jets
    htargetCoordinate htarget htargetCenter htargetLinear htargetCubic
  change PowerSeries.coeff 3
    (taylorPowerSeries
      ((targetCoordinate ∘ target) - (sourceCoordinate ∘ source)) center) = 0
  rw [coeff_taylorPowerSeries,
    iteratedDeriv_sub
      (htargetCoordinate.comp_of_eq htarget htargetCenter).contDiffAt
      (hsourceCoordinate.comp_of_eq hsource hsourceCenter).contDiffAt,
    htargetComp, hsourceComp]
  norm_num

/-- On a two-Julia carrier with critical order-two input/output jets and the
critical ramification balance, distinct normalized monic tangent generators
would force a nonzero and a zero cubic coefficient simultaneously. -/
theorem normalized_generators_equal_of_critical_balance
    (carrier : TwoJuliaAbelCarrier)
    (degree ramification : ℕ)
    (hfirstMonic : carrier.firstGenerator.IsMonicOfDegree degree)
    (hsecondMonic : carrier.secondGenerator.IsMonicOfDegree degree)
    (hfirstConstant : carrier.firstGenerator.coeff 0 = 0)
    (hsecondConstant : carrier.secondGenerator.coeff 0 = 0)
    (hfirstLinear : carrier.firstGenerator.coeff 1 = 0)
    (hsecondLinear : carrier.secondGenerator.coeff 1 = 0)
    (hdegree : 2 ≤ degree)
    (hbalance : ramification * (degree - 1) = 2)
    (hreciprocalOrder :
      analyticOrderAt carrier.reciprocal carrier.center =
        (ramification : ℕ))
    (hfirstInfinityDerivative : ∀ᶠ z in 𝓝 0,
      HasDerivAt carrier.firstInfinityTime
        (reciprocalTimeIntegrand carrier.firstGenerator degree z) z)
    (hsecondInfinityDerivative : ∀ᶠ z in 𝓝 0,
      HasDerivAt carrier.secondInfinityTime
        (reciprocalTimeIntegrand carrier.secondGenerator degree z) z)
    (hsourceLinearJet : deriv carrier.source carrier.center = 0)
    (htargetLinearJet : deriv carrier.target carrier.center = 0)
    (hsourceCubicJet :
      iteratedDeriv 3 carrier.source carrier.center = 0)
    (htargetCubicJet :
      iteratedDeriv 3 carrier.target carrier.center = 0) :
    carrier.firstGenerator = carrier.secondGenerator := by
  rcases monic_tangent_time_coordinate_alternative hdegree
      hfirstMonic hsecondMonic hfirstConstant hsecondConstant
      hfirstLinear hsecondLinear with hgenerators | hcollision
  · exact hgenerators
  · obtain ⟨collisionDegree, hcollisionTwo, hcollisionLt,
        hcollisionOrder⟩ := hcollision
    obtain ⟨hramification, hdegreeThree, hcollisionDegree,
        hcollisionOrderNat⟩ :=
      critical_balance_nonproportional_collision_unique
        ramification degree collisionDegree hdegree hcollisionTwo
        hcollisionLt hbalance
    let infinityCollision : ℂ → ℂ := fun z ↦
      carrier.secondInfinityTime z - carrier.firstInfinityTime z
    have hinfinityCollisionAnalytic :
        AnalyticAt ℂ infinityCollision 0 := by
      exact carrier.secondInfinity_analytic.sub
        carrier.firstInfinity_analytic
    have hinfinityCollisionTaylor :=
      taylorPowerSeries_infinityTime_collision
        carrier.firstGenerator carrier.secondGenerator degree
        hfirstMonic hsecondMonic hdegree
        carrier.firstInfinity_analytic carrier.secondInfinity_analytic
        carrier.firstInfinity_zero carrier.secondInfinity_zero
        hfirstInfinityDerivative hsecondInfinityDerivative
    have hinfinityCollisionTaylorOrder :
        PowerSeries.order
          (taylorPowerSeries infinityCollision 0) = ((3 : ℕ) : ℕ∞) := by
      rw [hinfinityCollisionTaylor, hcollisionOrder]
      rw [hcollisionOrderNat]
    have hinfinityCollisionOrder :
        analyticOrderAt infinityCollision 0 = ((3 : ℕ) : ℕ∞) := by
      rw [← order_taylorPowerSeries_eq_analyticOrderAt
        hinfinityCollisionAnalytic]
      exact hinfinityCollisionTaylorOrder
    let pulledCollision : ℂ → ℂ :=
      infinityCollision ∘ carrier.reciprocal
    have hpulledAnalytic : AnalyticAt ℂ pulledCollision carrier.center := by
      exact hinfinityCollisionAnalytic.comp_of_eq
        carrier.reciprocal_analytic carrier.reciprocal_zero
    have hinfinityCollisionAtReciprocalCenter :
        AnalyticAt ℂ infinityCollision (carrier.reciprocal carrier.center) := by
      simpa only [carrier.reciprocal_zero] using
        hinfinityCollisionAnalytic
    have hpulledOrderRaw :=
      hinfinityCollisionAtReciprocalCenter.analyticOrderAt_comp
        carrier.reciprocal_analytic
    have hpulledOrder :
        analyticOrderAt pulledCollision carrier.center = ((3 : ℕ) : ℕ∞) := by
      simpa only [pulledCollision, carrier.reciprocal_zero, sub_zero,
        hinfinityCollisionOrder, hreciprocalOrder, hramification,
        ENat.coe_one, mul_one] using hpulledOrderRaw
    have hpulledTaylorOrder :
        PowerSeries.order
          (taylorPowerSeries pulledCollision carrier.center) =
            ((3 : ℕ) : ℕ∞) := by
      rw [order_taylorPowerSeries_eq_analyticOrderAt hpulledAnalytic]
      exact hpulledOrder
    have hpulledCubic :
        PowerSeries.coeff 3
          (taylorPowerSeries pulledCollision carrier.center) ≠ 0 :=
      (PowerSeries.order_eq_nat.mp hpulledTaylorOrder).1
    let finiteCollision : ℂ → ℂ := fun t ↦
      carrier.secondFiniteTime (carrier.target t) -
        carrier.firstFiniteTime (carrier.source t)
    have hfiniteCollisionAnalytic :
        AnalyticAt ℂ finiteCollision carrier.center := by
      exact (carrier.secondFinite_analytic.comp_of_eq
        carrier.target_analytic carrier.target_center).sub
          (carrier.firstFinite_analytic.comp_of_eq
            carrier.source_analytic carrier.source_center)
    have habel : pulledCollision =ᶠ[𝓝 carrier.center]
        finiteCollision := by
      simpa only [pulledCollision, infinityCollision, finiteCollision,
        Function.comp_apply] using carrier.centered_abel_collision
    have htaylorEquality :
        taylorPowerSeries pulledCollision carrier.center =
          taylorPowerSeries finiteCollision carrier.center :=
      taylorPowerSeries_eq_of_eventuallyEq hpulledAnalytic
        hfiniteCollisionAnalytic habel
    have hfiniteCubic :
        PowerSeries.coeff 3
          (taylorPowerSeries finiteCollision carrier.center) = 0 := by
      simpa only [finiteCollision] using
        coeff_three_finite_collision_eq_zero
          carrier.firstFinite_analytic carrier.secondFinite_analytic
          carrier.source_analytic carrier.target_analytic
          carrier.source_center carrier.target_center
          hsourceLinearJet htargetLinearJet hsourceCubicJet htargetCubicJet
    apply False.elim
    apply hpulledCubic
    rw [htaylorEquality, hfiniteCubic]

/-- Aggregated nonproportional critical-branch exclusion. -/
theorem analytic_ramified_cubic_collision_terminal_certificate :
    ∀ (carrier : TwoJuliaAbelCarrier)
      (degree ramification : ℕ),
      carrier.firstGenerator.IsMonicOfDegree degree →
      carrier.secondGenerator.IsMonicOfDegree degree →
      carrier.firstGenerator.coeff 0 = 0 →
      carrier.secondGenerator.coeff 0 = 0 →
      carrier.firstGenerator.coeff 1 = 0 →
      carrier.secondGenerator.coeff 1 = 0 →
      2 ≤ degree →
      ramification * (degree - 1) = 2 →
      analyticOrderAt carrier.reciprocal carrier.center =
        (ramification : ℕ) →
      (∀ᶠ z in 𝓝 0,
        HasDerivAt carrier.firstInfinityTime
          (reciprocalTimeIntegrand carrier.firstGenerator degree z) z) →
      (∀ᶠ z in 𝓝 0,
        HasDerivAt carrier.secondInfinityTime
          (reciprocalTimeIntegrand carrier.secondGenerator degree z) z) →
      deriv carrier.source carrier.center = 0 →
      deriv carrier.target carrier.center = 0 →
      iteratedDeriv 3 carrier.source carrier.center = 0 →
      iteratedDeriv 3 carrier.target carrier.center = 0 →
      carrier.firstGenerator = carrier.secondGenerator := by
  intro carrier degree ramification hfirstMonic hsecondMonic
    hfirstConstant hsecondConstant hfirstLinear hsecondLinear hdegree
    hbalance hreciprocalOrder hfirstInfinityDerivative
    hsecondInfinityDerivative hsourceLinearJet htargetLinearJet
    hsourceCubicJet htargetCubicJet
  exact normalized_generators_equal_of_critical_balance carrier
    degree ramification hfirstMonic hsecondMonic hfirstConstant
    hsecondConstant hfirstLinear hsecondLinear hdegree hbalance
    hreciprocalOrder hfirstInfinityDerivative hsecondInfinityDerivative
    hsourceLinearJet htargetLinearJet hsourceCubicJet htargetCubicJet

end FormalAnalyticRamifiedCubicCollision
