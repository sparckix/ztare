import Mathlib.Analysis.Analytic.IsolatedZeros
import Mathlib.Analysis.Calculus.ContDiff.Polynomial
import Mathlib.Analysis.ODE.Gronwall
import Mathlib.Tactic

/-!
# Analytic autonomous polynomial trajectories

This file joins three existing Mathlib mechanisms without introducing a
second ODE solver:

* polynomial vector fields are locally Lipschitz;
* Grönwall uniqueness identifies two solutions near one initial time; and
* the analytic identity theorem propagates that identification through a
  preconnected continuation domain.

The terminal result identifies a selected trajectory for the scaled
generator `c • p` with the time-rescaled trajectory `t ↦ x (c*t)` of `p`.
Both endpoints `0` and `1` must belong to the comparison domain, and the
rescaled times must remain in the original trajectory's domain.
-/

namespace FormalAnalyticAutonomousTrajectory

open Filter Set
open scoped Topology

/-- Two analytic solutions of the same autonomous polynomial ODE with the
same initial value agree in a neighborhood of the initial time. -/
theorem eventuallyEq_of_same_polynomial_ode
    (generator : Polynomial ℝ)
    {left right : ℝ → ℝ} {t₀ : ℝ}
    (hleftAnalytic : AnalyticAt ℝ left t₀)
    (hrightAnalytic : AnalyticAt ℝ right t₀)
    (hleftODE : ∀ᶠ t in 𝓝 t₀,
      HasDerivAt left (generator.aeval (left t)) t)
    (hrightODE : ∀ᶠ t in 𝓝 t₀,
      HasDerivAt right (generator.aeval (right t)) t)
    (hinitial : left t₀ = right t₀) :
    left =ᶠ[𝓝 t₀] right := by
  obtain ⟨K, stateSet, hstateSet, hlipschitz⟩ :=
    (generator.contDiff_aeval 1).contDiffAt.exists_lipschitzOnWith
      (x := left t₀)
  have hleftMem : ∀ᶠ t in 𝓝 t₀, left t ∈ stateSet :=
    hleftAnalytic.continuousAt.preimage_mem_nhds hstateSet
  have hrightStateSet : stateSet ∈ 𝓝 (right t₀) := by
    simpa only [← hinitial] using hstateSet
  have hrightMem : ∀ᶠ t in 𝓝 t₀, right t ∈ stateSet :=
    hrightAnalytic.continuousAt.preimage_mem_nhds hrightStateSet
  exact ODE_solution_unique_of_eventually
    (K := K)
    (v := fun _ x ↦ generator.aeval x)
    (s := fun _ ↦ stateSet)
    (.of_forall fun _ ↦ hlipschitz)
    (hleftODE.and hleftMem)
    (hrightODE.and hrightMem)
    hinitial

/-- Analytic solutions of one autonomous polynomial ODE agree throughout a
preconnected open continuation domain once they agree at one point. -/
theorem eqOn_of_same_polynomial_ode
    (generator : Polynomial ℝ)
    {domain : Set ℝ} {left right : ℝ → ℝ} {t₀ : ℝ}
    (hopen : IsOpen domain)
    (hpreconnected : IsPreconnected domain)
    (ht₀ : t₀ ∈ domain)
    (hleftAnalytic : AnalyticOnNhd ℝ left domain)
    (hrightAnalytic : AnalyticOnNhd ℝ right domain)
    (hleftODE : ∀ t ∈ domain,
      HasDerivAt left (generator.aeval (left t)) t)
    (hrightODE : ∀ t ∈ domain,
      HasDerivAt right (generator.aeval (right t)) t)
    (hinitial : left t₀ = right t₀) :
    EqOn left right domain := by
  have hdomain : domain ∈ 𝓝 t₀ := hopen.mem_nhds ht₀
  have hleftODE' : ∀ᶠ t in 𝓝 t₀,
      HasDerivAt left (generator.aeval (left t)) t :=
    by
      filter_upwards [hdomain] with t ht
      exact hleftODE t ht
  have hrightODE' : ∀ᶠ t in 𝓝 t₀,
      HasDerivAt right (generator.aeval (right t)) t :=
    by
      filter_upwards [hdomain] with t ht
      exact hrightODE t ht
  exact hleftAnalytic.eqOn_of_preconnected_of_eventuallyEq
    hrightAnalytic hpreconnected ht₀
    (eventuallyEq_of_same_polynomial_ode generator
      (hleftAnalytic t₀ ht₀) (hrightAnalytic t₀ ht₀)
      hleftODE' hrightODE' hinitial)

/-- A trajectory of the scaled generator `c • p` is the selected
time-rescaling `t ↦ x (c*t)` of a trajectory of `p`, throughout any declared
preconnected analytic continuation domain. -/
theorem proportional_trajectory_eqOn_time_rescaling
    (generator : Polynomial ℝ) (c : ℝ)
    {originalDomain comparisonDomain : Set ℝ}
    {original scaled : ℝ → ℝ}
    (hcomparisonOpen : IsOpen comparisonDomain)
    (hcomparisonPreconnected : IsPreconnected comparisonDomain)
    (hzero : (0 : ℝ) ∈ comparisonDomain)
    (hmaps : MapsTo (fun t : ℝ ↦ c * t)
      comparisonDomain originalDomain)
    (horiginalAnalytic : AnalyticOnNhd ℝ original originalDomain)
    (hscaledAnalytic : AnalyticOnNhd ℝ scaled comparisonDomain)
    (horiginalODE : ∀ t ∈ originalDomain,
      HasDerivAt original (generator.aeval (original t)) t)
    (hscaledODE : ∀ t ∈ comparisonDomain,
      HasDerivAt scaled (c * generator.aeval (scaled t)) t)
    (hinitial : original 0 = scaled 0) :
    EqOn (fun t ↦ original (c * t)) scaled comparisonDomain := by
  have hreparamAnalytic :
      AnalyticOnNhd ℝ (fun t : ℝ ↦ original (c * t)) comparisonDomain := by
    simpa only [Function.comp_def] using
      horiginalAnalytic.comp
        (analyticOnNhd_const.mul analyticOnNhd_id) hmaps
  apply eqOn_of_same_polynomial_ode (Polynomial.C c * generator)
    hcomparisonOpen hcomparisonPreconnected hzero
    hreparamAnalytic hscaledAnalytic
  · intro t ht
    have hderiv :=
      (horiginalODE (c * t) (hmaps ht)).comp t
        (hasDerivAt_const_mul c)
    simpa only [map_mul, Polynomial.aeval_C, RingHom.id_apply,
      mul_comm] using hderiv
  · intro t ht
    simpa only [map_mul, Polynomial.aeval_C, RingHom.id_apply]
      using hscaledODE t ht
  · simpa only [mul_zero] using hinitial

/-- Endpoint form of proportional trajectory identification.  The conclusion
uses only the explicitly declared time `c` of the original branch. -/
theorem proportional_trajectory_time_one_eq_original_time
    (generator : Polynomial ℝ) (c : ℝ)
    {originalDomain comparisonDomain : Set ℝ}
    {original scaled : ℝ → ℝ}
    (hcomparisonOpen : IsOpen comparisonDomain)
    (hcomparisonPreconnected : IsPreconnected comparisonDomain)
    (hzero : (0 : ℝ) ∈ comparisonDomain)
    (hone : (1 : ℝ) ∈ comparisonDomain)
    (hmaps : MapsTo (fun t : ℝ ↦ c * t)
      comparisonDomain originalDomain)
    (horiginalAnalytic : AnalyticOnNhd ℝ original originalDomain)
    (hscaledAnalytic : AnalyticOnNhd ℝ scaled comparisonDomain)
    (horiginalODE : ∀ t ∈ originalDomain,
      HasDerivAt original (generator.aeval (original t)) t)
    (hscaledODE : ∀ t ∈ comparisonDomain,
      HasDerivAt scaled (c * generator.aeval (scaled t)) t)
    (hinitial : original 0 = scaled 0) :
    scaled 1 = original c := by
  have h := proportional_trajectory_eqOn_time_rescaling generator c
    hcomparisonOpen hcomparisonPreconnected hzero hmaps
    horiginalAnalytic hscaledAnalytic horiginalODE hscaledODE hinitial hone
  simpa only [mul_one] using h.symm

/-- Pointwise trajectory identification promotes to equality of the complete
selected endpoint maps when the continuation data are supplied uniformly in
the initial state. -/
theorem proportional_endpoint_map_eq_original_time
    (generator : Polynomial ℝ) (c : ℝ)
    (originalDomain comparisonDomain : Set ℝ)
    (original scaled : ℝ → ℝ → ℝ)
    (hcomparisonOpen : IsOpen comparisonDomain)
    (hcomparisonPreconnected : IsPreconnected comparisonDomain)
    (hzero : (0 : ℝ) ∈ comparisonDomain)
    (hone : (1 : ℝ) ∈ comparisonDomain)
    (hmaps : MapsTo (fun t : ℝ ↦ c * t)
      comparisonDomain originalDomain)
    (horiginalAnalytic : ∀ x,
      AnalyticOnNhd ℝ (original x) originalDomain)
    (hscaledAnalytic : ∀ x,
      AnalyticOnNhd ℝ (scaled x) comparisonDomain)
    (horiginalODE : ∀ x t, t ∈ originalDomain →
      HasDerivAt (original x) (generator.aeval (original x t)) t)
    (hscaledODE : ∀ x t, t ∈ comparisonDomain →
      HasDerivAt (scaled x) (c * generator.aeval (scaled x t)) t)
    (hinitial : ∀ x, original x 0 = scaled x 0) :
    (fun x ↦ scaled x 1) = fun x ↦ original x c := by
  funext x
  exact proportional_trajectory_time_one_eq_original_time generator c
    hcomparisonOpen hcomparisonPreconnected hzero hone hmaps
    (horiginalAnalytic x) (hscaledAnalytic x)
    (horiginalODE x) (hscaledODE x) (hinitial x)

/-- Aggregated reusable certificate: proportional analytic polynomial
trajectories are identified on their comparison domain and at time one. -/
theorem proportional_analytic_trajectory_terminal_certificate :
    (∀ (generator : Polynomial ℝ) (c : ℝ)
      (originalDomain comparisonDomain : Set ℝ)
      (original scaled : ℝ → ℝ),
      IsOpen comparisonDomain →
      IsPreconnected comparisonDomain →
      (0 : ℝ) ∈ comparisonDomain →
      MapsTo (fun t : ℝ ↦ c * t) comparisonDomain originalDomain →
      AnalyticOnNhd ℝ original originalDomain →
      AnalyticOnNhd ℝ scaled comparisonDomain →
      (∀ t ∈ originalDomain,
        HasDerivAt original (generator.aeval (original t)) t) →
      (∀ t ∈ comparisonDomain,
        HasDerivAt scaled (c * generator.aeval (scaled t)) t) →
      original 0 = scaled 0 →
      EqOn (fun t ↦ original (c * t)) scaled comparisonDomain) ∧
    (∀ (generator : Polynomial ℝ) (c : ℝ)
      (originalDomain comparisonDomain : Set ℝ)
      (original scaled : ℝ → ℝ),
      IsOpen comparisonDomain →
      IsPreconnected comparisonDomain →
      (0 : ℝ) ∈ comparisonDomain →
      (1 : ℝ) ∈ comparisonDomain →
      MapsTo (fun t : ℝ ↦ c * t) comparisonDomain originalDomain →
      AnalyticOnNhd ℝ original originalDomain →
      AnalyticOnNhd ℝ scaled comparisonDomain →
      (∀ t ∈ originalDomain,
        HasDerivAt original (generator.aeval (original t)) t) →
      (∀ t ∈ comparisonDomain,
        HasDerivAt scaled (c * generator.aeval (scaled t)) t) →
      original 0 = scaled 0 →
      scaled 1 = original c) ∧
    (∀ (generator : Polynomial ℝ) (c : ℝ)
      (originalDomain comparisonDomain : Set ℝ)
      (original scaled : ℝ → ℝ → ℝ),
      IsOpen comparisonDomain →
      IsPreconnected comparisonDomain →
      (0 : ℝ) ∈ comparisonDomain →
      (1 : ℝ) ∈ comparisonDomain →
      MapsTo (fun t : ℝ ↦ c * t) comparisonDomain originalDomain →
      (∀ x, AnalyticOnNhd ℝ (original x) originalDomain) →
      (∀ x, AnalyticOnNhd ℝ (scaled x) comparisonDomain) →
      (∀ x t, t ∈ originalDomain →
        HasDerivAt (original x) (generator.aeval (original x t)) t) →
      (∀ x t, t ∈ comparisonDomain →
        HasDerivAt (scaled x) (c * generator.aeval (scaled x t)) t) →
      (∀ x, original x 0 = scaled x 0) →
      (fun x ↦ scaled x 1) = fun x ↦ original x c) := by
  exact ⟨proportional_trajectory_eqOn_time_rescaling,
    proportional_trajectory_time_one_eq_original_time,
    proportional_endpoint_map_eq_original_time⟩

end FormalAnalyticAutonomousTrajectory
