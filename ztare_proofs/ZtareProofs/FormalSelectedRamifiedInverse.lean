import Mathlib.Algebra.Ring.GeomSum
import Mathlib.Analysis.Analytic.Order
import Mathlib.Analysis.Calculus.InverseFunctionTheorem.Analytic
import Mathlib.Tactic

/-!
# Selection of a ramified analytic inverse germ

An `n`th-power identity leaves a root-of-unity ambiguity.  Derivative-one
normalization removes it.  The resulting uniformizing coordinate identity,
together with local inverse-function uniqueness, identifies the selected
analytic germ with the constructed inverse coordinate.
-/

namespace FormalSelectedRamifiedInverse

open Filter Finset
open scoped Topology

/-- An analytic `n`th root of `zⁿ` with value zero and derivative one is the
identity germ. -/
theorem analytic_nth_root_branch_unique
    {selectedCoordinate : ℂ → ℂ} {order : ℕ}
    (hanalytic : AnalyticAt ℂ selectedCoordinate 0)
    (hzero : selectedCoordinate 0 = 0)
    (hderivative : deriv selectedCoordinate 0 = 1)
    (hpositive : order ≠ 0)
    (hpower : ∀ᶠ w in 𝓝 0,
      selectedCoordinate w ^ order = w ^ order) :
    selectedCoordinate =ᶠ[𝓝 0] fun w ↦ w := by
  have hderivativeNonzero : deriv selectedCoordinate 0 ≠ 0 := by
    simp [hderivative]
  have horder : analyticOrderAt selectedCoordinate 0 = (1 : ℕ) :=
    hanalytic.analyticOrderAt_eq_one_of_zero_deriv_ne_zero
      hzero hderivativeNonzero
  obtain ⟨unit, hunitAnalytic, _hunitNonzero, hfactor⟩ :=
    hanalytic.analyticOrderAt_eq_natCast.mp horder
  have hfactor' : selectedCoordinate =ᶠ[𝓝 0]
      fun w ↦ w * unit w := by
    filter_upwards [hfactor] with w hw
    simpa using hw
  have hproductDerivative :
      deriv (fun w : ℂ ↦ w * unit w) 0 = unit 0 := by
    simpa using
      ((hasDerivAt_id (0 : ℂ)).mul
        hunitAnalytic.differentiableAt.hasDerivAt).deriv
  have hunitZero : unit 0 = 1 := by
    calc
      unit 0 = deriv (fun w : ℂ ↦ w * unit w) 0 :=
        hproductDerivative.symm
      _ = deriv selectedCoordinate 0 :=
        (EventuallyEq.deriv_eq hfactor').symm
      _ = 1 := hderivative
  let geometricFactor : ℂ → ℂ := fun w ↦
    ∑ i ∈ Finset.range order, unit w ^ i
  have hgeometricAnalytic : AnalyticAt ℂ geometricFactor 0 := by
    dsimp only [geometricFactor]
    fun_prop
  have hgeometricZero : geometricFactor 0 = (order : ℂ) := by
    simp [geometricFactor, hunitZero]
  have horderCast : (order : ℂ) ≠ 0 := by
    exact Nat.cast_ne_zero.mpr hpositive
  have hgeometricNonzero : ∀ᶠ w in 𝓝 0,
      geometricFactor w ≠ 0 := by
    exact hgeometricAnalytic.continuousAt.eventually_ne
      (by simpa [hgeometricZero] using horderCast)
  have hunitPower : ∀ᶠ w in 𝓝 0, unit w ^ order = 1 := by
    filter_upwards [hfactor', hpower] with w hfactorw hpowerw
    by_cases hw : w = 0
    · subst w
      simp [hunitZero]
    · rw [hfactorw, mul_pow] at hpowerw
      apply mul_left_cancel₀ (pow_ne_zero order hw)
      simpa using hpowerw
  have hunitOne : ∀ᶠ w in 𝓝 0, unit w = 1 := by
    filter_upwards [hunitPower, hgeometricNonzero] with w hupower hgeom
    have hfactorPower :=
      (Commute.all (unit w) (1 : ℂ)).mul_geom_sum₂ order
    simp only [one_pow, mul_one] at hfactorPower
    have hproductZero :
        (unit w - 1) * geometricFactor w = 0 := by
      rw [hfactorPower]
      simp [hupower]
    rcases mul_eq_zero.mp hproductZero with hleft | hright
    · exact sub_eq_zero.mp hleft
    · exact (hgeom hright).elim
  filter_upwards [hfactor', hunitOne] with w hfactorw hu
  simp [hfactorw, hu]

/-- A selected analytic uniformizing germ whose coordinate has the normalized
`n`th-power identity equals any analytic local right inverse of that
coordinate. -/
theorem selected_eq_inverseCoordinate
    {coordinate selected inverseCoordinate : ℂ → ℂ} {order : ℕ}
    (hcoordinateAnalytic : AnalyticAt ℂ coordinate 0)
    (hcoordinateZero : coordinate 0 = 0)
    (hcoordinateDerivative : deriv coordinate 0 = 1)
    (hselectedAnalytic : AnalyticAt ℂ selected 0)
    (hselectedZero : selected 0 = 0)
    (hselectedDerivative : deriv selected 0 = 1)
    (hinverseAnalytic : AnalyticAt ℂ inverseCoordinate 0)
    (hinverseZero : inverseCoordinate 0 = 0)
    (hrightInverse : ∀ᶠ w in 𝓝 0,
      coordinate (inverseCoordinate w) = w)
    (hpositive : order ≠ 0)
    (hpower : ∀ᶠ w in 𝓝 0,
      coordinate (selected w) ^ order = w ^ order) :
    selected =ᶠ[𝓝 0] inverseCoordinate := by
  have hcoordinateHasDeriv : HasDerivAt coordinate 1 0 := by
    simpa [hcoordinateDerivative] using
      hcoordinateAnalytic.differentiableAt.hasDerivAt
  have hselectedHasDeriv : HasDerivAt selected 1 0 := by
    simpa [hselectedDerivative] using
      hselectedAnalytic.differentiableAt.hasDerivAt
  have hcompositionAnalytic :
      AnalyticAt ℂ (coordinate ∘ selected) 0 :=
    hcoordinateAnalytic.comp_of_eq hselectedAnalytic hselectedZero
  have hcompositionZero : (coordinate ∘ selected) 0 = 0 := by
    simp [Function.comp_apply, hselectedZero, hcoordinateZero]
  have hcompositionDerivative : deriv (coordinate ∘ selected) 0 = 1 := by
    have hcoordinateAtSelected :
        HasDerivAt coordinate 1 (selected 0) := by
      simpa [hselectedZero] using hcoordinateHasDeriv
    simpa using
      (hcoordinateAtSelected.comp 0 hselectedHasDeriv).deriv
  have hselectedCoordinate :
      coordinate ∘ selected =ᶠ[𝓝 0] fun w ↦ w := by
    apply analytic_nth_root_branch_unique hcompositionAnalytic
      hcompositionZero hcompositionDerivative hpositive
    simpa only [Function.comp_apply] using hpower
  have hstrict : HasStrictDerivAt coordinate 1 0 := by
    simpa [hcoordinateDerivative] using hcoordinateAnalytic.hasStrictDerivAt
  let localInverse := hstrict.localInverse coordinate 1 0 one_ne_zero
  have hleftInverse :
      localInverse ∘ coordinate =ᶠ[𝓝 0] fun z ↦ z := by
    simpa [localInverse, hcoordinateZero] using
      hstrict.eventually_left_inverse one_ne_zero
  have hselectedTendsto : Tendsto selected (𝓝 0) (𝓝 0) := by
    have hcontinuous := hselectedAnalytic.continuousAt
    change Tendsto selected (𝓝 0) (𝓝 (selected 0)) at hcontinuous
    simpa only [hselectedZero] using hcontinuous
  have hinverseTendsto : Tendsto inverseCoordinate (𝓝 0) (𝓝 0) := by
    have hcontinuous := hinverseAnalytic.continuousAt
    change Tendsto inverseCoordinate (𝓝 0)
      (𝓝 (inverseCoordinate 0)) at hcontinuous
    simpa only [hinverseZero] using hcontinuous
  have hleftSelected : ∀ᶠ w in 𝓝 0,
      localInverse (coordinate (selected w)) = selected w := by
    simpa only [Function.comp_apply] using
      EventuallyEq.comp_tendsto hleftInverse hselectedTendsto
  have hleftInverseCoordinate : ∀ᶠ w in 𝓝 0,
      localInverse (coordinate (inverseCoordinate w)) =
        inverseCoordinate w := by
    simpa only [Function.comp_apply] using
      EventuallyEq.comp_tendsto hleftInverse hinverseTendsto
  filter_upwards [hleftSelected, hleftInverseCoordinate,
    hselectedCoordinate, hrightInverse] with w hleftSelected hleftInverseW
      hselectedW hrightW
  calc
    selected w = localInverse (coordinate (selected w)) :=
      hleftSelected.symm
    _ = localInverse w := congrArg localInverse hselectedW
    _ = localInverse (coordinate (inverseCoordinate w)) :=
      congrArg localInverse hrightW.symm
    _ = inverseCoordinate w := hleftInverseW

/-- A separated-time identity at a reciprocal-infinity base point becomes the
exact ramified time identity after the normalized reparameterization
`t = t₀ + unit * wⁿ`. -/
theorem timeCoordinate_reparam_eq_power
    {timeCoordinate reciprocalTrajectory : ℂ → ℂ}
    {t₀ unit : ℂ} {order : ℕ}
    (htimeZero : timeCoordinate 0 = 0)
    (htrajectoryBase : reciprocalTrajectory t₀ = 0)
    (hseparated : ∀ᶠ w in 𝓝 0,
      timeCoordinate
          (reciprocalTrajectory (t₀ + unit * w ^ order)) -
        (t₀ + unit * w ^ order) =
      timeCoordinate (reciprocalTrajectory t₀) - t₀) :
    ∀ᶠ w in 𝓝 0,
      timeCoordinate
        (reciprocalTrajectory (t₀ + unit * w ^ order)) =
      unit * w ^ order := by
  filter_upwards [hseparated] with w hw
  rw [htrajectoryBase, htimeZero] at hw
  linear_combination hw

/-- The time-coordinate normal form converts an exact ramified time identity
into the normalized `n`th-power identity for the analytic coordinate. -/
theorem coordinate_power_eq_of_timeCoordinate_eq
    {timeCoordinate coordinate selected : ℂ → ℂ}
    {unit : ℂ} {order : ℕ}
    (hunit : unit ≠ 0)
    (hselectedAnalytic : AnalyticAt ℂ selected 0)
    (hselectedZero : selected 0 = 0)
    (hnormal : timeCoordinate =ᶠ[𝓝 0]
      fun z ↦ unit * coordinate z ^ order)
    (htimeSelected : ∀ᶠ w in 𝓝 0,
      timeCoordinate (selected w) = unit * w ^ order) :
    ∀ᶠ w in 𝓝 0,
      coordinate (selected w) ^ order = w ^ order := by
  have hselectedTendsto : Tendsto selected (𝓝 0) (𝓝 0) := by
    have hcontinuous := hselectedAnalytic.continuousAt
    change Tendsto selected (𝓝 0) (𝓝 (selected 0)) at hcontinuous
    simpa only [hselectedZero] using hcontinuous
  have hnormalSelected : ∀ᶠ w in 𝓝 0,
      timeCoordinate (selected w) =
        unit * coordinate (selected w) ^ order := by
    simpa only [Function.comp_apply] using
      EventuallyEq.comp_tendsto hnormal hselectedTendsto
  filter_upwards [hnormalSelected, htimeSelected] with w hnormalw htimew
  apply mul_left_cancel₀ hunit
  simpa [hnormalw] using htimew

/-- Full local branch identification from the separated reciprocal-time
identity, the analytic power normal form, and derivative-one branch data. -/
theorem selected_reparam_eq_inverse_of_separatedTime
    {timeCoordinate reciprocalTrajectory coordinate inverseCoordinate :
      ℂ → ℂ}
    {t₀ unit : ℂ} {order : ℕ}
    (hpositive : order ≠ 0)
    (hunit : unit ≠ 0)
    (htimeZero : timeCoordinate 0 = 0)
    (htrajectoryBase : reciprocalTrajectory t₀ = 0)
    (hcoordinateAnalytic : AnalyticAt ℂ coordinate 0)
    (hcoordinateZero : coordinate 0 = 0)
    (hcoordinateDerivative : deriv coordinate 0 = 1)
    (hnormal : timeCoordinate =ᶠ[𝓝 0]
      fun z ↦ unit * coordinate z ^ order)
    (hselectedAnalytic : AnalyticAt ℂ
      (fun w ↦ reciprocalTrajectory (t₀ + unit * w ^ order)) 0)
    (hselectedDerivative : deriv
      (fun w ↦ reciprocalTrajectory (t₀ + unit * w ^ order)) 0 = 1)
    (hinverseAnalytic : AnalyticAt ℂ inverseCoordinate 0)
    (hinverseZero : inverseCoordinate 0 = 0)
    (hrightInverse : ∀ᶠ w in 𝓝 0,
      coordinate (inverseCoordinate w) = w)
    (hseparated : ∀ᶠ w in 𝓝 0,
      timeCoordinate
          (reciprocalTrajectory (t₀ + unit * w ^ order)) -
        (t₀ + unit * w ^ order) =
      timeCoordinate (reciprocalTrajectory t₀) - t₀) :
    (fun w ↦ reciprocalTrajectory (t₀ + unit * w ^ order)) =ᶠ[𝓝 0]
      inverseCoordinate := by
  let selected : ℂ → ℂ :=
    fun w ↦ reciprocalTrajectory (t₀ + unit * w ^ order)
  have hselectedZero : selected 0 = 0 := by
    simp [selected, hpositive, htrajectoryBase]
  have htimeSelected : ∀ᶠ w in 𝓝 0,
      timeCoordinate (selected w) = unit * w ^ order := by
    simpa only [selected] using
      timeCoordinate_reparam_eq_power htimeZero
        htrajectoryBase hseparated
  have hpower : ∀ᶠ w in 𝓝 0,
      coordinate (selected w) ^ order = w ^ order :=
    coordinate_power_eq_of_timeCoordinate_eq hunit
      hselectedAnalytic hselectedZero hnormal htimeSelected
  exact selected_eq_inverseCoordinate hcoordinateAnalytic
    hcoordinateZero hcoordinateDerivative hselectedAnalytic
    hselectedZero hselectedDerivative hinverseAnalytic hinverseZero
    hrightInverse hpositive hpower

/-- Aggregated reusable certificate for selected ramified inverse germs. -/
theorem selected_ramified_inverse_terminal_certificate :
    (∀ (selectedCoordinate : ℂ → ℂ) (order : ℕ),
      AnalyticAt ℂ selectedCoordinate 0 →
      selectedCoordinate 0 = 0 →
      deriv selectedCoordinate 0 = 1 →
      order ≠ 0 →
      (∀ᶠ w in 𝓝 0,
        selectedCoordinate w ^ order = w ^ order) →
      selectedCoordinate =ᶠ[𝓝 0] fun w ↦ w) ∧
    (∀ (coordinate selected inverseCoordinate : ℂ → ℂ)
      (order : ℕ),
      AnalyticAt ℂ coordinate 0 →
      coordinate 0 = 0 →
      deriv coordinate 0 = 1 →
      AnalyticAt ℂ selected 0 →
      selected 0 = 0 →
      deriv selected 0 = 1 →
      AnalyticAt ℂ inverseCoordinate 0 →
      inverseCoordinate 0 = 0 →
      (∀ᶠ w in 𝓝 0,
        coordinate (inverseCoordinate w) = w) →
      order ≠ 0 →
      (∀ᶠ w in 𝓝 0,
        coordinate (selected w) ^ order = w ^ order) →
      selected =ᶠ[𝓝 0] inverseCoordinate) ∧
    (∀ (timeCoordinate reciprocalTrajectory coordinate inverseCoordinate :
        ℂ → ℂ) (t₀ unit : ℂ) (order : ℕ),
      order ≠ 0 → unit ≠ 0 → timeCoordinate 0 = 0 →
      reciprocalTrajectory t₀ = 0 →
      AnalyticAt ℂ coordinate 0 → coordinate 0 = 0 →
      deriv coordinate 0 = 1 →
      timeCoordinate =ᶠ[𝓝 0]
        (fun z ↦ unit * coordinate z ^ order) →
      AnalyticAt ℂ
        (fun w ↦ reciprocalTrajectory (t₀ + unit * w ^ order)) 0 →
      deriv (fun w ↦ reciprocalTrajectory
        (t₀ + unit * w ^ order)) 0 = 1 →
      AnalyticAt ℂ inverseCoordinate 0 → inverseCoordinate 0 = 0 →
      (∀ᶠ w in 𝓝 0, coordinate (inverseCoordinate w) = w) →
      (∀ᶠ w in 𝓝 0,
        timeCoordinate
            (reciprocalTrajectory (t₀ + unit * w ^ order)) -
          (t₀ + unit * w ^ order) =
        timeCoordinate (reciprocalTrajectory t₀) - t₀) →
      (fun w ↦ reciprocalTrajectory
        (t₀ + unit * w ^ order)) =ᶠ[𝓝 0] inverseCoordinate) := by
  constructor
  · intro selectedCoordinate order hanalytic hzero hderivative
      hpositive hpower
    exact analytic_nth_root_branch_unique hanalytic hzero hderivative
      hpositive hpower
  · constructor
    · intro coordinate selected inverseCoordinate order
        hcoordinateAnalytic hcoordinateZero hcoordinateDerivative
        hselectedAnalytic hselectedZero hselectedDerivative
        hinverseAnalytic hinverseZero hrightInverse hpositive hpower
      exact selected_eq_inverseCoordinate
        hcoordinateAnalytic hcoordinateZero hcoordinateDerivative
        hselectedAnalytic hselectedZero hselectedDerivative
        hinverseAnalytic hinverseZero hrightInverse hpositive hpower
    · intro timeCoordinate reciprocalTrajectory coordinate
        inverseCoordinate t₀ unit order hpositive hunit htimeZero
        htrajectoryBase hcoordinateAnalytic hcoordinateZero
        hcoordinateDerivative hnormal hselectedAnalytic
        hselectedDerivative hinverseAnalytic hinverseZero hrightInverse
        hseparated
      exact selected_reparam_eq_inverse_of_separatedTime hpositive hunit
        htimeZero htrajectoryBase hcoordinateAnalytic hcoordinateZero
        hcoordinateDerivative hnormal hselectedAnalytic
        hselectedDerivative hinverseAnalytic hinverseZero hrightInverse
        hseparated

end FormalSelectedRamifiedInverse
