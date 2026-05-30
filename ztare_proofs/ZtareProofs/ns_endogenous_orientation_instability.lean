import Mathlib.Analysis.SpecialFunctions.Exp
import Mathlib.Tactic
import ZtareProofs.ns_centrifugal_transversality
import ZtareProofs.ns_marginal_tax_rate

namespace ZtareProofs

/-!
`ns_endogenous_orientation_instability` formalizes the lesson imported from the
163d orientation controls.

In the gravity sandbox, tensor orientation is an externally imposed boundary
parameter. In Navier-Stokes, the profitable orientation is a material state
variable: the vorticity/strain-frame alignment evolves under the PDE. This file
therefore names the proof route where blowup is blocked not because the
instantaneous viscous tax already exceeds production, but because the equations
cannot hold the high-profit orientation fixed.
-/

/--
An abstract high-intensity orientation-escape law.

`escapeVelocity E` is the endogenous outward speed of the signed escape
coordinate at intensity `E`. A positive lower bound says the danger orientation
is not a controllable external knob: once the state is sufficiently intense, it
is forced out of alignment.
-/
def endogenousEscapeLaw
    (escapeVelocity : Real → Real) (EStar γ : Real) : Prop :=
  ∀ ⦃E : Real⦄, EStar ≤ E → γ ≤ escapeVelocity E

/--
A profitable orientation lock would mean that some high-intensity return can
hold the escape coordinate non-increasing.
-/
def profitableOrientationLock
    (escapeVelocity : Real → Real) (EStar : Real) : Prop :=
  ∃ E : Real, EStar ≤ E ∧ escapeVelocity E ≤ 0

/--
Angular gain-suppression premise.

`G0` is the hypothetical perfectly aligned gain. `Gθ` is the realized gain
after endogenous frame escape has moved the state away from the high-profit
orientation. A discount `discount < 1` represents the angular penalty.
-/
def angularGainSuppressed
    (G0 Gθ : Real → Real) (discount EStar : Real) : Prop :=
  ∀ ⦃E : Real⦄, EStar ≤ E → Gθ E ≤ discount * G0 E

/--
Quadratic angular gain-decay law.

This is the formal version of the orientation lesson: `G0` is the aligned
gain envelope, `Gθ` is the realized gain after the frame has escaped by angle
`θ E`, and the high-gain orientation loses efficiency at least quadratically
away from alignment.
-/
def quadraticAngularGainDecay
    (G0 Gθ θ : Real → Real) (c EStar : Real) : Prop :=
  ∀ ⦃E : Real⦄, EStar ≤ E → Gθ E ≤ (1 - c * (θ E) ^ 2) * G0 E

/--
High-intensity angular escape lower bound.

Angles are represented as nonnegative distances from the profitable alignment.
-/
def angularEscapeLowerBound
    (θ : Real → Real) (EStar θStar : Real) : Prop :=
  ∀ ⦃E : Real⦄, EStar ≤ E → θStar ≤ θ E

/-- The fixed discount induced by escaping at least `θStar` from alignment. -/
noncomputable def angularDiscount (c θStar : Real) : Real :=
  1 - c * θStar ^ 2

/--
If the endogenous escape law has a strictly positive lower bound, a profitable
orientation lock is impossible above the threshold.
-/
theorem no_profitable_orientation_lock_of_endogenous_escape
    {escapeVelocity : Real → Real} {EStar γ : Real}
    (hγ : 0 < γ)
    (hlaw : endogenousEscapeLaw escapeVelocity EStar γ) :
    ¬ profitableOrientationLock escapeVelocity EStar := by
  intro hlock
  rcases hlock with ⟨E, hE, hnonpos⟩
  have hpos : 0 < escapeVelocity E := lt_of_lt_of_le hγ (hlaw hE)
  linarith

/--
If angular escape suppresses the realized gain by a factor strictly below one,
then any positive baseline marginal tax rate is boosted by `1 / discount`.
-/
theorem marginal_tax_boost_of_angular_gain_suppression
    {G0 Gθ L : cycleGain} {discount EStar E : Real}
    (hdiscount_pos : 0 < discount)
    (hLnonneg : 0 ≤ L E)
    (hG0pos : 0 < G0 E)
    (hGθpos : 0 < Gθ E)
    (hE : EStar ≤ E)
    (hsupp : angularGainSuppressed G0 Gθ discount EStar) :
    marginalTaxRate G0 L E / discount ≤ marginalTaxRate Gθ L E := by
  unfold marginalTaxRate
  have hGθ_le : Gθ E ≤ discount * G0 E := hsupp hE
  have h_inv : 1 / (discount * G0 E) ≤ 1 / (Gθ E) := by
    exact one_div_le_one_div_of_le hGθpos hGθ_le
  have hmul : L E * (1 / (discount * G0 E)) ≤ L E * (1 / (Gθ E)) := by
    exact mul_le_mul_of_nonneg_left h_inv hLnonneg
  have hleft : L E / G0 E / discount = L E * (discount * G0 E)⁻¹ := by
    field_simp [hdiscount_pos.ne', hG0pos.ne']
  have hright : L E / Gθ E = L E * (1 / (Gθ E)) := by
    ring
  simpa [hleft, hright, one_div] using hmul

/--
Quadratic angular decay plus a high-intensity escape angle yields the abstract
gain-suppression premise used by the recurrence spine.

This is the exact bridge from "orientation is the hidden control variable" to
the scalar budget map: if the PDE supplies an angle floor `θStar`, then the
realized danger gain is uniformly discounted by `1 - c θStar²`.
-/
theorem angular_gain_suppressed_of_quadratic_escape
    {G0 Gθ θ : Real → Real} {c EStar θStar : Real}
    (hquad : quadraticAngularGainDecay G0 Gθ θ c EStar)
    (hescape : angularEscapeLowerBound θ EStar θStar)
    (hG0_nonneg : ∀ ⦃E : Real⦄, EStar ≤ E → 0 ≤ G0 E)
    (hc : 0 ≤ c)
    (hθStar_nonneg : 0 ≤ θStar) :
    angularGainSuppressed G0 Gθ (angularDiscount c θStar) EStar := by
  intro E hE
  unfold angularDiscount
  have hθ_le : θStar ≤ θ E := hescape hE
  have hsq_le : θStar ^ 2 ≤ (θ E) ^ 2 := by
    nlinarith [hθStar_nonneg, hθ_le]
  have hcmul : c * θStar ^ 2 ≤ c * (θ E) ^ 2 := by
    exact mul_le_mul_of_nonneg_left hsq_le hc
  have hfactor : 1 - c * (θ E) ^ 2 ≤ 1 - c * θStar ^ 2 := by
    linarith
  have hscaled :
      (1 - c * (θ E) ^ 2) * G0 E ≤
        (1 - c * θStar ^ 2) * G0 E := by
    exact mul_le_mul_of_nonneg_right hfactor (hG0_nonneg hE)
  exact le_trans (hquad hE) hscaled

/--
Tax dominance transfers from a discounted aligned gain to the realized gain.

This is the recurrence-facing algebraic statement: if the baseline loss already
beats the angularly discounted aligned gain, then it beats the realized gain.
-/
theorem tax_dominance_of_discounted_gain_bound
    {G0 Gθ L : cycleGain} {discount EStar : Real}
    (hsupp : angularGainSuppressed G0 Gθ discount EStar)
    (hdiscounted :
      ∀ ⦃E : Real⦄, EStar ≤ E → discount * G0 E < L E) :
    exhaustHorizon Gθ L EStar := by
  intro E hE
  exact lt_of_le_of_lt (hsupp hE) (hdiscounted hE)

/--
Angular gain suppression routes directly to recurrence contraction.
-/
theorem contractive_recurrence_of_angular_suppression
    {G0 Gθ L : cycleGain} {discount EStar : Real}
    (hsupp : angularGainSuppressed G0 Gθ discount EStar)
    (hdiscounted :
      ∀ ⦃E : Real⦄, EStar ≤ E → discount * G0 E < L E) :
    contractiveAbove (recurrenceFromGainLoss Gθ L) EStar := by
  exact contractive_of_exhaustHorizon
    (tax_dominance_of_discounted_gain_bound hsupp hdiscounted)

/--
Orientation-budget cap: if endogenous escape pushes the state across a danger
tube of width `Δ - a0` at speed at least `γ`, then a production rate bounded by
`χmax` can harvest at most this integrated budget.
-/
noncomputable def orientationVisitBudget (χmax a0 Δ γ : Real) : Real :=
  χmax * ((Δ - a0) / γ)

/--
The compact version of the NS orientation-instability route:
positive endogenous escape bounds dwell time, and the dwell bound caps
single-visit amplification.
-/
theorem visit_cap_of_endogenous_orientation_instability
    {ω_enter ω_exit χmax a0 Δ γ dwell : Real}
    (hω_nonneg : 0 ≤ ω_enter)
    (hgrowth : ω_exit ≤ ω_enter * Real.exp (χmax * dwell))
    (hχmax : 0 ≤ χmax)
    (hγ : 0 < γ)
    (ha0 : 0 ≤ a0)
    (ha0_le : a0 ≤ Δ)
    (hband : a0 + γ * dwell ≤ Δ)
    (hbudget_cap : orientationVisitBudget χmax a0 Δ γ ≤ (1 : Real) / 100) :
    ω_exit ≤ ω_enter * Real.exp ((1 : Real) / 100) := by
  unfold orientationVisitBudget at hbudget_cap
  exact visit_cap_of_signed_escape
    hω_nonneg hgrowth hχmax hγ ha0 ha0_le hband hbudget_cap

/--
Pointwise centrifugal version:
if the `-Ω²` transverse channel beats pressure, viscosity, and vorticity-vector
rotation by a positive margin `γ`, then the danger orientation is endogenously
unstable and the visit amplification is capped.
-/
theorem visit_cap_of_centrifugal_orientation_instability
    {ω_enter ω_exit χmax a0 Δ γ dwell : Real}
    {dEscape tauOmegaSq tauPressure tauViscous tauOmegaDir : Real}
    (hω_nonneg : 0 ≤ ω_enter)
    (hgrowth : ω_exit ≤ ω_enter * Real.exp (χmax * dwell))
    (hχmax : 0 ≤ χmax)
    (hγ : 0 < γ)
    (ha0 : 0 ≤ a0)
    (ha0_le : a0 ≤ Δ)
    (hdecomp : dEscape = tauOmegaSq + tauPressure + tauViscous + tauOmegaDir)
    (hmargin : γ ≤ tauOmegaSq - |tauPressure| - |tauViscous| - |tauOmegaDir|)
    (hband : a0 + γ * dwell ≤ Δ)
    (hbudget_cap : orientationVisitBudget χmax a0 Δ γ ≤ (1 : Real) / 100) :
    ω_exit ≤ ω_enter * Real.exp ((1 : Real) / 100) := by
  have _hescape : γ ≤ dEscape := by
    exact outward_transversality_of_centrifugal_margin hdecomp hmargin
  exact visit_cap_of_endogenous_orientation_instability
    hω_nonneg hgrowth hχmax hγ ha0 ha0_le hband hbudget_cap

/--
Model-torque version using the theorem-seed centrifugal lower bound.

This is the current analytic bottleneck in its cleanest form: prove the
pointwise margin involving `ω² sin(2θ)/(2 gap)`, and the profitable alignment
visit is no longer an absorbing state.
-/
theorem visit_cap_of_model_centrifugal_orientation_instability
    {ω_enter ω_exit χmax a0 Δ γ dwell : Real}
    {dEscape ω θ gap tauPressure tauViscous tauOmegaDir : Real}
    (hω_nonneg : 0 ≤ ω_enter)
    (hgrowth : ω_exit ≤ ω_enter * Real.exp (χmax * dwell))
    (hχmax : 0 ≤ χmax)
    (hγ : 0 < γ)
    (ha0 : 0 ≤ a0)
    (ha0_le : a0 ≤ Δ)
    (hgap : 0 < gap)
    (hdecomp :
      dEscape =
        centrifugalTorqueLowerBound ω θ gap + tauPressure + tauViscous + tauOmegaDir)
    (hmargin :
      γ ≤ centrifugalTorqueLowerBound ω θ gap - |tauPressure| - |tauViscous| - |tauOmegaDir|)
    (hband : a0 + γ * dwell ≤ Δ)
    (hbudget_cap : orientationVisitBudget χmax a0 Δ γ ≤ (1 : Real) / 100) :
    ω_exit ≤ ω_enter * Real.exp ((1 : Real) / 100) := by
  have _hescape : γ ≤ dEscape := by
    exact outward_transversality_of_model_centrifugal_bound
      hgap hdecomp hmargin
  exact visit_cap_of_endogenous_orientation_instability
    hω_nonneg hgrowth hχmax hγ ha0 ha0_le hband hbudget_cap

/--
Target shape after the 163d comparison:
the proof burden is no longer immediate viscous bankruptcy. It is proving that
the endogenous orientation law makes the profitable alignment non-absorbing
with a budget small enough to prevent consolidation.
-/
theorem endogenous_orientation_instability_target_shape
    {χmax a0 Δ γ : Real}
    (_hγ : 0 < γ)
    (hsmall : orientationVisitBudget χmax a0 Δ γ ≤ (1 : Real) / 100) :
    orientationVisitBudget χmax a0 Δ γ ≤ (1 : Real) / 100 := by
  exact hsmall

end ZtareProofs
