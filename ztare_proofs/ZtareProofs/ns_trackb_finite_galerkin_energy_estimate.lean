import Mathlib.Analysis.InnerProductSpace.EuclideanDist
import Mathlib.MeasureTheory.Integral.IntervalIntegral.FundThmCalculus
import Mathlib.MeasureTheory.Integral.DominatedConvergence
import Mathlib.Tactic

/-!
# Finite-N Galerkin energy estimate (force-free, conservative nonlinearity)

This file proves the classical *finite-dimensional* energy estimate for an
abstract Galerkin truncation of Navier-Stokes.

If `u : ℝ → EuclideanSpace ℝ (Fin N)` is differentiable on `[0, T]` and the
energy ODE

  d/dt (1/2)‖u(t)‖² = -D(t)

holds on `(0, T)` for some continuous nonneg `D : ℝ → ℝ`
(viscous dissipation `ν‖∇u_N(t)‖²`, force-free + nonlinearity-conservative),
then

  (1/2)‖u(T)‖² + ∫₀ᵀ D(t) dt ≤ (1/2)‖u(0)‖².

Integrated, this is in fact an equality (the dissipation is exactly the
energy lost); the inequality is the weakest, force-free Leray-Hopf-style
restatement.

This is purely an ODE / integration fact: the fundamental theorem of
calculus turns the pointwise ODE into the integral identity.  No PDE
content is involved — that is the whole point of the finite-N estimate.

References:
  Constantin–Foias, *Navier-Stokes Equations*, §7.
  Temam, *Navier-Stokes Equations*, Ch. III §3 (Galerkin energy estimate).
-/

namespace ZtareProofs.NS

noncomputable section

open MeasureTheory Set

/-- Hypotheses for the abstract finite-N Galerkin energy estimate.
`u` is the (finite-dim) velocity field, `D` is the dissipation
`t ↦ ν‖∇u_N(t)‖²`, both packaged as the data of an ODE solution
satisfying the force-free / conservative-nonlinearity energy ODE. -/
structure FiniteGalerkinEnergyData (N : ℕ) (T : ℝ) where
  /-- The truncated velocity field. -/
  u : ℝ → EuclideanSpace ℝ (Fin N)
  /-- The viscous dissipation rate `ν‖∇u_N(t)‖²`, treated abstractly. -/
  D : ℝ → ℝ
  /-- `T > 0`, so we are integrating over a nondegenerate interval. -/
  T_pos : 0 < T
  /-- `D` is continuous on `[0, T]` (so it is integrable on the interval). -/
  D_continuousOn : ContinuousOn D (Icc 0 T)
  /-- `D` is nonneg on `[0, T]`. -/
  D_nonneg : ∀ t ∈ Icc (0 : ℝ) T, 0 ≤ D t
  /-- The energy `t ↦ (1/2)‖u t‖²` is differentiable on `[0, T]`
  (closed interval; this gives continuity at the endpoints). -/
  energy_differentiable :
    ∀ t ∈ Icc (0 : ℝ) T, DifferentiableAt ℝ (fun s => (1/2 : ℝ) * ‖u s‖^2) t
  /-- The force-free, nonlinearity-conservative energy ODE on `(0, T)`:
  `d/dt (1/2)‖u(t)‖² = -D(t)`. -/
  energy_ode :
    ∀ t ∈ Ioo (0 : ℝ) T, deriv (fun s => (1/2 : ℝ) * ‖u s‖^2) t = - D t

namespace FiniteGalerkinEnergyData

variable {N : ℕ} {T : ℝ}

/-- The kinetic energy `t ↦ (1/2)‖u(t)‖²` as a real-valued function. -/
def energy (H : FiniteGalerkinEnergyData N T) : ℝ → ℝ :=
  fun t => (1/2 : ℝ) * ‖H.u t‖^2

lemma energy_differentiableAt
    (H : FiniteGalerkinEnergyData N T) {t : ℝ} (ht : t ∈ Icc (0 : ℝ) T) :
    DifferentiableAt ℝ H.energy t :=
  H.energy_differentiable t ht

lemma energy_continuousOn (H : FiniteGalerkinEnergyData N T) :
    ContinuousOn H.energy (Icc 0 T) := by
  intro t ht
  exact (H.energy_differentiableAt ht).continuousAt.continuousWithinAt

/-- On the open interval `(0, T)`, the energy has derivative `-D`. -/
lemma hasDerivAt_energy_neg_D
    (H : FiniteGalerkinEnergyData N T) {t : ℝ} (ht : t ∈ Ioo (0 : ℝ) T) :
    HasDerivAt H.energy (- H.D t) t := by
  have htIcc : t ∈ Icc (0 : ℝ) T := ⟨le_of_lt ht.1, le_of_lt ht.2⟩
  have hdiff : DifferentiableAt ℝ H.energy t := H.energy_differentiableAt htIcc
  have hode : deriv H.energy t = - H.D t := H.energy_ode t ht
  have h := hdiff.hasDerivAt
  rw [hode] at h
  exact h

/-- `D` is interval-integrable on `[0, T]`. -/
lemma D_intervalIntegrable (H : FiniteGalerkinEnergyData N T) :
    IntervalIntegrable H.D MeasureTheory.volume 0 T := by
  have hle : (0 : ℝ) ≤ T := H.T_pos.le
  have hcont : ContinuousOn H.D (uIcc (0 : ℝ) T) := by
    rw [uIcc_of_le hle]
    exact H.D_continuousOn
  exact hcont.intervalIntegrable

/-- `-D` is interval-integrable on `[0, T]`. -/
lemma neg_D_intervalIntegrable (H : FiniteGalerkinEnergyData N T) :
    IntervalIntegrable (fun t => - H.D t) MeasureTheory.volume 0 T :=
  H.D_intervalIntegrable.neg

/-- **Fundamental theorem of calculus, applied to the energy ODE.**

  ∫₀ᵀ -D(t) dt = (1/2)‖u(T)‖² - (1/2)‖u(0)‖². -/
lemma integral_neg_D_eq
    (H : FiniteGalerkinEnergyData N T) :
    ∫ t in (0 : ℝ)..T, - H.D t = H.energy T - H.energy 0 := by
  have hle : (0 : ℝ) ≤ T := H.T_pos.le
  have hcont : ContinuousOn H.energy (Icc 0 T) := H.energy_continuousOn
  have hderiv : ∀ x ∈ Ioo (0 : ℝ) T,
      HasDerivAt H.energy (- H.D x) x :=
    fun x hx => H.hasDerivAt_energy_neg_D hx
  have hint : IntervalIntegrable (fun t => - H.D t) MeasureTheory.volume 0 T :=
    H.neg_D_intervalIntegrable
  exact intervalIntegral.integral_eq_sub_of_hasDerivAt_of_le hle hcont hderiv hint

/-- Convert the interval integral `∫ s in 0..T, D s` to the set integral
`∫ s in Icc 0 T, D s` (the boundary is null). -/
lemma intervalIntegral_D_eq_setIntegral
    (H : FiniteGalerkinEnergyData N T) :
    ∫ t in (0 : ℝ)..T, H.D t = ∫ t in Icc (0 : ℝ) T, H.D t := by
  have hle : (0 : ℝ) ≤ T := H.T_pos.le
  rw [intervalIntegral.integral_of_le hle, MeasureTheory.integral_Icc_eq_integral_Ioc]

/-- **Finite-N Galerkin energy identity (force-free).**

  (1/2)‖u(T)‖² + ∫₀ᵀ D(t) dt = (1/2)‖u(0)‖². -/
theorem finite_galerkin_energy_identity
    (H : FiniteGalerkinEnergyData N T) :
    H.energy T + ∫ t in Icc (0 : ℝ) T, H.D t = H.energy 0 := by
  have hFTC : ∫ t in (0 : ℝ)..T, - H.D t = H.energy T - H.energy 0 :=
    H.integral_neg_D_eq
  have hneg : ∫ t in (0 : ℝ)..T, - H.D t = - ∫ t in (0 : ℝ)..T, H.D t :=
    intervalIntegral.integral_neg
  have hset : ∫ t in (0 : ℝ)..T, H.D t = ∫ t in Icc (0 : ℝ) T, H.D t :=
    H.intervalIntegral_D_eq_setIntegral
  -- combine: -(∫ Icc D) = energy T - energy 0
  rw [hneg, hset] at hFTC
  linarith

/-- **Finite-N Galerkin energy estimate (force-free).**

This is the canonical force-free energy inequality:

  (1/2)‖u(T)‖² + ∫₀ᵀ D(t) dt ≤ (1/2)‖u(0)‖².

In our setting it is in fact an equality (the dissipation accounts exactly
for the energy lost), but the inequality form is what is used downstream
in Leray-Hopf style limit passage. -/
theorem finite_galerkin_energy_estimate
    (H : FiniteGalerkinEnergyData N T) :
    H.energy T + ∫ t in Icc (0 : ℝ) T, H.D t ≤ H.energy 0 :=
  le_of_eq (H.finite_galerkin_energy_identity)

end FiniteGalerkinEnergyData

end

end ZtareProofs.NS
