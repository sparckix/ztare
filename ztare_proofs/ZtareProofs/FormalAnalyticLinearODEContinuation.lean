import Mathlib.Analysis.Complex.HasPrimitives
import Mathlib.Analysis.SpecialFunctions.ExpDeriv
import ZtareProofs.FormalAnalyticTaylorAlgebra

/-!
# Analytic continuation of scalar linear ODE solutions

Holomorphic scalar coefficients have normalized exponential solutions on a
disk.  Taylor transport and formal coefficient induction prove uniqueness on
connected overlaps, so local disk solutions can be glued without assuming
their compatibility.
-/

namespace FormalAnalyticLinearODEContinuation

open Filter Metric Set
open PowerSeries
open FormalAnalyticTaylorAlgebra
open FormalAnalyticTaylorTransport
open FormalPowerSeriesLinearODE
open scoped Topology

/-- A holomorphic scalar linear ODE has a solution on a disk with any
prescribed value at an anchor in that disk. -/
theorem exists_solution_on_ball
    {coefficient : ℂ → ℂ} {center anchor : ℂ} {radius : ℝ}
    (hradius : 0 < radius)
    (hanchor : anchor ∈ ball center radius)
    (hcoefficient : AnalyticOnNhd ℂ coefficient (ball center radius))
    (initial : ℂ) :
    ∃ endpoint : ℂ → ℂ,
      AnalyticOnNhd ℂ endpoint (ball center radius) ∧
      endpoint anchor = initial ∧
      (∀ z ∈ ball center radius,
        HasDerivAt endpoint (coefficient z * endpoint z) z) ∧
      (initial ≠ 0 → ∀ z ∈ ball center radius, endpoint z ≠ 0) := by
  obtain ⟨primitive, hprimitiveAnchor, hprimitive⟩ :=
    hcoefficient.differentiableOn.isExactOn_ball.with_val_at anchor 0
  let endpoint : ℂ → ℂ := fun z => initial * Complex.exp (primitive z)
  have hderivative : ∀ z ∈ ball center radius,
      HasDerivAt endpoint (coefficient z * endpoint z) z := by
    intro z hz
    have h := (hprimitive z hz).cexp.const_mul initial
    convert h using 1 <;> simp only [endpoint]
    ring
  have _hcenterDerivative := hderivative center (mem_ball_self hradius)
  have _hanchorDerivative := hderivative anchor hanchor
  have hanalytic : AnalyticOnNhd ℂ endpoint (ball center radius) := by
    apply DifferentiableOn.analyticOnNhd _ isOpen_ball
    intro z hz
    exact (hderivative z hz).differentiableAt.differentiableWithinAt
  refine ⟨endpoint, hanalytic, ?_, hderivative, ?_⟩
  · simp [endpoint, hprimitiveAnchor]
  · intro hinitial z _hz hzero
    have hexp : Complex.exp (primitive z) ≠ 0 := Complex.exp_ne_zero _
    exact hinitial (mul_eq_zero.mp hzero |>.resolve_right hexp)

/-- Two analytic solutions of the same scalar linear ODE that agree at one
point agree on their connected common domain. -/
theorem solution_eqOn_of_eq_at
    {coefficient left right : ℂ → ℂ} {domain : Set ℂ} {anchor : ℂ}
    (hopen : IsOpen domain)
    (hconnected : IsPreconnected domain)
    (hanchor : anchor ∈ domain)
    (hcoefficient : AnalyticOnNhd ℂ coefficient domain)
    (hleft : AnalyticOnNhd ℂ left domain)
    (hright : AnalyticOnNhd ℂ right domain)
    (hleftODE : ∀ z ∈ domain,
      HasDerivAt left (coefficient z * left z) z)
    (hrightODE : ∀ z ∈ domain,
      HasDerivAt right (coefficient z * right z) z)
    (hvalue : left anchor = right anchor) :
    EqOn left right domain := by
  have hleftGerm : deriv left =ᶠ[𝓝 anchor]
      fun z => coefficient z * left z := by
    filter_upwards [hopen.mem_nhds hanchor] with z hz
    exact (hleftODE z hz).deriv
  have hrightGerm : deriv right =ᶠ[𝓝 anchor]
      fun z => coefficient z * right z := by
    filter_upwards [hopen.mem_nhds hanchor] with z hz
    exact (hrightODE z hz).deriv
  have hleftFormal := taylorPowerSeries_linearODE
    (hcoefficient anchor hanchor) (hleft anchor hanchor) hleftGerm
  have hrightFormal := taylorPowerSeries_linearODE
    (hcoefficient anchor hanchor) (hright anchor hanchor) hrightGerm
  have hconstant :
      constantCoeff (taylorPowerSeries left anchor) =
        constantCoeff (taylorPowerSeries right anchor) := by
    simp [hvalue]
  have htaylor :
      taylorPowerSeries left anchor =
        taylorPowerSeries right anchor :=
    linear_ode_solution_unique hconstant hleftFormal hrightFormal
  have hleftSeries := hasFPowerSeriesAt_taylorPowerSeries
    (hleft anchor hanchor)
  have hrightSeries := hasFPowerSeriesAt_taylorPowerSeries
    (hright anchor hanchor)
  rw [← htaylor] at hrightSeries
  have hnear : left =ᶠ[𝓝 anchor] right := by
    filter_upwards [hleftSeries.eventually_hasSum_sub,
      hrightSeries.eventually_hasSum_sub] with z hzleft hzright
    exact hzleft.unique hzright
  exact hleft.eqOn_of_preconnected_of_eventuallyEq
    hright hconnected hanchor hnear

/-- Local solutions glue across the intersection of two overlapping disks. -/
theorem solution_eqOn_ball_inter_ball
    {coefficient left right : ℂ → ℂ}
    {firstCenter secondCenter anchor : ℂ}
    {firstRadius secondRadius : ℝ}
    (hanchor : anchor ∈
      ball firstCenter firstRadius ∩ ball secondCenter secondRadius)
    (hcoefficient : AnalyticOnNhd ℂ coefficient
      (ball firstCenter firstRadius ∩ ball secondCenter secondRadius))
    (hleft : AnalyticOnNhd ℂ left
      (ball firstCenter firstRadius ∩ ball secondCenter secondRadius))
    (hright : AnalyticOnNhd ℂ right
      (ball firstCenter firstRadius ∩ ball secondCenter secondRadius))
    (hleftODE : ∀ z ∈
      ball firstCenter firstRadius ∩ ball secondCenter secondRadius,
      HasDerivAt left (coefficient z * left z) z)
    (hrightODE : ∀ z ∈
      ball firstCenter firstRadius ∩ ball secondCenter secondRadius,
      HasDerivAt right (coefficient z * right z) z)
    (hvalue : left anchor = right anchor) :
    EqOn left right
      (ball firstCenter firstRadius ∩ ball secondCenter secondRadius) := by
  apply solution_eqOn_of_eq_at
    (isOpen_ball.inter isOpen_ball)
    ((convex_ball _ _).inter (convex_ball _ _)).isPreconnected
    hanchor hcoefficient hleft hright hleftODE hrightODE hvalue

/-- Aggregated local-existence and connected-overlap uniqueness certificate. -/
theorem analytic_linear_ode_continuation_terminal_certificate :
    (∀ {coefficient : ℂ → ℂ} {center anchor : ℂ} {radius : ℝ},
      0 < radius →
      anchor ∈ ball center radius →
      AnalyticOnNhd ℂ coefficient (ball center radius) →
      ∀ initial : ℂ,
        ∃ endpoint : ℂ → ℂ,
          AnalyticOnNhd ℂ endpoint (ball center radius) ∧
          endpoint anchor = initial ∧
          ∀ z ∈ ball center radius,
            HasDerivAt endpoint (coefficient z * endpoint z) z) ∧
    (∀ {coefficient left right : ℂ → ℂ}
      {domain : Set ℂ} {anchor : ℂ},
      IsOpen domain → IsPreconnected domain → anchor ∈ domain →
      AnalyticOnNhd ℂ coefficient domain →
      AnalyticOnNhd ℂ left domain → AnalyticOnNhd ℂ right domain →
      (∀ z ∈ domain, HasDerivAt left (coefficient z * left z) z) →
      (∀ z ∈ domain, HasDerivAt right (coefficient z * right z) z) →
      left anchor = right anchor → EqOn left right domain) := by
  constructor
  · intro coefficient center anchor radius hradius hanchor hcoefficient initial
    obtain ⟨endpoint, hanalytic, hvalue, hODE, _hnonzero⟩ :=
      exists_solution_on_ball hradius hanchor hcoefficient initial
    exact ⟨endpoint, hanalytic, hvalue, hODE⟩
  · intro coefficient left right domain anchor hopen hconnected hanchor
      hcoefficient hleft hright hleftODE hrightODE hvalue
    exact solution_eqOn_of_eq_at hopen hconnected hanchor hcoefficient
      hleft hright hleftODE hrightODE hvalue

end FormalAnalyticLinearODEContinuation
