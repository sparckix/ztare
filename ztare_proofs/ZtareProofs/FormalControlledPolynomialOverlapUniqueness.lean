import Mathlib.Analysis.Normed.Group.Bounded
import Mathlib.Analysis.ODE.Gronwall
import Mathlib.Topology.Order.IntermediateValue
import Mathlib.Tactic
import ZtareProofs.FormalBoundedControlledPolynomialEndpoint

/-!
# Complete overlap uniqueness for controlled polynomial trajectories

Two complex trajectories satisfying the same bounded-driver polynomial ODE
and agreeing once agree on their complete preconnected real time domain.
For each target time, compactness of the segment from the anchor constructs a
common state ball.  A coefficient bound on the derivative polynomial gives a
Lipschitz constant there, and the correctly oriented Gronwall theorem gives
equality at the target.

No state bound, Lipschitz witness, solution-uniqueness law, analyticity
premise, or preselected compact interval is supplied.
-/

namespace FormalControlledPolynomialOverlapUniqueness

open Metric Polynomial Set
open scoped NNReal

open FormalBoundedControlledPolynomialEndpoint

/-- The bounded driver scales the explicit derivative-polynomial Lipschitz
constant on every closed state ball. -/
theorem field_lipschitzOn_closedBall
    (p : ℂ[X]) {driver : ℝ → ℂ} (driverBound radius : ℝ≥0)
    (hdriverBound : ∀ t, ‖driver t‖₊ ≤ driverBound) (t : ℝ) :
    LipschitzOnWith
      (driverBound * polynomialNNNormBound p.derivative radius)
      (fun z : ℂ ↦ driver t * p.eval z)
      (closedBall 0 (radius : ℝ)) := by
  have hpolynomial : LipschitzOnWith
      (polynomialNNNormBound p.derivative radius)
      (fun z : ℂ ↦ p.eval z) (closedBall 0 (radius : ℝ)) := by
    apply (convex_closedBall (0 : ℂ) (radius : ℝ)).lipschitzOnWith_of_nnnorm_deriv_le
    · intro z hz
      exact (p.hasDerivAt z).differentiableAt
    · intro z hz
      rw [(p.hasDerivAt z).deriv]
      exact eval_nnnorm_le_polynomialNNNormBound p.derivative z radius
        (by exact_mod_cast (mem_closedBall_zero_iff.mp hz))
  have hscaled :=
    (lipschitzWith_smul (driver t)).comp_lipschitzOnWith hpolynomial
  have hconstant :
      ‖driver t‖₊ * polynomialNNNormBound p.derivative radius ≤
        driverBound * polynomialNNNormBound p.derivative radius :=
    mul_le_mul_right' (hdriverBound t)
      (polynomialNNNormBound p.derivative radius)
  simpa only [Function.comp_apply, smul_eq_mul] using
    hscaled.weaken hconstant

/-- Two bounded-driver controlled-polynomial trajectories agreeing at one
point agree on their complete preconnected common time domain. -/
theorem eqOn_of_same_controlled_polynomial_ode
    (p : ℂ[X]) {driver : ℝ → ℂ} (driverBound : ℝ≥0)
    (hdriverBound : ∀ t, ‖driver t‖₊ ≤ driverBound)
    {domain : Set ℝ} {left right : ℝ → ℂ} {anchor : ℝ}
    (hpreconnected : IsPreconnected domain)
    (hanchor : anchor ∈ domain)
    (hleftODE : ∀ t ∈ domain,
      HasDerivAt left (driver t * p.eval (left t)) t)
    (hrightODE : ∀ t ∈ domain,
      HasDerivAt right (driver t * p.eval (right t)) t)
    (hinitial : left anchor = right anchor) :
    EqOn left right domain := by
  intro target htarget
  have hsegment : uIcc anchor target ⊆ domain :=
    hpreconnected.ordConnected.uIcc_subset hanchor htarget
  have hleftContinuous : ContinuousOn left (uIcc anchor target) := by
    intro t ht
    exact (hleftODE t (hsegment ht)).continuousAt.continuousWithinAt
  have hrightContinuous : ContinuousOn right (uIcc anchor target) := by
    intro t ht
    exact (hrightODE t (hsegment ht)).continuousAt.continuousWithinAt
  obtain ⟨leftBound, hleftBound⟩ :=
    isCompact_uIcc.exists_bound_of_continuousOn hleftContinuous
  obtain ⟨rightBound, hrightBound⟩ :=
    isCompact_uIcc.exists_bound_of_continuousOn hrightContinuous
  let stateRadiusReal : ℝ := max (max leftBound rightBound) 0
  let stateRadius : ℝ≥0 :=
    ⟨stateRadiusReal, le_max_right (max leftBound rightBound) 0⟩
  have hleftState : ∀ t ∈ uIcc anchor target,
      left t ∈ closedBall (0 : ℂ) (stateRadius : ℝ) := by
    intro t ht
    rw [mem_closedBall_zero_iff]
    change ‖left t‖ ≤ stateRadiusReal
    exact (hleftBound t ht).trans
      ((le_max_left leftBound rightBound).trans
        (le_max_left (max leftBound rightBound) 0))
  have hrightState : ∀ t ∈ uIcc anchor target,
      right t ∈ closedBall (0 : ℂ) (stateRadius : ℝ) := by
    intro t ht
    rw [mem_closedBall_zero_iff]
    change ‖right t‖ ≤ stateRadiusReal
    exact (hrightBound t ht).trans
      ((le_max_right leftBound rightBound).trans
        (le_max_left (max leftBound rightBound) 0))
  rcases le_total anchor target with hforward | hbackward
  · have hleftContinuousIcc : ContinuousOn left (Icc anchor target) := by
      simpa only [uIcc_of_le hforward] using hleftContinuous
    have hrightContinuousIcc : ContinuousOn right (Icc anchor target) := by
      simpa only [uIcc_of_le hforward] using hrightContinuous
    have heq := ODE_solution_unique_of_mem_Icc_right
      (K := driverBound * polynomialNNNormBound p.derivative stateRadius)
      (v := fun t : ℝ ↦ fun z : ℂ ↦ driver t * p.eval z)
      (s := fun _ : ℝ ↦ closedBall (0 : ℂ) (stateRadius : ℝ))
      (a := anchor) (b := target) (f := left) (g := right)
      (fun t ht ↦ field_lipschitzOn_closedBall p driverBound stateRadius
        hdriverBound t)
      hleftContinuousIcc
      (fun t ht ↦
        (hleftODE t (hsegment (by
          rw [uIcc_of_le hforward]
          exact Ico_subset_Icc_self ht))).hasDerivWithinAt)
      (fun t ht ↦ hleftState t (by
        rw [uIcc_of_le hforward]
        exact Ico_subset_Icc_self ht))
      hrightContinuousIcc
      (fun t ht ↦
        (hrightODE t (hsegment (by
          rw [uIcc_of_le hforward]
          exact Ico_subset_Icc_self ht))).hasDerivWithinAt)
      (fun t ht ↦ hrightState t (by
        rw [uIcc_of_le hforward]
        exact Ico_subset_Icc_self ht))
      hinitial
    exact heq ⟨hforward, le_rfl⟩
  · have hleftContinuousIcc : ContinuousOn left (Icc target anchor) := by
      simpa only [uIcc_of_ge hbackward] using hleftContinuous
    have hrightContinuousIcc : ContinuousOn right (Icc target anchor) := by
      simpa only [uIcc_of_ge hbackward] using hrightContinuous
    have heq := ODE_solution_unique_of_mem_Icc_left
      (K := driverBound * polynomialNNNormBound p.derivative stateRadius)
      (v := fun t : ℝ ↦ fun z : ℂ ↦ driver t * p.eval z)
      (s := fun _ : ℝ ↦ closedBall (0 : ℂ) (stateRadius : ℝ))
      (a := target) (b := anchor) (f := left) (g := right)
      (fun t ht ↦ field_lipschitzOn_closedBall p driverBound stateRadius
        hdriverBound t)
      hleftContinuousIcc
      (fun t ht ↦
        (hleftODE t (hsegment (by
          rw [uIcc_of_ge hbackward]
          exact Ioc_subset_Icc_self ht))).hasDerivWithinAt)
      (fun t ht ↦ hleftState t (by
        rw [uIcc_of_ge hbackward]
        exact Ioc_subset_Icc_self ht))
      hrightContinuousIcc
      (fun t ht ↦
        (hrightODE t (hsegment (by
          rw [uIcc_of_ge hbackward]
          exact Ioc_subset_Icc_self ht))).hasDerivWithinAt)
      (fun t ht ↦ hrightState t (by
        rw [uIcc_of_ge hbackward]
        exact Ioc_subset_Icc_self ht))
      hinitial
    exact heq ⟨le_rfl, hbackward⟩

/-- Aggregated complete-overlap uniqueness terminal. -/
theorem controlled_polynomial_overlap_uniqueness_terminal_certificate :
    ∀ (p : ℂ[X]) (driver : ℝ → ℂ) (driverBound : ℝ≥0),
      (∀ t, ‖driver t‖₊ ≤ driverBound) →
      ∀ (domain : Set ℝ) (left right : ℝ → ℂ) (anchor : ℝ),
        IsPreconnected domain →
        anchor ∈ domain →
        (∀ t ∈ domain,
          HasDerivAt left (driver t * p.eval (left t)) t) →
        (∀ t ∈ domain,
          HasDerivAt right (driver t * p.eval (right t)) t) →
        left anchor = right anchor →
        EqOn left right domain := by
  intro p driver driverBound hdriverBound domain left right anchor
    hpreconnected hanchor hleftODE hrightODE hinitial
  exact eqOn_of_same_controlled_polynomial_ode p driverBound hdriverBound
    hpreconnected hanchor hleftODE hrightODE hinitial

end FormalControlledPolynomialOverlapUniqueness
