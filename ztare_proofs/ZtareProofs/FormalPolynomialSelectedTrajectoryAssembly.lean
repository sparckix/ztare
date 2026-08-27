import Mathlib.Topology.Separation.Hausdorff
import ZtareProofs.FormalPolynomialTimeSeparation
import ZtareProofs.FormalSelectedRamifiedInverse

/-!
# Assembly of polynomial time separation with a selected ramified inverse

Time separation holds on the finite punctured trajectory domain.  The selected
ramified germ is centered at the reciprocal-infinity boundary time.  This file
uses continuity at that center to identify the separated constant there and
then invokes the selected inverse-germ kernel.
-/

namespace FormalPolynomialSelectedTrajectoryAssembly

open Filter Polynomial Set
open scoped Topology

open FormalPolynomialInfinityTimeCoordinate
open FormalPolynomialTimeSeparation
open FormalSelectedRamifiedInverse

/-- The punctured finite-time separation and the centered ramified inverse
assemble without assuming the value of the separated constant at infinity. -/
theorem selected_trajectory_assembly_terminal_certificate
    (p : ℂ[X]) (degree : ℕ)
    {domain : Set ℂ}
    {timeCoordinate reciprocalTrajectory coordinate inverseCoordinate :
      ℂ → ℂ}
    {anchor infinityTime unit : ℂ} {order : ℕ}
    (hopen : IsOpen domain)
    (hpreconnected : IsPreconnected domain)
    (hanchor : anchor ∈ domain)
    (htimeDerivative : ∀ t ∈ domain, HasDerivAt timeCoordinate
      (reciprocalTimeIntegrand p degree (reciprocalTrajectory t))
      (reciprocalTrajectory t))
    (htrajectoryDerivative : ∀ t ∈ domain,
      HasDerivAt reciprocalTrajectory
        (reciprocalVectorField p degree (reciprocalTrajectory t)) t)
    (htrajectoryNonzero : ∀ t ∈ domain,
      reciprocalTrajectory t ≠ 0)
    (hreverseNonzero : ∀ t ∈ domain,
      p.reverse.eval (reciprocalTrajectory t) ≠ 0)
    (hpositive : order ≠ 0)
    (hunit : unit ≠ 0)
    (htimeAnalytic : AnalyticAt ℂ timeCoordinate 0)
    (htimeZero : timeCoordinate 0 = 0)
    (htrajectoryInfinity : reciprocalTrajectory infinityTime = 0)
    (hcoordinateAnalytic : AnalyticAt ℂ coordinate 0)
    (hcoordinateZero : coordinate 0 = 0)
    (hcoordinateDerivative : deriv coordinate 0 = 1)
    (hnormal : timeCoordinate =ᶠ[𝓝 0]
      fun z ↦ unit * coordinate z ^ order)
    (hselectedAnalytic : AnalyticAt ℂ
      (fun w ↦ reciprocalTrajectory
        (infinityTime + unit * w ^ order)) 0)
    (hselectedDerivative : deriv
      (fun w ↦ reciprocalTrajectory
        (infinityTime + unit * w ^ order)) 0 = 1)
    (hinverseAnalytic : AnalyticAt ℂ inverseCoordinate 0)
    (hinverseZero : inverseCoordinate 0 = 0)
    (hrightInverse : ∀ᶠ w in 𝓝 0,
      coordinate (inverseCoordinate w) = w)
    (hreparamMapsPunctured : ∀ᶠ w in 𝓝[≠] 0,
      infinityTime + unit * w ^ order ∈ domain) :
    (fun w ↦ reciprocalTrajectory
      (infinityTime + unit * w ^ order)) =ᶠ[𝓝 0]
        inverseCoordinate := by
  let reparam : ℂ → ℂ :=
    fun w ↦ infinityTime + unit * w ^ order
  let selected : ℂ → ℂ :=
    fun w ↦ reciprocalTrajectory (reparam w)
  let separatedAlongSelected : ℂ → ℂ :=
    fun w ↦ timeCoordinate (selected w) - reparam w
  let separatedConstant : ℂ :=
    timeCoordinate (reciprocalTrajectory anchor) - anchor
  have hselectedZero : selected 0 = 0 := by
    simp [selected, reparam, hpositive, htrajectoryInfinity]
  have hseparatedOnDomain := separatedTime_eqOn p degree
    hopen hpreconnected hanchor htimeDerivative htrajectoryDerivative
      htrajectoryNonzero hreverseNonzero
  have hpuncturedConstant :
      separatedAlongSelected =ᶠ[𝓝[≠] 0]
        fun _ ↦ separatedConstant := by
    filter_upwards [hreparamMapsPunctured] with w hw
    exact hseparatedOnDomain (reparam w) hw
  have hselectedAnalytic' : AnalyticAt ℂ selected 0 := by
    simpa only [selected, reparam] using hselectedAnalytic
  have htimeSelectedAnalytic :
      AnalyticAt ℂ (timeCoordinate ∘ selected) 0 :=
    htimeAnalytic.comp_of_eq hselectedAnalytic' hselectedZero
  have hreparamAnalytic : AnalyticAt ℂ reparam 0 := by
    dsimp only [reparam]
    fun_prop
  have hseparatedAnalytic :
      AnalyticAt ℂ separatedAlongSelected 0 := by
    simpa only [separatedAlongSelected, Function.comp_apply] using
      htimeSelectedAnalytic.sub hreparamAnalytic
  have hfullConstant :
      separatedAlongSelected =ᶠ[𝓝 0]
        fun _ ↦ separatedConstant := by
    exact (ContinuousAt.eventuallyEq_nhds_iff_eventuallyEq_nhdsNE
      hseparatedAnalytic.continuousAt continuousAt_const).mp
      hpuncturedConstant
  have hinfinityConstant :
      timeCoordinate (reciprocalTrajectory infinityTime) - infinityTime =
        separatedConstant := by
    have hcenter := hfullConstant.self_of_nhds
    simpa [separatedAlongSelected, selected, reparam, hpositive] using
      hcenter
  have hcenteredSeparation : ∀ᶠ w in 𝓝 0,
      timeCoordinate
          (reciprocalTrajectory
            (infinityTime + unit * w ^ order)) -
        (infinityTime + unit * w ^ order) =
      timeCoordinate (reciprocalTrajectory infinityTime) - infinityTime := by
    filter_upwards [hfullConstant] with w hw
    calc
      timeCoordinate
            (reciprocalTrajectory
              (infinityTime + unit * w ^ order)) -
          (infinityTime + unit * w ^ order) =
        separatedAlongSelected w := by rfl
      _ = separatedConstant := hw
      _ = timeCoordinate (reciprocalTrajectory infinityTime) -
          infinityTime := hinfinityConstant.symm
  exact selected_reparam_eq_inverse_of_separatedTime hpositive hunit
    htimeZero htrajectoryInfinity hcoordinateAnalytic hcoordinateZero
    hcoordinateDerivative hnormal hselectedAnalytic hselectedDerivative
    hinverseAnalytic hinverseZero hrightInverse hcenteredSeparation

end FormalPolynomialSelectedTrajectoryAssembly
