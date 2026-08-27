import Mathlib.Algebra.Polynomial.FieldDivision
import Mathlib.Analysis.Analytic.Polynomial
import Mathlib.Tactic
import ZtareProofs.FormalAnalyticLinearODEContinuation

/-!
# Rigidity of polynomial trajectories starting at an equilibrium

Polynomial division turns displacement from an equilibrium into a scalar
linear ODE.  Analytic linear-ODE uniqueness then forces the displacement to
vanish on the complete connected continuation domain.
-/

namespace FormalPolynomialEquilibriumTrajectoryRigidity

open Filter Polynomial Set
open scoped Topology

open FormalAnalyticLinearODEContinuation

/-- The polynomial divided difference at `center`. -/
noncomputable def equilibriumQuotient
    (p : ℂ[X]) (center : ℂ) : ℂ[X] :=
  p /ₘ (X - C center)

/-- Evaluation of the polynomial factorization at an equilibrium. -/
theorem eval_eq_sub_mul_equilibriumQuotient
    (p : ℂ[X]) (center y : ℂ)
    (hequilibrium : p.eval center = 0) :
    p.eval y =
      (y - center) * (equilibriumQuotient p center).eval y := by
  have hfactor := X_sub_C_mul_divByMonic_eq_sub_modByMonic p center
  have heval := congrArg (fun r : ℂ[X] ↦ r.eval y) hfactor
  simp only [eval_mul, eval_sub, eval_X, eval_C,
    modByMonic_X_sub_C_eq_C_eval] at heval
  rw [hequilibrium] at heval
  simpa using heval.symm

/-- An analytic polynomial trajectory starting at an equilibrium is constant
on its open preconnected continuation domain. -/
theorem equilibrium_trajectory_eqOn
    (p : ℂ[X]) (center : ℂ)
    {domain : Set ℂ} {trajectory : ℂ → ℂ} {anchor : ℂ}
    (hopen : IsOpen domain)
    (hpreconnected : IsPreconnected domain)
    (hanchor : anchor ∈ domain)
    (htrajectoryAnalytic : AnalyticOnNhd ℂ trajectory domain)
    (htrajectoryODE : ∀ t ∈ domain,
      HasDerivAt trajectory (p.eval (trajectory t)) t)
    (hinitial : trajectory anchor = center)
    (hequilibrium : p.eval center = 0) :
    EqOn trajectory (fun _ ↦ center) domain := by
  let quotient : ℂ[X] := equilibriumQuotient p center
  let coefficient : ℂ → ℂ :=
    fun t ↦ quotient.eval (trajectory t)
  let displacement : ℂ → ℂ :=
    fun t ↦ trajectory t - center
  have hcoefficientAnalytic :
      AnalyticOnNhd ℂ coefficient domain := by
    have hpolynomial :
        AnalyticOnNhd ℂ (fun y : ℂ ↦ quotient.eval y) univ :=
      AnalyticOnNhd.eval_polynomial quotient
    have hcomposition := hpolynomial.comp htrajectoryAnalytic
      (mapsTo_univ trajectory domain)
    simpa only [coefficient, Function.comp_def] using hcomposition
  have hdisplacementAnalytic :
      AnalyticOnNhd ℂ displacement domain := by
    dsimp only [displacement]
    exact htrajectoryAnalytic.sub analyticOnNhd_const
  have hzeroAnalytic :
      AnalyticOnNhd ℂ (fun _ : ℂ ↦ (0 : ℂ)) domain :=
    analyticOnNhd_const
  have hdisplacementODE : ∀ t ∈ domain,
      HasDerivAt displacement
        (coefficient t * displacement t) t := by
    intro t ht
    have hderivative := (htrajectoryODE t ht).sub_const center
    have hfactor := eval_eq_sub_mul_equilibriumQuotient
      p center (trajectory t) hequilibrium
    convert hderivative using 1
    simp only [displacement, coefficient, quotient]
    rw [hfactor]
    ring
  have hzeroODE : ∀ t ∈ domain,
      HasDerivAt (fun _ : ℂ ↦ 0)
        (coefficient t * 0) t := by
    intro t _ht
    simpa using (hasDerivAt_const t (0 : ℂ))
  have hdisplacementAnchor : displacement anchor = 0 := by
    simp [displacement, hinitial]
  have heqZero : EqOn displacement (fun _ : ℂ ↦ 0) domain :=
    solution_eqOn_of_eq_at hopen hpreconnected hanchor
      hcoefficientAnalytic hdisplacementAnalytic hzeroAnalytic
      hdisplacementODE hzeroODE hdisplacementAnchor
  intro t ht
  have hzero := heqZero ht
  simpa only [displacement, sub_eq_zero] using hzero

/-- A polynomial trajectory that is regular at time zero cannot arrive at an
equilibrium at time one.  Otherwise uniqueness based at the endpoint would
make the complete trajectory constant back to the regular source. -/
theorem time_one_endpoint_not_equilibrium_of_regular_source
    (p : ℂ[X])
    {timeDomain : Set ℂ} (trajectory : ℂ → ℂ)
    (hopen : IsOpen timeDomain)
    (hpreconnected : IsPreconnected timeDomain)
    (hzero : (0 : ℂ) ∈ timeDomain)
    (hone : (1 : ℂ) ∈ timeDomain)
    (htrajectoryAnalytic : AnalyticOnNhd ℂ trajectory timeDomain)
    (htrajectoryODE : ∀ t ∈ timeDomain,
      HasDerivAt trajectory (p.eval (trajectory t)) t)
    (hsourceRegular : p.eval (trajectory 0) ≠ 0) :
    p.eval (trajectory 1) ≠ 0 := by
  intro hendpointEquilibrium
  have heqOn := equilibrium_trajectory_eqOn
    p (trajectory 1) hopen hpreconnected hone htrajectoryAnalytic
    htrajectoryODE rfl hendpointEquilibrium
  have hsourceEq : trajectory 0 = trajectory 1 := heqOn hzero
  exact hsourceRegular (by rw [hsourceEq]; exact hendpointEquilibrium)

/-- Aggregated equilibrium-rigidity certificate for analytic polynomial
trajectories. -/
theorem polynomial_equilibrium_trajectory_rigidity_terminal_certificate :
    ∀ (p : ℂ[X]) (center : ℂ)
      (domain : Set ℂ) (trajectory : ℂ → ℂ) (anchor : ℂ),
      IsOpen domain →
      IsPreconnected domain →
      anchor ∈ domain →
      AnalyticOnNhd ℂ trajectory domain →
      (∀ t ∈ domain,
        HasDerivAt trajectory (p.eval (trajectory t)) t) →
      trajectory anchor = center →
      p.eval center = 0 →
      EqOn trajectory (fun _ ↦ center) domain := by
  intro p center domain trajectory anchor hopen hpreconnected hanchor
    htrajectoryAnalytic htrajectoryODE hinitial hequilibrium
  exact equilibrium_trajectory_eqOn p center hopen hpreconnected hanchor
    htrajectoryAnalytic htrajectoryODE hinitial hequilibrium

end FormalPolynomialEquilibriumTrajectoryRigidity
